import asyncio
import os
import sys
import nodriver as nd

# Make sure we use the same Python path if needed
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

async def main():
    print("Starting Nodriver browser test...", flush=True)
    browser = await nd.start()
    tab = await browser.get("https://account.apple.com/account/manage/section/payment")
    print("Navigated to Apple ID Sign-In page", flush=True)
    
    # Helper to find element in frames
    async def find_element_in_all_frames(selector):
        # 1. Main tab
        try:
            el = await tab.select(selector, timeout=1)
            if el:
                return el, tab
        except Exception:
            pass
            
        # 2. Child frames
        try:
            frames = await tab.get_frames()
            for frame in frames:
                try:
                    el = await frame.select(selector, timeout=1)
                    if el:
                        return el, frame
                except Exception:
                    pass
        except Exception:
            pass
        return None, None

    # Wait for email field
    email_el = None
    target_frame = None
    print("Waiting for email field...", flush=True)
    for i in range(15):
        email_el, target_frame = await find_element_in_all_frames("input[type='text']")
        if email_el:
            print("Found email field!", flush=True)
            break
        await asyncio.sleep(1)
        
    if not email_el:
        print("Email field not found.", flush=True)
        await browser.stop()
        return

    # Type email
    await email_el.send_keys("test_email@example.com")
    print("Typed email successfully", flush=True)
    await asyncio.sleep(1)
    
    # Try to find continue button
    btn = None
    for selector in ['button#sign-in', 'button.first-button', 'button[idms-sign-in]', 'button']:
        try:
            btn = await target_frame.select(selector, timeout=1)
            if btn:
                break
        except Exception:
            pass
            
    if btn:
        await btn.click()
        print("Clicked continue button", flush=True)
    else:
        print("Pressing Enter as continue button wasn't found", flush=True)
        await email_el.send_keys("\n")
        
    # Wait for password field
    print("Waiting for password field...", flush=True)
    pw_el = None
    target_frame2 = None
    for i in range(15):
        pw_el, target_frame2 = await find_element_in_all_frames("input[type='password']")
        if pw_el:
            print("Found password field!", flush=True)
            break
        await asyncio.sleep(1)
        
    if pw_el:
        await pw_el.send_keys("TestPassword123")
        print("Typed password successfully", flush=True)
        await asyncio.sleep(1)
        
        # Click submit button
        btn2 = None
        for selector in ['button#sign-in', 'button.first-button', 'button[idms-sign-in]', 'button']:
            try:
                btn2 = await target_frame2.select(selector, timeout=1)
                if btn2:
                    break
            except Exception:
                pass
        if btn2:
            await btn2.click()
            print("Clicked submit button", flush=True)
        else:
            await pw_el.send_keys("\n")
            print("Pressed Enter for password submit", flush=True)
            
    # Take screenshot to verify
    await asyncio.sleep(3)
    screenshot_dir = r"C:\Users\Admin\.gemini\antigravity-ide\brain\1209099c-192e-42cb-bd86-628e5621cdfa"
    screenshot_path = os.path.join(screenshot_dir, "test_apple_login_result.jpg")
    await tab.save_screenshot(screenshot_path)
    print(f"Screenshot saved to {screenshot_path}", flush=True)
    
    await browser.stop()
    print("Browser closed. Test complete.", flush=True)

if __name__ == "__main__":
    asyncio.run(main())
