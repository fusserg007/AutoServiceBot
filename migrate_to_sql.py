"""
Скрипт для миграции данных из JSON файлов в SQL базу данных
"""
import json
import logging
import os
from datetime import datetime
from database import init_db, get_session, close_session, engine

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def migrate_users():
    """
    Миграция пользователей из JSON в базу данных
    """
    from models import User  # Импортируем здесь, чтобы избежать циклических импортов
    
    if not os.path.exists('users.json'):
        logger.warning("Файл users.json не найден, миграция пользователей не требуется")
        return []
        
    session = get_session()
    users = []
    
    try:
        with open('users.json', 'r', encoding='utf-8') as f:
            users_data = json.load(f)
            logger.info(f"Загружено {len(users_data)} записей пользователей из JSON")
            
            for user_data in users_data:
                # Проверяем, существует ли пользователь в базе данных
                user = session.query(User).filter_by(telegram_id=user_data['telegram_id']).first()
                
                if not user:
                    # Создаем нового пользователя
                    user = User(
                        telegram_id=user_data['telegram_id'],
                        username=user_data.get('username'),
                        first_name=user_data.get('first_name'),
                        last_name=user_data.get('last_name'),
                        phone=user_data.get('phone')
                    )
                    
                    # Преобразуем строку даты в объект datetime
                    if 'created_at' in user_data:
                        try:
                            user.created_at = datetime.fromisoformat(user_data['created_at'])
                        except (ValueError, TypeError):
                            user.created_at = datetime.now()
                    
                    session.add(user)
                    logger.info(f"Добавлен пользователь с telegram_id: {user.telegram_id}")
                    users.append(user)
                else:
                    logger.info(f"Пользователь с telegram_id: {user.telegram_id} уже существует")
                    users.append(user)
            
            session.commit()
            logger.info(f"Миграция пользователей завершена успешно, добавлено {len(users)} пользователей")
            
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при миграции пользователей: {e}")
    finally:
        close_session(session)
    
    return users

def migrate_requests():
    """
    Миграция заявок из JSON в базу данных
    """
    from models import User, ServiceRequest, RequestStatus  # Импортируем здесь, чтобы избежать циклических импортов
    
    if not os.path.exists('requests.json'):
        logger.warning("Файл requests.json не найден, миграция заявок не требуется")
        return
        
    session = get_session()
    
    try:
        with open('requests.json', 'r', encoding='utf-8') as f:
            requests_data = json.load(f)
            logger.info(f"Загружено {len(requests_data)} заявок из JSON")
            
            for req_data in requests_data:
                # Проверяем, существует ли заявка в базе данных
                request = session.query(ServiceRequest).filter_by(id=req_data['id']).first()
                
                if not request:
                    # Создаем новую заявку
                    request = ServiceRequest(
                        user_id=req_data['user_id'],
                        car_model=req_data['car_model'],
                        license_plate=req_data['license_plate'],
                        mileage=req_data['mileage'],
                        requested_work=req_data['requested_work'],
                        preferred_date=req_data['preferred_date'],
                        preferred_time=req_data.get('preferred_time', ''),
                        phone=req_data['phone'],
                        real_name=req_data.get('real_name', None),
                        real_surname=req_data.get('real_surname', None)
                    )
                    
                    # Устанавливаем ID из JSON
                    request.id = req_data['id']
                    
                    # Устанавливаем статус
                    try:
                        # Если статус уже строка, используем его напрямую
                        if isinstance(req_data['status'], str):
                            request.status = req_data['status']
                        else:
                            # Если это объект Enum, получаем его значение
                            request.status = RequestStatus(req_data['status']).value
                    except (ValueError, KeyError):
                        request.status = RequestStatus.COMPLETED.value
                    
                    # Устанавливаем примечания администратора
                    request.admin_notes = req_data.get('admin_notes', '')
                    
                    # Преобразуем строки дат в объекты datetime
                    if 'created_at' in req_data:
                        try:
                            request.created_at = datetime.fromisoformat(req_data['created_at'])
                        except (ValueError, TypeError):
                            request.created_at = datetime.now()
                    
                    if 'updated_at' in req_data:
                        try:
                            request.updated_at = datetime.fromisoformat(req_data['updated_at'])
                        except (ValueError, TypeError):
                            request.updated_at = datetime.now()
                    
                    # Добавляем заявку в базу
                    session.add(request)
                    
                    # Связываем с пользователем
                    user = session.query(User).filter_by(telegram_id=request.user_id).first()
                    if user:
                        if request not in user.requests:
                            user.requests.append(request)
                    
                    logger.info(f"Добавлена заявка с ID: {request.id}")
                else:
                    logger.info(f"Заявка с ID: {request.id} уже существует")
            
            session.commit()
            logger.info("Миграция заявок завершена успешно")
            
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при миграции заявок: {e}")
    finally:
        close_session(session)

def create_backup():
    """
    Создание резервных копий JSON файлов перед миграцией
    """
    try:
        if os.path.exists('users.json'):
            with open('users.json', 'r', encoding='utf-8') as f:
                with open('users.json.bak', 'w', encoding='utf-8') as backup:
                    backup.write(f.read())
            logger.info("Создана резервная копия users.json")
        
        if os.path.exists('requests.json'):
            with open('requests.json', 'r', encoding='utf-8') as f:
                with open('requests.json.bak', 'w', encoding='utf-8') as backup:
                    backup.write(f.read())
            logger.info("Создана резервная копия requests.json")
    except Exception as e:
        logger.error(f"Ошибка при создании резервных копий: {e}")

def main():
    """
    Основная функция миграции
    """
    logger.info("Начинаем миграцию данных из JSON в SQL")
    
    # Создаем резервные копии файлов JSON
    create_backup()
    
    # Инициализируем базу данных (создаем таблицы)
    init_db()
    
    # Мигрируем пользователей
    migrate_users()
    
    # Мигрируем заявки
    migrate_requests()
    
    logger.info("Миграция данных из JSON в SQL завершена")

if __name__ == "__main__":
    main()