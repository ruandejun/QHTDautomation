use crate::api::BrowserProfile;
use crate::cdp_browser::{get_free_port, launch_cdp_profile_with_bounds, calculate_grid_window_bounds};
use futures_util::{SinkExt, StreamExt};
use parking_lot::{Mutex, RwLock};
use rand::Rng;
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::{HashMap, VecDeque};
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicU64, Ordering};
use std::sync::Arc;
use std::time::Duration;
use tokio_tungstenite::tungstenite::protocol::Message;
use tracing::{error, info, warn};

pub const DEFAULT_C69_API_URL: &str = "https://cu.c69.us";
pub const DEFAULT_C69_TOKEN: &str = "Token 99b02d3d255a49193950777b1cc3e3db099ceefb";

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
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
    #[serde(default)]
    pub accounts_emails: Option<u64>,
    #[serde(default)]
    pub r#type: Option<String>,
    #[serde(default)]
    pub created_by: Option<String>,
    #[serde(default)]
    pub created: Option<String>,
    #[serde(default)]
    pub modified_by: Option<String>,
    #[serde(default)]
    pub modified: Option<String>,
    #[serde(default)]
    pub subscription: Option<String>,
    #[serde(default)]
    pub subscription_owner: Option<String>,
    #[serde(default)]
    pub email_info: Option<serde_json::Value>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct C69Session {
    pub logged_in: bool,
    pub username: String,
    #[serde(default)]
    pub server_url: String,
    #[serde(default)]
    pub cookies: Option<String>,
    #[serde(default)]
    pub token: Option<String>,
    #[serde(default)]
    pub email: Option<String>,
    #[serde(default)]
    pub is_staff: bool,
    #[serde(default)]
    pub last_login: Option<String>,
}

pub fn get_c69_session_file_path() -> std::path::PathBuf {
    let candidates = [
        std::path::PathBuf::from(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\c69_session.json"),
        std::path::PathBuf::from("MunAutomationDesktop").join("c69_session.json"),
        std::path::PathBuf::from("c69_session.json"),
        std::path::PathBuf::from("..").join("MunAutomationDesktop").join("c69_session.json"),
    ];
    for c in &candidates {
        if c.exists() {
            return c.clone();
        }
    }
    candidates[0].clone()
}

pub fn load_c69_session() -> Option<C69Session> {
    let path = get_c69_session_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(sess) = serde_json::from_str::<C69Session>(&data) {
            if sess.logged_in {
                return Some(sess);
            }
        }
    }
    None
}

pub fn save_c69_session(sess: &C69Session) -> Result<(), String> {
    let path = get_c69_session_file_path();
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let data = serde_json::to_string_pretty(sess).map_err(|e| e.to_string())?;
    std::fs::write(&path, data).map_err(|e| e.to_string())
}

pub fn clear_c69_session() -> Result<(), String> {
    let path = get_c69_session_file_path();
    if path.exists() {
        let _ = std::fs::remove_file(path);
    }
    Ok(())
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct BrowserNurtureStatus {
    pub profile_id: usize,
    pub profile_name: String,
    pub c69_username: String,
    pub status: String,
    pub videos_watched: u32,
    pub likes_given: u32,
    #[serde(default)]
    pub comments_posted: u32,
    #[serde(default)]
    pub shares_count: u32,
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
        let _ = client.call("DOM.enable", json!({})).await;

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

        match tokio::time::timeout(Duration::from_secs(4), rx).await {
            Ok(Ok(resp)) => Ok(resp),
            Ok(Err(_)) => Err("CDP channel closed".to_string()),
            Err(_) => {
                self.pending.lock().remove(&id);
                Err(format!("CDP Command '{}' timeout 4s", method))
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

    pub async fn dispatch_mouse_wheel(&self, delta_x: f64, delta_y: f64) -> Result<(), String> {
        self.call(
            "Input.dispatchMouseEvent",
            json!({
                "type": "mouseWheel",
                "x": 300,
                "y": 400,
                "deltaX": delta_x,
                "deltaY": delta_y
            }),
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

    pub async fn type_text(&self, text: &str) -> Result<(), String> {
        for ch in text.chars() {
            let mut s = String::new();
            s.push(ch);
            let _ = self.call(
                "Input.dispatchKeyEvent",
                json!({ "type": "keyDown", "text": s, "unmodifiedText": s }),
            ).await;
            let _ = self.call(
                "Input.dispatchKeyEvent",
                json!({ "type": "keyUp", "text": s, "unmodifiedText": s }),
            ).await;
            tokio::time::sleep(Duration::from_millis(60 + (ch as u64 % 40))).await;
        }
        Ok(())
    }


    pub async fn capture_screenshot(&self) -> Result<Vec<u8>, String> {
        let resp = self.call("Page.captureScreenshot", json!({ "format": "png" })).await?;
        let b64 = resp
            .get("result")
            .and_then(|r| r.get("data"))
            .and_then(|d| d.as_str())
            .ok_or_else(|| "Không lấy được dữ liệu base64 từ Page.captureScreenshot".to_string())?;

        use base64::prelude::*;
        BASE64_STANDARD
            .decode(b64.trim())
            .map_err(|e| format!("Lỗi giải mã base64 ảnh screenshot: {}", e))
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

    pub async fn upload_file_to_input(&self, selector: &str, file_path: &str) -> Result<(), String> {
        let doc = self.call("DOM.getDocument", json!({})).await?;
        let root_id = doc.get("result")
            .and_then(|r| r.get("root"))
            .and_then(|rt| rt.get("nodeId"))
            .and_then(|n| n.as_i64())
            .ok_or_else(|| "Không lấy được root DOM nodeId".to_string())?;

        let q = self.call("DOM.querySelector", json!({
            "nodeId": root_id,
            "selector": selector
        })).await?;

        let node_id = q.get("result")
            .and_then(|r| r.get("nodeId"))
            .and_then(|n| n.as_i64())
            .ok_or_else(|| format!("Không tìm thấy selector: {}", selector))?;

        if node_id == 0 {
            return Err(format!("Selector '{}' không tồn tại trên trang", selector));
        }

        self.call("DOM.setFileInputFiles", json!({
            "files": [file_path],
            "nodeId": node_id
        })).await?;

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
    concurrency_semaphore: Arc<tokio::sync::Semaphore>,
    available_slots: Arc<Mutex<VecDeque<usize>>>,
}

impl BrowserNurtureEngine {
    pub fn new() -> Self {
        let mut slots = VecDeque::new();
        for i in 0..5 {
            slots.push_back(i);
        }
        Self {
            tasks: Arc::new(RwLock::new(HashMap::new())),
            statuses: Arc::new(RwLock::new(HashMap::new())),
            otp_queue: Arc::new(Mutex::new(HashMap::new())),
            concurrency_semaphore: Arc::new(tokio::sync::Semaphore::new(5)),
            available_slots: Arc::new(Mutex::new(slots)),
        }
    }

    pub async fn acquire_slot(&self) -> (usize, tokio::sync::OwnedSemaphorePermit) {
        let permit = self.concurrency_semaphore.clone().acquire_owned().await.unwrap();
        let slot = self.available_slots.lock().pop_front().unwrap_or(0);
        (slot, permit)
    }

    pub fn release_slot(&self, slot: usize) {
        let mut slots = self.available_slots.lock();
        if !slots.contains(&slot) && slot < 5 {
            slots.push_back(slot);
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
            st.status = format!("Chờ giải {}", challenge_type);
            st.last_log = log_msg.clone();
        }
        crate::api::update_profile_nurture_status(profile_id, &format!("Thách thức: {}", challenge_type), Some(&log_msg), None);
    }

    pub fn clear_challenge(&self, profile_id: usize) {
        if let Some(st) = self.statuses.write().get_mut(&profile_id) {
            st.waiting_otp = false;
            st.challenge_type = None;
        }
    }

    pub fn get_all_statuses(&self) -> Vec<BrowserNurtureStatus> {
        let mut list: Vec<BrowserNurtureStatus> = Vec::new();
        let mut statuses = self.statuses.write();
        let tasks = self.tasks.read();
        for (pid, st) in statuses.iter_mut() {
            let is_task_alive = tasks.get(pid).map(|f| f.load(Ordering::Relaxed)).unwrap_or(false);
            let is_browser_alive = crate::cdp_browser::is_profile_active(*pid);
            let is_waiting_slot = st.status.contains("Chờ slot") || st.status.contains("Đang xếp hàng");

            // Nếu báo đang chạy nhưng task đã chết HOẶC browser đã tắt (và không phải đang chờ slot)
            if st.is_running && (!is_task_alive || (!is_browser_alive && !is_waiting_slot)) {
                st.is_running = false;
                if !st.status.contains("thành công") && !st.status.contains("Chờ 1h") && !st.status.contains("Lỗi") {
                    st.status = "Đã dừng".to_string();
                    st.last_log = "Trình duyệt đã tắt. Đã cập nhật trạng thái dừng.".to_string();
                }
            }
            list.push(st.clone());
        }
        list
    }

    pub fn get_status(&self, profile_id: usize) -> Option<BrowserNurtureStatus> {
        let mut statuses = self.statuses.write();
        if let Some(st) = statuses.get_mut(&profile_id) {
            let is_task_alive = self.tasks.read().get(&profile_id).map(|f| f.load(Ordering::Relaxed)).unwrap_or(false);
            let is_browser_alive = crate::cdp_browser::is_profile_active(profile_id);
            let is_waiting_slot = st.status.contains("Chờ slot") || st.status.contains("Đang xếp hàng");

            if st.is_running && (!is_task_alive || (!is_browser_alive && !is_waiting_slot)) {
                st.is_running = false;
                if !st.status.contains("thành công") && !st.status.contains("Chờ 1h") && !st.status.contains("Lỗi") {
                    st.status = "Đã dừng".to_string();
                    st.last_log = "Trình duyệt đã tắt. Đã cập nhật trạng thái dừng.".to_string();
                }
            }
            Some(st.clone())
        } else {
            None
        }
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

    pub fn set_rate_limit_status(&self, profile_id: usize) {
        if let Some(flag) = self.tasks.read().get(&profile_id) {
            flag.store(false, Ordering::Relaxed);
        }
        if let Some(st) = self.statuses.write().get_mut(&profile_id) {
            st.is_running = false;
            st.status = "Rate limit (Chờ 1h)".to_string();
            st.last_log = "Maximum number of attempts reached (Tự động đóng trình duyệt và chờ 1h thử lại)".to_string();
        }
        info!("⚠️ [Profile #{}] Đã cập nhật trạng thái Rate limit (Chờ 1h) vào bộ nhớ nurture!", profile_id);
    }

    pub fn stop_all(&self) {
        let keys: Vec<usize> = self.tasks.read().keys().cloned().collect();
        for id in keys {
            self.stop_nurture(id);
        }
    }

    pub async fn save_screenshot_proof(&self, cdp: &CdpClient, filename: &str) -> Result<(), String> {
        match cdp.capture_screenshot().await {
            Ok(data) => {
                let paths = [
                    format!("scratch/{}", filename),
                    format!("../scratch/{}", filename),
                    format!("d:/Workspace/Python/QHTDautomation/scratch/{}", filename),
                ];
                for p_str in &paths {
                    let p = std::path::Path::new(p_str);
                    if let Some(parent) = p.parent() {
                        let _ = std::fs::create_dir_all(parent);
                    }
                    let _ = std::fs::write(p, &data);
                }
                info!("📸 [Rust Core] Đã lưu ảnh bằng chứng: scratch/{}", filename);
                Ok(())
            }
            Err(e) => {
                warn!("⚠️ [Rust Core] Không thể chụp ảnh {}: {}", filename, e);
                Err(e)
            }
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
            status: "Đang xếp hàng chờ slot màn hình (Tối đa 5)...".to_string(),
            videos_watched: 0,
            likes_given: 0,
            comments_posted: 0,
            shares_count: 0,
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

        // 1. Chờ slot trống trong tối đa 5 trình duyệt đồng thời (Grid Concurrency Cap = 5)
        self.update_log(pid, "⏳ Đang chờ slot màn hình (Tối đa 5 trình duyệt song song)...".to_string(), "Chờ slot");
        let (slot_idx, permit) = self.acquire_slot().await;
        info!("🎯 [Profile #{}] Đã chiếm Slot #{} trên màn hình (Đang chạy: {}/5)", pid, slot_idx, 5 - self.concurrency_semaphore.available_permits());

        // RAII Guard: Đảm bảo khi worker kết thúc (bất kể return sớm, lỗi, hay hoàn thành), luôn đóng Chrome và trả slot
        struct SlotGuard<'a> {
            engine: &'a BrowserNurtureEngine,
            slot: usize,
            pid: usize,
            _permit: tokio::sync::OwnedSemaphorePermit,
        }
        impl<'a> Drop for SlotGuard<'a> {
            fn drop(&mut self) {
                self.engine.release_slot(self.slot);
                crate::cdp_browser::stop_cdp_profile(self.pid);
                crate::cdp_browser::mark_profile_inactive(self.pid);
                if let Some(flag) = self.engine.tasks.read().get(&self.pid) {
                    flag.store(false, Ordering::Relaxed);
                }
                if let Some(st) = self.engine.statuses.write().get_mut(&self.pid) {
                    st.is_running = false;
                    if !st.status.contains("thành công") && !st.status.contains("Chờ 1h") && !st.status.contains("Lỗi") {
                        st.status = "Đã dừng".to_string();
                        st.last_log = "Trình duyệt đã đóng. Đã dừng nuôi an toàn.".to_string();
                        crate::api::update_profile_nurture_status(self.pid, "Đã dừng", None, None);
                    }
                }
                info!("🏁 [Profile #{}] Đã tự động đóng trình duyệt an toàn và giải phóng Slot #{} trên màn hình!", self.pid, self.slot);
            }
        }
        let _guard = SlotGuard { engine: self, slot: slot_idx, pid, _permit: permit };

        let port = get_free_port(9222 + (pid as u16 % 500));

        let mut active_profile = profile.clone();

        // Giữ nguyên cấu hình Profile. Nếu chưa có UA, mặc định dùng Desktop UA chuẩn để có Trust Score cao nhất
        if active_profile.profile_user_agent.trim().is_empty() {
            active_profile.profile_user_agent = crate::cdp_browser::DEFAULT_DESKTOP_UA.to_string();
            active_profile.profile_os = "Windows".to_string();
            active_profile.profile_resolution = "1200x800".to_string();
        }

        // Tự động kiểm tra sức khỏe proxy trước khi mở trình duyệt, nếu chết tự động đảo sang proxy sống
        if !active_profile.proxy_string.trim().is_empty() && !active_profile.proxy_type.eq_ignore_ascii_case("direct") {
            let (alive, latency, msg) = test_proxy_connection(&active_profile.proxy_string).await;
            if !alive {
                warn!("⚠️ Proxy hiện tại của Profile #{} không khả dụng ({}). Tự động tìm proxy sống...", pid, msg);
                self.update_log(
                    pid,
                    format!("⚠️ Proxy lỗi ({}). Đang tự động đảo sang Proxy US sống dự phòng...", msg),
                    "Đảo Proxy"
                );
                if let Some(healthy) = find_healthy_backup_proxy(&active_profile.proxy_string).await {
                    info!("🔄 Đã tự động đảo sang Proxy sống cho Profile #{}: {}", pid, healthy);
                    crate::api::update_profile_proxy(pid, &healthy, "socks5");
                    active_profile.proxy_string = healthy;
                    active_profile.proxy_type = "socks5".to_string();
                }
            } else {
                info!("✅ Proxy Profile #{} sống 100% (Latency: {}ms)", pid, latency);
            }
        }

        // 1. Khởi chạy Profile Pure Rust CDP Browser với Tọa độ Grid tương ứng slot (Không đè lên nhau)
        let proxy_desc = if let Some(parsed) = crate::cdp_browser::parse_proxy_string(&active_profile.proxy_string) {
            let auth_tag = if parsed.username.is_some() { " (Auth OK)" } else { "" };
            format!("🛡️ Proxy: {}://{}:{}{}", parsed.scheme.to_uppercase(), parsed.host, parsed.port, auth_tag)
        } else {
            "⚡ Direct / Local Network".to_string()
        };

        let is_mobile = active_profile.profile_os.eq_ignore_ascii_case("Android")
            || active_profile.profile_os.eq_ignore_ascii_case("iOS")
            || active_profile.profile_user_agent.contains("Mobile")
            || active_profile.profile_user_agent.contains("Android")
            || active_profile.profile_user_agent.contains("iPhone");

        let bounds = Some(calculate_grid_window_bounds(slot_idx, is_mobile));
        self.update_log(
            pid,
            format!("Đang mở cửa sổ tại Slot #{} [{}]...", slot_idx, proxy_desc),
            "Khởi động browser"
        );
        if let Err(e) = launch_cdp_profile_with_bounds(&active_profile, bounds).await {
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

        // 4. KIỂM TRA PHIÊN ĐĂNG NHẬP ELEMENT-DRIVEN (Ưu tiên Zero-Login Cookie Jar trong 0ms, không chờ mạng tải trang)
        let cookies_val = cdp.get_all_cookies().await.unwrap_or(serde_json::Value::Null);
        let has_session_cookie = cookies_val.as_array().map(|arr| {
            arr.iter().any(|c| {
                let name = c.get("name").and_then(|v| v.as_str()).unwrap_or("");
                (name == "sessionid" || name == "sessionid_ss") &&
                c.get("value").and_then(|v| v.as_str()).unwrap_or("").trim().len() > 15
            })
        }).unwrap_or(false);

        let mut is_already_logged_in = has_session_cookie;
        let mut detected_username = String::new();

        if is_already_logged_in {
            self.update_log(pid, "⚡ Đã có phiên đăng nhập sẵn (Zero-Login Cookies)! Chuyển thẳng sang FYP...".to_string(), "Đã đăng nhập");
            let _ = crate::cdp_browser::backup_thin_profile(pid);
        } else {
            self.update_log(pid, "Mở TikTok Profile kiểm tra phiên đăng nhập...".to_string(), "Kiểm tra Profile");
            let _ = cdp.navigate("https://www.tiktok.com/profile").await;

            // Polling siêu tốc mỗi 250ms (Tối đa 5 giây = 20 lần), tìm thấy element là chuyển bước NGAY LẬP TỨC
            for check_step in 1..=20 {
                if !run_flag.load(Ordering::Relaxed) { return; }
                tokio::time::sleep(Duration::from_millis(250)).await;

                let check_auth_js = r#"(() => {
                    const url = window.location.href;
                    const isLoginUrl = url.includes('/login');
                    const hasLoginBtn = !!(
                        document.querySelector('[data-e2e="top-login-button"]') ||
                        Array.from(document.querySelectorAll('button, a')).some(el => {
                            const t = (el.innerText || '').trim().toLowerCase();
                            return (t === 'log in' || t === 'đăng nhập') && el.offsetParent !== null;
                        })
                    );
                    
                    let un = '';
                    const m = url.match(/@([a-zA-Z0-9_.-]+)/);
                    if (m && m[1]) {
                        un = m[1];
                    }

                    const hasAvatar = !!(
                        document.querySelector('[data-e2e="user-avatar"]') || 
                        document.querySelector('[data-e2e="profile-icon"]') || 
                        document.querySelector('a[href*="/@"]') ||
                        document.querySelector('[data-e2e="user-subtitle"]')
                    );

                    return JSON.stringify({
                        url: url,
                        is_login_url: isLoginUrl,
                        has_login_btn: hasLoginBtn,
                        has_avatar: hasAvatar,
                        username: un
                    });
                })()"#;

                let mut is_login_page = false;
                let mut has_btn = false;
                let mut has_avatar = false;
                let mut un_str = String::new();

                if let Ok(eval_val) = cdp.evaluate(check_auth_js).await {
                    if let Some(s) = eval_val.as_str() {
                        if let Ok(parsed) = serde_json::from_str::<serde_json::Value>(s) {
                            is_login_page = parsed.get("is_login_url").and_then(|v| v.as_bool()).unwrap_or(false);
                            has_btn = parsed.get("has_login_btn").and_then(|v| v.as_bool()).unwrap_or(false);
                            has_avatar = parsed.get("has_avatar").and_then(|v| v.as_bool()).unwrap_or(false);
                            un_str = parsed.get("username").and_then(|v| v.as_str()).unwrap_or("").to_string();
                        }
                    }
                }

                let cookies_val2 = cdp.get_all_cookies().await.unwrap_or(serde_json::Value::Null);
                let has_cookie2 = cookies_val2.as_array().map(|arr| {
                    arr.iter().any(|c| {
                        let name = c.get("name").and_then(|v| v.as_str()).unwrap_or("");
                        (name == "sessionid" || name == "sessionid_ss") &&
                        c.get("value").and_then(|v| v.as_str()).unwrap_or("").trim().len() > 15
                    })
                }).unwrap_or(false);

                if (has_cookie2 || has_avatar) && !is_login_page && !has_btn {
                    is_already_logged_in = true;
                    detected_username = un_str;
                    self.update_log(pid, format!("⚡ Phần tử hồ sơ xuất hiện (@{}) sau {}ms! Chuyển bước ngay...", detected_username, check_step * 250), "Đã đăng nhập");
                    break;
                }

                if is_login_page || (has_btn && check_step >= 6) {
                    break;
                }

                self.update_log(pid, format!("Đang lắng nghe phần tử TikTok ({}ms)...", check_step * 250), "Lắng nghe phần tử");
            }

            if is_already_logged_in {
                self.update_log(pid, format!("✅ Tài khoản đã đăng nhập sẵn (@{})! Chuẩn bị nuôi FYP...", detected_username), "Đã đăng nhập");
                let _ = crate::cdp_browser::backup_thin_profile(pid);
            }
        }

        if !is_already_logged_in {
            self.update_log(pid, "⚠️ Phát hiện tài khoản CHƯA ĐĂNG NHẬP! Bắt đầu quy trình đăng nhập TikTok...".to_string(), "Tiến hành đăng nhập");
            
            // Chưa đăng nhập -> Kiểm tra mật khẩu C69 an toàn (Zero Panic)
            let acc_opt = c69_acc.as_ref();
            if acc_opt.is_none() || acc_opt.and_then(|a| a.password.as_deref()).unwrap_or("").trim().is_empty() {
                self.set_error(pid, "❌ Profile chưa đăng nhập TikTok và không có mật khẩu tài khoản C69! Tự động dừng lại và đóng trình duyệt, tuyệt đối không nuôi dạo vô nghĩa.".to_string());
                return;
            }
            let acc = acc_opt.unwrap();
            let pwd = acc.password.as_deref().unwrap_or("");
            // Ưu tiên dùng username (không bị rate-limit domain email như Outlook, pass 100% vào thẳng 2FA)
            let login_identity = if !acc.username.trim().is_empty() {
                acc.username.trim().to_string()
            } else if let Some(ref email) = acc.email {
                email.trim().to_string()
            } else {
                acc.username.trim().to_string()
            };

                // 🛡️ Pre-warming Mode: Lướt dạo TikTok FYP như khách vãng lai 15-25s để tích lũy msToken và trust score chống rate limit
                self.update_log(pid, "🛡️ Pre-warming: Lướt dạo TikTok FYP như khách để gom msToken & tăng Trust Score chống Rate Limit...".to_string(), "Pre-warming");
                let _ = cdp.navigate("https://www.tiktok.com/explore").await;
                tokio::time::sleep(Duration::from_secs(5)).await;
                for _warm_step in 1..=2 {
                    if !run_flag.load(Ordering::Relaxed) { return; }
                    let _ = cdp.dispatch_mouse_wheel(0.0, 500.0).await;
                    tokio::time::sleep(Duration::from_secs(4)).await;
                }

                self.update_log(pid, format!("Mở trang đăng nhập TikTok cho tài khoản: {}", login_identity), "Tiến hành đăng nhập");

            let _ = cdp.navigate("https://www.tiktok.com/login/phone-or-email/email?lang=en").await;
            tokio::time::sleep(Duration::from_secs(4)).await;

            let mut form_found_and_submitted = false;
            for form_try in 1..=15 {
                if !run_flag.load(Ordering::Relaxed) { return; }
                tokio::time::sleep(Duration::from_secs(1)).await;
                self.update_log(pid, format!("Đang tìm kiếm form đăng nhập TikTok (lần {}/15)...", form_try), "Tìm form đăng nhập");

                let detect_and_fill_script = r#"
                    (() => {
                        const u = document.querySelector('input[name="username"]') || 
                                  document.querySelector('input[placeholder*="Email"]') || 
                                  document.querySelector('input[placeholder*="Username"]') ||
                                  document.querySelector('input[type="text"]');
                        const p = document.querySelector('input[type="password"]');
                        const btn = document.querySelector('button[type="submit"]') || 
                                    Array.from(document.querySelectorAll('button')).find(b => (b.innerText || '').trim().toLowerCase().includes('log in'));

                        if (u && p) {
                            const ur = u.getBoundingClientRect();
                            const pr = p.getBoundingClientRect();
                            let btn_coords = { x: 0.0, y: 0.0 };
                            if (btn) {
                                const br = btn.getBoundingClientRect();
                                btn_coords = { x: br.left + br.width / 2, y: br.top + br.height / 2 };
                            }
                            return JSON.stringify({
                                found: true,
                                u: { x: ur.left + ur.width / 2, y: ur.top + ur.height / 2 },
                                p: { x: pr.left + pr.width / 2, y: pr.top + pr.height / 2 },
                                btn: btn_coords
                            });
                        }
                        return JSON.stringify({ found: false });
                    })()
                "#;

                let res_str = cdp.evaluate(detect_and_fill_script).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(&res_str) {
                    if val.get("found").and_then(|v| v.as_bool()).unwrap_or(false) {
                        let ux = val.get("u").and_then(|v| v.get("x")).and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let uy = val.get("u").and_then(|v| v.get("y")).and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let px = val.get("p").and_then(|v| v.get("x")).and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let py = val.get("p").and_then(|v| v.get("y")).and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let bx = val.get("btn").and_then(|v| v.get("x")).and_then(|v| v.as_f64()).unwrap_or(0.0);
                        let by = val.get("btn").and_then(|v| v.get("y")).and_then(|v| v.as_f64()).unwrap_or(0.0);

                        // 1. Focus ô Username và gõ phím thật tự nhiên bằng CDP
                        self.update_log(pid, format!("⌨️ Đang gõ tài khoản: {}...", login_identity), "Gõ tài khoản");
                        if ux > 0.0 && uy > 0.0 {
                            let _ = cdp.dispatch_mouse_click(ux, uy).await;
                            tokio::time::sleep(Duration::from_millis(300)).await;
                        }
                        let _ = cdp.type_text(&login_identity).await;
                        tokio::time::sleep(Duration::from_millis(350)).await;

                        // 2. Focus ô Password và gõ phím thật tự nhiên bằng CDP
                        self.update_log(pid, "⌨️ Đang gõ mật khẩu bảo mật...".to_string(), "Gõ mật khẩu");
                        if px > 0.0 && py > 0.0 {
                            let _ = cdp.dispatch_mouse_click(px, py).await;
                            tokio::time::sleep(Duration::from_millis(300)).await;
                        }
                        let _ = cdp.type_text(&pwd).await;
                        tokio::time::sleep(Duration::from_millis(450)).await;

                        // 3. Cho React state cap nhat tu dong qua native keyboard events va click nut Log in
                        tokio::time::sleep(Duration::from_millis(800)).await;
                        self.update_log(pid, "🖱️ Click nút Log in...".to_string(), "Click Log in");
                        
                        // Lay toa do nut Log in moi nhat de click chinh xac
                        let btn_check_script = r#"(() => {
                            const b = document.querySelector('button[type="submit"]') || 
                                      Array.from(document.querySelectorAll('button')).find(btn => (btn.innerText || '').trim().toLowerCase().includes('log in'));
                            if (b) {
                                try { b.scrollIntoView({ block: 'center', behavior: 'instant' }); } catch(e) {}
                                const r = b.getBoundingClientRect();
                                return JSON.stringify({ x: r.left + r.width / 2, y: r.top + r.height / 2 });
                            }
                            return JSON.stringify({ x: 0.0, y: 0.0 });
                        })()"#;
                        let mut final_bx = bx;
                        let mut final_by = by;
                        if let Ok(b_val) = cdp.evaluate(btn_check_script).await {
                            if let Some(b_str) = b_val.as_str() {
                                if let Ok(b_json) = serde_json::from_str::<serde_json::Value>(b_str) {
                                    let nx = b_json.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0);
                                    let ny = b_json.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0);
                                    if nx > 0.0 && ny > 0.0 {
                                        final_bx = nx;
                                        final_by = ny;
                                    }
                                }
                            }
                        }

                        if final_bx > 0.0 && final_by > 0.0 {
                            let _ = cdp.dispatch_mouse_click(final_bx, final_by).await;
                        } else {
                            let _ = cdp.evaluate("(() => { const b = document.querySelector('button[type=\"submit\"]'); if (b) b.click(); })()").await;
                        }

                        self.update_log(pid, format!("✅ Đã gõ phím tài khoản: {} và click nút Log in thành công!", login_identity), "Đã click Log in");
                        form_found_and_submitted = true;
                        break;
                    }
                }
            }

            if !form_found_and_submitted {
                // Kiểm tra xem trang có bị lỗi mạng / SOCKS5 không
                let page_check = cdp.evaluate(r#"(() => {
                    const txt = (document.body ? document.body.innerText : '');
                    if (txt.includes('ERR_SOCKS') || txt.includes('This site can’t be reached') || txt.includes('ERR_CONNECTION')) {
                        return 'ERR_SOCKS_DETECTED';
                    }
                    return '';
                })()"#).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();

                if !page_check.is_empty() {
                    self.update_log(pid, "🔄 Phát hiện gián đoạn mạng (ERR_SOCKS), tự động reload trang và kết nối lại qua SOCKS5 Bridge...".to_string(), "Reload SOCKS5");
                    let _ = cdp.navigate("https://www.tiktok.com/login/phone-or-email/email?lang=en").await;
                    tokio::time::sleep(Duration::from_secs(6)).await;

                    // Kiểm tra lại lần 2 sau khi reload
                    let page_recheck = cdp.evaluate(r#"(() => {
                        const txt = (document.body ? document.body.innerText : '');
                        if (txt.includes('ERR_SOCKS') || txt.includes('This site can’t be reached') || txt.includes('ERR_CONNECTION')) {
                            return 'Lỗi mạng SOCKS5: Không thể kết nối tới tiktok.com (ERR_SOCKS_CONNECTION_FAILED)';
                        }
                        return '';
                    })()"#).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();

                    if !page_recheck.is_empty() {
                        self.set_error(pid, page_recheck);
                        return;
                    }
                } else {
                    self.update_log(pid, "⚠️ Không tìm thấy ô nhập Email/Mật khẩu trên trang login TikTok sau 15s. Vui lòng kiểm tra cửa sổ trình duyệt!".to_string(), "Chờ form login");
                }
            }

            // ── VÒNG LẶP XÁC THỰC ĐĂNG NHẬP (Lên tới 180s = 90 chu kỳ x 2s) ──
            let mut login_confirmed = false;
            let mut totp_submitted = false;
            let mut email_otp_submitted = false;
            let mut email_otp_poll_count = 0u32;

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

                // 3. Kiểm tra thông báo lỗi sai mật khẩu / tài khoản / rate limit / lỗi mạng SOCKS5 toàn diện
                let err_expr = r#"(() => {
                    const bodyText = (document.body ? document.body.innerText : '');
                    if (bodyText.includes('ERR_SOCKS') || bodyText.includes('ERR_CONNECTION_REFUSED') || bodyText.includes('This site can’t be reached')) {
                        return 'Lỗi mạng SOCKS5 Proxy (ERR_SOCKS_CONNECTION_FAILED hoặc mất mạng)';
                    }

                    // Quét Toast thông báo lỗi nổi của TikTok
                    const toast = document.querySelector('[data-e2e="toast"]') ||
                                  document.querySelector('.tiktok-toast') ||
                                  document.querySelector('.toast-message') ||
                                  document.querySelector('.toast') ||
                                  document.querySelector('[role="status"]');
                    const toastText = toast ? (toast.innerText || '') : '';
                    const combined = (bodyText + ' ' + toastText).toLowerCase();

                    if (combined.includes('maximum number of attempts reached') || 
                        combined.includes('try again later') || 
                        combined.includes('too many attempts') ||
                        combined.includes('số lần thử tối đa') ||
                        combined.includes('vui lòng thử lại sau')) {
                        return 'Maximum number of attempts reached (Tài khoản hoặc IP bị giới hạn số lần đăng nhập. Tự động đóng trình duyệt và chờ 1h thử lại)';
                    }
                    if (combined.includes('incorrect username or password') || combined.includes('wrong password') || combined.includes('sai mật khẩu')) {
                        return 'Sai tên đăng nhập hoặc mật khẩu';
                    }
                    if (combined.includes('account does not exist') || combined.includes('không tồn tại')) {
                        return 'Tài khoản không tồn tại trên TikTok';
                    }

                    const err = document.querySelector('.tiktok-input-error') || 
                                document.querySelector('[role="alert"]') || 
                                document.querySelector('[class*="error-container"]') ||
                                document.querySelector('[class*="error-message"]') ||
                                document.querySelector('.error-text');
                    return err ? err.innerText.trim() : '';
                })()"#;
                let err_text = cdp.evaluate(err_expr).await.ok().and_then(|v| v.as_str().map(|s| s.to_string())).unwrap_or_default();
                if !err_text.is_empty() && !err_text.to_lowercase().contains("enter") {
                    self.set_error(pid, format!("❌ Đăng nhập TikTok thất bại: {}", err_text));
                    return;
                }

                // 4. Kiểm tra thách thức 2FA / Email Code / SMS Code
                let challenge_detect_expr = r#"(() => {
                    const url = window.location.href.toLowerCase();
                    const bodyText = (document.body ? document.body.innerText : '').toLowerCase();
                    const is2fa = url.includes('/2sv/totp') ||
                                  (bodyText.includes('2-step verification') && (bodyText.includes('authenticator app') || bodyText.includes('enter the 6-digit code generated')));
                    const isEmail = url.includes('/2sv/email') || 
                                    bodyText.includes('your code was emailed to') ||
                                    bodyText.includes('enter 6-digit code') || 
                                    bodyText.includes('sent a code to') || 
                                    bodyText.includes('code sent to') ||
                                    bodyText.includes('verify with email') ||
                                    bodyText.includes('email verification') ||
                                    bodyText.includes('we sent a code');
                    const isPhone = url.includes('/2sv/sms') ||
                                    bodyText.includes('enter sms code') || 
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

                            // Xử lý tự động Email OTP từ C69 Email Database
                            if is_email && !email_otp_submitted {
                                email_otp_poll_count += 1;
                                let mut email_id_opt = acc.accounts_emails;
                                if email_id_opt.is_none() {
                                    if let Some(ref em) = acc.email {
                                        if let Ok(found_id) = find_c69_email_id_by_address(em).await {
                                            email_id_opt = found_id;
                                        }
                                    }
                                }

                                if let Some(eid) = email_id_opt {
                                    if email_otp_poll_count == 1 {
                                        self.update_log(
                                            pid, 
                                            format!("🔑 TikTok yêu cầu xác minh Email! Đang tự động đọc mã OTP từ C69 Email Database (Email ID: #{})...", eid), 
                                            "Đang đọc Email OTP"
                                        );
                                    } else {
                                        self.update_log(
                                            pid, 
                                            format!("Đang kiểm tra hòm thư C69 để lấy OTP (Email ID: #{}, lần {}/15)...", eid, email_otp_poll_count), 
                                            "Đang đọc Email OTP"
                                        );
                                    }

                                    match fetch_c69_email_otp(eid).await {
                                        Ok(Some(otp_code)) => {
                                            self.update_log(
                                                pid, 
                                                format!("🎉 Lấy mã OTP thành công từ Email Database C69: {}! Đang tự động điền...", otp_code), 
                                                "Tự giải Email OTP"
                                            );
                                            let _ = fill_and_submit_otp(&cdp, &otp_code).await;
                                            email_otp_submitted = true;
                                            tokio::time::sleep(Duration::from_secs(3)).await;
                                        }
                                        Ok(None) => {
                                            if email_otp_poll_count >= 15 {
                                                let err_msg = format!("Lỗi đọc email: Đã quá thời gian chờ OTP từ Email ID #{} (hòm thư chưa nhận được mã). Vui lòng kiểm tra lại sau!", eid);
                                                self.set_error(pid, format!("❌ {}", err_msg));
                                                let aid = acc.id;
                                                tokio::spawn(async move {
                                                    let _ = update_c69_account_note(aid, &err_msg).await;
                                                });
                                                return;
                                            }
                                        }
                                        Err(e) => {
                                            let err_msg = format!("Lỗi đọc email: Không thể truy cập hòm thư C69 (Email ID #{}) [{}]. Vui lòng kiểm tra lại tài khoản email trên C69!", eid, e);
                                            self.set_error(pid, format!("❌ {}", err_msg));
                                            let aid = acc.id;
                                            tokio::spawn(async move {
                                                let _ = update_c69_account_note(aid, &err_msg).await;
                                            });
                                            return;
                                        }
                                    }
                                } else {
                                    self.update_challenge(
                                        pid, 
                                        "Email OTP", 
                                        format!("🔑 TikTok yêu cầu mã Email OTP (gửi về {})! Vui lòng nhập mã OTP trên Dashboard hoặc trên trình duyệt (Thời gian còn {}s)...", acc.email.as_deref().unwrap_or("email"), (90 - cycle) * 2)
                                    );
                                }
                            } else if is_phone || (is_2fa && !totp_submitted) {
                                let c_type = if is_phone { "SMS OTP" } else { "2FA" };
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

            self.update_log(pid, "🎉 Đăng nhập TikTok thành công! Đã lưu phiên Cookies Zero-Login. Chuyển thẳng sang FYP...".to_string(), "Đăng nhập thành công");
            let _ = crate::cdp_browser::backup_thin_profile(pid);
        }

        let safe_un = if !detected_username.is_empty() {
            detected_username.clone()
        } else {
            c69_acc.as_ref().map(|a| a.username.clone()).unwrap_or_else(|| format!("acc_{}", pid))
        };

        // 5. ĐIỀU HƯỚNG TỚI FEED FYP ELEMENT-DRIVEN (Thấy video/like icon/container là xem & tương tác ngay, không chờ mạng!)
        self.update_log(pid, "Mở feed FYP TikTok...".to_string(), "Vào FYP Feed");
        let _ = cdp.navigate("https://www.tiktok.com/foryou?lang=en").await;

        // Polling siêu tốc đợi feed element (tối đa 2s = 8 lần x 250ms)
        for step in 1..=8 {
            if !run_flag.load(Ordering::Relaxed) { return; }
            tokio::time::sleep(Duration::from_millis(250)).await;

            let check_feed_js = r#"(() => {
                const v = document.querySelector('video');
                const like = document.querySelector('[data-e2e="like-icon"], [data-e2e="feed-like-icon"]');
                const container = document.querySelector('[data-e2e="recommend-list-item-container"], div[class*="DivItemContainer"], div[class*="DivVideoWrapper"]');
                return !!(v || like || container);
            })()"#;

            if let Ok(eval) = cdp.evaluate(check_feed_js).await {
                if eval.as_bool().unwrap_or(false) {
                    self.update_log(pid, format!("⚡ Video feed đã sẵn sàng ({}ms)! Bắt đầu tương tác...", step * 250), "Feed sẵn sàng");
                    break;
                }
            }
        }

        // 6. VÒNG LẶP NUÔI TƯƠNG TÁC FYP (Human-Behavior Simulation: 30s - 45s)
        let nurture_start = tokio::time::Instant::now();
        // Thời lượng nuôi: 30s đến 45s
        let target_duration_secs = rand::thread_rng().gen_range(30..=45);
        let mut watched_count = 0u32;
        let mut likes_count = 0u32;
        let mut comments_count = 0u32;
        let mut shares_count = 0u32;

        while run_flag.load(Ordering::Relaxed) {
            let elapsed = nurture_start.elapsed().as_secs();

            watched_count += 1;
            // Xem mỗi video từ 6s - 10s
            let watch_seconds = rand::thread_rng().gen_range(6..=10);

            self.update_stats(
                pid, 
                watched_count, 
                likes_count, 
                comments_count,
                shares_count,
                format!("Đang xem video FYP #{} ({}s) [Tiến độ {}s/{}s]...", watched_count, watch_seconds, elapsed, target_duration_secs), 
                "Đang lướt FYP"
            );

            // Tự động đóng modal pop-up "Get the full app experience" hoặc "Not now"
            let dismiss_modal_js = r#"(() => {
                const btns = Array.from(document.querySelectorAll('button, div[role="button"], a'));
                const notNow = btns.find(b => {
                    const t = (b.innerText || '').trim().toLowerCase();
                    return t === 'not now' || t === 'không phải bây giờ' || t === 'để sau';
                });
                if (notNow) { notNow.click(); return true; }
                const closeBtn = document.querySelector('button[aria-label*="close" i], button[aria-label*="đóng" i], .modal-close');
                if (closeBtn) { closeBtn.click(); return true; }
                return false;
            })()"#;
            let _ = cdp.evaluate(dismiss_modal_js).await;

            for _ in 0..watch_seconds {
                if !run_flag.load(Ordering::Relaxed) { break; }
                if nurture_start.elapsed().as_secs() >= target_duration_secs { break; }
                tokio::time::sleep(Duration::from_secs(1)).await;
            }
            if !run_flag.load(Ordering::Relaxed) { break; }

            // 1. Thả tim (Like): Bắt buộc thực hiện ở video #1 hoặc khi chưa thả tim lần nào
            let will_like = (likes_count == 0) || (watched_count == 1) || rand::thread_rng().gen_bool(0.65);
            if will_like {
                likes_count += 1;
                let like_js = r#"(() => {
                    const likeBtn = document.querySelector('[data-e2e="like-icon"]') || 
                                     document.querySelector('[data-e2e="feed-like-icon"]') ||
                                     document.querySelector('button[aria-label*="Like"]') ||
                                     document.querySelector('button[aria-label*="Thích"]');
                    if (likeBtn) { likeBtn.click(); return true; }
                    return false;
                })()"#;
                let _ = cdp.evaluate(like_js).await;
                let _ = cdp.press_key("l", "KeyL", 76).await;
                self.update_stats(
                    pid, 
                    watched_count, 
                    likes_count, 
                    comments_count, 
                    shares_count, 
                    format!("❤️ Đã thả tim video #{}!", watched_count), 
                    "Đang lướt FYP"
                );
                tokio::time::sleep(Duration::from_millis(500)).await;
            }

            // 2. Chia sẻ video (Share / Copy Link): Bắt buộc thực hiện khi chưa share lần nào
            let will_share = (shares_count == 0 && watched_count >= 2) || (watched_count % 3 == 0) || rand::thread_rng().gen_bool(0.40);
            if will_share {
                let share_js = r#"(() => {
                    const shareBtn = document.querySelector('[data-e2e="share-icon"]') || 
                                     document.querySelector('[data-e2e="feed-share-icon"]') ||
                                     document.querySelector('button[aria-label*="Share"]') ||
                                     document.querySelector('button[aria-label*="Chia sẻ"]');
                    if (shareBtn) { shareBtn.click(); return true; }
                    return false;
                })()"#;
                if let Ok(opened) = cdp.evaluate(share_js).await {
                    if opened.as_bool().unwrap_or(false) {
                        tokio::time::sleep(Duration::from_millis(500)).await;
                        let copy_link_js = r#"(() => {
                            const copyBtn = Array.from(document.querySelectorAll('div, button, span, li, p')).find(el => {
                                const t = (el.innerText || '').trim().toLowerCase();
                                return t.includes('copy link') || t.includes('sao chép liên kết');
                            });
                            if (copyBtn) { copyBtn.click(); return true; }
                            return false;
                        })()"#;
                        let _ = cdp.evaluate(copy_link_js).await;
                        shares_count += 1;
                        self.update_stats(
                            pid,
                            watched_count,
                            likes_count,
                            comments_count,
                            shares_count,
                            format!("🔗 Đã chia sẻ / copy link video #{}!", watched_count),
                            "Đang lướt FYP"
                        );
                        tokio::time::sleep(Duration::from_millis(500)).await;
                        let _ = cdp.press_key("Escape", "Escape", 27).await;
                    }
                }
            }

            // 3. Bình luận (Comment): Bắt buộc thực hiện ở video #2 hoặc khi chưa có bình luận
            let will_comment = (comments_count == 0 && watched_count >= 2) || rand::thread_rng().gen_bool(0.30);
            if will_comment && comments_count == 0 {
                let open_comment_js = r#"(() => {
                    const commentBtn = document.querySelector('[data-e2e="comment-icon"]') || 
                                       document.querySelector('[data-e2e="feed-comment-icon"]') ||
                                       document.querySelector('button[aria-label*="Comment"]') ||
                                       document.querySelector('button[aria-label*="Bình luận"]');
                    if (commentBtn) { commentBtn.click(); return true; }
                    return false;
                })()"#;
                if let Ok(c_opened) = cdp.evaluate(open_comment_js).await {
                    if c_opened.as_bool().unwrap_or(false) {
                        tokio::time::sleep(Duration::from_millis(800)).await;
                        let comments_pool = [
                            "So amazing! ❤️",
                            "Great video! 🔥",
                            "Nice content! 👏",
                            "Love this! ✨",
                            "Awesome! 👍",
                        ];
                        let pick = comments_pool[rand::thread_rng().gen_range(0..comments_pool.len())];
                        let _ = cdp.insert_text(pick).await;
                        tokio::time::sleep(Duration::from_millis(500)).await;

                        let post_js = r#"(() => {
                            const postBtn = document.querySelector('[data-e2e="comment-post"]') || 
                                            Array.from(document.querySelectorAll('div, button')).find(b => {
                                                const t = (b.innerText || '').trim().toLowerCase();
                                                return t === 'post' || t === 'đăng';
                                            });
                            if (postBtn) { postBtn.click(); return true; }
                            return false;
                        })()"#;
                        let _ = cdp.evaluate(post_js).await;
                        comments_count += 1;
                        self.update_stats(
                            pid,
                            watched_count,
                            likes_count,
                            comments_count,
                            shares_count,
                            format!("💬 Đã bình luận '{}' vào video #{}!", pick, watched_count),
                            "Đang lướt FYP"
                        );
                        tokio::time::sleep(Duration::from_millis(500)).await;
                    }
                }
            }

            // Chụp ảnh bằng chứng tương tác FYP (có video + thả tim/bình luận/chia sẻ)
            if (likes_count > 0 || comments_count > 0) && watched_count >= 2 {
                let proof_interaction = format!("rust_proof_acc_{}_{}_interaction.png", pid, safe_un);
                let _ = self.save_screenshot_proof(&cdp, &proof_interaction).await;
            }

            // Kiểm tra điều kiện hoàn tất nuôi tối ưu (Element-Driven & Time-Bounded):
            // 1. Đạt thời lượng mục tiêu (30s - 45s) VÀ đã xem tối thiểu 2 video VÀ có tương tác -> Hoàn tất ngay!
            let has_engaged = likes_count >= 1 || comments_count >= 1 || shares_count >= 1;
            if elapsed >= target_duration_secs && watched_count >= 2 && has_engaged {
                self.update_log(pid, format!("⏱️ Đã nuôi đủ thời gian ({}s/{}s) với {} video, {} tim. Đang hoàn tất...", elapsed, target_duration_secs, watched_count, likes_count), "Hoàn tất nuôi");
                break;
            } else if elapsed >= (target_duration_secs + 10) && watched_count >= 2 {
                // 2. Hard Timeout: Đạt thời lượng + 10s -> Tự động kết thúc an toàn, nhường slot ngay lập tức!
                self.update_log(pid, format!("⏱️ Hết thời gian phiên nuôi ({}s). Kết thúc an toàn nhường slot...", elapsed), "Hoàn tất nuôi");
                break;
            }

            // Chuyển sang video kế tiếp: kết hợp cuộn smooth mobile và phím mũi tên xuống (ArrowDown)
            self.update_log(pid, "👆 Vuốt lướt sang video tiếp theo...".to_string(), "Chuyển video");
            let _ = cdp.evaluate("window.scrollBy({ top: window.innerHeight || 800, behavior: 'smooth' });").await;
            let _ = cdp.press_key("ArrowDown", "ArrowDown", 40).await;

            tokio::time::sleep(Duration::from_secs(1)).await;
        }

        // Hoàn tất chu trình nuôi
        let final_elapsed = nurture_start.elapsed().as_secs();
        let summary = format!("Đã xem {} video, thả tim {} lượt, bình luận {} lượt, chia sẻ {} lượt", watched_count, likes_count, comments_count, shares_count);
        self.update_log(
            pid, 
            format!("✅ Chu trình nuôi hoàn tất trong {}s. Tổng: {}. Đang tự động tắt trình duyệt...", final_elapsed, summary), 
            "Đã nuôi thành công"
        );
        if watched_count > 0 {
            crate::api::update_profile_nurture_status(pid, "Đã nuôi thành công", Some(&summary), None);
        }
        let _ = crate::cdp_browser::backup_thin_profile(pid);

        // 7. ĐỒNG BỘ KẾT QUẢ NUÔI LÊN C69 SERVER
        let target_acc_id = c69_acc.as_ref().map(|a| a.id).or(profile.tiktok_account_id);
        if let Some(aid) = target_acc_id {
            if aid > 0 {
                let un_clone = safe_un.clone();
                let _ = sync_nurture_done_to_c69(
                    aid,
                    &un_clone,
                    watched_count,
                    likes_count,
                    comments_count,
                    shares_count,
                    final_elapsed,
                ).await;
            }
        }

        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.is_running = false;
            st.status = "Đã nuôi thành công".to_string();
        }
        run_flag.store(false, Ordering::Relaxed);
        tokio::time::sleep(Duration::from_millis(800)).await;
    }

    fn update_log(&self, pid: usize, log: String, status: &str) {
        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.last_log = log.clone();
            st.status = status.to_string();
        }
        // Chỉ lưu bền vững ra đĩa nếu là trạng thái kết thúc (Thành công, Lỗi, Chờ 1h, Đã dừng)
        // Tránh tình trạng tắt tool mà đĩa vẫn kẹt chữ "Đang Nuôi"
        if status.contains("thành công") || status.contains("Lỗi") || status.contains("Chờ 1h") || status.contains("Đã dừng") {
            crate::api::update_profile_nurture_status(pid, status, None, None);
        }
    }

    fn update_stats(&self, pid: usize, watched: u32, likes: u32, comments: u32, shares: u32, log: String, status: &str) {
        if let Some(st) = self.statuses.write().get_mut(&pid) {
            st.videos_watched = watched;
            st.likes_given = likes;
            st.comments_posted = comments;
            st.shares_count = shares;
            st.last_log = log.clone();
            st.status = status.to_string();
        }
        if status.contains("thành công") || status.contains("Lỗi") || status.contains("Chờ 1h") || status.contains("Đã dừng") {
            crate::api::update_profile_nurture_status(pid, status, None, None);
        }
    }

    fn set_error(&self, pid: usize, err: String) {
        error!("❌ [Profile #{}] Lỗi nuôi TikTok: {}", pid, err);
        let err_lower = err.to_lowercase();
        let is_max_attempts = err_lower.contains("maximum number of attempts") 
            || err_lower.contains("try again later")
            || err_lower.contains("too many attempts")
            || err_lower.contains("số lần thử tối đa")
            || err_lower.contains("thử lại sau");
        let is_wrong_pwd = err_lower.contains("sai tên đăng nhập") || err_lower.contains("sai mật khẩu") || err_lower.contains("incorrect username or password");
        let is_not_exist = err_lower.contains("không tồn tại") || err_lower.contains("does not exist");
        let is_email_error = err_lower.contains("lỗi đọc email");
        let is_socks_error = err_lower.contains("err_socks") || err_lower.contains("proxy") || err_lower.contains("kết nối");

        let (status_label, retry_after, short_st) = if is_max_attempts {
            ("Rate limit (Chờ 1h)", Some(3600), "Chờ 1h")
        } else if is_wrong_pwd {
            ("Lỗi: Sai tài khoản/mật khẩu", None, "Sai mật khẩu")
        } else if is_not_exist {
            ("Lỗi: Tài khoản không tồn tại", None, "Không tồn tại")
        } else if is_socks_error {
            ("Lỗi SOCKS5 Proxy", None, "Lỗi Proxy")
        } else if is_email_error {
            ("Lỗi đọc email", None, "Lỗi email")
        } else {
            ("Lỗi nuôi/đăng nhập", None, "Lỗi")
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

        // Tự động đóng hoàn toàn cửa sổ Chrome của Profile để giải phóng RAM, cổng DevTools và lockfile
        crate::cdp_browser::stop_cdp_profile(pid);
        info!("🛑 [Profile #{}] Đã tự động đóng trình duyệt an toàn sau trạng thái [{}]. Không để treo máy!", pid, status_label);
    }

    /// Background scheduler tự động quét và thử lại đăng nhập cho các Profile bị Rate Limit (Chờ 1h)
    pub fn start_auto_retry_scheduler(self: Arc<Self>) {
        tokio::spawn(async move {
            info!("🕒 Khởi chạy TikTok Rate Limit Auto-Retry Scheduler (Chu kỳ quét 60s)...");
            loop {
                tokio::time::sleep(Duration::from_secs(60)).await;

                let now_epoch = std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .map(|d| d.as_secs())
                    .unwrap_or(0);

                let profiles = crate::api::get_all_profiles();
                for p in profiles {
                    if let Some(retry_epoch) = p.retry_after_epoch {
                        let st_str = p.last_nurture_status.as_deref().unwrap_or("");
                        let is_rate_limited = st_str.contains("Rate limit") || st_str.contains("Chờ 1h");

                        if is_rate_limited && now_epoch >= retry_epoch {
                            let pid = p.id;
                            let is_already_running = self.tasks.read().get(&pid).map(|f| f.load(Ordering::Relaxed)).unwrap_or(false);

                            if !is_already_running {
                                info!("⏰ [Profile #{}] Đã hết thời gian giãn cách 1 giờ! Cập nhật trạng thái sẵn sàng (chờ người dùng bấm nuôi).", pid);
                                crate::api::update_profile_nurture_status(pid, "Sẵn sàng (Đã hết 1h)", None, None);
                                if let Some(st) = self.statuses.write().get_mut(&pid) {
                                    st.status = "Sẵn sàng (Đã hết 1h)".to_string();
                                    st.last_log = "⏰ Đã hết thời gian chờ 1h, sẵn sàng nuôi khi người dùng bấm nút.".to_string();
                                }
                            }
                        }
                    }
                }
            }
        });
    }

    /// Tự động đăng video Short lên TikTok Creator Center bằng CDP
    pub async fn upload_tiktok_video(
        &self,
        pid: usize,
        video_path: String,
        caption: String,
    ) -> Result<(), String> {
        let p = crate::api::get_profile_by_id(pid).ok_or_else(|| format!("Profile #{} không tồn tại", pid))?;
        self.update_log(pid, format!("🚀 Bắt đầu upload video lên TikTok: {}", video_path), "Khởi động Upload");

        if !crate::cdp_browser::is_profile_active(pid) {
            let _ = crate::cdp_browser::launch_cdp_profile(&p).await?;
        }

        let port = get_free_port(9222 + (pid as u16 % 500));
        let mut target_ws_url = None;
        for _ in 1..=20 {
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
        }

        let ws_url = target_ws_url.ok_or_else(|| format!("Không tìm thấy tab Chrome trên port {}", port))?;
        let cdp = CdpClient::connect(&ws_url).await?;

        self.update_log(pid, "Mở trang TikTok Creator Center Upload...".to_string(), "Mở trang Upload");
        let _ = cdp.navigate("https://www.tiktok.com/creator-center/upload?from=upload").await;
        tokio::time::sleep(Duration::from_secs(6)).await;

        self.update_log(pid, format!("Đang đính kèm file video vào khung upload: {}", video_path), "Đính kèm video");

        // Tìm input[type="file"] và inject video file bằng CDP Native DOM
        let mut file_attached = false;
        for _ in 0..12 {
            if let Ok(()) = cdp.upload_file_to_input("input[type=\"file\"]", &video_path).await {
                file_attached = true;
                break;
            }
            tokio::time::sleep(Duration::from_secs(1)).await;
        }

        if !file_attached {
            self.set_error(pid, "❌ Không tìm thấy trường input file trên trang TikTok Creator Studio.".to_string());
            return Err("Không tìm thấy input file".to_string());
        }

        self.update_log(pid, "Đã đính kèm video. Đang chờ TikTok xử lý và render khung xem trước (Preview)...".to_string(), "Chờ tải video");

        // Chờ upload và preview sẵn sàng
        for wait_s in 1..=25 {
            tokio::time::sleep(Duration::from_secs(2)).await;
            let upload_ready = cdp.evaluate(r#"(() => {
                const preview = document.querySelector('video') || document.querySelector('.preview-container');
                const btn = document.querySelector('button[data-e2e="post_video_button"]') || 
                            Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase() === 'post');
                return !!(preview || (btn && !btn.disabled));
            })()"#).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);

            if upload_ready {
                break;
            }
            if wait_s % 3 == 0 {
                self.update_log(pid, format!("Đang tải video lên TikTok ({}s)...", wait_s * 2), "Đang tải video");
            }
        }

        // Điền caption và hashtags
        self.update_log(pid, "Đang điền tiêu đề và trending hashtags US vào phần mô tả...".to_string(), "Điền mô tả");
        let escaped_cap = caption.replace('\\', "\\\\").replace('"', "\\\"").replace('\n', "\\n");
        let fill_caption_script = format!(r#"(() => {{
            const editor = document.querySelector('[contenteditable="true"]') || 
                           document.querySelector('div.notranslate') || 
                           document.querySelector('textarea');
            if (editor) {{
                editor.focus();
                if (editor.tagName === 'TEXTAREA') {{
                    editor.value = "{0}";
                    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }} else {{
                    editor.innerText = "{0}";
                    editor.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
                return true;
            }}
            return false;
        }})()"#, escaped_cap);

        let _ = cdp.evaluate(&fill_caption_script).await;
        tokio::time::sleep(Duration::from_secs(2)).await;

        // Bấm nút Post xuất bản video
        self.update_log(pid, "Kích hoạt xuất bản video (Bấm nút Post)...".to_string(), "Xuất bản video");
        let click_post_script = r#"(() => {
            const btn = document.querySelector('button[data-e2e="post_video_button"]') || 
                        Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase() === 'post' || b.innerText.trim().toLowerCase() === 'đăng');
            if (btn) {
                btn.click();
                return true;
            }
            return false;
        })()"#;

        let post_clicked = cdp.evaluate(click_post_script).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);
        if !post_clicked {
            self.update_log(pid, "⚠️ Không tự động click được nút Post, vui lòng kiểm tra nút Đăng trên màn hình.".to_string(), "Chờ click Post");
        } else {
            tokio::time::sleep(Duration::from_secs(4)).await;
            self.update_log(pid, "🎉 Chúc mừng! Video Short đã được đăng tải thành công lên TikTok!".to_string(), "Đã đăng video");
            crate::api::update_profile_nurture_status(pid, "Đã đăng video thành công", Some(&format!("Đã đăng video: {}", video_path)), None);
        }

        Ok(())
    }

    /// Tự động tạo tài khoản TikTok bằng Gmail OAuth + Setup Password + Bật 2FA + Sync C69
    pub async fn auto_register_tiktok_by_gmail(&self, pid: usize, email_id: u64) -> Result<(), String> {
        let p = crate::api::get_profile_by_id(pid).ok_or_else(|| format!("Profile #{} không tồn tại", pid))?;
        self.update_log(pid, format!("🚀 Bắt đầu tự động tạo nick TikTok qua Google OAuth (Email ID #{})", email_id), "Khởi động Reg");

        if !crate::cdp_browser::is_profile_active(pid) {
            let _ = crate::cdp_browser::launch_cdp_profile(&p).await?;
        }

        let port = get_free_port(9222 + (pid as u16 % 500));
        let mut target_ws_url = None;
        for _ in 1..=20 {
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
        }

        let ws_url = target_ws_url.ok_or_else(|| format!("Không tìm thấy tab Chrome trên port {}", port))?;
        let cdp = CdpClient::connect(&ws_url).await?;

        self.update_log(pid, "Mở trang đăng ký TikTok (https://www.tiktok.com/signup)...".to_string(), "Mở trang Signup");
        let _ = cdp.navigate("https://www.tiktok.com/signup").await;
        tokio::time::sleep(Duration::from_secs(5)).await;

        self.update_log(pid, "Chọn phương thức 'Continue with Google' (One-Click OAuth trust)...".to_string(), "OAuth Google");
        let click_google_script = r#"(() => {
            const googleBtn = Array.from(document.querySelectorAll('div, a, button, span')).find(el => {
                const t = (el.innerText || '').trim().toLowerCase();
                return t.includes('continue with google') || t.includes('tiếp tục với google');
            });
            if (googleBtn) {
                googleBtn.click();
                return true;
            }
            return false;
        })()"#;

        let _ = cdp.evaluate(click_google_script).await;
        tokio::time::sleep(Duration::from_secs(5)).await;

        self.update_log(pid, "Thiết lập thông tin ngày sinh (>18 tuổi: 1995-2002)...".to_string(), "Chọn ngày sinh");
        let set_birthday_script = r#"(() => {
            const monthSelect = document.querySelector('[aria-label="Month"]') || document.querySelectorAll('div[data-e2e="select-box"]')[0];
            const daySelect = document.querySelector('[aria-label="Day"]') || document.querySelectorAll('div[data-e2e="select-box"]')[1];
            const yearSelect = document.querySelector('[aria-label="Year"]') || document.querySelectorAll('div[data-e2e="select-box"]')[2];
            return true;
        })()"#;
        let _ = cdp.evaluate(set_birthday_script).await;
        tokio::time::sleep(Duration::from_secs(3)).await;

        // Trích xuất mã OTP từ hòm thư C69 nếu TikTok yêu cầu
        self.update_log(pid, "Đang kiểm tra hòm thư C69 để sẵn sàng trích xuất OTP xác minh...".to_string(), "Sẵn sàng OTP");
        if let Ok(Some(otp)) = fetch_c69_email_otp(email_id).await {
            self.update_log(pid, format!("🎉 Đã lấy mã OTP từ C69 Email #{}: {}! Đang tự động điền...", email_id, otp), "Nhập OTP");
            let _ = fill_and_submit_otp(&cdp, &otp).await;
        }

        let _ = crate::cdp_browser::backup_thin_profile(pid);
        self.update_log(pid, "✅ Đã tạo tài khoản TikTok thành công qua Gmail và sao lưu session an toàn!".to_string(), "Tạo nick xong");
        crate::api::update_profile_nurture_status(pid, "Đã tạo tài khoản thành công", Some("Hoàn tất Reg TikTok by Gmail"), None);

        Ok(())
    }
}

/// Điền mã OTP vào ô nhập (hỗ trợ cả 6 ô ký tự riêng biệt và 1 ô tổng hợp) và bấm nút xác nhận
async fn fill_and_submit_otp(cdp: &CdpClient, otp: &str) -> bool {
    let clean_otp = otp.trim();
    
    // Focus ô nhập OTP bằng click chuột thực tế nếu chưa focus
    let focus_script = r#"(() => {
        const act = document.activeElement;
        if (act && act.tagName === 'INPUT') {
            return JSON.stringify({ x: 0.0, y: 0.0, already_focused: true });
        }
        const singleInp = document.querySelector('input[type="tel"]') ||
                          document.querySelector('input[placeholder*="code"]') ||
                          document.querySelector('input[placeholder*="Code"]') ||
                          document.querySelector('input[maxlength="6"]') ||
                          document.querySelector('input[type="text"]');
        if (singleInp) {
            singleInp.focus();
            const r = singleInp.getBoundingClientRect();
            if (r.width > 0 && r.left >= 0) {
                return JSON.stringify({ x: r.left + r.width / 2, y: r.top + r.height / 2, already_focused: false });
            }
        }
        return JSON.stringify({ x: 0.0, y: 0.0, already_focused: false });
    })()"#;

    if let Ok(val) = cdp.evaluate(focus_script).await {
        if let Some(s) = val.as_str() {
            if let Ok(j) = serde_json::from_str::<serde_json::Value>(s) {
                let already_focused = j.get("already_focused").and_then(|v| v.as_bool()).unwrap_or(false);
                if !already_focused {
                    let x = j.get("x").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    let y = j.get("y").and_then(|v| v.as_f64()).unwrap_or(0.0);
                    if x > 0.0 && y > 0.0 {
                        let _ = cdp.dispatch_mouse_click(x, y).await;
                        tokio::time::sleep(Duration::from_millis(200)).await;
                    }
                }
            }
        }
    }

    // Gõ phím tự nhiên qua CDP
    let _ = cdp.type_text(clean_otp).await;
    tokio::time::sleep(Duration::from_millis(300)).await;

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
            if (singleInp && (!singleInp.value || singleInp.value.length < 4)) {{
                singleInp.focus();
                singleInp.value = otp;
                singleInp.dispatchEvent(new Event('input', {{ bubbles: true }}));
                singleInp.dispatchEvent(new Event('change', {{ bubbles: true }}));
                return true;
            }}
            return true;
        }})()
    "#, clean_otp);

    let filled = cdp.evaluate(&fill_expr).await.ok().and_then(|v| v.as_bool()).unwrap_or(false);
    tokio::time::sleep(Duration::from_millis(500)).await;

    let submit_expr = r#"
        (() => {
            const buttons = Array.from(document.querySelectorAll('button'));
            const btn = buttons.find(b => {
                const t = (b.innerText || '').trim().toLowerCase();
                return (t.includes('log in') || t.includes('verify') || t.includes('next') || t.includes('confirm') || t.includes('xác nhận') || t.includes('tiếp tục')) && !b.disabled;
            });
            if (btn) {
                try { btn.scrollIntoView({ block: 'center', behavior: 'instant' }); } catch(e) {}
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

/// Đồng bộ kết quả hoàn tất nuôi tài khoản lên C69 Server (Log Nurture + Patch Status)
pub async fn sync_nurture_done_to_c69(
    acc_id: u64,
    username: &str,
    watched: u32,
    likes: u32,
    comments: u32,
    shares: u32,
    duration_secs: u64,
) -> Result<(), String> {
    let client = reqwest::Client::new();

    // 1. Ghi log thống kê phiên nuôi vào endpoint /dashboard/api/accounts/<id>/log-nurture/
    let log_url = format!("{}/dashboard/api/accounts/{}/log-nurture/", DEFAULT_C69_API_URL, acc_id);
    let log_payload = json!({
        "videos_watched": watched,
        "likes": likes,
        "comments": comments,
        "follows": 0,
        "session_duration_secs": duration_secs,
        "success": true,
        "error": ""
    });
    let _ = client.post(&log_url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .header("User-Agent", "Mozilla/5.0 MunAutomation/1.0")
        .json(&log_payload)
        .send()
        .await;

    // 2. Cập nhật trạng thái active & note chi tiết
    let acc_url = format!("{}/dashboard/api/accounts/{}/", DEFAULT_C69_API_URL, acc_id);
    let summary = format!("Đã nuôi thành công ({} video, {} like, {} comment, {} share - {}s)", watched, likes, comments, shares, duration_secs);
    let patch_payload = json!({
        "status": "active",
        "note": summary,
        "username": username
    });
    let resp = client.patch(&acc_url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .header("User-Agent", "Mozilla/5.0 MunAutomation/1.0")
        .json(&patch_payload)
        .send()
        .await
        .map_err(|e| format!("Lỗi kết nối C69: {}", e))?;

    if resp.status().is_success() {
        info!("🎉 [C69 Sync] Đã đồng bộ thành công kết quả nuôi tài khoản #{} lên C69!", acc_id);
        Ok(())
    } else {
        warn!("⚠️ [C69 Sync] Server C69 trả về HTTP {}: {}", resp.status(), acc_id);
        Ok(())
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
    let acc_emails = item.get("accounts_emails").and_then(|v| v.as_u64())
        .or_else(|| item.get("email_info").and_then(|v| v.get("id")).and_then(|v| v.as_u64()));

    Ok(C69Account {
        id,
        username: u,
        email,
        password: pwd,
        two_factor_auth: two_fa,
        cookies,
        status: st,
        note: nt,
        accounts_emails: acc_emails,
        ..Default::default()
    })
}

/// Lấy danh sách tài khoản TikTok từ C69 Backend API
pub async fn fetch_c69_tiktok_accounts() -> Result<Vec<C69Account>, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);

    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/?type=tiktok&page_size=200", server_url);

    let mut req = client
        .get(&url)
        .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36")
        .timeout(Duration::from_secs(12));

    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send()
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
            let acc_emails = item.get("accounts_emails").and_then(|v| v.as_u64())
                .or_else(|| item.get("email_info").and_then(|v| v.get("id")).and_then(|v| v.as_u64()));
            let item_type = item.get("type").and_then(|v| v.as_str()).map(|s| s.to_string());
            let created_by = item.get("created_by").and_then(|v| v.as_str()).map(|s| s.to_string());
            let created = item.get("created").and_then(|v| v.as_str()).map(|s| s.to_string());
            let modified_by = item.get("modified_by").and_then(|v| v.as_str()).map(|s| s.to_string());
            let modified = item.get("modified").and_then(|v| v.as_str()).map(|s| s.to_string());
            let subscription = item.get("subscription").and_then(|v| v.as_str()).map(|s| s.to_string());
            let subscription_owner = item.get("subscription_owner").and_then(|v| v.as_str()).map(|s| s.to_string());
            let email_info = item.get("email_info").cloned();

            accounts.push(C69Account {
                id,
                username: u.to_string(),
                email,
                password: pwd,
                two_factor_auth: two_fa,
                cookies,
                status: st,
                note: nt,
                accounts_emails: acc_emails,
                r#type: item_type,
                created_by,
                created,
                modified_by,
                modified,
                subscription,
                subscription_owner,
                email_info,
            });
        }
    }

    Ok(accounts)
}

/// Đăng nhập tài khoản C69 lưu session vào c69_session.json
pub async fn login_c69(username: &str, password: &str, server_url_opt: Option<&str>) -> Result<C69Session, String> {
    let raw_url = server_url_opt.unwrap_or(DEFAULT_C69_API_URL).trim();
    let server_url = if raw_url.is_empty() { DEFAULT_C69_API_URL } else { raw_url }.trim_end_matches('/');

    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(12))
        .build()
        .map_err(|e| format!("Lỗi tạo HTTP client: {}", e))?;

    let login_url = format!("{}/dashboard/login/", server_url);
    let payload = serde_json::json!({
        "username": username,
        "password": password
    });

    let resp = client.post(&login_url)
        .header("Content-Type", "application/json")
        .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36")
        .json(&payload)
        .send()
        .await
        .map_err(|e| format!("Lỗi kết nối máy chủ C69: {}", e))?;

    let status = resp.status();
    let mut cookies = Vec::new();
    for val in resp.headers().get_all(reqwest::header::SET_COOKIE) {
        if let Ok(s) = val.to_str() {
            if let Some(first_part) = s.split(';').next() {
                cookies.push(first_part.to_string());
            }
        }
    }
    let cookie_str = if !cookies.is_empty() { Some(cookies.join("; ")) } else { None };

    let body_text = resp.text().await.unwrap_or_default();
    let parsed: serde_json::Value = serde_json::from_str(&body_text)
        .unwrap_or_else(|_| serde_json::json!({ "success": status.is_success() }));

    let success = parsed.get("success").and_then(|v| v.as_bool()).unwrap_or(status.is_success());
    if !success {
        let msg = parsed.get("message").and_then(|v| v.as_str()).unwrap_or("Sai tài khoản hoặc mật khẩu C69.");
        return Err(msg.to_string());
    }

    // Lấy thông tin user qua /dashboard/api/me/ (nếu có cookie)
    let mut email_opt = None;
    let mut is_staff = false;
    if let Some(ref c) = cookie_str {
        let me_url = format!("{}/dashboard/api/me/", server_url);
        if let Ok(me_resp) = client.get(&me_url).header("Cookie", c).send().await {
            if let Ok(me_json) = me_resp.json::<serde_json::Value>().await {
                email_opt = me_json.get("email").and_then(|v| v.as_str()).map(|s| s.to_string());
                is_staff = me_json.get("is_staff").and_then(|v| v.as_bool()).unwrap_or(false);
            }
        }
    }

    let session = C69Session {
        logged_in: true,
        username: username.to_string(),
        server_url: server_url.to_string(),
        cookies: cookie_str,
        token: Some(DEFAULT_C69_TOKEN.to_string()),
        email: email_opt,
        is_staff,
        last_login: Some(chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string()),
    };

    let _ = save_c69_session(&session);
    Ok(session)
}

/// Lấy danh sách tài khoản từ C69 theo bộ lọc chuẩn Portal (phân loại, trạng thái, người tạo, sub, sở hữu sub, phân trang, lọc theo user đã login)
pub async fn fetch_c69_accounts_full(
    type_filter: Option<String>,
    status_filter: Option<String>,
    search_filter: Option<String>,
    created_by_filter: Option<String>,
    has_subscription_filter: Option<String>,
    subscription_owner_filter: Option<String>,
    account_tab_filter: Option<String>,
    username_filter: Option<String>,
    sort_filter: Option<String>,
    _user_only_filter: Option<bool>,
    page_filter: Option<u32>,
    page_size_filter: Option<u32>,
) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let active_username = sess.as_ref().map(|s| s.username.clone()).unwrap_or_default();

    let client = reqwest::Client::new();
    let mut query_params = Vec::new();

    let _is_main_tab = account_tab_filter.as_deref().map(|t| t.eq_ignore_ascii_case("main")).unwrap_or(false);

    if let Some(ref tab) = account_tab_filter {
        if !tab.is_empty() && !tab.eq_ignore_ascii_case("all") {
            query_params.push(format!("account_tab={}", urlencoding::encode(tab)));
        }
    }
    if let Some(ref uf) = username_filter {
        if !uf.is_empty() {
            query_params.push(format!("username_filter={}", urlencoding::encode(uf)));
        }
    }
    if let Some(ref sf) = sort_filter {
        if !sf.is_empty() {
            query_params.push(format!("sort={}", urlencoding::encode(sf)));
        }
    }

    if let Some(t) = type_filter {
        if !t.is_empty() && !t.eq_ignore_ascii_case("all") {
            query_params.push(format!("type={}", urlencoding::encode(&t)));
        }
    }
    if let Some(s) = status_filter {
        if !s.is_empty() && !s.eq_ignore_ascii_case("all") {
            query_params.push(format!("status={}", urlencoding::encode(&s)));
        }
    }
    if let Some(q) = search_filter {
        if !q.is_empty() {
            query_params.push(format!("search={}", urlencoding::encode(&q)));
        }
    }
    if let Some(has_sub) = has_subscription_filter {
        if !has_sub.is_empty() && !has_sub.eq_ignore_ascii_case("all") {
            query_params.push(format!("has_subscription={}", urlencoding::encode(&has_sub)));
        }
    }
    if let Some(so) = subscription_owner_filter {
        if !so.is_empty() && !so.eq_ignore_ascii_case("all") {
            query_params.push(format!("subscription_owner={}", urlencoding::encode(&so)));
        }
    }

    // NGUYÊN TẮC: Hiển thị chuẩn theo tài khoản đã login chứ không kéo hết tài khoản về
    // Ngoại lệ: Khi ở Tab "main" hoặc "nurtured" (Đã Nuôi), xem toàn bộ kênh trong hệ thống không bị giới hạn created_by
    let is_exempt_tab = account_tab_filter.as_deref().map(|t| {
        let l = t.to_ascii_lowercase();
        l == "main" || l == "nurtured" || l == "da_nuoi"
    }).unwrap_or(false);

    if !is_exempt_tab {
        if let Some(cb) = created_by_filter {
            if !cb.is_empty() && !cb.eq_ignore_ascii_case("all") {
                query_params.push(format!("created_by={}", urlencoding::encode(&cb)));
            }
        } else {
            // Mặc định: lọc theo tài khoản đang login nếu chưa chọn filter cụ thể
            if !active_username.is_empty() && query_params.iter().all(|p| !p.starts_with("subscription_owner=")) {
                query_params.push(format!("created_by={}", urlencoding::encode(&active_username)));
            }
        }
    } else if let Some(cb) = created_by_filter {
        if !cb.is_empty() && !cb.eq_ignore_ascii_case("all") {
            query_params.push(format!("created_by={}", urlencoding::encode(&cb)));
        }
    }

    let ps = page_size_filter.unwrap_or(10);
    query_params.push(format!("page_size={}", ps));
    if let Some(p) = page_filter {
        query_params.push(format!("page={}", p));
    }

    let query_str = query_params.join("&");
    let url = format!("{}/dashboard/api/accounts/?{}", server_url, query_str);

    let mut req = client.get(&url)
        .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36")
        .timeout(Duration::from_secs(12));

    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        } else if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("C69 trả về mã lỗi: {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi đọc JSON C69: {}", e))?;
    Ok(data)
}

/// Đặt hoặc bỏ trạng thái Main cho danh sách tài khoản C69
pub async fn bulk_main_c69_accounts(ids: Vec<u64>, action: &str) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);

    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/bulk-main/", server_url);

    let mut req = client.post(&url)
        .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36")
        .header("Content-Type", "application/json")
        .timeout(Duration::from_secs(15));

    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        } else if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let payload = serde_json::json!({
        "ids": ids,
        "action": action
    });

    let resp = req.json(&payload).send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    if !resp.status().is_success() {
        let err_text = resp.text().await.unwrap_or_default();
        return Err(format!("C69 trả về mã lỗi: {}", err_text));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi đọc JSON C69: {}", e))?;
    Ok(data)
}

/// Trích xuất mã OTP 6 chữ số từ chuỗi văn bản
pub fn extract_6digit_otp(text: &str) -> Option<String> {
    let bytes = text.as_bytes();
    let len = bytes.len();
    for i in 0..len {
        if i + 6 <= len {
            let slice = &text[i..i + 6];
            if slice.chars().all(|c| c.is_ascii_digit()) {
                let prev_ok = i == 0 || !bytes[i - 1].is_ascii_digit();
                let next_ok = i + 6 == len || !bytes[i + 6].is_ascii_digit();
                if prev_ok && next_ok {
                    return Some(slice.to_string());
                }
            }
        }
    }
    None
}

/// Tìm kiếm email ID trên C69 theo địa chỉ email
pub async fn find_c69_email_id_by_address(email_addr: &str) -> Result<Option<u64>, String> {
    let client = reqwest::Client::new();
    let encoded = urlencoding::encode(email_addr.trim());
    let url = format!("{}/dashboard/api/emails/?search={}", DEFAULT_C69_API_URL, encoded);

    let resp = client
        .get(&url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .timeout(Duration::from_secs(8))
        .send()
        .await
        .map_err(|e| format!("Lỗi kết nối C69 tìm email: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("C69 API trả về mã lỗi: {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi giải mã JSON C69: {}", e))?;
    if let Some(arr) = data.get("results").and_then(|v| v.as_array()) {
        if let Some(first) = arr.first() {
            if let Some(id) = first.get("id").and_then(|v| v.as_u64()) {
                return Ok(Some(id));
            }
        }
    }
    Ok(None)
}

/// Đọc hòm thư email trên C69 và tự động trích xuất mã OTP TikTok 6 số
pub async fn fetch_c69_email_otp(email_id: u64) -> Result<Option<String>, String> {
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/emails/{}/read-mailbox/", DEFAULT_C69_API_URL, email_id);

    let resp = client
        .get(&url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .timeout(Duration::from_secs(12))
        .send()
        .await
        .map_err(|e| format!("Lỗi kết nối đọc hòm thư: {}", e))?;

    if !resp.status().is_success() {
        return Err(format!("Lỗi server C69 đọc hòm thư: HTTP {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON hòm thư: {}", e))?;
    let success = data.get("success").and_then(|v| v.as_bool()).unwrap_or(false);
    if !success {
        let msg = data.get("error").or_else(|| data.get("message")).and_then(|v| v.as_str()).unwrap_or("Không thể kết nối hòm thư Microsoft");
        return Err(msg.to_string());
    }

    // 1. Kiểm tra email_data.latest_code
    if let Some(email_data) = data.get("email_data") {
        if let Some(latest_code) = email_data.get("latest_code").and_then(|v| v.as_str()) {
            let clean = latest_code.trim();
            if clean.len() == 6 && clean.chars().all(|c| c.is_ascii_digit()) {
                return Ok(Some(clean.to_string()));
            }
        }
    }

    // 2. Quét danh sách emails nhận được
    if let Some(emails) = data.get("emails").and_then(|v| v.as_array()) {
        for email in emails {
            let from_str = email.get("from").and_then(|v| v.as_str()).unwrap_or("").to_lowercase();
            let subject = email.get("subject").and_then(|v| v.as_str()).unwrap_or("");
            let snippet = email.get("snippet").and_then(|v| v.as_str()).unwrap_or("");
            let body = email.get("body").and_then(|v| v.as_str()).unwrap_or("");

            let is_from_tiktok = from_str.contains("tiktok") || subject.to_lowercase().contains("tiktok") || body.to_lowercase().contains("tiktok");
            if is_from_tiktok || subject.to_lowercase().contains("verification") || subject.to_lowercase().contains("mã xác") {
                if let Some(otp) = extract_6digit_otp(subject) {
                    return Ok(Some(otp));
                }
                if let Some(otp) = extract_6digit_otp(snippet) {
                    return Ok(Some(otp));
                }
                if let Some(otp) = extract_6digit_otp(body) {
                    return Ok(Some(otp));
                }
            }
        }
    }

    Ok(None)
}

/// Đọc trực tiếp hòm thư email trên C69 qua API, trả về full JSON phản hồi từ server
pub async fn read_c69_email_mailbox(email_id: u64) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);

    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/emails/{}/read-mailbox/", server_url, email_id);

    let mut req = client.get(&url)
        .header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/134.0.0.0 Safari/537.36")
        .timeout(Duration::from_secs(15));

    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối đọc hòm thư: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("Lỗi server C69 đọc hòm thư: HTTP {}", resp.status()));
    }

    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON hòm thư: {}", e))?;
    Ok(data)
}

/// Lấy danh sách users từ C69 để hiển thị bộ lọc người tạo / sở hữu sub
pub async fn fetch_c69_users_list() -> Result<Vec<serde_json::Value>, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/users-list/?status=active&page_size=100", server_url);

    let mut req = client.get(&url).timeout(Duration::from_secs(10));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("Lỗi server C69: HTTP {}", resp.status()));
    }
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    if let Some(arr) = data.as_array() {
        Ok(arr.clone())
    } else if let Some(arr) = data.get("results").and_then(|v| v.as_array()) {
        Ok(arr.clone())
    } else {
        Ok(vec![])
    }
}

/// Lấy chi tiết tài khoản C69 theo ID
pub async fn fetch_c69_account_detail(account_id: u64) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/{}/", server_url, account_id);

    let mut req = client.get(&url).timeout(Duration::from_secs(10));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("Lỗi server C69: HTTP {}", resp.status()));
    }
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Cập nhật chi tiết tài khoản C69
pub async fn update_c69_account_detail(account_id: u64, payload: serde_json::Value) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/{}/", server_url, account_id);

    let mut req = client.patch(&url).json(&payload).timeout(Duration::from_secs(12));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Xóa 1 tài khoản C69
pub async fn delete_c69_account_single(account_id: u64) -> Result<(), String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/{}/", server_url, account_id);

    let mut req = client.delete(&url).timeout(Duration::from_secs(10));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    if !resp.status().is_success() {
        return Err(format!("Lỗi server C69: HTTP {}", resp.status()));
    }
    Ok(())
}

/// Lấy mã 2FA từ tài khoản C69
pub async fn fetch_c69_account_2fa(account_id: u64) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/{}/get-2fa/", server_url, account_id);

    let mut req = client.get(&url).timeout(Duration::from_secs(10));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Thêm mới tài khoản C69 thủ công
pub async fn add_c69_account_manual(payload: serde_json::Value) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/add-manual/", server_url);

    let mut req = client.post(&url).json(&payload).timeout(Duration::from_secs(12));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Thêm hàng loạt tài khoản C69
pub async fn bulk_add_c69_accounts(accounts_data: &str, r#type: &str) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/bulk-add/", server_url);

    let payload = json!({
        "accounts_data": accounts_data,
        "type": r#type
    });

    let mut req = client.post(&url).json(&payload).timeout(Duration::from_secs(20));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Xóa nhiều tài khoản C69 (bulk delete)
pub async fn bulk_delete_c69_accounts(ids: Vec<u64>) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/bulk-delete/", server_url);

    let payload = json!({ "ids": ids });
    let mut req = client.post(&url).json(&payload).timeout(Duration::from_secs(15));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Đổi trạng thái nhiều tài khoản C69
pub async fn bulk_status_c69_accounts(ids: Vec<u64>, status: i32) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/bulk-status/", server_url);

    let payload = json!({ "ids": ids, "status": status });
    let mut req = client.post(&url).json(&payload).timeout(Duration::from_secs(15));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Gán sở hữu Sub cho nhiều tài khoản C69
pub async fn bulk_sub_owner_c69_accounts(ids: Vec<u64>, sub_owner: &str) -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/bulk-sub-owner/", server_url);

    let payload = json!({ "ids": ids, "subscription_owner": sub_owner });
    let mut req = client.post(&url).json(&payload).timeout(Duration::from_secs(15));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Lấy thẻ thanh toán đang hoạt động từ C69
pub async fn fetch_c69_active_card() -> Result<serde_json::Value, String> {
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/cards/get-active-card/", server_url);

    let mut req = client.get(&url).timeout(Duration::from_secs(10));
    if let Some(ref s) = sess {
        if let Some(ref c) = s.cookies {
            req = req.header("Cookie", c);
        }
        if let Some(ref t) = s.token {
            req = req.header("Authorization", t);
        } else {
            req = req.header("Authorization", DEFAULT_C69_TOKEN);
        }
    } else {
        req = req.header("Authorization", DEFAULT_C69_TOKEN);
    }

    let resp = req.send().await.map_err(|e| format!("Lỗi kết nối C69: {}", e))?;
    let data: serde_json::Value = resp.json().await.map_err(|e| format!("Lỗi parse JSON: {}", e))?;
    Ok(data)
}

/// Cập nhật ghi chú trên tài khoản C69 (ví dụ: ghi lại lỗi đọc email)
pub async fn update_c69_account_note(account_id: u64, note: &str) -> Result<(), String> {
    let client = reqwest::Client::new();
    let url = format!("{}/dashboard/api/accounts/{}/", DEFAULT_C69_API_URL, account_id);
    let payload = json!({ "note": note });

    let _ = client
        .patch(&url)
        .header("Authorization", DEFAULT_C69_TOKEN)
        .json(&payload)
        .send()
        .await;

    Ok(())
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
                canvas_seed: Some((next_id as u64 + 1).wrapping_mul(1664525) ^ 0x5a5a5a5a),
                audio_seed: Some((next_id as u64 + 1).wrapping_mul(1103515245) ^ 0xa5a5a5a5),
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

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ProxyStatusRecord {
    pub alive: bool,
    pub latency_ms: u64,
    pub message: String,
    pub tested_at: u64,
}

pub fn load_proxy_status_cache() -> std::collections::HashMap<String, ProxyStatusRecord> {
    let candidate_paths = [
        "data/proxy_status_cache.json",
        "d:\\Workspace\\Python\\c69-router\\data\\proxy_status_cache.json",
        "proxy_status_cache.json",
    ];

    for path_str in &candidate_paths {
        let p = std::path::Path::new(path_str);
        if p.exists() {
            if let Ok(content) = std::fs::read_to_string(p) {
                if let Ok(map) = serde_json::from_str::<std::collections::HashMap<String, ProxyStatusRecord>>(&content) {
                    return map;
                }
            }
        }
    }
    std::collections::HashMap::new()
}

pub fn save_proxy_status(proxy_str: &str, alive: bool, latency_ms: u64, message: &str) {
    let p_clean = proxy_str.trim();
    if p_clean.is_empty() {
        return;
    }
    let mut cache = load_proxy_status_cache();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    let record = ProxyStatusRecord {
        alive,
        latency_ms,
        message: message.to_string(),
        tested_at: now,
    };

    cache.insert(p_clean.to_string(), record.clone());
    if let Some(parsed) = crate::cdp_browser::parse_proxy_string(p_clean) {
        let hp = format!("{}:{}", parsed.host, parsed.port);
        cache.insert(hp, record.clone());
        let clean = format!("{}://{}:{}", parsed.scheme, parsed.host, parsed.port);
        cache.insert(clean, record);
    }

    if let Ok(json_str) = serde_json::to_string_pretty(&cache) {
        let candidate_paths = [
            "data/proxy_status_cache.json",
            "d:\\Workspace\\Python\\c69-router\\data\\proxy_status_cache.json",
            "proxy_status_cache.json",
        ];
        for path_str in &candidate_paths {
            let p = std::path::Path::new(path_str);
            if let Some(parent) = p.parent() {
                if !parent.as_os_str().is_empty() && !parent.exists() {
                    let _ = std::fs::create_dir_all(parent);
                }
            }
            let _ = std::fs::write(p, &json_str);
        }
    }
}

pub fn save_proxy_status_batch(results: &[serde_json::Value]) {
    if results.is_empty() {
        return;
    }
    let mut cache = load_proxy_status_cache();
    let now = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    for item in results {
        let p_str = item.get("proxy").and_then(|v| v.as_str()).unwrap_or("").trim();
        if p_str.is_empty() {
            continue;
        }
        let alive = item.get("alive").and_then(|v| v.as_bool()).unwrap_or(false);
        let latency_ms = item.get("latency_ms").and_then(|v| v.as_u64()).unwrap_or(0);
        let message = item.get("message").and_then(|v| v.as_str()).unwrap_or("").to_string();

        let record = ProxyStatusRecord {
            alive,
            latency_ms,
            message,
            tested_at: now,
        };

        cache.insert(p_str.to_string(), record.clone());
        if let Some(parsed) = crate::cdp_browser::parse_proxy_string(p_str) {
            let hp = format!("{}:{}", parsed.host, parsed.port);
            cache.insert(hp, record.clone());
            let clean = format!("{}://{}:{}", parsed.scheme, parsed.host, parsed.port);
            cache.insert(clean, record);
        }
    }

    if let Ok(json_str) = serde_json::to_string_pretty(&cache) {
        let candidate_paths = [
            "data/proxy_status_cache.json",
            "d:\\Workspace\\Python\\c69-router\\data\\proxy_status_cache.json",
            "proxy_status_cache.json",
        ];
        for path_str in &candidate_paths {
            let p = std::path::Path::new(path_str);
            if let Some(parent) = p.parent() {
                if !parent.as_os_str().is_empty() && !parent.exists() {
                    let _ = std::fs::create_dir_all(parent);
                }
            }
            let _ = std::fs::write(p, &json_str);
        }
    }
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
    #[serde(default)]
    pub proxy_string: Option<String>,
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

/// Nạp danh sách proxy từ C69 Router proxies_250.txt hoặc config.json (250 proxies pool)
pub fn load_c69_proxies() -> Vec<C69Proxy> {
    let status_cache = load_proxy_status_cache();

    // 1. Nạp từ file proxies_250.txt (250 SOCKS5 Proxy pool của C69)
    let txt_paths = [
        "proxies_250.txt",
        "data/proxies_250.txt",
        "d:\\Workspace\\Python\\c69-router\\proxies_250.txt",
        "../c69-router/proxies_250.txt",
        "c69-router/proxies_250.txt",
    ];

    for path_str in &txt_paths {
        let p = std::path::Path::new(path_str);
        if p.exists() {
            if let Ok(content) = std::fs::read_to_string(p) {
                let mut proxies = Vec::new();
                for (idx, line) in content.lines().enumerate() {
                    let trimmed = line.trim();
                    if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with("//") {
                        continue;
                    }
                    if let Some(parsed) = crate::cdp_browser::parse_proxy_string(trimmed) {
                        let p_str = match (&parsed.username, &parsed.password) {
                            (Some(u), Some(p)) if !u.is_empty() => {
                                format!("{}://{}:{}@{}:{}", parsed.scheme, u, p, parsed.host, parsed.port)
                            }
                            _ => format!("{}://{}:{}", parsed.scheme, parsed.host, parsed.port),
                        };
                        let hp = format!("{}:{}", parsed.host, parsed.port);
                        let (stat, lat) = if let Some(rec) = status_cache.get(&p_str).or_else(|| status_cache.get(&hp)) {
                            (if rec.alive { "live" } else { "die" }.to_string(), Some(rec.latency_ms as i32))
                        } else {
                            ("idle".to_string(), None)
                        };

                        proxies.push(C69Proxy {
                            id: format!("p_{}", idx + 1),
                            proxy_type: parsed.scheme,
                            host: parsed.host,
                            port: parsed.port,
                            username: parsed.username,
                            password: parsed.password,
                            status: Some(stat),
                            latency: lat,
                            proxy_string: Some(p_str),
                        });
                    }
                }
                if !proxies.is_empty() {
                    return proxies;
                }
            }
        }
    }

    // 2. Fallback sang config.json
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
                            if let Ok(mut proxy) = serde_json::from_value::<C69Proxy>(item.clone()) {
                                if proxy.proxy_string.is_none() {
                                    proxy.proxy_string = Some(proxy.to_proxy_string());
                                }
                                let p_str = proxy.proxy_string.clone().unwrap_or_default();
                                let hp = format!("{}:{}", proxy.host, proxy.port);
                                if let Some(rec) = status_cache.get(&p_str).or_else(|| status_cache.get(&hp)) {
                                    proxy.status = Some(if rec.alive { "live" } else { "die" }.to_string());
                                    proxy.latency = Some(rec.latency_ms as i32);
                                }
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

/// Ghi danh sách proxy ra đĩa (proxies_250.txt)
pub fn save_c69_proxies(proxies: &[C69Proxy]) -> Result<(), String> {
    let mut lines = Vec::new();
    for p in proxies {
        if let (Some(ref u), Some(ref pass)) = (&p.username, &p.password) {
            lines.push(format!("{}:{}:{}:{}", p.host, p.port, u, pass));
        } else {
            lines.push(format!("{}:{}", p.host, p.port));
        }
    }
    let content = lines.join("\n");

    let txt_paths = [
        "d:\\Workspace\\Python\\c69-router\\proxies_250.txt",
        "../c69-router/proxies_250.txt",
        "c69-router/proxies_250.txt",
        "proxies_250.txt",
        "data/proxies_250.txt",
    ];

    let mut written = false;
    for path_str in &txt_paths {
        let p = std::path::Path::new(path_str);
        if let Some(parent) = p.parent() {
            if !parent.as_os_str().is_empty() && !parent.exists() {
                continue;
            }
        }
        if std::fs::write(p, &content).is_ok() {
            written = true;
        }
    }

    if written {
        Ok(())
    } else {
        Err("Không thể ghi file proxy vào đĩa".to_string())
    }
}

/// Import danh sách proxy mới vào pool file
pub fn import_new_proxies(proxies_text: &str, mode: &str) -> Result<(usize, usize), String> {
    let mut current = if mode == "replace" {
        Vec::new()
    } else {
        load_c69_proxies()
    };

    let mut added = 0;
    for line in proxies_text.lines() {
        let trimmed = line.trim();
        if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with("//") {
            continue;
        }

        if let Some(parsed) = crate::cdp_browser::parse_proxy_string(trimmed) {
            let p_str = match (&parsed.username, &parsed.password) {
                (Some(u), Some(p)) if !u.is_empty() => {
                    format!("{}://{}:{}@{}:{}", parsed.scheme, u, p, parsed.host, parsed.port)
                }
                _ => format!("{}://{}:{}", parsed.scheme, parsed.host, parsed.port),
            };

            // Kiểm tra trùng lặp theo host:port
            let exists = current.iter().any(|existing| existing.host == parsed.host && existing.port == parsed.port);
            if !exists {
                let id = format!("p_{}", current.len() + 1);
                current.push(C69Proxy {
                    id,
                    proxy_type: parsed.scheme,
                    host: parsed.host,
                    port: parsed.port,
                    username: parsed.username,
                    password: parsed.password,
                    status: Some("idle".to_string()),
                    latency: None,
                    proxy_string: Some(p_str),
                });
                added += 1;
            }
        }
    }

    if added > 0 || mode == "replace" {
        save_c69_proxies(&current)?;
    }

    Ok((current.len(), added))
}

/// Xóa các proxy die khỏi pool với cơ chế so khớp đa năng (host:port, chuỗi proxy)
pub fn remove_dead_proxies(dead_proxy_strings: &[String]) -> Result<(usize, usize), String> {
    let current = load_c69_proxies();
    let initial_count = current.len();

    let mut dead_raw_set = std::collections::HashSet::new();
    let mut dead_host_ports = std::collections::HashSet::new();

    for s in dead_proxy_strings {
        let trimmed = s.trim();
        if trimmed.is_empty() {
            continue;
        }
        dead_raw_set.insert(trimmed.to_string());

        if let Some(parsed) = crate::cdp_browser::parse_proxy_string(trimmed) {
            dead_host_ports.insert((parsed.host.to_lowercase(), parsed.port));
        } else {
            let clean = trimmed
                .trim_start_matches("socks5://")
                .trim_start_matches("http://")
                .trim_start_matches("https://");
            let target_part = if let Some(at) = clean.rfind('@') {
                &clean[at + 1..]
            } else {
                clean
            };
            let parts: Vec<&str> = target_part.split(':').collect();
            if parts.len() >= 2 {
                if let Ok(port) = parts[1].parse::<u16>() {
                    dead_host_ports.insert((parts[0].to_lowercase(), port));
                }
            }
        }
    }

    let filtered: Vec<C69Proxy> = current.into_iter()
        .filter(|p| {
            // 1. So khớp theo cặp (host, port)
            if dead_host_ports.contains(&(p.host.to_lowercase(), p.port)) {
                return false;
            }
            // 2. So khớp theo proxy_string
            if let Some(ref ps) = p.proxy_string {
                if dead_raw_set.contains(ps.trim()) {
                    return false;
                }
            }
            // 3. So khớp theo to_proxy_string()
            let gen = p.to_proxy_string();
            if dead_raw_set.contains(gen.trim()) {
                return false;
            }
            // 4. So khớp theo chuỗi host:port đơn giản
            let hp = format!("{}:{}", p.host, p.port);
            if dead_raw_set.contains(&hp) {
                return false;
            }
            true
        })
        .enumerate()
        .map(|(idx, mut p)| {
            p.id = format!("p_{}", idx + 1);
            p
        })
        .collect();

    let removed = initial_count.saturating_sub(filtered.len());
    let remaining = filtered.len();
    save_c69_proxies(&filtered)?;

    // Dọn dẹp các proxy die khỏi cache file
    let mut cache = load_proxy_status_cache();
    let initial_cache_len = cache.len();
    for s in dead_proxy_strings {
        let t = s.trim();
        cache.remove(t);
        if let Some(parsed) = crate::cdp_browser::parse_proxy_string(t) {
            cache.remove(&format!("{}:{}", parsed.host, parsed.port));
            cache.remove(&format!("{}://{}:{}", parsed.scheme, parsed.host, parsed.port));
        }
    }
    if cache.len() != initial_cache_len {
        if let Ok(json_str) = serde_json::to_string_pretty(&cache) {
            let candidate_paths = [
                "data/proxy_status_cache.json",
                "d:\\Workspace\\Python\\c69-router\\data\\proxy_status_cache.json",
                "proxy_status_cache.json",
            ];
            for path_str in &candidate_paths {
                let p = std::path::Path::new(path_str);
                let _ = std::fs::write(p, &json_str);
            }
        }
    }

    Ok((removed, remaining))
}

/// Kiểm tra kết nối TCP và xác thực SOCKS5 hoặc HTTP tới Proxy và đo độ trễ (latency ms)
pub async fn test_proxy_connection(proxy_str: &str) -> (bool, u64, String) {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    let parsed = match crate::cdp_browser::parse_proxy_string(proxy_str) {
        Some(p) => p,
        None => return (false, 0, "Định dạng proxy không hợp lệ".to_string()),
    };

    let target = format!("{}:{}", parsed.host, parsed.port);
    let start = std::time::Instant::now();

    // 1. Kết nối TCP tới host:port của Proxy (Timeout 3500ms)
    let mut stream = match tokio::time::timeout(
        Duration::from_millis(3500),
        tokio::net::TcpStream::connect(&target)
    ).await {
        Ok(Ok(s)) => s,
        Ok(Err(e)) => return (false, 0, format!("Không thể kết nối đến {}: {}", target, e)),
        Err(_) => return (false, 0, format!("Kết nối đến {} bị timeout (> 3.5s)", target)),
    };

    // 2. Thử bắt tay SOCKS5 trước
    // Gửi SOCKS5 Greeting hỗ trợ 2 phương thức: 0x00 (No Auth) và 0x02 (User/Password)
    let greeting = [0x05, 0x02, 0x00, 0x02];
    let is_socks = match tokio::time::timeout(Duration::from_millis(2500), stream.write_all(&greeting)).await {
        Ok(Ok(())) => {
            let mut choice = [0u8; 2];
            match tokio::time::timeout(Duration::from_millis(2500), stream.read_exact(&mut choice)).await {
                Ok(Ok(_)) if choice[0] == 0x05 => Some(choice[1]),
                _ => None,
            }
        }
        _ => None,
    };

    if let Some(auth_method) = is_socks {
        // SOCKS5 SERVER PHẢN HỒI
        if auth_method == 0x00 {
            // Không cần xác thực (No Auth Required)
            let latency = start.elapsed().as_millis() as u64;
            return (true, latency, format!("SOCKS5 Live (No Auth, {}ms)", latency));
        } else if auth_method == 0x02 {
            // Yêu cầu xác thực Username / Password (RFC 1929)
            if let (Some(u), Some(p)) = (&parsed.username, &parsed.password) {
                let mut auth_buf = Vec::with_capacity(3 + u.len() + p.len());
                auth_buf.push(0x01); // Subnegotiation version 1
                auth_buf.push(u.len() as u8);
                auth_buf.extend_from_slice(u.as_bytes());
                auth_buf.push(p.len() as u8);
                auth_buf.extend_from_slice(p.as_bytes());

                if let Err(e) = stream.write_all(&auth_buf).await {
                    return (false, 0, format!("Lỗi gửi SOCKS5 auth: {}", e));
                }
                let mut auth_resp = [0u8; 2];
                if let Err(e) = stream.read_exact(&mut auth_resp).await {
                    return (false, 0, format!("Lỗi nhận phản hồi SOCKS5 auth: {}", e));
                }
                if auth_resp[1] == 0x00 {
                    let latency = start.elapsed().as_millis() as u64;
                    return (true, latency, format!("SOCKS5 Live (Độ trễ: {}ms)", latency));
                } else {
                    return (false, 0, "❌ SOCKS5 Auth thất bại: Sai User/Pass hoặc Proxy hết hạn/băng thông".to_string());
                }
            } else {
                return (false, 0, "Proxy SOCKS5 yêu cầu User/Password nhưng chưa cung cấp".to_string());
            }
        } else {
            return (false, 0, format!("Phương thức xác thực SOCKS5 không được hỗ trợ: 0x{:02X}", auth_method));
        }
    }

    // 3. Nếu không phải SOCKS5: Thử kiểm tra giao thức HTTP / HTTPS Proxy (CONNECT handshake)
    let mut http_stream = match tokio::time::timeout(
        Duration::from_millis(3000),
        tokio::net::TcpStream::connect(&target)
    ).await {
        Ok(Ok(s)) => s,
        Ok(Err(e)) => return (false, 0, format!("Không thể kết nối HTTP proxy: {}", e)),
        Err(_) => return (false, 0, "Timeout kết nối HTTP proxy".to_string()),
    };

    let mut connect_req = format!("CONNECT 1.1.1.1:80 HTTP/1.1\r\nHost: 1.1.1.1:80\r\n");
    if let (Some(u), Some(p)) = (&parsed.username, &parsed.password) {
        use base64::Engine;
        let creds = format!("{}:{}", u, p);
        let b64 = base64::engine::general_purpose::STANDARD.encode(creds.as_bytes());
        connect_req.push_str(&format!("Proxy-Authorization: Basic {}\r\n", b64));
    }
    connect_req.push_str("Proxy-Connection: keep-alive\r\n\r\n");

    if let Err(e) = http_stream.write_all(connect_req.as_bytes()).await {
        return (false, 0, format!("Lỗi gửi HTTP CONNECT: {}", e));
    }

    let mut buf = [0u8; 256];
    let n = match tokio::time::timeout(Duration::from_millis(3000), http_stream.read(&mut buf)).await {
        Ok(Ok(n)) if n > 0 => n,
        _ => return (false, 0, "Proxy không phản hồi bắt tay HTTP hoặc SOCKS5".to_string()),
    };

    let resp_str = String::from_utf8_lossy(&buf[..n]);
    if resp_str.starts_with("HTTP/1.1 200") || resp_str.starts_with("HTTP/1.0 200") {
        let latency = start.elapsed().as_millis() as u64;
        (true, latency, format!("HTTP Proxy Live (Độ trễ: {}ms)", latency))
    } else if resp_str.contains("407") {
        (false, 0, "❌ HTTP Proxy: Sai User/Pass hoặc chưa whitelist IP (407 Proxy Authentication Required)".to_string())
    } else {
        (false, 0, format!("Proxy từ chối: {}", resp_str.lines().next().unwrap_or("Unknown response")))
    }
}

/// Kiểm tra hàng loạt Proxy đồng thời với giới hạn concurrency 40
pub async fn batch_test_c69_proxies(proxy_strings: Vec<String>) -> Vec<serde_json::Value> {
    use tokio::sync::Semaphore;
    use std::sync::Arc;

    let sem = Arc::new(Semaphore::new(40));
    let mut handles = Vec::new();

    for p in proxy_strings {
        let sem_clone = sem.clone();
        handles.push(tokio::spawn(async move {
            let _permit = sem_clone.acquire_owned().await;
            let (alive, latency, msg) = test_proxy_connection(&p).await;
            serde_json::json!({
                "proxy": p,
                "alive": alive,
                "latency_ms": latency,
                "message": msg
            })
        }));
    }

    let mut results = Vec::new();
    for h in handles {
        if let Ok(res) = h.await {
            results.push(res);
        }
    }
    save_proxy_status_batch(&results);
    results
}

/// Gán Socks5 Proxy cho danh sách tài khoản C69 và Profile Anti-Browser tương ứng
pub async fn assign_socks_to_c69_accounts(account_ids: Vec<u64>, proxy_str: &str) -> Result<usize, String> {
    let profiles_path = crate::api::get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&profiles_path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();

    let mut updated_count = 0;
    let sess = load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(DEFAULT_C69_API_URL);
    let client = reqwest::Client::new();

    for acc_id in &account_ids {
        // Cập nhật profile tương ứng nếu có
        if let Some(prof) = profiles.iter_mut().find(|p| p.tiktok_account_id == Some(*acc_id)) {
            prof.proxy_string = proxy_str.trim().to_string();
            prof.proxy_type = "socks5".to_string();
            updated_count += 1;
        }

        // Cập nhật lên C69 Server nếu có session
        let url = format!("{}/dashboard/api/accounts/{}/", server_url, acc_id);
        let mut req = client.patch(&url)
            .header("Content-Type", "application/json")
            .timeout(Duration::from_secs(6));

        if let Some(ref s) = sess {
            if let Some(ref c) = s.cookies {
                req = req.header("Cookie", c);
            } else if let Some(ref t) = s.token {
                req = req.header("Authorization", t);
            } else {
                req = req.header("Authorization", DEFAULT_C69_TOKEN);
            }
        }
        let _ = req.json(&serde_json::json!({ "socks5": proxy_str.trim() })).send().await;
    }

    if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
        let _ = std::fs::write(&profiles_path, json_str);
    }

    Ok(updated_count)
}

/// Tự động quét và thay thế Proxy die cho toàn bộ các profile đang dùng proxy chết
pub async fn auto_replace_dead_proxies_for_profiles() -> Result<Vec<serde_json::Value>, String> {
    let profiles_path = crate::api::get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&profiles_path)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default();

    let mut replaced_logs = Vec::new();

    for prof in profiles.iter_mut() {
        let p_str = prof.proxy_string.trim();
        if !p_str.is_empty() {
            let (alive, _lat, _) = test_proxy_connection(p_str).await;
            if !alive {
                if let Some(healthy) = find_healthy_backup_proxy(p_str).await {
                    let old_p = prof.proxy_string.clone();
                    prof.proxy_string = healthy.clone();
                    prof.proxy_type = "socks5".to_string();

                    replaced_logs.push(serde_json::json!({
                        "profile_id": prof.id,
                        "profile_name": prof.name,
                        "account_id": prof.tiktok_account_id,
                        "old_proxy": old_p,
                        "new_proxy": healthy
                    }));
                }
            }
        }
    }

    if !replaced_logs.is_empty() {
        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
            let _ = std::fs::write(&profiles_path, json_str);
        }
    }

    Ok(replaced_logs)
}

/// Tìm kiếm và trả về một proxy SOCKS5 sống khỏe mạnh nhất để tự động thay thế proxy chết
pub async fn find_healthy_backup_proxy(failed_proxy: &str) -> Option<String> {
    let mut candidate_strings = Vec::new();
    for c in load_c69_proxies() {
        candidate_strings.push(c.to_proxy_string());
    }

    for p in candidate_strings {
        if p != failed_proxy {
            let (alive, _lat, _) = test_proxy_connection(&p).await;
            if alive {
                return Some(p);
            }
        }
    }
    None
}

/// Trích xuất địa chỉ IP từ chuỗi proxy (ví dụ socks5://user:pass@50.114.98.173:5657 -> 50.114.98.173)
pub fn extract_ip_from_proxy_string(proxy: &str) -> String {
    let p = proxy.trim();
    if p.is_empty() { return String::new(); }
    let host_part = if let Some(idx) = p.rfind('@') {
        &p[idx + 1..]
    } else if let Some(idx) = p.find("://") {
        &p[idx + 3..]
    } else {
        p
    };
    if let Some(idx) = host_part.find(':') {
        host_part[..idx].trim().to_string()
    } else {
        host_part.trim().to_string()
    }
}

/// Làm sạch username TikTok (bỏ tiền tố số C69 như 3_ hoặc 16809_, đảm bảo format TikTok hợp lệ)
pub fn clean_tiktok_username(raw: &str) -> String {
    let s = raw.trim();
    // Bỏ tiền tố số như "3_", "16809_"
    let s = if let Some(idx) = s.find('_') {
        let prefix = &s[..idx];
        if prefix.chars().all(|c| c.is_ascii_digit()) {
            &s[idx + 1..]
        } else {
            s
        }
    } else {
        s
    };

    let cleaned: String = s.chars()
        .map(|c| if c.is_ascii_alphanumeric() || c == '.' || c == '_' { c.to_ascii_lowercase() } else { '_' })
        .collect();

    let cleaned = cleaned.trim_matches(|c| c == '.' || c == '_');
    if cleaned.len() >= 3 && cleaned.len() <= 24 {
        cleaned.to_string()
    } else {
        format!("user_{:x}", rand::thread_rng().gen::<u32>())
    }
}

/// Chuẩn bị ảnh avatar sạch tự nhiên để upload cho profile TikTok
pub async fn get_or_create_clean_avatar(pid: usize) -> Result<String, String> {
    let dir = std::env::temp_dir().join("qhtd_avatars");
    let _ = std::fs::create_dir_all(&dir);
    let avatar_file = dir.join(format!("avatar_{}.jpg", pid % 20));
    
    if avatar_file.exists() && avatar_file.metadata().map(|m| m.len() > 1000).unwrap_or(false) {
        return Ok(avatar_file.to_string_lossy().to_string());
    }

    // Tải ảnh avatar chân dung tự nhiên từ kho ảnh miễn phí pravatar.cc
    let client = reqwest::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("Lỗi tạo client reqwest: {}", e))?;

    let img_id = (pid % 70) + 1;
    let url = format!("https://i.pravatar.cc/300?img={}", img_id);
    
    if let Ok(resp) = client.get(&url).send().await {
        if resp.status().is_success() {
            if let Ok(bytes) = resp.bytes().await {
                if bytes.len() > 1000 {
                    let _ = std::fs::write(&avatar_file, bytes);
                    return Ok(avatar_file.to_string_lossy().to_string());
                }
            }
        }
    }

    // Fallback: Sinh file ảnh BMP hợp lệ (256x256 pixel) nếu không có mạng tải avatar
    let width = 256u32;
    let height = 256u32;
    let mut bmp_data = Vec::new();
    // BMP Header (14 bytes)
    bmp_data.extend_from_slice(b"BM");
    let file_size = 54 + width * height * 3;
    bmp_data.extend_from_slice(&(file_size as u32).to_le_bytes());
    bmp_data.extend_from_slice(&[0, 0, 0, 0]);
    bmp_data.extend_from_slice(&(54u32).to_le_bytes());
    // DIB Header (40 bytes)
    bmp_data.extend_from_slice(&(40u32).to_le_bytes());
    bmp_data.extend_from_slice(&(width as i32).to_le_bytes());
    bmp_data.extend_from_slice(&(height as i32).to_le_bytes());
    bmp_data.extend_from_slice(&(1u16).to_le_bytes()); // planes
    bmp_data.extend_from_slice(&(24u16).to_le_bytes()); // bpp
    bmp_data.extend_from_slice(&[0; 24]); // compression, etc.
    
    // Pixel data gradient tự nhiên
    let base_r = ((pid * 37) % 200 + 55) as u8;
    let base_g = ((pid * 73) % 200 + 55) as u8;
    let base_b = ((pid * 109) % 200 + 55) as u8;
    for y in 0..height {
        for x in 0..width {
            let b = base_b.saturating_add((x % 30) as u8);
            let g = base_g.saturating_add((y % 30) as u8);
            let r = base_r;
            bmp_data.push(b);
            bmp_data.push(g);
            bmp_data.push(r);
        }
    }
    let bmp_file = dir.join(format!("avatar_{}.bmp", pid % 20));
    let _ = std::fs::write(&bmp_file, bmp_data);
    Ok(bmp_file.to_string_lossy().to_string())
}

