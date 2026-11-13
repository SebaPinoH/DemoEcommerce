from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Configuración de conexión MySQL
USER = 'root'
PASSWORD = 'tu_contraseña_real'  # <-- Reemplaza por tu contraseña real
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

class Carrito(db.Model):
    __tablename__ = 'carritos'
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False, unique=True)

# ---------------------------------------------------------
# RUTA DE INTERFAZ HTML
# ---------------------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

# ---------------------------------------------------------
# ENDPOINTS API (LOGIN, CREACIÓN Y BORRADO DE USUARIOS)
# ---------------------------------------------------------
@app.route('/api/usuarios', methods=['GET'])
def listar_usuarios():
    usuarios = Usuario.query.all()
    return jsonify([
        {'id': u.id, 'nombre': u.nombre, 'email': u.email}
        for u in usuarios
    ]), 200

@app.route('/api/registro', methods=['POST'])
def registrar_usuario():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('nombre'):
        return jsonify({'error': 'Todos los campos son obligatorios'}), 400

    if Usuario.query.filter_by(email=data['email']).first():
        return jsonify({'error': 'El correo ya está registrado'}), 400

    hashed_pwd = generate_password_hash(data['password'], method='pbkdf2:sha256')
    nuevo_usuario = Usuario(
        nombre=data['nombre'],
        email=data['email'],
        password=hashed_pwd
    )
    db.session.add(nuevo_usuario)
    db.session.commit()

    # Crear carrito vinculado
    nuevo_carrito = Carrito(usuario_id=nuevo_usuario.id)
    db.session.add(nuevo_carrito)
    db.session.commit()

    return jsonify({'mensaje': 'Usuario creado con éxito', 'id': nuevo_usuario.id}), 201

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    usuario = Usuario.query.filter_by(email=data.get('email')).first()

    if not usuario or not check_password_hash(usuario.password, data.get('password', '')):
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

if __name__ == '__main__':
    app.run(debug=True, port=5000)