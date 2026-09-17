import sys
import os

# Ensure MunAutomationDesktop is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mun_anti_browser.proxy_manager import ProxyManager, ProxyConfig


def test_proxy_test_connection_live_socks5():
    """Happy path: Live verified SOCKS5 proxy should return alive=True with positive latency."""
    proxy_str = "socks5://iifcuwil:o6jm2azbq5gs@50.114.98.173:5657"
    res = ProxyManager.test_connection(proxy_str, timeout=10.0, target_host="www.google.com", target_port=80)
    assert isinstance(res, dict)
    assert res["alive"] is True
    assert res["latency_ms"] > 0.0
    assert res["error"] is None
    assert res["proxy_address"] == "50.114.98.173:5657"
    assert res["proxy_type"] == "socks5"


def test_proxy_test_connection_with_proxyconfig_object():
    """Happy path: Calling test_connection with ProxyConfig object directly."""
    cfg = ProxyConfig(
        proxy_type="socks5",
        ip="23.27.210.99",
        port="6469",
        username="iifcuwil",
        password="o6jm2azbq5gs",
    )
    res = ProxyManager.test_connection(cfg, timeout=10.0, target_host="www.google.com", target_port=80)
    assert res["alive"] is True
    assert res["latency_ms"] > 0.0
    assert res["error"] is None


def test_proxy_test_connection_invalid_input_type():
    """Failure test: Invalid input type (integer or None) should gracefully return error."""
    res = ProxyManager.test_connection(12345)  # type: ignore
    assert res["alive"] is False
    assert res["latency_ms"] == -1.0
    assert "Invalid proxy parameter type" in res["error"]


def test_proxy_test_connection_missing_port():
    """Failure test: Proxy string missing port should return error."""
    res = ProxyManager.test_connection("socks5://1.2.3.4")
    assert res["alive"] is False
    assert "Missing proxy IP or port" in res["error"]


def test_proxy_test_connection_unreachable_dead_proxy():
    """Edge case: Unreachable/dead proxy should fail quickly and report error without crashing."""
    dead_proxy = "socks5://127.0.0.1:59999"
    res = ProxyManager.test_connection(dead_proxy, timeout=1.5)
    assert res["alive"] is False
    assert res["latency_ms"] == -1.0
    assert res["error"] is not None
