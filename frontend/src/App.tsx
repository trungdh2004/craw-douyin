import { useCallback, useEffect, useState } from 'react'
import {
  AlertTriangle,
  Bookmark,
  CalendarClock,
  CheckCircle2,
  Clock,
  ExternalLink,
  Film,
  History,
  KeyRound,
  LayoutDashboard,
  Link2,
  Lock,
  LogOut,
  Plus,
  RefreshCw,
  RotateCcw,
  Send,
  Server,
  ShieldCheck,
  Terminal,
  Trash2,
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
import { BrandLogo } from '@/components/BrandLogo'
import { LiveTerminalDrawer } from '@/components/LiveTerminalDrawer'
import {
  type VideoFilterState,
  VideoListSection,
} from '@/components/VideoListSection'
import { VideoPreviewDialog } from '@/components/VideoPreviewDialog'
import {
  type AntiBotSettings,
  type AuthStatusResponse,
  type BookmarkCollection,
  type BrowserStatus,
  type CrawlLogPage,
  type CrawlTargetItem,
  type EditStudioConfig,
  type LoginResponse,
  type OverviewStats,
  type PresetName,
  type ScheduleType,
  type SchedulerStatus,
  type SendToEditResponse,
  type SuggestedTopicItem,
  type TargetType,
  type TrendsResponse,
  type VideoItem,
  type VideoPage,
  apiFetch,
  clearSessionToken,
  describeSchedule,
  formatDateTime,
  formatDurationMs,
  formatExecutionDuration,
  formatNumber,
  getSessionToken,
  setSessionToken,
} from '@/lib/api'

type NavSection =
  | 'overview'
  | 'library'
  | 'bookmarks'
  | 'analyzed'
  | 'single-crawl'
  | 'targets'
  | 'history'
  | 'studio-settings'
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
  is_bookmarked: '',
  is_analyzed: '',
  edit_status: '',
  date_from: '',
  date_to: '',
  min_digg: '',
  min_duration_sec: '',
  max_duration_sec: '',
  bookmark_collection: '',
  sort: 'crawled_at',
  order: 'desc',
  page: 1,
}

const DEFAULT_ANALYZED_FILTERS: VideoFilterState = {
  ...DEFAULT_VIDEO_FILTERS,
  sort: 'edit_sent_at',
}

export function App() {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(true)
  const [adminUsername, setAdminUsername] = useState<string>('admin')
  const [loginUsername, setLoginUsername] = useState<string>('admin')
  const [loginPassword, setLoginPassword] = useState<string>('')
  const [loginError, setLoginError] = useState<string | null>(null)
  const [loginLoading, setLoginLoading] = useState<boolean>(false)

  const [pwCurrent, setPwCurrent] = useState<string>('')
  const [pwNewUsername, setPwNewUsername] = useState<string>('admin')
  const [pwNewPassword, setPwNewPassword] = useState<string>('')
  const [pwNotice, setPwNotice] = useState<string | null>(null)
  const [pwError, setPwError] = useState<string | null>(null)

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
  const [analyzedPage, setAnalyzedPage] = useState<VideoPage>({
    items: [],
    total: 0,
    page: 1,
    page_size: 24,
  })
  const [collections, setCollections] = useState<BookmarkCollection[]>([])
  const [trends, setTrends] = useState<TrendsResponse | null>(null)
  const [libraryFilters, setLibraryFilters] = useState<VideoFilterState>(DEFAULT_VIDEO_FILTERS)
  const [bookmarkFilters, setBookmarkFilters] = useState<VideoFilterState>(DEFAULT_VIDEO_FILTERS)
  const [analyzedFilters, setAnalyzedFilters] = useState<VideoFilterState>(DEFAULT_ANALYZED_FILTERS)
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
  const [terminalOpen, setTerminalOpen] = useState(false)
  const [terminalMinimized, setTerminalMinimized] = useState(false)
  const [selectedTerminalLogId, setSelectedTerminalLogId] = useState<number | null>(null)

  const openLogTerminal = (logId?: number | null) => {
    if (logId !== undefined && logId !== null) {
      setSelectedTerminalLogId(logId)
    }
    setTerminalOpen(true)
    setTerminalMinimized(false)
  }

  // Anti-bot & Studio Settings state
  const [antiBot, setAntiBot] = useState<AntiBotSettings | null>(null)
  const [antiBotSavedNotice, setAntiBotSavedNotice] = useState(false)
  const [studioHost, setStudioHost] = useState('127.0.0.1')
  const [studioPort, setStudioPort] = useState(8000)
  const [studioSavedNotice, setStudioSavedNotice] = useState(false)
  const [confirmDialog, setConfirmDialog] = useState<{
    title: string
    description: string
    confirmLabel?: string
    onConfirm: () => Promise<void>
  } | null>(null)
  const [sendingEditIds, setSendingEditIds] = useState<string[]>([])
  const [editStudioBanner, setEditStudioBanner] = useState<{
    status: 'sending' | 'success' | 'error'
    message: string
    studioUrl?: string
  } | null>(null)

  const editStudioBaseUrl = `http://${studioHost.trim() || '127.0.0.1'}:${studioPort || 8000}`

  const buildVideoQuery = (
    filters: VideoFilterState,
    options?: { forceBookmark?: boolean; forceAnalyzed?: boolean },
  ): string => {
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
    if (options?.forceBookmark) {
      params.set('is_bookmarked', 'true')
    } else if (filters.is_bookmarked !== '') {
      params.set('is_bookmarked', filters.is_bookmarked)
    }
    if (options?.forceAnalyzed) {
      params.set('is_analyzed', 'true')
    } else if (filters.is_analyzed) {
      params.set('is_analyzed', filters.is_analyzed)
    }
    if (filters.edit_status) {
      params.set('edit_status', filters.edit_status)
    }
    if (filters.date_from) {
      params.set('date_from', new Date(filters.date_from).toISOString())
    }
    if (filters.date_to) {
      params.set('date_to', new Date(filters.date_to).toISOString())
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
      const [browserRes, schedRes, statsRes, targetsRes, trendsRes] = await Promise.all([
        apiFetch<{ status: BrowserStatus }>('/api/browser/status'),
        apiFetch<SchedulerStatus>('/api/scheduler/status'),
        apiFetch<OverviewStats>('/api/stats'),
        apiFetch<CrawlTargetItem[]>('/api/targets'),
        apiFetch<TrendsResponse>('/api/trends').catch(() => null),
      ])
      setBrowserStatus(browserRes.status)
      setSchedulerStatus(schedRes)
      setStats(statsRes)
      setTargets(targetsRes)
      if (trendsRes) {
        setTrends(trendsRes)
      }
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
      const q = buildVideoQuery(bookmarkFilters, { forceBookmark: true })
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

  const loadAnalyzed = useCallback(async () => {
    try {
      const q = buildVideoQuery(analyzedFilters, { forceAnalyzed: true })
      const data = await apiFetch<VideoPage>(`/api/videos?${q}`)
      setAnalyzedPage(data)
    } catch {
      // ignore
    }
  }, [analyzedFilters])

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
      if (data.edit_studio_host) setStudioHost(data.edit_studio_host)
      if (data.edit_studio_port) setStudioPort(data.edit_studio_port)
    } catch {
      // ignore
    }
  }, [])

  const checkAuthStatus = useCallback(async () => {
    try {
      const res = await apiFetch<AuthStatusResponse>('/api/auth/status')
      if (res.authenticated === false) {
        clearSessionToken()
        setIsAuthenticated(false)
        return
      }
      if (res.authenticated === true) {
        // Strict session-only guard: if tab was closed and reopened without sessionStorage token, require login
        if (!getSessionToken()) {
          await apiFetch('/api/auth/logout', { method: 'POST' }).catch(() => null)
          setIsAuthenticated(false)
          return
        }
        setIsAuthenticated(true)
        if (res.username) {
          setAdminUsername(res.username)
          setPwNewUsername(res.username)
        }
      }
    } catch {
      setIsAuthenticated(false)
    }
  }, [])

  useEffect(() => {
    void checkAuthStatus()
    const onUnauthorized = () => {
      setIsAuthenticated(false)
    }
    window.addEventListener('douyin:unauthorized', onUnauthorized)
    return () => window.removeEventListener('douyin:unauthorized', onUnauthorized)
  }, [checkAuthStatus])

  const handleAdminLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoginError(null)
    setLoginLoading(true)
    try {
      const res = await apiFetch<LoginResponse>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({
          username: loginUsername.trim(),
          password: loginPassword,
        }),
      })
      setSessionToken(res.token)
      setAdminUsername(res.username)
      setPwNewUsername(res.username)
      setLoginPassword('')
      setIsAuthenticated(true)
      await Promise.all([
        refreshCoreStatus(),
        loadLibrary(),
        loadBookmarks(),
        loadAnalyzed(),
        loadLogs(),
        loadAntiBot(),
      ])
    } catch (err) {
      setLoginError(
        err instanceof Error ? err.message : 'Sai tên đăng nhập hoặc mật khẩu',
      )
    } finally {
      setLoginLoading(false)
    }
  }

  const handleAdminLogout = async () => {
    clearSessionToken()
    await apiFetch('/api/auth/logout', { method: 'POST' }).catch(() => null)
    setIsAuthenticated(false)
    setLoginPassword('')
  }

  const handleChangeAdminPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwError(null)
    setPwNotice(null)
    try {
      const res = await apiFetch<LoginResponse>('/api/auth/password', {
        method: 'PUT',
        body: JSON.stringify({
          current_password: pwCurrent,
          new_username: pwNewUsername.trim() || adminUsername,
          new_password: pwNewPassword,
        }),
      })
      setSessionToken(res.token)
      setAdminUsername(res.username)
      setPwNewUsername(res.username)
      setPwCurrent('')
      setPwNewPassword('')
      setPwNotice(`Đã cập nhật thông tin đăng nhập (${res.username})`)
      window.setTimeout(() => setPwNotice(null), 3000)
    } catch (err) {
      setPwError(
        err instanceof Error ? err.message : 'Không thể đổi mật khẩu',
      )
    }
  }

  useEffect(() => {
    void refreshCoreStatus()
    void loadLibrary()
    void loadBookmarks()
    void loadAnalyzed()
    void loadLogs()
    void loadAntiBot()
  }, [refreshCoreStatus, loadLibrary, loadBookmarks, loadAnalyzed, loadLogs, loadAntiBot])

  useEffect(() => {
    void loadLibrary()
    void loadBookmarks()
    void loadAnalyzed()
  }, [stats.total_videos, stats.running_jobs, loadLibrary, loadBookmarks, loadAnalyzed])

  useEffect(() => {
    const isBusy =
      stats.running_jobs > 0 ||
      logsPage.items.some((l) => l.status === 'RUNNING')
    const intervalMs = isBusy ? 1500 : 3000
    const timer = window.setInterval(() => {
      void refreshCoreStatus()
      if (
        isBusy ||
        terminalOpen ||
        activeSection === 'history' ||
        activeSection === 'overview'
      ) {
        void loadLogs()
      }
      if (isBusy) {
        void loadLibrary()
        void loadBookmarks()
      }
    }, intervalMs)
    return () => window.clearInterval(timer)
  }, [
    stats.running_jobs,
    logsPage.items,
    terminalOpen,
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

  const handleSendToEdit = async (awemeIds: string[]) => {
    if (awemeIds.length === 0) return
    setSendingEditIds((prev) => Array.from(new Set([...prev, ...awemeIds])))
    setEditStudioBanner({
      status: 'sending',
      message: `Đang tải file MP4 không logo & đẩy ${awemeIds.length} video sang Edit Studio...`,
    })
    try {
      const res = await apiFetch<SendToEditResponse>('/api/videos/send-to-edit', {
        method: 'POST',
        body: JSON.stringify({
          aweme_ids: awemeIds,
          auto_process: true,
          profile: 'detailed',
        }),
      })
      setEditStudioBanner({
        status: 'success',
        message: `Đã gửi ${res.item_ids.length} video sang Edit Studio để phân tích.`,
        studioUrl: res.studio_url,
      })
      if (previewVideo && awemeIds.includes(previewVideo.aweme_id) && res.item_ids[0]) {
        setPreviewVideo({
          ...previewVideo,
          edit_item_id: res.item_ids[0],
          edit_list_id: res.list_id,
        })
      }
      await Promise.all([loadLibrary(), loadBookmarks(), loadAnalyzed(), refreshCoreStatus()])
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Không thể gửi video sang Edit Studio'
      setEditStudioBanner({
        status: 'error',
        message: `Lỗi gửi sang Edit Studio: ${msg}`,
      })
      await Promise.all([loadLibrary(), loadBookmarks(), loadAnalyzed()])
    } finally {
      setSendingEditIds((prev) => prev.filter((id) => !awemeIds.includes(id)))
    }
  }

  const handleClearEditStatus = async (awemeId: string) => {
    setConfirmDialog({
      title: 'Bỏ khỏi danh sách Đã gửi Phân tích?',
      description: `Bạn có chắc chắn muốn gỡ video #${awemeId} khỏi danh sách đã gửi phân tích không? (Video gốc trong Thư viện vẫn được giữ nguyên).`,
      confirmLabel: 'Xác nhận bỏ',
      onConfirm: async () => {
        await apiFetch(`/api/videos/${awemeId}/edit-status`, {
          method: 'DELETE',
        })
        await Promise.all([loadLibrary(), loadBookmarks(), loadAnalyzed(), refreshCoreStatus()])
      },
    })
  }

  const handleSaveStudioSettings = async (e: React.FormEvent) => {
    e.preventDefault()
    const res = await apiFetch<EditStudioConfig>('/api/settings/edit-studio', {
      method: 'PUT',
      body: JSON.stringify({
        host: studioHost.trim() || '127.0.0.1',
        port: Number(studioPort) || 8000,
      }),
    })
    setStudioHost(res.host)
    setStudioPort(res.port)
    if (antiBot) {
      setAntiBot({
        ...antiBot,
        edit_studio_host: res.host,
        edit_studio_port: res.port,
      })
    }
    setStudioSavedNotice(true)
    window.setTimeout(() => setStudioSavedNotice(false), 2000)
    await Promise.all([loadLibrary(), loadBookmarks(), loadAnalyzed()])
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
        ? `Đã hẹn giờ quét ${res.count} ID/link (#${res.log_id})`
        : `Đang chạy quét ${res.count} ID/link (#${res.log_id})`,
    )
    await Promise.all([refreshCoreStatus(), loadLogs(), loadLibrary()])
    if (res.status !== 'SCHEDULED') {
      openLogTerminal(res.log_id)
    }
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
    openLogTerminal(null)
  }

  const handleQuickCrawlTopic = async (topic: SuggestedTopicItem) => {
    const existing = targets.find(
      (t) => t.target_type === 'KEYWORD' && t.target_value === topic.keyword,
    )
    let targetId = existing?.id
    if (!targetId) {
      const created = await apiFetch<CrawlTargetItem>('/api/targets', {
        method: 'POST',
        body: JSON.stringify({
          name: `Xu hướng: ${topic.label}`,
          target_type: 'KEYWORD',
          target_value: topic.keyword,
          cron_expr: '0 */6 * * *',
          schedule_type: 'INTERVAL',
          schedule_config: { every: 6, unit: 'hours' },
          run_at: null,
          auto_download: false,
          max_items_per_run: 30,
          is_active: true,
        }),
      })
      targetId = created.id
    }
    await apiFetch(`/api/targets/${targetId}/run`, { method: 'POST' })
    await Promise.all([refreshCoreStatus(), loadLogs()])
    openLogTerminal(null)
  }

  const handleToggleTargetActive = async (target: CrawlTargetItem) => {
    await apiFetch(`/api/targets/${target.id}`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: !target.is_active }),
    })
    await refreshCoreStatus()
  }

  const handleDeleteTarget = async (targetId: number) => {
    const targetObj = targets.find((t) => t.id === targetId)
    setConfirmDialog({
      title: 'Xóa mục tiêu quét?',
      description: `Bạn có chắc chắn muốn xóa mục tiêu "${targetObj?.name || `#${targetId}`}"? Các lịch hẹn giờ của mục tiêu này sẽ dừng lại.`,
      confirmLabel: 'Xóa mục tiêu',
      onConfirm: async () => {
        await apiFetch(`/api/targets/${targetId}`, { method: 'DELETE' })
        await refreshCoreStatus()
      },
    })
  }

  const handleRetryLog = async (logId: number) => {
    await apiFetch(`/api/logs/${logId}/retry`, { method: 'POST' })
    await Promise.all([loadLogs(), refreshCoreStatus()])
  }

  const handleDeleteLog = async (logId: number) => {
    setConfirmDialog({
      title: `Xóa bản ghi lịch sử #${logId}?`,
      description: `Bạn có chắc chắn muốn xóa vĩnh viễn bản ghi phiên chạy #${logId} khỏi lịch sử?`,
      confirmLabel: 'Xóa bản ghi',
      onConfirm: async () => {
        await apiFetch(`/api/logs/${logId}`, { method: 'DELETE' })
        await loadLogs()
      },
    })
  }

  const handleClearCompletedLogs = async () => {
    setConfirmDialog({
      title: 'Dọn toàn bộ lịch sử đã hoàn tất?',
      description: 'Tất cả các bản ghi phiên chạy đã kết thúc (Thành công / Thất bại) sẽ bị xóa khỏi danh sách lịch sử.',
      confirmLabel: 'Dọn lịch sử',
      onConfirm: async () => {
        await apiFetch('/api/logs', { method: 'DELETE' })
        await loadLogs()
      },
    })
  }

  const handleToggleHeadless = async (nextHeadless: boolean) => {
    const updated = await apiFetch<AntiBotSettings>('/api/settings/anti-bot', {
      method: 'PUT',
      body: JSON.stringify({ headless_mode: nextHeadless }),
    })
    setAntiBot(updated)
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
    {
      id: 'analyzed',
      label: 'Đã gửi Phân tích',
      icon: Send,
      badge: analyzedPage.total || undefined,
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
      badge: stats.running_jobs > 0 ? stats.running_jobs : undefined,
    },
    { id: 'studio-settings', label: 'Server Phân tích', icon: Server },
    { id: 'anti-bot', label: 'Cấu hình Chống Bot', icon: ShieldCheck },
  ]

  const currentNavTitle =
    navItems.find((item) => item.id === activeSection)?.label || 'Tổng quan'

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen w-screen items-center justify-center bg-background text-foreground p-4">
        <Card className="surface-standard w-full max-w-sm">
          <CardHeader className="space-y-2 pb-3">
            <div className="flex items-center gap-2.5">
              <div className="relative shrink-0">
                <BrandLogo size={34} className="rounded-lg shadow-sm" />
                <span className="absolute -bottom-1 -right-1 flex size-4 items-center justify-center rounded-full bg-card border border-border text-muted-foreground">
                  <Lock className="size-2.5" />
                </span>
              </div>
              <div>
                <CardTitle className="text-base font-semibold tracking-tight">
                  Đăng nhập Quản trị
                </CardTitle>
                <CardDescription className="text-xs">
                  Douyin Crawler & Lưu trữ Nội bộ
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <form className="space-y-3.5" onSubmit={(e) => void handleAdminLogin(e)}>
              <div className="space-y-1.5">
                <Label htmlFor="admin-login-username" className="text-xs">
                  Tên đăng nhập
                </Label>
                <Input
                  id="admin-login-username"
                  aria-label="Tên đăng nhập"
                  autoComplete="username"
                  placeholder="admin"
                  value={loginUsername}
                  onChange={(e) => setLoginUsername(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="admin-login-password" className="text-xs">
                  Mật khẩu
                </Label>
                <Input
                  id="admin-login-password"
                  aria-label="Mật khẩu"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  required
                />
              </div>

              {loginError && (
                <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                  {loginError}
                </div>
              )}

              <Button
                type="submit"
                className="w-full"
                disabled={loginLoading}
              >
                {loginLoading ? 'Đang xác thực...' : 'Đăng nhập hệ thống'}
              </Button>

              <p className="text-[11px] text-muted-foreground text-center pt-1">
                Phiên đăng nhập tự động khóa khi đóng trình duyệt.
              </p>
            </form>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="relative flex h-screen w-screen overflow-hidden bg-background text-foreground p-2.5 gap-2.5">
      {/* =====================================================================
          QUIET LIQUID GLASS SIDEBAR
         ===================================================================== */}
      <aside className="lg-regular w-56 shrink-0 rounded-2xl flex flex-col justify-between z-30">
        <div className="p-3 space-y-4">
          <div className="flex items-center gap-2.5 px-2.5 pt-1">
            <BrandLogo size={30} className="shrink-0 rounded-lg shadow-xs" />
            <div className="min-w-0">
              <div className="font-semibold tracking-tight text-sm leading-tight truncate">
                Douyin Crawler
              </div>
              <div className="text-[11px] text-muted-foreground truncate">
                Quản lý & Lưu trữ
              </div>
            </div>
          </div>

          <nav aria-label="Điều hướng chính" className="space-y-0.5">
            {navItems.map((item) => {
              const Icon = item.icon
              const active = activeSection === item.id
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full min-h-[34px] flex items-center justify-between rounded-lg px-2.5 py-1.5 text-[13px] transition ${
                    active
                      ? 'bg-foreground/[0.08] text-foreground font-medium'
                      : 'text-muted-foreground hover:bg-foreground/[0.04] hover:text-foreground'
                  }`}
                >
                  <span className="flex items-center gap-2.5">
                    <Icon className="size-4 shrink-0 opacity-75" />
                    <span>{item.label}</span>
                  </span>
                  {item.badge !== undefined && (
                    <span className="font-mono tabular-nums text-[11px] text-muted-foreground">
                      {item.badge}
                    </span>
                  )}
                </button>
              )
            })}
          </nav>
        </div>

        {/* Trạng thái phiên gọn nhẹ ở chân Sidebar */}
        <div className="p-3 m-2 rounded-xl border border-border/80 bg-card/50 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-muted-foreground">Phiên Douyin</span>
            <span className="inline-flex items-center gap-1.5 font-medium text-foreground">
              <span
                className={`size-1.5 rounded-full ${
                  browserStatus === 'AUTHENTICATED'
                    ? 'bg-foreground'
                    : browserStatus === 'CAPTCHA_REQUIRED'
                      ? 'bg-destructive'
                      : 'bg-muted-foreground'
                }`}
              />
              {browserStatus === 'AUTHENTICATED'
                ? 'Đã kết nối'
                : browserStatus === 'CAPTCHA_REQUIRED'
                  ? 'Captcha'
                  : 'Chưa đăng nhập'}
            </span>
          </div>
          {antiBot && (
            <div className="flex items-center justify-between text-xs pt-1 border-t border-border/60">
              <span className="text-muted-foreground" title="Bật để chạy ngầm không hiện cửa sổ Chrome khi cào">
                Chạy ẩn (Headless)
              </span>
              <Switch
                aria-label="Chạy ẩn trình duyệt (Headless)"
                checked={Boolean(antiBot.headless_mode)}
                onCheckedChange={(v) => void handleToggleHeadless(v)}
              />
            </div>
          )}
          <Button
            size="xs"
            variant="outline"
            className="w-full"
            disabled={browserStatus === 'LOGIN_IN_PROGRESS'}
            onClick={() => void handleOpenLoginBrowser()}
          >
            {browserStatus === 'CAPTCHA_REQUIRED'
              ? 'Mở trình duyệt giải Captcha'
              : 'Mở trình duyệt đăng nhập'}
          </Button>
          <div className="flex items-center justify-between pt-1.5 border-t border-border/60 text-xs">
            <span className="text-muted-foreground truncate font-mono text-[11px]">
              @{adminUsername}
            </span>
            <Button
              size="xs"
              variant="ghost"
              className="h-6 px-2 text-muted-foreground hover:text-foreground"
              onClick={() => void handleAdminLogout()}
            >
              <LogOut className="size-3 mr-1" />
              Đăng xuất
            </Button>
          </div>
        </div>
      </aside>

      {/* =====================================================================
          MAIN VIEWPORT
         ===================================================================== */}
      <div className="relative flex-1 flex flex-col min-w-0 overflow-hidden rounded-2xl">
        {/* QUIET LIQUID GLASS TOP BAR */}
        <header className="lg-regular absolute top-0 left-0 right-0 z-30 h-12 px-4 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2.5 text-xs">
            <span className="font-semibold text-sm text-foreground">
              {currentNavTitle}
            </span>
            {stats.running_jobs > 0 && (
              <span className="text-muted-foreground font-mono tabular-nums">
                · Đang chạy {stats.running_jobs} tác vụ
              </span>
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              size="xs"
              variant="ghost"
              onClick={() => void handleToggleScheduler()}
            >
              Scheduler: {schedulerStatus.paused ? 'Tạm dừng' : 'Đang bật'}
            </Button>
            <Button
              size="xs"
              variant={terminalOpen ? 'secondary' : 'outline'}
              onClick={() => {
                if (terminalOpen) {
                  setTerminalOpen(false)
                } else {
                  openLogTerminal(selectedTerminalLogId)
                }
              }}
            >
              <Terminal className="size-3.5 mr-1" />
              Nhật ký
            </Button>
            <Button
              size="xs"
              variant="outline"
              onClick={() => {
                void refreshCoreStatus()
                void loadLibrary()
                void loadBookmarks()
                void loadLogs()
              }}
            >
              <RefreshCw className="size-3.5 mr-1" /> Làm mới
            </Button>
          </div>
        </header>

        {/* CONTENT LAYER */}
        <main className="scroll-edge-top flex-1 overflow-y-auto pt-15 pb-8 px-2">
          <div className="mx-auto max-w-6xl space-y-5">
            {browserStatus === 'CAPTCHA_REQUIRED' && (
              <div className="surface-standard border-destructive/30 rounded-xl px-4 py-3 flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs text-destructive">
                  <AlertTriangle className="size-4 shrink-0" />
                  <span>
                    Phát hiện yêu cầu xác thực Captcha từ Douyin. Hãy mở trình duyệt để xác thực.
                  </span>
                </div>
                <Button
                  size="xs"
                  variant="destructive"
                  onClick={() => void handleOpenLoginBrowser()}
                >
                  Giải Captcha
                </Button>
              </div>
            )}

            {editStudioBanner && (
              <div className="surface-standard rounded-xl px-4 py-2.5 flex items-center justify-between text-xs">
                <span>{editStudioBanner.message}</span>
                <div className="flex items-center gap-2">
                  {editStudioBanner.studioUrl && (
                    <Button
                      size="xs"
                      variant="default"
                      onClick={() => window.open(editStudioBanner.studioUrl, '_blank')}
                    >
                      <ExternalLink className="size-3.5 mr-1" />
                      Mở Studio
                    </Button>
                  )}
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => setEditStudioBanner(null)}
                  >
                    Đóng
                  </Button>
                </div>
              </div>
            )}

            {activeSection === 'overview' && (
              <div className="space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-lg font-semibold tracking-tight">
                      Tổng quan Hệ thống Douyin Crawler
                    </h1>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Theo dõi kho video, mục đã lưu và các lịch thu thập tự động.
                    </p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={() => {
                        setActiveSection('targets')
                        openCreateTargetModal()
                      }}
                    >
                      <Plus className="size-3.5 mr-1.5" /> Thêm lịch quét
                    </Button>
                    <Button size="sm" variant="default" onClick={() => setActiveSection('single-crawl')}>
                      <Link2 className="size-3.5 mr-1.5" /> Crawl nhanh 1 ID / Link
                    </Button>
                  </div>
                </div>

                {/* Dải thống kê nhẹ nhàng, đơn sắc */}
                <div className="surface-standard rounded-xl overflow-hidden grid sm:grid-cols-2 lg:grid-cols-4 divide-y sm:divide-y-0 sm:divide-x divide-border">
                  <button
                    type="button"
                    onClick={() => setActiveSection('library')}
                    className="p-4 text-left hover:bg-muted/40 transition space-y-1"
                  >
                    <div className="text-xs text-muted-foreground">Tổng video</div>
                    <div className="font-mono tabular-nums text-2xl font-semibold">
                      {formatNumber(stats.total_videos)}
                    </div>
                    <div className="text-[11px] text-muted-foreground font-mono tabular-nums">
                      Đã tải về: {stats.downloaded_videos}
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveSection('bookmarks')}
                    className="p-4 text-left hover:bg-muted/40 transition space-y-1"
                  >
                    <div className="text-xs text-muted-foreground">Đã Bookmark</div>
                    <div className="font-mono tabular-nums text-2xl font-semibold">
                      {formatNumber(stats.bookmarked_videos)}
                    </div>
                    <div className="text-[11px] text-muted-foreground font-mono tabular-nums">
                      {collections.length} bộ sưu tập
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveSection('targets')}
                    className="p-4 text-left hover:bg-muted/40 transition space-y-1"
                  >
                    <div className="text-xs text-muted-foreground">Lịch hẹn giờ</div>
                    <div className="font-mono tabular-nums text-2xl font-semibold">
                      {stats.active_targets} <span className="text-sm font-normal text-muted-foreground">/ {stats.total_targets}</span>
                    </div>
                    <div className="text-[11px] text-muted-foreground font-mono tabular-nums">
                      {schedulerStatus.jobs_count} tác vụ đang bật
                    </div>
                  </button>

                  <button
                    type="button"
                    onClick={() => setActiveSection('history')}
                    className="p-4 text-left hover:bg-muted/40 transition space-y-1"
                  >
                    <div className="text-xs text-muted-foreground">Phiên hoàn tất</div>
                    <div className="font-mono tabular-nums text-2xl font-semibold">
                      {stats.completed_jobs}
                    </div>
                    <div className="text-[11px] text-muted-foreground font-mono tabular-nums">
                      Lỗi: {stats.failed_jobs} · Đang chạy: {stats.running_jobs}
                    </div>
                  </button>
                </div>

                {/* Từ khóa & Hashtag tối giản */}
                {trends &&
                  ((trends.trending_hashtags?.length ?? 0) > 0 ||
                    (trends.suggested_topics?.length ?? 0) > 0) && (
                    <div className="flex flex-wrap items-center gap-1.5 text-xs">
                      <span className="text-muted-foreground mr-1">Xu hướng:</span>
                      {(trends.trending_hashtags ?? []).slice(0, 8).map((item) => (
                        <button
                          key={item.tag}
                          type="button"
                          onClick={() => {
                            setLibraryFilters({
                              ...libraryFilters,
                              search: item.tag,
                              page: 1,
                            })
                            setActiveSection('library')
                          }}
                          className="inline-flex min-h-[28px] items-center gap-1 rounded-full border border-border bg-card hover:bg-muted px-2.5 py-0.5 text-xs transition"
                        >
                          <span>#{item.tag}</span>
                          <span className="font-mono tabular-nums text-[11px] text-muted-foreground">
                            {item.video_count}
                          </span>
                        </button>
                      ))}
                      {(trends.suggested_topics ?? []).map((topic) => (
                        <button
                          key={topic.keyword}
                          type="button"
                          onClick={() => void handleQuickCrawlTopic(topic)}
                          className="inline-flex min-h-[28px] items-center gap-1 rounded-full border border-border bg-card hover:bg-muted px-2.5 py-0.5 text-xs text-muted-foreground hover:text-foreground transition"
                        >
                          <span>+ {topic.label}</span>
                        </button>
                      ))}
                    </div>
                  )}

                <div className="grid gap-5 lg:grid-cols-12">
                  <Card className="surface-standard lg:col-span-7">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <div>
                        <CardTitle className="text-sm font-semibold">
                          Bài đăng mới thu thập
                        </CardTitle>
                      </div>
                      <Button
                        size="xs"
                        variant="ghost"
                        onClick={() => setActiveSection('library')}
                      >
                        Xem tất cả →
                      </Button>
                    </CardHeader>
                    <CardContent className="divide-y divide-border">
                      {videosPage.items.slice(0, 5).map((v) => (
                        <div
                          key={v.aweme_id}
                          onClick={() => setPreviewVideo(v)}
                          className="flex items-center gap-3 py-2.5 first:pt-0 last:pb-0 hover: opacity-95 cursor-pointer"
                        >
                          <div className="relative h-12 w-20 rounded-md bg-muted overflow-hidden shrink-0">
                            {v.cover_url && (
                              <img
                                src={v.cover_url}
                                alt=""
                                className="h-full w-full object-cover"
                              />
                            )}
                            <span className="lg-clear absolute bottom-1 right-1 rounded px-1 py-0 text-[10px] font-mono tabular-nums">
                              {v.aweme_type === 68
                                ? `${v.image_count} ảnh`
                                : formatDurationMs(v.duration_ms)}
                            </span>
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-xs font-medium">
                              {v.description || v.aweme_id}
                            </p>
                            <div className="text-[11px] text-muted-foreground mt-0.5 font-mono tabular-nums">
                              <span className="font-sans">@{v.author_nickname}</span> ·{' '}
                              {formatDateTime(v.create_time)} · {formatNumber(v.digg_count)} tim
                            </div>
                          </div>
                          <div
                            className="flex items-center gap-1.5 shrink-0"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <span className="text-[11px] text-muted-foreground font-mono">
                              {v.download_status === 'COMPLETED' ? 'Đã tải' : ''}
                            </span>
                          </div>
                        </div>
                      ))}
                      {videosPage.items.length === 0 && (
                        <p className="text-xs text-muted-foreground py-8 text-center">
                          Chưa có video nào được thu thập.
                        </p>
                      )}
                    </CardContent>
                  </Card>

                  <Card className="surface-standard lg:col-span-5">
                    <CardHeader className="flex flex-row items-center justify-between pb-2">
                      <div>
                        <CardTitle className="text-sm font-semibold">Phiên chạy gần đây</CardTitle>
                      </div>
                      <Button
                        size="xs"
                        variant="ghost"
                        onClick={() => setActiveSection('history')}
                      >
                        Chi tiết →
                      </Button>
                    </CardHeader>
                    <CardContent className="divide-y divide-border">
                      {logsPage.items.slice(0, 6).map((log) => (
                        <div
                          key={log.id}
                          className="flex items-center justify-between gap-2 py-2.5 first:pt-0 last:pb-0 text-xs"
                        >
                          <div className="space-y-0.5 min-w-0">
                            <div className="font-medium truncate">
                              {log.target_name || log.input_summary || `Phiên #${log.id}`}
                            </div>
                            <div className="text-muted-foreground font-mono tabular-nums text-[11px]">
                              {formatDateTime(log.started_at)} ·{' '}
                              {formatExecutionDuration(log.duration_ms)} · +{log.new_videos_count}{' '}
                              mới
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <Button
                              size="xs"
                              variant="ghost"
                              onClick={() => openLogTerminal(log.id)}
                            >
                              Log
                            </Button>
                            <Badge variant="outline" className="font-mono text-[10px] font-normal">
                              {log.status}
                            </Badge>
                          </div>
                        </div>
                      ))}
                      {logsPage.items.length === 0 && (
                        <p className="text-xs text-muted-foreground py-8 text-center">
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
                subtitle="Danh sách video và album đã thu thập."
                videos={videosPage.items}
                total={videosPage.total}
                pageSize={videosPage.page_size}
                targets={targets}
                trends={trends}
                editStudioBaseUrl={editStudioBaseUrl}
                filters={libraryFilters}
                onFiltersChange={setLibraryFilters}
                onRefresh={loadLibrary}
                onDownloadSingle={handleDownloadSingle}
                onBatchDownload={handleBatchDownload}
                onToggleBookmark={handleToggleBookmark}
                onBatchBookmark={handleBatchBookmark}
                onPreview={(v) => setPreviewVideo(v)}
                onQuickCrawlTopic={handleQuickCrawlTopic}
                onSendToEdit={handleSendToEdit}
                sendingEditIds={sendingEditIds}
              />
            )}

            {activeSection === 'bookmarks' && (
              <VideoListSection
                title="Kho Video Đã Bookmark"
                subtitle="Các bài đăng đã đánh dấu và đồng bộ từ Douyin."
                videos={bookmarksPage.items}
                total={bookmarksPage.total}
                pageSize={bookmarksPage.page_size}
                targets={targets}
                collections={collections}
                trends={trends}
                bookmarkOnly
                editStudioBaseUrl={editStudioBaseUrl}
                filters={bookmarkFilters}
                onFiltersChange={setBookmarkFilters}
                onRefresh={loadBookmarks}
                onDownloadSingle={handleDownloadSingle}
                onBatchDownload={handleBatchDownload}
                onToggleBookmark={handleToggleBookmark}
                onBatchBookmark={handleBatchBookmark}
                onPreview={(v) => setPreviewVideo(v)}
                onSyncDouyinCollect={handleSyncDouyinCollect}
                onSendToEdit={handleSendToEdit}
                sendingEditIds={sendingEditIds}
              />
            )}

            {activeSection === 'analyzed' && (
              <VideoListSection
                title="Video Đã Đẩy Sang Phân Tích"
                subtitle={`Danh sách các bài đăng đã gửi sang Server Phân tích (${editStudioBaseUrl}).`}
                videos={analyzedPage.items}
                total={analyzedPage.total}
                pageSize={analyzedPage.page_size}
                targets={targets}
                analyzedOnly
                editStudioBaseUrl={editStudioBaseUrl}
                onOpenStudioSettings={() => setActiveSection('studio-settings')}
                onClearEditStatus={handleClearEditStatus}
                filters={analyzedFilters}
                onFiltersChange={setAnalyzedFilters}
                onRefresh={loadAnalyzed}
                onDownloadSingle={handleDownloadSingle}
                onBatchDownload={handleBatchDownload}
                onToggleBookmark={handleToggleBookmark}
                onBatchBookmark={handleBatchBookmark}
                onPreview={(v) => setPreviewVideo(v)}
                onSendToEdit={handleSendToEdit}
                sendingEditIds={sendingEditIds}
              />
            )}

            {activeSection === 'single-crawl' && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-lg font-semibold tracking-tight">
                    Crawl theo ID / Link Chia Sẻ Douyin
                  </h1>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Nhập mã aweme_id, link video/note hoặc dán văn bản chia sẻ từ ứng dụng Douyin.
                  </p>
                </div>

                <div className="grid gap-5 lg:grid-cols-12">
                  <Card className="surface-standard lg:col-span-7">
                    <CardHeader>
                      <CardTitle className="text-sm font-semibold">Danh sách ID hoặc Link</CardTitle>
                      <CardDescription className="text-xs">
                        Mỗi dòng một mã ID hoặc một đường dẫn chia sẻ
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <form className="space-y-4" onSubmit={(e) => void handleSubmitSingleCrawl(e)}>
                        <div className="space-y-1.5">
                          <Textarea
                            rows={6}
                            className="font-mono text-xs"
                            placeholder={
                              '7345678901234567890\nhttps://www.douyin.com/video/7345678901234567891\nhttps://v.douyin.com/iYAbCdE/'
                            }
                            value={singleInputsText}
                            onChange={(e) => setSingleInputsText(e.target.value)}
                            required
                          />
                        </div>

                        <div className="grid gap-4 sm:grid-cols-2 rounded-xl border border-border p-3.5">
                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-medium">Tự động tải file không logo</span>
                            <Switch
                              checked={singleAutoDownload}
                              onCheckedChange={setSingleAutoDownload}
                            />
                          </div>

                          <div className="flex items-center justify-between gap-2">
                            <span className="text-xs font-medium">Tự động gắn Bookmark</span>
                            <Switch
                              checked={singleBookmark}
                              onCheckedChange={setSingleBookmark}
                            />
                          </div>
                        </div>

                        {singleBookmark && (
                          <div className="space-y-1.5">
                            <Label className="text-xs">Nhãn bộ sưu tập (tuỳ chọn)</Label>
                            <Input
                              placeholder="Ví dụ: Tham khảo..."
                              value={singleCollection}
                              onChange={(e) => setSingleCollection(e.target.value)}
                            />
                          </div>
                        )}

                        <div className="rounded-xl border border-border p-3.5 space-y-2.5">
                          <Label className="text-xs font-medium">Thời điểm chạy</Label>
                          <div className="flex flex-wrap gap-2">
                            <Button
                              type="button"
                              size="sm"
                              variant={singleScheduleMode === 'NOW' ? 'default' : 'outline'}
                              onClick={() => setSingleScheduleMode('NOW')}
                            >
                              Chạy ngay
                            </Button>
                            <Button
                              type="button"
                              size="sm"
                              variant={singleScheduleMode === 'ONCE' ? 'default' : 'outline'}
                              onClick={() => setSingleScheduleMode('ONCE')}
                            >
                              <Clock className="size-3.5 mr-1.5" /> Hẹn giờ 1 lần
                            </Button>
                          </div>
                          {singleScheduleMode === 'ONCE' && (
                            <div className="pt-1">
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
                          <div className="rounded-lg border border-border bg-muted px-3 py-2 text-xs flex items-center gap-2">
                            <CheckCircle2 className="size-4 shrink-0" />
                            <span>{singleStatusMessage}</span>
                          </div>
                        )}

                        <Button type="submit" className="w-full">
                          {singleScheduleMode === 'ONCE'
                            ? 'Lên lịch Crawl'
                            : 'Bắt đầu Crawl'}
                        </Button>
                      </form>
                    </CardContent>
                  </Card>

                  <Card className="surface-standard lg:col-span-5">
                    <CardHeader>
                      <CardTitle className="text-sm font-semibold">Lịch sử Crawl lẻ</CardTitle>
                    </CardHeader>
                    <CardContent className="divide-y divide-border">
                      {logsPage.items
                        .filter((l) => l.job_type === 'SINGLE_CRAWL')
                        .slice(0, 8)
                        .map((log) => (
                          <div key={log.id} className="py-2.5 first:pt-0 last:pb-0 text-xs space-y-1">
                            <div className="flex items-center justify-between">
                              <span className="font-mono tabular-nums font-medium truncate max-w-[200px]">
                                {log.input_summary || `Phiên #${log.id}`}
                              </span>
                              <Badge variant="outline" className="font-mono text-[10px] font-normal">
                                {log.status}
                              </Badge>
                            </div>
                            <div className="text-muted-foreground font-mono tabular-nums flex items-center justify-between">
                              <span>{formatDateTime(log.started_at)}</span>
                              <Button
                                size="xs"
                                variant="ghost"
                                onClick={() => openLogTerminal(log.id)}
                              >
                                Xem Log
                              </Button>
                            </div>
                          </div>
                        ))}
                    </CardContent>
                  </Card>
                </div>
              </div>
            )}

            {activeSection === 'targets' && (
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-lg font-semibold tracking-tight">
                      Mục tiêu Quét & Thiết lập Hẹn Giờ
                    </h1>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Quản lý Kênh (CHANNEL), Từ khóa (KEYWORD) và mục Đã lưu (COLLECT).
                    </p>
                  </div>
                  <Button size="sm" onClick={openCreateTargetModal}>
                    <Plus className="size-3.5 mr-1.5" /> Thêm Mục tiêu
                  </Button>
                </div>

                <Card className="surface-standard py-0">
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Tên mục tiêu</TableHead>
                          <TableHead>Loại & Giá trị</TableHead>
                          <TableHead>Lịch chạy</TableHead>
                          <TableHead>Chạy tiếp theo</TableHead>
                          <TableHead>Lần chạy cuối</TableHead>
                          <TableHead>Tự tải</TableHead>
                          <TableHead>Trạng thái</TableHead>
                          <TableHead className="text-right">Thao tác</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {targets.map((target) => (
                          <TableRow key={target.id}>
                            <TableCell className="font-medium text-xs">
                              <div>{target.name}</div>
                              <div className="text-[11px] font-mono tabular-nums text-muted-foreground font-normal">
                                Tối đa {target.max_items_per_run} bài
                              </div>
                            </TableCell>
                            <TableCell className="text-xs">
                              <span className="font-mono text-[11px] text-muted-foreground mr-1.5">
                                [{target.target_type}]
                              </span>
                              <code className="text-[11px] font-mono text-foreground truncate max-w-[160px] inline-block align-bottom">
                                {target.target_value}
                              </code>
                            </TableCell>
                            <TableCell className="text-xs">
                              {describeSchedule(target)}
                            </TableCell>
                            <TableCell className="text-xs font-mono tabular-nums text-muted-foreground">
                              {target.is_active && target.next_run_at
                                ? formatDateTime(target.next_run_at)
                                : 'Tạm tắt'}
                            </TableCell>
                            <TableCell className="text-xs font-mono tabular-nums text-muted-foreground">
                              {formatDateTime(target.last_run_at)}
                            </TableCell>
                            <TableCell className="text-xs text-muted-foreground">
                              {target.auto_download ? 'Có' : 'Không'}
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline" className="font-mono text-[10px] font-normal">
                                {target.last_status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right space-x-1">
                              <Button
                                size="xs"
                                variant="secondary"
                                onClick={() => void handleRunTargetNow(target.id)}
                              >
                                Chạy
                              </Button>
                              <Button
                                size="xs"
                                variant="outline"
                                onClick={() => openEditTargetModal(target)}
                              >
                                Sửa
                              </Button>
                              <Button
                                size="xs"
                                variant="ghost"
                                onClick={() => void handleToggleTargetActive(target)}
                              >
                                {target.is_active ? 'Tắt' : 'Bật'}
                              </Button>
                              <Button
                                size="icon-xs"
                                variant="ghost"
                                aria-label={`Xóa mục tiêu ${target.name}`}
                                onClick={() => void handleDeleteTarget(target.id)}
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                        {targets.length === 0 && (
                          <TableRow>
                            <TableCell colSpan={8} className="py-12 text-center text-muted-foreground text-xs">
                              Chưa có mục tiêu nào.
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
              <div className="space-y-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h1 className="text-lg font-semibold tracking-tight">
                      Lịch sử Chạy Chi Tiết (Execution History)
                    </h1>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Nhật ký các phiên quét tự động và thủ công.
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button variant="outline" size="sm" onClick={() => void loadLogs()}>
                      Làm mới
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => void handleClearCompletedLogs()}
                    >
                      Dọn lịch sử đã xong
                    </Button>
                  </div>
                </div>

                <Card className="surface-standard">
                  <CardContent className="p-3 flex flex-wrap items-center gap-2.5">
                    <select
                      aria-label="Lọc theo loại tác vụ"
                      className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
                      value={logJobTypeFilter}
                      onChange={(e) => setLogJobTypeFilter(e.target.value)}
                    >
                      <option value="">Mọi loại tác vụ</option>
                      <option value="TARGET_CRAWL">Quét Mục tiêu</option>
                      <option value="SINGLE_CRAWL">Crawl lẻ</option>
                      <option value="DOWNLOAD">Tải Media</option>
                    </select>
                    <select
                      aria-label="Lọc theo trạng thái phiên chạy"
                      className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
                      value={logStatusFilter}
                      onChange={(e) => setLogStatusFilter(e.target.value)}
                    >
                      <option value="">Mọi trạng thái</option>
                      <option value="RUNNING">Đang chạy</option>
                      <option value="SUCCESS">Thành công</option>
                      <option value="FAILED">Thất bại</option>
                    </select>
                    <select
                      aria-label="Lọc theo mục tiêu"
                      className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
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
                    <span className="ml-auto text-xs text-muted-foreground font-mono tabular-nums">
                      {logsPage.total} phiên
                    </span>
                  </CardContent>
                </Card>

                <Card className="surface-standard py-0">
                  <CardContent className="p-0">
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>ID</TableHead>
                          <TableHead>Loại</TableHead>
                          <TableHead>Mục tiêu</TableHead>
                          <TableHead>Thời gian</TableHead>
                          <TableHead>Thời lượng</TableHead>
                          <TableHead>Kết quả</TableHead>
                          <TableHead>Trạng thái</TableHead>
                          <TableHead className="text-right">Thao tác</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {logsPage.items.map((log) => (
                          <TableRow key={log.id}>
                            <TableCell className="font-mono tabular-nums text-xs text-muted-foreground">
                              #{log.id}
                            </TableCell>
                            <TableCell className="text-xs font-mono">
                              {log.job_type}
                            </TableCell>
                            <TableCell className="text-xs font-medium max-w-[200px] truncate">
                              {log.target_name || log.input_summary || '—'}
                            </TableCell>
                            <TableCell className="text-xs font-mono tabular-nums text-muted-foreground">
                              {formatDateTime(log.started_at)}
                            </TableCell>
                            <TableCell className="text-xs font-mono tabular-nums">
                              {formatExecutionDuration(log.duration_ms)}
                            </TableCell>
                            <TableCell className="text-xs font-mono tabular-nums">
                              +{log.new_videos_count} mới · {log.updated_videos_count} trùng
                            </TableCell>
                            <TableCell>
                              <Badge variant="outline" className="font-mono text-[10px] font-normal">
                                {log.status}
                              </Badge>
                            </TableCell>
                            <TableCell className="text-right space-x-1">
                              <Button
                                size="xs"
                                variant="ghost"
                                onClick={() => openLogTerminal(log.id)}
                              >
                                Xem Log
                              </Button>
                              {(log.status === 'FAILED' || log.status === 'CAPTCHA_BLOCKED') && (
                                <Button
                                  size="xs"
                                  variant="outline"
                                  onClick={() => void handleRetryLog(log.id)}
                                >
                                  <RotateCcw className="size-3.5 mr-1" /> Chạy lại
                                </Button>
                              )}
                              <Button
                                size="icon-xs"
                                variant="ghost"
                                aria-label={`Xóa bản ghi lịch sử #${log.id}`}
                                onClick={() => void handleDeleteLog(log.id)}
                              >
                                <Trash2 className="size-3.5" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeSection === 'studio-settings' && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-lg font-semibold tracking-tight">
                    Cấu hình Server Phân tích (IP & Port)
                  </h1>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Trỏ tới địa chỉ IP và Port của dịch vụ phân tích / Edit Studio (có thể chạy trên máy này hoặc máy chủ khác trong mạng).
                  </p>
                </div>

                <Card className="surface-standard max-w-2xl">
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold">
                      Địa chỉ kết nối Server Phân tích
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Đường dẫn hiện tại: <code className="font-mono text-foreground">{editStudioBaseUrl}</code>
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form className="space-y-4" onSubmit={(e) => void handleSaveStudioSettings(e)}>
                      <div className="grid gap-4 sm:grid-cols-3 font-mono tabular-nums">
                        <div className="space-y-1.5 sm:col-span-2">
                          <Label htmlFor="studio-host-input" className="font-sans text-xs">
                            Địa chỉ IP hoặc Hostname
                          </Label>
                          <Input
                            id="studio-host-input"
                            aria-label="Địa chỉ IP hoặc Hostname"
                            placeholder="Ví dụ: 192.168.1.50 hoặc 127.0.0.1"
                            value={studioHost}
                            onChange={(e) => setStudioHost(e.target.value)}
                            required
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="studio-port-input" className="font-sans text-xs">
                            Cổng (Port)
                          </Label>
                          <Input
                            id="studio-port-input"
                            aria-label="Cổng (Port)"
                            type="number"
                            min={1}
                            max={65535}
                            placeholder="8000"
                            value={studioPort}
                            onChange={(e) => setStudioPort(Number(e.target.value))}
                            required
                          />
                        </div>
                      </div>

                      <div className="flex flex-wrap items-center gap-2 pt-1">
                        <span className="text-xs text-muted-foreground">Mẫu nhanh:</span>
                        <Button
                          type="button"
                          size="xs"
                          variant="outline"
                          onClick={() => {
                            setStudioHost('127.0.0.1')
                            setStudioPort(8000)
                          }}
                        >
                          Localhost (127.0.0.1:8000)
                        </Button>
                      </div>

                      <div className="flex items-center justify-between pt-2 border-t border-border">
                        {studioSavedNotice ? (
                          <span className="text-xs text-foreground flex items-center gap-1.5">
                            <CheckCircle2 className="size-4" /> Đã lưu địa chỉ {editStudioBaseUrl}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Không bắt buộc kết nối ngầm khi duyệt danh sách video.
                          </span>
                        )}
                        <Button type="submit" size="sm">
                          Lưu địa chỉ Server
                        </Button>
                      </div>
                    </form>
                  </CardContent>
                </Card>

                <Card className="surface-standard max-w-2xl">
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold flex items-center gap-2">
                      <KeyRound className="size-4" />
                      Tài khoản Quản trị (Đổi mật khẩu)
                    </CardTitle>
                    <CardDescription className="text-xs">
                      Đổi tên đăng nhập hoặc mật khẩu bảo vệ hệ thống. Đang đăng nhập: <code className="font-mono text-foreground">{adminUsername}</code>
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <form className="space-y-4" onSubmit={(e) => void handleChangeAdminPassword(e)}>
                      <div className="grid gap-4 sm:grid-cols-3">
                        <div className="space-y-1.5">
                          <Label htmlFor="admin-new-username" className="text-xs">
                            Tên đăng nhập mới
                          </Label>
                          <Input
                            id="admin-new-username"
                            aria-label="Tên đăng nhập mới"
                            value={pwNewUsername}
                            onChange={(e) => setPwNewUsername(e.target.value)}
                            required
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="admin-current-pw" className="text-xs">
                            Mật khẩu hiện tại
                          </Label>
                          <Input
                            id="admin-current-pw"
                            aria-label="Mật khẩu hiện tại"
                            type="password"
                            placeholder="Nhập mật khẩu cũ"
                            value={pwCurrent}
                            onChange={(e) => setPwCurrent(e.target.value)}
                            required
                          />
                        </div>
                        <div className="space-y-1.5">
                          <Label htmlFor="admin-new-pw" className="text-xs">
                            Mật khẩu mới
                          </Label>
                          <Input
                            id="admin-new-pw"
                            aria-label="Mật khẩu mới"
                            type="password"
                            placeholder="Ít nhất 4 ký tự"
                            minLength={4}
                            value={pwNewPassword}
                            onChange={(e) => setPwNewPassword(e.target.value)}
                            required
                          />
                        </div>
                      </div>

                      {pwError && (
                        <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                          {pwError}
                        </div>
                      )}

                      <div className="flex items-center justify-between pt-2 border-t border-border">
                        {pwNotice ? (
                          <span className="text-xs text-foreground flex items-center gap-1.5">
                            <CheckCircle2 className="size-4" /> {pwNotice}
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground">
                            Đổi mật khẩu sẽ hủy hiệu lực các phiên đăng nhập cũ ngay lập tức.
                          </span>
                        )}
                        <Button type="submit" size="sm" variant="secondary">
                          Cập nhật mật khẩu
                        </Button>
                      </div>
                    </form>
                  </CardContent>
                </Card>
              </div>
            )}

            {activeSection === 'anti-bot' && antiBot && (
              <div className="space-y-5">
                <div>
                  <h1 className="text-lg font-semibold tracking-tight">
                    Thiết lập Chống Bot (Anti-Bot & Stealth)
                  </h1>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    Điều chỉnh tốc độ cuộn trang, thời gian nghỉ và chế độ bảo vệ tài khoản.
                  </p>
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  {(
                    [
                      {
                        key: 'SAFE',
                        title: 'An Toàn (SAFE)',
                        desc: 'Nghỉ 3.0s–6.5s mỗi nhịp cuộn, Cooldown 25s giữa các kênh.',
                      },
                      {
                        key: 'BALANCED',
                        title: 'Cân Bằng (BALANCED)',
                        desc: 'Nghỉ 1.5s–3.5s mỗi nhịp cuộn, Cooldown 10s.',
                      },
                      {
                        key: 'FAST',
                        title: 'Nhanh (FAST)',
                        desc: 'Nghỉ 0.6s–1.4s, phù hợp quét nhanh số lượng ít.',
                      },
                    ] as const
                  ).map((p) => (
                    <Card
                      key={p.key}
                      onClick={() => void handleApplyPreset(p.key)}
                      className={`surface-standard cursor-pointer transition ${
                        antiBot.preset === p.key
                          ? 'ring-2 ring-foreground border-foreground'
                          : 'hover:border-foreground/25'
                      }`}
                    >
                      <CardHeader className="pb-2">
                        <div className="flex items-center justify-between">
                          <CardTitle className="text-sm font-semibold">{p.title}</CardTitle>
                          {antiBot.preset === p.key && (
                            <Badge variant="secondary" className="text-[10px]">
                              Đang chọn
                            </Badge>
                          )}
                        </div>
                        <CardDescription className="text-xs">
                          {p.desc}
                        </CardDescription>
                      </CardHeader>
                    </Card>
                  ))}
                </div>

                <Card className="surface-standard">
                  <CardHeader>
                    <CardTitle className="text-sm font-semibold">
                      Thông số chi tiết
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <form className="space-y-4" onSubmit={(e) => void handleSaveAntiBot(e)}>
                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 font-mono tabular-nums">
                        <div className="space-y-1.5">
                          <Label className="font-sans text-xs">
                            Độ trễ cuộn tối thiểu (ms)
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
                          <Label className="font-sans text-xs">
                            Độ trễ cuộn tối đa (ms)
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
                          <Label className="font-sans text-xs">
                            Nghỉ giữa 2 mục tiêu (giây)
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
                          <Label className="font-sans text-xs">Độ trễ tải tối thiểu (ms)</Label>
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
                          <Label className="font-sans text-xs">Độ trễ tải tối đa (ms)</Label>
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
                          <Label className="font-sans text-xs">Số lần cuộn tối đa</Label>
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

                      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4 rounded-xl border border-border p-3.5">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium">Chạy ẩn (Headless)</span>
                          <Switch
                            checked={Boolean(antiBot.headless_mode)}
                            onCheckedChange={(v) =>
                              setAntiBot({ ...antiBot, headless_mode: v })
                            }
                          />
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium">Ẩn WebDriver (Stealth)</span>
                          <Switch
                            checked={antiBot.stealth_mode}
                            onCheckedChange={(v) => setAntiBot({ ...antiBot, stealth_mode: v })}
                          />
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium">Cuộn tự nhiên</span>
                          <Switch
                            checked={antiBot.human_scroll}
                            onCheckedChange={(v) => setAntiBot({ ...antiBot, human_scroll: v })}
                          />
                        </div>

                        <div className="flex items-center justify-between gap-2">
                          <span className="text-xs font-medium">Tự dừng khi gặp Captcha</span>
                          <Switch
                            checked={antiBot.auto_stop_on_captcha}
                            onCheckedChange={(v) =>
                              setAntiBot({ ...antiBot, auto_stop_on_captcha: v })
                            }
                          />
                        </div>
                      </div>

                      <div className="flex items-center justify-between pt-1">
                        {antiBotSavedNotice ? (
                          <span className="text-xs text-foreground flex items-center gap-1.5">
                            <CheckCircle2 className="size-4" /> Đã lưu cấu hình
                          </span>
                        ) : (
                          <span className="text-xs text-muted-foreground font-mono tabular-nums">
                            Cập nhật: {formatDateTime(antiBot.updated_at)}
                          </span>
                        )}
                        <Button type="submit" size="sm">Lưu cấu hình</Button>
                      </div>
                    </form>
                  </CardContent>
                </Card>
              </div>
            )}
          </div>
        </main>
      </div>

      <VideoPreviewDialog
        video={previewVideo}
        open={previewVideo !== null}
        onOpenChange={(open) => {
          if (!open) setPreviewVideo(null)
        }}
        onDownload={handleDownloadSingle}
        onSaveBookmark={handleSaveBookmarkDetail}
        onSendToEdit={handleSendToEdit}
        sendingToEdit={previewVideo ? sendingEditIds.includes(previewVideo.aweme_id) : false}
      />

      <Dialog open={targetModalOpen} onOpenChange={setTargetModalOpen}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle>
              {targetForm.id === null
                ? 'Thêm Mục tiêu Quét'
                : `Chỉnh sửa Mục tiêu #${targetForm.id}`}
            </DialogTitle>
            <DialogDescription>
              Thiết lập nguồn dữ liệu và lịch chạy tự động.
            </DialogDescription>
          </DialogHeader>

          <form className="space-y-4 mt-2" onSubmit={(e) => void handleSaveTarget(e)}>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-1.5">
                <Label className="text-xs">Tên hiển thị</Label>
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
                  aria-label="Loại mục tiêu"
                  className="h-8 w-full rounded-lg border border-input bg-card px-3 text-xs text-foreground outline-none"
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
                  <option value="CHANNEL">CHANNEL (Kênh Douyin)</option>
                  <option value="KEYWORD">KEYWORD (Từ khóa)</option>
                  <option value="COLLECT">COLLECT (Mục Đã lưu)</option>
                </select>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-1.5 sm:col-span-2">
                <Label className="text-xs">Giá trị nguồn</Label>
                <Input
                  placeholder="Link kênh, từ khóa hoặc self"
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
                  className="font-mono tabular-nums"
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

            <div className="rounded-xl border border-border p-3.5 space-y-3">
              <Label className="text-xs font-medium">Chế độ hẹn giờ</Label>
              <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5">
                {(
                  [
                    { id: 'INTERVAL', label: 'Chu kỳ lặp' },
                    { id: 'DAILY', label: 'Hàng ngày' },
                    { id: 'ONCE', label: 'Chạy 1 lần' },
                    { id: 'CRON', label: 'Cron' },
                    { id: 'MANUAL', label: 'Thủ công' },
                  ] as const
                ).map((mode) => (
                  <Button
                    key={mode.id}
                    type="button"
                    size="sm"
                    variant={targetForm.schedule_type === mode.id ? 'default' : 'outline'}
                    onClick={() => setTargetForm({ ...targetForm, schedule_type: mode.id })}
                  >
                    {mode.label}
                  </Button>
                ))}
              </div>

              {targetForm.schedule_type === 'INTERVAL' && (
                <div className="grid grid-cols-2 gap-3 pt-1">
                  <div className="space-y-1">
                    <Label className="text-xs">Mỗi khoảng</Label>
                    <Input
                      type="number"
                      min={1}
                      className="font-mono tabular-nums"
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
                    <Label className="text-xs">Đơn vị</Label>
                    <select
                      aria-label="Đơn vị thời gian"
                      className="h-8 w-full rounded-lg border border-input bg-card px-3 text-xs text-foreground outline-none"
                      value={targetForm.interval_unit}
                      onChange={(e) =>
                        setTargetForm({
                          ...targetForm,
                          interval_unit: e.target.value as 'minutes' | 'hours',
                        })
                      }
                    >
                      <option value="minutes">Phút</option>
                      <option value="hours">Giờ</option>
                    </select>
                  </div>
                </div>
              )}

              {targetForm.schedule_type === 'DAILY' && (
                <div className="grid grid-cols-3 gap-3 pt-1">
                  <div className="space-y-1">
                    <Label className="text-xs">Giờ (0–23)</Label>
                    <Input
                      type="number"
                      min={0}
                      max={23}
                      className="font-mono tabular-nums"
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
                      className="font-mono tabular-nums"
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
                    <Label className="text-xs">Thứ</Label>
                    <Input
                      className="font-mono text-xs"
                      placeholder="*"
                      value={targetForm.daily_days}
                      onChange={(e) =>
                        setTargetForm({ ...targetForm, daily_days: e.target.value })
                      }
                    />
                  </div>
                </div>
              )}

              {targetForm.schedule_type === 'ONCE' && (
                <div className="pt-1">
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
                <div className="pt-1">
                  <Input
                    className="font-mono text-xs"
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

            <div className="grid gap-3 sm:grid-cols-2 rounded-xl border border-border p-3.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium">Tự động tải file không logo</span>
                <Switch
                  checked={targetForm.auto_download}
                  onCheckedChange={(v) => setTargetForm({ ...targetForm, auto_download: v })}
                />
              </div>

              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium">Kích hoạt lịch ngay</span>
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

      <Dialog
        open={confirmDialog !== null}
        onOpenChange={(open) => {
          if (!open) setConfirmDialog(null)
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{confirmDialog?.title}</DialogTitle>
            <DialogDescription>{confirmDialog?.description}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => setConfirmDialog(null)}
            >
              Hủy
            </Button>
            <Button
              type="button"
              variant="destructive"
              onClick={() => {
                const action = confirmDialog?.onConfirm
                setConfirmDialog(null)
                if (action) void action()
              }}
            >
              {confirmDialog?.confirmLabel || 'Xác nhận xóa'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <LiveTerminalDrawer
        logs={logsPage.items}
        selectedLogId={selectedTerminalLogId}
        open={terminalOpen}
        minimized={terminalMinimized}
        onSelectLog={(id) => setSelectedTerminalLogId(id)}
        onToggleMinimize={() => setTerminalMinimized((m) => !m)}
        onClose={() => setTerminalOpen(false)}
        onRetry={handleRetryLog}
      />
    </div>
  )
}
