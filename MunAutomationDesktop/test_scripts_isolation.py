import asyncio
import os
import sys
import json

os.chdir(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
sys.path.append(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import nodriver
import nodriver.cdp.emulation as emulation
import nodriver.cdp.network as network_cdp
import nodriver.cdp.page as page_cdp
from mun_anti_browser.script_loader import ScriptLoader

async def test_bundle(name, scripts_to_include):
    print(f"\n==========================================")
    print(f"🧪 TESTING BUNDLE: {name}")
    print(f"Scripts: {scripts_to_include}")
    print(f"==========================================")

    cfg = nodriver.Config()
    cfg.sandbox = False
    cfg.headless = True

    browser = await nodriver.start(config=cfg)
    tab = browser.main_tab

    # Native CDP User Agent
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

    sl = ScriptLoader()
    combined_js = []
    
    for s_name in scripts_to_include:
        s_content = sl.load_script(s_name)
        if s_name == "canvas":
            s_content = s_content.replace("{{canvas_shift}}", '{"r": 1, "g": -1, "b": 1, "a": 0}')
        elif s_name == "rects":
            s_content = s_content.replace("{{rects}}", "0.25")
        elif s_name == "fonts":
            s_content = s_content.replace("{{fonts}}", '["Arial", "Calibri", "Segoe UI"]')
        elif s_name in ["navigator_extra", "network", "battery"]:
            s_content = s_content.replace("{{plugins_seed}}", "12345").replace("{{profile_width}}", "1920").replace("{{profile_height}}", "1080")
        combined_js.append(s_content)

    if combined_js:
        full_js = "\n\n".join(combined_js)
        await tab.send(page_cdp.add_script_to_evaluate_on_new_document(source=full_js))

    await tab.get("https://iphey.com")
    print("⏳ Chờ tải xong iphey (12s)...")
    await asyncio.sleep(12)

    script = """
    (() => {
        const text = document.body.innerText || '';
        const signals = [];
        document.querySelectorAll('.detail-entry, [class*="detail"]').forEach(el => {
            const txt = (el.innerText || '').trim();
            if (txt && (txt.includes('pineapple') || txt.includes('roadmap') || txt.includes('Detected') || txt.includes('SIGNALS'))) {
                signals.push(txt.replace(/\\n+/g, ' : '));
            }
        });
        const status = text.includes('Trustworthy') ? 'TRUSTWORTHY ✅' : (text.includes('Unreliable') ? 'UNRELIABLE ❌' : 'UNKNOWN');
        return JSON.stringify({ status: status, signals: signals });
    })()
    """
    res = await tab.evaluate(script)
    print(f"👉 RESULT FOR [{name}]:", res)

    try:
        browser.stop()
    except Exception:
        pass

async def main():
    # Test A: navigator_extra
    await test_bundle("navigator_extra only", ["navigator_extra"])
    
    # Test B: network + battery + speech + media + ping
    await test_bundle("network + battery + speech + media + ping", ["network", "battery", "speech_synthesis", "media_devices", "ping"])

if __name__ == "__main__":
    asyncio.run(main())
