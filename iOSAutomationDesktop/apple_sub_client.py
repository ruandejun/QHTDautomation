"""
Apple Subscription Client - Desktop Worker Module
Refactored for full-cycle backend-driven automation with GrandSlam SRP-6a.

This module connects to the C69 Django backend APIs to:
1. Login Apple ID via GrandSlam + Anisette Server
2. Handle 2FA verification flow
3. Execute subscription purchase via iTunes Store
4. Verify receipt with TikTok API
"""
import requests
import json
import time
import logging
from PyQt5.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


class AppleSubscriptionClient:
    """
    Client that communicates with C69 backend APIs for Apple subscription automation.
    Supports both SOCKS5 and HTTP proxy protocols.
    """
    
    # C69 Backend API base URL
    DEFAULT_API_BASE = "https://c69.us/dashboard"
    
    # Local Anisette Server (Docker container on c69)
    DEFAULT_ANISETTE_URL = "http://anisette:6969"
    
    def __init__(self, api_base=None, anisette_url=None):
        self.api_base = api_base or self.DEFAULT_API_BASE
        self.anisette_url = anisette_url or self.DEFAULT_ANISETTE_URL
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        # Auth state
        self.session_id = None
        self.authenticated = False
        self.apple_id = None
    
    def _configure_proxy(self, proxy_string):
        """
        Configure proxy for requests. Supports:
        - socks5://user:pass@ip:port
        - http://user:pass@ip:port
        - ip:port (auto-detect or default to socks5)
        """
        if not proxy_string:
            return
        
        proxy_string = proxy_string.strip()
        
        # Auto-prefix if no protocol
        if not proxy_string.startswith(('socks5://', 'socks4://', 'http://', 'https://')):
            proxy_string = f'socks5://{proxy_string}'
        
        self.session.proxies.update({
            'http': proxy_string,
            'https': proxy_string
        })
    
    def get_anisette_headers(self):
        """Fetch Anisette headers from Anisette Server (Docker container)."""
        try:
            r = requests.get(f"{self.anisette_url}/", timeout=5)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            logger.warning(f"Anisette fetch failed: {e}")
        return {}
    
    def login_apple_id(self, apple_id, password, proxy=None):
        """
        Step 1: Initiate Apple ID login via C69 backend.
        Backend handles GrandSlam SRP-6a + Anisette headers.
        
        Returns:
            dict: {success, requires_2fa, session_id, message}
        """
        self.apple_id = apple_id
        
        if proxy:
            self._configure_proxy(proxy)
        
        try:
            r = self.session.post(
                f"{self.api_base}/api/apple-sub/login/",
                json={
                    'apple_id': apple_id,
                    'password': password,
                    'proxy': proxy or '',
                    'anisette_url': self.anisette_url,
                },
                timeout=30
            )
            
            result = r.json()
            self.session_id = result.get('session_id')
            
            if result.get('success'):
                self.authenticated = True
            
            return result
        except Exception as e:
            logger.error(f"Login API error: {e}")
            return {
                'success': False,
                'requires_2fa': False,
                'message': f'Lỗi kết nối C69 API: {str(e)}'
            }
    
    def verify_2fa(self, code_2fa):
        """
        Step 2: Verify 2FA code via C69 backend.
        
        Returns:
            dict: {success, message, account_info}
        """
        if not self.session_id:
            return {'success': False, 'message': 'Chưa thực hiện login (session_id trống).'}
        
        try:
            r = self.session.post(
                f"{self.api_base}/api/apple-sub/verify-2fa/",
                json={
                    'session_id': self.session_id,
                    'code_2fa': str(code_2fa).strip(),
                },
                timeout=30
            )
            
            result = r.json()
            
            if result.get('success'):
                self.authenticated = True
            
            return result
        except Exception as e:
            logger.error(f"2FA API error: {e}")
            return {'success': False, 'message': f'Lỗi xác minh 2FA: {str(e)}'}
    
    def purchase_subscription(self, tiktok_username, tier_id=None, adam_id=None):
        """
        Step 3: Execute subscription purchase via C69 backend.
        Backend handles: Apple Store purchase → Receipt → TikTok verification.
        
        Returns:
            dict: {success, message, tiktok_user, purchase_result, tiktok_verify}
        """
        if not self.session_id or not self.authenticated:
            return {'success': False, 'message': 'Apple Account chưa xác thực.'}
        
        try:
            r = self.session.post(
                f"{self.api_base}/api/apple-sub/purchase/",
                json={
                    'session_id': self.session_id,
                    'tiktok_username': tiktok_username,
                    'tier_id': tier_id or '',
                    'adam_id': adam_id or '',
                },
                timeout=60
            )
            
            return r.json()
        except Exception as e:
            logger.error(f"Purchase API error: {e}")
            return {'success': False, 'message': f'Lỗi mua subscription: {str(e)}'}
    
    def lookup_tiktok_user(self, username):
        """Lookup TikTok user info via C69 backend."""
        try:
            r = self.session.get(
                f"{self.api_base}/api/apple-sub/tiktok-lookup/",
                params={'username': username},
                timeout=15
            )
            return r.json()
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_subscription_tiers(self, creator_id=None):
        """Get available subscription tiers via C69 backend."""
        try:
            params = {}
            if creator_id:
                params['creator_id'] = creator_id
            
            r = self.session.get(
                f"{self.api_base}/api/apple-sub/tiktok-tiers/",
                params=params,
                timeout=15
            )
            return r.json()
        except Exception as e:
            return {'success': False, 'tiers': [], 'message': str(e)}
    
    def list_accounts(self):
        """List all authenticated Apple accounts."""
        try:
            r = self.session.get(
                f"{self.api_base}/api/apple-sub/accounts/",
                timeout=15
            )
            return r.json()
        except Exception as e:
            return {'success': False, 'accounts': [], 'message': str(e)}


class AppleSubscriptionWorker(QThread):
    """
    PyQt5 Worker thread for full-cycle subscription automation.
    
    Flow:
    1. Login Apple ID → 2FA → Token
    2. Lookup TikTok user
    3. Purchase subscription via Apple Store
    4. Verify receipt with TikTok
    """
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, bool)  # (status_text, is_running)
    code_2fa_required_signal = pyqtSignal(str)  # session_id
    purchase_complete_signal = pyqtSignal(dict)  # result dict
    
    def __init__(
        self,
        apple_id,
        password,
        proxy,
        tiktok_username,
        tier_id=None,
        code2fa=None,
        api_base=None,
    ):
        super().__init__()
        self.apple_id = apple_id
        self.password = password
        self.proxy = proxy
        self.tiktok_username = tiktok_username
        self.tier_id = tier_id
        self.code2fa = code2fa
        self.client = AppleSubscriptionClient(api_base=api_base)
        self._session_id = None
    
    def set_2fa_code(self, code):
        """Set 2FA code after user input (called from main thread)."""
        self.code2fa = code
    
    def set_session_id(self, session_id):
        """Resume from existing session."""
        self._session_id = session_id
        self.client.session_id = session_id
    
    def run(self):
        self.log_signal.emit(f"🚀 Bắt đầu TikTok Subscription Automation...")
        self.log_signal.emit(f"   Apple ID: {self.apple_id}")
        self.log_signal.emit(f"   TikTok: @{self.tiktok_username.lstrip('@')}")
        self.log_signal.emit(f"   Proxy: {self.proxy or 'Direct'}")
        self.status_signal.emit("Đang xử lý...", True)
        
        # ── Step 1: Login Apple ID ──
        if not self._session_id:
            self.log_signal.emit(f"\n🔑 Bước 1: Đăng nhập Apple ID ({self.apple_id}) qua GrandSlam SRP-6a...")
            login_result = self.client.login_apple_id(self.apple_id, self.password, self.proxy)
            
            if login_result.get('requires_2fa'):
                self.log_signal.emit("⚠️ Apple yêu cầu xác minh 2FA!")
                self._session_id = login_result.get('session_id')
                self.client.session_id = self._session_id
                
                if not self.code2fa:
                    self.log_signal.emit("📲 Đang chờ mã 2FA từ người dùng...")
                    self.code_2fa_required_signal.emit(self._session_id)
                    self.status_signal.emit("Chờ 2FA", False)
                    return
            
            if not login_result.get('success') and not login_result.get('requires_2fa'):
                self.log_signal.emit(f"❌ Login thất bại: {login_result.get('message')}")
                self.status_signal.emit("Lỗi Login", False)
                return
            
            if login_result.get('success'):
                self.log_signal.emit("✅ Đăng nhập Apple ID thành công!")
                self._session_id = login_result.get('session_id')
                self.client.session_id = self._session_id
        
        # ── Step 1.5: Verify 2FA if code provided ──
        if self.code2fa:
            self.log_signal.emit(f"\n🔐 Bước 1.5: Xác minh mã 2FA ({self.code2fa})...")
            verify_result = self.client.verify_2fa(self.code2fa)
            
            if not verify_result.get('success'):
                self.log_signal.emit(f"❌ 2FA thất bại: {verify_result.get('message')}")
                self.status_signal.emit("Lỗi 2FA", False)
                return
            
            self.log_signal.emit("✅ Xác minh 2FA thành công! Token đã lưu.")
        
        # ── Step 2: Lookup TikTok User ──
        self.log_signal.emit(f"\n🎵 Bước 2: Tra cứu TikTok user @{self.tiktok_username.lstrip('@')}...")
        user_info = self.client.lookup_tiktok_user(self.tiktok_username)
        
        if user_info.get('success'):
            self.log_signal.emit(f"   ✅ Found: {user_info.get('nickname', '')} (ID: {user_info.get('user_id', 'N/A')})")
            self.log_signal.emit(f"   👥 Followers: {user_info.get('followers', 0):,}")
        else:
            self.log_signal.emit(f"   ⚠️ Lookup limited: {user_info.get('message', '')}")
        
        # ── Step 3: Purchase Subscription ──
        self.log_signal.emit(f"\n💰 Bước 3: Đang mua subscription gói {self.tier_id or 'default'}...")
        self.log_signal.emit(f"   🍎 Gửi request tới Apple iTunes Store (MZFinance)...")
        
        purchase_result = self.client.purchase_subscription(
            tiktok_username=self.tiktok_username,
            tier_id=self.tier_id,
        )
        
        if purchase_result.get('success'):
            self.log_signal.emit(f"\n🎉 ═══════════════════════════════════════════")
            self.log_signal.emit(f"🎉 SUBSCRIPTION THÀNH CÔNG!")
            self.log_signal.emit(f"🎉 TikTok: @{purchase_result.get('tiktok_user', {}).get('username', self.tiktok_username)}")
            self.log_signal.emit(f"🎉 TxID: {purchase_result.get('purchase_result', {}).get('transaction_id') or 'N/A'}")
            self.log_signal.emit(f"🎉 ═══════════════════════════════════════════\n")
            self.status_signal.emit("Hoàn thành ✅", True)
            self.purchase_complete_signal.emit(purchase_result)
        else:
            step = purchase_result.get('step', 'unknown')
            msg = purchase_result.get('message', 'Unknown error')
            self.log_signal.emit(f"❌ Thất bại tại bước '{step}': {msg}")
            self.status_signal.emit(f"Lỗi: {step}", False)
            self.purchase_complete_signal.emit(purchase_result)
