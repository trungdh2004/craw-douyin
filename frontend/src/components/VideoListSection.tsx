import { useState } from 'react'
import {
  Bookmark,
  Calendar,
  Clock,
  Download,
  ExternalLink,
  Eye,
  Film,
  Heart,
  Image as ImageIcon,
  LayoutGrid,
  List,
  MessageCircle,
  Music,
  RefreshCw,
  Search,
  Share2,
  Star,
} from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  type BookmarkCollection,
  type CrawlTargetItem,
  type VideoItem,
  formatDateTime,
  formatDurationMs,
  formatNumber,
} from '@/lib/api'

export interface VideoFilterState {
  search: string
  target_id: string
  aweme_type: string
  download_status: string
  min_digg: string
  min_duration_sec: string
  max_duration_sec: string
  bookmark_collection: string
  sort: string
  order: 'asc' | 'desc'
  page: number
}

interface VideoListSectionProps {
  title: string
  subtitle: string
  videos: VideoItem[]
  total: number
  pageSize: number
  targets: CrawlTargetItem[]
  collections?: BookmarkCollection[]
  bookmarkOnly?: boolean
  filters: VideoFilterState
  onFiltersChange: (next: VideoFilterState) => void
  onRefresh: () => Promise<void>
  onDownloadSingle: (awemeId: string) => Promise<void>
  onBatchDownload: (awemeIds: string[]) => Promise<void>
  onToggleBookmark: (video: VideoItem) => Promise<void>
  onBatchBookmark: (awemeIds: string[], isBookmarked: boolean, collection?: string) => Promise<void>
  onPreview: (video: VideoItem) => void
  onSyncDouyinCollect?: () => Promise<void>
}

export function VideoListSection({
  title,
  subtitle,
  videos,
  total,
  pageSize,
  targets,
  collections = [],
  bookmarkOnly = false,
  filters,
  onFiltersChange,
  onRefresh,
  onDownloadSingle,
  onBatchDownload,
  onToggleBookmark,
  onBatchBookmark,
  onPreview,
  onSyncDouyinCollect,
}: VideoListSectionProps) {
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid')
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [batchCollection, setBatchCollection] = useState('')

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const toggleSelect = (awemeId: string) => {
    setSelectedIds((prev) =>
      prev.includes(awemeId) ? prev.filter((id) => id !== awemeId) : [...prev, awemeId],
    )
  }

  const toggleSelectAll = () => {
    if (selectedIds.length === videos.length) {
      setSelectedIds([])
    } else {
      setSelectedIds(videos.map((v) => v.aweme_id))
    }
  }

  const updateFilter = (patch: Partial<VideoFilterState>) => {
    onFiltersChange({ ...filters, page: 1, ...patch })
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {bookmarkOnly && onSyncDouyinCollect && (
            <Button variant="secondary" size="sm" onClick={() => void onSyncDouyinCollect()}>
              <Bookmark className="size-4 mr-1.5 text-amber-400" />
              Đồng bộ mục Đã lưu từ Douyin
            </Button>
          )}
          <div className="inline-flex rounded-lg border bg-muted/40 p-0.5">
            <Button
              size="sm"
              variant={viewMode === 'grid' ? 'default' : 'ghost'}
              className="h-7 px-2.5 text-xs"
              onClick={() => setViewMode('grid')}
            >
              <LayoutGrid className="size-3.5 mr-1" /> Lưới Card
            </Button>
            <Button
              size="sm"
              variant={viewMode === 'table' ? 'default' : 'ghost'}
              className="h-7 px-2.5 text-xs"
              onClick={() => setViewMode('table')}
            >
              <List className="size-3.5 mr-1" /> Bảng Metadata
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={() => void onRefresh()}>
            <RefreshCw className="size-4 mr-1.5" /> Làm mới
          </Button>
        </div>
      </div>

      {bookmarkOnly && collections.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Bộ sưu tập:</span>
          <Button
            size="sm"
            variant={filters.bookmark_collection === '' ? 'default' : 'outline'}
            className="h-7 text-xs"
            onClick={() => updateFilter({ bookmark_collection: '' })}
          >
            Tất cả ({total})
          </Button>
          {collections.map((col) => (
            <Button
              key={col.name}
              size="sm"
              variant={filters.bookmark_collection === col.name ? 'default' : 'outline'}
              className="h-7 text-xs"
              onClick={() => updateFilter({ bookmark_collection: col.name })}
            >
              {col.name} ({col.count})
            </Button>
          ))}
        </div>
      )}

      <Card>
        <CardContent className="p-4 space-y-3">
          <div className="grid gap-2.5 md:grid-cols-6">
            <div className="relative md:col-span-2">
              <Search className="size-4 absolute left-2.5 top-2.5 text-muted-foreground" />
              <Input
                className="pl-8"
                placeholder="Tìm theo mô tả, hashtag..."
                value={filters.search}
                onChange={(e) => updateFilter({ search: e.target.value })}
              />
            </div>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={filters.target_id}
              onChange={(e) => updateFilter({ target_id: e.target.value })}
            >
              <option value="">Mọi nguồn quét</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name} ({t.target_type})
                </option>
              ))}
            </select>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={filters.aweme_type}
              onChange={(e) => updateFilter({ aweme_type: e.target.value })}
            >
              <option value="">Mọi định dạng</option>
              <option value="0">🎬 Video (.mp4)</option>
              <option value="68">📷 Album ảnh trượt</option>
            </select>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={filters.download_status}
              onChange={(e) => updateFilter({ download_status: e.target.value })}
            >
              <option value="">Mọi trạng thái tải</option>
              <option value="NONE">Chưa tải (NONE)</option>
              <option value="DOWNLOADING">Đang tải (DOWNLOADING)</option>
              <option value="COMPLETED">Đã tải xong (COMPLETED)</option>
              <option value="FAILED">Lỗi tải (FAILED)</option>
            </select>
            <Input
              type="number"
              min={0}
              placeholder="Tim tối thiểu..."
              value={filters.min_digg}
              onChange={(e) => updateFilter({ min_digg: e.target.value })}
            />
          </div>

          <div className="grid gap-2.5 md:grid-cols-6 items-center">
            <Input
              type="number"
              min={0}
              placeholder="Thời lượng từ (giây)"
              value={filters.min_duration_sec}
              onChange={(e) => updateFilter({ min_duration_sec: e.target.value })}
            />
            <Input
              type="number"
              min={0}
              placeholder="Thời lượng đến (giây)"
              value={filters.max_duration_sec}
              onChange={(e) => updateFilter({ max_duration_sec: e.target.value })}
            />
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm md:col-span-2"
              value={filters.sort}
              onChange={(e) => updateFilter({ sort: e.target.value })}
            >
              <option value="create_time">Sắp xếp: Thời gian đăng bài</option>
              <option value="crawled_at">Sắp xếp: Thời gian crawl về</option>
              <option value="duration_ms">Sắp xếp: Thời lượng video (MM:SS)</option>
              <option value="digg_count">Sắp xếp: Lượt tim (❤)</option>
              <option value="comment_count">Sắp xếp: Bình luận (💬)</option>
              <option value="share_count">Sắp xếp: Chia sẻ (↗)</option>
              <option value="collect_count">Sắp xếp: Lượt lưu Douyin (🔖)</option>
            </select>
            <select
              className="h-9 rounded-md border bg-background px-3 text-sm"
              value={filters.order}
              onChange={(e) => updateFilter({ order: e.target.value as 'asc' | 'desc' })}
            >
              <option value="desc">Giảm dần (Cao → Thấp / Mới nhất)</option>
              <option value="asc">Tăng dần (Thấp → Cao / Cũ nhất)</option>
            </select>
            <div className="text-right text-xs text-muted-foreground">
              Tổng cộng: <strong className="text-foreground">{total}</strong> bài đăng
            </div>
          </div>

          {selectedIds.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 border-t pt-3">
              <Badge variant="default">Đã chọn {selectedIds.length} bài</Badge>
              <Button
                size="sm"
                onClick={() => {
                  void onBatchDownload(selectedIds)
                  setSelectedIds([])
                }}
              >
                <Download className="size-3.5 mr-1.5" /> Tải hàng loạt ({selectedIds.length})
              </Button>
              <Input
                className="h-8 w-48 text-xs"
                placeholder="Nhãn Bookmark hàng loạt..."
                value={batchCollection}
                onChange={(e) => setBatchCollection(e.target.value)}
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={() => {
                  void onBatchBookmark(selectedIds, true, batchCollection || undefined)
                  setSelectedIds([])
                }}
              >
                <Star className="size-3.5 mr-1 text-amber-400" /> Bookmark đã chọn
              </Button>
              {bookmarkOnly && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    void onBatchBookmark(selectedIds, false)
                    setSelectedIds([])
                  }}
                >
                  Bỏ Bookmark đã chọn
                </Button>
              )}
              <Button size="sm" variant="ghost" onClick={() => setSelectedIds([])}>
                Bỏ chọn
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {videos.length === 0 ? (
        <Card>
          <CardContent className="py-14 text-center text-muted-foreground">
            Không tìm thấy bài đăng nào khớp bộ lọc hiện tại.
          </CardContent>
        </Card>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {videos.map((video) => {
            const isAlbum = video.aweme_type === 68
            const isSelected = selectedIds.includes(video.aweme_id)
            return (
              <Card
                key={video.aweme_id}
                className={`overflow-hidden transition border ${
                  isSelected ? 'ring-2 ring-primary border-primary' : 'hover:border-primary/40'
                }`}
              >
                <div
                  className="relative aspect-video bg-slate-900 cursor-pointer group"
                  onClick={() => onPreview(video)}
                >
                  {video.cover_url ? (
                    <img
                      src={video.cover_url}
                      alt={video.description}
                      className="h-full w-full object-cover transition group-hover:scale-[1.02]"
                    />
                  ) : (
                    <div className="flex h-full w-full items-center justify-center text-muted-foreground">
                      <Film className="size-10" />
                    </div>
                  )}

                  <div
                    className="absolute top-2 left-2 z-10 flex items-center gap-1.5"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => toggleSelect(video.aweme_id)}
                      className="size-4 rounded accent-primary"
                    />
                    <Badge variant="secondary" className="bg-black/75 text-white text-[11px]">
                      ID: {video.aweme_id.slice(-8)}
                    </Badge>
                  </div>

                  <div
                    className="absolute top-2 right-2 z-10 flex items-center gap-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <Button
                      size="icon"
                      variant={video.is_bookmarked ? 'default' : 'secondary'}
                      className="size-7 rounded-full"
                      title={video.is_bookmarked ? 'Bỏ Bookmark' : 'Đánh dấu Bookmark'}
                      onClick={() => void onToggleBookmark(video)}
                    >
                      <Star
                        className={`size-3.5 ${
                          video.is_bookmarked ? 'fill-amber-300 text-amber-300' : ''
                        }`}
                      />
                    </Button>
                  </div>

                  {/* Badge Thời lượng phát của video (MM:SS) hoặc số ảnh Album */}
                  <div className="absolute bottom-2 right-2 rounded-md bg-black/85 px-2 py-0.5 text-xs font-semibold text-white flex items-center gap-1 shadow">
                    {isAlbum ? (
                      <>
                        <ImageIcon className="size-3.5 text-cyan-400" />
                        <span>{video.image_count || 1} ảnh</span>
                      </>
                    ) : (
                      <>
                        <Clock className="size-3.5 text-cyan-400" />
                        <span>{formatDurationMs(video.duration_ms)}</span>
                      </>
                    )}
                  </div>

                  {video.width && video.height && (
                    <div className="absolute bottom-2 left-2 rounded bg-black/70 px-1.5 py-0.5 text-[10px] text-slate-200">
                      {video.width}×{video.height}
                    </div>
                  )}
                </div>

                <CardContent className="p-3.5 space-y-2.5">
                  <div className="flex items-center justify-between gap-2 text-xs">
                    <span className="font-semibold text-foreground truncate">
                      @{video.author_nickname}
                    </span>
                    <Badge
                      variant={
                        video.download_status === 'COMPLETED'
                          ? 'default'
                          : video.download_status === 'FAILED'
                            ? 'destructive'
                            : 'outline'
                      }
                      className="text-[10px]"
                    >
                      {video.download_status}
                    </Badge>
                  </div>

                  <p
                    className="line-clamp-2 text-sm font-medium leading-snug cursor-pointer hover:text-primary"
                    onClick={() => onPreview(video)}
                  >
                    {video.description || '(Không có mô tả)'}
                  </p>

                  {video.hashtags.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {video.hashtags.slice(0, 4).map((tag) => (
                        <span
                          key={tag}
                          className="rounded bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground"
                        >
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Metadata Thời gian đăng, thời gian crawl, nhạc nền & nguồn */}
                  <div className="rounded-lg bg-muted/40 p-2 text-[11px] text-muted-foreground space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1">
                        <Calendar className="size-3 text-primary" /> Đăng:
                      </span>
                      <span className="font-medium text-foreground">
                        {formatDateTime(video.create_time)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="inline-flex items-center gap-1">
                        <Clock className="size-3 text-cyan-400" /> Thời lượng:
                      </span>
                      <span className="font-semibold text-foreground">
                        {isAlbum
                          ? `Album ${video.image_count || 1} ảnh`
                          : formatDurationMs(video.duration_ms)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Crawl lúc:</span>
                      <span>{formatDateTime(video.crawled_at)}</span>
                    </div>
                    {video.music_title && (
                      <div className="flex items-center gap-1 truncate">
                        <Music className="size-3 shrink-0 text-primary" />
                        <span className="truncate">{video.music_title}</span>
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <span>Nguồn:</span>
                      <span className="truncate max-w-[160px] font-medium text-foreground">
                        {video.source_names.join(', ') || 'Crawl ID lẻ'}
                      </span>
                    </div>
                  </div>

                  {video.bookmark_collection && (
                    <div className="flex items-center gap-1.5 text-xs">
                      <Badge variant="secondary" className="text-[11px]">
                        ★ {video.bookmark_collection}
                      </Badge>
                      {video.bookmark_note && (
                        <span className="text-[11px] text-muted-foreground truncate">
                          “{video.bookmark_note}”
                        </span>
                      )}
                    </div>
                  )}

                  <div className="grid grid-cols-4 gap-1 border-t pt-2 text-center text-xs">
                    <span className="inline-flex items-center justify-center gap-1 text-rose-400">
                      <Heart className="size-3.5" /> {formatNumber(video.digg_count)}
                    </span>
                    <span className="inline-flex items-center justify-center gap-1 text-sky-400">
                      <MessageCircle className="size-3.5" /> {formatNumber(video.comment_count)}
                    </span>
                    <span className="inline-flex items-center justify-center gap-1 text-emerald-400">
                      <Share2 className="size-3.5" /> {formatNumber(video.share_count)}
                    </span>
                    <span className="inline-flex items-center justify-center gap-1 text-amber-400">
                      <Bookmark className="size-3.5" /> {formatNumber(video.collect_count)}
                    </span>
                  </div>

                  <div className="flex items-center gap-1.5 pt-1">
                    <Button
                      size="sm"
                      variant="secondary"
                      className="h-8 text-xs flex-1"
                      onClick={() => onPreview(video)}
                    >
                      <Eye className="size-3.5 mr-1" /> Xem & Meta
                    </Button>
                    <Button
                      size="sm"
                      variant={video.download_status === 'COMPLETED' ? 'outline' : 'default'}
                      className="h-8 text-xs flex-1"
                      onClick={() => void onDownloadSingle(video.aweme_id)}
                    >
                      <Download className="size-3.5 mr-1" />
                      {video.download_status === 'COMPLETED' ? 'Đã lưu' : 'Lưu Video'}
                    </Button>
                    <Button size="icon" variant="ghost" className="size-8" asChild>
                      <a href={video.original_url} target="_blank" rel="noreferrer" title="Mở link gốc">
                        <ExternalLink className="size-3.5" />
                      </a>
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      checked={videos.length > 0 && selectedIds.length === videos.length}
                      onChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead>Bài đăng & Metadata</TableHead>
                  <TableHead>Tác giả & Nguồn</TableHead>
                  <TableHead>Thời lượng & Kích thước</TableHead>
                  <TableHead>Thời gian (Đăng / Crawl)</TableHead>
                  <TableHead>Tương tác (❤/💬/↗/🔖)</TableHead>
                  <TableHead>Trạng thái</TableHead>
                  <TableHead className="text-right">Thao tác</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {videos.map((video) => (
                  <TableRow key={video.aweme_id}>
                    <TableCell>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(video.aweme_id)}
                        onChange={() => toggleSelect(video.aweme_id)}
                      />
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <div className="flex items-start gap-2.5">
                        {video.cover_url && (
                          <img
                            src={video.cover_url}
                            alt=""
                            className="h-12 w-20 rounded object-cover shrink-0 cursor-pointer"
                            onClick={() => onPreview(video)}
                          />
                        )}
                        <div className="space-y-1 min-w-0">
                          <p
                            className="text-xs font-medium line-clamp-2 cursor-pointer hover:text-primary"
                            onClick={() => onPreview(video)}
                          >
                            {video.description || '(Không có mô tả)'}
                          </p>
                          <div className="flex flex-wrap items-center gap-1 text-[10px] text-muted-foreground">
                            <code>ID: {video.aweme_id}</code>
                            {video.music_title && <span>· 🎵 {video.music_title}</span>}
                          </div>
                        </div>
                      </div>
                    </TableCell>
                    <TableCell className="text-xs">
                      <div className="font-semibold">@{video.author_nickname}</div>
                      <div className="text-[11px] text-muted-foreground">
                        {video.source_names.join(', ') || 'Crawl lẻ'}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs">
                      <Badge variant="secondary" className="font-mono">
                        {video.aweme_type === 68
                          ? `${video.image_count || 1} ảnh`
                          : formatDurationMs(video.duration_ms)}
                      </Badge>
                      {video.width && video.height && (
                        <div className="text-[11px] text-muted-foreground mt-1">
                          {video.width}×{video.height}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-xs">
                      <div>Đăng: {formatDateTime(video.create_time)}</div>
                      <div className="text-[11px] text-muted-foreground">
                        Crawl: {formatDateTime(video.crawled_at)}
                      </div>
                    </TableCell>
                    <TableCell className="text-xs">
                      <div>
                        ❤ {formatNumber(video.digg_count)} · 💬 {formatNumber(video.comment_count)}
                      </div>
                      <div className="text-muted-foreground">
                        ↗ {formatNumber(video.share_count)} · 🔖 {formatNumber(video.collect_count)}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge
                        variant={
                          video.download_status === 'COMPLETED'
                            ? 'default'
                            : video.download_status === 'FAILED'
                              ? 'destructive'
                              : 'outline'
                        }
                      >
                        {video.download_status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right space-x-1">
                      <Button
                        size="icon"
                        variant={video.is_bookmarked ? 'default' : 'ghost'}
                        className="size-7"
                        onClick={() => void onToggleBookmark(video)}
                      >
                        <Star className="size-3.5" />
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        className="h-7 text-xs"
                        onClick={() => onPreview(video)}
                      >
                        Xem
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 text-xs"
                        onClick={() => void onDownloadSingle(video.aweme_id)}
                      >
                        Tải
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-muted-foreground">
          Trang {filters.page} / {totalPages} (Tổng {total} bài)
        </span>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={filters.page <= 1}
            onClick={() => onFiltersChange({ ...filters, page: filters.page - 1 })}
          >
            Trang trước
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={filters.page >= totalPages}
            onClick={() => onFiltersChange({ ...filters, page: filters.page + 1 })}
          >
            Trang sau
          </Button>
        </div>
      </div>
    </div>
  )
}
