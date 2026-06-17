from flask import Flask
from app.routes.auth import auth_bp

# Создаем само приложение. Указываем Flask'у, где лежат наши HTML-шаблоны
app = Flask(__name__, template_folder='../frontend/templates')

# Секретный ключ нужен для работы flash-сообщений и будущих сессий пользователя
app.secret_key = 'super-secret-key-for-pi-project'

# Подключаем модуль авторизации
app.register_blueprint(auth_bp)

if __name__ == '__main__':
    # Запускаем сервер в режиме отладки (будет сам перезагружаться при изменении кода)
    app.run(debug=True)