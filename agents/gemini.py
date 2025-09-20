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
    try:
        # Use Gemini with web search to find prerequisites
        prompt = f"""Find the prerequisites for {course_code} at {school}. 

Search the official course catalog, academic bulletin, or department website for {school}.

Look for:
1. Prerequisite courses required before taking {course_code}
2. Corequisite courses that must be taken at the same time
3. Any other course requirements

Return ONLY a JSON array of course codes that are prerequisites for {course_code}.
If no prerequisites are found, return an empty array [].

Examples of what to look for:
- "Prerequisites: CS0401, MATH0220"
- "Must have completed CS0445"
- "Corequisite: MATH0230"

Course code: {course_code}
School: {school}

Return format: ["CS0401", "MATH0220"] or []"""
        
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
            # Filter out the course code itself
            filtered_matches = [match for match in matches if match != course_code]
            return list(set(filtered_matches))  # Remove duplicates
        
        return []
        
    except Exception as e:
        print(f"Error searching for prerequisites for {course_code}: {e}")
        return []

def search_course_catalog(school: str, subject: str = None, course_code: str = None) -> List[Dict]:
    """Search for courses in the university catalog using web search."""
    if course_code:
        search_query = f"{school} {course_code} course catalog description"
    elif subject:
        search_query = f"{school} {subject} courses catalog list"
    else:
        search_query = f"{school} course catalog"
    
    try:
        prompt = f"""Search for course information in the {school} course catalog.
        
        {'Course: ' + course_code if course_code else ''}
        {'Subject: ' + subject if subject else ''}
        
        Return a JSON array of course objects with this structure:
        [
            {{
                "code": "course code (e.g., CS0401)",
                "title": "course title",
                "credits": number_of_credits,
                "description": "brief course description",
                "prerequisites": ["list of prerequisite course codes"],
                "offered": ["semesters when offered (e.g., Fall, Spring)"]
            }}
        ]
        
        If searching for a specific course, return one object. If searching for a subject, return multiple courses."""
        
        resp = client.models.generate_content(
            model=MODEL,
            config={
                "response_mime_type": "application/json",
                "tools": [{"google_search": {}}]
            },
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        if resp.parsed:
            if isinstance(resp.parsed, list):
                return resp.parsed
            elif isinstance(resp.parsed, dict):
                return [resp.parsed]
        
        return []
        
    except Exception as e:
        print(f"Error searching course catalog: {e}")
        return []

def search_general_education_requirements(school: str) -> List[Dict]:
    """Search for general education requirements at a university."""
    try:
        prompt = f"""Find the general education (gen ed) requirements for {school}.
        
        Search the university's official academic bulletin or general education requirements page.
        
        Return a JSON array of general education categories:
        [
            {{
                "label": "category name (e.g., Writing Intensive, Literature, History)",
                "description": "brief description of what this category covers",
                "count": number_of_courses_required,
                "options": ["list of course codes that satisfy this requirement"],
                "credits": number_of_credits_required
            }}
        ]
        
        Include all major gen ed categories like:
        - Writing/Composition
        - Literature/Humanities
        - History/Social Sciences
        - Natural Sciences
        - Mathematics
        - Arts
        - Philosophy/Ethics
        - Foreign Language (if required)
        - Diversity/Global Studies (if required)"""
        
        resp = client.models.generate_content(
            model=MODEL,
            config={
                "response_mime_type": "application/json",
                "tools": [{"google_search": {}}]
            },
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        if resp.parsed and isinstance(resp.parsed, list):
            return resp.parsed
        
        return []
        
    except Exception as e:
        print(f"Error searching gen ed requirements: {e}")
        return []

def search_major_electives(school: str, major: str) -> List[Dict]:
    """Search for major elective options."""
    try:
        prompt = f"""Find elective course options for {school} {major} major.
        
        Search the department website or course catalog for elective requirements.
        
        Return a JSON array of elective categories:
        [
            {{
                "label": "elective category name (e.g., Upper Level CS Electives, Technical Electives)",
                "description": "brief description of this elective category",
                "count": number_of_courses_required,
                "options": ["list of course codes to choose from"],
                "credits": number_of_credits_required
            }}
        ]"""
        
        resp = client.models.generate_content(
            model=MODEL,
            config={
                "response_mime_type": "application/json",
                "tools": [{"google_search": {}}]
            },
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        if resp.parsed and isinstance(resp.parsed, list):
            return resp.parsed
        
        return []
        
    except Exception as e:
        print(f"Error searching major electives: {e}")
        return []

def get_comprehensive_course_info(school: str, query: str) -> dict:
    """Get comprehensive course information using web search and AI parsing."""
    try:
        prompt = f"""Find comprehensive information about courses at {school} based on this query: {query}
        
        This could be:
        - A specific course code (e.g., CS0401)
        - A subject area (e.g., Computer Science courses)
        - General education requirements
        - Major requirements for a specific program
        - Prerequisites for courses
        - Course descriptions and details
        
        Search the university's official course catalog, academic bulletin, or department websites.
        
        Return a JSON object with this structure:
        {{
            "query": "{query}",
            "school": "{school}",
            "courses": [
                {{
                    "code": "course code",
                    "title": "course title",
                    "credits": number_of_credits,
                    "description": "detailed course description",
                    "prerequisites": ["list of prerequisite course codes"],
                    "offered": ["semesters when offered"],
                    "instructor": "typical instructor",
                    "department": "department name",
                    "url": "course catalog URL if found"
                }}
            ],
            "requirements": {{
                "genEds": [
                    {{
                        "label": "category name",
                        "count": number_required,
                        "options": ["course codes that satisfy this requirement"]
                    }}
                ],
                "electives": [
                    {{
                        "label": "elective category",
                        "count": number_required,
                        "options": ["course codes to choose from"]
                    }}
                ]
            }},
            "prerequisites": [
                {{
                    "course": "course code",
                    "requires": ["prerequisite course codes"]
                }}
            ],
            "sources": ["list of URLs or sources used"]
        }}
        
        Include as much relevant information as possible based on the query."""
        
        resp = client.models.generate_content(
            model=MODEL,
            config={
                "response_mime_type": "application/json",
                "tools": [{"google_search": {}}]
            },
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        if resp.parsed and isinstance(resp.parsed, dict):
            return resp.parsed
        
        # Fallback structure
        return {
            "query": query,
            "school": school,
            "courses": [],
            "requirements": {"genEds": [], "electives": []},
            "prerequisites": [],
            "sources": []
        }
        
    except Exception as e:
        print(f"Error getting comprehensive course info: {e}")
        return {
            "query": query,
            "school": school,
            "courses": [],
            "requirements": {"genEds": [], "electives": []},
            "prerequisites": [],
            "sources": []
        }

def get_requirements_with_prereqs(school: str, major: str) -> dict:
    """Get requirements and parse prerequisites using pure web search - no fallbacks."""
    # First get the basic requirements
    from services.requirements import get_requirements
    requirements = get_requirements(school, major)
    
    # Clean course codes (remove spaces and extract just the course code part)
    cleaned_required = []
    for course in requirements.required:
        # Handle formats like "CS0401-INTERMEDIATEPROGRAMMINGUSINGJAVA" or "CS0401"
        if "-" in course:
            cleaned_course = course.split("-")[0]  # Take only the part before the dash
        else:
            cleaned_course = course.replace(" ", "")
        cleaned_required.append(cleaned_course)
    
    # Clean gen ed options (no fallbacks)
    cleaned_gen_eds = []
    for gen_ed in requirements.genEds:
        cleaned_options = []
        for option in gen_ed.options:
            # Handle formats like "ENGCMP0200-WRITINGINTENSIVE" or "ENGCMP0200"
            if "-" in option:
                cleaned_option = option.split("-")[0]  # Take only the part before the dash
            else:
                cleaned_option = option.replace(" ", "")
            cleaned_options.append(cleaned_option)
        
        cleaned_gen_eds.append({
            "label": gen_ed.label,
            "count": gen_ed.count,
            "options": cleaned_options
        })
    
    # Clean elective options
    cleaned_choose_from = []
    for choice in requirements.chooseFrom:
        cleaned_options = []
        for option in choice.options:
            # Handle formats like "CS1621-COMPUTERARCHITECTURE" or "CS1621"
            if "-" in option:
                cleaned_option = option.split("-")[0]  # Take only the part before the dash
            else:
                cleaned_option = option.replace(" ", "")
            cleaned_options.append(cleaned_option)
        
        cleaned_choose_from.append({
            "label": choice.label,
            "count": choice.count,
            "options": cleaned_options
        })
    
    # Skip prerequisite search for now to avoid API rate limits
    # TODO: Implement batch prerequisite search or caching
    prereqs = []
    multi_semester_prereqs = []
    
    # Convert to dict and add cleaned data
    req_dict = requirements.model_dump()
    req_dict["required"] = cleaned_required
    req_dict["genEds"] = cleaned_gen_eds
    req_dict["chooseFrom"] = cleaned_choose_from
    req_dict["prereqs"] = prereqs
    req_dict["multiSemesterPrereqs"] = multi_semester_prereqs
    
    return req_dict

def search_university_courses(school: str, filters: dict = None) -> List[Dict]:
    """Search for courses at a university with optional filters."""
    try:
        # Build search query based on filters
        query_parts = [school]
        
        if filters:
            if filters.get('subject'):
                query_parts.append(filters['subject'] + " courses")
            if filters.get('level'):
                query_parts.append(filters['level'] + " level")
            if filters.get('credits'):
                query_parts.append(f"{filters['credits']} credits")
            if filters.get('semester'):
                query_parts.append(filters['semester'] + " semester")
        
        search_query = " ".join(query_parts)
        
        prompt = f"""Find courses at {school} matching these criteria:
        
        Search Query: {search_query}
        Filters: {filters or 'None'}
        
        Search the university's course catalog or schedule.
        
        Return a JSON array of course objects:
        [
            {{
                "code": "course code",
                "title": "course title",
                "credits": number_of_credits,
                "description": "course description",
                "prerequisites": ["prerequisite course codes"],
                "offered": ["semesters offered"],
                "instructor": "instructor name",
                "department": "department",
                "level": "undergraduate/graduate",
                "url": "course URL if available"
            }}
        ]
        
        Return as many relevant courses as possible."""
        
        resp = client.models.generate_content(
            model=MODEL,
            config={
                "response_mime_type": "application/json",
                "tools": [{"google_search": {}}]
            },
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        if resp.parsed and isinstance(resp.parsed, list):
            return resp.parsed
        
        return []
        
    except Exception as e:
        print(f"Error searching university courses: {e}")
        return []
