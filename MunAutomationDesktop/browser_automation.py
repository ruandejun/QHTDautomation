"""
Browser Automation Module
Contains browser driver start/control actions, Apple ID login filling,
payment details form autofill, and multiple card sequence automation.
"""
import asyncio
import json
import time
import nodriver
import nodriver.cdp.page as cdp_page
import nodriver.cdp.runtime as cdp_runtime

async def evaluate_in_iframe_robust(tab, expression):
    """Evaluate a JS expression inside the cross-origin idmsa.apple.com iframe safely, handling context destruction"""
    def find_login_frame(ft):
        if 'idmsa.apple.com' in (ft.frame.url or ''):
            return ft.frame
        if ft.child_frames:
            for child in ft.child_frames:
                result = find_login_frame(child)
                if result:
                    return result
        return None
        
    try:
        frame_tree = await tab.send(cdp_page.get_frame_tree())
        login_frame = find_login_frame(frame_tree)
        if not login_frame:
            return None, "IFRAME_NOT_FOUND"
        
        # Always create a new isolated world context to guarantee executing on the current active document state
        context_id = await tab.send(cdp_page.create_isolated_world(
            frame_id=login_frame.id_,
            world_name="mun_login_inject_robust"
        ))
        
        result = await tab.send(cdp_runtime.evaluate(
            expression=expression,
            context_id=context_id,
            return_by_value=True
        ))
        val = result[0].value if hasattr(result[0], 'value') else str(result[0])
        return val, None
    except Exception as e:
        return None, str(e)

async def automate_apple_login(tab, apple_id, password):
    """Automate Apple ID login using CDP to access cross-origin idmsa.apple.com iframe"""
    print(f"[MunAutomation] Automating Apple ID login for: {apple_id}")
    
    # 1. Wait for email input to be visible in iframe
    email_found = False
    for attempt in range(30):  # 30 seconds timeout
        val, err = await evaluate_in_iframe_robust(
            tab,
            "!!(document.querySelector('input#account_name_text_field') || document.querySelector('input[type=\"email\"]'))"
        )
        if val is True:
            email_found = True
            print(f"[MunAutomation] Email field detected in iframe at attempt {attempt}")
            break
        if attempt % 5 == 0:
            print(f"[MunAutomation] Waiting for email field... attempt {attempt} (err={err})")
        await asyncio.sleep(1)
    
    if not email_found:
        print("[MunAutomation] Email field not found in login iframe after 30s")
        return False
    
    # 2. Fill email field
    fill_res, err = await evaluate_in_iframe_robust(tab, f"""
        (() => {{
            const inp = document.querySelector('input#account_name_text_field') ||
                       document.querySelector('input[type="email"]') ||
                       document.querySelector('input[type="text"]');
            if (!inp) return 'NO_INPUT';
            inp.focus();
            inp.value = '{apple_id}';
            inp.dispatchEvent(new Event('input', {{bubbles: true}}));
            inp.dispatchEvent(new Event('change', {{bubbles: true}}));
            return 'OK';
        }})()
    """)
    print(f"[MunAutomation] Email fill result: {fill_res} (err={err})")
    if fill_res != 'OK':
        return False
        
    await asyncio.sleep(1)
    
    # 3. Click the Continue/Sign-In button to trigger password transition
    click_res, err = await evaluate_in_iframe_robust(tab, """
        (() => {
            const btn = document.querySelector('button#sign-in') ||
                       document.querySelector('button.si-button') ||
                       document.querySelector('button[type="submit"]');
            if (btn) {
                btn.click();
                return 'CLICKED';
            }
            return 'NO_BUTTON';
        })()
    """)
    print(f"[MunAutomation] Continue button click: {click_res} (err={err})")
    
    # 4. Wait for transition and fill password
    print("[MunAutomation] Waiting for password field to be ready...")
    pw_filled = False
    for attempt in range(20):
        await asyncio.sleep(0.5)
        is_visible, err = await evaluate_in_iframe_robust(tab, """
            (() => {
                const pw = document.querySelector('input#password_text_field') ||
                           document.querySelector('input[type="password"]');
                return pw && pw.offsetParent !== null;
            })()
        """)
        
        if is_visible is True:
            # Fill password
            fill_pw, err = await evaluate_in_iframe_robust(tab, f"""
                (() => {{
                    const inp = document.querySelector('input#password_text_field') ||
                               document.querySelector('input[type="password"]');
                    if (!inp) return 'NO_PW';
                    inp.focus();
                    inp.value = '{password}';
                    inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                    inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return 'OK';
                }})()
            """)
            print(f"[MunAutomation] Password fill result: {fill_pw} (err={err})")
            if fill_pw == 'OK':
                pw_filled = True
                
                # Click sign-in final
                await asyncio.sleep(1)
                signin_res, err = await evaluate_in_iframe_robust(tab, """
                    (() => {
                        const btn = document.querySelector('button#sign-in') ||
                                   document.querySelector('button[type="submit"]');
                        if (btn) {
                            btn.click();
                            return 'CLICKED_FINAL';
                        }
                        return 'NO_BTN';
                    })()
                """)
                print(f"[MunAutomation] Final Sign-In click: {signin_res} (err={err})")
                break
    
    if not pw_filled:
        print("[MunAutomation] Failed to fill password field")
        return False
        
    print("[MunAutomation] Login automation completed successfully")
    return True

async def automate_payment_filling(tab, card_data):
    """Automate card form filling using Nodriver elements directly (bypassing JS evaluate sandbox)"""
    print("[MunAutomation] Automating card form filling...")
    
    for _ in range(12):
        # 1. Get all inputs from main page
        all_inputs = []
        try:
            all_inputs.extend(await tab.select_all("input"))
            all_inputs.extend(await tab.select_all("select"))
        except Exception:
            pass
            
        # 2. Get all inputs from all iframes
        try:
            iframes = await tab.select_all("iframe")
            for iframe in iframes:
                try:
                    all_inputs.extend(await tab.query_selector_all("input", iframe))
                    all_inputs.extend(await tab.query_selector_all("select", iframe))
                except Exception:
                    pass
        except Exception:
            pass
            
        if not all_inputs:
            await asyncio.sleep(1)
            continue
            
        filled_any = False
        for input_el in all_inputs:
            try:
                name = input_el.attrs.get('name', '').lower()
                id_ = input_el.attrs.get('id', '').lower()
                label = input_el.attrs.get('aria-label', '').lower()
                placeholder = input_el.attrs.get('placeholder', '').lower()
                
                if 'cardnumber' in id_ or 'cardnumber' in name or 'card number' in label or 'card number' in placeholder:
                    await input_el.send_keys(card_data.get("card_number", ""))
                    filled_any = True
                    print("[MunAutomation] Filled card number")
                    
                elif 'exp' in id_ or 'exp' in name or 'expiration' in label or 'expiration' in placeholder:
                    if 'mm/yy' in placeholder or 'month/year' in label:
                        combined = f"{card_data.get('expiry_month', '')}{card_data.get('expiry_year', '')[-2:]}"
                        await input_el.send_keys(combined)
                        filled_any = True
                        print("[MunAutomation] Filled combined expiry date")
                    elif 'month' in id_ or 'month' in name or 'month' in label or 'mm' in placeholder:
                        await input_el.send_keys(card_data.get('expiry_month', ''))
                        filled_any = True
                        print("[MunAutomation] Filled expiry month")
                    elif 'year' in id_ or 'year' in name or 'year' in label or 'yy' in placeholder:
                        val = card_data.get('expiry_year', '')
                        if len(val) == 4 and 'yy' in placeholder and not 'yyyy' in placeholder:
                            val = val[-2:]
                        await input_el.send_keys(val)
                        filled_any = True
                        print("[MunAutomation] Filled expiry year")
                        
                elif 'cvv' in id_ or 'cvv' in name or 'cvc' in id_ or 'cvc' in name or 'security code' in label or 'security code' in placeholder or 'verification' in id_ or 'verification' in name:
                    await input_el.send_keys(card_data.get('cvv', ''))
                    filled_any = True
                    print("[MunAutomation] Filled security code (CVV)")
                    
                elif 'firstname' in id_ or 'firstname' in name or 'first name' in label or 'first name' in placeholder:
                    await input_el.send_keys(card_data.get('first_name', 'Nguyen'))
                elif 'lastname' in id_ or 'lastname' in name or 'last name' in label or 'last name' in placeholder:
                    await input_el.send_keys(card_data.get('last_name', 'Van A'))
                elif 'street' in id_ or 'street' in name or 'address' in label or 'address' in placeholder:
                    await input_el.send_keys(card_data.get('address_line1', '123 Le Loi'))
                elif 'city' in id_ or 'city' in name or 'city' in label or 'city' in placeholder:
                    await input_el.send_keys(card_data.get('city', 'Ho Chi Minh'))
                elif 'zip' in id_ or 'zip' in name or 'postal' in label or 'postal' in placeholder:
                    await input_el.send_keys(card_data.get('zip_code', '70000'))
                elif 'phone' in id_ or 'phone' in name or 'phone' in label or 'phone' in placeholder:
                    await input_el.send_keys(card_data.get('phone', '0987654321'))
            except Exception as e_field:
                print(f"[MunAutomation] Error filling individual field: {e_field}")
        
        if filled_any:
            print("[MunAutomation] Card fields found and auto-filled!")
            break
        await asyncio.sleep(1)

async def find_button_by_text(tab, texts):
    """Tìm button hoặc clickable element có chứa một trong các chuỗi văn bản chỉ định"""
    all_buttons = []
    try:
        all_buttons.extend(await tab.select_all("button"))
        all_buttons.extend(await tab.select_all("input[type='button']"))
        all_buttons.extend(await tab.select_all("input[type='submit']"))
        all_buttons.extend(await tab.select_all("a"))
        all_buttons.extend(await tab.select_all("span"))
    except Exception:
        pass
        
    try:
        iframes = await tab.select_all("iframe")
        for iframe in iframes:
            try:
                all_buttons.extend(await tab.query_selector_all("button", iframe))
                all_buttons.extend(await tab.query_selector_all("input[type='button']", iframe))
                all_buttons.extend(await tab.query_selector_all("input[type='submit']", iframe))
                all_buttons.extend(await tab.query_selector_all("a", iframe))
                all_buttons.extend(await tab.query_selector_all("span", iframe))
            except Exception:
                pass
    except Exception:
        pass
        
    for btn in all_buttons:
        try:
            text = ""
            if btn.tag == 'input':
                text = btn.attrs.get('value', '').lower()
            else:
                text = btn.text.lower()
                
            for t in texts:
                if t.lower() in text:
                    return btn
        except Exception:
            pass
    return None

async def automate_add_payment_cards(bridge_obj, tab, cards):
    """Automate adding a list of cards to Apple account one by one"""
    success_count = 0
    total_count = len(cards)
    
    for idx, card in enumerate(cards):
        card_num = card.get("card_number", "")
        print(f"[MunAutomation] Attempting to add card {idx+1}/{total_count}: ****{card_num[-4:]}")
        bridge_obj.statusMessage.emit(f"💳 Đang thêm thẻ {idx+1}/{total_count} (****{card_num[-4:]})...")
        
        # 1. Ensure we are on the payment section page
        try:
            if "section/payment" not in tab.url:
                await tab.get("https://account.apple.com/account/manage/section/payment")
                await asyncio.sleep(3)
        except Exception:
            pass
            
        # 2. Click "Add Payment Method"
        clicked_add = False
        for _ in range(5):
            try:
                btn = await find_button_by_text(tab, ['add payment', 'add a payment', 'thêm phương thức', 'thêm thẻ'])
                if btn:
                    await btn.click()
                    clicked_add = True
                    print("[MunAutomation] Clicked 'Add Payment Method' button")
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
            
        # Wait for the card form to appear
        await asyncio.sleep(3)
        
        # 3. Fill the form
        try:
            await automate_payment_filling(tab, card)
        except Exception as e_fill:
            print(f"[MunAutomation] Fill error: {e_fill}")
            
        # 4. Click Save
        clicked_save = False
        for _ in range(3):
            try:
                btn = await find_button_by_text(tab, ['save', 'lưu'])
                if btn:
                    await btn.click()
                    clicked_save = True
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
            
        print("[MunAutomation] Clicked save, waiting for validation results...")
        await asyncio.sleep(6) # Wait for Apple to validate and process
        
        # 5. Check if success or error
        has_error = False
        error_message = ""
        for _ in range(5):
            try:
                error_els = []
                try:
                    error_els.extend(await tab.select_all(".error-message, .alert, [role='alert'], .error, .msg-error"))
                except Exception:
                    pass
                try:
                    iframes = await tab.select_all("iframe")
                    for iframe in iframes:
                        error_els.extend(await tab.query_selector_all(".error-message, .alert, [role='alert'], .error, .msg-error", iframe))
                except Exception:
                    pass
                    
                for el in error_els:
                    txt = el.text.strip()
                    if txt:
                        has_error = True
                        error_message = txt
                        break
                        
                if has_error:
                    break
                    
                # Also check for invalid fields (red fields)
                invalid_els = []
                try:
                    invalid_els.extend(await tab.select_all(".invalid, [aria-invalid='true']"))
                except Exception:
                    pass
                try:
                    iframes = await tab.select_all("iframe")
                    for iframe in iframes:
                        invalid_els.extend(await tab.query_selector_all(".invalid, [aria-invalid='true']", iframe))
                except Exception:
                    pass
                    
                if len(invalid_els) > 0:
                    has_error = True
                    error_message = "Thông tin nhập không hợp lệ (Trường đỏ)"
                    break
            except Exception:
                pass
            await asyncio.sleep(1)
            
        if has_error:
            print(f"[MunAutomation] Card declined/error: {error_message}")
            bridge_obj.statusMessage.emit(f"❌ Thẻ ****{card_num[-4:]} bị lỗi: {error_message}")
            bridge_obj.update_card_status_on_server(card.get("id"), "Thẻ chết")
            
            # Click Cancel to close form and reset for next card
            try:
                btn = await find_button_by_text(tab, ['cancel', 'hủy'])
                if btn:
                    await btn.click()
            except Exception:
                pass
            await asyncio.sleep(2)
        else:
            print(f"[MunAutomation] Card ****{card_num[-4:]} added successfully!")
            bridge_obj.statusMessage.emit(f"✅ Thẻ ****{card_num[-4:]} thành công!")
            success_count += 1
            bridge_obj.update_card_status_on_server(card.get("id"), "Đã sử dụng")
            await asyncio.sleep(3)
            
    # Final result notification
    bridge_obj.statusMessage.emit(f"🎉 Hoàn tất thêm thẻ: {success_count}/{total_count} thành công!")
    return success_count
