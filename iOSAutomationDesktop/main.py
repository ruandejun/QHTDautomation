import sys
import os
import random
import urllib.request

# Đảm bảo import chéo hoạt động tốt bất kể chạy từ đâu
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGroupBox, QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QPushButton, QTextEdit, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor

from worker import AutomationWorker
from wda_client import WDAClient
try:
    from iOSAutomationDesktop.apple_sub_client import AppleSubscriptionWorker
except ImportError:
    from apple_sub_client import AppleSubscriptionWorker


# CSS stylesheet cho giao diện sang trọng, hiện đại (Dark Theme)
QSS_STYLE = """
QMainWindow {
    background-color: #0d0e12;
}
QWidget {
    color: #e2e8f0;
    font-family: 'Segoe UI', -apple-system, Roboto, sans-serif;
    font-size: 13px;
}
QGroupBox {
    border: 1px solid #1e293b;
    border-radius: 8px;
    margin-top: 14px;
    background-color: #151821;
    font-weight: bold;
    color: #94a3b8;
    padding: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
    padding: 0 5px;
}
QLabel {
    color: #94a3b8;
    font-weight: 500;
}
QLineEdit, QComboBox, QSpinBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 6px 10px;
    color: #ffffff;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
    border: 1px solid #6366f1;
}
QPushButton {
    background-color: #4f46e5;
    border: none;
    color: white;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #4338ca;
}
QPushButton:pressed {
    background-color: #3730a3;
}
QPushButton:disabled {
    background-color: #1e293b;
    color: #64748b;
    border: 1px solid #334155;
}
QPushButton#checkConnBtn {
    background-color: #0f766e;
}
QPushButton#checkConnBtn:hover {
    background-color: #0d9488;
}
QPushButton#checkConnBtn:pressed {
    background-color: #115e59;
}
QPushButton#stopBtn {
    background-color: #dc2626;
}
QPushButton#stopBtn:hover {
    background-color: #b91c1c;
}
QPushButton#stopBtn:pressed {
    background-color: #991b1b;
}
QPushButton#clearLogBtn {
    background-color: #334155;
    font-size: 11px;
    padding: 4px 8px;
}
QPushButton#clearLogBtn:hover {
    background-color: #475569;
}
QTextEdit {
    background-color: #090a0f;
    border: 1px solid #1e293b;
    border-radius: 6px;
    padding: 10px;
    color: #38bdf8;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}
QCheckBox {
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #475569;
    background-color: #1e293b;
}
QCheckBox::indicator:checked {
    background-color: #6366f1;
    border: 1px solid #6366f1;
}
QFrame#statsCard {
    background-color: #090a0f;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 15px;
}
"""

class DownloadWorker(QThread):
    progress_signal = pyqtSignal(int)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, save_path):
        super().__init__()
        self.url = url
        self.save_path = save_path
        
    def run(self):
        try:
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)
            # Tải file sử dụng urllib
            def report_progress(block_num, block_size, total_size):
                if total_size > 0:
                    percent = int(block_num * block_size * 100 / total_size)
                    self.progress_signal.emit(min(percent, 100))
            
            urllib.request.urlretrieve(self.url, self.save_path, reporthook=report_progress)
            self.finished_signal.emit(self.save_path)
        except Exception as e:
            self.error_signal.emit(str(e))

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MunAutomation iOS Studio v1.0")
        self.resize(820, 580)
        self.setStyleSheet(QSS_STYLE)
        
        self.worker = None
        self.init_ui()
        self.setup_connections()
        self.load_config()

        
    def init_ui(self):
        # Widget trung tâm
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout chính chia làm 2 cột
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)
        
        # =========================================================================
        # CỘT TRÁI: CẤU HÌNH (Rộng khoảng 320px)
        # =========================================================================
        left_column = QWidget()
        left_layout = QVBoxLayout(left_column)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        left_column.setFixedWidth(330)
        
        # Tiêu đề ứng dụng
        title_label = QLabel("📱 MunAutomation iOS Studio")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")
        subtitle_label = QLabel("Tự động xem video trên iPhone qua WebDriverAgent USB")
        subtitle_label.setStyleSheet("font-size: 11px; color: #64748b;")
        
        left_layout.addWidget(title_label)
        left_layout.addWidget(subtitle_label)
        
        # Vạch phân cách ngang
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #1e293b;")
        left_layout.addWidget(sep)
        
        # 1. Cấu hình Kết Nối
        conn_group = QGroupBox("🔌 CẤU HÌNH KẾT NỐI USB")
        conn_grid = QVBoxLayout(conn_group)
        conn_grid.setSpacing(8)
        
        host_layout = QHBoxLayout()
        host_lbl = QLabel("Địa chỉ WDA:")
        self.host_input = QLineEdit("http://localhost")
        self.host_input.setPlaceholderText("http://localhost")
        host_layout.addWidget(host_lbl)
        host_layout.addWidget(self.host_input)
        
        port_layout = QHBoxLayout()
        port_lbl = QLabel("Cổng (Port):")
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(8100)
        port_layout.addWidget(port_lbl)
        port_layout.addWidget(self.port_spin)
        
        self.check_conn_btn = QPushButton("🔌 Kiểm Tra Kết Nối WDA")
        self.check_conn_btn.setObjectName("checkConnBtn")
        
        self.conn_status_badge = QLabel("⚪ Chưa kiểm tra")
        self.conn_status_badge.setStyleSheet("font-weight: bold; color: #94a3b8; font-size: 12px; margin-top: 4px;")
        
        conn_grid.addLayout(host_layout)
        conn_grid.addLayout(port_layout)
        conn_grid.addWidget(self.check_conn_btn)
        conn_grid.addWidget(self.conn_status_badge)
        
        left_layout.addWidget(conn_group)
        
        # 1.5. Tiện ích WebDriverAgent (WDA)
        wda_tool_group = QGroupBox("📦 TIỆN ÍCH WEBDRIVERAGENT")
        wda_tool_layout = QVBoxLayout(wda_tool_group)
        wda_tool_layout.setSpacing(8)
        
        repo_layout = QHBoxLayout()
        repo_lbl = QLabel("GitHub Repo:")
        self.repo_input = QLineEdit("ruandejun/antidetect-automatic")
        repo_layout.addWidget(repo_lbl)
        repo_layout.addWidget(self.repo_input)
        
        token_layout = QHBoxLayout()
        token_lbl = QLabel("GitHub Token:")
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setPlaceholderText("ghp_...")
        token_layout.addWidget(token_lbl)
        token_layout.addWidget(self.token_input)
        
        self.download_wda_btn = QPushButton("📥 Tải WDA về máy")
        self.download_wda_btn.setObjectName("checkConnBtn")
        
        wda_tool_layout.addLayout(repo_layout)
        wda_tool_layout.addLayout(token_layout)
        wda_tool_layout.addWidget(self.download_wda_btn)
        left_layout.addWidget(wda_tool_group)
        
        # 2. Cấu hình chạy tự động
        config_group = QGroupBox("⚙️ CẤU HÌNH CHẠY")
        config_grid = QVBoxLayout(config_group)
        config_grid.setSpacing(10)
        
        app_lbl = QLabel("Ứng dụng chạy:")
        self.app_combo = QComboBox()
        self.app_combo.addItem("TikTok (Quốc tế)", "com.zhiliaoapp.musically")
        self.app_combo.addItem("Douyin (Trung Quốc)", "com.ss.iphone.ugc.Aweme")
        self.app_combo.addItem("YouTube Shorts", "com.google.ios.youtube")
        self.app_combo.addItem("Facebook Reels", "com.facebook.Facebook")
        self.app_combo.addItem("Instagram Reels", "com.burbn.instagram")
        self.app_combo.addItem("Tự Nhập Bundle ID...", "custom")
        
        custom_app_lbl = QLabel("Nhập Bundle ID khác:")
        self.custom_app_input = QLineEdit()
        self.custom_app_input.setPlaceholderText("com.example.app")
        self.custom_app_input.setEnabled(False) # Chỉ bật khi chọn Custom
        
        delay_lbl = QLabel("Thời gian chờ vuốt (giây):")
        delay_layout = QHBoxLayout()
        self.delay_min_spin = QSpinBox()
        self.delay_min_spin.setRange(1, 999)
        self.delay_min_spin.setValue(5)
        delay_layout.addWidget(QLabel("Từ:"))
        delay_layout.addWidget(self.delay_min_spin)
        
        self.delay_max_spin = QSpinBox()
        self.delay_max_spin.setRange(1, 999)
        self.delay_max_spin.setValue(12)
        delay_layout.addWidget(QLabel("Đến:"))
        delay_layout.addWidget(self.delay_max_spin)
        
        self.randomize_cb = QCheckBox("Trộn ngẫu nhiên thời gian (Jitter)")
        self.randomize_cb.setChecked(True)
        
        config_grid.addWidget(app_lbl)
        config_grid.addWidget(self.app_combo)
        config_grid.addWidget(custom_app_lbl)
        config_grid.addWidget(self.custom_app_input)
        config_grid.addWidget(delay_lbl)
        config_grid.addLayout(delay_layout)
        config_grid.addWidget(self.randomize_cb)
        
        left_layout.addWidget(config_group)
        
        # 3. Mua & Đăng ký Sub Apple / TikTok via API
        sub_group = QGroupBox("🍎 TỰ ĐỘNG MUA & SUB SUBSCRIPTION APPLE")
        sub_grid = QVBoxLayout(sub_group)
        sub_grid.setSpacing(8)
        
        adam_layout = QHBoxLayout()
        adam_lbl = QLabel("Adam ID (Sub):")
        self.adam_input = QLineEdit()
        self.adam_input.setPlaceholderText("1479707472")
        adam_layout.addWidget(adam_lbl)
        adam_layout.addWidget(self.adam_input)
        
        tiktok_layout = QHBoxLayout()
        tiktok_lbl = QLabel("ID Kênh TikTok:")
        self.channel_input = QLineEdit()
        self.channel_input.setPlaceholderText("ID Kênh hoặc Username")
        tiktok_layout.addWidget(tiktok_lbl)
        tiktok_layout.addWidget(self.channel_input)
        
        self.run_sub_btn = QPushButton("🛍️ Gửi Request Mua & Sub TikTok")
        self.run_sub_btn.setObjectName("checkConnBtn")
        
        sub_grid.addLayout(adam_layout)
        sub_grid.addLayout(tiktok_layout)
        sub_grid.addWidget(self.run_sub_btn)
        
        left_layout.addWidget(sub_group)
        left_layout.addStretch()

        
        # =========================================================================
        # CỘT PHẢI: ĐIỀU KHIỂN & NHẬT KÝ
        # =========================================================================
        right_column = QWidget()
        right_layout = QVBoxLayout(right_column)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # 1. Bảng số liệu thống kê (Stats Card)
        stats_card = QFrame()
        stats_card.setObjectName("statsCard")
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.setContentsMargins(15, 10, 15, 10)
        stats_layout.setSpacing(4)
        
        stats_title = QLabel("TỔNG SỐ LƯỢT VUỐT")
        stats_title.setStyleSheet("font-size: 11px; font-weight: bold; color: #64748b; letter-spacing: 1px;")
        stats_title.setAlignment(Qt.AlignCenter)
        
        self.counter_label = QLabel("0")
        self.counter_label.setStyleSheet("font-size: 54px; font-weight: bold; color: #10b981;")
        self.counter_label.setAlignment(Qt.AlignCenter)
        
        stats_layout.addWidget(stats_title)
        stats_layout.addWidget(self.counter_label)
        
        right_layout.addWidget(stats_card)
        
        # 2. Các Nút Điều Khiển Chạy
        controls_layout = QHBoxLayout()
        self.start_btn = QPushButton("🚀 BẮT ĐẦU CHẠY")
        self.start_btn.setFixedHeight(45)
        self.start_btn.setStyleSheet("font-size: 14px;")
        
        self.stop_btn = QPushButton("🛑 DỪNG LẠI")
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.setFixedHeight(45)
        self.stop_btn.setStyleSheet("font-size: 14px;")
        self.stop_btn.setEnabled(False)
        
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        right_layout.addLayout(controls_layout)
        
        # 3. Console Log
        log_group = QGroupBox("📋 NHẬT KÝ HOẠT ĐỘNG (LOGS)")
        log_layout = QVBoxLayout(log_group)
        log_layout.setSpacing(8)
        
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        
        log_header_layout = QHBoxLayout()
        log_header_layout.addStretch()
        self.clear_log_btn = QPushButton("🧹 Xóa Nhật Ký")
        self.clear_log_btn.setObjectName("clearLogBtn")
        log_header_layout.addWidget(self.clear_log_btn)
        
        log_layout.addLayout(log_header_layout)
        log_layout.addWidget(self.log_console)
        
        right_layout.addWidget(log_group)
        
        # Thêm các cột vào Layout chính
        main_layout.addWidget(left_column)
        main_layout.addWidget(right_column)
        
        # Thêm log chào mừng
        self.append_log("✨ Chào mừng bạn đến với iOS AutoSwipe Studio!")
        self.append_log("👉 Hãy cắm iPhone, bật chạy WebDriverAgent và bấm 'Kiểm Tra Kết Nối WDA' để bắt đầu.")
        
    def setup_connections(self):
        # Combo box thay đổi
        self.app_combo.currentIndexChanged.connect(self.on_app_combo_changed)
        
        # Các nút bấm kích hoạt tính năng
        self.check_conn_btn.clicked.connect(self.check_connection)
        self.download_wda_btn.clicked.connect(self.start_wda_download)
        self.run_sub_btn.clicked.connect(self.start_apple_sub)
        self.start_btn.clicked.connect(self.start_automation)
        self.stop_btn.clicked.connect(self.stop_automation)
        self.clear_log_btn.clicked.connect(self.clear_logs)
        
        # Ràng buộc điều khiển Delay min <= max
        self.delay_min_spin.valueChanged.connect(self.on_delay_min_changed)
        self.delay_max_spin.valueChanged.connect(self.on_delay_max_changed)

    def start_apple_sub(self):
        adam_id = self.adam_input.text().strip() or "1479707472"
        channel_id = self.channel_input.text().strip()
        bundle_id = "com.ss.iphone.ugc.Ame" # TikTok Bundle ID
        apple_token = "MOCK_APPLE_SESSION_TOKEN"
        user_id = "user_789"
        
        self.append_log("🛍️ Khởi chạy luồng tự động mua & Sub TikTok...")
        self.sub_worker = AppleSubscriptionWorker(
            adam_id=adam_id,
            bundle_id=bundle_id,
            apple_token=apple_token,
            channel_id=channel_id,
            user_id=user_id
        )
        self.sub_worker.log_signal.connect(self.append_log)
        self.sub_worker.start()

        
    def on_app_combo_changed(self, index):
        # Bật/tắt ô nhập bundle ID tuỳ biến
        is_custom = self.app_combo.currentData() == "custom"
        self.custom_app_input.setEnabled(is_custom)
        if is_custom:
            self.custom_app_input.setFocus()
            
    def on_delay_min_changed(self, val):
        if val > self.delay_max_spin.value():
            self.delay_max_spin.setValue(val)
            
    def on_delay_max_changed(self, val):
        if val < self.delay_min_spin.value():
            self.delay_min_spin.setValue(val)
            
    def append_log(self, message):
        self.log_console.append(message)
        self.log_console.ensureCursorVisible()
        
    def clear_logs(self):
        self.log_console.clear()
        self.append_log("🧹 Đã làm sạch nhật ký.")
        
    def check_connection(self):
        host = self.host_input.text().strip()
        port = self.port_spin.value()
        
        self.append_log(f"🔍 Đang kiểm tra kết nối tới WDA ở địa chỉ {host}:{port}...")
        self.conn_status_badge.setText("🟡 Đang kết nối...")
        self.conn_status_badge.setStyleSheet("font-weight: bold; color: #f59e0b;")
        self.check_conn_btn.setEnabled(False)
        
        # Tạo luồng phụ để không treo UI khi check
        class ConnChecker(QThread):
            result = pyqtSignal(bool)
            def __init__(self, host, port):
                super().__init__()
                self.host = host
                self.port = port
            def run(self):
                client = WDAClient(host=self.host, port=self.port)
                self.result.emit(client.check_status())
                
        self.checker = ConnChecker(host, port)
        self.checker.result.connect(self.on_connection_checked)
        self.checker.start()
        
    def on_connection_checked(self, success):
        self.check_conn_btn.setEnabled(True)
        if success:
            self.append_log("✅ Kết nối WebDriverAgent thành công! Thiết bị đã sẵn sàng.")
            self.conn_status_badge.setText("🟢 Đã kết nối")
            self.conn_status_badge.setStyleSheet("font-weight: bold; color: #10b981;")
        else:
            self.append_log("❌ Không thể kết nối tới WebDriverAgent.")
            self.append_log("👉 Vui lòng kiểm tra lại: \n1. Đã bật WDA trên điện thoại chưa?\n2. Đã cắm cáp USB?\n3. Đã chạy cổng chuyển tiếp `iproxy 8100 8100` chưa?")
            self.conn_status_badge.setText("🔴 Lỗi kết nối")
            self.conn_status_badge.setStyleSheet("font-weight: bold; color: #ef4444;")
            
    def start_wda_download(self):
        repo = self.repo_input.text().strip()
        token = self.token_input.text().strip()
        
        if not repo:
            self.append_log("❌ Lỗi: Vui lòng nhập GitHub Repo!")
            return
            
        save_path = os.path.join(current_dir, "WebDriverAgentRunner.ipa")
        release_url = f"https://github.com/{repo}/releases/download/wda-build/WebDriverAgentRunner.ipa"
        
        self.append_log(f"🔍 Đang kiểm tra bản build WDA trên repo {repo}...")
        self.download_wda_btn.setEnabled(False)
        self.save_config()
        
        # Tạo luồng chạy kiểm tra và kích hoạt Action
        class GitHubBuildChecker(QThread):
            log_signal = pyqtSignal(str)
            status_signal = pyqtSignal(str) # 'download', 'error'
            
            def __init__(self, repo, token, url):
                super().__init__()
                self.repo = repo
                self.token = token
                self.url = url
                
            def run(self):
                import requests
                # 1. Thử kiểm tra xem Release có sẵn hay không
                try:
                    r = requests.head(self.url, allow_redirects=True, timeout=5)
                    if r.status_code == 200:
                        self.log_signal.emit("✅ Tìm thấy bản build WDA có sẵn trên Releases!")
                        self.status_signal.emit("download")
                        return
                except Exception:
                    pass
                    
                # 2. Nếu không có sẵn, cần token để kích hoạt build
                if not self.token:
                    self.log_signal.emit("❌ Không tìm thấy bản build WDA trên Releases.")
                    self.log_signal.emit("👉 Gợi ý: Vui lòng điền 'GitHub Token' (PAT) để phần mềm tự động kích hoạt build trên Actions.")
                    self.status_signal.emit("error")
                    return
                    
                # 3. Kích hoạt workflow_dispatch qua API
                self.log_signal.emit("🔄 Đang gửi yêu cầu kích hoạt GitHub Actions để build bản WDA mới nhất...")
                headers = {
                    "Authorization": f"token {self.token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "Mozilla/5.0"
                }
                
                trigger_url = f"https://api.github.com/repos/{self.repo}/actions/workflows/build-wda.yml/dispatches"
                payload = {"ref": "master"}
                
                try:
                    r_trig = requests.post(trigger_url, json=payload, headers=headers, timeout=10)
                    if r_trig.status_code == 404:
                        payload = {"ref": "main"}
                        r_trig = requests.post(trigger_url, json=payload, headers=headers, timeout=10)
                        
                    if r_trig.status_code not in [200, 204, 201]:
                        self.log_signal.emit(f"❌ Kích hoạt build thất bại. Mã lỗi: {r_trig.status_code}")
                        self.status_signal.emit("error")
                        return
                        
                    self.log_signal.emit("✅ Đã kích hoạt GitHub Actions thành công!")
                    self.log_signal.emit("⏳ Đang giám sát tiến trình build (quá trình này mất khoảng 2-3 phút)...")
                    
                    import time
                    runs_url = f"https://api.github.com/repos/{self.repo}/actions/runs?workflow_id=build-wda.yml"
                    
                    for attempt in range(40):
                        time.sleep(10)
                        r_runs = requests.get(runs_url, headers=headers, timeout=10)
                        if r_runs.status_code == 200:
                            runs = r_runs.json().get("workflow_runs", [])
                            if runs:
                                latest_run = runs[0]
                                status = latest_run.get("status")
                                conclusion = latest_run.get("conclusion")
                                self.log_signal.emit(f"📊 Trạng thái GitHub Actions: {status}" + (f" ({conclusion})" if conclusion else ""))
                                
                                if status == "completed":
                                    if conclusion == "success":
                                        self.log_signal.emit("✅ GitHub Actions build thành công!")
                                        self.status_signal.emit("download")
                                        return
                                    else:
                                        self.log_signal.emit(f"❌ GitHub Actions build thất bại: {conclusion}")
                                        self.status_signal.emit("error")
                                        return
                        else:
                            self.log_signal.emit(f"⚠️ Kiểm tra trạng thái lỗi: {r_runs.status_code}")
                            
                    self.log_signal.emit("❌ Quá thời gian chờ (Timeout).")
                    self.status_signal.emit("error")
                except Exception as e:
                    self.log_signal.emit(f"❌ Lỗi kết nối: {e}")
                    self.status_signal.emit("error")
                    
        self.checker_thread = GitHubBuildChecker(repo, token, release_url)
        self.checker_thread.log_signal.connect(self.append_log)
        self.checker_thread.status_signal.connect(self.on_build_status)
        self.checker_thread.start()
        
    def on_build_status(self, status):
        if status == "download":
            repo = self.repo_input.text().strip()
            release_url = f"https://github.com/{repo}/releases/download/wda-build/WebDriverAgentRunner.ipa"
            save_path = os.path.join(current_dir, "WebDriverAgentRunner.ipa")
            
            self.dl_worker = DownloadWorker(release_url, save_path)
            self.dl_worker.progress_signal.connect(self.on_download_progress)
            self.dl_worker.finished_signal.connect(self.on_download_finished)
            self.dl_worker.error_signal.connect(self.on_download_error)
            self.dl_worker.start()
        else:
            self.download_wda_btn.setEnabled(True)
            
    def on_download_progress(self, percent):
        if percent % 20 == 0:
            self.append_log(f"⏳ Tiến trình tải: {percent}%...")
            
    def on_download_finished(self, path):
        self.append_log(f"🎉 Tải thành công! File lưu tại: {path}")
        self.append_log("👉 Hãy kéo thả file này vào Sideloadly để ký và cài đặt lên điện thoại.")
        self.download_wda_btn.setEnabled(True)
        try:
            os.startfile(os.path.dirname(path))
        except Exception:
            pass
            
    def on_download_error(self, err_msg):
        self.append_log(f"❌ Lỗi tải file: {err_msg}")
        self.download_wda_btn.setEnabled(True)
        
    def load_config(self):
        import json
        config_path = os.path.join(current_dir, "config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.repo_input.setText(data.get("github_repo", "ruandejun/antidetect-automatic"))
                    self.token_input.setText(data.get("github_token", ""))
                    self.host_input.setText(data.get("wda_host", "http://localhost"))
                    self.port_spin.setValue(data.get("wda_port", 8100))
                    self.delay_min_spin.setValue(data.get("delay_min", 5))
                    self.delay_max_spin.setValue(data.get("delay_max", 12))
                    self.randomize_cb.setChecked(data.get("randomize", True))
            except Exception:
                pass
                
    def save_config(self):
        import json
        config_path = os.path.join(current_dir, "config.json")
        data = {
            "github_repo": self.repo_input.text().strip(),
            "github_token": self.token_input.text().strip(),
            "wda_host": self.host_input.text().strip(),
            "wda_port": self.port_spin.value(),
            "delay_min": self.delay_min_spin.value(),
            "delay_max": self.delay_max_spin.value(),
            "randomize": self.randomize_cb.isChecked()
        }
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass
            
    def get_selected_bundle_id(self):
        app_type = self.app_combo.currentData()
        if app_type == "custom":
            return self.custom_app_input.text().strip()
        return app_type
        
    def start_automation(self):
        host = self.host_input.text().strip()
        port = self.port_spin.value()
        bundle_id = self.get_selected_bundle_id()
        delay_min = self.delay_min_spin.value()
        delay_max = self.delay_max_spin.value()
        randomize = self.randomize_cb.isChecked()
        
        if self.app_combo.currentData() == "custom" and not bundle_id:
            self.append_log("❌ Lỗi: Vui lòng nhập Bundle ID hợp lệ!")
            return
            
        self.counter_label.setText("0")
        self.append_log("🚀 Khởi chạy chương trình tự động...")
        
        # Khởi chạy luồng Worker
        self.worker = AutomationWorker(
            host=host,
            port=port,
            bundle_id=bundle_id,
            delay_min=delay_min,
            delay_max=delay_max,
            randomize=randomize
        )
        
        # Kết nối tín hiệu
        self.worker.log_signal.connect(self.append_log)
        self.worker.count_signal.connect(self.update_counter)
        self.worker.status_signal.connect(self.update_run_status)
        
        # Bắt đầu chạy thread
        self.worker.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
    def stop_automation(self):
        if self.worker and self.worker.isRunning():
            self.append_log("⏳ Đang gửi yêu cầu dừng tự động hóa...")
            self.worker.requestInterruption()
            # Disable stop button to avoid double clicking
            self.stop_btn.setEnabled(False)
            
    def update_counter(self, count):
        self.counter_label.setText(str(count))
        
    def update_run_status(self, status, is_running):
        if not is_running:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.append_log(f"ℹ️ Luồng chạy kết thúc. Trạng thái: {status}")
            
    def closeEvent(self, event):
        # Lưu lại cấu hình trước khi đóng ứng dụng
        self.save_config()
        # Khi đóng cửa sổ, dừng thread nếu đang chạy để tránh sập app đột ngột
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption()
            self.worker.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Thiết lập giao diện hiển thị cao cấp, sắc nét
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # Thiết lập font chữ mặc định đẹp hơn
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
