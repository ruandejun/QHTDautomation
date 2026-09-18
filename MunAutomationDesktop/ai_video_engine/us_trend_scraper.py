"""
US Trend Scraper & Niche Analyzer for TikTok Phone Farm
Collects trending US hashtags, viral topics, and hooks from TikTok Creative Center.
"""
import random
import requests
from typing import Dict, List

# Curated High-Performing US Niches & Trending Topics
US_TRENDING_NICHES = {
    "life_hacks": {
        "name": "Life Hacks & Daily Tips",
        "hashtags": ["#lifehacks", "#productivity", "#dailyhacks", "#learnontiktok", "#smarttips", "#tiktoktaughtme"],
        "topics": [
            "3 psychological tricks that make people instantly respect you",
            "Hidden iPhone settings 99% of people have no idea exist",
            "How to fall asleep in under 2 minutes using a military technique",
            "Secret flight booking hack airlines don't want you to know",
            "How to read any person's body language in 10 seconds"
        ]
    },
    "ai_tech": {
        "name": "AI Tools & Tech Secrets",
        "hashtags": ["#aitools", "#techhacks", "#chatgpt", "#aiwebsites", "#futuretech", "#techtok"],
        "topics": [
            "3 free AI websites that feel completely illegal to know",
            "Stop using ChatGPT like a beginner: The prompt formula that changes everything",
            "This secret AI tool creates entire presentations in 30 seconds",
            "How high school and college students are studying 10x faster with AI",
            "The top 3 AI websites that do 10 hours of work in 5 minutes"
        ]
    },
    "fitness_health": {
        "name": "Fitness & Biohacking",
        "hashtags": ["#fitnesshacks", "#gymmotivation", "#biohacking", "#healthtips", "#nutritiontips", "#weightloss"],
        "topics": [
            "The 1 morning habit that doubles your metabolism naturally",
            "Stop doing 100 crunches: Do this 1 exercise for a visible core",
            "What happens to your brain when you drink black coffee without sugar for 14 days",
            "The easiest way to lose 5 pounds of water weight without starving",
            "Why creatine is the most researched supplement on the planet"
        ]
    },
    "motivation_wealth": {
        "name": "Motivation & Financial Habits",
        "hashtags": ["#mindset", "#wealthhabits", "#moneymindset", "#successmotivation", "#discipline", "#sidehustle"],
        "topics": [
            "The brutal truth about money that 99% of people realize too late",
            "3 habits that keep poor people poor according to self-made millionaires",
            "Why you must stop caring about what other people think immediately",
            "The 5-hour rule used by Bill Gates and Elon Musk to stay ahead",
            "How to rewire your brain for extreme focus in 7 days"
        ]
    }
}

class USTrendScraper:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9"
        }

    def fetch_live_creative_center_trends(self) -> List[Dict]:
        """Fetch trending hashtags from TikTok Creative Center API if accessible"""
        try:
            url = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list?page=1&limit=20&period=7&country_code=US"
            resp = requests.get(url, headers=self.headers, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                items = data.get("data", {}).get("list", [])
                trends = []
                for it in items:
                    name = it.get("hashtag_name", "")
                    if name:
                        trends.append({
                            "hashtag": f"#{name}",
                            "rank": it.get("rank", 0),
                            "video_views": it.get("video_views", 0)
                        })
                if trends:
                    return trends
        except Exception:
            pass
        return []

    def get_trend_for_video(self, niche_key: str = None) -> Dict:
        """Pick a viral topic and trending hashtags for video generation"""
        if not niche_key or niche_key not in US_TRENDING_NICHES:
            niche_key = random.choice(list(US_TRENDING_NICHES.keys()))

        niche_data = US_TRENDING_NICHES[niche_key]
        topic = random.choice(niche_data["topics"])
        
        # Combine live trends if available with niche hashtags
        live_trends = self.fetch_live_creative_center_trends()
        hashtags = list(niche_data["hashtags"])
        if live_trends:
            for t in live_trends[:3]:
                if t["hashtag"] not in hashtags:
                    hashtags.append(t["hashtag"])
                    
        # Add general viral US hashtags
        viral_tags = ["#fyp", "#viral", "#foryou", "#trending", "#tiktokusa"]
        hashtags.extend(viral_tags[:2])

        return {
            "niche": niche_key,
            "niche_name": niche_data["name"],
            "topic": topic,
            "hashtags": list(set(hashtags))[:6]
        }

if __name__ == "__main__":
    scraper = USTrendScraper()
    trend = scraper.get_trend_for_video()
    print("Picked Trend:", trend)
