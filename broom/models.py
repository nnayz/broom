from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


Kind = Literal["promotional", "important", "social", "updates", "other"]
Bucket = Literal["promotional", "important", "other"]


class Address(BaseModel):
    name: str = ""
    email: str = ""


class Attachment(BaseModel):
    id: str = ""
    filename: str = ""
    mime_type: str = ""
    size: int = 0


class UnsubscribeInfo(BaseModel):
    http_url: str | None = None
    mailto: str | None = None
    mailto_subject: str = "unsubscribe"
    mailto_body: str = "unsubscribe"
    one_click: bool = False
    list_id: str | None = None


class Classification(BaseModel):
    kind: Kind
    bucket: Bucket
    confidence: float = 0.0
    is_spam: float = 0.0
    is_phishing: float = 0.0
    urgency: float = 0.0
    needs_reply: float = 0.0
    probabilities: dict[str, float] = Field(default_factory=dict)
    gmail_category: str | None = None


class EmailSummary(BaseModel):
    id: str
    thread_id: str = ""
    subject: str = ""
    from_name: str = ""
    from_email: str = ""
    date: str = ""
    snippet: str = ""
    labels: list[str] = Field(default_factory=list)
    size_estimate: int = 0
    has_attachments: bool = False
    gmail_url: str = ""
    unsubscribe: UnsubscribeInfo | None = None
    classification: Classification | None = None


class EmailDetail(EmailSummary):
    to: list[Address] = Field(default_factory=list)
    cc: list[Address] = Field(default_factory=list)
    body_text: str = ""
    attachments: list[Attachment] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)


class StorageInfo(BaseModel):
    email_address: str = ""
    messages_total: int | None = None
    threads_total: int | None = None
    usage_bytes: int | None = None
    limit_bytes: int | None = None
    usage_in_drive_bytes: int | None = None
    usage_in_gmail_bytes: int | None = None
    source: str = "gmail_profile"


class AuthStatus(BaseModel):
    connected: bool
    has_client: bool
    email_address: str | None = None
    model_ready: bool = False
    model_loading: bool = False
    error: str | None = None


class ScanRequest(BaseModel):
    query: str = "in:inbox newer_than:30d"
    max_results: int = Field(default=40, ge=1, le=2000)
    classify: bool = True


class UnsubscribeRequest(BaseModel):
    id: str
    method: Literal["one_click", "http", "mailto"] = "one_click"


class UnsubscribeResult(BaseModel):
    ok: bool
    method: str
    detail: str
    opened_url: str | None = None


class LabelList(BaseModel):
    labels: list[str]


class ApiError(BaseModel):
    error: str
    detail: str | None = None
