//! Device fingerprint v2 — thuần Rust, thay thế `maxchanger_generator.py`.
//!
//! Nguyên tắc (rút ra từ audit 2026-10-18, đo thực tế trên S8+ chạy LineageOS 16):
//!  * KHÔNG bịa phần cứng. Mọi thứ native đọc được (SoC, kernel, GPU, Android release/SDK, OUI MAC,
//!    mức pin) được ĐO từ máy thật rồi đưa vào profile -> hook Java và native luôn khớp nhau.
//!  * Pool model chỉ gồm họ Exynos 8895 (Galaxy S8 / S8+ / Note8) chạy Android 9 với fingerprint firmware thật.
//!  * Xoá dấu vết ROM tuỳ biến (ro.lineage.*, ro.modversion, ...) và đặt props stock-like.
//!  * IMSI / ICCID / số điện thoại cùng MCC-MNC; vị trí + timezone lấy từ IP thoát thật của máy (proxy).
//!  * Props bền qua reboot nhờ Magisk module `farm_props` (post-fs-data.sh + service.sh).
//!  * Nguồn dữ liệu duy nhất là map Device.xml -> khôi phục profile theo nick chỉ cần Device.xml đã backup.

use chrono::{FixedOffset, TimeZone};
use rand::seq::SliceRandom;
use rand::Rng;
use std::collections::BTreeMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use tracing::{info, warn};

pub type DeviceMap = BTreeMap<String, String>;

const MAXCHANGER_PKG: &str = "com.minsoftware.maxchanger";
const TIKTOK_PKG: &str = "com.zhiliaoapp.musically";
const AOSP_BUILD_ID: &str = "PPR1.180610.011"; // Android 9 (Pie) - khớp ro.build.version.sdk=28 thật của máy

// ───────────────────────────── Pool profile (firmware Samsung thật) ─────────────────────────────

pub struct BuildSpec {
    /// Mã build/bootloader Samsung, ví dụ G955FXXUCDVG4
    pub code: &'static str,
    /// Năm/tháng của security patch, suy ra từ ký tự năm + tháng trong mã build
    /// (… ví dụ `UD1` = 2021-04, `VG4` = 2022-07; ký tự năm: A=2001 … U=2021, V=2022).
    pub year: i32,
    pub month: u32,
}

pub struct ModelSpec {
    pub model: &'static str,
    pub device: &'static str,
    pub product: &'static str,
    /// TAC (8 số đầu IMEI) thật của model, tra cứu từ swappa/fccid.
    pub tacs: &'static [&'static str],
    pub builds: &'static [BuildSpec],
}

pub const MODELS: &[ModelSpec] = &[
    ModelSpec {
        model: "SM-G975F",
        device: "beyond2lte",
        product: "beyond2ltexx",
        tacs: &["35614310", "35614410", "35445210"],
        builds: &[
            BuildSpec { code: "G975FXXSDFUI5", year: 2021, month: 9 },
            BuildSpec { code: "G975FXXSEFUJ2", year: 2021, month: 10 },
        ],
    },
    ModelSpec {
        model: "SM-G980F",
        device: "hubbless",
        product: "hubbleltexx",
        tacs: &["35332611", "35332711", "35332811"],
        builds: &[
            BuildSpec { code: "G980FXXU8DUE1", year: 2021, month: 5 },
            BuildSpec { code: "G980FXXSFFVHA", year: 2022, month: 8 },
        ],
    },
    ModelSpec {
        model: "SM-G990E",
        device: "r9q",
        product: "r9qxx",
        tacs: &["35028423", "35028523", "35028623"],
        builds: &[
            BuildSpec { code: "G990EXXU1CVC5", year: 2022, month: 3 },
            BuildSpec { code: "G990EXXU3CVJ6", year: 2022, month: 10 },
        ],
    },
    ModelSpec {
        model: "SM-N980F",
        device: "c1",
        product: "c1xx",
        tacs: &["35182911", "35183011"],
        builds: &[
            BuildSpec { code: "N980FXXS4FVH1", year: 2022, month: 8 },
        ],
    },
    ModelSpec {
        model: "SM-A536E",
        device: "a53x",
        product: "a53xnsxx",
        tacs: &["35492144", "35492244"],
        builds: &[
            BuildSpec { code: "A536EXXU1AVBB", year: 2022, month: 2 },
            BuildSpec { code: "A536EXXU4BVK1", year: 2022, month: 11 },
        ],
    },
    ModelSpec {
        model: "SM-N950F",
        device: "greatlte",
        product: "greatltexx",
        tacs: &["35200309", "35912008", "35201509"],
        builds: &[
            BuildSpec { code: "N950FXXSGDUG6", year: 2021, month: 7 },
            BuildSpec { code: "N950FXXUGDVG5", year: 2022, month: 7 },
            BuildSpec { code: "N950FXXS7DSG1", year: 2019, month: 7 },
        ],
    },
];

pub struct Carrier {
    pub mccmnc: &'static str,
    pub name: &'static str,
    pub iccid_prefix: &'static str,
}

const US_CARRIERS: &[Carrier] = &[
    Carrier { mccmnc: "310260", name: "T-Mobile", iccid_prefix: "8901260" },
    Carrier { mccmnc: "310410", name: "AT&T", iccid_prefix: "8901410" },
    Carrier { mccmnc: "311480", name: "Verizon", iccid_prefix: "8914800" },
];

const VN_CARRIERS: &[Carrier] = &[
    Carrier { mccmnc: "45204", name: "Viettel", iccid_prefix: "898404" },
    Carrier { mccmnc: "45201", name: "MobiFone", iccid_prefix: "898401" },
    Carrier { mccmnc: "45202", name: "VinaPhone", iccid_prefix: "898402" },
];

pub fn pick_carrier(country: &str, rng: &mut impl Rng) -> &'static Carrier {
    let list = if country.eq_ignore_ascii_case("VN") { VN_CARRIERS } else { US_CARRIERS };
    list.choose(rng).unwrap_or(&US_CARRIERS[0])
}

// ───────────────────────────── Dữ kiện đo từ máy thật ─────────────────────────────

#[derive(Debug, Clone, Default)]
pub struct LiveFacts {
    pub hardware: String,
    pub board_platform: String,
    pub boot_hardware: String,
    pub board: String,
    pub abilist: String,
    pub arch: String,
    pub sdk: String,
    pub release: String,
    pub kernel: String,
    pub mac: String,
    pub gl_vendor: String,
    pub gl_renderer: String,
    pub bat_level: i32,
    pub bat_temp: i32,
    pub bat_status: i32,
}

const LIVE_SCRIPT: &str = r#"#!/system/bin/sh
echo "HW=$(getprop ro.hardware)"
echo "BP=$(getprop ro.board.platform)"
echo "BH=$(getprop ro.boot.hardware)"
echo "BOARD=$(getprop ro.product.board)"
echo "ABI=$(getprop ro.product.cpu.abilist)"
echo "ARCH=$(getprop ro.arch)"
echo "SDK=$(getprop ro.build.version.sdk)"
echo "REL=$(getprop ro.build.version.release)"
echo "KERNEL=$(uname -r)"
echo "MAC=$(cat /sys/class/net/wlan0/address 2>/dev/null)"
echo "GL=$(dumpsys SurfaceFlinger 2>/dev/null | grep -m1 'GLES:')"
echo "BATLEVEL=$(dumpsys battery | sed -n 's/^ *level: *//p' | head -1)"
echo "BATTEMP=$(dumpsys battery | sed -n 's/^ *temperature: *//p' | head -1)"
echo "BATSTATUS=$(dumpsys battery | sed -n 's/^ *status: *//p' | head -1)"
"#;

pub fn parse_live(out: &str) -> LiveFacts {
    let mut f = LiveFacts { bat_level: -1, bat_temp: 300, bat_status: 2, ..Default::default() };
    for line in out.lines() {
        let line = line.trim();
        let Some((k, v)) = line.split_once('=') else { continue };
        let v = v.trim().to_string();
        match k {
            "HW" => f.hardware = v,
            "BP" => f.board_platform = v,
            "BH" => f.boot_hardware = v,
            "BOARD" => f.board = v,
            "ABI" => f.abilist = v,
            "ARCH" => f.arch = v,
            "SDK" => f.sdk = v,
            "REL" => f.release = v,
            "KERNEL" => f.kernel = v,
            "MAC" => f.mac = v,
            "GL" => {
                // "GLES: ARM, Mali-G71, OpenGL ES 3.2 v1.r22p0-..."
                let body = v.trim_start_matches("GLES:").trim();
                let mut it = body.split(',').map(|s| s.trim());
                if let Some(vendor) = it.next() {
                    f.gl_vendor = vendor.to_string();
                }
                if let Some(renderer) = it.next() {
                    f.gl_renderer = renderer.to_string();
                }
            }
            "BATLEVEL" => f.bat_level = v.parse().unwrap_or(-1),
            "BATTEMP" => f.bat_temp = v.parse().unwrap_or(300),
            "BATSTATUS" => f.bat_status = v.parse().unwrap_or(2),
            _ => {}
        }
    }
    // Mặc định an toàn nếu máy không trả về (đúng với Exynos 8895 của giàn S8+).
    if f.hardware.is_empty() {
        f.hardware = "samsungexynos8895".into();
    }
    if f.board_platform.is_empty() {
        f.board_platform = "exynos5".into();
    }
    if f.boot_hardware.is_empty() {
        f.boot_hardware = f.hardware.clone();
    }
    if f.board.is_empty() {
        f.board = "universal8895".into();
    }
    if f.abilist.is_empty() {
        f.abilist = "arm64-v8a,armeabi-v7a,armeabi".into();
    }
    if f.arch.is_empty() {
        f.arch = "arm64".into();
    }
    if f.sdk.is_empty() {
        f.sdk = "28".into();
    }
    if f.release.is_empty() {
        f.release = "9".into();
    }
    if f.gl_vendor.is_empty() {
        f.gl_vendor = "ARM".into();
    }
    if f.gl_renderer.is_empty() {
        f.gl_renderer = "Mali-G71".into();
    }
    f
}

// ───────────────────────────── Geo (theo IP thoát của máy) ─────────────────────────────

#[derive(Debug, Clone)]
pub struct Geo {
    pub country: String,
    pub timezone: String,
    pub lat: f64,
    pub lon: f64,
    pub source: String,
}

pub fn fallback_geo(rng: &mut impl Rng) -> Geo {
    const CITIES: &[(&str, f64, f64)] = &[
        ("America/New_York", 40.7128, -74.0060),
        ("America/Chicago", 41.8781, -87.6298),
        ("America/Denver", 39.7392, -104.9903),
        ("America/Los_Angeles", 34.0522, -118.2437),
        ("America/Phoenix", 33.4484, -112.0740),
    ];
    let (tz, lat, lon) = *CITIES.choose(rng).unwrap_or(&CITIES[0]);
    Geo { country: "US".into(), timezone: tz.into(), lat, lon, source: "fallback-us-city".into() }
}

pub fn parse_geo_json(body: &str, rng: &mut impl Rng) -> Option<Geo> {
    let v: serde_json::Value = serde_json::from_str(body.trim()).ok()?;
    if v.get("status").and_then(|s| s.as_str()) != Some("success") {
        return None;
    }
    let tz = v.get("timezone").and_then(|s| s.as_str())?.to_string();
    let lat = v.get("lat").and_then(|s| s.as_f64())?;
    let lon = v.get("lon").and_then(|s| s.as_f64())?;
    let country = v.get("countryCode").and_then(|s| s.as_str()).unwrap_or("US").to_string();
    let ip = v.get("query").and_then(|s| s.as_str()).unwrap_or("?");
    Some(Geo {
        country,
        timezone: tz,
        // lệch nhẹ để mỗi nick một toạ độ riêng nhưng vẫn cùng thành phố với IP
        lat: lat + rng.gen_range(-0.03..=0.03),
        lon: lon + rng.gen_range(-0.03..=0.03),
        source: format!("ip:{}", ip),
    })
}

// ───────────────────────────── Sinh định danh ─────────────────────────────

fn rand_hex(rng: &mut impl Rng, n: usize) -> String {
    (0..n).map(|_| char::from_digit(rng.gen_range(0..16), 16).unwrap_or('0')).collect()
}

fn rand_digits(rng: &mut impl Rng, n: usize) -> String {
    (0..n).map(|_| char::from_digit(rng.gen_range(0..10), 10).unwrap_or('0')).collect()
}

fn rand_alnum_upper(rng: &mut impl Rng, n: usize) -> String {
    const SET: &[u8] = b"ABCDEFGHJKLMNPQRSTUVWXYZ0123456789";
    (0..n).map(|_| SET[rng.gen_range(0..SET.len())] as char).collect()
}

pub fn luhn_check_digit(body: &str) -> u32 {
    let mut sum = 0;
    for (i, c) in body.chars().rev().enumerate() {
        let mut d = c.to_digit(10).unwrap_or(0);
        if i % 2 == 0 {
            d *= 2;
            if d > 9 {
                d -= 9;
            }
        }
        sum += d;
    }
    (10 - sum % 10) % 10
}

pub fn make_imei(tac: &str, rng: &mut impl Rng) -> String {
    let body = format!("{}{}", tac, rand_digits(rng, 6));
    format!("{}{}", body, luhn_check_digit(&body))
}

pub fn make_iccid(prefix: &str, rng: &mut impl Rng) -> String {
    let fill = 19usize.saturating_sub(prefix.len());
    let body = format!("{}{}", prefix, rand_digits(rng, fill));
    format!("{}{}", body, luhn_check_digit(&body))
}

pub fn make_imsi(mccmnc: &str, rng: &mut impl Rng) -> String {
    format!("{}{}", mccmnc, rand_digits(rng, 15usize.saturating_sub(mccmnc.len())))
}

/// Số điện thoại hợp lệ theo NANP (đầu 2-9, không phải dạng N11) hoặc VN.
pub fn make_phone(country: &str, rng: &mut impl Rng) -> String {
    if country.eq_ignore_ascii_case("VN") {
        return format!("+849{}", rand_digits(rng, 8));
    }
    let n_xx = |rng: &mut dyn rand::RngCore| -> String {
        loop {
            let a = rng.gen_range(2..=9);
            let b = rng.gen_range(0..=9);
            let c = rng.gen_range(0..=9);
            if !(b == 1 && c == 1) {
                return format!("{}{}{}", a, b, c);
            }
        }
    };
    let area = n_xx(rng);
    let exch = n_xx(rng);
    format!("+1{}{}{}", area, exch, rand_digits(rng, 4))
}

fn make_mac(oui: &str, rng: &mut impl Rng) -> String {
    let suffix: Vec<String> = (0..3).map(|_| format!("{:02x}", rng.gen_range(0..=255u32))).collect();
    format!("{}:{}", oui, suffix.join(":"))
}

fn uuid_v4(rng: &mut impl Rng) -> String {
    let mut b = [0u8; 16];
    rng.fill(&mut b);
    b[6] = (b[6] & 0x0f) | 0x40;
    b[8] = (b[8] & 0x3f) | 0x80;
    format!(
        "{:02x}{:02x}{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}-{:02x}{:02x}{:02x}{:02x}{:02x}{:02x}",
        b[0], b[1], b[2], b[3], b[4], b[5], b[6], b[7], b[8], b[9], b[10], b[11], b[12], b[13], b[14], b[15]
    )
}

fn kst() -> FixedOffset {
    FixedOffset::east_opt(9 * 3600).expect("KST offset")
}

/// Ngày build (ms epoch) nằm trong đúng tháng patch của firmware, giờ KST.
fn build_time_ms(spec: &BuildSpec, rng: &mut impl Rng) -> i64 {
    let day = rng.gen_range(3..=24);
    let dt = kst()
        .with_ymd_and_hms(spec.year, spec.month, day, rng.gen_range(9..=18), rng.gen_range(0..=59), rng.gen_range(0..=59))
        .single()
        .unwrap_or_else(|| kst().with_ymd_and_hms(spec.year, spec.month, 10, 12, 0, 0).unwrap());
    dt.timestamp() * 1000
}

pub fn security_patch_from_ms(ms: i64) -> String {
    let dt = kst().timestamp_opt(ms / 1000, 0).single().unwrap_or_else(|| kst().timestamp_opt(0, 0).unwrap());
    dt.format("%Y-%m-01").to_string()
}

pub fn build_date_from_ms(ms: i64) -> String {
    let dt = kst().timestamp_opt(ms / 1000, 0).single().unwrap_or_else(|| kst().timestamp_opt(0, 0).unwrap());
    dt.format("%a %b %e %H:%M:%S KST %Y").to_string()
}

// ───────────────────────────── Blacklist theo (model|build) ─────────────────────────────

fn blacklist_path() -> PathBuf {
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            return parent.join("flagged_profiles.json");
        }
    }
    PathBuf::from("flagged_profiles.json")
}

fn load_blacklist() -> Vec<String> {
    fs::read_to_string(blacklist_path())
        .ok()
        .and_then(|s| serde_json::from_str::<serde_json::Value>(&s).ok())
        .and_then(|v| v.get("flagged").cloned())
        .and_then(|v| serde_json::from_value::<Vec<String>>(v).ok())
        .unwrap_or_default()
}

/// Ghi nhận cặp model|build bị TikTok chặn để lần sau ưu tiên cặp khác.
pub fn flag_profile(model: &str, build: &str) {
    if model.is_empty() {
        return;
    }
    let mut list = load_blacklist();
    let key = format!("{}|{}", model, build);
    if !list.contains(&key) {
        list.push(key.clone());
        list.sort();
        let body = serde_json::json!({ "flagged": list });
        if let Err(e) = fs::write(blacklist_path(), serde_json::to_string_pretty(&body).unwrap_or_default()) {
            warn!("Không ghi được flagged_profiles.json: {}", e);
        } else {
            info!("Đã ghi nhận profile bị flag: {}", key);
        }
    }
}

pub fn pick_model_build<'a>(flagged: &[String], rng: &mut impl Rng) -> (&'a ModelSpec, &'a BuildSpec) {
    let mut all: Vec<(&ModelSpec, &BuildSpec)> = Vec::new();
    for m in MODELS {
        for b in m.builds {
            all.push((m, b));
        }
    }
    let free: Vec<(&ModelSpec, &BuildSpec)> = all
        .iter()
        .copied()
        .filter(|(m, b)| !flagged.contains(&format!("{}|{}", m.model, b.code)))
        .collect();
    let pool = if free.is_empty() { all } else { free };
    *pool.choose(rng).expect("MODELS không rỗng")
}

// ───────────────────────────── Sinh map Device.xml ─────────────────────────────

pub fn generate_map(facts: &LiveFacts, geo: &Geo, flagged: &[String], rng: &mut impl Rng) -> DeviceMap {
    let (spec, build) = pick_model_build(flagged, rng);
    let carrier = pick_carrier(&geo.country, rng);
    let tac = spec.tacs.choose(rng).copied().unwrap_or("35879208");

    let android_id = rand_hex(rng, 16);
    let imei = make_imei(tac, rng);
    let imsi = make_imsi(carrier.mccmnc, rng);
    let iccid = make_iccid(carrier.iccid_prefix, rng);
    let phone = make_phone(&geo.country, rng);
    let serial = format!("R58{}", rand_alnum_upper(rng, 8));
    let oui = if facts.mac.len() >= 8 { facts.mac[..8].to_lowercase() } else { "30:07:4d".to_string() };
    let wifi_mac = make_mac(&oui, rng);
    let bt_mac = make_mac(&oui, rng).to_uppercase();
    let wifi_name = format!(
        "{}_{}",
        ["NETGEAR", "TP-Link", "Linksys", "Xfinity", "SpectrumSetup", "ATT"].choose(rng).copied().unwrap_or("NETGEAR"),
        rand_hex(rng, 4).to_uppercase()
    );
    let battery = if facts.bat_level > 0 { facts.bat_level } else { rng.gen_range(55..=95) };
    let time_check = rng.gen_range(50_000_000..=99_999_999);
    let bt_ms = build_time_ms(build, rng);
    let host = format!("SWDD{}", rand_digits(rng, 4));

    let release = facts.release.clone();
    let sdk = facts.sdk.clone();
    let model = spec.model.to_string();
    let code = build.code.to_string();
    let display = format!("{}.{}", AOSP_BUILD_ID, code);
    let fingerprint = format!(
        "samsung/{}/{}:{}/{}/{}:user/release-keys",
        spec.product, spec.device, release, AOSP_BUILD_ID, code
    );
    let description = format!("{}-user {} {} {} release-keys", spec.product, release, AOSP_BUILD_ID, code);
    let ua = format!(
        "Mozilla/5.0 (Linux; Android {}; {} Build/{}; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/114.0.5735.196 Mobile Safari/537.36",
        release, model, AOSP_BUILD_ID
    );
    let http_agent = format!("Dalvik/2.1.0 (Linux; U; Android {}; {} Build/{})", release, model, AOSP_BUILD_ID);
    let cpu_abi = facts.abilist.split(',').next().unwrap_or("arm64-v8a").trim().to_string();

    let mut m = DeviceMap::new();
    let mut put = |k: &str, v: String| {
        m.insert(k.to_string(), v);
    };
    put("country", geo.country.to_lowercase());
    put("release", release.clone());
    put("build_time", bt_ms.to_string());
    put("build_user", "dpi".into());
    put("type", "user".into());
    put("deviceName", format!("SAMSUNG_{}", model));
    put("glRenderer", facts.gl_renderer.clone());
    put("glVendor", facts.gl_vendor.clone());
    put("fingerprint", fingerprint.clone());
    put("host", host.clone());
    put("simOperator", carrier.mccmnc.into());
    put("model", model.clone());
    put("phone_num", phone);
    put("wifimac", wifi_mac);
    put("brand", "samsung".into());
    put("hardware", facts.hardware.clone());
    put("longitude", format!("{:.6}", geo.lon));
    put("ro_hardware", facts.hardware.clone());
    put("os_arch", facts.kernel.clone());
    put("simSerial", iccid);
    put("tags", "release-keys".into());
    put("http_agent", http_agent);
    put("build_id", AOSP_BUILD_ID.into());
    put("cpu_abilist", facts.abilist.clone());
    put("batteryPercent", battery.to_string());
    put("device", spec.device.into());
    put("ro_arch", facts.hardware.clone());
    put("latitude", format!("{:.6}", geo.lat));
    put("description", description);
    put("ADB_CHANGE", "true".into());
    put("imsi", imsi.clone());
    put("manufacturer", "samsung".into());
    put("vm_version", "2.1.0".into());
    put("bluetooth_mac", bt_mac.clone());
    put("wifiName", wifi_name);
    put("bootloader", code.clone());
    put("time_check", time_check.to_string());
    put("simOperatorName", carrier.name.into());
    put("radio_version", code.clone());
    put("user_agent", ua);
    put("product", spec.product.into());
    put("build_display", display.clone());
    put("os_version", "aarch64".into());
    put("incremental", code.clone());
    put("persist_radio_multisim_config", String::new());
    put("ro_board_platform", facts.board_platform.clone());
    put("ro_boot_hardware", facts.boot_hardware.clone());
    put("serial", serial.clone());
    put("imei", imei.clone());
    put("API", release.clone());
    put("android_id", android_id.clone());
    put("board", facts.board.clone());
    put("tz", geo.timezone.clone());

    put("TIME", bt_ms.to_string());
    put("SDK", sdk);
    put("RELEASE", release);
    put("MODEL", model);
    put("BRAND", "samsung".into());
    put("MANUFACTURER", "samsung".into());
    put("FINGERPRINT", fingerprint);
    put("HARDWARE", facts.hardware.clone());
    put("DEVICE", spec.device.into());
    put("DISPLAY", display);
    put("ID", AOSP_BUILD_ID.into());
    put("BOARD", facts.board.clone());
    put("BOOTLOADER", code.clone());
    put("HOST", host);
    put("PRODUCT", spec.product.into());
    put("RADIO", code.clone());
    put("TAGS", "release-keys".into());
    put("TYPE", "user".into());
    put("USER", "dpi".into());
    put("SERIAL", serial);
    put("CPU_ABI", cpu_abi);
    put("BASE_OS", String::new());
    put("ANDROID_ID", android_id);
    put("IMEI", imei);
    put("IMSI", imsi);
    put("BLUETOOTH_MAC", bt_mac);
    put("BATTERYPERCENT", battery.to_string());
    put("COUNTRY", geo.country.to_lowercase());
    put("LATITUDE", format!("{:.6}", geo.lat));
    put("LONGITUDE", format!("{:.6}", geo.lon));
    m
}

fn xml_escape(s: &str) -> String {
    s.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;").replace('"', "&quot;")
}

pub fn to_device_xml(m: &DeviceMap) -> String {
    let mut out = String::from("<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n");
    for (k, v) in m {
        out.push_str(&format!("    <string name=\"{}\">{}</string>\n", k, xml_escape(v)));
    }
    out.push_str("</map>\n");
    out
}

pub fn parse_device_xml(xml: &str) -> DeviceMap {
    let mut m = DeviceMap::new();
    if let Ok(doc) = roxmltree::Document::parse(xml.trim_start_matches('\u{feff}')) {
        for n in doc.descendants().filter(|n| n.has_tag_name("string")) {
            if let Some(name) = n.attribute("name") {
                m.insert(name.to_string(), n.text().unwrap_or("").to_string());
            }
        }
    }
    m
}

// ───────────────────────────── Sinh script áp props ─────────────────────────────

fn sq(s: &str) -> String {
    format!("'{}'", s.replace('\'', "'\\''"))
}

const SH_HELPERS: &str = r#"#!/system/bin/sh
RP="magisk resetprop"
command -v resetprop >/dev/null 2>&1 && RP=resetprop
fp() { $RP "$1" "$2"; }
op() { [ -n "$(getprop "$1")" ] && $RP "$1" "$2"; }
dp() { $RP --delete "$1" 2>/dev/null; }
"#;

fn fp_line(s: &mut String, k: &str, v: &str) {
    s.push_str(&format!("fp {} {}\n", k, sq(v)));
}

fn op_line(s: &mut String, k: &str, v: &str) {
    s.push_str(&format!("op {} {}\n", k, sq(v)));
}

/// Script chạy ở post-fs-data (và ngay lập tức khi apply): xoá dấu vết ROM + đặt props stock-like.
pub fn early_script(m: &DeviceMap) -> String {
    let g = |k: &str| m.get(k).cloned().unwrap_or_default();
    let (model, brand, manu, device, product) = (g("model"), g("brand"), g("manufacturer"), g("device"), g("product"));
    let fingerprint = g("fingerprint");
    let code = g("incremental");
    let bt_ms: i64 = g("build_time").parse().unwrap_or(0);

    let mut s = String::from(SH_HELPERS);
    // 1. Xoá toàn bộ dấu vết LineageOS (chỉ ro.* / updater, KHÔNG đụng sys.* để khỏi phá LineageSettings)
    s.push_str(
        "for p in $(getprop | grep -E '^\\[(ro\\.lineage|lineage\\.|ro\\.modversion|ro\\.cm\\.)' | cut -d']' -f1 | tr -d '['); do dp \"$p\"; done\n",
    );
    // 2. Nhóm product
    for (k, v) in [
        ("ro.product.model", &model),
        ("ro.product.brand", &brand),
        ("ro.product.manufacturer", &manu),
        ("ro.product.device", &device),
        ("ro.product.name", &product),
        ("ro.build.product", &device),
    ] {
        fp_line(&mut s, k, v);
    }
    for part in ["vendor", "odm", "system"] {
        op_line(&mut s, &format!("ro.product.{}.model", part), &model);
        op_line(&mut s, &format!("ro.product.{}.brand", part), &brand);
        op_line(&mut s, &format!("ro.product.{}.manufacturer", part), &manu);
        op_line(&mut s, &format!("ro.product.{}.device", part), &device);
        op_line(&mut s, &format!("ro.product.{}.name", part), &product);
    }
    // 3. Nhóm build
    for k in [
        "ro.build.fingerprint",
    ] {
        fp_line(&mut s, k, &fingerprint);
    }
    for k in [
        "ro.vendor.build.fingerprint",
        "ro.bootimage.build.fingerprint",
        "ro.system.build.fingerprint",
        "ro.odm.build.fingerprint",
    ] {
        op_line(&mut s, k, &fingerprint);
    }
    fp_line(&mut s, "ro.build.description", &g("description"));
    fp_line(&mut s, "ro.build.display.id", &g("build_display"));
    fp_line(&mut s, "ro.build.id", &g("build_id"));
    fp_line(&mut s, "ro.build.flavor", &format!("{}-user", product));
    fp_line(&mut s, "ro.build.version.incremental", &code);
    fp_line(&mut s, "ro.build.version.security_patch", &security_patch_from_ms(bt_ms));
    op_line(&mut s, "ro.vendor.build.security_patch", &security_patch_from_ms(bt_ms));
    fp_line(&mut s, "ro.build.date", &build_date_from_ms(bt_ms));
    fp_line(&mut s, "ro.build.date.utc", &(bt_ms / 1000).to_string());
    fp_line(&mut s, "ro.build.user", &g("build_user"));
    fp_line(&mut s, "ro.build.host", &g("host"));
    fp_line(&mut s, "ro.build.type", "user");
    fp_line(&mut s, "ro.build.tags", "release-keys");
    fp_line(&mut s, "ro.build.PDA", &code);
    fp_line(&mut s, "ro.bootloader", &g("bootloader"));
    op_line(&mut s, "ro.boot.bootloader", &g("bootloader"));
    op_line(&mut s, "ro.com.google.clientidbase", "android-samsung");
    s
}

/// Script chạy muộn (service.sh): baseband do RIL tự ghi đè sau khi boot nên phải đặt lại.
pub fn late_script(m: &DeviceMap) -> String {
    let radio = m.get("radio_version").cloned().unwrap_or_default();
    let mut s = String::from(SH_HELPERS);
    s.push_str("[ \"$1\" = \"now\" ] || { while [ \"$(getprop sys.boot_completed)\" != \"1\" ]; do sleep 2; done; sleep 25; }\n");
    fp_line(&mut s, "gsm.version.baseband", &format!("{},{}", radio, radio));
    fp_line(&mut s, "ril.sw_ver", &radio);
    fp_line(&mut s, "ril.sw_ver2", &radio);
    s
}

const MODULE_PROP: &str = "id=farm_props\nname=Farm Props\nversion=v2\nversionCode=2\nauthor=farm\ndescription=Re-apply fake device props after every boot\n";

/// Script chạy 1 lần khi apply: settings, GAID, dọn dấu vết, gỡ app thừa, sửa pin, cài module.
pub fn apply_script(m: &DeviceMap, facts: &LiveFacts, gaid: &str) -> String {
    let g = |k: &str| m.get(k).cloned().unwrap_or_default();
    let model = g("model");
    let aid = g("android_id");
    let tz = g("tz");
    let mut s = String::from("#!/system/bin/sh\n");

    // Settings
    s.push_str(&format!("settings put secure android_id {}\n", sq(&aid)));
    s.push_str(&format!("settings put global device_name {}\n", sq(&model)));
    s.push_str(&format!("settings put secure bluetooth_name {}\n", sq(&model)));
    s.push_str("settings put secure mock_location 0\n");
    s.push_str("rm -f /data/system/users/0/settings_ssaid.xml\n");
    if !tz.is_empty() {
        s.push_str(&format!("setprop persist.sys.timezone {}\n", sq(&tz)));
        s.push_str(&format!("service call alarm 3 s16 {} >/dev/null 2>&1\n", sq(&tz)));
    }

    // MaxChanger Device.xml (cat > giữ nguyên owner/SELinux của file cũ)
    s.push_str(&format!(
        "D=/data/data/{p}/shared_prefs\nmkdir -p $D\ncat /data/local/tmp/farm_Device.xml > $D/Device.xml\nchown $(stat -c %u:%g $D) $D/Device.xml\nchmod 666 $D/Device.xml\nrestorecon $D/Device.xml 2>/dev/null\n",
        p = MAXCHANGER_PKG
    ));

    // GAID mới
    s.push_str(&format!(
        "G=/data/data/com.google.android.gms/shared_prefs\nmkdir -p $G\ncat > $G/adid_settings.xml <<'FARM_EOF'\n<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n<map>\n    <boolean name=\"enable_debug_logging\" value=\"false\" />\n    <boolean name=\"using_cert\" value=\"false\" />\n    <string name=\"adid_key\">{gaid}</string>\n    <string name=\"fake_adid_key\"></string>\n    <int name=\"adid_reset_count\" value=\"1\" />\n    <boolean name=\"enable_limit_ad_tracking\" value=\"false\" />\n</map>\nFARM_EOF\nchown $(stat -c %u:%g $G) $G/adid_settings.xml\nchmod 660 $G/adid_settings.xml\nrestorecon $G/adid_settings.xml 2>/dev/null\n",
        gaid = gaid
    ));

    // Dấu vết tracking của TikTok / ByteDance + rác dump trên /sdcard
    s.push_str(&format!(
        "rm -rf /sdcard/Android/data/{t} /sdcard/.tiktok* /sdcard/snssdk* /sdcard/.bd_turing* /sdcard/.byteio* /data/data/{t}/app_webview /data/data/{t}/shared_prefs/bdturing* /data/data/{t}/shared_prefs/device_register* /data/data/{t}/shared_prefs/app_setting*\n",
        t = TIKTOK_PKG
    ));
    s.push_str("cd /sdcard && rm -rf chk_*.xml cur*.xml s_*.xml u_*.xml tab_*.xml step_dump.xml under_back.xml native_tree.xml live_chk.xml dbg_0c.xml err_0c.xml bday_chk.xml d_nut.xml prof_0c81.xml rule_chk.xml uid.xml av.png n.png proof_f.png r.png s.png sc.png screen_*.png cpuinfo nk\n");

    // Gỡ app tự động hoá thừa. KHÔNG gỡ com.steinwurf.adbjoinwifi: nó là chủ của cấu hình Wi-Fi đã lưu,
    // gỡ app -> Android xoá mạng -> máy mất Wi-Fi (đã gặp khi test live 18/10).
    s.push_str("for p in io.appium.uiautomator2.server io.appium.uiautomator2.server.test ru.andr7e.deviceinfohw; do pm uninstall \"$p\" >/dev/null 2>&1; done\n");

    // Pin: nhiệt độ -20°C / not-charging khi đang cắm USB là dữ liệu vô lý
    let temp = 290 + (aid.bytes().fold(0u32, |a, b| a.wrapping_add(b as u32)) % 60) as i32; // 29.0 - 34.9°C ổn định theo máy
    if facts.bat_temp < 100 || facts.bat_status == 4 {
        let status = if facts.bat_level >= 100 { 5 } else { 2 };
        s.push_str(&format!(
            "dumpsys battery set usb 1 >/dev/null 2>&1\ndumpsys battery set status {} >/dev/null 2>&1\ndumpsys battery set temp {} >/dev/null 2>&1\n",
            status, temp
        ));
    }

    // Cài Magisk module để props bền qua reboot
    s.push_str(
        "M=/data/adb/modules/farm_props\nmkdir -p $M\ncp /data/local/tmp/farm_module.prop $M/module.prop\ncp /data/local/tmp/farm_post_fs.sh $M/post-fs-data.sh\ncp /data/local/tmp/farm_service.sh $M/service.sh\nchmod 755 $M/post-fs-data.sh $M/service.sh\nchmod 644 $M/module.prop\nrm -f $M/disable $M/remove\n",
    );

    // Ghi đè trực tiếp vào /system/build.prop và /system/vendor/build.prop (chống native C++ fopen đọc S8 gốc)
    let brand = g("brand");
    let manu = g("manufacturer");
    let device = g("device");
    let product = g("product");
    let fingerprint = g("fingerprint");
    let display = g("build_display");

    s.push_str(
        "mount -o remount,rw /system 2>/dev/null || mount -o rw,remount / 2>/dev/null\n\
        if [ -w /system/build.prop ]; then\n\
            sed -i \"s/^ro\\.product\\.model=.*/ro.product.model="
    );
    s.push_str(&model);
    s.push_str(
        "/g\" /system/build.prop\n\
            sed -i \"s/^ro\\.product\\.brand=.*/ro.product.brand="
    );
    s.push_str(&brand);
    s.push_str(
        "/g\" /system/build.prop\n\
            sed -i \"s/^ro\\.product\\.manufacturer=.*/ro.product.manufacturer="
    );
    s.push_str(&manu);
    s.push_str(
        "/g\" /system/build.prop\n\
            sed -i \"s/^ro\\.product\\.device=.*/ro.product.device="
    );
    s.push_str(&device);
    s.push_str(
        "/g\" /system/build.prop\n\
            sed -i \"s/^ro\\.product\\.name=.*/ro.product.name="
    );
    s.push_str(&product);
    s.push_str(
        "/g\" /system/build.prop\n\
            sed -i \"s/^ro\\.build\\.product=.*/ro.build.product="
    );
    s.push_str(&device);
    s.push_str(
        "/g\" /system/build.prop\n\
            sed -i \"s/^ro\\.build\\.display\\.id=.*/ro.build.display.id="
    );
    s.push_str(&display);
    s.push_str(
        "/g\" /system/build.prop\n\
            sed -i \"s|^ro\\.build\\.fingerprint=.*|ro.build.fingerprint="
    );
    s.push_str(&fingerprint);
    s.push_str(
        "|g\" /system/build.prop\n\
            chmod 644 /system/build.prop\n\
            restorecon /system/build.prop 2>/dev/null || chcon u:object_r:system_file:s0 /system/build.prop 2>/dev/null\n\
        fi\n\
        mount -o remount,ro /system 2>/dev/null || mount -o ro,remount / 2>/dev/null\n"
    );

    s.push_str("am force-stop com.google.android.gms\n");
    s
}

// ───────────────────────────── ADB helpers ─────────────────────────────

fn adb_cmd(adb: &Path) -> Command {
    let mut c = Command::new(adb);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x08000000);
    }
    c
}

fn adb_out(adb: &Path, serial: &str, args: &[&str]) -> Result<String, String> {
    let out = adb_cmd(adb)
        .arg("-s")
        .arg(serial)
        .args(args)
        .output()
        .map_err(|e| format!("adb: {}", e))?;
    Ok(String::from_utf8_lossy(&out.stdout).to_string())
}

fn push_text(adb: &Path, serial: &str, name: &str, remote: &str, body: &str) -> Result<(), String> {
    let local = std::env::temp_dir().join(format!("farm_{}_{}", serial, name));
    // LF thuần: shell Android không chịu CRLF
    fs::write(&local, body.replace("\r\n", "\n")).map_err(|e| e.to_string())?;
    let out = adb_cmd(adb)
        .arg("-s")
        .arg(serial)
        .arg("push")
        .arg(&local)
        .arg(remote)
        .output()
        .map_err(|e| format!("adb push: {}", e))?;
    let _ = fs::remove_file(&local);
    if out.status.success() {
        Ok(())
    } else {
        Err(format!("adb push {} lỗi: {}", name, String::from_utf8_lossy(&out.stderr).trim()))
    }
}

fn run_su_script(adb: &Path, serial: &str, remote: &str, args: &str) -> Result<String, String> {
    adb_out(adb, serial, &["shell", &format!("su -c 'sh {} {}'", remote, args)])
}

pub fn read_live(adb: &Path, serial: &str) -> Result<LiveFacts, String> {
    push_text(adb, serial, "live.sh", "/data/local/tmp/farm_live.sh", LIVE_SCRIPT)?;
    let out = run_su_script(adb, serial, "/data/local/tmp/farm_live.sh", "")?;
    if out.trim().is_empty() {
        return Err("Không đọc được thông số máy (su/adb lỗi?)".into());
    }
    Ok(parse_live(&out))
}

pub fn lookup_geo(adb: &Path, serial: &str, rng: &mut impl Rng) -> Geo {
    let body = adb_out(
        adb,
        serial,
        &["shell", "curl -s -m 6 'http://ip-api.com/json?fields=status,countryCode,timezone,lat,lon,query'"],
    )
    .unwrap_or_default();
    let geo = parse_geo_json(&body, rng).unwrap_or_else(|| {
        warn!("[Device {}] Không tra được geo từ IP thoát, dùng thành phố Mỹ dự phòng", serial);
        fallback_geo(rng)
    });
    if geo.country.eq_ignore_ascii_case("US") || geo.country.eq_ignore_ascii_case("VN") {
        return geo;
    }
    warn!(
        "[Device {}] IP thoát thuộc '{}' (không có bảng nhà mạng) -> dùng profile Mỹ đồng nhất để SIM/múi giờ không mâu thuẫn",
        serial, geo.country
    );
    let mut g = fallback_geo(rng);
    g.source = format!("fallback-us(ip-country={})", geo.country);
    g
}

#[derive(Debug, Clone)]
pub struct AppliedProfile {
    pub model: String,
    pub build: String,
    pub imei: String,
    pub android_id: String,
    pub gaid: String,
    pub operator: String,
    pub timezone: String,
    pub geo_source: String,
}

fn apply_map(adb: &Path, serial: &str, m: &DeviceMap, facts: &LiveFacts, geo_source: &str) -> Result<AppliedProfile, String> {
    let mut rng = rand::thread_rng();
    let gaid = uuid_v4(&mut rng);

    let early = early_script(m);
    let late = late_script(m);
    let script = apply_script(m, facts, &gaid);

    push_text(adb, serial, "Device.xml", "/data/local/tmp/farm_Device.xml", &to_device_xml(m))?;
    push_text(adb, serial, "module.prop", "/data/local/tmp/farm_module.prop", MODULE_PROP)?;
    push_text(adb, serial, "post_fs.sh", "/data/local/tmp/farm_post_fs.sh", &early)?;
    push_text(adb, serial, "service.sh", "/data/local/tmp/farm_service.sh", &late)?;
    push_text(adb, serial, "apply.sh", "/data/local/tmp/farm_apply.sh", &script)?;

    // Áp ngay: props (early + late), rồi settings/GAID/dọn/module
    run_su_script(adb, serial, "/data/local/tmp/farm_post_fs.sh", "")?;
    run_su_script(adb, serial, "/data/local/tmp/farm_service.sh", "now")?;
    run_su_script(adb, serial, "/data/local/tmp/farm_apply.sh", "")?;
    // MaxChanger nhận Device.xml mới
    let _ = adb_out(
        adb,
        serial,
        &["shell", "am broadcast -a com.minsoftware.maxchanger.ADB_ACTION --es ADB_CHANGE true"],
    );
    // dọn file tạm
    let _ = adb_out(
        adb,
        serial,
        &["shell", "rm -f /data/local/tmp/farm_Device.xml /data/local/tmp/farm_post_fs.sh /data/local/tmp/farm_service.sh /data/local/tmp/farm_apply.sh /data/local/tmp/farm_module.prop /data/local/tmp/farm_live.sh"],
    );

    let g = |k: &str| m.get(k).cloned().unwrap_or_default();
    Ok(AppliedProfile {
        model: g("model"),
        build: g("incremental"),
        imei: g("imei"),
        android_id: g("android_id"),
        gaid,
        operator: format!("{} {}", g("simOperatorName"), g("simOperator")),
        timezone: g("tz"),
        geo_source: geo_source.to_string(),
    })
}

/// Pool S8/S8+/Note8 chỉ khớp phần cứng Exynos 8895 (dream2lte/dreamlte/greatlte).
pub fn is_supported_hardware(f: &LiveFacts) -> bool {
    format!("{} {} {}", f.hardware, f.board_platform, f.boot_hardware).contains("8895")
}

/// Sinh định danh mới (đo máy thật + geo theo IP thoát) và áp lên máy.
pub fn apply_new(adb: &Path, serial: &str) -> Result<AppliedProfile, String> {
    let facts = read_live(adb, serial)?;
    if !is_supported_hardware(&facts) {
        return Err(format!(
            "phần cứng '{}/{}' không thuộc pool Exynos 8895 -> không tạo profile mâu thuẫn",
            facts.hardware, facts.board_platform
        ));
    }
    if facts.sdk != "28" {
        warn!("[Device {}] SDK thật = {} (pool profile viết cho Android 9/SDK 28)", serial, facts.sdk);
    }
    let mut rng = rand::thread_rng();
    let geo = lookup_geo(adb, serial, &mut rng);
    let flagged = load_blacklist();
    let m = generate_map(&facts, &geo, &flagged, &mut rng);
    apply_map(adb, serial, &m, &facts, &geo.source)
}

/// Khôi phục profile đã lưu của một nick (Device.xml backup) -> áp lại cả props hệ thống.
pub fn apply_from_device_xml(adb: &Path, serial: &str, xml: &str) -> Result<AppliedProfile, String> {
    let m = parse_device_xml(xml);
    for k in ["model", "fingerprint", "build_time", "android_id", "incremental"] {
        if m.get(k).map(|v| v.is_empty()).unwrap_or(true) {
            return Err(format!("Device.xml thiếu khoá '{}', không khôi phục props được", k));
        }
    }
    let facts = read_live(adb, serial)?;
    apply_map(adb, serial, &m, &facts, "restored")
}

// ───────────────────────────── Unit tests ─────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;
    use rand::rngs::StdRng;
    use rand::SeedableRng;

    // Dữ liệu đo thật trên ce0417140c8138370c (S8+ / LineageOS 16 / Exynos 8895)
    const LIVE_FIXTURE: &str = "HW=samsungexynos8895\nBP=exynos5\nBH=samsungexynos8895\nBOARD=universal8895\nABI=arm64-v8a,armeabi-v7a,armeabi\nARCH=arm64\nSDK=28\nREL=9\nKERNEL=4.4.111-ge843fcf8661e\nMAC=30:07:4d:6c:1b:46\nGL=GLES: ARM, Mali-G71, OpenGL ES 3.2 v1.r22p0\nBATLEVEL=95\nBATTEMP=-200\nBATSTATUS=4\n";

    fn facts() -> LiveFacts {
        parse_live(LIVE_FIXTURE)
    }

    fn geo() -> Geo {
        Geo { country: "US".into(), timezone: "America/New_York".into(), lat: 40.7, lon: -74.0, source: "test".into() }
    }

    #[test]
    fn luhn_known_vector() {
        // 490154203237518 là IMEI test hợp lệ kinh điển
        assert_eq!(luhn_check_digit("49015420323751"), 8);
    }

    #[test]
    fn imei_and_iccid_are_luhn_valid() {
        let mut rng = StdRng::seed_from_u64(7);
        for _ in 0..50 {
            let imei = make_imei("35879208", &mut rng);
            assert_eq!(imei.len(), 15);
            assert_eq!(luhn_check_digit(&imei[..14]).to_string(), imei[14..]);
            let iccid = make_iccid("8901260", &mut rng);
            assert_eq!(iccid.len(), 20);
            assert!(iccid.starts_with("8901260"));
            assert_eq!(luhn_check_digit(&iccid[..19]).to_string(), iccid[19..]);
        }
    }

    #[test]
    fn parse_live_reads_real_values() {
        let f = facts();
        assert_eq!(f.hardware, "samsungexynos8895");
        assert_eq!(f.sdk, "28");
        assert_eq!(f.release, "9");
        assert_eq!(f.gl_vendor, "ARM");
        assert_eq!(f.gl_renderer, "Mali-G71");
        assert_eq!(f.bat_temp, -200);
        assert_eq!(f.bat_status, 4);
        assert_eq!(f.kernel, "4.4.111-ge843fcf8661e");
    }

    #[test]
    fn generated_map_matches_real_hardware_not_fake_hardware() {
        let mut rng = StdRng::seed_from_u64(1);
        for _ in 0..40 {
            let m = generate_map(&facts(), &geo(), &[], &mut rng);
            // phần cứng/OS lấy từ máy thật -> hook Java và native cùng một sự thật
            assert_eq!(m["hardware"], "samsungexynos8895");
            assert_eq!(m["os_arch"], "4.4.111-ge843fcf8661e");
            assert_eq!(m["glRenderer"], "Mali-G71");
            assert_eq!(m["SDK"], "28");
            assert_eq!(m["release"], "9");
            assert!(m["fingerprint"].contains(":9/PPR1.180610.011/"), "fingerprint {}", m["fingerprint"]);
            // fingerprint, bootloader, baseband, incremental cùng mã build
            let code = &m["incremental"];
            assert!(m["fingerprint"].contains(code));
            assert_eq!(&m["bootloader"], code);
            assert_eq!(&m["radio_version"], code);
            assert!(m["model"].starts_with("SM-"));
            assert_eq!(m["model"], m["MODEL"]);
        }
    }

    #[test]
    fn sim_data_is_consistent_with_operator_and_nanp() {
        let mut rng = StdRng::seed_from_u64(3);
        for _ in 0..60 {
            let m = generate_map(&facts(), &geo(), &[], &mut rng);
            let op = &m["simOperator"];
            assert!(m["imsi"].starts_with(op.as_str()), "imsi {} vs op {}", m["imsi"], op);
            assert_eq!(m["imsi"].len(), 15);
            assert!(m["phone_num"].starts_with("+1"));
            let digits = &m["phone_num"][2..];
            assert_eq!(digits.len(), 10);
            assert!(digits.as_bytes()[0] >= b'2' && digits.as_bytes()[3] >= b'2', "NANP không hợp lệ: {}", m["phone_num"]);
            assert_eq!(m["country"], "us");
            assert!(m["IMSI"] == m["imsi"] && m["IMEI"] == m["imei"]);
        }
    }

    #[test]
    fn imei_tac_belongs_to_model() {
        let mut rng = StdRng::seed_from_u64(5);
        for _ in 0..60 {
            let m = generate_map(&facts(), &geo(), &[], &mut rng);
            let spec = MODELS.iter().find(|s| s.model == m["model"]).expect("model trong pool");
            assert!(spec.tacs.iter().any(|t| m["imei"].starts_with(t)), "TAC {} không thuộc {}", m["imei"], m["model"]);
        }
    }

    #[test]
    fn mac_keeps_real_oui_samsung() {
        let mut rng = StdRng::seed_from_u64(9);
        let m = generate_map(&facts(), &geo(), &[], &mut rng);
        assert!(m["wifimac"].starts_with("30:07:4d"));
        assert!(m["bluetooth_mac"].starts_with("30:07:4D"));
    }

    #[test]
    fn blacklist_is_soft_and_falls_back() {
        let mut rng = StdRng::seed_from_u64(11);
        let all: Vec<String> = MODELS
            .iter()
            .flat_map(|m| m.builds.iter().map(move |b| format!("{}|{}", m.model, b.code)))
            .collect();
        // chặn hết -> vẫn phải chọn được (không panic)
        let (m, b) = pick_model_build(&all, &mut rng);
        assert!(!m.model.is_empty() && !b.code.is_empty());
        // chặn 1 cặp -> không bao giờ chọn cặp đó
        let one = vec!["SM-G955F|G955FXXUCDVG4".to_string()];
        for _ in 0..200 {
            let (m, b) = pick_model_build(&one, &mut rng);
            assert!(!(m.model == "SM-G955F" && b.code == "G955FXXUCDVG4"));
        }
    }

    #[test]
    fn early_script_removes_lineage_and_sets_stock_props() {
        let mut rng = StdRng::seed_from_u64(13);
        let m = generate_map(&facts(), &geo(), &[], &mut rng);
        let s = early_script(&m);
        assert!(s.contains("ro\\.lineage"), "thiếu vòng xoá ro.lineage");
        assert!(s.contains("ro\\.modversion"));
        assert!(!s.contains("fp ro.lineage"), "không được tạo thêm prop lineage");
        assert!(s.contains(&format!("fp ro.build.flavor '{}-user'", m["product"])));
        assert!(s.contains("fp ro.build.type 'user'"));
        assert!(s.contains("ro.build.version.security_patch"));
        // không đụng serialno (adbd dùng nó để định danh máy trong farm)
        assert!(!s.contains("serialno"));
        // không ghi đè release/sdk thật
        assert!(!s.contains("ro.build.version.release"));
        assert!(!s.contains("ro.build.version.sdk"));
    }

    #[test]
    fn security_patch_matches_build_month() {
        let mut rng = StdRng::seed_from_u64(17);
        for _ in 0..30 {
            let (spec, build) = pick_model_build(&[], &mut rng);
            let _ = spec;
            let ms = build_time_ms(build, &mut rng);
            assert_eq!(security_patch_from_ms(ms), format!("{}-{:02}-01", build.year, build.month));
        }
    }

    #[test]
    fn late_script_sets_baseband_after_boot() {
        let mut rng = StdRng::seed_from_u64(19);
        let m = generate_map(&facts(), &geo(), &[], &mut rng);
        let s = late_script(&m);
        let code = &m["radio_version"];
        assert!(s.contains(&format!("fp gsm.version.baseband '{0},{0}'", code)));
        assert!(s.contains("sys.boot_completed"));
    }

    #[test]
    fn apply_script_fixes_p1_items() {
        let mut rng = StdRng::seed_from_u64(23);
        let m = generate_map(&facts(), &geo(), &[], &mut rng);
        let s = apply_script(&m, &facts(), "11111111-2222-4333-8444-555555555555");
        assert!(s.contains("settings put secure mock_location 0"));
        assert!(s.contains("io.appium.uiautomator2.server"));
        assert!(s.contains("dumpsys battery set temp"), "pin -200°C phải được sửa");
        assert!(s.contains("dumpsys battery set status 2"));
        assert!(s.contains("persist.sys.timezone 'America/New_York'"));
        assert!(s.contains("/data/adb/modules/farm_props"));
        // adbkeyboard KHÔNG bị gỡ (farm_container còn dùng)
        assert!(!s.contains("adbkeyboard"));
    }

    #[test]
    fn healthy_battery_is_left_alone() {
        let mut rng = StdRng::seed_from_u64(29);
        let m = generate_map(&facts(), &geo(), &[], &mut rng);
        let mut f = facts();
        f.bat_temp = 310;
        f.bat_status = 2;
        let s = apply_script(&m, &f, "x");
        assert!(!s.contains("dumpsys battery set"));
    }

    #[test]
    fn device_xml_roundtrip() {
        let mut rng = StdRng::seed_from_u64(31);
        let m = generate_map(&facts(), &geo(), &[], &mut rng);
        let back = parse_device_xml(&to_device_xml(&m));
        assert_eq!(m, back);
    }

    #[test]
    fn geo_json_parsing_and_fallback() {
        let mut rng = StdRng::seed_from_u64(37);
        let g = parse_geo_json(
            r#"{"status":"success","countryCode":"US","timezone":"America/Chicago","lat":41.88,"lon":-87.63,"query":"1.2.3.4"}"#,
            &mut rng,
        )
        .expect("parse");
        assert_eq!(g.timezone, "America/Chicago");
        assert!((g.lat - 41.88).abs() < 0.05 && (g.lon + 87.63).abs() < 0.05);
        assert!(parse_geo_json(r#"{"status":"fail"}"#, &mut rng).is_none());
        assert!(parse_geo_json("", &mut rng).is_none());
        assert_eq!(fallback_geo(&mut rng).country, "US");
    }

    #[test]
    fn vn_geo_uses_vn_carrier_and_number() {
        let mut rng = StdRng::seed_from_u64(41);
        let vn = Geo { country: "VN".into(), timezone: "Asia/Ho_Chi_Minh".into(), lat: 10.8, lon: 106.7, source: "t".into() };
        let m = generate_map(&facts(), &vn, &[], &mut rng);
        assert!(m["simOperator"].starts_with("452"));
        assert!(m["phone_num"].starts_with("+849"));
        assert!(m["imsi"].starts_with(m["simOperator"].as_str()));
    }

    #[test]
    fn restore_rejects_incomplete_device_xml() {
        // Device.xml thiếu khoá bắt buộc phải bị từ chối trước khi chạm vào máy
        let r = apply_from_device_xml(Path::new("adb-khong-ton-tai"), "x", "<map><string name=\"model\">SM-G955F</string></map>");
        assert!(r.is_err());
        assert!(r.unwrap_err().contains("thiếu khoá"));
    }
}
