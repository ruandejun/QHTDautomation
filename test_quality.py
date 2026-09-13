import subprocess
import time
from PIL import Image
import io

adb = r"d:\Workspace\Python\QHTDautomation\bin\platform-tools\adb.exe"

# Capture raw screen from device 2 (ce03171371483c3c05)
res = subprocess.run([adb, "-s", "ce03171371483c3c05", "exec-out", "screencap", "-p"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
raw = res.stdout
print(f"Captured raw image: {len(raw)} bytes")

img = Image.open(io.BytesIO(raw))
print(f"Original size: {img.size}")

# Test 1: Old way (260x534, NEAREST)
t0 = time.time()
img_nearest = img.resize((260, 534), Image.NEAREST)
buf_nearest = io.BytesIO()
img_nearest.convert("RGB").save(buf_nearest, format="JPEG", quality=70)
dt1 = time.time() - t0
print(f"Old Nearest 260x534: {len(buf_nearest.getvalue())} bytes in {dt1*1000:.2f}ms")
img_nearest.save(r"d:\Workspace\Python\QHTDautomation\test_nearest.png")

# Test 2: New way (360x740, BILINEAR / TRIANGLE)
t0 = time.time()
img_bilinear = img.resize((360, 740), Image.BILINEAR)
buf_bilinear = io.BytesIO()
img_bilinear.convert("RGB").save(buf_bilinear, format="JPEG", quality=80)
dt2 = time.time() - t0
print(f"New Bilinear 360x740: {len(buf_bilinear.getvalue())} bytes in {dt2*1000:.2f}ms")
img_bilinear.save(r"d:\Workspace\Python\QHTDautomation\test_bilinear.png")

