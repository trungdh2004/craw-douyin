export type BrowserStatus =
  | 'AUTHENTICATED'
  | 'LOGIN_REQUIRED'
  | 'LOGIN_IN_PROGRESS'
  | 'CAPTCHA_REQUIRED'

export type TargetType = 'CHANNEL' | 'KEYWORD' | 'COLLECT'
export type ScheduleType = 'INTERVAL' | 'DAILY' | 'ONCE' | 'CRON' | 'MANUAL'
export type PresetName = 'SAFE' | 'BALANCED' | 'FAST' | 'CUSTOM'

export interface OverviewStats {
  total_videos: number
  downloaded_videos: number
  bookmarked_videos: number
  active_targets: number
  total_targets: number
  running_jobs: number
  completed_jobs: number
  failed_jobs: number
}

export interface SchedulerStatus {
  running: boolean
  paused: boolean
  jobs_count: number
}

export interface CrawlTargetItem {
  id: number
  name: string
  target_type: TargetType
  target_value: string
  cron_expr: string
  schedule_type: ScheduleType
  schedule_config: Record<string, unknown>
  run_at: string | null
  auto_download: boolean
  max_items_per_run: number
  is_active: boolean
  last_status: string
  last_run_at: string | null
  next_run_at: string | null
  scheduled: boolean
}

export interface VideoItem {
  aweme_id: string
  target_id: number | null
  source_names: string[]
  aweme_type: number
  description: string
  hashtags: string[]
  create_time: string
  crawled_at: string
  author_sec_uid: string
  author_nickname: string
  author_avatar: string | null
  digg_count: number
  comment_count: number
  share_count: number
  collect_count: number
  duration_ms: number
  width: number | null
  height: number | null
  music_title: string | null
  music_author: string | null
  image_count: number
  cover_url: string | null
  original_url: string
  download_status: 'NONE' | 'DOWNLOADING' | 'COMPLETED' | 'FAILED'
  video_local_path: string | null
  downloaded_at: string | null
  download_error: string | null
  is_bookmarked: boolean
  bookmarked_at: string | null
  bookmark_collection: string | null
  bookmark_note: string | null
  edit_item_id?: string | null
  edit_list_id?: string | null
  edit_sent_at?: string | null
  edit_status?: 'SENT' | 'FAILED' | string | null
  edit_error?: string | null
  edit_studio_url?: string | null
}

export interface EditStudioConfig {
  host: string
  port: number
  base_url: string
  updated_at?: string
}

export interface SendToEditResponse {
  list_id: string
  item_ids: string[]
  studio_url: string
  edit_base_url: string
}

export interface VideoPage {
  items: VideoItem[]
  total: number
  page: number
  page_size: number
}

export interface BookmarkCollection {
  name: string
  count: number
}

export interface TrendingHashtagItem {
  tag: string
  video_count: number
  total_digg: number
}

export interface TrendingMusicItem {
  title: string
  author: string | null
  video_count: number
  total_digg: number
}

export interface SuggestedTopicItem {
  keyword: string
  label: string
  category: string
}

export interface TrendsResponse {
  trending_hashtags: TrendingHashtagItem[]
  trending_music: TrendingMusicItem[]
  suggested_topics: SuggestedTopicItem[]
}

export interface CrawlLogEventItem {
  ts: string
  level: 'INFO' | 'SUCCESS' | 'WARN' | 'ERROR' | string
  step: string
  message: string
}

export interface CrawlLogItem {
  id: number
  target_id: number | null
  target_name: string | null
  job_type: 'TARGET_CRAWL' | 'SINGLE_CRAWL' | 'DOWNLOAD'
  trigger_type: 'SCHEDULED' | 'MANUAL' | 'ONCE' | 'RETRY'
  input_summary: string | null
  started_at: string
  finished_at: string | null
  duration_ms: number | null
  status: 'SCHEDULED' | 'RUNNING' | 'SUCCESS' | 'FAILED' | 'CAPTCHA_BLOCKED'
  new_videos_count: number
  updated_videos_count: number
  scanned_count?: number
  target_limit?: number
  current_phase?: string | null
  events?: CrawlLogEventItem[]
  error_message: string | null
}

export interface CrawlLogPage {
  items: CrawlLogItem[]
  total: number
  page: number
  page_size: number
}

export interface AntiBotSettings {
  preset: PresetName
  scroll_delay_min_ms: number
  scroll_delay_max_ms: number
  download_delay_min_ms: number
  download_delay_max_ms: number
  cooldown_between_targets_sec: number
  stealth_mode: boolean
  human_scroll: boolean
  auto_stop_on_captcha: boolean
  headless_mode?: boolean
  max_pages_per_run: number
  user_agent: string | null
  proxy_url: string | null
  edit_studio_host?: string
  edit_studio_port?: number
  updated_at: string
}

export function formatDurationMs(durationMs: number | null | undefined): string {
  if (!durationMs || durationMs <= 0) return '00:00'
  const totalSeconds = Math.round(durationMs / 1000)
  const hours = Math.floor(totalSeconds / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const mm = String(minutes).padStart(2, '0')
  const ss = String(seconds).padStart(2, '0')
  if (hours > 0) {
    return `${String(hours).padStart(2, '0')}:${mm}:${ss}`
  }
  return `${mm}:${ss}`
}

export function formatExecutionDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return 'Đang chạy…'
  if (ms < 1000) return `${ms}ms`
  const sec = (ms / 1000).toFixed(1)
  return `${sec}s`
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('vi-VN', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function formatNumber(n: number | null | undefined): string {
  if (n === null || n === undefined) return '0'
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 10_000) return `${(n / 1_000).toFixed(1)}K`
  return n.toLocaleString('vi-VN')
}

export function describeSchedule(target: CrawlTargetItem): string {
  const cfg = target.schedule_config || {}
  switch (target.schedule_type) {
    case 'INTERVAL': {
      const every = Number(cfg.every || 60)
      const unit = cfg.unit === 'hours' ? 'giờ' : 'phút'
      return `Mỗi ${every} ${unit}`
    }
    case 'DAILY': {
      const hh = String(cfg.hour ?? 8).padStart(2, '0')
      const mm = String(cfg.minute ?? 0).padStart(2, '0')
      const days = cfg.days_of_week && cfg.days_of_week !== '*' ? ` (${String(cfg.days_of_week)})` : ' hằng ngày'
      return `${hh}:${mm}${days}`
    }
    case 'ONCE':
      return target.run_at ? `1 lần: ${formatDateTime(target.run_at)}` : 'Chạy 1 lần'
    case 'MANUAL':
      return 'Thủ công'
    case 'CRON':
    default:
      return `Cron: ${target.cron_expr}`
  }
}

export interface AuthStatusResponse {
  authenticated?: boolean
  username?: string | null
}

export interface LoginResponse {
  authenticated: boolean
  username: string
  token: string
}

const SESSION_TOKEN_KEY = 'douyin_session_token'

export function getSessionToken(): string | null {
  try {
    return window.sessionStorage.getItem(SESSION_TOKEN_KEY)
  } catch {
    return null
  }
}

export function setSessionToken(token: string): void {
  try {
    window.sessionStorage.setItem(SESSION_TOKEN_KEY, token)
  } catch {
    // ignore storage errors
  }
}

export function clearSessionToken(): void {
  try {
    window.sessionStorage.removeItem(SESSION_TOKEN_KEY)
  } catch {
    // ignore storage errors
  }
}

export async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const token = getSessionToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((init?.headers as Record<string, string>) || {}),
  }
  const response = await fetch(url, {
    credentials: 'same-origin',
    ...init,
    headers,
  })
  if (!response.ok) {
    if (response.status === 401 && !url.includes('/api/auth/login')) {
      clearSessionToken()
      window.dispatchEvent(new CustomEvent('douyin:unauthorized'))
    }
    const text = await response.text()
    let message = text || `HTTP ${response.status}`
    try {
      const parsed = JSON.parse(text) as { detail?: string }
      if (parsed?.detail) {
        message = parsed.detail
      }
    } catch {
      // keep raw text
    }
    throw new Error(message)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
