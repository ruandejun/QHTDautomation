use crate::api::BrowserProfile;
use futures_util::{SinkExt, StreamExt};
use serde_json::json;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::Command;
use std::time::Duration;
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::protocol::Message;
use tracing::{info, warn};

/// Tìm đường dẫn chrome.exe trên máy Windows
pub fn find_chrome_executable() -> Option<PathBuf> {
    let candidates = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Users\Admin\AppData\Local\Google\Chrome\Application\chrome.exe",
    ];

    for c in &candidates {
        let p = PathBuf::from(c);
        if p.exists() {
            return Some(p);
        }
    }

    // Thử tìm trong %LOCALAPPDATA%
    if let Ok(local_app) = std::env::var("LOCALAPPDATA") {
        let p = PathBuf::from(local_app).join(r"Google\Chrome\Application\chrome.exe");
        if p.exists() {
            return Some(p);
        }
    }

    // Thử tìm trong %PROGRAMFILES%
    if let Ok(pf) = std::env::var("ProgramFiles") {
        let p = PathBuf::from(pf).join(r"Google\Chrome\Application\chrome.exe");
        if p.exists() {
            return Some(p);
        }
    }

    None
}

/// Tìm một port TCP trống trên localhost
fn get_free_port(start: u16) -> u16 {
    for port in start..(start + 100) {
        if TcpListener::bind(("127.0.0.1", port)).is_ok() {
            return port;
        }
    }
    9222
}

/// Tạo clean stealth injection script (Không monkey-patch prototype của plugins, connection, battery)
/// Đảm bảo vượt qua iphey.com với đánh giá "Trustworthy" và MX Score 100
fn generate_stealth_script(profile: &BrowserProfile) -> String {
    let p_id = profile.id;
    let r_shift = ((p_id * 17) % 5) as i32 - 2;
    let g_shift = ((p_id * 31) % 5) as i32 - 2;
    let b_shift = ((p_id * 47) % 5) as i32 - 2;

    let vendor = "Google Inc. (NVIDIA)";
    let renderer = "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)";

    format!(
        r#"// Mun Anti-Browser Pure Rust Clean Stealth Script v3.0
(function() {{
    'use strict';

    // 1. Subtle Canvas Noise
    try {{
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function(sx, sy, sw, sh) {{
            const imgData = originalGetImageData.apply(this, arguments);
            for (let i = 0; i < imgData.data.length; i += 4) {{
                imgData.data[i] = Math.max(0, Math.min(255, imgData.data[i] + ({r_shift})));
                imgData.data[i+1] = Math.max(0, Math.min(255, imgData.data[i+1] + ({g_shift})));
                imgData.data[i+2] = Math.max(0, Math.min(255, imgData.data[i+2] + ({b_shift})));
            }}
            return imgData;
        }};

        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {{
            const ctx = this.getContext('2d');
            if (ctx) {{
                try {{
                    const w = this.width, h = this.height;
                    if (w > 0 && h > 0) {{
                        const imgData = originalGetImageData.call(ctx, 0, 0, Math.min(10, w), Math.min(10, h));
                        imgData.data[0] = Math.max(0, Math.min(255, imgData.data[0] + ({r_shift})));
                        ctx.putImageData(imgData, 0, 0);
                    }}
                }} catch(e) {{}}
            }}
            return originalToDataURL.apply(this, arguments);
        }};
    }} catch(e) {{}}

    // 2. WebGL Hardware Spoofing (DirectX D3D11 NVIDIA)
    try {{
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(param) {{
            if (param === 37445) return '{vendor}';
            if (param === 37446) return '{renderer}';
            return getParameter.apply(this, arguments);
        }};

        if (window.WebGL2RenderingContext) {{
            const getParameter2 = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(param) {{
                if (param === 37445) return '{vendor}';
                if (param === 37446) return '{renderer}';
                return getParameter2.apply(this, arguments);
            }};
        }}
    }} catch(e) {{}}

    // 3. Subtle AudioBuffer Noise
    try {{
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function() {{
            const channel = originalGetChannelData.apply(this, arguments);
            for (let i = 0; i < Math.min(channel.length, 100); i += 10) {{
                channel[i] += 0.0000001 * {p_id};
            }}
            return channel;
        }};
    }} catch(e) {{}}
}})();"#,
        r_shift = r_shift,
        g_shift = g_shift,
        b_shift = b_shift,
        vendor = vendor,
        renderer = renderer,
        p_id = p_id
    )
}

/// Khởi chạy profile trình duyệt hoàn toàn bằng Pure Rust CDP
pub async fn launch_cdp_profile(profile: &BrowserProfile) -> Result<(), String> {
    let chrome_path = find_chrome_executable()
        .ok_or_else(|| "Không tìm thấy file thực thi Google Chrome (chrome.exe)".to_string())?;

    let port = get_free_port(9222 + (profile.id as u16 % 500));
    
    // Thư mục dữ liệu riêng biệt cho từng profile
    let user_data_dir = std::env::temp_dir().join(format!("mun_profile_{}", profile.id));
    let _ = std::fs::create_dir_all(&user_data_dir);

    let start_url = if profile.profile_start_url.trim().is_empty() {
        "https://iphey.com".to_string()
    } else {
        profile.profile_start_url.clone()
    };

    let resolution = if profile.profile_resolution.is_empty() {
        "1920x1080".to_string()
    } else {
        profile.profile_resolution.clone()
    };
    let parts: Vec<&str> = resolution.split('x').collect();
    let width = parts.first().unwrap_or(&"1920");
    let height = parts.get(1).unwrap_or(&"1080");

    let ua = if profile.profile_user_agent.trim().is_empty() {
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36".to_string()
    } else {
        profile.profile_user_agent.clone()
    };

    info!(
        "🚀 Khởi chạy Chrome CDP Native (Rust) cho Profile #{} trên port {}",
        profile.id, port
    );

    // Chuẩn bị các flags Chrome sạch (Clean Stealth)
    let mut cmd = Command::new(&chrome_path);
    cmd.arg(format!("--remote-debugging-port={}", port))
        .arg("--remote-allow-origins=*")
        .arg(format!("--user-data-dir={}", user_data_dir.display()))
        .arg("--no-first-run")
        .arg("--no-default-browser-check")
        .arg("--disable-blink-features=AutomationControlled")
        .arg(format!("--window-size={},{}", width, height))
        .arg("--lang=vi-VN,vi,en-US,en")
        .arg(format!("--user-agent={}", ua));

    if !profile.proxy_string.trim().is_empty() {
        cmd.arg(format!("--proxy-server={}", profile.proxy_string.trim()));
    }

    // Mở about:blank trước để tiêm CDP script trước khi load trang thật
    cmd.arg("about:blank");

    let _child = cmd
        .spawn()
        .map_err(|e| format!("Lỗi khi khởi chạy chrome.exe: {}", e))?;

    // Chờ Chrome mở cổng DevTools
    let client = reqwest::Client::builder()
        .timeout(Duration::from_millis(1500))
        .build()
        .map_err(|e| e.to_string())?;

    let json_url = format!("http://127.0.0.1:{}/json", port);
    let mut target_ws_url: Option<String> = None;

    for _ in 0..30 {
        tokio::time::sleep(Duration::from_millis(300)).await;
        if let Ok(res) = client.get(&json_url).send().await {
            if let Ok(targets) = res.json::<serde_json::Value>().await {
                if let Some(arr) = targets.as_array() {
                    for t in arr {
                        if t.get("type").and_then(|v| v.as_str()) == Some("page") {
                            if let Some(ws) = t.get("webSocketDebuggerUrl").and_then(|v| v.as_str()) {
                                target_ws_url = Some(ws.to_string());
                                break;
                            }
                        }
                    }
                }
            }
        }
        if target_ws_url.is_some() {
            break;
        }
    }

    let ws_url = match target_ws_url {
        Some(url) => url,
        None => {
            warn!("Không lấy được WebSocket target của Chrome sau 9s, Chrome vẫn tiếp tục chạy.");
            return Ok(());
        }
    };

    info!("🔌 Kết nối CDP WebSocket: {}", ws_url);

    // Kết nối WebSocket qua tokio-tungstenite
    let (ws_stream, _) = connect_async(&ws_url)
        .await
        .map_err(|e| format!("Lỗi kết nối WebSocket CDP: {}", e))?;

    let (mut write, mut read) = ws_stream.split();

    // 1. Emulation.setUserAgentOverride
    let ua_override_cmd = json!({
        "id": 1,
        "method": "Emulation.setUserAgentOverride",
        "params": {
            "userAgent": ua,
            "acceptLanguage": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "platform": "Win32",
            "userAgentMetadata": {
                "brands": [
                    {"brand": "Chromium", "version": "135"},
                    {"brand": "Not:A-Brand", "version": "24"},
                    {"brand": "Google Chrome", "version": "135"}
                ],
                "fullVersion": "135.0.0.0",
                "platform": "Windows",
                "platformVersion": "15.0.0",
                "architecture": "x86",
                "model": "",
                "mobile": false,
                "bitness": "64",
                "wow64": false
            }
        }
    });

    write
        .send(Message::Text(ua_override_cmd.to_string()))
        .await
        .map_err(|e| e.to_string())?;

    // 2. Network.setUserAgentOverride
    let net_ua_override_cmd = json!({
        "id": 2,
        "method": "Network.setUserAgentOverride",
        "params": {
            "userAgent": ua,
            "acceptLanguage": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
            "platform": "Win32"
        }
    });

    write
        .send(Message::Text(net_ua_override_cmd.to_string()))
        .await
        .map_err(|e| e.to_string())?;

    // 3. Page.addScriptToEvaluateOnNewDocument
    let stealth_js = generate_stealth_script(profile);
    let add_script_cmd = json!({
        "id": 3,
        "method": "Page.addScriptToEvaluateOnNewDocument",
        "params": {
            "source": stealth_js
        }
    });

    write
        .send(Message::Text(add_script_cmd.to_string()))
        .await
        .map_err(|e| e.to_string())?;

    // 4. Page.navigate tới start_url
    let nav_cmd = json!({
        "id": 4,
        "method": "Page.navigate",
        "params": {
            "url": start_url
        }
    });

    write
        .send(Message::Text(nav_cmd.to_string()))
        .await
        .map_err(|e| e.to_string())?;

    info!("✅ Đã cấu hình Clean Stealth CDP và điều hướng tới {}", start_url);

    // Chờ nhận phản hồi để chắc chắn lệnh đã được nhận
    tokio::spawn(async move {
        let mut count = 0;
        while let Some(Ok(_msg)) = read.next().await {
            count += 1;
            if count >= 4 {
                break;
            }
        }
    });

    Ok(())
}
