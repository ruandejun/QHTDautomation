mod adb_manager;
mod api;
pub mod cdp_browser;
mod stream_manager;
mod tiktok_nurture;

use adb_manager::AdbManager;
use api::{create_router, AppState};
use stream_manager::StreamManager;
use tiktok_nurture::TikTokNurtureEngine;

use std::net::SocketAddr;
use std::sync::Arc;
use tao::event::{Event, StartCause, WindowEvent};
use tao::event_loop::{ControlFlow, EventLoop};
use tao::window::WindowBuilder;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};
use wry::WebViewBuilder;

#[global_allocator]
static GLOBAL: mimalloc::MiMalloc = mimalloc::MiMalloc;

fn main() {
    std::panic::set_hook(Box::new(|info| {
        let msg = format!("[FATAL ERROR] Panic occurred: {:?}\n", info);
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
            for attempt in 1..=20 {
                match tokio::net::TcpListener::bind(addr).await {
                    Ok(l) => {
                        listener = Some(l);
                        break;
                    }
                    Err(e) => {
                        eprintln!("⚠️ [Port 9090] Đang chờ giải phóng socket (lần {}/20: {})...", attempt, e);
                        tokio::time::sleep(tokio::time::Duration::from_millis(250)).await;
                    }
                }
            }

            let listener = match listener {
                Some(l) => l,
                None => {
                    eprintln!("❌ [Rust Core] Lỗi nghiêm trọng: Không thể bind cổng {} sau 20 lần thử!", port);
                    let _ = ready_tx.send(false);
                    return;
                }
            };

            let adb = Arc::new(AdbManager::new());
            let stream = Arc::new(StreamManager::new(adb.clone()));
            let nurture = Arc::new(TikTokNurtureEngine::new(adb.clone()));

            let app_state = AppState {
                adb: adb.clone(),
                stream: stream.clone(),
                nurture: nurture.clone(),
            };

            let app = create_router(app_state);
            println!("🌐 [Rust Core] Server running at http://127.0.0.1:{}", port);
            let _ = ready_tx.send(true);

            if let Err(e) = axum::serve(listener, app).await {
                eprintln!("❌ [Axum Server] Dừng với lỗi: {:?}", e);
            }
        });
    });

    // Chờ Axum server sẵn sàng trước khi hiển thị giao diện (tối đa 8 giây)
    match ready_rx.recv_timeout(std::time::Duration::from_secs(8)) {
        Ok(true) => (),
        _ => {
            eprintln!("❌ [Rust Core] Server cổng 9090 không thể khởi động, hủy nạp GUI.");
            return;
        }
    }

    // 3. Kiểm tra nếu chạy chế độ --headless (dành cho server / background)
    let args: Vec<String> = std::env::args().collect();
    if args.iter().any(|arg| arg == "--headless" || arg == "-h") {
        println!("🚀 Chạy chế độ Headless Server (không mở cửa sổ GUI). Nhấn Ctrl+C để thoát.");
        loop {
            std::thread::sleep(std::time::Duration::from_secs(3600));
        }
    }

    // 4. Mở Cửa Sổ Ứng Dụng Desktop Native 100% Rust (Zero Python)
    println!("🖥️ [Rust GUI] Đang mở cửa sổ Native Desktop App...");
    let event_loop = EventLoop::new();
    let window = match WindowBuilder::new()
        .with_title("MunAutomation Suite — Android Phone Farm & TikTok Studio (Pure Rust)")
        .with_inner_size(tao::dpi::LogicalSize::new(1460.0, 900.0))
        .with_min_inner_size(tao::dpi::LogicalSize::new(1100.0, 700.0))
        .with_visible(true)
        .with_resizable(true)
        .build(&event_loop)
    {
        Ok(w) => w,
        Err(e) => {
            eprintln!("❌ Lỗi tạo cửa sổ Desktop GUI: {:?}", e);
            return;
        }
    };

    let url = format!("http://127.0.0.1:{}", port);

    let _webview = match WebViewBuilder::new(&window)
        .with_url(&url)
        .with_devtools(true)
        .build()
    {
        Ok(wv) => wv,
        Err(e) => {
            eprintln!("❌ Lỗi tạo WebView2 Desktop GUI: {:?}", e);
            return;
        }
    };

    window.set_visible(true);
    window.set_focus();

    event_loop.run(move |event, _, control_flow| {
        *control_flow = ControlFlow::Wait;
        let _keep_alive_wv = &_webview;
        let _keep_alive_win = &window;

        match event {
            Event::NewEvents(StartCause::Init) => {
                window.set_visible(true);
                window.set_focus();
                println!("✅ Cửa sổ MunAutomation Suite đã hiển thị thành công trên màn hình!");
            }
            Event::WindowEvent {
                event: WindowEvent::CloseRequested,
                ..
            } => {
                println!("👋 Đóng ứng dụng MunAutomation Suite.");
                *control_flow = ControlFlow::Exit;
                std::process::exit(0);
            }
            _ => (),
        }
    });
}
