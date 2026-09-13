import subprocess

adb = r"d:\Workspace\Python\QHTDautomation\bin\platform-tools\adb.exe"

def run(args):
    return subprocess.run([adb] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout.strip()

lines = run(["devices", "-l"]).splitlines()
devs = [line.split()[0] for line in lines[1:] if len(line.split()) >= 2 and line.split()[1] == 'device']

print(f"Optimizing {len(devs)} devices to 720x1480 / 280dpi / Portrait...")
for d in devs:
    run(["-s", d, "shell", "wm", "size", "720x1480"])
    run(["-s", d, "shell", "wm", "density", "280"])
    run(["-s", d, "shell", "settings", "put", "system", "accelerometer_rotation", "0"])
    run(["-s", d, "shell", "settings", "put", "system", "user_rotation", "0"])
    print(f" -> Device {d}: Optimized HD+ Portrait OK")

print("All devices optimized!")
