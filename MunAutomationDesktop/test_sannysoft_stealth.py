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

async def test_stealth_sannysoft():
    print("=" * 60)
    print("🚀 [TEST 2] KIỂM TRA BOT DETECTION & STEALTH NÂNG CAO (SANNYSOFT)...")
    print("=" * 60)

    bm = NodriverBrowserManager()
    profile = bm.profile_manager.create_random_profile()
    profile["id"] = "stealth_audit_sannysoft"

    try:
        browser, tab = await bm.start(
            profile_config=profile,
            headless=False,
            start_url="https://bot.sannysoft.com/"
        )
        print("✅ Chrome đã mở trang bot.sannysoft.com! Đang chờ nạp trang 5s...")
        await asyncio.sleep(5)

        # Lấy kết quả từ bảng kết quả trên bot.sannysoft.com
        eval_script = """
        (() => {
            const rows = Array.from(document.querySelectorAll('table tr'));
            const results = {};
            for (const r of rows) {
                const cols = r.querySelectorAll('td, th');
                if (cols.length >= 2) {
                    const testName = cols[0].innerText.trim();
                    const testResult = cols[1].innerText.trim();
                    if (testName && testResult) {
                        results[testName] = testResult;
                    }
                }
            }
            return {
                tableResults: results,
                userAgent: navigator.userAgent,
                webdriver: navigator.webdriver,
                pluginsLength: navigator.plugins.length,
                languages: navigator.languages.join(','),
                hasChromeRuntime: typeof window.chrome !== 'undefined' && typeof window.chrome.runtime !== 'undefined'
            };
        })()
        """

        raw_res = await tab.evaluate(eval_script)
        parsed = {}
        if isinstance(raw_res, list):
            for item in raw_res:
                if isinstance(item, list) and len(item) == 2:
                    k, v_obj = item[0], item[1]
                    if isinstance(v_obj, dict):
                        parsed[k] = v_obj.get("value", v_obj.get("type"))
                    else:
                        parsed[k] = v_obj
        elif isinstance(raw_res, dict):
            parsed = raw_res

        print("\n📊 BẢNG KẾT QUẢ BOT.SANNYSOFT.COM:")
        print(f"  - User-Agent:         {parsed.get('userAgent')}")
        print(f"  - navigator.webdriver:{parsed.get('webdriver')} (Status: {'PASS ✅' if not parsed.get('webdriver') or parsed.get('webdriver') == 'undefined' else 'FAIL ❌'})")
        print(f"  - Plugins count:      {parsed.get('pluginsLength')} (Status: {'PASS ✅' if parsed.get('pluginsLength', 0) > 0 else 'WARN ⚠️'})")
        print(f"  - Languages:          {parsed.get('languages')}")
        print(f"  - chrome.runtime:     {parsed.get('hasChromeRuntime')} (Status: {'PASS ✅' if parsed.get('hasChromeRuntime') else 'FAIL ❌'})")

        tbl = parsed.get("tableResults", {})
        if tbl:
            print("\n🔍 CHI TIẾT TỪNG MỤC TEST:")
            for k, v in list(tbl.items())[:15]:
                print(f"    • {k:<32}: {v}")

        await asyncio.sleep(2)
        await bm.close()
        print("\n🎉 Hoàn thành kiểm tra Bot Detection & Stealth trên bot.sannysoft.com!")

    except Exception as e:
        print(f"\n❌ Lỗi: {e}")
        try:
            await bm.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(test_stealth_sannysoft())
