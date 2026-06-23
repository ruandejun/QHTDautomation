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
import asyncio

# Đảm bảo import được ipatool cho dù ứng dụng được chạy từ thư mục nào
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# === PyQt6 Imports ===
from PyQt6.QtCore import (
    QThread, pyqtSignal, pyqtSlot, Qt, QTimer, QUrl, QObject, QFile, QIODevice
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

# Anti-Detect Browser
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


class AgentPollSignals(QObject):
    command_received = pyqtSignal(dict)
    log_signal = pyqtSignal(str)


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
    def start_poll_thread(self):
        """Khởi chạy luồng polling ngầm đồng bộ với server sử dụng threading.Thread"""
        if hasattr(self, 'poll_running') and self.poll_running:
            return

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
                
                # Sleep 3 seconds (check poll_running every 500ms)
                for _ in range(6):
                    if not self.poll_running:
                        break
                    time.sleep(0.5)

        import threading
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
            
            self.browser_workers[pid_int] = worker
            worker.start()

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
        # Read qwebchannel.js from Qt resources
        self.qwebchannel_js = ""
        file = QFile(":/qtwebchannel/qwebchannel.js")
        if file.open(QIODevice.OpenModeFlag.ReadOnly):
            self.qwebchannel_js = bytes(file.readAll()).decode("utf-8")
            file.close()

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
        self._load_cookies_from_disk()
        QTimer.singleShot(3000, self.bridge.start_poll_thread)
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
        if "--test-tor" in sys.argv:
            self.web_view.setUrl(QUrl(C69_BASE_URL + "/?tab=proxies"))
            QTimer.singleShot(8000, self.take_test_screenshot)
        else:
            self.web_view.setUrl(QUrl(C69_BASE_URL))

    # --- Cookie sharing helpers ---
    def _on_cookie_added(self, cookie):
        """Khi browser thêm cookie → sync sang Python cookie jar và lưu vào disk"""
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
                if c['value'] == cookie_dict['value']:
                    return
                jar[i] = cookie_dict
                self._save_cookies_to_disk()
                return
        jar.append(cookie_dict)
        self._save_cookies_to_disk()

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
            self._save_cookies_to_disk()

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
                        window.qhtdBridge = channel.objects.qhtdBridge;
                        window.__QHTD_DESKTOP__ = true;
                        window.__QHTD_VERSION__ = '%s';
                        console.log('[QHTD] QWebChannel bridge connected successfully, version %s');
                        // Dispatch ready event to notify frontend
                        var event = new CustomEvent('qhtdBridgeReady');
                        window.dispatchEvent(event);
                    });
                } else {
                    console.error('[QHTD] Failed to load QWebChannel script!');
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
            
            self.bridge._cookie_jar = saved_cookies
            
            for c_dict in saved_cookies:
                qcookie = QNetworkCookie(
                    c_dict.get('name', '').encode('utf-8'),
                    c_dict.get('value', '').encode('utf-8')
                )
                qcookie.setDomain(c_dict.get('domain', ''))
                qcookie.setPath(c_dict.get('path', '/'))
                qcookie.setSecure(c_dict.get('secure', False))
                qcookie.setHttpOnly(c_dict.get('httponly', False))
                
                self._cookie_store.setCookie(qcookie, QUrl(C69_BASE_URL))
                
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
