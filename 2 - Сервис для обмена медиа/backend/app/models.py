from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(100), unique=True, nullable=False)  # Логин
    username = Column(String(50), nullable=False)  # Имя
    password_hash = Column(String(255), nullable=False)  # Хэш пароля
    policy_accepted = Column(Boolean, default=True)  # Чекбокс согласия
    created_at = Column(DateTime, default=datetime.utcnow)  # Дата регистрации

    # Связь: позволяет получить все файлы юзера (например, user.media_files)
    media_files = relationship("MediaFile", back_populates="author")


class MediaFile(Base):
    __tablename__ = 'media_files'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)  # Название модели
    description = Column(Text, nullable=True)  # Описание (может быть пустым)
    file_path = Column(String(255), nullable=False)  # Путь на диске (storage/...)
    file_type = Column(String(10), nullable=False)  # Расширение (.glb, .obj)
    file_size = Column(Integer, nullable=False)  # Размер в байтах
    created_at = Column(DateTime, default=datetime.utcnow)  # Дата загрузки

    # Внешний ключ: привязка к конкретному пользователю
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Обратная связь: позволяет легко получить автора файла (например, file.author.username)
    author = relationship("User", back_populates="media_files")