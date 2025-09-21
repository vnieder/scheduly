"""
Memory-based session storage implementation.
Provides in-memory session storage as a fallback when Redis/Database are not available.
"""

import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

from .session_storage import SessionStorage, SessionData

logger = logging.getLogger(__name__)

class MemorySessionStorage(SessionStorage):
    """In-memory session storage implementation."""
    
    def __init__(self, timeout_hours: int = 24):
        super().__init__(timeout_hours)
        self._sessions: Dict[str, SessionData] = {}
        self._lock = asyncio.Lock()
        logger.info("Initialized memory session storage")
    
    async def create_session(self, session_id: str, data: Dict) -> bool:
        """Create a new session in memory."""
        try:
            if not self._validate_session_data(data):
                raise SessionStorageError("Invalid session data structure")
            
            async with self._lock:
                session_data = SessionData(session_id, data)
                self._sessions[session_id] = session_data
                logger.info(f"Created session {session_id} in memory")
                return True
                
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data from memory."""
        try:
            async with self._lock:
                session_data = self._sessions.get(session_id)
                if session_data is None:
                    return None
                
                # Check if expired
                if session_data.is_expired(self.timeout_hours):
                    del self._sessions[session_id]
                    logger.info(f"Session {session_id} expired and removed")
                    return None
                
                # Update last accessed time
                session_data.last_accessed = datetime.now()
                logger.debug(f"Retrieved session {session_id} from memory")
                return session_data
                
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, data: Dict) -> bool:
        """Update existing session data in memory."""
        try:
            if not self._validate_session_data(data):
                raise SessionStorageError("Invalid session data structure")
            
            async with self._lock:
                if session_id not in self._sessions:
                    logger.warning(f"Session {session_id} not found for update")
                    return False
                
                session_data = self._sessions[session_id]
                session_data.data = data
                session_data.last_accessed = datetime.now()
                logger.info(f"Updated session {session_id} in memory")
                return True
                
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete a session from memory."""
        try:
            async with self._lock:
                if session_id in self._sessions:
                    del self._sessions[session_id]
                    logger.info(f"Deleted session {session_id} from memory")
                    return True
                else:
                    logger.warning(f"Session {session_id} not found for deletion")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """Remove expired sessions and return count."""
        try:
            async with self._lock:
                expired_sessions = []
                for session_id, session_data in self._sessions.items():
                    if session_data.is_expired(self.timeout_hours):
                        expired_sessions.append(session_id)
                
                for session_id in expired_sessions:
                    del self._sessions[session_id]
                
                if expired_sessions:
                    logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
                
                return len(expired_sessions)
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_all_sessions(self) -> List[SessionData]:
        """Get all active sessions."""
        try:
            async with self._lock:
                active_sessions = []
                for session_data in self._sessions.values():
                    if not session_data.is_expired(self.timeout_hours):
                        active_sessions.append(session_data)
                
                logger.debug(f"Retrieved {len(active_sessions)} active sessions")
                return active_sessions
                
        except Exception as e:
            logger.error(f"Failed to get all sessions: {e}")
            return []
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists."""
        try:
            async with self._lock:
                if session_id not in self._sessions:
                    return False
                
                session_data = self._sessions[session_id]
                if session_data.is_expired(self.timeout_hours):
                    del self._sessions[session_id]
                    return False
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to check session existence {session_id}: {e}")
            return False
    
    async def close(self):
        """Close memory storage (no-op for memory storage)."""
        async with self._lock:
            self._sessions.clear()
            logger.info("Memory session storage closed and cleared")
