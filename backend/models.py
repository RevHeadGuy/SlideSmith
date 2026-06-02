"""Database models for SlideSmith presentations"""

from sqlalchemy import Column, Integer, String,ForeignKey, DateTime, JSON, Text, Enum as SQLEnum
from sqlalchemy.sql import func
from datetime import datetime
from db import Base
import enum

class PresentationStatus(str, enum.Enum):
    """Enum for presentation generation status"""
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    VALIDATED = "validated"

class Presentation(Base):
    """Presentation metadata and file tracking"""
    __tablename__ = "presentations"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(500), nullable=False)
    slide_count = Column(Integer, default=5)
    theme = Column(String(50), default="modern")
    language = Column(String(50), default="english")
    status = Column(SQLEnum(PresentationStatus), default=PresentationStatus.PROCESSING)
    pptx_path = Column(String(500), nullable=True)
    pdf_path = Column(String(500), nullable=True)
    file_type = Column(String(10), nullable=True)  # 'pdf', 'pptx', or None for topic-based
    
    user_id = Column(
    Integer,
    ForeignKey("users.id")
    )

    # Content storage
    content_json = Column(JSON, nullable=True)  # Raw outline from LLM
    slides_json = Column(JSON, nullable=True)  # Structured slides
    
    # Status tracking
    error = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Presentation(id={self.id}, topic='{self.topic}', status={self.status})>"
    
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)

    email = Column(String, unique=True, nullable=False)

    hashed_password = Column(String, nullable=False)