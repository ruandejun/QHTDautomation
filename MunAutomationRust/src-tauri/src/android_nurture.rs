use rand::Rng;
use serde::{Deserialize, Serialize};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio::time::sleep;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AndroidNurtureConfig {
    pub device_serial: String,
    pub videos_per_session: u32,
    pub like_probability: f32,
    pub comment_probability: f32,
    pub follow_probability: f32,
    pub min_watch_seconds: u32,
    pub max_watch_seconds: u32,
    pub fallback_comments: Vec<String>,
}

impl Default for AndroidNurtureConfig {
    fn default() -> Self {
        Self {
            device_serial: String::new(),
            videos_per_session: 30,
            like_probability: 0.65,
            comment_probability: 0.15,
            follow_probability: 0.05,
            min_watch_seconds: 8,
            max_watch_seconds: 45,
            fallback_comments: vec![
                "Video hay quá! 🔥".to_string(),
                "Nội dung chất lượng ❤️".to_string(),
                "Thú vị thật 😍".to_string(),
                "Ủng hộ bạn nha 💪".to_string(),
                "Love this! 🔥".to_string(),
            ],
        }
    }
}

pub struct ADBBridge {
    pub serial: String,
    pub screen_width: u32,
    pub screen_height: u32,
}

impl ADBBridge {
    pub fn new(serial: String) -> Self {
        let mut bridge = Self {
            serial,
            screen_width: 1080,
            screen_height: 2400,
        };
        let (w, h) = bridge.detect_screen_size();
        bridge.screen_width = w;
        bridge.screen_height = h;
        bridge
    }

    pub fn run_cmd(&self, args: &[&str]) -> String {
        let mut cmd = Command::new("adb");
        if !self.serial.is_empty() {
            cmd.arg("-s").arg(&self.serial);
        }
        cmd.args(args);

        match cmd.output() {
            Ok(output) => String::from_utf8_lossy(&output.stdout).trim().to_string(),
            Err(_) => String::new(),
        }
    }

    pub fn detect_screen_size(&self) -> (u32, u32) {
        let out = self.run_cmd(&["shell", "wm", "size"]);
        for line in out.lines() {
            if line.to_lowercase().contains("size:") {
                if let Some(size_part) = line.split(':').last() {
                    let parts: Vec<&str> = size_part.trim().split('x').collect();
                    if parts.len() == 2 {
                        if let (Ok(w), Ok(h)) = (parts[0].parse::<u32>(), parts[1].parse::<u32>()) {
                            return (w, h);
                        }
                    }
                }
            }
        }
        (1080, 2400)
    }

    pub fn ensure_screen_awake(&self) {
        let dumpsys = self.run_cmd(&["shell", "dumpsys", "power"]);
        if dumpsys.contains("mWakefulness=Asleep") || dumpsys.contains("mWakefulness=Dozing") {
            self.run_cmd(&["shell", "input", "keyevent", "26"]); // KEYCODE_POWER
            std::thread::sleep(Duration::from_millis(500));
        }
        // Swipe unlock
        let w = self.screen_width;
        let h = self.screen_height;
        self.run_cmd(&[
            "shell",
            "input",
            "swipe",
            &(w / 2).to_string(),
            &(h * 8 / 10).to_string(),
            &(w / 2).to_string(),
            &(h * 2 / 10).to_string(),
            "200",
        ]);
    }

    pub fn launch_tiktok(&self) {
        self.ensure_screen_awake();
        let out = self.run_cmd(&[
            "shell",
            "monkey",
            "-p",
            "com.zhiliaoapp.musically",
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]);
        if out.contains("No activities found") {
            self.run_cmd(&[
                "shell",
                "monkey",
                "-p",
                "com.ss.android.ugc.trill",
                "-c",
                "android.intent.category.LAUNCHER",
                "1",
            ]);
        }
    }

    pub fn swipe_up(&self) {
        let mut rng = rand::thread_rng();
        let w = self.screen_width;
        let h = self.screen_height;

        let x = rng.gen_range((w * 45 / 100)..=(w * 55 / 100));
        let y1 = rng.gen_range((h * 70 / 100)..=(h * 80 / 100));
        let y2 = rng.gen_range((h * 15 / 100)..=(h * 25 / 100));
        let duration = rng.gen_range(220..=380);

        self.run_cmd(&[
            "shell",
            "input",
            "swipe",
            &x.to_string(),
            &y1.to_string(),
            &x.to_string(),
            &y2.to_string(),
            &duration.to_string(),
        ]);
    }

    pub fn double_tap_like(&self) {
        let mut rng = rand::thread_rng();
        let w = self.screen_width;
        let h = self.screen_height;

        let x = rng.gen_range((w * 45 / 100)..=(w * 55 / 100));
        let y = rng.gen_range((h * 40 / 100)..=(h * 55 / 100));

        self.run_cmd(&["shell", "input", "tap", &x.to_string(), &y.to_string()]);
        std::thread::sleep(Duration::from_millis(80));
        self.run_cmd(&["shell", "input", "tap", &x.to_string(), &y.to_string()]);
    }

    pub fn post_comment(&self, comment: &str) {
        let w = self.screen_width;
        let h = self.screen_height;

        // Chạm nút comment
        let comment_x = (w * 92 / 100).to_string();
        let comment_y = (h * 58 / 100).to_string();
        self.run_cmd(&["shell", "input", "tap", &comment_x, &comment_y]);
        std::thread::sleep(Duration::from_millis(1500));

        // Chạm khung text
        let input_x = (w / 2).to_string();
        let input_y = (h * 95 / 100).to_string();
        self.run_cmd(&["shell", "input", "tap", &input_x, &input_y]);
        std::thread::sleep(Duration::from_millis(1000));

        // Nhập text
        let escaped = comment.replace(' ', "%s");
        self.run_cmd(&["shell", "input", "text", &escaped]);
        std::thread::sleep(Duration::from_millis(1000));

        // Bấm nút gửi
        let send_x = (w * 92 / 100).to_string();
        let send_y = (h * 95 / 100).to_string();
        self.run_cmd(&["shell", "input", "tap", &send_x, &send_y]);
        std::thread::sleep(Duration::from_millis(1000));

        // Back thoát bảng comment
        self.run_cmd(&["shell", "input", "keyevent", "4"]);
    }

    pub fn get_connected_devices() -> Vec<String> {
        let output = Command::new("adb").arg("devices").output();
        let mut devices = Vec::new();

        if let Ok(out) = output {
            let stdout = String::from_utf8_lossy(&out.stdout);
            for line in stdout.lines().skip(1) {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 2 && parts[1] == "device" {
                    devices.push(parts[0].to_string());
                }
            }
        }
        devices
    }
}

pub struct AndroidNurtureSession {
    pub bridge: ADBBridge,
    pub config: AndroidNurtureConfig,
    pub is_running: Arc<AtomicBool>,
}

impl AndroidNurtureSession {
    pub fn new(serial: String, config: AndroidNurtureConfig, is_running: Arc<AtomicBool>) -> Self {
        Self {
            bridge: ADBBridge::new(serial),
            config,
            is_running,
        }
    }

    pub async fn run<F>(&self, log_callback: F)
    where
        F: Fn(&str, &str) + Send + Sync + 'static,
    {
        let (w, h) = (self.bridge.screen_width, self.bridge.screen_height);
        log_callback(
            "INFO",
            &format!(
                "🚀 [Rust ADB] Khởi động phiên nuôi thiết bị [{}] (Màn hình: {}x{})",
                self.bridge.serial, w, h
            ),
        );

        self.bridge.launch_tiktok();
        sleep(Duration::from_secs(5)).await;

        for i in 1..=self.config.videos_per_session {
            if !self.is_running.load(Ordering::SeqCst) {
                log_callback("WARN", &format!("⛔ Đã dừng nuôi thiết bị [{}]", self.bridge.serial));
                break;
            }

            let watch_seconds = {
                let mut rng = rand::thread_rng();
                rng.gen_range(self.config.min_watch_seconds..=self.config.max_watch_seconds)
            };

            log_callback(
                "INFO",
                &format!(
                    "👀 [{}] Đang xem video FYP {}/{} (Thời lượng: {}s)",
                    self.bridge.serial, i, self.config.videos_per_session, watch_seconds
                ),
            );

            sleep(Duration::from_secs(watch_seconds as u64)).await;

            // Xử lý Like
            let should_like = {
                let mut rng = rand::thread_rng();
                rng.gen_range(0.0..1.0) < self.config.like_probability
            };
            if should_like {
                self.bridge.double_tap_like();
                log_callback(
                    "SUCCESS",
                    &format!("❤️ [{}] Đã thả tim (Double-tap) video {}", self.bridge.serial, i),
                );
                sleep(Duration::from_millis(800)).await;
            }

            // Xử lý Comment
            let should_comment = {
                let mut rng = rand::thread_rng();
                rng.gen_range(0.0..1.0) < self.config.comment_probability
            };
            if should_comment && !self.config.fallback_comments.is_empty() {
                let comment = {
                    let mut rng = rand::thread_rng();
                    let idx = rng.gen_range(0..self.config.fallback_comments.len());
                    self.config.fallback_comments[idx].clone()
                };
                self.bridge.post_comment(&comment);
                log_callback(
                    "SUCCESS",
                    &format!("💬 [{}] Đã bình luận: \"{}\"", self.bridge.serial, comment),
                );
                sleep(Duration::from_millis(1000)).await;
            }

            // Lướt video tiếp theo
            self.bridge.swipe_up();
            sleep(Duration::from_millis(1500)).await;
        }

        log_callback(
            "SUCCESS",
            &format!("🎉 [{}] Hoàn thành chu trình nuôi TikTok.", self.bridge.serial),
        );
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_adb_bridge_initialization() {
        let bridge = ADBBridge::new("test_serial_123".to_string());
        assert_eq!(bridge.serial, "test_serial_123");
        assert!(bridge.screen_width > 0);
        assert!(bridge.screen_height > 0);
    }

    #[test]
    fn test_config_defaults() {
        let cfg = AndroidNurtureConfig::default();
        assert_eq!(cfg.videos_per_session, 30);
        assert!(!cfg.fallback_comments.is_empty());
    }
}
