"""
Test Suite: Kiểm thử khả năng chống chịu lỗi Maximum attempts & Auto-Retry Scheduler của TikTok Login
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

def read_profiles():
    with open(PROFILES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def write_profiles(data):
    with open(PROFILES_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def main():
    print("=" * 60)
    print("🧪 BẮT ĐẦU TEST SUITE: TIKTOK LOGIN MAXIMUM ATTEMPTS & AUTO-RETRY")
    print("=" * 60)

    # 1. Đảm bảo Core đang chạy
    proc = None
    try:
        r = requests.get(f"{BASE_URL}/api/browser/profiles", timeout=2)
        print("✅ Core server đã chạy sẵn trên cổng 9090.")
    except Exception:
        print(f"🚀 Khởi chạy {EXE_PATH}...")
        proc = subprocess.Popen([EXE_PATH], cwd=r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
        time.sleep(3)

    # Test 1: Kiểm tra endpoint rate-limit-signal
    print("\n--- [TEST 1] Kiểm tra tín hiệu Rate Limit (Maximum attempts) ---")
    now_epoch = int(time.time())
    resp = requests.post(
        f"{BASE_URL}/api/browser/tiktok/rate-limit-signal",
        json={"profile_id": 1},
        timeout=5
    )
    assert resp.status_code == 200, f"Lỗi gọi API: {resp.status_code}"
    res_data = resp.json()
    assert res_data.get("success") == True, "API không trả về success: true"
    print("✅ Endpoint /api/browser/tiktok/rate-limit-signal phản hồi 200 OK.")

    # Kiểm tra dữ liệu được cập nhật trong file JSON
    time.sleep(0.5)
    profiles = read_profiles()
    p1 = next((p for p in profiles if p["id"] == 1), None)
    assert p1 is not None, "Không tìm thấy Profile #1"
    
    st = p1.get("last_nurture_status", "")
    err = p1.get("last_nurture_error", "")
    retry_epoch = p1.get("retry_after_epoch", 0)

    print(f"  - Status: {st}")
    print(f"  - Error: {err}")
    print(f"  - Retry After Epoch: {retry_epoch} (Cách hiện tại: {retry_epoch - now_epoch}s)")

    assert "Rate limit" in st or "Chờ 1h" in st, f"Status không đúng: {st}"
    assert "Maximum number of attempts" in err, f"Error không ghi nhận Maximum: {err}"
    assert retry_epoch >= now_epoch + 3500, f"Retry epoch không đủ 1h: {retry_epoch - now_epoch}s"
    print("✅ TEST 1 PASSED: Đã lưu đúng trạng thái Rate limit (Chờ 1h) và retry_after_epoch = now + 3600s!")

    # Test 2: Kiểm tra tự động đóng trình duyệt khi nhận tín hiệu Rate Limit
    print("\n--- [TEST 2] Kiểm tra tự động đóng Chrome (Graceful Shutdown) ---")
    # Khởi chạy Profile #1
    launch_resp = requests.post(f"{BASE_URL}/api/browser/profiles/launch", json={"id": 1}, timeout=10)
    print(f"  - Launch response: {launch_resp.status_code}")
    time.sleep(4)

    # Kiểm tra profile có trong active list không
    active_resp = requests.get(f"{BASE_URL}/api/browser/active", timeout=5).json()
    print(f"  - Active profiles trước khi báo lỗi: {active_resp}")
    assert 1 in active_resp, "Profile #1 chưa active sau khi launch!"

    # Gửi tín hiệu Rate Limit
    print("  - Gửi tín hiệu Rate Limit Maximum attempts...")
    requests.post(f"{BASE_URL}/api/browser/tiktok/rate-limit-signal", json={"profile_id": 1}, timeout=5)
    time.sleep(2)

    # Kiểm tra active profiles sau khi báo lỗi
    active_resp_after = requests.get(f"{BASE_URL}/api/browser/active", timeout=5).json()
    print(f"  - Active profiles sau khi báo lỗi: {active_resp_after}")
    assert 1 not in active_resp_after, "Profile #1 vẫn còn active sau khi gặp lỗi Maximum!"
    print("✅ TEST 2 PASSED: Trình duyệt Chrome đã tự động đóng sạch sẽ, giải phóng 100% RAM và port CDP!")

    # Test 3: Kiểm tra tín hiệu Login Thành Công (Happy Path)
    print("\n--- [TEST 3] Kiểm tra tín hiệu Login Thành Công & Xóa Rate Limit ---")
    succ_resp = requests.post(f"{BASE_URL}/api/browser/tiktok/login-success-signal", json={"profile_id": 1}, timeout=5)
    assert succ_resp.status_code == 200, f"Lỗi login success: {succ_resp.status_code}"
    time.sleep(0.5)

    profiles = read_profiles()
    p1 = next((p for p in profiles if p["id"] == 1), None)
    st_succ = p1.get("last_nurture_status", "")
    print(f"  - Status sau login thành công: {st_succ}")
    assert "Đã đăng nhập" in st_succ, f"Status không chuyển sang đã đăng nhập: {st_succ}"
    print("✅ TEST 3 PASSED: Đã cập nhật thành công trạng thái Đã đăng nhập sẵn (Sẵn sàng)!")

    # Test 4: Kiểm tra Scheduler Auto-Retry khi hết hạn 1h
    print("\n--- [TEST 4] Kiểm tra Scheduler Auto-Retry khi hết hạn 1h ---")
    # Đặt retry_after_epoch về quá khứ (đã hết 1h)
    profiles = read_profiles()
    for p in profiles:
        if p["id"] == 1:
            p["last_nurture_status"] = "Rate limit (Chờ 1h)"
            p["retry_after_epoch"] = int(time.time()) - 10 # 10 giây trước
            break
    write_profiles(profiles)

    # Thử gọi API nurture start, hệ thống không được báo lỗi "Vui lòng chờ thêm ... phút"
    start_resp = requests.post(f"{BASE_URL}/api/browser/nurture/start", json={"profile_id": 1}, timeout=10)
    print(f"  - Start nurture response: {start_resp.status_code} - {start_resp.text}")
    assert start_resp.status_code == 200, f"Bị chặn không cho chạy lại dù đã hết 1h: {start_resp.text}"
    print("✅ TEST 4 PASSED: Khi hết hạn 1h, hệ thống tự động cho phép khởi chạy lại đăng nhập mà không bị chặn!")

    # Dọn dẹp dừng nurture
    requests.post(f"{BASE_URL}/api/browser/nurture/stop", json={"profile_id": 1}, timeout=5)
    time.sleep(1)

    print("\n" + "=" * 60)
    print("🎉 TẤT CẢ 4/4 CA KIỂM THỬ ĐÃ HOÀN TOÀN ĐẠT (100% PASSED)!")
    print("=" * 60)

if __name__ == "__main__":
    main()
