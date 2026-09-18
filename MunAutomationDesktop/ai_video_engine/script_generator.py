"""
AI Script Generator for TikTok Short Videos (US Audience)
Generates high-retention viral scripts following the Hook -> Value Body -> CTA structure.
"""
import os
import random
from typing import Dict, List

# High-Retention Script Templates for fast generation without external API dependency
SCRIPT_TEMPLATES = {
    "life_hacks": [
        {
            "hook": "Stop doing this if you want people to respect you immediately.",
            "body": "Number one: Never speak over someone, even if they interrupt you. Silence makes you look in total control. Number two: Maintain eye contact for two seconds after someone finishes talking. It shows confidence without being aggressive. And number three: Never complain about things you can change.",
            "cta": "Save this video for later and follow for daily life hacks."
        },
        {
            "hook": "Here is a military sleep technique that knocks you out in two minutes.",
            "body": "Start by relaxing all the muscles in your face, including your tongue and jaw. Next, drop your shoulders as low as they can go and let your hands go limp. Exhale completely, and clear your mind by visualizing a calm, pitch-black lake. If any thought enters, repeat the words: don't think, for ten seconds.",
            "cta": "Try this tonight and follow for more productivity secrets."
        }
    ],
    "ai_tech": [
        {
            "hook": "Three free AI websites that feel completely illegal to know.",
            "body": "First is Gamma app. It generates entire professional presentations and documents from a single text prompt in thirty seconds. Second is Scribe. It records your screen and automatically writes step-by-step guides with screenshots. And third is ElevenLabs, which generates ultra-realistic human voices that sound one hundred percent real.",
            "cta": "Which one was your favorite? Comment below and follow for more AI secrets."
        },
        {
            "hook": "Stop using ChatGPT like a beginner. Use this prompt formula instead.",
            "body": "Most people write vague questions and get terrible answers. Instead, always use this three-step formula: Role, Context, and Output format. Tell the AI who it is, give it the exact background details, and specify the exact style and length you need.",
            "cta": "Double tap if this helped you, and follow for more daily tech hacks."
        }
    ],
    "fitness_health": [
        {
            "hook": "The number one morning habit that doubles your metabolism naturally.",
            "body": "Drink sixteen ounces of cold water with a pinch of Himalayan salt the moment you wake up. This instantly rehydrates your brain cells, kickstarts your digestive enzymes, and prevents false hunger cravings throughout the entire morning.",
            "cta": "Start doing this tomorrow morning and follow for daily fitness tips."
        }
    ],
    "motivation_wealth": [
        {
            "hook": "The brutal truth about money that ninety-nine percent of people learn too late.",
            "body": "You don't get rich by working harder at a job that pays by the hour. You get rich by owning assets that work for you while you sleep. Stop trading your limited time for depreciating currency, and start building digital systems that scale.",
            "cta": "Save this to remind yourself every morning, and follow for wealth mindset."
        }
    ]
}

class ScriptGenerator:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")

    def generate_script(self, niche: str, topic: str) -> Dict[str, str]:
        """Generate high-retention 30-second script for TikTok"""
        # Pick best template for niche or fallback
        templates = SCRIPT_TEMPLATES.get(niche, SCRIPT_TEMPLATES["life_hacks"])
        selected = random.choice(templates)
        
        full_text = f"{selected['hook']} {selected['body']} {selected['cta']}"
        
        return {
            "niche": niche,
            "topic": topic,
            "hook": selected["hook"],
            "body": selected["body"],
            "cta": selected["cta"],
            "full_text": full_text
        }

if __name__ == "__main__":
    gen = ScriptGenerator()
    script = gen.generate_script("ai_tech", "AI Tools")
    print("Generated Script:\n", script["full_text"])
