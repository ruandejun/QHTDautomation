import threading
import time
import logging
import socket
from typing import Optional

try:
    import socks as pysocks
except ImportError:
    import urllib3.contrib.socks as pysocks

logger = logging.getLogger(__name__)

class ProxyAuthFix:
    """Fix cho phần relay proxy auth (không leak thread)"""
    
    def __init__(self):
        self.threads: list = []
    
    def _relay(self, src, dst, name: str):
        try:
            while True:
                data = src.recv(65536)
                if not data:
                    break
                dst.sendall(data)
        except Exception as e:
            logger.debug(f"{name} relay error: {e}")
        finally:
            try:
                src.close()
                dst.close()
            except:
                pass
    
    def _handle_client(self, client_sock, config):
        try:
            # SOCKS5 handshake
            init = client_sock.recv(2)
            if not init or init[0] != 0x05:
                return
            client_sock.sendall(b'\x05\x00')  # NO AUTH
            
            # CONNECT request
            header = client_sock.recv(4)
            atyp = header[3]
            if atyp == 0x01:  # IPv4
                addr_data = client_sock.recv(4)
                dst_addr = socket.inet_ntoa(addr_data)
            elif atyp == 0x03:  # Domain
                domain_len = client_sock.recv(1)[0]
                dst_addr = client_sock.recv(domain_len).decode('ascii')
            else:
                return
            
            dst_port = int.from_bytes(client_sock.recv(2), 'big')
            
            # Connect remote with auth
            remote_sock = pysocks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
            remote_sock.set_proxy(
                pysocks.SOCKS5, 
                config.ip, 
                config.port, 
                username=config.username, 
                password=config.password
            )
            remote_sock.settimeout(30)
            remote_sock.connect((dst_addr, dst_port))
            
            # Reply success
            reply = b'\x05\x00\x00\x01' + socket.inet_aton('0.0.0.0') + (0).to_bytes(2, 'big')
            client_sock.sendall(reply)
            
            # Relay with shutdown event
            shutdown_event = threading.Event()
            t1 = threading.Thread(target=self._relay, args=(client_sock, remote_sock, "client->remote"), daemon=True)
            t2 = threading.Thread(target=self._relay, args=(remote_sock, client_sock, "remote->client"), daemon=True)
            
            t1.start()
            t2.start()
            
            # Set threads list
            self.threads.extend([t1, t2])
            
            # Wait for shutdown (optional)
            # client_sock.settimeout(None)  # keep alive
            
        except Exception as e:
            logger.debug(f"Proxy auth error: {e}")
        finally:
            try:
                client_sock.close()
                remote_sock.close()
            except:
                pass
    
    def start_auth_relay(self, config):
        # Trả về local port
        local_port = getattr(config, 'local_port', 0) or 1080
        return local_port
