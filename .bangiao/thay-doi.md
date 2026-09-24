# Nhật Ký Thay Đổi Kỹ Thuật (Coder Handover)

**Người thực hiện:** Chuyên viên Coder (Dây Chuyền 4 Agent Nối Ca)  
**Nhánh:** `feature/iphey-reliable-phone-headers`  
**Ngày thực hiện:** 2026-09-24  
**Bám sát kế hoạch:** `.bangiao/ke-hoach.md`

---

## 1. Mục Tiêu & Phạm Vi Triển Khai
Xử lý dứt điểm các chỉ số "Unreliable" trên `https://iphey.com` và hoàn thiện tính năng Phone / Mobile Headers (Pixel 8 Pro, Android 14) cho quy trình nuôi TikTok:
- Khắc phục triệt để lỗi lệch múi giờ / vị trí địa lý giữa proxy IP và browser timezone (`Emulation.setTimezoneOverride` / `Emulation.setGeolocationOverride`).
- Loại bỏ hoàn toàn nhiễu fingerprint giả tạo (canvas noise, audio oscillator distortion, performance.now tamper) gây kích hoạt thuật toán phát hiện bot của Iphey / MixVisit.
- Chuẩn hóa Client Hints `Sec-CH-UA`, `Sec-CH-UA-Mobile`, `Sec-CH-UA-Platform`, User-Agent, Viewport (412x915) và Touch Points (5) chuẩn thiết bị di động thật.

---

## 2. Chi Tiết Các File Đã Thay Đổi

### A. `qhtd-farm-rust/src/cdp_browser.rs`
1. **Dynamic Proxy Geo & Timezone Resolver (`GeoInfo` & `resolve_proxy_geo`):**
   - Bổ sung struct `GeoInfo` lưu trữ `timezone`, `latitude`, `longitude`, `locale`.
   - Hàm `resolve_proxy_geo(host)`: Tự động phân tích IP proxy:
     - IP `50.114.98.173` -> Múi giờ `America/Denver` (Mountain Time), tọa độ `40.3032, -111.675` (Orem, Utah, US).
     - IP `23.27.210.99` -> Múi giờ `America/New_York` (Eastern Time), tọa độ `38.9586, -77.357` (Herndon, Virginia, US).
     - IP `104.164.131.28` -> Múi giờ `America/Los_Angeles` (Pacific Time), tọa độ `37.7749, -122.419` (San Francisco, California, US).
     - Fallback dynamic lookup qua `http://ip-api.com/json/{host}` với timeout 2.5s.
     - Fallback an toàn mặc định `America/New_York`.

2. **Khởi Chạy Chrome CDP Với Cấu Hình Chuẩn:**
   - Thay đổi cờ `--lang=vi-VN,vi,en-US,en` thành `--lang=en-US,en` để đồng bộ hoàn toàn với IP US residential.
   - Thêm cờ `--disable-blink-features=AutomationControlled` và `--font-render-hinting=medium`.
   - Trong `launch_cdp_profile_with_bounds`:
     - Gửi lệnh `Emulation.setTimezoneOverride` với đúng `geo.timezone` của proxy.
     - Gửi lệnh `Emulation.setGeolocationOverride` với đúng tọa độ `geo.latitude`, `geo.longitude` và `accuracy: 100`.
     - Gửi lệnh `Emulation.setLocaleOverride` với `geo.locale` (`en-US`).
     - Khi `is_mobile`:
       - Gửi `Emulation.setDeviceMetricsOverride`: `width: 412, height: 915, deviceScaleFactor: 2.625, mobile: true`.
       - Gửi `Emulation.setTouchEmulationEnabled`: `enabled: true, maxTouchPoints: 5`.
       - Gửi `Network.setUserAgentOverride` kèm đầy đủ `userAgentMetadata`:
         - `brands`: Google Chrome 134, Chromium 134, Not:A-Brand 24
         - `fullVersion`: "134.0.6998.98"
         - `platform`: "Android"
         - `platformVersion`: "14.0.0"
         - `architecture`: "arm64"
         - `model`: "Pixel 8 Pro"
         - `mobile`: true
         - `acceptLanguage`: "en-US,en;q=0.9"

3. **Tái Cấu Trúc Stealth Script Sạch Sẽ (Clean Pure Stealth Script v7.0):**
   - Loại bỏ triệt để việc ghi đè `toDataURL`, `getImageData`, `AudioContext`, `OfflineAudioContext`, `performance.now`, `getClientRects` - vì các thuật toán kiểm tra của Iphey/CreepJS nhận diện ngay các wrapper JavaScript không tự nhiên là "Tampered/Spoofed".
   - Chuẩn hóa `navigator.platform` thành `"Linux armv8l"` cho mobile (khắc phục lỗi chính tả trước đây `Linux armv81`).
   - Ẩn triệt để `navigator.webdriver` (chuyển sang `undefined` thay vì `false`).
   - Giả lập `navigator.userAgentData` khớp 100% với CDP UserAgentMetadata.
   - Giữ nguyên WebGL renderer và vendor tự nhiên của phần cứng thật.

### B. `qhtd-farm-rust/src/browser_nurture.rs`
1. Đảm bảo cấu hình nuôi TikTok tự động chuẩn hóa sang Phone / Mobile Headers:
   - User-Agent: `DEFAULT_PHONE_UA` (Android 14 / Pixel 8 Pro).
   - Profile OS: `"Android"`.
   - Resolution: `412x915`.
   - Tối ưu hóa tương tác cuộn và tap touch tự nhiên trên TikTok mobile.

---

## 3. Kết Quả Kiểm Tra Sơ Bộ
- `cargo check`: Đạt chuẩn, 0 lỗi biên dịch.
- Đang tiến hành build bản release binary và bàn giao cho Tester.
