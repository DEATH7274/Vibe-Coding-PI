from flask import Flask
from app.routes.auth import auth_bp
from app.routes.media import media_bp # <--- Добавили импорт

app = Flask(__name__, template_folder='../frontend/templates')
app.secret_key = 'super-secret-key-for-pi-project'

app.register_blueprint(auth_bp)
app.register_blueprint(media_bp) # <--- Зарегистрировали модуль загрузки

if __name__ == '__main__':
    app.run(debug=True)