import os, sys, asyncio, logging, json, requests, random, time, re, urllib.parse
import nodriver.cdp.network as cdp_net
sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from cdp_automation_helper import cdp_type_text, cdp_click_btn_by_text, cdp_type_code_6digits
from cdp_reset_helper import reset_microsoft_password_fvia
from tiktok_reg_automation import C69MailBox, TempMailFviainboxes

logger = logging.getLogger(__name__)

async def auto_login_microsoft_and_get_token_cdp(browser, email, password, note_field, client_id, email_id, c69_client, update_step_callback=None):
    tab = browser.main_tab
    
    async def report_step(step_msg: str):
        if update_step_callback:
            try:
                update_step_callback(email, step_msg)
            except Exception:
                pass
                
    try:
        await report_step("Đang khởi tạo trình duyệt & mở login.live.com...")
        # Xóa cookie / session cũ trước khi nạp trang mới
        try:
            await tab.send(cdp_net.clear_browser_cookies())
        except Exception:
            pass
            
        await tab.get("https://login.live.com/")
        await asyncio.sleep(4)
        
        # 1. Điền Email
        await report_step("Đang điền tài khoản Email...")
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
            
        # Kiểm tra nếu email sai / không tồn tại
        body_after_email = await tab.evaluate("document.body.innerText") or ""
        body_after_email_lower = body_after_email.lower()
        if "that microsoft account doesn't exist" in body_after_email_lower:
            logger.warning(f"[{email}] Tài khoản không tồn tại trên Microsoft.")
            if c69_client and email_id:
                c69_client.update_email_status(email_id, 3, "Tài khoản Microsoft không tồn tại")
            return None

        # ⚡ TỐI ƯU HÓA: Bỏ qua màn hình Password nếu Microsoft hiển thị ngay Verify your email (@fviainboxes.com)
        # NẾU MÀN HÌNH NÀY CÓ "USE YOUR PASSWORD" -> BẤM USE YOUR PASSWORD ĐỂ VÀO LUỒNG CHÍNH THỐNG (Tránh bị Microsoft chặn gửi mã từ màn hình verify trước pass)
        has_use_password = "use your password" in body_after_email_lower or "password" in body_after_email_lower
        has_proof_input = await tab.evaluate("Boolean(document.querySelector('#proof-confirmation-email-input, #iProofEmail'))")
        
        if ("@fviainboxes.com" in body_after_email_lower or "fviainboxes" in body_after_email_lower) and has_proof_input and not has_use_password:
            email_prefix = email.split('@')[0].strip()
            expected_fvia_email = f"{email_prefix}@fviainboxes.com".lower()
            logger.info(f"[{email}] ⚡ Bắt được màn hình xác minh fviainboxes.com ngay bước đầu! Điền luôn: {expected_fvia_email}")
            await report_step(f"⚡ Điền email fviainboxes ({expected_fvia_email}) & Gửi mã...")
            await cdp_type_text(tab, "#proof-confirmation-email-input, input[id='proof-confirmation-email-input'], #iProofEmail, input[id='iProofEmail'], input[name*='Proof'], input[type='email'], input[type='text']", expected_fvia_email)
            await asyncio.sleep(1)
            await cdp_click_btn_by_text(tab, ["send code", "next", "submit", "gửi mã", "send", "iSelectProofAction"])
            await asyncio.sleep(5)
            
            # XỬ LÝ NHẬP OTP NGAY TẠI BƯỚC NÀY
            await report_step("Đang chờ mã OTP fviainboxes...")
            fvia_client = TempMailFviainboxes(username=email_prefix, domain="fviainboxes.com")
            otp_code = None
            for attempt in range(1, 4):
                send_time = int(time.time()) - 5
                await report_step(f"Đang chờ mã OTP fviainboxes ({email_prefix}) - Lần {attempt}/3...")
                # Bớt 5s để bù độ trễ lệch clock giữa server Fvia và VPS
                otp_code = await fvia_client.get_microsoft_otp(timeout_secs=65, min_created_at=send_time - 15)
                if otp_code:
                    break
                if attempt < 3:
                    logger.warning(f"[{email}] Chưa có OTP sau lần {attempt}, bấm Revert/Back để yêu cầu gửi lại mã...")
                    await report_step(f"Chưa có OTP, đang bấm gửi lại mã (Lần {attempt+1})...")
                    await cdp_click_btn_by_text(tab, ["back-button", "use a different verification option", "iVerifyCodeRevert", "back", "cancel"])
                    await asyncio.sleep(4)
                    await cdp_type_text(tab, "#proof-confirmation-email-input, input[id='proof-confirmation-email-input'], #iProofEmail, input[id='iProofEmail'], input[name*='Proof'], input[type='email'], input[type='text']", expected_fvia_email)
                    await asyncio.sleep(1)
                    await cdp_click_btn_by_text(tab, ["send code", "next", "submit", "gửi mã", "send", "iSelectProofAction"])
                    await asyncio.sleep(5)
                    
            if otp_code:
                logger.info(f"[{email}] 🎉 Điền mã OTP: {otp_code}")
                await report_step(f"Điền mã OTP ({otp_code}) & Xác nhận...")
                await cdp_type_code_6digits(tab, str(otp_code))
                await asyncio.sleep(0.5)
                await cdp_click_btn_by_text(tab, ["next", "submit", "verify", "sign in", "iVerifyCodeAction"])
                await asyncio.sleep(5)
            else:
                logger.warning(f"[{email}] Không nhận được OTP từ fviainboxes.com sau 3 lần thử! Đang kích hoạt Reset Mật khẩu...")
                await report_step("Chưa có OTP login -> Đang tự động chuyển sang Reset Mật khẩu...")
                email_prefix = email.split('@')[0].strip()
                new_auto_password = "$1$Zxcv123456"
                
                reset_success = await reset_microsoft_password_fvia(
                    tab=tab,
                    email=email,
                    email_prefix=email_prefix,
                    new_password=new_auto_password,
                    report_step=report_step
                )
                if reset_success:
                    password = new_auto_password
                    if c69_client and email_id:
                        c69_client.session.patch(f"{c69_client.base_url}/dashboard/api/emails/{email_id}/", json={"password": new_auto_password, "note": "Đã tự động Reset Mật khẩu"})
                        logger.info(f"[{email}] 🎉 Đã cập nhật mật khẩu mới lên C69 DB!")
                    # Đăng nhập lại với mật khẩu mới
                    await tab.get("https://login.live.com/")
                    await asyncio.sleep(4)
                    await cdp_type_text(tab, "input[name='loginfmt'], input[type='email'], #usernameEntry", email)
                    await asyncio.sleep(0.5)
                    await cdp_click_btn_by_text(tab, ["next", "submit"])
                    await asyncio.sleep(4)
                    await cdp_click_btn_by_text(tab, ["use your password", "other ways to sign in", "password", "sign in with your password", "enter password"])
                    await asyncio.sleep(2)
                    await cdp_type_text(tab, "input[name='passwd'], input[type='password'], #passwordEntry, input[id*='Password']", password)
                    await asyncio.sleep(0.5)
                    await cdp_click_btn_by_text(tab, ["sign in", "next", "submit"])
                    await asyncio.sleep(5)
                else:
                    logger.warning(f"[{email}] Không nhận được OTP từ fviainboxes.com (kể cả reset pass)")
                    await report_step("❌ Không nhận được OTP fviainboxes sau 3 lần!")
                    if c69_client and email_id:
                        c69_client.update_email_status(email_id, 3, "Không nhận được OTP từ fviainboxes.com (3 lần)")
                    return None
        if "verify your email" in body_after_email_lower or "use your password" in body_after_email_lower:
            # Nếu bắt xác minh trước password -> Click "Use your password" để vào màn hình nhập pass chính thống!
            logger.info(f"[{email}] 🛡️ Màn hình bắt xác minh trước password, bấm 'Use your password'...")
            await report_step("Đang bấm 'Use your password'...")
            await cdp_click_btn_by_text(tab, ["use your password", "other ways to sign in", "password", "sign in with your password", "enter password"])
            await asyncio.sleep(3)
            
        # 2. Điền Password
        await report_step("Đang xử lý nhập Password...")
        typed_pass = False
        for _ in range(3):
            typed_pass = await cdp_type_text(tab, "input[name='passwd'], input[type='password'], #passwordEntry, input[id*='Password']", password)
            if typed_pass:
                break
            
            # Click vào "Use your password" hoặc "Other ways to sign in"
            logger.info(f"[{email}] Đang tìm và click vào 'Use your password'...")
            await report_step("Đang click 'Use your password'...")
            await cdp_click_btn_by_text(tab, ["use your password", "other ways to sign in", "password", "sign in with your password", "enter password"])
            await asyncio.sleep(2.5)
            
        if not typed_pass:
            # Kiểm tra nếu lúc này mới hiện màn hình fviainboxes
            body_check = await tab.evaluate("document.body.innerText") or ""
            if "@fviainboxes.com" in body_check.lower():
                email_prefix = email.split('@')[0].strip()
                expected_fvia_email = f"{email_prefix}@fviainboxes.com".lower()
                logger.info(f"[{email}] 🛡️ Điền email fviainboxes: {expected_fvia_email}")
                await cdp_type_text(tab, "#iProofEmail, input[id='iProofEmail'], input[name*='Proof'], input[type='email'], input[type='text']", expected_fvia_email)
                await cdp_click_btn_by_text(tab, ["send code", "next", "submit", "gửi mã", "send", "iSelectProofAction"])
                await asyncio.sleep(4)
            else:
                logger.warning(f"[{email}] Không tìm thấy ô nhập password.")
                if c69_client and email_id:
                    c69_client.update_email_status(email_id, 3, "Không hiển thị ô nhập Password")
                return None
            
        await asyncio.sleep(0.5)
        await report_step("Đang bấm Sign in...")
        await cdp_click_btn_by_text(tab, ["sign in", "next", "submit"])
        await asyncio.sleep(5)
        
        # Kiểm tra pass sai / khóa tài khoản
        body_eval = await tab.evaluate("document.body.innerText")
        body_after_pass = body_eval if isinstance(body_eval, str) else ""
        body_lower = body_after_pass.lower()
        if "that password is incorrect" in body_lower or "password is incorrect" in body_lower:
            logger.warning(f"[{email}] Mật khẩu không chính xác! Đang kích hoạt cơ chế Tự động Reset Mật khẩu qua fviainboxes...")
            email_prefix = email.split('@')[0].strip()
            new_auto_password = "$1$Zxcv123456"
            
            reset_success = await reset_microsoft_password_fvia(
                tab=tab,
                email=email,
                email_prefix=email_prefix,
                new_password=new_auto_password,
                report_step=report_step
            )
            if reset_success:
                password = new_auto_password
                if c69_client and email_id:
                    c69_client.session.patch(f"{c69_client.base_url}/dashboard/api/emails/{email_id}/", json={"password": new_auto_password, "note": "Đã tự động Reset Mật khẩu"})
                    logger.info(f"[{email}] 🎉 Đã cập nhật mật khẩu mới lên C69 DB!")
            else:
                logger.warning(f"[{email}] Reset mật khẩu qua fviainboxes không thành công.")
                if c69_client and email_id:
                    c69_client.update_email_status(email_id, 3, "Mật khẩu sai (Reset thất bại)")
                return None
        if "account has been locked" in body_lower or "your account has been temporarily suspended" in body_lower:
            logger.warning(f"[{email}] Tài khoản bị Microsoft khóa/treo.")
            if c69_client and email_id:
                c69_client.update_email_status(email_id, 3, "Tài khoản bị khóa (Locked)")
            return None
            
        # 3. Click qua Modal Privacy Notice nếu có
        await cdp_click_btn_by_text(tab, ["ok", "next", "continue", "got it", "yes"])
        await asyncio.sleep(3)
        
        # 4. Điều hướng tới OAuth URL (nếu chưa ở trang OAuth)
        cur_url = tab.url or await tab.evaluate("window.location.href") or ""
        redirect_uri = "https://login.microsoftonline.com/common/oauth2/nativeclient"
        auth_url = f"https://login.live.com/oauth20_authorize.srf?" \
                   f"client_id={client_id}" \
                   f"&response_type=code" \
                   f"&redirect_uri={redirect_uri}" \
                   f"&scope=https://outlook.office.com/IMAP.AccessAsUser.All%20https://outlook.office.com/POP.AccessAsUser.All%20https://outlook.office.com/SMTP.Send%20offline_access" \
                   f"&state=c69_auto_token"
                   
        await tab.get(auth_url)
        await asyncio.sleep(4)
        
        # 5. Xử lý các màn hình OAuth / Proof Add
        recovery_box_used = None
        for step in range(15):
            url_step = tab.url or await tab.evaluate("window.location.href") or ""
            
            # A. Nếu có Authorization Code trong URL
            if "code=" in url_step:
                parsed = urllib.parse.urlparse(url_step)
                params = urllib.parse.parse_qs(parsed.query or parsed.fragment)
                code = params.get("code", [None])[0]
                if code:
                    logger.info(f"[{email}] 🎉 Tìm thấy Code, đang đổi lấy Refresh Token...")
                    # Thử lấy token qua endpoint live.com và microsoftonline
                    token_url = "https://login.live.com/oauth20_token.srf"
                    token_url_v2 = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
                    data = {
                        "client_id": client_id,
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                        "scope": "https://outlook.office.com/IMAP.AccessAsUser.All https://outlook.office.com/POP.AccessAsUser.All https://outlook.office.com/SMTP.Send offline_access"
                    }
                    r = None
                    try:
                        r = requests.post(token_url, data=data, timeout=25)
                    except Exception:
                        try:
                            r = requests.post(token_url_v2, data=data, timeout=25)
                        except Exception:
                            pass
                    if not r or r.status_code != 200:
                        try:
                            r = requests.post(token_url_v2, data=data, timeout=25)
                        except Exception:
                            pass
                        
                    if r and r.status_code == 200:
                        res = r.json()
                        new_ref = res.get("refresh_token")
                        if new_ref:
                            if c69_client and email_id:
                                c69_client.save_mailbox_results(email_id, new_ref)
                                c69_client.update_email_status(email_id, 0)
                            logger.info(f"[{email}] 🎉 Cấp mới Refresh Token thành công!")
                            return new_ref
                break

            # Nếu bị rơi vào trang wrongplace của Microsoft
            if "wrongplace" in url_step.lower():
                logger.info(f"[{email}] Đang ở trang wrongplace, chuyển lại về URL OAuth chuẩn...")
                await tab.get(auth_url)
                await asyncio.sleep(4)
                continue
                
            body_eval_step = await tab.evaluate("document.body.innerText")
            body_step = body_eval_step if isinstance(body_eval_step, str) else ""
            body_step_lower = body_step.lower()
            
                    # B. Nếu bắt thiết lập email khôi phục mới (Let's protect your account / proofs/Add - Chưa có email khôi phục)
            if "proofs/add" in url_step.lower():
                await report_step("Đang thiết lập thêm email bảo mật C69...")
                if not recovery_box_used and c69_client:
                    recovery_box_used = c69_client.get_random_valid_recovery_mailbox(exclude_email=email)
                
                if recovery_box_used:
                    rec_email = recovery_box_used.get("email")
                    rec_id = recovery_box_used.get("id")
                    logger.info(f"[{email}] Điền email khôi phục C69: {rec_email}")
                    await report_step(f"Điền email bảo mật C69: {rec_email}...")
                    await cdp_type_text(tab, "input[name='iAltEmail'], input[name='EmailAddress'], input[id*='AltEmail'], input[type='email']", rec_email)
                    await asyncio.sleep(0.5)
                    await cdp_click_btn_by_text(tab, ["next", "submit"])
                    await asyncio.sleep(5)
                    
            # B. Màn hình nhập mã xác thực OTP (Hỗ trợ cả Fviainboxes lẫn C69 Recovery Mail)
            if "iotttext" in body_step_lower or "otc" in body_step_lower or "enter code" in body_step_lower or "codeentry" in body_step_lower or "enter your code" in body_step_lower or "codeentry-0" in body_step_lower or "enter your security code" in body_step_lower:
                await report_step("Đang ở màn hình nhập OTP...")
                otp_code = None
                
                # 1. Nếu trước đó dùng C69 Recovery Box (Màn hình proofs/Add)
                if recovery_box_used:
                    rec_email = recovery_box_used.get("email")
                    rec_id = recovery_box_used.get("id")
                    await report_step(f"Đang chờ mã OTP từ C69 ({rec_email})...")
                    rec_mb = C69MailBox(c69_client, rec_id, rec_email)
                    otp_code = await rec_mb.get_microsoft_otp_code(timeout_secs=60)
                    if otp_code:
                        c69_client.update_recovery_email_only(email_id, rec_email)

                # 2. Ngược lại: Chờ lấy OTP từ fviainboxes.com
                else:
                    email_prefix = email.split('@')[0].strip()
                    fvia_client = TempMailFviainboxes(username=email_prefix, domain="fviainboxes.com")
                    
                    for attempt in range(1, 4):
                        send_time = int(time.time()) - 5
                        await report_step(f"Đang chờ mã OTP fviainboxes ({email_prefix}) - Lần {attempt}/3...")
                        # Bớt 5s để bù độ trễ lệch clock giữa server Fvia và VPS
                        otp_code = await fvia_client.get_microsoft_otp(timeout_secs=65, min_created_at=send_time - 15)
                        if otp_code:
                            break
                        
                        if attempt < 3:
                            logger.warning(f"[{email}] Chưa có OTP sau lần {attempt}, bấm Revert/Back để yêu cầu gửi lại mã...")
                            await report_step(f"Chưa có OTP, đang bấm gửi lại mã (Lần {attempt+1})...")
                            await cdp_click_btn_by_text(tab, ["back-button", "use a different verification option", "iVerifyCodeRevert", "back", "cancel"])
                            await asyncio.sleep(4)
                            expected_fvia_email = f"{email_prefix}@fviainboxes.com".lower()
                            await cdp_type_text(tab, "#proof-confirmation-email-input, input[id='proof-confirmation-email-input'], #iProofEmail, input[id='iProofEmail'], input[name*='Proof'], input[type='email'], input[type='text']", expected_fvia_email)
                            await asyncio.sleep(1)
                            await cdp_click_btn_by_text(tab, ["send code", "next", "submit", "gửi mã", "send", "iSelectProofAction"])
                            await asyncio.sleep(5)
                    if otp_code:
                        expected_fvia_email = f"{email_prefix}@fviainboxes.com".lower()
                        c69_client.update_recovery_email_only(email_id, expected_fvia_email)
                
                # 3. Fallback: Nếu không rõ nguồn, thử kiểm tra cả fviainboxes.com
                if not otp_code:
                    email_prefix = email.split('@')[0].strip()
                    await report_step(f"Đang polling mã OTP ({email_prefix})...")
                    fvia_client = TempMailFviainboxes(username=email_prefix, domain="fviainboxes.com")
                    otp_code = await fvia_client.get_microsoft_otp(timeout_secs=30)
                
                if otp_code:
                    logger.info(f"[{email}] 🎉 Điền mã OTP: {otp_code}")
                    await report_step(f"Điền mã OTP ({otp_code}) & Xác nhận...")
                    await cdp_type_code_6digits(tab, str(otp_code))
                    await asyncio.sleep(0.5)
                    await cdp_click_btn_by_text(tab, ["next", "submit", "verify", "sign in", "iVerifyCodeAction"])
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.warning(f"[{email}] Không nhận được OTP từ fviainboxes.com sau khi chờ! Đang kích hoạt Reset Mật khẩu...")
                    await report_step("Chưa có OTP xác minh -> Đang tự động Reset Mật khẩu...")
                    email_prefix = email.split('@')[0].strip()
                    new_auto_password = "$1$Zxcv123456"
                    
                    reset_success = await reset_microsoft_password_fvia(
                        tab=tab,
                        email=email,
                        email_prefix=email_prefix,
                        new_password=new_auto_password,
                        report_step=report_step
                    )
                    if reset_success:
                        password = new_auto_password
                        if c69_client and email_id:
                            c69_client.session.patch(f"{c69_client.base_url}/dashboard/api/emails/{email_id}/", json={"password": new_auto_password, "note": "Đã tự động Reset Mật khẩu"})
                            logger.info(f"[{email}] 🎉 Đã cập nhật mật khẩu mới lên C69 DB!")
                        # Điều hướng tới trang OAuth để tiếp tục
                        await tab.get(auth_url)
                        await asyncio.sleep(4)
                        continue
                    else:
                        logger.warning(f"[{email}] Không nhận được OTP từ fviainboxes.com")
                        await report_step("❌ Không nhận được OTP fviainboxes!")
                        if c69_client and email_id:
                            c69_client.update_email_status(email_id, 3, "Không nhận được OTP từ fviainboxes.com")
                        return None

            # C. Nếu gặp màn hình xác minh danh tính "Help us protect your account" (ĐÃ CÓ EMAIL KHÔI PHỤC)
            if "protect your account" in body_step_lower or "help us protect" in body_step_lower or "verify your identity" in body_step_lower or "identity/confirm" in url_step.lower():
                await report_step("Đang kiểm tra phương thức xác thực danh tính...")
                
                # 1. Nếu màn hình có option fviainboxes.com -> Click chọn option này và điền email gửi mã
                if "fviainboxes" in body_step_lower or "@fviainboxes.com" in body_step_lower:
                    email_prefix = email.split('@')[0].strip()
                    expected_fvia_email = f"{email_prefix}@fviainboxes.com".lower()
                    
                    logger.info(f"[{email}] 🛡️ Phát hiện màn hình xác minh fviainboxes.com! Bấm chọn option và điền {expected_fvia_email}")
                    await report_step(f"Đang chọn phương thức xác thực {expected_fvia_email}...")
                    
                    # Click vào dòng option fviainboxes
                    await tab.evaluate("""
                    (() => {
                        const el = Array.from(document.querySelectorAll("*")).find(e => (e.innerText || '').includes('fviainboxes.com'));
                        if (el) el.click();
                    })()
                    """)
                    await asyncio.sleep(1.5)
                    
                    # Điền email vào ô input
                    await cdp_type_text(tab, "#iProofEmail, input[id='iProofEmail'], input[name*='Proof'], input[type='email'], input[type='text'], input[id*='Proof'], input[name*='Email']", expected_fvia_email)
                    await asyncio.sleep(1)
                    
                    send_time = int(time.time()) - 5
                    await report_step(f"Đang bấm Gửi mã tới {expected_fvia_email}...")
                    await cdp_click_btn_by_text(tab, ["send code", "next", "submit", "gửi mã", "send", "iSelectProofAction"])
                    await asyncio.sleep(5)
                    
                    # Chờ OTP và nhập mã
                    fvia_client = TempMailFviainboxes(username=email_prefix, domain="fviainboxes.com")
                    otp_code = await fvia_client.get_microsoft_otp(timeout_secs=65, min_created_at=send_time - 15)
                    if otp_code:
                        logger.info(f"[{email}] 🎉 Điền mã OTP: {otp_code}")
                        await report_step(f"Điền mã OTP ({otp_code}) & Xác nhận...")
                        await cdp_type_code_6digits(tab, str(otp_code))
                        await asyncio.sleep(2)
                        await cdp_click_btn_by_text(tab, ["next", "submit", "verify", "sign in", "iVerifyCodeAction"])
                        await asyncio.sleep(6)
                    continue
                
            # C. Nếu bắt OTP từ email lạ ngoài hệ thống
            if "verify your identity" in body_step_lower or "verify your email" in body_step_lower:
                email_hint_match = re.search(r'[\w\.*-]+@[\w\.-]+\.\w+', body_step)
                hint = email_hint_match.group(0) if email_hint_match else "Email lạ"
                logger.warning(f"[{email}] Bắt xác minh qua email khôi phục lạ: {hint}")
                if c69_client and email_id:
                    c69_client.update_email_status(email_id, 3, f"Bắt OTP email khôi phục lạ ({hint})")
                return None
                
            # D. Xử lý màn hình cấp quyền OAuth Consent (Let this app access your info? / Consent/Update)
            if "consent" in url_step.lower() or "access your info" in body_step_lower or "let this app" in body_step_lower:
                logger.info(f"[{email}] 🛡️ Phát hiện màn hình OAuth Consent, bấm Accept/Yes...")
                await report_step("Đang xác nhận cấp quyền ứng dụng (Consent)...")
                await cdp_click_btn_by_text(tab, ["yes", "accept", "idBtn_Accept", "continue"])
                await asyncio.sleep(4)
                continue

            # E. Click Accept / Yes trên các màn hình xác nhận khác
            await cdp_click_btn_by_text(tab, ["yes", "accept", "ok", "next", "continue", "idBtn_Accept", "idSIButton9"])
            await asyncio.sleep(3)
            
    except Exception as e:
        logger.error(f"[{email}] Lỗi trong luồng CDP OAuth: {e}")
        if c69_client and email_id:
            c69_client.update_email_status(email_id, 3, f"Lỗi exception: {str(e)[:100]}")
    return None
