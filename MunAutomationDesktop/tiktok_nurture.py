"""
TikTok Nurture Automation Module
=================================
Tu dong nuoi tai khoan TikTok voi chien luoc khep kin:
  1. WatchVideoEngine   -- Xem video FYP tu nhien, xay dung watch history
  2. EngagementEngine   -- Like, comment (AI), follow, reply
  3. VideoPostingEngine -- Upload video len Creator Center
  4. TikTokNurtureSession  -- Dieu phoi 1 phien nuoi = 1 tai khoan
  5. TikTokNurtureManager  -- Quan ly nhieu tai khoan tuan tu

Usage (standalone):
    python tiktok_nurture.py --email x@x.com --password pass --videos 10
"""

import asyncio
import json
import logging
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ---- UTF-8 Windows ----
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    import requests
    from mun_anti_browser.browser_manager import NodriverBrowserManager
    MUN_ANTI_BROWSER_AVAILABLE = True
except ImportError as e:
    print(f"[TikTokNurture] Warning import: {e}")
    MUN_ANTI_BROWSER_AVAILABLE = False
    class NodriverBrowserManager:  # type: ignore
        """Stub khi mun_anti_browser chua duoc cai dat."""
        def __init__(self, **kwargs):
            pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("TikTokNurture")


# ============================================================================
# NURTURE CONFIG
# ============================================================================

@dataclass
class NurtureConfig:
    """Cau hinh chien luoc nuoi mot tai khoan TikTok.

    Attributes:
        videos_per_session: So video xem moi phien nuoi.
        like_probability:   Xac suat tha tim video da xem.
        comment_probability: Xac suat binh luan video da xem.
        follow_probability: Xac suat follow creator.
        min_watch_seconds:  Thoi gian xem toi thieu (giay).
        max_watch_seconds:  Thoi gian xem toi da (giay).
        action_delay_mean:  Trung binh delay giua cac action (Gaussian).
        action_delay_std:   Do lech chuan delay giua cac action.
        scroll_delay_mean:  Trung binh delay khi cuon video.
        scroll_delay_std:   Do lech chuan delay cuon.
        post_videos_per_day: So video AI dang moi ngay.
        video_niche:        Niche noi dung (trending/education/entertainment).
        video_language:     Ngon ngu noi dung ("vi" hoac "en").
        proxy:              Proxy string (vi du: socks5://user:pass@host:port).
        proxy_type:         Loai proxy (socks5/http).
        headless:           An browser hay hien thi.
        c69_url:            URL he thong C69 backend.
        fallback_comments:  Comment mau khi khong co AI.
    """
    videos_per_session: int = 30
    like_probability: float = 0.70
    comment_probability: float = 0.15
    share_probability: float = 0.10
    follow_probability: float = 0.05
    min_watch_seconds: int = 8
    max_watch_seconds: int = 60
    session_minutes_min: int = 3
    session_minutes_max: int = 7
    action_delay_mean: float = 2.5
    action_delay_std: float = 0.8
    scroll_delay_mean: float = 1.5
    scroll_delay_std: float = 0.5
    post_videos_per_day: int = 2
    video_niche: str = "trending"
    video_language: str = "vi"
    proxy: str = ""
    proxy_type: str = "socks5"
    headless: bool = False
    c69_url: str = "https://c69.us"
    auto_setup_profile: bool = True
    avatar_pool_dir: str = ""
    fallback_comments: List[str] = field(default_factory=lambda: [
        "Video hay qua! 🔥",
        "Cam on ban da chia se ❤️",
        "Thu vi that! 😍",
        "Ung ho ban nha! 💪",
        "Keep it up! 🙌",
        "Love this so much! ❤️🔥",
        "Amazing content! 😮",
        "This made my day! 😊",
        "Wow, incredible! 🤩",
        "Great video! More please 🙏",
    ])
    # C69 Automation integration
    c69_username: str = ""           # Tên đăng nhập C69 backend (để auto-fetch queue)
    c69_password: str = ""           # Mật khẩu C69 backend
    c69_auto_fetch: bool = True      # Tự động lấy accounts từ C69 khi accounts=[]


# ============================================================================
# SHARED HELPERS
# ============================================================================

def _clean_cdp_val(val: Any) -> Any:
    """Chuyển đổi RemoteObject của nodriver/CDP về dict/list/primitive thuần Python."""
    if isinstance(val, dict):
        if "value" in val and len(val) <= 2:
            return _clean_cdp_val(val["value"])
        return {k: _clean_cdp_val(v) for k, v in val.items()}
    elif isinstance(val, list):
        # Format nodriver trả về cho Object: [['key', {'type': '...', 'value': '...'}], ...]
        if val and isinstance(val[0], (list, tuple)) and len(val[0]) == 2 and isinstance(val[0][0], str):
            res_dict = {}
            for item in val:
                k = item[0]
                v = item[1]
                res_dict[k] = _clean_cdp_val(v)
            return res_dict
        return [_clean_cdp_val(x) for x in val]
    return val

async def _safe_eval_json(tab: Any, js_code: str) -> Any:
    """Evaluate JavaScript và ép kiểu JSON stringify để luôn parse ra dict thuần."""
    wrapped_js = f"JSON.stringify({js_code})"
    try:
        raw_res = await tab.evaluate(wrapped_js)
        raw_str = _clean_cdp_val(raw_res)
        if isinstance(raw_str, str):
            return json.loads(raw_str)
        return _clean_cdp_val(raw_res)
    except Exception:
        # Fallback eval trực tiếp
        res = await tab.evaluate(js_code)
        return _clean_cdp_val(res)

async def _human_delay(mean: float = 2.0, std: float = 0.6, min_val: float = 0.3) -> None:
    """Delay Gaussian de mo phong hanh vi nguoi that."""
    delay = max(min_val, random.gauss(mean, std))
    await asyncio.sleep(delay)


async def _scroll(tab: Any, direction: str = "down", amount: Optional[int] = None) -> None:
    """Cuon trang ngau nhien."""
    px = amount or random.randint(300, 800)
    px = px if direction == "down" else -px
    try:
        await tab.evaluate(f"window.scrollBy(0, {px})")
    except Exception:
        pass


# ============================================================================
# AI COMMENT GENERATOR
# ============================================================================

class AICommentGenerator:
    """
    Sinh comment ngan, tu nhien bang Gemini Flash API.
    Neu khong co API key thi dung fallback ngau nhien.
    """

    def __init__(self, api_key: str = "", language: str = "vi"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.language = language
        self._available = bool(self.api_key)

    def generate_comment(self, video_topic: str = "", fallbacks: Optional[List[str]] = None) -> str:
        """Sinh comment cho video topic da cho. Fallback neu khong co API."""
        if not self._available:
            return self._fallback(fallbacks)
        try:
            import urllib.request
            lang = "Vietnamese" if self.language == "vi" else "English"
            prompt = (
                f"Generate one short, genuine, natural TikTok comment in {lang} "
                f"for a video about: '{video_topic}'. "
                "Max 12 words. Use 1-2 emojis. Just the comment text, no quotes."
            )
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.92, "maxOutputTokens": 60},
            }).encode("utf-8")
            url = (
                "https://generativelanguage.googleapis.com/v1beta/"
                f"models/gemini-1.5-flash:generateContent?key={self.api_key}"
            )
            req = urllib.request.Request(
                url, data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                return text or self._fallback(fallbacks)
        except Exception as exc:
            logger.debug(f"[AIComment] generate failed: {exc}")
            return self._fallback(fallbacks)

    @staticmethod
    def _fallback(pool: Optional[List[str]]) -> str:
        default = ["Great content! 🔥", "Love this! ❤️", "Amazing! 🤩", "So cool! 😍"]
        return random.choice(pool if pool else default)


# ============================================================================
# WATCH VIDEO ENGINE
# ============================================================================

class WatchVideoEngine:
    """
    Dieu khien TikTok For You Page de xem video tu nhien.
    - Cuon xuong load video moi
    - Mo phong thoi gian xem thuc te (Gaussian)
    - Thu thap metadata video da xem de dung cho EngagementEngine
    """

    FYP_URL = "https://www.tiktok.com/foryou?lang=en"

    def __init__(self, tab: Any, config: NurtureConfig):
        self.tab = tab
        self.config = config
        self.watched_videos: List[Dict[str, Any]] = []

    async def navigate_to_fyp(self) -> bool:
        """Dieu huong den FYP."""
        try:
            logger.info("Navigating to TikTok FYP...")
            await self.tab.get(self.FYP_URL)
            await asyncio.sleep(3)
            url = await self.tab.evaluate("window.location.href")
            return "tiktok.com" in str(url)
        except Exception as exc:
            logger.error(f"FYP navigation error: {exc}")
            return False

    async def _get_video_info(self) -> Dict[str, Any]:
        """Lay thong tin video dang hien thi."""
        try:
            info = await _safe_eval_json(self.tab, """
            (() => {
                const desc = document.querySelector('[data-e2e="browse-video-desc"]') || document.querySelector('h1');
                const author = document.querySelector('[data-e2e="browse-username"]');
                const tags = Array.from(document.querySelectorAll('a[href*="tag"]'))
                    .map(a => a.innerText).filter(t => t.startsWith('#'));
                return {
                    url: window.location.href,
                    description: desc ? desc.innerText.slice(0, 200) : '',
                    author: author ? author.innerText : '',
                    hashtags: tags.slice(0, 10)
                };
            })()
            """)
            if isinstance(info, dict):
                return info
            return {"url": "", "description": "", "author": "", "hashtags": []}
        except Exception:
            return {"url": "", "description": "", "author": "", "hashtags": []}

    async def watch_one_video(self) -> Dict[str, Any]:
        """Xem mot video trong khoang thoi gian ngau nhien."""
        info = await self._get_video_info()
        secs = random.randint(self.config.min_watch_seconds, self.config.max_watch_seconds)
        logger.info(f"Watching [{secs}s]: {info.get('description', '')[:60]}")
        elapsed = 0.0
        while elapsed < secs:
            chunk = random.uniform(1.5, 4.0)
            await asyncio.sleep(min(chunk, secs - elapsed))
            elapsed += chunk
            # Micro-scroll nho 30% thoi gian
            if random.random() < 0.3:
                try:
                    await self.tab.evaluate(f"window.scrollBy(0, {random.randint(-40, 40)})")
                except Exception:
                    pass
        info["watch_seconds"] = secs
        self.watched_videos.append(info)
        return info

    async def scroll_to_next(self) -> None:
        """Cuon sang video tiep theo."""
        await _human_delay(self.config.scroll_delay_mean, self.config.scroll_delay_std)
        try:
            await self.tab.evaluate("""
            (() => {
                const btn = document.querySelector('[data-e2e="browse-video-arrow-down"]')
                         || document.querySelector('[data-e2e="arrow-right"]');
                if (btn) { btn.click(); return; }
                document.dispatchEvent(new KeyboardEvent('keydown', {key: 'ArrowDown', bubbles: true}));
            })()
            """)
        except Exception:
            await _scroll(self.tab, "down", random.randint(600, 900))

    async def run_watch_session(self) -> List[Dict[str, Any]]:
        """Chay toan bo phien xem video. Tra ve danh sach video da xem."""
        logger.info(f"Watch session: {self.config.videos_per_session} videos")
        self.watched_videos = []
        if not await self.navigate_to_fyp():
            return []
        for i in range(self.config.videos_per_session):
            logger.info(f"Video {i+1}/{self.config.videos_per_session}")
            try:
                vid = await self.watch_one_video()
                logger.info(f"  Done: {vid.get('watch_seconds', 0)}s @{vid.get('author', '?')}")
            except Exception as exc:
                logger.warning(f"  Watch error: {exc}")
            if i < self.config.videos_per_session - 1:
                await self.scroll_to_next()
        logger.info(f"Watch done: {len(self.watched_videos)} videos")
        return self.watched_videos


# ============================================================================
# ENGAGEMENT ENGINE
# ============================================================================

class EngagementEngine:
    """
    Tuong tac voi video da xem:
    - like: theo xac suat like_probability
    - comment: theo xac suat comment_probability (AI hoac fallback)
    - follow: theo xac suat follow_probability
    - reply: reply comment tren video cua chinh account dang nuoi
    """

    def __init__(self, tab: Any, config: NurtureConfig, ai: Optional[AICommentGenerator] = None):
        self.tab = tab
        self.config = config
        self.ai = ai or AICommentGenerator(language=config.video_language)
        self.likes = 0
        self.comments = 0
        self.shares = 0
        self.follows = 0
        self.replies_sent = 0

    # ---- Internal actions ----

    async def _share(self) -> bool:
        """Thực hiện chia sẻ (copy link) video hiện tại."""
        js = """
        (() => {
            const shareBtn = document.querySelector('[data-e2e="share-icon"]')
                          || document.querySelector('[data-e2e="browse-share-icon"]')
                          || document.querySelector('button[aria-label*="Share"]')
                          || document.querySelector('button[aria-label*="Chia sẻ"]');
            if (shareBtn) {
                shareBtn.click();
                return true;
            }
            return false;
        })()
        """
        try:
            res = await self.tab.evaluate(js)
            if res:
                await asyncio.sleep(1.0)
                # Click Copy link trong popup share neu co
                await self.tab.evaluate("""
                (() => {
                    const copyBtn = document.querySelector('[data-e2e="share-copy-link"]')
                                 || Array.from(document.querySelectorAll('button, div')).find(el => (el.innerText || '').toLowerCase().includes('copy link') || (el.innerText || '').toLowerCase().includes('sao chép'));
                    if (copyBtn) copyBtn.click();
                })()
                """)
                self.shares += 1
                return True
        except Exception as exc:
            logger.debug(f"  Share error: {exc}")
        return False

    async def _like(self) -> bool:
        """Tha tim video hien tai."""
        js = """
        (() => {
            const btn = document.querySelector('[data-e2e="browse-like-icon"]')
                     || document.querySelector('button[aria-label*="Like"]');
            if (btn && btn.getAttribute('aria-pressed') !== 'true') { btn.click(); return true; }
            return false;
        })()
        """
        try:
            for sel in ('[data-e2e="browse-like-icon"]', 'button[aria-label*="Like"]'):
                el = await self.tab.select(sel, timeout=3)
                if el:
                    await el.click()
                    await _human_delay(0.8, 0.3)
                    self.likes += 1
                    return True
        except Exception:
            pass
        try:
            result = await self.tab.evaluate(js)
            if result:
                self.likes += 1
            return bool(result)
        except Exception:
            return False

    async def _comment(self, video_info: Dict[str, Any]) -> bool:
        """Binh luan tren video hien tai."""
        topic = video_info.get("description", "") or " ".join(video_info.get("hashtags", []))
        text = self.ai.generate_comment(video_topic=topic, fallbacks=self.config.fallback_comments)
        logger.info(f"  Comment: {text}")
        try:
            # Mo comment panel
            for sel in ('[data-e2e="browse-comment-icon"]', 'button[aria-label*="Comment"]'):
                el = await self.tab.select(sel, timeout=3)
                if el:
                    await el.click()
                    await asyncio.sleep(1.5)
                    break
            # Tim input
            for sel in ('[data-e2e="comment-input"]', 'div[contenteditable="true"]'):
                inp = await self.tab.select(sel, timeout=3)
                if inp:
                    await inp.click()
                    await asyncio.sleep(0.3)
                    for ch in text:
                        await inp.send_keys(ch)
                        await asyncio.sleep(random.uniform(0.03, 0.12))
                    await asyncio.sleep(0.6)
                    # Submit
                    await self.tab.evaluate("""
                    (() => {
                        const btn = document.querySelector('[data-e2e="comment-post-button"]');
                        if (btn) { btn.click(); return; }
                        document.activeElement.dispatchEvent(
                            new KeyboardEvent('keydown', {key: 'Enter', bubbles: true})
                        );
                    })()
                    """)
                    self.comments += 1
                    await _human_delay(1.5, 0.5)
                    return True
        except Exception as exc:
            logger.warning(f"  Comment error: {exc}")
        return False

    async def _follow(self) -> bool:
        """Follow creator cua video hien tai."""
        for sel in ('[data-e2e="browse-follow-button"]', 'button[aria-label*="Follow"]'):
            try:
                el = await self.tab.select(sel, timeout=3)
                if el:
                    txt = await self.tab.evaluate(f"document.querySelector('{sel}')?.innerText || ''")
                    if "Following" in str(txt):
                        return False
                    await el.click()
                    await _human_delay(1.0, 0.4)
                    self.follows += 1
                    return True
            except Exception:
                continue
        return False

    # ---- Public methods ----

    async def engage_on_watched(self, watched: List[Dict[str, Any]]) -> Dict[str, int]:
        """Tuong tac tren danh sach video da xem."""
        logger.info(f"Engaging on {len(watched)} watched videos...")
        for i, vid in enumerate(watched):
            url = vid.get("url", "")
            if not url or "tiktok.com" not in url:
                continue
            logger.info(f"Engage {i+1}/{len(watched)}: {url[:70]}")
            try:
                await self.tab.get(url)
                await asyncio.sleep(random.uniform(2.0, 4.0))

                if random.random() < self.config.like_probability:
                    ok = await self._like()
                    if ok:
                        logger.info(f"  Liked (total={self.likes})")
                    await _human_delay(self.config.action_delay_mean, self.config.action_delay_std)

                if random.random() < self.config.share_probability:
                    ok = await self._share()
                    if ok:
                        logger.info(f"  Shared/Copied (total={self.shares})")
                    await _human_delay(self.config.action_delay_mean, self.config.action_delay_std)

                if random.random() < self.config.comment_probability:
                    ok = await self._comment(vid)
                    if ok:
                        logger.info(f"  Commented (total={self.comments})")
                    await _human_delay(self.config.action_delay_mean, self.config.action_delay_std)

                if random.random() < self.config.follow_probability:
                    ok = await self._follow()
                    if ok:
                        logger.info(f"  Followed (total={self.follows})")
                    await _human_delay(self.config.action_delay_mean, self.config.action_delay_std)

            except Exception as exc:
                logger.warning(f"  Engage error: {exc}")
            await _human_delay(2.0, 0.8)

        stats = {"likes": self.likes, "comments": self.comments, "shares": self.shares, "follows": self.follows}
        logger.info(f"Engage done: {stats}")
        return stats

    async def reply_own_video_comments(self, tiktok_username: str) -> int:
        """Reply cac comment tren video cua account dang nuoi."""
        logger.info(f"Checking replies for @{tiktok_username}...")
        try:
            await self.tab.get(f"https://www.tiktok.com/@{tiktok_username}")
            await asyncio.sleep(3)
            first = await self.tab.select('[data-e2e="user-post-item"]', timeout=5)
            if not first:
                return 0
            await first.click()
            await asyncio.sleep(2)
            reply_btns = await self.tab.select_all('button[aria-label*="Reply"]')
            count = 0
            for btn in reply_btns[:3]:
                try:
                    await btn.click()
                    await asyncio.sleep(1)
                    reply_text = self.ai.generate_comment(
                        video_topic="reply to follower",
                        fallbacks=["Cam on ban! ❤️", "Thank you! 🙏", "Ung ho nha! 💪"],
                    )
                    inp = await self.tab.select('div[contenteditable="true"]', timeout=3)
                    if inp:
                        for ch in reply_text:
                            await inp.send_keys(ch)
                            await asyncio.sleep(random.uniform(0.03, 0.10))
                        await asyncio.sleep(0.5)
                        await self.tab.evaluate("""
                        (() => {
                            const b = document.querySelector('[data-e2e="comment-post-button"]');
                            if (b) b.click();
                        })()
                        """)
                        count += 1
                        logger.info(f"  Replied: {reply_text}")
                        await _human_delay(2.0, 0.8)
                except Exception as exc:
                    logger.debug(f"  Reply error: {exc}")
            self.replies_sent += count
            return count
        except Exception as exc:
            logger.warning(f"Reply check error: {exc}")
            return 0


# ============================================================================
# VIDEO POSTING ENGINE
# ============================================================================

class VideoPostingEngine:
    """
    Upload video len TikTok Creator Center.
    - Upload file video .mp4
    - Dien caption va hashtag
    - Bam Publish
    """

    UPLOAD_URL = "https://www.tiktok.com/creator-center/upload?lang=en"

    def __init__(self, tab: Any, config: NurtureConfig):
        self.tab = tab
        self.config = config

    async def upload_video(self, video_path: str, caption: str, hashtags: List[str]) -> bool:
        """
        Upload va dang video.

        Args:
            video_path: Duong dan tuyet doi den file .mp4
            caption:    Caption bai dang
            hashtags:   Danh sach hashtag (khong can #)

        Returns:
            True neu dang thanh cong.
        """
        if not os.path.exists(video_path):
            logger.error(f"Video not found: {video_path}")
            return False
        logger.info(f"Uploading: {os.path.basename(video_path)}")
        try:
            await self.tab.get(self.UPLOAD_URL)
            await asyncio.sleep(4)

            # Chon file
            file_input = await self.tab.select('input[type="file"]', timeout=10)
            if not file_input:
                logger.error("File input not found.")
                return False
            await file_input.send_file(video_path)
            logger.info("File selected, waiting upload...")
            await asyncio.sleep(20)

            # Dien caption + hashtag
            full_cap = caption
            if hashtags:
                full_cap += "\n" + " ".join(f"#{h.lstrip('#')}" for h in hashtags[:10])
            for sel in ('[data-e2e="video-desc-input"]', 'div[contenteditable="true"]'):
                try:
                    cap_el = await self.tab.select(sel, timeout=5)
                    if cap_el:
                        await cap_el.click()
                        await asyncio.sleep(0.4)
                        for ch in full_cap:
                            await cap_el.send_keys(ch)
                            await asyncio.sleep(random.uniform(0.02, 0.06))
                        break
                except Exception:
                    continue
            await asyncio.sleep(2)

            # Bam Publish
            published = await self.tab.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const btn = btns.find(b => b.innerText.includes('Post') || b.innerText.includes('Publish'));
                if (btn) { btn.click(); return true; }
                return false;
            })()
            """)
            if published:
                await asyncio.sleep(5)
                logger.info("Video published!")
                return True
            logger.error("Publish button not found.")
            return False
        except Exception as exc:
            logger.error(f"Upload error: {exc}")
            return False


# ============================================================================
# PROFILE SETUP ENGINE (Username / Nickname & Avatar Auto-Config)
# ============================================================================

class ProfileSetupEngine:
    """
    Kiem tra va thiet lap profile TikTok cho tai khoan moi:
    - Kiem tra username co phai dang mac dinh he thong random (user1234567...) hay khong -> doi nick.
    - Kiem tra avatar co phai anh mac dinh hay khong -> upload anh bat ky tu avatar_pool.
    """

    DEFAULT_NAMES = [
        "Linh Đan", "Minh Khang", "Bảo Châu", "Hoàng Nam", "Khánh Vy", "Gia Hưng",
        "Thảo Nguyên", "Tuấn Kiệt", "Mai Anh", "Hải Đăng", "Quỳnh Nga", "Đức Anh",
        "Phương Linh", "Quốc Bảo", "Thu Trang", "Nhật Minh", "Thanh Hằng", "Việt Dũng",
        "Alex Nguyen", "Sophie Tran", "Ryan Le", "Chloe Pham", "Lucas Hoang", "Mia Vu"
    ]

    def __init__(self, tab: Any, config: NurtureConfig, account: Dict[str, Any]):
        self.tab = tab
        self.config = config
        self.account = account

    async def audit_and_setup(self) -> Dict[str, Any]:
        """Kiem tra va tu dong cap nhat username / avatar neu con mac dinh."""
        logger.info("🔍 [ProfileSetup] Bắt đầu kiểm tra thông tin tài khoản...")
        res = {"username_updated": False, "avatar_updated": False, "nickname": "", "username": ""}
        try:
            # Vao trang profile ca nhan
            await self.tab.get("https://www.tiktok.com/@me")
            await asyncio.sleep(4)

            # Lay username va nickname hien tai
            profile_info = await _safe_eval_json(self.tab, """
            (() => {
                const userH1 = document.querySelector('[data-e2e="user-title"]') || document.querySelector('h1[data-e2e="user-title"]');
                const subTitle = document.querySelector('[data-e2e="user-subtitle"]');
                const avatarImg = document.querySelector('[data-e2e="user-avatar"] img') || document.querySelector('span[data-e2e="user-avatar"] img');
                return {
                    nickname: userH1 ? userH1.innerText.trim() : '',
                    username: subTitle ? subTitle.innerText.trim().replace('@', '') : '',
                    avatar_src: avatarImg ? avatarImg.src : ''
                };
            })()
            """)
            logger.info(f"  Profile hiện tại: {profile_info}")

            if not isinstance(profile_info, dict):
                profile_info = {}

            curr_user = profile_info.get("username", "") if profile_info else ""
            curr_nick = profile_info.get("nickname", "") if profile_info else ""
            avatar_src = profile_info.get("avatar_src", "") if profile_info else ""

            # 1. Kiem tra va doi Nickname / Username neu mac dinh
            is_default_user = not curr_user or curr_user.lower().startswith("user") or bool(re.match(r"^user\d{6,}", curr_user.lower()))
            if is_default_user or not curr_nick:
                logger.info("⚠️ Phát hiện tên nick hoặc username mặc định -> Bắt đầu đổi profile...")
                ok = await self._update_name_and_username()
                res["username_updated"] = ok

            # 2. Kiem tra avatar
            has_custom_avatar = avatar_src and not ("default" in avatar_src.lower() or "silhouette" in avatar_src.lower() or "avatar-default" in avatar_src.lower())
            if not has_custom_avatar:
                logger.info("⚠️ Chưa có Avatar (đang dùng avatar mặc định) -> Tự động upload avatar mới...")
                ok_ava = await self._upload_random_avatar()
                res["avatar_updated"] = ok_ava
            else:
                logger.info("✅ Tài khoản đã có Avatar cá nhân.")

        except Exception as exc:
            logger.warning(f"  [ProfileSetup] Lỗi audit profile: {exc}")

        return res

    async def _update_name_and_username(self) -> bool:
        """Mo modal edit profile va doi name/username."""
        try:
            edit_clicked = await self.tab.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"]'));
                const b = btns.find(el => (el.innerText || '').toLowerCase().includes('edit profile') || (el.innerText || '').toLowerCase().includes('sửa hồ sơ'));
                if (b) { b.click(); return true; }
                return false;
            })()
            """)
            if not edit_clicked:
                logger.info("  Không tìm thấy nút Edit profile.")
                return False

            await asyncio.sleep(2.5)

            new_name = random.choice(self.DEFAULT_NAMES)
            clean_tag = re.sub(r'[^a-zA-Z0-9_.]', '', self.account.get('email', '').split('@')[0])
            if len(clean_tag) < 3: clean_tag = f"user_{random.randint(10000, 99999)}"

            # Dien nickname
            await self.tab.evaluate(f"""
            (() => {{
                const inputs = Array.from(document.querySelectorAll('input'));
                if (inputs.length >= 1) {{
                    inputs[0].value = '{new_name}';
                    inputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            }})()
            """)
            await asyncio.sleep(1)

            # Click Save
            await self.tab.evaluate("""
            (() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const save = btns.find(b => (b.innerText || '').toLowerCase().includes('save') || (b.innerText || '').toLowerCase().includes('lưu'));
                if (save) save.click();
            })()
            """)
            await asyncio.sleep(2)
            logger.info(f"✅ Đã cập nhật Nickname mới: {new_name}")
            return True
        except Exception as e:
            logger.warning(f"  Lỗi cập nhật tên: {e}")
            return False

    async def _upload_random_avatar(self) -> bool:
        """Lay 1 anh ngau nhien tu avatar_pool de upload avatar len TikTok."""
        try:
            pool_dir = self.config.avatar_pool_dir
            if not pool_dir or not os.path.exists(pool_dir):
                base_dir = os.path.dirname(os.path.abspath(__file__))
                pool_dir = os.path.join(base_dir, "avatar_pool")

            if not os.path.exists(pool_dir):
                os.makedirs(pool_dir, exist_ok=True)

            img_files = [
                os.path.join(pool_dir, f) for f in os.listdir(pool_dir)
                if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
            ]

            if not img_files:
                logger.warning("  Không tìm thấy ảnh nào trong avatar_pool để upload.")
                return False

            chosen_avatar = random.choice(img_files)
            logger.info(f"  Chọn avatar upload: {os.path.basename(chosen_avatar)}")

            file_inp = await self.tab.select('input[type="file"][accept*="image"]', timeout=3)
            if not file_inp:
                file_inp = await self.tab.select('input[type="file"]', timeout=3)

            if file_inp:
                await file_inp.send_keys(os.path.abspath(chosen_avatar))
                await asyncio.sleep(2.5)
                await self.tab.evaluate("""
                (() => {
                    const btns = Array.from(document.querySelectorAll('button'));
                    const applyBtn = btns.find(b => (b.innerText || '').toLowerCase().includes('apply') || (b.innerText || '').toLowerCase().includes('áp dụng') || (b.innerText || '').toLowerCase().includes('save') || (b.innerText || '').toLowerCase().includes('lưu'));
                    if (applyBtn) applyBtn.click();
                })()
                """)
                await asyncio.sleep(2)
                logger.info("✅ Upload avatar ngẫu nhiên thành công!")
                return True
            else:
                logger.info("  Không tìm thấy input upload ảnh avatar.")
                return False
        except Exception as e:
            logger.warning(f"  Lỗi upload avatar: {e}")
            return False


# ============================================================================
# SESSION ORCHESTRATOR
# ============================================================================

class TikTokNurtureSession:
    """
    Dieu phoi toan bo vong lap nuoi cho 1 tai khoan:
    1. Khoi dong browser (NodriverBrowserManager)
    2. Dang nhap neu chua logged in
    3. Xem video FYP (WatchVideoEngine)
    4. Tuong tac (EngagementEngine)
    5. Reply comment tren video cua minh
    6. Dang video AI (VideoPostingEngine) neu co
    7. Ket thuc va dong browser
    """

    def __init__(
        self,
        account: Dict[str, Any],
        config: NurtureConfig,
        progress_callback=None,
    ):
        """
        Args:
            account: Dict tu C69 API chua {id, email, password, username, profile_id, ...}
            config: NurtureConfig
            progress_callback: callable(message: str, level: str) gui log real-time
        """
        self.account = account
        self.config = config
        self._cb = progress_callback or (lambda msg, lvl="info": logger.info(msg))
        self.browser_manager: Optional[Any] = None
        self.tab: Optional[Any] = None
        self._stop_flag = False

    def log(self, msg: str, level: str = "info") -> None:
        logger.info(f"[{level.upper()}] {msg}")
        self._cb(msg, level)

    def stop(self) -> None:
        """Yeu cau dung session."""
        self._stop_flag = True

    async def _start_browser(self) -> bool:
        profile_id = self.account.get("profile_id") or f"nurture_{self.account.get('id', 'default')}"
        try:
            self.log(f"Starting browser (profile={profile_id})...")
            self.browser_manager = NodriverBrowserManager()
            # Random fingerprint moi phien, nhung "id" co dinh theo tai khoan de dung chung
            # 1 thu muc user_data_dir (persist cookie/login) giua cac lan nuoi cua cung 1 account
            profile_config = self.browser_manager.profile_manager.create_random_profile(
                socks5=self.config.proxy if self.config.proxy_type == "socks5" else "",
                proxy=self.config.proxy if self.config.proxy_type != "socks5" else "",
            )
            profile_config["id"] = profile_id
            _, self.tab = await self.browser_manager.start(
                profile_config=profile_config,
                proxy_string=self.config.proxy or "",
                proxy_type=self.config.proxy_type,
                headless=self.config.headless,
                start_url="https://www.tiktok.com",
            )
            await asyncio.sleep(3)
            self.log("Browser started.", "success")
            return True
        except Exception as exc:
            self.log(f"Browser start error: {exc}", "error")
            return False

    async def _stop_browser(self) -> None:
        try:
            if self.browser_manager:
                await self.browser_manager.close()
        except Exception:
            pass

    async def _check_logged_in(self) -> bool:
        try:
            ok = await self.tab.evaluate(
                "document.cookie.includes('sid_guard') || document.cookie.includes('sessionid')"
            )
            return bool(ok)
        except Exception:
            return False

    async def _login(self) -> bool:
        """Dang nhap bang email/password, tu dong doc OTP qua OAuth2 C69 neu can."""
        if await self._check_logged_in():
            self.log("Already logged in.")
            return True
        email = self.account.get("email", "")
        password = self.account.get("password", "")
        if not email or not password:
            self.log("No credentials.", "error")
            return False
        self.log(f"Logging in: {email}")
        try:
            await self.tab.get("https://www.tiktok.com/login/phone-or-email/email?lang=en")
            await asyncio.sleep(4)

            # Điền form đăng nhập sử dụng native prototype setter để kích hoạt hoàn toàn React state
            fill_success = await self.tab.evaluate(f"""
            (() => {{
                const usernameInput = document.querySelector('input[name="username"]') || document.querySelector('input[type="text"]') || document.querySelector('input[placeholder*="Email"]');
                const passwordInput = document.querySelector('input[type="password"]');

                function setNativeValue(element, value) {{
                    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                    const prototype = Object.getPrototypeOf(element);
                    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                    if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {{
                        prototypeValueSetter.call(element, value);
                    }} else if (valueSetter) {{
                        valueSetter.call(element, value);
                    }} else {{
                        element.value = value;
                    }}
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}

                if (usernameInput && passwordInput) {{
                    usernameInput.focus();
                    setNativeValue(usernameInput, {json.dumps(email)});
                    passwordInput.focus();
                    setNativeValue(passwordInput, {json.dumps(password)});
                    return true;
                }}
                return false;
            }})()
            """)

            if not fill_success:
                # Fallback send_keys nếu evaluate không tìm thấy
                email_inp = await self.tab.select('input[name="username"], input[type="email"]', timeout=4)
                if email_inp:
                    await email_inp.click()
                    for ch in email:
                        await email_inp.send_keys(ch)
                        await asyncio.sleep(0.05)
                pw_inp = await self.tab.select('input[type="password"]', timeout=4)
                if pw_inp:
                    await pw_inp.click()
                    for ch in password:
                        await pw_inp.send_keys(ch)
                        await asyncio.sleep(0.05)

            await asyncio.sleep(1.5)

            # Click Submit button
            await self.tab.evaluate("""
            (() => {
                const btn = document.querySelector('button[type="submit"]');
                if (btn && !btn.disabled) { btn.click(); return true; }
                return false;
            })()
            """)
            await asyncio.sleep(6)

            # Kiem tra xem da vao duoc luon chua
            if await self._check_logged_in():
                self.log("Login OK (Session established)!", "success")
                return True

            # Neu TikTok yeu cau ma xac minh OTP (6-digit code)
            is_otp_page = await self.tab.evaluate("""
            (() => {
                const txt = (document.body ? document.body.innerText : '').toLowerCase();
                return txt.includes('6-digit code') || txt.includes('enter code') || txt.includes('mã 6 chữ số') || Boolean(document.querySelector('input[placeholder*="code"], input[name*="code"]'));
            })()
            """)

            if is_otp_page:
                self.log("📧 TikTok yêu cầu mã 6 số (OTP) -> Đang đọc hòm thư qua OAuth2 C69...", "warning")
                ae_id = self.account.get("accounts_emails") or self.account.get("accounts_emails_id")
                otp_code = None
                if ae_id:
                    # Polling hòm thư qua C69 Graph API trong 45s
                    headers = {"Authorization": "Token 99b02d3d255a49193950777b1cc3e3db099ceefb"}
                    c69_base = self.config.c69_url.rstrip("/")
                    for wait_idx in range(15):
                        await asyncio.sleep(3)
                        try:
                            r_mail = requests.get(f"{c69_base}/dashboard/api/emails/{ae_id}/read-mailbox/", headers=headers, timeout=10)
                            if r_mail.status_code == 200:
                                emails = r_mail.json().get("emails", [])
                                for m in emails[:5]:
                                    subj = m.get("subject", "")
                                    snip = m.get("snippet", "")
                                    # Tim ma 6 chu so trong subject hoac snippet
                                    m_code = re.search(r'\b(\d{6})\b', subj) or re.search(r'\b(\d{6})\b', snip)
                                    if m_code:
                                        otp_code = m_code.group(1)
                                        self.log(f"🔑 Lấy được mã TikTok OTP qua OAuth2: {otp_code} (Subject: {subj})", "success")
                                        break
                            if otp_code:
                                break
                        except Exception as e_poll:
                            logger.debug(f"Poll mail error: {e_poll}")

                if otp_code:
                    # Dien ma OTP vao input tren trang
                    otp_inputs = await self.tab.select_all('input[type="text"], input[inputmode="numeric"]')
                    if otp_inputs:
                        if len(otp_inputs) >= 6:
                            for idx, digit in enumerate(otp_code):
                                await otp_inputs[idx].send_keys(digit)
                                await asyncio.sleep(0.15)
                        else:
                            await otp_inputs[0].send_keys(otp_code)
                    await asyncio.sleep(4)

            if await self._check_logged_in():
                self.log("Login OK!", "success")
                return True
            self.log("Login pending or captcha challenge detected.", "warning")
            return False
        except Exception as exc:
            self.log(f"Login error: {exc}", "error")
            return False

    async def run_session(
        self,
        ai_video_path: Optional[str] = None,
        ai_video_meta: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Chay mot phien nuoi hoan chinh.

        Args:
            ai_video_path: Duong dan video AI de dang (optional)
            ai_video_meta: {caption, hashtags} cho video AI

        Returns:
            Dict ket qua {account, success, videos_watched, likes,
                          comments, follows, replies, video_posted, error}
        """
        username = self.account.get("username") or self.account.get("email", "unknown")
        self.log(f"Starting nurture session @{username}...")

        # ── Sinh kịch bản ngẫu nhiên riêng biệt cho từng nick (Per-Account Strategy) ──
        session_mins = random.uniform(self.config.session_minutes_min, self.config.session_minutes_max)
        calc_videos = max(3, int(session_mins * random.uniform(2.5, 4.5)))

        account_config = NurtureConfig(
            videos_per_session=calc_videos,
            like_probability=round(random.uniform(0.35, 0.75), 2),
            comment_probability=round(random.uniform(0.08, 0.25), 2),
            share_probability=round(random.uniform(0.05, 0.20), 2),
            follow_probability=round(random.uniform(0.02, 0.10), 2),
            min_watch_seconds=random.randint(6, 12),
            max_watch_seconds=random.randint(35, 75),
            action_delay_mean=random.uniform(2.0, 3.2),
            action_delay_std=0.8,
            scroll_delay_mean=random.uniform(1.2, 2.0),
            scroll_delay_std=0.5,
            video_niche=self.config.video_niche,
            video_language=self.config.video_language,
            proxy=self.config.proxy,
            proxy_type=self.config.proxy_type,
            headless=self.config.headless,
            c69_url=self.config.c69_url,
            auto_setup_profile=self.config.auto_setup_profile,
            avatar_pool_dir=self.config.avatar_pool_dir,
            fallback_comments=self.config.fallback_comments,
        )

        self.log(
            f"🎲 Kịch bản cá nhân hóa @{username}: "
            f"Thời gian ~{session_mins:.1f} phút, {calc_videos} videos | "
            f"Tỷ lệ: Like {int(account_config.like_probability*100)}%, "
            f"Comment {int(account_config.comment_probability*100)}%, "
            f"Share {int(account_config.share_probability*100)}%, "
            f"Follow {int(account_config.follow_probability*100)}%"
        )

        result: Dict[str, Any] = {
            "account": username,
            "success": False,
            "profile_setup": None,
            "videos_watched": 0,
            "likes": 0,
            "comments": 0,
            "shares": 0,
            "follows": 0,
            "replies": 0,
            "video_posted": False,
            "error": None,
        }

        # 1. Start browser
        if not await self._start_browser():
            result["error"] = "Browser start failed"
            return result

        try:
            # 2. Login
            if not await self._login():
                result["error"] = "Login failed"
                return result

            if self._stop_flag:
                return result

            # 3. Kiem tra va setup Nickname / Avatar neu con mac dinh
            if account_config.auto_setup_profile:
                profile_engine = ProfileSetupEngine(self.tab, account_config, self.account)
                setup_res = await profile_engine.audit_and_setup()
                result["profile_setup"] = setup_res

            if self._stop_flag:
                return result

            # 4. Watch videos theo kich ban ca nhan
            self.log(f"Watching {account_config.videos_per_session} videos...")
            watch_eng = WatchVideoEngine(self.tab, account_config)
            watched = await watch_eng.run_watch_session()
            result["videos_watched"] = len(watched)

            if self._stop_flag:
                return result

            # 5. Engage theo kich ban ca nhan
            self.log("Engaging on watched videos...")
            eng = EngagementEngine(self.tab, account_config)
            stats = await eng.engage_on_watched(watched)
            result.update(stats)

            if self._stop_flag:
                return result

            # 6. Reply own comments
            tt_user = self.account.get("tiktok_username", "")
            if tt_user:
                self.log(f"Checking own comments @{tt_user}...")
                result["replies"] = await eng.reply_own_video_comments(tt_user)

            if self._stop_flag:
                return result

            # 6. Post AI video
            if ai_video_path and os.path.exists(ai_video_path):
                self.log(f"Posting AI video: {os.path.basename(ai_video_path)}")
                poster = VideoPostingEngine(self.tab, self.config)
                caption = (ai_video_meta or {}).get("caption", "Check this out! 🔥 #fyp")
                hashtags = (ai_video_meta or {}).get("hashtags", ["trending", "viral", "fyp"])
                posted = await poster.upload_video(ai_video_path, caption, hashtags)
                result["video_posted"] = posted
                if posted:
                    self.log("AI video posted!", "success")

            result["success"] = True
            self.log(
                f"Session done! "
                f"watched={result['videos_watched']} likes={result['likes']} "
                f"shares={result['shares']} comments={result['comments']} "
                f"follows={result['follows']} replies={result['replies']}",
                "success",
            )
        except Exception as exc:
            import traceback
            traceback.print_exc()
            result["error"] = str(exc)
        finally:
            await self._stop_browser()

        return result


# ============================================================================
# MULTI-ACCOUNT MANAGER
# ============================================================================

class TikTokNurtureManager:
    """
    Quan ly viec nuoi nhieu tai khoan TikTok chay tuan tu.
    (Khong chay song song de tranh detect bot.)

    Tich hop C69 Automation:
    - Neu accounts=[] va config.c69_auto_fetch=True: tu dong lay nurture queue tu C69
    - Sau moi phien: ghi log va cookies len C69
    """

    def __init__(
        self,
        accounts: List[Dict[str, Any]],
        config: NurtureConfig,
        progress_callback=None,
    ):
        self.accounts = accounts
        self.config = config
        self._cb = progress_callback or (lambda msg, lvl: None)
        self._running = False
        self._stop_flag = False
        self._current_session: Optional[TikTokNurtureSession] = None
        # C69 client (lazy-init khi can)
        self._c69_client = None

    def _get_c69_client(self):
        """Tra ve C69Client da dang nhap, hoac None neu khong co credentials."""
        if self._c69_client is not None:
            return self._c69_client
        if not (self.config.c69_username and self.config.c69_password):
            return None
        try:
            from tiktok_reg_automation import C69Client
            client = C69Client(base_url=self.config.c69_url)
            if client.login(self.config.c69_username, self.config.c69_password):
                self._cb(f"✅ Đã đăng nhập C69 thành công ({self.config.c69_url})", "success")
                self._c69_client = client
                return client
            else:
                self._cb("⚠️ Đăng nhập C69 thất bại — sẽ chạy offline.", "warning")
        except Exception as e:
            self._cb(f"⚠️ Không thể import/kết nối C69Client: {e}", "warning")
        return None

    def stop(self) -> None:
        """Dung toan bo tien trinh."""
        self._stop_flag = True
        if self._current_session:
            self._current_session.stop()

    @property
    def is_running(self) -> bool:
        return self._running

    async def run_all(self, ai_videos: Optional[List[Dict]] = None) -> List[Dict[str, Any]]:
        """
        Nuoi tat ca tai khoan trong self.accounts.
        Neu accounts rong va c69_auto_fetch=True, se tu dong lay queue tu C69.

        Args:
            ai_videos: [{path, caption, hashtags}] — video AI can dang (optional)

        Returns:
            Danh sach ket qua session.
        """
        self._running = True
        self._stop_flag = False
        results: List[Dict[str, Any]] = []
        ai_idx = 0

        # --- Auto-fetch accounts from C69 if not provided ---
        c69 = self._get_c69_client()
        accounts = list(self.accounts)  # Tao copy de khong lam lo accounts goc

        if not accounts and self.config.c69_auto_fetch and c69:
            self._cb("📡 Không có tài khoản — đang lấy nurture queue từ C69...", "info")
            fetched = c69.get_nurture_queue(limit=20, status=0)
            if fetched:
                accounts = fetched
                self._cb(f"✅ Lấy được {len(accounts)} tài khoản từ C69 nurture queue.", "success")
            else:
                self._cb("⚠️ Không có tài khoản nào trong C69 nurture queue.", "warning")
                self._running = False
                return []
        elif not accounts:
            self._cb("❌ Danh sách tài khoản trống và không có C69 credentials.", "error")
            self._running = False
            return []

        for i, account in enumerate(accounts):
            if self._stop_flag:
                break
            username = account.get("username") or account.get("email", "?")
            self._cb(f"Account {i+1}/{len(accounts)}: @{username}", "info")

            # Video AI cho tai khoan nay
            ai_path, ai_meta = None, None
            if ai_videos and ai_idx < len(ai_videos):
                av = ai_videos[ai_idx]
                ai_path = av.get("path")
                ai_meta = {"caption": av.get("caption", ""), "hashtags": av.get("hashtags", [])}
                ai_idx += 1

            session_start = time.time()
            self._current_session = TikTokNurtureSession(account, self.config, self._cb)
            res = await self._current_session.run_session(ai_path, ai_meta)
            session_duration = int(time.time() - session_start)
            results.append(res)

            # --- Sync ket qua len C69 sau moi phien ---
            account_id = account.get("id")
            if c69 and account_id:
                # 1. Ghi log nuoi
                try:
                    stats = {
                        "videos_watched": res.get("videos_watched", 0),
                        "likes": res.get("likes", 0),
                        "comments": res.get("comments", 0),
                        "follows": res.get("follows", 0),
                        "session_duration_secs": session_duration,
                        "success": res.get("success", False),
                        "error": res.get("error", ""),
                    }
                    if c69.log_nurture_session(account_id, stats):
                        self._cb(f"📊 Đã ghi log nuôi lên C69 cho @{username}", "info")
                except Exception as log_err:
                    self._cb(f"⚠️ Lỗi ghi log C69: {log_err}", "warning")

                # 2. Luu cookies neu phien thanh cong
                if res.get("success") and res.get("cookies"):
                    try:
                        cookies_str = json.dumps(res["cookies"]) if isinstance(res["cookies"], list) else res["cookies"]
                        tiktok_handle = res.get("tiktok_username", account.get("tiktok_username", ""))
                        if c69.update_account_cookies(account_id, cookies_str, tiktok_handle):
                            self._cb(f"🍪 Đã lưu cookies mới lên C69 cho @{username}", "info")
                    except Exception as ck_err:
                        self._cb(f"⚠️ Lỗi lưu cookies C69: {ck_err}", "warning")

            # Delay giua cac tai khoan: 5-15 phut
            if i < len(accounts) - 1 and not self._stop_flag:
                delay_mins = random.uniform(5, 15)
                self._cb(f"Waiting {delay_mins:.1f} min before next account...", "info")
                for _ in range(int(delay_mins * 60)):
                    if self._stop_flag:
                        break
                    await asyncio.sleep(1)

        self._running = False
        ok = sum(1 for r in results if r.get("success"))
        self._cb(f"All done: {ok}/{len(results)} accounts succeeded.", "success")
        return results


# ============================================================================
# STANDALONE CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="TikTok Nurture — CLI Mode")
    parser.add_argument("--email", required=True, help="TikTok account email")
    parser.add_argument("--password", required=True, help="TikTok account password")
    parser.add_argument("--username", default="", help="TikTok @username (for reply check)")
    parser.add_argument("--profile-id", default="", help="Browser profile ID")
    parser.add_argument("--proxy", default="", help="Proxy (socks5://host:port)")
    parser.add_argument("--videos", type=int, default=10, help="Videos to watch per session")
    parser.add_argument("--headless", action="store_true", help="Hide browser")
    parser.add_argument("--gemini-key", default="", help="Gemini API key for AI comments")
    parser.add_argument("--video-path", default="", help="AI video path to post (optional)")
    args = parser.parse_args()

    if args.gemini_key:
        os.environ["GEMINI_API_KEY"] = args.gemini_key

    cfg = NurtureConfig(
        videos_per_session=args.videos,
        proxy=args.proxy,
        headless=args.headless,
        video_language="vi",
    )
    acc = {
        "id": 1,
        "email": args.email,
        "password": args.password,
        "username": args.username or args.email.split("@")[0],
        "tiktok_username": args.username,
        "profile_id": args.profile_id or f"nurture_{args.email.split('@')[0]}",
    }

    def on_log(msg: str, level: str = "info"):
        print(f"[{level.upper()}] {msg}")

    session = TikTokNurtureSession(acc, cfg, on_log)

    async def _main():
        ai_meta = None
        ai_path = args.video_path if args.video_path and os.path.exists(args.video_path) else None
        res = await session.run_session(ai_path, ai_meta)
        print("\n=== SESSION RESULT ===")
        print(json.dumps(res, ensure_ascii=False, indent=2))

    asyncio.run(_main())
