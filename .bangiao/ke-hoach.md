# KẾ HOẠCH THIẾT KẾ KỸ THUẬT (AGENT 1 - PLANNER)

- **Mục tiêu:** 
  1. Thu nhỏ kích thước cửa sổ Chrome về đúng chuẩn kích thước và tỷ lệ điện thoại thật (375x820) bằng Chrome App Mode, loại bỏ thanh tab và omnibox cồng kềnh.
  2. Tái cấu trúc Step 1 kiểm tra Login chuẩn xác: vào TikTok 10s, nếu có nút Login -> tiến hành Login; nếu không có nút Login (đã đăng nhập) -> lướt video, like, share, comment từ 30s - 1 phút rồi tự động tắt trình duyệt.
- **Ngày lập:** 2026-09-20
- **Nhánh triển khai:** `feature/tiktok-nurture-pipeline-grid-layout`
- **Người thực hiện:** Agent 1 (Planner)

---

## 1. Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA)

### 1.1. Tại sao cửa sổ Chrome trước đó to và không giống điện thoại?
- Khi mở Chrome ở chế độ cửa sổ bình thường (Regular Window), Chrome có thanh Tabs, thanh địa chỉ Omnibox, nút Extension và điều khiển cửa sổ.
- Hệ điều hành Windows và Chromium ép giới hạn cứng `min-width = 516px`.
- **Giải pháp đột phá:** Khi kích hoạt cờ `--app={start_url}` (Chrome Application Mode), Chrome chuyển sang chế độ cửa sổ ứng dụng không tab, không toolbar, không omnibox, và **hoàn toàn gỡ bỏ giới hạn min-width 516px**. Kích thước cửa sổ thu nhỏ chuẩn xác về **`width = 375px, height = 820px`** (tỉ lệ 9:19.5 chuẩn smartphone hiện đại).

### 1.2. Tại sao kiểm tra Login trước đó bị lỗi nhận diện sai?
- Script cũ kiểm tra: `hasAvatar && !hasLoginBtn`, trong đó `hasAvatar` dùng selector `img[alt*="avatar"]` hoặc `a[href*="/@"]`.
- Trên trang chủ TikTok FYP, **mỗi video của khách vãng lai đều có avatar và link kênh của tác giả video**!
- Trong khi đó, nút Login trên Mobile Web có selector và cấu trúc DOM khác desktop khiến `hasLoginBtn` trả về `false`.
- Hậu quả: Dù profile chưa hề login, script vẫn kết luận sai là "Đã đăng nhập" và vào lướt video như đã login thành công!

---

## 2. Thiết kế giải pháp kỹ thuật

### 2.1. Kích thước cửa sổ Chuẩn Điện Thoại (375x820) & Grid Layout
- Khi `is_mobile`:
  * Sử dụng flag `--app={start_url}` thay vì mở cửa sổ thông thường.
  * Kích thước cửa sổ cố định chuẩn điện thoại: `width = 375`, `height = 820`.
  * Grid Layout 5 slot:
    - Slot 0: `x = 15, y = 10`
    - Slot 1: `x = 15 + 1 * (375 + 15) = 405, y = 10`
    - Slot 2: `x = 15 + 2 * (375 + 15) = 795, y = 10`
    - Slot 3: `x = 15 + 3 * (375 + 15) = 1185, y = 10`
    - Slot 4: `x = 15 + 4 * (375 + 15) = 1575, y = 10`
    - Tổng bề ngang cả 5 cửa sổ là `1950px` (vừa vặn, thông thoáng trên màn hình 2752px của anh Tony, và cực kỳ đẹp mắt).

### 2.2. Luồng kiểm tra Login chuẩn xác (Step 1)
1. **Vào TikTok và chờ 10s:**
   * Điều hướng vào `https://www.tiktok.com`.
   * Lắng nghe DOM trong 10s để trang tải đầy đủ các component.
2. **Kiểm tra nút Login xuất hiện:**
   * Dùng script kiểm tra DOM chính xác:
     - Quét các nút có text `"Log in"`, `"Đăng nhập"`, attribute `data-e2e="top-login-button"`, `data-e2e="nav-login-button"`, link `href*="/login"`.
     - Kiểm tra song song CDP Cookies: có cookie `sessionid` / `sessionid_ss` hay không.
   * **Nếu CÓ nút Login:**
     - Xác định tài khoản CHƯA ĐĂNG NHẬP.
     - Cập nhật log & status: `Chưa đăng nhập TikTok -> Đang tiến hành đăng nhập...`.
     - Thực hiện quy trình đăng nhập:
       * Mở form login hoặc click nút Login.
       * Tự động điền email/username và password từ C69.
       * Click Log in.
       * Nếu thành công: lưu thin profile và chuyển sang nuôi.
       * Nếu gặp captcha/rate limit: báo trạng thái và đóng an toàn.
   * **Nếu KHÔNG CÓ nút Login (Đã đăng nhập sẵn):**
     - Xác định tài khoản ĐÃ ĐĂNG NHẬP SẴN.
     - Cập nhật log: `✅ Đã đăng nhập sẵn -> Bắt đầu lướt video, like, share, comment...`.
     - Tiến hành lướt video trên FYP:
       * Thời gian nuôi: **tốn khoảng 30s - 1 phút** (tổng chu kỳ 35s-55s).
       * Xem 4-6 video (mỗi video 6-12s).
       * Thả tim (Like) ngẫu nhiên ~65%.
       * Chia sẻ (Share/Copy link) ngẫu nhiên ~30%.
       * Bình luận (Comment) ngẫu nhiên ~20%.
     - **Sau khi nuôi xong (30s - 1 phút):**
       * Cập nhật status: `Đã nuôi thành công (Xem X video, Y like, Z comment, W share)`.
       * **TẮT TRÌNH DUYỆT ĐI NGAY LẬP TỨC** để giải phóng RAM, nhả slot cho profile tiếp theo trong hàng đợi!

---

## 3. Tiêu chí nghiệm thu (Acceptance Criteria)
1. Cửa sổ Chrome mở ra chuẩn tỷ lệ điện thoại `375x820` bằng App Mode, không có thanh tab và omnibox cồng kềnh.
2. Không nhận diện nhầm avatar tác giả video thành avatar tài khoản đăng nhập.
3. Nếu tài khoản chưa login -> tự động phát hiện nút Login và tiến hành login.
4. Nếu tài khoản đã login -> lướt video, like, share, comment từ 30s - 1 phút rồi tự động đóng trình duyệt.
