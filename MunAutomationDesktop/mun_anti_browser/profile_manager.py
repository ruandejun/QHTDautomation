import random
import json
from typing import Dict, Any, Optional
from .fingerprint_data import generate_audio_fingerprint, generate_canvas_fingerprint, generate_webgl_fingerprint, generate_rects_offset, generate_font_list, generate_user_agent

class ProfileManager:
    def __init__(self):
        self.profiles = []

    def create_random_profile(
        self,
        proxy: Optional[str] = None,
        os_type: str = "Window",
        phone_os: Optional[str] = None,
        socks5: Optional[str] = None,
        proxy_username: str = "",
        proxy_password: str = ""
    ) -> Dict[str, Any]:
        """Tạo profile ngẫu nhiên hoàn chỉnh"""
        # Nếu truyền socks5 thì ưu tiên gán proxy
        if socks5 and not proxy:
            proxy = socks5
        # Mặc định tạo Desktop profile (Window/Mac) để đồng nhất với Chrome binary trên desktop
        # Tránh lỗi OS mismatch khi UA là mobile nhưng platform là desktop.


        # Generate base info
        ua, device_name, resolution, cpu = generate_user_agent(os_type, phone_os)
        audio = generate_audio_fingerprint()
        canvas = generate_canvas_fingerprint()
        webgl = generate_webgl_fingerprint(phone_os, os_type)
        rects = generate_rects_offset()
        fonts = generate_font_list()

        profile = {
            "id": random.randint(10000, 99999),
            "name": f"Profile_{random.randint(1000, 9999)}",
            "profile_os": os_type,
            "profile_user_agent": ua,
            "profile_resolution": resolution,
            "profile_cpu": cpu,
            "profile_audio": audio,
            "profile_canvas": canvas,
            "profile_webgl": webgl,
            "profile_rects": rects,
            "profile_font": fonts,
            "profile_start_url": "https://cu.c69.us",
            "proxy": proxy or "",
            "proxy_type": "socks5",
            "profile_vendor": webgl.get("37446", "Google Inc."),
            "profile_renderer": webgl.get("37445", "Google Inc."),
        }

        # Add server_id if exists
        if random.random() > 0.7:
            profile["server_id"] = random.randint(100000, 999999)

        return profile

    def get_profile(self, profile_id: int) -> Optional[Dict[str, Any]]:
        for p in self.profiles:
            if p.get("id") == profile_id:
                return p
        return None

    def list_profiles(self, limit: int = 10) -> list:
        return [self.create_random_profile() for _ in range(limit)]
