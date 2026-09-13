"""
Batch Test: 5 Profiles độc lập sử dụng Mun Anti-Browser Engine với 5 Proxy Socks5 và 5 Tài khoản TikTok C69
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
    print(f"🎬 TEST PROFILE #{idx}: ID={account['id']} | Email: {account['email']}")
    print(f"👤 Username: @{account['username']}")
    print(f"🛡️ Socks5: {proxy_line}")
    print(f"=======================================================")

    profile_id = f"anti_test_p{idx}_{account['id']}"
    bm = NodriverBrowserManager()
    
    # 1. Mun Anti-Browser Profile Generator (Random UA, WebGL, Canvas, Audio, Fonts, Rects)
    cfg = bm.profile_manager.create_random_profile(socks5=proxy_line)
    cfg['id'] = profile_id

    print(f"  [#{idx}] Fingerprint generated:")
    print(f"    - User-Agent: {cfg.get('profile_user_agent')}")
    print(f"    - Resolution: {cfg.get('profile_resolution')}")
    print(f"    - WebGL Vendor: {cfg.get('profile_vendor')}")
    print(f"    - WebGL Renderer: {cfg.get('profile_renderer')}")

    result = {
        "index": idx,
        "account_id": account["id"],
        "email": account["email"],
        "proxy": proxy_line.split(':')[0],
        "status": "Unknown",
        "detail": ""
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
        print(f"  [#{idx}] Outbound IP: {out_ip}")

        # Dien form theo react native setter
        email = account["email"]
        password = account["password"]

        print(f"  [#{idx}] Typing credentials via React native dispatcher...")
        await tab.evaluate(f"""
        (() => {{
            const usernameInput = document.querySelector('input[name="username"]') || document.querySelector('input[type="text"]') || document.querySelector('input[placeholder*="Email"]');
            const passwordInput = document.querySelector('input[type="password"]');

            function setNativeValue(element, value) {{
                const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                const prototype = Object.getPrototypeOf(element);
                const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {{
                    prototypeValueSetter.call(element, value);
                }} else if (valueSetter) {{
                    valueSetter.call(element, value);
                }} else {{
                    element.value = value;
                }}
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}

            if (usernameInput && passwordInput) {{
                usernameInput.focus();
                setNativeValue(usernameInput, {json.dumps(email)});
                passwordInput.focus();
                setNativeValue(passwordInput, {json.dumps(password)});
            }}
        }})()
        """)

        await asyncio.sleep(1.0)

        # Click nút Log in
        btn_clicked = await tab.evaluate("""
        (() => {
            const b = document.querySelector('button[type="submit"]');
            if (b && !b.disabled) { b.click(); return true; }
            return false;
        })()
        """)
        print(f"  [#{idx}] Click submit button: {btn_clicked}")

        await asyncio.sleep(7)

        # Đọc kết quả từ DOM
        body_text = await tab.evaluate("(document.body ? document.body.innerText : '').slice(0, 500)")
        cookies = await tab.evaluate("document.cookie")

        is_logged_in = "sessionid" in str(cookies) or "sid_guard" in str(cookies)
        has_max_attempts = "maximum number of attempts reached" in str(body_text).lower()
        has_otp = "6-digit code" in str(body_text).lower() or "enter code" in str(body_text).lower()
        has_captcha = await tab.evaluate("Boolean(document.querySelector('#captcha-verify-image, #secsdk-captcha-drag-wrapper, .captcha_verify_container, [class*=\"captcha\"]'))")

        if is_logged_in:
            result["status"] = "SUCCESS_LOGGED_IN"
            print(f"  [#{idx}] 🎉 THÀNH CÔNG: Đã đăng nhập và có sessionid!")
        elif has_otp:
            result["status"] = "NEED_OTP"
            print(f"  [#{idx}] 📧 THÀNH CÔNG BƯỚC 1: TikTok yêu cầu mã 6 số (OTP).")
        elif has_captcha:
            result["status"] = "CAPTCHA_CHALLENGE"
            print(f"  [#{idx}] 🧩 TikTok xuất hiện Captcha kéo thả (không bị Maximum attempts).")
        elif has_max_attempts:
            result["status"] = "MAX_ATTEMPTS"
            print(f"  [#{idx}] ❌ BỊ MAXIMUM ATTEMPTS.")
        else:
            first_err = body_text.split('\n')[0] if body_text else 'Unknown'
            result["status"] = "OTHER_STATUS"
            result["detail"] = first_err[:80]
            print(f"  [#{idx}] ℹ️ Trạng thái: {first_err[:80]}")

        await asyncio.sleep(2)
    except Exception as exc:
        result["status"] = "ERROR"
        result["detail"] = str(exc)
        print(f"  [#{idx}] Lỗi ngoại lệ: {exc}")
    finally:
        await bm.close()
        print(f"  [#{idx}] Đã đóng browser profile.")

    return result

async def main():
    print("==================================================")
    print("🚀 BẮT ĐẦU TEST 5 PROFILES MUN ANTI-BROWSER")
    print("==================================================")

    # 1. Lay 5 tai khoan hop le tu cu.c69.us
    headers = {"Authorization": "Token 99b02d3d255a49193950777b1cc3e3db099ceefb"}
    r = requests.get("https://cu.c69.us/dashboard/api/accounts/?type=tiktok&page_size=20", headers=headers, timeout=12)
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
    for r in results:
        icon = "❌" if r["status"] == "MAX_ATTEMPTS" else "🟢"
        print(f"{icon} Profile #{r['index']} (ID={r['account_id']}, IP={r['proxy']}): {r['status']} {r['detail']}")

if __name__ == "__main__":
    asyncio.run(main())
