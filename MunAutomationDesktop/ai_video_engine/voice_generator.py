"""
High-Fidelity AI Voiceover Generator using Edge-TTS
Generates native US voiceover (Christopher / Jenny) and subtitle timings.
"""
import asyncio
import os
import edge_tts
from typing import Dict, Optional

# Top Rated US Voices in Edge-TTS
VOICE_MALE_US = "en-US-ChristopherNeural"      # Deep, authoritative, engaging
VOICE_FEMALE_US = "en-US-JennyNeural"          # Warm, natural, dynamic
VOICE_FAST_PACE = "en-US-GuyNeural"            # Energetic, viral style

class VoiceGenerator:
    def __init__(self, voice: str = VOICE_MALE_US, rate: str = "+5%"):
        self.voice = voice
        self.rate = rate

    async def generate_audio_async(self, text: str, output_audio_path: str, output_vtt_path: Optional[str] = None) -> Dict:
        """Asynchronously generate audio file and optional VTT subtitle file"""
        communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
        
        submaker = edge_tts.SubMaker()
        with open(output_audio_path, "wb") as file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)

        vtt_content = submaker.get_srt()
        if output_vtt_path and vtt_content:
            with open(output_vtt_path, "w", encoding="utf-8") as f:
                f.write(vtt_content)

        return {
            "audio_path": output_audio_path,
            "vtt_path": output_vtt_path,
            "voice": self.voice
        }

    def generate_audio(self, text: str, output_audio_path: str, output_vtt_path: Optional[str] = None) -> Dict:
        """Synchronous wrapper for generating audio"""
        os.makedirs(os.path.dirname(os.path.abspath(output_audio_path)), exist_ok=True)
        return asyncio.run(self.generate_audio_async(text, output_audio_path, output_vtt_path))

if __name__ == "__main__":
    vg = VoiceGenerator()
    out_mp3 = "test_voice.mp3"
    out_srt = "test_sub.srt"
    res = vg.generate_audio("Stop scrolling right now. Here is three secret AI tools you must know.", out_mp3, out_srt)
    print("Voice Generated:", res)
