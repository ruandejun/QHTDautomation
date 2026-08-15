"""
Script tạo và khởi tạo sẵn 5 Persistent Profiles Anti-detect Browser cho 5 hệ thống:
1. maidzo.vn
2. chuyenhang365.com
3. alo68.vn
4. airewards.cc
5. cu.c69.us
"""

import asyncio
import os
import sys
import json
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

os.environ["DISPLAY"] = ":99"
sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser.browser_manager import NodriverBrowserManager
from mun_anti_browser.profile_manager import ProfileManager

PROFILES_DEF = [
    {
        "id": "profile_maidzo_vn",
        "name": "Maidzo Production Admin Profile",
        "site": "maidzo.vn",
        "start_url": "https://maidzo.vn/#/dang-nhap/",
        "os_type": "Window"
    },
    {
        "id": "profile_chuyenhang365_com",
        "name": "ChuyenHang365 Production Admin Profile",
        "site": "chuyenhang365.com",
        "start_url": "https://chuyenhang365.com/#/dang-nhap/",
        "os_type": "Window"
    },
    {
        "id": "profile_alo68_vn",
        "name": "Alo68 Production Admin Profile",
        "site": "alo68.vn",
        "start_url": "https://alo68.vn/#/dang-nhap/",
        "os_type": "Window"
    },
    {
        "id": "profile_airewards_cc",
        "name": "AiRewards Production Profile",
        "site": "airewards.cc",
        "start_url": "https://airewards.cc",
        "os_type": "Window"
    },
    {
        "id": "profile_cu_c69_us",
        "name": "C69 Admin Tool Profile",
        "site": "cu.c69.us",
        "start_url": "https://cu.c69.us",
        "os_type": "Window"
    }
]

PROFILES_JSON_PATH = "/root/Workspace/Python/QHTDautomation/MunAutomationDesktop/system_debug_profiles.json"

async def init_single_profile(prof_info):
    prof_id = prof_info["id"]
    site_url = prof_info["start_url"]
    logger.info(f"[*] Đang khởi tạo Profile: {prof_id} ({prof_info['name']}) -> {site_url}")
    
    pm = ProfileManager()
    base_prof = pm.create_random_profile(os_type=prof_info["os_type"])
    base_prof["id"] = prof_id
    base_prof["name"] = prof_info["name"]
    base_prof["site"] = prof_info["site"]
    base_prof["start_url"] = site_url

    manager = NodriverBrowserManager()
    try:
        browser, tab = await asyncio.wait_for(
            manager.start(
                profile_config=base_prof,
                start_url=site_url,
                headless=False
            ),
            timeout=30.0
        )
        await asyncio.sleep(4)
        logger.info(f"[+] Profile {prof_id} đã tải xong trang {site_url}, Cookies & LocalStorage đã được mount!")
    except Exception as e:
        logger.warning(f"[-] Lỗi khi init {prof_id}: {e}")
    finally:
        try:
            await manager.close()
        except Exception:
            pass

    return base_prof

async def main():
    saved_configs = []
    for p in PROFILES_DEF:
        cfg = await init_single_profile(p)
        saved_configs.append(cfg)

    with open(PROFILES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(saved_configs, f, indent=2, ensure_ascii=False)
    
    logger.info(f"[SUCCESS] Đã lưu thông tin 5 profiles vào: {PROFILES_JSON_PATH}")

if __name__ == "__main__":
    asyncio.run(main())
