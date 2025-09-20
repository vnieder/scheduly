from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import logging
import os
from datetime import datetime, timedelta
import json
from models.schemas import RequirementSet, Preferences, SchedulePlan, Section, Prereq
from services.requirements import get_requirements
from services.pitt_catalog import get_sections
from services.solver import build_schedule
from services.terms import to_term_code
from agents.gemini import parse_preferences, get_requirements_with_prereqs

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scheduly Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://scheduly.space"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
)

# Configuration from environment variables
DEFAULT_TERM = os.getenv("DEFAULT_TERM", "2251")
DEFAULT_SCHOOL = os.getenv("DEFAULT_SCHOOL", "Pitt")
MAX_COURSES_PER_SEMESTER = int(os.getenv("MAX_COURSES_PER_SEMESTER", "6"))
MAX_COURSE_SELECTION = int(os.getenv("MAX_COURSE_SELECTION", "10"))
SESSION_TIMEOUT_HOURS = int(os.getenv("SESSION_TIMEOUT_HOURS", "24"))

# File-based session store (simple but persistent)
SESSION_FILE = "sessions.json"

def load_sessions() -> Dict[str, Dict]:
    """Load sessions from file."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load sessions: {e}")
    return {}

def save_sessions(sessions: Dict[str, Dict]):
    """Save sessions to file."""
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(sessions, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save sessions: {e}")

def cleanup_expired_sessions(sessions: Dict[str, Dict]):
    """Remove expired sessions."""
    cutoff = datetime.now() - timedelta(hours=SESSION_TIMEOUT_HOURS)
    expired = []
    
    for session_id, session_data in sessions.items():
        created_at = session_data.get('created_at')
        if created_at:
            try:
                created_time = datetime.fromisoformat(created_at)
                if created_time < cutoff:
                    expired.append(session_id)
            except ValueError:
                expired.append(session_id)
    
    for session_id in expired:
        del sessions[session_id]
        logger.info(f"Cleaned up expired session: {session_id}")
    
    return sessions

# Load and initialize sessions
SESSIONS = cleanup_expired_sessions(load_sessions())

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
        super().__init__(status_code=400, detail=f"Invalid term format: {term}. Expected format: YYYYMM")

class InvalidSchoolError(HTTPException):
    def __init__(self, school: str):
        super().__init__(status_code=400, detail=f"School '{school}' not supported. Currently only supports: {DEFAULT_SCHOOL}")

class AIServiceError(HTTPException):
    def __init__(self, service: str, error: str):
        super().__init__(status_code=503, detail=f"AI service '{service}' error: {error}")

class CatalogServiceError(HTTPException):
    def __init__(self, error: str):
        super().__init__(status_code=503, detail=f"Course catalog service error: {error}")

def validate_term(term: str) -> bool:
    """Validate term format (YYYYMM)."""
    if not term or len(term) != 6:
        return False
    try:
        year = int(term[:4])
        month = int(term[4:])
        return 2020 <= year <= 2030 and 1 <= month <= 12
    except ValueError:
        return False

def validate_school(school: str) -> bool:
    """Validate school is supported."""
    return school.lower() == DEFAULT_SCHOOL.lower()

def validate_course_codes(course_codes: List[str]) -> List[str]:
    """Validate and clean course codes."""
    validated = []
    for code in course_codes:
        # Basic validation: should be alphanumeric and reasonable length
        clean_code = code.strip().upper()
        if clean_code and len(clean_code) >= 3 and len(clean_code) <= 10:
            validated.append(clean_code)
    return validated

@app.get("/health")
def health_check():
    return {"ok": True}

@app.post("/build")
def build_schedule_endpoint(p: BuildPayload):
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
        
        # Get requirements with prerequisites using agentic search
        try:
            requirements_data = get_requirements_with_prereqs(p.school, p.major)
            requirements = RequirementSet(**requirements_data)
        except Exception as e:
            logger.error(f"Failed to get requirements: {e}")
            raise AIServiceError("Gemini", str(e))
        
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
        except Exception as e:
            logger.error(f"Failed to get sections: {e}")
            raise CatalogServiceError(str(e))
        
        # Parse preferences
        try:
            prefs_data = parse_preferences(p.utterance) if p.utterance else {}
            preferences = Preferences(**prefs_data)
        except Exception as e:
            logger.error(f"Failed to parse preferences: {e}")
            raise AIServiceError("Gemini", str(e))
        
        # Build initial schedule with prerequisites and available courses
        # For first semester, no completed courses yet
        completed_courses = []
        plan = build_schedule(p.term, sections, preferences, requirements.prereqs, course_codes, requirements.multiSemesterPrereqs, completed_courses)
        
        # Store session state with timestamp
        SESSIONS[session_id] = {
            "created_at": datetime.now().isoformat(),
            "school": p.school,
            "major": p.major,
            "term": p.term,
            "preferences": preferences.model_dump(),
            "courses": course_codes,
            "prereqs": [prereq.model_dump() for prereq in requirements.prereqs],
            "multiSemesterPrereqs": [prereq.model_dump() for prereq in requirements.multiSemesterPrereqs],
            "completedCourses": completed_courses,
            "last_plan": plan.model_dump()
        }
        
        # Save sessions to file
        save_sessions(SESSIONS)
        
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
def optimize_schedule(p: OptimizePayload):
    try:
        # Validate session exists
        if p.session_id not in SESSIONS:
            raise SessionNotFoundError(p.session_id)
        
        session = SESSIONS[p.session_id]
        
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
        existing_prefs = session["preferences"]
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
            sections = get_sections(session["term"], session["courses"])
        except Exception as e:
            logger.error(f"Failed to get sections: {e}")
            raise CatalogServiceError(str(e))
        
        # Get prerequisites from session
        prereqs_data = session.get("prereqs", [])
        prereqs = [Prereq(**p) for p in prereqs_data] if prereqs_data else []
        
        # Build new schedule with updated preferences and prerequisites
        available_courses = session.get("courses", [])
        multi_semester_prereqs_data = session.get("multiSemesterPrereqs", [])
        multi_semester_prereqs = [Prereq(**p) for p in multi_semester_prereqs_data] if multi_semester_prereqs_data else []
        completed_courses = session.get("completedCourses", [])
        plan = build_schedule(session["term"], sections, preferences, prereqs, available_courses, multi_semester_prereqs, completed_courses)
        
        # Update session state
        session["preferences"] = preferences.model_dump()
        session["last_plan"] = plan.model_dump()
        
        # Save sessions to file
        save_sessions(SESSIONS)
        
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

# Removed multi-semester planning endpoint - out of scope for current frontend
