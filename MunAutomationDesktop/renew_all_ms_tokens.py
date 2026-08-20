import os, sys, asyncio, logging, json, requests, random, time
sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from tiktok_reg_automation import auto_login_microsoft_and_get_token, C69Client

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('/root/Workspace/Python/QHTDautomation/MunAutomationDesktop/renew_tokens.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

STATUS_FILE = '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop/renew_status.json'

def update_progress(total, processed, success, failed, skipped, current_email, current_step):
    data = {
        "total": total,
        "processed": processed,
        "success": success,
        "failed": failed,
        "skipped": skipped,
        "current_email": current_email,
        "current_step": current_step,
        "last_updated": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass

async def test_fast_refresh(email_item):
    """Thử refresh token qua API trước, nếu được thì đỡ phải bật browser"""
    email = email_item['email']
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

async def run_worker():
    logger.info("🚀 KHỞI ĐỘNG TIẾN TRÌNH RENEW MICROSOFT OAUTH2 TOKENS")
    
    # 1. Login C69
    c69 = C69Client("https://cu.c69.us")
    if not c69.login("Admin", "Zxcv@123"):
        logger.error("❌ Không thể đăng nhập vào C69!")
        return

    # 2. Tải danh sách proxy 500
    proxies = []
    try:
        r = requests.get("https://cu.c69.us/500", timeout=10)
        if r.status_code == 200:
            proxies = [l.strip() for l in r.text.strip().split('\n') if l.strip()]
            logger.info(f"✅ Đã tải {len(proxies)} proxies từ https://cu.c69.us/500")
    except Exception as e:
        logger.warning(f"Không thể tải proxy từ /500: {e}")

    # 3. Lấy toàn bộ danh sách Hotmail/Outlook từ DB C69
    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect('167.233.89.198', username='root', password='fJU9JtkbELfi', timeout=15)

    script = """
import os, django, json
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'storagon.settings')
django.setup()
from telegram_bot.models import AccountsEmails
from django.db.models import Q

ms_emails = AccountsEmails.objects.filter(
    Q(email__icontains='@hotmail') | Q(email__icontains='@outlook')
).exclude(status=2).order_by('id')

items = list(ms_emails.values('id', 'email', 'password', 'note', 'refresh_token', 'client_id', 'status'))
print(json.dumps(items))
"""
    stdin, stdout, stderr = ssh.exec_command(f'docker exec -i storagon-storagon-1 python -c "{script}"')
    raw_data = stdout.read().decode()
    ssh.close()
    
    try:
        all_emails = json.loads(raw_data)
        logger.info(f"📋 Đã lấy được {len(all_emails)} email Hotmail/Outlook cần kiểm tra.")
    except Exception as e:
        logger.error(f"Lỗi parse dữ liệu email từ DB: {e}")
        return

    total = len(all_emails)
    processed = 0
    success = 0
    failed = 0
    skipped = 0

    update_progress(total, processed, success, failed, skipped, "", "Đang chuẩn bị...")

    manager = NodriverBrowserManager()

    for idx, item in enumerate(all_emails):
        processed = idx + 1
        email = item['email']
        email_id = item['id']
        password = item['password']
        note = item['note']
        client_id = item.get('client_id') or "9e5f94bc-e8a4-4e73-b8be-63364c29d753"

        logger.info(f"\n=======================================================")
        logger.info(f"[{processed}/{total}] Đang xử lý: {email} (ID: {email_id})")
        update_progress(total, processed, success, failed, skipped, email, "Kiểm tra fast-refresh API...")

        # Bước 1: Thử Fast Refresh qua API nếu đang có token
        fast_ok, new_ref = await test_fast_refresh(item)
        if fast_ok:
            logger.info(f"⚡ Fast Refresh thành công qua API cho {email}!")
            c69.save_mailbox_results(email_id, new_ref)
            c69.update_email_status(email_id, 0) # 0: Normal / Sống tốt
            success += 1
            update_progress(total, processed, success, failed, skipped, email, "Fast Refresh thành công")
            continue

        # Bước 2: Nếu token hết hạn hoặc chưa có token -> Mở Trình duyệt Anti-Detect giải challenge
        if not password:
            logger.warning(f"⚠️ Email {email} không có password trên DB! Bỏ qua.")
            c69.update_email_status(email_id, 3) # 3: Cần kiểm tra
            skipped += 1
            update_progress(total, processed, success, failed, skipped, email, "Thiếu password trên DB")
            continue

        update_progress(total, processed, success, failed, skipped, email, "Mở trình duyệt tự động login & cấp token...")
        
        # Chọn random proxy từ pool 500
        proxy_str = random.choice(proxies) if proxies else ""
        profile = manager.profile_manager.create_random_profile(os_type="Window", socks5=proxy_str)

        browser = None
        tab = None
        try:
            browser, tab = await manager.start(
                profile_config=profile,
                proxy_string=proxy_str,
                proxy_type="socks5" if proxy_str else "http",
                headless=True
            )
            if not tab:
                logger.error(f"❌ Không thể mở browser cho {email}")
                failed += 1
                update_progress(total, processed, success, failed, skipped, email, "Lỗi mở trình duyệt")
                continue

            # Chạy luồng tự động đăng nhập và lấy mã Token
            res_token = await auto_login_microsoft_and_get_token(
                browser=browser,
                email=email,
                password=password,
                note_field=note,
                client_id=client_id,
                email_id=email_id,
                c69_client=c69
            )

            if res_token:
                logger.info(f"🎉 Tự động cấp Token mới thành công cho {email}!")
                c69.update_email_status(email_id, 0) # 0: Normal
                success += 1
                update_progress(total, processed, success, failed, skipped, email, "Cấp Token mới thành công")
            else:
                logger.warning(f"❌ Không thể lấy token cho {email}")
                failed += 1
                update_progress(total, processed, success, failed, skipped, email, "Thất bại khi lấy token")

        except Exception as e_proc:
            logger.error(f"Lỗi ngoại lệ khi xử lý {email}: {e_proc}")
            failed += 1
            update_progress(total, processed, success, failed, skipped, email, f"Lỗi: {e_proc}")
        finally:
            if browser:
                try:
                    await manager.close()
                except Exception:
                    pass

        await asyncio.sleep(2)

    logger.info("\n🏁 HOÀN TẤT TOÀN BỘ TIẾN TRÌNH RENEW TOKENS!")
    update_progress(total, processed, success, failed, skipped, "", "Đã hoàn thành toàn bộ")

if __name__ == "__main__":
    asyncio.run(run_worker())
