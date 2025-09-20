from models.schemas import RequirementSet

CURATED = {
  ("pitt","computer science"): RequirementSet(
     catalogYear="2025-2026",
     required=["CS0401","CS0441","CS0445","CS1501","CS1502","CS1550"],
     genEds=[
         {"label": "Writing Intensive", "count": 1, "options": ["ENGCMP0200","ENGCMP0205","ENGCMP0207"]},
         {"label": "Literature", "count": 1, "options": ["ENGLIT0200","ENGLIT0400","ENGLIT0500"]},
         {"label": "History", "count": 1, "options": ["HIST0100","HIST0600","HIST0700"]},
         {"label": "Social Science", "count": 1, "options": ["PSY0010","SOC0010","ANTH0780"]},
         {"label": "Natural Science", "count": 1, "options": ["BIOSC0150","CHEM0110","PHYS0174"]},
         {"label": "Arts", "count": 1, "options": ["MUSIC0211","THEA0800","ARTSC0100"]},
         {"label": "Philosophy", "count": 1, "options": ["PHIL0080","PHIL0300","PHIL0400"]}
     ],
     chooseFrom=[
         {"label": "Upper Level CS Electives", "count": 2, "options": ["CS1621","CS1653","CS1674","CS1699","CS1695","CS1690"]},
         {"label": "Math Requirements", "count": 3, "options": ["MATH0220","MATH0230","MATH1180","STAT1151"]}
     ],
     minCredits=12, maxCredits=18, 
     prereqs=[],
     multiSemesterPrereqs=[
         {"course": "CS1502", "requires": ["CS1501"]},  # Must take CS1501 in previous semester
         {"course": "CS1621", "requires": ["CS0445"]},  # Must take CS0445 in previous semester
         {"course": "CS1653", "requires": ["CS0445"]},  # Must take CS0445 in previous semester
         {"course": "CS1674", "requires": ["CS0445"]},  # Must take CS0445 in previous semester
         {"course": "CS1699", "requires": ["CS0445"]}   # Must take CS0445 in previous semester
     ]
  )
}

def get_requirements(school:str, major:str) -> RequirementSet:
    key = (school.lower(), major.lower())
    if key in CURATED:
        return CURATED[key]
    from agents.gemini import client, MODEL, requirement_set_schema
    prompt = f"""Find the official degree requirements for {school} {major}.
Output JSON only, matching the schema. Normalize course codes exactly as on the page."""
    resp = client.models.generate_content(
        model=MODEL,
        config={"response_mime_type":"application/json",
                "response_schema": requirement_set_schema,
                "tools":[{"google_search":{}}]},
        contents=[{"role":"user","parts":[{"text": prompt}]}]
    )
    data = resp.parsed or {"required":[]}
    return RequirementSet(**data)
