#!/usr/bin/env python3
"""
Simple test script to verify the interactive test works properly.
"""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_semester_planning_direct():
    """Test the semester planning endpoint directly."""
    print("🧪 Testing semester planning endpoint...")
    
    payload = {
        "school": "Pitt",
        "major": "Computer Science",
        "starting_term": "2251",
        "num_semesters": 2,
        "utterance": "no Friday"
    }
    
    response = requests.post(f"{BASE_URL}/plan-semesters", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Semester planning endpoint working!")
        print(f"Total semesters: {data['total_semesters']}")
        
        for semester in data['semester_plans']:
            plan = semester['plan']
            print(f"\n📚 {semester['semester']} (Term: {semester['term']})")
            print(f"   Total Credits: {plan['totalCredits']}")
            print(f"   Courses: {len(plan['sections'])}")
            if plan['sections']:
                for section in plan['sections'][:3]:  # Show first 3
                    print(f"     • {section['course']} {section['section']} - {section['days']} {section['start']}-{section['end']}")
                if len(plan['sections']) > 3:
                    print(f"     ... and {len(plan['sections']) - 3} more courses")
            else:
                print("     No courses scheduled")
            
            if plan['explanations']:
                print(f"   Notes: {'; '.join(plan['explanations'])}")
        
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        if "429" in str(response.status_code) or "RESOURCE_EXHAUSTED" in response.text:
            print("⚠️  Rate limit exceeded. Please wait before trying again.")
        else:
            print(f"Response: {response.text}")
        return False

def test_single_schedule():
    """Test the single schedule endpoint."""
    print("\n🧪 Testing single schedule endpoint...")
    
    payload = {
        "school": "Pitt",
        "major": "Computer Science",
        "term": "2251",
        "utterance": "no Friday"
    }
    
    response = requests.post(f"{BASE_URL}/build", json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print("✅ Single schedule endpoint working!")
        print(f"Total Credits: {data['plan']['totalCredits']}")
        print(f"Sections: {len(data['plan']['sections'])}")
        
        if data['plan']['sections']:
            for section in data['plan']['sections'][:3]:  # Show first 3
                print(f"  • {section['course']} {section['section']} - {section['days']} {section['start']}-{section['end']}")
            if len(data['plan']['sections']) > 3:
                print(f"  ... and {len(data['plan']['sections']) - 3} more courses")
        else:
            print("  No courses scheduled")
        
        return True
    else:
        print(f"❌ Error: {response.status_code}")
        if "429" in str(response.status_code) or "RESOURCE_EXHAUSTED" in response.text:
            print("⚠️  Rate limit exceeded. Please wait before trying again.")
        else:
            print(f"Response: {response.text}")
        return False

if __name__ == "__main__":
    print("🚀 Testing Scheduly Backend")
    print("=" * 50)
    
    # Test health first
    try:
        health = requests.get(f"{BASE_URL}/health")
        if health.status_code == 200:
            print("✅ Server is running!")
        else:
            print("❌ Server health check failed")
            exit(1)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server. Make sure it's running on port 8000")
        exit(1)
    
    # Test endpoints
    success1 = test_single_schedule()
    success2 = test_semester_planning_direct()
    
    if success1 and success2:
        print("\n🎉 All tests passed! The interactive test script should work properly.")
    else:
        print("\n⚠️  Some tests failed. Check the server logs for details.")
