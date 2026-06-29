import os
import sys
import random
import time
import socket
import threading
import asyncio
import base64
import logging
import http.server
import socketserver

_http_server_started = False
_http_server_lock = threading.Lock()

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class WDAHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        ipa_path = getattr(self.server, 'ipa_path', '')
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            
            local_ip = get_local_ip()
            ts_url = f"apple-magnifier://install?url=http://{local_ip}:8081/WebDriverAgentRunner.ipa"
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Cài đặt WebDriverAgent</title>
                <style>
                    body {{
                        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
                        background-color: #f5f5f7;
                        color: #1d1d1f;
                        text-align: center;
                        padding: 30px 15px;
                        margin: 0;
                    }}
                    .container {{
                        background: white;
                        border-radius: 18px;
                        padding: 24px;
                        max-width: 400px;
                        margin: 0 auto;
                        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
                    }}
                    h1 {{
                        font-size: 24px;
                        margin-bottom: 8px;
                    }}
                    p {{
                        font-size: 14px;
                        color: #86868b;
                        line-height: 1.5;
                    }}
                    .btn {{
                        display: block;
                        background-color: #0071e3;
                        color: white;
                        text-decoration: none;
                        padding: 14px 20px;
                        border-radius: 10px;
                        font-weight: 600;
                        font-size: 16px;
                        margin: 20px 0;
                        transition: background-color 0.2s;
                    }}
                    .btn:hover {{
                        background-color: #0077ed;
                    }}
                    .btn-secondary {{
                        background-color: #86868b;
                    }}
                    .btn-secondary:hover {{
                        background-color: #98989d;
                    }}
                    .instructions {{
                        text-align: left;
                        font-size: 13px;
                        background: #f5f5f7;
                        padding: 12px;
                        border-radius: 8px;
                        margin-top: 20px;
                    }}
                    ol {{
                        padding-left: 20px;
                        margin: 8px 0;
                    }}
                    li {{
                        margin-bottom: 6px;
                    }}
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>Cài đặt WebDriverAgent</h1>
                    <p>Chọn phương thức cài đặt qua TrollStore cho iPhone của bạn:</p>
                    
                    <a class="btn" href="{ts_url}">Cách 1: Cài trực tiếp qua TrollStore</a>
                    <p style="font-size: 11px; margin-top:-10px;">(Yêu cầu đã bật "URL Scheme" trong cài đặt TrollStore)</p>
                    
                    <a class="btn btn-secondary" href="/WebDriverAgentRunner.ipa">Cách 2: Tải file IPA về máy</a>
                    
                    <div class="instructions">
                        <strong>Hướng dẫn cách 2 (Nếu cách 1 không hoạt động):</strong>
                        <ol>
                            <li>Bấm <strong>Tải file IPA về máy</strong> và xác nhận tải xuống.</li>
                            <li>Mở trình tải xuống trong Safari (hoặc ứng dụng Tệp/Files).</li>
                            <li>Nhấn giữ vào file <code>WebDriverAgentRunner.ipa</code> vừa tải về.</li>
                            <li>Chọn <strong>Chia sẻ (Share)</strong> -> Chọn ứng dụng <strong>TrollStore</strong> để cài đặt.</li>
                        </ol>
                    </div>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode('utf-8'))
            
        elif self.path == '/WebDriverAgentRunner.ipa':
            if ipa_path and os.path.exists(ipa_path):
                self.send_response(200)
                self.send_header('Content-Type', 'application/octet-stream')
                self.send_header('Content-Disposition', 'attachment; filename="WebDriverAgentRunner.ipa"')
                self.send_header('Content-Length', str(os.path.getsize(ipa_path)))
                self.end_headers()
                with open(ipa_path, 'rb') as f:
                    self.wfile.write(f.read())
            else:
                self.send_error(404, "File not found")
        else:
            self.send_error(404, "Not found")

def ensure_wda_http_server(ipa_path):
    global _http_server_started
    with _http_server_lock:
        if _http_server_started:
            return True
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(('127.0.0.1', 8081))
            s.close()
            _http_server_started = True
            logger.info("WDA HTTP server is already running on port 8081.")
            return True
        except Exception:
            pass
        try:
            class CustomTCPServer(socketserver.TCPServer):
                allow_reuse_address = True
            server = CustomTCPServer(('0.0.0.0', 8081), WDAHTTPHandler)
            server.ipa_path = ipa_path
            t = threading.Thread(target=server.serve_forever, daemon=True)
            t.start()
            _http_server_started = True
            logger.info("Started WDA HTTP server on port 8081.")
            return True
        except Exception as e:
            logger.error(f"Failed to start WDA HTTP server: {e}")
            return False

logger = logging.getLogger("DeviceBridge")
logger.setLevel(logging.INFO)

# Setup simple console handler if needed
if not logger.handlers:
    ch = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

PYMOBILEDEVICE3_AVAILABLE = False

try:
    import pymobiledevice3
    import pymobiledevice3.usbmux as usbmux
    from pymobiledevice3.lockdown import create_using_usbmux
    from pymobiledevice3.services.installation_proxy import InstallationProxyService
    from pymobiledevice3.services.screenshot import ScreenshotService
    from pymobiledevice3.services.simulate_location import DtSimulateLocation
    from pymobiledevice3.services.wda import WdaClient
    from pymobiledevice3.services.afc import AfcService
    
    # DVT services
    from pymobiledevice3.services.dvt.instruments.dvt_provider import DvtProvider
    from pymobiledevice3.services.dvt.instruments.screenshot import Screenshot
    from pymobiledevice3.services.dvt.instruments.process_control import ProcessControl
    from pymobiledevice3.services.dvt.instruments.location_simulation import LocationSimulation
    from pymobiledevice3.services.dvt.testmanaged.xcuitest import XCUITestService, TestConfig
    
    PYMOBILEDEVICE3_AVAILABLE = True
except Exception as e:
    logger.warning(f"Failed to import pymobiledevice3 dependencies: {e}")


class PortForwarder:
    def __init__(self, local_port, remote_port, device_serial):
        self.local_port = local_port
        self.remote_port = remote_port
        self.device_serial = device_serial
        self.running = False
        self.server_sock = None
        self.thread = None
        self.cached_device = None

    def start(self):
        self.running = True
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_sock.bind(('127.0.0.1', self.local_port))
        self.server_sock.listen(5)
            
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"PortForwarder started on localhost:{self.local_port} -> device:{self.remote_port}")

    def _run(self):
        # Resolve the device once asynchronously in the thread to cache it
        try:
            async def resolve():
                devs = await usbmux.list_devices()
                for d in devs:
                    if d.serial == self.device_serial:
                        return d
                if devs:
                    return devs[0]
                return None
            loop = asyncio.new_event_loop()
            self.cached_device = loop.run_until_complete(resolve())
            loop.close()
        except Exception as e:
            logger.error(f"Error resolving usbmux device in thread: {e}")

        while self.running:
            try:
                client_sock, addr = self.server_sock.accept()
            except Exception:
                break
            
            # Start forwarding in a thread
            threading.Thread(target=self._forward_conn, args=(client_sock,), daemon=True).start()

    def _forward_conn(self, client_sock):
        loop = asyncio.new_event_loop()
        
        async def do_relay():
            try:
                dev = self.cached_device
                if not dev:
                    devs = await usbmux.list_devices()
                    for d in devs:
                        if d.serial == self.device_serial:
                            dev = d
                            break
                    if not dev and devs:
                        dev = devs[0] # Fallback
                if not dev:
                    logger.error("No device found for port relay!")
                    client_sock.close()
                    return
                
                device_sock = await dev.connect(self.remote_port)
                
                def pipe(src, dst):
                    try:
                        while self.running:
                            data = src.recv(4096)
                            if not data:
                                break
                            dst.sendall(data)
                    except Exception:
                        pass
                    finally:
                        try:
                            src.close()
                        except Exception:
                            pass
                        try:
                            dst.close()
                        except Exception:
                            pass

                t1 = threading.Thread(target=pipe, args=(client_sock, device_sock), daemon=True)
                t2 = threading.Thread(target=pipe, args=(device_sock, client_sock), daemon=True)
                t1.start()
                t2.start()
            except Exception as e:
                logger.error(f"Relay connection failed: {e}")
                client_sock.close()

        loop.run_until_complete(do_relay())
        loop.close()

    def stop(self):
        self.running = False
        if self.server_sock:
            try:
                self.server_sock.close()
            except Exception:
                pass
        logger.info("PortForwarder stopped.")


class WDARunnerThread(threading.Thread):
    def __init__(self, serial, wda_bundle_id):
        super().__init__()
        self.serial = serial
        self.bundle_id = wda_bundle_id
        self.daemon = True
        self.loop = None
        self.running = False
        self.exception = None

    def run(self):
        self.running = True
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        async def _run_wda():
            try:
                # Connect on-the-fly inside this thread's loop
                lockdown = await create_using_usbmux(serial=self.serial)
                try:
                    from pymobiledevice3.cli.mounter import auto_mount
                    await auto_mount(lockdown)
                except Exception:
                    pass
                cfg = await TestConfig.create_for(lockdown, self.bundle_id)
                svc = XCUITestService(lockdown)
                await svc.run(cfg)
            except Exception as e:
                self.exception = e
                logger.error(f"Error running WDA: {e}")

        try:
            self.loop.run_until_complete(_run_wda())
        finally:
            self.running = False
            self.loop.close()

    def stop(self):
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)


if PYMOBILEDEVICE3_AVAILABLE:
    class WDAClient(WdaClient):
        def __init__(self, host="http://127.0.0.1", port=8100, serial=None):
            # Parse host/port into base_url
            if not host.startswith("http"):
                host = f"http://{host}"
            base_url = f"{host}:{port}"
            super().__init__(base_url=base_url)
            self.session_id = None
            self.serial = serial

        def check_status(self) -> bool:
            try:
                status = self.get_status()
                return isinstance(status, dict)
            except Exception:
                return False

        def start_session(self, bundle_id: str = None) -> bool:
            try:
                session_id = super().start_session(bundle_id)
                self.session_id = session_id
                return self.session_id is not None
            except Exception:
                return False

        def launch_app(self, bundle_id: str) -> bool:
            try:
                session_id = self.session_id
                if not session_id:
                    if not self.start_session():
                        return False
                    session_id = self.session_id
                payload = {"bundleId": bundle_id}
                self._request_json("POST", f"/session/{session_id}/wda/apps/launch", payload)
                return True
            except Exception:
                return False

        def swipe(self, from_x: float, from_y: float, to_x: float, to_y: float, duration_ms: int = 500) -> bool:
            try:
                session_id = self.session_id
                if not session_id:
                    return False
                
                # Add natural randomized jitter to start and end points
                jitter_fx = from_x + random.uniform(-6.0, 6.0)
                jitter_fy = from_y + random.uniform(-10.0, 10.0)
                jitter_tx = to_x + random.uniform(-6.0, 6.0)
                jitter_ty = to_y + random.uniform(-10.0, 10.0)
                
                # Randomize duration slightly (+/- 10%)
                randomized_duration = (duration_ms + random.randint(-50, 50)) / 1000.0
                randomized_duration = max(0.1, randomized_duration)
                
                super().swipe(
                    start_x=int(jitter_fx),
                    start_y=int(jitter_fy),
                    end_x=int(jitter_tx),
                    end_y=int(jitter_ty),
                    duration=randomized_duration,
                    session_id=session_id
                )
                return True
            except Exception as e:
                logger.error(f"WDA swipe error: {e}")
                return False

        def tap(self, x: float, y: float) -> bool:
            try:
                session_id = self.session_id
                if not session_id:
                    return False
                
                # Add human-like touch offset (jitter)
                jitter_x = x + random.uniform(-3.5, 3.5)
                jitter_y = y + random.uniform(-3.5, 3.5)
                
                payload = {"x": jitter_x, "y": jitter_y}
                try:
                    self._request_json("POST", f"/session/{session_id}/wda/tap/0", payload)
                except Exception:
                    self._request_json("POST", f"/session/{session_id}/click", payload)
                return True
            except Exception:
                return False

        def type_text(self, text: str) -> bool:
            try:
                session_id = self.session_id
                if not session_id:
                    return False
                self.send_keys(text, session_id=session_id)
                return True
            except Exception:
                return False

        def go_home(self) -> bool:
            try:
                session_id = self.session_id
                if not session_id:
                    return False
                self.press_button("home", session_id=session_id)
                return True
            except Exception:
                return False

        def get_window_size(self) -> dict:
            try:
                session_id = self.session_id
                if not session_id:
                    return {"width": 375, "height": 812}
                return super().get_window_size(session_id=session_id)
            except Exception:
                return {"width": 375, "height": 812}

        def screenshot(self) -> str:
            # Try native screenshot first if serial is provided, as it is much faster and bypasses WDA completely
            if self.serial:
                try:
                    img_bytes = DeviceBridge.take_screenshot(self.serial)
                    if img_bytes:
                        return base64.b64encode(img_bytes).decode('utf-8')
                except Exception as e:
                    logger.warning(f"Native take_screenshot failed: {e}. Falling back to WDA.")
            try:
                session_id = self.session_id
                img_bytes = self.get_screenshot(session_id=session_id)
                if img_bytes:
                    return base64.b64encode(img_bytes).decode('utf-8')
            except Exception:
                pass
            return ""

        def close_session(self) -> bool:
            if not self.session_id:
                return True
            try:
                self._request_json("DELETE", f"/session/{self.session_id}", {})
                self.session_id = None
                return True
            except Exception:
                return False
else:
    class WDAClient:
        def __init__(self, host="http://127.0.0.1", port=8100):
            pass
        def check_status(self) -> bool:
            return False
        def start_session(self, bundle_id: str = None) -> bool:
            return False
        def launch_app(self, bundle_id: str) -> bool:
            return False
        def swipe(self, from_x: float, from_y: float, to_x: float, to_y: float, duration_ms: int = 500) -> bool:
            return False
        def tap(self, x: float, y: float) -> bool:
            return False
        def type_text(self, text: str) -> bool:
            return False
        def go_home(self) -> bool:
            return False
        def get_window_size(self) -> dict:
            return {"width": 375, "height": 812}
        def screenshot(self) -> str:
            return ""
        def close_session(self) -> bool:
            return True


class DeviceBridge:
    @staticmethod
    def get_connected_devices() -> list:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return []
        try:
            async def _list():
                return await usbmux.list_devices()
            devs = asyncio.run(_list())
            result = []
            for d in devs:
                result.append({
                    "serial": d.serial,
                    "connection_type": d.connection_type,
                    "devid": getattr(d, "devid", None)
                })
            return result
        except Exception as e:
            logger.error(f"Error listing connected devices: {e}")
            return []

    @staticmethod
    def get_device_info(serial=None) -> dict:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return {}
        try:
            async def _get():
                lockdown = await create_using_usbmux(serial=serial)
                info = getattr(lockdown, "short_info", {})
                if not info:
                    info = {
                        "Identifier": lockdown.udid,
                        "DeviceName": "iPhone",
                        "ProductVersion": lockdown.product_version,
                        "ProductType": lockdown.product_type,
                    }
                return {
                    "udid": info.get("Identifier", lockdown.udid),
                    "name": info.get("DeviceName", "iPhone"),
                    "ios_version": info.get("ProductVersion", lockdown.product_version),
                    "model": info.get("ProductType", lockdown.product_type),
                    "connection_type": info.get("ConnectionType", "USB")
                }
            return asyncio.run(_get())
        except Exception as e:
            logger.error(f"Error getting device info: {e}")
            return {}

    @staticmethod
    def take_screenshot(serial=None) -> bytes:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return b""
        
        async def _take():
            lockdown = await create_using_usbmux(serial=serial)
            try:
                from pymobiledevice3.services.screenshot import ScreenshotService
                return await ScreenshotService(lockdown).take_screenshot()
            except Exception as e:
                logger.info(f"Direct ScreenshotService failed: {e}. Trying auto_mount.")
                try:
                    from pymobiledevice3.cli.mounter import auto_mount
                    await asyncio.wait_for(auto_mount(lockdown), timeout=10.0)
                    from pymobiledevice3.services.screenshot import ScreenshotService
                    return await ScreenshotService(lockdown).take_screenshot()
                except Exception as mount_err:
                    logger.info(f"ScreenshotService with mount failed: {mount_err}. Trying DVT fallback.")
                    
            async with DvtProvider(lockdown) as dvt, Screenshot(dvt) as screenshot:
                return await screenshot.get_screenshot()
                
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                res = []
                err = []
                def run_thread():
                    try:
                        new_loop = asyncio.new_event_loop()
                        res.append(new_loop.run_until_complete(_take()))
                        new_loop.close()
                    except Exception as ex:
                        err.append(ex)
                t = threading.Thread(target=run_thread)
                t.start()
                t.join()
                if err:
                    raise err[0]
                return res[0]
            else:
                return asyncio.run(_take())
        except Exception as e:
            logger.error(f"All screenshot methods failed: {e}")
            raise RuntimeError(f"Cannot take screenshot: {e}")

    @staticmethod
    def launch_app(serial, bundle_id: str) -> int:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return -1
        try:
            async def _launch():
                lockdown = await create_using_usbmux(serial=serial)
                try:
                    async with DvtProvider(lockdown) as dvt, ProcessControl(dvt) as pc:
                        return await pc.launch(bundle_id=bundle_id)
                except Exception as e:
                    logger.info(f"Direct launch_app failed: {e}. Trying auto_mount.")
                    try:
                        from pymobiledevice3.cli.mounter import auto_mount
                        await asyncio.wait_for(auto_mount(lockdown), timeout=10.0)
                        async with DvtProvider(lockdown) as dvt, ProcessControl(dvt) as pc:
                            return await pc.launch(bundle_id=bundle_id)
                    except Exception as mount_err:
                        logger.error(f"Launch app with mount failed: {mount_err}")
                        raise RuntimeError(f"Cannot launch app: {mount_err}")
            return asyncio.run(_launch())
        except Exception as e:
            logger.error(f"Failed to launch app {bundle_id}: {e}")
            raise RuntimeError(f"Cannot launch app: {e}")

    @staticmethod
    def kill_app(serial, bundle_id: str) -> bool:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return False
        try:
            async def _kill():
                lockdown = await create_using_usbmux(serial=serial)
                try:
                    async with DvtProvider(lockdown) as dvt, ProcessControl(dvt) as pc:
                        pid = await pc.process_identifier_for_bundle_identifier(bundle_id)
                        if pid and pid > 0:
                            await pc.kill(pid)
                            return True
                        return False
                except Exception as e:
                    logger.info(f"Direct kill_app failed: {e}. Trying auto_mount.")
                    try:
                        from pymobiledevice3.cli.mounter import auto_mount
                        await asyncio.wait_for(auto_mount(lockdown), timeout=10.0)
                        async with DvtProvider(lockdown) as dvt, ProcessControl(dvt) as pc:
                            pid = await pc.process_identifier_for_bundle_identifier(bundle_id)
                            if pid and pid > 0:
                                await pc.kill(pid)
                                return True
                            return False
                    except Exception as mount_err:
                        logger.error(f"Kill app with mount failed: {mount_err}")
                        return False
            return asyncio.run(_kill())
        except Exception as e:
            logger.error(f"Failed to kill app {bundle_id}: {e}")
            return False

    @staticmethod
    def simulate_location(serial, latitude: float, longitude: float) -> bool:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return False
        
        async def _set():
            lockdown = await create_using_usbmux(serial=serial)
            try:
                service = DtSimulateLocation(lockdown)
                await service.set(latitude, longitude)
                return True
            except Exception as e:
                logger.info(f"Direct simulate_location failed: {e}. Trying auto_mount.")
                try:
                    from pymobiledevice3.cli.mounter import auto_mount
                    await asyncio.wait_for(auto_mount(lockdown), timeout=10.0)
                    service = DtSimulateLocation(lockdown)
                    await service.set(latitude, longitude)
                    return True
                except Exception as mount_err:
                    logger.info(f"DtSimulateLocation with mount failed, trying DVT: {mount_err}")
                
            async with DvtProvider(lockdown) as dvt, LocationSimulation(dvt) as ls:
                await ls.set(latitude, longitude)
                return True
                
        try:
            return asyncio.run(_set())
        except Exception as e:
            logger.error(f"All simulate location methods failed: {e}")
            raise RuntimeError(f"Cannot simulate location: {e}")

    @staticmethod
    def clear_location(serial) -> bool:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return False
        
        async def _clear():
            lockdown = await create_using_usbmux(serial=serial)
            try:
                service = DtSimulateLocation(lockdown)
                await service.clear()
                return True
            except Exception as e:
                logger.info(f"Direct clear_location failed: {e}. Trying auto_mount.")
                try:
                    from pymobiledevice3.cli.mounter import auto_mount
                    await asyncio.wait_for(auto_mount(lockdown), timeout=10.0)
                    service = DtSimulateLocation(lockdown)
                    await service.clear()
                    return True
                except Exception as mount_err:
                    logger.info(f"DtSimulateLocation clear with mount failed, trying DVT: {mount_err}")
                
            async with DvtProvider(lockdown) as dvt, LocationSimulation(dvt) as ls:
                await ls.clear()
                return True
                
        try:
            return asyncio.run(_clear())
        except Exception as e:
            logger.error(f"All clear location methods failed: {e}")
            raise RuntimeError(f"Cannot clear simulated location: {e}")

    @staticmethod
    def list_apps(serial=None) -> dict:
        if not PYMOBILEDEVICE3_AVAILABLE:
            return {}
        try:
            async def _list():
                lockdown = await create_using_usbmux(serial=serial)
                service = InstallationProxyService(lockdown)
                return await service.get_apps()
            return asyncio.run(_list())
        except Exception as e:
            logger.error(f"Failed to list apps: {e}")
            return {}

    @staticmethod
    def install_ipa(serial, ipa_path: str):
        if not PYMOBILEDEVICE3_AVAILABLE:
            return
        try:
            async def _install():
                lockdown = await create_using_usbmux(serial=serial)
                service = InstallationProxyService(lockdown)
                await service.install_from_local(ipa_path)
            asyncio.run(_install())
        except Exception as e:
            logger.error(f"Failed to install IPA {ipa_path}: {e}")
            raise RuntimeError(f"Cannot install IPA: {e}")


class WDAManager:
    def __init__(self, local_port=8100, remote_port=8100):
        self.local_port = local_port
        self.remote_port = remote_port
        self.relay = None
        self.runner_thread = None

    def check_wda_installed(self, serial) -> str:
        """Returns the bundle ID of the installed WDA, or empty string if not found."""
        if not PYMOBILEDEVICE3_AVAILABLE:
            return ""
        try:
            apps = DeviceBridge.list_apps(serial)
            for bundle_id in apps.keys():
                if "webdriveragentrunner" in bundle_id.lower():
                    return bundle_id
        except Exception as e:
            logger.error(f"Error checking WDA installation: {e}")
        return ""

    def install_wda(self, serial, ipa_path: str):
        DeviceBridge.install_ipa(serial, ipa_path)

    def start_wda(self, serial, wda_bundle_id: str) -> bool:
        """Launches WDA on the device using DVT."""
        self.stop_wda()
        try:
            self.runner_thread = WDARunnerThread(serial, wda_bundle_id)
            self.runner_thread.start()
            
            # Wait for thread to start or error out
            time.sleep(1)
            if self.runner_thread.exception:
                raise self.runner_thread.exception
            return True
        except Exception as e:
            logger.error(f"Failed to start WDA: {e}")
            self.stop_wda()
            return False

    def stop_wda(self):
        if self.runner_thread:
            self.runner_thread.stop()
            self.runner_thread = None

    def start_relay(self, device_serial: str) -> bool:
        self.stop_relay()
        try:
            self.relay = PortForwarder(self.local_port, self.remote_port, device_serial)
            self.relay.start()
            return True
        except Exception as e:
            logger.error(f"Failed to start port relay: {e}")
            return False

    def stop_relay(self):
        if self.relay:
            self.relay.stop()
            self.relay = None

    def auto_setup(self, serial, ipa_path: str, log_cb=None) -> bool:
        """
        Auto-setup WDA on device using serial (keeps all calls strictly inside separate event loops):
        1. Check if WDA installed. If not, installs it.
        2. Launches WDA.
        3. Sets up port relay.
        4. Verifies connection to WDA status endpoint.
        """
        def log(msg):
            if log_cb:
                log_cb(msg)
            else:
                logger.info(msg)

        if not PYMOBILEDEVICE3_AVAILABLE:
            log("❌ Lỗi: Thư viện pymobiledevice3 không khả dụng.")
            return False

        log("🔄 Đang quét thiết bị và kiểm tra WDA...")
        
        bundle_id = self.check_wda_installed(serial)
        if not bundle_id:
            log("ℹ️ Không tìm thấy WebDriverAgent trên thiết bị.")
            if not os.path.exists(ipa_path):
                log(f"❌ Lỗi: Không tìm thấy file WDA IPA tại {ipa_path}")
                return False
            
            # Check if TrollStore is installed on the device
            trollstore_installed = False
            try:
                apps = DeviceBridge.list_apps(serial)
                if "com.opa334.TrollStore" in apps:
                    trollstore_installed = True
            except Exception:
                pass

            log(f"📦 Đang tiến hành cài đặt WDA IPA từ {ipa_path}...")
            try:
                self.install_wda(serial, ipa_path)
                log("✅ Cài đặt WDA hoàn tất.")
            except Exception as e:
                log(f"⚠️ Cài đặt WDA qua cổng hệ thống thất bại: {e}")
                if trollstore_installed:
                    log("ℹ️ Phát hiện TrollStore trên thiết bị. Tiến hành cài đặt qua TrollStore...")
                    try:
                        # 1. Start dynamic HTTP server to serve the IPA
                        ensure_wda_http_server(ipa_path)
                        local_ip = get_local_ip()
                        server_url = f"http://{local_ip}:8081/"
                        
                        # 2. Push via AFC as a backup
                        log("📦 Đang chép file WDA IPA vào thiết bị qua cổng AFC làm bản dự phòng...")
                        try:
                            async def _push():
                                lockdown = await create_using_usbmux(serial=serial)
                                afc = AfcService(lockdown)
                                await afc.push(ipa_path, "/Downloads/WebDriverAgentRunner.ipa")
                            asyncio.run(_push())
                            log("✅ Đã chép file IPA.")
                        except Exception as afc_err:
                            log(f"⚠️ Không thể sao chép qua AFC: {afc_err}")
                        
                        # 3. Launch Safari pointing to local server URL
                        log("🚀 Đang mở Safari trên màn hình iPhone...")
                        async def _launch_safari():
                            lockdown = await create_using_usbmux(serial=serial)
                            try:
                                from pymobiledevice3.cli.mounter import auto_mount
                                await auto_mount(lockdown)
                            except Exception:
                                pass
                            
                            webinspector_ok = False
                            try:
                                from pymobiledevice3.services.webinspector import WebinspectorService
                                from pymobiledevice3.services.web_protocol.driver import WebDriver
                                from contextlib import asynccontextmanager

                                @asynccontextmanager
                                async def local_webinspector(ld):
                                    ins = WebinspectorService(lockdown=ld)
                                    await ins.connect()
                                    async with ins:
                                        yield ins

                                log("🌐 Đang tải URL trực tiếp vào Safari qua WebInspector...")
                                async with local_webinspector(lockdown) as inspector:
                                    safari_app = await inspector.open_app("com.apple.mobilesafari")
                                    session = await inspector.automation_session(safari_app)
                                    driver = WebDriver(session)
                                    await driver.start_session()
                                    await driver.get(server_url)
                                    await session.stop_session()
                                log("✅ Đã tải thành công URL vào Safari qua WebInspector.")
                                webinspector_ok = True
                            except Exception as web_err:
                                log(f"⚠️ WebInspector không thể tự động mở URL (hãy bật 'Remote Automation' và 'Web Inspector' trong Cài đặt -> Safari -> Nâng cao): {web_err}")

                            if not webinspector_ok:
                                log("🚀 Đang mở ứng dụng Safari...")
                                async with DvtProvider(lockdown) as dvt, ProcessControl(dvt) as pc:
                                    await pc.launch("com.apple.mobilesafari")
                        
                        try:
                            asyncio.run(_launch_safari())
                            log("📱 Đã gửi tín hiệu mở Safari trên điện thoại.")
                        except Exception as launch_err:
                            log(f"⚠️ Không thể mở Safari tự động: {launch_err}")
                        
                        log("👉 VUI LÒNG MỞ ĐIỆN THOẠI VÀ THỰC HIỆN CÀI ĐẶT:")
                        log(f"🔗 Nếu Safari chưa mở, hãy truy cập địa chỉ: {server_url}")
                        log("  - Cách 1: Bấm 'Cài trực tiếp qua TrollStore' (yêu cầu bật URL Scheme trong cài đặt TrollStore).")
                        log("  - Cách 2: Bấm 'Tải file IPA về máy', mở file đã tải, chọn nút Chia sẻ (Share) -> chọn TrollStore để cài đặt.")
                        log("⏳ Đang chờ cài đặt ứng dụng (tối đa 60 giây)...")
                        
                        # Wait for app to be installed
                        for wait_sec in range(60):
                            time.sleep(1)
                            bundle_id = self.check_wda_installed(serial)
                            if bundle_id:
                                log("🟢 WebDriverAgent đã được cài đặt thành công qua TrollStore!")
                                break
                        else:
                            log("❌ Lỗi: Quá thời gian chờ cài đặt (60 giây).")
                            return False
                    except Exception as ts_err:
                        log(f"❌ Lỗi cài đặt qua TrollStore: {ts_err}")
                        return False
                else:
                    log("❌ Lỗi: Không thể cài đặt WDA vì thiết bị chưa Jailbreak/chưa cài TrollStore để cài app ngoài AppStore.")
                    log("👉 Gợi ý: Hãy cài đặt TrollStore trước (sử dụng tab 'Cài TrollStore tự động' của phần mềm) rồi thử lại.")
                    return False

            # Verify bundle_id again
            bundle_id = self.check_wda_installed(serial)
            if not bundle_id:
                log("❌ Lỗi: Cài đặt thành công nhưng không thể xác nhận Bundle ID của WDA.")
                return False

        log(f"✅ Đã xác nhận WDA được cài đặt với Bundle ID: {bundle_id}")
        log("🚀 Đang khởi động WebDriverAgent trên thiết bị...")
        if not self.start_wda(serial, bundle_id):
            log("❌ Lỗi: Không thể khởi chạy WebDriverAgent.")
            return False

        log("🔌 Đang thiết lập cổng chuyển tiếp dữ liệu (Port Relay)...")
        if not self.start_relay(serial):
            log("❌ Lỗi: Không thể thiết lập Port Relay.")
            return False

        log("⏳ Đang kiểm tra trạng thái hoạt động của WDA...")
        client = WDAClient(host="http://127.0.0.1", port=self.local_port)
        for i in range(10):
            time.sleep(1)
            if client.check_status():
                log("🟢 WebDriverAgent đã khởi động và sẵn sàng hoạt động!")
                return True
        
        log("❌ Lỗi: Đã chạy WDA nhưng không nhận được phản hồi từ cổng 8100.")
        return False
