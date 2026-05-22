from sqlalchemy import create_engine, Column, String, Integer, Text, DateTime, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import datetime

SQLALCHEMY_DATABASE_URL = "sqlite:///./taskforge.db"

engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


class Task(Base):
    """Таблица с основными заданиями (эталонами)"""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    original_text = Column(Text, nullable=False)
    parsed_text = Column(Text, nullable=False)
    
    # Анализ структуры из llm_service
    task_structure = Column(JSON, nullable=True)
    

    difficulty_override = Column(String, nullable=True)  # "easier", "same", "harder"
    target_grade = Column(String, nullable=True)  # "5", "6", "7", "8", "9", "10", "11"
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Связь с вариантами
    variants = relationship("GeneratedVariant", back_populates="task", cascade="all, delete-orphan")


class GeneratedVariant(Base):
    """Таблица с сгенерированными вариантами заданий"""
    __tablename__ = "generated_variants"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=False)
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_number = Column(Integer, nullable=False)
    
    content = Column(Text, nullable=False)
    edited_content = Column(Text, nullable=True)
    
    difficulty_score = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.datetime.utcnow, nullable=False)
    
    # Связь с заданием
    task = relationship("Task", back_populates="variants")
    
    __table_args__ = (
        UniqueConstraint("task_id", "variant_number", name="uix_task_variant"),
    )


# Создаём таблицы
Base.metadata.create_all(bind=engine)