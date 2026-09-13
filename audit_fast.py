import subprocess
import time
import os

adb = r"d:\Workspace\Python\QHTDautomation\bin\platform-tools\adb.exe"

def run_adb(args, timeout=5):
    try:
        res = subprocess.run([adb] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
        return res.stdout, res.stderr, res.returncode
    except subprocess.TimeoutExpired:
        return b"", b"TIMEOUT", -1
    except Exception as e:
        return b"", str(e).encode(), -1

stdout, _, _ = run_adb(["devices", "-l"])
lines = stdout.decode('utf-8', errors='ignore').strip().splitlines()
devices = []
for line in lines[1:]:
    parts = line.split()
    if len(parts) >= 2 and parts[1] == 'device':
        devices.append(parts[0])

print(f"Total connected devices: {len(devices)}")
for i, d in enumerate(devices):
    out_size, _, _ = run_adb(["-s", d, "shell", "wm", "size"])
    size_str = out_size.decode('utf-8', errors='ignore').strip()
    
    t0 = time.time()
    img_data, err, code = run_adb(["-s", d, "exec-out", "screencap", "-p"], timeout=4)
    dt = time.time() - t0
    
    print(f"[{i+1}] Serial: {d} | Size: {size_str} | Screencap: {len(img_data)} bytes ({dt:.3f}s) | Code: {code}")
    if code != 0 or len(img_data) < 1000:
        print(f"    --> ERROR: {err.decode('utf-8', errors='ignore')}")
    else:
        sample_path = f"d:\\Workspace\\Python\\QHTDautomation\\sample_{i+1}_{d}.png"
        with open(sample_path, "wb") as f:
            f.write(img_data)

