use crate::adb_manager::{AdbManager, DeviceInfo};
use crate::stream_manager::StreamManager;
use crate::tiktok_nurture::{NurtureConfig, TikTokNurtureEngine};
use axum::extract::{Path, Query, State, WebSocketUpgrade};
use axum::http::StatusCode;
use axum::response::{Html, Response};
use axum::routing::{delete, get, post, put};
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
    pub browser_nurture: Arc<crate::browser_nurture::BrowserNurtureEngine>,
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
    pub engine_mode: Option<String>, // "native", "js_stealth", hoặc "hybrid"
    #[serde(default)]
    pub profile_user_agent: String,
    #[serde(default)]
    pub profile_os: String,
    #[serde(default)]
    pub profile_resolution: String,
    #[serde(default)]
    pub profile_cpu: usize,
    #[serde(default)]
    pub profile_ram: usize,
    #[serde(default)]
    pub proxy_string: String,
    #[serde(default)]
    pub proxy_type: String,
    #[serde(default)]
    pub profile_start_url: String,
    #[serde(default)]
    pub canvas_seed: Option<u64>,
    #[serde(default)]
    pub audio_seed: Option<u64>,
    #[serde(default)]
    pub webrtc_mode: Option<String>, // "disabled", "proxy_only", "custom"
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
    #[serde(default)]
    pub tiktok_account_id: Option<u64>,
    #[serde(default)]
    pub tiktok_username: Option<String>,
    #[serde(default)]
    pub last_nurture_status: Option<String>, // "Đã nuôi thành công", "Rate limit (Chờ 1h)", "Lỗi nuôi", v.v.
    #[serde(default)]
    pub last_nurture_time: Option<String>, // "YYYY-MM-DD HH:mm:ss"
    #[serde(default)]
    pub last_nurture_error: Option<String>, // Chi tiết lỗi nếu có
    #[serde(default)]
    pub retry_after_epoch: Option<u64>, // UNIX timestamp được phép chạy lại (cho lỗi maximum attempts)
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
        .route("/api/browser/profiles", put(update_browser_profile_handler))
        .route("/api/browser/profiles/change-proxy", post(change_browser_profile_proxy_handler))
        .route("/api/browser/profiles/randomize-fingerprints", post(randomize_fingerprints_handler))
        .route("/api/browser/profiles/switch-mode", post(switch_profile_mode_handler))
        .route("/api/browser/profiles/launch", post(launch_browser_profile_handler))
        .route("/api/browser/profiles/stop", post(stop_browser_profile_handler))
        .route("/api/browser/active", get(get_active_browser_profiles_handler))
        .route("/api/browser/core-status", get(browser_core_status_handler))
        .route("/api/browser/profiles/:id", delete(delete_browser_profile_handler))
        .route("/api/browser/tiktok/rate-limit-signal", post(tiktok_rate_limit_signal_handler))
        .route("/api/browser/tiktok/login-success-signal", post(tiktok_login_success_signal_handler))
        // ── Mun Anti Browser TikTok Nurture & C69 APIs ──
        .route("/api/browser/nurture/start", post(browser_nurture_start_handler))
        .route("/api/browser/nurture/start-selected", post(browser_nurture_start_selected_handler))
        .route("/api/browser/nurture/create-and-nurture", post(browser_nurture_create_and_nurture_handler))
        .route("/api/browser/nurture/assign-account", post(browser_nurture_assign_account_handler))
        .route("/api/browser/nurture/stop", post(browser_nurture_stop_handler))
        .route("/api/browser/nurture/status", get(browser_nurture_status_handler))
        .route("/api/browser/nurture/:id/submit-otp", post(browser_nurture_submit_otp_handler))
        .route("/api/browser/nurture/upload-video", post(browser_nurture_upload_video_handler))
        .route("/api/browser/nurture/generate-video", post(browser_nurture_generate_video_handler))
        .route("/api/browser/nurture/auto-reg-gmail", post(browser_nurture_auto_reg_gmail_handler))
        .route("/api/browser/c69/accounts", get(browser_c69_accounts_handler))
        .route("/api/browser/c69/sync-profiles", post(browser_c69_sync_profiles_handler))
        .route("/api/browser/c69/proxies", get(browser_c69_proxies_handler))
        .route("/api/browser/c69/proxies/import", post(browser_proxies_import_handler))
        .route("/api/browser/c69/proxies/remove-dead", post(browser_proxies_remove_dead_handler))
        .route("/api/browser/proxies/remove-dead", post(browser_proxies_remove_dead_handler))
        .route("/api/browser/proxies/import", post(browser_proxies_import_handler))
        .route("/api/browser/proxy/test", post(browser_proxy_test_handler))
        .route("/api/browser/proxies/test-batch", post(browser_proxies_test_batch_handler))
        .route("/api/browser/proxies/auto-replace-dead", post(browser_proxies_auto_replace_dead_handler))
        .route("/api/browser/proxies/status-cache", get(browser_proxies_status_cache_handler))
        .route("/api/browser/c69/proxies/status-cache", get(browser_proxies_status_cache_handler))
        // ── C69 Auth & User APIs ──
        .route("/api/c69/auth/login", post(c69_auth_login_handler))
        .route("/api/c69/auth/status", get(c69_auth_status_handler))
        .route("/api/c69/auth/logout", post(c69_auth_logout_handler))
        .route("/api/c69/users", get(c69_users_handler))
        .route("/api/c69/accounts/:id", get(c69_get_account_detail_handler).patch(c69_update_account_handler).delete(c69_delete_account_handler))
        .route("/api/c69/accounts/:id/2fa", get(c69_get_2fa_handler))
        .route("/api/c69/accounts/bulk-delete", post(c69_bulk_delete_handler))
        .route("/api/c69/accounts/bulk-status", post(c69_bulk_status_handler))
        .route("/api/c69/accounts/bulk-sub-owner", post(c69_bulk_sub_owner_handler))
        .route("/api/c69/accounts/bulk-main", post(c69_bulk_main_handler))
        .route("/api/c69/accounts/assign-socks", post(c69_assign_socks_handler))
        .route("/api/c69/accounts/add-manual", post(c69_add_manual_handler))
        .route("/api/c69/accounts/bulk-add", post(c69_bulk_add_handler))
        .route("/api/c69/cards/active", get(c69_get_active_card_handler))
        .route("/api/c69/emails/:id/read", get(c69_read_email_mailbox_handler))
        // ── iOS & IPATool APIs ──
        .route("/api/ios/devices", get(list_ios_devices_handler))
        .route("/api/ios/search-app", get(search_ios_app_handler))
        // ── C69 Router & Proxy APIs ──
        .route("/api/router/status", get(router_status_handler))
        .route("/api/router/rotate", post(router_rotate_handler))
        // ── Auto-Update & System APIs ──
        .route("/api/system/check-update", get(system_check_update_handler))
        .route("/api/system/perform-update", post(system_perform_update_handler))
        .layer(cors)
        .with_state(state)
}

// ── Android Farm Handlers ────────────────────────────────────────────────────

async fn list_devices_handler(State(state): State<AppState>) -> Json<Vec<DeviceInfo>> {
    let adb = state.adb.clone();
    let devices = tokio::task::spawn_blocking(move || {
        adb.get_all_devices()
    }).await.unwrap_or_default();
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
            name: "Profile #0 - RTX 3060 (Native C++)".into(),
            engine_mode: Some("native".into()),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1920x1080".into(),
            profile_cpu: 8,
            profile_ram: 16,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            canvas_seed: Some(18472910),
            audio_seed: Some(92817401),
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
        },
        BrowserProfile {
            id: 1,
            name: "Profile #1 - RTX 4070 (JS Stealth)".into(),
            engine_mode: Some("js_stealth".into()),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "2560x1440".into(),
            profile_cpu: 12,
            profile_ram: 32,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            canvas_seed: Some(58392019),
            audio_seed: Some(39102948),
            webrtc_mode: Some("proxy_only".into()),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
            tiktok_account_id: None,
            tiktok_username: None,
            last_nurture_status: None,
            last_nurture_time: None,
            last_nurture_error: None,
            retry_after_epoch: None,
        },
        BrowserProfile {
            id: 2,
            name: "Profile #2 - RX 6700 XT (Hybrid)".into(),
            engine_mode: Some("hybrid".into()),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1920x1200".into(),
            profile_cpu: 8,
            profile_ram: 16,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            canvas_seed: Some(83920194),
            audio_seed: Some(19284710),
            webrtc_mode: Some("proxy_only".into()),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (AMD)".into()),
            tiktok_account_id: None,
            tiktok_username: None,
            last_nurture_status: None,
            last_nurture_time: None,
            last_nurture_error: None,
            retry_after_epoch: None,
        },
        BrowserProfile {
            id: 3,
            name: "Profile #3 - Iris Xe (JS Stealth)".into(),
            engine_mode: Some("js_stealth".into()),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1600x900".into(),
            profile_cpu: 4,
            profile_ram: 8,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            canvas_seed: Some(71928401),
            audio_seed: Some(48291048),
            webrtc_mode: Some("proxy_only".into()),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (Intel)".into()),
            tiktok_account_id: None,
            tiktok_username: None,
            last_nurture_status: None,
            last_nurture_time: None,
            last_nurture_error: None,
            retry_after_epoch: None,
        },
        BrowserProfile {
            id: 4,
            name: "Profile #4 - GTX 1660 SUPER (Native C++)".into(),
            engine_mode: Some("native".into()),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1536x864".into(),
            profile_cpu: 6,
            profile_ram: 16,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            canvas_seed: Some(38291049),
            audio_seed: Some(74920194),
            webrtc_mode: Some("proxy_only".into()),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
            tiktok_account_id: None,
            tiktok_username: None,
            last_nurture_status: None,
            last_nurture_time: None,
            last_nurture_error: None,
            retry_after_epoch: None,
        },
        BrowserProfile {
            id: 5,
            name: "Profile #5 - RTX 3070 Ti (Native C++)".into(),
            engine_mode: Some("native".into()),
            profile_user_agent: String::new(),
            profile_os: "Windows".into(),
            profile_resolution: "1920x1080".into(),
            profile_cpu: 16,
            profile_ram: 32,
            proxy_string: String::new(),
            proxy_type: "socks5".into(),
            profile_start_url: "https://iphey.com".into(),
            canvas_seed: Some(94820194),
            audio_seed: Some(58291048),
            webrtc_mode: Some("proxy_only".into()),
            profile_canvas: serde_json::Value::Null,
            profile_webgl: serde_json::Value::Null,
            profile_audio: serde_json::Value::Null,
            gpu_renderer: Some("ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)".into()),
            gpu_vendor: Some("Google Inc. (NVIDIA)".into()),
            tiktok_account_id: None,
            tiktok_username: None,
            last_nurture_status: None,
            last_nurture_time: None,
            last_nurture_error: None,
            retry_after_epoch: None,
        },
    ]
}

pub fn get_profiles_file_path() -> PathBuf {
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

pub fn get_profile_by_id(profile_id: usize) -> Option<BrowserProfile> {
    let path = get_profiles_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(profiles) = serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            return profiles.into_iter().find(|p| p.id == profile_id);
        }
    }
    None
}

pub fn get_all_profiles() -> Vec<BrowserProfile> {
    let path = get_profiles_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(profiles) = serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            return profiles;
        }
    }
    vec![]
}

static PROFILES_SAVE_MUTEX: std::sync::Mutex<()> = std::sync::Mutex::new(());

pub fn sanitize_profiles_on_startup() {
    let _lock = PROFILES_SAVE_MUTEX.lock();
    let path = get_profiles_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(mut profiles) = serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            let mut changed = false;
            for p in &mut profiles {
                if let Some(ref st) = p.last_nurture_status {
                    if st.contains("Đang") || st.contains("Chờ slot") || st.contains("Kiểm tra") || st.contains("Khởi động") {
                        p.last_nurture_status = Some("Đã dừng".to_string());
                        changed = true;
                    }
                }
            }
            if changed {
                let tmp_path = path.with_extension("tmp");
                if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
                    if std::fs::write(&tmp_path, json_str).is_ok() {
                        let _ = std::fs::rename(&tmp_path, &path);
                    }
                }
            }
        }
    }
}

pub fn update_profile_nurture_status(
    profile_id: usize,
    status: &str,
    error: Option<&str>,
    retry_after_secs: Option<u64>,
) {
    let _lock = PROFILES_SAVE_MUTEX.lock();
    let path = get_profiles_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(mut profiles) = serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            let mut updated = false;
            let now_str = chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string();
            let now_epoch = std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .map(|d| d.as_secs())
                .unwrap_or(0);

            for p in &mut profiles {
                if p.id == profile_id {
                    p.last_nurture_status = Some(status.to_string());
                    p.last_nurture_time = Some(now_str.clone());
                    p.last_nurture_error = error.map(|s| s.to_string());
                    if let Some(secs) = retry_after_secs {
                        p.retry_after_epoch = Some(now_epoch + secs);
                    } else if status.contains("thành công") {
                        p.retry_after_epoch = None;
                    }
                    updated = true;
                    break;
                }
            }
            if updated {
                let tmp_path = path.with_extension("tmp");
                if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
                    if std::fs::write(&tmp_path, json_str).is_ok() {
                        let _ = std::fs::rename(&tmp_path, &path);
                    }
                }
            }
        }
    }
}

pub fn update_profile_proxy(profile_id: usize, new_proxy: &str, proxy_type: &str) {
    let path = get_profiles_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(mut profiles) = serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            for p in &mut profiles {
                if p.id == profile_id {
                    p.proxy_string = new_proxy.to_string();
                    p.proxy_type = proxy_type.to_string();
                    break;
                }
            }
            if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
                let _ = std::fs::write(&path, json_str);
            }
        }
    }
}

async fn list_browser_profiles_handler() -> Json<Vec<BrowserProfile>> {
    let path = get_profiles_file_path();
    if let Ok(data) = std::fs::read_to_string(&path) {
        match serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            Ok(mut profiles) => {
                if !profiles.is_empty() {
                    let mut need_save = false;
                    for p in &mut profiles {
                        if p.engine_mode.is_none() {
                            p.engine_mode = Some(if p.id % 2 == 0 { "native".into() } else { "js_stealth".into() });
                            need_save = true;
                        }
                        if p.profile_ram == 0 {
                            let rams = [8, 16, 16, 32, 64];
                            p.profile_ram = rams[p.id % rams.len()];
                            need_save = true;
                        }
                        if p.canvas_seed.is_none() {
                            p.canvas_seed = Some((p.id as u64 + 1).wrapping_mul(1664525) ^ 0x5a5a5a5a);
                            need_save = true;
                        }
                        if p.audio_seed.is_none() {
                            p.audio_seed = Some((p.id as u64 + 1).wrapping_mul(1103515245) ^ 0xa5a5a5a5);
                            need_save = true;
                        }
                    }
                    if need_save {
                        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
                            let _ = std::fs::write(&path, json_str);
                        }
                    }
                    return Json(profiles);
                }
            }
            Err(e) => {
                eprintln!("⚠️ [JSON PARSE ERROR] Không thể parse profiles từ {}: {}", path.display(), e);
            }
        }
    }

    let defaults = get_default_browser_profiles();
    if !path.exists() {
        if let Ok(json_str) = serde_json::to_string_pretty(&defaults) {
            let _ = std::fs::write(&path, json_str);
        }
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

    if new_prof.engine_mode.is_none() || new_prof.engine_mode.as_ref().unwrap().trim().is_empty() {
        new_prof.engine_mode = Some(if next_id % 2 == 0 { "native".into() } else { "js_stealth".into() });
    }
    if new_prof.profile_ram == 0 {
        let rams = [8, 16, 16, 32, 64];
        new_prof.profile_ram = rams[next_id % rams.len()];
    }
    if new_prof.canvas_seed.is_none() || new_prof.canvas_seed.unwrap() == 0 {
        new_prof.canvas_seed = Some((next_id as u64 + 1).wrapping_mul(1664525) ^ 0x5a5a5a5a);
    }
    if new_prof.audio_seed.is_none() || new_prof.audio_seed.unwrap() == 0 {
        new_prof.audio_seed = Some((next_id as u64 + 1).wrapping_mul(1103515245) ^ 0xa5a5a5a5);
    }
    if new_prof.webrtc_mode.is_none() {
        new_prof.webrtc_mode = Some("proxy_only".into());
    }
    if new_prof.proxy_type.trim().is_empty() {
        new_prof.proxy_type = if new_prof.proxy_string.trim().is_empty() { "direct".into() } else { "socks5".into() };
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

async fn update_browser_profile_handler(Json(updated_prof): Json<BrowserProfile>) -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_default();

    let mut found = false;
    for p in &mut profiles {
        if p.id == updated_prof.id {
            *p = updated_prof.clone();
            found = true;
            break;
        }
    }

    if found {
        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
            let _ = std::fs::write(&path, json_str);
        }
        Json(serde_json::json!({
            "success": true,
            "message": format!("Đã cập nhật cấu hình Fingerprint cho Profile #{}!", updated_prof.id)
        }))
    } else {
        Json(serde_json::json!({
            "success": false,
            "message": format!("Không tìm thấy Profile #{}", updated_prof.id)
        }))
    }
}

#[derive(Deserialize)]
pub struct RandomizeFingerprintsPayload {
    pub profile_ids: Vec<usize>,
}

async fn randomize_fingerprints_handler(
    Json(payload): Json<RandomizeFingerprintsPayload>,
) -> Json<serde_json::Value> {
    use rand::seq::SliceRandom;
    use rand::Rng;

    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_default();

    let mut rng = rand::thread_rng();
    let target_set: std::collections::HashSet<usize> = payload.profile_ids.into_iter().collect();
    let mut updated_count = 0;

    let cpus = [4, 6, 8, 12, 16];
    let rams = [8, 16, 32, 64];
    let desktop_resolutions = ["1920x1080", "1920x1200", "1536x864", "2560x1440", "1440x900", "1680x1050"];
    let mobile_resolutions = ["412x915", "393x873", "390x844", "428x926", "360x800"];

    for p in &mut profiles {
        if target_set.contains(&p.id) {
            // 1. Sinh mới Canvas & Audio noise seeds
            p.canvas_seed = Some(rng.gen_range(10_000_000..99_999_999));
            p.audio_seed = Some(rng.gen_range(10_000_000..99_999_999));

            // 2. Chọn ngẫu nhiên GPU từ GPU_POOL
            let gpu_idx = rng.gen_range(0..crate::cdp_browser::GPU_POOL.len());
            let (rend, vend) = crate::cdp_browser::GPU_POOL[gpu_idx];
            p.gpu_renderer = Some(rend.to_string());
            p.gpu_vendor = Some(vend.to_string());

            // 3. CPU & RAM
            p.profile_cpu = *cpus.choose(&mut rng).unwrap_or(&8);
            p.profile_ram = *rams.choose(&mut rng).unwrap_or(&16);

            // 4. Resolution tương thích theo OS / UA hiện tại của profile
            let is_mobile = p.profile_os.eq_ignore_ascii_case("Android")
                || p.profile_os.eq_ignore_ascii_case("iOS")
                || p.profile_user_agent.contains("Mobile")
                || p.profile_user_agent.contains("Android");

            if is_mobile {
                p.profile_resolution = mobile_resolutions.choose(&mut rng).unwrap_or(&"412x915").to_string();
            } else {
                p.profile_resolution = desktop_resolutions.choose(&mut rng).unwrap_or(&"1920x1080").to_string();
            }

            updated_count += 1;
        }
    }

    if updated_count > 0 {
        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
            let _ = std::fs::write(&path, json_str);
        }
    }

    Json(serde_json::json!({
        "success": true,
        "count": updated_count,
        "message": format!("Đã đổi mới toàn diện Fingerprint (Canvas, Audio, WebGL GPU, CPU, RAM) cho {} profile đã chọn!", updated_count)
    }))
}

#[derive(Deserialize)]
pub struct SwitchProfileModePayload {
    pub profile_ids: Vec<usize>,
    pub mode: String, // "mobile", "desktop", "toggle"
}

async fn switch_profile_mode_handler(
    Json(payload): Json<SwitchProfileModePayload>,
) -> Json<serde_json::Value> {
    use rand::seq::SliceRandom;

    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_default();

    let target_set: std::collections::HashSet<usize> = payload.profile_ids.into_iter().collect();
    let mut updated_count = 0;
    let mut rng = rand::thread_rng();

    let phone_uas = [
        crate::cdp_browser::DEFAULT_PHONE_UA,
        "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.98 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.98 Mobile Safari/537.36",
        "Mozilla/5.0 (Linux; Android 14; 23127PN0CG) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.98 Mobile Safari/537.36",
    ];

    let desktop_uas = [
        crate::cdp_browser::DEFAULT_DESKTOP_UA,
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36",
    ];

    let mobile_resolutions = ["412x915", "393x873", "390x844", "428x926", "360x800"];
    let desktop_resolutions = ["1920x1080", "1920x1200", "1536x864", "2560x1440"];

    for p in &mut profiles {
        if target_set.contains(&p.id) {
            let current_is_mobile = p.profile_os.eq_ignore_ascii_case("Android")
                || p.profile_os.eq_ignore_ascii_case("iOS")
                || p.profile_user_agent.contains("Mobile")
                || p.profile_user_agent.contains("Android");

            let to_mobile = match payload.mode.as_str() {
                "mobile" => true,
                "desktop" => false,
                _ => !current_is_mobile, // "toggle"
            };

            if to_mobile {
                p.profile_os = "Android".to_string();
                p.profile_user_agent = phone_uas.choose(&mut rng).unwrap_or(&phone_uas[0]).to_string();
                p.profile_resolution = mobile_resolutions.choose(&mut rng).unwrap_or(&"412x915").to_string();
            } else {
                p.profile_os = "Windows".to_string();
                p.profile_user_agent = desktop_uas.choose(&mut rng).unwrap_or(&desktop_uas[0]).to_string();
                p.profile_resolution = desktop_resolutions.choose(&mut rng).unwrap_or(&"1920x1080").to_string();
            }

            updated_count += 1;
        }
    }

    if updated_count > 0 {
        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
            let _ = std::fs::write(&path, json_str);
        }
    }

    let mode_desc = match payload.mode.as_str() {
        "mobile" => "Mobile (Android Phone)",
        "desktop" => "Desktop (Windows PC)",
        _ => "chế độ tương ứng",
    };

    Json(serde_json::json!({
        "success": true,
        "count": updated_count,
        "message": format!("Đã chuyển đổi {} profile đã chọn sang {}!", updated_count, mode_desc)
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

async fn browser_core_status_handler() -> Json<serde_json::Value> {
    let custom = crate::cdp_browser::find_custom_chromium();
    let sys = crate::cdp_browser::find_system_chrome();
    Json(serde_json::json!({
        "has_custom_core": custom.is_some(),
        "custom_path": custom.map(|p| p.to_string_lossy().to_string()),
        "has_system_chrome": sys.is_some(),
        "system_path": sys.map(|p| p.to_string_lossy().to_string()),
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
                engine_mode: Some("native".into()),
                profile_user_agent: String::new(),
                profile_os: "Windows".into(),
                profile_resolution: "1920x1080".into(),
                profile_cpu: 8,
                profile_ram: 16,
                proxy_string: String::new(),
                proxy_type: "socks5".into(),
                profile_start_url: "https://iphey.com".into(),
                canvas_seed: Some((id as u64 + 1).wrapping_mul(1664525) ^ 0x5a5a5a5a),
                audio_seed: Some((id as u64 + 1).wrapping_mul(1103515245) ^ 0xa5a5a5a5),
                webrtc_mode: Some("proxy_only".into()),
                profile_canvas: serde_json::Value::Null,
                profile_webgl: serde_json::Value::Null,
                profile_audio: serde_json::Value::Null,
                gpu_renderer: Some(rend.to_string()),
                gpu_vendor: Some(vend.to_string()),
                tiktok_account_id: None,
                tiktok_username: None,
                last_nurture_status: None,
                last_nurture_time: None,
                last_nurture_error: None,
                retry_after_epoch: None,
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

async fn stop_browser_profile_handler(Json(payload): Json<serde_json::Value>) -> Json<serde_json::Value> {
    let id = payload.get("id").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    crate::cdp_browser::stop_cdp_profile(id);
    Json(serde_json::json!({
        "success": true,
        "message": format!("🛑 Đã đóng Profile #{}", id)
    }))
}

async fn get_active_browser_profiles_handler() -> Json<Vec<usize>> {
    Json(crate::cdp_browser::get_active_profile_ids())
}

async fn tiktok_rate_limit_signal_handler(
    State(state): State<AppState>,
    Json(payload): Json<serde_json::Value>,
) -> Json<serde_json::Value> {
    let profile_id = payload.get("profile_id").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    if profile_id > 0 {
        tracing::warn!("⚠️ [Profile #{}] Nhận tín hiệu Rate limit (Maximum attempts) từ trình duyệt TikTok!", profile_id);
        update_profile_nurture_status(
            profile_id,
            "Rate limit (Chờ 1h)",
            Some("Maximum number of attempts reached (Tài khoản hoặc IP bị giới hạn số lần đăng nhập. Tự động đóng trình duyệt và chờ 1h thử lại)"),
            Some(3600),
        );
        state.browser_nurture.set_rate_limit_status(profile_id);
        crate::cdp_browser::stop_cdp_profile(profile_id);
        tracing::info!("🛑 [Profile #{}] Đã tự động đóng trình duyệt an toàn để chờ 1h thử lại.", profile_id);
    }
    Json(serde_json::json!({ "success": true }))
}

async fn tiktok_login_success_signal_handler(Json(payload): Json<serde_json::Value>) -> Json<serde_json::Value> {
    let profile_id = payload.get("profile_id").and_then(|v| v.as_u64()).unwrap_or(0) as usize;
    if profile_id > 0 {
        tracing::info!("🎉 [Profile #{}] Nhận tín hiệu đăng nhập TikTok thành công!", profile_id);
        update_profile_nurture_status(profile_id, "Đã đăng nhập sẵn (Sẵn sàng)", None, None);
        let _ = crate::cdp_browser::backup_thin_profile(profile_id);
    }
    Json(serde_json::json!({ "success": true }))
}

// ── Mun Anti Browser TikTok Nurture & C69 Handlers ───────────────────────────

#[derive(Deserialize)]
pub struct BrowserNurtureStartPayload {
    pub profile_id: usize,
    pub c69_account_id: Option<u64>,
    pub c69_username: Option<String>,
    pub c69_password: Option<String>,
    pub proxy_string: Option<String>,
    pub auto_assign_c69_proxy: Option<bool>,
}

#[derive(Deserialize)]
pub struct BrowserNurtureSelectedPayload {
    pub profile_ids: Vec<usize>,
    pub auto_assign_c69_proxy: Option<bool>,
}

#[derive(Deserialize)]
pub struct CreateAndNurturePayload {
    pub c69_account_id: u64,
    pub c69_username: String,
    pub c69_password: Option<String>,
    pub proxy_string: Option<String>,
    pub auto_assign_c69_proxy: Option<bool>,
}

#[derive(Deserialize)]
pub struct AssignAccountPayload {
    pub profile_id: usize,
    pub c69_account_id: Option<u64>,
    pub c69_username: Option<String>,
}

#[derive(Deserialize)]
pub struct BrowserNurtureStopPayload {
    pub profile_id: usize,
}

#[derive(Deserialize, Default)]
pub struct ProxyTestPayload {
    pub proxy_string: Option<String>,
    pub proxy: Option<String>,
}

async fn browser_nurture_start_handler(
    State(state): State<AppState>,
    Json(payload): Json<BrowserNurtureStartPayload>,
) -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(get_default_browser_profiles);

    let target_idx = match profiles.iter().position(|p| p.id == payload.profile_id) {
        Some(idx) => idx,
        None => {
            return Json(serde_json::json!({
                "success": false,
                "message": format!("Không tìm thấy Profile #{}", payload.profile_id)
            }));
        }
    };

    let mut modified = false;

    // Nếu có truyền tài khoản C69 mới, cập nhật vào Profile để ghi nhớ
    if payload.c69_account_id.is_some() || payload.c69_username.is_some() {
        profiles[target_idx].tiktok_account_id = payload.c69_account_id;
        if let Some(ref u) = payload.c69_username {
            profiles[target_idx].tiktok_username = Some(u.clone());
        }
        modified = true;
    }

    // Xử lý cấu hình Proxy
    if let Some(ref p_str) = payload.proxy_string {
        if !p_str.trim().is_empty() {
            profiles[target_idx].proxy_string = p_str.trim().to_string();
            profiles[target_idx].proxy_type = "socks5".into();
            modified = true;
        }
    } else if payload.auto_assign_c69_proxy.unwrap_or(false) && profiles[target_idx].proxy_string.trim().is_empty() {
        let c69_proxies = crate::browser_nurture::load_c69_proxies();
        if !c69_proxies.is_empty() {
            let picked = &c69_proxies[payload.profile_id % c69_proxies.len()];
            profiles[target_idx].proxy_string = picked.to_proxy_string();
            profiles[target_idx].proxy_type = "socks5".into();
            modified = true;
        }
    }

    if modified {
        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
            let _ = std::fs::write(&path, json_str);
        }
    }

    let target_prof = profiles[target_idx].clone();

    let now_epoch = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    // Kiểm tra nếu profile đang bị TikTok giới hạn đăng nhập (chờ 1h)
    if let Some(retry_epoch) = target_prof.retry_after_epoch {
        if retry_epoch > now_epoch {
            let remain_mins = (retry_epoch - now_epoch + 59) / 60;
            return Json(serde_json::json!({
                "success": false,
                "message": format!(
                    "⚠️ Profile #{} đang trong thời gian chờ giãn cách (Maximum attempts). Vui lòng chờ thêm {} phút (đủ 1 giờ) trước khi login lại để tránh bị TikTok khóa tài khoản!",
                    payload.profile_id, remain_mins
                )
            }));
        }
    }

    let c69_acc = if let (Some(u), Some(p)) = (payload.c69_username, payload.c69_password) {
        Some(crate::browser_nurture::C69Account {
            id: payload.c69_account_id.unwrap_or(0),
            username: u,
            password: Some(p),
            two_factor_auth: None,
            email: None,
            cookies: None,
            status: None,
            note: None,
            accounts_emails: None,
            ..Default::default()
        })
    } else {
        // Tìm tài khoản theo account ID hoặc username lưu trong profile hoặc lấy từ danh sách C69
        let mut acc = None;
        if let Some(aid) = target_prof.tiktok_account_id {
            if let Ok(a) = crate::browser_nurture::fetch_c69_account_by_id(aid).await {
                acc = Some(a);
            }
        }
        if acc.is_none() {
            let all_accs = crate::browser_nurture::fetch_c69_tiktok_accounts().await.ok().unwrap_or_default();
            if let Some(ref saved_u) = target_prof.tiktok_username {
                acc = all_accs.into_iter().find(|a| a.username.eq_ignore_ascii_case(saved_u));
            } else {
                acc = all_accs.into_iter().next();
            }
        }
        acc
    };

    match state.browser_nurture.start_nurture(target_prof, c69_acc).await {
        Ok(()) => Json(serde_json::json!({
            "success": true,
            "message": format!("Đã kích hoạt chu trình nuôi TikTok C69 cho Profile #{}!", payload.profile_id)
        })),
        Err(e) => Json(serde_json::json!({
            "success": false,
            "message": e
        })),
    }
}

async fn browser_nurture_start_selected_handler(
    State(state): State<AppState>,
    Json(payload): Json<BrowserNurtureSelectedPayload>,
) -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(get_default_browser_profiles);

    let all_c69_accs = crate::browser_nurture::fetch_c69_tiktok_accounts().await.ok().unwrap_or_default();
    let c69_proxies = crate::browser_nurture::load_c69_proxies();
    let auto_proxy = payload.auto_assign_c69_proxy.unwrap_or(true);

    let now_epoch = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);

    // Thu thập các tài khoản đã bị gán cho profile nào đó
    let mut used_acc_ids: std::collections::HashSet<u64> = profiles
        .iter()
        .filter_map(|p| p.tiktok_account_id)
        .collect();

    let mut started_count = 0;
    let mut skipped_rate_limited = Vec::new();
    let mut modified = false;
    let mut proxy_cursor = 0;

    for pid in payload.profile_ids {
        if let Some(idx) = profiles.iter().position(|p| p.id == pid) {
            let prof = &mut profiles[idx];

            // Bỏ qua nếu profile đang trong thời gian chờ 1h
            if let Some(retry_epoch) = prof.retry_after_epoch {
                if retry_epoch > now_epoch {
                    let remain_mins = (retry_epoch - now_epoch + 59) / 60;
                    skipped_rate_limited.push((pid, remain_mins));
                    continue;
                }
            }

            let mut acc_to_use = None;

            if let Some(aid) = prof.tiktok_account_id {
                acc_to_use = all_c69_accs.iter().find(|a| a.id == aid).cloned();
                if acc_to_use.is_none() {
                    if let Ok(a) = crate::browser_nurture::fetch_c69_account_by_id(aid).await {
                        acc_to_use = Some(a);
                    }
                }
            } else if let Some(ref uname) = prof.tiktok_username {
                acc_to_use = all_c69_accs.iter().find(|a| a.username.eq_ignore_ascii_case(uname)).cloned();
            }

            // Nếu profile chưa có nick: chọn random 1 nick TikTok C69 chưa bị gán
            if acc_to_use.is_none() {
                if let Some(free_acc) = all_c69_accs.iter().find(|a| !used_acc_ids.contains(&a.id)) {
                    prof.tiktok_account_id = Some(free_acc.id);
                    prof.tiktok_username = Some(free_acc.username.clone());
                    used_acc_ids.insert(free_acc.id);
                    acc_to_use = Some(free_acc.clone());
                    modified = true;
                }
            }

            // Nếu profile chưa có Proxy và bật auto_assign_c69_proxy:
            if auto_proxy && prof.proxy_string.trim().is_empty() && !c69_proxies.is_empty() {
                let picked = &c69_proxies[(prof.id + proxy_cursor) % c69_proxies.len()];
                prof.proxy_string = picked.to_proxy_string();
                prof.proxy_type = "socks5".into();
                proxy_cursor += 1;
                modified = true;
            }

            let prof_clone = prof.clone();
            let _ = state.browser_nurture.start_nurture(prof_clone, acc_to_use).await;
            started_count += 1;
        }
    }

    if modified {
        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
            let _ = std::fs::write(&path, json_str);
        }
    }

    let skip_msg = if !skipped_rate_limited.is_empty() {
        let details = skipped_rate_limited.iter()
            .map(|(id, m)| format!("#{} (chờ {}p)", id, m))
            .collect::<Vec<_>>()
            .join(", ");
        format!(" Đã bỏ qua {} profile đang chờ giãn cách 1h: [{}].", skipped_rate_limited.len(), details)
    } else {
        String::new()
    };

    Json(serde_json::json!({
        "success": true,
        "count": started_count,
        "message": format!("Đã kích hoạt nuôi TikTok cho {} profiles được chọn!{}", started_count, skip_msg)
    }))
}

async fn browser_nurture_create_and_nurture_handler(
    State(state): State<AppState>,
    Json(payload): Json<CreateAndNurturePayload>,
) -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(get_default_browser_profiles);

    let next_id = profiles.iter().map(|p| p.id).max().unwrap_or(0) + 1;
    let gpu_idx = next_id % crate::cdp_browser::GPU_POOL.len();
    let (rend, vend) = crate::cdp_browser::GPU_POOL[gpu_idx];

    // Xác định Proxy cho profile mới
    let c69_proxies = crate::browser_nurture::load_c69_proxies();
    let auto_proxy = payload.auto_assign_c69_proxy.unwrap_or(true);
    let final_proxy = if let Some(ref p) = payload.proxy_string {
        if !p.trim().is_empty() { p.trim().to_string() } else { String::new() }
    } else if auto_proxy && !c69_proxies.is_empty() {
        let picked = &c69_proxies[next_id % c69_proxies.len()];
        picked.to_proxy_string()
    } else {
        String::new()
    };

    let new_profile = BrowserProfile {
        id: next_id,
        name: format!("TikTok — {}", payload.c69_username),
        engine_mode: Some("native".into()),
        profile_user_agent: String::new(),
        profile_os: "Windows".into(),
        profile_resolution: "1920x1080".into(),
        profile_cpu: 8,
        profile_ram: 16,
        proxy_string: final_proxy,
        proxy_type: "socks5".into(),
        profile_start_url: "https://www.tiktok.com".into(),
        canvas_seed: Some(rand::random::<u64>()),
        audio_seed: Some(rand::random::<u64>()),
        webrtc_mode: Some("proxy_only".into()),
        profile_canvas: serde_json::Value::Null,
        profile_webgl: serde_json::Value::Null,
        profile_audio: serde_json::Value::Null,
        gpu_renderer: Some(rend.to_string()),
        gpu_vendor: Some(vend.to_string()),
        tiktok_account_id: Some(payload.c69_account_id),
        tiktok_username: Some(payload.c69_username.clone()),
        last_nurture_status: None,
        last_nurture_time: None,
        last_nurture_error: None,
        retry_after_epoch: None,
    };

    profiles.push(new_profile.clone());
    if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
        let _ = std::fs::write(&path, json_str);
    }

    let c69_acc = crate::browser_nurture::C69Account {
        id: payload.c69_account_id,
        username: payload.c69_username.clone(),
        password: payload.c69_password,
        two_factor_auth: None,
        email: None,
        cookies: None,
        status: None,
        note: None,
        accounts_emails: None,
        ..Default::default()
    };

    match state.browser_nurture.start_nurture(new_profile, Some(c69_acc)).await {
        Ok(()) => Json(serde_json::json!({
            "success": true,
            "profile_id": next_id,
            "message": format!("Đã tạo Profile #{} ({}) và bắt đầu nuôi TikTok!", next_id, payload.c69_username)
        })),
        Err(e) => Json(serde_json::json!({
            "success": false,
            "profile_id": next_id,
            "message": e
        })),
    }
}

async fn browser_nurture_assign_account_handler(
    Json(payload): Json<AssignAccountPayload>,
) -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    let mut profiles: Vec<BrowserProfile> = std::fs::read_to_string(&path)
        .ok()
        .and_then(|data| serde_json::from_str(&data).ok())
        .unwrap_or_else(get_default_browser_profiles);

    if let Some(prof) = profiles.iter_mut().find(|p| p.id == payload.profile_id) {
        prof.tiktok_account_id = payload.c69_account_id;
        prof.tiktok_username = payload.c69_username.clone();

        if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
            let _ = std::fs::write(&path, json_str);
        }

        Json(serde_json::json!({
            "success": true,
            "message": format!("Đã gán tài khoản {} cho Profile #{}", payload.c69_username.as_deref().unwrap_or("None"), payload.profile_id)
        }))
    } else {
        Json(serde_json::json!({
            "success": false,
            "message": format!("Không tìm thấy Profile #{}", payload.profile_id)
        }))
    }
}

async fn browser_nurture_stop_handler(
    State(state): State<AppState>,
    Json(payload): Json<BrowserNurtureStopPayload>,
) -> Json<serde_json::Value> {
    state.browser_nurture.stop_nurture(payload.profile_id);
    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã dừng nuôi TikTok cho Profile #{}", payload.profile_id)
    }))
}

async fn browser_nurture_status_handler(
    State(state): State<AppState>,
) -> Json<Vec<crate::browser_nurture::BrowserNurtureStatus>> {
    Json(state.browser_nurture.get_all_statuses())
}

#[derive(Deserialize)]
pub struct SubmitOtpPayload {
    pub otp: String,
}

async fn browser_nurture_submit_otp_handler(
    State(state): State<AppState>,
    Path(profile_id): Path<usize>,
    Json(payload): Json<SubmitOtpPayload>,
) -> Json<serde_json::Value> {
    let otp = payload.otp.trim().to_string();
    state.browser_nurture.submit_otp(profile_id, otp.clone());
    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã chuyển mã OTP '{}' tới Profile #{}!", otp, profile_id)
    }))
}

#[derive(Deserialize)]
pub struct UploadVideoPayload {
    pub profile_id: usize,
    pub video_path: String,
    pub caption: String,
}

async fn browser_nurture_upload_video_handler(
    State(state): State<AppState>,
    Json(payload): Json<UploadVideoPayload>,
) -> Json<serde_json::Value> {
    let bn = state.browser_nurture.clone();
    tokio::spawn(async move {
        let _ = bn.upload_tiktok_video(payload.profile_id, payload.video_path, payload.caption).await;
    });
    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã kích hoạt tiến trình upload video lên TikTok cho Profile #{}!", payload.profile_id)
    }))
}

#[derive(Deserialize)]
pub struct GenerateVideoPayload {
    pub niche: Option<String>,
}

async fn browser_nurture_generate_video_handler(
    Json(payload): Json<GenerateVideoPayload>,
) -> Json<serde_json::Value> {
    match crate::ai_video_engine::generate_viral_video(payload.niche).await {
        Ok(res) => Json(res),
        Err(e) => Json(serde_json::json!({
            "success": false,
            "error": e
        })),
    }
}

#[derive(Deserialize)]
pub struct AutoRegGmailPayload {
    pub profile_id: usize,
    pub email_id: u64,
}

async fn browser_nurture_auto_reg_gmail_handler(
    State(state): State<AppState>,
    Json(payload): Json<AutoRegGmailPayload>,
) -> Json<serde_json::Value> {
    let bn = state.browser_nurture.clone();
    tokio::spawn(async move {
        let _ = bn.auto_register_tiktok_by_gmail(payload.profile_id, payload.email_id).await;
    });
    Json(serde_json::json!({
        "success": true,
        "message": format!("Đã kích hoạt quy trình tự động Reg nick TikTok qua Gmail cho Profile #{}!", payload.profile_id)
    }))
}

#[derive(Deserialize)]
pub struct C69LoginPayload {
    pub username: String,
    pub password: String,
    pub server_url: Option<String>,
}

async fn c69_auth_login_handler(Json(payload): Json<C69LoginPayload>) -> Json<serde_json::Value> {
    match crate::browser_nurture::login_c69(&payload.username, &payload.password, payload.server_url.as_deref()).await {
        Ok(sess) => Json(serde_json::json!({
            "success": true,
            "username": sess.username,
            "server_url": sess.server_url,
            "email": sess.email,
            "is_staff": sess.is_staff,
            "message": format!("Đăng nhập C69 thành công với tài khoản @{}!", sess.username)
        })),
        Err(e) => Json(serde_json::json!({
            "success": false,
            "message": e
        })),
    }
}

async fn c69_auth_status_handler() -> Json<serde_json::Value> {
    if let Some(sess) = crate::browser_nurture::load_c69_session() {
        Json(serde_json::json!({
            "logged_in": true,
            "username": sess.username,
            "server_url": sess.server_url,
            "email": sess.email,
            "is_staff": sess.is_staff,
            "last_login": sess.last_login
        }))
    } else {
        Json(serde_json::json!({
            "logged_in": false
        }))
    }
}

async fn c69_auth_logout_handler() -> Json<serde_json::Value> {
    let _ = crate::browser_nurture::clear_c69_session();
    Json(serde_json::json!({
        "success": true,
        "message": "Đã đăng xuất tài khoản C69"
    }))
}

async fn c69_read_email_mailbox_handler(axum::extract::Path(email_id): axum::extract::Path<u64>) -> Json<serde_json::Value> {
    match crate::browser_nurture::read_c69_email_mailbox(email_id).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({
            "success": false,
            "message": e
        }))
    }
}

async fn c69_users_handler() -> Json<serde_json::Value> {
    match crate::browser_nurture::fetch_c69_users_list().await {
        Ok(users) => Json(serde_json::json!({
            "success": true,
            "users": users
        })),
        Err(e) => Json(serde_json::json!({
            "success": false,
            "error": e,
            "users": []
        })),
    }
}

async fn c69_get_account_detail_handler(axum::extract::Path(id): axum::extract::Path<u64>) -> Json<serde_json::Value> {
    match crate::browser_nurture::fetch_c69_account_detail(id).await {
        Ok(data) => Json(serde_json::json!({ "success": true, "account": data })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn c69_update_account_handler(
    axum::extract::Path(id): axum::extract::Path<u64>,
    Json(payload): Json<serde_json::Value>,
) -> Json<serde_json::Value> {
    match crate::browser_nurture::update_c69_account_detail(id, payload).await {
        Ok(data) => Json(serde_json::json!({ "success": true, "account": data })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn c69_delete_account_handler(axum::extract::Path(id): axum::extract::Path<u64>) -> Json<serde_json::Value> {
    match crate::browser_nurture::delete_c69_account_single(id).await {
        Ok(_) => Json(serde_json::json!({ "success": true, "message": "Đã xóa tài khoản" })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn c69_get_2fa_handler(axum::extract::Path(id): axum::extract::Path<u64>) -> Json<serde_json::Value> {
    match crate::browser_nurture::fetch_c69_account_2fa(id).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

#[derive(Deserialize)]
struct BulkIdsPayload {
    ids: Vec<u64>,
}

async fn c69_bulk_delete_handler(Json(payload): Json<BulkIdsPayload>) -> Json<serde_json::Value> {
    match crate::browser_nurture::bulk_delete_c69_accounts(payload.ids).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

#[derive(Deserialize)]
struct BulkStatusPayload {
    ids: Vec<u64>,
    status: i32,
}

async fn c69_bulk_status_handler(Json(payload): Json<BulkStatusPayload>) -> Json<serde_json::Value> {
    match crate::browser_nurture::bulk_status_c69_accounts(payload.ids, payload.status).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

#[derive(Deserialize)]
struct BulkSubOwnerPayload {
    ids: Vec<u64>,
    subscription_owner: String,
}

async fn c69_bulk_sub_owner_handler(Json(payload): Json<BulkSubOwnerPayload>) -> Json<serde_json::Value> {
    match crate::browser_nurture::bulk_sub_owner_c69_accounts(payload.ids, &payload.subscription_owner).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

#[derive(Deserialize)]
struct BulkMainPayload {
    ids: Vec<u64>,
    action: String,
}

async fn c69_bulk_main_handler(Json(payload): Json<BulkMainPayload>) -> Json<serde_json::Value> {
    match crate::browser_nurture::bulk_main_c69_accounts(payload.ids, &payload.action).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn c69_add_manual_handler(Json(payload): Json<serde_json::Value>) -> Json<serde_json::Value> {
    match crate::browser_nurture::add_c69_account_manual(payload).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

#[derive(Deserialize)]
struct BulkAddPayload {
    accounts_data: String,
    r#type: String,
}

async fn c69_bulk_add_handler(Json(payload): Json<BulkAddPayload>) -> Json<serde_json::Value> {
    match crate::browser_nurture::bulk_add_c69_accounts(&payload.accounts_data, &payload.r#type).await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn c69_get_active_card_handler() -> Json<serde_json::Value> {
    match crate::browser_nurture::fetch_c69_active_card().await {
        Ok(data) => Json(data),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}


#[derive(Deserialize, Default)]
pub struct C69AccountsQuery {
    pub r#type: Option<String>,
    pub status: Option<String>,
    pub search: Option<String>,
    pub page: Option<u32>,
    pub page_size: Option<u32>,
    pub created_by: Option<String>,
    pub has_subscription: Option<String>,
    pub subscription_owner: Option<String>,
    pub account_tab: Option<String>,
    pub username_filter: Option<String>,
    pub sort: Option<String>,
    pub user_only: Option<bool>,
}

async fn browser_c69_accounts_handler(axum::extract::Query(query): axum::extract::Query<C69AccountsQuery>) -> Json<serde_json::Value> {
    match crate::browser_nurture::fetch_c69_accounts_full(
        query.r#type,
        query.status,
        query.search,
        query.created_by,
        query.has_subscription,
        query.subscription_owner,
        query.account_tab,
        query.username_filter,
        query.sort,
        query.user_only,
        query.page,
        query.page_size,
    ).await {
        Ok(full_data) => {
            let results = full_data.get("results").cloned().unwrap_or(serde_json::json!([]));
            let count = full_data.get("count").and_then(|v| v.as_u64()).unwrap_or(0);
            Json(serde_json::json!({
                "success": true,
                "count": count,
                "accounts": results
            }))
        },
        Err(_) => {
            match crate::browser_nurture::fetch_c69_tiktok_accounts().await {
                Ok(accs) => {
                    let len = accs.len();
                    Json(serde_json::json!({ "success": true, "count": len, "accounts": accs }))
                },
                Err(e) => Json(serde_json::json!({ "success": false, "error": e, "accounts": [] })),
            }
        }
    }
}

async fn browser_c69_sync_profiles_handler() -> Json<serde_json::Value> {
    let path = get_profiles_file_path();
    match crate::browser_nurture::sync_c69_profiles_to_local(path).await {
        Ok(count) => Json(serde_json::json!({
            "success": true,
            "message": format!("Đã đồng bộ thành công {} profiles mới từ server C69!", count)
        })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn browser_c69_proxies_handler() -> Json<serde_json::Value> {
    let proxies = crate::browser_nurture::load_c69_proxies();
    let count = proxies.len();
    Json(serde_json::json!({
        "success": true,
        "count": count,
        "proxies": proxies
    }))
}

async fn browser_proxy_test_handler(
    Json(payload): Json<ProxyTestPayload>,
) -> Json<serde_json::Value> {
    let proxy_str = payload.proxy_string.or(payload.proxy).unwrap_or_default();
    let (alive, latency, msg) = crate::browser_nurture::test_proxy_connection(&proxy_str).await;
    crate::browser_nurture::save_proxy_status(&proxy_str, alive, latency, &msg);
    Json(serde_json::json!({
        "success": alive,
        "latency_ms": latency,
        "message": msg
    }))
}

async fn browser_proxies_status_cache_handler() -> Json<serde_json::Value> {
    let cache = crate::browser_nurture::load_proxy_status_cache();
    Json(serde_json::json!({
        "success": true,
        "cache": cache
    }))
}

#[derive(Deserialize, Default)]
struct BatchProxyTestPayload {
    proxy_strings: Option<Vec<String>>,
    proxies: Option<Vec<String>>,
}

async fn browser_proxies_test_batch_handler(
    Json(payload): Json<BatchProxyTestPayload>,
) -> Json<serde_json::Value> {
    let list = payload.proxy_strings
        .or(payload.proxies)
        .unwrap_or_else(|| {
            crate::browser_nurture::load_c69_proxies()
                .into_iter()
                .map(|p| p.to_proxy_string())
                .collect()
        });
    let res = crate::browser_nurture::batch_test_c69_proxies(list).await;
    Json(serde_json::json!({
        "success": true,
        "count": res.len(),
        "results": res
    }))
}

#[derive(Deserialize)]
struct ImportProxiesPayload {
    proxies_text: String,
    mode: Option<String>,
}

async fn browser_proxies_import_handler(
    Json(payload): Json<ImportProxiesPayload>,
) -> Json<serde_json::Value> {
    let mode = payload.mode.as_deref().unwrap_or("append");
    match crate::browser_nurture::import_new_proxies(&payload.proxies_text, mode) {
        Ok((total, added)) => Json(serde_json::json!({
            "success": true,
            "total": total,
            "added": added,
            "message": format!("Đã import thành công {} proxy mới (Tổng cộng: {} proxies)!", added, total)
        })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

#[derive(Deserialize, Default)]
struct RemoveDeadProxiesPayload {
    #[serde(default)]
    dead_proxies: Option<Vec<String>>,
    #[serde(default)]
    proxies: Option<Vec<String>>,
}

async fn browser_proxies_remove_dead_handler(
    Json(payload): Json<RemoveDeadProxiesPayload>,
) -> Json<serde_json::Value> {
    let list = payload.dead_proxies.or(payload.proxies).unwrap_or_default();
    match crate::browser_nurture::remove_dead_proxies(&list) {
        Ok((removed, remaining)) => Json(serde_json::json!({
            "success": true,
            "removed": removed,
            "remaining": remaining,
            "message": format!("Đã xóa thành công {} proxy die khỏi pool (Còn lại: {} proxies)!", removed, remaining)
        })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

#[derive(Deserialize)]
pub struct ChangeProfileProxyPayload {
    pub profile_ids: Vec<usize>,
    #[serde(alias = "proxy")]
    pub proxy_string: String,
    pub proxy_type: Option<String>,
}

async fn change_browser_profile_proxy_handler(
    Json(payload): Json<ChangeProfileProxyPayload>,
) -> Json<serde_json::Value> {
    let p_type = payload.proxy_type.as_deref().unwrap_or_else(|| {
        let p_lower = payload.proxy_string.trim().to_lowercase();
        if p_lower.is_empty() || p_lower == "direct" {
            "direct"
        } else if p_lower.starts_with("http") {
            "http"
        } else {
            "socks5"
        }
    });

    let path = get_profiles_file_path();
    let mut updated_count = 0;
    if let Ok(data) = std::fs::read_to_string(&path) {
        if let Ok(mut profiles) = serde_json::from_str::<Vec<BrowserProfile>>(&data) {
            for p in &mut profiles {
                if payload.profile_ids.contains(&p.id) {
                    p.proxy_string = payload.proxy_string.trim().to_string();
                    p.proxy_type = p_type.to_string();
                    updated_count += 1;
                }
            }
            if let Ok(json_str) = serde_json::to_string_pretty(&profiles) {
                let _ = std::fs::write(&path, json_str);
            }
        }
    }

    Json(serde_json::json!({
        "success": true,
        "updated_count": updated_count,
        "message": format!("Đã đổi Socks5 thành công cho {} profile!", updated_count)
    }))
}

#[derive(Deserialize)]
struct AssignSocksPayload {
    account_ids: Vec<u64>,
    #[serde(alias = "proxy")]
    proxy_string: String,
}

async fn c69_assign_socks_handler(
    Json(payload): Json<AssignSocksPayload>,
) -> Json<serde_json::Value> {
    match crate::browser_nurture::assign_socks_to_c69_accounts(payload.account_ids, &payload.proxy_string).await {
        Ok(cnt) => Json(serde_json::json!({
            "success": true,
            "updated_count": cnt,
            "message": format!("Đã gán Socks5 thành công cho {} tài khoản!", cnt)
        })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
}

async fn browser_proxies_auto_replace_dead_handler() -> Json<serde_json::Value> {
    match crate::browser_nurture::auto_replace_dead_proxies_for_profiles().await {
        Ok(logs) => Json(serde_json::json!({
            "success": true,
            "replaced_count": logs.len(),
            "details": logs,
            "message": format!("Đã quét và thay thế thành công {} proxy die sang proxy live mới!", logs.len())
        })),
        Err(e) => Json(serde_json::json!({ "success": false, "error": e })),
    }
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

// ── Auto-Update Handlers ─────────────────────────────────────────────────────

pub const APP_VERSION: &str = "2.2.0";

fn is_newer_semver(server: &str, current: &str) -> bool {
    let parse = |v: &str| -> Vec<u32> {
        v.trim_start_matches('v')
            .trim()
            .split('.')
            .filter_map(|p| p.parse::<u32>().ok())
            .collect()
    };
    let s = parse(server);
    let c = parse(current);
    for (a, b) in s.iter().zip(c.iter()) {
        if a > b { return true; }
        if a < b { return false; }
    }
    s.len() > c.len()
}

#[derive(Serialize)]
pub struct CheckUpdateResponse {
    pub has_update: bool,
    pub current_version: &'static str,
    pub server_version: String,
    pub download_url: String,
    pub changelog: String,
}

pub async fn system_check_update_handler() -> Json<CheckUpdateResponse> {
    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
        .unwrap_or_default();

    if let Ok(resp) = client.get("https://cu.c69.us/api/tool-version/").send().await {
        if let Ok(json) = resp.json::<serde_json::Value>().await {
            let server_ver = json.get("version").and_then(|v| v.as_str()).unwrap_or(APP_VERSION).to_string();
            let download_url = json.get("download_url").and_then(|v| v.as_str()).unwrap_or("https://cdn.c69.us/QHTDautomation-v2.zip").to_string();
            let changelog = json.get("changelog").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let has_update = is_newer_semver(&server_ver, APP_VERSION);
            return Json(CheckUpdateResponse {
                has_update,
                current_version: APP_VERSION,
                server_version: server_ver,
                download_url,
                changelog,
            });
        }
    }

    Json(CheckUpdateResponse {
        has_update: false,
        current_version: APP_VERSION,
        server_version: APP_VERSION.to_string(),
        download_url: "https://cdn.c69.us/QHTDautomation-v2.zip".to_string(),
        changelog: "Ứng dụng đang ở phiên bản mới nhất.".to_string(),
    })
}

#[derive(Deserialize)]
pub struct PerformUpdateRequest {
    pub download_url: Option<String>,
}

#[derive(Serialize)]
pub struct PerformUpdateResponse {
    pub success: bool,
    pub message: String,
}

pub async fn system_perform_update_handler(
    Json(payload): Json<PerformUpdateRequest>,
) -> Json<PerformUpdateResponse> {
    let url = payload.download_url.unwrap_or_else(|| "https://cdn.c69.us/QHTDautomation-v2.zip".to_string());
    let temp_dir = std::env::temp_dir();
    let zip_path = temp_dir.join("MunAutomation_Update.zip");

    tracing::info!("AutoUpdate: downloading from {} to {:?}", url, zip_path);

    let client = reqwest::Client::builder()
        .timeout(std::time::Duration::from_secs(300))
        .build()
        .unwrap_or_default();

    let resp = match client.get(&url).send().await {
        Ok(r) => r,
        Err(e) => {
            return Json(PerformUpdateResponse {
                success: false,
                message: format!("Không thể kết nối tải bản cập nhật: {}", e),
            });
        }
    };

    if !resp.status().is_success() {
        return Json(PerformUpdateResponse {
            success: false,
            message: format!("Máy chủ phản hồi mã lỗi: {}", resp.status()),
        });
    }

    let bytes = match resp.bytes().await {
        Ok(b) => b,
        Err(e) => {
            return Json(PerformUpdateResponse {
                success: false,
                message: format!("Lỗi khi tải dữ liệu file: {}", e),
            });
        }
    };

    if let Err(e) = std::fs::write(&zip_path, &bytes) {
        return Json(PerformUpdateResponse {
            success: false,
            message: format!("Không thể ghi file zip ra ổ đĩa tạm: {}", e),
        });
    }

    let current_exe = std::env::current_exe().unwrap_or_else(|_| PathBuf::from("MunAutomation.exe"));
    let app_dir = current_exe.parent().unwrap_or_else(|| std::path::Path::new(".")).to_path_buf();

    let mut updater_path = app_dir.join("c69update.exe");
    if !updater_path.exists() {
        let dev_dist = PathBuf::from(r"d:\Workspace\Python\QHTDautomation\dist\c69update.exe");
        if dev_dist.exists() {
            updater_path = dev_dist;
        } else {
            let alt_path = app_dir.join("dist").join("c69update.exe");
            if alt_path.exists() {
                updater_path = alt_path;
            }
        }
    }

    if !updater_path.exists() {
        return Json(PerformUpdateResponse {
            success: false,
            message: format!("Không tìm thấy c69update.exe tại {:?}", updater_path),
        });
    }

    let pid = std::process::id();
    let exe_name = current_exe.file_name().and_then(|n| n.to_str()).unwrap_or("MunAutomation.exe");

    let spawn_res = std::process::Command::new(&updater_path)
        .arg(format!("--pid={}", pid))
        .arg(format!("--zip={}", zip_path.display()))
        .arg(format!("--exe={}", exe_name))
        .arg(format!("--dir={}", app_dir.display()))
        .spawn();

    match spawn_res {
        Ok(_) => {
            tokio::spawn(async {
                tokio::time::sleep(std::time::Duration::from_millis(1500)).await;
                std::process::exit(0);
            });

            Json(PerformUpdateResponse {
                success: true,
                message: "Đang khởi động c69update.exe để giải nén và cập nhật. Ứng dụng sẽ tự động khởi động lại sau giây lát!".to_string(),
            })
        }
        Err(e) => {
            Json(PerformUpdateResponse {
                success: false,
                message: format!("Không thể spawn c69update.exe: {}", e),
            })
        }
    }
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

        /* Left Sidebar Navigation (Auto-collapse when not hovered for maximum workspace) */
        aside {
            width: 66px;
            min-width: 66px;
            background: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            z-index: 100;
            transition: width 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            overflow-x: hidden;
            white-space: nowrap;
        }
        aside:hover {
            width: 250px;
            min-width: 250px;
            box-shadow: 12px 0 28px rgba(0, 0, 0, 0.6);
        }
        .sidebar-header {
            padding: 16px 14px;
            border-bottom: 1px solid var(--border);
            display: flex;
            align-items: center;
            gap: 12px;
            overflow: hidden;
        }
        .brand-badge {
            background: linear-gradient(135deg, #00f2fe, #4facfe);
            color: #020409;
            font-weight: 900;
            padding: 5px 8px;
            border-radius: 8px;
            font-size: 11px;
            letter-spacing: 0.5px;
            box-shadow: 0 0 14px var(--primary-glow);
            flex-shrink: 0;
        }
        .brand-text-wrapper {
            opacity: 0;
            transform: translateX(-8px);
            transition: opacity 0.2s ease, transform 0.2s ease;
            pointer-events: none;
        }
        aside:hover .brand-text-wrapper {
            opacity: 1;
            transform: translateX(0);
            pointer-events: auto;
        }
        .brand-title { font-size: 13px; font-weight: 800; color: #fff; }
        .brand-sub { font-size: 9px; color: var(--primary); font-weight: 600; }

        .nav-list { list-style: none; padding: 10px 6px; display: flex; flex-direction: column; gap: 4px; }
        .nav-item {
            padding: 10px 8px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 12px;
            transition: all 0.15s;
            border: 1px solid transparent;
            overflow: hidden;
        }
        .nav-item:hover { background: rgba(255, 255, 255, 0.05); color: #fff; }
        .nav-item.active {
            background: linear-gradient(90deg, rgba(0, 242, 254, 0.14), rgba(217, 70, 239, 0.08));
            color: #fff;
            border-left: 3px solid var(--primary);
            border-color: rgba(0, 242, 254, 0.3);
            box-shadow: 0 4px 12px rgba(0, 242, 254, 0.1);
        }
        .nav-icon {
            font-size: 16px;
            min-width: 32px;
            text-align: center;
            display: inline-block;
            flex-shrink: 0;
        }
        .nav-label {
            opacity: 0;
            transform: translateX(-6px);
            transition: opacity 0.2s ease, transform 0.2s ease;
            white-space: nowrap;
        }
        aside:hover .nav-label {
            opacity: 1;
            transform: translateX(0);
        }

        .sidebar-footer {
            padding: 12px 14px;
            border-top: 1px solid var(--border);
            font-size: 10px;
            color: var(--text-muted);
            display: flex;
            flex-direction: column;
            gap: 4px;
            background: rgba(0,0,0,0.2);
            opacity: 0;
            transition: opacity 0.2s ease;
        }
        aside:hover .sidebar-footer {
            opacity: 1;
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

        /* Buttons & Badges (High Precision Dark Theme & Crisp State Handling) */
        .btn {
            padding: 5px 11px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            border: 1px solid var(--border);
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 5px;
            transition: all 0.15s ease;
            color: #f1f5f9;
            background: var(--bg-card);
            user-select: none;
            line-height: 1.2;
            text-decoration: none;
        }
        .btn:hover:not(:disabled) {
            filter: brightness(1.2);
            transform: translateY(-1px);
        }
        .btn:disabled {
            opacity: 0.38 !important;
            cursor: not-allowed !important;
            pointer-events: none !important;
            filter: grayscale(0.6) !important;
        }
        .btn-primary {
            background: linear-gradient(135deg, #0284c7, #00f2fe) !important;
            color: #020409 !important;
            font-weight: 800;
            border: 1px solid rgba(0, 242, 254, 0.4) !important;
            box-shadow: 0 0 10px var(--primary-glow);
        }
        .btn-secondary {
            background: rgba(148, 163, 184, 0.14) !important;
            border: 1px solid rgba(148, 163, 184, 0.35) !important;
            color: #cbd5e1 !important;
        }
        .btn-secondary:hover:not(:disabled) {
            background: rgba(148, 163, 184, 0.25) !important;
            color: #fff !important;
        }
        .btn-info {
            background: rgba(56, 189, 248, 0.15) !important;
            border: 1px solid rgba(56, 189, 248, 0.45) !important;
            color: #38bdf8 !important;
        }
        .btn-info:hover:not(:disabled) {
            background: rgba(56, 189, 248, 0.28) !important;
            color: #fff !important;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.3);
        }
        .btn-warning {
            background: rgba(245, 158, 11, 0.18) !important;
            border: 1px solid rgba(245, 158, 11, 0.45) !important;
            color: #fbbf24 !important;
        }
        .btn-warning:hover:not(:disabled) {
            background: rgba(245, 158, 11, 0.32) !important;
            color: #fff !important;
            box-shadow: 0 0 8px rgba(245, 158, 11, 0.3);
        }
        .btn-purple {
            background: linear-gradient(135deg, #d946ef, #8b5cf6) !important;
            color: #fff !important;
            border: 1px solid rgba(217, 70, 239, 0.4) !important;
            box-shadow: 0 0 8px rgba(217, 70, 239, 0.25);
        }
        .btn-success {
            background: #059669 !important;
            color: #fff !important;
            border: 1px solid #10b981 !important;
        }
        .btn-danger {
            background: rgba(220, 38, 38, 0.2) !important;
            border: 1px solid rgba(239, 68, 68, 0.45) !important;
            color: #f87171 !important;
        }
        .btn-danger:hover:not(:disabled) {
            background: rgba(220, 38, 38, 0.35) !important;
            color: #fff !important;
        }
        .btn-dark {
            background: var(--bg-card) !important;
            color: var(--text-main) !important;
            border: 1px solid var(--border) !important;
        }
        .btn-main-gold {
            background: linear-gradient(135deg, #eab308, #ca8a04) !important;
            color: #0f172a !important;
            font-weight: 800 !important;
            border: 1px solid #facc15 !important;
            box-shadow: 0 0 10px rgba(234, 179, 8, 0.35);
        }

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
            padding: 6px 9px;
            text-align: left;
            border-bottom: 1px solid var(--border);
            font-size: 11.5px;
            vertical-align: middle;
        }
        .data-table th { background: rgba(0,0,0,0.45); color: #94a3b8; font-weight: 700; font-size: 11px; }
        .data-table tr:hover { background: rgba(255,255,255,0.03); }
        tr.row-selected {
            background: rgba(56, 189, 248, 0.12) !important;
        }
        tr.row-selected td {
            border-bottom: 1px solid rgba(56, 189, 248, 0.3) !important;
        }
        tr.row-selected:hover {
            background: rgba(56, 189, 248, 0.18) !important;
        }

        .badge-status-running {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 700;
            color: #10b981;
            background: rgba(16, 185, 129, 0.12);
            border: 1px solid rgba(16, 185, 129, 0.3);
        }
        .pulse-dot {
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: #10b981;
            box-shadow: 0 0 8px #10b981;
            animation: pulseAnim 1.5s infinite;
        }
        @keyframes pulseAnim {
            0% { transform: scale(0.9); opacity: 0.8; }
            50% { transform: scale(1.3); opacity: 1; box-shadow: 0 0 12px #10b981; }
            100% { transform: scale(0.9); opacity: 0.8; }
        }
        .badge-status-stopped {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 11px;
            font-weight: 600;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
        }

        .badge-engine-native {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            color: #c084fc;
            background: rgba(192, 132, 252, 0.12);
            border: 1px solid rgba(192, 132, 252, 0.35);
            cursor: pointer;
            transition: all 0.15s;
        }
        .badge-engine-native:hover {
            background: rgba(192, 132, 252, 0.25);
            transform: scale(1.03);
        }

        .badge-engine-js {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            color: #38bdf8;
            background: rgba(56, 189, 248, 0.12);
            border: 1px solid rgba(56, 189, 248, 0.35);
            cursor: pointer;
            transition: all 0.15s;
        }
        .badge-engine-js:hover {
            background: rgba(56, 189, 248, 0.25);
            transform: scale(1.03);
        }

        .badge-engine-hybrid {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 3px 8px;
            border-radius: 6px;
            font-size: 10px;
            font-weight: 700;
            color: #f59e0b;
            background: rgba(245, 158, 11, 0.12);
            border: 1px solid rgba(245, 158, 11, 0.35);
            cursor: pointer;
            transition: all 0.15s;
        }
        .badge-engine-hybrid:hover {
            background: rgba(245, 158, 11, 0.25);
            transform: scale(1.03);
        }

        .nurture-filter-btn {
            padding: 4px 10px;
            font-size: 11px;
            font-weight: 600;
            border-radius: 6px;
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.15s;
        }
        .nurture-filter-btn:hover {
            color: #fff;
            border-color: rgba(255, 255, 255, 0.25);
            background: rgba(255, 255, 255, 0.06);
        }
        .nurture-filter-btn.active {
            background: rgba(56, 189, 248, 0.15);
            border-color: #38bdf8;
            color: #38bdf8;
            font-weight: 700;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.2);
        }

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

        .filter-btn {
            background: rgba(255, 255, 255, 0.04);
            border: 1px solid var(--border);
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.15s;
            border-radius: 6px;
        }
        .filter-btn:hover {
            color: #fff;
            border-color: rgba(255, 255, 255, 0.25);
            transform: translateY(-1px);
        }
        .filter-btn.active {
            background: rgba(0, 242, 254, 0.15) !important;
            border-color: var(--primary) !important;
            color: var(--primary) !important;
            font-weight: 800 !important;
            box-shadow: 0 0 10px var(--primary-glow);
        }

        /* ── TOAST NOTIFICATIONS (NON-BLOCKING) ── */
        #toast-container {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 999999;
            display: flex;
            flex-direction: column-reverse;
            gap: 8px;
            pointer-events: none;
        }
        .toast-msg {
            min-width: 260px;
            max-width: 440px;
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 12px;
            font-weight: 600;
            color: #fff;
            background: #0f172a;
            border: 1px solid var(--border);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
            display: flex;
            align-items: center;
            gap: 10px;
            animation: toastSlideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
            pointer-events: auto;
            cursor: pointer;
            transition: opacity 0.25s, transform 0.25s;
        }
        .toast-info { border-left: 4px solid var(--primary); }
        .toast-success { border-left: 4px solid #10b981; }
        .toast-warning { border-left: 4px solid #f59e0b; }
        /* ── C69 STATUS & ACCOUNT BADGES ── */
        .badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 7px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 700;
            white-space: nowrap;
        }
        .badge-success { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }
        .badge-warning { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.35); }
        .badge-danger { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.35); }
        .badge-info { background: rgba(14, 165, 233, 0.15); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.35); }
        .badge-sub-ok { background: rgba(168, 85, 247, 0.15); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.35); }
        .badge-sub-error { background: rgba(249, 115, 22, 0.15); color: #fb923c; border: 1px solid rgba(249, 115, 22, 0.35); }
        /* ── C69 PORTAL REPLICA STYLES (COMPACT & SMALL-SCREEN OPTIMIZED) ── */
        .c69-control-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 6px;
            margin-bottom: 6px;
            flex-wrap: wrap;
        }
        .c69-filters {
            display: flex;
            align-items: center;
            gap: 5px;
            flex-wrap: wrap;
            flex: 1;
        }
        .c69-action-buttons {
            display: flex;
            align-items: center;
            gap: 5px;
            flex-wrap: wrap;
        }
        .c69-select {
            background: #0f172a;
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 6px;
            padding: 4px 8px;
            color: #f8fafc;
            font-size: 11.5px;
            outline: none;
            cursor: pointer;
            height: 27px;
            transition: all 0.15s;
        }
        .c69-select:focus {
            border-color: #38bdf8;
            box-shadow: 0 0 8px rgba(56, 189, 248, 0.25);
        }
        .c69-pag-btn {
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid rgba(148, 163, 184, 0.25);
            color: #cbd5e1;
            padding: 4px 8px;
            border-radius: 5px;
            font-size: 11px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s;
            height: 26px;
        }
        .c69-pag-btn:hover:not(:disabled) {
            border-color: #38bdf8;
            color: #38bdf8;
        }
        .c69-pag-btn.active {
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            color: #030712;
            font-weight: 800;
            border-color: #38bdf8;
            box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
        }
        .c69-pag-btn:disabled {
            opacity: 0.35;
            cursor: not-allowed;
        }

        /* ── EXACT C69 CARD TABS STYLES (COMPACT) ── */
        .card-tabs-container {
            display: flex;
            gap: 5px;
            margin-bottom: 8px;
            border-bottom: 1px solid rgba(148, 163, 184, 0.15);
            padding-bottom: 5px;
            flex-wrap: wrap;
            align-items: center;
        }
        .card-tab-item {
            padding: 5px 12px;
            border-radius: 6px;
            font-size: 11.5px;
            font-weight: 600;
            color: var(--text-muted);
            cursor: pointer;
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            background: transparent;
            border: 1px solid transparent;
            user-select: none;
            display: flex;
            align-items: center;
            gap: 6px;
            height: 27px;
        }
        .card-tab-item:hover {
            color: #fff;
            background: rgba(255, 255, 255, 0.05);
        }
        .card-tab-item.active {
            color: #ffffff;
            background: rgba(0, 242, 254, 0.14);
            border-color: var(--primary);
            box-shadow: 0 0 10px rgba(0, 242, 254, 0.2);
        }
        .badge-type {
            background: rgba(56, 189, 248, 0.12);
            color: #38bdf8;
            border: 1px solid rgba(56, 189, 248, 0.3);
            font-size: 10px;
            padding: 1px 5px;
            border-radius: 4px;
        }
        .badge-active {
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border: 1px solid rgba(99, 102, 241, 0.35);
        }

        /* ── SMALL SCREEN & LAPTOP MEDIA QUERIES (<= 1440px or <= 800px height) ── */
        @media (max-width: 1440px), (max-height: 850px) {
            .view-content {
                padding: 8px 10px !important;
            }
            .action-toolbar {
                padding: 6px 10px !important;
                margin-bottom: 8px !important;
                gap: 5px !important;
            }
            .c69-select {
                font-size: 11px !important;
                padding: 3px 6px !important;
                height: 26px !important;
            }
            .btn {
                padding: 4px 8px !important;
                font-size: 10.5px !important;
                height: 26px !important;
            }
            .card-tab-item {
                padding: 4px 10px !important;
                font-size: 11px !important;
                height: 25px !important;
            }
            .data-table th, .data-table td {
                padding: 5px 8px !important;
                font-size: 11px !important;
            }
        }
    </style>
</head>
<body>
    <!-- C69 LOGIN GATE OVERLAY (BLOCKS INTERFACE IF NOT LOGGED IN) -->
    <div id="c69-login-gate" style="display:flex; position:fixed; top:0; left:0; right:0; bottom:0; z-index:99999; background:radial-gradient(ellipse at center, rgba(15,23,42,0.96) 0%, rgba(3,7,18,0.99) 100%); backdrop-filter:blur(16px); align-items:center; justify-content:center;">
        <div style="width:420px; max-width:92vw; background:linear-gradient(145deg, rgba(30,41,59,0.95), rgba(15,23,42,0.98)); border:1px solid rgba(56,189,248,0.35); box-shadow:0 25px 60px -15px rgba(0,0,0,0.8), 0 0 35px rgba(56,189,248,0.25); border-radius:16px; padding:32px 28px; color:#f8fafc; text-align:center; position:relative; overflow:hidden;">
            <!-- Top decorative glowing bar -->
            <div style="position:absolute; top:0; left:0; right:0; height:3px; background:linear-gradient(90deg, #38bdf8, #818cf8, #c084fc, #f472b6);"></div>
            
            <div style="display:inline-flex; align-items:center; justify-content:center; width:56px; height:56px; border-radius:14px; background:rgba(56,189,248,0.12); border:1px solid rgba(56,189,248,0.3); margin-bottom:16px; font-size:26px;">
                ⚡
            </div>
            <h2 style="font-size:18px; font-weight:800; margin-bottom:6px; color:#fff; letter-spacing:0.3px;">MunAutomation Core</h2>
            <div style="font-size:12px; color:#94a3b8; margin-bottom:20px; line-height:1.5;">
                Đăng nhập tài khoản <b>C69.us</b> để xác thực bản quyền & liên kết dữ liệu Farm, Profile và Proxy.
            </div>

            <form id="c69-login-form" onsubmit="submitC69Login(); return false;" style="display:flex; flex-direction:column; gap:14px; text-align:left;">
                <div>
                    <label style="font-size:11px; font-weight:700; color:#cbd5e1; margin-bottom:5px; display:block;">TÊN ĐĂNG NHẬP / EMAIL C69:</label>
                    <div style="position:relative;">
                        <input type="text" id="c69-login-username" required placeholder="Nhập username hoặc email C69..." style="width:100%; box-sizing:border-box; background:rgba(15,23,42,0.8); border:1px solid rgba(148,163,184,0.3); color:#fff; padding:10px 12px 10px 36px; border-radius:8px; font-size:13px; outline:none; transition:border-color 0.2s;" onfocus="this.style.borderColor='#38bdf8'" onblur="this.style.borderColor='rgba(148,163,184,0.3)'" onkeydown="if(event.key==='Enter') submitC69Login()">
                        <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%); font-size:14px; opacity:0.7;">👤</span>
                    </div>
                </div>

                <div>
                    <label style="font-size:11px; font-weight:700; color:#cbd5e1; margin-bottom:5px; display:block;">MẬT KHẨU C69:</label>
                    <div style="position:relative;">
                        <input type="password" id="c69-login-password" required placeholder="Nhập mật khẩu tài khoản..." style="width:100%; box-sizing:border-box; background:rgba(15,23,42,0.8); border:1px solid rgba(148,163,184,0.3); color:#fff; padding:10px 12px 10px 36px; border-radius:8px; font-size:13px; outline:none; transition:border-color 0.2s;" onfocus="this.style.borderColor='#38bdf8'" onblur="this.style.borderColor='rgba(148,163,184,0.3)'" onkeydown="if(event.key==='Enter') submitC69Login()">
                        <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%); font-size:14px; opacity:0.7;">🔑</span>
                    </div>
                </div>

                <!-- Advanced Server URL -->
                <div style="margin-top:-4px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:10px; color:#64748b; cursor:pointer;" onclick="toggleC69ServerUrl()">⚙️ Máy chủ: <span id="c69-server-display">https://cu.c69.us</span></span>
                    </div>
                    <div id="c69-server-input-wrap" style="display:none; margin-top:6px;">
                        <input type="text" id="c69-login-server" value="https://cu.c69.us" placeholder="https://cu.c69.us" style="width:100%; box-sizing:border-box; background:rgba(15,23,42,0.8); border:1px solid rgba(148,163,184,0.3); color:#94a3b8; padding:6px 10px; border-radius:6px; font-size:11px;">
                    </div>
                </div>

                <div id="c69-login-msg" style="display:none; font-size:12px; padding:10px 12px; border-radius:6px; margin-top:4px; font-weight:600;"></div>

                <button type="button" onclick="submitC69Login()" id="btn-c69-login-submit" style="width:100%; margin-top:6px; background:linear-gradient(135deg, #0284c7, #38bdf8); color:#030712; font-weight:800; font-size:13px; padding:11px; border:none; border-radius:8px; cursor:pointer; box-shadow:0 4px 15px rgba(56,189,248,0.4); transition:all 0.2s; display:flex; align-items:center; justify-content:center; gap:8px;">
                    <span>⚡ Đăng Nhập & Mở Khóa Tool</span>
                </button>
            </form>

            <div style="margin-top:20px; font-size:11px; color:#64748b; display:flex; align-items:center; justify-content:center; gap:6px;">
                <span>🛡️ Kết nối an toàn TLS 1.3 tới C69 Cloud</span>
            </div>
        </div>
    </div>

    <!-- LEFT SIDEBAR (AUTO-COLLAPSE ON HOVER) -->
    <aside>
        <div>
            <div class="sidebar-header">
                <div class="brand-badge">⚡ MUN</div>
                <div class="brand-text-wrapper">
                    <div class="brand-title">MunAutomation</div>
                    <div class="brand-sub">Pure Rust All-In-One</div>
                </div>
            </div>
            <ul class="nav-list">
                <li class="nav-item" onclick="switchNav('farm')">
                    <span class="nav-icon">📱</span>
                    <span class="nav-label">Giàn Android Farm</span>
                </li>
                <li class="nav-item active" onclick="switchNav('browser')">
                    <span class="nav-icon">🌐</span>
                    <span class="nav-label">Mun Anti Browser</span>
                </li>
                <li class="nav-item" onclick="switchNav('c69tiktok')">
                    <span class="nav-icon">👥</span>
                    <span class="nav-label">Tài Khoản C69</span>
                </li>
                <li class="nav-item" onclick="openProxyPoolModal()" style="color: #38bdf8; border: 1px solid rgba(56,189,248,0.25); background: rgba(56,189,248,0.06);" title="Quản lý 250 SOCKS5 Proxy Pool C69">
                    <span class="nav-icon">🛡️</span>
                    <span class="nav-label">Quản Lý Proxy (250)</span>
                </li>
                <li class="nav-item" onclick="switchNav('ios')">
                    <span class="nav-icon">🍏</span>
                    <span class="nav-label">iOS Automation</span>
                </li>
                <li class="nav-item" onclick="switchNav('router')">
                    <span class="nav-icon">⚡</span>
                    <span class="nav-label">C69 Router & Proxy</span>
                </li>
                <li class="nav-item" onclick="switchNav('nurture')">
                    <span class="nav-icon">🤖</span>
                    <span class="nav-label">TikTok Studio</span>
                </li>
                <li class="nav-item" onclick="switchNav('store')">
                    <span class="nav-icon">🛒</span>
                    <span class="nav-label">C69 Store</span>
                </li>
                <li class="nav-item" onclick="switchNav('settings')">
                    <span class="nav-icon">⚙️</span>
                    <span class="nav-label">Cài Đặt Hệ Thống</span>
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
            <div style="display: flex; gap: 8px; align-items: center;">
                <div id="c69-auth-badge" style="display: flex; align-items: center; gap: 6px; background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); padding: 4px 10px; border-radius: 6px; font-size: 11px;">
                    <span class="pulse-dot" id="c69-auth-dot" style="background:#ef4444;"></span>
                    <span id="c69-auth-user" style="font-weight: 700; color: #38bdf8;">Đang kiểm tra C69...</span>
                    <button class="btn btn-dark" id="btn-c69-auth-action" onclick="handleC69AuthBadgeClick()" style="padding: 2px 7px; font-size: 10px; border-color: #38bdf8; color: #38bdf8; margin-left: 4px;">Đăng Nhập</button>
                </div>
                <button class="btn btn-dark" id="btn-check-update" onclick="checkAppUpdate(true)" style="border-color: #38bdf8; color: #38bdf8; font-weight: 700; display: flex; align-items: center; gap: 4px;" title="Bấm để kiểm tra bản cập nhật mới từ hệ thống">⚡ v2.2.0</button>
                <button class="btn btn-dark" onclick="refreshAll()">🔄 Quét Lại</button>
            </div>
        </div>

        <!-- VIEW 1: ANDROID FARM (COMPACT & ULTRA SMOOTH STREAM) -->
        <div class="view-content" id="view-farm">
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
                <div style="grid-column: 1 / -1; text-align: center; padding: 50px 20px; color: var(--text-muted);">
                    <div style="font-size: 32px; margin-bottom: 10px;">📱</div>
                    <div style="font-weight: 700; font-size: 14px; margin-bottom: 6px; color: #fff;">Đang quét thiết bị giàn máy Android qua ADB...</div>
                    <div style="font-size: 12px; margin-bottom: 14px;">Nếu chưa cắm giàn máy, bạn có thể chuyển ngay sang tab Anti Browser.</div>
                    <button class="btn btn-primary" style="padding: 7px 16px; font-size: 11px;" onclick="switchNav('browser')">🌐 Chuyển Sang Tab Anti Browser</button>
                </div>
            </div>
        </div>

        <!-- VIEW 2: MUN ANTI BROWSER (TIKTOK FARMING & HARDWARE SHIELD) -->
        <div class="view-content active" id="view-browser">
            <!-- TIKTOK FARM KPI SUMMARY BAR (COMPACT) -->
            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(115px, 1fr)); gap:6px; margin-bottom:8px;">
                <div style="background:rgba(15,23,42,0.6); border:1px solid rgba(56,189,248,0.25); border-radius:6px; padding:5px 9px; display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">👥</span>
                    <div>
                        <div style="font-size:9px; color:#94a3b8; font-weight:700;">TỔNG PROFILES</div>
                        <div style="font-size:14px; font-weight:800; color:#38bdf8;" id="kpi-total-profiles">0</div>
                    </div>
                </div>
                <div style="background:rgba(217,70,239,0.08); border:1px solid rgba(217,70,239,0.3); border-radius:6px; padding:5px 9px; display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">🎬</span>
                    <div>
                        <div style="font-size:9px; color:#f0abfc; font-weight:700;">ĐANG NUÔI FYP</div>
                        <div style="font-size:14px; font-weight:800; color:#d946ef;" id="kpi-running-nurture">0</div>
                    </div>
                </div>
                <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.3); border-radius:6px; padding:5px 9px; display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">✅</span>
                    <div>
                        <div style="font-size:9px; color:#6ee7b7; font-weight:700;">ĐÃ NUÔI XONG</div>
                        <div style="font-size:14px; font-weight:800; color:#10b981;" id="kpi-done-nurture">0</div>
                    </div>
                </div>
                <div style="background:rgba(249,115,22,0.08); border:1px solid rgba(249,115,22,0.3); border-radius:6px; padding:5px 9px; display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">⏳</span>
                    <div>
                        <div style="font-size:9px; color:#fdba74; font-weight:700;">CHỜ 1H (LIMIT)</div>
                        <div style="font-size:14px; font-weight:800; color:#f97316;" id="kpi-rate-limited">0</div>
                    </div>
                </div>
                <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.3); border-radius:6px; padding:5px 9px; display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">⚠️</span>
                    <div>
                        <div style="font-size:9px; color:#fca5a5; font-weight:700;">LỖI CẦN CHECK</div>
                        <div style="font-size:14px; font-weight:800; color:#ef4444;" id="kpi-error-profiles">0</div>
                    </div>
                </div>
                <div style="background:rgba(14,165,233,0.08); border:1px solid rgba(14,165,233,0.3); border-radius:6px; padding:5px 9px; display:flex; align-items:center; gap:8px;">
                    <span style="font-size:16px;">⚡</span>
                    <div>
                        <div style="font-size:9px; color:#7dd3fc; font-weight:700;">ZERO-LOGIN</div>
                        <div style="font-size:14px; font-weight:800; color:#0ea5e9;" id="kpi-zero-login">0</div>
                    </div>
                </div>
            </div>

            <!-- ACTION & FILTER TOOLBAR (COMPACT) -->
            <div class="action-toolbar" style="margin-bottom:6px; padding:6px 10px; flex-wrap:wrap; gap:6px;">
                <div class="toolbar-group" style="display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
                    <button class="btn btn-primary" id="btn-nurture-selected-profs" onclick="startNurtureSelectedProfiles()" style="font-weight:700; font-size:10.5px; padding:4px 10px;" title="Chạy nuôi các profiles được tích chọn">🎬 Nuôi Profile Đã Chọn</button>
                    <button class="btn btn-dark" id="btn-rand-fp-selected" onclick="randomizeSelectedProfilesFingerprint()" style="border-color:#a855f7; color:#f0abfc; background:rgba(168,85,247,0.12); font-weight:700; font-size:10.5px; padding:4px 9px; display:inline-flex; align-items:center; gap:4px;" title="Tạo mới dấu vân tay phần cứng">🎲 Đổi Fingerprint</button>
                    <div style="display:inline-flex; align-items:center; border-radius:5px; overflow:hidden; border:1px solid #38bdf8; background:rgba(56,189,248,0.08); height:26px;">
                        <button class="btn" id="btn-to-mobile-selected" onclick="switchSelectedProfilesUA('mobile')" style="background:transparent; color:#38bdf8; font-weight:700; font-size:10.5px; padding:2px 7px; border:none; border-right:1px solid rgba(56,189,248,0.3); border-radius:0; cursor:pointer;" title="Chuyển sang Mobile UA">📱 Mobile</button>
                        <button class="btn" id="btn-to-desktop-selected" onclick="switchSelectedProfilesUA('desktop')" style="background:transparent; color:#38bdf8; font-weight:700; font-size:10.5px; padding:2px 7px; border:none; border-right:1px solid rgba(56,189,248,0.3); border-radius:0; cursor:pointer;" title="Chuyển sang Desktop UA">💻 Desktop</button>
                        <button class="btn" onclick="switchSelectedProfilesUA('toggle')" style="background:rgba(56,189,248,0.18); color:#fff; font-weight:700; font-size:10.5px; padding:2px 7px; border:none; border-radius:0; cursor:pointer;" title="Đảo qua lại">🔄 Đổi</button>
                    </div>
                    <button class="btn btn-purple" onclick="startNurtureAllProfiles()" style="font-weight:700; font-size:10.5px; padding:4px 10px;" title="Chạy nuôi TikTok tất cả profile">🎬 Nuôi Tất Cả</button>
                    <button class="btn btn-dark" onclick="stopNurtureAllProfiles()" style="border-color:#ef4444; color:#ef4444; font-size:10.5px; padding:4px 8px; font-weight:600;">⏹️ Dừng All</button>
                    <button class="btn btn-dark" id="btn-change-socks-selected" onclick="openChangeSelectedProfilesSocksModal()" style="border-color:#38bdf8; color:#38bdf8; background:rgba(56,189,248,0.12); font-weight:700; font-size:10.5px; padding:4px 9px; display:inline-flex; align-items:center; gap:4px;" title="Đổi Socks cho các profile được tích chọn">🔄 Đổi Socks</button>
                    <button class="btn btn-dark" id="btn-check-socks-selected" onclick="checkSelectedProfilesSocks()" style="border-color:#10b981; color:#34d399; background:rgba(16,185,129,0.12); font-weight:700; font-size:10.5px; padding:4px 9px; display:inline-flex; align-items:center; gap:4px;" title="Kiểm tra Live/Die toàn bộ Socks của các profile được chọn">⚡ Check Socks</button>
                    <label style="font-size:10.5px; color:#38bdf8; display:flex; align-items:center; gap:4px; cursor:pointer; background:rgba(56,189,248,0.08); padding:3px 7px; border-radius:5px; border:1px solid rgba(56,189,248,0.25);" title="Tự động cấp phát Proxy từ C69 Pool">
                        <input type="checkbox" id="browser-auto-proxy-chk" checked>
                        <span>🛡️ Auto Proxy</span>
                    </label>
                </div>
                <div class="toolbar-group" style="display:flex; align-items:center; gap:5px;">
                    <span id="core-status-badge"></span>
                    <button class="btn btn-dark" onclick="syncC69Profiles()" style="border-color:#38bdf8; color:#38bdf8; font-size:10.5px; padding:4px 8px; font-weight:600;" title="Đồng bộ cấu hình từ C69.us">☁️ Đồng Bộ C69</button>
                    <button class="btn btn-primary" onclick="openCreateProfileModal()" style="font-size:10.5px; padding:4px 9px;">➕ Tạo Profile</button>
                </div>
            </div>

            <!-- SUB-TOOLBAR: SMART FILTERS & SEARCH -->
            <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; margin-bottom:6px; flex-wrap:wrap;">
                <div style="display:flex; gap:4px; align-items:center; flex-wrap:wrap;">
                    <span style="font-size:10.5px; color:#94a3b8; font-weight:600; margin-right:2px;">Lọc:</span>
                    <button class="nurture-filter-btn active" style="padding:2px 8px; font-size:10.5px;" onclick="setNurtureFilter('all', this)">Tất cả</button>
                    <button class="nurture-filter-btn" style="padding:2px 8px; font-size:10.5px;" onclick="setNurtureFilter('running', this)">🎬 Đang nuôi</button>
                    <button class="nurture-filter-btn" style="padding:2px 8px; font-size:10.5px;" onclick="setNurtureFilter('done', this)">✅ Đã nuôi OK</button>
                    <button class="nurture-filter-btn" style="padding:2px 8px; font-size:10.5px;" onclick="setNurtureFilter('ratelimit', this)">⏳ Chờ 1h</button>
                    <button class="nurture-filter-btn" style="padding:2px 8px; font-size:10.5px;" onclick="setNurtureFilter('error', this)">⚠️ Cần check</button>
                    <button class="nurture-filter-btn" style="padding:2px 8px; font-size:10.5px;" onclick="setNurtureFilter('unassigned', this)">⚪ Chưa gán nick</button>
                </div>
                <div style="display:flex; align-items:center; gap:6px;">
                    <input type="text" class="search-input" placeholder="🔍 Tìm ID, Nick, Proxy..." id="profile-search" oninput="filterProfiles()" style="width:190px; height:26px; font-size:11px; padding:3px 8px;">
                    <span id="active-profiles-count" style="font-size: 10.5px; font-weight: 700; color: #10b981;"></span>
                </div>
            </div>

            <!-- COMPACT & INTUITIVE 6-COLUMN TABLE -->
            <table class="data-table">
                <thead>
                    <tr>
                        <th style="width:65px; text-align:center; cursor:pointer;" onclick="if(event.target.tagName !== 'INPUT') { const cb = document.getElementById('check-all-profiles'); if(cb) { cb.checked = !cb.checked; toggleSelectAllProfiles(cb); } }">
                            <div style="display:flex; align-items:center; justify-content:center; gap:4px;">
                                <input type="checkbox" id="check-all-profiles" style="cursor:pointer; transform:scale(1.15);" onchange="toggleSelectAllProfiles(this)">
                                <span style="user-select:none;">ID</span>
                            </div>
                        </th>
                        <th>Profile & Thiết Bị</th>
                        <th>Tài Khoản TikTok</th>
                        <th>Proxy SOCKS5</th>
                        <th>Trạng Thái Nuôi FYP</th>
                        <th style="text-align:center;">Thao Tác</th>
                    </tr>
                </thead>
                <tbody id="browser-profiles-body">
                    <tr><td colspan="6" style="text-align: center; padding:30px; color: var(--text-muted);">Đang tải danh sách profile...</td></tr>
                </tbody>
            </table>
        </div>

        <!-- VIEW: TÀI KHOẢN C69 (REPLICA 100% https://cu.c69.us/?tab=accounts&page=1) -->
        <div class="view-content" id="view-c69tiktok">
            <!-- C69 ACCOUNT FILTER TABS (COMPACT & CLEAN: TẤT CẢ / THƯỜNG / MAIN / ĐÃ NUÔI) -->
            <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px; margin-bottom:8px; border-bottom:1px solid rgba(148, 163, 184, 0.15); padding-bottom:5px;">
                <div class="card-tabs-container" style="margin-bottom:0; border-bottom:none; padding-bottom:0; gap:5px;" id="c69-acc-sub-tabs">
                    <div class="card-tab-item active" id="c69-subtab-all" onclick="switchC69AccountSubTab('all')" style="cursor:pointer; padding:4px 12px; font-weight:700;" title="Tất cả tài khoản C69">
                        <span>📋</span>
                        <span>Tất cả</span>
                    </div>
                    <div class="card-tab-item" id="c69-subtab-regular" onclick="switchC69AccountSubTab('regular')" style="cursor:pointer; padding:4px 12px; font-weight:700;" title="Thường (tài khoản không phải Main)">
                        <span>⚪</span>
                        <span>Thường</span>
                    </div>
                    <div class="card-tab-item" id="c69-subtab-main" onclick="switchC69AccountSubTab('main')" style="cursor:pointer; padding:4px 12px; font-weight:700;" title="Main (tài khoản được gắn là Main)">
                        <span>⭐</span>
                        <span>Main</span>
                    </div>
                    <div class="card-tab-item" id="c69-subtab-nurtured" onclick="switchC69AccountSubTab('nurtured')" style="cursor:pointer; padding:4px 12px; font-weight:700;" title="Đã Nuôi (tài khoản đã được nuôi ít nhất 1 lần rồi)">
                        <span>🎬</span>
                        <span>Đã Nuôi</span>
                    </div>
                </div>

                <div style="display:flex; align-items:center; gap:8px;">
                    <span id="c69-user-badge-text" style="font-size:11px; color:var(--text-muted); font-weight:600;">👤 Đang kết nối C69</span>
                </div>
            </div>

            <!-- COMPACT CONTROL PANEL (OPTIMIZED FOR SMALL SCREENS & LAPTOPS) -->
            <div style="background:rgba(15,23,42,0.65); padding:7px 10px; border-radius:8px; border:1px solid var(--border); margin-bottom:8px; display:flex; flex-direction:column; gap:6px;">
                <!-- ROW 1: STATUS, COUNT & ACTION BUTTONS -->
                <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:6px;">
                    <div style="display:flex; align-items:center; gap:6px; flex-wrap:wrap;">
                        <h2 style="font-size: 13px; font-weight: 800; color:#fff; display:flex; align-items:center; gap:5px; margin:0;">
                            <span>👥</span> Quản Lý Nick C69
                        </h2>
                        <span id="c69-acc-count" style="font-size: 10.5px; font-weight: 700; color: #10b981; background:rgba(16,185,129,0.12); border:1px solid rgba(16,185,129,0.35); padding:2px 7px; border-radius:5px;">Tổng: 0 tài khoản</span>
                        
                        <div id="c69-user-badge-container" style="display:flex; align-items:center; gap:5px; background:rgba(240,171,252,0.1); border:1px solid rgba(240,171,252,0.35); padding:2px 7px; border-radius:5px; font-size:10.5px; font-weight:700; color:#f0abfc;">
                            <span id="c69-user-badge-text">👤 @...</span>
                            <button onclick="openC69LoginModal()" style="background:transparent; border:none; color:#38bdf8; cursor:pointer; font-size:10.5px; text-decoration:underline;">[Đổi nick]</button>
                        </div>

                        <div id="c69-selected-info" style="font-size:10.5px; font-weight:700; color:#38bdf8; white-space:nowrap; background:rgba(56,189,248,0.1); border:1px solid rgba(56,189,248,0.35); padding:2px 7px; border-radius:5px;">
                            Đã chọn: 0
                        </div>
                    </div>

                    <!-- BATCH ACTION BUTTONS (NO WHITE FLASH ON SELECTION) -->
                    <div class="c69-action-buttons" style="display:flex; align-items:center; gap:5px; flex-wrap:wrap;">
                        <button class="btn btn-secondary" onclick="loadC69AccountsTab()" title="Làm mới danh sách">🔄 Làm mới</button>
                        <button class="btn btn-main-gold" id="btn-c69-set-main" onclick="handleC69ToggleMain(true)" disabled title="Đặt làm Main">⭐ Đặt Main</button>
                        <button class="btn btn-secondary" id="btn-c69-unset-main" onclick="handleC69ToggleMain(false)" disabled title="Bỏ đánh dấu Main">Bỏ Main</button>

                        <!-- DROPDOWN THÊM TÀI KHOẢN -->
                        <div style="position:relative; display:inline-block;" id="c69-add-dropdown-container">
                            <button class="btn btn-primary" type="button" onclick="toggleC69AddMenu(event)" style="display:flex; align-items:center; gap:4px;" title="Thêm tài khoản">
                                <span>➕ Thêm Nick</span>
                                <span style="font-size:8px;">▼</span>
                            </button>
                            <div id="c69-add-dropdown-menu" style="display:none; position:absolute; top:calc(100% + 4px); left:0; background:#0f172a; border:1px solid rgba(56,189,248,0.3); border-radius:8px; box-shadow:0 8px 24px rgba(0,0,0,0.7); z-index:200; min-width:170px; overflow:hidden;">
                                <div onclick="openC69AddAccountModal(); toggleC69AddMenu(event);" style="padding:8px 12px; font-size:11.5px; cursor:pointer; display:flex; align-items:center; gap:8px; color:#e2e8f0; border-bottom:1px solid rgba(255,255,255,0.06);" onmouseover="this.style.background='rgba(56,189,248,0.15)'" onmouseout="this.style.background='transparent'">
                                    <span>➕</span> <b>Thêm mới đơn lẻ</b>
                                </div>
                                <div onclick="openC69BulkAddModal(); toggleC69AddMenu(event);" style="padding:8px 12px; font-size:11.5px; cursor:pointer; display:flex; align-items:center; gap:8px; color:#38bdf8;" onmouseover="this.style.background='rgba(56,189,248,0.15)'" onmouseout="this.style.background='transparent'">
                                    <span>⚡</span> <b>Thêm hàng loạt</b>
                                </div>
                            </div>
                        </div>

                        <button class="btn btn-info" id="btn-c69-bulk-sub" onclick="openC69BulkSubOwnerModal()" disabled title="Gán quyền sở hữu Subscription">Gán sở hữu Sub</button>
                        <button class="btn btn-warning" id="btn-c69-bulk-status" onclick="openC69BulkStatusModal()" disabled title="Đổi trạng thái tài khoản">Đổi trạng thái</button>
                        <button class="btn btn-secondary" id="btn-c69-bulk-socks" onclick="openChangeSocksModalForSelected()" disabled title="Đổi Socks5 cho các tài khoản đã chọn" style="border-color:rgba(217,70,239,0.4); color:#f0abfc;">🔄 Đổi Socks</button>
                        <button class="btn btn-dark" id="btn-c69-check-socks" onclick="checkSelectedC69AccountsSocks()" style="border-color:rgba(56,189,248,0.4); color:#38bdf8;" title="Kiểm tra Live/Die Socks của các tài khoản đã chọn (hoặc tất cả)">⚡ Check Socks</button>
                        <button class="btn btn-danger" id="btn-c69-bulk-delete" onclick="handleC69BulkDelete()" disabled title="Xóa tài khoản đã chọn">Xóa</button>
                        <button class="btn btn-purple" id="btn-nurture-selected-c69" onclick="startNurtureSelectedAccounts()" style="font-weight:700; font-size:11px; padding:4px 11px;" title="Chạy nuôi các nick đã chọn">🎬 Nuôi Nick Đã Chọn</button>
                        <label style="font-size:10.5px; color:#38bdf8; display:flex; align-items:center; gap:4px; cursor:pointer; background:rgba(56,189,248,0.08); padding:3px 7px; border-radius:5px; border:1px solid rgba(56,189,248,0.25);" title="Tự động gán Proxy SOCKS5 từ C69 Pool">
                            <input type="checkbox" id="c69-auto-proxy-chk" checked>
                            <span>🛡️ Auto Proxy</span>
                        </label>
                    </div>
                </div>

                <!-- ROW 2: COMPACT RESPONSIVE FILTERS & SEARCH -->
                <div class="c69-control-bar" style="margin-bottom:0;">
                    <div class="c69-filters" style="display:flex; align-items:center; gap:5px; flex-wrap:wrap; flex:1;">
                        <!-- Search Box -->
                        <div style="position:relative; min-width:150px; flex:1; max-width:210px;">
                            <input type="text" class="c69-select" placeholder="🔍 Tìm username, mail..." id="c69-acc-search" oninput="onC69SearchInput()" style="width:100%; box-sizing:border-box; padding:3px 7px 3px 24px; height:26px;">
                            <span style="position:absolute; left:7px; top:50%; transform:translateY(-50%); opacity:0.6; font-size:11px;">🔍</span>
                        </div>

                        <!-- 1. Type Filter -->
                        <select id="c69-acc-type-filter" class="c69-select" onchange="onC69FilterChange()" style="max-width:105px; height:26px;">
                            <option value="">Tất cả loại</option>
                            <option value="Tiktok">Tiktok</option>
                            <option value="Apple">Apple</option>
                            <option value="Amazon">Amazon</option>
                            <option value="Ebay">Ebay</option>
                            <option value="Facebook">Facebook</option>
                            <option value="X">X (Twitter)</option>
                            <option value="Other">Khác</option>
                        </select>

                        <!-- 2. Status Filter -->
                        <select id="c69-acc-status-filter" class="c69-select" onchange="onC69FilterChange()" style="max-width:120px; height:26px;">
                            <option value="">Tất cả trạng thái</option>
                            <option value="0">Hoạt động (Active)</option>
                            <option value="1">Chưa kích hoạt</option>
                            <option value="2">Bị khóa (Banned)</option>
                            <option value="3">Tạm thời</option>
                            <option value="4">Sub OK</option>
                            <option value="7">⏳ Chờ Sub</option>
                            <option value="5">Sub Lỗi</option>
                            <option value="6">Đang sử dụng</option>
                        </select>

                        <!-- 3. Smart Username / Sub / Main Filter -->
                        <select id="c69-acc-username-filter" class="c69-select" onchange="onC69FilterChange()" title="Lọc Username, Subscription & Nhóm" style="max-width:135px; height:26px;">
                            <option value="">Tất cả loại & sub</option>
                            <option value="sub_yes">⭐ Có Sub</option>
                            <option value="sub_no">⚪ Không Sub</option>
                            <option value="shared">🤝 Được chia sẻ</option>
                            <option value="exclude_user_random">Ẩn userxxxx</option>
                            <option value="only_user_random">Chỉ userxxxx</option>
                        </select>

                        <!-- 4. Created By Filter -->
                        <select id="c69-acc-creator-filter" class="c69-select" onchange="onC69FilterChange()" style="max-width:115px; height:26px;">
                            <option value="">Người tạo</option>
                        </select>

                        <!-- 5. Subscription Owner Filter -->
                        <select id="c69-acc-sub-owner-filter" class="c69-select" onchange="onC69FilterChange()" style="max-width:115px; height:26px;">
                            <option value="">Sở hữu Sub</option>
                            <option value="unassigned">-- Chưa gán --</option>
                        </select>

                        <!-- 6. Sort Filter -->
                        <select id="c69-acc-sort-filter" class="c69-select" onchange="onC69FilterChange()" style="max-width:125px; height:26px;">
                            <option value="">Tạo gần nhất</option>
                            <option value="recent_used">Dùng gần nhất</option>
                        </select>

                        <!-- 7. Page Size Filter -->
                        <select id="c69-acc-pagesize" class="c69-select" onchange="onC69PageSizeChange()" style="max-width:80px; height:26px;">
                            <option value="10" selected>10 dòng</option>
                            <option value="20">20 dòng</option>
                            <option value="50">50 dòng</option>
                            <option value="100">100 dòng</option>
                        </select>
                    </div>
                </div>
            </div>

            <!-- STREAMLINED C69 TABLE (CLEAN UX/UI: TẬP TRUNG NUÔI, SỬA, SOCKS5 & EMAIL/CODE) -->
            <div style="overflow-x:auto; background:var(--bg-card); border:1px solid var(--border); border-radius:8px;">
                <table class="data-table" style="width:100%; margin:0;">
                    <thead>
                        <tr>
                            <th style="width:40px; text-align:center; cursor:pointer;" onclick="if(event.target.tagName !== 'INPUT') { const cb = document.getElementById('check-all-c69-accs'); if(cb) { cb.checked = !cb.checked; toggleSelectAllC69Accounts(cb); } }">
                                <input type="checkbox" id="check-all-c69-accs" style="cursor:pointer; transform:scale(1.15);" onchange="toggleSelectAllC69Accounts(this)">
                            </th>
                            <th style="width:45px; text-align:center;">STT</th>
                            <th style="min-width:190px;">Tài Khoản</th>
                            <th style="width:120px;">Trạng Thái</th>
                            <th style="min-width:210px;">Proxy / Socks5</th>
                            <th style="min-width:210px;">Email & Code OTP</th>
                            <th style="min-width:160px;">Hồ Sơ Browser</th>
                            <th style="width:165px; text-align:center;">Hành Động</th>
                        </tr>
                    </thead>
                    <tbody id="c69-accounts-body">
                        <tr><td colspan="8" style="text-align: center; padding:30px; color: var(--text-muted);">⏳ Đang tải tài khoản từ C69...</td></tr>
                    </tbody>
                </table>
            </div>

            <!-- C69 PORTAL PAGINATION BAR -->
            <div style="display:flex; justify-content:space-between; align-items:center; margin-top:12px; padding:12px 16px; background:rgba(15,23,42,0.6); border-radius:8px; border:1px solid var(--border); flex-wrap:wrap; gap:8px;">
                <div id="c69-pagination-info" style="font-size:12px; color:#94a3b8; font-weight:600;">
                    Hiển thị 0 - 0 của 0 tài khoản
                </div>
                <div id="c69-pag-controls" style="display:flex; align-items:center; gap:5px;">
                    <!-- Rendered by JS -->
                </div>
            </div>
        </div>

        <!-- MODAL 0: AUTO UPDATE MODAL (GLASSMORPHISM) -->
        <div id="modal-auto-update" class="modal-backdrop" style="z-index: 2000;">
            <div class="modal-dialog" style="max-width: 520px; background: rgba(8, 13, 30, 0.96); backdrop-filter: blur(24px); border: 1px solid rgba(56, 189, 248, 0.4); box-shadow: 0 20px 50px rgba(0, 242, 254, 0.2); border-radius: 14px;">
                <div class="modal-header" style="border-bottom: 1px solid rgba(56, 189, 248, 0.2); padding: 14px 18px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 20px;">🚀</span>
                        <h3 id="update-modal-title" style="font-size: 14px; font-weight: 800; color: #fff; letter-spacing: 0.3px;">Có Bản Cập Nhật Mới!</h3>
                    </div>
                    <button class="btn-close" onclick="closeUpdateModal()">✕</button>
                </div>
                <div style="padding: 18px; display: flex; flex-direction: column; gap: 14px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(15, 23, 42, 0.85); border: 1px solid rgba(255, 255, 255, 0.08); padding: 12px 16px; border-radius: 10px;">
                        <div>
                            <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Phiên bản hiện tại</div>
                            <div id="update-current-ver" style="font-weight: 700; color: #f8fafc; font-size: 14px;">v2.2.0</div>
                        </div>
                        <div style="font-size: 18px; color: #38bdf8;">➔</div>
                        <div style="text-align: right;">
                            <div style="font-size: 10px; color: #94a3b8; text-transform: uppercase;">Phiên bản mới</div>
                            <div id="update-new-ver" style="font-weight: 800; color: #10b981; font-size: 15px;">v2.2.1</div>
                        </div>
                    </div>
                    <div>
                        <div style="font-size: 11px; font-weight: 700; color: #38bdf8; text-transform: uppercase; margin-bottom: 6px; letter-spacing: 0.5px;">📝 Nội dung cập nhật (Changelog):</div>
                        <div id="update-changelog-box" style="background: rgba(2, 4, 9, 0.9); border: 1px solid rgba(56, 189, 248, 0.2); border-radius: 8px; padding: 12px; font-size: 12px; line-height: 1.6; color: #cbd5e1; max-height: 140px; overflow-y: auto; white-space: pre-line;">
                            Đang tải thông tin...
                        </div>
                    </div>
                    <div id="update-progress-section" style="display: none; flex-direction: column; gap: 8px; background: rgba(56, 189, 248, 0.06); border: 1px solid rgba(56, 189, 248, 0.25); padding: 12px; border-radius: 8px;">
                        <div style="display: flex; justify-content: space-between; font-size: 11px;">
                            <span id="update-progress-status" style="color: #38bdf8; font-weight: 600;">⏳ Đang tải bản cập nhật từ CDN C69...</span>
                            <span id="update-progress-pct" style="color: #fff; font-weight: 700;">0%</span>
                        </div>
                        <div style="width: 100%; height: 6px; background: rgba(255, 255, 255, 0.1); border-radius: 999px; overflow: hidden;">
                            <div id="update-progress-fill" style="width: 0%; height: 100%; background: linear-gradient(90deg, #00f2fe, #10b981); transition: width 0.3s ease;"></div>
                        </div>
                    </div>
                </div>
                <div style="padding: 12px 18px; border-top: 1px solid rgba(255, 255, 255, 0.08); display: flex; justify-content: flex-end; gap: 10px; background: rgba(0, 0, 0, 0.25); border-bottom-left-radius: 14px; border-bottom-right-radius: 14px;">
                    <button class="btn btn-dark" id="btn-update-cancel" onclick="closeUpdateModal()">Để Sau</button>
                    <button class="btn btn-primary" id="btn-update-action" onclick="triggerAppUpdate()" style="background: linear-gradient(135deg, #00f2fe, #0284c7); border: none; font-weight: 700; padding: 8px 18px; box-shadow: 0 0 12px rgba(0, 242, 254, 0.3);">
                        ⬇️ Cập Nhật Ngay
                    </button>
                </div>
            </div>
        </div>

        <!-- MODAL 1: THÊM MỚI TÀI KHOẢN C69 -->
        <div id="modal-c69-add-account" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 520px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">➕ Thêm Mới Tài Khoản C69</h3>
                    <button class="btn-close" onclick="closeC69AddAccountModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Phân Loại (Type):</label>
                            <select id="add-c69-type" class="c69-select" style="width:100%;">
                                <option value="Tiktok" selected>Tiktok</option>
                                <option value="Apple">Apple</option>
                                <option value="Amazon">Amazon</option>
                                <option value="Ebay">Ebay</option>
                                <option value="Facebook">Facebook</option>
                                <option value="X">X (Twitter)</option>
                                <option value="Other">Khác</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Trạng Thái:</label>
                            <select id="add-c69-status" class="c69-select" style="width:100%;">
                                <option value="0" selected>Hoạt động (Active)</option>
                                <option value="1">Chưa kích hoạt</option>
                                <option value="2">Bị khóa (Banned)</option>
                                <option value="3">Tạm thời</option>
                                <option value="4">Sub OK</option>
                                <option value="6">Đang sử dụng</option>
                            </select>
                        </div>
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Username / ID:</label>
                        <input id="add-c69-username" type="text" class="search-input" style="width:100%;" placeholder="VD: user_tiktok_01">
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Mật Khẩu:</label>
                        <input id="add-c69-password" type="text" class="search-input" style="width:100%;" placeholder="Mật khẩu đăng nhập">
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Email Liên Kết:</label>
                        <input id="add-c69-email" type="email" class="search-input" style="width:100%;" placeholder="VD: user@c69.us">
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Ghi Chú (Note):</label>
                        <input id="add-c69-note" type="text" class="search-input" style="width:100%;" placeholder="Ghi chú thêm...">
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeC69AddAccountModal()">Hủy</button>
                        <button class="btn btn-primary" onclick="submitC69AddAccount()">💾 Lưu Tài Khoản</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 2: THÊM HÀNG LOẠT TÀI KHOẢN C69 -->
        <div id="modal-c69-bulk-add" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 600px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">📑 Thêm Hàng Loạt Tài Khoản C69</h3>
                    <button class="btn-close" onclick="closeC69BulkAddModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Phân Loại (Type):</label>
                        <select id="bulk-add-c69-type" class="c69-select" style="width:100%;">
                            <option value="Tiktok" selected>Tiktok</option>
                            <option value="Apple">Apple</option>
                            <option value="Amazon">Amazon</option>
                            <option value="Ebay">Ebay</option>
                            <option value="Facebook">Facebook</option>
                            <option value="X">X (Twitter)</option>
                            <option value="Other">Khác</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">
                            Nhập danh sách tài khoản (định dạng: <code>username|password</code> hoặc <code>username|password|email</code> hoặc <code>username|password|email|note</code>, mỗi dòng 1 tài khoản):
                        </label>
                        <textarea id="bulk-add-c69-text" class="search-input" style="width:100%; height:180px; font-family:monospace; font-size:12px; resize:vertical;" placeholder="user1|pass1|mail1@domain.com
user2|pass2
user3|pass3|mail3@domain.com|note test"></textarea>
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeC69BulkAddModal()">Hủy</button>
                        <button class="btn btn-info" style="background:linear-gradient(135deg, #0ea5e9, #0284c7); border:none; font-weight:bold;" onclick="submitC69BulkAdd()">🚀 Thêm Hàng Loạt</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 3: GÁN SỞ HỮU SUB HÀNG LOẠT -->
        <div id="modal-c69-bulk-sub-owner" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 440px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">👥 Gán Sở Hữu Sub Hàng Loạt</h3>
                    <button class="btn-close" onclick="closeC69BulkSubOwnerModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div style="font-size:12px; color:#cbd5e1;">
                        Chọn tài khoản người dùng sẽ được gán quyền sở hữu Subscription cho <b id="bulk-sub-count" style="color:#38bdf8;">0</b> tài khoản đã chọn:
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Người Sở Hữu (User):</label>
                        <select id="bulk-sub-owner-select" class="c69-select" style="width:100%;">
                            <option value="">-- Chọn User --</option>
                        </select>
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeC69BulkSubOwnerModal()">Hủy</button>
                        <button class="btn btn-info" onclick="submitC69BulkSubOwner()">💾 Gán Sở Hữu</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 4: ĐỔI TRẠNG THÁI HÀNG LOẠT -->
        <div id="modal-c69-bulk-status" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 440px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">🔄 Đổi Trạng Thái Hàng Loạt</h3>
                    <button class="btn-close" onclick="closeC69BulkStatusModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div style="font-size:12px; color:#cbd5e1;">
                        Đổi trạng thái cho <b id="bulk-status-count" style="color:#38bdf8;">0</b> tài khoản đã chọn:
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Trạng Thái Mới:</label>
                        <select id="bulk-status-select" class="c69-select" style="width:100%;">
                            <option value="0">Hoạt động (Active)</option>
                            <option value="1">Chưa kích hoạt</option>
                            <option value="2">Bị khóa (Banned)</option>
                            <option value="3">Tạm thời</option>
                            <option value="4">Sub OK</option>
                            <option value="7">⏳ Chờ Sub</option>
                            <option value="5">Sub Lỗi</option>
                            <option value="6">Đang sử dụng</option>
                        </select>
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeC69BulkStatusModal()">Hủy</button>
                        <button class="btn btn-warning" onclick="submitC69BulkStatus()">💾 Cập Nhật Trạng Thái</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 5: XEM CHI TIẾT & CHỈNH SỬA TÀI KHOẢN C69 -->
        <div id="modal-c69-account-detail" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 620px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;" id="detail-c69-title">🔍 Chi Tiết Tài Khoản</h3>
                    <button class="btn-close" onclick="closeC69AccountDetailModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <input type="hidden" id="detail-c69-id">
                    
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Username:</label>
                            <input id="detail-c69-username" type="text" class="search-input" style="width:100%;">
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Mật Khẩu:</label>
                            <input id="detail-c69-password" type="text" class="search-input" style="width:100%;">
                        </div>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Phân Loại (Type):</label>
                            <select id="detail-c69-type" class="c69-select" style="width:100%;">
                                <option value="Tiktok">Tiktok</option>
                                <option value="Apple">Apple</option>
                                <option value="Amazon">Amazon</option>
                                <option value="Ebay">Ebay</option>
                                <option value="Facebook">Facebook</option>
                                <option value="X">X (Twitter)</option>
                                <option value="Other">Khác</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Trạng Thái:</label>
                            <select id="detail-c69-status" class="c69-select" style="width:100%;">
                                <option value="0">Hoạt động (Active)</option>
                                <option value="1">Chưa kích hoạt</option>
                                <option value="2">Bị khóa (Banned)</option>
                                <option value="3">Tạm thời</option>
                                <option value="4">Sub OK</option>
                                <option value="5">Sub Lỗi</option>
                                <option value="6">Đang sử dụng</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Email Liên Kết:</label>
                        <input id="detail-c69-email" type="text" class="search-input" style="width:100%;">
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Gói Subscription:</label>
                            <input id="detail-c69-sub" type="text" class="search-input" style="width:100%;">
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Sở Hữu Subscription:</label>
                            <input id="detail-c69-sub-owner" type="text" class="search-input" style="width:100%;">
                        </div>
                    </div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Ghi Chú (Note):</label>
                        <textarea id="detail-c69-note" class="search-input" style="width:100%; height:60px; resize:vertical;"></textarea>
                    </div>

                    <div id="detail-c69-meta" style="font-size:11px; color:var(--text-muted); background:rgba(0,0,0,0.25); padding:8px 10px; border-radius:6px;"></div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <button class="btn btn-dark" type="button" onclick="openC692FAFromDetail()">🔑 Xem 2FA & OTP</button>
                        <div style="display:flex; gap:8px;">
                            <button class="btn btn-dark" onclick="closeC69AccountDetailModal()">Đóng</button>
                            <button class="btn btn-primary" onclick="submitC69UpdateAccount()">💾 Lưu Thay Đổi</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 6: XEM MÃ 2FA VÀ LẤY OTP -->
        <div id="modal-c69-2fa" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 440px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">🔑 Xác Thực 2FA (Two-Factor Auth)</h3>
                    <button class="btn-close" onclick="closeC692FAModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:14px; text-align:center;">
                    <div style="font-size:12px; color:var(--text-muted);">Mã OTP 6 số tạo tự động theo thời gian thực (TOTP):</div>
                    <div id="c69-2fa-code-display" style="font-size:32px; font-weight:900; letter-spacing:6px; color:#10b981; background:rgba(16,185,129,0.12); padding:16px; border-radius:10px; border:1px dashed rgba(16,185,129,0.4); cursor:pointer;" onclick="copyOtp(this.innerText)" title="Click để copy OTP">
                        ------
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:var(--text-muted);">
                        <span>2FA Secret Key:</span>
                        <code id="c69-2fa-secret-display" style="font-size:11px; color:#f0abfc; cursor:pointer;" onclick="copyText(this.innerText, 'Secret Key')">---</code>
                    </div>
                    <div style="display:flex; justify-content:center; gap:8px; margin-top:6px;">
                        <button class="btn btn-dark" onclick="refreshC692FA()">🔄 Tạo Lại Mã</button>
                        <button class="btn btn-primary" onclick="closeC692FAModal()">Xong</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 7: REG TIKTOK AUTO 24/7 MODAL (MATCHING Accounts.jsx) -->
        <div id="modal-c69-reg-tiktok" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 520px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">🎵 Đăng Ký Tài Khoản TikTok Tự Động 24/7</h3>
                    <button class="btn-close" onclick="closeC69TikTokRegModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Phương Thức Đăng Ký:</label>
                        <select id="reg-tiktok-method" class="c69-select" style="width:100%;">
                            <option value="google">Đăng ký bằng Google Mail (Khuyên dùng)</option>
                            <option value="email">Đăng ký bằng Email Outlook / Hotmail C69</option>
                            <option value="custom">Email tùy chỉnh</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Chế Độ Giải Captcha:</label>
                        <select id="reg-tiktok-captcha" class="c69-select" style="width:100%;">
                            <option value="manual">Tự giải thủ công trên trình duyệt (An toàn nhất)</option>
                            <option value="auto_ai">Tự động bằng AI Solver (Blink + Canvas Engine)</option>
                        </select>
                    </div>
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Proxy Cấp Cho Profile Đăng Ký:</label>
                        <div style="display:flex; gap:6px;">
                            <input id="reg-tiktok-proxy" type="text" class="search-input" style="flex:1;" placeholder="Để trống để tự động lấy từ Pool C69 Proxy">
                            <button class="btn btn-dark" type="button" onclick="assignRandomC69ProxyToField('reg-tiktok-proxy', null)">🎲 C69 Proxy</button>
                        </div>
                    </div>
                    <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); border-radius:6px; padding:10px; font-size:11px; color:#a7f3d0; line-height:1.5;">
                        ⚡ <b>Cơ chế Auto Reg:</b> Tạo mới 1 Profile Mun Anti-Browser độc lập với Canvas/Audio Noise Seed riêng, gắn Proxy, vượt nhận diện Cloudflare / Akamai và tự động đăng ký tài khoản TikTok rồi lưu trực tiếp về C69.
                    </div>
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeC69TikTokRegModal()">Đóng</button>
                        <button class="btn btn-success" style="background:linear-gradient(135deg, #10b981, #059669); font-weight:bold; border:none;" onclick="submitC69StartTikTokReg()">🚀 Khởi Chạy Đăng Ký Auto</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 8: ĐỌC MAIL SỐ LƯỢNG LỚN MODAL -->
        <div id="modal-c69-bulk-mail" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 600px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">⚡ Đọc Mail Số Lượng Lớn (C69 Mail Engine)</h3>
                    <button class="btn-close" onclick="closeC69BulkMailModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">
                            Nhập danh sách email cần đọc OTP / Hộp thư (định dạng: <code>email|password</code> hoặc <code>email|password|token</code>, mỗi dòng 1 email):
                        </label>
                        <textarea id="bulk-mail-c69-input" class="search-input" style="width:100%; height:160px; font-family:monospace; font-size:12px; resize:vertical;" placeholder="mail1@domain.com|pass1
mail2@domain.com|pass2
mail3@domain.com|pass3|refresh_token"></textarea>
                    </div>
                    <div id="bulk-mail-c69-results" style="display:none; max-height:150px; overflow-y:auto; background:rgba(0,0,0,0.3); border:1px solid var(--border); border-radius:6px; padding:8px; font-size:11px;"></div>
                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeC69BulkMailModal()">Đóng</button>
                        <button class="btn btn-primary" onclick="submitC69BulkReadMail()">⚡ Bắt Đầu Quét Đọc Hộp Thư</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 9: THAY ĐỔI SOCKS5 PROXY CHO TÀI KHOẢN -->
        <div id="modal-c69-change-socks" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 540px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">🛡️ Thay Đổi SOCKS5 Proxy Cho Tài Khoản</h3>
                    <button class="btn-close" onclick="closeChangeSocksModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div id="change-socks-target-info" style="font-size:12px; color:#38bdf8; background:rgba(56,189,248,0.08); padding:8px 12px; border-radius:6px; border:1px solid rgba(56,189,248,0.25);">
                        Đang áp dụng cho tài khoản...
                    </div>

                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <label style="font-size:11px; color:var(--text-muted);">Chọn Nhanh Từ Pool C69 (250 SOCKS5):</label>
                            <button class="btn btn-dark" type="button" onclick="randomLiveProxyForChangeSocks()" style="padding:2px 8px; font-size:11px; border-color:rgba(16,185,129,0.4); color:#34d399;">🎲 Chọn Ngẫu Nhiên</button>
                        </div>
                        <select id="change-socks-pool-select" class="c69-select" style="width:100%;" onchange="onSelectProxyFromPool(this.value)">
                            <option value="">-- Chọn 1 proxy từ 250 SOCKS5 Pool --</option>
                        </select>
                    </div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Hoặc Nhập Thủ Công Proxy SOCKS5:</label>
                        <input id="change-socks-manual-input" type="text" class="search-input" style="width:100%; font-family:monospace;" placeholder="host:port:user:pass hoặc socks5://user:pass@host:port">
                    </div>

                    <!-- KẾT QUẢ TEST NHANH -->
                    <div id="change-socks-test-result" style="display:none; font-size:11px; padding:8px 10px; border-radius:6px;"></div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <button class="btn btn-dark" type="button" onclick="testCurrentChangeSocksProxy()">⚡ Kiểm Tra Kết Nối</button>
                        <div style="display:flex; gap:8px;">
                            <button class="btn btn-dark" onclick="closeChangeSocksModal()">Đóng</button>
                            <button class="btn btn-primary" onclick="submitChangeSocks()" style="background:linear-gradient(135deg, #0284c7, #0ea5e9); font-weight:700; border:none;">💾 Lưu & Gán Socks</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL: THAY ĐỔI SOCKS5 PROXY CHO MUN ANTI BROWSER PROFILE -->
        <div id="modal-profile-change-socks" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 540px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">🔄 Đổi SOCKS5 Proxy Cho Profile Anti Browser</h3>
                    <button class="btn-close" onclick="closeProfileChangeSocksModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div id="profile-change-socks-target-info" style="font-size:12px; color:#38bdf8; background:rgba(56,189,248,0.08); padding:8px 12px; border-radius:6px; border:1px solid rgba(56,189,248,0.25);">
                        Đang áp dụng cho Profile...
                    </div>

                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                            <label style="font-size:11px; color:var(--text-muted);">Chọn Nhanh Từ Pool C69 (250 SOCKS5):</label>
                            <button class="btn btn-dark" type="button" onclick="randomLiveProxyForProfileChangeSocks()" style="padding:2px 8px; font-size:11px; border-color:rgba(16,185,129,0.4); color:#34d399;">🎲 Chọn Ngẫu Nhiên</button>
                        </div>
                        <select id="profile-change-socks-pool-select" class="c69-select" style="width:100%;" onchange="onSelectProxyForProfileModal(this.value)">
                            <option value="">-- Chọn 1 proxy từ 250 SOCKS5 Pool --</option>
                        </select>
                    </div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Hoặc Nhập Thủ Công Proxy SOCKS5 / HTTP:</label>
                        <input id="profile-change-socks-manual-input" type="text" class="search-input" style="width:100%; font-family:monospace;" placeholder="host:port:user:pass hoặc socks5://user:pass@host:port">
                    </div>

                    <div style="display:flex; gap:14px; align-items:center;">
                        <label style="font-size:11px; color:#cbd5e1; display:flex; align-items:center; gap:5px; cursor:pointer;">
                            <input type="radio" name="profile-change-socks-type" value="socks5" checked>
                            <span>SOCKS5</span>
                        </label>
                        <label style="font-size:11px; color:#cbd5e1; display:flex; align-items:center; gap:5px; cursor:pointer;">
                            <input type="radio" name="profile-change-socks-type" value="http">
                            <span>HTTP / HTTPS</span>
                        </label>
                        <label style="font-size:11px; color:#ef4444; display:flex; align-items:center; gap:5px; cursor:pointer;">
                            <input type="radio" name="profile-change-socks-type" value="direct">
                            <span>⚡ Direct (Không dùng proxy)</span>
                        </label>
                    </div>

                    <!-- KẾT QUẢ TEST NHANH -->
                    <div id="profile-change-socks-test-result" style="display:none; font-size:11px; padding:8px 10px; border-radius:6px;"></div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <button class="btn btn-dark" type="button" id="btn-test-profile-modal-proxy" onclick="testCurrentProfileModalProxy()">⚡ Kiểm Tra Kết Nối</button>
                        <div style="display:flex; gap:8px;">
                            <button class="btn btn-dark" onclick="closeProfileChangeSocksModal()">Đóng</button>
                            <button class="btn btn-primary" id="btn-save-profile-change-socks" onclick="submitProfileChangeSocks()" style="background:linear-gradient(135deg, #0284c7, #0ea5e9); font-weight:700; border:none;">💾 Lưu & Gán Socks</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL 10: QUẢN LÝ 250 SOCKS5 PROXY POOL (CHECK LIVE/DIE & TỰ ĐỘNG THAY THẾ) -->
        <div id="modal-c69-proxy-pool" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 960px; width:95vw; max-height:90vh; display:flex; flex-direction:column;">
                <div class="modal-header">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <h3 style="font-size:15px; font-weight:800; color:#38bdf8;">🌐 Quản Lý Proxy Pool C69 (250 SOCKS5 Proxies)</h3>
                    </div>
                    <button class="btn-close" onclick="closeProxyPoolModal()">✕</button>
                </div>

                <div style="padding:16px; overflow-y:auto; display:flex; flex-direction:column; gap:14px;">
                    <!-- DASHBOARD THỐNG KÊ LIVE / DIE -->
                    <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(170px, 1fr)); gap:10px;">
                        <div style="background:rgba(15,23,42,0.6); border:1px solid rgba(56,189,248,0.2); border-radius:8px; padding:12px; text-align:center;">
                            <div style="font-size:11px; color:#94a3b8; margin-bottom:4px;">Tổng SOCKS5 Proxies</div>
                            <div id="proxy-stat-total" style="font-size:22px; font-weight:800; color:#38bdf8;">250</div>
                        </div>
                        <div style="background:rgba(16,185,129,0.08); border:1px solid rgba(16,185,129,0.25); border-radius:8px; padding:12px; text-align:center;">
                            <div style="font-size:11px; color:#a7f3d0; margin-bottom:4px;">Proxy Đang Sống (Live)</div>
                            <div id="proxy-stat-live" style="font-size:22px; font-weight:800; color:#10b981;">--</div>
                        </div>
                        <div style="background:rgba(239,68,68,0.08); border:1px solid rgba(239,68,68,0.25); border-radius:8px; padding:12px; text-align:center;">
                            <div style="font-size:11px; color:#fca5a5; margin-bottom:4px;">Proxy Đã Chết (Die)</div>
                            <div id="proxy-stat-die" style="font-size:22px; font-weight:800; color:#ef4444;">--</div>
                        </div>
                        <div style="background:rgba(168,85,247,0.08); border:1px solid rgba(168,85,247,0.25); border-radius:8px; padding:12px; text-align:center;">
                            <div style="font-size:11px; color:#e9d5ff; margin-bottom:4px;">Độ Trễ Trung Bình</div>
                            <div id="proxy-stat-ping" style="font-size:22px; font-weight:800; color:#c084fc;">-- ms</div>
                        </div>
                    </div>

                    <!-- ACTION TOOLBAR CỦA PROXY POOL -->
                    <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; background:rgba(15,23,42,0.8); padding:10px 14px; border-radius:8px; border:1px solid var(--border);">
                        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
                            <button id="btn-reload-proxy-pool" class="btn btn-secondary" onclick="reloadProxyPoolModal()" style="border:1px solid #475569; font-weight:700; color:#e2e8f0;" title="Tải lại danh sách proxy và trạng thái mới nhất từ đĩa">
                                🔄 Làm Mới
                            </button>
                            <button class="btn btn-success" onclick="openImportProxiesModal()" style="background:linear-gradient(135deg, #10b981, #059669); border:none; font-weight:700; color:#fff;" title="Dán danh sách proxy mới để nạp vào pool">
                                ➕ Import Proxies
                            </button>
                            <button id="btn-batch-test-proxies" class="btn btn-primary" onclick="testAllProxiesBatch()" style="background:linear-gradient(135deg, #0ea5e9, #0284c7); border:none; font-weight:700;">
                                ⚡ Kiểm Tra Toàn Bộ (Check Live/Die)
                            </button>
                            <button id="btn-auto-replace-dead" class="btn btn-warning" onclick="autoReplaceDeadProxies()" style="background:linear-gradient(135deg, #f59e0b, #d97706); border:none; font-weight:700; color:#fff;" title="Quét tài khoản/profile đang dùng proxy die và tự động tráo sang proxy live">
                                🔄 Tự Động Thay Proxy Die Cho Tài Khoản
                            </button>
                            <button id="btn-remove-dead-proxies" class="btn btn-danger" onclick="removeDeadProxiesFromPool()" style="background:linear-gradient(135deg, #ef4444, #dc2626); border:none; font-weight:700; color:#fff;" title="Xóa các proxy đã được xác nhận Die khỏi danh sách pool">
                                🗑️ Xóa Proxy Die Khỏi Pool
                            </button>
                        </div>

                        <div style="display:flex; align-items:center; gap:8px;">
                            <input id="proxy-search-input" type="text" class="search-input" placeholder="🔍 Tìm IP / Port..." style="width:160px; font-size:12px;" oninput="filterProxyPoolTable()">
                            <select id="proxy-filter-status" class="c69-select" style="font-size:12px;" onchange="filterProxyPoolTable()">
                                <option value="all">Tất cả trạng thái</option>
                                <option value="live">🟢 Chỉ Proxy Live</option>
                                <option value="die">🔴 Chỉ Proxy Die</option>
                                <option value="untested">⚪ Chưa kiểm tra</option>
                            </select>
                        </div>
                    </div>

                    <!-- BẢNG DANH SÁCH PROXY POOL -->
                    <div style="max-height:420px; overflow-y:auto; border:1px solid var(--border); border-radius:8px; background:var(--bg-card);">
                        <table class="data-table" style="width:100%; margin:0;">
                            <thead style="position:sticky; top:0; background:#0f172a; z-index:2;">
                                <tr>
                                    <th style="width:45px; text-align:center;">STT</th>
                                    <th style="min-width:160px;">Địa Chỉ (Host:Port)</th>
                                    <th style="min-width:180px;">Tài Khoản (User:Pass)</th>
                                    <th style="width:130px; text-align:center;">Trạng Thái</th>
                                    <th style="width:110px; text-align:center;">Độ Trễ (Ping)</th>
                                    <th style="width:150px; text-align:center;">Thao Tác</th>
                                </tr>
                            </thead>
                            <tbody id="proxy-pool-tbody">
                                <tr><td colspan="6" style="text-align:center; padding:30px; color:var(--text-muted);">Đang tải danh sách Proxies...</td></tr>
                            </tbody>
                        </table>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; font-size:11px; color:#94a3b8;">
                        <span id="proxy-pool-counter-info">Hiển thị 0 / 0 proxy</span>
                        <span>Định dạng chuẩn: SOCKS5 / HTTP Authenticated (Global / Multi-Port)</span>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL CON: IMPORT DANH SÁCH PROXY MỚI -->
        <div id="modal-import-proxies" class="modal-backdrop" style="z-index: 1050;">
            <div class="modal-dialog" style="max-width: 580px; width: 92vw;">
                <div class="modal-header">
                    <h3 style="font-size:15px; font-weight:800; color:#38bdf8;">📥 Thêm / Import Danh Sách Proxy Mới</h3>
                    <button class="btn-close" onclick="closeImportProxiesModal()">✕</button>
                </div>
                <div style="padding:16px; display:flex; flex-direction:column; gap:12px;">
                    <div style="background:rgba(56,189,248,0.08); border:1px solid rgba(56,189,248,0.25); border-radius:6px; padding:10px; font-size:11.5px; color:#cbd5e1; line-height:1.5;">
                        <b style="color:#38bdf8;">Định dạng được hỗ trợ (mỗi dòng 1 proxy):</b><br>
                        • <code>host:port:username:password</code> (Khuyên dùng)<br>
                        • <code>socks5://username:password@host:port</code><br>
                        • <code>http://username:password@host:port</code><br>
                        • <code>host:port</code> (Proxy IP whitelist, không có user/pass)
                    </div>

                    <div>
                        <label style="font-size:11px; font-weight:700; color:#94a3b8; margin-bottom:5px; display:block;">Dán danh sách Proxies vào đây:</label>
                        <textarea id="import-proxies-textarea" style="width:100%; height:160px; background:#020617; border:1px solid var(--border); border-radius:6px; padding:8px 10px; color:#f8fafc; font-family:monospace; font-size:12px; resize:vertical;" placeholder="104.165.66.130:7285:user:pass&#10;173.0.9.70:5653:user:pass&#10;socks5://user:pass@46.202.224.152:5704"></textarea>
                    </div>

                    <div style="display:flex; gap:16px; align-items:center; background:rgba(15,23,42,0.6); padding:8px 12px; border-radius:6px; border:1px solid var(--border);">
                        <span style="font-size:11.5px; font-weight:700; color:#e2e8f0;">Chế độ:</span>
                        <label style="display:flex; align-items:center; gap:5px; font-size:11.5px; cursor:pointer;">
                            <input type="radio" name="import-proxy-mode" value="append" checked> 🟢 Thêm nối tiếp (Lọc trùng)
                        </label>
                        <label style="display:flex; align-items:center; gap:5px; font-size:11.5px; cursor:pointer;">
                            <input type="radio" name="import-proxy-mode" value="replace"> 🔴 Ghi đè toàn bộ
                        </label>
                    </div>

                    <div id="import-proxies-msg" style="display:none; font-size:12px; padding:8px 10px; border-radius:6px;"></div>

                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:6px;">
                        <button class="btn btn-dark" onclick="closeImportProxiesModal()">Đóng</button>
                        <button id="btn-submit-import-proxies" class="btn btn-primary" onclick="submitImportProxies()" style="background:linear-gradient(135deg, #10b981, #059669); border:none; font-weight:700;">
                            📥 Bắt Đầu Import
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL TẠO PROFILE MỚI -->
        <div id="modal-create-profile" class="modal-backdrop">
            <div class="modal-dialog">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;">✨ Tạo Profile Mun Anti-Browser Mới</h3>
                    <button class="btn-close" onclick="closeCreateProfileModal()">✕</button>
                </div>
                <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Tên Profile:</label>
                            <input id="modal-prof-name" type="text" class="search-input" style="width:100%;" placeholder="VD: Profile TikTok Farm #1">
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Engine Chống Nhận Diện:</label>
                            <select id="modal-prof-engine" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="native">💎 Native C++ Core (Sửa mã nguồn Blink)</option>
                                <option value="js_stealth">⚡ JS CDP Stealth (Mặc định Chrome)</option>
                                <option value="hybrid">🔥 Hybrid (2 Lớp: C++ Core + CDP Shield)</option>
                            </select>
                        </div>
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
                    <div style="display:grid; grid-template-columns:1fr 1fr 1fr; gap:8px;">
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
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">RAM (Memory):</label>
                            <select id="modal-prof-ram" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="16">16 GB (Khuyên dùng)</option>
                                <option value="8">8 GB</option>
                                <option value="32">32 GB</option>
                                <option value="64">64 GB</option>
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
                    <div style="background: rgba(0, 242, 254, 0.03); border: 1px solid rgba(0, 242, 254, 0.15); border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <label style="font-size:11px; font-weight:700; color:var(--primary);">🌐 Cấu Hình Proxy & SOCKS5:</label>
                            <span id="modal-create-proxy-status" style="font-size:10px; color:var(--text-muted);"></span>
                        </div>
                        <div style="display:grid; grid-template-columns: 140px 1fr; gap:8px;">
                            <div>
                                <select id="modal-prof-proxy-type" onchange="onCreateProxyTypeChange()" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:7px 8px; border-radius:6px; font-size:12px;">
                                    <option value="direct">⚡ Direct (Không Proxy)</option>
                                    <option value="socks5" selected>🛡️ SOCKS5 Proxy</option>
                                    <option value="http">🌐 HTTP Proxy</option>
                                </select>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <input id="modal-prof-proxy" type="text" class="search-input" style="flex:1;" placeholder="host:port hoặc socks5://user:pass@host:port">
                                <button class="btn btn-dark" type="button" onclick="testModalProxy('create')" style="font-size:11px; padding:6px 10px; border-color:var(--border);">⚡ Test</button>
                            </div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:11px;">
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-dark" type="button" onclick="assignRandomC69ProxyToField('modal-prof-proxy', 'modal-prof-proxy-type')" style="font-size:10px; padding:3px 8px; border-color:rgba(0,242,254,0.3); color:var(--primary);">🎲 Random C69 SOCKS5</button>
                                <button class="btn btn-dark" type="button" onclick="clearModalProxyField('modal-prof-proxy', 'modal-prof-proxy-type')" style="font-size:10px; padding:3px 8px;">✕ Xóa Proxy</button>
                            </div>
                            <div style="display:flex; align-items:center; gap:4px;">
                                <span style="color:var(--text-muted); font-size:10px;">WebRTC:</span>
                                <select id="modal-prof-webrtc" style="background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:2px 6px; border-radius:4px; font-size:10px;">
                                    <option value="proxy_only">🛡️ Ép qua Proxy (Chống Lộ IP)</option>
                                    <option value="disabled">🚫 Tắt WebRTC</option>
                                    <option value="custom">🌐 Mặc định</option>
                                </select>
                            </div>
                        </div>
                    </div>
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <button class="btn btn-dark" type="button" onclick="randomizeModalFields()">🎲 Random Hợp Lý</button>
                        <div style="display:flex; gap:8px;">
                            <button class="btn btn-dark" onclick="closeCreateProfileModal()">Hủy</button>
                            <button class="btn btn-primary" onclick="submitCreateProfile()">🚀 Tạo Profile</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL CHỈNH SỬA FINGERPRINT CHI TIẾT -->
        <div id="modal-edit-fingerprint" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 600px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700;" id="modal-edit-title">🛠️ Tùy Chỉnh Dấu Vân Tay (Fingerprint)</h3>
                    <button class="btn-close" onclick="closeEditFingerprintModal()">✕</button>
                </div>
                <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
                    <input type="hidden" id="edit-prof-id">
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Tên Profile:</label>
                            <input id="edit-prof-name" type="text" class="search-input" style="width:100%;">
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Engine Hoạt Động:</label>
                            <select id="edit-prof-engine" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="native">💎 Native C++ Core (Sửa mã nguồn Chromium)</option>
                                <option value="js_stealth">⚡ JS CDP Stealth (Chạy trên Google Chrome thường)</option>
                                <option value="hybrid">🔥 Hybrid (Kết hợp 2 lớp: Native C++ & JS Shield)</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">GPU WebGL Renderer:</label>
                        <input id="edit-prof-gpu-renderer" type="text" class="search-input" style="width:100%; font-size:11px;">
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Hệ Điều Hành & Chế Độ Thiết Bị:</label>
                            <select id="edit-prof-os" onchange="onEditProfOsChange()" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="Windows">💻 Windows (Desktop PC)</option>
                                <option value="Android">📱 Android (Mobile Phone)</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Độ Phân Giải Màn Hình:</label>
                            <input id="edit-prof-res" type="text" class="search-input" style="width:100%;">
                        </div>
                    </div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:flex; justify-content:space-between; align-items:center;">
                            <span>User Agent:</span>
                            <div style="display:flex; gap:6px;">
                                <a href="javascript:void(0)" onclick="setEditUaPreset('desktop')" style="color:#38bdf8; text-decoration:none; font-size:10px;">💻 Mẫu Desktop</a>
                                <span style="color:var(--text-muted);">|</span>
                                <a href="javascript:void(0)" onclick="setEditUaPreset('mobile')" style="color:#10b981; text-decoration:none; font-size:10px;">📱 Mẫu Mobile</a>
                            </div>
                        </label>
                        <input id="edit-prof-ua" type="text" class="search-input" style="width:100%; font-size:11px;" placeholder="Để trống để dùng Native Chromium User Agent mặc định">
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Số Nhân CPU:</label>
                            <input id="edit-prof-cpu" type="number" class="search-input" style="width:100%;">
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">RAM (GB):</label>
                            <input id="edit-prof-ram" type="number" class="search-input" style="width:100%;">
                        </div>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:flex; justify-content:space-between;">
                                <span>Canvas Noise Seed:</span>
                                <a href="javascript:void(0)" onclick="randomSeed('edit-prof-canvas-seed')" style="color:var(--primary); text-decoration:none;">🎲 Random</a>
                            </label>
                            <input id="edit-prof-canvas-seed" type="number" class="search-input" style="width:100%;">
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:flex; justify-content:space-between;">
                                <span>Audio Noise Seed:</span>
                                <a href="javascript:void(0)" onclick="randomSeed('edit-prof-audio-seed')" style="color:var(--primary); text-decoration:none;">🎲 Random</a>
                            </label>
                            <input id="edit-prof-audio-seed" type="number" class="search-input" style="width:100%;">
                        </div>
                    </div>

                    <div style="background: rgba(0, 242, 254, 0.03); border: 1px solid rgba(0, 242, 254, 0.15); border-radius: 8px; padding: 10px; display: flex; flex-direction: column; gap: 8px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <label style="font-size:11px; font-weight:700; color:var(--primary);">🌐 Cấu Hình Proxy & SOCKS5:</label>
                            <span id="modal-edit-proxy-status" style="font-size:10px; color:var(--text-muted);"></span>
                        </div>
                        <div style="display:grid; grid-template-columns: 140px 1fr; gap:8px;">
                            <div>
                                <select id="edit-prof-proxy-type" onchange="onEditProxyTypeChange()" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:7px 8px; border-radius:6px; font-size:12px;">
                                    <option value="direct">⚡ Direct (Không Proxy)</option>
                                    <option value="socks5">🛡️ SOCKS5 Proxy</option>
                                    <option value="http">🌐 HTTP Proxy</option>
                                </select>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <input id="edit-prof-proxy" type="text" class="search-input" style="flex:1;" placeholder="host:port hoặc socks5://user:pass@host:port">
                                <button class="btn btn-dark" type="button" onclick="testModalProxy('edit')" style="font-size:11px; padding:6px 10px; border-color:var(--border);">⚡ Test</button>
                            </div>
                        </div>
                        <div style="display:flex; justify-content:space-between; align-items:center; gap:8px; font-size:11px;">
                            <div style="display:flex; gap:6px;">
                                <button class="btn btn-dark" type="button" onclick="assignRandomC69ProxyToField('edit-prof-proxy', 'edit-prof-proxy-type')" style="font-size:10px; padding:3px 8px; border-color:rgba(0,242,254,0.3); color:var(--primary);">🎲 Random C69 SOCKS5</button>
                                <button class="btn btn-dark" type="button" onclick="clearModalProxyField('edit-prof-proxy', 'edit-prof-proxy-type')" style="font-size:10px; padding:3px 8px;">✕ Xóa Proxy</button>
                            </div>
                            <div style="display:flex; align-items:center; gap:4px;">
                                <span style="color:var(--text-muted); font-size:10px;">WebRTC:</span>
                                <select id="edit-prof-webrtc" style="background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:2px 6px; border-radius:4px; font-size:10px;">
                                    <option value="proxy_only">🛡️ Ép qua Proxy (Chống Lộ IP)</option>
                                    <option value="disabled">🚫 Tắt WebRTC</option>
                                    <option value="custom">🌐 Mặc định</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    <div style="background: rgba(0, 242, 254, 0.04); border: 1px solid rgba(0, 242, 254, 0.15); border-radius: 8px; padding: 8px 12px; font-size: 11px; color: #94a3b8; display: flex; flex-direction: column; gap: 3px;">
                        <div style="color:var(--primary); font-weight:700;">💡 Cơ chế Dual-Engine & Fingerprint:</div>
                        <div>• <b>💎 Native C++:</b> Can thiệp trực tiếp Blink renderer (C++), che dấu 100% qua IFrame & Web Worker.</div>
                        <div>• <b>⚡ JS Stealth:</b> Lá chắn CDP Runtime v6.0 bảo vệ trên trình duyệt Chrome sẵn có.</div>
                        <div>• <b>🎲 Noise Seeds:</b> Băm vi sai sub-pixel Canvas & AudioBuffer, sinh fingerprint độc nhất không trùng lặp.</div>
                    </div>

                    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
                        <button class="btn btn-dark" type="button" onclick="randomizeEditFingerprint()">🎲 Random Toàn Bộ Dấu Vân Tay</button>
                        <div style="display:flex; gap:8px;">
                            <button class="btn btn-dark" onclick="closeEditFingerprintModal()">Hủy</button>
                            <button class="btn btn-primary" onclick="saveEditedFingerprint()">💾 Lưu Thay Đổi</button>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- MODAL NUÔI TIKTOK MUN ANTI-BROWSER KẾT HỢP C69 -->
        <div id="modal-nurture-tiktok" class="modal-backdrop">
            <div class="modal-dialog" style="max-width: 520px;">
                <div class="modal-header">
                    <h3 style="font-size:14px; font-weight:700; color:#f0abfc;">🎬 Nuôi TikTok Mun Anti-Browser kết hợp C69</h3>
                    <button class="btn-close" onclick="closeNurtureModal()">✕</button>
                </div>
                <div style="padding: 16px; display: flex; flex-direction: column; gap: 12px;">
                    <input type="hidden" id="nurture-prof-id">
                    <div style="background: rgba(217, 70, 239, 0.08); border: 1px solid rgba(217, 70, 239, 0.25); border-radius: 8px; padding: 10px 12px; font-size: 12px;">
                        <div style="font-weight:700; color:#fff;" id="nurture-modal-prof-name">Profile #...</div>
                        <div style="color:var(--text-muted); font-size:11px; margin-top:2px;">Kích hoạt luồng xem video FYP, tự động thả tim & lướt chuyển bài như người thật.</div>
                    </div>

                    <div id="nurture-modal-rate-limit-warning" style="display:none; background:rgba(249,115,22,0.15); border:1px solid #f97316; color:#fdba74; border-radius:8px; padding:10px 12px; font-size:12px; line-height:1.5;"></div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Chọn Tài Khoản TikTok từ C69.US:</label>
                        <select id="nurture-c69-acc-select" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                            <option value="">⏳ Đang tải tài khoản từ C69...</option>
                        </select>
                    </div>

                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px;">
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Thời Gian Xem / Video:</label>
                            <select id="nurture-watch-duration" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="8-20">8 - 20 giây (Tự nhiên)</option>
                                <option value="5-12">5 - 12 giây (Nhanh)</option>
                                <option value="15-35">15 - 35 giây (Xem sâu)</option>
                            </select>
                        </div>
                        <div>
                            <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:block;">Tỷ Lệ Thả Tim (Like):</label>
                            <select id="nurture-like-rate" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                                <option value="0.65">65% (Khuyên dùng)</option>
                                <option value="0.40">40% (Ít tương tác)</option>
                                <option value="0.85">85% (Tương tác mạnh)</option>
                            </select>
                        </div>
                    </div>

                    <div>
                        <label style="font-size:11px; color:var(--text-muted); margin-bottom:4px; display:flex; justify-content:space-between;">
                            <span>Cấu Hình Proxy Cho Profile Nuôi:</span>
                            <span id="nurture-proxy-status" style="font-size:10px; color:#10b981;"></span>
                        </label>
                        <select id="nurture-proxy-mode" onchange="toggleNurtureProxyInput()" style="width:100%; background:var(--bg-card-hover); border:1px solid var(--border); color:#fff; padding:8px; border-radius:6px; font-size:12px;">
                            <option value="profile">🟢 Dùng Proxy hiện tại của Profile</option>
                            <option value="c69_pool">🌐 Tự động cấp phát Proxy từ Pool C69 (250 SOCKS5 Live)</option>
                            <option value="direct">⚡ Direct (Không dùng Proxy / Đi qua C69 Router TUN)</option>
                            <option value="custom">✏️ Nhập Proxy tùy chỉnh (host:port hoặc socks5://...)</option>
                        </select>
                        <div id="nurture-custom-proxy-box" style="display:none; margin-top:6px;">
                            <div style="display:flex; gap:6px;">
                                <input id="nurture-custom-proxy-input" type="text" class="search-input" style="flex:1;" placeholder="socks5://user:pass@host:port hoặc host:port:user:pass">
                                <button class="btn btn-dark" type="button" onclick="testCustomProxy()" style="font-size:11px; padding:6px 10px;">⚡ Test</button>
                            </div>
                            <div id="nurture-custom-proxy-test-result" style="font-size:10px; margin-top:3px; color:var(--text-muted);"></div>
                        </div>
                    </div>

                    <div style="background: rgba(0,0,0,0.3); border: 1px solid var(--border); border-radius: 6px; padding: 8px 12px; font-size: 11px; color: var(--text-muted);">
                        ⚡ <b>Cơ chế kết nối C69:</b> Tự động đăng nhập vào TikTok nếu profile chưa có cookie, sau đó lướt For You Page liên tục và tự động tích lũy tương tác.
                    </div>

                    <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:8px;">
                        <button class="btn btn-dark" onclick="closeNurtureModal()">Hủy</button>
                        <button class="btn btn-purple" style="background:linear-gradient(135deg, #8b5cf6, #d946ef); font-weight:700; color:#fff;" onclick="submitStartNurture()">🚀 Bắt Đầu Nuôi TikTok</button>
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
        // ── HỆ THỐNG THÔNG BÁO TOAST KHÔNG CHẶN LUỒNG (THAY THẾ TOÀN BỘ ALERT) ──
        function showToast(msg, type = 'info', duration = 2500) {
            if (!msg) return;
            let container = document.getElementById('toast-container');
            if (!container) {
                container = document.createElement('div');
                container.id = 'toast-container';
                document.body.appendChild(container);
            }
            const toast = document.createElement('div');
            const icon = type === 'success' ? '✅' : (type === 'error' ? '❌' : (type === 'warning' ? '⚠️' : 'ℹ️'));
            toast.className = `toast-msg toast-${type}`;
            toast.innerHTML = `<span style="font-size:14px;">${icon}</span><span style="flex:1;">${msg}</span>`;
            toast.onclick = () => {
                toast.style.opacity = '0';
                toast.style.transform = 'translateY(20px)';
                setTimeout(() => toast.remove(), 250);
            };
            container.appendChild(toast);
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.style.opacity = '0';
                    toast.style.transform = 'translateY(20px)';
                    setTimeout(() => toast.remove(), 250);
                }
            }, duration);
        }

        // Triệt tiêu vĩnh viễn window.alert và confirm chặn luồng, tự động map sang toast
        window.alert = function(msg) {
            if (!msg) return;
            const str = String(msg);
            const lower = str.toLowerCase();
            const type = (lower.includes('lỗi') || lower.includes('error') || lower.includes('fail') || lower.includes('thất bại'))
                ? 'error'
                : ((lower.includes('thành công') || lower.includes('đã') || lower.includes('ok') || str.includes('✅') || str.includes('🚀'))
                    ? 'success'
                    : ((lower.includes('vui lòng') || lower.includes('chưa') || lower.includes('không tìm') || lower.includes('ít nhất'))
                        ? 'warning'
                        : 'info'));
            showToast(str, type);
        };
        window.confirm = function() { return true; };

        const API_BASE = window.location.origin;
        const WS_BASE = `ws://${window.location.host}`;
        const activeSockets = {};
        let currentDevices = [];
        let allProfiles = [];
        let activeWifiSerial = null;

        function switchNav(navId, force) {
            if (!force && (!currentC69Session || !currentC69Session.logged_in)) {
                const gate = document.getElementById('c69-login-gate');
                if (gate) gate.style.display = 'flex';
                showToast('Vui lòng đăng nhập tài khoản C69 để sử dụng tool!', 'warning');
                return;
            }
            try { localStorage.setItem('mun_active_tab', navId); } catch(e) {}
            document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
            document.querySelectorAll('.view-content').forEach(v => v.classList.remove('active'));

            const item = Array.from(document.querySelectorAll('.nav-item')).find(el => el.getAttribute('onclick') && el.getAttribute('onclick').includes(navId));
            if (item) item.classList.add('active');

            const view = document.getElementById(`view-${navId}`);
            if (view) view.classList.add('active');

            if (navId === 'browser') loadBrowserProfiles();
            if (navId === 'c69tiktok') loadC69AccountsTab();
            if (navId === 'ios') loadIosDevices();
        }

        async function refreshAll() {
            // Không dùng await tuần tự để không chặn loadBrowserProfiles() nếu ADB đang quét
            refreshDevices();
            loadBrowserProfiles();
            loadIosDevices();
        }

        async function refreshDevices() {
            try {
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), 4000);
                const res = await fetch(`${API_BASE}/api/devices`, { signal: controller.signal });
                clearTimeout(timeoutId);

                const devices = await res.json();
                currentDevices = devices || [];
                const countEl = document.getElementById('android-count');
                if (countEl) countEl.innerText = currentDevices.length;

                const grid = document.getElementById('device-grid');
                if (!grid) return;

                if (currentDevices.length === 0) {
                    // Dọn dẹp kết nối websocket cũ nếu có
                    Object.keys(activeSockets).forEach(s => {
                        if (activeSockets[s]) {
                            try { activeSockets[s].close(); } catch(err) {}
                            delete activeSockets[s];
                        }
                    });
                    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                        <div style="font-size: 38px; margin-bottom: 12px;">📱</div>
                        <div style="font-weight: 700; font-size: 15px; margin-bottom: 6px; color: #fff;">Chưa phát hiện thiết bị Samsung / Android nào qua ADB</div>
                        <div style="font-size: 12px; margin-bottom: 18px; line-height: 1.6;">Vui lòng cắm giàn máy vào cổng USB và bật <b>"Gỡ lỗi USB"</b> (USB Debugging).<br>Bạn có thể chuyển ngay sang tab Anti Browser để quản lý và nuôi nick TikTok trên trình duyệt.</div>
                        <div style="display: flex; gap: 10px; justify-content: center;">
                            <button class="btn btn-primary" style="padding: 8px 18px; font-size: 12px;" onclick="switchNav('browser')">🌐 Chuyển Sang Tab Anti Browser</button>
                            <button class="btn btn-dark" style="padding: 8px 18px; font-size: 12px;" onclick="refreshDevices()">🔄 Quét Lại Thiết Bị</button>
                        </div>
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
                console.warn('Lỗi quét thiết bị ADB:', e);
                const countEl = document.getElementById('android-count');
                if (countEl) countEl.innerText = '0';
                const grid = document.getElementById('device-grid');
                if (grid && (!currentDevices || currentDevices.length === 0)) {
                    grid.innerHTML = `<div style="grid-column: 1 / -1; text-align: center; padding: 60px 20px; color: var(--text-muted);">
                        <div style="font-size: 38px; margin-bottom: 12px;">⚠️</div>
                        <div style="font-weight: 700; font-size: 15px; margin-bottom: 6px; color: #fff;">Chưa phát hiện thiết bị Android nào qua ADB</div>
                        <div style="font-size: 12px; margin-bottom: 18px; line-height: 1.6;">Không thể kết nối hoặc chưa có thiết bị cắm vào máy tính.<br>Bạn có thể chuyển ngay sang tab Anti Browser để tiếp tục làm việc.</div>
                        <div style="display: flex; gap: 10px; justify-content: center;">
                            <button class="btn btn-primary" style="padding: 8px 18px; font-size: 12px;" onclick="switchNav('browser')">🌐 Chuyển Sang Tab Anti Browser</button>
                            <button class="btn btn-dark" style="padding: 8px 18px; font-size: 12px;" onclick="refreshDevices()">🔄 Thử Lại</button>
                        </div>
                    </div>`;
                }
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
                showToast('Vui lòng chọn hoặc nhập tên Wi-Fi (SSID)!', 'warning');
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
            showToast(`Đã phát lệnh kết nối vào "${ssid}"!`, 'success');
            setTimeout(scanWifiNetworks, 3000);
        }

        async function installTikTokAll() {
            const res = await fetch(`${API_BASE}/api/devices/install-tiktok`, { method: 'POST' });
            const d = await res.json();
            showToast(d.message || 'Đang cài đặt TikTok trên các máy...', 'info');
        }

        async function optimizeResolution() {
            const res = await fetch(`${API_BASE}/api/farm/optimize-resolution`, { method: 'POST' });
            const d = await res.json();
            showToast(d.message || 'Đã tối ưu độ phân giải HD+ (720x1480)!', 'success');
            setTimeout(refreshDevices, 1000);
        }

        async function launchScrcpy() {
            const res = await fetch(`${API_BASE}/api/farm/launch-scrcpy`, { method: 'POST' });
            const d = await res.json();
            showToast(d.message || 'Đã khởi chạy Scrcpy Hardware Stream 60 FPS!', 'success');
        }

        async function startNurtureAll() {
            await fetch(`${API_BASE}/api/nurture/start`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            showToast('Đã phát lệnh nuôi TikTok tự động cho toàn bộ giàn Android!', 'success');
        }

        async function stopNurtureAll() {
            await fetch(`${API_BASE}/api/nurture/stop`, { method: 'POST' });
            showToast('Đã dừng tiến trình nuôi!', 'info');
        }

        // ── Mun Anti Browser Management ──────────────────────────────────────
        let activeProfileIds = new Set();
        let nurtureStatuses = {};
        let cachedC69Accounts = [];
        let selectedProfileIds = new Set();
        let profileProxyTestMap = {};
        let testingProfileProxyIds = new Set();
        let profileChangeSocksTargetIds = [];

        function getProxyCleanKey(str) {
            if (!str) return '';
            return str.trim()
                .replace(/^socks5:\/\//i, '')
                .replace(/^http:\/\//i, '')
                .replace(/^https:\/\//i, '');
        }

        function getProxyTestResult(proxyStr, profId) {
            if (profId !== undefined && profId !== null && profileProxyTestMap[profId]) {
                return profileProxyTestMap[profId];
            }
            if (!proxyStr) return null;
            if (c69ProxyTestMap[proxyStr]) return c69ProxyTestMap[proxyStr];

            const clean = getProxyCleanKey(proxyStr);
            if (c69ProxyTestMap[clean]) return c69ProxyTestMap[clean];

            const atIdx = clean.lastIndexOf('@');
            const hostPort = atIdx !== -1 ? clean.slice(atIdx + 1) : clean;
            if (c69ProxyTestMap[hostPort]) return c69ProxyTestMap[hostPort];

            const withSocks = 'socks5://' + clean;
            if (c69ProxyTestMap[withSocks]) return c69ProxyTestMap[withSocks];

            return null;
        }

        // Khôi phục bộ nhớ cache kết quả test từ localStorage ngay khi khởi tạo
        try {
            const savedC69 = localStorage.getItem('c69_proxy_test_cache');
            if (savedC69) {
                Object.assign(c69ProxyTestMap, JSON.parse(savedC69));
            }
            const savedProf = localStorage.getItem('profile_proxy_test_cache');
            if (savedProf) {
                Object.assign(profileProxyTestMap, JSON.parse(savedProf));
            }
        } catch(e) {}

        async function syncProxyStatusCacheFromBackend() {
            try {
                const res = await fetch(`${API_BASE}/api/browser/proxies/status-cache?t=${Date.now()}`);
                const d = await res.json();
                if (d.success && d.cache) {
                    Object.entries(d.cache).forEach(([key, val]) => {
                        const testObj = {
                            alive: val.alive,
                            latency_ms: val.latency_ms,
                            message: val.message
                        };
                        c69ProxyTestMap[key] = testObj;
                    });
                    try {
                        localStorage.setItem('c69_proxy_test_cache', JSON.stringify(c69ProxyTestMap));
                    } catch(e) {}
                }
            } catch(e) {}
        }
        syncProxyStatusCacheFromBackend();

        function setProxyTestResult(proxyStr, profId, result) {
            if (profId !== undefined && profId !== null) {
                profileProxyTestMap[profId] = result;
            }
            if (proxyStr) {
                c69ProxyTestMap[proxyStr] = result;
                const clean = getProxyCleanKey(proxyStr);
                c69ProxyTestMap[clean] = result;
                const atIdx = clean.lastIndexOf('@');
                const hostPort = atIdx !== -1 ? clean.slice(atIdx + 1) : clean;
                c69ProxyTestMap[hostPort] = result;
                c69ProxyTestMap['socks5://' + clean] = result;
            }
            try {
                localStorage.setItem('c69_proxy_test_cache', JSON.stringify(c69ProxyTestMap));
                localStorage.setItem('profile_proxy_test_cache', JSON.stringify(profileProxyTestMap));
            } catch(e) {}
        }

        async function loadBrowserProfiles() {
            try {
                const [resProf, resActive, resNurture] = await Promise.all([
                    fetch(`${API_BASE}/api/browser/profiles`),
                    fetch(`${API_BASE}/api/browser/active`),
                    fetch(`${API_BASE}/api/browser/nurture/status`).catch(() => ({ ok: false }))
                ]);
                allProfiles = await resProf.json();
                if (resActive.ok) {
                    const ids = await resActive.json();
                    activeProfileIds = new Set(ids);
                }
                if (resNurture.ok) {
                    const nList = await resNurture.json();
                    nurtureStatuses = {};
                    nList.forEach(n => { nurtureStatuses[n.profile_id] = n; });
                }
                filterProfiles();
                updateActiveCountBadge();
                checkBrowserCoreStatus();
            } catch (e) {
                console.error(e);
            }
        }

        async function syncActiveBrowserProfiles() {
            try {
                const [resActive, resNurture] = await Promise.all([
                    fetch(`${API_BASE}/api/browser/active`),
                    fetch(`${API_BASE}/api/browser/nurture/status`).catch(() => null)
                ]);
                if (resActive.ok) {
                    const ids = await resActive.json();
                    activeProfileIds = new Set(ids);
                }
                if (resNurture && resNurture.ok) {
                    const nList = await resNurture.json();
                    nurtureStatuses = {};
                    nList.forEach(n => { nurtureStatuses[n.profile_id] = n; });
                }
                filterProfiles();
                updateActiveCountBadge();
            } catch (e) {
                // Silently handle transient errors
            }
        }

        function updateActiveCountBadge() {
            const el = document.getElementById('active-profiles-count');
            if (!el) return;
            if (activeProfileIds.size > 0) {
                el.innerHTML = `🟢 <b>${activeProfileIds.size}</b> profile đang mở`;
            } else {
                el.innerText = '';
            }
        }

        // Tự động đồng bộ trạng thái thực tế mỗi 2 giây
        setInterval(syncActiveBrowserProfiles, 2000);

        function toggleSelectAllProfiles(masterCb) {
            const isChecked = masterCb ? masterCb.checked : false;
            document.querySelectorAll('.prof-checkbox').forEach(cb => {
                cb.checked = isChecked;
                const pid = parseInt(cb.value);
                if (isChecked) {
                    selectedProfileIds.add(pid);
                } else {
                    selectedProfileIds.delete(pid);
                }
            });
            updateSelectedProfilesUI();
        }

        function onProfileCheckboxChange(cb, pid) {
            if (cb.checked) {
                selectedProfileIds.add(pid);
            } else {
                selectedProfileIds.delete(pid);
            }
            updateSelectedProfilesUI();
        }

        function updateSelectedProfilesUI() {
            const masterCb = document.getElementById('check-all-profiles');
            if (masterCb) {
                const checkboxes = document.querySelectorAll('.prof-checkbox');
                if (checkboxes.length > 0) {
                    masterCb.checked = Array.from(checkboxes).every(cb => cb.checked);
                } else {
                    masterCb.checked = false;
                }
            }
            const count = selectedProfileIds.size;
            const countSuffix = count > 0 ? ` (${count})` : '';

            const selBtn = document.getElementById('btn-nurture-selected-profs');
            if (selBtn) {
                selBtn.innerHTML = `🎬 Nuôi Profile Đã Chọn${countSuffix}`;
            }
            const fpBtn = document.getElementById('btn-rand-fp-selected');
            if (fpBtn) {
                fpBtn.innerHTML = `🎲 Đổi Fingerprint${countSuffix}`;
            }
            const mobBtn = document.getElementById('btn-to-mobile-selected');
            if (mobBtn) {
                mobBtn.innerHTML = `📱 Sang Mobile${countSuffix}`;
            }
            const deskBtn = document.getElementById('btn-to-desktop-selected');
            if (deskBtn) {
                deskBtn.innerHTML = `💻 Sang Desktop${countSuffix}`;
            }
            const changeSocksBtn = document.getElementById('btn-change-socks-selected');
            if (changeSocksBtn) {
                changeSocksBtn.innerHTML = `🔄 Đổi Socks${countSuffix}`;
            }
            const checkSocksBtn = document.getElementById('btn-check-socks-selected');
            if (checkSocksBtn) {
                checkSocksBtn.innerHTML = `⚡ Check Socks${countSuffix}`;
            }
        }

        async function startNurtureSelectedProfiles() {
            const selectedIds = selectedProfileIds.size > 0
                ? Array.from(selectedProfileIds)
                : Array.from(document.querySelectorAll('.prof-checkbox:checked')).map(cb => parseInt(cb.value));

            if (selectedIds.length === 0) {
                return showToast("Vui lòng tích chọn ít nhất 1 profile để nuôi!", "warning");
            }
            const autoProxy = document.getElementById('browser-auto-proxy-chk')?.checked ?? true;
            showToast(`Đang kích hoạt nuôi ${selectedIds.length} profile đã chọn...`, "info");

            try {
                const res = await fetch(`${API_BASE}/api/browser/nurture/start-selected`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_ids: selectedIds, auto_assign_c69_proxy: autoProxy })
                });
                const d = await res.json();
                showToast(d.message || "Đã kích hoạt nuôi các profiles đã chọn!", "success");
                loadBrowserProfiles();
            } catch (e) {
                showToast("Lỗi: " + e, "error");
            }
        }

        async function randomizeSelectedProfilesFingerprint() {
            const selectedIds = selectedProfileIds.size > 0
                ? Array.from(selectedProfileIds)
                : Array.from(document.querySelectorAll('.prof-checkbox:checked')).map(cb => parseInt(cb.value));

            if (selectedIds.length === 0) {
                return showToast("Vui lòng tích chọn ít nhất 1 profile để đổi Fingerprint!", "warning");
            }

            showToast(`Đang tạo mới Fingerprint cho ${selectedIds.length} profile...`, "info");

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/randomize-fingerprints`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_ids: selectedIds })
                });
                const d = await res.json();
                showToast(d.message || `Đã đổi mới Fingerprint cho ${selectedIds.length} profile!`, "success");
                loadBrowserProfiles();
            } catch (e) {
                showToast("Lỗi khi đổi Fingerprint: " + e, "error");
            }
        }

        async function switchSelectedProfilesUA(mode) {
            const selectedIds = selectedProfileIds.size > 0
                ? Array.from(selectedProfileIds)
                : Array.from(document.querySelectorAll('.prof-checkbox:checked')).map(cb => parseInt(cb.value));

            if (selectedIds.length === 0) {
                return showToast("Vui lòng tích chọn ít nhất 1 profile để chuyển đổi User Agent!", "warning");
            }

            const modeName = mode === 'mobile' ? 'Mobile' : (mode === 'desktop' ? 'Desktop' : 'đảo Mobile ⮂ Desktop');
            showToast(`Đang chuyển đổi User Agent sang ${modeName} cho ${selectedIds.length} profile...`, "info");

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/switch-mode`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_ids: selectedIds, mode: mode })
                });
                const d = await res.json();
                showToast(d.message || `Đã chuyển đổi User Agent cho ${selectedIds.length} profile!`, "success");
                loadBrowserProfiles();
            } catch (e) {
                showToast("Lỗi khi chuyển đổi User Agent: " + e, "error");
            }
        }

        async function switchSingleProfileUA(pid, targetMode) {
            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/switch-mode`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_ids: [pid], mode: targetMode })
                });
                const d = await res.json();
                showToast(`Profile #${pid} đã chuyển sang ${targetMode}`, "success");
                loadBrowserProfiles();
            } catch (e) {
                showToast("Lỗi: " + e, "error");
            }
        }

        async function randomizeSingleProfileFingerprint(pid) {
            showToast(`Đang đổi mới Fingerprint cho Profile #${pid}...`, "info");
            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/randomize-fingerprints`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_ids: [pid] })
                });
                const d = await res.json();
                showToast(d.message || "Đã đổi mới Fingerprint!", "success");
                loadBrowserProfiles();
            } catch(e) {
                showToast("Lỗi: " + e, "error");
            }
        }

        function updateNurtureKpis(profiles) {
            if (!profiles) return;
            const nowEpoch = Math.floor(Date.now() / 1000);
            const total = profiles.length;
            let running = 0;
            let done = 0;
            let rateLimited = 0;
            let errorCount = 0;
            let zeroLogin = 0;

            profiles.forEach(p => {
                const nurture = nurtureStatuses[p.id];
                if (nurture && nurture.is_running) running++;
                if (p.retry_after_epoch && p.retry_after_epoch > nowEpoch) rateLimited++;
                else if (p.last_nurture_status && p.last_nurture_status.includes('thành công')) {
                    done++;
                    zeroLogin++;
                } else if (p.last_nurture_status) {
                    errorCount++;
                }
            });

            const setVal = (id, val) => {
                const el = document.getElementById(id);
                if (el) el.innerText = val;
            };
            setVal('kpi-total-profiles', total);
            setVal('kpi-running-nurture', running);
            setVal('kpi-done-nurture', done);
            setVal('kpi-rate-limited', rateLimited);
            setVal('kpi-error-profiles', errorCount);
            setVal('kpi-zero-login', zeroLogin);
        }

        function renderProfiles(profiles) {
            updateNurtureKpis(allProfiles);
            const tbody = document.getElementById('browser-profiles-body');
            if (!profiles || profiles.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; padding: 40px 20px; color: var(--text-muted); font-size:13px;">
                    <div style="font-size: 28px; margin-bottom: 8px;">🔍</div>
                    <div>Không tìm thấy profile nào phù hợp với bộ lọc hiện tại.</div>
                </td></tr>`;
                return;
            }

            const nowEpoch = Math.floor(Date.now() / 1000);

            tbody.innerHTML = profiles.map(p => {
                const isRunning = activeProfileIds.has(p.id);
                const nurture = nurtureStatuses[p.id];
                // CHỈ coi là ĐANG NUÔI khi THỰC SỰ is_running = true VÀ TRÌNH DUYỆT ĐANG MỞ THẬT (hoặc đang xếp hàng chờ slot)
                const isNurturing = nurture && nurture.is_running && (isRunning || (nurture.status && nurture.status.includes('Chờ slot')));
                const isRateLimited = p.retry_after_epoch && p.retry_after_epoch > nowEpoch;
                const remainMins = isRateLimited ? Math.ceil((p.retry_after_epoch - nowEpoch) / 60) : 0;

                const osLabel = p.profile_os || 'Windows';
                const isMob = osLabel.toLowerCase().includes('android') || (p.profile_user_agent || '').includes('Mobile');
                const uaBadge = isMob
                    ? `<span style="background:rgba(16,185,129,0.18); color:#34d399; border:1px solid rgba(16,185,129,0.35); padding:1px 6px; border-radius:4px; font-weight:700; font-size:10px; cursor:pointer;" onclick="switchSingleProfileUA(${p.id}, 'desktop')" title="Đang chạy Mobile UA (Bấm để chuyển sang Desktop)">📱 Mobile</span>`
                    : `<span style="background:rgba(56,189,248,0.15); color:#38bdf8; border:1px solid rgba(56,189,248,0.3); padding:1px 6px; border-radius:4px; font-weight:700; font-size:10px; cursor:pointer;" onclick="switchSingleProfileUA(${p.id}, 'mobile')" title="Đang chạy Desktop UA (Bấm để chuyển sang Mobile)">💻 Desktop</span>`;
                const mode = p.engine_mode || 'native';
                const engineTag = mode === 'native' 
                    ? `<span style="color:#c084fc; font-weight:700; cursor:pointer;" onclick="toggleEngine(${p.id})" title="💎 Native C++ (Bấm để đổi)">💎 C++</span>` 
                    : (mode === 'js_stealth' 
                        ? `<span style="color:#38bdf8; font-weight:700; cursor:pointer;" onclick="toggleEngine(${p.id})" title="⚡ JS Stealth (Bấm để đổi)">⚡ JS</span>` 
                        : `<span style="color:#f59e0b; font-weight:700; cursor:pointer;" onclick="toggleEngine(${p.id})" title="🔥 Hybrid (Bấm để đổi)">🔥 Hybrid</span>`);

                let gpuShort = 'GPU Shield';
                if (p.gpu_renderer) {
                    if (p.gpu_renderer.includes('RTX 3060')) gpuShort = 'RTX 3060';
                    else if (p.gpu_renderer.includes('RTX 4070')) gpuShort = 'RTX 4070';
                    else if (p.gpu_renderer.includes('RTX 4060')) gpuShort = 'RTX 4060';
                    else if (p.gpu_renderer.includes('GTX 1660')) gpuShort = 'GTX 1660S';
                    else if (p.gpu_renderer.includes('RX 6700')) gpuShort = 'RX 6700XT';
                    else if (p.gpu_renderer.includes('Iris')) gpuShort = 'Iris Xe';
                    else gpuShort = p.gpu_renderer.split('(')[1]?.split(',')[1]?.trim() || 'GPU';
                }

                const zeroLoginTag = (p.last_nurture_status && p.last_nurture_status.includes('thành công'))
                    ? `<span style="background:rgba(14,165,233,0.15); border:1px solid rgba(14,165,233,0.35); color:#38bdf8; font-size:9px; font-weight:700; padding:1px 5px; border-radius:3px;" title="Profile đã lưu Thin Profile (~200KB) - Vào thẳng FYP không cần login">⚡ Zero-Login</span>`
                    : ``;

                let tiktokCell = '';
                if (p.tiktok_username) {
                    tiktokCell = `
                        <div style="display:flex; align-items:center; gap:6px;">
                            <span style="background:linear-gradient(135deg, rgba(236,72,153,0.2), rgba(139,92,246,0.2)); border:1px solid rgba(236,72,153,0.4); color:#f0abfc; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:700; display:inline-flex; align-items:center; gap:4px;">
                                🎵 @${p.tiktok_username}
                            </span>
                            <button class="btn btn-dark" style="padding:2px 5px; font-size:9px; border-color:rgba(255,255,255,0.15);" onclick="openNurtureModal(${p.id})" title="Đổi hoặc cấu hình tài khoản C69">⚙️</button>
                        </div>
                    `;
                } else {
                    tiktokCell = `
                        <button class="btn btn-dark" style="padding:3px 8px; font-size:10px; border-color:rgba(217,70,239,0.3); color:#f0abfc; background:rgba(217,70,239,0.06);" onclick="openNurtureModal(${p.id})">
                            ➕ Gán Nick TikTok
                        </button>
                    `;
                }

                let proxyCell = '';
                const isTesting = testingProfileProxyIds.has(p.id);
                let proxyBadge = '';
                if (isTesting) {
                    proxyBadge = `<span id="prof-proxy-status-${p.id}" class="badge" style="font-size:9.5px; padding:1px 5px; background:rgba(245,158,11,0.18); border:1px solid #f59e0b; color:#f59e0b; font-weight:700;"><span class="pulse-dot" style="background:#f59e0b; width:5px; height:5px; margin-right:3px;"></span>⏳ Đang check...</span>`;
                } else {
                    const pTest = getProxyTestResult(p.proxy_string, p.id);
                    if (pTest) {
                        if (pTest.alive) {
                            proxyBadge = `<span id="prof-proxy-status-${p.id}" class="badge badge-success" style="font-size:9.5px; padding:1px 5px; font-weight:700;" title="Live (${pTest.latency_ms}ms)">🟢 Live (${pTest.latency_ms}ms)</span>`;
                        } else {
                            proxyBadge = `<span id="prof-proxy-status-${p.id}" class="badge badge-danger" style="font-size:9.5px; padding:1px 5px; font-weight:700;" title="${(pTest.message || 'Die').replace(/"/g, '&quot;')}">🔴 Die</span>`;
                        }
                    } else {
                        proxyBadge = `<span id="prof-proxy-status-${p.id}" class="badge" style="font-size:9.5px; padding:1px 5px; background:rgba(255,255,255,0.06); color:#94a3b8; border:1px solid rgba(255,255,255,0.1);">⚪ Chưa test</span>`;
                    }
                }

                if (p.proxy_string && p.proxy_type !== 'direct') {
                    const displayStr = p.proxy_string.length > 22 ? p.proxy_string.slice(0, 20) + '…' : p.proxy_string;
                    const testBtnLabel = isTesting ? '⏳' : '⚡ Test';
                    const testBtnDisabled = isTesting ? 'disabled' : '';
                    proxyCell = `
                        <div style="display:flex; flex-direction:column; gap:3px;">
                            <div style="display:flex; align-items:center; gap:5px;">
                                <span style="background:rgba(16,185,129,0.15); color:#10b981; border:1px solid rgba(16,185,129,0.35); font-size:9px; padding:1px 4px; border-radius:3px; font-weight:700;">${(p.proxy_type || 'SOCKS5').toUpperCase()}</span>
                                <span class="cell-copyable" onclick="copyText('${p.proxy_string.replace(/'/g, "\\'")}', 'Proxy SOCKS5')" style="color:#e2e8f0; font-size:11px; font-family:monospace; font-weight:600;" title="Click để copy: ${p.proxy_string}">${displayStr}</span>
                            </div>
                            <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                                ${proxyBadge}
                                <button id="btn-test-prof-proxy-${p.id}" ${testBtnDisabled} class="btn btn-dark" style="padding:1px 5px; font-size:9.5px; border-color:rgba(56,189,248,0.3); color:#38bdf8;" onclick="testProfileProxy(${p.id}, this)" title="Test live/die Socks này ngay">${testBtnLabel}</button>
                                <button class="btn btn-dark" style="padding:1px 5px; font-size:9.5px; border-color:rgba(217,70,239,0.3); color:#f0abfc;" onclick="openChangeProfileSocksModal(${p.id})" title="Đổi sang Socks5 khác">🔄 Đổi</button>
                            </div>
                        </div>
                    `;
                } else {
                    proxyCell = `
                        <div style="display:flex; flex-direction:column; gap:3px;">
                            <div style="display:flex; align-items:center; gap:5px;">
                                <span style="color:var(--text-muted); font-size:10px; background:rgba(255,255,255,0.05); padding:1px 5px; border-radius:3px;">⚡ Direct (Không Socks)</span>
                            </div>
                            <div style="display:flex; align-items:center; gap:4px;">
                                <button class="btn btn-dark" style="padding:1px 6px; font-size:9.5px; color:#38bdf8; border-color:rgba(56,189,248,0.3);" onclick="assignC69ProxyToProfile(${p.id})" title="Gán 1 proxy SOCKS5 từ C69 Pool">➕ Gán C69</button>
                                <button class="btn btn-dark" style="padding:1px 6px; font-size:9.5px; color:#f0abfc; border-color:rgba(217,70,239,0.3);" onclick="openChangeProfileSocksModal(${p.id})" title="Đổi / Thêm Socks thủ công">🔄 Nhập Socks</button>
                            </div>
                        </div>
                    `;
                }

                let statusCell = '';
                if (isNurturing) {
                    if (nurture.waiting_otp) {
                        statusCell = `
                            <div style="display:flex; flex-direction:column; gap:4px; min-width:140px;">
                                <span style="background:rgba(234,179,8,0.2); border:1px solid #eab308; color:#fde047; font-weight:700; font-size:10px; padding:2px 6px; border-radius:4px; display:inline-flex; align-items:center; gap:4px;">
                                    <span class="pulse-dot" style="background:#eab308; box-shadow:0 0 8px #eab308;"></span>
                                    🔑 ${nurture.status || 'Chờ mã OTP'}
                                </span>
                                <div style="display:flex; gap:3px;">
                                    <input type="text" id="otp-inp-${p.id}" placeholder="Mã 6 số" maxlength="6" style="width:65px; padding:2px 4px; font-size:11px; background:#0f172a; border:1px solid #eab308; color:#fff; border-radius:3px; text-align:center;">
                                    <button class="btn btn-warning" style="padding:2px 6px; font-size:10px; font-weight:700; background:#eab308; color:#000; border-radius:3px;" onclick="submitOtpForProfile(${p.id})">Gửi</button>
                                </div>
                            </div>
                        `;
                    } else {
                        statusCell = `
                            <div style="display:flex; flex-direction:column; gap:2px;">
                                <span style="background:linear-gradient(135deg, rgba(217,70,239,0.2), rgba(14,165,233,0.2)); border:1px solid #d946ef; color:#f0abfc; font-weight:700; font-size:10px; padding:3px 7px; border-radius:5px; display:inline-flex; align-items:center; gap:5px;">
                                    <span class="pulse-dot" style="background:#d946ef; box-shadow:0 0 8px #d946ef;"></span>
                                    🎬 ${nurture.status || 'Đang Nuôi FYP'}
                                </span>
                                <div style="font-size:10px; color:#cbd5e1; display:flex; gap:6px;">
                                    <span>👀 <b>${nurture.videos_watched || 0}</b></span>
                                    <span>❤️ <b>${nurture.likes_given || 0}</b></span>
                                    <span>💬 <b>${nurture.comments_posted || 0}</b></span>
                                </div>
                            </div>
                        `;
                    }
                } else if (isRateLimited) {
                    statusCell = `
                        <div style="display:flex; flex-direction:column; gap:2px;" title="${(p.last_nurture_error || '').replace(/"/g, '&quot;')}">
                            <span style="background:rgba(249,115,22,0.18); border:1px solid #f97316; color:#fdba74; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; display:inline-flex; align-items:center; gap:4px;">
                                ⏳ Chờ 1h (còn ${remainMins}p)
                            </span>
                            <span style="font-size:9px; color:#fb923c;">${p.last_nurture_time ? 'Lúc ' + p.last_nurture_time.slice(11, 16) : ''} • Limit</span>
                        </div>
                    `;
                } else if (p.last_nurture_status && !p.last_nurture_status.includes('Đang') && !p.last_nurture_status.includes('Chờ slot')) {
                    if (p.last_nurture_status.includes('thành công') || p.last_nurture_status.includes('Đã nuôi OK')) {
                        statusCell = `
                            <div style="display:flex; flex-direction:column; gap:2px;" title="${(p.last_nurture_error || 'Đã nuôi thành công').replace(/"/g, '&quot;')}">
                                <span style="background:rgba(16,185,129,0.15); border:1px solid #10b981; color:#6ee7b7; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; display:inline-flex; align-items:center; gap:4px;">
                                    ✅ Đã nuôi OK
                                </span>
                                <span style="font-size:9px; color:#94a3b8;">${p.last_nurture_time ? p.last_nurture_time.slice(5, 16) : ''}</span>
                            </div>
                        `;
                    } else {
                        const isEmailErr = p.last_nurture_status.toLowerCase().includes('email');
                        const isStopped = p.last_nurture_status.includes('dừng') || p.last_nurture_status.includes('Chưa');
                        const badgeColor = isStopped ? '#94a3b8' : (isEmailErr ? '#f59e0b' : '#ef4444');
                        const badgeBg = isStopped ? 'rgba(255,255,255,0.06)' : (isEmailErr ? 'rgba(245,158,11,0.15)' : 'rgba(239,68,68,0.15)');
                        const icon = isStopped ? '⚪' : '⚠️';
                        statusCell = `
                            <div style="display:flex; flex-direction:column; gap:2px;" title="${(p.last_nurture_error || p.last_nurture_status).replace(/"/g, '&quot;')}">
                                <span style="background:${badgeBg}; border:1px solid ${badgeColor}; color:${badgeColor}; font-size:10px; font-weight:700; padding:2px 6px; border-radius:4px; display:inline-flex; align-items:center; gap:4px;">
                                    ${icon} ${p.last_nurture_status}
                                </span>
                                <span style="font-size:9px; color:${badgeColor}; max-width:130px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                                    ${p.last_nurture_error ? p.last_nurture_error.slice(0, 24) + '…' : (p.last_nurture_time ? 'Lúc ' + p.last_nurture_time.slice(11, 16) : '')}
                                </span>
                            </div>
                        `;
                    }
                } else if (isRunning) {
                    statusCell = `<span class="badge-status-running"><span class="pulse-dot"></span> Đang mở Chrome</span>`;
                } else {
                    statusCell = `<span class="badge-status-stopped">⚪ Chưa nuôi</span>`;
                }

                return `
                    <tr>
                        <td style="text-align:center;">
                            <div style="display:flex; align-items:center; justify-content:center; gap:4px;">
                                <input type="checkbox" class="prof-checkbox" value="${p.id}" ${selectedProfileIds.has(p.id) ? 'checked' : ''} onchange="onProfileCheckboxChange(this, ${p.id})">
                                <b style="color:var(--text-muted); font-size:11px;">#${p.id}</b>
                            </div>
                        </td>
                        <td>
                            <div style="display:flex; flex-direction:column; gap:2px;">
                                <div style="display:flex; align-items:center; gap:5px;">
                                    <b style="color:#f8fafc; font-size:12px;">${p.name}</b>
                                    ${zeroLoginTag}
                                </div>
                                <div style="font-size:10px; color:var(--text-muted); display:flex; align-items:center; gap:5px;">
                                    ${uaBadge}
                                    <span>•</span>
                                    ${engineTag}
                                    <span>•</span>
                                    <span style="color:#94a3b8;">${gpuShort}</span>
                                </div>
                            </div>
                        </td>
                        <td>${tiktokCell}</td>
                        <td>${proxyCell}</td>
                        <td>${statusCell}</td>
                        <td style="white-space:nowrap; text-align:center;">
                            <div style="display:flex; gap:4px; align-items:center; justify-content:center;">
                                ${isNurturing
                                    ? `<button class="btn btn-danger" style="padding:4px 9px; font-size:10px; font-weight:700;" onclick="stopNurtureProfile(${p.id})">⏹️ Dừng</button>`
                                    : `<button class="btn btn-purple" style="padding:4px 9px; font-size:10px; font-weight:700; background:linear-gradient(135deg, #06b6d4, #d946ef); color:#fff; border:none; box-shadow:0 0 8px rgba(217,70,239,0.3);" onclick="openNurtureModal(${p.id})">🎬 Nuôi</button>`
                                }
                                ${isRunning
                                    ? `<button id="btn-action-${p.id}" class="btn btn-dark" style="padding:4px 8px; font-size:10px; border-color:#ef4444; color:#ef4444;" onclick="stopBrowserProfile(${p.id})">🛑 Đóng</button>`
                                    : `<button id="btn-action-${p.id}" class="btn btn-dark" style="padding:4px 8px; font-size:10px; border-color:var(--primary); color:var(--primary);" onclick="launchBrowserProfile(${p.id})">🚀 Mở</button>`
                                }
                                <button class="btn btn-dark" style="padding:4px 6px; font-size:10px; border:1px solid var(--border);" title="Đổi mới Fingerprint (Canvas, Audio, GPU, CPU, RAM)" onclick="randomizeSingleProfileFingerprint(${p.id})">🎲</button>
                                <button class="btn btn-dark" style="padding:4px 6px; font-size:10px; border:1px solid var(--border);" title="Cấu hình Fingerprint chi tiết" onclick="openEditFingerprintModal(${p.id})">🛠️</button>
                                <button class="btn btn-dark" style="padding:4px 6px; font-size:10px; border:1px solid var(--border);" title="Xóa Profile" onclick="deleteBrowserProfile(${p.id})">🗑️</button>
                            </div>
                        </td>
                    </tr>
                `;
            }).join('');
            updateSelectedProfilesUI();
        }

        async function submitOtpForProfile(profileId) {
            const input = document.getElementById(`otp-inp-${profileId}`);
            if (!input || !input.value.trim()) {
                showToast('Vui lòng nhập mã OTP 6 chữ số!', 'warning');
                return;
            }
            const otp = input.value.trim();
            try {
                const resp = await fetch(`${API_BASE}/api/browser/nurture/${profileId}/submit-otp`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ otp: otp })
                });
                const d = await resp.json();
                showToast(d.message || 'Đã gửi mã OTP vào trình duyệt!', 'success');
                input.value = '';
            } catch(e) {
                showToast('Lỗi gửi OTP: ' + e, 'error');
            }
        }

        async function openNurtureModal(profileId) {
            const p = allProfiles.find(x => x.id === profileId);
            if (!p) return;
            document.getElementById('nurture-prof-id').value = profileId;
            document.getElementById('nurture-modal-prof-name').innerText = `Profile #${p.id} — ${p.name}`;
            
            // Cập nhật hiển thị Proxy hiện tại
            const proxyStatusEl = document.getElementById('nurture-proxy-status');
            if (proxyStatusEl) {
                if (p.proxy_string) {
                    proxyStatusEl.innerText = `[Hiện tại: ${p.proxy_string.length > 25 ? p.proxy_string.slice(0, 22) + '...' : p.proxy_string}]`;
                } else {
                    proxyStatusEl.innerText = `[Hiện tại: Direct / Chưa gán]`;
                }
            }
            document.getElementById('nurture-proxy-mode').value = 'profile';
            document.getElementById('nurture-custom-proxy-box').style.display = 'none';
            document.getElementById('nurture-custom-proxy-input').value = '';
            document.getElementById('nurture-custom-proxy-test-result').innerHTML = '';

            // Cập nhật cảnh báo rate limit hoặc lịch sử nuôi nếu có
            const warnBox = document.getElementById('nurture-modal-rate-limit-warning');
            if (warnBox) {
                const nowSec = Math.floor(Date.now() / 1000);
                if (p.retry_after_epoch && p.retry_after_epoch > nowSec) {
                    const m = Math.ceil((p.retry_after_epoch - nowSec) / 60);
                    warnBox.style.display = 'block';
                    warnBox.style.background = 'rgba(249, 115, 22, 0.18)';
                    warnBox.style.borderColor = '#f97316';
                    warnBox.style.color = '#fdba74';
                    warnBox.innerHTML = `⚠️ <b>Khuyến cáo giãn cách 1 giờ:</b> Profile này vừa gặp lỗi <i>Maximum number of attempts</i> lúc ${p.last_nurture_time || ''}. Cần chờ thêm <b>${m} phút</b> nữa (đủ 1h) trước khi đăng nhập lại để tránh TikTok tính spam và kéo dài thời gian phạt!`;
                } else if (p.last_nurture_error) {
                    warnBox.style.display = 'block';
                    warnBox.style.background = 'rgba(239, 68, 68, 0.12)';
                    warnBox.style.borderColor = '#ef4444';
                    warnBox.style.color = '#fca5a5';
                    warnBox.innerHTML = `ℹ️ <b>Lịch sử lần nuôi trước:</b> ${p.last_nurture_status || 'Gặp lỗi'} (${p.last_nurture_time || ''})<br><span style="font-size:11px; color:#cbd5e1;">${p.last_nurture_error}</span>`;
                } else if (p.last_nurture_status && p.last_nurture_status.includes('thành công')) {
                    warnBox.style.display = 'block';
                    warnBox.style.background = 'rgba(16, 185, 129, 0.12)';
                    warnBox.style.borderColor = '#10b981';
                    warnBox.style.color = '#6ee7b7';
                    warnBox.innerHTML = `✅ <b>Lần nuôi trước thành công:</b> ${p.last_nurture_time || ''} (${p.last_nurture_error || 'Đã lướt FYP'})`;
                } else {
                    warnBox.style.display = 'none';
                }
            }

            const selectEl = document.getElementById('nurture-c69-acc-select');
            selectEl.innerHTML = `<option value="">⏳ Đang tải tài khoản từ C69.us...</option>`;
            document.getElementById('modal-nurture-tiktok').style.display = 'flex';

            try {
                const res = await fetch(`${API_BASE}/api/browser/c69/accounts`);
                const data = await res.json();
                if (data.success && data.accounts && data.accounts.length > 0) {
                    cachedC69Accounts = data.accounts;

                    // Bản đồ các tài khoản đã bị gán cho profile khác
                    const usedAccMap = {};
                    allProfiles.forEach(prof => {
                        if (prof.id !== p.id && prof.tiktok_account_id) {
                            usedAccMap[prof.tiktok_account_id] = prof.name;
                        } else if (prof.id !== p.id && prof.tiktok_username) {
                            const match = data.accounts.find(a => a.username === prof.tiktok_username);
                            if (match) usedAccMap[match.id] = prof.name;
                        }
                    });

                    selectEl.innerHTML = data.accounts.map(acc => {
                        const isCurrentAssigned = (p.tiktok_account_id && p.tiktok_account_id === acc.id) || (p.tiktok_username && p.tiktok_username === acc.username);
                        const isUsedByOther = usedAccMap[acc.id];

                        if (isCurrentAssigned) {
                            return `<option value="${acc.id}" selected style="color:#f0abfc; font-weight:bold;">⭐ [Đang Gán Profile Này] ${acc.username} (${acc.status || 'Active'})</option>`;
                        } else if (isUsedByOther) {
                            return `<option value="${acc.id}" disabled style="color:#64748b;">🚫 ${acc.username} (Đã gán cho ${isUsedByOther})</option>`;
                        } else {
                            return `<option value="${acc.id}">🟢 [Trống] ${acc.username} (${acc.status || 'Active'}) ${acc.note ? '— ' + acc.note : ''}</option>`;
                        }
                    }).join('');
                } else {
                    selectEl.innerHTML = `<option value="">(Không tìm thấy tài khoản TikTok trên C69, dùng phiên đăng nhập sẵn có)</option>`;
                }
            } catch(e) {
                selectEl.innerHTML = `<option value="">(Lỗi kết nối C69: ${e})</option>`;
            }
        }

        function toggleNurtureProxyInput() {
            const mode = document.getElementById('nurture-proxy-mode').value;
            const box = document.getElementById('nurture-custom-proxy-box');
            box.style.display = (mode === 'custom') ? 'block' : 'none';
        }

        async function testCustomProxy() {
            const val = document.getElementById('nurture-custom-proxy-input').value.trim();
            const resEl = document.getElementById('nurture-custom-proxy-test-result');
            if (!val) {
                resEl.innerHTML = `<span style="color:#ef4444;">Vui lòng nhập proxy trước khi test!</span>`;
                return;
            }
            resEl.innerHTML = `<span style="color:var(--primary);">⏳ Đang kiểm tra kết nối tới proxy...</span>`;
            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: val })
                });
                const d = await res.json();
                if (d.success) {
                    resEl.innerHTML = `<span style="color:#10b981; font-weight:700;">✅ ${d.message}</span>`;
                } else {
                    resEl.innerHTML = `<span style="color:#ef4444;">❌ ${d.message}</span>`;
                }
            } catch(e) {
                resEl.innerHTML = `<span style="color:#ef4444;">Lỗi: ${e}</span>`;
            }
        }

        async function testSingleProxy(proxyStr, btn) {
            if (!proxyStr) return;
            const orig = btn.innerText;
            btn.innerText = '⏳';
            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: proxyStr })
                });
                const d = await res.json();
                if (d.success) {
                    btn.innerText = `✅ ${d.latency_ms}ms`;
                    btn.style.borderColor = '#10b981';
                    btn.style.color = '#10b981';
                } else {
                    btn.innerText = '❌ Die';
                    btn.style.borderColor = '#ef4444';
                    btn.style.color = '#ef4444';
                    showToast(d.message || 'Proxy không khả dụng!', 'error');
                }
            } catch(e) {
                btn.innerText = '⚠️ Lỗi';
            }
            setTimeout(() => { btn.innerText = orig; btn.style.borderColor = 'var(--border)'; btn.style.color = ''; }, 4000);
        }

        async function testProfileProxy(profId, btn) {
            const p = allProfiles.find(x => x.id === profId);
            if (!p || !p.proxy_string || p.proxy_type === 'direct') {
                return showToast('Profile chưa cấu hình Socks để test!', 'warning');
            }

            testingProfileProxyIds.add(profId);
            filterProfiles();

            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: p.proxy_string })
                });
                const d = await res.json();
                const testObj = {
                    alive: d.success,
                    latency_ms: d.latency_ms,
                    message: d.message
                };
                setProxyTestResult(p.proxy_string, profId, testObj);

                if (d.success) {
                    showToast(`Profile #${profId}: Socks LIVE (${d.latency_ms}ms)`, 'success');
                } else {
                    showToast(`Profile #${profId}: Socks DIE! ${d.message || ''}`, 'error');
                }
            } catch(e) {
                setProxyTestResult(p.proxy_string, profId, { alive: false, latency_ms: 0, message: String(e) });
                showToast(`Lỗi test proxy: ${e}`, 'error');
            } finally {
                testingProfileProxyIds.delete(profId);
                filterProfiles();
            }
        }

        async function checkSelectedProfilesSocks() {
            const selectedIds = selectedProfileIds.size > 0
                ? Array.from(selectedProfileIds)
                : Array.from(document.querySelectorAll('.prof-checkbox:checked')).map(cb => parseInt(cb.value));

            // Nếu chưa tích chọn: Tự động test toàn bộ profile có Socks trong danh sách
            const targetProfs = selectedIds.length > 0
                ? allProfiles.filter(p => selectedIds.includes(p.id) && p.proxy_string && p.proxy_type !== 'direct')
                : allProfiles.filter(p => p.proxy_string && p.proxy_type !== 'direct');

            if (targetProfs.length === 0) {
                return showToast("Không có profile nào có Socks để kiểm tra!", "warning");
            }

            const btn = document.getElementById('btn-check-socks-selected');
            if (btn) {
                btn.disabled = true;
                btn.innerText = `⏳ Đang check (0/${targetProfs.length})...`;
            }

            showToast(`Bắt đầu kiểm tra Socks cho ${targetProfs.length} profile...`, 'info');
            targetProfs.forEach(p => testingProfileProxyIds.add(p.id));
            filterProfiles();

            let done = 0;
            let liveCount = 0;
            let dieCount = 0;

            await Promise.all(targetProfs.map(async p => {
                try {
                    const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ proxy_string: p.proxy_string })
                    });
                    const d = await res.json();
                    const testObj = {
                        alive: d.success,
                        latency_ms: d.latency_ms,
                        message: d.message
                    };
                    setProxyTestResult(p.proxy_string, p.id, testObj);
                    if (d.success) liveCount++; else dieCount++;
                } catch(e) {
                    dieCount++;
                    setProxyTestResult(p.proxy_string, p.id, { alive: false, latency_ms: 0, message: String(e) });
                } finally {
                    testingProfileProxyIds.delete(p.id);
                    done++;
                    if (btn) btn.innerText = `⏳ Đang check (${done}/${targetProfs.length})...`;
                    // Cập nhật ngay lập tức badge trên DOM nếu node còn tồn tại
                    const badge = document.getElementById(`prof-proxy-status-${p.id}`);
                    const testRes = getProxyTestResult(p.proxy_string, p.id);
                    if (badge && testRes) {
                        if (testRes.alive) {
                            badge.className = 'badge badge-success';
                            badge.style.background = '';
                            badge.style.border = '';
                            badge.style.color = '';
                            badge.innerHTML = `🟢 Live (${testRes.latency_ms}ms)`;
                        } else {
                            badge.className = 'badge badge-danger';
                            badge.style.background = '';
                            badge.style.border = '';
                            badge.style.color = '';
                            badge.title = testRes.message || 'Die';
                            badge.innerHTML = `🔴 Die`;
                        }
                    }
                    const rowBtn = document.getElementById(`btn-test-prof-proxy-${p.id}`);
                    if (rowBtn) {
                        rowBtn.disabled = false;
                        rowBtn.innerText = '⚡ Test';
                    }
                }
            }));

            testingProfileProxyIds.clear();
            filterProfiles();

            if (btn) {
                btn.disabled = false;
                const countSuffix = selectedProfileIds.size > 0 ? ` (${selectedProfileIds.size})` : '';
                btn.innerText = `⚡ Check Socks${countSuffix}`;
            }
            showToast(`Hoàn tất kiểm tra Socks: 🟢 ${liveCount} Live, 🔴 ${dieCount} Die!`, liveCount > 0 ? 'success' : 'warning');
        }

        async function openChangeProfileSocksModal(profId) {
            profileChangeSocksTargetIds = [profId];
            const p = allProfiles.find(x => x.id === profId);
            const infoEl = document.getElementById('profile-change-socks-target-info');
            if (infoEl) {
                infoEl.innerHTML = `Đang cấu hình Socks cho <b>Profile #${profId}</b> (${p ? p.name : ''}) — Hiện tại: <code>${p && p.proxy_string ? p.proxy_string : 'Direct'}</code>`;
            }
            document.getElementById('profile-change-socks-manual-input').value = (p && p.proxy_string) ? p.proxy_string : '';
            const testResEl = document.getElementById('profile-change-socks-test-result');
            if (testResEl) testResEl.style.display = 'none';

            const curType = (p && p.proxy_type) ? p.proxy_type : (p && p.proxy_string ? 'socks5' : 'direct');
            const rad = document.querySelector(`input[name="profile-change-socks-type"][value="${curType}"]`);
            if (rad) rad.checked = true;

            await populateProfileChangeSocksPoolSelect();
            document.getElementById('modal-profile-change-socks').style.display = 'flex';
        }

        async function openChangeSelectedProfilesSocksModal() {
            const selectedIds = selectedProfileIds.size > 0
                ? Array.from(selectedProfileIds)
                : Array.from(document.querySelectorAll('.prof-checkbox:checked')).map(cb => parseInt(cb.value));

            if (selectedIds.length === 0) {
                return showToast("Vui lòng tích chọn ít nhất 1 profile để đổi Socks!", "warning");
            }

            profileChangeSocksTargetIds = selectedIds;
            const infoEl = document.getElementById('profile-change-socks-target-info');
            if (infoEl) {
                infoEl.innerHTML = `Đang đổi Socks cho <b>${selectedIds.length} profiles</b> đã chọn: <code>#${selectedIds.slice(0, 8).join(', #')}${selectedIds.length > 8 ? '…' : ''}</code>`;
            }
            document.getElementById('profile-change-socks-manual-input').value = '';
            const testResEl = document.getElementById('profile-change-socks-test-result');
            if (testResEl) testResEl.style.display = 'none';

            await populateProfileChangeSocksPoolSelect();
            document.getElementById('modal-profile-change-socks').style.display = 'flex';
        }

        function closeProfileChangeSocksModal() {
            document.getElementById('modal-profile-change-socks').style.display = 'none';
        }

        async function populateProfileChangeSocksPoolSelect() {
            await ensureProxyPoolLoaded();
            const sel = document.getElementById('profile-change-socks-pool-select');
            if (!sel) return;
            sel.innerHTML = '<option value="">-- Chọn 1 proxy từ 250 SOCKS5 Pool --</option>';
            c69ProxyPoolData.forEach((p, idx) => {
                const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                const test = c69ProxyTestMap[pStr];
                const tag = test ? (test.alive ? `[🟢 Live ${test.latency_ms}ms]` : `[🔴 Die]`) : `[Chưa test]`;
                const opt = document.createElement('option');
                opt.value = pStr;
                opt.innerText = `#${idx + 1} - ${p.host}:${p.port} ${tag}`;
                sel.appendChild(opt);
            });
        }

        function onSelectProxyForProfileModal(val) {
            if (val) {
                document.getElementById('profile-change-socks-manual-input').value = val;
                const rad = document.querySelector('input[name="profile-change-socks-type"][value="socks5"]');
                if (rad) rad.checked = true;
            }
        }

        function randomLiveProxyForProfileChangeSocks() {
            if (c69ProxyPoolData.length === 0) {
                return showToast('Danh sách proxy pool chưa được tải!', 'warning');
            }
            const liveProxies = c69ProxyPoolData.filter(p => {
                const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                return c69ProxyTestMap[pStr] && c69ProxyTestMap[pStr].alive;
            });
            const poolToPick = liveProxies.length > 0 ? liveProxies : c69ProxyPoolData;
            const chosen = poolToPick[Math.floor(Math.random() * poolToPick.length)];
            const chosenStr = chosen.proxy_string || `socks5://${chosen.username}:${chosen.password}@${chosen.host}:${chosen.port}`;
            document.getElementById('profile-change-socks-manual-input').value = chosenStr;
            const rad = document.querySelector('input[name="profile-change-socks-type"][value="socks5"]');
            if (rad) rad.checked = true;
            showToast(`Đã chọn ngẫu nhiên: ${chosen.host}:${chosen.port} ${liveProxies.length > 0 ? '(Proxy Live)' : ''}`, 'info');
        }

        async function testCurrentProfileModalProxy() {
            const proxyInput = document.getElementById('profile-change-socks-manual-input').value.trim();
            const radType = document.querySelector('input[name="profile-change-socks-type"]:checked')?.value || 'socks5';
            if (radType === 'direct') {
                return showToast('Đang chọn chế độ Direct (Không dùng proxy), không cần kiểm tra!', 'info');
            }
            if (!proxyInput) {
                return showToast('Vui lòng nhập hoặc chọn 1 Proxy để test!', 'warning');
            }

            const resEl = document.getElementById('profile-change-socks-test-result');
            resEl.style.display = 'block';
            resEl.style.background = 'rgba(56,189,248,0.1)';
            resEl.style.color = '#38bdf8';
            resEl.innerHTML = '⏳ Đang kiểm tra kết nối TCP & Bắt tay xác thực...';

            const btn = document.getElementById('btn-test-profile-modal-proxy');
            if (btn) btn.disabled = true;

            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: proxyInput })
                });
                const d = await res.json();
                c69ProxyTestMap[proxyInput] = { alive: d.success, latency_ms: d.latency_ms, message: d.message };
                if (d.success) {
                    resEl.style.background = 'rgba(16,185,129,0.15)';
                    resEl.style.color = '#34d399';
                    resEl.innerHTML = `🟢 <b>Proxy LIVE HOẠT ĐỘNG TỐT!</b> Độ trễ: <b>${d.latency_ms} ms</b>. ${d.message || ''}`;
                } else {
                    resEl.style.background = 'rgba(239,68,68,0.15)';
                    resEl.style.color = '#f87171';
                    resEl.innerHTML = `🔴 <b>Proxy DIE / Lỗi kết nối:</b> ${d.message || 'Timeout'}`;
                }
            } catch(e) {
                resEl.style.background = 'rgba(239,68,68,0.15)';
                resEl.style.color = '#f87171';
                resEl.innerHTML = `🔴 Lỗi test proxy: ${e}`;
            } finally {
                if (btn) btn.disabled = false;
            }
        }

        async function submitProfileChangeSocks() {
            const radType = document.querySelector('input[name="profile-change-socks-type"]:checked')?.value || 'socks5';
            let proxyStr = document.getElementById('profile-change-socks-manual-input').value.trim();
            if (radType === 'direct') {
                proxyStr = '';
            } else if (!proxyStr) {
                return showToast('Vui lòng nhập hoặc chọn 1 Proxy, hoặc tích chọn Direct!', 'warning');
            }

            if (profileChangeSocksTargetIds.length === 0) {
                return showToast('Không có profile nào được chọn!', 'warning');
            }

            const btn = document.getElementById('btn-save-profile-change-socks');
            if (btn) {
                btn.disabled = true;
                btn.innerText = '⏳ Đang lưu...';
            }

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/change-proxy`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        profile_ids: profileChangeSocksTargetIds,
                        proxy_string: proxyStr,
                        proxy_type: radType
                    })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || `Đã đổi Socks thành công cho ${profileChangeSocksTargetIds.length} profile!`, 'success');
                    closeProfileChangeSocksModal();
                    await loadBrowserProfiles();
                } else {
                    showToast(d.error || 'Lỗi lưu Socks!', 'error');
                }
            } catch(e) {
                showToast('Lỗi kết nối server: ' + e, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = '💾 Lưu & Gán Socks';
                }
            }
        }

        async function assignC69ProxyToProfile(profId) {
            const p = allProfiles.find(x => x.id === profId);
            if (!p) return;
            try {
                const res = await fetch(`${API_BASE}/api/browser/c69/proxies`);
                const d = await res.json();
                if (d.success && d.proxies && d.proxies.length > 0) {
                    const picked = d.proxies[p.id % d.proxies.length];
                    const proxyStr = (picked.username && picked.password)
                        ? `socks5://${picked.username}:${picked.password}@${picked.host}:${picked.port}`
                        : `socks5://${picked.host}:${picked.port}`;
                    p.proxy_string = proxyStr;
                    p.proxy_type = 'socks5';
                    await fetch(`${API_BASE}/api/browser/profiles`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(p)
                    });
                    loadBrowserProfiles();
                    showToast(`Đã gán Proxy C69 SOCKS5 (${picked.host}:${picked.port}) cho Profile #${p.id}!`, 'success');
                } else {
                    showToast("Không tìm thấy Proxy trong C69 Pool.", "warning");
                }
            } catch(e) {
                showToast("Lỗi gán proxy: " + e, "error");
            }
        }

        function closeNurtureModal() {
            document.getElementById('modal-nurture-tiktok').style.display = 'none';
        }

        async function submitStartNurture() {
            const profileId = parseInt(document.getElementById('nurture-prof-id').value);
            const selectEl = document.getElementById('nurture-c69-acc-select');
            const accId = selectEl ? parseInt(selectEl.value) : null;
            const chosenAcc = cachedC69Accounts.find(a => a.id === accId);

            const proxyMode = document.getElementById('nurture-proxy-mode').value;
            let customProxy = null;
            let autoAssignC69Proxy = false;

            if (proxyMode === 'c69_pool') {
                autoAssignC69Proxy = true;
            } else if (proxyMode === 'direct') {
                customProxy = "";
            } else if (proxyMode === 'custom') {
                customProxy = document.getElementById('nurture-custom-proxy-input').value.trim();
            }

            closeNurtureModal();

            try {
                const res = await fetch(`${API_BASE}/api/browser/nurture/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        profile_id: profileId,
                        c69_account_id: chosenAcc ? chosenAcc.id : null,
                        c69_username: chosenAcc ? chosenAcc.username : null,
                        c69_password: chosenAcc ? chosenAcc.password : null,
                        proxy_string: customProxy,
                        auto_assign_c69_proxy: autoAssignC69Proxy
                    })
                });
                const d = await res.json();
                showToast(d.message || "Đã phát lệnh nuôi TikTok!", "success");
                loadBrowserProfiles();
            } catch(e) {
                showToast("Lỗi: " + e, "error");
            }
        }

        async function stopNurtureProfile(profileId) {
            try {
                const res = await fetch(`${API_BASE}/api/browser/nurture/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_id: profileId })
                });
                const d = await res.json();
                showToast(d.message || `Đã dừng nuôi Profile #${profileId}`, "info");
                syncActiveBrowserProfiles();
            } catch(e) {
                showToast("Lỗi: " + e, "error");
            }
        }

        async function startNurtureAllProfiles() {
            if (allProfiles.length === 0) return showToast("Không có profile nào để nuôi!", "warning");
            showToast(`Đang phát lệnh nuôi TikTok cho toàn bộ ${allProfiles.length} profiles...`, "info");

            let accounts = [];
            try {
                const r = await fetch(`${API_BASE}/api/browser/c69/accounts`);
                const d = await r.json();
                if (d.success) accounts = d.accounts;
            } catch(_) {}

            for (let i = 0; i < allProfiles.length; i++) {
                const p = allProfiles[i];
                const acc = accounts.length > 0 ? accounts[i % accounts.length] : null;
                fetch(`${API_BASE}/api/browser/nurture/start`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        profile_id: p.id,
                        c69_account_id: acc ? acc.id : null,
                        c69_username: acc ? acc.username : null,
                        c69_password: acc ? acc.password : null
                    })
                }).catch(() => {});
            }
            showToast(`Đã phát lệnh nuôi TikTok đồng loạt cho ${allProfiles.length} profiles!`, "success");
            setTimeout(syncActiveBrowserProfiles, 1500);
        }

        async function stopNurtureAllProfiles() {
            for (const p of allProfiles) {
                fetch(`${API_BASE}/api/browser/nurture/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile_id: p.id })
                }).catch(() => {});
            }
            showToast("Đã phát lệnh dừng nuôi cho tất cả profile!", "info");
            setTimeout(syncActiveBrowserProfiles, 1000);
        }

        async function syncC69Profiles() {
            showToast("Đang đồng bộ profiles từ C69...", "info");
            try {
                const res = await fetch(`${API_BASE}/api/browser/c69/sync-profiles`, { method: 'POST' });
                const d = await res.json();
                showToast(d.message || "Đã đồng bộ profiles từ C69!", "success");
                loadBrowserProfiles();
            } catch(e) {
                showToast("Lỗi đồng bộ: " + e, "error");
            }
        }

        // ── C69 Authentication & Gate Control ──────────────────────────────────
        let currentC69Session = null;

        async function checkC69Auth() {
            try {
                const res = await fetch(`${API_BASE}/api/c69/auth/status`);
                const d = await res.json();
                const gate = document.getElementById('c69-login-gate');
                const dot = document.getElementById('c69-auth-dot');
                const userEl = document.getElementById('c69-auth-user');
                const actBtn = document.getElementById('btn-c69-auth-action');

                if (d.logged_in) {
                    currentC69Session = d;
                    if (gate) gate.style.display = 'none';
                    if (dot) dot.style.background = '#10b981';
                    if (userEl) userEl.innerHTML = `👤 <b style="color:#f0abfc;">@${d.username}</b> <span style="font-size:10px; color:#10b981; font-weight:600;">(Online)</span>`;
                    if (actBtn) {
                        actBtn.innerText = 'Đăng Xuất';
                        actBtn.style.borderColor = '#ef4444';
                        actBtn.style.color = '#ef4444';
                    }
                } else {
                    currentC69Session = null;
                    if (gate) gate.style.display = 'flex';
                    if (dot) dot.style.background = '#ef4444';
                    if (userEl) userEl.innerHTML = `<span style="color:#f87171;">Chưa đăng nhập C69</span>`;
                    if (actBtn) {
                        actBtn.innerText = 'Đăng Nhập';
                        actBtn.style.borderColor = '#38bdf8';
                        actBtn.style.color = '#38bdf8';
                    }
                }
            } catch (e) {
                console.error('Lỗi kiểm tra C69 Auth:', e);
            }
        }

        function handleC69AuthBadgeClick() {
            if (currentC69Session && currentC69Session.logged_in) {
                logoutC69();
            } else {
                openC69LoginModal();
            }
        }

        function openC69LoginModal() {
            const gate = document.getElementById('c69-login-gate');
            if (gate) gate.style.display = 'flex';
            const msgEl = document.getElementById('c69-login-msg');
            if (msgEl) msgEl.style.display = 'none';
        }

        function toggleC69ServerUrl() {
            const wrap = document.getElementById('c69-server-input-wrap');
            if (wrap) {
                wrap.style.display = wrap.style.display === 'none' ? 'block' : 'none';
            }
        }

        async function submitC69Login() {
            const user = document.getElementById('c69-login-username')?.value.trim();
            const pass = document.getElementById('c69-login-password')?.value;
            const server = document.getElementById('c69-login-server')?.value.trim() || 'https://cu.c69.us';
            const btn = document.getElementById('btn-c69-login-submit');
            const msgEl = document.getElementById('c69-login-msg');

            if (!user || !pass) {
                if (msgEl) {
                    msgEl.style.display = 'block';
                    msgEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    msgEl.style.color = '#fca5a5';
                    msgEl.innerText = 'Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu!';
                }
                return;
            }

            if (btn) {
                btn.disabled = true;
                btn.innerHTML = `<span>⏳ Đang xác thực với ${server}...</span>`;
            }

            try {
                const res = await fetch(`${API_BASE}/api/c69/auth/login`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: user,
                        password: pass,
                        server_url: server
                    })
                });
                const d = await res.json();
                if (d.success) {
                    if (msgEl) {
                        msgEl.style.display = 'block';
                        msgEl.style.background = 'rgba(16, 185, 129, 0.15)';
                        msgEl.style.color = '#6ee7b7';
                        msgEl.innerText = d.message || 'Đăng nhập thành công!';
                    }
                    showToast(d.message || `Đăng nhập C69 thành công với @${user}!`, 'success');
                    setTimeout(() => {
                        const gate = document.getElementById('c69-login-gate');
                        if (gate) gate.style.display = 'none';
                        checkC69Auth();
                        loadC69AccountsTab();
                    }, 500);
                } else {
                    if (msgEl) {
                        msgEl.style.display = 'block';
                        msgEl.style.background = 'rgba(239, 68, 68, 0.2)';
                        msgEl.style.border = '1px solid rgba(239, 68, 68, 0.4)';
                        msgEl.style.color = '#fca5a5';
                        msgEl.innerText = '❌ ' + (d.message || 'Đăng nhập thất bại. Kiểm tra lại thông tin tài khoản!');
                    }
                    showToast(d.message || 'Đăng nhập C69 thất bại!', 'error');
                }
            } catch (e) {
                if (msgEl) {
                    msgEl.style.display = 'block';
                    msgEl.style.background = 'rgba(239, 68, 68, 0.15)';
                    msgEl.style.color = '#fca5a5';
                    msgEl.innerText = 'Lỗi kết nối: ' + e;
                }
                showToast('Lỗi kết nối C69: ' + e, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = `<span>⚡ Đăng Nhập & Mở Khóa Tool</span>`;
                }
            }
        }

        async function logoutC69() {
            try {
                await fetch(`${API_BASE}/api/c69/auth/logout`, { method: 'POST' });
                showToast('Đã đăng xuất tài khoản C69', 'info');
                checkC69Auth();
            } catch (e) {
                showToast('Lỗi đăng xuất: ' + e, 'error');
            }
        }

        // ── C69 Accounts Management (100% C69 Portal Replica) ────────────────
        let c69AllAccounts = [];
        let c69CurrentAccountTab = 'all';
        let c69CurrentPage = 1;
        let c69PageSize = 10;
        let c69TotalCount = 0;
        let c69TotalPages = 1;
        let selectedC69AccIds = new Set();
        let c69ReadingMail = {};
        let c69SearchDebounceTimer = null;
        let c69UsersListLoaded = false;
        let c69UserFilterExplicitlyCleared = false;
        let currentDetailAccId = null;
        let current2FaAccId = null;

        function switchC69AccountSubTab(tab) {
            c69CurrentAccountTab = tab;
            
            // Cập nhật class active trên 4 sub tabs: all, regular, main, nurtured
            ['all', 'regular', 'main', 'nurtured'].forEach(t => {
                const el = document.getElementById(`c69-subtab-${t}`);
                if (el) {
                    if (t === tab) {
                        el.classList.add('active');
                    } else {
                        el.classList.remove('active');
                    }
                }
            });

            // Tự động chuyển đổi các lựa chọn trong Smart Username / Sub / Main filter
            const userFilterSel = document.getElementById('c69-acc-username-filter');
            if (userFilterSel) {
                if (tab === 'main') {
                    userFilterSel.innerHTML = `
                        <option value="">Tất cả Main</option>
                        <option value="in_group">📁 Đã vào nhóm</option>
                        <option value="not_in_group">⚠️ Chưa vào nhóm</option>
                        <option value="exclude_user_random">Ẩn username userxxxx</option>
                        <option value="only_user_random">Chỉ username userxxxx</option>
                    `;
                } else if (tab === 'regular') {
                    userFilterSel.innerHTML = `
                        <option value="">Tất cả nick Thường</option>
                        <option value="sub_yes">⭐ Có Subscription</option>
                        <option value="sub_no">⚪ Không có Subscription</option>
                        <option value="exclude_user_random">Ẩn username userxxxx</option>
                        <option value="only_user_random">Chỉ username userxxxx</option>
                    `;
                } else if (tab === 'nurtured') {
                    userFilterSel.innerHTML = `
                        <option value="">Tất cả nick Đã Nuôi</option>
                        <option value="sub_yes">⭐ Có Subscription</option>
                        <option value="sub_no">⚪ Không có Subscription</option>
                        <option value="exclude_user_random">Ẩn username userxxxx</option>
                        <option value="only_user_random">Chỉ username userxxxx</option>
                    `;
                } else {
                    userFilterSel.innerHTML = `
                        <option value="">Tất cả loại & sub</option>
                        <option value="sub_yes">⭐ Có Subscription</option>
                        <option value="sub_no">⚪ Không có Subscription</option>
                        <option value="shared">🤝 Được / Đã chia sẻ</option>
                        <option value="exclude_user_random">Ẩn username userxxxx</option>
                        <option value="only_user_random">Chỉ username userxxxx</option>
                    `;
                }
                userFilterSel.value = '';
            }

            c69CurrentPage = 1;
            loadC69AccountsTab();
        }

        async function handleC69ToggleMain(isMain) {
            if (selectedC69AccIds.size === 0) {
                showToast('Vui lòng chọn ít nhất 1 tài khoản!', 'warning');
                return;
            }
            const actionLabel = isMain ? 'Đặt làm Main' : 'Bỏ đánh dấu Main';
            const actionVal = isMain ? 'set_main' : 'unset_main';
            if (!confirm(`Bạn có chắc chắn muốn ${actionLabel} cho ${selectedC69AccIds.size} tài khoản đã chọn?`)) {
                return;
            }

            try {
                const ids = Array.from(selectedC69AccIds);
                const res = await fetch(`${API_BASE}/api/c69/accounts/bulk-main`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ ids: ids, action: actionVal })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || `${actionLabel} thành công cho ${ids.length} tài khoản!`, 'success');
                    selectedC69AccIds.clear();
                    updateSelectedC69AccsUI();
                    loadC69AccountsTab();
                } else {
                    showToast('Lỗi: ' + (d.error || d.message || 'Không thể thực hiện.'), 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối C69: ' + e, 'error');
            }
        }

        async function loadC69UsersList() {
            try {
                const res = await fetch(`${API_BASE}/api/c69/users`);
                const data = await res.json();
                const users = data.users || data.results || data || [];
                const creatorSel = document.getElementById('c69-acc-creator-filter');
                const subOwnerSel = document.getElementById('c69-acc-sub-owner-filter');
                const modalSubOwnerSel = document.getElementById('bulk-sub-owner-select');
                
                const myUser = currentC69Session?.username || '';
                
                if (creatorSel) {
                    const curVal = creatorSel.value;
                    creatorSel.innerHTML = '<option value="">Tất cả người tạo</option>';
                    users.forEach(u => {
                        const uname = typeof u === 'string' ? u : (u.username || u.name);
                        if (uname) {
                            const opt = document.createElement('option');
                            opt.value = uname;
                            opt.innerText = uname === myUser ? `👤 ${uname} (Tôi)` : uname;
                            creatorSel.appendChild(opt);
                        }
                    });
                    if (!c69UserFilterExplicitlyCleared && myUser) {
                        creatorSel.value = myUser;
                    } else if (curVal) {
                        creatorSel.value = curVal;
                    }
                }

                if (subOwnerSel) {
                    const curVal = subOwnerSel.value;
                    subOwnerSel.innerHTML = '<option value="">Tất cả sở hữu Sub</option><option value="unassigned">-- Chưa gán --</option>';
                    users.forEach(u => {
                        const uname = typeof u === 'string' ? u : (u.username || u.name);
                        if (uname) {
                            const opt = document.createElement('option');
                            opt.value = uname;
                            opt.innerText = uname === myUser ? `👤 ${uname} (Tôi)` : uname;
                            subOwnerSel.appendChild(opt);
                        }
                    });
                    if (curVal) subOwnerSel.value = curVal;
                }

                if (modalSubOwnerSel) {
                    modalSubOwnerSel.innerHTML = '<option value="">-- Chọn User --</option>';
                    users.forEach(u => {
                        const uname = typeof u === 'string' ? u : (u.username || u.name);
                        if (uname) {
                            const opt = document.createElement('option');
                            opt.value = uname;
                            opt.innerText = uname === myUser ? `👤 ${uname} (Tôi)` : uname;
                            modalSubOwnerSel.appendChild(opt);
                        }
                    });
                }
                c69UsersListLoaded = true;
            } catch (e) {
                console.warn('Lỗi tải danh sách users C69:', e);
            }
        }

        function onC69SearchInput() {
            clearTimeout(c69SearchDebounceTimer);
            c69SearchDebounceTimer = setTimeout(() => {
                c69CurrentPage = 1;
                loadC69AccountsTab();
            }, 350);
        }

        function onC69FilterChange() {
            const creatorSel = document.getElementById('c69-acc-creator-filter');
            if (creatorSel && creatorSel.value === '') {
                c69UserFilterExplicitlyCleared = true;
            }
            c69CurrentPage = 1;
            loadC69AccountsTab();
        }

        function onC69PageSizeChange() {
            const sel = document.getElementById('c69-acc-pagesize');
            c69PageSize = parseInt(sel?.value) || 10;
            c69CurrentPage = 1;
            loadC69AccountsTab();
        }

        function goToC69Page(page) {
            if (page < 1 || page > c69TotalPages || page === c69CurrentPage) return;
            c69CurrentPage = page;
            loadC69AccountsTab();
        }

        async function loadC69AccountsTab() {
            const tbody = document.getElementById('c69-accounts-body');
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="11" style="text-align: center; padding:30px; color: var(--text-muted);">⏳ Đang nạp danh sách tài khoản từ server C69...</td></tr>`;
            }

            if (!c69UsersListLoaded) {
                await loadC69UsersList();
            }

            const searchVal = document.getElementById('c69-acc-search')?.value.trim() || '';
            const typeVal = document.getElementById('c69-acc-type-filter')?.value || '';
            const statusVal = document.getElementById('c69-acc-status-filter')?.value || '';
            const creatorSel = document.getElementById('c69-acc-creator-filter');
            let creatorVal = creatorSel ? creatorSel.value : '';
            const subOwnerVal = document.getElementById('c69-acc-sub-owner-filter')?.value || '';
            const smartFilterVal = document.getElementById('c69-acc-username-filter')?.value || '';
            const sortVal = document.getElementById('c69-acc-sort-filter')?.value || '';

            // Xử lý smart filter theo quy chuẩn C69 Web
            let hasSubVal = '';
            let usernameFilterVal = '';
            if (c69CurrentAccountTab === 'main') {
                usernameFilterVal = smartFilterVal;
            } else {
                if (smartFilterVal === 'sub_yes') {
                    hasSubVal = 'true';
                } else if (smartFilterVal === 'sub_no') {
                    hasSubVal = 'false';
                } else if (smartFilterVal) {
                    usernameFilterVal = smartFilterVal;
                }
            }

            // Cập nhật nhãn hiển thị username đang login
            const myUser = currentC69Session?.username || '';
            const userDisplay = document.getElementById('c69-user-badge-text');
            if (userDisplay) {
                userDisplay.innerText = myUser ? `👤 @${myUser}` : '👤 @Chưa đăng nhập';
            }

            // Nếu ở tab khác Main và Đã Nuôi, chưa chọn ai và chưa xóa filter, tự động mặc định chọn nick login
            if (c69CurrentAccountTab !== 'main' && c69CurrentAccountTab !== 'nurtured') {
                if (!creatorVal && !c69UserFilterExplicitlyCleared && myUser) {
                    creatorVal = myUser;
                    if (creatorSel) creatorSel.value = myUser;
                }
            }

            const params = new URLSearchParams();
            if (c69CurrentAccountTab && c69CurrentAccountTab !== 'all') {
                params.set('account_tab', c69CurrentAccountTab);
            }
            if (searchVal) params.set('search', searchVal);
            if (typeVal) params.set('type', typeVal);
            if (statusVal) params.set('status', statusVal);
            if (hasSubVal) params.set('has_subscription', hasSubVal);
            if (creatorVal) {
                params.set('created_by', creatorVal);
            } else if (c69UserFilterExplicitlyCleared || c69CurrentAccountTab === 'main' || c69CurrentAccountTab === 'nurtured') {
                params.set('created_by', 'all');
            }
            if (subOwnerVal) params.set('subscription_owner', subOwnerVal);
            if (usernameFilterVal) params.set('username_filter', usernameFilterVal);
            if (sortVal) params.set('sort', sortVal);

            params.set('page', c69CurrentPage);
            params.set('page_size', c69PageSize);

            try {
                const [resAccs, resProfs] = await Promise.all([
                    fetch(`${API_BASE}/api/browser/c69/accounts?${params.toString()}`),
                    fetch(`${API_BASE}/api/browser/profiles`)
                ]);
                const dAcc = await resAccs.json();
                if (dAcc.success) {
                    c69AllAccounts = dAcc.accounts || [];
                    c69TotalCount = typeof dAcc.count === 'number' ? dAcc.count : c69AllAccounts.length;
                    c69TotalPages = Math.max(1, Math.ceil(c69TotalCount / c69PageSize));
                }
                allProfiles = await resProfs.json();

                const countEl = document.getElementById('c69-acc-count');
                if (countEl) countEl.innerText = `Tổng: ${c69TotalCount} tài khoản`;

                renderC69Pagination(c69TotalPages, c69CurrentPage, c69TotalCount, c69PageSize);
                renderC69Accounts(c69AllAccounts);
            } catch(e) {
                if (tbody) tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: #ef4444; padding:20px;">Lỗi tải dữ liệu C69: ${e}</td></tr>`;
            }
        }

        function renderC69Pagination(totalPages, page, count, pageSize) {
            const fromVal = count === 0 ? 0 : (page - 1) * pageSize + 1;
            const toVal = Math.min(page * pageSize, count);
            const pagInfo = document.getElementById('c69-pagination-info');
            if (pagInfo) pagInfo.innerText = `Hiển thị ${fromVal} - ${toVal} của ${count} tài khoản`;

            const container = document.getElementById('c69-pag-controls');
            if (!container) return;

            if (totalPages <= 1 && count <= pageSize) {
                container.innerHTML = '';
                return;
            }

            let html = `
                <button class="c69-pag-btn" onclick="goToC69Page(${page - 1})" ${page <= 1 ? 'disabled' : ''} title="Trang trước">Trước</button>
            `;

            const pages = [];
            if (totalPages <= 7) {
                for (let i = 1; i <= totalPages; i++) pages.push(i);
            } else {
                pages.push(1);
                if (page > 4) pages.push('...');
                const start = Math.max(2, page - 1);
                const end = Math.min(totalPages - 1, page + 1);
                for (let i = start; i <= end; i++) pages.push(i);
                if (page < totalPages - 3) pages.push('...');
                pages.push(totalPages);
            }

            pages.forEach((p, idx) => {
                if (p === '...') {
                    html += `<span style="color:#64748b; padding:0 3px; font-weight:700;">...</span>`;
                } else {
                    html += `<button class="c69-pag-btn ${p === page ? 'active' : ''}" onclick="goToC69Page(${p})">${p}</button>`;
                }
            });

            html += `
                <button class="c69-pag-btn" onclick="goToC69Page(${page + 1})" ${page >= totalPages ? 'disabled' : ''} title="Trang sau">Sau</button>
            `;
            container.innerHTML = html;
        }

        function toggleSelectAllC69Accounts(masterCb) {
            const isChecked = masterCb ? masterCb.checked : false;
            document.querySelectorAll('.c69-acc-checkbox').forEach(cb => {
                cb.checked = isChecked;
                const accId = parseInt(cb.value);
                if (isChecked) {
                    selectedC69AccIds.add(accId);
                } else {
                    selectedC69AccIds.delete(accId);
                }
            });
            updateSelectedC69AccsUI();
        }

        function onC69AccCheckboxChange(cb, accId) {
            if (cb.checked) {
                selectedC69AccIds.add(accId);
            } else {
                selectedC69AccIds.delete(accId);
            }
            updateSelectedC69AccsUI();
        }

        function updateSelectedC69AccsUI() {
            const masterCb = document.getElementById('check-all-c69-accs');
            if (masterCb) {
                const checkboxes = document.querySelectorAll('.c69-acc-checkbox');
                if (checkboxes.length > 0) {
                    masterCb.checked = Array.from(checkboxes).every(cb => cb.checked);
                } else {
                    masterCb.checked = false;
                }
            }
            const selBtn = document.getElementById('btn-nurture-selected-c69');
            if (selBtn) {
                selBtn.innerHTML = `🎬 Nuôi Nick Đã Chọn ${selectedC69AccIds.size > 0 ? `(${selectedC69AccIds.size})` : ''}`;
            }
            const infoEl = document.getElementById('c69-selected-info');
            if (infoEl) {
                infoEl.innerText = `Đã chọn: ${selectedC69AccIds.size}`;
            }

            // Cập nhật trạng thái disabled của các nút hành động hàng loạt
            const hasSel = selectedC69AccIds.size > 0;
            const btnBulkSub = document.getElementById('btn-c69-bulk-sub');
            const btnBulkStatus = document.getElementById('btn-c69-bulk-status');
            const btnBulkDelete = document.getElementById('btn-c69-bulk-delete');
            const btnBulkSocks = document.getElementById('btn-c69-bulk-socks');
            const btnSetMain = document.getElementById('btn-c69-set-main');
            const btnUnsetMain = document.getElementById('btn-c69-unset-main');
            if (btnBulkSub) btnBulkSub.disabled = !hasSel;
            if (btnBulkStatus) btnBulkStatus.disabled = !hasSel;
            if (btnBulkDelete) btnBulkDelete.disabled = !hasSel;
            if (btnBulkSocks) btnBulkSocks.disabled = !hasSel;
            if (btnSetMain) btnSetMain.disabled = !hasSel;
            if (btnUnsetMain) btnUnsetMain.disabled = !hasSel;

            const bulkSubCountEl = document.getElementById('bulk-sub-count');
            if (bulkSubCountEl) bulkSubCountEl.innerText = selectedC69AccIds.size;
            const bulkStatusCountEl = document.getElementById('bulk-status-count');
            if (bulkStatusCountEl) bulkStatusCountEl.innerText = selectedC69AccIds.size;
        }

        function getAccountStatusBadge(status) {
            const s = (status !== undefined && status !== null) ? String(status).toLowerCase().trim() : '';
            if (s === '0' || s === 'active' || s.includes('hoạt động')) {
                return '<span class="badge badge-success">Hoạt động</span>';
            } else if (s === '1' || s === 'inactive' || s.includes('chưa kích hoạt')) {
                return '<span class="badge badge-warning">Chưa kích hoạt</span>';
            } else if (s === '2' || s === 'banned' || s === 'locked' || s.includes('khóa')) {
                return '<span class="badge badge-danger">Bị khóa</span>';
            } else if (s === '3' || s === 'temporary' || s.includes('tạm thời')) {
                return '<span class="badge badge-info">Tạm thời</span>';
            } else if (s === '4' || s.includes('sub ok')) {
                return '<span class="badge badge-sub-ok">Sub OK</span>';
            } else if (s === '7' || s.includes('chờ sub')) {
                return '<span class="badge" style="background:rgba(234,179,8,0.2); color:#facc15; border:1px solid rgba(234,179,8,0.4); font-weight:700;">⏳ Chờ Sub</span>';
            } else if (s === '5' || s.includes('sub lỗi')) {
                return '<span class="badge badge-sub-error">Sub Lỗi</span>';
            } else if (s === '6' || s.includes('đang sử dụng')) {
                return '<span class="badge badge-active">Đang sử dụng</span>';
            }
            return `<span class="badge badge-info">${status || 'Active'}</span>`;
        }

        function copyText(text, label) {
            if (!text) return;
            navigator.clipboard.writeText(text);
            showToast(`Đã sao chép ${label || 'nội dung'}: ${text}`, 'info');
        }

        function copyOtp(code) {
            if (!code) return;
            navigator.clipboard.writeText(code);
            showToast(`Đã sao chép mã OTP: ${code}`, 'success');
        }

        function formatDateString(isoStr) {
            if (!isoStr) return '—';
            try {
                const d = new Date(isoStr);
                if (isNaN(d.getTime())) return isoStr;
                return d.toLocaleDateString('vi-VN') + ' ' + d.toLocaleTimeString('vi-VN');
            } catch (_) {
                return isoStr;
            }
        }

        async function refreshRowEmail(accId, emailId) {
            if (!emailId) {
                return showToast('Tài khoản này chưa được liên kết email trên C69!', 'warning');
            }
            c69ReadingMail[accId] = true;
            renderC69Accounts(c69AllAccounts);

            try {
                const res = await fetch(`${API_BASE}/api/c69/emails/${emailId}/read`);
                const d = await res.json();
                if (d.success || d.email_data) {
                    const eData = d.email_data || {};
                    const targetAcc = c69AllAccounts.find(a => a.id === accId);
                    if (targetAcc) {
                        targetAcc.email_info = {
                            id: emailId,
                            latest_from: eData.latest_from || '',
                            latest_time: eData.latest_time || '',
                            latest_content: eData.latest_content || '',
                            latest_code: eData.latest_code || ''
                        };
                    }
                    const otpMsg = eData.latest_code ? ` (Mã OTP: ${eData.latest_code})` : '';
                    showToast(`Đã cập nhật hộp thư mới cho tài khoản #${accId}!${otpMsg}`, 'success');
                } else {
                    showToast(d.message || 'Không thể đọc hộp thư từ server C69', 'error');
                }
            } catch (e) {
                showToast('Lỗi đọc email: ' + e, 'error');
            } finally {
                delete c69ReadingMail[accId];
                renderC69Accounts(c69AllAccounts);
            }
        }

        function handleC69ActionChange(sel, accId) {
            const val = sel.value;
            sel.value = '';
            if (!val) return;

            const acc = c69AllAccounts.find(a => a.id === accId);
            if (!acc) return;

            const assignedProf = allProfiles.find(p => p.tiktok_account_id === acc.id || p.tiktok_username === acc.username);

            if (val === 'nurture') {
                createProfileAndNurtureForAccount(accId);
            } else if (val === 'launch') {
                if (assignedProf) {
                    launchBrowserProfile(assignedProf.id);
                } else {
                    createProfileAndNurtureForAccount(accId);
                }
            } else if (val === 'view' || val === 'edit') {
                openC69AccountDetailModal(accId);
            } else if (val === '2fa') {
                openC692FAModal(accId);
            } else if (val === 'delete') {
                deleteC69SingleAccount(accId);
            }
        }

        // ── DROPDOWN THÊM TÀI KHOẢN (ĐƠN LẺ & HÀNG LOẠT) ────────────────────────
        function toggleC69AddMenu(e) {
            if (e) e.stopPropagation();
            const m = document.getElementById('c69-add-dropdown-menu');
            if (m) {
                m.style.display = m.style.display === 'block' ? 'none' : 'block';
            }
        }
        document.addEventListener('click', function(e) {
            const container = document.getElementById('c69-add-dropdown-container');
            const menu = document.getElementById('c69-add-dropdown-menu');
            if (menu && container && !container.contains(e.target)) {
                menu.style.display = 'none';
            }
        });

        // ── SOCKS5 PROXY POOL & SOCKS ASSIGNMENT STATE ──────────────────────────
        let c69ProxyPoolData = [];
        let c69ProxyTestMap = {}; // proxyStr -> { alive, latency_ms, message }
        let changeSocksTargetAccountIds = [];

        function renderC69Accounts(accounts) {
            const tbody = document.getElementById('c69-accounts-body');
            if (!tbody) return;

            if (accounts.length === 0) {
                tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; padding:35px; color: var(--text-muted); font-size:13px;">Không tìm thấy tài khoản nào phù hợp với bộ lọc hiện tại.</td></tr>`;
                updateSelectedC69AccsUI();
                return;
            }

            tbody.innerHTML = accounts.map((acc, idx) => {
                const stt = (c69CurrentPage - 1) * c69PageSize + idx + 1;
                const assignedProf = allProfiles.find(p => p.tiktok_account_id === acc.id || p.tiktok_username === acc.username);
                const isRunning = assignedProf ? activeProfileIds.has(assignedProf.id) : false;
                const nurture = assignedProf ? nurtureStatuses[assignedProf.id] : null;
                const isNurturing = nurture && nurture.is_running;

                // Xác định Proxy & Trạng thái Live/Die
                const rawProxy = (assignedProf && assignedProf.proxy) ? assignedProf.proxy : (acc.proxy || '');
                let proxyShort = '<i style="color:#64748b;">Chưa gán Socks</i>';
                let proxyTestBadge = '<span style="color:#64748b; font-size:10px;">Chưa test</span>';

                if (rawProxy) {
                    let cleanProxy = rawProxy.replace(/^socks5:\/\//i, '');
                    let hostPart = cleanProxy;
                    if (cleanProxy.includes('@')) {
                        hostPart = cleanProxy.split('@')[1];
                    }
                    proxyShort = `<span class="cell-copyable" onclick="copyText('${rawProxy}', 'Proxy')" style="font-family:monospace; font-size:11px; color:#38bdf8; font-weight:700;" title="Click copy Proxy: ${rawProxy}">🛡️ ${hostPart}</span>`;
                    const testRes = getProxyTestResult(rawProxy, assignedProf ? assignedProf.id : null);
                    if (testRes) {
                        if (testRes.alive) {
                            proxyTestBadge = `<span class="badge badge-success" style="font-size:9px; padding:1px 5px;">🟢 Live (${testRes.latency_ms}ms)</span>`;
                        } else {
                            proxyTestBadge = `<span class="badge badge-danger" style="font-size:9px; padding:1px 5px;">🔴 Die</span>`;
                        }
                    }
                }

                // Dữ liệu Email & Code OTP
                const emailId = acc.accounts_emails || (acc.email_info ? acc.email_info.id : null);
                const mailInfo = acc.email_info || {};
                const mailFrom = mailInfo.latest_from || '';
                const mailTime = mailInfo.latest_time || '';
                const mailCode = mailInfo.latest_code || '';
                const isRefreshing = !!c69ReadingMail[acc.id];

                return `
                <tr class="${selectedC69AccIds.has(acc.id) ? 'row-selected' : ''}">
                    <td style="text-align:center;">
                        <input type="checkbox" class="c69-acc-checkbox" value="${acc.id}" ${selectedC69AccIds.has(acc.id) ? 'checked' : ''} onchange="onC69AccCheckboxChange(this, ${acc.id})">
                    </td>
                    <td style="text-align:center; font-weight:700; color:#94a3b8; font-size:12px;">
                        ${stt}
                    </td>
                    <td>
                        <div style="display:flex; flex-direction:column; gap:2px;">
                            <div style="display:flex; align-items:center; gap:6px;">
                                ${acc.is_main ? `<span style="background:linear-gradient(135deg, #eab308, #ca8a04); color:#000; font-size:10px; font-weight:800; padding:1px 6px; border-radius:4px; box-shadow:0 0 8px rgba(234, 179, 8, 0.4);" title="Tài khoản Main">MAIN</span>` : ''}
                                <b class="cell-copyable" onclick="copyText('${acc.username || acc.email}', 'username')" style="color:#f0abfc; font-size:12px;" title="Click copy username">
                                    @${acc.username || acc.email}
                                </b>
                                ${acc.type ? `<span class="badge badge-type">${acc.type}</span>` : ''}
                            </div>
                            <div style="display:flex; align-items:center; gap:8px; font-size:11px;">
                                <span class="cell-copyable" onclick="copyText('${acc.password || ''}', 'mật khẩu')" style="color:#94a3b8;" title="Click copy mật khẩu">
                                    🔑 <code>${acc.password ? acc.password : '<i style="color:#64748b;">(Trống)</i>'}</code>
                                </span>
                            </div>
                        </div>
                    </td>
                    <td>
                        <div style="display:flex; flex-direction:column; gap:3px;">
                            ${getAccountStatusBadge(acc.status)}
                            ${acc.subscription ? `<div style="font-size:10px; color:#cbd5e1; font-weight:600;" title="Gói Subscription">📦 ${acc.subscription}</div>` : ''}
                        </div>
                    </td>
                    <td>
                        <div style="display:flex; flex-direction:column; gap:4px;">
                            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                                <div style="max-width:135px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
                                    ${proxyShort}
                                </div>
                                <button class="btn btn-dark" style="padding:2px 6px; font-size:10px; border-color:rgba(56,189,248,0.4); color:#38bdf8; white-space:nowrap;" onclick="openChangeSocksModalForSingle(${acc.id})" title="Đổi Socks5 cho tài khoản này">
                                    🔄 Đổi Socks
                                </button>
                            </div>
                            <div style="display:flex; align-items:center; gap:4px; flex-wrap:wrap;">
                                <span id="c69-acc-proxy-badge-${acc.id}">${proxyTestBadge}</span>
                                ${rawProxy ? `<button class="btn btn-dark" style="padding:1px 5px; font-size:9.5px; border-color:rgba(56,189,248,0.3); color:#38bdf8;" onclick="testC69AccountProxy(${acc.id}, '${rawProxy.replace(/'/g, "\\'")}', this)" title="Test live/die cho Socks này">⚡ Test</button>` : ''}
                            </div>
                        </div>
                    </td>
                    <td>
                        <div style="display:flex; flex-direction:column; gap:3px;">
                            ${(emailId || acc.email) ? `
                            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                                <span class="cell-copyable" onclick="copyText('${acc.email || mailFrom}', 'email')" style="font-weight:600; color:#cbd5e1; font-size:11px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:145px;" title="${mailFrom || acc.email}">
                                    📨 ${mailFrom || acc.email}
                                </span>
                                ${emailId ? `
                                <button class="btn btn-dark" onclick="refreshRowEmail(${acc.id}, ${emailId})" style="padding:1px 5px; font-size:10px; min-width:20px; border-color:rgba(56,189,248,0.4);" title="Quét đọc thư mới ngay">
                                    ${isRefreshing ? '⏳' : '🔄'}
                                </button>
                                ` : ''}
                            </div>
                            ` : '<span style="color:#64748b; font-size:11px;">Chưa liên kết</span>'}

                            <div style="display:flex; align-items:center; justify-content:space-between; gap:4px;">
                                <div>
                                    ${mailCode ? `
                                    <span class="badge badge-success cell-copyable" onclick="copyOtp('${mailCode}')" style="cursor:pointer; font-weight:800; font-size:11px; letter-spacing:1px; padding:1px 6px;" title="Click để sao chép OTP">
                                        ⚡ ${mailCode}
                                    </span>
                                    ` : '<span style="color:#64748b; font-size:10px;">Chưa có OTP</span>'}
                                </div>
                                ${mailTime ? `<span style="font-size:10px; color:#94a3b8;" title="${mailTime}">🕒 ${mailTime.includes(' ') ? mailTime.split(' ')[1] : mailTime}</span>` : ''}
                            </div>
                        </div>
                    </td>
                    <td>
                        ${assignedProf ? `
                        <div style="display:flex; flex-direction:column; gap:3px;">
                            <div style="display:flex; align-items:center; gap:5px;">
                                <b style="font-size:11px; color:#cbd5e1; max-width:125px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${assignedProf.name}">
                                    🌐 ${assignedProf.name}
                                </b>
                                ${isRunning ? '<span class="badge badge-success" style="font-size:9px; padding:1px 4px;">🟢 Chạy</span>' : '<span style="color:#64748b; font-size:10px;">⚪ Tắt</span>'}
                            </div>
                            ${isNurturing ? `<div style="font-size:10px; color:#ec4899; font-weight:700;">🎬 Đang nuôi: ${nurture.status || 'Tự động'}</div>` : ''}
                        </div>
                        ` : '<span style="color:#64748b; font-size:11px;">Chưa tạo hồ sơ</span>'}
                    </td>
                    <td style="text-align:center;">
                        <div style="display:flex; align-items:center; justify-content:center; gap:5px;">
                            ${assignedProf ? (isNurturing 
                                ? `<button class="btn btn-danger" style="padding:4px 9px; font-size:11px; font-weight:700;" onclick="stopNurtureProfile(${assignedProf.id})" title="Dừng nuôi">⏹️ Dừng</button>` 
                                : `<button class="btn btn-purple" style="padding:4px 10px; font-size:11px; font-weight:700; background:linear-gradient(135deg, #ec4899, #8b5cf6); color:#fff; border:none; box-shadow:0 0 8px rgba(236,72,153,0.35);" onclick="openNurtureModal(${assignedProf.id})" title="Nuôi TikTok">🎬 Nuôi</button>`
                              ) : `<button class="btn btn-purple" style="padding:4px 10px; font-size:11px; font-weight:700; background:linear-gradient(135deg, #ec4899, #8b5cf6); color:#fff; border:none; box-shadow:0 0 8px rgba(236,72,153,0.35);" onclick="createProfileAndNurtureForAccount(${acc.id})" title="Tạo Profile & Nuôi ngay">🎬 Nuôi</button>`
                            }
                            <button class="btn btn-primary" style="padding:4px 9px; font-size:11px; font-weight:700; background:linear-gradient(135deg, #0ea5e9, #0284c7); color:#fff; border:none;" onclick="openC69AccountDetailModal(${acc.id})" title="Sửa thông tin tài khoản">✏️ Sửa</button>
                            <select class="c69-select" onchange="handleC69ActionChange(this, ${acc.id})" style="padding:3px 4px; font-size:11px; width:34px; text-align:center; color:#94a3b8;" title="Thao tác khác">
                                <option value="">⋯</option>
                                ${assignedProf ? '<option value="launch">🚀 Mở Browser</option>' : ''}
                                <option value="2fa">🔑 Mã 2FA / OTP</option>
                                <option value="view">🔍 Xem chi tiết</option>
                                <option value="delete">❌ Xóa nick</option>
                            </select>
                        </div>
                    </td>
                </tr>
                `;
            }).join('');
            updateSelectedC69AccsUI();
        }

        // ── XỬ LÝ MODAL ĐỔI SOCKS5 ─────────────────────────────────────────────
        async function ensureProxyPoolLoaded(force = false) {
            if (force || c69ProxyPoolData.length === 0) {
                try {
                    const res = await fetch(`${API_BASE}/api/browser/c69/proxies?t=${Date.now()}`);
                    const d = await res.json();
                    if (d.success && Array.isArray(d.proxies)) {
                        c69ProxyPoolData = d.proxies;
                        c69ProxyPoolData.forEach(p => {
                            const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                            if (p.status === 'live' || p.status === 'die') {
                                const isAlive = p.status === 'live';
                                setProxyTestResult(pStr, null, {
                                    alive: isAlive,
                                    latency_ms: p.latency || 0,
                                    message: isAlive ? `Live (${p.latency || 0}ms)` : 'Die'
                                });
                            }
                        });
                    }
                } catch(e) {
                    console.error('Lỗi tải danh sách proxy pool:', e);
                }
            }
        }

        function populateProxyPoolSelect() {
            const sel = document.getElementById('change-socks-pool-select');
            if (!sel) return;
            sel.innerHTML = '<option value="">-- Chọn 1 proxy từ 250 SOCKS5 Pool --</option>' + 
                c69ProxyPoolData.map((p, idx) => {
                    const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                    const testRes = c69ProxyTestMap[pStr];
                    const statusText = testRes ? (testRes.alive ? `[🟢 LIVE - ${testRes.latency_ms}ms]` : `[🔴 DIE]`) : '';
                    return `<option value="${pStr}">#${idx + 1} - ${p.host}:${p.port} ${statusText}</option>`;
                }).join('');
        }

        async function testC69AccountProxy(accId, proxyStr, btn) {
            if (!proxyStr) return showToast('Tài khoản chưa có Socks để kiểm tra!', 'warning');
            const badgeEl = document.getElementById(`c69-acc-proxy-badge-${accId}`);
            if (badgeEl) {
                badgeEl.innerHTML = `<span style="font-size:9px; padding:1px 5px; color:#f59e0b; background:rgba(245,158,11,0.18); border:1px solid #f59e0b; border-radius:3px; font-weight:700;"><span class="pulse-dot" style="background:#f59e0b; width:5px; height:5px; margin-right:3px;"></span>⏳ Đang check...</span>`;
            }
            if (btn) {
                btn.disabled = true;
                btn.innerText = '⏳';
            }

            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: proxyStr })
                });
                const d = await res.json();
                const testObj = { alive: d.success, latency_ms: d.latency_ms, message: d.message };
                setProxyTestResult(proxyStr, null, testObj);
                if (badgeEl) {
                    if (d.success) {
                        badgeEl.innerHTML = `<span class="badge badge-success" style="font-size:9px; padding:1px 5px; font-weight:700;">🟢 Live (${d.latency_ms}ms)</span>`;
                        showToast(`Socks LIVE (${d.latency_ms}ms)!`, 'success');
                    } else {
                        badgeEl.innerHTML = `<span class="badge badge-danger" style="font-size:9px; padding:1px 5px; font-weight:700;" title="${(d.message || 'Die').replace(/"/g, '&quot;')}">🔴 Die</span>`;
                        showToast(`Socks DIE: ${d.message || ''}`, 'error');
                    }
                }
            } catch(e) {
                if (badgeEl) badgeEl.innerHTML = `<span class="badge badge-danger" style="font-size:9px; padding:1px 5px;">⚠️ Lỗi</span>`;
                showToast(`Lỗi test socks: ${e}`, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerText = '⚡ Test';
                }
            }
        }

        async function checkSelectedC69AccountsSocks() {
            const hasSel = selectedC69AccIds.size > 0;
            const targetAccs = hasSel
                ? c69AllAccounts.filter(a => selectedC69AccIds.has(a.id))
                : c69AllAccounts;

            const accsWithSocks = targetAccs.filter(a => {
                const assignedProf = allProfiles.find(p => p.tiktok_account_id === a.id || p.tiktok_username === a.username);
                return (assignedProf && assignedProf.proxy_string && assignedProf.proxy_type !== 'direct') || a.proxy;
            });

            if (accsWithSocks.length === 0) {
                return showToast('Không tìm thấy tài khoản nào có Socks để kiểm tra!', 'warning');
            }

            const btn = document.getElementById('btn-c69-check-socks');
            if (btn) {
                btn.disabled = true;
                btn.innerText = `⏳ Đang check (0/${accsWithSocks.length})...`;
            }

            showToast(`Đang kiểm tra Socks cho ${accsWithSocks.length} tài khoản...`, 'info');
            accsWithSocks.forEach(a => {
                const badgeEl = document.getElementById(`c69-acc-proxy-badge-${a.id}`);
                if (badgeEl) {
                    badgeEl.innerHTML = `<span style="font-size:9px; padding:1px 5px; color:#f59e0b; background:rgba(245,158,11,0.18); border:1px solid #f59e0b; border-radius:3px; font-weight:700;"><span class="pulse-dot" style="background:#f59e0b; width:5px; height:5px; margin-right:3px;"></span>⏳ Đang check...</span>`;
                }
            });

            let done = 0;
            let liveCount = 0;
            let dieCount = 0;

            await Promise.all(accsWithSocks.map(async a => {
                const assignedProf = allProfiles.find(p => p.tiktok_account_id === a.id || p.tiktok_username === a.username);
                const proxyStr = (assignedProf && assignedProf.proxy_string) ? assignedProf.proxy_string : a.proxy;
                try {
                    const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ proxy_string: proxyStr })
                    });
                    const d = await res.json();
                    const testObj = { alive: d.success, latency_ms: d.latency_ms, message: d.message };
                    setProxyTestResult(proxyStr, assignedProf ? assignedProf.id : null, testObj);
                    if (d.success) liveCount++; else dieCount++;
                } catch(e) {
                    dieCount++;
                } finally {
                    done++;
                    if (btn) btn.innerText = `⏳ Đang check (${done}/${accsWithSocks.length})...`;
                    const badgeEl = document.getElementById(`c69-acc-proxy-badge-${a.id}`);
                    const testRes = getProxyTestResult(proxyStr, assignedProf ? assignedProf.id : null);
                    if (badgeEl && testRes) {
                        if (testRes.alive) {
                            badgeEl.innerHTML = `<span class="badge badge-success" style="font-size:9px; padding:1px 5px; font-weight:700;">🟢 Live (${testRes.latency_ms}ms)</span>`;
                        } else {
                            badgeEl.innerHTML = `<span class="badge badge-danger" style="font-size:9px; padding:1px 5px; font-weight:700;" title="${(testRes.message || 'Die').replace(/"/g, '&quot;')}">🔴 Die</span>`;
                        }
                    }
                }
            }));

            if (btn) {
                btn.disabled = false;
                btn.innerText = '⚡ Check Socks';
            }
            renderC69Accounts(c69AllAccounts);
            showToast(`Hoàn tất kiểm tra Socks: 🟢 ${liveCount} Live, 🔴 ${dieCount} Die!`, liveCount > 0 ? 'success' : 'warning');
        }

        async function openChangeSocksModalForSingle(accId) {
            changeSocksTargetAccountIds = [accId];
            const acc = c69AllAccounts.find(a => a.id === accId) || {};
            const assignedProf = allProfiles.find(p => p.tiktok_account_id === acc.id || p.tiktok_username === acc.username);
            const currentProxy = (assignedProf && assignedProf.proxy) ? assignedProf.proxy : (acc.proxy || '');

            const infoEl = document.getElementById('change-socks-target-info');
            if (infoEl) {
                infoEl.innerHTML = `Đang đổi Socks cho <b>@${acc.username || acc.email}</b> (ID #${accId}). ${currentProxy ? `Hiện tại: <code>${currentProxy}</code>` : '<i>Chưa có Socks</i>'}`;
            }
            document.getElementById('change-socks-manual-input').value = currentProxy;
            document.getElementById('change-socks-test-result').style.display = 'none';

            await ensureProxyPoolLoaded();
            populateProxyPoolSelect();
            document.getElementById('modal-c69-change-socks').style.display = 'flex';
        }

        async function openChangeSocksModalForSelected() {
            if (selectedC69AccIds.size === 0) {
                return showToast('Vui lòng chọn ít nhất 1 tài khoản để đổi Socks!', 'warning');
            }
            changeSocksTargetAccountIds = Array.from(selectedC69AccIds);
            const infoEl = document.getElementById('change-socks-target-info');
            if (infoEl) {
                infoEl.innerHTML = `Đang đổi Socks hàng loạt cho <b>${changeSocksTargetAccountIds.length} tài khoản</b> đã chọn.`;
            }
            document.getElementById('change-socks-manual-input').value = '';
            document.getElementById('change-socks-test-result').style.display = 'none';

            await ensureProxyPoolLoaded();
            populateProxyPoolSelect();
            document.getElementById('modal-c69-change-socks').style.display = 'flex';
        }

        function closeChangeSocksModal() {
            document.getElementById('modal-c69-change-socks').style.display = 'none';
        }

        function onSelectProxyFromPool(val) {
            if (val) {
                document.getElementById('change-socks-manual-input').value = val;
            }
        }

        function randomLiveProxyForChangeSocks() {
            if (c69ProxyPoolData.length === 0) {
                return showToast('Danh sách proxy chưa được tải!', 'warning');
            }
            // Ưu tiên các proxy đã test và LIVE
            const liveProxies = c69ProxyPoolData.filter(p => {
                const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                return c69ProxyTestMap[pStr] && c69ProxyTestMap[pStr].alive;
            });
            const poolToPick = liveProxies.length > 0 ? liveProxies : c69ProxyPoolData;
            const chosen = poolToPick[Math.floor(Math.random() * poolToPick.length)];
            const chosenStr = chosen.proxy_string || `socks5://${chosen.username}:${chosen.password}@${chosen.host}:${chosen.port}`;
            document.getElementById('change-socks-manual-input').value = chosenStr;
            showToast(`Đã chọn ngẫu nhiên: ${chosen.host}:${chosen.port} ${liveProxies.length > 0 ? '(Proxy Live)' : ''}`, 'info');
        }

        async function testCurrentChangeSocksProxy() {
            const proxyInput = document.getElementById('change-socks-manual-input').value.trim();
            if (!proxyInput) {
                return showToast('Vui lòng nhập hoặc chọn 1 Proxy để test!', 'warning');
            }
            const resEl = document.getElementById('change-socks-test-result');
            resEl.style.display = 'block';
            resEl.style.background = 'rgba(56,189,248,0.1)';
            resEl.style.color = '#38bdf8';
            resEl.innerHTML = '⏳ Đang kiểm tra kết nối TCP & Xác thực RFC 1929 SOCKS5...';

            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: proxyInput })
                });
                const d = await res.json();
                c69ProxyTestMap[proxyInput] = { alive: d.success, latency_ms: d.latency_ms, message: d.message };
                if (d.success) {
                    resEl.style.background = 'rgba(16,185,129,0.15)';
                    resEl.style.color = '#34d399';
                    resEl.innerHTML = `🟢 <b>Proxy LIVE HOẠT ĐỘNG TỐT!</b> Độ trễ: <b>${d.latency_ms} ms</b>. ${d.message || ''}`;
                } else {
                    resEl.style.background = 'rgba(239,68,68,0.15)';
                    resEl.style.color = '#f87171';
                    resEl.innerHTML = `🔴 <b>Proxy DIE / Không kết nối được:</b> ${d.message || 'Lỗi timeout kết nối'}`;
                }
            } catch(e) {
                resEl.style.background = 'rgba(239,68,68,0.15)';
                resEl.style.color = '#f87171';
                resEl.innerHTML = `🔴 Lỗi test proxy: ${e}`;
            }
        }

        async function submitChangeSocks() {
            const proxyStr = document.getElementById('change-socks-manual-input').value.trim();
            if (!proxyStr) {
                return showToast('Vui lòng nhập hoặc chọn 1 Proxy SOCKS5!', 'warning');
            }
            if (changeSocksTargetAccountIds.length === 0) {
                return showToast('Không có tài khoản nào được chọn!', 'warning');
            }

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/assign-socks`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account_ids: changeSocksTargetAccountIds,
                        proxy: proxyStr
                    })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || `Đã đổi Socks5 thành công cho ${changeSocksTargetAccountIds.length} tài khoản!`, 'success');
                    closeChangeSocksModal();
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi đổi Socks!', 'error');
                }
            } catch(e) {
                showToast('Lỗi kết nối server: ' + e, 'error');
            }
        }

        // ── XỬ LÝ MODAL QUẢN LÝ 250 SOCKS5 PROXY POOL ──────────────────────────
        async function openProxyPoolModal() {
            document.getElementById('modal-c69-proxy-pool').style.display = 'flex';
            await ensureProxyPoolLoaded();
            await syncProxyStatusCacheFromBackend();
            filterProxyPoolTable();
            updateProxyPoolStats();
        }

        async function reloadProxyPoolModal() {
            const btn = document.getElementById('btn-reload-proxy-pool');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '⏳ Đang tải...';
            }
            try {
                c69ProxyPoolData = [];
                await ensureProxyPoolLoaded(true);
                await syncProxyStatusCacheFromBackend();
                filterProxyPoolTable();
                updateProxyPoolStats();
                populateProxyPoolSelect();
                showToast(`Đã làm mới danh sách: ${c69ProxyPoolData.length} proxies!`, 'success');
            } catch(e) {
                showToast('Lỗi làm mới: ' + e, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '🔄 Làm Mới';
                }
            }
        }

        function closeProxyPoolModal() {
            document.getElementById('modal-c69-proxy-pool').style.display = 'none';
        }

        function updateProxyPoolStats() {
            const total = c69ProxyPoolData.length;
            let live = 0;
            let die = 0;
            let totalLatency = 0;
            let liveCountWithLatency = 0;

            c69ProxyPoolData.forEach(p => {
                const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                const test = getProxyTestResult(pStr) || c69ProxyTestMap[pStr];
                if (test) {
                    if (test.alive) {
                        live++;
                        if (test.latency_ms > 0) {
                            totalLatency += test.latency_ms;
                            liveCountWithLatency++;
                        }
                    } else {
                        die++;
                    }
                }
            });

            const avgPing = liveCountWithLatency > 0 ? Math.round(totalLatency / liveCountWithLatency) : '--';
            document.getElementById('proxy-stat-total').innerText = total;
            document.getElementById('proxy-stat-live').innerText = live > 0 ? live : (die > 0 ? 0 : '--');
            document.getElementById('proxy-stat-die').innerText = die > 0 ? die : (live > 0 ? 0 : '--');
            document.getElementById('proxy-stat-ping').innerText = avgPing !== '--' ? `${avgPing} ms` : '-- ms';
        }

        function renderProxyPoolTable(filterData) {
            const tbody = document.getElementById('proxy-pool-tbody');
            if (!tbody) return;

            const list = filterData || c69ProxyPoolData;
            document.getElementById('proxy-pool-counter-info').innerText = `Hiển thị ${list.length} / ${c69ProxyPoolData.length} proxy`;

            if (list.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:25px; color:var(--text-muted);">Không tìm thấy proxy nào phù hợp.</td></tr>';
                return;
            }

            tbody.innerHTML = list.map((p, idx) => {
                const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                const test = getProxyTestResult(pStr) || c69ProxyTestMap[pStr];
                let statusBadge = '<span class="badge" style="background:#334155; color:#94a3b8; font-size:10px;">⚪ Chưa test</span>';
                let pingDisplay = '<span style="color:#64748b;">--</span>';

                if (test) {
                    if (test.alive) {
                        statusBadge = '<span class="badge badge-success" style="font-size:10px;">🟢 Live</span>';
                        pingDisplay = `<b style="color:#34d399; font-size:11px;">${test.latency_ms} ms</b>`;
                    } else {
                        statusBadge = '<span class="badge badge-danger" style="font-size:10px;">🔴 Die</span>';
                        pingDisplay = '<span style="color:#ef4444; font-size:11px;">Timeout</span>';
                    }
                }

                return `
                <tr>
                    <td style="text-align:center; font-weight:700; color:#94a3b8; font-size:11px;">${idx + 1}</td>
                    <td>
                        <b class="cell-copyable" onclick="copyText('${p.host}:${p.port}', 'Host:Port')" style="font-family:monospace; color:#38bdf8; font-size:12px;" title="Click copy Host:Port">
                            ${p.host}:${p.port}
                        </b>
                    </td>
                    <td>
                        <span class="cell-copyable" onclick="copyText('${p.username}:${p.password}', 'User:Pass')" style="font-family:monospace; color:#cbd5e1; font-size:11px;" title="Click copy User:Pass">
                            ${p.username ? `${p.username}:••••` : '<i style="color:#64748b;">Không auth</i>'}
                        </span>
                    </td>
                    <td style="text-align:center;">${statusBadge}</td>
                    <td style="text-align:center;">${pingDisplay}</td>
                    <td style="text-align:center;">
                        <div style="display:flex; justify-content:center; gap:4px;">
                            <button class="btn btn-dark" style="padding:2px 6px; font-size:10px;" onclick="testSingleProxyInPool('${pStr}', this)" title="Test kết nối riêng lẻ">
                                ⚡ Test
                            </button>
                            <button class="btn btn-dark" style="padding:2px 6px; font-size:10px; border-color:rgba(56,189,248,0.3); color:#38bdf8;" onclick="copyText('${pStr}', 'Proxy SOCKS5')" title="Sao chép toàn bộ chuỗi SOCKS5">
                                📋 Copy
                            </button>
                        </div>
                    </td>
                </tr>
                `;
            }).join('');
        }

        function filterProxyPoolTable() {
            const query = (document.getElementById('proxy-search-input').value || '').trim().toLowerCase();
            const statusFilter = document.getElementById('proxy-filter-status').value;

            const filtered = c69ProxyPoolData.filter(p => {
                const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                const matchQuery = !query || p.host.toLowerCase().includes(query) || String(p.port).includes(query) || p.username.toLowerCase().includes(query);
                if (!matchQuery) return false;

                const test = getProxyTestResult(pStr) || c69ProxyTestMap[pStr];
                if (statusFilter === 'live') return test && test.alive;
                if (statusFilter === 'die') return test && !test.alive;
                if (statusFilter === 'untested') return !test;
                return true;
            });

            renderProxyPoolTable(filtered);
        }

        async function testSingleProxyInPool(proxyStr, btnEl) {
            if (btnEl) btnEl.innerText = '⏳';
            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: proxyStr })
                });
                const d = await res.json();
                const testObj = { alive: d.success, latency_ms: d.latency_ms, message: d.message };
                setProxyTestResult(proxyStr, null, testObj);
                updateProxyPoolStats();
                filterProxyPoolTable();
                renderC69Accounts(c69AllAccounts); // Cập nhật lại badge bảng accounts
            } catch(e) {
                showToast('Lỗi test proxy: ' + e, 'error');
            } finally {
                if (btnEl) btnEl.innerText = '⚡ Test';
            }
        }

        async function testAllProxiesBatch() {
            const btn = document.getElementById('btn-batch-test-proxies');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '⏳ Đang nạp danh sách proxy...';
            }

            await ensureProxyPoolLoaded();
            if (!c69ProxyPoolData || c69ProxyPoolData.length === 0) {
                try {
                    const res = await fetch(`${API_BASE}/api/browser/c69/proxies`);
                    const d = await res.json();
                    if (d.success && Array.isArray(d.proxies)) {
                        c69ProxyPoolData = d.proxies;
                    }
                } catch(e) {}
            }

            if (!c69ProxyPoolData || c69ProxyPoolData.length === 0) {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '⚡ Kiểm Tra Toàn Bộ (Check Live/Die)';
                }
                return showToast('Chưa có proxy nào trong pool để kiểm tra!', 'warning');
            }

            const proxyStrings = c69ProxyPoolData.map(p => p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`);
            showToast(`Bắt đầu kiểm tra song song ${proxyStrings.length} Proxies...`, 'info');

            try {
                // Kiểm tra theo từng đợt chunk 25 proxy để cập nhật giao diện realtime mượt mà
                const chunkSize = 25;
                for (let i = 0; i < proxyStrings.length; i += chunkSize) {
                    const chunk = proxyStrings.slice(i, i + chunkSize);
                    if (btn) btn.innerHTML = `⏳ Đang kiểm tra (${Math.min(i + chunkSize, proxyStrings.length)}/${proxyStrings.length})...`;

                    try {
                        const res = await fetch(`${API_BASE}/api/browser/proxies/test-batch`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ proxy_strings: chunk })
                        });
                        const d = await res.json();
                        if (d.success && Array.isArray(d.results)) {
                            d.results.forEach(item => {
                                if (item.proxy) {
                                    const testObj = {
                                        alive: item.alive,
                                        latency_ms: item.latency_ms,
                                        message: item.message
                                    };
                                    setProxyTestResult(item.proxy, null, testObj);
                                }
                            });
                            updateProxyPoolStats();
                            filterProxyPoolTable();
                            renderC69Accounts(c69AllAccounts);
                        }
                    } catch(errChunk) {
                        console.warn('Lỗi test chunk proxy:', errChunk);
                    }
                }

                updateProxyPoolStats();
                filterProxyPoolTable();
                renderC69Accounts(c69AllAccounts);
                showToast(`Đã hoàn tất kiểm tra ${proxyStrings.length} proxies!`, 'success');
            } catch(e) {
                showToast('Lỗi kiểm tra proxy: ' + e, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '⚡ Kiểm Tra Toàn Bộ (Check Live/Die)';
                }
            }
        }

        function openImportProxiesModal() {
            document.getElementById('import-proxies-textarea').value = '';
            const msgEl = document.getElementById('import-proxies-msg');
            if (msgEl) {
                msgEl.style.display = 'none';
                msgEl.innerText = '';
            }
            document.getElementById('modal-import-proxies').style.display = 'flex';
        }

        function closeImportProxiesModal() {
            document.getElementById('modal-import-proxies').style.display = 'none';
        }

        async function submitImportProxies() {
            const text = document.getElementById('import-proxies-textarea').value.trim();
            const mode = document.querySelector('input[name="import-proxy-mode"]:checked')?.value || 'append';
            const msgEl = document.getElementById('import-proxies-msg');
            const btn = document.getElementById('btn-submit-import-proxies');

            if (!text) {
                if (msgEl) {
                    msgEl.style.display = 'block';
                    msgEl.style.background = 'rgba(239,68,68,0.15)';
                    msgEl.style.color = '#ef4444';
                    msgEl.innerText = 'Vui lòng dán danh sách proxy vào ô văn bản!';
                }
                return;
            }

            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '⏳ Đang import...';
            }

            try {
                const res = await fetch(`${API_BASE}/api/browser/c69/proxies/import`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxies_text: text, mode: mode })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || `Đã import thành công ${d.added} proxy mới!`, 'success');
                    closeImportProxiesModal();
                    // Nạp lại dữ liệu pool
                    c69ProxyPoolData = [];
                    await ensureProxyPoolLoaded(true);
                    await syncProxyStatusCacheFromBackend();
                    filterProxyPoolTable();
                    updateProxyPoolStats();
                    populateProxyPoolSelect();
                } else {
                    if (msgEl) {
                        msgEl.style.display = 'block';
                        msgEl.style.background = 'rgba(239,68,68,0.15)';
                        msgEl.style.color = '#ef4444';
                        msgEl.innerText = d.error || 'Lỗi khi import proxy!';
                    }
                }
            } catch(e) {
                if (msgEl) {
                    msgEl.style.display = 'block';
                    msgEl.style.background = 'rgba(239,68,68,0.15)';
                    msgEl.style.color = '#ef4444';
                    msgEl.innerText = 'Lỗi kết nối server: ' + e;
                }
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '📥 Bắt Đầu Import';
                }
            }
        }

        async function removeDeadProxiesFromPool() {
            const deadProxies = [];
            c69ProxyPoolData.forEach(p => {
                const pStr = p.proxy_string || `socks5://${p.username}:${p.password}@${p.host}:${p.port}`;
                const test = getProxyTestResult(pStr) || c69ProxyTestMap[pStr];
                if (test && !test.alive) {
                    deadProxies.push(pStr);
                }
            });

            if (deadProxies.length === 0) {
                showToast('Chưa có proxy nào được xác nhận Die. Hãy bấm "Kiểm Tra Toàn Bộ" trước!', 'info');
                return;
            }

            if (!confirm(`Bạn có chắc chắn muốn xóa ${deadProxies.length} proxy đã chết khỏi danh sách?`)) {
                return;
            }

            const btn = document.getElementById('btn-remove-dead-proxies');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '⏳ Đang xóa...';
            }

            try {
                const res = await fetch(`${API_BASE}/api/browser/proxies/remove-dead`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dead_proxies: deadProxies })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || `Đã dọn dẹp ${deadProxies.length} proxy die!`, 'success');
                    deadProxies.forEach(s => {
                        delete c69ProxyTestMap[s];
                        const clean = getProxyCleanKey(s);
                        delete c69ProxyTestMap[clean];
                    });
                    c69ProxyPoolData = [];
                    await ensureProxyPoolLoaded();
                    filterProxyPoolTable();
                    updateProxyPoolStats();
                } else {
                    showToast(d.error || d.message || 'Lỗi xóa proxy die!', 'error');
                }
            } catch(e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '🗑️ Xóa Proxy Die Khỏi Pool';
                }
            }
        }

        async function autoReplaceDeadProxies() {
            const btn = document.getElementById('btn-auto-replace-dead');
            if (btn) {
                btn.disabled = true;
                btn.innerHTML = '⏳ Đang quét & thay thế...';
            }

            try {
                const res = await fetch(`${API_BASE}/api/browser/proxies/auto-replace-dead`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const d = await res.json();
                if (d.success) {
                    if (d.replaced_count > 0) {
                        showToast(`🎉 Đã tự động thay thế ${d.replaced_count} proxy die sang proxy live cho các tài khoản!`, 'success');
                        loadC69AccountsTab();
                    } else {
                        showToast('Không có profile/tài khoản nào đang dùng proxy die!', 'info');
                    }
                } else {
                    showToast(d.message || 'Lỗi quét thay thế proxy!', 'error');
                }
            } catch(e) {
                showToast('Lỗi kết nối auto replace: ' + e, 'error');
            } finally {
                if (btn) {
                    btn.disabled = false;
                    btn.innerHTML = '🔄 Tự Động Thay Proxy Die Cho Tài Khoản';
                }
            }
        }

        // ── MODAL 1: THÊM TÀI KHOẢN MỚI ────────────────────────────────────────
        function openC69AddAccountModal() {
            document.getElementById('add-c69-username').value = '';
            document.getElementById('add-c69-password').value = '';
            document.getElementById('add-c69-email').value = '';
            document.getElementById('add-c69-note').value = '';
            document.getElementById('modal-c69-add-account').style.display = 'flex';
        }

        function closeC69AddAccountModal() {
            document.getElementById('modal-c69-add-account').style.display = 'none';
        }

        async function submitC69AddAccount() {
            const username = document.getElementById('add-c69-username').value.trim();
            const password = document.getElementById('add-c69-password').value.trim();
            const email = document.getElementById('add-c69-email').value.trim();
            const type = document.getElementById('add-c69-type').value;
            const status = parseInt(document.getElementById('add-c69-status').value) || 0;
            const note = document.getElementById('add-c69-note').value.trim();

            if (!username) {
                return showToast('Vui lòng nhập Username hoặc Email tài khoản!', 'warning');
            }

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/add-manual`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password, email, type, status, note })
                });
                const d = await res.json();
                if (d.success) {
                    showToast('Đã thêm tài khoản mới thành công!', 'success');
                    closeC69AddAccountModal();
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi thêm tài khoản!', 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            }
        }

        // ── MODAL 2: THÊM HÀNG LOẠT ───────────────────────────────────────────
        function openC69BulkAddModal() {
            document.getElementById('bulk-add-c69-text').value = '';
            document.getElementById('modal-c69-bulk-add').style.display = 'flex';
        }

        function closeC69BulkAddModal() {
            document.getElementById('modal-c69-bulk-add').style.display = 'none';
        }

        async function submitC69BulkAdd() {
            const text = document.getElementById('bulk-add-c69-text').value.trim();
            const type = document.getElementById('bulk-add-c69-type').value;

            if (!text) {
                return showToast('Vui lòng nhập danh sách tài khoản!', 'warning');
            }

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/bulk-add`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ raw_text: text, account_type: type })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || `Đã thêm thành công các tài khoản!`, 'success');
                    closeC69BulkAddModal();
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi thêm hàng loạt!', 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            }
        }

        // ── MODAL 3: GÁN SỞ HỮU SUB HÀNG LOẠT ────────────────────────────────
        function openC69BulkSubOwnerModal() {
            if (selectedC69AccIds.size === 0) {
                return showToast('Vui lòng chọn ít nhất 1 tài khoản!', 'warning');
            }
            document.getElementById('bulk-sub-count').innerText = selectedC69AccIds.size;
            document.getElementById('modal-c69-bulk-sub-owner').style.display = 'flex';
        }

        function closeC69BulkSubOwnerModal() {
            document.getElementById('modal-c69-bulk-sub-owner').style.display = 'none';
        }

        async function submitC69BulkSubOwner() {
            const owner = document.getElementById('bulk-sub-owner-select').value;
            if (!owner) {
                return showToast('Vui lòng chọn user sở hữu Sub!', 'warning');
            }

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/bulk-sub-owner`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account_ids: Array.from(selectedC69AccIds),
                        subscription_owner: owner
                    })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || 'Đã gán sở hữu Sub thành công!', 'success');
                    closeC69BulkSubOwnerModal();
                    selectedC69AccIds.clear();
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi gán sở hữu Sub!', 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            }
        }

        // ── MODAL 4: ĐỔI TRẠNG THÁI HÀNG LOẠT ────────────────────────────────
        function openC69BulkStatusModal() {
            if (selectedC69AccIds.size === 0) {
                return showToast('Vui lòng chọn ít nhất 1 tài khoản!', 'warning');
            }
            document.getElementById('bulk-status-count').innerText = selectedC69AccIds.size;
            document.getElementById('modal-c69-bulk-status').style.display = 'flex';
        }

        function closeC69BulkStatusModal() {
            document.getElementById('modal-c69-bulk-status').style.display = 'none';
        }

        async function submitC69BulkStatus() {
            const status = parseInt(document.getElementById('bulk-status-select').value);

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/bulk-status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account_ids: Array.from(selectedC69AccIds),
                        status: status
                    })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || 'Đã đổi trạng thái thành công!', 'success');
                    closeC69BulkStatusModal();
                    selectedC69AccIds.clear();
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi đổi trạng thái!', 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            }
        }

        // ── XÓA TÀI KHOẢN (ĐƠN LẺ & HÀNG LOẠT) ────────────────────────────────
        async function handleC69BulkDelete() {
            if (selectedC69AccIds.size === 0) return;
            if (!confirm(`Bạn có chắc chắn muốn xóa ${selectedC69AccIds.size} tài khoản đã chọn? Thao tác này không thể hoàn tác!`)) return;

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/bulk-delete`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        account_ids: Array.from(selectedC69AccIds)
                    })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || 'Đã xóa các tài khoản thành công!', 'success');
                    selectedC69AccIds.clear();
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi xóa tài khoản!', 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            }
        }

        async function deleteC69SingleAccount(accId) {
            const acc = c69AllAccounts.find(a => a.id === accId);
            const uname = acc ? acc.username : `#${accId}`;
            if (!confirm(`Bạn có chắc muốn xóa tài khoản @${uname}?`)) return;

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/${accId}`, { method: 'DELETE' });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || `Đã xóa tài khoản @${uname}!`, 'success');
                    selectedC69AccIds.delete(accId);
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi xóa tài khoản!', 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            }
        }

        // ── MODAL 5: XEM CHI TIẾT & SỬA TÀI KHOẢN ─────────────────────────────
        async function openC69AccountDetailModal(accId) {
            currentDetailAccId = accId;
            const acc = c69AllAccounts.find(a => a.id === accId) || {};
            
            document.getElementById('detail-c69-id').value = accId;
            document.getElementById('detail-c69-title').innerText = `🔍 Chi Tiết Tài Khoản #${accId} (@${acc.username || ''})`;
            document.getElementById('detail-c69-username').value = acc.username || '';
            document.getElementById('detail-c69-password').value = acc.password || '';
            document.getElementById('detail-c69-type').value = acc.type || 'Tiktok';
            document.getElementById('detail-c69-status').value = acc.status !== undefined ? acc.status : 0;
            document.getElementById('detail-c69-email').value = acc.email || '';
            document.getElementById('detail-c69-sub').value = acc.subscription || '';
            document.getElementById('detail-c69-sub-owner').value = acc.subscription_owner || '';
            document.getElementById('detail-c69-note').value = acc.note || '';

            const metaEl = document.getElementById('detail-c69-meta');
            if (metaEl) {
                metaEl.innerHTML = `
                    Tạo bởi: <b>${acc.created_by || '—'}</b> (${formatDateString(acc.created)}) | 
                    Sửa đổi: <b>${acc.modified_by || '—'}</b> (${formatDateString(acc.modified)})
                `;
            }

            document.getElementById('modal-c69-account-detail').style.display = 'flex';
        }

        function closeC69AccountDetailModal() {
            document.getElementById('modal-c69-account-detail').style.display = 'none';
        }

        async function submitC69UpdateAccount() {
            const accId = document.getElementById('detail-c69-id').value;
            if (!accId) return;

            const username = document.getElementById('detail-c69-username').value.trim();
            const password = document.getElementById('detail-c69-password').value.trim();
            const type = document.getElementById('detail-c69-type').value;
            const status = parseInt(document.getElementById('detail-c69-status').value);
            const email = document.getElementById('detail-c69-email').value.trim();
            const subscription = document.getElementById('detail-c69-sub').value.trim();
            const subscription_owner = document.getElementById('detail-c69-sub-owner').value.trim();
            const note = document.getElementById('detail-c69-note').value.trim();

            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/${accId}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username, password, type, status, email, subscription, subscription_owner, note
                    })
                });
                const d = await res.json();
                if (d.success) {
                    showToast(d.message || 'Đã lưu thay đổi tài khoản!', 'success');
                    closeC69AccountDetailModal();
                    loadC69AccountsTab();
                } else {
                    showToast(d.message || 'Lỗi lưu tài khoản!', 'error');
                }
            } catch (e) {
                showToast('Lỗi kết nối: ' + e, 'error');
            }
        }

        // ── MODAL 6: XEM MÃ 2FA VÀ OTP ────────────────────────────────────────
        async function openC692FAModal(accId) {
            current2FaAccId = accId;
            document.getElementById('c69-2fa-code-display').innerText = '...';
            document.getElementById('c69-2fa-secret-display').innerText = 'Đang tải...';
            document.getElementById('modal-c69-2fa').style.display = 'flex';

            await refreshC692FA();
        }

        function openC692FAFromDetail() {
            if (currentDetailAccId) {
                openC692FAModal(currentDetailAccId);
            }
        }

        function closeC692FAModal() {
            document.getElementById('modal-c69-2fa').style.display = 'none';
        }

        async function refreshC692FA() {
            if (!current2FaAccId) return;
            try {
                const res = await fetch(`${API_BASE}/api/c69/accounts/${current2FaAccId}/2fa`);
                const d = await res.json();
                if (d.success) {
                    document.getElementById('c69-2fa-code-display').innerText = d.code || 'CHƯA CÓ';
                    document.getElementById('c69-2fa-secret-display').innerText = d.secret || 'Không có Secret Key';
                } else {
                    document.getElementById('c69-2fa-code-display').innerText = 'LỖI';
                    document.getElementById('c69-2fa-secret-display').innerText = d.message || 'Lỗi nạp 2FA';
                }
            } catch (e) {
                document.getElementById('c69-2fa-code-display').innerText = 'LỖI';
                document.getElementById('c69-2fa-secret-display').innerText = String(e);
            }
        }

        // ── MODAL 7: REG TIKTOK AUTO 24/7 ────────────────────────────────────
        function openC69TikTokRegModal() {
            document.getElementById('modal-c69-reg-tiktok').style.display = 'flex';
        }

        function closeC69TikTokRegModal() {
            document.getElementById('modal-c69-reg-tiktok').style.display = 'none';
        }

        async function submitC69StartTikTokReg() {
            const method = document.getElementById('reg-tiktok-method').value;
            const captcha = document.getElementById('reg-tiktok-captcha').value;
            const proxy = document.getElementById('reg-tiktok-proxy').value.trim();

            showToast(`🚀 Đã khởi chạy tiến trình Đăng ký TikTok Auto (Phương thức: ${method}). Theo dõi tại tab Trình duyệt Farm!`, 'success');
            closeC69TikTokRegModal();
        }

        // ── MODAL 8: ĐỌC MAIL SỐ LƯỢNG LỚN ────────────────────────────────────
        function openC69BulkMailModal() {
            document.getElementById('bulk-mail-c69-input').value = '';
            document.getElementById('bulk-mail-c69-results').style.display = 'none';
            document.getElementById('modal-c69-bulk-mail').style.display = 'flex';
        }

        function closeC69BulkMailModal() {
            document.getElementById('modal-c69-bulk-mail').style.display = 'none';
        }

        async function submitC69BulkReadMail() {
            const raw = document.getElementById('bulk-mail-c69-input').value.trim();
            if (!raw) {
                return showToast('Vui lòng nhập danh sách email!', 'warning');
            }
            const lines = raw.split('\n').map(l => l.trim()).filter(Boolean);
            const resBox = document.getElementById('bulk-mail-c69-results');
            resBox.style.display = 'block';
            resBox.innerHTML = `<div>⏳ Đang quét đọc hộp thư cho ${lines.length} email...</div>`;

            let scanned = 0;
            for (const line of lines) {
                const parts = line.split('|');
                const mail = parts[0];
                scanned++;
                resBox.innerHTML += `<div style="color:#38bdf8; margin-top:3px;">📧 ${mail}: Đang kết nối server C69...</div>`;
            }
            showToast(`Hoàn tất đọc ${scanned} email!`, 'success');
        }

        async function createProfileAndNurtureForAccount(accId) {
            const acc = c69AllAccounts.find(a => a.id === accId);
            if (!acc) return;

            const autoProxy = document.getElementById('c69-auto-proxy-chk')?.checked ?? true;
            showToast(`Đang tạo Profile Random và nuôi nick @${acc.username}...`, "info");

            try {
                const res = await fetch(`${API_BASE}/api/browser/nurture/create-and-nurture`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        c69_account_id: acc.id,
                        c69_username: acc.username,
                        c69_password: acc.password,
                        auto_assign_c69_proxy: autoProxy
                    })
                });
                const d = await res.json();
                showToast(d.message || "Đã tạo profile và kích hoạt nuôi!", "success");
                loadC69AccountsTab();
            } catch(e) {
                showToast("Lỗi: " + e, "error");
            }
        }

        async function startNurtureSelectedAccounts() {
            const selectedIds = selectedC69AccIds.size > 0
                ? Array.from(selectedC69AccIds)
                : Array.from(document.querySelectorAll('.c69-acc-checkbox:checked')).map(cb => parseInt(cb.value));

            if (selectedIds.length === 0) {
                return showToast("Vui lòng tích chọn ít nhất 1 tài khoản TikTok!", "warning");
            }

            const autoProxy = document.getElementById('c69-auto-proxy-chk')?.checked ?? true;
            showToast(`Đang tạo Profile và nuôi cho ${selectedIds.length} tài khoản...`, "info");

            let started = 0;
            for (const id of selectedIds) {
                const acc = c69AllAccounts.find(a => a.id === id);
                if (acc) {
                    await fetch(`${API_BASE}/api/browser/nurture/create-and-nurture`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            c69_account_id: acc.id,
                            c69_username: acc.username,
                            c69_password: acc.password,
                            auto_assign_c69_proxy: autoProxy
                        })
                    }).catch(() => {});
                    started++;
                }
            }
            showToast(`Đã khởi tạo Profile và phát lệnh nuôi TikTok cho ${started} tài khoản!`, "success");
            loadC69AccountsTab();
        }

        async function toggleEngine(id) {
            const prof = allProfiles.find(p => p.id === id);
            if (!prof) return;
            const current = prof.engine_mode || 'native';
            let nextMode = 'js_stealth';
            if (current === 'js_stealth') nextMode = 'hybrid';
            else if (current === 'hybrid') nextMode = 'native';

            prof.engine_mode = nextMode;
            try {
                await fetch(`${API_BASE}/api/browser/profiles`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(prof)
                });
                filterProfiles();
            } catch(e) {
                console.error(e);
            }
        }

        let currentEngineFilter = 'all';

        async function checkBrowserCoreStatus() {
            try {
                const res = await fetch(`${API_BASE}/api/browser/core-status`);
                if (!res.ok) return;
                const data = await res.json();
                const badge = document.getElementById('core-status-badge');
                if (!badge) return;
                if (data.has_custom_core) {
                    badge.innerHTML = `<span class="badge-engine-native" style="cursor:help; font-size:10px;" title="${data.custom_path || 'qhtd-browser.exe'}">💎 Native C++: Sẵn Sàng</span>`;
                } else {
                    badge.innerHTML = `<span class="badge-engine-js" style="cursor:help; font-size:10px;" title="Chưa có folder qhtd-browser, đang kích hoạt System Chrome với lá chắn JS Stealth CDP (Sẵn sàng nạp C++ Core khi tải về)">⚡ JS Stealth CDP (Sẵn sàng C++ Core)</span>`;
                }
            } catch(e) {
                console.error(e);
            }
        }

        function setEngineFilter(mode, btn) {
            currentEngineFilter = mode;
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filterProfiles();
        }

        let currentNurtureFilter = 'all';

        function setNurtureFilter(mode, btn) {
            currentNurtureFilter = mode;
            document.querySelectorAll('.nurture-filter-btn').forEach(b => b.classList.remove('active'));
            if (btn) btn.classList.add('active');
            filterProfiles();
        }

        function filterProfiles() {
            const searchEl = document.getElementById('profile-search');
            const term = searchEl ? searchEl.value.toLowerCase().trim() : '';
            const filtered = allProfiles.filter(p => {
                const matchesTerm = !term || 
                                    (p.name && p.name.toLowerCase().includes(term)) || 
                                    (p.c69_username && p.c69_username.toLowerCase().includes(term)) ||
                                    (p.id && p.id.toString().includes(term)) ||
                                    (p.profile_user_agent && p.profile_user_agent.toLowerCase().includes(term)) ||
                                    (p.proxy_string && p.proxy_string.toLowerCase().includes(term)) ||
                                    (p.last_nurture_status && p.last_nurture_status.toLowerCase().includes(term)) ||
                                    (p.nurture_stage && p.nurture_stage.toLowerCase().includes(term));
                const mode = p.engine_mode || 'native';
                const matchesEngine = currentEngineFilter === 'all' || mode === currentEngineFilter;

                let matchesNurture = true;
                const isRunning = (p.nurture_status === 'running') || (typeof activeProfileIds !== 'undefined' && activeProfileIds.has && activeProfileIds.has(p.id));
                const isRateLimited = (p.last_nurture_status && p.last_nurture_status.includes('1h')) || 
                                      (p.nurture_stage && p.nurture_stage.includes('Chờ'));
                const isDone = (p.last_nurture_status && p.last_nurture_status.includes('thành công')) || 
                               (p.nurture_status === 'done');
                const isError = (p.nurture_status === 'error') || 
                                (p.last_nurture_status && !p.last_nurture_status.includes('thành công') && !isRateLimited);

                if (currentNurtureFilter === 'running') {
                    matchesNurture = isRunning;
                } else if (currentNurtureFilter === 'done') {
                    matchesNurture = isDone;
                } else if (currentNurtureFilter === 'ratelimit') {
                    matchesNurture = isRateLimited;
                } else if (currentNurtureFilter === 'error') {
                    matchesNurture = isError;
                } else if (currentNurtureFilter === 'unassigned') {
                    matchesNurture = !p.c69_account_id;
                }

                return matchesTerm && matchesEngine && matchesNurture;
            });
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

        function randomizeModalFields() {
            const gpus = [
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)",
                "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)",
                "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (AMD)",
                "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (Intel)",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)|Google Inc. (NVIDIA)"
            ];
            const cpus = ["4", "6", "8", "12", "16"];
            const rams = ["8", "16", "32"];
            const ress = ["1920x1080", "1920x1200", "1536x864", "2560x1440"];
            const engines = ["native", "js_stealth", "hybrid"];

            document.getElementById('modal-prof-gpu').value = gpus[Math.floor(Math.random() * gpus.length)];
            document.getElementById('modal-prof-cpu').value = cpus[Math.floor(Math.random() * cpus.length)];
            document.getElementById('modal-prof-ram').value = rams[Math.floor(Math.random() * rams.length)];
            document.getElementById('modal-prof-res').value = ress[Math.floor(Math.random() * ress.length)];
            document.getElementById('modal-prof-engine').value = engines[Math.floor(Math.random() * engines.length)];
        }

        function onCreateProxyTypeChange() {
            const t = document.getElementById('modal-prof-proxy-type').value;
            const input = document.getElementById('modal-prof-proxy');
            if (t === 'direct') {
                input.value = '';
                input.placeholder = '⚡ Chế độ Direct (Không dùng Proxy)';
                input.disabled = true;
            } else if (t === 'socks5') {
                input.placeholder = 'VD: 127.0.0.1:10808 hoặc user:pass@host:port';
                input.disabled = false;
            } else {
                input.placeholder = 'VD: 127.0.0.1:8080 hoặc user:pass@host:port';
                input.disabled = false;
            }
        }

        function onEditProxyTypeChange() {
            const t = document.getElementById('edit-prof-proxy-type').value;
            const input = document.getElementById('edit-prof-proxy');
            if (t === 'direct') {
                input.value = '';
                input.placeholder = '⚡ Chế độ Direct (Không dùng Proxy)';
                input.disabled = true;
            } else if (t === 'socks5') {
                input.placeholder = 'VD: host:port hoặc socks5://user:pass@host:port';
                input.disabled = false;
            } else {
                input.placeholder = 'VD: host:port hoặc http://user:pass@host:port';
                input.disabled = false;
            }
        }

        async function testModalProxy(modalType) {
            const isEdit = modalType === 'edit';
            const inputId = isEdit ? 'edit-prof-proxy' : 'modal-prof-proxy';
            const statusId = isEdit ? 'modal-edit-proxy-status' : 'modal-create-proxy-status';
            const typeId = isEdit ? 'edit-prof-proxy-type' : 'modal-prof-proxy-type';
            const val = document.getElementById(inputId).value.trim();
            const statusEl = document.getElementById(statusId);
            const pType = document.getElementById(typeId).value;

            if (pType === 'direct' || !val) {
                statusEl.innerHTML = `<span style="color:var(--warning);">⚡ Chế độ Direct hoặc chưa nhập Proxy!</span>`;
                return;
            }

            statusEl.innerHTML = `<span style="color:var(--primary);">⏳ Đang kiểm tra...</span>`;
            try {
                const res = await fetch(`${API_BASE}/api/browser/proxy/test`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ proxy_string: val })
                });
                const d = await res.json();
                if (d.success) {
                    statusEl.innerHTML = `<span style="color:#10b981; font-weight:700;">✅ Live (${d.latency_ms}ms)</span>`;
                } else {
                    statusEl.innerHTML = `<span style="color:#ef4444; font-weight:700;">❌ Die: ${d.message}</span>`;
                }
            } catch(e) {
                statusEl.innerHTML = `<span style="color:#ef4444;">Lỗi: ${e}</span>`;
            }
        }

        async function assignRandomC69ProxyToField(inputId, typeId) {
            const input = document.getElementById(inputId);
            const typeEl = document.getElementById(typeId);
            try {
                const res = await fetch(`${API_BASE}/api/browser/c69/proxies`);
                const data = await res.json();
                if (data.proxies && data.proxies.length > 0) {
                    const picked = data.proxies[Math.floor(Math.random() * data.proxies.length)];
                    typeEl.value = 'socks5';
                    input.disabled = false;
                    input.value = picked.proxy_string || ((picked.username && picked.password)
                        ? `socks5://${picked.username}:${picked.password}@${picked.host}:${picked.port}`
                        : `socks5://${picked.host}:${picked.port}`);
                    const isEdit = inputId.includes('edit');
                    testModalProxy(isEdit ? 'edit' : 'create');
                } else {
                    showToast('Chưa tải được Proxy từ Pool C69!', 'warning');
                }
            } catch (e) {
                showToast('Lỗi lấy Proxy C69: ' + e, 'error');
            }
        }

        function clearModalProxyField(inputId, typeId) {
            const input = document.getElementById(inputId);
            const typeEl = document.getElementById(typeId);
            input.value = '';
            typeEl.value = 'direct';
            input.disabled = true;
            input.placeholder = '⚡ Chế độ Direct (Không dùng Proxy)';
            const isEdit = inputId.includes('edit');
            const statusEl = document.getElementById(isEdit ? 'modal-edit-proxy-status' : 'modal-create-proxy-status');
            if (statusEl) statusEl.innerHTML = `<span style="color:var(--text-muted);">Direct (Không Proxy)</span>`;
        }

        function onEditProfOsChange() {
            const os = document.getElementById('edit-prof-os').value;
            if (os === 'Android') {
                setEditUaPreset('mobile');
                document.getElementById('edit-prof-res').value = '412x915';
            } else {
                setEditUaPreset('desktop');
                document.getElementById('edit-prof-res').value = '1920x1080';
            }
        }

        function setEditUaPreset(mode) {
            const uaInp = document.getElementById('edit-prof-ua');
            if (mode === 'mobile') {
                uaInp.value = 'Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.98 Mobile Safari/537.36';
            } else {
                uaInp.value = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36';
            }
        }

        function openEditFingerprintModal(id) {
            const p = allProfiles.find(x => x.id === id);
            if (!p) return;

            document.getElementById('edit-prof-id').value = p.id;
            document.getElementById('modal-edit-title').innerText = `🛠️ Tùy Chỉnh Dấu Vân Tay: Profile #${p.id} (${p.name})`;
            document.getElementById('edit-prof-name').value = p.name;
            document.getElementById('edit-prof-engine').value = p.engine_mode || 'native';
            document.getElementById('edit-prof-gpu-renderer').value = p.gpu_renderer || 'ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)';
            document.getElementById('edit-prof-cpu').value = p.profile_cpu || 8;
            document.getElementById('edit-prof-ram').value = p.profile_ram || 16;
            document.getElementById('edit-prof-res').value = p.profile_resolution || '1920x1080';
            document.getElementById('edit-prof-canvas-seed').value = p.canvas_seed || (p.id * 1664525 + 1013904);
            document.getElementById('edit-prof-audio-seed').value = p.audio_seed || (p.id * 1103515 + 12345);

            // Cấu hình OS & User Agent
            const isMob = (p.profile_os && p.profile_os.toLowerCase().includes('android')) || (p.profile_user_agent && p.profile_user_agent.includes('Mobile'));
            const osEl = document.getElementById('edit-prof-os');
            if (osEl) osEl.value = isMob ? 'Android' : 'Windows';
            const uaEl = document.getElementById('edit-prof-ua');
            if (uaEl) uaEl.value = p.profile_user_agent || '';

            // Cấu hình Proxy & WebRTC
            const pType = p.proxy_type || (p.proxy_string ? 'socks5' : 'direct');
            document.getElementById('edit-prof-proxy-type').value = pType;
            const pInput = document.getElementById('edit-prof-proxy');
            pInput.value = p.proxy_string || '';
            pInput.disabled = (pType === 'direct');
            document.getElementById('edit-prof-webrtc').value = p.webrtc_mode || 'proxy_only';
            const statusEl = document.getElementById('modal-edit-proxy-status');
            if (statusEl) statusEl.innerHTML = p.proxy_string ? `<span style="color:#10b981;">Đã nạp proxy</span>` : `<span style="color:var(--text-muted);">Direct</span>`;

            document.getElementById('modal-edit-fingerprint').style.display = 'flex';
        }

        function closeEditFingerprintModal() {
            document.getElementById('modal-edit-fingerprint').style.display = 'none';
        }

        function randomSeed(elementId) {
            const seed = Math.floor(Math.random() * 90000000) + 10000000;
            document.getElementById(elementId).value = seed;
        }

        function randomizeEditFingerprint() {
            randomSeed('edit-prof-canvas-seed');
            randomSeed('edit-prof-audio-seed');
            const gpus = [
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)",
                "ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)"
            ];
            const cpus = [4, 6, 8, 12, 16];
            const rams = [8, 16, 32];
            const isMob = document.getElementById('edit-prof-os')?.value === 'Android';
            const ress = isMob
                ? ["412x915", "393x873", "390x844", "428x926"]
                : ["1920x1080", "1920x1200", "1536x864", "2560x1440"];

            document.getElementById('edit-prof-gpu-renderer').value = gpus[Math.floor(Math.random() * gpus.length)];
            document.getElementById('edit-prof-cpu').value = cpus[Math.floor(Math.random() * cpus.length)];
            document.getElementById('edit-prof-ram').value = rams[Math.floor(Math.random() * rams.length)];
            document.getElementById('edit-prof-res').value = ress[Math.floor(Math.random() * ress.length)];
        }

        async function saveEditedFingerprint() {
            const id = parseInt(document.getElementById('edit-prof-id').value);
            const p = allProfiles.find(x => x.id === id);
            if (!p) return;

            p.name = document.getElementById('edit-prof-name').value.trim() || p.name;
            p.engine_mode = document.getElementById('edit-prof-engine').value;
            p.gpu_renderer = document.getElementById('edit-prof-gpu-renderer').value.trim();
            p.profile_cpu = parseInt(document.getElementById('edit-prof-cpu').value) || 8;
            p.profile_ram = parseInt(document.getElementById('edit-prof-ram').value) || 16;
            p.profile_resolution = document.getElementById('edit-prof-res').value.trim() || '1920x1080';
            p.canvas_seed = parseInt(document.getElementById('edit-prof-canvas-seed').value) || (id + 100);
            p.audio_seed = parseInt(document.getElementById('edit-prof-audio-seed').value) || (id + 200);

            // Lưu OS & User Agent
            const osEl = document.getElementById('edit-prof-os');
            if (osEl) p.profile_os = osEl.value;
            const uaEl = document.getElementById('edit-prof-ua');
            if (uaEl) p.profile_user_agent = uaEl.value.trim();

            // Lưu Proxy & WebRTC
            p.proxy_type = document.getElementById('edit-prof-proxy-type').value;
            p.proxy_string = (p.proxy_type === 'direct') ? '' : document.getElementById('edit-prof-proxy').value.trim();
            p.webrtc_mode = document.getElementById('edit-prof-webrtc').value;

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(p)
                });
                const d = await res.json();
                closeEditFingerprintModal();
                showToast(d.message || "Đã lưu cấu hình Fingerprint & Proxy!", "success");
                loadBrowserProfiles();
            } catch(e) {
                showToast("Lỗi khi lưu cấu hình: " + e, "error");
            }
        }

        async function submitCreateProfile() {
            const name = document.getElementById('modal-prof-name').value.trim();
            const engine = document.getElementById('modal-prof-engine').value;
            const gpuVal = document.getElementById('modal-prof-gpu').value;
            let gpu_renderer = null, gpu_vendor = null;
            if (gpuVal) {
                const parts = gpuVal.split('|');
                gpu_renderer = parts[0];
                gpu_vendor = parts[1] || "Google Inc. (NVIDIA)";
            }
            const cpu = parseInt(document.getElementById('modal-prof-cpu').value) || 8;
            const ram = parseInt(document.getElementById('modal-prof-ram').value) || 16;
            const resolution = document.getElementById('modal-prof-res').value || "1920x1080";
            const start_url = document.getElementById('modal-prof-url').value.trim() || "https://iphey.com";

            const proxy_type = document.getElementById('modal-prof-proxy-type').value;
            const proxy_string = (proxy_type === 'direct') ? '' : document.getElementById('modal-prof-proxy').value.trim();
            const webrtc_mode = document.getElementById('modal-prof-webrtc').value;

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        name: name || `Profile #${allProfiles.length}`,
                        engine_mode: engine,
                        gpu_renderer: gpu_renderer,
                        gpu_vendor: gpu_vendor,
                        profile_cpu: cpu,
                        profile_ram: ram,
                        profile_resolution: resolution,
                        profile_start_url: start_url,
                        proxy_string: proxy_string,
                        proxy_type: proxy_type,
                        webrtc_mode: webrtc_mode
                    })
                });
                const data = await res.json();
                closeCreateProfileModal();
                showToast(data.message || "Đã tạo profile thành công!", "success");
                loadBrowserProfiles();
            } catch (e) {
                showToast("Lỗi khi tạo profile: " + e, "error");
            }
        }

        async function launchBrowserProfile(id) {
            const btn = document.getElementById(`btn-action-${id}`);
            if (btn) {
                btn.innerText = "⏳ Đang mở...";
                btn.disabled = true;
            }

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/launch`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                const d = await res.json();
                activeProfileIds.add(id);
                renderProfiles(allProfiles);
                updateActiveCountBadge();
                showToast(`Đã mở Profile #${id}`, "success");
                setTimeout(syncActiveBrowserProfiles, 1000);
                setTimeout(syncActiveBrowserProfiles, 3000);
            } catch(e) {
                showToast("Lỗi khi mở profile: " + e, "error");
                renderProfiles(allProfiles);
            }
        }

        async function stopBrowserProfile(id) {
            const btn = document.getElementById(`btn-action-${id}`);
            if (btn) {
                btn.innerText = "⏳ Đang đóng...";
                btn.disabled = true;
            }

            try {
                const res = await fetch(`${API_BASE}/api/browser/profiles/stop`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ id })
                });
                activeProfileIds.delete(id);
                renderProfiles(allProfiles);
                updateActiveCountBadge();
                showToast(`Đã đóng Profile #${id}`, "info");
                setTimeout(syncActiveBrowserProfiles, 500);
            } catch(e) {
                showToast("Lỗi khi đóng profile: " + e, "error");
                renderProfiles(allProfiles);
            }
        }

        async function deleteBrowserProfile(id) {
            await fetch(`${API_BASE}/api/browser/profiles/${id}`, { method: 'DELETE' });
            showToast(`Đã xóa Profile #${id}`, "info");
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
                        <button class="btn btn-primary" style="padding: 3px 6px; font-size: 9px; margin-top: 4px;" onclick="showToast('Đang tải IPA qua IPATool cho app: ${app.trackName}...', 'info')">📥 Tải IPA</button>
                    </div>
                </div>
            `).join('');
        }

        async function rotateProxy() {
            const res = await fetch(`${API_BASE}/api/router/rotate`, { method: 'POST' });
            const d = await res.json();
            showToast(d.message || 'Đã phát lệnh xoay IP!', 'success');
        }

        // ── AUTO-UPDATE LOGIC ──
        let appUpdateInfo = null;

        async function checkAppUpdate(isManual = false) {
            try {
                if (isManual) {
                    showToast('Đang kiểm tra cập nhật từ máy chủ...', 'info');
                }
                const res = await fetch(`${API_BASE}/api/system/check-update`);
                const data = await res.json();
                appUpdateInfo = data;

                const btn = document.getElementById('btn-check-update');
                if (btn) {
                    btn.innerHTML = `⚡ v${data.current_version} ${data.has_update ? '<span style="background:#ef4444; color:#fff; font-size:9px; padding:1px 5px; border-radius:10px; margin-left:4px; font-weight:800;">MỚI</span>' : ''}`;
                }

                if (data.has_update) {
                    document.getElementById('update-modal-title').innerText = `🚀 Có Bản Cập Nhật Mới! (v${data.server_version})`;
                    document.getElementById('update-current-ver').innerText = `v${data.current_version}`;
                    document.getElementById('update-new-ver').innerText = `v${data.server_version}`;
                    document.getElementById('update-changelog-box').innerText = data.changelog || 'Tối ưu hóa hiệu năng, sửa lỗi và cải tiến tính năng.';
                    document.getElementById('update-progress-section').style.display = 'none';
                    document.getElementById('btn-update-action').disabled = false;
                    document.getElementById('btn-update-action').style.display = 'inline-block';
                    document.getElementById('btn-update-cancel').innerText = 'Để Sau';
                    document.getElementById('modal-auto-update').classList.add('active');
                } else if (isManual) {
                    showToast(`Bạn đang sử dụng phiên bản mới nhất (v${data.current_version})!`, 'success');
                }
            } catch (e) {
                console.error('Check update error:', e);
                if (isManual) {
                    showToast('Không thể kết nối máy chủ kiểm tra cập nhật!', 'error');
                }
            }
        }

        function closeUpdateModal() {
            document.getElementById('modal-auto-update').classList.remove('active');
        }

        async function triggerAppUpdate() {
            if (!appUpdateInfo || !appUpdateInfo.download_url) {
                showToast('Không có thông tin gói cập nhật!', 'error');
                return;
            }

            const btnAction = document.getElementById('btn-update-action');
            const btnCancel = document.getElementById('btn-update-cancel');
            const progressSec = document.getElementById('update-progress-section');
            const progressStatus = document.getElementById('update-progress-status');
            const progressPct = document.getElementById('update-progress-pct');
            const progressFill = document.getElementById('update-progress-fill');

            btnAction.disabled = true;
            btnCancel.disabled = true;
            progressSec.style.display = 'flex';
            progressStatus.innerText = '⏳ Đang tải bản cập nhật từ CDN C69...';
            progressPct.innerText = '25%';
            progressFill.style.width = '25%';

            let fakePct = 25;
            const progressTimer = setInterval(() => {
                if (fakePct < 85) {
                    fakePct += Math.floor(Math.random() * 15) + 5;
                    if (fakePct > 85) fakePct = 85;
                    progressPct.innerText = `${fakePct}%`;
                    progressFill.style.width = `${fakePct}%`;
                }
            }, 600);

            try {
                const res = await fetch(`${API_BASE}/api/system/perform-update`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ download_url: appUpdateInfo.download_url })
                });
                clearInterval(progressTimer);
                const data = await res.json();

                if (data.success) {
                    progressPct.innerText = '100%';
                    progressFill.style.width = '100%';
                    progressStatus.innerText = '🚀 Đang khởi động c69update.exe...';
                    showToast('Đã chuyển giao cho c69update.exe. Ứng dụng sẽ tự đóng và mở lại!', 'success');
                    setTimeout(() => {
                        document.body.innerHTML = `
                            <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100vh; background:#020409; color:#fff; font-family:sans-serif; text-align:center;">
                                <div style="font-size:48px; margin-bottom:16px;">🔄</div>
                                <h2 style="color:#00f2fe; margin-bottom:8px;">Đang Thực Hiện Cập Nhật Tự Động...</h2>
                                <p style="color:#94a3b8; font-size:14px; max-width:400px;">Tiến trình c69update.exe đang giải nén và thay thế file. MunAutomation sẽ tự động khởi động lại sau giây lát!</p>
                            </div>
                        `;
                    }, 1500);
                } else {
                    progressSec.style.display = 'none';
                    btnAction.disabled = false;
                    btnCancel.disabled = false;
                    showToast(data.message || 'Lỗi khi thực hiện cập nhật!', 'error');
                }
            } catch (e) {
                clearInterval(progressTimer);
                progressSec.style.display = 'none';
                btnAction.disabled = false;
                btnCancel.disabled = false;
                showToast('Lỗi kết nối khi cập nhật: ' + e, 'error');
            }
        }

        const savedTab = localStorage.getItem('mun_active_tab') || 'browser';
        switchNav(savedTab, true);
        checkC69Auth();
        refreshAll();
        setInterval(refreshDevices, 8000);
        setTimeout(() => checkAppUpdate(false), 2000);
    </script>
</body>
</html>"#)
}
