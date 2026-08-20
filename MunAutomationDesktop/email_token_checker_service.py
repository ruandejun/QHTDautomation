import os, sys, asyncio, logging, json, requests, random, time, re
from datetime import datetime

sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from tiktok_reg_automation import auto_login_microsoft_and_get_token, C69Client

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

# Telegram Bot Token và Chat ID của Tony
def get_telegram_bot_token():
    # 1. Thử lấy từ /root/.hermes/.env (Token bot chính đang chat)
    try:
        if os.path.exists('/root/.hermes/.env'):
            with open('/root/.hermes/.env') as f:
                content = f.read()
            m = re.search(r'TELEGRAM_BOT_TOKEN=([^\s\r\n]+)', content)
            if m:
                return m.group(1).strip()
    except Exception:
        pass
    return "8723774645:AAFqKsqLg4_eY_v6sV0e4c6W7-Ei4mFUg"

TELEGRAM_BOT_TOKEN = get_telegram_bot_token()
TELEGRAM_CHAT_ID = "8229878462"  # Tony

def send_telegram_message(text: str, reply_markup=None):
    """Gửi tin nhắn mới lên Telegram và trả về message_id để edit realtime"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            return r.json().get('result', {}).get('message_id')
    except Exception as e:
        logger.error(f"Lỗi gửi Telegram: {e}")
    return None

def edit_telegram_message(message_id: int, text: str, reply_markup=None):
    """Cập nhật nội dung tin nhắn realtime trên Telegram theo message_id (Kiểu MunBot Checker)"""
    if not message_id:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.debug(f"Lỗi edit Telegram: {e}")

def create_checker_card_html(total, checked, left, valid, invalid, error, current_mail="", current_status=""):
    """Tạo format HTML Card chuẩn checker của MunBot"""
    return f"""<b>👻 MunBot Email Token Checker Realtime 👽</b>

<b>📊 Tổng số Email:</b> <code>{total} 🛒</code>
<b>⏳ Tiến độ:</b> <code>{checked}/{total}</code> (Còn lại: <code>{left}</code>)

<b>✅ Valid (Token OK):</b> <code>{valid}</code>
<b>❌ Invalid (Token chết/Hết hạn):</b> <code>{invalid}</code>
<b>⚠️ Error (Cần xử lý tay):</b> <code>{error}</code>

<b>🔍 Đang xử lý:</b> <code>{current_mail or 'Đang khởi động...'}</code>
<b>📌 Trạng thái:</b> <i>{current_status or 'Đang quét...'}</i>

<pre>Last updated @ {datetime.now().strftime('%d-%m-%Y %H:%M:%S')}</pre>"""

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

async def run_checker():
    logger.info("🚀 Khởi chạy MunBot Email Token Checker Continuous Subprocess với Realtime Telegram Updates...")
    
    # 1. Đăng nhập C69
    c69 = C69Client("https://cu.c69.us")
    if not c69.login("Admin", "Zxcv@123"):
        logger.error("Không thể đăng nhập C69!")
        return

    # Lấy toàn bộ danh sách email cần check
    url_emails = "https://cu.c69.us/dashboard/api/emails/?limit=1000&ordering=modified"
    try:
        r = c69.session.get(url_emails, timeout=15)
        if r.status_code != 200:
            return
        data = r.json()
        total_count = data.get('count', 7190)
        results = data.get('results', [])
    except Exception as e:
        logger.error(f"Lỗi fetch email: {e}")
        return

    candidates = [
        item for item in results 
        if any(item.get('email', '').lower().endswith(d) for d in ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com'])
    ]

    valid_count = 0
    invalid_count = 0
    error_count = 0
    checked_count = 0
    batch_total = len(candidates)

    # Gửi tin nhắn Telegram mở đầu (Card bắt đầu check)
    msg_card = create_checker_card_html(
        total=total_count,
        checked=0,
        left=batch_total,
        valid=0,
        invalid=0,
        error=0,
        current_mail="Bắt đầu tiến trình",
        current_status="Đang nạp danh sách email từ C69..."
    )
    # Quản lý gửi tin nhắn mới định kỳ mỗi 60s để tránh bị trôi tin nhắn
    last_send_new_msg_time = time.time()
    tg_msg_id = send_telegram_message(msg_card)

    def update_telegram_live(curr_mail, curr_status):
        nonlocal tg_msg_id, last_send_new_msg_time
        now = time.time()
        card_content = create_checker_card_html(
            total=total_count,
            checked=checked_count,
            left=batch_total - checked_count,
            valid=valid_count,
            invalid=invalid_count,
            error=error_count,
            current_mail=curr_mail,
            current_status=curr_status
        )
        
        # Nếu đã qua 60 giây kể từ lần gửi tin nhắn mới -> Gửi tin nhắn Card mới để nổi lên đầu
        if now - last_send_new_msg_time >= 60:
            new_id = send_telegram_message(card_content)
            if new_id:
                tg_msg_id = new_id
                last_send_new_msg_time = now
        else:
            # Ngược lại edit cập nhật trực tiếp tin nhắn hiện tại
            if tg_msg_id:
                edit_telegram_message(tg_msg_id, card_content)

    for item in candidates:
        email = item.get('email')
        email_id = item.get('id')
        password = item.get('password')
        note = item.get('note')
        client_id = item.get('client_id') or "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

        # Cập nhật telegram đang check mail này
        update_telegram_live(email, "Đang test Fast Refresh Token...")

        # A. Test Fast Refresh
        fast_ok, new_ref = await test_fast_refresh(item)
        if fast_ok:
            c69.save_mailbox_results(email_id, new_ref)
            c69.update_email_status(email_id, 0)
            valid_count += 1
            checked_count += 1
            logger.info(f"✅ [VALID] {email}")
            update_telegram_live(email, "✅ Token hợp lệ (Fast Refreshed)")
            continue

        # B. Không có password -> Báo Error / Cần xử lý tay
        if not password:
            error_count += 1
            checked_count += 1
            c69.update_email_status(email_id, 3)
            logger.warning(f"⚠️ [NO PASS] {email} -> Status 3")
            update_telegram_live(email, "⚠️ Không có pass (Gán status=3)")
            continue

        # C. Token chết -> Đang thử cấp lại
        invalid_count += 1
        update_telegram_live(email, "Token chết! Đang mở browser auto-login & cấp token...")

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
                logger.info(f"🎉 [RECOVERED TO VALID] Đã cấp token mới cho {email}!")
                c69.update_email_status(email_id, 0)
                valid_count += 1
                invalid_count -= 1
            else:
                error_count += 1
                c69.update_email_status(email_id, 3)
        except Exception as e_b:
            logger.error(f"Lỗi browser cho {email}: {e_b}")
            error_count += 1
            c69.update_email_status(email_id, 3)
        finally:
            checked_count += 1
            try:
                await manager.close()
            except Exception:
                pass

        # Cập nhật kết quả sau mỗi email
        update_telegram_live(email, "Đã xong lượt kiểm tra email này.")
        await asyncio.sleep(2)

    # Tổng kết cuối batch
    final_card = create_checker_card_html(
        total=total_count,
        checked=checked_count,
        left=0,
        valid=valid_count,
        invalid=invalid_count,
        error=error_count,
        current_mail="---",
        current_status="🎉 Hoàn tất batch kiểm tra & gia hạn token!"
    )
    edit_telegram_message(tg_msg_id, final_card)

if __name__ == "__main__":
    asyncio.run(run_checker())
