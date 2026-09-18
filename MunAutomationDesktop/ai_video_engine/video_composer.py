"""
High-Performance TikTok Video Composer using FFmpeg
Renders vertical 9:16 short videos with voiceover, background visual, and styled captions.
"""
import os
import subprocess
import shutil
from typing import Dict, Optional

FFMPEG_PATH = r"D:\Workspace\Python\MunLogin\ffmpeg.exe"

class VideoComposer:
    def __init__(self, ffmpeg_bin: str = FFMPEG_PATH):
        self.ffmpeg = ffmpeg_bin if os.path.exists(ffmpeg_bin) else shutil.which("ffmpeg")
        if not self.ffmpeg:
            raise FileNotFoundError(f"FFmpeg binary not found at {ffmpeg_bin} or in PATH")

    def get_audio_duration(self, audio_path: str) -> float:
        """Get precise duration of audio in seconds using ffmpeg"""
        try:
            cmd = [
                self.ffmpeg, "-i", audio_path, "-f", "null", "-"
            ]
            res = subprocess.run(cmd, stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
            for line in res.stderr.split("\n"):
                if "Duration:" in line:
                    time_str = line.split("Duration:")[1].split(",")[0].strip()
                    parts = time_str.split(":")
                    return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        except Exception:
            pass
        return 30.0

    def render_short_video(
        self,
        audio_path: str,
        output_video_path: str,
        title_text: str = "MUST WATCH",
        hook_text: str = "",
        bg_video_path: Optional[str] = None
    ) -> str:
        """
        Renders a 9:16 TikTok ready MP4 video (1080x1920 or 720x1280)
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
        duration = self.get_audio_duration(audio_path)
        
        # Clean and escape title / hook for FFmpeg drawtext
        clean_title = title_text.replace("'", "").replace(":", " -")
        clean_hook = hook_text.replace("'", "").replace(":", " -")[:60]
        if len(hook_text) > 60:
            clean_hook += "..."

        # If background video is not provided or missing, generate a dynamic dark gradient background
        if bg_video_path and os.path.exists(bg_video_path):
            video_input = ["-stream_loop", "-1", "-i", bg_video_path]
            filter_chain = (
                f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
                f"boxblur=1:1,"
                f"drawbox=y=0:color=black@0.4:width=iw:height=ih:t=fill,"
                f"drawtext=text='{clean_title}':fontcolor=yellow:fontsize=52:x=(w-text_w)/2:y=320:borderw=4:bordercolor=black,"
                f"drawtext=text='{clean_hook}':fontcolor=white:fontsize=44:x=(w-text_w)/2:y=420:borderw=3:bordercolor=black[v]"
            )
        else:
            # Generate animated gradient aesthetic background via color filter
            video_input = [
                "-f", "lavfi",
                "-i", f"color=c=0x111625:s=1080x1920:d={duration+0.5}:r=30"
            ]
            filter_chain = (
                f"[0:v]drawbox=y=250:color=0x1e293b@0.85:width=980:height=300:x=50:t=fill,"
                f"drawbox=y=250:color=0x38bdf8:width=980:height=300:x=50:t=4,"
                f"drawtext=text='{clean_title}':fontcolor=0xfacc15:fontsize=56:x=(w-text_w)/2:y=310:borderw=4:bordercolor=black,"
                f"drawtext=text='{clean_hook}':fontcolor=white:fontsize=42:x=(w-text_w)/2:y=410:borderw=3:bordercolor=black[v]"
            )

        cmd = [
            self.ffmpeg, "-y",
            *video_input,
            "-i", audio_path,
            "-filter_complex", filter_chain,
            "-map", "[v]",
            "-map", "1:a",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "128k",
            "-t", str(duration + 0.3),
            "-pix_fmt", "yuv420p",
            output_video_path
        ]

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg rendering failed: {res.stderr[-300:]}")

        return output_video_path

if __name__ == "__main__":
    composer = VideoComposer()
    print("VideoComposer initialized with:", composer.ffmpeg)
