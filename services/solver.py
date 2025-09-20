from models.schemas import Section, Preferences, SchedulePlan, Prereq
from typing import List, Set

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

def _has_prerequisites_met(section: Section, chosen_sections: List[Section], prereqs: List[Prereq], available_courses: List[str] = None, multi_semester_prereqs: List[Prereq] = None, completed_courses: List[str] = None) -> bool:
    """Check if section's prerequisites are met by chosen sections, available courses, or completed courses."""
    if multi_semester_prereqs is None:
        multi_semester_prereqs = []
    if completed_courses is None:
        completed_courses = []
    
    # Check same-semester prerequisites
    for prereq in prereqs:
        if prereq.course == section.course:
            chosen_courses = {s.course for s in chosen_sections}
            available_courses_set = set(available_courses) if available_courses else set()
            
            # A prerequisite is met if:
            # 1. It's already in the chosen sections, OR
            # 2. It's available in the same term (meaning we can take it in parallel)
            for req in prereq.requires:
                if req not in chosen_courses and req not in available_courses_set:
                    return False
    
    # Check multi-semester prerequisites (must be completed in previous semesters)
    for prereq in multi_semester_prereqs:
        if prereq.course == section.course:
            completed_courses_set = set(completed_courses)
            
            # Multi-semester prerequisites must be completed in previous semesters
            for req in prereq.requires:
                if req not in completed_courses_set:
                    return False
    
    return True

def _already_has_course(chosen_sections: List[Section], course: str) -> bool:
    """Check if we already have a section for this course."""
    return any(s.course == course for s in chosen_sections)

def build_schedule(term: str, sections: List[Section], prefs: Preferences, prereqs: List[Prereq] = None, available_courses: List[str] = None, multi_semester_prereqs: List[Prereq] = None, completed_courses: List[str] = None) -> SchedulePlan:
    chosen: List[Section] = []
    explanations: List[str] = []
    skipped_courses = []
    skipped_days = []
    skipped_times = []
    skipped_prereqs = []
    
    if prereqs is None:
        prereqs = []
    if multi_semester_prereqs is None:
        multi_semester_prereqs = []
    if available_courses is None:
        available_courses = list(set(s.course for s in sections))
    if completed_courses is None:
        completed_courses = []
    
    # First, add all pinned sections
    pinned_sections = [s for s in sections if _should_include_pinned(s, prefs)]
    for pinned in pinned_sections:
        if not _violates_hard_constraints(pinned, prefs):
            chosen.append(pinned)
            explanations.append(f"Pinned section {pinned.course} {pinned.section} (CRN: {pinned.crn})")
        else:
            explanations.append(f"Could not pin section {pinned.course} {pinned.section} due to hard constraints")
    
    # Sort sections by course, prioritizing courses with no prerequisites first
    def get_course_priority(section):
        course = section.course
        # Find prerequisites for this course
        for prereq in prereqs:
            if prereq.course == course:
                # More prerequisites = lower priority (taken later)
                return len(prereq.requires)
        # No prerequisites = highest priority (taken first)
        return 0
    
    # Sort sections: pinned first, then by prerequisite priority, then alphabetically
    sorted_sections = sorted(
        [s for s in sections if s not in pinned_sections], 
        key=lambda x: (get_course_priority(x), x.course)
    )
    
    # Then add other sections
    for s in sorted_sections:
        # Skip if we already have this course
        if _already_has_course(chosen, s.course):
            continue
            
        if _violates_hard_constraints(s, prefs):
            if s.course in (prefs.skipCourses or []):
                skipped_courses.append(s.course)
            elif any(d in (prefs.noDays or []) for d in s.days):
                skipped_days.extend([d for d in s.days if d in (prefs.noDays or [])])
            elif (prefs.earliestStart and s.start < prefs.earliestStart) or (prefs.latestEnd and s.end > prefs.latestEnd):
                skipped_times.append(s.course)
            continue
        
        # Check prerequisites
        if not _has_prerequisites_met(s, chosen, prereqs, available_courses, multi_semester_prereqs, completed_courses):
            skipped_prereqs.append(s.course)
            continue
            
        # Check for overlaps with already chosen sections
        if any(_overlap(s, c) for c in chosen):
            continue
        
        # Limit to reasonable number of courses per semester (5-6 courses max)
        if len(chosen) >= 6:
            explanations.append(f"Reached maximum courses per semester (6)")
            break
            
        chosen.append(s)
    
    total = sum(s.credits for s in chosen)
    
    # Generate explanations
    if skipped_courses:
        explanations.append(f"Skipped courses: {', '.join(set(skipped_courses))}")
    if skipped_days:
        explanations.append(f"Avoided days: {', '.join(set(skipped_days))}")
    if skipped_times:
        explanations.append(f"Skipped due to time constraints: {', '.join(set(skipped_times))}")
    if skipped_prereqs:
        explanations.append(f"Skipped due to prerequisites: {', '.join(set(skipped_prereqs))}")
    
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
