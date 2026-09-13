import asyncio
import os
import sys
import json
import random
import requests
import time

os.chdir(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
sys.path.append(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from mun_anti_browser.browser_manager import NodriverBrowserManager

async def run_tiktok_login_test():
    print("=" * 65)
    print("🎬 [TIKTOK LIVE LOGIN AUDIT] MUN ANTI-BROWSER TEST")
    print("=" * 65)

    # 1. Lấy danh sách tài khoản TikTok từ C69
    print("\n🔑 Bước 1: Lấy tài khoản TikTok từ C69 Dashboard API...")
    headers = {"Authorization": "Token 99b02d3d255a49193950777b1cc3e3db099ceefb"}
    try:
        r = requests.get("https://cu.c69.us/dashboard/api/accounts/?type=tiktok&page_size=20", headers=headers, timeout=12)
        accs = r.json().get("results", [])
    except Exception as e:
        print(f"❌ Lỗi lấy tài khoản C69: {e}")
        return

    valid_acc = None
    for a in accs:
        if a.get("username") == "phng.phng.trc74" and a.get("password"):
            valid_acc = a
            valid_acc["login_id"] = a["username"]
            break

    if not valid_acc:
        for a in accs:
            login_user = a.get("email") or a.get("username")
            if login_user and a.get("password"):
                valid_acc = a
                valid_acc["login_id"] = login_user
                break

    print(f"✅ Tài khoản mục tiêu: ID={valid_acc['id']} | Login ID={valid_acc['login_id']} | Pass=******")

    # 2. Lấy 1 proxy SOCKS5 live
    print("\n🛡️ Bước 2: Kiểm tra proxy SOCKS5 từ pool C69...")
    selected_proxy = None
    try:
        r_p = requests.get("https://cu.c69.us/250", timeout=10)
        lines = [l.strip() for l in r_p.text.strip().splitlines() if l.strip() and not l.startswith('#')]
        random.shuffle(lines)
        for line in lines[:15]:
            parts = line.split(':')
            if len(parts) == 4:
                host, port, user, pwd = parts
                proxy_socks = f"socks5://{user}:{pwd}@{host}:{port}"
                try:
                    r_t = requests.get("https://api.ipify.org?format=json", proxies={'http': proxy_socks, 'https': proxy_socks}, timeout=3.0)
                    if r_t.status_code == 200:
                        selected_proxy = line
                        print(f"✅ Chọn được proxy SOCKS5 Live: {host}:{port} (Outbound IP: {r_t.json().get('ip')})")
                        break
                except Exception:
                    continue
    except Exception as e:
        print(f"⚠️ Không lấy được proxy pool, sẽ dùng DIRECT IP: {e}")

    # 3. Tạo profile Mun Anti Browser
    print("\n🌐 Bước 3: Khởi tạo Profile và Fingerprint Shield...")
    bm = NodriverBrowserManager()
    cfg = bm.profile_manager.create_random_profile(socks5=selected_proxy)
    profile_id = f"tiktok_test_{valid_acc['id']}"
    cfg['id'] = profile_id

    print(f"  • User-Agent:      {cfg.get('profile_user_agent')}")
    print(f"  • WebGL GPU:       {cfg.get('profile_renderer')}")
    print(f"  • Canvas Noise:    {cfg.get('profile_canvas')}")
    print(f"  • Resolution:      {cfg.get('profile_resolution')}")

    try:
        print("\n🚀 Bước 4: Mở trình duyệt Chrome ẩn danh vào trang TikTok Login...")
        browser, tab = await bm.start(
            profile_config=cfg,
            proxy_string=selected_proxy,
            proxy_type="socks5" if selected_proxy else "direct",
            headless=False,
            start_url="https://www.tiktok.com/login/phone-or-email/email?lang=en"
        )

        print("⏳ Chờ tải trang đăng nhập TikTok (6s)...")
        await asyncio.sleep(6)

        # Kiểm tra title và URL hiện tại
        raw_info = await tab.evaluate("JSON.stringify({ title: document.title, url: window.location.href })")
        try:
            page_info = json.loads(raw_info) if isinstance(raw_info, str) else {}
        except Exception:
            page_info = {}
        print(f"📄 Trang hiện tại: Title='{page_info.get('title')}' | URL={page_info.get('url')}")

        # Kiểm tra xem có bị Cloudflare hay Verify Page không
        raw_cf = await tab.evaluate("""
        JSON.stringify((() => {
            const text = document.body.innerText || '';
            const isCf = text.includes('Just a moment') || text.includes('Verify you are human') || document.querySelector('#challenge-running');
            return { isCf: !!isCf };
        })())
        """)
        try:
            cf_data = json.loads(raw_cf) if isinstance(raw_cf, str) else {}
        except Exception:
            cf_data = {}

        if cf_data.get("isCf"):
            print("⚠️ Phát hiện trang Cloudflare Challenge, đang chờ bypass tự động...")
            await asyncio.sleep(5)

        # Điền thông tin đăng nhập
        print(f"\n✍️ Bước 5: Điền thông tin tài khoản: {valid_acc['login_id']}")
        fill_script = f"""
        JSON.stringify((() => {{
            const usernameInput = document.querySelector('input[name="username"]') || 
                                  document.querySelector('input[type="text"]') || 
                                  document.querySelector('input[placeholder*="Email"]') ||
                                  document.querySelector('input[placeholder*="Username"]');
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
                setNativeValue(usernameInput, {json.dumps(valid_acc['login_id'])});
                passwordInput.focus();
                setNativeValue(passwordInput, {json.dumps(valid_acc['password'])});
                return {{ success: true, emailFilled: usernameInput.value, passFilled: !!passwordInput.value }};
            }}
            return {{ success: false, reason: 'Inputs not found' }};
        }})())
        """
        raw_fill = await tab.evaluate(fill_script)
        try:
            fill_res = json.loads(raw_fill) if isinstance(raw_fill, str) else {}
        except Exception:
            fill_res = {}
        print(f"  • Kết quả điền form: {fill_res}")

        await asyncio.sleep(1.5)

        # Bấm nút Log In
        print("\n🖱️ Bước 6: Bấm nút 'Log in'...")
        click_script = """
        JSON.stringify((() => {
            const btn = document.querySelector('button[type="submit"]') || 
                        Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase() === 'log in');
            if (btn) {
                btn.focus();
                btn.click();
                return { clicked: true, text: btn.innerText.trim() };
            }
            return { clicked: false };
        })())
        """
        raw_click = await tab.evaluate(click_script)
        try:
            click_res = json.loads(raw_click) if isinstance(raw_click, str) else {}
        except Exception:
            click_res = {}
        print(f"  • Kết quả bấm nút: {click_res}")

        print("\n⏳ Bước 7: Quan sát phản hồi từ máy chủ TikTok sau khi bấm đăng nhập (10s)...")
        await asyncio.sleep(8)

        # Kiểm tra phản hồi DOM
        dom_script = """
        JSON.stringify((() => {
            const bodyText = document.body.innerText || '';
            const captchaModal = document.querySelector('#captcha-verify-image') || 
                                 document.querySelector('.captcha_verify_container') ||
                                 document.querySelector('[id*="captcha"]') ||
                                 document.querySelector('[class*="captcha"]');
            const errorMsg = document.querySelector('[role="alert"]') || 
                             document.querySelector('.error-message') ||
                             document.querySelector('[class*="error"]');
            
            return {
                url: window.location.href,
                hasCaptcha: !!captchaModal,
                errorText: errorMsg ? errorMsg.innerText.trim() : '',
                bodySnippet: bodyText.substring(0, 300).replace(/\\n/g, ' ')
            };
        })())
        """
        raw_dom = await tab.evaluate(dom_script)
        try:
            dom_status = json.loads(raw_dom) if isinstance(raw_dom, str) else {}
        except Exception:
            dom_status = {}

        print("\n📊 BÁO CÁO PHẢN HỒI THỰC TẾ TRÊN TIKTOK:")
        print(f"  • URL sau khi gửi: {dom_status.get('url')}")
        print(f"  • Xuất hiện Captcha: {'CÓ (Cần giải đố hình)' if dom_status.get('hasCaptcha') else 'KHÔNG'}")
        if dom_status.get('errorText'):
            print(f"  • Thông báo lỗi giao diện: {dom_status.get('errorText')}")
        print(f"  • Nội dung màn hình: {dom_status.get('bodySnippet')[:150]}...")

        print("\n✅ Trình duyệt sẽ giữ mở thêm 15 giây để anh Tony quan sát trực tiếp trên màn hình...")
        await asyncio.sleep(15)

        await bm.close()
        print("\n🎉 Đã hoàn thành phiên test login TikTok.")

    except Exception as e:
        print(f"\n❌ Lỗi trong quá trình test: {e}")
        import traceback
        traceback.print_exc()
        try:
            await bm.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(run_tiktok_login_test())
