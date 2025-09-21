from src.models.schemas import RequirementSet
import logging

# Conditional imports for production mode only
try:
    from src.agents.gemini import client, MODEL, requirement_set_schema
    GEMINI_AVAILABLE = True
except (ImportError, ValueError) as e:
    # GEMINI_API_KEY not set or other import error
    GEMINI_AVAILABLE = False
    client = None
    MODEL = None
    requirement_set_schema = None

logger = logging.getLogger(__name__)

def _get_generic_requirements(school: str, major: str) -> RequirementSet:
    """Generate generic requirements template for any school/major combination."""
    # Create a generic template that works for any school/major
    major_code = major[:2].upper() if len(major) >= 2 else "CS"
    
    return RequirementSet(
        catalogYear="2024-2025",
        required=[
            f"{major_code}101",  # Intro course
            f"{major_code}201",  # Intermediate course
            f"{major_code}301",  # Advanced course
            f"{major_code}401",  # Capstone course
        ],
        genEds=[
            {
                "label": "Writing Intensive",
                "count": 1,
                "options": ["WRIT100", "WRIT101", "WRIT102"]
            },
            {
                "label": "Literature",
                "count": 1, 
                "options": ["LIT100", "LIT101", "LIT102"]
            },
            {
                "label": "History",
                "count": 1,
                "options": ["HIST100", "HIST101", "HIST102"]
            },
            {
                "label": "Social Science",
                "count": 1,
                "options": ["SOC100", "SOC101", "SOC102"]
            },
            {
                "label": "Natural Science",
                "count": 1,
                "options": ["SCI100", "SCI101", "SCI102"]
            },
            {
                "label": "Arts",
                "count": 1,
                "options": ["ART100", "ART101", "ART102"]
            },
            {
                "label": "Philosophy",
                "count": 1,
                "options": ["PHIL100", "PHIL101", "PHIL102"]
            }
        ],
        chooseFrom=[
            {
                "label": f"Upper Level {major_code} Electives",
                "count": 2,
                "options": [f"{major_code}300", f"{major_code}301", f"{major_code}302", f"{major_code}303"]
            },
            {
                "label": "Technical Electives", 
                "count": 1,
                "options": ["MATH200", "STAT200", "PHYS200"]
            }
        ],
        minCredits=12,
        maxCredits=18
    )

def get_requirements(school: str, major: str) -> RequirementSet:
    """Dynamically fetch degree requirements using web search and AI parsing."""
    
    # Check if we're in development mode
    import os
    APP_MODE = os.getenv("APP_MODE", "development").lower()
    DEVELOPMENT_MODE = APP_MODE == "development"
    
    # Generic template for development mode (any school/major)
    if DEVELOPMENT_MODE:
        logger.info(f"Using generic template for {school} {major} (development mode)")
        return _get_generic_requirements(school, major)
    
    # Production mode: Use AI to fetch real requirements
    if not GEMINI_AVAILABLE:
        logger.warning(f"GEMINI_API_KEY not available, falling back to generic requirements for {school} {major}")
        return _get_generic_requirements(school, major)
    
    logger.info(f"Using AI to fetch requirements for {school} {major}")
    
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
