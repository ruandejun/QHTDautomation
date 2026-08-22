import asyncio
import os
import sys
import requests
import json
import time
import urllib.parse
import re
import logging
from typing import Optional, Dict, Any

from tiktok_reg_automation import TempMailFviainboxes
from cdp_automation_helper import (
    cdp_type_text,
    cdp_click_btn_by_text,
    cdp_type_code_6digits
)

logger = logging.getLogger(__name__)

async def reset_microsoft_password_fvia(tab, email: str, email_prefix: str, new_password: str, report_step=None) -> bool:
    """Tự động thực hiện Reset Password qua hòm thư fviainboxes.com khi bị sai pass hoặc lỗi login"""
    try:
        if report_step:
            await report_step("🛡️ Đang chuyển sang quy trình Reset Mật khẩu qua fviainboxes...")
        logger.info(f"[{email}] 🛡️ Bắt đầu luồng Reset Mật khẩu qua fviainboxes.com...")
        
        reset_url = "https://account.live.com/password/reset?mkt=EN-US&uiflavor=host"
        await tab.get(reset_url)
        await asyncio.sleep(4)
        
        # 1. Điền email
        await cdp_type_text(tab, "input[name='loginfmt'], input[type='email'], #usernameEntry", email)
        await asyncio.sleep(1)
        await cdp_click_btn_by_text(tab, ["next", "submit", "tiếp theo"])
        await asyncio.sleep(4)
        
        # 2. Chọn radio và điền prefix
        await tab.evaluate("""
        (() => {
            const radio = document.querySelector("#textproofOption0, input[type='radio']");
            if (radio) radio.click();
        })()
        """)
        await asyncio.sleep(1)
        await cdp_type_text(tab, "#proofInput0, input[name='proofPickerEmail']", email_prefix)
        await asyncio.sleep(1)
        
        send_time = int(time.time()) - 10
        if report_step:
            await report_step(f"Đang gửi mã Reset Password tới {email_prefix}@fviainboxes.com...")
        await cdp_click_btn_by_text(tab, ["get code", "send code", "next", "submit", "iSelectProofAction"])
        await asyncio.sleep(5)
        
        # 3. Polling OTP từ Fviainboxes
        if report_step:
            await report_step("Đang chờ mã OTP Reset Password từ fviainboxes...")
        fvia = TempMailFviainboxes(username=email_prefix, domain="fviainboxes.com")
        
        otp = None
        for sec in range(45):
            try:
                r = requests.get(f"https://fviainboxes.com/messages?username={email_prefix}&domain=fviainboxes.com", timeout=10)
                if r.status_code == 200:
                    msgs = r.json().get('result', [])
                    for m in msgs:
                        if "password reset" in m.get('subject', '').lower() and m.get('createdAt', 0) >= send_time - 15:
                            r_det = requests.get(f"https://fviainboxes.com/message?username={email_prefix}&domain=fviainboxes.com&id={m.get('id')}", timeout=10)
                            match = re.search(r'Here is your code:.*?([0-9]{6})', r_det.text, re.DOTALL) or re.search(r'\b([0-9]{6})\b', r_det.text)
                            if match:
                                otp = match.group(1)
                                break
            except Exception:
                pass
            if otp:
                break
            await asyncio.sleep(2)
            
        if not otp:
            logger.warning(f"[{email}] Không nhận được OTP Reset Password sau 90s")
            return False
            
        logger.info(f"[{email}] 🎉 Nhận được OTP Reset: {otp}")
        if report_step:
            await report_step(f"Điền OTP Reset ({otp}) & Đặt mật khẩu mới...")
            
        # 4. Điền OTP vào #iVerifyText
        await cdp_type_text(tab, "#iVerifyText, input[name='iVerifyText'], input[type='number']", str(otp))
        await asyncio.sleep(1)
        await cdp_click_btn_by_text(tab, ["next", "submit", "verify", "iVerifyIdentityAction"])
        await asyncio.sleep(6)
        
        # 5. Đặt mật khẩu mới
        await cdp_type_text(tab, "input[name='PasswordInput'], input[type='password'], #PasswordInput, input[id*='Password'], #iPassword", new_password)
        await asyncio.sleep(1)
        await cdp_type_text(tab, "input[name='RetypePasswordInput'], #RetypePasswordInput, input[id*='Retype'], #iRetypePassword", new_password)
        await asyncio.sleep(1)
        
        await cdp_click_btn_by_text(tab, ["next", "save", "finish", "done", "tiếp theo", "iSubmit", "iResetPwdAction"])
        await asyncio.sleep(6)
        
        logger.info(f"[{email}] 🎉 Đã đổi mật khẩu mới thành công: {new_password}")
        return True
    except Exception as e:
        logger.error(f"[{email}] Lỗi trong quá trình Reset Password: {e}")
        return False
