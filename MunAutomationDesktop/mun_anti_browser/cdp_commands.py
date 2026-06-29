"""
MunAntiBrowser - CDP Commands
================================
Chrome DevTools Protocol commands for fingerprint spoofing.
Ported from mybrowser.py set_execute_cdp_cmd() (lines 941-1098).

Uses nodriver's native CDP interface (snake_case functions).
Functions are called via: await tab.send(cdp_module.function_name(...))
"""

import logging
from typing import Optional, Dict, Any

import nodriver.cdp.emulation as emulation
import nodriver.cdp.network as network_cdp
import nodriver.cdp.page as page_cdp

logger = logging.getLogger(__name__)


# ─── Platform Mapping ────────────────────────────────────────────────────────

PLATFORM_MAP = {
    "Window":    "Win32",
    "Mac OS X":  "MacIntel",
    "Linux":     "Linux x86_64",
    "Chrome OS": "CrOS X86_64",
}


def get_platform(os_name: str) -> tuple:
    """
    Map OS name to navigator.platform value and mobile flag.

    Returns:
        (platform_string, is_mobile)
    """
    os_lower = os_name.lower()
    if "iphone" in os_lower:
        return "iPhone", True
    elif "android" in os_lower:
        return "Android", True
    elif os_lower in ("samsung",):
        return "Android", True
    return PLATFORM_MAP.get(os_name, "Win32"), False


# ─── CDP Command Functions ───────────────────────────────────────────────────

async def set_timezone(tab, timezone_id: str):
    """Override browser timezone."""
    # Map from Etc/GMT POSIX style to common IANA zone name to bypass IPhey / check mismatch
    # In POSIX timezone naming, GMT-X actually means GMT+X, and GMT+X means GMT-X.
    tz_map = {
        "Etc/GMT-12": "Pacific/Auckland",
        "Etc/GMT-11": "Pacific/Pago_Pago",
        "Etc/GMT-10": "Pacific/Honolulu",
        "Etc/GMT-9": "America/Anchorage",
        "Etc/GMT-8": "Asia/Singapore",    # GMT+8
        "Etc/GMT-7": "Asia/Bangkok",      # GMT+7
        "Etc/GMT-6": "Asia/Dhaka",        # GMT+6
        "Etc/GMT-5": "Asia/Karachi",      # GMT+5
        "Etc/GMT-4": "Asia/Dubai",        # GMT+4
        "Etc/GMT-3": "Europe/Moscow",     # GMT+3
        "Etc/GMT-2": "Europe/Kiev",       # GMT+2
        "Etc/GMT-1": "Europe/Paris",      # GMT+1
        "Etc/GMT+0": "UTC",
        "Etc/GMT": "UTC",
        "Etc/GMT+1": "Atlantic/Cape_Verde", # GMT-1
        "Etc/GMT+2": "America/Noronha",     # GMT-2
        "Etc/GMT+3": "America/Argentina/Buenos_Aires", # GMT-3
        "Etc/GMT+4": "America/Halifax",     # GMT-4
        "Etc/GMT+5": "America/New_York",    # GMT-5
        "Etc/GMT+6": "America/Chicago",     # GMT-6
        "Etc/GMT+7": "America/Denver",      # GMT-7
        "Etc/GMT+8": "America/Los_Angeles", # GMT-8
        "Etc/GMT+9": "America/Anchorage",   # GMT-9
        "Etc/GMT+10": "Pacific/Honolulu",   # GMT-10
        "Etc/GMT+11": "Pacific/Pago_Pago",   # GMT-11
    }
    
    target_tz = tz_map.get(timezone_id, timezone_id)
    try:
        await tab.send(emulation.set_timezone_override(timezone_id=target_tz))
        logger.debug(f"Timezone set to: {target_tz} (original: {timezone_id})")
    except Exception as e:
        logger.warning(f"Failed to set timezone: {e}")


async def set_geolocation(tab, latitude: float, longitude: float, accuracy: float = 1.0):
    """Override browser geolocation."""
    try:
        await tab.send(emulation.set_geolocation_override(
            latitude=latitude,
            longitude=longitude,
            accuracy=accuracy,
        ))
        logger.debug(f"Geolocation set to: {latitude}, {longitude}")
    except Exception as e:
        logger.warning(f"Failed to set geolocation: {e}")


async def set_user_agent(
    tab,
    user_agent: str,
    platform: str,
    browser_version: str = "",
    is_mobile: bool = False,
):
    """
    Override user agent via both Network and Emulation CDP domains.
    """
    try:
        version_first = browser_version.split(".")[0] if browser_version else "109"

        # Build user agent metadata
        metadata = emulation.UserAgentMetadata(
            platform=platform,
            platform_version=platform,
            architecture="" if is_mobile else "x86",
            model="",
            mobile=is_mobile,
            full_version=browser_version or version_first,
            full_version_list=[
                emulation.UserAgentBrandVersion(brand="Chrome", version=version_first),
            ],
            brands=[
                emulation.UserAgentBrandVersion(brand="Chrome", version=version_first),
                emulation.UserAgentBrandVersion(brand="Chromium", version=version_first),
                emulation.UserAgentBrandVersion(brand="Not A;Brand", version="24"),
            ],
        )

        # Network domain
        await tab.send(network_cdp.set_user_agent_override(
            user_agent=user_agent,
            accept_language="en-US,en",
            platform=platform,
            user_agent_metadata=metadata,
        ))

        # Emulation domain
        await tab.send(emulation.set_user_agent_override(
            user_agent=user_agent,
            accept_language="en-US,en",
            platform=platform,
            user_agent_metadata=metadata,
        ))

        logger.debug(f"User agent set: {user_agent[:60]}...")
    except Exception as e:
        logger.warning(f"Failed to set user agent: {e}")


async def set_device_metrics(
    tab,
    width: int,
    height: int,
    is_mobile: bool = False,
    device_scale_factor: int = 0,
):
    """Override device screen metrics."""
    try:
        scale = 50 if is_mobile else device_scale_factor

        await tab.send(emulation.set_device_metrics_override(
            width=width,
            height=height,
            device_scale_factor=float(scale),
            mobile=is_mobile,
            screen_width=width,
            screen_height=height,
            screen_orientation=emulation.ScreenOrientation(
                type_="portraitPrimary" if is_mobile else "landscapePrimary",
                angle=0,
            ),
        ))

        if is_mobile:
            await tab.send(emulation.set_emit_touch_events_for_mouse(
                enabled=True,
                configuration="mobile",
            ))
            await tab.send(emulation.set_touch_emulation_enabled(
                enabled=True,
                max_touch_points=5,
            ))

        logger.debug(f"Device metrics set: {width}x{height}, mobile={is_mobile}")
    except Exception as e:
        logger.warning(f"Failed to set device metrics: {e}")


async def set_hardware_concurrency(tab, cpu_count: int):
    """Override hardware concurrency (CPU core count)."""
    try:
        await tab.send(emulation.set_hardware_concurrency_override(
            hardware_concurrency=cpu_count,
        ))
        logger.debug(f"CPU cores set to: {cpu_count}")
    except Exception as e:
        logger.warning(f"Failed to set hardware concurrency: {e}")


async def disable_cache(tab):
    """Disable browser cache."""
    try:
        await tab.send(network_cdp.set_cache_disabled(cache_disabled=True))
    except Exception as e:
        logger.warning(f"Failed to disable cache: {e}")


async def inject_script_on_new_document(tab, source: str):
    """
    Register a script to be evaluated on every new document in ALL frames.
    Uses Page.addScriptToEvaluateOnNewDocument which works WITHOUT Page.enable().
    
    NOTE: Do NOT call Page.enable() — it activates CDP Page domain event monitoring
    which is detectable by anti-detect services like iphey (triggers 'squirrel' signal).
    """
    try:
        # Register script for ALL frames (existing + new)
        await tab.send(page_cdp.add_script_to_evaluate_on_new_document(
            source=source,
        ))
        logger.debug(f"Registered injection script ({len(source)} chars)")
    except Exception as e:
        logger.warning(f"Failed to register injection script: {e}")


async def inject_into_all_frames(tab, source: str):
    """
    Previously injected script into existing frames via Runtime.evaluate.
    
    DISABLED: Runtime.enable() and Runtime.evaluate() activate CDP domains
    that are detectable by anti-detect services. The script injection via
    addScriptToEvaluateOnNewDocument is sufficient as it runs on all new
    document loads including the initial page load.
    """
    # No-op: rely on addScriptToEvaluateOnNewDocument instead
    logger.debug("inject_into_all_frames: skipped (using addScriptToEvaluateOnNewDocument only)")
    pass


async def apply_all_cdp_overrides(
    tab,
    profile_config: Dict[str, Any],
    injection_script: str,
):
    """
    Apply all CDP overrides to a tab in one call.
    This replaces the old set_execute_cdp_cmd() polling loop.

    Args:
        tab: nodriver Tab object
        profile_config: Profile configuration dictionary
        injection_script: Composed JS injection string
    """
    import httpagentparser

    # Enable Page domain so Chrome registers add_script_to_evaluate_on_new_document.
    # IMPORTANT: Page domain MUST be disabled immediately after navigate in browser_manager
    # to bypass bot detection (which looks for CDP Page event listeners, e.g. "squirrel").
    await tab.send(page_cdp.enable())

    # NOTE: Do NOT call page_cdp.set_bypass_csp() — it requires Page domain
    # and is also a detectable CDP signal.

    # Disable cache
    await disable_cache(tab)

    # Platform detection
    os_name = profile_config.get("profile_os", "Window")
    platform, is_mobile = get_platform(os_name)

    # User Agent override
    user_agent_str = profile_config.get("profile_user_agent", "")
    if user_agent_str:
        ua_parsed = httpagentparser.detect(user_agent_str)
        browser_version = ua_parsed.get("browser", {}).get("version", "109")
        await set_user_agent(tab, user_agent_str, platform, browser_version, is_mobile)

    # Timezone override
    timezone_info = profile_config.get("_timezone_data")
    if timezone_info:
        if "timezone_id" in timezone_info:
            await set_timezone(tab, timezone_info["timezone_id"])
        if "latitude" in timezone_info and "longitude" in timezone_info:
            await set_geolocation(
                tab,
                timezone_info["latitude"],
                timezone_info["longitude"],
                timezone_info.get("accuracy", 1.0),
            )

    # Screen resolution - Only apply physical device metrics override for mobile
    if is_mobile:
        resolution = profile_config.get("profile_resolution", "")
        if resolution:
            parts = resolution.strip().replace(" ", "").split("x")
            if len(parts) == 2:
                width = int(parts[0])
                height = int(parts[1])
                await set_device_metrics(tab, width, height, is_mobile)

    # CPU cores
    cpu = profile_config.get("profile_cpu")
    if cpu:
        await set_hardware_concurrency(tab, int(cpu))

    # Inject fingerprint scripts into ALL frames (existing + future)
    await inject_script_on_new_document(tab, injection_script)

    # Also inject into all currently existing frames (including cross-origin iframes)
    await inject_into_all_frames(tab, injection_script)

    logger.info("All CDP overrides applied successfully (including cross-origin frames)")

