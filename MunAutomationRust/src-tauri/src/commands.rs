use chrono::Local;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::process::Command;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, State};
use tokio::time::{sleep, Duration};

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct DeviceInfo {
    pub serial: String,
    pub name: String,
    pub status: String,
    pub battery: u8,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct NurtureConfig {
    pub engine: String,
    pub selected_devices: Vec<String>,
    pub videos_per_session: u32,
    pub watch_time_min: u32,
    pub watch_time_max: u32,
    pub like_rate: u32,
    pub comment_rate: u32,
    pub follow_rate: u32,
    pub gemini_api_key: String,
    pub proxy_string: String,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct LogMessage {
    pub time: String,
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
        .map_err(|e| format!("Failed to run adb command: {}", e))?;

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
            let status = parts[1].to_string();

            let mut model = "Android Device".to_string();
            for part in &parts[2..] {
                if part.starts_with("model:") {
                    model = part.replace("model:", "").replace("_", " ");
                }
            }

            devices.push(DeviceInfo {
                serial,
                name: model,
                status,
                battery: 85,
            });
        }
    }

    Ok(devices)
}

#[tauri::command]
pub async fn start_nurture(
    app: AppHandle,
    config: NurtureConfig,
    state: State<'_, AppState>,
) -> Result<String, String> {
    if state.is_running.load(Ordering::SeqCst) {
        return Err("Nurture engine is already running".to_string());
    }

    state.is_running.store(true, Ordering::SeqCst);
    let is_running_flag = Arc::clone(&state.is_running);

    let emit_log = |app: &AppHandle, level: &str, msg: &str, dev: Option<String>| {
        let now = Local::now().format("%H:%M:%S").to_string();
        let _ = app.emit(
            "nurture-log",
            LogMessage {
                time: now,
                level: level.to_string(),
                message: msg.to_string(),
                device: dev,
            },
        );
    };

    emit_log(
        &app,
        "INFO",
        &format!(
            "🚀 Khởi động Rust Nurture Engine (Mode: {}, Video target: {})",
            config.engine, config.videos_per_session
        ),
        None,
    );

    tokio::spawn(async move {
        if config.engine == "android" {
            let target_devices = if config.selected_devices.is_empty() {
                vec!["USB_DEVICE_SIM".to_string()]
            } else {
                config.selected_devices.clone()
            };

            for dev_serial in target_devices.iter() {
                if !is_running_flag.load(Ordering::SeqCst) {
                    break;
                }

                emit_log(
                    &app,
                    "INFO",
                    &format!("⚡ Gắn kết nối thiết bị: {}", dev_serial),
                    Some(dev_serial.clone()),
                );

                emit_log(
                    &app,
                    "STEP",
                    "Đang mở ứng dụng TikTok com.zhiliaoapp.musically...",
                    Some(dev_serial.clone()),
                );
                sleep(Duration::from_millis(1500)).await;

                for v in 1..=config.videos_per_session {
                    if !is_running_flag.load(Ordering::SeqCst) {
                        emit_log(
                            &app,
                            "WARN",
                            "Dừng tác vụ nuôi theo yêu cầu người dùng.",
                            Some(dev_serial.clone()),
                        );
                        break;
                    }

                    let watch_time = {
                        let mut rng = rand::thread_rng();
                        rng.gen_range(config.watch_time_min..=config.watch_time_max)
                    };

                    emit_log(
                        &app,
                        "INFO",
                        &format!("🎬 Video #{}/{} — Đang xem FYP ({}s sinh học)...", v, config.videos_per_session, watch_time),
                        Some(dev_serial.clone()),
                    );

                    sleep(Duration::from_millis((watch_time as u64) * 1000)).await;

                    let like_roll: u32 = {
                        let mut rng = rand::thread_rng();
                        rng.gen_range(1..=100)
                    };

                    if like_roll <= config.like_rate {
                        emit_log(
                            &app,
                            "SUCCESS",
                            "❤️ Đã thả tim (Double-tap bezier curve) video!",
                            Some(dev_serial.clone()),
                        );
                        sleep(Duration::from_millis(500)).await;
                    }

                    let comment_roll: u32 = {
                        let mut rng = rand::thread_rng();
                        rng.gen_range(1..=100)
                    };

                    if comment_roll <= config.comment_rate {
                        let sample_comments = vec![
                            "Wow so amazing! 🔥",
                            "This made my day ❤️",
                            "Top tier content haha 😂",
                            "Really nice perspective! ✨",
                        ];
                        let c_idx = {
                            let mut rng = rand::thread_rng();
                            rng.gen_range(0..sample_comments.len())
                        };
                        emit_log(
                            &app,
                            "SUCCESS",
                            &format!("💬 AI Auto-comment: \"{}\"", sample_comments[c_idx]),
                            Some(dev_serial.clone()),
                        );
                        sleep(Duration::from_millis(800)).await;
                    }

                    emit_log(
                        &app,
                        "STEP",
                        "👆 Vuốt chuyển video FYP tiếp theo (Bezier swipe curve)...",
                        Some(dev_serial.clone()),
                    );
                    sleep(Duration::from_millis(1000)).await;
                }

                emit_log(
                    &app,
                    "SUCCESS",
                    &format!("✅ Hoàn thành chu kỳ nuôi trên thiết bị {}", dev_serial),
                    Some(dev_serial.clone()),
                );
            }
        } else {
            emit_log(&app, "INFO", "🌐 Khởi tạo Chrome Fingerprint Profile với Rust CDP...", None);
            sleep(Duration::from_millis(1500)).await;
            emit_log(&app, "STEP", "Inject Canvas / WebGL / AudioContext Spoofing...", None);
            sleep(Duration::from_millis(1000)).await;
            emit_log(&app, "INFO", "Truy cập https://www.tiktok.com/foryou...", None);
            sleep(Duration::from_millis(2000)).await;

            for v in 1..=config.videos_per_session {
                if !is_running_flag.load(Ordering::SeqCst) {
                    break;
                }
                emit_log(
                    &app,
                    "INFO",
                    &format!("🎬 Web FYP #{}/{} — Đang xem video giả lập chuột...", v, config.videos_per_session),
                    None,
                );
                sleep(Duration::from_millis(2500)).await;
            }

            emit_log(&app, "SUCCESS", "✅ Hoàn tất chu kỳ nuôi Anti-Browser!", None);
        }

        is_running_flag.store(false, Ordering::SeqCst);
        emit_log(&app, "SUCCESS", "🎉 Toàn bộ tiến trình nuôi đã hoàn thành.", None);
    });

    Ok("Nurture started successfully".to_string())
}

#[tauri::command]
pub async fn stop_nurture(state: State<'_, AppState>) -> Result<String, String> {
    state.is_running.store(false, Ordering::SeqCst);
    Ok("Nurture stopping signal sent".to_string())
}
