import { useState } from 'react'
import {
  Bookmark,
  Check,
  Clock,
  Copy,
  Download,
  ExternalLink,
  Film,
  FolderCheck,
  Heart,
  Image as ImageIcon,
  MessageCircle,
  Music,
  Share2,
  Sparkles,
  User,
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
}

export function VideoPreviewDialog({
  video,
  open,
  onOpenChange,
  onDownload,
  onSaveBookmark,
}: VideoPreviewDialogProps) {
  const [collection, setCollection] = useState('')
  const [note, setNote] = useState('')
  const [copied, setCopied] = useState(false)
  const [albumIndex, setAlbumIndex] = useState(1)

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
        }
        onOpenChange(next)
      }}
    >
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">
              ID: {video.aweme_id}
            </Badge>
            <Badge variant="secondary" className="gap-1">
              {isAlbum ? (
                <>
                  <ImageIcon className="size-3.5" /> Album ({video.image_count || 1} ảnh)
                </>
              ) : (
                <>
                  <Clock className="size-3.5" /> {formatDurationMs(video.duration_ms)}
                </>
              )}
            </Badge>
            {video.width && video.height && (
              <Badge variant="outline">
                {video.width}×{video.height}
              </Badge>
            )}
            <Badge
              variant={
                video.download_status === 'COMPLETED'
                  ? 'default'
                  : video.download_status === 'FAILED'
                    ? 'destructive'
                    : 'secondary'
              }
            >
              {video.download_status}
            </Badge>
          </div>
          <DialogTitle className="mt-2 text-lg leading-snug">
            {video.description || 'Không có tiêu đề / mô tả'}
          </DialogTitle>
          <DialogDescription className="flex flex-wrap items-center gap-4 text-xs">
            <span className="inline-flex items-center gap-1 font-medium text-foreground">
              <User className="size-3.5 text-primary" /> {video.author_nickname} (
              <code className="text-[11px] text-muted-foreground">{video.author_sec_uid}</code>)
            </span>
            <span>Đăng lúc: {formatDateTime(video.create_time)}</span>
            <span>Crawl lúc: {formatDateTime(video.crawled_at)}</span>
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-6 md:grid-cols-12 mt-2">
          <div className="md:col-span-6 flex flex-col items-center justify-center rounded-xl border bg-black/90 p-3 min-h-[320px]">
            {isDownloaded && !isAlbum ? (
              <video
                key={video.aweme_id}
                src={`/api/videos/${video.aweme_id}/stream`}
                poster={video.cover_url || undefined}
                controls
                autoPlay
                className="max-h-[440px] w-full rounded-lg object-contain"
              />
            ) : isDownloaded && isAlbum ? (
              <div className="flex flex-col items-center gap-3 w-full">
                <img
                  src={`/api/videos/${video.aweme_id}/images/${albumIndex}`}
                  alt={`Slide ${albumIndex}`}
                  className="max-h-[380px] w-full rounded-lg object-contain"
                />
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={albumIndex <= 1}
                    onClick={() => setAlbumIndex((i) => Math.max(1, i - 1))}
                  >
                    Ảnh trước
                  </Button>
                  <span className="text-xs text-white">
                    Ảnh {albumIndex} / {Math.max(1, video.image_count)}
                  </span>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={albumIndex >= Math.max(1, video.image_count)}
                    onClick={() => setAlbumIndex((i) => i + 1)}
                  >
                    Ảnh tiếp
                  </Button>
                </div>
              </div>
            ) : (
              <div className="relative flex flex-col items-center justify-center text-center p-4 w-full">
                {video.cover_url ? (
                  <img
                    src={video.cover_url}
                    alt={video.description}
                    className="max-h-[320px] rounded-lg object-contain opacity-80"
                  />
                ) : (
                  <Film className="size-16 text-muted-foreground mb-3" />
                )}
                <div className="mt-4 flex flex-col items-center gap-2">
                  <p className="text-xs text-slate-300">
                    Video/Album chưa tải về ổ cứng. Bấm tải để lưu bản gốc không logo và phát trực tiếp.
                  </p>
                  <Button size="sm" onClick={() => void onDownload(video.aweme_id)}>
                    <Download className="size-4 mr-1.5" /> Tải Media Không Logo & Xem Ngay
                  </Button>
                </div>
              </div>
            )}
          </div>

          <div className="md:col-span-6 flex flex-col gap-4">
            <div className="grid grid-cols-4 gap-2 rounded-xl border bg-muted/40 p-3 text-center">
              <div>
                <div className="flex items-center justify-center gap-1 text-rose-500 font-semibold">
                  <Heart className="size-4" /> {formatNumber(video.digg_count)}
                </div>
                <span className="text-[11px] text-muted-foreground">Lượt tim</span>
              </div>
              <div>
                <div className="flex items-center justify-center gap-1 text-sky-400 font-semibold">
                  <MessageCircle className="size-4" /> {formatNumber(video.comment_count)}
                </div>
                <span className="text-[11px] text-muted-foreground">Bình luận</span>
              </div>
              <div>
                <div className="flex items-center justify-center gap-1 text-emerald-400 font-semibold">
                  <Share2 className="size-4" /> {formatNumber(video.share_count)}
                </div>
                <span className="text-[11px] text-muted-foreground">Chia sẻ</span>
              </div>
              <div>
                <div className="flex items-center justify-center gap-1 text-amber-400 font-semibold">
                  <Bookmark className="size-4" /> {formatNumber(video.collect_count)}
                </div>
                <span className="text-[11px] text-muted-foreground">Lượt lưu</span>
              </div>
            </div>

            <div className="space-y-2 text-xs rounded-xl border p-3">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Thời lượng video:</span>
                <span className="font-semibold">{formatDurationMs(video.duration_ms)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Nhạc nền:</span>
                <span className="font-medium inline-flex items-center gap-1">
                  <Music className="size-3.5 text-primary" />
                  {video.music_title || 'Âm thanh gốc'}
                  {video.music_author ? ` — ${video.music_author}` : ''}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Nguồn thu thập:</span>
                <span className="font-medium">
                  {video.source_names.length > 0 ? video.source_names.join(', ') : 'Crawl lẻ theo ID'}
                </span>
              </div>
              {video.video_local_path && (
                <div className="flex items-center justify-between gap-2 pt-1 border-t">
                  <span className="text-muted-foreground inline-flex items-center gap-1">
                    <FolderCheck className="size-3.5 text-emerald-400" /> File local:
                  </span>
                  <code className="truncate max-w-[240px] rounded bg-muted px-1.5 py-0.5 text-[11px]">
                    {video.video_local_path}
                  </code>
                </div>
              )}
              {video.hashtags.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-2 border-t">
                  {video.hashtags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-[11px]">
                      #{tag}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded-xl border p-3 space-y-3 bg-card">
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold inline-flex items-center gap-1.5">
                  <Sparkles className="size-3.5 text-amber-400" /> Quản lý Bookmark cá nhân
                </span>
                <Badge variant={video.is_bookmarked ? 'default' : 'outline'}>
                  {video.is_bookmarked ? '★ Đã Bookmark' : 'Chưa Bookmark'}
                </Badge>
              </div>
              <div className="grid gap-2">
                <Label className="text-xs">Nhãn bộ sưu tập (Collection)</Label>
                <Input
                  placeholder="Ví dụ: Idea kịch bản, Nhạc xu hướng, Đối thủ..."
                  value={collection}
                  onChange={(e) => setCollection(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label className="text-xs">Ghi chú cá nhân</Label>
                <Textarea
                  rows={2}
                  placeholder="Ghi chú điểm hay của video này..."
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
              </div>
              <div className="flex flex-wrap gap-2">
                <Button
                  size="sm"
                  onClick={() =>
                    void onSaveBookmark(video.aweme_id, true, collection, note)
                  }
                >
                  <Bookmark className="size-3.5 mr-1.5" />
                  {video.is_bookmarked ? 'Cập nhật Bookmark' : 'Lưu vào Bookmark'}
                </Button>
                {video.is_bookmarked && (
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() =>
                      void onSaveBookmark(video.aweme_id, false, collection, note)
                    }
                  >
                    Bỏ Bookmark
                  </Button>
                )}
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-auto">
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopy(video.aweme_id)}
              >
                {copied ? <Check className="size-3.5 mr-1" /> : <Copy className="size-3.5 mr-1" />}
                Copy ID
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => handleCopy(video.original_url)}
              >
                <Copy className="size-3.5 mr-1" /> Copy Link gốc
              </Button>
              {video.video_local_path && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => handleCopy(video.video_local_path || '')}
                >
                  <Copy className="size-3.5 mr-1" /> Copy Đường dẫn file
                </Button>
              )}
              <Button size="sm" variant="outline" asChild>
                <a href={video.original_url} target="_blank" rel="noreferrer">
                  <ExternalLink className="size-3.5 mr-1" /> Mở Douyin gốc
                </a>
              </Button>
              <Button
                size="sm"
                className="ml-auto"
                onClick={() => void onDownload(video.aweme_id)}
              >
                <Download className="size-3.5 mr-1.5" />
                {isDownloaded ? 'Tải lại Video' : 'Lưu Video Không Logo'}
              </Button>
            </div>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
