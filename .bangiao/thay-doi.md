# BÀN GIAO THAY ĐỔI CODE — FIX TIKTOK MAXIMUM ATTEMPTS & CLEAN PURE FINGERPRINT (AGENT 2 - CODER)

- **Nhánh:** `fix/mun-anti-tiktok-login-fingerprint-clean`
- **Người thực hiện:** Agent 2 (Coder)
- **Tài liệu căn cứ:** `.bangiao/ke-hoach.md`

---

## 1. Tóm Tắt Các Thay Đổi Thực Hiện (Chesterton's Fence & Surgical Fixes)

### 1.1. Tái Cấu Trúc Stealth Script — Clean Pure Stealth v8.0 (`qhtd-farm-rust/src/cdp_browser.rs`)
- **Loại bỏ Prototype Poisoning:**
  - Xóa bỏ hoàn toàn việc hook vào `Node.prototype.appendChild` và `Node.prototype.insertBefore`.
  - Xóa bỏ việc hook vào `HTMLIFrameElement.prototype.contentWindow` và `contentDocument`.
  - Xóa bỏ cờ `__hooked__ = true` trên `WebGLRenderingContext.prototype.getParameter`.
- **Loại bỏ biến cờ rò rỉ toàn cục:**
  - Xóa sạch `w.__MUN_STEALTH_APPLIED__ = true` trên `window`.
- **Chuẩn hóa Navigator Attributes trên Prototype:**
  - Chuyển việc định nghĩa `hardwareConcurrency`, `deviceMemory`, `maxTouchPoints`, `platform`, `language`, `languages` lên `Navigator.prototype`.
  - Đảm bảo `navigator.hasOwnProperty(...)` trả về `false` chuẩn xác như Chrome nguyên bản.
  - Xóa sạch cờ `navigator.webdriver` mà không để lại own-property.

### 1.2. Thêm cờ khởi động Native Anti-Automation (`qhtd-farm-rust/src/cdp_browser.rs`)
- Bổ sung `--disable-blink-features=AutomationControlled` vào danh sách tham số khởi chạy của Google Chrome.
- Cờ này loại bỏ cờ tự động hóa trực tiếp từ tầng C++ Blink engine, giúp `navigator.webdriver` tự nhiên nhận `false` mà không cần tiêm script JS can thiệp.

### 1.3. Gỡ bỏ cưỡng bức Phone Emulation trên Desktop (`qhtd-farm-rust/src/browser_nurture.rs`)
- Bỏ logic tự động ghi đè mọi profile sang Mobile Phone `DEFAULT_PHONE_UA` (Android 14 / Pixel 8 Pro).
- Nếu profile không chỉ định Mobile, giữ nguyên cấu hình Desktop chuẩn (`DEFAULT_DESKTOP_UA`, Windows NT 10.0, Win32, 1200x800).
- Tránh được mâu thuẫn hệ thống nghiêm trọng (Pixel 8 Pro chạy GPU DirectX 11 / SwiftShader trên Windows).

### 1.4. Nâng Cấp Bộ Gõ Phím Thật CDP & Click Tự Nhiên (`qhtd-farm-rust/src/browser_nurture.rs`)
- Nâng cấp `type_text` của `CdpClient`: kết hợp `Input.dispatchKeyEvent` (`keyDown`), `Input.insertText` và `Input.dispatchKeyEvent` (`keyUp`) kèm jitter ngẫu nhiên 35-60ms giữa các phím gõ.
- Thay thế hoàn toàn cơ chế điền tức thì `setReactVal` và `form.requestSubmit()` bằng quy trình:
  1. Click chuột focus ô Username $\to$ Gõ từng ký tự phím thật qua CDP.
  2. Click chuột focus ô Password $\to$ Gõ từng ký tự phím thật qua CDP.
  3. Đồng bộ React State fallback và click chuột tọa độ tự nhiên vào nút "Log in".

### 1.5. Chuẩn Hóa Danh Sách Profile (`MunAutomationDesktop/browser_profiles.json`)
- Chuẩn hóa 5 profile về môi trường Windows Desktop sạch:
  - User-Agent: Chrome 134 Windows 10/11 x64.
  - Platform: `Windows`, Độ phân giải `1200x800`.
  - Card đồ họa: NVIDIA GeForce RTX 3060/4070 Direct3D11 thật (loại bỏ hoàn toàn SwiftShader bot device).
  - Xóa cờ rate-limit cũ (`last_nurture_status: null`, `retry_after_epoch: null`).

---

## 2. Danh Sách File Đã Chỉnh Sửa
1. `qhtd-farm-rust/src/cdp_browser.rs`
2. `qhtd-farm-rust/src/browser_nurture.rs`
3. `MunAutomationDesktop/browser_profiles.json`
4. `.bangiao/ke-hoach.md`
5. `.bangiao/thay-doi.md`
