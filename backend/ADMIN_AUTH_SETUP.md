# Admin authentication deployment setup

The admin authentication implementation requires these Render/backend environment variables:

| Variable | Purpose |
|---|---|
| `ADMIN_EMAIL` | The single administrator login email |
| `ADMIN_PASSWORD` | Initial administrator password; use a unique high-entropy value |
| `ADMIN_RECOVERY_EMAIL` | Inbox that receives one-time password-reset links |
| `JWT_SECRET` | High-entropy random secret used to sign admin sessions; do not reuse another application's secret |
| `PUBLIC_SITE_URL` | Exact public frontend origin used to construct reset links, e.g. `https://your-domain.example` |
| `CORS_ORIGINS` | Comma-separated exact trusted frontend origins, e.g. `https://your-domain.example`; wildcard values are rejected |
| `EMERGENT_EMAIL_KEY` | Managed email integration key used to send reset links |
| `EMAIL_FROM_NAME` | Sender display name for admin recovery emails |
| `EMAIL_REPLY_TO` | Optional reply-to address |

Existing backend settings `MONGO_URL` and `DB_NAME` are also required.

## Behavior

- Admin sessions are JWTs with an eight-hour expiry.
- Passwords are stored as bcrypt hashes in MongoDB.
- Five failed attempts from one IP/email pair trigger a 15-minute lockout.
- Password reset links are single-use and expire after 30 minutes.
- Password reset invalidates all previously issued admin sessions.
- Logout revokes the active admin token and clears the HttpOnly cookie.
- The backend sets the session as an `HttpOnly`, `Secure`, `SameSite=Lax` cookie when the frontend and API use the same site (for example, `https://flareonix.in` and `https://api.flareonix.in`). Keep credentialed CORS enabled for the exact frontend origin.. The frontend never reads or stores the JWT in JavaScript storage.
- Passwords must be at least 12 characters, include letters and numbers, and remain within bcrypt's 72-byte input limit.

## Deployment caution

Do not deploy until every required variable is configured in the backend host, the exact frontend origin is confirmed, and cross-site cookie behavior has been tested in supported browsers. Do not run admin integration tests against production: they write directly to MongoDB and mutate content. Run them only against a dedicated test database. Admin integration requests must authenticate with the `admin_token` cookie.
