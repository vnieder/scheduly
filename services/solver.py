from models.schemas import Section, Preferences, SchedulePlan
from typing import List

def _overlap(a:Section,b:Section)->bool:
    if not set(a.days).intersection(b.days): return False
    return not (a.end <= b.start or b.end <= a.start)

def _violates(s:Section, p:Preferences)->bool:
    if any(d in (p.noDays or []) for d in s.days): return True
    if p.earliestStart and s.start < p.earliestStart: return True
    if p.latestEnd and s.end > p.latestEnd: return True
    return False

def build_schedule(term:str, sections:List[Section], prefs:Preferences)->SchedulePlan:
    chosen: List[Section] = []
    for s in sections:
        if _violates(s,prefs): continue
        if any(_overlap(s,c) for c in chosen): continue
        if s.course in (prefs.skipCourses or []): continue
        chosen.append(s)
    total = sum(s.credits for s in chosen)
    return SchedulePlan(term=term, totalCredits=total, sections=chosen,
                        explanations=[], alternatives=[])
