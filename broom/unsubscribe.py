from __future__ import annotations

from email.utils import parseaddr
from urllib.parse import parse_qs, unquote, urlparse

from broom.models import UnsubscribeInfo


def _split_angle_list(value: str) -> list[str]:
    items: list[str] = []
    buf = ""
    in_angle = False
    for ch in value:
        if ch == "<":
            in_angle = True
            buf = ""
            continue
        if ch == ">" and in_angle:
            items.append(buf.strip())
            in_angle = False
            buf = ""
            continue
        if in_angle:
            buf += ch
    if not items:
        # Some senders omit angle brackets.
        items = [part.strip() for part in value.split(",") if part.strip()]
    return items


def parse_unsubscribe(headers: dict[str, str]) -> UnsubscribeInfo | None:
    raw = headers.get("list-unsubscribe") or headers.get("List-Unsubscribe") or ""
    if not raw:
        return None
    post = (
        headers.get("list-unsubscribe-post")
        or headers.get("List-Unsubscribe-Post")
        or ""
    )
    list_id = headers.get("list-id") or headers.get("List-Id") or None
    http_url = None
    mailto = None
    subject = "unsubscribe"
    body = "unsubscribe"
    for item in _split_angle_list(raw):
        lowered = item.lower()
        if lowered.startswith("mailto:"):
            parsed = urlparse(item)
            mailto = unquote(parsed.path)
            qs = parse_qs(parsed.query)
            if "subject" in qs:
                subject = qs["subject"][0]
            if "body" in qs:
                body = qs["body"][0]
        elif lowered.startswith("https:") or lowered.startswith("http:"):
            if http_url is None or lowered.startswith("https:"):
                http_url = item
    if not http_url and not mailto:
        return None
    one_click = "one-click" in post.lower() and http_url is not None
    return UnsubscribeInfo(
        http_url=http_url,
        mailto=mailto,
        mailto_subject=subject,
        mailto_body=body,
        one_click=one_click,
        list_id=list_id,
    )


def header_map(headers: list[dict]) -> dict[str, str]:
    out: dict[str, str] = {}
    for h in headers:
        name = str(h.get("name") or "")
        if not name:
            continue
        out[name.lower()] = str(h.get("value") or "")
        out[name] = str(h.get("value") or "")
    return out


def sender_email(from_header: str) -> str:
    _, addr = parseaddr(from_header)
    return addr
