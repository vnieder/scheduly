# Scheduly Backend

A backend service for building class schedules based on degree requirements and user preferences.

## Features

- **Smart Schedule Building**: Automatically builds class schedules from degree requirements
- **Preference Parsing**: Uses Gemini AI to parse natural language preferences into structured constraints
- **Live Course Data**: Fetches real-time course sections from Pitt's PeopleSoft system
- **Session Management**: Maintains user sessions for iterative schedule optimization
- **Constraint Handling**: Supports time constraints, day preferences, course skipping, and section pinning
- **Caching**: In-memory caching for improved performance
- **Error Handling**: Robust error handling with retry logic and fallback to mock data

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment**:
   Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Run the server**:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

4. **Test the API**:
   ```bash
   python test_endpoints.py
   ```

## API Endpoints

### `GET /health`
Health check endpoint.

**Response**: `{"ok": true}`

### `POST /build`
Build an initial schedule for a student.

**Request**:
```json
{
  "school": "Pitt",
  "major": "Computer Science", 
  "term": "2251",
  "utterance": "no Friday, start after 10am, 15 credits"
}
```

**Response**:
```json
{
  "session_id": "uuid-string",
  "requirements": {...},
  "plan": {
    "term": "2251",
    "totalCredits": 12,
    "sections": [...],
    "explanations": [...],
    "alternatives": []
  }
}
```

### `POST /optimize`
Optimize an existing schedule with new preferences.

**Request**:
```json
{
  "session_id": "uuid-string",
  "utterance": "avoid Tue/Thu, pin section CRN 45678"
}
```

**Response**:
```json
{
  "plan": {
    "term": "2251",
    "totalCredits": 12,
    "sections": [...],
    "explanations": [...],
    "alternatives": []
  }
}
```

### `POST /catalog/sections`
Fetch available sections for specific courses.

**Request**:
```json
{
  "term": "2251",
  "course_codes": ["CS0445", "CS1501", "CS1550"]
}
```

## Architecture

- **`app.py`**: FastAPI application with session management and orchestration
- **`models/schemas.py`**: Pydantic models for data validation
- **`services/pitt_catalog.py`**: Pitt PeopleSoft API integration with caching
- **`services/requirements.py`**: Degree requirements management
- **`services/solver.py`**: Schedule optimization algorithm
- **`services/terms.py`**: Term code utilities
- **`agents/gemini.py`**: Gemini AI integration for preference parsing

## Term Codes

Pitt uses a 4-digit term code system:
- Fall 2025: `2251`
- Spring 2025: `2244` 
- Summer 2025: `2257`

Use the `to_term_code()` function in `services/terms.py` to convert seasons and years to term codes.

## Testing

Run the comprehensive test suite:
```bash
python test_endpoints.py
```

This will test all endpoints and verify the system works end-to-end.

## Development

The backend is designed to be:
- **Stateless**: Each request is independent (except for session management)
- **Resilient**: Graceful fallbacks when external services fail
- **Fast**: In-memory caching reduces API calls
- **Extensible**: Easy to add new schools, constraint types, or solvers
