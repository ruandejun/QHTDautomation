import asyncio
import os
import sys
import json

os.chdir(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
sys.path.append(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from mun_anti_browser.browser_manager import NodriverBrowserManager

async def main():
    with open("browser_profiles.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    cfg = profs[0]

    # Cung cấp timezone chuẩn
    cfg["_timezone_data"] = {
        "timezone_id": "Asia/Ho_Chi_Minh",
        "latitude": 21.0285,
        "longitude": 105.8542
    }

    bm = NodriverBrowserManager()
    browser, tab = await bm.start(
        profile_config=cfg,
        proxy_string="",
        proxy_type="direct",
        headless=True,
        start_url="https://iphey.com"
    )

    print("⏳ Chờ tải xong iphey...")
    await asyncio.sleep(12)

    # Click BROWSER card
    await tab.evaluate("""
    (() => {
        const btn = Array.from(document.querySelectorAll('*')).find(el => el.children.length === 0 && (el.innerText || '').trim() === 'BROWSER');
        if (btn) btn.click();
    })()
    """)
    await asyncio.sleep(2)

    # Lấy toàn bộ các hàng kiểm tra trong BROWSER
    script = """
    (() => {
        const results = [];
        document.querySelectorAll('tr, .check-row, [class*="item"]').forEach(el => {
            const text = el.innerText.trim().replace(/\\n+/g, ' | ');
            if (text.length > 3 && text.length < 300) {
                // Kiểm tra có icon fail / red / alert không
                const hasFail = !!el.querySelector('[class*="fail"], [class*="red"], [class*="error"], [class*="warn"], [class*="unreliable"], svg[fill*="red"], svg[stroke*="red"]');
                const hasPass = !!el.querySelector('[class*="pass"], [class*="green"], [class*="success"], svg[fill*="green"], svg[stroke*="green"]');
                results.push({
                    text: text,
                    status: hasFail ? 'FAIL' : (hasPass ? 'PASS' : 'UNKNOWN')
                });
            }
        });
        return JSON.stringify(results);
    })()
    """
    raw_res = await tab.evaluate(script)
    items = json.loads(raw_res) if isinstance(raw_res, str) else []
    print("\n--- CHI TIẾT CÁC MỤC KIỂM TRA TRONG IPHEY ---")
    for it in items:
        if it['status'] == 'FAIL' or any(w in it['text'].lower() for w in ['unreliable', 'suspicious', 'mismatch', 'fail']):
            print(f"  ❌ [{it['status']}] {it['text']}")
        elif any(w in it['text'].lower() for w in ['browser', 'webrtc', 'user-agent', 'timezone', 'platform', 'plugins']):
            print(f"  ℹ️ [{it['status']}] {it['text']}")

if __name__ == "__main__":
    asyncio.run(main())
