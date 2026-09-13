"""
Batch Test: Kiem tra dang nhap 5 Profiles, 5 Tai khoan khac nhau va 5 Socks5 khac nhau
De xac minh xem co bi loi "Maximum number of attempts reached" tren IP socks5 sach hay khong.
"""
import asyncio
import os
import sys
import random
import requests
import json
import re

os.chdir("D:/Workspace/Python/QHTDautomation/MunAutomationDesktop")
sys.path.append("D:/Workspace/Python/QHTDautomation/MunAutomationDesktop")

from mun_anti_browser.browser_manager import NodriverBrowserManager

async def test_single_account(idx, account, proxy_line):
    print(f"\n=======================================================")
    print(f"🎬 TEST #{idx}: Account ID={account['id']} | {account['email']}")
    print(f"👤 Username: @{account['username']}")
    print(f"🛡️ Socks5: {proxy_line}")
    print(f"=======================================================")

    profile_id = f"batch_test_p{idx}_{account['id']}"
    bm = NodriverBrowserManager()
    cfg = bm.profile_manager.create_random_profile(socks5=proxy_line)
    cfg['id'] = profile_id

    result = {
        "index": idx,
        "account_id": account["id"],
        "email": account["email"],
        "proxy": proxy_line.split(':')[0],
        "status": "Unknown",
        "error_msg": "",
        "got_otp": False,
        "url_after": ""
    }

    try:
        browser, tab = await bm.start(
            profile_config=cfg,
            proxy_string=proxy_line,
            proxy_type="socks5",
            headless=False,
            start_url="https://www.tiktok.com/login/phone-or-email/email?lang=en"
        )
        print(f"  [#{idx}] Browser started! Loading login page...")
        await asyncio.sleep(5)

        # Kiem tra IP thuc te trong browser
        out_ip = await tab.evaluate("""
        fetch('https://api.ipify.org?format=json')
            .then(r => r.json())
            .then(d => d.ip)
            .catch(() => 'unknown')
        """)
        print(f"  [#{idx}] Browser IP: {out_ip}")

        # Dien thong tin dang nhap
        email = account["email"]
        password = account["password"]

        print(f"  [#{idx}] Typing email & password...")
        email_inp = await tab.select('input[name="username"], input[type="email"], input[placeholder*="Email"]', timeout=5)
        if email_inp:
            await email_inp.click()
            for ch in email:
                await email_inp.send_keys(ch)
                await asyncio.sleep(random.uniform(0.02, 0.08))

        await asyncio.sleep(0.5)

        pw_inp = await tab.select('input[type="password"]', timeout=5)
        if pw_inp:
            await pw_inp.click()
            for ch in password:
                await pw_inp.send_keys(ch)
                await asyncio.sleep(random.uniform(0.02, 0.08))

        await asyncio.sleep(1.0)

        # Click nút Log in
        submit_btn = await tab.select('button[type="submit"]', timeout=5)
        if submit_btn:
            print(f"  [#{idx}] Clicking Log in button...")
            await submit_btn.click()

        # Đợi 7 giây để TikTok xử lý response
        await asyncio.sleep(7)

        url_after = await tab.evaluate("window.location.href")
        body_text = await tab.evaluate("(document.body ? document.body.innerText : '').slice(0, 500)")
        cookies = await tab.evaluate("document.cookie")

        result["url_after"] = str(url_after)

        print(f"  [#{idx}] URL sau click: {url_after}")

        # Phân tích phản hồi từ TikTok
        is_logged_in = "sessionid" in str(cookies) or "sid_guard" in str(cookies)
        has_max_attempts = "maximum number of attempts reached" in str(body_text).lower()
        has_incorrect_pw = "incorrect username or password" in str(body_text).lower() or "wrong password" in str(body_text).lower()
        has_otp_prompt = "6-digit code" in str(body_text).lower() or "enter code" in str(body_text).lower()
        has_captcha = await tab.evaluate("Boolean(document.querySelector('#captcha-verify-image, #secsdk-captcha-drag-wrapper, .captcha_verify_container'))")

        if is_logged_in:
            result["status"] = "SUCCESS_LOGGED_IN"
            print(f"  [#{idx}] 🎉 ĐĂNG NHẬP THÀNH CÔNG! Đã có Session/Cookie.")
        elif has_otp_prompt:
            result["status"] = "NEED_OTP"
            print(f"  [#{idx}] 📧 TikTok yêu cầu mã xác minh OTP 6 số qua email!")
            # Thu lay OTP tu C69 mailbox
            ae_id = account.get("ae_id")
            if ae_id:
                headers = {"Authorization": "Token 99b02d3d255a49193950777b1cc3e3db099ceefb"}
                r_mail = requests.get(f"https://cu.c69.us/dashboard/api/emails/{ae_id}/read-mailbox/", headers=headers, timeout=8)
                if r_mail.status_code == 200:
                    emails = r_mail.json().get("emails", [])
                    if emails:
                        print(f"  [#{idx}] 📬 Đọc được mail: {emails[0].get('subject')}")
                        result["got_otp"] = True
        elif has_max_attempts:
            result["status"] = "MAX_ATTEMPTS"
            result["error_msg"] = "Maximum number of attempts reached"
            print(f"  [#{idx}] ❌ BỊ LỖI MAXIMUM ATTEMPTS!")
        elif has_captcha:
            result["status"] = "CAPTCHA_CHALLENGE"
            print(f"  [#{idx}] 🧩 TikTok xuất hiện Captcha kéo thả / xoay hình.")
        elif has_incorrect_pw:
            result["status"] = "INCORRECT_PASSWORD"
            result["error_msg"] = "Incorrect password"
            print(f"  [#{idx}] ⚠️ Sai mật khẩu hoặc username.")
        else:
            first_line = body_text.split('\n')[0] if body_text else ''
            result["status"] = "PENDING_OR_OTHER"
            result["error_msg"] = first_line[:100]
            print(f"  [#{idx}] ℹ️ Trạng thái khác: {first_line}")

        await asyncio.sleep(2)
    except Exception as exc:
        result["status"] = "ERROR"
        result["error_msg"] = str(exc)
        print(f"  [#{idx}] Lỗi ngoại lệ: {exc}")
    finally:
        await bm.close()
        print(f"  [#{idx}] Đã đóng browser profile.")

    return result

async def main():
    print("==================================================")
    print("🚀 BẮT ĐẦU TEST 5 PROFILES X 5 ACCOUNTS X 5 SOCKS5")
    print("==================================================")

    # 1. Lay 5 tai khoan
    headers = {"Authorization": "Token 99b02d3d255a49193950777b1cc3e3db099ceefb"}
    r = requests.get("https://cu.c69.us/dashboard/api/accounts/?type=tiktok&page_size=25", headers=headers, timeout=12)
    accs = r.json().get("results", [])

    test_accounts = []
    for a in accs:
        if a["id"] in [16505, 16504]:
            continue
        if a.get("email") and a.get("password") and a.get("username"):
            test_accounts.append({
                "id": a["id"],
                "email": a["email"],
                "username": a["username"],
                "password": a["password"],
                "ae_id": a.get("accounts_emails")
            })
        if len(test_accounts) >= 5:
            break

    # 2. Lay 5 socks5 proxy live tu cu.c69.us/250
    r_p = requests.get("https://cu.c69.us/250", timeout=10)
    lines = [l.strip() for l in r_p.text.strip().splitlines() if l.strip() and not l.startswith('#')]
    random.shuffle(lines)

    test_proxies = []
    for line in lines:
        parts = line.split(':')
        if len(parts) == 4:
            host, port, user, pwd = parts
            proxy_socks = f"socks5://{user}:{pwd}@{host}:{port}"
            proxies_dict = {'http': proxy_socks, 'https': proxy_socks}
            try:
                r_t = requests.get("https://api.ipify.org?format=json", proxies=proxies_dict, timeout=3.5)
                if r_t.status_code == 200:
                    test_proxies.append(line)
                    if len(test_proxies) >= 5:
                        break
            except Exception:
                continue

    print(f"✅ Đã chuẩn bị {len(test_accounts)} tài khoản và {len(test_proxies)} socks5 proxy sạch.")

    results = []
    for idx in range(min(len(test_accounts), len(test_proxies))):
        acc = test_accounts[idx]
        proxy = test_proxies[idx]
        res = await test_single_account(idx + 1, acc, proxy)
        results.append(res)
        await asyncio.sleep(2)

    print("\n==================================================")
    print("📊 TỔNG HỢP KẾT QUẢ 5 PROFILES:")
    print("==================================================")
    max_count = 0
    for r in results:
        is_max = (r["status"] == "MAX_ATTEMPTS")
        if is_max: max_count += 1
        icon = "❌" if is_max else "🟢"
        print(f"{icon} Profile #{r['index']} (ID={r['account_id']}, IP={r['proxy']}): {r['status']} | {r['error_msg']}")

    print(f"\n👉 Kết luận: Có {max_count}/{len(results)} profile bị Maximum Attempts.")

if __name__ == "__main__":
    asyncio.run(main())
