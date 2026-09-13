import urllib.request
import json

try:
    req = urllib.request.urlopen("http://127.0.0.1:9090/api/devices")
    devices = json.loads(req.read().decode())
    print(f"Total live devices detected: {len(devices)}")
    for d in devices:
        print(f" - Serial: {d['serial']} | Model: {d['brand']} {d['model']} | Res: {d['width']}x{d['height']} | State: {d['state']}")
    
    if devices:
        s = devices[0]['serial']
        print(f"\nScanning Wi-Fi on device {s}...")
        w_req = urllib.request.urlopen(f"http://127.0.0.1:9090/api/devices/{s}/wifi/scan")
        w_data = json.loads(w_req.read().decode())
        nets = w_data.get("networks", [])
        print(f"Wi-Fi Scan Results: found {len(nets)} networks")
        for net in nets[:5]:
            print(f"   * SSID: {net['ssid']} | Level: {net['signal_level']} dBm | Freq: {net['frequency']} | Sec: {net['security']} | Connected: {net['is_connected']}")
except Exception as e:
    print("Error:", e)
