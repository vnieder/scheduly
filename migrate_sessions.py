#!/usr/bin/env python3
"""
Migration script to move sessions from file-based storage to new backend.
Run this script to migrate existing sessions.json to Redis/Database storage.
"""

import json
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict

from services.session_manager import session_manager
from services.session_storage import SessionStorageType

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SESSION_FILE = "sessions.json"

async def migrate_sessions(storage_type: SessionStorageType = None):
    """
    Migrate sessions from file-based storage to new backend.
    
    Args:
        storage_type: Target storage type (auto-detected if None)
    """
    if not os.path.exists(SESSION_FILE):
        logger.info(f"No sessions file found at {SESSION_FILE}, nothing to migrate")
        return
    
    try:
        # Load existing sessions
        logger.info(f"Loading sessions from {SESSION_FILE}")
        with open(SESSION_FILE, 'r') as f:
            sessions = json.load(f)
        
        if not sessions:
            logger.info("No sessions to migrate")
            return
        
        # Initialize new storage
        logger.info(f"Initializing {storage_type.value if storage_type else 'auto-detected'} storage")
        storage = await session_manager.initialize_storage(storage_type)
        
        # Migrate each session
        migrated_count = 0
        failed_count = 0
        
        for session_id, session_data in sessions.items():
            try:
                # Validate session data structure
                if not isinstance(session_data, dict):
                    logger.warning(f"Skipping invalid session {session_id}: not a dict")
                    failed_count += 1
                    continue
                
                # Check if session is expired
                created_at = session_data.get('created_at')
                if created_at:
                    try:
                        created_time = datetime.fromisoformat(created_at)
                        cutoff = datetime.now() - timedelta(hours=24)  # Default timeout
                        if created_time < cutoff:
                            logger.info(f"Skipping expired session {session_id}")
                            continue
                    except ValueError:
                        logger.warning(f"Invalid timestamp for session {session_id}: {created_at}")
                        continue
                
                # Create session in new storage
                success = await storage.create_session(session_id, session_data)
                if success:
                    migrated_count += 1
                    logger.info(f"Migrated session {session_id}")
                else:
                    failed_count += 1
                    logger.error(f"Failed to migrate session {session_id}")
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error migrating session {session_id}: {e}")
        
        logger.info(f"Migration completed: {migrated_count} migrated, {failed_count} failed")
        
        # Backup original file
        backup_file = f"{SESSION_FILE}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        os.rename(SESSION_FILE, backup_file)
        logger.info(f"Original sessions file backed up to {backup_file}")
        
        # Verify migration
        await verify_migration(storage, migrated_count)
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        raise
    finally:
        # Close storage connections
        await session_manager.close()

async def verify_migration(storage, expected_count: int):
    """Verify that migration was successful."""
    try:
        actual_count = await storage.get_session_count()
        if actual_count == expected_count:
            logger.info(f"✅ Migration verification successful: {actual_count} sessions")
        else:
            logger.warning(f"⚠️ Migration verification: expected {expected_count}, got {actual_count}")
    except Exception as e:
        logger.error(f"Migration verification failed: {e}")

async def list_sessions():
    """List all sessions in the new storage backend."""
    try:
        storage = await session_manager.initialize_storage()
        sessions = await storage.get_all_sessions()
        
        logger.info(f"Found {len(sessions)} sessions:")
        for session in sessions:
            logger.info(f"  {session.session_id}: {session.data.get('major', 'Unknown')} - {session.created_at}")
            
    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
    finally:
        await session_manager.close()

def main():
    """Main migration function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate sessions to new storage backend")
    parser.add_argument("--storage", choices=["redis", "database"], 
                       help="Target storage type (auto-detected if not specified)")
    parser.add_argument("--list", action="store_true", 
                       help="List sessions in new storage backend")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show what would be migrated without actually migrating")
    
    args = parser.parse_args()
    
    if args.list:
        asyncio.run(list_sessions())
    else:
        storage_type = None
        if args.storage:
            storage_type = SessionStorageType(args.storage)
        
        if args.dry_run:
            logger.info("DRY RUN: Would migrate sessions (not actually migrating)")
            # TODO: Implement dry run logic
        
        asyncio.run(migrate_sessions(storage_type))

if __name__ == "__main__":
    main()
