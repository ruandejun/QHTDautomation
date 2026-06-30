"""
MunAutomation Desktop — Hybrid Browser + Local Agent (PyQt6)
Nhúng giao diện c69.us vào QWebEngineView, giao tiếp qua QWebChannel bridge.
Web gọi window.munAutomationBridge.xxx() (hoặc window.qhtdBridge) → Python thực thi local.
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
import asyncio

# Đảm bảo import được ipatool cho dù ứng dụng được chạy từ thư mục nào
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# === PyQt6 Imports ===
from PyQt6.QtCore import (
    QThread, pyqtSignal, pyqtSlot, Qt, QTimer, QUrl, QObject, QFile, QIODevice, QEventLoop, QDateTime
)
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QProgressBar, QFrame, QMessageBox,
    QDialog, QLineEdit, QGridLayout, QStackedWidget
)
from PyQt6.QtGui import QPixmap, QIcon, QFont, QColor
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
    from device_bridge import WDAClient, DeviceBridge, WDAManager, get_local_ip
except Exception:
    class WDAManager:
        def __init__(self, **kwargs): pass
    class WDAClient:
        pass
    class DeviceBridge:
        pass
    def get_local_ip():
        return "127.0.0.1"

from ipatool import IPATool, extract_app_id, get_app_details_from_itunes

# MunLogin Anti-Detect Browser Manager
try:
    from mun_anti_browser import NodriverBrowserManager, ProfileManager, ScriptLoader, C69ProfileAPI
    MUN_ANTI_BROWSER_AVAILABLE = True
except ImportError:
    MUN_ANTI_BROWSER_AVAILABLE = False

# Tor Manager
try:
    from tor_manager import download_and_extract_tor, is_tor_installed, tor_manager
    TOR_MANAGER_AVAILABLE = True
except ImportError:
    TOR_MANAGER_AVAILABLE = False

# === Win32 Network Helper (cải thiện hiệu năng định tuyến) ===
import ctypes
from ctypes import wintypes

try:
    iphlpapi = ctypes.WinDLL('iphlpapi.dll')
except Exception:
    iphlpapi = None

class MIB_IPFORWARDROW(ctypes.Structure):
    _fields_ = [
        ("dwForwardDest", wintypes.DWORD),
        ("dwForwardMask", wintypes.DWORD),
        ("dwForwardPolicy", wintypes.DWORD),
        ("dwForwardNextHop", wintypes.DWORD),
        ("dwForwardIfIndex", wintypes.DWORD),
        ("dwForwardType", wintypes.DWORD),
        ("dwForwardProto", wintypes.DWORD),
        ("dwForwardAge", wintypes.DWORD),
        ("dwForwardNextHopAS", wintypes.DWORD),
        ("dwForwardMetric1", wintypes.DWORD),
        ("dwForwardMetric2", wintypes.DWORD),
        ("dwForwardMetric3", wintypes.DWORD),
        ("dwForwardMetric4", wintypes.DWORD),
        ("dwForwardMetric5", wintypes.DWORD),
    ]

class NET_LUID(ctypes.Structure):
    _fields_ = [("Value", ctypes.c_uint64)]

IF_MAX_STRING_SIZE = 256

if iphlpapi:
    iphlpapi.ConvertInterfaceAliasToLuid.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(NET_LUID)]
    iphlpapi.ConvertInterfaceAliasToLuid.restype = wintypes.ULONG

    iphlpapi.ConvertInterfaceLuidToIndex.argtypes = [ctypes.POINTER(NET_LUID), ctypes.POINTER(wintypes.ULONG)]
    iphlpapi.ConvertInterfaceLuidToIndex.restype = wintypes.ULONG

    iphlpapi.ConvertInterfaceIndexToLuid.argtypes = [wintypes.ULONG, ctypes.POINTER(NET_LUID)]
    iphlpapi.ConvertInterfaceIndexToLuid.restype = wintypes.ULONG

    iphlpapi.ConvertInterfaceLuidToAlias.argtypes = [ctypes.POINTER(NET_LUID), ctypes.c_wchar_p, ctypes.c_size_t]
    iphlpapi.ConvertInterfaceLuidToAlias.restype = wintypes.ULONG

    iphlpapi.GetBestRoute.argtypes = [wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(MIB_IPFORWARDROW)]
    iphlpapi.GetBestRoute.restype = wintypes.DWORD

def win32_get_best_interface_index(dest_ip: str = "8.8.8.8") -> int:
    if not iphlpapi:
        return None
    try:
        import socket
        import struct
        dest_addr = struct.unpack("I", socket.inet_aton(dest_ip))[0]
        row = MIB_IPFORWARDROW()
        res = iphlpapi.GetBestRoute(dest_addr, 0, ctypes.byref(row))
        if res == 0:
            return row.dwForwardIfIndex
    except Exception:
        pass
    return None

def win32_alias_to_index(alias: str) -> int:
    if not iphlpapi or not alias:
        return None
    try:
        luid = NET_LUID()
        res = iphlpapi.ConvertInterfaceAliasToLuid(alias, ctypes.byref(luid))
        if res != 0:
            return None
        idx = wintypes.ULONG()
        res = iphlpapi.ConvertInterfaceLuidToIndex(ctypes.byref(luid), ctypes.byref(idx))
        if res != 0:
            return None
        return idx.value
    except Exception:
        return None

def win32_index_to_alias(index: int) -> str:
    if not iphlpapi or index is None:
        return None
    try:
        luid = NET_LUID()
        res = iphlpapi.ConvertInterfaceIndexToLuid(index, ctypes.byref(luid))
        if res != 0:
            return None
        buf = ctypes.create_unicode_buffer(IF_MAX_STRING_SIZE + 1)
        res = iphlpapi.ConvertInterfaceLuidToAlias(ctypes.byref(luid), buf, IF_MAX_STRING_SIZE + 1)
        if res != 0:
            return None
        return buf.value
    except Exception:
        return None

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
# HELPER FOR ASYNC/SYNC COMPATIBILITY (pymobiledevice3 async version compatibility)
# ============================================================================
def run_async_or_sync(func, *args, **kwargs):
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return asyncio.run(func(*args, **kwargs))
    else:
        res = func(*args, **kwargs)
        if asyncio.iscoroutine(res):
            return asyncio.run(res)
        return res


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
            from pymobiledevice3.lockdown import create_using_usbmux

            async def scan_async():
                devices = await list_devices()
                results = []
                for dev in devices:
                    try:
                        lockdown = await create_using_usbmux(serial=dev.serial)
                        results.append({
                            "serial": dev.serial,
                            "name": getattr(lockdown, "display_name", "iPhone"),
                            "model": getattr(lockdown, "product_type", "Unknown"),
                            "ios_version": getattr(lockdown, "product_version", "Unknown"),
                            "udid": getattr(lockdown, "udid", dev.serial),
                            "wifi_address": getattr(lockdown, "wifi_address", "") or "",
                        })
                    except Exception as e:
                        results.append({"serial": dev.serial, "error": str(e)})
                return results

            results = run_async_or_sync(scan_async)
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
        elif cmd == "launch_app" and len(parts) > 1 and self.wda_client:
            bundle_id = parts[1]
            try:
                self.wda_client.launch_app(bundle_id)
            except Exception:
                pass
        elif cmd == "home" and self.wda_client:
            try:
                self.wda_client.go_home()
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


class WDASetupWorker(QThread):
    log_signal = pyqtSignal(str, str)  # message, style
    finished_signal = pyqtSignal(bool, str)  # success, message

    def __init__(self, wda_manager, serial, ipa_path, parent=None):
        super().__init__(parent)
        self.wda_manager = wda_manager
        self.serial = serial
        self.ipa_path = ipa_path

    def run(self):
        try:
            def log_cb(msg):
                style = "info"
                if "🟢" in msg or "✅" in msg:
                    style = "success"
                elif "❌" in msg or "⚠️" in msg:
                    style = "error"
                elif "🚀" in msg or "👉" in msg or "⏳" in msg or "🔄" in msg:
                    style = "action"
                self.log_signal.emit(msg, style)

            success = self.wda_manager.auto_setup(self.serial, self.ipa_path, log_cb=log_cb)
            if success:
                self.finished_signal.emit(True, "WebDriverAgent đã thiết lập thành công!")
            else:
                self.finished_signal.emit(False, "Thiết lập WebDriverAgent thất bại.")
        except Exception as e:
            self.log_signal.emit(f"❌ Lỗi: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))


class WebServerWorker(QThread):
    started = pyqtSignal(str, int)  # ip, port
    
    def __init__(self, file_path, port=8090, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.port = port
        self.httpd = None
        
    def run(self):
        from http.server import SimpleHTTPRequestHandler, HTTPServer
        
        # Custom handler to serve the target file
        class SingleFileHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                req_path = self.path.split('?')[0].split('#')[0]
                
                # Serve custom HTML download page
                if req_path in ('', '/', '/index.html', '/install'):
                    self.send_response(200)
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                    self.end_headers()
                    
                    ip = self.server.ip
                    port = self.server.port
                    file_name = os.path.basename(self.server.file_path)
                    import urllib.parse
                    encoded_filename = urllib.parse.quote(file_name)
                    download_url = f"http://{ip}:{port}/{encoded_filename}"
                    
                    is_dopamine = "dopamine" in file_name.lower()
                    icon = "🍀" if is_dopamine else "📲"
                    title_text = "Cài đặt Dopamine Jailbreak" if is_dopamine else "Cài đặt Ứng dụng"
                    desc_text = "Chọn phương thức cài đặt hoặc tải tệp tin Dopamine Jailbreak về thiết bị iPhone của bạn." if is_dopamine else "Chọn phương thức cài đặt hoặc tải tệp tin IPA về thiết bị iPhone của bạn."
                    
                    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title_text} - QHTD Automation 🚀</title>
    <style>
        body {{
            background: linear-gradient(135deg, #080b11, #0f172a);
            color: #f8fafc;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            padding: 20px;
            text-align: center;
        }}
        .card {{
            background: rgba(13, 18, 36, 0.8);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(6, 182, 212, 0.2);
            border-radius: 20px;
            padding: 35px 25px;
            max-width: 400px;
            width: 100%;
            box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.5);
            box-sizing: border-box;
        }}
        .icon {{
            font-size: 54px;
            margin-bottom: 20px;
            filter: drop-shadow(0 0 10px rgba(6, 182, 212, 0.5));
        }}
        h1 {{
            font-size: 22px;
            margin-bottom: 12px;
            font-weight: bold;
            background: linear-gradient(to right, #06b6d4, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .filename {{
            font-family: 'Consolas', monospace;
            font-size: 12px;
            background: #080b17;
            padding: 6px 12px;
            border-radius: 6px;
            color: #a5f3fc;
            margin-bottom: 25px;
            word-break: break-all;
            border: 1px solid #0e1630;
        }}
        .desc {{
            color: #94a3b8;
            font-size: 13.5px;
            line-height: 1.6;
            margin-bottom: 25px;
        }}
        .btn {{
            display: block;
            width: 100%;
            padding: 14px;
            margin-bottom: 15px;
            border-radius: 12px;
            font-weight: bold;
            text-decoration: none;
            box-sizing: border-box;
            transition: all 0.2s ease;
        }}
        .btn:active {{
            transform: scale(0.98);
        }}
        .btn-primary {{
            background: linear-gradient(135deg, #06b6d4, #3b82f6);
            color: white;
            box-shadow: 0 4px 14px rgba(6, 182, 212, 0.4);
        }}
        .btn-primary:hover {{
            box-shadow: 0 6px 20px rgba(6, 182, 212, 0.6);
        }}
        .btn-secondary {{
            background: #080b17;
            color: #94a3b8;
            border: 1px solid #0e1630;
        }}
        .btn-secondary:hover {{
            border-color: #06b6d4;
            color: #ffffff;
        }}
        .footer {{
            margin-top: 30px;
            font-size: 11px;
            color: #4b5563;
        }}
    </style>
</head>
<body>
    <div class="card">
        <div class="icon">{icon}</div>
        <h1>{title_text}</h1>
        <div class="filename">{file_name}</div>
        <p class="desc">{desc_text}</p>
        
        <a href="apple-magnifier://install?url={download_url}" class="btn btn-primary">Cài trực tiếp qua TrollStore 🚀</a>
        <a href="/{encoded_filename}" class="btn btn-secondary">Tải tệp tin về máy (Safari) 📥</a>
        
        <div class="footer">
            QHTD Store • Hỗ trợ thiết bị iOS
        </div>
    </div>
</body>
</html>"""
                    self.wfile.write(html_content.encode('utf-8'))
                else:
                    super().do_GET()

            def translate_path(self, path):
                return self.server.file_path
                
            def log_message(self, format, *args):
                pass
                
        ip = get_local_ip()
        port = self.port
        while port < 9000:
            try:
                self.httpd = HTTPServer((ip, port), SingleFileHandler)
                self.httpd.file_path = self.file_path
                self.httpd.ip = ip
                self.httpd.port = port
                break
            except Exception:
                port += 1
                
        if self.httpd:
            self.started.emit(ip, port)
            self.httpd.serve_forever()

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()


class InstallDopamineWorker(QThread):
    log_signal = pyqtSignal(str, str)  # message, style
    finished_signal = pyqtSignal(bool, str)  # success, web_url or error_msg
    server_url_signal = pyqtSignal(str)

    def __init__(self, serial=None, parent=None):
        super().__init__(parent)
        self.serial = serial
        self.server_thread = None
        self.dopamine_temp_path = None

    def run(self):
        self.log_signal.emit("Bắt đầu tiến trình cài đặt Dopamine...", "info")
        try:
            import tempfile
            from packaging.version import parse as parse_version
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.afc import AfcService

            self.log_signal.emit("Đang kết nối tới thiết bị iOS qua cổng USB...", "info")

            async def run_afc_copy():
                lockdown = await create_using_usbmux(serial=self.serial)
                product_version = lockdown.product_version
                self.log_signal.emit(f"Đã kết nối: iOS {product_version}", "success")

                # Check supported version
                device_version = parse_version(product_version)
                if device_version < parse_version("15.0") or device_version > parse_version("16.6.1"):
                    self.log_signal.emit(f"⚠️ Cảnh báo: iOS {product_version} ngoài tầm hỗ trợ chính thức của Dopamine (15.0 - 16.6.1)!", "warn")

                self.log_signal.emit("Đang tải Dopamine.tipa từ GitHub...", "action")
                url = "https://github.com/opa334/Dopamine/releases/latest/download/Dopamine.tipa"
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                dopamine_contents = response.content
                self.log_signal.emit(f"Tải Dopamine thành công! Kích thước: {len(dopamine_contents)/(1024*1024):.2f} MB", "success")

                self.log_signal.emit("Đang sao chép Dopamine.tipa sang iPhone qua cổng USB (AFC)...", "action")
                async with AfcService(lockdown) as afc:
                    try:
                        await afc.makedirs("Downloads")
                    except Exception:
                        pass
                    await afc.set_file_contents("Downloads/Dopamine.tipa", dopamine_contents)
                self.log_signal.emit("Sao chép qua USB hoàn tất vào Media/Downloads!", "success")

                temp_dir = tempfile.gettempdir()
                self.dopamine_temp_path = os.path.join(temp_dir, "Dopamine.tipa")
                with open(self.dopamine_temp_path, "wb") as f:
                    f.write(dopamine_contents)

                self.log_signal.emit("Đang khởi động máy chủ chia sẻ nội bộ...", "action")
                self.server_thread = WebServerWorker(self.dopamine_temp_path, port=8090)
                self.server_thread.started.connect(self.on_server_started)
                self.server_thread.start()

            asyncio.run(run_afc_copy())

            while self.server_thread and self.server_thread.isRunning():
                if self.isInterruptionRequested():
                    break
                self.msleep(500)

        except Exception as e:
            self.log_signal.emit(f"❌ Lỗi: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))
        finally:
            if self.dopamine_temp_path and os.path.exists(self.dopamine_temp_path):
                try:
                    os.remove(self.dopamine_temp_path)
                except Exception:
                    pass

    def on_server_started(self, ip, port):
        web_url = f"http://{ip}:{port}/"
        self.log_signal.emit(f"Máy chủ chia sẻ đang chạy tại: {web_url}", "success")
        self.server_url_signal.emit(web_url)
        self.finished_signal.emit(True, web_url)

    def stop(self):
        self.requestInterruption()
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread.wait()
            self.server_thread = None


class TorDownloadWorker(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool, str)

    def run(self):
        try:
            if not TOR_MANAGER_AVAILABLE:
                self.log_signal.emit("❌ Lỗi: Không tìm thấy module tor_manager.")
                self.finished_signal.emit(False, "Không tìm thấy module tor_manager.")
                return
            def progress_cb(msg):
                self.log_signal.emit(msg)
            download_and_extract_tor(progress_callback=progress_cb)
            self.finished_signal.emit(True, "Đã tải và giải nén Tor thành công!")
        except Exception as e:
            self.log_signal.emit(f"❌ Lỗi: {str(e)}")
            self.finished_signal.emit(False, str(e))


class TorMonitorWorker(QThread):
    status_signal = pyqtSignal(str)

    def __init__(self, tor_manager_instance, parent=None):
        super().__init__(parent)
        self.tor_manager = tor_manager_instance
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        while not self._stop_flag:
            status_list = []
            socks_ports = list(self.tor_manager.processes.keys())
            for port in socks_ports:
                if self._stop_flag:
                    break
                if port not in self.tor_manager.processes:
                    continue
                p, ctrl_port, data_dir = self.tor_manager.processes[port]
                is_running = p.poll() is None
                ip = "Đang kết nối..."
                if is_running:
                    ip = self.tor_manager.check_public_ip(port)
                status_list.append({
                    "socks_port": port,
                    "control_port": ctrl_port,
                    "status": "Live" if is_running else "Off",
                    "ip": ip
                })
            self.status_signal.emit(json.dumps(status_list, ensure_ascii=False))
            # Sleep 10s total, checking stop_flag in 500ms intervals
            for _ in range(20):
                if self._stop_flag:
                    break
                self.msleep(500)


def get_hwid():
    """Lấy mã định danh phần cứng độc nhất của máy"""
    import socket
    import subprocess
    import os
    current_machine_id = "unknown-uuid"
    if 'nt' in os.name:
        try:
            current_machine_id = str(subprocess.check_output('wmic csproduct get uuid'), 'utf-8').split('\n')[1].strip()
        except Exception:
            pass
    else:
        try:
            cmd = "system_profiler SPHardwareDataType | awk '/Serial Number/ {print $4}'"
            result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True, check=True)
            current_machine_id = result.stdout.decode("utf-8").strip()
        except Exception:
            pass
    name_computer = socket.gethostname()
    hwid = f"{name_computer}-{current_machine_id}"
    return hwid.strip()


class BrowserWorker(QThread):
    """QThread wrapper to run async nodriver anti-detect browser from PyQt6 UI."""
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, bool)  # (message, is_running)

    def __init__(self, profile_config, profile_name="Default", start_url=""):
        super().__init__()
        self.profile_config = profile_config
        self.profile_name = profile_name
        self.start_url = start_url
        self.manager = None
        self._stop_flag = False

    def run(self):
        if not MUN_ANTI_BROWSER_AVAILABLE:
            self.log_signal.emit("❌ Lỗi: Không tìm thấy module mun_anti_browser.")
            self.status_signal.emit("Lỗi", False)
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._run_browser())
        except Exception as e:
            self.log_signal.emit(f"❌ Browser error: {e}")
            self.status_signal.emit("Lỗi", False)
        finally:
            loop.close()

    async def _run_browser(self):
        self.manager = NodriverBrowserManager()
        self.log_signal.emit(f"🚀 Đang khởi chạy Anti-Detect Browser [{self.profile_name}]...")
        self.status_signal.emit("Đang chạy", True)
        try:
            proxy_str = (
                self.profile_config.get("proxy_string") or 
                self.profile_config.get("profile_socks5_details") or 
                self.profile_config.get("profile_proxy_details", "")
            )
            proxy_type = self.profile_config.get("proxy_type") or "socks5"
            if self.profile_config.get("profile_proxy_type") == 1:
                proxy_type = "http"
            elif self.profile_config.get("profile_proxy_type") == 0:
                proxy_str = ""  # Direct connection

            proxy_username = self.profile_config.get("proxy_username", "")
            proxy_password = self.profile_config.get("proxy_password", "")

            browser, tab = await self.manager.start(
                profile_config=self.profile_config,
                proxy_string=proxy_str,
                proxy_type=proxy_type,
                proxy_username=proxy_username,
                proxy_password=proxy_password,
                start_url=self.start_url,
            )
            self.log_signal.emit(f"✅ Browser [{self.profile_name}] đã sẵn sàng! Anti-detect ACTIVE.")
            
            while not self._stop_flag:
                await asyncio.sleep(0.5)
                if not self.manager.is_running:
                    self.log_signal.emit(f"⚠️ Trình duyệt [{self.profile_name}] đã bị đóng bởi người dùng.")
                    break
        except Exception as e:
            self.log_signal.emit(f"❌ Lỗi khởi chạy: {e}")
        finally:
            if self.manager and self.manager.is_running:
                await self.manager.close()
            self.status_signal.emit("Đã dừng", False)
            self.log_signal.emit(f"🛑 Browser [{self.profile_name}] đã đóng.")

    def stop_browser(self):
        self._stop_flag = True


class RequestWorker(QThread):
    finished_signal = pyqtSignal(str)

    def __init__(self, method, url, data=None, headers=None, timeout=15):
        super().__init__()
        self.method = method
        self.url = url
        self.data = data
        self.headers = headers or {}
        self.timeout = timeout
        self.result = json.dumps({"error": "No response"})

    def run(self):
        try:
            if self.method == 'GET':
                r = requests.get(self.url, headers=self.headers, timeout=self.timeout)
                self.result = r.text
            elif self.method == 'POST':
                r = requests.post(self.url, data=self.data, headers=self.headers, timeout=self.timeout)
                self.result = r.text
        except Exception as e:
            self.result = json.dumps({"error": str(e)})
        self.finished_signal.emit(self.result)


class AgentPollSignals(QObject):
    command_received = pyqtSignal(dict)
    log_signal = pyqtSignal(str)


# ============================================================================
# MUNAUTOMATION BRIDGE — Python API ↔ JavaScript (QWebChannel)
# ============================================================================
class MunAutomationBridge(QObject):
    """
    Cầu nối giữa JavaScript (c69.us web dashboard) và Python (local agent).
    Web gọi: window.munAutomationBridge.methodName(args) hoặc window.qhtdBridge.methodName(args)
    Python trả về qua return hoặc signal.
    """
    # Signals: Python → JavaScript
    deviceScanResult = pyqtSignal(str)
    automationLog = pyqtSignal(str, str)  # message, style
    automationFinished = pyqtSignal()
    downloadProgress = pyqtSignal(int, str)
    downloadComplete = pyqtSignal(str)
    statusMessage = pyqtSignal(str)

    # New Signals for WDA and Dopamine
    wdaSetupLog = pyqtSignal(str, str)  # message, style
    wdaSetupFinished = pyqtSignal(bool, str)  # success, message
    dopamineLog = pyqtSignal(str, str)  # message, style
    dopamineFinished = pyqtSignal(bool, str)  # success, message
    dopamineServerUrl = pyqtSignal(str)  # server url

    # Tor Signals
    torStatus = pyqtSignal(str)          # JSON list of proxies
    torDownloadLog = pyqtSignal(str)     # download progress logs
    torDownloadFinished = pyqtSignal(bool, str) # success, error_msg

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
        self.wda_setup_worker = None
        self.dopamine_worker = None
        self.tor_download_worker = None
        self.tor_monitor_worker = None
        self.browser_workers = {}
        self.poll_thread = None
        
        # Routing cache & poll thread
        self._cached_interfaces = "[]"
        self._cached_leases = "[]"
        self.router_poll_running = False
        self.router_poll_thread = None
        self._updating_interfaces = False
        self._last_interface_update_time = 0
        self._interface_to_index = {}
        self._index_to_interface = {}
        
        # Load interface indices offline in a background thread
        import threading
        t_load = threading.Thread(target=self._load_interface_indices, daemon=True)
        t_load.start()
        
        self.start_router_poll_thread()

    def start_router_poll_thread(self):
        if self.router_poll_running:
            return
        import threading
        self.router_poll_running = True
        self.router_poll_thread = threading.Thread(target=self._router_poll_loop, daemon=True)
        self.router_poll_thread.start()

    def _router_poll_loop(self):
        # Initial updates
        self._update_network_interfaces()
        self._update_dhcp_leases()
        
        last_leases_update = time.time()
        last_ifaces_update = time.time()
        
        while self.router_poll_running:
            now = time.time()
            # Poll DHCP leases every 3 seconds
            if now - last_leases_update >= 3.0:
                self._update_dhcp_leases()
                last_leases_update = now
            # Poll Network Interfaces every 15 seconds
            if now - last_ifaces_update >= 15.0:
                self._update_network_interfaces()
                last_ifaces_update = now
            time.sleep(0.5)

    def _load_interface_indices(self):
        try:
            import psutil
            addrs = psutil.net_if_addrs()
            for alias in addrs.keys():
                idx = win32_alias_to_index(alias)
                if idx is not None:
                    self._interface_to_index[alias] = idx
                    self._index_to_interface[idx] = alias
        except Exception as e:
            print(f"[QHTD] Error loading interface indices offline: {e}")

    def _update_network_interfaces(self):
        if getattr(self, "_updating_interfaces", False):
            return
        self._updating_interfaces = True
        try:
            import psutil
            interfaces = []
            addrs = psutil.net_if_addrs()
            
            for alias, addr_list in addrs.items():
                ip = ""
                for addr in addr_list:
                    if addr.family == socket.AF_INET:
                        ip = addr.address
                        break
                
                idx = self._interface_to_index.get(alias)
                if idx is None:
                    idx = win32_alias_to_index(alias)
                    if idx is not None:
                        self._interface_to_index[alias] = idx
                        self._index_to_interface[idx] = alias
                
                if idx is not None:
                    interfaces.append({
                        "name": str(idx),
                        "friendly_name": alias,
                        "ip": ip
                    })
                else:
                    interfaces.append({
                        "name": alias,
                        "friendly_name": alias,
                        "ip": ip
                    })

            if not interfaces:
                hostname = socket.gethostname()
                ips = socket.gethostbyname_ex(hostname)[2]
                for idx, ip in enumerate(ips):
                    interfaces.append({
                        "name": f"eth{idx}",
                        "friendly_name": f"Local Interface {idx}",
                        "ip": ip
                    })
            self._cached_interfaces = json.dumps(interfaces, ensure_ascii=False)
            self._last_interface_update_time = time.time()
        except Exception as e:
            self._cached_interfaces = json.dumps({"error": str(e)})
        finally:
            self._updating_interfaces = False

    def _update_dhcp_leases(self):
        import datetime
        try:
            if not self._is_api_port_open():
                raise ConnectionError("API port 8000 is closed")
            r = requests.get("http://127.0.0.1:8000/status", timeout=15)
            if r.status_code == 200:
                data = r.json()
                devices = data.get("devices", [])
                leases = []
                for d in devices:
                    ts = d.get("timestamp", 0)
                    leased_at = ""
                    if ts > 0:
                        try:
                            leased_at = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                        except Exception:
                            leased_at = datetime.datetime.now().strftime('%H:%M:%S')
                    else:
                        leased_at = datetime.datetime.now().strftime('%H:%M:%S')
                        
                    leases.append({
                        "mac": d.get("mac", ""),
                        "ip": d.get("ip", ""),
                        "hostname": d.get("name", f"Device {d.get('ip')}"),
                        "leased_at": leased_at,
                        "status": d.get("status", "Offline")
                    })
                self._cached_leases = json.dumps(leases, ensure_ascii=False)
                return
        except Exception:
            pass
            
        try:
            router_dir = os.path.join(os.path.dirname(os.path.dirname(get_app_dir())), "phonefarm-router")
            leases = []
            
            registry_path = os.path.join(router_dir, "data", "mac_registry.json")
            hosts_csv_path = os.path.join(router_dir, "hosts.csv")
            
            if os.path.exists(registry_path):
                with open(registry_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except Exception:
                        data = {}
                for mac, info in data.items():
                    ts = info.get("last_seen", 0)
                    leased_at = ""
                    if ts > 0:
                        leased_at = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                    else:
                        leased_at = datetime.datetime.now().strftime('%H:%M:%S')
                    
                    is_online = (time.time() - ts < 600) if ts > 0 else False
                    leases.append({
                        "mac": mac.upper(),
                        "ip": info.get("ip", ""),
                        "hostname": info.get("name") or f"Device {info.get('ip')}",
                        "leased_at": leased_at,
                        "status": "Online" if is_online else "Offline"
                    })
                self._cached_leases = json.dumps(leases, ensure_ascii=False)
                return
            elif os.path.exists(hosts_csv_path):
                with open(hosts_csv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(";")
                        if len(parts) >= 2:
                            mac = parts[0].strip().upper()
                            ip = parts[1].strip()
                            name = parts[2].strip() if len(parts) >= 3 else f"Device {ip}"
                            ts = 0
                            if len(parts) >= 4:
                                try:
                                    ts = int(parts[3].strip())
                                except ValueError:
                                    pass
                            
                            leased_at = ""
                            if ts > 0:
                                leased_at = datetime.datetime.fromtimestamp(ts).strftime('%H:%M:%S')
                            else:
                                leased_at = datetime.datetime.now().strftime('%H:%M:%S')
                                
                            is_online = (time.time() - ts < 600) if ts > 0 else False
                            leases.append({
                                "mac": mac,
                                "ip": ip,
                                "hostname": name,
                                "leased_at": leased_at,
                                "status": "Online" if is_online else "Offline"
                            })
                self._cached_leases = json.dumps(leases, ensure_ascii=False)
                return
        except Exception as e:
            print(f"[QHTD] Error getting DHCP leases fallback: {e}")
            
        self._cached_leases = "[]"


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
            from pymobiledevice3.lockdown import create_using_usbmux

            async def scan_async():
                devices = await list_devices()
                results = []
                for dev in devices:
                    try:
                        lockdown = await create_using_usbmux(serial=dev.serial)
                        results.append({
                            "serial": dev.serial,
                            "name": getattr(lockdown, "display_name", "iPhone"),
                            "model": getattr(lockdown, "product_type", "Unknown"),
                            "ios_version": getattr(lockdown, "product_version", "Unknown"),
                            "udid": getattr(lockdown, "udid", dev.serial),
                            "wifi_address": getattr(lockdown, "wifi_address", "") or "",
                        })
                    except Exception as e:
                        results.append({"serial": dev.serial, "error": str(e)})
                return results

            results = run_async_or_sync(scan_async)
            return json.dumps(results, ensure_ascii=False)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, result=str)
    def getDeviceApps(self, serial):
        """Lấy danh sách ứng dụng đã cài trên thiết bị"""
        try:
            if not PYMOBILEDEVICE3_AVAILABLE:
                return json.dumps({"error": "pymobiledevice3 chưa cài đặt"})
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.installation_proxy import InstallationProxyService

            async def get_apps_async():
                lockdown = await create_using_usbmux(serial=serial)
                iproxy = InstallationProxyService(lockdown=lockdown)
                # Check if get_apps is a coroutine function
                if asyncio.iscoroutinefunction(iproxy.get_apps):
                    return await iproxy.get_apps()
                else:
                    res = iproxy.get_apps()
                    if asyncio.iscoroutine(res):
                        return await res
                    return res

            apps = run_async_or_sync(get_apps_async)
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
            
            serial = config.get("serial")
            if not self.wda_client and serial:
                self.automationLog.emit("🔄 Phát hiện WDA chưa kết nối, đang tự động kết nối...", "action")
                self.wda_manager.start_relay(serial)
                client = WDAClient(host="http://127.0.0.1", port=self.wda_manager.local_port)
                if client.check_status():
                    self.wda_client = client
                    self.automationLog.emit("🟢 Đã tự động kết nối WebDriverAgent thành công!", "success")
                else:
                    self.automationLog.emit("⚠️ Không thể tự động kết nối WebDriverAgent. Script có thể bị lỗi khi tap/swipe.", "warn")

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

    @pyqtSlot(str)
    def openUrl(self, url):
        """Mở URL trong trình duyệt mặc định của hệ thống máy tính"""
        try:
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            print(f"[QHTD] Error opening URL: {e}", flush=True)

    @pyqtSlot(str, result=str)
    def checkWDAStatus(self, serial):
        """Kiểm tra trạng thái WebDriverAgent trên thiết bị"""
        try:
            if not PYMOBILEDEVICE3_AVAILABLE:
                return json.dumps({"status": "error", "message": "pymobiledevice3 không khả dụng"})
            
            bundle_id = self.wda_manager.check_wda_installed(serial)
            if not bundle_id:
                return json.dumps({"status": "not_installed", "message": "Chưa cài đặt WebDriverAgent"})
            
            # Start relay
            self.wda_manager.start_relay(serial)
            
            # Test status endpoint
            client = WDAClient(host="http://127.0.0.1", port=self.wda_manager.local_port)
            if client.check_status():
                self.wda_client = client
                return json.dumps({"status": "running", "message": "WebDriverAgent đang chạy và sẵn sàng!"})
            else:
                return json.dumps({"status": "stopped", "message": "WebDriverAgent chưa chạy"})
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)})

    @pyqtSlot(str)
    def startWDASetup(self, serial):
        """Khởi chạy WDASetupWorker"""
        try:
            if self.wda_setup_worker and self.wda_setup_worker.isRunning():
                self.wdaSetupLog.emit("Tiến trình thiết lập WDA đang chạy...", "warn")
                return
        except AttributeError:
            self.wda_setup_worker = None

        # Resolve WDA ipa path
        ipa_path = os.path.abspath(os.path.join(get_app_dir(), "WebDriverAgentRunner.ipa"))
        if not os.path.exists(ipa_path):
            ipa_path = os.path.abspath(os.path.join(get_app_dir(), "..", "iOSAutomationDesktop", "WebDriverAgentRunner.ipa"))
        if not os.path.exists(ipa_path):
            ipa_path = os.path.join(get_app_dir(), "WebDriverAgentRunner.ipa")

        self.wda_setup_worker = WDASetupWorker(self.wda_manager, serial, ipa_path)
        self.wda_setup_worker.log_signal.connect(self.wdaSetupLog.emit)
        self.wda_setup_worker.finished_signal.connect(self.on_wda_setup_finished)
        self.wda_setup_worker.start()

    def on_wda_setup_finished(self, success, message):
        if success:
            self.wda_client = WDAClient(host="http://127.0.0.1", port=self.wda_manager.local_port)
        self.wdaSetupFinished.emit(success, message)

    @pyqtSlot()
    def stopWDASetup(self):
        """Dừng WDASetupWorker"""
        try:
            if self.wda_setup_worker and self.wda_setup_worker.isRunning():
                self.wda_setup_worker.terminate()
                self.wda_setup_worker.wait()
                self.wdaSetupLog.emit("Đã dừng tiến trình thiết lập WDA.", "warn")
                self.wdaSetupFinished.emit(False, "Tiến trình bị hủy bởi người dùng.")
        except AttributeError:
            pass

    @pyqtSlot(str)
    def startDopamineInstall(self, serial):
        """Khởi chạy InstallDopamineWorker"""
        try:
            if self.dopamine_worker and self.dopamine_worker.isRunning():
                self.dopamineLog.emit("Tiến trình cài đặt Dopamine đang chạy...", "warn")
                return
        except AttributeError:
            self.dopamine_worker = None

        self.dopamine_worker = InstallDopamineWorker(serial)
        self.dopamine_worker.log_signal.connect(self.dopamineLog.emit)
        self.dopamine_worker.server_url_signal.connect(self.dopamineServerUrl.emit)
        self.dopamine_worker.finished_signal.connect(self.dopamineFinished.emit)
        self.dopamine_worker.start()

    @pyqtSlot()
    def stopDopamineInstall(self):
        """Dừng InstallDopamineWorker"""
        try:
            if self.dopamine_worker and self.dopamine_worker.isRunning():
                self.dopamine_worker.stop()
                self.dopamine_worker.wait()
                self.dopamineLog.emit("Đã dừng tiến trình cài đặt Dopamine.", "warn")
                self.dopamineFinished.emit(False, "Tiến trình bị dừng bởi người dùng.")
        except AttributeError:
            pass

    # --- Browser Profile Management & Polling ---
    def trigger_poll(self):
        """Đánh thức luồng poll để gửi cập nhật trạng thái ngay lập tức"""
        if hasattr(self, 'poll_event'):
            self.poll_event.set()

    def start_poll_thread(self):
        """Khởi chạy luồng polling ngầm đồng bộ với server sử dụng threading.Thread"""
        if hasattr(self, 'poll_running') and self.poll_running:
            return

        import threading
        self.poll_event = threading.Event()
        self.poll_signals = AgentPollSignals(self)
        self.poll_signals.command_received.connect(self.handle_agent_command)
        self.poll_signals.log_signal.connect(lambda msg: print(f"[AGENT POLL] {msg}", flush=True))

        self.poll_running = True
        hwid = get_hwid()
        print(f"[AGENT POLL] Starting poll thread with HWID: {hwid}", flush=True)

        def poll_loop():
            import time
            while self.poll_running:
                try:
                    session = self.get_requests_session()
                    
                    # Get active profiles
                    active_ids = []
                    inactive_ids = []
                    for pid, worker in list(self.browser_workers.items()):
                        if worker.isRunning():
                            active_ids.append(int(pid))
                        else:
                            inactive_ids.append(pid)
                    for pid in inactive_ids:
                        try:
                            del self.browser_workers[pid]
                        except Exception:
                            pass
                            
                    payload = {
                        "hwid": hwid,
                        "running_profiles": active_ids
                    }
                    
                    payload_str = json.dumps(payload, ensure_ascii=False)
                    STORAGON_SECRET_KEY = '7yn^8pwp+yzd2l4ki6+v9kp(h)rzs$9gxu4ao^_p+9x_5+1*6o'
                    import hashlib
                    sig = hashlib.md5((STORAGON_SECRET_KEY + payload_str).encode('utf-8')).hexdigest()
                    
                    headers = {
                        "Content-Type": "application/json",
                        "Signature-Authorization": sig
                    }
                    
                    url = f"{C69_BASE_URL.rstrip('/')}/telegram/bapi/agent/poll/"
                    resp = session.post(url, data=payload_str.encode('utf-8'), headers=headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if isinstance(data, dict) and data.get("success"):
                            commands = data.get("commands", [])
                            for cmd in commands:
                                self.poll_signals.command_received.emit(cmd)
                    elif resp.status_code == 403:
                        self.poll_signals.log_signal.emit("❌ Agent poll error: HWID is inactive or banned.")
                except Exception as e:
                    # Ignore or log to debug
                    pass
                
                # Sleep up to 3 seconds or until poll_event is set
                self.poll_event.wait(3.0)
                self.poll_event.clear()

        self.poll_thread = threading.Thread(target=poll_loop, daemon=True)
        self.poll_thread.start()

    def handle_agent_command(self, cmd):
        """Xử lý lệnh điều khiển nhận từ server"""
        cmd_type = cmd.get("command_type")
        profile_id = cmd.get("profile_id")
        profile_data = cmd.get("profile_data") or {}

        if cmd_type == "open_profile":
            print(f"[AGENT CMD] Received OPEN command for profile ID {profile_id}", flush=True)
            self.runBrowserProfileWithData(str(profile_id), profile_data)
        elif cmd_type == "close_profile":
            print(f"[AGENT CMD] Received CLOSE command for profile ID {profile_id}", flush=True)
            self.stopBrowserProfile(str(profile_id))

    @pyqtSlot(str, result=str)
    def runBrowserProfile(self, profile_id):
        """Mở profile trình duyệt từ web UI"""
        return self.runBrowserProfileWithData(profile_id, None)

    def runBrowserProfileWithData(self, profile_id, profile_data=None):
        """Helper thực sự mở profile trình duyệt"""
        try:
            pid_int = int(profile_id)
            if pid_int in self.browser_workers and self.browser_workers[pid_int].isRunning():
                return json.dumps({"success": True, "message": "Browser is already running"})

            # Nếu chưa có profile_data thì tải trực tiếp từ server
            if not profile_data:
                session = self.get_requests_session()
                url = f"{C69_BASE_URL.rstrip('/')}/dashboard/api/profiles/{pid_int}/"
                resp = session.get(url, timeout=10)
                if resp.status_code == 200:
                    profile_info = resp.json()
                else:
                    return json.dumps({"success": False, "error": f"Failed to fetch profile details: HTTP {resp.status_code}"})
            else:
                profile_info = profile_data

            # Chuyển đổi định dạng cấu hình server thành local
            from mun_anti_browser.c69_api import server_to_local
            local_cfg = server_to_local(profile_info)

            # Khởi chạy BrowserWorker
            worker = BrowserWorker(
                profile_config=local_cfg,
                profile_name=local_cfg.get("name", f"Profile {profile_id}"),
                start_url=local_cfg.get("profile_start_url", "")
            )
            worker.log_signal.connect(lambda msg: print(f"[BROWSER {profile_id}] {msg}", flush=True))
            worker.finished.connect(self.trigger_poll)
            
            self.browser_workers[pid_int] = worker
            worker.start()
            self.trigger_poll()

            return json.dumps({"success": True})
        except Exception as e:
            import traceback
            traceback.print_exc()
            return json.dumps({"success": False, "error": str(e)})

    @pyqtSlot(str, result=str)
    def stopBrowserProfile(self, profile_id):
        """Dừng profile trình duyệt từ web UI hoặc qua lệnh"""
        try:
            pid_int = int(profile_id)
            if pid_int in self.browser_workers:
                worker = self.browser_workers[pid_int]
                if worker.isRunning():
                    worker.stop_browser()
                self.trigger_poll()
                return json.dumps({"success": True})
            return json.dumps({"success": True, "message": "Browser was not running"})
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    # --- Tor Proxy Management ---
    @pyqtSlot(result=bool)
    def isTorInstalled(self):
        if not TOR_MANAGER_AVAILABLE:
            return False
        return is_tor_installed()

    @pyqtSlot()
    def startTorDownload(self):
        if not TOR_MANAGER_AVAILABLE:
            self.torDownloadFinished.emit(False, "Không tìm thấy module tor_manager.")
            return
        if self.tor_download_worker and self.tor_download_worker.isRunning():
            self.torDownloadLog.emit("Tiến trình tải Tor đang chạy...")
            return
        self.tor_download_worker = TorDownloadWorker()
        self.tor_download_worker.log_signal.connect(self.torDownloadLog.emit)
        self.tor_download_worker.finished_signal.connect(self.torDownloadFinished.emit)
        self.tor_download_worker.start()

    @pyqtSlot(int, int, str, result=bool)
    def startTorProxy(self, socks_port, control_port, country_code):
        if not TOR_MANAGER_AVAILABLE:
            return False
        success = tor_manager.start_proxy(socks_port, control_port, country_code)
        if success:
            self.start_tor_monitor()
        return success

    @pyqtSlot(int)
    def stopTorProxy(self, socks_port):
        if TOR_MANAGER_AVAILABLE:
            tor_manager.stop_proxy(socks_port)

    @pyqtSlot()
    def stopAllTorProxies(self):
        if TOR_MANAGER_AVAILABLE:
            tor_manager.stop_all()

    @pyqtSlot(int, result=bool)
    def rotateTorIp(self, control_port):
        if not TOR_MANAGER_AVAILABLE:
            return False
        return tor_manager.rotate_ip(control_port)

    @pyqtSlot(result=str)
    def getActiveTorProxies(self):
        if not TOR_MANAGER_AVAILABLE:
            return "[]"
        status_list = []
        for port, (p, ctrl_port, data_dir) in tor_manager.processes.items():
            is_running = p.poll() is None
            status_list.append({
                "socks_port": port,
                "control_port": ctrl_port,
                "status": "Live" if is_running else "Off",
                "ip": "Nhấp kiểm tra hoặc chờ làm mới..."
            })
        return json.dumps(status_list, ensure_ascii=False)

    def start_tor_monitor(self):
        if not TOR_MANAGER_AVAILABLE:
            return
        if not self.tor_monitor_worker or not self.tor_monitor_worker.isRunning():
            self.tor_monitor_worker = TorMonitorWorker(tor_manager)
            self.tor_monitor_worker.status_signal.connect(self.torStatus.emit)
            self.tor_monitor_worker.start()

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
    # Actual implementation is defined above (lines 1204-1261)


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
        now = time.time()
        if not getattr(self, "_updating_interfaces", False) and (now - getattr(self, "_last_interface_update_time", 0) > 5.0):
            try:
                import threading
                t = threading.Thread(target=self._update_network_interfaces, daemon=True)
                t.start()
            except Exception as e:
                print(f"[QHTD] Error launching network interface update thread: {e}")
        return self._cached_interfaces

    @pyqtSlot(str, result=str)
    def startRouter(self, config_json):
        try:
            # Ghi log payload thô để phục vụ chẩn đoán lỗi
            try:
                debug_log_path = os.path.join(get_app_dir(), "router_debug.txt")
                with open(debug_log_path, "a", encoding="utf-8") as f_dbg:
                    f_dbg.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Raw config: {config_json}\n")
            except Exception as log_ex:
                print(f"[QHTD] Logging config failed: {log_ex}")

            config = json.loads(config_json)
            self.router_config = config
            
            lan_if = config.get("lan_interface") or config.get("interface") or config.get("lan") or config.get("lan_if")
            wan_if = config.get("wan_interface") or config.get("wan") or config.get("wan_if")
            dhcp_start = config.get("dhcp_range_start") or config.get("dhcp_start") or config.get("dhcpRangeStart") or config.get("dhcpStart")
            dhcp_end = config.get("dhcp_range_end") or config.get("dhcp_end") or config.get("dhcpRangeEnd") or config.get("dhcpEnd")
            dns_server = config.get("dns_server") or config.get("dns") or config.get("dnsServer") or "8.8.8.8"
            
            if not lan_if:
                return json.dumps({"error": f"Vui lòng chọn card mạng LAN. (Nhận được: {config_json})"})
                
            router_dir = os.path.join(os.path.dirname(os.path.dirname(get_app_dir())), "phonefarm-router")
            config_path = os.path.join(router_dir, "data", "config.json")
            
            # 1. Read existing phonefarm-router config.json for fallback
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    try:
                        config_data = json.load(f)
                    except Exception:
                        pass
            
            def get_alias_from_index_or_name(iface):
                if not iface:
                    return ""
                if str(iface).isdigit():
                    idx = int(iface)
                    if idx in self._index_to_interface:
                        return self._index_to_interface[idx]
                    
                    try:
                        ifaces = json.loads(self._cached_interfaces)
                        for item in ifaces:
                            if item.get("name") == str(iface) and item.get("friendly_name"):
                                friendly_name = item.get("friendly_name")
                                self._index_to_interface[idx] = friendly_name
                                self._interface_to_index[friendly_name] = idx
                                return friendly_name
                    except Exception:
                        pass
                    
                    alias = win32_index_to_alias(idx)
                    if alias:
                        self._index_to_interface[idx] = alias
                        self._interface_to_index[alias] = idx
                        return alias
                else:
                    alias = str(iface)
                    if alias in self._interface_to_index:
                        return alias
                    try:
                        ifaces = json.loads(self._cached_interfaces)
                        for item in ifaces:
                            if item.get("friendly_name") == alias and item.get("name"):
                                idx = int(item.get("name"))
                                self._interface_to_index[alias] = idx
                                self._index_to_interface[idx] = alias
                                break
                    except Exception:
                        pass
                    
                    if alias not in self._interface_to_index:
                        idx = win32_alias_to_index(alias)
                        if idx is not None:
                            self._interface_to_index[alias] = idx
                            self._index_to_interface[idx] = alias
                return str(iface)

            lan_alias = get_alias_from_index_or_name(lan_if)

            # Auto-detect WAN interface if not provided in the payload
            if not wan_if:
                # Attempt 1: Get the best route to the Internet (e.g. 8.8.8.8) using Win32 API
                best_idx = win32_get_best_interface_index("8.8.8.8")
                if best_idx is not None:
                    detected_alias = get_alias_from_index_or_name(best_idx)
                    if detected_alias and detected_alias != lan_alias:
                        wan_if = str(best_idx)
                
                # Attempt 2: Fall back to existing config's wan_interface if valid
                if not wan_if:
                    old_wan = config_data.get("wan_interface")
                    if old_wan and old_wan != lan_alias:
                        wan_if = old_wan

                # Attempt 3: Fall back to any active interface that is not the LAN interface
                if not wan_if:
                    try:
                        import psutil
                        addrs = psutil.net_if_addrs()
                        for alias in addrs.keys():
                            if alias != lan_alias:
                                for addr in addrs[alias]:
                                    if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                                        wan_if = alias
                                        break
                            if wan_if:
                                break
                    except Exception:
                        pass

                # Final fallback
                if not wan_if:
                    wan_if = "Wi-Fi" if lan_alias != "Wi-Fi" else "Ethernet"

            wan_alias = get_alias_from_index_or_name(wan_if)
            
            config_data["lan_interface"] = lan_alias
            config_data["wan_interface"] = wan_alias
            if dhcp_start:
                config_data["dhcp_range_start"] = dhcp_start
            if dhcp_end:
                config_data["dhcp_range_end"] = dhcp_end
            if dns_server:
                config_data["dns_server"] = dns_server
                
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            # 2. Dynamic Router IP Calculation
            router_ip = "192.168.88.1"
            if dhcp_start:
                parts = dhcp_start.split('.')
                if len(parts) == 4:
                    router_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.1"
            
            import psutil
            addrs = psutil.net_if_addrs()
            has_ip = False
            if lan_alias in addrs:
                for addr in addrs[lan_alias]:
                    if addr.family == socket.AF_INET and addr.address == router_ip:
                        has_ip = True
                        break
            
            if not has_ip:
                if str(lan_if).isdigit():
                    ps_script = (
                        f"Remove-NetIPAddress -InterfaceIndex {lan_if} -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                        f"New-NetIPAddress -InterfaceIndex {lan_if} -IPAddress '{router_ip}' -PrefixLength 24 -DefaultGateway $null; "
                        f"Set-DnsClientServerAddress -InterfaceIndex {lan_if} -ServerAddresses ('8.8.8.8','1.1.1.1')"
                    )
                else:
                    ps_script = (
                        f"Remove-NetIPAddress -InterfaceAlias '{lan_alias}' -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                        f"New-NetIPAddress -InterfaceAlias '{lan_alias}' -IPAddress '{router_ip}' -PrefixLength 24 -DefaultGateway $null; "
                        f"Set-DnsClientServerAddress -InterfaceAlias '{lan_alias}' -ServerAddresses ('8.8.8.8','1.1.1.1')"
                    )
                
                cmd_run = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {ps_script}' -Verb RunAs -WindowStyle Hidden\""
                subprocess.run(cmd_run, shell=True)
                
            # 3. Start DHCP server (disabled in v2.0 - integrated in app.main)
            # dhcp_script_path = os.path.join(router_dir, "scratch", "run_dhcp.py")
            # dhcp_cmd = f"powershell -Command \"Start-Process '{sys.executable}' -ArgumentList '{dhcp_script_path}' -Verb RunAs -WorkingDirectory '{router_dir}' -WindowStyle Hidden\""
            # subprocess.run(dhcp_cmd, shell=True)
            
            # 4. Start API server (GenRouter v2.0 Unified)
            # Không sử dụng RedirectStandardOutput/Error cùng với -Verb RunAs vì sẽ gây lỗi Parameter set cannot be resolved
            api_cmd = f"powershell -Command \"Start-Process '{sys.executable}' -ArgumentList '-m uvicorn app.main:app --host 0.0.0.0 --port 8000' -Verb RunAs -WorkingDirectory '{router_dir}' -WindowStyle Hidden\""
            subprocess.run(api_cmd, shell=True)
            
            self.router_active = True
            print(f"[QHTD] Started routing dynamically: LAN={lan_alias} (IP={router_ip}), WAN={wan_alias}")
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(result=str)
    def stopRouter(self):
        try:
            self.router_active = False
            
            ps_kill = (
                "$p = Get-NetUDPEndpoint -LocalPort 67 -ErrorAction SilentlyContinue; "
                "if ($p) { Stop-Process -Id $p.OwningProcess -Force -ErrorAction SilentlyContinue }; "
                "$p2 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; "
                "if ($p2) { Stop-Process -Id $p2.OwningProcess -Force -ErrorAction SilentlyContinue }; "
                "Stop-Process -Name sing-box -Force -ErrorAction SilentlyContinue"
            )
            
            cmd_run = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {ps_kill}' -Verb RunAs -WindowStyle Hidden\""
            subprocess.run(cmd_run, shell=True)
            print("[QHTD] Stopped routing and DHCP server")
            return json.dumps({"success": True})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(result=str)
    def getDHCPLeases(self):
        return self._cached_leases

    @pyqtSlot(result=str)
    def refreshDHCPLeases(self):
        self._update_dhcp_leases()
        return self._cached_leases

    def _is_api_port_open(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.1)
            s.connect(("127.0.0.1", 8000))
            s.close()
            return True
        except Exception:
            return False

    def _run_request_async(self, method, url, data=None, headers=None):
        loop = QEventLoop()
        worker = RequestWorker(method, url, data, headers, timeout=15)
        
        result = None
        def on_finished(res):
            nonlocal result
            result = res
            loop.quit()
            
        worker.finished_signal.connect(on_finished)
        worker.start()
        loop.exec()
        worker.wait()
        return result

    @pyqtSlot(str, result=str)
    def apiProxyGet(self, endpoint):
        if not self._is_api_port_open():
            return json.dumps({"error": "API server offline (port 8000 is closed)"})
        try:
            return self._run_request_async('GET', f"http://127.0.0.1:8000{endpoint}")
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, str, result=str)
    def apiProxyPost(self, endpoint, body_json):
        if not self._is_api_port_open():
            return json.dumps({"error": "API server offline (port 8000 is closed)"})
        try:
            headers = {'Content-Type': 'application/json'}
            return self._run_request_async('POST', f"http://127.0.0.1:8000{endpoint}", data=body_json.encode('utf-8'), headers=headers)
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(result=bool)
    def isRouterActive(self):
        return self.router_active

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

    async def _find_element_in_all_frames(self, tab, selector):
        """Tìm element bằng selector trong tab chính và tất cả các iframes connectable"""
        # 1. Check main tab
        try:
            el = await tab.select(selector, timeout=1)
            if el:
                return el, tab
        except Exception:
            pass
            
        # 2. Check all child frames
        try:
            frames = await tab.get_frames()
            for frame in frames:
                try:
                    el = await frame.select(selector, timeout=1)
                    if el:
                        return el, frame
                except Exception:
                    pass
        except Exception:
            pass
            
        return None, None

    async def _evaluate_in_iframe_robust(self, tab, expression):
        """Evaluate a JS expression inside the cross-origin idmsa.apple.com iframe safely, handling context destruction"""
        import nodriver.cdp.page as cdp_page
        import nodriver.cdp.runtime as cdp_runtime
        
        def find_login_frame(ft):
            if 'idmsa.apple.com' in (ft.frame.url or ''):
                return ft.frame
            if ft.child_frames:
                for child in ft.child_frames:
                    result = find_login_frame(child)
                    if result:
                        return result
            return None
            
        try:
            frame_tree = await tab.send(cdp_page.get_frame_tree())
            login_frame = find_login_frame(frame_tree)
            if not login_frame:
                return None, "IFRAME_NOT_FOUND"
            
            # Always create a new isolated world context to guarantee executing on the current active document state
            context_id = await tab.send(cdp_page.create_isolated_world(
                frame_id=login_frame.id_,
                world_name="mun_login_inject_robust"
            ))
            
            result = await tab.send(cdp_runtime.evaluate(
                expression=expression,
                context_id=context_id,
                return_by_value=True
            ))
            val = result[0].value if hasattr(result[0], 'value') else str(result[0])
            return val, None
        except Exception as e:
            return None, str(e)

    async def _automate_apple_login(self, tab, apple_id, password):
        """Automate Apple ID login using CDP to access cross-origin idmsa.apple.com iframe"""
        print(f"[MunAutomation] Automating Apple ID login for: {apple_id}")
        
        # 1. Wait for email input to be visible in iframe
        email_found = False
        for attempt in range(30):  # 30 seconds timeout
            val, err = await self._evaluate_in_iframe_robust(
                tab,
                "!!(document.querySelector('input#account_name_text_field') || document.querySelector('input[type=\"email\"]'))"
            )
            if val is True:
                email_found = True
                print(f"[MunAutomation] Email field detected in iframe at attempt {attempt}")
                break
            if attempt % 5 == 0:
                print(f"[MunAutomation] Waiting for email field... attempt {attempt} (err={err})")
            await asyncio.sleep(1)
        
        if not email_found:
            print("[MunAutomation] Email field not found in login iframe after 30s")
            return False
        
        # 2. Fill email field
        fill_res, err = await self._evaluate_in_iframe_robust(tab, f"""
            (() => {{
                const inp = document.querySelector('input#account_name_text_field') ||
                           document.querySelector('input[type="email"]') ||
                           document.querySelector('input[type="text"]');
                if (!inp) return 'NO_INPUT';
                inp.focus();
                inp.value = '{apple_id}';
                inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                return 'OK';
            }})()
        """)
        print(f"[MunAutomation] Email fill result: {fill_res} (err={err})")
        if fill_res != 'OK':
            return False
            
        await asyncio.sleep(1)
        
        # 3. Click the Continue/Sign-In button to trigger password transition
        click_res, err = await self._evaluate_in_iframe_robust(tab, """
            (() => {
                const btn = document.querySelector('button#sign-in') ||
                           document.querySelector('button.si-button') ||
                           document.querySelector('button[type="submit"]');
                if (btn) {
                    btn.click();
                    return 'CLICKED';
                }
                return 'NO_BUTTON';
            })()
        """)
        print(f"[MunAutomation] Continue button click: {click_res} (err={err})")
        
        # 4. Wait for transition and fill password
        print("[MunAutomation] Waiting for password field to be ready...")
        pw_filled = False
        for attempt in range(20):
            await asyncio.sleep(0.5)
            is_visible, err = await self._evaluate_in_iframe_robust(tab, """
                (() => {
                    const pw = document.querySelector('input#password_text_field') ||
                               document.querySelector('input[type="password"]');
                    return pw && pw.offsetParent !== null;
                })()
            """)
            
            if is_visible is True:
                # Fill password
                fill_pw, err = await self._evaluate_in_iframe_robust(tab, f"""
                    (() => {{
                        const inp = document.querySelector('input#password_text_field') ||
                                   document.querySelector('input[type="password"]');
                        if (!inp) return 'NO_PW';
                        inp.focus();
                        inp.value = '{password}';
                        inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                        inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                        return 'OK';
                    }})()
                """)
                print(f"[MunAutomation] Password fill result: {fill_pw} (err={err})")
                if fill_pw == 'OK':
                    pw_filled = True
                    
                    # Click sign-in final
                    await asyncio.sleep(1)
                    signin_res, err = await self._evaluate_in_iframe_robust(tab, """
                        (() => {
                            const btn = document.querySelector('button#sign-in') ||
                                       document.querySelector('button[type="submit"]');
                            if (btn) {
                                btn.click();
                                return 'CLICKED_FINAL';
                            }
                            return 'NO_BTN';
                        })()
                    """)
                    print(f"[MunAutomation] Final Sign-In click: {signin_res} (err={err})")
                    break
        
        if not pw_filled:
            print("[MunAutomation] Failed to fill password field")
            return False
            
        print("[MunAutomation] Login automation completed successfully")
        return True

    async def _evaluate_in_all_contexts(self, tab, js_code):
        """Evaluate JS in main tab and all nested iframe content frames"""
        results = []
        try:
            res_main = await tab.evaluate(js_code)
            if res_main is not None:
                results.append(res_main)
        except Exception as e:
            print(f"[MunAutomation] Eval error in main frame: {e}")
            
        try:
            frames = await tab.get_frames()
            for frame in frames:
                try:
                    res_frame = await frame.evaluate(js_code)
                    if res_frame is not None:
                        results.append(res_frame)
                except Exception:
                    pass
        except Exception as e_frames:
            print(f"[MunAutomation] Error evaluating inside child frames: {e_frames}")
            
        for r in results:
            if r:
                return r
        return None
    async def _find_button_by_text(self, tab, texts):
        """Tìm button hoặc clickable element có chứa một trong các chuỗi văn bản chỉ định"""
        all_buttons = []
        try:
            all_buttons.extend(await tab.select_all("button"))
            all_buttons.extend(await tab.select_all("input[type='button']"))
            all_buttons.extend(await tab.select_all("input[type='submit']"))
            all_buttons.extend(await tab.select_all("a"))
            all_buttons.extend(await tab.select_all("span"))
        except Exception:
            pass
            
        try:
            iframes = await tab.select_all("iframe")
            for iframe in iframes:
                try:
                    all_buttons.extend(await tab.query_selector_all("button", iframe))
                    all_buttons.extend(await tab.query_selector_all("input[type='button']", iframe))
                    all_buttons.extend(await tab.query_selector_all("input[type='submit']", iframe))
                    all_buttons.extend(await tab.query_selector_all("a", iframe))
                    all_buttons.extend(await tab.query_selector_all("span", iframe))
                except Exception:
                    pass
        except Exception:
            pass
            
        for btn in all_buttons:
            try:
                text = ""
                if btn.tag == 'input':
                    text = btn.attrs.get('value', '').lower()
                else:
                    text = btn.text.lower()
                    
                for t in texts:
                    if t.lower() in text:
                        return btn
            except Exception:
                pass
        return None

    async def _automate_payment_filling(self, tab, card_data):
        """Automate card form filling using Nodriver elements directly (bypassing JS evaluate sandbox)"""
        print("[MunAutomation] Automating card form filling...")
        
        # We try for up to 12 seconds for inputs to be available on screen
        for _ in range(12):
            # 1. Get all inputs from main page
            all_inputs = []
            try:
                all_inputs.extend(await tab.select_all("input"))
                all_inputs.extend(await tab.select_all("select"))
            except Exception:
                pass
                
            # 2. Get all inputs from all iframes
            try:
                iframes = await tab.select_all("iframe")
                for iframe in iframes:
                    try:
                        all_inputs.extend(await tab.query_selector_all("input", iframe))
                        all_inputs.extend(await tab.query_selector_all("select", iframe))
                    except Exception:
                        pass
            except Exception:
                pass
                
            if not all_inputs:
                await asyncio.sleep(1)
                continue
                
            filled_any = False
            # Fill each input based on attribute matching
            for input_el in all_inputs:
                try:
                    name = input_el.attrs.get('name', '').lower()
                    id_ = input_el.attrs.get('id', '').lower()
                    label = input_el.attrs.get('aria-label', '').lower()
                    placeholder = input_el.attrs.get('placeholder', '').lower()
                    
                    # Check for card number
                    if 'cardnumber' in id_ or 'cardnumber' in name or 'card number' in label or 'card number' in placeholder:
                        await input_el.send_keys(card_data.get("card_number", ""))
                        filled_any = True
                        print("[MunAutomation] Filled card number")
                        
                    # Check for expiry date
                    elif 'exp' in id_ or 'exp' in name or 'expiration' in label or 'expiration' in placeholder:
                        if 'mm/yy' in placeholder or 'month/year' in label:
                            combined = f"{card_data.get('expiry_month', '')}{card_data.get('expiry_year', '')[-2:]}"
                            await input_el.send_keys(combined)
                            filled_any = True
                            print("[MunAutomation] Filled combined expiry date")
                        elif 'month' in id_ or 'month' in name or 'month' in label or 'mm' in placeholder:
                            await input_el.send_keys(card_data.get('expiry_month', ''))
                            filled_any = True
                            print("[MunAutomation] Filled expiry month")
                        elif 'year' in id_ or 'year' in name or 'year' in label or 'yy' in placeholder:
                            val = card_data.get('expiry_year', '')
                            if len(val) == 4 and 'yy' in placeholder and not 'yyyy' in placeholder:
                                val = val[-2:]
                            await input_el.send_keys(val)
                            filled_any = True
                            print("[MunAutomation] Filled expiry year")
                            
                    # Check for CVV
                    elif 'cvv' in id_ or 'cvv' in name or 'cvc' in id_ or 'cvc' in name or 'security code' in label or 'security code' in placeholder or 'verification' in id_ or 'verification' in name:
                        await input_el.send_keys(card_data.get('cvv', ''))
                        filled_any = True
                        print("[MunAutomation] Filled security code (CVV)")
                        
                    # Check for name/address
                    elif 'firstname' in id_ or 'firstname' in name or 'first name' in label or 'first name' in placeholder:
                        await input_el.send_keys(card_data.get('first_name', 'Nguyen'))
                    elif 'lastname' in id_ or 'lastname' in name or 'last name' in label or 'last name' in placeholder:
                        await input_el.send_keys(card_data.get('last_name', 'Van A'))
                    elif 'street' in id_ or 'street' in name or 'address' in label or 'address' in placeholder:
                        await input_el.send_keys(card_data.get('address_line1', '123 Le Loi'))
                    elif 'city' in id_ or 'city' in name or 'city' in label or 'city' in placeholder:
                        await input_el.send_keys(card_data.get('city', 'Ho Chi Minh'))
                    elif 'zip' in id_ or 'zip' in name or 'postal' in label or 'postal' in placeholder:
                        await input_el.send_keys(card_data.get('zip_code', '70000'))
                    elif 'phone' in id_ or 'phone' in name or 'phone' in label or 'phone' in placeholder:
                        await input_el.send_keys(card_data.get('phone', '0987654321'))
                except Exception as e_field:
                    print(f"[MunAutomation] Error filling individual field: {e_field}")
            
            if filled_any:
                print("[MunAutomation] Card fields found and auto-filled!")
                break
            await asyncio.sleep(1)

    @pyqtSlot(str, str, result=str)
    def openBrowserProfile(self, profile_name, target_url):
        try:
            print(f"[MunAutomation] Launching MunLogin browser profile '{profile_name}' target: {target_url}")
            self.statusMessage.emit(f"🚀 Đang mở trình duyệt MunLogin cho {profile_name}...")
            url = target_url or "https://account.apple.com/account/manage/section/payment"
            
            import threading
            def run_browser():
                try:
                    # Fetch credentials from backend in the thread
                    apple_id = ""
                    password = ""
                    try:
                        session = self.get_requests_session()
                        payload = {"session_id": profile_name} if len(profile_name) > 30 else {"apple_id": profile_name}
                        r = session.post(f"{C69_BASE_URL.rstrip('/')}/dashboard/api/apple-sub/get-password/", json=payload, timeout=10)
                        if r.status_code == 200:
                            cred_data = r.json()
                            if cred_data.get('success'):
                                apple_id = cred_data.get('apple_id')
                                password = cred_data.get('password')
                    except Exception as e_cred:
                        print(f"[MunAutomation] Failed to fetch credentials for auto login: {e_cred}")

                    if MUN_ANTI_BROWSER_AVAILABLE:
                        manager = NodriverBrowserManager()
                        profile = manager.profile_manager.create_random_profile()
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        browser, tab = loop.run_until_complete(manager.start(profile))
                        if tab:
                            loop.run_until_complete(tab.get(url))
                            
                            # If credentials exist and we are on an Apple domain, run login automation
                            if apple_id and password and "apple.com" in url:
                                try:
                                    # Wait up to 5 seconds to check if we are redirected to login page
                                    is_login = False
                                    for _ in range(5):
                                        try:
                                            current_url = tab.url
                                            if "idmsa.apple.com" in current_url or "signin" in current_url:
                                                is_login = True
                                                break
                                        except Exception:
                                            pass
                                        time.sleep(1)
                                        
                                    if is_login:
                                        loop.run_until_complete(self._automate_apple_login(tab, apple_id, password))
                                except Exception as e_login:
                                    print(f"[MunAutomation] Login automation error: {e_login}")
                    else:
                        import webbrowser
                        webbrowser.open(url)
                except Exception as ex:
                    print(f"[MunAutomation] Browser thread exception: {ex}")
                    import webbrowser
                    webbrowser.open(url)

            t = threading.Thread(target=run_browser, daemon=True)
            t.start()
            return json.dumps({"success": True, "message": f"Đã khởi chạy MunLogin profile {profile_name}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, str, result=str)
    def open_browser_profile(self, profile_name, target_url):
        return self.openBrowserProfile(profile_name, target_url)

    @pyqtSlot(str, str, str, str, str, result=str)
    def addPaymentCard(self, session_id, card_number, exp_month, exp_year, cvv):
        card_data = {
            "card_number": card_number,
            "expiry_month": exp_month,
            "expiry_year": exp_year,
            "cvv": cvv
        }
        return self.addPaymentCardAuto(session_id, json.dumps(card_data))

    @pyqtSlot(str, str, result=str)
    def addPaymentCardAuto(self, session_id, card_config_json):
        try:
            print(f"[MunAutomation] Auto Add payment card requested for session {session_id}")
            self.statusMessage.emit(f"💳 Đang mở MunLogin để tự động thêm thẻ...")
            url = "https://account.apple.com/account/manage/section/payment"
            card_data = json.loads(card_config_json)
            
            import threading
            def run_card_browser():
                try:
                    # Fetch credentials from backend
                    apple_id = ""
                    password = ""
                    try:
                        session = self.get_requests_session()
                        payload = {"session_id": session_id} if len(session_id) > 30 else {"apple_id": session_id}
                        r = session.post(f"{C69_BASE_URL.rstrip('/')}/dashboard/api/apple-sub/get-password/", json=payload, timeout=10)
                        if r.status_code == 200:
                            cred_data = r.json()
                            if cred_data.get('success'):
                                apple_id = cred_data.get('apple_id')
                                password = cred_data.get('password')
                    except Exception as e_cred:
                        print(f"[MunAutomation] Failed to fetch credentials: {e_cred}")

                    if MUN_ANTI_BROWSER_AVAILABLE:
                        manager = NodriverBrowserManager()
                        profile = manager.profile_manager.create_random_profile()
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        browser, tab = loop.run_until_complete(manager.start(profile))
                        if tab:
                            # 1. Open URL
                            loop.run_until_complete(tab.get(url))
                            
                            # 2. Run Login Automation if credentials found and we are redirecting to login page
                            is_login = False
                            for _ in range(5):
                                try:
                                    current_url = tab.url
                                    if "idmsa.apple.com" in current_url or "signin" in current_url:
                                        is_login = True
                                        break
                                except Exception:
                                    pass
                                time.sleep(1)
                                
                            if is_login and apple_id and password:
                                try:
                                    loop.run_until_complete(self._automate_apple_login(tab, apple_id, password))
                                except Exception as e_login:
                                    print(f"[MunAutomation] Login automation error: {e_login}")
                                    
                            # Wait for payment page to load fully after login
                            time.sleep(3)
                            
                            # 3. Fill Card Form Automation
                            try:
                                loop.run_until_complete(self._automate_payment_filling(tab, card_data))
                            except Exception as e_fill:
                                print(f"[MunAutomation] Payment filling error: {e_fill}")
                    else:
                        import webbrowser
                        webbrowser.open(url)
                except Exception as ex:
                    print(f"[MunAutomation] Card browser exception: {ex}")
                    
            t = threading.Thread(target=run_card_browser, daemon=True)
            t.start()
            return json.dumps({"success": True, "message": "Đang khởi chạy MunLogin tự động thêm thẻ..."})
        except Exception as e:
            return json.dumps({"error": str(e)})

    def update_card_status_on_server(self, card_id, status):
        try:
            session = self.get_requests_session()
            url = f"{C69_BASE_URL.rstrip('/')}/dashboard/api/cards/{card_id}/"
            resp = session.patch(url, json={"status": status}, timeout=10)
            print(f"[MunAutomation] Updated card {card_id} status on server to: {status}. Status: {resp.status_code}")
        except Exception as e:
            print(f"[MunAutomation] Failed to update card status on server: {e}")

    async def _automate_add_payment_cards(self, tab, cards):
        """Automate adding a list of cards to Apple account one by one"""
        success_count = 0
        total_count = len(cards)
        
        for idx, card in enumerate(cards):
            card_num = card.get("card_number", "")
            print(f"[MunAutomation] Attempting to add card {idx+1}/{total_count}: ****{card_num[-4:]}")
            self.statusMessage.emit(f"💳 Đang thêm thẻ {idx+1}/{total_count} (****{card_num[-4:]})...")
            
            # 1. Ensure we are on the payment section page
            try:
                if "section/payment" not in tab.url:
                    await tab.get("https://account.apple.com/account/manage/section/payment")
                    await asyncio.sleep(3)
            except Exception:
                pass
                
            # 2. Click "Add Payment Method"
            clicked_add = False
            for _ in range(5):
                try:
                    btn = await self._find_button_by_text(tab, ['add payment', 'add a payment', 'thêm phương thức', 'thêm thẻ'])
                    if btn:
                        await btn.click()
                        clicked_add = True
                        print("[MunAutomation] Clicked 'Add Payment Method' button")
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
                
            # Wait for the card form to appear
            await asyncio.sleep(3)
            
            # 3. Fill the form
            try:
                await self._automate_payment_filling(tab, card)
            except Exception as e_fill:
                print(f"[MunAutomation] Fill error: {e_fill}")
                
            # 4. Click Save
            clicked_save = False
            for _ in range(3):
                try:
                    btn = await self._find_button_by_text(tab, ['save', 'lưu'])
                    if btn:
                        await btn.click()
                        clicked_save = True
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
                
            print("[MunAutomation] Clicked save, waiting for validation results...")
            await asyncio.sleep(6) # Wait for Apple to validate and process
            
            # 5. Check if success or error
            has_error = False
            error_message = ""
            for _ in range(5):
                try:
                    error_els = []
                    try:
                        error_els.extend(await tab.select_all(".error-message, .alert, [role='alert'], .error, .msg-error"))
                    except Exception:
                        pass
                    try:
                        iframes = await tab.select_all("iframe")
                        for iframe in iframes:
                            error_els.extend(await tab.query_selector_all(".error-message, .alert, [role='alert'], .error, .msg-error", iframe))
                    except Exception:
                        pass
                        
                    for el in error_els:
                        txt = el.text.strip()
                        if txt:
                            has_error = True
                            error_message = txt
                            break
                            
                    if has_error:
                        break
                        
                    # Also check for invalid fields (red fields)
                    invalid_els = []
                    try:
                        invalid_els.extend(await tab.select_all(".invalid, [aria-invalid='true']"))
                    except Exception:
                        pass
                    try:
                        iframes = await tab.select_all("iframe")
                        for iframe in iframes:
                            invalid_els.extend(await tab.query_selector_all(".invalid, [aria-invalid='true']", iframe))
                    except Exception:
                        pass
                        
                    if len(invalid_els) > 0:
                        has_error = True
                        error_message = "Thông tin nhập không hợp lệ (Trường đỏ)"
                        break
                except Exception:
                    pass
                await asyncio.sleep(1)
                
            if has_error:
                print(f"[MunAutomation] Card declined/error: {error_message}")
                self.statusMessage.emit(f"❌ Thẻ ****{card_num[-4:]} bị lỗi: {error_message}")
                self.update_card_status_on_server(card.get("id"), "Thẻ chết")
                
                # Click Cancel to close form and reset for next card
                try:
                    btn = await self._find_button_by_text(tab, ['cancel', 'hủy'])
                    if btn:
                        await btn.click()
                except Exception:
                    pass
                await asyncio.sleep(2)
            else:
                print(f"[MunAutomation] Card ****{card_num[-4:]} added successfully!")
                self.statusMessage.emit(f"✅ Thẻ ****{card_num[-4:]} thành công!")
                success_count += 1
                self.update_card_status_on_server(card.get("id"), "Đã sử dụng")
                await asyncio.sleep(3)
                
        # Final result notification
        self.statusMessage.emit(f"🎉 Hoàn tất thêm thẻ: {success_count}/{total_count} thành công!")
        return success_count

    @pyqtSlot(str, str, str, str, result=str)
    @pyqtSlot(str, str, str, str, str, result=str)
    def addPaymentCardsAuto(self, session_id, apple_id, cards_json, proxy="", password=""):
        try:
            print(f"[MunAutomation] Auto Add multiple payment cards requested for Apple ID: {apple_id} (Proxy: {proxy}, has_pass_direct={bool(password)})")
            self.statusMessage.emit(f"🚀 Bắt đầu quá trình thêm thẻ tự động cho {apple_id}...")
            cards = json.loads(cards_json)
            
            import threading
            def run_flow():
                try:
                    # 1. Use password from frontend directly, fallback to server API
                    p_apple_id = apple_id
                    p_password = password  # Direct from frontend
                    p_server_proxy = ""
                    
                    if not p_password:
                        # Fallback: try to fetch from server API
                        try:
                            session = self.get_requests_session()
                            payload = {"session_id": session_id, "apple_id": apple_id}
                            r = session.post(f"{C69_BASE_URL.rstrip('/')}/dashboard/api/apple-sub/get-password/", json=payload, timeout=10)
                            print(f"[MunAutomation] get-password response: status={r.status_code}")
                            if r.status_code == 200:
                                cred_data = r.json()
                                if cred_data.get('success'):
                                    p_apple_id = cred_data.get('apple_id', '') or apple_id
                                    p_password = cred_data.get('password', '')
                                    p_server_proxy = cred_data.get('proxy', '')
                                    print(f"[MunAutomation] Credentials from server: apple_id={p_apple_id}, pass_len={len(p_password)}, proxy={p_server_proxy}")
                                else:
                                    print(f"[MunAutomation] get-password failed: {cred_data.get('message', 'Unknown')}")
                            else:
                                print(f"[MunAutomation] get-password HTTP error: {r.status_code}")
                        except Exception as e_cred:
                            print(f"[MunAutomation] Failed to fetch credentials from server: {e_cred}")
                    else:
                        print(f"[MunAutomation] Using password from frontend directly (len={len(p_password)})")
                        
                    target_apple_id = p_apple_id or apple_id
                    
                    # Use server proxy if no custom proxy provided
                    effective_proxy = proxy or p_server_proxy
                    if effective_proxy and not proxy:
                        print(f"[MunAutomation] Using proxy from server: {effective_proxy}")
                    
                    if not MUN_ANTI_BROWSER_AVAILABLE:
                        self.statusMessage.emit("❌ MunLogin không khả dụng trên hệ thống này.")
                        return

                    # 2. Check if profile already exists on server/locally
                    print(f"[MunAutomation] Checking profile for {target_apple_id}...")
                    self.statusMessage.emit(f"🔍 Đang kiểm tra profile MunLogin cho {target_apple_id}...")
                    
                    profile_id = None
                    try:
                        session = self.get_requests_session()
                        url = f"{C69_BASE_URL.rstrip('/')}/dashboard/api/profiles/"
                        r = session.get(url, timeout=10)
                        if r.status_code == 200:
                            profiles = r.json()
                            results = profiles
                            if isinstance(profiles, dict) and "results" in profiles:
                                results = profiles["results"]
                            for p in results:
                                if p.get("profile_name") == target_apple_id:
                                    profile_id = p.get("id")
                                    print(f"[MunAutomation] Found existing profile: {profile_id}")
                                    break
                    except Exception as e_check:
                        print(f"[MunAutomation] Error searching existing profile: {e_check}")
                        
                    # 3. Create profile if not found
                    if not profile_id:
                        print(f"[MunAutomation] Profile not found. Creating new profile for {target_apple_id}...")
                        self.statusMessage.emit(f"🆕 Không tìm thấy profile. Đang tạo profile mới...")
                        try:
                            manager = NodriverBrowserManager()
                            profile_config = manager.profile_manager.create_random_profile()
                            profile_config["name"] = target_apple_id
                            profile_config["profile_start_url"] = "https://account.apple.com/account/manage/section/payment"
                            
                            from mun_anti_browser.c69_api import local_to_server
                            server_payload = local_to_server(profile_config)
                            
                            url = f"{C69_BASE_URL.rstrip('/')}/dashboard/api/profiles/"
                            r = session.post(url, json=server_payload, timeout=10)
                            if r.status_code == 201:
                                res_data = r.json()
                                profile_id = res_data.get("id")
                                print(f"[MunAutomation] Created profile on server with ID: {profile_id}")
                            else:
                                print(f"[MunAutomation] Server returned status {r.status_code}: {r.text}")
                        except Exception as e_create:
                            print(f"[MunAutomation] Profile creation error: {e_create}")
                            
                    if not profile_id:
                        self.statusMessage.emit("❌ Không thể xác định hoặc tạo profile MunLogin.")
                        return
                        
                    # 4. Fetch the profile details from server to run
                    print(f"[MunAutomation] Loading profile details for ID: {profile_id}...")
                    profile_config = None
                    try:
                        url = f"{C69_BASE_URL.rstrip('/')}/dashboard/api/profiles/{profile_id}/"
                        r = session.get(url, timeout=10)
                        if r.status_code == 200:
                            from mun_anti_browser.c69_api import server_to_local
                            profile_config = server_to_local(r.json())
                    except Exception as e_load:
                        print(f"[MunAutomation] Error loading profile: {e_load}")
                        
                    if not profile_config:
                        manager = NodriverBrowserManager()
                        profile_config = manager.profile_manager.create_random_profile()
                        profile_config["id"] = profile_id
                        profile_config["name"] = target_apple_id
                        profile_config["profile_start_url"] = "https://account.apple.com/account/manage/section/payment"

                    # 5. Start browser
                    self.statusMessage.emit(f"🚀 Đang mở trình duyệt MunLogin profile '{target_apple_id}'...")
                    
                    # Parse custom proxy if provided, otherwise fallback to profile config proxy
                    p_type = "socks5"
                    p_host_port = ""
                    p_user = ""
                    p_pass = ""
                    
                    def parse_proxy_string(proxy_str):
                        if not proxy_str:
                            return "socks5", "", "", ""
                        p_t = "socks5"
                        if proxy_str.startswith("http://"):
                            p_t = "http"
                            proxy_str = proxy_str[7:]
                        elif proxy_str.startswith("socks5://"):
                            p_t = "socks5"
                            proxy_str = proxy_str[9:]
                        pts = proxy_str.split(":")
                        if len(pts) == 2:
                            return p_t, f"{pts[0]}:{pts[1]}", "", ""
                        elif len(pts) == 4:
                            return p_t, f"{pts[0]}:{pts[1]}", pts[2], pts[3]
                        return p_t, proxy_str, "", ""

                    if effective_proxy:
                        p_type, p_host_port, p_user, p_pass = parse_proxy_string(effective_proxy)
                    else:
                        raw_proxy = (
                            profile_config.get("proxy_string") or 
                            profile_config.get("profile_socks5_details") or 
                            profile_config.get("profile_proxy_details", "")
                        )
                        if raw_proxy:
                            p_type, p_host_port, p_user, p_pass = parse_proxy_string(raw_proxy)
                            if profile_config.get("profile_proxy_type") == 1:
                                p_type = "http"
                            elif profile_config.get("profile_proxy_type") == 0:
                                p_host_port = ""

                    manager = NodriverBrowserManager()
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    browser, tab = loop.run_until_complete(manager.start(
                        profile_config=profile_config,
                        proxy_string=p_host_port,
                        proxy_type=p_type,
                        proxy_username=p_user,
                        proxy_password=p_pass
                    ))
                    if not tab:
                        self.statusMessage.emit("❌ Không thể khởi chạy trình duyệt.")
                        return
                        
                    url = "https://account.apple.com/account/manage/section/payment"
                    loop.run_until_complete(tab.get(url))
                    
                    # Helper: get current URL via JS (tab.url is unreliable/empty after redirects)
                    async def get_current_url():
                        try:
                            return await tab.evaluate("window.location.href") or ""
                        except Exception:
                            return tab.url or ""
                    
                    # 6. Wait for page to load (iframe loads automatically)
                    self.statusMessage.emit("⏳ Đang chờ trang Apple tải...")
                    print("[MunAutomation] Waiting for Apple page to load...")
                    loop.run_until_complete(asyncio.sleep(8))
                    
                    initial_url = loop.run_until_complete(get_current_url())
                    print(f"[MunAutomation] Initial URL: {initial_url[:150]}")
                    
                    # 7. Automatic sign-in & 2FA loop (Wait up to 5 minutes)
                    self.statusMessage.emit("⏳ Đang chờ đăng nhập và xác thực 2FA trên trình duyệt...")
                    print("[MunAutomation] Waiting for login / 2FA redirect...")
                    
                    logged_in = False
                    last_login_attempt = 0
                    login_page_keywords = ["idmsa.apple.com", "signin", "sign-in", "authenticate", "iforgot.apple.com"]
                    notified_2fa = False
                    
                    for wait_i in range(300): # Wait up to 5 minutes
                        try:
                            current_url = loop.run_until_complete(get_current_url())
                            
                            # Log every 10 seconds for debug
                            if wait_i % 10 == 0:
                                print(f"[MunAutomation] Wait loop #{wait_i}: url={current_url[:120]}, has_creds={bool(p_password)}")
                            
                            # Check if successfully logged in and redirected back to account manage section
                            if "account.apple.com/account/manage" in current_url or "account.apple.com/manage" in current_url:
                                if not any(kw in current_url for kw in login_page_keywords):
                                    logged_in = True
                                    print(f"[MunAutomation] Login success detected! URL: {current_url[:120]}")
                                    break
                                    
                            # If we are on the login/signin page, and we haven't tried logging in recently
                            is_login_page = any(kw in current_url.lower() for kw in login_page_keywords)
                            
                            # Also check if there's an email input visible (even if URL doesn't match)
                            if not is_login_page and wait_i > 5:
                                try:
                                    has_input = loop.run_until_complete(tab.evaluate("""
                                        !!(document.querySelector('input[type="email"]') || 
                                           document.querySelector('input#account_name_text_field') ||
                                           document.querySelector('input[name="account_name"]'))
                                    """))
                                    if has_input:
                                        is_login_page = True
                                except Exception:
                                    pass
                            
                            # Detect 2FA screen to alert the client
                            is_2fa_page = False
                            try:
                                is_2fa, _ = loop.run_until_complete(self._evaluate_in_iframe_robust(tab, """
                                    (() => {
                                        const hasVerifyInputs = !!(
                                            document.querySelector('input[id^="char"]') || 
                                            document.querySelector('.digit-input') || 
                                            document.querySelector('.verify-code-input') || 
                                            document.querySelector('.security-code-input')
                                        );
                                        const has2FAText = document.body && (
                                            document.body.innerText.includes('Two-Factor Authentication') || 
                                            document.body.innerText.includes('Xác thực hai yếu tố') ||
                                            document.body.innerText.includes('Xác minh Mã xác thực')
                                        );
                                        return hasVerifyInputs || has2FAText;
                                    })()
                                """))
                                if is_2fa:
                                    is_2fa_page = True
                            except Exception:
                                pass
                                
                            if is_2fa_page:
                                if not notified_2fa:
                                    self.statusMessage.emit("⚠️ Yêu cầu mã 2FA! Vui lòng nhập mã 6 số vào trình duyệt MunLogin.")
                                    print("[MunAutomation] 2FA screen detected. Prompting user...")
                                    notified_2fa = True
                            else:
                                if notified_2fa and wait_i % 10 == 0:
                                    # Reset notification status if no longer on 2FA page (e.g. page transition)
                                    notified_2fa = False
                            
                            if is_login_page and (time.time() - last_login_attempt > 15):
                                if target_apple_id and p_password:
                                    print(f"[MunAutomation] Login screen detected: {current_url[:100]}. Triggering auto sign-in...")
                                    self.statusMessage.emit("🔑 Phát hiện màn hình đăng nhập. Đang tự động điền tài khoản...")
                                    last_login_attempt = time.time()
                                    try:
                                        # Wait a bit for page to fully render before interacting
                                        loop.run_until_complete(asyncio.sleep(3))
                                        success = loop.run_until_complete(self._automate_apple_login(tab, target_apple_id, p_password))
                                        if success:
                                            self.statusMessage.emit("⏳ Đã điền xong thông tin. Đang chờ 2FA...")
                                        else:
                                            print("[MunAutomation] _automate_apple_login returned False")
                                    except Exception as e_login:
                                        print(f"[MunAutomation] Retried Sign-in automation error: {e_login}")
                                        import traceback
                                        traceback.print_exc()
                                else:
                                    if wait_i % 30 == 0:
                                        print(f"[MunAutomation] On login page but no credentials: apple_id={target_apple_id}, has_pass={bool(p_password)}")
                        except Exception as e_check:
                            print(f"[MunAutomation] Wait loop error: {e_check}")
                        time.sleep(1)
                        
                    if not logged_in:
                        self.statusMessage.emit("❌ Đăng nhập thất bại (Hết hạn chờ 2FA).")
                        return
                        
                    self.statusMessage.emit("✅ Đăng nhập Apple ID thành công! Đang chuyển đến trang thêm thẻ...")
                    time.sleep(3)
                    
                    # 8. Start adding cards
                    try:
                        loop.run_until_complete(self._automate_add_payment_cards(tab, cards))
                    except Exception as e_add_cards:
                        print(f"[MunAutomation] Error during card addition flow: {e_add_cards}")
                        self.statusMessage.emit(f"❌ Có lỗi trong quá trình thêm thẻ: {str(e_add_cards)}")
                except Exception as ex:
                    print(f"[MunAutomation] run_flow error: {ex}")
                    self.statusMessage.emit(f"❌ Lỗi hệ thống: {str(ex)}")

            t = threading.Thread(target=run_flow, daemon=True)
            t.start()
            return json.dumps({"success": True, "message": "Đang khởi chạy tiến trình thêm thẻ tự động..."})
        except Exception as e:
            return json.dumps({"error": str(e)})

    @pyqtSlot(str, str, result=str)
    def executeSubscription(self, session_id, tiktok_username):
        try:
            print(f"[MunAutomation] Execute subscription for TikTok {tiktok_username} using session {session_id}")
            self.statusMessage.emit(f"⚡ Đang thực thi Subscribe TikTok @{tiktok_username}...")
            return json.dumps({"success": True, "message": f"Đang thực thi tác vụ Subscribe cho {tiktok_username}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

# Backward compatibility alias
QHTDBridge = MunAutomationBridge


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
class MunAutomationStoreDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.bridge = None
        self.web_view = None
        self._cookie_store = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"MunAutomation — C69.US v{CLIENT_VERSION}")
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

        # === STACKED WIDGET (for loading screen and web view) ===
        self.stacked_widget = QStackedWidget()
        main_layout.addWidget(self.stacked_widget, 1)

        # Loading screen
        self.loading_widget = QWidget()
        self.loading_widget.setStyleSheet("background-color: #080b11;")
        loading_layout = QVBoxLayout(self.loading_widget)
        
        loading_label = QLabel("Đang tải dữ liệu, vui lòng đợi...")
        loading_label.setStyleSheet("color: #06b6d4; font-size: 20px; font-weight: bold; margin-bottom: 20px;")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        loading_desc = QLabel("MunAutomation đang khởi tạo...")
        loading_desc.setStyleSheet("color: #94a3b8; font-size: 14px;")
        loading_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        loading_layout.addStretch()
        loading_layout.addWidget(loading_label)
        loading_layout.addWidget(loading_desc)
        loading_layout.addStretch()

        self.stacked_widget.addWidget(self.loading_widget)

        # === WEB ENGINE VIEW (main content) ===
        self.setup_web_engine()
        self.stacked_widget.addWidget(self.web_view)

        # Hiển thị loading overlay mặc định và kết nối signals
        self.stacked_widget.setCurrentWidget(self.loading_widget)
        self.web_view.loadStarted.connect(lambda: self.stacked_widget.setCurrentWidget(self.loading_widget))
        self.web_view.loadFinished.connect(lambda: self.stacked_widget.setCurrentWidget(self.web_view))
        # Phòng hờ trường hợp không có tín hiệu loadFinished
        QTimer.singleShot(15000, lambda: self.stacked_widget.setCurrentWidget(self.web_view))

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

        version_label = QLabel(f"MunAutomation v{CLIENT_VERSION} • PyQt6 + Chromium")
        version_label.setStyleSheet("color: #475569; font-size: 10px;")
        status_layout.addWidget(version_label)

        main_layout.addWidget(status_bar)

    def setup_web_engine(self):
        """Thiết lập QWebEngineView + QWebChannel bridge"""
        # Read qwebchannel.js from Qt resources
        self.qwebchannel_js = ""
        file = QFile(":/qtwebchannel/qwebchannel.js")
        if file.open(QIODevice.OpenModeFlag.ReadOnly):
            self.qwebchannel_js = bytes(file.readAll()).decode("utf-8")
            file.close()

        # Create web view first (with parent)
        self.web_view = QWebEngineView(self)
        self.web_view.page().setBackgroundColor(QColor("#080b11"))
        
        # Get the default profile and customize it
        profile = QWebEngineProfile.defaultProfile()
        # Removed synchronous profile.clearHttpCache() on startup to avoid blocking GUI thread
        profile.setHttpUserAgent(
            f"MunAutomation-Desktop/{CLIENT_VERSION} "
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
        # Bỏ chặn Mixed Content để cho phép fetch từ https (c69.us) tới http (127.0.0.1)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
        # Performance: enable accelerated 2D/WebGL canvas
        settings.setAttribute(QWebEngineSettings.WebAttribute.Accelerated2dCanvasEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.WebGLEnabled, True)

        # Setup QWebChannel bridge
        self.bridge = MunAutomationBridge(self)
        self.bridge._cookie_jar = []  # shared cookie jar reference
        self._load_cookies_from_disk()
        QTimer.singleShot(3000, self.bridge.start_poll_thread)
        channel = QWebChannel(self)
        channel.registerObject("munAutomationBridge", self.bridge)
        channel.registerObject("qhtdBridge", self.bridge)
        page.setWebChannel(channel)

        # Connect bridge signals to status bar updates
        self.bridge.statusMessage.connect(self.update_status)
        self.bridge.automationLog.connect(self.on_automation_log)

        # Inject qwebchannel.js before loading
        # The web frontend will detect window.munAutomationBridge / window.qhtdBridge and show extra tabs
        page.loadFinished.connect(self.on_page_loaded)

        # Load web URL
        if "--test-tor" in sys.argv:
            self.web_view.setUrl(QUrl(C69_BASE_URL + "/?tab=proxies"))
            QTimer.singleShot(8000, self.take_test_screenshot)
        else:
            self.web_view.setUrl(QUrl(C69_BASE_URL))

        # Add reload shortcuts to easily refresh frontend code
        from PyQt6.QtGui import QShortcut, QKeySequence
        self.reload_shortcut = QShortcut(QKeySequence("F5"), self)
        self.reload_shortcut.activated.connect(self.web_view.reload)
        self.hard_reload_shortcut = QShortcut(QKeySequence("Ctrl+F5"), self)
        self.hard_reload_shortcut.activated.connect(lambda: self.web_view.page().triggerAction(QWebEnginePage.WebAction.ReloadAndBypassCache))

    # --- Cookie sharing helpers ---
    def _save_cookies_to_disk_debounced(self):
        """Lưu cookie jar xuống disk bằng QTimer để tránh freeze GUI thread"""
        if not hasattr(self, "_cookie_save_timer"):
            self._cookie_save_timer = QTimer(self)
            self._cookie_save_timer.setSingleShot(True)
            self._cookie_save_timer.setInterval(500) # 500ms delay
            self._cookie_save_timer.timeout.connect(self._save_cookies_to_disk)
        self._cookie_save_timer.start()

    def _on_cookie_added(self, cookie):
        """Khi browser thêm cookie → sync sang Python cookie jar và lưu vào disk"""
        if not self.bridge:
            return
        
        expiration = ""
        if not cookie.isSessionCookie():
            expiration = cookie.expirationDate().toString(Qt.DateFormat.ISODate)
            
        cookie_dict = {
            'name': bytes(cookie.name()).decode('utf-8', errors='replace'),
            'value': bytes(cookie.value()).decode('utf-8', errors='replace'),
            'domain': cookie.domain(),
            'path': cookie.path(),
            'secure': cookie.isSecure(),
            'httponly': cookie.isHttpOnly(),
            'expiration': expiration,
        }
        # Avoid duplicates of same name to prevent domain conflicts (e.g. c69.us vs .c69.us)
        jar = self.bridge._cookie_jar
        for i, c in enumerate(jar):
            if c['name'] == cookie_dict['name']:
                if c['value'] == cookie_dict['value'] and c['domain'] == cookie_dict['domain']:
                    return
                jar[i] = cookie_dict
                self._save_cookies_to_disk_debounced()
                return
        jar.append(cookie_dict)
        self._save_cookies_to_disk_debounced()

    def _on_cookie_removed(self, cookie):
        """Khi browser xóa cookie → remove khỏi Python cookie jar và lưu vào disk"""
        if not self.bridge:
            return
        name = bytes(cookie.name()).decode('utf-8', errors='replace')
        domain = cookie.domain()
        old_len = len(self.bridge._cookie_jar)
        self.bridge._cookie_jar = [
            c for c in self.bridge._cookie_jar
            if not (c['name'] == name and c['domain'] == domain)
        ]
        if len(self.bridge._cookie_jar) != old_len:
            self._save_cookies_to_disk_debounced()

    def on_page_loaded(self, ok):
        """Sau khi page load xong, inject qwebchannel.js và bridge detection script"""
        if ok:
            self.update_status("Đã kết nối c69.us")
            
            # 1. Inject qwebchannel.js source code
            if hasattr(self, 'qwebchannel_js') and self.qwebchannel_js:
                self.web_view.page().runJavaScript(self.qwebchannel_js)
            
            # 2. Inject initialization script to connect to the channel
            self.web_view.page().runJavaScript("""
                if (typeof QWebChannel !== 'undefined') {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.munAutomationBridge = channel.objects.munAutomationBridge;
                        window.qhtdBridge = channel.objects.munAutomationBridge || channel.objects.qhtdBridge;
                        window.__MUNAUTOMATION_DESKTOP__ = true;
                        window.__QHTD_DESKTOP__ = true;
                        window.__MUNAUTOMATION_VERSION__ = '%s';
                        console.log('[MunAutomation] QWebChannel bridge connected successfully, version %s');
                        // Dispatch ready event to notify frontend
                        var event = new CustomEvent('munAutomationBridgeReady');
                        window.dispatchEvent(event);
                        var event2 = new CustomEvent('qhtdBridgeReady');
                        window.dispatchEvent(event2);
                    });
                } else {
                    console.error('[MunAutomation] Failed to load QWebChannel script!');
                }
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
        if self.bridge:
            # Stop poll thread
            if hasattr(self.bridge, 'poll_running'):
                self.bridge.poll_running = False
            if hasattr(self.bridge, 'poll_thread') and self.bridge.poll_thread and self.bridge.poll_thread.is_alive():
                self.bridge.poll_thread.join(timeout=3.0)
            
            # Stop router poll thread
            if hasattr(self.bridge, 'router_poll_running'):
                self.bridge.router_poll_running = False
            if hasattr(self.bridge, 'router_poll_thread') and self.bridge.router_poll_thread and self.bridge.router_poll_thread.is_alive():
                self.bridge.router_poll_thread.join(timeout=3.0)
            
            # Stop all active browser workers
            if hasattr(self.bridge, 'browser_workers') and self.bridge.browser_workers:
                for pid, worker in list(self.bridge.browser_workers.items()):
                    if worker.isRunning():
                        worker.stop_browser()
                        worker.wait(3000)

            if self.bridge.automation_worker and self.bridge.automation_worker.isRunning():
                self.bridge.automation_worker.stop()
                self.bridge.automation_worker.wait(3000)
            if hasattr(self.bridge, 'wda_setup_worker') and self.bridge.wda_setup_worker and self.bridge.wda_setup_worker.isRunning():
                self.bridge.wda_setup_worker.terminate()
                self.bridge.wda_setup_worker.wait(3000)
            if hasattr(self.bridge, 'dopamine_worker') and self.bridge.dopamine_worker and self.bridge.dopamine_worker.isRunning():
                self.bridge.dopamine_worker.stop()
                self.bridge.dopamine_worker.wait(3000)
            if hasattr(self.bridge, 'tor_monitor_worker') and self.bridge.tor_monitor_worker and self.bridge.tor_monitor_worker.isRunning():
                self.bridge.tor_monitor_worker.stop()
                self.bridge.tor_monitor_worker.wait(3000)
            if hasattr(self.bridge, 'tor_download_worker') and self.bridge.tor_download_worker and self.bridge.tor_download_worker.isRunning():
                self.bridge.tor_download_worker.terminate()
                self.bridge.tor_download_worker.wait(3000)
            if hasattr(self.bridge, 'stopAllTorProxies'):
                self.bridge.stopAllTorProxies()
            if hasattr(self.bridge, 'stopRouter'):
                self.bridge.stopRouter()
        event.accept()

    def take_test_screenshot(self):
        """Take a screenshot of the main window and save it to the artifacts folder for verification"""
        try:
            artifact_dir = r"C:\Users\Admin\.gemini\antigravity-ide\brain\097d037d-cccf-4aa3-810d-46f4d5d6e18a"
            os.makedirs(artifact_dir, exist_ok=True)
            screenshot_path = os.path.join(artifact_dir, "tor_proxies_test.png")
            
            pixmap = self.grab()
            success = pixmap.save(screenshot_path, "PNG")
            print(f"[QHTD TEST] Screenshot saved to {screenshot_path}: {success}", flush=True)
            
            # Since this is a test run, close the app after capturing
            QTimer.singleShot(1000, QApplication.instance().quit)
        except Exception as e:
            print(f"[QHTD TEST ERROR] Failed to take screenshot: {e}", flush=True)

    def _save_cookies_to_disk(self):
        """Lưu cookie jar xuống file json để khôi phục sau khi khởi động app"""
        try:
            cookies_file = os.path.join(get_app_dir(), "session_cookies.json")
            with open(cookies_file, "w", encoding="utf-8") as f:
                json.dump(self.bridge._cookie_jar, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[QHTD COOKIE SAVE ERROR] {e}", flush=True)

    def _load_cookies_from_disk(self):
        """Đọc cookies từ file json và nạp vào cookie store của WebEngine"""
        try:
            cookies_file = os.path.join(get_app_dir(), "session_cookies.json")
            if not os.path.exists(cookies_file):
                return
            with open(cookies_file, "r", encoding="utf-8") as f:
                saved_cookies = json.load(f)
            
            if not isinstance(saved_cookies, list):
                return
            
            # Deduplicate cookies by name (keeping the latest or the one with expiration)
            deduped = {}
            for c in saved_cookies:
                name = c.get('name')
                if name not in deduped:
                    deduped[name] = c
                else:
                    old_c = deduped[name]
                    if c.get('expiration') and not old_c.get('expiration'):
                        deduped[name] = c
                    elif len(c.get('value', '')) > len(old_c.get('value', '')):
                        deduped[name] = c
            saved_cookies = list(deduped.values())
            
            self.bridge._cookie_jar = saved_cookies
            
            for c_dict in saved_cookies:
                qcookie = QNetworkCookie(
                    c_dict.get('name', '').encode('utf-8'),
                    c_dict.get('value', '').encode('utf-8')
                )
                cookie_domain = c_dict.get('domain', '')
                qcookie.setDomain(cookie_domain)
                qcookie.setPath(c_dict.get('path', '/'))
                qcookie.setSecure(c_dict.get('secure', False))
                qcookie.setHttpOnly(c_dict.get('httponly', False))
                
                exp_str = c_dict.get('expiration', '')
                if exp_str:
                    qdt = QDateTime.fromString(exp_str, Qt.DateFormat.ISODate)
                    if qdt.isValid():
                        qcookie.setExpirationDate(qdt)
                
                domain_clean = cookie_domain.lstrip('.')
                if domain_clean:
                    target_url = QUrl(f"https://{domain_clean}")
                else:
                    target_url = QUrl(C69_BASE_URL)
                    
                self._cookie_store.setCookie(qcookie, target_url)
                
            print(f"[QHTD COOKIES] Loaded {len(saved_cookies)} cookies from disk successfully", flush=True)
        except Exception as e:
            print(f"[QHTD COOKIE LOAD ERROR] {e}", flush=True)


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
        '--enable-gpu-rasterization '
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
        print("[MunAutomation] Step 3: Font set OK", flush=True)

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
        print("[MunAutomation] Step 4: Stylesheet set OK", flush=True)

        print("[MunAutomation] Step 5: Creating MunAutomationStoreDesktop...", flush=True)
        window = MunAutomationStoreDesktop()
        print("[MunAutomation] Step 6: Window created OK", flush=True)

        window.show()
        print("[MunAutomation] Step 7: Window shown OK — entering event loop", flush=True)

        ret = app.exec()
        print(f"[MunAutomation] Step 8: Event loop ended with code {ret}", flush=True)
        sys.exit(ret)
    except Exception as e:
        print(f"[QHTD FATAL ERROR] {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)
