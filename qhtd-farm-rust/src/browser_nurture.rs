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
    pub email: Option<String>,
    #[serde(default)]
    pub password: Option<String>,
    #[serde(default)]
    pub two_factor_auth: Option<String>,
    #[serde(default)]
    pub cookies: Option<String>,
    #[serde(default)]
    pub status: Option<serde_json::Value>,
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
    #[serde(default)]
    pub waiting_otp: bool,
    #[serde(default)]
    pub challenge_type: Option<String>,
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

    pub async fn get_all_cookies(&self) -> Result<serde_json::Value, String> {
        let resp = self.call("Network.getCookies", json!({ "urls": ["https://www.tiktok.com", "https://tiktok.com"] })).await?;
        let cookies = resp.get("result").and_then(|r| r.get("cookies")).cloned().unwrap_or(json!([]));
        Ok(cookies)
    }

    pub async fn set_cookies(&self, cookies: &serde_json::Value) -> Result<(), String> {
        if let Some(arr) = cookies.as_array() {
            for c in arr {
                let name = c.get("name").and_then(|v| v.as_str()).unwrap_or("");
                let value = c.get("value").and_then(|v| v.as_str()).unwrap_or("");
                let domain = c.get("domain").and_then(|v| v.as_str()).unwrap_or(".tiktok.com");
                let path = c.get("path").and_then(|v| v.as_str()).unwrap_or("/");
                if !name.is_empty() {
                    let _ = self.call("Network.setCookie", json!({
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": path,
                        "secure": true
                    })).await;
                }
            }
        }
        Ok(())
    }

    pub async fn set_cookies_from_string(&self, cookie_str: &str) -> Result<(), String> {
        let pairs: Vec<&str> = cookie_str.split(';').collect();
        for p in pairs {
            let trimmed = p.trim();
            if let Some((k, v)) = trimmed.split_once('=') {
                let k_trim = k.trim();
                let v_trim = v.trim();
                if !k_trim.is_empty() {
                    let _ = self.call("Network.setCookie", json!({
                        "name": k_trim,
                        "value": v_trim,
                        "domain": ".tiktok.com",
                        "path": "/",
                        "secure": true
                    })).await;
                }
            }
        }
        Ok(())
    }
}

// ── Browser Nurture Engine ───────────────────────────────────────────────────

#[derive(Clone)]
pub struct BrowserNurtureEngine {
    tasks: Arc<RwLock<HashMap<usize, Arc<AtomicBool>>>>,
    statuses: Arc<RwLock<HashMap<usize, BrowserNurtureStatus>>>,
    otp_queue: Arc<Mutex<HashMap<usize, String>>>,
}

impl BrowserNurtureEngine {
    pub fn new() -> Self {
        Self {
            tasks: Arc::new(RwLock::new(HashMap::new())),
            statuses: Arc::new(RwLock::new(HashMap::new())),
            otp_queue: Arc::new(Mutex::new(HashMap::new())),
        }
    }

    pub fn submit_otp(&self, profile_id: usize, otp: String) {
        self.otp_queue.lock().insert(profile_id, otp);
    }

    pub fn take_otp(&self, profile_id: usize) -> Option<String> {
        self.otp_queue.lock().remove(&profile_id)
    }

    pub fn update_challenge(&self, profile_id: usize, challenge_type: &str, log_msg: String) {
        if let Some(st) = self.statuses.write().get_mut(&profile_id) {
            st.waiting_otp = true;
            st.challenge_type = Some(challenge_type.to_string());
            st.status = format!("Chờ mã {}", challenge_type);
            st.last_log = log_msg;
        }
    }

    pub fn clear_challenge(&self, profile_id: usize) {
        if let Some(st) = self.statuses.write().get_mut(&profile_id) {
            st.waiting_otp = false;
            st.challenge_type = None;
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

        let now_epoch = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs())
            .unwrap_or(0);

        if let Some(retry_epoch) = profile.retry_after_epoch {
            if retry_epoch > now_epoch {
                let remain_mins = (retry_epoch - now_epoch + 59) / 60;
                return Err(format!(
                    "Profile #{} đang bị giới hạn đăng nhập (Maximum attempts). Vui lòng chờ thêm {} phút (đủ 1 giờ) trước khi login lại!",
                    profile_id, remain_mins
                ));
            }
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
            waiting_otp: false,
            challenge_type: None,
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

        // 1. Khởi chạy Profile Pure Rust CDP Browser với Proxy Shield
        let proxy_desc = if let Some(parsed) = crate::cdp_browser::parse_proxy_string(&profile.proxy_string) {
            let auth_tag = if parsed.username.is_some() { " (Auth OK)" } else { "" };
            format!("🛡️ Proxy: {}://{}:{}{}", parsed.scheme.to_uppercase(), parsed.host, parsed.port, auth_tag)
        } else {
            "⚡ Direct / Local Network".to_string()
        };

        self.update_log(
            pid,
            format!("Đang nạp Anti-Detect [{}] với Mobile & C++ Shield...", proxy_desc),
            "Khởi động browser"
        );
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

        // Nếu chưa có c69_acc truyền vào nhưng profile đã gắn tiktok_account_id hoặc tiktok_username, thử tìm tài khoản C69 khớp
        if c69_acc.is_none() {
            if let Some(aid) = profile.tiktok_account_id {
                if let Ok(acc) = fetch_c69_account_by_id(aid).await {
                    c69_acc = Some(acc);
                }
            }
        }
        if c69_acc.is_none() {
            if let Some(ref saved_u) = profile.tiktok_username {
                if let Ok(accounts) = fetch_c69_tiktok_accounts().await {
                    c69_acc = accounts.into_iter().find(|a| a.username.eq_ignore_ascii_case(saved_u));
                }
            }
        }

        // 4. KIỂM TRA & NẠP COOKIES NẾU CÓ
        if let Some(ref acc) = c69_acc {
            if let Some(ref c_str) = acc.cookies {
                let trimmed_c = c_str.trim();
                if !trimmed_c.is_empty() {
                    if let Ok(c_json) = serde_json::from_str::<serde_json::Value>(trimmed_c) {
                        self.update_log(pid, "Nạp cookies JSON đăng nhập từ C69...".to_string(), "Nạp Cookies");
                        let _ = cdp.set_cookies(&c_json).await;
                    } else if trimmed_c.contains('=') {
                        self.update_log(pid, "Nạp cookies String đăng nhập từ C69...".to_string(), "Nạp Cookies");
                        let _ = cdp.set_cookies_from_string(trimmed_c).await;
                    }
                }
            }
        }

        self.update_log(pid, "Mở TikTok để kiểm tra phiên đăng nhập...".to_string(), "Kiểm tra đăng nhập");
        let _ = cdp.navigate("https://www.tiktok.com").await;
        tokio::time::sleep(Duration::from_secs(5)).await;
        if !run_flag.load(Ordering::Relaxed) { return; }

        // Kiểm tra xem đã đăng nhập chưa (Chỉ xác nhận đã login khi có Avatar và KHÔNG có nút Log In trên trang)
        let check_session_expr = r#"(() => {
            const hasAvatar = !!(
                document.querySelector('[data-e2e="profile-icon"]') || 
                document.querySelector('img[alt*="avatar"]') || 
                document.querySelector('a[href*="/@"]') || 
                document.querySelector('[data-e2e="inbox-icon"]')
            );
            const hasLoginBtn = !!(
                document.querySelector('#header-login-button') ||
                Array.from(document.querySelectorAll('button, a')).some(el => {
                    const t = (el.innerText || '').trim().toLowerCase();
                    return (t === 'log in' || t === 'đăng nhập') && el.offsetParent !== null;
                })
            );
            return hasAvatar && !hasLoginBtn;
        })()"#;

        let already_logged_in = cdp.evaluate(check_session_expr).await.ok()
            .and_then(|v| v.as_bool())
            .unwrap_or(false);

        if already_logged_in {
            self.update_log(pid, "✅ Phát hiện phiên đăng nhập TikTok có sẵn trong profile! Sẵn sàng vào FYP...".to_string(), "Đã đăng nhập");
            tokio::time::sleep(Duration::from_secs(2)).await;
        } else {
            // Chưa đăng nhập -> Cần thực hiện quy trình đăng nhập
            let has_valid_c69_pwd = c69_acc.as_ref().map(|a| a.password.as_deref().unwrap_or("").trim().len() > 0).unwrap_or(false);
            if !has_valid_c69_pwd {
                self.update_log(pid, "⚠️ Profile chưa đăng nhập TikTok! Đang mở trang đăng nhập https://www.tiktok.com/login... Vui lòng đăng nhập trên cửa sổ trình duyệt (hoặc gắn tài khoản C69 có mật khẩu).".to_string(), "Chờ đăng nhập");
                let _ = cdp.navigate("https://www.tiktok.com/login/phone-or-email/email?lang=en").await;

                let mut manual_login_ok = false;
                for wait_i in 1..=60 {
                    if !run_flag.load(Ordering::Relaxed) { return; }
                    tokio::time::sleep(Duration::from_secs(2)).await;
                    let check_now = cdp.evaluate(check_session_expr).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);
                    if check_now {
                        manual_login_ok = true;
                        break;
                    }
                    if wait_i % 5 == 0 {
                        self.update_log(pid, format!("Đang chờ bạn đăng nhập TikTok trên trình duyệt (thời gian còn {}s)...", (60 - wait_i) * 2), "Chờ đăng nhập");
                    }
                }
                if !manual_login_ok {
                    self.set_error(pid, "❌ Quá thời gian chờ đăng nhập TikTok (120s) hoặc chưa hoàn tất đăng nhập. Vui lòng thử lại.".to_string());
                    return;
                }
            } else {
                let acc = c69_acc.as_ref().unwrap();
                let pwd = acc.password.as_deref().unwrap_or("");
                let login_identity = if let Some(ref email) = acc.email {
                    if email.contains('@') { email.clone() } else { acc.username.clone() }
                } else {
                    acc.username.clone()
                };

                self.update_log(pid, format!("Mở trang đăng nhập TikTok cho tài khoản: {}", login_identity), "Tiến hành đăng nhập");

            let _ = cdp.navigate("https://www.tiktok.com/login/phone-or-email/email?lang=en").await;

            let mut form_found_and_submitted = false;
            for form_try in 1..=15 {
                if !run_flag.load(Ordering::Relaxed) { return; }
                tokio::time::sleep(Duration::from_secs(1)).await;
                self.update_log(pid, format!("Đang tìm kiếm form đăng nhập TikTok (lần {}/15)...", form_try), "Tìm form đăng nhập");

                let detect_and_fill_script = format!(r#"
                    (() => {{
                        // 1. Nếu đang ở màn hình chọn phương thức login chung, click vào "Use phone / email / username"
                        const methodBtn = Array.from(document.querySelectorAll('div, a, button, p, span')).find(el => {{
                            const t = (el.innerText || '').trim().toLowerCase();
                            return t === 'use phone / email / username' || t === 'sử dụng số điện thoại / email / tên người dùng';
                        }});
                        if (methodBtn && methodBtn.offsetParent !== null) {{
                            methodBtn.click();
                        }}

                        // 2. Nếu đang ở tab Phone, click chuyển sang tab "Log in with email or username"
                        const emailTab = Array.from(document.querySelectorAll('a, button, span, div')).find(el => {{
                            const t = (el.innerText || '').trim().toLowerCase();
                            return t === 'log in with email or username' || t === 'đăng nhập bằng email hoặc tên người dùng';
                        }});
                        if (emailTab && emailTab.offsetParent !== null) {{
                            emailTab.click();
                        }}

                        function setReactVal(input, val) {{
                            if (!input) return false;
                            input.scrollIntoView({{ behavior: 'smooth', block: 'center' }});
                            input.focus();
                            const proto = window.HTMLInputElement.prototype;
                            const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                            setter.call(input, val);
                            input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                            return true;
                        }}

                        const u = document.querySelector('input[name="username"]') || 
                                  document.querySelector('input[placeholder*="Email"]') || 
                                  document.querySelector('input[placeholder*="Username"]') ||
                                  document.querySelector('input[type="text"]');
                        const p = document.querySelector('input[type="password"]');

                        if (u && p) {{
                            setReactVal(u, "{}");
                            setReactVal(p, "{}");

                            const btn = document.querySelector('button[type="submit"]') || 
                                        Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase().includes('log in'));
                            if (btn) {{
                                btn.disabled = false;
                                btn.removeAttribute('disabled');
                                const r = btn.getBoundingClientRect();
                                return JSON.stringify({{
                                    found: true,
                                    x: r.left + r.width/2,
                                    y: r.top + r.height/2
                                }});
                            }}
                            return JSON.stringify({{ found: true, x: 0.0, y: 0.0 }});
                        }}
                        return JSON.stringify({{ found: false }});
                    }})()
                "#, login_identity.replace('\\', "\\\\").replace('"', "\\\""), pwd.replace('\\', "\\\\").replace('"', "\\\""));

                let res_str = cdp.evaluate(&detect_and_fill_script).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(&res_str) {
                    if val.get("found").and_then(|v| v.as_bool()).unwrap_or(false) {
                        let x = val.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let y = val.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0);

                        tokio::time::sleep(Duration::from_millis(400)).await;
                        if x > 0.0 && y > 0.0 {
                            let _ = cdp.dispatch_mouse_click(x, y).await;
                        }

                        // Kích hoạt thêm submit form và btn.click()
                        let _ = cdp.evaluate(r#"(() => {
                            const btn = document.querySelector('button[type="submit"]') || 
                                        Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase().includes('log in'));
                            if (btn) {
                                btn.disabled = false;
                                btn.removeAttribute('disabled');
                                btn.click();
                            }
                            const form = document.querySelector('form');
                            if (form) {
                                try { form.requestSubmit(); } catch(e) {}
                            }
                        })()"#).await;

                        self.update_log(pid, format!("✅ Đã tìm thấy form, tự động điền tài khoản: {} và click nút Log in!", login_identity), "Đã click Log in");
                        form_found_and_submitted = true;
                        break;
                    }
                }
            }

            if !form_found_and_submitted {
                self.update_log(pid, "⚠️ Không tìm thấy ô nhập Email/Mật khẩu trên trang login TikTok sau 15s. Vui lòng kiểm tra cửa sổ trình duyệt!".to_string(), "Chờ đăng nhập");
            }

            // ── VÒNG LẶP XÁC THỰC ĐĂNG NHẬP (Lên tới 180s = 90 chu kỳ x 2s) ──
            let mut login_confirmed = false;
            let mut totp_submitted = false;

            for cycle in 1..=90 {
                if !run_flag.load(Ordering::Relaxed) { return; }
                tokio::time::sleep(Duration::from_secs(2)).await;

                // 1. Kiểm tra đăng nhập thành công
                let login_ok_expr = r#"(() => {
                    const hasAvatar = !!(
                        document.querySelector('[data-e2e="profile-icon"]') || 
                        document.querySelector('img[alt*="avatar"]') || 
                        document.querySelector('a[href*="/@"]') ||
                        document.querySelector('[data-e2e="inbox-icon"]')
                    );
                    const hasLoginBtn = !!(
                        document.querySelector('#header-login-button') ||
                        Array.from(document.querySelectorAll('button, a')).some(el => {
                            const t = (el.innerText || '').trim().toLowerCase();
                            return (t === 'log in' || t === 'đăng nhập') && el.offsetParent !== null;
                        })
                    );
                    const notInLogin = !window.location.href.includes('/login');
                    return (hasAvatar || (document.cookie.includes('sessionid=') && !hasLoginBtn)) && notInLogin;
                })()"#;
                let is_ok = cdp.evaluate(login_ok_expr).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);
                if is_ok {
                    login_confirmed = true;
                    break;
                }

                // 2. Kiểm tra Captcha
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
                    self.update_challenge(pid, "Captcha", format!("⚠️ Phát hiện Captcha TikTok! Vui lòng kéo captcha trên cửa sổ trình duyệt (chu kỳ {}/90)...", cycle));
                }

                // 3. Kiểm tra thông báo lỗi sai mật khẩu / tài khoản / rate limit toàn diện
                let err_expr = r#"(() => {
                    const bodyText = (document.body ? document.body.innerText : '');
                    if (bodyText.includes('Maximum number of attempts reached') || bodyText.includes('Try again later')) {
                        return 'Maximum number of attempts reached (Tài khoản hoặc IP bị giới hạn số lần đăng nhập. Vui lòng đổi IP/Proxy hoặc thử lại sau)';
                    }
                    if (bodyText.includes('Incorrect username or password') || bodyText.includes('wrong password')) {
                        return 'Sai tên đăng nhập hoặc mật khẩu';
                    }
                    if (bodyText.includes('Account does not exist')) {
                        return 'Tài khoản không tồn tại trên TikTok';
                    }
                    if (bodyText.includes('Too many attempts')) {
                        return 'Quá nhiều lần thử thất bại';
                    }

                    const err = document.querySelector('.tiktok-input-error') || 
                                document.querySelector('[role="alert"]') || 
                                document.querySelector('[class*="error-container"]') ||
                                document.querySelector('[class*="error-message"]');
                    return err ? err.innerText.trim() : '';
                })()"#;
                let err_text = cdp.evaluate(err_expr).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
                if !err_text.is_empty() && !err_text.to_lowercase().contains("enter") {
                    self.set_error(pid, format!("❌ Đăng nhập TikTok thất bại: {}", err_text));
                    return;
                }

                // 4. Kiểm tra thách thức 2FA / Email Code / SMS Code
                let challenge_detect_expr = r#"(() => {
                    const bodyText = (document.body ? document.body.innerText : '').toLowerCase();
                    const is2fa = bodyText.includes('2-step verification') || 
                                  bodyText.includes('authenticator app') || 
                                  bodyText.includes('enter the 6-digit code generated');
                    const isEmail = bodyText.includes('enter 6-digit code') || 
                                    bodyText.includes('sent a code to') || 
                                    bodyText.includes('code sent to') ||
                                    bodyText.includes('verify with email') ||
                                    bodyText.includes('email verification') ||
                                    bodyText.includes('we sent a code');
                    const isPhone = bodyText.includes('enter sms code') || 
                                    bodyText.includes('sent an sms') ||
                                    bodyText.includes('sms verification');

                    const sendBtn = Array.from(document.querySelectorAll('button')).find(b => {
                        const t = b.innerText.toLowerCase();
                        return (t.includes('send code') || t.includes('gửi mã')) && !b.disabled;
                    });

                    return JSON.stringify({
                        is_2fa: is2fa,
                        is_email: isEmail,
                        is_phone: isPhone,
                        has_send_btn: !!sendBtn
                    });
                })()"#;

                if let Ok(ch_val) = cdp.evaluate(challenge_detect_expr).await {
                    if let Some(ch_str) = ch_val.as_str() {
                        if let Ok(ch) = serde_json::from_str::<serde_json::Value>(ch_str) {
                            let is_2fa = ch.get("is_2fa").and_then(|v| v.as_bool()).unwrap_or(false);
                            let is_email = ch.get("is_email").and_then(|v| v.as_bool()).unwrap_or(false);
                            let is_phone = ch.get("is_phone").and_then(|v| v.as_bool()).unwrap_or(false);
                            let has_send_btn = ch.get("has_send_btn").and_then(|v| v.as_bool()).unwrap_or(false);

                            // Tự động bấm Send Code nếu có nút gửi mã
                            if has_send_btn {
                                let click_send_expr = r#"(() => {
                                    const sendBtn = Array.from(document.querySelectorAll('button')).find(b => {
                                        const t = b.innerText.toLowerCase();
                                        return (t.includes('send code') || t.includes('gửi mã')) && !b.disabled;
                                    });
                                    if (sendBtn) { sendBtn.click(); return true; }
                                    return false;
                                })()"#;
                                let _ = cdp.evaluate(click_send_expr).await;
                                self.update_log(pid, "Đã tự động nhấn nút 'Send Code' để yêu cầu gửi mã xác thực về Email/SMS...".to_string(), "Đã gửi mã");
                            }

                            // Tự động xử lý 2FA nếu có Secret Key
                            if is_2fa && !totp_submitted {
                                if let Some(ref sec_key) = acc.two_factor_auth {
                                    let clean_sec = sec_key.trim();
                                    if clean_sec.len() >= 8 {
                                        let gen_totp_expr = format!(r#"
                                            (async () => {{
                                                const base32chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
                                                let bits = '';
                                                const clean = '{}'.replace(/[\s=-]/g, '').toUpperCase();
                                                for (let i = 0; i < clean.length; i++) {{
                                                    const val = base32chars.indexOf(clean[i]);
                                                    if (val >= 0) bits += val.toString(2).padStart(5, '0');
                                                }}
                                                const bytes = new Uint8Array(Math.floor(bits.length / 8));
                                                for (let i = 0; i < bytes.length; i++) {{
                                                    bytes[i] = parseInt(bits.substr(i * 8, 8), 2);
                                                }}
                                                const epoch = Math.floor(Date.now() / 1000);
                                                const counter = Math.floor(epoch / 30);
                                                const counterBuffer = new ArrayBuffer(8);
                                                const counterView = new DataView(counterBuffer);
                                                counterView.setUint32(4, counter, false);
                                                const key = await crypto.subtle.importKey('raw', bytes, {{ name: 'HMAC', hash: {{ name: 'SHA-1' }} }}, false, ['sign']);
                                                const sig = await crypto.subtle.sign('HMAC', key, counterBuffer);
                                                const sigBytes = new Uint8Array(sig);
                                                const offset = sigBytes[sigBytes.length - 1] & 0x0f;
                                                const code = ((sigBytes[offset] & 0x7f) << 24 | (sigBytes[offset + 1] & 0xff) << 16 | (sigBytes[offset + 2] & 0xff) << 8 | (sigBytes[offset + 3] & 0xff)) % 1000000;
                                                return code.toString().padStart(6, '0');
                                            }})()
                                        "#, clean_sec);
                                        if let Ok(val) = cdp.evaluate(&gen_totp_expr).await {
                                            if let Some(totp) = val.as_str() {
                                                if totp.len() == 6 {
                                                    self.update_log(pid, format!("🔑 Tìm thấy 2FA Secret C69! Đang tự động điền mã TOTP: {}...", totp), "Tự giải 2FA");
                                                    let _ = fill_and_submit_otp(&cdp, totp).await;
                                                    totp_submitted = true;
                                                    tokio::time::sleep(Duration::from_secs(2)).await;
                                                }
                                            }
                                        }
                                    }
                                }
                            }

                            // Cập nhật trạng thái chờ nhập mã xác thực
                            if is_email || is_phone || (is_2fa && !totp_submitted) {
                                let c_type = if is_email { "Email OTP" } else if is_phone { "SMS OTP" } else { "2FA" };
                                self.update_challenge(
                                    pid, 
                                    c_type, 
                                    format!("🔑 TikTok yêu cầu mã xác thực {}! Bạn có thể nhập mã OTP trực tiếp trên Dashboard hoặc trên trình duyệt (Thời gian còn {}s)...", c_type, (90 - cycle) * 2)
                                );
                            }
                        }
                    }
                }

                // 5. Kiểm tra mã OTP gửi từ Web Dashboard
                if let Some(user_otp) = self.take_otp(pid) {
                    self.update_log(pid, format!("🚀 Đã nhận mã OTP '{}' từ Dashboard! Đang điền vào TikTok...", user_otp), "Điền mã OTP");
                    let _ = fill_and_submit_otp(&cdp, &user_otp).await;
                    tokio::time::sleep(Duration::from_secs(3)).await;
                }
            }

                if !login_confirmed {
                    self.set_error(
                        pid, 
                        "❌ Đăng nhập TikTok thất bại: Hết thời gian chờ (Timeout 180s) hoặc chưa hoàn tất Captcha / Mã OTP xác thực. Dừng lại an toàn.".to_string()
                    );
                    return;
                }
            }

            self.clear_challenge(pid);

            // Thu thập Cookies đăng nhập và lưu lại
            if let Ok(cookies_val) = cdp.get_all_cookies().await {
                let cookies_str = cookies_val.to_string();
                if let Some(ref a) = c69_acc {
                    if a.id > 0 {
                        let aid = a.id;
                        let un = a.username.clone();
                        let cs = cookies_str.clone();
                        tokio::spawn(async move {
                            let _ = sync_cookies_to_c69(aid, cs, un).await;
                        });
                    }
                }
            }

            self.update_log(pid, "🎉 Đăng nhập TikTok thành công 100%! Đã lưu phiên Cookies. Đang chuyển sang Feed FYP...".to_string(), "Đăng nhập thành công");
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
        let summary = format!("Đã xem {} video, thả tim {} lượt", watched_count, likes_count);
        self.update_log(
            pid, 
            format!("Chu trình nuôi hoàn tất. Tổng {}.", summary), 
            "Đã dừng"
        );
        if watched_count > 0 {
            crate::api::update_profile_nurture_status(pid, "Đã nuôi thành công", Some(&summary), None);
        }
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
        let err_lower = err.to_lowercase();
        let is_max_attempts = err_lower.contains("maximum number of attempts") 
            || err_lower.contains("try again later")
            || err_lower.contains("too many attempts");

        let (status_label, retry_after, short_st) = if is_max_attempts {
            ("Rate limit (Chờ 1h)", Some(3600), "Chờ 1h")
        } else {
            ("Lỗi nuôi", None, "Lỗi")
        };

        crate::api::update_profile_nurture_status(pid, status_label, Some(&err), retry_after);

        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.is_running = false;
            st.status = short_st.to_string();
            st.last_log = err;
        }
        if let Some(f) = self.tasks.read().get(&pid) {
            f.store(false, Ordering::Relaxed);
        }
    }
}

/// Điền mã OTP vào ô nhập (hỗ trợ cả 6 ô ký tự riêng biệt và 1 ô tổng hợp) và bấm nút xác nhận
async fn fill_and_submit_otp(cdp: &CdpClient, otp: &str) -> bool {
    let clean_otp = otp.trim();
    let fill_expr = format!(r#"
        (() => {{
            const otp = '{}';
            const digitInputs = Array.from(document.querySelectorAll('input[maxlength="1"], input[data-index]'));
            if (digitInputs.length >= 4) {{
                for (let i = 0; i < digitInputs.length && i < otp.length; i++) {{
                    digitInputs[i].focus();
                    digitInputs[i].value = otp[i];
                    digitInputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                    digitInputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}
                return true;
            }}
            const singleInp = document.querySelector('input[placeholder*="code"]') ||
                              document.querySelector('input[placeholder*="Code"]') ||
                              document.querySelector('input[maxlength="6"]') ||
                              document.querySelector('input[type="tel"]');
            if (singleInp) {{
                singleInp.focus();
                singleInp.click();
                singleInp.value = otp;
                singleInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                singleInp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            return false;
        }})()
    "#, clean_otp);

    let filled = cdp.evaluate(&fill_expr).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);
    tokio::time::sleep(Duration::from_millis(500)).await;

    let submit_expr = r#"
        (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const btn = buttons.find(b => {
                const t = b.innerText.trim().toLowerCase();
                return (t.includes('log in') || t.includes('verify') || t.includes('next') || t.includes('confirm') || t.includes('xác nhận') || t.includes('tiếp tục')) && !b.disabled;
            });
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        })()
    "#;
    let _ = cdp.evaluate(submit_expr).await;
    filled
}

/// Đồng bộ Cookies lên C69 Server sau khi đăng nhập thành công
pub async fn sync_cookies_to_c69(acc_id: u64, cookies_json: String, username: String) -> Result<(), String> {
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/{}/update-cookies/", DEFAULT_C69_API_URL, acc_id);
    let payload = json!({
        "cookies": cookies_json,
        "username": username
    });
    let resp = client.post(&url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .header("User-Agent", "Mozilla/5.0 MunAutomation/1.0")
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Lỗi gửi cookies lên C69: {}", e))?;

    if resp.status().is_success() {
        info!("✅ Đã đồng bộ Cookies thành công lên C69 cho tài khoản #{}", acc_id);
        Ok(())
    } else {
        Err(format!("C69 update-cookies HTTP {}", resp.status()))
    }
}

/// Lấy chi tiết tài khoản TikTok từ C69 Backend API theo Account ID
pub async fn fetch_c69_account_by_id(account_id: u64) -> Result<C69Account, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/{}/", DEFAULT_C69_API_URL, account_id);

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

    let item: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi giải mã JSON C69: {}", e))?;
    let u = item.get("username").and_then(|v| v.as_str()).unwrap_or("").to_string();
    let id = item.get("id").and_then(|v| v.as_u64()).unwrap_or(account_id);
    let email = item.get("email").and_then(|v| v.as_str()).map(|s| s.to_string());
    let pwd = item.get("password").and_then(|v| v.as_str()).map(|s| s.to_string());
    let two_fa = item.get("two_factor_auth").and_then(|v| v.as_str()).map(|s| s.to_string());
    let cookies = item.get("cookies").and_then(|v| v.as_str()).map(|s| s.to_string());
    let st = item.get("status").cloned();
    let nt = item.get("note").and_then(|v| v.as_str()).map(|s| s.to_string());

    Ok(C69Account {
        id,
        username: u,
        email,
        password: pwd,
        two_factor_auth: two_fa,
        cookies,
        status: st,
        note: nt,
    })
}

/// Lấy danh sách tài khoản TikTok từ C69 Backend API
pub async fn fetch_c69_tiktok_accounts() -> Result<Vec<C69Account>, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/?type=tiktok&limit=100", DEFAULT_C69_API_URL);

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
            let email = item.get("email").and_then(|v| v.as_str()).map(|s| s.to_string());
            let pwd = item.get("password").and_then(|v| v.as_str()).map(|s| s.to_string());
            let two_fa = item.get("two_factor_auth").and_then(|v| v.as_str()).map(|s| s.to_string());
            let cookies = item.get("cookies").and_then(|v| v.as_str()).map(|s| s.to_string());
            let st = item.get("status").cloned();
            let nt = item.get("note").and_then(|v| v.as_str()).map(|s| s.to_string());
            accounts.push(C69Account {
                id,
                username: u.to_string(),
                email,
                password: pwd,
                two_factor_auth: two_fa,
                cookies,
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
                last_nurture_status: None,
                last_nurture_time: None,
                last_nurture_error: None,
                retry_after_epoch: None,
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

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct C69Proxy {
    pub id: String,
    #[serde(rename = "type")]
    pub proxy_type: String,
    pub host: String,
    pub port: u16,
    pub username: Option<String>,
    pub password: Option<String>,
    pub status: Option<String>,
    pub latency: Option<i32>,
}

impl C69Proxy {
    pub fn to_proxy_string(&self) -> String {
        match (&self.username, &self.password) {
            (Some(u), Some(p)) if !u.is_empty() => {
                format!("socks5://{}:{}@{}:{}", u, p, self.host, self.port)
            }
            _ => format!("socks5://{}:{}", self.host, self.port),
        }
    }
}

/// Nạp danh sách proxy SOCKS5 từ C69 Router config.json (250 proxies pool)
pub fn load_c69_proxies() -> Vec<C69Proxy> {
    let candidate_paths = [
        "d:\\Workspace\\Python\\c69-router\\data\\config.json",
        "../c69-router/data/config.json",
        "c69-router/data/config.json",
        "data/c69_proxies.json",
    ];

    for path_str in &candidate_paths {
        let p = std::path::Path::new(path_str);
        if p.exists() {
            if let Ok(content) = std::fs::read_to_string(p) {
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(&content) {
                    if let Some(arr) = val.get("proxies").and_then(|v| v.as_array()) {
                        let mut proxies = Vec::new();
                        for item in arr {
                            if let Ok(proxy) = serde_json::from_value::<C69Proxy>(item.clone()) {
                                proxies.push(proxy);
                            }
                        }
                        if !proxies.is_empty() {
                            return proxies;
                        }
                    }
                }
            }
        }
    }

    Vec::new()
}

/// Kiểm tra kết nối TCP tới Proxy và đo độ trễ (latency ms)
pub async fn test_proxy_connection(proxy_str: &str) -> (bool, u64, String) {
    let parsed = match crate::cdp_browser::parse_proxy_string(proxy_str) {
        Some(p) => p,
        None => return (false, 0, "Định dạng proxy không hợp lệ".to_string()),
    };

    let target = format!("{}:{}", parsed.host, parsed.port);
    let start = std::time::Instant::now();

    match tokio::time::timeout(
        Duration::from_millis(4000),
        tokio::net::TcpStream::connect(&target)
    ).await {
        Ok(Ok(_)) => {
            let latency = start.elapsed().as_millis() as u64;
            let msg = format!("Proxy Live (Độ trễ: {}ms)", latency);
            (true, latency, msg)
        }
        Ok(Err(e)) => (false, 0, format!("Không thể kết nối đến {}: {}", target, e)),
        Err(_) => (false, 0, format!("Kết nối đến {} bị timeout (> 4000ms)", target)),
    }
}

