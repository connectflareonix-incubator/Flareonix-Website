"""Flareonix AI Tools - multi-model (Claude Sonnet 5.5 / Opus 5.5, GPT 6 Luna) generators"""
import os
import json
import uuid
from datetime import datetime, timezone, timedelta
from pymongo import ReturnDocument
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone


# Model IDs below are taken from the published Emergent SDK examples.
# Keep the catalogue deliberately small and avoid advertising unverified/fictitious IDs.
MODELS = {
    "gpt-4o-mini": {"provider": "openai", "label": "GPT-4o mini", "hint": "Lower-cost option for quick drafts"},
}
DEFAULT_MODEL = "gpt-4o-mini"

# Conservative launch guardrails. These cap request volume, not a guaranteed
# currency spend; actual billing remains token/model dependent.
USER_HOURLY_LIMIT = 3
USER_DAILY_LIMIT = 10
GLOBAL_DAILY_LIMIT = 50
MAX_OUTPUT_TOKENS = 1024

async def _reserve_quota(db, user_id: str):
    now = datetime.now(timezone.utc)
    hour_key = now.strftime("%Y%m%d%H")
    day_key = now.strftime("%Y%m%d")
    windows = [
        ("user_hour", f"{user_id}:{hour_key}", USER_HOURLY_LIMIT),
        ("user_day", f"{user_id}:{day_key}", USER_DAILY_LIMIT),
        ("global_day", day_key, GLOBAL_DAILY_LIMIT),
    ]
    for scope, key, limit in windows:
        doc = await db.ai_usage_limits.find_one_and_update(
            {"scope": scope, "key": key},
            {"$inc": {"count": 1},
             "$setOnInsert": {"created_at": now, "expires_at": now + timedelta(days=3)}},
            upsert=True,
            return_document=ReturnDocument.AFTER,
        )
        if doc["count"] > limit:
            raise HTTPException(
                status_code=429,
                detail="AI usage limit reached. Please try again later.",
                headers={"Retry-After": "3600" if scope == "user_hour" else "86400"},
            )


def _key() -> str:
    k = os.environ.get("EMERGENT_LLM_KEY")
    if not k:
        raise HTTPException(status_code=500, detail="LLM key not configured")
    return k


# ==================== TOOL CONFIGS ====================

TOOL_CONFIGS = {
    "caption": {
        "name": "Caption Generator",
        "system": (
            "You are Flareonix's social-media caption expert. Write 5 viral, scroll-stopping "
            "captions for the user's brief. Each caption: punchy, on-brand, includes 3-5 "
            "relevant hashtags, ends with a CTA or hook. Number them 1-5. Use emojis sparingly "
            "(max 2 per caption). No fluff, no explanations."
        ),
    },
    "ad-copy": {
        "name": "Ad Copy Writer",
        "system": (
            "You are Flareonix's performance marketing copywriter. Generate 3 high-converting "
            "ad-copy variants (Meta + Google compatible) for the user's product/service. "
            "For each variant include: HEADLINE (max 30 chars), PRIMARY TEXT (max 125 chars), "
            "DESCRIPTION (max 90 chars), and a CTA. Format clearly with labels. "
            "Speak to the target audience, lead with a hook, and emphasise outcome."
        ),
    },
    "business-idea": {
        "name": "Business Idea Generator",
        "system": (
            "You are Flareonix's startup ideator for ambitious Indian youth. Given the user's "
            "skills/interests/budget, propose 3 validated, lean business ideas. For each idea "
            "include: TITLE, ONE-LINER, TARGET CUSTOMER, MVP IN 30 DAYS, REVENUE MODEL, "
            "INDIA-SPECIFIC EDGE. Be concrete, ground-level, no generic SaaS clichés."
        ),
    },
    "content-calendar": {
        "name": "Content Calendar",
        "system": (
            "You are Flareonix's content strategist. Build a 7-day content calendar for the "
            "user's niche. Output a markdown table with columns: Day | Platform | Content Type "
            "| Hook/Idea | CTA. Mix Reels, carousels, stories, and tweets. Each idea must be "
            "punchy, actionable, and aligned to growth."
        ),
    },
    "email-writer": {
        "name": "Email Writer",
        "system": (
            "You are Flareonix's cold-email expert. Write a short, personalised cold email "
            "based on the user's goal and recipient. Include: subject line (under 8 words), "
            "opener (1 line, hyper-specific), value (2-3 lines, outcome-led), CTA (1 line, "
            "low-friction ask). Keep total body under 90 words. No corporate jargon."
        ),
    },
    "pitch-deck": {
        "name": "Pitch Deck Assistant",
        "system": (
            "You are Flareonix's pitch-deck coach for early-stage founders. Given the user's "
            "startup brief, output a 10-slide investor-ready outline. For each slide give: "
            "SLIDE TITLE, KEY MESSAGE (1 line), and 3 BULLETS. Slides: 1) Vision, 2) Problem, "
            "3) Solution, 4) Market, 5) Product, 6) Traction, 7) Business Model, 8) "
            "Competition, 9) Team, 10) Ask. Be sharp and specific."
        ),
    },
}


# ==================== MODELS ====================

class GenerateRequest(BaseModel):
    tool: str
    prompt: str = Field(..., min_length=5, max_length=2000)
    model: str = DEFAULT_MODEL
    session_id: Optional[str] = None


class GenerationDoc(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    user_email: str
    tool: str
    tool_name: str
    prompt: str
    response: str
    model: str = DEFAULT_MODEL
    session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ==================== ROUTER ====================

def build_router(db, get_current_user):
    router = APIRouter(prefix="/api/ai", tags=["ai-tools"])

    @router.get("/tools")
    async def list_tools():
        """Public list of available tools"""
        return [{"slug": k, "name": v["name"]} for k, v in TOOL_CONFIGS.items()]

    @router.get("/models")
    async def list_models():
        return [{"id": k, "label": v["label"], "hint": v["hint"], "default": k == DEFAULT_MODEL}
                for k, v in MODELS.items()]

    @router.post("/generate")
    async def generate(req: GenerateRequest, user: dict = Depends(get_current_user)):
        """Stream generated content (SSE) from the user's chosen model."""
        cfg = TOOL_CONFIGS.get(req.tool)
        if not cfg:
            raise HTTPException(status_code=400, detail="Unknown tool")
        model = MODELS.get(req.model)
        if not model:
            raise HTTPException(status_code=400, detail="Unknown model")
        # Reserve quotas before contacting the paid model provider.
        await _reserve_quota(db, user["user_id"])
        session_id = f"ai_{user['user_id']}_{req.tool}_{uuid.uuid4().hex[:8]}"
        chat = LlmChat(
            api_key=_key(), session_id=session_id, system_message=cfg["system"],
        ).with_model(model["provider"], req.model).with_params(max_tokens=MAX_OUTPUT_TOKENS)

        def sse(payload: dict) -> str:
            return f"data: {json.dumps(payload)}\n\n"

        async def events():
            parts = []
            try:
                async for ev in chat.stream_message(UserMessage(text=req.prompt)):
                    if isinstance(ev, TextDelta):
                        parts.append(ev.content)
                        yield sse({"type": "delta", "content": ev.content})
                    elif isinstance(ev, StreamDone):
                        break
            except Exception as e:
                yield sse({"type": "error", "detail": f"AI generation failed: {str(e)[:200]}"})
                return
            doc = GenerationDoc(
                user_id=user["user_id"], user_email=user["email"], tool=req.tool,
                tool_name=cfg["name"], prompt=req.prompt, response="".join(parts),
                model=req.model, session_id=session_id,
            ).model_dump()
            doc["created_at"] = doc["created_at"].isoformat()
            await db.ai_generations.insert_one(doc)
            yield sse({"type": "done", "id": doc["id"], "model": req.model, "model_label": model["label"]})

        return StreamingResponse(events(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    @router.get("/history")
    async def history(user: dict = Depends(get_current_user)):
        """Get current user's last 50 generations"""
        items = await db.ai_generations.find(
            {"user_id": user["user_id"]}, {"_id": 0}
        ).sort("created_at", -1).to_list(50)
        return items

    @router.delete("/history/{gen_id}")
    async def delete_generation(gen_id: str, user: dict = Depends(get_current_user)):
        """Delete a generation owned by the user"""
        res = await db.ai_generations.delete_one(
            {"id": gen_id, "user_id": user["user_id"]}
        )
        if res.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Not found")
        return {"success": True}

    return router
