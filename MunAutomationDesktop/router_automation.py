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

def start_router_impl(bridge_obj, config_json, c69_base_url):
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
        dns_server = config.get("dns_server") or config.get("dns") or config.get("dnsServer") or "8.8.8.8"
        
        if not lan_if:
            return json.dumps({"error": f"Vui lòng chọn card mạng LAN. (Nhận được: {config_json})"})
            
        router_dir = os.path.join(os.path.dirname(os.path.dirname(get_app_dir())), "phonefarm-router")
        config_path = os.path.join(router_dir, "data", "config.json")
        
        # 1. Read existing phonefarm-router config.json for fallback
        config_data = {}
        if os.path.exists(config_path):
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
        
        config_data["lan_interface"] = lan_alias
        config_data["wan_interface"] = wan_alias
        if dhcp_start:
            config_data["dhcp_range_start"] = dhcp_start
        if dhcp_end:
            config_data["dhcp_range_end"] = dhcp_end
        if dns_server:
            config_data["dns_server"] = dns_server
            
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=2, ensure_ascii=False)
            
        # 2. Dynamic Router IP Calculation
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
            if str(lan_if).isdigit():
                ps_script = (
                    f"Remove-NetIPAddress -InterfaceIndex {lan_if} -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                    f"New-NetIPAddress -InterfaceIndex {lan_if} -IPAddress '{router_ip}' -PrefixLength 24 -DefaultGateway $null; "
                    f"Set-DnsClientServerAddress -InterfaceIndex {lan_if} -ServerAddresses ('8.8.8.8','1.1.1.1')"
                )
            else:
                ps_script = (
                    f"Remove-NetIPAddress -InterfaceAlias '{lan_alias}' -AddressFamily IPv4 -Confirm:$false -ErrorAction SilentlyContinue; "
                    f"New-NetIPAddress -InterfaceAlias '{lan_alias}' -IPAddress '{router_ip}' -PrefixLength 24 -DefaultGateway $null; "
                    f"Set-DnsClientServerAddress -InterfaceAlias '{lan_alias}' -ServerAddresses ('8.8.8.8','1.1.1.1')"
                )
            
            cmd_run = f"powershell -Command \"Start-Process powershell -ArgumentList '-Command {ps_script}' -Verb RunAs -WindowStyle Hidden\""
            subprocess.run(cmd_run, shell=True)
            
        # 3. Start API server (GenRouter v2.0 Unified)
        api_cmd = f"powershell -Command \"Start-Process '{sys.executable}' -ArgumentList '-m uvicorn app.main:app --host 0.0.0.0 --port 8000' -Verb RunAs -WorkingDirectory '{router_dir}' -WindowStyle Hidden\""
        subprocess.run(api_cmd, shell=True)
        
        bridge_obj.router_active = True
        print(f"[QHTD] Started routing dynamically: LAN={lan_alias} (IP={router_ip}), WAN={wan_alias}")
        return json.dumps({"success": True})
    except Exception as e:
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
