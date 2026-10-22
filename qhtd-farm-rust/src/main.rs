mod adb_manager;
mod api;
pub mod ai_video_engine;
pub mod browser_nurture;
pub mod cdp_browser;
pub mod farm_container;
mod stream_manager;
mod tiktok_nurture;
pub mod device_profile;
pub mod xml_login;
pub mod telegram_notifier;
mod fast_touch;
mod gui;
pub mod captcha_solver;

use adb_manager::AdbManager;
use api::{create_router, AppState};
use browser_nurture::BrowserNurtureEngine;
use stream_manager::StreamManager;
use tiktok_nurture::TikTokNurtureEngine;

use std::net::SocketAddr;
use std::sync::Arc;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

fn main() {
    std::panic::set_hook(Box::new(|info| {
        let backtrace = std::backtrace::Backtrace::capture();
        let payload = if let Some(s) = info.payload().downcast_ref::<&str>() {
            s.to_string()
        } else if let Some(s) = info.payload().downcast_ref::<String>() {
            s.clone()
        } else {
            "Unknown panic payload".to_string()
        };
        let location = info.location().map(|l| format!("{}:{}:{}", l.file(), l.line(), l.column())).unwrap_or_default();
        let msg = format!("[FATAL ERROR] Panic occurred: {} at {}\nBacktrace:\n{:?}\n", payload, location, backtrace);
        eprintln!("{}", msg);
        let _ = std::fs::write("panic.log", &msg);
    }));

    let _ = tracing_subscriber::registry()
        .with(
            tracing_subscriber::EnvFilter::try_from_default_env()
                .unwrap_or_else(|_| "qhtd_farm_core=info".into()),
        )
        .with(tracing_subscriber::fmt::layer())
        .try_init();

    eprintln!("🚀 QHTD AUTOMATION — 100% Pure Native Rust Desktop Engine");

    // 0. Đảm bảo Single Instance: Tự động dọn dẹp các tiến trình cũ đang chiếm cổng 9090
    let current_pid = std::process::id();
    let _ = std::process::Command::new("powershell")
        .args(&[
            "-NoProfile",
            "-Command",
            &format!(
                "Get-Process -Name 'MunAutomation', 'QHTD_Automation_Rust', 'qhtd-farm-core' -ErrorAction SilentlyContinue | Where-Object {{ $_.Id -ne {} }} | Stop-Process -Force -ErrorAction SilentlyContinue",
                current_pid
            ),
        ])
        .output();

    let port = 9090;
    let addr = SocketAddr::from(([127, 0, 0, 1], port));

    // 1. Cách ly thư mục dữ liệu WebView2 để tránh xung đột khoá file (0x800700AA)
    let temp_data_dir = std::env::temp_dir().join(format!("MunAutomation_WV_{}", current_pid));
    let _ = std::fs::create_dir_all(&temp_data_dir);
    std::env::set_var("WEBVIEW2_USER_DATA_FOLDER", &temp_data_dir);

    let (ready_tx, ready_rx) = std::sync::mpsc::channel();

    // 2. Khởi chạy Axum Server trong background runtime của Rust
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_multi_thread()
            .enable_all()
            .build()
            .expect("Failed to create Tokio runtime");

        rt.block_on(async {
            let mut listener = None;
            for attempt in 1..=30 {
                match tokio::net::TcpListener::bind(addr).await {
                    Ok(l) => {
                        listener = Some(l);
                        break;
                    }
                    Err(e) => {
                        eprintln!("⚠️ [Port 9090] Đang chờ giải phóng socket (lần {}/30: {})...", attempt, e);
                        tokio::time::sleep(tokio::time::Duration::from_millis(300)).await;
                    }
                }
            }

            let listener = match listener {
                Some(l) => l,
                None => {
                    eprintln!("❌ [Rust Core] Lỗi nghiêm trọng: Không thể bind cổng {} sau 30 lần thử!", port);
                    let _ = ready_tx.send(false);
                    return;
                }
            };

            crate::api::sanitize_profiles_on_startup();
            crate::telegram_notifier::start_telegram_polling();

            let adb = Arc::new(AdbManager::new());
            let stream = Arc::new(StreamManager::new(adb.clone()));
            let nurture = Arc::new(TikTokNurtureEngine::new(adb.clone()));
            let browser_nurture = Arc::new(BrowserNurtureEngine::new());
            browser_nurture.clone().start_auto_retry_scheduler();
            let farm_container = Arc::new(crate::farm_container::FarmContainerEngine::new(adb.clone()));

            let app_state = AppState {
                adb: adb.clone(),
                stream: stream.clone(),
                nurture: nurture.clone(),
                browser_nurture: browser_nurture.clone(),
                farm_container: farm_container.clone(),
            };

            let app = create_router(app_state);
            println!("🌐 [Rust Core] Server running at http://127.0.0.1:{}", port);
            let _ = ready_tx.send(true);

            if let Err(e) = axum::serve(listener, app).await {
                eprintln!("❌ [Axum Server] Dừng với lỗi: {:?}", e);
            }
        });
    });

    // Chờ Axum server sẵn sàng trước khi hiển thị giao diện (tối đa 15 giây)
    match ready_rx.recv_timeout(std::time::Duration::from_secs(15)) {
        Ok(true) => (),
        _ => {
            eprintln!("❌ [Rust Core] Server cổng 9090 không thể khởi động, hủy nạp GUI.");
            return;
        }
    }

    // 3. Khởi động Pure Rust Native GUI (Zero Edge, Zero Chromium, Zero WebView)
    let app_url = format!("http://127.0.0.1:{}", port);
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");
    println!("🚀 [Pure Rust Core] Backend Server đã sẵn sàng tại: {}", app_url);
    println!("⚡ Khởi động Desktop GUI thuần Rust — Tiết kiệm tối đa CPU & RAM");
    println!("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━");

    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|arg| arg == "--headless" || arg == "-h") {
        println!("🚀 Chạy chế độ Headless Server Daemon (không mở cửa sổ GUI).");
        loop {
            std::thread::sleep(std::time::Duration::from_secs(3600));
        }
    } else {
        println!("🖥️ [Pure Native Rust GUI] Đang mở cửa sổ ứng dụng Desktop (eframe/egui)...");
        let native_options = eframe::NativeOptions {
            viewport: eframe::egui::ViewportBuilder::default()
                .with_title("MunAutomation — Phone Farm (Pure Rust)")
                .with_inner_size([1500.0, 900.0])
                .with_min_inner_size([960.0, 600.0]),
            ..Default::default()
        };

        if let Err(e) = eframe::run_native(
            "MunAutomation Suite",
            native_options,
            Box::new(move |cc| Ok(Box::new(gui::FarmGuiApp::new(cc, port)))),
        ) {
            eprintln!("❌ Lỗi chạy Native GUI: {:?}", e);
        }
    }
}
