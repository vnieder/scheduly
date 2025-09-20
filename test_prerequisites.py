#!/usr/bin/env python3
"""
Test script to verify prerequisite functionality.
Run this to test the prerequisite search and caching.
"""

import os
import sys
import asyncio
import time
from dotenv import load_dotenv

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents.gemini import search_course_prerequisites, batch_search_prerequisites, get_requirements_with_prereqs

load_dotenv()

def test_single_prerequisite():
    """Test prerequisite search for a single course."""
    print("Testing single prerequisite search...")
    
    # Test with a well-known Pitt CS course that likely has prerequisites
    course_code = "CS1501"
    school = "University of Pittsburgh"
    
    try:
        prerequisites = search_course_prerequisites(course_code, school)
        print(f"✅ Found prerequisites for {course_code}: {prerequisites}")
        return True
    except Exception as e:
        print(f"❌ Error testing {course_code}: {e}")
        return False

def test_batch_prerequisites():
    """Test batch prerequisite search."""
    print("\nTesting batch prerequisite search...")
    
    course_codes = ["CS0401", "CS1501", "CS1550"]
    school = "University of Pittsburgh"
    
    try:
        results = batch_search_prerequisites(course_codes, school)
        print(f"✅ Batch prerequisite results:")
        for course, prereqs in results.items():
            print(f"  {course}: {prereqs}")
        return True
    except Exception as e:
        print(f"❌ Error in batch test: {e}")
        return False

def test_full_requirements():
    """Test the full requirements flow with prerequisites."""
    print("\nTesting full requirements with prerequisites...")
    
    school = "University of Pittsburgh"
    major = "Computer Science"
    
    try:
        requirements_data = get_requirements_with_prereqs(school, major)
        
        print(f"✅ Requirements data structure:")
        print(f"  Required courses: {len(requirements_data.get('required', []))}")
        print(f"  Gen ed groups: {len(requirements_data.get('genEds', []))}")
        print(f"  Elective groups: {len(requirements_data.get('chooseFrom', []))}")
        print(f"  Prerequisites: {len(requirements_data.get('prereqs', []))}")
        
        # Show some prerequisites
        prereqs = requirements_data.get('prereqs', [])
        if prereqs:
            print(f"  Sample prerequisites:")
            for prereq in prereqs[:3]:  # Show first 3
                print(f"    {prereq['course']} requires: {prereq['requires']}")
        
        return True
    except Exception as e:
        print(f"❌ Error in full requirements test: {e}")
        return False

def test_caching():
    """Test that caching works properly."""
    print("\nTesting prerequisite caching...")
    
    course_code = "CS0401"
    school = "University of Pittsburgh"
    
    try:
        # First call (should hit API)
        print("First call (should hit API)...")
        start_time = time.time()
        prereqs1 = search_course_prerequisites(course_code, school)
        first_call_time = time.time() - start_time
        
        # Second call (should hit cache)
        print("Second call (should hit cache)...")
        start_time = time.time()
        prereqs2 = search_course_prerequisites(course_code, school)
        second_call_time = time.time() - start_time
        
        if prereqs1 == prereqs2:
            print(f"✅ Cache working correctly")
            print(f"  First call time: {first_call_time:.2f}s")
            print(f"  Second call time: {second_call_time:.2f}s")
            print(f"  Results: {prereqs1}")
            return True
        else:
            print(f"❌ Cache not working - results differ")
            return False
            
    except Exception as e:
        print(f"❌ Error testing cache: {e}")
        return False

def main():
    """Run all prerequisite tests."""
    print("🧪 Testing Prerequisite Functionality")
    print("=" * 50)
    
    # Check if API key is set
    if not os.getenv("GEMINI_API_KEY"):
        print("❌ GEMINI_API_KEY not set. Please add it to your .env file.")
        return False
    
    import time
    
    tests = [
        test_single_prerequisite,
        test_batch_prerequisites,
        test_caching,
        test_full_requirements
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with exception: {e}")
            results.append(False)
    
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Prerequisites are working correctly.")
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
