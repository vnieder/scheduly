from models.schemas import RequirementSet
from agents.gemini import client, MODEL, requirement_set_schema
import logging

logger = logging.getLogger(__name__)

def get_requirements(school: str, major: str) -> RequirementSet:
    """Dynamically fetch degree requirements using web search and AI parsing."""
    
    # Hardcoded fallback for Pitt Computer Science
    if school.lower() == "pitt" and major.lower() in ["computer science", "cs", "computer science major"]:
        logger.info(f"Using hardcoded requirements for Pitt {major}")
        return RequirementSet(
            catalogYear="2024-2025",
            required=[
                "CS0401",
                "CS0441", 
                "CS0445",
                "CS0447",
                "CS0449",
                "CS1501",
                "CS1550",
                "CS1621",
                "CS1650"
            ],
            genEds=[
                {
                    "label": "Writing Intensive",
                    "count": 1,
                    "options": ["ENGCMP0200", "ENGCMP0201", "ENGCMP0202"]
                },
                {
                    "label": "Literature",
                    "count": 1, 
                    "options": ["ENGLIT0630", "ENGLIT0580", "ENGLIT0625"]
                },
                {
                    "label": "History",
                    "count": 1,
                    "options": ["HIST0600", "HIST0100", "HIST0200"]
                },
                {
                    "label": "Social Science",
                    "count": 1,
                    "options": ["POLI0010", "PSY0010", "SOC0010"]
                },
                {
                    "label": "Natural Science",
                    "count": 1,
                    "options": ["CHEM0111", "PHYS0174", "BIOSC0150"]
                },
                {
                    "label": "Arts",
                    "count": 1,
                    "options": ["MUSIC0211", "THEA0080", "HAA0010"]
                },
                {
                    "label": "Philosophy",
                    "count": 1,
                    "options": ["PHIL0010", "PHIL0050", "PHIL0080"]
                }
            ],
            chooseFrom=[
                {
                    "label": "Upper Level CS Electives",
                    "count": 2,
                    "options": ["CS1622", "CS1632", "CS1640", "CS1651"]
                },
                {
                    "label": "Technical Electives", 
                    "count": 1,
                    "options": ["MATH0230", "STAT1000", "ASTRON0083"]
                }
            ],
            minCredits=12,
            maxCredits=18
        )
    
    # Create a comprehensive prompt for finding all degree requirements
    prompt = f"""Find the complete official degree requirements for {school} {major} program.

Search the university's official course catalog, academic bulletin, department website, or degree requirements page.

Look for:
1. Required courses for the {major} major
2. General education requirements (writing, literature, history, social science, natural science, arts, philosophy, etc.)
3. Elective requirements and options
4. Credit hour requirements
5. Prerequisite chains

Return a JSON object with this EXACT structure:
{{
    "catalogYear": "current academic year (e.g., 2024-2025)",
    "required": ["list of required course codes for the major"],
    "genEds": [
        {{
            "label": "category name (e.g., Writing Intensive, Literature, History)",
            "count": number_of_courses_required,
            "options": ["list of specific course codes that satisfy this requirement"]
        }}
    ],
    "chooseFrom": [
        {{
            "label": "elective category name (e.g., Upper Level Electives, Technical Electives)",
            "count": number_of_courses_required,
            "options": ["list of specific course codes to choose from"]
        }}
    ],
    "minCredits": minimum_credits_per_semester,
    "maxCredits": maximum_credits_per_semester
}}

CRITICAL REQUIREMENTS:
- Find SPECIFIC course codes (e.g., CS0401, MATH0220, ENGCMP0200)
- Include REAL course options for each gen ed category
- Include REAL elective options with specific course codes
- Use exact course codes as they appear on the university website
- If you cannot find specific course codes, return empty arrays
- Focus on undergraduate degree requirements only
- Search multiple university web pages if needed

School: {school}
Major: {major}"""
    
    try:
        resp = client.models.generate_content(
            model=MODEL,
            config={
                "response_mime_type": "application/json",
                "response_schema": requirement_set_schema,
                "tools": [{"google_search": {}}]
            },
            contents=[{"role": "user", "parts": [{"text": prompt}]}]
        )
        
        # Parse the response
        data = resp.parsed or {"required": []}
        
        # Validate and clean the data
        if not isinstance(data, dict):
            logger.warning(f"Invalid response format for {school} {major}")
            data = {"required": []}
        
        # Ensure required fields exist
        if "required" not in data:
            data["required"] = []
        if "genEds" not in data:
            data["genEds"] = []
        if "chooseFrom" not in data:
            data["chooseFrom"] = []
            
        logger.info(f"Successfully fetched requirements for {school} {major}")
        return RequirementSet(**data)
        
    except Exception as e:
        logger.error(f"Error fetching requirements for {school} {major}: {e}")
        # Return minimal requirements structure
        return RequirementSet(
            catalogYear="2024-2025",
            required=[],
            genEds=[],
            chooseFrom=[],
            minCredits=12,
            maxCredits=18
        )
