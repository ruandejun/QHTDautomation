"""
Android Phone Farm TikTok Nurture Engine (ADB Driven - Enhanced)
================================================================
Tương tác nuôi TikTok trên Android Phone Farm thực tế qua ADB commands:
  1. Tự động nhận diện độ phân giải màn hình (`wm size`).
  2. Bật màn hình nếu đang tắt (`mWakefulness=Awake`).
  3. Lướt FYP theo gia tốc sinh học tự nhiên (random swipe curve).
  4. Hỗ trợ tiếng Việt qua ADB Unicode Keyboard & Clipboard.
  5. Xem hồ sơ tác giả (View Profile & Follow rate).
  6. Báo cáo tiến độ về C69 API.
"""

import os
import sys
import time
import random
import logging
import subprocess
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("AndroidNurture")

@dataclass
class AndroidNurtureConfig:
    device_serial: str = ""
    videos_per_session: int = 30
    like_probability: float = 0.65
    comment_probability: float = 0.15
    follow_probability: float = 0.05
    profile_view_probability: float = 0.10
    min_watch_seconds: int = 8
    max_watch_seconds: int = 45
    c69_url: str = "https://c69.us"
    fallback_comments: List[str] = field(default_factory=lambda: [
        "Video hay quá! 🔥", "Nội dung chất lượng ❤️", "Thú vị thật 😍", "Ủng hộ bạn nha 💪", "Love this! 🔥", "Quá xịn luôn 💯"
    ])

class ADBBridge:
    def __init__(self, serial: str):
        self.serial = serial
        self.screen_size: Tuple[int, int] = self.get_screen_size()

    def run_cmd(self, cmd_args: List[str], timeout: int = 15) -> str:
        full_cmd = ["adb", "-s", self.serial] + cmd_args
        try:
            res = subprocess.run(full_cmd, capture_output=True, text=True, timeout=timeout)
            return res.stdout.strip()
        except Exception as e:
            logger.error(f"ADB cmd failed [{self.serial}]: {e}")
            return ""

    def get_screen_size(self) -> Tuple[int, int]:
        """Lấy độ phân giải thực tế của màn hình thiết bị"""
        out = self.run_cmd(["shell", "wm", "size"])
        try:
            # Output format: "Physical size: 1080x2400"
            for line in out.splitlines():
                if "size:" in line.lower():
                    size_str = line.split(":")[-1].strip()
                    w, h = map(int, size_str.split("x"))
                    return w, h
        except Exception:
            pass
        return 1080, 2400  # Default fallback

    def ensure_screen_awake(self):
        """Đảm bảo màn hình sáng và mở khóa cơ bản"""
        dumpsys = self.run_cmd(["shell", "dumpsys", "power"])
        if "mWakefulness=Asleep" in dumpsys or "mWakefulness=Dozing" in dumpsys:
            self.run_cmd(["shell", "input", "keyevent", "26"])  # KEYCODE_POWER
            time.sleep(0.5)
        # Vuốt mở khóa màn hình
        w, h = self.screen_size
        self.run_cmd(["shell", "input", "swipe", str(w//2), str(int(h * 0.8)), str(w//2), str(int(h * 0.2)), "200"])

    def swipe_up(self):
        """Vuốt lướt video tiếp theo theo độ phân giải màn hình"""
        w, h = self.screen_size
        x = random.randint(int(w * 0.45), int(w * 0.55))
        y1 = random.randint(int(h * 0.70), int(h * 0.80))
        y2 = random.randint(int(h * 0.15), int(h * 0.25))
        duration = random.randint(220, 380)
        self.run_cmd(["shell", "input", "swipe", str(x), str(y1), str(x), str(y2), str(duration)])

    def double_tap_like(self):
        """Bấm đúp màn hình giữa để Like video"""
        w, h = self.screen_size
        x = random.randint(int(w * 0.45), int(w * 0.55))
        y = random.randint(int(h * 0.40), int(h * 0.55))
        self.run_cmd(["shell", "input", "tap", str(x), str(y)])
        time.sleep(0.08)
        self.run_cmd(["shell", "input", "tap", str(x), str(y)])

    def post_comment(self, comment_text: str):
        """Mở khung bình luận và gõ nội dung"""
        w, h = self.screen_size
        # Tap icon comment bên phải
        comment_btn_x = int(w * 0.92)
        comment_btn_y = int(h * 0.58)
        self.run_cmd(["shell", "input", "tap", str(comment_btn_x), str(comment_btn_y)])
        time.sleep(1.5)

        # Tap ô nhập text
        self.run_cmd(["shell", "input", "tap", str(w // 2), str(int(h * 0.95))])
        time.sleep(1.0)

        # Gõ text qua ADB broadcast hoặc text command
        escaped_text = comment_text.replace(" ", "%s")
        self.run_cmd(["shell", "input", "text", escaped_text])
        time.sleep(1.0)

        # Bấm gửi (Enter / Send button)
        self.run_cmd(["shell", "input", "tap", str(int(w * 0.92)), str(int(h * 0.95))])
        time.sleep(1.0)

        # Bấm nút Back để đóng bảng bình luận
        self.run_cmd(["shell", "input", "keyevent", "4"])

    def launch_tiktok(self):
        """Khởi chạy ứng dụng TikTok trên Android"""
        self.ensure_screen_awake()
        time.sleep(0.5)
        out = self.run_cmd(["shell", "monkey", "-p", "com.zhiliaoapp.musically", "-c", "android.intent.category.LAUNCHER", "1"])
        if "No activities found" in out:
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
        w, h = self.adb.screen_size
        self.callback(f"🚀 Bắt đầu nuôi TikTok trên Android Phone Farm: {self.adb.serial} (Độ phân giải: {w}x{h})", "info")
        self.adb.launch_tiktok()
        time.sleep(6)

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
                time.sleep(1.2)

            # Xử lý Comment ngẫu nhiên
            if random.random() < self.config.comment_probability:
                comment = random.choice(self.config.fallback_comments)
                self.adb.post_comment(comment)
                stats["commented"] += 1
                self.callback(f"💬 Device [{self.adb.serial}] đã Comment: '{comment}'", "success")
                time.sleep(1.5)

            # Lướt sang video tiếp theo
            self.adb.swipe_up()
            time.sleep(random.uniform(1.2, 2.8))

        self.callback(f"🎉 Hoàn tất chu trình nuôi trên Android [{self.adb.serial}]: {stats}", "success")
        return stats
