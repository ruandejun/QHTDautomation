#!/usr/bin/env python3
import asyncio
import sys
sys.path.insert(0, '/root/Workspace/Python/QHTDautomation/MunAutomationDesktop')

from mun_anti_browser import NodriverBrowserManager

async def main():
    manager = NodriverBrowserManager()
    browser, tab = await manager.start_named_profile(
        name="bearvault",
        start_url="https://www.bearvault.cc/my-cards",
        headless=False
    )
    print("Bearvault profile loaded via start_named_profile('bearvault')")

if __name__ == '__main__':
    asyncio.run(main())
