"""
MunAntiBrowser - Proxy Manager
================================
Handles proxy parsing and configuration for Chrome browser args.
Ported from mybrowser.py proxy handling logic (lines 767-858).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ProxyConfig:
    """Parsed proxy configuration."""
    proxy_type: str = ""        # "socks5", "http", "https"
    ip: str = ""
    port: str = ""
    username: Optional[str] = None
    password: Optional[str] = None
    raw: str = ""               # Original string

    @property
    def has_auth(self) -> bool:
        return bool(self.username and self.password)

    @property
    def address(self) -> str:
        return f"{self.ip}:{self.port}"

    @property
    def auth_address(self) -> str:
        if self.has_auth:
            return f"{self.username}:{self.password}@{self.ip}:{self.port}"
        return self.address


class ProxyManager:
    """
    Parses proxy strings in various formats and generates
    Chrome browser arguments for proxy connection.
    """

    @staticmethod
    def parse(
        proxy_string: str,
        proxy_type: str = "socks5",
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Optional[ProxyConfig]:
        """
        Parse a proxy string in various formats:
          - user:pass@ip:port
          - ip:port#user:pass
          - ip:port:user:pass (4 parts)
          - ip:port (no auth)

        External username/password override when provided separately.

        Args:
            proxy_string: Raw proxy string
            proxy_type: "socks5", "http", or "https"
            username: Optional override username
            password: Optional override password

        Returns:
            ProxyConfig or None if parsing fails.
        """
        proxy_string = proxy_string.strip()
        if not proxy_string:
            return None

        config = ProxyConfig(proxy_type=proxy_type, raw=proxy_string)

        try:
            if "@" in proxy_string:
                # Format: user:pass@ip:port
                auth_part, address_part = proxy_string.split("@", 1)
                config.ip = address_part.split(":")[0]
                config.port = address_part.split(":")[1]
                config.username = auth_part.split(":")[0]
                config.password = auth_part.split(":")[1]

            elif "#" in proxy_string:
                # Format: ip:port#user:pass
                address_part, auth_part = proxy_string.split("#", 1)
                config.ip = address_part.split(":")[0].strip()
                config.port = address_part.split(":")[1].strip()
                config.username = auth_part.split(":")[0].strip()
                config.password = auth_part.split(":")[1].strip()

            elif username and password:
                # External auth provided
                parts = proxy_string.split(":")
                config.ip = parts[0]
                config.port = parts[1]
                config.username = username
                config.password = password

            elif ":" in proxy_string:
                parts = proxy_string.split(":")
                config.ip = parts[0]
                config.port = parts[1]
                if len(parts) == 4:
                    # Format: ip:port:user:pass
                    config.username = parts[2]
                    config.password = parts[3]

            else:
                logger.warning(f"Cannot parse proxy string: {proxy_string}")
                return None

        except (IndexError, ValueError) as e:
            logger.error(f"Error parsing proxy '{proxy_string}': {e}")
            return None

        return config

    @staticmethod
    def get_chrome_args(config: Optional[ProxyConfig]) -> List[str]:
        """
        Generate Chrome command-line arguments for proxy.

        Args:
            config: Parsed ProxyConfig

        Returns:
            List of Chrome args (e.g., ['--proxy-server=socks5://ip:port'])
        """
        if not config:
            return []

        args = []
        proxy_url = f"{config.proxy_type}://{config.address}"
        args.append(f"--proxy-server={proxy_url}")

        return args

    @staticmethod
    def get_webrtc_args() -> List[str]:
        """Get Chrome args to disable WebRTC IP leak at C++ level."""
        return [
            "--force-webrtc-ip-handling-policy=disable_non_proxied_udp",
            "--disable-webrtc-hw-decoding",
            "--disable-webrtc-hw-encoding",
        ]

    @staticmethod
    def get_webrtc_prefs() -> dict:
        """Get Chrome preferences for WebRTC protection."""
        return {
            "webrtc.ip_handling_policy": "disable_non_proxied_udp",
            "webrtc.multiple_routes_enabled": False,
            "webrtc.nonproxied_udp_enabled": False,
        }
