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
    print("=" * 65)
    print("🔍 [IPHEY DEEP INSPECT] BÓC TÁCH TỪNG HẠNG MỤC CHECK CỦA IPHEY")
    print("=" * 65)

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

    print("⏳ Đang tải và phân tích iphey.com (12s)...")
    await asyncio.sleep(12)

    # Lấy chính xác mục BROWSER và LOCATION
    inspect_script = """
    (() => {
        const sections = {};
        document.querySelectorAll('.check-item, .card, [class*="section"], [class*="item"]').forEach(el => {
            const h = el.querySelector('h2, h3, h4, .title, .name');
            const desc = el.querySelector('.status, .desc, .result, p, span');
            if (h && desc) {
                sections[h.innerText.trim()] = desc.innerText.trim().replace(/\\n+/g, ' ');
            }
        });
        
        // Đọc tất cả các cảnh báo / dấu tích đỏ
        const redFlags = [];
        document.querySelectorAll('[class*="danger"], [class*="warn"], [class*="error"], [class*="unreliable"], [class*="fail"], svg[class*="red"]').forEach(el => {
            const parent = el.closest('div, li, p') || el;
            redFlags.push(parent.innerText.trim().replace(/\\n+/g, ' '));
        });

        return JSON.stringify({
            sections: sections,
            redFlags: redFlags.slice(0, 15),
            fullText: document.body.innerText
        });
    })()
    """

    raw_data = await tab.evaluate(inspect_script)
    data = json.loads(raw_data) if isinstance(raw_data, str) else {}
    print("\n--- CÁC MỤC KIỂM TRA CHÍNH ---")
    for k, v in data.get("sections", {}).items():
        print(f"  📌 {k}: {v}")

    print("\n--- CÁC DẤU HIỆU CẢNH BÁO (RED FLAGS) ---")
    for rf in data.get("redFlags", []):
        if rf:
            print(f"  ⚠️ {rf}")

    # Soi riêng đoạn text có chữ BROWSER
    lines = data.get("fullText", "").split("\n")
    print("\n--- CHI TIẾT ĐOẠN TEXT BROWSER TRÊN TRANG ---")
    for i, l in enumerate(lines):
        if "BROWSER" in l or "Unreliable" in l or "Click here" in l:
            context = lines[max(0, i-2):min(len(lines), i+8)]
            print("  >>> " + " | ".join([c.strip() for c in context if c.strip()]))
            break

if __name__ == "__main__":
    asyncio.run(main())
