from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import logging
from models.schemas import RequirementSet, Preferences, SchedulePlan, Section
from services.requirements import get_requirements
from services.pitt_catalog import get_sections
from services.solver import build_schedule
# from services.terms import to_term_code  # Available for future use
from agents.gemini import parse_preferences

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Scheduly Backend")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session store
SESSIONS: Dict[str, Dict] = {}

class BuildPayload(BaseModel):
    school: str
    major: str
    term: Optional[str] = "2251"  # Default to Fall 2025
    utterance: Optional[str] = ""

class OptimizePayload(BaseModel):
    session_id: str
    utterance: str

class SectionsPayload(BaseModel):
    term: str
    course_codes: List[str]

@app.get("/health")
def health_check():
    return {"ok": True}

@app.post("/build")
def build_schedule_endpoint(p: BuildPayload):
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Get requirements
        requirements = get_requirements(p.school, p.major)
        
        # Choose first 6 required courses for the term
        course_codes = requirements.required[:6]
        
        # Get sections for these courses
        sections = get_sections(p.term, course_codes)
        
        # Parse preferences
        prefs_data = parse_preferences(p.utterance) if p.utterance else {}
        preferences = Preferences(**prefs_data)
        
        # Build initial schedule
        plan = build_schedule(p.term, sections, preferences)
        
        # Store session state
        SESSIONS[session_id] = {
            "school": p.school,
            "major": p.major,
            "term": p.term,
            "preferences": preferences.model_dump(),
            "courses": course_codes,
            "last_plan": plan.model_dump()
        }
        
        return {
            "session_id": session_id,
            "requirements": requirements.model_dump(),
            "plan": plan.model_dump()
        }
        
    except Exception as e:
        logger.error(f"Error in /build: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize")
def optimize_schedule(p: OptimizePayload):
    try:
        # Get session
        if p.session_id not in SESSIONS:
            raise HTTPException(status_code=404, detail="Session not found")
        
        session = SESSIONS[p.session_id]
        
        # Parse new preferences
        new_prefs_data = parse_preferences(p.utterance)
        
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
        sections = get_sections(session["term"], session["courses"])
        
        # Build new schedule with updated preferences
        plan = build_schedule(session["term"], sections, preferences)
        
        # Update session state
        session["preferences"] = preferences.model_dump()
        session["last_plan"] = plan.model_dump()
        
        return {"plan": plan.model_dump()}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in /optimize: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/catalog/sections")
def catalog_sections(p: SectionsPayload):
    secs = get_sections(p.term, p.course_codes)
    return {"sections": [s.model_dump() for s in secs]}
