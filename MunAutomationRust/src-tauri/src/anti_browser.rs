use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ScreenConfig {
    pub width: u32,
    pub height: u32,
    pub avail_width: u32,
    pub avail_height: u32,
    pub color_depth: u32,
    pub pixel_depth: u32,
    pub device_pixel_ratio: f64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WebGLConfig {
    pub unmasked_vendor: String,
    pub unmasked_renderer: String,
    pub vendor: String,
    pub renderer: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct FingerprintConfig {
    pub user_agent: String,
    pub platform: String,
    pub hardware_concurrency: u32,
    pub device_memory: u32,
    pub screen: ScreenConfig,
    pub webgl: WebGLConfig,
    pub canvas_noise: f64,
    pub audio_noise: f64,
    pub timezone: String,
    pub locale: String,
}

impl Default for FingerprintConfig {
    fn default() -> Self {
        Self {
            user_agent: "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36".to_string(),
            platform: "Win32".to_string(),
            hardware_concurrency: 8,
            device_memory: 8,
            screen: ScreenConfig {
                width: 1920,
                height: 1080,
                avail_width: 1920,
                avail_height: 1040,
                color_depth: 24,
                pixel_depth: 24,
                device_pixel_ratio: 1.0,
            },
            webgl: WebGLConfig {
                unmasked_vendor: "Google Inc. (NVIDIA)".to_string(),
                unmasked_renderer: "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 Direct3D11 vs_5_0 ps_5_0, D3D11)".to_string(),
                vendor: "WebKit".to_string(),
                renderer: "WebKit WebGL".to_string(),
            },
            canvas_noise: 0.0001,
            audio_noise: 0.0001,
            timezone: "Asia/Ho_Chi_Minh".to_string(),
            locale: "vi-VN".to_string(),
        }
    }
}

pub struct ProfileManager {
    data_dir: PathBuf,
}

impl ProfileManager {
    pub fn new<P: AsRef<Path>>(data_dir: P) -> Self {
        let dir = data_dir.as_ref().to_path_buf();
        fs::create_dir_all(&dir).unwrap_or_default();
        Self { data_dir: dir }
    }

    pub fn get_or_create_profile(&self, profile_id: &str) -> (PathBuf, FingerprintConfig) {
        let profile_dir = self.data_dir.join("profiles").join(profile_id);
        fs::create_dir_all(&profile_dir).unwrap_or_default();

        let config_file = profile_dir.join("fingerprint.json");
        let config = if config_file.exists() {
            if let Ok(content) = fs::read_to_string(&config_file) {
                serde_json::from_str(&content).unwrap_or_default()
            } else {
                FingerprintConfig::default()
            }
        } else {
            let def = FingerprintConfig::default();
            if let Ok(json) = serde_json::to_string_pretty(&def) {
                let _ = fs::write(&config_file, json);
            }
            def
        };

        (profile_dir, config)
    }
}

pub fn generate_stealth_script(config: &FingerprintConfig) -> String {
    format!(
        r#"
(() => {{
    // 1. Overwrite Navigator properties
    const navProto = Navigator.prototype;
    Object.defineProperty(navProto, 'webdriver', {{ get: () => undefined, configurable: true }});
    Object.defineProperty(navProto, 'hardwareConcurrency', {{ get: () => {hardware_concurrency}, configurable: true }});
    Object.defineProperty(navProto, 'deviceMemory', {{ get: () => {device_memory}, configurable: true }});
    Object.defineProperty(navProto, 'platform', {{ get: () => '{platform}', configurable: true }});
    Object.defineProperty(navProto, 'userAgent', {{ get: () => '{user_agent}', configurable: true }});

    // 2. WebGL Fingerprint Spoofing
    const getParameter = WebGLRenderingContext.prototype.getParameter;
    WebGLRenderingContext.prototype.getParameter = function(parameter) {{
        // UNMASKED_VENDOR_WEBGL
        if (parameter === 37445) return '{webgl_vendor}';
        // UNMASKED_RENDERER_WEBGL
        if (parameter === 37446) return '{webgl_renderer}';
        return getParameter.apply(this, arguments);
    }};

    // 3. Canvas Noise injection
    const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
    HTMLCanvasElement.prototype.toDataURL = function() {{
        const context = this.getContext('2d');
        if (context) {{
            const imageData = context.getImageData(0, 0, this.width || 1, this.height || 1);
            imageData.data[0] = Math.min(255, imageData.data[0] + 1);
            context.putImageData(imageData, 0, 0);
        }}
        return originalToDataURL.apply(this, arguments);
    }};

    // 4. Chrome Runtime mock
    if (!window.chrome) {{
        window.chrome = {{
            app: {{ isInstalled: false, InstallState: {{ DISABLED: 'disabled', INSTALLED: 'installed', NOT_INSTALLED: 'not_installed' }}, RunningState: {{ CANNOT_RUN: 'cannot_run', READY_TO_RUN: 'ready_to_run', RUNNING: 'running' }} }},
            runtime: {{ OnInstalledReason: {{ CHROME_UPDATE: 'chrome_update', INSTALL: 'install', SHARED_MODULE_UPDATE: 'shared_module_update', UPDATE: 'update' }} }}
        }};
    }}
}})();
"#,
        hardware_concurrency = config.hardware_concurrency,
        device_memory = config.device_memory,
        platform = config.platform,
        user_agent = config.user_agent,
        webgl_vendor = config.webgl.unmasked_vendor,
        webgl_renderer = config.webgl.unmasked_renderer
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use tempfile::tempdir;

    #[test]
    fn test_profile_creation() {
        let temp = tempdir().unwrap();
        let manager = ProfileManager::new(temp.path());
        let (p_dir, config) = manager.get_or_create_profile("test_profile");
        
        assert!(p_dir.exists());
        assert_eq!(config.platform, "Win32");
        assert_eq!(config.hardware_concurrency, 8);
    }

    #[test]
    fn test_stealth_script_generation() {
        let config = FingerprintConfig::default();
        let script = generate_stealth_script(&config);
        assert!(script.contains("webdriver"));
        assert!(script.contains("UNMASKED_RENDERER_WEBGL"));
    }
}
