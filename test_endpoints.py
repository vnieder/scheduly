#!/usr/bin/env python3
"""
Test script to verify Scheduly backend functionality.
Run this after starting the server with: uvicorn app:app --reload --port 8000
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000"

def test_health():
    """Test the health endpoint."""
    print("Testing /health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("✓ Health check passed")
        print(f"  Response: {response.json()}")
    else:
        print(f"✗ Health check failed: {response.status_code}")
    print()

def test_build():
    """Test the build endpoint."""
    print("Testing /build endpoint...")
    payload = {
        "school": "Pitt",
        "major": "Computer Science",
        "term": "2251",
        "utterance": "no Friday, start after 10am, 15 credits"
    }
    
    response = requests.post(f"{BASE_URL}/build", json=payload)
    if response.status_code == 200:
        print("✓ Build endpoint passed")
        data = response.json()
        print(f"  Session ID: {data.get('session_id', 'N/A')}")
        print(f"  Total credits: {data.get('plan', {}).get('totalCredits', 'N/A')}")
        print(f"  Sections: {len(data.get('plan', {}).get('sections', []))}")
        print(f"  Explanations: {data.get('plan', {}).get('explanations', [])}")
        return data.get('session_id')
    else:
        print(f"✗ Build endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")
        return None

def test_optimize(session_id):
    """Test the optimize endpoint."""
    if not session_id:
        print("Skipping optimize test - no session ID")
        return
        
    print("Testing /optimize endpoint...")
    payload = {
        "session_id": session_id,
        "utterance": "avoid Tue/Thu, pin section CRN 45678"
    }
    
    response = requests.post(f"{BASE_URL}/optimize", json=payload)
    if response.status_code == 200:
        print("✓ Optimize endpoint passed")
        data = response.json()
        print(f"  Total credits: {data.get('plan', {}).get('totalCredits', 'N/A')}")
        print(f"  Sections: {len(data.get('plan', {}).get('sections', []))}")
        print(f"  Explanations: {data.get('plan', {}).get('explanations', [])}")
    else:
        print(f"✗ Optimize endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")

def test_sections():
    """Test the sections endpoint."""
    print("Testing /catalog/sections endpoint...")
    payload = {
        "term": "2251",
        "course_codes": ["CS0445", "CS1501", "CS1550"]
    }
    
    response = requests.post(f"{BASE_URL}/catalog/sections", json=payload)
    if response.status_code == 200:
        print("✓ Sections endpoint passed")
        data = response.json()
        print(f"  Sections returned: {len(data.get('sections', []))}")
        for section in data.get('sections', [])[:3]:  # Show first 3
            print(f"    {section.get('course')} {section.get('section')} - {section.get('days')} {section.get('start')}-{section.get('end')}")
    else:
        print(f"✗ Sections endpoint failed: {response.status_code}")
        print(f"  Error: {response.text}")

def test_terms():
    """Test the terms service."""
    print("Testing terms service...")
    try:
        from services.terms import to_term_code
        
        # Test cases
        test_cases = [
            ("Fall", 2025, "2251"),
            ("Spring", 2025, "2244"),
            ("Summer", 2025, "2257"),
        ]
        
        for season, year, expected in test_cases:
            result = to_term_code(season, year)
            if result == expected:
                print(f"✓ {season} {year} -> {result}")
            else:
                print(f"✗ {season} {year} -> {result} (expected {expected})")
                
    except Exception as e:
        print(f"✗ Terms service test failed: {e}")

def main():
    print("Scheduly Backend Test Suite")
    print("=" * 40)
    
    try:
        test_health()
        test_terms()
        test_sections()
        session_id = test_build()
        test_optimize(session_id)
        
        print("=" * 40)
        print("Test suite completed!")
        
    except requests.exceptions.ConnectionError:
        print("✗ Could not connect to server. Make sure it's running on port 8000")
        print("  Start with: uvicorn app:app --reload --port 8000")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
