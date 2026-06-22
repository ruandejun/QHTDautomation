"""
MunAntiBrowser - C69 Profile API Client
=============================================
Handles synchronization of browser fingerprint profiles
with the C69 server (https://c69.us/dashboard/api/profiles/).

Usage:
    api = C69ProfileAPI(api_url="https://c69.us", api_token="xxx")
    profiles = api.list_profiles()
    api.create_profile(local_config)
    server_config = api.get_profile(profile_id)
"""

import json
import logging
from typing import Any, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)


# ─── Field Mapping: Local config ↔ Server BrowserProfiles model ─────────────

# Maps local profile_config keys → server API field names
LOCAL_TO_SERVER_MAP = {
    "name":              "profile_name",
    "profile_os":        "profile_os",
    "profile_user_agent": "profile_user_agent",
    "profile_resolution": "profile_resolution",
    "profile_cpu":       "profile_cpu",
    "profile_canvas":    "profile_canvas",
    "profile_audio":     "profile_audio",
    "profile_webgl":     "profile_webgl",
    "profile_font":      "profile_font",
    "profile_rects":     "profile_rects",
    "profile_start_url": "profile_start_url",
    "profile_vendor":    "profile_vendor",
    "profile_renderer":  "profile_renderer",
    "proxy_string":      "profile_socks5_details",
    "proxy_type":        "profile_proxy_type",
    "proxy_username":    "profile_proxy_username",
    "proxy_password":    "profile_proxy_password",
}

# Reverse mapping
SERVER_TO_LOCAL_MAP = {v: k for k, v in LOCAL_TO_SERVER_MAP.items()}

# Fields that store JSON data (need serialization/deserialization)
JSON_FIELDS = {"profile_canvas", "profile_audio", "profile_webgl", "profile_font"}

# Proxy type mapping (server uses integer, local uses string)
PROXY_TYPE_TO_INT = {
    "socks5": 0,
    "http": 1,
    "": 0,
    "Không dùng proxy": 0,
}
PROXY_TYPE_FROM_INT = {0: "socks5", 1: "http"}


def local_to_server(profile_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a local profile_config dict to server API format.

    Args:
        profile_config: Local profile configuration dictionary.

    Returns:
        Dictionary ready to POST/PUT to server API.
    """
    server_data = {}

    for local_key, server_key in LOCAL_TO_SERVER_MAP.items():
        value = profile_config.get(local_key)
        if value is None:
            continue

        # Serialize JSON fields
        if server_key in JSON_FIELDS:
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)

        # Convert proxy type string → integer
        if server_key == "profile_proxy_type":
            value = PROXY_TYPE_TO_INT.get(str(value).lower(), 0)

        server_data[server_key] = value

    return server_data


def server_to_local(server_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a server API response dict to local profile_config format.

    Args:
        server_data: Dictionary from server API response.

    Returns:
        Local profile configuration dictionary.
    """
    local_config = {}

    for server_key, local_key in SERVER_TO_LOCAL_MAP.items():
        value = server_data.get(server_key)
        if value is None:
            continue

        # Deserialize JSON fields (keep as string for script_loader compatibility)
        # script_loader.compose_injection() handles JSON parsing itself
        if server_key in JSON_FIELDS and isinstance(value, str) and value.strip():
            # Keep as-is (string) - ScriptLoader handles json.loads()
            pass

        # Convert proxy type integer → string
        if server_key == "profile_proxy_type":
            try:
                value = PROXY_TYPE_FROM_INT.get(int(value), "socks5")
            except (ValueError, TypeError):
                value = "socks5"

        local_config[local_key] = value

    # Preserve server ID for tracking
    if "id" in server_data:
        local_config["server_id"] = server_data["id"]

    # Copy additional server-only fields that are useful
    for extra_key in ("profile_original_name", "profile_note", "profile_status",
                      "profile_browser", "profile_version", "created", "modified"):
        if extra_key in server_data and server_data[extra_key]:
            local_config[extra_key] = server_data[extra_key]

    return local_config


class C69ProfileAPI:
    """
    Client for C69 browser profile API.

    Authenticates with Token-based auth (from storagon login).
    Base URL: {api_url}/dashboard/api/profiles/
    """

    def __init__(self, api_url: str, api_token: str):
        """
        Args:
            api_url: Base server URL (e.g., 'https://c69.us').
            api_token: Auth token from storagon login.
        """
        self.api_url = api_url.rstrip("/")
        self.api_token = api_token
        self.base_url = f"{self.api_url}/dashboard/api/profiles/"
        self.timeout = 15

    @property
    def _headers(self) -> dict:
        return {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
        }

    def is_configured(self) -> bool:
        """Check if API is properly configured with URL and token."""
        return bool(self.api_url and self.api_token)

    # ─── CRUD Operations ─────────────────────────────────────────────────

    def list_profiles(
        self, page: int = 1, page_size: int = 100, search: str = ""
    ) -> List[Dict[str, Any]]:
        """
        Fetch all browser profiles from server.

        Returns:
            List of local profile_config dicts converted from server data.
        """
        all_profiles = []
        url = f"{self.base_url}?page={page}&page_size={page_size}"
        if search:
            url += f"&search={search}"

        try:
            resp = requests.get(url, headers=self._headers, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()

            results = data.get("results", data) if isinstance(data, dict) else data
            for item in results:
                local = server_to_local(item)
                all_profiles.append(local)

            # Handle pagination
            total_count = data.get("count", len(results)) if isinstance(data, dict) else len(results)
            total_pages = (total_count + page_size - 1) // page_size

            for p in range(2, total_pages + 1):
                next_url = f"{self.base_url}?page={p}&page_size={page_size}"
                if search:
                    next_url += f"&search={search}"
                try:
                    r = requests.get(next_url, headers=self._headers, timeout=self.timeout)
                    r.raise_for_status()
                    d = r.json()
                    for item in d.get("results", d):
                        all_profiles.append(server_to_local(item))
                except Exception as e:
                    logger.warning(f"Failed to fetch page {p}: {e}")
                    break

            logger.info(f"Fetched {len(all_profiles)} profiles from server")
            return all_profiles

        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list profiles: {e}")
            raise ConnectionError(f"Không thể kết nối server: {e}") from e

    def get_profile(self, profile_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetch a single profile by server ID.

        Returns:
            Local profile_config dict, or None if not found.
        """
        try:
            url = f"{self.base_url}{profile_id}/"
            resp = requests.get(url, headers=self._headers, timeout=self.timeout)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return server_to_local(resp.json())
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get profile {profile_id}: {e}")
            return None

    def create_profile(self, profile_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new profile on server.

        Args:
            profile_config: Local profile configuration.

        Returns:
            Created profile dict with server_id, or None on failure.
        """
        server_data = local_to_server(profile_config)

        try:
            resp = requests.post(
                self.base_url,
                headers=self._headers,
                json=server_data,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            created = resp.json()
            logger.info(f"Created profile on server: ID={created.get('id')}")
            return server_to_local(created)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create profile: {e}")
            return None

    def update_profile(
        self, profile_id: int, profile_config: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update an existing profile on server.

        Args:
            profile_id: Server profile ID.
            profile_config: Local profile configuration to update.

        Returns:
            Updated profile dict, or None on failure.
        """
        server_data = local_to_server(profile_config)

        try:
            url = f"{self.base_url}{profile_id}/"
            resp = requests.patch(
                url,
                headers=self._headers,
                json=server_data,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            updated = resp.json()
            logger.info(f"Updated profile on server: ID={profile_id}")
            return server_to_local(updated)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update profile {profile_id}: {e}")
            return None

    def delete_profile(self, profile_id: int) -> bool:
        """
        Delete a profile from server.

        Returns:
            True if successful, False otherwise.
        """
        try:
            url = f"{self.base_url}{profile_id}/"
            resp = requests.delete(url, headers=self._headers, timeout=self.timeout)
            if resp.status_code in (200, 204):
                logger.info(f"Deleted profile from server: ID={profile_id}")
                return True
            resp.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete profile {profile_id}: {e}")
            return False

    def test_connection(self) -> bool:
        """Test if the API connection and auth work."""
        try:
            url = f"{self.base_url}?page=1&page_size=1"
            resp = requests.get(url, headers=self._headers, timeout=5)
            return resp.status_code == 200
        except Exception:
            return False
