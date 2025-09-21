from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, JSONResponse
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import logging
import os
from datetime import datetime, timedelta
import json
from src.models.schemas import RequirementSet, Preferences, SchedulePlan, Section, Prereq
from src.services.requirements.requirements import get_requirements
from src.services.catalog.pitt_catalog import get_sections
from src.services.schedule.solver import build_schedule
from src.services.requirements.terms import to_term_code
from src.agents.gemini import parse_preferences, get_requirements_with_prereqs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scheduly Backend")

# Add CORS middleware - Allow all origins to bypass Railway restrictions
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using wildcard
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],  # Allow all headers
    expose_headers=["*"],  # Expose all headers
)

# Custom response function that always includes CORS headers
def cors_response(data: dict, status_code: int = 200, origin: str = None):
    """Create a response with proper CORS headers"""
    headers = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Allow-Credentials": "false",
        "Access-Control-Expose-Headers": "*"
    }
    return JSONResponse(content=data, status_code=status_code, headers=headers)

# Add custom middleware to force CORS headers (override Railway's CORS)
@app.middleware("http")
async def force_cors_headers(request: Request, call_next):
    response = await call_next(request)
    
    # Force CORS headers for all origins
    origin = request.headers.get("origin", "*")
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"
    response.headers["Access-Control-Allow-Credentials"] = "false"
    response.headers["Access-Control-Expose-Headers"] = "*"
    
    return response

# Configuration from environment variables
DEFAULT_TERM = os.getenv("DEFAULT_TERM", "2251")
DEFAULT_SCHOOL = os.getenv("DEFAULT_SCHOOL", "Pitt")
MAX_COURSES_PER_SEMESTER = int(os.getenv("MAX_COURSES_PER_SEMESTER", "6"))
MAX_COURSE_SELECTION = int(os.getenv("MAX_COURSE_SELECTION", "10"))
SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))
# Dual mode configuration
APP_MODE = os.getenv("APP_MODE", "development").lower()  # "development" or "production"
DEVELOPMENT_MODE = APP_MODE == "development"
PRODUCTION_MODE = APP_MODE == "production"

# Legacy support: If USE_AI_PREREQUISITES is set, override APP_MODE
LEGACY_USE_AI_PREREQUISITES = os.getenv("USE_AI_PREREQUISITES", "").lower()
if LEGACY_USE_AI_PREREQUISITES == "true":
    APP_MODE = "production"
    DEVELOPMENT_MODE = False
    PRODUCTION_MODE = True
    logger.warning("USE_AI_PREREQUISITES=true detected. This is deprecated. Use APP_MODE=production instead.")
elif LEGACY_USE_AI_PREREQUISITES == "false":
    APP_MODE = "development"
    DEVELOPMENT_MODE = True
    PRODUCTION_MODE = False
    logger.warning("USE_AI_PREREQUISITES=false detected. This is deprecated. Use APP_MODE=development instead.")

# Session storage using new backend system
from src.services.storage.session_manager import session_manager, get_session_storage
from src.services.storage.session_storage import SessionStorage, SessionNotFoundError as StorageSessionNotFoundError


class BuildPayload(BaseModel):
    school: str = DEFAULT_SCHOOL
    major: str
    term: Optional[str] = DEFAULT_TERM
    utterance: Optional[str] = ""

class OptimizePayload(BaseModel):
    session_id: str
    utterance: str

class SectionsPayload(BaseModel):
    term: str
    course_codes: List[str]

# Removed SemesterPlanPayload - multi-semester planning out of scope

# Custom exception classes for better error handling
class SessionNotFoundError(HTTPException):
    def __init__(self, session_id: str):
        super().__init__(status_code=404, detail=f"Session {session_id} not found or expired")

class InvalidTermError(HTTPException):
    def __init__(self, term: str):
        super().__init__(status_code=400, detail=f"Invalid term format: {term}. Expected format: YYMM (e.g., 2251 for Fall 2025)")

class InvalidSchoolError(HTTPException):
    def __init__(self, school: str):
        if DEVELOPMENT_MODE:
            super().__init__(status_code=400, detail=f"School '{school}' not supported in development mode. Currently only supports: {DEFAULT_SCHOOL}. Set APP_MODE=production for multi-university support.")
        else:
            super().__init__(status_code=400, detail=f"School '{school}' not supported. Please check the school name and try again.")

class AIServiceError(HTTPException):
    def __init__(self, service: str, error: str):
        super().__init__(status_code=503, detail=f"AI service '{service}' error: {error}")

class CatalogServiceError(HTTPException):
    def __init__(self, error: str):
        super().__init__(status_code=503, detail=f"Course catalog service error: {error}")

def validate_term(term: str) -> bool:
    """Validate term format (YYMM)."""
    if not term or len(term) != 4:
        return False
    try:
        year = int(term[:2])
        semester_code = int(term[2:])
        # Allow terms like 2251 (Fall 2025), 2244 (Spring 2025), 2257 (Summer 2025)
        # Semester codes: 44=Spring, 51=Fall, 57=Summer
        return 20 <= year <= 30 and semester_code in [44, 51, 57]
    except ValueError:
        return False

def validate_school(school: str) -> bool:
    """Validate school is supported."""
    if DEVELOPMENT_MODE:
        # In development mode, only support Pitt for hardcoded data
        return school.lower() == DEFAULT_SCHOOL.lower()
    else:
        # In production mode, support any school (AI will handle requirements)
        return True

def validate_course_codes(course_codes: List[str]) -> List[str]:
    """Validate and clean course codes."""
    validated = []
    for code in course_codes:
        # Clean course code - handle formats like "PHYS 0475 - Introduction to Physics" or "CS0401"
        clean_code = code.strip().upper()
        
        # Extract just the course code part (before any dash or description)
        if "-" in clean_code:
            clean_code = clean_code.split("-")[0].strip()
        
        # Remove spaces to get format like "PHYS0475" or "CS0401"
        clean_code = clean_code.replace(" ", "")
        
        # Basic validation: should be alphanumeric and reasonable length
        if clean_code and len(clean_code) >= 3 and len(clean_code) <= 10:
            validated.append(clean_code)
    return validated

@app.get("/health")
def health_check():
    return {
        "ok": True,
        "mode": APP_MODE,
        "development_mode": DEVELOPMENT_MODE,
        "production_mode": PRODUCTION_MODE,
        "legacy_mode": LEGACY_USE_AI_PREREQUISITES != "",
        "supported_schools": ["Pitt"] if DEVELOPMENT_MODE else ["Any university (AI-powered)"],
        "features": {
            "hardcoded_requirements": DEVELOPMENT_MODE,
            "ai_requirements": PRODUCTION_MODE,
            "ai_prerequisites": PRODUCTION_MODE,
            "multi_university": PRODUCTION_MODE
        }
    }

@app.get("/cors-test")
def cors_test():
    """Simple endpoint to test CORS configuration"""
    return {
        "message": "CORS is working!",
        "timestamp": datetime.now().isoformat(),
        "cors_policy": "Allow all origins (*)"
    }

@app.get("/cors-debug")
def cors_debug(request: Request):
    """Debug endpoint to check CORS headers"""
    return {
        "origin": request.headers.get("origin"),
        "user_agent": request.headers.get("user-agent"),
        "cors_policy": "Allow all origins (*)",
        "headers": dict(request.headers)
    }

@app.get("/cors-simple")
async def cors_simple(request: Request):
    """Simple endpoint that manually sets CORS headers"""
    origin = request.headers.get("origin")
    
    # Create response with manual CORS headers
    response_data = {
        "message": "CORS test successful",
        "origin": origin,
        "timestamp": datetime.now().isoformat()
    }
    
    response = Response(
        content=json.dumps(response_data),
        media_type="application/json",
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "false",
        }
    )
    
    return response

@app.options("/{path:path}")
async def options_handler(path: str):
    """Handle all OPTIONS requests for CORS preflight"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Allow-Credentials": "false",
            "Access-Control-Max-Age": "86400"
        }
    )

# CORS Proxy endpoint to bypass Railway's platform CORS
@app.post("/proxy/build")
async def proxy_build_endpoint(p: BuildPayload):
    """Proxy endpoint that bypasses Railway's CORS restrictions"""
    try:
        # Call the actual build endpoint internally
        result = await build_schedule_endpoint(p)
        return cors_response(result)
    except Exception as e:
        logger.error(f"Proxy build error: {e}")
        return cors_response({"error": str(e)}, 500)

@app.post("/proxy/optimize")
async def proxy_optimize_endpoint(p: OptimizePayload):
    """Proxy endpoint that bypasses Railway's CORS restrictions"""
    try:
        # Call the actual optimize endpoint internally
        result = await optimize_schedule(p)
        return cors_response(result)
    except Exception as e:
        logger.error(f"Proxy optimize error: {e}")
        return cors_response({"error": str(e)}, 500)

@app.post("/build")
async def build_schedule_endpoint(p: BuildPayload):
    try:
        # Validate inputs
        if not validate_term(p.term):
            raise InvalidTermError(p.term)
        
        if not validate_school(p.school):
            raise InvalidSchoolError(p.school)
        
        if not p.major or len(p.major.strip()) < 2:
            raise HTTPException(status_code=400, detail="Major must be at least 2 characters long")
        
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        logger.info(f"Building schedule for {p.school} {p.major} term {p.term}")
        
        # Get requirements based on mode
        try:
            if DEVELOPMENT_MODE:
                logger.info(f"Development mode: Using hardcoded requirements for {p.school} {p.major}")
                requirements = get_requirements(p.school, p.major)
            else:
                logger.info(f"Production mode: Using AI-generated requirements for {p.school} {p.major}")
                requirements = get_requirements(p.school, p.major)
        except Exception as e:
            logger.error(f"Failed to get requirements: {e}")
            raise AIServiceError("Requirements", str(e))
        
        # Choose courses for the term - mix of major requirements and gen eds
        all_courses = requirements.required.copy()
        
        # Add some general education courses
        for gen_ed_group in requirements.genEds:
            all_courses.extend(gen_ed_group.options[:gen_ed_group.count])
        
        # Add some major electives
        for choice_group in requirements.chooseFrom:
            all_courses.extend(choice_group.options[:choice_group.count])
        
        # Select up to MAX_COURSE_SELECTION courses to include gen eds
        course_codes = validate_course_codes(all_courses[:MAX_COURSE_SELECTION])
        
        if not course_codes:
            raise HTTPException(status_code=400, detail="No valid course codes found for the specified major")
        
        # Get sections for these courses
        try:
            sections = get_sections(p.term, course_codes)
            if not sections:
                raise HTTPException(status_code=400, detail="No sections found for any of the required courses in the specified term")
        except Exception as e:
            logger.error(f"Failed to get sections: {e}")
            raise CatalogServiceError(str(e))
        
        # Parse preferences based on mode
        try:
            if DEVELOPMENT_MODE and not p.utterance:
                # In development mode, use default preferences if no utterance
                preferences = Preferences()
                logger.info("Development mode: Using default preferences")
            else:
                # Use AI to parse preferences (both modes support this)
                prefs_data = parse_preferences(p.utterance) if p.utterance else {}
                preferences = Preferences(**prefs_data)
                logger.info(f"Parsed preferences: {prefs_data}")
        except Exception as e:
            logger.error(f"Failed to parse preferences: {e}")
            if DEVELOPMENT_MODE:
                # In development mode, fall back to default preferences
                preferences = Preferences()
                logger.warning("Development mode: Falling back to default preferences")
            else:
                raise AIServiceError("Gemini", str(e))
        
        # Add prerequisites based on mode
        prereqs = []
        multi_semester_prereqs = []
        
        if DEVELOPMENT_MODE:
            # Development mode: Use hardcoded prerequisites for Pitt CS
            if p.school.lower() == "pitt" and p.major.lower() in ["computer science", "cs", "computer science major"]:
                from src.models.schemas import Prereq
                multi_semester_prereqs = [
                    Prereq(course="CS1550", requires=["CS0449", "CS0447"]),
                    Prereq(course="CS1501", requires=["CS0441", "CS0445"]),
                    Prereq(course="CS0449", requires=["CS0441"]),
                    Prereq(course="CS0447", requires=["CS0441"]),
                    Prereq(course="CS0445", requires=["CS0441"]),
                ]
                logger.info("Development mode: Using hardcoded prerequisites for Pitt CS")
            else:
                logger.info("Development mode: No hardcoded prerequisites available for this school/major")
        else:
            # Production mode: Use AI to search for prerequisites
            try:
                from src.agents.gemini import get_requirements_with_prereqs
                requirements_data = get_requirements_with_prereqs(p.school, p.major)
                prereqs_data = requirements_data.get("prereqs", [])
                multi_semester_prereqs_data = requirements_data.get("multiSemesterPrereqs", [])
                from src.models.schemas import Prereq
                prereqs = [Prereq(**p) for p in prereqs_data]
                multi_semester_prereqs = [Prereq(**p) for p in multi_semester_prereqs_data]
                logger.info("Production mode: Using AI-searched prerequisites")
            except Exception as e:
                logger.warning(f"AI prerequisite search failed, using empty prerequisites: {e}")
                prereqs = []
                multi_semester_prereqs = []
        
        # Build initial schedule with prerequisites and available courses
        # For first semester, no completed courses yet
        completed_courses = []
        plan = build_schedule(p.term, sections, preferences, prereqs, course_codes, multi_semester_prereqs, completed_courses)
        
        # Merge prerequisites into requirements object
        requirements.prereqs = prereqs
        requirements.multiSemesterPrereqs = multi_semester_prereqs
        
        # Store session state with new storage backend
        storage = await get_session_storage()
        session_data = {
            "school": p.school,
            "major": p.major,
            "term": p.term,
            "preferences": preferences.model_dump(),
            "courses": course_codes,
            "prereqs": [prereq.model_dump() for prereq in prereqs],
            "multiSemesterPrereqs": [prereq.model_dump() for prereq in multi_semester_prereqs],
            "completedCourses": completed_courses,
            "last_plan": plan.model_dump()
        }
        
        # Create session in storage backend
        await storage.create_session(session_id, session_data)
        
        logger.info(f"Successfully created session {session_id} with {len(plan.sections)} sections")
        
        return {
            "session_id": session_id,
            "requirements": requirements.model_dump(),
            "plan": plan.model_dump()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /build: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/optimize")
async def optimize_schedule(p: OptimizePayload):
    try:
        # Validate session exists and get session data
        storage = await get_session_storage()
        session_data_obj = await storage.get_session(p.session_id)
        if session_data_obj is None:
            raise SessionNotFoundError(p.session_id)
        
        session_data = session_data_obj.data
        
        if not p.utterance or not p.utterance.strip():
            raise HTTPException(status_code=400, detail="Utterance cannot be empty for optimization")
        
        logger.info(f"Optimizing session {p.session_id} with utterance: {p.utterance}")
        
        # Parse new preferences
        try:
            new_prefs_data = parse_preferences(p.utterance)
        except Exception as e:
            logger.error(f"Failed to parse preferences: {e}")
            raise AIServiceError("Gemini", str(e))
        
        # Merge with existing preferences
        existing_prefs = session_data["preferences"]
        for key, value in new_prefs_data.items():
            if value is not None:
                if key in ["noDays", "skipCourses", "pinSections"] and isinstance(value, list):
                    # Merge lists
                    existing_prefs[key] = list(set(existing_prefs.get(key, []) + value))
                else:
                    existing_prefs[key] = value
        
        preferences = Preferences(**existing_prefs)
        
        # Re-fetch sections for the same courses
        try:
            sections = get_sections(session_data["term"], session_data["courses"])
            if not sections:
                raise HTTPException(status_code=400, detail="No sections found for the courses in this session. The course offerings may have changed.")
        except Exception as e:
            logger.error(f"Failed to get sections: {e}")
            raise CatalogServiceError(str(e))
        
        # Get prerequisites from session
        prereqs_data = session_data.get("prereqs", [])
        prereqs = [Prereq(**p) for p in prereqs_data] if prereqs_data else []
        
        # Build new schedule with updated preferences and prerequisites
        available_courses = session_data.get("courses", [])
        multi_semester_prereqs_data = session_data.get("multiSemesterPrereqs", [])
        multi_semester_prereqs = [Prereq(**p) for p in multi_semester_prereqs_data] if multi_semester_prereqs_data else []
        completed_courses = session_data.get("completedCourses", [])
        plan = build_schedule(session_data["term"], sections, preferences, prereqs, available_courses, multi_semester_prereqs, completed_courses)
        
        # Update session state
        session_data["preferences"] = preferences.model_dump()
        session_data["last_plan"] = plan.model_dump()
        
        # Update session in storage backend
        await storage.update_session(p.session_id, session_data)
        
        logger.info(f"Successfully optimized session {p.session_id}")
        
        return {"plan": plan.model_dump()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /optimize: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/catalog/sections")
def catalog_sections(p: SectionsPayload):
    try:
        # Validate inputs
        if not validate_term(p.term):
            raise InvalidTermError(p.term)
        
        if not p.course_codes or len(p.course_codes) == 0:
            raise HTTPException(status_code=400, detail="Course codes list cannot be empty")
        
        # Validate and clean course codes
        validated_codes = validate_course_codes(p.course_codes)
        if not validated_codes:
            raise HTTPException(status_code=400, detail="No valid course codes provided")
        
        logger.info(f"Fetching sections for term {p.term}, courses: {validated_codes}")
        
        try:
            secs = get_sections(p.term, validated_codes)
        except Exception as e:
            logger.error(f"Failed to get sections: {e}")
            raise CatalogServiceError(str(e))
        
        logger.info(f"Found {len(secs)} sections for {len(validated_codes)} courses")
        
        return {"sections": [s.model_dump() for s in secs]}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in /catalog/sections: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize session storage on startup."""
    try:
        session_manager.initialize_storage()
        logger.info("Session storage initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize session storage: {e}")
        logger.warning("Continuing without session storage - using memory fallback")
        # Don't raise - allow app to start with memory storage fallback

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up session storage on shutdown."""
    try:
        await session_manager.close()
        logger.info("Session storage connections closed")
    except Exception as e:
        logger.error(f"Error closing session storage: {e}")

