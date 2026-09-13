import subprocess

adb = r"d:\Workspace\Python\QHTDautomation\bin\platform-tools\adb.exe"

def run(args):
    return subprocess.run([adb] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()

lines = run(["devices", "-l"]).splitlines()
devs = [line.split()[0] for line in lines[1:] if len(line.split()) >= 2 and line.split()[1] == 'device']

print(f"Total devices: {len(devs)}")
for d in devs:
    s = run(["-s", d, "shell", "wm", "size"]).replace("\n", " | ")
    den = run(["-s", d, "shell", "wm", "density"]).replace("\n", " | ")
    top = run(["-s", d, "shell", "dumpsys", "window", "windows"]).splitlines()
    focused = [l.strip() for l in top if 'mCurrentFocus' in l or 'mFocusedApp' in l]
    print(f"Device {d}:")
    print(f"  Size: {s}")
    print(f"  Density: {den}")
    print(f"  Focus: {focused[:1]}")
