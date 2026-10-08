from __future__ import annotations

import json
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from broom import gmail_service
from broom.classify import model_status
from broom.config import ROOT, settings
from broom.models import ScanRequest, UnsubscribeRequest
from broom.oauth import auth_url, exchange_code, has_client, has_refresh_token


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        yield
    finally:
        await gmail_service.close_workspace()


app = FastAPI(title="Broom", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_origin,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIST = ROOT / "web" / "dist"


def _require_gmail() -> None:
    if not has_refresh_token():
        raise HTTPException(401, "Gmail is not connected.")
    if not has_client():
        raise HTTPException(400, "Missing Google client id/secret.")


@app.get("/api/health")
async def health() -> dict:
    ready, loading, error = model_status()
    return {"ok": True, "model_ready": ready, "model_loading": loading, "error": error}


@app.get("/api/auth/status")
async def auth_status():
    return await gmail_service.auth_status()


@app.get("/api/auth/start")
async def auth_start():
    if not has_client():
        raise HTTPException(
            400,
            "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env first.",
        )
    return {"url": auth_url()}


@app.get("/api/auth/callback")
async def auth_callback(code: str | None = None, error: str | None = None):
    if error:
        return HTMLResponse(
            f"<h1>Google auth failed</h1><p>{error}</p>", status_code=400
        )
    if not code:
        raise HTTPException(400, "Missing code")
    try:
        await exchange_code(code)
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            f"<h1>Token exchange failed</h1><p>{exc}</p>", status_code=400
        )
    await gmail_service.close_workspace()
    if WEB_DIST.exists():
        return RedirectResponse("/?connected=1")
    return RedirectResponse(settings.frontend_origin.rstrip("/") + "/?connected=1")


@app.get("/api/storage")
async def storage():
    _require_gmail()
    try:
        return await gmail_service.storage()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/labels")
async def labels():
    _require_gmail()
    try:
        return {"labels": await gmail_service.list_labels()}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/emails")
async def emails(
    query: str = Query(default="in:inbox newer_than:30d"),
    max_results: int = Query(default=40, ge=1, le=2000),
    classify: bool = True,
):
    _require_gmail()
    try:
        items = []
        async for item, body in gmail_service.iter_emails(query, max_results):
            if classify:
                gmail_service.classify_summary(item, body)
            items.append(item.model_dump())
        return {"emails": items}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/emails/scan")
async def scan(
    query: str = Query(default="in:inbox newer_than:30d"),
    max_results: int = Query(default=40, ge=1, le=2000),
):
    _require_gmail()

    async def events():
        try:
            count = 0
            yield _sse("meta", {"query": query, "max_results": max_results})
            async for item, body in gmail_service.iter_emails(query, max_results):
                try:
                    gmail_service.classify_summary(item, body)
                except Exception as exc:  # noqa: BLE001
                    yield _sse("error", {"id": item.id, "error": str(exc)})
                count += 1
                yield _sse("email", item.model_dump())
            yield _sse("done", {"ok": True, "total": count})
        except Exception as exc:  # noqa: BLE001
            yield _sse("fatal", {"error": str(exc)})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/emails/{message_id}")
async def email_detail(message_id: str, classify: bool = True):
    _require_gmail()
    try:
        return await gmail_service.get_email(message_id, classify=classify)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/emails/{message_id}/unsubscribe")
async def unsubscribe(message_id: str, body: UnsubscribeRequest | None = None):
    _require_gmail()
    detail = await gmail_service.get_email(message_id, classify=False)
    info = detail.unsubscribe
    if info is None:
        raise HTTPException(400, "No List-Unsubscribe header on this message.")
    method = (body.method if body else None) or (
        "one_click" if info.one_click else "http" if info.http_url else "mailto"
    )
    try:
        if method == "one_click":
            if not info.http_url or not info.one_click:
                raise HTTPException(
                    400, "This message does not support one-click unsubscribe."
                )
            status, reason = await gmail_service.one_click_unsubscribe(info.http_url)
            return {
                "ok": 200 <= status < 400,
                "method": "one_click",
                "detail": f"POST {info.http_url} → {status} {reason}",
                "opened_url": info.http_url,
            }
        if method == "http":
            if not info.http_url:
                raise HTTPException(400, "No HTTP unsubscribe URL.")
            return {
                "ok": True,
                "method": "http",
                "detail": "Open this URL in your browser to unsubscribe.",
                "opened_url": info.http_url,
            }
        if method == "mailto":
            if not info.mailto:
                raise HTTPException(400, "No mailto unsubscribe address.")
            result = await gmail_service.send_mail(
                info.mailto, info.mailto_subject, info.mailto_body
            )
            return {
                "ok": True,
                "method": "mailto",
                "detail": f"Sent unsubscribe mail to {info.mailto}",
                "opened_url": None,
                "send": result,
            }
        raise HTTPException(400, f"Unknown method {method}")
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@app.post("/api/scan")
async def scan_post(req: ScanRequest):
    return await emails(
        query=req.query, max_results=req.max_results, classify=req.classify
    )


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def run() -> None:
    import uvicorn

    uvicorn.run(
        "broom.main:app",
        host=settings.broom_host,
        port=settings.broom_port,
        reload=True,
    )


if WEB_DIST.exists():
    app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="ui")


if __name__ == "__main__":
    run()
