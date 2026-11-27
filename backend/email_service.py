""""Transactional email via Resend. Bodies come from server-side templates only."""
import os
import re
import ipaddress
import logging
import httpx
from html.parser import HTMLParser
from urllib.parse import urlparse
from fastapi import HTTPException

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
RESEND_API_KEY = os.environ.get("RESEND_API_KEY")
EMAIL_FROM_NAME = os.environ.get("EMAIL_FROM_NAME", "Flareonix").strip()
EMAIL_FROM_EMAIL = os.environ.get("EMAIL_FROM_EMAIL", "security@flareonix.in").strip()
EMAIL_REPLY_TO = os.environ.get("EMAIL_REPLY_TO")

_SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "cutt.ly", "goo.gl", "rebrand.ly")
_CRED_ASK = ("reply with your password", "reply with the code", "send your password", "cvv",
             "send us your password", "enter your password below", "confirm your card number",
             "your full card number", "seed phrase", "recovery phrase", "verify your card",
             "social security number", "confirm your bank details")
_HOSTISH = re.compile(r"\\b(?:https?://)?((?:[a-z0-9-]+\\.)+[a-z]{2,})", re.I)


def _host_ok(host: str) -> bool:
    if not host or "xn--" in host:
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        pass
    return not any(host == s or host.endswith("." + s) for s in _SHORTENERS)


def _same_site(shown: str, real: str) -> bool:
    return shown == real or real.endswith("." + shown) or shown.endswith("." + real)


class _EmailScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.urls, self.anchors = set(), [], []
        self._href, self._text = None, []

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag.lower())
        self.urls += [v for k, v in attrs if k.lower() in ("href", "src") and v]
        if tag.lower() == "a":
            self._href = dict((k.lower(), v) for k, v in attrs).get("href")
            self._text = []

    def handle_data(self, data):
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "a" and self._href is not None:
            self.anchors.append((self._href, "".join(self._text)))
            self._href, self._text = None, []


def _assert_safe_email(subject: str, html: str) -> None:
    scan = _EmailScan()
    scan.feed(html)
    if scan.tags & {"form", "input", "textarea", "select"}:
        raise ValueError("No forms or input fields in email (G2)")
    body = f"{subject}\\n{html}".lower()
    for p in _CRED_ASK:
        if p in body:
            raise ValueError(f"Email asks the recipient for credentials: {p!r} (G2)")
    for url in scan.urls:
        low = url.strip().lower()
        if low.startswith(("mailto:", "tel:", "cid:", "#")):
            continue
        if not low.startswith("https://"):
            raise ValueError(f"Email links/assets must be absolute https: {url!r} (G3)")
        host = urlparse(low).hostname or ""
        if not _host_ok(host) or urlparse(low).username is not None:
            raise ValueError(f"Shortened, numeric-host or credential-bearing URL: {url!r} (G3)")
    for href, text in scan.anchors:
        real = urlparse(href.strip().lower()).hostname or ""
        if not real:
            continue
        for m in _HOSTISH.finditer(text):
            if not _same_site(m.group(1).lower(), real):
                raise ValueError(f"Anchor text {m.group(1)!r} does not match link host {real!r} (G3)")


async def send_email(*, to: str, subject: str, html: str, reply_to: str | None = None) -> str | None:
    if not RESEND_API_KEY:
        logger.warning("Email is disabled: RESEND_API_KEY is not configured")
        raise HTTPException(status_code=503, detail="Email is not configured for this environment")
    if not EMAIL_FROM_NAME or not EMAIL_FROM_EMAIL:
        logger.error("Email is disabled: sender name or address is not configured")
        raise HTTPException(status_code=503, detail="Email sender is not configured for this environment")
    _assert_safe_email(subject, html)
    payload = {
        "from": f"{EMAIL_FROM_NAME} <{EMAIL_FROM_EMAIL}>",
        "to": [to],
        "subject": subject,
        "html": html,
    }
    effective_reply_to = reply_to or EMAIL_REPLY_TO
    if effective_reply_to:
        payload["reply_to"] = effective_reply_to
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                RESEND_API_URL,
                headers={"Authorization": f"Bearer {RESEND_API_KEY}", "Content-Type": "application/json"},
                json=payload,
            )
        resp.raise_for_status()
        message_id = resp.json().get("id")
        if not message_id:
            logger.error("Resend accepted no message identifier in its response")
            raise HTTPException(status_code=502, detail="Email provider returned an invalid response")
        return message_id
    except httpx.HTTPStatusError as e:
        logger.error("Resend email send failed: %s %s", e.response.status_code, e.response.text[:300])
        if e.response.status_code == 429 or e.response.status_code >= 500:
            raise HTTPException(status_code=503, detail="Email is temporarily unavailable")
        if e.response.status_code in (401, 403):
            raise HTTPException(status_code=503, detail="Email service authentication or sender configuration failed")
        raise HTTPException(status_code=502, detail="Failed to send email")
    except HTTPException:
        raise
    except (httpx.TimeoutException, httpx.NetworkError) as e:
        logger.warning("Resend email request could not be completed: %s", type(e).__name__)
        raise HTTPException(status_code=503, detail="Email service is temporarily unavailable")
    except Exception as e:
        logger.error("Email send error: %s", type(e).__name__)
        raise HTTPException(status_code=500, detail="Failed to send email")
"