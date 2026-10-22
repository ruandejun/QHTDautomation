//! Phone-Farm GUI thuần Rust (egui/eframe).
//!
//! Nguyên tắc UX:
//! * Mỗi máy = 1 SLOT cố định (lưu `farm_slots.json`), không bao giờ nhảy vị trí khi cắm/rút cáp.
//! * Lưới tự co giãn để toàn bộ giàn máy nằm gọn trong 1 màn hình (hoặc chỉnh tay).
//! * Click đầu thẻ = chọn máy; thao tác (nuôi / login / mở TikTok...) áp dụng cho máy đã chọn,
//!   nếu không chọn máy nào thì áp dụng cho TẤT CẢ máy online.
//! * Màn hình máy tương tác trực tiếp: click = tap, kéo = vuốt, giữ = long-press, lăn chuột = cuộn.

use crate::adb_manager::AdbManager;
use crate::fast_touch::{Cmd, FastTouch};
use eframe::egui::{self, pos2, vec2, Align2, Color32, FontId, Rect, RichText, Rounding, Sense, Stroke, Vec2};
use serde_json::{json, Value};
use std::collections::{HashMap, HashSet, VecDeque};
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, Mutex, MutexGuard, OnceLock};
use std::time::{Duration, Instant};

// ── Palette ─────────────────────────────────────────────────────────────────
const BG: Color32 = Color32::from_rgb(8, 11, 20);
const PANEL: Color32 = Color32::from_rgb(14, 19, 32);
const CARD_BG: Color32 = Color32::from_rgb(12, 17, 28);
const HDR_BG: Color32 = Color32::from_rgb(20, 28, 46);
const BORDER: Color32 = Color32::from_rgb(34, 46, 68);
const TEXT: Color32 = Color32::from_rgb(226, 232, 240);
const MUTED: Color32 = Color32::from_rgb(120, 134, 158);
const CYAN: Color32 = Color32::from_rgb(56, 189, 248);
const GREEN: Color32 = Color32::from_rgb(34, 197, 94);
const YELLOW: Color32 = Color32::from_rgb(250, 204, 21);
const ORANGE: Color32 = Color32::from_rgb(251, 146, 60);
const RED: Color32 = Color32::from_rgb(239, 68, 68);
const SLATE: Color32 = Color32::from_rgb(51, 65, 85);

// ── Kích thước thẻ máy ──────────────────────────────────────────────────────
const HDR_H: f32 = 20.0;
const FOOT_H: f32 = 42.0;
const PAD: f32 = 3.0;
const ASPECT: f32 = 1480.0 / 720.0;
const MIN_CARD_W: f32 = 96.0;
const SLOTS_FILE: &str = "farm_slots.json";
const TIKTOK_PKG: &str = "com.zhiliaoapp.musically";

fn lock<T>(m: &Mutex<T>) -> MutexGuard<'_, T> {
    m.lock().unwrap_or_else(|e| e.into_inner())
}

fn card_height(w: f32) -> f32 {
    HDR_H + (w - 2.0 * PAD) * ASPECT + FOOT_H + PAD
}

// ── Log toàn cục (thread nào cũng ghi được) ─────────────────────────────────
static LOGS: OnceLock<Mutex<VecDeque<String>>> = OnceLock::new();

fn logs() -> &'static Mutex<VecDeque<String>> {
    LOGS.get_or_init(|| Mutex::new(VecDeque::new()))
}

pub fn gui_log(msg: impl Into<String>) {
    let line = format!("[{}] {}", chrono::Local::now().format("%H:%M:%S"), msg.into());
    let mut l = lock(logs());
    if l.len() >= 600 {
        l.pop_front();
    }
    l.push_back(line);
}

// ── Dữ liệu dùng chung giữa poller và UI ────────────────────────────────────
#[derive(Clone, Default)]
struct DevLive {
    state: String, // "device" | "offline" | "unauthorized" | "" (mất kết nối)
    model: String,
    battery: i32,
    w: u32,
    h: u32,
    android: String,
    ip: String,
}

#[derive(Clone, Default)]
struct NurtureRow {
    status: String,
    last_action: String,
    videos: u64,
    likes: u64,
    comments: u64,
    follows: u64,
    user: String,
}

#[derive(Clone, Default)]
struct LoginRow {
    state: String,
    step: String,
    message: String,
    current_user: String,
    username: String,
}

#[derive(Clone, Default)]
struct BrowserRow {
    id: u64,
    name: String,
    user: String,
    status: String,
    videos: u64,
    likes: u64,
    comments: u64,
    running: bool,
    last_log: String,
    waiting_otp: bool,
}

#[derive(Clone, Default)]
struct Shared {
    live: HashMap<String, DevLive>,
    nurture: HashMap<String, NurtureRow>,
    login: HashMap<String, LoginRow>,
    login_running: bool,
    /// (total, success, failed, skipped, remaining)
    login_queue: (usize, usize, usize, usize, usize),
    browser: Vec<BrowserRow>,
    profile_count: usize,
    c69_user: Option<String>,
    api_ok: bool,
    profiles: Vec<ProfRow>,
    active_profiles: HashSet<u64>,
    core: String,
    proxies: Vec<ProxyRow>,
    router: String,
}

#[derive(Clone, Default)]
struct ProfRow {
    id: u64,
    name: String,
    os: String,
    mode: String,
    res: String,
    proxy: String,
    user: String,
    status: String,
}

#[derive(Clone, Default)]
struct ProxyRow {
    proxy: String,
    status: String,
    latency: String,
}

impl Shared {
    fn is_online(&self, serial: &str) -> bool {
        self.live.get(serial).map_or(false, |d| d.state == "device")
    }
}

// ── Điều khiển stream ───────────────────────────────────────────────────────
struct StreamCtl {
    enabled: AtomicBool,
    focused: AtomicBool,
    zoom: Mutex<Option<String>>,
    boost: Mutex<HashMap<String, Instant>>,
    inflight: Mutex<HashSet<String>>,
    last: Mutex<HashMap<String, Instant>>,
    rr: AtomicUsize,
    frames: Mutex<HashMap<String, egui::ColorImage>>,
    touch: FastTouch,
}

impl StreamCtl {
    fn new(adb_path: std::path::PathBuf) -> Self {
        Self {
            enabled: AtomicBool::new(true),
            focused: AtomicBool::new(true),
            zoom: Mutex::new(None),
            boost: Mutex::new(HashMap::new()),
            inflight: Mutex::new(HashSet::new()),
            last: Mutex::new(HashMap::new()),
            rr: AtomicUsize::new(0),
            frames: Mutex::new(HashMap::new()),
            touch: FastTouch::new(adb_path),
        }
    }

    /// Sau khi thao tác, ưu tiên chụp lại máy đó ngay để thấy phản hồi.
    fn boost(&self, serial: &str) {
        lock(&self.boost).insert(serial.to_string(), Instant::now());
    }
}

fn decode_frame(png: &[u8], width: u32) -> Option<egui::ColorImage> {
    let img = image::load_from_memory(png).ok()?;
    let height = (width as f32 * ASPECT).round() as u32;
    let rgba = img.resize_exact(width, height, image::imageops::FilterType::Triangle).to_rgba8();
    Some(egui::ColorImage::from_rgba_unmultiplied(
        [rgba.width() as usize, rgba.height() as usize],
        &rgba.into_raw(),
    ))
}

fn stream_worker(adb: Arc<AdbManager>, ctl: Arc<StreamCtl>, shared: Arc<Mutex<Shared>>, ctx: egui::Context) {
    loop {
        if !ctl.enabled.load(Ordering::Relaxed) {
            std::thread::sleep(Duration::from_millis(400));
            continue;
        }
        let mut online: Vec<String> = lock(&shared)
            .live
            .iter()
            .filter(|(_, d)| d.state == "device")
            .map(|(s, _)| s.clone())
            .collect();
        online.sort();
        if online.is_empty() {
            std::thread::sleep(Duration::from_millis(500));
            continue;
        }
        // Cửa sổ ẩn/mất focus -> giảm tải CPU & USB.
        let base_ms: u64 = if ctl.focused.load(Ordering::Relaxed) { 650 } else { 4000 };
        let zoom = lock(&ctl.zoom).clone();

        let pick: Option<String> = {
            let now = Instant::now();
            let mut inflight = lock(&ctl.inflight);
            let last = lock(&ctl.last);
            let boost = lock(&ctl.boost);
            let due = |s: &str, min_ms: u64| {
                last.get(s).map_or(true, |l| now.duration_since(*l) >= Duration::from_millis(min_ms))
            };
            let mut choice: Option<String> = None;
            for s in &online {
                if inflight.contains(s) {
                    continue;
                }
                if let Some(t) = boost.get(s) {
                    if now.duration_since(*t) < Duration::from_millis(2500) && due(s, 180) {
                        choice = Some(s.clone());
                        break;
                    }
                }
            }
            if choice.is_none() {
                if let Some(z) = &zoom {
                    if online.contains(z) && !inflight.contains(z) && due(z, 200) {
                        choice = Some(z.clone());
                    }
                }
            }
            if choice.is_none() {
                let start = ctl.rr.fetch_add(1, Ordering::Relaxed);
                for k in 0..online.len() {
                    let s = &online[(start + k) % online.len()];
                    if !inflight.contains(s) && due(s, base_ms) {
                        choice = Some(s.clone());
                        break;
                    }
                }
            }
            if let Some(s) = &choice {
                inflight.insert(s.clone());
            }
            choice
        };

        match pick {
            None => std::thread::sleep(Duration::from_millis(30)),
            Some(serial) => {
                let width = if zoom.as_deref() == Some(serial.as_str()) { 480 } else { 260 };
                let frame = adb.capture_screen_raw(&serial).ok().and_then(|png| decode_frame(&png, width));
                if let Some(img) = frame {
                    lock(&ctl.frames).insert(serial.clone(), img);
                    ctx.request_repaint();
                }
                lock(&ctl.last).insert(serial.clone(), Instant::now());
                lock(&ctl.inflight).remove(&serial);
            }
        }
    }
}

// ── Slot cố định ────────────────────────────────────────────────────────────
const DEFAULT_SLOTS: [&str; 19] = [
    "ce0117112dccec3404", "ce03171371483c3c05", "ce031713edfb4f3702", "ce031713f138907a0c",
    "ce04171409d8062401", "ce0417140c8138370c", "ce0417145ce4a0e80c", "ce041714a2d2211102",
    "ce051715c86d871f03", "ce0918298272403101", "ce011711c21da00403", "ce02182260b5580f04",
    "ce0317131000e70803", "ce0317139c3058f60d", "ce031713a40b80030c", "ce04171428e364860d",
    "ce0517153333513202", "ce081718a56b1e2802", "ce091719b40aa53b05",
];

fn load_slots() -> Vec<String> {
    let mut slots: Vec<String> = std::fs::read_to_string(SLOTS_FILE)
        .ok()
        .and_then(|d| serde_json::from_str::<Vec<String>>(&d).ok())
        .unwrap_or_else(|| DEFAULT_SLOTS.iter().map(|s| s.to_string()).collect());
    while slots.len() < 20 {
        slots.push(String::new());
    }
    slots
}

fn save_slots(slots: &[String]) {
    if let Ok(s) = serde_json::to_string_pretty(slots) {
        let _ = std::fs::write(SLOTS_FILE, s);
    }
}

// ── Pollers ─────────────────────────────────────────────────────────────────
fn jstr(v: &Value, k: &str) -> String {
    v.get(k).and_then(|x| x.as_str()).unwrap_or("").to_string()
}
fn ju64(v: &Value, k: &str) -> u64 {
    v.get(k).and_then(|x| x.as_u64()).unwrap_or(0)
}
fn jbool(v: &Value, k: &str) -> bool {
    v.get(k).and_then(|x| x.as_bool()).unwrap_or(false)
}

/// `adb devices` có kiểm tra lỗi: trả None nếu adb lỗi/đang khởi động lại (khác với "không có máy").
fn list_adb(adb_path: &std::path::Path) -> Option<Vec<(String, String)>> {
    let mut c = std::process::Command::new(adb_path);
    c.arg("devices");
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x08000000);
    }
    let out = c.output().ok()?;
    let text = String::from_utf8_lossy(&out.stdout).to_string();
    if !out.status.success() || !text.contains("List of devices") {
        return None;
    }
    Some(
        text.lines()
            .skip(1)
            .filter_map(|l| {
                let mut it = l.split_whitespace();
                let s = it.next()?;
                let st = it.next()?;
                Some((s.to_string(), st.to_string()))
            })
            .collect(),
    )
}

/// Poller nhanh: trạng thái ADB, login (đọc trực tiếp trong tiến trình), nuôi, profiles PC.
fn fast_poller(
    api: String,
    adb: Arc<AdbManager>,
    shared: Arc<Mutex<Shared>>,
    slots: Arc<Mutex<Vec<String>>>,
    refresh: Arc<AtomicBool>,
    ctx: egui::Context,
) {
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(4))
        .build()
        .unwrap_or_default();
    let mut tick: u64 = 0;
    let mut misses: HashMap<String, u32> = HashMap::new();
    loop {
        // Lấy danh sách ADB có kiểm tra lỗi + hysteresis để không nhấp nháy "mất kết nối".
        let prev: HashMap<String, String> = lock(&shared)
            .live
            .iter()
            .map(|(s, d)| (s.clone(), d.state.clone()))
            .collect();
        let mut list: Vec<(String, String)> = match list_adb(adb.get_adb_path()) {
            Some(l) => l,
            None => prev.iter().filter(|(_, st)| !st.is_empty()).map(|(s, st)| (s.clone(), st.clone())).collect(),
        };
        let present: HashSet<String> = list.iter().map(|(s, _)| s.clone()).collect();
        for s in &present {
            misses.remove(s);
        }
        for (s, st) in &prev {
            if st.is_empty() {
                continue;
            }
            if present.contains(s) {
                misses.remove(s);
            } else {
                let m = misses.entry(s.clone()).or_insert(0);
                *m += 1;
                if *m < 3 {
                    list.push((s.clone(), st.clone()));
                }
            }
        }

        // Gán máy mới cắm vào slot trống đầu tiên (máy cũ giữ nguyên vị trí).
        {
            let mut sl = lock(&slots);
            let mut changed = false;
            for (s, _) in &list {
                if !sl.contains(s) {
                    if let Some(p) = sl.iter().position(|x| x.is_empty()) {
                        sl[p] = s.clone();
                    } else {
                        sl.push(s.clone());
                    }
                    gui_log(format!("📱 Máy mới ...{} được xếp vào slot #{}", short_serial(s), sl.iter().position(|x| x == s).unwrap_or(0) + 1));
                    changed = true;
                }
            }
            if changed {
                save_slots(&sl);
            }
        }

        // Login XML: đọc trực tiếp từ engine (cùng tiến trình, không qua HTTP).
        let login_rows: HashMap<String, LoginRow> = crate::xml_login::snapshot()
            .into_iter()
            .map(|s| {
                (
                    s.serial.clone(),
                    LoginRow {
                        state: s.state,
                        step: s.step,
                        message: s.message,
                        current_user: s.current_user,
                        username: s.username,
                    },
                )
            })
            .collect();
        let login_running = crate::xml_login::is_running();
        let login_queue = crate::xml_login::queue_stats();

        {
            let mut sh = lock(&shared);
            for d in sh.live.values_mut() {
                d.state.clear();
            }
            for (s, st) in &list {
                sh.live.entry(s.clone()).or_default().state = st.clone();
            }
            sh.login = login_rows;
            sh.login_running = login_running;
            sh.login_queue = login_queue;
        }

        // Nuôi phone
        match client.get(format!("{}/api/nurture/status", api)).send().and_then(|r| r.json::<Value>()) {
            Ok(v) => {
                let mut map = HashMap::new();
                if let Some(arr) = v.get("devices").and_then(|d| d.as_array()) {
                    for d in arr {
                        map.insert(
                            jstr(d, "device_serial"),
                            NurtureRow {
                                status: jstr(d, "status"),
                                last_action: jstr(d, "last_action"),
                                videos: ju64(d, "videos_watched"),
                                likes: ju64(d, "likes_given"),
                                comments: ju64(d, "comments_posted"),
                                follows: ju64(d, "follows_given"),
                                user: jstr(d, "account_user"),
                            },
                        );
                    }
                }
                let mut sh = lock(&shared);
                sh.nurture = map;
                sh.api_ok = true;
            }
            Err(_) => lock(&shared).api_ok = false,
        }

        if tick % 2 == 0 {
            if let Ok(v) = client.get(format!("{}/api/browser/nurture/status", api)).send().and_then(|r| r.json::<Value>()) {
                let rows: Vec<BrowserRow> = v
                    .as_array()
                    .map(|a| {
                        a.iter()
                            .map(|b| BrowserRow {
                                id: ju64(b, "profile_id"),
                                name: jstr(b, "profile_name"),
                                user: jstr(b, "c69_username"),
                                status: jstr(b, "status"),
                                videos: ju64(b, "videos_watched"),
                                likes: ju64(b, "likes_given"),
                                comments: ju64(b, "comments_posted"),
                                running: jbool(b, "is_running"),
                                last_log: jstr(b, "last_log"),
                                waiting_otp: jbool(b, "waiting_otp"),
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                lock(&shared).browser = rows;
            }
        }
        if tick % 2 == 0 {
            let g = |p: &str| client.get(format!("{}{}", api, p)).send().and_then(|r| r.json::<Value>());
            if let Ok(v) = g("/api/browser/profiles") {
                let rows: Vec<ProfRow> = v
                    .as_array()
                    .map(|a| {
                        a.iter()
                            .map(|p| ProfRow {
                                id: ju64(p, "id"),
                                name: jstr(p, "name"),
                                os: jstr(p, "profile_os"),
                                mode: jstr(p, "engine_mode"),
                                res: jstr(p, "profile_resolution"),
                                proxy: jstr(p, "proxy_string"),
                                user: jstr(p, "tiktok_username"),
                                status: jstr(p, "last_nurture_status"),
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                lock(&shared).profiles = rows;
            }
            if let Ok(v) = g("/api/browser/active") {
                let set: HashSet<u64> = v.as_array().map(|a| a.iter().filter_map(|x| x.as_u64()).collect()).unwrap_or_default();
                lock(&shared).active_profiles = set;
            }
            if let Ok(v) = g("/api/browser/core-status") {
                let c = if jbool(&v, "has_custom_core") {
                    format!("Mun Core: {}", jstr(&v, "custom_path"))
                } else if jbool(&v, "has_system_chrome") {
                    format!("Chrome hệ thống: {}", jstr(&v, "system_path"))
                } else {
                    "Chưa có Chrome/Mun Core".to_string()
                };
                lock(&shared).core = c;
            }
        }
        if tick % 3 == 0 {
            let g = |p: &str| client.get(format!("{}{}", api, p)).send().and_then(|r| r.json::<Value>());
            if let Ok(v) = g("/api/browser/c69/proxies") {
                let rows: Vec<ProxyRow> = v
                    .get("proxies")
                    .and_then(|a| a.as_array())
                    .map(|a| {
                        a.iter()
                            .map(|p| ProxyRow {
                                proxy: jstr(p, "proxy_string"),
                                status: jstr(p, "status"),
                                latency: p.get("latency").map(|l| l.to_string().trim_matches('"').to_string()).unwrap_or_default(),
                            })
                            .collect()
                    })
                    .unwrap_or_default();
                lock(&shared).proxies = rows;
            }
            if let Ok(v) = g("/api/router/status") {
                lock(&shared).router = truncate(&v.to_string(), 140);
            }
        }
        if tick % 2 == 0 {
            if let Ok(v) = client.get(format!("{}/api/c69/auth/status", api)).send().and_then(|r| r.json::<Value>()) {
                lock(&shared).c69_user = if jbool(&v, "logged_in") { Some(jstr(&v, "username")) } else { None };
            }
            if let Ok(v) = client.get(format!("{}/api/farm/container/list", api)).send().and_then(|r| r.json::<Value>()) {
                if let Some(n) = v.get("profiles").and_then(|p| p.as_array()).map(|a| a.len()) {
                    lock(&shared).profile_count = n;
                }
            }
        }

        ctx.request_repaint();
        tick += 1;
        for _ in 0..25 {
            if refresh.swap(false, Ordering::Relaxed) {
                break;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
    }
}

/// Poller chậm: model / pin / độ phân giải / IP (getprop nhiều lệnh nên tách riêng).
fn detail_poller(adb: Arc<AdbManager>, shared: Arc<Mutex<Shared>>, refresh: Arc<AtomicBool>) {
    let mut tick: u64 = 0;
    loop {
        let need: Vec<String> = {
            let sh = lock(&shared);
            sh.live
                .iter()
                .filter(|(_, d)| d.state == "device" && (d.model.is_empty() || tick % 8 == 0))
                .map(|(s, _)| s.clone())
                .collect()
        };
        if !need.is_empty() {
            let results: Vec<(String, crate::adb_manager::DeviceInfo)> = std::thread::scope(|scope| {
                let handles: Vec<_> = need
                    .iter()
                    .map(|s| {
                        let adb = adb.clone();
                        let s = s.clone();
                        scope.spawn(move || {
                            let info = adb.get_device_detail(&s, "device");
                            (s, info)
                        })
                    })
                    .collect();
                handles.into_iter().filter_map(|h| h.join().ok()).collect()
            });
            let mut sh = lock(&shared);
            for (s, info) in results {
                let d = sh.live.entry(s).or_default();
                d.model = info.model;
                d.battery = info.battery;
                d.w = info.width;
                d.h = info.height;
                d.android = info.android_version;
                d.ip = info.ip_address;
            }
        }
        tick += 1;
        for _ in 0..30 {
            if refresh.load(Ordering::Relaxed) {
                break;
            }
            std::thread::sleep(Duration::from_millis(100));
        }
    }
}

// ── HTTP helper ─────────────────────────────────────────────────────────────
fn http_post(api: &str, path: &str, body: Value, label: &str) {
    http_call("POST", api, path, body, label);
}

fn http_call(method: &'static str, api: &str, path: &str, body: Value, label: &str) {
    let url = format!("{}{}", api, path);
    let label = label.to_string();
    std::thread::spawn(move || {
        let client = reqwest::blocking::Client::builder()
            .timeout(Duration::from_secs(300))
            .build()
            .unwrap_or_default();
        let req = match method {
            "DELETE" => client.delete(&url),
            "PUT" => client.put(&url).json(&body),
            _ => client.post(&url).json(&body),
        };
        match req.send() {
            Ok(r) => {
                let v: Value = r.json().unwrap_or(Value::Null);
                let ok = v.get("success").and_then(|x| x.as_bool()).unwrap_or(true);
                let msg = v
                    .get("message")
                    .or_else(|| v.get("error"))
                    .and_then(|x| x.as_str())
                    .unwrap_or("");
                gui_log(format!("{} {} — {}", if ok { "✔" } else { "✖" }, label, msg));
            }
            Err(e) => gui_log(format!("✖ {} — lỗi kết nối: {}", label, e)),
        }
    });
}

fn short_serial(s: &str) -> String {
    let n = s.chars().count();
    s.chars().skip(n.saturating_sub(6)).collect()
}

fn truncate(s: &str, max: usize) -> String {
    if s.chars().count() <= max {
        s.to_string()
    } else {
        let mut t: String = s.chars().take(max.saturating_sub(1)).collect();
        t.push('…');
        t
    }
}

fn find_payload_file() -> Option<String> {
    for p in ["payload_clean_run.json", "../payload_clean_run.json"] {
        if let Ok(d) = std::fs::read_to_string(p) {
            return Some(d);
        }
    }
    None
}

// ── Thẻ máy ─────────────────────────────────────────────────────────────────
enum CardEvent {
    Select,
    Zoom,
    MoveUp,
    MoveDown,
    Clear,
}

struct CardInfo<'a> {
    salt: &'static str,
    idx: usize,
    serial: &'a str,
    live: Option<&'a DevLive>,
    label: String,
    label_color: Color32,
    accent: Color32,
    selected: bool,
    wheel_ok: bool,
    tex: Option<&'a egui::TextureHandle>,
}

#[derive(Clone, Copy)]
enum NavKind {
    Back,
    Home,
    Recents,
    Power,
    App,
}

fn nav_button(ui: &mut egui::Ui, rect: Rect, id: egui::Id, kind: NavKind, accent: Color32, tip: &str) -> bool {
    let resp = ui.interact(rect, id, Sense::click()).on_hover_text(tip);
    let bg = if resp.is_pointer_button_down_on() {
        Color32::from_rgb(40, 56, 88)
    } else if resp.hovered() {
        Color32::from_rgb(30, 42, 68)
    } else {
        Color32::from_rgb(18, 25, 42)
    };
    let p = ui.painter();
    p.rect_filled(rect, Rounding::same(5.0), bg);
    p.rect_stroke(rect, Rounding::same(5.0), Stroke::new(1.0_f32, BORDER));
    let c = rect.center();
    let col = if resp.hovered() { Color32::WHITE } else { Color32::from_rgb(190, 200, 216) };
    match kind {
        NavKind::Back => {
            p.add(egui::Shape::convex_polygon(
                vec![pos2(c.x + 3.5, c.y - 5.0), pos2(c.x + 3.5, c.y + 5.0), pos2(c.x - 4.0, c.y)],
                col,
                Stroke::NONE,
            ));
        }
        NavKind::Home => {
            p.circle_stroke(c, 5.0, Stroke::new(1.6_f32, col));
        }
        NavKind::Recents => {
            p.rect_stroke(Rect::from_center_size(c, vec2(10.0, 10.0)), Rounding::same(2.0), Stroke::new(1.6_f32, col));
        }
        NavKind::Power => {
            p.circle_stroke(c + vec2(0.0, 1.0), 4.8, Stroke::new(1.5_f32, col));
            p.line_segment([pos2(c.x, c.y - 6.0), pos2(c.x, c.y)], Stroke::new(1.8_f32, col));
        }
        NavKind::App => {
            p.text(c, Align2::CENTER_CENTER, "TT", FontId::proportional(10.5), accent);
        }
    }
    resp.clicked()
}

fn draw_empty_slot(ui: &mut egui::Ui, w: f32, idx: usize) {
    let (rect, _) = ui.allocate_exact_size(vec2(w, card_height(w)), Sense::hover());
    let p = ui.painter_at(rect);
    p.rect_filled(rect, Rounding::same(8.0), Color32::from_rgba_unmultiplied(20, 28, 46, 90));
    p.rect_stroke(rect, Rounding::same(8.0), Stroke::new(1.0_f32, Color32::from_rgb(30, 41, 59)));
    p.text(
        rect.center() - vec2(0.0, 8.0),
        Align2::CENTER_CENTER,
        format!("SLOT {:02}", idx + 1),
        FontId::proportional(13.0),
        Color32::from_rgb(71, 85, 105),
    );
    p.text(
        rect.center() + vec2(0.0, 10.0),
        Align2::CENTER_CENTER,
        "trống",
        FontId::proportional(11.0),
        Color32::from_rgb(71, 85, 105),
    );
}

fn draw_card(ui: &mut egui::Ui, w: f32, info: &CardInfo, adb: &Arc<AdbManager>, ctl: &Arc<StreamCtl>) -> Vec<CardEvent> {
    let mut events = Vec::new();
    let (rect, _) = ui.allocate_exact_size(vec2(w, card_height(w)), Sense::hover());
    let painter = ui.painter_at(rect);
    let online = info.live.map_or(false, |l| l.state == "device");

    painter.rect_filled(rect, Rounding::same(8.0), CARD_BG);
    let (bc, bw) = if info.selected { (ORANGE, 2.2_f32) } else { (info.accent, 1.2_f32) };
    painter.rect_stroke(rect, Rounding::same(8.0), Stroke::new(bw, bc));

    // ── Header ──
    let hdr = Rect::from_min_size(rect.min, vec2(w, HDR_H));
    painter.rect_filled(hdr, Rounding { nw: 8.0, ne: 8.0, sw: 0.0, se: 0.0 }, HDR_BG);
    let cb = Rect::from_center_size(pos2(hdr.min.x + 12.0, hdr.center().y), vec2(11.0, 11.0));
    painter.rect_stroke(cb, Rounding::same(2.0), Stroke::new(1.2_f32, if info.selected { ORANGE } else { MUTED }));
    if info.selected {
        painter.rect_filled(cb.shrink(2.5), Rounding::same(1.0), ORANGE);
    }
    painter.text(
        pos2(hdr.min.x + 23.0, hdr.center().y),
        Align2::LEFT_CENTER,
        format!("#{:02}", info.idx + 1),
        FontId::proportional(12.0),
        Color32::WHITE,
    );
    if w >= 150.0 {
        painter.text(
            pos2(hdr.min.x + 52.0, hdr.center().y),
            Align2::LEFT_CENTER,
            short_serial(info.serial),
            FontId::proportional(9.5),
            MUTED,
        );
    }
    let zoom_rect = Rect::from_center_size(pos2(hdr.max.x - 12.0, hdr.center().y), vec2(18.0, HDR_H));
    if let Some(l) = info.live {
        if online && l.battery >= 0 {
            let col = if l.battery > 20 { GREEN } else { RED };
            painter.text(
                pos2(hdr.max.x - 24.0, hdr.center().y),
                Align2::RIGHT_CENTER,
                format!("{}%", l.battery),
                FontId::proportional(10.0),
                col,
            );
        }
    }
    let zc = zoom_rect.center();
    painter.circle_stroke(zc - vec2(1.0, 1.0), 3.8, Stroke::new(1.4_f32, MUTED));
    painter.line_segment([zc + vec2(1.8, 1.8), zc + vec2(5.0, 5.0)], Stroke::new(1.6_f32, MUTED));

    let hdr_click = Rect::from_min_max(hdr.min, pos2(zoom_rect.min.x, hdr.max.y));
    let hdr_resp = ui.interact(hdr_click, egui::Id::new(("hdr", info.salt, info.serial)), Sense::click());
    if hdr_resp.clicked() {
        events.push(CardEvent::Select);
    }
    hdr_resp.context_menu(|ui| {
        ui.label(RichText::new(format!("Slot #{:02} — {}", info.idx + 1, info.serial)).color(MUTED).size(11.0));
        if let Some(l) = info.live {
            if !l.model.is_empty() {
                ui.label(RichText::new(format!("{} • Android {} • {}", l.model, l.android, l.ip)).size(11.0));
            }
        }
        ui.separator();
        if ui.button("⬆ Đổi chỗ với slot trước").clicked() {
            events.push(CardEvent::MoveUp);
            ui.close_menu();
        }
        if ui.button("⬇ Đổi chỗ với slot sau").clicked() {
            events.push(CardEvent::MoveDown);
            ui.close_menu();
        }
        if ui.button("🗑 Bỏ máy khỏi slot này").clicked() {
            events.push(CardEvent::Clear);
            ui.close_menu();
        }
    });
    let zoom_resp = ui.interact(zoom_rect, egui::Id::new(("zoom", info.salt, info.serial)), Sense::click());
    if zoom_resp.on_hover_text("Phóng to").clicked() {
        events.push(CardEvent::Zoom);
    }

    // ── Màn hình ──
    let scr = Rect::from_min_size(
        pos2(rect.min.x + PAD, rect.min.y + HDR_H),
        vec2(w - 2.0 * PAD, (w - 2.0 * PAD) * ASPECT),
    );
    painter.rect_filled(scr, Rounding::same(3.0), Color32::BLACK);
    if let Some(tex) = info.tex {
        painter.image(tex.id(), scr, Rect::from_min_max(pos2(0.0, 0.0), pos2(1.0, 1.0)), Color32::WHITE);
    }
    if !online {
        painter.rect_filled(scr, Rounding::same(3.0), Color32::from_rgba_unmultiplied(6, 9, 16, if info.tex.is_some() { 200 } else { 255 }));
        let msg = match info.live.map(|l| l.state.as_str()) {
            Some("unauthorized") => "CHƯA CẤP QUYỀN\nUSB DEBUG",
            Some("offline") => "ADB OFFLINE",
            _ => "MẤT KẾT NỐI",
        };
        painter.text(scr.center(), Align2::CENTER_CENTER, msg, FontId::proportional(12.0), Color32::from_rgb(100, 116, 139));
    } else if info.tex.is_none() {
        painter.text(scr.center(), Align2::CENTER_CENTER, "Đang tải màn hình…", FontId::proportional(11.0), MUTED);
    }
    if online {
        if let Some(l) = info.live {
            if !l.model.is_empty() && w >= 150.0 {
                painter.text(
                    pos2(scr.min.x + 4.0, scr.max.y - 3.0),
                    Align2::LEFT_BOTTOM,
                    &l.model,
                    FontId::proportional(9.0),
                    Color32::from_rgba_unmultiplied(255, 255, 255, 120),
                );
            }
        }
        handle_screen_input(ui, scr, info, adb, ctl);
    }

    // ── Footer: nút điều hướng + trạng thái ──
    let foot_top = scr.max.y + 3.0;
    let gap = 3.0;
    let bw = (w - 2.0 * PAD - 4.0 * gap) / 5.0;
    let kinds = [
        (NavKind::Back, "Back"),
        (NavKind::Home, "Home"),
        (NavKind::Recents, "Recents"),
        (NavKind::Power, "Nguồn / đánh thức"),
        (NavKind::App, "Mở TikTok"),
    ];
    for (i, (kind, tip)) in kinds.iter().enumerate() {
        let kind = *kind;
        let r = Rect::from_min_size(pos2(rect.min.x + PAD + i as f32 * (bw + gap), foot_top), vec2(bw, 19.0));
        let id = egui::Id::new(("nav", info.salt, info.serial, i));
        if nav_button(ui, r, id, kind, info.accent, tip) && online {
            match kind {
                NavKind::Back => ctl.touch.send(info.serial, Cmd::Key(4)),
                NavKind::Home => ctl.touch.send(info.serial, Cmd::Key(3)),
                NavKind::Recents => ctl.touch.send(info.serial, Cmd::Key(187)),
                NavKind::Power => ctl.touch.send(info.serial, Cmd::Key(26)),
                NavKind::App => {
                    let a = adb.clone();
                    let s = info.serial.to_string();
                    std::thread::spawn(move || {
                        let _ = a.launch_app(&s, TIKTOK_PKG);
                    });
                }
            }
            ctl.boost(info.serial);
        }
    }
    let max_chars = ((w - 8.0) / 5.4) as usize;
    painter.text(
        pos2(rect.min.x + PAD + 2.0, foot_top + 29.0),
        Align2::LEFT_CENTER,
        truncate(&info.label, max_chars.max(6)),
        FontId::proportional(10.5),
        info.label_color,
    );
    events
}

fn handle_screen_input(ui: &mut egui::Ui, scr: Rect, info: &CardInfo, _adb: &Arc<AdbManager>, ctl: &Arc<StreamCtl>) {
    let id = egui::Id::new(("scr", info.salt, info.serial));
    let resp = ui.interact(scr, id, Sense::click_and_drag());
    let serial = info.serial;
    // Toạ độ chuẩn hoá 0..1 (FastTouch tự đổi ra pixel theo độ phân giải thật của máy).
    let frac = |p: egui::Pos2| -> (f32, f32) {
        (
            ((p.x - scr.min.x) / scr.width()).clamp(0.0, 1.0),
            ((p.y - scr.min.y) / scr.height()).clamp(0.0, 1.0),
        )
    };
    let now = ui.input(|i| i.time);

    // Rê chuột vào màn hình: bật sẵn kết nối chạm để lần chạm đầu tiên không bị trễ.
    if resp.hovered() {
        let key = id.with("warm");
        let prev: f64 = ui.memory(|m| m.data.get_temp(key)).unwrap_or(-100.0);
        if now - prev > 8.0 {
            ctl.touch.send(serial, Cmd::Warm);
            ui.memory_mut(|m| m.data.insert_temp(key, now));
        }
    }

    // Vuốt thời gian thực: Down ngay khi bắt đầu kéo, Move theo chuột, Up khi nhả.
    if resp.drag_started() {
        if let Some(p) = ui.input(|i| i.pointer.press_origin()).or_else(|| resp.interact_pointer_pos()) {
            let (x, y) = frac(p);
            ctl.touch.send(serial, Cmd::Down(x, y));
            ctl.boost(serial);
        }
    } else if resp.dragged() {
        if let Some(p) = resp.interact_pointer_pos() {
            let (x, y) = frac(p);
            ctl.touch.send(serial, Cmd::Move(x, y));
            ctl.boost(serial);
        }
    }
    if resp.drag_stopped() {
        if let Some(p) = resp.interact_pointer_pos().or_else(|| ui.input(|i| i.pointer.latest_pos())) {
            let (x, y) = frac(p);
            ctl.touch.send(serial, Cmd::Up(x, y));
            ctl.boost(serial);
        }
    } else if resp.clicked() {
        if let Some(p) = resp.interact_pointer_pos() {
            let (x, y) = frac(p);
            ctl.touch.send(serial, Cmd::Tap(x, y));
            ctl.boost(serial);
        }
    }

    // Lăn chuột = cuộn feed của máy đó (chỉ khi không xung đột với cuộn lưới)
    if resp.hovered() && info.wheel_ok {
        let dy = ui.input(|i| i.raw_scroll_delta.y);
        if dy.abs() > 1.0 {
            let key = id.with("wheel");
            let prev: f64 = ui.memory(|m| m.data.get_temp(key)).unwrap_or(0.0);
            if now - prev > 0.35 {
                if let Some(p) = ui.input(|i| i.pointer.latest_pos()) {
                    let (x, y) = frac(p);
                    // Lăn xuống (dy<0) = kéo nội dung lên = vuốt từ dưới lên
                    let (y1, y2) = if dy < 0.0 { (y.max(0.55), (y.max(0.55) - 0.35).max(0.05)) } else { (y.min(0.45), (y.min(0.45) + 0.35).min(0.95)) };
                    ctl.touch.send(serial, Cmd::Swipe(x, y1, x, y2, 180));
                    ui.memory_mut(|m| m.data.insert_temp(key, now));
                    ctl.boost(serial);
                }
            }
        }
    }
}

fn fit_layout(avail: Vec2, n: usize, gap: f32) -> (f32, usize) {
    let b = HDR_H + FOOT_H + PAD - 2.0 * PAD * ASPECT;
    let mut best = (0.0_f32, 1_usize);
    for cols in 1..=n.max(1) {
        let rows = (n + cols - 1) / cols;
        let w1 = (avail.x - gap * (cols as f32 - 1.0)) / cols as f32;
        let row_h = (avail.y - gap * (rows as f32 - 1.0)) / rows as f32;
        let w2 = (row_h - b) / ASPECT;
        let w = w1.min(w2);
        if w > best.0 {
            best = (w, cols);
        }
    }
    (best.0.clamp(MIN_CARD_W, 520.0), best.1)
}

// ── App ─────────────────────────────────────────────────────────────────────
#[derive(Clone, Copy, PartialEq)]
enum Tab {
    Farm,
    Control,
    Mun,
    Proxy,
    Logs,
}

pub struct FarmGuiApp {
    api_base: String,
    adb: Arc<AdbManager>,
    shared: Arc<Mutex<Shared>>,
    slots: Arc<Mutex<Vec<String>>>,
    ctl: Arc<StreamCtl>,
    refresh: Arc<AtomicBool>,
    textures: HashMap<String, egui::TextureHandle>,
    selected: HashSet<String>,
    tab: Tab,
    fit: bool,
    scale: f32,
    zoom: Option<String>,
    // cấu hình nuôi
    videos: u32,
    like_pct: f32,
    comment_pct: f32,
    follow_pct: f32,
    min_watch: u32,
    max_watch: u32,
    gemini_key: String,
    login_ids: String,
    c69_user_input: String,
    c69_pass_input: String,
    otp_inputs: HashMap<u64, String>,
    show_login: bool,
    login_server: String,
    mun_filter: String,
    mun_sel: HashSet<u64>,
    mun_proxy_input: String,
    mun_confirm_delete: bool,
    new_name: String,
    new_os: usize,
    new_proxy: String,
    mun_mode: usize,
    show_create: bool,
    new_url: String,
    new_count: u32,
    proxy_import: String,
    proxy_replace: bool,
    proxy_test_one: String,
}

impl FarmGuiApp {
    pub fn new(cc: &eframe::CreationContext<'_>, port: u16) -> Self {
        // Font Segoe UI (tiếng Việt chuẩn Windows) — emoji/ký hiệu dùng font dự phòng của egui.
        let mut fonts = egui::FontDefinitions::default();
        let mut loaded = false;
        for (key, path) in [("segoeui", r"C:\Windows\Fonts\segoeui.ttf"), ("arial", r"C:\Windows\Fonts\arial.ttf")] {
            if loaded {
                break;
            }
            if let Ok(data) = std::fs::read(path) {
                fonts.font_data.insert(key.to_owned(), egui::FontData::from_owned(data));
                if let Some(prop) = fonts.families.get_mut(&egui::FontFamily::Proportional) {
                    prop.insert(0, key.to_owned());
                }
                loaded = true;
            }
        }
        cc.egui_ctx.set_fonts(fonts);

        let mut style = (*cc.egui_ctx.style()).clone();
        let mut v = egui::Visuals::dark();
        v.panel_fill = BG;
        v.window_fill = PANEL;
        v.extreme_bg_color = Color32::from_rgb(4, 6, 12);
        v.widgets.noninteractive.bg_stroke = Stroke::new(1.0_f32, BORDER);
        v.widgets.noninteractive.fg_stroke.color = TEXT;
        for w in [&mut v.widgets.inactive, &mut v.widgets.hovered, &mut v.widgets.active] {
            w.rounding = Rounding::same(6.0);
        }
        v.widgets.inactive.bg_fill = Color32::from_rgb(24, 33, 54);
        v.widgets.inactive.weak_bg_fill = Color32::from_rgb(24, 33, 54);
        v.widgets.hovered.weak_bg_fill = Color32::from_rgb(34, 48, 78);
        v.selection.bg_fill = Color32::from_rgb(2, 110, 170);
        style.visuals = v;
        style.spacing.item_spacing = vec2(8.0, 6.0);
        style.spacing.button_padding = vec2(10.0, 4.0);
        cc.egui_ctx.set_style(style);

        let api_base = format!("http://127.0.0.1:{}", port);
        let adb = Arc::new(AdbManager::new());
        let shared = Arc::new(Mutex::new(Shared::default()));
        let slots = Arc::new(Mutex::new(load_slots()));
        let ctl = Arc::new(StreamCtl::new(adb.get_adb_path().to_path_buf()));
        let refresh = Arc::new(AtomicBool::new(false));
        let ctx = cc.egui_ctx.clone();

        {
            let (a, s, sl, r, c, api) = (adb.clone(), shared.clone(), slots.clone(), refresh.clone(), ctx.clone(), api_base.clone());
            std::thread::spawn(move || fast_poller(api, a, s, sl, r, c));
        }
        {
            let (a, s, r) = (adb.clone(), shared.clone(), refresh.clone());
            std::thread::spawn(move || detail_poller(a, s, r));
        }
        // Pool 6 luồng chụp màn hình song song.
        for _ in 0..6 {
            let (a, c, s, x) = (adb.clone(), ctl.clone(), shared.clone(), ctx.clone());
            std::thread::spawn(move || stream_worker(a, c, s, x));
        }

        gui_log("🚀 MunAutomation Phone Farm — GUI thuần Rust sẵn sàng.");
        gui_log("💡 Click đầu thẻ để chọn máy • chuột phải = đổi slot • TT = mở TikTok • kéo/click trên màn hình để điều khiển.");

        Self {
            api_base,
            adb,
            shared,
            slots,
            ctl,
            refresh,
            textures: HashMap::new(),
            selected: HashSet::new(),
            tab: Tab::Farm,
            fit: true,
            scale: 1.0,
            zoom: None,
            videos: 20,
            like_pct: 60.0,
            comment_pct: 15.0,
            follow_pct: 10.0,
            min_watch: 8,
            max_watch: 25,
            gemini_key: String::new(),
            login_ids: String::new(),
            c69_user_input: String::new(),
            c69_pass_input: String::new(),
            otp_inputs: HashMap::new(),
            show_login: false,
            login_server: String::new(),
            mun_filter: String::new(),
            mun_sel: HashSet::new(),
            mun_proxy_input: String::new(),
            mun_confirm_delete: false,
            new_name: String::new(),
            new_os: 0,
            new_proxy: String::new(),
            mun_mode: 0,
            show_create: false,
            new_url: String::new(),
            new_count: 1,
            proxy_import: String::new(),
            proxy_replace: false,
            proxy_test_one: String::new(),
        }
    }

    /// Máy mục tiêu: máy đã chọn (đang online), nếu không chọn gì -> tất cả máy online, theo thứ tự slot.
    fn targets(&self, sh: &Shared, slots: &[String]) -> Vec<String> {
        let any_selected = slots.iter().any(|s| !s.is_empty() && self.selected.contains(s));
        slots
            .iter()
            .filter(|s| !s.is_empty() && sh.is_online(s) && (!any_selected || self.selected.contains(*s)))
            .cloned()
            .collect()
    }

    fn bulk_adb<F>(&self, serials: Vec<String>, label: &str, f: F)
    where
        F: Fn(&AdbManager, &str) + Send + Sync + 'static,
    {
        gui_log(format!("▶ {} — {} máy", label, serials.len()));
        let f = Arc::new(f);
        for s in serials {
            let (a, f) = (self.adb.clone(), f.clone());
            std::thread::spawn(move || f(&a, &s));
        }
    }

    fn start_nurture(&self, targets: Vec<String>) {
        if targets.is_empty() {
            gui_log("⚠ Không có máy online để nuôi.");
            return;
        }
        let max_watch = self.max_watch.max(self.min_watch);
        let body = json!({
            "devices": targets,
            "config": {
                "videos_per_session": self.videos,
                "like_probability": self.like_pct / 100.0,
                "comment_probability": self.comment_pct / 100.0,
                "follow_probability": self.follow_pct / 100.0,
                "min_watch_seconds": self.min_watch,
                "max_watch_seconds": max_watch,
                "gemini_api_key": self.gemini_key,
                "video_niche": "trending",
                "video_language": "en"
            }
        });
        http_post(&self.api_base, "/api/nurture/start", body, &format!("Nuôi TikTok ({} máy)", targets.len()));
    }

    fn start_login(&self, targets: Vec<String>, explicit_selection: bool) {
        if targets.is_empty() {
            gui_log("⚠ Không có máy online để login.");
            return;
        }
        let ids: Vec<u64> = self
            .login_ids
            .split(|c: char| !c.is_ascii_digit())
            .filter(|s| !s.is_empty())
            .filter_map(|s| s.parse().ok())
            .collect();
        let mut body = if !ids.is_empty() {
            json!({ "account_ids": ids })
        } else if let Some(Ok(v)) = find_payload_file().map(|d| serde_json::from_str::<Value>(&d)) {
            v
        } else {
            gui_log("⚠ Chưa có danh sách nick: nhập account_id C69 ở tab Điều khiển hoặc đặt file payload_clean_run.json.");
            return;
        };
        if ids.is_empty() && !explicit_selection {
            // Giữ nguyên danh sách máy trong payload nếu anh không chọn máy cụ thể.
            if body.get("serials").is_none() {
                body["serials"] = json!(targets);
            }
        } else {
            body["serials"] = json!(targets);
        }
        http_post(&self.api_base, "/api/farm/xml-login/start", body, &format!("Login XML ({} máy)", targets.len()));
    }
}

fn pill(ui: &mut egui::Ui, label: &str, value: &str, color: Color32) {
    egui::Frame::none()
        .fill(Color32::from_rgb(18, 25, 42))
        .stroke(Stroke::new(1.0_f32, BORDER))
        .rounding(Rounding::same(12.0))
        .inner_margin(egui::Margin::symmetric(9.0, 3.0))
        .show(ui, |ui| {
            ui.horizontal(|ui| {
                ui.spacing_mut().item_spacing.x = 5.0;
                ui.label(RichText::new(label).size(11.0).color(MUTED));
                ui.label(RichText::new(value).size(12.0).strong().color(color));
            });
        });
}

fn action_btn(ui: &mut egui::Ui, text: &str, fill: Color32) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).size(12.5).strong().color(Color32::WHITE))
            .fill(fill)
            .rounding(Rounding::same(6.0))
            .min_size(vec2(0.0, 26.0)),
    )
}

fn ghost_btn(ui: &mut egui::Ui, text: &str) -> egui::Response {
    ui.add(
        egui::Button::new(RichText::new(text).size(12.0).color(TEXT))
            .fill(Color32::from_rgb(22, 30, 50))
            .stroke(Stroke::new(1.0_f32, BORDER))
            .rounding(Rounding::same(6.0))
            .min_size(vec2(0.0, 26.0)),
    )
}

fn section<R>(ui: &mut egui::Ui, title: &str, add: impl FnOnce(&mut egui::Ui) -> R) {
    egui::Frame::none()
        .fill(PANEL)
        .stroke(Stroke::new(1.0_f32, BORDER))
        .rounding(Rounding::same(10.0))
        .inner_margin(14.0)
        .show(ui, |ui| {
            ui.set_width(ui.available_width());
            ui.label(RichText::new(title).size(14.0).strong().color(CYAN));
            ui.add_space(6.0);
            add(ui);
        });
    ui.add_space(8.0);
}

/// Trạng thái hiển thị của 1 máy: (nhãn, màu nhãn, màu viền)
fn card_status(sh: &Shared, serial: &str) -> (String, Color32, Color32) {
    let live = sh.live.get(serial);
    match live.map(|l| l.state.as_str()) {
        Some("device") => {}
        Some("unauthorized") => return ("⚠ Chưa cấp quyền USB".into(), ORANGE, ORANGE),
        Some("offline") => return ("ADB offline".into(), RED, RED),
        _ => return ("Mất kết nối".into(), MUTED, SLATE),
    }
    if let Some(lg) = sh.login.get(serial) {
        match lg.state.as_str() {
            "running" | "queued" | "detecting" => {
                let step = if lg.step.is_empty() { &lg.message } else { &lg.step };
                return (format!("🔐 {}", step), YELLOW, YELLOW);
            }
            "failed" => return (format!("✖ {}", lg.message), RED, RED),
            "success" => {
                let u = if lg.current_user.is_empty() { &lg.username } else { &lg.current_user };
                return (format!("✔ @{}", u.trim_start_matches('@')), GREEN, GREEN);
            }
            _ => {}
        }
    }
    if let Some(n) = sh.nurture.get(serial) {
        match n.status.as_str() {
            "Starting" | "Watching FYP" => {
                return (
                    format!("🌱 {}  👁{} ❤{}", n.account_label(), n.videos, n.likes),
                    GREEN,
                    GREEN,
                )
            }
            "Hoàn thành" => return (format!("✅ {} xong {} video", n.account_label(), n.videos), GREEN, Color32::from_rgb(22, 120, 70)),
            "Đã dừng" => return ("⏹ Đã dừng nuôi".into(), MUTED, CYAN),
            _ => {}
        }
    }
    ("Sẵn sàng".into(), Color32::from_rgb(148, 163, 184), Color32::from_rgb(40, 110, 150))
}

impl NurtureRow {
    fn account_label(&self) -> String {
        let u = self.user.trim_start_matches('@');
        if u.is_empty() || u == "Detecting..." || u == "Đang hoạt động" {
            "TikTok".into()
        } else {
            format!("@{}", u)
        }
    }
}

impl eframe::App for FarmGuiApp {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        self.ctl.focused.store(ctx.input(|i| i.viewport().focused.unwrap_or(true)), Ordering::Relaxed);
        ctx.request_repaint_after(Duration::from_millis(500));

        // Frame mới -> texture GPU
        {
            let mut frames = lock(&self.ctl.frames);
            for (s, img) in frames.drain() {
                match self.textures.get_mut(&s) {
                    Some(t) => t.set(img, egui::TextureOptions::LINEAR),
                    None => {
                        let t = ctx.load_texture(format!("tex_{}", s), img, egui::TextureOptions::LINEAR);
                        self.textures.insert(s, t);
                    }
                }
            }
        }

        let sh = lock(&self.shared).clone();
        let slots = lock(&self.slots).clone();
        let n_assigned = slots.iter().filter(|s| !s.is_empty()).count();
        let n_online = slots.iter().filter(|s| !s.is_empty() && sh.is_online(s)).count();
        let n_nurturing = sh.nurture.values().filter(|n| n.status == "Starting" || n.status == "Watching FYP").count();
        let n_selected = slots.iter().filter(|s| !s.is_empty() && self.selected.contains(*s)).count();
        let targets = self.targets(&sh, &slots);
        let explicit = n_selected > 0;
        let target_label = if explicit { format!("{} máy đã chọn", targets.len()) } else { format!("tất cả {} máy online", targets.len()) };

        // ── Thanh trên: thương hiệu + chỉ số + tab ──
        egui::TopBottomPanel::top("top")
            .frame(egui::Frame::none().fill(Color32::from_rgb(10, 14, 26)).inner_margin(egui::Margin::symmetric(12.0, 8.0)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    ui.label(RichText::new("⚡ MunAutomation").size(17.0).strong().color(CYAN));
                    ui.label(RichText::new("Phone Farm").size(12.0).color(MUTED));
                    ui.add_space(8.0);
                    let oc = if n_online == n_assigned && n_assigned > 0 { GREEN } else if n_online == 0 { RED } else { YELLOW };
                    pill(ui, "Online", &format!("{}/{}", n_online, n_assigned), oc);
                    pill(ui, "Đang nuôi", &n_nurturing.to_string(), if n_nurturing > 0 { GREEN } else { MUTED });
                    let (lt, lc) = if sh.login_running {
                        (format!("chạy • còn {}", sh.login_queue.4), YELLOW)
                    } else {
                        ("nghỉ".to_string(), MUTED)
                    };
                    pill(ui, "Login", &lt, lc);
                    pill(ui, "Profiles", &sh.profile_count.to_string(), Color32::from_rgb(168, 85, 247));
                    pill(
                        ui,
                        "C69",
                        sh.c69_user.as_deref().unwrap_or("chưa đăng nhập"),
                        if sh.c69_user.is_some() { GREEN } else { ORANGE },
                    );
                    if sh.c69_user.is_some() {
                        if ghost_btn(ui, "🚪 Đăng xuất").clicked() {
                            http_post(&self.api_base, "/api/c69/auth/logout", json!({}), "Đăng xuất C69");
                            self.refresh.store(true, Ordering::Relaxed);
                        }
                    } else if action_btn(ui, "🔑 Đăng nhập", Color32::from_rgb(2, 110, 170)).clicked() {
                        self.show_login = true;
                    }
                    if !sh.api_ok {
                        pill(ui, "API", "mất kết nối", RED);
                    }
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        for (tab, label) in [
                            (Tab::Logs, "📜 Logs"),
                            (Tab::Proxy, "🛡 Proxy"),
                            (Tab::Mun, "🌐 Mun Browser"),
                            (Tab::Control, "⚙ Điều khiển"),
                            (Tab::Farm, "📱 Giàn máy"),
                        ] {
                            let sel = self.tab == tab;
                            let b = egui::Button::new(RichText::new(label).size(12.5).strong().color(if sel { Color32::WHITE } else { MUTED }))
                                .fill(if sel { Color32::from_rgb(2, 110, 170) } else { Color32::TRANSPARENT })
                                .stroke(Stroke::new(1.0_f32, if sel { CYAN } else { BORDER }))
                                .rounding(Rounding::same(6.0))
                                .min_size(vec2(0.0, 26.0));
                            if ui.add(b).clicked() {
                                self.tab = tab;
                            }
                        }
                    });
                });
                ui.add_space(6.0);
                // ── Thanh công cụ ──
                ui.horizontal_wrapped(|ui| {
                    ui.label(RichText::new("Chọn:").size(12.0).color(MUTED));
                    if ghost_btn(ui, "☑ Tất cả online").clicked() {
                        self.selected = slots.iter().filter(|s| !s.is_empty() && sh.is_online(s)).cloned().collect();
                    }
                    if ghost_btn(ui, "☐ Bỏ chọn").clicked() {
                        self.selected.clear();
                    }
                    ui.label(RichText::new(format!("→ {}", target_label)).size(12.0).strong().color(ORANGE));
                    ui.separator();
                    if action_btn(ui, "▶ Nuôi TikTok", Color32::from_rgb(5, 150, 105)).clicked() {
                        self.start_nurture(targets.clone());
                    }
                    if action_btn(ui, "⏹ Dừng nuôi", Color32::from_rgb(190, 40, 40)).clicked() {
                        http_post(&self.api_base, "/api/nurture/stop", json!({}), "Dừng nuôi TikTok");
                    }
                    ui.separator();
                    if action_btn(ui, "🔐 Login XML", Color32::from_rgb(180, 120, 10)).clicked() {
                        self.start_login(targets.clone(), explicit);
                    }
                    if ghost_btn(ui, "⏹ Dừng login").clicked() {
                        http_post(&self.api_base, "/api/farm/xml-login/stop", json!({}), "Dừng login XML");
                    }
                    ui.separator();
                    if ghost_btn(ui, "🎵 Mở TikTok").clicked() {
                        self.bulk_adb(targets.clone(), "Mở TikTok", |a, s| {
                            let _ = a.launch_app(s, TIKTOK_PKG);
                        });
                    }
                    if ghost_btn(ui, "🏠 Home").clicked() {
                        self.bulk_adb(targets.clone(), "Về Home", |a, s| {
                            let _ = a.keyevent(s, 3);
                        });
                    }
                    if ghost_btn(ui, "💡 Đánh thức").clicked() {
                        self.bulk_adb(targets.clone(), "Đánh thức", |a, s| {
                            let _ = a.wake_up(s);
                        });
                    }
                    ui.separator();
                    let stream_on = self.ctl.enabled.load(Ordering::Relaxed);
                    if ghost_btn(ui, if stream_on { "📺 Stream: BẬT" } else { "📺 Stream: TẮT" }).clicked() {
                        self.ctl.enabled.store(!stream_on, Ordering::Relaxed);
                    }
                    ui.checkbox(&mut self.fit, "Vừa màn hình");
                    if !self.fit {
                        ui.spacing_mut().slider_width = 90.0;
                        ui.add(egui::Slider::new(&mut self.scale, 0.5..=1.8).show_value(false));
                    }
                    if ghost_btn(ui, "🔄 Quét lại").clicked() {
                        self.refresh.store(true, Ordering::Relaxed);
                        gui_log("🔄 Quét lại thiết bị ADB...");
                    }
                });
            });

        // ── Thanh dưới: dòng log mới nhất ──
        egui::TopBottomPanel::bottom("bottom")
            .frame(egui::Frame::none().fill(Color32::from_rgb(10, 14, 26)).inner_margin(egui::Margin::symmetric(12.0, 4.0)))
            .show(ctx, |ui| {
                ui.horizontal(|ui| {
                    let last = lock(logs()).back().cloned().unwrap_or_default();
                    ui.label(RichText::new(last).size(11.0).color(MUTED));
                    ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                        ui.label(RichText::new(format!("Đã chọn {} • slot {}", n_selected, slots.len())).size(11.0).color(MUTED));
                    });
                });
            });

        // ── Cửa sổ đăng nhập C69 ──
        if self.show_login {
            let mut open = true;
            let mut do_login = false;
            egui::Window::new("🔑 Đăng nhập C69").open(&mut open).collapsible(false).resizable(false).show(ctx, |ui| {
                ui.add(egui::TextEdit::singleline(&mut self.c69_user_input).hint_text("Username").desired_width(260.0));
                ui.add(egui::TextEdit::singleline(&mut self.c69_pass_input).password(true).hint_text("Mật khẩu").desired_width(260.0));
                ui.add(egui::TextEdit::singleline(&mut self.login_server).hint_text("Server URL (để trống = mặc định)").desired_width(260.0));
                if action_btn(ui, "Đăng nhập", Color32::from_rgb(2, 110, 170)).clicked() {
                    do_login = true;
                }
            });
            if do_login {
                let mut body = json!({ "username": self.c69_user_input, "password": self.c69_pass_input });
                if !self.login_server.trim().is_empty() {
                    body["server_url"] = json!(self.login_server.trim());
                }
                http_post(&self.api_base, "/api/c69/auth/login", body, "Đăng nhập C69");
                self.c69_pass_input.clear();
                self.show_login = false;
            } else if !open {
                self.show_login = false;
            }
        }

        // ── Nội dung chính ──
        let mut card_events: Vec<(usize, CardEvent)> = Vec::new();
        egui::CentralPanel::default()
            .frame(egui::Frame::none().fill(BG).inner_margin(egui::Margin::same(8.0)))
            .show(ctx, |ui| match self.tab {
                Tab::Farm => {
                    let gap = 6.0;
                    let avail = ui.available_size() - vec2(4.0, 4.0);
                    let n = slots.len();
                    let (w, cols) = if self.fit {
                        fit_layout(avail, n, gap)
                    } else {
                        let w = (200.0 * self.scale).clamp(MIN_CARD_W, 520.0);
                        (w, (((avail.x + gap) / (w + gap)) as usize).max(1))
                    };
                    let wheel_ok = self.fit || ui.input(|i| i.modifiers.ctrl);
                    egui::ScrollArea::vertical().auto_shrink([false, false]).show(ui, |ui| {
                        ui.spacing_mut().item_spacing = vec2(gap, gap);
                        let rows = (n + cols - 1) / cols;
                        for r in 0..rows {
                            ui.horizontal(|ui| {
                                for c in 0..cols {
                                    let idx = r * cols + c;
                                    if idx >= n {
                                        break;
                                    }
                                    let serial = &slots[idx];
                                    if serial.is_empty() {
                                        draw_empty_slot(ui, w, idx);
                                        continue;
                                    }
                                    let (label, label_color, accent) = card_status(&sh, serial);
                                    let info = CardInfo {
                                        salt: "grid",
                                        idx,
                                        serial,
                                        live: sh.live.get(serial),
                                        label,
                                        label_color,
                                        accent,
                                        selected: self.selected.contains(serial),
                                        wheel_ok,
                                        tex: self.textures.get(serial),
                                    };
                                    for ev in draw_card(ui, w, &info, &self.adb, &self.ctl) {
                                        card_events.push((idx, ev));
                                    }
                                }
                            });
                        }
                    });
                }
                Tab::Control => {
                    egui::ScrollArea::vertical().auto_shrink([false, false]).show(ui, |ui| {
                        self.control_tab(ui, &targets, &target_label, explicit);
                    });
                }
                Tab::Mun => {
                    self.mun_tab(ui, &sh);
                }
                Tab::Proxy => {
                    egui::ScrollArea::vertical().auto_shrink([false, false]).show(ui, |ui| {
                        self.proxy_tab(ui, &sh);
                    });
                }
                Tab::Logs => {
                    ui.horizontal(|ui| {
                        ui.label(RichText::new("📜 Nhật ký hoạt động").size(15.0).strong());
                        if ghost_btn(ui, "🗑 Xóa log").clicked() {
                            lock(logs()).clear();
                        }
                    });
                    ui.add_space(4.0);
                    egui::Frame::none()
                        .fill(PANEL)
                        .stroke(Stroke::new(1.0_f32, BORDER))
                        .rounding(Rounding::same(8.0))
                        .inner_margin(10.0)
                        .show(ui, |ui| {
                            egui::ScrollArea::vertical().stick_to_bottom(true).auto_shrink([false, false]).show(ui, |ui| {
                                for line in lock(logs()).iter() {
                                    ui.label(RichText::new(line).monospace().size(11.5).color(Color32::from_rgb(203, 213, 225)));
                                }
                            });
                        });
                }
            });

        // ── Xử lý sự kiện thẻ ──
        for (idx, ev) in card_events {
            let serial = slots[idx].clone();
            match ev {
                CardEvent::Select => {
                    if !self.selected.remove(&serial) {
                        self.selected.insert(serial);
                    }
                }
                CardEvent::Zoom => {
                    *lock(&self.ctl.zoom) = Some(serial.clone());
                    self.zoom = Some(serial);
                }
                CardEvent::MoveUp | CardEvent::MoveDown | CardEvent::Clear => {
                    let mut sl = lock(&self.slots);
                    match ev {
                        CardEvent::MoveUp if idx > 0 => sl.swap(idx, idx - 1),
                        CardEvent::MoveDown if idx + 1 < sl.len() => sl.swap(idx, idx + 1),
                        CardEvent::Clear => sl[idx].clear(),
                        _ => {}
                    }
                    save_slots(&sl);
                }
            }
        }

        // ── Cửa sổ phóng to ──
        if let Some(zs) = self.zoom.clone() {
            let idx = slots.iter().position(|s| *s == zs).unwrap_or(0);
            let mut open = true;
            let mut zoom_events = Vec::new();
            egui::Window::new(format!("Máy #{:02}  ·  {}", idx + 1, short_serial(&zs)))
                .open(&mut open)
                .collapsible(false)
                .resizable(false)
                .show(ctx, |ui| {
                    let h_avail = ctx.screen_rect().height() - 140.0;
                    let w = ((h_avail - HDR_H - FOOT_H - PAD) / ASPECT + 2.0 * PAD).clamp(220.0, 520.0);
                    let (label, label_color, accent) = card_status(&sh, &zs);
                    let info = CardInfo {
                        salt: "zoom",
                        idx,
                        serial: &zs,
                        live: sh.live.get(&zs),
                        label,
                        label_color,
                        accent,
                        selected: self.selected.contains(&zs),
                        wheel_ok: true,
                        tex: self.textures.get(&zs),
                    };
                    zoom_events = draw_card(ui, w, &info, &self.adb, &self.ctl);
                });
            for ev in zoom_events {
                if let CardEvent::Select = ev {
                    if !self.selected.remove(&zs) {
                        self.selected.insert(zs.clone());
                    }
                }
            }
            if !open {
                self.zoom = None;
                *lock(&self.ctl.zoom) = None;
            }
        }
    }
}

impl FarmGuiApp {
    fn control_tab(&mut self, ui: &mut egui::Ui, targets: &[String], target_label: &str, explicit: bool) {
        section(ui, "🌱 Nuôi TikTok trên điện thoại", |ui| {
            ui.label(RichText::new(format!("Áp dụng cho: {}", target_label)).color(ORANGE));
            ui.add_space(4.0);
            egui::Grid::new("nurture_cfg").num_columns(2).spacing([14.0, 8.0]).show(ui, |ui| {
                ui.label("Số video / phiên");
                ui.add(egui::Slider::new(&mut self.videos, 1..=200));
                ui.end_row();
                ui.label("Xác suất thả tim (%)");
                ui.add(egui::Slider::new(&mut self.like_pct, 0.0..=100.0));
                ui.end_row();
                ui.label("Xác suất bình luận (%)");
                ui.add(egui::Slider::new(&mut self.comment_pct, 0.0..=100.0));
                ui.end_row();
                ui.label("Xác suất follow (%)");
                ui.add(egui::Slider::new(&mut self.follow_pct, 0.0..=100.0));
                ui.end_row();
                ui.label("Thời gian xem tối thiểu (giây)");
                ui.add(egui::Slider::new(&mut self.min_watch, 1..=120));
                ui.end_row();
                ui.label("Thời gian xem tối đa (giây)");
                ui.add(egui::Slider::new(&mut self.max_watch, 1..=180));
                ui.end_row();
                ui.label("Gemini API key (bình luận AI)");
                ui.add(egui::TextEdit::singleline(&mut self.gemini_key).password(true).desired_width(280.0));
                ui.end_row();
            });
            ui.add_space(6.0);
            ui.horizontal(|ui| {
                if action_btn(ui, "▶ Bắt đầu nuôi", Color32::from_rgb(5, 150, 105)).clicked() {
                    self.start_nurture(targets.to_vec());
                }
                if action_btn(ui, "⏹ Dừng nuôi", Color32::from_rgb(190, 40, 40)).clicked() {
                    http_post(&self.api_base, "/api/nurture/stop", json!({}), "Dừng nuôi TikTok");
                }
            });
        });

        section(ui, "🔐 Login nick TikTok (Native XML)", |ui| {
            ui.label(
                RichText::new("Nhập account_id trên C69 (cách nhau dấu phẩy/xuống dòng). Để trống = dùng file payload_clean_run.json.")
                    .size(12.0)
                    .color(MUTED),
            );
            ui.add(
                egui::TextEdit::multiline(&mut self.login_ids)
                    .desired_rows(3)
                    .desired_width(f32::INFINITY)
                    .hint_text("vd: 101, 102, 103"),
            );
            ui.horizontal(|ui| {
                if action_btn(ui, "🔐 Bắt đầu login", Color32::from_rgb(180, 120, 10)).clicked() {
                    self.start_login(targets.to_vec(), explicit);
                }
                if ghost_btn(ui, "⏹ Dừng login").clicked() {
                    http_post(&self.api_base, "/api/farm/xml-login/stop", json!({}), "Dừng login XML");
                }
            });
        });

        section(ui, "🔑 Tài khoản C69", |ui| {
            ui.horizontal(|ui| {
                ui.add(egui::TextEdit::singleline(&mut self.c69_user_input).hint_text("Username").desired_width(160.0));
                ui.add(egui::TextEdit::singleline(&mut self.c69_pass_input).password(true).hint_text("Mật khẩu").desired_width(160.0));
                if action_btn(ui, "Đăng nhập C69", Color32::from_rgb(2, 110, 170)).clicked() {
                    http_post(
                        &self.api_base,
                        "/api/c69/auth/login",
                        json!({ "username": self.c69_user_input, "password": self.c69_pass_input }),
                        "Đăng nhập C69",
                    );
                }
                if ghost_btn(ui, "Đăng xuất").clicked() {
                    http_post(&self.api_base, "/api/c69/auth/logout", json!({}), "Đăng xuất C69");
                }
            });
        });

        section(ui, "🧰 Thao tác hàng loạt (ADB)", |ui| {
            ui.label(RichText::new(format!("Áp dụng cho: {}", target_label)).color(ORANGE));
            ui.add_space(4.0);
            ui.horizontal_wrapped(|ui| {
                if ghost_btn(ui, "🎵 Mở TikTok").clicked() {
                    self.bulk_adb(targets.to_vec(), "Mở TikTok", |a, s| {
                        let _ = a.launch_app(s, TIKTOK_PKG);
                    });
                }
                if ghost_btn(ui, "⛔ Đóng TikTok").clicked() {
                    self.bulk_adb(targets.to_vec(), "Đóng TikTok", |a, s| {
                        let _ = a.force_stop(s, TIKTOK_PKG);
                    });
                }
                if ghost_btn(ui, "🏠 Home").clicked() {
                    self.bulk_adb(targets.to_vec(), "Về Home", |a, s| {
                        let _ = a.keyevent(s, 3);
                    });
                }
                if ghost_btn(ui, "◀ Back").clicked() {
                    self.bulk_adb(targets.to_vec(), "Back", |a, s| {
                        let _ = a.keyevent(s, 4);
                    });
                }
                if ghost_btn(ui, "💡 Đánh thức + mở khóa").clicked() {
                    self.bulk_adb(targets.to_vec(), "Mở khóa", |a, s| {
                        let _ = a.unlock(s);
                    });
                }
                if ghost_btn(ui, "📶 Bật Wi-Fi").clicked() {
                    self.bulk_adb(targets.to_vec(), "Bật Wi-Fi", |a, s| {
                        let _ = a.wifi_enable(s);
                    });
                }
                if ghost_btn(ui, "📐 Tối ưu 720x1480").clicked() {
                    self.bulk_adb(targets.to_vec(), "Tối ưu độ phân giải", |a, s| {
                        let _ = a.optimize_farm_device(s);
                    });
                }
            });
        });

        section(ui, "📍 Quản lý vị trí (slot)", |ui| {
            ui.label(
                RichText::new(
                    "Mỗi máy giữ 1 slot cố định (lưu trong farm_slots.json). Máy mới cắm vào sẽ tự xếp vào slot trống đầu tiên. \
                     Chuột phải vào đầu thẻ máy để đổi chỗ / bỏ khỏi slot.",
                )
                .size(12.0)
                .color(MUTED),
            );
            if ghost_btn(ui, "♻ Đặt lại slot về mặc định").clicked() {
                let mut sl = lock(&self.slots);
                *sl = DEFAULT_SLOTS.iter().map(|s| s.to_string()).collect();
                sl.push(String::new());
                save_slots(&sl);
                gui_log("♻ Đã đặt lại thứ tự slot mặc định.");
            }
        });
    }

    fn browser_tab(&mut self, ui: &mut egui::Ui, sh: &Shared) {
        ui.horizontal(|ui| {
            ui.label(RichText::new("🖥 Nuôi TikTok trên Profile PC (Browser)").size(15.0).strong());
            let running = sh.browser.iter().filter(|b| b.running).count();
            ui.label(RichText::new(format!("{} đang chạy / {} profile", running, sh.browser.len())).color(MUTED));
        });
        ui.add_space(6.0);
        if sh.browser.is_empty() {
            ui.label(RichText::new("Chưa có phiên nuôi trên profile PC nào. Bắt đầu từ web UI hoặc API /api/browser/nurture/*.").color(MUTED));
            return;
        }
        egui::Frame::none().fill(PANEL).stroke(Stroke::new(1.0_f32, BORDER)).rounding(Rounding::same(8.0)).inner_margin(10.0).show(ui, |ui| {
            egui::Grid::new("browser_grid").striped(true).num_columns(7).spacing([14.0, 8.0]).show(ui, |ui| {
                for h in ["#", "Profile", "Nick", "Trạng thái", "👁 ❤ 💬", "Log gần nhất", "Thao tác"] {
                    ui.label(RichText::new(h).strong().color(CYAN));
                }
                ui.end_row();
                for b in &sh.browser {
                    ui.label(b.id.to_string());
                    ui.label(truncate(&b.name, 22));
                    ui.label(RichText::new(truncate(&b.user, 22)).color(YELLOW));
                    ui.label(RichText::new(truncate(&b.status, 30)).color(if b.running { GREEN } else { MUTED }));
                    ui.label(format!("{} / {} / {}", b.videos, b.likes, b.comments));
                    ui.label(RichText::new(truncate(&b.last_log, 60)).size(11.0).color(MUTED));
                    ui.horizontal(|ui| {
                        if b.running && ghost_btn(ui, "⏹ Dừng").clicked() {
                            http_post(&self.api_base, "/api/browser/nurture/stop", json!({ "profile_id": b.id }), &format!("Dừng profile #{}", b.id));
                        }
                        if b.waiting_otp {
                            let buf = self.otp_inputs.entry(b.id).or_default();
                            ui.add(egui::TextEdit::singleline(buf).hint_text("OTP").desired_width(70.0));
                            if action_btn(ui, "Gửi OTP", Color32::from_rgb(180, 120, 10)).clicked() && !buf.trim().is_empty() {
                                http_post(
                                    &self.api_base,
                                    &format!("/api/browser/nurture/{}/submit-otp", b.id),
                                    json!({ "otp": buf.trim() }),
                                    &format!("OTP profile #{}", b.id),
                                );
                                buf.clear();
                            }
                        }
                    });
                    ui.end_row();
                }
            });
        });
    }
}

fn proxy_color(status: &str) -> Color32 {
    let s = status.to_lowercase();
    if s.contains("alive") || s.contains("live") || s == "ok" || s.contains("active") {
        GREEN
    } else if s.contains("dead") || s.contains("die") || s.contains("fail") || s.contains("timeout") || s.contains("error") {
        RED
    } else {
        MUTED
    }
}

fn hide_proxy_pass(p: &str) -> String {
    // socks5://user:pass@host:port -> socks5://user:***@host:port
    if let (Some(a), Some(at)) = (p.find("://"), p.rfind('@')) {
        let cred = &p[a + 3..at];
        if let Some(c) = cred.find(':') {
            return format!("{}{}:***{}", &p[..a + 3], &cred[..c], &p[at..]);
        }
    }
    p.to_string()
}

impl FarmGuiApp {
    fn mun_tab(&mut self, ui: &mut egui::Ui, sh: &Shared) {
        let api = self.api_base.clone();
        let proxy_status: HashMap<&str, &str> = sh.proxies.iter().map(|p| (p.proxy.as_str(), p.status.as_str())).collect();
        let running_ids: HashSet<u64> = sh.browser.iter().filter(|b| b.running).map(|b| b.id).collect();
        let is_err = |p: &ProfRow| {
            let s = p.status.to_lowercase();
            s.contains("maximum") || s.contains("error") || s.contains("fail") || s.contains("lỗi") || s.contains("rate_limit") || s.contains("captcha")
        };

        // ── Hàng 1: tiêu đề + chỉ số ──
        let n_open = sh.active_profiles.len();
        let n_noproxy = sh.profiles.iter().filter(|p| p.proxy.trim().is_empty()).count();
        let n_err = sh.profiles.iter().filter(|p| is_err(p)).count();
        ui.horizontal_wrapped(|ui| {
            ui.label(RichText::new("🌐 Mun Anti Browser").size(17.0).strong().color(CYAN));
            pill(ui, "Profile", &sh.profiles.len().to_string(), TEXT);
            pill(ui, "Đang mở", &n_open.to_string(), if n_open > 0 { GREEN } else { MUTED });
            pill(ui, "Đang nuôi", &running_ids.len().to_string(), if running_ids.is_empty() { MUTED } else { GREEN });
            pill(ui, "Thiếu proxy", &n_noproxy.to_string(), if n_noproxy > 0 { ORANGE } else { MUTED });
            pill(ui, "Lỗi", &n_err.to_string(), if n_err > 0 { RED } else { MUTED });
            ui.label(RichText::new(if sh.core.is_empty() { "đang kiểm tra core...".to_string() } else { sh.core.clone() }).size(11.0).color(MUTED));
        });
        ui.add_space(4.0);

        // ── Hàng 2: tìm kiếm + bộ lọc + tạo/đồng bộ ──
        ui.horizontal_wrapped(|ui| {
            ui.add(egui::TextEdit::singleline(&mut self.mun_filter).hint_text("🔎 Tìm tên / nick / id / proxy").desired_width(230.0));
            for (i, label) in ["Tất cả", "Đang mở", "Đang nuôi", "Thiếu proxy", "Lỗi"].iter().enumerate() {
                let sel = self.mun_mode == i;
                let b = egui::Button::new(RichText::new(*label).size(12.0).color(if sel { Color32::WHITE } else { MUTED }))
                    .fill(if sel { Color32::from_rgb(2, 110, 170) } else { Color32::TRANSPARENT })
                    .stroke(Stroke::new(1.0_f32, if sel { CYAN } else { BORDER }))
                    .rounding(Rounding::same(12.0));
                if ui.add(b).clicked() {
                    self.mun_mode = i;
                }
            }
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if action_btn(ui, "➕ Tạo profile", Color32::from_rgb(5, 150, 105)).clicked() {
                    self.show_create = true;
                }
                if ghost_btn(ui, "🔄 Đồng bộ C69").clicked() {
                    http_post(&api, "/api/browser/c69/sync-profiles", json!({}), "Đồng bộ profile từ C69");
                }
            });
        });
        ui.add_space(4.0);

        // ── Lọc ──
        let filter = self.mun_filter.trim().to_lowercase();
        let rows: Vec<&ProfRow> = sh
            .profiles
            .iter()
            .filter(|p| match self.mun_mode {
                1 => sh.active_profiles.contains(&p.id),
                2 => running_ids.contains(&p.id),
                3 => p.proxy.trim().is_empty(),
                4 => is_err(p),
                _ => true,
            })
            .filter(|p| {
                filter.is_empty()
                    || p.name.to_lowercase().contains(&filter)
                    || p.user.to_lowercase().contains(&filter)
                    || p.id.to_string() == filter
                    || p.proxy.to_lowercase().contains(&filter)
            })
            .collect();
        let sel_ids: Vec<u64> = sh.profiles.iter().map(|p| p.id).filter(|id| self.mun_sel.contains(id)).collect();
        let n_sel = sel_ids.len();
        let ids_json = json!(sel_ids);

        // ── Thanh thao tác hàng loạt (chỉ hiện khi có chọn) ──
        if n_sel > 0 {
            egui::Frame::none()
                .fill(Color32::from_rgb(10, 40, 62))
                .stroke(Stroke::new(1.0_f32, CYAN))
                .rounding(Rounding::same(8.0))
                .inner_margin(egui::Margin::symmetric(10.0, 6.0))
                .show(ui, |ui| {
                    ui.horizontal_wrapped(|ui| {
                        ui.label(RichText::new(format!("✔ Đã chọn {}", n_sel)).strong().color(CYAN));
                        if ghost_btn(ui, "Bỏ chọn").clicked() {
                            self.mun_sel.clear();
                        }
                        ui.separator();
                        if action_btn(ui, "▶ Nuôi", Color32::from_rgb(5, 150, 105)).clicked() {
                            http_post(&api, "/api/browser/nurture/start-selected", json!({ "profile_ids": ids_json, "auto_assign_c69_proxy": true }), &format!("Nuôi {} profile", n_sel));
                        }
                        if action_btn(ui, "⏹ Dừng nuôi", Color32::from_rgb(190, 40, 40)).clicked() {
                            for id in &sel_ids {
                                http_post(&api, "/api/browser/nurture/stop", json!({ "profile_id": id }), &format!("Dừng nuôi #{}", id));
                            }
                        }
                        ui.separator();
                        if ghost_btn(ui, "🚀 Mở").clicked() {
                            for id in &sel_ids {
                                http_post(&api, &format!("/api/browser/profiles/{}/launch", id), json!({ "id": id }), &format!("Mở profile #{}", id));
                            }
                        }
                        if ghost_btn(ui, "⏏ Đóng").clicked() {
                            for id in &sel_ids {
                                http_post(&api, &format!("/api/browser/profiles/{}/stop", id), json!({ "id": id }), &format!("Đóng profile #{}", id));
                            }
                        }
                        ui.separator();
                        ui.menu_button("🛡 Proxy ▾", |ui| {
                            ui.add(egui::TextEdit::singleline(&mut self.mun_proxy_input).hint_text("socks5://user:pass@host:port").desired_width(260.0));
                            if ui.button("Đổi proxy cho các profile chọn").clicked() && !self.mun_proxy_input.trim().is_empty() {
                                http_post(&api, "/api/browser/profiles/change-proxy", json!({ "profile_ids": ids_json, "proxy_string": self.mun_proxy_input.trim() }), "Đổi proxy");
                                ui.close_menu();
                            }
                            if ui.button("Gán proxy sống từ kho (mỗi profile 1 proxy)").clicked() {
                                let alive: Vec<&ProxyRow> = sh.proxies.iter().filter(|p| proxy_color(&p.status) == GREEN).collect();
                                if alive.is_empty() {
                                    gui_log("✖ Kho proxy chưa có proxy sống — qua tab Proxy bấm Test tất cả.");
                                }
                                for (i, id) in sel_ids.iter().enumerate() {
                                    if let Some(p) = alive.get(i % alive.len().max(1)) {
                                        http_post(&api, "/api/browser/profiles/change-proxy", json!({ "profile_ids": [id], "proxy_string": p.proxy }), &format!("Gán proxy #{}", id));
                                    }
                                }
                                ui.close_menu();
                            }
                        });
                        ui.menu_button("🧬 Fingerprint ▾", |ui| {
                            if ui.button("🎲 Fingerprint mới").clicked() {
                                http_post(&api, "/api/browser/profiles/randomize-fingerprints", json!({ "profile_ids": ids_json }), "Fingerprint mới");
                                ui.close_menu();
                            }
                            if ui.button("📱 Chuyển Mobile").clicked() {
                                http_post(&api, "/api/browser/profiles/switch-mode", json!({ "profile_ids": ids_json, "mode": "mobile" }), "Chuyển Mobile");
                                ui.close_menu();
                            }
                            if ui.button("🖥 Chuyển Desktop").clicked() {
                                http_post(&api, "/api/browser/profiles/switch-mode", json!({ "profile_ids": ids_json, "mode": "desktop" }), "Chuyển Desktop");
                                ui.close_menu();
                            }
                            if ui.button("🧹 Xóa dữ liệu duyệt").clicked() {
                                for id in &sel_ids {
                                    http_post(&api, &format!("/api/browser/profiles/{}/clear", id), json!({}), &format!("Xóa dữ liệu #{}", id));
                                }
                                ui.close_menu();
                            }
                        });
                        ui.separator();
                        if self.mun_confirm_delete {
                            if action_btn(ui, &format!("⚠ Xác nhận xóa {}", n_sel), Color32::from_rgb(190, 40, 40)).clicked() {
                                for id in &sel_ids {
                                    http_call("DELETE", &api, &format!("/api/browser/profiles/{}", id), Value::Null, &format!("Xóa profile #{}", id));
                                }
                                self.mun_sel.clear();
                                self.mun_confirm_delete = false;
                            }
                            if ghost_btn(ui, "Hủy").clicked() {
                                self.mun_confirm_delete = false;
                            }
                        } else if ghost_btn(ui, "🗑 Xóa").clicked() {
                            self.mun_confirm_delete = true;
                        }
                    });
                });
            ui.add_space(4.0);
        } else {
            self.mun_confirm_delete = false;
        }

        // ── Bảng profile (ảo hoá: chỉ vẽ dòng nhìn thấy, mượt với hàng nghìn profile) ──
        const W: [f32; 7] = [30.0, 54.0, 190.0, 150.0, 130.0, 270.0, 150.0];
        const ROW_H: f32 = 28.0;
        let cell = |ui: &mut egui::Ui, w: f32, f: &mut dyn FnMut(&mut egui::Ui)| {
            ui.allocate_ui_with_layout(vec2(w, ROW_H), egui::Layout::left_to_right(egui::Align::Center), |ui| {
                ui.set_min_width(w);
                ui.set_max_width(w);
                f(ui);
            });
        };
        let sess_h = if sh.browser.is_empty() { 0.0 } else { 190.0 };
        let table_h = (ui.available_height() - sess_h - 6.0).max(160.0);

        egui::Frame::none().fill(PANEL).stroke(Stroke::new(1.0_f32, BORDER)).rounding(Rounding::same(8.0)).inner_margin(egui::Margin::symmetric(8.0, 6.0)).show(ui, |ui| {
            ui.set_height(table_h);
            // Header
            ui.horizontal(|ui| {
                let all_sel = !rows.is_empty() && rows.iter().all(|p| self.mun_sel.contains(&p.id));
                let mut c = all_sel;
                cell(ui, W[0], &mut |ui| {
                    if ui.checkbox(&mut c, "").on_hover_text("Chọn / bỏ chọn tất cả (theo bộ lọc)").changed() {
                        if c {
                            for p in &rows {
                                self.mun_sel.insert(p.id);
                            }
                        } else {
                            for p in &rows {
                                self.mun_sel.remove(&p.id);
                            }
                        }
                    }
                });
                for (i, h) in ["#", "Tên profile", "Nick TikTok", "OS / Mode", "Proxy", "Trạng thái"].iter().enumerate() {
                    cell(ui, W[i + 1], &mut |ui| {
                        ui.label(RichText::new(*h).strong().size(12.0).color(CYAN));
                    });
                }
                ui.label(RichText::new(format!("{} / {} profile", rows.len(), sh.profiles.len())).size(11.0).color(MUTED));
            });
            ui.separator();
            if rows.is_empty() {
                ui.add_space(20.0);
                ui.vertical_centered(|ui| {
                    ui.label(RichText::new(if sh.profiles.is_empty() { "Chưa có profile. Bấm ➕ Tạo profile hoặc 🔄 Đồng bộ C69." } else { "Không có profile khớp bộ lọc." }).color(MUTED));
                });
                return;
            }
            egui::ScrollArea::vertical().auto_shrink([false, false]).show_rows(ui, ROW_H, rows.len(), |ui, range| {
                ui.spacing_mut().item_spacing.y = 0.0;
                for idx in range {
                    let p = rows[idx];
                    let selected = self.mun_sel.contains(&p.id);
                    let open = sh.active_profiles.contains(&p.id);
                    let nurturing = running_ids.contains(&p.id);
                    let fill = if selected {
                        Color32::from_rgb(12, 52, 80)
                    } else if idx % 2 == 1 {
                        Color32::from_rgb(16, 22, 38)
                    } else {
                        Color32::TRANSPARENT
                    };
                    egui::Frame::none().fill(fill).rounding(Rounding::same(4.0)).show(ui, |ui| {
                        ui.set_width(ui.available_width());
                        ui.horizontal(|ui| {
                            let mut c = selected;
                            cell(ui, W[0], &mut |ui| {
                                if ui.checkbox(&mut c, "").changed() {
                                    if c {
                                        self.mun_sel.insert(p.id);
                                    } else {
                                        self.mun_sel.remove(&p.id);
                                    }
                                }
                            });
                            cell(ui, W[1], &mut |ui| {
                                ui.label(RichText::new(p.id.to_string()).color(MUTED));
                            });
                            cell(ui, W[2], &mut |ui| {
                                ui.label(RichText::new(truncate(&p.name, 24)).strong());
                            });
                            cell(ui, W[3], &mut |ui| {
                                ui.label(RichText::new(if p.user.is_empty() { "—".to_string() } else { truncate(&p.user, 20) }).color(if p.user.is_empty() { MUTED } else { YELLOW }));
                            });
                            cell(ui, W[4], &mut |ui| {
                                let mobile = p.os.eq_ignore_ascii_case("android") || p.os.eq_ignore_ascii_case("ios") || p.mode.to_lowercase().contains("mobile");
                                ui.label(RichText::new(format!("{} {}", if mobile { "📱" } else { "🖥" }, p.os)).size(12.0));
                            });
                            cell(ui, W[5], &mut |ui| {
                                if p.proxy.trim().is_empty() {
                                    ui.label(RichText::new("● chưa có proxy").size(11.5).color(ORANGE));
                                } else {
                                    let st = proxy_status.get(p.proxy.as_str()).copied().unwrap_or("");
                                    let col = if st.is_empty() { MUTED } else { proxy_color(st) };
                                    ui.label(RichText::new("●").color(col));
                                    ui.label(RichText::new(truncate(&hide_proxy_pass(&p.proxy), 36)).size(11.5));
                                }
                            });
                            cell(ui, W[6], &mut |ui| {
                                let (t, col) = if nurturing {
                                    ("▶ Đang nuôi".to_string(), GREEN)
                                } else if open {
                                    ("● Đang mở".to_string(), CYAN)
                                } else if is_err(p) {
                                    (truncate(&p.status, 18), RED)
                                } else if p.status.is_empty() {
                                    ("Sẵn sàng".to_string(), MUTED)
                                } else {
                                    (truncate(&p.status, 18), MUTED)
                                };
                                ui.label(RichText::new(t).size(12.0).color(col)).on_hover_text(&p.status);
                            });
                            if open {
                                if ui.add(egui::Button::new("⏏").min_size(vec2(26.0, 20.0))).on_hover_text("Đóng profile").clicked() {
                                    http_post(&api, &format!("/api/browser/profiles/{}/stop", p.id), json!({ "id": p.id }), &format!("Đóng profile #{}", p.id));
                                }
                            } else if ui.add(egui::Button::new("🚀").min_size(vec2(26.0, 20.0))).on_hover_text("Mở profile").clicked() {
                                http_post(&api, &format!("/api/browser/profiles/{}/launch", p.id), json!({ "id": p.id }), &format!("Mở profile #{}", p.id));
                            }
                            if nurturing {
                                if ui.add(egui::Button::new("⏹").min_size(vec2(26.0, 20.0))).on_hover_text("Dừng nuôi").clicked() {
                                    http_post(&api, "/api/browser/nurture/stop", json!({ "profile_id": p.id }), &format!("Dừng nuôi #{}", p.id));
                                }
                            } else if ui.add(egui::Button::new("▶").min_size(vec2(26.0, 20.0))).on_hover_text("Nuôi profile này").clicked() {
                                http_post(&api, "/api/browser/nurture/start-selected", json!({ "profile_ids": [p.id], "auto_assign_c69_proxy": true }), &format!("Nuôi #{}", p.id));
                            }
                        });
                    });
                }
            });
        });

        // ── Phiên nuôi trên profile (OTP, log) ──
        if !sh.browser.is_empty() {
            ui.add_space(6.0);
            egui::ScrollArea::vertical().id_source("mun_sessions").max_height(sess_h).show(ui, |ui| {
                self.browser_tab(ui, sh);
            });
        }

        // ── Hộp thoại tạo profile ──
        if self.show_create {
            let mut open = true;
            let mut create = false;
            egui::Window::new("➕ Tạo profile mới").open(&mut open).collapsible(false).resizable(false).show(ui.ctx(), |ui| {
                egui::Grid::new("create_grid").num_columns(2).spacing([10.0, 8.0]).show(ui, |ui| {
                    ui.label("Tên:");
                    ui.add(egui::TextEdit::singleline(&mut self.new_name).hint_text("để trống = tự đặt").desired_width(280.0));
                    ui.end_row();
                    ui.label("Hệ điều hành:");
                    ui.horizontal(|ui| {
                        for (i, n) in ["Windows", "Android", "iOS"].iter().enumerate() {
                            ui.selectable_value(&mut self.new_os, i, *n);
                        }
                    });
                    ui.end_row();
                    ui.label("Proxy:");
                    ui.add(egui::TextEdit::singleline(&mut self.new_proxy).hint_text("socks5://user:pass@host:port").desired_width(280.0));
                    ui.end_row();
                    ui.label("Start URL:");
                    ui.add(egui::TextEdit::singleline(&mut self.new_url).hint_text("tuỳ chọn").desired_width(280.0));
                    ui.end_row();
                    ui.label("Số lượng:");
                    ui.add(egui::DragValue::new(&mut self.new_count).range(1..=50));
                    ui.end_row();
                });
                ui.add_space(6.0);
                if action_btn(ui, "➕ Tạo", Color32::from_rgb(5, 150, 105)).clicked() {
                    create = true;
                }
            });
            if create {
                let os = ["Windows", "Android", "iOS"][self.new_os.min(2)];
                let base = sh.profiles.iter().map(|p| p.id).max().unwrap_or(0) + 1;
                for i in 0..self.new_count.max(1) {
                    let name = if self.new_name.trim().is_empty() {
                        format!("Profile {}", base + i as u64)
                    } else if self.new_count > 1 {
                        format!("{} {}", self.new_name.trim(), i + 1)
                    } else {
                        self.new_name.trim().to_string()
                    };
                    http_post(
                        &api,
                        "/api/browser/profiles",
                        json!({ "name": name, "profile_os": os, "proxy_string": self.new_proxy.trim(), "profile_start_url": self.new_url.trim() }),
                        &format!("Tạo profile {}", name),
                    );
                }
                self.show_create = false;
            } else if !open {
                self.show_create = false;
            }
        }
    }
    fn proxy_tab(&mut self, ui: &mut egui::Ui, sh: &Shared) {
        let api = self.api_base.clone();
        let alive = sh.proxies.iter().filter(|p| proxy_color(&p.status) == GREEN).count();
        let dead: Vec<String> = sh.proxies.iter().filter(|p| proxy_color(&p.status) == RED).map(|p| p.proxy.clone()).collect();
        ui.horizontal_wrapped(|ui| {
            ui.label(RichText::new("🛡 Quản lý Proxy").size(16.0).strong().color(CYAN));
            pill(ui, "Tổng", &sh.proxies.len().to_string(), TEXT);
            pill(ui, "Sống", &alive.to_string(), GREEN);
            pill(ui, "Die", &dead.len().to_string(), if dead.is_empty() { MUTED } else { RED });
        });
        ui.add_space(4.0);

        section(ui, "🧰 Công cụ", |ui| {
            ui.horizontal_wrapped(|ui| {
                if action_btn(ui, "🧪 Test tất cả", Color32::from_rgb(2, 110, 170)).clicked() {
                    http_post(&api, "/api/browser/proxies/test-batch", json!({}), "Test toàn bộ proxy");
                }
                if ghost_btn(ui, &format!("🗑 Xóa proxy die ({})", dead.len())).clicked() && !dead.is_empty() {
                    http_post(&api, "/api/browser/proxies/remove-dead", json!({ "dead_proxies": dead }), "Xóa proxy die");
                }
                if ghost_btn(ui, "♻ Thay proxy die cho profile").clicked() {
                    http_post(&api, "/api/browser/proxies/auto-replace-dead", json!({}), "Thay proxy die");
                }
                if ghost_btn(ui, "🔀 Xoay IP router").clicked() {
                    http_post(&api, "/api/router/rotate", json!({}), "Xoay IP router");
                }
            });
            if !sh.router.is_empty() {
                ui.label(RichText::new(format!("Router: {}", sh.router)).size(11.0).color(MUTED));
            }
            ui.horizontal(|ui| {
                ui.add(egui::TextEdit::singleline(&mut self.proxy_test_one).hint_text("Test 1 proxy: socks5://user:pass@host:port").desired_width(380.0));
                if ghost_btn(ui, "🧪 Test").clicked() && !self.proxy_test_one.trim().is_empty() {
                    http_post(&api, "/api/browser/proxy/test", json!({ "proxy_string": self.proxy_test_one.trim() }), "Test proxy");
                }
            });
        });

        section(ui, "📥 Nhập proxy (mỗi dòng 1 proxy: host:port:user:pass hoặc socks5://...)", |ui| {
            ui.add(egui::TextEdit::multiline(&mut self.proxy_import).desired_rows(4).desired_width(f32::INFINITY));
            ui.horizontal(|ui| {
                ui.checkbox(&mut self.proxy_replace, "Thay thế toàn bộ (thay vì thêm vào)");
                if action_btn(ui, "📥 Nhập", Color32::from_rgb(5, 150, 105)).clicked() && !self.proxy_import.trim().is_empty() {
                    http_post(
                        &api,
                        "/api/browser/proxies/import",
                        json!({ "proxies_text": self.proxy_import, "mode": if self.proxy_replace { "replace" } else { "append" } }),
                        "Nhập proxy",
                    );
                    self.proxy_import.clear();
                }
            });
        });

        ui.add_space(6.0);
        egui::Frame::none().fill(PANEL).stroke(Stroke::new(1.0_f32, BORDER)).rounding(Rounding::same(8.0)).inner_margin(10.0).show(ui, |ui| {
            if sh.proxies.is_empty() {
                ui.label(RichText::new("Kho proxy trống. Nhập proxy ở trên.").color(MUTED));
                return;
            }
            egui::Grid::new("proxy_grid").striped(true).num_columns(4).spacing([18.0, 6.0]).show(ui, |ui| {
                for h in ["#", "Proxy", "Trạng thái", "Độ trễ"] {
                    ui.label(RichText::new(h).strong().color(CYAN));
                }
                ui.end_row();
                for (i, p) in sh.proxies.iter().enumerate() {
                    ui.label((i + 1).to_string());
                    ui.label(hide_proxy_pass(&p.proxy));
                    ui.label(RichText::new(if p.status.is_empty() { "chưa test" } else { &p.status }).color(proxy_color(&p.status)));
                    ui.label(RichText::new(&p.latency).color(MUTED));
                    ui.end_row();
                }
            });
        });
    }
}
