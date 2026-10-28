import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { App } from './App'
import { formatDurationMs } from './lib/api'

describe('Douyin Crawler Left Sidebar Dashboard', () => {
  afterEach(() => {
    cleanup()
  })
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
      const url = typeof input === 'string' ? input : input.toString()
      if (url.includes('/api/browser/status')) {
        return new Response(JSON.stringify({ status: 'AUTHENTICATED' }))
      }
      if (url.includes('/api/scheduler/status')) {
        return new Response(JSON.stringify({ running: true, paused: false, jobs_count: 2 }))
      }
      if (url.includes('/api/stats')) {
        return new Response(
          JSON.stringify({
            total_videos: 12,
            downloaded_videos: 5,
            bookmarked_videos: 3,
            active_targets: 2,
            total_targets: 2,
            running_jobs: 0,
            completed_jobs: 8,
            failed_jobs: 1,
          }),
        )
      }
      if (url.includes('/api/targets')) {
        return new Response(
          JSON.stringify([
            {
              id: 1,
              name: 'Kênh Thời Trang',
              target_type: 'CHANNEL',
              target_value: 'sec-fashion',
              cron_expr: '0 */6 * * *',
              schedule_type: 'INTERVAL',
              schedule_config: { every: 45, unit: 'minutes' },
              run_at: null,
              auto_download: true,
              max_items_per_run: 50,
              is_active: true,
              last_status: 'SUCCESS',
              last_run_at: '2026-10-27T01:00:00Z',
              next_run_at: '2026-10-27T01:45:00Z',
              scheduled: true,
            },
          ]),
        )
      }
      if (url.includes('/api/bookmarks/collections')) {
        return new Response(JSON.stringify([{ name: 'Idea kịch bản', count: 2 }]))
      }
      if (url.includes('/api/trends')) {
        return new Response(
          JSON.stringify({
            trending_hashtags: [{ tag: 'ootd', video_count: 5, total_digg: 12000 }],
            trending_music: [{ title: 'Nhạc nền hot', author: 'DJ A', video_count: 3, total_digg: 8000 }],
            suggested_topics: [{ keyword: '穿搭', label: 'Phối đồ OOTD (穿搭)', category: 'Thời trang' }],
          }),
        )
      }
      if (url.includes('/api/videos')) {
        return new Response(
          JSON.stringify({
            items: [
              {
                aweme_id: '7355555555555555555',
                target_id: 1,
                source_names: ['Kênh Thời Trang'],
                aweme_type: 0,
                description: 'Video mẫu có thời lượng 01:35',
                hashtags: ['ootd', 'douyin'],
                create_time: '2026-10-26T14:30:00Z',
                crawled_at: '2026-10-26T15:00:00Z',
                author_sec_uid: 'sec-fashion',
                author_nickname: 'Fashionista',
                author_avatar: null,
                digg_count: 1500,
                comment_count: 120,
                share_count: 45,
                collect_count: 310,
                duration_ms: 95000,
                width: 1080,
                height: 1920,
                music_title: 'Nhạc nền hot',
                music_author: 'DJ A',
                image_count: 0,
                cover_url: null,
                original_url: 'https://www.douyin.com/video/7355555555555555555',
                download_status: 'COMPLETED',
                video_local_path: 'downloads/Fashionista/2026-10-26/7355555555555555555.mp4',
                downloaded_at: '2026-10-26T15:05:00Z',
                download_error: null,
                is_bookmarked: true,
                bookmarked_at: '2026-10-26T15:10:00Z',
                bookmark_collection: 'Idea kịch bản',
                bookmark_note: 'Góc quay đẹp',
              },
            ],
            total: 1,
            page: 1,
            page_size: 24,
          }),
        )
      }
      if (url.includes('/api/logs')) {
        return new Response(
          JSON.stringify({
            items: [
              {
                id: 10,
                target_id: 1,
                target_name: 'Kênh Thời Trang',
                job_type: 'TARGET_CRAWL',
                trigger_type: 'SCHEDULED',
                input_summary: 'CHANNEL: Kênh Thời Trang',
                started_at: '2026-10-27T01:00:00Z',
                finished_at: '2026-10-27T01:00:12Z',
                duration_ms: 12000,
                status: 'SUCCESS',
                new_videos_count: 4,
                updated_videos_count: 2,
                error_message: null,
              },
            ],
            total: 1,
            page: 1,
            page_size: 50,
          }),
        )
      }
      if (url.includes('/api/settings/anti-bot')) {
        return new Response(
          JSON.stringify({
            preset: 'BALANCED',
            scroll_delay_min_ms: 1500,
            scroll_delay_max_ms: 3500,
            download_delay_min_ms: 500,
            download_delay_max_ms: 1500,
            cooldown_between_targets_sec: 10,
            stealth_mode: true,
            human_scroll: true,
            auto_stop_on_captcha: true,
            max_pages_per_run: 25,
            user_agent: null,
            proxy_url: null,
            updated_at: '2026-10-27T00:00:00Z',
          }),
        )
      }
      return new Response(JSON.stringify({}))
    })
  })

  it('formats video duration in MM:SS and HH:MM:SS', () => {
    expect(formatDurationMs(15000)).toBe('00:15')
    expect(formatDurationMs(95000)).toBe('01:35')
    expect(formatDurationMs(3661000)).toBe('01:01:01')
  })

  it('navigates across Left Sidebar sections and displays video metadata and duration', async () => {
    const user = userEvent.setup()
    render(<App />)

    expect(
      await screen.findByText('Tổng quan Hệ thống Douyin Crawler'),
    ).toBeInTheDocument()
    expect(await screen.findByText('Video mẫu có thời lượng 01:35')).toBeInTheDocument()

    // Navigate to Library
    await user.click(screen.getByRole('button', { name: /Thư viện Video/i }))
    expect(
      await screen.findByText('Thư viện Bài đăng Đã Crawl'),
    ).toBeInTheDocument()
    expect(screen.getAllByText('01:35').length).toBeGreaterThan(0)
    expect(screen.getByText('1080×1920')).toBeInTheDocument()

    // Navigate to Bookmarks
    await user.click(screen.getByRole('button', { name: /Đã Bookmark/i }))
    expect(await screen.findByText('Kho Video Đã Bookmark')).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Đồng bộ mục Đã lưu từ Douyin/i }),
    ).toBeInTheDocument()

    // Navigate to Analyzed Videos
    await user.click(screen.getByRole('button', { name: /Đã gửi Phân tích/i }))
    expect(
      await screen.findByText('Video Đã Đẩy Sang Phân Tích'),
    ).toBeInTheDocument()

    // Navigate to Studio Settings (IP & Port)
    await user.click(screen.getByRole('button', { name: /Server Phân tích/i }))
    expect(
      await screen.findByText('Cấu hình Server Phân tích (IP & Port)'),
    ).toBeInTheDocument()

    // Navigate to Single Crawl
    await user.click(screen.getByRole('button', { name: /Crawl 1 ID \/ Link/i }))
    expect(
      await screen.findByText('Crawl theo ID / Link Chia Sẻ Douyin'),
    ).toBeInTheDocument()

    // Navigate to Targets & Scheduler
    await user.click(screen.getByRole('button', { name: /Mục tiêu & Hẹn giờ/i }))
    expect(
      await screen.findByText('Mục tiêu Quét & Thiết lập Hẹn Giờ'),
    ).toBeInTheDocument()
    expect(screen.getByText('Mỗi 45 phút')).toBeInTheDocument()

    // Navigate to History
    await user.click(screen.getByRole('button', { name: /Lịch sử chạy/i }))
    expect(
      await screen.findByText('Lịch sử Chạy Chi Tiết (Execution History)'),
    ).toBeInTheDocument()
    expect(screen.getByText('12.0s')).toBeInTheDocument()

    // Navigate to Anti-Bot
    await user.click(screen.getByRole('button', { name: /Cấu hình Chống Bot/i }))
    expect(
      await screen.findByText('Thiết lập Chống Bot (Anti-Bot & Stealth)'),
    ).toBeInTheDocument()
  })

  it('requires admin login when unauthenticated, allows password change, and logs out', async () => {
    let loggedIn = false
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = typeof input === 'string' ? input : input.toString()
      const method = init?.method || 'GET'
      if (url.includes('/api/auth/status')) {
        return new Response(
          JSON.stringify({
            authenticated: loggedIn,
            username: loggedIn ? 'admin' : null,
          }),
        )
      }
      if (url.includes('/api/auth/login') && method === 'POST') {
        loggedIn = true
        return new Response(
          JSON.stringify({
            authenticated: true,
            username: 'admin',
            token: 'test-session-token-123',
          }),
        )
      }
      if (url.includes('/api/auth/password') && method === 'PUT') {
        return new Response(
          JSON.stringify({
            authenticated: true,
            username: 'trungadmin',
            token: 'test-session-token-456',
          }),
        )
      }
      if (url.includes('/api/auth/logout') && method === 'POST') {
        loggedIn = false
        return new Response(
          JSON.stringify({
            authenticated: false,
            username: null,
          }),
        )
      }
      if (url.includes('/api/browser/status')) {
        return new Response(JSON.stringify({ status: 'AUTHENTICATED' }))
      }
      if (url.includes('/api/scheduler/status')) {
        return new Response(JSON.stringify({ running: true, paused: false, jobs_count: 0 }))
      }
      if (url.includes('/api/stats')) {
        return new Response(
          JSON.stringify({
            total_videos: 0,
            downloaded_videos: 0,
            bookmarked_videos: 0,
            active_targets: 0,
            total_targets: 0,
            running_jobs: 0,
            completed_jobs: 0,
            failed_jobs: 0,
          }),
        )
      }
      if (url.includes('/api/targets')) {
        return new Response(JSON.stringify([]))
      }
      if (url.includes('/api/videos')) {
        return new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 24 }))
      }
      if (url.includes('/api/logs')) {
        return new Response(JSON.stringify({ items: [], total: 0, page: 1, page_size: 50 }))
      }
      return new Response(JSON.stringify({}))
    })

    const user = userEvent.setup()
    render(<App />)

    // 1. Shows Login screen initially
    expect(await screen.findByText('Đăng nhập Quản trị')).toBeInTheDocument()

    await user.type(screen.getByLabelText(/Tên đăng nhập/i), 'admin')
    await user.type(screen.getByLabelText(/Mật khẩu/i), 'admin123')
    await user.click(screen.getByRole('button', { name: /Đăng nhập hệ thống/i }))

    // 2. Enters Dashboard after login
    expect(
      await screen.findByText('Tổng quan Hệ thống Douyin Crawler'),
    ).toBeInTheDocument()

    // 3. Navigate to Server Phân tích / Settings to see Admin Password card
    await user.click(screen.getByRole('button', { name: /Server Phân tích/i }))
    expect(
      await screen.findByText('Tài khoản Quản trị (Đổi mật khẩu)'),
    ).toBeInTheDocument()

    // 4. Click Logout in Sidebar footer
    await user.click(screen.getByRole('button', { name: /Đăng xuất/i }))
    expect(await screen.findByText('Đăng nhập Quản trị')).toBeInTheDocument()
  })
})
