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

async def test_iphey_dom():
    bm = NodriverBrowserManager()
    profile = bm.profile_manager.create_random_profile()
    profile["id"] = "iphey_dom_inspector"

    try:
        browser, tab = await bm.start(
            profile_config=profile,
            headless=False,
            start_url="https://iphey.com"
        )
        print("⏳ Chờ 15s để iphey.com tải xong toàn bộ kết quả...")
        await asyncio.sleep(15)

        # Lấy tất cả các class và text của các thẻ trên iphey
        dom_report = await tab.evaluate("""
        JSON.stringify((() => {
            // Tìm tất cả các box chứa từ Hardware, Software, Browser, Location
            const sections = [];
            const allElements = document.querySelectorAll('*');
            
            // Tìm text của status chính (Trustworthy hay Unreliable)
            let trustVerdict = 'N/A';
            document.querySelectorAll('h1, h2, h3, .status, [class*="trust"], [class*="verdict"]').forEach(el => {
                const t = el.innerText.trim();
                if (t.includes('Trustworthy') || t.includes('Suspicious') || t.includes('Unreliable')) {
                    trustVerdict = t;
                }
            });

            // Tìm các cột hoặc card
            const cards = [];
            document.querySelectorAll('div, section, article').forEach(el => {
                const text = el.innerText ? el.innerText.trim() : '';
                // Nếu là card của 4 cột chính
                if (el.className && typeof el.className === 'string' && (el.className.includes('card') || el.className.includes('box') || el.className.includes('category') || el.className.includes('column'))) {
                    if (text.length > 10 && text.length < 500) {
                        cards.push({ class: el.className, text: text.replace(/\\n+/g, ' | ') });
                    }
                }
            });

            // Lấy kết quả cụ thể cho Canvas và WebGL
            let canvasStatus = 'N/A';
            let webglStatus = 'N/A';
            document.querySelectorAll('*').forEach(el => {
                const t = el.innerText ? el.innerText.trim() : '';
                if (t.startsWith('Canvas') && t.length < 100) canvasStatus = t;
                if (t.startsWith('WebGL') && t.length < 100) webglStatus = t;
            });

            return {
                verdict: trustVerdict,
                canvasStatus: canvasStatus,
                webglStatus: webglStatus,
                cards: cards.slice(0, 15),
                fullText: document.body.innerText
            };
        })())
        """)

        data = json.loads(dom_report) if isinstance(dom_report, str) else {}
        print("\n" + "=" * 65)
        print("🎯 VERDICT TRÊN IPHEY.COM:", data.get("verdict"))
        print("🎨 CANVAS STATUS:", data.get("canvasStatus"))
        print("🎮 WEBGL STATUS:", data.get("webglStatus"))
        print("=" * 65)

        # In các dòng trong fullText có chứa dấu hiệu check
        full_text = data.get("fullText", "")
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        for idx, line in enumerate(lines):
            if any(k in line.lower() for k in ["browser", "location", "personal data", "hardware", "software", "trustworthy", "suspicious", "unreliable", "passed", "failed"]):
                context = " -> ".join(lines[max(0, idx-1):min(len(lines), idx+3)])
                print(f"  [{idx}] {context[:120]}")

        await asyncio.sleep(5)
        await bm.close()

    except Exception as e:
        print("Lỗi:", e)
        try:
            await bm.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(test_iphey_dom())
