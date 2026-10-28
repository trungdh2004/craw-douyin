import { useEffect, useRef } from 'react'
import {
  ChevronDown,
  ChevronUp,
  RotateCcw,
  Terminal,
  X,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  type CrawlLogItem,
  formatDateTime,
  formatExecutionDuration,
} from '@/lib/api'

interface LiveTerminalDrawerProps {
  logs: CrawlLogItem[]
  selectedLogId: number | null
  open: boolean
  minimized: boolean
  onSelectLog: (logId: number) => void
  onToggleMinimize: () => void
  onClose: () => void
  onRetry?: (logId: number) => Promise<void>
}

export function LiveTerminalDrawer({
  logs,
  selectedLogId,
  open,
  minimized,
  onSelectLog,
  onToggleMinimize,
  onClose,
  onRetry,
}: LiveTerminalDrawerProps) {
  const scrollRef = useRef<HTMLDivElement | null>(null)

  const activeLog =
    logs.find((l) => l.id === selectedLogId) ||
    logs.find((l) => l.status === 'RUNNING') ||
    logs[0] ||
    null

  const events = activeLog?.events ?? []

  useEffect(() => {
    if (!minimized && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events.length, activeLog?.id, minimized])

  if (!open || !activeLog) return null

  const isRunning = activeLog.status === 'RUNNING'
  const targetLimit = activeLog.target_limit || 0
  const scannedCount =
    activeLog.scanned_count ??
    activeLog.new_videos_count + activeLog.updated_videos_count
  const progressPct =
    targetLimit > 0
      ? Math.min(100, Math.round((activeLog.new_videos_count / targetLimit) * 100))
      : 0

  return (
    <aside
      aria-label="Live Crawl Console"
      className="fixed bottom-4 right-4 z-50 w-[min(95vw,760px)] rounded-2xl border border-border bg-[#141519] text-foreground shadow-2xl overflow-hidden"
    >
      <div className="flex items-center justify-between gap-2 border-b border-border bg-card px-4 py-2.5">
        <div className="flex items-center gap-2.5 min-w-0">
          <Terminal className="size-4 text-muted-foreground shrink-0" />
          <span className="text-xs font-semibold text-foreground shrink-0">
            Nhật ký phiên chạy
          </span>
          {isRunning && (
            <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted px-2 py-0.5 text-[11px] text-foreground shrink-0">
              <span className="size-1.5 rounded-full bg-foreground animate-pulse" />
              Đang chạy
            </span>
          )}
          <select
            aria-label="Chọn phiên chạy để xem log"
            className="h-7 max-w-[280px] rounded-md border border-input bg-muted px-2 text-xs font-mono tabular-nums text-foreground outline-none"
            value={activeLog.id}
            onChange={(e) => onSelectLog(Number(e.target.value))}
          >
            {logs.slice(0, 15).map((item) => (
              <option key={item.id} value={item.id}>
                #{item.id} · {item.target_name || item.input_summary || item.job_type}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1 shrink-0">
          {(activeLog.status === 'FAILED' || activeLog.status === 'CAPTCHA_BLOCKED') &&
            onRetry && (
              <Button
                size="xs"
                variant="outline"
                onClick={() => void onRetry(activeLog.id)}
              >
                <RotateCcw className="size-3.5 mr-1" /> Chạy lại
              </Button>
            )}
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={onToggleMinimize}
            aria-label={minimized ? 'Mở rộng Console' : 'Thu gọn Console'}
          >
            {minimized ? <ChevronUp className="size-4" /> : <ChevronDown className="size-4" />}
          </Button>
          <Button
            size="icon-sm"
            variant="ghost"
            onClick={onClose}
            aria-label="Đóng Console"
          >
            <X className="size-4" />
          </Button>
        </div>
      </div>

      <div className="border-b border-border bg-muted/60 px-4 py-2 text-xs font-mono tabular-nums space-y-1.5">
        <div className="flex flex-wrap items-center justify-between gap-2 text-muted-foreground">
          <div className="flex items-center gap-2">
            <span className="text-foreground font-medium">#{activeLog.id}</span>
            <span>·</span>
            <span>{formatDateTime(activeLog.started_at)}</span>
            <span>·</span>
            <span>{formatExecutionDuration(activeLog.duration_ms)}</span>
          </div>
          <div>
            <strong className="text-foreground">+{activeLog.new_videos_count}</strong> mới ·{' '}
            {activeLog.updated_videos_count} trùng · Quét {scannedCount} ({events.length} dòng)
          </div>
        </div>

        {targetLimit > 0 && (
          <div className="h-1 w-full overflow-hidden rounded-full bg-border">
            <div
              className="h-full bg-foreground transition-all duration-300"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        )}
      </div>

      {!minimized && (
        <div
          ref={scrollRef}
          className="max-h-80 min-h-[200px] overflow-y-auto font-mono tabular-nums text-xs divide-y divide-border/80 bg-[#111216]"
        >
          {events.length === 0 ? (
            <div className="py-10 px-4 text-center text-muted-foreground font-sans">
              {activeLog.current_phase ||
                (activeLog.error_message
                  ? `Lỗi: ${activeLog.error_message}`
                  : 'Chưa có nhật ký chi tiết cho phiên này.')}
            </div>
          ) : (
            events.map((ev, idx) => (
              <div
                key={`${ev.ts}-${idx}`}
                className={`grid grid-cols-[28px_68px_92px_1fr] items-baseline gap-2.5 px-4 py-2 transition-colors hover:bg-white/[0.04] ${
                  ev.level === 'ERROR'
                    ? 'bg-destructive/10'
                    : idx % 2 === 1
                      ? 'bg-white/[0.015]'
                      : ''
                }`}
              >
                <span className="text-[11px] text-muted-foreground/50 select-none text-right">
                  {String(idx + 1).padStart(2, '0')}
                </span>
                <span className="text-[11px] text-muted-foreground">
                  {ev.ts}
                </span>
                <span className="truncate text-center rounded border border-border bg-card px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                  {ev.step}
                </span>
                <span
                  className={
                    ev.level === 'ERROR'
                      ? 'text-destructive font-medium break-words leading-5'
                      : 'text-foreground break-words leading-5'
                  }
                >
                  {ev.message}
                </span>
              </div>
            ))
          )}
        </div>
      )}
    </aside>
  )
}
