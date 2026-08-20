import os, sys, asyncio, logging, json, requests, random, time, re
from datetime import datetime

sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from cdp_oauth_engine import auto_login_microsoft_and_get_token_cdp
from tiktok_reg_automation import C69Client, TempMailFviainboxes

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/root/Workspace/Python/QHTDautomation/MunAutomationDesktop/renew_tokens.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Telegram Bot Token và Chat ID của Tony
def get_telegram_bot_token():
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
            return r.json().get("result", {}).get("message_id")
        else:
            logger.error(f"Lỗi gửi tin nhắn Telegram ({r.status_code}): {r.text}")
    except Exception as e:
        logger.error(f"Lỗi kết nối Telegram sendMessage: {e}")
    return None

def edit_telegram_message(message_id: int, text: str, reply_markup=None):
    """Edit nội dung tin nhắn Telegram đã gửi để nhảy số realtime"""
    if not message_id:
        return None
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
        r = requests.post(url, json=payload, timeout=8)
        if r.status_code == 200:
            return r.json().get("result", {}).get("message_id")
    except Exception:
        pass
    return None

def create_checker_card_html(total, checked, left, valid, invalid, error, current_mail="", current_status=""):
    """Format tin nhắn HTML Card phong cách MunBot Checker"""
    time_str = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    html = f"""
<b>👻 MunBot Email Token Checker AIO 👽</b>

<b>Total:</b> <code>{total}</code> 🛒
<b>Checked:</b> <code>{checked}</code> | <b>Left:</b> <code>{left}</code>
<b>Valid (Sống / Đã cấp lại):</b> <code>{valid}</code> 🟢
<b>Invalid (Token chết / Đang lấy):</b> <code>{invalid}</code> 🔴
<b>Error (Lỗi / Cần xử lý tay):</b> <code>{error}</code> ⚠️

<b>Current:</b> <code>{current_mail}</code>
<b>Status:</b> <i>{current_status}</i>

<pre>System: C69 Email Hub | Updated @{time_str}</pre>
"""
    return html.strip()

async def test_fast_refresh(email_item):
    """Thử refresh token qua API trước, nếu được thì đỡ phải bật browser"""
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
    logger.info("🚀 Khởi chạy MunBot Email Token Checker Continuous Subprocess quét TOÀN BỘ database...")
    
    # 1. Đăng nhập C69
    c69 = C69Client("https://cu.c69.us")
    if not c69.login("Admin", "Zxcv@123"):
        logger.error("Không thể đăng nhập C69!")
        return

    valid_count = 0
    invalid_count = 0
    error_count = 0
    checked_count = 0
    total_count = 7190

    # Khởi tạo Card ban đầu
    msg_card = create_checker_card_html(
        total=total_count,
        checked=0,
        left=total_count,
        valid=0,
        invalid=0,
        error=0,
        current_mail="Bắt đầu tiến trình",
        current_status="Đang nạp danh sách email từ C69..."
    )
    last_send_new_msg_time = time.time()
    tg_msg_id = send_telegram_message(msg_card)

    def update_telegram_live(curr_mail, curr_status):
        nonlocal tg_msg_id, last_send_new_msg_time
        now = time.time()
        card_content = create_checker_card_html(
            total=total_count,
            checked=checked_count,
            left=total_count - checked_count,
            valid=valid_count,
            invalid=invalid_count,
            error=error_count,
            current_mail=curr_mail,
            current_status=curr_status
        )
        
        # Gửi card mới mỗi 60s để chống trôi tin nhắn
        if now - last_send_new_msg_time >= 60:
            new_id = send_telegram_message(card_content)
            if new_id:
                tg_msg_id = new_id
                last_send_new_msg_time = now
        else:
            if tg_msg_id:
                edit_telegram_message(tg_msg_id, card_content)

    page = 1
    page_size = 100

    while True:
        # Lấy các email có status=0 (hoặc chưa đánh dấu cần check tay status=3) để quét
        url_emails = f"https://cu.c69.us/dashboard/api/emails/?page={page}&page_size={page_size}&status=0&ordering=modified"
        try:
            r = c69.session.get(url_emails, timeout=15)
            if r.status_code != 200:
                logger.error(f"Fetch page {page} trả về status {r.status_code}. Kết thúc.")
                break
            data = r.json()
            total_count = data.get('count', total_count)
            results = data.get('results', [])
            if not results:
                logger.info(f"Đã duyệt hết các trang (Trang cuối: {page-1}).")
                break
        except Exception as e:
            logger.error(f"Lỗi fetch page {page}: {e}")
            break

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

            update_telegram_live(email, "Đang test Fast Refresh Token...")

            # A. Test Fast Refresh: Nếu token còn sống -> Update status=0, note="Token sống", và bỏ qua không mở browser
            if item.get('refresh_token'):
                fast_ok, new_ref = await test_fast_refresh(item)
                if fast_ok:
                    c69.save_mailbox_results(email_id, new_ref)
                    c69.update_email_status(email_id, 0, "Token sống (Fast Refreshed)")
                    valid_count += 1
                    checked_count += 1
                    logger.info(f"✅ [VALID - ĐÃ CÓ TOKEN SỐNG] {email}")
                    update_telegram_live(email, "✅ Đã có Token sống (Bỏ qua)")
                    continue
                else:
                    logger.info(f"🔄 [TOKEN HẾT HẠN] {email} -> Cần cấp lại qua trình duyệt")
            else:
                logger.info(f"⚠️ [CHƯA CÓ TOKEN] {email} -> Cần cấp mới qua trình duyệt")

            # B. Không có password -> Báo Error / Cần xử lý tay
            if not password:
                error_count += 1
                checked_count += 1
                c69.update_email_status(email_id, 3, "Không có password trong DB")
                logger.warning(f"⚠️ [NO PASS] {email} -> Status 3")
                update_telegram_live(email, "⚠️ Không có pass (Gán status=3)")
                continue

            # C. Token chết -> Đang thử cấp lại qua trình duyệt
            invalid_count += 1
            update_telegram_live(email, "Token chết! Đang mở browser auto-login & cấp token...")

            try:
                r_p = requests.get("https://cu.c69.us/500", timeout=8)
                proxies = [p.strip() for p in r_p.text.strip().split("\n") if p.strip()]
                proxy_raw = random.choice(proxies) if proxies else ""
            except Exception:
                proxy_raw = ""

            proxy_str = ""
            proxy_u = ""
            proxy_p = ""
            if proxy_raw:
                parts = proxy_raw.split(":")
                if len(parts) >= 4:
                    proxy_str = f"{parts[0]}:{parts[1]}"
                    proxy_u = parts[2]
                    proxy_p = parts[3]
                else:
                    proxy_str = proxy_raw

            manager = NodriverBrowserManager()
            profile = manager.profile_manager.create_random_profile(
                os_type="Window", 
                socks5=proxy_str,
                proxy_username=proxy_u,
                proxy_password=proxy_p
            )
            try:
                browser, tab = await manager.start(
                    profile_config=profile,
                    proxy_string=proxy_str,
                    proxy_type="socks5" if proxy_str else "http",
                    proxy_username=proxy_u,
                    proxy_password=proxy_p,
                    headless=False
                )
                res_token = await asyncio.wait_for(
                    auto_login_microsoft_and_get_token_cdp(
                        browser=browser,
                        email=email,
                        password=password,
                        note_field=note,
                        client_id=client_id,
                        email_id=email_id,
                        c69_client=c69,
                        update_step_callback=update_telegram_live
                    ),
                    timeout=240
                )
                if res_token:
                    valid_count += 1
                    invalid_count -= 1
                    c69.update_email_status(email_id, 0)
                    logger.info(f"🎉 [TOKEN CẤP MỚI THÀNH CÔNG] {email}")
                    update_telegram_live(email, "🎉 Đã cấp lại Token OAuth2 thành công!")
                else:
                    error_count += 1
                    invalid_count -= 1
                    c69.update_email_status(email_id, 3, "Không hoàn tất cấp Token qua Browser")
                    logger.warning(f"⚠️ [CẦN CHECK TAY] {email}")
                    update_telegram_live(email, "⚠️ Cần check tay (Gán status=3)")
            except asyncio.TimeoutError:
                error_count += 1
                invalid_count -= 1
                c69.update_email_status(email_id, 3, "Quá thời gian chờ (Timeout 90s)")
                logger.warning(f"⏳ [TIMEOUT 90s] {email} -> Status 3")
                update_telegram_live(email, "⏳ Quá hạn 90s (Gán status=3)")
            except Exception as e_proc:
                error_count += 1
                invalid_count -= 1
                c69.update_email_status(email_id, 3, f"Lỗi exception: {str(e_proc)[:100]}")
                logger.error(f"❌ [LỖI] {email}: {e_proc}")
                update_telegram_live(email, f"❌ Lỗi: {e_proc} (Gán status=3)")
            finally:
                checked_count += 1
                try:
                    await manager.close()
                except Exception:
                    pass

            update_telegram_live(email, "Đã xong lượt kiểm tra email này.")
            await asyncio.sleep(1)

        page += 1

    # Hoàn tất toàn bộ
    final_card = create_checker_card_html(
        total=total_count,
        checked=checked_count,
        left=0,
        valid=valid_count,
        invalid=invalid_count,
        error=error_count,
        current_mail="---",
        current_status="🎉 Hoàn tất kiểm tra & gia hạn toàn bộ database!"
    )
    send_telegram_message(final_card)

if __name__ == "__main__":
    asyncio.run(run_checker())
