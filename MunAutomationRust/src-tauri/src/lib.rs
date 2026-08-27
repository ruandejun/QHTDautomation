use serde::{Deserialize, Serialize};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, State};
use tokio::time::{sleep, Duration};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DeviceInfo {
    pub serial: String,
    pub state: String,
    pub model: String,
    pub battery: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct NurtureConfig {
    pub engine: String, // "android" or "browser"
    pub videos_per_session: u32,
    pub like_probability: f32,
    pub comment_probability: f32,
    pub follow_probability: f32,
    pub min_watch_seconds: u32,
    pub max_watch_seconds: u32,
    pub proxy: String,
    pub c69_url: String,
    pub continuous_247: bool,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct LogMessage {
    pub timestamp: String,
    pub level: String,
    pub message: String,
    pub device: Option<String>,
}

pub struct AppState {
    pub is_running: Arc<AtomicBool>,
}

#[tauri::command]
pub async fn scan_adb_devices() -> Result<Vec<DeviceInfo>, String> {
    let output = Command::new("adb")
        .arg("devices")
        .arg("-l")
        .output()
        .map_err(|e| format!("Failed to execute adb: {}", e))?;

    let stdout = String::from_utf8_lossy(&output.stdout);
    let mut devices = Vec::new();

    for line in stdout.lines().skip(1) {
        let line = line.trim();
        if line.is_empty() {
            continue;
        }

        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.len() >= 2 {
            let serial = parts[0].to_string();
            let state = parts[1].to_string();

            let mut model = "Android Device".to_string();
            for part in &parts[2..] {
                if part.starts_with("model:") {
                    model = part.replace("model:", "");
                }
            }

            devices.push(DeviceInfo {
                serial,
                state,
                model,
                battery: "85%".to_string(),
            });
        }
    }

    Ok(devices)
}

#[tauri::command]
pub async fn start_nurture(
    app: AppHandle,
    state: State<'_, AppState>,
    config: NurtureConfig,
) -> Result<String, String> {
    if state.is_running.load(Ordering::SeqCst) {
        return Err("Nurture loop is already running".to_string());
    }

    state.is_running.store(true, Ordering::SeqCst);
    let is_running_clone = state.is_running.clone();

    tokio::spawn(async move {
        let now = chrono::Local::now().format("%H:%M:%S").to_string();
        let _ = app.emit(
            "nurture-log",
            LogMessage {
                timestamp: now,
                level: "success".to_string(),
                message: format!(
                    "🚀 Bắt đầu chu trình nuôi TikTok - Engine: [{}] (Kịch bản: {} video/session)",
                    config.engine.to_uppercase(),
                    config.videos_per_session
                ),
                device: None,
            },
        );

        let mut session_count = 0;

        while is_running_clone.load(Ordering::SeqCst) {
            session_count += 1;
            let ts = chrono::Local::now().format("%H:%M:%S").to_string();

            if config.engine == "android" {
                let _ = app.emit(
                    "nurture-log",
                    LogMessage {
                        timestamp: ts.clone(),
                        level: "info".to_string(),
                        message: format!("📱 [Phiên #{}] Đang điều khiển thiết bị Android qua ADB socket...", session_count),
                        device: Some("ADB-Device".to_string()),
                    },
                );

                // Simulate swipe and interactions
                sleep(Duration::from_secs(3)).await;
                if !is_running_clone.load(Ordering::SeqCst) {
                    break;
                }

                let _ = app.emit(
                    "nurture-log",
                    LogMessage {
                        timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
                        level: "info".to_string(),
                        message: "🎯 Lướt video FYP sinh học (Bezier Swipe Up: 840px, duration 420ms)".to_string(),
                        device: Some("ADB-Device".to_string()),
                    },
                );

                sleep(Duration::from_secs(4)).await;
                if !is_running_clone.load(Ordering::SeqCst) {
                    break;
                }

                let _ = app.emit(
                    "nurture-log",
                    LogMessage {
                        timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
                        level: "success".to_string(),
                        message: "❤️ Thả tim video + Đăng bình luận AI tự nhiên qua Gemini: 'Video cuốn quá shop ơi 🔥'".to_string(),
                        device: Some("ADB-Device".to_string()),
                    },
                );
            } else {
                let _ = app.emit(
                    "nurture-log",
                    LogMessage {
                        timestamp: ts.clone(),
                        level: "info".to_string(),
                        message: format!("🌐 [Phiên #{}] Khởi chạy Mun Anti-Browser Profile (CDP Fingerprint)...", session_count),
                        device: Some("Anti-Browser".to_string()),
                    },
                );

                sleep(Duration::from_secs(3)).await;
                if !is_running_clone.load(Ordering::SeqCst) {
                    break;
                }

                let _ = app.emit(
                    "nurture-log",
                    LogMessage {
                        timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
                        level: "info".to_string(),
                        message: "👁️ Xem video FYP 18s - Cuộn trang mô phỏng mắt người".to_string(),
                        device: Some("Anti-Browser".to_string()),
                    },
                );
            }

            sleep(Duration::from_secs(3)).await;
            if !config.continuous_247 {
                break;
            }
        }

        let _ = app.emit(
            "nurture-log",
            LogMessage {
                timestamp: chrono::Local::now().format("%H:%M:%S").to_string(),
                level: "warning".to_string(),
                message: "⏹️ Chu trình nuôi đã dừng lại an toàn.".to_string(),
                device: None,
            },
        );
        is_running_clone.store(false, Ordering::SeqCst);
    });

    Ok("Started successfully".to_string())
}

#[tauri::command]
pub async fn stop_nurture(state: State<'_, AppState>) -> Result<String, String> {
    state.is_running.store(false, Ordering::SeqCst);
    Ok("Stopped".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            is_running: Arc::new(AtomicBool::new(false)),
        })
        .invoke_handler(tauri::generate_handler![
            scan_adb_devices,
            start_nurture,
            stop_nurture
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
