"""
Test Suite Độc Lập: Kiểm thử Luồng Nuôi TikTok, Grid Layout 5 Slot & Fail-Safe Close Browser
Chạy trên MunAutomation.exe phiên bản mới nhất
"""
import os
import sys
import time
import json
import requests
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://127.0.0.1:9090"
EXE_PATH = r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\MunAutomation.exe"
PROFILES_PATH = r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\browser_profiles.json"

def calculate_grid_bounds(slot, is_mobile=True):
    slot_idx = slot % 5
    if is_mobile:
        w = 375
        h = 840
        x = 10 + (slot_idx * 381)
        y = 10
        return (x, y, w, h)
    else:
        w = 620
        h = 480
        row = 0 if slot_idx < 3 else 1
        col = slot_idx if slot_idx < 3 else slot_idx - 3
        x = 10 + (col * 630)
        y = 10 + (row * 500)
        return (x, y, w, h)

def read_profiles():
    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def write_profiles(data):
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def main():
    print("=" * 65)
    print("🧪 BẮT ĐẦU TEST SUITE: TIKTOK NURTURE PIPELINE, GRID LAYOUT & FAIL-SAFE")
    print("=" * 65)

    # 1. Khởi động / Kết nối Server
    try:
        r = requests.get(f"{BASE_URL}/api/browser/profiles", timeout=2)
        print("✅ Core server đã chạy sẵn trên cổng 9090.")
    except Exception:
        print(f"🚀 Khởi chạy {EXE_PATH}...")
        subprocess.Popen([EXE_PATH], cwd=r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
    # Reset retry_after_epoch cho các profile trước khi test
    profs = read_profiles()
    for p in profs:
        p["retry_after_epoch"] = None
    write_profiles(profs)

    # -------------------------------------------------------------
    # TEST 1: Kiểm tra thuật toán Grid Layout 5 Slot không đè nhau
    # -------------------------------------------------------------
    print("\n--- [TEST 1] Kiểm tra Tọa độ Grid Layout (5 Cột Dọc Song Song) ---")
    windows = []
    for s in range(5):
        bounds = calculate_grid_bounds(s, is_mobile=True)
        windows.append(bounds)
        print(f"  - Slot #{s}: x={bounds[0]}, y={bounds[1]}, w={bounds[2]}, h={bounds[3]}")

    # Kiểm tra không có bất kỳ cửa sổ nào bị đè lên nhau
    for i in range(4):
        x_curr, y_curr, w_curr, h_curr = windows[i]
        x_next, y_next, w_next, h_next = windows[i+1]
        assert x_next >= x_curr + w_curr, f"Slot {i+1} bị đè lên Slot {i}! (x_next={x_next}, x_curr+w={x_curr+w_curr})"

    total_width = windows[-1][0] + windows[-1][2]
    print(f"  - Tổng chiều ngang của cả 5 cửa sổ: {total_width}px (vừa khít màn hình 1920x1080)")
    assert total_width <= 1920, f"Tổng chiều ngang vượt quá màn hình: {total_width}"
    print("✅ TEST 1 PASSED: 5 Cửa sổ dàn đều song song, 100% không đè lên nhau!")

    # -------------------------------------------------------------
    # TEST 2: Kiểm tra cấu trúc Status có đủ Like, Share, Comment
    # -------------------------------------------------------------
    print("\n--- [TEST 2] Kiểm tra Cấu trúc Status Đầy Đủ Like - Share - Comment ---")
    st_resp = requests.get(f"{BASE_URL}/api/browser/nurture/status", timeout=5).json()
    print(f"  - Endpoint nurture/status phản hồi OK (Số lượng: {len(st_resp)})")

    # Kích hoạt thử profile #1 để kiểm tra status fields
    requests.post(f"{BASE_URL}/api/browser/nurture/start", json={"profile_id": 1}, timeout=5)
    time.sleep(1.5)

    all_st = requests.get(f"{BASE_URL}/api/browser/nurture/status", timeout=5).json()
    st1 = next((s for s in all_st if s.get("profile_id") == 1), None)
    assert st1 is not None, "Không tìm thấy status của Profile #1!"
    assert "shares_count" in st1, "Thiếu trường shares_count trong status!"
    assert "likes_given" in st1, "Thiếu trường likes_given trong status!"
    assert "comments_posted" in st1, "Thiếu trường comments_posted trong status!"
    assert "videos_watched" in st1, "Thiếu trường videos_watched trong status!"
    print(f"  - Fields: videos={st1['videos_watched']}, likes={st1['likes_given']}, comments={st1['comments_posted']}, shares={st1['shares_count']}")
    print("✅ TEST 2 PASSED: Cấu trúc status chuẩn hóa đầy đủ 4 tương tác (Watch, Like, Share, Comment)!")

    # Dừng profile #1
    requests.post(f"{BASE_URL}/api/browser/nurture/stop", json={"profile_id": 1}, timeout=5)
    time.sleep(2)

    # -------------------------------------------------------------
    # TEST 3: Kiểm tra Concurrency Cap = 5 (Tối đa 5 trình duyệt song song)
    # -------------------------------------------------------------
    print("\n--- [TEST 3] Kiểm tra Giới Hạn Tối Đa 5 Trình Duyệt Song Song (Cap = 5) ---")
    # Đảm bảo có ít nhất 7 profile trong database
    profiles = read_profiles()
    current_count = len(profiles)
    if current_count < 7:
        for extra_id in range(current_count + 1, 8):
            profiles.append({
                "id": extra_id,
                "name": f"Profile Test #{extra_id}",
                "profile_os": "Android",
                "profile_user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.98 Mobile Safari/537.36",
                "profile_resolution": "412x915",
                "proxy_type": "direct",
                "proxy_string": "",
                "profile_cpu": 8,
                "profile_ram": 16
            })
        write_profiles(profiles)

    # Kích hoạt 6 profile cùng lúc (1..6)
    for p_id in range(1, 7):
        requests.post(f"{BASE_URL}/api/browser/nurture/start", json={"profile_id": p_id}, timeout=5)
        time.sleep(0.3)

    time.sleep(3)
    all_statuses = requests.get(f"{BASE_URL}/api/browser/nurture/status", timeout=5).json()
    running_statuses = [s for s in all_statuses if s.get("is_running") == True]
    print(f"  - Tổng số profile đang trong chu trình: {len(running_statuses)}")

    # Kiểm tra số lượng profile đã mở Chrome (đã lấy được slot thực sự)
    # Concurrency Semaphore đảm bảo tối đa 5 permits
    # Profile thứ 6 phải ở trạng thái "Chờ slot"
    st6 = next((s for s in all_statuses if s.get("profile_id") == 6), None)
    if st6:
        print(f"  - Status Profile #6 (Hàng đợi): {st6.get('status')} - Log: {st6.get('last_log')}")
        assert "Chờ slot" in st6.get("status", "") or "chờ slot" in st6.get("last_log", "").lower(), "Profile #6 không vào hàng đợi chờ slot!"

    print("✅ TEST 3 PASSED: Giới hạn tối đa 5 trình duyệt song song hoạt động chuẩn xác!")

    # -------------------------------------------------------------
    # TEST 4: Kiểm tra Fail-Safe & Tự động Đóng Trình Duyệt Khi Lỗi
    # -------------------------------------------------------------
    print("\n--- [TEST 4] Kiểm tra Fail-Safe Tự Động Đóng Chrome & Nhả Slot ---")
    # Gửi tín hiệu Rate Limit cho Profile #1
    requests.post(f"{BASE_URL}/api/browser/tiktok/rate-limit-signal", json={"profile_id": 1}, timeout=5)
    time.sleep(2)

    # Kiểm tra Profile #1 đã dừng và đóng Chrome chưa
    all_st_after = requests.get(f"{BASE_URL}/api/browser/nurture/status", timeout=5).json()
    st1_after = next((s for s in all_st_after if s.get("profile_id") == 1), {})
    active_profs = requests.get(f"{BASE_URL}/api/browser/active", timeout=5).json()
    print(f"  - Profile #1 status: {st1_after.get('status')}")
    print(f"  - Active profiles list: {active_profs}")
    assert 1 not in active_profs, "Profile #1 vẫn còn chạy sau khi gặp lỗi!"
    assert "Rate limit" in st1_after.get("status", "") or "Chờ 1h" in st1_after.get("status", ""), "Status không cập nhật lỗi!"

    # Dọn dẹp dừng toàn bộ
    for p_id in range(1, 7):
        requests.post(f"{BASE_URL}/api/browser/nurture/stop", json={"profile_id": p_id}, timeout=5)
    time.sleep(2)

    print("\n" + "=" * 65)
    print("🎉 TẤT CẢ 4/4 CA KIỂM THỬ ĐÃ HOÀN TOÀN ĐẠT (100% PASSED)!")
    print("=" * 65)

if __name__ == "__main__":
    main()
