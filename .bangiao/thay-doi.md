# THAY ĐỔI (Coder) — 2026-10-22 01:33:44
Nhánh feat/device-fingerprint-v2 (chưa commit).
- NEW src/xml_signup.rs (mod con xml_login::signup, khai báo `#[path]` trong xml_login.rs): auto signup phone farm bằng XML + pick_unused_emails + register_on_c69 (pub).
- src/api.rs: thêm /api/farm/xml-signup/{start,status,stop}; farm_auto_reg_tiktok_handler + status chuyển sang Rust (bỏ spawn python run_farm_auto_reg_all.py).
- src/browser_nurture.rs: auto_register_tiktok_by_gmail viết lại thật (CDP, verify từng bước, chỉ OK khi có cookie sessionid) + helper web_*; fetch_c69_email_otp uỷ quyền bản kiểm tra độ tươi (<=600s).