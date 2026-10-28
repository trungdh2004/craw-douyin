import { useState } from 'react'
import {
  Bookmark,
  Download,
  ExternalLink,
  Film,
  LayoutGrid,
  List,
  RefreshCw,
  RotateCcw,
  Search,
  Settings2,
  Star,
  Trash2,
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
  type SuggestedTopicItem,
  type TrendsResponse,
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
  is_bookmarked: string
  is_analyzed?: string
  edit_status?: string
  date_from: string
  date_to: string
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
  trends?: TrendsResponse | null
  bookmarkOnly?: boolean
  analyzedOnly?: boolean
  editStudioBaseUrl?: string
  onOpenStudioSettings?: () => void
  onClearEditStatus?: (awemeId: string) => Promise<void>
  filters: VideoFilterState
  onFiltersChange: (next: VideoFilterState) => void
  onRefresh: () => Promise<void>
  onDownloadSingle: (awemeId: string) => Promise<void>
  onBatchDownload: (awemeIds: string[]) => Promise<void>
  onToggleBookmark: (video: VideoItem) => Promise<void>
  onBatchBookmark: (awemeIds: string[], isBookmarked: boolean, collection?: string) => Promise<void>
  onPreview: (video: VideoItem) => void
  onSyncDouyinCollect?: () => Promise<void>
  onQuickCrawlTopic?: (topic: SuggestedTopicItem) => Promise<void>
  onSendToEdit?: (awemeIds: string[]) => Promise<void>
  sendingEditIds?: string[]
}

export function VideoListSection({
  title,
  subtitle,
  videos,
  total,
  pageSize,
  targets,
  collections = [],
  trends = null,
  bookmarkOnly = false,
  analyzedOnly = false,
  editStudioBaseUrl = 'http://127.0.0.1:8000',
  onOpenStudioSettings,
  onClearEditStatus,
  filters,
  onFiltersChange,
  onRefresh,
  onDownloadSingle,
  onBatchDownload,
  onToggleBookmark,
  onBatchBookmark,
  onPreview,
  onSyncDouyinCollect,
  onQuickCrawlTopic,
  onSendToEdit,
  sendingEditIds = [],
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-lg font-semibold tracking-tight text-foreground">{title}</h1>
          <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {bookmarkOnly && onSyncDouyinCollect && (
            <Button variant="outline" size="sm" onClick={() => void onSyncDouyinCollect()}>
              <Bookmark className="size-3.5 mr-1.5" />
              Đồng bộ mục Đã lưu từ Douyin
            </Button>
          )}
          {analyzedOnly && onOpenStudioSettings && (
            <Button variant="outline" size="sm" onClick={onOpenStudioSettings}>
              <Settings2 className="size-3.5 mr-1.5" />
              Server: {editStudioBaseUrl.replace(/^https?:\/\//, '')}
            </Button>
          )}
          <div
            role="group"
            aria-label="Chế độ hiển thị"
            className="inline-flex rounded-lg border border-border bg-muted/60 p-0.5"
          >
            <Button
              size="sm"
              variant="ghost"
              className={`h-7 px-2.5 text-xs ${
                viewMode === 'grid' ? 'bg-card shadow-2xs text-foreground' : 'text-muted-foreground'
              }`}
              onClick={() => setViewMode('grid')}
            >
              <LayoutGrid className="size-3.5 mr-1.5" /> Lưới
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className={`h-7 px-2.5 text-xs ${
                viewMode === 'table' ? 'bg-card shadow-2xs text-foreground' : 'text-muted-foreground'
              }`}
              onClick={() => setViewMode('table')}
            >
              <List className="size-3.5 mr-1.5" /> Bảng
            </Button>
          </div>
          <Button variant="outline" size="sm" onClick={() => void onRefresh()}>
            <RefreshCw className="size-3.5 mr-1.5" /> Làm mới
          </Button>
        </div>
      </div>

      {/* Thanh lọc nhanh theo Hashtag & Chủ đề — tối giản, không màu mè */}
      {trends &&
        ((trends.trending_hashtags?.length ?? 0) > 0 ||
          (trends.suggested_topics?.length ?? 0) > 0) && (
          <div className="flex flex-wrap items-center gap-1.5 text-xs">
            {(trends.trending_hashtags ?? []).slice(0, 8).map((item) => {
              const active = filters.search === item.tag
              return (
                <button
                  key={item.tag}
                  type="button"
                  onClick={() => updateFilter({ search: active ? '' : item.tag })}
                  className={`inline-flex min-h-[28px] items-center gap-1 rounded-full border px-2.5 py-0.5 text-xs transition ${
                    active
                      ? 'bg-primary text-primary-foreground border-primary font-medium'
                      : 'bg-card border-border text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <span>#{item.tag}</span>
                  <span className="font-mono tabular-nums text-[11px] opacity-60">
                    {item.video_count}
                  </span>
                </button>
              )
            })}
            {!bookmarkOnly &&
              (trends.suggested_topics ?? []).slice(0, 5).map((topic) => (
                <button
                  key={topic.keyword}
                  type="button"
                  onClick={() =>
                    onQuickCrawlTopic
                      ? void onQuickCrawlTopic(topic)
                      : updateFilter({ search: topic.keyword })
                  }
                  className="inline-flex min-h-[28px] items-center gap-1 rounded-full border border-border bg-card px-2.5 py-0.5 text-xs text-muted-foreground hover:text-foreground transition"
                  title={`Quét chủ đề ${topic.label}`}
                >
                  <span>+ {topic.label}</span>
                </button>
              ))}
          </div>
        )}

      {bookmarkOnly && collections.length > 0 && (
        <div className="flex flex-wrap items-center gap-1.5">
          <Button
            size="sm"
            variant={filters.bookmark_collection === '' ? 'default' : 'outline'}
            onClick={() => updateFilter({ bookmark_collection: '' })}
          >
            Tất cả ({total})
          </Button>
          {collections.map((col) => (
            <Button
              key={col.name}
              size="sm"
              variant={filters.bookmark_collection === col.name ? 'default' : 'outline'}
              onClick={() => updateFilter({ bookmark_collection: col.name })}
            >
              {col.name} ({col.count})
            </Button>
          ))}
        </div>
      )}

      {analyzedOnly && (
        <div className="flex flex-wrap items-center gap-1.5">
          {(
            [
              { value: '', label: `Tất cả (${total})` },
              { value: 'SENT', label: 'Đã gửi thành công' },
              { value: 'FAILED', label: 'Gửi lỗi' },
            ] as const
          ).map((tab) => (
            <Button
              key={tab.value || 'ALL'}
              size="sm"
              variant={(filters.edit_status ?? '') === tab.value ? 'default' : 'outline'}
              onClick={() => updateFilter({ edit_status: tab.value })}
            >
              {tab.label}
            </Button>
          ))}
        </div>
      )}

      {/* Bộ lọc gọn nhẹ */}
      <Card className="surface-standard">
        <CardContent className="p-3 space-y-2">
          <div className="grid gap-2 md:grid-cols-6">
            <div className={analyzedOnly || bookmarkOnly ? 'relative md:col-span-2' : 'relative md:col-span-1'}>
              <Search className="size-3.5 absolute left-2.5 top-2.5 text-muted-foreground pointer-events-none" />
              <Input
                aria-label="Tìm theo mô tả hoặc hashtag"
                className="pl-8 h-8 text-xs"
                placeholder="Tìm mô tả, hashtag..."
                value={filters.search}
                onChange={(e) => updateFilter({ search: e.target.value })}
              />
            </div>
            <select
              aria-label="Lọc theo nguồn quét"
              className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
              value={filters.target_id}
              onChange={(e) => updateFilter({ target_id: e.target.value })}
            >
              <option value="">Mọi nguồn quét</option>
              {targets.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </select>
            <select
              aria-label="Lọc theo định dạng"
              className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
              value={filters.aweme_type}
              onChange={(e) => updateFilter({ aweme_type: e.target.value })}
            >
              <option value="">Mọi định dạng</option>
              <option value="0">Video (.mp4)</option>
              <option value="68">Album ảnh</option>
            </select>
            <select
              aria-label="Lọc theo trạng thái tải"
              className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
              value={filters.download_status}
              onChange={(e) => updateFilter({ download_status: e.target.value })}
            >
              <option value="">Mọi trạng thái tải</option>
              <option value="NONE">Chưa tải</option>
              <option value="COMPLETED">Đã tải xong</option>
              <option value="FAILED">Lỗi tải</option>
            </select>
            {!bookmarkOnly && !analyzedOnly && (
              <select
                aria-label="Lọc theo trạng thái phân tích"
                className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
                value={filters.is_analyzed ?? ''}
                onChange={(e) => updateFilter({ is_analyzed: e.target.value })}
              >
                <option value="">Mọi trạng thái phân tích</option>
                <option value="true">Đã gửi phân tích</option>
                <option value="false">Chưa gửi phân tích</option>
              </select>
            )}
            <select
              aria-label="Tiêu chí sắp xếp"
              className="h-8 rounded-lg border border-input bg-card px-2.5 text-xs text-foreground outline-none"
              value={filters.sort}
              onChange={(e) => updateFilter({ sort: e.target.value })}
            >
              {analyzedOnly && <option value="edit_sent_at">Mới gửi phân tích</option>}
              <option value="crawled_at">Mới crawl gần nhất</option>
              <option value="create_time">Ngày đăng bài</option>
              <option value="duration_ms">Thời lượng</option>
              <option value="digg_count">Lượt tim</option>
            </select>
          </div>

          {selectedIds.length > 0 && (
            <div className="lg-regular flex flex-wrap items-center gap-2 rounded-xl p-2 mt-1">
              <span className="text-xs font-medium px-2 font-mono tabular-nums">
                Đã chọn {selectedIds.length}
              </span>
              {onSendToEdit && (
                <Button
                  size="sm"
                  variant="default"
                  disabled={selectedIds.some((id) => sendingEditIds.includes(id))}
                  onClick={() => {
                    void onSendToEdit(selectedIds)
                    setSelectedIds([])
                  }}
                >
                  Phân tích & Dịch ({selectedIds.length})
                </Button>
              )}
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  void onBatchDownload(selectedIds)
                  setSelectedIds([])
                }}
              >
                <Download className="size-3.5 mr-1.5" /> Tải ({selectedIds.length})
              </Button>
              <Input
                className="h-7 w-40 text-xs"
                placeholder="Nhãn Bookmark..."
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
                Bookmark
              </Button>
              <Button
                size="sm"
                variant="ghost"
                className="ml-auto"
                onClick={() => setSelectedIds([])}
              >
                Bỏ chọn
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {videos.length === 0 ? (
        <div className="py-16 text-center text-muted-foreground text-sm">
          Không tìm thấy bài đăng nào khớp bộ lọc hiện tại.
        </div>
      ) : viewMode === 'grid' ? (
        <div className="grid gap-4 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {videos.map((video) => {
            const isAlbum = video.aweme_type === 68
            const isSelected = selectedIds.includes(video.aweme_id)
            return (
              <Card
                key={video.aweme_id}
                className={`surface-standard overflow-hidden transition flex flex-col justify-between py-0 gap-0 ${
                  isSelected
                    ? 'ring-2 ring-foreground border-foreground'
                    : 'hover:border-foreground/20'
                }`}
              >
                <div>
                  <div
                    className="relative aspect-[16/10] bg-muted cursor-pointer group overflow-hidden"
                    onClick={() => onPreview(video)}
                  >
                    {video.cover_url ? (
                      <img
                        src={video.cover_url}
                        alt={video.description || video.aweme_id}
                        className="h-full w-full object-cover transition duration-300 group-hover:scale-[1.02]"
                        loading="lazy"
                      />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-muted-foreground/40">
                        <Film className="size-6" />
                      </div>
                    )}

                    {/* Top-left selection */}
                    <div
                      className="absolute top-2 left-2 z-10"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <label className="lg-clear inline-flex size-7 items-center justify-center rounded-md cursor-pointer">
                        <input
                          type="checkbox"
                          aria-label={`Chọn bài ${video.aweme_id}`}
                          checked={isSelected}
                          onChange={() => toggleSelect(video.aweme_id)}
                          className="size-3.5 rounded accent-foreground"
                        />
                      </label>
                    </div>

                    {/* Top-right bookmark */}
                    <div
                      className="absolute top-2 right-2 z-10"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        type="button"
                        aria-label={video.is_bookmarked ? 'Bỏ Bookmark' : 'Đánh dấu Bookmark'}
                        onClick={() => void onToggleBookmark(video)}
                        className="lg-clear inline-flex size-7 items-center justify-center rounded-md transition"
                      >
                        <Star
                          className={`size-3.5 ${
                            video.is_bookmarked ? 'fill-white text-white' : 'text-white/80'
                          }`}
                        />
                      </button>
                    </div>

                    {/* Bottom-left resolution */}
                    {video.width && video.height && (
                      <div className="lg-clear absolute bottom-2 left-2 rounded px-1.5 py-0.5 text-[10px] font-mono tabular-nums">
                        {video.width}×{video.height}
                      </div>
                    )}

                    {/* Bottom-right duration */}
                    <div className="lg-clear absolute bottom-2 right-2 rounded px-1.5 py-0.5 text-[11px] font-mono tabular-nums">
                      {isAlbum
                        ? `${video.image_count || 1} ảnh`
                        : formatDurationMs(video.duration_ms)}
                    </div>
                  </div>

                  <CardContent className="p-3 space-y-1.5">
                    <p
                      className="line-clamp-2 text-xs font-medium leading-relaxed text-foreground cursor-pointer hover:underline min-h-[2.25rem]"
                      onClick={() => onPreview(video)}
                      title={video.description}
                    >
                      {video.description || '(Không có mô tả)'}
                    </p>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                      <span className="truncate font-medium text-foreground/80">
                        @{video.author_nickname}
                      </span>
                      <span className="font-mono tabular-nums">
                        {formatNumber(video.digg_count)} tim
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[11px] text-muted-foreground font-mono tabular-nums">
                      <span>
                        {analyzedOnly && video.edit_sent_at
                          ? `Gửi: ${formatDateTime(video.edit_sent_at)}`
                          : formatDateTime(video.create_time)}
                      </span>
                      <span>
                        {video.edit_status === 'FAILED' ? (
                          <span className="text-destructive">Lỗi gửi</span>
                        ) : video.edit_item_id || video.edit_status === 'SENT' ? (
                          'Đã phân tích'
                        ) : video.download_status === 'COMPLETED' ? (
                          'Đã tải'
                        ) : (
                          ''
                        )}
                      </span>
                    </div>
                    {analyzedOnly && video.edit_error && (
                      <p className="text-[11px] text-destructive line-clamp-2 font-mono">
                        {video.edit_error}
                      </p>
                    )}
                  </CardContent>
                </div>

                <div className="px-3 pb-3 pt-1 flex items-center gap-1.5">
                  <Button
                    size="xs"
                    variant="secondary"
                    className="flex-1"
                    onClick={() => onPreview(video)}
                  >
                    Xem
                  </Button>
                  {!analyzedOnly && (
                    <Button
                      size="xs"
                      variant="outline"
                      className="flex-1"
                      onClick={() => void onDownloadSingle(video.aweme_id)}
                    >
                      {video.download_status === 'COMPLETED' ? 'Đã lưu' : 'Lưu'}
                    </Button>
                  )}
                  {!isAlbum && onSendToEdit && (
                    video.edit_item_id ? (
                      <>
                        <Button size="xs" variant="outline" className={analyzedOnly ? 'flex-1' : ''} asChild>
                          <a
                            href={
                              video.edit_studio_url ||
                              `${editStudioBaseUrl.replace(/\/$/, '')}/items/${video.edit_item_id}`
                            }
                            target="_blank"
                            rel="noreferrer"
                          >
                            Studio ↗
                          </a>
                        </Button>
                        {analyzedOnly && (
                          <Button
                            size="icon-xs"
                            variant="outline"
                            disabled={sendingEditIds.includes(video.aweme_id)}
                            title="Gửi phân tích lại"
                            aria-label={`Gửi phân tích lại ${video.aweme_id}`}
                            onClick={() => void onSendToEdit([video.aweme_id])}
                          >
                            <RotateCcw className="size-3.5" />
                          </Button>
                        )}
                      </>
                    ) : (
                      <Button
                        size="xs"
                        variant="outline"
                        className={analyzedOnly ? 'flex-1' : ''}
                        disabled={sendingEditIds.includes(video.aweme_id)}
                        onClick={() => void onSendToEdit([video.aweme_id])}
                      >
                        {sendingEditIds.includes(video.aweme_id)
                          ? '...'
                          : analyzedOnly
                            ? 'Gửi lại'
                            : 'Dịch'}
                      </Button>
                    )
                  )}
                  {analyzedOnly && onClearEditStatus && (
                    <Button
                      size="icon-xs"
                      variant="ghost"
                      title="Bỏ khỏi danh sách đã gửi"
                      aria-label={`Bỏ bài ${video.aweme_id} khỏi danh sách đã gửi`}
                      onClick={() => void onClearEditStatus(video.aweme_id)}
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  )}
                  <Button size="icon-xs" variant="ghost" asChild>
                    <a
                      href={video.original_url}
                      target="_blank"
                      rel="noreferrer"
                      aria-label="Mở trên Douyin"
                    >
                      <ExternalLink className="size-3.5" />
                    </a>
                  </Button>
                </div>
              </Card>
            )
          })}
        </div>
      ) : (
        <Card className="surface-standard py-0">
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-10">
                    <input
                      type="checkbox"
                      aria-label="Chọn tất cả video trên trang"
                      checked={videos.length > 0 && selectedIds.length === videos.length}
                      onChange={toggleSelectAll}
                    />
                  </TableHead>
                  <TableHead>Bài đăng</TableHead>
                  <TableHead>Tác giả</TableHead>
                  <TableHead>Thời lượng</TableHead>
                  <TableHead>{analyzedOnly ? 'Thời điểm gửi' : 'Ngày đăng'}</TableHead>
                  <TableHead>Lượt tim</TableHead>
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
                        aria-label={`Chọn bài ${video.aweme_id}`}
                        checked={selectedIds.includes(video.aweme_id)}
                        onChange={() => toggleSelect(video.aweme_id)}
                      />
                    </TableCell>
                    <TableCell className="max-w-xs">
                      <p
                        className="text-xs font-medium line-clamp-1 cursor-pointer hover:underline"
                        onClick={() => onPreview(video)}
                      >
                        {video.description || video.aweme_id}
                      </p>
                      {analyzedOnly && video.edit_error && (
                        <p className="text-[11px] text-destructive line-clamp-1 font-mono mt-0.5">
                          {video.edit_error}
                        </p>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      @{video.author_nickname}
                    </TableCell>
                    <TableCell className="text-xs font-mono tabular-nums">
                      {video.aweme_type === 68
                        ? `${video.image_count || 1} ảnh`
                        : formatDurationMs(video.duration_ms)}
                    </TableCell>
                    <TableCell className="text-xs font-mono tabular-nums text-muted-foreground">
                      {analyzedOnly && video.edit_sent_at
                        ? formatDateTime(video.edit_sent_at)
                        : formatDateTime(video.create_time)}
                    </TableCell>
                    <TableCell className="text-xs font-mono tabular-nums">
                      {formatNumber(video.digg_count)}
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-[11px] font-normal">
                        {analyzedOnly
                          ? video.edit_status === 'FAILED'
                            ? 'FAILED'
                            : 'SENT'
                          : video.download_status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right space-x-1">
                      <Button size="xs" variant="ghost" onClick={() => onPreview(video)}>
                        Xem
                      </Button>
                      {video.edit_item_id && (
                        <Button size="xs" variant="outline" asChild>
                          <a
                            href={
                              video.edit_studio_url ||
                              `${editStudioBaseUrl.replace(/\/$/, '')}/items/${video.edit_item_id}`
                            }
                            target="_blank"
                            rel="noreferrer"
                          >
                            Studio ↗
                          </a>
                        </Button>
                      )}
                      {analyzedOnly && onSendToEdit && (
                        <Button
                          size="xs"
                          variant="outline"
                          disabled={sendingEditIds.includes(video.aweme_id)}
                          onClick={() => void onSendToEdit([video.aweme_id])}
                        >
                          Gửi lại
                        </Button>
                      )}
                      {analyzedOnly && onClearEditStatus ? (
                        <Button
                          size="xs"
                          variant="ghost"
                          onClick={() => void onClearEditStatus(video.aweme_id)}
                        >
                          Bỏ
                        </Button>
                      ) : (
                        <Button
                          size="xs"
                          variant="outline"
                          onClick={() => void onDownloadSingle(video.aweme_id)}
                        >
                          Tải
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      <div className="flex items-center justify-between pt-2">
        <span className="text-xs text-muted-foreground font-mono tabular-nums">
          Trang {filters.page} / {totalPages} ({total} mục)
        </span>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            disabled={filters.page <= 1}
            onClick={() => onFiltersChange({ ...filters, page: filters.page - 1 })}
          >
            Trước
          </Button>
          <Button
            size="sm"
            variant="outline"
            disabled={filters.page >= totalPages}
            onClick={() => onFiltersChange({ ...filters, page: filters.page + 1 })}
          >
            Sau
          </Button>
        </div>
      </div>
    </div>
  )
}
