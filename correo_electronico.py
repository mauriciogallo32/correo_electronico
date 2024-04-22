from flask import Flask, request, jsonify, render_template
from flask_mail import Mail, Message
from celery import Celery
import redis

app = Flask(__name__)

# Configuración de Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'MY_GMAIL'  # Reemplaza con tu dirección de correo
app.config['MAIL_PASSWORD'] = 'MY_KEY_GMAIL'  # Reemplaza con tu contraseña
app.config['MAIL_DEFAULT_SENDER'] = ('Mauricio', 'MY_GMAIL')  # Reemplaza con tu nombre y dirección de correo

# Configuración de Celery
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])

mail = Mail(app)

# Conexión a Redis
redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)

# Definición de tarea Celery para enviar correos electrónicos
@celery.task
def send_email(subject, recipient, message):
    try:
        msg = Message(subject, recipients=[recipient], body=message)
        message_status = mail.send(msg)
        return True
    except Exception as e:
        print("Error sending email:", str(e))
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/recetas', methods=['GET'])
def ver_recetas():
    recetas = []
    recetas_keys = redis_client.keys("receta:*")
    for key in recetas_keys:
        receta = redis_client.hgetall(key)
        recetas.append({
            'nombre': receta[b'nombre'].decode(),
            'ingredientes': receta[b'ingredientes'].decode(),
            'pasos': receta[b'pasos'].decode()
        })
    return jsonify(recetas)

@app.route('/recetas', methods=['POST'])
def agregar_receta():
    data = request.json
    nombre = data.get('nombre')
    ingredientes = data.get('ingredientes')
    pasos = data.get('pasos')

    nueva_receta = {
        'nombre': nombre,
        'ingredientes': ingredientes,
        'pasos': pasos
    }

    redis_client.hmset(f"receta:{nombre}", nueva_receta)
    return jsonify({"message": "Receta agregada con éxito."}), 201

@app.route('/recetas/<nombre>', methods=['PUT'])
def actualizar_receta(nombre):
    data = request.json
    ingredientes = data.get('ingredientes')
    pasos = data.get('pasos')

    if redis_client.exists(f"receta:{nombre}"):
        nueva_receta = {
            'nombre': nombre,
            'ingredientes': ingredientes,
            'pasos': pasos
        }
        redis_client.hmset(f"receta:{nombre}", nueva_receta)
        return jsonify({"message": "Receta actualizada con éxito."}), 200
    else:
        return jsonify({"message": "Receta no encontrada."}), 404

@app.route('/recetas/<nombre>', methods=['DELETE'])
def eliminar_receta(nombre):
    if redis_client.exists(f"receta:{nombre}"):
        redis_client.delete(f"receta:{nombre}")
        return jsonify({"message": "Receta eliminada con éxito."}), 200
    else:
        return jsonify({"message": "Receta no encontrada."}), 404

@app.route('/enviar_correo', methods=['POST'])
def enviar_correo():
    recetas = []
    recetas_keys = redis_client.keys("receta:*")
    for key in recetas_keys:
        receta = redis_client.hgetall(key)
        recetas.append({
            'nombre': receta[b'nombre'].decode(),
            'ingredientes': receta[b'ingredientes'].decode(),
            'pasos': receta[b'pasos'].decode()
        })

    message = "Recetas existentes:\n\n"
    for receta in recetas:
        message += f"Nombre: {receta['nombre']}\nIngredientes: {receta['ingredientes']}\nPasos: {receta['pasos']}\n\n"

    subject = "Recetas existentes"
    recipient = "MY_GMAIL"  # Reemplaza con tu correo electrónico real
    send_email.delay(subject, recipient, message)
    return jsonify({"message": "Correo electrónico enviado con éxito."}), 200

if __name__ == "__main__":
    app.run(debug=True)
