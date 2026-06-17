import os
import datetime
import secrets
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

app = Flask(__name__)
app.secret_key = "super-secret-key-change-in-production"
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database.db')

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        is_admin INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS files (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        original_name TEXT NOT NULL,
        uploaded_by INTEGER NOT NULL,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(uploaded_by) REFERENCES users(id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        message TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )''')
    c.execute("SELECT id FROM users WHERE username='admin'")
    if not c.fetchone():
        admin_hash = generate_password_hash("admin123")
        c.execute("INSERT INTO users (username, email, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                  ("admin", "admin@company.com", admin_hash, 1))
    conn.commit()
    conn.close()

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, is_admin):
        self.id = id
        self.username = username
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    conn = get_db()
    row = conn.execute("SELECT id, username, is_admin FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if row:
        return User(row['id'], row['username'], row['is_admin'])
    return None

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        conn = get_db()
        row = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if row and check_password_hash(row['password_hash'], password):
            user = User(row['id'], row['username'], row['is_admin'])
            login_user(user)
            return redirect(url_for('dashboard'))
        flash("Неверное имя пользователя или пароль", "error")
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm = request.form['confirm_password']
        if not username or not email or not password:
            flash("Все поля обязательны", "error")
            return render_template('register.html')
        if password != confirm:
            flash("Пароли не совпадают", "error")
            return render_template('register.html')
        if len(password) < 4:
            flash("Пароль минимум 4 символа", "error")
            return render_template('register.html')
        conn = get_db()
        existing = conn.execute("SELECT id FROM users WHERE username=? OR email=?", (username, email)).fetchone()
        if existing:
            flash("Имя пользователя или почта уже используется", "error")
            conn.close()
            return render_template('register.html')
        pw_hash = generate_password_hash(password)
        conn.execute("INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                      (username, email, pw_hash))
        conn.commit()
        conn.close()
        flash("Регистрация успешна! Войдите.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db()
    file_count = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    user_count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    msg_count = conn.execute("SELECT COUNT(*) FROM chat_messages").fetchone()[0]
    recent_files = conn.execute(
        "SELECT f.*, u.username FROM files f JOIN users u ON f.uploaded_by = u.id ORDER BY f.created_at DESC LIMIT 5"
    ).fetchall()
    conn.close()
    return render_template('dashboard.html', file_count=file_count, user_count=user_count, msg_count=msg_count, recent_files=recent_files)

@app.route('/files')
@login_required
def files_page():
    conn = get_db()
    files = conn.execute(
        "SELECT f.*, u.username FROM files f JOIN users u ON f.uploaded_by = u.id ORDER BY f.created_at DESC"
    ).fetchall()
    conn.close()
    return render_template('files.html', files=files)


@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    # Проверка наличия файла в запросе
    if 'file' not in request.files:
        flash("Файл не выбран", "error")
        return redirect(url_for('files_page'))

    file = request.files['file']

    # Проверка, что файл выбран
    if file.filename == '':
        flash("Файл не выбран", "error")
        return redirect(url_for('files_page'))

    # Проверка расширения файла
    if not allowed_file(file.filename):
        flash("Недопустимый тип файла", "error")
        return redirect(url_for('files_page'))

    try:
        # Безопасное создание имени файла
        file_ext = file.filename.rsplit('.', 1)[1].lower()
        safe_filename = f"{secrets.token_hex(8)}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.{file_ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], safe_filename)

        # Сохранение файла
        file.save(filepath)

        # Получение описания из формы
        description = request.form.get('description', '').strip()

        # Сохранение информации о файле в БД
        conn = get_db()
        conn.execute(
            "INSERT INTO files (filename, original_name, uploaded_by, description) VALUES (?, ?, ?, ?)",
            (safe_filename, file.filename, current_user.id, description)
        )
        conn.commit()
        conn.close()

        flash("Файл успешно загружен!", "success")

    except Exception as e:
        print(f"Ошибка при сохранении файла: {e}")  # Логирование ошибки
        flash("Ошибка при загрузке файла", "error")

    return redirect(url_for('files_page'))

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete_file/<int:file_id>', methods=['POST'])
@login_required
def delete_file(file_id):
    conn = get_db()
    row = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    if row:
        if current_user.is_admin or row['uploaded_by'] == current_user.id:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], row['filename'])
            if os.path.exists(filepath):
                os.remove(filepath)
            conn.execute("DELETE FROM files WHERE id=?", (file_id,))
            conn.commit()
            flash("Файл удалён", "success")
        else:
            flash("Нет прав", "error")
    conn.close()
    return redirect(url_for('files_page'))

@app.route('/chat')
@login_required
def chat_page():
    return render_template('chat.html')

@app.route('/chat/messages')
@login_required
def chat_messages():
    after_id = request.args.get('after_id', type=int)
    conn = get_db()
    if after_id:
        msgs = conn.execute(
            "SELECT cm.*, u.username FROM chat_messages cm JOIN users u ON cm.user_id = u.id WHERE cm.id > ? ORDER BY cm.created_at ASC",
            (after_id,)
        ).fetchall()
    else:
        msgs = conn.execute(
            "SELECT cm.*, u.username FROM chat_messages cm JOIN users u ON cm.user_id = u.id ORDER BY cm.created_at ASC LIMIT 100"
        ).fetchall()
    last_id = msgs[-1]['id'] if msgs else 0
    conn.close()
    messages = []
    for m in msgs:
        messages.append({
            'id': m['id'],
            'username': m['username'],
            'message': m['message'],
            'created_at': m['created_at'],
            'is_mine': m['user_id'] == current_user.id
        })
    return jsonify({'messages': messages, 'last_id': last_id})

@app.route('/chat/send', methods=['POST'])
@login_required
def send_message():
    data = request.get_json()
    message = data.get('message', '').strip()
    if message:
        conn = get_db()
        conn.execute("INSERT INTO chat_messages (user_id, message) VALUES (?, ?)",
                      (current_user.id, message))
        conn.commit()
        conn.close()
    return jsonify({'status': 'ok'})

@app.route('/admin')
@login_required
def admin_page():
    if not current_user.is_admin:
        flash("Доступ запрещён", "error")
        return redirect(url_for('dashboard'))
    conn = get_db()
    users = conn.execute("SELECT id, username, email, is_admin, created_at FROM users ORDER BY created_at DESC").fetchall()
    files = conn.execute(
        "SELECT f.*, u.username FROM files f JOIN users u ON f.uploaded_by = u.id ORDER BY f.created_at DESC"
    ).fetchall()
    conn.close()
    return render_template('admin.html', users=users, files=files)

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@login_required
def admin_delete_user(user_id):
    if not current_user.is_admin: return jsonify({'error': 'no'}), 403
    if user_id == current_user.id: return jsonify({'error': 'self'}), 400
    conn = get_db()
    conn.execute("DELETE FROM files WHERE uploaded_by=?", (user_id,))
    conn.execute("DELETE FROM chat_messages WHERE user_id=?", (user_id,))
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/admin/make_admin/<int:user_id>', methods=['POST'])
@login_required
def admin_make_admin(user_id):
    if not current_user.is_admin: return jsonify({'error': 'no'}), 403
    conn = get_db()
    conn.execute("UPDATE users SET is_admin=1 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/admin/remove_admin/<int:user_id>', methods=['POST'])
@login_required
def admin_remove_admin(user_id):
    if not current_user.is_admin: return jsonify({'error': 'no'}), 403
    if user_id == current_user.id: return jsonify({'error': 'self'}), 400
    conn = get_db()
    conn.execute("UPDATE users SET is_admin=0 WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

@app.route('/admin/delete_file/<int:file_id>', methods=['POST'])
@login_required
def admin_delete_file(file_id):
    if not current_user.is_admin: return jsonify({'error': 'no'}), 403
    conn = get_db()
    row = conn.execute("SELECT * FROM files WHERE id=?", (file_id,)).fetchone()
    if row:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], row['filename'])
        if os.path.exists(filepath): os.remove(filepath)
        conn.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()
    conn.close()
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
