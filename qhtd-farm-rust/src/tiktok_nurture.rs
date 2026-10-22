use crate::adb_manager::AdbManager;
use parking_lot::RwLock;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::path::Path;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tracing::{info, warn};

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default)]
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
            videos_per_session: 20,
            like_probability: 0.60,
            comment_probability: 0.15,
            follow_probability: 0.10,
            min_watch_seconds: 8,
            max_watch_seconds: 25,
            gemini_api_key: String::new(),
            video_niche: "trending".to_string(),
            video_language: "en".to_string(),
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NurtureStats {
    pub device_serial: String,
    pub account_user: String,
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
    /// Số worker đang chạy; về 0 thì engine tự reset is_running để có thể start lại.
    active_workers: Arc<AtomicUsize>,
    config: Arc<RwLock<NurtureConfig>>,
    stats: Arc<RwLock<std::collections::HashMap<String, NurtureStats>>>,
}

/// Giảm bộ đếm worker khi worker kết thúc (kể cả panic) và reset cờ chạy khi hết worker.
struct WorkerGuard {
    active: Arc<AtomicUsize>,
    running: Arc<AtomicBool>,
}

impl Drop for WorkerGuard {
    fn drop(&mut self) {
        if self.active.fetch_sub(1, Ordering::SeqCst) == 1 {
            self.running.store(false, Ordering::SeqCst);
        }
    }
}

#[derive(Debug, Clone)]
struct SimpleNode {
    text: String,
    desc: String,
    class: String,
    bounds: (i32, i32, i32, i32),
    clickable: bool,
}

impl SimpleNode {
    fn center(&self) -> (i32, i32) {
        ((self.bounds.0 + self.bounds.2) / 2, (self.bounds.1 + self.bounds.3) / 2)
    }
}

#[derive(Debug, Clone, Copy, PartialEq)]
enum Screen {
    Ok,
    NoInternet,
    RateLimit,
    LoggedOut,
    Captcha,
}

/// Phân loại màn hình TikTok hiện tại từ XML. Thứ tự ưu tiên: RateLimit > Captcha > NoInternet > LoggedOut.
fn classify_screen(nodes: &[SimpleNode]) -> Screen {
    let mut all = String::new();
    for n in nodes {
        all.push_str(&n.text.to_lowercase());
        all.push('\n');
        all.push_str(&n.desc.to_lowercase());
        all.push('\n');
    }
    let has = |keys: &[&str]| keys.iter().any(|k| all.contains(k));
    if has(&["maximum number of attempts", "too many attempts", "too many failed"]) {
        return Screen::RateLimit;
    }
    if has(&["drag the slider", "drag the puzzle", "verify to continue", "select 2 objects", "slide to verify"]) {
        return Screen::Captcha;
    }
    // Bảng/màn đăng nhập của TikTok (kể cả dạng bottom-sheet phủ lên feed khi like/comment lúc chưa login).
    if has(&["log in to tiktok", "use phone / email / username"]) {
        return Screen::LoggedOut;
    }
    // Màn đăng nhập: có nhiều phương thức đăng nhập và KHÔNG có thanh tab Home/Inbox/Profile.
    let on_feed = has(&["for you", "following"]) && has(&["inbox", "profile"]);
    if !on_feed
        && has(&["log in to tiktok", "sign up for tiktok", "continue with google", "continue with facebook", "use phone / email / username", "already have an account"])
    {
        return Screen::LoggedOut;
    }
    if has(&["no internet", "network error", "check your network", "no network", "connection failed", "tap to retry", "couldn't connect", "unable to connect"]) {
        return Screen::NoInternet;
    }
    Screen::Ok
}

/// Có đang ở feed TikTok thật không (thanh tab dưới: For You/Following + Inbox/Profile).
/// Màn hình chọn ngày sinh, onboarding, login... đều KHÔNG có thanh này.
fn on_feed(nodes: &[SimpleNode]) -> bool {
    let mut all = String::new();
    for n in nodes {
        all.push_str(&n.text.to_lowercase());
        all.push('\n');
        all.push_str(&n.desc.to_lowercase());
        all.push('\n');
    }
    (all.contains("for you") || all.contains("following")) && (all.contains("inbox") || all.contains("profile"))
}

fn first_texts(nodes: &[SimpleNode]) -> String {
    nodes.iter().map(|n| n.text.trim()).filter(|t| !t.is_empty()).take(2).collect::<Vec<_>>().join(" / ")
}

fn parse_simple_bounds(b: &str) -> (i32, i32, i32, i32) {
    let nums: Vec<i32> = b
        .split(|c: char| !c.is_ascii_digit())
        .filter(|s| !s.is_empty())
        .filter_map(|s| s.parse().ok())
        .collect();
    if nums.len() == 4 {
        (nums[0], nums[1], nums[2], nums[3])
    } else {
        (0, 0, 0, 0)
    }
}

/// Bản async: chạy uiautomator dump trên blocking pool để không làm đói tokio runtime.
async fn dump_xml_nodes_async(adb_path: &Path, serial: &str) -> Vec<SimpleNode> {
    let p = adb_path.to_path_buf();
    let s = serial.to_string();
    tokio::task::spawn_blocking(move || dump_xml_nodes(&p, &s))
        .await
        .unwrap_or_default()
}

fn dump_xml_nodes(adb_path: &Path, serial: &str) -> Vec<SimpleNode> {
    let mut cmd = std::process::Command::new(adb_path);
    cmd.args([
        "-s",
        serial,
        "shell",
        "rm -f /data/local/tmp/nurture_ui.xml; uiautomator dump /data/local/tmp/nurture_ui.xml >/dev/null 2>&1; cat /data/local/tmp/nurture_ui.xml",
    ]);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    let out = match cmd.output() {
        Ok(o) => String::from_utf8_lossy(&o.stdout).to_string(),
        Err(_) => return Vec::new(),
    };

    let start = match out.find("<hierarchy") {
        Some(s) => s,
        None => return Vec::new(),
    };
    let end = out.rfind("</hierarchy>").map(|e| e + "</hierarchy>".len()).unwrap_or(out.len());
    let doc = match roxmltree::Document::parse(&out[start..end]) {
        Ok(d) => d,
        Err(_) => return Vec::new(),
    };

    let mut nodes = Vec::new();
    for n in doc.descendants().filter(|n| n.has_tag_name("node")) {
        nodes.push(SimpleNode {
            text: n.attribute("text").unwrap_or("").to_string(),
            desc: n.attribute("content-desc").unwrap_or("").to_string(),
            class: n.attribute("class").unwrap_or("").to_string(),
            bounds: parse_simple_bounds(n.attribute("bounds").unwrap_or("")),
            clickable: n.attribute("clickable") == Some("true"),
        });
    }
    nodes
}

impl TikTokNurtureEngine {
    pub fn new(adb: Arc<AdbManager>) -> Self {
        Self {
            adb,
            is_running: Arc::new(AtomicBool::new(false)),
            active_workers: Arc::new(AtomicUsize::new(0)),
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
        if target_serials.is_empty() {
            warn!("TikTok Nurture: không có thiết bị nào để chạy.");
            return;
        }
        if self.is_running.swap(true, Ordering::SeqCst) {
            warn!("TikTok Nurture is already running.");
            return;
        }
        info!("Starting TikTok Native XML Nurture on {} devices...", target_serials.len());

        self.active_workers.store(target_serials.len(), Ordering::SeqCst);
        for serial in target_serials {
            let engine = self.clone();
            let s = serial.clone();
            tokio::spawn(async move {
                let _guard = WorkerGuard {
                    active: engine.active_workers.clone(),
                    running: engine.is_running.clone(),
                };
                engine.run_device_worker(s).await;
            });
        }
    }

    async fn run_device_worker(&self, serial: String) {
        let adb_path = self.adb.get_adb_path().to_path_buf();
        let (width, height) = self.adb.get_screen_resolution(&serial).unwrap_or((720, 1480));

        {
            let mut lock = self.stats.write();
            lock.insert(serial.clone(), NurtureStats {
                device_serial: serial.clone(),
                account_user: "Detecting...".to_string(),
                videos_watched: 0,
                likes_given: 0,
                comments_posted: 0,
                follows_given: 0,
                status: "Starting".to_string(),
                last_action: "Khởi động và kiểm tra màn hình".to_string(),
            });
        }

        // 1. Wake up
        let _ = self.adb.wake_up(&serial);
        tokio::time::sleep(Duration::from_millis(800)).await;

        // 1.2 Máy phải ở đúng Wi-Fi farm (hay trôi sang Wi-Fi phụ không có internet -> "No internet").
        {
            let (ap, sr) = (adb_path.clone(), serial.clone());
            let r = tokio::task::spawn_blocking(move || crate::xml_login::ensure_farm_wifi(&ap, &sr)).await;
            if let Ok(Err(e)) = r {
                self.finish_fatal(&serial, &e);
                return;
            }
        }

        // 1.5 TikTok phải được cài trên máy (nhiều máy chưa cài -> trước đây vuốt nhầm trên launcher/Play Store).
        if !self.is_tiktok_installed(&adb_path, &serial) {
            self.finish_fatal(&serial, "TikTok chưa được cài trên máy này (com.zhiliaoapp.musically) — cài app trước khi nuôi");
            return;
        }

        // 2. Launch TikTok app
        let _ = self.adb.launch_app(&serial, "com.zhiliaoapp.musically");
        tokio::time::sleep(Duration::from_secs(4)).await;

        // 2.5 Xác nhận TikTok thật sự đang ở foreground, không thì mở lại 1 lần rồi báo lỗi.
        if !self.is_tiktok_foreground(&adb_path, &serial) {
            let _ = self.adb.keyevent(&serial, 3);
            tokio::time::sleep(Duration::from_millis(800)).await;
            let _ = self.adb.launch_app(&serial, "com.zhiliaoapp.musically");
            tokio::time::sleep(Duration::from_secs(6)).await;
            if !self.is_tiktok_foreground(&adb_path, &serial) {
                self.finish_fatal(&serial, "Không mở được TikTok lên foreground (app lỗi/bị chặn)");
                return;
            }
        }

        // 3. Đọc XML kiểm tra và xử lý popup ban đầu
        self.dismiss_feed_popups(&adb_path, &serial).await;
        if let Err(e) = self.ensure_healthy(&adb_path, &serial, None).await {
            self.finish_fatal(&serial, &e);
            return;
        }

        // 4. Kiểm tra user hiện tại qua XML Profile hoặc Session
        let mut cur_user = match self.verify_logged_in(&adb_path, &serial, width, height).await {
            Ok(u) => u,
            Err(e) => {
                self.finish_fatal(&serial, &e);
                return;
            }
        };
        let nodes = if cur_user.is_empty() { dump_xml_nodes_async(&adb_path, &serial).await } else { Vec::new() };
        for n in &nodes {
            let t = n.text.trim();
            if t.starts_with('@') && t.len() > 1 {
                cur_user = t.to_string();
                break;
            }
        }
        if cur_user.is_empty() {
            // Lấy từ shared_prefs bằng adb process command
            let mut cmd = std::process::Command::new(&adb_path);
            cmd.args(["-s", &serial, "shell", "su -c 'cat /data/data/com.zhiliaoapp.musically/shared_prefs/aweme_user.xml 2>/dev/null'"]);
            #[cfg(target_os = "windows")]
            {
                use std::os::windows::process::CommandExt;
                cmd.creation_flags(0x08000000);
            }
            if let Ok(out) = cmd.output() {
                let out_str = String::from_utf8_lossy(&out.stdout);
                if let Some(pos) = out_str.find("unique_id&quot;:&quot;") {
                    let sub = &out_str[pos + 22..];
                    if let Some(end) = sub.find("&quot;") {
                        cur_user = format!("@{}", &sub[..end]);
                    }
                }
            }
        }

        {
            let mut lock = self.stats.write();
            if let Some(st) = lock.get_mut(&serial) {
                st.account_user = if cur_user.is_empty() { "Đang hoạt động".into() } else { cur_user.clone() };
                st.status = "Watching FYP".to_string();
            }
        }

        let config = self.config.read().clone();
        let target_videos = config.videos_per_session;

        // Đảm bảo ở tab Home (Feed FYP)
        let _ = self.adb.tap(&serial, 72, height - 30);
        tokio::time::sleep(Duration::from_millis(1500)).await;

        let mut relaunches = 0u32;
        let mut no_feed = 0u32;
        for vid_idx in 1..=target_videos {
            if !self.is_running.load(Ordering::Relaxed) {
                break;
            }

            // TikTok bị văng ra Home/app khác (crash, bị hệ thống tắt) -> mở lại, không vuốt nhầm trên launcher.
            if !self.is_tiktok_foreground(&adb_path, &serial) {
                relaunches += 1;
                if relaunches > 3 {
                    self.finish_fatal(&serial, "TikTok liên tục bị thoát ra ngoài (>3 lần) — kiểm tra máy/app");
                    return;
                }
                self.set_action(&serial, "Watching FYP", format!("TikTok bị thoát ra ngoài — mở lại ({}/3)", relaunches));
                let _ = self.adb.launch_app(&serial, "com.zhiliaoapp.musically");
                tokio::time::sleep(Duration::from_secs(5)).await;
            }

            // Dọn dẹp popup nếu có
            self.dismiss_feed_popups(&adb_path, &serial).await;

            // A. Thời gian xem ngẫu nhiên theo cấu hình
            let watch_sec = {
                let mut rng = rand::thread_rng();
                rng.gen_range(config.min_watch_seconds..=config.max_watch_seconds)
            };

            {
                let mut lock = self.stats.write();
                if let Some(st) = lock.get_mut(&serial) {
                    st.videos_watched = vid_idx;
                    st.last_action = format!("Video #{}/{} - xem {}s", vid_idx, target_videos, watch_sec);
                }
            }

            tokio::time::sleep(Duration::from_secs(watch_sec as u64)).await;

            if !self.is_running.load(Ordering::Relaxed) {
                break;
            }

            // Đọc UI XML để tương tác chính xác
            let screen_nodes = dump_xml_nodes_async(&adb_path, &serial).await;
            // Phát hiện màn hình lỗi (No internet / Maximum attempts / bị đăng xuất / captcha) và tự phục hồi.
            let screen_nodes = if !matches!(classify_screen(&screen_nodes), Screen::Ok) {
                match self.ensure_healthy(&adb_path, &serial, Some(screen_nodes)).await {
                    Ok(()) => dump_xml_nodes_async(&adb_path, &serial).await,
                    Err(e) => {
                        self.finish_fatal(&serial, &e);
                        return;
                    }
                }
            } else {
                screen_nodes
            };

            // Không ở feed (VD: màn hình nhập ngày sinh/onboarding) -> không vuốt bậy, báo lỗi nếu kéo dài.
            if !screen_nodes.is_empty() && !on_feed(&screen_nodes) {
                no_feed += 1;
                if no_feed >= 3 {
                    self.finish_fatal(&serial, &format!("Không thấy feed TikTok — đang ở màn hình lạ: {}", first_texts(&screen_nodes)));
                    return;
                }
                let _ = self.adb.keyevent(&serial, 4);
                tokio::time::sleep(Duration::from_millis(1000)).await;
                continue;
            }
            no_feed = 0;

            // B. Tương tác: Like (Tìm thẻ XML Like video hoặc Double Tap tự nhiên)
            let should_like = {
                let mut rng = rand::thread_rng();
                rng.gen::<f32>() < config.like_probability
            };

            if should_like {
                let mut liked = false;
                for n in &screen_nodes {
                    let d = n.desc.to_lowercase();
                    if (d.starts_with("like video") || d == "like") && n.bounds.2 > 0 {
                        let (cx, cy) = n.center();
                        let _ = self.adb.tap(&serial, cx as u32, cy as u32);
                        liked = true;
                        break;
                    }
                }
                if !liked {
                    let cx = width / 2;
                    let cy = height / 2;
                    let _ = self.adb.tap(&serial, cx, cy);
                    tokio::time::sleep(Duration::from_millis(120)).await;
                    let _ = self.adb.tap(&serial, cx, cy);
                }

                {
                    let mut lock = self.stats.write();
                    if let Some(st) = lock.get_mut(&serial) {
                        st.likes_given += 1;
                        st.last_action = "Đã thả tim video ❤️".to_string();
                    }
                }
                tokio::time::sleep(Duration::from_millis(600)).await;
            }

            // C. Tương tác: Follow (Tìm thẻ XML Follow)
            let should_follow = {
                let mut rng = rand::thread_rng();
                rng.gen::<f32>() < config.follow_probability
            };

            if should_follow {
                for n in &screen_nodes {
                    let d = n.desc.to_lowercase();
                    let t = n.text.to_lowercase();
                    if (d.starts_with("follow ") || t == "follow") && n.bounds.2 > 0 {
                        let (cx, cy) = n.center();
                        let _ = self.adb.tap(&serial, cx as u32, cy as u32);
                        {
                            let mut lock = self.stats.write();
                            if let Some(st) = lock.get_mut(&serial) {
                                st.follows_given += 1;
                                st.last_action = "Đã bấm Follow kênh ➕".to_string();
                            }
                        }
                        tokio::time::sleep(Duration::from_millis(800)).await;
                        break;
                    }
                }
            }

            // D. Tương tác: Comment (Tìm thẻ XML Read or add comments)
            let should_comment = {
                let mut rng = rand::thread_rng();
                rng.gen::<f32>() < config.comment_probability
            };

            if should_comment {
                let mut comment_node: Option<SimpleNode> = None;
                for n in &screen_nodes {
                    let d = n.desc.to_lowercase();
                    if d.contains("comments") && n.bounds.2 > 0 {
                        comment_node = Some(n.clone());
                        break;
                    }
                }

                if let Some(cn) = comment_node {
                    let (cx, cy) = cn.center();
                    let _ = self.adb.tap(&serial, cx as u32, cy as u32);
                    tokio::time::sleep(Duration::from_millis(1800)).await;
                    let sheet = dump_xml_nodes_async(&adb_path, &serial).await;
                    if !matches!(classify_screen(&sheet), Screen::Ok) {
                        if let Err(e) = self.ensure_healthy(&adb_path, &serial, Some(sheet)).await {
                            self.finish_fatal(&serial, &e);
                            return;
                        }
                        continue;
                    }
                    let input = sheet
                        .iter()
                        .find(|n| n.bounds.2 > 0 && (n.class.ends_with("EditText") || n.text.to_lowercase().starts_with("add comment")))
                        .cloned();
                    if let Some(inp) = input {
                        let (ix, iy) = inp.center();
                        let _ = self.adb.tap(&serial, ix as u32, iy as u32);
                        tokio::time::sleep(Duration::from_millis(1200)).await;

                        // adb `input text` không gõ được emoji/Unicode -> chỉ giữ ASCII.
                        let mut comment_text: String = self.generate_comment(&config).await.chars().filter(|c| c.is_ascii()).collect();
                        comment_text = comment_text.trim().to_string();
                        if comment_text.is_empty() {
                            comment_text = "Nice video!".to_string();
                        }
                        let _ = self.adb.input_text(&serial, &comment_text);
                        tokio::time::sleep(Duration::from_millis(900)).await;

                        let typed = dump_xml_nodes_async(&adb_path, &serial).await;
                        if !matches!(classify_screen(&typed), Screen::Ok) {
                            if let Err(e) = self.ensure_healthy(&adb_path, &serial, Some(typed)).await {
                                self.finish_fatal(&serial, &e);
                                return;
                            }
                            continue;
                        }
                        let send = typed
                            .iter()
                            .find(|n| {
                                let t = n.text.trim().to_lowercase();
                                let d = n.desc.trim().to_lowercase();
                                n.bounds.2 > 0 && (matches!(t.as_str(), "post" | "send") || matches!(d.as_str(), "post" | "send" | "post comment" | "send comment"))
                            })
                            .cloned();
                        match send {
                            Some(s) => {
                                let (sx2, sy2) = s.center();
                                let _ = self.adb.tap(&serial, sx2 as u32, sy2 as u32);
                            }
                            None => {
                                // Hạ bàn phím trước để nút Send đỏ hiện rõ
                                let _ = self.adb.keyevent(&serial, 4);
                                tokio::time::sleep(Duration::from_millis(500)).await;
                                // Fallback nút Send màu đỏ (hình mũi tên lên) ở góc dưới phải (x ≈ 643, y ≈ 1344 trên màn 720x1480)
                                let send_x = (width as f32 * 0.89) as u32;
                                let send_y = (height as f32 * 0.908) as u32;
                                let _ = self.adb.tap(&serial, send_x, send_y);
                            }
                        }
                        tokio::time::sleep(Duration::from_millis(2500)).await;

                        // Chỉ tính là đã bình luận khi nội dung xuất hiện thật trong danh sách bình luận.
                        let after = dump_xml_nodes_async(&adb_path, &serial).await;
                        let posted = after.iter().any(|n| n.text.contains(comment_text.as_str()) && !n.class.ends_with("EditText"));
                        let mut lock = self.stats.write();
                        if let Some(st) = lock.get_mut(&serial) {
                            if posted {
                                st.comments_posted += 1;
                                st.last_action = format!("Đã bình luận: \"{}\"", comment_text);
                            } else {
                                st.last_action = "Bình luận chưa đăng được (bỏ qua)".to_string();
                            }
                        }
                    }
                    // Đóng bảng bình luận (tối đa 2 lần Back).
                    for _ in 0..2 {
                        let _ = self.adb.keyevent(&serial, 4);
                        tokio::time::sleep(Duration::from_millis(800)).await;
                        let n = dump_xml_nodes_async(&adb_path, &serial).await;
                        if !n.iter().any(|x| x.text.to_lowercase().starts_with("add comment")) {
                            break;
                        }
                    }
                } else {
                    self.set_action(&serial, "Watching FYP", "Bỏ qua bình luận: không thấy nút bình luận".to_string());
                }
            }
            // E. Lướt sang video tiếp theo (Swipe Up mượt mà)
            let (sx, sy, ex, ey, dur) = {
                let mut rng = rand::thread_rng();
                let sx = width / 2 + rng.gen_range(0..40) - 20;
                let sy = (height as f32 * 0.78) as u32;
                let ex = sx + rng.gen_range(0..20) - 10;
                let ey = (height as f32 * 0.22) as u32;
                let dur = rng.gen_range(280..420);
                (sx, sy, ex, ey, dur)
            };

            let _ = self.adb.swipe(&serial, sx, sy, ex, ey, dur);
            tokio::time::sleep(Duration::from_millis(1200)).await;
        }

        // stop() đặt is_running=false => phiên bị ngắt giữa chừng, KHÔNG báo thành công.
        let completed = self.is_running.load(Ordering::Relaxed);
        let mut c69_log: Option<String> = None;
        {
            let mut lock = self.stats.write();
            if let Some(st) = lock.get_mut(&serial) {
                if completed {
                    st.status = "Hoàn thành".to_string();
                    st.last_action = "Phiên nuôi hoàn tất xuất sắc ✅".to_string();
                    // Ghi log tiến trình nuôi lên C69 để Client theo dõi theo chỉ đạo anh Tony
                    c69_log = Some(format!(
                        "Đã nuôi thành công trên thiết bị {} (Xem {} video, thả {} tim, {} bình luận, theo dõi {} kênh)",
                        serial, st.videos_watched, st.likes_given, st.comments_posted, st.follows_given
                    ));
                } else {
                    st.status = "Đã dừng".to_string();
                    st.last_action = "Đã dừng theo lệnh người dùng ⏹".to_string();
                }
            }
        }
        // Gọi C69 (HTTP blocking) ngoài lock và ngoài luồng async.
        if let Some(action_log) = c69_log {
            if !cur_user.is_empty() {
                let user = cur_user.clone();
                let _ = tokio::task::spawn_blocking(move || {
                    crate::xml_login::sync_c69_log_by_query(&user, &action_log, Some(0));
                })
                .await;
            }
        }
        info!("TikTok XML Nurture session finished for device {} (completed={})", serial, completed);
    }

    /// TikTok đã được cài trên máy chưa (pm list packages).
    fn is_tiktok_installed(&self, adb_path: &Path, serial: &str) -> bool {
        let mut cmd = std::process::Command::new(adb_path);
        cmd.args(["-s", serial, "shell", "pm list packages com.zhiliaoapp.musically"]);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000);
        }
        match cmd.output() {
            Ok(o) => {
                let s = String::from_utf8_lossy(&o.stdout);
                s.contains("com.zhiliaoapp.musically")
            }
            Err(_) => true,
        }
    }

    /// App đang ở foreground có phải TikTok không (dumpsys window mCurrentFocus).
    fn is_tiktok_foreground(&self, adb_path: &Path, serial: &str) -> bool {
        let mut cmd = std::process::Command::new(adb_path);
        cmd.args(["-s", serial, "shell", "dumpsys window | grep mCurrentFocus"]);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000);
        }
        match cmd.output() {
            Ok(o) => {
                let s = String::from_utf8_lossy(&o.stdout);
                // Không đọc được focus (rỗng) thì coi như ổn để khỏi mở lại vô ích.
                s.trim().is_empty() || s.contains("com.zhiliaoapp.musically")
            }
            Err(_) => true,
        }
    }

    /// Xác minh tài khoản thật sự đã đăng nhập (guest -> like/comment/follow đều bị chặn bởi bảng đăng nhập).
    /// Mở tab Profile: có @username => đã login; có nút Log in/Sign up => guest. Trả về username ("" nếu không đọc được).
    async fn verify_logged_in(&self, adb_path: &Path, serial: &str, width: u32, height: u32) -> Result<String, String> {
        let nodes = dump_xml_nodes_async(adb_path, serial).await;
        if !nodes.is_empty() && !on_feed(&nodes) {
            return Err(format!("Không thấy feed TikTok — đang ở màn hình lạ: {}", first_texts(&nodes)));
        }
        let low = (height as i32) * 3 / 4;
        let prof = nodes
            .iter()
            .find(|n| n.bounds.2 > 0 && n.bounds.1 > low && (n.text.eq_ignore_ascii_case("profile") || n.desc.eq_ignore_ascii_case("profile")))
            .cloned();
        match prof {
            Some(p) => {
                let (x, y) = p.center();
                let _ = self.adb.tap(serial, x as u32, y as u32);
            }
            None => {
                let _ = self.adb.tap(serial, width * 9 / 10, height.saturating_sub(30));
            }
        }
        tokio::time::sleep(Duration::from_millis(2500)).await;
        let mut pn = dump_xml_nodes_async(adb_path, serial).await;
        if matches!(classify_screen(&pn), Screen::Captcha) {
            info!("[Nurture {}] Màn hình Profile đang bị che bởi Captcha Puzzle. Tự động giải...", serial);
            let _ = crate::captcha_solver::solve_if_present(adb_path, serial, width, height).await;
            tokio::time::sleep(Duration::from_millis(2000)).await;
            pn = dump_xml_nodes_async(adb_path, serial).await;
        }

        // Đóng các popup chào mừng/avatar/reconfirm nếu đang che tab Profile
        if pn.iter().any(|n| {
            let t = n.text.to_lowercase();
            t.contains("your avatar, your style") || t.contains("create your tiktok avatar") || t.contains("reconfirm email")
        }) {
            let _ = self.adb.keyevent(serial, 4);
            tokio::time::sleep(Duration::from_millis(1500)).await;
            pn = dump_xml_nodes_async(adb_path, serial).await;
        }

        let login_wall = matches!(classify_screen(&pn), Screen::LoggedOut);
        let user = pn.iter().find(|n| n.text.starts_with('@') && n.text.len() > 1).map(|n| n.text.trim().to_string()).unwrap_or_default();
        let guest = user.is_empty()
            && pn.iter().any(|n| {
                let t = n.text.trim().to_lowercase();
                t == "sign up" || t == "log in" || t.starts_with("sign up for") || t.starts_with("sign up to") || t == "log in or sign up"
            });
        // Trở về tab Home.
        let home = pn
            .iter()
            .find(|n| n.bounds.2 > 0 && n.bounds.1 > low && (n.text.eq_ignore_ascii_case("home") || n.desc.eq_ignore_ascii_case("home")))
            .cloned();
        if login_wall {
            let _ = self.adb.keyevent(serial, 4);
        }
        match home {
            Some(h) => {
                let (x, y) = h.center();
                let _ = self.adb.tap(serial, x as u32, y as u32);
            }
            None => {
                let _ = self.adb.tap(serial, 72, height.saturating_sub(30));
            }
        }
        tokio::time::sleep(Duration::from_millis(1500)).await;
        if login_wall || guest {
            return Err("TikTok chưa đăng nhập (đang ở chế độ khách) — cần login trước khi nuôi".to_string());
        }
        Ok(user)
    }
    fn finish_fatal(&self, serial: &str, reason: &str) {
        let mut lock = self.stats.write();
        if let Some(st) = lock.get_mut(serial) {
            st.status = "Lỗi".to_string();
            st.last_action = reason.to_string();
        }
        info!("TikTok nurture {} dừng do lỗi: {}", serial, reason);
    }

    fn set_action(&self, serial: &str, status: &str, action: String) {
        let mut lock = self.stats.write();
        if let Some(st) = lock.get_mut(serial) {
            st.status = status.to_string();
            st.last_action = action;
        }
    }

    /// Kiểm tra màn hình TikTok. No internet -> tự khôi phục (retry, bật Wi-Fi, mở lại app, chờ).
    /// Maximum attempts / bị đăng xuất / captcha -> tự xử lý hoặc báo lỗi nếu không khắc phục được.
    async fn ensure_healthy(&self, adb_path: &Path, serial: &str, first: Option<Vec<SimpleNode>>) -> Result<(), String> {
        let mut nodes = match first {
            Some(n) => n,
            None => dump_xml_nodes_async(adb_path, serial).await,
        };
        let mut attempt = 0u32;
        loop {
            match classify_screen(&nodes) {
                Screen::Ok => {
                    if attempt > 0 {
                        self.set_action(serial, "Watching FYP", format!("Đã khôi phục mạng sau {} lần thử ✅", attempt));
                    }
                    return Ok(());
                }
                Screen::RateLimit => return Err("Maximum number of attempts reached — TikTok khoá tạm thời, cần đổi IP/chờ 1h".into()),
                Screen::LoggedOut => return Err("TikTok đang ở màn hình đăng nhập (chưa login/bị đăng xuất)".into()),
                Screen::Captcha => {
                    self.set_action(serial, "Solving Captcha", "Phát hiện Captcha Puzzle — đang tự giải...".into());
                    match crate::captcha_solver::solve_if_present(adb_path, serial, 720, 1480).await {
                        Ok(true) => {
                            self.set_action(serial, "Captcha OK", "Đã tự giải xong Captcha Puzzle ✅".into());
                            tokio::time::sleep(Duration::from_millis(1500)).await;
                            nodes = dump_xml_nodes_async(adb_path, serial).await;
                            continue;
                        }
                        Ok(false) => {
                            nodes = dump_xml_nodes_async(adb_path, serial).await;
                            continue;
                        }
                        Err(e) => {
                            return Err(format!("Không thể giải Captcha: {}", e));
                        }
                    }
                }
                Screen::NoInternet => {
                    attempt += 1;
                    if attempt > 4 {
                        return Err("No internet connection kéo dài — kiểm tra Wi-Fi/proxy của máy".into());
                    }
                    self.set_action(serial, "No internet", format!("No internet — thử khôi phục {}/4", attempt));
                    match attempt {
                        1 => {
                            self.tap_retry(&nodes, serial);
                            tokio::time::sleep(Duration::from_secs(5)).await;
                        }
                        2 => {
                            // Đảm bảo máy ở đúng Wi-Fi farm (tắt/bật Wi-Fi tới khi vào được).
                            let (ap, sr) = (adb_path.to_path_buf(), serial.to_string());
                            let _ = tokio::task::spawn_blocking(move || crate::xml_login::ensure_farm_wifi(&ap, &sr)).await;
                            self.tap_retry(&nodes, serial);
                            tokio::time::sleep(Duration::from_secs(6)).await;
                        }
                        3 => {
                            let _ = self.adb.force_stop(serial, "com.zhiliaoapp.musically");
                            tokio::time::sleep(Duration::from_millis(1200)).await;
                            let _ = self.adb.launch_app(serial, "com.zhiliaoapp.musically");
                            tokio::time::sleep(Duration::from_secs(9)).await;
                        }
                        _ => {
                            tokio::time::sleep(Duration::from_secs(20)).await;
                            let _ = self.adb.force_stop(serial, "com.zhiliaoapp.musically");
                            tokio::time::sleep(Duration::from_millis(1200)).await;
                            let _ = self.adb.launch_app(serial, "com.zhiliaoapp.musically");
                            tokio::time::sleep(Duration::from_secs(10)).await;
                        }
                    }
                    if !self.is_running.load(Ordering::Relaxed) {
                        return Ok(());
                    }
                    nodes = dump_xml_nodes_async(adb_path, serial).await;
                }
            }
        }
    }

    fn tap_retry(&self, nodes: &[SimpleNode], serial: &str) {
        for n in nodes {
            let t = n.text.trim().to_lowercase();
            let d = n.desc.trim().to_lowercase();
            let hit = |s: &str| matches!(s, "retry" | "try again" | "refresh" | "reload" | "tap to retry" | "tap to refresh" | "ok" | "got it");
            if (hit(&t) || hit(&d)) && n.bounds.2 > 0 {
                let (cx, cy) = n.center();
                let _ = self.adb.tap(serial, cx as u32, cy as u32);
                return;
            }
        }
    }

    /// Tự động quét XML để phát hiện và đóng mọi popup cản trở trên FYP
    async fn dismiss_feed_popups(&self, adb_path: &Path, serial: &str) {
        let nodes = dump_xml_nodes_async(adb_path, serial).await;
        for n in &nodes {
            let t = n.text.to_lowercase();
            let d = n.desc.to_lowercase();
            if t == "not now" || t == "skip" || t == "later" || t == "no thanks" || t == "cancel" || t == "dismiss"
                || d == "not now" || d == "skip" || d == "dismiss" || d == "close" || t == "lúc khác"
            {
                let (cx, cy) = n.center();
                let _ = self.adb.tap(serial, cx as u32, cy as u32);
                tokio::time::sleep(Duration::from_millis(600)).await;
                break;
            }
        }
    }

    async fn generate_comment(&self, config: &NurtureConfig) -> String {
        let fallbacks = [
            "Nice video! 🔥",
            "Love this content ❤️",
            "Great tips 👍",
            "Amazing! 😁",
            "So helpful, thanks!",
            "Really well done! 👏",
            "Thanks for sharing! 🔥",
        ];

        if config.gemini_api_key.trim().is_empty() {
            let mut rng = rand::thread_rng();
            return fallbacks[rng.gen_range(0..fallbacks.len())].to_string();
        }

        let prompt = format!(
            "Hãy viết một câu bình luận ngắn tiếng Anh (dưới 8 từ) tự nhiên như người dùng Mỹ khen ngợi video TikTok về chủ đề {}. Không dùng ngoặc kép, không giải thích.",
            config.video_niche
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
        if let Ok(resp) = client.post(&url).json(&body).timeout(Duration::from_secs(4)).send().await {
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
