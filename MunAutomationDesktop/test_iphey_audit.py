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
    print("🛡️ [IPHEY AUDIT] KIỂM TRA ĐỘ TIN CẬY DIGITAL IDENTITY")
    print("=" * 65)

    with open("browser_profiles.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    cfg = profs[0]

    print(f"Profile: ID={cfg.get('id')} | Name={cfg.get('name')}")
    print(f"  • OS:            {cfg.get('profile_os')}")
    print(f"  • User-Agent:    {cfg.get('profile_user_agent')}")
    print(f"  • GPU Renderer:  {cfg.get('profile_renderer')}")
    print(f"  • Canvas Noise:  {cfg.get('profile_canvas')}")

    bm = NodriverBrowserManager()
    browser, tab = await bm.start(
        profile_config=cfg,
        proxy_string="",
        proxy_type="direct",
        headless=True,
        start_url="https://iphey.com"
    )

    print("⏳ Đang tải và chờ iphey.com phân tích (12s)...")
    await asyncio.sleep(12)

    # Đọc kết quả từ DOM iphey
    audit_script = """
    (() => {
        const text = document.body.innerText || '';
        const isReliable = text.includes('Trustworthy') || text.includes('Everything is fine') || !text.includes('Unreliable');
        
        // Tìm các block kết quả
        const blocks = [];
        document.querySelectorAll('.check-item, .card, [class*="result"], [class*="status"]').forEach(el => {
            const t = el.innerText.trim();
            if (t.length > 5 && t.length < 300) {
                blocks.push(t.replace(/\\n+/g, ' | '));
            }
        });

        // Lấy các dòng chính
        const lines = text.split('\\n').map(l => l.trim()).filter(l => l.length > 0);
        return {
            title: document.title,
            isReliable: isReliable,
            summary: lines.slice(0, 30),
            highlights: blocks.slice(0, 15)
        };
    })()
    """

    raw_res = await tab.evaluate(audit_script)
    if isinstance(raw_res, str):
        try:
            res = json.loads(raw_res)
        except Exception:
            res = {"raw": raw_res}
    elif isinstance(raw_res, dict):
        res = raw_res
    else:
        res = {"result": str(raw_res)}

    print("\n📊 KẾT QUẢ TỪ IPHEY.COM:")
    print("Result data:", json.dumps(res, indent=2, ensure_ascii=False))

    try:
        if asyncio.iscoroutinefunction(browser.stop):
            await browser.stop()
        else:
            browser.stop()
    except Exception:
        pass

if __name__ == "__main__":
    asyncio.run(main())
