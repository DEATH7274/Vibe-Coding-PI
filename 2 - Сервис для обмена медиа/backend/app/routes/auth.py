from flask import Blueprint, request, render_template, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
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
    if request.method == 'POST':
        email = request.form.get('login')
        password = request.form.get('password')

        db = SessionLocal()
        try:
            # Ищем пользователя в базе по логину (email)
            user = db.query(User).filter(User.email == email).first()

            # Если пользователь найден И введенный пароль совпадает с хэшем в БД
            if user and check_password_hash(user.password_hash, password):
                # МАГИЯ АВТОРИЗАЦИИ: Записываем ID и имя в безопасную сессию
                session['user_id'] = user.id
                session['username'] = user.username

                flash(f'Добро пожаловать, {user.username}!', 'success')
                # Перенаправляем авторизованного пользователя на страницу загрузки моделей
                return redirect(url_for('media.home'))
            else:
                flash('Неверный логин или пароль', 'error')
                return redirect(url_for('auth.login'))
        finally:
            db.close()

    # Если метод GET — просто отдаем HTML-страницу входа
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    # Очищаем все данные из сессии пользователя
    session.clear()
    flash('Вы успешно вышли из системы.', 'success')
    # Перенаправляем обратно на страницу логина
    return redirect(url_for('auth.login'))