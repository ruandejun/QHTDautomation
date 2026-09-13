import asyncio
import os
import sys
import nodriver

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("=" * 60)
    print("🧪 TEST PURE UNTOUCHED CHROME ON IPHEY")
    print("=" * 60)
    cfg = nodriver.Config()
    cfg.sandbox = False
    cfg.headless = True

    browser = await nodriver.start(config=cfg)
    tab = browser.main_tab
    await tab.get("https://iphey.com")
    print("⏳ Chờ tải xong iphey (12s)...")
    await asyncio.sleep(12)

    script = """
    (() => {
        const sig = document.getElementById('signals');
        const signals = [];
        if (sig && sig.parentElement) {
            sig.parentElement.querySelectorAll('.detail-entry').forEach(el => {
                signals.push(el.innerText.trim().replace(/\\n+/g, ': '));
            });
        }
        const text = document.body.innerText;
        const isReliable = text.includes('Trustworthy') || text.includes('Everything is fine');
        return JSON.stringify({
            title: document.title,
            signals: signals,
            fullStatus: text.slice(0, 300)
        });
    })()
    """
    raw_res = await tab.evaluate(script)
    import json
    res = json.loads(raw_res) if isinstance(raw_res, str) else {}
    print("\n📊 KẾT QUẢ PURE CHROME:")
    print("Signals:", res.get("signals"))
    print("Status snippet:", res.get("fullStatus")[:150])

if __name__ == "__main__":
    asyncio.run(main())
