//! Native XML Login Engine (100% Pure Rust)
//! ==========================================
//! Đăng nhập đồng loạt nhiều máy Android Phone Farm vào TikTok bằng cây UI XML
//! của UIAutomator (`uiautomator dump`) — KHÔNG dùng tọa độ cố định.
//!
//! Kiến trúc: State-Machine. Mỗi vòng lặp: dump XML -> nhận diện màn hình -> hành động.
//! Nhờ vậy xử lý được mọi trạng thái xuất phát của máy (đang xem FYP, đang ở popup,
//! đang ở form login dở dang, đang login nick khác...) thay vì chạy tuyến tính.
//!
//! Luồng 2 bước của TikTok: Username -> Continue -> Password -> Log in -> (2FA TOTP).

use hmac::{Hmac, Mac};
use parking_lot::{Mutex, RwLock};
use serde::{Deserialize, Serialize};
use sha1::Sha1;
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};
use std::process::Command;
use std::sync::atomic::{AtomicBool, AtomicUsize, Ordering};
use std::sync::{Arc, OnceLock};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};
use tracing::{info, warn};
use rand::seq::SliceRandom;
use rand::Rng;

#[path = "xml_signup.rs"]
pub mod signup;

const APP_PKG: &str = "com.zhiliaoapp.musically";
const MAX_STEPS: usize = 400;
const DEVICE_TIMEOUT: Duration = Duration::from_secs(420);

// ───────────────────────────── TOTP (RFC 6238) ─────────────────────────────

fn base32_decode(s: &str) -> Option<Vec<u8>> {
    let mut bits: u32 = 0;
    let mut nbits: u32 = 0;
    let mut out = Vec::new();
    for c in s.chars() {
        let c = c.to_ascii_uppercase();
        if c == '=' || c == ' ' || c == '-' {
            continue;
        }
        let v = match c {
            'A'..='Z' => c as u32 - 'A' as u32,
            '2'..='7' => c as u32 - '2' as u32 + 26,
            _ => return None,
        };
        bits = (bits << 5) | v;
        nbits += 5;
        if nbits >= 8 {
            nbits -= 8;
            out.push(((bits >> nbits) & 0xFF) as u8);
            bits &= (1 << nbits) - 1;
        }
    }
    Some(out)
}

/// Sinh mã TOTP 6 số tại thời điểm `unix` (giây).
pub fn totp_at(secret: &str, unix: u64) -> Option<String> {
    let key = base32_decode(secret)?;
    if key.is_empty() {
        return None;
    }
    let counter = (unix / 30).to_be_bytes();
    let mut mac = <Hmac<Sha1> as Mac>::new_from_slice(&key).ok()?;
    mac.update(&counter);
    let h = mac.finalize().into_bytes();
    let o = (h[19] & 0x0f) as usize;
    let code = ((h[o] as u32 & 0x7f) << 24)
        | ((h[o + 1] as u32) << 16)
        | ((h[o + 2] as u32) << 8)
        | (h[o + 3] as u32);
    Some(format!("{:06}", code % 1_000_000))
}

pub fn totp_now(secret: &str) -> Option<String> {
    let now = SystemTime::now().duration_since(UNIX_EPOCH).ok()?.as_secs();
    totp_at(secret, now)
}

// ───────────────────────────── C69 Email OTP ─────────────────────────────

fn scan_6_digits(text: &str) -> Option<String> {
    let bytes = text.as_bytes();
    let mut i = 0;
    while i < bytes.len() {
        if bytes[i].is_ascii_digit() {
            let start = i;
            while i < bytes.len() && bytes[i].is_ascii_digit() {
                i += 1;
            }
            if i - start == 6 {
                let before_ok = start == 0 || !bytes[start - 1].is_ascii_digit();
                let after_ok = i == bytes.len() || !bytes[i].is_ascii_digit();
                if before_ok && after_ok {
                    let code = String::from_utf8_lossy(&bytes[start..i]).to_string();
                    // Loại trừ năm (2026, 2025, 2024...)
                    if !code.starts_with("202") {
                        return Some(code);
                    }
                }
            }
        } else {
            i += 1;
        }
    }
    None
}

/// Trích xuất mã OTP 6 số từ email TikTok (Ưu tiên tuyệt đối mã đi liền với các từ khóa OTP TikTok)
fn extract_6_digit_code(text: &str) -> Option<String> {
    if text.is_empty() {
        return None;
    }
    let lower = text.to_lowercase();

    // 1. ƯU TIÊN SỐ 1: Bắt mã 6 số gắn liền với các từ khóa đặc trưng của email TikTok
    // Ví dụ: "639111 is your 6-digit code", "743491là mã gồm 6 chữ số", "code is: 639111", "verification code: 743491"
    let keywords = [
        "is your 6-digit code",
        "is your code",
        "is your verification code",
        "is your tiktok code",
        "là mã gồm 6 chữ số",
        "là mã của bạn",
        "mã gồm 6 chữ số",
        "code is:",
        "code is :",
        "code is",
        "code:",
        "mã:",
        "verification code"
    ];

    for kw in &keywords {
        if let Some(pos) = lower.find(kw) {
            let start_window = pos.saturating_sub(40);
            let end_window = std::cmp::min(text.len(), pos + kw.len() + 40);
            let slice = &text[start_window..end_window];
            if let Some(c) = scan_6_digits(slice) {
                return Some(c);
            }
        }
    }

    // 2. Dự phòng: quét toàn văn bản tìm chuỗi 6 số hợp lệ
    scan_6_digits(text)
}

/// Trích xuất liên kết đăng nhập/xác minh TikTok (Magic link / Login link) từ email
pub fn extract_tiktok_login_link(text: &str) -> Option<String> {
    if text.is_empty() {
        return None;
    }
    let mut candidates = Vec::new();

    // 1. Quét theo thẻ href="<url>" trước (chuẩn HTML email)
    let href_lower = text.to_lowercase();
    let mut href_idx = 0;
    while let Some(pos) = href_lower[href_idx..].find("href=") {
        let actual_pos = href_idx + pos + 5;
        let rem = &text[actual_pos..].trim_start();
        if let Some(quote_char) = rem.chars().next() {
            if quote_char == '"' || quote_char == '\'' {
                let inner = &rem[1..];
                if let Some(end_q) = inner.find(quote_char) {
                    let raw_url = &inner[..end_q];
                    let clean_url = raw_url.replace("&amp;", "&").trim().to_string();
                    let u_lower = clean_url.to_lowercase();
                    if u_lower.starts_with("http") && (u_lower.contains("tiktok.com") || u_lower.contains("tiktokv.com")) {
                        let is_priority = u_lower.contains("login")
                            || u_lower.contains("magic")
                            || u_lower.contains("link")
                            || u_lower.contains("verify")
                            || u_lower.contains("auth")
                            || u_lower.contains("passport")
                            || u_lower.contains("token")
                            || u_lower.contains("redirect");
                        candidates.push((if is_priority { 10 } else { 5 }, clean_url));
                    }
                }
            }
        }
        href_idx = actual_pos + 1;
    }

    // 2. Quét raw URL http/https
    let lower = text.to_lowercase();
    let mut search_idx = 0;
    while let Some(pos) = lower[search_idx..].find("http") {
        let actual_pos = search_idx + pos;
        let slice = &text[actual_pos..];

        let end_pos = slice.find(|c: char| {
            c.is_whitespace() || c == '"' || c == '\'' || c == '<' || c == '>' || c == ')' || c == ']' || c == '}' || c == '\\'
        }).unwrap_or(slice.len());

        let mut url = slice[..end_pos].trim();
        url = url.trim_end_matches(|c: char| c == '.' || c == ',' || c == ';' || c == '!' || c == '?' || c == ')' || c == ']');

        let clean_url = url.replace("&amp;", "&");
        let url_lower = clean_url.to_lowercase();
        if url_lower.contains("tiktok.com") || url_lower.contains("tiktokv.com") {
            let is_priority = url_lower.contains("login")
                || url_lower.contains("magic")
                || url_lower.contains("link")
                || url_lower.contains("verify")
                || url_lower.contains("auth")
                || url_lower.contains("passport")
                || url_lower.contains("token")
                || url_lower.contains("confirm")
                || url_lower.contains("redirect");

            candidates.push((if is_priority { 8 } else { 3 }, clean_url));
        }

        search_idx = actual_pos + end_pos.max(4);
    }

    candidates.sort_by(|a, b| b.0.cmp(&a.0));
    candidates.into_iter().next().map(|(_, url)| url)
}

/// Kiểm tra xem thời gian gửi của email có nằm trong khoảng thời gian tươi mới (dưới max_age_secs giây) hay không
fn is_time_fresh(date_str: &str, max_age_secs: i64) -> bool {
    let clean = date_str.trim();
    if clean.is_empty() {
        return false;
    }
    let now_utc = chrono::Utc::now().naive_utc();
    let now_local = chrono::Local::now().naive_local();

    // 1. Định dạng chuẩn C69 database: "2026-10-20 01:52:56"
    if let Ok(parsed) = chrono::NaiveDateTime::parse_from_str(clean, "%Y-%m-%d %H:%M:%S") {
        let diff_utc = (now_utc - parsed).num_seconds();
        let diff_local = (now_local - parsed).num_seconds();
        if (diff_utc >= -180 && diff_utc <= max_age_secs) || (diff_local >= -180 && diff_local <= max_age_secs) {
            return true;
        }
    }

    // 2. Định dạng RFC 2822: "Tue, 20 Oct 2026 12:41:28 +0000 (UTC)"
    let rfc_clean = clean.replace("(UTC)", "").replace("UTC", "").trim().to_string();
    if let Ok(parsed_dt) = chrono::DateTime::parse_from_rfc2822(&rfc_clean) {
        let diff = (now_utc - parsed_dt.naive_utc()).num_seconds();
        if diff >= -180 && diff <= max_age_secs {
            return true;
        }
    }

    // 3. Định dạng ISO 8601 / RFC 3339: "2026-10-20T12:41:28Z"
    if let Ok(parsed_dt) = chrono::DateTime::parse_from_rfc3339(clean) {
        let diff = (now_utc - parsed_dt.naive_utc()).num_seconds();
        if diff >= -180 && diff <= max_age_secs {
            return true;
        }
    }

    // 4. Dự phòng: Nếu chứa ngày hôm nay (cả UTC lẫn Local)
    let today_utc = chrono::Utc::now().format("%Y-%m-%d").to_string();
    let today_loc = chrono::Local::now().format("%Y-%m-%d").to_string();
    if clean.contains(&today_utc) || clean.contains(&today_loc) {
        return true;
    }

    false
}

/// Đọc hòm thư email trên C69 để lấy link đăng nhập (Magic Link / Login Link) của TikTok (trong vòng 15 phút)
pub fn fetch_login_link_from_c69(email_id: u64) -> Option<String> {
    let sess = crate::browser_nurture::load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(crate::browser_nurture::DEFAULT_C69_API_URL);
    let token = sess.as_ref().and_then(|s| s.token.clone()).unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());
    // BỎ ?fast=1 để lấy trọn vẹn HTML body chứa liên kết Magic link đăng nhập
    let url = format!("{}/dashboard/api/emails/{}/read-mailbox/", server_url, email_id);

    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().ok()?;
    let data: serde_json::Value = rt.block_on(async {
        let client = reqwest::Client::builder().timeout(Duration::from_secs(12)).build().ok()?;
        let resp = client.get(&url)
            .header("Authorization", &token)
            .send().await.ok()?;
        resp.json().await.ok()
    })?;

    // 1. Kiểm tra trường latest_content trong email_data — BẮT BUỘC latest_time phải còn tươi (<= 15 phút / 900s)
    let email_data = data.get("email_data");
    let latest_time = email_data.and_then(|d| d.get("latest_time")).and_then(|t| t.as_str()).unwrap_or("");
    if is_time_fresh(latest_time, 900) {
        if let Some(content) = email_data.and_then(|d| d.get("latest_content")).and_then(|c| c.as_str()) {
            if let Some(link) = extract_tiktok_login_link(content) {
                return Some(link);
            }
        }
    }

    // 2. Kiểm tra danh sách emails gần nhất — BẮT BUỘC email.date phải còn tươi (<= 15 phút / 900s)
    if let Some(emails) = data.get("emails").and_then(|e| e.as_array()) {
        for email in emails {
            let date_str = email.get("date").and_then(|d| d.as_str()).unwrap_or("");
            if !is_time_fresh(date_str, 900) {
                continue;
            }

            let body = email.get("body").and_then(|s| s.as_str()).unwrap_or("");
            let snip = email.get("snippet").and_then(|s| s.as_str()).unwrap_or("");
            let html = email.get("html").and_then(|s| s.as_str()).unwrap_or("");

            if let Some(link) = extract_tiktok_login_link(body) {
                return Some(link);
            }
            if let Some(link) = extract_tiktok_login_link(html) {
                return Some(link);
            }
            if let Some(link) = extract_tiktok_login_link(snip) {
                return Some(link);
            }
        }
    }
    None
}

/// Đọc hòm thư email trên C69 để lấy mã OTP 6 số mới nhất (BẮT BUỘC TRONG VÒNG 10 PHÚT, CHỐNG LẤY MÃ CŨ EXPIRED)
pub fn fetch_otp_from_c69(email_id: u64) -> Option<String> {
    let sess = crate::browser_nurture::load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(crate::browser_nurture::DEFAULT_C69_API_URL);
    let token = sess.as_ref().and_then(|s| s.token.clone()).unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());
    let url = format!("{}/dashboard/api/emails/{}/read-mailbox/?fast=1", server_url, email_id);

    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().ok()?;
    let data: serde_json::Value = rt.block_on(async {
        let client = reqwest::Client::builder().timeout(Duration::from_secs(12)).build().ok()?;
        let resp = client.get(&url)
            .header("Authorization", &token)
            .send().await.ok()?;
        resp.json().await.ok()
    })?;

    // 1. Kiểm tra trường latest_code trong email_data — BẮT BUỘC latest_time phải còn tươi (<= 10 phút / 600s)
    let email_data = data.get("email_data");
    let latest_time = email_data.and_then(|d| d.get("latest_time")).and_then(|t| t.as_str()).unwrap_or("");
    let latest_code = email_data.and_then(|d| d.get("latest_code")).and_then(|c| c.as_str()).unwrap_or("").trim();

    if is_time_fresh(latest_time, 600) && latest_code.len() == 6 && latest_code.chars().all(|ch| ch.is_ascii_digit()) {
        return Some(latest_code.to_string());
    }

    // 2. Kiểm tra danh sách emails gần nhất — BẮT BUỘC email.date phải còn tươi (<= 10 phút / 600s)
    if let Some(emails) = data.get("emails").and_then(|e| e.as_array()) {
        for email in emails {
            let date_str = email.get("date").and_then(|d| d.as_str()).unwrap_or("");
            if !is_time_fresh(date_str, 600) {
                // Email trong hộp thư đã cũ hơn 10 phút -> Mã OTP này chắc chắn đã hết hạn (expired), BỎ QUA!
                continue;
            }

            let subj = email.get("subject").and_then(|s| s.as_str()).unwrap_or("");
            let snip = email.get("snippet").and_then(|s| s.as_str()).unwrap_or("");
            let body = email.get("body").and_then(|s| s.as_str()).unwrap_or("");

            if let Some(code) = extract_6_digit_code(subj) {
                return Some(code);
            }
            if let Some(code) = extract_6_digit_code(snip) {
                return Some(code);
            }
            if let Some(code) = extract_6_digit_code(body) {
                return Some(code);
            }
        }
    }
    None
}

/// Tra cứu ID hộp thư C69 theo username hoặc email
pub fn resolve_c69_email_id(query: &str) -> Option<u64> {
    let sess = crate::browser_nurture::load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(crate::browser_nurture::DEFAULT_C69_API_URL);
    let token = sess.as_ref().and_then(|s| s.token.clone()).unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());
    let url = format!("{}/dashboard/api/accounts/?search={}&page_size=1", server_url, urlencoding::encode(query));

    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().ok()?;
    let data: serde_json::Value = rt.block_on(async {
        let client = reqwest::Client::builder().timeout(Duration::from_secs(8)).build().ok()?;
        let resp = client.get(&url)
            .header("Authorization", &token)
            .send().await.ok()?;
        resp.json().await.ok()
    })?;

    let results = data.get("results").and_then(|r| r.as_array())?;
    let first = results.first()?;
    first.get("accounts_emails").and_then(|v| v.as_u64())
        .or_else(|| first.get("email_info").and_then(|e| e.get("id")).and_then(|v| v.as_u64()))
}

#[derive(Debug, PartialEq, Eq)]
pub enum C69EmailCheck {
    Readable,
    Unregistered, // Chứa "complete your signup" nhưng không có email login nào
    Unreadable,
}

fn extract_username_from_email_text(text: &str) -> Option<String> {
    if let Some(pos) = text.find("verify that @") {
        let rem = &text[pos + 13..];
        let end = rem.find(|c: char| c == ',' || c.is_control() || c.is_whitespace()).unwrap_or(rem.len());
        let u = rem[..end].trim_end_matches('.');
        if u.len() >= 3 && u.len() <= 24 && !u.ends_with(".com") && !u.ends_with(".net") {
            return Some(u.to_string());
        }
    }
    if let Some(pos) = text.find("account @") {
        let rem = &text[pos + 9..];
        let end = rem.find(|c: char| c == ',' || c.is_control() || c.is_whitespace()).unwrap_or(rem.len());
        let u = rem[..end].trim_end_matches('.');
        if u.len() >= 3 && u.len() <= 24 && !u.ends_with(".com") && !u.ends_with(".net") {
            return Some(u.to_string());
        }
    }
    if let Some(pos) = text.find("Hi ") {
        let rem = &text[pos + 3..];
        let end = rem.find(|c: char| c == ',' || c.is_control() || c.is_whitespace()).unwrap_or(rem.len());
        let u = rem[..end].trim_end_matches(|c: char| c == ',' || c == '.');
        if u.len() >= 3 && u.len() <= 24 && !u.ends_with(".com") && !u.ends_with(".net") && !u.eq_ignore_ascii_case("tiktok") {
            return Some(u.to_string());
        }
    }
    None
}

/// Kiểm tra xem hòm thư C69 của email_id có đọc được OTP không theo chỉ đạo anh Tony
pub fn check_c69_email_status(email_id: u64) -> (C69EmailCheck, Option<String>) {
    let sess = crate::browser_nurture::load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(crate::browser_nurture::DEFAULT_C69_API_URL);
    let token = sess.as_ref().and_then(|s| s.token.clone()).unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());
    let url = format!("{}/dashboard/api/emails/{}/read-mailbox/?fast=1", server_url, email_id);

    let rt = match tokio::runtime::Builder::new_current_thread().enable_all().build() {
        Ok(r) => r,
        Err(_) => return (C69EmailCheck::Unreadable, None),
    };
    rt.block_on(async {
        let client = match reqwest::Client::builder()
            .timeout(Duration::from_secs(25))
            .user_agent("Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
            .build() {
            Ok(c) => c,
            Err(_) => return (C69EmailCheck::Unreadable, None),
        };
        let resp = match client.get(&url)
            .header("Authorization", &token)
            .send().await {
            Ok(r) => r,
            Err(_) => return (C69EmailCheck::Unreadable, None),
        };
        if !resp.status().is_success() {
            return (C69EmailCheck::Unreadable, None);
        }
        let data: serde_json::Value = match resp.json().await {
            Ok(d) => d,
            Err(_) => return (C69EmailCheck::Unreadable, None),
        };

        let mut discovered_user = None;

        if let Some(list) = data.get("emails").and_then(|e| e.as_array()) {
            for m in list {
                let snip = m.get("snippet").and_then(|s| s.as_str()).unwrap_or("");
                let subj = m.get("subject").and_then(|s| s.as_str()).unwrap_or("");
                let body = m.get("body").and_then(|s| s.as_str()).unwrap_or("");
                let combined = format!("{} {} {}", subj, snip, body);
                if discovered_user.is_none() {
                    if let Some(u) = extract_username_from_email_text(&combined) {
                        discovered_user = Some(u);
                    }
                }
            }

            if let Some(first) = list.first() {
                let snip = first.get("snippet").and_then(|s| s.as_str()).unwrap_or("");
                let subj = first.get("subject").and_then(|s| s.as_str()).unwrap_or("");
                let body = format!("{} {}", subj, snip).to_lowercase();
                if (body.contains("complete your signup") || body.contains("confirm your email and complete"))
                    && !body.contains("login detected")
                    && !body.contains("use it to log in")
                    && list.len() <= 1
                {
                    return (C69EmailCheck::Unregistered, discovered_user);
                }
            }
            if !list.is_empty() {
                return (C69EmailCheck::Readable, discovered_user);
            }
        }

        if data.get("success").and_then(|s| s.as_bool()).unwrap_or(false)
            || data.get("email_data").and_then(|d| d.get("id")).is_some() {
            (C69EmailCheck::Readable, discovered_user)
        } else {
            (C69EmailCheck::Unreadable, None)
        }
    })
}

pub fn check_c69_email_readable(email_id: u64) -> bool {
    check_c69_email_status(email_id).0 == C69EmailCheck::Readable
}

// ───────────────────────────── SOCKS5 US PROXY WHITELIST ─────────────────────────────
const US_PROXY_PREFIXES: &[&str] = &[
    "140.235.", "143.14.", "149.19.", "162.252.", "166.0.", "167.253.",
    "172.111.", "180.149.", "185.77.", "192.101.", "193.56.", "194.110.",
    "194.180.", "198.12.", "199.7.", "199.96.", "200.229.", "206.125.",
    "212.87.", "23.95.", "45.136.", "64.49.", "88.218.", "89.106.",
    "91.132.", "93.177."
];

fn get_device_mac(adb: &Path, serial: &str) -> String {
    // 1. Tra cứu nhanh từ bảng MAC cố định của 10 máy phone farm (tránh lỗi khi máy đang reboot)
    match serial {
        "ce0117112dccec3404" => return "8C:F5:A3:C7:44:B5".into(),
        "ce03171371483c3c05" => return "8C:F5:A3:C8:8A:68".into(),
        "ce031713edfb4f3702" => return "8C:F5:A3:FB:64:F7".into(),
        "ce031713f138907a0c" => return "30:07:4D:1D:FE:60".into(),
        "ce04171409d8062401" => return "30:07:4D:69:CC:0B".into(),
        "ce0417140c8138370c" => return "30:07:4D:6C:1B:46".into(),
        "ce0417145ce4a0e80c" => return "F8:E6:1A:FE:0B:F1".into(),
        "ce041714a2d2211102" => return "30:07:4D:F6:24:9A".into(),
        "ce051715c86d871f03" => return "94:8B:C1:22:BE:1E".into(),
        "ce0918298272403101" => return "A8:2B:B9:1F:BA:6A".into(),
        _ => {}
    }
    // 2. Dự phòng: đọc động từ hệ thống nếu là serial lạ
    for _ in 0..4 {
        let mac = adb_shell(adb, serial, "cat /sys/class/net/wlan0/address").trim().to_uppercase();
        if !mac.is_empty() && mac.contains(':') {
            return mac;
        }
        std::thread::sleep(Duration::from_millis(1000));
    }
    String::new()
}

/// Tự động đổi proxy ngẫu nhiên từ router 192.168.0.244:9000 cho thiết bị và ĐỐI SOÁT THỰC TẾ TRÊN MÁY
/// Tiền tố /24 của Wi-Fi farm (lấy theo IP đa số thiết bị trong router GenRouter, mặc định 192.168.10.).
fn farm_wifi_prefix() -> String {
    let default = "192.168.10.".to_string();
    let client = match reqwest::blocking::Client::builder().timeout(Duration::from_secs(4)).build() {
        Ok(c) => c,
        Err(_) => return default,
    };
    let v: serde_json::Value = match client.get("http://192.168.0.244:9000/api/devices").send().and_then(|r| r.json()) {
        Ok(v) => v,
        Err(_) => return default,
    };
    let mut counts: std::collections::HashMap<String, usize> = std::collections::HashMap::new();
    if let Some(arr) = v.get("devices").and_then(|d| d.as_array()) {
        for d in arr {
            if let Some(ip) = d.get("ip").and_then(|i| i.as_str()) {
                let parts: Vec<&str> = ip.split('.').collect();
                if parts.len() == 4 {
                    *counts.entry(format!("{}.{}.{}.", parts[0], parts[1], parts[2])).or_insert(0) += 1;
                }
            }
        }
    }
    counts.into_iter().max_by_key(|(_, n)| *n).map(|(p, _)| p).unwrap_or(default)
}

/// Máy hay trôi sang Wi-Fi phụ ("Dac Tuan", 192.168.100.x) không có router/proxy => TikTok báo "No internet",
/// router trả 404 "Device not found". Đảm bảo máy đang ở đúng Wi-Fi farm; không thì tắt/bật Wi-Fi để kết nối lại.
pub fn ensure_farm_wifi(adb: &Path, serial: &str) -> Result<String, String> {
    let prefix = farm_wifi_prefix();
    let mut last_ip = String::new();
    for attempt in 0..4 {
        let out = adb_shell(adb, serial, "ip -4 addr show wlan0 | grep inet");
        last_ip = out
            .split_whitespace()
            .skip_while(|w| *w != "inet")
            .nth(1)
            .map(|s| s.split('/').next().unwrap_or("").to_string())
            .unwrap_or_default();
        if last_ip.starts_with(&prefix) {
            return Ok(last_ip);
        }
        if attempt >= 1 {
            // Tự động dọn dẹp profile wifi phụ nếu máy bị trôi mạng
            let clean_sh = "su -c 'if [ -f /data/misc/wifi/WifiConfigStore.xml ]; then sed -i \"/<Network>/,/<\\/Network>/{/Dac Tuan/d}\" /data/misc/wifi/WifiConfigStore.xml 2>/dev/null; chown system:wifi /data/misc/wifi/WifiConfigStore.xml 2>/dev/null; chmod 660 /data/misc/wifi/WifiConfigStore.xml 2>/dev/null; fi'";
            let _ = adb_shell(adb, serial, clean_sh);
        }
        let _ = adb_shell(adb, serial, "svc wifi disable");
        std::thread::sleep(Duration::from_secs(3));
        let _ = adb_shell(adb, serial, "svc wifi enable");
        std::thread::sleep(Duration::from_secs(10));
    }
    Err(format!("Máy không vào được Wi-Fi farm ({}x) — IP hiện tại '{}'", prefix, last_ip))
}

pub fn rotate_device_proxy(adb: &Path, serial: &str) -> Result<String, String> {
    // Phải ở đúng Wi-Fi farm thì router mới biết MAC của máy (nếu không sẽ 404 Device not found).
    ensure_farm_wifi(adb, serial)?;
    let mac_out = get_device_mac(adb, serial);
    if mac_out.is_empty() {
        return Err("Không lấy được MAC wlan0 từ thiết bị".into());
    }

    // 1. Lấy IP egress hiện tại của máy để đối soát
    let old_ip = adb_shell(adb, serial, "curl -s -m 5 https://ifconfig.me").trim().to_string();

    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().map_err(|e| e.to_string())?;

    // Thử tối đa 8 proxy Live khác nhau từ router cho đến khi máy thực sự có mạng
    for rotate_attempt in 1..=8 {
        let assign_res = rt.block_on(async {
            let client = reqwest::Client::builder().timeout(Duration::from_secs(8)).build().map_err(|e| e.to_string())?;
            let res = client.get("http://192.168.0.244:9000/api/proxies").send().await.map_err(|e| e.to_string())?;
            let data: serde_json::Value = res.json().await.map_err(|e| e.to_string())?;
            let proxies = data.get("proxies").and_then(|p| p.as_array()).ok_or("Không có danh sách proxies")?;

            // ĐỌC DANH SÁCH 500 PROXY 100% US LIVE TỪ NOTE 100:
            let whitelist_hosts: Option<std::collections::HashSet<String>> = std::fs::read_to_string("D:/Workspace/Python/QHTDautomation/us_proxies_whitelist.json")
                .ok()
                .and_then(|txt| serde_json::from_str::<serde_json::Value>(&txt).ok())
                .and_then(|val| val.as_array().cloned())
                .map(|arr| {
                    arr.iter().filter_map(|p| p.get("host").and_then(|h| h.as_str()).map(|s| s.to_string())).collect()
                });

            // LẤY TOÀN BỘ PROXY LIVE 100% US (LOẠI BỎ TRIỆT ĐỂ PROXY ĐỨC, UKRAINE, CHÂU ÂU):
            let live_proxies: Vec<&serde_json::Value> = proxies.iter().filter(|p| {
                let st = p.get("status").and_then(|s| s.as_str()).unwrap_or("");
                let host = p.get("host").and_then(|h| h.as_str()).unwrap_or("");
                if st != "Live" && st != "Unknown" {
                    return false;
                }
                // Nếu có whitelist 500 US thì đối chiếu 100%:
                if let Some(ref wl) = whitelist_hosts {
                    if !wl.is_empty() {
                        return wl.contains(host);
                    }
                }
                // Chặn cứng tuyệt đối các dải IP ngoại (Đức, Ukraine, Nga, Châu Âu):
                let is_foreign = host.starts_with("176.126.")
                    || host.starts_with("83.97.")
                    || host.starts_with("104.245.")
                    || host.starts_with("62.204.")
                    || host.starts_with("193.163.")
                    || host.starts_with("178.")
                    || host.starts_with("185.202.")
                    || host.starts_with("185.212.")
                    || host.starts_with("216.40.")
                    || host.starts_with("88.218.")
                    || host.starts_with("193.42.")
                    || host.starts_with("194.110.")
                    || host.starts_with("91.132.")
                    || host.starts_with("94.154.")
                    || host.starts_with("93.177.")
                    || host.starts_with("212.18.")
                    || host.starts_with("212.87.");
                !is_foreign
            }).collect();

            if live_proxies.is_empty() {
                return Err("Không có proxy US Live trên router 192.168.0.244".into());
            }

            // Ưu tiên chọn proxy có IP khác với old_ip hiện tại của máy
            let mut candidates: Vec<&serde_json::Value> = live_proxies.iter().copied().filter(|p| {
                let host = p.get("host").and_then(|v| v.as_str()).unwrap_or("");
                !old_ip.is_empty() && host != old_ip
            }).collect();
            if candidates.is_empty() {
                candidates = live_proxies;
            }

            let mut rng = rand::thread_rng();
            let chosen = candidates.choose(&mut rng).ok_or("Không chọn được proxy")?;
            let proxy_id = chosen.get("id").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let host = chosen.get("host").and_then(|v| v.as_str()).unwrap_or("").to_string();
            let port = chosen.get("port").and_then(|v| v.as_u64()).unwrap_or(0);

            let assign_payload = serde_json::json!({
                "mac": mac_out,
                "proxy_id": proxy_id
            });

            let resp = client.post("http://192.168.0.244:9000/api/devices/assign")
                .json(&assign_payload)
                .send().await.map_err(|e| format!("Lỗi gọi router assign: {}", e))?;

            if !resp.status().is_success() {
                return Err(format!("Router trả về HTTP {}", resp.status()));
            }

            Ok((host, port, proxy_id))
        });

        let (chosen_host, chosen_port, chosen_id) = match assign_res {
            Ok(tuple) => tuple,
            Err(e) => {
                if rotate_attempt == 8 {
                    return Err(e);
                }
                std::thread::sleep(Duration::from_millis(1500));
                continue;
            }
        };

        // ĐỐI SOÁT THỰC TẾ TRÊN MÁY THEO CHỈ ĐẠO CỐT LÕI CỦA ANH TONY:
        // 1. Kiểm tra máy có nhận IP mới ra ngoài không:
        let mut verified_ip = String::new();
        let check_start = Instant::now();
        while check_start.elapsed() < Duration::from_secs(12) {
            let cur_ip = adb_shell(adb, serial, "curl -s -m 3 http://api.ipify.org").trim().to_string();
            if !cur_ip.is_empty() && cur_ip.contains('.') && !cur_ip.contains("error") && !cur_ip.contains("html") {
                // CHỐT CHẶN BẢO VỆ 100%: TUYỆT ĐỐI CẤM LỌT IP VIỆT NAM GỐC HOẶC IP NGOẠI (ĐỨC, UKRAINE, CHÂU ÂU)!
                let is_bad_egress = cur_ip == "171.241.99.2"
                    || cur_ip.starts_with("171.")
                    || cur_ip.starts_with("14.")
                    || cur_ip.starts_with("113.")
                    || cur_ip.starts_with("118.")
                    || cur_ip.starts_with("27.")
                    || cur_ip.starts_with("42.")
                    || cur_ip.starts_with("123.")
                    || cur_ip.starts_with("125.")
                    || cur_ip.starts_with("222.")
                    || cur_ip.starts_with("1.53.")
                    || cur_ip.starts_with("176.126.")
                    || cur_ip.starts_with("83.97.")
                    || cur_ip.starts_with("104.245.")
                    || cur_ip.starts_with("62.204.")
                    || cur_ip.starts_with("193.163.")
                    || cur_ip.starts_with("88.218.");

                if is_bad_egress {
                    warn!("[Device {}] Proxy {} ({}:{}) rò rỉ IP không hợp lệ ({})! Cấm vào TikTok, lập tức đổi proxy khác...", serial, chosen_id, chosen_host, chosen_port, cur_ip);
                    break;
                }

                verified_ip = cur_ip;
                break;
            }
            std::thread::sleep(Duration::from_millis(800));
        }

        if verified_ip.is_empty() {
            warn!("[Device {}] Proxy {} ({}:{}) sau 12s không nhận được IP US hợp lệ. Đổi proxy khác...", serial, chosen_id, chosen_host, chosen_port);
            continue;
        }

        // 2. BẮT BUỘC ĐỐI SOÁT PROXY CÓ THỰC SỰ CẤP INTERNET CHO TIKTOK HAY KHÔNG (CHỐT CHẶN CHỐNG NO INTERNET):
        let mut tiktok_ok = false;
        for _ in 1..=3 {
            let tt_test = adb_shell(adb, serial, "curl -s -m 5 -I https://www.tiktok.com").trim().to_string();
            if tt_test.contains("200") || tt_test.contains("302") || tt_test.contains("HTTP/") {
                tiktok_ok = true;
                break;
            }
            std::thread::sleep(Duration::from_millis(1000));
        }

        if !tiktok_ok {
            warn!("[Device {}] Proxy {} ({}:{}) có IP {} nhưng KHÔNG KẾT NỐI ĐƯỢC TỚI TIKTOK. Đổi ngay proxy khác...", serial, chosen_id, chosen_host, chosen_port, verified_ip);
            continue;
        }

        return Ok(format!("{}:{} (Egress IP: {}, Proxy: {})", chosen_host, chosen_port, verified_ip, chosen_id));
    }

    Err(format!("Máy {} đã thử 8 proxy Live nhưng không có proxy nào kết nối được tới TikTok!", serial))
}

/// Ghi log timeline lên tài khoản C69 (chuẩn Garret Tan / C69 rule: CẤM đè note client, timeline [DD/MM HH:MM], ghim '--- Ghi chú gốc ---')
pub fn sync_c69_timeline_log(acc_id: u64, action_text: &str, new_status: Option<i64>) {
    let action_owned = action_text.to_string();
    std::thread::spawn(move || {
        let sess = crate::browser_nurture::load_c69_session();
        let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(crate::browser_nurture::DEFAULT_C69_API_URL);
        let token = sess.as_ref().and_then(|s| s.token.clone()).unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());

        let now = chrono::Local::now();
        let time_str = now.format("%d/%m %H:%M").to_string();
        let timeline_entry = format!("[{}] {}", time_str, action_owned);

        let rt = tokio::runtime::Builder::new_current_thread().enable_all().build();
        if let Ok(rt) = rt {
            let _ = rt.block_on(async {
                let client = reqwest::Client::builder().timeout(Duration::from_secs(8)).build().ok()?;
                let get_url = format!("{}/dashboard/api/accounts/{}/", server_url, acc_id);
                let resp = client.get(&get_url).header("Authorization", &token).send().await.ok()?;
                let acc_data: serde_json::Value = resp.json().await.ok()?;

                let cur_note = acc_data.get("note").and_then(|n| n.as_str()).unwrap_or("").trim();
                let new_note = if cur_note.is_empty() {
                    timeline_entry
                } else if cur_note.contains("--- Ghi chú gốc ---") {
                    format!("{}\n{}", timeline_entry, cur_note)
                } else {
                    format!("{}\n--- Ghi chú gốc ---\n{}", timeline_entry, cur_note)
                };

                let patch_url = format!("{}/dashboard/api/accounts/{}/", server_url, acc_id);
                let mut patch_body = serde_json::json!({
                    "note": new_note,
                    "modified_by": "MunAutomation"
                });
                if let Some(st) = new_status {
                    patch_body["status"] = serde_json::json!(st);
                }

                let _ = client.patch(&patch_url)
                    .header("Authorization", &token)
                    .json(&patch_body)
                    .send().await;
                Some(())
            });
        }
    });
}

/// Tìm account_id từ username / email trên C69 và ghi log
pub fn sync_c69_log_by_query(query: &str, action_text: &str, new_status: Option<i64>) {
    let clean_query = query.trim().trim_start_matches('@').to_string();
    if clean_query.is_empty() {
        return;
    }
    let action_owned = action_text.to_string();
    std::thread::spawn(move || {
        let sess = crate::browser_nurture::load_c69_session();
        let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(crate::browser_nurture::DEFAULT_C69_API_URL);
        let token = sess.as_ref().and_then(|s| s.token.clone()).unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());
        let url = format!("{}/dashboard/api/accounts/?search={}&page_size=1", server_url, urlencoding::encode(&clean_query));

        let rt = tokio::runtime::Builder::new_current_thread().enable_all().build();
        if let Ok(rt) = rt {
            let _ = rt.block_on(async {
                let client = reqwest::Client::builder().timeout(Duration::from_secs(8)).build().ok()?;
                let resp = client.get(&url).header("Authorization", &token).send().await.ok()?;
                let data: serde_json::Value = resp.json().await.ok()?;
                let first = data.get("results").and_then(|r| r.as_array())?.first()?;
                let acc_id = first.get("id").and_then(|v| v.as_u64())?;
                sync_c69_timeline_log(acc_id, &action_owned, new_status);
                if let Some(owner) = first.get("created_by").and_then(|v| v.as_str()).or_else(|| first.get("subscription_owner").and_then(|v| v.as_str())) {
                    crate::telegram_notifier::notify_client(owner, "Cập Nhật Tiến Trình C69 🌾", &action_owned);
                }
                Some(())
            });
        }
    });
}

// ───────────────────────────── Types & Status ─────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct LoginAccount {
    #[serde(default)]
    pub id: Option<u64>,
    pub username: String,
    pub password: String,
    #[serde(default, alias = "two_factor_auth")]
    pub secret: String,
    #[serde(default)]
    pub email_id: Option<u64>,
    #[serde(default)]
    pub email: Option<String>,
    #[serde(default)]
    pub client: Option<String>,
}

impl LoginAccount {
    /// Xác định thông tin đăng nhập theo đúng chỉ đạo anh Tony:
    /// - Nếu có mã 2FA secret key -> Bắt buộc dùng USERNAME để đăng nhập và vượt 2FA TOTP
    /// - Nếu KHÔNG CÓ mã 2FA secret key -> BẮT BUỘC dùng EMAIL đăng nhập đầu tiên để đọc OTP từ C69!
    pub fn login_identifier(&self) -> &str {
        let has_2fa = !self.secret.trim().is_empty();
        if has_2fa {
            self.username.trim()
        } else {
            if let Some(ref em) = self.email {
                let em_trimmed = em.trim();
                if em_trimmed.contains('@') {
                    return em_trimmed;
                }
            }
            if self.username.contains('@') {
                return self.username.trim();
            }
            self.username.trim()
        }
    }
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct XmlLoginStatus {
    pub serial: String,
    pub username: String,
    pub account_id: Option<u64>,
    /// detecting | queued | running | success | failed
    pub state: String,
    pub step: String,
    pub message: String,
    pub current_user: String,
    pub updated: String,
    pub logs: Vec<String>,
}

fn status_map() -> &'static RwLock<HashMap<String, XmlLoginStatus>> {
    static M: OnceLock<RwLock<HashMap<String, XmlLoginStatus>>> = OnceLock::new();
    M.get_or_init(|| RwLock::new(HashMap::new()))
}

static STOP: AtomicBool = AtomicBool::new(false);
static RUNNING: AtomicBool = AtomicBool::new(false);
static TOTAL_COUNT: AtomicUsize = AtomicUsize::new(0);
static SUCC_COUNT: AtomicUsize = AtomicUsize::new(0);
static FAIL_COUNT: AtomicUsize = AtomicUsize::new(0);
static SKIP_MANUAL_COUNT: AtomicUsize = AtomicUsize::new(0);
static QUEUE_REMAINING: AtomicUsize = AtomicUsize::new(0);

pub fn queue_stats() -> (usize, usize, usize, usize, usize) {
    (
        TOTAL_COUNT.load(Ordering::SeqCst),
        SUCC_COUNT.load(Ordering::SeqCst),
        FAIL_COUNT.load(Ordering::SeqCst),
        SKIP_MANUAL_COUNT.load(Ordering::SeqCst),
        QUEUE_REMAINING.load(Ordering::SeqCst),
    )
}

fn now_str() -> String {
    chrono::Local::now().format("%H:%M:%S").to_string()
}

fn upd(serial: &str, f: impl FnOnce(&mut XmlLoginStatus)) {
    let mut m = status_map().write();
    let e = m.entry(serial.to_string()).or_insert_with(|| XmlLoginStatus {
        serial: serial.to_string(),
        ..Default::default()
    });
    f(e);
    e.updated = now_str();
}

fn log(serial: &str, step: &str, msg: impl Into<String>) {
    let msg = msg.into();
    info!("[XMLLogin {}] {} — {}", serial, step, msg);
    upd(serial, |s| {
        s.step = step.to_string();
        s.logs.push(format!("{} {} — {}", now_str(), step, msg));
        if s.logs.len() > 40 {
            let drop = s.logs.len() - 40;
            s.logs.drain(0..drop);
        }
    });
}

pub fn snapshot() -> Vec<XmlLoginStatus> {
    let mut v: Vec<XmlLoginStatus> = status_map().read().values().cloned().collect();
    v.sort_by(|a, b| a.serial.cmp(&b.serial));
    v
}

pub fn is_running() -> bool {
    RUNNING.load(Ordering::SeqCst)
}

pub fn stop() {
    STOP.store(true, Ordering::SeqCst);
}

// ───────────────────────────── ADB helpers ─────────────────────────────

fn adb_raw(adb: &Path, serial: &str, args: &[&str]) -> Option<Vec<u8>> {
    let mut cmd = Command::new(adb);
    cmd.arg("-s").arg(serial).args(args);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    cmd.output().ok().map(|o| o.stdout)
}

fn adb_shell(adb: &Path, serial: &str, shell_cmd: &str) -> String {
    adb_raw(adb, serial, &["shell", shell_cmd])
        .map(|b| String::from_utf8_lossy(&b).trim().to_string())
        .unwrap_or_default()
}

fn tap(adb: &Path, serial: &str, x: i32, y: i32) {
    let mut rng = rand::thread_rng();
    let (jx, jy) = (rng.gen_range(-3..=3), rng.gen_range(-3..=3));
    adb_shell(adb, serial, &format!("input tap {} {}", x + jx, y + jy));
}

fn key(adb: &Path, serial: &str, code: u32) {
    adb_shell(adb, serial, &format!("input keyevent {}", code));
}

/// Vuốt lên với toạ độ/độ dài/thời gian ngẫu nhiên (tránh quỹ đạo cố định).
fn jitter_swipe_cmd(y0: i32, y1: i32, dur: u32) -> String {
    let mut rng = rand::thread_rng();
    let x0 = 360 + rng.gen_range(-45..=45);
    let x1 = x0 + rng.gen_range(-30..=30);
    let ya = y0 + rng.gen_range(-40..=40);
    let yb = y1 + rng.gen_range(-40..=40);
    let d = (dur as i32 + rng.gen_range(-70..=110)).max(180);
    format!("input swipe {} {} {} {} {}", x0, ya, x1, yb, d)
}

fn swipe_up(adb: &Path, serial: &str) {
    adb_shell(adb, serial, &jitter_swipe_cmd(1050, 400, 300));
}

fn run_quick_nurture(adb: &Path, serial: &str, count: usize) {
    // 1. Chuyển ngay về tab Home (FYP feed video) từ tab Profile
    adb_shell(adb, serial, "input tap 80 1375");
    std::thread::sleep(Duration::from_millis(1500));

    // 2. Chạm nhẹ tâm màn hình để đóng overlay hướng dẫn hoặc popup cản đường
    adb_shell(adb, serial, "input tap 360 740");
    std::thread::sleep(Duration::from_millis(1000));

    // 3. Vuốt nhẹ 1 lần để chắc chắn video bắt đầu chạy
    adb_shell(adb, serial, &jitter_swipe_cmd(1100, 300, 300));
    std::thread::sleep(Duration::from_millis(2000));

    let mut rng = rand::thread_rng();
    for i in 1..=count {
        if STOP.load(Ordering::SeqCst) {
            break;
        }
        let watch_secs = rng.gen_range(6..=12);
        log(serial, "NURTURE", format!("Đang xem video {}/{} (thời lượng {}s)...", i, count, watch_secs));
        std::thread::sleep(Duration::from_secs(watch_secs));

        // Thả tim ngẫu nhiên (double tap quanh tâm màn hình)
        if rng.gen_bool(0.75) {
            let (tx, ty) = (360 + rng.gen_range(-40..=40), 740 + rng.gen_range(-70..=70));
            let gap = rng.gen_range(90..=170);
            adb_shell(adb, serial, &format!("input tap {tx} {ty} && sleep 0.{gap:03} && input tap {} {}", tx + rng.gen_range(-6..=6), ty + rng.gen_range(-6..=6)));
            std::thread::sleep(Duration::from_millis(rng.gen_range(300..=600)));
        }

        // Vuốt sang video tiếp theo trên FYP
        adb_shell(adb, serial, &jitter_swipe_cmd(1100, 300, 280));
        std::thread::sleep(Duration::from_millis(rng.gen_range(1600..=2800)));
    }
    log(serial, "NURTURE", format!("Đã xem xong {} video FYP thành công!", count));
}

fn clean_filename(name: &str) -> String {
    name.chars()
        .map(|c| if c.is_alphanumeric() || c == '_' || c == '-' { c } else { '_' })
        .collect()
}

fn get_farm_containers_dir() -> PathBuf {
    if let Ok(exe) = std::env::current_exe() {
        if let Some(parent) = exe.parent() {
            return parent.join("farm_device_containers");
        }
    }
    PathBuf::from("farm_device_containers")
}

pub fn has_local_profile(acc: &LoginAccount) -> bool {
    let containers_dir = get_farm_containers_dir();
    if !containers_dir.exists() {
        return false;
    }
    if let Ok(entries) = fs::read_dir(&containers_dir) {
        let id_prefix = acc.id.map(|id| format!("acc_{}_", id));
        let user_clean = clean_filename(&acc.username);
        for entry in entries.flatten() {
            if let Ok(ft) = entry.file_type() {
                if ft.is_dir() {
                    let name = entry.file_name().to_string_lossy().to_string();
                    let matched = if let Some(ref p) = id_prefix {
                        name.starts_with(p)
                    } else {
                        name.contains(&user_clean)
                    };
                    if matched {
                        let tar = entry.path().join("data.tar.gz");
                        if tar.exists() {
                            if let Ok(m) = fs::metadata(&tar) {
                                if m.len() > 50_000 {
                                    return true;
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    false
}

fn backup_device_profile_to_pc(adb: &Path, serial: &str, profile_name: &str, acc: &LoginAccount) -> Result<f64, String> {
    let app_pkg = "com.zhiliaoapp.musically";
    let maxchanger_pkg = "com.minsoftware.maxchanger";

    let containers_dir = get_farm_containers_dir();
    let prof_dir = containers_dir.join(profile_name);
    let _ = fs::create_dir_all(&prof_dir);

    // 1. Dừng app TikTok để file SQLite hoàn tất ghi dữ liệu
    adb_shell(adb, serial, &format!("am force-stop {}", app_pkg));
    std::thread::sleep(Duration::from_millis(800));

    // 2. Kéo Device.xml từ MaxChanger
    let local_dev_xml = prof_dir.join("Device.xml");
    let _ = adb_raw(adb, serial, &["pull", &format!("/data/data/{}/shared_prefs/Device.xml", maxchanger_pkg), local_dev_xml.to_str().unwrap_or("")]);

    // 3. Kéo build.prop từ ROM
    let local_build_prop = prof_dir.join("build.prop");
    let _ = adb_raw(adb, serial, &["pull", "/system/build.prop", local_build_prop.to_str().unwrap_or("")]);

    // 4. Dọn dẹp cache và nén tar.gz siêu tối ưu (loại trừ thư viện .so trùng lặp và cache ML để chỉ còn ~5.5MB/nick)
    let compress_cmd = format!(
        "su -c \"find /data/data/{} -type s -delete && rm -rf /data/data/{}/cache/* /data/data/{}/files/offlineX /sdcard/tiktok_backups/* && mkdir -p /sdcard/tiktok_backups && tar --exclude=files/zoin --exclude=files/Pitaya --exclude=files/applog -czf /sdcard/tiktok_backups/data.tar.gz -C /data/data/{} .\"",
        app_pkg, app_pkg, app_pkg, app_pkg
    );
    let _ = adb_shell(adb, serial, &compress_cmd);

    // 5. Kéo data.tar.gz về PC
    let local_tar = prof_dir.join("data.tar.gz");
    let _ = adb_raw(adb, serial, &["pull", "/sdcard/tiktok_backups/data.tar.gz", local_tar.to_str().unwrap_or("")]);

    // 6. Xóa thư mục tạm trên thẻ nhớ
    let _ = adb_shell(adb, serial, "su -c 'rm -rf /sdcard/tiktok_backups'");

    // 7. Kiểm tra dung lượng và tạo meta.json
    let size_mb = if local_tar.exists() {
        let meta = fs::metadata(&local_tar).map_err(|e| e.to_string())?;
        let mb = (meta.len() as f64) / (1024.0 * 1024.0);
        (mb * 100.0).round() / 100.0
    } else {
        return Err("Không tạo được file data.tar.gz".to_string());
    };

    let model = adb_shell(adb, serial, "getprop ro.product.model").trim().to_string();
    let brand = adb_shell(adb, serial, "getprop ro.product.brand").trim().to_string();
    let android_id = adb_shell(adb, serial, "settings get secure android_id").trim().to_string();

    let meta_json = serde_json::json!({
        "account_id": acc.id,
        "username": acc.username,
        "email": acc.email,
        "profile_name": profile_name,
        "serial": serial,
        "brand": brand,
        "model": model,
        "android_id": android_id,
        "created_at": chrono::Local::now().format("%Y-%m-%d %H:%M:%S").to_string(),
        "data_size_mb": size_mb,
    });

    let _ = fs::write(prof_dir.join("meta.json"), serde_json::to_string_pretty(&meta_json).unwrap_or_default());

    Ok(size_mb)
}

fn input_text(adb: &Path, serial: &str, text: &str) {
    // 1. Ưu tiên gửi text qua ADB Keyboard bằng Base64 (chuẩn xác 100% mọi ký tự đặc biệt #, !, @, $, %, &, *, và chống rớt phím Shift)
    use base64::Engine;
    let b64 = base64::engine::general_purpose::STANDARD.encode(text);
    let b64_cmd = format!("am broadcast -a ADB_INPUT_B64 --es msg {}", b64);
    let out = adb_shell(adb, serial, &b64_cmd);
    if out.contains("result=0") {
        return;
    }

    // 2. Dự phòng: dùng lệnh input text chuẩn của Android nếu không có ADB Keyboard
    let esc = text.replace(' ', "%s").replace('\'', "'\\''");
    adb_shell(adb, serial, &format!("input text '{}'", esc));
}

fn launch_app(adb: &Path, serial: &str) {
    adb_shell(
        adb,
        serial,
        &format!("monkey -p {} -c android.intent.category.LAUNCHER 1", APP_PKG),
    );
}

fn relaunch_app(adb: &Path, serial: &str) {
    adb_shell(adb, serial, &format!("am force-stop {}", APP_PKG));
    std::thread::sleep(Duration::from_millis(800));
    launch_app(adb, serial);
}

fn flag_current_device_model(adb: &Path, serial: &str) {
    let curr_model = adb_shell(adb, serial, "getprop ro.product.model").trim().to_string();
    if !curr_model.is_empty() {
        let mut py_cmd = Command::new("python");
        py_cmd.arg("D:/Workspace/Python/QHTDautomation/maxchanger_generator.py").arg("--flag-model").arg(&curr_model);
        #[cfg(target_os = "windows")]
        {
            use std::os::windows::process::CommandExt;
            py_cmd.creation_flags(0x08000000);
        }
        let _ = py_cmd.output();
        warn!("[Device {}] Đã đưa model '{}' vào blacklist để các máy khác không fake trùng!", serial, curr_model);
    }
}

fn reboot_and_wait(adb: &Path, serial: &str) -> bool {
    log(serial, "REBOOT", "Khởi động lại máy (Reboot) để làm sạch 100% RAM và nạp ROM build.prop mới...");
    let _ = adb_raw(adb, serial, &["reboot"]);
    std::thread::sleep(Duration::from_secs(15));
    let start = Instant::now();
    let mut boot_ok = false;
    while start.elapsed() < Duration::from_secs(70) {
        let out = adb_shell(adb, serial, "getprop sys.boot_completed");
        if out.trim() == "1" {
            boot_ok = true;
            break;
        }
        std::thread::sleep(Duration::from_millis(2500));
    }

    if !boot_ok {
        warn!("[Device {}] Quá thời gian chờ boot_completed", serial);
        return false;
    }

    std::thread::sleep(Duration::from_millis(2000));
    log(serial, "REBOOT", "Thiết bị đã khởi động hoàn tất, hệ điều hành sạch 100% 🟢");
    adb_shell(adb, serial, "input keyevent 224");
    adb_shell(adb, serial, "input keyevent 82");

    // ĐỐI SOÁT VÀ CHỜ DỊCH VỤ HỆ ĐIỀU HÀNH (ACCESSIBILITY & WIFI) HOÀN TẤT SAU REBOOT:
    let srv_start = Instant::now();
    while srv_start.elapsed() < Duration::from_secs(30) {
        let acc_check = adb_shell(adb, serial, "service check accessibility");
        let wifi_check = adb_shell(adb, serial, "service check wifi");
        if acc_check.contains("found") && wifi_check.contains("found") {
            break;
        }
        std::thread::sleep(Duration::from_millis(2000));
    }

    // ĐỐI SOÁT VÀ CHỜ KẾT NỐI WIFI HOÀN TẤT SAU REBOOT:
    let wifi_start = Instant::now();
    let mut wifi_ready = false;
    while wifi_start.elapsed() < Duration::from_secs(25) {
        let wifi_info = adb_shell(adb, serial, "dumpsys wifi | grep 'Supplicant state'");
        if wifi_info.contains("COMPLETED") {
            wifi_ready = true;
            break;
        }
        std::thread::sleep(Duration::from_millis(2000));
    }

    if !wifi_ready {
        log(serial, "WIFI_KICK", "WiFi chưa kết nối sau reboot -> Tự động kích hoạt lại WiFi driver...");
        adb_shell(adb, serial, "svc wifi disable && sleep 2 && svc wifi enable");
        std::thread::sleep(Duration::from_millis(4000));
    }

    true
}

fn reset_app_clean(adb: &Path, serial: &str, hard_reboot: bool) {
    adb_shell(adb, serial, &format!("am force-stop {}", APP_PKG));
    adb_shell(adb, serial, &format!("pm clear {}", APP_PKG));

    // 1. Kích hoạt MaxChanger thay đổi toàn bộ thông tin phần cứng qua maxchanger_generator.py chuẩn đã kiểm chứng:
    // Sinh profile thật Exynos/Mali, ghi đè trực tiếp ROM /system/build.prop, nạp Device.xml và resetprop
    let mut py_cmd = Command::new("python");
    py_cmd.arg("D:/Workspace/Python/QHTDautomation/maxchanger_generator.py").arg(serial);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        py_cmd.creation_flags(0x08000000);
    }
    let py_res = py_cmd.output();
    if let Ok(ref out) = py_res {
        info!("[Device {}] MaxChanger info generator: {}", serial, String::from_utf8_lossy(&out.stdout).trim());
    }
    // Broadcast báo hiệu cho MaxChanger nhận Device.xml mới
    adb_shell(adb, serial, "am broadcast -a com.minsoftware.maxchanger.ADB_ACTION --es ADB_CHANGE true");

    // 2. Đồng bộ 100% Android ID giữa Device.xml và Settings OS, sinh GAID mới và dọn sạch dấu vết TikTok
    std::thread::sleep(Duration::from_millis(1500));

    // 3. THEO CHỈ ĐẠO MỚI CỦA ANH TONY: KHÔNG CẦN RESET MÁY CHO TỚI KHI BỊ MAXIMUM!
    // Tránh việc reset máy nhiều làm lỏng/drop kết nối USB của các máy.
    // CHỈ KHI NÀO hard_reboot == true (gặp Maximum attempts, dump fail >= 3 hoặc OTP 2 lần sai) -> MỚI REBOOT CỨNG!
    if hard_reboot {
        reboot_and_wait(adb, serial);
    }

    // 4. Lấy app UID và khôi phục zoin_dir
    let uid_out = adb_shell(adb, serial, &format!("dumpsys package {} | grep userId= | head -n 1", APP_PKG));
    let uid_num: u32 = uid_out
        .split('=')
        .nth(1)
        .and_then(|s| s.trim().parse().ok())
        .unwrap_or(10025);
    let u_tag = format!("u0_a{}", uid_num.saturating_sub(10000));

    let setup_cmd = format!(
        "su -c 'mkdir -p /data/data/{}/files && cp -r /sdcard/zoin_dir /data/data/{}/files/zoin && chown -R {}:{} /data/data/{}/files && chmod -R 775 /data/data/{}/files'",
        APP_PKG, APP_PKG, u_tag, u_tag, APP_PKG, APP_PKG
    );
    adb_shell(adb, serial, &setup_cmd);

    // CHỐT CHẶN BẮT BUỘC THEO CHỈ ĐẠO ANH TONY:
    // Kiểm tra thực tế xem máy đã THỰC SỰ KẾT NỐI ĐƯỢC TỚI TIKTOK hay chưa mới vào app!
    let mut net_ready = false;
    for _ in 1..=6 {
        let test_tt = adb_shell(adb, serial, "curl -s -m 4 -I https://www.tiktok.com").trim().to_string();
        if test_tt.contains("200") || test_tt.contains("302") || test_tt.contains("HTTP/") {
            net_ready = true;
            break;
        }
        std::thread::sleep(Duration::from_millis(1500));
    }
    if !net_ready {
        warn!("[Device {}] Thiết bị chưa thông mạng tới TikTok, chờ thêm 2 giây...", serial);
        std::thread::sleep(Duration::from_millis(2000));
    }

    launch_app(adb, serial);
    std::thread::sleep(Duration::from_millis(2500));
}

fn sleep_ms(ms: u64) {
    std::thread::sleep(Duration::from_millis(ms));
}

// ───────────────────────────── UI XML model ─────────────────────────────

#[derive(Clone, Debug, Default)]
struct UiNode {
    text: String,
    desc: String,
    rid: String,
    class: String,
    pkg: String,
    bounds: (i32, i32, i32, i32),
    clickable: bool,
    password: bool,
    selected: bool,
}

impl UiNode {
    fn center(&self) -> (i32, i32) {
        ((self.bounds.0 + self.bounds.2) / 2, (self.bounds.1 + self.bounds.3) / 2)
    }
    fn is_edit(&self) -> bool {
        self.class.ends_with("EditText")
    }
    fn is_button_like(&self) -> bool {
        self.clickable || self.class.ends_with("Button")
    }
    fn has_area(&self) -> bool {
        self.bounds.2 > self.bounds.0 && self.bounds.3 > self.bounds.1
    }
}

fn norm(s: &str) -> String {
    s.trim()
        .to_lowercase()
        .replace('’', "'")
        .replace('‘', "'")
        .replace('“', "\"")
        .replace('”', "\"")
}

struct Screen {
    nodes: Vec<UiNode>,
    pkg: String,
}

/// uiautomator đôi khi sinh `&#55357;` (surrogate) / ký tự điều khiển -> XML 1.0 không hợp lệ.
fn sanitize_xml(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    let mut i = 0;
    while i < s.len() {
        if s[i..].starts_with("&#") {
            if let Some(end) = s[i..].find(';') {
                let ent = &s[i + 2..i + end];
                let val = if let Some(h) = ent.strip_prefix('x').or_else(|| ent.strip_prefix('X')) {
                    u32::from_str_radix(h, 16).ok()
                } else {
                    ent.parse::<u32>().ok()
                };
                if let Some(v) = val {
                    let bad = (v < 32 && v != 9 && v != 10 && v != 13)
                        || (0xD800..=0xDFFF).contains(&v)
                        || v == 0xFFFE
                        || v == 0xFFFF;
                    if bad {
                        i += end + 1;
                        continue;
                    }
                }
            }
        }
        let ch = s[i..].chars().next().unwrap();
        if (ch as u32) < 32 && ch != '\n' && ch != '\r' && ch != '\t' {
            i += ch.len_utf8();
            continue;
        }
        out.push(ch);
        i += ch.len_utf8();
    }
    out
}

fn parse_bounds(b: &str) -> (i32, i32, i32, i32) {
    // "[x1,y1][x2,y2]"
    let nums: Vec<i32> = b
        .split(|c: char| !c.is_ascii_digit())
        .filter(|s| !s.is_empty())
        .filter_map(|s| s.parse().ok())
        .collect();
    if nums.len() == 4 {
        (nums[0], nums[1], nums[2], nums[3])
    } else {
        (0, 0, 0, 0)
    }
}

impl Screen {
    fn parse(xml: &str) -> Option<Screen> {
        let start = xml.find("<hierarchy")?;
        let end = xml.rfind("</hierarchy>").map(|e| e + "</hierarchy>".len()).unwrap_or(xml.len());
        let clean = sanitize_xml(&xml[start..end]);
        let doc = roxmltree::Document::parse(&clean).ok()?;
        let mut nodes = Vec::new();
        for n in doc.descendants().filter(|n| n.has_tag_name("node")) {
            let a = |k: &str| n.attribute(k).unwrap_or("").to_string();
            nodes.push(UiNode {
                text: a("text"),
                desc: a("content-desc"),
                rid: a("resource-id"),
                class: a("class"),
                pkg: a("package"),
                bounds: parse_bounds(n.attribute("bounds").unwrap_or("")),
                clickable: n.attribute("clickable") == Some("true"),
                password: n.attribute("password") == Some("true"),
                selected: n.attribute("selected") == Some("true"),
            });
        }
        if nodes.is_empty() {
            return None;
        }
        let pkg = nodes.iter().find(|n| !n.pkg.is_empty()).map(|n| n.pkg.clone()).unwrap_or_default();
        Some(Screen { nodes, pkg })
    }

    fn has_label(&self, labels: &[&str]) -> bool {
        self.nodes.iter().any(|n| {
            labels.iter().any(|l| {
                let l = norm(l);
                norm(&n.text) == l || norm(&n.desc) == l
            })
        })
    }

    fn has_contains(&self, subs: &[&str]) -> bool {
        self.nodes.iter().any(|n| {
            let t = norm(&n.text);
            let d = norm(&n.desc);
            subs.iter().any(|s| {
                let s = norm(s);
                t.contains(&s) || d.contains(&s)
            })
        })
    }

    /// Tìm nút khớp nhãn (text/desc), ưu tiên phần tử clickable/Button.
    fn find_btn(&self, labels: &[&str]) -> Option<&UiNode> {
        let matches: Vec<&UiNode> = self
            .nodes
            .iter()
            .filter(|n| n.has_area())
            .filter(|n| {
                labels.iter().any(|l| {
                    let l = norm(l);
                    norm(&n.text) == l || norm(&n.desc) == l
                })
            })
            .collect();
        matches
            .iter()
            .find(|n| n.is_button_like())
            .copied()
            .or_else(|| matches.first().copied())
    }

    fn edit_field(&self, password: bool) -> Option<&UiNode> {
        self.nodes.iter().find(|n| n.is_edit() && n.has_area() && n.password == password)
    }

    fn any_edit(&self) -> Option<&UiNode> {
        self.nodes.iter().find(|n| n.is_edit() && n.has_area())
    }

    /// Màn hình PROFILE CỦA CHÍNH MÌNH đã đăng nhập: có "Profile menu" / "Edit profile" / "Share profile" / "Following" / "Followers"
    fn own_profile_user(&self) -> Option<String> {
        let is_own_profile = self.has_contains(&[
            "edit profile", "share profile", "add bio", "profile menu", "change photo", "drafts", "favorites"
        ]) || (self.has_label(&["Following"]) && self.has_label(&["Followers"]))
           || (self.has_label(&["Profile menu"]) && self.has_label(&["Following"]));

        if !is_own_profile {
            return None;
        }

        // 1. Tìm text bắt đầu bằng @
        if let Some(n) = self.nodes.iter().find(|n| {
            let t = n.text.trim();
            t.starts_with('@') && t.len() > 1
        }) {
            return Some(n.text.trim().trim_start_matches('@').to_string());
        }

        // 2. Tìm content-desc bắt đầu bằng @
        if let Some(n) = self.nodes.iter().find(|n| {
            let d = n.desc.trim();
            d.starts_with('@') && d.len() > 1
        }) {
            return Some(n.desc.trim().trim_start_matches('@').to_string());
        }

        // 3. Nếu có "Edit profile" hoặc "Share profile" -> chắc chắn đã là profile chính mình đã đăng nhập
        Some(String::new())
    }

    fn error_kind(&self) -> Option<(&'static str, &'static str)> {
        if self.has_contains(&["maximum number of attempts", "too many attempts", "too many requests"]) {
            return Some(("RATE_LIMIT", "TikTok báo vượt giới hạn số lần thử (Maximum attempts)"));
        }
        if self.has_contains(&["incorrect account or password", "incorrect password", "wrong password", "account or password doesn"]) {
            return Some(("BAD_PASSWORD", "Sai tài khoản hoặc mật khẩu"));
        }
        if self.has_contains(&["permanently banned", "account was banned", "account has been banned"]) {
            return Some(("BANNED", "Tài khoản bị TikTok khóa/ban"));
        }
        if self.has_contains(&["drag the slider", "select 2 objects", "verify to continue", "puzzle piece"]) {
            return Some(("CAPTCHA", "TikTok yêu cầu CAPTCHA, không thể giải tự động"));
        }
        if self.has_contains(&[
            "couldn't find your account", "account doesn't exist", "no account found",
            "can't find this account", "user not found", "not registered",
            "account does not exist", "tài khoản không tồn tại", "find your account",
            "doesn't exist", "couldn't find", "create a new account"
        ]) {
            return Some(("NO_ACCOUNT", "Tài khoản không tồn tại trên TikTok"));
        }
        None
    }
}

fn dump_screen(adb: &Path, serial: &str) -> Option<Screen> {
    for _ in 0..4 {
        let out = adb_raw(
            adb,
            serial,
            &[
                "exec-out",
                "rm -f /data/local/tmp/qhtd_ui.xml; uiautomator dump --compressed /data/local/tmp/qhtd_ui.xml >/dev/null 2>&1; cat /data/local/tmp/qhtd_ui.xml",
            ],
        )?;
        let xml = String::from_utf8_lossy(&out).to_string();
        if let Some(s) = Screen::parse(&xml) {
            return Some(s);
        }
        sleep_ms(600);
    }
    None
}

fn tap_node(adb: &Path, serial: &str, n: &UiNode) {
    let (x, y) = n.center();
    tap(adb, serial, x, y);
}

/// Điền text vào ô: tap -> xóa sạch nội dung cũ -> gõ -> (tuỳ chọn) xác minh lại bằng XML.
fn fill_field(adb: &Path, serial: &str, field: &UiNode, text: &str, verify: bool) -> bool {
    tap_node(adb, serial, field);
    sleep_ms(500);
    let dels = std::cmp::max(field.text.chars().count(), 50) + 10;
    let mut cmd = String::from("input keyevent 123");
    for _ in 0..dels {
        cmd.push_str(" 67");
    }
    adb_shell(adb, serial, &cmd);
    sleep_ms(300);
    input_text(adb, serial, text);
    sleep_ms(600);
    if !verify {
        return true;
    }
    match dump_screen(adb, serial) {
        Some(s) => s
            .nodes
            .iter()
            .any(|n| n.is_edit() && !n.password && n.text.trim() == text.trim()),
        // Không đọc được XML (cursor/animation) -> tin là đã gõ đúng
        None => true,
    }
}

/// Bấm nút submit (Continue/Log in/...). Dump lại sau khi gõ; nếu dump hỏng (animation/toast)
/// thì dùng nút ở màn trước, cuối cùng tap mù vào vị trí nút chính (720x1480).
fn tap_submit(adb: &Path, serial: &str, labels: &[&str], prev: &Screen) {
    let s2 = dump_screen(adb, serial);
    let btn = s2
        .as_ref()
        .and_then(|s| s.find_btn(labels))
        .or_else(|| prev.find_btn(labels));
    match btn {
        Some(b) => tap_node(adb, serial, b),
        None => tap(adb, serial, 360, 1295),
    }
}

/// Đợi tới khi màn hình không còn thỏa `still` (TikTok xử lý mạng chậm) — tối đa `max_s` giây.
/// Tối ưu hóa: Polling chu kỳ 600ms, nếu phát hiện thông báo lỗi (NO_ACCOUNT, RATE_LIMIT...) thì THOÁT NGAY LẬP TỨC!
fn wait_leave<F: Fn(&Screen) -> bool>(adb: &Path, serial: &str, still: F, max_s: u64) {
    let start = Instant::now();
    sleep_ms(600);
    while start.elapsed() < Duration::from_secs(max_s) {
        if STOP.load(Ordering::SeqCst) {
            return;
        }
        if let Some(s) = dump_screen(adb, serial) {
            // Thoát ngay nếu đã xuất hiện thông báo lỗi từ TikTok (account doesn't exist, password, error...)
            if s.error_kind().is_some() || !still(&s) {
                return;
            }
        }
        sleep_ms(600);
    }
}

// ───────────────────────────── Detect current user ─────────────────────────────

/// Xác định nick TikTok đang đăng nhập trên máy (None nếu chưa login / không xác định).
pub fn detect_current_user(adb: &Path, serial: &str) -> Option<String> {
    adb_shell(adb, serial, "input keyevent 224");
    launch_app(adb, serial);
    sleep_ms(2500);
    for attempt in 0..3 {
        let s = match dump_screen(adb, serial) {
            Some(s) => s,
            None => {
                sleep_ms(1500);
                continue;
            }
        };
        if let Some(u) = s.own_profile_user() {
            return Some(u);
        }
        if s.pkg != APP_PKG {
            launch_app(adb, serial);
            sleep_ms(2500);
            continue;
        }
        if let Some(dismiss) = s.find_btn(&["Not now", "Skip", "Maybe later", "Later", "Got it"]) {
            tap_node(adb, serial, dismiss);
            sleep_ms(1200);
            continue;
        }
        if let Some(p) = s.find_btn(&["Profile"]) {
            tap_node(adb, serial, p);
            sleep_ms(2200);
            continue;
        }
        if attempt == 2 {
            break;
        }
        key(adb, serial, 4);
        sleep_ms(1200);
    }
    None
}

// ───────────────────────────── Per-device login worker ─────────────────────────────

fn notify_account_event(acc: &LoginAccount, _serial: &str, title: &str, details: &str) {
    let client_target = acc.client.as_deref().unwrap_or("tony");
    crate::telegram_notifier::notify_client(client_target, title, details);
}

fn finish(serial: &str, ok: bool, code: &str, msg: &str) {
    if ok {
        SUCC_COUNT.fetch_add(1, Ordering::SeqCst);
    } else if code == "MANUAL_LOGIN_REQUIRED" {
        SKIP_MANUAL_COUNT.fetch_add(1, Ordering::SeqCst);
    } else {
        FAIL_COUNT.fetch_add(1, Ordering::SeqCst);
    }
    upd(serial, |s| {
        s.state = if ok { "success".into() } else { "failed".into() };
        s.message = format!("{}: {}", code, msg);
    });
    log(serial, code, msg);
}

fn login_one(adb: PathBuf, serial: String, acc: LoginAccount, force_logout: bool) {
    let mut started = Instant::now();
    upd(&serial, |s| {
        s.state = "running".into();
        s.username = acc.username.clone();
        s.account_id = acc.id;
        s.message = String::new();
    });
    log(&serial, "START", format!("Login @{} bằng Native XML", acc.username));

    let has_2fa = !acc.secret.trim().is_empty();

    // 1. Kiểm tra hòm thư email trên C69 theo chỉ đạo anh Tony:
    // "Vậy em sửa lại logic em login bằng email thì bắt buộc phải kiểm tra email đó đọc được trên c69 nếu không đọc được mail thì phải dùng username để đăng nhập, nhưng nếu email không đọc được và ko có 2fa code thì em bỏ qua note lại luôn Email cần login tay."
    let mut resolved_email_id: Option<u64> = acc.email_id;
    let target_email: Option<String> = if let Some(ref em) = acc.email {
        let em_t = em.trim();
        if em_t.contains('@') { Some(em_t.to_string()) } else { None }
    } else if acc.username.contains('@') {
        Some(acc.username.trim().to_string())
    } else {
        None
    };

    if resolved_email_id.is_none() {
        if let Some(ref em) = target_email {
            resolved_email_id = resolve_c69_email_id(em);
            if resolved_email_id.is_none() {
                let u_prefix = em.split('@').next().unwrap_or(em);
                resolved_email_id = resolve_c69_email_id(u_prefix);
            }
        } else {
            resolved_email_id = resolve_c69_email_id(&acc.username);
        }
        if let Some(eid) = resolved_email_id {
            log(&serial, "EMAIL_ID", format!("Tìm thấy C69 Email ID: #{} cho @{}", eid, acc.username));
        }
    }

    let mut email_readable = false;
    let mut discovered_real_username: Option<String> = None;
    if let Some(eid) = resolved_email_id {
        let (email_check, real_u_opt) = check_c69_email_status(eid);
        discovered_real_username = real_u_opt;
        if email_check == C69EmailCheck::Unregistered && !has_2fa {
            let unreg_msg = "Tài khoản chưa hoàn tất đăng ký trên TikTok (chỉ có mã verify signup dở dang)";
            log(&serial, "UNREGISTERED", format!("Tài khoản @{} chưa hoàn tất đăng ký -> Chuyển ngay Status 2 theo chỉ đạo anh Tony!", acc.username));
            finish(&serial, false, "NO_ACCOUNT", unreg_msg);
            let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, unreg_msg);
            if let Some(aid) = acc.id {
                sync_c69_timeline_log(aid, &fail_log, Some(2));
            } else {
                sync_c69_log_by_query(&acc.username, &fail_log, Some(2));
            }
            notify_account_event(&acc, &serial, "Chưa Hoàn Tất Đăng Ký ❌", &fail_log);
            return;
        }
        email_readable = email_check == C69EmailCheck::Readable;
        if email_readable {
            log(&serial, "EMAIL_CHECK", format!("Hòm thư C69 email #{} đọc tốt 🟢", eid));
        } else {
            log(&serial, "EMAIL_CHECK", format!("Hòm thư C69 email #{} KHÔNG đọc được ⚠️", eid));
        }
    }

    // THEO CHỈ ĐẠO CỐT LÕI CỦA ANH TONY:
    // "Tất cả lô này có 2fa key thì login bằng username và 2fa key chứ không cần thông qua email"
    let clean_user = acc.username.trim();
    let mut current_iden = if has_2fa {
        // CÓ 2FA: BẮT BUỘC ĐĂNG NHẬP THẲNG BẰNG USERNAME + 2FA KEY, 100% TỰ CHỦ KHÔNG QUA EMAIL!
        log(&serial, "2FA_DIRECT", format!("Tài khoản @{} có 2FA Secret -> Đi thẳng bằng Username và mã 2FA TOTP!", clean_user));
        clean_user.to_string()
    } else {
        // KHÔNG CÓ 2FA: BẮT BUỘC PHẢI CÓ HÒM THƯ EMAIL ĐỌC ĐƯỢC OTP TRÊN C69:
        if !email_readable {
            let manual_msg = "Email cần login tay (không có 2FA và hòm thư C69 không đọc được OTP)";
            log(&serial, "MANUAL_REQUIRED", format!("Tài khoản @{} không có 2FA và email không đọc được trên C69 -> Bỏ qua, note C69 '{}'", acc.username, manual_msg));
            if let Some(aid) = acc.id {
                sync_c69_timeline_log(aid, manual_msg, None);
            } else {
                sync_c69_log_by_query(&acc.username, manual_msg, None);
            }
            finish(&serial, false, "MANUAL_LOGIN_REQUIRED", manual_msg);
            notify_account_event(&acc, &serial, "Cần Đăng Nhập Thủ Công ⚠️", &format!("Tài khoản @{}: {}", acc.username, manual_msg));
            return;
        }

        // Nếu email đọc được, ưu tiên username chuẩn hoặc email:
        if let Some(ref real_u) = discovered_real_username {
            log(&serial, "REAL_USER", format!("Phát hiện username thật trên TikTok từ Email C69: @{} (thay vì '{}')", real_u, clean_user));
            real_u.clone()
        } else if !clean_user.contains('@') && !clean_user.contains(' ') && !clean_user.is_empty() {
            clean_user.to_string()
        } else if target_email.is_some() && email_readable {
            target_email.as_ref().unwrap().clone()
        } else if clean_user.contains(' ') {
            let parts: Vec<&str> = clean_user.split_whitespace().collect();
            if let Some(last) = parts.last() {
                if last.chars().all(|c| c.is_alphanumeric() || c == '_' || c == '.') {
                    last.to_string()
                } else {
                    let err_msg = "Username không hợp lệ trên TikTok (chứa dấu cách, không có email)";
                    finish(&serial, false, "INVALID_USERNAME", err_msg);
                    let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, err_msg);
                    if let Some(aid) = acc.id {
                        sync_c69_timeline_log(aid, &fail_log, Some(2));
                    }
                    notify_account_event(&acc, &serial, "Sai Định Dạng Username ❌", &fail_log);
                    return;
                }
            } else {
                clean_user.to_string()
            }
        } else {
            clean_user.to_string()
        }
    };
    log(&serial, "IDEN_CHOSEN", format!("Định danh đăng nhập khởi điểm: {} (2FA: {}, Email readable: {})", current_iden, has_2fa, email_readable));

    // BẮT BUỘC NGUYÊN TẮC CỐT LÕI (CHỈ ĐẠO ANH TONY):
    // 1. ĐỔI PROXY MỚI VÀ ĐỐI SOÁT INTERNET THỰC TẾ TRÊN MÁY:
    match rotate_device_proxy(&adb, &serial) {
        Ok(new_px) => {
            log(&serial, "PROXY_INIT", format!("Đã gán và đối soát IP US mới thành công: {}", new_px));
        }
        Err(e) => {
            log(&serial, "PROXY_FAILED", format!("Lỗi đổi proxy: {}. Dừng tài khoản này để bảo đảm an toàn", e));
            finish(&serial, false, "NO_INTERNET", &e);
            return;
        }
    }

    adb_shell(&adb, &serial, "input keyevent 224");
    adb_shell(&adb, &serial, "input keyevent 82");

    // 2. ĐỔI PHONE INFO MỚI CỨNG (MaxChanger chuẩn 100% Android 9/Exynos/Mali) QUA SOFT RESET (3 GIÂY, KHÔNG REBOOT ĐỂ BẢO VỆ CỔNG USB VÀ CHỐNG KẸT MÁY):
    reset_app_clean(&adb, &serial, false);

    let mut dump_fail = 0;
    let mut nav_count = 0;
    let mut interests_picked = false;
    let mut fresh_login = false;
    let mut onboarding_steps = 0;
    let mut unknown = 0;
    let mut blank_consecutive = 0;
    let (mut user_tries, mut pwd_tries, mut totp_tries, mut logout_tries) = (0, 0, 0, 0);
    let mut email_otp_tries = 0;
    let mut last_submitted_otp: Option<String> = None;
    let mut otp_full_restarts = 0;
    let mut logging_out = false;
    let mut last_pwd_submit: Option<Instant> = None;
    let mut proxy_rotates = 0;
    let mut bday_tries = 0;
    let mut net_retries = 0;
    let mut username_stuck_restarts = 0;
    let mut tried_alt_iden_on_rate = false;

    for step in 0..MAX_STEPS {
        if STOP.load(Ordering::SeqCst) {
            finish(&serial, false, "STOPPED", "Đã dừng theo yêu cầu");
            return;
        }
        if started.elapsed() > DEVICE_TIMEOUT {
            finish(&serial, false, "TIMEOUT", "Quá thời gian login (420s)");
            let fail_log = format!("Đăng nhập dừng trên thiết bị {}: Quá thời gian chờ phản hồi từ TikTok (420s)", serial);
            if let Some(aid) = acc.id {
                sync_c69_timeline_log(aid, &fail_log, None);
            } else {
                sync_c69_log_by_query(&acc.username, &fail_log, None);
            }
            notify_account_event(&acc, &serial, "Hết Giờ Chờ ⚠️", &fail_log);
            return;
        }

        let scr = match dump_screen(&adb, &serial) {
            Some(s) => {
                dump_fail = 0;
                s
            }
            None => {
                dump_fail += 1;
                log(&serial, "DUMP", format!("Không đọc được UI XML (lần {})", dump_fail));
                if dump_fail == 1 {
                    // Lần 1: Vuốt nhẹ để tắt overlay animation hoặc tooltip
                    swipe_up(&adb, &serial);
                } else if dump_fail == 2 {
                    // Lần 2: Kiểm tra nhanh xem dịch vụ accessibility của Android có bị crash không
                    let acc_check = adb_shell(&adb, &serial, "service check accessibility");
                    if !acc_check.contains("found") {
                        log(&serial, "REBOOT", "Dịch vụ Accessibility của Android bị tắt -> Khởi động lại máy (Reboot) ngay lập tức!");
                        reboot_and_wait(&adb, &serial);
                        dump_fail = 0;
                        continue;
                    }
                    relaunch_app(&adb, &serial);
                } else if dump_fail >= 3 {
                    // THEO CHỈ ĐẠO CHÍNH XÁC CỦA ANH TONY:
                    // "A nghĩ dump fail khoảng 3 lần là em phải xử lý ngay rồi ấy 6 lần quá nhiều"
                    log(&serial, "REBOOT", "Không đọc được UI XML đến lần 3 -> Lập tức khởi động lại máy (Reboot) để cứu thiết bị theo chỉ đạo anh Tony!");
                    reboot_and_wait(&adb, &serial);
                    dump_fail = 0;
                    continue;
                }
                sleep_ms(1000);
                continue;
            }
        };

        // 0.1 XỬ LÝ MÀN HÌNH BIRTHDAY / POPUP ADD BIRTHDAY THEO CHỈ ĐẠO ANH TONY:
        if scr.has_contains(&["when's your birthday", "set your birthday", "add birthday", "your birthdate", "enter your birthdate"]) {
            // 1. Nếu đây là màn hình xác nhận ngày sinh sau khi đăng nhập (có nút Continue và chân trang hỏi 'Sign up'):
            let has_login_link = scr.nodes.iter().any(|n| n.has_area() && norm(&n.text) == "log in" && n.bounds.1 > 1200);
            if !has_login_link && scr.has_label(&["Continue", "Next"]) {
                bday_tries += 1;
                log(&serial, "BIRTHDAY_CONFIRM", format!("Phát hiện TikTok yêu cầu xác nhận ngày sinh sau login (lần {}) -> Cuộn năm sinh lùi >= 18 tuổi và bấm Continue theo chỉ đạo anh Tony!", bday_tries));
                if bday_tries > 4 {
                    log(&serial, "BIRTHDAY_STUCK", "Xác nhận ngày sinh không qua quá 4 lần -> Relaunch app để phục hồi giao diện!");
                    relaunch_app(&adb, &serial);
                    bday_tries = 0;
                    sleep_ms(3000);
                    continue;
                }

                // Cuộn cả 3 trục Month (x=184), Day (x=360), Year (x=536) để kích hoạt nút Continue sáng lên:
                adb_shell(&adb, &serial, "input swipe 184 800 184 920 150");
                sleep_ms(150);
                adb_shell(&adb, &serial, "input swipe 360 800 360 920 150");
                sleep_ms(150);
                // Picker Year nằm trong bounds [466, 742][606, 971]. Vuốt lùi năm về 1990-2000 (>= 25 tuổi)
                for _ in 0..8 {
                    adb_shell(&adb, &serial, "input swipe 536 760 536 960 120");
                    sleep_ms(150);
                }
                sleep_ms(600);
                // Bấm nút Continue tại (360, 1268)
                if let Some(cont_btn) = scr.find_btn(&["Continue", "Next"]) {
                    tap_node(&adb, &serial, cont_btn);
                } else {
                    tap(&adb, &serial, 360, 1268);
                }
                sleep_ms(2500);
                continue;
            }

            // 2. Nếu là màn hình Sign Up của app chưa đăng nhập:
            bday_tries += 1;
            log(&serial, "BIRTHDAY", format!("Phát hiện màn hình Birthday (Sign up flow, lần {}) -> Chuyển về form Login theo chỉ đạo anh Tony", bday_tries));
            if bday_tries > 3 {
                // Rơi sâu vào flow Sign up -> Relaunch app sạch sẽ để về màn Log in to TikTok, TUYỆT ĐỐI KHÔNG đánh lỗi tài khoản!
                log(&serial, "BIRTHDAY_RESET", "Bị kẹt luồng Sign up Birthday -> Relaunch app để mở lại màn Log in to TikTok");
                relaunch_app(&adb, &serial);
                bday_tries = 0;
                sleep_ms(3000);
                continue;
            }
            if let Some(login_btn) = scr.nodes.iter().find(|n| {
                n.has_area() && norm(&n.text) == "log in" && n.bounds.1 > 1200
            }) {
                log(&serial, "BIRTHDAY", "Chạm trực tiếp chữ đỏ Log in ở chân trang Birthday");
                tap_node(&adb, &serial, login_btn);
                sleep_ms(2000);
                continue;
            }
            // Dự phòng: chạm tọa độ chuẩn chữ đỏ chân trang (525, 1360)
            log(&serial, "BIRTHDAY", "Chạm chân trang (525, 1360) để chuyển sang Log in to TikTok");
            tap(&adb, &serial, 525, 1360);
            sleep_ms(2000);
            continue;
        }

        // 0.0 XỬ LÝ TỰ ĐỘNG ĐỔI PROXY KHI BỊ MAXIMUM ATTEMPTS, NO INTERNET HOẶC GẶP CAPTCHA THEO CHỈ ĐẠO ANH TONY:
        let is_rate_limit = scr.has_contains(&["maximum number of attempts", "too many attempts", "too many requests"]);
        let is_no_internet = scr.has_contains(&["no internet connection", "no internet", "network error"]);
        let is_captcha = scr.has_contains(&[
            "drag the slider", "select 2 objects", "verify to continue", "puzzle piece", 
            "slide to complete the puzzle", "security check", "rotate the image"
        ]) || scr.error_kind().map(|(c, _)| c == "CAPTCHA").unwrap_or(false);

        // 0.0.1 XỬ LÝ LỖI MẠNG (NO INTERNET) THEO ĐÚNG CHỈ ĐẠO CỐT LÕI CỦA ANH TONY:
        // "Nếu bị no internet connection khi dùng email thì ngay lập tức đăng nhập thử bằng username
        // nếu có username, nếu không có thì lấy tiền tố email đăng nhập thử. Nếu mà báo tài khoản không tồn tại
        // hoặc qua password có nghĩa là proxy không vấn đề gì mà là email rác thì chuyển ngay tài khoản không tồn tại."
        if is_no_internet && !is_rate_limit && !is_captcha {
            if current_iden.contains('@') {
                // Xác định username thử nghiệm: ưu tiên acc.username (nếu không chứa @), nếu không thì lấy tiền tố trước dấu @ của email
                let fallback_user = if !acc.username.contains('@') && !acc.username.trim().is_empty() {
                    acc.username.trim().to_string()
                } else {
                    current_iden.split('@').next().unwrap_or("").trim().to_string()
                };

                if !fallback_user.is_empty() && fallback_user != current_iden {
                    log(&serial, "NET_FALLBACK_USER", format!("Bị 'No internet' khi dùng email {} -> Thử ngay bằng Username/Tiền tố (@{}) theo chỉ đạo anh Tony!", current_iden, fallback_user));
                    current_iden = fallback_user;
                    if let Some(ef) = scr.edit_field(false) {
                        let ef = ef.clone();
                        let ok = fill_field(&adb, &serial, &ef, &current_iden, true);
                        if ok {
                            sleep_ms(400);
                            tap_submit(&adb, &serial, &["Continue", "Next", "Log in"], &scr);
                            sleep_ms(3000);

                            // Kiểm tra màn hình phản hồi sau khi submit username/tiền tố
                            if let Some(s_after) = dump_screen(&adb, &serial) {
                                // 1. Nếu TikTok báo tài khoản không tồn tại:
                                if s_after.has_contains(&[
                                    "couldn't find your account",
                                    "account doesn't exist",
                                    "no account found",
                                    "can't find this account",
                                    "user not found",
                                    "not registered",
                                    "tài khoản không tồn tại"
                                ]) {
                                    let err_msg = format!("Proxy OK (không lỗi mạng). Email '{}' là email rác/không tồn tại trên TikTok", acc.email.as_deref().unwrap_or(&acc.username));
                                    log(&serial, "NO_ACCOUNT", format!("{} -> Chuyển ngay Status 2 (Không tồn tại)", err_msg));
                                    finish(&serial, false, "NO_ACCOUNT", &err_msg);
                                    let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, err_msg);
                                    if let Some(aid) = acc.id {
                                        sync_c69_timeline_log(aid, &fail_log, Some(2));
                                    } else {
                                        sync_c69_log_by_query(&acc.username, &fail_log, Some(2));
                                    }
                                    notify_account_event(&acc, &serial, "Tài Khoản Không Tồn Tại ❌", &fail_log);
                                    return;
                                }

                                // 2. Nếu đã qua được bước Password hoặc bước xác thực (chứng tỏ proxy hoàn toàn sống, chỉ do email cũ bị rác/ngắt socket):
                                if s_after.edit_field(true).is_some() || s_after.has_contains(&["enter password", "password", "verify", "2-step"]) {
                                    log(&serial, "NET_RESOLVED", "Qua được bước Password! Khẳng định Proxy hoạt động tốt, đã khắc phục lỗi No internet.");
                                    continue;
                                }
                            }
                            continue;
                        }
                    }
                }
            }

            net_retries += 1;
            if net_retries <= 2 {
                // THEO CHỈ ĐẠO ANH TONY: Khi gặp lỗi No Internet, chờ 15s cho đường truyền ổn định rồi bấm lại!
                log(&serial, "NET_WAIT", format!("Phát hiện 'No internet' (lần {}) -> Chờ 15s cho SOCKS tunnel và TikTok socket ổn định theo chỉ đạo anh Tony...", net_retries));
                for _ in 1..=5 {
                    if STOP.load(Ordering::SeqCst) { break; }
                    sleep_ms(3000);
                }
                // Thử warm-up lại kết nối tới TikTok từ máy
                let _ = adb_shell(&adb, &serial, "curl -s -m 4 -I https://www.tiktok.com");
                
                log(&serial, "NET_RETRY", "Hết 15s chờ -> Bấm lại Continue / Try again để vượt qua lỗi mạng...");
                if let Some(ef) = scr.edit_field(false) {
                    tap_node(&adb, &serial, &ef);
                    sleep_ms(300);
                }
                tap_submit(&adb, &serial, &["Continue", "Next", "Log in", "Try again", "Retry"], &scr);
                sleep_ms(3000);
                continue;
            }

            // Nếu sau 15s bấm lại vẫn kẹt -> BẮT BUỘC ĐỔI PROXY MỚI TỪ ROUTER C69:
            log(&serial, "NO_INTERNET", format!("Sau 15s bấm lại vẫn lỗi mạng -> Bắt buộc xoay proxy mới từ Router C69 cho tài khoản @{} (TUYỆT ĐỐI KHÔNG ĐÁNH LỖI TÀI KHOẢN)...", acc.username));
            match rotate_device_proxy(&adb, &serial) {
                Ok(new_px) => {
                    log(&serial, "PROXY_ROTATE", format!("Đã đổi sang proxy có mạng TikTok thành công: {} -> Reset app và tiếp tục tài khoản @{}", new_px, acc.username));
                    reset_app_clean(&adb, &serial, false);
                    user_tries = 0;
                    pwd_tries = 0;
                    bday_tries = 0;
                    net_retries = 0;
                    continue;
                }
                Err(e) => {
                    log(&serial, "PROXY_ROTATE", format!("Chưa tìm được proxy vào được TikTok: {}. Tiếp tục đổi proxy khác...", e));
                    sleep_ms(2500);
                    continue; // Tiếp tục vòng lặp để đổi tiếp, CẤM gán tài khoản là lỗi!
                }
            }
        }

        // 0.0.1b XỬ LÝ CAPTCHA PUZZLE TỰ ĐỘNG BẰNG RUST SOLVER (TRÁNH BỊ REBOOT HOẶC ROTATE PROXY OAN!):
        if is_captcha {
            log(&serial, "CAPTCHA", "Phát hiện Captcha Puzzle trên màn hình -> Tiến hành tự động phân tích và kéo trượt giải...");
            match crate::captcha_solver::solve_if_present_sync(&adb, &serial, 720, 1480) {
                Ok(true) => {
                    log(&serial, "CAPTCHA_OK", "Đã tự động giải xong Captcha Puzzle thành công! Tiếp tục luồng đăng nhập ✅");
                    sleep_ms(2000);
                    continue;
                }
                Ok(false) => {
                    continue;
                }
                Err(e) => {
                    log(&serial, "CAPTCHA_FAIL", format!("Giải Captcha không thành công: {}. Tiến hành xử lý xoay proxy...", e));
                }
            }
        }

        // 0.0.2 XỬ LÝ RATE LIMIT HOẶC CAPTCHA (CHỈ KHI TIKTOK THỰC SỰ TRẢ VỀ RATE LIMIT / CAPTCHA):
        if is_rate_limit || is_captcha {
            // NẾU BỊ MAXIMUM ATTEMPTS: Thử ngay bằng định danh thay thế (Username <-> Email) TRƯỚC KHI tốn 3 lần đổi proxy và reboot!
            if is_rate_limit && !is_captcha && !tried_alt_iden_on_rate {
                tried_alt_iden_on_rate = true;
                if !current_iden.contains('@') {
                    if let Some(ref em) = target_email {
                        let em_clean = em.trim();
                        if em_clean.contains('@') && em_clean != current_iden {
                            log(&serial, "RATE_FALLBACK_EMAIL", format!("Bị Maximum attempts khi dùng Username '{}' -> Thử ngay bằng Email '{}' trước khi rotate proxy!", current_iden, em_clean));
                            current_iden = em_clean.to_string();
                            relaunch_app(&adb, &serial);
                            user_tries = 0;
                            pwd_tries = 0;
                            sleep_ms(2500);
                            continue;
                        }
                    }
                } else {
                    let u_candidate = if !acc.username.contains('@') && !acc.username.trim().is_empty() {
                        acc.username.trim().to_string()
                    } else {
                        current_iden.split('@').next().unwrap_or("").trim().to_string()
                    };
                    if !u_candidate.is_empty() && u_candidate != current_iden {
                        log(&serial, "RATE_FALLBACK_USER", format!("Bị Maximum attempts khi dùng Email '{}' -> Thử ngay bằng Username/Tiền tố '{}' trước khi rotate proxy!", current_iden, u_candidate));
                        current_iden = u_candidate;
                        relaunch_app(&adb, &serial);
                        user_tries = 0;
                        pwd_tries = 0;
                        sleep_ms(2500);
                        continue;
                    }
                }
            }

            if is_rate_limit {
                flag_current_device_model(&adb, &serial); // ĐƯA MODEL NÀY VÀO BLACKLIST ĐỂ CÁC MÁY KHÁC TRÁNH FAKE TRÙNG
            }
            if proxy_rotates < 3 {
                proxy_rotates += 1;
                let reason = if is_captcha { "Thử thách CAPTCHA" } else { "Rate-limit Maximum attempts" };
                log(&serial, "PROXY_ROTATE", format!("Phát hiện {} -> Tự động xoay proxy mới từ Router C69 (lần {}/3)...", reason, proxy_rotates));
                match rotate_device_proxy(&adb, &serial) {
                    Ok(new_px) => {
                        log(&serial, "PROXY_ROTATE", format!("Đã gán proxy mới: {} -> Tiến hành Reset máy sạch sẽ (Reboot) và chạy lại từ đầu với nick này", new_px));
                        reset_app_clean(&adb, &serial, true);
                        started = Instant::now(); // Reset lại timer cho chu kỳ proxy mới!
                        user_tries = 0;
                        username_stuck_restarts = 0;
                        pwd_tries = 0;
                        bday_tries = 0;
                        continue;
                    }
                    Err(e) => {
                        log(&serial, "PROXY_ROTATE", format!("Không xoay được proxy: {}", e));
                    }
                }
            } else {
                let err_code = if is_captcha { "CAPTCHA" } else { "RATE_LIMIT" };
                let err_msg = "Đã đổi proxy 3 lần vẫn dính rate limit/CAPTCHA";
                finish(&serial, false, err_code, err_msg);
                let fail_log = format!("Đăng nhập dừng trên thiết bị {}: {}", serial, err_msg);
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &fail_log, Some(3));
                } else {
                    sync_c69_log_by_query(&acc.username, &fail_log, Some(3));
                }
                notify_account_event(&acc, &serial, "Cảnh Báo Rate-limit / CAPTCHA ⚠️", &fail_log);
                return;
            }
        }

        // 0. Lỗi cứng từ TikTok
        if let Some((code, msg)) = scr.error_kind() {
            if code == "RATE_LIMIT" || code == "CAPTCHA" {
                // Đã xử lý ở trên qua rotate proxy, bỏ qua return ngay
            } else if code == "NO_ACCOUNT" {
                log(&serial, "NO_ACCOUNT", format!("Phát hiện TikTok báo '{}' -> Kết luận ngay lập tức!", msg));
                finish(&serial, false, code, msg);
                let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, msg);
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &fail_log, Some(2));
                } else {
                    sync_c69_log_by_query(&acc.username, &fail_log, Some(2));
                }
                notify_account_event(&acc, &serial, "Tài Khoản Không Tồn Tại ❌", &fail_log);
                return;
            } else if code != "BAD_PASSWORD" || pwd_tries > 0 {
                finish(&serial, false, code, msg);
                let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, msg);
                let st = if code == "BANNED" || code == "NO_ACCOUNT" { Some(2) } else if code == "BAD_PASSWORD" { Some(5) } else { None };
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &fail_log, st);
                } else {
                    sync_c69_log_by_query(&acc.username, &fail_log, st);
                }
                notify_account_event(&acc, &serial, "Đăng Nhập Thất Bại ❌", &fail_log);
                return;
            }
        }

        // 1. App không ở foreground
        if scr.pkg != APP_PKG {
            let is_perm = scr.pkg.contains("packageinstaller") || scr.pkg.contains("permissioncontroller");
            if is_perm {
                if let Some(deny) = scr.nodes.iter().find(|n| {
                    n.has_area() && (n.rid.contains("permission_deny") || n.rid.contains("deny"))
                }).or_else(|| scr.find_btn(&["Don't allow", "Deny", "Don’t allow"])) {
                    log(&serial, "PERMISSION", "Từ chối popup quyền hệ thống");
                    tap_node(&adb, &serial, deny);
                    sleep_ms(1200);
                    continue;
                }
            }
            log(&serial, "FOREGROUND", format!("Foreground là {}, mở lại TikTok", scr.pkg));
            launch_app(&adb, &serial);
            sleep_ms(2500);
            continue;
        }

        let cur_user = scr.own_profile_user();

        // 2. Đã ở profile của chính mình
        if let Some(ref u) = cur_user {
            let final_u = if u.is_empty() { acc.username.clone() } else { u.clone() };
            upd(&serial, |s| s.current_user = final_u.clone());
            let match_user = fresh_login
                || u.is_empty()
                || u.eq_ignore_ascii_case(&acc.username)
                || acc.username.split('@').next().map(|p| u.eq_ignore_ascii_case(p)).unwrap_or(false);
            if match_user {
                finish(&serial, true, "SUCCESS", &format!("Đã đăng nhập @{} (Account: {})", final_u, acc.username));
                let action_log = format!("Tài khoản đang hoạt động tốt trên thiết bị {} (User: @{}, Account: {})", serial, final_u, acc.username);
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &action_log, Some(0));
                } else {
                    sync_c69_log_by_query(&acc.username, &action_log, Some(0));
                }
                notify_account_event(&acc, &serial, "Tài Khoản Hoạt Động Tốt 🟢", &action_log);
                return;
            }
            if !force_logout {
                finish(&serial, false, "OTHER_ACCOUNT", &format!("Máy đang login @{} (không phải @{}), chưa bật force_logout", u, acc.username));
                return;
            }
            if !logging_out {
                log(&serial, "LOGOUT", format!("Đang login @{} -> đăng xuất để vào @{}", u, acc.username));
            }
            logging_out = true;
        }

        // 3. Luồng đăng xuất (nick sai)
        if logging_out {
            logout_tries += 1;
            if logout_tries > 14 {
                finish(&serial, false, "LOGOUT_FAILED", "Không đăng xuất được nick cũ qua UI");
                return;
            }
            // 3a. Hộp thoại xác nhận (có Cancel + Log out)
            if scr.has_label(&["Cancel"]) && scr.has_label(&["Log out"]) {
                let confirm = scr
                    .nodes
                    .iter()
                    .filter(|n| n.has_area() && norm(&n.text) == "log out" && n.is_button_like())
                    .last()
                    .or_else(|| scr.nodes.iter().filter(|n| n.has_area() && norm(&n.text) == "log out").last());
                if let Some(c) = confirm {
                    log(&serial, "LOGOUT", "Xác nhận Log out");
                    tap_node(&adb, &serial, c);
                    sleep_ms(3500);
                    continue;
                }
            }
            // 3b. Trang Settings: cuộn tìm "Log out"
            if scr.has_label(&["Settings and privacy"]) && !scr.has_label(&["Profile menu"]) {
                if let Some(lo) = scr.find_btn(&["Log out"]) {
                    log(&serial, "LOGOUT", "Bấm Log out trong Settings");
                    tap_node(&adb, &serial, lo);
                    sleep_ms(1800);
                } else {
                    swipe_up(&adb, &serial);
                    sleep_ms(900);
                }
                continue;
            }
            // 3c. Menu bên (sau khi bấm Profile menu): có mục "Settings and privacy"
            if let Some(sp) = scr.find_btn(&["Settings and privacy"]) {
                log(&serial, "LOGOUT", "Mở Settings and privacy");
                tap_node(&adb, &serial, sp);
                sleep_ms(2000);
                continue;
            }
            // 3d. Đang ở profile: mở Profile menu
            if cur_user.is_some() {
                if let Some(pm) = scr.find_btn(&["Profile menu"]) {
                    tap_node(&adb, &serial, pm);
                    sleep_ms(1800);
                    continue;
                }
            }
            // Không nhận diện được -> rơi xuống xử lý chung (popup/back)
        }

        // 3.5 Onboarding SAU khi login thành công (Choose your interests...). KHÔNG được BACK ở đây
        // vì BACK sẽ thoát về trang login. Chọn 3 sở thích rồi bấm Next/Skip.
        if scr.has_contains(&["choose your interests", "get better video recommendations"]) {
            onboarding_steps += 1;
            pwd_tries = 0;
            user_tries = 0;
            if onboarding_steps > 12 {
                finish(&serial, false, "ONBOARDING_STUCK", "Kẹt ở màn Choose your interests");
                return;
            }
            if !interests_picked {
                log(&serial, "ONBOARDING", "Chọn sở thích (Comedy/Music/Food)");
                for label in ["Comedy", "Music", "Food"] {
                    if let Some(n) = scr.find_btn(&[label]) {
                        tap_node(&adb, &serial, n);
                        sleep_ms(500);
                    }
                }
                interests_picked = true;
                sleep_ms(800);
                continue;
            }
            if let Some(b) = scr.find_btn(&["Next", "Done", "Continue", "Skip", "Confirm"]) {
                log(&serial, "ONBOARDING", format!("Bấm \"{}\"", b.label_owned()));
                tap_node(&adb, &serial, b);
            } else {
                swipe_up(&adb, &serial);
            }
            sleep_ms(2500);
            continue;
        }

        // 3.65 Bottom sheet "Choose an option to log in" (TikTok yêu cầu chọn phương thức phục hồi/đăng nhập)
        let is_choose_login_option = scr.has_contains(&[
            "choose an option to log in",
            "choose an option",
            "reset password with email",
            "reset password with phone",
            "recover your account",
            "log in with email",
            "log in with email code"
        ]);
        if is_choose_login_option {
            log(&serial, "LOGIN_OPTION", format!("Phát hiện popup 'Choose an option to log in' cho @{}", acc.username));
            // Ưu tiên chọn "Reset password with email" hoặc "Log in with email" để đón link/OTP từ C69
            if let Some(opt_btn) = scr.find_btn(&[
                "Reset password with email",
                "Log in with email",
                "Send link to email",
                "Email"
            ]) {
                log(&serial, "LOGIN_OPTION", format!("Chạm chọn: {}", opt_btn.label_owned()));
                tap_node(&adb, &serial, opt_btn);
                sleep_ms(2500);
                continue;
            } else if let Some(node) = scr.nodes.iter().find(|n| {
                n.has_area() && norm(&n.text).contains("reset password with email")
            }) {
                log(&serial, "LOGIN_OPTION", "Chạm text 'Reset password with email'");
                tap_node(&adb, &serial, node);
                sleep_ms(2500);
                continue;
            }
        }

        // 3.7 Màn hình "Check your inbox" / "TikTok send link" (Magic Link / Click link đăng nhập qua Email)
        let is_check_inbox = scr.has_contains(&[
            "check your inbox",
            "check your email",
            "sent a link to",
            "we've sent a link",
            "we sent a link",
            "tap the link in your email",
            "click the link in your email",
            "open email app",
            "link to log in",
            "magic link",
            "login link sent",
            "link has been sent",
            "log in with email link",
            "check your inbox to log in",
            "we sent an email",
            "we've sent an email",
            "sent an email",
            "email with a login link",
            "kiểm tra hộp thư",
            "kiểm tra email",
            "liên kết đăng nhập",
            "chúng tôi đã gửi"
        ]);

        if is_check_inbox {
            log(&serial, "CHECK_INBOX", format!("Phát hiện màn hình TikTok yêu cầu bấm link trong Email ('Check your inbox') cho @{}", acc.username));

            // Tìm email_id nếu chưa có
            if resolved_email_id.is_none() {
                let q = acc.email.as_deref().unwrap_or(&acc.username);
                resolved_email_id = resolve_c69_email_id(q);
                if resolved_email_id.is_none() && q.contains('@') {
                    let u_prefix = q.split('@').next().unwrap_or(q);
                    resolved_email_id = resolve_c69_email_id(u_prefix);
                }
                if let Some(eid) = resolved_email_id {
                    log(&serial, "EMAIL_ID", format!("Tìm thấy C69 Email ID: #{} cho @{}", eid, acc.username));
                }
            }

            let mut link_opt = None;
            let mut code_opt = None;

            if let Some(eid) = resolved_email_id {
                log(&serial, "EMAIL_LINK", format!("Đang quét link đăng nhập từ hòm thư C69 email #{}...", eid));
                for attempt in 1..=10 {
                    sleep_ms(3500);
                    if let Some(link) = fetch_login_link_from_c69(eid) {
                        link_opt = Some(link);
                        break;
                    }
                    if let Some(code) = fetch_otp_from_c69(eid) {
                        code_opt = Some(code);
                    }
                    log(&serial, "EMAIL_LINK", format!("Chờ TikTok gửi link đăng nhập về email C69 (thử lần {}/10)...", attempt));
                }
            }

            if let Some(ref link) = link_opt {
                log(&serial, "CLICK_LINK", format!("Lấy được link đăng nhập từ Email: {} -> Mở trực tiếp trên máy qua ADB Intent...", link));

                let clean_link = link.replace("&amp;", "&").replace("'", "'\\''");
                fresh_login = true;

                // 1. Mở thẳng vào ApplinkHookActivity chuyên trách xử lý /ucenter_web/deeplink của TikTok:
                let open_hook_cmd = format!("am start -n com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.ApplinkHookActivity -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d '{}'", clean_link);
                adb_shell(&adb, &serial, &open_hook_cmd);
                sleep_ms(3000);

                // 2. Dự phòng: mở intent VIEW với package com.zhiliaoapp.musically
                let open_tiktok_cmd = format!("am start -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d '{}' com.zhiliaoapp.musically", clean_link);
                adb_shell(&adb, &serial, &open_tiktok_cmd);
                sleep_ms(3000);

                // Kiểm tra nếu có popup "Open with / Chọn ứng dụng mở" (Resolver dialog)
                if let Some(s_check) = dump_screen(&adb, &serial) {
                    if s_check.pkg.contains("android") && s_check.has_contains(&["open with", "complete action using", "just once", "always"]) {
                        if let Some(tt_node) = s_check.nodes.iter().find(|n| norm(&n.text) == "tiktok") {
                            tap_node(&adb, &serial, tt_node);
                            sleep_ms(800);
                        }
                        if let Some(always_btn) = s_check.find_btn(&["Always", "Just once"]) {
                            tap_node(&adb, &serial, always_btn);
                            sleep_ms(2000);
                        }
                    }
                }

                // Chờ màn hình rời khỏi "Check your inbox"
                wait_leave(&adb, &serial, |s| {
                    s.has_contains(&["check your inbox", "check your email", "sent a link to", "open email app"])
                }, 30);
                continue;
            } else if let Some(ref code) = code_opt {
                if scr.any_edit().is_some() {
                    log(&serial, "EMAIL_CODE_FALLBACK", format!("Không thấy link nhưng tìm thấy mã OTP: {} -> Điền mã OTP...", code));
                    if let Some(field) = scr.any_edit() {
                        tap_node(&adb, &serial, field);
                    }
                    sleep_ms(300);
                    let mut key_cmd = String::new();
                    for ch in code.chars() {
                        if let Some(d) = ch.to_digit(10) {
                            key_cmd.push_str(&format!("input keyevent {}; sleep 0.15; ", 7 + d));
                        }
                    }
                    if !key_cmd.is_empty() {
                        adb_shell(&adb, &serial, &key_cmd);
                    }
                    sleep_ms(600);
                    tap_submit(&adb, &serial, &["Next", "Verify", "Continue", "Log in", "Submit", "Confirm"], &scr);
                    fresh_login = true;
                    wait_leave(&adb, &serial, |s| {
                        s.has_contains(&["check your inbox", "check your email", "sent a link to"])
                    }, 30);
                    continue;
                }
            }

            // Nếu không có link, kiểm tra xem có nút quay lại nhập Password không
            if let Some(pwd_btn) = scr.find_btn(&["Log in with password", "Use password", "Enter password", "Log in with phone / email / username"]) {
                log(&serial, "CHECK_INBOX_FALLBACK", format!("Không nhận được link -> Bấm \"{}\" để chuyển sang nhập mật khẩu!", pwd_btn.label_owned()));
                tap_node(&adb, &serial, pwd_btn);
                sleep_ms(2500);
                continue;
            }

            // Nếu sau 10 lần quét không có link và không có code
            log(&serial, "CHECK_INBOX_TIMEOUT", "Hết thời gian chờ (35s) không nhận được link đăng nhập từ TikTok về C69 Email");
            finish(&serial, false, "LINK_TIMEOUT", "Không nhận được link đăng nhập từ TikTok về hòm thư C69");
            let fail_log = format!("Đăng nhập dừng tại bước 'Check your inbox' trên thiết bị {}: Không nhận được link đăng nhập từ C69 Email", serial);
            if let Some(aid) = acc.id {
                sync_c69_timeline_log(aid, &fail_log, Some(3));
            } else {
                sync_c69_log_by_query(&acc.username, &fail_log, Some(3));
            }
            notify_account_event(&acc, &serial, "Kẹt Bước Check Inbox ⚠️", &fail_log);
            return;
        }

        // 3.8 Màn hình xác thực Email OTP (Verify email / 2-step verification qua Email)
            let is_verify_email = scr.has_contains(&[
                "verify email",
                "enter the code sent to",
                "we sent a code to",
                "we've sent a code to",
                "code sent to",
                "enter the 6-digit code",
                "enter 6-digit code",
                "resend code",
                "resend email",
                "enter code"
            ]) && !scr.has_label(&["Email / Username", "Phone", "Log in"]);

            // NẾU TÀI KHOẢN CÓ 2FA SECRET: Chuyển ngay sang Authenticator app qua nút "Use another method", CẤM chờ Email vô ích!
            if !acc.secret.trim().is_empty() {
                if let Some(another_btn) = scr.find_btn(&["Use another method", "use another method"]) {
                    log(&serial, "SWITCH_2FA", "Tài khoản có 2FA Secret -> Bấm 'Use another method' để chuyển sang nhập mã Authenticator app!");
                    tap_node(&adb, &serial, another_btn);
                    sleep_ms(1500);
                    if let Some(s_method) = dump_screen(&adb, &serial) {
                        if let Some(auth_btn) = s_method.find_btn(&["Authenticator", "Authenticator app"]) {
                            tap_node(&adb, &serial, auth_btn);
                            sleep_ms(2000);
                            continue;
                        } else {
                            // Dự phòng: tap toạ độ Authenticator button trên bottom sheet (360, 1245)
                            tap(&adb, &serial, 360, 1245);
                            sleep_ms(2000);
                            continue;
                        }
                    }
                }
            }

            if is_verify_email {
                // 1. Kiểm tra xem mã trước đó có bị TikTok báo lỗi "expired or incorrect" hay không:
                let code_was_rejected = scr.has_contains(&[
                    "expired or incorrect",
                    "incorrect code",
                    "invalid code",
                    "code expired",
                    "try again"
                ]);

                if code_was_rejected && last_submitted_otp.is_some() {
                    email_otp_tries += 1;
                    log(&serial, "EMAIL_VERIFY", format!("Mã OTP bị TikTok báo không hợp lệ/hết hạn -> Đếm số lần thử: {}/2", email_otp_tries));

                    if email_otp_tries > 2 {
                        // THEO CHỈ ĐẠO CỐT LÕI CỦA ANH TONY:
                        // "Với case này nhập 2 lần otp mà báo sai thì phải reset lại và làm lại từ đầu như 1 nick mới thì mới được"
                        if otp_full_restarts < 1 {
                            otp_full_restarts += 1;
                            log(&serial, "OTP_RESET", "Nhập OTP 2 lần không qua -> Tiến hành đổi SOCKS US mới + fake info + Reboot máy và làm lại từ đầu như nick mới theo chỉ đạo anh Tony!");
                            let _ = rotate_device_proxy(&adb, &serial);
                            reset_app_clean(&adb, &serial, true);
                            email_otp_tries = 0;
                            user_tries = 0;
                            pwd_tries = 0;
                            totp_tries = 0;
                            last_submitted_otp = None;
                            started = Instant::now();
                            continue;
                        }

                        let err_msg = "Nhập mã OTP Email 2 lần vẫn không qua (đã reset máy làm lại từ đầu vẫn không qua)";
                        finish(&serial, false, "OTP_FAILED", err_msg);
                        let fail_log = format!("Đăng nhập dừng trên thiết bị {}: {}", serial, err_msg);
                        if let Some(aid) = acc.id {
                            sync_c69_timeline_log(aid, &fail_log, Some(3));
                        } else {
                            sync_c69_log_by_query(&acc.username, &fail_log, Some(3));
                        }
                        notify_account_event(&acc, &serial, "Lỗi Mã OTP ❌", &fail_log);
                        return;
                    }

                    // Bấm nút "Resend code" trên TikTok để yêu cầu TikTok gửi mã mới tinh!
                    log(&serial, "EMAIL_VERIFY", "Bấm 'Resend code' để TikTok gửi mã OTP mới...");
                    if let Some(resend_btn) = scr.find_btn(&["Resend code", "resend code", "Resend"]) {
                        tap_node(&adb, &serial, resend_btn);
                    } else {
                        // Tọa độ nút Resend code ở giữa màn hình bên dưới 6 ô OTP
                        tap(&adb, &serial, 360, 480);
                    }
                    sleep_ms(2500);
                }

                // Tìm email_id nếu chưa có
                if resolved_email_id.is_none() {
                    let q = acc.email.as_deref().unwrap_or(&acc.username);
                    resolved_email_id = resolve_c69_email_id(q);
                    if resolved_email_id.is_none() && q.contains('@') {
                        let u_prefix = q.split('@').next().unwrap_or(q);
                        resolved_email_id = resolve_c69_email_id(u_prefix);
                    }
                    if let Some(eid) = resolved_email_id {
                        log(&serial, "EMAIL_ID", format!("Tìm thấy C69 Email ID: #{} cho @{}", eid, acc.username));
                    }
                }

                let mut code_opt = None;
                let mut link_opt = None;

                if let Some(eid) = resolved_email_id {
                    log(&serial, "EMAIL_VERIFY", format!("Đang đọc hòm thư C69 email #{} (chờ mã tươi trong tối đa 75s)...", eid));
                    for attempt in 1..=18 {
                        sleep_ms(4000);
                        // 1. QUÉT TÌM MÃ OTP 6 SỐ TƯƠI TRƯỚC TIÊN (Ưu tiên số 1 tuyệt đối cho màn Verify Email)
                        if let Some(c) = fetch_otp_from_c69(eid) {
                            if last_submitted_otp.as_deref() != Some(&c) {
                                code_opt = Some(c);
                                break;
                            }
                        }
                        // 2. Dự phòng: lưu tạm link nếu có nhưng KHÔNG ĐƯỢC break để tiếp tục chờ mã OTP
                        if link_opt.is_none() {
                            if let Some(link) = fetch_login_link_from_c69(eid) {
                                link_opt = Some(link);
                            }
                        }
                        // Nếu sau 8 lần (~32s) vẫn chưa thấy mã về -> Bấm nhẹ nút Resend code để TikTok phát lại lệnh
                        if attempt == 8 && code_opt.is_none() {
                            log(&serial, "EMAIL_VERIFY", "Chưa thấy OTP sau 32s -> Bấm nhẹ 'Resend code' để TikTok gửi lại mã...");
                            if let Some(resend_btn) = scr.find_btn(&["Resend code", "resend code", "Resend"]) {
                                tap_node(&adb, &serial, resend_btn);
                            } else {
                                tap(&adb, &serial, 360, 480);
                            }
                        }
                        log(&serial, "EMAIL_VERIFY", format!("Chờ mã OTP mới gửi về email (thử lần {}/18)...", attempt));
                    }
                }

                // Ưu tiên số 1: Điền mã OTP 6 số vào các ô nhập (Phương thức chuẩn xác nhất trên màn Verify Email)
                if let Some(ref code) = code_opt {
                    last_submitted_otp = Some(code.clone());
                    log(&serial, "EMAIL_VERIFY", format!("Lấy được mã OTP tươi từ C69: {}! Tiến hành nhập chuẩn xác vào các ô...", code));

                    // 1. Chạm DUY NHẤT vào ô OTP số 1 (x=102, y=430) để mở bàn phím và đặt con trỏ tại vị trí đầu tiên
                    tap(&adb, &serial, 102, 430);
                    sleep_ms(300);

                    // 2. Xóa các ký tự cũ (nếu có) trong ô bằng phím Backspace nhanh
                    adb_shell(&adb, &serial, "input keyevent 67 67 67 67 67 67 67 67");
                    sleep_ms(200);

                    // 3. PASTE TRỰC TIẾP NGUYÊN KHỐI 6 SỐ VÀO Ô OTP THEO CHỈ ĐẠO ANH TONY:
                    log(&serial, "EMAIL_VERIFY", format!("Paste trực tiếp mã OTP 6 số ({}) vào TikTok...", code));

                    // 3.1 Broadcast Paste qua ADB Keyboard (commitText của InputConnection, chuẩn paste 100%):
                    use base64::Engine;
                    let b64 = base64::engine::general_purpose::STANDARD.encode(code);
                    adb_shell(&adb, &serial, &format!("am broadcast -a ADB_INPUT_B64 --es msg {}", b64));
                    sleep_ms(150);

                    // 3.2 Inject nguyên khối bằng input text (chuẩn xác 100% vào cả 6 ô cùng lúc):
                    adb_shell(&adb, &serial, &format!("input text {}", code));
                    sleep_ms(200);

                    // 3.3 Gửi phím Paste (KEYCODE_PASTE = 279) dự phòng:
                    adb_shell(&adb, &serial, "input keyevent 279");
                    sleep_ms(1500);

                    fresh_login = true;
                    last_pwd_submit = Some(Instant::now()); // Kích hoạt timer chờ mạng TikTok xử lý OTP (kiên nhẫn chờ 25s, cấm force-stop!)
                    started = Instant::now(); // Gia hạn thêm thời gian chờ watchdog khi đã lấy được OTP và đang xử lý đăng nhập
                    wait_leave(&adb, &serial, |s| {
                        s.has_contains(&["enter the code sent to", "code sent to"]) && !s.has_contains(&["expired or incorrect", "try again"])
                    }, 25);
                    continue;
                } else if let Some(ref link) = link_opt {
                    // Dự phòng cấp 2: Nếu không bóc được mã OTP 6 số nhưng có Magic Link -> Mở link qua Intent
                    log(&serial, "CLICK_LINK", format!("Không thấy mã OTP nhưng có Magic link -> Mở link đăng nhập qua ADB Intent..."));
                    let clean_link = link.replace("&amp;", "&").replace("'", "'\\''");
                    fresh_login = true;
                    let open_hook_cmd = format!("am start -n com.zhiliaoapp.musically/com.ss.android.ugc.aweme.splash.ApplinkHookActivity -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d '{}'", clean_link);
                    adb_shell(&adb, &serial, &open_hook_cmd);
                    sleep_ms(3000);
                    let open_tiktok_cmd = format!("am start -a android.intent.action.VIEW -c android.intent.category.BROWSABLE -d '{}' com.zhiliaoapp.musically", clean_link);
                    adb_shell(&adb, &serial, &open_tiktok_cmd);
                    sleep_ms(3000);

                    wait_leave(&adb, &serial, |s| {
                        s.has_contains(&["verify email", "enter the code sent to", "code sent to", "resend code"])
                    }, 25);
                    continue;
                } else {
                    // Nếu không đọc được cả OTP lẫn link sau 10 lần -> Báo UNKNOWN
                    log(&serial, "UNKNOWN", "Không đọc được mã OTP mới từ email C69 -> Chuyển trạng thái UNKNOWN");
                    finish(&serial, false, "UNKNOWN", "Không đọc được mã OTP mới từ email C69");
                    let fail_log = format!("Đăng nhập dừng tại bước Verify Email trên thiết bị {}: Không lấy được mã OTP mới từ hòm thư C69", serial);
                    if let Some(aid) = acc.id {
                        sync_c69_timeline_log(aid, &fail_log, Some(3));
                    } else {
                        sync_c69_log_by_query(&acc.username, &fail_log, Some(3));
                    }
                    return;
                }
            }

        // 4. Màn nhập 2FA (Bao gồm cả Authenticator app dạng 6 ô số không có EditText)
        let is_totp_screen = (scr.has_contains(&["authenticator app", "your code was sent to your authenticator"])
            || (scr.has_contains(&["authenticator", "6-digit", "6 digit", "verification code", "2-step"])
                && scr.edit_field(true).is_none()
                && !scr.has_label(&["Email / Username", "Phone", "Log in"])))
            && !scr.has_contains(&["enter the code sent to", "code sent to", "we sent a code to", "resend code"]);

        if is_totp_screen {
            pwd_tries = 0;
            totp_tries += 1;
            if totp_tries > 3 {
                let err_msg = "Nhập mã 2FA TOTP nhiều lần vẫn không qua";
                finish(&serial, false, "TOTP_FAILED", err_msg);
                let fail_log = format!("Đăng nhập dừng trên thiết bị {}: {}", serial, err_msg);
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &fail_log, None);
                } else {
                    sync_c69_log_by_query(&acc.username, &fail_log, None);
                }
                notify_account_event(&acc, &serial, "Lỗi 2FA TOTP ⚠️", &fail_log);
                return;
            }
            if acc.secret.trim().is_empty() {
                // Thử bấm "Use another method" -> "Password" nếu có theo chỉ đạo anh Tony
                if let Some(another) = scr.find_btn(&["Use another method"]) {
                    log(&serial, "2FA", "Không có secret 2FA -> Bấm \"Use another method\" để chuyển sang Password");
                    tap_node(&adb, &serial, another);
                    sleep_ms(1500);
                    if let Some(s2) = dump_screen(&adb, &serial) {
                        if let Some(pwd_btn) = s2.find_btn(&["Password"]) {
                            log(&serial, "2FA", "Chọn phương thức xác thực Password");
                            tap_node(&adb, &serial, pwd_btn);
                            sleep_ms(2000);
                            continue;
                        }
                    }
                }
                let err_msg = "TikTok yêu cầu 2FA nhưng tài khoản không có secret key";
                finish(&serial, false, "NEED_2FA", err_msg);
                let fail_log = format!("Đăng nhập dừng trên thiết bị {}: {}", serial, err_msg);
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &fail_log, None);
                } else {
                    sync_c69_log_by_query(&acc.username, &fail_log, None);
                }
                notify_account_event(&acc, &serial, "Cần 2FA Secret ⚠️", &fail_log);
                return;
            }
            // Tránh mã sắp hết hạn
            let now = SystemTime::now().duration_since(UNIX_EPOCH).map(|d| d.as_secs()).unwrap_or(0);
            let remain = 30 - (now % 30);
            if remain < 5 {
                sleep_ms((remain + 1) * 1000);
            }
            match totp_now(&acc.secret) {
                Some(code) => {
                    log(&serial, "2FA", format!("Nhập mã TOTP 6 số: {}...", code));
                    if let Some(field) = scr.any_edit() {
                        tap_node(&adb, &serial, &field);
                        sleep_ms(250);
                    } else {
                        // Màn hình Authenticator app 6 ô số: tap vào ô số 1 tại (138, 255)
                        tap(&adb, &serial, 138, 255);
                        sleep_ms(250);
                    }

                    // Gửi từng ký tự số qua keyevent KEYCODE_0..KEYCODE_9
                    for ch in code.chars() {
                        if let Some(d) = ch.to_digit(10) {
                            adb_shell(&adb, &serial, &format!("input keyevent {}", 7 + d));
                            sleep_ms(120);
                        }
                    }
                    sleep_ms(800);

                    // Bấm nút Continue
                    if let Some(cont_btn) = scr.find_btn(&["Continue", "Next", "Verify", "Submit"]) {
                        tap_node(&adb, &serial, cont_btn);
                    } else {
                        tap(&adb, &serial, 360, 1295);
                    }
                    fresh_login = true;
                    last_pwd_submit = Some(Instant::now());
                    started = Instant::now();
                    wait_leave(&adb, &serial, |s| {
                        s.has_contains(&["authenticator app", "your code was sent to your authenticator"])
                    }, 25);
                }
                None => {
                    finish(&serial, false, "BAD_2FA_SECRET", "Secret 2FA không hợp lệ (Base32)");
                    return;
                }
            }
            continue;
        }

        // 5. Bước mật khẩu
        if let Some(pf) = scr.edit_field(true) {
            if let Some(t) = last_pwd_submit {
                if t.elapsed() < Duration::from_secs(7) {
                    sleep_ms(1500);
                    continue; // đang chờ TikTok xử lý
                }
            }
            pwd_tries += 1;
            if pwd_tries > 3 {
                let err_msg = "Sai mật khẩu hoặc lỗi xác thực mật khẩu trên TikTok (thử 3 lần vẫn kẹt)";
                finish(&serial, false, "PASSWORD_STUCK", err_msg);
                let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, err_msg);
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &fail_log, Some(5));
                } else {
                    sync_c69_log_by_query(&acc.username, &fail_log, Some(5));
                }
                notify_account_event(&acc, &serial, "Sai Mật Khẩu ❌", &fail_log);
                return;
            }
            log(&serial, "PASSWORD", format!("Nhập mật khẩu (lần {})", pwd_tries));
            let pf = pf.clone();
            fill_field(&adb, &serial, &pf, &acc.password, false);
            sleep_ms(400);
            tap_submit(&adb, &serial, &["Log in", "Continue", "Next"], &scr);
            last_pwd_submit = Some(Instant::now());
            fresh_login = true;
            wait_leave(&adb, &serial, |s| s.edit_field(true).is_some(), 40);
            continue;
        }

        // 5.5 CHỐT CHẶN CỐT LÕI CỦA ANH TONY:
        // "Thường xác nhận ngày sinh là click nhầm vào sign up mà, mà tool phải xác nhận là page login mới click vào email và username mà"
        // Kiểm tra nếu màn hình đang ở luồng Sign up (có "Already have an account", "Sign up for TikTok", hoặc title là "Sign up"):
        let is_signup_screen = scr.has_contains(&["already have an account", "sign up for tiktok", "create a profile"])
            || (scr.has_label(&["Sign up"]) && !scr.has_contains(&["don't have an account", "log in to tiktok", "welcome back"]));

        if is_signup_screen {
            log(&serial, "WELCOME_SIGNUP", "Phát hiện màn hình Sign up -> Chạm chữ đỏ Log in ở chân trang để chuyển sang Login theo chỉ đạo anh Tony!");
            if let Some(login_btn) = scr.nodes.iter().find(|n| {
                n.has_area() && norm(&n.text).contains("log in") && n.bounds.1 > 1200
            }) {
                tap_node(&adb, &serial, login_btn);
            } else {
                tap(&adb, &serial, 507, 1345);
            }
            sleep_ms(2500);
            continue;
        }

        // 6. Form Username (Email / Username) — BẮT BUỘC PHẢI Ở MÀN HÌNH LOG IN THEO CHỈ ĐẠO ANH TONY:
        // Bắt buộc màn hình phải có tab "Email / Username" HOẶC tiêu đề "Log in" / "Log in to TikTok", TUYỆT ĐỐI CẤM nhập nhầm vào Sign up!
        if let Some(ef) = scr.edit_field(false) {
            let is_login_screen = scr.has_label(&["Email / Username", "Log in to TikTok"]) 
                || scr.nodes.iter().any(|n| norm(&n.desc) == "email / username" || (norm(&n.text) == "log in" && n.bounds.1 < 250));

            if is_login_screen {
                // Phải ở tab "Email / Username"
                if let Some(tab) = scr.nodes.iter().find(|n| n.has_area() && norm(&n.desc) == "email / username") {
                    if !tab.selected {
                        let other_sel = scr.nodes.iter().any(|n| norm(&n.desc) == "phone" && n.selected);
                        let tab_sel_unknown = !scr.nodes.iter().any(|n| (norm(&n.desc) == "phone" || norm(&n.desc) == "email / username") && n.selected);
                        if other_sel || tab_sel_unknown {
                            log(&serial, "TAB", "Chuyển sang tab Email / Username");
                            let t = tab.clone();
                            tap_node(&adb, &serial, &t);
                            sleep_ms(1500);
                            continue;
                        }
                    }
                }
                // QUÉT XML KIỂM TRA LỖI TRƯỚC TIÊN TẠI MÀN HÌNH USERNAME:
                // 1. Nếu TikTok hiện rõ Maximum attempts / Rate limit -> Bắt buộc đổi IP + info + xóa sạch dữ liệu ngay!
                let is_step_rate_limit = scr.has_contains(&["maximum number of attempts", "too many attempts", "too many requests"]);
                if is_step_rate_limit {
                    // FALLBACK 2 CHIỀU NGAY KHI GẶP MAXIMUM ATTEMPTS TẠI BƯỚC USERNAME:
                    if !tried_alt_iden_on_rate {
                        tried_alt_iden_on_rate = true;
                        if !current_iden.contains('@') {
                            if let Some(ref em) = target_email {
                                let em_clean = em.trim();
                                if em_clean.contains('@') && em_clean != current_iden {
                                    log(&serial, "RATE_FALLBACK_EMAIL", format!("Điền Username '{}' bị Maximum attempts -> Thử ngay bằng Email '{}' trước khi rotate proxy!", current_iden, em_clean));
                                    current_iden = em_clean.to_string();
                                    user_tries = 0;
                                    let ef = ef.clone();
                                    fill_field(&adb, &serial, &ef, &current_iden, true);
                                    sleep_ms(400);
                                    tap_submit(&adb, &serial, &["Continue", "Next", "Log in"], &scr);
                                    sleep_ms(2500);
                                    continue;
                                }
                            }
                        } else {
                            let fallback_user = if !acc.username.contains('@') && !acc.username.trim().is_empty() {
                                acc.username.trim().to_string()
                            } else {
                                current_iden.split('@').next().unwrap_or("").trim().to_string()
                            };
                            if !fallback_user.is_empty() && fallback_user != current_iden {
                                log(&serial, "RATE_FALLBACK_USER", format!("Điền Email '{}' bị Maximum attempts -> Thử ngay bằng Username/Tiền tố (@{})!", current_iden, fallback_user));
                                current_iden = fallback_user;
                                user_tries = 0;
                                let ef = ef.clone();
                                fill_field(&adb, &serial, &ef, &current_iden, true);
                                sleep_ms(400);
                                tap_submit(&adb, &serial, &["Continue", "Next", "Log in"], &scr);
                                sleep_ms(2500);
                                continue;
                            }
                        }
                    }

                    flag_current_device_model(&adb, &serial); // ĐƯA MODEL NÀY VÀO BLACKLIST ĐỂ CÁC MÁY KHÁC TRÁNH FAKE TRÙNG
                    if proxy_rotates < 3 {
                        proxy_rotates += 1;
                        log(&serial, "PROXY_ROTATE", format!("Phát hiện Maximum attempts tại bước Username -> Tự động xoay SOCKS US mới + đổi full info + xóa sạch dữ liệu (lần {}/3)...", proxy_rotates));
                        match rotate_device_proxy(&adb, &serial) {
                            Ok(new_px) => {
                                log(&serial, "PROXY_ROTATE", format!("Đã gán SOCKS US mới: {} -> Reset máy sạch sẽ (Reboot) và chạy lại từ đầu nick này", new_px));
                                reset_app_clean(&adb, &serial, true);
                                started = Instant::now(); // Reset lại timer cho chu kỳ proxy mới!
                                user_tries = 0;
                                username_stuck_restarts = 0;
                                pwd_tries = 0;
                                bday_tries = 0;
                                continue;
                            }
                            Err(e) => {
                                log(&serial, "PROXY_ROTATE", format!("Không xoay được SOCKS: {}", e));
                            }
                        }
                    } else {
                        let err_msg = "Rate-limit Maximum attempts tại bước Username (đã đổi SOCKS 3 lần vẫn bị)";
                        finish(&serial, false, "RATE_LIMIT", err_msg);
                        let fail_log = format!("Đăng nhập dừng trên thiết bị {}: {}", serial, err_msg);
                        if let Some(aid) = acc.id {
                            sync_c69_timeline_log(aid, &fail_log, Some(3));
                        } else {
                            sync_c69_log_by_query(&acc.username, &fail_log, Some(3));
                        }
                        notify_account_event(&acc, &serial, "Cảnh Báo Rate-limit ⚠️", &fail_log);
                        return;
                    }
                }

                // 2. Nếu TikTok hiện rõ tài khoản không tồn tại -> Kết luận NO_ACCOUNT ngay lập tức
                if scr.has_contains(&[
                    "couldn't find your account",
                    "account doesn't exist",
                    "no account found",
                    "can't find this account",
                    "user not found",
                    "not registered",
                    "tài khoản không tồn tại"
                ]) {
                    let err_msg = "Tài khoản không tồn tại trên TikTok (Account doesn't exist)";
                    log(&serial, "NO_ACCOUNT", format!("Phát hiện TikTok báo '{}' -> Kết luận ngay!", err_msg));
                    finish(&serial, false, "NO_ACCOUNT", err_msg);
                    let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, err_msg);
                    if let Some(aid) = acc.id {
                        sync_c69_timeline_log(aid, &fail_log, Some(2));
                    } else {
                        sync_c69_log_by_query(&acc.username, &fail_log, Some(2));
                    }
                    notify_account_event(&acc, &serial, "Tài Khoản Không Tồn Tại ❌", &fail_log);
                    return;
                }

                user_tries += 1;
                let iden = current_iden.clone();
                let _already = ef.text.trim() == iden;

                if user_tries > 1 {
                    // THEO CHỈ ĐẠO CỐT LÕI CỦA ANH TONY:
                    // "Nếu mà không qua thì phải đọc xml nguyên nhân là gì không qua chứ em và nếu username không đúng thì dùng email thay thế"

                    // 1. Đọc XML trích xuất chính xác nguyên nhân TikTok không cho qua:
                    let xml_reason = scr.nodes.iter().find(|n| {
                        let t = n.text.to_lowercase();
                        let d = n.desc.to_lowercase();
                        (t.contains("couldn't find") || t.contains("not found") || t.contains("doesn't exist")
                            || t.contains("invalid") || t.contains("enter a valid") || t.contains("error")
                            || t.contains("try again") || t.contains("maximum") || t.contains("too many")
                            || t.contains("not registered") || d.contains("error") || d.contains("invalid"))
                            && !t.contains("by continuing") && !t.contains("terms of service")
                    }).map(|n| n.label_owned());

                    if let Some(ref r_text) = xml_reason {
                        log(&serial, "XML_REASON", format!("Đọc XML phát hiện nguyên nhân không qua: \"{}\"", r_text));
                    }

                    // 2. NẾU ĐANG DÙNG USERNAME MÀ KHÔNG QUA -> DÙNG EMAIL THAY THẾ NGAY LẬP TỨC:
                    let is_using_username = !current_iden.contains('@');
                    if is_using_username {
                        if let Some(ref em) = target_email {
                            let em_clean = em.trim();
                            if em_clean.contains('@') && em_clean != current_iden {
                                log(&serial, "FALLBACK_EMAIL", format!("Điền Username '{}' không qua -> Lập tức đổi sang dùng Email '{}' thay thế theo chỉ đạo anh Tony!", current_iden, em_clean));
                                current_iden = em_clean.to_string();
                                user_tries = 0;
                                let ef = ef.clone();
                                fill_field(&adb, &serial, &ef, &current_iden, true);
                                sleep_ms(400);
                                tap_submit(&adb, &serial, &["Continue", "Next", "Log in"], &scr);
                                sleep_ms(2500);
                                continue;
                            }
                        }
                    }

                    // 3. NẾU ĐANG DÙNG EMAIL MÀ KHÔNG QUA -> DÙNG USERNAME / TIỀN TỐ EMAIL THAY THẾ:
                    let is_using_email = current_iden.contains('@');
                    if is_using_email {
                        let u_candidate = if !acc.username.contains('@') && !acc.username.trim().is_empty() {
                            acc.username.trim().to_string()
                        } else {
                            current_iden.split('@').next().unwrap_or("").trim().to_string()
                        };
                        if !u_candidate.is_empty() && u_candidate != current_iden {
                            log(&serial, "FALLBACK_USER", format!("Điền Email '{}' không qua -> Lập tức đổi sang dùng Username/Tiền tố '{}' thay thế theo chỉ đạo anh Tony!", current_iden, u_candidate));
                            current_iden = u_candidate;
                            user_tries = 0;
                            let ef = ef.clone();
                            fill_field(&adb, &serial, &ef, &current_iden, true);
                            sleep_ms(400);
                            tap_submit(&adb, &serial, &["Continue", "Next", "Log in"], &scr);
                            sleep_ms(2500);
                            continue;
                        }
                    }

                    // 4. NẾU ĐÃ THỬ CẢ HAI MÀ VẪN KẸT -> TIẾN HÀNH THOÁT RA LÀM LẠI:
                    if username_stuck_restarts < 3 {
                        username_stuck_restarts += 1;
                        let reason_str = xml_reason.as_deref().unwrap_or("Nút Continue không chuyển trang");
                        log(&serial, "USERNAME_RETRY", format!("Bấm Continue không qua (Nguyên nhân: {}) -> Thoát app làm lại (lần {}/3) theo chỉ đạo anh Tony!", reason_str, username_stuck_restarts));
                        relaunch_app(&adb, &serial);
                        user_tries = 0;
                        sleep_ms(2500);
                        continue;
                    }

                    // Nếu đã thoát ra làm lại 3 lần mà vẫn bị kẹt ở ô Username -> ĐỔI SOCKS + ĐỔI INFO + REBOOT:
                    if proxy_rotates < 1 {
                        proxy_rotates += 1;
                        username_stuck_restarts = 0;
                        user_tries = 0;
                        log(&serial, "PROXY_ROTATE", "Đã thoát ra làm lại 3 lần vẫn kẹt Username -> Đổi SOCKS US mới + fake full info + xóa sạch dữ liệu theo chỉ đạo anh Tony...");
                        match rotate_device_proxy(&adb, &serial) {
                            Ok(new_px) => {
                                log(&serial, "PROXY_ROTATE", format!("Đã gán SOCKS US mới: {} -> Reset máy sạch sẽ (Reboot) và thử lại thêm 3 lần cho nick này", new_px));
                                reset_app_clean(&adb, &serial, true);
                                started = Instant::now(); // Reset lại timer cho chu kỳ proxy mới!
                                pwd_tries = 0;
                                bday_tries = 0;
                                continue;
                            }
                            Err(e) => {
                                log(&serial, "PROXY_ROTATE", format!("Lỗi xoay SOCKS: {}", e));
                            }
                        }
                    }

                    // Nếu sau khi đổi SOCKS rồi mà sau 3 lần nữa vẫn bị kẹt -> Báo RATE LIMIT:
                    let reason_str = xml_reason.as_deref().unwrap_or("Kẹt tại ô Username");
                    let err_msg = format!("Rate limit (sau khi đổi SOCKS vẫn bị kẹt tại bước Username: {})", reason_str);
                    log(&serial, "RATE_LIMIT", format!("{} -> Dừng nick @{}", err_msg, acc.username));
                    finish(&serial, false, "RATE_LIMIT", &err_msg);
                    let fail_log = format!("Đăng nhập dừng trên thiết bị {}: {}", serial, err_msg);
                    if let Some(aid) = acc.id {
                        sync_c69_timeline_log(aid, &fail_log, Some(3));
                    } else {
                        sync_c69_log_by_query(&acc.username, &fail_log, Some(3));
                    }
                    notify_account_event(&acc, &serial, "Cảnh Báo Rate-limit ⚠️", &fail_log);
                    return;
                }
                let iden = current_iden.clone();
                let already = ef.text.trim() == iden;
                if already {
                    log(&serial, "USERNAME", format!("Tài khoản {} đã điền sẵn, bấm Continue lại (lần {})", iden, user_tries));
                    if scr.has_contains(&["no internet", "network error", "try again"]) {
                        // THEO CHỈ ĐẠO ANH TONY: Nếu đã điền Email mà bị No internet -> thử ngay bằng Username (hoặc tiền tố email)
                        if current_iden.contains('@') {
                            let fallback_user = if !acc.username.contains('@') && !acc.username.trim().is_empty() {
                                acc.username.trim().to_string()
                            } else {
                                current_iden.split('@').next().unwrap_or("").trim().to_string()
                            };

                            if !fallback_user.is_empty() && fallback_user != current_iden {
                                log(&serial, "NET_FALLBACK_USER", format!("Đã điền email bị No internet -> Chuyển sang Username/Tiền tố (@{}) theo chỉ đạo anh Tony!", fallback_user));
                                current_iden = fallback_user;
                                let ef = ef.clone();
                                fill_field(&adb, &serial, &ef, &current_iden, true);
                                sleep_ms(400);
                                tap_submit(&adb, &serial, &["Continue", "Next", "Log in"], &scr);
                                sleep_ms(3000);

                                if let Some(s_after) = dump_screen(&adb, &serial) {
                                    if s_after.has_contains(&[
                                        "couldn't find your account",
                                        "account doesn't exist",
                                        "no account found",
                                        "can't find this account",
                                        "user not found",
                                        "not registered",
                                        "tài khoản không tồn tại"
                                    ]) {
                                        let err_msg = format!("Proxy OK (không lỗi mạng). Email '{}' là email rác/không tồn tại trên TikTok", acc.email.as_deref().unwrap_or(&acc.username));
                                        log(&serial, "NO_ACCOUNT", format!("{} -> Chuyển ngay Status 2 (Không tồn tại)", err_msg));
                                        finish(&serial, false, "NO_ACCOUNT", &err_msg);
                                        let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, err_msg);
                                        if let Some(aid) = acc.id {
                                            sync_c69_timeline_log(aid, &fail_log, Some(2));
                                        } else {
                                            sync_c69_log_by_query(&acc.username, &fail_log, Some(2));
                                        }
                                        notify_account_event(&acc, &serial, "Tài Khoản Không Tồn Tại ❌", &fail_log);
                                        return;
                                    }
                                }
                                continue;
                            }
                        }
                        sleep_ms(3000);
                    }
                } else {
                    let iden_type = if iden.contains('@') { "Email" } else { "Username" };
                    log(&serial, "USERNAME", format!("Điền {} {} (lần {})", iden_type, iden, user_tries));
                    let ef = ef.clone();
                    let ok = fill_field(&adb, &serial, &ef, &iden, true);
                    if !ok {
                        log(&serial, "USERNAME", format!("Xác minh {} thất bại, thử lại", iden_type));
                        continue;
                    }
                }
                tap_submit(&adb, &serial, &["Continue", "Next", "Log in"], &scr);
                wait_leave(
                    &adb,
                    &serial,
                    |s| s.edit_field(false).is_some() && s.has_label(&["Continue"]) && !s.has_contains(&["no internet", "network error"]),
                    25,
                );
                continue;
            }
        }

        // 6.3 Màn hình "Welcome back" (Lưu nick cũ trước đó): Bấm "Add another account" để vào màn chọn phương thức
        if scr.has_contains(&["welcome back"]) {
            if let Some(b) = scr.find_btn(&["Add another account", "Use another account"]) {
                log(&serial, "WELCOME_BACK", "Phát hiện màn Welcome back -> Chọn Add another account");
                tap_node(&adb, &serial, b);
                sleep_ms(2000);
                continue;
            } else {
                log(&serial, "WELCOME_BACK", "Phát hiện màn Welcome back -> Chạm tọa độ Add another account (360, 1018)");
                tap(&adb, &serial, 360, 1018);
                sleep_ms(2000);
                continue;
            }
        }

        // 7. Màn CHỌN PHƯƠNG THỨC ĐĂNG NHẬP (Chỉ bấm khi chắc chắn màn hình là Log in to TikTok)
        if scr.has_contains(&["log in to tiktok"]) && !scr.has_contains(&["sign up for tiktok"]) {
            if let Some(b) = scr.find_btn(&["Use phone / email / username", "Use phone or email"]) {
                log(&serial, "METHOD", format!("Đang ở màn Log in -> Chọn \"{}\"", b.label_owned()));
                logging_out = false;
                user_tries = 0;
                pwd_tries = 0;
                totp_tries = 0;
                tap_node(&adb, &serial, b);
                sleep_ms(2000);
                continue;
            }
        }

        // 7.8 Phát hiện tài khoản bị khóa (Suspended / Appeal deadline expired)
        if scr.has_contains(&["account is currently suspended", "appeal deadline expired"]) {
            let err_msg = "Tài khoản đã bị TikTok đình chỉ vĩnh viễn (Account is currently suspended / Appeal deadline expired)";
            log(&serial, "SUSPENDED", format!("Phát hiện TikTok báo '{}' -> Đánh dấu BỊ KHÓA ngay lập tức!", err_msg));
            finish(&serial, false, "SUSPENDED", err_msg);
            let fail_log = format!("Đăng nhập thất bại trên thiết bị {}: {}", serial, err_msg);
            if let Some(aid) = acc.id {
                sync_c69_timeline_log(aid, &fail_log, Some(2));
            } else {
                sync_c69_log_by_query(&acc.username, &fail_log, Some(2));
            }
            notify_account_event(&acc, &serial, "Tài Khoản Bị Khóa (Suspended) ❌", &fail_log);
            return;
        }

        // 8. Popup cản đường / Terms of Service / Welcome Agree and continue / Avatar dialog
        if scr.has_contains(&["your avatar, your style", "create your tiktok avatar"]) {
            log(&serial, "AVATAR_MODAL", "Phát hiện modal Avatar -> Bấm Back để đóng và tiếp tục theo chỉ đạo anh Tony");
            key(&adb, &serial, 4); // Back
            sleep_ms(1200);
            continue;
        }

        if scr.has_contains(&["swipe up for more"]) {
            log(&serial, "SWIPE_GUIDE", "Phát hiện hướng dẫn 'Swipe up for more' -> Vuốt lên để vào video feed");
            adb_shell(&adb, &serial, "input swipe 360 900 360 300 250");
            sleep_ms(1500);
            continue;
        }

        if let Some(b) = scr.find_btn(&[
            "Agree and continue", "Agree & continue", "Agree", "I agree", "Accept",
            "Restore", "Not now", "Lúc khác", "Skip", "Maybe later", "Later", 
            "Got it", "No thanks", "Dismiss", "Close", "Đóng", "Get started", 
            "Get Started", "Understand", "I understand", "Start watching", 
            "Let's go", "Let’s go", "OK", "Done", "Confirm", "Select"
        ]) {
            log(&serial, "POPUP", format!("Đóng popup: {}", b.label_owned()));
            tap_node(&adb, &serial, b);
            sleep_ms(1500);
            continue;
        }

        // 9. Profile chưa đăng nhập / màn có nút Log in
        if let Some(b) = scr
            .nodes
            .iter()
            .find(|n| n.has_area() && norm(&n.text) == "log in")
        {
            logging_out = false;
            log(&serial, "LOGIN", "Bấm nút Log in");
            tap_node(&adb, &serial, b);
            sleep_ms(2200);
            continue;
        }

        // 9.5 Login MỚI vừa qua password/2FA/onboarding: Vào thẳng nuôi FYP, KHÔNG sleep chờ lâu và KHÔNG gọi detect_current_user thừa thãi!
        if fresh_login
            && (onboarding_steps > 0 || totp_tries > 0)
            && (scr.has_contains(&["swipe up to start watching"]) || (scr.has_label(&["Home"]) && scr.has_label(&["Profile"])))
        {
            let verified_user = acc.username.clone();
            log(&serial, "FYP", "Đã vào màn hình FYP thành công -> Xác nhận login và chuyển sang nuôi ngay lập tức!");
            finish(
                &serial,
                true,
                "SUCCESS",
                &format!("Đã login @{} thành công trọn vẹn", verified_user),
            );

            // Ghi log lên C69 để Client thấy theo chỉ đạo anh Tony
            let action_log = format!("Đã login thành công trên thiết bị {} (User: @{})", serial, verified_user);
            if let Some(aid) = acc.id {
                sync_c69_timeline_log(aid, &action_log, Some(0));
            } else {
                sync_c69_log_by_query(&acc.username, &action_log, Some(0));
            }
            notify_account_event(&acc, &serial, "TikTok Login Thành Công 🟢", &action_log);
            return;
        }

        // 10. Thanh điều hướng dưới -> sang tab Profile
        if let Some(p) = scr.find_btn(&["Profile"]) {
            nav_count += 1;
            log(&serial, "NAV", "Mở tab Profile");
            if nav_count >= 4 && fresh_login {
                log(&serial, "NAV_SUCCESS", "Đã ở tab Profile sau khi login thành công -> Xác nhận hoàn tất!");
                finish(&serial, true, "SUCCESS", &format!("Đã login @{} thành công", acc.username));
                let action_log = format!("Đã login thành công trên thiết bị {} (User: @{})", serial, acc.username);
                if let Some(aid) = acc.id {
                    sync_c69_timeline_log(aid, &action_log, Some(0));
                } else {
                    sync_c69_log_by_query(&acc.username, &action_log, Some(0));
                }
                notify_account_event(&acc, &serial, "TikTok Login Thành Công 🟢", &action_log);
                return;
            }
            if nav_count % 3 == 0 {
                // overlay hướng dẫn có thể nuốt cú tap -> vuốt để tắt rồi tap lại
                swipe_up(&adb, &serial);
                sleep_ms(800);
            }
            tap_node(&adb, &serial, p);
            sleep_ms(2200);
            continue;
        }

        // 11. Màn không nhận diện (bao gồm MÀN HÌNH TRẮNG sau khi nhập OTP/Password do WebView hoặc Animation kẹt)
        let summary: String = scr
            .nodes
            .iter()
            .filter(|n| !n.text.trim().is_empty() || !n.desc.trim().is_empty())
            .take(8)
            .map(|n| n.label_owned())
            .collect::<Vec<_>>()
            .join(" | ");

        let is_blank_white_screen = summary.trim().is_empty() || scr.nodes.len() <= 6;
        if is_blank_white_screen {
            // NẾU VỪA BẤM SUBMIT PASSWORD HOẶC OTP CHƯA QUÁ 25S: Đang chờ mạng TikTok phản hồi -> KIÊN NHẪN CHỜ, CẤM VUỐT HOẶC FORCE-STOP!
            let is_waiting_network = last_pwd_submit.map(|t| t.elapsed() < Duration::from_secs(25)).unwrap_or(false);
            if is_waiting_network {
                let wait_secs = last_pwd_submit.map(|t| t.elapsed().as_secs()).unwrap_or(0);
                log(&serial, "WAIT_NETWORK", format!("Đang chờ TikTok tải phản hồi sau khi nhập mật khẩu/xác thực (chờ {}s/25s)...", wait_secs));
                blank_consecutive = 0;
                sleep_ms(2000);
                continue;
            }

            blank_consecutive += 1;
            log(&serial, "BLANK_SCREEN", format!("Phát hiện MÀN HÌNH TRẮNG (lần {}) sau bước xác thực -> Tự động xử lý đánh thức UI...", blank_consecutive));

            // Đánh thức màn hình trắng / thoát SparkActivity bị kẹt treo sau OTP:
            if blank_consecutive == 3 {
                // Chạm nhẹ giữa màn hình để kích hoạt WebView render
                adb_shell(&adb, &serial, "input tap 360 700");
            } else if blank_consecutive == 5 || blank_consecutive == 8 {
                // Thoát WebView/SparkActivity treo bằng phím Back
                log(&serial, "BLANK_SCREEN", "Bấm phím Back để thoát SparkActivity/WebView bị kẹt trắng");
                key(&adb, &serial, 4);
            } else if blank_consecutive >= 15 {
                // Nếu màn hình trắng kẹt liên tiếp quá 15 lần (>30s) mà không có tiến triển -> Mới force-stop và mở lại app
                log(&serial, "BLANK_SCREEN", "Màn hình trắng kẹt liên tiếp quá lâu (>30s) -> Force-stop và mở lại TikTok để phục hồi giao diện");
                relaunch_app(&adb, &serial);
                blank_consecutive = 0;
                unknown = 0;
                sleep_ms(3000);
            }
            sleep_ms(1500);
            continue;
        }

        blank_consecutive = 0;
        unknown += 1;

        log(&serial, "UNKNOWN", format!("Màn hình lạ (lần {}, bước {}): {}", unknown, step, summary));
        if let Some(b) = scr.find_btn(&["Skip", "Not now", "Maybe later", "Next", "Continue", "Done", "Got it", "OK", "No thanks", "Allow", "Let's go", "Let’s go", "Start watching", "Agree and continue"]) {
            log(&serial, "UNKNOWN", format!("Bấm nút an toàn \"{}\"", b.label_owned()));
            tap_node(&adb, &serial, b);
            sleep_ms(2000);
        } else if unknown % 8 == 0 {
            relaunch_app(&adb, &serial);
            sleep_ms(3000);
        } else if unknown % 8 >= 5 {
            key(&adb, &serial, 4);
            sleep_ms(1200);
        } else {
            sleep_ms(2500);
        }
    }

    finish(&serial, false, "MAX_STEPS", "Hết số bước tối đa mà chưa vào được tài khoản");
    let fail_log = format!("Đăng nhập dừng trên thiết bị {}: Hết số bước tương tác tối đa", serial);
    if let Some(aid) = acc.id {
        sync_c69_timeline_log(aid, &fail_log, None);
    } else {
        sync_c69_log_by_query(&acc.username, &fail_log, None);
    }
    notify_account_event(&acc, &serial, "Dừng Đăng Nhập ⚠️", &fail_log);
}

impl UiNode {
    fn label_owned(&self) -> String {
        if self.text.trim().is_empty() {
            self.desc.clone()
        } else {
            self.text.clone()
        }
    }
}

// ───────────────────────────── Orchestration ─────────────────────────────

/// Ghép máy <-> tài khoản: máy nào đang login đúng 1 nick trong danh sách thì giữ nguyên,
/// các máy còn lại nhận nick chưa được gán theo thứ tự.
fn plan(adb: &Path, serials: &[String], accounts: Vec<LoginAccount>) -> Vec<(String, LoginAccount)> {
    let detected: Arc<Mutex<HashMap<String, Option<String>>>> = Arc::new(Mutex::new(HashMap::new()));
    std::thread::scope(|sc| {
        for s in serials {
            let detected = detected.clone();
            sc.spawn(move || {
                upd(s, |st| {
                    st.state = "detecting".into();
                    st.step = "DETECT".into();
                    st.message = "Đang kiểm tra nick đang đăng nhập...".into();
                });
                let u = detect_current_user(adb, s);
                upd(s, |st| st.current_user = u.clone().unwrap_or_default());
                detected.lock().insert(s.clone(), u);
            });
        }
    });
    let detected = detected.lock().clone();

    let mut remaining: Vec<LoginAccount> = accounts;
    let mut assigned: Vec<(String, LoginAccount)> = Vec::new();
    let mut unassigned_serials: Vec<String> = Vec::new();

    for s in serials {
        let cur = detected.get(s).cloned().flatten();
        if let Some(cu) = cur {
            if let Some(pos) = remaining.iter().position(|a| {
                a.username.eq_ignore_ascii_case(&cu)
                    || a.username.split('@').next().map(|p| p.eq_ignore_ascii_case(&cu)).unwrap_or(false)
            }) {
                assigned.push((s.clone(), remaining.remove(pos)));
                continue;
            }
        }
        unassigned_serials.push(s.clone());
    }
    for s in unassigned_serials {
        if remaining.is_empty() {
            upd(&s, |st| {
                st.state = "failed".into();
                st.message = "NO_ACCOUNT: Không còn tài khoản để gán cho máy này".into();
            });
            continue;
        }
        assigned.push((s, remaining.remove(0)));
    }
    assigned.sort_by(|a, b| a.0.cmp(&b.0));
    assigned
}

/// Khởi chạy login độc lập đa luồng theo hàng đợi (Queue Worker Pool)
/// Mỗi máy là một worker độc lập, xong nick nào lập tức bốc nick tiếp theo, không chờ nhau!
pub fn start(adb: PathBuf, serials: Vec<String>, accounts: Vec<LoginAccount>, force_logout: bool) -> Result<usize, String> {
    if serials.is_empty() {
        return Err("Không có thiết bị Android nào online".into());
    }
    if accounts.is_empty() {
        return Err("Không có tài khoản nào để đăng nhập".into());
    }
    if RUNNING.swap(true, Ordering::SeqCst) {
        return Err("Đang có phiên login Native XML khác đang chạy".into());
    }
    STOP.store(false, Ordering::SeqCst);
    status_map().write().clear();
    for s in &serials {
        upd(s, |st| {
            st.state = "queued".into();
            st.step = "QUEUED".into();
        });
    }

    let mut skipped_existing = 0;
    let filtered_accounts: Vec<LoginAccount> = accounts.into_iter().filter(|acc| {
        if has_local_profile(acc) {
            skipped_existing += 1;
            false
        } else {
            true
        }
    }).collect();

    if filtered_accounts.is_empty() {
        RUNNING.store(false, Ordering::SeqCst);
        return Err(format!("Tất cả {} tài khoản đều ĐÃ CÓ PROFILE LƯU TRÊN PC! Không cần đăng nhập lại.", skipped_existing));
    }
    if skipped_existing > 0 {
        info!("[XMLLogin] Đã tự động bỏ qua {} tài khoản vì ĐÃ CÓ PROFILE TRÊN PC!", skipped_existing);
    }

    let total = filtered_accounts.len();
    TOTAL_COUNT.store(total, Ordering::SeqCst);
    SUCC_COUNT.store(0, Ordering::SeqCst);
    FAIL_COUNT.store(0, Ordering::SeqCst);
    SKIP_MANUAL_COUNT.store(0, Ordering::SeqCst);
    QUEUE_REMAINING.store(total, Ordering::SeqCst);

    let queue = Arc::new(std::sync::Mutex::new(std::collections::VecDeque::from(filtered_accounts)));

    std::thread::spawn(move || {
        info!("[XMLLogin] Bắt đầu Worker Pool độc lập trên {} máy cho {} tài khoản", serials.len(), total);
        let mut handles = Vec::new();

        for serial in serials {
            let adb = adb.clone();
            let queue = queue.clone();
            let serial = serial.clone();

            handles.push(std::thread::spawn(move || {
                while !STOP.load(Ordering::SeqCst) {
                    let acc = {
                        let mut q = match queue.lock() {
                            Ok(guard) => guard,
                            Err(poisoned) => poisoned.into_inner(),
                        };
                        match q.pop_front() {
                            Some(a) => {
                                QUEUE_REMAINING.fetch_sub(1, Ordering::SeqCst);
                                a
                            }
                            None => break, // Hết tài khoản trong hàng đợi
                        }
                    };

                    info!("[Worker {}] Bắt đầu xử lý tài khoản @{}", serial, acc.username);
                    login_one(adb.clone(), serial.clone(), acc.clone(), force_logout);

                    // Kiểm tra kết quả: nếu login thành công và chưa nhận lệnh STOP -> nuôi tương tác 3 video
                    let is_succ = status_map().read().get(&serial).map(|s| s.state == "success").unwrap_or(false);
                    if is_succ && !STOP.load(Ordering::SeqCst) {
                        upd(&serial, |s| {
                            s.state = "nurturing".into();
                            s.step = "NURTURE".into();
                        });
                        log(&serial, "NURTURE", "Bắt đầu nuôi tương tác tự nhiên 3 video FYP...");
                        run_quick_nurture(&adb, &serial, 3);

                        // TỰ ĐỘNG ĐÓNG GÓI VÀ LƯU PROFILE TIKTOK VÀO PC THEO CHỈ ĐẠO ANH TONY:
                        upd(&serial, |s| {
                            s.step = "BACKUP_PROFILE".into();
                        });
                        let prof_name = format!("acc_{}_{}", acc.id.unwrap_or(0), clean_filename(&acc.username));
                        log(&serial, "BACKUP_PROFILE", format!("Đang đóng gói và lưu Profile của @{} về PC...", acc.username));
                        match backup_device_profile_to_pc(&adb, &serial, &prof_name, &acc) {
                            Ok(mb) => {
                                log(&serial, "BACKUP_PROFILE", format!("Đã lưu Profile về PC thành công: {} ({:.1} MB) 🟢", prof_name, mb));
                                if let Some(aid) = acc.id {
                                    sync_c69_timeline_log(aid, &format!("Đã lưu Profile TikTok về PC ({:.1} MB) 🟢", mb), None);
                                }
                            }
                            Err(e) => {
                                log(&serial, "BACKUP_PROFILE", format!("Lỗi lưu Profile về PC: {}", e));
                            }
                        }
                    }

                    // Ngay sau khi xong nick này -> worker này lập tức bốc nick tiếp theo trong queue,
                    // tự động đổi Proxy mới, đối soát IP, reset phần cứng MaxChanger và chạy tiếp!
                }

                upd(&serial, |s| {
                    s.state = "idle".into();
                    s.step = "IDLE".into();
                });
                info!("[Worker {}] Đã hoàn thành mọi công việc, chuyển sang Idle", serial);
            }));
        }

        for h in handles {
            let _ = h.join();
        }
        RUNNING.store(false, Ordering::SeqCst);
        info!("[XMLLogin] Hoàn tất toàn bộ hàng đợi {} tài khoản trên các máy!", total);
    });

    Ok(total)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn totp_rfc6238_vector() {
        // RFC 6238: secret ASCII "12345678901234567890", T=59 -> 94287082 (8 số) => 6 số cuối 287082
        assert_eq!(totp_at("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 59).as_deref(), Some("287082"));
        // T=1111111109 -> 07081804 => 081804
        assert_eq!(totp_at("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 1111111109).as_deref(), Some("081804"));
    }

    #[test]
    fn totp_rejects_bad_secret() {
        assert!(totp_at("!!!notbase32!!!", 59).is_none());
    }

    #[test]
    fn bounds_parse() {
        assert_eq!(parse_bounds("[81,404][586,439]"), (81, 404, 586, 439));
    }

    #[test]
    fn sanitize_removes_surrogates() {
        let s = sanitize_xml("a&#55357;b&#128512;c");
        assert_eq!(s, "ab&#128512;c");
    }

    #[test]
    fn detects_own_profile_and_login_form() {
        let profile = r#"<hierarchy><node text="" content-desc="Profile menu" class="android.widget.Button" package="com.zhiliaoapp.musically" bounds="[10,10][50,50]" clickable="true" /><node text="@leahclarkdean" class="android.widget.TextView" package="com.zhiliaoapp.musically" bounds="[10,60][200,90]" /><node text="Following" class="android.widget.TextView" package="com.zhiliaoapp.musically" bounds="[10,100][200,130]" /></hierarchy>"#;
        let s = Screen::parse(profile).unwrap();
        assert_eq!(s.own_profile_user().as_deref(), Some("leahclarkdean"));

        let form = r#"<hierarchy><node text="Log in" class="android.widget.TextView" package="com.zhiliaoapp.musically" bounds="[53,175][206,242]" /><node text="abc" class="android.widget.EditText" package="com.zhiliaoapp.musically" bounds="[81,404][586,439]" /><node text="Continue" class="android.widget.Button" package="com.zhiliaoapp.musically" bounds="[56,1250][664,1341]" clickable="true" /></hierarchy>"#;
        let s = Screen::parse(form).unwrap();
        assert!(s.own_profile_user().is_none());
        assert!(s.edit_field(false).is_some());
        assert!(s.edit_field(true).is_none());
        assert!(s.find_btn(&["Continue"]).is_some());
    }
}
