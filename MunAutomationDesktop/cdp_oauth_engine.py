import os, sys, asyncio, logging, json, requests, random, time, re, urllib.parse
sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from cdp_automation_helper import cdp_type_text, cdp_click_btn_by_text
from tiktok_reg_automation import C69Client, C69MailBox

logger = logging.getLogger(__name__)

async def auto_login_microsoft_and_get_token_cdp(browser, email, password, note_field, client_id, email_id, c69_client):
    tab = browser.main_tab
    try:
        await tab.get("https://login.live.com/")
        await asyncio.sleep(4)
        
        # 1. Điền Email
        typed_email = await cdp_type_text(tab, "input[name='loginfmt'], input[type='email'], #usernameEntry", email)
        if not typed_email:
            logger.warning(f"[{email}] Không tìm thấy ô nhập email.")
            return None
        await asyncio.sleep(0.5)
        await cdp_click_btn_by_text(tab, ["next", "submit"])
        await asyncio.sleep(4)
        
        # Kiểm tra nếu email sai / không tồn tại
        body_after_email = await tab.evaluate("document.body.innerText") or ""
        if "that microsoft account doesn't exist" in body_after_email.lower():
            logger.warning(f"[{email}] Tài khoản không tồn tại trên Microsoft.")
            if c69_client and email_id:
                c69_client.update_email_status(email_id, 3, "Tài khoản Microsoft không tồn tại")
            return None
            
        # 2. Điền Password (có xử lý nút "Use your password" hoặc các phương thức đăng nhập khác)
        await cdp_click_btn_by_text(tab, ["use your password", "other ways to sign in", "password"])
        await asyncio.sleep(2)
        
        typed_pass = await cdp_type_text(tab, "input[name='passwd'], input[type='password'], #passwordEntry, input[id*='Password']", password)
        if not typed_pass:
            # Thử lại bấm "Use your password" hoặc click trực tiếp vào chữ "Use your password"
            await tab.evaluate("""
            (() => {
                const el = Array.from(document.querySelectorAll("a, button, span, div")).find(e => (e.innerText || "").toLowerCase().includes("use your password") || (e.innerText || "").toLowerCase().includes("password"));
                if (el) el.click();
            })()
            """)
            await asyncio.sleep(3)
            typed_pass = await cdp_type_text(tab, "input[name='passwd'], input[type='password'], #passwordEntry, input[id*='Password']", password)
            
        if not typed_pass:
            logger.warning(f"[{email}] Không tìm thấy ô nhập password.")
            if c69_client and email_id:
                c69_client.update_email_status(email_id, 3, "Không hiển thị ô nhập Password")
            return None
            
        await asyncio.sleep(0.5)
        await cdp_click_btn_by_text(tab, ["sign in", "next", "submit"])
        await asyncio.sleep(5)
        
        # Kiểm tra pass sai / khóa tài khoản
        body_after_pass = await tab.evaluate("document.body.innerText") or ""
        body_lower = body_after_pass.lower()
        if "that password is incorrect" in body_lower or "password is incorrect" in body_lower:
            logger.warning(f"[{email}] Mật khẩu không chính xác.")
            if c69_client and email_id:
                c69_client.update_email_status(email_id, 3, "Mật khẩu sai (Incorrect password)")
            return None
        if "account has been locked" in body_lower or "your account has been temporarily suspended" in body_lower:
            logger.warning(f"[{email}] Tài khoản bị Microsoft khóa/treo.")
            if c69_client and email_id:
                c69_client.update_email_status(email_id, 3, "Tài khoản bị khóa (Locked)")
            return None
            
        # 3. Click qua Modal Privacy Notice nếu có
        await cdp_click_btn_by_text(tab, ["ok", "next", "continue", "got it", "yes"])
        await asyncio.sleep(3)
        
        # 4. Điều hướng tới OAuth URL
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        auth_url = f"https://login.live.com/oauth20_authorize.srf?" \
                   f"client_id={client_id}" \
                   f"&response_type=code" \
                   f"&redirect_uri={redirect_uri}" \
                   f"&scope=https://graph.microsoft.com/Mail.Read%20offline_access" \
                   f"&state=c69_auto_token"
                   
        await tab.get(auth_url)
        await asyncio.sleep(4)
        
        # 5. Xử lý các màn hình OAuth / Proof Add
        recovery_box_used = None
        for step in range(12):
            url_step = tab.url or await tab.evaluate("window.location.href") or ""
            
            # A. Nếu có Authorization Code trong URL
            if "code=" in url_step:
                parsed = urllib.parse.urlparse(url_step)
                params = urllib.parse.parse_qs(parsed.query or parsed.fragment)
                code = params.get("code", [None])[0]
                if code:
                    logger.info(f"[{email}] 🎉 Tìm thấy Code, đang đổi lấy Refresh Token...")
                    token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
                    data = {
                        "client_id": client_id,
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "scope": "https://graph.microsoft.com/Mail.Read offline_access"
                    }
                    r = requests.post(token_url, data=data, timeout=10)
                    if r.status_code == 200:
                        res = r.json()
                        new_ref = res.get("refresh_token")
                        if new_ref:
                            if c69_client and email_id:
                                c69_client.save_mailbox_results(email_id, new_ref)
                                c69_client.update_email_status(email_id, 0)
                            logger.info(f"[{email}] 🎉 Cấp mới Refresh Token thành công!")
                            return new_ref
                break
                
            body_step = await tab.evaluate("document.body.innerText") or ""
            body_step_lower = body_step.lower()
            
            # B. Nếu bắt thiết lập email khôi phục mới (Let's protect your account / proofs/Add)
            if "proofs/add" in url_step.lower() or "protect your account" in body_step_lower:
                if not recovery_box_used and c69_client:
                    recovery_box_used = c69_client.get_random_valid_recovery_mailbox(exclude_email=email)
                
                if recovery_box_used:
                    rec_email = recovery_box_used.get("email")
                    rec_id = recovery_box_used.get("id")
                    logger.info(f"[{email}] Điền email khôi phục C69: {rec_email}")
                    await cdp_type_text(tab, "input[name='iAltEmail'], input[name='EmailAddress'], input[id*='AltEmail'], input[type='email']", rec_email)
                    await asyncio.sleep(0.5)
                    await cdp_click_btn_by_text(tab, ["next", "submit"])
                    await asyncio.sleep(5)
                    
                    # Chờ lấy OTP từ hòm thư khôi phục
                    rec_mb = C69MailBox(c69_client, rec_id, rec_email)
                    otp_code = await rec_mb.get_microsoft_otp_code(timeout_secs=60)
                    if otp_code:
                        logger.info(f"[{email}] Nhập OTP khôi phục: {otp_code}")
                        await cdp_type_text(tab, "input[id='idTxtBx_OTC'], input[name='otc'], input[id*='OTC'], input[type='tel']", otp_code)
                        await asyncio.sleep(0.5)
                        await cdp_click_btn_by_text(tab, ["next", "submit"])
                        # Lưu ngay recovery_email lên DB C69
                        c69_client.update_recovery_email_only(email_id, rec_email)
                        await asyncio.sleep(5)
                    else:
                        logger.warning(f"[{email}] Không nhận được OTP từ hòm thư {rec_email}")
                continue
                
            # C. Nếu bắt OTP từ email lạ ngoài hệ thống
            if "verify your identity" in body_step_lower or "verify your email" in body_step_lower:
                email_hint_match = re.search(r'[\w\.*-]+@[\w\.-]+\.\w+', body_step)
                hint = email_hint_match.group(0) if email_hint_match else "Email lạ"
                logger.warning(f"[{email}] Bắt xác minh qua email khôi phục lạ: {hint}")
                if c69_client and email_id:
                    c69_client.update_email_status(email_id, 3, f"Bắt OTP email khôi phục lạ ({hint})")
                return None
                
            # D. Click Accept / Yes trên các màn hình xác nhận
            await cdp_click_btn_by_text(tab, ["yes", "accept", "ok", "next", "continue"])
            await asyncio.sleep(3)
            
    except Exception as e:
        logger.error(f"[{email}] Lỗi trong luồng CDP OAuth: {e}")
        if c69_client and email_id:
            c69_client.update_email_status(email_id, 3, f"Lỗi exception: {str(e)[:100]}")
    return None
