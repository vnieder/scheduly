"""
Session storage abstraction layer for Scheduly backend.
Provides multiple storage backends with a unified interface.
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging
from enum import Enum

logger = logging.getLogger(__name__)

class SessionStorageType(Enum):
    """Available session storage types."""
    REDIS = "redis"
    DATABASE = "database"
    MEMORY = "memory"
    FILE = "file"  # Legacy fallback

class SessionData:
    """Session data model with validation."""
    
    def __init__(self, session_id: str, data: Dict, created_at: datetime = None, last_accessed: datetime = None):
        self.session_id = session_id
        self.data = data
        self.created_at = created_at or datetime.now()
        self.last_accessed = last_accessed or datetime.now()
    
    def is_expired(self, timeout_hours: int) -> bool:
        """Check if session is expired."""
        cutoff = datetime.now() - timedelta(hours=timeout_hours)
        return self.created_at < cutoff
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "session_id": self.session_id,
            "data": self.data,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SessionData':
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            data=data["data"],
            created_at=datetime.fromisoformat(data["created_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"])
        )

class SessionStorage(ABC):
    """Abstract base class for session storage backends."""
    
    def __init__(self, timeout_hours: int = 24):
        self.timeout_hours = timeout_hours
    
    @abstractmethod
    async def create_session(self, session_id: str, data: Dict) -> bool:
        """Create a new session."""
        pass
    
    @abstractmethod
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data by ID."""
        pass
    
    @abstractmethod
    async def update_session(self, session_id: str, data: Dict) -> bool:
        """Update existing session data."""
        pass
    
    @abstractmethod
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        pass
    
    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired sessions and return count."""
        pass
    
    @abstractmethod
    async def get_all_sessions(self) -> List[SessionData]:
        """Get all active sessions (for admin/debugging)."""
        pass
    
    @abstractmethod
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        pass
    
    def _validate_session_data(self, data: Dict) -> bool:
        """Validate session data structure."""
        required_fields = ["school", "major", "term", "preferences", "courses"]
        return all(field in data for field in required_fields)

class SessionStorageError(Exception):
    """Base exception for session storage errors."""
    pass

class SessionNotFoundError(SessionStorageError):
    """Session not found error."""
    pass

class SessionStorageConnectionError(SessionStorageError):
    """Connection error to storage backend."""
    pass

class SessionStorageValidationError(SessionStorageError):
    """Session data validation error."""
    pass
