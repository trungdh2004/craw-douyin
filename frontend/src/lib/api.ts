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
  max_pages_per_run: number
  user_agent: string | null
  proxy_url: string | null
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

export async function apiFetch<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers || {}),
    },
    ...init,
  })
  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `HTTP ${response.status}`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return (await response.json()) as T
}
