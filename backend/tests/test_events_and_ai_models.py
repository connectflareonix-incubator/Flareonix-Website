"""Events (public/admin/comments/waitlist) + AI model picker/SSE tests"""
import os
import json
import uuid
import pytest
import requests
from dotenv import load_dotenv

load_dotenv("/app/frontend/.env")
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL").rstrip("/")
ADMIN = ("connectflareonix@gmail.com", "Flareonix@admin02")
QA_COOKIE = {"session_token": "qa_session_token_123"}


@pytest.fixture(scope="module")
def created_ids():
    ids = []
    yield ids
    for i in ids:
        requests.delete(f"{BASE_URL}/api/admin/events/{i}", auth=ADMIN)


def _create(payload, created_ids):
    r = requests.post(f"{BASE_URL}/api/admin/events", json=payload, auth=ADMIN)
    if r.status_code == 200:
        created_ids.append(r.json()["id"])
    return r


def _put(ev, **changes):
    body = {k: ev.get(k) for k in [
        "title", "date", "venue", "theme", "description", "short_description",
        "cover_image_url", "guests", "highlights", "registration_link",
        "registration_button_text", "capacity", "status", "slug", "published", "display_order"]}
    body = {k: v for k, v in body.items() if v is not None}
    body.update(changes)
    return requests.put(f"{BASE_URL}/api/admin/events/{ev['id']}", json=body, auth=ADMIN)


# ---- Public events ----
class TestPublicEvents:
    def test_list_only_published_no_spots(self):
        r = requests.get(f"{BASE_URL}/api/events")
        assert r.status_code == 200
        for ev in r.json():
            assert ev.get("published") is True
            assert "spots_filled" not in ev
            assert ev.get("slug") != "fft-001"

    def test_fft_hidden(self):
        assert requests.get(f"{BASE_URL}/api/events/fft-001").status_code == 404

    def test_interest_removed(self):
        r = requests.post(f"{BASE_URL}/api/events/fft-001/interest")
        assert r.status_code in (404, 405)


# ---- Admin events ----
class TestAdminEvents:
    def test_admin_requires_auth(self):
        assert requests.get(f"{BASE_URL}/api/admin/events").status_code == 401

    def test_admin_lists_fft_draft(self):
        r = requests.get(f"{BASE_URL}/api/admin/events", auth=ADMIN)
        assert r.status_code == 200
        fft = [e for e in r.json() if e.get("slug") == "fft-001"]
        assert len(fft) == 1
        f = fft[0]
        assert f["published"] is False
        assert f["venue"] == "Gautami Heights, Kashipur, Uttarakhand"
        assert "20 December 2026" in f["date"]
        assert "Delhi" not in json.dumps(f) and "zite.so" not in json.dumps(f)

    def test_slug_autogen(self, created_ids):
        r = _create({"title": "TEST_ Auto Slug Event " + uuid.uuid4().hex[:4]}, created_ids)
        assert r.status_code == 200
        d = r.json()
        assert d["slug"].startswith("test-auto-slug-event-")
        assert d["published"] is False

    def test_invalid_slug(self, created_ids):
        assert _create({"title": "TEST_ bad", "slug": "Bad Slug"}, created_ids).status_code == 400
        assert _create({"title": "TEST_ bad", "slug": "bad slug"}, created_ids).status_code == 400

    def test_duplicate_slug(self, created_ids):
        assert _create({"title": "TEST_ dup", "slug": "fft-001"}, created_ids).status_code == 400

    def test_http_link_rejected(self, created_ids):
        r = _create({"title": "TEST_ link", "registration_link": "http://x.com"}, created_ids)
        assert r.status_code == 400

    def test_invalid_status(self, created_ids):
        assert _create({"title": "TEST_ st", "status": "cancelled"}, created_ids).status_code == 422


# ---- Publish / comments / waitlist flow ----
class TestPublishFlow:
    def test_publish_comments_waitlist(self, created_ids):
        slug = "test-pub-" + uuid.uuid4().hex[:6]
        r = _create({"title": "TEST_ Publish", "slug": slug,
                     "registration_link": "https://example.com/reg"}, created_ids)
        assert r.status_code == 200
        ev = r.json()
        assert requests.get(f"{BASE_URL}/api/events/{slug}").status_code == 404
        # comments on unpublished -> 404
        assert requests.get(f"{BASE_URL}/api/events/{slug}/comments").status_code == 404
        assert requests.post(f"{BASE_URL}/api/events/{slug}/comments", json={"content": "hi"},
                             cookies=QA_COOKIE).status_code == 404

        assert _put(ev, published=True).status_code == 200
        lst = requests.get(f"{BASE_URL}/api/events").json()
        assert any(e["slug"] == slug for e in lst)
        for key in (slug, ev["id"]):
            g = requests.get(f"{BASE_URL}/api/events/{key}")
            assert g.status_code == 200 and g.json()["id"] == ev["id"]
            assert "spots_filled" not in g.json()

        # comments
        assert requests.post(f"{BASE_URL}/api/events/{slug}/comments",
                             json={"content": "TEST_ comment"}).status_code == 401
        c = requests.post(f"{BASE_URL}/api/events/{slug}/comments",
                          json={"content": "TEST_ comment"}, cookies=QA_COOKIE)
        assert c.status_code == 200, c.text
        assert "user_email" not in c.json()
        cid = c.json()["id"]
        reply = requests.post(f"{BASE_URL}/api/events/{ev['id']}/comments",
                              json={"content": "TEST_ reply", "parent_id": cid}, cookies=QA_COOKIE)
        assert reply.status_code == 200
        lc = requests.get(f"{BASE_URL}/api/events/{slug}/comments")
        assert lc.status_code == 200
        assert len(lc.json()) == 2
        assert all("user_email" not in x for x in lc.json())
        assert "qa.tester@example.com" not in lc.text
        lst = requests.get(f"{BASE_URL}/api/events").json()
        assert [e for e in lst if e["slug"] == slug][0]["comment_count"] == 2

        # waitlist closed
        w = requests.post(f"{BASE_URL}/api/events/{slug}/waitlist",
                          json={"name": "TEST", "email": "test@example.com"})
        assert w.status_code == 403
        assert "not open yet" in w.json()["detail"]

        # unpublish -> hidden
        assert _put(ev, published=False).status_code == 200
        assert requests.get(f"{BASE_URL}/api/events/{slug}").status_code == 404
        assert requests.get(f"{BASE_URL}/api/events/{ev['id']}").status_code == 404


# ---- AI models / SSE ----
def _stream(model, cookies=QA_COOKIE):
    r = requests.post(f"{BASE_URL}/api/ai/generate", cookies=cookies, stream=True, timeout=180,
                      json={"tool": "caption", "prompt": "TEST_ caption for a chai startup",
                            "model": model})
    return r


class TestAI:
    def test_models(self):
        r = requests.get(f"{BASE_URL}/api/ai/models")
        assert r.status_code == 200
        d = r.json()
        assert [m["id"] for m in d] == ["claude-sonnet-5-5", "claude-opus-5-5", "gpt-6-luna"]
        assert [m["id"] for m in d if m["default"]] == ["claude-sonnet-5-5"]

    def test_unknown_model(self):
        assert _stream("gpt-x").status_code == 400

    def test_unauth(self):
        assert _stream("gpt-6-luna", cookies={}).status_code == 401

    @pytest.mark.parametrize("model", ["gpt-6-luna", "claude-sonnet-5-5", "claude-opus-5-5"])
    def test_stream(self, model):
        r = _stream(model)
        assert r.status_code == 200
        assert "text/event-stream" in r.headers.get("content-type", "")
        frames = []
        for line in r.iter_lines(decode_unicode=True):
            if line and line.startswith("data: "):
                frames.append(json.loads(line[6:]))
        types = [f["type"] for f in frames]
        assert "error" not in types, frames[-1]
        assert types.count("delta") >= 1
        assert types[-1] == "done"
        done = frames[-1]
        assert done["model"] == model
        h = requests.get(f"{BASE_URL}/api/ai/history", cookies=QA_COOKIE).json()
        item = [x for x in h if x["id"] == done["id"]]
        assert item and item[0]["model"] == model and len(item[0]["response"]) > 10
        requests.delete(f"{BASE_URL}/api/ai/history/{done['id']}", cookies=QA_COOKIE)
