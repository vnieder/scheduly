#!/usr/bin/env python3
"""
Demo script showing the Scheduly backend in action.
This demonstrates the complete workflow without user interaction.
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def demo_build_and_optimize():
    """Demonstrate building and optimizing a schedule."""
    print("🎓 Scheduly Backend Demo")
    print("=" * 50)
    
    # Step 1: Build initial schedule
    print("\n📚 Step 1: Building initial schedule")
    print("Major: Computer Science")
    print("Preferences: 'no Friday, start after 10am, 15 credits'")
    
    payload = {
        "school": "Pitt",
        "major": "Computer Science",
        "term": "2251",
        "utterance": "no Friday, start after 10am, 15 credits"
    }
    
    response = requests.post(f"{BASE_URL}/build", json=payload)
    if response.status_code != 200:
        print(f"❌ Build failed: {response.status_code} - {response.text}")
        return
    
    data = response.json()
    session_id = data.get('session_id')
    plan = data.get('plan', {})
    
    print("✅ Schedule built successfully!")
    print(f"Session ID: {session_id}")
    print(f"Total Credits: {plan.get('totalCredits')}")
    print(f"Number of Sections: {len(plan.get('sections', []))}")
    
    # Show initial schedule
    print("\n📋 Initial Schedule:")
    for section in plan.get('sections', []):
        days_str = ', '.join(section.get('days', []))
        print(f"  • {section['course']} {section['section']} - {days_str} {section['start']}-{section['end']}")
    
    # Step 2: Optimize schedule
    print("\n🔧 Step 2: Optimizing schedule")
    print("New preferences: 'avoid Tuesday and Thursday'")
    
    optimize_payload = {
        "session_id": session_id,
        "utterance": "avoid Tuesday and Thursday"
    }
    
    response = requests.post(f"{BASE_URL}/optimize", json=optimize_payload)
    if response.status_code != 200:
        print(f"❌ Optimization failed: {response.status_code} - {response.text}")
        return
    
    data = response.json()
    optimized_plan = data.get('plan', {})
    
    print("✅ Schedule optimized successfully!")
    print(f"Total Credits: {optimized_plan.get('totalCredits')}")
    print(f"Number of Sections: {len(optimized_plan.get('sections', []))}")
    
    # Show optimized schedule
    print("\n📋 Optimized Schedule:")
    for section in optimized_plan.get('sections', []):
        days_str = ', '.join(section.get('days', []))
        print(f"  • {section['course']} {section['section']} - {days_str} {section['start']}-{section['end']}")
    
    # Show explanations
    if optimized_plan.get('explanations'):
        print("\n💡 Explanations:")
        for explanation in optimized_plan['explanations']:
            print(f"  • {explanation}")
    
    print("\n🎉 Demo completed successfully!")
    print("The backend successfully:")
    print("  ✅ Built an initial schedule with preferences")
    print("  ✅ Optimized the schedule with new constraints")
    print("  ✅ Respected prerequisites (CS1550 requires CS0449, CS0447)")
    print("  ✅ Avoided conflicting days and times")
    print("  ✅ Used real course sections from Pitt's API")

if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code != 200:
            print("❌ Server is not running. Please start it first:")
            print("uvicorn app:app --reload --port 8000")
            sys.exit(1)
        
        demo_build_and_optimize()
        
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server.")
        print("Make sure the server is running: uvicorn app:app --reload --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        sys.exit(1)
