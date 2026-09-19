# BIÊN BẢN THAY ĐỔI MÃ NGUỒN (AGENT 2 - CODER)

- **Người thực hiện:** Agent 2 (Coder)
- **Ngày thực hiện:** 2026-09-19
- **Nhánh triển khai:** `feature/tiktok-nurture-pipeline-grid-layout`
- **Tài liệu tham chiếu:** `.bangiao/ke-hoach.md`
- **Phiên bản nhị phân:** `MunAutomationDesktop/MunAutomation.exe` (Release Build 55.40s)

---

## 1. Tóm tắt các thay đổi đã thực hiện

### 1.1. Module `qhtd-farm-rust/src/cdp_browser.rs`
- **Bổ sung hàm tính toán Grid Layout (`calculate_grid_window_bounds`):**
  * Chia 5 slot độc lập trên màn hình.
  * Với profile Phone / Mobile: Mỗi cửa sổ có kích thước `375 x 840`, khoảng cách gap `6px`.
  * Tọa độ `x` của 5 slot từ 0 đến 4: `x = 10 + slot * 381`, `y = 10`. Tổng 5 cửa sổ chiếm 1900px, xếp vừa khít màn hình 1920x1080 mà **không bao giờ đè lên nhau**.
  * Với profile Desktop: Bố trí 2 hàng (hàng trên 3 cửa sổ, hàng dưới 2 cửa sổ).
- **Mở rộng `launch_cdp_profile_with_bounds`:**
  * Cho phép truyền trực tiếp tọa độ slot `bounds: Option<(i32, i32, u32, u32)>` từ nurture pool vào flags Chrome `--window-position` và `--window-size`.

### 1.2. Module `qhtd-farm-rust/src/browser_nurture.rs`
- **Tích hợp Concurrency Semaphore & Slot Pool:**
  * Thêm `concurrency_semaphore: Arc<tokio::sync::Semaphore>` giới hạn đúng 5 permits.
  * Thêm `available_slots: Arc<Mutex<VecDeque<usize>>>` chứa danh sách slot rảnh `[0, 1, 2, 3, 4]`.
  * Xây dựng 2 hàm `acquire_slot` và `release_slot`.
- **Cơ chế RAII `SlotGuard` (Fail-safe đóng browser tức thì):**
  * Khi worker bắt đầu, lấy permit và slot `(slot_idx, permit)`.
  * Định nghĩa struct `SlotGuard` cài đặt trait `Drop`: Bất kể worker kết thúc theo cách nào (hoàn thành, lỗi ở bất kỳ step nào, timeout, hủy tác vụ):
    1. Tự động gọi `crate::cdp_browser::stop_cdp_profile(self.pid)` để đóng hoàn toàn trình duyệt Chrome, giải phóng RAM, cổng port và file lock.
    2. Tự động trả slot `slot_idx` về `available_slots`.
    3. Tự động giải phóng permit semaphore cho tài khoản tiếp theo đang xếp hàng được mở lên ngay tại vị trí ô slot đó.
- **Bổ sung tương tác Share (Chia sẻ / Copy Link):**
  * Tích hợp selector `[data-e2e="share-icon"]` và menu action `copy link` với tỷ lệ tự nhiên 30%.
  * Cập nhật `shares_count: u32` vào `BrowserNurtureStatus` và hàm `update_stats`.
- **Cập nhật tổng kết chu trình:**
  * Ghi nhận đầy đủ: `Đã xem X video, thả tim Y lượt, bình luận Z lượt, chia sẻ W lượt`.

---

## 2. Bàn giao sang Agent 3 (Tester)
Mã nguồn đã biên dịch release tối ưu hóa (55.40s) và đã được đồng bộ sang `MunAutomationDesktop/MunAutomation.exe`. Đề nghị Agent 3 tiến hành viết test suite kiểm định độc lập.
