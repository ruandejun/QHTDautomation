use crate::api::BrowserProfile;
use futures_util::{SinkExt, StreamExt};
use serde::{Deserialize, Serialize};
use serde_json::json;
use std::collections::HashSet;
use std::net::TcpListener;
use std::path::PathBuf;
use std::process::Command;
use std::sync::OnceLock;
use std::time::Duration;
use parking_lot::RwLock;
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::protocol::Message;
use tracing::{info, warn};

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ParsedProxy {
    pub scheme: String, // "socks5", "http", "https"
    pub host: String,
    pub port: u16,
    pub username: Option<String>,
    pub password: Option<String>,
}

impl ParsedProxy {
    pub fn server_arg(&self) -> String {
        format!("{}://{}:{}", self.scheme, self.host, self.port)
    }

    pub fn to_proxy_string(&self) -> String {
        match (&self.username, &self.password) {
            (Some(u), Some(p)) if !u.is_empty() => {
                format!("{}://{}:{}@{}:{}", self.scheme, u, p, self.host, self.port)
            }
            _ => format!("{}://{}:{}", self.scheme, self.host, self.port),
        }
    }
}

pub fn parse_proxy_string(raw: &str) -> Option<ParsedProxy> {
    let s = raw.trim();
    if s.is_empty() {
        return None;
    }

    // Trường hợp 1: Có scheme (socks5:// hoặc http:// hoặc https://)
    if let Some(pos) = s.find("://") {
        let scheme = s[..pos].to_lowercase();
        let rest = &s[pos + 3..];
        if let Some(at_pos) = rest.find('@') {
            let auth = &rest[..at_pos];
            let host_port = &rest[at_pos + 1..];
            let (user, pass) = if let Some(c_pos) = auth.find(':') {
                (Some(auth[..c_pos].to_string()), Some(auth[c_pos + 1..].to_string()))
            } else {
                (Some(auth.to_string()), None)
            };
            let (host, port) = parse_host_port(host_port)?;
            return Some(ParsedProxy { scheme, host, port, username: user, password: pass });
        } else {
            let (host, port) = parse_host_port(rest)?;
            return Some(ParsedProxy { scheme, host, port, username: None, password: None });
        }
    }

    // Trường hợp 2: Định dạng host:port:user:pass (rất phổ biến)
    let parts: Vec<&str> = s.split(':').collect();
    if parts.len() == 4 {
        let host = parts[0].to_string();
        let port = parts[1].parse::<u16>().ok()?;
        let user = parts[2].to_string();
        let pass = parts[3].to_string();
        return Some(ParsedProxy {
            scheme: "socks5".into(),
            host,
            port,
            username: Some(user),
            password: Some(pass),
        });
    }

    // Trường hợp 3: user:pass@host:port (không có scheme)
    if let Some(at_pos) = s.find('@') {
        let auth = &s[..at_pos];
        let host_port = &s[at_pos + 1..];
        let (user, pass) = if let Some(c_pos) = auth.find(':') {
            (Some(auth[..c_pos].to_string()), Some(auth[c_pos + 1..].to_string()))
        } else {
            (Some(auth.to_string()), None)
        };
        let (host, port) = parse_host_port(host_port)?;
        return Some(ParsedProxy { scheme: "socks5".into(), host, port, username: user, password: pass });
    }

    // Trường hợp 4: host:port
    if parts.len() == 2 {
        let host = parts[0].to_string();
        let port = parts[1].parse::<u16>().ok()?;
        return Some(ParsedProxy { scheme: "socks5".into(), host, port, username: None, password: None });
    }

    None
}

fn parse_host_port(hp: &str) -> Option<(String, u16)> {
    let clean = hp.trim_matches('/').trim();
    let parts: Vec<&str> = clean.split(':').collect();
    if parts.len() == 2 {
        let host = parts[0].to_string();
        let port = parts[1].parse::<u16>().ok()?;
        Some((host, port))
    } else {
        None
    }
}


static ACTIVE_PROFILES: OnceLock<RwLock<HashSet<usize>>> = OnceLock::new();

pub fn active_profiles() -> &'static RwLock<HashSet<usize>> {
    ACTIVE_PROFILES.get_or_init(|| RwLock::new(HashSet::new()))
}

pub fn is_profile_active(id: usize) -> bool {
    active_profiles().read().contains(&id)
}

pub fn get_active_profile_ids() -> Vec<usize> {
    active_profiles().read().iter().copied().collect()
}

pub fn mark_profile_active(id: usize) {
    active_profiles().write().insert(id);
}

pub fn mark_profile_inactive(id: usize) {
    active_profiles().write().remove(&id);
}

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

/// Tìm đường dẫn Custom Anti-Detect Chromium (qhtd-browser.exe)
pub fn find_custom_chromium() -> Option<PathBuf> {
    let current_dir = std::env::current_exe().ok().and_then(|p| p.parent().map(|d| d.to_path_buf()));
    if let Some(ref d) = current_dir {
        let custom_candidates = [
            d.join("qhtd-browser").join("qhtd-browser.exe"),
            d.join("qhtd-browser").join("chrome.exe"),
            d.join("qhtd-browser.exe"),
            d.join("bin").join("qhtd-browser.exe"),
            PathBuf::from(r"D:\Workspace\Python\QHTDautomation\qhtd-browser\qhtd-browser.exe"),
            PathBuf::from(r"D:\Workspace\Python\QHTDautomation\qhtd-browser\chrome.exe"),
        ];
        for c in &custom_candidates {
            if c.exists() {
                return Some(c.clone());
            }
        }
    }
    None
}

/// Tìm đường dẫn Google Chrome chuẩn của hệ thống
pub fn find_system_chrome() -> Option<PathBuf> {
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

/// Tìm executable dựa trên engine_mode của Profile
pub fn find_executable_for_engine(engine_mode: &str) -> (Option<PathBuf>, &'static str) {
    match engine_mode {
        "native" => {
            if let Some(custom) = find_custom_chromium() {
                (Some(custom), "Native C++ Core (qhtd-browser)")
            } else {
                warn!("⚠️ Chưa tải Custom Chromium, tự động fallback về System Chrome với JS Stealth!");
                (find_system_chrome(), "System Chrome (Fallback to JS Stealth)")
            }
        }
        "js_stealth" => {
            (find_system_chrome(), "Standard Google Chrome (JS CDP Stealth)")
        }
        _ => {
            // "hybrid" hoặc mặc định: Ưu tiên Custom nếu có, nếu không thì dùng Chrome thường
            if let Some(custom) = find_custom_chromium() {
                (Some(custom), "Hybrid (Native C++ Core + CDP Shield)")
            } else {
                (find_system_chrome(), "Standard Google Chrome (JS CDP Stealth)")
            }
        }
    }
}

/// Tìm một port TCP trống trên localhost
pub fn get_free_port(start: u16) -> u16 {
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

    let ram = if profile.profile_ram == 0 {
        match p_id % 5 {
            0 => 16,
            1 => 32,
            2 => 16,
            3 => 8,
            _ => 16,
        }
    } else {
        profile.profile_ram
    };

    let resolution = if profile.profile_resolution.trim().is_empty() {
        "1920x1080".to_string()
    } else {
        profile.profile_resolution.clone()
    };

    let canvas_seed_val = profile.canvas_seed.unwrap_or((p_id as u32).wrapping_mul(1664525) ^ 0x5a5a5a5a) as u64;
    let audio_seed_val = profile.audio_seed.unwrap_or((p_id as u32).wrapping_mul(1103515245) ^ 0xa5a5a5a5) as u64;

    // Tạo hash 16-hex độc nhất và nhất quán cho từng profile
    let audio_hash = format!("{:016x}", 0xa819c4d291e0f47bu64.wrapping_add(audio_seed_val.wrapping_mul(0x9e3779b97f4a7c15)));
    let webgl_hash = format!("{:016x}", 0x89b271fa3e409cd1u64.wrapping_add((p_id as u64).wrapping_mul(0xbf58476d1ce4e5b9)));
    let canvas_hash = format!("{:016x}", 0x5d8201fe99aa4b72u64.wrapping_add(canvas_seed_val.wrapping_mul(0x94d049bb133111eb)));
    let client_rects_hash = format!("{:016x}", 0x26a37c61fad57beau64.wrapping_add((p_id as u64).wrapping_mul(0x517cc1b727220a95)));
    let dom_tags_hash = format!("{:016x}", 0xb020a925a07b81f7u64.wrapping_add((p_id as u64).wrapping_mul(0x6c62272e07bb0142)));
    let plugins_hash = format!("{:016x}", 0xc4fad881c920d19du64.wrapping_add((p_id as u64).wrapping_mul(0xd1b54a32d192ed03)));
    let mime_types_hash = format!("{:016x}", 0xa675b3ce589cf2bbu64.wrapping_add((p_id as u64).wrapping_mul(0xe37a9142f1c8411d)));
    let svg_computed_style = format!("{:.4}", 124.4 + ((p_id as f64) * 1.713));
    let timing_res_str = format!("{:.17}, {:.17}", 0.099999 + (p_id as f64) * 0.000003, 0.100000 + (p_id as f64) * 0.000004);

    let audio_delta = format!("{:.8}", 0.00000005 * ((audio_seed_val % 20 + 1) as f64));
    let timing_delta = format!("{:.7}", 0.00001 * ((p_id % 20 + 1) as f64));
    let canvas_delta = ((canvas_seed_val % 3) as usize) + 1;

    let is_mobile = profile.profile_os.eq_ignore_ascii_case("Android")
        || profile.profile_os.eq_ignore_ascii_case("iOS")
        || profile.profile_user_agent.contains("Mobile")
        || profile.profile_user_agent.contains("Android")
        || profile.profile_user_agent.contains("iPhone");

    let platform = if profile.profile_os.eq_ignore_ascii_case("iOS") || profile.profile_user_agent.contains("iPhone") {
        "iPhone"
    } else if is_mobile {
        "Linux armv81"
    } else {
        "Win32"
    };

    let touch_points = if is_mobile { 5 } else { 0 };

    format!(
        r#"// Mun Anti-Browser Pure Rust Clean Stealth Script v6.0 (Profile #{p_id})
(function() {{
    'use strict';

    function patchTargetWindow(w) {{
        if (!w) return;
        try {{
            if (w.__MUN_STEALTH_APPLIED__) return;
            w.__MUN_STEALTH_APPLIED__ = true;
        }} catch(e) {{}}

        // 1. Hardware Concurrency & Device Memory (Độc lập từng Profile)
        try {{
            Object.defineProperty(w.navigator, 'hardwareConcurrency', {{ get: () => {cpu}, configurable: true }});
            Object.defineProperty(w.navigator, 'deviceMemory', {{ get: () => {ram}, configurable: true }});
            Object.defineProperty(w.navigator, 'webdriver', {{ get: () => false, configurable: true }});
            Object.defineProperty(w.navigator, 'maxTouchPoints', {{ get: () => {touch_points}, configurable: true }});
            Object.defineProperty(w.navigator, 'platform', {{ get: () => '{platform}', configurable: true }});
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
            if (w.WebGLRenderingContext) hookGetParam(w.WebGLRenderingContext.prototype);
            if (w.WebGL2RenderingContext) hookGetParam(w.WebGL2RenderingContext.prototype);
        }} catch(e) {{}}

        // 3. Subtle Canvas Noise (Seed #{p_id})
        try {{
            if (w.CanvasRenderingContext2D) {{
                const originalGetImageData = w.CanvasRenderingContext2D.prototype.getImageData;
                w.CanvasRenderingContext2D.prototype.getImageData = function() {{
                    const d = originalGetImageData.apply(this, arguments);
                    d.data[0] = Math.max(0, Math.min(255, d.data[0] + {canvas_delta}));
                    return d;
                }};
            }}
        }} catch(e) {{}}

        // 4. Subtle AudioBuffer Noise
        try {{
            if (w.AudioBuffer) {{
                const originalGetChannelData = w.AudioBuffer.prototype.getChannelData;
                w.AudioBuffer.prototype.getChannelData = function() {{
                    const channel = originalGetChannelData.apply(this, arguments);
                    for (let i = 0; i < channel.length; i += 50) {{
                        channel[i] += {audio_delta};
                    }}
                    return channel;
                }};
            }}
        }} catch(e) {{}}

        // 5. Subtle Timing Jitter
        try {{
            if (w.performance && w.performance.now) {{
                const origNow = w.performance.now.bind(w.performance);
                const delta = {timing_delta};
                w.performance.now = function() {{
                    return origNow() + delta;
                }};
            }}
        }} catch(e) {{}}
    }}

    // Áp dụng bảo vệ ngay lập tức cho window chính
    patchTargetWindow(window);

    // 6. Deep Iframe Shield: Hook toàn diện HTMLIFrameElement & DOM insertion
    try {{
        const origContentWindowDesc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentWindow');
        if (origContentWindowDesc && origContentWindowDesc.get) {{
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {{
                get: function() {{
                    const win = origContentWindowDesc.get.apply(this);
                    if (win) patchTargetWindow(win);
                    return win;
                }},
                configurable: true
            }});
        }}

        const origContentDocDesc = Object.getOwnPropertyDescriptor(HTMLIFrameElement.prototype, 'contentDocument');
        if (origContentDocDesc && origContentDocDesc.get) {{
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentDocument', {{
                get: function() {{
                    const doc = origContentDocDesc.get.apply(this);
                    if (doc && doc.defaultView) patchTargetWindow(doc.defaultView);
                    return doc;
                }},
                configurable: true
            }});
        }}

        const origAppend = Node.prototype.appendChild;
        Node.prototype.appendChild = function(child) {{
            const res = origAppend.apply(this, arguments);
            if (child && child.tagName === 'IFRAME') {{
                try {{ if (child.contentWindow) patchTargetWindow(child.contentWindow); }} catch(e) {{}}
            }}
            return res;
        }};

        const origInsert = Node.prototype.insertBefore;
        Node.prototype.insertBefore = function(child, ref) {{
            const res = origInsert.apply(this, arguments);
            if (child && child.tagName === 'IFRAME') {{
                try {{ if (child.contentWindow) patchTargetWindow(child.contentWindow); }} catch(e) {{}}
            }}
            return res;
        }};
    }} catch(e) {{}}

    // 7. Complete DOM Synchronizer for Iphey.com Audit Display
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

/// Dừng profile Chrome đang chạy và xóa trạng thái
pub fn stop_cdp_profile(profile_id: usize) {
    info!("🛑 Dừng tiến trình Chrome của Profile #{}", profile_id);
    let user_data_dir = std::env::temp_dir().join(format!("mun_profile_{}", profile_id));
    cleanup_profile_process_and_locks(profile_id, &user_data_dir);
    mark_profile_inactive(profile_id);
}

/// Khởi chạy profile trình duyệt hoàn toàn bằng Pure Rust CDP
pub async fn launch_cdp_profile(profile: &BrowserProfile) -> Result<(), String> {
    let mode = profile.engine_mode.as_deref().unwrap_or("native");
    let (exec_path_opt, engine_label) = find_executable_for_engine(mode);
    let chrome_path = exec_path_opt
        .ok_or_else(|| "Không tìm thấy file thực thi trình duyệt (chrome.exe hoặc qhtd-browser.exe)".to_string())?;

    let _is_native_engine = engine_label.contains("Native C++");
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

    let is_mobile = profile.profile_os.eq_ignore_ascii_case("Android")
        || profile.profile_os.eq_ignore_ascii_case("iOS")
        || profile.profile_user_agent.contains("Mobile")
        || profile.profile_user_agent.contains("Android")
        || profile.profile_user_agent.contains("iPhone");

    let (screen_w, screen_h) = if let Some((w_s, h_s)) = profile.profile_resolution.split_once('x') {
        (w_s.trim().parse::<i64>().unwrap_or(390), h_s.trim().parse::<i64>().unwrap_or(844))
    } else if is_mobile {
        (390, 844)
    } else {
        (1920, 1080)
    };

    // Kích thước cửa sổ hiển thị trên màn hình:
    // Nếu là profile phone/mobile -> hiển thị khung cửa sổ điện thoại gọn gàng 440x920
    // Nếu là desktop -> 1200x800
    let (window_width, window_height) = if is_mobile {
        (440, 920)
    } else {
        (1200, 800)
    };

    let has_custom_ua = !profile.profile_user_agent.trim().is_empty()
        && !profile.profile_user_agent.contains("Chrome/134.")
        && !profile.profile_user_agent.contains("Chrome/135.")
        && !profile.profile_user_agent.contains("Chrome/136.");

    let offset_x = 60 + ((profile.id as i32 * 35) % 400);
    let offset_y = 40 + ((profile.id as i32 * 25) % 250);

    info!(
        "🚀 Khởi chạy trình duyệt cho Profile #{} ({}) [{}] trên port {}",
        profile.id, profile.name, engine_label, port
    );

    // Chuẩn bị các flags Chrome sạch (Clean Stealth)
    let mut cmd = Command::new(&chrome_path);
    cmd.arg(format!("--remote-debugging-port={}", port))
        .arg("--remote-allow-origins=*")
        .arg(format!("--user-data-dir={}", user_data_dir.display()))
        .arg("--no-first-run")
        .arg("--no-default-browser-check")
        .arg(format!("--window-size={},{}", window_width, window_height))
        .arg(format!("--window-position={},{}", offset_x, offset_y))
        .arg("--lang=vi-VN,vi,en-US,en")
        .arg("--new-window")
        .arg("about:blank");

    if has_custom_ua {
        cmd.arg(format!("--user-agent={}", profile.profile_user_agent.trim()));
    }

    let gpu_idx = profile.id % GPU_POOL.len();
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
        [4, 6, 8, 12, 16][profile.id % 5]
    } else {
        profile.profile_cpu
    };

    let ram = if profile.profile_ram == 0 {
        match profile.id % 5 {
            0 => 16,
            1 => 32,
            2 => 16,
            3 => 8,
            _ => 16,
        }
    } else {
        profile.profile_ram
    };

    let canvas_seed = profile.canvas_seed.unwrap_or((profile.id as u32).wrapping_mul(1664525) ^ 0x5a5a5a5a);
    let audio_seed = profile.audio_seed.unwrap_or((profile.id as u32).wrapping_mul(1103515245) ^ 0xa5a5a5a5);

    if let Some(parsed_proxy) = parse_proxy_string(&profile.proxy_string) {
        let server_arg = parsed_proxy.server_arg();
        info!("🛡️ Cấu hình Proxy cho Profile #{}: {}", profile.id, server_arg);
        cmd.arg(format!("--proxy-server={}", server_arg));

        // WebRTC Leak Protection: Bắt buộc định tuyến WebRTC qua Proxy hoặc tắt non-proxied UDP
        cmd.arg("--webrtc-ip-handling-policy=disable_non_proxied_udp")
            .arg("--enforce-webrtc-ip-permission-check")
            .arg("--force-webrtc-ip-handling-policy=disable_non_proxied_udp");

        // Nếu proxy có xác thực Username / Password:
        // Tự động sinh Chrome Proxy Auth Extension vào thư mục user_data_dir của profile
        if let (Some(u), Some(p)) = (&parsed_proxy.username, &parsed_proxy.password) {
            let ext_dir = user_data_dir.join("qhtd_proxy_auth_ext");
            if let Ok(_) = std::fs::create_dir_all(&ext_dir) {
                let manifest = r#"{
  "version": "1.0.0",
  "manifest_version": 2,
  "name": "QHTD Anti-Detect Proxy Auth",
  "permissions": [
    "proxy",
    "tabs",
    "unlimitedStorage",
    "storage",
    "<all_urls>",
    "webRequest",
    "webRequestBlocking"
  ],
  "background": {
    "scripts": ["background.js"]
  },
  "minimum_chrome_version": "22.0.0"
}"#;
                let _ = std::fs::write(ext_dir.join("manifest.json"), manifest);

                let bg_js = format!(
                    r#"chrome.webRequest.onAuthRequired.addListener(
    function(details) {{
        return {{
            authCredentials: {{
                username: "{}",
                password: "{}"
            }}
        }};
    }},
    {{urls: ["<all_urls>"]}},
    ['blocking']
);"#,
                    u.replace('\\', "\\\\").replace('"', "\\\""),
                    p.replace('\\', "\\\\").replace('"', "\\\"")
                );
                let _ = std::fs::write(ext_dir.join("background.js"), bg_js);

                cmd.arg(format!("--load-extension={}", ext_dir.display()));
                info!("🔐 Đã nạp Proxy Auth Extension cho Profile #{} (User: {})", profile.id, u);
            }
        }
    }

    // Các switches C++ Native Anti-Detect (Được nhận diện trực tiếp bởi QHTD Custom Chromium)
    cmd.arg(format!("--qhtd-hardware-concurrency={}", cpu))
        .arg(format!("--qhtd-device-memory={}", ram))
        .arg(format!("--qhtd-canvas-noise={}", canvas_seed))
        .arg(format!("--qhtd-audio-noise={}", audio_seed))
        .arg(format!("--qhtd-webgl-vendor={}", vendor))
        .arg(format!("--qhtd-webgl-renderer={}", renderer));

    let mut child = cmd
        .spawn()
        .map_err(|e| format!("Lỗi khi khởi chạy trình duyệt: {}", e))?;

    let p_id = profile.id;
    mark_profile_active(p_id);

    // Theo dõi tiến trình Chrome nền, khi tắt thì cập nhật trạng thái
    std::thread::spawn(move || {
        let _ = child.wait();
        info!("🛑 Cửa sổ Chrome của Profile #{} đã đóng.", p_id);
        mark_profile_inactive(p_id);
    });

    // Chờ Chrome mở cổng DevTools
    let client = reqwest::Client::builder()
        .timeout(Duration::from_millis(2000))
        .build()
        .map_err(|e| e.to_string())?;

    let version_url = format!("http://127.0.0.1:{}/json/version", port);
    let mut browser_ws_url: Option<String> = None;

    for _ in 0..40 {
        tokio::time::sleep(Duration::from_millis(250)).await;
        if let Ok(res) = client.get(&version_url).send().await {
            if let Ok(v) = res.json::<serde_json::Value>().await {
                if let Some(ws) = v.get("webSocketDebuggerUrl").and_then(|v| v.as_str()) {
                    browser_ws_url = Some(ws.to_string());
                    break;
                }
            }
        }
    }

    let ws_url = match browser_ws_url {
        Some(url) => url,
        None => {
            warn!("Không lấy được Browser WebSocket của Chrome sau 10s, Chrome vẫn tiếp tục chạy.");
            return Ok(());
        }
    };

    info!("🔌 Kết nối Browser CDP WebSocket: {}", ws_url);

    // Kết nối Browser WebSocket qua tokio-tungstenite
    let (ws_stream, _) = connect_async(&ws_url)
        .await
        .map_err(|e| format!("Lỗi kết nối Browser WebSocket CDP: {}", e))?;

    let (mut write, mut read) = ws_stream.split();
    let (tx, mut rx) = tokio::sync::mpsc::unbounded_channel::<Message>();

    // Writer task gửi message không đồng bộ
    tokio::spawn(async move {
        while let Some(msg) = rx.recv().await {
            if let Err(_) = write.send(msg).await {
                break;
            }
        }
    });

    // Kích hoạt Target.setAutoAttach để tự động quản lý 100% các tab (Tab ban đầu, Tab mới Ctrl+T, Popup, Link click)
    let auto_attach_cmd = json!({
        "id": 1,
        "method": "Target.setAutoAttach",
        "params": {
            "autoAttach": true,
            "waitForDebuggerOnStart": true,
            "flatten": true
        }
    });
    let _ = tx.send(Message::Text(auto_attach_cmd.to_string()));

    let stealth_js = generate_stealth_script(profile);
    let profile_id = profile.id;

    let custom_ua_cmds = if has_custom_ua {
        let (major_ver, full_ver) = extract_chrome_version(&profile.profile_user_agent);
        let platform_str = if profile.profile_os.eq_ignore_ascii_case("iOS") || profile.profile_user_agent.contains("iPhone") {
            "iPhone"
        } else if is_mobile {
            "Linux armv81"
        } else {
            "Win32"
        };
        let platform_title = if is_mobile {
            if platform_str == "iPhone" { "iOS" } else { "Android" }
        } else {
            "Windows"
        };

        Some((
            json!({
                "method": "Emulation.setUserAgentOverride",
                "params": {
                    "userAgent": profile.profile_user_agent,
                    "acceptLanguage": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                    "platform": platform_str,
                    "userAgentMetadata": {
                        "brands": [
                            {"brand": "Chromium", "version": major_ver},
                            {"brand": "Not:A-Brand", "version": "24"},
                            {"brand": "Google Chrome", "version": major_ver}
                        ],
                        "fullVersion": full_ver,
                        "platform": platform_title,
                        "platformVersion": "15.0.0",
                        "architecture": if is_mobile { "arm" } else { "x86" },
                        "model": if is_mobile { "SM-S918B" } else { "" },
                        "mobile": is_mobile,
                        "bitness": "64",
                        "wow64": false
                    }
                }
            }),
            json!({
                "method": "Network.setUserAgentOverride",
                "params": {
                    "userAgent": profile.profile_user_agent,
                    "acceptLanguage": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
                    "platform": platform_str
                }
            })
        ))
    } else {
        None
    };

    let start_url_clone = start_url.clone();

    // Reader task lắng nghe Target.attachedToTarget để tiêm Stealth vào MỌI tab mới tạo
    tokio::spawn(async move {
        let mut cmd_id: u64 = 100;
        let mut is_first_tab = true;

        while let Some(Ok(msg)) = read.next().await {
            if let Ok(text) = msg.to_text() {
                if let Ok(val) = serde_json::from_str::<serde_json::Value>(text) {
                    if val.get("method").and_then(|m| m.as_str()) == Some("Target.attachedToTarget") {
                        if let Some(params) = val.get("params") {
                            let session_id = params.get("sessionId").and_then(|s| s.as_str()).unwrap_or("");
                            let target_type = params.get("targetInfo")
                                .and_then(|ti| ti.get("type"))
                                .and_then(|t| t.as_str())
                                .unwrap_or("");

                            let is_page = target_type == "page";
                            let is_iframe = target_type == "iframe";

                            if (is_page || is_iframe) && !session_id.is_empty() {
                                // 1. Bật Page domain cho target này
                                cmd_id += 1;
                                let _ = tx.send(Message::Text(json!({
                                    "id": cmd_id,
                                    "sessionId": session_id,
                                    "method": "Page.enable"
                                }).to_string()));

                                // 2. Override UA nếu có tùy biến
                                if let Some((ref ua_cmd, ref net_cmd)) = custom_ua_cmds {
                                    cmd_id += 1;
                                    let mut c1 = ua_cmd.clone();
                                    c1["id"] = json!(cmd_id);
                                    c1["sessionId"] = json!(session_id);
                                    let _ = tx.send(Message::Text(c1.to_string()));

                                    cmd_id += 1;
                                    let mut c2 = net_cmd.clone();
                                    c2["id"] = json!(cmd_id);
                                    c2["sessionId"] = json!(session_id);
                                    let _ = tx.send(Message::Text(c2.to_string()));
                                }

                                // 2b. Mô phỏng Mobile Phone Device Metrics và Touch nếu là profile phone
                                if is_mobile {
                                    cmd_id += 1;
                                    let _ = tx.send(Message::Text(json!({
                                        "id": cmd_id,
                                        "sessionId": session_id,
                                        "method": "Emulation.setDeviceMetricsOverride",
                                        "params": {
                                            "width": screen_w,
                                            "height": screen_h,
                                            "deviceScaleFactor": 3.0,
                                            "mobile": true,
                                            "fitWindow": false
                                        }
                                    }).to_string()));

                                    cmd_id += 1;
                                    let _ = tx.send(Message::Text(json!({
                                        "id": cmd_id,
                                        "sessionId": session_id,
                                        "method": "Emulation.setTouchEmulationEnabled",
                                        "params": {
                                            "enabled": true,
                                            "maxTouchPoints": 5
                                        }
                                    }).to_string()));
                                }

                                // 3. Tiêm Clean Stealth Script cho MỌI lần chuyển trang trong frame/tab này
                                cmd_id += 1;
                                let _ = tx.send(Message::Text(json!({
                                    "id": cmd_id,
                                    "sessionId": session_id,
                                    "method": "Page.addScriptToEvaluateOnNewDocument",
                                    "params": {
                                        "source": stealth_js
                                    }
                                }).to_string()));

                                // 4. Đánh giá ngay lập tức trên document hiện tại (đảm bảo iframe có dữ liệu tức thì)
                                cmd_id += 1;
                                let _ = tx.send(Message::Text(json!({
                                    "id": cmd_id,
                                    "sessionId": session_id,
                                    "method": "Runtime.evaluate",
                                    "params": {
                                        "expression": stealth_js
                                    }
                                }).to_string()));

                                // 5. Nếu là tab ban đầu của window, điều hướng tới start_url và bringToFront (không áp dụng cho iframe nhúng)
                                if is_page && is_first_tab {
                                    is_first_tab = false;
                                    cmd_id += 1;
                                    let _ = tx.send(Message::Text(json!({
                                        "id": cmd_id,
                                        "sessionId": session_id,
                                        "method": "Page.navigate",
                                        "params": {
                                            "url": start_url_clone
                                        }
                                    }).to_string()));

                                    cmd_id += 1;
                                    let _ = tx.send(Message::Text(json!({
                                        "id": cmd_id,
                                        "sessionId": session_id,
                                        "method": "Page.bringToFront"
                                    }).to_string()));
                                }

                                // 6. Cho phép frame/tab tiếp tục chạy (Runtime.runIfWaitingForDebugger)
                                cmd_id += 1;
                                let _ = tx.send(Message::Text(json!({
                                    "id": cmd_id,
                                    "sessionId": session_id,
                                    "method": "Runtime.runIfWaitingForDebugger"
                                }).to_string()));

                                let type_label = if is_page { "Tab" } else { "Iframe (OOPIF)" };
                                info!("🛡️ [Profile #{}] Đã tự động kích hoạt Stealth Shield cho {} mới (Session: {})", profile_id, type_label, session_id);
                            }
                        }
                    }
                }
            }
        }
        info!("🔌 Kết nối Browser CDP của Profile #{} đã ngắt.", profile_id);
        mark_profile_inactive(profile_id);
    });

    info!("✅ Đã cấu hình Browser Auto-Attach Stealth CDP cho Profile #{}", profile.id);
    Ok(())
}
