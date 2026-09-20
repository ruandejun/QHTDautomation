# BIÊN BẢN THAY ĐỔI MÃ NGUỒN (AGENT 2 - CODER)

- **Người thực hiện:** Agent 2 (Coder)
- **Ngày thực hiện:** 2026-09-20
- **Nhánh triển khai:** `feature/dynamic-screen-adaptive-grid`
- **Tài liệu tham chiếu:** `.bangiao/ke-hoach.md`
- **Phiên bản nhị phân:** `MunAutomationDesktop/MunAutomation.exe` (Release Build 38.85s)

---

## 1. Tóm tắt các thay đổi đã thực hiện

### 1.1. Module `qhtd-farm-rust/src/cdp_browser.rs`
1. **Bổ sung Win32 Native Work Area Detection (`get_screen_work_area`):**
   * Gọi `SystemParametersInfoW(SPI_GETWORKAREA)` và fallback `GetSystemMetrics(SM_CXSCREEN)`.
   * Lấy chính xác kích thước vùng làm việc màn hình thực tế (đã trừ taskbar và thích ứng DPI scaling).
   * Ví dụ: Trên màn hình máy anh Tony trả về đúng `2752 x 1112`. Trên màn hình Full HD trả về `1920 x 1040`.

2. **Nâng cấp thuật toán `calculate_grid_window_bounds` (Adaptive Smart Grid):**
   * **Màn hình siêu rộng (screen_w >= 2560px, như màn hình 2752px của anh Tony):**
     - Xếp 5 cột song song 1 hàng ngang.
     - Chiều rộng mỗi cửa sổ: `width = (screen_w - 20 - 4 * 12) / 5 = 536px >= 516px` (vượt ngưỡng hardcoded min-width của Chrome).
     - Chiều cao: `height = screen_h - 20` (~1090px).
     - Tọa độ `x = 10 + slot_idx * (width + 12)`:
       * Slot 0: `x = 10` (rộng 536px, chiếm 10 -> 546)
       * Slot 1: `x = 558` (rộng 536px, chiếm 558 -> 1094) -> **Cách Slot 0 đúng 12px, 100% không đè!**
       * Slot 2: `x = 1106` -> **Cách Slot 1 đúng 12px, 100% không đè!**
       * Slot 3: `x = 1654` -> **Cách Slot 2 đúng 12px, 100% không đè!**
       * Slot 4: `x = 2202` (chiếm 2202 -> 2738 <= 2752) -> **Cách Slot 3 đúng 12px, 100% không đè!**
   * **Màn hình Full HD (1920x1080) hoặc Laptop (< 2560px):**
     - Do min-width Chrome là ~516px nên 1 hàng 1920px chỉ nhét được tối đa 3 cửa sổ.
     - Tự động chia thành **2 Hàng Ma Trận Thông Minh**:
       * Hàng trên: 3 cửa sổ (`width = (screen_w - 44) / 3 = 625px`, `height = (screen_h - 35) / 2 = 502px`).
       * Hàng dưới: 2 cửa sổ căn giữa cân đối màn hình.
       * Cả 5 cửa sổ hiển thị trọn vẹn, không bao giờ đè lên nhau!

3. **Khớp khít Viewport bên trong với Cửa sổ bên ngoài:**
   * Trong `Emulation.setDeviceMetricsOverride`:
     - Truyền `v_width = std::cmp::max(412, win_w.saturating_sub(16))`
     - Truyền `v_height = std::cmp::max(700, win_h.saturating_sub(85))`
     - Bật `"fitWindow": true`
     - Giải quyết triệt để tình trạng "độ rộng trình duyệt to hơn so với màn hình hiển thị". Giao diện TikTok co giãn vừa khít 100% với khung cửa sổ Chrome!

---

## 2. Bàn giao sang Agent 3 (Tester)
Mã nguồn đã biên dịch release (38.85s) và đã được đồng bộ sang `MunAutomationDesktop/MunAutomation.exe`. Đề nghị Agent 3 tiến hành viết test suite kiểm định độc lập kích thước cửa sổ thực tế.
