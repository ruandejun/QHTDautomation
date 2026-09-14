import os
import sys

def find_installed_windows_sdk():
    for root_dir in [r"C:\Program Files (x86)\Windows Kits\10\Include", r"C:\Program Files\Windows Kits\10\Include"]:
        if os.path.exists(root_dir):
            versions = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d)) and d.startswith("10.0.")]
            if versions:
                versions.sort(key=lambda s: [int(u) for u in s.split('.') if u.isdigit()])
                return versions[-1]
    return "10.0.22621.0"

def main():
    sdk_ver = find_installed_windows_sdk()
    print(f"[GenerateArgs] Detected Windows SDK: {sdk_ver}")

    os.makedirs("out/Release", exist_ok=True)
    args_content = f"""is_debug = false
is_official_build = false
symbol_level = 0
blink_symbol_level = 0
enable_nacl = false
is_component_build = false
chrome_pgo_phase = 0
treat_warnings_as_errors = false
dcheck_always_on = false
windows_sdk_version = "{sdk_ver}"
"""
    with open("out/Release/args.gn", "w", encoding="utf-8") as f:
        f.write(args_content)
    print("[GenerateArgs] Successfully generated out/Release/args.gn")

if __name__ == "__main__":
    main()
