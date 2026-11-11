from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuración de conexión MySQL
# Reemplaza 'tu_usuario' y 'tu_contraseña' por tus credenciales de MySQL local
USER = 'root'
PASSWORD = 'Admin1234'
HOST = '127.0.0.1'
PORT = '3306'
DB_NAME = 'ecommerce'

# URI de conexión utilizando pymysql como driver
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{USER}:{PASSWORD}@{HOST}:{PORT}/{DB_NAME}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ---------------------------------------------------------
# MODELOS (Mapeo de las tablas de la BD ecommerce)
# ---------------------------------------------------------

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    creado_en = db.Column(db.DateTime, server_default=db.func.now())

    # Relación 1 a 1 con Carrito
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
    __tablename__ = 'carritos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)
    items = db.relationship('CarritoItem', backref='carrito', cascade="all, delete-orphan")

class CarritoItem(db.Model):
    __tablename__ = 'carrito_items'
    id = db.Column(db.Integer, primary_key=True)
    carrito_id = db.Column(db.Integer, db.ForeignKey('carritos.id'), nullable=False)
    producto_id = db.Column(db.Integer, db.ForeignKey('productos.id'), nullable=False)
    cantidad = db.Column(db.Integer, nullable=False, default=1)
    
    producto = db.relationship('Producto')
    
# ---------------------------------------------------------
# ENDPOINTS DE AUTENTICACIÓN / LOGIN
# ---------------------------------------------------------

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email y contraseña requeridos'}), 400
        
    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'El email ya está registrado'}), 400
        
    #pwd_hash = generate_password_hash(data['password'])
    
    # Por esta (especificando el método pbkdf2):
    pwd_hash = generate_password_hash(data['password'], method='pbkdf2:sha256')
    nuevo_usuario = Usuario(
        nombre=data.get('nombre', 'Usuario'),
        email=data['email'],
        password_hash=pwd_hash
    )
    
    db.session.add(nuevo_usuario)
    db.session.commit()
    
    # Crear carrito automático para el usuario recién registrado
    nuevo_carrito = Carrito(usuario_id=nuevo_usuario.id)
    db.session.add(nuevo_carrito)
    db.session.commit()
    
    return jsonify({'mensaje': 'Usuario registrado con éxito', 'usuario_id': nuevo_usuario.id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(email=data.get('email')).first()
    
    if usuario and check_password_hash(usuario.password_hash, data.get('password', '')):
        return jsonify({
            'mensaje': 'Login exitoso',
            'usuario': {
                'id': usuario.id,
                'nombre': usuario.nombre,
                'email': usuario.email
            }
        }), 200
        
    return jsonify({'error': 'Credenciales inválidas'}), 401

# ---------------------------------------------------------
# ENDPOINTS PARA CARRITO DE COMPRAS
# ---------------------------------------------------------

@app.route('/api/carrito/agregar', methods=['POST'])
def agregar_al_carrito():
    data = request.get_json()
    usuario_id = data.get('usuario_id')
    producto_id = data.get('producto_id')
    cantidad = data.get('cantidad', 1)
    
    carrito = Carrito.query.filter_by(usuario_id=usuario_id).first()
    if not carrito:
        return jsonify({'error': 'Carrito no encontrado'}), 404
        
    item = CarritoItem.query.filter_by(carrito_id=carrito.id, producto_id=producto_id).first()
    
    if item:
        item.cantidad += cantidad
    else:
        item = CarritoItem(carrito_id=carrito.id, producto_id=producto_id, cantidad=cantidad)
        db.session.add(item)
        
    db.session.commit()
    return jsonify({'mensaje': 'Producto agregado al carrito con éxito'}), 200

# ---------------------------------------------------------
# RUTAS DE PRUEBA (ENDPOINTS)
# ---------------------------------------------------------

@app.route('/api/productos', methods=['GET'])
def obtener_productos():
    productos = Producto.query.all()
    resultado = []
    for p in productos:
        resultado.append({
            'id': p.id,
            'nombre': p.nombre,
            'descripcion': p.descripcion,
            'precio': float(p.precio),
            'stock': p.stock,
            'categoria': p.categoria.nombre if p.categoria else None
        })
    return jsonify(resultado), 200

@app.route('/api/carrito/<int:usuario_id>', methods=['GET'])
def ver_carrito(usuario_id):
    carrito = Carrito.query.filter_by(usuario_id=usuario_id).first()
    if not carrito:
        return jsonify({'mensaje': 'Carrito no encontrado'}), 404
    
    items = []
    total = 0
    for item in carrito.items:
        subtotal = float(item.producto.precio) * item.cantidad
        total += subtotal
        items.append({
            'producto_id': item.producto.id,
            'nombre': item.producto.nombre,
            'precio_unitario': float(item.producto.precio),
            'cantidad': item.cantidad,
            'subtotal': subtotal
        })
    
    return jsonify({
        'carrito_id': carrito.id,
        'usuario_id': usuario_id,
        'items': items,
        'total': total
    }), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)