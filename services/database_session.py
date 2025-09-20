"""
Database-based session storage implementation.
Provides persistent, ACID-compliant session storage.
"""

import json
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

try:
    import sqlalchemy as sa
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker, declarative_base
    from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    sa = None
    create_async_engine = None
    AsyncSession = None
    sessionmaker = None
    declarative_base = None

from .session_storage import SessionStorage, SessionData, SessionStorageError

logger = logging.getLogger(__name__)

# Database models
Base = declarative_base() if DATABASE_AVAILABLE else None

class SessionModel(Base):
    """SQLAlchemy model for sessions table."""
    __tablename__ = "sessions"
    
    session_id = Column(String(255), primary_key=True)
    data = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    last_accessed = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)

class DatabaseSessionStorage(SessionStorage):
    """Database-based session storage with async support."""
    
    def __init__(self, 
                 database_url: str,
                 timeout_hours: int = 24,
                 pool_size: int = 10,
                 max_overflow: int = 20):
        
        if not DATABASE_AVAILABLE:
            raise ImportError("sqlalchemy package not available. Install with: pip install sqlalchemy[asyncio]")
        
        super().__init__(timeout_hours)
        self.database_url = database_url
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        
        self.engine = None
        self.session_factory = None
    
    async def _get_session_factory(self):
        """Get database session factory."""
        if self.session_factory is None:
            self.engine = create_async_engine(
                self.database_url,
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                echo=False  # Set to True for SQL debugging
            )
            
            self.session_factory = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info(f"Connected to database: {self.database_url}")
        
        return self.session_factory
    
    async def create_session(self, session_id: str, data: Dict) -> bool:
        """Create a new session in database."""
        try:
            if not self._validate_session_data(data):
                raise SessionStorageError("Invalid session data structure")
            
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                expires_at = datetime.utcnow() + timedelta(hours=self.timeout_hours)
                
                session_record = SessionModel(
                    session_id=session_id,
                    data=json.dumps(data),
                    created_at=datetime.utcnow(),
                    last_accessed=datetime.utcnow(),
                    expires_at=expires_at,
                    is_active=True
                )
                
                session.add(session_record)
                await session.commit()
                
                logger.info(f"Created session {session_id} in database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data from database."""
        try:
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    sa.select(SessionModel)
                    .where(SessionModel.session_id == session_id)
                    .where(SessionModel.is_active == True)
                    .where(SessionModel.expires_at > datetime.utcnow())
                )
                
                session_record = result.scalar_one_or_none()
                if session_record is None:
                    return None
                
                # Update last accessed time
                session_record.last_accessed = datetime.utcnow()
                await session.commit()
                
                # Convert to SessionData
                data = json.loads(session_record.data)
                return SessionData(
                    session_id=session_record.session_id,
                    data=data,
                    created_at=session_record.created_at,
                    last_accessed=session_record.last_accessed
                )
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in session {session_id}: {e}")
            await self.delete_session(session_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, data: Dict) -> bool:
        """Update existing session data in database."""
        try:
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    sa.select(SessionModel)
                    .where(SessionModel.session_id == session_id)
                    .where(SessionModel.is_active == True)
                )
                
                session_record = result.scalar_one_or_none()
                if session_record is None:
                    return False
                
                # Update data and last accessed time
                session_record.data = json.dumps(data)
                session_record.last_accessed = datetime.utcnow()
                
                await session.commit()
                
                logger.info(f"Updated session {session_id} in database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from database (soft delete)."""
        try:
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    sa.select(SessionModel)
                    .where(SessionModel.session_id == session_id)
                    .where(SessionModel.is_active == True)
                )
                
                session_record = result.scalar_one_or_none()
                if session_record is None:
                    return False
                
                # Soft delete
                session_record.is_active = False
                await session.commit()
                
                logger.info(f"Deleted session {session_id} from database")
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """Remove expired sessions from database."""
        try:
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                # Soft delete expired sessions
                result = await session.execute(
                    sa.update(SessionModel)
                    .where(SessionModel.expires_at < datetime.utcnow())
                    .where(SessionModel.is_active == True)
                    .values(is_active=False)
                )
                
                await session.commit()
                expired_count = result.rowcount
                
                if expired_count > 0:
                    logger.info(f"Cleaned up {expired_count} expired sessions from database")
                
                return expired_count
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_all_sessions(self) -> List[SessionData]:
        """Get all active sessions (for admin/debugging)."""
        try:
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    sa.select(SessionModel)
                    .where(SessionModel.is_active == True)
                    .where(SessionModel.expires_at > datetime.utcnow())
                )
                
                sessions = []
                for session_record in result.scalars():
                    try:
                        data = json.loads(session_record.data)
                        sessions.append(SessionData(
                            session_id=session_record.session_id,
                            data=data,
                            created_at=session_record.created_at,
                            last_accessed=session_record.last_accessed
                        ))
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping corrupted session data for: {session_record.session_id}")
                
                return sessions
                
        except Exception as e:
            logger.error(f"Failed to get all sessions: {e}")
            return []
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists in database."""
        try:
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    sa.select(SessionModel.session_id)
                    .where(SessionModel.session_id == session_id)
                    .where(SessionModel.is_active == True)
                    .where(SessionModel.expires_at > datetime.utcnow())
                )
                
                return result.scalar_one_or_none() is not None
                
        except Exception as e:
            logger.error(f"Failed to check session existence {session_id}: {e}")
            return False
    
    async def get_session_count(self) -> int:
        """Get total number of active sessions."""
        try:
            session_factory = await self._get_session_factory()
            async with session_factory() as session:
                result = await session.execute(
                    sa.select(sa.func.count(SessionModel.session_id))
                    .where(SessionModel.is_active == True)
                    .where(SessionModel.expires_at > datetime.utcnow())
                )
                
                return result.scalar() or 0
                
        except Exception as e:
            logger.error(f"Failed to get session count: {e}")
            return 0
    
    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
        self.session_factory = None
        logger.info("Database connection closed")
