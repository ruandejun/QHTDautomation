import random
import json
import os
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

    def get_or_create_named_profile(
        self,
        name: str,
        profile_os: str = "Window",
        proxy: Optional[str] = None,
        save_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """Tạo mới hoặc lấy profile cố định theo tên để dùng lại"""
        clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name.lower())
        if save_dir:
            profile_file = os.path.join(save_dir, f"{clean_name}_config.json")
            if os.path.exists(profile_file):
                try:
                    with open(profile_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["name"] = name
                        return data
                except Exception:
                    pass

        profile = self.create_random_profile(proxy=proxy, os_type=profile_os)
        profile["id"] = clean_name
        profile["name"] = name

        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            profile_file = os.path.join(save_dir, f"{clean_name}_config.json")
            try:
                with open(profile_file, "w", encoding="utf-8") as f:
                    json.dump(profile, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

        return profile

    def get_profile(self, profile_id: int) -> Optional[Dict[str, Any]]:
        for p in self.profiles:
            if p.get("id") == profile_id:
                return p
        return None

    def list_profiles(self, limit: int = 10) -> list:
        return [self.create_random_profile() for _ in range(limit)]
