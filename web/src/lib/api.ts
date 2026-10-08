import type { AuthStatus, EmailDetail, EmailSummary, StorageInfo } from "./types"

async function parseError(res: Response): Promise<string> {
  try {
    const data = await res.json()
    if (typeof data.detail === "string") return data.detail
    if (Array.isArray(data.detail)) return JSON.stringify(data.detail)
    if (typeof data.error === "string") return data.error
  } catch {
    /* ignore */
  }
  return `${res.status} ${res.statusText}`
}

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(await parseError(res))
  return res.json() as Promise<T>
}

export async function getAuth(): Promise<AuthStatus> {
  return json(await fetch("/api/auth/status"))
}

export async function startAuth(): Promise<string> {
  const data = await json<{ url: string }>(await fetch("/api/auth/start"))
  return data.url
}

export async function getStorage(): Promise<StorageInfo> {
  return json(await fetch("/api/storage"))
}

export async function getEmail(id: string): Promise<EmailDetail> {
  return json(await fetch(`/api/emails/${encodeURIComponent(id)}`))
}

export async function unsubscribeEmail(
  id: string,
  method: "one_click" | "http" | "mailto",
): Promise<{ ok: boolean; method: string; detail: string; opened_url: string | null }> {
  return json(
    await fetch(`/api/emails/${encodeURIComponent(id)}/unsubscribe`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, method }),
    }),
  )
}

export function scanEmails(
  query: string,
  maxResults: number,
  onEmail: (email: EmailSummary) => void,
  onMeta: (meta: { query: string; max_results: number }) => void,
  onDone: (total: number) => void,
  onError: (message: string) => void,
): () => void {
  const params = new URLSearchParams({
    query,
    max_results: String(maxResults),
  })
  const es = new EventSource(`/api/emails/scan?${params.toString()}`)
  es.addEventListener("meta", (ev) => {
    onMeta(JSON.parse((ev as MessageEvent).data))
  })
  es.addEventListener("email", (ev) => {
    onEmail(JSON.parse((ev as MessageEvent).data) as EmailSummary)
  })
  es.addEventListener("done", (ev) => {
    const data = JSON.parse((ev as MessageEvent).data) as { total?: number }
    es.close()
    onDone(data.total ?? 0)
  })
  es.addEventListener("fatal", (ev) => {
    const data = JSON.parse((ev as MessageEvent).data) as { error?: string }
    es.close()
    onError(data.error || "Scan failed")
  })
  es.onerror = () => {
    es.close()
    onError("Lost connection to the Broom API. Is the Python server running?")
  }
  return () => es.close()
}
