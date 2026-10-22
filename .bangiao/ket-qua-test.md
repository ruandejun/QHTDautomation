# KẾT QUẢ TEST (Tester) — 2026-10-22 01:33:44
- cargo test --release: 28 passed / 0 failed (5 test mới xml_login::signup: birthday_parse, birthday_is_adult, password_is_valid_for_tiktok, classify_feed_and_unknown, classify_real_screens).
- cargo build --release: OK.
## Live phone farm (ce0117112dccec3404, email C69 #21215 & #21214)
OK thật: EMAIL_CHECK, PROXY (egress US đối soát), IDENTITY (device_profile Rust), SignUpMenu, Birthday (verify EditText), PhoneEmailForm, nhập email (verify XML).
FAIL (môi trường): TikTok "Maximum number of attempts reached" ngay sau Continue email, 3/3 lần, đổi proxy+identity+email vẫn bị → chặn phía TikTok. Các màn sau (code/password/username) CHƯA verify live.
## Live Mun Browser (profile test 9995, IP nhà, không proxy)
OK thật: mở form, Birthday verify, email + password verify value, Send code → "Resend code", OTP về C69 (nhận đúng mã). Bước nhập mã bị "Maximum number of attempts reached" (IP/thiết bị bị đốt). Phát hiện + sửa: click chuột Send code không ăn → thêm verify + fallback JS click.
Không có nick nào được tạo; không có chuyện báo thành công giả.