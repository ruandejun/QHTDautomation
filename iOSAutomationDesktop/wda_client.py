import requests

class WDAClient:
    def __init__(self, host="http://localhost", port=8100):
        self.base_url = f"{host}:{port}"
        self.session_id = None
        
    def check_status(self) -> bool:
        """Kiểm tra kết nối tới dịch vụ WDA trên điện thoại"""
        try:
            r = requests.get(f"{self.base_url}/status", timeout=5)
            return r.status_code == 200
        except Exception:
            return False
            
    def start_session(self) -> bool:
        """Bắt đầu một phiên điều khiển tự động"""
        payload = {
            "capabilities": {}
        }
        try:
            r = requests.post(f"{self.base_url}/session", json=payload, timeout=10)
            if r.status_code == 200:
                data = r.json()
                # Thử lấy sessionId theo nhiều định dạng phản hồi khác nhau của WDA
                self.session_id = data.get("sessionId")
                if not self.session_id:
                    self.session_id = data.get("value", {}).get("sessionId")
                return self.session_id is not None
        except Exception as e:
            print(f"Failed to start session: {e}")
        return False
        
    def launch_app(self, bundle_id: str) -> bool:
        """Mở ứng dụng trên điện thoại bằng Bundle ID"""
        if not self.session_id:
            if not self.start_session():
                return False
        payload = {
            "bundleId": bundle_id
        }
        try:
            r = requests.post(f"{self.base_url}/session/{self.session_id}/wda/apps/launch", json=payload, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print(f"Failed to launch app: {e}")
            return False
            
    def swipe(self, from_x: float, from_y: float, to_x: float, to_y: float, duration_ms: int = 500) -> bool:
        """Mô phỏng thao tác vuốt màn hình"""
        if not self.session_id:
            return False
        payload = {
            "fromX": from_x,
            "fromY": from_y,
            "toX": to_x,
            "toY": to_y,
            "duration": duration_ms / 1000.0 # WDA yêu cầu giây (float)
        }
        try:
            r = requests.post(f"{self.base_url}/session/{self.session_id}/wda/drag", json=payload, timeout=10)
            return r.status_code == 200
        except Exception as e:
            print(f"Failed to swipe: {e}")
            return False
            
    def go_home(self) -> bool:
        """Bấm nút Home vật lý / thoát màn hình chính"""
        if not self.session_id:
            return False
        try:
            r = requests.post(f"{self.base_url}/session/{self.session_id}/wda/homescreen", timeout=10)
            return r.status_code == 200
        except Exception as e:
            print(f"Failed to go home: {e}")
            return False
            
    def get_window_size(self) -> dict:
        """Lấy kích thước màn hình của điện thoại (points)"""
        if not self.session_id:
            return {"width": 375, "height": 812}
        try:
            r = requests.get(f"{self.base_url}/session/{self.session_id}/window/size", timeout=5)
            if r.status_code == 200:
                return r.json().get("value", {"width": 375, "height": 812})
        except Exception as e:
            print(f"Failed to get window size: {e}")
        return {"width": 375, "height": 812}

    def close_session(self) -> bool:
        """Đóng phiên điều khiển hiện tại"""
        if not self.session_id:
            return True
        try:
            r = requests.delete(f"{self.base_url}/session/{self.session_id}", timeout=5)
            self.session_id = None
            return r.status_code == 200
        except Exception:
            return False

