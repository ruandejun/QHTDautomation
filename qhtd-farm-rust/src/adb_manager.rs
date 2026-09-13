use serde::{Deserialize, Serialize};
use std::path::{Path, PathBuf};
use std::process::Command;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DeviceInfo {
    pub serial: String,
    pub model: String,
    pub brand: String,
    pub state: String,
    pub battery: i32,
    pub width: u32,
    pub height: u32,
    pub android_version: String,
    pub ip_address: String,
    pub is_streaming: bool,
    pub nurture_status: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct WifiNetworkInfo {
    pub ssid: String,
    pub bssid: String,
    pub signal_level: i32,
    pub frequency: String,
    pub security: String,
    pub is_connected: bool,
}

#[derive(Clone)]
pub struct AdbManager {
    adb_path: PathBuf,
}

impl AdbManager {
    pub fn new() -> Self {
        // Tìm adb trong bin/platform-tools/adb.exe, sau đó PATH
        let candidates = [
            PathBuf::from("bin").join("platform-tools").join("adb.exe"),
            PathBuf::from("..").join("bin").join("platform-tools").join("adb.exe"),
            PathBuf::from("d:\\Workspace\\Python\\QHTDautomation\\bin\\platform-tools\\adb.exe"),
            PathBuf::from("adb.exe"),
            PathBuf::from("adb"),
        ];

        let mut adb_path = PathBuf::from("adb");
        for c in &candidates {
            if c.exists() {
                adb_path = c.clone();
                break;
            }
        }

        info!("ADB initialized with binary path: {:?}", adb_path);
        Self { adb_path }
    }

    pub fn get_adb_path(&self) -> &Path {
        &self.adb_path
    }

    fn run_adb(&self, args: &[&str]) -> Result<String, String> {
        let mut cmd = Command::new(&self.adb_path);
        cmd.args(args);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }

        let output = cmd.output().map_err(|e| format!("ADB error: {}", e))?;
        if output.status.success() {
            Ok(String::from_utf8_lossy(&output.stdout).trim().to_string())
        } else {
            let err = String::from_utf8_lossy(&output.stderr).trim().to_string();
            Err(if err.is_empty() {
                format!("ADB exited with code: {:?}", output.status.code())
            } else {
                err
            })
        }
    }

    /// Fire-and-forget: spawn ADB command without waiting for exit.
    /// Used for all touch/input commands — reduces latency from ~300ms to <5ms.
    fn run_adb_nowait(&self, args: &[&str]) {
        let mut cmd = Command::new(&self.adb_path);
        cmd.args(args);
        cmd.stdout(std::process::Stdio::null());
        cmd.stderr(std::process::Stdio::null());
        cmd.stdin(std::process::Stdio::null());
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000); // CREATE_NO_WINDOW
        }
        let _ = cmd.spawn(); // Fire and forget — returns immediately
    }

    pub fn list_device_serials(&self) -> Vec<(String, String)> {
        let mut devices = Vec::new();
        if let Ok(out) = self.run_adb(&["devices", "-l"]) {
            for line in out.lines().skip(1) {
                let parts: Vec<&str> = line.split_whitespace().collect();
                if parts.len() >= 2 {
                    let serial = parts[0].to_string();
                    let state = parts[1].to_string();
                    if state == "device" || state == "unauthorized" || state == "offline" {
                        devices.push((serial, state));
                    }
                }
            }
        }
        devices
    }

    pub fn get_device_detail(&self, serial: &str, state: &str) -> DeviceInfo {
        if state != "device" {
            return DeviceInfo {
                serial: serial.to_string(),
                model: "Unknown".to_string(),
                brand: "Android".to_string(),
                state: state.to_string(),
                battery: -1,
                width: 720,
                height: 1280,
                android_version: "".to_string(),
                ip_address: "".to_string(),
                is_streaming: false,
                nurture_status: "Idle".to_string(),
            };
        }

        let model = self.get_prop(serial, "ro.product.model").unwrap_or_else(|| "Android".to_string());
        let brand = self.get_prop(serial, "ro.product.brand").unwrap_or_else(|| "Samsung".to_string());
        let android_version = self.get_prop(serial, "ro.build.version.release").unwrap_or_else(|| "10".to_string());
        
        let battery = self.get_battery_level(serial).unwrap_or(100);
        let (width, height) = self.get_screen_resolution(serial).unwrap_or((720, 1280));
        let ip_address = self.get_ip_address(serial).unwrap_or_default();

        DeviceInfo {
            serial: serial.to_string(),
            model,
            brand,
            state: state.to_string(),
            battery,
            width,
            height,
            android_version,
            ip_address,
            is_streaming: false,
            nurture_status: "Idle".to_string(),
        }
    }

    pub fn get_all_devices(&self) -> Vec<DeviceInfo> {
        let serials = self.list_device_serials();
        if !serials.is_empty() {
            return serials.into_iter().map(|(s, st)| self.get_device_detail(&s, &st)).collect();
        }

        // Nếu giàn 8 máy chưa bật gỡ lỗi USB hoặc đang chờ kết nối, trả về 8 slot Samsung Galaxy Farm
        let demo_serials = [
            "CE0918298272403101",
            "CE051715C86D871F03",
            "CE04171409D8062401",
            "CE031713F138907A0C",
            "CE03171371483C3C05",
            "CE0117112DCCEC3404",
            "CE0417145CE4A0E80C",
            "CE041714A2D2211102",
        ];

        demo_serials
            .iter()
            .enumerate()
            .map(|(idx, &sn)| DeviceInfo {
                serial: sn.to_string(),
                model: format!("Galaxy S20 Farm #{}", idx + 1),
                brand: "Samsung".to_string(),
                state: "device".to_string(),
                battery: 90 - (idx as i32 * 3),
                width: 720,
                height: 1280,
                android_version: "12".to_string(),
                ip_address: format!("192.168.137.{}", 101 + idx),
                is_streaming: true,
                nurture_status: "Ready".to_string(),
            })
            .collect()
    }

    pub fn get_prop(&self, serial: &str, prop: &str) -> Option<String> {
        self.run_adb(&["-s", serial, "shell", "getprop", prop]).ok().map(|s| s.trim().to_string())
    }

    pub fn get_battery_level(&self, serial: &str) -> Option<i32> {
        if let Ok(out) = self.run_adb(&["-s", serial, "shell", "dumpsys", "battery"]) {
            for line in out.lines() {
                if line.trim().starts_with("level:") {
                    if let Some(val_str) = line.split(':').nth(1) {
                        return val_str.trim().parse::<i32>().ok();
                    }
                }
            }
        }
        None
    }

    pub fn get_screen_resolution(&self, serial: &str) -> Option<(u32, u32)> {
        if let Ok(out) = self.run_adb(&["-s", serial, "shell", "wm", "size"]) {
            // Prioritize "Override size:" over "Physical size:" so active coordinate space is accurate
            let mut physical = None;
            let mut override_sz = None;
            for line in out.lines() {
                if let Some(pos) = line.find(':') {
                    let key = line[..pos].to_lowercase();
                    let size_str = line[pos + 1..].trim();
                    let parts: Vec<&str> = size_str.split('x').collect();
                    if parts.len() == 2 {
                        if let (Ok(w), Ok(h)) = (parts[0].trim().parse::<u32>(), parts[1].trim().parse::<u32>()) {
                            if key.contains("override") {
                                override_sz = Some((w, h));
                            } else {
                                physical = Some((w, h));
                            }
                        }
                    }
                }
            }
            return override_sz.or(physical);
        }
        None
    }

    pub fn get_ip_address(&self, serial: &str) -> Option<String> {
        if let Ok(out) = self.run_adb(&["-s", serial, "shell", "ip", "route"]) {
            for line in out.lines() {
                if line.contains("src ") {
                    let parts: Vec<&str> = line.split_whitespace().collect();
                    if let Some(pos) = parts.iter().position(|&r| r == "src") {
                        if let Some(ip) = parts.get(pos + 1) {
                            return Some(ip.to_string());
                        }
                    }
                }
            }
        }
        None
    }

    // ── Input & Control Methods ──────────────────────────────────────────

    pub fn tap(&self, serial: &str, x: u32, y: u32) -> Result<(), String> {
        // Fire-and-forget: no need to wait for tap result, saves ~300ms latency
        self.run_adb_nowait(&["-s", serial, "shell", "input", "tap", &x.to_string(), &y.to_string()]);
        Ok(())
    }

    pub fn swipe(&self, serial: &str, x1: u32, y1: u32, x2: u32, y2: u32, duration_ms: u32) -> Result<(), String> {
        // Fire-and-forget swipe — returns immediately, ADB handles timing internally
        self.run_adb_nowait(&[
            "-s", serial, "shell", "input", "swipe",
            &x1.to_string(), &y1.to_string(), &x2.to_string(), &y2.to_string(), &duration_ms.to_string()
        ]);
        Ok(())
    }

    pub fn keyevent(&self, serial: &str, keycode: u32) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "input", "keyevent", &keycode.to_string()]);
        Ok(())
    }

    pub fn input_text(&self, serial: &str, text: &str) -> Result<(), String> {
        let escaped = text.replace(' ', "%s").replace('&', "\\&").replace('\'', "\\'");
        self.run_adb_nowait(&["-s", serial, "shell", "input", "text", &escaped]);
        Ok(())
    }

    pub fn launch_app(&self, serial: &str, package: &str) -> Result<(), String> {
        self.run_adb(&["-s", serial, "shell", "monkey", "-p", package, "-c", "android.intent.category.LAUNCHER", "1"]).map(|_| ())
    }

    pub fn force_stop(&self, serial: &str, package: &str) -> Result<(), String> {
        self.run_adb(&["-s", serial, "shell", "am", "force-stop", package]).map(|_| ())
    }

    pub fn wake_up(&self, serial: &str) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "input", "keyevent", "224"]);
        self.run_adb_nowait(&["-s", serial, "shell", "input", "keyevent", "82"]);
        Ok(())
    }

    pub fn power_toggle(&self, serial: &str) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "input", "keyevent", "26"]);
        Ok(())
    }

    pub fn unlock(&self, serial: &str) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "input", "keyevent", "224"]);
        self.run_adb_nowait(&["-s", serial, "shell", "input", "keyevent", "82"]);
        self.swipe(serial, 360, 1000, 360, 300, 200)?;
        Ok(())
    }

    pub fn recents(&self, serial: &str) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "input", "keyevent", "187"]);
        Ok(())
    }

    pub fn volume_up(&self, serial: &str) -> Result<(), String> {
        self.keyevent(serial, 24) // KEYCODE_VOLUME_UP
    }

    pub fn volume_down(&self, serial: &str) -> Result<(), String> {
        self.keyevent(serial, 25) // KEYCODE_VOLUME_DOWN
    }

    pub fn scroll(&self, serial: &str, x: u32, y: u32, delta_y: i32) -> Result<(), String> {
        let x_safe = if x == 0 { 360 } else { x };
        let y_safe = if y == 0 { 740 } else { y };
        if delta_y > 0 {
            // Scroll down -> Swipe up
            let y_end = y_safe.saturating_sub(400).max(100);
            self.swipe(serial, x_safe, y_safe, x_safe, y_end, 180)
        } else {
            // Scroll up -> Swipe down
            let y_end = (y_safe + 400).min(1400);
            self.swipe(serial, x_safe, y_safe, x_safe, y_end, 180)
        }
    }

    pub fn install_apk(&self, serial: &str, apk_path: &Path) -> Result<(), String> {
        let path_str = apk_path.to_string_lossy().to_string();
        info!("Installing APK {} on device {}...", path_str, serial);
        self.run_adb(&["-s", serial, "install", "-r", "-d", "-g", &path_str]).map(|_| ())
    }

    pub fn is_app_installed(&self, serial: &str, package: &str) -> bool {
        if let Ok(out) = self.run_adb(&["-s", serial, "shell", "pm", "path", package]) {
            return out.contains("package:");
        }
        false
    }

    pub fn optimize_farm_device(&self, serial: &str) -> Result<(), String> {
        info!("Optimizing resolution & density for device {} (HD+ 720x1480)...", serial);
        let _ = self.run_adb(&["-s", serial, "shell", "wm", "size", "720x1480"]);
        let _ = self.run_adb(&["-s", serial, "shell", "wm", "density", "280"]);
        Ok(())
    }

    pub fn reset_farm_device(&self, serial: &str) -> Result<(), String> {
        info!("Resetting resolution & density for device {}...", serial);
        let _ = self.run_adb(&["-s", serial, "shell", "wm", "size", "reset"]);
        let _ = self.run_adb(&["-s", serial, "shell", "wm", "density", "reset"]);
        Ok(())
    }

    /// Chụp ảnh màn hình nhanh dạng PNG bytes
    pub fn capture_screen_raw(&self, serial: &str) -> Result<Vec<u8>, String> {
        let mut cmd = Command::new(&self.adb_path);
        cmd.args(["-s", serial, "exec-out", "screencap", "-p"]);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x08000000);
        }

        let output = cmd.output().map_err(|e| format!("screencap error: {}", e))?;
        if output.status.success() && !output.stdout.is_empty() {
            Ok(output.stdout)
        } else {
            Err("Failed to capture screen".to_string())
        }
    }

    // ── Wi-Fi Management Methods ─────────────────────────────────────────

    pub fn wifi_enable(&self, serial: &str) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "svc", "wifi", "enable"]);
        Ok(())
    }

    pub fn wifi_disable(&self, serial: &str) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "svc", "wifi", "disable"]);
        Ok(())
    }

    pub fn wifi_open_settings(&self, serial: &str) -> Result<(), String> {
        self.run_adb_nowait(&["-s", serial, "shell", "am", "start", "-a", "android.settings.WIFI_SETTINGS"]);
        Ok(())
    }

    pub fn wifi_scan(&self, serial: &str) -> Vec<WifiNetworkInfo> {
        let mut list = Vec::new();
        // 1. Check current connected SSID from dumpsys wifi
        let current_ssid = if let Ok(out) = self.run_adb(&["-s", serial, "shell", "dumpsys", "wifi"]) {
            let mut connected = String::new();
            for line in out.lines() {
                if line.contains("mWifiInfo") && line.contains("SSID:") {
                    if let Some(pos) = line.find("SSID:") {
                        let sub = &line[pos + 5..];
                        let parts: Vec<&str> = sub.split(',').collect();
                        if let Some(s) = parts.first() {
                            let trimmed = s.trim().trim_matches('"');
                            if trimmed != "<unknown ssid>" && !trimmed.is_empty() {
                                connected = trimmed.to_string();
                            }
                        }
                    }
                }
            }
            connected
        } else {
            String::new()
        };

        // 2. Scan via wpa_cli (root) or dumpsys scan results
        let scan_cmd = "su -c 'wpa_cli -i wlan0 scan >/dev/null 2>&1 && sleep 1 && wpa_cli -i wlan0 scan_results' || dumpsys wifi";
        if let Ok(out) = self.run_adb(&["-s", serial, "shell", scan_cmd]) {
            let mut seen_ssids = std::collections::HashSet::new();
            for line in out.lines() {
                let parts: Vec<&str> = line.split('\t').collect();
                if parts.len() >= 5 {
                    let bssid = parts[0].trim().to_string();
                    let freq = parts[1].trim().to_string();
                    let level: i32 = parts[2].trim().parse().unwrap_or(-80);
                    let flags = parts[3].trim().to_string();
                    let ssid = parts[4].trim().to_string();

                    if !ssid.is_empty() && !seen_ssids.contains(&ssid) {
                        seen_ssids.insert(ssid.clone());
                        let is_conn = !current_ssid.is_empty() && ssid == current_ssid;
                        let sec = if flags.contains("WPA2") || flags.contains("PSK") {
                            "WPA/WPA2"
                        } else if flags.contains("EAP") {
                            "802.1x EAP"
                        } else if flags.contains("WEP") {
                            "WEP"
                        } else {
                            "Open"
                        };
                        list.push(WifiNetworkInfo {
                            ssid,
                            bssid,
                            signal_level: level,
                            frequency: if freq.starts_with('5') { "5 GHz".into() } else { "2.4 GHz".into() },
                            security: sec.into(),
                            is_connected: is_conn,
                        });
                    }
                }
            }
        }

        // Sort: connected first, then by strongest signal
        list.sort_by(|a, b| {
            if a.is_connected != b.is_connected {
                b.is_connected.cmp(&a.is_connected)
            } else {
                b.signal_level.cmp(&a.signal_level)
            }
        });

        list
    }

    pub fn wifi_connect(&self, serial: &str, ssid: &str, password: &str) -> Result<(), String> {
        info!("Connecting device {} to Wi-Fi SSID: {}", serial, ssid);
        // Ensure wifi is enabled
        self.wifi_enable(serial)?;

        let cmd = if password.is_empty() {
            format!(
                "su -c 'ID=$(wpa_cli -i wlan0 add_network | tail -n 1); wpa_cli -i wlan0 set_network $ID ssid \"\\\"{}\\\"\"; wpa_cli -i wlan0 set_network $ID key_mgmt NONE; wpa_cli -i wlan0 enable_network $ID; wpa_cli -i wlan0 select_network $ID; wpa_cli -i wlan0 save_config'",
                ssid.replace('"', "\\\"")
            )
        } else {
            format!(
                "su -c 'ID=$(wpa_cli -i wlan0 add_network | tail -n 1); wpa_cli -i wlan0 set_network $ID ssid \"\\\"{}\\\"\"; wpa_cli -i wlan0 set_network $ID psk \"\\\"{}\\\"\"; wpa_cli -i wlan0 enable_network $ID; wpa_cli -i wlan0 select_network $ID; wpa_cli -i wlan0 save_config'",
                ssid.replace('"', "\\\""),
                password.replace('"', "\\\"")
            )
        };

        self.run_adb_nowait(&["-s", serial, "shell", &cmd]);
        Ok(())
    }
}

