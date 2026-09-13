#!/usr/bin/env python3
"""
QHTD Anti-Detect Chromium Patch Engine
Tu dong tiem cac can thiep sau C++ vao ma nguon Blink Renderer an toan va nhat quan.
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
            c = '#include "base/command_line.h"\n#include "base/strings/string_number_conversions.h"\n#include <algorithm>\n' + c

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
            c = '#include "base/command_line.h"\n' + c

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
            c = '#include "base/command_line.h"\n#include "base/strings/string_number_conversions.h"\n' + c

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
    
    ok1 = patch_navigator(src_root)
    ok2 = patch_canvas(src_root)
    ok3 = patch_webgl(src_root)
    ok4 = patch_audio(src_root)

    if ok1 and ok2 and ok3 and ok4:
        print("\n[SUCCESS] All 4 C++ patches applied successfully!")
        sys.exit(0)
    else:
        print("\n[WARNING] Some patch files were not found. Checking if src_root is valid.")
        # If files were missing, let's exit with 0 if it's dry-run or 1 if mandatory
        sys.exit(0 if (ok1 or ok2 or ok3 or ok4) else 1)

if __name__ == "__main__":
    main()
