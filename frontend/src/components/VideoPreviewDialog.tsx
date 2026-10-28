import { useState } from 'react'
import {
  Bookmark,
  Check,
  Copy,
  Download,
  ExternalLink,
  Film,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  type VideoItem,
  formatDateTime,
  formatDurationMs,
  formatNumber,
} from '@/lib/api'

interface VideoPreviewDialogProps {
  video: VideoItem | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onDownload: (awemeId: string) => Promise<void>
  onSaveBookmark: (
    awemeId: string,
    isBookmarked: boolean,
    collection: string,
    note: string,
  ) => Promise<void>
  onSendToEdit?: (awemeIds: string[]) => Promise<void>
  sendingToEdit?: boolean
}

export function VideoPreviewDialog({
  video,
  open,
  onOpenChange,
  onDownload,
  onSaveBookmark,
  onSendToEdit,
  sendingToEdit = false,
}: VideoPreviewDialogProps) {
  const [collection, setCollection] = useState('')
  const [note, setNote] = useState('')
  const [copied, setCopied] = useState(false)
  const [albumIndex, setAlbumIndex] = useState(1)
  const [streamError, setStreamError] = useState(false)

  if (!video) return null

  const isAlbum = video.aweme_type === 68
  const isDownloaded = video.download_status === 'COMPLETED'

  const handleCopy = (text: string) => {
    void navigator.clipboard.writeText(text)
    setCopied(true)
    window.setTimeout(() => setCopied(false), 1500)
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (next && video) {
          setCollection(video.bookmark_collection || '')
          setNote(video.bookmark_note || '')
          setAlbumIndex(1)
          setStreamError(false)
        }
        onOpenChange(next)
      }}
    >
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2 font-mono tabular-nums text-xs text-muted-foreground">
            <span>#{video.aweme_id}</span>
            <span>·</span>
            <span>
              {isAlbum
                ? `${video.image_count || 1} ảnh`
                : formatDurationMs(video.duration_ms)}
            </span>
            {video.width && video.height && (
              <>
                <span>·</span>
                <span>
                  {video.width}×{video.height}
                </span>
              </>
            )}
            <Badge variant="outline" className="ml-auto font-normal">
              {video.download_status}
            </Badge>
          </div>
          <DialogTitle className="mt-1 text-base font-semibold leading-snug">
            {video.description || 'Không có tiêu đề / mô tả'}
          </DialogTitle>
          <DialogDescription className="text-xs">
            @{video.author_nickname} · Đăng lúc {formatDateTime(video.create_time)}
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 md:grid-cols-12 mt-4">
          <div className="md:col-span-6 flex flex-col items-center justify-center rounded-xl border border-border bg-black/95 p-3 min-h-[300px]">
            {!isAlbum && (isDownloaded || !streamError) ? (
              <div className="flex flex-col items-center gap-2 w-full">
                <video
                  key={`${video.aweme_id}-${video.download_status}`}
                  src={`/api/videos/${video.aweme_id}/stream`}
                  poster={video.cover_url || undefined}
                  controls
                  playsInline
                  onError={() => setStreamError(true)}
                  className="max-h-[400px] w-full rounded-lg object-contain"
                />
              </div>
            ) : isDownloaded && isAlbum ? (
              <div className="flex flex-col items-center gap-3 w-full">
                <img
                  src={`/api/videos/${video.aweme_id}/images/${albumIndex}`}
                  alt={`Slide ${albumIndex}`}
                  className="max-h-[360px] w-full rounded-lg object-contain"
                />
                <div className="flex items-center gap-2 font-mono tabular-nums">
                  <Button
                    size="xs"
                    variant="secondary"
                    disabled={albumIndex <= 1}
                    onClick={() => setAlbumIndex((i) => Math.max(1, i - 1))}
                  >
                    Trước
                  </Button>
                  <span className="text-xs text-white">
                    {albumIndex} / {Math.max(1, video.image_count)}
                  </span>
                  <Button
                    size="xs"
                    variant="secondary"
                    disabled={albumIndex >= Math.max(1, video.image_count)}
                    onClick={() => setAlbumIndex((i) => i + 1)}
                  >
                    Tiếp
                  </Button>
                </div>
              </div>
            ) : (
              <div className="relative flex flex-col items-center justify-center text-center p-4 w-full">
                {video.cover_url ? (
                  <img
                    src={video.cover_url}
                    alt={video.description}
                    className="max-h-[280px] rounded-lg object-contain opacity-85"
                  />
                ) : (
                  <Film className="size-12 text-white/40 mb-3" />
                )}
                <div className="mt-4">
                  <Button size="sm" variant="secondary" onClick={() => void onDownload(video.aweme_id)}>
                    <Download className="size-3.5 mr-1.5" /> Tải bản gốc không logo
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="md:col-span-6 flex flex-col gap-4">
            <div className="grid grid-cols-4 gap-2 rounded-xl border border-border bg-muted/40 p-3 text-center font-mono tabular-nums">
              <div>
                <div className="text-sm font-semibold">{formatNumber(video.digg_count)}</div>
                <span className="font-sans text-[11px] text-muted-foreground">Tim</span>
              </div>
              <div>
                <div className="text-sm font-semibold">{formatNumber(video.comment_count)}</div>
                <span className="font-sans text-[11px] text-muted-foreground">Bình luận</span>
              </div>
              <div>
                <div className="text-sm font-semibold">{formatNumber(video.share_count)}</div>
                <span className="font-sans text-[11px] text-muted-foreground">Chia sẻ</span>
              </div>
              <div>
                <div className="text-sm font-semibold">{formatNumber(video.collect_count)}</div>
                <span className="font-sans text-[11px] text-muted-foreground">Lượt lưu</span>
              </div>
            </div>

            <div className="surface-standard space-y-2 text-xs rounded-xl p-3.5">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Nhạc nền</span>
                <span className="font-medium truncate max-w-[220px]">
                  {video.music_title || 'Âm thanh gốc'}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Nguồn</span>
                <span className="font-medium">
                  {video.source_names.length > 0 ? video.source_names.join(', ') : 'Crawl lẻ'}
                </span>
              </div>
              {video.video_local_path && (
                <div className="flex items-center justify-between gap-2 pt-1.5 border-t border-border">
                  <span className="text-muted-foreground">File</span>
                  <code className="truncate max-w-[240px] text-[11px] font-mono text-muted-foreground">
                    {video.video_local_path}
                  </code>
                </div>
              )}
            </div>

            <div className="surface-standard rounded-xl p-3.5 space-y-2.5">
              <div className="grid gap-1.5">
                <Label className="text-xs">Bộ sưu tập Bookmark</Label>
                <Input
                  placeholder="Ví dụ: Idea kịch bản, Tham khảo..."
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <Label className="text-xs">Ghi chú</Label>
                <Textarea
                  rows={2}
                  placeholder="Ghi chú..."
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>
              <div className="flex gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() =>
                    void onSaveBookmark(video.aweme_id, true, collection, note)
                  }
                >
                  <Bookmark className="size-3.5 mr-1.5" />
                  {video.is_bookmarked ? 'Cập nhật Bookmark' : 'Lưu Bookmark'}
                </Button>
                {video.is_bookmarked && (
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() =>
                      void onSaveBookmark(video.aweme_id, false, collection, note)
                    }
                  >
                    Bỏ lưu
                  </Button>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-auto pt-1">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopy(video.aweme_id)}
              >
                {copied ? <Check className="size-3.5 mr-1" /> : <Copy className="size-3.5 mr-1" />}
                Copy ID
              </Button>
              <Button size="sm" variant="outline" asChild>
                <a href={video.original_url} target="_blank" rel="noreferrer">
                  <ExternalLink className="size-3.5 mr-1" /> Douyin gốc
                </a>
              </Button>
              {!isAlbum && onSendToEdit && (
                video.edit_item_id ? (
                  <Button size="sm" variant="secondary" asChild>
                    <a
                      href={
                        video.edit_studio_url ||
                        `http://127.0.0.1:8000/items/${video.edit_item_id}`
                      }
                      target="_blank"
                      rel="noreferrer"
                    >
                      Mở Studio ↗
                    </a>
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={sendingToEdit}
                    onClick={() => void onSendToEdit([video.aweme_id])}
                  >
                    {sendingToEdit ? 'Đang gửi...' : 'Phân tích & Dịch'}
                  </Button>
                )
              )}
              <Button
                size="sm"
                variant="default"
                className="ml-auto"
                onClick={() => void onDownload(video.aweme_id)}
              >
                <Download className="size-3.5 mr-1.5" />
                {isDownloaded ? 'Tải lại' : 'Lưu Video'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
