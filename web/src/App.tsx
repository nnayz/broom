import { useEffect, useMemo, useState } from "react"
import {
  Broom,
  ExternalLink,
  Inbox,
  Loader2,
  Mail,
  RefreshCw,
  Search,
  Unplug,
} from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Progress } from "@/components/ui/progress"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { getAuth, getEmail, getStorage, scanEmails, startAuth, unsubscribeEmail } from "@/lib/api"
import { formatBytes, formatDate, pct, senderLabel } from "@/lib/format"
import type {
  AuthStatus,
  Bucket,
  EmailDetail,
  EmailSummary,
  StorageInfo,
} from "@/lib/types"

const PRESETS: { label: string; query: string }[] = [
  { label: "Inbox 30d", query: "in:inbox newer_than:30d" },
  { label: "Promotions", query: "category:promotions newer_than:90d" },
  { label: "Large", query: "larger:1M" },
  { label: "Unread", query: "in:inbox is:unread" },
  { label: "Newsletters", query: "unsubscribe newer_than:90d" },
]

export default function App() {
  const [auth, setAuth] = useState<AuthStatus | null>(null)
  const [storage, setStorage] = useState<StorageInfo | null>(null)
  const [emails, setEmails] = useState<EmailSummary[]>([])
  const [query, setQuery] = useState(PRESETS[0].query)
  const [maxResults, setMaxResults] = useState(40)
  const [scanning, setScanning] = useState(false)
  const [bucket, setBucket] = useState<"all" | Bucket>("all")
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [detail, setDetail] = useState<EmailDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [confirm, setConfirm] = useState<EmailSummary | null>(null)
  const [busy, setBusy] = useState(false)

  async function refreshAuth() {
    const status = await getAuth()
    setAuth(status)
    if (status.connected) {
      try {
        setStorage(await getStorage())
      } catch (err) {
        toast.error(err instanceof Error ? err.message : "Storage lookup failed")
      }
    }
  }

  useEffect(() => {
    refreshAuth().catch((err) => toast.error(String(err)))
  }, [])

  useEffect(() => {
    if (!selectedId) {
      setDetail(null)
      return
    }
    let cancelled = false
    setDetailLoading(true)
    getEmail(selectedId)
      .then((row) => {
        if (!cancelled) setDetail(row)
      })
      .catch((err) => toast.error(err instanceof Error ? err.message : "Could not load mail"))
      .finally(() => {
        if (!cancelled) setDetailLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selectedId])

  function runScan(nextQuery = query) {
    setScanning(true)
    setEmails([])
    setSelectedId(null)
    const stop = scanEmails(
      nextQuery,
      maxResults,
      (email) => setEmails((cur) => [...cur, email]),
      () => undefined,
      (total) => {
        setScanning(false)
        toast.success(`Classified ${total} messages`)
      },
      (message) => {
        setScanning(false)
        toast.error(message)
      },
    )
    return stop
  }

  const filtered = useMemo(() => {
    if (bucket === "all") return emails
    return emails.filter((e) => e.classification?.bucket === bucket)
  }, [emails, bucket])

  const counts = useMemo(() => {
    const out = { all: emails.length, promotional: 0, important: 0, other: 0 }
    for (const e of emails) {
      const b = e.classification?.bucket
      if (b) out[b] += 1
    }
    return out
  }, [emails])

  const selected = emails.find((e) => e.id === selectedId) ?? null

  if (!auth) {
    return (
      <div className="flex min-h-svh items-center justify-center">
        <Loader2 className="size-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!auth.connected) {
    return <ConnectScreen auth={auth} onRefresh={refreshAuth} />
  }

  const used = storage?.usage_bytes
  const limit = storage?.limit_bytes
  const usedPct = used != null && limit ? Math.min(100, (used / limit) * 100) : null

  return (
    <div className="flex min-h-svh flex-col bg-background">
      <header className="border-b border-border/80">
        <div className="mx-auto flex w-full max-w-7xl items-center gap-4 px-6 py-4">
          <div className="flex items-center gap-2.5">
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground">
              <Broom className="size-5" />
            </div>
            <div>
              <div className="text-sm font-semibold tracking-tight">Broom</div>
              <div className="text-xs text-muted-foreground">Local Gmail triage</div>
            </div>
          </div>
          <div className="ml-auto flex min-w-0 items-center gap-4">
            <div className="hidden min-w-56 flex-col gap-1 sm:flex">
              <div className="flex justify-between text-[11px] text-muted-foreground">
                <span>{storage?.email_address || "Gmail"}</span>
                <span>
                  {formatBytes(used)} / {formatBytes(limit)}
                </span>
              </div>
              <Progress value={usedPct ?? 0} className="w-56" />
            </div>
            <Badge variant="outline" className="hidden md:inline-flex">
              {auth.model_ready ? "laya-mlx ready" : auth.model_loading ? "loading model…" : "model idle"}
            </Badge>
          </div>
        </div>
      </header>

      <main className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-5 px-6 py-5">
        <div className="grid gap-4 md:grid-cols-4">
          <StatCard label="Scanned" value={String(counts.all)} hint="this pass" />
          <StatCard label="Promotional" value={String(counts.promotional)} hint="cleanup candidates" />
          <StatCard label="Important" value={String(counts.important)} hint="keep" />
          <StatCard
            label="Mailbox"
            value={storage?.messages_total != null ? storage.messages_total.toLocaleString() : "—"}
            hint="total messages"
          />
        </div>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Scan</CardTitle>
            <CardDescription>
              Mirage reads Gmail. laya-mlx classifies. Unsubscribe is optional. Deletion stays in Gmail.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-3">
            <div className="flex flex-wrap gap-2">
              {PRESETS.map((p) => (
                <Button
                  key={p.query}
                  size="sm"
                  variant={query === p.query ? "default" : "outline"}
                  onClick={() => {
                    setQuery(p.query)
                    runScan(p.query)
                  }}
                >
                  {p.label}
                </Button>
              ))}
            </div>
            <div className="flex flex-col gap-2 sm:flex-row">
              <div className="relative flex-1">
                <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  className="pl-8"
                  placeholder="Gmail search query"
                />
              </div>
              <Input
                className="sm:w-24"
                type="number"
                min={1}
                max={2000}
                value={maxResults}
                onChange={(e) => setMaxResults(Number(e.target.value) || 40)}
              />
              <Button onClick={() => runScan()} disabled={scanning}>
                {scanning ? <Loader2 className="animate-spin" /> : <RefreshCw />}
                {scanning ? "Scanning…" : "Scan"}
              </Button>
            </div>
          </CardContent>
        </Card>

        <div className="flex items-center justify-between gap-3">
          <Tabs value={bucket} onValueChange={(v) => setBucket(v as typeof bucket)}>
            <TabsList>
              <TabsTrigger value="all">All {counts.all}</TabsTrigger>
              <TabsTrigger value="promotional">Promotional {counts.promotional}</TabsTrigger>
              <TabsTrigger value="important">Important {counts.important}</TabsTrigger>
              <TabsTrigger value="other">Other {counts.other}</TabsTrigger>
            </TabsList>
          </Tabs>
          <p className="hidden text-xs text-muted-foreground md:block">
            Broom never deletes mail. Use Open in Gmail to trash it yourself.
          </p>
        </div>

        <Card className="flex-1 overflow-hidden">
          {scanning && emails.length === 0 ? (
            <div className="space-y-3 p-6">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center gap-2 py-24 text-center">
              <Inbox className="size-8 text-muted-foreground" />
              <p className="text-sm font-medium">No messages in this view</p>
              <p className="text-xs text-muted-foreground">Run a scan to classify your inbox.</p>
            </div>
          ) : (
            <div className="divide-y">
              {filtered.map((email) => (
                <button
                  key={email.id}
                  type="button"
                  onClick={() => setSelectedId(email.id)}
                  className="flex w-full items-start gap-3 px-4 py-3 text-left hover:bg-muted/50"
                >
                  <div className="mt-0.5 flex size-9 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
                    {(email.from_name || email.from_email || "?").slice(0, 1).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium">
                        {senderLabel(email.from_name, email.from_email)}
                      </span>
                      <span className="ml-auto shrink-0 text-[11px] text-muted-foreground">
                        {formatDate(email.date)}
                      </span>
                    </div>
                    <div className="truncate text-sm">{email.subject || "(no subject)"}</div>
                    <div className="truncate text-xs text-muted-foreground">{email.snippet}</div>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <KindBadge email={email} />
                    <span className="text-[11px] text-muted-foreground">{formatBytes(email.size_estimate)}</span>
                    {email.unsubscribe ? (
                      <span className="text-[11px] text-primary">Unsubscribe</span>
                    ) : null}
                  </div>
                </button>
              ))}
            </div>
          )}
        </Card>
      </main>

      <Sheet open={Boolean(selectedId)} onOpenChange={(open) => !open && setSelectedId(null)}>
        <SheetContent className="w-full sm:max-w-lg">
          <SheetHeader>
            <SheetTitle className="pr-8 text-left">{selected?.subject || "Message"}</SheetTitle>
            <SheetDescription className="text-left">
              {senderLabel(selected?.from_name || "", selected?.from_email || "")}
              {selected?.from_email ? ` · ${selected.from_email}` : ""}
            </SheetDescription>
          </SheetHeader>
          {selected ? (
            <EmailPane
              summary={selected}
              detail={detail}
              loading={detailLoading}
              onUnsubscribe={() => setConfirm(selected)}
            />
          ) : null}
        </SheetContent>
      </Sheet>

      <Dialog open={Boolean(confirm)} onOpenChange={(open) => !open && setConfirm(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Unsubscribe?</DialogTitle>
            <DialogDescription>
              This sends the publisher’s List-Unsubscribe request. Broom will not delete the message.
            </DialogDescription>
          </DialogHeader>
          <p className="text-sm">{confirm?.subject}</p>
          <p className="text-xs text-muted-foreground">{confirm?.from_email}</p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirm(null)}>
              Cancel
            </Button>
            <Button
              disabled={busy || !confirm}
              onClick={async () => {
                if (!confirm?.unsubscribe) return
                setBusy(true)
                try {
                  const method = confirm.unsubscribe.one_click
                    ? "one_click"
                    : confirm.unsubscribe.http_url
                      ? "http"
                      : "mailto"
                  const result = await unsubscribeEmail(confirm.id, method)
                  if (result.opened_url && method === "http") {
                    window.open(result.opened_url, "_blank", "noopener,noreferrer")
                  }
                  toast.success(result.detail)
                  setConfirm(null)
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Unsubscribe failed")
                } finally {
                  setBusy(false)
                }
              }}
            >
              {busy ? <Loader2 className="animate-spin" /> : <Unplug />}
              Confirm
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

function StatCard({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <Card>
      <CardHeader className="pb-2">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl tabular-nums">{value}</CardTitle>
      </CardHeader>
      <CardContent className="text-xs text-muted-foreground">{hint}</CardContent>
    </Card>
  )
}

function KindBadge({ email }: { email: EmailSummary }) {
  const kind = email.classification?.kind
  if (!kind) return <Badge variant="outline">…</Badge>
  if (kind === "promotional") return <Badge>promo</Badge>
  if (kind === "important") return <Badge variant="secondary">important</Badge>
  return <Badge variant="outline">{kind}</Badge>
}

function EmailPane({
  summary,
  detail,
  loading,
  onUnsubscribe,
}: {
  summary: EmailSummary
  detail: EmailDetail | null
  loading: boolean
  onUnsubscribe: () => void
}) {
  const cls = detail?.classification ?? summary.classification
  return (
    <ScrollArea className="h-[calc(100svh-8rem)] px-4 pb-6">
      <div className="flex flex-col gap-4">
        <div className="flex flex-wrap gap-2">
          <KindBadge email={detail ?? summary} />
          {cls ? <Badge variant="outline">{pct(cls.confidence)} confident</Badge> : null}
          {summary.has_attachments ? <Badge variant="outline">attachments</Badge> : null}
        </div>
        {cls ? (
          <div className="grid grid-cols-2 gap-2 text-xs">
            <Metric label="Spam" value={pct(cls.is_spam)} warn={cls.is_spam > 0.6} />
            <Metric label="Phishing" value={pct(cls.is_phishing)} warn={cls.is_phishing > 0.5} />
            <Metric label="Needs reply" value={pct(cls.needs_reply)} />
            <Metric label="Urgency" value={cls.urgency.toFixed(2)} />
          </div>
        ) : null}
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            nativeButton={false}
            render={
              <a href={summary.gmail_url} target="_blank" rel="noreferrer" />
            }
          >
            <ExternalLink />
            Open in Gmail
          </Button>
          {summary.unsubscribe ? (
            <Button size="sm" onClick={onUnsubscribe}>
              <Unplug />
              Unsubscribe
            </Button>
          ) : (
            <Button size="sm" variant="outline" disabled>
              No unsubscribe header
            </Button>
          )}
        </div>
        <p className="text-[11px] text-muted-foreground">
          Deletion is manual. Trash the message in Gmail if you want it gone.
        </p>
        <Separator />
        {loading ? (
          <Skeleton className="h-40 w-full" />
        ) : (
          <pre className="whitespace-pre-wrap font-sans text-sm leading-6 text-foreground/90">
            {detail?.body_text || summary.snippet || "(empty body)"}
          </pre>
        )}
      </div>
    </ScrollArea>
  )
}

function Metric({ label, value, warn }: { label: string; value: string; warn?: boolean }) {
  return (
    <div className="rounded-lg border border-border/80 px-2 py-1.5">
      <div className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</div>
      <div className={`text-sm tabular-nums ${warn ? "text-destructive" : ""}`}>{value}</div>
    </div>
  )
}

function ConnectScreen({ auth, onRefresh }: { auth: AuthStatus; onRefresh: () => Promise<void> }) {
  const [pending, setPending] = useState(false)
  return (
    <div className="flex min-h-svh items-center justify-center p-6">
      <Card className="w-full max-w-lg">
        <CardHeader>
          <div className="mb-2 flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground">
            <Broom className="size-5" />
          </div>
          <CardTitle>Connect Gmail</CardTitle>
          <CardDescription>
            Broom runs locally. Mirage mounts your mailbox. laya-mlx classifies promotional vs important
            mail on Apple Silicon. Nothing is deleted here.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {!auth.has_client ? (
            <div className="rounded-lg border border-border p-3 text-sm text-muted-foreground">
              Add <code className="text-foreground">GOOGLE_CLIENT_ID</code> and{" "}
              <code className="text-foreground">GOOGLE_CLIENT_SECRET</code> to <code>.env</code>, then
              restart the API. Redirect URI:{" "}
              <code className="text-foreground">http://127.0.0.1:8000/api/auth/callback</code>
            </div>
          ) : (
            <Button
              disabled={pending}
              onClick={async () => {
                setPending(true)
                try {
                  const url = await startAuth()
                  window.location.href = url
                } catch (err) {
                  toast.error(err instanceof Error ? err.message : "Could not start OAuth")
                  setPending(false)
                }
              }}
            >
              {pending ? <Loader2 className="animate-spin" /> : <Mail />}
              Continue with Google
            </Button>
          )}
          {auth.error ? <p className="text-sm text-destructive">{auth.error}</p> : null}
          <Button variant="ghost" onClick={() => onRefresh()}>
            Refresh status
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
