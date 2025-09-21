#!/usr/bin/env python3
"""
Interactive test script for Scheduly backend.
Test the complete workflow: build schedule → optimize schedule → test preferences.
"""

import requests
import json
import sys
import os
from typing import Optional

BASE_URL = "http://localhost:8000"

def print_separator():
    print("=" * 60)

def print_header(title: str):
    print_separator()
    print(f"🎓 {title}")
    print_separator()

def print_schedule(plan: dict, title: str = "Schedule"):
    """Pretty print a schedule plan."""
    print(f"\n📚 {title}")
    print(f"Term: {plan.get('term', 'N/A')}")
    print(f"Total Credits: {plan.get('totalCredits', 'N/A')}")
    print(f"Sections: {len(plan.get('sections', []))}")
    
    if plan.get('sections'):
        print("\n📋 Courses:")
        for section in plan['sections']:
            days_str = ', '.join(section.get('days', []))
            print(f"  • {section['course']} {section['section']} - {days_str} {section['start']}-{section['end']} (CRN: {section['crn']})")
    
    if plan.get('explanations'):
        print("\n💡 Explanations:")
        for explanation in plan['explanations']:
            print(f"  • {explanation}")

def test_health():
    """Test the health endpoint."""
    print_header("Testing Health Endpoint")
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server")
        print("Make sure the server is running: uvicorn app:app --reload --port 8000")
        return False
    except Exception as e:
        print(f"❌ Health check error: {e}")
        return False

def test_build_schedule():
    """Test building a schedule interactively."""
    print_header("Building Schedule")
    
    # Get user input
    print("Let's build your schedule!")
    
    # Major
    major = input("Enter your major (default: Computer Science): ").strip()
    if not major:
        major = "Computer Science"
        print(f"Using default major: {major}")
    
    # Preferences
    print("\nEnter your preferences (e.g., 'no Friday, start after 10am, 15 credits'):")
    preferences = input("Preferences: ").strip()
    if not preferences:
        preferences = "no Friday, start after 10am, 15 credits"
        print(f"Using default preferences: {preferences}")
    
    # Build the schedule
    payload = {
        "school": "Pitt",
        "major": major,
        "term": "2251",  # Fall 2025
        "utterance": preferences
    }
    
    print(f"\n🚀 Building schedule for {major} with preferences: '{preferences}'")
    
    try:
        response = requests.post(f"{BASE_URL}/build", json=payload)
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            
            print("✅ Schedule built successfully!")
            print(f"Session ID: {session_id}")
            
            # Show requirements
            requirements = data.get('requirements', {})
            print(f"\n📋 Requirements:")
            print(f"  Required courses: {len(requirements.get('required', []))}")
            print(f"  Gen ed groups: {len(requirements.get('genEds', []))}")
            print(f"  Elective groups: {len(requirements.get('chooseFrom', []))}")
            
            # Show schedule
            plan = data.get('plan', {})
            print_schedule(plan, "Initial Schedule")
            
            return session_id
        else:
            print(f"❌ Build failed: {response.status_code}")
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Build error: {e}")
        return None

def test_optimize_schedule(session_id: str):
    """Test optimizing a schedule interactively."""
    if not session_id:
        print("❌ No session ID available for optimization")
        return
    
    print_header("Optimizing Schedule")
    
    print("Let's optimize your schedule!")
    print("Try suggestions like:")
    print("  • 'avoid Tuesday and Thursday'")
    print("  • 'pin section CRN 19394'")
    print("  • 'skip CS0445'")
    print("  • 'start after 11am'")
    print("  • 'no classes after 4pm'")
    
    # Get optimization preferences
    optimization = input("\nEnter optimization preferences: ").strip()
    if not optimization:
        optimization = "avoid Tuesday and Thursday"
        print(f"Using default optimization: {optimization}")
    
    payload = {
        "session_id": session_id,
        "utterance": optimization
    }
    
    print(f"\n🔧 Optimizing with: '{optimization}'")
    
    try:
        response = requests.post(f"{BASE_URL}/optimize", json=payload)
        if response.status_code == 200:
            data = response.json()
            plan = data.get('plan', {})
            
            print("✅ Schedule optimized successfully!")
            print_schedule(plan, "Optimized Schedule")
            
            return True
        else:
            print(f"❌ Optimization failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Optimization error: {e}")
        return False

def test_course_sections():
    """Test fetching course sections."""
    print_header("Testing Course Sections")
    
    courses = input("Enter course codes (comma-separated, default: CS0445,CS1501,CS1550): ").strip()
    if not courses:
        courses = "CS0445,CS1501,CS1550"
        print(f"Using default courses: {courses}")
    
    course_codes = [code.strip().upper() for code in courses.split(',')]
    
    payload = {
        "term": "2251",
        "course_codes": course_codes
    }
    
    print(f"\n🔍 Fetching sections for: {', '.join(course_codes)}")
    
    try:
        response = requests.post(f"{BASE_URL}/catalog/sections", json=payload)
        if response.status_code == 200:
            data = response.json()
            sections = data.get('sections', [])
            
            print(f"✅ Found {len(sections)} sections")
            
            if sections:
                print("\n📋 Available Sections:")
                for section in sections:
                    days_str = ', '.join(section.get('days', []))
                    instructor = section.get('instructor', 'TBD')
                    print(f"  • {section['course']} {section['section']} - {days_str} {section['start']}-{section['end']} (CRN: {section['crn']}) - {instructor}")
            
            return True
        else:
            print(f"❌ Sections fetch failed: {response.status_code}")
            print(f"Error: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Sections fetch error: {e}")
        return False

def test_environment_variables():
    """Test environment variable configuration."""
    print_header("Environment Configuration")
    
    print("🔧 Current Configuration:")
    print(f"  USE_AI_PREREQUISITES: {os.getenv('USE_AI_PREREQUISITES', 'false')}")
    print(f"  DEFAULT_TERM: {os.getenv('DEFAULT_TERM', '2251')}")
    print(f"  DEFAULT_SCHOOL: {os.getenv('DEFAULT_SCHOOL', 'Pitt')}")
    print(f"  MAX_COURSES_PER_SEMESTER: {os.getenv('MAX_COURSES_PER_SEMESTER', '6')}")
    print(f"  SESSION_TIMEOUT_HOURS: {os.getenv('SESSION_TIMEOUT_HOURS', '24')}")
    
    print("\n💡 To change AI prerequisites mode:")
    print("  export USE_AI_PREREQUISITES=true   # Use AI search")
    print("  export USE_AI_PREREQUISITES=false  # Use hardcoded (default)")

def main():
    """Main interactive test function."""
    print_header("Scheduly Backend Interactive Test")
    
    print("This interactive test will guide you through testing the Scheduly backend.")
    print("Make sure the server is running: uvicorn app:app --reload --port 8000")
    
    # Test health first
    if not test_health():
        print("\n❌ Server is not running. Please start it first.")
        return
    
    # Show environment info
    test_environment_variables()
    
    # Main test loop
    while True:
        print_separator()
        print("🎯 What would you like to test?")
        print("1. Build a new schedule")
        print("2. Test course sections lookup")
        print("3. Show environment configuration")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            # Build and optimize schedule
            session_id = test_build_schedule()
            
            if session_id:
                # Ask if user wants to optimize
                optimize = input("\nWould you like to optimize this schedule? (y/n): ").strip().lower()
                if optimize in ['y', 'yes']:
                    test_optimize_schedule(session_id)
        
        elif choice == "2":
            test_course_sections()
        
        elif choice == "3":
            test_environment_variables()
        
        elif choice == "4":
            print("\n👋 Thanks for testing Scheduly!")
            break
        
        else:
            print("❌ Invalid choice. Please enter 1-4.")
        
        # Ask if user wants to continue
        continue_test = input("\nWould you like to run another test? (y/n): ").strip().lower()
        if continue_test not in ['y', 'yes']:
            print("\n👋 Thanks for testing Scheduly!")
            break

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
