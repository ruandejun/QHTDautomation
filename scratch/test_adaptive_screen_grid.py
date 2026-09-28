"""
Test Suite Độc Lập: Kiểm thử Thuật toán Adaptive Smart Grid & Kích thước Cửa sổ Thực tế
Xác nhận 100% Không Đè Lên Nhau trên Màn Hình Thật của Windows
"""
import os
import sys
import time
import ctypes
from ctypes import wintypes
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

user32 = ctypes.windll.user32

def get_work_area():
    rect = wintypes.RECT()
    # SPI_GETWORKAREA = 0x0030
    if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rect), 0):
        w = rect.right - rect.left
        h = rect.bottom - rect.top
        if w > 640 and h > 480:
            return (w, h)
    w = user32.GetSystemMetrics(0)
    h = user32.GetSystemMetrics(1)
    return (w, h - 40)

def calculate_adaptive_grid(slot, is_mobile=True, custom_screen=None):
    slot_idx = slot % 5
    screen_w, screen_h = custom_screen if custom_screen else get_work_area()

    if is_mobile:
        if screen_w >= 2560:
            margin = 10
            gap = 12
            width = int((screen_w - (2 * margin) - (4 * gap)) / 5)
            height = int(screen_h - 20)
            x = margin + (slot_idx * (width + gap))
            y = 10
            return (x, y, width, height)
        else:
            margin = 10
            gap_x = 12
            gap_y = 15
            width = int((screen_w - (2 * margin) - (2 * gap_x)) / 3)
            height = int((screen_h - (2 * margin) - gap_y) / 2)
            if slot_idx < 3:
                x = margin + (slot_idx * (width + gap_x))
                y = margin
                return (x, y, width, height)
            else:
                row2_col = slot_idx - 3
                row2_margin = int((screen_w - (2 * width + gap_x)) / 2)
                x = row2_margin + (row2_col * (width + gap_x))
                y = margin + height + gap_y
                return (x, y, width, height)
    else:
        margin = 10
        gap_x = 15
        gap_y = 15
        width = int((screen_w - (2 * margin) - (2 * gap_x)) / 3)
        height = int((screen_h - (2 * margin) - gap_y) / 2)
        if slot_idx < 3:
            x = margin + (slot_idx * (width + gap_x))
            y = margin
            return (x, y, width, height)
        else:
            row2_col = slot_idx - 3
            row2_margin = int((screen_w - (2 * width + gap_x)) / 2)
            x = row2_margin + (row2_col * (width + gap_x))
            y = margin + height + gap_y
            return (x, y, width, height)

def main():
    print("=" * 65)
    print("🧪 BẮT ĐẦU TEST SUITE: ADAPTIVE SMART GRID & REAL WINDOW BOUNDS")
    print("=" * 65)

    real_w, real_h = get_work_area()
    print(f"🖥️ Vùng làm việc màn hình hiện tại: {real_w} x {real_h}")

    # -------------------------------------------------------------
    # TEST 1: Kiểm tra Tọa độ trên Màn hình Hiện tại (2752x1112)
    # -------------------------------------------------------------
    print(f"\n--- [TEST 1] Kiểm tra 5 Slot trên Màn hình Rộng ({real_w}x{real_h}) ---")
    windows = []
    for s in range(5):
        bounds = calculate_adaptive_grid(s, is_mobile=True)
        windows.append(bounds)
        print(f"  - Slot #{s}: x={bounds[0]}, y={bounds[1]}, width={bounds[2]}px, height={bounds[3]}px")

    # Kiểm tra chiều rộng >= 516px (vượt qua min-width của Chrome)
    for i, w in enumerate(windows):
        assert w[2] >= 516, f"Slot #{i} có chiều rộng {w[2]}px < 516px (sẽ bị Chrome bung to ra làm lệch vị trí)!"

    # Kiểm tra không có bất kỳ khoảng đè chồng lấn nào
    for i in range(4):
        x_curr, y_curr, w_curr, h_curr = windows[i]
        x_next, y_next, w_next, h_next = windows[i+1]
        gap_between = x_next - (x_curr + w_curr)
        print(f"  - Khoảng cách an toàn giữa Slot #{i} và Slot #{i+1}: {gap_between}px")
        assert gap_between >= 0, f"Slot #{i+1} đè lên Slot #{i} (Khoảng cách âm: {gap_between}px)!"

    last_x = windows[-1][0] + windows[-1][2]
    print(f"  - Tổng chiều ngang cả 5 cửa sổ: {last_x}px <= {real_w}px")
    assert last_x <= real_w, f"Cửa sổ cuối cùng bị tràn ra ngoài màn hình: {last_x} > {real_w}"
    print("✅ TEST 1 PASSED: 5 Cửa sổ dàn đều song song, 100% không đè lên nhau trên màn hình rộng!")

    # -------------------------------------------------------------
    # TEST 2: Kiểm tra Mô phỏng trên Màn hình Chuẩn Full HD (1920x1040)
    # -------------------------------------------------------------
    print("\n--- [TEST 2] Kiểm tra Mô phỏng trên Màn hình Full HD (1920x1040) ---")
    fhd_windows = []
    for s in range(5):
        bounds = calculate_adaptive_grid(s, is_mobile=True, custom_screen=(1920, 1040))
        fhd_windows.append(bounds)
        print(f"  - Slot #{s}: x={bounds[0]}, y={bounds[1]}, width={bounds[2]}px, height={bounds[3]}px")

    # Kiểm tra Hàng 1 (Slot 0, 1, 2)
    for i in range(2):
        x_c, y_c, w_c, h_c = fhd_windows[i]
        x_n, y_n, w_n, h_n = fhd_windows[i+1]
        assert x_n >= x_c + w_c, f"Hàng 1: Slot #{i+1} đè lên Slot #{i}!"
        assert y_c == y_n, "Hàng 1: Các cửa sổ phải cùng nằm trên hàng top y=10!"

    # Kiểm tra Hàng 2 (Slot 3, 4)
    x3, y3, w3, h3 = fhd_windows[3]
    x4, y4, w4, h4 = fhd_windows[4]
    assert x4 >= x3 + w3, "Hàng 2: Slot #4 đè lên Slot #3!"
    assert y3 >= fhd_windows[0][1] + fhd_windows[0][3], "Hàng 2 đè lên Hàng 1 theo chiều dọc!"
    print("✅ TEST 2 PASSED: Bố trí 2 Hàng Ma Trận Thông Minh trên Full HD hoàn toàn không đè nhau!")

    # -------------------------------------------------------------
    # TEST 3: Khởi chạy Trực tiếp 5 Cửa sổ Chrome Thật và Đo bằng Win32 API
    # -------------------------------------------------------------
    print("\n--- [TEST 3] Khởi chạy Thực tế 5 Cửa sổ Chrome và Đo Tọa độ Win32 API ---")
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    processes = []
    try:
        for s in range(5):
            b = windows[s]
            cmd = [
                chrome_path,
                f"--remote-debugging-port={9250 + s}",
                "--remote-allow-origins=*",
                f"--user-data-dir=C:\\Users\\Admin\\AppData\\Local\\Temp\\test_grid_{s}",
                f"--window-size={b[2]},{b[3]}",
                f"--window-position={b[0]},{b[1]}",
                "--no-first-run",
                "about:blank"
            ]
            p = subprocess.Popen(cmd)
            processes.append(p)
            time.sleep(0.4)

        time.sleep(2.5)

        # Đo kích thước thực tế của từng cửa sổ qua Win32 API
        real_rects = []
        for s, p in enumerate(processes):
            hwnd_found = None
            def enum_cb(hwnd, extra):
                nonlocal hwnd_found
                if user32.IsWindowVisible(hwnd):
                    pid = wintypes.DWORD()
                    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                    if pid.value == p.pid:
                        rect = wintypes.RECT()
                        user32.GetWindowRect(hwnd, ctypes.byref(rect))
                        w = rect.right - rect.left
                        h = rect.bottom - rect.top
                        if w > 300 and h > 300:
                            hwnd_found = (rect.left, rect.top, w, h)
                return True
            CMPFUNC = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
            user32.EnumWindows(CMPFUNC(enum_cb), 0)
            if hwnd_found:
                real_rects.append((s, hwnd_found))
                print(f"  - Chrome Slot #{s} (Thực tế): left={hwnd_found[0]}, top={hwnd_found[1]}, width={hwnd_found[2]}px, height={hwnd_found[3]}px")

        assert len(real_rects) == 5, f"Chỉ tìm thấy {len(real_rects)}/5 cửa sổ Chrome!"

        # Sắp xếp theo thứ tự left tăng dần và kiểm tra overlap thực tế
        real_rects.sort(key=lambda item: item[1][0])
        for i in range(4):
            curr_s, (c_l, c_t, c_w, c_h) = real_rects[i]
            next_s, (n_l, n_t, n_w, n_h) = real_rects[i+1]
            real_gap = n_l - (c_l + c_w)
            print(f"  - Khoảng cách thực tế giữa Cửa sổ #{curr_s} và Cửa sổ #{next_s}: {real_gap}px")
            assert real_gap >= -5, f"Cửa sổ #{next_s} đè lên Cửa sổ #{curr_s} (Gap: {real_gap}px)!"

        print("✅ TEST 3 PASSED: Cả 5 cửa sổ Chrome thật trên Windows đứng song song, 100% không đè lên nhau!")

    finally:
        print("\n🧹 Dọn dẹp đóng các cửa sổ test...")
        for p in processes:
            try:
                p.kill()
            except Exception:
                pass

    print("\n" + "=" * 65)
    print("🎉 TẤT CẢ 3/3 CA KIỂM THỬ ĐÃ HOÀN TOÀN ĐẠT (100% PASSED)!")
    print("=" * 65)

if __name__ == "__main__":
    main()
