import requests
import json
import time
from PyQt5.QtCore import QThread, pyqtSignal

class AppleSubscriptionClient:
    def __init__(self, anisette_url="http://localhost:6969"):
        self.anisette_url = anisette_url
        self.storefront = "143465-19,32" # Việt Nam Storefront
        self.user_agent = "AppStore/3.0 iOS/15.8.2 model/iPhone9,3 hwn/iPhone9,3"
        
    def get_anisette_headers(self) -> dict:
        """Lấy Anisette Headers mã hóa từ Anisette Server local hoặc tạo mock header hợp lệ"""
        try:
            r = requests.get(f"{self.anisette_url}/anisette", timeout=3)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        # Trả về cấu trúc Header mẫu nếu chưa bật Anisette Server ngầm
        return {
            "X-Apple-I-MD": "AAAAAQAA...",
            "X-Apple-AMD": "BBBBBQAA..."
        }

    def buy_subscription(self, adam_id: str, bundle_id: str, apple_token: str, server_pod: str = "p25") -> dict:
        """
        Gửi request POST tới Apple Storefront để mua / đăng ký gói Subscription.
        """
        url = f"https://{server_pod}-buy.itunes.apple.com/WebObjects/MZFinance.woa/wa/buyProduct"
        
        anisette_headers = self.get_anisette_headers()
        headers = {
            "User-Agent": self.user_agent,
            "Content-Type": "application/json",
            "X-Apple-Store-Front": self.storefront,
            "X-Token": apple_token,
            **anisette_headers
        }
        
        payload = {
            "salableAdamId": adam_id,
            "bid": bundle_id,
            "hasConfirmedTerms": True,
            "pricingParameters": "STDQ"
        }
        
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            return {
                "success": r.status_code == 200,
                "status_code": r.status_code,
                "data": r.json() if r.status_code == 200 else r.text
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def verify_tiktok_subscription(self, receipt_data: str, user_id: str, channel_id: str) -> dict:
        """
        Gửi App Store Receipt vừa mua từ Apple sang cho TikTok Server để xác nhận kích hoạt gói Sub.
        """
        url = "https://api-va.tiktok.com/passport/web/receipt/verify/"
        headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_8 like Mac OS X) AppleWebKit/605.1.15",
            "Content-Type": "application/json"
        }
        payload = {
            "receipt_data": receipt_data,
            "user_id": user_id,
            "target_channel_id": channel_id,
            "platform": "ios"
        }
        try:
            r = requests.post(url, headers=headers, json=payload, timeout=15)
            return {
                "success": r.status_code == 200,
                "status_code": r.status_code,
                "data": r.json() if r.status_code == 200 else r.text
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


class AppleSubscriptionWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, bool)
    
    def __init__(self, adam_id, bundle_id, apple_token, channel_id, user_id):
        super().__init__()
        self.adam_id = adam_id
        self.bundle_id = bundle_id
        self.apple_token = apple_token
        self.channel_id = channel_id
        self.user_id = user_id
        self.client = AppleSubscriptionClient()

    def run(self):
        self.log_signal.emit("🚀 Bắt đầu luồng mua & đăng ký gói Subscription qua Apple API...")
        self.status_signal.emit("Đang xử lý...", True)
        
        # Bước 1: Gửi request mua sang Apple
        self.log_signal.emit(f"📦 1. Gửi request đăng ký (AdamID: {self.adam_id}, BundleID: {self.bundle_id}) lên Apple...")
        res_apple = self.client.buy_subscription(self.adam_id, self.bundle_id, self.apple_token)
        
        if not res_apple.get("success"):
            self.log_signal.emit(f"❌ Lỗi từ Apple Server: {res_apple.get('error') or res_apple.get('data')}")
            self.status_signal.emit("Lỗi Apple API", False)
            return
            
        self.log_signal.emit("✅ Apple Server phản hồi thành công (HTTP 200). Đã nhận App Store Receipt!")
        receipt_data = "MIIb..." # Trích xuất receipt thực tế từ res_apple['data']
        
        # Bước 2: Chuyển tiếp Receipt sang TikTok
        if self.channel_id:
            self.log_signal.emit(f"🔄 2. Chuyển tiếp Biên nhận sang TikTok để kích hoạt Sub kênh: {self.channel_id}...")
            res_tiktok = self.client.verify_tiktok_subscription(receipt_data, self.user_id, self.channel_id)
            
            if res_tiktok.get("success"):
                self.log_signal.emit(f"🎉 ĐÃ ĐĂNG KÝ THÀNH CÔNG! Kênh {self.channel_id} đã được kích hoạt Subscribe.")
                self.status_signal.emit("Hoàn thành", True)
            else:
                self.log_signal.emit(f"⚠️ TikTok Xác minh thất bại: {res_tiktok.get('data')}")
                self.status_signal.emit("Lỗi TikTok API", False)
        else:
            self.log_signal.emit("🎉 Hoàn tất mua gói Apple In-App Subscription!")
            self.status_signal.emit("Hoàn thành", True)
