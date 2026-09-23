# KẾ HOẠCH KHẮC PHỤC LỖI TỰ ĐỘNG BẤM NUÔI (AGENT 1 - PLANNER)

- **Mục tiêu:** 
  Chấm dứt hoàn toàn tình trạng tool tự động kích hoạt tiến trình nuôi khi anh Tony chưa chủ động bấm nút "Nuôi".
- **Ngày lập:** 2026-09-23
- **Nhánh triển khai:** `fix/disable-auto-nurture-trigger`
- **Người thực hiện:** Agent 1 (Planner)

---

## 1. Phân tích nguyên nhân gốc rễ (Root Cause Analysis - RCA)

Qua rà soát toàn bộ mã nguồn Rust và Frontend, em đã xác định được **2 nguyên nhân chính** dẫn đến việc tool tự động bấm nuôi:

### Nguyên nhân 1: Background Scheduler tự động kích hoạt nuôi (`start_auto_retry_scheduler`)
- Nằm trong `qhtd-farm-rust/src/browser_nurture.rs` (dòng 1597-1638), được gọi từ `main.rs` (dòng 101).
- Cơ chế cũ: Cứ mỗi 60 giây, scheduler tự quét file `browser_profiles.json`. Nếu một profile trước đó có `retry_after_epoch` (do rate limit hoặc chờ 1h) và thời gian hiện tại đã trôi qua mốc này:
  -> Hệ thống tự động gọi: `engine.start_nurture(prof, None).await`!
- Khi anh Tony mở tool lên, các profile có epoch cũ lập tức bị scheduler tự động khởi động và chạy quy trình nuôi!

### Nguyên nhân 2: Nút "🚀 Mở" Profile (Launch) tự động kích hoạt script nuôi TikTok
- Nằm trong `qhtd-farm-rust/src/cdp_browser.rs` (dòng 1625-1635).
- Cơ chế cũ: Khi người dùng bấm nút "🚀 Mở" chỉ để xem trình duyệt thủ công hoặc kiểm tra IP, hàm `launch_cdp_profile` lại kiểm tra nếu URL chứa `tiktok.com` thì tự động `tokio::spawn(check_and_handle_tiktok_login_cdp(...))` -> Tự kiểm tra, tự login và tự chuyển sang lướt `foryou`.

---

## 2. Kế hoạch sửa đổi kỹ thuật (Proposed Solution)

1. **Vô hiệu hóa tự động nuôi trong `start_auto_retry_scheduler` (`browser_nurture.rs`):**
   - Khi hết thời gian rate limit / giãn cách 1h, hệ thống CHỈ cập nhật nhãn trạng thái: `"Sẵn sàng (Đã hết 1h)"`, xóa `retry_after_epoch`.
   - **TUYỆT ĐỐI KHÔNG GỌI `start_nurture`!** Quyền quyết định nuôi thuộc về người dùng.
2. **Tách biệt hoàn toàn chế độ "Mở thủ công" (`launch_cdp_profile`) và "Chạy nuôi tự động" (`run_nurture_worker`):**
   - Xóa bỏ việc tự động gọi `check_and_handle_tiktok_login_cdp` trong `cdp_browser.rs` khi mở trình duyệt.
   - Nút "🚀 Mở" chỉ đơn thuần mở cửa sổ Chrome độc lập để người dùng thao tác bằng tay.
   - Tiến trình nuôi TikTok CHỈ ĐƯỢC CHẠY khi người dùng chủ động bấm:
     * Nút **"Nuôi"** của từng profile.
     * Nút **"Nuôi profiles đã chọn"** (`startNurtureSelectedProfiles`).
     * Nút **"Nuôi tất cả"** (`startNurtureAllProfiles`).
3. **Dọn dẹp `retry_after_epoch` tồn đọng trong `browser_profiles.json`** để không còn profile nào bị treo trạng thái kích hoạt ngầm.
