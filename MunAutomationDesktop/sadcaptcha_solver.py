"""
SadCaptcha Solver Module for TikTok (Slide Puzzle, Rotate Puzzle, 3D Shapes)
Hỗ trợ:
- Tự động load/save API Key từ config file (~/mun_checker_settings.json hoặc setting dialog).
- Gọi API SadCaptcha lấy tọa độ pixel trượt x / góc xoay.
- Điều khiển CDP Dispatch Mouse Events kéo mượt mà theo đường cong Bezier.
"""

import os
import json
import asyncio
import logging
import random
import math
from typing import Optional, Dict, Any, Tuple
import requests

import nodriver.cdp.input_ as input_cdp

logger = logging.getLogger("SadCaptchaSolver")

CONFIG_PATH = os.path.expanduser("~/.mun_checker_settings.json")


def load_settings() -> Dict[str, Any]:
    """Tải cài đặt cấu hình checker (SadCaptcha Key, luồng, timeout...)."""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Lỗi đọc config: {e}")
    return {
        "sadcaptcha_api_key": "",
        "max_threads": 5,
        "proxy_pool_url": "https://proxy.webshare.io/api/v2/proxy/list/download/lfdlebxwolvropzxpyuiwqbqyngnvfhkpsmjesxe/-/any/username/direct/-/?plan_id=13766824",
        "solve_captcha_enabled": True
    }


def save_settings(settings: Dict[str, Any]) -> bool:
    """Lưu cài đặt cấu hình checker."""
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Lỗi lưu config: {e}")
        return False


def get_api_key() -> str:
    """Lấy SadCaptcha API Key từ config hoặc ENV."""
    cfg = load_settings()
    return cfg.get("sadcaptcha_api_key") or os.getenv("SADCAPTCHA_API_KEY", "")


class SadCaptchaSolver:
    """Engine giải Captcha (TikTok, Taobao / Alibaba SECSDK Slider, Geetest) qua SadCaptcha API và CDP mouse events."""

    BASE_URL = "https://www.sadcaptcha.com/api/v1"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or get_api_key()

    def set_api_key(self, api_key: str):
        self.api_key = api_key
        cfg = load_settings()
        cfg["sadcaptcha_api_key"] = api_key
        save_settings(cfg)

    def is_configured(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    async def solve_taobao_slider(self, tab) -> bool:
        """Tự động phát hiện và giải thanh trượt Taobao / Alibaba SECSDK NC Slider."""
        try:
            # 1. Kiểm tra sự tồn tại của slider
            slider_info = await tab.evaluate("""
                (() => {
                    const btn = document.querySelector('#nc_1_n1z, .btn_slide, .nc_iconfont.btn_slide');
                    const track = document.querySelector('#nc_1_n1t, .nc_scale, .nc_wrapper');
                    if (!btn || !track) return null;
                    const btnRect = btn.getBoundingClientRect();
                    const trackRect = track.getBoundingClientRect();
                    return JSON.stringify({
                        x: btnRect.x + btnRect.width / 2,
                        y: btnRect.y + btnRect.height / 2,
                        distance: trackRect.width - btnRect.width + 10
                    });
                })()
            """)
            if not slider_info:
                return False

            data = json.loads(slider_info) if isinstance(slider_info, str) else slider_info
            start_x = float(data.get("x", 0))
            start_y = float(data.get("y", 0))
            distance = float(data.get("distance", 260))

            if start_x <= 0 or distance <= 0:
                return False

            logger.info(f"[*] Phát hiện Taobao SECSDK Slider tại ({start_x}, {start_y}), cự ly kéo: {distance}px")

            # 2. Điều khiển CDP kéo mượt mà theo đường cong sinh học
            await self.human_bezier_drag(tab, start_x, start_y, distance)
            await asyncio.sleep(2.5)

            # 3. Kiểm tra kết quả vượt slider
            passed = await tab.evaluate("""
                (() => {
                    const successText = document.querySelector('.nc-lang-cnt, .scale_text');
                    if (successText && (successText.innerText.includes('验证通过') || successText.innerText.includes('Verified') || successText.innerText.includes('通过'))) {
                        return true;
                    }
                    return !document.querySelector('#nc_1_wrapper, .nc_wrapper, #baxia-punish');
                })()
            """)
            return bool(passed)
        except Exception as e:
            logger.error(f"[-] Lỗi giải Taobao slider: {e}")
            return False

    async def extract_captcha_images(self, tab) -> Optional[Dict[str, str]]:
        """Trích xuất ảnh nền và mảnh ghép từ DOM TikTok Captcha."""
        try:
            data = await tab.evaluate("""
                (() => {
                    const bg = document.querySelector('#captcha-verify-image') || document.querySelector('.captcha-verify-image') || document.querySelector('img[alt="captcha"]');
                    const piece = document.querySelector('img.captcha_verify_img_slide') || document.querySelector('.captcha_verify_img_slide');
                    const slider = document.querySelector('.secsdk-captcha-drag-icon') || document.querySelector('.captcha_drag_icon') || document.querySelector('.secsdk_captcha_drag_icon');
                    
                    let sliderRect = null;
                    if (slider) {
                        const rect = slider.getBoundingClientRect();
                        sliderRect = { x: rect.x + rect.width / 2, y: rect.y + rect.height / 2, width: rect.width, height: rect.height };
                    }
                    
                    return {
                        bg_url: bg ? bg.src : '',
                        piece_url: piece ? piece.src : '',
                        has_slider: !!slider,
                        slider_rect: sliderRect
                    };
                })()
            """)
            if data and isinstance(data, dict) and data.get("bg_url"):
                return data
            return None
        except Exception as e:
            logger.warning(f"Lỗi extract captcha DOM: {e}")
            return None

    async def call_puzzle_api_async(self, puzzle_image_b64_or_url: str, piece_image_b64_or_url: str) -> Optional[int]:
        """Gửi request không chặn async lên SadCaptcha Puzzle API để lấy tọa độ slide_x."""
        if not self.is_configured():
            logger.error("SadCaptcha API Key chưa được thiết lập!")
            return None

        url = f"{self.BASE_URL}/puzzle"
        payload = {
            "api_key": self.api_key,
            "puzzle_image_b64": puzzle_image_b64_or_url,
            "piece_image_b64": piece_image_b64_or_url
        }

        try:
            import httpx
            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    slide_x = data.get("slide_x") or data.get("distance")
                    return int(slide_x) if slide_x is not None else None
                else:
                    logger.warning(f"SadCaptcha API error: {res.status_code} - {res.text}")
                    return None
        except Exception as e:
            logger.error(f"Lỗi kết nối SadCaptcha API: {e}")
            return None
            return None

    async def human_bezier_drag(self, tab, start_x: float, start_y: float, distance_x: float):
        """Mô phỏng kéo thanh trượt theo quỹ đạo đường cong Bezier của người thật."""
        steps = random.randint(25, 40)
        target_x = start_x + distance_x
        target_y = start_y + random.uniform(-2.0, 2.0)

        # 1. Di chuyển chuột tới slider và nhấn chuột xuống
        await tab.send(input_cdp.dispatch_mouse_event(
            type_="mouseMoved", x=start_x, y=start_y
        ))
        await asyncio.sleep(random.uniform(0.08, 0.15))
        await tab.send(input_cdp.dispatch_mouse_event(
            type_="mousePressed", x=start_x, y=start_y, button=input_cdp.MouseButton.LEFT, click_count=1
        ))
        await asyncio.sleep(random.uniform(0.05, 0.12))

        # 2. Tạo đường cong di chuyển có gia tốc
        curr_x = start_x
        curr_y = start_y
        for i in range(1, steps + 1):
            t = i / steps
            # Gia tốc hình sin (nhanh ở giữa, chậm lại khi gần đến đích)
            ease = math.sin(t * (math.pi / 2))
            next_x = start_x + distance_x * ease
            # Rung nhẹ trục Y
            next_y = start_y + math.sin(t * math.pi * 3) * random.uniform(1.0, 2.5)

            await tab.send(input_cdp.dispatch_mouse_event(
                type_="mouseMoved", x=next_x, y=next_y, button=input_cdp.MouseButton.LEFT
            ))
            # Delay ngẫu nhiên giữa các bước di chuyển
            await asyncio.sleep(random.uniform(0.008, 0.025))

        # 3. Quá đà nhẹ và căn chỉnh lại (Human Overshoot effect)
        overshoot = random.uniform(1.5, 4.0)
        await tab.send(input_cdp.dispatch_mouse_event(
            type_="mouseMoved", x=target_x + overshoot, y=target_y, button=input_cdp.MouseButton.LEFT
        ))
        await asyncio.sleep(random.uniform(0.04, 0.08))
        await tab.send(input_cdp.dispatch_mouse_event(
            type_="mouseMoved", x=target_x, y=target_y, button=input_cdp.MouseButton.LEFT
        ))
        await asyncio.sleep(random.uniform(0.05, 0.15))

        # 4. Thả chuột
        await tab.send(input_cdp.dispatch_mouse_event(
            type_="mouseReleased", x=target_x, y=target_y, button=input_cdp.MouseButton.LEFT, click_count=1
        ))
        logger.info(f"[+] Hoàn tất thao tác kéo chuột {distance_x}px qua CDP.")

    async def solve_and_drag(self, tab) -> bool:
        """Hàm tổng hợp: phát hiện captcha -> gửi SadCaptcha -> kéo thanh trượt."""
        if not self.is_configured():
            logger.info("Chưa có SadCaptcha API Key, bỏ qua giải captcha.")
            return False

        captcha_info = await self.extract_captcha_images(tab)
        if not captcha_info or not captcha_info.get("has_slider"):
            logger.info("Không phát hiện thành phần Captcha cần giải.")
            return False

        bg_url = str(captcha_info.get("bg_url", ""))
        piece_url = str(captcha_info.get("piece_url", ""))
        slider_rect = captcha_info.get("slider_rect")

        if not bg_url:
            return False

        logger.info("[*] Gửi ảnh captcha lên SadCaptcha để giải...")
        slide_x = await self.call_puzzle_api_async(bg_url, piece_url)
        if not slide_x:
            return False

        start_x = float(slider_rect.get("x", 200.0)) if isinstance(slider_rect, dict) else 200.0
        start_y = float(slider_rect.get("y", 400.0)) if isinstance(slider_rect, dict) else 400.0

        await self.human_bezier_drag(tab, start_x, start_y, slide_x)
        await asyncio.sleep(2.5)  # Đợi TikTok xác thực kết quả captcha
        return True
