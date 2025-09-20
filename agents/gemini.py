import os
from dotenv import load_dotenv
from google import genai
import requests
from typing import List, Dict, Optional

load_dotenv()

# Initialize the client with the API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set. Please add it to your .env file.")

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.0-flash" # todo: update to latest model

requirement_set_schema = {
  "type":"object",
  "properties":{
    "catalogYear":{"type":"string"},
    "required":{"type":"array","items":{"type":"string"}},
    "genEds":{"type":"array","items":{
      "type":"object",
      "properties":{"label":{"type":"string"},"count":{"type":"integer"},
                    "options":{"type":"array","items":{"type":"string"}}},
      "required":["label","count","options"]
    }},
    "chooseFrom":{"type":"array","items":{
      "type":"object",
      "properties":{"label":{"type":"string"},"count":{"type":"integer"},
                    "options":{"type":"array","items":{"type":"string"}}},
      "required":["label","count","options"]
    }},
    "minCredits":{"type":"integer"},
    "maxCredits":{"type":"integer"},
    "prereqs":{"type":"array","items":{
      "type":"object",
      "properties":{"course":{"type":"string"},
                    "requires":{"type":"array","items":{"type":"string"}}},
      "required":["course","requires"]
    }},
    "multiSemesterPrereqs":{"type":"array","items":{
      "type":"object",
      "properties":{"course":{"type":"string"},
                    "requires":{"type":"array","items":{"type":"string"}}},
      "required":["course","requires"]
    }}
  },
  "required":["required"]
}

preferences_schema = {
  "type":"object",
  "properties":{
    "noDays":{"type":"array","items":{"type":"string"}},
    "earliestStart":{"type":"string"},
    "latestEnd":{"type":"string"},
    "minCredits":{"type":"integer"},
    "maxCredits":{"type":"integer"},
    "skipCourses":{"type":"array","items":{"type":"string"}},
    "pinSections":{"type":"array","items":{"type":"string"}},
    "avoidGaps":{"type":"boolean"}
  }
}

def parse_preferences(utterance:str)->dict:
    resp = client.models.generate_content(
        model=MODEL,
        config={"response_mime_type":"application/json",
                "response_schema":preferences_schema},
        contents=[{"role":"user","parts":[{"text": utterance}]}]
    )
    return resp.parsed or {}

def search_course_prerequisites(course_code: str, school: str = "University of Pittsburgh") -> List[str]:
    """Search for course prerequisites using web search and AI parsing."""
    search_query = f"{school} {course_code} prerequisites course catalog requirements"
    
    try:
        # Use Gemini with web search to find prerequisites
        prompt = f"""Find the prerequisites for {course_code} at {school}. 
        Search the official course catalog or university website.
        Return ONLY a JSON array of course codes that are prerequisites for {course_code}.
        If no prerequisites are found, return an empty array [].
        Example: ["CS0401", "MATH0220"] or []
        
        Course code: {course_code}
        School: {school}"""
        
        resp = client.models.generate_content(
            model=MODEL,
            config={
                "response_mime_type": "application/json",
                "tools": [{"google_search": {}}]
            },
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        # Parse the response
        if resp.parsed:
            if isinstance(resp.parsed, list):
                return resp.parsed
            elif isinstance(resp.parsed, dict) and "prerequisites" in resp.parsed:
                return resp.parsed["prerequisites"]
        
        # Fallback: try to extract from text response
        if resp.text:
            import re
            # Look for course codes in the response
            course_pattern = r'\b[A-Z]{2,4}\d{3,4}\b'
            matches = re.findall(course_pattern, resp.text)
            return list(set(matches))  # Remove duplicates
        
        return []
        
    except Exception as e:
        print(f"Error searching for prerequisites for {course_code}: {e}")
        return []

def get_requirements_with_prereqs(school: str, major: str) -> dict:
    """Get requirements and parse prerequisites using web search."""
    # First get the basic requirements
    from services.requirements import get_requirements
    requirements = get_requirements(school, major)
    
    # For each required course, search for prerequisites
    prereqs = []
    for course in requirements.required:
        course_prereqs = search_course_prerequisites(course, school)
        if course_prereqs:
            prereqs.append({
                "course": course,
                "requires": course_prereqs
            })
    
    # Convert to dict and add prereqs
    req_dict = requirements.model_dump()
    req_dict["prereqs"] = prereqs
    
    return req_dict
