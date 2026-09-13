"""
Router Automation Module
Manages Win32 routing, network interface conversions, and starting/stopping DHCP/API servers.
"""
import os
import sys
import json
import time
import socket
import subprocess
import urllib.request
import zipfile
import io
import ssl
import ctypes
from ctypes import wintypes

try:
    iphlpapi = ctypes.WinDLL('iphlpapi.dll')
except Exception:
    iphlpapi = None

class MIB_IPFORWARDROW(ctypes.Structure):
    _fields_ = [
        ("dwForwardDest", wintypes.DWORD),
        ("dwForwardMask", wintypes.DWORD),
        ("dwForwardPolicy", wintypes.DWORD),
        ("dwForwardNextHop", wintypes.DWORD),
        ("dwForwardIfIndex", wintypes.DWORD),
        ("dwForwardType", wintypes.DWORD),
        ("dwForwardProto", wintypes.DWORD),
        ("dwForwardAge", wintypes.DWORD),
        ("dwForwardNextHopAS", wintypes.DWORD),
        ("dwForwardMetric1", wintypes.DWORD),
        ("dwForwardMetric2", wintypes.DWORD),
        ("dwForwardMetric3", wintypes.DWORD),
        ("dwForwardMetric4", wintypes.DWORD),
        ("dwForwardMetric5", wintypes.DWORD),
    ]

class NET_LUID(ctypes.Structure):
    _fields_ = [("Value", ctypes.c_uint64)]

IF_MAX_STRING_SIZE = 256

if iphlpapi:
    iphlpapi.ConvertInterfaceAliasToLuid.argtypes = [ctypes.c_wchar_p, ctypes.POINTER(NET_LUID)]
    iphlpapi.ConvertInterfaceAliasToLuid.restype = wintypes.ULONG

    iphlpapi.ConvertInterfaceLuidToIndex.argtypes = [ctypes.POINTER(NET_LUID), ctypes.POINTER(wintypes.ULONG)]
    iphlpapi.ConvertInterfaceLuidToIndex.restype = wintypes.ULONG

    iphlpapi.ConvertInterfaceIndexToLuid.argtypes = [wintypes.ULONG, ctypes.POINTER(NET_LUID)]
    iphlpapi.ConvertInterfaceIndexToLuid.restype = wintypes.ULONG

    iphlpapi.ConvertInterfaceLuidToAlias.argtypes = [ctypes.POINTER(NET_LUID), ctypes.c_wchar_p, ctypes.c_size_t]
    iphlpapi.ConvertInterfaceLuidToAlias.restype = wintypes.ULONG

    iphlpapi.GetBestRoute.argtypes = [wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(MIB_IPFORWARDROW)]
    iphlpapi.GetBestRoute.restype = wintypes.DWORD

def win32_get_best_interface_index(dest_ip: str = "8.8.8.8") -> int:
    if not iphlpapi:
        return None
    try:
        import struct
        dest_addr = struct.unpack("I", socket.inet_aton(dest_ip))[0]
        row = MIB_IPFORWARDROW()
        res = iphlpapi.GetBestRoute(dest_addr, 0, ctypes.byref(row))
        if res == 0:
            return row.dwForwardIfIndex
    except Exception:
        pass
    return None

def win32_alias_to_index(alias: str) -> int:
    if not iphlpapi or not alias:
        return None
    try:
        luid = NET_LUID()
        res = iphlpapi.ConvertInterfaceAliasToLuid(alias, ctypes.byref(luid))
        if res != 0:
            return None
        idx = wintypes.ULONG()
        res = iphlpapi.ConvertInterfaceLuidToIndex(ctypes.byref(luid), ctypes.byref(idx))
        if res != 0:
            return None
        return idx.value
    except Exception:
        return None

def win32_index_to_alias(index: int) -> str:
    if not iphlpapi or index is None:
        return None
    try:
        luid = NET_LUID()
        res = iphlpapi.ConvertInterfaceIndexToLuid(index, ctypes.byref(luid))
        if res != 0:
            return None
        buf = ctypes.create_unicode_buffer(IF_MAX_STRING_SIZE + 1)
        res = iphlpapi.ConvertInterfaceLuidToAlias(ctypes.byref(luid), buf, IF_MAX_STRING_SIZE + 1)
        if res != 0:
            return None
        return buf.value
    except Exception:
        return None

# Helper to get the app directory
def get_app_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _find_router_python(router_dir):
    """
    Tìm đúng Python executable để chạy c69-router uvicorn.
    Ưu tiên theo thứ tự:
    1. .venv trong router_dir (nếu có)
    2. Python trong PATH hệ thống (nếu có uvicorn)
    Trả về (python_exe, error_msg)
    """
    # 1. Check .venv trong router_dir
    for venv_python in [
        os.path.join(router_dir, ".venv", "Scripts", "python.exe"),
        os.path.join(router_dir, "venv", "Scripts", "python.exe"),
    ]:
        if os.path.exists(venv_python):
            return venv_python, None

    # 2. Check sys._base_executable (nếu chạy trong venv bình thường)
    base_exe = getattr(sys, '_base_executable', None)
    if base_exe and os.path.exists(base_exe) and 'python' in base_exe.lower():
        return base_exe, None

    # 3. Dùng python từ PATH hệ thống
    for python_name in ["python.exe", "python3.exe", "python"]:
        try:
            result = subprocess.run(
                [python_name, "-c", "import uvicorn"],
                capture_output=True, timeout=5
            )
            if result.returncode == 0:
                return python_name, None
        except Exception:
            pass

    return None, "Không tìm thấy Python có uvicorn. Hãy cài đặt c69-router và chạy pip install -r requirements.txt trong thư mục đó."


def _check_and_download_binaries(bin_dir, log_cb):
    """
    Kiểm tra và tải sing-box.exe + wintun.dll nếu chưa có.
    bin_dir: thư mục đích (luôn là cạnh exe, không cần Python).
    Trả về (success, error_msg)
    """
    os.makedirs(bin_dir, exist_ok=True)
    singbox_exe = os.path.join(bin_dir, "sing-box.exe")
    wintun_dll  = os.path.join(bin_dir, "wintun.dll")

    SINGBOX_URL = "https://github.com/SagerNet/sing-box/releases/download/v1.13.14/sing-box-1.13.14-windows-amd64.zip"
    WINTUN_URL  = "https://www.wintun.net/builds/wintun-0.14.1.zip"

    context = ssl._create_unverified_context()

    if not os.path.exists(singbox_exe):
        log_cb(f"⚠️ Không tìm thấy sing-box.exe — bắt đầu tải xuống...", "warning")
        log_cb(f"   Đường dẫn lưu: {singbox_exe}", "info")
        try:
            req = urllib.request.Request(SINGBOX_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=context, timeout=120) as resp:
                zip_data = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                for name in z.namelist():
                    if name.endswith("sing-box.exe"):
                        with open(singbox_exe, "wb") as f:
                            f.write(z.read(name))
                        log_cb(f"✅ Tải sing-box.exe thành công → {singbox_exe}", "success")
                        break
                else:
                    return False, "Không tìm thấy sing-box.exe trong file zip tải về."
        except Exception as e:
            return False, f"Tải sing-box.exe thất bại: {e}"
    else:
        log_cb(f"✅ sing-box.exe đã có tại: {singbox_exe}", "info")

    if not os.path.exists(wintun_dll):
        log_cb(f"⚠️ Không tìm thấy wintun.dll — bắt đầu tải xuống...", "warning")
        log_cb(f"   Đường dẫn lưu: {wintun_dll}", "info")
        try:
            req = urllib.request.Request(WINTUN_URL, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, context=context, timeout=60) as resp:
                zip_data = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_data)) as z:
                for name in z.namelist():
                    if name.endswith("wintun/bin/amd64/wintun.dll"):
                        with open(wintun_dll, "wb") as f:
                            f.write(z.read(name))
                        log_cb(f"✅ Tải wintun.dll thành công → {wintun_dll}", "success")
                        break
                else:
                    return False, "Không tìm thấy wintun.dll trong file zip tải về."
        except Exception as e:
            return False, f"Tải wintun.dll thất bại: {e}"
    else:
        log_cb(f"✅ wintun.dll đã có tại: {wintun_dll}", "info")

    return True, (singbox_exe, wintun_dll)


def _copy_binary_to_router(src, dst_dir, log_cb):
    """
    Copy một file binary từ bin_dir vào router_dir nếu chưa có ở đó.
    singbox_manager.py cần sing-box.exe ở PROJECT_DIR (tức router_dir).
    """
    import shutil
    dst = os.path.join(dst_dir, os.path.basename(src))
    if not os.path.exists(dst):
        try:
            shutil.copy2(src, dst)
            log_cb(f"📎 Đã copy {os.path.basename(src)} → {dst}", "info")
        except Exception as e:
            log_cb(f"⚠️ Không copy được {os.path.basename(src)} vào c69-router: {e}", "warning")


def _wait_for_port(host, port, timeout=20.0, interval=0.5, log_cb=None):
    """
    Chờ cho đến khi port được mở, hoặc timeout.
    Trả về True nếu port sẵn sàng trong thời gian timeout.
    """
    deadline = time.time() + timeout
    attempts = 0
    while time.time() < deadline:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect((host, port))
            s.close()
            return True
        except Exception:
            pass
        attempts += 1
        if log_cb and attempts % 4 == 0:  # Log mỗi 2 giây
            remaining = int(deadline - time.time())
            log_cb(f"⏳ Đang chờ server khởi động trên cổng {port}... (còn {remaining}s)", "info")
        time.sleep(interval)
    return False


def start_router_impl(bridge_obj, config_json, c69_base_url, log_callback=None):
    """
    Khởi động hệ thống định tuyến GenRouter.
    
    log_callback: callable(message: str, level: str) — gửi log về UI.
                  level có thể là 'info', 'success', 'warning', 'error'.
    """
    def log(msg, level="info"):
        print(f"[QHTD Router] [{level.upper()}] {msg}")
        if log_callback:
            try:
                log_callback(msg, level)
            except Exception:
                pass

    try:
        # Log raw config payload
        try:
            debug_log_path = os.path.join(get_app_dir(), "router_debug.txt")
            with open(debug_log_path, "a", encoding="utf-8") as f_dbg:
                f_dbg.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Raw config: {config_json}\n")
        except Exception as log_ex:
            print(f"[QHTD] Logging config failed: {log_ex}")

        config = json.loads(config_json)
        bridge_obj.router_config = config
        
        lan_if = config.get("lan_interface") or config.get("interface") or config.get("lan") or config.get("lan_if")
        wan_if = config.get("wan_interface") or config.get("wan") or config.get("wan_if")
        dhcp_start = config.get("dhcp_range_start") or config.get("dhcp_start") or config.get("dhcpRangeStart") or config.get("dhcpStart")
        dhcp_end = config.get("dhcp_range_end") or config.get("dhcp_end") or config.get("dhcpRangeEnd") or config.get("dhcpEnd")
        dns_server = config.get("dns_server") or config.get("dns") or config.get("dnsServer")
        
        if not lan_if:
            return json.dumps({"error": f"Vui lòng chọn card mạng LAN. (Nhận được: {config_json})"})
            
        # ─── Thư mục đích cho binary (luôn cạnh exe) ────────────────
        app_dir = get_app_dir()
        bin_dir = os.path.join(app_dir, "c69-router")  # [tool_dir]\c69-router\
        os.makedirs(bin_dir, exist_ok=True)
        log(f"📁 Thư mục tool: {app_dir}", "info")
        log(f"   Binary sẽ được lưu tại: {bin_dir}", "info")

        # ─── BƯỚC 1: Kiểm tra & Tải binary (sing-box, wintun) ────
        log("🔍 Bước 1/4: Kiểm tra file binary sing-box và wintun...", "info")
        ok, result = _check_and_download_binaries(bin_dir, log)
        if not ok:
            return json.dumps({"error": f"Không thể chuẩn bị binary định tuyến: {result}"})
        singbox_exe, wintun_dll = result

        # ─── Tìm router_dir cho uvicorn API (tùy chọn, không bắt buộc) ─
        # Trước tiên: kiểm tra bin_dir chính nó có code FastAPI không
        # (client distribute: c69-router/ nằm cạnh exe, có app/ subfolder)
        router_dir = None
        candidate_dirs = [
            bin_dir,                                                              # [exe]/c69-router/ — client standard
            os.path.join(os.path.dirname(app_dir), "c69-router"),               # [dist]/../c69-router — dev dist/
            os.path.join(os.path.dirname(os.path.dirname(app_dir)), "c69-router"),  # dev workspace
        ]
        for candidate in candidate_dirs:
            norm = os.path.normpath(candidate)
            if os.path.isdir(norm) and os.path.isdir(os.path.join(norm, "app")):
                router_dir = norm
                break

        if router_dir:
            log(f"✅ Tìm thấy c69-router API tại: {router_dir}", "success")
            # Copy binary sang router_dir để singbox_manager.py tìm thấy
            if os.path.normpath(router_dir) != os.path.normpath(bin_dir):
                _copy_binary_to_router(singbox_exe, router_dir, log)
                _copy_binary_to_router(wintun_dll, router_dir, log)
        else:
            log("⚠️ Không tìm thấy c69-router API (thiếu thư mục app/). uvicorn sẽ không được khởi động.", "warning")

        config_path = os.path.join(router_dir, "data", "config.json") if router_dir else None

        log("⚙️ Bước 2/4: Cập nhật cấu hình định tuyến...", "info")
        config_data = {}
        if config_path and os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                try:
                    config_data = json.load(f)
                except Exception:
                    pass

        def get_alias_from_index_or_name(iface):
            if not iface:
                return ""
            if str(iface).isdigit():
                idx = int(iface)
                if idx in bridge_obj._index_to_interface:
                    return bridge_obj._index_to_interface[idx]
                
                try:
                    ifaces = json.loads(bridge_obj._cached_interfaces)
                    for item in ifaces:
                        if item.get("name") == str(iface) and item.get("friendly_name"):
                            friendly_name = item.get("friendly_name")
                            bridge_obj._index_to_interface[idx] = friendly_name
                            bridge_obj._interface_to_index[friendly_name] = idx
                            return friendly_name
                except Exception:
                    pass
                
                alias = win32_index_to_alias(idx)
                if alias:
                    bridge_obj._index_to_interface[idx] = alias
                    bridge_obj._interface_to_index[alias] = idx
                    return alias
            else:
                alias = str(iface)
                if alias in bridge_obj._interface_to_index:
                    return alias
                try:
                    ifaces = json.loads(bridge_obj._cached_interfaces)
                    for item in ifaces:
                        if item.get("friendly_name") == alias and item.get("name"):
                            idx = int(item.get("name"))
                            bridge_obj._interface_to_index[alias] = idx
                            bridge_obj._index_to_interface[idx] = alias
                            break
                except Exception:
                    pass
                
                if alias not in bridge_obj._interface_to_index:
                    idx = win32_alias_to_index(alias)
                    if idx is not None:
                        bridge_obj._interface_to_index[alias] = idx
                        bridge_obj._index_to_interface[idx] = alias
            return str(iface)

        lan_alias = get_alias_from_index_or_name(lan_if)

        # Auto-detect WAN interface if not provided in the payload
        if not wan_if:
            best_idx = win32_get_best_interface_index("8.8.8.8")
            if best_idx is not None:
                detected_alias = get_alias_from_index_or_name(best_idx)
                if detected_alias and detected_alias != lan_alias:
                    wan_if = str(best_idx)
            
            if not wan_if:
                old_wan = config_data.get("wan_interface")
                if old_wan and old_wan != lan_alias:
                    wan_if = old_wan

            if not wan_if:
                try:
                    import psutil
                    addrs = psutil.net_if_addrs()
                    for alias in addrs.keys():
                        if alias != lan_alias:
                            for addr in addrs[alias]:
                                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                                    wan_if = alias
                                    break
                        if wan_if:
                            break
                except Exception:
                    pass

            if not wan_if:
                wan_if = "Wi-Fi" if lan_alias != "Wi-Fi" else "Ethernet"

        wan_alias = get_alias_from_index_or_name(wan_if)
        log(f"🌐 LAN: {lan_alias}, WAN: {wan_alias}", "info")
        
        config_data["lan_interface"] = lan_alias
        config_data["wan_interface"] = wan_alias
        if dhcp_start:
            config_data["dhcp_range_start"] = dhcp_start
        if dhcp_end:
            config_data["dhcp_range_end"] = dhcp_end
        if dns_server:
            config_data["dns_server"] = dns_server

        if config_path:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            log(f"✅ Đã ghi cấu hình vào {config_path}", "info")
            
        # ─── BƯỚC 2b. Dynamic Router IP Calculation ──────────────
        router_ip = "192.168.88.1"
        if dhcp_start:
            parts = dhcp_start.split('.')
            if len(parts) == 4:
                router_ip = f"{parts[0]}.{parts[1]}.{parts[2]}.1"
        
        import psutil
        addrs = psutil.net_if_addrs()
        has_ip = False
        if lan_alias in addrs:
            for addr in addrs[lan_alias]:
                if addr.family == socket.AF_INET and addr.address == router_ip:
                    has_ip = True
                    break
        
        if not has_ip:
            log(f"🔧 Đặt IP {router_ip} cho card {lan_alias}...", "info")
            if str(lan_if).isdigit():
                ps_script = (
                    f"Remove-NetIPAddress -InterfaceIndex {lan_if} -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                    f"New-NetIPAddress -InterfaceIndex {lan_if} -IPAddress '{router_ip}' -PrefixLength 24; "
                    f"Set-DnsClientServerAddress -InterfaceIndex {lan_if} -ServerAddresses ('8.8.8.8','1.1.1.1')"
                )
            else:
                ps_script = (
                    f"Remove-NetIPAddress -InterfaceAlias '{lan_alias}' -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                    f"New-NetIPAddress -InterfaceAlias '{lan_alias}' -IPAddress '{router_ip}' -PrefixLength 24; "
                    f"Set-DnsClientServerAddress -InterfaceAlias '{lan_alias}' -ServerAddresses ('8.8.8.8','1.1.1.1')"
                )
            
            cmd_run = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {ps_script}' -Verb RunAs -WindowStyle Hidden\""
            subprocess.run(cmd_run, shell=True)
            log(f"✅ Đã gán IP {router_ip}/24 cho {lan_alias}.", "success")
        else:
            log(f"✅ Card {lan_alias} đã có IP {router_ip}/24 — bỏ qua bước gán IP.", "info")
            
        # ─── BƯỚC 3: Tìm Python và khởi động API Server ──────────
        if not router_dir:
            # Không có c69-router/app/ → chỉ có binary, không chạy uvicorn
            log("⚠️ Bỏ qua Bước 3/4 (không có c69-router API). sing-box sẵn sàng tại bin_dir.", "warning")
            bridge_obj.router_active = True
            log(f"✅ Binary định tuyến sẵn sàng tại: {bin_dir}", "success")
            log(f"   sing-box.exe: {singbox_exe}", "info")
            log(f"   wintun.dll:   {wintun_dll}", "info")
            return json.dumps({"success": True, "note": "Binary OK, no API server (c69-router not found)"})

        # ─── BƯỚC 3: Khởi động API Server (Ưu tiên Rust Native Core) ──────────
        rust_exe = os.path.join(router_dir, "c69-router.exe")
        if not os.path.exists(rust_exe):
            rust_exe = os.path.join(router_dir, "c69-router-rust", "target", "release", "c69-router-core.exe")
            
        if os.path.exists(rust_exe):
            log(f"🚀 Phát hiện C69-Router Rust Native Core tại: {rust_exe}", "info")
            api_cmd = (
                f"powershell -Command \"Start-Process '{rust_exe}' "
                f"-Verb RunAs -WorkingDirectory '{router_dir}' -WindowStyle Hidden\""
            )
            subprocess.run(api_cmd, shell=True)
            log("🚀 Đã gửi lệnh khởi động C69-Router Rust Core...", "info")
        else:
            log("🔍 Bước 3/4: Tìm Python và khởi động c69-router API server...", "info")
            python_exe, python_err = _find_router_python(router_dir)
            if not python_exe:
                return json.dumps({"error": f"Bước 3 thất bại: {python_err}"})
            
            log(f"🐍 Sử dụng Python: {python_exe}", "info")
            
            # Kill any existing process on port 8000 first
            kill_ps = (
                "$p = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; "
                "if ($p) { Stop-Process -Id $p.OwningProcess -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                f"powershell -Command \"{kill_ps}\"",
                shell=True, capture_output=True, timeout=5
            )
            time.sleep(0.5)

            # Khởi động API server
            api_cmd = (
                f"powershell -Command \"Start-Process '{python_exe}' "
                f"-ArgumentList '-m uvicorn app.main:app --host 0.0.0.0 --port 8000' "
                f"-Verb RunAs -WorkingDirectory '{router_dir}' -WindowStyle Hidden\""
            )
            subprocess.run(api_cmd, shell=True)
            log("🚀 Đã gửi lệnh khởi động API server uvicorn...", "info")

        # ─── BƯỚC 4: Chờ server sẵn sàng ────────────────────────
        log("⏳ Bước 4/4: Chờ API server lắng nghe cổng 8000...", "info")
        server_ready = _wait_for_port("127.0.0.1", 8000, timeout=20.0, interval=0.5, log_cb=log)
        
        if not server_ready:
            bridge_obj.router_active = False
            err_msg = (
                "API server không khởi động được trên cổng 8000 sau 20 giây.\n"
                f"Hãy kiểm tra:\n"
                f"  1. Python có đúng không: {python_exe}\n"
                f"  2. uvicorn đã cài chưa (pip install uvicorn fastapi)\n"
                f"  3. sing-box.exe có trong: {router_dir}\n"
                f"  4. Chạy tool với quyền Administrator"
            )
            log(f"❌ {err_msg}", "error")
            return json.dumps({"error": err_msg})
        
        bridge_obj.router_active = True
        log(f"✅ Định tuyến đã khởi động thành công! LAN={lan_alias} (IP={router_ip}), WAN={wan_alias}", "success")
        return json.dumps({"success": True})
    except Exception as e:
        import traceback
        err_detail = traceback.format_exc()
        print(f"[QHTD Router] Exception: {err_detail}")
        if log_callback:
            try:
                log_callback(f"❌ Lỗi không xác định: {e}", "error")
            except Exception:
                pass
        return json.dumps({"error": str(e)})


def stop_router_impl(bridge_obj):
    try:
        bridge_obj.router_active = False
        
        ps_kill = (
            "$p = Get-NetUDPEndpoint -LocalPort 67 -ErrorAction SilentlyContinue; "
            "if ($p) { Stop-Process -Id $p.OwningProcess -Force -ErrorAction SilentlyContinue }; "
            "$p2 = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue; "
            "if ($p2) { Stop-Process -Id $p2.OwningProcess -Force -ErrorAction SilentlyContinue }; "
            "Stop-Process -Name sing-box -Force -ErrorAction SilentlyContinue"
        )
        
        cmd_run = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {ps_kill}' -Verb RunAs -WindowStyle Hidden\""
        subprocess.run(cmd_run, shell=True)
        print("[QHTD] Stopped routing and DHCP server")
        return json.dumps({"success": True})
    except Exception as e:
        return json.dumps({"error": str(e)})
