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
use std::io::{Read, Write};
use tokio_tungstenite::connect_async;
use tokio_tungstenite::tungstenite::protocol::Message;
use tracing::{info, warn};
use zip::write::SimpleFileOptions;
use zip::CompressionMethod;
use zip::{ZipArchive, ZipWriter};

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

pub fn parse_proxy_string_with_type(raw: &str, proxy_type: &str) -> Option<ParsedProxy> {
    if proxy_type.eq_ignore_ascii_case("direct") || raw.trim().is_empty() {
        return None;
    }
    let default_scheme = if proxy_type.eq_ignore_ascii_case("http") { "http" } else { "socks5" };
    let mut parsed = parse_proxy_string(raw)?;
    if !raw.contains("://") {
        parsed.scheme = default_scheme.to_string();
    }
    Some(parsed)
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

/// Lấy thư mục lưu trữ các bản sao lưu Thin Profile (.zip)
pub fn get_profile_backup_dir() -> PathBuf {
    let p1 = PathBuf::from(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\profile_backups");
    if p1.parent().map(|p| p.exists()).unwrap_or(false) {
        let _ = std::fs::create_dir_all(&p1);
        return p1;
    }
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            let p2 = parent.join("profile_backups");
            let _ = std::fs::create_dir_all(&p2);
            return p2;
        }
    }
    let fallback = PathBuf::from("profile_backups");
    let _ = std::fs::create_dir_all(&fallback);
    fallback
}

/// Helper duyệt tất cả các file trong thư mục con
fn walk_dir_files(dir: &std::path::Path) -> Vec<PathBuf> {
    let mut files = Vec::new();
    if let Ok(entries) = std::fs::read_dir(dir) {
        for entry in entries.flatten() {
            let path = entry.path();
            if path.is_dir() {
                files.extend(walk_dir_files(&path));
            } else if path.is_file() {
                files.push(path);
            }
        }
    }
    files
}

/// Sao lưu Thin Profile (chỉ nén 7 file/thư mục phiên cốt lõi: Local State, Cookies, Storage... ~200KB/profile)
pub fn backup_thin_profile(profile_id: usize) -> Result<(PathBuf, u64), String> {
    let user_data_dir = std::env::temp_dir().join(format!("mun_profile_{}", profile_id));
    if !user_data_dir.exists() {
        return Err(format!("Thư mục profile không tồn tại: {}", user_data_dir.display()));
    }

    let backup_dir = get_profile_backup_dir();
    let zip_path = backup_dir.join(format!("profile_{}.zip", profile_id));
    let temp_zip_path = backup_dir.join(format!("profile_{}.tmp.zip", profile_id));

    let file = std::fs::File::create(&temp_zip_path)
        .map_err(|e| format!("Không thể tạo file zip tạm: {}", e))?;
    let mut zip = ZipWriter::new(file);
    let options = SimpleFileOptions::default()
        .compression_method(CompressionMethod::Deflated);

    let essential_paths = [
        "Local State",
        "Default/Preferences",
        "Default/Network",
        "Default/Local Storage",
        "Default/Session Storage",
        "Default/IndexedDB",
        "Default/Web Data",
    ];

    let mut total_files = 0usize;

    for rel_path_str in &essential_paths {
        let os_rel = rel_path_str.replace('/', &std::path::MAIN_SEPARATOR.to_string());
        let target_path = user_data_dir.join(&os_rel);
        if !target_path.exists() {
            continue;
        }

        if target_path.is_file() {
            if let Ok(mut f) = std::fs::File::open(&target_path) {
                let zip_entry_name = rel_path_str.replace('\\', "/");
                if zip.start_file(&zip_entry_name, options).is_ok() {
                    let mut buf = Vec::new();
                    if f.read_to_end(&mut buf).is_ok() {
                        let _ = zip.write_all(&buf);
                        total_files += 1;
                    }
                }
            }
        } else if target_path.is_dir() {
            for entry in walk_dir_files(&target_path) {
                if let Ok(rel) = entry.strip_prefix(&user_data_dir) {
                    let zip_entry_name = rel.to_string_lossy().replace('\\', "/");
                    if entry.is_file() {
                        if let Ok(mut f) = std::fs::File::open(&entry) {
                            if zip.start_file(&zip_entry_name, options).is_ok() {
                                let mut buf = Vec::new();
                                if f.read_to_end(&mut buf).is_ok() {
                                    let _ = zip.write_all(&buf);
                                    total_files += 1;
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    zip.finish().map_err(|e| format!("Lỗi hoàn tất nén zip: {}", e))?;

    // Đổi tên nguyên tử (Atomic replace)
    let _ = std::fs::remove_file(&zip_path);
    std::fs::rename(&temp_zip_path, &zip_path)
        .map_err(|e| format!("Lỗi lưu file zip backup: {}", e))?;

    let size = std::fs::metadata(&zip_path).map(|m| m.len()).unwrap_or(0);
    info!(
        "💾 Đã sao lưu Thin Profile #{} thành công: {} ({} files, {:.1} KB)",
        profile_id,
        zip_path.display(),
        total_files,
        (size as f64) / 1024.0
    );
    Ok((zip_path, size))
}

/// Phục hồi Thin Profile từ bản nén ZIP vào thư mục temp trước khi khởi chạy Chrome
pub fn restore_thin_profile(profile_id: usize) -> Result<bool, String> {
    let backup_dir = get_profile_backup_dir();
    let zip_path = backup_dir.join(format!("profile_{}.zip", profile_id));
    if !zip_path.exists() {
        return Ok(false);
    }

    let user_data_dir = std::env::temp_dir().join(format!("mun_profile_{}", profile_id));
    let _ = std::fs::create_dir_all(&user_data_dir);

    let file = std::fs::File::open(&zip_path)
        .map_err(|e| format!("Không thể mở file zip backup: {}", e))?;
    let mut archive = ZipArchive::new(file)
        .map_err(|e| format!("Lỗi đọc file zip backup: {}", e))?;

    archive.extract(&user_data_dir)
        .map_err(|e| format!("Lỗi giải nén profile backup: {}", e))?;

    info!("⚡ Đã phục hồi Thin Profile #{} thành công từ {}", profile_id, zip_path.display());
    Ok(true)
}

/// Dừng profile Chrome đang chạy, tự động sao lưu Thin Profile và xóa trạng thái
pub fn stop_cdp_profile(profile_id: usize) {
    info!("🛑 Dừng tiến trình Chrome của Profile #{}", profile_id);
    let user_data_dir = std::env::temp_dir().join(format!("mun_profile_{}", profile_id));
    cleanup_profile_process_and_locks(profile_id, &user_data_dir);

    // Tự động sao lưu phiên đăng nhập (Thin Profile Backup) khi trình duyệt tắt
    let _ = backup_thin_profile(profile_id);

    mark_profile_inactive(profile_id);
}

/// Khởi chạy Local SOCKS5 Bridge trong Tokio background để Chrome kết nối không cần pass
/// và Bridge tự động thực hiện xác thực RFC 1929 SOCKS5 với upstream remote proxy.
pub async fn spawn_socks5_bridge(
    remote_host: String,
    remote_port: u16,
    remote_user: Option<String>,
    remote_pass: Option<String>,
) -> Result<(u16, tokio::sync::oneshot::Sender<()>), String> {
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0")
        .await
        .map_err(|e| format!("Không thể mở local port cho proxy bridge: {}", e))?;
    let local_port = listener.local_addr().map_err(|e| e.to_string())?.port();
    let (shutdown_tx, mut shutdown_rx) = tokio::sync::oneshot::channel::<()>();

    tokio::spawn(async move {
        loop {
            tokio::select! {
                _ = &mut shutdown_rx => {
                    break;
                }
                accept_res = listener.accept() => {
                    match accept_res {
                        Ok((client_stream, _)) => {
                            let r_host = remote_host.clone();
                            let r_port = remote_port;
                            let r_user = remote_user.clone();
                            let r_pass = remote_pass.clone();
                            tokio::spawn(async move {
                                let _ = handle_socks5_bridge_client(client_stream, r_host, r_port, r_user, r_pass).await;
                            });
                        }
                        Err(_) => break,
                    }
                }
            }
        }
    });

    Ok((local_port, shutdown_tx))
}

async fn handle_socks5_bridge_client(
    mut client: tokio::net::TcpStream,
    remote_host: String,
    remote_port: u16,
    remote_user: Option<String>,
    remote_pass: Option<String>,
) -> Result<(), Box<dyn std::error::Error + Send + Sync>> {
    use tokio::io::{AsyncReadExt, AsyncWriteExt};

    // 1. Chrome -> Bridge: Handshake
    let mut ver_methods = [0u8; 256];
    let n = client.read(&mut ver_methods).await?;
    if n < 2 || ver_methods[0] != 0x05 {
        return Ok(());
    }
    // Accept NO AUTHENTICATION (0x05, 0x00)
    client.write_all(&[0x05, 0x00]).await?;

    // 2. Chrome -> Bridge: Connect Request
    let mut req_hdr = [0u8; 4];
    client.read_exact(&mut req_hdr).await?;
    if req_hdr[0] != 0x05 || req_hdr[1] != 0x01 {
        return Ok(());
    }
    let atyp = req_hdr[3];
    let mut full_req = req_hdr.to_vec();
    match atyp {
        0x01 => {
            let mut buf = [0u8; 6];
            client.read_exact(&mut buf).await?;
            full_req.extend_from_slice(&buf);
        }
        0x03 => {
            let mut len_byte = [0u8; 1];
            client.read_exact(&mut len_byte).await?;
            full_req.push(len_byte[0]);
            let mut domain_and_port = vec![0u8; len_byte[0] as usize + 2];
            client.read_exact(&mut domain_and_port).await?;
            full_req.extend_from_slice(&domain_and_port);
        }
        0x04 => {
            let mut buf = [0u8; 18];
            client.read_exact(&mut buf).await?;
            full_req.extend_from_slice(&buf);
        }
        _ => return Ok(()),
    }

    // 3. Connect to remote upstream SOCKS5 server
    let target = format!("{}:{}", remote_host, remote_port);
    let mut upstream = match tokio::time::timeout(
        Duration::from_secs(12),
        tokio::net::TcpStream::connect(&target)
    ).await {
        Ok(Ok(s)) => s,
        _ => {
            let _ = client.write_all(&[0x05, 0x05, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await;
            return Ok(());
        }
    };

    // 4. Negotiate authentication with upstream
    if let (Some(u), Some(p)) = (remote_user, remote_pass) {
        upstream.write_all(&[0x05, 0x01, 0x02]).await?;
        let mut method_choice = [0u8; 2];
        upstream.read_exact(&mut method_choice).await?;
        if method_choice[0] != 0x05 || method_choice[1] != 0x02 {
            let _ = client.write_all(&[0x05, 0x05, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await;
            return Ok(());
        }

        let mut auth_buf = Vec::with_capacity(3 + u.len() + p.len());
        auth_buf.push(0x01);
        auth_buf.push(u.len() as u8);
        auth_buf.extend_from_slice(u.as_bytes());
        auth_buf.push(p.len() as u8);
        auth_buf.extend_from_slice(p.as_bytes());
        upstream.write_all(&auth_buf).await?;

        let mut auth_resp = [0u8; 2];
        upstream.read_exact(&mut auth_resp).await?;
        if auth_resp[1] != 0x00 {
            let _ = client.write_all(&[0x05, 0x05, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await;
            return Ok(());
        }
    } else {
        upstream.write_all(&[0x05, 0x01, 0x00]).await?;
        let mut method_choice = [0u8; 2];
        upstream.read_exact(&mut method_choice).await?;
        if method_choice[0] != 0x05 || method_choice[1] != 0x00 {
            let _ = client.write_all(&[0x05, 0x05, 0x00, 0x01, 0, 0, 0, 0, 0, 0]).await;
            return Ok(());
        }
    }

    // 5. Forward connect request to upstream
    upstream.write_all(&full_req).await?;

    // 6. Read upstream reply header and forward to client
    let mut reply_hdr = [0u8; 4];
    upstream.read_exact(&mut reply_hdr).await?;
    let rep_atyp = reply_hdr[3];

    let mut reply_buf = Vec::new();
    reply_buf.extend_from_slice(&reply_hdr);
    match rep_atyp {
        0x01 => {
            let mut b = [0u8; 6];
            upstream.read_exact(&mut b).await?;
            reply_buf.extend_from_slice(&b);
        }
        0x03 => {
            let mut dlen = [0u8; 1];
            upstream.read_exact(&mut dlen).await?;
            reply_buf.push(dlen[0]);
            let mut dbuf = vec![0u8; dlen[0] as usize + 2];
            upstream.read_exact(&mut dbuf).await?;
            reply_buf.extend_from_slice(&dbuf);
        }
        0x04 => {
            let mut b = [0u8; 18];
            upstream.read_exact(&mut b).await?;
            reply_buf.extend_from_slice(&b);
        }
        _ => {}
    }
    client.write_all(&reply_buf).await?;

    if reply_hdr[1] != 0x00 {
        return Ok(());
    }

    // 7. Bidirectional streaming
    let _ = tokio::io::copy_bidirectional(&mut client, &mut upstream).await;
    Ok(())
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

    // Tự động phục hồi Thin Profile (nếu có bản sao lưu trước đó) - Đảm bảo Zero Login
    if let Ok(restored) = restore_thin_profile(profile.id) {
        if restored {
            info!("⚡ Đã nạp thành công Thin Profile (Zero-Login) cho Profile #{}", profile.id);
        }
    }

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

    let use_proxy = !profile.proxy_type.eq_ignore_ascii_case("direct") && !profile.proxy_string.trim().is_empty();
    let mut proxy_bridge_shutdown: Option<tokio::sync::oneshot::Sender<()>> = None;

    if use_proxy {
        if let Some(parsed_proxy) = parse_proxy_string_with_type(&profile.proxy_string, &profile.proxy_type) {
            let has_auth = parsed_proxy.username.is_some() && parsed_proxy.password.is_some();
            let is_socks = parsed_proxy.scheme.starts_with("socks");

            if is_socks && has_auth {
                // Chromium không hỗ trợ xác thực RFC 1929 SOCKS5 user/pass trực tiếp từ command line.
                // Khởi tạo Local In-Process SOCKS5 Bridge không cần auth cho Chrome kết nối!
                match spawn_socks5_bridge(
                    parsed_proxy.host.clone(),
                    parsed_proxy.port,
                    parsed_proxy.username.clone(),
                    parsed_proxy.password.clone(),
                ).await {
                    Ok((local_port, tx)) => {
                        info!("🚀 Đã kích hoạt Local SOCKS5 Bridge 127.0.0.1:{} -> {}:{} cho Profile #{}", local_port, parsed_proxy.host, parsed_proxy.port, profile.id);
                        cmd.arg(format!("--proxy-server=socks5://127.0.0.1:{}", local_port));
                        proxy_bridge_shutdown = Some(tx);
                    }
                    Err(e) => {
                        warn!("⚠️ Không thể mở Local SOCKS5 Bridge ({}), fallback sang direct flag", e);
                        cmd.arg(format!("--proxy-server={}", parsed_proxy.server_arg()));
                    }
                }
            } else {
                let server_arg = parsed_proxy.server_arg();
                info!("🛡️ Cấu hình Proxy [{}] cho Profile #{}: {}", parsed_proxy.scheme.to_uppercase(), profile.id, server_arg);
                cmd.arg(format!("--proxy-server={}", server_arg));
            }

            // WebRTC Leak Protection: Bắt buộc định tuyến WebRTC qua Proxy hoặc tắt hẳn
            let webrtc_mode = profile.webrtc_mode.as_deref().unwrap_or("proxy_only");
            if webrtc_mode == "disabled" {
                cmd.arg("--disable-webrtc");
            } else if webrtc_mode == "proxy_only" {
                cmd.arg("--webrtc-ip-handling-policy=disable_non_proxied_udp")
                    .arg("--enforce-webrtc-ip-permission-check")
                    .arg("--force-webrtc-ip-handling-policy=disable_non_proxied_udp");
            }

            // Nếu là HTTP proxy có auth: nạp Extension cho HTTP
            if !is_socks && has_auth {
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

    // Theo dõi tiến trình Chrome nền, khi tắt thì cập nhật trạng thái và giải phóng bridge
    std::thread::spawn(move || {
        let _ = child.wait();
        info!("🛑 Cửa sổ Chrome của Profile #{} đã đóng.", p_id);
        mark_profile_inactive(p_id);
        if let Some(tx) = proxy_bridge_shutdown {
            let _ = tx.send(());
        }
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
    let profile_tiktok_username = profile.tiktok_username.clone();
    let profile_tiktok_account_id = profile.tiktok_account_id;

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
                                    let is_tiktok = start_url_clone.contains("tiktok.com") 
                                        || profile_tiktok_username.is_some() 
                                        || profile_tiktok_account_id.is_some();
                                    if is_tiktok {
                                        let s_id = session_id.to_string();
                                        let tx_sub = tx.clone();
                                        let p_id = profile_id;
                                        let u_name = profile_tiktok_username.clone();
                                        let a_id = profile_tiktok_account_id;
                                        tokio::spawn(async move {
                                            check_and_handle_tiktok_login_cdp(p_id, s_id, tx_sub, u_name, a_id).await;
                                        });
                                    }
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

async fn check_and_handle_tiktok_login_cdp(
    profile_id: usize,
    session_id: String,
    tx: tokio::sync::mpsc::UnboundedSender<Message>,
    tiktok_username: Option<String>,
    tiktok_account_id: Option<u64>,
) {
    // 1. Chờ 6s để trang web TikTok tải xong hoàn toàn
    tokio::time::sleep(Duration::from_secs(6)).await;
    info!("🔍 [Profile #{}] Đang kiểm tra trạng thái đăng nhập TikTok...", profile_id);

    // Lấy thông tin tài khoản C69 gắn với profile này (nếu có)
    let c69_acc = if let Ok(accounts) = crate::browser_nurture::fetch_c69_tiktok_accounts().await {
        accounts.into_iter().find(|a| {
            if let Some(aid) = tiktok_account_id {
                if a.id == aid { return true; }
            }
            if let Some(ref u) = tiktok_username {
                if a.username.eq_ignore_ascii_case(u) { return true; }
            }
            false
        })
    } else {
        None
    };

    if let Some(acc) = c69_acc {
        let login_target = if let Some(ref em) = acc.email {
            if em.contains('@') { em.clone() } else { acc.username.clone() }
        } else {
            acc.username.clone()
        };
        let pwd_str = acc.password.clone().unwrap_or_default();
        let two_fa = acc.two_factor_auth.clone().unwrap_or_default();

        info!("👤 [Profile #{}] Đã gắn tài khoản C69: {}. Kiểm tra phiên đăng nhập...", profile_id, login_target);

        // Script kiểm tra và tự động điền form đăng nhập nếu chưa login
        let login_script = format!(r#"
            (async () => {{
                const hasAvatar = !!(
                    document.querySelector('[data-e2e="profile-icon"]') || 
                    document.querySelector('img[alt*="avatar"]') || 
                    document.querySelector('a[href*="/@"]') ||
                    document.querySelector('[data-e2e="inbox-icon"]')
                );
                const hasLoginBtn = !!(
                    document.querySelector('#header-login-button') ||
                    Array.from(document.querySelectorAll('button, a')).some(el => {{
                        const t = (el.innerText || '').trim().toLowerCase();
                        return (t === 'log in' || t === 'đăng nhập') && el.offsetParent !== null;
                    }})
                );

                if (hasAvatar && !hasLoginBtn) {{
                    console.log('QHTD: Tài khoản TikTok đã đăng nhập sẵn!');
                    if (window.location.href.includes('/login')) {{
                        window.location.href = 'https://www.tiktok.com/foryou';
                    }}
                    return 'already_logged_in';
                }}

                // Nếu chưa ở trang login, chuyển hướng vào trang login
                if (!window.location.href.includes('/login')) {{
                    console.log('QHTD: Chưa đăng nhập, chuyển hướng đến trang Login...');
                    window.location.href = 'https://www.tiktok.com/login/phone-or-email/email?lang=en';
                    return 'redirecting_to_login';
                }}

                // Nếu đã ở trang login, tự động điền thông tin tài khoản bằng React Synthetic setter
                function setReactVal(input, val) {{
                    if (!input) return;
                    input.focus();
                    const proto = window.HTMLInputElement.prototype;
                    const desc = Object.getOwnPropertyDescriptor(proto, 'value');
                    if (desc && desc.set) {{
                        desc.set.call(input, val);
                    }} else {{
                        input.value = val;
                    }}
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}

                const uInp = document.querySelector('input[name="username"]') || 
                             document.querySelector('input[placeholder*="Email"]') || 
                             document.querySelector('input[placeholder*="Username"]') ||
                             document.querySelector('input[type="text"]');
                const pInp = document.querySelector('input[type="password"]');

                if (uInp && pInp) {{
                    setReactVal(uInp, '{}');
                    setReactVal(pInp, '{}');

                    const submitBtn = document.querySelector('button[type="submit"]') || 
                                      Array.from(document.querySelectorAll('button')).find(b => b.innerText.trim().toLowerCase().includes('log in'));
                    if (submitBtn) {{
                        submitBtn.disabled = false;
                        submitBtn.removeAttribute('disabled');
                        setTimeout(() => {{
                            submitBtn.click();
                            const form = document.querySelector('form');
                            if (form) {{ try {{ form.requestSubmit(); }} catch(e) {{}} }}
                        }}, 600);
                        return 'form_submitted';
                    }}
                }}
                return 'waiting_login_fields';
            }})()
        "#, login_target.replace('\\', "\\\\").replace('\'', "\\'").replace('"', "\\\""), pwd_str.replace('\\', "\\\\").replace('\'', "\\'").replace('"', "\\\""));

        let cmd_exec = json!({
            "id": 999902,
            "sessionId": session_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": login_script,
                "awaitPromise": true
            }
        });
        let _ = tx.send(Message::Text(cmd_exec.to_string()));

        // Chờ 6s và thử điền lại (cho trường hợp vừa chuyển hướng từ tiktok.com sang trang login)
        tokio::time::sleep(Duration::from_secs(6)).await;
        let cmd_retry = json!({
            "id": 999903,
            "sessionId": session_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": login_script,
                "awaitPromise": true
            }
        });
        let _ = tx.send(Message::Text(cmd_retry.to_string()));

        // Nếu có 2FA Secret Key, chờ thêm 4s để tự động giải mã và điền OTP TOTP
        if !two_fa.trim().is_empty() && two_fa.trim().len() >= 8 {
            tokio::time::sleep(Duration::from_secs(4)).await;
            let totp_script = format!(r#"
                (async () => {{
                    const base32chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
                    let bits = '';
                    const clean = '{}'.replace(/[\s=-]/g, '').toUpperCase();
                    for (let i = 0; i < clean.length; i++) {{
                        const val = base32chars.indexOf(clean[i]);
                        if (val >= 0) bits += val.toString(2).padStart(5, '0');
                    }}
                    const bytes = new Uint8Array(Math.floor(bits.length / 8));
                    for (let i = 0; i < bytes.length; i++) {{
                        bytes[i] = parseInt(bits.substr(i * 8, 8), 2);
                    }}
                    const epoch = Math.floor(Date.now() / 1000);
                    const counter = Math.floor(epoch / 30);
                    const counterBuffer = new ArrayBuffer(8);
                    const counterView = new DataView(counterBuffer);
                    counterView.setUint32(4, counter, false);
                    const key = await crypto.subtle.importKey('raw', bytes, {{ name: 'HMAC', hash: {{ name: 'SHA-1' }} }}, false, ['sign']);
                    const sig = await crypto.subtle.sign('HMAC', key, counterBuffer);
                    const sigBytes = new Uint8Array(sig);
                    const offset = sigBytes[sigBytes.length - 1] & 0x0f;
                    const code = ((sigBytes[offset] & 0x7f) << 24 | (sigBytes[offset + 1] & 0xff) << 16 | (sigBytes[offset + 2] & 0xff) << 8 | (sigBytes[offset + 3] & 0xff)) % 1000000;
                    const totp = code.toString().padStart(6, '0');

                    const otpInputs = Array.from(document.querySelectorAll('input')).filter(i => {{
                        const maxL = i.getAttribute('maxlength');
                        return maxL === '1' || maxL === '6' || i.className.includes('digit') || i.className.includes('code');
                    }});
                    if (otpInputs.length === 6) {{
                        for (let i = 0; i < 6; i++) {{
                            otpInputs[i].value = totp[i];
                            otpInputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        }}
                        return 'totp_filled_multi';
                    }} else if (otpInputs.length >= 1) {{
                        otpInputs[0].value = totp;
                        otpInputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        return 'totp_filled_single';
                    }}
                    return 'no_otp_input';
                }})()
            "#, two_fa.trim());

            let cmd_totp = json!({
                "id": 999904,
                "sessionId": session_id,
                "method": "Runtime.evaluate",
                "params": {
                    "expression": totp_script,
                    "awaitPromise": true
                }
            });
            let _ = tx.send(Message::Text(cmd_totp.to_string()));
            info!("🔑 [Profile #{}] Đã tự động tính toán mã 2FA TOTP RFC 6238 và gửi vào form xác thực!", profile_id);
        }
    } else {
        // Chưa liên kết tài khoản C69 -> Kiểm tra nếu chưa login thì điều hướng đến trang login để người dùng tiện đăng nhập
        let redirect_script = r#"
            (() => {
                const hasCookie = document.cookie.includes('sessionid=');
                const hasAvatar = !!(
                    document.querySelector('[data-e2e="profile-icon"]') || 
                    document.querySelector('img[alt*="avatar"]') || 
                    document.querySelector('a[href*="/@"]') ||
                    document.querySelector('[data-e2e="inbox-icon"]')
                );
                if (!hasCookie && !hasAvatar && !window.location.href.includes('/login')) {
                    window.location.href = 'https://www.tiktok.com/login/phone-or-email/email?lang=en';
                    return 'redirected_to_login';
                }
                return 'ok';
            })()
        "#;
        let cmd_redir = json!({
            "id": 999905,
            "sessionId": session_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": redirect_script
            }
        });
        let _ = tx.send(Message::Text(cmd_redir.to_string()));
    }
}
