"""Events endpoints: public (published only) list/detail + comments, and admin CRUD."""
import re
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
from models_extra import (
    Event, EventInput, EventComment, EventCommentCreate,
    WaitlistEntry, WaitlistEntryCreate,
)

# Fields never sent to the public site
PUBLIC_HIDE = {"_id": 0, "spots_filled": 0}
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _serialize(d: dict) -> dict:
    out = dict(d)
    out.pop("_id", None)
    for k, v in list(out.items()):
        if isinstance(v, datetime):
            out[k] = v.isoformat()
    return out


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def build_events_router(db, verify_admin, get_current_user):
    router = APIRouter(prefix="/api", tags=["events"])

    async def _public_event(key: str) -> dict:
        ev = await db.events.find_one(
            {"published": True, "$or": [{"slug": key}, {"id": key}]}, PUBLIC_HIDE
        )
        if not ev:
            raise HTTPException(404, "Event not found")
        return ev

    async def _clean_input(inp: EventInput, self_id: str = None) -> dict:
        data = inp.model_dump()
        slug = (data.get("slug") or "").strip().lower() or _slugify(data["title"])
        if not SLUG_RE.match(slug):
            raise HTTPException(400, "Slug may only contain lowercase letters, numbers and hyphens")
        clash = await db.events.find_one({"slug": slug, "id": {"$ne": self_id}}, {"_id": 1})
        if clash:
            raise HTTPException(400, "Another event already uses this URL slug")
        data["slug"] = slug
        link = (data.get("registration_link") or "").strip()
        if link and not link.startswith("https://"):
            raise HTTPException(400, "Registration link must start with https://")
        data["registration_link"] = link or None
        return data

    # ============ PUBLIC ============

    @router.get("/events")
    async def list_events():
        items = await db.events.find({"published": True}, PUBLIC_HIDE).sort("display_order", 1).to_list(500)
        counts = await db.event_comments.aggregate([
            {"$match": {"event_id": {"$in": [e["id"] for e in items]}}},
            {"$group": {"_id": "$event_id", "n": {"$sum": 1}}},
        ]).to_list(500)
        by_id = {c["_id"]: c["n"] for c in counts}
        for ev in items:
            ev["comment_count"] = by_id.get(ev["id"], 0)
        return items

    @router.get("/events/{key}")
    async def get_event(key: str):
        return await _public_event(key)

    @router.get("/events/{key}/comments")
    async def list_comments(key: str):
        ev = await _public_event(key)
        return await db.event_comments.find(
            {"event_id": ev["id"]}, {"_id": 0, "user_email": 0, "user_id": 0}
        ).sort("created_at", -1).to_list(500)

    @router.post("/events/{key}/comments")
    async def add_comment(key: str, inp: EventCommentCreate,
                          user: dict = Depends(get_current_user)):
        ev = await _public_event(key)
        if inp.parent_id:
            parent = await db.event_comments.find_one(
                {"id": inp.parent_id, "event_id": ev["id"]}, {"_id": 1}
            )
            if not parent:
                raise HTTPException(404, "Parent comment not found")
        c = EventComment(
            event_id=ev["id"], parent_id=inp.parent_id, user_id=user["user_id"],
            user_name=user["name"], user_email=user["email"],
            user_picture=user.get("picture"), content=inp.content,
        ).model_dump()
        c["created_at"] = c["created_at"].isoformat()
        await db.event_comments.insert_one(c)
        out = _serialize(c)
        out.pop("user_email", None)
        out.pop("user_id", None)
        return out

    # ============ WAITLIST (closed until privacy policy + review are done) ============

    @router.post("/events/{key}/waitlist")
    async def join_waitlist(key: str, inp: WaitlistEntryCreate):
        ev = await _public_event(key)
        enabled = await db.site_settings.find_one({"key": "events_waitlist_enabled"}, {"_id": 0})
        if not (enabled and enabled.get("value") is True):
            raise HTTPException(403, "The waitlist is not open yet")
        email = (inp.email or "").strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
            raise HTTPException(400, "Please enter a valid email address")
        if await db.event_waitlist.find_one({"event_id": ev["id"], "email": email}, {"_id": 1}):
            return {"success": True, "already": True}
        entry = WaitlistEntry(event_id=ev["id"], name=(inp.name or "").strip(), email=email).model_dump()
        entry["created_at"] = entry["created_at"].isoformat()
        await db.event_waitlist.insert_one(entry)
        return {"success": True, "already": False}

    # ============ ADMIN ============

    @router.get("/admin/events")
    async def admin_list_events(_: str = Depends(verify_admin)):
        return await db.events.find({}, {"_id": 0}).sort("display_order", 1).to_list(1000)

    @router.post("/admin/events")
    async def admin_create_event(inp: EventInput, _: str = Depends(verify_admin)):
        ev = Event(**(await _clean_input(inp))).model_dump()
        ev["created_at"] = ev["created_at"].isoformat()
        await db.events.insert_one(ev)
        return _serialize(ev)

    @router.put("/admin/events/{event_id}")
    async def admin_update_event(event_id: str, inp: EventInput,
                                 _: str = Depends(verify_admin)):
        if not await db.events.find_one({"id": event_id}, {"_id": 1}):
            raise HTTPException(404, "Event not found")
        await db.events.update_one({"id": event_id}, {"$set": await _clean_input(inp, event_id)})
        return await db.events.find_one({"id": event_id}, {"_id": 0})

    @router.delete("/admin/events/{event_id}")
    async def admin_delete_event(event_id: str, _: str = Depends(verify_admin)):
        if (await db.events.delete_one({"id": event_id})).deleted_count == 0:
            raise HTTPException(404, "Event not found")
        await db.event_comments.delete_many({"event_id": event_id})
        await db.event_waitlist.delete_many({"event_id": event_id})
        return {"success": True}

    @router.get("/admin/events/{event_id}/comments")
    async def admin_list_event_comments(event_id: str, _: str = Depends(verify_admin)):
        return await db.event_comments.find(
            {"event_id": event_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(1000)

    @router.delete("/admin/events/comments/{comment_id}")
    async def admin_delete_event_comment(comment_id: str, _: str = Depends(verify_admin)):
        await db.event_comments.delete_one({"id": comment_id})
        await db.event_comments.delete_many({"parent_id": comment_id})
        return {"success": True}

    @router.get("/admin/events/{event_id}/waitlist")
    async def admin_list_waitlist(event_id: str, _: str = Depends(verify_admin)):
        return await db.event_waitlist.find(
            {"event_id": event_id}, {"_id": 0}
        ).sort("created_at", -1).to_list(5000)

    @router.delete("/admin/events/waitlist/{entry_id}")
    async def admin_delete_waitlist(entry_id: str, _: str = Depends(verify_admin)):
        await db.event_waitlist.delete_one({"id": entry_id})
        return {"success": True}

    return router
