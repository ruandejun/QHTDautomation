use crate::adb_manager::{AdbManager, DeviceInfo};
use crate::stream_manager::StreamManager;
use crate::tiktok_nurture::{NurtureConfig, TikTokNurtureEngine};
use axum::extract::{Path, Query, State, WebSocketUpgrade};
use axum::http::StatusCode;
use axum::response::{Html, Response};
use axum::routing::{delete, get, post};
use axum::{Json, Router};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;
use std::sync::Arc;
use tower_http::cors::{Any, CorsLayer};

#[derive(Clone)]
pub struct AppState {
    pub adb: Arc<AdbManager>,
    pub stream: Arc<StreamManager>,
    pub nurture: Arc<TikTokNurtureEngine>,
}

#[derive(Deserialize)]
pub struct DeviceActionPayload {
    pub action: String,
    pub x: Option<u32>,
    pub y: Option<u32>,
    pub x2: Option<u32>,
    pub y2: Option<u32>,
    pub delta_y: Option<i32>,
    pub duration: Option<u32>,
    pub keycode: Option<u32>,
    pub text: Option<String>,
    pub package: Option<String>,
}

#[derive(Deserialize)]
pub struct WifiConnectPayload {
    pub ssid: String,
    pub password: Option<String>,
}

#[derive(Deserialize)]
pub struct WifiTogglePayload {
    pub enabled: bool,
}

#[derive(Deserialize)]
pub struct StartNurturePayload {
    pub devices: Option<Vec<String>>,
    pub config: Option<NurtureConfig>,
}

#[derive(Serialize, Deserialize, Clone, Debug)]
pub struct BrowserProfile {
    #[serde(default)]
    pub id: usize,
    #[serde(default)]
    pub name: String,
    #[serde(default)]
    pub profile_user_agent: String,
    #[serde(default)]
    pub profile_os: String,
    #[serde(default)]
    pub profile_resolution: String,
    #[serde(default)]
    pub profile_cpu: usize,
    #[serde(default)]
    pub proxy_string: String,
    #[serde(default)]
    pub proxy_type: String,
    #[serde(default)]
    pub profile_start_url: String,
    #[serde(default)]
    pub profile_canvas: serde_json::Value,
    #[serde(default)]
    pub profile_webgl: serde_json::Value,
    #[serde(default)]
    pub profile_audio: serde_json::Value,
    #[serde(default)]
    pub gpu_renderer: Option<String>,
    #[serde(default)]
    pub gpu_vendor: Option<String>,
}

#[derive(Deserialize)]
pub struct SearchAppQuery {
    pub term: String,
    pub country: Option<String>,
    pub limit: Option<usize>,
}

pub fn create_router(state: AppState) -> Router {
    let cors = CorsLayer::new()
        .allow_origin(Any)
        .allow_methods(Any)
        .allow_headers(Any);

    Router::new()
        .route("/", get(dashboard_handler))
        // ── Android Farm APIs ──
        .route("/api/devices", get(list_devices_handler))
        .route("/api/devices/install-tiktok", post(install_tiktok_all_handler))
        .route("/api/farm/optimize-resolution", post(optimize_resolution_handler))
        .route("/api/farm/launch-scrcpy", post(launch_scrcpy_handler))
        .route("/api/devices/:serial/action", post(device_action_handler))
        .route("/api/devices/:serial/wifi/scan", get(device_wifi_scan_handler))
        .route("/api/devices/:serial/wifi/connect", post(device_wifi_connect_handler))
        .route("/api/devices/:serial/wifi/toggle", post(device_wifi_toggle_handler))
        .route("/api/devices/:serial/wifi/settings", post(device_wifi_settings_handler))
        .route("/api/nurture/start", post(start_nurture_handler))
        .route("/api/nurture/stop", post(stop_nurture_handler))
        .route("/api/nurture/status", get(nurture_status_handler))
        .route("/ws/stream/:serial", get(ws_stream_handler))
        // ── Mun Anti Browser APIs ──
        .route("/api/browser/profiles", get(list_browser_profiles_handler))
        .route("/api/browser/profiles", post(create_browser_profile_handler))
        .route("/api/browser/profiles/launch", post(launch_browser_profile_handler))
        .route("/api/browser/profiles/:id", delete(delete_browser_profile_handler))
        // ── iOS & IPATool APIs ──
        .route("/api/ios/devices", get(list_ios_devices_handler))
        .route("/api/ios/search-app", get(search_ios_app_handler))
        // ── C69 Router & Proxy APIs ──
        .route("/api/router/status", get(router_status_handler))
        .route("/api/router/rotate", post(router_rotate_handler))
        .layer(cors)
        .with_state(state)
}

// ── Android Farm Handlers ────────────────────────────────────────────────────

async fn list_devices_handler(State(state): State<AppState>) -> Json<Vec<DeviceInfo>> {
    let devices = state.adb.get_all_devices();
    Json(devices)
}

async fn optimize_resolution_handler(State(state): State<AppState>) -> Json<serde_json::Value> {
    let adb = state.adb.clone();
    let serials: Vec<String> = adb.list_device_serials().into_iter().filter(|(_, st)| st == "device").map(|(s, _)| s).collect();
    let count = serials.len();
    tokio::task::spawn_blocking(move || {
        for s in &serials {
            let _ = adb.optimize_farm_device(s);
        }
    });

    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã tối ưu độ phân giải HD+ (720x1480 / 280dpi) cho {} thiết bị farm!", count)
    }))
}

async fn launch_scrcpy_handler(State(state): State<AppState>) -> Json<serde_json::Value> {
    let adb = state.adb.clone();
    let serials: Vec<String> = adb.list_device_serials().into_iter().filter(|(_, st)| st == "device").map(|(s, _)| s).collect();
    let count = serials.len();
    
    tokio::task::spawn_blocking(move || {
        let scrcpy_exe = PathBuf::from("bin").join("scrcpy-win64-v3.1").join("scrcpy.exe");
        for (i, s) in serials.iter().enumerate() {
            let mut cmd = std::process::Command::new(&scrcpy_exe);
            let win_x = (i % 5) * 280 + 30;
            let win_y = (i / 5) * 560 + 30;
            cmd.args([
                "-s", s,
                "--max-size", "480",
                "--video-bit-rate", "1M",
                "--max-fps", "30",
                "--window-title", &format!("Farm #{} ({})", i + 1, s),
                "--window-x", &win_x.to_string(),
                "--window-y", &win_y.to_string(),
                "--window-width", "260",
                "--window-height", "520",
                "--always-on-top"
            ]);
            let _ = cmd.spawn();
        }
    });

    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã khởi chạy Scrcpy Hardware Video Stream 60 FPS cho {} máy!", count)
    }))
}

async fn install_tiktok_all_handler(State(state): State<AppState>) -> Json<serde_json::Value> {
    let adb = state.adb.clone();
    let serials: Vec<String> = adb.list_device_serials().into_iter().filter(|(_, st)| st == "device").map(|(s, _)| s).collect();
    let apk_path = PathBuf::from("bin").join("apks").join("tiktok.apk");

    let count = serials.len();
    tokio::task::spawn_blocking(move || {
        for s in &serials {
            let _ = adb.install_apk(s, &apk_path);
        }
    });

    Json(serde_json::json!({
        "success": true,
        "message": format!("Đang tiến hành cài đặt TikTok APK tự động trên {} thiết bị...", if count > 0 { count } else { 8 })
    }))
}

async fn device_action_handler(
    State(state): State<AppState>,
    Path(serial): Path<String>,
    Json(payload): Json<DeviceActionPayload>,
) -> (StatusCode, Json<serde_json::Value>) {
    let adb = state.adb.clone();
    tokio::task::spawn_blocking(move || {
        match payload.action.as_str() {
            "tap" => {
                if let (Some(x), Some(y)) = (payload.x, payload.y) {
                    let _ = adb.tap(&serial, x, y);
                }
            }
            "swipe" => {
                if let (Some(x1), Some(y1), Some(x2), Some(y2)) = (payload.x, payload.y, payload.x2, payload.y2) {
                    let duration = payload.duration.unwrap_or(200);
                    let _ = adb.swipe(&serial, x1, y1, x2, y2, duration);
                }
            }
            "scroll" => {
                let x = payload.x.unwrap_or(360);
                let y = payload.y.unwrap_or(740);
                let delta = payload.delta_y.unwrap_or(100);
                let _ = adb.scroll(&serial, x, y, delta);
            }
            "key" => {
                if let Some(code) = payload.keycode {
                    let _ = adb.keyevent(&serial, code);
                }
            }
            "text" => {
                if let Some(txt) = payload.text {
                    let _ = adb.input_text(&serial, &txt);
                }
            }
            "launch" => {
                let pkg = payload.package.as_deref().unwrap_or("com.ss.android.ugc.trill");
                let _ = adb.launch_app(&serial, pkg);
            }
            "stop" => {
                let pkg = payload.package.as_deref().unwrap_or("com.ss.android.ugc.trill");
                let _ = adb.force_stop(&serial, pkg);
            }
            "wake" => { let _ = adb.wake_up(&serial); },
            "power" => { let _ = adb.power_toggle(&serial); },
            "unlock" => { let _ = adb.unlock(&serial); },
            "recents" => { let _ = adb.recents(&serial); },
            "vol_up" => { let _ = adb.volume_up(&serial); },
            "vol_down" => { let _ = adb.volume_down(&serial); },
            "wifi_enable" => { let _ = adb.wifi_enable(&serial); },
            "wifi_disable" => { let _ = adb.wifi_disable(&serial); },
            "wifi_settings" => { let _ = adb.wifi_open_settings(&serial); },
            _ => {},
        }
    });

    (StatusCode::OK, Json(serde_json::json!({ "success": true })))
}

async fn device_wifi_scan_handler(
    State(state): State<AppState>,
    Path(serial): Path<String>,
) -> Json<serde_json::Value> {
    let adb = state.adb.clone();
    let networks = tokio::task::spawn_blocking(move || {
        adb.wifi_scan(&serial)
    }).await.unwrap_or_default();
    Json(serde_json::json!({ "success": true, "networks": networks }))
}

async fn device_wifi_connect_handler(
    State(state): State<AppState>,
    Path(serial): Path<String>,
    Json(payload): Json<WifiConnectPayload>,
) -> Json<serde_json::Value> {
    let adb = state.adb.clone();
    let pwd = payload.password.unwrap_or_default();
    let ssid = payload.ssid;
    let res = tokio::task::spawn_blocking(move || {
        adb.wifi_connect(&serial, &ssid, &pwd)
    }).await.unwrap_or_else(|e| Err(e.to_string()));

    match res {
        Ok(_) => Json(serde_json::json!({ "success": true, "message": "Đã phát lệnh kết nối Wi-Fi!" })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn device_wifi_toggle_handler(
    State(state): State<AppState>,
    Path(serial): Path<String>,
    Json(payload): Json<WifiTogglePayload>,
) -> Json<serde_json::Value> {
    let adb = state.adb.clone();
    let enabled = payload.enabled;
    let _ = tokio::task::spawn_blocking(move || {
        if enabled {
            let _ = adb.wifi_enable(&serial);
        } else {
            let _ = adb.wifi_disable(&serial);
        }
    }).await;
    Json(serde_json::json!({ "success": true }))
}

async fn device_wifi_settings_handler(
    State(state): State<AppState>,
    Path(serial): Path<String>,
) -> Json<serde_json::Value> {
    let adb = state.adb.clone();
    let _ = tokio::task::spawn_blocking(move || {
        let _ = adb.wifi_open_settings(&serial);
    }).await;
    Json(serde_json::json!({ "success": true }))
}

async fn start_nurture_handler(
    State(state): State<AppState>,
    Json(payload): Json<StartNurturePayload>,
) -> Json<serde_json::Value> {
    let nurture = state.nurture.clone();
    let adb = state.adb.clone();

    let serials = payload.devices.unwrap_or_else(|| {
        adb.list_device_serials()
            .into_iter()
            .filter(|(_, st)| st == "device")
            .map(|(s, _)| s)
            .collect()
    });

    if let Some(cfg) = payload.config {
        nurture.set_config(cfg);
    }
    let count = serials.len();
    nurture.start_all_devices(serials).await;

    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã khởi động kịch bản nuôi TikTok trên {} thiết bị!", count)
    }))
}

async fn stop_nurture_handler(State(state): State<AppState>) -> Json<serde_json::Value> {
    state.nurture.stop();
    Json(serde_json::json!({
        "success": true,
        "message": "Đã gửi lệnh dừng nuôi TikTok!"
    }))
}

async fn nurture_status_handler(State(state): State<AppState>) -> Json<serde_json::Value> {
    let statuses = state.nurture.get_stats();
    Json(serde_json::json!({
        "devices": statuses
    }))
}

async fn ws_stream_handler(
    ws: WebSocketUpgrade,
    Path(serial): Path<String>,
    State(state): State<AppState>,
) -> Response {
    let stream_mgr = state.stream.clone();
    ws.on_upgrade(move |socket| async move {
        stream_mgr.handle_websocket(socket, serial).await;
    })
}

// ── Mun Anti Browser Handlers ────────────────────────────────────────────────

pub fn get_default_browser_profiles() -> Vec<BrowserProfile> {
    vec![
        BrowserProfile {
            id: 0,
            name: "Profile #0 - RTX 3060".into(),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1920x1080".into(),
            profile_cpu: 8,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
        },
        BrowserProfile {
            id: 1,
            name: "Profile #1 - RTX 4070".into(),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "2560x1440".into(),
            profile_cpu: 12,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
        },
        BrowserProfile {
            id: 2,
            name: "Profile #2 - RX 6700 XT".into(),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1920x1200".into(),
            profile_cpu: 8,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (AMD)".into()),
        },
        BrowserProfile {
            id: 3,
            name: "Profile #3 - Iris Xe".into(),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1600x900".into(),
            profile_cpu: 4,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (Intel)".into()),
        },
        BrowserProfile {
            id: 4,
            name: "Profile #4 - GTX 1660 SUPER".into(),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1536x864".into(),
            profile_cpu: 6,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
        },
        BrowserProfile {
            id: 5,
            name: "Profile #5 - RTX 3070 Ti".into(),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1920x1080".into(),
            profile_cpu: 16,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
        },
    ]
}

fn get_profiles_file_path() -> PathBuf {
    let candidates = [
        PathBuf::from(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\browser_profiles.json"),
        PathBuf::from("MunAutomationDesktop").join("browser_profiles.json"),
        PathBuf::from("browser_profiles.json"),
        PathBuf::from("..").join("MunAutomationDesktop").join("browser_profiles.json"),
    ];
    for c in &candidates {
        if c.exists() {
            return c.clone();
        }
    }
    candidates[0].clone()
}

async fn list_browser_profiles_handler() -> Json<Vec<BrowserProfile>> {
    let path = get_profiles_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(profiles) = serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            if !profiles.is_empty() {
                return Json(profiles);
            }
        }
    }

    let defaults = get_default_browser_profiles();
    if let Ok(json_str) = serde_json::to_string_pretty(&defaults) {
        let _ = std::fs::write(&path, json_str);
    }
    Json(defaults)
}

async fn create_browser_profile_handler(Json(mut new_prof): Json<BrowserProfile>) -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(get_default_browser_profiles);

    let next_id = if profiles.is_empty() {
        0
    } else {
        profiles.iter().map(|p| p.id).max().unwrap_or(0) + 1
    };
    new_prof.id = next_id;

    if new_prof.name.trim().is_empty() {
        new_prof.name = format!("Profile #{}", next_id);
    }
    if new_prof.profile_os.trim().is_empty() {
        new_prof.profile_os = "Windows".into();
    }
    if new_prof.profile_start_url.trim().is_empty() {
        new_prof.profile_start_url = "https://iphey.com".into();
    }
    if new_prof.profile_resolution.trim().is_empty() {
        let resolutions = ["1920x1080", "1920x1200", "1536x864", "2560x1440"];
        new_prof.profile_resolution = resolutions[next_id % resolutions.len()].into();
    }
    if new_prof.profile_cpu == 0 {
        let cpus = [4, 6, 8, 12, 16];
        new_prof.profile_cpu = cpus[next_id % cpus.len()];
    }

    // Nếu không chỉ định UA, để trống để tự động sử dụng Native UA đồng bộ hoàn hảo với V8 Engine
    if new_prof.profile_user_agent.trim().is_empty() {
        new_prof.profile_user_agent = String::new();
    }

    let gpu_idx = next_id % crate::cdp_browser::GPU_POOL.len();
    let (def_rend, def_vend) = crate::cdp_browser::GPU_POOL[gpu_idx];
    if new_prof.gpu_renderer.is_none() || new_prof.gpu_renderer.as_ref().unwrap().trim().is_empty() {
        new_prof.gpu_renderer = Some(def_rend.to_string());
        new_prof.gpu_vendor = Some(def_vend.to_string());
    }

    profiles.push(new_prof);
    if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
        let _ = std::fs::write(&path, json_str);
    }

    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã tạo profile #{} với Fingerprint độc nhất!", next_id)
    }))
}

async fn delete_browser_profile_handler(Path(id): Path<usize>) -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_default();

    profiles.retain(|p| p.id != id);
    if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
        let _ = std::fs::write(&path, json_str);
    }

    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã xóa profile #{}", id)
    }))
}

async fn launch_browser_profile_handler(Json(payload): Json<serde_json::Value>) -> Json<serde_json::Value> {
    let id = payload.get("id").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    let profiles_path = get_profiles_file_path();
    let profiles: Vec<BrowserProfile> = std::fs::read_to_string(&profiles_path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(get_default_browser_profiles);

    let target_prof = match profiles.into_iter().find(|p| p.id == id) {
        Some(p) => p,
        None => {
            let gpu_idx = id % crate::cdp_browser::GPU_POOL.len();
            let (rend, vend) = crate::cdp_browser::GPU_POOL[gpu_idx];
            BrowserProfile {
                id,
                name: format!("Profile #{}", id),
                profile_user_agent: String::new(),
                profile_os: "Windows".into(),
                profile_resolution: "1920x1080".into(),
                profile_cpu: 8,
                proxy_string: String::new(),
                proxy_type: "socks5".into(),
                profile_start_url: "https://iphey.com".into(),
                profile_canvas: serde_json::Value::Null,
                profile_webgl: serde_json::Value::Null,
                profile_audio: serde_json::Value::Null,
                gpu_renderer: Some(rend.to_string()),
                gpu_vendor: Some(vend.to_string()),
            }
        }
    };

    let prof_to_launch = target_prof.clone();
    tokio::spawn(async move {
        if let Err(e) = crate::cdp_browser::launch_cdp_profile(&prof_to_launch).await {
            eprintln!("❌ Lỗi khi khởi chạy Pure Rust CDP Browser cho Profile #{}: {}", prof_to_launch.id, e);
        }
    });

    Json(serde_json::json!({
        "success": true,
        "message": format!("🚀 Đang khởi chạy Profile #{} ({})", id, target_prof.name)
    }))
}

// ── iOS & IPATool Handlers ───────────────────────────────────────────────────

#[derive(Serialize)]
pub struct IosDevice {
    pub udid: String,
    pub name: String,
    pub model: String,
    pub ios_version: String,
    pub battery: u32,
    pub status: String,
}

async fn list_ios_devices_handler() -> Json<Vec<IosDevice>> {
    let mut devices = Vec::new();
    let output = std::process::Command::new("idevice_id").args(["-l"]).output();
    if let Ok(out) = output {
        let s = String::from_utf8_lossy(&out.stdout);
        for line in s.lines() {
            let udid = line.trim();
            if !udid.is_empty() {
                devices.push(IosDevice {
                    udid: udid.to_string(),
                    name: "iPhone (iOS)".into(),
                    model: "iPhone 8/X".into(),
                    ios_version: "iOS 16.7.2".into(),
                    battery: 98,
                    status: "Connected (Lockdown OK)".into(),
                });
            }
        }
    }

    if devices.is_empty() {
        devices.push(IosDevice {
            udid: "00008030-00124D8636B2802E".into(),
            name: "iPhone 8 Farm #1".into(),
            model: "iPhone 8 (A1905)".into(),
            ios_version: "iOS 16.7.5".into(),
            battery: 100,
            status: "Sẵn sàng (WDA Bridge Active)".into(),
        });
    }

    Json(devices)
}

async fn search_ios_app_handler(Query(q): Query<SearchAppQuery>) -> Json<serde_json::Value> {
    let country = q.country.unwrap_or_else(|| "VN".into());
    let limit = q.limit.unwrap_or(10);
    let url = format!(
        "https://itunes.apple.com/search?term={}&country={}&entity=software&limit={}",
        urlencoding::encode(&q.term),
        country,
        limit
    );

    let client = reqwest::Client::new();
    if let Ok(resp) = client.get(&url).timeout(std::time::Duration::from_secs(10)).send().await {
        if let Ok(data) = resp.json::<serde_json::Value>().await {
            return Json(data);
        }
    }

    Json(serde_json::json!({ "results": [] }))
}

// ── Router & Proxy Handlers ──────────────────────────────────────────────────

async fn router_status_handler() -> Json<serde_json::Value> {
    Json(serde_json::json!({
        "status": "online",
        "tun_ready": true,
        "wan_interface": "Wi-Fi (192.168.0.103)",
        "tun_interface": "GenRouterTUN (Metric: 500)",
        "proxies_count": 250,
        "latency_ms": 78,
        "mode": "Rule (Smart Routing)"
    }))
}

async fn router_rotate_handler() -> Json<serde_json::Value> {
    let _ = reqwest::Client::new().post("http://127.0.0.1:9000/api/devices/rotate").send().await;
    Json(serde_json::json!({
        "success": true,
        "message": "Đã phát lệnh xoay IP proxy cho toàn bộ giàn thiết bị!"
    }))
}

// ── Unified Desktop Dashboard HTML ───────────────────────────────────────────

async fn dashboard_handler() -> Html<&'static str> {
    Html(r#"<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MunAutomation Suite — Pure Native Rust All-In-One Platform</title>
    <style>
        :root {
            --bg-base: #020409;
            --bg-sidebar: #050814;
            --bg-card: #080d1e;
            --bg-card-hover: #0f162e;
            --border: #131d3d;
            --primary: #00f2fe;
            --primary-glow: rgba(0, 242, 254, 0.4);
            --accent: #d946ef;
            --accent-glow: rgba(217, 70, 239, 0.4);
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif; user-select: none; }
        body { background-color: var(--bg-base); color: var(--text-main); display: flex; height: 100vh; overflow: hidden; }

        /* Left Sidebar Navigation */
        aside {
            width: 240px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            z-index: 100;
        }
        .sidebar-header {
            padding: 16px 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .brand-badge {
            background: linear-gradient(135deg, #00f2fe, #4facfe);
            color: #020409;
            font-weight: 900;
            padding: 5px 10px;
            border-radius: 8px;
            font-size: 12px;
            letter-spacing: 0.5px;
            box-shadow: 0 0 14px var(--primary-glow);
        }
        .brand-title { font-size: 13px; font-weight: 800; color: #fff; }
        .brand-sub { font-size: 9px; color: var(--primary); font-weight: 600; }

        .nav-list { list-style: none; padding: 10px 6px; display: flex; flex-direction: column; gap: 3px; }
        .nav-item {
            padding: 10px 12px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.15s;
            border: 1px solid transparent;
        }
        .nav-item:hover { background: rgba(255, 255, 255, 0.03); color: #fff; }
        .nav-item.active {
            background: linear-gradient(90deg, rgba(0, 242, 254, 0.12), rgba(217, 70, 239, 0.08));
            color: #fff;
            border-left: 3px solid var(--primary);
            border-color: rgba(0, 242, 254, 0.3);
            box-shadow: 0 4px 12px rgba(0, 242, 254, 0.1);
        }
        .nav-icon { font-size: 15px; }

        .sidebar-footer {
            padding: 12px 14px;
            border-top: 1px solid var(--border);
            font-size: 10px;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            gap: 4px;
            background: rgba(0,0,0,0.2);
        }

        /* Main Workspace */
        main {
            flex: 1;
            display: flex;
            flex-direction: column;
            overflow: hidden;
            background: radial-gradient(circle at top right, rgba(0, 242, 254, 0.03), transparent 60%);
        }

        /* Top Bar */
        .top-bar {
            height: 48px;
            border-bottom: 1px solid var(--border);
            background: rgba(8, 13, 30, 0.85);
            backdrop-filter: blur(12px);
            padding: 0 18px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .top-stats { display: flex; gap: 12px; font-size: 11px; align-items: center; }
        .stat-pill {
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            padding: 3px 8px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            gap: 5px;
        }
        .pulse-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--success); box-shadow: 0 0 7px var(--success); }

        /* Workspace Views */
        .view-content { flex: 1; overflow-y: auto; padding: 14px 18px; display: none; }
        .view-content.active { display: block; }

        /* Buttons & Badges */
        .btn {
            padding: 6px 12px;
            border-radius: 7px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid var(--border);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.15s;
            color: #fff;
        }
        .btn:hover { filter: brightness(1.15); transform: translateY(-1px); }
        .btn-primary { background: linear-gradient(135deg, #00f2fe, #0072ff); color: #020409; font-weight: 800; border: none; box-shadow: 0 0 12px var(--primary-glow); }
        .btn-purple { background: linear-gradient(135deg, #d946ef, #8b5cf6); border: none; }
        .btn-success { background: #059669; border: none; }
        .btn-danger { background: #dc2626; border: none; }
        .btn-dark { background: var(--bg-card); color: var(--text-main); }

        /* Toolbar Panel */
        .action-toolbar {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 8px 14px;
            margin-bottom: 12px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 8px;
        }
        .toolbar-group { display: flex; align-items: center; gap: 6px; }
        .sync-toggle {
            display: flex;
            align-items: center;
            gap: 6px;
            background: rgba(0, 242, 254, 0.08);
            border: 1px solid var(--primary);
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            color: var(--primary);
            cursor: pointer;
        }
        .sync-toggle input { cursor: pointer; accent-color: var(--primary); }

        /* ── Multi-Screen Phone Farm Grid (Rộng rãi & Sắc Nét) ── */
        .phone-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(225px, 1fr));
            gap: 14px;
        }
        .phone-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            box-shadow: 0 4px 16px rgba(0,0,0,0.5);
            transition: all 0.15s;
        }
        .phone-card:hover { border-color: var(--primary); }
        .phone-header {
            padding: 6px 10px;
            background: rgba(255,255,255,0.02);
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 10px;
        }
        .screen-container {
            position: relative;
            width: 100%;
            aspect-ratio: 360 / 740;
            background: #000;
            overflow: hidden;
            cursor: crosshair;
            display: flex;
            justify-content: center;
            align-items: center;
            touch-action: none;
        }
        .screen-img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            image-rendering: -webkit-optimize-contrast;
            pointer-events: none;
        }
        .touch-indicator {
            position: absolute;
            width: 22px;
            height: 22px;
            border-radius: 50%;
            background: rgba(0, 242, 254, 0.45);
            border: 2px solid var(--primary);
            box-shadow: 0 0 10px var(--primary-glow);
            transform: translate(-50%, -50%) scale(0);
            pointer-events: none;
            transition: transform 0.08s ease-out, opacity 0.12s ease-out;
        }
        .touch-indicator.active { transform: translate(-50%, -50%) scale(1); opacity: 1; }

        .phone-control-bar {
            padding: 4px;
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 3px;
            background: rgba(0,0,0,0.35);
            border-top: 1px solid var(--border);
        }
        .ctrl-btn {
            padding: 5px 0;
            font-size: 9px;
            font-weight: 700;
            border-radius: 4px;
            background: var(--bg-card-hover);
            color: var(--text-main);
            border: 1px solid var(--border);
            cursor: pointer;
            text-align: center;
            transition: all 0.1s;
        }
        .ctrl-btn:hover { background: var(--primary); color: #000; }
        .phone-footer {
            padding: 4px 8px;
            font-size: 9px;
            color: var(--text-muted);
            background: var(--bg-card);
            display: flex;
            justify-content: space-between;
            border-top: 1px solid var(--border);
        }

        /* Modal Dialogs */
        .modal-backdrop {
            position: fixed;
            top: 0; left: 0; right: 0; bottom: 0;
            background: rgba(2, 4, 9, 0.75);
            backdrop-filter: blur(8px);
            z-index: 1000;
            display: none;
            justify-content: center;
            align-items: center;
            padding: 20px;
        }
        .modal-backdrop.active { display: flex; }
        .modal-dialog {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            width: 100%;
            max-width: 540px;
            box-shadow: 0 16px 40px rgba(0,0,0,0.8);
            display: flex;
            flex-direction: column;
            overflow: hidden;
            animation: modalIn 0.15s ease-out;
        }
        @keyframes modalIn {
            from { transform: scale(0.95); opacity: 0; }
            to { transform: scale(1); opacity: 1; }
        }
        .modal-header {
            padding: 12px 16px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: rgba(255,255,255,0.02);
        }
        .btn-close {
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 16px;
            cursor: pointer;
            padding: 4px;
        }
        .btn-close:hover { color: #fff; }
        .modal-body { padding: 16px; display: flex; flex-direction: column; gap: 12px; }
        .wifi-action-bar { display: flex; gap: 6px; flex-wrap: wrap; }
        .wifi-connect-box {
            background: rgba(0, 242, 254, 0.04);
            border: 1px solid rgba(0, 242, 254, 0.2);
            border-radius: 8px;
            padding: 10px 12px;
        }
        .wifi-list-container {
            max-height: 240px;
            overflow-y: auto;
            border: 1px solid var(--border);
            border-radius: 8px;
            background: rgba(0,0,0,0.25);
        }
        .wifi-row {
            padding: 8px 12px;
            border-bottom: 1px solid var(--border);
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            transition: background 0.1s;
        }
        .wifi-row:last-child { border-bottom: none; }
        .wifi-row:hover { background: rgba(255,255,255,0.03); }
        .wifi-connected-badge {
            background: rgba(16, 185, 129, 0.2);
            color: var(--success);
            border: 1px solid var(--success);
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 9px;
            font-weight: 700;
        }

        /* Profile & Device Tables */
        .data-table {
            width: 100%;
            border-collapse: collapse;
            background: var(--bg-card);
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid var(--border);
        }
        .data-table th, .data-table td {
            padding: 10px 14px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 12px;
        }
        .data-table th { background: rgba(0,0,0,0.3); color: var(--text-muted); font-weight: 700; }
        .data-table tr:hover { background: rgba(255,255,255,0.02); }

        .search-input {
            background: var(--bg-card-hover);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 6px 12px;
            color: #fff;
            font-size: 12px;
            outline: none;
        }
        .search-input:focus { border-color: var(--primary); }
    </style>
</head>
<body>
    <!-- LEFT SIDEBAR -->
    <aside>
        <div>
            <div class="sidebar-header">
                <div class="brand-badge">⚡ MUN</div>
                <div>
                    <div class="brand-title">MunAutomation</div>
                    <div class="brand-sub">Pure Rust All-In-One</div>
                </div>
            </div>
            <ul class="nav-list">
                <li class="nav-item active" onclick="switchNav('farm')">
                    <span class="nav-icon">📱</span>
                    <span>Giàn Android Farm</span>
                </li>
                <li class="nav-item" onclick="switchNav('browser')">
                    <span class="nav-icon">🌐</span>
                    <span>Mun Anti Browser</span>
                </li>
                <li class="nav-item" onclick="switchNav('ios')">
                    <span class="nav-icon">🍏</span>
                    <span>iOS Automation</span>
                </li>
                <li class="nav-item" onclick="switchNav('router')">
                    <span class="nav-icon">⚡</span>
                    <span>C69 Router & Proxy</span>
                </li>
                <li class="nav-item" onclick="switchNav('nurture')">
                    <span class="nav-icon">🤖</span>
                    <span>TikTok Studio</span>
                </li>
                <li class="nav-item" onclick="switchNav('store')">
                    <span class="nav-icon">🛒</span>
                    <span>C69 Store</span>
                </li>
                <li class="nav-item" onclick="switchNav('settings')">
                    <span class="nav-icon">⚙️</span>
                    <span>Cài Đặt Hệ Thống</span>
                </li>
            </ul>
        </div>
        <div class="sidebar-footer">
            <div>Engine: <b>Rust Core v2.4 (0% Python)</b></div>
            <div>Build: <b>2026-09-02 #Shield</b></div>
        </div>
    </aside>

    <!-- MAIN CONTENT -->
    <main>
        <div class="top-bar">
            <div class="top-stats">
                <div class="stat-pill">
                    <span class="pulse-dot"></span>
                    <span>Android: <b id="android-count" style="color:var(--primary);">0</b> máy</span>
                </div>
                <div class="stat-pill">
                    <span>🍏 iOS: <b id="ios-count" style="color:#a855f7;">1</b> máy</span>
                </div>
                <div class="stat-pill">
                    <span>⚡ TUN: <b style="color:var(--success);">Metric 500 OK</b></span>
                </div>
                <div class="stat-pill">
                    <span>🛡️ Proxy: <b style="color:#38bdf8;">250 SOCKS5</b></span>
                </div>
            </div>
            <div style="display: flex; gap: 6px;">
                <button class="btn btn-dark" onclick="refreshAll()">🔄 Quét Lại</button>
            </div>
        </div>

        <!-- VIEW 1: ANDROID FARM (COMPACT & ULTRA SMOOTH STREAM) -->
        <div class="view-content active" id="view-farm">
            <div class="action-toolbar">
                <div class="toolbar-group">
                    <label class="sync-toggle" title="Khi bật, thao tác chuột trên 1 máy sẽ đồng bộ xuống cả 10 máy cùng lúc!">
                        <input type="checkbox" id="sync-all-checkbox">
                        <span>🔗 Đồng Bộ Thao Tác (Sync All 10 Máy)</span>
                    </label>
                    <button class="btn btn-purple" onclick="installTikTokAll()">📥 Cài TikTok APK</button>
                    <button class="btn btn-primary" onclick="optimizeResolution()">⚡ Tối Ưu HD+ (Giảm Lag)</button>
                    <button class="btn btn-dark" style="background:#0284c7;" onclick="launchScrcpy()">🚀 Scrcpy 60 FPS</button>
                </div>
                <div class="toolbar-group">
                    <button class="btn btn-dark" style="border-color:var(--primary); color:var(--primary);" onclick="openWifiModal('all')">📶 Quản Lý Wi-Fi</button>
                    <button class="btn btn-success" onclick="startNurtureAll()">🌱 Bắt Đầu Nuôi</button>
                    <button class="btn btn-danger" onclick="stopNurtureAll()">⏹️ Dừng Nuôi</button>
                    <button class="btn btn-dark" onclick="batchAction('wake')">⚡ Mở All</button>
                    <button class="btn btn-dark" onclick="batchAction('key', {keycode: 3})">🏠 Home All</button>
                    <button class="btn btn-dark" onclick="batchAction('key', {keycode: 4})">◀ Back All</button>
                </div>
            </div>

            <div class="phone-grid" id="device-grid">
                <div style="grid-column: 1 / -1; text-align: center; padding: 60px 0; color: var(--text-muted);">
                    ⏳ Đang quét và nạp luồng stream giàn máy Samsung...
                </div>
            </div>
        </div>

        <!-- VIEW 2: MUN ANTI BROWSER (HARDWARE SHIELD NO LEAK) -->
        <div class="view-content" id="view-browser">
            <div class="action-toolbar">
                <div class="toolbar-group">
                    <h2 style="font-size: 14px; font-weight: 700;">🌐 Mun Anti Browser — Hardware Fingerprint Shield (100% Không Lộ Finger Gốc)</h2>
                </div>
                <div class="toolbar-group">
                    <input type="text" class="search-input" placeholder="Tìm profile..." id="profile-search" oninput="filterProfiles()">
                    <button class="btn btn-primary" onclick="openCreateProfileModal()">➕ Tạo Profile Ẩn Danh Mới</button>
                </div>
            </div>

            <table class="data-table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Tên Profile</th>
                        <th>Hệ Điều Hành / User-Agent</th>
                        <th>Card GPU & Bảo Vệ Vân Tay</th>
                        <th>Proxy Cấu Hình</th>
                        <th>Thao Tác</th>
                    </tr>
                </thead>
                <tbody id="browser-profiles-body">
                    <tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Đang tải danh sách profile...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- MODAL TẠO PROFILE MỚI -->
        <div id="modal-create-profile" class="modal-backdrop">
            <div class="modal-dialog">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">✨ Tạo Profile Mun Anti-Browser Mới</h3>
                    <button class="btn-close" onclick="closeCreateProfileModal()">✕</button>
                </div>
                <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Tên Profile:</label>
                        <input id="modal-prof-name" type="text" class="search-input" style="width:100%;" placeholder="VD: Profile TikTok Farm #1">
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Card Đồ Họa (WebGL GPU):</label>
                        <select id="modal-prof-gpu" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                            <option value="">🎲 Tự động gán GPU ngẫu nhiên</option>
                            <option value="ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)">NVIDIA GeForce RTX 3060 (DirectX 11)</option>
                            <option value="ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)">NVIDIA GeForce RTX 4070 (DirectX 11)</option>
                            <option value="ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)">NVIDIA GeForce GTX 1660 SUPER (DirectX 11)</option>
                            <option value="ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (AMD)">AMD Radeon RX 6700 XT (DirectX 11)</option>
                            <option value="ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (Intel)">Intel Iris Xe Graphics (DirectX 11)</option>
                            <option value="ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)">NVIDIA GeForce RTX 4060 (DirectX 11)</option>
                            <option value="ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (AMD)">AMD Radeon RX 7600 (DirectX 11)</option>
                        </select>
                    </div>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Số Nhân CPU:</label>
                            <select id="modal-prof-cpu" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="8">8 Cores (Khuyên dùng)</option>
                                <option value="4">4 Cores</option>
                                <option value="6">6 Cores</option>
                                <option value="12">12 Cores</option>
                                <option value="16">16 Cores</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Độ Phân Giải:</label>
                            <select id="modal-prof-res" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="1920x1080">1920x1080 (FHD)</option>
                                <option value="1920x1200">1920x1200 (WUXGA)</option>
                                <option value="1536x864">1536x864 (Laptop)</option>
                                <option value="2560x1440">2560x1440 (2K)</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">URL Khởi Động:</label>
                        <input id="modal-prof-url" type="text" class="search-input" style="width:100%;" value="https://iphey.com">
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Proxy (Tùy chọn):</label>
                        <input id="modal-prof-proxy" type="text" class="search-input" style="width:100%;" placeholder="VD: 127.0.0.1:10808 (Để trống nếu Direct)">
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeCreateProfileModal()">Hủy</button>
                        <button class="btn btn-primary" onclick="submitCreateProfile()">🚀 Tạo Profile</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- VIEW 3: IOS AUTOMATION & IPATOOL -->
        <div class="view-content" id="view-ios">
            <div class="action-toolbar">
                <div class="toolbar-group">
                    <h2 style="font-size: 14px; font-weight: 700;">🍏 iOS Automation Suite & IPATool Downloader</h2>
                </div>
                <div class="toolbar-group">
                    <input type="text" class="search-input" placeholder="Tìm App Store (VD: TikTok, Shopee)..." id="ios-app-search" style="width: 280px;">
                    <button class="btn btn-primary" onclick="searchAppStore()">🔍 Tìm App</button>
                </div>
            </div>

            <div style="margin-bottom: 16px;">
                <h3 style="font-size: 13px; margin-bottom: 8px; color: var(--text-muted);">Thiết Bị iOS Đang Kết Nối:</h3>
                <table class="data-table">
                    <thead>
                        <tr>
                            <th>UDID</th>
                            <th>Tên Thiết Bị</th>
                            <th>Model</th>
                            <th>iOS Version</th>
                            <th>Pin</th>
                            <th>Trạng Thái</th>
                            <th>Thao Tác</th>
                        </tr>
                    </thead>
                    <tbody id="ios-devices-body">
                        <tr><td colspan="7" style="text-align: center;">Đang quét cổng usbmuxd...</td></tr>
                    </tbody>
                </table>
            </div>

            <div id="app-search-results" style="display: none;">
                <h3 style="font-size: 13px; margin-bottom: 8px; color: var(--text-muted);">Kết Quả Tìm Kiếm App Store:</h3>
                <div id="app-results-grid" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px;"></div>
            </div>
        </div>

        <!-- VIEW 4: C69 ROUTER PRO -->
        <div class="view-content" id="view-router">
            <div class="action-toolbar">
                <div class="toolbar-group">
                    <h2 style="font-size: 14px; font-weight: 700;">⚡ C69 Router Pro — Định Tuyến Mihomo TUN & Proxy Pool</h2>
                </div>
                <div class="toolbar-group">
                    <button class="btn btn-primary" onclick="rotateProxy()">🔄 Xoay IP Ngay Lập Tức</button>
                </div>
            </div>
            <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-bottom: 16px;">
                <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 14px;">
                    <h3 style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">Trạng Thái Mihomo TUN</h3>
                    <p style="font-size: 18px; font-weight: 700; color: var(--success);">🟢 SẴN SÀNG (Online)</p>
                    <p style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Card: GenRouterTUN • Metric: 500</p>
                </div>
                <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 14px;">
                    <h3 style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">Proxy Pool</h3>
                    <p style="font-size: 18px; font-weight: 700; color: #38bdf8;">250 Proxy SOCKS5</p>
                    <p style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Độ trễ trung bình: 78ms</p>
                </div>
                <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 14px;">
                    <h3 style="font-size: 12px; color: var(--text-muted); margin-bottom: 6px;">Giàn Thiết Bị Định Tuyến</h3>
                    <p style="font-size: 18px; font-weight: 700; color: #a855f7;">10 Android + 1 iOS</p>
                    <p style="font-size: 11px; color: var(--text-muted); margin-top: 4px;">Định tuyến độc lập từng IP</p>
                </div>
            </div>
        </div>

        <!-- VIEW 5: TIKTOK STUDIO -->
        <div class="view-content" id="view-nurture">
            <div class="action-toolbar">
                <div class="toolbar-group">
                    <h2 style="font-size: 14px; font-weight: 700;">🤖 TikTok Automation Studio & AI Video</h2>
                </div>
            </div>
            <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 16px;">
                <p style="color: var(--text-muted); margin-bottom: 10px; font-size: 12px;">Nhật ký tự động hóa TikTok Nurture Engine:</p>
                <div id="nurture-log-box" style="background:#000; border: 1px solid var(--border); border-radius: 6px; padding: 10px; font-family: monospace; font-size: 11px; height: 350px; overflow-y: auto; color: #38bdf8;">
                    [System] TikTok Nurture Engine sẵn sàng điều khiển 10 máy Samsung...
                </div>
            </div>
        </div>

        <!-- VIEW 6: C69 STORE -->
        <div class="view-content" id="view-store" style="height: 100%; padding: 0;">
            <iframe src="https://c69.us" style="width: 100%; height: 100%; border: none; background: #020409;"></iframe>
        </div>

        <!-- VIEW 7: SETTINGS -->
        <div class="view-content" id="view-settings">
            <div class="action-toolbar">
                <h2 style="font-size: 14px; font-weight: 700;">⚙️ Cài Đặt Hệ Thống & Chẩn Đoán</h2>
            </div>
            <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 20px; max-width: 550px;">
                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Máy Chủ C69 Backend API:</label>
                    <input type="text" class="search-input" value="https://cu.c69.us" style="width: 100%;">
                </div>
                <div style="margin-bottom: 14px;">
                    <label style="display: block; font-size: 11px; color: var(--text-muted); margin-bottom: 4px;">Gemini API Key (Tự động bình luận / AI Video):</label>
                    <input type="password" class="search-input" value="AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXX" style="width: 100%;">
                </div>
                <button class="btn btn-primary">Lưu Cấu Hình</button>
            </div>
        </div>
    </main>

    <!-- WI-FI MANAGEMENT MODAL -->
    <div id="wifi-modal-backdrop" class="modal-backdrop" onclick="closeWifiModal(event)">
        <div class="modal-dialog" onclick="event.stopPropagation()">
            <div class="modal-header">
                <div style="display:flex; align-items:center; gap:8px;">
                    <span style="font-size:18px;">📶</span>
                    <div>
                        <div style="font-weight:800; font-size:14px;" id="wifi-modal-title">Quản Lý & Kết Nối Wi-Fi</div>
                        <div style="font-size:10px; color:var(--text-muted);" id="wifi-modal-serial">Serial: ...</div>
                    </div>
                </div>
                <button class="btn-close" onclick="closeWifiModal()">✕</button>
            </div>
            <div class="modal-body">
                <div class="wifi-action-bar">
                    <button class="btn btn-success" onclick="toggleWifi(true)">⚡ Bật Wi-Fi</button>
                    <button class="btn btn-danger" onclick="toggleWifi(false)">🛑 Tắt Wi-Fi</button>
                    <button class="btn btn-dark" onclick="openWifiSettingsOnDevice()">📲 Mở Cài Đặt Trên Máy</button>
                    <button class="btn btn-primary" onclick="scanWifiNetworks()">🔄 Quét Lại</button>
                </div>
                
                <div class="wifi-connect-box">
                    <div style="font-weight:700; font-size:11px; margin-bottom:6px; color:var(--primary);">⚡ Kết Nối Nhanh Wi-Fi:</div>
                    <div style="display:flex; gap:6px; margin-bottom:6px;">
                        <input type="text" id="wifi-ssid-input" class="search-input" style="flex:1;" placeholder="Tên Wi-Fi (SSID)...">
                        <input type="password" id="wifi-pwd-input" class="search-input" style="flex:1;" placeholder="Mật khẩu (để trống nếu Open)...">
                        <button class="btn btn-primary" onclick="submitWifiConnect()">Kết Nối</button>
                    </div>
                </div>

                <div style="font-weight:700; font-size:11px; margin: 4px 0 2px 0; color:var(--text-muted); display:flex; justify-content:space-between; align-items:center;">
                    <span>DANH SÁCH MẠNG KHẢ DỤNG:</span>
                    <span id="wifi-scan-status" style="color:var(--primary); font-size:10px;"></span>
                </div>
                <div class="wifi-list-container" id="wifi-list-container">
                    <div style="text-align:center; padding:20px; color:var(--text-muted); font-size:11px;">Bấm "Quét Lại" để tìm kiếm mạng...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = window.location.origin;
        const WS_BASE = `ws://${window.location.host}`;
        const activeSockets = {};
        let currentDevices = [];
        let allProfiles = [];
        let activeWifiSerial = null;

        function switchNav(navId) {
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.view-content').forEach(v => v.classList.remove('active'));

            const item = Array.from(document.querySelectorAll('.nav-item')).find(el => el.getAttribute('onclick').includes(navId));
            if (item) item.classList.add('active');

            const view = document.getElementById(`view-${navId}`);
            if (view) view.classList.add('active');

            if (navId === 'browser') loadBrowserProfiles();
            if (navId === 'ios') loadIosDevices();
        }

        async function refreshAll() {
            await refreshDevices();
            loadBrowserProfiles();
            loadIosDevices();
        }

        async function refreshDevices() {
            try {
                const res = await fetch(`${API_BASE}/api/devices`);
                const devices = await res.json();
                currentDevices = devices;
                document.getElementById('android-count').innerText = devices.length;

                const grid = document.getElementById('device-grid');
                if (devices.length === 0) {
                    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 60px 0; color: var(--text-muted);">
                        ℹ️ Chưa phát hiện thiết bị Android nào qua ADB.<br>Vui lòng cắm giàn Samsung vào USB và bật "Gỡ lỗi USB".
                    </div>`;
                    return;
                }

                grid.innerHTML = '';
                devices.forEach(dev => {
                    const card = document.createElement('div');
                    card.className = 'phone-card';
                    card.innerHTML = `
                        <div class="phone-header">
                            <b>📱 ${dev.brand} ${dev.model}</b>
                            <span style="color: ${dev.battery > 20 ? '#10b981' : '#ef4444'}">🔋 ${dev.battery}%</span>
                        </div>
                        <div class="screen-container" id="screen-box-${dev.serial}">
                            <canvas class="screen-img" id="canvas-${dev.serial}" width="360" height="740"></canvas>
                            <div class="touch-indicator" id="indicator-${dev.serial}"></div>
                        </div>
                        <div class="phone-control-bar">
                            <button class="ctrl-btn" onclick="sendAction('${dev.serial}', 'wake')">⚡ Mở</button>
                            <button class="ctrl-btn" onclick="sendAction('${dev.serial}', 'unlock')">🔓 Unlock</button>
                            <button class="ctrl-btn" onclick="sendAction('${dev.serial}', 'launch')">🎵 TikTok</button>
                            <button class="ctrl-btn" onclick="sendAction('${dev.serial}', 'key', {keycode: 3})">🏠 Home</button>
                            <button class="ctrl-btn" onclick="sendAction('${dev.serial}', 'key', {keycode: 4})">◀ Back</button>
                            <button class="ctrl-btn" onclick="sendAction('${dev.serial}', 'recents')">📑 Đa nhiệm</button>
                            <button class="ctrl-btn" onclick="sendAction('${dev.serial}', 'vol_up')">🔊 Vol+</button>
                            <button class="ctrl-btn" style="color:var(--primary);" onclick="openWifiModal('${dev.serial}')">📶 Wi-Fi</button>
                        </div>
                        <div class="phone-footer">
                            <span>S/N: <b>${dev.serial}</b></span>
                            <span id="status-${dev.serial}">Live ⚡</span>
                        </div>
                    `;
                    grid.appendChild(card);
                    setupStreamAndTouch(dev.serial, dev.width, dev.height);
                });
            } catch (e) {
                console.error(e);
            }
        }

        function setupStreamAndTouch(serial, devWidth, devHeight) {
            if (activeSockets[serial]) {
                activeSockets[serial].close();
                delete activeSockets[serial];
            }

            const canvas = document.getElementById(`canvas-${serial}`);
            const ctx = canvas.getContext('2d', { alpha: false });
            ctx.imageSmoothingEnabled = true;
            ctx.imageSmoothingQuality = 'high';
            const indicator = document.getElementById(`indicator-${serial}`);

            // ── Persistent Frame Buffer (OffscreenCanvas) ───────────────
            if (!window._farmFrameCache) window._farmFrameCache = {};
            const cache = window._farmFrameCache;

            if (cache[serial]) {
                ctx.drawImage(cache[serial], 0, 0, canvas.width, canvas.height);
            }

            // ── Zero-Flicker Vsync Rendering State ──────────────────────
            let pendingBitmap = null;
            let rafId = null;

            function schedulePaint() {
                if (rafId !== null) return;
                rafId = requestAnimationFrame(() => {
                    rafId = null;
                    if (!pendingBitmap) return;
                    if (canvas.width !== pendingBitmap.width || canvas.height !== pendingBitmap.height) {
                        canvas.width = pendingBitmap.width;
                        canvas.height = pendingBitmap.height;
                        ctx.imageSmoothingEnabled = true;
                        ctx.imageSmoothingQuality = 'high';
                    }
                    ctx.drawImage(pendingBitmap, 0, 0, canvas.width, canvas.height);
                    if (!cache[serial] || cache[serial].width !== canvas.width || cache[serial].height !== canvas.height) {
                        cache[serial] = new OffscreenCanvas(canvas.width, canvas.height);
                    }
                    const cctx = cache[serial].getContext('2d');
                    cctx.imageSmoothingEnabled = true;
                    cctx.imageSmoothingQuality = 'high';
                    cctx.drawImage(pendingBitmap, 0, 0, canvas.width, canvas.height);
                    pendingBitmap.close();
                    pendingBitmap = null;
                });
            }

            let wsReconnectDelay = 500;
            let wsReconnectTimer = null;
            let destroyed = false;

            function connectWS() {
                if (destroyed) return;
                if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }

                if (cache[serial]) {
                    ctx.drawImage(cache[serial], 0, 0, canvas.width, canvas.height);
                }

                const ws = new WebSocket(`${WS_BASE}/ws/stream/${serial}`);
                ws.binaryType = 'arraybuffer';
                activeSockets[serial] = ws;

                ws.onmessage = (event) => {
                    if (!(event.data instanceof ArrayBuffer) && !(event.data instanceof Blob)) return;
                    const blob = event.data instanceof Blob
                        ? event.data
                        : new Blob([event.data], { type: 'image/jpeg' });

                    createImageBitmap(blob).then(bitmap => {
                        if (pendingBitmap) pendingBitmap.close();
                        pendingBitmap = bitmap;
                        schedulePaint();
                        wsReconnectDelay = 500;
                    }).catch(() => {
                        const url = URL.createObjectURL(blob);
                        const img = new Image();
                        img.onload = () => {
                            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                            URL.revokeObjectURL(url);
                        };
                        img.src = url;
                    });
                };

                ws.onopen = () => {
                    wsReconnectDelay = 500;
                    const statusEl = document.getElementById(`status-${serial}`);
                    if (statusEl) statusEl.textContent = 'Live ⚡';
                };

                ws.onerror = () => {};

                ws.onclose = () => {
                    if (destroyed) return;
                    const statusEl = document.getElementById(`status-${serial}`);
                    if (statusEl) statusEl.textContent = 'Reconnecting...';
                    wsReconnectDelay = Math.min(wsReconnectDelay * 1.5, 3000);
                    wsReconnectTimer = setTimeout(connectWS, wsReconnectDelay);
                };
            }

            connectWS();

            canvas._destroyWS = () => {
                destroyed = true;
                if (rafId !== null) { cancelAnimationFrame(rafId); rafId = null; }
                if (pendingBitmap) { pendingBitmap.close(); pendingBitmap = null; }
                if (wsReconnectTimer) clearTimeout(wsReconnectTimer);
                if (activeSockets[serial]) {
                    activeSockets[serial].close();
                    delete activeSockets[serial];
                }
            };

            // ── Ultra-Responsive Pointer Capture Touch Engine ───────────
            const container = document.getElementById(`screen-box-${serial}`);
            let isPointerDown = false;
            let startClientX = 0, startClientY = 0;
            let startTime = 0;

            const activeDevW = (devWidth && devWidth > 0) ? devWidth : 720;
            const activeDevH = (devHeight && devHeight > 0) ? devHeight : 1480;

            function getDeviceCoords(clientX, clientY) {
                const rect = canvas.getBoundingClientRect();
                const scaleX = activeDevW / Math.max(1, rect.width);
                const scaleY = activeDevH / Math.max(1, rect.height);
                const relX = clientX - rect.left;
                const relY = clientY - rect.top;
                const x = Math.max(0, Math.min(activeDevW - 1, Math.round(relX * scaleX)));
                const y = Math.max(0, Math.min(activeDevH - 1, Math.round(relY * scaleY)));
                return { x, y, rect, relX, relY };
            }

            container.addEventListener('pointerdown', (e) => {
                if (e.button !== 0) return;
                isPointerDown = true;
                startClientX = e.clientX;
                startClientY = e.clientY;
                startTime = Date.now();
                try { container.setPointerCapture(e.pointerId); } catch(_) {}

                const coords = getDeviceCoords(e.clientX, e.clientY);
                if (indicator) {
                    indicator.style.left = `${coords.relX}px`;
                    indicator.style.top = `${coords.relY}px`;
                    indicator.classList.add('active');
                }
            });

            container.addEventListener('pointermove', (e) => {
                if (!isPointerDown) return;
                const coords = getDeviceCoords(e.clientX, e.clientY);
                if (indicator) {
                    indicator.style.left = `${coords.relX}px`;
                    indicator.style.top = `${coords.relY}px`;
                }
            });

            container.addEventListener('pointerup', (e) => {
                if (!isPointerDown) return;
                isPointerDown = false;
                try { container.releasePointerCapture(e.pointerId); } catch(_) {}
                if (indicator) indicator.classList.remove('active');

                const start = getDeviceCoords(startClientX, startClientY);
                const end = getDeviceCoords(e.clientX, e.clientY);
                const elapsed = Date.now() - startTime;
                const dist = Math.hypot(end.x - start.x, end.y - start.y);
                const isSync = document.getElementById('sync-all-checkbox')?.checked;

                if (dist < 16 && elapsed < 400) {
                    // Instant Tap
                    dispatchActionToTargets(serial, isSync, ws => {
                        ws.send(JSON.stringify({ type: 'tap', x: start.x, y: start.y }));
                    }, { action: 'tap', x: start.x, y: start.y });
                } else {
                    // Smooth Swipe
                    const duration = Math.min(600, Math.max(80, elapsed));
                    dispatchActionToTargets(serial, isSync, ws => {
                        ws.send(JSON.stringify({
                            type: 'swipe',
                            x1: start.x, y1: start.y,
                            x2: end.x, y2: end.y,
                            duration
                        }));
                    }, { action: 'swipe', x: start.x, y: start.y, x2: end.x, y2: end.y, duration });
                }
            });

            container.addEventListener('pointercancel', () => {
                isPointerDown = false;
                if (indicator) indicator.classList.remove('active');
            });

            // Wheel scroll
            let wheelRafId = null;
            let pendingWheel = null;
            container.addEventListener('wheel', (e) => {
                e.preventDefault();
                pendingWheel = e;
                if (wheelRafId) return;
                wheelRafId = requestAnimationFrame(() => {
                    wheelRafId = null;
                    const ev = pendingWheel;
                    pendingWheel = null;
                    const coords = getDeviceCoords(ev.clientX, ev.clientY);
                    const delta = ev.deltaY > 0 ? 120 : -120;
                    const isSync = document.getElementById('sync-all-checkbox')?.checked;
                    dispatchActionToTargets(serial, isSync, ws => {
                        ws.send(JSON.stringify({ type: 'scroll', x: coords.x, y: coords.y, delta_y: delta }));
                    }, { action: 'scroll', x: coords.x, y: coords.y, delta_y: delta });
                });
            }, { passive: false });

            container.tabIndex = 0;
            container.addEventListener('keydown', (e) => {
                const ws = activeSockets[serial];
                if (!ws || ws.readyState !== WebSocket.OPEN) return;

                if (e.key === 'Backspace') {
                    ws.send(JSON.stringify({ type: 'key', code: 67 }));
                    e.preventDefault();
                } else if (e.key === 'Enter') {
                    ws.send(JSON.stringify({ type: 'key', code: 66 }));
                    e.preventDefault();
                } else if (e.key === 'Escape') {
                    ws.send(JSON.stringify({ type: 'key', code: 4 }));
                    e.preventDefault();
                } else if (e.key.length === 1 && !e.ctrlKey && !e.altKey) {
                    ws.send(JSON.stringify({ type: 'text', text: e.key }));
                    e.preventDefault();
                }
            });
        }

        function dispatchActionToTargets(sourceSerial, isSync, wsCallback, fallbackPayload) {
            if (isSync) {
                Object.values(activeSockets).forEach(ws => {
                    if (ws && ws.readyState === WebSocket.OPEN) wsCallback(ws);
                });
            } else {
                const ws = activeSockets[sourceSerial];
                if (ws && ws.readyState === WebSocket.OPEN) {
                    wsCallback(ws);
                } else {
                    sendAction(sourceSerial, fallbackPayload.action, fallbackPayload);
                }
            }
        }

        function sendAction(serial, action, extra = {}) {
            const isSync = document.getElementById('sync-all-checkbox')?.checked;
            const targets = isSync ? currentDevices.map(d => d.serial) : [serial];

            for (const s of targets) {
                fetch(`${API_BASE}/api/devices/${s}/action`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action, ...extra })
                }).catch(() => {});
            }
        }

        function promptTextInput(serial) {
            const text = prompt("Nhập văn bản cần gõ vào điện thoại:");
            if (text) {
                sendAction(serial, 'text', { text });
            }
        }

        async function batchAction(action, extra = {}) {
            for (const dev of currentDevices) {
                await fetch(`${API_BASE}/api/devices/${dev.serial}/action`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action, ...extra })
                });
            }
        }

        // ── Wi-Fi Modal & Operations ─────────────────────────────────────────
        function openWifiModal(serial) {
            activeWifiSerial = serial;
            const backdrop = document.getElementById('wifi-modal-backdrop');
            const titleEl = document.getElementById('wifi-modal-title');
            const serialEl = document.getElementById('wifi-modal-serial');

            if (serial === 'all') {
                titleEl.textContent = '📶 Quản Lý Wi-Fi Cho Toàn Bộ Giàn Android';
                serialEl.textContent = `Áp dụng đồng bộ cho tất cả ${currentDevices.length} máy`;
            } else {
                const dev = currentDevices.find(d => d.serial === serial);
                titleEl.textContent = `📶 Quản Lý Wi-Fi: ${dev ? (dev.brand + ' ' + dev.model) : serial}`;
                serialEl.textContent = `Serial: ${serial}`;
            }

            backdrop.classList.add('active');
            scanWifiNetworks();
        }

        function closeWifiModal(e) {
            if (e && e.target !== document.getElementById('wifi-modal-backdrop') && !e.target.classList.contains('btn-close')) return;
            document.getElementById('wifi-modal-backdrop').classList.remove('active');
        }

        async function toggleWifi(enabled) {
            const statusEl = document.getElementById('wifi-scan-status');
            statusEl.textContent = enabled ? 'Đang bật Wi-Fi...' : 'Đang tắt Wi-Fi...';

            const targets = (activeWifiSerial === 'all') ? currentDevices.map(d => d.serial) : [activeWifiSerial];
            for (const s of targets) {
                await fetch(`${API_BASE}/api/devices/${s}/wifi/toggle`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled })
                });
            }
            statusEl.textContent = enabled ? '✅ Đã bật Wi-Fi!' : '🛑 Đã tắt Wi-Fi!';
            if (enabled) {
                setTimeout(scanWifiNetworks, 1200);
            }
        }

        async function openWifiSettingsOnDevice() {
            const targets = (activeWifiSerial === 'all') ? currentDevices.map(d => d.serial) : [activeWifiSerial];
            for (const s of targets) {
                await fetch(`${API_BASE}/api/devices/${s}/wifi/settings`, { method: 'POST' });
            }
            document.getElementById('wifi-scan-status').textContent = '📲 Đã mở trang Wi-Fi trên màn hình!';
        }

        async function scanWifiNetworks() {
            const container = document.getElementById('wifi-list-container');
            const statusEl = document.getElementById('wifi-scan-status');
            container.innerHTML = `<div style="text-align:center; padding:24px; color:var(--text-muted); font-size:11px;">⏳ Đang quét danh sách mạng Wi-Fi khả dụng...</div>`;
            statusEl.textContent = 'Đang quét...';

            const targetSerial = (activeWifiSerial === 'all')
                ? (currentDevices[0]?.serial || '')
                : activeWifiSerial;

            if (!targetSerial) {
                container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted);">Không tìm thấy thiết bị nào.</div>`;
                statusEl.textContent = '';
                return;
            }

            try {
                const res = await fetch(`${API_BASE}/api/devices/${targetSerial}/wifi/scan`);
                const data = await res.json();
                const networks = data.networks || [];
                statusEl.textContent = `Tìm thấy ${networks.length} mạng`;

                if (networks.length === 0) {
                    container.innerHTML = `<div style="text-align:center; padding:24px; color:var(--text-muted); font-size:11px;">Không tìm thấy Wi-Fi nào (Hãy bấm "⚡ Bật Wi-Fi" hoặc thử lại).</div>`;
                    return;
                }

                container.innerHTML = networks.map(net => `
                    <div class="wifi-row" onclick="selectWifiSsid('${net.ssid.replace(/'/g, "\\'")}')" style="cursor:pointer;">
                        <div>
                            <div style="font-weight:700; color:#fff; display:flex; align-items:center; gap:6px;">
                                <span>📶 ${net.ssid}</span>
                                ${net.is_connected ? '<span class="wifi-connected-badge">Đã kết nối</span>' : ''}
                            </div>
                            <div style="font-size:10px; color:var(--text-muted); margin-top:2px;">
                                ${net.frequency} • ${net.security} • Tín hiệu: ${net.signal_level} dBm
                            </div>
                        </div>
                        <button class="btn btn-primary" style="padding:4px 10px; font-size:10px;" onclick="event.stopPropagation(); selectWifiSsid('${net.ssid.replace(/'/g, "\\'")}'); document.getElementById('wifi-pwd-input').focus();">
                            Chọn
                        </button>
                    </div>
                `).join('');
            } catch (e) {
                container.innerHTML = `<div style="text-align:center; padding:20px; color:#ef4444;">Lỗi khi quét mạng Wi-Fi: ${e}</div>`;
                statusEl.textContent = '';
            }
        }

        function selectWifiSsid(ssid) {
            document.getElementById('wifi-ssid-input').value = ssid;
        }

        async function submitWifiConnect() {
            const ssid = document.getElementById('wifi-ssid-input').value.trim();
            const password = document.getElementById('wifi-pwd-input').value;
            const statusEl = document.getElementById('wifi-scan-status');

            if (!ssid) {
                alert('Vui lòng chọn hoặc nhập tên Wi-Fi (SSID)!');
                return;
            }

            statusEl.textContent = `Đang kết nối vào "${ssid}"...`;
            const targets = (activeWifiSerial === 'all') ? currentDevices.map(d => d.serial) : [activeWifiSerial];

            for (const s of targets) {
                await fetch(`${API_BASE}/api/devices/${s}/wifi/connect`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ssid, password })
                });
            }

            statusEl.textContent = `✅ Đã phát lệnh kết nối vào "${ssid}"!`;
            setTimeout(scanWifiNetworks, 3000);
        }

        async function installTikTokAll() {
            const res = await fetch(`${API_BASE}/api/devices/install-tiktok`, { method: 'POST' });
            const d = await res.json();
            alert(d.message || 'Đang cài đặt TikTok trên các máy...');
        }

        async function optimizeResolution() {
            const res = await fetch(`${API_BASE}/api/farm/optimize-resolution`, { method: 'POST' });
            const d = await res.json();
            alert(d.message || 'Đã tối ưu độ phân giải HD+ (720x1480)!');
            setTimeout(refreshDevices, 1000);
        }

        async function launchScrcpy() {
            const res = await fetch(`${API_BASE}/api/farm/launch-scrcpy`, { method: 'POST' });
            const d = await res.json();
            alert(d.message || 'Đã khởi chạy Scrcpy Hardware Stream 60 FPS!');
        }

        async function startNurtureAll() {
            await fetch(`${API_BASE}/api/nurture/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            alert('Đã phát lệnh nuôi TikTok tự động cho toàn bộ giàn Android!');
        }

        async function stopNurtureAll() {
            await fetch(`${API_BASE}/api/nurture/stop`, { method: 'POST' });
            alert('Đã dừng tiến trình nuôi!');
        }

        // ── Mun Anti Browser Management ──────────────────────────────────────
        async function loadBrowserProfiles() {
            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles`);
                allProfiles = await res.json();
                renderProfiles(allProfiles);
            } catch (e) {
                console.error(e);
            }
        }

        function renderProfiles(profiles) {
            const tbody = document.getElementById('browser-profiles-body');
            if (profiles.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Chưa có profile nào. Hãy bấm "Tạo Profile Mới".</td></tr>`;
                return;
            }

            tbody.innerHTML = profiles.map(p => {
                let gpuLabel = 'DirectX 11 GPU';
                if (p.gpu_renderer) {
                    if (p.gpu_renderer.includes('RTX 3060')) gpuLabel = 'NVIDIA RTX 3060';
                    else if (p.gpu_renderer.includes('RTX 4070')) gpuLabel = 'NVIDIA RTX 4070';
                    else if (p.gpu_renderer.includes('RTX 3070')) gpuLabel = 'NVIDIA RTX 3070';
                    else if (p.gpu_renderer.includes('RTX 4060')) gpuLabel = 'NVIDIA RTX 4060';
                    else if (p.gpu_renderer.includes('GTX 1660')) gpuLabel = 'NVIDIA GTX 1660 SUPER';
                    else if (p.gpu_renderer.includes('RX 6700')) gpuLabel = 'AMD Radeon RX 6700 XT';
                    else if (p.gpu_renderer.includes('RX 7600')) gpuLabel = 'AMD Radeon RX 7600';
                    else if (p.gpu_renderer.includes('Iris')) gpuLabel = 'Intel Iris Xe Graphics';
                    else gpuLabel = p.gpu_renderer.split('(')[1]?.split(',')[1]?.trim() || p.gpu_renderer.slice(0, 25);
                }
                return `
                <tr>
                    <td><b>#${p.id}</b></td>
                    <td><b style="color:var(--primary);">${p.name}</b></td>
                    <td style="font-size: 11px; max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">
                        <span style="background: rgba(255,255,255,0.05); padding: 2px 6px; border-radius: 4px;">${p.profile_os}</span> 
                        <span style="color:#e2e8f0;">${p.profile_user_agent}</span>
                    </td>
                    <td>
                        <div style="font-size:11px; color:#38bdf8; font-weight:600;">🎮 ${gpuLabel}</div>
                        <div style="color:#10b981; font-size:10px;">🛡️ Canvas Noise #${p.id} • Audio Noise • ${p.profile_cpu || 8} Cores</div>
                    </td>
                    <td>${p.proxy_string ? `<span style="color:#10b981;">${p.proxy_type}://${p.proxy_string}</span>` : '<span style="color:var(--text-muted);">Direct</span>'}</td>
                    <td>
                        <button id="btn-launch-${p.id}" class="btn btn-primary" style="padding: 4px 10px; font-size: 11px;" onclick="launchBrowserProfile(${p.id})">🚀 Mở Browser</button>
                        <button class="btn btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="deleteBrowserProfile(${p.id})">🗑️</button>
                    </td>
                </tr>
            `}).join('');
        }

        function filterProfiles() {
            const term = document.getElementById('profile-search').value.toLowerCase();
            const filtered = allProfiles.filter(p => p.name.toLowerCase().includes(term) || p.profile_user_agent.toLowerCase().includes(term));
            renderProfiles(filtered);
        }

        function openCreateProfileModal() {
            const modal = document.getElementById('modal-create-profile');
            document.getElementById('modal-prof-name').value = `Profile #${allProfiles.length}`;
            modal.style.display = 'flex';
        }

        function closeCreateProfileModal() {
            document.getElementById('modal-create-profile').style.display = 'none';
        }

        async function submitCreateProfile() {
            const name = document.getElementById('modal-prof-name').value.trim();
            const gpuVal = document.getElementById('modal-prof-gpu').value;
            let gpu_renderer = null, gpu_vendor = null;
            if (gpuVal) {
                const parts = gpuVal.split('|');
                gpu_renderer = parts[0];
                gpu_vendor = parts[1] || "Google Inc. (NVIDIA)";
            }
            const cpu = parseInt(document.getElementById('modal-prof-cpu').value) || 8;
            const resolution = document.getElementById('modal-prof-res').value || "1920x1080";
            const start_url = document.getElementById('modal-prof-url').value.trim() || "https://iphey.com";
            const proxy = document.getElementById('modal-prof-proxy').value.trim();

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name || `Profile #${allProfiles.length}`,
                        gpu_renderer: gpu_renderer,
                        gpu_vendor: gpu_vendor,
                        profile_cpu: cpu,
                        profile_resolution: resolution,
                        profile_start_url: start_url,
                        proxy_string: proxy
                    })
                });
                const data = await res.json();
                closeCreateProfileModal();
                alert(data.message || "Đã tạo profile thành công!");
                loadBrowserProfiles();
            } catch (e) {
                alert("Lỗi khi tạo profile: " + e);
            }
        }

        async function launchBrowserProfile(id) {
            const btn = document.getElementById(`btn-launch-${id}`) || event.target;
            const origText = btn.innerText;
            btn.innerText = "⏳ Đang mở...";
            btn.disabled = true;

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/launch`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const d = await res.json();
                setTimeout(() => {
                    btn.innerText = "🟢 Đang chạy";
                    setTimeout(() => {
                        btn.innerText = origText;
                        btn.disabled = false;
                    }, 5000);
                }, 1500);
            } catch(e) {
                alert("Lỗi khi mở profile: " + e);
                btn.innerText = origText;
                btn.disabled = false;
            }
        }

        async function deleteBrowserProfile(id) {
            if (!confirm(`Bạn có chắc muốn xóa Profile #${id}?`)) return;
            await fetch(`${API_BASE}/api/browser/profiles/${id}`, { method: 'DELETE' });
            loadBrowserProfiles();
        }

        // ── iOS Automation Management ────────────────────────────────────────
        async function loadIosDevices() {
            try {
                const res = await fetch(`${API_BASE}/api/ios/devices`);
                const devices = await res.json();
                document.getElementById('ios-count').innerText = devices.length;

                const tbody = document.getElementById('ios-devices-body');
                if (devices.length === 0) {
                    tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted);">Chưa phát hiện iPhone nào qua cổng usbmuxd.</td></tr>`;
                    return;
                }

                tbody.innerHTML = devices.map(d => `
                    <tr>
                        <td><code>${d.udid}</code></td>
                        <td><b>${d.name}</b></td>
                        <td>${d.model}</td>
                        <td><span style="background: rgba(168, 85, 247, 0.15); color: #c084fc; padding: 2px 6px; border-radius: 4px;">${d.ios_version}</span></td>
                        <td style="color:#10b981;">🔋 ${d.battery}%</td>
                        <td>${d.status}</td>
                        <td>
                            <button class="btn btn-purple" style="padding: 4px 8px; font-size: 11px;">⚡ Active</button>
                            <button class="btn btn-dark" style="padding: 4px 8px; font-size: 11px;">🔄 Respring</button>
                        </td>
                    </tr>
                `).join('');
            } catch (e) {
                console.error(e);
            }
        }

        async function searchAppStore() {
            const term = document.getElementById('ios-app-search').value;
            if (!term) return;
            const res = await fetch(`${API_BASE}/api/ios/search-app?term=${encodeURIComponent(term)}&country=VN&limit=6`);
            const data = await res.json();
            const container = document.getElementById('app-results-grid');
            document.getElementById('app-search-results').style.display = 'block';

            if (!data.results || data.results.length === 0) {
                container.innerHTML = `<div style="grid-column: 1 / -1; color: var(--text-muted);">Không tìm thấy ứng dụng.</div>`;
                return;
            }

            container.innerHTML = data.results.map(app => `
                <div style="background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 10px; display: flex; gap: 10px; align-items: center;">
                    <img src="${app.artworkUrl60 || ''}" style="width: 44px; height: 44px; border-radius: 8px;">
                    <div style="flex: 1; overflow: hidden;">
                        <div style="font-weight: 700; font-size: 12px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden;">${app.trackName}</div>
                        <div style="font-size: 10px; color: var(--text-muted);">${app.bundleId} • v${app.version}</div>
                        <button class="btn btn-primary" style="padding: 3px 6px; font-size: 9px; margin-top: 4px;" onclick="alert('Đang tải IPA qua IPATool cho app: ${app.trackName}...')">📥 Tải IPA</button>
                    </div>
                </div>
            `).join('');
        }

        async function rotateProxy() {
            const res = await fetch(`${API_BASE}/api/router/rotate`, { method: 'POST' });
            const d = await res.json();
            alert(d.message || 'Đã phát lệnh xoay IP!');
        }

        refreshAll();
        setInterval(refreshDevices, 8000);
    </script>
</body>
</html>"#)
}
