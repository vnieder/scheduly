"""
User schedule storage service for PostgreSQL.
"""

import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.models.user_models import User, ScheduleHistory
import logging

logger = logging.getLogger(__name__)

class UserScheduleStorage:
    """Service for managing user schedules in PostgreSQL."""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    
    def get_db_session(self) -> Session:
        """Get database session."""
        return self.SessionLocal()
    
    def get_or_create_user(self, auth0_id: str, email: str, name: str = None, picture: str = None) -> User:
        """Get existing user or create new one."""
        db = self.get_db_session()
        try:
            # Try to find existing user
            user = db.query(User).filter(User.auth0_id == auth0_id).first()
            
            if user:
                # Update user info if needed
                if email != user.email or name != user.name or picture != user.picture:
                    user.email = email
                    user.name = name
                    user.picture = picture
                    user.updated_at = datetime.utcnow()
                    db.commit()
                return user
            
            # Create new user
            user = User(
                auth0_id=auth0_id,
                email=email,
                name=name,
                picture=picture
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            return user
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error getting/creating user: {e}")
            raise
        finally:
            db.close()
    
    def save_schedule(self, 
                     auth0_id: str, 
                     session_id: str, 
                     school: str, 
                     major: str, 
                     term: str, 
                     schedule_data: Dict[str, Any],
                     title: str = None) -> ScheduleHistory:
        """Save a schedule for a user."""
        db = self.get_db_session()
        try:
            # Get or create user
            user = self.get_or_create_user(auth0_id, "", "")
            
            # Create schedule history entry
            schedule = ScheduleHistory(
                user_id=user.id,
                session_id=session_id,
                title=title or f"{school} {major} - {term}",
                school=school,
                major=major,
                term=term,
                schedule_data=schedule_data
            )
            
            db.add(schedule)
            db.commit()
            db.refresh(schedule)
            
            logger.info(f"Saved schedule {schedule.id} for user {auth0_id}")
            return schedule
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error saving schedule: {e}")
            raise
        finally:
            db.close()
    
    def get_user_schedules(self, auth0_id: str, limit: int = 50, offset: int = 0) -> List[ScheduleHistory]:
        """Get all schedules for a user."""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.auth0_id == auth0_id).first()
            if not user:
                return []
            
            schedules = db.query(ScheduleHistory)\
                .filter(ScheduleHistory.user_id == user.id)\
                .order_by(ScheduleHistory.created_at.desc())\
                .offset(offset)\
                .limit(limit)\
                .all()
            
            return schedules
            
        except Exception as e:
            logger.error(f"Error getting user schedules: {e}")
            raise
        finally:
            db.close()
    
    def get_schedule_by_id(self, auth0_id: str, schedule_id: str) -> Optional[ScheduleHistory]:
        """Get a specific schedule by ID."""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.auth0_id == auth0_id).first()
            if not user:
                return None
            
            schedule = db.query(ScheduleHistory)\
                .filter(ScheduleHistory.id == schedule_id)\
                .filter(ScheduleHistory.user_id == user.id)\
                .first()
            
            return schedule
            
        except Exception as e:
            logger.error(f"Error getting schedule by ID: {e}")
            raise
        finally:
            db.close()
    
    def delete_schedule(self, auth0_id: str, schedule_id: str) -> bool:
        """Delete a schedule."""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.auth0_id == auth0_id).first()
            if not user:
                return False
            
            schedule = db.query(ScheduleHistory)\
                .filter(ScheduleHistory.id == schedule_id)\
                .filter(ScheduleHistory.user_id == user.id)\
                .first()
            
            if not schedule:
                return False
            
            db.delete(schedule)
            db.commit()
            
            logger.info(f"Deleted schedule {schedule_id} for user {auth0_id}")
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting schedule: {e}")
            raise
        finally:
            db.close()
    
    def update_schedule_title(self, auth0_id: str, schedule_id: str, title: str) -> bool:
        """Update schedule title."""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.auth0_id == auth0_id).first()
            if not user:
                return False
            
            schedule = db.query(ScheduleHistory)\
                .filter(ScheduleHistory.id == schedule_id)\
                .filter(ScheduleHistory.user_id == user.id)\
                .first()
            
            if not schedule:
                return False
            
            schedule.title = title
            schedule.updated_at = datetime.utcnow()
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error updating schedule title: {e}")
            raise
        finally:
            db.close()
    
    def toggle_favorite(self, auth0_id: str, schedule_id: str) -> bool:
        """Toggle favorite status of a schedule."""
        db = self.get_db_session()
        try:
            user = db.query(User).filter(User.auth0_id == auth0_id).first()
            if not user:
                return False
            
            schedule = db.query(ScheduleHistory)\
                .filter(ScheduleHistory.id == schedule_id)\
                .filter(ScheduleHistory.user_id == user.id)\
                .first()
            
            if not schedule:
                return False
            
            schedule.is_favorite = not schedule.is_favorite
            schedule.updated_at = datetime.utcnow()
            db.commit()
            
            return True
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error toggling favorite: {e}")
            raise
        finally:
            db.close()

