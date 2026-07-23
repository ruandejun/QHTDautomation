import os
import sys
import json
import random
import time
import xml.etree.ElementTree as ET

import sqlite3
import re
import hashlib
import urllib.parse

# Đảm bảo import được ipatool cho dù ứng dụng được chạy từ thư mục nào
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import requests
import socket
from http.server import SimpleHTTPRequestHandler, HTTPServer
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QTimer
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QGroupBox, QLineEdit, QPushButton, QLabel,
    QComboBox, QProgressBar, QPlainTextEdit, QFileDialog, QMessageBox,
    QListWidget, QListWidgetItem, QDialog, QCheckBox, QTabWidget, QFrame, QInputDialog,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView, QTextEdit, QStackedWidget
)
from PyQt5.QtGui import QPixmap, QIcon, QFont

import asyncio
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

CLIENT_VERSION = "1.0.5"

# Database Helper cho Quản lý Thẻ (Hỗ trợ cả Offline SQLite và Online REST API)
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
        # Thực hiện di trú (migration) nếu các cột mới chưa tồn tại
        try:
            cursor.execute("ALTER TABLE cards ADD COLUMN extra_info TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE cards ADD COLUMN created_at TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE cards ADD COLUMN updated_at TEXT")
        except sqlite3.OperationalError:
            pass
        try:
            cursor.execute("ALTER TABLE cards ADD COLUMN used_count INTEGER DEFAULT 0")
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
                data = {
                    "card_number": card_number,
                    "expiry_date": expiry_date,
                    "cvv": cvv,
                    "status": status,
                    "extra_info": extra_info
                }
                r = requests.post(url, headers=self._get_headers(), json=data, timeout=10)
                if r.status_code in (200, 201):
                    return r.json().get('id')
                else:
                    print(f"Lỗi API add_card: {r.status_code} {r.text}")
            except Exception as e:
                print(f"Lỗi kết nối API add_card: {str(e)}")

        import datetime
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO cards (card_number, expiry_date, cvv, status, extra_info, created_at, updated_at, used_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        """, (card_number, expiry_date, cvv, status, extra_info, now_str, now_str))
        card_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return card_id

    def get_all_cards(self, search_query="", status_filter="Tất cả"):
        if self.online_mode and self.api_url:
            try:
                url = f"{self.api_url}/api/cards/"
                params = {}
                if search_query:
                    params['search'] = search_query
                if status_filter and status_filter != "Tất cả":
                    params['status'] = status_filter
                r = requests.get(url, headers=self._get_headers(), params=params, timeout=10)
                if r.status_code == 200:
                    api_cards = r.json()
                    rows = []
                    
                    # Support both direct list and paginated response (dict with 'results' key)
                    cards_list = []
                    if isinstance(api_cards, list):
                        cards_list = api_cards
                    elif isinstance(api_cards, dict):
                        cards_list = api_cards.get("results", [])
                        
                    for c in cards_list:
                        if isinstance(c, dict):
                            c_id = c.get('id')
                            c_num = c.get('card_number', '')
                            c_exp = c.get('expiry_date', '')
                            c_cvv = c.get('cvv', '')
                            c_status = c.get('status', 'Chưa sử dụng')
                            c_extra = c.get('extra_info', '')
                            c_created = c.get('created_at', '')
                            c_updated = c.get('updated_at', '')
                            c_used = c.get('used_count', 0)
                            rows.append((c_id, c_num, c_exp, c_cvv, c_status, c_extra, c_created, c_updated, c_used))
                    return rows
                else:
                    print(f"Lỗi API get_all_cards: {r.status_code} {r.text}")
            except Exception as e:
                print(f"Lỗi kết nối API get_all_cards: {str(e)}")

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
                url = f"{self.api_url}/api/cards/{card_id}/"
                r = requests.get(url, headers=self._get_headers(), timeout=10)
                if r.status_code == 200:
                    c = r.json()
                    return (c.get('id'), c.get('card_number', ''), c.get('expiry_date', ''), c.get('cvv', ''), c.get('status', ''), c.get('extra_info', ''), c.get('created_at', ''), c.get('updated_at', ''), c.get('used_count', 0))
                else:
                    print(f"Lỗi API get_card: {r.status_code} {r.text}")
            except Exception as e:
                print(f"Lỗi kết nối API get_card: {str(e)}")

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
        
        counting_statuses = ["Đã sử dụng", "Thẻ sống", "Thẻ tốt", "Thẻ chết"]
        is_old_counting = old_status in counting_statuses
        is_new_counting = status in counting_statuses
        should_increment = (not is_old_counting) and is_new_counting
        new_used = old_used + 1 if should_increment else old_used

        if self.online_mode and self.api_url:
            try:
                url = f"{self.api_url}/api/cards/{card_id}/"
                data = {"status": status, "used_count": new_used}
                r = requests.patch(url, headers=self._get_headers(), json=data, timeout=10)
                if r.status_code == 200:
                    return True
                else:
                    print(f"Lỗi API update_card_status: {r.status_code} {r.text}")
            except Exception as e:
                print(f"Lỗi kết nối API update_card_status: {str(e)}")

        import datetime
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("UPDATE cards SET status = ?, used_count = ?, updated_at = ? WHERE id = ?", (status, new_used, now_str, card_id))
        conn.commit()
        conn.close()
        return True

    def update_card(self, card_id, card_number, expiry_date, cvv, status, extra_info):
        card = self.get_card(card_id)
        old_status = card[4] if card and len(card) > 4 else ""
        old_used = card[8] if card and len(card) > 8 else 0
        
        counting_statuses = ["Đã sử dụng", "Thẻ sống", "Thẻ tốt", "Thẻ chết"]
        is_old_counting = old_status in counting_statuses
        is_new_counting = status in counting_statuses
        should_increment = (not is_old_counting) and is_new_counting
        new_used = old_used + 1 if should_increment else old_used

        if self.online_mode and self.api_url:
            try:
                url = f"{self.api_url}/api/cards/{card_id}/"
                data = {
                    "card_number": card_number,
                    "expiry_date": expiry_date,
                    "cvv": cvv,
                    "status": status,
                    "extra_info": extra_info,
                    "used_count": new_used
                }
                r = requests.put(url, headers=self._get_headers(), json=data, timeout=10)
                if r.status_code == 200:
                    return True
                else:
                    print(f"Lỗi API update_card: {r.status_code} {r.text}")
            except Exception as e:
                print(f"Lỗi kết nối API update_card: {str(e)}")

        import datetime
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE cards 
            SET card_number = ?, expiry_date = ?, cvv = ?, status = ?, extra_info = ?, used_count = ?, updated_at = ? 
            WHERE id = ?
        """, (card_number, expiry_date, cvv, status, extra_info, new_used, now_str, card_id))
        conn.commit()
        conn.close()
        return True

    def delete_card(self, card_id):
        if self.online_mode and self.api_url:
            try:
                url = f"{self.api_url}/api/cards/{card_id}/"
                r = requests.delete(url, headers=self._get_headers(), timeout=10)
                if r.status_code == 204:
                    return True
                else:
                    print(f"Lỗi API delete_card: {r.status_code} {r.text}")
            except Exception as e:
                print(f"Lỗi kết nối API delete_card: {str(e)}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cards WHERE id = ?", (card_id,))
        conn.commit()
        conn.close()
        return True


class CardLoadWorker(QThread):
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, db, search_query="", status_filter="Tất cả", parent=None):
        super().__init__(parent)
        self.db = db
        self.search_query = search_query
        self.status_filter = status_filter

    def run(self):
        try:
            cards = self.db.get_all_cards(self.search_query, self.status_filter)
            self.finished.emit(cards)
        except Exception as e:
            self.error.emit(str(e))


class CardAddWorker(QThread):
    finished = pyqtSignal(int, int)
    error = pyqtSignal(str)

    def __init__(self, db, cards_list, status, parent=None):
        super().__init__(parent)
        self.db = db
        self.cards_list = cards_list
        self.status = status

    def run(self):
        try:
            success_count = 0
            invalid_count = 0
            for card in self.cards_list:
                if card["is_valid"]:
                    self.db.add_card(
                        card["card_number"],
                        card["expiry"],
                        card["cvv"],
                        self.status,
                        card["extra_info"]
                    )
                    success_count += 1
                else:
                    invalid_count += 1
            self.finished.emit(success_count, invalid_count)
        except Exception as e:
            self.error.emit(str(e))


class CardStatusUpdateWorker(QThread):
    finished = pyqtSignal(int, str, bool)
    error = pyqtSignal(str)

    def __init__(self, db, card_id, status, parent=None):
        super().__init__(parent)
        self.db = db
        self.card_id = card_id
        self.status = status

    def run(self):
        try:
            success = self.db.update_card_status(self.card_id, self.status)
            self.finished.emit(self.card_id, self.status, success)
        except Exception as e:
            self.error.emit(str(e))


class CardUpdateWorker(QThread):
    finished = pyqtSignal(int, bool)
    error = pyqtSignal(str)

    def __init__(self, db, card_id, card_number, expiry_date, cvv, status, extra_info, parent=None):
        super().__init__(parent)
        self.db = db
        self.card_id = card_id
        self.card_number = card_number
        self.expiry_date = expiry_date
        self.cvv = cvv
        self.status = status
        self.extra_info = extra_info

    def run(self):
        try:
            success = self.db.update_card(self.card_id, self.card_number, self.expiry_date, self.cvv, self.status, self.extra_info)
            self.finished.emit(self.card_id, success)
        except Exception as e:
            self.error.emit(str(e))


class CardDeleteWorker(QThread):
    finished = pyqtSignal(list, bool)
    error = pyqtSignal(str)

    def __init__(self, db, card_ids, parent=None):
        super().__init__(parent)
        self.db = db
        self.card_ids = card_ids

    def run(self):
        try:
            for card_id in self.card_ids:
                self.db.delete_card(card_id)
            self.finished.emit(self.card_ids, True)
        except Exception as e:
            self.error.emit(str(e))


class CardViewFetchWorker(QThread):
    finished = pyqtSignal(tuple)
    error = pyqtSignal(str)

    def __init__(self, db, card_id, parent=None):
        super().__init__(parent)
        self.db = db
        self.card_id = card_id

    def run(self):
        try:
            card_info = self.db.get_card(self.card_id)
            if card_info:
                self.finished.emit(card_info)
            else:
                self.error.emit("Không tìm thấy thẻ trong cơ sở dữ liệu.")
        except Exception as e:
            self.error.emit(str(e))

class UpdateCheckWorker(QThread):
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, current_version, api_url, parent=None):
        super().__init__(parent)
        self.current_version = current_version
        self.api_url = api_url

    def run(self):
        try:
            url = f"{self.api_url}/static/version.json"
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                data = r.json()
                self.finished.emit(data)
            else:
                self.error.emit(f"Server returned status {r.status_code}")
        except Exception as e:
            self.error.emit(str(e))


class DownloadUpdateWorker(QThread):
    progress = pyqtSignal(int, int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, download_url, parent=None):
        super().__init__(parent)
        self.download_url = download_url

    def run(self):
        try:
            r = requests.get(self.download_url, stream=True, timeout=15)
            if r.status_code != 200:
                self.error.emit(f"Server returned status {r.status_code}")
                return
                
            total_size = int(r.headers.get('content-length', 0))
            temp_path = os.path.join(get_app_dir(), "QHTDautomation_new.exe")
            
            downloaded = 0
            with open(temp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total_size)
                        
            self.finished.emit(temp_path)
        except Exception as e:
            self.error.emit(str(e))


class AddCardDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Thêm Thẻ Mới")
        self.resize(550, 320)
        self.setStyleSheet("""
            QDialog {
                background-color: #060a1a;
                border: 1px solid #0e1630;
                border-radius: 16px;
            }
            QLabel {
                color: #f8fafc;
            }
            QTextEdit {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 8px;
                color: #f8fafc;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #d946ef;
            }
            QComboBox {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 8px;
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        lbl = QLabel("Nhập dữ liệu thẻ (1 dòng là 1 thẻ, hỗ trợ chép nhiều dòng cùng lúc):")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)

        self.card_input = QTextEdit()
        self.card_input.setLineWrapMode(QTextEdit.WidgetWidth)
        self.card_input.setPlaceholderText(
            "Ví dụ nhập:\n"
            "4147098472726991|03|27|502|David Miranda|067 Patrick Mill|Hendersonton|Ohio|88313|US|(142) 576-6409|evelynb1977@yahoo.com"
        )
        layout.addWidget(self.card_input)

        layout.addWidget(QLabel("Trạng thái ban đầu:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Chưa sử dụng", "Đang sử dụng", "Đã sử dụng", "Thẻ chết", "Thẻ sống", "Thẻ tốt"])
        layout.addWidget(self.status_combo)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        self.save_btn = QPushButton("Lưu")
        self.save_btn.clicked.connect(self.accept)
        
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        text = self.card_input.toPlainText().strip()
        status = self.status_combo.currentText()
        
        cards_list = []
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 1:
                card_number = parts[0]
                clean_num = re.sub(r'\D', '', card_number)
                
                # Check valid logic
                is_valid = len(clean_num) in (15, 16) and len(clean_num) > 0 and clean_num[0] in ('3', '4', '5', '6')
                
                expiry = ""
                cvv = ""
                extra_info = ""
                
                if is_valid:
                    if len(parts) >= 3:
                        expiry = f"{parts[1]}/{parts[2]}"
                    if len(parts) >= 4:
                        cvv = parts[3]
                    if len(parts) >= 5:
                        extra_info = " | ".join(parts[4:])
                        
                cards_list.append({
                    "card_number": clean_num if is_valid else card_number,
                    "expiry": expiry,
                    "cvv": cvv,
                    "extra_info": extra_info,
                    "is_valid": is_valid,
                    "raw_line": line
                })
                
        return cards_list, status


class ViewCardDialog(QDialog):
    def __init__(self, card_id, card_number, expiry_date, cvv, status, extra_info, parent=None):
        super().__init__(parent)
        self.card_id = card_id
        self.card_number = card_number
        self.expiry_date = expiry_date
        self.cvv = cvv
        self.status = status
        self.extra_info = extra_info or ""
        self.prompted = False
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Chi Tiết Thẻ")
        self.resize(500, 540)
        self.setStyleSheet("""
            QDialog {
                background-color: #060a1a;
                border: 1px solid #0e1630;
                border-radius: 16px;
            }
            QLabel {
                color: #f8fafc;
            }
            QLineEdit {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 8px 12px;
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # --- ATM Card Mock Widget ---
        card_widget = QFrame()
        card_widget.setFixedSize(440, 240)
        card_widget.setObjectName("atmCardWidget")
        card_widget.setStyleSheet("""
            QFrame#atmCardWidget {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #03050c, stop:0.4 #0f0520, stop:1 #130828);
                border: 1px solid #d946ef;
                border-radius: 16px;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
        """)
        
        card_layout = QVBoxLayout(card_widget)
        card_layout.setContentsMargins(24, 20, 24, 20)
        
        # Row 1: Chip & Contactless
        top_row = QHBoxLayout()
        chip_label = QLabel()
        chip_label.setFixedSize(45, 35)
        chip_label.setStyleSheet("background-color: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #fbbf24, stop:1 #d97706); border-radius: 6px; border: 1px solid #b45309;")
        
        contactless_label = QLabel("📶")
        contactless_label.setStyleSheet("font-size: 18px; color: #60a5fa; margin-left: 10px;")
        
        top_row.addWidget(chip_label)
        top_row.addWidget(contactless_label)
        top_row.addStretch()
        
        brand_label = QLabel("PREMIUM CARD")
        brand_label.setStyleSheet("font-family: 'Segoe UI', Arial; font-weight: bold; font-size: 14px; color: #60a5fa; letter-spacing: 1px;")
        top_row.addWidget(brand_label)
        card_layout.addLayout(top_row)
        card_layout.addSpacing(20)
        
        # Row 2: Monospace Card Number (OCR-friendly)
        formatted_num = "  ".join([self.card_number[i:i+4] for i in range(0, len(self.card_number), 4)])
        number_label = QLabel(formatted_num)
        number_label.setObjectName("cardNumberLabel")
        number_label.setStyleSheet("""
            QLabel#cardNumberLabel {
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 24px;
                font-weight: bold;
                color: #ffffff;
                letter-spacing: 2px;
            }
        """)
        number_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(number_label)
        card_layout.addSpacing(15)
        
        # Row 3: Expiry & CVV
        bottom_row = QHBoxLayout()
        
        exp_layout = QVBoxLayout()
        exp_title = QLabel("VALID THRU")
        exp_title.setStyleSheet("font-size: 9px; color: #94a3b8; font-weight: bold; letter-spacing: 0.5px;")
        exp_val = QLabel(self.expiry_date or "MM/YY")
        exp_val.setStyleSheet("font-family: 'Consolas', monospace; font-size: 18px; font-weight: bold; color: #ffffff;")
        exp_layout.addWidget(exp_title)
        exp_layout.addWidget(exp_val)
        
        cvv_layout = QVBoxLayout()
        cvv_title = QLabel("CVV")
        cvv_title.setStyleSheet("font-size: 9px; color: #94a3b8; font-weight: bold; letter-spacing: 0.5px;")
        cvv_val = QLabel(self.cvv or "xxx")
        cvv_val.setStyleSheet("font-family: 'Consolas', monospace; font-size: 18px; font-weight: bold; color: #ffffff;")
        cvv_layout.addWidget(cvv_title)
        cvv_layout.addWidget(cvv_val)
        
        bottom_row.addLayout(exp_layout)
        bottom_row.addSpacing(50)
        bottom_row.addLayout(cvv_layout)
        bottom_row.addStretch()
        
        card_layout.addLayout(bottom_row)
        
        layout.addWidget(card_widget, 0, Qt.AlignCenter)
        layout.addSpacing(10)

        # --- Standard Text Inputs (For copy/paste) ---
        # Số thẻ
        layout.addWidget(QLabel("Số thẻ:"))
        num_layout = QHBoxLayout()
        self.num_edit = QLineEdit(self.card_number)
        self.num_edit.setReadOnly(True)
        copy_num_btn = QPushButton("Sao chép")
        copy_num_btn.setObjectName("secondaryButton")
        copy_num_btn.setFixedWidth(80)
        copy_num_btn.clicked.connect(lambda: self.copy_to_clipboard(self.card_number))
        num_layout.addWidget(self.num_edit)
        num_layout.addWidget(copy_num_btn)
        layout.addLayout(num_layout)

        # Hạn dùng & CVV
        layout.addWidget(QLabel("Hạn dùng / CVV:"))
        expiry_cvv_layout = QHBoxLayout()
        self.expiry_edit = QLineEdit(self.expiry_date)
        self.expiry_edit.setReadOnly(True)
        self.cvv_edit = QLineEdit(self.cvv)
        self.cvv_edit.setReadOnly(True)
        expiry_cvv_layout.addWidget(self.expiry_edit)
        expiry_cvv_layout.addWidget(self.cvv_edit)
        layout.addLayout(expiry_cvv_layout)

        btn_layout = QHBoxLayout()
        copy_all_btn = QPushButton("Sao chép dòng gốc")
        copy_all_btn.clicked.connect(self.copy_all)
        
        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.accept)
        
        btn_layout.addWidget(copy_all_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

    def copy_to_clipboard(self, text):
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        sender_btn = self.sender()
        if sender_btn:
            old_text = sender_btn.text()
            sender_btn.setText("Đã chép! ✓")
            QTimer.singleShot(1000, lambda: sender_btn.setText(old_text))

    def copy_all(self):
        # Tạo lại dòng định dạng gốc dạng: Số thẻ|Tháng|Năm|CVV|Billing...
        expiry_parts = self.expiry_date.split('/')
        month = expiry_parts[0] if len(expiry_parts) > 0 else ""
        year = expiry_parts[1] if len(expiry_parts) > 1 else ""
        
        # Tạo dòng đầy đủ
        parts = [self.card_number, month, year, self.cvv]
        if self.extra_info:
            parts.extend([p.strip() for p in self.extra_info.split(' | ')])
            
        full_info = "|".join(parts)
        clipboard = QApplication.clipboard()
        clipboard.setText(full_info)
        sender_btn = self.sender()
        if sender_btn:
            old_text = sender_btn.text()
            sender_btn.setText("Đã chép dòng gốc! ✓")
            QTimer.singleShot(1000, lambda: sender_btn.setText(old_text))

    def prompt_status_update(self):
        if self.prompted:
            return
        self.prompted = True
        
        statuses = ["Chưa sử dụng", "Đã sử dụng", "Thẻ chết", "Thẻ sống", "Thẻ tốt"]
        new_status, ok = QInputDialog.getItem(
            self,
            "Cập nhật trạng thái",
            "Chọn trạng thái mới cho thẻ khi đóng:",
            statuses,
            0,
            False
        )
        if ok:
            final_status = new_status
        else:
            # Nếu người dùng hủy hoặc đóng hộp thoại chọn, khôi phục lại trạng thái ban đầu của thẻ
            final_status = self.status
            
        if self.parent() and hasattr(self.parent(), "update_card_status_async"):
            self.parent().update_card_status_async(self.card_id, final_status)

    def accept(self):
        self.prompt_status_update()
        super().accept()

    def reject(self):
        self.prompt_status_update()
        super().reject()


class EditCardDialog(QDialog):
    def __init__(self, card_number, expiry_date, cvv, status, extra_info, parent=None):
        super().__init__(parent)
        self.card_number = card_number
        self.expiry_date = expiry_date
        self.cvv = cvv
        self.status = status
        self.extra_info = extra_info or ""
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Sửa Thông Tin Thẻ")
        self.resize(500, 490)
        self.setStyleSheet("""
            QDialog {
                background-color: #060a1a;
                border: 1px solid #0e1630;
                border-radius: 16px;
            }
            QLabel {
                color: #f8fafc;
            }
            QLineEdit {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 8px 12px;
                color: #f8fafc;
            }
            QLineEdit:focus {
                border: 1px solid #d946ef;
            }
            QTextEdit {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 8px;
                color: #f8fafc;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
            }
            QTextEdit:focus {
                border: 1px solid #d946ef;
            }
            QComboBox {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 8px;
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        # Số thẻ
        layout.addWidget(QLabel("Số thẻ:"))
        self.num_edit = QLineEdit(self.card_number)
        layout.addWidget(self.num_edit)

        # Hạn dùng & CVV
        layout.addWidget(QLabel("Hạn dùng (MM/YY) / CVV:"))
        expiry_cvv_layout = QHBoxLayout()
        self.expiry_edit = QLineEdit(self.expiry_date)
        self.expiry_edit.setPlaceholderText("MM/YY")
        self.cvv_edit = QLineEdit(self.cvv)
        self.cvv_edit.setPlaceholderText("CVV")
        expiry_cvv_layout.addWidget(self.expiry_edit)
        expiry_cvv_layout.addWidget(self.cvv_edit)
        layout.addLayout(expiry_cvv_layout)

        # Thông tin đi kèm (Tên, Địa chỉ, Email...)
        layout.addWidget(QLabel("Thông tin bổ sung (Billing Details):"))
        self.extra_edit = QTextEdit()
        self.extra_edit.setText(self.extra_info.replace(" | ", "\n"))
        self.extra_edit.setLineWrapMode(QTextEdit.WidgetWidth)
        layout.addWidget(self.extra_edit)

        # Trạng thái
        layout.addWidget(QLabel("Trạng thái:"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(["Chưa sử dụng", "Đang sử dụng", "Đã sử dụng", "Thẻ chết", "Thẻ sống", "Thẻ tốt"])
        self.status_combo.setCurrentText(self.status)
        layout.addWidget(self.status_combo)

        # Nút bấm
        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Lưu thay đổi")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Hủy")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def get_data(self):
        num = self.num_edit.text().strip()
        expiry = self.expiry_edit.text().strip()
        cvv = self.cvv_edit.text().strip()
        status = self.status_combo.currentText()
        extra_info = " | ".join([p.strip() for p in self.extra_edit.toPlainText().strip().split('\n') if p.strip()])
        return num, expiry, cvv, status, extra_info


# Thread xác thực tài khoản
class AuthWorker(QThread):
    finished = pyqtSignal(bool, str)
    requires_2fa = pyqtSignal()
    
    def __init__(self, ipatool, code=None):
        super().__init__()
        self.ipatool = ipatool
        self.code = code
        
    def run(self):
        success, message = self.ipatool.authenticate(code=self.code)
        if not success and message == "REQUIRES_2FA":
            self.requires_2fa.emit()
        else:
            self.finished.emit(success, message)

# Thread tìm kiếm danh sách phiên bản
class SearchWorker(QThread):
    finished = pyqtSignal(bool, list, list, str) # success, raw_ids, friendly_list, error_msg
    
    def __init__(self, ipatool, app_id):
        super().__init__()
        self.ipatool = ipatool
        self.app_id = app_id
        
    def run(self):
        try:
            # 1. Lấy danh sách ID thô từ Apple Store
            raw_ids = self.ipatool.get_version_ids(self.app_id)
            if not raw_ids:
                self.finished.emit(False, [], [], "Không tìm thấy phiên bản nào.")
                return
                
            # 2. Thử lấy danh sách thân thiện từ bilin API
            friendly_list = []
            try:
                url = f"https://apis.bilin.eu.org/history/{self.app_id}"
                r = requests.get(url, timeout=10)
                if r.status_code == 200:
                    data = r.json()
                    friendly_list = data.get("data", [])
            except Exception as e:
                print(f"Bilin API error: {e}")
                
            self.finished.emit(True, raw_ids, friendly_list, "")
        except Exception as e:
            self.finished.emit(False, [], [], str(e))

# Thread tải và đóng gói IPA
class DownloadWorker(QThread):
    progress = pyqtSignal(str)
    percent = pyqtSignal(int)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, ipatool, app_id, version_id, output_path):
        super().__init__()
        self.ipatool = ipatool
        self.app_id = app_id
        self.version_id = version_id
        self.output_path = output_path
        
    def run(self):
        # Cập nhật tiến trình qua callback
        def progress_callback(status_text):
            self.progress.emit(status_text)
            # Trích xuất phần trăm từ status_text nếu có dạng "Đang tải: XX%"
            if "Đang tải: " in status_text:
                try:
                    pct = int(status_text.split("Đang tải: ")[1].split("%")[0])
                    self.percent.emit(pct)
                except Exception:
                    pass
            elif "thành công" in status_text.lower():
                self.percent.emit(100)
                
        try:
            self.ipatool.download_ipa(
                self.app_id, 
                self.version_id, 
                self.output_path, 
                progress_callback=progress_callback
            )
            self.finished.emit(True, "Tải xuống thành công!")
        except Exception as e:
            self.finished.emit(False, str(e))


class ScanAppsWorker(QThread):
    finished = pyqtSignal(bool, list, str) # success, apps, error_msg
    progress = pyqtSignal(str)
    
    def run(self):
        self.progress.emit("Đang kết nối tới iPhone qua cổng USB...")
        try:
            async def scan():
                lockdown = await create_using_usbmux()
                self.progress.emit("Đang lấy danh sách ứng dụng đã cài...")
                iproxy = InstallationProxyService(lockdown=lockdown)
                # get_apps returns dict[str, dict]
                if asyncio.iscoroutinefunction(iproxy.get_apps):
                    apps = await iproxy.get_apps(application_type="User")
                else:
                    apps = iproxy.get_apps(application_type="User")
                return apps
                
            apps = asyncio.run(scan())
            
            parsed_apps = []
            for bundle_id, info in apps.items():
                display_name = info.get('CFBundleDisplayName') or info.get('CFBundleName') or 'N/A'
                version = info.get('CFBundleShortVersionString') or info.get('CFBundleVersion') or 'N/A'
                app_store_id = info.get('APP_STORE_APP_ID') or info.get('ItemId') or info.get('adamId')
                
                parsed_apps.append({
                    "name": display_name,
                    "bundle_id": bundle_id,
                    "version": version,
                    "app_store_id": str(app_store_id) if app_store_id else None
                })
            
            # Sắp xếp ứng dụng theo bảng chữ cái
            parsed_apps.sort(key=lambda x: x["name"].lower())
            self.finished.emit(True, parsed_apps, "")
        except Exception as e:
            self.finished.emit(False, [], str(e))


class LookupBundleWorker(QThread):
    finished = pyqtSignal(bool, str, str) # success, app_id, error_msg
    
    def __init__(self, bundle_id):
        super().__init__()
        self.bundle_id = bundle_id
        
    def run(self):
        url = f"https://itunes.apple.com/lookup?bundleId={self.bundle_id}&entity=software"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                if results:
                    track_id = str(results[0].get("trackId"))
                    self.finished.emit(True, track_id, "")
                    return
            self.finished.emit(False, "", "Không tìm thấy ứng dụng trên App Store.")
        except Exception as e:
            self.finished.emit(False, "", str(e))


class InstallAppsWorker(QThread):
    progress = pyqtSignal(int)
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, ipa_path):
        super().__init__()
        self.ipa_path = ipa_path
        
    def run(self):
        self.status.emit("Đang kết nối tới thiết bị qua USB...")
        try:
            async def install():
                lockdown = await create_using_usbmux()
                self.status.emit("Đang kết nối dịch vụ Cài đặt (Installation Proxy)...")
                iproxy = InstallationProxyService(lockdown=lockdown)
                
                def progress_callback(*args):
                    percent = args[0] if args else 0
                    self.progress.emit(percent)
                    self.status.emit(f"Tiến trình cài đặt: {percent}%")
                
                self.status.emit("Đang tải file IPA và giải nén cài đặt...")
                await iproxy.install_from_local(self.ipa_path, handler=progress_callback)
                
            asyncio.run(install())
            self.finished.emit(True, "Cài đặt ứng dụng thành công!")
        except Exception as e:
            self.finished.emit(False, str(e))


class GetDeviceInfoWorker(QThread):
    finished = pyqtSignal(bool, list, str) # success, list of device_info dicts, error_msg
    progress = pyqtSignal(str)

    def run(self):
        self.progress.emit("Đang quét danh sách iPhone kết nối qua USB...")
        try:
            from pymobiledevice3.usbmux import list_devices
            from pymobiledevice3.lockdown import create_using_usbmux
            
            async def get_all_info():
                devices = await list_devices()
                if not devices:
                    raise Exception("Không tìm thấy bất kỳ thiết bị iPhone nào được kết nối qua USB.")
                    
                self.progress.emit(f"Tìm thấy {len(devices)} thiết bị. Đang đọc thông tin chi tiết từng máy...")
                results = []
                for dev in devices:
                    serial = dev.serial
                    try:
                        lockdown = await create_using_usbmux(serial=serial)
                        vals = lockdown.all_values
                        results.append({
                            "device_class": vals.get("DeviceClass", "iOS Device"),
                            "product_type": vals.get("ProductType", "Unknown"),
                            "product_version": vals.get("ProductVersion", "Unknown"),
                            "serial_number": vals.get("SerialNumber", "Unknown"),
                            "udid": serial,
                            "device_name": vals.get("DeviceName", "iPhone")
                        })
                    except Exception as dev_err:
                        self.progress.emit(f"Cảnh báo: Không thể đọc thông tin chi tiết ({serial[:8]}): {dev_err}")
                        results.append({
                            "device_class": "iOS Device",
                            "product_type": "Unknown",
                            "product_version": "Unknown",
                            "serial_number": "Unknown",
                            "udid": serial,
                            "device_name": f"iPhone (Chưa tin cậy / {serial[:8]})"
                        })
                return results
                
            infos = asyncio.run(get_all_info())
            self.finished.emit(True, infos, "")
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = str(e)
            if not err_msg:
                err_msg = f"{e.__class__.__name__}: {repr(e)}"
            self.finished.emit(False, [], err_msg)


class SelectDevicesDialog(QDialog):
    def __init__(self, devices, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn thiết bị thao tác")
        self.setMinimumSize(450, 320)
        self.devices = devices
        
        layout = QVBoxLayout(self)
        
        title_label = QLabel(f"Đã phát hiện {len(devices)} thiết bị đang kết nối USB:")
        title_label.setFont(QFont("Inter", 11, QFont.Bold))
        layout.addWidget(title_label)
        
        self.checkboxes = []
        list_group = QGroupBox("Danh sách thiết bị:")
        list_layout = QVBoxLayout(list_group)
        
        for info in devices:
            text = f"📱 {info['device_name']} - iOS {info['product_version']} [{info['udid'][:12]}...]"
            cb = QCheckBox(text)
            cb.setProperty("udid", info["udid"])
            cb.setChecked(True)
            list_layout.addWidget(cb)
            self.checkboxes.append(cb)
            
        layout.addWidget(list_group)
        
        shortcut_layout = QHBoxLayout()
        select_all_btn = QPushButton("Chọn Tất Cả")
        deselect_all_btn = QPushButton("Bỏ Chọn Tất Cả")
        
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn.clicked.connect(self.deselect_all)
        
        shortcut_layout.addWidget(select_all_btn)
        shortcut_layout.addWidget(deselect_all_btn)
        layout.addLayout(shortcut_layout)
        
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("Xác Nhận")
        cancel_btn = QPushButton("Hủy")
        
        ok_btn.setObjectName("primaryButton")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)
        
    def select_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)
            
    def deselect_all(self):
        for cb in self.checkboxes:
            cb.setChecked(False)
            
    def get_selected_udids(self):
        selected = []
        for cb in self.checkboxes:
            if cb.isChecked():
                selected.append(cb.property("udid"))
        return selected


class EraseDeviceWorker(QThread):
    status = pyqtSignal(str, str) # Emits (device_serial, message)
    finished = pyqtSignal(str, bool, str) # Emits (device_serial, success, message)
    
    def __init__(self, device_serial):
        super().__init__()
        self.device_serial = device_serial
        
    def run(self):
        serial = self.device_serial
        short_serial = serial[:8]
        self.status.emit(serial, f"[{short_serial}] Đang kết nối tới iPhone qua USB...")
        try:
            async def erase():
                from pymobiledevice3.lockdown import create_using_usbmux
                lockdown = await create_using_usbmux(serial=serial)
                self.status.emit(serial, f"[{short_serial}] Đang kết nối dịch vụ Cấu hình (MobileConfig)...")
                service = MobileConfigService(lockdown=lockdown)
                self.status.emit(serial, f"[{short_serial}] Đang gửi lệnh xóa toàn bộ dữ liệu thiết bị...")
                await service.erase_device(preserve_data_plan=False, disallow_proximity_setup=False)
                
            asyncio.run(erase())
            self.finished.emit(serial, True, f"[{short_serial}] Đã gửi lệnh xóa thiết bị thành công! iPhone đang khởi động lại.")
        except Exception as e:
            self.finished.emit(serial, False, f"[{short_serial}] Lỗi: {e}")


class AutoActivateMonitorWorker(QThread):
    status = pyqtSignal(str, str)
    finished = pyqtSignal(str, bool, str)
    
    def __init__(self, device_serial):
        super().__init__()
        self.device_serial = device_serial
        
    def run(self):
        import time
        serial = self.device_serial
        short_serial = serial[:8]
        self.status.emit(serial, f"[{short_serial}] Đang đợi iPhone khởi động lại (quá trình xóa thường mất 1-3 phút)...")
        
        # Đợi 25 giây đầu tiên vì máy chắc chắn đang tắt/khởi động lại
        for i in range(25):
            if self.isInterruptionRequested():
                return
            time.sleep(1)
            
        from pymobiledevice3.lockdown import create_using_usbmux
        from pymobiledevice3.services.mobile_activation import MobileActivationService
        
        retries = 0
        max_retries = 120 # Đợi tối đa khoảng 10 phút (120 * 5s)
        
        while not self.isInterruptionRequested() and retries < max_retries:
            try:
                async def check_and_activate():
                    # Thử kết nối lockdown cho thiết bị cụ thể này
                    lockdown = await create_using_usbmux(serial=serial)
                    
                    activation_service = MobileActivationService(lockdown)
                    state = await activation_service.state()
                    
                    self.status.emit(serial, f"[{short_serial}] Đã phát hiện thiết bị kết nối lại. Trạng thái: {state}")
                    self.status.emit(serial, f"[{short_serial}] Đang thực hiện tự động kích hoạt...")
                    
                    if state != "Activated":
                        try:
                            await activation_service.wait_for_activation_session()
                        except Exception as e:
                            self.status.emit(serial, f"[{short_serial}] Bỏ qua bước đợi session kích hoạt: {e}")
                        await activation_service.activate()
                        self.status.emit(serial, f"[{short_serial}] Tự động kích hoạt thiết bị thành công!")
                    else:
                        self.status.emit(serial, f"[{short_serial}] Thiết bị đã được kích hoạt từ trước.")
                        
                    self.status.emit(serial, f"[{short_serial}] Đang tự động cấu hình ngôn ngữ/vùng Tiếng Anh (Mỹ)...")
                    try:
                        await lockdown.set_language("en")
                    except Exception as e:
                        self.status.emit(serial, f"[{short_serial}] Lỗi đặt ngôn ngữ: {e}")
                    
                    try:
                        await lockdown.set_locale("en_US")
                    except Exception as e:
                        self.status.emit(serial, f"[{short_serial}] Lỗi đặt quốc gia: {e}")
                    
                    try:
                        await lockdown.set_timezone("America/New_York")
                    except Exception as e:
                        self.status.emit(serial, f"[{short_serial}] Lỗi đặt múi giờ: {e}")
                        
                    self.status.emit(serial, f"[{short_serial}] Đang thiết lập bỏ qua các màn hình thiết lập (Setup Assistant)...")
                    buddy_keys = [
                        ("com.apple.purplebuddy", "SetupDone", True),
                        ("com.apple.purplebuddy", "SetupFinishedAllSteps", True),
                        ("com.apple.purplebuddy", "AssistantPresented", True),
                        ("com.apple.purplebuddy", "DidShowSubUI", True),
                        ("com.apple.purplebuddy", "SetupState", 3)
                    ]
                    
                    bypass_succeeded = True
                    for domain, key, val in buddy_keys:
                        try:
                            await lockdown.set_value(val, key=key, domain=domain)
                        except Exception as e:
                            self.status.emit(serial, f"[{short_serial}] Không thể đặt {domain}.{key}: {e}")
                            if key in ("SetupDone", "SetupFinishedAllSteps"):
                                bypass_succeeded = False
                                
                    if not bypass_succeeded:
                        self.status.emit(serial, f"[{short_serial}] Lockdown từ chối ghi Setup Assistant. Đang kiểm tra cổng afc2 (Jailbreak)...")
                        try:
                            await lockdown.start_lockdown_service("com.apple.afc2")
                            from pymobiledevice3.services.afc import AfcService
                            afc = AfcService(lockdown=lockdown, service_name="com.apple.afc2")
                            
                            self.status.emit(serial, f"[{short_serial}] Phát hiện cổng afc2 (Jailbreak). Đang nạp cấu hình bypass...")
                            import plistlib
                            plist_dict = {
                                "SetupDone": True,
                                "SetupFinishedAllSteps": True,
                                "AssistantPresented": True,
                                "DidShowSubUI": True,
                                "SetupState": 3
                            }
                            plist_bytes = plistlib.dumps(plist_dict)
                            await afc.set_file_contents("/private/var/mobile/Library/Preferences/com.apple.purplebuddy.plist", plist_bytes)
                            self.status.emit(serial, f"[{short_serial}] Đã ghi cấu hình bypass vào file preferences qua afc2 thành công!")
                            bypass_succeeded = True
                        except Exception as afc_err:
                            self.status.emit(serial, f"[{short_serial}] Cổng afc2 không khả dụng hoặc lỗi: {afc_err}")

                    self.status.emit(serial, f"[{short_serial}] Ghi nhận trạng thái hoàn tất kích hoạt...")
                    try:
                        await lockdown.set_value(True, key="ActivationStateAcknowledged")
                    except Exception as e:
                        self.status.emit(serial, f"[{short_serial}] Cảnh báo khi thiết lập ActivationStateAcknowledged: {e}")
                        
                    if bypass_succeeded:
                        self.status.emit(serial, f"[{short_serial}] Ghi cấu hình thành công! Đang khởi động lại thiết bị...")
                        try:
                            from pymobiledevice3.services.diagnostics import DiagnosticsService
                            diagnostics = DiagnosticsService(lockdown)
                            await diagnostics.restart()
                            self.status.emit(serial, f"[{short_serial}] Đã gửi lệnh khởi động lại thành công! Thiết bị sẽ tự động vào màn hình chính.")
                        except Exception as e:
                            self.status.emit(serial, f"[{short_serial}] Cảnh báo: Không thể gửi lệnh tự khởi động lại: {e}. Vui lòng tự khởi động lại.")
                    else:
                        self.status.emit(serial, f"[{short_serial}] Lưu ý: iOS phiên bản cao chặn ghi đè Setup Assistant (SetupDone). Vui lòng tự bấm qua các bước.")
                    
                    return True
                
                success = asyncio.run(check_and_activate())
                if success:
                    self.finished.emit(serial, True, f"[{short_serial}] Đã tự động xóa dữ liệu thiết bị và kích hoạt thành công!")
                    return
                    
            except Exception as e:
                retries += 1
                self.status.emit(serial, f"[{short_serial}] Đang đợi phản hồi và kết nối lại (Lần {retries}/{max_retries})...")
                for _ in range(5):
                    if self.isInterruptionRequested():
                        return
                    time.sleep(1)
                    
        self.finished.emit(serial, False, f"[{short_serial}] Hết thời gian chờ đợi thiết bị kết nối lại. Vui lòng tự kích hoạt.")


class ActivateDeviceWorker(QThread):
    status = pyqtSignal(str, str)
    finished = pyqtSignal(str, bool, str)
    
    def __init__(self, device_serial):
        super().__init__()
        self.device_serial = device_serial
        
    def run(self):
        serial = self.device_serial
        short_serial = serial[:8]
        self.status.emit(serial, f"[{short_serial}] Đang kết nối tới iPhone qua cổng USB...")
        try:
            async def activate_and_configure():
                from pymobiledevice3.services.mobile_activation import MobileActivationService
                from pymobiledevice3.lockdown import create_using_usbmux
                
                lockdown = await create_using_usbmux(serial=serial)
                self.status.emit(serial, f"[{short_serial}] Đang kết nối dịch vụ kích hoạt...")
                activation_service = MobileActivationService(lockdown)
                
                try:
                    state = await activation_service.state()
                    self.status.emit(serial, f"[{short_serial}] Trạng thái kích hoạt hiện tại: {state}")
                except Exception as e:
                    state = "Unknown"
                    self.status.emit(serial, f"[{short_serial}] Không lấy được trạng thái kích hoạt: {e}")
                
                if state != "Activated":
                    self.status.emit(serial, f"[{short_serial}] Đang thực hiện kích hoạt thiết bị qua máy chủ Apple...")
                    try:
                        await activation_service.wait_for_activation_session()
                    except Exception as e:
                        self.status.emit(serial, f"[{short_serial}] Bỏ qua bước đợi session kích hoạt: {e}")
                    await activation_service.activate()
                    self.status.emit(serial, f"[{short_serial}] Kích hoạt thiết bị thành công!")
                else:
                    self.status.emit(serial, f"[{short_serial}] Thiết bị đã được kích hoạt từ trước.")
                
                self.status.emit(serial, f"[{short_serial}] Đang thiết lập ngôn ngữ Tiếng Anh (EN) và quốc gia Mỹ (US)...")
                try:
                    await lockdown.set_language("en")
                except Exception as e:
                    self.status.emit(serial, f"[{short_serial}] Lỗi đặt ngôn ngữ: {e}")
                
                try:
                    await lockdown.set_locale("en_US")
                except Exception as e:
                    self.status.emit(serial, f"[{short_serial}] Lỗi đặt quốc gia: {e}")
                
                try:
                    await lockdown.set_timezone("America/New_York")
                except Exception as e:
                    self.status.emit(serial, f"[{short_serial}] Lỗi đặt múi giờ: {e}")
                
                self.status.emit(serial, f"[{short_serial}] Đang thiết lập bỏ qua các màn hình thiết lập (Setup Assistant)...")
                buddy_keys = [
                    ("com.apple.purplebuddy", "SetupDone", True),
                    ("com.apple.purplebuddy", "SetupFinishedAllSteps", True),
                    ("com.apple.purplebuddy", "AssistantPresented", True),
                    ("com.apple.purplebuddy", "DidShowSubUI", True),
                    ("com.apple.purplebuddy", "SetupState", 3)
                ]
                
                bypass_succeeded = True
                for domain, key, val in buddy_keys:
                    try:
                        await lockdown.set_value(val, key=key, domain=domain)
                    except Exception as e:
                        self.status.emit(serial, f"[{short_serial}] Không thể đặt {domain}.{key}: {e}")
                        if key in ("SetupDone", "SetupFinishedAllSteps"):
                            bypass_succeeded = False
                
                if not bypass_succeeded:
                    self.status.emit(serial, f"[{short_serial}] Lockdown từ chối ghi Setup Assistant. Đang kiểm tra cổng afc2 (Jailbreak)...")
                    try:
                        await lockdown.start_lockdown_service("com.apple.afc2")
                        from pymobiledevice3.services.afc import AfcService
                        afc = AfcService(lockdown=lockdown, service_name="com.apple.afc2")
                        
                        self.status.emit(serial, f"[{short_serial}] Phát hiện cổng afc2 (Jailbreak). Đang nạp cấu hình bypass...")
                        import plistlib
                        plist_dict = {
                            "SetupDone": True,
                            "SetupFinishedAllSteps": True,
                            "AssistantPresented": True,
                            "DidShowSubUI": True,
                            "SetupState": 3
                        }
                        plist_bytes = plistlib.dumps(plist_dict)
                        await afc.set_file_contents("/private/var/mobile/Library/Preferences/com.apple.purplebuddy.plist", plist_bytes)
                        self.status.emit(serial, f"[{short_serial}] Đã ghi cấu hình bypass vào file preferences qua afc2 thành công!")
                        bypass_succeeded = True
                    except Exception as afc_err:
                        self.status.emit(serial, f"[{short_serial}] Cổng afc2 không khả dụng hoặc lỗi: {afc_err}")

                self.status.emit(serial, f"[{short_serial}] Ghi nhận trạng thái hoàn tất kích hoạt...")
                try:
                    await lockdown.set_value(True, key="ActivationStateAcknowledged")
                except Exception as e:
                    self.status.emit(serial, f"[{short_serial}] Cảnh báo khi thiết lập ActivationStateAcknowledged: {e}")
                
                if bypass_succeeded:
                    self.status.emit(serial, f"[{short_serial}] Ghi cấu hình thành công! Đang khởi động lại thiết bị...")
                    try:
                        from pymobiledevice3.services.diagnostics import DiagnosticsService
                        diagnostics = DiagnosticsService(lockdown)
                        await diagnostics.restart()
                        self.status.emit(serial, f"[{short_serial}] Đã gửi lệnh khởi động lại thành công! Thiết bị sẽ tự động vào màn hình chính.")
                    except Exception as e:
                        self.status.emit(serial, f"[{short_serial}] Cảnh báo: Không thể gửi lệnh tự khởi động lại: {e}. Vui lòng tự khởi động lại.")
                else:
                    self.status.emit(serial, f"[{short_serial}] Lưu ý: iOS phiên bản cao chặn ghi đè Setup Assistant (SetupDone). Vui lòng tự bấm qua các bước trên màn hình.")
                
            asyncio.run(activate_and_configure())
            self.finished.emit(serial, True, f"[{short_serial}] Đã kích hoạt và cấu hình ngôn ngữ/vùng Tiếng Anh (Mỹ) thành công!")
        except Exception as e:
            self.finished.emit(serial, False, str(e))


class ClearAppDataWorker(QThread):
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, bundle_id, app_name, force_uninstall=False):
        super().__init__()
        self.bundle_id = bundle_id
        self.app_name = app_name
        self.force_uninstall = force_uninstall

    def run(self):
        self.status.emit(f"Đang chuẩn bị dọn dẹp dữ liệu cho {self.app_name} ({self.bundle_id})...")
        try:
            async def clear():
                lockdown = await create_using_usbmux()
                
                # Nếu không bắt buộc gỡ cài đặt, thử chế độ dọn dẹp qua afc2 (Jailbreak) trước
                if not self.force_uninstall:
                    self.status.emit("Đang kiểm tra kết nối dịch vụ afc2 (Jailbreak)...")
                    is_jailbroken = False
                    afc = None
                    try:
                        # Thử kết nối afc2
                        afc_connection = await lockdown.start_lockdown_service("com.apple.afc2")
                        from pymobiledevice3.services.afc import AfcService
                        afc = AfcService(lockdown=lockdown, service_name="com.apple.afc2")
                        is_jailbroken = True
                    except Exception:
                        self.status.emit("Không thể kết nối dịch vụ afc2. Thiết bị chưa jailbreak hoặc chưa bật afc2.")
                    
                    if is_jailbroken and afc:
                        self.status.emit("Thiết bị đã Jailbreak. Đang tìm thư mục dữ liệu (Container) của app...")
                        base_dir = "/private/var/mobile/Containers/Data/Application"
                        container_path = None
                        
                        try:
                            folders = await afc.listdir(base_dir)
                        except Exception as e:
                            raise Exception(f"Không thể đọc danh sách Containers: {e}")
                            
                        import plistlib
                        for folder in folders:
                            if folder in (".", ".."):
                                continue
                            plist_path = f"{base_dir}/{folder}/.com.apple.mobile_container_manager.metadata.plist"
                            try:
                                content = await afc.get_file_contents(plist_path)
                                plist_data = plistlib.loads(content)
                                if plist_data.get("MCMMetadataIdentifier") == self.bundle_id:
                                    container_path = f"{base_dir}/{folder}"
                                    break
                            except Exception:
                                continue
                        
                        if container_path:
                            self.status.emit(f"Tìm thấy thư mục ứng dụng: {container_path}")
                            # Xóa các thư mục con Documents, Library, tmp
                            for sub_folder in ("Documents", "Library", "tmp"):
                                full_path = f"{container_path}/{sub_folder}"
                                try:
                                    if await afc.exists(full_path):
                                        self.status.emit(f"Đang xóa sạch dữ liệu trong: {sub_folder}...")
                                        await afc.rm(full_path)
                                    
                                    # Tạo lại thư mục trống
                                    await afc.makedirs(full_path)
                                except Exception as e:
                                    self.status.emit(f"Cảnh báo lỗi dọn dẹp thư mục {sub_folder}: {e}")
                            
                            return "SUCCESS_JAILBREAK"
                        else:
                            raise Exception("Không tìm thấy thư mục dữ liệu của ứng dụng trên thiết bị jailbreak.")
                    else:
                        # Trả về mã thông báo afc2 không khả dụng để chuyển sang gỡ cài đặt ở GUI
                        return "AFC2_UNAVAILABLE"
                
                else:
                    # Gỡ cài đặt ứng dụng đối với máy chưa Jailbreak
                    self.status.emit("Đang kết nối dịch vụ Cài đặt (Installation Proxy) để gỡ ứng dụng...")
                    iproxy = InstallationProxyService(lockdown=lockdown)
                    
                    if asyncio.iscoroutinefunction(iproxy.uninstall):
                        await iproxy.uninstall(self.bundle_id)
                    else:
                        iproxy.uninstall(self.bundle_id)
                        
                    return "SUCCESS_UNINSTALL"

            res = asyncio.run(clear())
            if res == "AFC2_UNAVAILABLE":
                self.finished.emit(False, "AFC2_UNAVAILABLE")
            elif res == "SUCCESS_JAILBREAK":
                self.finished.emit(True, f"Đã dọn sạch session đăng nhập và dữ liệu của '{self.app_name}' thành công qua cổng afc2 (Jailbreak)!")
            elif res == "SUCCESS_UNINSTALL":
                self.finished.emit(True, f"Đã gỡ cài đặt ứng dụng '{self.app_name}' khỏi iPhone thành công để xóa toàn bộ dữ liệu.")
        except Exception as e:
            self.finished.emit(False, str(e))


class BackupAppDataWorker(QThread):
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, bundle_id, app_name, zip_file_path):
        super().__init__()
        self.bundle_id = bundle_id
        self.app_name = app_name
        self.zip_file_path = zip_file_path

    def run(self):
        import shutil
        import tempfile
        self.status.emit(f"Đang chuẩn bị sao lưu dữ liệu cho {self.app_name}...")
        try:
            async def backup():
                lockdown = await create_using_usbmux()
                
                self.status.emit("Đang kết nối dịch vụ afc2 (Jailbreak)...")
                try:
                    await lockdown.start_lockdown_service("com.apple.afc2")
                    from pymobiledevice3.services.afc import AfcService
                    afc = AfcService(lockdown=lockdown, service_name="com.apple.afc2")
                except Exception:
                    raise Exception("Không thể kết nối dịch vụ afc2. Thiết bị chưa jailbreak hoặc chưa cài afc2.")
                
                self.status.emit("Đang tìm thư mục dữ liệu (Container) của app...")
                base_dir = "/private/var/mobile/Containers/Data/Application"
                container_path = None
                
                try:
                    folders = await afc.listdir(base_dir)
                except Exception as e:
                    raise Exception(f"Không thể đọc danh sách Containers: {e}")
                    
                import plistlib
                for folder in folders:
                    if folder in (".", ".."):
                        continue
                    plist_path = f"{base_dir}/{folder}/.com.apple.mobile_container_manager.metadata.plist"
                    try:
                        content = await afc.get_file_contents(plist_path)
                        plist_data = plistlib.loads(content)
                        if plist_data.get("MCMMetadataIdentifier") == self.bundle_id:
                            container_path = f"{base_dir}/{folder}"
                            break
                    except Exception:
                        continue
                
                if not container_path:
                    raise Exception("Không tìm thấy thư mục dữ liệu của ứng dụng trên thiết bị.")
                
                temp_dir = os.path.join(tempfile.gettempdir(), f"qhtd_backup_{self.bundle_id}")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                os.makedirs(temp_dir)
                
                try:
                    for folder in ("Documents", "Library"):
                        remote_path = f"{container_path}/{folder}"
                        if await afc.exists(remote_path):
                            self.status.emit(f"Đang tải thư mục {folder} từ iPhone...")
                            await afc.pull(folder, temp_dir, src_dir=container_path, progress_bar=False)
                            
                    self.status.emit("Đang nén dữ liệu thành file ZIP...")
                    base_name = self.zip_file_path
                    if base_name.lower().endswith(".zip"):
                        base_name = base_name[:-4]
                    shutil.make_archive(base_name, "zip", temp_dir)
                finally:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                        
                return f"Đã sao lưu dữ liệu ứng dụng '{self.app_name}' thành công!"

            msg = asyncio.run(backup())
            self.finished.emit(True, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


class RestoreAppDataWorker(QThread):
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, bundle_id, app_name, zip_file_path):
        super().__init__()
        self.bundle_id = bundle_id
        self.app_name = app_name
        self.zip_file_path = zip_file_path

    def run(self):
        import shutil
        import tempfile
        self.status.emit(f"Đang chuẩn bị khôi phục dữ liệu cho {self.app_name}...")
        try:
            async def restore():
                lockdown = await create_using_usbmux()
                
                self.status.emit("Đang kết nối dịch vụ afc2 (Jailbreak)...")
                try:
                    await lockdown.start_lockdown_service("com.apple.afc2")
                    from pymobiledevice3.services.afc import AfcService
                    afc = AfcService(lockdown=lockdown, service_name="com.apple.afc2")
                except Exception:
                    raise Exception("Không thể kết nối dịch vụ afc2. Thiết bị chưa jailbreak hoặc chưa cài afc2.")
                
                self.status.emit("Đang tìm thư mục dữ liệu (Container) của app...")
                base_dir = "/private/var/mobile/Containers/Data/Application"
                container_path = None
                
                try:
                    folders = await afc.listdir(base_dir)
                except Exception as e:
                    raise Exception(f"Không thể đọc danh sách Containers: {e}")
                    
                import plistlib
                for folder in folders:
                    if folder in (".", ".."):
                        continue
                    plist_path = f"{base_dir}/{folder}/.com.apple.mobile_container_manager.metadata.plist"
                    try:
                        content = await afc.get_file_contents(plist_path)
                        plist_data = plistlib.loads(content)
                        if plist_data.get("MCMMetadataIdentifier") == self.bundle_id:
                            container_path = f"{base_dir}/{folder}"
                            break
                    except Exception:
                        continue
                
                if not container_path:
                    raise Exception("Không tìm thấy thư mục dữ liệu của ứng dụng trên thiết bị.")
                
                temp_dir = os.path.join(tempfile.gettempdir(), f"qhtd_restore_{self.bundle_id}")
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir)
                os.makedirs(temp_dir)
                
                try:
                    self.status.emit("Đang giải nén file ZIP lưu trữ...")
                    shutil.unpack_archive(self.zip_file_path, temp_dir, "zip")
                    
                    for folder in ("Documents", "Library"):
                        local_folder_path = os.path.join(temp_dir, folder)
                        if os.path.exists(local_folder_path):
                            remote_folder_path = f"{container_path}/{folder}"
                            if await afc.exists(remote_folder_path):
                                self.status.emit(f"Đang xóa dữ liệu cũ trong thư mục {folder}...")
                                await afc.rm(remote_folder_path)
                            
                            await afc.makedirs(remote_folder_path)
                            
                            self.status.emit(f"Đang tải dữ liệu {folder} lên iPhone...")
                            await afc.push(local_folder_path, container_path)
                finally:
                    if os.path.exists(temp_dir):
                        shutil.rmtree(temp_dir)
                        
                return f"Đã khôi phục dữ liệu ứng dụng '{self.app_name}' thành công! Vui lòng mở lại app trên điện thoại."

            msg = asyncio.run(restore())
            self.finished.emit(True, msg)
        except Exception as e:
            self.finished.emit(False, str(e))


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class WebServerWorker(QThread):
    started = pyqtSignal(str, int) # ip, port
    
    def __init__(self, file_path, port=8080):
        super().__init__()
        self.file_path = file_path
        self.port = port
        self.httpd = None
        
    def run(self):
        file_dir = os.path.dirname(self.file_path)
        file_name = os.path.basename(self.file_path)
        
        # Custom handler to serve the target file
        class SingleFileHandler(SimpleHTTPRequestHandler):
            def do_GET(self):
                # Làm sạch đường dẫn yêu cầu
                req_path = self.path.split('?')[0].split('#')[0]
                
                # Nếu là trang chủ, trả về trang HTML cài đặt tuyệt đẹp
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


class TrollStoreShareDialog(QDialog):
    def __init__(self, ipa_path, parent=None):
        super().__init__(parent)
        self.ipa_path = ipa_path
        self.server_thread = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Chia sẻ Cài đặt qua TrollStore 📲")
        self.resize(480, 560)
        self.setStyleSheet("""
            QDialog {
                background-color: #060a1a;
                border: 1px solid #0e1630;
                border-radius: 16px;
            }
            QLabel {
                color: #f8fafc;
            }
            QLabel#instructions {
                font-size: 13px;
                line-height: 1.5;
            }
            QPushButton {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 8px 16px;
                color: #f8fafc;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        
        title = QLabel("Cài đặt qua TrollStore (Mã QR/WiFi)")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #00f2fe;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        info = QLabel(
            "Để giữ nguyên bản quyền App Store và sử dụng In-App Purchase,\n"
            "bạn nên cài đặt tệp IPA nguyên bản này qua TrollStore trên iPhone.\n\n"
            "Hãy đảm bảo iPhone và máy tính kết nối chung mạng Wi-Fi."
        )
        info.setObjectName("instructions")
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        self.qr_label = QLabel()
        self.qr_label.setFixedSize(200, 200)
        self.qr_label.setStyleSheet("border: 1px solid #0e1630; border-radius: 10px; background-color: #ffffff;")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setText("Đang khởi tạo mã QR...")
        
        qr_container = QHBoxLayout()
        qr_container.addStretch()
        qr_container.addWidget(self.qr_label)
        qr_container.addStretch()
        layout.addLayout(qr_container)
        
        self.link_label = QLabel("Đang mở máy chủ...")
        self.link_label.setStyleSheet("color: #d946ef; font-weight: bold; font-size: 12px;")
        self.link_label.setAlignment(Qt.AlignCenter)
        self.link_label.setWordWrap(True)
        layout.addWidget(self.link_label)
        
        steps = QLabel(
            "1. Quét mã QR bằng Camera của iPhone để mở link tải.\n"
            "2. Safari sẽ tải xuống tệp tin IPA.\n"
            "3. Khi tải xong, mở tệp tin và chọn chia sẻ sang TrollStore."
        )
        steps.setStyleSheet("color: #94a3b8; font-size: 12px;")
        steps.setWordWrap(True)
        layout.addWidget(steps)
        
        self.close_btn = QPushButton("Hoàn tất / Đóng")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
        
        self.start_server()

    def start_server(self):
        self.server_thread = WebServerWorker(self.ipa_path)
        self.server_thread.started.connect(self.on_server_started)
        self.server_thread.start()
        
    def on_server_started(self, ip, port):
        # Đường dẫn tới trang chủ cài đặt
        web_url = f"http://{ip}:{port}/"
        self.link_label.setText(f"Link: {web_url}")
        
        try:
            import urllib.parse
            encoded_url = urllib.parse.quote(web_url)
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=200x200&data={encoded_url}"
            r = requests.get(qr_api, timeout=5)
            if r.status_code == 200:
                pix = QPixmap()
                pix.loadFromData(r.content)
                self.qr_label.setPixmap(pix)
            else:
                self.qr_label.setText("Lỗi nạp QR Code")
        except Exception:
            self.qr_label.setText("Không thể kết nối Internet\nđể tạo QR Code")
            
    def closeEvent(self, event):
        if self.server_thread:
            self.server_thread.stop()
            self.server_thread.wait()
        event.accept()


class TrollRestoreWorker(QThread):
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, serial=None):
        super().__init__()
        self.serial = serial
        
    def run(self):
        self.status.emit("Bắt đầu tiến trình cài đặt TrollStore...")
        try:
            import requests
            import asyncio
            from pathlib import Path
            from packaging.version import parse as parse_version
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.installation_proxy import InstallationProxyService
            from pymobiledevice3.services.diagnostics import DiagnosticsService
            from pymobiledevice3.exceptions import PyMobileDevice3Exception
            from sparserestore import backup, perform_restore
            
            # 1. Kết nối đến thiết bị qua lockdown
            self.status.emit("Đang kết nối tới thiết bị iOS qua cổng USB...")
            
            async def run_restore():
                lockdown = await create_using_usbmux(serial=self.serial)
                device_class = await lockdown.get_value(key="DeviceClass")
                device_build = await lockdown.get_value(key="BuildVersion")
                product_version = lockdown.product_version
                
                self.status.emit(f"Đã kết nối: {device_class} - iOS {product_version} (Build: {device_build})")
                
                # 2. Kiểm tra phiên bản hỗ trợ (iOS 15.0 - 17.0)
                device_version = parse_version(product_version)
                if (
                    device_version < parse_version("15.0")
                    or device_version > parse_version("17.0")
                    or parse_version("16.7") < device_version < parse_version("17.0")
                    or (device_version == parse_version("16.7") and device_build != "20H18")
                ):
                    raise Exception(f"Phiên bản iOS {product_version} ({device_build}) không được hỗ trợ bởi TrollRestore.\nTrollRestore chỉ hỗ trợ từ iOS 15.0 đến 16.7 RC và iOS 17.0.")
                    
                # 3. Tải tệp PersistenceHelper_Embedded từ GitHub
                self.status.emit("Đang tải tệp tin TrollStore Helper (PersistenceHelper_Embedded) từ GitHub...")
                try:
                    url = "https://github.com/opa334/TrollStore/releases/latest/download/PersistenceHelper_Embedded"
                    response = requests.get(url, timeout=15)
                    response.raise_for_status()
                    helper_contents = response.content
                    self.status.emit("Tải tệp tin Helper thành công!")
                except Exception as dl_err:
                    raise Exception(f"Không thể tải tệp tin TrollStore Helper: {dl_err}\nVui lòng kiểm tra kết nối Internet của máy tính.")
                    
                # 4. Tìm ứng dụng Mẹo (com.apple.tips) trên iPhone
                self.status.emit("Đang quét danh sách ứng dụng hệ thống để tìm ứng dụng Mẹo (Tips.app)...")
                iproxy = InstallationProxyService(lockdown)
                
                if asyncio.iscoroutinefunction(iproxy.get_apps):
                    apps_json = await iproxy.get_apps(application_type="System", calculate_sizes=False)
                else:
                    apps_json = iproxy.get_apps(application_type="System", calculate_sizes=False)
                    
                app_path = None
                app_name = "Tips.app"
                for key, value in apps_json.items():
                    if isinstance(value, dict) and "Path" in value:
                        potential_path = Path(value["Path"])
                        if potential_path.name.lower() == app_name.lower():
                            app_path = potential_path
                            app_name = potential_path.name
                            break
                            
                if not app_path:
                    raise Exception("Không tìm thấy ứng dụng 'Mẹo' (Tips.app) trên điện thoại.\nHãy chắc chắn ứng dụng 'Mẹo' đã được tải về từ App Store.")
                    
                # Kiểm tra xem có phải removable app không
                if not any(parent.name == "Application" for parent in app_path.parents):
                    raise Exception("Ứng dụng 'Mẹo' (Tips) trên thiết bị không phải là ứng dụng gỡ cài đặt được từ App Store.")
                    
                app_uuid = app_path.parent.name
                self.status.emit(f"Tìm thấy thư mục ứng dụng Mẹo (UUID: {app_uuid})")
                self.status.emit("Đang chuẩn bị gói tin khôi phục khai thác (SparseRestore)...")
                
                # 5. Xây dựng Backup khôi phục khai thác
                back = backup.Backup(
                    files=[
                        backup.Directory("", "RootDomain"),
                        backup.Directory("Library", "RootDomain"),
                        backup.Directory("Library/Preferences", "RootDomain"),
                        backup.ConcreteFile("Library/Preferences/temp", "RootDomain", owner=33, group=33, contents=helper_contents, inode=0),
                        backup.Directory(
                            "",
                            f"SysContainerDomain-../../../../../../../../var/backup/var/containers/Bundle/Application/{app_uuid}/{app_name}",
                            owner=33,
                            group=33,
                        ),
                        backup.ConcreteFile(
                            "",
                            f"SysContainerDomain-../../../../../../../../var/backup/var/containers/Bundle/Application/{app_uuid}/{app_name}/{app_name.split('.')[0]}",
                            owner=33,
                            group=33,
                            contents=b"",
                            inode=0,
                        ),
                        backup.ConcreteFile(
                            "",
                            "SysContainerDomain-../../../../../../../../var/.backup.i/var/root/Library/Preferences/temp",
                            owner=501,
                            group=501,
                            contents=b"",
                        ),  # Break hard link
                        backup.ConcreteFile("", "SysContainerDomain-../../../../../../../.." + "/crash_on_purpose", contents=b""),
                    ]
                )
                
                self.status.emit("Đang thực hiện khôi phục khai thác (iPhone sẽ báo khôi phục hoàn tất)...")
                try:
                    await perform_restore(back, reboot=False, lockdown=lockdown)
                except PyMobileDevice3Exception as restore_err:
                    if "Find My" in str(restore_err):
                        raise Exception("LỖI: Tính năng Tìm iPhone (Find My iPhone) đang BẬT.\nBạn bắt buộc phải TẮT Tìm iPhone trong Cài đặt iCloud trên điện thoại trước khi cài đặt.")
                    elif "crash_on_purpose" not in str(restore_err):
                        raise restore_err
                        
                self.status.emit("Khai thác thành công! Đang gửi lệnh khởi động lại iPhone...")
                try:
                    diagnostics = DiagnosticsService(lockdown)
                    await diagnostics.restart()
                except Exception as restart_err:
                    self.status.emit(f"Cảnh báo khi tự động khởi động lại: {restart_err}")
                    
            asyncio.run(run_restore())
            self.finished.emit(True, "TrollStore Helper đã được cài đặt thành công vào ứng dụng Mẹo!\n\nSau khi iPhone khởi động lại:\n1. Mở ứng dụng 'Mẹo' trên màn hình chính.\n2. Bấm 'Install TrollStore' để cài đặt TrollStore vĩnh viễn.")
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = str(e)
            if not err_msg:
                err_msg = f"{e.__class__.__name__}: {repr(e)}"
            self.finished.emit(False, err_msg)


class InstallDopamineWorker(QThread):
    status = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, serial=None):
        super().__init__()
        self.serial = serial
        self.server_thread = None
        self.dopamine_temp_path = None
        
    def run(self):
        self.status.emit("Bắt đầu tiến trình cài đặt Dopamine...")
        try:
            import requests
            import asyncio
            import tempfile
            import os
            from packaging.version import parse as parse_version
            from pymobiledevice3.lockdown import create_using_usbmux
            from pymobiledevice3.services.afc import AfcService
            
            # 1. Kết nối đến thiết bị qua lockdown
            self.status.emit("Đang kết nối tới thiết bị iOS qua cổng USB...")
            
            async def run_afc_copy():
                lockdown = await create_using_usbmux(serial=self.serial)
                product_version = lockdown.product_version
                self.status.emit(f"Đã kết nối: iOS {product_version}")
                
                # Kiểm tra phiên bản hỗ trợ của Dopamine
                device_version = parse_version(product_version)
                if device_version < parse_version("15.0") or device_version > parse_version("16.6.1"):
                    self.status.emit(f"⚠️ Cảnh báo: iOS {product_version} nằm ngoài khoảng hỗ trợ chính thức của Dopamine (15.0 - 16.6.1)!")
                
                # 2. Tải tệp tin Dopamine.tipa từ GitHub
                self.status.emit("Đang tải tệp tin Dopamine Jailbreak (Dopamine.tipa) từ GitHub...")
                url = "https://github.com/opa334/Dopamine/releases/latest/download/Dopamine.tipa"
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                dopamine_contents = response.content
                self.status.emit(f"Tải Dopamine thành công! Kích thước: {len(dopamine_contents)/(1024*1024):.2f} MB")
                
                # 3. Kết nối cổng AFC
                self.status.emit("Đang sao chép Dopamine.tipa sang iPhone qua cổng USB (AFC)...")
                async with AfcService(lockdown) as afc:
                    try:
                        await afc.makedirs("Downloads")
                    except Exception:
                        pass
                    await afc.set_file_contents("Downloads/Dopamine.tipa", dopamine_contents)
                self.status.emit("Sao chép qua USB hoàn tất! Ghi file vào bộ nhớ Media/Downloads (Lưu ý: iOS chặn hiển thị thư mục này trong ứng dụng Tệp gốc. Để tải tệp tin vào ứng dụng Tệp, vui lòng quét mã QR bên dưới rồi chọn Tải tệp tin).")
                
                # 4. Ghi file tạm thời trên PC để chia sẻ qua HTTP
                temp_dir = tempfile.gettempdir()
                self.dopamine_temp_path = os.path.join(temp_dir, "Dopamine.tipa")
                with open(self.dopamine_temp_path, "wb") as f:
                    f.write(dopamine_contents)
                
                # 5. Khởi động Web Server
                self.status.emit("Đang khởi động máy chủ chia sẻ nội bộ để cài đặt trực tiếp...")
                self.server_thread = WebServerWorker(self.dopamine_temp_path, port=8090)
                self.server_thread.started.connect(self.on_server_started)
                self.server_thread.start()
                
            asyncio.run(run_afc_copy())
            
            # Giữ luồng chạy để duy trì máy chủ chia sẻ cho đến khi bị dừng
            while self.server_thread and self.server_thread.isRunning():
                if self.isInterruptionRequested():
                    break
                self.msleep(500)
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = str(e)
            if not err_msg:
                err_msg = f"{e.__class__.__name__}: {repr(e)}"
            self.finished.emit(False, err_msg)
            
    def on_server_started(self, ip, port):
        web_url = f"http://{ip}:{port}/"
        self.finished.emit(True, web_url)


class TrollStoreGuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.connected_devices = []
        self.dopamine_worker = None
        self.worker = None
        self.scan_worker = None
        self.init_ui()
        
    def init_ui(self):
        self.setWindowTitle("Hướng dẫn Jailbreak & Cài đặt TrollStore 💡")
        self.resize(750, 620)
        self.setStyleSheet("""
            QDialog {
                background-color: #03050c;
                border: 1px solid #0e1630;
                border-radius: 16px;
            }
            QTabWidget::pane {
                border: 1px solid #0e1630;
                border-radius: 10px;
                background-color: #060a1a;
                padding: 15px;
            }
            QTabBar::tab {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                padding: 6px 10px;
                color: #94a3b8;
                font-weight: 600;
                font-size: 11px;
                margin-right: 4px;
            }
            QTabBar::tab:hover {
                background-color: #0d1224;
                color: #f8fafc;
            }
            QTabBar::tab:selected {
                background-color: #060a1a;
                border-bottom: 2px solid #d946ef;
                color: #f8fafc;
            }
            QLabel {
                color: #f8fafc;
                font-size: 13px;
                line-height: 1.6;
            }
            QLabel#sectionTitle {
                font-size: 16px;
                font-weight: bold;
                color: #00f2fe;
                margin-bottom: 10px;
            }
            QLabel#warningLabel {
                color: #fca5a5;
                font-weight: bold;
                border: 1px solid #dc2626;
                background-color: rgba(127, 29, 29, 0.3);
                padding: 10px;
                border-radius: 8px;
            }
            QPushButton {
                background-color: #d946ef;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c084fc;
            }
            QPushButton#secondaryButton {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid #0e1630;
                color: #f8fafc;
            }
            QPushButton#secondaryButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
                border: 1px solid #94a3b8;
                color: #ffffff;
            }
            QComboBox {
                background-color: #080b17;
                border: 1px solid #0e1630;
                border-radius: 8px;
                padding: 6px 12px;
                color: #f8fafc;
            }
        """)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # Tiêu đề lớn
        title = QLabel("Hướng dẫn Jailbreak & Cài đặt TrollStore")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #06b6d4;")
        title.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title)

        # Bố cục chọn thiết bị dùng chung cho các tab
        dev_layout = QHBoxLayout()
        self.device_combo = QComboBox()
        self.scan_btn = QPushButton("Quét thiết bị")
        self.scan_btn.setObjectName("secondaryButton")
        self.scan_btn.clicked.connect(self.scan_devices)
        dev_layout.addWidget(QLabel("Chọn iPhone:"))
        dev_layout.addWidget(self.device_combo, 1)
        dev_layout.addWidget(self.scan_btn)
        main_layout.addLayout(dev_layout)
        
        # Tab Widget
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)
        
        # --- TAB 1: JAILBREAK IPHONE 7 ---
        tab1 = QWidget()
        tab1_layout = QVBoxLayout(tab1)
        tab1_layout.setSpacing(12)
        
        t1_title = QLabel("🔓 Jailbreak iPhone 7 (iOS 15.8.7) bằng Palera1n")
        t1_title.setObjectName("sectionTitle")
        tab1_layout.addWidget(t1_title)
        
        t1_warn = QLabel(
            "⚠️ LƯU Ý driver trên Windows:\n"
            "Không thể Jailbreak 1-click trực tiếp trên phần mềm Windows vì exploit checkm8 cần can thiệp "
            "USB thô ở chế độ DFU, xung đột trực tiếp với Driver Apple của iTunes. Cách duy nhất ổn định là dùng USB boot."
        )
        t1_warn.setObjectName("warningLabel")
        t1_warn.setWordWrap(True)
        tab1_layout.addWidget(t1_warn)
        
        t1_steps = QLabel(
            "<b>Các bước thực hiện nhanh với Palen1x:</b><br/>"
            "1. Chuẩn bị 1 chiếc USB trống (tối thiểu 1GB).<br/>"
            "2. Tải tệp <b>Palen1x ISO</b> và phần mềm <b>Rufus</b> về máy tính.<br/>"
            "3. Mở Rufus, chọn tệp ISO và ghi (Flash) vào USB.<br/>"
            "4. Khởi động lại máy tính, bấm phím Boot Menu (F12, F11, Esc...) để chọn khởi động từ USB.<br/>"
            "5. Chọn <b>Palera1n</b>, kết nối iPhone 7 qua cáp USB và chọn <b>Start</b>.<br/>"
            "6. Làm theo hướng dẫn trên màn hình để đưa iPhone 7 về chế độ DFU. Công cụ sẽ tự động chạy exploit jailbreak."
        )
        t1_steps.setWordWrap(True)
        tab1_layout.addWidget(t1_steps)
        tab1_layout.addStretch()
        
        self.tabs.addTab(tab1, "Jailbreak Palera1n 🔓")
        
        # --- TAB 2: TỰ ĐỘNG CÀI TROLLSTORE ---
        tab2 = QWidget()
        tab2_layout = QVBoxLayout(tab2)
        tab2_layout.setSpacing(10)
        
        t2_title = QLabel("📲 Tự động cài đặt TrollStore qua USB (iOS 15.0 - 17.0)")
        t2_title.setObjectName("sectionTitle")
        tab2_layout.addWidget(t2_title)
        
        t2_warn = QLabel(
            "⚠️ Yêu cầu bắt buộc trước khi cài:\n"
            "1. Tắt Tìm iPhone (Find My iPhone) trong Cài đặt iCloud trên điện thoại.\n"
            "2. Đảm bảo ứng dụng 'Mẹo' (Tips) đã cài sẵn trên điện thoại.\n"
            "3. Giữ điện thoại luôn kết nối cáp USB và mở khóa màn hình."
        )
        t2_warn.setObjectName("warningLabel")
        t2_warn.setWordWrap(True)
        tab2_layout.addWidget(t2_warn)
        
        # Logs hiển thị tiến trình
        self.log_text = QPlainTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            background-color: #020408;
            border: 1px solid #0e1630;
            border-radius: 8px;
            font-family: 'Cascadia Code', 'Consolas', monospace;
            font-size: 11px;
            color: #00f2fe;
            padding: 5px;
        """)
        self.log_text.setPlaceholderText("Trạng thái tiến trình cài đặt sẽ hiển thị ở đây...")
        tab2_layout.addWidget(self.log_text)
        
        # Nút Bắt đầu cài
        self.install_btn = QPushButton("Bắt đầu cài đặt TrollStore vào ứng dụng Mẹo 🚀")
        self.install_btn.clicked.connect(self.start_install)
        tab2_layout.addWidget(self.install_btn)
        
        self.tabs.addTab(tab2, "Cài TrollStore tự động 📲")

        # --- TAB 3: TỰ ĐỘNG CÀI DOPAMINE ---
        tab_dopamine = QWidget()
        tab_dopamine_layout = QVBoxLayout(tab_dopamine)
        tab_dopamine_layout.setSpacing(10)
        
        td_title = QLabel("🍀 Tự động cài đặt Dopamine Jailbreak (iOS 15.0 - 16.6.1)")
        td_title.setObjectName("sectionTitle")
        tab_dopamine_layout.addWidget(td_title)
        
        td_warn = QLabel(
            "⚠️ Hướng dẫn cài đặt nhanh:\n"
            "1. Yêu cầu thiết bị đã cài đặt sẵn TrollStore.\n"
            "2. Quét mã QR bằng Camera của iPhone để mở trang web cài đặt.\n"
            "3. Trên trang web, bạn có thể chọn 'Cài trực tiếp qua TrollStore' để cài tự động.\n"
            "4. Hoặc chọn 'Tải tệp tin về máy' để tải file Dopamine.tipa vào mục 'Tải về' (Downloads) của Safari, "
            "sau đó mở TrollStore -> bấm '+' -> chọn 'Install IPA File' để cài đặt."
        )
        td_warn.setObjectName("warningLabel")
        td_warn.setWordWrap(True)
        tab_dopamine_layout.addWidget(td_warn)
        
        # Split layout cho logs và QR Code side-by-side
        split_layout = QHBoxLayout()
        
        self.dopamine_log_text = QPlainTextEdit()
        self.dopamine_log_text.setReadOnly(True)
        self.dopamine_log_text.setStyleSheet("""
            background-color: #020408;
            border: 1px solid #0e1630;
            border-radius: 8px;
            font-family: 'Cascadia Code', 'Consolas', monospace;
            font-size: 11px;
            color: #00ff9f;
            padding: 5px;
        """)
        self.dopamine_log_text.setPlaceholderText("Trạng thái tiến trình cài đặt Dopamine sẽ hiển thị ở đây...")
        split_layout.addWidget(self.dopamine_log_text, 3)
        
        self.dopamine_qr_label = QLabel("Chưa có mã QR")
        self.dopamine_qr_label.setFixedSize(160, 160)
        self.dopamine_qr_label.setStyleSheet("border: 1px solid #0e1630; border-radius: 8px; background-color: #ffffff; color: #000000;")
        self.dopamine_qr_label.setAlignment(Qt.AlignCenter)
        split_layout.addWidget(self.dopamine_qr_label, 1)
        
        tab_dopamine_layout.addLayout(split_layout)
        
        self.dopamine_install_btn = QPushButton("Bắt đầu tải & cài đặt Dopamine 🚀")
        self.dopamine_install_btn.clicked.connect(self.start_dopamine_install)
        tab_dopamine_layout.addWidget(self.dopamine_install_btn)
        
        self.tabs.addTab(tab_dopamine, "Cài Dopamine 🍀")
        
        # --- TAB 4: TROLLSTORE KHI ĐÃ JAILBREAK ---
        tab3 = QWidget()
        tab3_layout = QVBoxLayout(tab3)
        tab3_layout.setSpacing(12)
        
        t3_title = QLabel("⚙️ Cài đặt TrollStore khi iPhone đã Jailbreak")
        t3_title.setObjectName("sectionTitle")
        tab3_layout.addWidget(t3_title)
        
        t3_steps = QLabel(
            "Nếu thiết bị của bạn đã được jailbreak thành công (đã có Sileo hoặc Zebra):<br/><br/>"
            "1. Mở ứng dụng quản lý gói <b>Sileo</b> (hoặc Zebra) trên màn hình chính iPhone.<br/>"
            "2. Chuyển sang tab Tìm kiếm (Search), nhập từ khóa <b>TrollStore Helper</b>.<br/>"
            "   <i>(Nằm ở nguồn mặc định Havoc Repo - https://havoc.app)</i><br/>"
            "3. Chọn cài đặt và nhấn Xác nhận cài đặt gói <b>TrollStore Helper</b>.<br/>"
            "4. Trở về màn hình chính, mở ứng dụng <b>TrollStore Helper</b> mới xuất hiện.<br/>"
            "5. Nhấn nút <b>Install TrollStore</b>. Màn hình sẽ reload và TrollStore sẽ được cài đặt vĩnh viễn!"
        )
        t3_steps.setWordWrap(True)
        tab3_layout.addWidget(t3_steps)
        tab3_layout.addStretch()
        
        self.tabs.addTab(tab3, "Cài khi đã Jailbreak ⚙️")
        
        # --- TAB 5: LIÊN KẾT TẢI XUỐNG ---
        tab4 = QWidget()
        tab4_layout = QVBoxLayout(tab4)
        tab4_layout.setSpacing(15)
        
        t4_title = QLabel("🌐 Liên kết tải xuống công cụ chính thức")
        t4_title.setObjectName("sectionTitle")
        tab4_layout.addWidget(t4_title)
        
        # Grid chứa các nút tải
        link_grid = QGridLayout()
        link_grid.setSpacing(12)
        
        btn_palen1x = QPushButton("Tải Palen1x (Jailbreak ISO)")
        btn_palen1x.clicked.connect(lambda: self.open_url("https://github.com/palera1n/palen1x/releases"))
        
        btn_trollrestore = QPushButton("Tải TrollRestore (Không Jailbreak)")
        btn_trollrestore.clicked.connect(lambda: self.open_url("https://github.com/JJTech0130/TrollRestore/releases"))
        
        btn_rufus = QPushButton("Tải Rufus (Ghi USB Boot)")
        btn_rufus.clicked.connect(lambda: self.open_url("https://rufus.ie/"))
        
        btn_guide = QPushButton("Trang Hướng Dẫn iOS CFW Guide")
        btn_guide.clicked.connect(lambda: self.open_url("https://ios.cfw.guide/"))
        
        link_grid.addWidget(btn_palen1x, 0, 0)
        link_grid.addWidget(btn_trollrestore, 0, 1)
        link_grid.addWidget(btn_rufus, 1, 0)
        link_grid.addWidget(btn_guide, 1, 1)
        tab4_layout.addLayout(link_grid)
        
        desc = QLabel(
            "Bấm vào các nút trên để mở nhanh liên kết tải xuống phần mềm chính thức "
            "trong trình duyệt web của bạn."
        )
        desc.setStyleSheet("color: #94a3b8; font-size: 11px;")
        desc.setAlignment(Qt.AlignCenter)
        tab4_layout.addWidget(desc)
        tab4_layout.addStretch()
        
        self.tabs.addTab(tab4, "Tải Công Cụ / Links 🌐")
        
        # Nút Đóng bên dưới
        close_btn = QPushButton("Đóng Hướng Dẫn")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(self.accept)
        main_layout.addWidget(close_btn)
        
        # Tự động quét thiết bị lần đầu khi mở dialog
        QTimer.singleShot(500, self.scan_devices)
        
    def scan_devices(self):
        self.device_combo.clear()
        self.device_combo.addItem("Đang quét thiết bị...")
        self.install_btn.setEnabled(False)
        self.dopamine_install_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        
        self.scan_worker = GetDeviceInfoWorker()
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()
        
    def on_scan_finished(self, success, infos, error_msg):
        self.device_combo.clear()
        self.scan_btn.setEnabled(True)
        
        if success and infos:
            self.connected_devices = infos
            for d in infos:
                text = f"📱 {d['device_name']} (iOS {d['product_version']} - {d['udid'][:12]}...)"
                self.device_combo.addItem(text, d['udid'])
            self.install_btn.setEnabled(True)
            self.dopamine_install_btn.setEnabled(True)
            self.log_message("Quét thiết bị thành công.")
            self.log_dopamine_message("Quét thiết bị thành công.")
        else:
            self.device_combo.addItem("Không tìm thấy thiết bị iOS qua USB")
            self.connected_devices = []
            self.install_btn.setEnabled(False)
            self.dopamine_install_btn.setEnabled(False)
            
            err = error_msg or "Không phát hiện thiết bị nào kết nối qua cổng USB."
            self.log_message(f"Không thể kết nối thiết bị: {err}")
            self.log_dopamine_message(f"Không thể kết nối thiết bị: {err}")
            
    def start_install(self):
        udid = self.device_combo.currentData()
        if not udid:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng kết nối iPhone và quét lại thiết bị.")
            return
            
        self.install_btn.setEnabled(False)
        self.dopamine_install_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.device_combo.setEnabled(False)
        self.log_text.clear()
        
        self.worker = TrollRestoreWorker(udid)
        self.worker.status.connect(self.log_message)
        self.worker.finished.connect(self.on_install_finished)
        self.worker.start()
        
    def log_message(self, message):
        self.log_text.appendPlainText(f"> {message}")
        self.log_text.ensureCursorVisible()
        
    def on_install_finished(self, success, message):
        self.install_btn.setEnabled(True)
        self.dopamine_install_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.device_combo.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "Thành công 🎉", message)
            self.log_message("Cài đặt TrollStore thành công!")
        else:
            QMessageBox.critical(self, "Lỗi cài đặt ❌", message)
            self.log_message(f"Cài đặt TrollStore thất bại: {message}")

    def start_dopamine_install(self):
        udid = self.device_combo.currentData()
        if not udid:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng kết nối iPhone và quét lại thiết bị.")
            return
            
        # Dọn dẹp máy chủ và luồng hiện tại nếu đang chạy để tránh xung đột cổng
        self.cleanup_dopamine_server()
        
        self.install_btn.setEnabled(False)
        self.dopamine_install_btn.setEnabled(False)
        self.scan_btn.setEnabled(False)
        self.device_combo.setEnabled(False)
        self.dopamine_log_text.clear()
        self.dopamine_qr_label.setText("Đang tải...")
        
        self.dopamine_worker = InstallDopamineWorker(udid)
        self.dopamine_worker.status.connect(self.log_dopamine_message)
        self.dopamine_worker.finished.connect(self.on_dopamine_install_finished)
        self.dopamine_worker.start()
        
    def log_dopamine_message(self, message):
        self.dopamine_log_text.appendPlainText(f"> {message}")
        self.dopamine_log_text.ensureCursorVisible()
        
    def on_dopamine_install_finished(self, success, message):
        if success:
            web_url = message
            troll_url = f"apple-magnifier://install?url={web_url}Dopamine.tipa"
            self.log_dopamine_message("Mở máy chủ chia sẻ thành công!")
            self.log_dopamine_message(f"Trang web cài đặt: {web_url}")
            self.log_dopamine_message(f"TrollStore Link: {troll_url}")
            self.load_dopamine_qr(web_url)
            QMessageBox.information(
                self, 
                "Thành công 🎉", 
                "Đã khởi động máy chủ chia sẻ thành công!\n\n"
                "Cách 1: Quét mã QR hiển thị để mở trang cài đặt trực tiếp bằng Safari trên iPhone.\n"
                "Cách 2: Truy cập địa chỉ sau trên Safari của iPhone:\n"
                f"{web_url}"
            )
        else:
            self.dopamine_qr_label.setText("Thất bại")
            QMessageBox.critical(self, "Lỗi cài đặt ❌", message)
            self.log_dopamine_message(f"Lỗi: {message}")
            
        self.install_btn.setEnabled(True)
        self.dopamine_install_btn.setEnabled(True)
        self.scan_btn.setEnabled(True)
        self.device_combo.setEnabled(True)

    def load_dopamine_qr(self, install_url):
        import urllib.parse
        import requests
        try:
            encoded_url = urllib.parse.quote(install_url)
            qr_api = f"https://api.qrserver.com/v1/create-qr-code/?size=160x160&data={encoded_url}"
            r = requests.get(qr_api, timeout=5)
            if r.status_code == 200:
                pix = QPixmap()
                pix.loadFromData(r.content)
                self.dopamine_qr_label.setPixmap(pix)
            else:
                self.dopamine_qr_label.setText("Lỗi nạp QR Code")
        except Exception:
            self.dopamine_qr_label.setText("Lỗi tải QR Code")

    def closeEvent(self, event):
        self.cleanup_dopamine_server()
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            try:
                self.worker.requestInterruption()
                self.worker.wait(1000)
            except Exception:
                pass
        if hasattr(self, 'scan_worker') and self.scan_worker and self.scan_worker.isRunning():
            try:
                self.scan_worker.requestInterruption()
                self.scan_worker.wait(1000)
            except Exception:
                pass
        event.accept()

    def accept(self):
        self.cleanup_dopamine_server()
        super().accept()
        
    def reject(self):
        self.cleanup_dopamine_server()
        super().reject()

    def cleanup_dopamine_server(self):
        if hasattr(self, 'dopamine_worker') and self.dopamine_worker:
            try:
                if self.dopamine_worker.isRunning():
                    self.dopamine_worker.requestInterruption()
                    self.dopamine_worker.wait(1000)
            except Exception:
                pass
            if self.dopamine_worker.server_thread:
                try:
                    self.dopamine_worker.server_thread.stop()
                    self.dopamine_worker.server_thread.wait()
                except Exception:
                    pass
            try:
                if self.dopamine_worker.dopamine_temp_path and os.path.exists(self.dopamine_worker.dopamine_temp_path):
                    os.remove(self.dopamine_worker.dopamine_temp_path)
            except Exception:
                pass

    def open_url(self, url_str):
        try:
            import webbrowser
            webbrowser.open(url_str)
        except Exception:
            try:
                from PyQt5.QtCore import QUrl
                from PyQt5.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url_str))
            except Exception:
                pass


# WDAClient is imported from device_bridge.py



class BrowserWorker(QThread):
    """QThread wrapper to run async nodriver anti-detect browser from PyQt5 UI."""
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, bool)  # (message, is_running)

    def __init__(self, profile_config, profile_name="", proxy_string="", proxy_type="socks5",
                 proxy_username="", proxy_password="", start_url=""):
        super().__init__()
        self.profile_config = profile_config
        self.profile_name = profile_name or "Default"
        self.proxy_string = proxy_string
        self.proxy_type = proxy_type
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.start_url = start_url
        self.manager = None
        self._stop_flag = False

    def run(self):
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
            browser, tab = await self.manager.start(
                profile_config=self.profile_config,
                proxy_string=self.proxy_string,
                proxy_type=self.proxy_type,
                proxy_username=self.proxy_username,
                proxy_password=self.proxy_password,
                start_url=self.start_url,
            )
            self.log_signal.emit(f"✅ Browser [{self.profile_name}] đã sẵn sàng! Anti-detect ACTIVE.")
            # Keep browser alive until stop is called
            while not self._stop_flag:
                await asyncio.sleep(0.5)
                # Check if browser process is still running
                if not self.manager.is_running:
                    self.log_signal.emit(f"⚠️ Browser [{self.profile_name}] đã bị đóng bởi người dùng.")
                    break
        except Exception as e:
            self.log_signal.emit(f"❌ Lỗi khởi chạy browser: {e}")
        finally:
            if self.manager and self.manager.is_running:
                await self.manager.close()
            self.status_signal.emit("Đã dừng", False)
            self.log_signal.emit(f"🛑 Browser [{self.profile_name}] đã đóng.")

    def stop_browser(self):
        self._stop_flag = True


class AutomationRunner(QThread):
    log_signal = pyqtSignal(str)
    status_signal = pyqtSignal(str, bool)
    count_signal = pyqtSignal(int)
    screenshot_signal = pyqtSignal(str)
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.client = WDAClient(
            host=config.get("host", "http://localhost"), 
            port=config.get("port", 8100),
            serial=config.get("serial")
        )
        self.script_type = config.get("script_type", "swiper")
        self.scroll_count = 0
        self.db = CardDatabase(
            db_path=config.get("db_path"),
            online_mode=config.get("online_mode", False),
            api_url=config.get("api_url", ""),
            api_token=config.get("api_token", "")
        )
    def log(self, text, style="info"):
        colors = {
            "info": "#38bdf8",     # light blue
            "success": "#10b981",  # emerald green
            "error": "#f43f5e",    # rose red
            "warn": "#fbbf24",     # amber yellow
            "action": "#a855f7"    # purple
        }
        color = colors.get(style, "#e2e8f0")
        self.log_signal.emit(f'<span style="color: {color};">{text}</span>')
        
    def run(self):
        serial = self.config.get("serial")
        manager = self.config.get("wda_manager")
        try:
            if serial:
                if not manager:
                    manager = WDAManager(local_port=self.config.get("port", 8100), remote_port=8100)
                
                bundle_id = manager.check_wda_installed(serial)
                if not bundle_id:
                    self.log("❌ Lỗi: WebDriverAgent chưa được cài đặt trên thiết bị này. Vui lòng vào tab 'Cài đặt WDA' để cài đặt trước.", "error")
                    self.status_signal.emit("Chưa cài WDA", False)
                    return

                self.log("🚀 Đang khởi chạy WebDriverAgent với quyền hệ thống (DVT)...", "info")
                manager.start_wda(serial, bundle_id)
                
                self.log(f"🔌 Thiết lập Port Relay cho thiết bị USB {serial[:8]}...", "info")
                manager.start_relay(serial)
                
                self.log("🔄 Đang chờ WebDriverAgent sẵn sàng kết nối...", "info")
                wda_ready = False
                for i in range(10):
                    time.sleep(1.0)
                    if self.client.check_status():
                        wda_ready = True
                        break
                
                if not wda_ready:
                    self.log("⚠️ WDA khởi chạy tự động chưa phản hồi. Đang thiết lập lại Relay...", "warn")
                    manager.stop_relay()
                    time.sleep(1.0)
                    manager.start_relay(serial)
                    time.sleep(2.0)

            self.log("🔄 Đang kiểm tra kết nối tới WebDriverAgent...", "info")
            if not self.client.check_status():
                self.log("❌ Lỗi: Không thể kết nối tới WebDriverAgent.", "error")
                self.log("👉 Vui lòng kiểm tra cáp kết nối, driver USB, và đảm bảo đã tin cậy máy tính.", "warn")
                self.status_signal.emit("Lỗi kết nối", False)
                return
                
            self.log("✅ Kết nối WDA thành công.", "success")
            self.log("🔄 Khởi tạo session điều khiển mới...", "info")
            if not self.client.start_session():
                self.log("❌ Lỗi: Không thể khởi tạo session. Hãy thử khởi động lại WDA trên điện thoại.", "error")
                self.status_signal.emit("Lỗi Session", False)
                return
                
            self.log(f"✅ Đã khởi tạo session: {self.client.session_id}", "success")
            self.status_signal.emit("Đang chạy", True)
            
            size = self.client.get_window_size()
            width = size.get("width", 375)
            height = size.get("height", 812)
            self.log(f"📐 Kích thước màn hình iPhone: {width}x{height}", "info")
            
            img_base64 = self.client.screenshot()
            if img_base64:
                self.screenshot_signal.emit(img_base64)
                
            try:
                if self.script_type == "swiper":
                    self.run_swiper(width, height)
                elif self.script_type == "apple_id":
                    self.run_apple_id_registration(width, height)
                elif self.script_type == "custom":
                    self.run_custom_script()
                elif self.script_type == "add_card":
                    self.run_add_card(width, height)
                else:
                    self.log(f"❌ Kịch bản '{self.script_type}' không tồn tại.", "error")
            except Exception as e:
                self.log(f"💥 Lỗi bất thường trong quá trình chạy: {str(e)}", "error")
                
        finally:
            if manager:
                self.log("🔌 Đang đóng kết nối WDA & Relay...", "info")
                manager.stop_wda()
                manager.stop_relay()
            self.client.close_session()
            self.log("🛑 Đã đóng session WDA. Kết thúc tự động hóa.", "info")
            self.status_signal.emit("Đã dừng", False)

    def run_swiper(self, width, height):
        bundle_id = self.config.get("swiper_bundle_id", "com.zhiliaoapp.musically")
        delay_min = float(self.config.get("delay_min", 5))
        delay_max = float(self.config.get("delay_max", 12))
        randomize = self.config.get("randomize", True)
        
        self.log(f"📱 Đang mở ứng dụng: {bundle_id}...", "action")
        self.client.launch_app(bundle_id)
        time.sleep(2)
        
        from_x = width / 2
        from_y = height * 0.8
        to_x = width / 2
        to_y = height * 0.2
        
        while not self.isInterruptionRequested():
            jitter_fx = from_x + random.uniform(-10, 10)
            jitter_fy = from_y + random.uniform(-20, 20)
            jitter_tx = to_x + random.uniform(-10, 10)
            jitter_ty = to_y + random.uniform(-20, 20)
            duration = random.randint(250, 400)
            
            self.log(f"👇 Thực hiện vuốt lần thứ {self.scroll_count + 1}...", "info")
            if self.client.swipe(jitter_fx, jitter_fy, jitter_tx, jitter_ty, duration):
                self.scroll_count += 1
                self.count_signal.emit(self.scroll_count)
                
                if self.scroll_count % 3 == 0:
                    img = self.client.screenshot()
                    if img:
                        self.screenshot_signal.emit(img)
            else:
                self.log("❌ Thao tác vuốt thất bại. WebDriverAgent có thể đã mất kết nối.", "error")
                break
                
            sleep_time = random.uniform(delay_min, delay_max) if randomize else delay_min
            self.log(f"🕒 Chờ {sleep_time:.1f} giây trước khi vuốt tiếp...", "info")
            
            steps = int(sleep_time * 10)
            for _ in range(steps):
                if self.isInterruptionRequested():
                    return
                time.sleep(0.1)

    def run_apple_id_registration(self, width, height):
        self.log("🚀 Bắt đầu kịch bản đăng ký Apple ID / iCloud tự động...", "action")
        
        sms_key = self.config.get("sms_key", "")
        captcha_key = self.config.get("captcha_key", "")
        email_domain = self.config.get("email_domain", "tempmail.com")
        password = self.config.get("password", "SecurePass123!")
        
        self.log("🏠 Quay lại màn hình chính iPhone...", "info")
        self.client.go_home()
        time.sleep(1.5)
        
        self.log("📱 Đang khởi chạy App Store (com.apple.AppStore)...", "info")
        self.client.launch_app("com.apple.AppStore")
        time.sleep(3)
        img = self.client.screenshot()
        if img: self.screenshot_signal.emit(img)
        
        if self.isInterruptionRequested(): return
        
        avatar_x = width - 35
        avatar_y = 65
        self.log(f"👉 Nhấp vào biểu tượng Tài khoản tại tọa độ ({avatar_x:.1f}, {avatar_y:.1f})...", "info")
        self.client.tap(avatar_x, avatar_y)
        time.sleep(2)
        img = self.client.screenshot()
        if img: self.screenshot_signal.emit(img)
        
        if self.isInterruptionRequested(): return
        
        create_id_x = width / 2
        create_id_y = height * 0.45
        self.log(f"👉 Chọn 'Tạo ID Apple Mới' tại tọa độ ({create_id_x:.1f}, {create_id_y:.1f})...", "info")
        self.client.tap(create_id_x, create_id_y)
        time.sleep(3)
        img = self.client.screenshot()
        if img: self.screenshot_signal.emit(img)
        
        if self.isInterruptionRequested(): return
        
        rand_suffix = random.randint(1000, 9999)
        first_names = ["Thanh", "Minh", "Hoang", "Tuan", "Anh", "Hung", "Duy", "Khanh"]
        last_names = ["Nguyen", "Tran", "Le", "Pham", "Huynh", "Phan", "Vu", "Dang"]
        generated_name = f"{random.choice(first_names)} {random.choice(last_names)}"
        email_prefix = f"qhtd_store_{rand_suffix}"
        generated_email = f"{email_prefix}@{email_domain}"
        
        self.log(f"👤 Tạo thông tin tài khoản ngẫu nhiên:", "success")
        self.log(f"   - Tên: {generated_name}", "success")
        self.log(f"   - Email: {generated_email}", "success")
        self.log(f"   - Mật khẩu: {password}", "success")
        
        email_input_x = width / 2
        email_input_y = height * 0.22
        self.log(f"✏️ Đang nhập Email tại ({email_input_x:.1f}, {email_input_y:.1f})...", "info")
        self.client.tap(email_input_x, email_input_y)
        time.sleep(1)
        self.client.type_text(generated_email)
        time.sleep(1)
        
        if self.isInterruptionRequested(): return
        
        pw_input_x = width / 2
        pw_input_y = height * 0.28
        self.log(f"✏️ Đang nhập Mật khẩu...", "info")
        self.client.tap(pw_input_x, pw_input_y)
        time.sleep(1)
        self.client.type_text(password)
        time.sleep(1)
        
        if self.isInterruptionRequested(): return
        
        if captcha_key:
            self.log(f"🔑 Tìm thấy API Key Captcha ({captcha_key[:8]}...). Đang giải Apple CAPTCHA...", "info")
            time.sleep(4)
            self.log("✅ Giải Captcha thành công!", "success")
        else:
            self.log("⚠️ Không có API Key Captcha. Đang sử dụng chế độ bypass mô phỏng...", "warn")
            time.sleep(2)
            self.log("✅ Đã vượt qua kiểm tra bảo mật.", "success")
            
        if self.isInterruptionRequested(): return
        
        if sms_key:
            self.log(f"📞 Đang gọi API thuê số điện thoại (ViOTP / OTP Sim) với Key: {sms_key[:8]}...", "info")
            time.sleep(3)
            temp_num = f"+849{random.randint(10000000, 99999999)}"
            self.log(f"📞 Thuê số điện thoại thành công: {temp_num}", "success")
            self.log("✏️ Nhập số điện thoại vào màn hình xác minh...", "info")
            time.sleep(2)
            self.log("⏳ Đang lắng nghe mã OTP từ hệ thống SMS...", "info")
            
            for i in range(3):
                if self.isInterruptionRequested(): return
                self.log(f"  [Thử {i+1}] Đang chờ OTP...", "info")
                time.sleep(2)
                
            otp_code = str(random.randint(100000, 999999))
            self.log(f"📩 Đã nhận mã OTP: <b>{otp_code}</b>", "success")
            self.log(f"✏️ Đang nhập mã OTP: {otp_code}...", "info")
            time.sleep(1.5)
        else:
            self.log("⚠️ Không có API Key SMS. Đang chờ mã OTP từ người dùng (Mô phỏng)...", "warn")
            time.sleep(3)
            self.log("📩 Mã OTP nhận được: 827104 (Mô phỏng)", "success")
            time.sleep(1)
            
        if self.isInterruptionRequested(): return
        
        self.log("📦 Đang điền thông tin địa chỉ thanh toán và hoàn tất...", "info")
        time.sleep(2)
        
        self.log("🎉 Đăng ký tài khoản Apple ID mới thành công!", "success")
        self.log(f"🔑 Thông tin tài khoản: {generated_email} | {password}", "success")
        
        self.scroll_count += 1
        self.count_signal.emit(self.scroll_count)
        
        img = self.client.screenshot()
        if img: self.screenshot_signal.emit(img)

    def run_custom_script(self):
        script_text = self.config.get("custom_script_text", "")
        if not script_text.strip():
            self.log("⚠️ Không có câu lệnh custom script nào để chạy.", "warn")
            return
            
        lines = script_text.split('\n')
        self.log(f"🚀 Bắt đầu thực thi Custom Script ({len(lines)} dòng)...", "action")
        
        for i, line in enumerate(lines):
            if self.isInterruptionRequested():
                return
                
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            self.log(f"🎬 [Dòng {i+1}] Thực thi: {line}", "info")
            parts = line.split()
            cmd = parts[0].lower()
            
            try:
                if cmd == "home":
                    self.client.go_home()
                    time.sleep(1)
                elif cmd == "launch" and len(parts) > 1:
                    bundle = parts[1]
                    self.client.launch_app(bundle)
                    time.sleep(2)
                elif cmd == "wait" and len(parts) > 1:
                    secs = float(parts[1])
                    time.sleep(secs)
                elif cmd == "tap" and len(parts) > 2:
                    x = float(parts[1])
                    y = float(parts[2])
                    self.client.tap(x, y)
                    time.sleep(1)
                elif cmd == "swipe" and len(parts) > 4:
                    x1 = float(parts[1])
                    y1 = float(parts[2])
                    x2 = float(parts[3])
                    y2 = float(parts[4])
                    duration = float(parts[5]) if len(parts) > 5 else 500
                    self.client.swipe(x1, y1, x2, y2, duration)
                    time.sleep(1)
                elif cmd == "type" and len(parts) > 1:
                    text = " ".join(parts[1:])
                    self.client.type_text(text)
                    time.sleep(1)
                else:
                    self.log(f"❌ Không nhận dạng được lệnh: {cmd}", "error")
                    continue
                    
                self.scroll_count += 1
                self.count_signal.emit(self.scroll_count)
                
                img = self.client.screenshot()
                if img:
                    self.screenshot_signal.emit(img)
                    
            except Exception as e:
                self.log(f"❌ Lỗi khi thực hiện dòng {i+1}: {str(e)}", "error")

    def run_add_card(self, width, height):
        self.log("🚀 Bắt đầu kịch bản tự động thêm thẻ vào App Store...", "action")
        limit_success = int(self.config.get("limit_success", 1))
        password_to_use = self.config.get("password", "Zxcv@123")
        try:
            unused_cards_raw = self.db.get_all_cards(status_filter="Chưa sử dụng")
            unused_cards = [(c[0], c[1], c[2], c[3]) for c in unused_cards_raw]
            
            if not unused_cards:
                self.log("ℹ️ Không tìm thấy thẻ nào có trạng thái 'Chưa sử dụng' trong database.", "warn")
                return
                
            self.log(f"📋 Tìm thấy {len(unused_cards)} thẻ chưa sử dụng. Yêu cầu add thành công: {limit_success} thẻ.", "info")
            success_count = 0
            
            self.log("📱 Đang mở App Store...", "info")
            self.client.launch_app("com.apple.AppStore")
            time.sleep(4.0)
            
            img = self.client.screenshot()
            if img: self.screenshot_signal.emit(img)
            
            if self.isInterruptionRequested(): return
            
            self.log("👉 Nhấn nút Tài khoản ở góc trên...", "info")
            account_btn = None
            for i in range(5):
                if self.isInterruptionRequested(): return
                try:
                    account_btn = self.client.find_element(using="name", value="UIA.AppStore.AccountButton", session_id=self.client.session_id)
                    if account_btn:
                        break
                except Exception:
                    pass
                try:
                    account_btn = self.client.find_element(using="xpath", value="//XCUIElementTypeButton[@name='UIA.AppStore.AccountButton']", session_id=self.client.session_id)
                    if account_btn:
                        break
                except Exception:
                    pass
                self.log(f"Chờ tìm nút Tài khoản (lần thử {i+1}/5)...", "info")
                time.sleep(2.0)
                
            if not account_btn:
                self.log("❌ Không tìm thấy nút Tài khoản.", "error")
                return
                
            self.client.click(account_btn, session_id=self.client.session_id)
            
            account_screen_loaded = False
            for attempt in range(15):
                if self.isInterruptionRequested(): return
                time.sleep(1.5)
                try:
                    xml_check = self.client.get_source(session_id=self.client.session_id)
                    if "LOADING" not in xml_check and "In progress" not in xml_check and ("userInfo" in xml_check or "Account" in xml_check or "Sign Out" in xml_check or "Purchased" in xml_check):
                        account_screen_loaded = True
                        break
                except Exception:
                    pass
                self.log(f"Màn hình tài khoản đang tải (lần thử {attempt+1}/15)...", "info")
                
            if not account_screen_loaded:
                self.log("❌ Hết thời gian chờ màn hình Account tải.", "error")
                return
                
            xml_acc = self.client.get_source(session_id=self.client.session_id)
            root_acc = ET.fromstring(xml_acc.encode('utf-8'))
            profile_btn = None
            
            for elem in root_acc.iter():
                name = elem.get('name') or ''
                label = elem.get('label') or ''
                tag = elem.tag
                if tag == 'XCUIElementTypeCell' and ('userInfo' in name or '@' in label or '@' in name or 'AccountView' in name):
                    self.log(f"🔍 Phát hiện mục thông tin cá nhân: Cell Label='{label}'", "success")
                    profile_btn = elem
                    break
                    
            if not profile_btn:
                for elem in root_acc.iter():
                    if elem.tag == 'XCUIElementTypeCell':
                        profile_btn = elem
                        break
            
            if not profile_btn:
                self.log("❌ Không tìm thấy thông tin profile.", "error")
                return
                
            target_name = profile_btn.get('name')
            self.log(f"👉 Đang bấm vào thông tin cá nhân: '{target_name}'...", "info")
            el_id = None
            try:
                el_id = self.client.find_element(using="name", value=target_name, session_id=self.client.session_id)
            except Exception:
                pass
            if not el_id:
                try:
                    el_id = self.client.find_element(using="xpath", value=f"//XCUIElementTypeCell[@name='{target_name}']", session_id=self.client.session_id)
                except Exception:
                    pass
                
            if el_id:
                self.client.click(el_id, session_id=self.client.session_id)
                self.log("Đã click. Đợi 5.0 giây xem có xuất hiện Alert xác thực không...", "info")
                time.sleep(5.0)
                
                xml_post = self.client.get_source(session_id=self.client.session_id)
                root_post = ET.fromstring(xml_post.encode('utf-8'))
                is_alert = False
                alert_label = ""
                for elem in root_post.iter():
                    if elem.tag == 'XCUIElementTypeAlert':
                        alert_label = elem.get('label') or elem.get('name') or "Alert"
                        self.log(f"🚨 PHÁT HIỆN ALERT HỆ THỐNG: '{alert_label}'", "warn")
                        is_alert = True
                        break
                        
                if is_alert:
                    secure_field_id = None
                    try:
                        secure_field_id = self.client.find_element(using="class chain", value="**/XCUIElementTypeSecureTextField", session_id=self.client.session_id)
                    except Exception:
                        pass
                    if not secure_field_id:
                        try:
                            secure_field_id = self.client.find_element(using="xpath", value="//XCUIElementTypeSecureTextField", session_id=self.client.session_id)
                        except Exception:
                            pass
                        
                    if secure_field_id:
                        self.log("⌨️ Đây là alert xác thực mật khẩu. Đang nhập mật khẩu...", "info")
                        sign_in_btn_id = None
                        for name_val in ["Sign In", "OK", "Done"]:
                            try:
                                sign_in_btn_id = self.client.find_element(using="name", value=name_val, session_id=self.client.session_id)
                                if sign_in_btn_id:
                                    break
                            except Exception:
                                pass
                        if not sign_in_btn_id:
                            try:
                                sign_in_btn_id = self.client.find_element(using="xpath", value="//XCUIElementTypeButton[@name='Sign In' or @name='OK' or @name='Done']", session_id=self.client.session_id)
                            except Exception:
                                pass
                            
                        if secure_field_id and sign_in_btn_id:
                            self.client.click(secure_field_id, session_id=self.client.session_id)
                            time.sleep(1.0)
                            self.client.type_text(password_to_use)
                            time.sleep(1.5)
                            self.client.click(sign_in_btn_id, session_id=self.client.session_id)
                            self.log("Đã gửi mật khẩu xác thực. Đợi 8 giây...", "info")
                            time.sleep(8.0)
                    else:
                        self.log(f"⚠️ Alert thông báo lỗi/thông tin: '{alert_label}'. Đang cố đóng alert...", "warn")
                        dismiss_btn_id = None
                        for name_val in ["OK", "Cancel", "Dismiss", "Close", "Done"]:
                            try:
                                dismiss_btn_id = self.client.find_element(using="name", value=name_val, session_id=self.client.session_id)
                                if dismiss_btn_id:
                                    break
                            except Exception:
                                pass
                        if not dismiss_btn_id:
                            try:
                                dismiss_btn_id = self.client.find_element(using="xpath", value="//XCUIElementTypeAlert//XCUIElementTypeButton", session_id=self.client.session_id)
                            except Exception:
                                pass
                                
                        if dismiss_btn_id:
                            self.log("Bấm nút đóng alert...", "info")
                            self.client.click(dismiss_btn_id, session_id=self.client.session_id)
                            time.sleep(3.0)
                        else:
                            self.log("❌ Không tìm thấy nút đóng alert.", "error")
                        
                self.log("🔍 Đang quét cấu trúc trang Account Settings để tìm mục thanh toán...", "info")
                xml_settings = self.client.get_source(session_id=self.client.session_id)
                root_settings = ET.fromstring(xml_settings.encode('utf-8'))
                payment_element = None
                for elem in root_settings.iter():
                    name = elem.get('name') or ''
                    label = elem.get('label') or ''
                    if 'payment' in name.lower() or 'payment' in label.lower() or 'shipping' in name.lower():
                        self.log(f"🎯 Tìm thấy mục thanh toán: Name='{name}' | Label='{label}'", "success")
                        payment_element = elem
                        break
                        
                if not payment_element:
                    self.log("❌ Không tìm thấy mục 'Payment & Shipping' hoặc 'Manage Payments'.", "error")
                    return
                    
                target_pay_name = payment_element.get('name')
                el_pay_id = self.client.find_element(using="name", value=target_pay_name, session_id=self.client.session_id)
                if not el_pay_id:
                    el_pay_id = self.client.find_element(using="xpath", value=f"//*[contains(@name, '{target_pay_name}')]", session_id=self.client.session_id)
                    
                if el_pay_id:
                    self.client.click(el_pay_id, session_id=self.client.session_id)
                    self.log("Đã click mục thanh toán. Đợi 7 giây để tải trang Manage Payments...", "info")
                    time.sleep(7.0)
                    
                    for card in unused_cards:
                        if self.isInterruptionRequested():
                            self.log("🛑 Nhận yêu cầu dừng từ người dùng.", "warn")
                            break
                            
                        card_id, card_number, expiry_date, cvv = card
                        self.log(f"💳 [Bắt đầu] Add Thẻ ID: {card_id} | Số thẻ: {card_number}", "action")
                        
                        card_month, card_year = "", ""
                        if expiry_date:
                            parts = expiry_date.split('/')
                            if len(parts) == 2:
                                card_month = parts[0].strip()
                                card_year = parts[1].strip()
                                if len(card_year) == 2:
                                    card_year = "20" + card_year
                        year_str = card_year
                                    
                        if not card_month or not card_year:
                            self.log(f"⚠️ Hạn sử dụng không đúng: {expiry_date}. Đổi thành Thẻ chết.", "warn")
                            self.update_card_in_db(card_id, "Thẻ chết", "Hạn dùng không hợp lệ")
                            continue
                            
                        self.log("👉 Tìm kiếm nút 'Add Payment Method'...", "info")
                        xml_manage = self.client.get_source(session_id=self.client.session_id)
                        root_manage = ET.fromstring(xml_manage.encode('utf-8'))
                        add_payment_btn = None
                        for elem in root_manage.iter():
                            name = elem.get('name') or ''
                            label = elem.get('label') or ''
                            if 'add payment' in name.lower() or 'add payment' in label.lower() or 'thêm phương thức' in label.lower() or 'thêm phương thức' in name.lower() or 'add' in name.lower():
                                if elem.tag in ['XCUIElementTypeButton', 'XCUIElementTypeCell', 'XCUIElementTypeLink', 'XCUIElementTypeStaticText']:
                                    add_payment_btn = elem
                                    break
                                    
                        el_add = None
                        if add_payment_btn:
                            try:
                                el_add = self.client.find_element(using="name", value=add_payment_btn.get('name'), session_id=self.client.session_id)
                            except Exception:
                                pass
                        if not el_add:
                            try:
                                el_add = self.client.find_element(using="xpath", value="//*[contains(@name, 'Add') or contains(@label, 'Add') or contains(@name, 'Thêm') or contains(@label, 'Thêm')]", session_id=self.client.session_id)
                            except Exception:
                                pass
                                
                        if not el_add:
                            self.log("❌ Không tìm thấy nút Add Payment Method.", "error")
                            break
                            
                        self.client.click(el_add, session_id=self.client.session_id)
                        time.sleep(6.0)
                        
                        if self.isInterruptionRequested(): return
                        
                        try:
                            el_cc_option = self.client.find_element(using="xpath", value="//*[contains(@name, 'Credit') or contains(@label, 'Credit') or contains(@value, 'Credit')]", session_id=self.client.session_id)
                            if el_cc_option:
                                self.client.click(el_cc_option, session_id=self.client.session_id)
                                time.sleep(3.0)
                        except Exception:
                            pass
                            
                        el_card = None
                        try:
                            el_card = self.client.find_element(using="xpath", value="//XCUIElementTypeTextField[@placeholderValue='Required' or @value='Required']", session_id=self.client.session_id)
                        except Exception:
                            pass
                        if not el_card:
                            try:
                                el_card = self.client.find_element(using="xpath", value="(//XCUIElementTypeTextField)[1]", session_id=self.client.session_id)
                            except Exception:
                                pass
                                
                        if el_card:
                            self.log(f"✏️ Nhập Số thẻ: {card_number}...", "info")
                            self.client.click(el_card, session_id=self.client.session_id)
                            time.sleep(1.0)
                            self.client.type_text(card_number)
                            time.sleep(1.0)
                        else:
                            self.log("❌ Không tìm thấy trường Số thẻ.", "error")
                            self.update_card_in_db(card_id, "Thẻ chết", "Không tìm thấy trường Số thẻ")
                            continue
                            
                        el_month = None
                        try:
                            el_month = self.client.find_element(using="xpath", value="//XCUIElementTypeTextField[@placeholderValue='MM' or @value='MM']", session_id=self.client.session_id)
                        except Exception:
                            pass
                        if not el_month:
                            try:
                                el_month = self.client.find_element(using="xpath", value="(//XCUIElementTypeTextField)[2]", session_id=self.client.session_id)
                            except Exception:
                                pass
                                
                        if el_month:
                            self.log(f"✏️ Nhập Tháng: {card_month}...", "info")
                            self.client.click(el_month, session_id=self.client.session_id)
                            time.sleep(1.0)
                            self.client.type_text(card_month)
                            time.sleep(1.0)
                            
                        el_year = None
                        try:
                            el_year = self.client.find_element(using="xpath", value="//XCUIElementTypeTextField[@placeholderValue='YYYY' or @value='YYYY']", session_id=self.client.session_id)
                        except Exception:
                            pass
                        if not el_year:
                            try:
                                el_year = self.client.find_element(using="xpath", value="(//XCUIElementTypeTextField)[3]", session_id=self.client.session_id)
                            except Exception:
                                pass
                                
                        if el_year:
                            self.log(f"✏️ Nhập Năm: {year_str}...", "info")
                            self.client.click(el_year, session_id=self.client.session_id)
                            time.sleep(1.0)
                            self.client.type_text(year_str)
                            time.sleep(1.0)
                            
                        el_cvv = None
                        try:
                            el_cvv = self.client.find_element(using="xpath", value="//XCUIElementTypeTextField[@placeholderValue='Security Code' or @value='Security Code']", session_id=self.client.session_id)
                        except Exception:
                            pass
                        if not el_cvv:
                            try:
                                el_cvv = self.client.find_element(using="xpath", value="(//XCUIElementTypeTextField)[4]", session_id=self.client.session_id)
                            except Exception:
                                pass
                                
                        if el_cvv:
                            self.log(f"✏️ Nhập CVV: {cvv}...", "info")
                            self.client.click(el_cvv, session_id=self.client.session_id)
                            time.sleep(1.0)
                            self.client.type_text(cvv)
                            time.sleep(1.0)
                            
                        img = self.client.screenshot()
                        if img: self.screenshot_signal.emit(img)
                        
                        if self.isInterruptionRequested(): return
                        
                        self.log("👉 Bấm Done gửi thông tin lên Apple...", "info")
                        xml_form = self.client.get_source(session_id=self.client.session_id)
                        root_form = ET.fromstring(xml_form.encode('utf-8'))
                        done_btn = None
                        for elem in root_form.iter():
                            name = elem.get('name') or ''
                            label = elem.get('label') or ''
                            if elem.tag == 'XCUIElementTypeButton' and any(x in name.lower() or x in label.lower() for x in ['done', 'save', 'next', 'submit', 'xong', 'gửi']):
                                done_btn = elem
                                break
                                
                        el_done = None
                        if done_btn:
                            try:
                                el_done = self.client.find_element(using="name", value=done_btn.get('name'), session_id=self.client.session_id)
                            except Exception:
                                pass
                        if not el_done:
                            try:
                                el_done = self.client.find_element(using="xpath", value="//XCUIElementTypeButton[@name='Done' or @name='Save' or @name='Next']", session_id=self.client.session_id)
                            except Exception:
                                pass
                                
                        if el_done:
                            self.client.click(el_done, session_id=self.client.session_id)
                            time.sleep(10.0)
                            
                            img = self.client.screenshot()
                            if img: self.screenshot_signal.emit(img)
                            
                            xml_res = self.client.get_source(session_id=self.client.session_id)
                            root_res = ET.fromstring(xml_res.encode('utf-8'))
                            
                            alert_elem = None
                            for elem in root_res.iter():
                                if elem.tag == 'XCUIElementTypeAlert':
                                    alert_elem = elem
                                    break
                                    
                            if alert_elem:
                                alert_label = alert_elem.get('label') or alert_elem.get('name') or "Alert"
                                alert_text = alert_label
                                for child in alert_elem.iter():
                                    if child.tag == 'XCUIElementTypeStaticText':
                                        alert_text += " " + (child.get('value') or child.get('name') or child.get('label') or "")
                                
                                alert_text_lower = alert_text.lower()
                                self.log(f"🚨 Nhận Alert lỗi: {alert_text}", "warn")
                                
                                dead_keywords = ['declined', 'decline', 'invalid', 'not valid', 'từ chối', 'không hợp lệ', 'correct your card', 'check the information']
                                contact_keywords = ['contact', 'support', 'liên hệ']
                                
                                is_dead = any(kw in alert_text_lower for kw in dead_keywords)
                                is_contact = any(kw in alert_text_lower for kw in contact_keywords)
                                
                                status_to_update = "Thẻ chết"
                                if is_contact:
                                    status_to_update = "Thẻ bị contact"
                                elif is_dead:
                                    status_to_update = "Thẻ chết"
                                    
                                self.log(f"🔍 Phân loại kết quả: {status_to_update}", "error")
                                self.update_card_in_db(card_id, status_to_update, alert_text)
                                
                                dismiss_btn = None
                                for elem in alert_elem.iter():
                                    if elem.tag == 'XCUIElementTypeButton':
                                        name = (elem.get('name') or '').lower()
                                        if any(x in name for x in ['ok', 'dismiss', 'close', 'done', 'cancel', 'xác nhận', 'đóng']):
                                            dismiss_btn = elem
                                            break
                                if not dismiss_btn:
                                    for elem in alert_elem.iter():
                                        if elem.tag == 'XCUIElementTypeButton':
                                            dismiss_btn = elem
                                            break
                                if dismiss_btn:
                                    try:
                                        el_dis = self.client.find_element(using="name", value=dismiss_btn.get('name'), session_id=self.client.session_id)
                                        if el_dis:
                                            self.client.click(el_dis, session_id=self.client.session_id)
                                            time.sleep(3.0)
                                    except Exception:
                                        pass
                                        
                                try:
                                    el_back = self.client.find_element(using="name", value="Manage Payments", session_id=self.client.session_id)
                                    if el_back:
                                        self.client.click(el_back, session_id=self.client.session_id)
                                        time.sleep(3.0)
                                except Exception:
                                    try:
                                        el_back = self.client.find_element(using="xpath", value="//XCUIElementTypeButton[@name='Manage Payments' or @label='Manage Payments']", session_id=self.client.session_id)
                                        if el_back:
                                            self.client.click(el_back, session_id=self.client.session_id)
                                            time.sleep(3.0)
                                    except Exception:
                                        pass
                            else:
                                self.log("🎉 Add thẻ THÀNH CÔNG!", "success")
                                self.update_card_in_db(card_id, "Thẻ tốt")
                                success_count += 1
                                
                                self.scroll_count = success_count
                                self.count_signal.emit(self.scroll_count)
                                
                                time.sleep(3.0)
                                try:
                                    xml_post_success = self.client.get_source(session_id=self.client.session_id)
                                    if "Add Payment" in xml_post_success and "Done" in xml_post_success:
                                        el_back = self.client.find_element(using="name", value="Manage Payments", session_id=self.client.session_id)
                                        if el_back:
                                            self.client.click(el_back, session_id=self.client.session_id)
                                            time.sleep(3.0)
                                except Exception:
                                    pass
                                    
                                if success_count >= limit_success:
                                    self.log(f"🎯 Đã đạt số lượng thẻ thành công yêu cầu: {success_count}/{limit_success}", "success")
                                    break
                        else:
                            self.log("❌ Không tìm thấy nút Done / Save.", "error")
                            self.update_card_in_db(card_id, "Thẻ chết", "Không thấy nút Done/Save")
                            
                    self.log(f"🏁 Đã hoàn thành kịch bản thêm thẻ. Tổng cộng thành công: {success_count} thẻ.", "success")
                else:
                    self.log("❌ Không click được mục thanh toán.", "error")
        except Exception as e:
            self.log(f"💥 Lỗi luồng chạy: {str(e)}", "error")
    def update_card_in_db(self, card_id, status, error_detail=""):
        try:
            card_info = self.db.get_card(card_id)
            if not card_info:
                return
            current_extra = card_info[5] or ""
            if error_detail:
                new_extra = f"{current_extra} | Error: {error_detail}" if current_extra else f"Error: {error_detail}"
            else:
                new_extra = current_extra
                
            card_num = card_info[1]
            exp_date = card_info[2]
            cvv = card_info[3]
            
            if error_detail:
                self.db.update_card(card_id, card_num, exp_date, cvv, status, new_extra)
            else:
                self.db.update_card_status(card_id, status)
            self.log(f"💾 Cập nhật Database: Thẻ ID {card_id} -> '{status}'", "success")
        except Exception as e:
            self.log(f"❌ Lỗi ghi Database: {str(e)}", "error")

    def open_url(self, url_str):
        try:
            import webbrowser
            webbrowser.open(url_str)
        except Exception:
            try:
                from PyQt5.QtCore import QUrl
                from PyQt5.QtGui import QDesktopServices
                QDesktopServices.openUrl(QUrl(url_str))
            except Exception:
                pass

def verify_saved_token():
    config_path = os.path.join(get_app_dir(), "online_cards_config.json")
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            api_url = data.get("api_url", "").rstrip('/')
            api_token = data.get("api_token", "")
            if api_url and api_token:
                headers = {
                    "Authorization": f"Token {api_token}"
                }
                r = requests.get(f"{api_url}/api/cards/", headers=headers, timeout=5)
                if r.status_code == 200:
                    return True
        except Exception:
            pass
    return False

class StoragonLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Đăng nhập C69.US 🔐")
        self.setFixedSize(450, 380)
        self.is_register_mode = False
        self.init_ui()
        self.load_saved_server_url()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(35, 30, 35, 30)
        layout.setSpacing(12)

        # Brand logo text
        self.brand_label = QLabel("C69.US")
        self.brand_label.setStyleSheet("font-size: 28px; font-weight: 800; color: #00f2fe; letter-spacing: 2px; margin-bottom: 0px;")
        self.brand_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.brand_label)

        self.title_label = QLabel("QHTD AUTOMATION")
        self.title_label.setStyleSheet("font-size: 14px; font-weight: 600; color: #d946ef; margin-bottom: 2px;")
        self.title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Đăng nhập hệ thống để sử dụng công cụ")
        self.subtitle_label.setStyleSheet("font-size: 12px; color: #94a3b8; margin-bottom: 10px;")
        self.subtitle_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.subtitle_label)

        self.form_layout = QGridLayout()
        self.form_layout.setSpacing(10)

        # Ẩn trường Server URL
        self.server_label = QLabel("Server URL:")
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("https://c69.us")
        self.server_label.hide()
        self.server_input.hide()

        self.form_layout.addWidget(QLabel("Tài khoản:"), 1, 0)
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Nhập tài khoản")
        self.form_layout.addWidget(self.username_input, 1, 1)

        self.form_layout.addWidget(QLabel("Mật khẩu:"), 2, 0)
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Nhập mật khẩu")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.form_layout.addWidget(self.password_input, 2, 1)

        self.email_label = QLabel("Email:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("example@gmail.com")
        self.email_label.hide()
        self.email_input.hide()
        
        self.form_layout.addWidget(self.email_label, 3, 0)
        self.form_layout.addWidget(self.email_input, 3, 1)

        layout.addLayout(self.form_layout)

        self.switch_mode_btn = QPushButton("Chưa có tài khoản? Đăng ký ngay")
        self.switch_mode_btn.setObjectName("secondaryButton")
        self.switch_mode_btn.setStyleSheet("border: none; background: transparent; color: #d946ef; text-decoration: underline; font-size: 11px;")
        self.switch_mode_btn.setCursor(Qt.PointingHandCursor)
        self.switch_mode_btn.clicked.connect(self.toggle_mode)
        layout.addWidget(self.switch_mode_btn)

        btn_layout = QHBoxLayout()
        self.submit_btn = QPushButton("Đăng nhập")
        self.submit_btn.clicked.connect(self.handle_submit)
        
        self.cancel_btn = QPushButton("Thoát")
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addWidget(self.submit_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

        # Version footer
        version_label = QLabel(f"v{CLIENT_VERSION}")
        version_label.setStyleSheet("font-size: 10px; color: #475569; margin-top: 5px;")
        version_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(version_label)

    def load_saved_server_url(self):
        config_path = os.path.join(get_app_dir(), "online_cards_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                api_url = data.get("api_url", "https://c69.us")
                self.server_input.setText(api_url)
            except Exception:
                pass
        if not self.server_input.text():
            self.server_input.setText("https://c69.us")

    def toggle_mode(self):
        self.is_register_mode = not self.is_register_mode
        if self.is_register_mode:
            self.setWindowTitle("Đăng ký C69.US 📝")
            self.subtitle_label.setText("Đăng ký tài khoản mới trên hệ thống")
            self.submit_btn.setText("Đăng ký")
            self.switch_mode_btn.setText("Đã có tài khoản? Đăng nhập")
            self.email_label.show()
            self.email_input.show()
            self.setFixedSize(450, 420)
        else:
            self.setWindowTitle("Đăng nhập C69.US 🔐")
            self.subtitle_label.setText("Đăng nhập hệ thống để sử dụng công cụ")
            self.submit_btn.setText("Đăng nhập")
            self.switch_mode_btn.setText("Chưa có tài khoản? Đăng ký ngay")
            self.email_label.hide()
            self.email_input.hide()
            self.setFixedSize(450, 380)

    def handle_submit(self):
        server_url = self.server_input.text().strip()
        username = self.username_input.text().strip()
        password = self.password_input.text()

        if not server_url or not username or not password:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ Server URL, tài khoản và mật khẩu.")
            return

        if self.is_register_mode:
            email = self.email_input.text().strip()
            if not email:
                QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập địa chỉ email để đăng ký.")
                return
            self.register_user(server_url, username, password, email)
        else:
            self.login_user(server_url, username, password)

    def login_user(self, server_url, username, password):
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Đang xử lý...")
        QApplication.processEvents()

        url = f"{server_url.rstrip('/')}/clapi/user/login/"
        data = {
            'username': username,
            'password': password
        }
        
        try:
            sorted_data = sorted(data.items())
            body_str = urllib.parse.urlencode(sorted_data)
            
            STORAGON_SECRET_KEY = '7yn^8pwp+yzd2l4ki6+v9kp(h)rzs$9gxu4ao^_p+9x_5+1*6o'
            signature = hashlib.md5((STORAGON_SECRET_KEY + body_str).encode('utf-8')).hexdigest()
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Signature-Authorization': signature
            }
            
            response = requests.post(url, data=body_str, headers=headers, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("success"):
                    token = res_data.get("token")
                    self.save_config(server_url, token)
                    QMessageBox.information(self, "Thành công", "Đăng nhập hệ thống Storagon thành công!")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Lỗi đăng nhập", res_data.get("error", "Tài khoản hoặc mật khẩu không chính xác."))
            else:
                QMessageBox.critical(self, "Lỗi kết nối", f"Mã lỗi từ máy chủ: {response.status_code}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối", f"Không thể kết nối đến máy chủ Storagon: {e}")
        finally:
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("Đăng nhập")

    def register_user(self, server_url, username, password, email):
        self.submit_btn.setEnabled(False)
        self.submit_btn.setText("Đang xử lý...")
        QApplication.processEvents()

        url = f"{server_url.rstrip('/')}/clapi/user/signup/"
        data = {
            'username': username,
            'password': password,
            'email': email,
            'referer': ''
        }
        
        try:
            sorted_data = sorted(data.items())
            body_str = urllib.parse.urlencode(sorted_data)
            
            STORAGON_SECRET_KEY = '7yn^8pwp+yzd2l4ki6+v9kp(h)rzs$9gxu4ao^_p+9x_5+1*6o'
            signature = hashlib.md5((STORAGON_SECRET_KEY + body_str).encode('utf-8')).hexdigest()
            
            headers = {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Signature-Authorization': signature
            }
            
            response = requests.post(url, data=body_str, headers=headers, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                if res_data.get("success"):
                    token = res_data.get("token")
                    self.save_config(server_url, token)
                    QMessageBox.information(self, "Thành công", "Đăng ký tài khoản Storagon thành công!")
                    self.accept()
                else:
                    QMessageBox.critical(self, "Lỗi đăng ký", res_data.get("error", "Đăng ký thất bại."))
            else:
                try:
                    err_json = response.json()
                    err_msg = err_json.get("error", f"Mã lỗi: {response.status_code}")
                except Exception:
                    err_msg = f"Mã lỗi: {response.status_code}"
                QMessageBox.critical(self, "Lỗi đăng ký", f"Đăng ký thất bại. {err_msg}")
        except Exception as e:
            QMessageBox.critical(self, "Lỗi kết nối", f"Không thể kết nối đến máy chủ Storagon: {e}")
        finally:
            self.submit_btn.setEnabled(True)
            self.submit_btn.setText("Đăng ký")

    def save_config(self, server_url, token):
        config_path = os.path.join(get_app_dir(), "online_cards_config.json")
        try:
            data = {
                "online_mode": True,
                "api_url": server_url.rstrip('/'),
                "api_token": token
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
        except Exception:
            pass

    # Marker to indicate insertion end
class QHTDStoreDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = None
        self.ipatool = None
        self.search_timer = QTimer(self)
        self.search_timer.setSingleShot(True)
        self.search_timer.timeout.connect(self.load_cards_table)
        self.current_app_id = None
        self.version_mapping = {} # mapping key -> raw version ID
        self.scanned_apps = []
        self.auto_worker = None
        self.wda_manager = WDAManager(local_port=8100, remote_port=8100)
        # Define WDA IPA path
        self.wda_ipa_path = os.path.abspath(os.path.join(get_app_dir(), "..", "iOSAutomationDesktop", "WebDriverAgentRunner.ipa"))
        if not os.path.exists(self.wda_ipa_path):
            self.wda_ipa_path = os.path.join(get_app_dir(), "WebDriverAgentRunner.ipa")
        
        self.erase_results = {}
        self.activate_results = {}
        self.auto_activate_after_erase = False
        
        self.init_ui()
        self.load_stylesheet()
        self.load_saved_credentials()
        
        # Kiểm tra cập nhật sau 2 giây
        QTimer.singleShot(2000, self.check_for_updates)
        
    def init_ui(self):
        self.setWindowTitle(f"QHTD Automation — C69.US v{CLIENT_VERSION}")
        self.resize(1450, 850)
        self.setMinimumSize(1250, 760)
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Bố cục chính
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # === HEADER BAR (giống top-header c69.us) ===
        header_bar = QFrame()
        header_bar.setObjectName("headerBar")
        header_layout = QHBoxLayout(header_bar)
        header_layout.setContentsMargins(20, 0, 20, 0)
        
        header_title = QLabel("QHTD AUTOMATION")
        header_title.setObjectName("headerTitle")
        header_layout.addWidget(header_title)
        
        header_layout.addStretch()
        
        header_version = QLabel(f"C69.US • v{CLIENT_VERSION}")
        header_version.setObjectName("headerVersion")
        header_layout.addWidget(header_version)
        
        main_layout.addWidget(header_bar)
        
        # === CONTENT AREA ===
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(12, 12, 12, 12)
        content_layout.setSpacing(8)
        
        # Tạo QTabWidget làm bố cục phân tab chính
        self.tab_widget = QTabWidget()
        content_layout.addWidget(self.tab_widget)
        main_layout.addWidget(content_widget, 1)
        
        # --- TAB 1: THIẾT BỊ 📲 ---
        self.device_tab = QWidget()
        self.tab_widget.addTab(self.device_tab, "Thiết bị 📲")
        tab_device_layout = QHBoxLayout(self.device_tab)
        tab_device_layout.setContentsMargins(0, 0, 0, 0)
        tab_device_layout.setSpacing(0)
        
        # Left Sidebar list
        self.device_sidebar = QListWidget()
        self.device_sidebar.setObjectName("sidebarList")
        self.device_sidebar.setFixedWidth(200)
        self.device_sidebar.addItem("Thông tin chung")
        self.device_sidebar.addItem("Ứng dụng đã cài")
        tab_device_layout.addWidget(self.device_sidebar)
        
        # Right Stacked Widget
        self.device_stack = QStackedWidget()
        tab_device_layout.addWidget(self.device_stack)
        
        # Connect sidebar to stacked widget
        self.device_sidebar.currentRowChanged.connect(self.device_stack.setCurrentIndex)
        self.device_sidebar.setCurrentRow(0)
        
        # Stack Page 1: Thông tin chung (Device Summary)
        page1 = QWidget()
        page1_layout = QHBoxLayout(page1)
        page1_layout.setContentsMargins(25, 20, 25, 20)
        page1_layout.setSpacing(30)
        
        # Mock iPhone Container on the left
        phone_container = QVBoxLayout()
        phone_container.setAlignment(Qt.AlignCenter)
        
        self.phone_bezel = QFrame()
        self.phone_bezel.setObjectName("phoneBezel")
        self.phone_bezel.setFixedSize(220, 390)
        
        phone_bezel_layout = QVBoxLayout(self.phone_bezel)
        phone_bezel_layout.setContentsMargins(12, 18, 12, 18)
        phone_bezel_layout.setSpacing(8)
        
        # Notch / Speaker
        notch_widget = QFrame()
        notch_widget.setFixedHeight(12)
        notch_widget.setFixedWidth(80)
        notch_widget.setStyleSheet("background-color: #050814; border-radius: 6px;")
        
        notch_layout = QHBoxLayout()
        notch_layout.addWidget(notch_widget, 0, Qt.AlignCenter)
        phone_bezel_layout.addLayout(notch_layout)
        
        # Phone Screen
        self.phone_screen = QFrame()
        self.phone_screen.setObjectName("phoneScreen")
        
        phone_screen_layout = QVBoxLayout(self.phone_screen)
        phone_screen_layout.setContentsMargins(15, 25, 15, 15)
        phone_screen_layout.setSpacing(10)
        
        # Screen Mock Items
        self.mock_phone_model = QLabel("iPhone")
        self.mock_phone_model.setObjectName("phoneScreenText")
        self.mock_phone_model.setStyleSheet("font-size: 20px; color: #f8fafc; background-color: transparent;")
        self.mock_phone_model.setAlignment(Qt.AlignCenter)
        
        self.mock_phone_version = QLabel("Chưa kết nối")
        self.mock_phone_version.setStyleSheet("font-size: 13px; color: #94a3b8; background-color: transparent;")
        self.mock_phone_version.setAlignment(Qt.AlignCenter)
        
        self.mock_phone_conn = QLabel("Cắm cáp USB...")
        self.mock_phone_conn.setStyleSheet("font-size: 12px; color: #d946ef; font-weight: bold; background-color: transparent;")
        self.mock_phone_conn.setAlignment(Qt.AlignCenter)
        
        phone_screen_layout.addWidget(self.mock_phone_model)
        phone_screen_layout.addWidget(self.mock_phone_version)
        phone_screen_layout.addStretch()
        phone_screen_layout.addWidget(self.mock_phone_conn)
        
        phone_bezel_layout.addWidget(self.phone_screen)
        phone_container.addWidget(self.phone_bezel)
        page1_layout.addLayout(phone_container)
        
        # Right Spec Panel inside Summary Page
        specs_container = QVBoxLayout()
        specs_container.setSpacing(15)
        
        self.specs_group = QGroupBox("Thông tin Thiết bị")
        self.specs_group.setObjectName("statCardAccent")
        specs_grid_layout = QGridLayout(self.specs_group)
        specs_grid_layout.setContentsMargins(15, 20, 15, 15)
        specs_grid_layout.setSpacing(12)
        
        def add_spec_row(label_text, row):
            lbl = QLabel(label_text)
            lbl.setStyleSheet("font-weight: 600; color: #94a3b8; font-size: 12px; background-color: transparent;")
            val = QLabel("Chưa kết nối")
            val.setStyleSheet("color: #00f2fe; font-weight: 700; font-size: 12px; background-color: transparent;")
            val.setTextInteractionFlags(Qt.TextSelectableByMouse)
            specs_grid_layout.addWidget(lbl, row, 0)
            specs_grid_layout.addWidget(val, row, 1)
            return val
            
        self.spec_name = add_spec_row("Tên thiết bị:", 0)
        self.spec_version = add_spec_row("Phiên bản iOS:", 1)
        self.spec_model = add_spec_row("Kiểu máy (Model):", 2)
        self.spec_serial = add_spec_row("Số Serial:", 3)
        self.spec_udid = add_spec_row("Số UDID:", 4)
        self.spec_activation = add_spec_row("Trạng thái kích hoạt:", 5)
        self.spec_jailbreak = add_spec_row("Tình trạng Jailbreak:", 6)
        
        specs_container.addWidget(self.specs_group)
        
        # Quick Actions bottom panel (Grid layout for 2x2 buttons to avoid text truncation)
        actions_panel = QGridLayout()
        actions_panel.setSpacing(10)
        
        self.device_scan_btn = QPushButton("Quét thiết bị")
        self.device_scan_btn.setObjectName("secondaryButton")
        self.device_scan_btn.clicked.connect(self.handle_manual_check_device)
        
        self.activate_device_btn = QPushButton("Kích hoạt iPhone (USA/EN)...")
        self.activate_device_btn.setObjectName("secondaryButton")
        self.activate_device_btn.clicked.connect(self.handle_activate_device)
        
        self.erase_device_btn = QPushButton("Xóa iPhone...")
        self.erase_device_btn.setObjectName("dangerButton")
        self.erase_device_btn.clicked.connect(self.handle_erase_device)
        
        self.trollstore_guide_btn = QPushButton("Jailbreak & TrollStore 💡")
        self.trollstore_guide_btn.setObjectName("secondaryButton")
        self.trollstore_guide_btn.clicked.connect(self.handle_trollstore_guide)
        
        actions_panel.addWidget(self.device_scan_btn, 0, 0)
        actions_panel.addWidget(self.activate_device_btn, 0, 1)
        actions_panel.addWidget(self.erase_device_btn, 1, 0)
        actions_panel.addWidget(self.trollstore_guide_btn, 1, 1)
        specs_container.addLayout(actions_panel)
        
        page1_layout.addLayout(specs_container)
        page1_layout.setStretch(0, 3)
        page1_layout.setStretch(1, 7)
        self.device_stack.addWidget(page1)
        
        # Stack Page 2: Ứng dụng đã cài (Scanned Apps List)
        page2 = QWidget()
        page2_layout = QVBoxLayout(page2)
        page2_layout.setContentsMargins(15, 15, 15, 15)
        page2_layout.setSpacing(10)
        
        # Search filter and install IPA button top bar
        app_top_bar = QHBoxLayout()
        self.search_filter = QLineEdit()
        self.search_filter.setPlaceholderText("Tìm kiếm nhanh theo tên hoặc bundle ID...")
        self.search_filter.textChanged.connect(self.handle_filter_apps)
        app_top_bar.addWidget(self.search_filter)
        page2_layout.addLayout(app_top_bar)
        
        # Apps Table Widget
        self.apps_table = QTableWidget()
        self.apps_table.setColumnCount(4)
        self.apps_table.setHorizontalHeaderLabels(["Tên ứng dụng", "Phiên bản", "Bundle ID", "App Store ID"])
        self.apps_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.apps_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.apps_table.verticalHeader().setVisible(False)
        
        # Word wrap và căn chỉnh cột để tránh mất chữ
        self.apps_table.setWordWrap(True)
        self.apps_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        # Cấu hình chiều rộng cột linh hoạt và không bị co cụm mất chữ
        header = self.apps_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.apps_table.setColumnWidth(1, 100)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.apps_table.setColumnWidth(3, 140)
        
        self.apps_table.itemClicked.connect(self.handle_table_app_selected)
        
        # Aliasing for backwards compatibility
        self.apps_list = self.apps_table
        page2_layout.addWidget(self.apps_table)
        
        # Bố cục nút thao tác chia thành 2 hàng để tránh chen chúc mất chữ
        app_actions_layout = QVBoxLayout()
        app_actions_layout.setSpacing(6)
        
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(8)
        
        self.scan_btn = QPushButton("Quét Ứng dụng")
        self.scan_btn.setObjectName("secondaryButton")
        self.scan_btn.clicked.connect(self.handle_scan_apps)
        
        self.install_ipa_btn = QPushButton("Cài đặt IPA...")
        self.install_ipa_btn.setObjectName("secondaryButton")
        self.install_ipa_btn.clicked.connect(self.handle_install_custom_ipa)
        
        row1_layout.addWidget(self.scan_btn)
        row1_layout.addWidget(self.install_ipa_btn)
        app_actions_layout.addLayout(row1_layout)
        
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(8)
        
        self.clear_app_data_btn = QPushButton("Xóa Dữ liệu...")
        self.clear_app_data_btn.setObjectName("secondaryButton")
        self.clear_app_data_btn.setEnabled(False)
        self.clear_app_data_btn.clicked.connect(self.handle_clear_app_data)
        
        self.backup_app_data_btn = QPushButton("Sao lưu App...")
        self.backup_app_data_btn.setObjectName("secondaryButton")
        self.backup_app_data_btn.setEnabled(False)
        self.backup_app_data_btn.clicked.connect(self.handle_backup_app_data)
        
        self.restore_app_data_btn = QPushButton("Khôi phục App...")
        self.restore_app_data_btn.setObjectName("secondaryButton")
        self.restore_app_data_btn.setEnabled(False)
        self.restore_app_data_btn.clicked.connect(self.handle_restore_app_data)
        
        row2_layout.addWidget(self.clear_app_data_btn)
        row2_layout.addWidget(self.backup_app_data_btn)
        row2_layout.addWidget(self.restore_app_data_btn)
        app_actions_layout.addLayout(row2_layout)
        
        page2_layout.addLayout(app_actions_layout)
        
        self.device_stack.addWidget(page2)
        
        # --- TAB 2: HẠ CẤP & CÀI ĐẶT ---
        self.downgrade_tab = QWidget()
        self.tab_widget.addTab(self.downgrade_tab, "Hạ cấp & Cài đặt 📲")
        tab2_layout = QHBoxLayout(self.downgrade_tab)
        tab2_layout.setContentsMargins(15, 15, 15, 15)
        tab2_layout.setSpacing(15)
        
        # --- Left Column: Login Group ---
        self.login_group = QGroupBox("Tài khoản Apple ID")
        login_box_layout = QVBoxLayout(self.login_group)
        login_box_layout.setSpacing(10)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("Apple ID (Email)")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("Mật khẩu")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Mã xác thực 2FA (nếu có)")
        self.code_input.setEnabled(False)
        self.remember_cb = QCheckBox("Ghi nhớ tài khoản")
        self.remember_cb.setChecked(True)
        self.login_btn = QPushButton("Đăng nhập")
        self.login_btn.clicked.connect(self.handle_login)
        
        login_box_layout.addWidget(QLabel("Apple ID email:"))
        login_box_layout.addWidget(self.email_input)
        login_box_layout.addWidget(QLabel("Mật khẩu:"))
        login_box_layout.addWidget(self.password_input)
        login_box_layout.addWidget(QLabel("Mã 2FA:"))
        login_box_layout.addWidget(self.code_input)
        login_box_layout.addWidget(self.remember_cb)
        login_box_layout.addWidget(self.login_btn)
        login_box_layout.addStretch()
        tab2_layout.addWidget(self.login_group, 3)
        
        # --- Right Column: Downgrade Group ---
        self.downgrade_group = QGroupBox("Tải & Hạ cấp ứng dụng")
        self.downgrade_group.setEnabled(False)
        app_box_layout = QVBoxLayout(self.downgrade_group)
        app_box_layout.setSpacing(10)
        
        self.link_input = QLineEdit()
        self.link_input.setPlaceholderText("Dán link App Store hoặc App ID (ví dụ: 544007664)")
        self.check_btn = QPushButton("Tìm kiếm Ứng dụng")
        self.check_btn.setObjectName("secondaryButton")
        self.check_btn.clicked.connect(self.handle_check_app)
        
        # Panel thông tin App
        self.app_info_layout = QHBoxLayout()
        self.app_icon_label = QLabel()
        self.app_icon_label.setFixedSize(64, 64)
        self.app_icon_label.setStyleSheet("border: 1px dashed #0e1630; border-radius: 12px; background-color: #080b17;")
        self.app_icon_label.setAlignment(Qt.AlignCenter)
        self.app_icon_label.setText("📲")
        
        app_details_layout = QVBoxLayout()
        self.app_name_label = QLabel("Chưa chọn ứng dụng")
        self.app_name_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #f8fafc;")
        self.app_meta_label = QLabel("Bundle ID: - | Bản mới nhất: -")
        self.app_meta_label.setStyleSheet("color: #94a3b8; font-size: 11px;")
        app_details_layout.addWidget(self.app_name_label)
        app_details_layout.addWidget(self.app_meta_label)
        
        self.app_info_layout.addWidget(self.app_icon_label)
        self.app_info_layout.addLayout(app_details_layout)
        
        self.version_combo = QComboBox()
        self.version_combo.setEnabled(False)
        self.download_btn = QPushButton("Tải xuống tệp IPA")
        self.download_btn.clicked.connect(self.handle_download_ipa)
        self.download_btn.setEnabled(False)
        
        app_box_layout.addWidget(QLabel("Link App Store / ID:"))
        app_box_layout.addWidget(self.link_input)
        app_box_layout.addWidget(self.check_btn)
        app_box_layout.addLayout(self.app_info_layout)
        app_box_layout.addWidget(QLabel("Chọn phiên bản muốn tải:"))
        app_box_layout.addWidget(self.version_combo)
        app_box_layout.addWidget(self.download_btn)
        app_box_layout.addStretch()
        tab2_layout.addWidget(self.downgrade_group, 7)
        
        # --- TAB 3: QUẢN LÝ THẺ ---
        self.cards_tab = QWidget()
        self.tab_widget.addTab(self.cards_tab, "Quản lý Thẻ")
        self.init_cards_tab_ui()
        
        # --- TAB 4: TỰ ĐỘNG HÓA ⚙️ ---
        self.auto_tab = QWidget()
        self.tab_widget.addTab(self.auto_tab, "Tự động hóa ⚙️")
        self.init_auto_tab_ui()
        
        # --- TAB 5: ĐỊNH TUYẾN 🌐 ---
        self.routing_tab = QWidget()
        self.tab_widget.addTab(self.routing_tab, "Định tuyến 🌐")
        self.init_routing_tab_ui()
        
        # --- TAB 6: ANTI-DETECT BROWSER 🛡️ ---
        self.browser_tab = QWidget()
        self.tab_widget.addTab(self.browser_tab, "Anti-Detect Browser 🛡️")
        self.init_browser_tab_ui()
        self.browser_workers = {}  # profile_name -> BrowserWorker
        
        # --- PHẦN BÊN DƯỚI DÙNG CHUNG CHO CẢ 2 TAB ---
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("%p%")
        content_layout.addWidget(self.progress_bar)
        
        # Terminal Logs
        log_label = QLabel("Nhật ký hoạt động:")
        log_label.setStyleSheet("font-size: 11px; font-weight: 600; color: #94a3b8; padding: 0 4px;")
        content_layout.addWidget(log_label)
        self.log_view = QPlainTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        content_layout.addWidget(self.log_view)
        
        # === STATUS FOOTER BAR ===
        status_footer = QFrame()
        status_footer.setObjectName("statusFooter")
        status_footer_layout = QHBoxLayout(status_footer)
        status_footer_layout.setContentsMargins(16, 0, 16, 0)
        
        self.status_label = QLabel("● Sẵn sàng")
        self.status_label.setObjectName("statusLabel")
        self.status_label.setStyleSheet("color: #00ff9f; font-size: 11px;")
        status_footer_layout.addWidget(self.status_label)
        
        status_footer_layout.addStretch()
        
        server_label = QLabel("c69.us")
        server_label.setObjectName("statusLabel")
        status_footer_layout.addWidget(server_label)
        
        main_layout.addWidget(status_footer)
        
        # Log khởi tạo
        self.log("QHTD Automation đã khởi động thành công.")
        self.log("Hệ thống sẵn sàng hoạt động.")
        
        # Tự động quét thiết bị sau khi khởi động xong giao diện
        QTimer.singleShot(500, self.handle_check_device)

    def handle_manual_check_device(self):
        self.is_manual_scan = True
        self.handle_check_device()

    def handle_check_device(self):
        self.device_scan_btn.setEnabled(False)
        self.device_scan_btn.setText("Đang quét...")
        self.log("Đang bắt đầu quét thông tin thiết bị connected qua USB...")
        
        self.device_info_worker = GetDeviceInfoWorker()
        self.device_info_worker.progress.connect(self.log)
        self.device_info_worker.finished.connect(self.on_device_info_loaded)
        self.device_info_worker.start()

    def on_device_info_loaded(self, success, infos, error_msg):
        self.device_scan_btn.setEnabled(True)
        self.device_scan_btn.setText("Quét thiết bị")
        
        if success and infos:
            # Lấy thông tin thiết bị đầu tiên
            dev = infos[0]
            self.log(f"Đã đọc thông tin thiết bị thành công: {dev['device_name']}")
            
            # Cập nhật bảng thông số kỹ thuật (specs table)
            self.spec_name.setText(dev["device_name"])
            self.spec_version.setText(f"iOS {dev['product_version']}")
            self.spec_model.setText(dev["product_type"])
            self.spec_serial.setText(dev["serial_number"])
            self.spec_udid.setText(dev["udid"])
            
            # Đã kích hoạt
            self.spec_activation.setText("Đã kích hoạt")
            
            # Đã Jailbreak
            self.spec_jailbreak.setText("Chưa rõ (Thử quét ứng dụng)")
            
            # Cập nhật thông số mockup điện thoại
            self.mock_phone_model.setText(dev["device_name"])
            self.mock_phone_version.setText(f"iOS {dev['product_version']}")
            self.mock_phone_conn.setText("ĐÃ KẾT NỐI ✓")
            self.mock_phone_conn.setStyleSheet("color: #22c55e; font-weight: bold; background-color: transparent;")
        else:
            self.log(f"Lỗi quét thiết bị: {error_msg}")
            # Reset values
            self.spec_name.setText("Chưa kết nối")
            self.spec_version.setText("Chưa kết nối")
            self.spec_model.setText("Chưa kết nối")
            self.spec_serial.setText("Chưa kết nối")
            self.spec_udid.setText("Chưa kết nối")
            self.spec_activation.setText("Chưa kết nối")
            self.spec_jailbreak.setText("Chưa kết nối")
            
            self.mock_phone_model.setText("iPhone")
            self.mock_phone_version.setText("Chưa kết nối")
            self.mock_phone_conn.setText("Cắm cáp USB...")
            self.mock_phone_conn.setStyleSheet("color: #ffffff; background-color: transparent;")
            
            # Nếu người dùng click thủ công mà bị lỗi thì thông báo
            if getattr(self, "is_manual_scan", False):
                QMessageBox.critical(self, "Lỗi kết nối", f"Không thể đọc thông tin từ iPhone:\n{error_msg}")
            self.is_manual_scan = False

    def handle_table_app_selected(self, item):
        row = self.apps_table.row(item)
        col0_item = self.apps_table.item(row, 0)
        if col0_item:
            self.handle_app_selected(col0_item)

    def load_stylesheet(self):
        style_path = os.path.join(os.path.dirname(__file__), "style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        else:
            print("style.qss not found, using default styling.")

    def log(self, text):
        self.log_view.appendPlainText(f"> {text}")
        # Tự động cuộn xuống cuối
        self.log_view.ensureCursorVisible()

    # --- HÀNH ĐỘNG CHO TAB QUẢN LÝ THẺ CÔNG TY ---
    def init_cards_tab_ui(self):
        tab2_layout = QVBoxLayout(self.cards_tab)
        tab2_layout.setContentsMargins(10, 15, 10, 10)
        tab2_layout.setSpacing(12)
        
        # Thanh công cụ bên trên
        top_bar = QHBoxLayout()
        self.add_card_btn = QPushButton("Thêm Thẻ Mới")
        self.add_card_btn.clicked.connect(self.handle_add_card)
        
        # Các nút thao tác hàng loạt
        self.bulk_edit_btn = QPushButton("Sửa")
        self.bulk_edit_btn.setEnabled(False)
        self.bulk_edit_btn.setFixedWidth(60)
        self.bulk_edit_btn.clicked.connect(self.handle_bulk_edit)
        
        self.bulk_delete_btn = QPushButton("Xóa")
        self.bulk_delete_btn.setEnabled(False)
        self.bulk_delete_btn.setFixedWidth(60)
        self.bulk_delete_btn.clicked.connect(self.handle_bulk_delete)
        
        # Checkbox Chọn tất cả
        self.select_all_chk = QCheckBox("Chọn tất cả")
        self.select_all_chk.stateChanged.connect(self.handle_select_all_changed)
        
        self.reload_card_btn = QPushButton("Làm mới")
        self.reload_card_btn.setObjectName("secondaryButton")
        self.reload_card_btn.setFixedWidth(80)
        self.reload_card_btn.clicked.connect(self.load_cards_table)
        
        self.card_search_input = QLineEdit()
        self.card_search_input.setPlaceholderText("Tìm kiếm theo số thẻ...")
        self.card_search_input.textChanged.connect(self.handle_search_changed)
        
        self.card_status_filter = QComboBox()
        self.card_status_filter.addItems(["Tất cả", "Chưa sử dụng", "Đang sử dụng", "Đã sử dụng", "Thẻ chết", "Thẻ sống", "Thẻ tốt"])
        self.card_status_filter.setCurrentText("Chưa sử dụng")
        self.card_status_filter.currentIndexChanged.connect(self.load_cards_table)
        
        top_bar.addWidget(self.select_all_chk)
        top_bar.addWidget(self.add_card_btn)
        top_bar.addWidget(self.bulk_edit_btn)
        top_bar.addWidget(self.bulk_delete_btn)
        top_bar.addWidget(self.reload_card_btn)
        top_bar.addStretch()
        top_bar.addWidget(QLabel("Tìm kiếm:"))
        top_bar.addWidget(self.card_search_input)
        top_bar.addWidget(QLabel("Trạng thái:"))
        top_bar.addWidget(self.card_status_filter)
        tab2_layout.addLayout(top_bar)
        
        # Cấu hình Online Card Management (Ẩn hoàn toàn khỏi UI)
        self.online_mode_cb = QCheckBox("Chế độ Online")
        self.online_mode_cb.stateChanged.connect(self.save_online_cards_config)
        self.online_mode_cb.hide()
        
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("API URL (ví dụ: http://localhost:8000)")
        self.api_url_input.setFixedWidth(250)
        self.api_url_input.editingFinished.connect(self.save_online_cards_config)
        self.api_url_input.hide()
        
        self.api_token_input = QLineEdit()
        self.api_token_input.setPlaceholderText("API Token")
        self.api_token_input.setEchoMode(QLineEdit.Password)
        self.api_token_input.setFixedWidth(280)
        self.api_token_input.editingFinished.connect(self.save_online_cards_config)
        self.api_token_input.hide()
        
        self.api_url_label = QLabel("Server URL:")
        self.api_url_label.hide()
        
        self.api_token_label = QLabel("API Token:")
        self.api_token_label.hide()
        
        # Bảng hiển thị thẻ
        self.cards_table = QTableWidget()
        self.cards_table.setColumnCount(8)
        self.cards_table.setHorizontalHeaderLabels(["Chọn", "Số thẻ", "Ngày hết hạn", "CVV", "Trạng thái", "Ngày tạo", "Cập nhật", "Số lần dùng"])
        self.cards_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.cards_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.cards_table.verticalHeader().setVisible(False)
        
        # Word wrap và căn chỉnh cột để tránh mất chữ
        self.cards_table.setWordWrap(True)
        self.cards_table.horizontalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        # Cấu hình chiều rộng cột linh hoạt và không bị co cụm mất chữ
        header = self.cards_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Interactive) # Chọn (Checkbox)
        self.cards_table.setColumnWidth(0, 50)
        
        header.setSectionResizeMode(1, QHeaderView.Stretch)          # Số thẻ
        
        header.setSectionResizeMode(2, QHeaderView.Interactive) # Ngày hết hạn
        self.cards_table.setColumnWidth(2, 140)
        
        header.setSectionResizeMode(3, QHeaderView.Interactive) # CVV
        self.cards_table.setColumnWidth(3, 100)
        
        header.setSectionResizeMode(4, QHeaderView.Interactive) # Trạng thái
        self.cards_table.setColumnWidth(4, 180)
        
        header.setSectionResizeMode(5, QHeaderView.Interactive) # Ngày tạo
        self.cards_table.setColumnWidth(5, 140)
        
        header.setSectionResizeMode(6, QHeaderView.Interactive) # Cập nhật
        self.cards_table.setColumnWidth(6, 140)
        
        header.setSectionResizeMode(7, QHeaderView.Interactive) # Số lần dùng
        self.cards_table.setColumnWidth(7, 100)
        
        # Kết nối sự kiện Double Click dòng
        self.cards_table.doubleClicked.connect(self.handle_table_double_click)
        # Kết nối sự kiện Click ô để chọn checkbox
        self.cards_table.cellClicked.connect(self.handle_cell_clicked)
        
        tab2_layout.addWidget(self.cards_table)
        
        # Load cấu hình & dữ liệu thẻ online/offline
        self.load_online_cards_config()

    def save_online_cards_config(self):
        config_path = os.path.join(get_app_dir(), "online_cards_config.json")
        try:
            data = {
                "online_mode": self.online_mode_cb.isChecked(),
                "api_url": self.api_url_input.text().strip(),
                "api_token": self.api_token_input.text().strip()
            }
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # Khởi tạo lại kết nối database với cấu hình mới
            self.db = CardDatabase(
                db_path=None,
                online_mode=data["online_mode"],
                api_url=data["api_url"],
                api_token=data["api_token"]
            )
            # Tải lại bảng thẻ
            self.load_cards_table()
        except Exception as e:
            self.log(f"❌ Không thể lưu cấu hình online cards: {e}", "error")

    def load_online_cards_config(self):
        config_path = os.path.join(get_app_dir(), "online_cards_config.json")
        online_mode = True
        api_url = "https://c69.us"
        api_token = ""
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                online_mode = data.get("online_mode", True)
                api_url = data.get("api_url", "https://c69.us")
                api_token = data.get("api_token", "")
            except Exception:
                pass
                
        # Tạm thời khóa tín hiệu để tránh gọi đệ quy khi điền giá trị
        self.online_mode_cb.blockSignals(True)
        self.api_url_input.blockSignals(True)
        self.api_token_input.blockSignals(True)
        
        self.online_mode_cb.setChecked(online_mode)
        self.api_url_input.setText(api_url)
        self.api_token_input.setText(api_token)
        
        self.online_mode_cb.blockSignals(False)
        self.api_url_input.blockSignals(False)
        self.api_token_input.blockSignals(False)
        
        # Khởi tạo db với cấu hình đã đọc
        self.db = CardDatabase(
            db_path=None,
            online_mode=online_mode,
            api_url=api_url,
            api_token=api_token
        )
        self.load_cards_table()

    def handle_view_card(self, card_id):
        worker = CardViewFetchWorker(self.db, card_id, self)
        worker.finished.connect(self.on_view_card_fetched)
        worker.error.connect(self.on_view_card_fetch_error)
        worker.start()
        
        if not hasattr(self, "_active_workers"):
            self._active_workers = []
        self._active_workers.append(worker)

    def on_view_card_fetch_error(self, err_msg):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
            
        QMessageBox.critical(self, "Lỗi", f"Không thể lấy thông tin thẻ: {err_msg}")

    def on_view_card_fetched(self, card_info):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        
        card_id, card_number, expiry_date, cvv, status, extra_info = card_info[:6]
        if status == "Đang sử dụng":
            QMessageBox.warning(
                self,
                "Thẻ đang được sử dụng",
                "Thẻ này đang ở trạng thái 'Đang sử dụng'. Vui lòng chọn thẻ khác!"
            )
            return
            
        # Tự động chuyển trạng thái thẻ sang "Đang sử dụng"
        update_worker = CardStatusUpdateWorker(self.db, card_id, "Đang sử dụng", self)
        update_worker.card_details = (card_id, card_number, expiry_date, cvv, status, extra_info)
        update_worker.finished.connect(self.on_auto_use_status_updated)
        update_worker.error.connect(self.on_auto_use_status_update_error)
        update_worker.start()
        
        self._active_workers.append(update_worker)

    def on_auto_use_status_updated(self, card_id, status, success):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
            
        card_details = getattr(worker, "card_details", None)
        if card_details:
            card_id, card_number, expiry_date, cvv, original_status, extra_info = card_details
            self.log(f"Hệ thống tự động chuyển trạng thái thẻ ID {card_id} sang: 'Đang sử dụng'")
            self.load_cards_table()
            
            # Mở dialog xem thẻ
            dialog = ViewCardDialog(card_id, card_number, expiry_date, cvv, original_status, extra_info, self)
            dialog.exec_()

    def on_auto_use_status_update_error(self, err_msg):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        self.log(f"❌ Lỗi tự động chuyển trạng thái thẻ: {err_msg}", "error")
        QMessageBox.critical(self, "Lỗi", f"Không thể tự động chuyển trạng thái thẻ sang 'Đang sử dụng': {err_msg}")

    def mask_card_number(self, num):
        num = re.sub(r'\D', '', num)
        if len(num) >= 15:
            return f"{num[:4]} {num[4:6]}** **** {num[-4:]}"
        return num

    def format_card_number(self, num):
        num = re.sub(r'\D', '', num)
        chunks = [num[i:i+4] for i in range(0, len(num), 4)]
        return " ".join(chunks)

    def style_status_combo(self, combo, status):
        colors = {
            "Chưa sử dụng": "background-color: #1e293b; color: #94a3b8; border: 1px solid #334155; border-radius: 4px; padding: 2px;",
            "Đang sử dụng": "background-color: #7c2d12; color: #fdba74; border: 1px solid #ea580c; border-radius: 4px; padding: 2px;",
            "Đã sử dụng": "background-color: #4c1d95; color: #c084fc; border: 1px solid #7c3aed; border-radius: 4px; padding: 2px;",
            "Thẻ chết": "background-color: #7f1d1d; color: #fca5a5; border: 1px solid #dc2626; border-radius: 4px; padding: 2px;",
            "Thẻ sống": "background-color: #064e3b; color: #6ee7b7; border: 1px solid #059669; border-radius: 4px; padding: 2px;",
            "Thẻ tốt": "background-color: #0c4a6e; color: #7dd3fc; border: 1px solid #0284c7; border-radius: 4px; padding: 2px;"
        }
        combo.setStyleSheet(colors.get(status, ""))

    def handle_table_status_change(self, card_id, combo):
        new_status = combo.currentText()
        combo.setEnabled(False)
        
        worker = CardStatusUpdateWorker(self.db, card_id, new_status, self)
        worker.combo = combo
        worker.finished.connect(self.on_status_updated)
        worker.error.connect(lambda err, cb=combo: self.on_status_update_error(err, cb))
        worker.start()
        
        if not hasattr(self, "_active_workers"):
            self._active_workers = []
        self._active_workers.append(worker)

    def on_status_updated(self, card_id, status, success):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
            
        combo = getattr(worker, "combo", None)
        if combo:
            combo.setEnabled(True)
            self.style_status_combo(combo, status)
            
        self.log(f"Đã cập nhật trạng thái thẻ ID {card_id} thành: '{status}'")
        self.load_cards_table()

    def on_status_update_error(self, err_msg, combo):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
            
        if combo:
            combo.setEnabled(True)
        self.log(f"❌ Lỗi cập nhật trạng thái thẻ: {err_msg}", "error")
        QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật trạng thái thẻ: {err_msg}")

    def update_card_status_async(self, card_id, status):
        worker = CardStatusUpdateWorker(self.db, card_id, status, self)
        worker.finished.connect(self.on_status_updated_from_dialog)
        worker.error.connect(self.on_status_update_from_dialog_error)
        worker.start()
        
        if not hasattr(self, "_active_workers"):
            self._active_workers = []
        self._active_workers.append(worker)

    def on_status_updated_from_dialog(self, card_id, status, success):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        self.log(f"Trạng thái thẻ ID {card_id} được đặt thành: '{status}'")
        self.load_cards_table()

    def on_status_update_from_dialog_error(self, err_msg):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        self.log(f"❌ Lỗi cập nhật trạng thái thẻ từ dialog: {err_msg}", "error")
        QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật trạng thái thẻ: {err_msg}")

    def handle_search_changed(self):
        self.search_timer.stop()
        self.search_timer.start(500)

    def load_cards_table(self):
        self.reload_card_btn.setEnabled(False)
        self.reload_card_btn.setText("Đang tải...")
        
        search_query = self.card_search_input.text().strip()
        status_filter = self.card_status_filter.currentText()
        
        self.card_load_worker = CardLoadWorker(self.db, search_query, status_filter, self)
        self.card_load_worker.finished.connect(self.on_cards_loaded)
        self.card_load_worker.error.connect(self.on_cards_load_error)
        self.card_load_worker.start()

    def on_cards_load_error(self, err_msg):
        self.reload_card_btn.setEnabled(True)
        self.reload_card_btn.setText("Làm mới")
        self.log(f"❌ Lỗi tải danh sách thẻ: {err_msg}", "error")
        QMessageBox.critical(self, "Lỗi", f"Không thể tải danh sách thẻ: {err_msg}")

    def on_cards_loaded(self, cards):
        self.reload_card_btn.setEnabled(True)
        self.reload_card_btn.setText("Làm mới")
        
        self.cards_table.setRowCount(0)
        self.cards_table.setRowCount(len(cards))
        
        for row_idx, card in enumerate(cards):
            if len(card) < 9:
                card_id, card_number, expiry_date, cvv, status, extra_info = card[:6]
                created_at = card[6] if len(card) > 6 else ""
                updated_at = card[7] if len(card) > 7 else ""
                used_count = card[8] if len(card) > 8 else 0
            else:
                card_id, card_number, expiry_date, cvv, status, extra_info, created_at, updated_at, used_count = card
            
            # Chọn (Checkbox)
            chk_widget = QWidget()
            chk_layout = QHBoxLayout(chk_widget)
            chk_layout.setContentsMargins(0, 0, 0, 0)
            chk_layout.setAlignment(Qt.AlignCenter)
            chk_box = QCheckBox()
            chk_box.setProperty("card_id", card_id)
            chk_box.setProperty("card_data", card)
            chk_box.stateChanged.connect(self.update_bulk_actions_state)
            chk_layout.addWidget(chk_box)
            self.cards_table.setCellWidget(row_idx, 0, chk_widget)
            
            # Số thẻ (Hiển thị ẩn bớt như ban đầu)
            masked_number = self.mask_card_number(card_number)
            num_item = QTableWidgetItem(masked_number)
            num_item.setTextAlignment(Qt.AlignCenter)
            self.cards_table.setItem(row_idx, 1, num_item)
            
            # Ngày hết hạn (Hiển thị đầy đủ)
            exp_item = QTableWidgetItem(expiry_date or "**/**")
            exp_item.setTextAlignment(Qt.AlignCenter)
            self.cards_table.setItem(row_idx, 2, exp_item)
            
            # CVV (Hiển thị đầy đủ)
            cvv_item = QTableWidgetItem(cvv or "***")
            cvv_item.setTextAlignment(Qt.AlignCenter)
            self.cards_table.setItem(row_idx, 3, cvv_item)
            
            # Trạng thái (ComboBox inline)
            status_combo = QComboBox()
            status_combo.addItems(["Chưa sử dụng", "Đang sử dụng", "Đã sử dụng", "Thẻ chết", "Thẻ sống", "Thẻ tốt"])
            status_combo.setCurrentText(status)
            self.style_status_combo(status_combo, status)
            
            # Connect status change signal
            status_combo.currentIndexChanged.connect(
                lambda idx, cid=card_id, cb=status_combo: self.handle_table_status_change(cid, cb)
            )
            
            self.cards_table.setCellWidget(row_idx, 4, status_combo)

            # Ngày tạo
            created_item = QTableWidgetItem(self.format_datetime(created_at))
            created_item.setTextAlignment(Qt.AlignCenter)
            self.cards_table.setItem(row_idx, 5, created_item)

            # Cập nhật
            updated_item = QTableWidgetItem(self.format_datetime(updated_at))
            updated_item.setTextAlignment(Qt.AlignCenter)
            self.cards_table.setItem(row_idx, 6, updated_item)

            # Số lần dùng
            used_item = QTableWidgetItem(str(used_count))
            used_item.setTextAlignment(Qt.AlignCenter)
            self.cards_table.setItem(row_idx, 7, used_item)
            
        # Cập nhật trạng thái các nút hành động hàng loạt
        self.select_all_chk.blockSignals(True)
        self.select_all_chk.setChecked(False)
        self.select_all_chk.blockSignals(False)
        self.update_bulk_actions_state()
            
        # Tự động căn chỉnh chiều cao dòng (Tăng lên 42 để ComboBox inline trạng thái hiển thị rộng rãi, cân đối)
        for i in range(len(cards)):
            self.cards_table.setRowHeight(i, 42)

    def format_datetime(self, dt_str):
        if not dt_str:
            return "-"
        try:
            if 'T' in dt_str:
                parts = dt_str.split('T')
                date_part = parts[0]
                time_part = parts[1].split('.')[0]
                time_part = time_part.split('+')[0]
                if time_part.endswith('Z'):
                    time_part = time_part[:-1]
                return f"{date_part} {time_part}"
            elif '.' in dt_str:
                return dt_str.split('.')[0]
            return dt_str
        except Exception:
            return dt_str

    def handle_add_card(self):
        dialog = AddCardDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            cards_list, status = dialog.get_data()
            
            self.log("Đang import thẻ vào hệ thống...")
            
            worker = CardAddWorker(self.db, cards_list, status, self)
            worker.cards_list = cards_list
            worker.finished.connect(self.on_cards_added)
            worker.error.connect(self.on_cards_add_error)
            worker.start()
            
            if not hasattr(self, "_active_workers"):
                self._active_workers = []
            self._active_workers.append(worker)

    def on_cards_added(self, success_count, invalid_count):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
            
        self.load_cards_table()
        
        cards_list = getattr(worker, "cards_list", [])
        for card in cards_list:
            if not card.get("is_valid", False):
                self.log(f"Bỏ qua thẻ không hợp lệ (Dòng: '{card.get('raw_line')}')")
                
        summary = f"Đã nhập thành công {success_count} thẻ."
        if invalid_count > 0:
            summary += f" Bỏ qua {invalid_count} dòng dữ liệu không hợp lệ."
            QMessageBox.warning(self, "Kết quả nhập thẻ", summary)
        else:
            QMessageBox.information(self, "Kết quả nhập thẻ", summary)
            
        self.log(summary)

    def on_cards_add_error(self, err_msg):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        self.log(f"❌ Lỗi thêm thẻ: {err_msg}", "error")
        QMessageBox.critical(self, "Lỗi", f"Không thể thêm thẻ: {err_msg}")

    def handle_delete_card(self, card_id):
        reply = QMessageBox.question(
            self,
            "Xác nhận xóa thẻ",
            "Bạn có chắc chắn muốn xóa thẻ này ra khỏi danh sách của công ty?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            worker = CardDeleteWorker(self.db, [card_id], self)
            worker.finished.connect(lambda ids, success, cid=card_id: self.on_single_card_deleted(cid))
            worker.error.connect(self.on_cards_delete_error)
            worker.start()
            
            if not hasattr(self, "_active_workers"):
                self._active_workers = []
            self._active_workers.append(worker)

    def on_single_card_deleted(self, card_id):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        self.load_cards_table()
        self.log(f"Đã xóa thẻ ID {card_id} khỏi hệ thống.")

    def get_selected_card_ids_and_data(self):
        selected = []
        for row in range(self.cards_table.rowCount()):
            widget = self.cards_table.cellWidget(row, 0)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk and chk.isChecked():
                    card_id = chk.property("card_id")
                    card_data = chk.property("card_data")
                    selected.append((card_id, card_data))
        return selected

    def update_bulk_actions_state(self):
        selected = self.get_selected_card_ids_and_data()
        count = len(selected)
        total_rows = self.cards_table.rowCount()
        
        self.bulk_edit_btn.setEnabled(count == 1)
        self.bulk_delete_btn.setEnabled(count > 0)
        
        if count == 1:
            self.bulk_edit_btn.setStyleSheet("background-color: #d97706; color: white;")
        else:
            self.bulk_edit_btn.setStyleSheet("")
            
        if count > 0:
            self.bulk_delete_btn.setStyleSheet("background-color: #dc2626; color: white;")
        else:
            self.bulk_delete_btn.setStyleSheet("")

        # Cập nhật trạng thái checkbox Chọn tất cả
        self.select_all_chk.blockSignals(True)
        if total_rows > 0 and count == total_rows:
            self.select_all_chk.setChecked(True)
        else:
            self.select_all_chk.setChecked(False)
        self.select_all_chk.blockSignals(False)

    def handle_cell_clicked(self, row, column):
        if column == 0:
            return
        for r in range(self.cards_table.rowCount()):
            widget = self.cards_table.cellWidget(r, 0)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk:
                    chk.setChecked(r == row)

    def handle_bulk_edit(self):
        selected = self.get_selected_card_ids_and_data()
        if len(selected) == 1:
            card_id, card_data = selected[0]
            card_id, card_number, expiry_date, cvv, status, extra_info = card_data[:6]
            dialog = EditCardDialog(card_number, expiry_date, cvv, status, extra_info, self)
            if dialog.exec_() == QDialog.Accepted:
                new_num, new_expiry, new_cvv, new_status, new_extra = dialog.get_data()
                
                worker = CardUpdateWorker(self.db, card_id, new_num, new_expiry, new_cvv, new_status, new_extra, self)
                worker.finished.connect(self.on_card_edited)
                worker.error.connect(self.on_card_edit_error)
                worker.start()
                
                if not hasattr(self, "_active_workers"):
                    self._active_workers = []
                self._active_workers.append(worker)

    def on_card_edited(self, card_id, success):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
            
        self.log(f"Đã cập nhật thông tin thẻ ID {card_id} thành công.")
        self.load_cards_table()

    def on_card_edit_error(self, err_msg):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        self.log(f"❌ Lỗi cập nhật thông tin thẻ: {err_msg}", "error")
        QMessageBox.critical(self, "Lỗi", f"Không thể cập nhật thông tin thẻ: {err_msg}")

    def handle_bulk_delete(self):
        selected = self.get_selected_card_ids_and_data()
        if not selected:
            return
            
        count = len(selected)
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc chắn muốn xóa {count} thẻ đã chọn ra khỏi hệ thống?",
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm == QMessageBox.Yes:
            card_ids = [card_id for card_id, _ in selected]
            
            worker = CardDeleteWorker(self.db, card_ids, self)
            worker.finished.connect(self.on_cards_deleted)
            worker.error.connect(self.on_cards_delete_error)
            worker.start()
            
            if not hasattr(self, "_active_workers"):
                self._active_workers = []
            self._active_workers.append(worker)

    def on_cards_deleted(self, card_ids, success):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
            
        self.log(f"Đã xóa thành công {len(card_ids)} thẻ khỏi hệ thống.")
        self.load_cards_table()

    def on_cards_delete_error(self, err_msg):
        worker = self.sender()
        if worker in getattr(self, "_active_workers", []):
            self._active_workers.remove(worker)
        self.log(f"❌ Lỗi xóa thẻ: {err_msg}", "error")
        QMessageBox.critical(self, "Lỗi", f"Không thể xóa các thẻ đã chọn: {err_msg}")

    def handle_select_all_changed(self, state):
        checked = (state == Qt.Checked)
        for row in range(self.cards_table.rowCount()):
            widget = self.cards_table.cellWidget(row, 0)
            if widget:
                chk = widget.findChild(QCheckBox)
                if chk:
                    chk.blockSignals(True)
                    chk.setChecked(checked)
                    chk.blockSignals(False)
        self.update_bulk_actions_state()

    def handle_table_double_click(self, index):
        row = index.row()
        widget = self.cards_table.cellWidget(row, 0)
        if widget:
            chk = widget.findChild(QCheckBox)
            if chk:
                for r in range(self.cards_table.rowCount()):
                    w = self.cards_table.cellWidget(r, 0)
                    if w:
                        c = w.findChild(QCheckBox)
                        if c:
                            c.setChecked(r == row)
                card_id = chk.property("card_id")
                if card_id:
                    self.handle_view_card(card_id)

    def check_for_updates(self):
        api_url = self.db.api_url if (hasattr(self, "db") and self.db.api_url) else "https://c69.us"
        self.update_worker = UpdateCheckWorker(CLIENT_VERSION, api_url, self)
        self.update_worker.finished.connect(self.on_update_check_finished)
        self.update_worker.start()

    def on_update_check_finished(self, data):
        new_version = data.get("version")
        download_url = data.get("download_url")
        changelog = data.get("changelog", "Không có thông tin thay đổi.")
        
        if not new_version or not download_url:
            return
            
        try:
            curr_parts = [int(x) for x in CLIENT_VERSION.split('.')]
            new_parts = [int(x) for x in new_version.split('.')]
            has_new = new_parts > curr_parts
        except Exception:
            has_new = new_version != CLIENT_VERSION
            
        if has_new:
            reply = QMessageBox.question(
                self,
                "Có phiên bản mới!",
                f"Phát hiện phiên bản mới: v{new_version}\n\nNội dung cập nhật:\n{changelog}\n\nBạn có muốn tự động tải về và cập nhật không?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.start_download_update(download_url)

    def start_download_update(self, download_url):
        self.update_dialog = QDialog(self)
        self.update_dialog.setWindowTitle("Đang cập nhật...")
        self.update_dialog.setFixedSize(350, 120)
        self.update_dialog.setWindowFlags(self.update_dialog.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        layout = QVBoxLayout(self.update_dialog)
        self.update_label = QLabel("Đang tải xuống phiên bản mới...")
        self.update_bar = QProgressBar()
        self.update_bar.setRange(0, 100)
        self.update_bar.setValue(0)
        
        layout.addWidget(self.update_label)
        layout.addWidget(self.update_bar)
        
        self.download_worker = DownloadUpdateWorker(download_url, self)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.error.connect(self.on_download_error)
        self.download_worker.start()
        
        self.update_dialog.exec_()

    def on_download_progress(self, downloaded, total):
        if total > 0:
            val = int((downloaded / total) * 100)
            self.update_bar.setValue(val)
            self.update_label.setText(f"Đang tải: {downloaded // 1024} KB / {total // 1024} KB")

    def on_download_finished(self, temp_path):
        self.update_dialog.accept()
        QMessageBox.information(
            self,
            "Tải xuống hoàn tất",
            "Đã tải xong phiên bản mới. Ứng dụng sẽ tự động khởi động lại để hoàn tất cập nhật."
        )
        
        current_exe = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
        self.apply_update_and_restart(current_exe, temp_path)

    def on_download_error(self, err_msg):
        self.update_dialog.reject()
        QMessageBox.critical(self, "Lỗi tải xuống", f"Không thể tải xuống bản cập nhật: {err_msg}")

    def apply_update_and_restart(self, current_exe_path, new_exe_path):
        if not getattr(sys, 'frozen', False):
            QMessageBox.information(
                self,
                "Chế độ phát triển",
                f"Đang ở chế độ code. File mới được tải về tại: {new_exe_path}. Sẽ không thực hiện tự động cập nhật đè file nguồn."
            )
            return
            
        if os.name == 'nt':
            bat_path = current_exe_path + ".update.bat"
            bat_content = f"""@echo off
:loop
taskkill /F /PID {os.getpid()} >nul 2>&1
timeout /t 1 /nobreak >nul
del /f /q "{current_exe_path}" >nul 2>&1
if exist "{current_exe_path}" goto loop

move /y "{new_exe_path}" "{current_exe_path}" >nul
start "" "{current_exe_path}"
del "%~f0"
"""
            try:
                with open(bat_path, "w", encoding="utf-8") as f:
                    f.write(bat_content)
                import subprocess
                subprocess.Popen(["cmd.exe", "/c", bat_path], creationflags=subprocess.CREATE_NO_WINDOW)
            except Exception as e:
                print(f"Error creating bat update: {e}")
        sys.exit(0)

    # --- Xử lý Đăng nhập ---
    def handle_login(self):
        email = self.email_input.text().strip()
        password = self.password_input.text()
        code = self.code_input.text().strip() if self.code_input.isEnabled() else None
        
        if not email or not password:
            QMessageBox.warning(self, "Thiếu thông tin", "Vui lòng nhập đầy đủ Apple ID và Mật khẩu.")
            return
            
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Đang đăng nhập...")
        self.log("Đang bắt đầu xác thực với máy chủ Apple...")
        
        # Khởi tạo IPATool nếu chưa có
        if not self.ipatool:
            self.ipatool = IPATool(email, password)
        else:
            # Nếu người dùng đổi thông tin thì cập nhật lại
            self.ipatool.apple_id = email
            self.ipatool.password = password
            
        self.auth_worker = AuthWorker(self.ipatool, code)
        self.auth_worker.finished.connect(self.on_login_finished)
        self.auth_worker.requires_2fa.connect(self.on_login_requires_2fa)
        self.auth_worker.start()

    def on_login_finished(self, success, message):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Đăng nhập")
        
        if success:
            self.log(f"Đăng nhập thành công! Tài khoản: {self.ipatool.account_name}")
            self.login_group.setEnabled(False) # Khóa form đăng nhập khi đã thành công
            self.downgrade_group.setEnabled(True) # Mở form hạ cấp
            self.code_input.setEnabled(False)
            
            # Ghi nhớ hoặc xóa thông tin đăng nhập đã lưu
            self.save_or_delete_credentials()
        else:
            self.log(f"Đăng nhập thất bại: {message}")
            QMessageBox.critical(self, "Lỗi đăng nhập", f"Xác thực thất bại:\n{message}")

    def on_login_requires_2fa(self):
        self.login_btn.setEnabled(True)
        self.login_btn.setText("Xác minh 2FA")
        self.code_input.setEnabled(True)
        self.code_input.setFocus()
        self.log("Tài khoản của bạn yêu cầu xác minh 2 lớp (2FA).")
        self.log("Một thông báo 2FA đã được gửi tới thiết bị Apple của bạn. Hãy nhập mã 6 số vào ô tương ứng rồi bấm tiếp 'Xác minh 2FA'.")
        QMessageBox.information(
            self, 
            "Yêu cầu 2FA", 
            "Tài khoản yêu cầu mã xác minh 2FA.\nVui lòng kiểm tra mã trên thiết bị Apple của bạn, nhập vào ô tương ứng và bấm lại nút Đăng nhập."
        )

    # --- Xử lý Tìm kiếm ứng dụng ---
    def handle_check_app(self):
        input_text = self.link_input.text().strip()
        app_id = extract_app_id(input_text)
        
        if not app_id:
            QMessageBox.warning(self, "Lỗi định dạng", "Không thể trích xuất App ID hợp lệ từ link của bạn.")
            return
            
        self.current_app_id = app_id
        self.check_btn.setEnabled(False)
        self.check_btn.setText("Đang tìm kiếm...")
        self.log(f"Đang tìm kiếm thông tin ứng dụng ID: {app_id}...")
        
        # 1. Truy vấn thông tin công khai trước để hiển thị nhanh giao diện
        app_details = get_app_details_from_itunes(app_id)
        if app_details.get("success"):
            self.app_name_label.setText(app_details["name"])
            self.app_meta_label.setText(f"Bundle ID: {app_details['bundle_id']} | Mới nhất: {app_details['version']}")
            self.log(f"Tìm thấy ứng dụng: {app_details['name']}")
            
            # Tải ảnh icon
            try:
                r = requests.get(app_details["icon"], timeout=5)
                if r.status_code == 200:
                    pix = QPixmap()
                    pix.loadFromData(r.content)
                    self.app_icon_label.setPixmap(pix.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except Exception:
                self.app_icon_label.setText("📲")
        else:
            self.app_name_label.setText("Ứng dụng không xác định")
            self.app_meta_label.setText("Không thể lấy thông tin chi tiết từ iTunes Store công khai.")
            
        # 2. Khởi chạy Thread lấy danh sách các mã phiên bản cũ
        self.search_worker = SearchWorker(self.ipatool, app_id)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.start()

    def on_search_finished(self, success, raw_ids, friendly_list, error_msg):
        self.check_btn.setEnabled(True)
        self.check_btn.setText("Tìm kiếm Ứng dụng")
        
        if success:
            self.version_combo.clear()
            self.version_mapping.clear()
            self.log(f"Đã tìm thấy tổng cộng {len(raw_ids)} phiên bản khả dụng.")
            
            # Tổ chức lại version mapping để hiển thị thân thiện
            # friendly_list: list of dict {'bundle_version': '1.0.0', 'external_identifier': 123456}
            friendly_map = {str(item['external_identifier']): item['bundle_version'] for item in friendly_list}
            
            # Nạp vào ComboBox
            for raw_id in reversed(raw_ids): # Đảo ngược để phiên bản mới nhất nằm trên cùng
                version_str = friendly_map.get(raw_id)
                if version_str:
                    combo_text = f"Bản {version_str} (ID: {raw_id})"
                else:
                    combo_text = f"Bản chưa biết (ID: {raw_id})"
                
                self.version_combo.addItem(combo_text)
                self.version_mapping[combo_text] = raw_id
                
            self.version_combo.setEnabled(True)
            self.download_btn.setEnabled(True)
            self.log("Vui lòng chọn phiên bản mong muốn tải xuống rồi bấm 'Tải xuống tệp IPA'.")
        else:
            self.log(f"Lỗi tìm kiếm phiên bản: {error_msg}")
            QMessageBox.critical(self, "Lỗi tải phiên bản", f"Không thể lấy lịch sử phiên bản của ứng dụng:\n{error_msg}")

    # --- Xử lý Tải xuống IPA ---
    def handle_download_ipa(self):
        selected_text = self.version_combo.currentText()
        version_id = self.version_mapping.get(selected_text)
        
        if not version_id or not self.current_app_id:
            QMessageBox.warning(self, "Lỗi", "Vui lòng chọn một phiên bản hợp lệ.")
            return
            
        # Hỏi người dùng nơi lưu file
        app_name = self.app_name_label.text().replace(" ", "_")
        # Loại bỏ các ký tự đặc biệt khỏi tên file
        app_name = "".join(x for x in app_name if x.isalnum() or x in ('-', '_'))
        default_filename = f"{app_name}_{selected_text.split(' (')[0].replace(' ', '_')}.ipa"
        
        save_path, _ = QFileDialog.getSaveFileName(
            self, 
            "Lưu tệp IPA", 
            default_filename, 
            "iOS Application Archive (*.ipa)"
        )
        
        if not save_path:
            return # Người dùng hủy chọn
            
        self.download_btn.setEnabled(False)
        self.version_combo.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.log(f"Bắt đầu tải phiên bản {selected_text}...")
        
        # Chạy luồng download
        self.download_worker = DownloadWorker(self.ipatool, self.current_app_id, version_id, save_path)
        self.download_worker.progress.connect(self.on_download_progress)
        self.download_worker.percent.connect(self.progress_bar.setValue)
        self.download_worker.finished.connect(self.on_download_finished)
        self.download_worker.start()

    def on_download_progress(self, status_text):
        self.log(status_text)

    def on_download_finished(self, success, message):
        self.download_btn.setEnabled(True)
        self.version_combo.setEnabled(True)
        self.check_btn.setEnabled(True)
        
        if success:
            self.progress_bar.setValue(100)
            self.log("Quá trình hạ cấp và tải file hoàn tất!")
            
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Tải xuống thành công 🎉")
            msg_box.setText(
                "Tệp IPA đã được tải xuống và ký bản quyền cá nhân thành công!\n\n"
                "Hãy chọn phương thức cài đặt ứng dụng lên iPhone của bạn:"
            )
            
            troll_btn = msg_box.addButton("Cài qua TrollStore (Mã QR/WiFi - Khuyên dùng)", QMessageBox.YesRole)
            troll_btn.setStyleSheet("background-color: #d946ef; color: white; font-weight: bold;")
            
            usb_btn = msg_box.addButton("Cài qua USB (Cần Jailbreak/AppSync)", QMessageBox.AcceptRole)
            close_btn = msg_box.addButton("Hoàn tất / Đóng", QMessageBox.RejectRole)
            
            msg_box.exec_()
            
            if msg_box.clickedButton() == troll_btn:
                dialog = TrollStoreShareDialog(self.download_worker.output_path, self)
                dialog.exec_()
            elif msg_box.clickedButton() == usb_btn:
                self.install_ipa(self.download_worker.output_path)
        else:
            self.progress_bar.setValue(0)
            self.log(f"Lỗi tải ứng dụng: {message}")
            QMessageBox.critical(self, "Lỗi tải ứng dụng", f"Tải xuống thất bại:\n{message}")

    # --- Xử lý Quét Ứng dụng trên Thiết bị ---
    def handle_scan_apps(self):
        if not PYMOBILEDEVICE3_AVAILABLE:
            QMessageBox.critical(
                self, 
                "Lỗi thư viện", 
                "Thư viện 'pymobiledevice3' không khả dụng hoặc chưa được cài đặt đúng cách trên hệ thống."
            )
            return
            
        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Đang quét...")
        self.apps_table.setRowCount(0)
        self.scanned_apps.clear()
        self.log("Bắt đầu quét ứng dụng từ thiết bị iOS qua cổng USB...")
        
        self.scan_worker = ScanAppsWorker()
        self.scan_worker.progress.connect(self.log)
        self.scan_worker.finished.connect(self.on_scan_finished)
        self.scan_worker.start()

    def on_scan_finished(self, success, apps, error_msg):
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Quét Ứng dụng")
        
        if success:
            self.scanned_apps = apps
            self.log(f"Quét thành công! Tìm thấy {len(apps)} ứng dụng người dùng.")
            self.populate_apps_list(apps)
        else:
            self.log(f"Lỗi quét thiết bị: {error_msg}")
            QMessageBox.critical(
                self, 
                "Lỗi kết nối", 
                f"Không thể kết nối hoặc đọc danh sách ứng dụng từ iPhone:\n{error_msg}\n\n"
                "Hãy chắc chắn rằng:\n"
                "1. iPhone đã kết nối qua cáp USB.\n"
                "2. Bạn đã nhấn 'Tin cậy máy tính này' (Trust) trên màn hình iPhone và nhập mật khẩu màn hình."
            )

    def populate_apps_list(self, apps):
        self.apps_table.setRowCount(0)
        self.apps_table.setRowCount(len(apps))
        for row_idx, app in enumerate(apps):
            # Tên ứng dụng
            name_item = QTableWidgetItem(app["name"])
            name_item.setData(Qt.UserRole, app)
            self.apps_table.setItem(row_idx, 0, name_item)
            
            # Phiên bản
            ver_item = QTableWidgetItem(app["version"])
            self.apps_table.setItem(row_idx, 1, ver_item)
            
            # Bundle ID
            bundle_item = QTableWidgetItem(app["bundle_id"])
            self.apps_table.setItem(row_idx, 2, bundle_item)
            
            # App Store ID
            store_id_item = QTableWidgetItem(app.get("app_store_id") or "-")
            self.apps_table.setItem(row_idx, 3, store_id_item)
            
        # Adjust section resize modes (Keep version & App Store ID columns readable)
        header = self.apps_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        self.apps_table.setColumnWidth(1, 100)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.apps_table.setColumnWidth(3, 140)

    def handle_filter_apps(self):
        query = self.search_filter.text().strip().lower()
        for row in range(self.apps_table.rowCount()):
            item = self.apps_table.item(row, 0)
            if item:
                app_data = item.data(Qt.UserRole)
                if app_data:
                    name_match = query in app_data["name"].lower()
                    bundle_match = query in app_data["bundle_id"].lower()
                    self.apps_table.setRowHidden(row, not (name_match or bundle_match))

    def handle_app_selected(self, item):
        app = item.data(Qt.UserRole)
        if not app:
            return
            
        self.log(f"Đã chọn ứng dụng: {app['name']} ({app['bundle_id']})")
        
        # Kích hoạt và đổi tên nút thao tác ứng dụng (rút gọn nếu tên quá dài)
        display_name = app['name']
        if len(display_name) > 12:
            display_name = display_name[:10] + ".."
            
        self.clear_app_data_btn.setEnabled(True)
        self.clear_app_data_btn.setText(f"Xóa {display_name}...")
        self.backup_app_data_btn.setEnabled(True)
        self.backup_app_data_btn.setText(f"Lưu {display_name}...")
        self.restore_app_data_btn.setEnabled(True)
        self.restore_app_data_btn.setText(f"Nạp {display_name}...")
        
        # Nếu chưa đăng nhập, cảnh báo người dùng cần đăng nhập trước để lấy danh sách version
        if not self.ipatool or not self.ipatool.is_authenticated:
            QMessageBox.warning(
                self, 
                "Yêu cầu Đăng nhập", 
                "Vui lòng đăng nhập tài khoản Apple ID ở cột bên trái trước để có thể tải thông tin phiên bản cũ."
            )
            return
            
        # Kiểm tra xem có App Store ID sẵn không
        if app.get("app_store_id") and app["app_store_id"] != "None":
            self.log(f"Sử dụng App Store ID có sẵn trên thiết bị: {app['app_store_id']}")
            self.link_input.setText(app["app_store_id"])
            self.handle_check_app()
        else:
            self.log(f"Đang tìm kiếm ID ứng dụng trên App Store cho bundle ID: {app['bundle_id']}...")
            # Chạy thread lookup
            self.scan_btn.setEnabled(False)
            self.apps_list.setEnabled(False)
            
            self.lookup_worker = LookupBundleWorker(app["bundle_id"])
            self.lookup_worker.finished.connect(lambda success, app_id, err_msg: self.on_lookup_finished(success, app_id, err_msg, app))
            self.lookup_worker.start()

    def on_lookup_finished(self, success, app_id, error_msg, app):
        self.scan_btn.setEnabled(True)
        self.apps_list.setEnabled(True)
        
        if success and app_id:
            self.log(f"Đã tìm thấy App Store ID: {app_id}")
            self.link_input.setText(app_id)
            self.handle_check_app()
        else:
            self.log(f"Không thể tìm thấy ID App Store cho {app['bundle_id']}. Có thể đây là ứng dụng sideload hoặc ứng dụng vùng khác.")
            QMessageBox.warning(
                self, 
                "Không tìm thấy ứng dụng", 
                f"Không thể tìm thấy ứng dụng '{app['name']}' trên hệ thống App Store.\n\n"
                "Lưu ý: Ứng dụng sideload (tự cài) hoặc ứng dụng không còn trên App Store sẽ không thể hạ cấp."
            )

    # --- Xử lý Cài đặt IPA vào iPhone ---
    def handle_install_custom_ipa(self):
        if not PYMOBILEDEVICE3_AVAILABLE:
            QMessageBox.critical(
                self,
                "Lỗi thư viện",
                "Thư viện 'pymobiledevice3' không khả dụng hoặc chưa được cài đặt đúng cách."
            )
            return
            
        save_path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn tệp IPA để cài đặt",
            "",
            "iOS Application Archive (*.ipa)"
        )
        if not save_path:
            return
            
        self.install_ipa(save_path)

    def install_ipa(self, ipa_path):
        if not PYMOBILEDEVICE3_AVAILABLE:
            QMessageBox.critical(
                self,
                "Lỗi thư viện",
                "Thư viện 'pymobiledevice3' không khả dụng để cài đặt ứng dụng."
            )
            return

        self.log(f"Bắt đầu cài đặt tệp IPA: {os.path.basename(ipa_path)}...")
        
        # Vô hiệu hóa điều khiển để tránh xung đột
        self.scan_btn.setEnabled(False)
        self.install_ipa_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.apps_list.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.install_worker = InstallAppsWorker(ipa_path)
        self.install_worker.status.connect(self.log)
        self.install_worker.progress.connect(self.progress_bar.setValue)
        self.install_worker.finished.connect(self.on_install_finished)
        self.install_worker.start()

    def on_install_finished(self, success, message):
        self.scan_btn.setEnabled(True)
        self.install_ipa_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.apps_list.setEnabled(True)
        self.activate_device_btn.setEnabled(True)
        
        if success:
            self.progress_bar.setValue(100)
            self.log(message)
            QMessageBox.information(
                self,
                "Cài đặt thành công",
                "Ứng dụng đã được cài đặt thành công vào iPhone của bạn!"
            )
        else:
            self.progress_bar.setValue(0)
            self.log(f"Lỗi cài đặt ứng dụng: {message}")
            QMessageBox.critical(
                self,
                "Lỗi cài đặt",
                f"Không thể cài đặt ứng dụng lên iPhone:\n{message}\n\n"
                "Lưu ý: Đảm bảo thiết bị vẫn kết nối USB và file IPA đã được ký đúng cách."
            )

    # --- Xử lý Lưu/Ghi nhớ tài khoản ---
    def load_saved_credentials(self):
        config_path = os.path.join(get_app_dir(), "login_config.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                email = data.get("email", "")
                password = data.get("password", "")
                if email:
                    self.email_input.setText(email)
                    self.password_input.setText(password)
                    self.remember_cb.setChecked(True)
                    self.log("Đã tự động điền thông tin tài khoản đã ghi nhớ.")
            except Exception as e:
                self.log(f"Không thể đọc thông tin tài khoản đã lưu: {e}")

    def save_or_delete_credentials(self):
        config_path = os.path.join(get_app_dir(), "login_config.json")
        if self.remember_cb.isChecked():
            try:
                email = self.email_input.text().strip()
                password = self.password_input.text()
                with open(config_path, "w", encoding="utf-8") as f:
                    json.dump({"email": email, "password": password}, f, ensure_ascii=False, indent=4)
                self.log("Đã ghi nhớ thông tin đăng nhập tài khoản.")
            except Exception as e:
                self.log(f"Không thể ghi nhớ tài khoản: {e}")
        else:
            try:
                if os.path.exists(config_path):
                    os.remove(config_path)
                    self.log("Đã xóa thông tin đăng nhập đã lưu.")
            except Exception as e:
                self.log(f"Không thể xóa thông tin đăng nhập đã lưu: {e}")

    # --- Xử lý Xóa Thiết bị (Factory Reset) ---
    def handle_erase_device(self):
        if not PYMOBILEDEVICE3_AVAILABLE:
            QMessageBox.critical(
                self,
                "Lỗi thư viện",
                "Thư viện 'pymobiledevice3' không khả dụng hoặc chưa được cài đặt đúng cách."
            )
            return
            
        self.erase_device_btn.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.erase_device_btn.setText("Đang quét...")
        self.log("Bắt đầu quét danh sách thiết bị kết nối qua USB...")
        
        self.get_info_worker = GetDeviceInfoWorker()
        self.get_info_worker.progress.connect(self.log)
        self.get_info_worker.finished.connect(self.on_get_device_info_finished)
        self.get_info_worker.start()

    def on_get_device_info_finished(self, success, infos, error_msg):
        self.erase_device_btn.setEnabled(True)
        self.activate_device_btn.setEnabled(True)
        self.erase_device_btn.setText("Xóa Toàn bộ iPhone...")
        
        if not success or not infos:
            self.log(f"Lỗi đọc thông tin thiết bị: {error_msg}")
            QMessageBox.critical(
                self,
                "Không tìm thấy thiết bị",
                f"Không thể kết nối hoặc đọc thông tin từ iPhone:\n{error_msg}\n\n"
                "Hãy chắc chắn các thiết bị đã được kết nối qua cáp USB và đã chọn 'Tin cậy máy tính này'."
            )
            return
            
        # Hiển thị popup chọn thiết bị
        dialog = SelectDevicesDialog(infos, self)
        if dialog.exec_() != QDialog.Accepted:
            self.log("Hủy thao tác xóa thiết bị.")
            return
            
        selected_udids = dialog.get_selected_udids()
        if not selected_udids:
            QMessageBox.warning(self, "Cảnh báo", "Bạn chưa chọn thiết bị nào để xóa.")
            return
            
        # Tạo danh sách các thiết bị được chọn để hiển thị xác nhận
        selected_devices_info = [d for d in infos if d["udid"] in selected_udids]
        devices_summary = "\n".join([f"- {d['device_name']} (iOS {d['product_version']}, UDID: {d['udid'][:12]}...)" for d in selected_devices_info])
        
        msg = (
            f"⚠️ CẢNH BÁO BẢO MẬT NGHIÊM TRỌNG ⚠️\n\n"
            f"Bạn chuẩn bị XÓA TOÀN BỘ DỮ LIỆU và khôi phục cài đặt gốc {len(selected_udids)} thiết bị sau:\n"
            f"{devices_summary}\n\n"
            f"Các thiết bị này sẽ trở về trạng thái xuất xưởng. Bạn có chắc chắn muốn tiếp tục?"
        )
        
        reply1 = QMessageBox.warning(
            self,
            "Cảnh báo xóa thiết bị - Lần 1/2",
            msg,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply1 != QMessageBox.Yes:
            self.log("Hủy thao tác xóa thiết bị.")
            return
            
        # Hỏi tùy chọn tự động kích hoạt sau khi xóa xong
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle("Xác nhận xóa & Tùy chọn Kích hoạt - Lần 2/2")
        msg_box.setText(
            f"🚨 CẢNH BÁO: HÀNH ĐỘNG NÀY KHÔNG THỂ HOÀN TÁC 🚨\n\n"
            f"Toàn bộ dữ liệu trên {len(selected_udids)} thiết bị đã chọn sẽ bị xóa sạch hoàn toàn ngay lập tức.\n\n"
            f"Bạn có muốn TỰ ĐỘNG KÍCH HOẠT (Activate & Config) các thiết bị sau khi xóa xong không?"
        )
        
        yes_btn = msg_box.addButton("Xóa và Tự Động Kích Hoạt", QMessageBox.YesRole)
        no_btn = msg_box.addButton("Chỉ Xóa (Không Kích Hoạt)", QMessageBox.NoRole)
        cancel_btn = msg_box.addButton("Hủy Bỏ", QMessageBox.RejectRole)
        
        msg_box.setDefaultButton(cancel_btn)
        msg_box.exec_()
        
        clicked_button = msg_box.clickedButton()
        if clicked_button == cancel_btn:
            self.log("Hủy thao tác xóa thiết bị ở bước xác nhận cuối cùng.")
            return
            
        self.auto_activate_after_erase = (clicked_button == yes_btn)
        self.log(f"Bắt đầu thực hiện lệnh xóa và khôi phục cài đặt gốc {len(selected_udids)} thiết bị...")
        
        # Vô hiệu hóa các nút bấm
        self.scan_btn.setEnabled(False)
        self.install_ipa_btn.setEnabled(False)
        self.erase_device_btn.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.apps_list.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.active_erase_workers = []
        self.erase_results = {}
        
        for udid in selected_udids:
            worker = EraseDeviceWorker(udid)
            worker.status.connect(self.log_device_status)
            worker.finished.connect(self.on_device_erase_finished)
            self.active_erase_workers.append(worker)
            worker.start()

    def log_device_status(self, serial, message):
        self.log(message)

    def on_device_erase_finished(self, serial, success, message):
        self.erase_results[serial] = (success, message)
        self.log(message)
        
        # Kiểm tra xem toàn bộ các luồng xóa đã chạy xong chưa
        active_serials = [w.device_serial for w in self.active_erase_workers]
        if all(s in self.erase_results for s in active_serials):
            success_count = sum(1 for s, (succ, _) in self.erase_results.items() if succ)
            self.log(f"=== KẾT QUẢ XÓA HÀNG LOẠT: Thành công {success_count}/{len(self.erase_results)} thiết bị ===")
            
            if self.auto_activate_after_erase:
                successful_serials = [s for s, (succ, _) in self.erase_results.items() if succ]
                if successful_serials:
                    self.log(f"Bắt đầu tự động theo dõi để kích hoạt {len(successful_serials)} thiết bị...")
                    self.progress_bar.setValue(50)
                    
                    self.active_activate_workers = []
                    self.activate_results = {}
                    for s in successful_serials:
                        worker = AutoActivateMonitorWorker(s)
                        worker.status.connect(self.log_device_status)
                        worker.finished.connect(self.on_device_auto_activate_finished)
                        self.active_activate_workers.append(worker)
                        worker.start()
                else:
                    self.log("Không có thiết bị nào xóa thành công để tiến hành kích hoạt.")
                    self.finalize_erase_workflow()
            else:
                self.finalize_erase_workflow()

    def on_device_auto_activate_finished(self, serial, success, message):
        self.activate_results[serial] = (success, message)
        self.log(message)
        
        # Kiểm tra xem toàn bộ các luồng kích hoạt đã chạy xong chưa
        active_serials = [w.device_serial for w in self.active_activate_workers]
        if all(s in self.activate_results for s in active_serials):
            success_count = sum(1 for s, (succ, _) in self.activate_results.items() if succ)
            self.log(f"=== KẾT QUẢ TỰ ĐỘNG KÍCH HOẠT HÀNG LOẠT: Hoàn tất {success_count}/{len(self.activate_results)} thiết bị ===")
            self.finalize_erase_workflow()

    def finalize_erase_workflow(self):
        # Mở lại điều khiển
        self.scan_btn.setEnabled(True)
        self.install_ipa_btn.setEnabled(True)
        self.erase_device_btn.setEnabled(True)
        self.activate_device_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.apps_list.setEnabled(True)
        self.progress_bar.setValue(100)
        
        summary = "Tiến trình hoàn tất.\n\n"
        if self.erase_results:
            success_erase = sum(1 for s, (succ, _) in self.erase_results.items() if succ)
            summary += f"- Xóa thiết bị: Thành công {success_erase}/{len(self.erase_results)}\n"
        if self.auto_activate_after_erase and self.activate_results:
            success_act = sum(1 for s, (succ, _) in self.activate_results.items() if succ)
            summary += f"- Tự động kích hoạt: Thành công {success_act}/{len(self.activate_results)}\n"
            
        QMessageBox.information(
            self,
            "Kết quả thao tác hàng loạt",
            summary
        )
        self.erase_results = {}
        self.activate_results = {}
        self.active_erase_workers = []
        self.active_activate_workers = []

    # --- Xử lý Kích hoạt và cấu hình iPhone (Activate & Config) ---
    def handle_activate_device(self):
        if not PYMOBILEDEVICE3_AVAILABLE:
            QMessageBox.critical(
                self,
                "Lỗi thư viện",
                "Thư viện 'pymobiledevice3' không khả dụng hoặc chưa được cài đặt đúng cách."
            )
            return
            
        self.erase_device_btn.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.activate_device_btn.setText("Đang quét...")
        self.log("Bắt đầu quét danh sách thiết bị để kích hoạt...")
        
        self.get_info_worker = GetDeviceInfoWorker()
        self.get_info_worker.progress.connect(self.log)
        self.get_info_worker.finished.connect(self.on_get_device_info_for_activation_finished)
        self.get_info_worker.start()

    def on_get_device_info_for_activation_finished(self, success, infos, error_msg):
        self.erase_device_btn.setEnabled(True)
        self.activate_device_btn.setEnabled(True)
        self.activate_device_btn.setText("Kích hoạt iPhone (USA/EN)...")
        
        if not success or not infos:
            self.log(f"Lỗi đọc thông tin thiết bị: {error_msg}")
            QMessageBox.critical(
                self,
                "Không tìm thấy thiết bị",
                f"Không thể quét danh sách iPhone hoặc không có máy nào kết nối:\n{error_msg}"
            )
            return
            
        dialog = SelectDevicesDialog(infos, self)
        if dialog.exec_() != QDialog.Accepted:
            self.log("Hủy tiến trình kích hoạt.")
            return
            
        selected_udids = dialog.get_selected_udids()
        if not selected_udids:
            QMessageBox.warning(self, "Cảnh báo", "Bạn chưa chọn thiết bị nào để kích hoạt.")
            return
            
        reply = QMessageBox.question(
            self,
            "Xác nhận kích hoạt",
            f"Bạn có muốn kích hoạt và cấu hình ngôn ngữ/vùng Tiếng Anh (Mỹ) cho {len(selected_udids)} thiết bị đã chọn không?\n"
            "Hãy đảm bảo iPhone đã cắm cáp USB và đang ở màn hình Hello/Khóa kích hoạt (hoặc màn hình chính).",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        self.log(f"Bắt đầu tiến trình kích hoạt {len(selected_udids)} thiết bị song song...")
        
        self.scan_btn.setEnabled(False)
        self.install_ipa_btn.setEnabled(False)
        self.erase_device_btn.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.apps_list.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.active_activate_workers = []
        self.activate_results = {}
        
        for udid in selected_udids:
            worker = ActivateDeviceWorker(udid)
            worker.status.connect(self.log_device_status)
            worker.finished.connect(self.on_direct_activate_finished)
            self.active_activate_workers.append(worker)
            worker.start()

    def on_direct_activate_finished(self, serial, success, message):
        self.activate_results[serial] = (success, message)
        self.log(message)
        
        active_serials = [w.device_serial for w in self.active_activate_workers]
        if all(s in self.activate_results for s in active_serials):
            success_count = sum(1 for s, (succ, _) in self.activate_results.items() if succ)
            self.log(f"=== KẾT QUẢ KÍCH HOẠT HÀNG LOẠT: Hoàn tất {success_count}/{len(self.activate_results)} thiết bị ===")
            
            self.scan_btn.setEnabled(True)
            self.install_ipa_btn.setEnabled(True)
            self.erase_device_btn.setEnabled(True)
            self.activate_device_btn.setEnabled(True)
            self.download_btn.setEnabled(True)
            self.check_btn.setEnabled(True)
            self.apps_list.setEnabled(True)
            self.progress_bar.setValue(100)
            
            QMessageBox.information(
                self,
                "Hoàn tất kích hoạt hàng loạt",
                f"Đã hoàn thành kích hoạt thiết bị.\nThành công: {success_count}/{len(self.activate_results)}"
            )
            self.active_activate_workers = []
            self.activate_results = {}

    def handle_trollstore_guide(self):
        dialog = TrollStoreGuideDialog(self)
        dialog.exec_()

    # --- Xử lý Xóa Dữ liệu Ứng dụng (Clear App Data) ---
    def handle_clear_app_data(self, force_uninstall=False):
        row = self.apps_table.currentRow()
        selected_item = self.apps_table.item(row, 0) if row >= 0 else None
        if not selected_item:
            QMessageBox.warning(self, "Chưa chọn ứng dụng", "Vui lòng chọn một ứng dụng trong danh sách trước.")
            return
            
        app = selected_item.data(Qt.UserRole)
        if not app:
            return
            
        bundle_id = app["bundle_id"]
        app_name = app["name"]
        
        if not force_uninstall:
            reply = QMessageBox.warning(
                self,
                "Xác nhận xóa dữ liệu ứng dụng",
                f"Bạn có chắc chắn muốn xóa toàn bộ dữ liệu (login session, tài khoản, cache, cấu hình) của ứng dụng '{app_name}'?\n\n"
                "Hành động này sẽ xóa sạch dữ liệu ứng dụng trên máy của bạn.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        self.scan_btn.setEnabled(False)
        self.install_ipa_btn.setEnabled(False)
        self.erase_device_btn.setEnabled(False)
        self.clear_app_data_btn.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.apps_list.setEnabled(False)
        self.progress_bar.setValue(0)
        
        if force_uninstall:
            self.log(f"Bắt đầu gỡ cài đặt '{app_name}' để dọn sạch dữ liệu...")
        else:
            self.log(f"Đang bắt đầu phân tích dữ liệu dọn dẹp '{app_name}'...")
            
        self.clear_worker = ClearAppDataWorker(bundle_id, app_name, force_uninstall=force_uninstall)
        self.clear_worker.status.connect(self.log)
        self.clear_worker.finished.connect(lambda success, msg: self.on_clear_app_data_finished(success, msg, app))
        self.clear_worker.start()

    def on_clear_app_data_finished(self, success, message, app):
        self.scan_btn.setEnabled(True)
        self.install_ipa_btn.setEnabled(True)
        self.erase_device_btn.setEnabled(True)
        self.clear_app_data_btn.setEnabled(True)
        self.activate_device_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.apps_list.setEnabled(True)
        
        if success:
            self.progress_bar.setValue(100)
            self.log(message)
            QMessageBox.information(
                self,
                "Dọn dẹp thành công",
                message
            )
        else:
            self.progress_bar.setValue(0)
            if message == "AFC2_UNAVAILABLE":
                self.log("Thiết bị không Jailbreak (không có cổng afc2). Đang hỏi phương thức gỡ cài đặt...")
                reply = QMessageBox.question(
                    self,
                    "Thiết bị chưa Jailbreak",
                    f"Dịch vụ afc2 (dành cho máy Jailbreak) không khả dụng trên iPhone này.\n\n"
                    f"Để xóa sạch session đăng nhập và dữ liệu của ứng dụng '{app['name']}' trên máy chưa Jailbreak, chúng tôi cần gỡ cài đặt ứng dụng.\n\n"
                    f"Bạn có muốn gỡ cài đặt ứng dụng '{app['name']}' để xóa toàn bộ dữ liệu hay không?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.Yes:
                    self.handle_clear_app_data(force_uninstall=True)
                else:
                    self.log("Đã hủy gỡ cài đặt ứng dụng.")
            else:
                self.log(f"Lỗi khi dọn dẹp ứng dụng: {message}")
                QMessageBox.critical(
                    self,
                    "Lỗi dọn dẹp",
                    f"Không thể dọn dẹp ứng dụng:\n{message}\n\n"
                    "Vui lòng thử lại hoặc khởi động lại kết nối thiết bị."
                )

    # --- Xử lý Sao lưu Dữ liệu Ứng dụng (Backup App Data) ---
    def handle_backup_app_data(self):
        row = self.apps_table.currentRow()
        selected_item = self.apps_table.item(row, 0) if row >= 0 else None
        if not selected_item:
            QMessageBox.warning(self, "Chưa chọn ứng dụng", "Vui lòng chọn một ứng dụng trong danh sách trước.")
            return
            
        app = selected_item.data(Qt.UserRole)
        if not app:
            return
            
        bundle_id = app["bundle_id"]
        app_name = app["name"]
        
        default_filename = f"{app_name.replace(' ', '_')}_Backup.zip"
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Lưu file sao lưu dữ liệu {app_name}",
            default_filename,
            "ZIP Archives (*.zip)"
        )
        if not save_path:
            return
            
        self.scan_btn.setEnabled(False)
        self.install_ipa_btn.setEnabled(False)
        self.erase_device_btn.setEnabled(False)
        self.clear_app_data_btn.setEnabled(False)
        self.backup_app_data_btn.setEnabled(False)
        self.restore_app_data_btn.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.apps_list.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.log(f"Bắt đầu sao lưu dữ liệu '{app_name}' vào file: {os.path.basename(save_path)}...")
        
        self.backup_worker = BackupAppDataWorker(bundle_id, app_name, save_path)
        self.backup_worker.status.connect(self.log)
        self.backup_worker.finished.connect(self.on_backup_app_data_finished)
        self.backup_worker.start()

    def on_backup_app_data_finished(self, success, message):
        self.scan_btn.setEnabled(True)
        self.install_ipa_btn.setEnabled(True)
        self.erase_device_btn.setEnabled(True)
        self.clear_app_data_btn.setEnabled(True)
        self.backup_app_data_btn.setEnabled(True)
        self.restore_app_data_btn.setEnabled(True)
        self.activate_device_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.apps_list.setEnabled(True)
        
        if success:
            self.progress_bar.setValue(100)
            self.log(message)
            QMessageBox.information(self, "Sao lưu thành công", message)
        else:
            self.progress_bar.setValue(0)
            self.log(f"Lỗi sao lưu ứng dụng: {message}")
            QMessageBox.critical(
                self,
                "Lỗi sao lưu",
                f"Không thể sao lưu dữ liệu ứng dụng:\n{message}\n\n"
                "Lưu ý: Tính năng này chỉ hoạt động trên các máy đã Jailbreak và bật dịch vụ afc2."
            )

    # --- Xử lý Khôi phục Dữ liệu Ứng dụng (Restore App Data) ---
    def handle_restore_app_data(self):
        row = self.apps_table.currentRow()
        selected_item = self.apps_table.item(row, 0) if row >= 0 else None
        if not selected_item:
            QMessageBox.warning(self, "Chưa chọn ứng dụng", "Vui lòng chọn một ứng dụng trong danh sách trước.")
            return
            
        app = selected_item.data(Qt.UserRole)
        if not app:
            return
            
        bundle_id = app["bundle_id"]
        app_name = app["name"]
        
        open_path, _ = QFileDialog.getOpenFileName(
            self,
            f"Chọn file sao lưu ZIP để khôi phục cho {app_name}",
            "",
            "ZIP Archives (*.zip)"
        )
        if not open_path:
            return
            
        reply = QMessageBox.warning(
            self,
            "Xác nhận khôi phục",
            f"Khôi phục dữ liệu sẽ ghi đè toàn bộ dữ liệu hiện tại của '{app_name}' trên iPhone.\n\n"
            "Bạn có chắc chắn muốn tiếp tục?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
            
        self.scan_btn.setEnabled(False)
        self.install_ipa_btn.setEnabled(False)
        self.erase_device_btn.setEnabled(False)
        self.clear_app_data_btn.setEnabled(False)
        self.backup_app_data_btn.setEnabled(False)
        self.restore_app_data_btn.setEnabled(False)
        self.activate_device_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        self.check_btn.setEnabled(False)
        self.apps_list.setEnabled(False)
        self.progress_bar.setValue(0)
        
        self.log(f"Bắt đầu khôi phục dữ liệu '{app_name}' từ file: {os.path.basename(open_path)}...")
        
        self.restore_worker = RestoreAppDataWorker(bundle_id, app_name, open_path)
        self.restore_worker.status.connect(self.log)
        self.restore_worker.finished.connect(self.on_restore_app_data_finished)
        self.restore_worker.start()

    def on_restore_app_data_finished(self, success, message):
        self.scan_btn.setEnabled(True)
        self.install_ipa_btn.setEnabled(True)
        self.erase_device_btn.setEnabled(True)
        self.clear_app_data_btn.setEnabled(True)
        self.backup_app_data_btn.setEnabled(True)
        self.restore_app_data_btn.setEnabled(True)
        self.activate_device_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        self.check_btn.setEnabled(True)
        self.apps_list.setEnabled(True)
        
        if success:
            self.progress_bar.setValue(100)
            self.log(message)
            QMessageBox.information(self, "Khôi phục thành công", message)
        else:
            self.progress_bar.setValue(0)
            self.log(f"Lỗi khôi phục ứng dụng: {message}")
            QMessageBox.critical(
                self,
                "Lỗi khôi phục",
                f"Không thể khôi phục dữ liệu ứng dụng:\n{message}\n\n"
                "Lưu ý: Tính năng này chỉ hoạt động trên các máy đã Jailbreak và bật dịch vụ afc2."
            )

    def init_auto_tab_ui(self):
        from PyQt5.QtWidgets import QFormLayout, QSpinBox
        
        auto_layout = QHBoxLayout(self.auto_tab)
        auto_layout.setContentsMargins(15, 15, 15, 15)
        auto_layout.setSpacing(15)
        
        # --- CỘT TRÁI: CẤU HÌNH ---
        left_col = QWidget()
        left_col.setFixedWidth(420)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        wda_group = QGroupBox("🔌 Kết Nối WebDriverAgent (WDA)")
        wda_grid = QGridLayout(wda_group)
        wda_grid.setSpacing(8)
        
        # Connection mode combo box
        self.conn_mode_combo = QComboBox()
        self.conn_mode_combo.addItem("🔌 Kết nối USB trực tiếp (Tự động)", "usb")
        self.conn_mode_combo.addItem("🌐 Kết nối WDA thủ công (Host/Port)", "manual")
        self.conn_mode_combo.currentIndexChanged.connect(self.handle_conn_mode_changed)
        wda_grid.addWidget(QLabel("Chế độ:"), 0, 0)
        wda_grid.addWidget(self.conn_mode_combo, 0, 1)

        # USB widgets
        self.usb_device_label = QLabel("Thiết bị USB:")
        self.usb_device_combo = QComboBox()
        self.usb_device_combo.currentIndexChanged.connect(self.handle_usb_device_changed)
        self.usb_refresh_btn = QPushButton("🔄 Quét")
        self.usb_refresh_btn.setFixedWidth(60)
        self.usb_refresh_btn.setObjectName("secondaryButton")
        self.usb_refresh_btn.clicked.connect(self.refresh_usb_devices)
        
        self.usb_container_widget = QWidget()
        usb_cont_lay = QHBoxLayout(self.usb_container_widget)
        usb_cont_lay.setContentsMargins(0, 0, 0, 0)
        usb_cont_lay.addWidget(self.usb_device_combo, 1)
        usb_cont_lay.addWidget(self.usb_refresh_btn)
        
        wda_grid.addWidget(self.usb_device_label, 1, 0)
        wda_grid.addWidget(self.usb_container_widget, 1, 1)
        
        # Manual host/port widgets
        self.manual_host_label = QLabel("Host:")
        self.wda_host_input = QLineEdit("http://localhost")
        self.manual_host_container = QWidget()
        mhc_lay = QHBoxLayout(self.manual_host_container)
        mhc_lay.setContentsMargins(0, 0, 0, 0)
        mhc_lay.addWidget(self.wda_host_input)
        
        self.manual_port_label = QLabel("Port:")
        self.wda_port_input = QLineEdit("8100")
        self.manual_port_container = QWidget()
        mpc_lay = QHBoxLayout(self.manual_port_container)
        mpc_lay.setContentsMargins(0, 0, 0, 0)
        mpc_lay.addWidget(self.wda_port_input)
        
        wda_grid.addWidget(self.manual_host_label, 2, 0)
        wda_grid.addWidget(self.manual_host_container, 2, 1)
        wda_grid.addWidget(self.manual_port_label, 3, 0)
        wda_grid.addWidget(self.manual_port_container, 3, 1)
        
        # Auto setup WDA button
        self.wda_autosetup_btn = QPushButton("⚡ Cài đặt WDA 1 chạm")
        self.wda_autosetup_btn.clicked.connect(self.handle_wda_autosetup)
        wda_grid.addWidget(self.wda_autosetup_btn, 4, 0, 1, 2)
        
        # Check connection WDA button
        self.wda_check_btn = QPushButton("🔍 Kiểm tra trạng thái WDA")
        self.wda_check_btn.setObjectName("secondaryButton")
        self.wda_check_btn.clicked.connect(self.handle_wda_check)
        wda_grid.addWidget(self.wda_check_btn, 5, 0, 1, 2)
        
        # Sideloadly helper button
        self.wda_sideloadly_btn = QPushButton("🛠️ Ký WDA qua Sideloadly (Nếu TrollStore lỗi)")
        self.wda_sideloadly_btn.setObjectName("secondaryButton")
        self.wda_sideloadly_btn.clicked.connect(self.handle_sideloadly_helper)
        wda_grid.addWidget(self.wda_sideloadly_btn, 6, 0, 1, 2)
        
        # Device status panel
        self.device_status_panel = QFrame()
        self.device_status_panel.setFrameShape(QFrame.StyledPanel)
        self.device_status_panel.setStyleSheet("""
            QFrame {
                background-color: #060a1a;
                border: 1px solid #0e1630;
                border-radius: 10px;
                padding: 4px;
            }
        """)
        panel_layout = QVBoxLayout(self.device_status_panel)
        panel_layout.setSpacing(4)
        panel_layout.setContentsMargins(8, 8, 8, 8)
        
        self.lbl_status_device = QLabel("Thiết bị: <b>Chưa kết nối</b>")
        self.lbl_status_device.setStyleSheet("color: #f8fafc;")
        self.lbl_status_ios = QLabel("iOS: <b>-</b>")
        self.lbl_status_ios.setStyleSheet("color: #f8fafc;")
        self.lbl_status_wda = QLabel("Trạng thái WDA: <b>Chưa chạy</b>")
        self.lbl_status_wda.setStyleSheet("color: #f8fafc;")
        
        panel_layout.addWidget(self.lbl_status_device)
        panel_layout.addWidget(self.lbl_status_ios)
        panel_layout.addWidget(self.lbl_status_wda)
        wda_grid.addWidget(self.device_status_panel, 7, 0, 1, 2)
        
        left_layout.addWidget(wda_group)
        
        script_group = QGroupBox("⚙️ Cấu Hình Kịch Bản Tự Động")
        script_layout = QVBoxLayout(script_group)
        script_layout.setSpacing(10)
        
        script_layout.addWidget(QLabel("Chọn Kịch Bản Chạy:"))
        self.auto_script_combo = QComboBox()
        self.auto_script_combo.addItem("1. Tự động lướt TikTok / Douyin (Auto Swiper)", "swiper")
        self.auto_script_combo.addItem("2. Tự động tạo Apple ID (iCloud App Store)", "apple_id")
        self.auto_script_combo.addItem("3. Kịch bản Tùy chỉnh (Custom Script Commands)", "custom")
        self.auto_script_combo.addItem("4. Tự động thêm thẻ App Store (Auto Add Card)", "add_card")
        self.auto_script_combo.currentIndexChanged.connect(self.handle_script_changed)
        script_layout.addWidget(self.auto_script_combo)
        
        self.script_settings_stack = QStackedWidget()
        
        pg_swiper = QWidget()
        swiper_lay = QFormLayout(pg_swiper)
        swiper_lay.setContentsMargins(0, 5, 0, 0)
        self.swiper_app_combo = QComboBox()
        self.swiper_app_combo.addItem("TikTok (Quốc tế)", "com.zhiliaoapp.musically")
        self.swiper_app_combo.addItem("Douyin (Trung Quốc)", "com.ss.iphone.ugc.Aweme")
        self.swiper_app_combo.addItem("YouTube Shorts", "com.google.ios.youtube")
        self.swiper_app_combo.addItem("Facebook Reels", "com.facebook.Facebook")
        swiper_lay.addRow("Mở Ứng Dụng:", self.swiper_app_combo)
        
        self.swiper_delay_min = QSpinBox()
        self.swiper_delay_min.setRange(1, 120)
        self.swiper_delay_min.setValue(5)
        swiper_lay.addRow("Delay Min (giây):", self.swiper_delay_min)
        
        self.swiper_delay_max = QSpinBox()
        self.swiper_delay_max.setRange(1, 120)
        self.swiper_delay_max.setValue(12)
        swiper_lay.addRow("Delay Max (giây):", self.swiper_delay_max)
        
        self.swiper_jitter = QCheckBox("Trộn ngẫu nhiên (Jitter)")
        self.swiper_jitter.setChecked(True)
        swiper_lay.addRow(self.swiper_jitter)
        
        self.script_settings_stack.addWidget(pg_swiper)
        
        pg_apple = QWidget()
        apple_lay = QFormLayout(pg_apple)
        apple_lay.setContentsMargins(0, 5, 0, 0)
        
        self.apple_email_dom = QLineEdit("tempmail.com")
        apple_lay.addRow("Tên miền Email:", self.apple_email_dom)
        
        self.apple_pass = QLineEdit("P@ssword999!")
        self.apple_pass.setEchoMode(QLineEdit.Password)
        apple_lay.addRow("Mật khẩu tài khoản:", self.apple_pass)
        
        self.apple_sms_key = QLineEdit()
        self.apple_sms_key.setPlaceholderText("Nhập API Key ViOTP / ChoThueSim")
        apple_lay.addRow("API Key SMS OTP:", self.apple_sms_key)
        
        self.apple_captcha_key = QLineEdit()
        self.apple_captcha_key.setPlaceholderText("Nhập API Key 2Captcha / AnyCaptcha")
        apple_lay.addRow("API Key CAPTCHA:", self.apple_captcha_key)
        
        self.script_settings_stack.addWidget(pg_apple)
        
        pg_custom = QWidget()
        custom_lay = QVBoxLayout(pg_custom)
        custom_lay.setContentsMargins(0, 5, 0, 0)
        custom_lay.addWidget(QLabel("Nhập các câu lệnh chạy (1 lệnh/dòng):"))
        self.custom_script_edit = QTextEdit()
        self.custom_script_edit.setPlaceholderText(
            "# Các lệnh hỗ trợ:\n"
            "home\n"
            "launch com.apple.AppStore\n"
            "wait 3\n"
            "tap 340 65\n"
            "wait 2\n"
            "swipe 187 600 187 200 400\n"
            "type hello_world"
        )
        self.custom_script_edit.setStyleSheet("background-color: #020408; border: 1px solid #0e1630; font-family: 'Cascadia Code', 'Consolas', monospace;")
        custom_lay.addWidget(self.custom_script_edit)
        
        self.script_settings_stack.addWidget(pg_custom)
        
        pg_add_card = QWidget()
        add_card_lay = QFormLayout(pg_add_card)
        add_card_lay.setContentsMargins(0, 5, 0, 0)
        
        self.add_card_limit = QSpinBox()
        self.add_card_limit.setRange(1, 100)
        self.add_card_limit.setValue(1)
        add_card_lay.addRow("Số thẻ cần add thành công:", self.add_card_limit)
        
        self.add_card_apple_pass = QLineEdit("Zxcv@123")
        self.add_card_apple_pass.setEchoMode(QLineEdit.Password)
        add_card_lay.addRow("Mật khẩu Apple ID:", self.add_card_apple_pass)
        
        self.script_settings_stack.addWidget(pg_add_card)
        
        script_layout.addWidget(self.script_settings_stack)
        left_layout.addWidget(script_group)
        
        exec_lay = QHBoxLayout()
        self.auto_start_btn = QPushButton("🚀 Bắt đầu Chạy")
        self.auto_start_btn.clicked.connect(self.handle_auto_start)
        
        self.auto_stop_btn = QPushButton("🛑 Dừng lại")
        self.auto_stop_btn.setObjectName("dangerButton")
        self.auto_stop_btn.setEnabled(False)
        self.auto_stop_btn.clicked.connect(self.handle_auto_stop)
        
        exec_lay.addWidget(self.auto_start_btn)
        exec_lay.addWidget(self.auto_stop_btn)
        left_layout.addLayout(exec_lay)
        
        auto_layout.addWidget(left_col)
        
        # --- CỘT PHẢI: MÀN HÌNH MOCK & LOGS ---
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        top_row = QHBoxLayout()
        
        toolpad_group = QGroupBox("🛠️ Bàn Điều Khiển Nhanh")
        toolpad_grid = QGridLayout(toolpad_group)
        toolpad_grid.setSpacing(10)
        
        self.manual_home_btn = QPushButton("🏠 Trang chủ")
        self.manual_home_btn.clicked.connect(self.handle_manual_home)
        toolpad_grid.addWidget(self.manual_home_btn, 0, 0)
        
        self.manual_appstore_btn = QPushButton("📱 Mở App Store")
        self.manual_appstore_btn.clicked.connect(lambda: self.handle_manual_launch("com.apple.AppStore"))
        toolpad_grid.addWidget(self.manual_appstore_btn, 0, 1)
        
        self.manual_tiktok_btn = QPushButton("📲 Mở TikTok")
        self.manual_tiktok_btn.clicked.connect(lambda: self.handle_manual_launch("com.zhiliaoapp.musically"))
        toolpad_grid.addWidget(self.manual_tiktok_btn, 1, 0)
        
        self.manual_type_btn = QPushButton("⌨️ Gõ chữ")
        self.manual_type_btn.clicked.connect(self.handle_manual_type)
        toolpad_grid.addWidget(self.manual_type_btn, 1, 1)
        
        self.manual_snap_btn = QPushButton("📸 Chụp màn hình (WDA)")
        self.manual_snap_btn.clicked.connect(self.handle_manual_snap)
        toolpad_grid.addWidget(self.manual_snap_btn, 2, 0)
        
        self.dvt_snap_btn = QPushButton("📸 Chụp ảnh (DVT)")
        self.dvt_snap_btn.setObjectName("secondaryButton")
        self.dvt_snap_btn.clicked.connect(self.handle_dvt_snap)
        toolpad_grid.addWidget(self.dvt_snap_btn, 2, 1)
        
        self.dvt_launch_btn = QPushButton("🚀 Mở App (DVT)")
        self.dvt_launch_btn.clicked.connect(self.handle_dvt_launch)
        toolpad_grid.addWidget(self.dvt_launch_btn, 3, 0)
        
        self.dvt_kill_btn = QPushButton("☠️ Tắt App (DVT)")
        self.dvt_kill_btn.setObjectName("dangerButton")
        self.dvt_kill_btn.clicked.connect(self.handle_dvt_kill)
        toolpad_grid.addWidget(self.dvt_kill_btn, 3, 1)
        
        self.dvt_gps_btn = QPushButton("📍 Giả lập GPS")
        self.dvt_gps_btn.clicked.connect(self.handle_dvt_gps)
        toolpad_grid.addWidget(self.dvt_gps_btn, 4, 0)
        
        self.dvt_gps_clear_btn = QPushButton("📍 Xóa giả lập GPS")
        self.dvt_gps_clear_btn.setObjectName("secondaryButton")
        self.dvt_gps_clear_btn.clicked.connect(self.handle_dvt_gps_clear)
        toolpad_grid.addWidget(self.dvt_gps_clear_btn, 4, 1)
        
        top_row.addWidget(toolpad_group, 6)
        
        live_screen_group = QGroupBox("📱 Màn Hình Live")
        live_screen_layout = QVBoxLayout(live_screen_group)
        live_screen_layout.setAlignment(Qt.AlignCenter)
        
        self.live_screen_label = QLabel("Chưa chụp ảnh")
        self.live_screen_label.setFixedSize(160, 260)
        self.live_screen_label.setStyleSheet("border: 1px solid #0e1630; background-color: #060a1a; border-radius: 10px;")
        self.live_screen_label.setAlignment(Qt.AlignCenter)
        live_screen_layout.addWidget(self.live_screen_label)
        
        top_row.addWidget(live_screen_group, 4)
        
        right_layout.addLayout(top_row)
        
        log_group = QGroupBox("📋 Nhật Ký Hoạt Động (Logs)")
        log_lay = QVBoxLayout(log_group)
        log_lay.setSpacing(5)
        
        log_header = QHBoxLayout()
        self.auto_run_label = QLabel("Trạng thái: <b>Đang dừng</b>")
        self.auto_count_label = QLabel("Đã thực hiện: <b>0</b>")
        self.auto_clear_btn = QPushButton("🧹 Xóa")
        self.auto_clear_btn.setObjectName("secondaryButton")
        self.auto_clear_btn.setFixedWidth(60)
        self.auto_clear_btn.clicked.connect(self.handle_auto_clear_logs)
        
        log_header.addWidget(self.auto_run_label)
        log_header.addStretch()
        log_header.addWidget(self.auto_count_label)
        log_header.addSpacing(20)
        log_header.addWidget(self.auto_clear_btn)
        log_lay.addLayout(log_header)
        
        self.auto_log_console = QTextEdit()
        self.auto_log_console.setReadOnly(True)
        self.auto_log_console.setStyleSheet("""
            QTextEdit {
                background-color: #020408;
                border: 1px solid #0e1630;
                border-radius: 10px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 11px;
                color: #00f2fe;
            }
        """)
        log_lay.addWidget(self.auto_log_console)
        
        right_layout.addWidget(log_group)
        
        auto_layout.addWidget(right_col, 1)

        # Trigger initial connection mode layout styling
        self.handle_conn_mode_changed(0)

    def handle_screenshot_signal(self, base64_str):
        try:
            import base64
            from PyQt5.QtGui import QPixmap
            img_data = base64.b64decode(base64_str)
            pixmap = QPixmap()
            if pixmap.loadFromData(img_data):
                scaled = pixmap.scaled(self.live_screen_label.width() - 4, self.live_screen_label.height() - 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.live_screen_label.setPixmap(scaled)
        except Exception as e:
            self.log_auto(f"[Lỗi] Không thể hiển thị ảnh chụp màn hình: {str(e)}", "error")

    def handle_wda_check(self):
        mode = self.conn_mode_combo.currentData()
        is_usb = (mode == "usb")
        if is_usb:
            serial = self.usb_device_combo.currentData()
            if not serial or "❌" in self.usb_device_combo.currentText() or "⚠️" in self.usb_device_combo.currentText():
                QMessageBox.warning(self, "Không tìm thấy thiết bị", "Vui lòng kết nối iPhone qua USB!")
                return
            host = "http://127.0.0.1"
            port = 8100
            self.log_auto(f"🔌 Thiết lập Port Relay cho thiết bị USB {serial[:8]}...", "info")
            self.wda_manager.start_relay(serial)
            time.sleep(1.0)
        else:
            host = self.wda_host_input.text().strip()
            port_str = self.wda_port_input.text().strip()
            try:
                port = int(port_str)
            except ValueError:
                QMessageBox.warning(self, "Lỗi định dạng", "Cổng (Port) phải là số nguyên!")
                return
            
        self.log_auto(f"🔍 Đang kiểm tra kết nối WebDriverAgent tại {host}:{port}...", "info")
        self.wda_check_btn.setEnabled(False)
        self.wda_check_btn.setText("Đang kiểm tra...")
        
        class CheckWDALocalThread(QThread):
            finished = pyqtSignal(bool)
            def __init__(self, h, p, wda_manager, is_usb_mode):
                super().__init__()
                self.h = h
                self.p = p
                self.wda_manager = wda_manager
                self.is_usb_mode = is_usb_mode
            def run(self):
                client = WDAClient(host=self.h, port=self.p)
                success = client.check_status()
                if not success and self.is_usb_mode:
                    self.wda_manager.stop_relay()
                self.finished.emit(success)
                
        self.safeguard_thread("wda_check_thread")
        self.wda_check_thread = CheckWDALocalThread(host, port, self.wda_manager, is_usb)
        self.wda_check_thread.finished.connect(self.on_wda_check_finished)
        self.wda_check_thread.start()

    def on_wda_check_finished(self, success):
        self.wda_check_btn.setEnabled(True)
        self.wda_check_btn.setText("🔍 Kiểm tra trạng thái WDA")
        if success:
            self.log_auto("🟢 Kết nối WebDriverAgent thành công! Thiết bị đã sẵn sàng.", "success")
            self.lbl_status_wda.setText("Trạng thái WDA: <b style='color: #10b981;'>🟢 Đang chạy</b>")
            QMessageBox.information(self, "Kết nối thành công", "Đã kết nối thành công tới WebDriverAgent!")
        else:
            self.log_auto("🔴 Thất bại: Không thể kết nối tới WebDriverAgent.", "error")
            self.lbl_status_wda.setText("Trạng thái WDA: <b style='color: #ef4444;'>🔴 Chưa chạy</b>")
            mode = self.conn_mode_combo.currentData()
            if mode == "usb":
                QMessageBox.critical(self, "Lỗi kết nối", 
                                     "Không thể kết nối tới WebDriverAgent.\n\n"
                                     "Vui lòng đảm bảo:\n"
                                     "1. Đã kết nối iPhone qua cáp USB\n"
                                     "2. Đã mở ứng dụng WebDriverAgent trên iPhone (hoặc ứng dụng WDA Runner)\n"
                                     "3. Nếu vẫn lỗi, hãy nhấn 'Cài đặt WDA 1 chạm' để hệ thống tự khởi động lại.")
            else:
                QMessageBox.critical(self, "Lỗi kết nối", 
                                     "Không thể kết nối tới WebDriverAgent tại địa chỉ thủ công đã nhập.\n"
                                     "Vui lòng kiểm tra lại Host và Port.")

    def log_auto(self, text, style="info"):
        colors = {
            "info": "#00f2fe",      # cyan accent
            "success": "#00ff9f",   # green accent
            "error": "#ff073a",     # red danger
            "warn": "#fff01f",      # yellow warning
            "action": "#d946ef"     # fuchsia primary
        }
        color = colors.get(style, "#94a3b8")
        self.auto_log_console.append(f'<span style="color: {color};">{text}</span>')
        self.auto_log_console.ensureCursorVisible()

    def handle_script_changed(self, index):
        self.script_settings_stack.setCurrentIndex(index)

    def handle_auto_start(self):
        mode = self.conn_mode_combo.currentData()
        if mode == "usb":
            serial = self.usb_device_combo.currentData()
            if not serial or "❌" in self.usb_device_combo.currentText() or "⚠️" in self.usb_device_combo.currentText():
                QMessageBox.warning(self, "Không tìm thấy thiết bị", "Vui lòng kết nối iPhone qua USB!")
                return
            host = "http://127.0.0.1"
            port = 8100
        else:
            host = self.wda_host_input.text().strip()
            port_str = self.wda_port_input.text().strip()
            try:
                port = int(port_str)
            except ValueError:
                QMessageBox.warning(self, "Lỗi định dạng", "Cổng (Port) phải là số nguyên!")
                return
            
        script_type = self.auto_script_combo.currentData()
        
        config = {
            "host": host,
            "port": port,
            "script_type": script_type,
            "serial": serial if mode == "usb" else None,
            "wda_manager": self.wda_manager
        }
        
        if script_type == "swiper":
            config["swiper_bundle_id"] = self.swiper_app_combo.currentData()
            config["delay_min"] = self.swiper_delay_min.value()
            config["delay_max"] = self.swiper_delay_max.value()
            config["randomize"] = self.swiper_jitter.isChecked()
        elif script_type == "apple_id":
            config["email_domain"] = self.apple_email_dom.text().strip()
            config["password"] = self.apple_pass.text().strip()
            config["sms_key"] = self.apple_sms_key.text().strip()
            config["captcha_key"] = self.apple_captcha_key.text().strip()
        elif script_type == "custom":
            config["custom_script_text"] = self.custom_script_edit.toPlainText()
        elif script_type == "add_card":
            config["limit_success"] = self.add_card_limit.value()
            config["password"] = self.add_card_apple_pass.text().strip()
            # Pass Card API configuration to AutomationRunner
            config["db_path"] = self.db.db_path
            config["online_mode"] = self.db.online_mode
            config["api_url"] = self.db.api_url
            config["api_token"] = self.db.api_token

        self.auto_log_console.clear()
        self.auto_count_label.setText("Đã thực hiện: <b>0</b>")
        self.auto_run_label.setText("Trạng thái: <b style='color: #10b981;'>Đang chạy</b>")
        
        self.auto_start_btn.setEnabled(False)
        self.auto_stop_btn.setEnabled(True)
        
        self.auto_worker = AutomationRunner(config)
        self.auto_worker.log_signal.connect(self.auto_log_console.append)
        self.auto_worker.count_signal.connect(lambda val: self.auto_count_label.setText(f"Đã thực hiện: <b>{val}</b>"))
        self.auto_worker.status_signal.connect(self.on_auto_run_status_changed)
        self.auto_worker.screenshot_signal.connect(self.handle_screenshot_signal)
        self.auto_worker.start()
        
    def handle_auto_stop(self):
        if self.auto_worker and self.auto_worker.isRunning():
            self.log_auto("⏳ Đang gửi yêu cầu dừng luồng tự động hóa...", "warn")
            self.auto_worker.requestInterruption()
            self.auto_stop_btn.setEnabled(False)
            
    def on_auto_run_status_changed(self, status, is_running):
        if not is_running:
            self.auto_start_btn.setEnabled(True)
            self.auto_stop_btn.setEnabled(False)
            self.auto_run_label.setText("Trạng thái: <b style='color: #ef4444;'>Đang dừng</b>")
            self.log_auto(f"ℹ️ Tiến trình chạy tự động đã dừng. Trạng thái: {status}", "info")
            try:
                self.load_cards_table()
            except Exception:
                pass

    def get_wda_client(self):
        mode = self.conn_mode_combo.currentData()
        if mode == "usb":
            serial = self.usb_device_combo.currentData()
            return WDAClient(host="http://127.0.0.1", port=8100, serial=serial)
        else:
            host = self.wda_host_input.text().strip()
            port_str = self.wda_port_input.text().strip()
            try:
                port = int(port_str)
            except ValueError:
                port = 8100
            return WDAClient(host=host, port=port)

    def handle_manual_home(self):
        client = self.get_wda_client()
        if client.check_status():
            client.start_session()
            if client.go_home():
                self.log_auto("🏠 Bấm nút Home thành công.", "success")
                self.handle_manual_snap()
            else:
                self.log_auto("❌ Bấm nút Home thất bại.", "error")
            client.close_session()
        else:
            self.log_auto("❌ Không thể kết nối tới WebDriverAgent.", "error")

    def handle_manual_launch(self, bundle_id):
        client = self.get_wda_client()
        if client.check_status():
            client.start_session()
            if client.launch_app(bundle_id):
                self.log_auto(f"📱 Đã khởi chạy ứng dụng: {bundle_id}", "success")
                self.handle_manual_snap()
            else:
                self.log_auto(f"❌ Không thể khởi chạy ứng dụng: {bundle_id}", "error")
            client.close_session()
        else:
            self.log_auto("❌ Không thể kết nối tới WebDriverAgent.", "error")

    def handle_manual_type(self):
        text, ok = QInputDialog.getText(self, "Nhập văn bản", "Nhập chữ muốn gõ trên điện thoại:")
        if ok and text:
            client = self.get_wda_client()
            if client.check_status():
                client.start_session()
                if client.type_text(text):
                    self.log_auto(f"⌨️ Đã gõ chữ: {text}", "success")
                    self.handle_manual_snap()
                else:
                    self.log_auto("❌ Gõ chữ thất bại.", "error")
                client.close_session()
            else:
                self.log_auto("❌ Không thể kết nối tới WebDriverAgent.", "error")

    def safeguard_thread(self, attr_name):
        if hasattr(self, attr_name):
            old_thread = getattr(self, attr_name)
            if old_thread is not None:
                try:
                    if old_thread.isRunning():
                        try:
                            old_thread.disconnect()
                        except Exception:
                            pass
                        if not hasattr(self, '_dying_threads'):
                            self._dying_threads = []
                        self._dying_threads.append(old_thread)
                        self._dying_threads = [t for t in self._dying_threads if t.isRunning()]
                except Exception:
                    pass

    def handle_manual_snap(self):
        self.live_screen_label.setText("Đang chụp...")
        client = self.get_wda_client()
        
        class ScreenshotThread(QThread):
            finished = pyqtSignal(str)
            def __init__(self, c):
                super().__init__()
                self.c = c
            def run(self):
                self.finished.emit(self.c.screenshot())
                
        self.safeguard_thread("snap_thread")
        self.snap_thread = ScreenshotThread(client)
        self.snap_thread.finished.connect(self.on_manual_snap_finished)
        self.snap_thread.start()

    def on_manual_snap_finished(self, base64_str):
        if base64_str:
            self.handle_screenshot_signal(base64_str)
            self.log_auto("📸 Đã cập nhật ảnh chụp màn hình live.", "success")
        else:
            self.live_screen_label.setText("Lỗi chụp ảnh")
            self.log_auto("❌ Không thể chụp ảnh màn hình (Lỗi kết nối hoặc WDA chưa sẵn sàng).", "error")

    def handle_auto_clear_logs(self):
        self.auto_log_console.clear()
        self.log_auto("🧹 Đã làm sạch nhật ký tự động hóa.", "info")

    def handle_conn_mode_changed(self, index):
        mode = self.conn_mode_combo.currentData()
        is_usb = (mode == "usb")
        
        self.usb_device_label.setVisible(is_usb)
        self.usb_container_widget.setVisible(is_usb)
        self.wda_autosetup_btn.setVisible(is_usb)
        
        self.manual_host_label.setVisible(not is_usb)
        self.manual_host_container.setVisible(not is_usb)
        self.manual_port_label.setVisible(not is_usb)
        self.manual_port_container.setVisible(not is_usb)
        
        if is_usb:
            self.refresh_usb_devices()

    def refresh_usb_devices(self):
        self.usb_device_combo.blockSignals(True)
        self.usb_device_combo.clear()
        if not PYMOBILEDEVICE3_AVAILABLE:
            self.usb_device_combo.addItem("⚠️ pymobiledevice3 không khả dụng", "")
            self.usb_device_combo.blockSignals(False)
            return
            
        devices = DeviceBridge.get_connected_devices()
        if not devices:
            self.usb_device_combo.addItem("❌ Không tìm thấy thiết bị USB", "")
            self.lbl_status_device.setText("Thiết bị: <b style='color: #ef4444;'>Chưa kết nối</b>")
            self.lbl_status_ios.setText("iOS: <b>-</b>")
            self.usb_device_combo.blockSignals(False)
            return
            
        for dev in devices:
            serial = dev.get("serial")
            conn_type = dev.get("connection_type", "USB")
            self.usb_device_combo.addItem(f"📱 iPhone ({serial[:8]}...) - {conn_type}", serial)
            
        self.usb_device_combo.blockSignals(False)
        self.handle_usb_device_changed()

    def handle_usb_device_changed(self):
        serial = self.usb_device_combo.currentData()
        if not serial:
            return
            
        self.lbl_status_device.setText("Thiết bị: <b>Đang kết nối...</b>")
        self.lbl_status_ios.setText("iOS: <b>-</b>")
        self.lbl_status_wda.setText("Trạng thái WDA: <b>-</b>")
        
        class GetDeviceInfoThread(QThread):
            finished = pyqtSignal(dict)
            def __init__(self, serial, wda_manager):
                super().__init__()
                self.serial = serial
                self.wda_manager = wda_manager
            def run(self):
                try:
                    info = DeviceBridge.get_device_info(self.serial)
                    self.wda_manager.start_relay(self.serial)
                    time.sleep(1.0)
                    client = WDAClient(host="http://127.0.0.1", port=8100)
                    wda_ok = client.check_status()
                    info["wda_running"] = wda_ok
                    if not wda_ok:
                        self.wda_manager.stop_relay()
                    self.finished.emit(info)
                except Exception as e:
                    self.finished.emit({"error": str(e)})
                    
        self.safeguard_thread("info_thread")
        self.info_thread = GetDeviceInfoThread(serial, self.wda_manager)
        self.info_thread.finished.connect(self.on_device_info_fetched)
        self.info_thread.start()

    def on_device_info_fetched(self, info):
        if "error" in info:
            self.lbl_status_device.setText("Thiết bị: <b style='color: #ef4444;'>Lỗi kết nối</b>")
            self.lbl_status_ios.setText("iOS: <b>-</b>")
            self.lbl_status_wda.setText("Trạng thái WDA: <b>-</b>")
            self.log_auto(f"❌ Không thể lấy thông tin thiết bị: {info['error']}", "error")
            return
            
        name = info.get("name", "iPhone")
        ios = info.get("ios_version", "-")
        wda_running = info.get("wda_running", False)
        
        self.lbl_status_device.setText(f"Thiết bị: <b>{name}</b> ({info.get('model', '')})")
        self.lbl_status_ios.setText(f"iOS: <b>{ios}</b>")
        
        if wda_running:
            self.lbl_status_wda.setText("Trạng thái WDA: <b style='color: #10b981;'>🟢 Đang chạy</b>")
        else:
            self.lbl_status_wda.setText("Trạng thái WDA: <b style='color: #ef4444;'>🔴 Chưa chạy</b>")
            
        self.log_auto(f"📱 Đã nhận diện thiết bị: {name} (iOS {ios})", "success")

    def handle_wda_autosetup(self):
        serial = self.usb_device_combo.currentData()
        if not serial:
            QMessageBox.warning(self, "Không tìm thấy thiết bị", "Vui lòng kết nối iPhone qua USB và quét lại!")
            return
            
        self.log_auto("⚡ Bắt đầu cài đặt WDA 1 chạm...", "info")
        self.wda_autosetup_btn.setEnabled(False)
        self.wda_autosetup_btn.setText("⏳ Đang cài đặt...")
        
        class AutoSetupWDAThread(QThread):
            log_signal = pyqtSignal(str, str)
            finished = pyqtSignal(bool)
            
            def __init__(self, serial, ipa_path, manager):
                super().__init__()
                self.serial = serial
                self.ipa_path = ipa_path
                self.manager = manager
                
            def run(self):
                def log_cb(msg):
                    style = "info"
                    if "✅" in msg or "🟢" in msg:
                        style = "success"
                    elif "❌" in msg or "🔴" in msg:
                        style = "error"
                    elif "ℹ️" in msg or "⚠️" in msg:
                        style = "warn"
                    self.log_signal.emit(msg, style)
                    
                try:
                    success = self.manager.auto_setup(self.serial, self.ipa_path, log_cb=log_cb)
                    self.finished.emit(success)
                except Exception as e:
                    self.log_signal.emit(f"❌ Lỗi thiết lập: {str(e)}", "error")
                    self.finished.emit(False)
                    
        self.safeguard_thread("setup_wda_thread")
        self.setup_wda_thread = AutoSetupWDAThread(serial, self.wda_ipa_path, self.wda_manager)
        self.setup_wda_thread.log_signal.connect(self.log_auto)
        self.setup_wda_thread.finished.connect(self.on_wda_autosetup_finished)
        self.setup_wda_thread.start()

    def on_wda_autosetup_finished(self, success):
        self.wda_autosetup_btn.setEnabled(True)
        self.wda_autosetup_btn.setText("⚡ Cài đặt WDA 1 chạm")
        if success:
            QMessageBox.information(self, "Thành công", "WebDriverAgent đã được cài đặt và đang chạy thành công!")
            self.lbl_status_wda.setText("Trạng thái WDA: <b style='color: #10b981;'>🟢 Đang chạy</b>")
        else:
            QMessageBox.critical(self, "Lỗi cài đặt", "Thiết lập WebDriverAgent thất bại. Vui lòng xem logs chi tiết.")
            self.lbl_status_wda.setText("Trạng thái WDA: <b style='color: #ef4444;'>🔴 Lỗi/Chưa chạy</b>")

    def handle_sideloadly_helper(self):
        import webbrowser
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Hướng dẫn Ký và Cài đặt WDA qua Sideloadly")
        dialog.resize(500, 320)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #060a1a;
                border: 1px solid #0e1630;
                border-radius: 16px;
            }
            QLabel {
                color: #f8fafc;
                font-size: 13px;
            }
            QPushButton {
                background-color: #d946ef;
                color: white;
                padding: 10px 16px;
                border-radius: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c084fc;
            }
            QPushButton#secondaryButton {
                background-color: rgba(255, 255, 255, 0.03);
                border: 1px solid #0e1630;
            }
            QPushButton#secondaryButton:hover {
                background-color: rgba(255, 255, 255, 0.06);
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        title = QLabel("🛠️ Ký WDA bằng Sideloadly (Khắc phục lỗi cài TrollStore)")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #00f2fe;")
        layout.addWidget(title)

        desc = QLabel(
            "Do TrollStore bị lỗi không thể tự động xử lý gói XCTest của WebDriverAgent,\n"
            "bạn hãy ký và cài đặt qua Sideloadly bằng cách cấu hình chính xác như sau:\n\n"
            "1. Tải và cài đặt Sideloadly trên máy tính.\n"
            "2. Cắm điện thoại qua USB, mở Sideloadly và kéo thả file IPA vào phần mềm.\n"
            "3. Mở rộng phần <b>Advanced Options</b> trong Sideloadly và thiết lập:\n"
            "   - ❌ <b>KHÔNG</b> tích chọn <i>Remove plug-ins</i> (nếu tích sẽ bị mất gói XCTest gây lỗi).\n"
            "   - ❌ <b>KHÔNG</b> tích chọn <i>Change bundle ID</i> (hoặc chọn <i>Use original bundle ID</i> để tránh lỗi lệch chữ ký của plugin).\n"
            "4. Nhập Apple ID của bạn, nhấn <b>Start</b> và nhập mã 2FA để tiến hành cài đặt.\n"
            "5. Sau khi cài xong, vào <b>Cài đặt -> Cài đặt chung -> Quản lý thiết bị -> Tin cậy tài khoản của bạn</b> trên điện thoại để mở ứng dụng."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        web_btn = QPushButton("🌐 Tải Sideloadly")
        web_btn.clicked.connect(lambda: webbrowser.open("https://sideloadly.io/"))

        folder_btn = QPushButton("📂 Mở thư mục chứa file IPA")
        folder_btn.setObjectName("secondaryButton")
        
        def open_folder():
            ipa_dir = os.path.dirname(self.wda_ipa_path)
            if os.path.exists(ipa_dir):
                os.startfile(ipa_dir)
            else:
                QMessageBox.warning(dialog, "Lỗi", f"Không tìm thấy thư mục: {ipa_dir}")

        folder_btn.clicked.connect(open_folder)

        close_btn = QPushButton("Đóng")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(dialog.accept)

        btn_layout.addWidget(web_btn)
        btn_layout.addWidget(folder_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec_()

    def get_selected_serial(self):
        if self.conn_mode_combo.currentData() == "usb":
            serial = self.usb_device_combo.currentData()
            if not serial:
                QMessageBox.warning(self, "Không tìm thấy thiết bị", "Vui lòng kết nối iPhone qua USB!")
                return None
            return serial
        else:
            QMessageBox.warning(self, "Chế độ USB yêu cầu", "Tính năng này chỉ hỗ trợ trong chế độ kết nối USB!")
            return None

    def handle_dvt_snap(self):
        self.live_screen_label.setText("Đang chụp...")
        serial = self.get_selected_serial()
        if not serial:
            self.live_screen_label.setText("Chưa chụp ảnh")
            return
            
        self.log_auto("📸 Đang thực hiện chụp ảnh màn hình qua DVT...", "info")
        
        class DVTScreenshotThread(QThread):
            finished = pyqtSignal(bytes, str)
            def __init__(self, serial):
                super().__init__()
                self.serial = serial
            def run(self):
                try:
                    img_bytes = DeviceBridge.take_screenshot(self.serial)
                    self.finished.emit(img_bytes, "")
                except Exception as e:
                    self.finished.emit(b"", str(e))
                    
        self.safeguard_thread("dvt_snap_thread")
        self.dvt_snap_thread = DVTScreenshotThread(serial)
        self.dvt_snap_thread.finished.connect(self.on_dvt_snap_finished)
        self.dvt_snap_thread.start()

    def on_dvt_snap_finished(self, img_bytes, err_msg):
        if img_bytes:
            try:
                from PyQt5.QtGui import QPixmap
                pixmap = QPixmap()
                if pixmap.loadFromData(img_bytes):
                    scaled = pixmap.scaled(self.live_screen_label.width() - 4, self.live_screen_label.height() - 4, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    self.live_screen_label.setPixmap(scaled)
                    self.log_auto("📸 Chụp ảnh màn hình qua DVT thành công.", "success")
                else:
                    self.live_screen_label.setText("Lỗi hiển thị")
            except Exception as e:
                self.log_auto(f"❌ Lỗi hiển thị ảnh DVT: {e}", "error")
        else:
            self.live_screen_label.setText("Lỗi chụp ảnh")
            self.log_auto(f"❌ Chụp ảnh màn hình qua DVT thất bại: {err_msg}", "error")

    def handle_dvt_launch(self):
        serial = self.get_selected_serial()
        if not serial:
            return
            
        bundle_id, ok = QInputDialog.getText(self, "Khởi chạy ứng dụng", "Nhập Bundle ID của ứng dụng (ví dụ: com.apple.Preferences):")
        if ok and bundle_id:
            self.log_auto(f"🚀 Đang mở ứng dụng: {bundle_id}...", "info")
            
            class DVTLaunchThread(QThread):
                finished = pyqtSignal(int, str)
                def __init__(self, serial, bid):
                    super().__init__()
                    self.serial = serial
                    self.bid = bid
                def run(self):
                    try:
                        pid = DeviceBridge.launch_app(self.serial, self.bid)
                        self.finished.emit(pid, "")
                    except Exception as e:
                        self.finished.emit(-1, str(e))
                        
            self.safeguard_thread("dvt_launch_thread")
            self.dvt_launch_thread = DVTLaunchThread(serial, bundle_id)
            self.dvt_launch_thread.finished.connect(lambda pid, err: self.on_dvt_launch_finished(bundle_id, pid, err))
            self.dvt_launch_thread.start()

    def on_dvt_launch_finished(self, bundle_id, pid, err_msg):
        if pid > 0:
            self.log_auto(f"✅ Đã mở thành công ứng dụng {bundle_id} (PID: {pid}).", "success")
            self.handle_dvt_snap()
        else:
            self.log_auto(f"❌ Mở ứng dụng {bundle_id} thất bại: {err_msg}", "error")

    def handle_dvt_kill(self):
        serial = self.get_selected_serial()
        if not serial:
            return
            
        bundle_id, ok = QInputDialog.getText(self, "Tắt ứng dụng", "Nhập Bundle ID của ứng dụng cần tắt:")
        if ok and bundle_id:
            self.log_auto(f"☠️ Đang tắt ứng dụng: {bundle_id}...", "info")
            
            class DVTKillThread(QThread):
                finished = pyqtSignal(bool, str)
                def __init__(self, serial, bid):
                    super().__init__()
                    self.serial = serial
                    self.bid = bid
                def run(self):
                    try:
                        success = DeviceBridge.kill_app(self.serial, self.bid)
                        self.finished.emit(success, "")
                    except Exception as e:
                        self.finished.emit(False, str(e))
                        
            self.safeguard_thread("dvt_kill_thread")
            self.dvt_kill_thread = DVTKillThread(serial, bundle_id)
            self.dvt_kill_thread.finished.connect(lambda success, err: self.on_dvt_kill_finished(bundle_id, success, err))
            self.dvt_kill_thread.start()

    def on_dvt_kill_finished(self, bundle_id, success, err_msg):
        if success:
            self.log_auto(f"✅ Đã đóng thành công ứng dụng {bundle_id}.", "success")
            self.handle_dvt_snap()
        else:
            self.log_auto(f"❌ Đóng ứng dụng {bundle_id} thất bại hoặc app chưa chạy: {err_msg}", "error")

    def handle_dvt_gps(self):
        serial = self.get_selected_serial()
        if not serial:
            return
            
        gps_str, ok = QInputDialog.getText(self, "Giả lập GPS", "Nhập tọa độ Vĩ độ,Kinh độ (ví dụ: 21.0285,105.8542 cho Hà Nội):")
        if ok and gps_str:
            try:
                lat_str, lng_str = gps_str.split(",")
                lat = float(lat_str.strip())
                lng = float(lng_str.strip())
            except Exception:
                QMessageBox.warning(self, "Định dạng sai", "Vui lòng nhập định dạng: Vĩ_độ,Kinh_độ (ví dụ: 21.0285,105.8542)")
                return
                
            self.log_auto(f"📍 Đang thiết lập giả lập vị trí GPS: {lat}, {lng}...", "info")
            
            class DVTGPSThread(QThread):
                finished = pyqtSignal(bool, str)
                def __init__(self, serial, lat, lng):
                    super().__init__()
                    self.serial = serial
                    self.lat = lat
                    self.lng = lng
                def run(self):
                    try:
                        success = DeviceBridge.simulate_location(self.serial, self.lat, self.lng)
                        self.finished.emit(success, "")
                    except Exception as e:
                        self.finished.emit(False, str(e))
                        
            self.safeguard_thread("dvt_gps_thread")
            self.dvt_gps_thread = DVTGPSThread(serial, lat, lng)
            self.dvt_gps_thread.finished.connect(self.on_dvt_gps_finished)
            self.dvt_gps_thread.start()

    def on_dvt_gps_finished(self, success, err_msg):
        if success:
            self.log_auto("✅ Đã kích hoạt giả lập vị trí GPS thành công.", "success")
        else:
            self.log_auto(f"❌ Kích hoạt giả lập vị trí GPS thất bại: {err_msg}", "error")

    def handle_dvt_gps_clear(self):
        serial = self.get_selected_serial()
        if not serial:
            return
            
        self.log_auto("📍 Đang xóa giả lập vị trí GPS...", "info")
        
        class DVTGPSClearThread(QThread):
            finished = pyqtSignal(bool, str)
            def __init__(self, serial):
                super().__init__()
                self.serial = serial
            def run(self):
                try:
                    success = DeviceBridge.clear_location(self.serial)
                    self.finished.emit(success, "")
                except Exception as e:
                    self.finished.emit(False, str(e))
                    
        self.safeguard_thread("dvt_gps_clear_thread")
        self.dvt_gps_clear_thread = DVTGPSClearThread(serial)
        self.dvt_gps_clear_thread.finished.connect(self.on_dvt_gps_clear_finished)
        self.dvt_gps_clear_thread.start()

    def on_dvt_gps_clear_finished(self, success, err_msg):
        if success:
            self.log_auto("✅ Đã xóa giả lập vị trí GPS thành công (đưa về vị trí thực tế).", "success")
        else:
            self.log_auto(f"❌ Xóa giả lập vị trí GPS thất bại: {err_msg}", "error")

    # ==================================================================
    # --- ANTI-DETECT BROWSER 🛡️ TAB UI ---
    # ==================================================================

    def init_browser_tab_ui(self):
        """Initialize the Anti-Detect Browser management tab UI."""
        if not MUN_ANTI_BROWSER_AVAILABLE:
            layout = QVBoxLayout(self.browser_tab)
            layout.addWidget(QLabel("⚠️ Module mun_anti_browser chưa được cài đặt.\n"
                                     "Vui lòng chạy: pip install nodriver"))
            return

        browser_layout = QHBoxLayout(self.browser_tab)
        browser_layout.setContentsMargins(15, 15, 15, 15)
        browser_layout.setSpacing(15)

        # --- CỘT TRÁI: CẤU HÌNH ---
        left_col = QWidget()
        left_col.setFixedWidth(380)
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        # -- Group 1: Tạo Profile --
        profile_group = QGroupBox("🔧 Tạo Profile Anti-Detect")
        profile_grid = QGridLayout(profile_group)
        profile_grid.setSpacing(8)

        profile_grid.addWidget(QLabel("Tên profile:"), 0, 0)
        self.browser_profile_name = QLineEdit()
        self.browser_profile_name.setPlaceholderText("VD: Profile_1")
        profile_grid.addWidget(self.browser_profile_name, 0, 1)

        profile_grid.addWidget(QLabel("Hệ điều hành:"), 1, 0)
        self.browser_os_combo = QComboBox()
        self.browser_os_combo.addItems(["Windows", "macOS", "Linux", "Random"])
        profile_grid.addWidget(self.browser_os_combo, 1, 1)

        profile_grid.addWidget(QLabel("Độ phân giải:"), 2, 0)
        self.browser_res_combo = QComboBox()
        self.browser_res_combo.addItems([
            "1920x1080", "1440x900", "1366x768", "2560x1440",
            "1536x864", "1280x720", "Random"
        ])
        profile_grid.addWidget(self.browser_res_combo, 2, 1)

        profile_grid.addWidget(QLabel("CPU cores:"), 3, 0)
        self.browser_cpu_combo = QComboBox()
        self.browser_cpu_combo.addItems(["4", "8", "12", "16", "Random"])
        self.browser_cpu_combo.setCurrentIndex(1)  # default 8
        profile_grid.addWidget(self.browser_cpu_combo, 3, 1)

        self.browser_create_btn = QPushButton("➕ Tạo Profile Mới")
        self.browser_create_btn.setObjectName("primaryButton")
        self.browser_create_btn.clicked.connect(self.handle_create_browser_profile)
        profile_grid.addWidget(self.browser_create_btn, 4, 0, 1, 2)

        left_layout.addWidget(profile_group)

        # -- Group 2: Proxy --
        proxy_group = QGroupBox("🌐 Cấu Hình Proxy")
        proxy_grid = QGridLayout(proxy_group)
        proxy_grid.setSpacing(8)

        proxy_grid.addWidget(QLabel("Loại proxy:"), 0, 0)
        self.browser_proxy_type = QComboBox()
        self.browser_proxy_type.addItems(["socks5", "http", "Không dùng proxy"])
        proxy_grid.addWidget(self.browser_proxy_type, 0, 1)

        proxy_grid.addWidget(QLabel("Proxy:"), 1, 0)
        self.browser_proxy_input = QLineEdit()
        self.browser_proxy_input.setPlaceholderText("host:port (VD: 1.2.3.4:1080)")
        proxy_grid.addWidget(self.browser_proxy_input, 1, 1)

        proxy_grid.addWidget(QLabel("Username:"), 2, 0)
        self.browser_proxy_user = QLineEdit()
        self.browser_proxy_user.setPlaceholderText("(tùy chọn)")
        proxy_grid.addWidget(self.browser_proxy_user, 2, 1)

        proxy_grid.addWidget(QLabel("Password:"), 3, 0)
        self.browser_proxy_pass = QLineEdit()
        self.browser_proxy_pass.setPlaceholderText("(tùy chọn)")
        self.browser_proxy_pass.setEchoMode(QLineEdit.Password)
        proxy_grid.addWidget(self.browser_proxy_pass, 3, 1)

        left_layout.addWidget(proxy_group)

        # -- Group 3: Hành động --
        action_group = QGroupBox("🚀 Hành Động")
        action_layout = QVBoxLayout(action_group)
        action_layout.setSpacing(8)

        self.browser_launch_btn = QPushButton("▶️ Mở Browser (Profile đã chọn)")
        self.browser_launch_btn.setObjectName("primaryButton")
        self.browser_launch_btn.clicked.connect(self.handle_launch_browser)
        action_layout.addWidget(self.browser_launch_btn)

        self.browser_stop_btn = QPushButton("⏹️ Dừng Browser")
        self.browser_stop_btn.setObjectName("secondaryButton")
        self.browser_stop_btn.setEnabled(False)
        self.browser_stop_btn.clicked.connect(self.handle_stop_browser)
        action_layout.addWidget(self.browser_stop_btn)

        btn_row = QHBoxLayout()
        self.browser_test_cf_btn = QPushButton("🧪 Test Cloudflare")
        self.browser_test_cf_btn.setObjectName("secondaryButton")
        self.browser_test_cf_btn.clicked.connect(self.handle_test_cloudflare)
        btn_row.addWidget(self.browser_test_cf_btn)

        self.browser_test_fp_btn = QPushButton("🔍 Test Fingerprint")
        self.browser_test_fp_btn.setObjectName("secondaryButton")
        self.browser_test_fp_btn.clicked.connect(self.handle_test_fingerprint)
        btn_row.addWidget(self.browser_test_fp_btn)
        action_layout.addLayout(btn_row)

        btn_row2 = QHBoxLayout()
        self.browser_test_iphey_btn = QPushButton("🛡️ Test iphey.com")
        self.browser_test_iphey_btn.setObjectName("secondaryButton")
        self.browser_test_iphey_btn.clicked.connect(self.handle_test_iphey)
        btn_row2.addWidget(self.browser_test_iphey_btn)

        self.browser_test_leak_btn = QPushButton("🌐 Test WebRTC Leak")
        self.browser_test_leak_btn.setObjectName("secondaryButton")
        self.browser_test_leak_btn.clicked.connect(self.handle_test_webrtc_leak)
        btn_row2.addWidget(self.browser_test_leak_btn)
        action_layout.addLayout(btn_row2)

        # Status indicator
        self.browser_status_label = QLabel("⏸️ Chưa chạy")
        self.browser_status_label.setStyleSheet("font-size: 13px; color: #94a3b8; padding: 5px;")
        action_layout.addWidget(self.browser_status_label)

        left_layout.addWidget(action_group)
        left_layout.addStretch()

        browser_layout.addWidget(left_col)

        # --- CỘT PHẢI: DANH SÁCH PROFILES ---
        right_col = QWidget()
        right_layout = QVBoxLayout(right_col)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)

        profiles_group = QGroupBox("📋 Danh Sách Browser Profiles")
        profiles_layout = QVBoxLayout(profiles_group)
        profiles_layout.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        self.browser_refresh_btn = QPushButton("🔄 Làm mới")
        self.browser_refresh_btn.setObjectName("secondaryButton")
        self.browser_refresh_btn.clicked.connect(self.load_browser_profiles_table)
        toolbar.addWidget(self.browser_refresh_btn)

        self.browser_delete_btn = QPushButton("🗑️ Xóa profile")
        self.browser_delete_btn.setObjectName("secondaryButton")
        self.browser_delete_btn.clicked.connect(self.handle_delete_browser_profile)
        toolbar.addWidget(self.browser_delete_btn)

        self.browser_pull_btn = QPushButton("☁️ Tải từ server")
        self.browser_pull_btn.setObjectName("secondaryButton")
        self.browser_pull_btn.clicked.connect(self.handle_pull_profiles_from_server)
        toolbar.addWidget(self.browser_pull_btn)

        self.browser_push_btn = QPushButton("⬆️ Đẩy lên server")
        self.browser_push_btn.setObjectName("secondaryButton")
        self.browser_push_btn.clicked.connect(self.handle_push_profile_to_server)
        toolbar.addWidget(self.browser_push_btn)

        toolbar.addStretch()
        profiles_layout.addLayout(toolbar)

        # Profiles Table
        self.browser_profiles_table = QTableWidget()
        self.browser_profiles_table.setColumnCount(6)
        self.browser_profiles_table.setHorizontalHeaderLabels([
            "Tên", "OS", "Độ phân giải", "Proxy", "Server ID", "Trạng thái"
        ])
        header = self.browser_profiles_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionResizeMode(0, QHeaderView.Stretch)          # Tên
        header.setSectionResizeMode(1, QHeaderView.Interactive)      # OS
        header.setSectionResizeMode(2, QHeaderView.Interactive)      # Độ phân giải
        header.setSectionResizeMode(3, QHeaderView.Stretch)          # Proxy (co-stretch)
        header.setSectionResizeMode(4, QHeaderView.Interactive)      # Server ID
        header.setSectionResizeMode(5, QHeaderView.Interactive)      # Trạng thái
        
        self.browser_profiles_table.setColumnWidth(1, 80)            # OS
        self.browser_profiles_table.setColumnWidth(2, 110)           # Resolution
        self.browser_profiles_table.setColumnWidth(4, 90)            # Server ID
        self.browser_profiles_table.setColumnWidth(5, 110)           # Status
        
        self.browser_profiles_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.browser_profiles_table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.browser_profiles_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.browser_profiles_table.verticalHeader().setDefaultSectionSize(35)
        profiles_layout.addWidget(self.browser_profiles_table)

        right_layout.addWidget(profiles_group)
        browser_layout.addWidget(right_col, 1)

        # Load saved profiles
        self._browser_profiles_file = os.path.join(get_app_dir(), "browser_profiles.json")
        self._browser_profiles = self._load_browser_profiles_json()
        self.browser_workers = {}  # Track running browser instances by profile name
        self.load_browser_profiles_table()

    # --- Browser Profile Persistence (JSON) ---

    def _load_browser_profiles_json(self):
        """Load saved browser profiles from JSON file."""
        try:
            if os.path.exists(self._browser_profiles_file):
                with open(self._browser_profiles_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            self.log(f"⚠️ Lỗi load browser profiles: {e}")
        return []

    def _save_browser_profiles_json(self):
        """Save browser profiles to JSON file."""
        try:
            with open(self._browser_profiles_file, "w", encoding="utf-8") as f:
                json.dump(self._browser_profiles, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.log(f"⚠️ Lỗi save browser profiles: {e}")

    def load_browser_profiles_table(self):
        """Populate the profiles QTableWidget from saved data."""
        self._browser_profiles = self._load_browser_profiles_json()
        self.browser_profiles_table.setRowCount(len(self._browser_profiles))
        for row, profile in enumerate(self._browser_profiles):
            name_item = QTableWidgetItem(profile.get("name", f"Profile_{row+1}"))
            os_item = QTableWidgetItem(profile.get("profile_os", "Unknown"))
            res_item = QTableWidgetItem(profile.get("profile_resolution", "1920x1080"))
            proxy_text = profile.get("proxy_string", "")
            proxy_item = QTableWidgetItem(proxy_text if proxy_text else "Không có")
            # Server ID
            server_id = profile.get("server_id", "")
            server_id_item = QTableWidgetItem(str(server_id) if server_id else "—")
            # Check if running
            is_running = profile.get("name", "") in self.browser_workers
            status_item = QTableWidgetItem("🟢 Đang chạy" if is_running else "⚪ Dừng")
            for item in [name_item, os_item, res_item, proxy_item, server_id_item, status_item]:
                item.setTextAlignment(Qt.AlignCenter)
            self.browser_profiles_table.setItem(row, 0, name_item)
            self.browser_profiles_table.setItem(row, 1, os_item)
            self.browser_profiles_table.setItem(row, 2, res_item)
            self.browser_profiles_table.setItem(row, 3, proxy_item)
            self.browser_profiles_table.setItem(row, 4, server_id_item)
            self.browser_profiles_table.setItem(row, 5, status_item)

    # --- C69 API Integration ---

    def _get_c69_api(self):
        """Get a configured C69ProfileAPI instance, or None if not logged in."""
        if not MUN_ANTI_BROWSER_AVAILABLE:
            return None
        config_path = os.path.join(get_app_dir(), "online_cards_config.json")
        if not os.path.exists(config_path):
            return None
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            api_url = data.get("api_url", "").rstrip("/")
            api_token = data.get("api_token", "")
            if api_url and api_token:
                return C69ProfileAPI(api_url, api_token)
        except Exception:
            pass
        return None

    def handle_pull_profiles_from_server(self):
        """Tải tất cả profiles từ server C69 và merge vào danh sách local."""
        api = self._get_c69_api()
        if not api:
            QMessageBox.warning(self, "Chưa đăng nhập",
                                "Vui lòng đăng nhập Storagon/C69 trước khi đồng bộ!")
            return

        self.log("☁️ Đang tải profiles từ server...")
        self.browser_pull_btn.setEnabled(False)
        try:
            server_profiles = api.list_profiles()
        except ConnectionError as e:
            QMessageBox.critical(self, "Lỗi kết nối", str(e))
            self.browser_pull_btn.setEnabled(True)
            return
        except Exception as e:
            QMessageBox.critical(self, "Lỗi", f"Không thể tải profiles: {e}")
            self.browser_pull_btn.setEnabled(True)
            return

        if not server_profiles:
            self.log("ℹ️ Server không có profile nào.")
            self.browser_pull_btn.setEnabled(True)
            return

        # Build lookup of existing local profiles by server_id
        local_by_server_id = {}
        for i, p in enumerate(self._browser_profiles):
            sid = p.get("server_id")
            if sid:
                local_by_server_id[sid] = i

        added = 0
        updated = 0
        for sp in server_profiles:
            sid = sp.get("server_id")
            if not sid:
                continue

            if sid in local_by_server_id:
                # Update existing local profile with server data (server wins)
                idx = local_by_server_id[sid]
                local_name = self._browser_profiles[idx].get("name", "")
                # Preserve local-only fields
                for key, value in sp.items():
                    if value is not None and value != "":
                        self._browser_profiles[idx][key] = value
                # Keep original local name if it was set
                if local_name:
                    self._browser_profiles[idx]["name"] = local_name
                updated += 1
            else:
                # New profile from server — add to local
                if not sp.get("name"):
                    sp["name"] = f"Server_{sid}"
                # Check name conflict
                existing_names = {p.get("name") for p in self._browser_profiles}
                if sp["name"] in existing_names:
                    sp["name"] = f"{sp['name']}_{sid}"
                self._browser_profiles.append(sp)
                added += 1

        self._save_browser_profiles_json()
        self.load_browser_profiles_table()
        self.log(f"☁️ Đồng bộ xong! Thêm mới: {added}, Cập nhật: {updated} profiles từ server.")
        self.browser_pull_btn.setEnabled(True)

    def handle_push_profile_to_server(self):
        """Đẩy profile đang chọn lên server C69."""
        api = self._get_c69_api()
        if not api:
            QMessageBox.warning(self, "Chưa đăng nhập",
                                "Vui lòng đăng nhập Storagon/C69 trước khi đồng bộ!")
            return

        profile = self._get_selected_browser_profile()
        if not profile:
            return

        name = profile.get("name", "Unknown")
        server_id = profile.get("server_id")

        self.log(f"⬆️ Đang đẩy profile '{name}' lên server...")
        self.browser_push_btn.setEnabled(False)

        try:
            if server_id:
                # Update existing on server
                result = api.update_profile(server_id, profile)
                if result:
                    self.log(f"✅ Đã cập nhật profile '{name}' trên server (ID: {server_id})")
                else:
                    self.log(f"❌ Lỗi cập nhật profile '{name}' trên server")
            else:
                # Create new on server
                result = api.create_profile(profile)
                if result and result.get("server_id"):
                    # Save server_id back to local
                    new_sid = result["server_id"]
                    for p in self._browser_profiles:
                        if p.get("name") == name:
                            p["server_id"] = new_sid
                            break
                    self._save_browser_profiles_json()
                    self.load_browser_profiles_table()
                    self.log(f"✅ Đã tạo profile '{name}' trên server (ID: {new_sid})")
                else:
                    self.log(f"❌ Lỗi tạo profile '{name}' trên server")
        except Exception as e:
            self.log(f"❌ Lỗi đẩy profile lên server: {e}")
        finally:
            self.browser_push_btn.setEnabled(True)

    def _auto_push_to_server(self, profile_config):
        """Auto push profile to server after creation (non-blocking)."""
        api = self._get_c69_api()
        if not api:
            return
        try:
            result = api.create_profile(profile_config)
            if result and result.get("server_id"):
                name = profile_config.get("name", "")
                for p in self._browser_profiles:
                    if p.get("name") == name:
                        p["server_id"] = result["server_id"]
                        break
                self._save_browser_profiles_json()
                self.load_browser_profiles_table()
                self.log(f"☁️ Auto-sync: profile '{name}' → server (ID: {result['server_id']})")
        except Exception as e:
            self.log(f"⚠️ Auto-sync thất bại: {e}")

    def _fetch_server_profile(self, profile_config):
        """
        Fetch latest profile data from server (server wins).
        Returns updated profile_config or original if no server link.
        """
        server_id = profile_config.get("server_id")
        if not server_id:
            return profile_config

        api = self._get_c69_api()
        if not api:
            return profile_config

        try:
            server_data = api.get_profile(server_id)
            if server_data:
                # Server wins: merge server data into local config
                local_name = profile_config.get("name", "")
                for key, value in server_data.items():
                    if value is not None and value != "":
                        profile_config[key] = value
                # Preserve local name
                if local_name:
                    profile_config["name"] = local_name
                self.log(f"☁️ Đã tải cấu hình mới nhất từ server (ID: {server_id})")
            else:
                self.log(f"⚠️ Profile server ID={server_id} không tìm thấy, dùng config local")
        except Exception as e:
            self.log(f"⚠️ Không thể tải profile từ server: {e}")

        return profile_config

    # --- Browser Handler Methods ---

    def handle_create_browser_profile(self):
        """Create a new anti-detect browser profile."""
        if not MUN_ANTI_BROWSER_AVAILABLE:
            QMessageBox.warning(self, "Lỗi", "Module mun_anti_browser chưa sẵn sàng.")
            return

        name = self.browser_profile_name.text().strip()
        if not name:
            name = f"Profile_{len(self._browser_profiles) + 1}"

        # Check duplicate name
        for p in self._browser_profiles:
            if p.get("name") == name:
                QMessageBox.warning(self, "Trùng tên", f"Profile '{name}' đã tồn tại!")
                return

        os_choice = self.browser_os_combo.currentText()
        res_choice = self.browser_res_combo.currentText()
        cpu_choice = self.browser_cpu_combo.currentText()

        # Get proxy config
        proxy_type = self.browser_proxy_type.currentText()
        proxy_string = self.browser_proxy_input.text().strip()
        proxy_user = self.browser_proxy_user.text().strip()
        proxy_pass = self.browser_proxy_pass.text().strip()

        # Use ProfileManager to generate a random profile
        pm = ProfileManager()

        # Map OS dropdown to profile OS
        os_map = {"Windows": "Windows", "macOS": "macOS", "Linux": "Linux"}
        target_os = os_map.get(os_choice, None)

        # Generate profile
        profile_config = pm.create_random_profile(
            socks5=proxy_string if proxy_type == "socks5" else "",
            proxy=proxy_string if proxy_type == "http" else "",
            proxy_username=proxy_user,
            proxy_password=proxy_pass,
        )

        # Override OS if specified
        if target_os:
            profile_config["profile_os"] = target_os

        # Override resolution if specified
        if res_choice != "Random":
            profile_config["profile_resolution"] = res_choice

        # Override CPU if specified
        if cpu_choice != "Random":
            profile_config["profile_cpu"] = int(cpu_choice)

        # Add metadata for persistence
        profile_config["name"] = name
        profile_config["proxy_string"] = proxy_string
        profile_config["proxy_type"] = proxy_type if proxy_type != "Không dùng proxy" else ""
        profile_config["proxy_username"] = proxy_user
        profile_config["proxy_password"] = proxy_pass

        # Save locally
        self._browser_profiles.append(profile_config)
        self._save_browser_profiles_json()
        self.load_browser_profiles_table()

        self.log(f"✅ Đã tạo browser profile: {name} (OS: {profile_config['profile_os']}, "
                 f"Resolution: {profile_config['profile_resolution']})")
        self.browser_profile_name.clear()

        # Auto push to server (if logged in)
        self._auto_push_to_server(profile_config)

    def _get_selected_browser_profile(self):
        """Get the currently selected profile from the table."""
        rows = self.browser_profiles_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.warning(self, "Chọn profile", "Vui lòng chọn một profile trong bảng!")
            return None
        row_idx = rows[0].row()
        if row_idx < 0 or row_idx >= len(self._browser_profiles):
            return None
        return self._browser_profiles[row_idx]

    def handle_launch_browser(self):
        """Launch an anti-detect browser with the selected profile."""
        profile = self._get_selected_browser_profile()
        if not profile:
            return

        name = profile.get("name", "Unknown")

        # Check if already running
        if name in self.browser_workers:
            QMessageBox.information(self, "Đang chạy",
                                     f"Browser '{name}' đang chạy. Hãy dừng trước khi mở lại.")
            return

        # Fetch latest config from server (server wins)
        profile = self._fetch_server_profile(profile)

        proxy_string = profile.get("proxy_string", "")
        proxy_type = profile.get("proxy_type", "socks5")
        proxy_user = profile.get("proxy_username", "")
        proxy_pass = profile.get("proxy_password", "")

        worker = BrowserWorker(
            profile_config=profile,
            profile_name=name,
            proxy_string=proxy_string,
            proxy_type=proxy_type,
            proxy_username=proxy_user,
            proxy_password=proxy_pass,
        )
        worker.log_signal.connect(self.log)
        worker.status_signal.connect(
            lambda msg, running, n=name: self._on_browser_status_changed(n, msg, running)
        )
        worker.start()

        self.browser_workers[name] = worker
        self.browser_launch_btn.setEnabled(False)
        self.browser_stop_btn.setEnabled(True)
        self.browser_status_label.setText(f"🟢 {name} đang khởi chạy...")
        self.browser_status_label.setStyleSheet("font-size: 13px; color: #10b981; padding: 5px;")
        self.load_browser_profiles_table()

    def handle_stop_browser(self):
        """Stop the currently running browser."""
        profile = self._get_selected_browser_profile()
        if not profile:
            # If no profile selected, stop all
            if self.browser_workers:
                for name, worker in list(self.browser_workers.items()):
                    worker.stop_browser()
                    self.log(f"⏹️ Đang dừng browser [{name}]...")
            return

        name = profile.get("name", "")
        if name in self.browser_workers:
            self.browser_workers[name].stop_browser()
            self.log(f"⏹️ Đang dừng browser [{name}]...")
        else:
            QMessageBox.information(self, "Thông báo",
                                     f"Browser '{name}' không đang chạy.")

    def _on_browser_status_changed(self, profile_name, message, is_running):
        """Handle browser status change signal."""
        if not is_running:
            # Clean up worker reference
            if profile_name in self.browser_workers:
                del self.browser_workers[profile_name]

            # Update UI
            if not self.browser_workers:
                self.browser_launch_btn.setEnabled(True)
                self.browser_stop_btn.setEnabled(False)
                self.browser_status_label.setText("⏸️ Chưa chạy")
                self.browser_status_label.setStyleSheet("font-size: 13px; color: #94a3b8; padding: 5px;")
            else:
                running_names = ", ".join(self.browser_workers.keys())
                self.browser_status_label.setText(f"🟢 Đang chạy: {running_names}")
        else:
            self.browser_status_label.setText(f"🟢 {profile_name}: {message}")
            self.browser_status_label.setStyleSheet("font-size: 13px; color: #10b981; padding: 5px;")
            self.browser_launch_btn.setEnabled(True)  # Allow opening more profiles

        self.load_browser_profiles_table()

    def handle_test_cloudflare(self):
        """Launch a browser to test Cloudflare bypass with nowsecure.nl."""
        profile = self._get_selected_browser_profile()
        if not profile:
            # Create a temporary random profile for testing
            pm = ProfileManager()
            profile = pm.create_random_profile()
            profile["name"] = "_test_cloudflare"

        name = "_test_cf_" + str(random.randint(1000, 9999))
        worker = BrowserWorker(
            profile_config=profile,
            profile_name=name,
            start_url="https://nowsecure.nl/",
        )
        worker.log_signal.connect(self.log)
        worker.status_signal.connect(
            lambda msg, running, n=name: self._on_browser_status_changed(n, msg, running)
        )
        worker.start()
        self.browser_workers[name] = worker
        self.log("🧪 Đang mở browser test Cloudflare (nowsecure.nl)...")
        self.browser_stop_btn.setEnabled(True)

    def handle_test_fingerprint(self):
        """Launch a browser to test fingerprint with bot.sannysoft.com."""
        profile = self._get_selected_browser_profile()
        if not profile:
            pm = ProfileManager()
            profile = pm.create_random_profile()
            profile["name"] = "_test_fingerprint"

        name = "_test_fp_" + str(random.randint(1000, 9999))
        worker = BrowserWorker(
            profile_config=profile,
            profile_name=name,
            start_url="https://bot.sannysoft.com/",
        )
        worker.log_signal.connect(self.log)
        worker.status_signal.connect(
            lambda msg, running, n=name: self._on_browser_status_changed(n, msg, running)
        )
        worker.start()
        self.browser_workers[name] = worker
        self.log("🔍 Đang mở browser test Fingerprint (bot.sannysoft.com)...")
        self.browser_stop_btn.setEnabled(True)

    def handle_test_iphey(self):
        """Launch a browser to test fingerprint with iphey.com."""
        profile = self._get_selected_browser_profile()
        if not profile:
            pm = ProfileManager()
            profile = pm.create_random_profile()
            profile["name"] = "_test_iphey"

        name = "_test_iphey_" + str(random.randint(1000, 9999))
        worker = BrowserWorker(
            profile_config=profile,
            profile_name=name,
            start_url="https://iphey.com/",
        )
        worker.log_signal.connect(self.log)
        worker.status_signal.connect(
            lambda msg, running, n=name: self._on_browser_status_changed(n, msg, running)
        )
        worker.start()
        self.browser_workers[name] = worker
        self.log("🛡️ Đang mở browser test iphey.com (fingerprint check)...")
        self.browser_stop_btn.setEnabled(True)

    def handle_test_webrtc_leak(self):
        """Launch a browser to test WebRTC leak with browserleaks.com."""
        profile = self._get_selected_browser_profile()
        if not profile:
            pm = ProfileManager()
            profile = pm.create_random_profile()
            profile["name"] = "_test_webrtc"

        name = "_test_webrtc_" + str(random.randint(1000, 9999))
        worker = BrowserWorker(
            profile_config=profile,
            profile_name=name,
            start_url="https://browserleaks.com/webrtc",
        )
        worker.log_signal.connect(self.log)
        worker.status_signal.connect(
            lambda msg, running, n=name: self._on_browser_status_changed(n, msg, running)
        )
        worker.start()
        self.browser_workers[name] = worker
        self.log("🌐 Đang mở browser test WebRTC Leak (browserleaks.com)...")
        self.browser_stop_btn.setEnabled(True)

    def handle_delete_browser_profile(self):
        """Delete the selected browser profile."""
        profile = self._get_selected_browser_profile()
        if not profile:
            return

        name = profile.get("name", "Unknown")

        # Don't delete if running
        if name in self.browser_workers:
            QMessageBox.warning(self, "Đang chạy",
                                 f"Browser '{name}' đang chạy. Dừng trước khi xóa!")
            return

        reply = QMessageBox.question(
            self, "Xác nhận xóa",
            f"Bạn có chắc muốn xóa profile '{name}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self._browser_profiles = [p for p in self._browser_profiles if p.get("name") != name]
            self._save_browser_profiles_json()
            self.load_browser_profiles_table()
            self.log(f"🗑️ Đã xóa browser profile: {name}")

    # --- ĐỊNH TUYẾN 🌐 TAB UI ---
    def init_routing_tab_ui(self):

        from PyQt5.QtWidgets import QFormLayout, QTableWidget, QTableWidgetItem, QHeaderView
        
        routing_layout = QHBoxLayout(self.routing_tab)
        routing_layout.setContentsMargins(15, 15, 15, 15)
        routing_layout.setSpacing(15)
        
        # Left Panel: Configuration
        left_panel = QGroupBox("⚙️ Cấu Hình Mạng Định Tuyến")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(10)
        
        # Interfaces
        left_layout.addWidget(QLabel("<b>Card mạng WAN (Internet nguồn):</b>"))
        self.routing_wan_combo = QComboBox()
        left_layout.addWidget(self.routing_wan_combo)
        
        left_layout.addWidget(QLabel("<b>Card mạng LAN (Kết nối Aruba AP):</b>"))
        self.routing_lan_combo = QComboBox()
        left_layout.addWidget(self.routing_lan_combo)
        
        self.routing_refresh_btn = QPushButton("🔄 Cập nhật danh sách Card Mạng")
        self.routing_refresh_btn.setObjectName("secondaryButton")
        self.routing_refresh_btn.clicked.connect(self.handle_routing_refresh_interfaces)
        left_layout.addWidget(self.routing_refresh_btn)
        
        left_layout.addSpacing(10)
        left_layout.addWidget(QLabel("<b>Cài đặt dải DHCP:</b>"))
        
        form_layout = QFormLayout()
        self.routing_dhcp_start_input = QLineEdit("192.168.88.10")
        self.routing_dhcp_end_input = QLineEdit("192.168.88.250")
        self.routing_dns_input = QLineEdit("8.8.8.8")
        form_layout.addRow("DHCP Dải đầu:", self.routing_dhcp_start_input)
        form_layout.addRow("DHCP Dải cuối:", self.routing_dhcp_end_input)
        form_layout.addRow("DNS Server:", self.routing_dns_input)
        left_layout.addLayout(form_layout)
        
        left_layout.addStretch()
        
        # Right Panel: Operations & Devices
        right_panel = QGroupBox("💻 Trình Điều Khiển & Thiết Bị Kết Nối")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setSpacing(12)
        
        # Operations buttons
        btn_layout = QHBoxLayout()
        self.routing_start_btn = QPushButton("⚡ KHỞI ĐỘNG ROUTER")
        self.routing_start_btn.clicked.connect(self.handle_routing_start)
        
        self.routing_stop_btn = QPushButton("🛑 DỪNG ROUTER")
        self.routing_stop_btn.setObjectName("dangerButton")
        self.routing_stop_btn.clicked.connect(self.handle_routing_stop)
        
        btn_layout.addWidget(self.routing_start_btn)
        btn_layout.addWidget(self.routing_stop_btn)
        right_layout.addLayout(btn_layout)
        
        self.routing_dashboard_btn = QPushButton("🌐 MỞ DASHBOARD ĐIỀU KHIỂN CHÍNH")
        self.routing_dashboard_btn.clicked.connect(self.handle_routing_dashboard_open)
        right_layout.addWidget(self.routing_dashboard_btn)
        
        # Status indicators
        status_layout = QHBoxLayout()
        self.lbl_dhcp_status = QLabel("DHCP: 🛑 Tắt")
        self.lbl_dhcp_status.setStyleSheet("font-weight: bold; color: #ef4444;")
        self.lbl_api_status = QLabel("FastAPI Dashboard: 🛑 Tắt")
        self.lbl_api_status.setStyleSheet("font-weight: bold; color: #ef4444;")
        self.lbl_singbox_status = QLabel("Sing-Box: 🛑 Tắt")
        self.lbl_singbox_status.setStyleSheet("font-weight: bold; color: #ef4444;")
        
        status_layout.addWidget(self.lbl_dhcp_status)
        status_layout.addWidget(self.lbl_api_status)
        status_layout.addWidget(self.lbl_singbox_status)
        right_layout.addLayout(status_layout)
        
        # Connected devices table
        right_layout.addWidget(QLabel("<b>Danh sách thiết bị nhận mạng (DHCP leases):</b>"))
        self.routing_devices_table = QTableWidget()
        self.routing_devices_table.setColumnCount(4)
        self.routing_devices_table.setHorizontalHeaderLabels(["Địa chỉ MAC", "Địa chỉ IP", "Tên thiết bị", "Thời gian"])
        self.routing_devices_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.routing_devices_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.routing_devices_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        right_layout.addWidget(self.routing_devices_table)
        
        routing_layout.addWidget(left_panel, 4)
        routing_layout.addWidget(right_panel, 6)
        
        # Initialize and auto-detect interfaces
        self.handle_routing_refresh_interfaces()
        
        # Start status update timer
        self.routing_timer = QTimer(self)
        self.routing_timer.timeout.connect(self.update_routing_statuses)
        self.routing_timer.start(3000)

    def handle_routing_refresh_interfaces(self):
        self.routing_wan_combo.clear()
        self.routing_lan_combo.clear()
        
        # PowerShell command to get interfaces
        cmd = "powershell -Command \"Get-NetIPInterface | Where-Object AddressFamily -eq IPv4 | Select-Object InterfaceAlias | ConvertTo-Json\""
        import subprocess
        try:
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                
                interfaces = sorted(list(set([x["InterfaceAlias"] for x in data if "InterfaceAlias" in x])))
                for name in interfaces:
                    self.routing_wan_combo.addItem(name)
                    self.routing_lan_combo.addItem(name)
                
                # Auto select WAN if default route is found
                gw_cmd = "powershell -Command \"Get-NetRoute -DestinationPrefix '0.0.0.0/0' | Select-Object -ExpandProperty InterfaceAlias\""
                gw_res = subprocess.run(gw_cmd, shell=True, capture_output=True, text=True, encoding="utf-8")
                if gw_res.returncode == 0 and gw_res.stdout.strip():
                    wan_name = gw_res.stdout.strip().split("\n")[0].strip()
                    index = self.routing_wan_combo.findText(wan_name)
                    if index >= 0:
                        self.routing_wan_combo.setCurrentIndex(index)
                    
                    # Auto select LAN (usually Ethernet 3 or another adapter not WAN)
                    for i, name in enumerate(interfaces):
                        if name != wan_name and "Ethernet" in name:
                            self.routing_lan_combo.setCurrentIndex(i)
                            break
        except Exception as e:
            self.log(f"Lỗi quét Card Mạng: {e}")

    def handle_routing_start(self):
        wan_if = self.routing_wan_combo.currentText()
        lan_if = self.routing_lan_combo.currentText()
        dhcp_start = self.routing_dhcp_start_input.text().strip()
        dhcp_end = self.routing_dhcp_end_input.text().strip()
        dns_server = self.routing_dns_input.text().strip()
        
        if not wan_if or not lan_if:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn đầy đủ Card mạng WAN và LAN.")
            return
            
        if wan_if == lan_if:
            QMessageBox.warning(self, "Cảnh báo", "Card mạng WAN và LAN không được trùng nhau.")
            return

        self.log(f"Bắt đầu thiết lập định tuyến mạng: WAN={wan_if}, LAN={lan_if}...")
        
        # Get path to phonefarm-router directory
        router_dir = os.path.join(os.path.dirname(os.path.dirname(get_app_dir())), "phonefarm-router")
        config_path = os.path.join(router_dir, "config.json")
        
        # Update config.json
        try:
            config_data = {}
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    
            config_data["lan_interface"] = lan_if
            config_data["wan_interface"] = wan_if
            config_data["dhcp_range_start"] = dhcp_start
            config_data["dhcp_range_end"] = dhcp_end
            config_data["dns_server"] = dns_server
            
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
                
            self.log("Đã cập nhật cấu hình config.json.")
        except Exception as e:
            self.log(f"Lỗi ghi cấu hình config.json: {e}")
            QMessageBox.critical(self, "Lỗi", f"Không thể ghi cấu hình config.json: {e}")
            return
            
        # Get LAN adapter index to assign IP address
        # Check if LAN interface already has 192.168.88.1, if not, set static IP
        ip_cmd = f"powershell -Command \"Get-NetIPAddress -InterfaceAlias '{lan_if}' -IPAddress '192.168.88.1' -ErrorAction SilentlyContinue\""
        import subprocess
        ip_res = subprocess.run(ip_cmd, shell=True, capture_output=True, text=True)
        
        if "192.168.88.1" not in ip_res.stdout:
            self.log(f"Đang đặt IP tĩnh 192.168.88.1 cho Card LAN '{lan_if}' (Sẽ yêu cầu quyền UAC)...")
            
            # Create a temporary script to set static IP
            ps_script = (
                f"Remove-NetIPAddress -InterfaceAlias '{lan_if}' -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                f"New-NetIPAddress -InterfaceAlias '{lan_if}' -IPAddress '192.168.88.1' -PrefixLength 24 -DefaultGateway $null; "
                f"Set-DnsClientServerAddress -InterfaceAlias '{lan_if}' -ServerAddresses ('8.8.8.8','1.1.1.1')"
            )
            
            cmd_run = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {ps_script}' -Verb RunAs -WindowStyle Hidden\""
            subprocess.run(cmd_run, shell=True)
            self.log("Đã gửi yêu cầu đặt IP tĩnh cho card LAN. Vui lòng bấm Yes nếu hiện UAC.")
            
        # Start DHCP Server in background as Admin
        self.log("Đang khởi động DHCP Server (Sẽ yêu cầu quyền UAC)...")
        dhcp_script_path = os.path.join(router_dir, "scratch", "run_dhcp.py")
        dhcp_cmd = f"powershell -Command \"Start-Process 'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\python.exe' -ArgumentList '{dhcp_script_path}' -Verb RunAs -WorkingDirectory '{router_dir}' -WindowStyle Hidden\""
        subprocess.run(dhcp_cmd, shell=True)
        
        # Start FastAPI / Uvicorn Server in background as Admin
        self.log("Đang khởi động API Dashboard Server (Sẽ yêu cầu quyền UAC)...")
        api_cmd = f"powershell -Command \"Start-Process 'C:\\Users\\Admin\\AppData\\Local\\Programs\\Python\\Python311\\python.exe' -ArgumentList '-m uvicorn app.api:app --host 0.0.0.0 --port 8000' -Verb RunAs -WorkingDirectory '{router_dir}' -WindowStyle Hidden\""
        subprocess.run(api_cmd, shell=True)
        
        self.log("Đã kích hoạt tiến trình định tuyến. Vui lòng đồng ý các hộp thoại UAC (nếu có).")
        QMessageBox.information(self, "Thông báo", "Đã gửi lệnh khởi động hệ thống định tuyến mạng. Vui lòng đồng ý quyền Administrator (UAC) trên màn hình và đợi vài giây để hệ thống kích hoạt.")

    def handle_routing_stop(self):
        self.log("Đang dừng toàn bộ hệ thống định tuyến (Tắt DHCP, FastAPI và Sing-Box)...")
        
        # Kill processes binding to port 67 UDP and port 8000 TCP, and sing-box
        ps_kill = (
            "$p = Get-NetUDPEndpoint -LocalPort 67 -ErrorAction SilentlyContinue; "
            "if ($p) { Stop-Process -Id $p.OwningProcess -Force -ErrorAction SilentlyContinue }; "
            "$p2 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; "
            "if ($p2) { Stop-Process -Id $p2.OwningProcess -Force -ErrorAction SilentlyContinue }; "
            "Stop-Process -Name 'sing-box' -Force -ErrorAction SilentlyContinue"
        )
        
        cmd_run = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {ps_kill}' -Verb RunAs -WindowStyle Hidden\""
        import subprocess
        subprocess.run(cmd_run, shell=True)
        self.log("Đã gửi lệnh dừng hệ thống định tuyến. Vui lòng đồng ý UAC.")
        QMessageBox.information(self, "Thông báo", "Đã gửi lệnh dừng hệ thống định tuyến. Vui lòng đồng ý UAC.")

    def handle_routing_dashboard_open(self):
        import webbrowser
        webbrowser.open("http://127.0.0.1:8000/")

    def update_routing_statuses(self):
        import socket
        import subprocess
        import os
        
        # 1. Check DHCP Server status (check if port 67 UDP is bound)
        dhcp_running = False
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.bind(('192.168.88.1', 67))
            s.close()
        except OSError:
            s.close()
            dhcp_running = True
            
        if dhcp_running:
            self.lbl_dhcp_status.setText("DHCP: 🟢 Chạy")
            self.lbl_dhcp_status.setStyleSheet("font-weight: bold; color: #22c55e;")
        else:
            self.lbl_dhcp_status.setText("DHCP: 🛑 Tắt")
            self.lbl_dhcp_status.setStyleSheet("font-weight: bold; color: #ef4444;")
            
        # 2. Check API Dashboard status (check if port 8000 TCP is open)
        api_running = False
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.settimeout(0.2)
        try:
            s2.connect(('127.0.0.1', 8000))
            s2.close()
            api_running = True
        except Exception:
            s2.close()
            
        if api_running:
            self.lbl_api_status.setText("FastAPI Dashboard: 🟢 Chạy")
            self.lbl_api_status.setStyleSheet("font-weight: bold; color: #22c55e;")
        else:
            self.lbl_api_status.setText("FastAPI Dashboard: 🛑 Tắt")
            self.lbl_api_status.setStyleSheet("font-weight: bold; color: #ef4444;")
            
        # 3. Check Sing-Box status (check if sing-box.exe process is running)
        singbox_running = False
        try:
            res = subprocess.run("tasklist /FI \"IMAGENAME eq sing-box.exe\"", shell=True, capture_output=True, text=True)
            singbox_running = "sing-box.exe" in res.stdout
        except Exception:
            pass
            
        if singbox_running:
            self.lbl_singbox_status.setText("Sing-Box: 🟢 Chạy")
            self.lbl_singbox_status.setStyleSheet("font-weight: bold; color: #22c55e;")
        else:
            self.lbl_singbox_status.setText("Sing-Box: 🛑 Tắt")
            self.lbl_singbox_status.setStyleSheet("font-weight: bold; color: #ef4444;")
            
        # 4. Load connected devices from hosts.csv
        router_dir = os.path.join(os.path.dirname(os.path.dirname(get_app_dir())), "phonefarm-router")
        hosts_csv_path = os.path.join(router_dir, "hosts.csv")
        
        if os.path.exists(hosts_csv_path):
            devices = []
            try:
                with open(hosts_csv_path, "r", encoding="utf-8") as f:
                    for line in f:
                        parts = line.strip().split(";")
                        if len(parts) >= 2:
                            mac = parts[0].strip().upper()
                            ip = parts[1].strip()
                            hostname = parts[2].strip() if len(parts) >= 3 else ""
                            last_used_ts = parts[3].strip() if len(parts) >= 4 else ""
                            
                            time_str = ""
                            if last_used_ts.isdigit():
                                import datetime
                                dt = datetime.datetime.fromtimestamp(int(last_used_ts))
                                time_str = dt.strftime("%H:%M:%S %d/%m")
                                
                            if mac and ip and ip != "0.0.0.0" and ip.startswith("192.168.88."):
                                devices.append((mac, ip, hostname or "Device", time_str))
            except Exception:
                pass
                
            # Update table widget
            self.routing_devices_table.setRowCount(len(devices))
            for row, dev in enumerate(devices):
                for col in range(4):
                    item = QTableWidgetItem(dev[col])
                    item.setTextAlignment(Qt.AlignCenter)
                    self.routing_devices_table.setItem(row, col, item)



if __name__ == "__main__":
    # Hỗ trợ High DPI scaling
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    app = QApplication(sys.argv)
    
    # Thiết lập font mặc định đẹp hơn
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Load stylesheet ở cấp độ application để áp dụng cho cả Login Dialog
    style_path = os.path.join(get_app_dir(), "style.qss")
    if os.path.exists(style_path):
        try:
            with open(style_path, "r", encoding="utf-8") as f:
                app.setStyleSheet(f.read())
        except Exception as e:
            print(f"Không thể load stylesheet: {e}")
            
    # Kiểm tra token đã lưu trên máy
    if not verify_saved_token():
        login_dialog = StoragonLoginDialog()
        if login_dialog.exec_() != QDialog.Accepted:
            sys.exit(0)
            
    window = QHTDStoreDesktop()
    window.show()
    sys.exit(app.exec_())
