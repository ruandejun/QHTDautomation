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

async def run_anti_detect_audit():
    print("=" * 60)
    print("🚀 [TEST] KHỞI ĐỘNG MUN ANTI-BROWSER AUDIT TRÊN WINDOWS...")
    print("=" * 60)

    bm = NodriverBrowserManager()
    
    # Sinh ngẫu nhiên 1 profile đầy đủ thuộc tính
    profile = bm.profile_manager.create_random_profile()
    profile_id = "test_audit_win_01"
    profile["id"] = profile_id

    print("\n📋 CẤU HÌNH PROFILE ĐÃ TẠO:")
    print(f"  - User-Agent:      {profile.get('profile_user_agent')}")
    print(f"  - Resolution:      {profile.get('profile_resolution')}")
    print(f"  - Platform:        {profile.get('profile_os')}")
    print(f"  - WebGL Vendor:    {profile.get('profile_vendor')}")
    print(f"  - WebGL Renderer:  {profile.get('profile_renderer')}")
    print(f"  - Audio Noise:     {profile.get('profile_audio')}")
    print(f"  - Canvas Noise:    {profile.get('profile_canvas')}")

    print("\n🌐 Đang khởi động Chrome qua Nodriver (Anti-Detect Engine)...")
    try:
        # Khởi động với start_url là data url hoặc ip test
        browser, tab = await bm.start(
            profile_config=profile,
            headless=False,
            start_url="https://api.ipify.org?format=json"
        )
        print("✅ Chrome đã khởi động thành công!")
        await asyncio.sleep(4)

        # Đánh giá các biến môi trường Anti-Detect đã được inject
        audit_js = """
        (() => {
            const gl = document.createElement('canvas').getContext('webgl');
            let dbgRender = 'N/A';
            let dbgVendor = 'N/A';
            if (gl) {
                const ext = gl.getExtension('WEBGL_debug_renderer_info');
                if (ext) {
                    dbgVendor = gl.getParameter(ext.UNMASKED_VENDOR_WEBGL);
                    dbgRender = gl.getParameter(ext.UNMASKED_RENDERER_WEBGL);
                }
            }
            return {
                webdriver: navigator.webdriver,
                platform: navigator.platform,
                userAgent: navigator.userAgent,
                chromeRuntime: typeof window.chrome !== 'undefined' && typeof window.chrome.runtime !== 'undefined',
                chromeRuntimePlatform: window.chrome?.runtime?.PlatformOs,
                stealthActive: window.__mun_stealth_active === true,
                webglVendor: dbgVendor,
                webglRenderer: dbgRender,
                languages: navigator.languages,
                hardwareConcurrency: navigator.hardwareConcurrency
            };
        })()
        """
        
        eval_result = await tab.evaluate(audit_js)
        
        # Nodriver evaluate trả về dạng list of [key, {type: ..., value: ...}]
        parsed = {}
        if isinstance(eval_result, list):
            for item in eval_result:
                if isinstance(item, list) and len(item) == 2:
                    k, v_obj = item[0], item[1]
                    if isinstance(v_obj, dict):
                        parsed[k] = v_obj.get("value", v_obj.get("type"))
                    else:
                        parsed[k] = v_obj
        elif isinstance(eval_result, dict):
            parsed = eval_result

        print("\n🔍 KẾT QUẢ AUDIT LIVE TRÊN DOM:")
        print(f"  1. navigator.webdriver:           {parsed.get('webdriver')} (Cần undefined/false -> {'PASS ✅' if not parsed.get('webdriver') or parsed.get('webdriver') == 'undefined' else 'FAIL ❌'})")
        print(f"  2. navigator.platform:            {parsed.get('platform')} (Cần Win32 -> {'PASS ✅' if parsed.get('platform') == 'Win32' else 'FAIL ❌'})")
        print(f"  3. window.chrome.runtime:         {parsed.get('chromeRuntime')} (Cần True -> {'PASS ✅' if parsed.get('chromeRuntime') else 'FAIL ❌'})")
        print(f"  4. window.__mun_stealth_active:   {parsed.get('stealthActive')} (Cần True -> {'PASS ✅' if parsed.get('stealthActive') else 'FAIL ❌'})")
        print(f"  5. WebGL Vendor:                  {parsed.get('webglVendor')}")
        print(f"  6. WebGL Renderer:                {parsed.get('webglRenderer')}")
        print(f"  7. Hardware Concurrency (Cores):  {parsed.get('hardwareConcurrency')}")

        await asyncio.sleep(2)
        await bm.close()
        print("\n🎉 Đã đóng browser an toàn. Audit Mun Anti Browser hoàn tất!")
        return parsed

    except Exception as e:
        print(f"\n❌ LỖI KHI CHẠY AUDIT: {e}")
        import traceback
        traceback.print_exc()
        try:
            await bm.close()
        except Exception:
            pass
        return None

if __name__ == "__main__":
    asyncio.run(run_anti_detect_audit())
