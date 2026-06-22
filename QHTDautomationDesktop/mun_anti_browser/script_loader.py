"""
MunAntiBrowser - Script Loader
================================
Loads and composes JavaScript injection scripts from files.
Replaces inline JS strings from mybrowser.py with file-based approach.
"""

import json
import os
from typing import Dict, Any, Optional


class ScriptLoader:
    """
    Loads JS injection scripts from the inject_scripts/ directory
    and composes them with profile-specific template variables.
    """

    def __init__(self, scripts_dir: Optional[str] = None):
        if scripts_dir is None:
            scripts_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "inject_scripts",
            )
        self.scripts_dir = scripts_dir
        self._cache: Dict[str, str] = {}

    def load_script(self, name: str) -> str:
        """
        Load a JS script by name (without .js extension).

        Args:
            name: Script name (e.g., 'canvas', 'audio', 'webgl')

        Returns:
            Raw JS source code as string.
        """
        if name in self._cache:
            return self._cache[name]

        filepath = os.path.join(self.scripts_dir, f"{name}.js")
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Inject script not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            source = f.read()

        self._cache[name] = source
        return source

    def clear_cache(self):
        """Clear the script cache."""
        self._cache.clear()

    def compose_injection(self, profile_config: Dict[str, Any]) -> str:
        """
        Compose all injection scripts into a single JS string,
        replacing template variables with profile-specific values.

        Args:
            profile_config: Dictionary with profile configuration containing:
                - profile_user_agent (str)
                - profile_canvas (str/dict): JSON string or dict with r,g,b,a
                - profile_audio (str/dict): JSON string or dict with audio params
                - profile_webgl (str/dict): JSON string or dict with WebGL params
                - profile_webrtc (bool/int): Whether to disable WebRTC
                - profile_rects (float/str): ClientRect offset or 'Noise'
                - profile_font (str): JSON string of font list
                - profile_name (str): Profile name for status bar

        Returns:
            Combined JS injection string.
        """
        import random
        import hashlib

        # Extract stable profile_id
        profile_id = profile_config.get("id", 0)
        try:
            profile_id = int(profile_id)
        except (ValueError, TypeError):
            profile_id = 0

        if not profile_id:
            profile_name = profile_config.get("name", "")
            if profile_name:
                h = hashlib.md5(profile_name.encode("utf-8")).hexdigest()
                profile_id = int(h[:8], 16) % 1000000
            else:
                profile_id = random.randint(100000, 999999)

        parts = []

        # 1. CloudFlare bypass (always injected first)
        cf_script = self.load_script("cloudflare_bypass").replace("{{plugins_seed}}", str(profile_id))
        parts.append(cf_script)

        # 2. User Agent
        if profile_config.get("profile_user_agent"):
            ua_script = self.load_script("user_agent")
            ua_script = ua_script.replace(
                "{{UserAgent}}", profile_config["profile_user_agent"]
            )
            parts.append(ua_script)

        # 2. WebRTC protection (ALWAYS injected - critical for IP leak prevention)
        parts.append(self.load_script("webrtc"))

        # 4. Canvas
        if profile_config.get("profile_canvas"):
            canvas_script = self.load_script("canvas")
            canvas_data = profile_config["profile_canvas"]
            if isinstance(canvas_data, str):
                canvas_data = json.loads(canvas_data)
            canvas_script = canvas_script.replace(
                "{{canvas_shift}}", json.dumps(canvas_data)
            )
            parts.append(canvas_script)

        # 5. Audio
        if profile_config.get("profile_audio"):
            audio_script = self.load_script("audio")
            audio_data = profile_config["profile_audio"]
            if isinstance(audio_data, str):
                audio_data = json.loads(audio_data)
            for key, value in audio_data.items():
                audio_script = audio_script.replace(
                    "{{" + key + "}}", json.dumps(value) if isinstance(value, dict) else str(value)
                )
            parts.append(audio_script)

        # 6. WebGL
        if profile_config.get("profile_webgl"):
            webgl_script = self.load_script("webgl")
            webgl_data = profile_config["profile_webgl"]
            if isinstance(webgl_data, str):
                webgl_data = json.loads(webgl_data)
            for key, value in webgl_data.items():
                webgl_script = webgl_script.replace(
                    "{{" + key + "}}", str(value)
                )
            parts.append(webgl_script)

        # 7. ClientRects
        if profile_config.get("profile_rects"):
            rects_script = self.load_script("rects")
            rects_value = profile_config["profile_rects"]
            if rects_value == "Noise":
                rects_value = round(random.uniform(0.2, 0.35), 5)
            rects_script = rects_script.replace(
                "{{rects}}", str(rects_value)
            )
            parts.append(rects_script)

        # 8. Fonts
        if profile_config.get("profile_font"):
            fonts_script = self.load_script("fonts")
            font_data = profile_config["profile_font"]
            if isinstance(font_data, list):
                font_data = json.dumps(font_data)
            fonts_script = fonts_script.replace("{{fonts}}", font_data)
            parts.append(fonts_script)

        # 9. Network (always)
        net_script = self.load_script("network").replace("{{plugins_seed}}", str(profile_id))
        parts.append(net_script)

        # 10. Battery (always)
        bat_script = self.load_script("battery").replace("{{plugins_seed}}", str(profile_id))
        parts.append(bat_script)

        # 11. Navigator extra (always)
        nav_script = self.load_script("navigator_extra").replace("{{plugins_seed}}", str(profile_id))
        parts.append(nav_script)

        # 12. Speech synthesis (always)
        parts.append(self.load_script("speech_synthesis"))

        # 13. Media devices (always)
        parts.append(self.load_script("media_devices"))

        # 14. Ping block (always)
        parts.append(self.load_script("ping"))

        return "\n\n".join(parts)
