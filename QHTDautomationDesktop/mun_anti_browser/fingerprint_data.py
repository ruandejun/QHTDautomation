"""
MunAntiBrowser - Fingerprint Data Generators
=============================================
Generates randomized fingerprint data for browser profiles.
Ported from MunLogin/mybrowser.py create_random_profile() and get_inject_data().
"""

import json
import math
import random
from typing import Dict, List, Any, Optional


# ─── Constants ───────────────────────────────────────────────────────────────

CPU_COUNTS = ["2", "4", "6", "8", "10"]

SCREEN_RESOLUTIONS = [
    "1920x1200", "1920x1080", "1536x864",
    "1440x900", "1366x768", "1280x720",
]

CHROME_VERSIONS = [
    "136.0.7103.113", "136.0.7103.92", "135.0.7049.114",
    "135.0.7049.84", "134.0.6998.165", "134.0.6998.88",
    "133.0.6943.141", "133.0.6943.98", "132.0.6834.160",
    "131.0.6778.140", "130.0.6723.117", "129.0.6668.100",
    "128.0.6613.120", "127.0.6533.99",
]

IPHONE_DEVICES = {
    "iPhone 14 Pro Max":  {"resolution": "430x932",  "scale": "3"},
    "iPhone 14 Pro":      {"resolution": "393x852",  "scale": "3"},
    "iPhone 14 Plus":     {"resolution": "428x926",  "scale": "3"},
    "iPhone 14":          {"resolution": "390x844",  "scale": "3"},
    "iPhone SE 3rd gen":  {"resolution": "375x667",  "scale": "2"},
    "iPhone 13":          {"resolution": "390x844",  "scale": "3"},
    "iPhone 13 mini":     {"resolution": "375x812",  "scale": "3"},
    "iPhone 13 Pro Max":  {"resolution": "428x926",  "scale": "3"},
    "iPhone 13 Pro":      {"resolution": "390x844",  "scale": "3"},
    "iPhone 12":          {"resolution": "390x844",  "scale": "3"},
    "iPhone 12 mini":     {"resolution": "375x812",  "scale": "3"},
    "iPhone 12 Pro Max":  {"resolution": "428x926",  "scale": "3"},
    "iPhone 12 Pro":      {"resolution": "390x844",  "scale": "3"},
    "iPhone SE 2nd gen":  {"resolution": "375x667",  "scale": "2"},
    "iPhone 11 Pro Max":  {"resolution": "414x896",  "scale": "3"},
    "iPhone 11 Pro":      {"resolution": "375x812",  "scale": "3"},
    "iPhone 11":          {"resolution": "414x896",  "scale": "2"},
    "iPhone XR":          {"resolution": "414x896",  "scale": "2"},
    "iPhone XS Max":      {"resolution": "414x896",  "scale": "3"},
    "iPhone XS":          {"resolution": "375x812",  "scale": "3"},
    "iPhone X":           {"resolution": "375x812",  "scale": "3"},
}

ANDROID_DEVICES = {
    "Samsung Galaxy Z Flip 4": {"resolution": "412x1004", "scale": "3", "model": "SM-F721B"},
    "Samsung Galaxy S9+":      {"resolution": "360x740",  "scale": "3", "model": "SM-G965F"},
    "Samsung Galaxy S9":       {"resolution": "360x740",  "scale": "3", "model": "SM-G960U"},
    "Samsung Galaxy S8+":      {"resolution": "360x740",  "scale": "3", "model": "SM-G955F"},
    "Samsung Galaxy S8":       {"resolution": "360x740",  "scale": "3", "model": "SM-G950F"},
    "Nexus 6P":                {"resolution": "412x732",  "scale": "3", "model": "Nexus 6P"},
    "Nexus 5X":                {"resolution": "412x732",  "scale": "3", "model": "Nexus 5X"},
    "Google Pixel 4 XL":       {"resolution": "412x869",  "scale": "3", "model": "Pixel 4 XL"},
    "Google Pixel 4":          {"resolution": "412x869",  "scale": "3", "model": "Pixel 4"},
}

ANDROID_OS_VERSIONS = ["9", "10", "11", "12", "13"]
APPLE_IOS_VERSIONS = ["16_1", "15_7", "14_8", "13_7"]
DESKTOP_OS_LIST = ["Window", "Mac OS X", "Linux", "Chrome OS"]

GPU_VENDORS = [
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) UHD Graphics 630 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 580 Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 6600 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
    "ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11)",
]

# Curated subset of common Windows/Mac fonts
FONT_LIST = [
    "Arial", "Calibri", "Cambria", "Cambria Math", "Candara",
    "Comic Sans MS", "Consolas", "Constantia", "Corbel", "Courier New",
    "Ebrima", "Franklin Gothic", "Gabriola", "Georgia", "Impact",
    "Lucida Console", "Lucida Sans Unicode", "Malgun Gothic",
    "Microsoft Sans Serif", "Microsoft YaHei", "MS Gothic",
    "Palatino Linotype", "Segoe Print", "Segoe Script", "Segoe UI",
    "SimSun", "Tahoma", "Times New Roman", "Trebuchet MS", "Verdana",
    "Webdings", "Wingdings", "Yu Gothic", "Yu Gothic UI",
    "Arial Black", "Calibri Light", "Courier", "Helvetica",
    "Monaco", "Menlo", "Futura", "Garamond", "Baskerville",
    "Book Antiqua", "Century Gothic", "Didot", "Optima",
    "sans-serif", "serif", "monospace", "cursive", "fantasy",
    "inherit", "auto", "default",
]


# ─── Generator Functions ────────────────────────────────────────────────────

def generate_audio_fingerprint() -> Dict[str, Any]:
    """Generate randomized audio fingerprint data."""
    list_length = 44100
    audio_content = {}
    i = 0
    while i < list_length:
        index = int(random.uniform(0.01, 0.99) * i)
        audio_content[index] = round(random.uniform(0.01, 0.99) * 0.0000001, 15)
        i += 100

    return {
        "audio_content": audio_content,
        "audio_random1": round(random.uniform(0.01, 0.99), 15),
        "audio_random2": round(random.uniform(0.01, 0.99), 15),
    }


def generate_canvas_fingerprint() -> Dict[str, int]:
    """Generate randomized canvas RGBA shift values."""
    shifts = [-3, -2, -1, 0, 1, 2, 3]
    return {
        "r": random.choice(shifts),
        "g": random.choice(shifts),
        "b": random.choice(shifts),
        "a": random.choice(shifts),
    }


def generate_webgl_fingerprint(phone_os: Optional[str] = None) -> Dict[str, Any]:
    """Generate randomized WebGL parameters and GPU vendor."""
    list_floats = [math.pow(2, x) for x in [0, 10, 11, 12, 13]]
    list_int = [math.pow(2, x) for x in [13, 14, 15]]
    list_1234 = [math.pow(2, x) for x in [1, 2, 3, 4]]
    list_1415 = [math.pow(2, x) for x in [14, 15]]
    list_1213 = [math.pow(2, x) for x in [12, 13]]
    list_45678 = [math.pow(2, x) for x in [4, 5, 6, 7, 8]]
    list_10111213 = [math.pow(2, x) for x in [10, 11, 12, 13]]

    int_3386 = int(random.choice(list_int))

    webgl = {
        "36347": int(random.choice(list_1213)),
        "3379":  int(random.choice(list_1415)),
        "34076": int(random.choice(list_1415)),
        "34024": int(random.choice(list_1415)),
        "35661": int(random.choice(list_45678)),
        "36349": int(random.choice(list_10111213)),
        "3413":  int(random.choice(list_1234)),
        "3412":  int(random.choice(list_1234)),
        "3411":  int(random.choice(list_1234)),
        "3410":  int(random.choice(list_1234)),
        "35660": int(random.choice(list_1234)),
        "34047": int(random.choice(list_1234)),
        "34930": int(random.choice(list_1234)),
        "34921": int(random.choice(list_1234)),
        "3386":  [int_3386, int_3386],
        "33901": [round(random.uniform(0.01, 1), 15), random.choice(list_floats)],
        "33902": [round(random.uniform(0.01, 1), 15), random.choice(list_floats)],
        "34324": round(random.uniform(0.01, 0.99), 15),
        "35376": round(random.uniform(0.01, 0.99), 15),
        "35377": round(random.uniform(0.01, 0.99), 15),
        "35379": round(random.uniform(0.01, 0.99), 15),
        "35658": round(random.uniform(0.01, 0.99), 15),
        "gl_index": round(random.uniform(0.01, 0.99), 15),
        "gl_noise": round(random.uniform(0.01, 0.99), 15),
    }

    if phone_os == "iPhone":
        webgl["37446"] = "Apple GPU"
        webgl["37445"] = "Apple GPU"
    else:
        renderer = random.choice(GPU_VENDORS)
        webgl["37446"] = renderer
        # Vendor must match GPU brand in renderer string
        if "NVIDIA" in renderer:
            webgl["37445"] = "Google Inc. (NVIDIA)"
        elif "Intel" in renderer:
            webgl["37445"] = "Google Inc. (Intel)"
        elif "AMD" in renderer:
            webgl["37445"] = "Google Inc. (AMD)"
        else:
            webgl["37445"] = "Google Inc."

    webgl["7938"] = "WebGL 2.0 (OpenGL ES 3.0 Chromium)"
    webgl["35724"] = "WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)"

    return webgl


def generate_rects_offset() -> float:
    """Generate randomized ClientRect offset value."""
    return round(random.uniform(0.2, 0.35), 5)


def generate_font_list() -> List[str]:
    """Generate randomized font subset."""
    max_idx = random.randint(200, len(FONT_LIST) - 1) if len(FONT_LIST) > 200 else len(FONT_LIST) - 1
    min_idx = random.randint(0, min(150, max_idx))
    return FONT_LIST[min_idx:max_idx]


def generate_user_agent(
    os_type: str = "Window",
    phone_os: Optional[str] = None,
) -> tuple:
    """
    Generate user agent string and related info.

    Returns:
        (user_agent, os_name, resolution, cpu)
    """
    chrome_version = random.choice(CHROME_VERSIONS)
    cpu = random.choice(CPU_COUNTS)

    if phone_os == "iPhone":
        device_list = list(IPHONE_DEVICES.keys())
        device_name = random.choice(device_list)
        ua = (
            f"Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) "
            f"AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/{chrome_version} "
            f"Mobile/15E148 Safari/604.1"
        )
        resolution = IPHONE_DEVICES[device_name]["resolution"]
        return ua, device_name, resolution, cpu

    elif phone_os == "Android":
        device_list = list(ANDROID_DEVICES.keys())
        device_name = random.choice(device_list)
        os_version = random.choice(ANDROID_OS_VERSIONS)
        model = ANDROID_DEVICES[device_name]["model"]
        ua = (
            f"Mozilla/5.0 (Linux; Android {os_version}; {model}) "
            f"AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_version} "
            f"Mobile Safari/537.36 TwitterAndroid"
        )
        resolution = ANDROID_DEVICES[device_name]["resolution"]
        return ua, device_name, resolution, cpu

    else:
        # Desktop
        if os_type == "Window":
            agent_os = "Windows NT 10.0; Win64; x64"
        elif os_type == "Mac OS X":
            ios_ver = random.choice(APPLE_IOS_VERSIONS)
            agent_os = f"Macintosh; Intel Mac OS X {ios_ver}"
        elif os_type == "Linux":
            agent_os = "X11; Linux x86_64"
        else:
            agent_os = "X11; CrOS x86_64 14909.100.0"

        ua = (
            f"Mozilla/5.0 ({agent_os}) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{chrome_version} Safari/537.36"
        )
        resolution = random.choice(SCREEN_RESOLUTIONS)
        return ua, os_type, resolution, cpu
