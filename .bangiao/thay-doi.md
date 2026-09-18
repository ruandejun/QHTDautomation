# BIÊN BẢN THAY ĐỔI MÃ NGUỒN (AGENT 2 - CODER)

- **Người thực hiện:** Agent 2 (Coder)
- **Ngày thực hiện:** 2026-09-18
- **Nhánh triển khai:** `feature/tiktok-maximum-attempts-auto-retry`
- **Tài liệu tham chiếu:** `.bangiao/ke-hoach.md`
- **Phiên bản nhị phân:** `MunAutomationDesktop/MunAutomation.exe` (Release Build)

---

## 1. Tóm tắt các thay đổi đã thực hiện

### 1.1. Module `qhtd-farm-rust/src/browser_nurture.rs`
- **Nâng cấp phát hiện lỗi đăng nhập TikTok (`err_expr`):**
  * Quét toàn diện các toast nổi của TikTok: `[data-e2e="toast"]`, `.tiktok-toast`, `.toast-message`, `.toast`, `[role="status"]`.
  * Quét các chuỗi nhận diện: `maximum number of attempts reached`, `try again later`, `too many attempts`, `đã đạt số lần thử tối đa`, `vui lòng thử lại sau`.
- **Tự động đóng trình duyệt giải phóng tài nguyên trong `set_error`:**
  * Bổ sung gọi trực tiếp `crate::cdp_browser::stop_cdp_profile(pid)` khi gặp `is_max_attempts` và các lỗi nghiêm trọng.
  * Triệt tiêu hoàn toàn hiện tượng Chrome mồ côi chạy ngầm, rò rỉ RAM, xung đột DevTools port và treo tool.
- **Xây dựng Background Auto-Retry Scheduler (`start_auto_retry_scheduler`):**
  * Định kỳ mỗi 60 giây quét toàn bộ profiles có trạng thái `Rate limit (Chờ 1h)`.
  * Khi `now_epoch >= retry_after_epoch`: Tự động khởi động lại chu trình đăng nhập TikTok cho profile đó.
  * Áp dụng khoảng giãn cách 15s giữa các profile để chống quá tải kết nối (connection storm).

### 1.2. Module `qhtd-farm-rust/src/api.rs`
- **Bổ sung hàm hỗ trợ:**
  * `pub fn get_all_profiles() -> Vec<BrowserProfile>` để phục vụ scheduler quét profile tự động.
- **Thêm 2 REST Endpoints phản hồi tín hiệu thời gian thực từ DOM Chrome:**
  * `POST /api/browser/tiktok/rate-limit-signal`: Nhận tín hiệu khi trình duyệt bung toast `Maximum attempts`, lập tức cập nhật trạng thái `Rate limit (Chờ 1h)`, đặt `retry_after_epoch = now + 3600`, và gọi `stop_cdp_profile` tắt Chrome ngay lập tức.
  * `POST /api/browser/tiktok/login-success-signal`: Nhận tín hiệu khi đăng nhập thành công (phát hiện avatar profile), tự động sao lưu thin profile và chuyển trạng thái sang `Đã đăng nhập sẵn (Sẵn sàng)`.

### 1.3. Module `qhtd-farm-rust/src/cdp_browser.rs`
- **Tiêm script giám sát tự động (`monitor_script`) vào trang TikTok Login:**
  * Kiểm tra định kỳ 1.5s trực tiếp bên trong DOM của tab đăng nhập.
  * Tự động gửi POST request về backend khi phát hiện Toast Rate Limit hoặc Avatar thành công.

### 1.4. Module `qhtd-farm-rust/src/main.rs`
- Kích hoạt `browser_nurture.clone().start_auto_retry_scheduler()` ngay khi server khởi động.

---

## 2. Bàn giao sang Agent 3 (Tester)
Mã nguồn đã biên dịch release tối ưu hóa (29.33s), tệp nhị phân đã đồng bộ sang `MunAutomationDesktop/MunAutomation.exe`. Đề nghị Agent 3 tiến hành viết test suite kiểm định độc lập.
