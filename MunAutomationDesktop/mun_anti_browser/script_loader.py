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
            from . import fingerprint_data as fpdata
            canvas_script = self.load_script("canvas")
            canvas_data = profile_config["profile_canvas"]
            if isinstance(canvas_data, str):
                try:
                    canvas_data = json.loads(canvas_data)
                except Exception:
                    canvas_data = None
            if not isinstance(canvas_data, dict) or not canvas_data:
                canvas_data = fpdata.generate_canvas_fingerprint()
            canvas_script = canvas_script.replace(
                "{{canvas_shift}}", json.dumps(canvas_data)
            )
            parts.append(canvas_script)

        # 5. Audio
        if profile_config.get("profile_audio"):
            from . import fingerprint_data as fpdata
            audio_script = self.load_script("audio")
            audio_data = profile_config["profile_audio"]
            if isinstance(audio_data, str):
                try:
                    audio_data = json.loads(audio_data)
                except Exception:
                    audio_data = None
            if not isinstance(audio_data, dict) or not audio_data:
                audio_data = fpdata.generate_audio_fingerprint()
            for key, value in audio_data.items():
                audio_script = audio_script.replace(
                    "{{" + key + "}}", json.dumps(value) if isinstance(value, dict) else str(value)
                )
            parts.append(audio_script)

        # 6. WebGL
        if profile_config.get("profile_webgl") or profile_config.get("profile_vendor") or profile_config.get("profile_renderer"):
            from . import fingerprint_data as fpdata
            webgl_script = self.load_script("webgl")
            webgl_raw = profile_config.get("profile_webgl")
            
            # Parse or use default WebGL dict
            webgl_data = {}
            if webgl_raw:
                if isinstance(webgl_raw, str) and webgl_raw.strip():
                    try:
                        webgl_data = json.loads(webgl_raw)
                    except Exception:
                        webgl_data = {}
                elif isinstance(webgl_raw, dict):
                    webgl_data = webgl_raw

            # If empty or invalid, generate a random WebGL configuration base
            if not isinstance(webgl_data, dict) or not webgl_data or len(webgl_data) < 5:
                os_name = profile_config.get("profile_os", "")
                phone_os = None
                if os_name == "iPhone" or "iPhone" in os_name:
                    phone_os = "iPhone"
                elif os_name == "Android" or "Android" in os_name:
                    phone_os = "Android"
                webgl_data = fpdata.generate_webgl_fingerprint(phone_os, os_name)

            # Override with custom user-configured vendor and renderer if present
            custom_vendor = profile_config.get("profile_vendor")
            custom_renderer = profile_config.get("profile_renderer")
            if custom_vendor and str(custom_vendor).strip():
                vendor_str = str(custom_vendor).strip()
                webgl_data["37445"] = vendor_str
                
                # If custom_renderer is empty/random, choose a random renderer matching the vendor's brand
                if not custom_renderer or not str(custom_renderer).strip():
                    brand = ""
                    if "NVIDIA" in vendor_str:
                        brand = "NVIDIA"
                    elif "Intel" in vendor_str:
                        brand = "Intel"
                    elif "AMD" in vendor_str:
                        brand = "AMD"
                    
                    if brand:
                        matching_renderers = [r for r in fpdata.GPU_VENDORS if brand in r]
                        if matching_renderers:
                            webgl_data["37446"] = random.choice(matching_renderers)

            if custom_renderer and str(custom_renderer).strip():
                webgl_data["37446"] = str(custom_renderer).strip()

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
            from . import fingerprint_data as fpdata
            fonts_script = self.load_script("fonts")
            font_data = profile_config["profile_font"]
            if isinstance(font_data, str):
                try:
                    font_data = json.loads(font_data)
                except Exception:
                    font_data = None
            if not isinstance(font_data, list) or not font_data:
                font_data = fpdata.generate_font_list()
            fonts_script = fonts_script.replace("{{fonts}}", json.dumps(font_data))
            parts.append(fonts_script)

        # 9. Network (always)
        net_script = self.load_script("network").replace("{{plugins_seed}}", str(profile_id))
        parts.append(net_script)

        # 10. Battery (always)
        bat_script = self.load_script("battery").replace("{{plugins_seed}}", str(profile_id))
        parts.append(bat_script)

        # 11. Navigator extra (always)
        nav_script = self.load_script("navigator_extra").replace("{{plugins_seed}}", str(profile_id))
        resolution = profile_config.get("profile_resolution", "1920x1080")
        width, height = 1920, 1080
        if resolution:
            parts_res = resolution.strip().replace(" ", "").split("x")
            if len(parts_res) == 2:
                try:
                    width = int(parts_res[0])
                    height = int(parts_res[1])
                except ValueError:
                    pass
        nav_script = nav_script.replace("{{profile_width}}", str(width))
        nav_script = nav_script.replace("{{profile_height}}", str(height))
        parts.append(nav_script)

        # 12. Speech synthesis (always)
        parts.append(self.load_script("speech_synthesis"))

        # 13. Media devices (always)
        parts.append(self.load_script("media_devices"))

        # 14. Ping block (always)
        parts.append(self.load_script("ping"))

        combined = "\n\n".join(parts)
        cleanup_js = """
// Cleanup internal helper functions from global window to avoid detection
try {
  delete window._makeNative;
  delete window._safelyOverrideGetter;
  delete window._safelyOverrideValue;
} catch(e) {}
"""
        return combined + "\n\n" + cleanup_js
