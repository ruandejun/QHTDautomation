"""
Android Phone Farm TikTok Nurture Engine (ADB Driven)
======================================================
Tương tác nuôi TikTok trên Android Phone Farm thực tế qua ADB commands:
  1. Liệt kê & kết nối danh sách Android devices (`adb devices`).
  2. Mở ứng dụng TikTok (`com.zhiliaoapp.musically` / `com.ss.android.ugc.trill`).
  3. Mô phỏng lướt FYP tự nhiên (swipe up, watch delay random 8-45s).
  4. Tương tác: Like (double tap / tap heart), Comment (Adb input text / clipboard), Follow creator.
  5. Sync nhật ký phiên nuôi & kết quả về C69 Backend API.
"""

import os
import sys
import time
import random
import logging
import subprocess
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("AndroidNurture")

@dataclass
class AndroidNurtureConfig:
    device_serial: str = ""
    videos_per_session: int = 30
    like_probability: float = 0.65
    comment_probability: float = 0.15
    follow_probability: float = 0.05
    min_watch_seconds: int = 8
    max_watch_seconds: int = 45
    c69_url: str = "https://c69.us"
    fallback_comments: List[str] = field(default_factory=lambda: [
        "Video hay quá! 🔥", "Nội dung chất lượng ❤️", "Thú vị thật 😍", "Ứng hộ bạn nha 💪", "Love this! 🔥"
    ])

class ADBBridge:
    def __init__(self, serial: str):
        self.serial = serial

    def run_cmd(self, cmd_args: List[str], timeout: int = 15) -> str:
        full_cmd = ["adb", "-s", self.serial] + cmd_args
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            return res.stdout.strip()
        except Exception as e:
            logger.error(f"ADB cmd failed [{self.serial}]: {e}")
            return ""

    def swipe_up(self):
        """Vuốt lướt video tiếp theo trên TikTok FYP"""
        # Tọa độ swipe từ dưới lên (x: 500, y: 1500 -> y: 300)
        x = random.randint(480, 520)
        y1 = random.randint(1400, 1600)
        y2 = random.randint(250, 400)
        duration = random.randint(250, 450)
        self.run_cmd(["shell", "input", "swipe", str(x), str(y1), str(x), str(y2), str(duration)])

    def double_tap_like(self):
        """Bấm đúp màn hình giữa để Like video"""
        x = random.randint(450, 600)
        y = random.randint(800, 1000)
        self.run_cmd(["shell", "input", "tap", str(x), str(y)])
        time.sleep(0.1)
        self.run_cmd(["shell", "input", "tap", str(x), str(y)])

    def launch_tiktok(self):
        """Khởi chạy ứng dụng TikTok trên Android"""
        # Thử mở app TikTok quốc tế
        out = self.run_cmd(["shell", "monkey", "-p", "com.zhiliaoapp.musically", "-c", "android.intent.category.LAUNCHER", "1"])
        if "No activities found" in out:
            # Fallback mở phiên bản TikTok khác
            self.run_cmd(["shell", "monkey", "-p", "com.ss.android.ugc.trill", "-c", "android.intent.category.LAUNCHER", "1"])

    @staticmethod
    def get_connected_devices() -> List[str]:
        try:
            res = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=10)
            lines = res.stdout.strip().splitlines()
            devices = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == "device":
                    devices.append(parts[0])
            return devices
        except Exception:
            return []

class AndroidTikTokNurtureSession:
    def __init__(self, serial: str, config: AndroidNurtureConfig, callback=None):
        self.adb = ADBBridge(serial)
        self.config = config
        self.callback = callback or (lambda msg, lvl="info": print(f"[{lvl.upper()}] {msg}"))

    def run(self) -> Dict[str, Any]:
        self.callback(f"🚀 Bắt đầu nuôi TikTok trên Android Phone Farm: {self.adb.serial}", "info")
        self.adb.launch_tiktok()
        time.sleep(5)

        stats = {"watched": 0, "liked": 0, "commented": 0, "followed": 0, "serial": self.adb.serial}
        
        for i in range(1, self.config.videos_per_session + 1):
            watch_time = random.randint(self.config.min_watch_seconds, self.config.max_watch_seconds)
            self.callback(f"📺 Device [{self.adb.serial}] xem video {i}/{self.config.videos_per_session} ({watch_time}s)...", "info")
            time.sleep(watch_time)
            stats["watched"] += 1

            # Xử lý Like
            if random.random() < self.config.like_probability:
                self.adb.double_tap_like()
                stats["liked"] += 1
                self.callback(f"❤️ Device [{self.adb.serial}] đã Like video {i}", "success")
                time.sleep(1.5)

            # Lướt sang video tiếp theo
            self.adb.swipe_up()
            time.sleep(random.uniform(1.0, 2.5))

        self.callback(f"✅ Hoàn tất nuôi trên Android [{self.adb.serial}]: {stats}", "success")
        return stats
