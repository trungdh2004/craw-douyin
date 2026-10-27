import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  AlertTriangle,
  Bookmark,
  CalendarClock,
  CheckCircle2,
  Clock,
  Edit3,
  Film,
  History,
  LayoutDashboard,
  Link2,
  PauseCircle,
  Play,
  PlayCircle,
  Plus,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  Trash2,
  Zap,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'
import {
  type VideoFilterState,
  VideoListSection,
} from '@/components/VideoListSection'
import { VideoPreviewDialog } from '@/components/VideoPreviewDialog'
import {
  type AntiBotSettings,
  type BookmarkCollection,
  type BrowserStatus,
  type CrawlLogPage,
  type CrawlTargetItem,
  type OverviewStats,
  type PresetName,
  type ScheduleType,
  type SchedulerStatus,
  type TargetType,
  type VideoItem,
  type VideoPage,
  apiFetch,
  describeSchedule,
  formatDateTime,
  formatDurationMs,
  formatExecutionDuration,
  formatNumber,
} from '@/lib/api'

type NavSection =
  | 'overview'
  | 'library'
  | 'bookmarks'
  | 'single-crawl'
  | 'targets'
  | 'history'
  | 'anti-bot'

interface TargetFormState {
  id: number | null
  name: string
  target_type: TargetType
  target_value: string
  schedule_type: ScheduleType
  interval_every: number
  interval_unit: 'minutes' | 'hours'
  daily_hour: number
  daily_minute: number
  daily_days: string
  once_run_at: string
  cron_expr: string
  max_items_per_run: number
  auto_download: boolean
  is_active: boolean
}

const DEFAULT_TARGET_FORM: TargetFormState = {
  id: null,
  name: '',
  target_type: 'CHANNEL',
  target_value: '',
  schedule_type: 'INTERVAL',
  interval_every: 6,
  interval_unit: 'hours',
  daily_hour: 8,
  daily_minute: 0,
  daily_days: '*',
  once_run_at: '',
  cron_expr: '0 */6 * * *',
  max_items_per_run: 50,
  auto_download: false,
  is_active: true,
}

const DEFAULT_VIDEO_FILTERS: VideoFilterState = {
  search: '',
  target_id: '',
  aweme_type: '',
  download_status: '',
  min_digg: '',
  min_duration_sec: '',
  max_duration_sec: '',
  bookmark_collection: '',
  sort: 'create_time',
  order: 'desc',
  page: 1,
}

export function App() {
  const [activeSection, setActiveSection] = useState<NavSection>('overview')
  const [browserStatus, setBrowserStatus] = useState<BrowserStatus>('LOGIN_REQUIRED')
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus>({
    running: true,
    paused: false,
    jobs_count: 0,
  })
  const [stats, setStats] = useState<OverviewStats>({
    total_videos: 0,
    downloaded_videos: 0,
    bookmarked_videos: 0,
    active_targets: 0,
    total_targets: 0,
    running_jobs: 0,
    completed_jobs: 0,
    failed_jobs: 0,
  })
  const [targets, setTargets] = useState<CrawlTargetItem[]>([])
  const [videosPage, setVideosPage] = useState<VideoPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: 24,
  })
  const [bookmarksPage, setBookmarksPage] = useState<VideoPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: 24,
  })
  const [collections, setCollections] = useState<BookmarkCollection[]>([])
  const [libraryFilters, setLibraryFilters] = useState<VideoFilterState>(DEFAULT_VIDEO_FILTERS)
  const [bookmarkFilters, setBookmarkFilters] = useState<VideoFilterState>(DEFAULT_VIDEO_FILTERS)
  const [previewVideo, setPreviewVideo] = useState<VideoItem | null>(null)

  // Single Crawl state
  const [singleInputsText, setSingleInputsText] = useState('')
  const [singleAutoDownload, setSingleAutoDownload] = useState(true)
  const [singleBookmark, setSingleBookmark] = useState(false)
  const [singleCollection, setSingleCollection] = useState('')
  const [singleScheduleMode, setSingleScheduleMode] = useState<'NOW' | 'ONCE'>('NOW')
  const [singleRunAt, setSingleRunAt] = useState('')
  const [singleStatusMessage, setSingleStatusMessage] = useState<string | null>(null)

  // Target Modal state
  const [targetModalOpen, setTargetModalOpen] = useState(false)
  const [targetForm, setTargetForm] = useState<TargetFormState>(DEFAULT_TARGET_FORM)

  // Logs state
  const [logsPage, setLogsPage] = useState<CrawlLogPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: 50,
  })
  const [logJobTypeFilter, setLogJobTypeFilter] = useState('')
  const [logStatusFilter, setLogStatusFilter] = useState('')
  const [logTargetFilter, setLogTargetFilter] = useState('')

  // Anti-bot state
  const [antiBot, setAntiBot] = useState<AntiBotSettings | null>(null)
  const [antiBotSavedNotice, setAntiBotSavedNotice] = useState(false)

  const buildVideoQuery = (filters: VideoFilterState, forceBookmark?: boolean): string => {
    const params = new URLSearchParams()
    if (filters.search) params.set('search', filters.search)
    if (filters.target_id) params.set('target_id', filters.target_id)
    if (filters.aweme_type !== '') params.set('aweme_type', filters.aweme_type)
    if (filters.download_status) params.set('download_status', filters.download_status)
    if (filters.min_digg) params.set('min_digg', filters.min_digg)
    if (filters.min_duration_sec) {
      params.set('min_duration_ms', String(Number(filters.min_duration_sec) * 1000))
    }
    if (filters.max_duration_sec) {
      params.set('max_duration_ms', String(Number(filters.max_duration_sec) * 1000))
    }
    if (forceBookmark) {
      params.set('is_bookmarked', 'true')
    }
    if (filters.bookmark_collection) {
      params.set('bookmark_collection', filters.bookmark_collection)
    }
    params.set('sort', filters.sort)
    params.set('order', filters.order)
    params.set('page', String(filters.page))
    params.set('page_size', '24')
    return params.toString()
  }

  const refreshCoreStatus = useCallback(async () => {
    try {
      const [browserRes, schedRes, statsRes, targetsRes] = await Promise.all([
        apiFetch<{ status: BrowserStatus }>('/api/browser/status'),
        apiFetch<SchedulerStatus>('/api/scheduler/status'),
        apiFetch<OverviewStats>('/api/stats'),
        apiFetch<CrawlTargetItem[]>('/api/targets'),
      ])
      setBrowserStatus(browserRes.status)
      setSchedulerStatus(schedRes)
      setStats(statsRes)
      setTargets(targetsRes)
    } catch {
      // ignore transient network errors
    }
  }, [])

  const loadLibrary = useCallback(async () => {
    try {
      const q = buildVideoQuery(libraryFilters)
      const data = await apiFetch<VideoPage>(`/api/videos?${q}`)
      setVideosPage(data)
    } catch {
      // ignore
    }
  }, [libraryFilters])

  const loadBookmarks = useCallback(async () => {
    try {
      const q = buildVideoQuery(bookmarkFilters, true)
      const [data, cols] = await Promise.all([
        apiFetch<VideoPage>(`/api/videos?${q}`),
        apiFetch<BookmarkCollection[]>('/api/bookmarks/collections'),
      ])
      setBookmarksPage(data)
      setCollections(cols)
    } catch {
      // ignore
    }
  }, [bookmarkFilters])

  const loadLogs = useCallback(async () => {
    try {
      const params = new URLSearchParams()
      if (logJobTypeFilter) params.set('job_type', logJobTypeFilter)
      if (logStatusFilter) params.set('status', logStatusFilter)
      if (logTargetFilter) params.set('target_id', logTargetFilter)
      const data = await apiFetch<CrawlLogPage>(`/api/logs?${params.toString()}`)
      setLogsPage(data)
    } catch {
      // ignore
    }
  }, [logJobTypeFilter, logStatusFilter, logTargetFilter])

  const loadAntiBot = useCallback(async () => {
    try {
      const data = await apiFetch<AntiBotSettings>('/api/settings/anti-bot')
      setAntiBot(data)
    } catch {
      // ignore
    }
  }, [])

  useEffect(() => {
    void refreshCoreStatus()
    void loadLibrary()
    void loadBookmarks()
    void loadLogs()
    void loadAntiBot()
  }, [refreshCoreStatus, loadLibrary, loadBookmarks, loadLogs, loadAntiBot])

  // Auto-poll status while jobs or login are running
  useEffect(() => {
    const timer = window.setInterval(() => {
      void refreshCoreStatus()
      if (
        stats.running_jobs > 0 ||
        activeSection === 'history' ||
        activeSection === 'overview'
      ) {
        void loadLogs()
      }
      if (stats.running_jobs > 0) {
        void loadLibrary()
        void loadBookmarks()
      }
    }, 3000)
    return () => window.clearInterval(timer)
  }, [
    stats.running_jobs,
    activeSection,
    refreshCoreStatus,
    loadLogs,
    loadLibrary,
    loadBookmarks,
  ])

  const handleOpenLoginBrowser = async () => {
    const res = await apiFetch<{ status: BrowserStatus }>('/api/browser/login', {
      method: 'POST',
    })
    setBrowserStatus(res.status)
  }

  const handleToggleScheduler = async () => {
    const endpoint = schedulerStatus.paused ? '/api/scheduler/resume' : '/api/scheduler/pause'
    const res = await apiFetch<SchedulerStatus>(endpoint, { method: 'POST' })
    setSchedulerStatus(res)
  }

  const handleDownloadSingle = async (awemeId: string) => {
    await apiFetch(`/api/videos/${awemeId}/download`, { method: 'POST' })
    window.setTimeout(() => {
      void loadLibrary()
      void loadBookmarks()
      void refreshCoreStatus()
    }, 800)
  }

  const handleBatchDownload = async (awemeIds: string[]) => {
    if (awemeIds.length === 0) return
    await apiFetch('/api/videos/batch-download', {
      method: 'POST',
      body: JSON.stringify({ aweme_ids: awemeIds }),
    })
    window.setTimeout(() => {
      void loadLibrary()
      void loadBookmarks()
      void refreshCoreStatus()
    }, 800)
  }

  const handleToggleBookmark = async (video: VideoItem) => {
    const updated = await apiFetch<VideoItem>(`/api/videos/${video.aweme_id}/bookmark`, {
      method: 'PATCH',
      body: JSON.stringify({
        is_bookmarked: !video.is_bookmarked,
      }),
    })
    if (previewVideo?.aweme_id === video.aweme_id) {
      setPreviewVideo(updated)
    }
    await Promise.all([loadLibrary(), loadBookmarks(), refreshCoreStatus()])
  }

  const handleSaveBookmarkDetail = async (
    awemeId: string,
    isBookmarked: boolean,
    collection: string,
    note: string,
  ) => {
    const updated = await apiFetch<VideoItem>(`/api/videos/${awemeId}/bookmark`, {
      method: 'PATCH',
      body: JSON.stringify({
        is_bookmarked: isBookmarked,
        bookmark_collection: collection,
        bookmark_note: note,
      }),
    })
    setPreviewVideo(updated)
    await Promise.all([loadLibrary(), loadBookmarks(), refreshCoreStatus()])
  }

  const handleBatchBookmark = async (
    awemeIds: string[],
    isBookmarked: boolean,
    collection?: string,
  ) => {
    await apiFetch('/api/videos/batch-bookmark', {
      method: 'POST',
      body: JSON.stringify({
        aweme_ids: awemeIds,
        is_bookmarked: isBookmarked,
        bookmark_collection: collection,
      }),
    })
    await Promise.all([loadLibrary(), loadBookmarks(), refreshCoreStatus()])
  }

  const handleSyncDouyinCollect = async () => {
    await apiFetch('/api/bookmarks/sync-douyin', { method: 'POST' })
    await Promise.all([refreshCoreStatus(), loadLogs()])
  }

  const handleSubmitSingleCrawl = async (e: React.FormEvent) => {
    e.preventDefault()
    const lines = singleInputsText
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean)
    if (lines.length === 0) return

    const runAtIso =
      singleScheduleMode === 'ONCE' && singleRunAt
        ? new Date(singleRunAt).toISOString()
        : null

    const res = await apiFetch<{ status: string; log_id: number; count: number }>(
      '/api/crawl/items',
      {
        method: 'POST',
        body: JSON.stringify({
          inputs: lines,
          auto_download: singleAutoDownload,
          is_bookmarked: singleBookmark,
          bookmark_collection: singleCollection || null,
          run_at: runAtIso,
        }),
      },
    )
    setSingleInputsText('')
    setSingleStatusMessage(
      res.status === 'SCHEDULED'
        ? `Đã hẹn giờ quét ${res.count} ID/link (Mã phiên #${res.log_id})`
        : `Đang chạy quét ngay ${res.count} ID/link (Mã phiên #${res.log_id})`,
    )
    await Promise.all([refreshCoreStatus(), loadLogs(), loadLibrary()])
  }

  const openCreateTargetModal = () => {
    setTargetForm(DEFAULT_TARGET_FORM)
    setTargetModalOpen(true)
  }

  const openEditTargetModal = (target: CrawlTargetItem) => {
    const cfg = target.schedule_config || {}
    setTargetForm({
      id: target.id,
      name: target.name,
      target_type: target.target_type,
      target_value: target.target_value,
      schedule_type: target.schedule_type,
      interval_every: Number(cfg.every || 6),
      interval_unit: cfg.unit === 'minutes' ? 'minutes' : 'hours',
      daily_hour: Number(cfg.hour ?? 8),
      daily_minute: Number(cfg.minute ?? 0),
      daily_days: String(cfg.days_of_week || '*'),
      once_run_at: target.run_at ? target.run_at.slice(0, 16) : '',
      cron_expr: target.cron_expr || '0 */6 * * *',
      max_items_per_run: target.max_items_per_run,
      auto_download: target.auto_download,
      is_active: target.is_active,
    })
    setTargetModalOpen(true)
  }

  const handleSaveTarget = async (e: React.FormEvent) => {
    e.preventDefault()
    let scheduleConfig: Record<string, unknown> = {}
    let runAtIso: string | null = null

    if (targetForm.schedule_type === 'INTERVAL') {
      scheduleConfig = {
        every: Number(targetForm.interval_every),
        unit: targetForm.interval_unit,
      }
    } else if (targetForm.schedule_type === 'DAILY') {
      scheduleConfig = {
        hour: Number(targetForm.daily_hour),
        minute: Number(targetForm.daily_minute),
        days_of_week: targetForm.daily_days || '*',
      }
    } else if (targetForm.schedule_type === 'ONCE' && targetForm.once_run_at) {
      runAtIso = new Date(targetForm.once_run_at).toISOString()
    }

    const body = {
      name: targetForm.name,
      target_type: targetForm.target_type,
      target_value:
        targetForm.target_type === 'COLLECT' && !targetForm.target_value
          ? 'self'
          : targetForm.target_value,
      cron_expr: targetForm.cron_expr || '0 */6 * * *',
      schedule_type: targetForm.schedule_type,
      schedule_config: scheduleConfig,
      run_at: runAtIso,
      auto_download: targetForm.auto_download,
      max_items_per_run: Number(targetForm.max_items_per_run),
      is_active: targetForm.is_active,
    }

    if (targetForm.id === null) {
      await apiFetch('/api/targets', {
        method: 'POST',
        body: JSON.stringify(body),
      })
    } else {
      await apiFetch(`/api/targets/${targetForm.id}`, {
        method: 'PUT',
        body: JSON.stringify(body),
      })
    }
    setTargetModalOpen(false)
    await refreshCoreStatus()
  }

  const handleRunTargetNow = async (targetId: number) => {
    await apiFetch(`/api/targets/${targetId}/run`, { method: 'POST' })
    await Promise.all([refreshCoreStatus(), loadLogs()])
  }

  const handleToggleTargetActive = async (target: CrawlTargetItem) => {
    await apiFetch(`/api/targets/${target.id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: !target.is_active }),
    })
    await refreshCoreStatus()
  }

  const handleDeleteTarget = async (targetId: number) => {
    await apiFetch(`/api/targets/${targetId}`, { method: 'DELETE' })
    await refreshCoreStatus()
  }

  const handleRetryLog = async (logId: number) => {
    await apiFetch(`/api/logs/${logId}/retry`, { method: 'POST' })
    await Promise.all([loadLogs(), refreshCoreStatus()])
  }

  const handleDeleteLog = async (logId: number) => {
    await apiFetch(`/api/logs/${logId}`, { method: 'DELETE' })
    await loadLogs()
  }

  const handleClearCompletedLogs = async () => {
    await apiFetch('/api/logs', { method: 'DELETE' })
    await loadLogs()
  }

  const handleApplyPreset = async (preset: PresetName) => {
    const updated = await apiFetch<AntiBotSettings>('/api/settings/anti-bot', {
      method: 'PUT',
      body: JSON.stringify({ preset }),
    })
    setAntiBot(updated)
    setAntiBotSavedNotice(true)
    window.setTimeout(() => setAntiBotSavedNotice(false), 2000)
  }

  const handleSaveAntiBot = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!antiBot) return
    const updated = await apiFetch<AntiBotSettings>('/api/settings/anti-bot', {
      method: 'PUT',
      body: JSON.stringify({
        ...antiBot,
        preset: 'CUSTOM',
      }),
    })
    setAntiBot(updated)
    setAntiBotSavedNotice(true)
    window.setTimeout(() => setAntiBotSavedNotice(false), 2000)
  }

  const navItems: {
    id: NavSection
    label: string
    icon: React.ComponentType<{ className?: string }>
    badge?: string | number
  }[] = [
    { id: 'overview', label: 'Tổng quan', icon: LayoutDashboard },
    {
      id: 'library',
      label: 'Thư viện Video',
      icon: Film,
      badge: stats.total_videos || undefined,
    },
    {
      id: 'bookmarks',
      label: 'Đã Bookmark',
      icon: Bookmark,
      badge: stats.bookmarked_videos || undefined,
    },
    { id: 'single-crawl', label: 'Crawl 1 ID / Link', icon: Link2 },
    {
      id: 'targets',
      label: 'Mục tiêu & Hẹn giờ',
      icon: CalendarClock,
      badge: stats.active_targets || undefined,
    },
    {
      id: 'history',
      label: 'Lịch sử chạy',
      icon: History,
      badge: stats.running_jobs > 0 ? `${stats.running_jobs} chạy` : undefined,
    },
    { id: 'anti-bot', label: 'Cấu hình Chống Bot', icon: ShieldCheck },
  ]

  return (
    <div className="flex h-screen w-screen overflow-hidden bg-background text-foreground">
      {/* Left Sidebar cố định bên trái */}
      <aside className="w-64 shrink-0 border-r bg-sidebar flex flex-col justify-between">
        <div className="p-4 space-y-6">
          <div className="flex items-center gap-3 px-2">
            <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-primary-foreground font-bold shadow">
              DY
            </div>
            <div>
              <div className="font-bold tracking-tight text-base">Douyin Crawler</div>
              <div className="text-[11px] text-muted-foreground">
                Studio Thu Thập & Tải Không Logo
              </div>
            </div>
          </div>

          <nav className="space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = activeSection === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center justify-between rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                    active
                      ? 'bg-primary text-primary-foreground shadow-sm'
                      : 'text-sidebar-foreground/80 hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                  }`}
                >
                  <span className="flex items-center gap-2.5">
                    <Icon className="size-4" />
                    <span>{item.label}</span>
                  </span>
                  {item.badge !== undefined && (
                    <Badge
                      variant={active ? 'secondary' : 'outline'}
                      className="text-[10px] px-1.5 py-0"
                    >
                      {item.badge}
                    </Badge>
                  )}
                </button>
              )
            })}
          </nav>
        </div>

        {/* Trạng thái phiên & chống bot ở chân Sidebar */}
        <div className="p-4 border-t space-y-3 bg-muted/20">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Phiên Douyin:</span>
            <Badge
              variant={
                browserStatus === 'AUTHENTICATED'
                  ? 'default'
                  : browserStatus === 'CAPTCHA_REQUIRED'
                    ? 'destructive'
                    : 'secondary'
              }
              className="text-[10px]"
            >
              {browserStatus === 'AUTHENTICATED'
                ? 'Đã đăng nhập'
                : browserStatus === 'CAPTCHA_REQUIRED'
                  ? 'Dính Captcha!'
                  : browserStatus === 'LOGIN_IN_PROGRESS'
                    ? 'Đang mở...'
                    : 'Cần đăng nhập'}
            </Badge>
          </div>
          <Button
            size="sm"
            variant={browserStatus === 'CAPTCHA_REQUIRED' ? 'destructive' : 'outline'}
            className="w-full text-xs"
            disabled={browserStatus === 'LOGIN_IN_PROGRESS'}
            onClick={() => void handleOpenLoginBrowser()}
          >
            {browserStatus === 'CAPTCHA_REQUIRED'
              ? 'Mở Chromium giải Captcha'
              : 'Mở Chromium đăng nhập QR'}
          </Button>
          {antiBot && (
            <div className="flex items-center justify-between text-[11px] text-muted-foreground pt-1">
              <span>Chế độ Chống Bot:</span>
              <span className="font-semibold text-emerald-400">{antiBot.preset}</span>
            </div>
          )}
        </div>
      </aside>

      {/* Vùng nội dung chính bên phải */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Topbar trạng thái toàn cục */}
        <header className="h-14 shrink-0 border-b px-6 flex items-center justify-between bg-card/50 backdrop-blur">
          <div className="flex items-center gap-3 text-sm">
            <span className="font-semibold text-muted-foreground">
              Trạng thái đăng nhập Douyin:
            </span>
            <Badge
              variant={
                browserStatus === 'AUTHENTICATED'
                  ? 'default'
                  : browserStatus === 'CAPTCHA_REQUIRED'
                    ? 'destructive'
                    : 'outline'
              }
            >
              {browserStatus}
            </Badge>
            {stats.running_jobs > 0 && (
              <Badge variant="secondary" className="gap-1.5 animate-pulse">
                <Activity className="size-3.5 text-cyan-400" />
                Đang chạy {stats.running_jobs} tác vụ
              </Badge>
            )}
          </div>

          <div className="flex items-center gap-2.5">
            <div className="flex items-center gap-2 rounded-lg border px-3 py-1 text-xs">
              <span className="text-muted-foreground">Bộ hẹn giờ (Scheduler):</span>
              <Badge variant={schedulerStatus.paused ? 'secondary' : 'default'}>
                {schedulerStatus.paused ? 'Đang tạm dừng' : 'Đang hoạt động'}
              </Badge>
              <Button
                size="sm"
                variant="ghost"
                className="h-6 px-2 text-xs"
                onClick={() => void handleToggleScheduler()}
              >
                {schedulerStatus.paused ? (
                  <>
                    <PlayCircle className="size-3.5 mr-1 text-emerald-400" /> Tiếp tục
                  </>
                ) : (
                  <>
                    <PauseCircle className="size-3.5 mr-1 text-amber-400" /> Tạm dừng
                  </>
                )}
              </Button>
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => {
                void refreshCoreStatus()
                void loadLibrary()
                void loadBookmarks()
                void loadLogs()
              }}
            >
              <RefreshCw className="size-3.5 mr-1.5" /> Đồng bộ
            </Button>
          </div>
        </header>

        {/* Cảnh báo nổi bật nếu phát hiện Captcha */}
        {browserStatus === 'CAPTCHA_REQUIRED' && (
          <div className="bg-destructive/15 border-b border-destructive/40 px-6 py-3 flex items-center justify-between">
            <div className="flex items-center gap-2.5 text-sm text-destructive">
              <AlertTriangle className="size-5 shrink-0" />
              <span>
                <strong>Phát hiện Captcha từ Douyin!</strong> Hệ thống Chống Bot đã tự động dừng
                phiên quét để bảo vệ tài khoản. Hãy mở Chromium để kéo hình xác thực.
              </span>
            </div>
            <Button
              size="sm"
              variant="destructive"
              onClick={() => void handleOpenLoginBrowser()}
            >
              Mở Chromium giải Captcha ngay
            </Button>
          </div>
        )}

        {/* Nội dung từng phân khu của Sidebar */}
        <main className="flex-1 overflow-y-auto p-6">
          <div className="mx-auto max-w-7xl space-y-6">
            {activeSection === 'overview' && (
              <div className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight">
                      Tổng quan Hệ thống Douyin Crawler
                    </h1>
                    <p className="text-sm text-muted-foreground">
                      Giám sát thu thập dữ liệu, kho video không logo, Bookmark và lịch chạy tự động.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button size="sm" onClick={() => setActiveSection('single-crawl')}>
                      <Link2 className="size-4 mr-1.5" /> Crawl nhanh 1 ID / Link
                    </Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      onClick={() => {
                        setActiveSection('targets')
                        openCreateTargetModal()
                      }}
                    >
                      <Plus className="size-4 mr-1.5" /> Thêm Mục tiêu Hẹn giờ
                    </Button>
                  </div>
                </div>

                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                  <Card
                    className="cursor-pointer hover:border-primary/50"
                    onClick={() => setActiveSection('library')}
                  >
                    <CardHeader className="pb-2">
                      <CardDescription>Tổng bài đã Crawl</CardDescription>
                      <CardTitle className="text-3xl font-bold">
                        {formatNumber(stats.total_videos)}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-muted-foreground flex items-center justify-between">
                      <span>Đã tải không logo: {stats.downloaded_videos}</span>
                      <Film className="size-4 text-primary" />
                    </CardContent>
                  </Card>

                  <Card
                    className="cursor-pointer hover:border-primary/50"
                    onClick={() => setActiveSection('bookmarks')}
                  >
                    <CardHeader className="pb-2">
                      <CardDescription>Video Đã Bookmark</CardDescription>
                      <CardTitle className="text-3xl font-bold text-amber-400">
                        {formatNumber(stats.bookmarked_videos)}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-muted-foreground flex items-center justify-between">
                      <span>{collections.length} bộ sưu tập phân loại</span>
                      <Bookmark className="size-4 text-amber-400" />
                    </CardContent>
                  </Card>

                  <Card
                    className="cursor-pointer hover:border-primary/50"
                    onClick={() => setActiveSection('targets')}
                  >
                    <CardHeader className="pb-2">
                      <CardDescription>Mục tiêu Hẹn giờ Active</CardDescription>
                      <CardTitle className="text-3xl font-bold text-cyan-400">
                        {stats.active_targets} / {stats.total_targets}
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-muted-foreground flex items-center justify-between">
                      <span>{schedulerStatus.jobs_count} lịch trong Scheduler</span>
                      <CalendarClock className="size-4 text-cyan-400" />
                    </CardContent>
                  </Card>

                  <Card
                    className="cursor-pointer hover:border-primary/50"
                    onClick={() => setActiveSection('history')}
                  >
                    <CardHeader className="pb-2">
                      <CardDescription>Phiên chạy Thành công / Lỗi</CardDescription>
                      <CardTitle className="text-3xl font-bold text-emerald-400">
                        {stats.completed_jobs}{' '}
                        <span className="text-base font-normal text-rose-400">
                          / {stats.failed_jobs} lỗi
                        </span>
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="text-xs text-muted-foreground flex items-center justify-between">
                      <span>Đang chạy: {stats.running_jobs}</span>
                      <History className="size-4 text-emerald-400" />
                    </CardContent>
                  </Card>
                </div>

                <div className="grid gap-6 lg:grid-cols-12">
                  <Card className="lg:col-span-7">
                    <CardHeader className="flex flex-row items-center justify-between pb-3">
                      <div>
                        <CardTitle className="text-base">
                          Bài đăng mới thu thập gần nhất
                        </CardTitle>
                        <CardDescription>
                          Hiển thị sẵn thời lượng video (MM:SS), thời gian đăng và chỉ số tương tác
                        </CardDescription>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setActiveSection('library')}
                      >
                        Xem tất cả →
                      </Button>
                    </CardHeader>
                    <CardContent className="space-y-2.5">
                      {videosPage.items.slice(0, 5).map((v) => (
                        <div
                          key={v.aweme_id}
                          onClick={() => setPreviewVideo(v)}
                          className="flex items-center gap-3 rounded-xl border p-2.5 hover:bg-muted/40 cursor-pointer"
                        >
                          <div className="relative h-14 w-24 rounded-lg bg-slate-900 overflow-hidden shrink-0">
                            {v.cover_url && (
                              <img
                                src={v.cover_url}
                                alt=""
                                className="h-full w-full object-cover"
                              />
                            )}
                            <span className="absolute bottom-1 right-1 rounded bg-black/80 px-1.5 py-0.2 text-[10px] font-mono text-white">
                              {v.aweme_type === 68
                                ? `${v.image_count} ảnh`
                                : formatDurationMs(v.duration_ms)}
                            </span>
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-sm font-medium">
                              {v.description || v.aweme_id}
                            </p>
                            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground mt-0.5">
                              <span className="font-medium text-foreground">
                                @{v.author_nickname}
                              </span>
                              <span>· Đăng: {formatDateTime(v.create_time)}</span>
                              <span>· ❤ {formatNumber(v.digg_count)}</span>
                            </div>
                          </div>
                          <Badge variant="outline" className="text-[10px]">
                            {v.download_status}
                          </Badge>
                        </div>
                      ))}
                      {videosPage.items.length === 0 && (
                        <p className="text-sm text-muted-foreground py-8 text-center">
                          Chưa có video nào được thu thập. Hãy chạy quét mục tiêu hoặc Crawl 1 ID.
                        </p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="lg:col-span-5">
                    <CardHeader className="flex flex-row items-center justify-between pb-3">
                      <div>
                        <CardTitle className="text-base">Hoạt động chạy gần đây</CardTitle>
                        <CardDescription>Lịch sử các phiên quét gần nhất</CardDescription>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => setActiveSection('history')}
                      >
                        Chi tiết →
                      </Button>
                    </CardHeader>
                    <CardContent className="space-y-2.5">
                      {logsPage.items.slice(0, 6).map((log) => (
                        <div
                          key={log.id}
                          className="flex items-center justify-between rounded-xl border p-2.5 text-xs"
                        >
                          <div className="space-y-0.5 min-w-0">
                            <div className="font-medium truncate">
                              {log.target_name || log.input_summary || `Phiên #${log.id}`}
                            </div>
                            <div className="text-muted-foreground">
                              {formatDateTime(log.started_at)} ·{' '}
                              {formatExecutionDuration(log.duration_ms)} · +{log.new_videos_count}{' '}
                              mới
                            </div>
                          </div>
                          <Badge
                            variant={
                              log.status === 'SUCCESS'
                                ? 'default'
                                : log.status === 'RUNNING'
                                  ? 'secondary'
                                  : 'destructive'
                            }
                          >
                            {log.status}
                          </Badge>
                        </div>
                      ))}
                      {logsPage.items.length === 0 && (
                        <p className="text-sm text-muted-foreground py-8 text-center">
                          Chưa có lịch sử chạy nào.
                        </p>
                      )}
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'library' && (
              <VideoListSection
                title="Thư viện Bài đăng Đã Crawl"
                subtitle="Hiển thị đầy đủ Metadata, thời lượng phát của video (MM:SS), thời gian đăng & thời gian thu thập."
                videos={videosPage.items}
                total={videosPage.total}
                pageSize={videosPage.page_size}
                targets={targets}
                filters={libraryFilters}
                onFiltersChange={setLibraryFilters}
                onRefresh={loadLibrary}
                onDownloadSingle={handleDownloadSingle}
                onBatchDownload={handleBatchDownload}
                onToggleBookmark={handleToggleBookmark}
                onBatchBookmark={handleBatchBookmark}
                onPreview={(v) => setPreviewVideo(v)}
              />
            )}

            {activeSection === 'bookmarks' && (
              <VideoListSection
                title="Kho Video Đã Bookmark"
                subtitle="Quản lý các video tâm đắc theo bộ sưu tập, ghi chú ý tưởng và đồng bộ mục Đã lưu (Collect) từ Douyin."
                videos={bookmarksPage.items}
                total={bookmarksPage.total}
                pageSize={bookmarksPage.page_size}
                targets={targets}
                collections={collections}
                bookmarkOnly
                filters={bookmarkFilters}
                onFiltersChange={setBookmarkFilters}
                onRefresh={loadBookmarks}
                onDownloadSingle={handleDownloadSingle}
                onBatchDownload={handleBatchDownload}
                onToggleBookmark={handleToggleBookmark}
                onBatchBookmark={handleBatchBookmark}
                onPreview={(v) => setPreviewVideo(v)}
                onSyncDouyinCollect={handleSyncDouyinCollect}
              />
            )}

            {activeSection === 'single-crawl' && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight">
                    Crawl theo ID / Link Chia Sẻ Douyin
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    Nhập mã aweme_id, link video/note đầy đủ hoặc dán nguyên đoạn văn bản chia sẻ chứa link rút gọn v.douyin.com.
                  </p>
                </div>

                <div className="grid gap-6 lg:grid-cols-12">
                  <Card className="lg:col-span-7">
                    <CardHeader>
                      <CardTitle className="text-base">Nhập danh sách ID hoặc Link</CardTitle>
                      <CardDescription>
                        Hỗ trợ nhập 1 hoặc nhiều dòng (mỗi dòng 1 mã ID hoặc 1 đoạn link chia sẻ từ app Douyin)
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <form className="space-y-4" onSubmit={(e) => void handleSubmitSingleCrawl(e)}>
                        <div className="space-y-2">
                          <Label>Danh sách aweme_id / URL / Văn bản chia sẻ</Label>
                          <Textarea
                            rows={6}
                            placeholder={
                              'Ví dụ:\n7345678901234567890\nhttps://www.douyin.com/video/7345678901234567891\n4.89 复制打开抖音，看看【作品】https://v.douyin.com/iYAbCdE/'
                            }
                            value={singleInputsText}
                            onChange={(e) => setSingleInputsText(e.target.value)}
                            required
                          />
                        </div>

                        <div className="grid gap-4 sm:grid-cols-2 rounded-xl border p-3.5 bg-muted/30">
                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <div className="text-xs font-semibold">
                                Tự động tải Video/Album không logo
                              </div>
                              <div className="text-[11px] text-muted-foreground">
                                Tải luôn file .mp4 về máy ngay sau khi lấy metadata
                              </div>
                            </div>
                            <Switch
                              checked={singleAutoDownload}
                              onCheckedChange={setSingleAutoDownload}
                            />
                          </div>

                          <div className="flex items-center justify-between gap-2">
                            <div>
                              <div className="text-xs font-semibold">Tự động gắn Bookmark</div>
                              <div className="text-[11px] text-muted-foreground">
                                Lưu thẳng vào danh sách Đã Bookmark
                              </div>
                            </div>
                            <Switch
                              checked={singleBookmark}
                              onCheckedChange={setSingleBookmark}
                            />
                          </div>
                        </div>

                        {singleBookmark && (
                          <div className="space-y-1.5">
                            <Label className="text-xs">Nhãn bộ sưu tập Bookmark (tuỳ chọn)</Label>
                            <Input
                              placeholder="Ví dụ: Crawl lẻ, Tham khảo..."
                              value={singleCollection}
                              onChange={(e) => setSingleCollection(e.target.value)}
                            />
                          </div>
                        )}

                        <div className="rounded-xl border p-3.5 space-y-3">
                          <Label className="text-xs font-semibold">Thời điểm thực thi</Label>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant={singleScheduleMode === 'NOW' ? 'default' : 'outline'}
                              onClick={() => setSingleScheduleMode('NOW')}
                            >
                              <Zap className="size-3.5 mr-1.5" /> Chạy quét ngay lập tức
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant={singleScheduleMode === 'ONCE' ? 'default' : 'outline'}
                              onClick={() => setSingleScheduleMode('ONCE')}
                            >
                              <Clock className="size-3.5 mr-1.5" /> Hẹn giờ chạy 1 lần
                            </Button>
                          </div>
                          {singleScheduleMode === 'ONCE' && (
                            <div className="pt-2 space-y-1">
                              <Label className="text-xs">Chọn ngày giờ chạy</Label>
                              <Input
                                type="datetime-local"
                                value={singleRunAt}
                                onChange={(e) => setSingleRunAt(e.target.value)}
                                required
                              />
                            </div>
                          )}
                        </div>

                        {singleStatusMessage && (
                          <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300 flex items-center gap-2">
                            <CheckCircle2 className="size-4 shrink-0" />
                            <span>{singleStatusMessage}</span>
                          </div>
                        )}

                        <Button type="submit" className="w-full">
                          {singleScheduleMode === 'ONCE'
                            ? 'Lên lịch Crawl theo ID / Link'
                            : 'Bắt đầu Crawl ngay'}
                        </Button>
                      </form>
                    </CardContent>
                  </Card>

                  <Card className="lg:col-span-5">
                    <CardHeader>
                      <CardTitle className="text-base">Lịch sử Crawl lẻ gần đây</CardTitle>
                      <CardDescription>
                        Theo dõi tiến trình các lệnh Crawl 1 ID / Link
                      </CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-2.5">
                      {logsPage.items
                        .filter((l) => l.job_type === 'SINGLE_CRAWL')
                        .slice(0, 8)
                        .map((log) => (
                          <div
                            key={log.id}
                            className="rounded-xl border p-3 text-xs space-y-1.5"
                          >
                            <div className="flex items-center justify-between">
                              <span className="font-mono font-semibold truncate max-w-[200px]">
                                {log.input_summary || `Phiên #${log.id}`}
                              </span>
                              <Badge
                                variant={
                                  log.status === 'SUCCESS'
                                    ? 'default'
                                    : log.status === 'SCHEDULED'
                                      ? 'secondary'
                                      : log.status === 'RUNNING'
                                        ? 'outline'
                                        : 'destructive'
                                }
                              >
                                {log.status}
                              </Badge>
                            </div>
                            <div className="text-muted-foreground flex justify-between">
                              <span>{formatDateTime(log.started_at)}</span>
                              <span>
                                +{log.new_videos_count} mới / {log.updated_videos_count} cập nhật
                              </span>
                            </div>
                            {log.error_message && (
                              <div className="text-rose-400 text-[11px]">{log.error_message}</div>
                            )}
                          </div>
                        ))}
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'targets' && (
              <div className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight">
                      Mục tiêu Quét & Thiết lập Hẹn Giờ
                    </h1>
                    <p className="text-sm text-muted-foreground">
                      Quản lý Kênh (CHANNEL), Từ khóa (KEYWORD), và Đã lưu Douyin (COLLECT) với bộ chọn lịch trực quan.
                    </p>
                  </div>
                  <Button onClick={openCreateTargetModal}>
                    <Plus className="size-4 mr-1.5" /> Thêm Mục tiêu & Lịch mới
                  </Button>
                </div>

                <Card>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Tên mục tiêu</TableHead>
                          <TableHead>Loại & Giá trị</TableHead>
                          <TableHead>Chế độ Hẹn giờ</TableHead>
                          <TableHead>Chạy tiếp theo (Next Run)</TableHead>
                          <TableHead>Lần chạy cuối</TableHead>
                          <TableHead>Tự tải Video</TableHead>
                          <TableHead>Trạng thái</TableHead>
                          <TableHead className="text-right">Thao tác</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {targets.map((target) => (
                          <TableRow key={target.id}>
                            <TableCell className="font-semibold">
                              <div>{target.name}</div>
                              <div className="text-[11px] text-muted-foreground">
                                Tối đa {target.max_items_per_run} bài/lần
                              </div>
                            </TableCell>
                            <TableCell className="text-xs">
                              <Badge variant="outline" className="mr-1.5">
                                {target.target_type}
                              </Badge>
                              <code className="text-[11px] text-muted-foreground truncate max-w-[180px] inline-block align-bottom">
                                {target.target_value}
                              </code>
                            </TableCell>
                            <TableCell className="text-xs">
                              <Badge variant="secondary">{describeSchedule(target)}</Badge>
                            </TableCell>
                            <TableCell className="text-xs font-medium text-cyan-400">
                              {target.is_active && target.next_run_at
                                ? formatDateTime(target.next_run_at)
                                : 'Tạm tắt / Thủ công'}
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {formatDateTime(target.last_run_at)}
                            </TableCell>
                            <TableCell>
                              <Badge variant={target.auto_download ? 'default' : 'outline'}>
                                {target.auto_download ? 'Tự tải .mp4' : 'Chỉ Cover'}
                              </Badge>
                            </TableCell>
                            <TableCell>
                              <Badge
                                variant={
                                  target.last_status === 'SUCCESS'
                                    ? 'default'
                                    : target.last_status === 'FAILED'
                                      ? 'destructive'
                                      : 'secondary'
                                }
                              >
                                {target.last_status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right space-x-1">
                              <Button
                                size="sm"
                                variant="default"
                                className="h-7 text-xs"
                                onClick={() => void handleRunTargetNow(target.id)}
                              >
                                <Play className="size-3 mr-1" /> Chạy ngay
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="h-7 text-xs"
                                onClick={() => openEditTargetModal(target)}
                              >
                                <Edit3 className="size-3 mr-1" /> Sửa
                              </Button>
                              <Button
                                size="sm"
                                variant="ghost"
                                className="h-7 text-xs"
                                onClick={() => void handleToggleTargetActive(target)}
                              >
                                {target.is_active ? 'Tắt lịch' : 'Bật lịch'}
                              </Button>
                              <Button
                                size="icon"
                                variant="ghost"
                                className="size-7 text-rose-400"
                                onClick={() => void handleDeleteTarget(target.id)}
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        {targets.length === 0 && (
                          <TableRow>
                            <TableCell colSpan={8} className="py-12 text-center text-muted-foreground">
                              Chưa có mục tiêu nào. Bấm "Thêm Mục tiêu & Lịch mới" để bắt đầu.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeSection === 'history' && (
              <div className="space-y-6">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-2xl font-bold tracking-tight">
                      Lịch sử Chạy Chi Tiết (Execution History)
                    </h1>
                    <p className="text-sm text-muted-foreground">
                      Theo dõi toàn bộ các phiên quét theo lịch, quét thủ công, Crawl 1 ID, thời lượng chạy và chạy lại khi lỗi.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => void loadLogs()}>
                      <RefreshCw className="size-3.5 mr-1.5" /> Làm mới
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => void handleClearCompletedLogs()}
                    >
                      <Trash2 className="size-3.5 mr-1.5" /> Dọn lịch sử đã xong
                    </Button>
                  </div>
                </div>

                <Card>
                  <CardContent className="p-4 flex flex-wrap items-center gap-3">
                    <select
                      className="h-9 rounded-md border bg-background px-3 text-sm"
                      value={logJobTypeFilter}
                      onChange={(e) => setLogJobTypeFilter(e.target.value)}
                    >
                      <option value="">Mọi loại tác vụ</option>
                      <option value="TARGET_CRAWL">Quét Mục tiêu (Kênh/Từ khóa/Collect)</option>
                      <option value="SINGLE_CRAWL">Crawl lẻ theo ID / Link</option>
                    </select>
                    <select
                      className="h-9 rounded-md border bg-background px-3 text-sm"
                      value={logStatusFilter}
                      onChange={(e) => setLogStatusFilter(e.target.value)}
                    >
                      <option value="">Mọi trạng thái</option>
                      <option value="RUNNING">Đang chạy (RUNNING)</option>
                      <option value="SCHEDULED">Đã hẹn giờ (SCHEDULED)</option>
                      <option value="SUCCESS">Thành công (SUCCESS)</option>
                      <option value="FAILED">Thất bại (FAILED)</option>
                      <option value="CAPTCHA_BLOCKED">Chặn Captcha (CAPTCHA_BLOCKED)</option>
                    </select>
                    <select
                      className="h-9 rounded-md border bg-background px-3 text-sm"
                      value={logTargetFilter}
                      onChange={(e) => setLogTargetFilter(e.target.value)}
                    >
                      <option value="">Mọi mục tiêu</option>
                      {targets.map((t) => (
                        <option key={t.id} value={t.id}>
                          {t.name}
                        </option>
                      ))}
                    </select>
                    <span className="ml-auto text-xs text-muted-foreground">
                      Tổng cộng: <strong>{logsPage.total}</strong> phiên chạy
                    </span>
                  </CardContent>
                </Card>

                <Card>
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Loại & Nguồn kích hoạt</TableHead>
                          <TableHead>Mục tiêu / Đầu vào</TableHead>
                          <TableHead>Bắt đầu → Kết thúc</TableHead>
                          <TableHead>Thời lượng</TableHead>
                          <TableHead>Kết quả (Mới / Cập nhật)</TableHead>
                          <TableHead>Trạng thái & Lỗi</TableHead>
                          <TableHead className="text-right">Thao tác</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {logsPage.items.map((log) => (
                          <TableRow key={log.id}>
                            <TableCell className="font-mono text-xs">#{log.id}</TableCell>
                            <TableCell className="text-xs">
                              <Badge variant="outline" className="mr-1">
                                {log.job_type}
                              </Badge>
                              <Badge variant="secondary" className="text-[10px]">
                                {log.trigger_type}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-xs font-medium max-w-[220px] truncate">
                              {log.target_name || log.input_summary || '—'}
                            </TableCell>
                            <TableCell className="text-xs">
                              <div>{formatDateTime(log.started_at)}</div>
                              <div className="text-[11px] text-muted-foreground">
                                → {log.finished_at ? formatDateTime(log.finished_at) : 'Đang chạy'}
                              </div>
                            </TableCell>
                            <TableCell className="text-xs font-mono">
                              {formatExecutionDuration(log.duration_ms)}
                            </TableCell>
                            <TableCell className="text-xs">
                              <span className="text-emerald-400 font-semibold">
                                +{log.new_videos_count} mới
                              </span>{' '}
                              · <span>{log.updated_videos_count} cập nhật</span>
                            </TableCell>
                            <TableCell className="max-w-[220px]">
                              <Badge
                                variant={
                                  log.status === 'SUCCESS'
                                    ? 'default'
                                    : log.status === 'RUNNING' || log.status === 'SCHEDULED'
                                      ? 'secondary'
                                      : 'destructive'
                                }
                              >
                                {log.status}
                              </Badge>
                              {log.error_message && (
                                <p className="text-[11px] text-rose-400 mt-1 line-clamp-2">
                                  {log.error_message}
                                </p>
                              )}
                            </TableCell>
                            <TableCell className="text-right space-x-1">
                              {(log.status === 'FAILED' ||
                                log.status === 'CAPTCHA_BLOCKED' ||
                                log.status === 'SUCCESS') && (
                                <Button
                                  size="sm"
                                  variant="outline"
                                  className="h-7 text-xs"
                                  onClick={() => void handleRetryLog(log.id)}
                                >
                                  <RotateCcw className="size-3 mr-1" /> Chạy lại
                                </Button>
                              )}
                              <Button
                                size="icon"
                                variant="ghost"
                                className="size-7 text-rose-400"
                                onClick={() => void handleDeleteLog(log.id)}
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        {logsPage.items.length === 0 && (
                          <TableRow>
                            <TableCell colSpan={8} className="py-12 text-center text-muted-foreground">
                              Không có bản ghi lịch sử nào.
                            </TableCell>
                          </TableRow>
                        )}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeSection === 'anti-bot' && antiBot && (
              <div className="space-y-6">
                <div>
                  <h1 className="text-2xl font-bold tracking-tight">
                    Thiết lập Chống Bot (Anti-Bot & Stealth)
                  </h1>
                  <p className="text-sm text-muted-foreground">
                    Giả lập hành vi người dùng thật, tạo độ trễ ngẫu nhiên (Jitter), ẩn dấu vết WebDriver và tự động dừng an toàn khi gặp Captcha.
                  </p>
                </div>

                {/* 3 Preset Cards */}
                <div className="grid gap-4 md:grid-cols-3">
                  {(
                    [
                      {
                        key: 'SAFE',
                        title: '🛡 An Toàn Cao (SAFE)',
                        desc: 'Nghỉ 3.0s–6.5s mỗi nhịp cuộn, Cooldown 25s giữa các kênh. Phù hợp treo máy dài ngày không lo Captcha.',
                      },
                      {
                        key: 'BALANCED',
                        title: '⚖️ Cân Bằng (BALANCED - Khuyên dùng)',
                        desc: 'Nghỉ 1.5s–3.5s mỗi nhịp cuộn, Cooldown 10s, bật Stealth & cuộn tự nhiên như người thật.',
                      },
                      {
                        key: 'FAST',
                        title: '⚡ Tốc Độ Nhanh (FAST)',
                        desc: 'Nghỉ 0.6s–1.4s, tối đa 50 trang/lần. Dành cho quét nhanh số lượng ít.',
                      },
                    ] as const
                  ).map((p) => (
                    <Card
                      key={p.key}
                      onClick={() => void handleApplyPreset(p.key)}
                      className={`cursor-pointer transition ${
                        antiBot.preset === p.key
                          ? 'border-primary ring-2 ring-primary/40'
                          : 'hover:border-primary/40'
                      }`}
                    >
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-base">{p.title}</CardTitle>
                          {antiBot.preset === p.key && <Badge>Đang chọn</Badge>}
                        </div>
                        <CardDescription className="text-xs leading-relaxed">
                          {p.desc}
                        </CardDescription>
                      </CardHeader>
                    </Card>
                  ))}
                </div>

                <Card>
                  <CardHeader>
                    <CardTitle className="text-base">
                      Tuỳ chỉnh Thông số Chống Bot Chi Tiết
                    </CardTitle>
                    <CardDescription>
                      Mọi thay đổi được lưu trực tiếp vào PostgreSQL và áp dụng ngay cho phiên quét kế tiếp.
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form className="space-y-5" onSubmit={(e) => void handleSaveAntiBot(e)}>
                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                        <div className="space-y-1.5">
                          <Label className="text-xs">
                            Độ trễ cuộn trang tối thiểu (ms)
                          </Label>
                          <Input
                            type="number"
                            value={antiBot.scroll_delay_min_ms}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                scroll_delay_min_ms: Number(e.target.value),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">
                            Độ trễ cuộn trang tối đa (ms)
                          </Label>
                          <Input
                            type="number"
                            value={antiBot.scroll_delay_max_ms}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                scroll_delay_max_ms: Number(e.target.value),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">
                            Thời gian nghỉ giữa 2 mục tiêu (giây)
                          </Label>
                          <Input
                            type="number"
                            value={antiBot.cooldown_between_targets_sec}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                cooldown_between_targets_sec: Number(e.target.value),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">Độ trễ tải file tối thiểu (ms)</Label>
                          <Input
                            type="number"
                            value={antiBot.download_delay_min_ms}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                download_delay_min_ms: Number(e.target.value),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">Độ trễ tải file tối đa (ms)</Label>
                          <Input
                            type="number"
                            value={antiBot.download_delay_max_ms}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                download_delay_max_ms: Number(e.target.value),
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">Số lần cuộn tối đa mỗi phiên</Label>
                          <Input
                            type="number"
                            value={antiBot.max_pages_per_run}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                max_pages_per_run: Number(e.target.value),
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-3 rounded-xl border p-4 bg-muted/30">
                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <div className="text-xs font-semibold">Stealth Ẩn WebDriver</div>
                            <div className="text-[11px] text-muted-foreground">
                              Xóa cờ navigator.webdriver của Chromium
                            </div>
                          </div>
                          <Switch
                            checked={antiBot.stealth_mode}
                            onCheckedChange={(v) => setAntiBot({ ...antiBot, stealth_mode: v })}
                          />
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <div className="text-xs font-semibold">Cuộn trang như người thật</div>
                            <div className="text-[11px] text-muted-foreground">
                              Chia nhịp cuộn ngẫu nhiên thay vì nhảy cứng
                            </div>
                          </div>
                          <Switch
                            checked={antiBot.human_scroll}
                            onCheckedChange={(v) => setAntiBot({ ...antiBot, human_scroll: v })}
                          />
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <div>
                            <div className="text-xs font-semibold">
                              Tự dừng khi gặp Captcha
                            </div>
                            <div className="text-[11px] text-muted-foreground">
                              Dừng quét ngay và báo cảnh báo lên Dashboard
                            </div>
                          </div>
                          <Switch
                            checked={antiBot.auto_stop_on_captcha}
                            onCheckedChange={(v) =>
                              setAntiBot({ ...antiBot, auto_stop_on_captcha: v })
                            }
                          />
                        </div>
                      </div>

                      <div className="grid gap-4 sm:grid-cols-2">
                        <div className="space-y-1.5">
                          <Label className="text-xs">Proxy URL (HTTP / SOCKS5 - Tuỳ chọn)</Label>
                          <Input
                            placeholder="Ví dụ: http://127.0.0.1:7890 hoặc để trống"
                            value={antiBot.proxy_url || ''}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                proxy_url: e.target.value || null,
                              })
                            }
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label className="text-xs">Custom User-Agent (Tuỳ chọn)</Label>
                          <Input
                            placeholder="Để trống để dùng User-Agent chuẩn của Chromium Profile"
                            value={antiBot.user_agent || ''}
                            onChange={(e) =>
                              setAntiBot({
                                ...antiBot,
                                user_agent: e.target.value || null,
                              })
                            }
                          />
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-2">
                        {antiBotSavedNotice ? (
                          <span className="text-xs text-emerald-400 flex items-center gap-1.5">
                            <CheckCircle2 className="size-4" /> Đã lưu cấu hình Chống Bot thành công!
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Cập nhật lần cuối: {formatDateTime(antiBot.updated_at)}
                          </span>
                        )}
                        <Button type="submit">Lưu Cấu hình Chống Bot</Button>
                      </div>
                    </form>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Modal Xem Trước Video / Album & Chỉnh sửa Bookmark */}
      <VideoPreviewDialog
        video={previewVideo}
        open={previewVideo !== null}
        onOpenChange={(open) => {
          if (!open) setPreviewVideo(null)
        }}
        onDownload={handleDownloadSingle}
        onSaveBookmark={handleSaveBookmarkDetail}
      />

      {/* Modal Thêm / Sửa Mục tiêu & Bộ chọn Lịch Hẹn Giờ Trực Quan */}
      <Dialog open={targetModalOpen} onOpenChange={setTargetModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {targetForm.id === null
                ? 'Thêm Mục tiêu Quét & Thiết lập Hẹn Giờ'
                : `Chỉnh sửa Mục tiêu #${targetForm.id}`}
            </DialogTitle>
            <DialogDescription>
              Chọn loại nguồn dữ liệu và thiết lập lịch chạy tự động trực quan.
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4" onSubmit={(e) => void handleSaveTarget(e)}>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Tên hiển thị mục tiêu</Label>
                <Input
                  placeholder="Ví dụ: Kênh Thời trang A"
                  value={targetForm.name}
                  onChange={(e) => setTargetForm({ ...targetForm, name: e.target.value })}
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Loại mục tiêu</Label>
                <select
                  className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                  value={targetForm.target_type}
                  onChange={(e) =>
                    setTargetForm({
                      ...targetForm,
                      target_type: e.target.value as TargetType,
                      target_value:
                        e.target.value === 'COLLECT' ? 'self' : targetForm.target_value,
                    })
                  }
                >
                  <option value="CHANNEL">CHANNEL (Quét Kênh Douyin)</option>
                  <option value="KEYWORD">KEYWORD (Quét Từ khóa xu hướng)</option>
                  <option value="COLLECT">COLLECT (Đồng bộ mục Đã lưu trên Douyin)</option>
                </select>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5 sm:col-span-2">
                <Label className="text-xs">
                  {targetForm.target_type === 'CHANNEL'
                    ? 'Link kênh hoặc mã sec_uid'
                    : targetForm.target_type === 'KEYWORD'
                      ? 'Từ khóa tìm kiếm'
                      : 'Tài khoản Douyin (mặc định: self)'}
                </Label>
                <Input
                  placeholder={
                    targetForm.target_type === 'CHANNEL'
                      ? 'https://www.douyin.com/user/MS4wLjABAAAA...'
                      : targetForm.target_type === 'KEYWORD'
                        ? 'Ví dụ: 穿搭 / ẩm thực'
                        : 'self'
                  }
                  value={targetForm.target_value}
                  onChange={(e) =>
                    setTargetForm({ ...targetForm, target_value: e.target.value })
                  }
                  required
                />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Giới hạn bài / phiên</Label>
                <Input
                  type="number"
                  min={1}
                  max={500}
                  value={targetForm.max_items_per_run}
                  onChange={(e) =>
                    setTargetForm({
                      ...targetForm,
                      max_items_per_run: Number(e.target.value),
                    })
                  }
                  required
                />
              </div>
            </div>

            {/* Bộ chọn Lịch Hẹn Giờ Trực Quan (Visual Schedule Picker) */}
            <div className="rounded-xl border p-3.5 space-y-3 bg-muted/30">
              <Label className="text-xs font-semibold">Chế độ Hẹn Giờ (Schedule Mode)</Label>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5">
                {(
                  [
                    { id: 'INTERVAL', label: 'Chu kỳ lặp' },
                    { id: 'DAILY', label: 'Giờ cố định' },
                    { id: 'ONCE', label: 'Chạy 1 lần' },
                    { id: 'CRON', label: 'Cron nâng cao' },
                    { id: 'MANUAL', label: 'Thủ công' },
                  ] as const
                ).map((mode) => (
                  <Button
                    key={mode.id}
                    type="button"
                    size="sm"
                    variant={targetForm.schedule_type === mode.id ? 'default' : 'outline'}
                    className="text-xs h-8"
                    onClick={() => setTargetForm({ ...targetForm, schedule_type: mode.id })}
                  >
                    {mode.label}
                  </Button>
                ))}
              </div>

              {targetForm.schedule_type === 'INTERVAL' && (
                <div className="grid grid-cols-2 gap-3 pt-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Mỗi khoảng</Label>
                    <Input
                      type="number"
                      min={1}
                      value={targetForm.interval_every}
                      onChange={(e) =>
                        setTargetForm({
                          ...targetForm,
                          interval_every: Number(e.target.value),
                        })
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Đơn vị thời gian</Label>
                    <select
                      className="h-9 w-full rounded-md border bg-background px-3 text-sm"
                      value={targetForm.interval_unit}
                      onChange={(e) =>
                        setTargetForm({
                          ...targetForm,
                          interval_unit: e.target.value as 'minutes' | 'hours',
                        })
                      }
                    >
                      <option value="minutes">Phút (Minutes)</option>
                      <option value="hours">Giờ (Hours)</option>
                    </select>
                  </div>
                </div>
              )}

              {targetForm.schedule_type === 'DAILY' && (
                <div className="grid grid-cols-3 gap-3 pt-2">
                  <div className="space-y-1">
                    <Label className="text-xs">Giờ (0–23)</Label>
                    <Input
                      type="number"
                      min={0}
                      max={23}
                      value={targetForm.daily_hour}
                      onChange={(e) =>
                        setTargetForm({
                          ...targetForm,
                          daily_hour: Number(e.target.value),
                        })
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Phút (0–59)</Label>
                    <Input
                      type="number"
                      min={0}
                      max={59}
                      value={targetForm.daily_minute}
                      onChange={(e) =>
                        setTargetForm({
                          ...targetForm,
                          daily_minute: Number(e.target.value),
                        })
                      }
                    />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs">Thứ trong tuần</Label>
                    <Input
                      placeholder="* hoặc mon,wed,fri"
                      value={targetForm.daily_days}
                      onChange={(e) =>
                        setTargetForm({ ...targetForm, daily_days: e.target.value })
                      }
                    />
                  </div>
                </div>
              )}

              {targetForm.schedule_type === 'ONCE' && (
                <div className="pt-2 space-y-1">
                  <Label className="text-xs">Thời điểm chạy 1 lần duy nhất</Label>
                  <Input
                    type="datetime-local"
                    value={targetForm.once_run_at}
                    onChange={(e) =>
                      setTargetForm({ ...targetForm, once_run_at: e.target.value })
                    }
                    required
                  />
                </div>
              )}

              {targetForm.schedule_type === 'CRON' && (
                <div className="pt-2 space-y-1">
                  <Label className="text-xs">Biểu thức Cron 5 trường</Label>
                  <Input
                    placeholder="0 */6 * * *"
                    value={targetForm.cron_expr}
                    onChange={(e) =>
                      setTargetForm({ ...targetForm, cron_expr: e.target.value })
                    }
                    required
                  />
                </div>
              )}
            </div>

            <div className="grid gap-3 sm:grid-cols-2 rounded-xl border p-3">
              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-semibold">Tự động tải luôn Video/Album</div>
                  <div className="text-[11px] text-muted-foreground">
                    Có bài mới là tải sẵn file .mp4 không logo
                  </div>
                </div>
                <Switch
                  checked={targetForm.auto_download}
                  onCheckedChange={(v) => setTargetForm({ ...targetForm, auto_download: v })}
                />
              </div>

              <div className="flex items-center justify-between gap-2">
                <div>
                  <div className="text-xs font-semibold">Kích hoạt lịch ngay</div>
                  <div className="text-[11px] text-muted-foreground">
                    Tự động đưa vào bộ lập lịch
                  </div>
                </div>
                <Switch
                  checked={targetForm.is_active}
                  onCheckedChange={(v) => setTargetForm({ ...targetForm, is_active: v })}
                />
              </div>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setTargetModalOpen(false)}
              >
                Hủy
              </Button>
              <Button type="submit">
                {targetForm.id === null ? 'Tạo mục tiêu' : 'Lưu thay đổi'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
