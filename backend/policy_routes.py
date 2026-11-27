"""Versioned legal-policy storage. Drafts never replace live published documents."""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field


POLICY_CATALOG = {
    "privacy-policy": "Privacy Policy",
    "terms-of-use": "Terms of Use",
    "cookie-policy": "Cookie Policy",
    "disclaimer": "Disclaimer",
    "refund-cancellation": "Refund & Cancellation Policy",
    "community-guidelines": "Community Guidelines",
    "reviews-comments": "Reviews & Comments Policy",
    "grievance-redressal": "Grievance Redressal",
}


def _now():
    return datetime.now(timezone.utc).isoformat()


class PolicyUpdate(BaseModel):
    title: str = Field(..., min_length=3, max_length=160)
    content: str = Field(..., min_length=1, max_length=100000)
    expected_version: int = Field(..., ge=0)
    publish: bool = False


class NoticeUpdate(BaseModel):
    show_draft_notice: bool


def build_policy_router(db, verify_admin):
    router = APIRouter(prefix="/api", tags=["legal-policies"])

    async def latest_version(slug):
        latest = await db.legal_policy_versions.find_one(
            {"slug": slug}, {"_id": 0, "version": 1}, sort=[("version", -1)]
        )
        return int(latest.get("version", 0)) if latest else 0

    @router.get("/policies")
    async def public_policy_index():
        return await db.legal_policies.find(
            {"published": True},
            {"_id": 0, "slug": 1, "title": 1, "published_at": 1, "version": 1},
        ).to_list(50)

    @router.get("/policies/{slug}")
    async def public_policy(slug: str):
        if slug not in POLICY_CATALOG:
            raise HTTPException(404, "Policy not found")
        doc = await db.legal_policies.find_one(
            {"slug": slug, "published": True},
            {"_id": 0, "slug": 1, "title": 1, "content": 1, "version": 1, "published_at": 1},
        )
        if not doc:
            raise HTTPException(404, "Policy not published")
        return doc

    @router.get("/admin/policies")
    async def admin_policy_index(admin: str = Depends(verify_admin)):
        published = {d["slug"]: d for d in await db.legal_policies.find({}, {"_id": 0}).to_list(50)}
        drafts = {d["slug"]: d for d in await db.legal_policy_drafts.find({}, {"_id": 0}).to_list(50)}
        result = []
        for slug, title in POLICY_CATALOG.items():
            live = published.get(slug, {})
            draft = drafts.get(slug, {})
            result.append({
                "slug": slug, "title": draft.get("title", live.get("title", title)),
                "version": draft.get("version", await latest_version(slug)),
                "published": bool(live.get("published", False)),
                "published_version": live.get("version", 0),
                "show_draft_notice": live.get("show_draft_notice", True),
                "has_unpublished_draft": bool(draft),
            })
        return result

    @router.get("/admin/policies/{slug}")
    async def admin_get_policy(slug: str, admin: str = Depends(verify_admin)):
        if slug not in POLICY_CATALOG:
            raise HTTPException(404, "Policy not found")
        live = await db.legal_policies.find_one({"slug": slug}, {"_id": 0}) or {}
        draft = await db.legal_policy_drafts.find_one({"slug": slug}, {"_id": 0}) or {}
        source = draft or live
        return {
            "slug": slug,
            "title": source.get("title", POLICY_CATALOG[slug]),
            "content": source.get("content", ""),
            "version": source.get("version", await latest_version(slug)),
            "published": bool(live.get("published", False)),
            "published_version": live.get("version", 0),
            "show_draft_notice": live.get("show_draft_notice", True),
            "has_unpublished_draft": bool(draft),
        }

    @router.get("/admin/policies/{slug}/versions")
    async def admin_policy_versions(slug: str, admin: str = Depends(verify_admin)):
        if slug not in POLICY_CATALOG:
            raise HTTPException(404, "Policy not found")
        return await db.legal_policy_versions.find(
            {"slug": slug}, {"_id": 0}
        ).sort("version", -1).to_list(100)

    @router.put("/admin/policies/{slug}")
    async def admin_update_policy(slug: str, inp: PolicyUpdate, admin: str = Depends(verify_admin)):
        if slug not in POLICY_CATALOG:
            raise HTTPException(404, "Policy not found")
        current_version = await latest_version(slug)
        if inp.expected_version != current_version:
            raise HTTPException(409, "Policy changed elsewhere. Reload before saving.")
        next_version = current_version + 1
        now = _now()
        record = {
            "id": str(uuid.uuid4()), "slug": slug, "version": next_version,
            "title": inp.title.strip(), "content": inp.content,
            "published": bool(inp.publish), "saved_at": now, "saved_by": admin,
            "published_at": now if inp.publish else None,
        }
        try:
            await db.legal_policy_versions.insert_one(dict(record))
        except Exception:
            raise HTTPException(409, "Could not create a unique policy version. Reload and retry.")

        if inp.publish:
            await db.legal_policies.update_one(
                {"slug": slug},
                {"$set": {
                    "slug": slug, "title": record["title"], "content": record["content"],
                    "version": next_version, "published": True, "published_at": now,
                    "updated_at": now, "updated_by": admin,
                }, "$setOnInsert": {"show_draft_notice": True}},
                upsert=True,
            )
            await db.legal_policy_drafts.delete_one({"slug": slug})
        else:
            await db.legal_policy_drafts.update_one(
                {"slug": slug},
                {"$set": {
                    "slug": slug, "title": record["title"], "content": record["content"],
                    "version": next_version, "updated_at": now, "updated_by": admin,
                }},
                upsert=True,
            )

        await db.admin_audit.insert_one({
            "id": str(uuid.uuid4()),
            "action": "policy_published" if inp.publish else "policy_draft_saved",
            "actor": admin, "detail": f"{slug}:v{next_version}", "created_at": now,
        })
        return {k: v for k, v in record.items() if k != "id"}

    @router.patch("/admin/policies/{slug}/notice")
    async def admin_policy_notice(slug: str, inp: NoticeUpdate, admin: str = Depends(verify_admin)):
        if slug not in POLICY_CATALOG:
            raise HTTPException(404, "Policy not found")
        await db.legal_policies.update_one(
            {"slug": slug},
            {"$set": {"show_draft_notice": inp.show_draft_notice, "notice_updated_at": _now()}},
            upsert=True,
        )
        await db.admin_audit.insert_one({
            "id": str(uuid.uuid4()), "action": "policy_notice_changed",
            "actor": admin, "detail": slug, "created_at": _now(),
        })
        return {"slug": slug, "show_draft_notice": inp.show_draft_notice}

    return router
