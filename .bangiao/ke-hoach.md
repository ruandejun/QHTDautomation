# KẾ HOẠCH THIẾT KẾ KỸ THUẬT (AGENT 1 - PLANNER)

- **Mục tiêu:** Khắc phục triệt để hiện tượng cửa sổ Mobile bị to hơn màn hình hiển thị bên trong và các cửa sổ bị đè lên nhau.
- **Ngày lập:** 2026-09-20
- **Nhánh triển khai:** `feature/dynamic-screen-adaptive-grid`
- **Người thực hiện:** Agent 1 (Planner)

---

## 1. Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA)

### 1.1. Chrome Hardcoded Minimum Window Width trên Windows
- Kiểm tra thực nghiệm trực tiếp qua Win32 API (`GetWindowRect`) và thông điệp `WM_GETMINMAXINFO`:
  Trình duyệt Google Chrome trên Windows có giới hạn cứng: **Chiều rộng cửa sổ tối thiểu (Minimum Width) là ~516px** (do thanh tab, omnibox, menu và các nút điều khiển).
- Dù ta truyền cờ `--window-size=375,840` thì Windows và Chromium shell **vẫn ép cửa sổ rộng tối thiểu 516px**!

### 1.2. Thuật toán cũ bị đè chồng lấn (Window Overlap)
- Thuật toán cũ đặt:
  `let width = 375;`
  `let x = 10 + (slot_idx as i32 * 381);`
- Vì cửa sổ Chrome thực tế rộng **516px**, nhưng khoảng cách giữa các điểm bắt đầu chỉ là **381px**:
  * Slot 0: `x = 10` -> kéo dài đến `x = 526`
  * Slot 1: `x = 391` -> kéo dài đến `x = 907` (**ĐÈ LÊN SLOT 0 TẬN 135px!**)
  * Slot 2: `x = 772` -> kéo dài đến `x = 1288` (**ĐÈ LÊN SLOT 1 TẬN 135px!**)
  * Slot 3: `x = 1153` -> kéo dài đến `x = 1669` (**ĐÈ LÊN SLOT 2 TẬN 135px!**)
  * Slot 4: `x = 1534` -> kéo dài đến `x = 2050` (**ĐÈ LÊN SLOT 3 TẬN 135px!**)
=> Toàn bộ 5 cửa sổ bị đè chồng lấn lên nhau từ trái qua phải!

### 1.3. Lệch pha giữa Viewport hiển thị bên trong và Cửa sổ bên ngoài
- Trong `Emulation.setDeviceMetricsOverride` (dòng 1506-1510):
  Đang gán cứng: `width: 412, height: 915, fitWindow: false`.
- Cửa sổ ngoài rộng 516px+, nhưng viewport trang web chỉ có 412px và `fitWindow: false` -> dẫn đến trang web bị lọt thỏm ở giữa, hai bên viền thừa khoảng trống xám to đùng, tạo cảm giác "độ rộng trình duyệt to hơn so với màn hình hiển thị"!

---

## 2. Giải pháp kiến trúc kỹ thuật (Architectural Solution)

### 2.1. Tự động nhận diện diện tích làm việc màn hình thực tế (Dynamic Work Area Detection)
- Gọi Win32 API `SystemParametersInfoW(SPI_GETWORKAREA)` trong Rust:
  * Trả về chính xác `width` và `height` của khu vực làm việc (đã trừ Taskbar Windows và tính toán theo DPI scaling thực tế).
  * Ví dụ: Trên màn hình máy anh Tony trả về chính xác `2752 x 1112`. Trên màn hình Full HD trả về `1920 x 1040`.

### 2.2. Bố trí Grid Layout thích ứng thông minh (Adaptive Smart Grid)
Căn cứ vào `screen_width` thực tế:

1. **Nếu `screen_width >= 2600` (Màn hình rộng như 2752px của anh Tony):**
   - Xếp **5 cột song song trên 1 hàng ngang**:
     * `window_width = (screen_width - 20 - 4 * 12) / 5` (~536px trên màn hình 2752px, lớn hơn 516px min-width).
     * `window_height = screen_height - 20` (~1090px).
     * `x = 10 + slot_idx * (window_width + 12)`.
     * **Khoảng cách giữa các cửa sổ là 12px, 100% không đè lên nhau dù chỉ 1 pixel!**

2. **Nếu `screen_width < 2600` (Màn hình 1920x1080 Full HD hoặc Laptop):**
   - Vì min-width của Chrome là ~516px, 1 hàng ngang chỉ chứa tối đa 3 cửa sổ (`1920 / 516 = 3.7`).
   - Tự động chia thành **2 Hàng Ma Trận Thông Minh (2-Row Smart Grid)**:
     * Hàng trên: 3 cửa sổ (Slot 0, 1, 2)
       `width = (screen_width - 20 - 2 * 12) / 3` (~620px trên Full HD).
       `height = (screen_height - 20 - 15) / 2` (~490px-500px).
       `x = 10 + col * (width + 12)`, `y = 10`.
     * Hàng dưới: 2 cửa sổ (Slot 3, 4) căn giữa màn hình cân đối:
       `margin_x = (screen_width - (2 * width + 12)) / 2`.
       `x = margin_x + (slot - 3) * (width + 12)`, `y = 10 + height + 15`.
     * **Cả 5 cửa sổ đều hiển thị trọn vẹn, không cửa sổ nào bị đè lên nhau!**

### 2.3. Khớp khít Viewport bên trong với Cửa sổ bên ngoài
- Truyền `window_width` và `window_height` vào CDP reader task.
- Trong `Emulation.setDeviceMetricsOverride`:
  * `width`: Tính toán vừa khít inner width (`std::cmp::max(412, window_width - 16)`).
  * `height`: Tính toán vừa khít inner height (`std::cmp::max(700, window_height - 85)`).
  * `fitWindow`: Đặt thành `true` để trang TikTok tự động căn chỉnh tỷ lệ 100% khít khung hiển thị, không bị thừa lề xám hay lệch kích thước.

---

## 3. Tiêu chí nghiệm thu (Acceptance Criteria)
1. Cửa sổ Chrome của các slot không có bất kỳ khoảng đè chồng lấn (overlap) nào.
2. Tọa độ của cửa sổ sau phải luôn `>=` tọa độ của cửa sổ trước + chiều rộng thực tế của cửa sổ trước (`x_{i+1} >= x_i + w_i`).
3. Giao diện TikTok bên trong hiển thị vừa vặn, không bị thừa viền hay bóp méo.
4. Test suite tự động xác thực và chạy live trên Windows.
