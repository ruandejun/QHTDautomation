"""
MunAntiBrowser - Profile Manager
==================================
Creates, loads, and manages browser fingerprint profiles.
Ported from mybrowser.py create_random_profile() (lines 2369-2561).
"""

import json
import logging
import random
from typing import Dict, Any, Optional

from . import fingerprint_data as fpdata

logger = logging.getLogger(__name__)


class ProfileManager:
    """
    Manages browser fingerprint profiles.
    Can create random profiles or load profiles from API/local storage.
    """

    def create_random_profile(
        self,
        socks5: str = "",
        proxy: str = "",
        proxy_username: str = "",
        proxy_password: str = "",
        phone_os: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate a random browser fingerprint profile.

        Args:
            socks5: SOCKS5 proxy string
            proxy: HTTP/HTTPS proxy string
            proxy_username: Proxy auth username
            proxy_password: Proxy auth password
            phone_os: "iPhone", "Android", or None for desktop

        Returns:
            Profile configuration dictionary.
        """
        profile = {}

        # OS selection
        if phone_os:
            os_type = phone_os
        else:
            os_type = random.choice(fpdata.DESKTOP_OS_LIST)

        # User Agent & Resolution
        ua, os_name, resolution, cpu = fpdata.generate_user_agent(os_type, phone_os)
        profile["profile_user_agent"] = ua
        profile["profile_os"] = os_name
        profile["profile_resolution"] = resolution
        profile["profile_cpu"] = cpu

        # Geo/Timezone
        profile["profile_geo"] = 2
        profile["profile_time_zone"] = 2

        # WebRTC
        profile["profile_webrtc"] = 2

        # Proxy
        profile["profile_socks5_details"] = socks5
        profile["profile_proxy_details"] = proxy
        profile["profile_proxy_username"] = proxy_username
        profile["profile_proxy_password"] = proxy_password
        profile["profile_proxy_type"] = 2

        # Audio fingerprint
        audio_data = fpdata.generate_audio_fingerprint()
        profile["profile_audio"] = json.dumps(audio_data)

        # Canvas fingerprint
        canvas_data = fpdata.generate_canvas_fingerprint()
        profile["profile_canvas"] = json.dumps(canvas_data)

        # WebGL fingerprint
        webgl_data = fpdata.generate_webgl_fingerprint(phone_os, os_name)
        profile["profile_webgl"] = json.dumps(webgl_data)
        profile["profile_vendor"] = webgl_data.get("37445", "")
        profile["profile_renderer"] = webgl_data.get("37446", "")

        # ClientRects
        profile["profile_rects"] = fpdata.generate_rects_offset()

        # Fonts
        profile["profile_font"] = json.dumps(fpdata.generate_font_list())

        # Profile name
        profile["profile_name"] = ""
        profile["profile_start_url"] = ""
        profile["id"] = random.randint(100000, 999999)

        logger.info(
            f"Created random profile: OS={os_name}, "
            f"UA={ua[:50]}..., Resolution={resolution}"
        )
        return profile

    @staticmethod
    def from_api_data(api_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert API response data to profile config format.
        Used when loading profiles from the server.

        Args:
            api_data: Raw profile data from API.

        Returns:
            Normalized profile configuration dictionary.
        """
        # Map API field names to internal names
        field_map = {
            "profile_user_agent": "profile_user_agent",
            "profile_os": "profile_os",
            "profile_resolution": "profile_resolution",
            "profile_cpu": "profile_cpu",
            "profile_time_zone": "profile_time_zone",
            "profile_geo": "profile_geo",
            "profile_webrtc": "profile_webrtc",
            "profile_canvas": "profile_canvas",
            "profile_audio": "profile_audio",
            "profile_webgl": "profile_webgl",
            "profile_rects": "profile_rects",
            "profile_font": "profile_font",
            "profile_name": "profile_name",
            "profile_start_url": "profile_start_url",
            "profile_socks5_details": "profile_socks5_details",
            "profile_proxy_details": "profile_proxy_details",
            "profile_proxy_username": "profile_proxy_username",
            "profile_proxy_password": "profile_proxy_password",
            "id": "id",
        }

        profile = {}
        for api_key, internal_key in field_map.items():
            profile[internal_key] = api_data.get(api_key, "")

        # Ensure defaults
        profile.setdefault("profile_socks5_details", "")
        profile.setdefault("profile_proxy_details", "")
        profile.setdefault("profile_proxy_username", "")
        profile.setdefault("profile_proxy_password", "")
        profile.setdefault("profile_name", "")
        profile.setdefault("profile_start_url", "")
        profile.setdefault("id", 0)

        return profile
