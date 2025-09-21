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
   Use the interactive setup script:
   ```bash
   python scripts/setup_env.py
   ```
   
   Or manually create a `.env` file with your configuration:
   ```
   GEMINI_API_KEY=your_gemini_api_key_here
   REDIS_URL=redis://localhost:6379/0
   # or
   DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
   ```

3. **Run the server**:
   ```bash
   uvicorn app:app --reload --port 8000
   ```

4. **Test the API**:
   ```bash
   python scripts/test_backend.py
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

The backend follows a clean, organized structure with all API endpoints centralized in `app.py` for simplicity:

### Core Application
- **`app.py`**: FastAPI application with all API endpoints, session management, and orchestration
- **`src/models/schemas.py`**: Pydantic models for data validation
- **`src/agents/gemini.py`**: Gemini AI integration for preference parsing

### Services (`src/services/`)
- **`src/services/schedule/solver.py`**: Schedule optimization algorithm
- **`src/services/catalog/pitt_catalog.py`**: Pitt PeopleSoft API integration with caching
- **`src/services/catalog/course_parser.py`**: Course data parsing utilities
- **`src/services/requirements/requirements.py`**: Degree requirements management
- **`src/services/requirements/terms.py`**: Term code utilities
- **`src/services/storage/`**: Session storage backends (Redis, Database, Memory)

### Scripts (`scripts/`)
- **`scripts/setup_env.py`**: Interactive environment configuration
- **`scripts/migrate_sessions.py`**: Session data migration utilities
- **`scripts/test_backend.py`**: Comprehensive testing suite

## Term Codes

Pitt uses a 4-digit term code system:
- Fall 2025: `2251`
- Spring 2025: `2244` 
- Summer 2025: `2257`

Use the `to_term_code()` function in `src/services/requirements/terms.py` to convert seasons and years to term codes.

## Testing

### Comprehensive Testing
Run the interactive test suite:
```bash
python scripts/test_backend.py
```

This comprehensive testing tool allows you to:
- Build schedules with custom preferences
- Test optimization with different constraints
- Explore course sections
- Check environment configuration
- Run automated endpoint tests

The test suite provides both automated testing and interactive exploration of the backend functionality.

## Session Storage

The backend supports multiple session storage backends:

- **Redis** (Recommended): Fast, scalable, with automatic expiration
- **PostgreSQL**: Persistent, ACID-compliant storage
- **Memory**: In-memory storage for development/testing

### Migration

If you have existing sessions to migrate:

```bash
python scripts/migrate_sessions.py --storage redis
```

For more details, see [SESSION_STORAGE_IMPLEMENTATION.md](SESSION_STORAGE_IMPLEMENTATION.md).

## Project Structure

```
scheduly/
├── app.py                           # Main FastAPI application with all API endpoints
├── requirements.txt                 # Python dependencies
├── README.md                       # This file
├── SESSION_STORAGE_IMPLEMENTATION.md # Session storage documentation
│
├── src/                            # Core application code
│   ├── models/                     # Data models and schemas
│   ├── services/                   # Business logic services
│   │   ├── schedule/               # Schedule building and optimization
│   │   ├── catalog/                # Course catalog integration
│   │   ├── requirements/           # Degree requirements management
│   │   └── storage/                # Session storage backends
│   └── agents/                     # AI and external service integrations
│
└── scripts/                        # Utility scripts
    ├── setup_env.py                # Environment configuration
    ├── migrate_sessions.py         # Session data migration
    └── test_backend.py             # Testing and validation
```

## Development

The backend is designed to be:
- **Stateless**: Each request is independent (except for session management)
- **Resilient**: Graceful fallbacks when external services fail
- **Fast**: In-memory caching reduces API calls
- **Extensible**: Easy to add new schools, constraint types, or solvers
