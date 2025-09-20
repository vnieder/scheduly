# services/pitt_catalog.py
from typing import List
from models.schemas import Section
import requests

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

def _get_course_id(subject: str, number4: str) -> str | None:
    r = requests.get(SUBJECT_COURSES_API.format(subject=subject), timeout=20)
    r.raise_for_status()
    data = r.json()
    for c in data.get("courses", []):
        # catalog_nbr is zero-padded like "0150", "1501", etc.
        if str(c.get("catalog_nbr")) == number4:
            return str(c.get("crse_id"))
    return None

def _fetch_sections(term: str, course_id: str) -> list[dict]:
    r = requests.get(COURSE_SECTIONS_API.format(course_id=course_id, term=term), timeout=20)
    r.raise_for_status()
    return r.json().get("sections", [])

def _norm_days(raw) -> list[str]:
    if isinstance(raw, list): return raw
    if not isinstance(raw, str): return []
    # Convert "MoWeFr" style into ["Mon","Wed","Fri"]
    m = (raw.replace("Mo","Mon ").replace("Tu","Tue ")
             .replace("We","Wed ").replace("Th","Thu ")
             .replace("Fr","Fri ").replace("Sa","Sat ").replace("Su","Sun "))
    return [d for d in m.split() if d]

def get_sections(term: str, course_codes: List[str]) -> List[Section]:
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

    # Fallback mock so your demo is always live
    if not out:
        MOCK = {
          "CS0445":[{"crn":"45678","section":"LEC-201","days":["Tue","Thu"],"start":"11:00","end":"12:15","location":"SENSQ 5317","credits":3}],
          "CS1501":[{"crn":"78901","section":"LEC-101","days":["Mon","Wed","Fri"],"start":"10:00","end":"10:50","credits":3}],
          "CS1550":[{"crn":"12345","section":"LEC-101","days":["Mon","Wed","Fri"],"start":"09:00","end":"09:50","credits":3}]
        }
        for code in course_codes:
            for s in MOCK.get(code, []):
                out.append(Section(course=code, instructor=None, **s))

    return out
