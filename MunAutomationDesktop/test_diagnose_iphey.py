import asyncio
import os
import sys
import json

os.chdir(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
sys.path.append(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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

    print("⏳ Chờ tải xong iphey (12s)...")
    await asyncio.sleep(12)

    script = """
    (() => {
        const res = {};
        // 1. Get all signal rows
        const signals = [];
        document.querySelectorAll('.detail-entry, [class*="detail"]').forEach(el => {
            const txt = (el.innerText || '').trim();
            if (txt) signals.push(txt.replace(/\\n+/g, ' : '));
        });
        res.signals = signals;

        // 2. Get main status cards (Browser, Location, IP, Hardware, Software)
        const cards = [];
        document.querySelectorAll('.check-item, .card, [class*="card"]').forEach(el => {
            const txt = (el.innerText || '').trim();
            if (txt) cards.push(txt.replace(/\\n+/g, ' | '));
        });
        res.cards = cards;

        // 3. Extract text content
        res.text = (document.body.innerText || '').slice(0, 1000);
        return JSON.stringify(res);
    })()
    """
    res = await tab.evaluate(script)
    print("DETAILS:", res)
    try:
        browser.stop()
    except Exception:
        pass

if __name__ == "__main__":
    asyncio.run(main())
