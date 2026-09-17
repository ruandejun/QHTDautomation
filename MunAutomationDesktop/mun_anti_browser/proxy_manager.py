"""
MunAntiBrowser - Proxy Manager
================================
Handles proxy parsing and configuration for Chrome browser args.
Ported from mybrowser.py proxy handling logic (lines 767-858).

SOCKS5 Auth: Chrome --proxy-server does NOT support SOCKS5 authentication.
Solution: Start a local TCP relay (SOCKS5 server on 127.0.0.1) that forwards
all connections through the authenticated remote SOCKS5 proxy using PySocks.
"""

import logging
import socket
import threading
import time
from dataclasses import dataclass
from typing import Optional, List, Union, Dict, Any

import socks as pysocks

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
    local_relay_port: int = 0   # Port of local relay (set after start_auth_relay)

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

        # Clean scheme prefix (socks5://, http://, https://)
        parsed_type = proxy_type
        clean_str = proxy_string
        if "://" in clean_str:
            scheme, clean_str = clean_str.split("://", 1)
            parsed_type = scheme.lower()

        config = ProxyConfig(proxy_type=parsed_type, raw=proxy_string)

        try:
            if "@" in clean_str:
                # Format: user:pass@ip:port
                auth_part, address_part = clean_str.split("@", 1)
                config.ip = address_part.split(":")[0].strip()
                config.port = address_part.split(":")[1].strip().split("/")[0]
                if ":" in auth_part:
                    config.username, config.password = auth_part.split(":", 1)
                else:
                    config.username = auth_part
                    config.password = ""

            elif "#" in clean_str:
                # Format: ip:port#user:pass
                address_part, auth_part = clean_str.split("#", 1)
                config.ip = address_part.split(":")[0].strip()
                config.port = address_part.split(":")[1].strip().split("/")[0]
                if ":" in auth_part:
                    config.username, config.password = auth_part.split(":", 1)
                else:
                    config.username = auth_part
                    config.password = ""

            elif username and password:
                # External auth provided
                parts = clean_str.split(":")
                config.ip = parts[0].strip()
                config.port = parts[1].strip().split("/")[0]
                config.username = username
                config.password = password

            elif ":" in clean_str:
                parts = clean_str.split(":")
                config.ip = parts[0].strip()
                config.port = parts[1].strip().split("/")[0]
                if len(parts) == 4:
                    # Format: ip:port:user:pass
                    config.username = parts[2].strip()
                    config.password = parts[3].strip()

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

        When proxy has auth and local_relay_port is set, Chrome connects
        to the local relay (127.0.0.1:relay_port) instead of the remote proxy.

        Args:
            config: Parsed ProxyConfig (with local_relay_port set if auth proxy)

        Returns:
            List of Chrome args (e.g., ['--proxy-server=socks5://ip:port'])
        """
        if not config:
            return []

        args = []
        if config.local_relay_port > 0:
            # Proxy có auth → dùng local relay (đã handle auth qua PySocks)
            proxy_url = f"{config.proxy_type}://127.0.0.1:{config.local_relay_port}"
        else:
            # Proxy không auth → kết nối trực tiếp
            proxy_url = f"{config.proxy_type}://{config.address}"
        args.append(f"--proxy-server={proxy_url}")

        return args

    def close(self):
        """Đóng relay server và giải phóng port"""
        if hasattr(self, '_server_sock') and self._server_sock:
            try:
                self._server_sock.close()
            except Exception:
                pass
            self._server_sock = None

    def start_auth_relay(self, config: ProxyConfig) -> int:
        """
        Start a local SOCKS5 relay server for authenticated proxies.

        Chrome cannot do SOCKS5 authentication natively. This method:
          1. Listens on 127.0.0.1:<random_port> as a SOCKS5 server (NO auth)
          2. For each incoming SOCKS5 CONNECT, connects to the actual
             destination through the remote SOCKS5 proxy WITH auth (PySocks)
          3. Relays data bidirectionally

        Chrome → 127.0.0.1:local_port (no auth) → remote_proxy:port (with auth) → target

        Args:
            config: ProxyConfig with auth credentials.

        Returns:
            Local port number the relay is listening on.

        Raises:
            RuntimeError if relay cannot be started.
        """
        remote_host = config.ip
        remote_port = int(config.port)
        username = config.username
        password = config.password

        # Bind local server to get a free port
        server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('127.0.0.1', 0))
        local_port = server_sock.getsockname()[1]
        server_sock.listen(32)
        self._server_sock = server_sock

        def _relay(src, dst):
            """Relay data between two sockets until one closes."""
            try:
                while True:
                    data = src.recv(65536)
                    if not data:
                        break
                    dst.sendall(data)
            except Exception:
                pass
            finally:
                try:
                    src.close()
                except Exception:
                    pass
                try:
                    dst.close()
                except Exception:
                    pass

        def _handle_client(client_sock):
            """Handle one SOCKS5 connection from Chrome."""
            try:
                # === SOCKS5 Handshake ===
                # Chrome sends: VER(0x05) NMETHODS(1) METHODS(0x00=NO_AUTH)
                init = client_sock.recv(256)
                if not init or init[0] != 0x05:
                    client_sock.close()
                    return

                # Reply: VER(0x05) METHOD(0x00=NO_AUTH)
                client_sock.sendall(b'\x05\x00')

                # === SOCKS5 CONNECT Request ===
                # VER(0x05) CMD(0x01=CONNECT) RSV(0x00) ATYP DST.ADDR DST.PORT
                header = client_sock.recv(4)
                if not header or len(header) < 4:
                    client_sock.close()
                    return

                atyp = header[3]
                if atyp == 0x01:  # IPv4
                    addr_data = client_sock.recv(4)
                    dst_addr = socket.inet_ntoa(addr_data)
                elif atyp == 0x03:  # Domain name
                    domain_len = client_sock.recv(1)[0]
                    dst_addr = client_sock.recv(domain_len).decode('ascii')
                elif atyp == 0x04:  # IPv6
                    addr_data = client_sock.recv(16)
                    dst_addr = socket.inet_ntop(socket.AF_INET6, addr_data)
                else:
                    client_sock.close()
                    return

                port_data = client_sock.recv(2)
                dst_port = int.from_bytes(port_data, 'big')

                # === Connect through remote SOCKS5 proxy WITH auth ===
                remote_sock = pysocks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
                remote_sock.set_proxy(
                    pysocks.SOCKS5,
                    remote_host,
                    remote_port,
                    username=username,
                    password=password,
                )
                remote_sock.settimeout(30)
                remote_sock.connect((dst_addr, dst_port))

                # === Reply to Chrome: success ===
                # VER(0x05) REP(0x00=OK) RSV(0x00) ATYP(0x01=IPv4) BND.ADDR BND.PORT
                reply = b'\x05\x00\x00\x01' + socket.inet_aton('0.0.0.0') + (0).to_bytes(2, 'big')
                client_sock.sendall(reply)

                # === Relay data bidirectionally ===
                remote_sock.settimeout(None)
                t1 = threading.Thread(target=_relay, args=(client_sock, remote_sock), daemon=True)
                t2 = threading.Thread(target=_relay, args=(remote_sock, client_sock), daemon=True)
                t1.start()
                t2.start()

            except Exception as e:
                logger.debug(f"Relay connection error to {dst_addr if 'dst_addr' in dir() else '?'}:{dst_port if 'dst_port' in dir() else '?'}: {e}")
                try:
                    client_sock.close()
                except Exception:
                    pass

        def _accept_loop():
            """Accept loop for local relay server."""
            while True:
                try:
                    client_sock, _ = server_sock.accept()
                    t = threading.Thread(target=_handle_client, args=(client_sock,), daemon=True)
                    t.start()
                except Exception:
                    break

        # Start accept loop in background daemon thread
        accept_thread = threading.Thread(target=_accept_loop, daemon=True)
        accept_thread.start()

        logger.info(
            f"Local SOCKS5 relay started: 127.0.0.1:{local_port} "
            f"-> {remote_host}:{remote_port} (user: {username})"
        )

        config.local_relay_port = local_port
        return local_port

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

    @staticmethod
    def test_connection(
        proxy: Union[str, ProxyConfig],
        timeout: float = 10.0,
        target_host: str = "www.google.com",
        target_port: int = 80,
    ) -> Dict[str, Any]:
        """
        Test if a proxy is alive and measure round-trip handshake latency in milliseconds.
        Supports both SOCKS5 (with/without RFC 1929 auth) and HTTP proxies.
        """
        # Normalize input
        if isinstance(proxy, str):
            cfg = ProxyManager.parse(proxy)
            if cfg is None:
                return {
                    "alive": False,
                    "latency_ms": -1.0,
                    "error": f"Failed to parse proxy string (Missing proxy IP or port): {proxy}",
                    "proxy_address": proxy,
                    "proxy_type": "",
                }
        elif isinstance(proxy, ProxyConfig):
            cfg = proxy
        else:
            return {
                "alive": False,
                "latency_ms": -1.0,
                "error": "Invalid proxy parameter type",
                "proxy_address": "",
                "proxy_type": "",
            }

        if not cfg.ip or not cfg.port:
            return {
                "alive": False,
                "latency_ms": -1.0,
                "error": "Missing proxy IP or port",
                "proxy_address": cfg.address,
                "proxy_type": cfg.proxy_type,
            }

        try:
            port_num = int(cfg.port)
        except ValueError:
            return {
                "alive": False,
                "latency_ms": -1.0,
                "error": f"Invalid port number: {cfg.port}",
                "proxy_address": cfg.address,
                "proxy_type": cfg.proxy_type,
            }

        proxy_type_flag = pysocks.SOCKS5 if cfg.proxy_type.lower() == "socks5" else pysocks.HTTP
        sock = pysocks.socksocket()
        sock.settimeout(timeout)

        start_time = time.perf_counter()
        try:
            sock.set_proxy(
                proxy_type=proxy_type_flag,
                addr=cfg.ip,
                port=port_num,
                username=cfg.username if cfg.username else None,
                password=cfg.password if cfg.password else None,
            )
            sock.connect((target_host, target_port))
            latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
            sock.close()
            return {
                "alive": True,
                "latency_ms": latency_ms,
                "error": None,
                "proxy_address": cfg.address,
                "proxy_type": cfg.proxy_type,
            }
        except Exception as e:
            try:
                sock.close()
            except Exception:
                pass
            return {
                "alive": False,
                "latency_ms": -1.0,
                "error": str(e),
                "proxy_address": cfg.address,
                "proxy_type": cfg.proxy_type,
            }

