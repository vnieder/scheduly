#!/usr/bin/env python3
"""
Interactive test script for Scheduly backend.
Run this to test the API interactively.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def print_json(data):
    print(json.dumps(data, indent=2))

def test_build_interactive():
    print("🔨 Building a schedule...")
    
    # Ask for major
    major = input("What major are you? (e.g., 'Computer Science', 'Mathematics', 'Engineering'): ").strip()
    if not major:
        major = "Computer Science"  # Default
        print(f"Using default major: {major}")
    
    # Ask for preferences
    preferences = input("Enter preferences (e.g., 'no Friday, start after 10am'): ").strip()
    if not preferences:
        preferences = "no Friday, start after 10am"
        print(f"Using default preferences: {preferences}")
    
    payload = {
        "school": "Pitt",
        "major": major,
        "term": "2251",
        "utterance": preferences
    }
    
    response = requests.post(f"{BASE_URL}/build", json=payload)
    if response.status_code == 200:
        data = response.json()
        print("✅ Schedule built successfully!")
        print(f"Session ID: {data['session_id']}")
        print(f"Total Credits: {data['plan']['totalCredits']}")
        print(f"Sections: {len(data['plan']['sections'])}")
        print("\nSections:")
        for section in data['plan']['sections']:
            print(f"  {section['course']} {section['section']} - {section['days']} {section['start']}-{section['end']} (CRN: {section['crn']})")
        
        print("\nExplanations:")
        for explanation in data['plan']['explanations']:
            print(f"  • {explanation}")
        
        return data['session_id']
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None

def test_optimize_interactive(session_id):
    if not session_id:
        print("No session ID available for optimization")
        return
        
    print("\n🔧 Optimizing schedule...")
    utterance = input("Enter new preferences (e.g., 'avoid Tue/Thu, pin CRN 19394'): ")
    if not utterance:
        utterance = "avoid Tue/Thu"
    
    payload = {
        "session_id": session_id,
        "utterance": utterance
    }
    
    response = requests.post(f"{BASE_URL}/optimize", json=payload)
    if response.status_code == 200:
        data = response.json()
        print("✅ Schedule optimized successfully!")
        print(f"Total Credits: {data['plan']['totalCredits']}")
        print(f"Sections: {len(data['plan']['sections'])}")
        print("\nUpdated Sections:")
        for section in data['plan']['sections']:
            print(f"  {section['course']} {section['section']} - {section['days']} {section['start']}-{section['end']} (CRN: {section['crn']})")
        
        print("\nExplanations:")
        for explanation in data['plan']['explanations']:
            print(f"  • {explanation}")
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")

def test_semester_planning():
    print("📅 Planning multiple semesters...")
    
    # Ask for major
    major = input("What major are you? (e.g., 'Computer Science', 'Mathematics', 'Engineering'): ").strip()
    if not major:
        major = "Computer Science"
        print(f"Using default major: {major}")
    
    # Ask for number of semesters
    num_semesters = input("How many semesters to plan? (default 4): ").strip()
    if not num_semesters:
        num_semesters = 4
    else:
        num_semesters = int(num_semesters)
    
    # Ask for preferences
    preferences = input("Enter preferences (e.g., 'no Friday, start after 10am'): ").strip()
    if not preferences:
        preferences = "no Friday, start after 10am"
        print(f"Using default preferences: {preferences}")
    
    payload = {
        "school": "Pitt",
        "major": major,
        "starting_term": "2251",
        "num_semesters": num_semesters,
        "utterance": preferences
    }
    
    response = requests.post(f"{BASE_URL}/plan-semesters", json=payload)
    if response.status_code == 200:
        data = response.json()
        print("✅ Multi-semester plan created successfully!")
        print(f"Total semesters planned: {data['total_semesters']}")
        
        for semester in data['semester_plans']:
            plan = semester['plan']
            print(f"\n📚 {semester['semester']} (Term: {semester['term']})")
            print(f"   Total Credits: {plan['totalCredits']}")
            print(f"   Courses: {len(plan['sections'])}")
            for section in plan['sections']:
                print(f"     • {section['course']} {section['section']} - {section['days']} {section['start']}-{section['end']}")
            if plan['explanations']:
                print(f"   Notes: {'; '.join(plan['explanations'])}")
        
        return data
    else:
        print(f"❌ Error: {response.status_code} - {response.text}")
        return None

def main():
    print("🚀 Scheduly Backend Interactive Tester")
    print("=" * 50)
    
    # Test health first
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Server is running!")
        else:
            print("❌ Server health check failed")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on port 8000")
        return
    
    while True:
        print("\n" + "=" * 50)
        print("Choose an option:")
        print("1. Build a new schedule")
        print("2. Optimize existing schedule")
        print("3. View course sections")
        print("4. Plan multiple semesters")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == "1":
            session_id = test_build_interactive()
        elif choice == "2":
            if 'session_id' in locals():
                test_optimize_interactive(session_id)
            else:
                print("❌ No session available. Build a schedule first.")
        elif choice == "3":
            print("\n📚 Fetching course sections...")
            payload = {
                "term": "2251",
                "course_codes": ["CS0445", "CS1501", "CS1550"]
            }
            response = requests.post(f"{BASE_URL}/catalog/sections", json=payload)
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Found {len(data['sections'])} sections:")
                for section in data['sections'][:5]:  # Show first 5
                    print(f"  {section['course']} {section['section']} - {section['days']} {section['start']}-{section['end']} (CRN: {section['crn']})")
                if len(data['sections']) > 5:
                    print(f"  ... and {len(data['sections']) - 5} more sections")
            else:
                print(f"❌ Error: {response.status_code} - {response.text}")
        elif choice == "4":
            test_semester_planning()
        elif choice == "5":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1-5.")

if __name__ == "__main__":
    main()
