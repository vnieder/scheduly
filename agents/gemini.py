import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

# Initialize the client with the API key
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set. Please add it to your .env file.")

client = genai.Client(api_key=api_key)
MODEL = "gemini-2.0-flash" # todo: update to latest model

requirement_set_schema = {
  "type":"object",
  "properties":{
    "catalogYear":{"type":"string"},
    "required":{"type":"array","items":{"type":"string"}},
    "chooseFrom":{"type":"array","items":{
      "type":"object",
      "properties":{"label":{"type":"string"},"count":{"type":"integer"},
                    "options":{"type":"array","items":{"type":"string"}}},
      "required":["label","count","options"]
    }},
    "minCredits":{"type":"integer"},
    "maxCredits":{"type":"integer"},
    "prereqs":{"type":"array","items":{
      "type":"object",
      "properties":{"course":{"type":"string"},
                    "requires":{"type":"array","items":{"type":"string"}}},
      "required":["course","requires"]
    }}
  },
  "required":["required"]
}

preferences_schema = {
  "type":"object",
  "properties":{
    "noDays":{"type":"array","items":{"type":"string"}},
    "earliestStart":{"type":"string"},
    "latestEnd":{"type":"string"},
    "minCredits":{"type":"integer"},
    "maxCredits":{"type":"integer"},
    "skipCourses":{"type":"array","items":{"type":"string"}},
    "pinSections":{"type":"array","items":{"type":"string"}},
    "avoidGaps":{"type":"boolean"}
  }
}

def parse_preferences(utterance:str)->dict:
    resp = client.models.generate_content(
        model=MODEL,
        config={"response_mime_type":"application/json",
                "response_schema":preferences_schema},
        contents=[{"role":"user","parts":[{"text": utterance}]}]
    )
    return resp.parsed or {}
