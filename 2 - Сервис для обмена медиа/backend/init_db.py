from app.database import engine, Base
# Обязательно импортируем models, чтобы SQLAlchemy "увидела" классы перед созданием
from app import models

def init():
    print("Инициализация базы данных...")
    # Эта магическая команда ищет все классы, унаследованные от Base (наши User и MediaFile),
    # и создает для них таблицы в файле user-BD.db
    Base.metadata.create_all(bind=engine)
    print("Файл user-BD.db успешно создан, таблицы готовы!")

if __name__ == "__main__":
    init()