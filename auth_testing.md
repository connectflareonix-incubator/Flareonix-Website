# Admin Auth Testing Playbook (Flareonix)

1. Mongo: `db.admin_credentials.findOne()` -> `password_hash` starts with `$2b$`; `token_version` integer. Indexes: `login_attempts.identifier`, `admin_reset_tokens.expires_at` (TTL), `admin_reset_tokens.token_hash`.
2. Login: `curl -X POST $API/api/admin/login -H 'Content-Type: application/json' -d '{"email":"<ADMIN_EMAIL>","password":"<ADMIN_PASSWORD from backend/.env>"}'` -> `{token}`; then `curl -H "Authorization: Bearer <token>" $API/api/admin/verify`.
3. Wrong password -> 401; 5 wrong in a row from same IP -> 429 lockout (clean up `login_attempts` afterwards).
4. Reset flow without email: insert into `admin_reset_tokens` `{token_hash: sha256(raw), used: false, created_at: iso, expires_at: datetime(now+30m)}` then POST `/api/admin/reset-password` `{token: raw, new_password}`. Old tokens must then return 401 (token_version bumped). Reused token -> 400. Weak password (<12 or no digit) -> 400/422.
5. After any reset test, restore the admin password by setting the hash back: run `ensure_admin_credentials` logic — easiest: `db.admin_credentials.deleteMany({})` then restart backend (re-seeds from ADMIN_PASSWORD in .env).
