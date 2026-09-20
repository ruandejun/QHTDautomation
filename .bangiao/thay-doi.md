# NHẬT KÝ THAY ĐỔI (AGENT 2 - CODER)

- **Ngày thực hiện:** 2026-09-20
- **Nhánh triển khai:** `feature/tiktok-avatar-username-strict-login`
- **Người thực hiện:** Agent 2 (Coder)

---

## 1. Các thay đổi trong `qhtd-farm-rust/src/browser_nurture.rs`

### 1.1. Khắc phục triệt để lỗi bỏ qua Login (Strict /profile Verification)
- **Cơ chế cũ:** Kiểm tra DOM mập mờ trên trang chủ TikTok khiến thẻ sidebar `<a href="/@" data-e2e="nav-profile">Profile</a>` bị nhận diện nhầm thành "đã đăng nhập", dẫn đến việc hệ thống bỏ qua bước login và vào FYP lướt video với tư cách khách vãng lai.
- **Cơ chế mới:**
  * Điều hướng trực tiếp tới `https://www.tiktok.com/profile`.
  * TikTok server sẽ tự động redirect về `https://www.tiktok.com/login...` nếu chưa có phiên đăng nhập hợp lệ.
  * Kiểm tra đồng thời:
    1. URL không chứa `/login`.
    2. Không có nút "Log in" / "Đăng nhập" (`top-login-button`).
    3. Trình duyệt bắt buộc phải có Cookie `sessionid` hoặc `sessionid_ss` có độ dài > 15 ký tự.
    4. Trích xuất thành công `username` từ URL (`tiktok.com/@<username>`).
- **Nghiêm cấm tuyệt đối nuôi khách vãng lai:**
  * Nếu tài khoản chưa đăng nhập và không có mật khẩu C69 -> **DỪNG LẠI NGAY LẬP TỨC (`return`), ĐÓNG TRÌNH DUYỆT BẰNG `SlotGuard` VÀ BÁO LỖI RÕ RÀNG!**
  * Nếu có mật khẩu C69 -> Tiến hành quy trình đăng nhập tự động. Sau khi đăng nhập, bắt buộc xác thực lại lần 2 qua `https://www.tiktok.com/profile`. Nếu vẫn chưa đăng nhập thành công -> **DỪNG LẠI VÀ ĐÓNG TRÌNH DUYỆT!**

### 1.2. Tính năng Kiểm tra & Tự động cập nhật Avatar + Đổi Username (Step 4B)
- Sau khi đã đăng nhập 100%, hệ thống mở trang cá nhân `https://www.tiktok.com/profile` và quét thông tin tài khoản:
  * **Kiểm tra Avatar:**
    - Quét ảnh đại diện `avatarImg = document.querySelector('[data-e2e="user-avatar"] img')`.
    - Nếu ảnh là avatar mặc định (chứa `default-avatar`, `musically-maliva-obj/default`, hoặc rỗng) -> Xác định `need_upload_avatar = true`.
    - Tải/chuẩn bị ảnh avatar chân dung tự nhiên bằng `get_or_create_clean_avatar(pid)` và upload vào input file `input[type="file"]` qua CDP `DOM.setFileInputFiles`.
    - Tự động click `Apply` / `Confirm` để lưu ảnh đại diện mới.
  * **Kiểm tra Username:**
    - Đọc username hiện tại từ URL / tiêu đề trang cá nhân.
    - Nếu username là dạng mặc định của TikTok (`user123456789...` hoặc regex `^user\d{6,}` / `^user_`) -> Xác định `need_change_username = true`.
    - Chuẩn hóa username mới từ C69 hoặc profile (loại bỏ tiền tố số `3_` bằng `clean_tiktok_username`).
    - Nhập username mới vào input `input[name="username"]` và bấm `Save` / `Lưu`.
  * Cập nhật log theo thời gian thực hiển thị lên Dashboard UI.

---

## 2. Kết quả Build
- Đã biên dịch release thành công: `cargo build --release` (34.14s).
- Đã sao chép file chạy tối ưu vào: `MunAutomationDesktop/MunAutomation.exe`.
