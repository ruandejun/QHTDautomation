import asyncio
import os
import sys
import json

os.chdir(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
sys.path.append(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from mun_anti_browser.script_loader import ScriptLoader
import nodriver
import nodriver.cdp.emulation as emulation
import nodriver.cdp.network as network_cdp
import nodriver.cdp.page as page_cdp
from mun_anti_browser import cdp_commands

async def test_injection(script_name, script_code):
    print(f"\n--- Testing Injection: {script_name} ---")
    cfg = nodriver.Config()
    cfg.sandbox = False
    cfg.headless = True
    browser = await nodriver.start(config=cfg)
    tab = browser.main_tab

    # Apply CDP overrides
    dummy_prof = {
        "id": 100,
        "profile_user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.88 Safari/537.36",
        "profile_os": "Windows",
        "profile_resolution": "1920x1080",
        "profile_cpu": 8,
    }
    await cdp_commands.apply_all_cdp_overrides(tab, dummy_prof, script_code)

    await tab.get("https://iphey.com")
    await asyncio.sleep(12)

    eval_code = """
    (() => {
        const text = document.body.innerText || '';
        const signals = [];
        document.querySelectorAll('.detail-entry, [class*="detail"]').forEach(el => {
            const txt = (el.innerText || '').trim();
            if (txt && (txt.includes('pineapple') || txt.includes('roadmap') || txt.includes('SIGNALS'))) {
                signals.push(txt.replace(/\\n+/g, ' : '));
            }
        });
        const status = text.includes('Trustworthy') ? 'TRUSTWORTHY' : (text.includes('Unreliable') ? 'UNRELIABLE' : 'UNKNOWN');
        return JSON.stringify({ status: status, signals: signals });
    })()
    """
    res = await tab.evaluate(eval_code)
    print(f"Result for [{script_name}]: {res}")
    try:
        browser.stop()
    except Exception:
        pass

async def main():
    sl = ScriptLoader()
    with open("browser_profiles.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    prof = profs[0]

    group1 = ["cloudflare_bypass", "webrtc", "canvas", "audio", "webgl"]
    group2 = ["rects", "fonts", "network", "battery", "navigator_extra", "speech_synthesis", "media_devices", "ping"]

    def build_bundle(names):
        parts = []
        for n in names:
            s = sl.load_script(n)
            if n == "cloudflare_bypass":
                s = s.replace("{{plugins_seed}}", "100")
            elif n == "canvas":
                s = s.replace("{{canvas_shift}}", json.dumps(prof.get("profile_canvas", {})))
            elif n == "audio":
                pass
            elif n == "webgl":
                pass
            elif n == "rects":
                s = s.replace("{{rects}}", "0.25")
            elif n == "fonts":
                s = s.replace("{{fonts}}", '["Arial", "Segoe UI"]')
            elif n in ["network", "battery", "navigator_extra"]:
                s = s.replace("{{plugins_seed}}", "100").replace("{{profile_width}}", "1920").replace("{{profile_height}}", "1080")
            parts.append(s)
        return "\n\n".join(parts)

    group_clean = ["cloudflare_bypass", "webrtc", "canvas", "audio", "webgl", "rects", "fonts"]
    await test_injection("Clean Stealth (Group 1 + rects + fonts)", build_bundle(group_clean))

if __name__ == "__main__":
    asyncio.run(main())
