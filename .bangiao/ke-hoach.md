# KẾ HOẠCH KỸ THUẬT: XỬ LÝ LỖI TIKTOK LOGIN 'MAXIMUM ATTEMPTS', TỰ ĐỘNG ĐÓNG BROWSER & AUTO-RETRY SAU 1 GIỜ

- **Người lập kế hoạch:** Agent 1 (Planner)
- **Ngày lập:** 2026-09-18
- **Nhánh triển khai:** `feature/tiktok-maximum-attempts-auto-retry`
- **Tài liệu tham chiếu:** Yêu cầu từ anh Tony ngày 2026-09-18 16:51

---

## 1. Mục tiêu kỹ thuật
1. **Phát hiện triệt để lỗi `Maximum number of attempts reached`** ở cả 2 luồng:
   - Luồng 1: Nuôi tự động TikTok (`run_nurture_worker` trong `browser_nurture.rs`).
   - Luồng 2: Mở profile từ Dashboard (`check_and_handle_tiktok_login_cdp` trong `cdp_browser.rs`).
   - Hỗ trợ đa ngôn ngữ (Tiếng Anh + Tiếng Việt) và mọi vị trí hiển thị (Toast, Form alert, Error container, Modal).
2. **Dọn dẹp sạch sẽ & Đóng trình duyệt an toàn (Graceful Shutdown):**
   - Khi phát hiện lỗi Rate limit / Maximum: lập tức ghi nhận trạng thái `Rate limit (Chờ 1h)`, đặt `retry_after_epoch = now + 3600`.
   - Gọi ngay `crate::cdp_browser::stop_cdp_profile(pid)` để tắt hoàn toàn cửa sổ Chrome, dọn dẹp lockfile và giải phóng bridge SOCKS5, triệt tiêu tình trạng treo tool / crash / rò rỉ bộ nhớ.
3. **Cơ chế Auto-Retry Scheduler sau 1 giờ:**
   - Xây dựng background loop định kỳ (mỗi 60s) quét các profile đang ở trạng thái `Rate limit (Chờ 1h)`.
   - Khi thời gian hiện tại `now >= retry_after_epoch`:
     * Tự động khởi động lại chu trình đăng nhập cho profile đó.
     * Tiếp tục lặp lại: Thử đăng nhập -> Nếu vẫn bị Maximum -> Đóng browser, chờ tiếp 1h -> Thử lại tiếp... Cho tới khi nào đăng nhập thành công.
     * Khi đăng nhập thành công: Lưu cookies vào tài khoản C69 + backup thin profile (`backup_thin_profile(pid)`). Đổi trạng thái sang `Đã đăng nhập sẵn (Sẵn sàng)`. Từ lần sau mở lên dùng ngay, không bao giờ cần login nữa!

---

## 2. Phân tích nguyên nhân gốc rễ (RCA)
- **Tại sao tool tưởng như bị crash/không nhận ra:**
  1. Trong `cdp_browser.rs` (hàm `check_and_handle_tiktok_login_cdp`): Chỉ điền thông tin và OTP rồi dừng, không có vòng lặp lắng nghe response của TikTok sau submit. Nếu TikTok bung toast "Maximum number of attempts reached", không có code nào bắt sự kiện này.
  2. Trong `browser_nurture.rs` (hàm `set_error`): Khi phát hiện lỗi, hàm `set_error` chỉ gán cờ `run_flag = false` và cập nhật JSON, **KHÔNG HỀ GỌI `stop_cdp_profile(pid)`**. Cửa sổ Chrome vẫn mở, cổng WebSocket vẫn giữ kết nối, các file `SingletonLock` chưa được giải phóng -> Tool bị treo cửa sổ cũ, người dùng nhìn vào thấy đơ.
  3. Thiếu scheduler tự động: Sau khi đặt `retry_after_epoch = now + 3600`, không có thread nào kích hoạt lại worker khi hết hạn 1h.

---

## 3. Thiết kế giải pháp chi tiết

### Chặng A: Cải tiến bộ phát hiện lỗi TikTok Login (`detect_tiktok_login_error_cdp`)
Xây dựng hàm dùng chung hoặc script JS quét toàn diện:
- Các chuỗi nhận diện:
  * `"maximum number of attempts reached"`
  * `"try again later"`
  * `"too many attempts"`
  * `"đã đạt số lần thử tối đa"`
  * `"vui lòng thử lại sau"`
  * `"something went wrong"`
- Các selectors cần quét:
  * Toast container: `div[data-e2e="toast"]`, `.tiktok-toast`, `.toast-message`
  * Error container: `[role="alert"]`, `.tiktok-input-error`, `[class*="error-container"]`, `[class*="error-message"]`, `.error-text`
  * Body text toàn diện: `document.body ? document.body.innerText : ''`

### Chặng B: Dọn dẹp & Tắt trình duyệt khi gặp Maximum Attempts
Trong `set_error` của `browser_nurture.rs`:
- Sau khi cập nhật trạng thái `Rate limit (Chờ 1h)` và `retry_after_epoch`:
- Gọi `crate::cdp_browser::stop_cdp_profile(pid);`
- Đồng thời gửi thông báo log: `🛑 [Profile #{}] Đã tự động đóng trình duyệt an toàn để giải phóng tài nguyên. Sẽ tự động thử đăng nhập lại sau 1 giờ.`

Trong `check_and_handle_tiktok_login_cdp` của `cdp_browser.rs`:
- Bổ sung vòng lặp 15s sau khi submit form để lắng nghe kết quả:
  * Nếu thành công: lưu cookies, backup thin profile.
  * Nếu gặp Maximum attempts: cập nhật `update_profile_nurture_status(pid, "Rate limit (Chờ 1h)", ...)`, đặt `retry_after_epoch`, và gọi `stop_cdp_profile(pid)`.

### Chặng C: Background Auto-Retry Scheduler sau 1 giờ (`tiktok_rate_limit_scheduler`)
Trong `browser_nurture.rs` hoặc `main.rs`:
- Khởi chạy một tokio background task vĩnh viễn:
```rust
tokio::spawn(async move {
    loop {
        tokio::time::sleep(Duration::from_secs(60)).await;
        // Quét danh sách profiles
        // Nếu profile có retry_after_epoch <= now và status chứa "Rate limit" hoặc "Chờ 1h":
        // Tự động kích hoạt lại chu trình đăng nhập qua start_nurture
    }
});
```

---

## 4. Kế hoạch kiểm thử (Tester Plan)
1. **Unit/Integration Test:**
   - Giả lập trường hợp trang login hiển thị toast "Maximum number of attempts reached. Try again later."
   - Xác minh tool nhận diện chính xác mã lỗi `is_max_attempts`.
   - Xác minh `retry_after_epoch` được ghi nhận đúng `now + 3600`.
   - Xác minh Chrome process của profile bị terminate và lockfile được dọn dẹp sạch sẽ (không còn cửa sổ treo).
2. **Scheduler Test:**
   - Test scheduler kích hoạt tự động khi `retry_after_epoch` đến hạn.
3. **Happy Path Test:**
   - Khi login thành công: Xác nhận cookies được sync và thin profile được backup, trạng thái chuyển sang sẵn sàng.

---

## 5. Rủi ro & Giải pháp phòng ngừa
- **Rủi ro:** Khi auto-retry sau 1h, nếu nhiều profile cùng hết hạn cùng lúc có thể gây nghẽn mạng/CPU.
- **Giải pháp:** Áp dụng jitter/staggering (mỗi profile cách nhau 15-30 giây) khi auto-retry để phân tải mượt mà.
