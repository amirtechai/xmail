import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL ?? '/api'
const ACCESS_KEY = 'xmail_access'
const REFRESH_KEY = 'xmail_refresh'

export const tokenStore = {
  getAccess: () => localStorage.getItem(ACCESS_KEY),
  getRefresh: () => localStorage.getItem(REFRESH_KEY),
  set: (access: string, refresh: string) => {
    localStorage.setItem(ACCESS_KEY, access)
    localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear: () => {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const api: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30_000,
})

api.interceptors.request.use((config) => {
  const token = tokenStore.getAccess()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

let refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true
      try {
        if (!refreshing) {
          const refresh = tokenStore.getRefresh()
          if (!refresh) throw new Error('no refresh token')
          refreshing = axios
            .post<{ access_token: string; refresh_token: string; token_type: string }>(`${BASE_URL}/auth/refresh`, { refresh_token: refresh })
            .then((r) => {
              tokenStore.set(r.data.access_token, r.data.refresh_token)
              return r.data.access_token
            })
            .finally(() => { refreshing = null })
        }
        const newToken = await refreshing
        original.headers.Authorization = `Bearer ${newToken}`
        return api(original)
      } catch {
        tokenStore.clear()
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  },
)

export default api

// ── Response types ──────────────────────────────────────────────────────────

export interface User {
  id: string
  email: string
  role: 'admin' | 'viewer'
  is_active: boolean
  created_at: string
}

export interface BotStatus {
  state: string
  is_running: boolean
  daily_email_count: number
  total_emails_sent: number
  last_activity_at: string | null
  current_campaign_id: string | null
  error_message: string | null
}

export interface BotSSEEvent {
  state: string
  is_running: boolean
  daily_email_count: number
}

export interface AgentRun {
  id: string
  run_type: string
  status: string
  started_at: string
  finished_at: string | null
  contacts_found: number
  error_message: string | null
}

export interface DailyReport {
  id: string
  report_date: string
  contacts_discovered: number
  contacts_verified: number
  emails_sent: number
  emails_delivered: number
  emails_bounced: number
  emails_opened: number
  emails_clicked: number
  unsubscribes: number
}

export interface Contact {
  id: string
  email: string
  full_name: string | null
  first_name: string | null
  last_name: string | null
  job_title: string | null
  company: string | null
  website: string | null
  linkedin_url: string | null
  twitter_handle: string | null
  source_url: string
  source_type: string
  audience_type: string
  country: string | null
  language: string | null
  confidence_score: number
  relevance_score: number
  verified_status: string
  mx_valid: boolean | null
  smtp_valid: boolean | null
  is_disposable: boolean
  is_role_based: boolean
  created_at: string
}

export interface ContactUpdate {
  full_name?: string | null
  first_name?: string | null
  last_name?: string | null
  job_title?: string | null
  company?: string | null
  website?: string | null
  linkedin_url?: string | null
  twitter_handle?: string | null
  country?: string | null
  language?: string | null
  audience_type_key?: string | null
  confidence_score?: number | null
}

export interface PagedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface SuppressionEntry {
  id: string
  email: string
  reason: string
  notes: string | null
  added_at: string
}

export interface ReportItem {
  date: string
  pdf_available: boolean
  xml_available: boolean
  pdf_size: number
}

export interface TrendPoint {
  date: string
  contacts: number
  sent: number
  opened: number
}

export interface DomainCount {
  domain: string
  count: number
}

export interface AudienceCount {
  key: string
  count: number
}

export interface DashboardStats {
  contacts_today: number
  contacts_week: number
  contacts_total: number
  verified_total: number
  suppression_total: number
  trend: TrendPoint[]
  top_domains: DomainCount[]
  audience_breakdown: AudienceCount[]
}

export interface HealthStatus {
  status: 'ok' | 'degraded'
  checks: Record<string, string>
}

export interface AudienceType {
  key: string
  label_en: string
  label_tr: string
  description: string | null
  icon_name: string | null
  is_enabled_default: boolean
  contact_count: number
}

export interface AudienceCategory {
  name: string
  types: AudienceType[]
}

export interface AudienceTypesResponse {
  categories: AudienceCategory[]
  total: number
}

export interface BotConfig {
  enabled_audience_keys: string[]
  min_confidence: number
  target_countries: string[]
  target_languages: string[]
  exclude_domains: string[]
  llm_config_id: string | null
  active_hours_start: number
  active_hours_end: number
  max_emails_per_day: number
  max_emails_per_hour: number
  run_on_weekends: boolean
  human_in_the_loop: boolean
  dry_run: boolean
}

export interface LLMConfig {
  id: string
  provider: string
  model_name: string
  base_url: string | null
  is_active: boolean
  purpose: string
  display_name: string | null
}

export interface LLMConfigCreate {
  provider: string
  model_name: string
  api_key: string
  base_url?: string | null
  is_default?: boolean
  purpose?: string
  display_name?: string | null
}

export interface RunResponse {
  message: string
  run_type: string
  dry_run: boolean
  state: string
}

export interface SMTPConfig {
  id: string
  name: string
  host: string
  port: number
  username: string
  use_tls: boolean
  from_email: string
  from_name: string | null
  is_default: boolean
  daily_send_limit: number
}

export interface SMTPConfigCreate {
  name: string
  host: string
  port?: number
  username: string
  password: string
  use_tls?: boolean
  from_email: string
  from_name?: string
  daily_send_limit?: number
  is_default?: boolean
}

export interface Campaign {
  id: string
  name: string
  description: string | null
  status: string
  target_audience_keys: string[]
  smtp_config_id: string | null
  llm_config_id: string | null
  email_subject: string
  email_subject_b: string | null
  email_body_html: string
  email_body_text: string
  legitimate_interest_reason: string
  scheduled_at: string | null
  batch_size_per_hour: number | null
  dry_run: boolean
  created_at: string
}

export interface CampaignCreate {
  name: string
  description?: string | null
  target_audience_keys?: string[]
  target_countries?: string[]
  min_confidence?: number
  smtp_config_id?: string | null
  llm_config_id?: string | null
  email_subject?: string
  email_subject_b?: string | null
  email_body_html?: string
  email_body_text?: string
  legitimate_interest_reason?: string
  scheduled_at?: string | null
  batch_size_per_hour?: number | null
  dry_run?: boolean
}

export interface AIDraftResponse {
  subject: string
  body_html: string
  body_text: string
  subject_variants: string[]
}

export interface CampaignAlert {
  type: string
  message: string
}

export interface ABResults {
  subject_a: string
  subject_b: string
  a_sent: number
  b_sent: number
  a_opened: number
  b_opened: number
}

export interface CampaignStats {
  campaign_id: string
  name: string
  status: string
  total_queued: number
  sent: number
  delivered: number
  opened: number
  clicked: number
  replied: number
  bounced: number
  unsubscribed: number
  open_rate: number
  click_rate: number
  bounce_rate: number
  reply_rate: number
  unsub_rate: number
  alerts: CampaignAlert[]
  ab_results: ABResults | null
  created_at: string
}

export interface RecipientRow {
  id: string
  contact_id: string | null
  contact: string
  subject: string
  status: string
  sent_at: string | null
  opened_at: string | null
  bounce_reason: string | null
  click_count: number
}

// ── API helpers ─────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string | null
  refresh_token: string | null
  token_type: string
  requires_totp: boolean
  totp_token: string | null
}

export interface TOTPSetupResponse {
  secret: string
  provisioning_uri: string
  qr_data_url: string
}

export const authApi = {
  login: (email: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { email, password }),
  refresh: (refresh_token: string) =>
    api.post<{ access_token: string; refresh_token: string; token_type: string }>('/auth/refresh', { refresh_token }),
  me: () => api.get<User>('/auth/me'),
  changePassword: (current_password: string, new_password: string) =>
    api.post('/auth/change-password', { current_password, new_password }),
  totpSetup: () => api.post<TOTPSetupResponse>('/auth/totp/setup'),
  totpConfirm: (secret: string, code: string) =>
    api.post('/auth/totp/confirm', { secret, code }),
  totpDisable: (secret: string, code: string) =>
    api.post('/auth/totp/disable', { secret, code }),
  totpVerifyLogin: (totp_token: string, code: string) =>
    api.post<{ access_token: string; refresh_token: string; token_type: string }>('/auth/totp/verify-login', { totp_token, code }),
}

export const botApi = {
  status: () => api.get<BotStatus>('/bot/status'),
  pause: () => api.post('/bot/pause'),
  stop: () => api.post('/bot/stop'),
  run: (dry_run = false, run_type = 'discovery') =>
    api.post<RunResponse>('/bot/run', { dry_run, run_type }),
  runs: () => api.get<AgentRun[]>('/bot/runs'),
  streamUrl: () => `${BASE_URL}/bot/stream`,
}

export const botConfigApi = {
  get: () => api.get<BotConfig>('/bot/config'),
  update: (patch: Partial<BotConfig>) => api.put<BotConfig>('/bot/config', patch),
}

export const audienceTypesApi = {
  list: () => api.get<AudienceTypesResponse>('/audience-types/'),
  setEnabled: (key: string, is_enabled_default: boolean) =>
    api.patch(`/audience-types/${key}`, { is_enabled_default }),
}

export const llmApi = {
  list: () => api.get<LLMConfig[]>('/llm/'),
  create: (data: LLMConfigCreate) => api.post<LLMConfig>('/llm/', data),
  delete: (id: string) => api.delete(`/llm/${id}`),
  setDefault: (id: string) => api.post<LLMConfig>(`/llm/${id}/set-default`),
  test: (id: string, prompt?: string) =>
    api.post<{ success: boolean; content?: string; error?: string; model?: string; prompt_tokens: number; completion_tokens: number }>(
      `/llm/${id}/test`,
      { prompt: prompt ?? 'Say hello in one sentence.' },
    ),
}

export interface ImportError {
  row: number
  email: string
  error: string
}

export interface ImportResult {
  imported: number
  skipped: number
  errors: ImportError[]
}

export interface ContactListParams {
  page?: number
  page_size?: number
  search?: string
  audience_type?: string
  verified_status?: string
  country?: string
  language?: string
  min_confidence?: number
  max_confidence?: number
  sort_by?: string
  sort_dir?: 'asc' | 'desc'
}

export const contactsApi = {
  list: (params: ContactListParams = {}) =>
    api.get<PagedResponse<Contact>>('/contacts/', { params }),
  update: (id: string, patch: ContactUpdate) =>
    api.patch<Contact>(`/contacts/${id}`, patch),
  bulkDelete: (ids: string[]) =>
    api.post<{ deleted: number }>('/contacts/bulk-delete', { ids }),
  importContacts: (file: File, audienceType = 'imported') => {
    const form = new FormData()
    form.append('file', file)
    return api.post<ImportResult>(`/contacts/import?audience_type=${encodeURIComponent(audienceType)}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  exportUrl: (fmt: 'csv' | 'json', params: Omit<ContactListParams, 'page' | 'page_size' | 'sort_by' | 'sort_dir'> = {}) => {
    const qs = new URLSearchParams({ fmt, ...Object.fromEntries(Object.entries(params).filter(([, v]) => v != null).map(([k, v]) => [k, String(v)])) })
    return `${BASE_URL}/contacts/export?${qs.toString()}`
  },
}

export const reportsApi = {
  list: () => api.get<{ items: ReportItem[] }>('/reports/'),
  generate: (date: string) =>
    api.post('/reports/generate', { report_date: date, format: 'both' }),
  downloadPdfUrl: (date: string) => `${BASE_URL}/reports/download/${date}/pdf`,
  downloadXmlUrl: (date: string) => `${BASE_URL}/reports/download/${date}/xml`,
}

export const suppressionApi = {
  list: (page = 1, pageSize = 50, reason?: string, search?: string) =>
    api.get<PagedResponse<SuppressionEntry>>('/suppression/', {
      params: { page, page_size: pageSize, reason: reason || undefined, search: search || undefined },
    }),
  add: (email: string, reason: string, notes?: string) =>
    api.post('/suppression/', { email, reason, notes }),
  remove: (id: string) => api.delete(`/suppression/${id}`),
  bulkImport: (emails: string[], reason = 'manual', notes?: string) =>
    api.post<{ added: number; skipped: number }>('/suppression/bulk-import', { emails, reason, notes }),
  exportUrl: (reason?: string) => {
    const params = new URLSearchParams()
    if (reason) params.set('reason', reason)
    const qs = params.toString()
    return `${BASE_URL}/suppression/export${qs ? `?${qs}` : ''}`
  },
}

export interface AuditLogEntry {
  id: string
  actor_id: string | null
  actor_type: string
  action: string
  resource_type: string | null
  resource_id: string | null
  details: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export const auditApi = {
  list: (page = 1, pageSize = 50, action?: string, actorType?: string, resourceType?: string) =>
    api.get<PagedResponse<AuditLogEntry>>('/audit-logs/', {
      params: {
        page,
        page_size: pageSize,
        action: action || undefined,
        actor_type: actorType || undefined,
        resource_type: resourceType || undefined,
      },
    }),
}

export const statsApi = {
  dashboard: () => api.get<DashboardStats>('/stats/dashboard'),
}

export const healthApi = {
  detailed: () => api.get<HealthStatus>('/health/detailed'),
}

export const smtpApi = {
  list: () => api.get<SMTPConfig[]>('/smtp/'),
  create: (data: SMTPConfigCreate) => api.post<SMTPConfig>('/smtp/', data),
  delete: (id: string) => api.delete(`/smtp/${id}`),
  setDefault: (id: string) => api.post<SMTPConfig>(`/smtp/${id}/set-default`),
  test: (id: string, toEmail: string) =>
    api.post<{ success: boolean; error?: string }>(`/smtp/${id}/test`, { to_email: toEmail }),
}

export interface SequenceStep {
  id: string
  sequence_id: string
  step_number: number
  delay_days: number
  email_subject: string
  email_body_html: string
  email_body_text: string
  created_at: string
}

export interface Sequence {
  id: string
  campaign_id: string
  name: string
  is_active: boolean
  stop_on_reply: boolean
  created_at: string
  steps: SequenceStep[]
}

export const campaignsApi = {
  list: () => api.get<Campaign[]>('/campaigns/'),
  get: (id: string) => api.get<Campaign>(`/campaigns/${id}`),
  create: (data: CampaignCreate) => api.post<Campaign>('/campaigns/', data),
  update: (id: string, data: CampaignCreate) => api.put<Campaign>(`/campaigns/${id}`, data),
  send: (id: string, liaReason: string, scheduledAt?: string | null, batchSize?: number | null) =>
    api.post(`/campaigns/${id}/send`, {
      legitimate_interest_reason: liaReason,
      scheduled_at: scheduledAt ?? null,
      batch_size_per_hour: batchSize ?? null,
    }),
  testSend: (id: string, toEmail: string, subjectOverride?: string) =>
    api.post(`/campaigns/${id}/test-send`, {
      to_email: toEmail,
      subject_override: subjectOverride ?? null,
    }),
  aiDraft: (payload: {
    audience_key: string
    product_context: string
    tone?: string
    language?: string
    llm_config_id?: string | null
  }) => api.post<AIDraftResponse>('/campaigns/ai-draft', payload),
  stats: (id: string) => api.get<CampaignStats>(`/campaigns/${id}/stats`),
  recipients: (id: string, page = 1, pageSize = 50, statusFilter?: string) =>
    api.get<PagedResponse<RecipientRow>>(`/campaigns/${id}/recipients`, {
      params: { page, page_size: pageSize, status: statusFilter || undefined },
    }),
  listSequences: (campaignId: string) =>
    api.get<Sequence[]>(`/campaigns/${campaignId}/sequences`),
  createSequence: (campaignId: string, data: { name?: string; is_active?: boolean; stop_on_reply?: boolean }) =>
    api.post<Sequence>(`/campaigns/${campaignId}/sequences`, data),
  updateSequence: (campaignId: string, seqId: string, data: { name?: string; is_active?: boolean; stop_on_reply?: boolean }) =>
    api.patch<Sequence>(`/campaigns/${campaignId}/sequences/${seqId}`, data),
  deleteSequence: (campaignId: string, seqId: string) =>
    api.delete(`/campaigns/${campaignId}/sequences/${seqId}`),
  addStep: (campaignId: string, seqId: string, data: { step_number: number; delay_days: number; email_subject: string; email_body_html?: string; email_body_text?: string }) =>
    api.post<SequenceStep>(`/campaigns/${campaignId}/sequences/${seqId}/steps`, data),
  updateStep: (campaignId: string, seqId: string, stepId: string, data: { delay_days?: number; email_subject?: string; email_body_html?: string; email_body_text?: string }) =>
    api.patch<SequenceStep>(`/campaigns/${campaignId}/sequences/${seqId}/steps/${stepId}`, data),
  deleteStep: (campaignId: string, seqId: string, stepId: string) =>
    api.delete(`/campaigns/${campaignId}/sequences/${seqId}/steps/${stepId}`),
}
