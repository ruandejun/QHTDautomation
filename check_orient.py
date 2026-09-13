import subprocess
from PIL import Image

adb = r"d:\Workspace\Python\QHTDautomation\bin\platform-tools\adb.exe"

def run(args):
    return subprocess.run([adb] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()

lines = run(["devices", "-l"]).splitlines()
devs = [line.split()[0] for line in lines[1:] if len(line.split()) >= 2 and line.split()[1] == 'device']

for d in devs:
    rot = run(["-s", d, "shell", "dumpsys", "input"]).splitlines()
    orient = [l.strip() for l in rot if 'SurfaceOrientation' in l or 'Orientation' in l]
    
    # Check screencap dimensions
    raw = subprocess.run([adb, "-s", d, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE).stdout
    if len(raw) > 1000:
        import io
        im = Image.open(io.BytesIO(raw))
        print(f"Device {d}: Screencap image size = {im.size} (W x H) | Orientation: {orient[:1]}")

