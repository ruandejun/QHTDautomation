# QHTD Store Desktop 🚀

Một công cụ máy tính chạy trên Windows bằng **PyQt5** mô phỏng tính năng hạ cấp ứng dụng iOS của **QHTD Store**. Ứng dụng này cho phép tải xuống các phiên bản cũ của ứng dụng trên App Store trực tiếp về máy tính Windows dưới dạng file `.ipa` đã được nhúng chữ ký bản quyền (SINF) chính chủ của tài khoản Apple ID của bạn.

---

## Tính năng chính

- **Xác thực Apple ID an toàn**: Kết nối trực tiếp tới API iTunes của Apple để lấy khóa tải app, hỗ trợ đầy đủ bảo mật 2 lớp (2FA).
- **Xem lịch sử phiên bản**: Tự động phân tích và lấy toàn bộ lịch sử các mã ID phiên bản của ứng dụng từ máy chủ Apple, đồng thời tải thông tin phiên bản dễ đọc (ví dụ: `1.0.0`, `2.4.2`) từ máy chủ hỗ trợ.
- **Ký bản quyền tự động**: Trích xuất chữ ký bản quyền dạng `.sinf` tương thích với tài khoản Apple ID của bạn và tự động nhúng vào cấu trúc file IPA, giúp cài đặt và chạy ứng dụng mà không bị crash DRM.
- **Giao diện Sleek Dark Mode**: Thiết kế hiện đại, mượt mà và trực quan với PyQt5 Stylesheet.

---

## Hướng dẫn cài đặt và sử dụng

### 1. Chuẩn bị (Prerequisites)
Hãy đảm bảo bạn đã cài đặt các thư viện Python cần thiết. Nếu bạn chạy trong môi trường ảo của dự án `antidetect-automatic`, các thư viện này thường đã có sẵn.

Nếu cần cài đặt thủ công, hãy chạy lệnh sau:
```bash
pip install PyQt5 requests
```

### 2. Chạy ứng dụng
Mở terminal tại thư mục dự án và chạy:
```bash
python main.py
```

### 3. Quy trình hạ cấp & tải IPA
1. **Đăng nhập Apple ID**:
   - Nhập tài khoản và mật khẩu Apple ID của bạn.
   - Nhấp **Đăng nhập**. Nếu tài khoản bật 2FA, một thông báo chứa mã 6 chữ số sẽ hiện ra trên thiết bị Apple của bạn.
   - Hãy điền mã 6 chữ số này vào ô **Mã 2FA** rồi nhấp lại nút **Xác minh 2FA** để hoàn tất xác thực.
2. **Tìm kiếm ứng dụng**:
   - Dán link App Store của ứng dụng bạn muốn hạ cấp hoặc nhập trực tiếp App ID của ứng dụng đó (ví dụ YouTube là `544007664`).
   - Nhấp **Tìm kiếm Ứng dụng**. Ứng dụng sẽ hiển thị hình ảnh icon, tên và danh sách các phiên bản cũ.
3. **Tải xuống phiên bản mong muốn**:
   - Chọn số phiên bản bạn muốn tải trong danh sách thả xuống.
   - Nhấp **Tải xuống tệp IPA** và chọn thư mục lưu tệp trên máy tính của bạn.
   - Chờ tiến trình tải xuống và nhúng chữ ký hoàn tất.

---

## Lưu ý quan trọng khi sử dụng

> [!WARNING]
> - **Tài khoản phải từng sở hữu ứng dụng**: Để tải được ứng dụng cũ, tài khoản Apple ID của bạn bắt buộc phải từng tải (hoặc mua) ứng dụng đó ít nhất một lần trong lịch sử mua hàng.
> - **Cách cài đặt file IPA**: File IPA tải về có chữ ký bản quyền của tài khoản của bạn. Bạn có thể sử dụng các công cụ phổ biến trên PC như **Sideloadly**, **AltStore**, hoặc **3uTools** để cài đặt trực tiếp vào thiết bị của mình mà không cần jailbreak.
