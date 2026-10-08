from __future__ import annotations

import json
import secrets
from typing import Any
from urllib.parse import urlencode

import httpx

from broom.config import CREDENTIALS_PATH, DATA_DIR, settings

GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/drive.metadata.readonly",
    "openid",
    "email",
]


def load_credentials() -> dict[str, str]:
    data: dict[str, str] = {
        "client_id": settings.google_client_id,
        "client_secret": settings.google_client_secret,
        "refresh_token": settings.google_refresh_token,
    }
    if CREDENTIALS_PATH.exists():
        stored = json.loads(CREDENTIALS_PATH.read_text())
        for key in ("client_id", "client_secret", "refresh_token"):
            if stored.get(key):
                data[key] = stored[key]
    return data


def save_credentials(**kwargs: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    current = load_credentials()
    current.update({k: v for k, v in kwargs.items() if v})
    CREDENTIALS_PATH.write_text(json.dumps(current, indent=2))


def has_client() -> bool:
    creds = load_credentials()
    return bool(creds.get("client_id") and creds.get("client_secret"))


def has_refresh_token() -> bool:
    return bool(load_credentials().get("refresh_token"))


def auth_url(state: str | None = None) -> str:
    creds = load_credentials()
    if not creds.get("client_id"):
        raise RuntimeError("GOOGLE_CLIENT_ID is missing")
    params = {
        "client_id": creds["client_id"],
        "redirect_uri": settings.redirect_uri,
        "response_type": "code",
        "scope": " ".join(GMAIL_SCOPES),
        "access_type": "offline",
        "prompt": "consent",
        "state": state or secrets.token_urlsafe(16),
    }
    return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)


async def exchange_code(code: str) -> dict[str, Any]:
    creds = load_credentials()
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": creds["client_id"],
                "client_secret": creds["client_secret"],
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.redirect_uri,
            },
        )
        resp.raise_for_status()
        payload = resp.json()
    refresh = payload.get("refresh_token")
    if not refresh:
        raise RuntimeError(
            "Google did not return a refresh_token. Re-auth with prompt=consent "
            "and make sure the OAuth client redirect URI matches "
            f"{settings.redirect_uri}."
        )
    save_credentials(
        client_id=creds["client_id"],
        client_secret=creds["client_secret"],
        refresh_token=refresh,
    )
    return payload
