"""
Модуль для конфигурации базы данных и управления сессиями SQLAlchemy
"""
import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.ext.declarative import declarative_base

# Определим путь к базе данных SQLite
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///autoservice.db')

# Создаем движок базы данных
engine = create_engine(DATABASE_URL, echo=True)

# Создаем фабрику сессий
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)

def init_db():
    """
    Инициализация базы данных: создание всех таблиц
    """
    from models import Base  # Импортируем здесь, чтобы избежать циклических импортов
    
    logging.info(f"Инициализация базы данных по адресу: {DATABASE_URL}")
    Base.metadata.create_all(engine)
    logging.info("База данных инициализирована успешно")

def get_session():
    """
    Получение сессии базы данных
    """
    return Session()

def close_session(session):
    """
    Закрытие сессии базы данных
    """
    session.close()

# Функция для миграции данных из JSON файлов в SQL базу данных
def migrate_from_json(json_data_store):
    """
    Миграция данных из JSON в базу данных SQL
    
    Args:
        json_data_store: Экземпляр класса DataStore с данными из JSON файлов
    """
    from models import User, ServiceRequest  # Импортируем здесь, чтобы избежать циклических импортов
    
    logging.info("Начинаем миграцию данных из JSON в базу данных SQL")
    
    session = get_session()
    try:
        # Получаем всех пользователей из JSON
        users = json_data_store.get_all_users()
        logging.info(f"Найдено {len(users)} пользователей для миграции")
        
        # Добавляем пользователей в базу данных
        for user in users:
            # Проверяем, существует ли пользователь в базе данных
            db_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
            if not db_user:
                # Если пользователя нет, добавляем его
                session.add(user)
                logging.info(f"Добавлен пользователь {user.telegram_id}")
        
        # Получаем все заявки из JSON
        requests = json_data_store.get_all_requests()
        logging.info(f"Найдено {len(requests)} заявок для миграции")
        
        # Добавляем заявки в базу данных
        for req in requests:
            # Проверяем, существует ли заявка в базе данных
            db_request = session.query(ServiceRequest).filter_by(id=req.id).first()
            if not db_request:
                # Если заявки нет, добавляем её
                session.add(req)
                
                # Добавляем связь с пользователем
                user = session.query(User).filter_by(telegram_id=req.user_id).first()
                if user:
                    if req not in user.requests:
                        user.requests.append(req)
                
                logging.info(f"Добавлена заявка {req.id}")
        
        # Сохраняем изменения
        session.commit()
        logging.info("Миграция данных завершена успешно")
    except Exception as e:
        session.rollback()
        logging.error(f"Ошибка при миграции данных: {e}")
    finally:
        close_session(session) 