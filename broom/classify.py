from __future__ import annotations

import json
import threading
from typing import Any

from broom.config import CLASSIFICATION_CACHE_PATH, settings
from broom.models import Bucket, Classification, Kind

CATEGORIES = {
    "promotional": (
        "marketing, newsletters, sales, ads, deals, coupons, bulk mail, "
        "campaigns with unsubscribe links, brand blasts"
    ),
    "important": (
        "personal correspondence, work mail, invoices you must keep, receipts, "
        "security alerts, 2FA codes, travel, legal, bills, one-to-one messages"
    ),
    "social": "social networks, comments, follows, event invites from social apps",
    "updates": (
        "shipping notices, order status, account notifications that are not marketing"
    ),
}

GMAIL_LABEL_HINTS = {
    "CATEGORY_PROMOTIONS": "promotional",
    "CATEGORY_SOCIAL": "social",
    "CATEGORY_UPDATES": "updates",
    "CATEGORY_PERSONAL": "important",
    "IMPORTANT": "important",
}

_agent = None
_agent_lock = threading.Lock()
_loading = False
_load_error: str | None = None
_cache_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] | None = None


def model_status() -> tuple[bool, bool, str | None]:
    """ready, loading, error"""
    return _agent is not None, _loading, _load_error


def get_agent():
    global _agent, _loading, _load_error
    if _agent is not None:
        return _agent
    with _agent_lock:
        if _agent is not None:
            return _agent
        _loading = True
        _load_error = None
        try:
            import laya_mlx as laya

            _agent = laya.load(settings.laya_model, dtype="float16")
            return _agent
        except Exception as exc:  # noqa: BLE001
            _load_error = str(exc)
            raise
        finally:
            _loading = False


def _load_cache() -> dict[str, dict[str, Any]]:
    global _cache
    if _cache is not None:
        return _cache
    if CLASSIFICATION_CACHE_PATH.exists():
        _cache = json.loads(CLASSIFICATION_CACHE_PATH.read_text())
    else:
        _cache = {}
    return _cache


def _save_cache() -> None:
    if _cache is None:
        return
    CLASSIFICATION_CACHE_PATH.write_text(json.dumps(_cache))


def cached(message_id: str) -> Classification | None:
    with _cache_lock:
        row = _load_cache().get(message_id)
    if not row:
        return None
    return Classification.model_validate(row)


def store(message_id: str, classification: Classification) -> None:
    with _cache_lock:
        cache = _load_cache()
        cache[message_id] = classification.model_dump()
        _save_cache()


def _bucket(kind: Kind) -> Bucket:
    if kind == "promotional":
        return "promotional"
    if kind == "important":
        return "important"
    return "other"


def _gmail_hint(labels: list[str]) -> Kind | None:
    for label in labels:
        if label in GMAIL_LABEL_HINTS:
            return GMAIL_LABEL_HINTS[label]  # type: ignore[return-value]
    return None


def classify_email(
    *,
    message_id: str,
    subject: str,
    body: str,
    sender: str | None,
    labels: list[str] | None = None,
    use_cache: bool = True,
) -> Classification:
    if use_cache:
        hit = cached(message_id)
        if hit is not None:
            return hit

    from laya_mlx import email_questions, email_state

    agent = get_agent()
    state = email_state(subject=subject or "(no subject)", body=body or "", sender=sender)
    result = agent.predict(state, email_questions(CATEGORIES))
    answers = result["answers"]
    kind = answers["category"]["choice"]
    if kind not in CATEGORIES:
        kind = "updates"
    probs = answers["category"].get("probabilities") or {}
    confidence = float(answers["category"].get("answer_confidence") or 0.0)
    is_spam = float(answers["is_spam"]["noul"])
    is_phishing = float(answers["is_phishing"]["noul"])
    urgency = float(answers["urgency"]["score"])
    needs_reply = float(answers["needs_reply"]["noul"])

    # Strong spam signal belongs with promotional cleanup, not important.
    if is_spam >= 0.7 and kind == "important":
        kind = "promotional"
    hint = _gmail_hint(labels or [])
    classification = Classification(
        kind=kind,  # type: ignore[arg-type]
        bucket=_bucket(kind),  # type: ignore[arg-type]
        confidence=confidence,
        is_spam=is_spam,
        is_phishing=is_phishing,
        urgency=urgency,
        needs_reply=needs_reply,
        probabilities={k: float(v) for k, v in probs.items()},
        gmail_category=hint,
    )
    store(message_id, classification)
    return classification
