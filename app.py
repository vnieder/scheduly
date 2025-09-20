from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import uuid
import logging
from models.schemas import RequirementSet, Preferences, SchedulePlan, Section, Prereq
from services.requirements import get_requirements
from services.pitt_catalog import get_sections
from services.solver import build_schedule
# from services.terms import to_term_code  # Available for future use
from agents.gemini import parse_preferences, get_requirements_with_prereqs

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

class SemesterPlanPayload(BaseModel):
    school: str
    major: str
    starting_term: Optional[str] = "2251"  # Default to Fall 2025
    num_semesters: Optional[int] = 4
    utterance: Optional[str] = ""

@app.get("/health")
def health_check():
    return {"ok": True}

@app.post("/build")
def build_schedule_endpoint(p: BuildPayload):
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Get requirements with prerequisites using agentic search
        requirements_data = get_requirements_with_prereqs(p.school, p.major)
        requirements = RequirementSet(**requirements_data)
        
        # Choose courses for the term - mix of major requirements and gen eds
        all_courses = requirements.required.copy()
        
        # Add some general education courses
        for gen_ed_group in requirements.genEds:
            all_courses.extend(gen_ed_group.options[:gen_ed_group.count])
        
        # Add some major electives
        for choice_group in requirements.chooseFrom:
            all_courses.extend(choice_group.options[:choice_group.count])
        
        # Select up to 10 courses to include gen eds
        course_codes = all_courses[:10]
        
        # Get sections for these courses
        sections = get_sections(p.term, course_codes)
        
        # Parse preferences
        prefs_data = parse_preferences(p.utterance) if p.utterance else {}
        preferences = Preferences(**prefs_data)
        
        # Build initial schedule with prerequisites and available courses
        # For first semester, no completed courses yet
        completed_courses = []
        plan = build_schedule(p.term, sections, preferences, requirements.prereqs, course_codes, requirements.multiSemesterPrereqs, completed_courses)
        
        # Store session state
        SESSIONS[session_id] = {
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

@app.post("/plan-semesters")
def plan_semesters(p: SemesterPlanPayload):
    try:
        # Get requirements with prerequisites using agentic search
        requirements_data = get_requirements_with_prereqs(p.school, p.major)
        requirements = RequirementSet(**requirements_data)
        
        # Parse preferences
        prefs_data = parse_preferences(p.utterance) if p.utterance else {}
        preferences = Preferences(**prefs_data)
        
        # Get all courses (major + gen eds + electives)
        all_courses = requirements.required.copy()
        for gen_ed_group in requirements.genEds:
            all_courses.extend(gen_ed_group.options[:gen_ed_group.count])
        for choice_group in requirements.chooseFrom:
            all_courses.extend(choice_group.options[:choice_group.count])
        
        semester_plans = []
        completed_courses = []
        
        # Use the same term for all semesters since we're just planning
        # (future terms won't have section data available)
        term = p.starting_term
        
        # Get sections for available courses (only once)
        sections = get_sections(term, all_courses)
        
        # Generate semester plans
        for i in range(p.num_semesters):
            # Build schedule for this semester
            plan = build_schedule(term, sections, preferences, requirements.prereqs, all_courses, requirements.multiSemesterPrereqs, completed_courses)
            
            # Add completed courses from this semester to the list
            semester_courses = [s.course for s in plan.sections]
            completed_courses.extend(semester_courses)
            
            # Generate a unique term code for display purposes
            display_term = str(int(p.starting_term) + i * 10)
            
            semester_plans.append({
                "semester": f"Semester {i+1}",
                "term": display_term,
                "plan": plan.model_dump()
            })
        
        return {
            "requirements": requirements.model_dump(),
            "semester_plans": semester_plans,
            "total_semesters": p.num_semesters
        }
        
    except Exception as e:
        logger.error(f"Error in /plan-semesters: {e}")
        raise HTTPException(status_code=500, detail=str(e))
