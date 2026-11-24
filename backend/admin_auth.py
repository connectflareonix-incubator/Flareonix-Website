"""Admin sign-in: bcrypt password in MongoDB, short-lived JWT, lockout, and one-time email reset links."""
import os
import re
import uuid
import hashlib
import secrets
import logging
from datetime import datetime, timezone, timedelta
from html import escape

import bcrypt
import jwt
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from email_service import send_email

logger = logging.getLogger(__name__)

ADMIN_EMAIL = os.environ["ADMIN_EMAIL"].strip().lower()
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
ADMIN_RECOVERY_EMAIL = os.environ["ADMIN_RECOVERY_EMAIL"].strip().lower()
JWT_SECRET = os.environ["JWT_SECRET"]
PUBLIC_SITE_URL = os.environ["PUBLIC_SITE_URL"].rstrip("/")

COOKIE = "admin_token"
TOKEN_HOURS = 8
MAX_FAILS = 5
GLOBAL_MAX_FAILS = 25
LOCK_MINUTES = 15
RESET_MINUTES = 30
RESETS_PER_HOUR = 3
EXPIRED = "Your admin session has expired. Please sign in again."


def _now():
    return datetime.now(timezone.utc)


def _hash(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def _check(pw: str, hashed: str) -> bool:
    try:
        raw = pw.encode("utf-8")
        # bcrypt only processes passwords up to 72 bytes; reject longer values rather than silently truncating.
        if len(raw) > 72:
            return False
        return bcrypt.checkpw(raw, (hashed or "").encode())
    except (ValueError, TypeError):
        return False


def _sha(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for", "")
    return fwd.split(",")[0].strip() or (request.client.host if request.client else "unknown")


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    return f"{name[:2]}***@{domain}"


def _email_shell(body: str) -> str:
    return (
        '<table role="presentation" width="100%" style="background:#0D0D0D"><tr><td style="padding:32px;'
        'font-family:Arial,sans-serif;color:#F5F5F5">'
        '<p style="font-size:20px;font-weight:bold;color:#FF6B00;margin:0 0 16px">Flareonix Admin</p>'
        f"{body}"
        '<p style="font-size:12px;color:#888;margin-top:24px">Sent by Flareonix. We will never ask you '
        "to share your password by email or phone.</p></td></tr></table>"
    )


class LoginInput(BaseModel):
    email: str = Field(..., max_length=200)
    password: str = Field(..., min_length=1, max_length=200)


class ResetInput(BaseModel):
    token: str = Field(..., min_length=20, max_length=200)
    new_password: str = Field(..., min_length=12, max_length=128)


async def ensure_admin_credentials(db):
    """Seed the admin hash. Changing ADMIN_PASSWORD in the hosting settings makes it the new password."""
    await db.login_attempts.create_index("identifier")
    await db.admin_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.admin_reset_tokens.create_index("token_hash")
    await db.admin_audit.create_index("created_at")
    doc = await db.admin_credentials.find_one({"email": ADMIN_EMAIL}, {"_id": 0, "env_hash": 1})
    if doc and _check(ADMIN_PASSWORD, doc.get("env_hash")):
        return
    h = _hash(ADMIN_PASSWORD)
    await db.admin_credentials.update_one(
        {"email": ADMIN_EMAIL},
        {"$set": {"email": ADMIN_EMAIL, "password_hash": h, "env_hash": h,
                  "updated_at": _now().isoformat(), "updated_via": "hosting_settings"},
         "$inc": {"token_version": 1}},
        upsert=True,
    )


def build_admin_auth(db):
    router = APIRouter(prefix="/api/admin", tags=["admin-auth"])

    async def audit(action: str, request: Request, detail: str = ""):
        await db.admin_audit.insert_one({
            "id": str(uuid.uuid4()), "action": action, "actor": "admin", "ip": _ip(request),
            "detail": detail[:200], "created_at": _now().isoformat(),
        })

    async def verify_admin(request: Request) -> str:
        token = request.cookies.get(COOKIE)
        if not token:
            raise HTTPException(401, "Admin sign-in required")
        try:
            claims = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.PyJWTError:
            raise HTTPException(401, EXPIRED)
        doc = await db.admin_credentials.find_one({"email": claims.get("sub")}, {"_id": 0, "token_version": 1})
        if claims.get("type") != "admin" or not doc or doc.get("token_version") != claims.get("ver"):
            raise HTTPException(401, EXPIRED)
        return claims["sub"]

    async def _locked(ident: str) -> bool:
        rec = await db.login_attempts.find_one({"identifier": ident}, {"_id": 0})
        return bool(rec and rec.get("locked_until", "") > _now().isoformat())

    async def _fail(ident: str, limit: int):
        rec = await db.login_attempts.find_one({"identifier": ident}, {"_id": 0}) or {}
        count = rec.get("count", 0) + 1
        upd = {"identifier": ident, "count": count, "last_failed": _now().isoformat()}
        if count >= limit:
            upd.update(count=0, locked_until=(_now() + timedelta(minutes=LOCK_MINUTES)).isoformat())
        await db.login_attempts.update_one({"identifier": ident}, {"$set": upd}, upsert=True)

    @router.post("/login")
    async def login(inp: LoginInput, request: Request, response: Response):
        email = inp.email.strip().lower()
        ident, glob = f"{_ip(request)}:{email}", f"global:{email}"
        if await _locked(ident) or await _locked(glob):
            raise HTTPException(429, f"Too many failed attempts. Try again in {LOCK_MINUTES} minutes or reset your password.")
        doc = await db.admin_credentials.find_one({"email": ADMIN_EMAIL}, {"_id": 0})
        ok = bool(doc) and _check(inp.password, doc["password_hash"]) and email == ADMIN_EMAIL
        if not ok:
            await _fail(ident, MAX_FAILS)
            await _fail(glob, GLOBAL_MAX_FAILS)
            await audit("login_failed", request, email)
            raise HTTPException(401, "Invalid email or password")
        await db.login_attempts.delete_many({"identifier": {"$in": [ident, glob]}})
        token = jwt.encode({"sub": ADMIN_EMAIL, "type": "admin", "ver": doc.get("token_version", 1),
                            "exp": _now() + timedelta(hours=TOKEN_HOURS)}, JWT_SECRET, algorithm="HS256")
        response.set_cookie(COOKIE, token, httponly=True, secure=True, samesite="none",
                            max_age=TOKEN_HOURS * 3600, path="/")
        await audit("login_success", request)
        return {"success": True, "email": ADMIN_EMAIL, "expires_in": TOKEN_HOURS * 3600}

    @router.post("/logout")
    async def logout(request: Request, response: Response):
        # Revoke the current token as well as clearing the browser cookie.
        try:
            admin_email = await verify_admin(request)
            await db.admin_credentials.update_one(
                {"email": admin_email}, {"$inc": {"token_version": 1}}
            )
        except HTTPException:
            # Logout remains idempotent for expired or already-invalid sessions.
            pass
        response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="none")
        return {"success": True}

    @router.get("/verify")
    async def verify(request: Request):
        return {"success": True, "admin": await verify_admin(request)}

    @router.post("/forgot-password")
    async def forgot_password(request: Request):
        hour_ago = (_now() - timedelta(hours=1)).isoformat()
        if await db.admin_reset_tokens.count_documents({"created_at": {"$gt": hour_ago}}) >= RESETS_PER_HOUR:
            await audit("reset_throttled", request)
            raise HTTPException(429, "Reset links were sent recently. Check the recovery inbox or try again in an hour.")
        raw = secrets.token_urlsafe(32)
        await db.admin_reset_tokens.insert_one({
            "token_hash": _sha(raw), "used": False, "created_at": _now().isoformat(),
            "expires_at": _now() + timedelta(minutes=RESET_MINUTES),
        })
        link = f"{PUBLIC_SITE_URL}/admin/reset-password?token={raw}"
        body = (
            "<p>Someone asked to reset the Flareonix admin password.</p>"
            f'<p><a href="{escape(link)}" style="display:inline-block;background:#FF6B00;color:#ffffff;'
            'padding:12px 20px;border-radius:24px;text-decoration:none;font-weight:bold">Choose a new password</a></p>'
            f"<p>This link works once and expires in {RESET_MINUTES} minutes. If you did not ask for this, "
            "ignore this email and the current password keeps working.</p>"
        )
        await send_email(to=ADMIN_RECOVERY_EMAIL, subject="Reset your Flareonix admin password",
                         html=_email_shell(body))
        await audit("reset_requested", request)
        return {"success": True, "sent_to": _mask(ADMIN_RECOVERY_EMAIL), "expires_minutes": RESET_MINUTES}

    @router.post("/reset-password")
    async def reset_password(inp: ResetInput, request: Request, response: Response):
        pw = inp.new_password
        if len(pw.encode("utf-8")) > 72:
            raise HTTPException(400, "Password must be no more than 72 UTF-8 bytes")
        if not (re.search(r"[A-Za-z]", pw) and re.search(r"\d", pw)):
            raise HTTPException(400, "Use at least 12 characters, including letters and numbers")
        rec = await db.admin_reset_tokens.find_one_and_update(
            {"token_hash": _sha(inp.token), "used": False, "expires_at": {"$gt": _now()}},
            {"$set": {"used": True, "used_at": _now().isoformat()}},
        )
        if not rec:
            raise HTTPException(400, "This reset link is invalid, already used or expired. Request a new one.")
        await db.admin_credentials.update_one(
            {"email": ADMIN_EMAIL},
            {"$set": {"password_hash": _hash(pw), "updated_at": _now().isoformat(), "updated_via": "reset_link"},
             "$inc": {"token_version": 1}},
        )
        await db.admin_reset_tokens.update_many({"used": False}, {"$set": {"used": True}})
        await db.login_attempts.delete_many({})
        response.delete_cookie(COOKIE, path="/", secure=True, httponly=True, samesite="none")
        await audit("password_reset", request)
        notice = ("<p>The Flareonix admin password was just changed using a reset link, and all admin "
                  "sessions were signed out.</p><p>If this was not you, request a new reset link straight away.</p>")
        try:
            await send_email(to=ADMIN_RECOVERY_EMAIL, subject="Your Flareonix admin password was changed",
                             html=_email_shell(notice))
        except HTTPException:
            logger.warning("Password-changed notice could not be emailed")
        return {"success": True}

    return router, verify_admin
