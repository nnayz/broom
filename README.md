# Broom

Local Gmail cleaner. A Vite + React SPA talks to a FastAPI app on your Mac.

- **Mirage** mounts Gmail and reads messages (`GmailResource` + the same helpers as `gws gmail triage` / `gws gmail read`).
- **laya-mlx** classifies promotional vs important mail on Apple Silicon.
- **Unsubscribe** uses the message `List-Unsubscribe` header (one-click POST, HTTP link, or mailto via Gmail send).
- **Deletion is never automatic.** Broom does not trash or `rm` mail. Open the thread in Gmail and delete it yourself.

## Layout

```
broom/                 Python API (uv)
web/                   React SPA (bun + Vite + shadcn)
data/                  local tokens + classification cache (gitignored)
.env.example           Google client placeholders
```

## Requirements

- macOS 14+ on Apple Silicon
- Python 3.11+
- [uv](https://docs.astral.sh/uv/)
- [bun](https://bun.sh)
- A Google Cloud OAuth client

## 1. Python

```bash
uv sync
cp .env.example .env
```

## 2. Google OAuth

1. Create a project at [Google Cloud Console](https://console.cloud.google.com/).
2. Enable **Gmail API** and **Google Drive API** (Drive is only used for storage quota).
3. Configure the OAuth consent screen. Add yourself as a test user if the app is in Testing.
4. Create an OAuth client. **Web application** is easiest for this app.
5. Authorized redirect URI:

   `http://127.0.0.1:8000/api/auth/callback`

6. Put the client id and secret in `.env`:

```bash
GOOGLE_CLIENT_ID=....apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=...
```

Broom requests:

- `gmail.readonly` — list and read mail
- `gmail.send` — mailto-style unsubscribe only
- `drive.metadata.readonly` — account storage quota

It does **not** request `gmail.modify`, so it cannot trash messages.

## 3. TypeScript UI

```bash
cd web
bun install
```

## 4. Run

Terminal 1 — API:

```bash
uv run broom
```

Terminal 2 — UI:

```bash
cd web
bun run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) and connect Gmail.

The first classification downloads **laya-mlx** weights from Hugging Face (`aac6fef/laya-mlx`) and keeps them locally.

## How a scan works

1. Mirage lists Gmail messages for a search query (`in:inbox newer_than:30d`, `category:promotions`, `larger:1M`, …).
2. Each message is processed into Mirage’s `.gmail.json` shape (from, subject, body, labels, attachments).
3. laya-mlx answers `email_questions` with categories `promotional`, `important`, `social`, `updates`.
4. The UI buckets those into Promotional / Important / Other.
5. If `List-Unsubscribe` is present, you can confirm an unsubscribe. Broom still will not delete the mail.

## Production-style single port

```bash
cd web && bun run build
uv run broom
```

If `web/dist` exists, FastAPI serves the SPA at `/` as well as `/api`.

## Privacy

Everything runs on localhost. Tokens live in `data/google.json`. Classification cache lives in `data/classifications.json`. Neither is committed.
