use crate::adb_manager::AdbManager;
use rand::Rng;
use serde::{Deserialize, Serialize};
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tracing::info;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContainerMeta {
    #[serde(default, alias = "profile_name")]
    pub profile_id: String,
    #[serde(default)]
    pub serial: String,
    #[serde(default)]
    pub brand: String,
    #[serde(default)]
    pub model: String,
    #[serde(default)]
    pub imei: String,
    #[serde(default)]
    pub android_id: String,
    #[serde(default)]
    pub ssaid: String,
    #[serde(default)]
    pub created_at: String,
    #[serde(default)]
    pub data_size_mb: f64,
}

#[derive(Clone)]
pub struct FarmContainerEngine {
    adb: Arc<AdbManager>,
    containers_dir: PathBuf,
}

impl FarmContainerEngine {
    pub fn new(adb: Arc<AdbManager>) -> Self {
        let containers_dir = match std::env::current_exe() {
            Ok(p) => p.parent().unwrap_or(Path::new(".")).join("farm_device_containers"),
            Err(_) => PathBuf::from("farm_device_containers"),
        };
        let _ = fs::create_dir_all(&containers_dir);
        Self {
            adb,
            containers_dir,
        }
    }

    fn generate_hex16() -> String {
        let mut rng = rand::thread_rng();
        (0..16)
            .map(|_| {
                let idx = rng.gen_range(0..16);
                b"0123456789abcdef"[idx] as char
            })
            .collect()
    }

    /// Tái sinh một thiết bị: Cấp phát Android ID mới, đổi cấu hình phần cứng qua ATULAChanger, xóa sạch app
    pub async fn make_device_fresh(&self, serial: &str) -> Result<ContainerMeta, String> {
        info!("Rust Engine: Tái sinh danh tính phần cứng mới cho máy {}", serial);
        let app_pkg = "com.zhiliaoapp.musically";
        let maxchanger_pkg = "com.minsoftware.maxchanger";

        // 1. Dừng app
        let _ = self.adb.force_stop(serial, app_pkg);
        let _ = self.adb.force_stop(serial, maxchanger_pkg);

        // 2. Sinh Android ID ngẫu nhiên và gán trực tiếp vào hệ điều hành
        let new_aid = Self::generate_hex16();
        let cmd_aid = format!("su -c 'settings put secure android_id {}'", new_aid);
        let _ = self.run_shell(serial, &cmd_aid);

        // 3. Cập nhật SSAID trong settings_ssaid.xml cho com.zhiliaoapp.musically
        let ssaid_cmd = format!(
            "su -c \"grep -q 'package=\\\"{}\\\"' /data/system/users/0/settings_ssaid.xml && sed -i 's/name=\\\"10025\\\" value=\\\"[^\\\"]*\\\"/name=\\\"10025\\\" value=\\\"{}\\\"/g' /data/system/users/0/settings_ssaid.xml || true\"",
            app_pkg, new_aid
        );
        let _ = self.run_shell(serial, &ssaid_cmd);

        // 4. Mở ATULAChanger và bấm nút ATULA CHANGE INFO (x=360, y=1304)
        let _ = self.adb.launch_app(serial, &format!("{}/.MainActivity", maxchanger_pkg));
        tokio::time::sleep(tokio::time::Duration::from_millis(2000)).await;
        let _ = self.adb.tap(serial, 360, 1304);
        tokio::time::sleep(tokio::time::Duration::from_millis(2000)).await;

        // 5. Đọc lại thông số mới từ Device.xml
        let xml_out = self.run_shell(
            serial,
            &format!("su -c \"cat /data/data/{}/shared_prefs/Device.xml\"", maxchanger_pkg),
        ).unwrap_or_default();

        let brand = extract_xml_val(&xml_out, "brand").unwrap_or_else(|| "Google".to_string());
        let model = extract_xml_val(&xml_out, "model").unwrap_or_else(|| "Pixel".to_string());
        let imei = extract_xml_val(&xml_out, "imei").unwrap_or_else(|| "N/A".to_string());

        // 6. Xóa sạch dữ liệu cũ của TikTok và cache thẻ nhớ
        let _ = self.run_shell(serial, &format!("pm clear {}", app_pkg));
        let _ = self.run_shell(serial, &format!("su -c 'rm -rf /sdcard/Android/data/{}/* /sdcard/Android/media/{}/*'", app_pkg, app_pkg));
        let _ = self.run_shell(serial, "ime set com.android.adbkeyboard/.AdbIME");

        let meta = ContainerMeta {
            profile_id: format!("fresh_{}", &new_aid[..8]),
            serial: serial.to_string(),
            brand,
            model,
            imei,
            android_id: new_aid.clone(),
            ssaid: new_aid,
            created_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            data_size_mb: 0.0,
        };

        info!("Rust Engine: Tái sinh máy {} thành công: {} {} | AID: {}", serial, meta.brand, meta.model, meta.android_id);
        Ok(meta)
    }

    /// Đóng gói Nick hiện tại + Danh tính phần cứng thành 1 Container Profile riêng
    pub async fn export_profile(&self, serial: &str, profile_name: &str) -> Result<ContainerMeta, String> {
        info!("Rust Engine: Đang đóng gói Container Profile: {} cho máy {}", profile_name, serial);
        let app_pkg = "com.zhiliaoapp.musically";
        let maxchanger_pkg = "com.minsoftware.maxchanger";

        let prof_dir = self.containers_dir.join(profile_name);
        fs::create_dir_all(&prof_dir).map_err(|e| e.to_string())?;

        let _ = self.adb.force_stop(serial, app_pkg);
        tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;

        // 1. Kéo Device.xml
        let local_dev_xml = prof_dir.join("Device.xml");
        let remote_xml = format!("/data/data/{}/shared_prefs/Device.xml", maxchanger_pkg);
        let _ = self.adb_pull(serial, &remote_xml, &local_dev_xml);

        let xml_str = fs::read_to_string(&local_dev_xml).unwrap_or_default();
        let brand = extract_xml_val(&xml_str, "brand").unwrap_or_else(|| "Unknown".to_string());
        let model = extract_xml_val(&xml_str, "model").unwrap_or_else(|| "Unknown".to_string());
        let imei = extract_xml_val(&xml_str, "imei").unwrap_or_else(|| "N/A".to_string());
        let android_id = extract_xml_val(&xml_str, "android_id").unwrap_or_else(|| "".to_string());

        // 2. Đọc SSAID
        let ssaid_out = self.run_shell(serial, &format!("su -c \"grep '{}' /data/system/users/0/settings_ssaid.xml\"", app_pkg)).unwrap_or_default();
        let curr_ssaid = extract_regex(&ssaid_out, r#"value="([a-f0-9]+)""#).unwrap_or_default();

        // 3. Nén data.tar.gz sạch tối ưu (loại trừ thư viện .so và cache ML chỉ còn ~5.5MB)
        let _ = self.run_shell(serial, &format!("su -c \"find /data/data/{} -type s -delete && rm -rf /data/data/{}/cache/* /data/data/{}/files/offlineX /sdcard/tiktok_backups/*\"", app_pkg, app_pkg, app_pkg));
        let _ = self.run_shell(serial, &format!("su -c \"mkdir -p /sdcard/tiktok_backups && tar --exclude=files/zoin --exclude=files/Pitaya --exclude=files/applog -czf /sdcard/tiktok_backups/data.tar.gz -C /data/data/{} .\"", app_pkg));

        let local_tar = prof_dir.join("data.tar.gz");
        let _ = self.adb_pull(serial, "/sdcard/tiktok_backups/data.tar.gz", &local_tar);

        let size_mb = if local_tar.exists() {
            let metadata = fs::metadata(&local_tar).map_err(|e| e.to_string())?;
            (metadata.len() as f64) / (1024.0 * 1024.0)
        } else {
            0.0
        };

        let meta = ContainerMeta {
            profile_id: profile_name.to_string(),
            serial: serial.to_string(),
            brand,
            model,
            imei,
            android_id,
            ssaid: curr_ssaid,
            created_at: chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
            data_size_mb: (size_mb * 100.0).round() / 100.0,
        };

        let meta_json = serde_json::to_string_pretty(&meta).map_err(|e| e.to_string())?;
        fs::write(prof_dir.join("meta.json"), meta_json).map_err(|e| e.to_string())?;

        info!("Rust Engine: Đã đóng gói thành công Profile: {} ({} MB)", profile_name, meta.data_size_mb);
        Ok(meta)
    }

    /// Khôi phục chính xác danh tính thiết bị và Data của 1 Container Profile vào máy
    pub async fn switch_profile(&self, serial: &str, profile_name: &str) -> Result<ContainerMeta, String> {
        info!("Rust Engine: Đang khôi phục Profile [{}] vào thiết bị {}", profile_name, serial);
        let app_pkg = "com.zhiliaoapp.musically";
        let maxchanger_pkg = "com.minsoftware.maxchanger";

        let prof_dir = self.containers_dir.join(profile_name);
        if !prof_dir.exists() {
            return Err(format!("Profile '{}' không tồn tại", profile_name));
        }

        let _ = self.adb.force_stop(serial, app_pkg);
        tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

        // 1. Nạp Device.xml của Profile đó vào MaxChanger
        let dev_xml_path = prof_dir.join("Device.xml");
        if dev_xml_path.exists() {
            let _ = self.adb_push(serial, &dev_xml_path, "/sdcard/Device.xml");
            let uid_max = self.run_shell(serial, &format!("su -c \"stat -c '%u:%g' /data/data/{}/shared_prefs\"", maxchanger_pkg)).unwrap_or_default().trim().to_string();
            let _ = self.run_shell(serial, &format!(
                "su -c \"cp /sdcard/Device.xml /data/data/{}/shared_prefs/Device.xml && chown {} /data/data/{}/shared_prefs/Device.xml && chmod 660 /data/data/{}/shared_prefs/Device.xml\"",
                maxchanger_pkg, uid_max, maxchanger_pkg, maxchanger_pkg
            ));
        }

        // 2. Cập nhật SSAID và Android ID tương ứng
        let meta_file = prof_dir.join("meta.json");
        let meta: ContainerMeta = if meta_file.exists() {
            let data = fs::read_to_string(&meta_file).map_err(|e| e.to_string())?;
            serde_json::from_str(&data).map_err(|e| e.to_string())?
        } else {
            return Err("Không tìm thấy meta.json của Profile".to_string());
        };

        if !meta.ssaid.is_empty() {
            let ssaid_cmd = format!(
                "su -c \"grep -q 'package=\\\"{}\\\"' /data/system/users/0/settings_ssaid.xml && sed -i 's/name=\\\"10025\\\" value=\\\"[^\\\"]*\\\"/name=\\\"10025\\\" value=\\\"{}\\\"/g' /data/system/users/0/settings_ssaid.xml || true\"",
                app_pkg, meta.ssaid
            );
            let _ = self.run_shell(serial, &ssaid_cmd);
        }

        if !meta.android_id.is_empty() {
            let aid_cmd = format!("su -c 'settings put secure android_id {}'", meta.android_id);
            let _ = self.run_shell(serial, &aid_cmd);
        }

        // 3. Bung data.tar.gz vào app
        let tar_path = prof_dir.join("data.tar.gz");
        if tar_path.exists() {
            let _ = self.adb_push(serial, &tar_path, "/sdcard/data.tar.gz");
            let app_uid = self.run_shell(serial, &format!("su -c \"stat -c '%u:%g' /data/data/{}\"", app_pkg)).unwrap_or_default().trim().to_string();
            let uid_to_use = if app_uid.is_empty() { "10025:10025".to_string() } else { app_uid };
            let restore_cmd = format!(
                "su -c \"rm -rf /data/data/{0}/* && tar -xzf /sdcard/data.tar.gz -C /data/data/{0}/ && mkdir -p /data/data/{0}/files && cp -r /sdcard/zoin_dir /data/data/{0}/files/zoin && chown -R {1} /data/data/{0}/ && chmod -R 771 /data/data/{0}/ && chmod -R 775 /data/data/{0}/files\"",
                app_pkg, uid_to_use
            );
            let _ = self.run_shell(serial, &restore_cmd);
        }

        info!("Rust Engine: Khôi phục hoàn tất Profile [{}] trên máy {}!", profile_name, serial);
        Ok(meta)
    }

    /// Quét toàn bộ danh sách các Container Profile đang có trên hệ thống
    pub fn list_profiles(&self) -> Vec<ContainerMeta> {
        let mut profiles = Vec::new();
        if let Ok(entries) = fs::read_dir(&self.containers_dir) {
            for entry in entries.flatten() {
                if entry.path().is_dir() {
                    let meta_path = entry.path().join("meta.json");
                    if let Ok(content) = fs::read_to_string(&meta_path) {
                        if let Ok(meta) = serde_json::from_str::<ContainerMeta>(&content) {
                            profiles.push(meta);
                        }
                    }
                }
            }
        }
        profiles.sort_by(|a, b| b.created_at.cmp(&a.created_at));
        profiles
    }

    fn run_shell(&self, serial: &str, cmd: &str) -> Option<String> {
        let mut p = std::process::Command::new(self.adb.get_adb_path());
        p.args(["-s", serial, "shell", cmd]);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            p.creation_flags(0x08000000);
        }
        let output = p.output().ok()?;
        Some(String::from_utf8_lossy(&output.stdout).to_string())
    }

    fn adb_pull(&self, serial: &str, remote: &str, local: &Path) -> Result<(), String> {
        let mut p = std::process::Command::new(self.adb.get_adb_path());
        p.args(["-s", serial, "pull", remote, local.to_str().unwrap_or("")]);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            p.creation_flags(0x08000000);
        }
        let status = p.status().map_err(|e| e.to_string())?;
        if status.success() { Ok(()) } else { Err("ADB pull failed".to_string()) }
    }

    fn adb_push(&self, serial: &str, local: &Path, remote: &str) -> Result<(), String> {
        let mut p = std::process::Command::new(self.adb.get_adb_path());
        p.args(["-s", serial, "push", local.to_str().unwrap_or(""), remote]);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            p.creation_flags(0x08000000);
        }
        let status = p.status().map_err(|e| e.to_string())?;
        if status.success() { Ok(()) } else { Err("ADB push failed".to_string()) }
    }
}

fn extract_xml_val(xml: &str, key: &str) -> Option<String> {
    let pattern = format!(r#"<string name="{}">([^<]*)</string>"#, key);
    extract_regex(xml, &pattern)
}

fn extract_regex(text: &str, pattern: &str) -> Option<String> {
    let re = regex_lite_fallback(text, pattern)?;
    Some(re)
}

fn regex_lite_fallback(text: &str, pattern: &str) -> Option<String> {
    // Parser đơn giản cho XML <string name="KEY">VALUE</string>
    if pattern.contains("<string name=\"") {
        let key = pattern.split("name=\"").nth(1)?.split('"').next()?;
        let tag = format!("<string name=\"{}\">", key);
        let pos = text.find(&tag)?;
        let rest = &text[pos + tag.len()..];
        let end_pos = rest.find("</string>")?;
        return Some(rest[..end_pos].to_string());
    }
    if pattern.contains("value=\"") {
        let pos = text.find("value=\"")?;
        let rest = &text[pos + 7..];
        let end_pos = rest.find('"')?;
        return Some(rest[..end_pos].to_string());
    }
    None
}
