#!/usr/bin/env python3
"""
Database initialization script for Scheduly backend.
Creates the necessary tables for user management and schedule history.
"""

import os
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from models.user_models import Base

def create_tables(database_url: str):
    """Create all tables in the database."""
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Create all tables
        Base.metadata.create_all(engine)
        
        print("✅ Database tables created successfully!")
        print("Created tables:")
        print("  - users")
        print("  - schedule_history")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def verify_tables(database_url: str):
    """Verify that tables were created correctly."""
    try:
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with SessionLocal() as session:
            # Check if users table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """))
            users_exists = result.scalar()
            
            # Check if schedule_history table exists
            result = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'schedule_history'
                );
            """))
            history_exists = result.scalar()
            
            if users_exists and history_exists:
                print("✅ All tables verified successfully!")
                return True
            else:
                print("❌ Some tables are missing:")
                print(f"  - users: {'✅' if users_exists else '❌'}")
                print(f"  - schedule_history: {'✅' if history_exists else '❌'}")
                return False
                
    except Exception as e:
        print(f"❌ Error verifying tables: {e}")
        return False

def main():
    """Main function to initialize the database."""
    print("🚀 Initializing Scheduly Database...")
    print("=" * 50)
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        print("Please set DATABASE_URL to your PostgreSQL connection string.")
        print("Example: postgresql://user:password@localhost:5432/scheduly")
        sys.exit(1)
    
    print(f"📊 Database URL: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")
    
    # Create tables
    if not create_tables(database_url):
        sys.exit(1)
    
    # Verify tables
    if not verify_tables(database_url):
        sys.exit(1)
    
    print("=" * 50)
    print("🎉 Database initialization completed successfully!")
    print("\nNext steps:")
    print("1. Configure Auth0 credentials in your environment")
    print("2. Set AUTH0_DOMAIN and AUTH0_AUDIENCE environment variables")
    print("3. Start your FastAPI backend server")

if __name__ == "__main__":
    main()

