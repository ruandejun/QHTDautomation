import subprocess
import time
import os

adb = r"d:\Workspace\Python\QHTDautomation\bin\platform-tools\adb.exe"

def run_adb(args):
    res = subprocess.run([adb] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return res.stdout, res.stderr, res.returncode

# 1. List devices
stdout, _, _ = run_adb(["devices", "-l"])
lines = stdout.decode('utf-8', errors='ignore').strip().splitlines()
devices = []
for line in lines[1:]:
    parts = line.split()
    if len(parts) >= 2 and parts[1] == 'device':
        devices.append(parts[0])

print(f"Total connected devices: {len(devices)}")
for i, d in enumerate(devices):
    # Check screen on / power
    out_wake, _, _ = run_adb(["-s", d, "shell", "dumpsys", "window", "displays"])
    out_wake_str = out_wake.decode('utf-8', errors='ignore')
    mScreenState = [line.strip() for line in out_wake_str.splitlines() if 'mScreenState' in line or 'init=' in line]
    
    # Check screen size
    out_size, _, _ = run_adb(["-s", d, "shell", "wm", "size"])
    size_str = out_size.decode('utf-8', errors='ignore').strip()
    
    # Check screencap
    t0 = time.time()
    img_data, err, code = run_adb(["-s", d, "exec-out", "screencap", "-p"])
    dt = time.time() - t0
    
    print(f"[{i+1}] Serial: {d} | Size: {size_str} | Screencap: {len(img_data)} bytes in {dt:.3f}s | Code: {code}")
    if len(img_data) < 1000:
        print(f"    --> ERROR / EMPTY SCREENCAP: {err.decode('utf-8', errors='ignore')}")
    else:
        # Save sample
        sample_path = f"d:\\Workspace\\Python\\QHTDautomation\\sample_{i+1}_{d}.png"
        with open(sample_path, "wb") as f:
            f.write(img_data)
        print(f"    --> Saved sample to {sample_path} ({os.path.getsize(sample_path)} bytes)")

