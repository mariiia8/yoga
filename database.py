from sqlalchemy import create_engine, Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from datetime import datetime
from datetime import timedelta

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True)
    full_name = Column(String)
    phone = Column(String)
    agreed_to_offer = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    subscriptions = relationship("Subscription", back_populates="user")
    bookings = relationship("Booking", back_populates="user")

class Class(Base):
    __tablename__ = 'classes'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    description = Column(String)
    datetime = Column(DateTime)
    max_participants = Column(Integer)
    price = Column(Integer)
    subscriptions = relationship("SubscriptionType", back_populates="class_")
    bookings = relationship("Booking", back_populates="class_")

class SubscriptionType(Base):
    __tablename__ = 'subscription_types'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    class_id = Column(Integer, ForeignKey('classes.id'))
    visits_allowed = Column(Integer)
    price = Column(Integer)
    class_ = relationship("Class", back_populates="subscriptions")
    user_subscriptions = relationship("Subscription", back_populates="subscription_type")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    subscription_type_id = Column(Integer, ForeignKey('subscription_types.id'))
    visits_remaining = Column(Integer)
    purchase_date = Column(DateTime, default=datetime.now)
    user = relationship("User", back_populates="subscriptions")
    subscription_type = relationship("SubscriptionType", back_populates="user_subscriptions")

class Booking(Base):
    __tablename__ = 'bookings'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    class_id = Column(Integer, ForeignKey('classes.id'))
    datetime = Column(DateTime, default=datetime.now)
    user = relationship("User", back_populates="bookings")
    class_ = relationship("Class", back_populates="bookings")

# Создаем БД
engine = create_engine('sqlite:///yoga_studio.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()

# Временные и Тестовые данные
if not session.query(Class).count():
    # Занятия
    classes = [
        Class(
            name="Йога для начинающих",
            description="Базовые асаны для новичков. Подходит для любого уровня подготовки.",
            datetime=datetime.now() + timedelta(days=1),
            max_participants=10,
            price=800
        ),
        Class(
            name="Продвинутая йога",
            description="Сложные асаны и последовательности для опытных практиков.",
            datetime=datetime.now() + timedelta(days=2),
            max_participants=8,
            price=1000
        ),
        Class(
            name="Йога для беременных",
            description="Специальные упражнения для будущих мам.",
            datetime=datetime.now() + timedelta(days=3),
            max_participants=6,
            price=900
        )
    ]
    session.add_all(classes)
    
    # Типы абонементов
    subscription_types = [
        SubscriptionType(
            name="Абонемент на 5 занятий",
            class_id=1,
            visits_allowed=5,
            price=3500
        ),
        SubscriptionType(
            name="Абонемент на 10 занятий",
            class_id=1,
            visits_allowed=10,
            price=6000
        )
    ]
    session.add_all(subscription_types)
    
    # Пользователь (уже есть)
    user = session.query(User).filter_by(telegram_id=470064868).first()
    if not user:
        user = User(
            telegram_id=470064868,
            full_name="Новиков Дмитрий Олегович",
            phone="+79650138362",
            agreed_to_offer=True
        )
        session.add(user)
    
    session.commit()

