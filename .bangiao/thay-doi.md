# SỔ BÀN GIAO THAY ĐỔI CODE (AGENT 2 - CODER)

- **Người thực hiện:** Agent 2 (Coder)
- **Ngày thực hiện:** 2026-09-18
- **Nhánh:** `feature/iphey-reliable-phone-headers`
- **Tài liệu tham chiếu:** `.bangiao/ke-hoach.md`

---

## 1. Mục tiêu đã thi công
1. Khắc phục triệt để lỗi thẻ `LOCATION` bị Unreliable trên `https://iphey.com` ("Detected masked or inconsistent location data (light)").
2. Triển khai chuẩn hóa Phone Emulation / Mobile Headers (Pixel 8 Pro / Android 14) cho trình duyệt và quy trình nuôi TikTok theo chỉ đạo của anh Tony.

---

## 2. Chi tiết các tệp đã sửa đổi

### A. `qhtd-farm-rust/src/cdp_browser.rs`
1. **Định nghĩa GeoInfo & Dynamic Geo Resolver:**
   - Thêm `pub struct GeoInfo`: `timezone`, `latitude`, `longitude`, `locale`.
   - Hàm `pub async fn resolve_proxy_geo(proxy_host: &str) -> GeoInfo`:
     * Bảng ánh xạ nhanh: IP `50.114.98.173` -> Utah (`America/Denver`, lat: `40.3032`, lon: `-111.675`), IP `23.27.210.99` -> New York (`America/New_York`), IP `104.164.131.28` -> Los Angeles (`America/Los_Angeles`).
     * Cơ chế dynamic non-blocking lookup qua `http://ip-api.com/json/{host}` với timeout 1.5s cho mọi dải IP khác.
2. **Khắc phục Locale Leak:**
   - Đổi launch flag Chrome `--lang=vi-VN,vi,en-US,en` thành `--lang=en-US,en`.
   - Trong CDP Session tiêm `Emulation.setLocaleOverride` với `locale: geo_info.locale` (en-US).
3. **Đồng bộ Timezone & Geolocation trong CDP Target:**
   - Thay thế New York hardcoded bằng `geo_info.timezone`, `geo_info.latitude`, `geo_info.longitude`. Đảm bảo `Intl.DateTimeFormat().resolvedOptions().timeZone` khớp 100% với MaxMind GeoIP của IP proxy.
4. **Sửa lỗi Typo & Nâng cấp Stealth Script:**
   - Sửa `platform` từ `"Linux armv81"` (số 1) thành `"Linux armv8l"` (chữ l) cho mobile.
   - Thêm `navigator.language` (`en-US`), `navigator.languages` (`['en-US', 'en']`).
   - Thêm `navigator.userAgentData.mobile` và `navigator.userAgentData.platform` spoofing.
5. **Chuẩn hóa Phone Headers & Viewport:**
   - Hằng số `DEFAULT_PHONE_UA`: Pixel 8 Pro / Android 14 / Chrome 134.
   - `Emulation.setUserAgentOverride`:
     * `platformVersion`: `"14.0.0"` cho Android.
     * `model`: `"Pixel 8 Pro"`.
     * `acceptLanguage`: `"en-US,en;q=0.9"`.
   - `Emulation.setDeviceMetricsOverride`: width = `412`, height = `915`, `deviceScaleFactor: 2.625`, `mobile: true`.
   - `Emulation.setTouchEmulationEnabled`: `maxTouchPoints: 5`.

### B. `qhtd-farm-rust/src/browser_nurture.rs`
1. **Thiết lập Mặc định Phone Profile khi Nuôi TikTok:**
   - Nếu profile chưa có Mobile UA, tự động gán `DEFAULT_PHONE_UA`, `profile_os: "Android"`, `profile_resolution: "412x915"`.
2. **Mượt hóa Thao tác Chuyển Video:**
   - Bổ sung `window.scrollBy({ top: window.innerHeight, behavior: 'smooth' })` trước khi gửi phím `ArrowDown`, đảm bảo giao diện mobile vuốt chuyển video tự nhiên.

---

## 3. Bản dựng nhị phân (Binary Build)
- Đang biên dịch release: `qhtd-farm-rust/target/release/qhtd-farm-core.exe`
- Đích sao chép: `MunAutomationDesktop/MunAutomation.exe`

---

## 4. Bàn giao sang Agent 3 (Tester)
- **Mục tiêu kiểm thử:**
  1. Kiểm tra `https://iphey.com` với Profile #1 và proxy SOCKS5: xác nhận toàn bộ 5 thẻ xanh (Reliable / Trustworthy), không còn cảnh báo "inconsistent location data".
  2. Kiểm tra `https://www.tiktok.com` với Phone header: xác nhận tải mượt giao diện mobile feed, touch scroll hoạt động chuẩn xác.
