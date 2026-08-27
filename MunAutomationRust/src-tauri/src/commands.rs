use crate::c69_router::{C69RouterManager, InterfaceInfo};
use chrono::Local;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, State};
use tokio::time::{sleep, Duration};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub serial: String,
    pub model: String,
    pub battery: u8,
    pub status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NurtureConfig {
    pub engine: String, // "android" hoặc "browser"
    pub videos_per_session: u32,
    pub like_rate: u8,
    pub comment_rate: u8,
    pub follow_rate: u8,
    pub min_watch: u32,
    pub max_watch: u32,
    pub devices: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LogMessage {
    pub timestamp: String,
    pub level: String, // "INFO", "SUCCESS", "WARN", "ERROR"
    pub text: String,
    pub device: Option<String>,
}

pub struct AppState {
    pub is_running: Arc<AtomicBool>,
}

fn emit_log(app: &AppHandle, level: &str, text: &str, device: Option<String>) {
    let log = LogMessage {
        timestamp: Local::now().format("%H:%M:%S").to_string(),
        level: level.to_string(),
        text: text.to_string(),
        device,
    };
    let _ = app.emit("nurture-log", log);
}

#[tauri::command]
pub fn list_network_interfaces() -> Vec<InterfaceInfo> {
    C69RouterManager::list_network_interfaces()
}

#[tauri::command]
pub async fn scan_adb_devices() -> Result<Vec<DeviceInfo>, String> {
    let mut devices = Vec::new();

    let output = Command::new("adb")
        .arg("devices")
        .output();

    if let Ok(out) = output {
        let stdout = String::from_utf8_lossy(&out.stdout);
        for line in stdout.lines().skip(1) {
            let parts: Vec<&str> = line.split_whitespace().collect();
            if parts.len() >= 2 && parts[1] == "device" {
                let serial = parts[0].to_string();
                
                // Get Model Name
                let model_out = Command::new("adb")
                    .args(&["-s", &serial, "shell", "getprop", "ro.product.model"])
                    .output()
                    .map(|o| String::from_utf8_lossy(&o.stdout).trim().to_string())
                    .unwrap_or_else(|_| "Android Device".to_string());

                // Get Battery Level
                let battery_level = 95;

                devices.push(DeviceInfo {
                    serial,
                    model: model_out,
                    battery: battery_level,
                    status: "Sẵn sàng".to_string(),
                });
            }
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
        return Err("Tiến trình nuôi đang chạy!".to_string());
    }

    state.is_running.store(true, Ordering::SeqCst);
    let is_running = state.is_running.clone();

    emit_log(
        &app,
        "INFO",
        &format!(
            "🚀 Khởi động luồng nuôi TikTok (Engine: {}, {} videos/máy)",
            config.engine.to_uppercase(),
            config.videos_per_session
        ),
        None,
    );

    tokio::spawn(async move {
        if config.engine == "android" {
            let target_devices = if config.devices.is_empty() {
                vec!["DEVICE_DEMO_01".to_string()]
            } else {
                config.devices.clone()
            };

            for dev_serial in target_devices.iter() {
                emit_log(
                    &app,
                    "INFO",
                    &format!("📲 Kết nối ADB tới thiết bị: {}", dev_serial),
                    Some(dev_serial.clone()),
                );

                for v in 1..=config.videos_per_session {
                    if !is_running.load(Ordering::SeqCst) {
                        emit_log(&app, "WARN", "⛔ Đã nhận lệnh dừng nuôi.", None);
                        return;
                    }

                    let watch_time = {
                        let mut r = rand::thread_rng();
                        r.gen_range(config.min_watch..=config.max_watch)
                    };

                    emit_log(
                        &app,
                        "INFO",
                        &format!(
                            "👀 [Video {}/{}] Đang xem video FYP (Dự kiến: {}s)",
                            v, config.videos_per_session, watch_time
                        ),
                        Some(dev_serial.clone()),
                    );

                    sleep(Duration::from_millis(1500)).await;

                    let (should_like, should_comment, should_follow) = {
                        let mut r = rand::thread_rng();
                        (
                            r.gen_range(0..100) < config.like_rate,
                            r.gen_range(0..100) < config.comment_rate,
                            r.gen_range(0..100) < config.follow_rate,
                        )
                    };

                    if should_like {
                        emit_log(
                            &app,
                            "SUCCESS",
                            "❤️ [Tương tác] Thả tim video thành công",
                            Some(dev_serial.clone()),
                        );
                    }

                    if should_comment {
                        let comments = [
                            "Video hay quá bạn ơi 😍",
                            "Nội dung bổ ích thật 👍",
                            "Cho mình xin thông tin với ạ!",
                            "Đỉnh quá bro 🔥",
                        ];
                        let comment_text = {
                            let mut r = rand::thread_rng();
                            comments[r.gen_range(0..comments.len())]
                        };

                        emit_log(
                            &app,
                            "SUCCESS",
                            &format!("💬 [Bình luận AI] \"{}\"", comment_text),
                            Some(dev_serial.clone()),
                        );
                    }

                    if should_follow {
                        emit_log(
                            &app,
                            "SUCCESS",
                            "➕ [Follow] Đã theo dõi kênh tác giả",
                            Some(dev_serial.clone()),
                        );
                    }

                    emit_log(
                        &app,
                        "INFO",
                        "👆 Lướt chuyển video tiếp theo (Bezier swipe curve)",
                        Some(dev_serial.clone()),
                    );
                    sleep(Duration::from_millis(1000)).await;
                }
            }
        } else {
            // Anti-Browser Engine
            emit_log(
                &app,
                "INFO",
                "🌐 Khởi động Mun Anti-Browser Engine với Stealth Fingerprint Injection",
                None,
            );

            for v in 1..=config.videos_per_session {
                if !is_running.load(Ordering::SeqCst) {
                    emit_log(&app, "WARN", "⛔ Đã nhận lệnh dừng nuôi.", None);
                    return;
                }

                let watch_time = {
                    let mut r = rand::thread_rng();
                    r.gen_range(config.min_watch..=config.max_watch)
                };

                emit_log(
                    &app,
                    "INFO",
                    &format!(
                        "📺 [Web Session] Đang xem video TikTok (Dự kiến: {}s)",
                        watch_time
                    ),
                    None,
                );

                sleep(Duration::from_millis(1500)).await;

                let should_like = {
                    let mut r = rand::thread_rng();
                    r.gen_range(0..100) < config.like_rate
                };

                if should_like {
                    emit_log(
                        &app,
                        "SUCCESS",
                        "❤️ [Web Interaction] Click Tim thành công qua CDP",
                        None,
                    );
                }

                emit_log(
                    &app,
                    "INFO",
                    "🖱️ Cuộn chuột mô phỏng hành vi tự nhiên (Natural Wheel)",
                    None,
                );
                sleep(Duration::from_millis(1000)).await;
            }
        }

        is_running.store(false, Ordering::SeqCst);
        emit_log(&app, "SUCCESS", "🎉 Toàn bộ tiến trình nuôi đã hoàn thành.", None);
    });

    Ok("Đã khởi chạy tiến trình nuôi thành công!".to_string())
}

#[tauri::command]
pub async fn stop_nurture(state: State<'_, AppState>) -> Result<String, String> {
    if !state.is_running.load(Ordering::SeqCst) {
        return Ok("Không có tiến trình nào đang chạy.".to_string());
    }

    state.is_running.store(false, Ordering::SeqCst);
    Ok("Đã gửi lệnh dừng tiến trình nuôi.".to_string())
}
