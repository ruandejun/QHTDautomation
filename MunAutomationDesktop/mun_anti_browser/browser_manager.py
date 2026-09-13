"""
MunAntiBrowser - Browser Manager (Nodriver)
=============================================
Core async browser lifecycle management using nodriver.
Replaces mybrowser.py setting() function (lines 557-940).

Usage:
    from mun_anti_browser import NodriverBrowserManager

    manager = NodriverBrowserManager()
    profile = manager.profile_manager.create_random_profile()
    browser, tab = await manager.start(profile)
    # ... interact with tab ...
    await manager.close()
"""

import asyncio
import base64
import logging
import os
import random
import sys
from typing import Dict, Any, Optional, Tuple

import nodriver

from . import cdp_commands
from .profile_manager import ProfileManager
from .proxy_manager import ProxyManager, ProxyConfig
from .script_loader import ScriptLoader

logger = logging.getLogger(__name__)


class NodriverBrowserManager:
    """
    Manages anti-detect browser lifecycle using nodriver (CDP-based async).
    Handles:
        - Chrome launch with spoofed args
        - Fingerprint script injection
        - CDP overrides (UA, timezone, geolocation, device metrics)
        - Proxy configuration
        - Tab management
    """

    def __init__(
        self,
        chrome_path: Optional[str] = None,
        user_data_dir: Optional[str] = None,
    ):
        """
        Args:
            chrome_path: Path to Chrome binary. None = auto-detect.
            user_data_dir: Directory for browser profile data.
        """
        self.chrome_path = chrome_path
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "chrome_data"
        )
        self.browser: Optional[nodriver.Browser] = None
        self.main_tab = None
        self.profile_manager = ProfileManager()
        self.script_loader = ScriptLoader()
        self.proxy_manager = ProxyManager()
        self._injection_script: str = ""
        self._current_profile: Dict[str, Any] = {}

    async def start_profile(
        self,
        profile_id: str,
        start_url: str = "",
        proxy_string: str = "",
        proxy_type: str = "socks5",
        proxy_username: str = "",
        proxy_password: str = "",
        disable_images: bool = False,
        headless: bool = False,
        extra_args: Optional[list] = None,
        extensions: Optional[list] = None,
    ) -> Tuple[nodriver.Browser, Any]:
        """
        Start or get persistent anti-detect profile by ID / name.
        """
        profiles_base = os.path.join(self.user_data_dir, "named_profiles")
        profile_config = self.profile_manager.get_or_create_named_profile(
            identifier=profile_id,
            proxy=proxy_string,
            save_dir=profiles_base
        )
        clean_id = profile_config["id"]
        profile_dir = os.path.join(profiles_base, clean_id)
        os.makedirs(profile_dir, exist_ok=True)

        custom_manager = NodriverBrowserManager(
            chrome_path=self.chrome_path,
            user_data_dir=profiles_base
        )
        return await custom_manager.start(
            profile_config=profile_config,
            proxy_string=proxy_string,
            proxy_type=proxy_type,
            proxy_username=proxy_username,
            proxy_password=proxy_password,
            disable_images=disable_images,
            headless=headless,
            start_url=start_url,
            extra_args=extra_args,
            extensions=extensions,
        )

    async def start_named_profile(
        self,
        name: str,
        start_url: str = "",
        proxy_string: str = "",
        proxy_type: str = "socks5",
        proxy_username: str = "",
        proxy_password: str = "",
        disable_images: bool = False,
        headless: bool = False,
        extra_args: Optional[list] = None,
        extensions: Optional[list] = None,
    ) -> Tuple[nodriver.Browser, Any]:
        return await self.start_profile(
            profile_id=name,
            start_url=start_url,
            proxy_string=proxy_string,
            proxy_type=proxy_type,
            proxy_username=proxy_username,
            proxy_password=proxy_password,
            disable_images=disable_images,
            headless=headless,
            extra_args=extra_args,
            extensions=extensions,
        )

    async def start(
        self,
        profile_config: Optional[Dict[str, Any]] = None,
        proxy_string: str = "",
        proxy_type: str = "socks5",
        proxy_username: str = "",
        proxy_password: str = "",
        disable_images: bool = False,
        headless: bool = False,
        start_url: str = "",
        extra_args: Optional[list] = None,
        extensions: Optional[list] = None,
    ) -> Tuple[nodriver.Browser, Any]:
        """
        Start a new anti-detect browser instance.

        Args:
            profile_config: Profile configuration dict (or None for random).
            proxy_string: Proxy connection string.
            proxy_type: "socks5" or "http".
            proxy_username: Proxy auth username.
            proxy_password: Proxy auth password.
            disable_images: Disable image loading.
            headless: Run in headless mode.
            start_url: URL to open after launch.
            extra_args: Optional list of additional Chrome command-line arguments.

        Returns:
            (browser, main_tab) tuple.
        """
        # Generate random profile if none provided
        if profile_config is None:
            profile_config = self.profile_manager.create_random_profile(
                socks5=proxy_string if proxy_type == "socks5" else "",
                proxy=proxy_string if proxy_type != "socks5" else "",
                proxy_username=proxy_username,
                proxy_password=proxy_password,
            )
        self._current_profile = profile_config

        # Build Chrome args
        chrome_args = self._build_chrome_args(
            profile_config, disable_images, headless,
            proxy_string, proxy_type, proxy_username, proxy_password,
        )
        if extra_args:
            for arg in extra_args:
                if arg not in chrome_args:
                    chrome_args.append(arg)
            # Remove --disable-extensions if we are loading an extension
            if any(arg.startswith("--load-extension") for arg in extra_args):
                if "--disable-extensions" in chrome_args:
                    chrome_args.remove("--disable-extensions")

        # Build injection script
        self._injection_script = self.script_loader.compose_injection(profile_config)

        # Determine user data dir for this profile
        profile_id = profile_config.get("id", 0) or random.randint(10000, 99999)
        profile_dir = os.path.join(self.user_data_dir, str(profile_id))
        self._active_profile_dir = None

        logger.info(f"Starting browser with profile {profile_id}")
        logger.debug(f"Profile dir: {profile_dir}")
        logger.debug(f"Chrome args: {len(chrome_args)} args")

        # Write WebRTC protection prefs BEFORE browser starts
        self._write_webrtc_prefs(profile_dir)

        # Ensure DISPLAY is set in Linux environment
        if "DISPLAY" not in os.environ:
            os.environ["DISPLAY"] = ":1"

        # Start browser via nodriver
        config = nodriver.Config()
        is_root = (hasattr(os, "geteuid") and os.geteuid() == 0) or sys.platform == "win32"
        if is_root:
            config.sandbox = False
        else:
            config.sandbox = True
        for arg in chrome_args:
            config.add_argument(arg)
        config.user_data_dir = profile_dir

        # Add extensions if specified
        if extensions:
            for ext_path in extensions:
                config.add_extension(ext_path)

        if self.chrome_path:
            config.browser_executable_path = self.chrome_path

        if headless:
            config.headless = True

        for attempt in range(3):
            try:
                # Dọn sạch port và process rác trước khi khởi động
                self.browser = await nodriver.start(config=config)
                break
            except Exception as e:
                logger.warning(f"Lỗi khởi động Chrome lần {attempt+1}, kill dọn sạch và thử lại sau 2s: {e}")
                # Kill triệt để các Chrome treo cũ
                if sys.platform != "win32":
                    os.system("pkill -9 -f /opt/google/chrome/chrome || true")
                    os.system("pkill -9 -f /bin/google-chrome || true")
                await asyncio.sleep(2)
        if not self.browser:
            raise RuntimeError("Failed to launch browser after 3 attempts")

        # Get the initial tab
        self.main_tab = self.browser.main_tab

        # Apply CDP overrides (Page domain remains enabled so addScriptToEvaluateOnNewDocument executes)
        await cdp_commands.apply_all_cdp_overrides(
            self.main_tab,
            profile_config,
            self._injection_script,
        )

        # Navigate to start URL
        url = start_url or profile_config.get("profile_start_url", "")
        if url:
            await self.main_tab.get(url)

        # Register tab event handlers
        self._register_tab_handlers()

        logger.info("Browser started successfully")
        return self.browser, self.main_tab

    def _build_chrome_args(
        self,
        profile_config: Dict[str, Any],
        disable_images: bool,
        headless: bool,
        proxy_string: str,
        proxy_type: str,
        proxy_username: str,
        proxy_password: str,
    ) -> list:
        """
        Build Chrome command-line arguments for anti-detect.
        Ported from mybrowser.py setting() args construction.

        NOTE: nodriver Config handles these args natively (DO NOT add them here):
            --no-sandbox, --headless, --user-data-dir, --lang,
            --no-first-run, --no-service-autorun, --password-store=basic,
            --disable-infobars, --disable-dev-shm-usage
        """
        args = [
            # Disable various detections
            "--disable-component-update",
            "--disable-default-apps",
            "--disable-hang-monitor",
            "--disable-popup-blocking",
            "--disable-prompt-on-repost",
            "--disable-sync",
            "--disable-translate",
            "--disable-notifications",
        ]

        # Set window size from profile
        resolution = profile_config.get("profile_resolution", "1920x1080")
        parts = resolution.strip().replace(" ", "").split("x")
        if len(parts) == 2:
            args.append(f"--window-size={parts[0]},{parts[1]}")

        # Disable images
        if disable_images:
            args.append("--blink-settings=imagesEnabled=false")

        # Proxy
        proxy_str = proxy_string or profile_config.get("profile_socks5_details") or profile_config.get("profile_proxy_details", "")
        if proxy_str:
            proxy_config = self.proxy_manager.parse(
                proxy_str, proxy_type, proxy_username, proxy_password,
            )
            if proxy_config:
                # Nếu proxy có auth → start local relay (Chrome không hỗ trợ SOCKS5 auth)
                if proxy_config.has_auth:
                    self.proxy_manager.start_auth_relay(proxy_config)
                args.extend(self.proxy_manager.get_chrome_args(proxy_config))

        # WebRTC protection (ALWAYS enabled - prevents IP leak)
        args.extend(self.proxy_manager.get_webrtc_args())

        return args

    def _write_webrtc_prefs(self, profile_dir: str):
        """
        Write Chrome Preferences file with WebRTC IP handling policy.
        Must be called BEFORE browser starts so Chrome reads it on launch.
        This is the most reliable method - works at C++ level.
        """
        import json as json_module

        # Chrome stores Default profile prefs in:  <user-data-dir>/Default/Preferences
        default_dir = os.path.join(profile_dir, "Default")
        os.makedirs(default_dir, exist_ok=True)
        prefs_path = os.path.join(default_dir, "Preferences")

        # Load existing prefs or start fresh
        prefs = {}
        if os.path.exists(prefs_path):
            try:
                with open(prefs_path, "r", encoding="utf-8") as f:
                    prefs = json_module.load(f)
            except Exception:
                prefs = {}

        # Set WebRTC preferences
        if "webrtc" not in prefs:
            prefs["webrtc"] = {}
        prefs["webrtc"]["ip_handling_policy"] = "disable_non_proxied_udp"
        prefs["webrtc"]["multiple_routes_enabled"] = False
        prefs["webrtc"]["nonproxied_udp_enabled"] = False

        # Also disable WebRTC event logging
        if "webrtc_event_log_manager" not in prefs:
            prefs["webrtc_event_log_manager"] = {}
        prefs["webrtc_event_log_manager"]["allow_remote_bound"] = False

        try:
            with open(prefs_path, "w", encoding="utf-8") as f:
                json_module.dump(prefs, f, indent=2)
            logger.info(f"WebRTC prefs written to {prefs_path}")
        except Exception as e:
            logger.warning(f"Failed to write WebRTC prefs: {e}")

    def _register_tab_handlers(self):
        """
        Register event handlers for new tabs.
        Note: add_script_to_evaluate_on_new_document already persists
        across navigations within the same tab. For new tabs opened by
        the user, we handle injection in the new_tab() method.
        """
        pass  # CDP injection scripts persist via addScriptToEvaluateOnNewDocument

    async def _setup_proxy_auth(self, tab: Any, proxy_config: 'ProxyConfig'):
        """Setup CDP-based proxy authentication.

        Chrome's --proxy-server flag does NOT support inline authentication
        (user:pass@host:port). For SOCKS5/HTTP proxies with credentials,
        we use CDP Fetch domain to intercept 407 Proxy Authentication Required
        responses and automatically provide credentials.

        Args:
            tab: The browser tab to setup auth on.
            proxy_config: Parsed ProxyConfig with username/password.
        """
        if not proxy_config.has_auth:
            return

        username = proxy_config.username
        password = proxy_config.password
        logger.info(f"Setting up CDP proxy auth for {proxy_config.address} (user: {username})")

        try:
            # Use Network.setExtraHTTPHeaders is not enough for proxy auth.
            # Instead, use Fetch domain to handle authRequired events.
            import nodriver.cdp.fetch as fetch_cdp

            # Enable Fetch domain with handleAuthRequests=True
            await tab.send(fetch_cdp.enable(
                handle_auth_requests=True
            ))

            # Define handler for auth challenges
            async def handle_auth_required(event: fetch_cdp.AuthRequired):
                """Handle proxy 407 auth challenge automatically."""
                try:
                    await tab.send(fetch_cdp.continue_with_auth(
                        request_id=event.request_id,
                        auth_challenge_response=fetch_cdp.AuthChallengeResponse(
                            response="ProvideCredentials",
                            username=username,
                            password=password,
                        )
                    ))
                    logger.debug("Proxy auth credentials provided via CDP Fetch")
                except Exception as e:
                    logger.warning(f"Error handling proxy auth: {e}")

            # Define handler for regular requests (continue them normally)
            async def handle_request_paused(event: fetch_cdp.RequestPaused):
                """Continue non-auth paused requests normally."""
                try:
                    await tab.send(fetch_cdp.continue_request(
                        request_id=event.request_id
                    ))
                except Exception:
                    pass  # Silently ignore errors for continued requests

            # Register event handlers
            tab.add_handler(fetch_cdp.AuthRequired, handle_auth_required)
            tab.add_handler(fetch_cdp.RequestPaused, handle_request_paused)

            logger.info("CDP proxy authentication handler registered successfully")

        except Exception as e:
            logger.error(f"Failed to setup CDP proxy auth: {e}")
            logger.info("Falling back to no-auth proxy connection")

    async def new_tab(self, url: str = "") -> Any:
        """
        Open a new tab in the current browser.

        Args:
            url: URL to navigate to.

        Returns:
            New tab object.
        """
        if not self.browser:
            raise RuntimeError("Browser not started. Call start() first.")

        # Always open blank page first to apply overrides safely
        tab = await self.browser.get("about:blank", new_tab=True)
        await asyncio.sleep(0.5)

        # Apply injection to new tab (Page domain remains enabled so addScriptToEvaluateOnNewDocument executes)
        await cdp_commands.apply_all_cdp_overrides(
            tab, self._current_profile, self._injection_script,
        )

        # If URL is provided, navigate
        if url:
            await tab.get(url)

        return tab

    async def __aenter__(self):
        """Async context manager enter."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit with guaranteed cleanup."""
        await self.close()

    async def close(self):
        """Close the browser and clean up."""
        target_dir = getattr(self, '_active_profile_dir', None)

        if self.browser:
            try:
                # Force terminate child chrome process if available
                proc = getattr(self.browser, '_process', None) or getattr(self.browser, 'process', None)
                if proc and hasattr(proc, 'kill'):
                    try:
                        proc.kill()
                    except Exception:
                        pass
                proc_pid = getattr(self.browser, '_process_pid', None)
                if proc_pid:
                    try:
                        os.kill(proc_pid, 9)
                    except Exception:
                        pass
                try:
                    self.browser.stop()
                except Exception:
                    pass
                try:
                    if hasattr(self, 'proxy_manager') and self.proxy_manager:
                        self.proxy_manager.close()
                except Exception:
                    pass
                logger.info("Browser closed")
            except Exception as e:
                logger.warning(f"Error closing browser: {e}")
            finally:
                self.browser = None
                self.main_tab = None

        # Đợi 0.5s để tiến trình Chrome hoàn toàn nhả file lock
        await asyncio.sleep(0.5)

        # Tự động dọn dẹp thư mục user_data_dir nếu có profile cụ thể được khởi tạo
        if target_dir:
            try:
                import shutil
                if os.path.exists(target_dir):
                    shutil.rmtree(target_dir, ignore_errors=True)
                    logger.info(f"Cleaned up profile directory: {target_dir}")
            except Exception:
                pass
            self._active_profile_dir = None

    @property
    def is_running(self) -> bool:
        """Check if browser is still running."""
        return self.browser is not None

    async def get_cookies(self) -> list:
        """Get all cookies from the browser."""
        if not self.main_tab:
            return []
        try:
            import nodriver.cdp.network as net
            result = await self.main_tab.send(net.GetAllCookies())
            return [cookie.__dict__ for cookie in result] if result else []
        except Exception as e:
            logger.warning(f"Failed to get cookies: {e}")
            return []

    async def set_cookies(self, cookies: list):
        """Set cookies in the browser."""
        if not self.main_tab:
            return
        try:
            import nodriver.cdp.network as net
            cookie_params = []
            for c in cookies:
                cookie_params.append(net.CookieParam(
                    name=c.get("name", ""),
                    value=c.get("value", ""),
                    domain=c.get("domain", ""),
                    path=c.get("path", "/"),
                ))
            await self.main_tab.send(net.SetCookies(cookies=cookie_params))
        except Exception as e:
            logger.warning(f"Failed to set cookies: {e}")

    async def evaluate(self, script: str) -> Any:
        """Execute JavaScript on the current tab."""
        if not self.main_tab:
            raise RuntimeError("No tab available.")
        return await self.main_tab.evaluate(script)

    async def navigate(self, url: str):
        """Navigate the main tab to a URL."""
        if not self.main_tab:
            raise RuntimeError("No tab available.")
        await self.main_tab.get(url)

    async def scroll_like_human(self, scroll_times: int = 0):
        """
        Simulate human-like scrolling behavior.
        Ported from mybrowser.py scroll_like_human().
        """
        if not self.main_tab:
            return

        if not scroll_times:
            scroll_times = random.randint(5, 10)

        try:
            footer_y = await self.main_tab.evaluate(
                "document.body.scrollHeight"
            )
        except Exception:
            footer_y = random.uniform(300, 1000)

        scrolled = 0
        total_y = 0

        while scrolled < scroll_times:
            random_pos = random.uniform(300, 1000)
            random_action = random.randint(-1, 3)

            try:
                scroll_pos = await self.main_tab.evaluate("window.scrollY")
            except Exception:
                scroll_pos = 0

            if random_action <= 0 or total_y >= footer_y or scroll_pos >= footer_y - random_action:
                direction = -1 * int(random_pos)
            else:
                direction = int(random_pos)
                total_y += direction

            try:
                await self.main_tab.evaluate(f"window.scrollBy(0, {direction})")
            except Exception:
                pass

            scrolled += 1
            await asyncio.sleep(random.uniform(0.3, 1.0))
