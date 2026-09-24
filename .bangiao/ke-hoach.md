# KẾ HOẠCH ĐIỀU TRA & KHẮC PHỤC LỖI TIKTOK LOGIN "MAXIMUM ATTEMPTS" TRÊN MUN ANTI (AGENT 1 - PLANNER)

- **Mục tiêu:**
  1. Điều tra và phân tích nguyên nhân gốc rễ (RCA) vì sao đăng nhập TikTok qua Mun Anti lại bị lỗi "Maximum number of attempts reached. Try again later", trong khi các trình duyệt khác (Chrome chuẩn, AdsPower, GoLogin) lại đăng nhập hoàn toàn bình thường.
  2. Khắc phục triệt để hiện tượng Fingerprint Spoofing "quá đà" (Over-spoofing / Prototype Poisoning) và mâu thuẫn hệ điều hành / phần cứng.
  3. Chuẩn hóa cơ chế Profile sạch (Clean Pure Stealth) và cơ chế nhập liệu phím thật tự nhiên (CDP Native Keystrokes) cho luồng đăng nhập TikTok.
- **Ngày lập:** 2026-09-24
- **Nhánh triển khai:** `fix/mun-anti-tiktok-login-fingerprint-clean`
- **Người thực hiện:** Agent 1 (Planner)

---

## 1. Phân Tích Nguyên Nhân Gốc Rễ (RCA) Tại Sao Mun Anti Bị "Maximum Attempts"

Hệ thống bảo mật của TikTok (sử dụng ByteDance WebMSSDK, `secsdk`, `risk_control_service`, `bd_ticket_guard`) không chỉ kiểm tra số lần đăng nhập sai, mà "Maximum number of attempts reached" chính là **thông báo từ chối (Shadow-block / Bot-Flag)** khi Risk Score của phiên vượt ngưỡng an toàn.

Qua rà soát mã nguồn `cdp_browser.rs` và `browser_nurture.rs`, phát hiện 4 nguyên nhân chí mạng:

### 1.1. Mâu thuẫn dấu vân tay phần cứng và hệ điều hành (Device Inconsistency)
- Trong `browser_nurture.rs` (dòng 533-537), mã nguồn đang tự động ép MỌI profile sang chuẩn Mobile Phone:
  ```rust
  if active_profile.profile_user_agent.trim().is_empty() || !active_profile.profile_user_agent.contains("Mobile") {
      active_profile.profile_user_agent = crate::cdp_browser::DEFAULT_PHONE_UA.to_string(); // Android 14 Pixel 8 Pro
      active_profile.profile_os = "Android".to_string();
      active_profile.profile_resolution = "412x915".to_string();
  }
  ```
- Tuy nhiên, bên dưới trình duyệt là `chrome.exe` chạy trên Windows 10/11 x64.
- WebGL GPU của profile lại cấu hình là GPU máy bàn DirectX: `"ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)"` hoặc thiết bị giả lập Google `"SwiftShader Device"`.
- **Mâu thuẫn:** Không bao giờ có một chiếc điện thoại Google Pixel 8 Pro chạy chip ARM / Android mà lại sở hữu card đồ họa NVIDIA Direct3D11 (DirectX của Windows) hay SwiftShader của bot VM. Khi ByteDance WAF thu thập WebGL extensions và renderer, nó xác định ngay đây là profile nhân tạo (Synthetic Bot Profile) và lập tức nâng mức rủi ro lên cao nhất.

### 1.2. Can thiệp thô bạo vào Prototype JavaScript (JS Prototype Poisoning)
- Trong `cdp_browser.rs` (dòng 440-530), script `stealth_js` đang hook trực tiếp vào các hàm cốt lõi của trình duyệt:
  1. `Node.prototype.appendChild` và `Node.prototype.insertBefore`: Bị ghi đè bằng hàm JS tự tạo.
  2. `HTMLIFrameElement.prototype.contentWindow` và `contentDocument`: Bị ghi đè getter.
  3. `WebGLRenderingContext.prototype.getParameter`: Bị gắn cờ `fn.__hooked__ = true`.
  4. Để lộ cờ toàn cục: `w.__MUN_STEALTH_APPLIED__ = true;`.
  5. `Object.defineProperty(w.navigator, 'webdriver', { get: () => undefined })`: Biến `webdriver` thành own-property trên đối tượng `navigator` (trong khi Chrome thật `navigator.hasOwnProperty('webdriver') === false`).
- Khi TikTok tải các script bảo mật và Captcha iframe, TikTok kiểm tra tính nguyên bản của DOM methods:
  `Function.prototype.toString.call(Node.prototype.appendChild)` $\to$ Trả về mã nguồn JavaScript của hàm hook thay vì `function appendChild() { [native code] }`!
  TikTok nhận diện ngay trình duyệt đang bị công cụ tự động hóa can thiệp (Tampered DOM).

### 1.3. Nhập liệu biểu mẫu phi tự nhiên (Synthetic Input vs Real Keystrokes)
- Trong `browser_nurture.rs`, hàm điền form sử dụng React synthetic setter gán thẳng chuỗi ký tự vào `.value` trong 0 mili-giây, sau đó bấm `form.requestSubmit()` hoặc `btn.click()`.
- Không hề có sự kiện bàn phím thật (`keydown`, `keypress`, `keyup`), không có khoảng thời gian gõ phím tự nhiên (typing cadence 50-100ms), không có sự kiện chuột di chuyển (mouse trajectory).
- ByteDance theo dõi telemetry hành vi (behavioral biometrics). Một form đăng nhập bị điền toàn bộ tài khoản và mật khẩu tức thì rồi submit ngay lập tức được coi là bot script.

### 1.4. So sánh với trình duyệt khác (Tại sao trình duyệt khác lại login bình thường?)
- Trình duyệt khác (Chrome chuẩn hoặc Anti-detect chuyên nghiệp):
  * Chạy ở chế độ Desktop chuẩn: OS Windows, UA Windows, Win32, GPU DirectX thật, mọi thông số phần cứng đồng nhất 100%.
  * Giấu `navigator.webdriver` từ cấp độ nhân C++ qua cờ khởi động `--disable-blink-features=AutomationControlled`, KHÔNG can thiệp thô bạo vào prototype `appendChild` hay `contentWindow`.
  * Không để lộ bất kỳ biến toàn cục nào trên `window`.

---

## 2. Giải Pháp Kỹ Thuật (Architecture & Implementation Plan)

### A. Làm Sạch Toàn Diện Stealth Script (Clean Pure Stealth v8.0)
1. **Loại bỏ triệt để prototype poisoning:**
   - Xóa bỏ việc hook `Node.prototype.appendChild` và `Node.prototype.insertBefore`.
   - Xóa bỏ việc hook `HTMLIFrameElement.prototype.contentWindow` và `contentDocument`.
   - Xóa bỏ biến cờ rò rỉ toàn cục `window.__MUN_STEALTH_APPLIED__`.
   - Xóa bỏ cờ `fn.__hooked__` trên `getParameter`.
2. **Ẩn `navigator.webdriver` chuẩn Native:**
   - Bổ sung switch khởi động Chrome: `--disable-blink-features=AutomationControlled`.
   - Sử dụng `delete Object.getPrototypeOf(navigator).webdriver` hoặc prototype getter sạch, đảm bảo `navigator.hasOwnProperty('webdriver') === false`.
3. **Đồng bộ nhất quán hệ điều hành & phần cứng (Consistency First):**
   - Nếu profile là Desktop (Windows):
     * User-Agent: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36`
     * Platform: `Win32`
     * Platform Title: `Windows`
     * Touch points: `0`
     * GPU Vendor/Renderer: NVIDIA / Intel / AMD Direct3D11 thật
     * Viewport: `1200x800` hoặc `1920x1080` (Window Mode thông thường, không dùng `--app=`)
   - Nếu profile là Mobile (Phone): Phải đi kèm GPU renderer di động (Mali / Adreno), không ghép đôi với DirectX 11 hay SwiftShader.

### B. Mặc Định Desktop Mode Cho Đăng Nhập An Toàn (Tránh Ép Mobile Quá Đà)
- Trong `browser_nurture.rs`:
  - Bỏ đoạn code ép cưỡng bức `DEFAULT_PHONE_UA` cho mọi profile.
  - Cho phép profile giữ nguyên cấu hình Desktop tự nhiên (hoặc chuyển sang Desktop Profile khi đăng nhập TikTok để có Trust Score cao nhất như anh Tony kiểm chứng).

### C. Cơ Chế Nhập Liệu Phím Thật Tự Nhiên Bằng CDP (CDP Native Keystroke Typing)
- Sử dụng `cdp.type_text` với `Input.dispatchKeyEvent` (`keyDown`, `keyUp`) cho từng ký tự của Username và Password với delay ngẫu nhiên 35-70ms.
- Mô phỏng hành vi người dùng thật:
  1. Click chuột vào ô Username $\to$ Chờ 300ms $\to$ Gõ tài khoản từng phím.
  2. Bấm phím `Tab` hoặc click chuột vào ô Password $\to$ Chờ 400ms $\to$ Gõ mật khẩu từng phím.
  3. Chờ 600ms $\to$ Click chuột tọa độ vào nút "Log in" (không dùng `requestSubmit()` cưỡng bức).

---

## 3. Tiêu Chí Nghiệm Thu (Acceptance Criteria)

1. **Khắc phục lỗi Maximum Attempts:**
   - Chạy thử nghiệm đăng nhập tài khoản TikTok qua Mun Anti với Clean Desktop Profile: Không bị dính cờ đỏ "Maximum number of attempts reached" ngay lập tức.
   - Trình duyệt điều hướng mượt mà, chuyển sang bước yêu cầu 2FA / giải captcha hoặc đăng nhập thành công.
2. **Kiểm tra DOM Integrity (Không rò rỉ):**
   - `window.__MUN_STEALTH_APPLIED__` là `undefined`.
   - `Node.prototype.appendChild.toString()` là `'function appendChild() { [native code] }'`.
   - `navigator.hasOwnProperty('webdriver')` là `false`.
3. **Build & Release:**
   - Biên dịch `cargo build --release` thành công 100%.
   - Cập nhật binary `MunAutomationDesktop/MunAutomation.exe`.
