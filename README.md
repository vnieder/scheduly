# Scheduly 

## Demo

https://github.com/user-attachments/assets/3fb7f300-0e83-4594-9734-f226418a7cea

## Contributors
Vincent Niedermayer - VMN16@pitt.edu
Ava Luu - AML470@pitt.edu

## Structure

```
scheduly/
├── backend/   # FastAPI service (moved from repo root)
└── frontend/  # Next.js 15 app (TypeScript + Tailwind v4)
```

## Local Development

### Prereqs

- Python 3.10+
- Node.js 18+ (or 20+ recommended) and npm

### 1) Backend (FastAPI)

From the repo root:

```bash
cd backend
pip install -r requirements.txt
export APP_MODE=development
uvicorn app:app --reload --port 8000
```

Notes:

- You can also run from repo root with: `python -m uvicorn backend.app:app --reload --port 8000`.
- See `backend/CONFIGURATION.md` for environment variables and modes.

### 2) Frontend (Next.js + Tailwind)

From the repo root:

```bash
cd frontend
npm install
cp .env.local.example .env.local
# adjust NEXT_PUBLIC_API_URL as needed
npm run dev
```

Open http://localhost:3000.

## Environment Variables

### Backend

See `backend/CONFIGURATION.md`. Common dev values:

```bash
APP_MODE=development
# For production mode you will need:
# GEMINI_API_KEY=your_key
```

### Frontend

Create `frontend/.env.local`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Deployment

### Backend (Railway)

- Deploy the `backend/` directory as a Python service.
- Set required environment variables (see `backend/CONFIGURATION.md`).
- Expose the HTTP port (e.g., 8000) and set `uvicorn backend.app:app` (or `python -m uvicorn backend.app:app`) as the start command.
- Ensure CORS in `backend/app.py` includes your Vercel domain(s).

### Frontend (Vercel)

- Import the `frontend/` as a Vercel project.
- Set `NEXT_PUBLIC_API_URL` to your Railway backend public URL.
- Build command: `npm run build` (default from Next.js).

## Notes

- All original backend code lives in `backend/` unchanged in structure.
- Frontend is a fresh Next.js 15 + React 19 app with Tailwind CSS v4.
