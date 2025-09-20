from models.schemas import Section, Preferences, SchedulePlan
from typing import List

def _overlap(a: Section, b: Section) -> bool:
    if not set(a.days).intersection(b.days): 
        return False
    return not (a.end <= b.start or b.end <= a.start)

def _violates_hard_constraints(s: Section, p: Preferences) -> bool:
    """Check if section violates hard constraints."""
    if any(d in (p.noDays or []) for d in s.days): 
        return True
    if p.earliestStart and s.start < p.earliestStart: 
        return True
    if p.latestEnd and s.end > p.latestEnd: 
        return True
    if s.course in (p.skipCourses or []): 
        return True
    return False

def _should_include_pinned(s: Section, p: Preferences) -> bool:
    """Check if section should be included due to pinning."""
    return s.crn in (p.pinSections or [])

def build_schedule(term: str, sections: List[Section], prefs: Preferences) -> SchedulePlan:
    chosen: List[Section] = []
    explanations: List[str] = []
    skipped_courses = []
    skipped_days = []
    skipped_times = []
    
    # First, add all pinned sections
    pinned_sections = [s for s in sections if _should_include_pinned(s, prefs)]
    for pinned in pinned_sections:
        if not _violates_hard_constraints(pinned, prefs):
            chosen.append(pinned)
            explanations.append(f"Pinned section {pinned.course} {pinned.section} (CRN: {pinned.crn})")
        else:
            explanations.append(f"Could not pin section {pinned.course} {pinned.section} due to hard constraints")
    
    # Then add other sections
    for s in sections:
        if s in pinned_sections:
            continue  # Already processed
            
        if _violates_hard_constraints(s, prefs):
            if s.course in (prefs.skipCourses or []):
                skipped_courses.append(s.course)
            elif any(d in (prefs.noDays or []) for d in s.days):
                skipped_days.extend([d for d in s.days if d in (prefs.noDays or [])])
            elif (prefs.earliestStart and s.start < prefs.earliestStart) or (prefs.latestEnd and s.end > prefs.latestEnd):
                skipped_times.append(s.course)
            continue
            
        # Check for overlaps with already chosen sections
        if any(_overlap(s, c) for c in chosen):
            continue
            
        chosen.append(s)
    
    total = sum(s.credits for s in chosen)
    
    # Generate explanations
    if skipped_courses:
        explanations.append(f"Skipped courses: {', '.join(set(skipped_courses))}")
    if skipped_days:
        explanations.append(f"Avoided days: {', '.join(set(skipped_days))}")
    if skipped_times:
        explanations.append(f"Skipped due to time constraints: {', '.join(set(skipped_times))}")
    
    if prefs.minCredits and total < prefs.minCredits:
        explanations.append(f"Warning: Total credits ({total}) below minimum ({prefs.minCredits})")
    if prefs.maxCredits and total > prefs.maxCredits:
        explanations.append(f"Warning: Total credits ({total}) above maximum ({prefs.maxCredits})")
    
    if not explanations:
        explanations.append("Schedule built successfully with all constraints satisfied")
    
    return SchedulePlan(
        term=term, 
        totalCredits=total, 
        sections=chosen,
        explanations=explanations, 
        alternatives=[]
    )
