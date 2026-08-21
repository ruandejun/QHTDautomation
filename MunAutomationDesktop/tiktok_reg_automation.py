import asyncio
import os
import sys
import random
import string
import re
import json
import logging
import urllib.request
import imaplib
import email
from email.header import decode_header
from typing import Optional, Dict, Any, Tuple, List

# Cấu hình UTF-8 cho console Windows
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

# Đảm bảo import được mun_anti_browser
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import nodriver
    from mun_anti_browser.browser_manager import NodriverBrowserManager
    import requests
    import pyotp
except ImportError as e:
    print(f"Lỗi: Không thể import thư viện cần thiết: {e}")
    print("Vui lòng chạy: ..\\.venv\\Scripts\\pip install requests pyotp nodriver")
    sys.exit(1)

# Cấu hình Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("TikTokRegAuto")

# ============================================================================
# UTILITIES
# ============================================================================

def generate_random_string(length: int = 12, only_letters: bool = False) -> str:
    """Sinh chuỗi ngẫu nhiên cho mật khẩu hoặc username."""
    if only_letters:
        chars = string.ascii_letters
    else:
        chars = string.ascii_letters + string.digits + "!@#$%"
    return "".join(random.choice(chars) for _ in range(length))


# ============================================================================
# C69 API INTEGRATION
# ============================================================================

class C69Client:
    """Client giao tiếp với hệ thống C69 backend (https://cu.c69.us)"""

    def __init__(self, base_url: str = "https://cu.c69.us"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.logged_in = False
        
    def login(self, email_addr: str, password: str) -> bool:
        """Đăng nhập vào hệ thống C69 bằng Cookie Session"""
        login_url = f"{self.base_url}/dashboard/login/"
        try:
            # Lấy CSRF token trước
            self.session.get(self.base_url, timeout=10)
            headers = {
                "Content-Type": "application/json",
                "Referer": login_url
            }
            # Gửi dữ liệu đăng nhập
            payload = {"username": email_addr, "password": password}
            r = self.session.post(login_url, json=payload, headers=headers, timeout=15)
            if r.status_code == 200 and r.json().get("success"):
                logger.info("🎉 Đăng nhập vào hệ thống C69 thành công!")
                self.logged_in = True
                return True
            else:
                logger.error(f"Đăng nhập C69 thất bại: {r.text}")
        except Exception as e:
            logger.error(f"Lỗi khi kết nối tới C69 để đăng nhập: {e}")
        return False

    def get_active_account(self, account_type: str) -> Optional[Dict[str, Any]]:
        """Lấy một tài khoản chưa sử dụng (status = 0) từ C69"""
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể lấy tài khoản.")
            return None
        url = f"{self.base_url}/dashboard/api/accounts/get-active-account/?type={account_type}"
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                resp = r.json()
                if resp.get("success"):
                    account_data = resp.get("account_data")
                    logger.info(f"Lấy thành công tài khoản {account_type} từ C69: {account_data.get('email')}")
                    return account_data
                else:
                    logger.warning(f"Không có tài khoản {account_type} hoạt động: {resp.get('message')}")
            else:
                logger.error(f"Lỗi API lấy tài khoản từ C69 (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi kết nối API C69: {e}")
        return None

    def get_random_valid_recovery_mailbox(self, exclude_email: str = "") -> Optional[Dict[str, Any]]:
        """Lấy ngẫu nhiên 1 email Microsoft đang có token sống từ pool trên C69 để làm email khôi phục"""
        if not self.logged_in:
            return None
        # Lấy trang ngẫu nhiên từ danh sách email có status = 0
        rand_page = random.randint(1, 20)
        url = f"{self.base_url}/dashboard/api/emails/?status=0&page={rand_page}&page_size=20"
        try:
            r = self.session.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                # Lọc các email Microsoft khác với email đang xử lý và có token
                valid_candidates = [
                    item for item in results
                    if item.get("email") and item.get("email") != exclude_email
                    and item.get("refresh_token")
                    and any(item.get("email", "").lower().endswith(d) for d in ['@hotmail.com', '@outlook.com', '@live.com', '@msn.com'])
                ]
                if valid_candidates:
                    # Test thử nhanh 1 candidate xem token có đọc được mail qua Graph API không
                    random.shuffle(valid_candidates)
                    for cand in valid_candidates:
                        # Test refresh token
                        c_tok = cand.get("refresh_token")
                        c_cid = cand.get("client_id") or "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
                        try:
                            r_t = requests.post("https://login.live.com/oauth20_token.srf", data={
                                "client_id": c_cid,
                                "grant_type": "refresh_token",
                                "refresh_token": c_tok,
                                "scope": "https://graph.microsoft.com/Mail.Read offline_access"
                            }, timeout=5)
                            if r_t.status_code == 200 and "access_token" in r_t.json():
                                logger.info(f"🎲 Đã chọn và xác thực hòm thư khôi phục C69 sống 100%: {cand.get('email')} (ID: {cand.get('id')})")
                                return cand
                        except Exception:
                            continue
        except Exception as e:
            logger.error(f"Lỗi khi lấy random recovery mailbox từ C69: {e}")
        return None

    def update_recovery_email_only(self, email_id: int, recovery_email: str) -> bool:
        """Lưu ngay email khôi phục lên C69 DB ngay khi xác thực / điền form thành công mà không cần chờ đến bước OAuth cuối"""
        if not self.logged_in or not email_id or not recovery_email:
            return False
        url = f"{self.base_url}/dashboard/api/emails/{email_id}/"
        payload: Dict[str, Any] = {"recovery_email": recovery_email}
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
        try:
            r = self.session.patch(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201, 204):
                logger.info(f"💾 [AUTO-SAVE] Đã lưu ngay email khôi phục ({recovery_email}) vào DB C69 cho email ID {email_id}!")
                return True
        except Exception as e:
            logger.error(f"Lỗi auto-save recovery email: {e}")
        return False
    def update_recovery_email_and_token(self, email_id: int, refresh_token: Optional[str] = None, recovery_email: Optional[str] = None) -> bool:
        """Cập nhật đồng thời refresh_token, recovery_email và status = 0"""
        if not self.logged_in:
            return False
        url = f"{self.base_url}/dashboard/api/emails/{email_id}/"
        payload: Dict[str, Any] = {"status": 0}
        if refresh_token:
            payload["refresh_token"] = refresh_token
        if recovery_email:
            payload["recovery_email"] = recovery_email
            
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
            
        try:
            r = self.session.patch(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201, 204):
                logger.info(f"✅ Đã lưu refresh_token & recovery_email ({recovery_email}) cho email ID {email_id} trên C69 thành công!")
                return True
        except Exception as e:
            logger.error(f"Lỗi update recovery email: {e}")
        return False

    def update_2fa_key(self, account_id: int, two_factor_key: str) -> bool:
        """Cập nhật khóa 2FA cho tài khoản đang tồn tại trên C69"""
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể cập nhật.")
            return False
        url = f"{self.base_url}/dashboard/api/accounts/{account_id}/"
        payload = {"two_factor_auth": two_factor_key}
        # Thêm header CSRF token nếu cần thiết
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
            
        try:
            r = self.session.patch(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201, 204):
                logger.info(f"Đã cập nhật khóa 2FA cho tài khoản ID {account_id} trên C69 thành công!")
                return True
            else:
                logger.error(f"Lỗi cập nhật tài khoản trên C69 (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi cập nhật C69: {e}")
        return False

    def read_mailbox(self, email_id: int, email_addr: str = "Email") -> Optional[Dict[str, Any]]:
        """Gọi API backend C69 để đọc hộp thư theo email_id (IMAP cho Gmail, Microsoft Graph OAuth2
        cho Hotmail/Outlook - Microsoft đã tắt Basic Auth IMAP nên không thể đọc trực tiếp bằng mật khẩu)."""
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể đọc hộp thư.")
            return None
        url = f"{self.base_url}/dashboard/api/emails/{email_id}/read-mailbox/"
        try:
            r = self.session.get(url, timeout=20)
            if r.status_code == 200:
                resp = r.json()
                if resp.get("success"):
                    return resp
                else:
                    logger.warning(f"❌ [{email_addr}] Đọc hộp thư C69 thất bại: {resp.get('message')}")
            else:
                logger.error(f"❌ [{email_addr}] Lỗi API đọc hộp thư C69 (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"❌ [{email_addr}] Lỗi kết nối API đọc hộp thư C69: {e}")
        return None

    def save_mailbox_results(self, email_id: int, refresh_token: str = None) -> bool:
        """Lưu refresh token mới (hoặc rotated) lên server C69"""
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể cập nhật refresh token.")
            return False
        url = f"{self.base_url}/dashboard/api/emails/{email_id}/save-mailbox-results/"
        payload = {}
        if refresh_token:
            payload["refresh_token"] = refresh_token
            
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
            
        try:
            r = self.session.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201):
                logger.info(f"Đã lưu refresh token mới cho email ID {email_id} lên C69 thành công!")
                return True
            else:
                logger.error(f"Lỗi lưu refresh token lên C69 (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi kết nối API C69 save-mailbox-results: {e}")
        return False

    def update_email_status(self, email_id: int, status: int, note_reason: str = "") -> bool:
        """Cập nhật trạng thái (status) và lý do chi tiết (note) cho email trong DB C69"""
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể cập nhật trạng thái email.")
            return False
        url = f"{self.base_url}/dashboard/api/emails/{email_id}/"
        payload: Dict[str, Any] = {"status": status}
        if note_reason:
            payload["note"] = note_reason
        
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
            
        try:
            r = self.session.patch(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201, 204):
                logger.info(f"Đã cập nhật email ID {email_id} -> Status {status} (Lý do: {note_reason or 'None'}) thành công!")
                return True
            else:
                logger.error(f"Lỗi cập nhật trạng thái email trên C69 (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi cập nhật trạng thái email C69: {e}")
        return False

    def add_tiktok_account(self, email_addr: str, password: str, two_factor_key: str,
                           profile_id: str = "none",
                           accounts_emails_id: Optional[int] = None) -> bool:
        """Lưu tài khoản TikTok mới tạo kèm mã 2FA lên C69.
        accounts_emails_id (tuỳ chọn): ID của AccountsEmails nguồn để backend tự động link FK.
        """
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể thêm tài khoản.")
            return False
        url = f"{self.base_url}/dashboard/api/accounts/add-manual/"
        payload = {
            "email": email_addr,
            "password": password,
            "type": "Tiktok",
            "two_factor_auth": two_factor_key,
            "profile_id": profile_id,
            "note": "Tự động đăng ký qua MunAutomation",
        }
        if accounts_emails_id:
            payload["accounts_emails_id"] = accounts_emails_id

        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken

        try:
            r = self.session.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201):
                resp = r.json()
                account_id = resp.get("account_id")
                logger.info(f"🎉 Đã lưu tài khoản TikTok mới đăng ký lên C69 thành công! (account_id={account_id})")
                return True
            else:
                logger.error(f"Lỗi lưu tài khoản TikTok lên C69 (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi lưu tài khoản TikTok: {e}")
        return False

    def get_unused_email(self, email_type: str = "hotmail") -> Optional[Dict[str, Any]]:
        """Lấy một email chưa dùng (để đăng ký) từ AccountsEmails trên C69.
        Sử dụng endpoint /api/emails/get-unused-email/?type=<email_type>.
        Trả về dict có các key: id, email, password, refresh_token, type
        """
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể lấy email.")
            return None
        url = f"{self.base_url}/dashboard/api/emails/get-unused-email/?type={email_type}"
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                resp = r.json()
                if resp.get("success"):
                    email_data = resp.get("email_data")
                    logger.info(f"Lấy thành công email {email_type} chưa dùng từ C69: {email_data.get('email')}")
                    return email_data
                else:
                    logger.warning(f"Không có email {email_type} chưa dùng: {resp.get('message')}")
            else:
                logger.error(f"Lỗi API get-unused-email (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi kết nối API C69 get-unused-email: {e}")
        return None

    def mark_email_as_used(self, email_id: int) -> bool:
        """Cập nhật trạng thái email thành đã dùng (status=1) sau khi signup thành công."""
        if not self.logged_in:
            return False
        url = f"{self.base_url}/dashboard/api/emails/{email_id}/"
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
        try:
            r = self.session.patch(url, json={"status": 1}, headers=headers, timeout=10)
            if r.status_code in (200, 201, 204):
                logger.info(f"Cập nhật email_id={email_id} thành 'status=1 (Đã dùng)' trên C69.")
                return True
            else:
                logger.warning(f"Không được cập nhật trạng thái email (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.warning(f"Lỗi cập nhật trạng thái email: {e}")
        return False

    # ─────────────────────────────────────────────────────────────────────
    # TIKTOK NURTURE METHODS
    # ─────────────────────────────────────────────────────────────────────

    def get_tiktok_accounts(self, status: Optional[int] = None,
                            page_size: int = 100) -> List[Dict[str, Any]]:
        """Lấy danh sách tài khoản TikTok từ C69 (có thể filter theo status)."""
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể lấy danh sách TikTok accounts.")
            return []
        url = f"{self.base_url}/dashboard/api/accounts/?type=tiktok&page_size={page_size}"
        if status is not None:
            url += f"&status={status}"
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                resp = r.json()
                results = resp.get("results", resp) if isinstance(resp, dict) else resp
                logger.info(f"Lấy được {len(results)} TikTok accounts từ C69.")
                return results if isinstance(results, list) else []
            else:
                logger.error(f"Lỗi API get TikTok accounts (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi kết nối API C69 get_tiktok_accounts: {e}")
        return []

    def get_nurture_queue(self, limit: int = 10, status: int = 0) -> List[Dict[str, Any]]:
        """Lấy danh sách tài khoản TikTok cần nuôi, ưu tiên chưa nuôi lâu nhất.

        Endpoint: GET /dashboard/api/accounts/get-nurture-queue/?limit=N&status=0
        """
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể lấy nurture queue.")
            return []
        url = f"{self.base_url}/dashboard/api/accounts/get-nurture-queue/?limit={limit}&status={status}"
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                resp = r.json()
                if resp.get("success"):
                    accounts = resp.get("accounts", [])
                    logger.info(f"Lấy được {len(accounts)} TikTok accounts từ nurture queue C69.")
                    return accounts
                else:
                    logger.warning(f"Không lấy được nurture queue: {resp.get('message', '')}")
            else:
                logger.error(f"Lỗi API get-nurture-queue (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi kết nối API C69 get_nurture_queue: {e}")
        return []

    def log_nurture_session(self, account_id: int, stats: Dict[str, Any]) -> bool:
        """Ghi lại kết quả phiên nuôi TikTok lên C69.

        Endpoint: POST /dashboard/api/accounts/{id}/log-nurture/

        Args:
            account_id: ID của AccountsCreated trên C69
            stats: {videos_watched, likes, comments, follows, session_duration_secs, success, error}
        """
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể ghi log nuôi.")
            return False
        url = f"{self.base_url}/dashboard/api/accounts/{account_id}/log-nurture/"
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
        try:
            r = self.session.post(url, json=stats, headers=headers, timeout=15)
            if r.status_code in (200, 201):
                resp = r.json()
                if resp.get("success"):
                    s = resp.get("stats", {})
                    logger.info(
                        f"✅ Đã ghi log nuôi account_id={account_id}: "
                        f"sessions={s.get('nurture_sessions')}, "
                        f"total_videos={s.get('videos_watched_total')}"
                    )
                    return True
                else:
                    logger.warning(f"Ghi log nuôi thất bại: {resp}")
            else:
                logger.error(f"Lỗi API log-nurture (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi kết nối API C69 log_nurture_session: {e}")
        return False

    def update_account_cookies(self, account_id: int, cookies: str,
                               tiktok_username: str = "") -> bool:
        """Lưu cookies/session mới lên AccountsCreated sau phiên nuôi.

        Endpoint: POST /dashboard/api/accounts/{id}/update-cookies/
        """
        if not self.logged_in:
            logger.error("Chưa đăng nhập C69. Không thể cập nhật cookies.")
            return False
        url = f"{self.base_url}/dashboard/api/accounts/{account_id}/update-cookies/"
        csrftoken = self.session.cookies.get('csrftoken')
        headers = {"Content-Type": "application/json"}
        if csrftoken:
            headers["X-CSRFToken"] = csrftoken
        payload: Dict[str, Any] = {"cookies": cookies}
        if tiktok_username:
            payload["username"] = tiktok_username
        try:
            r = self.session.post(url, json=payload, headers=headers, timeout=15)
            if r.status_code in (200, 201):
                resp = r.json()
                if resp.get("success"):
                    logger.info(f"✅ Đã cập nhật cookies cho account_id={account_id}.")
                    return True
                else:
                    logger.warning(f"Cập nhật cookies thất bại: {resp}")
            else:
                logger.error(f"Lỗi API update-cookies (Status {r.status_code}): {r.text}")
        except Exception as e:
            logger.error(f"Lỗi kết nối API C69 update_account_cookies: {e}")
        return False


# ============================================================================
# EMAIL PROVIDER (TEMP-MAIL API & IMAP)
# ============================================================================


class TempMailFviainboxes:
    """Xử lý email tạm thời qua dịch vụ Fviainboxes.com (API free /messages)"""
    
    def __init__(self, username: str, domain: str = "fviainboxes.com"):
        clean_user = username.strip().lower()
        if "@" in clean_user:
            parts = clean_user.split("@", 1)
            clean_user = parts[0]
            if not domain or domain == "fviainboxes.com":
                domain = parts[1]
        self.username = clean_user
        self.domain = domain
        self.email_address = f"{self.username}@{self.domain}"
        
    async def get_microsoft_otp(self, timeout_secs: int = 150) -> Optional[str]:
        """Polling hộp thư fviainboxes.com để tìm mã OTP xác minh từ Microsoft với cơ chế retry và timeout linh hoạt."""
        logger.info(f"Đang chờ mã OTP Microsoft gửi đến {self.email_address} qua fviainboxes.com (Timeout: {timeout_secs}s)...")
        start_time = asyncio.get_event_loop().time()
        
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "*/*"
        })
        
        while asyncio.get_event_loop().time() - start_time < timeout_secs:
            url = f"https://fviainboxes.com/messages?username={urllib.parse.quote(self.username)}&domain={urllib.parse.quote(self.domain)}"
            try:
                loop = asyncio.get_event_loop()
                r = await loop.run_in_executor(None, lambda: session.get(url, timeout=15))
                if r.status_code == 200:
                    data = r.json()
                    messages = data.get("result", [])
                    # Sắp xếp tin nhắn mới nhất lên đầu nếu có createdAt
                    messages = sorted(messages, key=lambda m: m.get("createdAt", 0), reverse=True)
                    
                    for msg in messages:
                        subject = str(msg.get("subject", "")).lower()
                        sender = str(msg.get("from", "")).lower()
                        if "microsoft" in subject or "microsoft" in sender or "code" in subject or "verification" in subject or "security" in subject or "unusual" in subject:
                            msg_id = msg.get("id")
                            msg_url = f"https://fviainboxes.com/message?username={urllib.parse.quote(self.username)}&domain={urllib.parse.quote(self.domain)}&id={msg_id}"
                            r_detail = await loop.run_in_executor(None, lambda: session.get(msg_url, timeout=15))
                            if r_detail.status_code == 200:
                                raw_text = r_detail.text
                                text = raw_text.strip()
                                try:
                                    if text.startswith('"') and text.endswith('"'):
                                        text = json.loads(text)
                                    elif isinstance(text, dict):
                                        text = str(text)
                                except Exception:
                                    pass
                                    
                                text = text.replace(r'\u003c', '<').replace(r'\u003e', '>').replace(r'\"', '"').replace(r'\/', '/')
                                
                                # 1. Bóc từ định dạng text đơn giản mới của Microsoft: Your single-use code is: XXXXXX
                                text_clean_str = text.replace('\\r', '').replace('\\n', ' ')
                                single_use_match = re.search(r'single-use\s+code\s+is:\s*(\d{6,8})', text_clean_str, re.IGNORECASE)
                                if single_use_match:
                                    code = single_use_match.group(1)
                                    logger.info(f"🎉 [FVI-SINGLE-USE] Tìm thấy mã OTP Microsoft: {code}")
                                    return code

                                # 2. Bóc trực tiếp từ HTML pattern chuẩn của Microsoft: Security code: <span...>XXXXXX</span>
                                ms_html_match = re.search(r'Security\s+code:[^<]*<span[^>]*>\s*(\d{6,8})\s*</span>', text, re.IGNORECASE)
                                if ms_html_match:
                                    code = ms_html_match.group(1)
                                    logger.info(f"🎉 [FVI-HTML] Tìm thấy mã OTP Microsoft chuẩn xác: {code}")
                                    return code

                                # 3. Lọc bỏ toàn bộ thẻ HTML và mã màu CSS Hex
                                clean_no_html = re.sub(r'<[^>]+>', ' ', text)
                                clean_no_hex = re.sub(r'#[0-9a-fA-F]{3,8}', ' ', clean_no_html)
                                
                                # 4. Tìm chính xác mã OTP 6-8 số đứng sau "Security code", "single-use code" hoặc "Mã xác nhận"
                                otp_match = re.search(r'(?:single-use\s+code|Security\s+code|mã\s+xác\s+nhận|mã\s+bảo\s+mật|verification\s+code)[^\d]{1,50}(\b\d{6,8}\b)', clean_no_hex, re.IGNORECASE)
                                if not otp_match:
                                    otp_match = re.search(r'\b\d{6,8}\b', clean_no_hex)
                                    
                                if otp_match:
                                    code = otp_match.group(1) if len(otp_match.groups()) > 0 else otp_match.group(0)
                                    logger.info(f"🎉 [FVI-TEXT] Tìm thấy mã OTP Microsoft chuẩn xác: {code}")
                                    return code
            except Exception as e:
                logger.debug(f"Đang polling fviainboxes.com (thử lại sau 3s, lỗi: {e})...")
                
            await asyncio.sleep(3)
            
        logger.warning(f"Không tìm thấy mã OTP Microsoft trên fviainboxes.com ({self.email_address}) sau {timeout_secs}s.")
        return None


class TempMail1SecMail:
    """Xử lý email tạm thời qua API miễn phí 1secmail.com"""
    
    def __init__(self):
        self.email_address = ""
        self.login = ""
        self.domain = ""
        
    def generate_email(self) -> str:
        """Tạo một email ngẫu nhiên mới."""
        url = "https://www.1secmail.com/api/v1/?action=genRandomMailbox&count=1"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as response:
                emails = json.loads(response.read().decode())
                if emails:
                    self.email_address = emails[0]
                    self.login, self.domain = self.email_address.split("@")
                    logger.info(f"Đã sinh email tạm thời: {self.email_address}")
                    return self.email_address
        except Exception as e:
            logger.error(f"Lỗi khi tạo email tạm thời từ 1secmail: {e}")
        return ""

    async def get_otp_code(self, timeout_secs: int = 120) -> Optional[str]:
        """Polling hộp thư để tìm mã OTP xác minh từ TikTok."""
        logger.info(f"Đang chờ mã OTP xác minh gửi đến {self.email_address} (Timeout: {timeout_secs}s)...")
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout_secs:
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={self.login}&domain={self.domain}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    messages = json.loads(response.read().decode())
                    for msg in messages:
                        subject = msg.get("subject", "").lower()
                        sender = msg.get("sender", "").lower()
                        if "tiktok" in subject or "tiktok" in sender or "verification" in subject or "code" in subject:
                            msg_id = msg.get("id")
                            detail_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={self.login}&domain={self.domain}&id={msg_id}"
                            detail_req = urllib.request.Request(detail_url, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(detail_req, timeout=10) as detail_resp:
                                body = json.loads(detail_resp.read().decode())
                                text_content = body.get("textBody", "") + body.get("body", "")
                                otp_match = re.search(r'\b\d{6}\b', text_content)
                                if otp_match:
                                    code = otp_match.group(0)
                                    logger.info(f"Tìm thấy mã OTP TikTok: {code}")
                                    return code
            except Exception as e:
                logger.debug(f"Đang kiểm tra mail (lỗi tạm thời: {e})...")
            
            await asyncio.sleep(5)
            
        logger.warning("Không tìm thấy mã OTP trong khoảng thời gian quy định.")
        return None

    async def get_microsoft_otp(self, timeout_secs: int = 120) -> Optional[str]:
        """Polling hộp thư để tìm mã OTP xác minh từ Microsoft."""
        logger.info(f"Đang chờ mã OTP Microsoft gửi đến {self.email_address} (Timeout: {timeout_secs}s)...")
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout_secs:
            url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={self.login}&domain={self.domain}"
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=10) as response:
                    messages = json.loads(response.read().decode())
                    for msg in messages:
                        subject = msg.get("subject", "").lower()
                        sender = msg.get("sender", "").lower()
                        if "microsoft" in subject or "microsoft" in sender or "code" in subject or "verification" in subject:
                            msg_id = msg.get("id")
                            detail_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={self.login}&domain={self.domain}&id={msg_id}"
                            detail_req = urllib.request.Request(detail_url, headers={"User-Agent": "Mozilla/5.0"})
                            with urllib.request.urlopen(detail_req, timeout=10) as detail_resp:
                                body = json.loads(detail_resp.read().decode())
                                text_content = body.get("textBody", "") + body.get("body", "")
                                otp_match = re.search(r'(?:security\s+code|securitycode|mã\s+bảo\s+mật)[:\s]+(\d{6,8})', text_content, re.IGNORECASE)
                                if not otp_match:
                                    otp_match = re.search(r'(?:code|mã)[:\s]+(\d{6,8})', text_content, re.IGNORECASE)
                                if not otp_match:
                                    otp_match = re.search(r'\b\d{6,8}\b', text_content)
                                    
                                if otp_match:
                                    code = otp_match.group(1) if len(otp_match.groups()) > 0 else otp_match.group(0)
                                    logger.info(f"Tìm thấy mã OTP Microsoft: {code}")
                                    return code
            except Exception as e:
                logger.debug(f"Đang kiểm tra mail (lỗi tạm thời: {e})...")
            
            await asyncio.sleep(5)
            
        logger.warning("Không tìm thấy mã OTP Microsoft trong khoảng thời gian quy định.")
        return None


class IMAPMailBox:
    """Xử lý đọc OTP từ email cá nhân thông qua IMAP"""
    
    def __init__(self, host: str, user: str, password: str):
        self.host = host
        self.user = user
        self.password = password

    async def get_otp_code(self, timeout_secs: int = 120) -> Optional[str]:
        logger.info(f"Đang chờ nhận mail OTP qua IMAP ({self.user})...")
        start_time = asyncio.get_event_loop().time()
        
        while asyncio.get_event_loop().time() - start_time < timeout_secs:
            try:
                loop = asyncio.get_running_loop()
                code = await loop.run_in_executor(None, self._check_imap_mailbox)
                if code:
                    return code
            except Exception as e:
                logger.debug(f"Lỗi kiểm tra IMAP: {e}")
            await asyncio.sleep(8)
        return None

    def _check_imap_mailbox(self) -> Optional[str]:
        mail = imaplib.IMAP4_SSL(self.host)
        mail.login(self.user, self.password)
        mail.select("inbox")
        
        # Tìm thư chưa đọc từ TikTok
        status, messages = mail.search(None, '(UNSEEN)')
        if status == "OK" and messages[0]:
            mail_ids = messages[0].split()
            # Quét các mail chưa đọc từ mới nhất về cũ nhất
            for mail_id in reversed(mail_ids):
                status, data = mail.fetch(mail_id, '(RFC822)')
                if status != "OK":
                    continue
                raw_email = data[0][1]
                msg = email.message_from_bytes(raw_email)
                
                subject = decode_header(msg.get("Subject", ""))[0][0]
                if isinstance(subject, bytes):
                    subject = subject.decode(errors='ignore')
                subject = str(subject).lower()
                
                from_ = msg.get("From", "").lower()
                
                # Check nếu là mail từ TikTok
                if "tiktok" in subject or "tiktok" in from_ or "verification" in subject:
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type in ("text/plain", "text/html"):
                                try:
                                    body += part.get_payload(decode=True).decode(errors='ignore')
                                except Exception:
                                    pass
                    else:
                        body = msg.get_payload(decode=True).decode(errors='ignore')
                    
                    otp_match = re.search(r'\b\d{6}\b', body)
                    if otp_match:
                        mail.store(mail_id, '+FLAGS', '\\Seen')
                        mail.logout()
                        return otp_match.group(0)
                        
        mail.logout()
        return None


class C69MailBox:
    """Đọc OTP qua API backend C69 (/dashboard/api/emails/{id}/read-mailbox/) thay vì IMAP trực tiếp.

    Bắt buộc dùng cho tài khoản Hotmail/Outlook lấy từ C69: Microsoft đã tắt Basic Auth IMAP cho
    các tài khoản Outlook.com/Hotmail thông thường, nên đăng nhập IMAP bằng email+password sẽ luôn
    thất bại. Backend C69 đã xử lý việc này bằng Microsoft Graph API (OAuth2 refresh_token/ROPC),
    nên script chỉ cần gọi lại API đó qua email_id trả về từ get-active-account.
    """

    def __init__(self, c69_client: "C69Client", email_id: int, email_addr: str = "Email"):
        self.c69_client = c69_client
        self.email_id = email_id
        self.email_addr = email_addr

    async def get_otp_code(self, timeout_secs: int = 120) -> Optional[str]:
        logger.info(f"Đang chờ mã OTP qua API đọc hộp thư C69 ({self.email_addr}, email_id={self.email_id}, Timeout: {timeout_secs}s)...")
        loop = asyncio.get_event_loop()
        start_time = loop.time()

        while loop.time() - start_time < timeout_secs:
            result = await loop.run_in_executor(None, self.c69_client.read_mailbox, self.email_id, self.email_addr)
            if result:
                for msg in result.get("emails", []):
                    subject = (msg.get("subject") or "").lower()
                    sender = (msg.get("from") or "").lower()
                    if "tiktok" in subject or "tiktok" in sender:
                        text = f"{msg.get('subject', '')} {msg.get('body', '')}"
                        otp_match = re.search(r'\b\d{6}\b', text)
                        if otp_match:
                            code = otp_match.group(0)
                            logger.info(f"Tìm thấy mã OTP TikTok qua C69: {code}")
                            return code

                # Dự phòng: dùng latest_code đã được backend trích sẵn nếu email mới nhất là từ TikTok
                email_data = result.get("email_data") or {}
                latest_code = email_data.get("latest_code")
                latest_content = (email_data.get("latest_content") or "").lower()
                if latest_code and "tiktok" in latest_content:
                    logger.info(f"Tìm thấy mã OTP TikTok (latest_code) qua C69: {latest_code}")
                    return latest_code

            await asyncio.sleep(6)

        logger.warning(f"Không tìm thấy mã OTP TikTok qua API đọc hộp thư C69 trong thời gian quy định cho {self.email_addr}.")
        return None

    async def get_microsoft_otp_code(self, timeout_secs: int = 120) -> Optional[str]:
        """Đọc OTP xác nhận từ Microsoft gửi về thông qua API C69."""
        logger.info(f"Đang chờ mã OTP Microsoft qua API C69 ({self.email_addr}, email_id={self.email_id}, Timeout: {timeout_secs}s)...")
        loop = asyncio.get_event_loop()
        start_time = loop.time()
        while loop.time() - start_time < timeout_secs:
            result = await loop.run_in_executor(None, self.c69_client.read_mailbox, self.email_id, self.email_addr)
            if result:
                for msg in result.get("emails", []):
                    subject = (msg.get("subject") or "").lower()
                    sender = (msg.get("from") or "").lower()
                    if "microsoft" in subject or "microsoft" in sender or "code" in subject or "verification" in subject or "security" in subject:
                        text = f"{msg.get('subject', '')} {msg.get('body', '')}"
                        # Bắt chính xác mã OTP Microsoft 6 số từ HTML Body
                        otp_match = re.search(r'Security\s+code:\s*<[^>]+>\s*(\d{6})\s*<', text, re.IGNORECASE)
                        if not otp_match:
                            otp_match = re.search(r'Security\s+code:\s*(\d{6})', text, re.IGNORECASE)
                        if not otp_match:
                            otp_match = re.search(r'(?:mã\s+bảo\s+mật|mã\s+xác\s+nhận)[:\s]*(\d{6})', text, re.IGNORECASE)
                        if not otp_match:
                            otp_match = re.search(r'\b\d{6}\b', text)
                            
                        if otp_match:
                            code = otp_match.group(1) if len(otp_match.groups()) > 0 else otp_match.group(0)
                            logger.info(f"🎉 Tìm thấy mã OTP Microsoft chuẩn xác qua C69: {code}")
                            return code
                # Fallback: latest_code
                email_data = result.get("email_data") or {}
                latest_code = email_data.get("latest_code")
                latest_content = (email_data.get("latest_content") or "").lower()
                if latest_code and ("microsoft" in latest_content or "code" in latest_content or "verification" in latest_content):
                    logger.info(f"Tìm thấy mã OTP Microsoft (latest_code) qua C69: {latest_code}")
                    return latest_code
            await asyncio.sleep(6)
        logger.warning(f"Không tìm thấy mã OTP Microsoft qua API C69 trong thời gian quy định cho {self.email_addr}.")
        return None


# ============================================================================
# AUTOMATION LOGIC (TIKTOK SIGNUP, GOOGLE OAUTH, & 2FA)
# ============================================================================

class TikTokSignupAutomation:
    
    def __init__(self, manager: NodriverBrowserManager, tab: Any):
        self.manager = manager
        self.tab = tab

    async def select_dropdown_option(self, container_selector: str, option_text: str) -> bool:
        """Tìm và chọn option trong custom select của TikTok hoặc thẻ select chuẩn."""
        logger.info(f"Đang chọn giá trị '{option_text}' trong '{container_selector}'")
        try:
            # TikTok sử dụng custom div selectors thay vì select chuẩn.
            # Tìm phần tử container trước
            elements = await self.tab.select_all(container_selector)
            if not elements:
                # Nếu không tìm thấy bằng selector phức tạp, thử tìm các thẻ div/div custom
                logger.warning(f"Không tìm thấy selector: {container_selector}. Tìm kiếm phần tử div chứa placeholder...")
            
            # Thực thi đoạn JS tối ưu để tìm dropdown kích hoạt và chọn phần tử hiển thị tương ứng
            clicked = await self.tab.evaluate(f"""
                (() => {{
                    // 1. Thử tìm select element chuẩn trước
                    const selectors = "{container_selector}".split(",");
                    let sel = null;
                    for (let s of selectors) {{
                        const found = document.querySelector(s.trim());
                        if (found) {{ sel = found; break; }}
                    }}
                    
                    if (sel && sel.tag === 'SELECT') {{
                        for (let i = 0; i < sel.options.length; i++) {{
                            if (sel.options[i].text.includes('{option_text}') || sel.options[i].value == '{option_text}') {{
                                sel.selectedIndex = i;
                                sel.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                        }}
                    }}
                    
                    // 2. Với custom div dropdown của TikTok:
                    // Click vào phần tử selector trước để hiển thị danh sách dropdown
                    if (sel) {{
                        sel.click();
                    }} else {{
                        // Dự phòng: Tìm tất cả div có thuộc tính placeholder tương ứng
                        const allDivs = Array.from(document.querySelectorAll('div'));
                        const placeholder = "{container_selector}".includes('month') ? 'Month' : ("{container_selector}".includes('day') ? 'Day' : 'Year');
                        const targetDiv = allDivs.find(d => d.textContent.trim().includes(placeholder) && d.offsetHeight > 0);
                        if (targetDiv) targetDiv.click();
                    }}
                    
                    // Chờ danh sách hiện ra
                    return new Promise((resolve) => {{
                        setTimeout(() => {{
                            // Tìm tất cả các phần tử option hiển thị trong danh sách mới xuất hiện
                            const options = Array.from(document.querySelectorAll('div, li, span, p, a'));
                            const match = options.find(el => {{
                                const txt = el.textContent.trim().toLowerCase();
                                return txt === '{option_text.lower()}' || txt === '{option_text.lower().zfill(2)}';
                            }});
                            
                            if (match) {{
                                match.click();
                                resolve(true);
                            }} else {{
                                // Thử fallback tìm chuỗi con
                                const subMatch = options.find(el => el.textContent.trim().toLowerCase().includes('{option_text.lower()}'));
                                if (subMatch) {{
                                    subMatch.click();
                                    resolve(true);
                                }} else {{
                                    resolve(false);
                                }}
                            }}
                        }}, 500);
                    }});
                }})()
            """)
            return clicked
        except Exception as e:
            logger.error(f"Lỗi khi chọn dropdown '{container_selector}': {e}")
            return False

    async def fill_input_by_selectors(self, target_tab: Any, selectors: list, value: str) -> bool:
        """Tìm và điền input theo danh sách các selector có thể có trên tab được chỉ định."""
        import json as _json
        # Escape value để nhúng an toàn vào JS string (tránh SyntaxError với ký tự đặc biệt)
        value_js = _json.dumps(value)  # VD: "Abc!@#" → '"Abc!@#"' (có nháy kép, đã escape)

        for sel in selectors:
            try:
                element = await target_tab.select(sel)
                if element:
                    await element.click()
                    await asyncio.sleep(0.2)
                    # Xóa dữ liệu cũ nếu có — dùng double-quote để querySelector nhận selector có single-quote
                    sel_js = _json.dumps(sel)
                    await target_tab.evaluate(f"document.querySelector({sel_js}).value = ''")
                    # Tự động gõ phím kiểu người dùng thật
                    for char in value:
                        await element.send_keys(char)
                        await asyncio.sleep(random.uniform(0.04, 0.12))

                    # KIỂM TRA LẠI: Xem giá trị đã được điền thành công chưa
                    # Dùng sel_js thay vì '{sel}' để tránh conflict single-quote trong selector
                    current_val = await target_tab.evaluate(f"document.querySelector({sel_js}).value")
                    if current_val != value:
                        logger.warning(f"Gõ phím thất bại hoặc thiếu ký tự trên {sel}. Đang kích hoạt JS fallback...")
                        # Dùng value_js (đã được json.dumps escape) để tránh SyntaxError
                        await target_tab.evaluate(f"""
                            (() => {{
                                const input = document.querySelector({sel_js});
                                if (input) {{
                                    input.value = {value_js};
                                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                    return true;
                                }}
                                return false;
                            }})()
                        """)

                    logger.info(f"Đã điền thành công vào selector: {sel}")
                    return True
            except Exception as e:
                logger.debug(f"Lỗi khi điền vào selector {sel}: {e}")
                continue
        return False

    async def detect_captcha(self) -> bool:
        """Kiểm tra xem trên màn hình có xuất hiện Captcha hay không."""
        captcha_indicators = [
            "#captcha_container", ".captcha_container", 
            "iframe[src*='captcha']", "iframe[src*='secsdk']",
            ".secsdk-captcha-drag-icon", "#secsdk-captcha-wrapper",
            "div[class*='captcha']"
        ]
        for indicator in captcha_indicators:
            try:
                el = await self.tab.select(indicator)
                if el:
                    logger.info(f"Phát hiện chỉ báo Captcha: {indicator}")
                    return True
            except Exception:
                continue
        return False

    async def handle_captcha_flow(self, captcha_mode: str) -> bool:
        """Giải quyết captcha dựa trên chế độ giải."""
        is_captcha = await self.detect_captcha()
        if not is_captcha:
            return True
            
        logger.warning("⚠️ Captcha xuất hiện trên màn hình!")
        if captcha_mode == "manual":
            print("\n" + "="*60)
            print("HỆ THỐNG PHÁT HIỆN CAPTCHA! VUI LÒNG GIẢI CAPTCHA THỦ CÔNG TRÊN TRÌNH DUYỆT.")
            print("Sau khi giải xong Captcha và màn hình hết che khuất, nhấn Enter tại đây để tiếp tục...")
            print("="*60 + "\n")
            await asyncio.get_event_loop().run_in_executor(None, input)
            return True
        elif captcha_mode == "extension":
            logger.info("Đang chờ Extension giải Captcha tự động...")
            for _ in range(12):
                await asyncio.sleep(5)
                if not await self.detect_captcha():
                    logger.info("Captcha đã được giải bởi Extension!")
                    return True
            logger.warning("Extension giải quá lâu hoặc lỗi. Vui lòng giải tay!")
            await asyncio.get_event_loop().run_in_executor(None, input)
            return True
        else:
            logger.info("API Mode được chọn, đang chờ giải...")
            await asyncio.sleep(10)
        return True


# ============================================================================
# GOOGLE OAUTH AUTOMATION
# ============================================================================

async def automate_google_login(browser: nodriver.Browser, email_addr: str, password: str) -> bool:
    """Tự động hóa luồng đăng nhập Google OAuth trên cửa sổ Popup của Google bằng cơ chế CDP."""
    logger.info("Đang lắng nghe cửa sổ Google OAuth đăng nhập...")
    google_tab = None
    
    # Dò tìm Google OAuth tab thông qua nhiều phương pháp (CDP + browser.tabs)
    for i in range(25):
        try:
            targets = await browser._get_targets()
            for t in targets:
                if t.type_ == 'page' and t.url and 'accounts.google.com' in t.url:
                    logger.info(f"Phát hiện Google target qua CDP! Đang cập nhật targets...")
                    await browser.update_targets()
                    await asyncio.sleep(1)
                    break
        except Exception:
            pass

        for bt in browser.tabs:
            url = getattr(bt, 'url', '') or ''
            if 'accounts.google.com' in url:
                google_tab = bt
                break

        if google_tab:
            break

        # Check tab cuối
        if len(browser.tabs) > 1:
            candidate = browser.tabs[-1]
            try:
                url = await candidate.evaluate("window.location.href")
                if url and 'accounts.google.com' in str(url):
                    google_tab = candidate
                    break
            except Exception:
                pass

        await asyncio.sleep(1)
        
    if not google_tab:
        logger.error("Không tìm thấy cửa sổ Google OAuth đăng nhập.")
        return False
        
    logger.info(f"Đã phát hiện tab Google OAuth: {google_tab.url}")
    await asyncio.sleep(2)
    
    try:
        # Kích hoạt tab Google
        try:
            await google_tab
        except Exception as e:
            logger.warning(f"Kích hoạt Google tab: {e}")

        # 1. Nhập email bằng JS evaluate
        logger.info(f"Đang điền email: {email_addr}...")
        email_entered = False
        for attempt in range(15):
            try:
                result = await google_tab.evaluate(f"""(() => {{
                    const el = document.querySelector("input[type='email']") || 
                               document.querySelector("#identifierId") ||
                               document.querySelector("input[name='identifier']");
                    if (!el) return 'no_input';
                    el.focus();
                    el.value = '';
                    el.value = '{email_addr}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return 'entered';
                }})()""")
                if result == 'entered':
                    email_entered = True
                    break
            except Exception:
                pass
            await asyncio.sleep(1)

        if not email_entered:
            logger.error("Không tìm thấy ô nhập email của Google.")
            return False
            
        await asyncio.sleep(0.5)
        
        # Click nút Next email
        logger.info("Clicking Next...")
        await google_tab.evaluate("""(() => {
            const next = document.querySelector('#identifierNext');
            if (next) { next.click(); return; }
            const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
            const btn = buttons.find(b => b.textContent.includes('Next') || b.textContent.includes('Tiếp theo') || b.textContent.includes('Tiep'));
            if (btn) btn.click();
        })()""")

        logger.info("Đã gửi email, chờ chuyển tiếp sang ô nhập password...")
        await asyncio.sleep(5)
        
        # 2. Nhập mật khẩu bằng JS evaluate
        logger.info("Đang nhập mật khẩu Gmail...")
        pass_entered = False
        for attempt in range(15):
            try:
                result = await google_tab.evaluate(f"""(() => {{
                    const el = document.querySelector("input[type='password']") || 
                               document.querySelector("input[name='Passwd']");
                    if (!el || el.offsetHeight === 0) return 'no_input';
                    el.focus();
                    el.value = '';
                    el.value = '{password}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return 'entered';
                }})()""")
                if result == 'entered':
                    pass_entered = True
                    break
            except Exception:
                pass
            await asyncio.sleep(1)

        if not pass_entered:
            logger.error("Không tìm thấy ô nhập mật khẩu của Google.")
            return False
            
        await asyncio.sleep(0.5)
        
        # Click nút Next password
        logger.info("Clicking password Next...")
        await google_tab.evaluate("""(() => {
            const next = document.querySelector('#passwordNext');
            if (next && next.offsetHeight > 0) { next.click(); return; }
            const buttons = Array.from(document.querySelectorAll('button, div[role="button"]'));
            const btn = buttons.find(b => (b.textContent.includes('Next') || b.textContent.includes('Tiếp theo') || b.textContent.includes('Tiep')) && b.offsetHeight > 0);
            if (btn) btn.click();
        })()""")
            
        logger.info("Đã gửi mật khẩu, chờ đăng nhập hoàn tất...")
        await asyncio.sleep(6)
        
        # 3. Kiểm tra xem có trang yêu cầu xác minh bảo mật hoặc email khôi phục không
        recovery_prompt = await google_tab.evaluate("""
            (() => {
                const bodyText = document.body.textContent;
                return bodyText.includes('confirm your recovery email') || bodyText.includes('xác nhận email khôi phục') || bodyText.includes('Xác nhận email khôi phục');
            })()
        """)
        if recovery_prompt:
            logger.warning("⚠️ Google yêu cầu xác nhận email khôi phục!")
            await google_tab.evaluate("""
                (() => {
                    const divs = Array.from(document.querySelectorAll('div, p, span'));
                    const recoveryOpt = divs.find(d => d.textContent.includes('Confirm your recovery email') || d.textContent.includes('Xác nhận email khôi phục'));
                    if (recoveryOpt) recoveryOpt.click();
                })()
            """)
            await asyncio.sleep(2)
            
            # Gợi ý nhập email khôi phục tự động nếu có sẵn
            print("\n" + "="*50)
            rec_email = input("Nhập Email khôi phục (Recovery Email) cho tài khoản Gmail này: ").strip()
            print("="*50 + "\n")
            
            await google_tab.evaluate(f"""(() => {{
                const el = document.querySelector("input[type='email']");
                if (el) {{
                    el.focus();
                    el.value = '{rec_email}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }})()""")
            
            await asyncio.sleep(0.5)
            await google_tab.evaluate("""
                (() => {
                    const buttons = Array.from(document.querySelectorAll('button'));
                    const next = buttons.find(b => b.textContent.includes('Next') || b.textContent.includes('Tiếp theo'));
                    if (next) next.click();
                })()
            """)
            await asyncio.sleep(5)
                
        # Kiểm tra nếu vẫn còn yêu cầu OTP / xác minh điện thoại / ủy quyền
        for _ in range(30):
            # Check xem tab Google đã đóng chưa (tức là đã đăng nhập xong và redirect về TikTok)
            if google_tab not in browser.tabs:
                logger.info("Google OAuth login tab đã đóng. Tiếp tục luồng trên TikTok.")
                return True
                
            # Thử tự động click các nút "Understand", "Continue", "Allow", "Tôi hiểu", "Tiếp tục" nếu xuất hiện
            try:
                action = await google_tab.evaluate("""
                    (() => {
                        const findButtonByText = (texts) => {
                            const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
                            return buttons.find(b => {
                                if (b.offsetHeight === 0) return false;
                                const text = b.textContent.trim().toLowerCase();
                                return texts.some(t => text === t || text.includes(t));
                            });
                        };

                        const clickElement = (el) => {
                            const opts = { bubbles: true, cancelable: true, view: window };
                            el.focus();
                            el.dispatchEvent(new MouseEvent('mousedown', opts));
                            el.dispatchEvent(new MouseEvent('mouseup', opts));
                            el.dispatchEvent(new MouseEvent('click', opts));
                            
                            const children = el.querySelectorAll('*');
                            children.forEach(c => {
                                c.dispatchEvent(new MouseEvent('mousedown', opts));
                                c.dispatchEvent(new MouseEvent('mouseup', opts));
                                c.dispatchEvent(new MouseEvent('click', opts));
                            });
                        };

                        // 1. Tìm nút Understand / Tôi hiểu / Tôi đã hiểu
                        const understandBtn = findButtonByText(['understand', 'tôi hiểu', 'tôi đã hiểu', 'tôi đồng ý']);
                        if (understandBtn) {
                            clickElement(understandBtn);
                            return 'clicked_understand';
                        }
                        
                        // 2. Tìm nút Continue / Tiếp tục / Allow / Cho phép / Confirm / Xác nhận
                        const continueBtn = findButtonByText(['continue', 'tiếp tục', 'allow', 'cho phép', 'confirm', 'xác nhận']);
                        if (continueBtn) {
                            // Tránh click nhầm các nút Next/Tiếp tục của form nhập email/pass
                            if (document.querySelector("input[type='email']") || document.querySelector("input[type='password']")) {
                                return 'none'; 
                            }
                            clickElement(continueBtn);
                            return 'clicked_continue';
                        }
                        
                        return 'none';
                    })()
                """)
                if action != 'none':
                    logger.info(f"Đã tự động click nút trên Google OAuth: {action}")
                    await asyncio.sleep(2)
            except Exception:
                pass
                
            await asyncio.sleep(2)
            
        logger.warning("Cửa sổ Google OAuth vẫn chưa đóng. Có thể đang bị kẹt OTP hoặc xác minh 2 lớp. Vui lòng hoàn thành trên trình duyệt...")
        print("Nhấn Enter tại đây sau khi bạn đã hoàn tất đăng nhập Google trên trình duyệt...")
        await asyncio.get_event_loop().run_in_executor(None, input)
        return True
    except Exception as e:
        logger.exception(f"Lỗi khi tự động đăng nhập Google OAuth: {e}")
        return False


# ============================================================================
# TIKTOK 2FA SETUP AUTOMATION
# ============================================================================

async def setup_tiktok_2fa(tab: Any, mail_client: Any, email_addr: str) -> Optional[str]:
    """Tự động truy cập phần cấu hình bảo mật TikTok để bật 2FA bằng Authenticator App"""
    logger.info("=== BẮT ĐẦU LUỒNG KÍCH HOẠT 2FA TIKTOK ===")
    
    # 1. Truy cập trang Setting
    await tab.get("https://www.tiktok.com/setting?lang=en")
    await asyncio.sleep(5)
    
    try:
        # 2. Click chọn "Security" từ menu bên trái
        logger.info("Đang tìm và click mục 'Security'...")
        clicked_security = await tab.evaluate("""
            (() => {
                const els = Array.from(document.querySelectorAll('div, a, span, p'));
                const sec = els.find(e => e.textContent.trim() === 'Security' && e.offsetHeight > 0);
                if (sec) {
                    sec.click();
                    return true;
                }
                return false;
            })()
        """)
        if not clicked_security:
            # Click phần tử chứa chữ "Security"
            await tab.evaluate("""
                (() => {
                    const els = Array.from(document.querySelectorAll('*'));
                    const sec = els.find(e => e.textContent.includes('Security') && e.offsetHeight > 0);
                    if (sec) { sec.click(); return true; }
                    return false;
                })()
            """)
        await asyncio.sleep(3)
        
        # 3. Tìm mục "2-step verification" và click vào nút thiết lập
        logger.info("Đang tìm và click kích hoạt '2-step verification'...")
        # Tìm nút hoặc box liên quan đến 2-step verification
        await tab.evaluate("""
            (() => {
                const divs = Array.from(document.querySelectorAll('*'));
                // Tìm div hoặc button chứa chữ "2-step verification"
                const item = divs.find(e => e.textContent.includes('2-step verification') && e.offsetHeight > 0);
                if (item) {
                    // Click vào nó hoặc nút Turn on bên cạnh
                    const parent = item.parentElement;
                    const btn = parent ? parent.querySelector('button, a') : null;
                    if (btn) {
                        btn.click();
                    } else {
                        item.click();
                    }
                }
            })()
        """)
        await asyncio.sleep(3)
        
        # 4. Chọn phương thức Authenticator App
        logger.info("Đang chọn phương thức 'Authenticator app'...")
        await tab.evaluate("""
            (() => {
                const labels = Array.from(document.querySelectorAll('label, div, p, span'));
                const authOpt = labels.find(e => e.textContent.includes('Authenticator app') && e.offsetHeight > 0);
                if (authOpt) {
                    // Tìm checkbox/input trong option này và check
                    const parent = authOpt.closest('div');
                    const checkbox = parent ? parent.querySelector('input[type="checkbox"], input[type="radio"]') : null;
                    if (checkbox) {
                        checkbox.click();
                    } else {
                        authOpt.click();
                    }
                }
            })()
        """)
        await asyncio.sleep(1)
        
        # Click nút Turn On / Next tiếp tục
        await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const turnOn = buttons.find(b => b.textContent.includes('Turn on') || b.textContent.includes('Next') || b.textContent.includes('Tiếp tục'));
                if (turnOn) turnOn.click();
            })()
        """)
        await asyncio.sleep(3)
        
        # 5. Nếu TikTok yêu cầu OTP email để xác thực danh tính trước khi đổi cài đặt
        # Tìm nút Send Code
        send_code_clicked = await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const send = buttons.find(b => b.textContent.includes('Send code') || b.textContent.includes('Gửi mã'));
                if (send) {
                    send.click();
                    return true;
                }
                return false;
            })()
        """)
        if send_code_clicked:
            logger.info("Đã bấm gửi mã OTP xác nhận thay đổi cài đặt 2FA. Đang chờ lấy OTP...")
            await asyncio.sleep(3)
            otp_code = None
            if mail_client:
                otp_code = await mail_client.get_otp_code()
            if not otp_code:
                print("\n" + "="*50)
                otp_code = input("Nhập mã xác nhận OTP thay đổi cài đặt gửi về Email của bạn: ").strip()
                print("="*50 + "\n")
                
            if otp_code:
                # Điền OTP
                code_inputs = await tab.select_all("input[maxlength='6']")
                if code_inputs:
                    await code_inputs[0].click()
                    await code_inputs[0].send_keys(otp_code)
                else:
                    await tab.evaluate(f"""
                        (() => {{
                            const inp = document.querySelector("input[placeholder*='code'], input[maxlength='6']");
                            if (inp) {{
                                inp.value = '{otp_code}';
                                inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            }}
                        }})()
                    """)
                await asyncio.sleep(1)
                # Bấm Next/Submit
                await tab.evaluate("""
                    (() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const next = buttons.find(b => b.textContent.includes('Next') || b.textContent.includes('Submit') || b.textContent.includes('Tiếp tục'));
                        if (next) next.click();
                    })()
                """)
                await asyncio.sleep(4)
                
        # 6. TikTok sẽ hiển thị QR code và Khóa bí mật (Secret Key)
        logger.info("Đang quét tìm khóa bí mật 2FA (Secret Key) trên màn hình...")
        # Sử dụng JS quét toàn bộ text tìm khóa bí mật dạng Base32
        # TikTok 2FA key là một chuỗi chữ và số 16-32 ký tự viết hoa
        secret_key = await tab.evaluate("""
            (() => {
                // 1. Quét tìm trong các phần tử input dạng chỉ đọc
                const inputs = Array.from(document.querySelectorAll('input'));
                for (const inp of inputs) {
                    const val = inp.value.trim().replace(/\\s/g, '');
                    if (/^[A-Z2-7]{16,32}$/.test(val)) {
                        return val;
                    }
                }
                
                // 2. Quét tìm toàn bộ text node
                const walk = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                let node;
                while (node = walk.nextNode()) {
                    const txt = node.textContent.trim().replace(/\\s/g, '');
                    if (/^[A-Z2-7]{16,32}$/.test(txt)) {
                        return txt;
                    }
                }
                
                // 3. Quét các thẻ div, p, span có class hoặc thuộc tính đặc biệt
                const divs = Array.from(document.querySelectorAll('*'));
                for (const d of divs) {
                    if (d.children.length === 0) {
                        const txt = d.textContent.trim().replace(/\\s/g, '');
                        if (/^[A-Z2-7]{16,32}$/.test(txt)) {
                            return txt;
                        }
                    }
                }
                return null;
            })()
        """)
        
        if not secret_key:
            logger.warning("Không tự động trích xuất được 2FA Secret Key từ trang web.")
            print("\n" + "="*60)
            secret_key = input("Không tự động lấy được Key. Vui lòng sao chép 2FA Secret Key trên TikTok và dán vào đây: ").strip().replace(" ", "")
            print("="*60 + "\n")
            
        if not secret_key:
            logger.error("Không có khóa bí mật 2FA. Bỏ qua bật 2FA.")
            return None
            
        logger.info(f"🔑 Đã lấy được Khóa bí mật 2FA: {secret_key}")
        
        # 7. Tạo mã TOTP xác thực hoàn thành
        totp = pyotp.TOTP(secret_key)
        totp_code = totp.now()
        logger.info(f"Sinh mã TOTP xác nhận: {totp_code}")
        
        # Click Next tiếp tục để chuyển đến trang nhập mã xác thực TOTP
        await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const next = buttons.find(b => b.textContent.includes('Next') || b.textContent.includes('Tiếp tục'));
                if (next) next.click();
            })()
        """)
        await asyncio.sleep(2)
        
        # Nhập mã TOTP xác thực
        code_inputs = await tab.select_all("input[maxlength='6']")
        if code_inputs:
            await code_inputs[-1].click()
            await code_inputs[-1].send_keys(totp_code)
        else:
            await tab.evaluate(f"""
                (() => {{
                    const inp = document.querySelector("input[placeholder*='code'], input[maxlength='6']");
                    if (inp) {{
                        inp.value = '{totp_code}';
                        inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }})()
            """)
        await asyncio.sleep(1)
        
        # Bấm xác nhận hoàn tất
        await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const confirm = buttons.find(b => b.textContent.includes('Confirm') || b.textContent.includes('Done') || b.textContent.includes('Xác nhận'));
                if (confirm) confirm.click();
            })()
        """)
        await asyncio.sleep(4)
        logger.info("🎉 Đã hoàn tất cài đặt 2FA trên TikTok!")
        return secret_key
        
    except Exception as e:
        logger.exception(f"Lỗi trong quá trình kích hoạt 2FA: {e}")
        return None


async def disable_email_2fa(tab: Any, mail_client: Any) -> bool:
    """Tắt xác minh 2 bước qua Email hiện tại nếu nó đang được kích hoạt."""
    logger.info("=== BẮT ĐẦU TẮT XÁC MINH EMAIL CŨ (GMAIL) ===")
    await tab.get("https://www.tiktok.com/setting/security?lang=en")
    await asyncio.sleep(5)
    
    try:
        # Kiểm tra xem Email verification có đang BẬT không.
        is_email_active = await tab.evaluate("""
            (() => {
                const els = Array.from(document.querySelectorAll('*'));
                const emailNode = els.find(e => e.textContent.trim() === 'Email' && e.offsetHeight > 0);
                if (!emailNode) return false;
                
                // Đi tìm toggle hoặc trạng thái bên cạnh
                const parent = emailNode.closest('div');
                if (!parent) return false;
                
                const txt = parent.textContent.toLowerCase();
                if (txt.includes('active') || txt.includes('on') || txt.includes('bật')) {
                    return true;
                }
                
                const checkbox = parent.querySelector('input[type="checkbox"]');
                if (checkbox && checkbox.checked) return true;
                
                return false;
            })()
        """)
        
        if not is_email_active:
            logger.info("Email verification hiện tại đang TẮT. Không cần tắt.")
            return True
            
        logger.info("Phát hiện Email verification đang BẬT. Tiến hành tắt...")
        
        # Click vào nút/toggle Email để tắt
        await tab.evaluate("""
            (() => {
                const els = Array.from(document.querySelectorAll('*'));
                const emailNode = els.find(e => e.textContent.trim() === 'Email' && e.offsetHeight > 0);
                if (emailNode) {
                    const parent = emailNode.closest('div');
                    const btn = parent ? parent.querySelector('button, input[type="checkbox"], [role="switch"]') : null;
                    if (btn) btn.click();
                    else emailNode.click();
                }
            })()
        """)
        await asyncio.sleep(3)
        
        # Click "Turn off" xác nhận trong popup nếu hiện ra
        await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const turnOff = buttons.find(b => b.textContent.includes('Turn off') || b.textContent.includes('Tắt') || b.textContent.includes('Deactivate'));
                if (turnOff) turnOff.click();
            })()
        """)
        await asyncio.sleep(3)
        
        # Nếu yêu cầu mã OTP gửi về Email cũ
        send_clicked = await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const send = buttons.find(b => b.textContent.includes('Send code') || b.textContent.includes('Gửi mã'));
                if (send) { send.click(); return true; }
                return false;
            })()
        """)
        if send_clicked:
            logger.info("Đã bấm gửi mã OTP tắt Email 2FA. Đang chờ lấy OTP từ hòm thư cũ...")
            await asyncio.sleep(5)
            otp_code = await mail_client.get_otp_code()
            if not otp_code:
                print("\n" + "="*50)
                otp_code = input("Nhập mã xác nhận OTP tắt Email 2FA gửi về Email cũ của bạn: ").strip()
                print("="*50 + "\n")
                
            if otp_code:
                await tab.evaluate(f"""
                    (() => {{
                        const inp = document.querySelector("input[placeholder*='code'], input[maxlength='6']");
                        if (inp) {{
                            inp.value = '{otp_code}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }})()
                """)
                await asyncio.sleep(1)
                await tab.evaluate("""
                    (() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const next = buttons.find(b => b.textContent.includes('Next') || b.textContent.includes('Confirm') || b.textContent.includes('Submit'));
                        if (next) next.click();
                    })()
                """)
                await asyncio.sleep(4)
        
        logger.info("Đã tắt xác minh qua Email cũ thành công.")
        return True
    except Exception as e:
        logger.exception(f"Lỗi khi tắt xác minh qua Email cũ: {e}")
        return False


async def change_tiktok_email(tab: Any, mail_client_old: Any, c69: C69Client, replacement_email_data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Thay đổi email liên kết của tài khoản TikTok sang Hotmail mới từ C69."""
    logger.info("=== BẮT ĐẦU ĐỔI EMAIL TÀI KHOẢN TIKTOK ===")
    await tab.get("https://www.tiktok.com/setting/account?lang=en")
    await asyncio.sleep(5)
    
    try:
        # Click vào nút/mục Email hoặc Change email
        logger.info("Tìm và click nút đổi email...")
        email_clicked = await tab.evaluate("""
            (() => {
                const els = Array.from(document.querySelectorAll('*'));
                const emailNode = els.find(e => e.textContent.trim() === 'Email' && e.offsetHeight > 0);
                if (emailNode) {
                    const parent = emailNode.closest('div');
                    const btn = parent ? parent.querySelector('button, a, [role="button"]') : null;
                    if (btn) { btn.click(); return true; }
                    emailNode.click();
                    return true;
                }
                const changeBtn = els.find(e => e.textContent.includes('Change email') && e.offsetHeight > 0);
                if (changeBtn) { changeBtn.click(); return true; }
                return false;
            })()
        """)
        
        if not email_clicked:
            logger.error("Không tìm thấy nút hoặc mục Email để đổi.")
            return None
            
        await asyncio.sleep(3)
        
        # Bước 1: Xác minh email cũ
        logger.info("Gửi OTP xác minh email cũ...")
        send_old_clicked = await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const send = buttons.find(b => b.textContent.includes('Send code') || b.textContent.includes('Gửi mã'));
                if (send) { send.click(); return true; }
                return false;
            })()
        """)
        
        if send_old_clicked:
            logger.info("Đã gửi OTP về Email cũ. Đang chờ đọc hòm thư cũ...")
            await asyncio.sleep(5)
            otp_old = await mail_client_old.get_otp_code()
            if not otp_old:
                print("\n" + "="*50)
                otp_old = input("Nhập mã OTP xác minh email cũ gửi về Email cũ của bạn: ").strip()
                print("="*50 + "\n")
                
            if otp_old:
                await tab.evaluate(f"""
                    (() => {{
                        const inp = document.querySelector("input[placeholder*='code'], input[maxlength='6']");
                        if (inp) {{
                            inp.value = '{otp_old}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }})()
                """)
                await asyncio.sleep(1)
                await tab.evaluate("""
                    (() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const next = buttons.find(b => b.textContent.includes('Next') || b.textContent.includes('Confirm') || b.textContent.includes('Submit'));
                        if (next) next.click();
                    })()
                """)
                await asyncio.sleep(4)
                
        # Bước 2: Lấy Email Hotmail mới chưa đăng ký từ C69 hoặc dùng email được chỉ định sẵn
        new_email_data = None
        if replacement_email_data:
            new_email_data = replacement_email_data
            logger.info("Sử dụng Email Hotmail thay thế được chỉ định sẵn...")
        else:
            logger.info("Lấy Email Hotmail mới từ C69...")
            new_email_data = c69.get_unused_email("hotmail")
            
        if not new_email_data:
            logger.error("Không lấy được email Hotmail mới chưa dùng để đổi.")
            return None
            
        new_email_addr = new_email_data.get("email") or new_email_data.get("email_address", "")
        new_email_id = new_email_data.get("id")
        
        logger.info(f"Email Hotmail mới nhận được: {new_email_addr} (ID: {new_email_id})")
        
        # Nhập Email mới
        logger.info("Nhập Email mới...")
        email_filled = await tab.evaluate(f"""
            (() => {{
                const inp = document.querySelector("input[type='email']") || 
                           document.querySelector("input[placeholder*='Email']");
                if (inp) {{
                    inp.focus();
                    inp.value = '{new_email_addr}';
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            }})()
        """)
        
        if not email_filled:
            logger.error("Không tìm thấy ô nhập email mới để điền.")
            return None
            
        await asyncio.sleep(1)
        
        # Click "Send code" cho email mới
        logger.info("Gửi OTP đến Email mới...")
        send_new_clicked = await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const send = buttons.find(b => b.textContent.includes('Send code') || b.textContent.includes('Gửi mã'));
                if (send) { send.click(); return true; }
                return false;
            })()
        """)
        
        if not send_new_clicked:
            logger.error("Không click được nút gửi OTP đến Email mới.")
            return None
            
        logger.info("Đã gửi OTP đến Email mới. Đang chờ đọc hòm thư mới từ C69...")
        await asyncio.sleep(5)
        
        # Tạo mailbox đọc thư cho email mới
        mail_client_new = C69MailBox(c69, new_email_id, new_email_addr)
        otp_new = await mail_client_new.get_otp_code()
        
        if not otp_new:
            print("\n" + "="*50)
            otp_new = input(f"Nhập mã OTP đổi email gửi về Email mới ({new_email_addr}): ").strip()
            print("="*50 + "\n")
            
        if not otp_new:
            logger.error("Không có mã OTP cho email mới. Đổi email thất bại.")
            return None
            
        # Điền OTP mới
        await tab.evaluate(f"""
            (() => {{
                const inp = document.querySelector("input[placeholder*='code'], input[maxlength='6']");
                if (inp) {{
                    inp.value = '{otp_new}';
                    inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
            }})()
        """)
        await asyncio.sleep(1)
        
        # Bấm xác nhận hoàn tất đổi email
        await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const confirm = buttons.find(b => b.textContent.includes('Confirm') || b.textContent.includes('Done') || b.textContent.includes('Next') || b.textContent.includes('Xác nhận'));
                if (confirm) confirm.click();
            })()
        """)
        await asyncio.sleep(5)
        
        logger.info(f"🎉 Thay đổi email thành công! Email mới: {new_email_addr}")
        return new_email_data
        
    except Exception as e:
        logger.exception(f"Lỗi khi thực hiện thay đổi email liên kết: {e}")
        return None


async def enable_email_2fa_new(tab: Any, mail_client_new: Any) -> bool:
    """Bật lại tính năng xác minh 2 bước qua Email mới."""
    logger.info("=== BẮT ĐẦU BẬT XÁC MINH QUA EMAIL MỚI ===")
    await tab.get("https://www.tiktok.com/setting/security?lang=en")
    await asyncio.sleep(5)
    
    try:
        # Click chọn Email trong phần "2-step verification"
        await tab.evaluate("""
            (() => {
                const labels = Array.from(document.querySelectorAll('label, div, p, span'));
                const emailOpt = labels.find(e => e.textContent.trim() === 'Email' && e.offsetHeight > 0);
                if (emailOpt) {
                    const parent = emailOpt.closest('div');
                    const checkbox = parent ? parent.querySelector('input[type="checkbox"], input[type="radio"]') : null;
                    if (checkbox) checkbox.click();
                    else emailOpt.click();
                }
            })()
        """)
        await asyncio.sleep(1)
        
        # Click Next/Turn On
        await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const turnOn = buttons.find(b => b.textContent.includes('Turn on') || b.textContent.includes('Next') || b.textContent.includes('Tiếp tục'));
                if (turnOn) turnOn.click();
            })()
        """)
        await asyncio.sleep(3)
        
        # Click Send Code
        send_clicked = await tab.evaluate("""
            (() => {
                const buttons = Array.from(document.querySelectorAll('button'));
                const send = buttons.find(b => b.textContent.includes('Send code') || b.textContent.includes('Gửi mã'));
                if (send) { send.click(); return true; }
                return false;
            })()
        """)
        
        if send_clicked:
            logger.info("Đã gửi OTP kích hoạt Email 2FA mới. Đang chờ lấy OTP...")
            await asyncio.sleep(5)
            otp_code = await mail_client_new.get_otp_code()
            if not otp_code:
                print("\n" + "="*50)
                otp_code = input("Nhập mã OTP kích hoạt Email 2FA mới gửi về hòm thư mới của bạn: ").strip()
                print("="*50 + "\n")
                
            if otp_code:
                await tab.evaluate(f"""
                    (() => {{
                        const inp = document.querySelector("input[placeholder*='code'], input[maxlength='6']");
                        if (inp) {{
                            inp.value = '{otp_code}';
                            inp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }})()
                """)
                await asyncio.sleep(1)
                
                await tab.evaluate("""
                    (() => {
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const next = buttons.find(b => b.textContent.includes('Next') || b.textContent.includes('Confirm') || b.textContent.includes('Submit') || b.textContent.includes('Done'));
                        if (next) next.click();
                    })()
                """)
                await asyncio.sleep(4)
                
        logger.info("🎉 Bật xác minh bằng Email mới thành công.")
        return True
        
    except Exception as e:
        logger.exception(f"Lỗi khi bật lại xác minh qua Email mới: {e}")
        return False


# ============================================================================
# MAIN SCRIPT EXECUTION
# ============================================================================

async def _verify_signup_success(tab: Any, timeout_secs: int = 30) -> bool:
    """Kiểm tra đăng ký TikTok thành công bằng multi-signal detection.

    Positive signals (đăng ký thành công):
      - URL chuyển về feed / fyp / profile / suggest-accounts / interests
      - Avatar user hoặc element 'For You' page xuất hiện
      - Trang chọn sở thích / username (post-signup onboarding)

    Negative signals (đăng ký thất bại):
      - Vẫn còn OTP input trên màn hình
      - Error / alert message hiển thị rõ ràng
    """
    logger.info(f"Xác minh đăng ký thành công (timeout={timeout_secs}s)...")
    start = asyncio.get_event_loop().time()

    while asyncio.get_event_loop().time() - start < timeout_secs:
        try:
            # Log URL hiện tại để user theo dõi
            current_url = await tab.evaluate("window.location.href")
            elapsed = int(asyncio.get_event_loop().time() - start)
            logger.info(f"[Verify {elapsed}s] URL: {current_url}")

            # --- Negative signals (kiểm tra thất bại trước) ---
            has_otp_input = await tab.evaluate("""
                (() => {
                    const inp = document.querySelector("input[maxlength='6'], input[name='code']");
                    return inp ? inp.offsetHeight > 0 : false;
                })()
            """)
            if has_otp_input:
                logger.debug("Vẫn còn OTP input → chưa hoàn tất đăng ký.")
                await asyncio.sleep(2)
                continue

            # Kiểm tra error phrase và capture text thực tế để debug
            error_result = await tab.evaluate("""
                (() => {
                    const body = document.body.textContent.toLowerCase();
                    const errorPhrases = [
                        'incorrect code', 'invalid code', 'code expired',
                        'ma\u0303 kho\u00f4ng h\u1ee3p le\u0323', 'ma\u0303 xa\u0301c minh sai', 'something went wrong',
                        'this email has already been registered',
                        'maximum number of attempts',
                        'too many attempts', 'try again later',
                        'you\\'ve made too many',
                        'rate limit', 'account suspended',
                        'network error', 'connection error'
                    ];
                    const matched = errorPhrases.find(p => body.includes(p));
                    // Lấy đoạn text gần khu vực error để debug
                    const errEl = document.querySelector('[class*="error"], [class*="alert"], [role="alert"]');
                    const errText = errEl ? errEl.textContent.trim().substring(0, 200) : '';
                    return { matched: matched || null, errText: errText, bodySnippet: body.substring(0, 300) };
                })()
            """)
            if error_result and error_result.get('matched'):
                err_phrase = error_result.get('matched')
                err_text = error_result.get('errText', '')
                body_snippet = error_result.get('bodySnippet', '')
                logger.error(f"Phát hiện lỗi đăng ký: phrase='{err_phrase}' | errEl='{err_text}' | body='{body_snippet[:150]}'")
                return False

            # --- Positive signals ---
            url_lower = (current_url or "").lower()
            success_url_parts = [
                '/foryou', '/fyp', '/following', '/live',
                '/suggest-accounts', '/profile', '/home',
                'tiktok.com/@',       # profile page
                '/interests',         # chọn sở thích
                '/select-topics',     # chọn chủ đề
                '/onboarding',        # onboarding flow
                '/signup/select',     # select interests/username
            ]
            if any(part in url_lower for part in success_url_parts):
                logger.info(f"🎉 URL xác nhận đăng ký thành công: {current_url}")
                return True

            # Tìm element đặc trưng của user đã đăng nhập hoặc post-signup
            has_logged_in_el = await tab.evaluate("""
                (() => {
                    // Avatar / user menu
                    if (document.querySelector('[data-e2e="profile-icon"], [data-e2e="user-avatar"]')) return 'avatar';
                    // "For You" heading
                    const els = Array.from(document.querySelectorAll('h1, h2, span, p'));
                    if (els.find(e => e.textContent.trim().toLowerCase() === 'for you' && e.offsetHeight > 0)) return 'foryou';
                    // Nav bar của user đã đăng nhập
                    if (document.querySelector('[data-e2e="nav-profile"], [data-e2e="nav-upload"]')) return 'nav';
                    // Post-signup: chọn interests
                    const bodyText = document.body.textContent.toLowerCase();
                    if (bodyText.includes('what are you interested in') || bodyText.includes('select your interests')) return 'interests';
                    if (bodyText.includes('create a username') || bodyText.includes('choose a username')) return 'username';
                    // Signup modal đã biến mất (URL vẫn là tiktok.com/ nhưng form đã đóng = thành công)
                    const signupForm = document.querySelector('form[data-e2e="signup-form"], [class*="SignupModal"], [class*="signup-modal"]');
                    const loginModal = document.querySelector('[class*="LoginModal"], [class*="login-modal"], [data-e2e="modal-close-inner-button"]');
                    if (!signupForm && !loginModal) {
                        // Kiểm tra thêm: video feed hoặc sidebar xuất hiện (dấu hiệu đã vào trang chính)
                        if (document.querySelector('video, [data-e2e="recommend-list-item-container"], [class*="DivVideoFeed"]')) return 'feed-visible';
                    }
                    return null;
                })()
            """)
            if has_logged_in_el:
                logger.info(f"🎉 Phát hiện signal đăng ký thành công: {has_logged_in_el}")
                return True

        except Exception as e:
            logger.debug(f"Lỗi nhỏ khi verify signup: {e}")

        await asyncio.sleep(2)

    logger.warning("Hết timeout xác minh. Không xác định được trạng thái đăng ký.")
    return False


async def safe_send_keys(tab, selector, text, retries=3):
    for i in range(retries):
        try:
            # 1. Thử điền bằng JS DOM trực tiếp (chuẩn xác cho cả React/Fluent UI và tránh lỗi -32000 CDP)
            filled = await tab.evaluate(f"""
            (() => {{
                const sel = `{selector}`;
                const el = document.querySelector(sel);
                if (el) {{
                    el.focus();
                    const proto = Object.getPrototypeOf(el);
                    const setter = Object.getOwnPropertyDescriptor(proto, 'value')?.set || Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value')?.set;
                    if (setter) {{
                        setter.call(el, `{text}`);
                    }} else {{
                        el.value = `{text}`;
                    }}
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    return true;
                }}
                return false;
            }})()
            """)
            if filled:
                return True
                
            # 2. Fallback CDP select nếu DOM chưa render
            try:
                el = await tab.select(selector)
                if el:
                    await el.send_keys(text)
                    return True
            except Exception:
                pass
        except Exception as e:
            if i == retries - 1:
                logger.debug(f"[safe_send_keys] Không tìm thấy hoặc lỗi điền {selector}: {e}")
                return False
            await asyncio.sleep(1)
    return False

async def safe_click(tab, selector, retries=3):
    for i in range(retries):
        try:
            # Ưu tiên evaluate click trực tiếp bằng JS DOM để tránh lỗi CDP query selector
            clicked = await tab.evaluate(f"""
            (() => {{
                const sel = `{selector}`;
                const btn = document.querySelector(sel);
                if (btn) {{
                    btn.focus();
                    btn.click();
                    return true;
                }}
                // Tìm theo text content nếu có
                const buttons = Array.from(document.querySelectorAll('button, input[type="submit"], [role="button"], a'));
                for (const b of buttons) {{
                    const t = (b.innerText || b.value || b.textContent || '').trim().toLowerCase();
                    if (t === 'next' || t === 'tiếp theo' || t === 'send code' || t === 'gửi mã' || t === 'yes' || t === 'có' || t === 'accept' || t === 'chấp nhận') {{
                        b.click();
                        return true;
                    }}
                }}
                return false;
            }})()
            """)
            if clicked:
                return True
                
            try:
                el = await tab.select(selector)
                if el:
                    await el.click()
                    return True
            except Exception:
                pass
        except Exception as e:
            if i == retries - 1:
                logger.debug(f"[safe_click] Không tìm thấy phần tử {selector}: {e}")
                return False
            await asyncio.sleep(1)
    return False


async def auto_login_microsoft_and_get_token(browser, email, password, note_field, client_id, email_id, c69_client):
    logger.info(f"🔑 Khởi động luồng lấy Token cho {email}...")
    import re
    import urllib.parse
    
    # Trích xuất email khôi phục từ note
    recovery_email = None
    if note_field:
        emails_found = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', note_field)
        for e_found in emails_found:
            if e_found.lower() != email.lower():
                recovery_email = e_found.strip()
                break
    if recovery_email:
        logger.info(f"🔍 Tìm thấy email khôi phục liên kết: {recovery_email}")
        
    tab = await browser.get("about:blank", new_tab=True)
    try:
        # Truy cập trang đăng nhập live.com (timeout tối đa 8s để tránh treo chờ tài nguyên phụ)
        try:
            await asyncio.wait_for(tab.get("https://login.live.com/"), timeout=8)
        except Exception:
            logger.info("Chờ load trang live.com timeout, tiếp tục...")
        await asyncio.sleep(2)
        
        # 1. Điền Email
        await safe_send_keys(tab, "input[type='email'], input[name='loginfmt'], input[id*='username']", email)
        await asyncio.sleep(1)
        await safe_click(tab, "#idSIButton9, input[type='submit'], button[type='submit']")
        await asyncio.sleep(3)
            
        # 2. Điền Password
        has_pass = await safe_send_keys(tab, "input[type='password'], input[name='passwd'], #i0118, input[id*='Password']", password)
        if not has_pass:
            # Click 'Use your password' nếu có
            await safe_click(tab, "a:has-text('Use your password'), button:has-text('Use your password'), span:has-text('Use your password')")
            await asyncio.sleep(2)
            await safe_send_keys(tab, "input[type='password'], input[name='passwd'], #i0118, input[id*='Password']", password)
            
        await asyncio.sleep(1)
        await safe_click(tab, "#idSIButton9, input[type='submit'], button[type='submit'], button.fui-Button")
        await asyncio.sleep(4)
                
        # 3. Xử lý các màn hình trung gian (Xác minh khôi phục, Nhắc nhở bảo mật, Duy trì đăng nhập, Protect your account)
        temp_mail_client = None
        for step_idx in range(8):
            current_url = await tab.evaluate("window.location.href") or tab.url or ""
            logger.info(f"🔄 Đang ở bước trung gian {step_idx+1}/8 (URL: {current_url[:60]}...)")
            
            body_text = await tab.evaluate("document.body.textContent")
            if not isinstance(body_text, str):
                body_text = ""
            body_text_lower = body_text.lower()
            
            # Nếu đã vào màn hình chính tài khoản / account.live / portal -> thoát sớm sang OAuth
            if "account.live.com" in current_url and "proofs" not in current_url and "identity" not in current_url:
                logger.info("Đã vào trang tài khoản Microsoft thành công!")
                break
            
            # A. Nhận diện màn hình Protect your account (Cấu hình email khôi phục mới) bằng Selector
            alt_email_inp = await tab.select("input[name='iAltEmail'], input[name='EmailAddress'], input[name='iProofInput'], input[id*='AltEmail'], input[id*='iAlternate'], input[id*='Alternate']")
            if alt_email_inp:
                if not temp_mail_client:
                    # Lấy ngẫu nhiên 1 hòm thư Microsoft đang sống từ C69 Pool
                    rand_c69_box = None
                    if c69_client:
                        rand_c69_box = c69_client.get_random_valid_recovery_mailbox(exclude_email=email)
                    
                    if rand_c69_box and rand_c69_box.get("id") and rand_c69_box.get("email"):
                        rec_id = rand_c69_box["id"]
                        rec_mail = rand_c69_box["email"]
                        class C69ActiveMailbox:
                            def __init__(self, c69_c, m_id, m_email):
                                self.email_address = m_email
                                self.mailbox = C69MailBox(c69_c, m_id, m_email)
                            async def get_microsoft_otp(self):
                                return await self.mailbox.get_microsoft_otp_code()
                        temp_mail_client = C69ActiveMailbox(c69_client, rec_id, rec_mail)
                        logger.info(f"🎲 Chọn hòm thư khôi phục C69 sống: {rec_mail} (ID: {rec_id})")
                    else:
                        email_prefix = email.split("@")[0].strip() if "@" in email else email.strip()
                        clean_prefix = re.sub(r'[^a-zA-Z0-9._-]', '', email_prefix) or "recovery"
                        temp_mail_client = TempMailFviainboxes(username=clean_prefix, domain="fviainboxes.com")
                    
                if temp_mail_client and temp_mail_client.email_address:
                    logger.info(f"🔑 Phát hiện màn hình yêu cầu Email bảo mật mới. Đang điền: {temp_mail_client.email_address}")
                    await safe_send_keys(tab, "input[name='iAltEmail'], input[name='EmailAddress'], input[name='iProofInput'], input[id*='AltEmail'], input[id*='iAlternate'], input[id*='Alternate']", temp_mail_client.email_address)
                    await asyncio.sleep(1)
                    await safe_click(tab, "input[type='submit'], input#idSIButton9, button[type='submit'], button:has-text('Next')")
                    await asyncio.sleep(4)
                    continue

            # B. Nhận diện màn hình nhập mã OTP của Email bảo mật mới bằng Selector OTC
            otc_inp = await tab.select("input[id='idTxtBx_OTC'], input[name='otc'], input[id*='OTC'], input[type='tel']")
            if otc_inp and temp_mail_client:
                logger.info("🔑 Phát hiện màn hình yêu cầu nhập mã OTP cho Email bảo mật mới...")
                otp_code = await temp_mail_client.get_microsoft_otp()
                if otp_code:
                    logger.info(f"🔑 Đang điền mã OTP: {otp_code}")
                    await safe_send_keys(tab, "input[id='idTxtBx_OTC'], input[name='otc'], input[id*='OTC'], input[type='tel']", otp_code)
                    await asyncio.sleep(1)
                    await safe_click(tab, "input[type='submit'], input#idSIButton9, #idSIButton9, button[type='submit']")
                    await asyncio.sleep(5)
                    
                    # Cập nhật ngay tức thì recovery_email lên DB C69 ngay khi xác minh OTP thành công
                    if c69_client and email_id and getattr(temp_mail_client, 'email_address', None):
                        try:
                            _loop = asyncio.get_event_loop()
                            await _loop.run_in_executor(None, c69_client.update_recovery_email_only, email_id, temp_mail_client.email_address)
                        except Exception as e_up:
                            logger.error(f"Lỗi auto-save recovery email: {e_up}")
                    continue
                else:
                    logger.warning("Không lấy được OTP từ email bảo mật tạm thời.")

            # C. Nếu bắt xác minh email khôi phục cũ (Verify your identity / Verify your email)
            if "verify your identity" in body_text_lower or "verify your email" in body_text_lower or "khôi phục" in body_text_lower:
                # 1. Trích xuất gợi ý hint email (ví dụ: ng*****@gmail.com hoặc ng*****@fviainboxes.com)
                email_hint_match = re.search(r'[\w\.*-]+@[\w\.-]+\.\w+', body_text)
                hint_str = email_hint_match.group(0).lower() if email_hint_match else ""
                
                # 2. Kiểm tra xem email khôi phục có nằm trong hệ thống mail tạm fviainboxes.com hay note liên kết không
                is_fvia_hint = "fviainboxes" in hint_str or (recovery_email and "fviainboxes" in recovery_email.lower())
                
                # Lấy tiền tố username của email chính
                email_prefix = email.split("@")[0].strip() if "@" in email else email.strip()
                clean_prefix = re.sub(r'[^a-zA-Z0-9._-]', '', email_prefix)
                expected_fvia_email = f"{clean_prefix}@fviainboxes.com".lower()
                
                target_rec_email = None
                if is_fvia_hint:
                    target_rec_email = expected_fvia_email
                    if not temp_mail_client:
                        temp_mail_client = TempMailFviainboxes(username=clean_prefix, domain="fviainboxes.com")
                elif recovery_email and "fviainboxes" in recovery_email.lower():
                    target_rec_email = recovery_email
                    if not temp_mail_client:
                        rec_user = recovery_email.split("@")[0]
                        temp_mail_client = TempMailFviainboxes(username=rec_user, domain="fviainboxes.com")
                elif recovery_email:
                    # Có email khôi phục cụ thể trong note (ví dụ từ trước)
                    target_rec_email = recovery_email
                else:
                    # Gợi ý là domain ngoài (gmail.com, yahoo.com...) mà không có trong note -> Bỏ qua ngay
                    target_rec_email = None
                
                if target_rec_email:
                    logger.info(f"🔑 Nhận diện email khôi phục tạm thời hợp lệ: {target_rec_email}. Đang tiến hành xác minh...")
                    # Tìm option "Email ....."
                    await safe_click(tab, "[id*='Proof'], [class*='proof'], [data-value*='@']")
                    await asyncio.sleep(2)
                    
                    proof_input = await tab.select("input[type='email'], input[name='ProofConfirm'], input[id*='ProofConfirm'], input[name='EmailAddress'], input[name='iProofInput']")
                    if proof_input:
                        await safe_send_keys(tab, "input[type='email'], input[name='ProofConfirm'], input[id*='ProofConfirm'], input[name='EmailAddress'], input[name='iProofInput']", target_rec_email)
                        await asyncio.sleep(1)
                        await safe_click(tab, "input[type='submit'], input#idSIButton9, #idSIButton9, button[type='submit'], button:has-text('Send code')")
                        await asyncio.sleep(4)
                        continue
                else:
                    # Email khôi phục ở domain ngoài khác (Gmail, Yahoo, Mail cá nhân lạ...) không thuộc mail tạm -> Bỏ qua và cập nhật status=3 (Tạm thời/Cần check lại) lên C69
                    logger.warning(f"⚠️ Email {email} yêu cầu xác minh qua email khôi phục lạ ({hint_str or 'Unknown'}). Bỏ qua và cập nhật trạng thái lên C69.")
                    if c69_client and email_id:
                        try:
                            c69_client.update_email_status(email_id, 3, f"Bắt OTP email khôi phục lạ ({hint_str})") # 3: Temporary / Cần kiểm tra lại
                        except Exception as e_st:
                            pass
                    return False
                        
            # D. Bấm qua các màn hình khác như "Stay signed in?", "Break free from passwords"
            await safe_click(tab, "input[type='submit'], input#idSIButton9, button[type='submit'], #idSIButton9")
            await asyncio.sleep(3)
                
        # 4. Điều hướng tới OAuth URL để xin cấp quyền lấy Authorization Code
        redirect_uri = "https://login.live.com/oauth20_desktop.srf"
        auth_url = f"https://login.live.com/oauth20_authorize.srf?" \
                   f"client_id={client_id}" \
                   f"&response_type=code" \
                   f"&redirect_uri={redirect_uri}" \
                   f"&scope=https://graph.microsoft.com/Mail.Read%20offline_access" \
                   f"&state=c69_auto_token"
                   
        logger.info("Chuyển hướng trình duyệt tới URL xin quyền OAuth...")
        try:
            await asyncio.wait_for(tab.get(auth_url), timeout=8)
        except Exception:
            logger.info("Chờ load trang OAuth timeout, tiếp tục...")
        await asyncio.sleep(2)
        
        # Click Accept (nếu có Consent screen)
        has_clicked_accept = False
        for _ in range(12):  # Tăng lên 12 lần để đủ thời gian chờ mail OTP
            current_url = tab.url
            if "nativeclient" in current_url and "code=" in current_url:
                break
                
            body_text = await tab.evaluate("document.body.textContent")
            if not isinstance(body_text, str):
                body_text = ""
            body_text_lower = body_text.lower()
            
            # A. Màn hình Protect your account (Cấu hình email khôi phục mới) bằng Selector
            alt_email_inp = await tab.select("input[name='iAltEmail'], input[name='EmailAddress'], input[id*='AltEmail'], input[id*='iAlternate'], input[id*='Alternate']")
            if alt_email_inp:
                if not temp_mail_client:
                    temp_mail_client = TempMail1SecMail()
                    temp_mail_client.generate_email()
                    # Fallback nếu 1secmail bị block/403
                    if not temp_mail_client.email_address:
                        logger.warning("⚠️ 1secmail bị lỗi/block. Sử dụng email bảo mật dự phòng hệ thống...")
                        class C69FallbackMailbox:
                            def __init__(self, c69, email_id, email):
                                self.email_address = email
                                self.mailbox = C69MailBox(c69, email_id, email)
                            async def get_microsoft_otp(self):
                                return await self.mailbox.get_microsoft_otp_code()
                        # Dùng email active ID 1074 làm email khôi phục dự phòng
                        temp_mail_client = C69FallbackMailbox(c69_client, 1074, "uyentungphamtun081960@hotmail.com")
                if temp_mail_client.email_address:
                    logger.info(f"🔑 [OAuth Step] Phát hiện yêu cầu email bảo mật. Đang điền: {temp_mail_client.email_address}")
                    await safe_send_keys(tab, "input[name='iAltEmail'], input[name='EmailAddress'], input[id*='AltEmail'], input[id*='iAlternate'], input[id*='Alternate']", temp_mail_client.email_address)
                    await asyncio.sleep(1)
                    await safe_click(tab, "input[type='submit'], input#idSIButton9, #idSIButton9, button[type='submit']")
                    await asyncio.sleep(5)
                    continue

            # B. Màn hình nhập OTP (nếu xuất hiện sau khi click Accept)
            otc_inp = await tab.select("input[id='idTxtBx_OTC'], input[name='otc'], input[id*='OTC'], input[type='tel']")
            if otc_inp and temp_mail_client:
                logger.info("🔑 [OAuth Step] Phát hiện yêu cầu nhập mã OTP cho email bảo mật...")
                otp_code = await temp_mail_client.get_microsoft_otp()
                if otp_code:
                    logger.info(f"🔑 [OAuth Step] Đang điền mã OTP email bảo mật: {otp_code}")
                    await safe_send_keys(tab, "input[id='idTxtBx_OTC'], input[name='otc'], input[id*='OTC'], input[type='tel']", otp_code)
                    await asyncio.sleep(1)
                    await safe_click(tab, "input[type='submit'], input#idSIButton9, #idSIButton9, button[type='submit']")
                    await asyncio.sleep(5)
                    continue
                else:
                    logger.warning("Không lấy được OTP từ email bảo mật tạm thời.")
                        
            if not has_clicked_accept:
                accept_btn = await tab.select("input#idBtn_Accept, button#idBtn_Accept, input[type='submit'], input#idSIButton9, button[type='submit']")
                if accept_btn:
                    logger.info("Click Accept đồng ý cấp quyền...")
                    await safe_click(tab, "input#idBtn_Accept, button#idBtn_Accept, input[type='submit'], input#idSIButton9, button[type='submit'], #idSIButton9")
                    has_clicked_accept = True
                    await asyncio.sleep(3)
                    continue
            await asyncio.sleep(2)
                
        # 5. Lấy code từ redirect url
        current_url = await tab.evaluate("window.location.href")
        if not isinstance(current_url, str):
            current_url = tab.url or ""
            
        logger.info(f"URL sau khi cấp quyền OAuth: {current_url}")
        if "code=" in current_url:
            parsed = urllib.parse.urlparse(current_url)
            code = urllib.parse.parse_qs(parsed.query).get("code", [None])[0]
            if code:
                logger.info(f"🎉 Đã lấy được Authorization Code: {code[:12]}...")
                # Gửi request POST đổi code lấy token
                token_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"
                payload = {
                    "client_id": client_id,
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri
                }
                
                loop = asyncio.get_event_loop()
                res = await loop.run_in_executor(None, lambda: requests.post(token_url, data=payload, timeout=15))
                if res.status_code == 200:
                    res_json = res.json()
                    new_ref_token = res_json.get("refresh_token")
                    if new_ref_token:
                        # Lưu lên C69
                        saved = await loop.run_in_executor(None, c69_client.save_mailbox_results, email_id, new_ref_token)
                        if saved:
                            logger.info(f"🎉 Tự động làm mới và cập nhật thành công Token OAuth cho {email}!")
                            return True
                    else:
                        logger.error(f"Response Microsoft không có refresh_token: {res.text}")
                else:
                    logger.error(f"Lỗi đổi code lấy token (Status {res.status_code}): {res.text}")
        else:
            logger.error(f"Không thể chuyển hướng đến URL callback chứa code (URL hiện tại: {current_url})")
            
    except Exception as e:
        logger.error(f"Lỗi khi tự động lấy token: {e}")
    finally:
        try:
            await tab.close()
        except Exception:
            pass
            
    return False


async def run_tiktok_registration_flow(args):
    logger.info("=== BẮT ĐẦU LUỒNG TỰ ĐỘNG ĐĂNG KÝ TIKTOK ===")
    
    # 1. Kết nối và Đăng nhập C69
    c69 = C69Client(base_url=args.get("c69_url", "https://c69.us"))
    
    # Đọc credentials C69 từ login_config.json
    login_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "login_config.json")
    c69_logged = False
    
    if os.path.exists(login_config_path):
        try:
            with open(login_config_path, "r") as f:
                c69_creds = json.load(f)
                email_c69 = c69_creds.get("email")
                pass_c69 = c69_creds.get("password")
                if email_c69 and pass_c69:
                    logger.info(f"Tìm thấy cấu hình C69: {email_c69}, đang đăng nhập...")
                    c69_logged = c69.login(email_c69, pass_c69)
        except Exception as e:
            logger.error(f"Lỗi đọc login_config.json: {e}")
            
    if not c69_logged:
        # Hỏi thông tin đăng nhập C69 từ console nếu không có file cấu hình
        print("\n" + "="*50)
        email_c69 = input("Nhập Email tài khoản C69.us: ").strip()
        pass_c69 = input("Nhập Mật khẩu C69.us: ").strip()
        print("="*50 + "\n")
        c69_logged = c69.login(email_c69, pass_c69)
        
    if not c69_logged:
        logger.error("Không thể đăng nhập vào C69. Dừng chương trình.")
        return False

    # 2. Lấy thông tin email đầu vào từ C69 để đăng ký
    reg_method = args.get("reg_method", "c69-email")
    c69_email_data = None   # dict từ AccountsEmails (nguồn email đăng ký)
    email_addr = ""
    password = ""
    email_id = None         # ID trong AccountsEmails (để đọc OTP và link FK)

    # Nếu truyền trực tiếp email từ GUI chọn thủ công
    custom_email = args.get("email")
    custom_email_id = args.get("email_id")
    custom_email_password = args.get("email_password")

    if custom_email:
        email_addr = custom_email
        if custom_email_id is not None:
            try:
                email_id = int(custom_email_id)
            except (ValueError, TypeError):
                email_id = None
        else:
            email_id = None
        password = custom_email_password or args.get("password") or generate_random_string(12)
        logger.info(f"Sử dụng email chọn thủ công từ GUI: {email_addr} (id={email_id})")
    else:
        # Nếu không có email chọn thủ công, lấy email tự động từ C69 theo phương thức đăng ký
        if reg_method == "c69-email":
            # Lấy email Hotmail/Gmail chưa dùng từ AccountsEmails trên C69
            # Thứ tự ưu tiên: hotmail trước (Microsoft Graph OTP), fallback sang gmail
            c69_email_data = c69.get_unused_email("hotmail") or c69.get_unused_email("gmail")
            if not c69_email_data:
                logger.error("Không tìm thấy email chưa dùng nào trên C69 để đăng ký.")
                return False
            email_addr = c69_email_data.get("email") or c69_email_data.get("email_address", "")
            password = c69_email_data.get("password", "")
            email_id = c69_email_data.get("id")  # AccountsEmails.id
        elif reg_method == "google":
            # Lấy email chưa đăng ký TikTok từ C69 (Gmail, Google Workspace, Edu — bất kỳ tài khoản Google nào)
            c69_email_data = c69.get_unused_email("tiktok")
            if not c69_email_data:
                logger.error("Không tìm thấy email chưa đăng ký TikTok nào trên C69.")
                return False
            email_addr = c69_email_data.get("email") or c69_email_data.get("email_address", "")
            password = c69_email_data.get("password", "")
            email_id = c69_email_data.get("id")  # AccountsEmails.id
        else:
            # Chế độ tự sinh TempMail
            mail_client = TempMail1SecMail()
            email_addr = mail_client.generate_email()
            password = args.get("password") or generate_random_string(12)

    # Xử lý thông tin email thay thế (replacement_email)
    custom_replacement_email = args.get("replacement_email")
    custom_replacement_email_id = args.get("replacement_email_id")
    custom_replacement_email_password = args.get("replacement_email_password")
    
    replacement_email_data = None
    if custom_replacement_email:
        replacement_email_data = {
            "email": custom_replacement_email,
            "id": custom_replacement_email_id,
            "password": custom_replacement_email_password
        }

    logger.info(f"Thông tin Tài khoản Đăng ký: Email={email_addr} | Password={password}")

    # 3. Cấu hình Mail Client để nhận OTP
    mail_client = None
    if reg_method == "c69-email" or reg_method == "google":
        if email_id:
            # Ưu tiên đọc mail qua API backend C69: dùng Microsoft Graph OAuth2 cho Hotmail/Outlook
            # (Microsoft đã tắt Basic Auth IMAP, đăng nhập IMAP bằng password sẽ luôn thất bại) và
            # IMAP chuẩn cho Gmail. Tránh script tự kết nối IMAP thô sẽ không hoạt động với Hotmail/Outlook.
            logger.info(f"Dùng API đọc hộp thư của C69 (email_id={email_id}) để lấy mã OTP.")
            mail_client = C69MailBox(c69, email_id, email_addr)
        else:
            logger.warning(
                "Tài khoản C69 không có email_id liên kết. Chuyển sang đọc IMAP trực tiếp - "
                "lưu ý: Microsoft đã tắt Basic Auth IMAP cho Hotmail/Outlook nên luồng này có thể thất bại."
            )
            imap_host = "imap.gmail.com"
            email_lower = email_addr.lower()
            if any(dom in email_lower for dom in ["hotmail.com", "outlook.com", "live.com", "msn.com"]):
                imap_host = "outlook.office365.com"

            mail_client = IMAPMailBox(
                host=args.get("imap_host") or imap_host,
                user=email_addr,
                password=password
            )
    elif args.get("email_mode") == "tempmail":
        mail_client = TempMail1SecMail()
        mail_client.email_address = email_addr
        mail_client.login, mail_client.domain = email_addr.split("@")

    # 4. Khởi động Mun AntiBrowser
    manager = NodriverBrowserManager()
    extra_args = []
    extension_path = args.get("extension_path", "")
    if extension_path and os.path.exists(extension_path):
        logger.info(f"Đang nạp Extension giải Captcha từ: {extension_path}")
        extra_args.append(f"--load-extension={extension_path}")
        
    logger.info("Đang khởi động trình duyệt chống phát hiện...")
    browser, tab = await manager.start(
        proxy_string=args.get("proxy", ""),
        proxy_type=args.get("proxy_type", "socks5"),
        start_url="https://www.tiktok.com/",
        headless=args.get("headless", False),
        extra_args=extra_args
    )
    
    auto = TikTokSignupAutomation(manager, tab)

    # Kiểm tra thử khả năng đọc thư qua Graph API nếu là Hotmail/Outlook có liên kết email_id
    if reg_method == "c69-email" and email_id:
        email_lower = email_addr.lower()
        if any(dom in email_lower for dom in ["hotmail.com", "outlook.com", "live.com", "msn.com"]):
            logger.info("🔍 Kiểm tra kết nối hòm thư Microsoft Graph API...")
            test_res = None
            try:
                loop = asyncio.get_running_loop()
                test_res = await loop.run_in_executor(None, c69.read_mailbox, email_id)
            except Exception as e:
                logger.warning(f"Lỗi khi kiểm tra thử hòm thư: {e}")
                
            need_reauth = False
            if test_res and not test_res.get('success'):
                msg = test_res.get('message', '')
                if any(x in msg for x in ["Graph API", "JWT", "InvalidAuthenticationToken", "token", "Token"]):
                    logger.warning(f"⚠️ Hòm thư Microsoft báo lỗi Token: {msg}")
                    need_reauth = True
            elif not test_res:
                logger.warning("⚠️ Không thể kết nối kiểm tra hòm thư Microsoft.")
                
            if need_reauth:
                logger.info("🚀 Tự động mở tab mới để đăng nhập và lấy lại Token OAuth...")
                note = args.get("note", "")
                client_id = args.get("client_id") or "9e5f94bc-e8a4-4e73-b8be-63364c29d753"
                reauth_success = await auto_login_microsoft_and_get_token(
                    browser=browser,
                    email=email_addr,
                    password=password,
                    note_field=note,
                    client_id=client_id,
                    email_id=email_id,
                    c69_client=c69
                )
                if reauth_success:
                    logger.info("🎉 Cấp lại token thành công! Tạo lại đối tượng hòm thư C69MailBox.")
                    mail_client = C69MailBox(c69, email_id, email_addr)
                else:
                    logger.error("❌ Tự động cấp lại token OAuth thất bại. Sẽ thử dùng IMAP fallback của server.")

    # Chờ trang TikTok load xong (quan trọng khi dùng proxy — trang load chậm hơn)
    logger.info("Đang chờ trang TikTok tải xong...")
    page_loaded = False
    for wait_i in range(15):  # Tối đa 30 giây (15 x 2s)
        try:
            ready = await tab.evaluate("""
                (() => {
                    if (document.readyState !== 'complete') return 'loading';
                    // Kiểm tra có nội dung TikTok thực sự (không phải blank page)
                    const body = document.body ? document.body.textContent : '';
                    if (body.length < 50) return 'empty';
                    if (body.toLowerCase().includes('tiktok') || body.toLowerCase().includes('log in') || body.toLowerCase().includes('for you')) return 'ready';
                    return 'partial';
                })()
            """)
            logger.info(f"  Page status [{wait_i*2}s]: {ready}")
            if ready == 'ready':
                page_loaded = True
                break
            elif ready == 'partial' and wait_i >= 5:
                # Sau 10s nếu có content nhưng chưa detect TikTok → vẫn tiếp tục
                page_loaded = True
                break
        except Exception:
            pass
        await asyncio.sleep(2)

    if not page_loaded:
        logger.warning("Trang TikTok load chậm — tiếp tục thử click Login...")

    await asyncio.sleep(random.uniform(1.0, 2.0))  # Mô phỏng xem trang

    # 1. Mô phỏng click vào nút Log in / Đăng nhập ở trang chủ để mở Modal
    logger.info("Đang click nút Log in trên trang chủ...")
    login_clicked = False
    for attempt in range(3):
        login_clicked = await tab.evaluate("""
            (() => {
                let btn = document.querySelector('[data-e2e="top-login-button"]');
                if (btn) { btn.click(); return true; }
                btn = document.querySelector('[data-e2e="nav-login-button"]');
                if (btn) { btn.click(); return true; }
                const els = Array.from(document.querySelectorAll('button, a, div'));
                const match = els.find(e => {
                    const txt = e.textContent.toLowerCase();
                    return (txt.includes('log in') || txt.includes('đăng nhập')) && e.offsetHeight > 0;
                });
                if (match) { match.click(); return true; }
                return false;
            })()
        """)
        await asyncio.sleep(2)
        # Kiểm tra xem Login Modal đã mở chưa
        has_modal = await tab.evaluate("""
            (() => {
                const text = document.body.textContent.toLowerCase();
                return text.includes('log in to tiktok') || text.includes('đăng nhập vào tiktok') || !!document.querySelector('iframe[src*="login"]');
            })()
        """)
        if has_modal:
            logger.info("Đã mở thành công Modal Đăng nhập.")
            login_clicked = True
            break
        else:
            logger.warning(f"Lần {attempt+1}: Chưa thấy Modal mở. Đang thử lại...")

    if not login_clicked:
        logger.warning("Không thể mở Modal đăng nhập bằng click. Thực hiện chuyển hướng trực tiếp...")
        await tab.get("https://www.tiktok.com/login")
        await asyncio.sleep(4)

    # 2. Click vào link 'Sign up' (Đăng ký) ở dưới chân Modal để đổi sang form Đăng ký
    logger.info("Đang bấm chuyển hướng sang Modal Đăng ký...")
    signup_modal_clicked = False
    for attempt in range(3):
        signup_modal_clicked = await tab.evaluate("""
            (() => {
                const elements = Array.from(document.querySelectorAll('a, p, span, div, button'));
                let signUpLink = elements.find(l => {
                    const txt = l.textContent.trim();
                    if (txt === 'Sign up' || txt === 'Đăng ký') {
                        const parentTxt = l.parentElement ? l.parentElement.textContent : '';
                        if (parentTxt.includes("Don't have") || parentTxt.includes("Chưa có tài khoản")) {
                            return l.offsetHeight > 0;
                        }
                    }
                    return false;
                });
                if (!signUpLink) {
                    signUpLink = elements.find(l => {
                        const txt = l.textContent.trim();
                        return (txt === 'Sign up' || txt === 'Đăng ký') && l.offsetHeight > 0;
                    });
                }
                if (!signUpLink) {
                    const links = Array.from(document.querySelectorAll('a'));
                    signUpLink = links.find(a => a.href && a.href.includes('/signup'));
                }
                if (signUpLink) {
                    signUpLink.click();
                    return true;
                }
                return false;
            })()
        """)
        await asyncio.sleep(2)
        # Kiểm tra xem màn hình Đăng ký đã hiện ra chưa
        has_signup_choices = await tab.evaluate("""
            (() => {
                const text = document.body.textContent.toLowerCase();
                return text.includes('sign up for tiktok') || text.includes('đăng ký tiktok') || window.location.href.includes('/signup');
            })()
        """)
        if has_signup_choices:
            logger.info("Đã chuyển sang màn hình Đăng ký thành công.")
            signup_modal_clicked = True
            break
        else:
            logger.warning(f"Lần {attempt+1}: Chưa chuyển sang màn hình Đăng ký. Thử lại...")

    if not signup_modal_clicked:
        logger.warning("Thực hiện chuyển hướng trực tiếp sang trang Đăng ký...")
        await tab.get("https://www.tiktok.com/signup")
        await asyncio.sleep(4)

    # 3. Click chọn phương thức đăng ký trong Modal Đăng ký
    try:
        if reg_method == "google":
            # Luồng Đăng ký bằng Google OAuth
            logger.info("Đang chọn 'Continue with Google'...")
            google_btn_clicked = False
            for attempt in range(5):
                google_btn_clicked = await tab.evaluate("""
                    (() => {
                        const candidates = [];
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
                        let node;
                        while (node = walker.nextNode()) {
                            const ownText = Array.from(node.childNodes)
                                .filter(n => n.nodeType === 3)
                                .map(n => n.textContent.trim())
                                .join(' ').toLowerCase();
                            if (ownText.includes('google') && node.offsetHeight > 0 && node.offsetWidth > 20) {
                                const r = node.getBoundingClientRect();
                                candidates.push({ el: node, area: r.width * r.height, text: ownText });
                            }
                        }
                        if (candidates.length === 0) {
                            const all = Array.from(document.querySelectorAll('div[role="button"], button, a'));
                            for (const el of all) {
                                const t = el.textContent.trim().toLowerCase();
                                if (t.includes('continue with google') && el.offsetHeight > 0) {
                                    candidates.push({ el: el, area: 1, text: t });
                                }
                            }
                        }
                        if (candidates.length === 0) return false;
                        candidates.sort((a, b) => a.area - b.area);
                        const best = candidates[0];
                        
                        let clickable = best.el;
                        let parent = best.el;
                        for (let i = 0; i < 5; i++) {
                            parent = parent.parentElement;
                            if (!parent) break;
                            if (parent.tagName === 'BUTTON' || parent.tagName === 'A' || parent.getAttribute('role') === 'button') {
                                clickable = parent;
                                break;
                            }
                        }
                        clickable.click();
                        return true;
                    })()
                """)
                await asyncio.sleep(2)
                
                has_popup = False
                try:
                    targets = await browser._get_targets()
                    has_popup = any(t.url and 'accounts.google.com' in t.url for t in targets)
                except Exception:
                    pass
                    
                if not has_popup:
                    has_popup = any("accounts.google.com" in (getattr(t, 'url', '') or '') for t in browser.tabs)
                    
                if has_popup:
                    logger.info("Đã mở cửa sổ Google OAuth thành công.")
                    google_btn_clicked = True
                    break
                else:
                    logger.warning(f"Lần {attempt+1}: Chưa phát hiện cửa sổ Google OAuth. Thử lại...")
            
            if not google_btn_clicked:
                logger.error("Không thể kích hoạt luồng Google OAuth. Hủy đăng ký.")
                return False

            google_success = await automate_google_login(browser, email_addr, password)
            if not google_success:
                logger.error("Đăng nhập Google OAuth thất bại.")
                return False
                
            logger.info("Chờ TikTok chuyển trang hoàn tất đăng ký...")
            await asyncio.sleep(8)
            
        else:
            # Luồng Đăng ký bằng Email + Mật khẩu trực tiếp
            logger.info("Đang click chọn tùy chọn 'Use phone / email / username'...")
            email_option_clicked = False
            for attempt in range(3):
                email_option_clicked = await tab.evaluate("""
                    (() => {
                        const elements = Array.from(document.querySelectorAll('button, a, div, p, span'));
                        const matches = elements.filter(el => {
                            const txt = el.textContent.trim().toLowerCase();
                            const hasPhoneEmail = (txt.includes('phone') || txt.includes('điện thoại')) && txt.includes('email');
                            const hasUsername = txt.includes('username') || txt.includes('tên người dùng');
                            return (hasPhoneEmail || hasUsername) && el.offsetHeight > 0;
                        });
                        if (matches.length === 0) return false;
                        
                        // Sắp xếp chọn thẻ lá nhỏ nhất để không bấm nhầm vào container lớn
                        matches.sort((a, b) => {
                            const rA = a.getBoundingClientRect();
                            const rB = b.getBoundingClientRect();
                            return (rA.width * rA.height) - (rB.width * rB.height);
                        });
                        
                        matches[0].click();
                        return true;
                    })()
                """)
                await asyncio.sleep(2)
                # Kiểm tra các dropdown ngày sinh đã hiển thị chưa
                has_dropdowns = await tab.evaluate("""
                    (() => {
                        return !!(document.querySelector('[data-e2e="month-select"]') || document.querySelector('select[name="month"]'));
                    })()
                """)
                if has_dropdowns:
                    logger.info("Đã mở thành công form điền thông tin đăng ký.")
                    email_option_clicked = True
                    break
                else:
                    logger.warning(f"Lần {attempt+1}: Chưa mở được form điền Email. Thử lại...")

            if not email_option_clicked:
                logger.warning("Thực hiện chuyển hướng trực tiếp sang Form đăng ký bằng Email...")
                await tab.get("https://www.tiktok.com/signup/phone-or-email/email")
                await asyncio.sleep(4)

            # 1. Điền Ngày sinh (Sinh ngẫu nhiên tuổi từ 18-35)
            month_names = ["January", "February", "March", "April", "May", "June", 
                           "July", "August", "September", "October", "November", "December"]
            birth_month = random.choice(month_names)
            birth_day = str(random.randint(1, 28))
            birth_year = str(random.randint(1990, 2005))
            
            logger.info(f"Thiết lập ngày sinh ảo: {birth_month} {birth_day}, {birth_year}")
            
            # Chọn Tháng, Ngày, Năm
            month_sel = "[data-e2e='month-select'], select[placeholder='Month'], select[name='month']"
            await auto.select_dropdown_option(month_sel, birth_month)
            await asyncio.sleep(0.5)
            
            day_sel = "[data-e2e='day-select'], select[placeholder='Day'], select[name='day']"
            await auto.select_dropdown_option(day_sel, birth_day)
            await asyncio.sleep(0.5)
            
            year_sel = "[data-e2e='year-select'], select[placeholder='Year'], select[name='year']"
            await auto.select_dropdown_option(year_sel, birth_year)
            await asyncio.sleep(1)

            # 1.5 Chuyển đổi từ tab Số điện thoại sang tab Email nếu mặc định là Số điện thoại
            logger.info("Đang chuyển đổi sang tab 'Sign up with email'...")
            switch_to_email_clicked = False
            for attempt in range(3):
                switch_to_email_clicked = await tab.evaluate("""
                    (() => {
                        const elements = Array.from(document.querySelectorAll('a, p, span, div, button'));
                        const matches = elements.filter(l => {
                            // 1. Khớp theo liên kết href (Cách chính xác và tối ưu nhất)
                            if (l.tagName === 'A' && l.href && l.href.includes('/signup/phone-or-email/email')) {
                                return l.offsetHeight > 0;
                            }
                            
                            // 2. Khớp dự phòng bằng văn bản hiển thị
                            const txt = l.textContent.trim().toLowerCase();
                            const isEmailSwitch = txt === 'sign up with email' || 
                                                 txt === 'đăng ký bằng email' || 
                                                 txt === 'use email' || 
                                                 txt === 'sử dụng email' ||
                                                 txt.includes('sign up with email') || 
                                                 txt.includes('đăng ký bằng email') || 
                                                 txt.includes('use email') || 
                                                 txt.includes('sử dụng email');
                            return isEmailSwitch && l.offsetHeight > 0;
                        });
                        
                        if (matches.length > 0) {
                            // Sắp xếp chọn thẻ lá nhỏ nhất để click chính xác
                            matches.sort((a, b) => {
                                const rA = a.getBoundingClientRect();
                                const rB = b.getBoundingClientRect();
                                return (rA.width * rA.height) - (rB.width * rB.height);
                            });
                            matches[0].click();
                            return true;
                        }
                        return false;
                    })()
                """)
                await asyncio.sleep(2)
                
                # Xác minh: Kiểm tra xem input[name="email"] đã hiện ra chưa
                has_email_input = await tab.evaluate("""
                    (() => {
                        return !!(document.querySelector('input[name="email"]') || document.querySelector('input[type="email"]') || document.querySelector('input[placeholder*="Email"]'));
                    })()
                """)
                if has_email_input:
                    logger.info("Đã chuyển đổi sang tab Đăng ký bằng Email thành công.")
                    switch_to_email_clicked = True
                    break
                else:
                    logger.warning(f"Lần {attempt+1}: Chưa chuyển đổi được sang tab Email. Thử lại...")
            
            if not switch_to_email_clicked:
                logger.warning("Không thể chuyển đổi tab qua click. Thực hiện điều hướng trực tiếp sang Form đăng ký bằng Email...")
                await tab.get("https://www.tiktok.com/signup/phone-or-email/email")
                await asyncio.sleep(4)

            # 2. Điền Email & Mật khẩu
            logger.info("Đang điền thông tin tài khoản...")
            email_selectors = ["input[name='email']", "input[type='email']", "input[placeholder*='Email']"]
            password_selectors = ["input[type='password']", "input[placeholder*='Password']"]
            
            await auto.fill_input_by_selectors(tab, email_selectors, email_addr)
            await asyncio.sleep(0.5)
            await auto.fill_input_by_selectors(tab, password_selectors, password)
            await asyncio.sleep(1)

            # 3. Click gửi mã OTP (Send Code)
            logger.info("Đang tìm và click nút gửi mã xác minh (Send Code)...")
            send_btn = None
            all_buttons = await tab.select_all("button")
            for btn in all_buttons:
                text = btn.text.lower()
                if "send code" in text or "gửi mã" in text or "send otp" in text:
                    send_btn = btn
                    break
                    
            if send_btn:
                await send_btn.click()
            else:
                send_btn = await tab.select("button[data-e2e='send-code-button'], button[type='button']")
                if send_btn: await send_btn.click()
                
            await asyncio.sleep(3)

            # 3.5. Kiểm tra lỗi rate-limit ngay sau click Send Code
            page_error = await tab.evaluate("""
                (() => {
                    const body = document.body.textContent.toLowerCase();
                    const rateLimitPhrases = [
                        'maximum number of attempts',
                        'too many attempts',
                        'try again later',
                        'you\'ve made too many',
                        'rate limit',
                        'account suspended',
                        'this email has already been registered'
                    ];
                    const matched = rateLimitPhrases.find(p => body.includes(p));
                    if (matched) {
                        // Lấy text error element cụ thể
                        const errEl = document.querySelector('[class*="error"], [class*="alert"], [role="alert"], [class*="Error"]');
                        const errText = errEl ? errEl.textContent.trim().substring(0, 300) : '';
                        return { error: matched, detail: errText || body.substring(0, 300) };
                    }
                    return null;
                })()
            """)
            if page_error and isinstance(page_error, dict):
                err_msg = page_error.get('error', 'unknown')
                err_detail = page_error.get('detail', '')
                logger.error(f"TikTok bao loi sau Send Code: '{err_msg}'")
                logger.error(f"   Chi tiet: {err_detail[:200]}")
                logger.info("Goi y: Doi IP/proxy hoac cho vai gio truoc khi thu lai.")
                return False

            # 4. Kiểm tra và Giải quyết Captcha
            await auto.handle_captcha_flow(args.get("captcha_mode", "manual"))

            # 4.5. Kiểm tra lỗi lần 2 sau captcha (TikTok có thể hiện lỗi sau khi giải captcha)
            await asyncio.sleep(2)
            post_captcha_error = await tab.evaluate("""
                (() => {
                    const body = document.body.textContent.toLowerCase();
                    const phrases = [
                        'maximum number of attempts',
                        'too many attempts', 'try again later',
                        'this email has already been registered'
                    ];
                    const matched = phrases.find(p => body.includes(p));
                    return matched || null;
                })()
            """)
            if post_captcha_error and isinstance(post_captcha_error, str):
                logger.error(f"TikTok bao loi sau Captcha: '{post_captcha_error}'")
                logger.info("Goi y: Doi IP/proxy hoac cho vai gio truoc khi thu lai.")
                return False

            # 5. Nhận mã OTP và điền xác minh
            otp_code = None
            if mail_client:
                otp_code = await mail_client.get_otp_code()
                
            if not otp_code:
                # Báo email lỗi lên C69
                if email_id:
                    logger.warning(f"⚠️ Báo email ID {email_id} lỗi đọc mail/không có OTP lên server C69...")
                    try:
                        loop = asyncio.get_running_loop()
                        await loop.run_in_executor(None, c69.update_email_status, email_id, 5)
                    except Exception as e:
                        logger.error(f"Lỗi khi cập nhật trạng thái email lỗi: {e}")
                
                print("\n" + "="*50)
                otp_code = input("Nhập mã OTP 6 số nhận từ Email của bạn: ").strip()
                print("="*50 + "\n")
                
            if not otp_code:
                logger.error("Không có mã OTP. Dừng luồng đăng ký.")
                return False

            code_input_selectors = ["input[placeholder*='code']", "input[name='code']", "input[data-e2e='code-input']", "input[maxlength='6']"]
            await auto.fill_input_by_selectors(tab, code_input_selectors, otp_code)
            await asyncio.sleep(1)

            # 6. Click Sign Up hoàn tất
            logger.info("Đang thực hiện click đăng ký tài khoản...")
            signup_btn = None
            all_buttons = await tab.select_all("button")
            for btn in all_buttons:
                text = btn.text.lower()
                if "next" in text or "sign up" in text or "đăng ký" in text or "tiếp tục" in text:
                    signup_btn = btn
                    break
                    
            if signup_btn:
                await signup_btn.click()
            else:
                signup_btn = await tab.select("button[type='submit']")
                if signup_btn: await signup_btn.click()

            await asyncio.sleep(8)
            
        # 5. Xác minh đăng ký thành công trên TikTok (multi-signal detection)
        logger.info("Đang xác minh kết quả đăng ký TikTok...")
        success = await _verify_signup_success(tab, timeout_secs=30)

        if not success:
            logger.error("⛔ Xác minh đăng ký thất bại — TikTok không xác nhận tài khoản mới.")
            return False

        logger.info("🎉 ĐĂNG KÝ TÀI KHOẢN TIKTOK THÀNH CÔNG!")
        
        # 6. Thiết lập và tối ưu bảo mật tài khoản
        final_email_addr = email_addr
        final_email_id = email_id
        two_factor_key = ""
        
        # 6.1. Tắt xác minh qua Email cũ (Gmail) nếu đang bật
        await disable_email_2fa(tab, mail_client)
        
        # 6.2. Kích hoạt bảo mật 2 lớp qua Authenticator App
        two_factor_key = await setup_tiktok_2fa(tab, mail_client, email_addr)
        if not two_factor_key:
            logger.warning("Bật 2FA Authenticator thất bại hoặc bị bỏ qua.")
            two_factor_key = ""
            
        # 6.3. Đổi Email tài khoản TikTok sang Hotmail mới từ C69
        new_email_data = await change_tiktok_email(tab, mail_client, c69, replacement_email_data)
        
        if new_email_data:
            final_email_addr = new_email_data.get("email") or new_email_data.get("email_address", "")
            final_email_id = new_email_data.get("id")
            
            # Tạo mailbox mới để bật lại 2FA qua Email mới
            mail_client_new = C69MailBox(c69, final_email_id, final_email_addr)
            
            # 6.4. Bật lại xác minh qua Email mới (Hotmail)
            await enable_email_2fa_new(tab, mail_client_new)
        else:
            logger.error("Đổi Email tài khoản TikTok sang Hotmail mới thất bại! Giữ nguyên Gmail cũ.")

        # 7. Đồng bộ lưu trữ kết quả lên C69 với thông tin tài khoản hoàn thiện
        profile_id = str(manager._current_profile.get("id", "none"))

        db_email_id = final_email_id
        if db_email_id and not str(db_email_id).isdigit():
            db_email_id = None

        c69.add_tiktok_account(
            email_addr=final_email_addr,
            password=password,
            two_factor_key=two_factor_key,
            profile_id=profile_id,
            accounts_emails_id=db_email_id,  # Link về email Hotmail mới hoạt động
        )

        # Đánh dấu email mới là đã sử dụng
        if db_email_id:
            c69.mark_email_as_used(db_email_id)
            
        # Lưu trữ dự phòng ở file cục bộ
        account_data = {
            "email": final_email_addr,
            "password": password,
            "two_factor_auth": two_factor_key,
            "profile_id": profile_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        
        output_file = "registered_accounts.json"
        accounts = []
        if os.path.exists(output_file):
            try:
                with open(output_file, "r") as f:
                    accounts = json.load(f)
            except Exception: pass
            
        accounts.append(account_data)
        with open(output_file, "w") as f:
            json.dump(accounts, f, indent=4)
            
        logger.info("Đã hoàn tất quy trình và lưu trữ thông tin tài khoản!")
        return True

    except Exception as e:
        logger.exception(f"Lỗi không mong muốn trong quá trình thực thi: {e}")
        return False
        
    finally:
        await asyncio.sleep(5)
        logger.info("Đang đóng trình duyệt...")
        await manager.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TikTok Auto-Registration Tool via Mun AntiBrowser")
    parser.add_argument("--reg-method", choices=["c69-email", "google", "tempmail"], default="c69-email",
                        help="Phương thức đăng ký: c69-email (email C69), google (Google OAuth Gmail C69), tempmail (TempMail)")
    parser.add_argument("--email-mode", choices=["tempmail", "imap", "manual"], default="imap",
                        help="Chế độ email: tempmail, imap, manual")
    parser.add_argument("--c69-url", default="https://c69.us", help="URL của máy chủ C69")
    parser.add_argument("--email", default="", help="Địa chỉ email nếu dùng chế độ manual")
    parser.add_argument("--password", default="", help="Mật khẩu tài khoản TikTok (mặc định sinh ngẫu nhiên)")
    parser.add_argument("--proxy", default="", help="Proxy kết nối (ví dụ: host:port hoặc user:pass@host:port)")
    parser.add_argument("--proxy-type", default="socks5", choices=["socks5", "http"], help="Loại proxy")
    parser.add_argument("--captcha-mode", choices=["manual", "extension", "api"], default="manual",
                        help="Chế độ giải captcha: manual (giải tay), extension (load ext), api")
    parser.add_argument("--extension-path", default="", help="Đường dẫn đến thư mục extension giải captcha")
    parser.add_argument("--headless", action="store_true", help="Chạy ẩn danh trình duyệt (không khuyến khích khi cần giải tay)")
    
    # Cấu hình IMAP
    parser.add_argument("--imap-host", default="", help="Địa chỉ máy chủ IMAP")
    parser.add_argument("--imap-user", default="", help="Tài khoản IMAP")
    parser.add_argument("--imap-pass", default="", help="Mật khẩu IMAP")

    args = parser.parse_args()
    asyncio.run(run_tiktok_registration_flow(vars(args)))
