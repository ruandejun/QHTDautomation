"""
Master AI Short Video Generator Pipeline
One-click autonomous flow: US Trends -> Script -> Voiceover -> 9:16 Video Rendering -> Metadata JSON.
"""
import os
import json
import time
from typing import Dict, Optional

from .us_trend_scraper import USTrendScraper
from .script_generator import ScriptGenerator
from .voice_generator import VoiceGenerator, VOICE_MALE_US, VOICE_FEMALE_US
from .video_composer import VideoComposer

OUTPUT_DIR = r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\rendered_videos"

class AIVideoPipeline:
    def __init__(self, output_dir: str = OUTPUT_DIR):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.trend_scraper = USTrendScraper()
        self.script_gen = ScriptGenerator()
        self.voice_gen = VoiceGenerator(voice=VOICE_MALE_US)
        self.composer = VideoComposer()

    def generate_viral_video(self, niche: Optional[str] = None, female_voice: bool = False) -> Dict:
        """
        Executes end-to-end pipeline:
        1. Trend Scraping
        2. Script Generation
        3. Voice Synthesis
        4. Video Composite Rendering
        """
        timestamp = int(time.time())
        if female_voice:
            self.voice_gen.voice = VOICE_FEMALE_US

        # Step 1: Pick US Trend
        trend_info = self.trend_scraper.get_trend_for_video(niche)
        niche_key = trend_info["niche"]
        topic = trend_info["topic"]
        hashtags = trend_info["hashtags"]

        # Step 2: Generate Script
        script_data = self.script_gen.generate_script(niche_key, topic)
        full_text = script_data["full_text"]
        hook = script_data["hook"]

        # Step 3: Generate Voiceover & Subtitles
        audio_filename = f"audio_{niche_key}_{timestamp}.mp3"
        srt_filename = f"sub_{niche_key}_{timestamp}.srt"
        audio_path = os.path.join(self.output_dir, audio_filename)
        srt_path = os.path.join(self.output_dir, srt_filename)

        voice_res = self.voice_gen.generate_audio(full_text, audio_path, srt_path)

        # Step 4: Composite 9:16 Video
        video_filename = f"tiktok_{niche_key}_{timestamp}.mp4"
        video_path = os.path.join(self.output_dir, video_filename)

        self.composer.render_short_video(
            audio_path=audio_path,
            output_video_path=video_path,
            title_text=trend_info["niche_name"].upper(),
            hook_text=hook
        )

        # Step 5: Build TikTok Upload Metadata
        caption = f"{hook}\n\n{' '.join(hashtags)}"
        metadata = {
            "video_path": video_path,
            "audio_path": audio_path,
            "title": topic,
            "caption": caption,
            "hashtags": hashtags,
            "niche": niche_key,
            "timestamp": timestamp,
            "duration": self.composer.get_audio_duration(audio_path)
        }

        meta_path = os.path.join(self.output_dir, f"meta_{niche_key}_{timestamp}.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        metadata["meta_path"] = meta_path
        return metadata

if __name__ == "__main__":
    pipeline = AIVideoPipeline()
    print("Starting sample video generation...")
    res = pipeline.generate_viral_video("ai_tech")
    print("\n[SUCCESS] Successfully rendered short video!")
    print("Video Path:", res["video_path"])
    print("Caption:\n", res["caption"])
