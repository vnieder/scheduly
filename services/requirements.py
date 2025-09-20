from models.schemas import RequirementSet

CURATED = {
  ("pitt","computer science"): RequirementSet(
     catalogYear="2025-2026",
     required=["CS0445","CS1501","CS1550"],
     chooseFrom=[],
     minCredits=12, maxCredits=18, prereqs=[]
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
