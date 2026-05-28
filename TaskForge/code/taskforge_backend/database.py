from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./taskforge.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    tasks = relationship("Task", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")


class UserSession(Base):
    __tablename__ = "user_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, index=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="sessions")


class Task(Base):
    """Таблица с основными заданиями (эталонами)"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    original_text = Column(Text, nullable=False)
    parsed_text = Column(Text, nullable=False)
    
    task_structure = Column(JSON, nullable=True)
    
    difficulty_override = Column(String, nullable=True)
    target_grade = Column(String, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    user = relationship("User", back_populates="tasks")
    variants = relationship("GeneratedVariant", back_populates="task", cascade="all, delete-orphan")


class GeneratedVariant(Base):
    """Таблица с сгенерированными вариантами заданий"""
    __tablename__ = "generated_variants"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_number = Column(Integer, nullable=False)
    
    content = Column(Text, nullable=False)
    edited_content = Column(Text, nullable=True)
    
    difficulty_score = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    task = relationship("Task", back_populates="variants")
    user = relationship("User")
    
    __table_args__ = (
        UniqueConstraint("task_id", "variant_number", name="uix_task_variant"),
    )

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


Base.metadata.create_all(bind=engine)
