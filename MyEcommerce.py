from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Configuración de conexión MySQL
USER = 'root'
PASSWORD = 'Admin1234'  # <-- Tu contraseña real
HOST = '127.0.0.1'
PORT = '3306'
DB_NAME = 'ecommerce'

app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------------------------------------
# MODELOS
# ---------------------------------------------------------
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, server_default=db.func.now())

    carrito = db.relationship('Carrito', backref='usuario', uselist=False, cascade="all, delete")

class Categoria(db.Model):
    __tablename__ = 'categorias'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    productos = db.relationship('Producto', backref='categoria', lazy=True)

class Producto(db.Model):
    __tablename__ = 'productos'
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias.id'), nullable=True)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer, default=0)
    imagen_url = db.Column(db.String(255))

class Carrito(db.Model):
    __tablename__ = 'carrito'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    items = db.relationship('CarritoItem', backref='carrito', cascade="all, delete-orphan")

class CarritoItem(db.Model):
    __tablename__ = 'carrito_items'
    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carrito.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    producto = db.relationship('Producto')

# ---------------------------------------------------------
# VISTAS HTML
# ---------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/tienda')
def tienda():
    return render_template('tienda.html')

# ---------------------------------------------------------
# ENDPOINTS USUARIOS Y LOGIN
# ---------------------------------------------------------
@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([{'id': u.id, 'nombre': u.nombre, 'email': u.email} for u in usuarios]), 200

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('nombre'):
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'El correo ya está registrado'}), 400

    nuevo_usuario = Usuario(nombre=data['nombre'], email=data['email'], password=data['password'])
    db.session.add(nuevo_usuario)
    db.session.commit()

    nuevo_carrito = Carrito(usuario_id=nuevo_usuario.id)
    db.session.add(nuevo_carrito)
    db.session.commit()

    return jsonify({'mensaje': 'Usuario creado con éxito', 'id': nuevo_usuario.id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(email=data.get('email')).first()

    if not usuario or usuario.password != data.get('password', ''):
        return jsonify({'error': 'Correo o contraseña incorrectos'}), 401

    return jsonify({
        'mensaje': f'Bienvenido/a, {usuario.nombre}',
        'usuario': {
            'id': usuario.id,
            'nombre': usuario.nombre,
            'email': usuario.email,
            'carrito_id': usuario.carrito.id if usuario.carrito else None
        }
    }), 200

@app.route('/api/usuarios/<int:usuario_id>', methods=['DELETE'])
def eliminar_usuario(usuario_id):
    usuario = Usuario.query.get(usuario_id)
    if not usuario:
        return jsonify({'error': 'Usuario no encontrado'}), 404
    db.session.delete(usuario)
    db.session.commit()
    return jsonify({'mensaje': 'Usuario eliminado correctamente'}), 200

# ---------------------------------------------------------
# ENDPOINTS PRODUCTOS Y CARRITO DE COMPRAS
# ---------------------------------------------------------
@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    productos = Producto.query.all()
    return jsonify([
        {
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'precio': float(p.precio),
            'stock': p.stock,
            'categoria': p.categoria.nombre if p.categoria else 'General'
        } for p in productos
    ]), 200

@app.route('/api/carrito/<int:usuario_id>', methods=['GET'])
def ver_carrito(usuario_id):
    carrito = Carrito.query.filter_by(usuario_id=usuario_id).first()
    if not carrito:
        return jsonify({'items': [], 'total': 0}), 200

    items = []
    total = 0
    for item in carrito.items:
        precio_unit = float(item.producto.precio)
        subtotal = precio_unit * item.cantidad
        total += subtotal
        items.append({
            'item_id': item.id,
            'producto_id': item.producto.id,
            'nombre': item.producto.nombre,
            'precio_unitario': precio_unit,
            'cantidad': item.cantidad,
            'subtotal': subtotal
        })

    return jsonify({'carrito_id': carrito.id, 'items': items, 'total': total}), 200

@app.route('/api/carrito/agregar', methods=['POST'])
def agregar_al_carrito():
    data = request.get_json()
    usuario_id = data.get('usuario_id')
    producto_id = data.get('producto_id')
    cantidad = int(data.get('cantidad', 1))

    carrito = Carrito.query.filter_by(usuario_id=usuario_id).first()
    if not carrito:
        carrito = Carrito(usuario_id=usuario_id)
        db.session.add(carrito)
        db.session.commit()

    item = CarritoItem.query.filter_by(carrito_id=carrito.id, producto_id=producto_id).first()
    if item:
        item.cantidad += cantidad
        if item.cantidad <= 0:
            db.session.delete(item)
    elif cantidad > 0:
        item = CarritoItem(carrito_id=carrito.id, producto_id=producto_id, cantidad=cantidad)
        db.session.add(item)

    db.session.commit()
    return jsonify({'mensaje': 'Carrito actualizado'}), 200

@app.route('/api/carrito/item/<int:item_id>', methods=['DELETE'])
def eliminar_item_carrito(item_id):
    item = CarritoItem.query.get(item_id)
    if item:
        db.session.delete(item)
        db.session.commit()
    return jsonify({'mensaje': 'Producto quitado del carrito'}), 200

@app.route('/api/carrito/vaciar/<int:usuario_id>', methods=['DELETE'])
def vaciar_carrito(usuario_id):
    carrito = Carrito.query.filter_by(usuario_id=usuario_id).first()
    if carrito:
        CarritoItem.query.filter_by(carrito_id=carrito.id).delete()
        db.session.commit()
    return jsonify({'mensaje': 'Carrito vaciado'}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)