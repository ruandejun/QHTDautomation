# NHẬT KÝ THAY ĐỔI (AGENT 2 - CODER)

- **Ngày thực hiện:** 2026-09-20
- **Nhánh triển khai:** `feature/tiktok-element-driven-pipeline`
- **Người thực hiện:** Agent 2 (Coder)

---

## 1. Các thay đổi cốt lõi trong `qhtd-farm-rust/src/browser_nurture.rs`

### 1.1. Tăng Timeout CDP lên 20s & Loại Bỏ Hoàn Toàn `unwrap()` Gây Crash
- **Khắc phục timeout giả:** Tăng thời gian chờ phản hồi CDP trong `CdpClient::call` từ `8s` lên `20s`. Khi SOCKS5 proxy có độ trễ cao hoặc đang tải asset nặng, kết nối WebSocket CDP không còn bị timeout oan.
- **Loại bỏ nguy cơ Panic/Crash (Zero Panic Guarantee):** Thay thế đoạn `c69_acc.as_ref().unwrap()` bằng kiểm tra `acc_opt.is_none()` an toàn. Nếu thiếu mật khẩu hoặc tài khoản không tồn tại, hàm dừng lại an toàn, đóng browser và giải phóng tài nguyên.

### 1.2. Cơ chế Element-Driven State Transition (Kiểm tra phần tử DOM chuyển bước)
Đúng theo kiến trúc anh Tony chỉ đạo:
- **Bước 1 (Kiểm tra IP SOCKS5 tại iphey.com):**
  * Tự động trích xuất IP proxy mục tiêu qua hàm `extract_ip_from_proxy_string(&profile.proxy_string)`.
  * Điều hướng mở `https://iphey.com` và polling kiểm tra sự xuất hiện của IP trên `document.body.innerText` (mỗi 1.5s).
  * **Ngay khi thấy IP xuất hiện -> Ghi log xác nhận proxy sống và CHUYỂN NGAY SANG TIKTOK!** Không phải chờ trang iphey tải hết 100% các script nặng khác!
- **Bước 2 (Vào TikTok vài giây -> Mở link kiểm tra Profile):**
  * Điều hướng `https://www.tiktok.com`, chờ 3s cho cookie và proxy khởi tạo.
  * Điều hướng thẳng vào link trang cá nhân: `https://www.tiktok.com/profile`.
- **Bước 3 (Kiểm tra phần tử Profile/Login):**
  * Polling kiểm tra phần tử trên trang Profile:
    - Nếu xuất hiện nút Log in hoặc URL bị chuyển về `/login` -> Nhận diện cần đăng nhập, chuyển sang luồng Login C69.
    - Nếu có username và session cookie -> Nhận diện đã đăng nhập sẵn.
- **Bước 4 (Kiểm tra & Cập nhật Avatar + Username):**
  * Quét ảnh avatar: Nếu mặc định -> Tự upload avatar chân dung tự nhiên bằng `get_or_create_clean_avatar(pid)`.
  * Quét username: Nếu mặc định (`user...`) -> Tự đổi username sạch (bỏ tiền tố số C69 `3_`).
- **Bước 5 (Lướt FYP):**
  * Điều hướng `https://www.tiktok.com/foryou?lang=en`.
  * Lướt video và tương tác 35s - 55s (khoảng 30s - 1 phút) rồi tự động đóng trình duyệt.

---

## 2. Kết quả Build
- Đã biên dịch release thành công: `cargo build --release` (29.81s).
- Đã ghi đè file thực thi: `MunAutomationDesktop/MunAutomation.exe`.
