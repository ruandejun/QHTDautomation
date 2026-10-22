# KẾ HOẠCH — Auto tạo TikTok (Phone Farm XML + Mun Browser) — 2026-10-22

## Mục tiêu
1. Audit code vừa viết (captcha_solver, xml_login 2FA/C69 sync, tiktok nurture).
2. Phone farm: tự đăng ký TikTok bằng **email C69 + OTP đọc từ C69**, điều khiển hoàn toàn bằng **XML UI dump** (không toạ độ mù).
3. Mun Browser (CDP): chức năng tương tự trên TikTok web.
4. Tài liệu cho Hermes.

## Thiết kế
### Phone farm — `src/xml_signup.rs` (mod con `xml_login::signup`)
Luồng 1 máy / 1 email (`signup_one`):
`EMAIL_CHECK (C69 đọc được?) → PROXY (router, egress US verify) → IDENTITY (device_profile::apply_new | reset_app_clean) → launch TikTok → vòng classify(XML) → handler từng màn → verify → lưu C69`.
- `classify(&Screen) -> SignupScreen` thuần (test được bằng XML giả).
- Birthday: 3 SeekBar picker, vuốt trong bounds, **đọc lại EditText "Month D, YYYY"** để verify (vòng kín).
- OTP: `wait_otp` → `fetch_otp_from_c69` (chỉ mã ≤ 600s) + loại các mã đã dùng.
- RATE_LIMIT ("Maximum number of attempts"): đổi proxy + identity, thử lại tối đa 3 lần.
- Thành công chỉ khi vào Feed/Profile có username thật → `add-manual` C69 (+ accounts_emails_id).
- API: `POST /api/farm/xml-signup/start {emails:[{email,email_id,password?}],serials?,auto_count?,client?}`, `GET .../status`, `POST .../stop`. `/api/farm/auto-reg-tiktok` giờ gọi module Rust (bỏ Python).

### Mun Browser — `browser_nurture.rs::auto_register_tiktok_by_gmail` (route `/api/browser/nurture/auto-reg-gmail`)
Tên giữ cho tương thích, nội dung viết lại thật: email C69 → birthday (combobox role) → email+password (verify value) → Send code (verify nút chuyển "Resend code") → OTP tươi C69 → nhập mã → username → **chỉ thành công khi có cookie `sessionid`** → backup profile → C69 add-manual + sync cookies.

## Rủi ro / Edge
- TikTok trả "Maximum number of attempts reached" (rate-limit theo thiết bị/IP/email) → không bypass được bằng code; cần IP sạch/residential & email mới.
- Proxy whitelist `us_proxies_whitelist.json` chỉ dùng được từ router (IP đã whitelist), không dùng trực tiếp trên PC.
- Email loại `8edu` trả 500 (không đọc được OTP) → bị lọc bởi `check_c69_email_readable`.
