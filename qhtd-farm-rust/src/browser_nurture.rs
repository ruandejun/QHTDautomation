use crate::api::BrowserProfile;
use crate::cdp_browser::{get_free_port, launch_cdp_profile};
use futures_util::{SinkExt, StreamExt};
use parking_lot::RwLock;
use rand::Rng;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio_tungstenite::tungstenite::protocol::Message;
use tracing::{error, info};

pub const DEFAULT_C69_API_URL: &str = "https://cu.c69.us";
pub const DEFAULT_C69_TOKEN: &str = "Token 99b02d3d255a49193950777b1cc3e3db099ceefb";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct C69Account {
    pub id: u64,
    pub username: String,
    #[serde(default)]
    pub password: Option<String>,
    #[serde(default)]
    pub status: Option<String>,
    #[serde(default)]
    pub note: Option<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserNurtureStatus {
    pub profile_id: usize,
    pub profile_name: String,
    pub c69_username: String,
    pub status: String,
    pub videos_watched: u32,
    pub likes_given: u32,
    pub is_running: bool,
    pub last_log: String,
}

#[derive(Clone)]
pub struct BrowserNurtureEngine {
    tasks: Arc<RwLock<HashMap<usize, Arc<AtomicBool>>>>,
    statuses: Arc<RwLock<HashMap<usize, BrowserNurtureStatus>>>,
}

impl BrowserNurtureEngine {
    pub fn new() -> Self {
        Self {
            tasks: Arc::new(RwLock::new(HashMap::new())),
            statuses: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn get_all_statuses(&self) -> Vec<BrowserNurtureStatus> {
        self.statuses.read().values().cloned().collect()
    }

    pub fn get_status(&self, profile_id: usize) -> Option<BrowserNurtureStatus> {
        self.statuses.read().get(&profile_id).cloned()
    }

    pub fn is_profile_running(&self, profile_id: usize) -> bool {
        if let Some(flag) = self.tasks.read().get(&profile_id) {
            flag.load(Ordering::Relaxed)
        } else {
            false
        }
    }

    pub fn stop_nurture(&self, profile_id: usize) {
        if let Some(flag) = self.tasks.read().get(&profile_id) {
            flag.store(false, Ordering::Relaxed);
        }
        if let Some(st) = self.statuses.write().get_mut(&profile_id) {
            st.is_running = false;
            st.status = "Đã dừng".to_string();
            st.last_log = "Người dùng yêu cầu dừng nuôi.".to_string();
        }
        info!("🛑 [Mun Anti Browser] Đã yêu cầu dừng nuôi TikTok cho Profile #{}", profile_id);
    }

    pub fn stop_all(&self) {
        let keys: Vec<usize> = self.tasks.read().keys().cloned().collect();
        for id in keys {
            self.stop_nurture(id);
        }
    }

    pub async fn start_nurture(
        &self,
        profile: BrowserProfile,
        c69_acc: Option<C69Account>,
    ) -> Result<(), String> {
        let profile_id = profile.id;
        if self.is_profile_running(profile_id) {
            return Err(format!("Profile #{} đang chạy nuôi TikTok rồi!", profile_id));
        }

        let run_flag = Arc::new(AtomicBool::new(true));
        self.tasks.write().insert(profile_id, run_flag.clone());

        let c69_user = c69_acc.as_ref().map(|a| a.username.clone()).unwrap_or_else(|| "Tài khoản lưu sẵn".to_string());
        let initial_status = BrowserNurtureStatus {
            profile_id,
            profile_name: profile.name.clone(),
            c69_username: c69_user.clone(),
            status: "Đang khởi động Anti-Browser...".to_string(),
            videos_watched: 0,
            likes_given: 0,
            is_running: true,
            last_log: "Bắt đầu chu trình nuôi TikTok kết hợp C69...".to_string(),
        };
        self.statuses.write().insert(profile_id, initial_status);

        let engine = self.clone();
        tokio::spawn(async move {
            engine.run_nurture_worker(profile, c69_acc, run_flag).await;
        });

        Ok(())
    }

    async fn run_nurture_worker(
        &self,
        profile: BrowserProfile,
        c69_acc: Option<C69Account>,
        run_flag: Arc<AtomicBool>,
    ) {
        let pid = profile.id;
        let port = get_free_port(9222 + (pid as u16 % 500));

        // 1. Khởi chạy Profile Pure Rust CDP
        self.update_log(pid, "Đang nạp trình duyệt Anti-Detect với Mobile & C++ Shield...".to_string(), "Khởi động browser");
        if let Err(e) = launch_cdp_profile(&profile).await {
            self.set_error(pid, format!("Lỗi khởi chạy browser: {}", e));
            return;
        }

        // 2. Chờ CDP Port sẵn sàng
        let mut target_ws_url = None;
        for attempt in 1..=20 {
            if !run_flag.load(Ordering::Relaxed) { return; }
            tokio::time::sleep(Duration::from_millis(600)).await;

            let url = format!("http://127.0.0.1:{}/json/list", port);
            if let Ok(resp) = reqwest::get(&url).await {
                if let Ok(targets) = resp.json::<Vec<serde_json::Value>>().await {
                    for t in targets {
                        if t.get("type").and_then(|v| v.as_str()) == Some("page") {
                            if let Some(ws) = t.get("webSocketDebuggerUrl").and_then(|v| v.as_str()) {
                                target_ws_url = Some(ws.to_string());
                                break;
                            }
                        }
                    }
                }
            }
            if target_ws_url.is_some() { break; }
            self.update_log(pid, format!("Đang tìm kiếm tab Chrome (lần {}/20)...", attempt), "Chờ kết nối");
        }

        let ws_url = match target_ws_url {
            Some(u) => u,
            None => {
                self.set_error(pid, format!("Không tìm thấy tab Chrome trên cổng {}", port));
                return;
            }
        };

        // 3. Kết nối WebSocket CDP
        let (ws_stream, _) = match tokio_tungstenite::connect_async(&ws_url).await {
            Ok(conn) => conn,
            Err(e) => {
                self.set_error(pid, format!("Lỗi kết nối WebSocket CDP: {}", e));
                return;
            }
        };

        let (mut write, _read) = ws_stream.split();
        let mut msg_id = 1u64;

        // Bật domains Page và Runtime
        msg_id += 1;
        let _ = write.send(Message::Text(json!({ "id": msg_id, "method": "Page.enable" }).to_string())).await;
        msg_id += 1;
        let _ = write.send(Message::Text(json!({ "id": msg_id, "method": "Runtime.enable" }).to_string())).await;

        // 4. Nếu có thông tin C69 Account, kiểm tra và tự động đăng nhập nếu chưa login
        if let Some(acc) = &c69_acc {
            if let Some(pwd) = &acc.password {
                if !pwd.trim().is_empty() {
                    self.update_log(pid, format!("Điều hướng tới trang đăng nhập TikTok cho tài khoản C69 ({})", acc.username), "Đăng nhập C69");
                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Page.navigate",
                        "params": { "url": "https://www.tiktok.com/login/phone-or-email/email?lang=en" }
                    }).to_string())).await;

                    tokio::time::sleep(Duration::from_secs(6)).await;
                    if !run_flag.load(Ordering::Relaxed) { return; }

                    // Gõ username qua CDP
                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "(() => { const u = document.querySelector('input[name=\"username\"]') || document.querySelector('input[placeholder*=\"Email\"]') || document.querySelector('input[type=\"text\"]'); if (u) { u.focus(); u.click(); } })()"
                        }
                    }).to_string())).await;
                    tokio::time::sleep(Duration::from_millis(300)).await;

                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Input.insertText",
                        "params": { "text": acc.username }
                    }).to_string())).await;
                    tokio::time::sleep(Duration::from_millis(500)).await;

                    // Gõ password qua CDP
                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "(() => { const p = document.querySelector('input[type=\"password\"]'); if (p) { p.focus(); p.click(); } })()"
                        }
                    }).to_string())).await;
                    tokio::time::sleep(Duration::from_millis(300)).await;

                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Input.insertText",
                        "params": { "text": pwd }
                    }).to_string())).await;
                    tokio::time::sleep(Duration::from_millis(800)).await;

                    // Click chuột thật vào nút Log in
                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Runtime.evaluate",
                        "params": {
                            "expression": "(() => { const btn = document.querySelector('button[type=\"submit\"]') || Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase() === 'log in'); if (btn) { const r = btn.getBoundingClientRect(); return JSON.stringify({x: r.left + r.width/2, y: r.top + r.height/2}); } return '{}'; })()",
                            "returnByValue": true
                        }
                    }).to_string())).await;

                    // Real Mouse Click
                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Input.dispatchMouseEvent",
                        "params": { "type": "mouseMoved", "x": 200, "y": 380 }
                    }).to_string())).await;
                    tokio::time::sleep(Duration::from_millis(100)).await;

                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Input.dispatchMouseEvent",
                        "params": { "type": "mousePressed", "button": "left", "clickCount": 1, "x": 200, "y": 380 }
                    }).to_string())).await;
                    tokio::time::sleep(Duration::from_millis(100)).await;

                    msg_id += 1;
                    let _ = write.send(Message::Text(json!({
                        "id": msg_id,
                        "method": "Input.dispatchMouseEvent",
                        "params": { "type": "mouseReleased", "button": "left", "clickCount": 1, "x": 200, "y": 380 }
                    }).to_string())).await;

                    self.update_log(pid, format!("Đã kích hoạt click đăng nhập cho tài khoản C69: {}", acc.username), "Chờ TikTok xác thực");
                    tokio::time::sleep(Duration::from_secs(6)).await;
                }
            }
        }

        // 5. Điều hướng tới Feed FYP For You
        self.update_log(pid, "Mở trang video For You Page (FYP) để bắt đầu nuôi tương tác...".to_string(), "Vào FYP Feed");
        msg_id += 1;
        let _ = write.send(Message::Text(json!({
            "id": msg_id,
            "method": "Page.navigate",
            "params": { "url": "https://www.tiktok.com/foryou?lang=en" }
        }).to_string())).await;
        tokio::time::sleep(Duration::from_secs(5)).await;

        // 6. Vòng lặp nuôi tương tác FYP (Human-Behavior Simulation)
        let mut watched_count = 0u32;
        let mut likes_count = 0u32;

        while run_flag.load(Ordering::Relaxed) {
            watched_count += 1;
            let watch_seconds = rand::thread_rng().gen_range(8..22);

            self.update_stats(pid, watched_count, likes_count, format!("Đang xem video #{} ({} giây)...", watched_count, watch_seconds), "Đang lướt FYP");

            // Xem từng đoạn nhỏ để đáp ứng tín hiệu dừng nhanh nhạy
            for _ in 0..watch_seconds {
                if !run_flag.load(Ordering::Relaxed) { break; }
                tokio::time::sleep(Duration::from_secs(1)).await;
            }
            if !run_flag.load(Ordering::Relaxed) { break; }

            // 65% xác suất thả tim (Like)
            let will_like = rand::thread_rng().gen_bool(0.65);
            if will_like {
                likes_count += 1;
                // Nhấn phím 'l' trên bàn phím (phím tắt mặc định của TikTok Web để Like video)
                msg_id += 1;
                let _ = write.send(Message::Text(json!({
                    "id": msg_id,
                    "method": "Input.dispatchKeyEvent",
                    "params": { "type": "rawKeyDown", "windowsVirtualKeyCode": 76, "key": "l", "code": "KeyL" }
                }).to_string())).await;
                tokio::time::sleep(Duration::from_millis(50)).await;

                msg_id += 1;
                let _ = write.send(Message::Text(json!({
                    "id": msg_id,
                    "method": "Input.dispatchKeyEvent",
                    "params": { "type": "keyUp", "windowsVirtualKeyCode": 76, "key": "l", "code": "KeyL" }
                }).to_string())).await;

                self.update_stats(pid, watched_count, likes_count, format!("❤️ Đã thả tim video #{}!", watched_count), "Đang lướt FYP");
                tokio::time::sleep(Duration::from_millis(800)).await;
            }

            // Chuyển sang video kế tiếp (Phím mũi tên xuống hoặc Touch swipe up)
            self.update_log(pid, "👆 Vuốt lướt sang video tiếp theo...".to_string(), "Chuyển video");
            msg_id += 1;
            let _ = write.send(Message::Text(json!({
                "id": msg_id,
                "method": "Input.dispatchKeyEvent",
                "params": { "type": "rawKeyDown", "windowsVirtualKeyCode": 40, "key": "ArrowDown", "code": "ArrowDown" }
            }).to_string())).await;
            tokio::time::sleep(Duration::from_millis(80)).await;

            msg_id += 1;
            let _ = write.send(Message::Text(json!({
                "id": msg_id,
                "method": "Input.dispatchKeyEvent",
                "params": { "type": "keyUp", "windowsVirtualKeyCode": 40, "key": "ArrowDown", "code": "ArrowDown" }
            }).to_string())).await;

            tokio::time::sleep(Duration::from_secs(2)).await;
        }

        // Hoàn tất hoặc dừng
        self.update_log(pid, format!("Chu trình nuôi hoàn tất. Tổng đã xem: {} video, thả tim: {} lượt.", watched_count, likes_count), "Đã dừng");
        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.is_running = false;
            st.status = "Đã dừng".to_string();
        }
        run_flag.store(false, Ordering::Relaxed);
    }

    fn update_log(&self, pid: usize, log: String, status: &str) {
        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.last_log = log;
            st.status = status.to_string();
        }
    }

    fn update_stats(&self, pid: usize, watched: u32, likes: u32, log: String, status: &str) {
        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.videos_watched = watched;
            st.likes_given = likes;
            st.last_log = log;
            st.status = status.to_string();
        }
    }

    fn set_error(&self, pid: usize, err: String) {
        error!("❌ [Profile #{}] Lỗi nuôi TikTok: {}", pid, err);
        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.is_running = false;
            st.status = "Lỗi".to_string();
            st.last_log = err;
        }
        if let Some(f) = self.tasks.read().get(&pid) {
            f.store(false, Ordering::Relaxed);
        }
    }
}

/// Lấy danh sách tài khoản TikTok từ C69 Backend API
pub async fn fetch_c69_tiktok_accounts() -> Result<Vec<C69Account>, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/?type=tiktok&page_size=50", DEFAULT_C69_API_URL);

    let resp = client
        .get(&url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .timeout(Duration::from_secs(8))
        .send()
        .await
        .map_err(|e| format!("Lỗi kết nối server C69: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Server C69 trả về mã lỗi: {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi giải mã JSON C69: {}", e))?;
    let results = data.get("results").and_then(|v| v.as_array()).cloned().unwrap_or_default();

    let mut accounts = Vec::new();
    for item in results {
        if let Some(u) = item.get("username").and_then(|v| v.as_str()) {
            let id = item.get("id").and_then(|v| v.as_u64()).unwrap_or(0);
            let pwd = item.get("password").and_then(|v| v.as_str()).map(|s| s.to_string());
            let st = item.get("status").and_then(|v| v.as_str()).map(|s| s.to_string());
            let nt = item.get("note").and_then(|v| v.as_str()).map(|s| s.to_string());
            accounts.push(C69Account {
                id,
                username: u.to_string(),
                password: pwd,
                status: st,
                note: nt,
            });
        }
    }

    Ok(accounts)
}

/// Đồng bộ Profiles từ C69 Profile API và lưu vào browser_profiles.json
pub async fn sync_c69_profiles_to_local(profiles_path: PathBuf) -> Result<usize, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/profiles/?page_size=100", DEFAULT_C69_API_URL);

    let resp = client
        .get(&url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .timeout(Duration::from_secs(10))
        .send()
        .await
        .map_err(|e| format!("Lỗi kết nối C69 Profiles API: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("C69 Profiles API trả về lỗi: {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi đọc JSON C69: {}", e))?;
    let results = data.get("results").and_then(|v| v.as_array()).cloned().unwrap_or_default();

    if results.is_empty() {
        return Ok(0);
    }

    let mut local_profiles: Vec<BrowserProfile> = std::fs::read_to_string(&profiles_path)
        .ok()
        .and_then(|d| serde_json::from_str(&d).ok())
        .unwrap_or_default();

    let mut count_added = 0;
    for (idx, item) in results.iter().enumerate() {
        let name = item.get("profile_name").and_then(|v| v.as_str()).unwrap_or("C69 Profile");
        let ua = item.get("profile_user_agent").and_then(|v| v.as_str()).unwrap_or("");
        let os = item.get("profile_os").and_then(|v| v.as_str()).unwrap_or("Windows");
        let res = item.get("profile_resolution").and_then(|v| v.as_str()).unwrap_or("1920x1080");
        let cpu = item.get("profile_cpu").and_then(|v| v.as_u64()).unwrap_or(8) as u32;
        let proxy = item.get("profile_socks5_details").and_then(|v| v.as_str()).unwrap_or("");

        // Kiểm tra xem profile đã tồn tại theo tên chưa
        let exists = local_profiles.iter().any(|p| p.name == name);
        if !exists {
            let next_id = local_profiles.iter().map(|p| p.id).max().unwrap_or(0) + 1;
            local_profiles.push(BrowserProfile {
                id: next_id,
                name: name.to_string(),
                engine_mode: Some(if next_id % 2 == 0 { "native".into() } else { "js_stealth".into() }),
                profile_user_agent: ua.to_string(),
                profile_os: os.to_string(),
                profile_resolution: res.to_string(),
                profile_cpu: cpu as usize,
                profile_ram: 16,
                proxy_string: proxy.to_string(),
                proxy_type: if proxy.is_empty() { "".into() } else { "socks5".into() },
                profile_start_url: "https://www.tiktok.com".into(),
                canvas_seed: Some((next_id as u32 + 1).wrapping_mul(1664525) ^ 0x5a5a5a5a),
                audio_seed: Some((next_id as u32 + 1).wrapping_mul(1103515245) ^ 0xa5a5a5a5),
                webrtc_mode: Some("proxy_only".into()),
                profile_canvas: serde_json::Value::Null,
                profile_webgl: serde_json::Value::Null,
                profile_audio: serde_json::Value::Null,
                gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
                gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
            });
            count_added += 1;
        }
    }

    if count_added > 0 {
        if let Ok(json_str) = serde_json::to_string_pretty(&local_profiles) {
            let _ = std::fs::write(&profiles_path, json_str);
        }
    }

    Ok(count_added)
}
