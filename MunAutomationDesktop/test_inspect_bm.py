import asyncio
import os
import sys
import json

os.chdir(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")
sys.path.append(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop")

from mun_anti_browser.browser_manager import NodriverBrowserManager

async def main():
    bm = NodriverBrowserManager()
    with open("browser_profiles.json", "r", encoding="utf-8") as f:
        profs = json.load(f)
    cfg = profs[0]

    args = bm._build_chrome_args(cfg, False, True, "", "direct", "", "")
    print("CHROME ARGS:")
    for a in args:
        print("  ", a)

    print("\nPROFILE DIR:")
    profile_id = cfg.get("id", 0)
    profile_dir = os.path.join(bm.user_data_dir, str(profile_id))
    print("  ", profile_dir)

    print("\nINJECTION SCRIPT LENGTH:")
    inj = bm.script_loader.compose_injection(cfg)
    print("  ", len(inj))

if __name__ == "__main__":
    asyncio.run(main())
