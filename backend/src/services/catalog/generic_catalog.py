from typing import List
from src.models.schemas import Section
import logging

logger = logging.getLogger(__name__)

def get_sections(term: str, course_codes: List[str], include_recitations: bool = False) -> List[Section]:
    """Generate generic sections for any school/major combination in development mode."""
    out: List[Section] = []
    
    for i, code in enumerate(course_codes):
        # Generate multiple sections for each course to simulate real course offerings
        for section_num in ["001", "002", "003"]:
            # Create realistic time slots
            time_slots = [
                ("09:00", "10:15", ["Mon", "Wed", "Fri"]),
                ("10:30", "11:45", ["Mon", "Wed", "Fri"]),
                ("14:00", "15:15", ["Mon", "Wed", "Fri"]),
                ("15:30", "16:45", ["Mon", "Wed", "Fri"]),
                ("09:00", "10:30", ["Tue", "Thu"]),
                ("11:00", "12:30", ["Tue", "Thu"]),
                ("14:00", "15:30", ["Tue", "Thu"]),
            ]
            
            start_time, end_time, days = time_slots[i % len(time_slots)]
            
            # Generate a realistic CRN
            crn = f"{term}{i:02d}{int(section_num):01d}"
            
            out.append(Section(
                course=code,
                crn=crn,
                section=section_num,
                days=days,
                start=start_time,
                end=end_time,
                location=f"Building {chr(65 + i % 5)} Room {100 + int(section_num)}",
                instructor=f"Dr. {chr(65 + i % 26)}. Professor",
                credits=3
            ))
    
    logger.info(f"Generated {len(out)} generic sections for {len(course_codes)} courses")
    return out
