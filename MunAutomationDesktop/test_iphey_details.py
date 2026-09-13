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

async def audit_iphey_details():
    bm = NodriverBrowserManager()
    profile = bm.profile_manager.create_random_profile()
    profile["id"] = "iphey_detailed_check"

    try:
        browser, tab = await bm.start(
            profile_config=profile,
            headless=False,
            start_url="https://iphey.com"
        )
        print("⏳ Chờ nạp trang và phân tích (12s)...")
        await asyncio.sleep(12)

        # Trích xuất chi tiết từng card trên iphey.com
        detail_script = """
        JSON.stringify((() => {
            // Lấy tất cả các khối kiểm tra
            const results = [];
            const cards = document.querySelectorAll('.card, [class*="card"], [class*="check"]');
            cards.forEach(card => {
                const header = card.querySelector('h2, h3, h4, .title, .header')?.innerText?.trim();
                const status = card.querySelector('.status, .badge, [class*="status"], [class*="badge"]')?.innerText?.trim();
                const items = [];
                card.querySelectorAll('li, tr, .row, .item, [class*="item"]').forEach(item => {
                    const text = item.innerText?.trim();
                    if (text && text.length < 200) {
                        items.push(text.replace(/\\n+/g, ' -> '));
                    }
                });
                if (header) {
                    results.push({ header, status, items: items.slice(0, 10) });
                }
            });

            // Tìm cụ thể các cảnh báo đỏ hoặc fail
            const alerts = [];
            document.querySelectorAll('.fail, .error, .warn, .unreliable, [class*="fail"], [class*="warn"], [class*="alert"]').forEach(el => {
                const txt = el.innerText?.trim();
                if (txt && txt.length < 150 && !alerts.includes(txt)) {
                    alerts.push(txt);
                }
            });

            // Lấy toàn bộ text chia theo dòng
            const lines = document.body.innerText.split('\\n').map(l => l.trim()).filter(l => l.length > 0);

            return {
                cards: results,
                alerts: alerts,
                rawLines: lines.slice(0, 100)
            };
        })())
        """

        raw = await tab.evaluate(detail_script)
        data = json.loads(raw) if isinstance(raw, str) else {}

        print("\n" + "=" * 65)
        print("🔍 CHI TIẾT CÁC MỤC TRÊN IPHEY.COM:")
        print("=" * 65)

        lines = data.get("rawLines", [])
        # In các dòng quan trọng liên quan đến Browser, Location, Personal Data, Hardware, Software
        collect = False
        current_cat = ""
        for line in lines:
            if line in ["Browser", "Location", "Personal Data", "Hardware", "Software"]:
                print(f"\n📂 [{line.upper()}]:")
                current_cat = line
            elif line in ["Trustworthy", "Suspicious", "Unreliable", "Reliable"]:
                print(f"    ➡️ Trạng thái: {line}")
            elif any(k in line.lower() for k in ["canvas", "webgl", "audio", "ip", "timezone", "user-agent", "platform", "language", "webrtc"]):
                print(f"    • {line}")

        print("\n⚠️ CÁC CẢNH BÁO / DẤU HIỆU UNRELIABLE:")
        for a in data.get("alerts", [])[:10]:
            print(f"    ! {a}")

        await asyncio.sleep(5)
        await bm.close()

    except Exception as e:
        print(f"Lỗi: {e}")
        try:
            await bm.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(audit_iphey_details())
