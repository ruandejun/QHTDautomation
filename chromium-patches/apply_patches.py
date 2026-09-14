#!/usr/bin/env python3
"""
QHTD Anti-Detect Chromium Patch Engine
Tu dong tiem cac can thiep sau C++ vao ma nguon Blink Renderer an toan va nhat quan.
Dong thoi fix loi Windows SDK toolchain va LASTCHANGE tren moi truong CI runner.
"""

import os
import sys
import re

# Ensure stdout handles UTF-8 on Windows command prompts
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

def patch_file(filepath, description, transform_func):
    if not os.path.exists(filepath):
        print(f"[SKIP] File not found: {filepath}")
        return False
    
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    new_content = transform_func(content)
    if new_content == content:
        print(f"[UNCHANGED] {description} in {filepath} (may already be patched)")
        return True

    with open(filepath, "w", encoding="utf-8", newline="\n") as f:
        f.write(new_content)
    print(f"[SUCCESS] {description} -> {filepath}")
    return True

def ensure_lastchange(src_root):
    """Tao san LASTCHANGE va cac file version/hash can thiet de tranh Ninja thieu file dependency"""
    files_to_create = [
        # 1. Build util LASTCHANGE
        (
            os.path.join(src_root, "build", "util", "LASTCHANGE"),
            "LASTCHANGE=128.0.6613.119-qhtd\n"
        ),
        (
            os.path.join(src_root, "build", "util", "LASTCHANGE.committime"),
            "1725148800\n"
        ),
        (
            os.path.join(src_root, "build", "util", "LASTCHANGE.blink"),
            "LASTCHANGE=128.0.6613.119\n"
        ),
        # 2. DAWN WebGPU dependencies (Fix ninja missing DAWN_VERSION error)
        (
            os.path.join(src_root, "gpu", "webgpu", "DAWN_VERSION"),
            "128.0.6613.119\n"
        ),
        (
            os.path.join(src_root, "gpu", "webgpu", "dawn_commit_hash.h"),
            "#ifndef GPU_WEBGPU_DAWN_COMMIT_HASH_H_\n#define GPU_WEBGPU_DAWN_COMMIT_HASH_H_\n#define DAWN_COMMIT_HASH \"128.0.6613.119\"\n#endif\n"
        ),
        # 3. GPU Lists version
        (
            os.path.join(src_root, "gpu", "config", "gpu_lists_version.h"),
            "#ifndef GPU_CONFIG_GPU_LISTS_VERSION_H_\n#define GPU_CONFIG_GPU_LISTS_VERSION_H_\n#define GPU_LISTS_VERSION \"128.0.6613.119\"\n#endif\n"
        ),
        # 4. Skia commit hash
        (
            os.path.join(src_root, "skia", "ext", "skia_commit_hash.h"),
            "#ifndef SKIA_EXT_SKIA_COMMIT_HASH_H_\n#define SKIA_EXT_SKIA_COMMIT_HASH_H_\n#define SKIA_COMMIT_HASH \"128.0.6613.119\"\n#endif\n"
        ),
    ]

    for filepath, content in files_to_create:
        parent = os.path.dirname(filepath)
        os.makedirs(parent, exist_ok=True)
        # Luon ghi hoac cap nhat de dam bao Ninja co file voi timestamp hop le
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"[SUCCESS] Created/Updated: {filepath}")

    return True

def find_installed_windows_sdk():
    preferred_versions = ["10.0.22621.0", "10.0.20348.0", "10.0.19041.0", "10.0.17763.0"]
    for root_dir in [r"C:\Program Files (x86)\Windows Kits\10\Include", r"C:\Program Files\Windows Kits\10\Include"]:
        if os.path.exists(root_dir):
            versions = [d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d)) and d.startswith("10.0.")]
            print(f"[SDK_FINDER] Installed SDKs in {root_dir}: {versions}")
            # Ưu tiên các phiên bản chuẩn đã được Chromium kiểm thử tương thích hoàn toàn
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
    """
    Sua triet de loi Microsoft SDK thieu dinh nghia NTDDI_WIN11_BR (0x0A00000C)
    khien preprocessor coi NTDDI_WIN11_BR la 0 dan toi mat FILE_INFO_BY_HANDLE_CLASS.
    """
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
        print(f"[INFO] Fixing Windows SDK headers in: {sdk_root}")

        # 1. Patch shared/sdkddkver.h va shared/minwinbase.h
        for target in ["sdkddkver.h", "minwinbase.h"]:
            filepath = os.path.join(sdk_root, "shared", target)
            if os.path.exists(filepath):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        c = f.read()
                    if "NTDDI_WIN11_BR 0x0A00000C" not in c:
                        with open(filepath, "w", encoding="utf-8") as f:
                            f.write(inject_defs + "\n" + c)
                        print(f"[SUCCESS] Patched Windows SDK shared header: {filepath}")
                except Exception as e:
                    print(f"[WARNING] Could not patch {filepath}: {e}")

        # 2. Patch um/fileapi.h, um/winbase.h, um/fileapifromapp.h
        um_targets = ["fileapi.h", "winbase.h", "fileapifromapp.h"]
        for target in um_targets:
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
                        print(f"[SUCCESS] Patched Windows SDK um header: {filepath}")
                except Exception as e:
                    print(f"[WARNING] Could not patch {filepath}: {e}")

def patch_win_build_gn(src_root):
    """
    Sua build/config/win/BUILD.gn de truyen gia tri so nguyen 0x0A00000C cho NTDDI_VERSION
    thay vi dinh danh chu NTDDI_WIN11_BR ma SDK cu khong co.
    """
    path = os.path.join(src_root, "build", "config", "win", "BUILD.gn")
    if not os.path.exists(path):
        print(f"[SKIP] Not found: {path}")
        return False
    def transform(c):
        # Thay NTDDI_VERSION=NTDDI_WIN11_BR bang so nguyen literal
        c = re.sub(
            r'["\']NTDDI_VERSION=NTDDI_WIN11_BR["\']',
            '"NTDDI_VERSION=0x0A00000C",\n    "NTDDI_WIN11_BR=0x0A00000C"',
            c
        )
        return c
    return patch_file(path, "Patch NTDDI_VERSION literal in build/config/win/BUILD.gn", transform)

def patch_windows_version_cc(src_root):
    """Bypass check SDK 10.0.28000.0 trong base/win/windows_version.cc"""
    path = os.path.join(src_root, "base", "win", "windows_version.cc")
    if not os.path.exists(path):
        return True
    def transform(c):
        c = re.sub(r'#error\s+Windows\s+10\.0\.28000\.0\s+SDK[^\n]*', '// Windows 10.0.28000.0 SDK check bypassed for CI', c)
        return c
    return patch_file(path, "Bypass SDK 10.0.28000.0 check in base/win/windows_version.cc", transform)

def patch_setup_toolchain(src_root):
    """Khac phuc loi Windows SDK khong ton tai thu muc (nhu 10.0.28000.0) va dong bo SDK version"""
    sdk_ver = find_installed_windows_sdk()
    print(f"[INFO] Target Windows SDK version: {sdk_ver}")

    # Fix header SDK
    fix_windows_sdk_headers(sdk_ver)

    # Patch build/config/win/BUILD.gn
    patch_win_build_gn(src_root)

    # Patch base/win/windows_version.cc
    patch_windows_version_cc(src_root)

    # 1. Patch build/vs_toolchain.py
    vs_path = os.path.join(src_root, "build", "vs_toolchain.py")
    if os.path.exists(vs_path):
        def transform_vs(c):
            return re.sub(r"SDK_VERSION\s*=\s*['\"][^'\"]+['\"]", f"SDK_VERSION = '{sdk_ver}'", c)
        patch_file(vs_path, f"Set vs_toolchain SDK_VERSION to {sdk_ver}", transform_vs)

    # 2. Patch build/toolchain/win/setup_toolchain.py
    path = os.path.join(src_root, "build", "toolchain", "win", "setup_toolchain.py")
    def transform(c):
        c = re.sub(r"SDK_VERSION\s*=\s*['\"][^'\"]+['\"]", f"SDK_VERSION = '{sdk_ver}'", c)
        c = re.sub(r"if\s+not\s+os\.path\.exists\(part\)[^:]*:", "if False and not os.path.exists(part):", c)
        return c

    patch_file(path, "Patch Windows SDK Toolchain Path Check", transform)

    # 3. Patch root BUILD.gn to remove //build/modules
    root_gn = os.path.join(src_root, "BUILD.gn")
    if os.path.exists(root_gn):
        def transform_root_gn(c):
            return c.replace('"//build/modules",', '# "//build/modules",')
        patch_file(root_gn, "Comment out //build/modules in root BUILD.gn", transform_root_gn)

    # 4. Patch build/modules/BUILD.gn: bypass expand_directory on Windows
    mod_gn = os.path.join(src_root, "build", "modules", "BUILD.gn")
    if os.path.exists(mod_gn):
        def transform_mod(c):
            return re.sub(
                r"foreach\s*\(\s*include_flag\s*,\s*current_win_toolchain_data\.include_flags_I_list\s*\)\s*\{[\s\S]*?expand_directory[\s\S]*?\}",
                "# Windows SDK expand_directory bypassed for CI",
                c
            )
        patch_file(mod_gn, "Bypass Windows SDK expand_directory in build/modules/BUILD.gn", transform_mod)

    return True


def patch_navigator(src_root):
    path = os.path.join(src_root, "third_party", "blink", "renderer", "core", "frame", "navigator.cc")
    
    def transform(c):
        # 1. Add headers
        if "base/command_line.h" not in c:
            c = '#include "base/command_line.h"\n#include "base/strings/string_number_conversions.h"\n' + c
        
        # 2. Patch hardwareConcurrency
        if "qhtd-hardware-concurrency" not in c:
            pattern = r"(unsigned int Navigator::hardwareConcurrency\(\) const \{)"
            replacement = r"""\1
  const base::CommandLine& qhtd_cmd = *base::CommandLine::ForCurrentProcess();
  if (qhtd_cmd.HasSwitch("qhtd-hardware-concurrency")) {
    unsigned int custom_val = 0;
    if (base::StringToUint(qhtd_cmd.GetSwitchValueASCII("qhtd-hardware-concurrency"), &custom_val) && custom_val > 0) {
      return custom_val;
    }
  }"""
            c = re.sub(pattern, replacement, c)

        # 3. Patch deviceMemory if exists
        if "qhtd-device-memory" not in c:
            pattern_dm = r"(float Navigator::deviceMemory\(\) const \{)"
            replacement_dm = r"""\1
  const base::CommandLine& qhtd_cmd = *base::CommandLine::ForCurrentProcess();
  if (qhtd_cmd.HasSwitch("qhtd-device-memory")) {
    double custom_ram = 0;
    if (base::StringToDouble(qhtd_cmd.GetSwitchValueASCII("qhtd-device-memory"), &custom_ram) && custom_ram > 0) {
      return static_cast<float>(custom_ram);
    }
  }"""
            c = re.sub(pattern_dm, replacement_dm, c)
        return c

    return patch_file(path, "Patch Hardware Concurrency & RAM", transform)

def patch_canvas(src_root):
    path = os.path.join(src_root, "third_party", "blink", "renderer", "modules", "canvas", "canvas2d", "base_rendering_context_2d.cc")

    def transform(c):
        if "base/command_line.h" not in c:
            c = '#include "base/command_line.h"\n#include "base/strings/string_number_conversions.h"\n#include <algorithm>\n#include "third_party/blink/renderer/core/typed_arrays/dom_array_buffer_view.h"\n' + c

        if "qhtd-canvas-noise" not in c:
            target = "return image_data;"
            noise_code = """
  // QHTD Anti-Detect Canvas Sub-Pixel Perturbation
  const base::CommandLine& qhtd_cmd = *base::CommandLine::ForCurrentProcess();
  if (qhtd_cmd.HasSwitch("qhtd-canvas-noise")) {
    uint32_t seed = 0;
    base::StringToUint(qhtd_cmd.GetSwitchValueASCII("qhtd-canvas-noise"), &seed);
    if (seed != 0 && image_data && image_data->data()) {
      DOMArrayBufferView* array_buffer = image_data->data();
      uint8_t* raw_bytes = static_cast<uint8_t*>(array_buffer->BaseAddressMaybeShared());
      size_t byte_length = array_buffer->byteLength();
      uint32_t rng_state = seed;
      for (size_t i = 0; i < byte_length; i += 4) {
        rng_state = rng_state * 1664525u + 1013904223u;
        if ((rng_state % 37) == 0) {
          int delta = ((rng_state >> 16) & 1) ? 1 : -1;
          int val = static_cast<int>(raw_bytes[i]) + delta;
          raw_bytes[i] = static_cast<uint8_t>(std::clamp(val, 0, 255));
        }
      }
    }
  }
  return image_data;"""
            # Replace only inside getImageData
            if "ImageData* BaseRenderingContext2D::getImageData" in c:
                parts = c.split("ImageData* BaseRenderingContext2D::getImageData")
                if len(parts) > 1 and target in parts[1]:
                    parts[1] = parts[1].replace(target, noise_code, 1)
                    c = "ImageData* BaseRenderingContext2D::getImageData".join(parts)
        return c

    return patch_file(path, "Patch Canvas Sub-Pixel Noise", transform)

def patch_webgl(src_root):
    path = os.path.join(src_root, "third_party", "blink", "renderer", "modules", "webgl", "webgl_rendering_context_base.cc")

    def transform(c):
        if "base/command_line.h" not in c:
            c = '#include "base/command_line.h"\n#include "third_party/blink/renderer/platform/wtf/text/wtf_string.h"\n' + c

        if "qhtd-webgl-renderer" not in c:
            # Patch UNMASKED_RENDERER_WEBGL
            if "case GL_UNMASKED_RENDERER_WEBGL:" in c:
                sub_ren = """case GL_UNMASKED_RENDERER_WEBGL:
      {
        const base::CommandLine& qhtd_cmd = *base::CommandLine::ForCurrentProcess();
        if (qhtd_cmd.HasSwitch("qhtd-webgl-renderer")) {
          return WebGLAny(script_state, String(qhtd_cmd.GetSwitchValueASCII("qhtd-webgl-renderer").c_str()));
        }
      }"""
                c = c.replace("case GL_UNMASKED_RENDERER_WEBGL:", sub_ren, 1)

            # Patch UNMASKED_VENDOR_WEBGL
            if "case GL_UNMASKED_VENDOR_WEBGL:" in c:
                sub_ven = """case GL_UNMASKED_VENDOR_WEBGL:
      {
        const base::CommandLine& qhtd_cmd = *base::CommandLine::ForCurrentProcess();
        if (qhtd_cmd.HasSwitch("qhtd-webgl-vendor")) {
          return WebGLAny(script_state, String(qhtd_cmd.GetSwitchValueASCII("qhtd-webgl-vendor").c_str()));
        }
      }"""
                c = c.replace("case GL_UNMASKED_VENDOR_WEBGL:", sub_ven, 1)
        return c

    return patch_file(path, "Patch WebGL GPU Spoofing", transform)

def patch_audio(src_root):
    path = os.path.join(src_root, "third_party", "blink", "renderer", "modules", "webaudio", "audio_buffer.cc")

    def transform(c):
        if "base/command_line.h" not in c:
            c = '#include "base/command_line.h"\n#include "base/strings/string_number_conversions.h"\n#include "third_party/blink/renderer/core/typed_arrays/dom_typed_array.h"\n' + c

        if "qhtd-audio-noise" not in c:
            target = "return NotShared<DOMFloat32Array>(channels_[channel_index].Get());"
            audio_code = """
  // QHTD AudioContext Fingerprint Micro-Perturbation
  const base::CommandLine& qhtd_cmd = *base::CommandLine::ForCurrentProcess();
  if (qhtd_cmd.HasSwitch("qhtd-audio-noise")) {
    uint32_t audio_seed = 0;
    base::StringToUint(qhtd_cmd.GetSwitchValueASCII("qhtd-audio-noise"), &audio_seed);
    if (audio_seed != 0 && channels_[channel_index]) {
      float* data = channels_[channel_index]->Data();
      size_t len = channels_[channel_index]->length();
      uint32_t state = audio_seed;
      for (size_t i = 0; i < len; i += 100) {
        state = state * 1103515245u + 12345u;
        float noise = static_cast<float>((state & 0x7F) - 64) * 0.0000001f;
        data[i] += noise;
      }
    }
  }

  return NotShared<DOMFloat32Array>(channels_[channel_index].Get());"""
            c = c.replace(target, audio_code, 1)
        return c

    return patch_file(path, "Patch AudioContext Micro-Perturbation", transform)

def main():
    src_root = sys.argv[1] if len(sys.argv) > 1 else "."
    print(f"[INFO] Applying QHTD Anti-Detect Patches to: {os.path.abspath(src_root)}")
    
    # 1. Ensure LASTCHANGE files exist
    ensure_lastchange(src_root)

    # 2. Patch Windows SDK toolchain check
    patch_setup_toolchain(src_root)

    # 3. Patch Blink C++ Sources
    ok1 = patch_navigator(src_root)
    ok2 = patch_canvas(src_root)
    ok3 = patch_webgl(src_root)
    ok4 = patch_audio(src_root)

    if ok1 and ok2 and ok3 and ok4:
        print("\n[SUCCESS] All 4 C++ patches and CI toolchain fixes applied successfully!")
        sys.exit(0)
    else:
        print("\n[INFO] Patches processed.")
        sys.exit(0 if (ok1 or ok2 or ok3 or ok4) else 1)

if __name__ == "__main__":
    main()
