"""
User and schedule history models for PostgreSQL database.
"""

from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()

class User(Base):
    """User model for Auth0 integration."""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    auth0_id = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)
    picture = Column(String(500), nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to schedule history
    schedules = relationship("ScheduleHistory", back_populates="user", cascade="all, delete-orphan")

class ScheduleHistory(Base):
    """Schedule history model for storing user schedules."""
    __tablename__ = "schedule_history"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(255), nullable=True, index=True)  # Original session ID from backend
    title = Column(String(255), nullable=True)  # User-defined title for the schedule
    school = Column(String(255), nullable=False)
    major = Column(String(255), nullable=False)
    term = Column(String(10), nullable=False)
    schedule_data = Column(JSON, nullable=False)  # Full schedule data as JSON
    is_favorite = Column(Boolean, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user
    user = relationship("User", back_populates="schedules")

