# KẾ HOẠCH KỸ THUẬT: TÁI CẤU TRÚC LUỒNG NUÔI TIKTOK, CONCURRENCY CAP = 5 & GRID LAYOUT (AGENT 1 - PLANNER)

- **Người lập kế hoạch:** Agent 1 (Planner)
- **Ngày lập:** 2026-09-19
- **Nhánh triển khai:** `feature/tiktok-nurture-pipeline-grid-layout`
- **Mục tiêu chính:**
  1. Viết lại luồng nuôi TikTok toàn diện từ Login -> Lướt video -> Like -> Share (Copy Link) -> Comment.
  2. Bất kỳ bước nào gặp lỗi (lỗi mạng, proxy, sai mật khẩu, maximum attempts, captcha/otp timeout, crash) đều phải lập tức cập nhật status chi tiết và đóng ngay trình duyệt Chrome để giải phóng tài nguyên trước khi mở tài khoản khác.
  3. Giới hạn đồng thời tối đa **5 trình duyệt** (`Concurrency Cap = 5`).
  4. Tự động tính toán tọa độ cửa sổ theo dạng **Grid Layout 5 cột dọc** (`--window-position` & `--window-size`), xếp gọn gàng song song trên màn hình, không đè lên nhau để người dùng bao quát được trọn vẹn.

---

## 1. Phân tích hiện trạng & Khiếm khuyết kỹ thuật

| Thành phần | Hiện trạng | Vấn đề phát sinh | Giải pháp khắc phục |
| :--- | :--- | :--- | :--- |
| **Giới hạn đồng thời (Concurrency)** | Không có giới hạn số luồng trong `start_nurture` | Nếu user chọn nuôi 10-20 profile, máy mở ồ ạt 20 Chrome -> đơ máy, tràn RAM, nghẽn mạng | Tích hợp `Arc<tokio::sync::Semaphore>` với đúng 5 permits + Slot Pool `0..4` |
| **Bố cục hiển thị (Window Layout)** | `offset_x = 60 + (id * 35) % 400`, `offset_y = 40 + (id * 25) % 250` | Cửa sổ mở đè chồng chéo lên nhau dạng bậc thang, người dùng không nhìn được nội dung các cửa sổ phía sau | Xây dựng thuật toán **Grid Layout 5 cột dọc**: mỗi slot có tọa độ cố định (`x = slot * 380, y = 10, w = 375, h = 840`), xếp vừa khít màn hình 1920x1080 |
| **Tương tác TikTok** | Chỉ có Lướt (Watch), Like (Thả tim), Comment (Bình luận) | **Thiếu tính năng Share (Chia sẻ / Copy link)** theo yêu cầu của anh Tony | Bổ sung tương tác **Share/Copy link** qua selector `[data-e2e="share-icon"]` và menu action |
| **Xử lý lỗi & Thu hồi tài nguyên (Fail-safe)** | Một số nhánh lỗi hoặc khi nuôi xong không gọi `stop_cdp_profile` | Chrome chạy mồ côi giữ file locks và port DevTools, slot không được trả lại | Bọc toàn bộ worker trong cơ chế Guard đảm bảo: **Lỗi tại bất kỳ step nào -> Cập nhật status -> Gọi `stop_cdp_profile(pid)` -> Nhả slot** |

---

## 2. Thiết kế chi tiết kiến trúc giải pháp

### 2.1. Thuật toán Grid Layout (Tọa độ 5 cửa sổ không đè nhau)
Với màn hình chuẩn Full HD (1920 x 1080) và màn hình tỷ lệ 16:9 / 16:10:
Kích thước mỗi cửa sổ mô phỏng điện thoại:
- `width = 375px`
- `height = 840px` (để chừa 40px thanh Taskbar Windows)
- `gap = 6px`

Bảng phân bổ 5 Slot:
- **Slot 0**: `x = 10`, `y = 10`, `width = 375`, `height = 840`
- **Slot 1**: `x = 391`, `y = 10`, `width = 375`, `height = 840`
- **Slot 2**: `x = 772`, `y = 10`, `width = 375`, `height = 840`
- **Slot 3**: `x = 1153`, `y = 10`, `width = 375`, `height = 840`
- **Slot 4**: `x = 1534`, `y = 10`, `width = 375`, `height = 840`

Tổng chiều ngang chiếm: `1534 + 375 = 1909px <= 1920px`. 5 cửa sổ xếp vừa in từ cạnh trái sang cạnh phải màn hình, tạo góc nhìn bao quát 100% không chồng lấn.

### 2.2. Cơ chế Concurrency Cap = 5 & Slot Pool
Trong `BrowserNurtureEngine`:
```rust
pub struct BrowserNurtureEngine {
    // ...
    concurrency_semaphore: Arc<tokio::sync::Semaphore>, // 5 permits
    available_slots: Arc<parking_lot::Mutex<VecDeque<usize>>>, // [0, 1, 2, 3, 4]
}
```
- Khi bắt đầu: Chờ lấy permit từ semaphore, rút 1 slot từ `available_slots`.
- Truyền tọa độ `(x, y, w, h)` của slot đó vào hàm khởi chạy Chrome (`launch_cdp_profile_with_bounds`).
- Khi kết thúc hoặc lỗi: Luôn hoàn trả slot về `available_slots` và thả permit.

### 2.3. Luồng tương tác TikTok 6 bước chuẩn chỉnh
1. **Step 1: Khởi động & Kiểm tra mạng/Proxy:**
   - Đảo proxy sống nếu proxy hiện tại lỗi.
   - Mở Chrome với tọa độ slot. Kết nối CDP. Nếu lỗi -> Set status, đóng Chrome, nhả slot -> Return.
2. **Step 2: Xác thực phiên đăng nhập (Session Check):**
   - Nạp Cookies C69 nếu có. Mở `tiktok.com`. Nếu đã đăng nhập -> Chuyển sang Step 4.
3. **Step 3: Đăng nhập tự động & Xử lý thách thức:**
   - Pre-warming Explore.
   - Điền identity/password.
   - Bắt lỗi tức thời: `Maximum attempts` -> Đóng Chrome, set status `Rate limit (Chờ 1h)`, nhả slot -> Return.
   - Xử lý 2FA TOTP RFC 6238 tự động từ C69 Secret.
   - Xử lý Email OTP tự động từ C69 Email DB.
   - Nếu timeout 90s không qua -> Set status lỗi, đóng Chrome, nhả slot -> Return.
   - Thành công: Lưu cookies, backup thin profile -> Step 4.
4. **Step 4: Điều hướng For You Page (FYP):**
   - Vào `https://www.tiktok.com/foryou?lang=en`.
   - Kiểm tra mạng định kỳ. Nếu mất mạng/proxy đứt -> Set status lỗi mạng, đóng Chrome, nhả slot -> Return.
5. **Step 5: Vòng lặp hành vi người thật (Watch -> Like -> Share -> Comment):**
   - **Watch Video:** Phân phối xem từ 10s - 30s. Nghỉ giải lao tự nhiên sau mỗi 7 video.
   - **Like:** Xác suất ~65% (phím `l` hoặc click icon Like).
   - **Share (Copy link):** Xác suất ~30% (click Share icon, click Copy Link hoặc menu share).
   - **Comment:** Xác suất ~20% (click Comment icon, nhập nội dung tích cực, submit).
   - **Chuyển video:** Smooth scroll + phím `ArrowDown`.
6. **Step 6: Hoàn tất chu trình & Dọn dẹp tài nguyên:**
   - Update status `Đã nuôi thành công`.
   - Backup thin profile.
   - **Đóng Chrome hoàn toàn bằng `stop_cdp_profile(pid)`.**
   - Trả slot về pool cho tài khoản tiếp theo.

---

## 3. Kế hoạch kiểm thử của Tester (Agent 3)
- **TC-01:** Kiểm thử Concurrency Cap: Chạy cùng lúc nhiều hơn 5 profiles, verify số lượng active profiles tại mọi thời điểm không vượt quá 5.
- **TC-02:** Kiểm thử Grid Layout: Verify các cờ `--window-position` và `--window-size` của 5 slot khớp chính xác tọa độ, không đè lên nhau.
- **TC-03:** Kiểm thử Fail-Safe: Giả lập lỗi ở các step (lỗi proxy, timeout, rate limit), verify status được cập nhật ngay lập tức và Chrome của profile bị đóng sạch sẽ trong <1s, slot được giải phóng cho profile khác.
- **TC-04:** Kiểm thử Like - Share - Comment: Verify các selector và event dispatch cho cả 3 hành động tương tác.

---

## 4. Bàn giao sang Coder (Agent 2)
Kế hoạch đã chi tiết và bao quát toàn bộ yêu cầu. Chuyển giao sang Agent 2 (Coder) để tiến hành sửa code trong `cdp_browser.rs` và `browser_nurture.rs`.
