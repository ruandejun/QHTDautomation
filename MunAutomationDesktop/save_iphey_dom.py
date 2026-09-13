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

    # Lấy toàn bộ HTML của trang để phân tích CSS class và nội dung
    html = await tab.evaluate("document.documentElement.outerHTML")
    with open("iphey_dump.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Đã lưu iphey_dump.html (kích thước:", len(html), "bytes)")

if __name__ == "__main__":
    asyncio.run(main())
