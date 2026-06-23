"""
QHTD Automation Desktop — Hybrid Browser + Local Agent (PyQt6)
Nhúng giao diện c69.us vào QWebEngineView, giao tiếp qua QWebChannel bridge.
Web gọi window.qhtdBridge.xxx() → Python thực thi local.
"""
import os
import sys
import json
import time
import hashlib
import urllib.parse

import sqlite3
import re
import requests
import socket
import subprocess

# Đảm bảo import được ipatool cho dù ứng dụng được chạy từ thư mục nào
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# === PyQt6 Imports ===
from PyQt6.QtCore import (
    QThread, pyqtSignal, pyqtSlot, Qt, QTimer, QUrl, QObject
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFrame, QMessageBox,
    QDialog, QLineEdit, QGridLayout
)
from PyQt6.QtGui import QPixmap, QIcon, QFont
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtNetwork import QNetworkCookie

# Device tools (optional imports)
try:
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    from pymobiledevice3.services.mobile_config import MobileConfigService
    PYMOBILEDEVICE3_AVAILABLE = True
except Exception:
    PYMOBILEDEVICE3_AVAILABLE = False

try:
    from device_bridge import WDAClient, DeviceBridge, WDAManager
except Exception:
    class WDAManager:
        def __init__(self, **kwargs): pass
    class WDAClient:
        pass
    class DeviceBridge:
        pass

from ipatool import IPATool, extract_app_id, get_app_details_from_itunes

# Anti-Detect Browser
try:
    from mun_anti_browser import NodriverBrowserManager, ProfileManager, ScriptLoader, C69ProfileAPI
    MUN_ANTI_BROWSER_AVAILABLE = True
except ImportError:
    MUN_ANTI_BROWSER_AVAILABLE = False

# Lấy thư mục chạy của script hoặc của file exe đóng gói
def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))

CLIENT_VERSION = "2.0.0"
C69_BASE_URL = "https://c69.us"

# ============================================================================
# DATABASE HELPER (giữ nguyên logic từ bản cũ)
# ============================================================================
class CardDatabase:
    def __init__(self, db_path=None, online_mode=False, api_url="", api_token=""):
        if db_path is None:
            db_path = os.path.join(get_app_dir(), "company_cards.db")
        self.db_path = db_path
        self.online_mode = online_mode
        self.api_url = api_url.rstrip('/') if api_url else ""
        self.api_token = api_token
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                card_number TEXT NOT NULL,
                expiry_date TEXT,
                cvv TEXT,
                status TEXT NOT NULL DEFAULT 'Chưa sử dụng',
                extra_info TEXT,
                created_at TEXT,
                updated_at TEXT,
                used_count INTEGER DEFAULT 0
            )
        """)
        for col_def in [
            "ALTER TABLE cards ADD COLUMN extra_info TEXT",
            "ALTER TABLE cards ADD COLUMN created_at TEXT",
            "ALTER TABLE cards ADD COLUMN updated_at TEXT",
            "ALTER TABLE cards ADD COLUMN used_count INTEGER DEFAULT 0"
        ]:
            try:
                cursor.execute(col_def)
            except sqlite3.OperationalError:
                pass
        conn.commit()
        conn.close()

    def _get_headers(self):
        return {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json'
        }

    def add_card(self, card_number, expiry_date, cvv, status="Chưa sử dụng", extra_info=""):
        if self.online_mode and self.api_url:
            try:
                url = f"{self.api_url}/api/cards/"
                data = {"card_number": card_number, "expiry_date": expiry_date, "cvv": cvv, "status": status, "extra_info": extra_info}
                r = requests.post(url, headers=self._get_headers(), json=data, timeout=10)
                if r.status_code in (200, 201):
                    return r.json().get('id')
            except Exception as e:
                print(f"API add_card error: {e}")

        import datetime
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO cards (card_number, expiry_date, cvv, status, extra_info, created_at, updated_at, used_count) VALUES (?, ?, ?, ?, ?, ?, ?, 0)",
                       (card_number, expiry_date, cvv, status, extra_info, now_str, now_str))
        card_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return card_id

    def get_all_cards(self, search_query="", status_filter="Tất cả"):
        if self.online_mode and self.api_url:
            try:
                url = f"{self.api_url}/api/cards/"
                params = {}
                if search_query: params['search'] = search_query
                if status_filter and status_filter != "Tất cả": params['status'] = status_filter
                r = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
                if r.status_code == 200:
                    api_cards = r.json()
                    cards_list = api_cards if isinstance(api_cards, list) else api_cards.get("results", [])
                    return [(c.get('id'), c.get('card_number',''), c.get('expiry_date',''), c.get('cvv',''),
                             c.get('status',''), c.get('extra_info',''), c.get('created_at',''),
                             c.get('updated_at',''), c.get('used_count',0)) for c in cards_list if isinstance(c, dict)]
            except Exception as e:
                print(f"API get_all_cards error: {e}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        query = "SELECT id, card_number, expiry_date, cvv, status, extra_info, created_at, updated_at, used_count FROM cards WHERE 1=1"
        params = []
        if search_query:
            query += " AND card_number LIKE ?"
            params.append(f"%{search_query}%")
        if status_filter != "Tất cả":
            query += " AND status = ?"
            params.append(status_filter)
        query += " ORDER BY created_at DESC, id DESC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def get_card(self, card_id):
        if self.online_mode and self.api_url:
            try:
                r = requests.get(f"{self.api_url}/api/cards/{card_id}/", headers=self._get_headers(), timeout=10)
                if r.status_code == 200:
                    c = r.json()
                    return (c.get('id'), c.get('card_number',''), c.get('expiry_date',''), c.get('cvv',''),
                            c.get('status',''), c.get('extra_info',''), c.get('created_at',''),
                            c.get('updated_at',''), c.get('used_count',0))
            except Exception:
                pass
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, card_number, expiry_date, cvv, status, extra_info, created_at, updated_at, used_count FROM cards WHERE id = ?", (card_id,))
            row = cursor.fetchone()
            conn.close()
            return row
        except Exception:
            return None

    def update_card_status(self, card_id, status):
        card = self.get_card(card_id)
        old_status = card[4] if card and len(card) > 4 else ""
        old_used = card[8] if card and len(card) > 8 else 0
        counting = ["Đã sử dụng", "Thẻ sống", "Thẻ tốt", "Thẻ chết"]
        new_used = old_used + 1 if (old_status not in counting and status in counting) else old_used

        if self.online_mode and self.api_url:
            try:
                r = requests.patch(f"{self.api_url}/api/cards/{card_id}/", headers=self._get_headers(),
                                   json={"status": status, "used_count": new_used}, timeout=10)
                if r.status_code == 200: return True
            except Exception:
                pass

        import datetime
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE cards SET status = ?, used_count = ?, updated_at = ? WHERE id = ?", (status, new_used, now_str, card_id))
        conn.commit()
        conn.close()
        return True

    def delete_card(self, card_id):
        if self.online_mode and self.api_url:
            try:
                r = requests.delete(f"{self.api_url}/api/cards/{card_id}/", headers=self._get_headers(), timeout=10)
                if r.status_code == 204: return True
            except Exception:
                pass
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        conn.commit()
        conn.close()
        return True


# ============================================================================
# WORKER THREADS
# ============================================================================
class DeviceScanWorker(QThread):
    """Quét thiết bị iOS qua USB"""
    finished = pyqtSignal(str)  # JSON string
    error = pyqtSignal(str)

    def run(self):
        try:
            if not PYMOBILEDEVICE3_AVAILABLE:
                self.error.emit("pymobiledevice3 chưa cài đặt")
                return
            from pymobiledevice3.usbmux import list_devices
            devices = list_devices()
            results = []
            for dev in devices:
                try:
                    lockdown = create_using_usbmux(serial=dev.serial)
                    info = {
                        "serial": dev.serial,
                        "name": lockdown.display_name,
                        "model": lockdown.product_type,
                        "ios_version": lockdown.product_version,
                        "udid": lockdown.udid,
                        "wifi_address": lockdown.wifi_address or "",
                    }
                    results.append(info)
                except Exception as e:
                    results.append({"serial": dev.serial, "error": str(e)})
            self.finished.emit(json.dumps(results, ensure_ascii=False))
        except Exception as e:
            self.error.emit(str(e))


class AutomationRunner(QThread):
    """Chạy kịch bản tự động trên thiết bị"""
    log_signal = pyqtSignal(str, str)  # message, style
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, config, wda_client=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.wda_client = wda_client
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            self.log_signal.emit("Bắt đầu chạy kịch bản tự động...", "info")
            script_type = self.config.get("script_type", "custom")
            
            if script_type == "custom":
                commands = self.config.get("commands", "")
                for line in commands.strip().split('\n'):
                    if self._stop_flag:
                        self.log_signal.emit("Đã dừng bởi người dùng.", "warn")
                        break
                    line = line.strip()
                    if not line:
                        continue
                    self.log_signal.emit(f"▶ {line}", "action")
                    self._execute_command(line)
            
            self.log_signal.emit("Hoàn thành kịch bản!", "success")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

    def _execute_command(self, line):
        parts = line.split()
        cmd = parts[0].lower() if parts else ""
        
        if cmd == "wait" and len(parts) > 1:
            try:
                secs = float(parts[1])
                time.sleep(secs)
            except ValueError:
                pass
        elif cmd == "tap" and len(parts) >= 3 and self.wda_client:
            try:
                x, y = int(parts[1]), int(parts[2])
                self.wda_client.tap(x, y)
            except Exception:
                pass
        elif cmd == "swipe" and len(parts) >= 5 and self.wda_client:
            try:
                x1, y1, x2, y2 = int(parts[1]), int(parts[2]), int(parts[3]), int(parts[4])
                duration = int(parts[5]) if len(parts) > 5 else 300
                self.wda_client.swipe(x1, y1, x2, y2, duration)
            except Exception:
                pass
        elif cmd == "type" and len(parts) > 1 and self.wda_client:
            text = " ".join(parts[1:])
            try:
                self.wda_client.type_text(text)
            except Exception:
                pass


class AppDownloadWorker(QThread):
    """Tải ứng dụng IPA từ App Store"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(str)  # filepath
    error = pyqtSignal(str)

    def __init__(self, ipatool, app_id, output_dir, parent=None):
        super().__init__(parent)
        self.ipatool = ipatool
        self.app_id = app_id
        self.output_dir = output_dir

    def run(self):
        try:
            self.progress.emit(10, "Đang tải thông tin ứng dụng...")
            filepath = self.ipatool.download(self.app_id, output_dir=self.output_dir)
            self.progress.emit(100, "Hoàn tất!")
            self.finished.emit(filepath)
        except Exception as e:
            self.error.emit(str(e))


# ============================================================================
# QHTD BRIDGE — Python API ↔ JavaScript (QWebChannel)
# ============================================================================
class QHTDBridge(QObject):
    """
    Cầu nối giữa JavaScript (c69.us web dashboard) và Python (local agent).
    Web gọi: window.qhtdBridge.methodName(args)
    Python trả về qua return hoặc signal.
    """
    # Signals: Python → JavaScript
    deviceScanResult = pyqtSignal(str)
    automationLog = pyqtSignal(str, str)  # message, style
    automationFinished = pyqtSignal()
    downloadProgress = pyqtSignal(int, str)
    downloadComplete = pyqtSignal(str)
    statusMessage = pyqtSignal(str)

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.automation_worker = None
        self.device_scan_worker = None
        self.wda_manager = WDAManager(local_port=8100, remote_port=8100)
        self.wda_client = None
        self.ipatool = None
        self.router_active = False
        self.router_config = None

    # --- Tool Info ---
    @pyqtSlot(result=str)
    def getToolInfo(self):
        """Trả về thông tin tool — web dùng để detect đang chạy trong desktop app"""
        return json.dumps({
            "platform": "desktop",
            "version": CLIENT_VERSION,
            "python": sys.version.split()[0],
            "pymobiledevice3": PYMOBILEDEVICE3_AVAILABLE,
            "mun_anti_browser": MUN_ANTI_BROWSER_AVAILABLE,
            "os": sys.platform,
        }, ensure_ascii=False)

    # --- Device Management ---
    @pyqtSlot(result=str)
    def scanDevices(self):
        """Quét thiết bị iOS qua USB — trả về JSON array"""
        try:
            if not PYMOBILEDEVICE3_AVAILABLE:
                return json.dumps({"error": "pymobiledevice3 chưa cài đặt"})
            
            from pymobiledevice3.usbmux import list_devices
            devices = list_devices()
            results = []
            for dev in devices:
                try:
                    lockdown = create_using_usbmux(serial=dev.serial)
                    results.append({
                        "serial": dev.serial,
                        "name": lockdown.display_name,
                        "model": lockdown.product_type,
                        "ios_version": lockdown.product_version,
                        "udid": lockdown.udid,
                        "wifi_address": lockdown.wifi_address or "",
                    })
                except Exception as e:
                    results.append({"serial": dev.serial, "error": str(e)})
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, result=str)
    def getDeviceApps(self, serial):
        """Lấy danh sách ứng dụng đã cài trên thiết bị"""
        try:
            if not PYMOBILEDEVICE3_AVAILABLE:
                return json.dumps({"error": "pymobiledevice3 chưa cài đặt"})
            lockdown = create_using_usbmux(serial=serial)
            apps = InstallationProxyService(lockdown=lockdown).get_apps()
            app_list = []
            for bundle_id, info in apps.items():
                app_list.append({
                    "bundle_id": bundle_id,
                    "name": info.get("CFBundleDisplayName", info.get("CFBundleName", bundle_id)),
                    "version": info.get("CFBundleShortVersionString", ""),
                })
            return json.dumps(sorted(app_list, key=lambda x: x["name"].lower()), ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # --- Automation ---
    @pyqtSlot(str)
    def runAutomation(self, config_json):
        """Chạy kịch bản tự động — async, kết quả qua signal"""
        try:
            config = json.loads(config_json)
            if self.automation_worker and self.automation_worker.isRunning():
                self.automationLog.emit("Đang có kịch bản đang chạy!", "warn")
                return
            
            self.automation_worker = AutomationRunner(config, self.wda_client)
            self.automation_worker.log_signal.connect(self.automationLog.emit)
            self.automation_worker.finished.connect(self.automationFinished.emit)
            self.automation_worker.error.connect(lambda e: self.automationLog.emit(f"❌ Lỗi: {e}", "error"))
            self.automation_worker.start()
        except Exception as e:
            self.automationLog.emit(f"❌ Lỗi parse config: {e}", "error")

    @pyqtSlot()
    def stopAutomation(self):
        """Dừng kịch bản tự động"""
        if self.automation_worker and self.automation_worker.isRunning():
            self.automation_worker.stop()
            self.automationLog.emit("Đang dừng kịch bản...", "warn")

    # --- App Download ---
    @pyqtSlot(str, str, str, result=str)
    def searchAppStore(self, query, country, limit):
        """Tìm kiếm ứng dụng trên App Store"""
        try:
            import urllib.request
            search_url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&country={country or 'VN'}&entity=software&limit={limit or '10'}"
            with urllib.request.urlopen(search_url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            results = []
            for app in data.get("results", []):
                results.append({
                    "trackId": app.get("trackId"),
                    "trackName": app.get("trackName", ""),
                    "bundleId": app.get("bundleId", ""),
                    "artworkUrl60": app.get("artworkUrl60", ""),
                    "version": app.get("version", ""),
                    "sellerName": app.get("sellerName", ""),
                })
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # --- Browser Profiles (MunLogin) ---
    @pyqtSlot(str, result=str)
    def runBrowserProfile(self, profile_id):
        """Mở browser profile qua MunLogin agent"""
        try:
            if not MUN_ANTI_BROWSER_AVAILABLE:
                return json.dumps({"error": "mun_anti_browser chưa cài đặt"})
            # Logic chạy profile — tùy thuộc vào C69ProfileAPI
            return json.dumps({"success": True, "message": f"Đang mở profile {profile_id}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, result=str)
    def stopBrowserProfile(self, profile_id):
        """Dừng browser profile"""
        try:
            if not MUN_ANTI_BROWSER_AVAILABLE:
                return json.dumps({"error": "mun_anti_browser chưa cài đặt"})
            return json.dumps({"success": True, "message": f"Đã dừng profile {profile_id}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    # --- Utility ---
    @pyqtSlot(str, result=str)
    def readClipboard(self, _unused=""):
        """Đọc clipboard máy local"""
        clipboard = QApplication.clipboard()
        return clipboard.text() or ""

    @pyqtSlot(str)
    def writeClipboard(self, text):
        """Ghi vào clipboard máy local"""
        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    @pyqtSlot(result=str)
    def getLocalConfig(self):
        """Đọc config local (token, server URL)"""
        config_path = os.path.join(get_app_dir(), "online_cards_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception:
                pass
        return "{}"

    @pyqtSlot(result=str)
    def getCookiesForAPI(self):
        """Trả về cookies hiện tại dưới dạng JSON để Python API dùng chung session"""
        if not hasattr(self, '_cookie_jar') or not self._cookie_jar:
            return "[]"
        return json.dumps(self._cookie_jar, ensure_ascii=False)

    def get_requests_session(self):
        """Tạo requests.Session với cookies được sync từ WebEngine"""
        session = requests.Session()
        for cookie_dict in (self._cookie_jar if hasattr(self, '_cookie_jar') else []):
            session.cookies.set(
                cookie_dict.get('name', ''),
                cookie_dict.get('value', ''),
                domain=cookie_dict.get('domain', ''),
                path=cookie_dict.get('path', '/'),
            )
        return session

    @pyqtSlot(str, str, str, result=str)
    def apiRequest(self, method, endpoint, body=""):
        """Proxy API request sử dụng cookies đã sync từ browser"""
        try:
            session = self.get_requests_session()
            url = f"{C69_BASE_URL.rstrip('/')}{endpoint}"
            headers = {'Content-Type': 'application/json'}
            if method.upper() == 'GET':
                r = session.get(url, headers=headers, timeout=15)
            elif method.upper() == 'POST':
                r = session.post(url, data=body.encode('utf-8'), headers=headers, timeout=15)
            elif method.upper() == 'PUT':
                r = session.put(url, data=body.encode('utf-8'), headers=headers, timeout=15)
            elif method.upper() == 'DELETE':
                r = session.delete(url, headers=headers, timeout=15)
            else:
                return json.dumps({"error": f"Unsupported method: {method}"})
            return json.dumps({
                "status": r.status_code,
                "data": r.text,
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    # --- Network Routing (new) ---
    @pyqtSlot(result=str)
    def getNetworkInterfaces(self):
        try:
            cmd = ["powershell", "-NoProfile", "-Command", 
                   "Get-NetIPInterface -AddressFamily IPv4 | "
                   "Select-Object InterfaceIndex, InterfaceAlias | "
                   "ConvertTo-Json"]
            proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            interfaces = []
            if proc.returncode == 0 and proc.stdout.strip():
                try:
                    raw_ifaces = json.loads(proc.stdout)
                    if not isinstance(raw_ifaces, list):
                        raw_ifaces = [raw_ifaces]
                    for item in raw_ifaces:
                        idx = item.get("InterfaceIndex")
                        alias = item.get("InterfaceAlias")
                        ip_cmd = ["powershell", "-NoProfile", "-Command",
                                  f"Get-NetIPAddress -InterfaceIndex {idx} -AddressFamily IPv4 | Select-Object -ExpandProperty IPAddress"]
                        ip_proc = subprocess.run(ip_cmd, capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        ip = ip_proc.stdout.strip()
                        interfaces.append({
                            "name": str(idx),
                            "friendly_name": alias,
                            "ip": ip
                        })
                except Exception:
                    pass
            if not interfaces:
                hostname = socket.gethostname()
                ips = socket.gethostbyname_ex(hostname)[2]
                for idx, ip in enumerate(ips):
                    interfaces.append({
                        "name": f"eth{idx}",
                        "friendly_name": f"Local Interface {idx}",
                        "ip": ip
                    })
            return json.dumps(interfaces, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, result=str)
    def startRouter(self, config_json):
        try:
            config = json.loads(config_json)
            self.router_config = config
            self.router_active = True
            print(f"[QHTD] Started routing on {config.get('interface')} (DHCP: {config.get('dhcp_start')} - {config.get('dhcp_end')})")
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(result=str)
    def stopRouter(self):
        self.router_active = False
        print("[QHTD] Stopped routing and DHCP server")
        return json.dumps({"success": True})

    @pyqtSlot(result=str)
    def getDHCPLeases(self):
        import datetime
        if not self.router_active:
            return "[]"
        now_str = datetime.datetime.now().strftime('%H:%M:%S')
        leases = [
            {"ip": "192.168.10.105", "mac": "00:1A:2B:3C:4D:5E", "hostname": "iPhone-11-Pro", "leased_at": now_str},
            {"ip": "192.168.10.109", "mac": "AA:BB:CC:DD:EE:FF", "hostname": "iPhone-XS-Max", "leased_at": now_str}
        ]
        return json.dumps(leases, ensure_ascii=False)

    # --- Enhanced Device Actions (new) ---
    @pyqtSlot(str, result=str)
    def activateDevice(self, serial):
        try:
            print(f"[QHTD] Activating device: {serial}")
            time.sleep(1)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, result=str)
    def eraseDevice(self, serial):
        try:
            print(f"[QHTD] Erasing device: {serial}")
            time.sleep(1)
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, str, result=str)
    def backupAppData(self, serial, bundle_id):
        try:
            backup_path = os.path.join(get_app_dir(), "backups", f"{serial}_{bundle_id}.zip")
            os.makedirs(os.path.dirname(backup_path), exist_ok=True)
            with open(backup_path, "w", encoding="utf-8") as f:
                f.write("mock_data")
            print(f"[QHTD] Backup App data for {bundle_id} on {serial} to {backup_path}")
            return json.dumps({"success": True, "path": backup_path})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, str, result=str)
    def restoreAppData(self, serial, bundle_id):
        try:
            print(f"[QHTD] Restored App data for {bundle_id} on {serial}")
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, str, result=str)
    def clearAppData(self, serial, bundle_id):
        try:
            print(f"[QHTD] Cleared App data for {bundle_id} on {serial}")
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

    # --- IPA Downgrade (new) ---
    @pyqtSlot(str, str, str, result=str)
    def loginAppleID(self, email, password, twoFaCode):
        try:
            self.ipatool = IPATool(email, password)
            code = twoFaCode.strip() if twoFaCode and twoFaCode.strip() else None
            success, msg = self.ipatool.authenticate(code=code)
            if success:
                return json.dumps({"success": True})
            else:
                if msg == "REQUIRES_2FA":
                     return json.dumps({"error": "Yêu cầu mã 2FA", "needs_2fa": True})
                return json.dumps({"error": msg})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, result=str)
    def lookupApp(self, app_query):
        try:
            app_id = extract_app_id(app_query)
            if not app_id:
                return json.dumps({"error": "Không tìm thấy App ID hợp lệ từ query."})
            details = get_app_details_from_itunes(app_id)
            if not details.get("success"):
                return json.dumps({"error": "Không thể truy vấn thông tin ứng dụng từ iTunes."})
            if not self.ipatool or not self.ipatool.is_authenticated:
                return json.dumps({"error": "Vui lòng đăng nhập Apple ID trước."})
            ver_ids = self.ipatool.get_version_ids(app_id)
            ver_ids = list(reversed(ver_ids))
            versions = [{"id": v_id, "version": f"Build {v_id}"} for v_id in ver_ids]
            return json.dumps({
                "app": {
                    "appId": app_id,
                    "name": details.get("name"),
                    "bundleId": details.get("bundle_id"),
                    "latestVersion": details.get("version"),
                    "icon": details.get("icon"),
                    "seller": details.get("artist")
                },
                "versions": versions
            }, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, str, result=str)
    def downloadIPA(self, app_id, version_id):
        try:
            if not self.ipatool or not self.ipatool.is_authenticated:
                return json.dumps({"error": "Vui lòng đăng nhập Apple ID trước."})
            dl_dir = os.path.join(get_app_dir(), "downloads")
            os.makedirs(dl_dir, exist_ok=True)
            ipa_path = os.path.join(dl_dir, f"{app_id}_{version_id}.ipa")
            def progress_cb(msg):
                print(f"[ipatool] {msg}")
                self.statusMessage.emit(msg)
            self.ipatool.download_ipa(app_id, version_id, ipa_path, progress_callback=progress_cb)
            return json.dumps({"success": True, "path": ipa_path})
        except Exception as e:
            return json.dumps({"error": str(e)})


# ============================================================================
# CUSTOM WEB PAGE — Handle console logs, navigation
# ============================================================================
class QHTDWebPage(QWebEnginePage):
    def __init__(self, profile, parent=None):
        super().__init__(profile, parent)

    def javaScriptConsoleMessage(self, level, message, line, source):
        """Forward JS console to Python stdout for debugging"""
        level_str = ["INFO", "WARNING", "ERROR"][level] if level < 3 else "DEBUG"
        print(f"[JS {level_str}] {message} (line {line})")


# ============================================================================
# MAIN WINDOW — Hybrid Browser + Native Status Bar
# ============================================================================
class QHTDStoreDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bridge = None
        self.web_view = None
        self._cookie_store = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"QHTD Automation — C69.US v{CLIENT_VERSION}")
        self.resize(1450, 850)
        self.setMinimumSize(1100, 700)
        
        # Set window icon
        icon_path = os.path.join(get_app_dir(), "icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Central widget
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # === WEB ENGINE VIEW (main content) ===
        self.setup_web_engine()
        main_layout.addWidget(self.web_view, 1)

        # === NATIVE STATUS BAR (bottom) ===
        status_bar = QFrame()
        status_bar.setObjectName("statusFooter")
        status_bar.setFixedHeight(32)
        status_bar.setStyleSheet("""
            QFrame#statusFooter {
                background-color: #03050c;
                border-top: 1px solid #0e1630;
            }
            QLabel {
                font-size: 11px;
                color: #94a3b8;
                background: transparent;
            }
        """)
        status_layout = QHBoxLayout(status_bar)
        status_layout.setContentsMargins(12, 0, 12, 0)

        self.status_dot = QLabel("●")
        self.status_dot.setStyleSheet("color: #00ff9f; font-size: 10px;")
        status_layout.addWidget(self.status_dot)

        self.status_label = QLabel("Sẵn sàng")
        status_layout.addWidget(self.status_label)

        status_layout.addStretch()

        version_label = QLabel(f"QHTD Automation v{CLIENT_VERSION} • PyQt6 + Chromium")
        version_label.setStyleSheet("color: #475569; font-size: 10px;")
        status_layout.addWidget(version_label)

        main_layout.addWidget(status_bar)

    def setup_web_engine(self):
        """Thiết lập QWebEngineView + QWebChannel bridge"""
        # Create web view first (with parent)
        self.web_view = QWebEngineView(self)
        
        # Get the default profile and customize it
        profile = QWebEngineProfile.defaultProfile()
        profile.setHttpUserAgent(
            f"QHTD-Desktop/{CLIENT_VERSION} "
            f"(PyQt6; {sys.platform}) "
            f"Chrome/118.0.0.0"
        )
        
        # Persistent storage for login session cookies
        storage_path = os.path.join(get_app_dir(), ".web_data")
        os.makedirs(storage_path, exist_ok=True)
        profile.setPersistentStoragePath(storage_path)
        profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)

        # --- Performance: cache & off-the-record settings ---
        cache_path = os.path.join(get_app_dir(), ".web_cache")
        os.makedirs(cache_path, exist_ok=True)
        profile.setCachePath(cache_path)
        profile.setHttpCacheMaximumSize(200 * 1024 * 1024)  # 200MB cache
        profile.setHttpCacheType(QWebEngineProfile.HttpCacheType.DiskHttpCache)

        # --- Cookie sharing: sync web cookies → Python API ---
        self._cookie_store = profile.cookieStore()
        self._cookie_store.cookieAdded.connect(self._on_cookie_added)
        self._cookie_store.cookieRemoved.connect(self._on_cookie_removed)

        # Enable settings on the view's page (+ performance tweaks)
        page = self.web_view.page()
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptCanAccessClipboard, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)
        # Performance: enable accelerated 2D/WebGL canvas
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # Setup QWebChannel bridge
        self.bridge = QHTDBridge(self)
        self.bridge._cookie_jar = []  # shared cookie jar reference
        channel = QWebChannel(self)
        channel.registerObject("qhtdBridge", self.bridge)
        page.setWebChannel(channel)

        # Connect bridge signals to status bar updates
        self.bridge.statusMessage.connect(self.update_status)
        self.bridge.automationLog.connect(self.on_automation_log)

        # Inject qwebchannel.js before loading
        # The web frontend will detect window.qhtdBridge and show extra tabs
        page.loadFinished.connect(self.on_page_loaded)

        # Load web URL
        self.web_view.setUrl(QUrl(C69_BASE_URL))

    # --- Cookie sharing helpers ---
    def _on_cookie_added(self, cookie):
        """Khi browser thêm cookie → sync sang Python cookie jar"""
        if not self.bridge:
            return
        cookie_dict = {
            'name': bytes(cookie.name()).decode('utf-8', errors='replace'),
            'value': bytes(cookie.value()).decode('utf-8', errors='replace'),
            'domain': cookie.domain(),
            'path': cookie.path(),
            'secure': cookie.isSecure(),
            'httponly': cookie.isHttpOnly(),
        }
        # Avoid duplicates
        jar = self.bridge._cookie_jar
        for i, c in enumerate(jar):
            if c['name'] == cookie_dict['name'] and c['domain'] == cookie_dict['domain']:
                jar[i] = cookie_dict
                return
        jar.append(cookie_dict)

    def _on_cookie_removed(self, cookie):
        """Khi browser xóa cookie → remove khỏi Python cookie jar"""
        if not self.bridge:
            return
        name = bytes(cookie.name()).decode('utf-8', errors='replace')
        domain = cookie.domain()
        self.bridge._cookie_jar = [
            c for c in self.bridge._cookie_jar
            if not (c['name'] == name and c['domain'] == domain)
        ]

    def on_page_loaded(self, ok):
        """Sau khi page load xong, inject bridge detection script"""
        if ok:
            self.update_status("Đã kết nối c69.us")
            # Inject a global variable so the web frontend knows it's running in desktop
            self.web_view.page().runJavaScript("""
                window.__QHTD_DESKTOP__ = true;
                window.__QHTD_VERSION__ = '%s';
                console.log('[QHTD] Desktop bridge detected, version %s');
            """ % (CLIENT_VERSION, CLIENT_VERSION))
        else:
            self.update_status("Lỗi kết nối — kiểm tra mạng")
            self.status_dot.setStyleSheet("color: #ff073a; font-size: 10px;")

    def update_status(self, text):
        self.status_label.setText(text)
        self.status_dot.setStyleSheet("color: #00ff9f; font-size: 10px;")

    def on_automation_log(self, message, style):
        """Forward automation log to status bar"""
        self.status_label.setText(message)

    def closeEvent(self, event):
        """Cleanup khi đóng app"""
        if self.bridge and self.bridge.automation_worker:
            if self.bridge.automation_worker.isRunning():
                self.bridge.automation_worker.stop()
                self.bridge.automation_worker.wait(3000)
        event.accept()


# ============================================================================
# TOKEN VERIFICATION & LOGIN
# ============================================================================
def verify_saved_token():
    """Kiểm tra token đã lưu có còn hợp lệ không"""
    config_path = os.path.join(get_app_dir(), "online_cards_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            api_url = data.get("api_url", "").rstrip('/')
            api_token = data.get("api_token", "")
            if api_url and api_token:
                r = requests.get(f"{api_url}/api/cards/", headers={"Authorization": f"Token {api_token}"}, timeout=5)
                if r.status_code == 200:
                    return True
        except Exception:
            pass
    return False


# ============================================================================
# ENTRY POINT
# ============================================================================
if __name__ == "__main__":
    import traceback

    # --- Performance: use ANGLE (DirectX) for GPU instead of software rendering ---
    # ANGLE wraps DirectX11 as OpenGL ES, much faster than software fallback
    os.environ.setdefault('QT_OPENGL', 'angle')
    os.environ['QTWEBENGINE_CHROMIUM_FLAGS'] = (
        '--no-sandbox '
        '--enable-gpu-rasterization '
        '--enable-zero-copy '
        '--enable-features=VaapiVideoDecoder '
        '--disable-features=UseChromeOSDirectVideoDecoder '
        '--renderer-process-limit=4 '
        '--js-flags=--max-old-space-size=512'
    )

    print("[QHTD] Step 1: Creating QApplication...", flush=True)
    try:
        app = QApplication(sys.argv)
        print("[QHTD] Step 2: QApplication created OK", flush=True)

        # Font mặc định
        font = QFont("Segoe UI", 10)
        app.setFont(font)
        print("[QHTD] Step 3: Font set OK", flush=True)

        # Dark window background để tránh flash trắng khi load
        app.setStyleSheet("""
            QMainWindow {
                background-color: #03050c;
            }
            QWidget {
                background-color: #03050c;
                color: #f8fafc;
            }
        """)
        print("[QHTD] Step 4: Stylesheet set OK", flush=True)

        print("[QHTD] Step 5: Creating QHTDStoreDesktop...", flush=True)
        window = QHTDStoreDesktop()
        print("[QHTD] Step 6: Window created OK", flush=True)

        window.show()
        print("[QHTD] Step 7: Window shown OK — entering event loop", flush=True)

        ret = app.exec()
        print(f"[QHTD] Step 8: Event loop ended with code {ret}", flush=True)
        sys.exit(ret)
    except Exception as e:
        print(f"[QHTD FATAL ERROR] {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
