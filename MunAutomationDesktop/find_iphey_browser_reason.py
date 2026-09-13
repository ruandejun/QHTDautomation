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
    await asyncio.sleep(10)

    # Click vào nút BROWSER để mở chi tiết lỗi
    click_script = """
    (() => {
        // Tìm element có chữ BROWSER và click
        const els = Array.from(document.querySelectorAll('*'));
        const btn = els.find(el => el.children.length === 0 && (el.innerText || '').trim() === 'BROWSER');
        if (btn) {
            btn.click();
            btn.parentElement.click();
            return "Clicked BROWSER button";
        }
        return "Button not found";
    })()
    """
    res_click = await tab.evaluate(click_script)
    print("Click result:", res_click)
    await asyncio.sleep(3)

    # Đọc lại toàn bộ nội dung trong modal hoặc trang sau khi mở chi tiết
    detail_script = """
    (() => {
        const items = [];
        document.querySelectorAll('tr, li, .detail-item, .modal, [class*="popup"], [class*="modal"], [class*="row"]').forEach(el => {
            const t = el.innerText.trim();
            if (t.length > 5 && t.length < 500 && (t.includes('Unreliable') || t.includes('Check') || t.includes('Browser') || t.includes('Version') || t.includes('Header') || t.includes('User-Agent') || t.includes('Flash') || t.includes('PDF') || t.includes('Extensions'))) {
                items.push(t.replace(/\\n+/g, ' | '));
            }
        });
        return JSON.stringify({
            items: items,
            fullText: document.body.innerText
        });
    })()
    """
    raw_details = await tab.evaluate(detail_script)
    details = json.loads(raw_details) if isinstance(raw_details, str) else {}
    print("\n--- CHI TIẾT LỖI BROWSER TỪ IPHEY ---")
    for item in details.get("items", []):
        print("  👉", item)

    print("\n--- TÌM CÁC TỪ KHOÁ CỤ THỂ BỊ LỖI ---")
    lines = details.get("fullText", "").split("\n")
    record = False
    for line in lines:
        l = line.strip()
        if "BROWSER" in l:
            record = True
        if "LOCATION" in l or "HARDWARE" in l:
            if record:
                record = False
        if record and l:
            print("   [LINE]:", l)

if __name__ == "__main__":
    asyncio.run(main())
