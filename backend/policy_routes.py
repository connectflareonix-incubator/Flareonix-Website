"""Policy pages: public read, admin edit with version history and a removable draft notice."""
import uuid
from pathlib import Path
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

CONTENT_DIR = Path(__file__).parent / "policy_content"
POLICIES = [
    ("privacy", "Privacy Policy", "How we collect, use, protect and share personal data, and your rights."),
    ("terms", "Terms of Use", "The rules for using the Flareonix website, community, AI tools and programmes."),
    ("event-terms", "Event Participation Terms", "Passes, entry, conduct, safety and programme changes at Flareonix events."),
    ("refunds", "Cancellation & Refund Policy", "When event passes can be cancelled, transferred or refunded, and how."),
    ("media-consent", "Photo, Video & Media Consent", "How we photograph and film events, and how to opt out or ask for removal."),
    ("pitch-arena", "Pitch Arena Rules & IP", "Eligibility, judging, confidentiality, and why your idea stays yours."),
    ("grievance", "Grievance Redressal", "Who to contact with a complaint or privacy request, and how we respond."),
]
LIST_FIELDS = {"_id": 0, "body_md": 0}


def _now():
    return datetime.now(timezone.utc).isoformat()


class PolicyUpdate(BaseModel):
    title: str = Field(..., min_length=3, max_length=120)
    summary: str = Field("", max_length=300)
    body_md: str = Field(..., min_length=20, max_length=100000)
    show_draft_notice: bool = True
    change_note: str = Field("", max_length=200)


class NoticeUpdate(BaseModel):
    show_draft_notice: bool


async def seed_policies(db):
    """Insert starter drafts only when a policy is missing; never overwrites admin edits."""
    await db.policies.create_index("slug", unique=True)
    await db.policy_versions.create_index("slug")
    for order, (slug, title, summary) in enumerate(POLICIES):
        if await db.policies.find_one({"slug": slug}, {"_id": 1}):
            continue
        await db.policies.insert_one({
            "id": str(uuid.uuid4()), "slug": slug, "title": title, "summary": summary,
            "body_md": (CONTENT_DIR / f"{slug}.md").read_text(encoding="utf-8"),
            "version": 1, "show_draft_notice": True, "display_order": order,
            "change_note": "Initial draft for legal review", "updated_at": _now(), "updated_by": "system",
        })


def build_policy_router(db, verify_admin):
    router = APIRouter(prefix="/api", tags=["policies"])

    async def _get(slug: str) -> dict:
        doc = await db.policies.find_one({"slug": slug}, {"_id": 0})
        if not doc:
            raise HTTPException(404, "Policy not found")
        return doc

    async def _audit(action: str, detail: str):
        await db.admin_audit.insert_one({
            "id": str(uuid.uuid4()), "action": action, "actor": "admin",
            "detail": detail[:200], "created_at": _now(),
        })

    @router.get("/policies")
    async def list_policies():
        return await db.policies.find({}, LIST_FIELDS).sort("display_order", 1).to_list(50)

    @router.get("/policies/{slug}")
    async def get_policy(slug: str):
        return await _get(slug)

    @router.get("/admin/policies")
    async def admin_list(_: str = Depends(verify_admin)):
        return await db.policies.find({}, LIST_FIELDS).sort("display_order", 1).to_list(50)

    @router.get("/admin/policies/{slug}")
    async def admin_get(slug: str, _: str = Depends(verify_admin)):
        return await _get(slug)

    @router.put("/admin/policies/{slug}")
    async def admin_update(slug: str, inp: PolicyUpdate, admin: str = Depends(verify_admin)):
        cur = await _get(slug)
        await db.policy_versions.insert_one({**cur, "archived_at": _now()})
        version = cur.get("version", 1) + 1
        await db.policies.update_one({"slug": slug}, {"$set": {
            **inp.model_dump(), "version": version, "updated_at": _now(), "updated_by": admin,
        }})
        await _audit("policy_updated", f"{slug} v{version}: {inp.change_note}")
        return await _get(slug)

    @router.patch("/admin/policies/{slug}/notice")
    async def admin_notice(slug: str, inp: NoticeUpdate, admin: str = Depends(verify_admin)):
        await _get(slug)
        await db.policies.update_one({"slug": slug}, {"$set": {
            "show_draft_notice": inp.show_draft_notice, "notice_changed_at": _now(), "notice_changed_by": admin,
        }})
        await _audit("policy_notice", f"{slug} draft notice {'shown' if inp.show_draft_notice else 'removed'}")
        return await _get(slug)

    @router.get("/admin/policies/{slug}/versions")
    async def admin_versions(slug: str, _: str = Depends(verify_admin)):
        return await db.policy_versions.find(
            {"slug": slug}, {"_id": 0, "body_md": 0}
        ).sort("version", -1).to_list(100)

    return router
