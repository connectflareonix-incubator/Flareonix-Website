# Flareonix: Self-Hosting Setup Guide

Stack: React (CRA + craco) frontend, FastAPI backend, MongoDB.

## 1. Requirements
- Node 18+ and Yarn
- Python 3.11+
- MongoDB 6+ (local or MongoDB Atlas)

## 2. Backend
```bash
cd backend
cp .env.example .env        # then fill in the values
pip install -r requirements.txt
# emergentintegrations is not on PyPI; install it from:
pip install emergentintegrations --extra-index-url https://d33sy5i8bnduwe.cloudfront.net/simple/
uvicorn server:app --host 0.0.0.0 --port 8001 --reload
```
All API routes are served under `/api`.

| Variable | Purpose |
|---|---|
| `MONGO_URL` | MongoDB connection string |
| `DB_NAME` | Database name |
| `CORS_ORIGINS` | Comma-separated allowed frontend origins |
| `ADMIN_EMAIL` / `ADMIN_PASSWORD` | Admin panel login. Changing `ADMIN_PASSWORD` and restarting resets the admin password |
| `ADMIN_RECOVERY_EMAIL` | Inbox that receives "Forgot password" reset links |
| `JWT_SECRET` | Random secret that signs admin sessions (64 hex characters) |
| `PUBLIC_SITE_URL` | Public frontend address used in reset-link emails, e.g. `https://flareonix.in` |
| `EMERGENT_EMAIL_KEY` / `EMAIL_FROM_NAME` / `EMAIL_REPLY_TO` | Transactional email (Emergent Managed Email, powered by Resend) |
| `EMERGENT_LLM_KEY` | Key used by the AI Tools (Claude Sonnet 5.5, Claude Opus 5.5, GPT 6 Luna) |

### Resetting the admin password
1. **From the website:** `/admin` → "Forgot password?" emails a one-time link (valid 30 minutes) to `ADMIN_RECOVERY_EMAIL`.
2. **From your hosting settings:** set a new `ADMIN_PASSWORD` and restart the backend; it replaces the current password and signs out old sessions.

## 3. Frontend
```bash
cd frontend
cp .env.example .env        # set REACT_APP_BACKEND_URL to your backend URL
yarn install
yarn start                  # dev on http://localhost:3000
yarn build                  # production build in frontend/build
```

## 4. Production deployment (outline)
- Backend: any Python host (Render, Railway, Fly.io, VPS) running `uvicorn server:app --host 0.0.0.0 --port $PORT`.
- Frontend: deploy `frontend/build` to any static host (Vercel, Netlify, Cloudflare Pages). Set `REACT_APP_BACKEND_URL` at build time.
- Database: MongoDB Atlas. Put its connection string in `MONGO_URL`.
- Set `CORS_ORIGINS` to your real frontend domain.

## 5. Services that currently run through Emergent (unchanged)
These keep working as they are today. Switch them only if you host somewhere else:

| Feature | Where in code | Current provider | Self-hosted replacement |
|---|---|---|---|
| Google sign-in | `frontend/src/context/AuthContext.jsx` (login redirect), `backend/server.py` (`/api/auth/session` exchange) | Emergent-managed Google login | Your own Google OAuth Client ID/Secret from Google Cloud Console |
| AI Tools | `backend/ai_tools.py` | Emergent LLM key (`emergentintegrations`) | Your own Anthropic API key with the official `anthropic` SDK |
| Logo image | `frontend/src/config/constants.js` | Emergent asset CDN | Copy the image into `frontend/public` and point to it |

Admin email/password login, the CMS, blog, consultation forms, analytics and animations are standard code and do not depend on Emergent.
