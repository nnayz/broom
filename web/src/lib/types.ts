export type Kind = "promotional" | "important" | "social" | "updates" | "other"
export type Bucket = "promotional" | "important" | "other"

export type Address = {
  name: string
  email: string
}

export type Attachment = {
  id: string
  filename: string
  mime_type: string
  size: number
}

export type UnsubscribeInfo = {
  http_url: string | null
  mailto: string | null
  mailto_subject: string
  mailto_body: string
  one_click: boolean
  list_id: string | null
}

export type Classification = {
  kind: Kind
  bucket: Bucket
  confidence: number
  is_spam: number
  is_phishing: number
  urgency: number
  needs_reply: number
  probabilities: Record<string, number>
  gmail_category: string | null
}

export type EmailSummary = {
  id: string
  thread_id: string
  subject: string
  from_name: string
  from_email: string
  date: string
  snippet: string
  labels: string[]
  size_estimate: number
  has_attachments: boolean
  gmail_url: string
  unsubscribe: UnsubscribeInfo | null
  classification: Classification | null
}

export type EmailDetail = EmailSummary & {
  to: Address[]
  cc: Address[]
  body_text: string
  attachments: Attachment[]
  headers: Record<string, string>
}

export type StorageInfo = {
  email_address: string
  messages_total: number | null
  threads_total: number | null
  usage_bytes: number | null
  limit_bytes: number | null
  usage_in_drive_bytes: number | null
  usage_in_gmail_bytes: number | null
  source: string
}

export type AuthStatus = {
  connected: boolean
  has_client: boolean
  email_address: string | null
  model_ready: boolean
  model_loading: boolean
  error: string | null
}
