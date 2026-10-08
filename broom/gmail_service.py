from __future__ import annotations

from typing import Any

import httpx
from pydantic import SecretStr

from broom.classify import classify_email, model_status
from broom.models import (
    Address,
    Attachment,
    AuthStatus,
    EmailDetail,
    EmailSummary,
    StorageInfo,
)
from broom.oauth import has_client, has_refresh_token, load_credentials
from broom.unsubscribe import header_map, parse_unsubscribe, sender_email

_workspace = None
_vfs = None
_config = None


def _gmail_url(thread_id: str) -> str:
    if not thread_id:
        return "https://mail.google.com/mail/u/0/#inbox"
    return f"https://mail.google.com/mail/u/0/#inbox/{thread_id}"


def _secret(value: str | None) -> SecretStr | None:
    return SecretStr(value) if value else None


def google_config():
    global _config
    from mirage.resource.gmail import GmailConfig

    creds = load_credentials()
    if not creds.get("client_id") or not creds.get("refresh_token"):
        raise RuntimeError("Gmail is not connected. Add Google credentials first.")
    _config = GmailConfig(
        client_id=creds["client_id"],
        client_secret=_secret(creds.get("client_secret")),
        refresh_token=SecretStr(creds["refresh_token"]),
    )
    return _config


async def get_workspace():
    global _workspace, _vfs
    if _workspace is not None:
        return _workspace
    from mirage import MountMode, Workspace
    from mirage.commands.cli.builtin.gws import GWS
    from mirage.resource.gmail import GmailResource

    config = google_config()
    _vfs = GmailResource(config=config)
    _workspace = Workspace({"/gmail": _vfs}, mode=MountMode.READ)
    _workspace.register_cli("gws", GWS, config.model_dump(mode="json"))
    return _workspace


async def close_workspace() -> None:
    global _workspace, _vfs, _config
    if _vfs is not None:
        await _vfs.close()
    if _workspace is not None:
        await _workspace.close()
    _workspace = None
    _vfs = None
    _config = None


async def _shell(command: str) -> str:
    ws = await get_workspace()
    result = await ws.execute(command)
    stdout = await result.stdout_str()
    if result.exit_code not in (0, None):
        stderr = (await result.stderr_str()).strip()
        raise RuntimeError(stderr or f"mirage command failed: {command}")
    return stdout


async def list_labels() -> list[str]:
    out = await _shell("ls /gmail/")
    return [line.strip() for line in out.splitlines() if line.strip()]


def _to_summary(
    processed: dict[str, Any],
    *,
    raw: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> EmailSummary:
    frm = processed.get("from") or {}
    if isinstance(frm, str):
        email = sender_email(frm)
        name = frm.split("<")[0].strip().strip('"')
    else:
        email = frm.get("email") or ""
        name = frm.get("name") or ""
    labels = list(processed.get("labels") or [])
    thread_id = processed.get("thread_id") or processed.get("threadId") or ""
    size = 0
    if raw:
        size = int(raw.get("sizeEstimate") or 0)
    hdrs = headers or {}
    unsub = parse_unsubscribe(hdrs) if hdrs else None
    attachments = processed.get("attachments") or []
    return EmailSummary(
        id=processed.get("id") or "",
        thread_id=thread_id,
        subject=processed.get("subject") or "",
        from_name=name,
        from_email=email,
        date=processed.get("date") or "",
        snippet=processed.get("snippet") or "",
        labels=labels,
        size_estimate=size,
        has_attachments=bool(attachments),
        gmail_url=_gmail_url(thread_id),
        unsubscribe=unsub,
    )


def _to_detail(processed: dict[str, Any], raw: dict[str, Any]) -> EmailDetail:
    headers = header_map(raw.get("payload", {}).get("headers") or [])
    summary = _to_summary(processed, raw=raw, headers=headers)
    to_addrs = [
        Address(name=a.get("name", ""), email=a.get("email", ""))
        for a in (processed.get("to") or [])
        if isinstance(a, dict)
    ]
    cc_addrs = [
        Address(name=a.get("name", ""), email=a.get("email", ""))
        for a in (processed.get("cc") or [])
        if isinstance(a, dict)
    ]
    attachments = [
        Attachment(
            id=a.get("id") or "",
            filename=a.get("filename") or "",
            mime_type=a.get("mime_type") or "",
            size=int(a.get("size") or 0),
        )
        for a in (processed.get("attachments") or [])
        if isinstance(a, dict)
    ]
    interesting = {
        k: headers[k]
        for k in (
            "list-unsubscribe",
            "list-unsubscribe-post",
            "list-id",
            "from",
            "to",
            "subject",
            "date",
        )
        if k in headers
    }
    return EmailDetail(
        **summary.model_dump(),
        to=to_addrs,
        cc=cc_addrs,
        body_text=processed.get("body_text") or "",
        attachments=attachments,
        headers=interesting,
    )


async def fetch_raw_and_processed(message_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    from mirage.core.gmail.messages import get_message_raw, process_message
    from mirage.core.google.client import TokenManager

    async with TokenManager(google_config()) as tm:
        raw = await get_message_raw(tm, message_id)
    return raw, process_message(raw)


async def list_message_stubs(tm, query: str, max_results: int) -> list[dict]:
    """Page Gmail messages.list. Gmail caps each page at 500."""
    from mirage.core.google.client import gmail_base, google_get

    url = f"{gmail_base(tm)}/users/me/messages"
    stubs: list[dict] = []
    page_token = None
    while len(stubs) < max_results:
        page_size = min(500, max_results - len(stubs))
        params: dict = {"maxResults": page_size}
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token
        data = await google_get(tm, url, params=params)
        batch = data.get("messages") or []
        stubs.extend(batch)
        page_token = data.get("nextPageToken")
        if not page_token or not batch:
            break
    return stubs[:max_results]


async def iter_emails(query: str, max_results: int):
    """Yield (summary, body) using Mirage Gmail helpers (same path as `gws gmail triage`)."""
    from mirage.core.gmail.messages import get_message_raw, process_message
    from mirage.core.google.client import TokenManager

    async with TokenManager(google_config()) as tm:
        stubs = await list_message_stubs(tm, query, max_results)
        for stub in stubs:
            raw = await get_message_raw(tm, stub["id"])
            processed = process_message(raw)
            headers = header_map(raw.get("payload", {}).get("headers") or [])
            summary = _to_summary(processed, raw=raw, headers=headers)
            body = processed.get("body_text") or summary.snippet
            yield summary, body


async def list_emails(query: str, max_results: int) -> list[EmailSummary]:
    return [summary async for summary, _body in iter_emails(query, max_results)]


def classify_summary(email: EmailSummary, body: str) -> EmailSummary:
    classification = classify_email(
        message_id=email.id,
        subject=email.subject,
        body=body or email.snippet,
        sender=email.from_email,
        labels=email.labels,
    )
    email.classification = classification
    return email


async def get_email(message_id: str, classify: bool = True) -> EmailDetail:
    raw, processed = await fetch_raw_and_processed(message_id)
    detail = _to_detail(processed, raw)
    if classify:
        detail.classification = classify_email(
            message_id=detail.id,
            subject=detail.subject,
            body=detail.body_text or detail.snippet,
            sender=detail.from_email,
            labels=detail.labels,
        )
    return detail


async def storage() -> StorageInfo:
    from mirage.core.google.client import TokenManager, gmail_base, google_get

    info = StorageInfo()
    async with TokenManager(google_config()) as tm:
        profile = await google_get(tm, f"{gmail_base(tm)}/users/me/profile")
        info.email_address = profile.get("emailAddress") or ""
        info.messages_total = profile.get("messagesTotal")
        info.threads_total = profile.get("threadsTotal")
        info.source = "gmail_profile"
        try:
            about = await google_get(
                tm,
                "https://www.googleapis.com/drive/v3/about",
                params={"fields": "storageQuota,user"},
            )
            quota = about.get("storageQuota") or {}
            info.usage_bytes = int(quota["usage"]) if quota.get("usage") else None
            info.limit_bytes = int(quota["limit"]) if quota.get("limit") else None
            info.usage_in_drive_bytes = (
                int(quota["usageInDrive"]) if quota.get("usageInDrive") else None
            )
            info.usage_in_gmail_bytes = (
                int(quota["usageInDriveTrash"]) if False else None
            )
            # Gmail-specific usage is not always present; keep Drive totals.
            if quota.get("usageInGmail"):
                info.usage_in_gmail_bytes = int(quota["usageInGmail"])
            info.source = "drive_about"
        except Exception:
            pass
    return info


async def auth_status() -> AuthStatus:
    ready, loading, error = model_status()
    status = AuthStatus(
        connected=has_refresh_token(),
        has_client=has_client(),
        model_ready=ready,
        model_loading=loading,
        error=error,
    )
    if status.connected:
        try:
            info = await storage()
            status.email_address = info.email_address
        except Exception as exc:  # noqa: BLE001
            status.error = str(exc)
    return status


async def send_mail(to: str, subject: str, body: str) -> dict[str, Any]:
    from mirage.core.gmail.send import send_message
    from mirage.core.google.client import TokenManager

    async with TokenManager(google_config()) as tm:
        return await send_message(tm, to, subject, body)


async def one_click_unsubscribe(url: str) -> tuple[int, str]:
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        resp = await client.post(
            url,
            content="List-Unsubscribe=One-Click",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        return resp.status_code, resp.reason_phrase
