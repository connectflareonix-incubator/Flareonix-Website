# Flareonix Test Credentials

## Admin Panel (`/admin`)
- Email: value of `ADMIN_EMAIL` in `/app/backend/.env` (connectflareonix@gmail.com)
- Password: value of `ADMIN_PASSWORD` in `/app/backend/.env` (read it from the file; never write it in this repo — the repos are public)
- Auth: `POST /api/admin/login` {email, password} -> `{token}` + httpOnly `admin_token` cookie. Send `Authorization: Bearer <token>` on `/api/admin/*`.
- Other endpoints: `GET /api/admin/verify`, `POST /api/admin/logout`, `POST /api/admin/forgot-password` (emails a reset link to ADMIN_RECOVERY_EMAIL; max 3/hour), `POST /api/admin/reset-password` {token, new_password}
- Lockout: 5 failed logins per IP+email -> 15 min (429). HTTP Basic auth no longer works.
- Reset: if ADMIN_PASSWORD changes in .env and the backend restarts, it becomes the admin password again.

## User Authentication
- Strategy: Emergent Google OAuth (`/login`), session via `session_token` cookie or `Authorization: Bearer <token>` (7 days)

## Pre-seeded QA user session (preview DB)
- user_id `user_qa_test`, email `qa.tester@example.com`
- Cookie `session_token=qa_session_token_123` (or `Authorization: Bearer qa_session_token_123`)

## Backend env
- `EMERGENT_LLM_KEY` (AI tools: claude-sonnet-5-5, claude-opus-5-5, gpt-6-luna)
- `EMERGENT_EMAIL_KEY`, `EMAIL_FROM_NAME`, `ADMIN_RECOVERY_EMAIL` (aayushmanjhariya@gmail.com), `PUBLIC_SITE_URL`, `JWT_SECRET`
