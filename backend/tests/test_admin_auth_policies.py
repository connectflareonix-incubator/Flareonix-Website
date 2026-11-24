"""Iteration 6: admin token auth, lockout, reset-password flow (no email), policies public/admin."""
import os
import hashlib
import secrets
from datetime import datetime, timezone, timedelta

import pytest
import requests
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv("/app/frontend/.env")
load_dotenv("/app/backend/.env")
BASE_URL = os.environ["REACT_APP_BACKEND_URL"].rstrip("/")
API = f"{BASE_URL}/api"
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"]
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
_db = MongoClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
SLUGS = ["privacy", "terms", "event-terms", "refunds", "media-consent", "pitch-arena", "grievance"]


def login(pw=ADMIN_PASSWORD, email=ADMIN_EMAIL, headers=None):
    return requests.post(f"{API}/admin/login", json={"email": email, "password": pw}, headers=headers or {})


def bearer(tok):
    return {"Authorization": f"Bearer {tok}"}


@pytest.fixture(scope="module")
def token():
    r = login()
    assert r.status_code == 200, r.text
    return r.json()["token"]


# ---- Exposed password / legacy Basic auth ----
class TestLegacy:
    def test_frontend_src_has_no_password(self):
        import subprocess
        out = subprocess.run(["grep", "-rl", "Flareonix@admin02\\|ADMIN_CREDENTIALS", "/app/frontend/src"],
                             capture_output=True, text=True).stdout
        assert out.strip() == ""

    def test_basic_auth_rejected(self):
        r = requests.get(f"{API}/admin/dashboard", auth=(ADMIN_EMAIL, ADMIN_PASSWORD))
        assert r.status_code == 401

    def test_no_auth_rejected(self):
        assert requests.get(f"{API}/admin/verify").status_code == 401
        assert requests.get(f"{API}/admin/policies").status_code == 401


# ---- Login + bearer on admin endpoints ----
class TestLogin:
    def test_login_ok_and_cookie(self):
        r = login()
        assert r.status_code == 200
        d = r.json()
        assert isinstance(d["token"], str) and d["email"] == ADMIN_EMAIL.lower()
        sc = r.headers.get("set-cookie", "")
        assert "admin_token=" in sc and "HttpOnly" in sc

    def test_bcrypt_hash(self):
        doc = _db.admin_credentials.find_one({"email": ADMIN_EMAIL.lower()})
        assert doc["password_hash"].startswith("$2b$")
        assert isinstance(doc["token_version"], int)

    @pytest.mark.parametrize("path", ["/admin/verify", "/admin/events", "/admin/policies", "/admin/dashboard",
                                      "/admin/users", "/admin/blog/posts", "/admin/team", "/admin/signups"])
    def test_bearer_endpoints(self, token, path):
        r = requests.get(f"{API}{path}", headers=bearer(token))
        assert r.status_code == 200, f"{path}: {r.status_code} {r.text[:200]}"

    def test_wrong_password(self):
        r = login("wrong-password-xyz", headers={"X-Forwarded-For": "10.66.66.1"})
        assert r.status_code == 401
        assert r.json()["detail"] == "Invalid email or password"
        _db.login_attempts.delete_many({"identifier": {"$in": [f"10.66.66.1:{ADMIN_EMAIL.lower()}"]}})

    def test_lockout_after_5(self):
        ip = "10.66.66.2"
        ident = f"{ip}:{ADMIN_EMAIL.lower()}"
        try:
            codes = [login("bad-pw-123", headers={"X-Forwarded-For": ip}).status_code for _ in range(5)]
            assert codes == [401] * 5
            r = login("bad-pw-123", headers={"X-Forwarded-For": ip})
            assert r.status_code == 429
            # correct password also blocked while locked
            assert login(headers={"X-Forwarded-For": ip}).status_code == 429
        finally:
            _db.login_attempts.delete_many({"identifier": ident})
            _db.login_attempts.delete_many({"identifier": f"global:{ADMIN_EMAIL.lower()}"})


# ---- Policies ----
class TestPolicies:
    def test_public_list(self):
        r = requests.get(f"{API}/policies")
        assert r.status_code == 200
        d = r.json()
        assert [p["slug"] for p in d] == SLUGS
        assert all("body_md" not in p and "_id" not in p for p in d)

    def test_public_get(self):
        r = requests.get(f"{API}/policies/privacy")
        assert r.status_code == 200
        d = r.json()
        assert len(d["body_md"]) > 500 and "_id" not in d
        assert requests.get(f"{API}/policies/nope-xyz").status_code == 404

    def test_admin_writes_need_token(self):
        assert requests.patch(f"{API}/admin/policies/privacy/notice", json={"show_draft_notice": False}).status_code == 401
        assert requests.put(f"{API}/admin/policies/privacy", json={"title": "x", "body_md": "y" * 30}).status_code == 401

    def test_notice_toggle(self, token):
        try:
            r = requests.patch(f"{API}/admin/policies/grievance/notice", json={"show_draft_notice": False},
                               headers=bearer(token))
            assert r.status_code == 200 and r.json()["show_draft_notice"] is False
            assert requests.get(f"{API}/policies/grievance").json()["show_draft_notice"] is False
        finally:
            r = requests.patch(f"{API}/admin/policies/grievance/notice", json={"show_draft_notice": True},
                               headers=bearer(token))
            assert r.json()["show_draft_notice"] is True

    def test_put_creates_version(self, token):
        cur = requests.get(f"{API}/admin/policies/media-consent", headers=bearer(token)).json()
        body = {"title": cur["title"], "summary": cur["summary"], "body_md": cur["body_md"],
                "show_draft_notice": True, "change_note": "TEST_ QA version check (content unchanged)"}
        r = requests.put(f"{API}/admin/policies/media-consent", json=body, headers=bearer(token))
        assert r.status_code == 200
        assert r.json()["version"] == cur["version"] + 1
        assert r.json()["body_md"] == cur["body_md"]
        v = requests.get(f"{API}/admin/policies/media-consent/versions", headers=bearer(token)).json()
        assert v[0]["version"] == cur["version"] and "body_md" not in v[0]

    def test_put_validation(self, token):
        r = requests.put(f"{API}/admin/policies/terms", json={"title": "ab", "body_md": "short"}, headers=bearer(token))
        assert r.status_code == 422


# ---- Reset flow (direct DB tokens, no emails sent except the "password changed" notice) ----
def _insert_token(expired=False):
    raw = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    # created_at 2h ago so it does not count against the 3/hour forgot-password throttle
    _db.admin_reset_tokens.insert_one({
        "token_hash": hashlib.sha256(raw.encode()).hexdigest(), "used": False,
        "created_at": (now - timedelta(hours=2)).isoformat(),
        "expires_at": now - timedelta(minutes=1) if expired else now + timedelta(minutes=30),
        "qa_test": True,
    })
    return raw


class TestResetFlow:
    NEW_PW = "TESTqaReset2026x"

    def test_reset_flow(self):
        old = login().json()["token"]
        assert requests.get(f"{API}/admin/verify", headers=bearer(old)).status_code == 200
        # weak passwords
        raw = _insert_token()
        r = requests.post(f"{API}/admin/reset-password", json={"token": raw, "new_password": "short1"})
        assert r.status_code in (400, 422)
        r = requests.post(f"{API}/admin/reset-password", json={"token": raw, "new_password": "nodigitsatallhere"})
        assert r.status_code == 400
        # expired
        exp = _insert_token(expired=True)
        r = requests.post(f"{API}/admin/reset-password", json={"token": exp, "new_password": self.NEW_PW})
        assert r.status_code == 400
        # invalid
        r = requests.post(f"{API}/admin/reset-password", json={"token": "x" * 40, "new_password": self.NEW_PW})
        assert r.status_code == 400
        # success
        r = requests.post(f"{API}/admin/reset-password", json={"token": raw, "new_password": self.NEW_PW})
        assert r.status_code == 200, r.text
        assert requests.get(f"{API}/admin/verify", headers=bearer(old)).status_code == 401
        # reused
        r = requests.post(f"{API}/admin/reset-password", json={"token": raw, "new_password": self.NEW_PW})
        assert r.status_code == 400
        # new pw works, old env pw doesn't
        assert login(self.NEW_PW).status_code == 200
        assert login(headers={"X-Forwarded-For": "10.66.66.3"}).status_code == 401
        _db.login_attempts.delete_many({"identifier": {"$in": [f"10.66.66.3:{ADMIN_EMAIL.lower()}",
                                                                f"global:{ADMIN_EMAIL.lower()}"]}})
        _db.admin_reset_tokens.delete_many({"qa_test": True})
