# Scheduly Backend Configuration

## Dual Mode System

The Scheduly backend now supports two distinct modes:

### Development Mode (`APP_MODE=development`)
- **Purpose**: Fast, reliable responses for frontend development
- **Features**:
  - Returns hardcoded Pitt CS data
  - No AI API calls (no rate limiting)
  - Fast response times
  - Predictable data structure
  - Only supports Pitt University
- **Use Case**: Frontend team development, testing, demos

### Production Mode (`APP_MODE=production`)
- **Purpose**: Dynamic, AI-powered responses for any university
- **Features**:
  - AI-generated requirements for any school/major
  - AI-searched prerequisites
  - Dynamic course catalog integration
  - Multi-university support
  - Full agentic behavior
- **Use Case**: Production deployment, multi-university support

## Environment Variables

```bash
# Application Mode (required)
APP_MODE=development  # or "production"

# AI Configuration (required for production mode)
GEMINI_API_KEY=your_gemini_api_key_here

# Session Storage (choose one)
REDIS_URL=redis://localhost:6379/0
# or
DATABASE_URL=postgresql+asyncpg://user:pass@host:port/db
# or (development only)
SESSION_STORAGE=memory

# Default Values
DEFAULT_TERM=2251
DEFAULT_SCHOOL=Pitt
MAX_COURSES_PER_SEMESTER=6
MAX_COURSE_SELECTION=10
SESSION_TIMEOUT_HOURS=24
```

## Quick Start

### For Frontend Development:
```bash
export APP_MODE=development
uvicorn app:app --reload --port 8000
```

### For Production:
```bash
export APP_MODE=production
export GEMINI_API_KEY=your_key_here
uvicorn app:app --reload --port 8000
```

## Mode Behavior Differences

| Feature | Development Mode | Production Mode |
|---------|------------------|-----------------|
| Requirements | Hardcoded Pitt CS | AI-generated for any school |
| Prerequisites | Hardcoded Pitt CS | AI-searched |
| School Support | Pitt only | Any university |
| AI API Calls | Minimal (preferences only) | Full AI integration |
| Response Time | Fast | Slower (AI calls) |
| Rate Limiting | None | Subject to AI API limits |
| Data Consistency | Always consistent | Dynamic |

## Migration from Legacy System

The old `USE_AI_PREREQUISITES` flag is now deprecated. Use `APP_MODE` instead:

- `USE_AI_PREREQUISITES=false` → `APP_MODE=development`
- `USE_AI_PREREQUISITES=true` → `APP_MODE=production`
