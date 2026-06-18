import uuid
from pathlib import Path
from flask import Blueprint, request, render_template, jsonify, session, redirect, url_for, flash, send_from_directory
from app.database import SessionLocal
from app.models import MediaFile, User

media_bp = Blueprint('media', __name__)


# Маршрут-заглушка для кнопки "На главную"
@media_bp.route('/home')
def home():
    # 1. Защищаем главную страницу от гостей
    if 'user_id' not in session:
        flash('Пожалуйста, войдите в систему.', 'error')
        return redirect(url_for('auth.login'))

    db = SessionLocal()
    try:
        # 2. Достаем все модели из БД, сортируем по убыванию даты (новые сверху)
        # SQLAlchemy сама подтянет авторов благодаря relationship
        models = db.query(MediaFile).order_by(MediaFile.created_at.desc()).all()

        return render_template('home.html', models=models)
    finally:
        db.close()


@media_bp.route('/storage/models_3d/<path:filename>')
def serve_models(filename):
    current_dir = Path(__file__).resolve().parent
    project_root = current_dir.parent.parent.parent
    storage_path = project_root / 'storage' / 'models_3d'

    return send_from_directory(storage_path, filename)


@media_bp.route('/upload', methods=['GET', 'POST'])
def upload_model():
    # 1. ПРОВЕРКА АВТОРИЗАЦИИ
    # Если ключа 'user_id' нет в сессии, значит человек не вошел на сайт
    if 'user_id' not in session:
        flash('Для загрузки моделей необходимо войти в аккаунт.', 'error')
        # Если это фоновый POST-запрос от JavaScript, отдаем ошибку в JSON
        if request.method == 'POST':
            return jsonify({"error": "Требуется авторизация"}), 401
        # Если это обычный переход по ссылке, перекидываем на логин
        return redirect(url_for('auth.login'))

    # Получаем реальный ID текущего пользователя из сессии
    current_user_id = session['user_id']

    if request.method == 'GET':
        return render_template('upload.html')

    if request.method == 'POST':
        # Проверяем, пришел ли файл
        if 'file' not in request.files:
            return jsonify({"error": "Файл не найден"}), 400

        file = request.files['file']
        title = request.form.get('title', 'Без названия')
        description = request.form.get('description', '')

        if file.filename == '' or not file.filename.lower().endswith('.glb'):
            return jsonify({"error": "Допускаются только файлы формата .glb"}), 400

        current_dir = Path(__file__).resolve().parent
        project_root = current_dir.parent.parent.parent
        storage_path = project_root / 'storage' / 'models_3d'
        storage_path.mkdir(parents=True, exist_ok=True)

        unique_filename = f"{uuid.uuid4()}.glb"
        file_path = storage_path / unique_filename

        db = SessionLocal()
        try:
            file.save(file_path)

            # 2. ЗАПИСЬ АВТОРА В БАЗУ ДАННЫХ
            # Используем ID текущего авторизованного пользователя
            new_media = MediaFile(
                title=title,
                description=description,
                file_path=f"storage/models_3d/{unique_filename}",
                file_type="glb",
                file_size=file_path.stat().st_size,
                user_id=current_user_id  # <--- Теперь здесь реальный ID автора
            )
            db.add(new_media)
            db.commit()

            return jsonify({"message": "Файл успешно загружен!"}), 200

        except Exception as e:
            db.rollback()
            return jsonify({"error": str(e)}), 500
        finally:
            db.close()