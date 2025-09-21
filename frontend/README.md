## Scheduly Frontend

Next.js 15 + React 19 Scheduler app using TypeScript and Tailwind CSS v4.

### Stack

- Next.js 15
- React 19
- TypeScript
- Tailwind CSS v4
- ESLint

### Environment

Create `.env.local` (see `env.example`):

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### Development

```bash
npm install
cp env.example .env.local
npm run dev
```

Open http://localhost:3000.

### Build & Start

```bash
npm run build
npm start
```

### Deployment (Vercel)

- Connect this `frontend/` directory as a Vercel project.
- Set environment variable `NEXT_PUBLIC_API_URL` to your Railway backend URL.
- Default build command `npm run build` is supported.

### Backend API (used by the app)

- `GET /health` — check mode and features
- `POST /build` — create initial schedule, returns `session_id` and `plan`
- `POST /optimize` — adjust existing schedule with new preferences
- `POST /catalog/sections` — fetch sections by course codes

### Notes

- Tailwind v4 is configured via `@import "tailwindcss"` in `src/app/globals.css`.
- Configure CORS on the backend to allow your Vercel domain(s).
