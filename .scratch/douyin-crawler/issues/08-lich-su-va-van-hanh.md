# 08: Hoàn thiện lịch sử chạy và trải nghiệm vận hành

**What to build:** Người vận hành có thể theo dõi các phiên quét gần nhất trên Dashboard và khởi chạy hệ thống theo một quy trình rõ ràng gồm PostgreSQL trong Docker cùng dịch vụ FastAPI, Scheduler và Web Dashboard hợp nhất.

**Blocked by:** 01: Khởi tạo ứng dụng và lưu trữ Douyin; 03: Quản lý mục tiêu và tự động thu thập bài mới theo kênh; 04: Quản lý mục tiêu và thu thập kết quả theo từ khóa.

**Status:** ready-for-agent

- [ ] Dashboard hiển thị lịch sử gần nhất với mục tiêu, thời gian bắt đầu/kết thúc, trạng thái, số bài mới, số bài cập nhật và thông báo lỗi.
- [ ] Lịch sử có thứ tự ổn định, phân trang được và phản ánh cả tác vụ theo lịch lẫn Run Now.
- [ ] Cấu hình mẫu và hướng dẫn vận hành nêu rõ cách chuẩn bị môi trường, khởi chạy PostgreSQL, cài Chromium và chạy dịch vụ hợp nhất.
- [ ] Quy trình khởi động lại không làm mất mục tiêu, metadata, lịch sử, cover, media đã tải hoặc persistent browser profile.
- [ ] Kiểm thử smoke xác nhận dịch vụ khởi động, Scheduler được nạp mục tiêu đang hoạt động và Dashboard truy cập được.
