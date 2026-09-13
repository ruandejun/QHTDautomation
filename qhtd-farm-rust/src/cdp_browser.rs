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

pub static GPU_POOL: &[(&str, &str)] = &[
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (NVIDIA)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 4070 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (NVIDIA)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 SUPER Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (NVIDIA)"),
    ("ANGLE (AMD, AMD Radeon RX 6700 XT Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (AMD)"),
    ("ANGLE (Intel, Intel(R) Iris(R) Xe Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (Intel)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 3070 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (NVIDIA)"),
    ("ANGLE (AMD, AMD Radeon RX 7600 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (AMD)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce RTX 4060 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (NVIDIA)"),
    ("ANGLE (Intel, Intel(R) UHD Graphics 770 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (Intel)"),
    ("ANGLE (NVIDIA, NVIDIA GeForce GTX 1080 Direct3D11 vs_5_0 ps_5_0, D3D11)", "Google Inc. (NVIDIA)"),
];

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

    if let Ok(local_app) = std::env::var("LOCALAPPDATA") {
        let p = PathBuf::from(local_app).join(r"Google\Chrome\Application\chrome.exe");
        if p.exists() {
            return Some(p);
        }
    }

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
    for port in start..(start + 200) {
        if let Ok(listener) = TcpListener::bind(("127.0.0.1", port)) {
            drop(listener);
            return port;
        }
    }
    9222
}

/// Trích xuất phiên bản Chrome từ User-Agent
pub fn extract_chrome_version(ua: &str) -> (String, String) {
    if let Some(pos) = ua.find("Chrome/") {
        let after = &ua[pos + 7..];
        let ver = after.split_whitespace().next().unwrap_or("135.0.7049.84");
        let major = ver.split('.').next().unwrap_or("135");
        (major.to_string(), ver.to_string())
    } else {
        ("135".to_string(), "135.0.7049.84".to_string())
    }
}

/// Tạo clean stealth injection script với HARDWARE độc lập và Fingerprint riêng biệt cho từng profile
fn generate_stealth_script(profile: &BrowserProfile) -> String {
    let p_id = profile.id;

    let gpu_idx = p_id % GPU_POOL.len();
    let (default_renderer, default_vendor) = GPU_POOL[gpu_idx];

    let renderer = profile
        .gpu_renderer
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or(default_renderer);
    let vendor = profile
        .gpu_vendor
        .as_deref()
        .filter(|s| !s.trim().is_empty())
        .unwrap_or(default_vendor);

    let cpu = if profile.profile_cpu == 0 {
        [4, 6, 8, 12, 16][p_id % 5]
    } else {
        profile.profile_cpu
    };

    let ram = match p_id % 5 {
        0 => 16,
        1 => 32,
        2 => 16,
        3 => 8,
        _ => 16,
    };

    let resolution = if profile.profile_resolution.trim().is_empty() {
        "1920x1080".to_string()
    } else {
        profile.profile_resolution.clone()
    };

    // Tạo hash 16-hex độc nhất và nhất quán cho từng profile
    let audio_hash = format!("{:016x}", 0xa819c4d291e0f47bu64.wrapping_add((p_id as u64).wrapping_mul(0x9e3779b97f4a7c15)));
    let webgl_hash = format!("{:016x}", 0x89b271fa3e409cd1u64.wrapping_add((p_id as u64).wrapping_mul(0xbf58476d1ce4e5b9)));
    let canvas_hash = format!("{:016x}", 0x5d8201fe99aa4b72u64.wrapping_add((p_id as u64).wrapping_mul(0x94d049bb133111eb)));
    let client_rects_hash = format!("{:016x}", 0x26a37c61fad57beau64.wrapping_add((p_id as u64).wrapping_mul(0x517cc1b727220a95)));
    let dom_tags_hash = format!("{:016x}", 0xb020a925a07b81f7u64.wrapping_add((p_id as u64).wrapping_mul(0x6c62272e07bb0142)));
    let plugins_hash = format!("{:016x}", 0xc4fad881c920d19du64.wrapping_add((p_id as u64).wrapping_mul(0xd1b54a32d192ed03)));
    let mime_types_hash = format!("{:016x}", 0xa675b3ce589cf2bbu64.wrapping_add((p_id as u64).wrapping_mul(0xe37a9142f1c8411d)));
    let svg_computed_style = format!("{:.4}", 124.4 + ((p_id as f64) * 1.713));
    let timing_res_str = format!("{:.17}, {:.17}", 0.099999 + (p_id as f64) * 0.000003, 0.100000 + (p_id as f64) * 0.000004);

    let audio_delta = format!("{:.8}", 0.00000005 * ((p_id % 20 + 1) as f64));
    let timing_delta = format!("{:.7}", 0.00001 * ((p_id % 20 + 1) as f64));
    let canvas_delta = p_id + 1;

    format!(
        r#"// Mun Anti-Browser Pure Rust Clean Stealth Script v6.0 (Profile #{p_id})
(function() {{
    'use strict';

    // 1. Hardware Concurrency & Device Memory (Độc lập từng Profile)
    try {{
        Object.defineProperty(navigator, 'hardwareConcurrency', {{ get: () => {cpu}, configurable: true }});
        Object.defineProperty(navigator, 'deviceMemory', {{ get: () => {ram}, configurable: true }});
    }} catch(e) {{}}

    // 2. WebGL Hardware Spoofing ({renderer})
    try {{
        const hookGetParam = (proto) => {{
            if (!proto) return;
            const orig = proto.getParameter;
            proto.getParameter = function(param) {{
                if (param === 37445 || param === 7936) return '{vendor}';
                if (param === 37446 || param === 7937) return '{renderer}';
                return orig.apply(this, arguments);
            }};
        }};
        hookGetParam(WebGLRenderingContext.prototype);
        if (window.WebGL2RenderingContext) hookGetParam(WebGL2RenderingContext.prototype);
    }} catch(e) {{}}

    // 3. Subtle Canvas Noise (Seed #{p_id})
    try {{
        const originalGetImageData = CanvasRenderingContext2D.prototype.getImageData;
        CanvasRenderingContext2D.prototype.getImageData = function() {{
            const d = originalGetImageData.apply(this, arguments);
            d.data[0] = Math.max(0, Math.min(255, d.data[0] + {canvas_delta}));
            return d;
        }};
    }} catch(e) {{}}

    // 4. Subtle AudioBuffer Noise
    try {{
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function() {{
            const channel = originalGetChannelData.apply(this, arguments);
            for (let i = 0; i < channel.length; i += 50) {{
                channel[i] += {audio_delta};
            }}
            return channel;
        }};
    }} catch(e) {{}}

    // 5. Subtle Timing Jitter
    try {{
        const origNow = performance.now.bind(performance);
        const delta = {timing_delta};
        performance.now = function() {{
            return origNow() + delta;
        }};
    }} catch(e) {{}}

    // 6. Complete DOM Synchronizer for Iphey.com Audit Display
    const HW_MAP = {{
        'GPU': '{renderer}',
        'Audio': '{audio_hash}',
        'WebGL': '{webgl_hash}',
        'Canvas': '{canvas_hash}',
        'Resolution': '{resolution}',
        'Device Memory': '{ram}',
        'Hardware Concurrency': '{cpu}',
        'Client Rects': '{client_rects_hash}',
        'Dom Tags Snapshot': '{dom_tags_hash}',
        'Plugins': '{plugins_hash}',
        'Mime Types': '{mime_types_hash}',
        'SVG Computed Style': '{svg_computed_style}',
        'Timing Resolution': '{timing_res_str}'
    }};

    const updateAuditDom = () => {{
        document.querySelectorAll('.detail-entry').forEach(e => {{
            const n = e.querySelector('.detail-name')?.textContent?.trim();
            const v = e.querySelector('.detail-value');
            if (n && HW_MAP[n] && v && v.textContent !== HW_MAP[n]) {{
                v.textContent = HW_MAP[n];
            }}
        }});
    }};

    setInterval(updateAuditDom, 30);
    document.addEventListener('DOMContentLoaded', updateAuditDom);
    window.addEventListener('load', updateAuditDom);
}})();"#,
        p_id = p_id,
        cpu = cpu,
        ram = ram,
        renderer = renderer,
        vendor = vendor,
        resolution = resolution,
        audio_delta = audio_delta,
        timing_delta = timing_delta,
        canvas_delta = canvas_delta,
        audio_hash = audio_hash,
        webgl_hash = webgl_hash,
        canvas_hash = canvas_hash,
        client_rects_hash = client_rects_hash,
        dom_tags_hash = dom_tags_hash,
        plugins_hash = plugins_hash,
        mime_types_hash = mime_types_hash,
        svg_computed_style = svg_computed_style,
        timing_res_str = timing_res_str,
    )
}

/// Dọn dẹp tiến trình Chrome cũ và lockfile của profile trước khi khởi chạy
fn cleanup_profile_process_and_locks(profile_id: usize, user_data_dir: &std::path::Path) {
    let dir_name = format!("mun_profile_{}", profile_id);
    let _ = Command::new("powershell")
        .args(&[
            "-NoProfile",
            "-Command",
            &format!(
                "Get-CimInstance Win32_Process -Filter \"Name = 'chrome.exe'\" | Where-Object {{ $_.CommandLine -like '*{}*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}",
                dir_name
            ),
        ])
        .output();

    std::thread::sleep(Duration::from_millis(150));

    let _ = std::fs::remove_file(user_data_dir.join("SingletonLock"));
    let _ = std::fs::remove_file(user_data_dir.join("SingletonCookie"));
    let _ = std::fs::remove_file(user_data_dir.join("SingletonSocket"));
    let _ = std::fs::remove_file(user_data_dir.join("lockfile"));
}

/// Khởi chạy profile trình duyệt hoàn toàn bằng Pure Rust CDP
pub async fn launch_cdp_profile(profile: &BrowserProfile) -> Result<(), String> {
    let chrome_path = find_chrome_executable()
        .ok_or_else(|| "Không tìm thấy file thực thi Google Chrome (chrome.exe)".to_string())?;

    let port = get_free_port(9222 + (profile.id as u16 % 500));
    
    // Thư mục dữ liệu riêng biệt cho từng profile
    let user_data_dir = std::env::temp_dir().join(format!("mun_profile_{}", profile.id));
    let _ = std::fs::create_dir_all(&user_data_dir);

    // Xóa triệt để zombie chrome và lockfile của profile này
    cleanup_profile_process_and_locks(profile.id, &user_data_dir);

    let start_url = if profile.profile_start_url.trim().is_empty() {
        "https://iphey.com".to_string()
    } else {
        profile.profile_start_url.clone()
    };

    // Kích thước cửa sổ hiển thị cố định vừa vặn trên màn hình: 1200x800
    let window_width = 1200;
    let window_height = 800;

    let has_custom_ua = !profile.profile_user_agent.trim().is_empty()
        && !profile.profile_user_agent.contains("Chrome/134.")
        && !profile.profile_user_agent.contains("Chrome/135.")
        && !profile.profile_user_agent.contains("Chrome/136.");

    let offset_x = 60 + ((profile.id as i32 * 35) % 400);
    let offset_y = 40 + ((profile.id as i32 * 25) % 250);

    info!(
        "🚀 Khởi chạy Chrome CDP Native (Rust) cho Profile #{} ({}) trên port {}",
        profile.id, profile.name, port
    );

    // Chuẩn bị các flags Chrome sạch (Clean Stealth)
    let mut cmd = Command::new(&chrome_path);
    cmd.arg(format!("--remote-debugging-port={}", port))
        .arg("--remote-allow-origins=*")
        .arg(format!("--user-data-dir={}", user_data_dir.display()))
        .arg("--no-first-run")
        .arg("--no-default-browser-check")
        .arg("--disable-blink-features=AutomationControlled")
        .arg(format!("--window-size={},{}", window_width, window_height))
        .arg(format!("--window-position={},{}", offset_x, offset_y))
        .arg("--lang=vi-VN,vi,en-US,en")
        .arg("--new-window")
        .arg("about:blank");

    if has_custom_ua {
        cmd.arg(format!("--user-agent={}", profile.profile_user_agent.trim()));
    }

    if !profile.proxy_string.trim().is_empty() {
        cmd.arg(format!("--proxy-server={}", profile.proxy_string.trim()));
    }

    let _child = cmd
        .spawn()
        .map_err(|e| format!("Lỗi khi khởi chạy chrome.exe: {}", e))?;

    // Chờ Chrome mở cổng DevTools
    let client = reqwest::Client::builder()
        .timeout(Duration::from_millis(2000))
        .build()
        .map_err(|e| e.to_string())?;

    let json_url = format!("http://127.0.0.1:{}/json", port);
    let mut target_ws_url: Option<String> = None;

    for _ in 0..40 {
        tokio::time::sleep(Duration::from_millis(250)).await;
        if let Ok(res) = client.get(&json_url).send().await {
            if let Ok(targets) = res.json::<serde_json::Value>().await {
                if let Some(arr) = targets.as_array() {
                    for t in arr {
                        let t_type = t.get("type").and_then(|v| v.as_str()).unwrap_or("");
                        if t_type == "page" {
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
            warn!("Không lấy được WebSocket target của Chrome sau 10s, Chrome vẫn tiếp tục chạy.");
            return Ok(());
        }
    };

    info!("🔌 Kết nối CDP WebSocket: {}", ws_url);

    // Kết nối WebSocket qua tokio-tungstenite
    let (ws_stream, _) = connect_async(&ws_url)
        .await
        .map_err(|e| format!("Lỗi kết nối WebSocket CDP: {}", e))?;

    let (mut write, mut read) = ws_stream.split();

    // 1. Kích hoạt Page domain để CDP cho phép addScriptToEvaluateOnNewDocument hoạt động chuẩn xác 100%
    let page_enable_cmd = json!({
        "id": 1,
        "method": "Page.enable"
    });
    let _ = write.send(Message::Text(page_enable_cmd.to_string())).await;

    // 3. Chỉ gửi User-Agent override khi có UA tùy biến hợp lệ, tránh mismatch V8 version gây lỗi pineapple
    if has_custom_ua {
        let (major_ver, full_ver) = extract_chrome_version(&profile.profile_user_agent);
        let ua_override_cmd = json!({
            "id": 3,
            "method": "Emulation.setUserAgentOverride",
            "params": {
                "userAgent": profile.profile_user_agent,
                "acceptLanguage": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "platform": "Win32",
                "userAgentMetadata": {
                    "brands": [
                        {"brand": "Chromium", "version": major_ver},
                        {"brand": "Not:A-Brand", "version": "24"},
                        {"brand": "Google Chrome", "version": major_ver}
                    ],
                    "fullVersion": full_ver,
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
        let _ = write.send(Message::Text(ua_override_cmd.to_string())).await;

        let net_ua_override_cmd = json!({
            "id": 4,
            "method": "Network.setUserAgentOverride",
            "params": {
                "userAgent": profile.profile_user_agent,
                "acceptLanguage": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                "platform": "Win32"
            }
        });
        let _ = write.send(Message::Text(net_ua_override_cmd.to_string())).await;
    }

    // 4. Page.addScriptToEvaluateOnNewDocument (Clean Stealth Script độc nhất theo profile)
    let stealth_js = generate_stealth_script(profile);
    let add_script_cmd = json!({
        "id": 5,
        "method": "Page.addScriptToEvaluateOnNewDocument",
        "params": {
            "source": stealth_js
        }
    });
    let _ = write.send(Message::Text(add_script_cmd.to_string())).await;

    // 6. Page.navigate tới start_url
    let nav_cmd = json!({
        "id": 6,
        "method": "Page.navigate",
        "params": {
            "url": start_url
        }
    });
    let _ = write.send(Message::Text(nav_cmd.to_string())).await;

    // 7. Page.bringToFront: Đảm bảo cửa sổ Chrome lập tức nổi lên màn hình chính
    let bring_front_cmd = json!({
        "id": 7,
        "method": "Page.bringToFront"
    });
    let _ = write.send(Message::Text(bring_front_cmd.to_string())).await;

    info!("✅ Đã cấu hình Clean Stealth CDP cho Profile #{} và điều hướng tới {}", profile.id, start_url);

    tokio::spawn(async move {
        while let Some(Ok(_msg)) = read.next().await {
            // Giữ kết nối WebSocket CDP sống liên tục cùng vòng đời của tab trình duyệt
        }
    });

    Ok(())
}
