from fastapi import FastAPI
from pydantic import BaseModel
from typing import List
from models.schemas import RequirementSet, Preferences, SchedulePlan, Section
from services.requirements import get_requirements
from services.pitt_catalog import get_sections
from services.solver import build_schedule
from agents.gemini import parse_preferences

app = FastAPI(title="Scheduly Backend")

class StartPayload(BaseModel):
    school: str
    major: str

class SectionsPayload(BaseModel):
    term: str
    course_codes: List[str]

class OptimizePayload(BaseModel):
    term: str
    utterance: str
    sections: List[Section]

@app.post("/session/start")
def session_start(p: StartPayload):
    reqs: RequirementSet = get_requirements(p.school, p.major)
    return {"requirements": reqs.model_dump()}

@app.post("/catalog/sections")
def catalog_sections(p: SectionsPayload):
    secs = get_sections(p.term, p.course_codes)
    return {"sections": [s.model_dump() for s in secs]}

@app.post("/optimize")
def optimize(p: OptimizePayload):
    prefs = Preferences(**parse_preferences(p.utterance))
    plan: SchedulePlan = build_schedule(
        p.term,
        [s if isinstance(s, Section) else Section(**s) for s in p.sections],
        prefs
    )
    return plan.model_dump()
