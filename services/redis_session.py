"""
Redis-based session storage implementation.
Provides high-performance, distributed session storage.
"""

import json
import asyncio
from typing import Dict, Optional, List
from datetime import datetime, timedelta
import logging

try:
    import redis.asyncio as redis
    from redis.asyncio import ConnectionPool
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None
    ConnectionPool = None

from .session_storage import SessionStorage, SessionData, SessionStorageError

logger = logging.getLogger(__name__)

class RedisSessionStorage(SessionStorage):
    """Redis-based session storage with async support."""
    
    def __init__(self, 
                 host: str = "localhost", 
                 port: int = 6379, 
                 db: int = 0,
                 password: Optional[str] = None,
                 timeout_hours: int = 24,
                 key_prefix: str = "scheduly:session:",
                 max_connections: int = 20):
        
        if not REDIS_AVAILABLE:
            raise ImportError("redis package not available. Install with: pip install redis[hiredis]")
        
        super().__init__(timeout_hours)
        self.host = host
        self.port = port
        self.db = db
        self.password = password
        self.key_prefix = key_prefix
        self.max_connections = max_connections
        
        # Connection pool for better performance
        self.pool = None
        self._client = None
    
    async def _get_client(self) -> redis.Redis:
        """Get Redis client with connection pooling."""
        if self._client is None:
            if self.pool is None:
                self.pool = ConnectionPool(
                    host=self.host,
                    port=self.port,
                    db=self.db,
                    password=self.password,
                    max_connections=self.max_connections,
                    decode_responses=True
                )
            
            self._client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            try:
                await self._client.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise SessionStorageError(f"Redis connection failed: {e}")
        
        return self._client
    
    async def create_session(self, session_id: str, data: Dict) -> bool:
        """Create a new session in Redis."""
        try:
            if not self._validate_session_data(data):
                raise SessionStorageError("Invalid session data structure")
            
            client = await self._get_client()
            session_data = SessionData(session_id, data)
            key = f"{self.key_prefix}{session_id}"
            
            # Set with expiration
            await client.setex(
                key, 
                timedelta(hours=self.timeout_hours),
                json.dumps(session_data.to_dict())
            )
            
            logger.info(f"Created session {session_id} in Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[SessionData]:
        """Get session data from Redis."""
        try:
            client = await self._get_client()
            key = f"{self.key_prefix}{session_id}"
            
            data = await client.get(key)
            if data is None:
                return None
            
            session_dict = json.loads(data)
            session_data = SessionData.from_dict(session_dict)
            
            # Update last accessed time
            session_data.last_accessed = datetime.now()
            await client.setex(
                key,
                timedelta(hours=self.timeout_hours),
                json.dumps(session_data.to_dict())
            )
            
            return session_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in session {session_id}: {e}")
            # Clean up corrupted session
            await self.delete_session(session_id)
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def update_session(self, session_id: str, data: Dict) -> bool:
        """Update existing session data in Redis."""
        try:
            client = await self._get_client()
            key = f"{self.key_prefix}{session_id}"
            
            # Check if session exists
            if not await client.exists(key):
                return False
            
            session_data = SessionData(session_id, data)
            
            # Update with same expiration
            await client.setex(
                key,
                timedelta(hours=self.timeout_hours),
                json.dumps(session_data.to_dict())
            )
            
            logger.info(f"Updated session {session_id} in Redis")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update session {session_id}: {e}")
            return False
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis."""
        try:
            client = await self._get_client()
            key = f"{self.key_prefix}{session_id}"
            
            result = await client.delete(key)
            if result:
                logger.info(f"Deleted session {session_id} from Redis")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def cleanup_expired(self) -> int:
        """Clean up expired sessions (Redis handles this automatically with TTL)."""
        # Redis automatically expires keys based on TTL, so this is mostly for logging
        try:
            client = await self._get_client()
            
            # Get all session keys
            pattern = f"{self.key_prefix}*"
            keys = await client.keys(pattern)
            
            # Check which ones are expired (TTL < 0 means expired)
            expired_count = 0
            for key in keys:
                ttl = await client.ttl(key)
                if ttl == -2:  # Key doesn't exist (expired)
                    expired_count += 1
            
            if expired_count > 0:
                logger.info(f"Redis automatically cleaned up {expired_count} expired sessions")
            
            return expired_count
            
        except Exception as e:
            logger.error(f"Failed to cleanup expired sessions: {e}")
            return 0
    
    async def get_all_sessions(self) -> List[SessionData]:
        """Get all active sessions (for admin/debugging)."""
        try:
            client = await self._get_client()
            pattern = f"{self.key_prefix}*"
            keys = await client.keys(pattern)
            
            sessions = []
            for key in keys:
                data = await client.get(key)
                if data:
                    try:
                        session_dict = json.loads(data)
                        sessions.append(SessionData.from_dict(session_dict))
                    except json.JSONDecodeError:
                        logger.warning(f"Skipping corrupted session data for key: {key}")
            
            return sessions
            
        except Exception as e:
            logger.error(f"Failed to get all sessions: {e}")
            return []
    
    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists in Redis."""
        try:
            client = await self._get_client()
            key = f"{self.key_prefix}{session_id}"
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check session existence {session_id}: {e}")
            return False
    
    async def get_session_count(self) -> int:
        """Get total number of active sessions."""
        try:
            client = await self._get_client()
            pattern = f"{self.key_prefix}*"
            keys = await client.keys(pattern)
            return len(keys)
        except Exception as e:
            logger.error(f"Failed to get session count: {e}")
            return 0
    
    async def close(self):
        """Close Redis connection."""
        if self._client:
            await self._client.close()
            self._client = None
        if self.pool:
            await self.pool.disconnect()
            self.pool = None
        logger.info("Redis connection closed")
