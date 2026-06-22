"""
MunAntiBrowser - Anti-Detect Browser Package
==============================================
A modular anti-detect browser engine using nodriver (CDP-based async).
Ported from MunLogin/mybrowser.py to clean, maintainable architecture.

Usage:
    import asyncio
    from mun_anti_browser import NodriverBrowserManager, ProfileManager

    async def main():
        manager = NodriverBrowserManager()
        profile = manager.profile_manager.create_random_profile()
        browser, tab = await manager.start(profile)
        await tab.get("https://browserleaks.com")
        # ... interact ...
        await manager.close()

    asyncio.run(main())
"""

from .browser_manager import NodriverBrowserManager
from .profile_manager import ProfileManager
from .proxy_manager import ProxyManager, ProxyConfig
from .script_loader import ScriptLoader
from .c69_api import C69ProfileAPI
from .fingerprint_data import (
    generate_audio_fingerprint,
    generate_canvas_fingerprint,
    generate_webgl_fingerprint,
    generate_rects_offset,
    generate_font_list,
    generate_user_agent,
)

__all__ = [
    "NodriverBrowserManager",
    "ProfileManager",
    "ProxyManager",
    "ProxyConfig",
    "ScriptLoader",
    "C69ProfileAPI",
    "generate_audio_fingerprint",
    "generate_canvas_fingerprint",
    "generate_webgl_fingerprint",
    "generate_rects_offset",
    "generate_font_list",
    "generate_user_agent",
]

__version__ = "1.0.0"

