from pydantic import BaseModel
from typing import List, Optional

class ChooseFrom(BaseModel):
    label: str
    count: int
    options: List[str]

class Prereq(BaseModel):
    course: str
    requires: List[str]

class RequirementSet(BaseModel):
    catalogYear: Optional[str] = None
    required: List[str] = []  # Major requirements
    genEds: List[ChooseFrom] = []  # General education requirements
    chooseFrom: List[ChooseFrom] = []  # Major electives
    minCredits: Optional[int] = None
    maxCredits: Optional[int] = None
    prereqs: List[Prereq] = []
    multiSemesterPrereqs: List[Prereq] = []  # Prerequisites that must be taken in previous semesters

class Section(BaseModel):
    course: str
    crn: str
    section: str
    days: List[str]
    start: str
    end: str
    location: Optional[str] = None
    instructor: Optional[str] = None
    credits: int = 3

class Preferences(BaseModel):
    noDays: List[str] = []
    earliestStart: Optional[str] = None
    latestEnd: Optional[str] = None
    minCredits: Optional[int] = None
    maxCredits: Optional[int] = None
    skipCourses: List[str] = []
    pinSections: List[str] = []
    avoidGaps: Optional[bool] = None

class SchedulePlan(BaseModel):
    term: str
    totalCredits: int
    sections: List[Section]
    explanations: List[str] = []
    alternatives: List[dict] = []
