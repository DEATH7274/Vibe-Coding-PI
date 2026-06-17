from flask import Blueprint, request, render_template, redirect, url_for, flash
from werkzeug.security import generate_password_hash
from app.database import SessionLocal
from app.models import User

# Создаем Blueprint (модуль) для маршрутов авторизации
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # 1. Получаем данные из HTML-формы (по атрибутам name="")
        email = request.form.get('login')
        username = request.form.get('name')
        password = request.form.get('password')

        # Чекбокс передает "on" (если галочка стоит), иначе None
        policy_accepted = request.form.get('policy_checkbox') == 'on'

        # 2. Открываем сессию для работы с базой данных
        db = SessionLocal()
        try:
            # Проверяем, нет ли уже юзера с таким email
            existing_user = db.query(User).filter(User.email == email).first()
            if existing_user:
                # flash отправляет всплывающее сообщение на фронтенд
                flash('Пользователь с таким логином уже существует!', 'error')
                return redirect(url_for('auth.register'))

            # 3. Хэшируем пароль (никогда не храним в открытом виде!)
            hashed_password = generate_password_hash(password)

            # 4. Создаем нового пользователя по нашей модели
            new_user = User(
                email=email,
                username=username,
                password_hash=hashed_password,
                policy_accepted=policy_accepted
            )

            # 5. Сохраняем в файл user-BD.db
            db.add(new_user)
            db.commit()

            flash('Регистрация прошла успешно! Теперь вы можете войти.', 'success')
            return redirect(url_for('auth.login'))

        except Exception as e:
            db.rollback()  # Если что-то пошло не так, отменяем изменения
            flash(f'Ошибка при регистрации: {e}', 'error')
            return redirect(url_for('auth.register'))
        finally:
            db.close()  # Обязательно закрываем соединение! Иначе база зависнет

    # Если метод GET (человек просто перешел по ссылке) — показываем HTML-форму
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Пока ставим заглушку для страницы входа, чтобы работал редирект
    return render_template('login.html')