#!/usr/bin/env python3
"""
Test suite for session storage implementations.
Tests both Redis and Database storage backends.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

from services.session_storage import SessionData, SessionStorageError
from services.redis_session import RedisSessionStorage
from services.database_session import DatabaseSessionStorage
from services.session_manager import session_manager

class TestSessionData:
    """Test SessionData model."""
    
    def test_session_data_creation(self):
        """Test SessionData creation and serialization."""
        data = {"test": "data", "number": 123}
        session = SessionData("test-id", data)
        
        assert session.session_id == "test-id"
        assert session.data == data
        assert isinstance(session.created_at, datetime)
        assert isinstance(session.last_accessed, datetime)
    
    def test_session_data_serialization(self):
        """Test SessionData to_dict and from_dict."""
        data = {"test": "data"}
        session = SessionData("test-id", data)
        
        # Convert to dict
        session_dict = session.to_dict()
        assert session_dict["session_id"] == "test-id"
        assert session_dict["data"] == data
        assert "created_at" in session_dict
        assert "last_accessed" in session_dict
        
        # Convert back from dict
        restored = SessionData.from_dict(session_dict)
        assert restored.session_id == session.session_id
        assert restored.data == session.data
        assert restored.created_at == session.created_at
    
    def test_session_expiration(self):
        """Test session expiration logic."""
        data = {"test": "data"}
        
        # Create session with 1 hour timeout
        session = SessionData("test-id", data)
        session.created_at = datetime.now() - timedelta(hours=2)  # 2 hours ago
        
        assert session.is_expired(1) == True  # Expired
        assert session.is_expired(3) == False  # Not expired

class TestRedisSessionStorage:
    """Test Redis session storage."""
    
    @pytest.fixture
    async def redis_storage(self):
        """Create Redis storage instance for testing."""
        storage = RedisSessionStorage(
            host="localhost",
            port=6379,
            db=15,  # Use test database
            timeout_hours=1
        )
        yield storage
        await storage.close()
    
    @pytest.mark.asyncio
    async def test_create_and_get_session(self, redis_storage):
        """Test creating and retrieving a session."""
        session_id = "test-session-1"
        data = {"major": "Computer Science", "term": "2251"}
        
        # Create session
        success = await redis_storage.create_session(session_id, data)
        assert success == True
        
        # Retrieve session
        retrieved = await redis_storage.get_session(session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id
        assert retrieved.data == data
    
    @pytest.mark.asyncio
    async def test_session_not_found(self, redis_storage):
        """Test retrieving non-existent session."""
        retrieved = await redis_storage.get_session("non-existent")
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_update_session(self, redis_storage):
        """Test updating session data."""
        session_id = "test-session-2"
        original_data = {"major": "Computer Science"}
        updated_data = {"major": "Mathematics"}
        
        # Create session
        await redis_storage.create_session(session_id, original_data)
        
        # Update session
        success = await redis_storage.update_session(session_id, updated_data)
        assert success == True
        
        # Verify update
        retrieved = await redis_storage.get_session(session_id)
        assert retrieved.data == updated_data
    
    @pytest.mark.asyncio
    async def test_delete_session(self, redis_storage):
        """Test deleting a session."""
        session_id = "test-session-3"
        data = {"major": "Computer Science"}
        
        # Create session
        await redis_storage.create_session(session_id, data)
        
        # Verify session exists
        assert await redis_storage.session_exists(session_id) == True
        
        # Delete session
        success = await redis_storage.delete_session(session_id)
        assert success == True
        
        # Verify session deleted
        assert await redis_storage.session_exists(session_id) == False
        assert await redis_storage.get_session(session_id) is None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, redis_storage):
        """Test cleanup of expired sessions."""
        # Redis handles TTL automatically, so this mainly tests the interface
        count = await redis_storage.cleanup_expired()
        assert isinstance(count, int)

class TestDatabaseSessionStorage:
    """Test Database session storage."""
    
    @pytest.fixture
    async def db_storage(self):
        """Create Database storage instance for testing."""
        # Use in-memory SQLite for testing
        storage = DatabaseSessionStorage(
            database_url="sqlite+aiosqlite:///:memory:",
            timeout_hours=1
        )
        yield storage
        await storage.close()
    
    @pytest.mark.asyncio
    async def test_create_and_get_session(self, db_storage):
        """Test creating and retrieving a session."""
        session_id = "test-session-1"
        data = {"major": "Computer Science", "term": "2251"}
        
        # Create session
        success = await db_storage.create_session(session_id, data)
        assert success == True
        
        # Retrieve session
        retrieved = await db_storage.get_session(session_id)
        assert retrieved is not None
        assert retrieved.session_id == session_id
        assert retrieved.data == data
    
    @pytest.mark.asyncio
    async def test_session_expiration(self, db_storage):
        """Test session expiration handling."""
        session_id = "test-session-expired"
        data = {"major": "Computer Science"}
        
        # Create session
        await db_storage.create_session(session_id, data)
        
        # Manually expire the session by updating expires_at
        from services.database_session import SessionModel
        from sqlalchemy import update
        
        session_factory = await db_storage._get_session_factory()
        async with session_factory() as session:
            await session.execute(
                update(SessionModel)
                .where(SessionModel.session_id == session_id)
                .values(expires_at=datetime.utcnow() - timedelta(hours=1))
            )
            await session.commit()
        
        # Session should not be retrievable
        retrieved = await db_storage.get_session(session_id)
        assert retrieved is None
    
    @pytest.mark.asyncio
    async def test_cleanup_expired(self, db_storage):
        """Test cleanup of expired sessions."""
        # Create some expired sessions
        expired_data = {"major": "Test"}
        for i in range(3):
            session_id = f"expired-session-{i}"
            await db_storage.create_session(session_id, expired_data)
            
            # Manually expire them
            from services.database_session import SessionModel
            from sqlalchemy import update
            
            session_factory = await db_storage._get_session_factory()
            async with session_factory() as session:
                await session.execute(
                    update(SessionModel)
                    .where(SessionModel.session_id == session_id)
                    .values(expires_at=datetime.utcnow() - timedelta(hours=1))
                )
                await session.commit()
        
        # Cleanup should remove expired sessions
        count = await db_storage.cleanup_expired()
        assert count >= 3

class TestSessionManager:
    """Test session manager factory."""
    
    @pytest.mark.asyncio
    async def test_auto_detection(self):
        """Test storage type auto-detection."""
        with patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379'}):
            storage_type = session_manager._detect_storage_type()
            assert storage_type.value == "redis"
        
        with patch.dict('os.environ', {'DATABASE_URL': 'postgresql://localhost/test'}):
            storage_type = session_manager._detect_storage_type()
            assert storage_type.value == "database"
    
    @pytest.mark.asyncio
    async def test_redis_initialization(self):
        """Test Redis storage initialization."""
        with patch.dict('os.environ', {'REDIS_URL': 'redis://localhost:6379/15'}):
            storage = await session_manager.initialize_storage()
            assert isinstance(storage, RedisSessionStorage)
            await session_manager.close()

# Integration tests
class TestIntegration:
    """Integration tests for session storage."""
    
    @pytest.mark.asyncio
    async def test_migration_simulation(self):
        """Test simulating session migration."""
        # This would test the actual migration process
        # For now, just test that the interfaces work together
        pass

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
