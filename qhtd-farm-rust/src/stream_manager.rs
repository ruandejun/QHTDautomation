use crate::adb_manager::AdbManager;
use axum::extract::ws::{Message, WebSocket};
use futures_util::{SinkExt, StreamExt};
use parking_lot::RwLock;
use serde::Deserialize;
use std::collections::HashMap;
use std::sync::Arc;
use std::time::Duration;
use tokio::sync::broadcast;
use tokio::sync::broadcast::error::RecvError;
use tracing::info;

#[derive(Debug, Deserialize)]
#[serde(tag = "type")]
pub enum TouchEvent {
    #[serde(rename = "down")]
    Down { x: u32, y: u32 },
    #[serde(rename = "move")]
    Move { x: u32, y: u32 },
    #[serde(rename = "up")]
    Up { x: u32, y: u32 },
    #[serde(rename = "tap")]
    Tap { x: u32, y: u32 },
    #[serde(rename = "swipe")]
    Swipe { x1: u32, y1: u32, x2: u32, y2: u32, duration: u32 },
    #[serde(rename = "scroll")]
    Scroll { x: u32, y: u32, delta_y: i32 },
    #[serde(rename = "key")]
    Key { code: u32 },
    #[serde(rename = "text")]
    Text { text: String },
    #[serde(rename = "home")]
    Home,
    #[serde(rename = "back")]
    Back,
    #[serde(rename = "recents")]
    Recents,
    #[serde(rename = "wake")]
    Wake,
    #[serde(rename = "power")]
    Power,
    #[serde(rename = "unlock")]
    Unlock,
    #[serde(rename = "vol_up")]
    VolumeUp,
    #[serde(rename = "vol_down")]
    VolumeDown,
    #[serde(rename = "launch")]
    Launch { package: Option<String> },
}

#[derive(Clone)]
pub struct StreamManager {
    adb: Arc<AdbManager>,
    channels: Arc<RwLock<HashMap<String, broadcast::Sender<Vec<u8>>>>>,
    active_devices: Arc<RwLock<HashMap<String, bool>>>,
}

impl StreamManager {
    pub fn new(adb: Arc<AdbManager>) -> Self {
        Self {
            adb,
            channels: Arc::new(RwLock::new(HashMap::new())),
            active_devices: Arc::new(RwLock::new(HashMap::new())),
        }
    }

    pub fn get_or_create_channel(&self, serial: &str) -> broadcast::Sender<Vec<u8>> {
        let mut lock = self.channels.write();
        if let Some(tx) = lock.get(serial) {
            return tx.clone();
        }

        // Buffer = 2: keeps strictly latest frames, zero latency & zero memory buildup
        let (tx, _) = broadcast::channel(2);
        lock.insert(serial.to_string(), tx.clone());

        let adb_path = self.adb.get_adb_path().to_path_buf();
        let s = serial.to_string();
        let tx_clone = tx.clone();
        let active_map = self.active_devices.clone();

        // One independent async green-thread per device — no shared blocking pool contention.
        tokio::spawn(async move {
            info!("Starting ASYNC capture loop for device {}", s);
            active_map.write().insert(s.clone(), true);

            // Stagger start: each device offset by its serial hash to avoid ADB burst at t=0
            let stagger_ms = (s.bytes().map(|b| b as u64).sum::<u64>() % 10) * 20;
            tokio::time::sleep(Duration::from_millis(stagger_ms)).await;

            let mut frame_count: u64 = 0;

            loop {
                if !active_map.read().get(&s).copied().unwrap_or(false) {
                    break;
                }

                // Skip capture entirely if nobody is watching — saves USB + CPU
                if tx_clone.receiver_count() == 0 {
                    tokio::time::sleep(Duration::from_millis(200)).await;
                    continue;
                }

                frame_count += 1;
                let adb_path_c = adb_path.clone();
                let serial_c = s.clone();

                // ── REAL DEVICE: screencap in its own blocking thread ──
                let capture_result = tokio::task::spawn_blocking(move || {
                    let mut cmd = std::process::Command::new(&adb_path_c);
                    cmd.args(["-s", &serial_c, "exec-out", "screencap", "-p"]);
                    cmd.stdout(std::process::Stdio::piped());
                    cmd.stderr(std::process::Stdio::null());
                    cmd.stdin(std::process::Stdio::null());
                    #[cfg(target_os = "windows")]
                    {
                        use std::os::windows::process::CommandExt;
                        cmd.creation_flags(0x08000000);
                    }
                    let out = cmd.output()?;
                    if out.status.success() && out.stdout.len() > 2048 {
                        Ok::<Vec<u8>, std::io::Error>(out.stdout)
                    } else {
                        Err(std::io::Error::new(std::io::ErrorKind::Other, "empty"))
                    }
                }).await;

                match capture_result {
                    Ok(Ok(raw)) => {
                        // ── Compress in a blocking thread, THEN send ──
                        // We AWAIT this so the frame is definitely in the channel before we sleep.
                        let tx2 = tx_clone.clone();
                        let _ = tokio::task::spawn_blocking(move || {
                            if let Ok(img) = image::load_from_memory(&raw) {
                                let orig_w = img.width();
                                let orig_h = img.height();

                                // Dynamic aspect ratio scaling to crisp HD resolution (360x740 for 720x1480)
                                let (target_w, target_h) = if orig_h >= orig_w {
                                    let tw = 360;
                                    let th = ((orig_h as f64 / orig_w.max(1) as f64) * tw as f64).round() as u32;
                                    (tw, th)
                                } else {
                                    let th = 360;
                                    let tw = ((orig_w as f64 / orig_h.max(1) as f64) * th as f64).round() as u32;
                                    (tw, th)
                                };

                                let resized = img.resize_exact(
                                    target_w, target_h,
                                    image::imageops::FilterType::Triangle, // Smooth Bilinear antialiasing, crisp text!
                                );
                                let mut buf = Vec::with_capacity(32768);
                                let mut cur = std::io::Cursor::new(&mut buf);
                                let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut cur, 80);
                                if encoder.encode_image(&resized).is_ok() {
                                    let _ = tx2.send(buf);
                                }
                            }
                        }).await;

                        // ~14 FPS pacing: smooth live feedback with minimal memory overhead
                        tokio::time::sleep(Duration::from_millis(70)).await;
                    }
                    _ => {
                        // ── NO DEVICE: send ONE static placeholder frame then wait ──
                        if frame_count == 1 {
                            let tx2 = tx_clone.clone();
                            let _ = tokio::task::spawn_blocking(move || {
                                let w: u32 = 360;
                                let h: u32 = 740;
                                let mut img = image::RgbImage::new(w, h);
                                for (_x, _y, pixel) in img.enumerate_pixels_mut() {
                                    *pixel = image::Rgb([8, 12, 22]); // solid dark navy
                                }
                                let mut buf = Vec::new();
                                let mut cur = std::io::Cursor::new(&mut buf);
                                let mut encoder = image::codecs::jpeg::JpegEncoder::new_with_quality(&mut cur, 80);
                                if encoder.encode_image(&img).is_ok() {
                                    let _ = tx2.send(buf);
                                }
                            }).await;
                        }
                        // Wait 1s between retry checks
                        tokio::time::sleep(Duration::from_secs(1)).await;
                    }
                }
            }

            info!("Stopped ASYNC capture loop for device {}", s);
        });

        tx
    }

    pub async fn handle_websocket(&self, socket: WebSocket, serial: String) {
        let tx = self.get_or_create_channel(&serial);
        let mut rx = tx.subscribe();
        let adb = self.adb.clone();
        let serial_touch = serial.clone();

        let (mut sender, mut receiver) = socket.split();

        // Task 1: Forward video frames to browser.
        // CRITICAL FIX: handle RecvError::Lagged by skipping dropped frames
        // instead of exiting the loop — this prevents WebSocket disconnection
        // which was causing the all-screens-flicker symptom.
        let send_task = tokio::spawn(async move {
            loop {
                match rx.recv().await {
                    Ok(frame_data) => {
                        // If sending to browser fails (client disconnected), stop cleanly
                        if sender.send(Message::Binary(frame_data)).await.is_err() {
                            break;
                        }
                    }
                    Err(RecvError::Lagged(n)) => {
                        // Buffer overrun: skip the n dropped frames and continue.
                        // DO NOT break — this was the root cause of flicker!
                        info!("WS [{}]: {} frames dropped (receiver too slow), continuing", serial, n);
                        continue;
                    }
                    Err(RecvError::Closed) => {
                        // Sender gone (device removed) — exit cleanly
                        break;
                    }
                }
            }
        });

        // Task 2: Receive touch events from browser → ADB (non-blocking spawn_blocking)
        let recv_task = tokio::spawn(async move {
            while let Some(Ok(msg)) = receiver.next().await {
                match msg {
                    Message::Text(txt) => {
                        if let Ok(event) = serde_json::from_str::<TouchEvent>(&txt) {
                            let adb2 = adb.clone();
                            let s2 = serial_touch.clone();
                            tokio::task::spawn_blocking(move || {
                                match event {
                                    TouchEvent::Tap { x, y } => { let _ = adb2.tap(&s2, x, y); }
                                    TouchEvent::Swipe { x1, y1, x2, y2, duration } => {
                                        let _ = adb2.swipe(&s2, x1, y1, x2, y2, duration);
                                    }
                                    TouchEvent::Scroll { x, y, delta_y } => {
                                        let _ = adb2.scroll(&s2, x, y, delta_y);
                                    }
                                    TouchEvent::Key { code } => { let _ = adb2.keyevent(&s2, code); }
                                    TouchEvent::Text { text } => { let _ = adb2.input_text(&s2, &text); }
                                    TouchEvent::Home => { let _ = adb2.keyevent(&s2, 3); }
                                    TouchEvent::Back => { let _ = adb2.keyevent(&s2, 4); }
                                    TouchEvent::Recents => { let _ = adb2.recents(&s2); }
                                    TouchEvent::Wake => { let _ = adb2.wake_up(&s2); }
                                    TouchEvent::Power => { let _ = adb2.power_toggle(&s2); }
                                    TouchEvent::Unlock => { let _ = adb2.unlock(&s2); }
                                    TouchEvent::VolumeUp => { let _ = adb2.volume_up(&s2); }
                                    TouchEvent::VolumeDown => { let _ = adb2.volume_down(&s2); }
                                    TouchEvent::Launch { package } => {
                                        let pkg = package.as_deref().unwrap_or("com.ss.android.ugc.trill");
                                        let _ = adb2.launch_app(&s2, pkg);
                                    }
                                    TouchEvent::Down { x, y } => { let _ = adb2.tap(&s2, x, y); }
                                    TouchEvent::Move { .. } => {}
                                    TouchEvent::Up { .. } => {}
                                }
                            });
                        }
                    }
                    Message::Close(_) => break,
                    _ => {}
                }
            }
        });

        tokio::select! {
            _ = send_task => {},
            _ = recv_task => {},
        }
    }
}
