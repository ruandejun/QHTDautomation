import os
import sys
import socket
import subprocess
import tarfile
import urllib.request
import logging
import requests
import psutil
import shutil

logger = logging.getLogger("QHTDTorManager")
logging.basicConfig(level=logging.INFO)

# Determine base paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BIN_DIR = os.path.join(BASE_DIR, "bin")
TOR_DIR = os.path.join(BIN_DIR, "tor")
DATA_DIR = os.path.join(BASE_DIR, "data")

TOR_EXE_SUBPATH_1 = os.path.join(TOR_DIR, "tor", "tor.exe")
TOR_EXE_SUBPATH_2 = os.path.join(TOR_DIR, "tor.exe")

PRIMARY_URL = "https://dist.torproject.org/torbrowser/15.0.16/tor-expert-bundle-windows-x86_64-15.0.16.tar.gz"
FALLBACK_URL = "https://dist.torproject.org/torbrowser/14.0.1/tor-expert-bundle-windows-x86_64-14.0.1.tar.gz"

def get_tor_exe_path():
    """Returns the absolute path to tor.exe if it exists, otherwise None."""
    if os.path.exists(TOR_EXE_SUBPATH_1):
        return TOR_EXE_SUBPATH_1
    if os.path.exists(TOR_EXE_SUBPATH_2):
        return TOR_EXE_SUBPATH_2
    return None

def is_tor_installed():
    """Checks if tor.exe is installed."""
    return get_tor_exe_path() is not None

def download_and_extract_tor(progress_callback=None):
    """Downloads Tor Expert Bundle and extracts it to bin/tor."""
    os.makedirs(BIN_DIR, exist_ok=True)
    os.makedirs(TOR_DIR, exist_ok=True)
    
    tar_path = os.path.join(BIN_DIR, "tor_expert_bundle.tar.gz")
    
    # Try downloading from primary URL, fallback if it fails
    urls = [PRIMARY_URL, FALLBACK_URL]
    success = False
    
    for url in urls:
        try:
            logger.info(f"Downloading Tor from {url}...")
            if progress_callback:
                progress_callback(f"Đang tải Tor từ {url.split('/')[-2]}...")
            
            # Download with progress chunking
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get('Content-Length', 0))
                downloaded = 0
                block_size = 8192
                
                with open(tar_path, 'wb') as f:
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        f.write(buffer)
                        if progress_callback and total_size > 0:
                            percent = int(downloaded * 100 / total_size)
                            progress_callback(f"Đang tải: {percent}% ({downloaded // 1024} KB / {total_size // 1024} KB)")
            
            success = True
            break
        except Exception as e:
            logger.warning(f"Failed to download from {url}: {e}")
            if os.path.exists(tar_path):
                try:
                    os.remove(tar_path)
                except:
                    pass
                    
    if not success:
        raise Exception("Không thể tải xuống Tor từ bất kỳ nguồn nào. Vui lòng kiểm tra lại kết nối mạng.")

    if progress_callback:
        progress_callback("Đang giải nén Tor Expert Bundle...")
    
    try:
        logger.info("Extracting Tor Expert Bundle...")
        with tarfile.open(tar_path, "r:gz") as tar:
            tar.extractall(path=TOR_DIR)
        logger.info("Extraction completed successfully!")
    finally:
        if os.path.exists(tar_path):
            try:
                os.remove(tar_path)
            except:
                pass

    if not is_tor_installed():
        raise Exception("Giải nén thành công nhưng không tìm thấy file tor.exe.")
    
    if progress_callback:
        progress_callback("Đã tải và cài đặt Tor thành công!")

def kill_all_tor_processes():
    """Kills all running tor.exe processes on the system to avoid port conflicts."""
    try:
        logger.info("Killing any residual tor.exe processes...")
        # Clean up using taskkill on Windows for absolute safety
        if os.name == 'nt':
            subprocess.run(
                ["taskkill", "/F", "/IM", "tor.exe"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
            )
        else:
            # Fallback to psutil for non-Windows platforms
            for proc in psutil.process_iter(['name']):
                if proc.info['name'] and proc.info['name'].lower() == 'tor.exe':
                    try:
                        proc.kill()
                    except Exception:
                        pass
    except Exception as e:
        logger.error(f"Error killing residual tor processes: {e}")

def kill_process_on_port(port: int):
    """Finds and kills any tor.exe process listening on the specified port to free it up."""
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.laddr and conn.laddr.port == port:
                pid = conn.pid
                if pid:
                    try:
                        p = psutil.Process(pid)
                        if p.name().lower() == 'tor.exe':
                            logger.info(f"Port {port} is occupied by tor.exe (PID {pid}). Terminating...")
                            p.kill()
                            p.wait(timeout=2)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
    except Exception as e:
        logger.warning(f"Could not check/kill process on port {port}: {e}")

class TorProxyManager:
    """Manages lifecycle of multiple Tor SOCKS5 instances."""
    def __init__(self):
        self.processes = {}  # socks_port -> subprocess.Popen
        # Cleanup any orphan tor processes on startup
        kill_all_tor_processes()
        
    def start_proxy(self, socks_port: int, control_port: int, country_code: str = "") -> bool:
        """Starts a Tor proxy instance on specified ports, optionally targeting a specific country exit node."""
        if socks_port in self.processes:
            logger.info(f"Tor proxy already running on port {socks_port}")
            return True
            
        tor_exe = get_tor_exe_path()
        if not tor_exe:
            logger.error("Tor is not installed.")
            return False
            
        # Ensure target ports are free of any residual Tor processes before starting
        kill_process_on_port(socks_port)
        kill_process_on_port(control_port)

        # Prepare directories
        instance_data_dir = os.path.join(DATA_DIR, f"tor_data_{socks_port}")
        os.makedirs(instance_data_dir, exist_ok=True)
        
        # Build commands
        cmd = [
            tor_exe,
            "--SocksPort", f"127.0.0.1:{socks_port}",
            "--ControlPort", f"127.0.0.1:{control_port}",
            "--DataDirectory", instance_data_dir,
            "--CookieAuthentication", "0"
        ]
        
        if country_code and country_code.strip():
            cmd.extend([
                "--ExitNodes", f"{{{country_code.lower().strip()}}}",
                "--StrictNodes", "1"
            ])
        
        try:
            logger.info(f"Starting Tor on SocksPort={socks_port}, ControlPort={control_port}, Country={country_code or 'Auto'}...")
            # Hide console window on Windows
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = 0  # SW_HIDE
            
            p = subprocess.Popen(
                cmd,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            self.processes[socks_port] = (p, control_port, instance_data_dir)
            return True
        except Exception as e:
            logger.error(f"Failed to start Tor on port {socks_port}: {e}")
            return False
            
    def stop_proxy(self, socks_port: int):
        """Stops the Tor proxy instance running on specified port."""
        if socks_port not in self.processes:
            return
            
        p, control_port, data_dir = self.processes[socks_port]
        logger.info(f"Stopping Tor proxy on port {socks_port}...")
        try:
            p.terminate()
            p.wait(timeout=2)
        except Exception:
            try:
                p.kill()
            except:
                pass
        
        # Clear data directory to keep things clean
        try:
            shutil.rmtree(data_dir, ignore_errors=True)
        except:
            pass
            
        del self.processes[socks_port]
        
    def stop_all(self):
        """Stops all running Tor instances."""
        ports = list(self.processes.keys())
        for port in ports:
            self.stop_proxy(port)
        # Force kill any orphan/residual tor processes
        kill_all_tor_processes()
            
    def rotate_ip(self, control_port: int) -> bool:
        """Sends NEWNYM signal to control port to request a new IP circuit."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3.0)
            s.connect(("127.0.0.1", control_port))
            s.sendall(b"AUTHENTICATE\r\n")
            res = s.recv(1024).decode()
            if "250" not in res:
                s.close()
                return False
                
            s.sendall(b"SIGNAL NEWNYM\r\n")
            res = s.recv(1024).decode()
            s.sendall(b"QUIT\r\n")
            s.close()
            return "250" in res
        except Exception as e:
            logger.error(f"Error rotating IP on control port {control_port}: {e}")
            return False
            
    def check_public_ip(self, socks_port: int) -> str:
        """Checks the public IP address routed through the specified SOCKS port."""
        proxies = {
            "http": f"socks5h://127.0.0.1:{socks_port}",
            "https": f"socks5h://127.0.0.1:{socks_port}"
        }
        try:
            # Short timeout to avoid blocking indefinitely
            res = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=6)
            if res.ok:
                return res.json().get("ip", "Không xác định")
        except Exception as e:
            logger.debug(f"IP check failed on port {socks_port}: {e}")
        return "Không hoạt động / Đang kết nối..."

# Singleton instance
tor_manager = TorProxyManager()
