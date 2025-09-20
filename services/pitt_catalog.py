from typing import List
from models.schemas import Section
import requests
import logging
import time

logger = logging.getLogger(__name__)

# Simple in-memory cache with timestamps
_cache = {}
CACHE_TTL = 600  # 10 minutes

# Endpoints lifted from your PittAPI course.py (no CSRF needed for these GETs)
SUBJECT_COURSES_API = (
    "https://pitcsprd.csps.pitt.edu/psc/pitcsprd/EMPLOYEE/SA/s/"
    "WEBLIB_HCX_CM.H_COURSE_CATALOG.FieldFormula.IScript_SubjectCourses"
    "?institution=UPITT&subject={subject}"
)
COURSE_SECTIONS_API = (
    "https://pitcsprd.csps.pitt.edu/psc/pitcsprd/EMPLOYEE/SA/s/"
    "WEBLIB_HCX_CM.H_BROWSE_CLASSES.FieldFormula.IScript_BrowseSections"
    "?institution=UPITT&campus=&location=&course_id={course_id}&term={term}&crse_offer_nbr=1"
)
def _hhmm(t: str) -> str:
    # handles "15.00", "09.30", "1500", "15:00"
    if not t: return "00:00"
    t = str(t).strip()
    if ":" in t and len(t) >= 5: return t[:5]
    if "." in t:
        hh, mm = t.split(".", 1)
        return f"{hh.zfill(2)}:{mm[:2].ljust(2,'0')}"
    if len(t) == 4 and t.isdigit():
        return f"{t[:2]}:{t[2:]}"
    return t[:5]

def _split(code: str) -> tuple[str, str]:
    sub = "".join(c for c in code if c.isalpha())
    num = "".join(c for c in code if c.isdigit())
    # pad to 4 (e.g., "150" -> "0150")
    if len(num) < 4:
        num = ("0" * (4 - len(num))) + num
    return sub, num

def _is_likely_recitation(section_num: str, days: list[str]) -> bool:
    """Heuristic to identify recitation sections."""
    return (len(days) == 1 and days[0] in {"Fri", "Thu"})

def _get_course_id(subject: str, number4: str) -> str | None:
    cache_key = f"course_id:{subject}"
    current_time = time.time()
    
    # Check cache first
    if cache_key in _cache:
        cached_data, timestamp = _cache[cache_key]
        if current_time - timestamp < CACHE_TTL:
            # Find the specific course in cached data
            for c in cached_data.get("courses", []):
                if str(c.get("catalog_nbr")) == number4:
                    return str(c.get("crse_id"))
            return None
    
    for attempt in range(2):  # Retry once
        try:
            r = requests.get(SUBJECT_COURSES_API.format(subject=subject), timeout=20)
            r.raise_for_status()
            data = r.json()
            
            # Cache the response
            _cache[cache_key] = (data, current_time)
            
            for c in data.get("courses", []):
                # catalog_nbr is zero-padded like "0150", "1501", etc.
                if str(c.get("catalog_nbr")) == number4:
                    return str(c.get("crse_id"))
            return None
        except Exception as e:
            if attempt == 0:
                logger.warning(f"Failed to get course ID for {subject} {number4}, retrying: {e}")
                time.sleep(1)
            else:
                logger.error(f"Failed to get course ID for {subject} {number4} after retry: {e}")
                return None

def _fetch_sections(term: str, course_id: str) -> list[dict]:
    cache_key = f"sections:{term}:{course_id}"
    current_time = time.time()
    
    # Check cache first
    if cache_key in _cache:
        cached_data, timestamp = _cache[cache_key]
        if current_time - timestamp < CACHE_TTL:
            return cached_data.get("sections", [])
    
    for attempt in range(2):  # Retry once
        try:
            r = requests.get(COURSE_SECTIONS_API.format(course_id=course_id, term=term), timeout=20)
            r.raise_for_status()
            data = r.json()
            
            # Cache the response
            _cache[cache_key] = (data, current_time)
            
            return data.get("sections", [])
        except Exception as e:
            if attempt == 0:
                logger.warning(f"Failed to fetch sections for course_id {course_id}, retrying: {e}")
                time.sleep(1)
            else:
                logger.error(f"Failed to fetch sections for course_id {course_id} after retry: {e}")
                return []

def _norm_days(raw) -> list[str]:
    if isinstance(raw, list): return raw
    if not isinstance(raw, str): return []
    # Convert "MoWeFr" style into ["Mon","Wed","Fri"]
    m = (raw.replace("Mo","Mon ").replace("Tu","Tue ")
            .replace("We","Wed ").replace("Th","Thu ")
            .replace("Fr","Fri ").replace("Sa","Sat ").replace("Su","Sun "))
    return [d for d in m.split() if d]

def get_sections(term: str, course_codes: List[str], include_recitations: bool = False) -> List[Section]:
    out: List[Section] = []

    for code in course_codes:
        subject, number4 = _split(code)
        try:
            course_id = _get_course_id(subject, number4)
            if not course_id:
                continue
            sections = _fetch_sections(term, course_id)
        except Exception:
            sections = []

        # Map each PeopleSoft section to your Section schema
        for s in sections:
            class_nbr = str(s.get("class_nbr", ""))
            section_num = str(s.get("class_section", ""))
            meetings = s.get("meetings", [])
            if meetings:
                # choose the primary meeting block
                m = meetings[0]
                days = _norm_days(m.get("days", []))
                start = _hhmm(m.get("start_time", "00:00"))
                end   = _hhmm(m.get("end_time", "00:00"))
            else:
                days, start, end = [], "00:00", "00:00"

            # Skip recitation sections unless explicitly requested
            if not include_recitations and _is_likely_recitation(section_num, days):
                continue

            instructors = s.get("instructors", [])
            instructor_name = None
            if instructors and isinstance(instructors, list):
                # list of {"name":..., "email":...} or "To be Announced"
                first = instructors[0]
                if isinstance(first, dict):
                    instructor_name = first.get("name")
                elif isinstance(first, str) and first not in ("To be Announced", "-"):
                    instructor_name = first

            out.append(Section(
                course=code,
                crn=class_nbr,
                section=section_num,
                days=days,
                start=start,
                end=end,
                location=None,
                instructor=instructor_name,
                credits=3
            ))

    # If no sections found, try to get course information from web search
    if not out:
        logger.info("No sections found via API, attempting web search")
        from agents.gemini import search_course_catalog
        
        for code in course_codes:
            try:
                # Search for course information online
                courses = search_course_catalog("University of Pittsburgh", course_code=code)
                if courses:
                    course = courses[0]  # Take the first result
                    # Create a mock section with basic info
                    out.append(Section(
                        course=code,
                        crn="TBD",  # To be determined
                        section="LEC-001",
                        days=["TBD"],
                        start="TBD",
                        end="TBD",
                        location="TBD",
                        instructor="TBD",
                        credits=course.get("credits", 3)
                    ))
            except Exception as e:
                logger.warning(f"Could not find course information for {code}: {e}")
                continue

    return out
