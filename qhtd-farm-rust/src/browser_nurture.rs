use crate::api::BrowserProfile;
use crate::cdp_browser::{get_free_port, launch_cdp_profile};
use futures_util::{SinkExt, StreamExt};
use parking_lot::{Mutex, RwLock};
use rand::Rng;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
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

// ── Native Rust CDP Client ───────────────────────────────────────────────────

#[derive(Clone)]
pub struct CdpClient {
    tx: tokio::sync::mpsc::Sender<Message>,
    pending: Arc<Mutex<HashMap<u64, tokio::sync::oneshot::Sender<serde_json::Value>>>>,
    counter: Arc<AtomicU64>,
}

impl CdpClient {
    pub async fn connect(ws_url: &str) -> Result<Self, String> {
        let (ws_stream, _) = tokio_tungstenite::connect_async(ws_url)
            .await
            .map_err(|e| format!("Lỗi kết nối WebSocket CDP ({}): {}", ws_url, e))?;

        let (mut write, mut read) = ws_stream.split();
        let (tx, mut rx) = tokio::sync::mpsc::channel::<Message>(64);
        let pending: Arc<Mutex<HashMap<u64, tokio::sync::oneshot::Sender<serde_json::Value>>>> = Arc::new(Mutex::new(HashMap::new()));
        let pending_clone = pending.clone();

        // Writer task
        tokio::spawn(async move {
            while let Some(msg) = rx.recv().await {
                if write.send(msg).await.is_err() {
                    break;
                }
            }
        });

        // Reader task
        tokio::spawn(async move {
            while let Some(Ok(msg)) = read.next().await {
                if let Message::Text(text) = msg {
                    if let Ok(v) = serde_json::from_str::<serde_json::Value>(&text) {
                        if let Some(id) = v.get("id").and_then(|i| i.as_u64()) {
                            if let Some(sender) = pending_clone.lock().remove(&id) {
                                let _ = sender.send(v);
                            }
                        }
                    }
                }
            }
        });

        let client = Self {
            tx,
            pending,
            counter: Arc::new(AtomicU64::new(10)),
        };

        // Kích hoạt các domain cần thiết
        let _ = client.call("Page.enable", json!({})).await;
        let _ = client.call("Runtime.enable", json!({})).await;

        Ok(client)
    }

    pub async fn call(&self, method: &str, params: serde_json::Value) -> Result<serde_json::Value, String> {
        let id = self.counter.fetch_add(1, Ordering::SeqCst);
        let (tx, rx) = tokio::sync::oneshot::channel();
        self.pending.lock().insert(id, tx);

        let msg = json!({
            "id": id,
            "method": method,
            "params": params
        });

        self.tx
            .send(Message::Text(msg.to_string()))
            .await
            .map_err(|e| format!("Lỗi gửi lệnh CDP {}: {}", method, e))?;

        match tokio::time::timeout(Duration::from_secs(8), rx).await {
            Ok(Ok(resp)) => Ok(resp),
            Ok(Err(_)) => Err("CDP channel closed".to_string()),
            Err(_) => {
                self.pending.lock().remove(&id);
                Err(format!("CDP Command '{}' timeout 8s", method))
            }
        }
    }

    pub async fn evaluate(&self, expr: &str) -> Result<serde_json::Value, String> {
        let resp = self
            .call(
                "Runtime.evaluate",
                json!({
                    "expression": expr,
                    "returnByValue": true,
                    "awaitPromise": true
                }),
            )
            .await?;

        let val = resp
            .get("result")
            .and_then(|r| r.get("result"))
            .and_then(|res| res.get("value"))
            .cloned()
            .unwrap_or(serde_json::Value::Null);

        Ok(val)
    }

    pub async fn navigate(&self, url: &str) -> Result<(), String> {
        self.call("Page.navigate", json!({ "url": url })).await?;
        Ok(())
    }

    pub async fn insert_text(&self, text: &str) -> Result<(), String> {
        self.call("Input.insertText", json!({ "text": text })).await?;
        Ok(())
    }

    pub async fn dispatch_mouse_click(&self, x: f64, y: f64) -> Result<(), String> {
        self.call(
            "Input.dispatchMouseEvent",
            json!({ "type": "mouseMoved", "x": x, "y": y }),
        )
        .await?;
        tokio::time::sleep(Duration::from_millis(60)).await;

        self.call(
            "Input.dispatchMouseEvent",
            json!({ "type": "mousePressed", "button": "left", "clickCount": 1, "x": x, "y": y }),
        )
        .await?;
        tokio::time::sleep(Duration::from_millis(80)).await;

        self.call(
            "Input.dispatchMouseEvent",
            json!({ "type": "mouseReleased", "button": "left", "clickCount": 1, "x": x, "y": y }),
        )
        .await?;
        Ok(())
    }

    pub async fn press_key(&self, key: &str, code: &str, vk: i32) -> Result<(), String> {
        self.call(
            "Input.dispatchKeyEvent",
            json!({ "type": "rawKeyDown", "windowsVirtualKeyCode": vk, "key": key, "code": code }),
        )
        .await?;
        tokio::time::sleep(Duration::from_millis(60)).await;

        self.call(
            "Input.dispatchKeyEvent",
            json!({ "type": "keyUp", "windowsVirtualKeyCode": vk, "key": key, "code": code }),
        )
        .await?;
        Ok(())
    }
}

// ── Browser Nurture Engine ───────────────────────────────────────────────────

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

        let c69_user = c69_acc
            .as_ref()
            .map(|a| a.username.clone())
            .unwrap_or_else(|| {
                profile
                    .tiktok_username
                    .clone()
                    .unwrap_or_else(|| "Tài khoản lưu sẵn".to_string())
            });

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
        mut c69_acc: Option<C69Account>,
        run_flag: Arc<AtomicBool>,
    ) {
        let pid = profile.id;
        let port = get_free_port(9222 + (pid as u16 % 500));

        // 1. Khởi chạy Profile Pure Rust CDP Browser
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

        // 3. Kết nối WebSocket CDP Client
        let cdp = match CdpClient::connect(&ws_url).await {
            Ok(c) => c,
            Err(e) => {
                self.set_error(pid, e);
                return;
            }
        };

        // Nếu chưa có c69_acc truyền vào nhưng profile đã gắn tiktok_username, thử tìm tài khoản C69 khớp
        if c69_acc.is_none() {
            if let Some(ref saved_u) = profile.tiktok_username {
                if let Ok(accounts) = fetch_c69_tiktok_accounts().await {
                    c69_acc = accounts.into_iter().find(|a| a.username == *saved_u);
                }
            }
        }

        // 4. KIỂM TRA ĐĂNG NHẬP TIKTOK NGHIÊM NGẶT
        self.update_log(pid, "Mở TikTok để kiểm tra phiên đăng nhập...".to_string(), "Kiểm tra đăng nhập");
        let _ = cdp.navigate("https://www.tiktok.com").await;
        tokio::time::sleep(Duration::from_secs(5)).await;
        if !run_flag.load(Ordering::Relaxed) { return; }

        // Kiểm tra xem đã đăng nhập chưa
        let check_session_expr = r#"(() => {
            const hasCookie = document.cookie.includes('sessionid=');
            const hasAvatar = !!(
                document.querySelector('[data-e2e="profile-icon"]') || 
                document.querySelector('img[alt*="avatar"]') || 
                document.querySelector('a[href*="/@"]') ||
                document.querySelector('[data-e2e="inbox-icon"]')
            );
            return hasCookie || hasAvatar;
        })()"#;

        let already_logged_in = cdp.evaluate(check_session_expr).await.ok()
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        if already_logged_in {
            self.update_log(pid, "✅ Phát hiện phiên đăng nhập TikTok có sẵn trong profile! Sẵn sàng vào FYP...".to_string(), "Đã đăng nhập");
            tokio::time::sleep(Duration::from_secs(2)).await;
        } else {
            // Chưa đăng nhập -> Cần thực hiện quy trình đăng nhập bằng tài khoản C69
            let acc = match &c69_acc {
                Some(a) if a.password.as_deref().unwrap_or("").trim().len() > 0 => a,
                _ => {
                    self.set_error(pid, "❌ Profile chưa đăng nhập TikTok và chưa được gắn tài khoản C69 hợp lệ! Vui lòng chọn tài khoản có mật khẩu để tự động đăng nhập.".to_string());
                    return;
                }
            };

            let pwd = acc.password.as_deref().unwrap_or("");
            self.update_log(pid, format!("Mở trang đăng nhập TikTok cho tài khoản C69: {}", acc.username), "Tiến hành đăng nhập");

            let _ = cdp.navigate("https://www.tiktok.com/login/phone-or-email/email?lang=en").await;
            tokio::time::sleep(Duration::from_secs(6)).await;
            if !run_flag.load(Ordering::Relaxed) { return; }

            // Nhập Username
            let find_user_expr = r#"(() => {
                const u = document.querySelector('input[name="username"]') || 
                          document.querySelector('input[placeholder*="Email"]') || 
                          document.querySelector('input[placeholder*="Username"]') ||
                          document.querySelector('input[type="text"]');
                if (u) {
                    u.focus();
                    u.click();
                    const r = u.getBoundingClientRect();
                    return JSON.stringify({x: r.left + r.width/2, y: r.top + r.height/2});
                }
                return '';
            })()"#;

            let user_pos = cdp.evaluate(find_user_expr).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
            if !user_pos.is_empty() {
                if let Ok(c) = serde_json::from_str::<serde_json::Value>(&user_pos) {
                    let x = c.get("x").and_then(|v| v.as_f64()).unwrap_or(200.0);
                    let y = c.get("y").and_then(|v| v.as_f64()).unwrap_or(280.0);
                    let _ = cdp.dispatch_mouse_click(x, y).await;
                }
            }
            tokio::time::sleep(Duration::from_millis(300)).await;
            let _ = cdp.insert_text(&acc.username).await;
            tokio::time::sleep(Duration::from_millis(600)).await;
            if !run_flag.load(Ordering::Relaxed) { return; }

            // Nhập Password
            let find_pwd_expr = r#"(() => {
                const p = document.querySelector('input[type="password"]');
                if (p) {
                    p.focus();
                    p.click();
                    const r = p.getBoundingClientRect();
                    return JSON.stringify({x: r.left + r.width/2, y: r.top + r.height/2});
                }
                return '';
            })()"#;

            let pwd_pos = cdp.evaluate(find_pwd_expr).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
            if !pwd_pos.is_empty() {
                if let Ok(c) = serde_json::from_str::<serde_json::Value>(&pwd_pos) {
                    let x = c.get("x").and_then(|v| v.as_f64()).unwrap_or(200.0);
                    let y = c.get("y").and_then(|v| v.as_f64()).unwrap_or(330.0);
                    let _ = cdp.dispatch_mouse_click(x, y).await;
                }
            }
            tokio::time::sleep(Duration::from_millis(300)).await;
            let _ = cdp.insert_text(pwd).await;
            tokio::time::sleep(Duration::from_millis(800)).await;
            if !run_flag.load(Ordering::Relaxed) { return; }

            // Lấy tọa độ nút Log In thật và click
            let find_btn_expr = r#"(() => {
                const btn = document.querySelector('button[type="submit"]') || 
                            Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase().includes('log in'));
                if (btn) {
                    const r = btn.getBoundingClientRect();
                    return JSON.stringify({x: r.left + r.width/2, y: r.top + r.height/2});
                }
                return '';
            })()"#;

            let btn_pos = cdp.evaluate(find_btn_expr).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
            if !btn_pos.is_empty() {
                if let Ok(c) = serde_json::from_str::<serde_json::Value>(&btn_pos) {
                    let x = c.get("x").and_then(|v| v.as_f64()).unwrap_or(200.0);
                    let y = c.get("y").and_then(|v| v.as_f64()).unwrap_or(390.0);
                    let _ = cdp.dispatch_mouse_click(x, y).await;
                }
            } else {
                let _ = cdp.dispatch_mouse_click(200.0, 390.0).await;
            }

            self.update_log(pid, format!("Đã kích hoạt bấm nút Đăng Nhập cho: {}. Đang xác thực...", acc.username), "Chờ xác thực đăng nhập");

            // ── VÒNG LẶP XÁC THỰC ĐĂNG NHẬP (Login Verification Loop - tối đa 60 giây) ──
            let mut login_confirmed = false;
            for sec in 1..=30 {
                if !run_flag.load(Ordering::Relaxed) { return; }
                tokio::time::sleep(Duration::from_secs(2)).await;

                // Kiểm tra Captcha
                let captcha_expr = r#"(() => {
                    const c = document.querySelector('#captcha_container') || 
                              document.querySelector('.secsdk-captcha-drag-icon') || 
                              document.querySelector('[class*="captcha"]') || 
                              document.querySelector('.verify-wrap') || 
                              document.querySelector('iframe[src*="captcha"]');
                    return !!c;
                })()"#;
                let has_captcha = cdp.evaluate(captcha_expr).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);
                if has_captcha {
                    self.update_log(
                        pid, 
                        format!("⚠️ Phát hiện Captcha TikTok! Vui lòng kéo captcha trên cửa sổ trình duyệt (chu kỳ {}/30)...", sec), 
                        "Chờ giải Captcha"
                    );
                }

                // Kiểm tra thông báo lỗi
                let err_expr = r#"(() => {
                    const err = document.querySelector('.tiktok-input-error') || 
                                document.querySelector('[role="alert"]') || 
                                document.querySelector('[class*="error-container"]') ||
                                document.querySelector('[class*="error-message"]');
                    return err ? err.innerText.trim() : '';
                })()"#;
                let err_text = cdp.evaluate(err_expr).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
                if !err_text.is_empty() {
                    self.set_error(pid, format!("❌ Đăng nhập TikTok thất bại: {}", err_text));
                    return;
                }

                // Kiểm tra đăng nhập thành công
                let login_ok_expr = r#"(() => {
                    const hasCookie = document.cookie.includes('sessionid=');
                    const hasAvatar = !!(
                        document.querySelector('[data-e2e="profile-icon"]') || 
                        document.querySelector('img[alt*="avatar"]') || 
                        document.querySelector('a[href*="/@"]') ||
                        document.querySelector('[data-e2e="inbox-icon"]')
                    );
                    const notInLogin = !window.location.href.includes('/login');
                    return (hasCookie || hasAvatar) && notInLogin;
                })()"#;
                let is_ok = cdp.evaluate(login_ok_expr).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);
                if is_ok {
                    login_confirmed = true;
                    break;
                }
            }

            if !login_confirmed {
                self.set_error(
                    pid, 
                    "❌ Đăng nhập TikTok thất bại: Hết thời gian chờ (Timeout 60s) hoặc chưa vượt qua Captcha. Hệ thống dừng lại, không chuyển qua lướt video.".to_string()
                );
                return;
            }

            self.update_log(pid, "🎉 Đăng nhập TikTok thành công 100%! Đang chuyển sang Feed FYP...".to_string(), "Đăng nhập thành công");
            tokio::time::sleep(Duration::from_secs(3)).await;
        }

        // 5. ĐIỀU HƯỚNG TỚI FEED FYP (FOR YOU PAGE)
        self.update_log(pid, "Mở trang video For You Page (FYP) để bắt đầu nuôi tương tác...".to_string(), "Vào FYP Feed");
        let _ = cdp.navigate("https://www.tiktok.com/foryou?lang=en").await;
        tokio::time::sleep(Duration::from_secs(6)).await;

        // 6. VÒNG LẶP NUÔI TƯƠNG TÁC FYP (Human-Behavior Simulation)
        let mut watched_count = 0u32;
        let mut likes_count = 0u32;

        while run_flag.load(Ordering::Relaxed) {
            watched_count += 1;
            let watch_seconds = rand::thread_rng().gen_range(8..22);

            self.update_stats(
                pid, 
                watched_count, 
                likes_count, 
                format!("Đang xem video FYP #{} ({} giây)...", watched_count, watch_seconds), 
                "Đang lướt FYP"
            );

            for _ in 0..watch_seconds {
                if !run_flag.load(Ordering::Relaxed) { break; }
                tokio::time::sleep(Duration::from_secs(1)).await;
            }
            if !run_flag.load(Ordering::Relaxed) { break; }

            // 65% xác suất thả tim (Like) bằng phím tắt 'L'
            let will_like = rand::thread_rng().gen_bool(0.65);
            if will_like {
                likes_count += 1;
                let _ = cdp.press_key("l", "KeyL", 76).await;
                self.update_stats(
                    pid, 
                    watched_count, 
                    likes_count, 
                    format!("❤️ Đã thả tim video #{}!", watched_count), 
                    "Đang lướt FYP"
                );
                tokio::time::sleep(Duration::from_millis(800)).await;
            }

            // Chuyển sang video kế tiếp bằng phím mũi tên xuống (ArrowDown)
            self.update_log(pid, "👆 Vuốt lướt sang video tiếp theo...".to_string(), "Chuyển video");
            let _ = cdp.press_key("ArrowDown", "ArrowDown", 40).await;

            tokio::time::sleep(Duration::from_secs(2)).await;
        }

        // Hoàn tất hoặc dừng
        self.update_log(
            pid, 
            format!("Chu trình nuôi hoàn tất. Tổng đã xem: {} video, thả tim: {} lượt.", watched_count, likes_count), 
            "Đã dừng"
        );
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
    let url = format!("{}/dashboard/api/accounts/?type=tiktok&page_size=100", DEFAULT_C69_API_URL);

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
    for item in results {
        let name = item.get("profile_name").and_then(|v| v.as_str()).unwrap_or("C69 Profile");
        let ua = item.get("profile_user_agent").and_then(|v| v.as_str()).unwrap_or("");
        let os = item.get("profile_os").and_then(|v| v.as_str()).unwrap_or("Windows");
        let res = item.get("profile_resolution").and_then(|v| v.as_str()).unwrap_or("1920x1080");
        let cpu = item.get("profile_cpu").and_then(|v| v.as_u64()).unwrap_or(8) as u32;
        let proxy = item.get("profile_socks5_details").and_then(|v| v.as_str()).unwrap_or("");

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
                tiktok_account_id: None,
                tiktok_username: None,
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
