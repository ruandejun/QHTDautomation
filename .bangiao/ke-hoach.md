# KẾ HOẠCH THIẾT KẾ KỸ THUẬT (AGENT 1 - PLANNER)

- **Mục tiêu:** 
  1. Khắc phục triệt để lỗi bỏ qua Login: Bắt buộc tài khoản phải Login thành công mới được vào nuôi. Nếu chưa login và login không thành công thì DỪNG LẠI và ĐÓNG TRÌNH DUYỆT, nghiêm cấm nuôi dạo khách vãng lai.
  2. Kiểm tra Username & Avatar của tài khoản: Sau khi login, vào trang Profile/Setting để kiểm tra. Nếu avatar là ảnh mặc định hoặc username là chuỗi tự sinh (`user123456...`), tự động đổi username và upload avatar hoàn thiện profile.
- **Ngày lập:** 2026-09-20
- **Nhánh triển khai:** `feature/tiktok-avatar-username-strict-login`
- **Người thực hiện:** Agent 1 (Planner)

---

## 1. Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA)

### 1.1. Tại sao profile chưa login nhưng vẫn bị dẫn vào lướt FYP?
- Trên giao diện web của TikTok (cả desktop lẫn mobile view), thanh Sidebar luôn chứa thẻ:
  `<a href="/@" data-e2e="nav-profile">Profile</a>` (dẫn người dùng tới trang Profile, click vào sẽ hiện popup bắt đăng nhập).
- Code kiểm tra trước đó lại coi `document.querySelector('[data-e2e="nav-profile"]')` là dấu hiệu "đã có menu người dùng đăng nhập" (`user_profile_found = true`)!
- Hơn nữa, nếu `login_btn_found` bị lệch điều kiện hoặc cookie cũ còn sót, tool ngộ nhận là tài khoản đã login sẵn.
- **Hậu quả:** Trình duyệt lướt video với tư cách "Khách vãng lai" (Guest), mọi hành động Thả tim (Like), Bình luận (Comment), Chia sẻ (Share) đều không được TikTok ghi nhận cho tài khoản, khiến lượt nuôi trở nên vô ích.

### 1.2. Giải pháp chốt chặn Login nghiêm ngặt (Strict Verification)
1. **Kiểm tra thực tế phiên đăng nhập:**
   - Phải có Cookie `sessionid` hoặc `sessionid_ss` có giá trị hợp lệ (> 20 ký tự).
   - Tuyệt đối KHÔNG xuất hiện nút `[data-e2e="top-login-button"]` hoặc bất kỳ nút nào có text "Log in" / "Đăng nhập".
   - Mở thử URL `https://www.tiktok.com/profile`:
     * Nếu bị chuyển hướng (Redirect) về `tiktok.com/login` -> **100% CHƯA LOGIN**.
     * Nếu hiển thị trang profile cá nhân -> **ĐÃ LOGIN THÀNH CÔNG**.
2. **Quy tắc bất di bất dịch:**
   - Nếu chưa login: Tiến hành đăng nhập tự động (điền form, submit, bắt rate limit/OTP).
   - **NẾU ĐĂNG NHẬP THẤT BẠI HOẶC CHƯA LOGIN: DỪNG LẠI NGAY LẬP TỨC! ĐÓNG TRÌNH DUYỆT! BÁO LỖI! TUYỆT ĐỐI KHÔNG ĐƯỢC NUÔI!**

---

## 2. Thiết kế tính năng Kiểm tra & Cập nhật Avatar + Username

### 2.1. Kiểm tra Avatar
- Mở trang cá nhân `https://www.tiktok.com/@me` hoặc `https://www.tiktok.com/setting`.
- Quét ảnh đại diện:
  * Nếu ảnh avatar có src chứa chuỗi default của TikTok (ví dụ: `default-avatar`, `tiktok-avatar`, avatar bóng người) hoặc chưa có ảnh đại diện.
  * Tự động chuẩn bị ảnh avatar chất lượng cao từ thư mục `assets/avatars` hoặc tự động tạo ảnh avatar tự nhiên.
  * Sử dụng CDP `DOM.setFileInputFiles` đưa file ảnh vào thẻ `input[type="file"]` trong popup "Edit profile".
  * Bấm nút Save / Lưu để cập nhật.

### 2.2. Kiểm tra Username
- Đọc username hiện tại trên trang cá nhân:
  * Nếu username có dạng mặc định hệ thống: `user` theo sau bởi chuỗi số (regex: `^user\d{6,}` hoặc `user_`).
  * Lấy username mong muốn từ `profile.tiktok_username` hoặc tài khoản C69.
  * Mở popup "Edit profile", nhập username mới vào ô input `input[name="username"]` hoặc `input[placeholder*="Username"]`.
  * Bấm nút Save / Lưu để xác nhận đổi username.

---

## 3. Tiêu chí nghiệm thu (Acceptance Criteria)
1. Không bao giờ xảy ra tình trạng chưa login mà lại vào nuôi dạo FYP. Nếu login không thành công, trình duyệt phải đóng và báo lỗi rõ ràng.
2. Sau khi login thành công, hệ thống tự động kiểm tra avatar và username.
3. Nếu avatar trống -> tự động upload avatar mới.
4. Nếu username dạng rác (`user123456...`) -> tự động đổi username sạch đẹp.
5. Sau khi tài khoản chuẩn chỉnh -> mới tiến hành nuôi 30s-1 phút rồi tự động tắt trình duyệt.
