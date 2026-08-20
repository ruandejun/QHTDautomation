import os, sys, asyncio, logging, json, requests, random, time
sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from tiktok_reg_automation import auto_login_microsoft_and_get_token, C69Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Cấu hình Telegram Bot từ backend C69
TELEGRAM_BOT_TOKEN = "2115090413:AAEgFk2-n1kP1X_O_Qk_32H67w2eA_XYZ" # Hoặc token checker
TELEGRAM_CHAT_ID = "8229878462" # Tony Telegram ID

def send_telegram_alert(msg: str):
    """Gửi cảnh báo / thông báo trạng thái realtime về Telegram"""
    try:
        # 1. Gửi qua Hermes Agent (Nội bộ nếu có)
        # 2. Hoặc gửi trực tiếp qua Telegram Bot API
        url = f"https://api.telegram.org/bot7597148564:AAErkUf7Ld_xKxGqGz_k92/sendMessage" # Fallback bot token
        # Gửi thông báo định dạng HTML
        data = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": msg,
            "parse_mode": "HTML"
        }
        # Tạm log console
        logger.info(f"[TELEGRAM NOTIFY] {msg}")
    except Exception as e:
        logger.error(f"Lỗi gửi Telegram: {e}")

async def test_fast_refresh(email_item):
    email = email_item.get('email')
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

async def run_email_checker_and_renew_job():
    logger.info("🔍 [CHECKER] Bắt đầu quét & kiểm tra trạng thái Email Microsoft...")
    
    # 1. Đăng nhập C69
    c69 = C69Client("https://cu.c69.us")
    if not c69.login("Admin", "Zxcv@123"):
        logger.error("Không thể đăng nhập C69!")
        return

    # 2. Lấy 1 batch 20 email cần check/renew (Ưu tiên modified cũ nhất)
    url_emails = "https://cu.c69.us/dashboard/api/emails/?limit=20&ordering=modified"
    try:
        r = c69.session.get(url_emails, timeout=10)
        if r.status_code != 200:
            return
        results = r.json().get('results', [])
    except Exception as e:
        logger.error(f"Lỗi fetch email: {e}")
        return

    candidates = [
        item for item in results 
        if any(item.get('email', '').lower().endswith(d) for d in ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com'])
    ]

    for item in candidates:
        email = item.get('email')
        email_id = item.get('id')
        password = item.get('password')
        note = item.get('note')
        client_id = item.get('client_id') or "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

        # A. Kiểm tra Fast Refresh API
        fast_ok, new_ref = await test_fast_refresh(item)
        if fast_ok:
            c69.save_mailbox_results(email_id, new_ref)
            c69.update_email_status(email_id, 0)
            logger.info(f"✅ [VALID] Email {email} (ID: {email_id}) - Token OK & Đã làm mới!")
            continue

        # B. Nếu không có refresh_token hoặc refresh_token chết -> Cần cấp lại
        if not password:
            logger.warning(f"⚠️ [NO PASS] Email {email} (ID: {email_id}) không có mật khẩu -> Set Status=3 để xử lý tay.")
            c69.update_email_status(email_id, 3)
            continue

        # C. Thử mở browser tự động login cấp lại
        logger.info(f"🔄 [RENEWING] Đang mở trình duyệt cấp lại token cho: {email}...")
        try:
            r_p = requests.get("https://cu.c69.us/500", timeout=8)
            proxies = [p.strip() for p in r_p.text.strip().split("\n") if p.strip()]
            proxy_str = random.choice(proxies) if proxies else ""
        except Exception:
            proxy_str = ""

        manager = NodriverBrowserManager()
        profile = manager.profile_manager.create_random_profile(os_type="Window", socks5=proxy_str)
        try:
            browser, tab = await manager.start(
                profile_config=profile,
                proxy_string=proxy_str,
                proxy_type="socks5" if proxy_str else "http",
                headless=True
            )
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
                logger.info(f"🎉 [SUCCESS] Đã cấp token mới thành công cho {email}!")
                c69.update_email_status(email_id, 0)
            else:
                logger.warning(f"❌ [MANUAL NEEDED] Không tự cấp được token cho {email} -> Đổi status=3 để check tay.")
                c69.update_email_status(email_id, 3)
        except Exception as e_b:
            logger.error(f"Lỗi browser khi xử lý {email}: {e_b}")
            c69.update_email_status(email_id, 3)
        finally:
            try:
                await manager.close()
            except Exception:
                pass
        
        # Nghỉ nhẹ giữa các email
        await asyncio.sleep(2)

if __name__ == "__main__":
    asyncio.run(run_email_checker_and_renew_job())
