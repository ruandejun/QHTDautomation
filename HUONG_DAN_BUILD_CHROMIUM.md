# Hướng Dẫn Kích Hoạt Build Custom Chromium C++ Trên GitHub Actions

Tài liệu này hướng dẫn cách chạy Workflow build trình duyệt **QHTD Anti-Detect Chromium Core** hoàn toàn tự động trên hạ tầng máy chủ của GitHub (GitHub Actions), không tốn dung lượng ổ đĩa hay CPU máy cá nhân.

---

## 1. Cấu Trúc Bộ Patch C++ Đã Tạo Trong Repository

Toàn bộ patch C++ nằm tại thư mục `chromium-patches/`:
* `01_navigator_hardware.patch`: Chèn switch `--qhtd-hardware-concurrency` và `--qhtd-device-memory` vào `navigator.cc` để giả lập số luồng CPU và dung lượng RAM ở tầng Native C++.
* `02_canvas_noise.patch`: Chèn sub-pixel noise vào `base_rendering_context_2d.cc` theo tham số `--qhtd-canvas-noise=<seed>` trước khi trả về `getImageData()`.
* `03_webgl_spoof.patch`: Can thiệp `webgl_rendering_context_base.cc` để gán GPU Vendor và Renderer thông qua `--qhtd-webgl-vendor` và `--qhtd-webgl-renderer`.
* `04_audio_noise.patch`: Chèn vi sai âm thanh vào `audio_buffer.cc` theo `--qhtd-audio-noise=<seed>` cho AudioContext Fingerprint.

---

## 2. Cách Kích Hoạt Build Trên GitHub

1. Truy cập vào GitHub repository của anh: `https://github.com/ruandejun/QHTDautomation`
2. Chọn tab **Actions** trên thanh menu.
3. Ở cột bên trái, bấm chọn workflow: **Build Custom Anti-Detect Chromium Core**.
4. Bấm nút **Run workflow**:
   * Nhập Release Tag: `v128.0.0-qhtd` (hoặc phiên bản mong muốn).
   * Bấm nút màu xanh **Run workflow**.
5. GitHub Actions sẽ tự động khởi tạo máy ảo Windows x64:
   * Tải Google `depot_tools`.
   * Kéo mã nguồn Chromium.
   * Apply toàn bộ 4 file C++ patches trong `chromium-patches/`.
   * Biên dịch file thực thi `chrome.exe` và đóng gói thành `qhtd-browser-windows-x64.zip`.
   * Tự động tạo bản Release và đính kèm file ZIP sẵn sàng tải về.

---

## 3. Cách Sử Dụng Sau Khi Tải Về

Sau khi GitHub Actions build xong:
1. Tải file `qhtd-browser-windows-x64.zip` từ mục **Releases** về máy.
2. Giải nén vào thư mục `d:\Workspace\Python\QHTDautomation\qhtd-browser\` (sao cho có file `qhtd-browser.exe` hoặc `chrome.exe` trong đó).
3. Hệ thống **QHTD Farm Rust Core** (`qhtd-farm-core.exe` / `QHTD_Automation_Rust.exe`) đã được lập trình sẵn cơ chế tự nhận diện:
   * Nếu có thư mục `qhtd-browser/`: Tự động sử dụng Custom Chromium C++ Core với 100% Native Anti-Detect Flags.
   * Nếu chưa tải: Tự động fallback dùng Google Chrome mặc định của máy với bộ lá chắn Stealth CDP sẵn có.
