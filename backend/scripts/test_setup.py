#!/usr/bin/env python3
"""
Test script to verify Scheduly backend setup.
"""

import os
import sys
import asyncio
from sqlalchemy import create_engine, text

# Add the src directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_database_connection():
    """Test database connection."""
    print("🔍 Testing database connection...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL environment variable not set!")
        return False
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_auth0_config():
    """Test Auth0 configuration."""
    print("🔍 Testing Auth0 configuration...")
    
    required_vars = ["AUTH0_DOMAIN", "AUTH0_AUDIENCE"]
    missing_vars = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing Auth0 environment variables: {', '.join(missing_vars)}")
        return False
    
    print("✅ Auth0 configuration looks good!")
    return True

def test_imports():
    """Test that all required modules can be imported."""
    print("🔍 Testing imports...")
    
    try:
        from src.models.user_models import User, ScheduleHistory
        from src.services.auth.auth0_middleware import Auth0Service
        from src.services.storage.user_schedule_storage import UserScheduleStorage
        print("✅ All imports successful!")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_tables_exist():
    """Test that required tables exist."""
    print("🔍 Testing database tables...")
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not set")
        return False
    
    try:
        engine = create_engine(database_url)
        with engine.connect() as conn:
            # Check users table
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'users'
                );
            """))
            users_exists = result.scalar()
            
            # Check schedule_history table
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'schedule_history'
                );
            """))
            history_exists = result.scalar()
            
            if users_exists and history_exists:
                print("✅ All required tables exist!")
                return True
            else:
                print("❌ Missing tables:")
                print(f"  - users: {'✅' if users_exists else '❌'}")
                print(f"  - schedule_history: {'✅' if history_exists else '❌'}")
                return False
                
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def main():
    """Run all tests."""
    print("🚀 Scheduly Backend Setup Test")
    print("=" * 50)
    
    tests = [
        ("Database Connection", test_database_connection),
        ("Auth0 Configuration", test_auth0_config),
        ("Module Imports", test_imports),
        ("Database Tables", test_tables_exist),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
        else:
            print(f"❌ {test_name} failed")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} passed")
    
    if passed == total:
        print("🎉 All tests passed! Your backend is ready to go!")
        print("\nNext steps:")
        print("1. Start the backend server: uvicorn app:app --reload --port 8000")
        print("2. Configure Auth0 in the frontend")
        print("3. Start the frontend: npm run dev")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        print("\nCommon fixes:")
        print("- Set DATABASE_URL environment variable")
        print("- Set AUTH0_DOMAIN and AUTH0_AUDIENCE environment variables")
        print("- Run: python scripts/init_database.py")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

