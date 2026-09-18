# KẾ HOẠCH KỸ THUẬT (PLANNER) — KHẮC PHỤC UNRELIABLE TRÊN IPHEY & CHUẨN HÓA PHONE HEADERS NUÔI TIKTOK

> **Mã nhiệm vụ:** `/ship IPHEY_RELIABLE_PHONE_HEADERS`  
> **Người lập:** Agent 1 — Planner  
> **Nhánh thi công:** `feature/iphey-reliable-phone-headers`  
> **Trạng thái:** HOÀN TẤT THIẾT KẾ — BÀN GIAO SANG CODER  

---

## 1. Phân tích nguyên nhân gốc (Root Cause Analysis - RCA)

### A. Tại sao `iphey.com` báo "Your Digital Identity Looks Unreliable" và `LOCATION` bị đỏ?
1. **Lệch múi giờ giữa IP và Browser Intl Timezone (Timezone Mismatch):**
   - Trong `cdp_browser.rs` (dòng 1326), `Emulation.setTimezoneOverride` bị gán cứng là `"America/New_York"` (múi giờ miền Đông, UTC-4).
   - Trong khi đó, Proxy IP `50.114.98.173` nằm tại Orem, Utah — thuộc múi giờ `"America/Denver"` (Mountain Time, UTC-6).
   - Hệ thống phát hiện gian lận của MixVisit / Iphey đối chiếu: IP ở Utah (UTC-6) nhưng JavaScript trình duyệt báo New York (UTC-4) -> Chênh lệch 2 tiếng -> Kích hoạt cảnh báo `Detected masked or inconsistent location data (light)` -> Toàn bộ thẻ `LOCATION` biến thành ĐỎ!
2. **Lệch tọa độ Geolocation (GPS Spoofing Mismatch):**
   - Tọa độ gán cứng tại New York (`lat: 40.7128, lon: -74.0060`), trong khi tọa độ thực của IP Utah là `40.3032, -111.675` (cách nhau hơn 3.000 km).
3. **Lệch ngôn ngữ hệ thống và proxy:**
   - Chrome khởi chạy với cờ `--lang=vi-VN,vi,en-US,en` khiến header `Accept-Language` ưu tiên tiếng Việt trên một IP Mỹ -> Tăng điểm nghi ngờ vị trí.

### B. Tại sao chuyển đổi sang Phone/Mobile Headers là giải pháp tối ưu cho nuôi TikTok?
- **Đánh giá của anh Tony:** *"với nuôi tiktok a nghĩ là phải dùng header là phone sẽ đơn giản hơn"*.
- **Cơ sở kỹ thuật vững chắc:**
  1. TikTok Web Desktop có hệ thống phòng thủ bot cực nặng (FunCaptcha xoay hình, Wasm sensor, audio/canvas fingerprinting chặt chẽ, dễ bị `Maximum number of attempts reached`).
  2. TikTok Mobile Web (`m.tiktok.com`) được thiết kế cho điện thoại di động lướt trên mạng 4G/5G/Proxy động, thuật toán đánh giá bot nới lỏng hơn rất nhiều.
  3. Giao diện mobile dọc (9:16) gọn gàng, tải video nhẹ hơn 40%, thao tác vuốt cuộn (Touch scroll) tự nhiên, không bị vướng form phức tạp của desktop.

---

## 2. Thiết kế Giải pháp Kỹ thuật Chi tiết

### Module 1: Dynamic Proxy Geolocation & Timezone Resolver
- Tạo hàm bất đồng bộ `resolve_proxy_geo(proxy_host)`:
  - Tra cứu thông tin IP: Thành phố, Bang, Quốc gia, Múi giờ IANA chuẩn (`timezone`), Tọa độ (`latitude`, `longitude`).
  - Cache cục bộ cho các IP quen thuộc:
    * `50.114.98.173` -> Utah, `America/Denver`, Lat: `40.3032`, Lon: `-111.675`.
    * `23.27.210.99` -> Virginia, `America/New_York`, Lat: `38.9586`, Lon: `-77.357`.
    * `104.164.131.28` -> California, `America/Los_Angeles`, Lat: `37.7749`, Lon: `-122.419`.
  - Fallback tra cứu qua `http://ip-api.com/json/{host}` nếu gặp proxy mới.
- Áp dụng vào `Emulation.setTimezoneOverride` và `Emulation.setGeolocationOverride` tương ứng 100% với IP của proxy.
- Chuyển ngôn ngữ khởi chạy sang `--lang=en-US,en` và `Emulation.setLocaleOverride: "en-US"`.

### Module 2: Chuẩn Hóa Bộ Nhận Diện Điện Thoại (Android Phone Profile Standard)
Xây dựng pool thiết bị Android cao cấp (Google Pixel 8 Pro, Samsung Galaxy S24 Ultra):
1. **User Agent:**
   `Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.98 Mobile Safari/537.36`
2. **Client Hints (`Network.setUserAgentOverride`):**
   - `sec-ch-ua`: `"Chromium";v="134", "Not:A-Brand";v="24", "Google Chrome";v="134"`
   - `sec-ch-ua-mobile`: `?1`
   - `sec-ch-ua-platform`: `"Android"`
   - `sec-ch-ua-platform-version`: `"14.0.0"`
   - `sec-ch-ua-model`: `"Pixel 8 Pro"`
   - `platform`: `"Android"`
3. **Viewport & Touch Emulation:**
   - Kích thước màn hình ảo: `width: 412, height: 915, deviceScaleFactor: 2.625, mobile: true`.
   - `Emulation.setTouchEmulationEnabled: { enabled: true, maxTouchPoints: 5 }`.
   - Cửa sổ hiển thị trên màn hình Windows: `440x920` (vừa vặn khung điện thoại cho người dùng theo dõi).
4. **Navigator Stealth JS Injection:**
   - `navigator.platform = "Linux armv8l"`
   - `navigator.maxTouchPoints = 5`
   - `navigator.hardwareConcurrency = 8` (Octa-core CPU)
   - `navigator.deviceMemory = 8` (8 GB RAM)
   - `navigator.language = "en-US"`
   - `navigator.languages = ["en-US", "en"]`

### Module 3: Tối Ưu Hóa Nuôi TikTok Trên Giao Diện Mobile Web (`browser_nurture.rs`)
- Mặc định khởi chạy nuôi TikTok với chế độ Phone Headers.
- Tự động điều hướng vào `https://www.tiktok.com` với giao diện Mobile feed.
- Thao tác cuộn video bằng mô phỏng cảm ứng vuốt chạm Mobile Touch (`Input.dispatchTouchEvent` hoặc mouse drag dọc) thay vì phím mũi tên desktop.

---

## 3. Kế hoạch Kiểm thử & Tiêu chuẩn Nghiệm thu (Test Criteria)
1. **Kiểm thử Iphey.com:**
   - Cả 5 thẻ `BROWSER`, `LOCATION`, `IP ADDRESS`, `HARDWARE`, `SOFTWARE` đều đạt **GREEN CHECKMARK**.
   - MX Score đạt từ **90 - 100 điểm**.
   - Headline chuyển thành: **"Your Digital Identity Looks Trustworthy"**.
2. **Kiểm thử TikTok Mobile Feed:**
   - Truy cập `https://www.tiktok.com` tải giao diện mobile mượt mà, video tự động play, không bị vướng desktop recaptcha.
3. **Nghiệm thu Dây chuyền:**
   - Coder thi công đúng scope -> Tester chạy test thực tế xuất ảnh chứng minh -> Reviewer soi git diff và ban hành phán quyết.
