import json
import logging
import os
from datetime import datetime
import copy
from models import User, ServiceRequest, RequestStatus
from database import get_session, close_session, Session

class DataStore:
    """
    Хранилище данных на базе SQL с использованием SQLAlchemy
    """
    
    def __init__(self):
        """Инициализация хранилища данных"""
        logging.info("Инициализация хранилища данных SQL")
        
        # Флаг миграции (будет использоваться при первом запуске)
        self.migrated = False
    
    def get_user(self, telegram_id):
        """
        Получение пользователя по его Telegram ID
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            User: объект пользователя или None, если не найден
        """
        session = get_session()
        try:
            return session.query(User).filter_by(telegram_id=telegram_id).first()
        except Exception as e:
            logging.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
            return None
        finally:
            close_session(session)
    
    def add_user(self, user):
        """
        Добавление нового пользователя
        
        Args:
            user: объект пользователя User
            
        Returns:
            User: добавленный пользователь
        """
        session = get_session()
        try:
            # Проверяем, существует ли пользователь
            existing_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
            if existing_user:
                return existing_user
                
            # Добавляем нового пользователя
            session.add(user)
            session.commit()
            logging.info(f"Добавлен новый пользователь {user.telegram_id}")
            return user
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при добавлении пользователя: {e}")
            return None
        finally:
            close_session(session)
    
    def update_user(self, user):
        """
        Обновление существующего пользователя
        
        Args:
            user: объект пользователя User с обновленными данными
            
        Returns:
            bool: True, если обновление прошло успешно
        """
        session = get_session()
        try:
            existing_user = session.query(User).filter_by(telegram_id=user.telegram_id).first()
            if not existing_user:
                return False
                
            # Обновляем данные пользователя
            existing_user.username = user.username
            existing_user.first_name = user.first_name
            existing_user.last_name = user.last_name
            existing_user.phone = user.phone
            
            session.commit()
            logging.info(f"Обновлен пользователь {user.telegram_id}")
            return True
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при обновлении пользователя: {e}")
            return False
        finally:
            close_session(session)
    
    def get_all_users(self):
        """
        Получение всех зарегистрированных пользователей
        
        Returns:
            list: список всех пользователей
        """
        session = get_session()
        try:
            users = session.query(User).all()
            # Создаем копии объектов, чтобы избежать проблем с закрытой сессией
            return [copy.copy(user) for user in users]
        except Exception as e:
            logging.error(f"Ошибка при получении списка пользователей: {e}")
            return []
        finally:
            close_session(session)
    
    def add_request(self, request):
        """
        Добавление новой заявки
        
        Args:
            request: объект заявки ServiceRequest
            
        Returns:
            ServiceRequest: добавленная заявка
        """
        session = get_session()
        try:
            # Проверяем, существует ли заявка
            existing_request = session.query(ServiceRequest).filter_by(id=request.id).first()
            if existing_request:
                return existing_request
                
            # Проверяем, существует ли пользователь
            user = session.query(User).filter_by(telegram_id=request.user_id).first()
            if not user:
                logging.error(f"Не найден пользователь {request.user_id} для добавления заявки")
                return None
                
            # Добавляем новую заявку
            session.add(request)
            
            # Добавляем связь с пользователем
            if request not in user.requests:
                user.requests.append(request)
                
            session.commit()
            logging.info(f"Добавлена новая заявка {request.id}")
            return request
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при добавлении заявки: {e}")
            return None
        finally:
            close_session(session)
    
    def get_request(self, request_id):
        """
        Получение заявки по её ID
        
        Args:
            request_id: ID заявки
            
        Returns:
            ServiceRequest: объект заявки или None, если не найдена
        """
        session = get_session()
        try:
            return session.query(ServiceRequest).filter_by(id=request_id).first()
        except Exception as e:
            logging.error(f"Ошибка при получении заявки {request_id}: {e}")
            return None
        finally:
            close_session(session)
    
    def update_request(self, request):
        """
        Обновление существующей заявки
        
        Args:
            request: объект заявки ServiceRequest с обновленными данными
            
        Returns:
            bool: True, если обновление прошло успешно
        """
        session = get_session()
        try:
            existing_request = session.query(ServiceRequest).filter_by(id=request.id).first()
            if not existing_request:
                return False
                
            # Обновляем данные заявки
            existing_request.car_model = request.car_model
            existing_request.license_plate = request.license_plate
            existing_request.mileage = request.mileage
            existing_request.requested_work = request.requested_work
            existing_request.preferred_date = request.preferred_date
            existing_request.preferred_time = request.preferred_time
            existing_request.phone = request.phone
            existing_request.real_name = request.real_name
            existing_request.real_surname = request.real_surname
            existing_request.status = request.status
            existing_request.admin_notes = request.admin_notes
            existing_request.updated_at = datetime.now()
            
            session.commit()
            logging.info(f"Обновлена заявка {request.id}")
            return True
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при обновлении заявки: {e}")
            return False
        finally:
            close_session(session)
        
    def delete_request(self, request_id):
        """
        Полное удаление заявки
        
        Args:
            request_id: ID заявки для удаления
            
        Returns:
            bool: True, если удаление прошло успешно
        """
        session = get_session()
        try:
            request = session.query(ServiceRequest).filter_by(id=request_id).first()
            if not request:
                return False
                
            # Удаляем заявку
            session.delete(request)
            session.commit()
            logging.info(f"Удалена заявка {request_id}")
            return True
        except Exception as e:
            session.rollback()
            logging.error(f"Ошибка при удалении заявки: {e}")
            return False
        finally:
            close_session(session)
    
    def get_user_requests(self, telegram_id):
        """
        Получение всех заявок для конкретного пользователя
        
        Args:
            telegram_id: ID пользователя в Telegram
            
        Returns:
            list: список заявок пользователя
        """
        session = get_session()
        try:
            return session.query(ServiceRequest).filter_by(user_id=telegram_id).all()
        except Exception as e:
            logging.error(f"Ошибка при получении заявок пользователя {telegram_id}: {e}")
            return []
        finally:
            close_session(session)
    
    def get_all_requests(self):
        """
        Получение всех заявок
        
        Returns:
            list: список всех заявок
        """
        session = get_session()
        try:
            requests = session.query(ServiceRequest).all()
            # Создаем копии объектов, чтобы избежать проблем с закрытой сессией
            return [copy.copy(req) for req in requests]
        except Exception as e:
            logging.error(f"Ошибка при получении списка всех заявок: {e}")
            return []
        finally:
            close_session(session)
    
    def get_requests_by_status(self, status):
        """
        Получение всех заявок с определенным статусом
        
        Args:
            status: статус заявки (RequestStatus)
            
        Returns:
            list: список заявок с указанным статусом
        """
        session = get_session()
        try:
            return session.query(ServiceRequest).filter_by(status=status).all()
        except Exception as e:
            logging.error(f"Ошибка при получении заявок со статусом {status}: {e}")
            return []
        finally:
            close_session(session)

# Глобальный экземпляр хранилища данных
data_store = DataStore()
