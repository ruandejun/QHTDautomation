import sys
import os
import asyncio
import json

os.chdir(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
sys.path.append(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from mun_anti_browser.browser_manager import NodriverBrowserManager

async def launch(profile_id, start_url=None):
    bm = NodriverBrowserManager()
    profiles_file = "browser_profiles.json"
    cfg = None
    if os.path.exists(profiles_file):
        try:
            with open(profiles_file, "r", encoding="utf-8") as f:
                profs = json.load(f)
                if isinstance(profs, list):
                    for p in profs:
                        if str(p.get("id")) == str(profile_id):
                            cfg = p
                            break
        except Exception as e:
            print(f"Error reading {profiles_file}: {e}")

    if not cfg:
        cfg = bm.profile_manager.create_random_profile()
        cfg["id"] = profile_id

    url = start_url or cfg.get("profile_start_url") or "https://whoer.net"
    proxy = cfg.get("proxy_string") or cfg.get("profile_socks5_details") or cfg.get("proxy") or ""

    print(f"🚀 Launching Mun Anti Browser for profile #{profile_id}...")
    print(f"  • URL:   {url}")
    print(f"  • Proxy: {proxy or 'Direct'}")
    print(f"  • UA:    {cfg.get('profile_user_agent')}")

    try:
        browser, tab = await bm.start(
            profile_config=cfg,
            proxy_string=proxy if proxy else "",
            proxy_type=cfg.get("proxy_type", "socks5") if proxy else "direct",
            headless=False,
            start_url=url
        )
        print("✅ Chrome đã mở thành công trên Desktop!")

        # Giữ process sống cho đến khi user đóng Chrome
        while True:
            await asyncio.sleep(2)
            try:
                # Kiểm tra tab còn sống không
                await tab.evaluate("1+1")
            except Exception:
                print("👋 User đã đóng trình duyệt.")
                break

    except Exception as e:
        print(f"❌ Lỗi mở browser: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await bm.close()
        except Exception:
            pass

if __name__ == "__main__":
    p_id = sys.argv[1] if len(sys.argv) > 1 else "1"
    p_url = sys.argv[2] if len(sys.argv) > 2 else None
    asyncio.run(launch(p_id, p_url))
