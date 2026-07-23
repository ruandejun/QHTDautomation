"""
Test: Detailed Apple Login Flow Simulation
1. Fill email
2. Click Continue button
3. Wait and check password field visibility/focus
4. Fill password
5. Click Sign-In button
"""
import asyncio
import sys
import nodriver
import nodriver.cdp
import nodriver.cdp.page as cdp_page
import nodriver.cdp.runtime as cdp_runtime

sys.path.insert(0, r"d:\Workspace\Python\QHTDautomation")
sys.path.insert(0, r"d:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

TEST_EMAIL = "flowersyw5lyowen@hotmail.com"
# We don't need a real password to test the element transitions
TEST_PASSWORD = "FakePassword123!"

from mun_anti_browser import NodriverBrowserManager

async def test_login_flow():
    manager = NodriverBrowserManager()
    profile = manager.profile_manager.create_random_profile()
    
    print("[INFO] Starting browser...")
    browser, tab = await manager.start(profile)
    if not tab:
        print("[FAIL] tab is None!")
        return
    print("[OK] Browser started")
    
    url = "https://account.apple.com/account/manage/section/payment"
    print(f"[NAV] Navigating to: {url}")
    await tab.get(url)
    
    print("[WAIT] Waiting 10 seconds for iframe to load...")
    await asyncio.sleep(10)
    
    # Get frame tree and find login iframe
    frame_tree = await tab.send(cdp_page.get_frame_tree())
    
    def find_login_frame(ft):
        if 'idmsa.apple.com' in (ft.frame.url or ''):
            return ft.frame
        if ft.child_frames:
            for child in ft.child_frames:
                result = find_login_frame(child)
                if result:
                    return result
        return None
    
    login_frame = find_login_frame(frame_tree)
    if not login_frame:
        print("[FAIL] Login iframe not found!")
        return
    
    print(f"[OK] Found iframe: id={login_frame.id_}")
    
    # Create isolated world
    context_id = await tab.send(cdp_page.create_isolated_world(
        frame_id=login_frame.id_,
        world_name="test_flow_world"
    ))
    
    async def eval_in_iframe(expression):
        result = await tab.send(cdp_runtime.evaluate(
            expression=expression,
            context_id=context_id,
            return_by_value=True
        ))
        return result[0].value if hasattr(result[0], 'value') else str(result[0])
    
    # Check initial visibility of password field
    pw_initial = await eval_in_iframe("""
        (() => {
            const pw = document.querySelector('input#password_text_field');
            if (!pw) return 'NOT_FOUND';
            const style = window.getComputedStyle(pw);
            return JSON.stringify({
                visible: pw.offsetParent !== null,
                display: style.display,
                visibility: style.visibility,
                opacity: style.opacity,
                value: pw.value
            });
        })()
    """)
    print(f"[STEP 0] Password field initial state: {pw_initial}")
    
    # ── Step 1: Fill Email ──
    print(f"\n[STEP 1] Filling email: {TEST_EMAIL}")
    email_res = await eval_in_iframe(f"""
        (() => {{
            const email = document.querySelector('input#account_name_text_field');
            if (!email) return 'NO_EMAIL_FIELD';
            email.focus();
            email.value = '{TEST_EMAIL}';
            email.dispatchEvent(new Event('input', {{bubbles: true}}));
            email.dispatchEvent(new Event('change', {{bubbles: true}}));
            return 'FILLED';
        }})()
    """)
    print(f"  Email fill result: {email_res}")
    
    # ── Step 2: Click Continue ──
    print("\n[STEP 2] Clicking Continue button...")
    click_res = await eval_in_iframe("""
        (() => {
            const btn = document.querySelector('button#sign-in') || 
                        document.querySelector('button[type="submit"]');
            if (!btn) return 'NO_BUTTON';
            btn.click();
            return 'CLICKED:' + btn.id;
        })()
    """)
    print(f"  Click result: {click_res}")
    
    # ── Step 3: Wait and monitor transition ──
    print("\n[STEP 3] Waiting for transition (checking every 0.5s for 5 seconds)...")
    for i in range(10):
        await asyncio.sleep(0.5)
        # Create a new isolated world just in case the context was recreated
        try:
            temp_context = await tab.send(cdp_page.create_isolated_world(
                frame_id=login_frame.id_,
                world_name=f"test_flow_world_{i}"
            ))
            
            async def eval_temp(expr):
                r = await tab.send(cdp_runtime.evaluate(
                    expression=expr,
                    context_id=temp_context,
                    return_by_value=True
                ))
                return r[0].value if hasattr(r[0], 'value') else str(r[0])
            
            pw_state = await eval_temp("""
                (() => {
                    const pw = document.querySelector('input#password_text_field');
                    if (!pw) return 'NOT_FOUND';
                    const style = window.getComputedStyle(pw);
                    // Check if password section or parent container has hidden class
                    const parent = pw.closest('.password-container') || pw.parentElement;
                    return JSON.stringify({
                        visible: pw.offsetParent !== null,
                        display: style.display,
                        opacity: style.opacity,
                        value: pw.value,
                        parent_visible: parent ? parent.offsetParent !== null : 'N/A'
                    });
                })()
            """)
            print(f"  T+{0.5*(i+1)}s: {pw_state}")
            
            # If visible, break
            if '"visible":true' in pw_state:
                print("  [OK] Password field is now visible!")
                
                # ── Step 4: Fill Password ──
                print(f"  [STEP 4] Filling password...")
                fill_pw_res = await eval_temp(f"""
                    (() => {{
                        const pw = document.querySelector('input#password_text_field');
                        if (!pw) return 'NO_PW_FIELD';
                        pw.focus();
                        pw.value = '{TEST_PASSWORD}';
                        pw.dispatchEvent(new Event('input', {{bubbles: true}}));
                        pw.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'PW_FILLED';
                    }})()
                """)
                print(f"    Password fill result: {fill_pw_res}")
                
                # ── Step 5: Click Sign-In ──
                print("    [STEP 5] Clicking Sign-In button again...")
                click_signin = await eval_temp("""
                    (() => {
                        const btn = document.querySelector('button#sign-in') || 
                                    document.querySelector('button[type="submit"]');
                        if (!btn) return 'NO_BUTTON';
                        btn.click();
                        return 'CLICKED';
                    })()
                """)
                print(f"    Sign-in click: {click_signin}")
                break
                
        except Exception as e:
            print(f"  T+{0.5*(i+1)}s error: {e}")
            
    print("\n" + "=" * 60)
    print("TEST FLOW COMPLETE - Browser open for 60s")
    print("=" * 60)
    await asyncio.sleep(60)

try:
    asyncio.run(test_login_flow())
except KeyboardInterrupt:
    print("\nExiting...")
