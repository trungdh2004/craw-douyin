# 03: Quản lý Bookmark Nội bộ & Đồng bộ Danh sách Đã lưu (`COLLECT`) từ Douyin

**What to build:** Người vận hành có thể đánh dấu Bookmark (Gắn sao) lẻ hoặc hàng loạt cho các bài đăng trên Dashboard, gắn nhãn bộ sưu tập (`bookmark_collection`) và ghi chú cá nhân (`bookmark_note`), quản lý và tải hàng loạt trong trang Đã Bookmark, cũng như đồng bộ các bài đã lưu (`COLLECT`) từ tài khoản Douyin đang đăng nhập về thẳng danh sách Bookmark.

**Blocked by:** 02: Thư viện Bài đăng Giàu Metadata, Thời lượng Video (`MM:SS`) & Modal Xem Trước Media.

**Status:** ready-for-agent

- [x] Hỗ trợ bật/tắt Bookmark và cập nhật `bookmark_collection`, `bookmark_note` cho từng bài đăng (`PATCH /api/videos/{aweme_id}/bookmark`) hoặc hàng loạt (`POST /api/videos/batch-bookmark`).
- [x] `GET /api/videos` hỗ trợ lọc theo `is_bookmarked` và `bookmark_collection`; bổ sung danh sách các nhãn bộ sưu tập hiện có để lọc nhanh trên giao diện.
- [x] Hỗ trợ loại mục tiêu `COLLECT` và endpoint `POST /api/bookmarks/sync-douyin` để quét danh sách video đã lưu từ tài khoản Douyin đang đăng nhập, tự động gắn `is_bookmarked = True`.
- [x] Giao diện trang Đã Bookmark trên Sidebar cho phép lọc theo nhãn bộ sưu tập, chỉnh sửa ghi chú/nhãn, đồng bộ từ Douyin và tải hàng loạt các video đã Bookmark.
- [x] Kiểm thử tích hợp xác nhận thao tác Bookmark lẻ/hàng loạt, lọc theo nhãn bộ sưu tập và đồng bộ mục `COLLECT` từ Douyin.
