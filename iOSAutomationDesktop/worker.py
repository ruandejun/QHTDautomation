import time
import random
from PyQt5.QtCore import QThread, pyqtSignal

try:
    from iOSAutomationDesktop.wda_client import WDAClient
except ImportError:
    from wda_client import WDAClient

class AutomationWorker(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, bool)
    count_signal = pyqtSignal(int)
    
    def __init__(self, host="http://localhost", port=8100, bundle_id="com.zhiliaoapp.musically", delay_min=5, delay_max=15, randomize=True):
        super().__init__()
        self.host = host
        self.port = int(port)
        self.bundle_id = bundle_id
        self.delay_min = float(delay_min)
        self.delay_max = float(delay_max)
        self.randomize = randomize
        self.scroll_count = 0
        self.client = WDAClient(host=self.host, port=self.port)
        
    def run(self):
        self.log_signal.emit("🔄 Đang kiểm tra kết nối tới WebDriverAgent...")
        if not self.client.check_status():
            self.log_signal.emit("❌ Lỗi: Không thể kết nối tới WebDriverAgent.")
            self.log_signal.emit("👉 Gợi ý: Hãy chắc chắn bạn đã cắm iPhone qua USB, bật WebDriverAgent trên điện thoại và chạy cổng chuyển tiếp qua iproxy (Ví dụ: `iproxy 8100 8100`).")
            self.status_signal.emit("Chưa kết nối", False)
            return
            
        self.log_signal.emit("✅ Đã kết nối thành công tới WebDriverAgent.")
        self.log_signal.emit("🔄 Đang khởi tạo session điều khiển mới...")
        if not self.client.start_session():
            self.log_signal.emit("❌ Lỗi: Không thể khởi tạo session. Hãy thử khởi động lại WebDriverAgent trên điện thoại.")
            self.status_signal.emit("Lỗi Session", False)
            return
            
        self.log_signal.emit(f"✅ Khởi tạo session thành công. Session ID: {self.client.session_id}")
        self.status_signal.emit("Đang chạy", True)
        
        if self.bundle_id:
            self.log_signal.emit(f"📱 Đang mở ứng dụng có Bundle ID: {self.bundle_id}...")
            if self.client.launch_app(self.bundle_id):
                self.log_signal.emit(f"✅ Đã mở ứng dụng: {self.bundle_id}")
            else:
                self.log_signal.emit(f"⚠️ Cảnh báo: Không thể mở tự động. Hãy tự click mở ứng dụng {self.bundle_id} trên màn hình iPhone.")

        # Lấy kích thước màn hình
        self.log_signal.emit("📐 Đang lấy kích thước màn hình để tự động tính toán tọa độ...")
        size = self.client.get_window_size()
        width = size.get("width", 375)
        height = size.get("height", 812)
        self.log_signal.emit(f"📐 Kích thước màn hình: {width}x{height} points.")
        
        # Tọa độ vuốt
        from_x = width / 2
        from_y = height * 0.8
        to_x = width / 2
        to_y = height * 0.2
        
        self.log_signal.emit("🚀 Bắt đầu vòng lặp vuốt màn hình tự động...")
        while not self.isInterruptionRequested():
            self.log_signal.emit(f"👇 Thực hiện vuốt lần thứ {self.scroll_count + 1}...")
            
            # Thêm nhiễu ngẫu nhiên vào tọa độ để bắt chước hành vi người thật
            jitter_fx = from_x + random.uniform(-10, 10)
            jitter_fy = from_y + random.uniform(-20, 20)
            jitter_tx = to_x + random.uniform(-10, 10)
            jitter_ty = to_y + random.uniform(-20, 20)
            duration = random.randint(250, 400)
            
            if self.client.swipe(jitter_fx, jitter_fy, jitter_tx, jitter_ty, duration_ms=duration):
                self.scroll_count += 1
                self.count_signal.emit(self.scroll_count)
                self.log_signal.emit(f"✅ Vuốt thành công lần {self.scroll_count}.")
            else:
                self.log_signal.emit("❌ Lỗi: Vuốt thất bại. WebDriverAgent có thể đã bị ngắt kết nối.")
                break
                
            # Tính thời gian chờ ngẫu nhiên hoặc cố định
            if self.randomize:
                sleep_time = random.uniform(self.delay_min, self.delay_max)
            else:
                sleep_time = self.delay_min
                
            self.log_signal.emit(f"🕒 Chờ {sleep_time:.1f} giây trước khi xem tiếp...")
            
            # Ngủ ngắn quãng nhỏ để dễ dàng ngắt khi bấm STOP
            steps = int(sleep_time * 10)
            for _ in range(steps):
                if self.isInterruptionRequested():
                    break
                time.sleep(0.1)
                
        self.log_signal.emit("🛑 Đang đóng session và dừng luồng tự động...")
        self.client.close_session()
        self.log_signal.emit("👋 Đã dừng tự động hóa.")
        self.status_signal.emit("Đã dừng", False)
