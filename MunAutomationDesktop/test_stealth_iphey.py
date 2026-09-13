import asyncio
import os
import sys
import nodriver
import nodriver.cdp.emulation as emulation
import nodriver.cdp.network as network_cdp
import nodriver.cdp.page as page_cdp

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

async def main():
    print("=" * 60)
    print("🔬 TEST MINIMAL CLEAN STEALTH ON IPHEY")
    print("=" * 60)
    cfg = nodriver.Config()
    cfg.sandbox = False
    cfg.headless = True

    browser = await nodriver.start(config=cfg)
    tab = browser.main_tab

    # 1. Native CDP User Agent override (C++ level, NO JS prototype monkey-patching)
    target_ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.7049.84 Safari/537.36"
    metadata = emulation.UserAgentMetadata(
        platform="Windows",
        platform_version="15.0.0",
        architecture="x86",
        model="",
        mobile=False,
        full_version="135.0.7049.84",
        full_version_list=[
            emulation.UserAgentBrandVersion(brand="Chromium", version="135.0.7049.84"),
            emulation.UserAgentBrandVersion(brand="Google Chrome", version="135.0.7049.84"),
            emulation.UserAgentBrandVersion(brand="Not(A:Brand", version="99.0.0.0"),
        ],
        brands=[
            emulation.UserAgentBrandVersion(brand="Chromium", version="135"),
            emulation.UserAgentBrandVersion(brand="Google Chrome", version="135"),
            emulation.UserAgentBrandVersion(brand="Not(A:Brand", version="99"),
        ],
    )
    await tab.send(emulation.set_user_agent_override(
        user_agent=target_ua,
        accept_language="en-US,en",
        platform="Windows",
        user_agent_metadata=metadata
    ))
    await tab.send(network_cdp.set_user_agent_override(
        user_agent=target_ua,
        accept_language="en-US,en",
        platform="Windows",
        user_agent_metadata=metadata
    ))

    # 2. Inject Canvas & WebGL noise scripts
    from mun_anti_browser.script_loader import ScriptLoader
    sl = ScriptLoader()
    canvas_js = sl.load_script("canvas").replace("{{canvas_shift}}", '{"r": 1, "g": -1, "b": 1, "a": 0}')
    await tab.send(page_cdp.add_script_to_evaluate_on_new_document(source=canvas_js))

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
    print("\n📊 KẾT QUẢ TEST MINIMAL CLEAN STEALTH:")
    print("Signals:", res.get("signals"))
    for l in res.get("fullStatus", "").split("\n"):
        if any(w in l.lower() for w in ["trustworthy", "unreliable", "everything is fine", "browser", "hardware"]):
            print("  👉", l)

if __name__ == "__main__":
    asyncio.run(main())
