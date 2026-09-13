use crate::adb_manager::AdbManager;
use parking_lot::RwLock;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tracing::{info, warn};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NurtureConfig {
    pub videos_per_session: u32,
    pub like_probability: f32,
    pub comment_probability: f32,
    pub follow_probability: f32,
    pub min_watch_seconds: u32,
    pub max_watch_seconds: u32,
    pub gemini_api_key: String,
    pub video_niche: String,
    pub video_language: String,
}

impl Default for NurtureConfig {
    fn default() -> Self {
        Self {
            videos_per_session: 30,
            like_probability: 0.65,
            comment_probability: 0.15,
            follow_probability: 0.05,
            min_watch_seconds: 8,
            max_watch_seconds: 35,
            gemini_api_key: String::new(),
            video_niche: "trending".to_string(),
            video_language: "vi".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NurtureStats {
    pub device_serial: String,
    pub videos_watched: u32,
    pub likes_given: u32,
    pub comments_posted: u32,
    pub follows_given: u32,
    pub status: String,
    pub last_action: String,
}

#[derive(Clone)]
pub struct TikTokNurtureEngine {
    adb: Arc<AdbManager>,
    is_running: Arc<AtomicBool>,
    config: Arc<RwLock<NurtureConfig>>,
    stats: Arc<RwLock<std::collections::HashMap<String, NurtureStats>>>,
}

impl TikTokNurtureEngine {
    pub fn new(adb: Arc<AdbManager>) -> Self {
        Self {
            adb,
            is_running: Arc::new(AtomicBool::new(false)),
            config: Arc::new(RwLock::new(NurtureConfig::default())),
            stats: Arc::new(RwLock::new(std::collections::HashMap::new())),
        }
    }

    pub fn set_config(&self, cfg: NurtureConfig) {
        *self.config.write() = cfg;
    }

    pub fn get_stats(&self) -> Vec<NurtureStats> {
        self.stats.read().values().cloned().collect()
    }

    pub fn is_running(&self) -> bool {
        self.is_running.load(Ordering::Relaxed)
    }

    pub fn stop(&self) {
        self.is_running.store(false, Ordering::Relaxed);
        info!("TikTok Nurture Engine stop requested.");
    }

    pub async fn start_all_devices(&self, target_serials: Vec<String>) {
        if self.is_running.load(Ordering::Relaxed) {
            warn!("TikTok Nurture is already running.");
            return;
        }

        self.is_running.store(true, Ordering::Relaxed);
        info!("Starting TikTok Nurture on {} devices...", target_serials.len());

        for serial in target_serials {
            let engine = self.clone();
            let s = serial.clone();
            tokio::spawn(async move {
                engine.run_device_worker(s).await;
            });
        }
    }

    async fn run_device_worker(&self, serial: String) {
        let (width, height) = self.adb.get_screen_resolution(&serial).unwrap_or((720, 1280));
        
        {
            let mut lock = self.stats.write();
            lock.insert(serial.clone(), NurtureStats {
                device_serial: serial.clone(),
                videos_watched: 0,
                likes_given: 0,
                comments_posted: 0,
                follows_given: 0,
                status: "Starting".to_string(),
                last_action: "Waking up device".to_string(),
            });
        }

        // 1. Wake up and unlock
        let _ = self.adb.wake_up(&serial);
        tokio::time::sleep(Duration::from_millis(1000)).await;

        // 2. Launch TikTok app
        // Common packages: com.zhiliaoapp.musically (Global), com.ss.android.ugc.trill (Asia/VN), com.ss.android.ugc.aweme.lite
        let tiktok_pkgs = ["com.zhiliaoapp.musically", "com.ss.android.ugc.trill", "com.ss.android.ugc.aweme.lite"];
        let mut launched = false;
        for pkg in &tiktok_pkgs {
            if self.adb.launch_app(&serial, pkg).is_ok() {
                launched = true;
                break;
            }
        }

        if !launched {
            let _ = self.adb.launch_app(&serial, "com.zhiliaoapp.musically");
        }

        info!("Launched TikTok on device {}", serial);
        tokio::time::sleep(Duration::from_secs(5)).await;

        let config = self.config.read().clone();
        let target_videos = config.videos_per_session;

        for vid_idx in 1..=target_videos {
            if !self.is_running.load(Ordering::Relaxed) {
                break;
            }

            // A. Watch video for randomized duration
            let watch_sec = {
                let mut rng = rand::thread_rng();
                rng.gen_range(config.min_watch_seconds..=config.max_watch_seconds)
            };

            {
                let mut lock = self.stats.write();
                if let Some(st) = lock.get_mut(&serial) {
                    st.videos_watched = vid_idx;
                    st.status = "Watching FYP".to_string();
                    st.last_action = format!("Video #{}/{} - watching {}s", vid_idx, target_videos, watch_sec);
                }
            }

            tokio::time::sleep(Duration::from_secs(watch_sec as u64)).await;

            if !self.is_running.load(Ordering::Relaxed) {
                break;
            }

            // B. Engagement: Like (Double tap)
            let should_like = {
                let mut rng = rand::thread_rng();
                rng.gen::<f32>() < config.like_probability
            };

            if should_like {
                let (center_x, center_y) = {
                    let mut rng = rand::thread_rng();
                    (
                        width / 2 + rng.gen_range(0..50) - 25,
                        height / 2 + rng.gen_range(0..100) - 50,
                    )
                };
                let _ = self.adb.tap(&serial, center_x, center_y);
                tokio::time::sleep(Duration::from_millis(150)).await;
                let _ = self.adb.tap(&serial, center_x, center_y);
                
                {
                    let mut lock = self.stats.write();
                    if let Some(st) = lock.get_mut(&serial) {
                        st.likes_given += 1;
                        st.last_action = "Liked video (double tap)".to_string();
                    }
                }
                tokio::time::sleep(Duration::from_millis(800)).await;
            }

            // C. Engagement: Follow creator
            let should_follow = {
                let mut rng = rand::thread_rng();
                rng.gen::<f32>() < config.follow_probability
            };

            if should_follow {
                // Follow button is typically around (width * 0.9, height * 0.45)
                let follow_x = (width as f32 * 0.9) as u32;
                let follow_y = (height as f32 * 0.45) as u32;
                let _ = self.adb.tap(&serial, follow_x, follow_y);
                {
                    let mut lock = self.stats.write();
                    if let Some(st) = lock.get_mut(&serial) {
                        st.follows_given += 1;
                        st.last_action = "Followed creator".to_string();
                    }
                }
                tokio::time::sleep(Duration::from_millis(1000)).await;
            }

            // D. Engagement: Comment
            let should_comment = {
                let mut rng = rand::thread_rng();
                rng.gen::<f32>() < config.comment_probability
            };

            if should_comment {
                self.perform_comment(&serial, width, height, &config).await;
            }

            // E. Swipe up to next video in FYP
            let (start_x, start_y, end_x, end_y, swipe_dur) = {
                let mut rng = rand::thread_rng();
                let sx = width / 2 + rng.gen_range(0..40) - 20;
                let sy = (height as f32 * 0.8) as u32;
                let ex = sx + rng.gen_range(0..20) - 10;
                let ey = (height as f32 * 0.2) as u32;
                let dur = rng.gen_range(300..500);
                (sx, sy, ex, ey, dur)
            };

            let _ = self.adb.swipe(&serial, start_x, start_y, end_x, end_y, swipe_dur);
            tokio::time::sleep(Duration::from_millis(1500)).await;
        }

        {
            let mut lock = self.stats.write();
            if let Some(st) = lock.get_mut(&serial) {
                st.status = "Completed".to_string();
                st.last_action = "Session finished successfully".to_string();
            }
        }
        info!("TikTok Nurture session completed for device {}", serial);
    }

    async fn perform_comment(&self, serial: &str, width: u32, height: u32, config: &NurtureConfig) {
        // Comment icon coordinate in TikTok is roughly around (width * 0.9, height * 0.6)
        let comment_btn_x = (width as f32 * 0.9) as u32;
        let comment_btn_y = (height as f32 * 0.6) as u32;

        let _ = self.adb.tap(serial, comment_btn_x, comment_btn_y);
        tokio::time::sleep(Duration::from_millis(1500)).await;

        // Generate AI Comment or fallback
        let comment_text = self.generate_comment(config).await;

        // Tap comment input box
        let input_x = width / 2;
        let input_y = height - 80;
        let _ = self.adb.tap(serial, input_x, input_y);
        tokio::time::sleep(Duration::from_millis(800)).await;

        // Type comment text
        let _ = self.adb.input_text(serial, &comment_text);
        tokio::time::sleep(Duration::from_millis(1000)).await;

        // Send comment (Enter / send icon)
        let send_x = width - 60;
        let send_y = height - 80;
        let _ = self.adb.tap(serial, send_x, send_y);
        let _ = self.adb.keyevent(serial, 66); // KEYCODE_ENTER
        tokio::time::sleep(Duration::from_millis(1200)).await;

        // Close comment sheet (Back button or tap upper area)
        let _ = self.adb.keyevent(serial, 4); // KEYCODE_BACK
        tokio::time::sleep(Duration::from_millis(800)).await;

        {
            let mut lock = self.stats.write();
            if let Some(st) = lock.get_mut(serial) {
                st.comments_posted += 1;
                st.last_action = format!("Commented: \"{}\"", comment_text);
            }
        }
    }

    async fn generate_comment(&self, config: &NurtureConfig) -> String {
        let fallbacks = [
            "Video hay qua ban oi! 🔥",
            "Dung la kien thuc bo ich ❤️",
            "Tuyet voi qua a 👍",
            "10 diem khong co nhung 😁",
            "Hay qua shop oi!",
            "Thanks for sharing! 🔥",
            "Amazing content ❤️",
        ];

        if config.gemini_api_key.trim().is_empty() {
            let mut rng = rand::thread_rng();
            return fallbacks[rng.gen_range(0..fallbacks.len())].to_string();
        }

        // Call Gemini REST API for contextual comment
        let prompt = format!(
            "Hãy viết một câu bình luận ngắn (dưới 10 từ) tự nhiên như người dùng thật khen ngợi video TikTok về chủ đề {}. Ngôn ngữ: {}. Không dùng ngoặc kép, không giải thích.",
            config.video_niche, config.video_language
        );

        let url = format!(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={}",
            config.gemini_api_key.trim()
        );

        let body = serde_json::json!({
            "contents": [{
                "parts": [{ "text": prompt }]
            }]
        });

        let client = reqwest::Client::new();
        if let Ok(resp) = client.post(&url).json(&body).timeout(Duration::from_secs(5)).send().await {
            if let Ok(json_val) = resp.json::<serde_json::Value>().await {
                if let Some(candidate) = json_val["candidates"][0]["content"]["parts"][0]["text"].as_str() {
                    let cleaned = candidate.trim().replace('"', "").replace('\n', " ");
                    if !cleaned.is_empty() {
                        return cleaned;
                    }
                }
            }
        }

        let mut rng = rand::thread_rng();
        fallbacks[rng.gen_range(0..fallbacks.len())].to_string()
    }
}
