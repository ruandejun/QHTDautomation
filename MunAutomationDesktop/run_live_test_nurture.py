"""
Test Standalone: Chay thu nghiem chuc nang nuoi TikTok voi tai khoan thuc te tu cu.c69.us
- Ket noi lay Proxy tu https://cu.c69.us/250
- Khong dung headless (hien thi browser that)
- Doc mail OTP tu dong qua OAuth2 C69 (Graph API)
- Kiem tra username / nickname & avatar
- Luot TikTok FYP tu nhien
"""
import asyncio
import os
import sys
import random
import requests

# Set working dir
os.chdir("D:/Workspace/Python/QHTDautomation/MunAutomationDesktop")
sys.path.append("D:/Workspace/Python/QHTDautomation/MunAutomationDesktop")

from tiktok_nurture import NurtureConfig, TikTokNurtureSession

def get_live_proxy_from_c69():
    """Lay 1 proxy song ngau nhien tu endpoint https://cu.c69.us/250"""
    try:
        url = "https://cu.c69.us/250"
        print(f"📡 Đang tải danh sách Proxy từ {url}...")
        r = requests.get(url, timeout=10)
        if r.status_code == 200 and r.text.strip():
            lines = [l.strip() for l in r.text.strip().splitlines() if l.strip() and not l.startswith('#')]
            print(f"✅ Tải thành công {len(lines)} proxies từ cu.c69.us/250.")
            random.shuffle(lines)
            # Test nhanh 5 candidate xem co connect duoc khong
            for line in lines[:8]:
                parts = line.split(':')
                if len(parts) == 4:
                    host, port, user, pwd = parts
                    proxy_socks = f"socks5://{user}:{pwd}@{host}:{port}"
                    proxies_dict = {'http': proxy_socks, 'https': proxy_socks}
                    try:
                        r_test = requests.get("https://api.ipify.org?format=json", proxies=proxies_dict, timeout=4)
                        if r_test.status_code == 200:
                            out_ip = r_test.json().get("ip")
                            print(f"🟢 Chọn được Proxy Live chất lượng: {host}:{port} (Out IP: {out_ip})")
                            return line
                    except Exception:
                        continue
            # Fallback tra ve proxy dau tien
            return lines[0]
    except Exception as e:
        print(f"⚠️ Lỗi lấy proxy từ cu.c69.us/250: {e}")
    return ""

def main():
    print("==================================================")
    print("🚀 BẮT ĐẦU CHẠY THỬ NGHIỆM CHỨC NĂNG NUÔI TIKTOK")
    print("🌐 C69 API: https://cu.c69.us")
    print("🛡️ Proxy Pool: https://cu.c69.us/250")
    print("🖥️ Chế độ: MỞ PROFILE MỚI, KHÔNG HEADLESS")
    print("==================================================")

    # 1. Ket noi API cu.c69.us de lay tai khoan TikTok hop le
    headers = {"Authorization": "Token 99b02d3d255a49193950777b1cc3e3db099ceefb"}
    c69_base = "https://cu.c69.us"

    print("🔍 Đang truy vấn tài khoản TikTok có sub OK & đọc được OAuth2...")
    r = requests.get(f"{c69_base}/dashboard/api/accounts/?type=tiktok&page_size=25", headers=headers, timeout=12)
    if r.status_code != 200:
        print(f"❌ Lỗi truy vấn C69 API: {r.status_code} {r.text}")
        return

    accounts = r.json().get("results", [])
    selected_acc = None

    # Uu tien cac tai khoan chua bi attempt
    priority_ids = [16504, 16503, 16502, 16501, 16500, 16499, 16498]
    for p_id in priority_ids:
        r_p = requests.get(f"{c69_base}/dashboard/api/accounts/{p_id}/", headers=headers, timeout=10)
        if r_p.status_code == 200:
            acc = r_p.json()
            ae_id = acc.get("accounts_emails")
            if ae_id and acc.get("password") and acc.get("email"):
                r_mail = requests.get(f"{c69_base}/dashboard/api/emails/{ae_id}/read-mailbox/", headers=headers, timeout=8)
                if r_mail.status_code == 200 and r_mail.json().get("success"):
                    selected_acc = acc
                    print(f"🎯 Đã chọn tài khoản mục tiêu: {acc['email']} | User: @{acc['username']} | AE_ID: {ae_id}")
                    break

    if not selected_acc:
        for acc in accounts:
            ae_id = acc.get("accounts_emails")
            if ae_id and acc.get("password") and acc.get("email"):
                r_mail = requests.get(f"{c69_base}/dashboard/api/emails/{ae_id}/read-mailbox/", headers=headers, timeout=10)
                if r_mail.status_code == 200 and r_mail.json().get("success"):
                    selected_acc = acc
                    print(f"✅ Đã chọn tài khoản: {acc['email']} | User: @{acc['username']} | AE_ID: {ae_id}")
                    break

    if not selected_acc:
        print("❌ Không tìm thấy tài khoản TikTok thỏa mãn điều kiện.")
        return

    # 2. Lay proxy tu cu.c69.us/250
    selected_proxy = get_live_proxy_from_c69()

    # 3. Cau hinh NurtureSession
    profile_id = f"nurture_test_{selected_acc['id']}"
    selected_acc["profile_id"] = profile_id

    cfg = NurtureConfig(
        c69_url=c69_base,
        proxy=selected_proxy,
        proxy_type="socks5",
        headless=False,                # BẬT GIAO DIỆN TRÌNH DUYỆT THẬT
        session_minutes_min=3,
        session_minutes_max=5,
        like_probability=0.70,
        share_probability=0.20,
        comment_probability=0.20,
        auto_setup_profile=True,       # TỰ ĐỘNG AUDIT USERNAME & AVATAR
        avatar_pool_dir="D:/Workspace/Python/QHTDautomation/MunAutomationDesktop/avatar_pool"
    )

    session = TikTokNurtureSession(
        account=selected_acc,
        config=cfg,
        progress_callback=lambda msg, lvl: print(f"[{lvl.upper()}] {msg}")
    )

    # 4. Chay phien nuoi
    print("\n🎬 Bắt đầu khởi động Browser và chạy kịch bản...")
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    res = loop.run_until_complete(session.run_session())

    print("\n==================================================")
    print("📊 KẾT QUẢ PHIÊN NUÔI:")
    for k, v in res.items():
        print(f"  - {k}: {v}")
    print("==================================================")

if __name__ == "__main__":
    main()
