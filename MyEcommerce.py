from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

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