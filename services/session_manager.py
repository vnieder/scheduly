"""
Session manager factory and configuration.
Handles session storage backend selection and initialization.
"""

import os
from typing import Optional
from enum import Enum
import logging

from .session_storage import SessionStorage, SessionStorageType
from .redis_session import RedisSessionStorage
from .database_session import DatabaseSessionStorage
from .memory_session import MemorySessionStorage

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages session storage backend selection and lifecycle."""
    
    def __init__(self):
        self.storage: Optional[SessionStorage] = None
        self.storage_type: Optional[SessionStorageType] = None
    
    def initialize_storage(self, 
                          storage_type: Optional[SessionStorageType] = None,
                          **kwargs) -> SessionStorage:
        """
        Initialize session storage backend.
        
        Args:
            storage_type: Storage type to use (auto-detected if None)
            **kwargs: Storage-specific configuration
        
        Returns:
            Initialized session storage instance
        """
        if storage_type is None:
            storage_type = self._detect_storage_type()
        
        self.storage_type = storage_type
        
        if storage_type == SessionStorageType.REDIS:
            try:
                self.storage = self._create_redis_storage(**kwargs)
            except Exception as e:
                logger.warning(f"Failed to initialize Redis storage, falling back to memory: {e}")
                self.storage = self._create_memory_storage(**kwargs)
                self.storage_type = SessionStorageType.MEMORY
        elif storage_type == SessionStorageType.DATABASE:
            try:
                self.storage = self._create_database_storage(**kwargs)
            except Exception as e:
                logger.warning(f"Failed to initialize Database storage, falling back to memory: {e}")
                self.storage = self._create_memory_storage(**kwargs)
                self.storage_type = SessionStorageType.MEMORY
        elif storage_type == SessionStorageType.MEMORY:
            self.storage = self._create_memory_storage(**kwargs)
        else:
            raise ValueError(f"Unsupported storage type: {storage_type}")
        
        logger.info(f"Initialized session storage: {storage_type.value}")
        return self.storage
    
    def _detect_storage_type(self) -> SessionStorageType:
        """Auto-detect preferred storage type based on environment."""
        # Check environment variables
        redis_url = os.getenv("REDIS_URL")
        database_url = os.getenv("DATABASE_URL")
        
        if redis_url:
            logger.info("Detected Redis URL, using Redis storage")
            return SessionStorageType.REDIS
        elif database_url:
            logger.info("Detected Database URL, using Database storage")
            return SessionStorageType.DATABASE
        else:
            # Default to Redis for development
            logger.warning("No storage URL detected, defaulting to Redis")
            return SessionStorageType.REDIS
    
    def _create_redis_storage(self, **kwargs) -> RedisSessionStorage:
        """Create Redis storage instance."""
        redis_url = os.getenv("REDIS_URL")
        
        if redis_url:
            # Parse Redis URL (redis://user:password@host:port/db)
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            
            config = {
                "host": parsed.hostname or "localhost",
                "port": parsed.port or 6379,
                "db": int(parsed.path.lstrip("/")) if parsed.path else 0,
                "password": parsed.password,
                "timeout_hours": int(os.getenv("SESSION_TIMEOUT_HOURS", "24")),
                **kwargs
            }
        else:
            config = {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", "6379")),
                "db": int(os.getenv("REDIS_DB", "0")),
                "password": os.getenv("REDIS_PASSWORD"),
                "timeout_hours": int(os.getenv("SESSION_TIMEOUT_HOURS", "24")),
                **kwargs
            }
        
        return RedisSessionStorage(**config)
    
    def _create_database_storage(self, **kwargs) -> DatabaseSessionStorage:
        """Create Database storage instance."""
        database_url = os.getenv("DATABASE_URL")
        
        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required for database storage")
        
        config = {
            "database_url": database_url,
            "timeout_hours": int(os.getenv("SESSION_TIMEOUT_HOURS", "24")),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "10")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "20")),
            **kwargs
        }
        
        return DatabaseSessionStorage(**config)
    
    def _create_memory_storage(self, **kwargs) -> MemorySessionStorage:
        """Create Memory storage instance."""
        config = {
            "timeout_hours": int(os.getenv("SESSION_TIMEOUT_HOURS", "24")),
            **kwargs
        }
        
        return MemorySessionStorage(**config)
    
    async def get_storage(self) -> SessionStorage:
        """Get initialized storage instance."""
        if self.storage is None:
            self.initialize_storage()
        return self.storage
    
    async def close(self):
        """Close storage connections."""
        if self.storage:
            await self.storage.close()
            self.storage = None
            logger.info("Session storage connections closed")

# Global session manager instance
session_manager = SessionManager()

async def get_session_storage() -> SessionStorage:
    """Get the global session storage instance."""
    return await session_manager.get_storage()

async def close_session_storage():
    """Close the global session storage connections."""
    await session_manager.close()
