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
from src.services.catalog.pitt_catalog import get_sections as get_pitt_sections
from src.services.catalog.generic_catalog import get_sections as get_generic_sections
from src.services.schedule.solver import build_schedule
from src.services.requirements.terms import to_term_code
from src.services.auth.auth0_middleware import get_current_user, get_optional_user
from src.services.storage.user_schedule_storage import UserScheduleStorage
# Conditional imports for production mode only
try:
    from src.agents.gemini import parse_preferences, get_requirements_with_prereqs
    GEMINI_AVAILABLE = True
except (ImportError, ValueError) as e:
    # GEMINI_API_KEY not set or other import error
    GEMINI_AVAILABLE = False
    parse_preferences = None
    get_requirements_with_prereqs = None

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

class SaveSchedulePayload(BaseModel):
    session_id: str
    title: Optional[str] = None

class UpdateSchedulePayload(BaseModel):
    title: Optional[str] = None
    is_favorite: Optional[bool] = None

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
    # Support any school in both development and production modes
    # Development mode will use generic templates, production mode will use AI
    return bool(school and len(school.strip()) >= 2)

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

def _get_generic_prerequisites(major: str) -> List:
    """Generate generic prerequisites template for any major."""
    from src.models.schemas import Prereq
    major_code = major[:2].upper() if len(major) >= 2 else "CS"
    
    return [
        Prereq(course=f"{major_code}401", requires=[f"{major_code}301"]),
        Prereq(course=f"{major_code}301", requires=[f"{major_code}201"]),
        Prereq(course=f"{major_code}201", requires=[f"{major_code}101"]),
        Prereq(course="MATH200", requires=["MATH100"]),
        Prereq(course="STAT200", requires=["MATH100"]),
    ]

def get_sections(term: str, course_codes: List[str], include_recitations: bool = False):
    """Choose the appropriate sections provider based on mode and school."""
    if DEVELOPMENT_MODE:
        # In development mode, use generic sections for any school
        return get_generic_sections(term, course_codes, include_recitations)
    else:
        # In production mode, use Pitt catalog for Pitt, generic for others
        # For now, use generic for all schools in production mode
        # This could be enhanced to support multiple real catalog APIs
        return get_generic_sections(term, course_codes, include_recitations)

@app.get("/health")
def health_check():
    return {
        "ok": True,
        "mode": APP_MODE,
        "development_mode": DEVELOPMENT_MODE,
        "production_mode": PRODUCTION_MODE,
        "legacy_mode": LEGACY_USE_AI_PREREQUISITES != "",
        "supported_schools": ["Any university"] if DEVELOPMENT_MODE else ["Any university (AI-powered)"],
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
                if GEMINI_AVAILABLE and parse_preferences:
                    prefs_data = parse_preferences(p.utterance) if p.utterance else {}
                else:
                    logger.warning("GEMINI_API_KEY not available, using default preferences")
                    prefs_data = {}
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
            # Development mode: Use generic prerequisites template
            from src.models.schemas import Prereq
            multi_semester_prereqs = _get_generic_prerequisites(p.major)
            logger.info(f"Development mode: Using generic prerequisites for {p.school} {p.major}")
        else:
            # Production mode: Use AI to search for prerequisites
            try:
                if GEMINI_AVAILABLE and get_requirements_with_prereqs:
                    requirements_data = get_requirements_with_prereqs(p.school, p.major)
                    prereqs_data = requirements_data.get("prereqs", [])
                    multi_semester_prereqs_data = requirements_data.get("multiSemesterPrereqs", [])
                else:
                    logger.warning("GEMINI_API_KEY not available, using generic prerequisites")
                    prereqs_data = []
                    multi_semester_prereqs_data = _get_generic_prerequisites(p.major)
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
            if GEMINI_AVAILABLE and parse_preferences:
                new_prefs_data = parse_preferences(p.utterance)
            else:
                logger.warning("GEMINI_API_KEY not available, using default preferences")
                new_prefs_data = {}
        except Exception as e:
            logger.error(f"Failed to parse preferences: {e}")
            if GEMINI_AVAILABLE:
                raise AIServiceError("Gemini", str(e))
            else:
                new_prefs_data = {}
        
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

# Initialize user schedule storage
user_schedule_storage = None

def get_user_schedule_storage():
    """Get user schedule storage instance."""
    global user_schedule_storage
    if user_schedule_storage is None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise HTTPException(status_code=500, detail="Database URL not configured")
        user_schedule_storage = UserScheduleStorage(database_url)
    return user_schedule_storage

# User and Schedule Management Endpoints

@app.post("/schedules")
async def save_schedule(
    payload: SaveSchedulePayload,
    current_user: dict = Depends(get_current_user)
):
    """Save a schedule for the authenticated user."""
    try:
        # Get session data
        storage = await get_session_storage()
        session_data_obj = await storage.get_session(payload.session_id)
        if session_data_obj is None:
            raise SessionNotFoundError(payload.session_id)
        
        session_data = session_data_obj.data
        
        # Save to user schedule storage
        user_storage = get_user_schedule_storage()
        schedule = user_storage.save_schedule(
            auth0_id=current_user["sub"],
            session_id=payload.session_id,
            school=session_data["school"],
            major=session_data["major"],
            term=session_data["term"],
            schedule_data=session_data["last_plan"],
            title=payload.title
        )
        
        return {
            "id": str(schedule.id),
            "title": schedule.title,
            "school": schedule.school,
            "major": schedule.major,
            "term": schedule.term,
            "created_at": schedule.created_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error saving schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to save schedule")

@app.get("/schedules")
async def get_user_schedules(
    limit: int = 50,
    offset: int = 0,
    current_user: dict = Depends(get_current_user)
):
    """Get all schedules for the authenticated user."""
    try:
        user_storage = get_user_schedule_storage()
        schedules = user_storage.get_user_schedules(
            auth0_id=current_user["sub"],
            limit=limit,
            offset=offset
        )
        
        return {
            "schedules": [
                {
                    "id": str(schedule.id),
                    "title": schedule.title,
                    "school": schedule.school,
                    "major": schedule.major,
                    "term": schedule.term,
                    "is_favorite": schedule.is_favorite,
                    "created_at": schedule.created_at.isoformat(),
                    "updated_at": schedule.updated_at.isoformat()
                }
                for schedule in schedules
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting user schedules: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedules")

@app.get("/schedules/{schedule_id}")
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get a specific schedule by ID."""
    try:
        user_storage = get_user_schedule_storage()
        schedule = user_storage.get_schedule_by_id(
            auth0_id=current_user["sub"],
            schedule_id=schedule_id
        )
        
        if not schedule:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {
            "id": str(schedule.id),
            "title": schedule.title,
            "school": schedule.school,
            "major": schedule.major,
            "term": schedule.term,
            "schedule_data": schedule.schedule_data,
            "is_favorite": schedule.is_favorite,
            "created_at": schedule.created_at.isoformat(),
            "updated_at": schedule.updated_at.isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to get schedule")

@app.put("/schedules/{schedule_id}")
async def update_schedule(
    schedule_id: str,
    payload: UpdateSchedulePayload,
    current_user: dict = Depends(get_current_user)
):
    """Update a schedule."""
    try:
        user_storage = get_user_schedule_storage()
        
        if payload.title is not None:
            success = user_storage.update_schedule_title(
                auth0_id=current_user["sub"],
                schedule_id=schedule_id,
                title=payload.title
            )
            if not success:
                raise HTTPException(status_code=404, detail="Schedule not found")
        
        if payload.is_favorite is not None:
            success = user_storage.toggle_favorite(
                auth0_id=current_user["sub"],
                schedule_id=schedule_id
            )
            if not success:
                raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {"message": "Schedule updated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to update schedule")

@app.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete a schedule."""
    try:
        user_storage = get_user_schedule_storage()
        success = user_storage.delete_schedule(
            auth0_id=current_user["sub"],
            schedule_id=schedule_id
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="Schedule not found")
        
        return {"message": "Schedule deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete schedule")

@app.get("/user/profile")
async def get_user_profile(current_user: dict = Depends(get_current_user)):
    """Get current user profile."""
    return {
        "sub": current_user["sub"],
        "email": current_user["email"],
        "name": current_user["name"],
        "picture": current_user["picture"]
    }

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

