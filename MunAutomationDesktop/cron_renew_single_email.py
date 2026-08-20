import os, sys, asyncio, logging, json, requests, random, time
sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from tiktok_reg_automation import auto_login_microsoft_and_get_token, C69Client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

STATUS_FILE = '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop/cron_renew_stats.json'

async def test_fast_refresh(email_item):
    """Thử refresh token qua API trước"""
    ref_token = email_item.get('refresh_token')
    if not ref_token:
        return False, None
    client_id = email_item.get('client_id') or "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
    endpoints = [
        "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
        "https://login.microsoftonline.com/common/oauth2/v2.0/token",
        "https://login.live.com/oauth20_token.srf"
    ]
    for url in endpoints:
        data = {
            "client_id": client_id,
            "grant_type": "refresh_token",
            "refresh_token": ref_token,
            "scope": "https://graph.microsoft.com/Mail.Read offline_access"
        }
        try:
            loop = asyncio.get_event_loop()
            r = await loop.run_in_executor(None, lambda: requests.post(url, data=data, timeout=6))
            if r.status_code == 200:
                res_json = r.json()
                if "access_token" in res_json:
                    new_ref = res_json.get("refresh_token") or ref_token
                    return True, new_ref
        except Exception:
            pass
    return False, None

async def run_single_email_cron():
    # 1. Đăng nhập C69
    c69 = C69Client("https://cu.c69.us")
    if not c69.login("Admin", "Zxcv@123"):
        logger.error("Không thể đăng nhập C69!")
        return

    # 2. Lấy 1 email cần renew nhất (status != 0 hoặc chưa có refresh token)
    # Lấy danh sách email và chọn 1 email chưa được cập nhật token gần đây
    url_emails = "https://cu.c69.us/dashboard/api/emails/?limit=50&ordering=modified"
    try:
        r = c69.session.get(url_emails, timeout=10)
        if r.status_code != 200:
            logger.error(f"Lỗi fetch emails từ C69: {r.status_code}")
            return
        results = r.json().get('results', [])
    except Exception as e:
        logger.error(f"Lỗi kết nối C69: {e}")
        return

    # Lọc email hotmail/outlook cần renew
    candidates = [
        item for item in results 
        if any(item.get('email', '').lower().endswith(d) for d in ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com'])
    ]
    
    if not candidates:
        logger.info("Không có email nào cần renew lúc này.")
        return

    # Chọn 1 email đầu tiên
    target = candidates[0]
    email = target.get('email')
    password = target.get('password')
    email_id = target.get('id')
    note = target.get('note')
    client_id = target.get('client_id') or "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

    logger.info(f"🎯 [CRON] Bắt đầu xử lý email ID {email_id}: {email}")

    # A. Thử Fast Refresh API trước
    fast_ok, new_ref = await test_fast_refresh(target)
    if fast_ok:
        c69.save_mailbox_results(email_id, new_ref)
        c69.update_email_status(email_id, 0)
        logger.info(f"⚡ [CRON] Fast Refresh thành công cho {email}!")
        return

    if not password:
        logger.warning(f"⚠️ Email {email} không có mật khẩu. Đổi status = 3.")
        c69.update_email_status(email_id, 3)
        return

    # B. Lấy proxy WebShare
    try:
        r_p = requests.get("https://cu.c69.us/500", timeout=8)
        proxies = [p.strip() for p in r_p.text.strip().split("\n") if p.strip()]
        proxy_str = random.choice(proxies) if proxies else ""
    except Exception:
        proxy_str = ""

    # C. Khởi chạy browser xử lý
    manager = NodriverBrowserManager()
    profile = manager.profile_manager.create_random_profile(os_type="Window", socks5=proxy_str)
    
    try:
        browser, tab = await manager.start(
            profile_config=profile,
            proxy_string=proxy_str,
            proxy_type="socks5" if proxy_str else "http",
            headless=True
        )
        if not tab:
            logger.error(f"Không mở được browser cho {email}")
            return

        res_token = await asyncio.wait_for(
            auto_login_microsoft_and_get_token(
                browser=browser,
                email=email,
                password=password,
                note_field=note,
                client_id=client_id,
                email_id=email_id,
                c69_client=c69
            ),
            timeout=90
        )

        if res_token:
            logger.info(f"🎉 [CRON] Cấp token thành công cho {email}!")
            c69.update_email_status(email_id, 0)
        else:
            logger.warning(f"❌ [CRON] Không lấy được token cho {email}. Cập nhật status = 3.")
            c69.update_email_status(email_id, 3)

    except asyncio.TimeoutError:
        logger.warning(f"⏳ [CRON] Timeout khi xử lý {email}.")
        c69.update_email_status(email_id, 3)
    except Exception as e:
        logger.error(f"❌ [CRON] Lỗi: {e}")
        c69.update_email_status(email_id, 3)
    finally:
        try:
            await manager.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(run_single_email_cron())
