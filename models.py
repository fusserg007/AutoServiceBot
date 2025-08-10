from enum import Enum
from datetime import datetime
import uuid
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum as SQLEnum, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class RequestStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"

# Таблица связи для отношения многие-ко-многим между пользователями и заявками
user_requests = Table(
    'user_requests',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.telegram_id')),
    Column('request_id', String, ForeignKey('service_requests.id'))
)

class User(Base):
    __tablename__ = 'users'
    
    telegram_id = Column(Integer, primary_key=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    # Отношение с заявками
    requests = relationship("ServiceRequest", secondary=user_requests, back_populates="users")
    
    def __init__(self, telegram_id, username=None, first_name=None, last_name=None, phone=None):
        self.telegram_id = telegram_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        self.phone = phone
        self.created_at = datetime.now()
        
    def to_dict(self):
        return {
            'telegram_id': self.telegram_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'request_count': len(self.requests)
        }
        
class ServiceRequest(Base):
    __tablename__ = 'service_requests'
    
    id = Column(String, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.telegram_id'))
    car_model = Column(String, nullable=False)
    license_plate = Column(String, nullable=False)
    mileage = Column(Float, nullable=True)
    requested_work = Column(String, nullable=False)
    preferred_date = Column(String, nullable=False)
    preferred_time = Column(String, nullable=True)
    phone = Column(String, nullable=False)
    real_name = Column(String, nullable=True)
    real_surname = Column(String, nullable=True)
    status = Column(String, default=RequestStatus.PENDING.value)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    admin_notes = Column(String, nullable=True)
    
    # Отношение с пользователями
    users = relationship("User", secondary=user_requests, back_populates="requests")
    
    def __init__(self, user_id, car_model, license_plate, mileage, 
                 requested_work, preferred_date, preferred_time, phone, real_name=None, real_surname=None):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.car_model = car_model
        self.license_plate = license_plate
        self.mileage = mileage
        self.requested_work = requested_work
        self.preferred_date = preferred_date
        self.preferred_time = preferred_time
        self.phone = phone
        self.real_name = real_name
        self.real_surname = real_surname
        self.status = RequestStatus.PENDING.value
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.admin_notes = ""
        
    def approve(self, notes=""):
        self.status = RequestStatus.APPROVED.value
        self.admin_notes = notes
        self.updated_at = datetime.now()
        
    def reject(self, notes=""):
        self.status = RequestStatus.REJECTED.value
        self.admin_notes = notes
        self.updated_at = datetime.now()
    
    def complete(self, notes=""):
        self.status = RequestStatus.COMPLETED.value
        self.admin_notes = notes
        self.updated_at = datetime.now()
        
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'car_model': self.car_model,
            'license_plate': self.license_plate,
            'mileage': self.mileage,
            'requested_work': self.requested_work,
            'preferred_date': self.preferred_date,
            'preferred_time': self.preferred_time,
            'phone': self.phone,
            'real_name': self.real_name,
            'real_surname': self.real_surname, 
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'admin_notes': self.admin_notes
        }
