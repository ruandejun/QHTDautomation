import os
import sys

def find_installed_windows_sdk():
    preferred_versions = ["10.0.22621.0", "10.0.20348.0", "10.0.19041.0", "10.0.17763.0"]
    for root_dir in [r"C:\Program Files (x86)\Windows Kits\10\Include", r"C:\Program Files\Windows Kits\10\Include"]:
        if os.path.exists(root_dir):
            versions = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d)) and d.startswith("10.0.")]
            print(f"[SDK_FINDER] Installed SDKs in {root_dir}: {versions}")
            for pref in preferred_versions:
                if pref in versions:
                    print(f"[SDK_FINDER] Selected preferred stable SDK: {pref}")
                    return pref
            if versions:
                versions.sort(key=lambda s: [int(u) for u in s.split('.') if u.isdigit()])
                print(f"[SDK_FINDER] Selected latest available SDK: {versions[-1]}")
                return versions[-1]
    return "10.0.22621.0"

def fix_windows_sdk_headers(sdk_ver):
    """Sua triet de loi Microsoft SDK thieu dinh nghia NTDDI_WIN11_BR (0x0A00000C)"""
    inject_defs = (
        "/* QHTD Clang compilation fix for NTDDI_WIN11_BR and FILE_INFO_BY_HANDLE_CLASS */\n"
        "#ifndef NTDDI_WIN11_BR\n"
        "#define NTDDI_WIN11_BR 0x0A00000C\n"
        "#endif\n"
        "#ifndef NTDDI_VERSION\n"
        "#define NTDDI_VERSION 0x0A00000C\n"
        "#endif\n"
    )
    for root_dir in [r"C:\Program Files (x86)\Windows Kits\10\Include", r"C:\Program Files\Windows Kits\10\Include"]:
        sdk_root = os.path.join(root_dir, sdk_ver)
        if not os.path.exists(sdk_root):
            continue
        for target in ["sdkddkver.h", "minwinbase.h"]:
            filepath = os.path.join(sdk_root, "shared", target)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        c = f.read()
                    if "NTDDI_WIN11_BR 0x0A00000C" not in c:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(inject_defs + "\n" + c)
                        print(f"[GenerateArgs] Patched SDK shared: {filepath}")
                except Exception as e:
                    print(f"[WARNING] Could not patch {filepath}: {e}")

        for target in ["fileapi.h", "winbase.h", "fileapifromapp.h"]:
            filepath = os.path.join(sdk_root, "um", target)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        c = f.read()
                    if "QHTD_MINWINBASE_FIX_V2" not in c:
                        um_fix = (
                            "/* QHTD Clang compilation fix for FILE_INFO_BY_HANDLE_CLASS */\n"
                            "#ifndef QHTD_MINWINBASE_FIX_V2\n"
                            "#define QHTD_MINWINBASE_FIX_V2\n"
                            + inject_defs +
                            "#include <sdkddkver.h>\n"
                            "#include <minwinbase.h>\n"
                            "#endif\n\n"
                        )
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(um_fix + c)
                        print(f"[GenerateArgs] Patched SDK um: {filepath}")
                except Exception as e:
                    print(f"[WARNING] Could not patch {filepath}: {e}")

def patch_win_build_gn(src_root="."):
    path = os.path.join(src_root, "build", "config", "win", "BUILD.gn")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                c = f.read()
            import re
            c = re.sub(r'["\']NTDDI_VERSION=NTDDI_WIN11_BR["\']', '"NTDDI_VERSION=0x0A00000C",\n    "NTDDI_WIN11_BR=0x0A00000C"', c)
            with open(path, "w", encoding="utf-8") as f:
                f.write(c)
            print(f"[GenerateArgs] Patched NTDDI_VERSION in {path}")
        except Exception as e:
            print(f"[WARNING] Could not patch {path}: {e}")

def ensure_version_files(src_root="."):
    files = [
        (os.path.join(src_root, "build", "util", "LASTCHANGE"), "LASTCHANGE=128.0.6613.119-qhtd\n"),
        (os.path.join(src_root, "build", "util", "LASTCHANGE.committime"), "1725148800\n"),
        (os.path.join(src_root, "build", "util", "LASTCHANGE.blink"), "LASTCHANGE=128.0.6613.119\n"),
        (os.path.join(src_root, "gpu", "webgpu", "DAWN_VERSION"), "128.0.6613.119\n"),
        (os.path.join(src_root, "gpu", "webgpu", "dawn_commit_hash.h"), "#ifndef GPU_WEBGPU_DAWN_COMMIT_HASH_H_\n#define GPU_WEBGPU_DAWN_COMMIT_HASH_H_\n#define DAWN_COMMIT_HASH \"128.0.6613.119\"\n#endif\n"),
        (os.path.join(src_root, "gpu", "config", "gpu_lists_version.h"), "#ifndef GPU_CONFIG_GPU_LISTS_VERSION_H_\n#define GPU_CONFIG_GPU_LISTS_VERSION_H_\n#define GPU_LISTS_VERSION \"128.0.6613.119\"\n#endif\n"),
        (os.path.join(src_root, "skia", "ext", "skia_commit_hash.h"), "#ifndef SKIA_EXT_SKIA_COMMIT_HASH_H_\n#define SKIA_EXT_SKIA_COMMIT_HASH_H_\n#define SKIA_COMMIT_HASH \"128.0.6613.119\"\n#endif\n"),
    ]
    for filepath, content in files:
        parent = os.path.dirname(filepath)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[GenerateArgs] Version file verified: {filepath}")

def main():
    sdk_ver = find_installed_windows_sdk()
    print(f"[GenerateArgs] Detected Windows SDK: {sdk_ver}")
    fix_windows_sdk_headers(sdk_ver)
    patch_win_build_gn(".")
    ensure_version_files(".")

    os.makedirs("out/Release", exist_ok=True)
    args_content = f"""is_debug = false
is_official_build = false
symbol_level = 0
blink_symbol_level = 0
v8_symbol_level = 0
enable_nacl = false
is_component_build = false
chrome_pgo_phase = 0
treat_warnings_as_errors = false
dcheck_always_on = false
enable_iterator_debugging = false
exclude_unwind_tables = true
enable_resource_allowlist_generation = false
use_remoteexec = false
use_siso = false
windows_sdk_version = "{sdk_ver}"
"""
    with open("out/Release/args.gn", "w", encoding="utf-8") as f:
        f.write(args_content)
    print("[GenerateArgs] Successfully generated out/Release/args.gn")

if __name__ == "__main__":
    main()
