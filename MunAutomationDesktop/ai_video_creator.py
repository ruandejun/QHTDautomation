"""
AI Video Creator Module
========================
Tao video ngan dang TikTok tu dong bang AI:
  1. TrendFetcher    -- Lay xu huong tu TikTok/Google Trends
  2. ScriptGenerator -- AI (Gemini Flash) tao script, caption, hashtag
  3. VideoComposer   -- Ghep video tu anh stock + TTS + subtitle (MoviePy)
  4. AIVideoCreator  -- Dieu phoi toan bo pipeline

Dependencies:
  pip install moviepy requests google-cloud-texttospeech gtts

Usage:
  from ai_video_creator import AIVideoCreator, VideoCreatorConfig
  creator = AIVideoCreator(VideoCreatorConfig(gemini_api_key="AIza..."))
  result = asyncio.run(creator.create_video("trending dance challenge"))
  # -> {"path": "outputs/abc123.mp4", "caption": "...", "hashtags": [...]}
"""

import asyncio
import hashlib
import json
import logging
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---- UTF-8 ----
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("AIVideoCreator")


# ============================================================================
# CONFIG
# ============================================================================

@dataclass
class VideoCreatorConfig:
    """Cau hinh pipeline tao video AI.

    Attributes:
        gemini_api_key:  Google Gemini API key (cho script + caption generation).
        pexels_api_key:  Pexels API key (cho anh/clip stock mien phi).
        output_dir:      Thu muc luu video dau ra.
        video_width:     Chieu rong video (px). Default 1080 (doc).
        video_height:    Chieu cao video (px). Default 1920 (doc 9:16).
        video_duration:  Thoi luong video (giay). Default 30.
        tts_language:    Ngon ngu TTS ('vi' hoac 'en').
        niche:           Niche noi dung ('trending', 'education', 'entertainment').
        max_hashtags:    So hashtag toi da trong caption.
    """
    gemini_api_key: str = ""
    pexels_api_key: str = ""
    output_dir: str = ""
    video_width: int = 1080
    video_height: int = 1920
    video_duration: int = 30
    tts_language: str = "vi"
    niche: str = "trending"
    max_hashtags: int = 10

    def __post_init__(self):
        if not self.output_dir:
            self.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_videos")
        os.makedirs(self.output_dir, exist_ok=True)
        # Override tu env vars neu chua set
        if not self.gemini_api_key:
            self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        if not self.pexels_api_key:
            self.pexels_api_key = os.environ.get("PEXELS_API_KEY", "")


# ============================================================================
# TREND FETCHER
# ============================================================================

class TrendFetcher:
    """
    Lay xu huong dang hot tu nhieu nguon:
    - Google Trends (qua pytrends, neu co)
    - Danh sach trending hashtag curated theo niche
    - TikTok web scraping (qua browser, neu co tab)
    """

    # Xu huong curated theo niche (fallback khi khong co API)
    _NICHE_TRENDS: Dict[str, List[str]] = {
        "trending": [
            "viral challenge", "fyp", "trending dance", "morning routine",
            "day in my life", "life hack", "satisfying video", "transformation",
            "pov moment", "storytime",
        ],
        "education": [
            "did you know", "learn something new", "fun fact", "history explained",
            "science trick", "language learning", "study tips", "math trick",
            "psychology fact", "life lesson",
        ],
        "entertainment": [
            "funny moments", "comedy skit", "try not to laugh", "reaction video",
            "meme compilation", "celebrity news", "gaming highlight", "anime moment",
            "sports clip", "cooking fail",
        ],
        "lifestyle": [
            "morning routine", "healthy recipe", "workout tips", "self care",
            "aesthetic room", "fashion haul", "travel vlog", "solo travel",
            "minimalism", "glow up",
        ],
        "review": [
            "product review", "unboxing", "honest review", "worth it or not",
            "amazon finds", "aliexpress haul", "tech review", "food review",
            "app review", "book review",
        ],
    }

    def __init__(self, niche: str = "trending"):
        self.niche = niche

    def get_trending_topics(self, count: int = 5) -> List[str]:
        """
        Lay danh sach chu de dang trending.
        Uu tien Google Trends (neu pytrends available),
        fallback ve danh sach curated.
        """
        # Thu dung Google Trends
        try:
            from pytrends.request import TrendReq
            pytrends = TrendReq(hl="vi-VN", tz=420, timeout=(10, 25))
            pytrends.build_payload(kw_list=["tiktok", "viral", "trending"], timeframe="now 1-d")
            related = pytrends.related_queries()
            topics = []
            for kw in related:
                top = related[kw].get("top")
                if top is not None:
                    topics.extend(top["query"].head(3).tolist())
            if topics:
                selected = random.sample(topics, min(count, len(topics)))
                logger.info(f"[TrendFetcher] Google Trends: {selected}")
                return selected
        except Exception as exc:
            logger.debug(f"[TrendFetcher] Google Trends unavailable: {exc}")

        # Fallback: curated list
        pool = self._NICHE_TRENDS.get(self.niche, self._NICHE_TRENDS["trending"])
        selected = random.sample(pool, min(count, len(pool)))
        logger.info(f"[TrendFetcher] Curated trends: {selected}")
        return selected


# ============================================================================
# SCRIPT GENERATOR
# ============================================================================

class ScriptGenerator:
    """
    Dung Gemini Flash API de tao:
    - Script/voiceover text
    - Caption bai dang
    - Hashtags phu hop

    Fallback ve template co san neu khong co API.
    """

    def __init__(self, api_key: str = "", language: str = "vi"):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.language = language
        self._available = bool(self.api_key)

    def generate(self, topic: str) -> Dict[str, Any]:
        """
        Tao noi dung cho video ve chu de da cho.

        Returns:
            {
                "topic": str,
                "script": str,       # Voiceover text (30-60 words)
                "caption": str,      # Caption bai dang TikTok
                "hashtags": List[str],
                "video_style": str,  # "slideshow"|"talking_head"|"text_animation"
                "keywords": List[str]  # Tu khoa de tim anh stock
            }
        """
        if not self._available:
            return self._fallback_content(topic)

        try:
            import urllib.request
            lang = "Vietnamese" if self.language == "vi" else "English"
            prompt = f"""
You are a viral TikTok content creator. Generate content for a TikTok short video about: "{topic}".

Respond with ONLY a valid JSON object (no markdown, no explanation):
{{
  "script": "<voiceover text, 40-80 words, engaging and conversational in {lang}>",
  "caption": "<TikTok caption, 1-2 sentences in {lang}, hook at start>",
  "hashtags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "video_style": "slideshow",
  "keywords": ["keyword1", "keyword2", "keyword3"]
}}

Rules:
- script: natural spoken language, include a hook in first 5 words
- caption: start with question or bold statement, max 150 chars
- hashtags: mix of trending (#fyp #viral) and niche-specific, no # prefix
- keywords: English noun phrases for stock image search
- video_style: always "slideshow" for now
"""
            payload = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.85, "maxOutputTokens": 400},
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
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
                raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                # Clean markdown code blocks neu co
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                content = json.loads(raw_text.strip())
                content["topic"] = topic
                logger.info(f"[ScriptGen] Generated for: {topic}")
                logger.info(f"  caption: {content.get('caption', '')[:80]}")
                return content
        except Exception as exc:
            logger.warning(f"[ScriptGen] Gemini failed: {exc}")
            return self._fallback_content(topic)

    @staticmethod
    def _fallback_content(topic: str) -> Dict[str, Any]:
        """Tra ve noi dung mau khi Gemini khong kha dung."""
        return {
            "topic": topic,
            "script": (
                f"Ban co biet dieu thu vi ve {topic} khong? "
                "Hay xem video nay de kham pha nhung dieu bat ngo! "
                "Dung quen like va follow de xem them nhieu noi dung hay nha!"
            ),
            "caption": f"Kham pha {topic} cung minh! 🔥 Ban se ngac nhien day!",
            "hashtags": ["fyp", "viral", "trending", "tiktok", topic.replace(" ", "")],
            "video_style": "slideshow",
            "keywords": [topic, "exciting", "trending"],
        }


# ============================================================================
# STOCK MEDIA FETCHER
# ============================================================================

class StockMediaFetcher:
    """
    Lay anh va clip mien phi tu Pexels API.
    Fallback: tao anh gradient bang Pillow.
    """

    PEXELS_API = "https://api.pexels.com/v1/search"

    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("PEXELS_API_KEY", "")

    def fetch_images(self, keyword: str, count: int = 5, save_dir: str = "") -> List[str]:
        """
        Tai anh stock tu Pexels theo tu khoa.

        Returns:
            Danh sach duong dan den cac anh da tai.
        """
        if not self.api_key:
            logger.info("[StockMedia] No Pexels key, using gradient fallback")
            return self._generate_gradient_images(keyword, count, save_dir)

        paths = []
        try:
            import urllib.request
            url = f"{self.PEXELS_API}?query={urllib.request.quote(keyword)}&per_page={count}&orientation=portrait"
            req = urllib.request.Request(url, headers={"Authorization": self.api_key})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            photos = data.get("photos", [])
            for i, photo in enumerate(photos[:count]):
                img_url = photo.get("src", {}).get("portrait") or photo.get("src", {}).get("medium", "")
                if not img_url:
                    continue
                fname = os.path.join(save_dir, f"stock_{i}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}.jpg")
                if not os.path.exists(fname):
                    with urllib.request.urlopen(img_url, timeout=30) as r:
                        with open(fname, "wb") as f:
                            f.write(r.read())
                paths.append(fname)
                logger.info(f"  Downloaded: {fname}")
        except Exception as exc:
            logger.warning(f"[StockMedia] Pexels error: {exc}")
            return self._generate_gradient_images(keyword, count, save_dir)
        return paths

    @staticmethod
    def _generate_gradient_images(keyword: str, count: int, save_dir: str) -> List[str]:
        """Tao anh gradient mau don gian neu khong co Pexels."""
        paths = []
        try:
            from PIL import Image, ImageDraw, ImageFont
            color_pairs = [
                ("#667eea", "#764ba2"),
                ("#f093fb", "#f5576c"),
                ("#4facfe", "#00f2fe"),
                ("#43e97b", "#38f9d7"),
                ("#fa709a", "#fee140"),
                ("#a18cd1", "#fbc2eb"),
            ]
            for i in range(count):
                c1, c2 = color_pairs[i % len(color_pairs)]
                img = Image.new("RGB", (1080, 1920))
                draw = ImageDraw.Draw(img)
                # Gradient don gian
                for y in range(1920):
                    t = y / 1920
                    r = int(int(c1[1:3], 16) * (1 - t) + int(c2[1:3], 16) * t)
                    g = int(int(c1[3:5], 16) * (1 - t) + int(c2[3:5], 16) * t)
                    b = int(int(c1[5:7], 16) * (1 - t) + int(c2[5:7], 16) * t)
                    draw.line([(0, y), (1080, y)], fill=(r, g, b))
                # Ve text o giua
                try:
                    font = ImageFont.truetype("arial.ttf", 60)
                except Exception:
                    font = ImageFont.load_default()
                text = keyword.upper()
                bbox = draw.textbbox((0, 0), text, font=font)
                x = (1080 - (bbox[2] - bbox[0])) // 2
                y = (1920 - (bbox[3] - bbox[1])) // 2
                draw.text((x, y), text, fill="white", font=font)

                fname = os.path.join(save_dir, f"gradient_{i}_{abs(hash(keyword + str(i)))}.jpg")
                img.save(fname, "JPEG", quality=90)
                paths.append(fname)
        except Exception as exc:
            logger.warning(f"[StockMedia] Gradient generation failed: {exc}")
        return paths


# ============================================================================
# TTS ENGINE
# ============================================================================

class TTSEngine:
    """
    Text-to-Speech cho script video.
    Uu tien gTTS (Google TTS mien phi), fallback ve silent audio.
    """

    def __init__(self, language: str = "vi"):
        self.language = language

    def synthesize(self, text: str, output_path: str) -> bool:
        """
        Chuyen text thanh file audio MP3.

        Returns:
            True neu thanh cong.
        """
        # Thu gTTS
        try:
            from gtts import gTTS
            tts = gTTS(text=text, lang=self.language, slow=False)
            tts.save(output_path)
            logger.info(f"[TTS] gTTS OK: {output_path}")
            return True
        except Exception as exc:
            logger.warning(f"[TTS] gTTS failed: {exc}")

        # Thu pyttsx3 (offline)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty("rate", 160)
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                logger.info(f"[TTS] pyttsx3 OK: {output_path}")
                return True
        except Exception as exc:
            logger.debug(f"[TTS] pyttsx3 failed: {exc}")

        # Fallback: tao file am thanh trong bang ffmpeg
        try:
            import subprocess
            subprocess.run(
                ["ffmpeg", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                 "-t", "30", "-q:a", "9", "-acodec", "libmp3lame", output_path, "-y"],
                capture_output=True, check=True,
            )
            logger.warning(f"[TTS] Using silent audio fallback: {output_path}")
            return True
        except Exception:
            pass

        return False


# ============================================================================
# VIDEO COMPOSER
# ============================================================================

class VideoComposer:
    """
    Ghep video tu:
    - Anh stock (slideshow)
    - Audio TTS
    - Subtitle text (MoviePy TextClip)

    Output: file .mp4 doc 9:16, 30 giay.
    """

    def __init__(self, config: VideoCreatorConfig):
        self.config = config

    def compose(
        self,
        image_paths: List[str],
        audio_path: str,
        script_text: str,
        output_path: str,
    ) -> bool:
        """
        Ghep video slideshow tu anh + audio + subtitle.

        Args:
            image_paths: Danh sach duong dan anh stock
            audio_path:  Duong dan file audio TTS
            script_text: Text hien thi subtitle
            output_path: Duong dan luu video dau ra

        Returns:
            True neu thanh cong.
        """
        if not image_paths:
            logger.error("[VideoComposer] No images to compose.")
            return False

        try:
            from moviepy.editor import (
                ImageClip, concatenate_videoclips, AudioFileClip,
                TextClip, CompositeVideoClip
            )
            import numpy as np

            w, h = self.config.video_width, self.config.video_height
            total_dur = float(self.config.video_duration)
            dur_per_img = total_dur / len(image_paths)

            clips = []
            for img_path in image_paths:
                clip = ImageClip(img_path, duration=dur_per_img)
                # Resize/crop de fill 9:16
                clip = clip.resize(height=h)
                if clip.w < w:
                    clip = clip.resize(width=w)
                # Center crop
                x_center = clip.w / 2
                y_center = clip.h / 2
                clip = clip.crop(
                    x1=x_center - w/2, y1=y_center - h/2,
                    x2=x_center + w/2, y2=y_center + h/2,
                )
                # Ken zoom effect nhe
                clip = clip.resize(lambda t: 1 + 0.02 * t / dur_per_img)
                clips.append(clip)

            video = concatenate_videoclips(clips, method="compose")

            # Them audio TTS
            if os.path.exists(audio_path) and os.path.getsize(audio_path) > 0:
                try:
                    audio = AudioFileClip(audio_path)
                    if audio.duration > total_dur:
                        audio = audio.subclip(0, total_dur)
                    video = video.set_audio(audio)
                except Exception as exc:
                    logger.warning(f"[VideoComposer] Audio attach failed: {exc}")

            # Subtitle (phan tich script thanh tung doan)
            sentences = [s.strip() for s in script_text.replace("!", "!|").replace("?", "?|").split("|") if s.strip()]
            if sentences:
                sub_dur = total_dur / len(sentences)
                subtitles = []
                for i, sent in enumerate(sentences):
                    try:
                        txt_clip = (
                            TextClip(
                                sent, fontsize=52, color="white",
                                stroke_color="black", stroke_width=2,
                                size=(w - 80, None), method="caption",
                                align="center",
                            )
                            .set_start(i * sub_dur)
                            .set_duration(sub_dur)
                            .set_position(("center", h * 0.75))
                        )
                        subtitles.append(txt_clip)
                    except Exception:
                        pass  # TextClip co the loi neu thieu ImageMagick
                if subtitles:
                    video = CompositeVideoClip([video] + subtitles)

            # Xuat file
            video.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                threads=2,
                logger=None,
                preset="ultrafast",
            )
            logger.info(f"[VideoComposer] Video saved: {output_path}")
            return True

        except ImportError:
            logger.error("[VideoComposer] moviepy not installed. Run: pip install moviepy")
            return self._compose_with_ffmpeg(image_paths, audio_path, output_path)
        except Exception as exc:
            logger.error(f"[VideoComposer] Compose error: {exc}")
            return self._compose_with_ffmpeg(image_paths, audio_path, output_path)

    def _compose_with_ffmpeg(
        self, image_paths: List[str], audio_path: str, output_path: str
    ) -> bool:
        """Fallback: dung ffmpeg CLI de tao video slideshow."""
        try:
            import subprocess
            import tempfile

            w, h = self.config.video_width, self.config.video_height
            dur_per = self.config.video_duration / max(len(image_paths), 1)

            # Tao file list cho ffmpeg concat
            list_file = os.path.join(tempfile.gettempdir(), "ffmpeg_img_list.txt")
            with open(list_file, "w") as f:
                for img in image_paths:
                    f.write(f"file '{img}'\n")
                    f.write(f"duration {dur_per:.2f}\n")
                # Lap lai anh cuoi (ffmpeg requirement)
                if image_paths:
                    f.write(f"file '{image_paths[-1]}'\n")

            cmd = [
                "ffmpeg", "-y",
                "-f", "concat", "-safe", "0", "-i", list_file,
                "-vf", f"scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h},fps=30",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "28",
                "-t", str(self.config.video_duration),
            ]
            if os.path.exists(audio_path):
                cmd += ["-i", audio_path, "-c:a", "aac", "-shortest"]
            cmd.append(output_path)

            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"[VideoComposer] ffmpeg video: {output_path}")
            return True
        except Exception as exc:
            logger.error(f"[VideoComposer] ffmpeg fallback failed: {exc}")
            return False


# ============================================================================
# AI VIDEO CREATOR — ORCHESTRATOR
# ============================================================================

class AIVideoCreator:
    """
    Pipeline tao video TikTok hoan chinh:
    TrendFetcher → ScriptGenerator → StockMediaFetcher → TTSEngine → VideoComposer

    Usage:
        creator = AIVideoCreator(VideoCreatorConfig(gemini_api_key="..."))
        result = asyncio.run(creator.create_video("morning routine"))
    """

    def __init__(self, config: VideoCreatorConfig):
        self.config = config
        self.trend_fetcher = TrendFetcher(niche=config.niche)
        self.script_gen = ScriptGenerator(api_key=config.gemini_api_key, language=config.tts_language)
        self.media_fetcher = StockMediaFetcher(api_key=config.pexels_api_key)
        self.tts = TTSEngine(language=config.tts_language)
        self.composer = VideoComposer(config)

    async def create_video(self, topic: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Tao mot video hoan chinh.

        Args:
            topic: Chu de video (neu None thi tu dong lay tu TrendFetcher)

        Returns:
            {path, caption, hashtags, topic, script} hoac None neu that bai.
        """
        # 1. Lay chu de neu chua co
        if not topic:
            topics = self.trend_fetcher.get_trending_topics(count=3)
            topic = random.choice(topics) if topics else "viral trending"
        logger.info(f"[AICreator] Creating video: '{topic}'")

        # 2. Tao script, caption, hashtag
        logger.info("[AICreator] Generating script...")
        content = await asyncio.get_event_loop().run_in_executor(
            None, self.script_gen.generate, topic
        )
        script = content.get("script", "")
        caption = content.get("caption", f"Check this out! #{topic.replace(' ', '')} #fyp")
        hashtags = content.get("hashtags", ["fyp", "viral", "trending"])[:self.config.max_hashtags]
        keywords = content.get("keywords", [topic])

        # 3. Tao thu muc tam
        vid_id = hashlib.md5(f"{topic}{time.time()}".encode()).hexdigest()[:10]
        tmp_dir = os.path.join(self.config.output_dir, f"tmp_{vid_id}")
        os.makedirs(tmp_dir, exist_ok=True)

        # 4. Tai anh stock
        logger.info(f"[AICreator] Fetching stock images for: {keywords}")
        kw = " ".join(keywords[:2])
        image_paths = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.media_fetcher.fetch_images(kw, count=5, save_dir=tmp_dir)
        )
        if not image_paths:
            logger.error("[AICreator] No stock images available.")
            return None

        # 5. TTS
        logger.info("[AICreator] Synthesizing voiceover...")
        audio_path = os.path.join(tmp_dir, "voiceover.mp3")
        audio_ok = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.tts.synthesize(script, audio_path)
        )
        if not audio_ok:
            logger.warning("[AICreator] TTS failed, video will be silent.")
            audio_path = ""

        # 6. Ghep video
        logger.info("[AICreator] Composing video...")
        output_path = os.path.join(self.config.output_dir, f"ai_video_{vid_id}.mp4")
        composed = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self.composer.compose(image_paths, audio_path, script, output_path)
        )
        if not composed:
            logger.error("[AICreator] Video composition failed.")
            return None

        # 7. Don dep tmp
        try:
            import shutil
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass

        result = {
            "path": output_path,
            "caption": caption,
            "hashtags": hashtags,
            "topic": topic,
            "script": script,
        }
        logger.info(f"[AICreator] Done! Video: {output_path}")
        return result

    async def create_batch(self, topics: Optional[List[str]] = None, count: int = 3) -> List[Dict[str, Any]]:
        """
        Tao nhieu video mot luc.

        Args:
            topics: Danh sach chu de (neu None thi lay tu TrendFetcher)
            count:  So video can tao

        Returns:
            Danh sach ket qua.
        """
        if not topics:
            topics = self.trend_fetcher.get_trending_topics(count=count)
        results = []
        for topic in topics[:count]:
            result = await self.create_video(topic)
            if result:
                results.append(result)
            await asyncio.sleep(2)  # Rate limiting giua cac API call
        return results


# ============================================================================
# STANDALONE CLI
# ============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AI TikTok Video Creator")
    parser.add_argument("--topic", default="", help="Video topic (auto from trends if empty)")
    parser.add_argument("--count", type=int, default=1, help="Number of videos to create")
    parser.add_argument("--niche", default="trending", help="Content niche")
    parser.add_argument("--language", default="vi", help="TTS language (vi/en)")
    parser.add_argument("--duration", type=int, default=30, help="Video duration (seconds)")
    parser.add_argument("--output-dir", default="", help="Output directory")
    parser.add_argument("--gemini-key", default="", help="Gemini API key")
    parser.add_argument("--pexels-key", default="", help="Pexels API key")
    args = parser.parse_args()

    config = VideoCreatorConfig(
        gemini_api_key=args.gemini_key or os.environ.get("GEMINI_API_KEY", ""),
        pexels_api_key=args.pexels_key or os.environ.get("PEXELS_API_KEY", ""),
        output_dir=args.output_dir,
        niche=args.niche,
        tts_language=args.language,
        video_duration=args.duration,
    )

    creator = AIVideoCreator(config)

    async def _main():
        if args.count == 1:
            result = await creator.create_video(args.topic or None)
            if result:
                print("\n=== VIDEO CREATED ===")
                print(json.dumps(result, ensure_ascii=False, indent=2))
            else:
                print("ERROR: Video creation failed.")
                sys.exit(1)
        else:
            topics = [args.topic] if args.topic else None
            results = await creator.create_batch(topics, count=args.count)
            print(f"\n=== {len(results)} VIDEOS CREATED ===")
            for r in results:
                print(f"  {r['path']} | {r['topic']}")

    asyncio.run(_main())
