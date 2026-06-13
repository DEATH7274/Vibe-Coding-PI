#используеться библиотека SQLAlchemy

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связь: указывает, что у юзера есть список его файлов
    media_files = relationship("MediaFile", back_populates="author")


class MediaFile(Base):
    __tablename__ = 'media_files'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=False)
    file_type = Column(String(10), nullable=False)
    file_size = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Внешний ключ на таблицу юзеров
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)

    # Связь: позволяет легко получить автора файла (file.author.username)
    author = relationship("User", back_populates="media_files")