# NHẬT KÝ THAY ĐỔI (AGENT 2 - CODER)

- **Ngày thực hiện:** 2026-09-20
- **Nhánh triển khai:** `feature/tiktok-nurture-pipeline-grid-layout`
- **Người thực hiện:** Agent 2 (Coder)

---

## 1. Danh sách các file thay đổi

### 1.1. `qhtd-farm-rust/src/cdp_browser.rs`
- **Kích thước cửa sổ chuẩn Smartphone:** Cập nhật hàm `calculate_grid_window_bounds`: khi `is_mobile == true`, kích thước cố định là **`width = 375px, height = 820px`** (tỉ lệ 9:19.5 chuẩn smartphone iPhone 14/15/16 Pro và Android Pixel/Galaxy).
- **Chrome App Mode:** Trong `launch_cdp_profile_with_bounds`, khi `is_mobile == true`, kích hoạt cờ `--app={start_url}` thay vì `--new-window` và `about:blank`. Cờ `--app` biến Chrome thành cửa sổ ứng dụng độc lập, loại bỏ thanh tab, thanh omnibox, thanh extension, và loại bỏ giới hạn cứng 516px của Windows.
- **Khớp khít Viewport App Mode:** Cập nhật `Emulation.setDeviceMetricsOverride` với `v_width = win_w (375)`, `v_height = win_h - 35 (785)`, `"fitWindow": true` để nội dung hiển thị tràn viền chuẩn xác 100%.

### 1.2. `qhtd-farm-rust/src/browser_nurture.rs`
- **Tái cấu trúc Step 1: Kiểm tra Login 10s:**
  * Mở TikTok và lắng nghe DOM trong 10 giây.
  * Quét sự xuất hiện của các nút/thẻ có chứa text hoặc attribute liên quan tới `"Log in"`, `"Đăng nhập"`, `data-e2e="top-login-button"`, `href*="/login"`.
  * Quét menu user profile (`[data-e2e="profile-icon"]`, `[data-e2e="inbox-icon"]`) và kiểm tra cookies `sessionid` / `sessionid_ss` từ CDP WebSocket.
  * **Nếu CÓ nút Login hoặc chưa có phiên:** Xác định tài khoản chưa login -> Cập nhật log và tiến hành quy trình login tự động (điền form, submit, kiểm tra OTP/Rate limit).
  * **Nếu KHÔNG CÓ nút Login:** Xác định tài khoản đã đăng nhập sẵn -> Cập nhật log: `✅ Không thấy nút Login (Tài khoản đã đăng nhập sẵn)! Bắt đầu nuôi video...`.
- **Tái cấu trúc Step 2: Nuôi tương tác từ 30s - 1 phút:**
  * Khởi tạo `nurture_start = tokio::time::Instant::now()`.
  * Đặt mục tiêu thời lượng ngẫu nhiên `target_duration_secs = rand(35..=55)` (chuẩn 30s - 1 phút theo đúng chỉ đạo của anh Tony).
  * Xem 4-6 video (mỗi video 6-10s), thả tim (Like ~65%), chia sẻ (Share/Copy link ~30%), bình luận (Comment ~20%).
  * Khi `elapsed >= target_duration_secs`: Thoát khỏi vòng lặp nuôi và cập nhật status `Đã nuôi thành công`.
- **Tự động đóng trình duyệt ngay lập tức khi nuôi xong:**
  * Tận dụng cơ chế RAII `SlotGuard`: Khi hàm worker return sau 30s - 1 phút, destructor của `_guard` tự động kích hoạt `crate::cdp_browser::stop_cdp_profile(pid)` để tắt hoàn toàn trình duyệt Chrome, dọn dẹp tiến trình và giải phóng slot trên màn hình.

---

## 2. Kết quả Build
- Đã biên dịch release thành công: `cargo build --release` (32.13s).
- Đã sao chép file chạy tối ưu vào: `MunAutomationDesktop/MunAutomation.exe`.
