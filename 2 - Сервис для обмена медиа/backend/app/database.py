from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Указываем имя файла нашей базы данных.
# sqlite:/// означает, что файл создастся прямо в текущей папке проекта
SQLALCHEMY_DATABASE_URL = "sqlite:///user-BD.db"

# Создаем движок подключения.
# check_same_thread=False нужно только для SQLite, чтобы Flask не ругался при множественных запросах
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

# Создаем фабрику сессий (через нее мы будем делать запросы: добавлять юзеров, искать логины)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Базовый класс, от которого мы будем наследовать все наши таблицы
Base = declarative_base()

# Вспомогательная функция, чтобы получать сессию в маршрутах (роутах) Flask
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()