# KẾ HOẠCH IMPORT 20 TÀI KHOẢN C69 (USERNAME USERXXXXX) VÀ RESET PROFILE (AGENT 1 - PLANNER)

- **Mục tiêu:**
  1. Xóa toàn bộ các Profile cũ đang có trong hệ thống để làm sạch môi trường.
  2. Kết nối tới C69 Backend API (`https://cu.c69.us`), lọc và lấy chính xác 20 tài khoản TikTok có Username bắt đầu bằng `userxxxxx` (đầy đủ mật khẩu và email).
  3. Tạo mới 20 Profile (ID từ 0 đến 19) với cấu hình Phone Emulation chuẩn (Android 14, Pixel 8 Pro, mobile viewport 412x915, GPU pool và Canvas/Audio seed độc lập).
  4. Gán luân phiên 3 SOCKS5 proxy dân cư US chất lượng cao từ C69 Router.
  5. Lưu vào cả 2 vị trí: `MunAutomationDesktop/browser_profiles.json` và `browser_profiles.json`.
- **Ngày lập:** 2026-09-23
- **Nhánh triển khai:** `feature/import-20-c69-user-accounts`
- **Người thực hiện:** Agent 1 (Planner)

---

## 1. Danh sách 20 tài khoản C69 dự kiến import

Từ C69 API (`https://cu.c69.us/dashboard/api/accounts/?type=tiktok&search=user&page_size=50`):
1. `ID=16819` | `user475761481557` (Email: `grychglucasl9uez8@hotmail.com`)
2. `ID=16818` | `user83562995022056` (Email: `supertsoucy57o05t@hotmail.com`)
3. `ID=16808` | `user1520468208572` (Email: `brandonvqmrodrigueztt660@outlook.com`)
4. `ID=16807` | `user1093481327113` (Email: `anthonyvfxmoralesmw703@outlook.com`)
5. `ID=16803` | `user58108599773320` (Email: `heidiglenguyenlc470@outlook.com`)
6. `ID=16802` | `user9991105082684` (Email: `lindsay.mdi@outlook.com`)
7. `ID=16801` | `user3918235291261` (Email: `camacholi.17031983@outlook.com`)
8. `ID=16800` | `user6556562888156` (Email: `knightnf.21021984@outlook.com`)
9. `ID=16798` | `user4910348126130` (Email: `ebonydruhernandezfi27101984@outlook.com`)
10. `ID=16797` | `user9679302957410` (Email: `chavezyimmorganmy895@hotmail.com`)
11. `ID=16795` | `user72195754912033` (Email: `kathrynew.pkrausewz8912@outlook.com`)
12. `ID=16789` | `user3152617096654` (Email: `ernestinabouer480@hotmail.com`)
13. `ID=16785` | `user71750594603561` (Email: `julieldmsfleminghaz556@outlook.com`)
14. `ID=16782` | `user9575671291098` (Email: `craighfmpeckwd3551@outlook.com`)
15. `ID=16781` | `user3927530918796` (Email: `dauvideotwiatsongo422@outlook.com`)
16. `ID=16775` | `user58541901623734` (Email: `timothyfs19031988@hotmail.com`)
17. `ID=16774` | `user4480704572311` (Email: `nayraw.patel8418@outlook.com`)
18. `ID=16773` | `user1961267858417` (Email: `jessicatsmbcollinsmm9570@outlook.com`)
19. `ID=16772` | `user7945651172672` (Email: `arthur.ndi@outlook.com`)
20. `ID=16770` | `user6681263971638` (Email: `davidjitwrsporterulne22091998@hotmail.com`)

---

## 2. Thông số kỹ thuật cho 20 Profiles mới
- **Hệ điều hành:** `Android` (Mobile Phone Emulation)
- **Thiết bị:** Google Pixel 8 Pro
- **User-Agent:** `Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.98 Mobile Safari/537.36`
- **Độ phân giải:** `412x915` (tỷ lệ chuẩn màn hình điện thoại)
- **Engine Mode:** `js_stealth`
- **Start URL:** `https://iphey.com`
- **SOCKS5 Proxy Pool:** Luân phiên 3 SOCKS5 proxy US (`50.114.98.173`, `23.27.210.99`, `104.164.131.28`).
- **Fingerprint:** GPU pool luân phiên, Audio & Canvas Seed ngẫu nhiên theo ID để chống nhận diện liên đới.
- **Trạng thái ban đầu:** `Sẵn sàng`, `retry_after_epoch: null` (Không tự động chạy nuôi).
