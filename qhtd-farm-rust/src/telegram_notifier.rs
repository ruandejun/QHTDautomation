//! Telegram Notifier Module (Pure Rust)
//! ====================================
//! Tự động liên kết và gửi thông báo kết quả đăng nhập / nuôi / phân loại tài khoản
//! về Telegram riêng của từng client thông qua bot @C69autobot.

use parking_lot::RwLock;
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, AtomicI64, Ordering};
use std::sync::OnceLock;
use std::time::Duration;
use tracing::info;

const DEFAULT_BOT_TOKEN: &str = match option_env!("QHTD_TELEGRAM_BOT_TOKEN") { Some(t) => t, None => "" };

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct ClientTelegramInfo {
    pub client_name: String,
    pub chat_id: i64,
    pub telegram_username: Option<String>,
    pub first_name: Option<String>,
    pub linked_at: String,
    pub verified: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct TelegramConfig {
    pub bot_token: String,
    pub enabled: bool,
    pub clients: HashMap<String, ClientTelegramInfo>,
}

fn config_path() -> PathBuf {
    let candidates = [
        PathBuf::from(r"D:\Workspace\Python\QHTDautomation\MunAutomationDesktop\client_telegram_map.json"),
        PathBuf::from("MunAutomationDesktop").join("client_telegram_map.json"),
        PathBuf::from("client_telegram_map.json"),
    ];
    for c in &candidates {
        if c.exists() {
            return c.clone();
        }
    }
    candidates[0].clone()
}

fn global_config() -> &'static RwLock<TelegramConfig> {
    static CONFIG: OnceLock<RwLock<TelegramConfig>> = OnceLock::new();
    CONFIG.get_or_init(|| {
        let p = config_path();
        let cfg = if p.exists() {
            std::fs::read_to_string(&p)
                .ok()
                .and_then(|s| serde_json::from_str(&s).ok())
                .unwrap_or_else(|| TelegramConfig {
                    bot_token: DEFAULT_BOT_TOKEN.into(),
                    enabled: true,
                    clients: HashMap::new(),
                })
        } else {
            TelegramConfig {
                bot_token: DEFAULT_BOT_TOKEN.into(),
                enabled: true,
                clients: HashMap::new(),
            }
        };
        RwLock::new(cfg)
    })
}

pub fn save_config() {
    let p = config_path();
    if let Some(parent) = p.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let cfg = global_config().read().clone();
    if let Ok(s) = serde_json::to_string_pretty(&cfg) {
        let _ = std::fs::write(&p, s);
    }
}

pub fn get_bot_token() -> String {
    // Ưu tiên đọc từ file riêng nếu có, fallback config hoặc default
    if let Ok(t) = std::fs::read_to_string("telegram_bot_token.txt") {
        let trimmed = t.trim();
        if !trimmed.is_empty() {
            return trimmed.to_string();
        }
    }
    let t = global_config().read().bot_token.clone();
    if t.trim().is_empty() {
        DEFAULT_BOT_TOKEN.into()
    } else {
        t
    }
}

pub fn get_linked_clients() -> HashMap<String, ClientTelegramInfo> {
    global_config().read().clients.clone()
}

pub fn link_client_chat_id(client_name: &str, chat_id: i64, username: Option<String>, first_name: Option<String>) {
    let now = chrono::Local::now().format("%d/%m/%Y %H:%M:%S").to_string();
    let norm_name = client_name.trim().to_lowercase();
    let info = ClientTelegramInfo {
        client_name: norm_name.clone(),
        chat_id,
        telegram_username: username,
        first_name,
        linked_at: now,
        verified: true,
    };
    {
        let mut cfg = global_config().write();
        cfg.clients.insert(norm_name, info);
    }
    save_config();
}

/// Gửi tin nhắn qua Telegram Bot API (không chặn, an toàn trong mọi thread context)
pub fn send_telegram_raw(chat_id: i64, html_text: &str) {
    let token = get_bot_token();
    let text = html_text.to_string();
    std::thread::spawn(move || {
        let rt = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build();
        if let Ok(rt) = rt {
            rt.block_on(async {
                let client = reqwest::Client::builder().timeout(Duration::from_secs(10)).build();
                if let Ok(client) = client {
                    let url = format!("https://api.telegram.org/bot{}/sendMessage", token);
                    let payload = serde_json::json!({
                        "chat_id": chat_id,
                        "text": text,
                        "parse_mode": "HTML",
                        "disable_web_page_preview": true
                    });
                    let _ = client.post(&url).json(&payload).send().await;
                }
            });
        }
    });
}

/// Gửi thông báo đến Client theo tên sở hữu (ví dụ "lanemm", "tiktok12"...)
pub fn notify_client(client_name: &str, title: &str, details: &str) {
    let norm_name = client_name.trim().to_lowercase();
    let client_opt = {
        let cfg = global_config().read();
        cfg.clients.get(&norm_name).cloned()
    };

    if let Some(ci) = client_opt {
        if ci.verified && ci.chat_id != 0 {
            let now = chrono::Local::now().format("%d/%m %H:%M:%S").to_string();
            let msg = format!(
                "🔔 <b>{}</b>\n\
                 ━━━━━━━━━━━━━━━━━━\n\
                 👤 <b>Khách hàng:</b> <code>{}</code>\n\
                 {}\n\
                 🕒 <i>{}</i>",
                title, ci.client_name, details, now
            );
            send_telegram_raw(ci.chat_id, &msg);
            info!("📨 [Telegram] Đã gửi thông báo cho client '{}' (chat_id: {})", ci.client_name, ci.chat_id);
        }
    }
}

static POLLING_RUNNING: AtomicBool = AtomicBool::new(false);
static LAST_UPDATE_ID: AtomicI64 = AtomicI64::new(0);

/// Khởi chạy background poller lắng nghe tin nhắn xác thực từ client qua bot @C69autobot
pub fn start_telegram_polling() {
    if POLLING_RUNNING.swap(true, Ordering::SeqCst) {
        return;
    }

    tokio::spawn(async move {
        info!("🤖 [Telegram Bot] Bắt đầu lắng nghe tin nhắn xác thực client qua @C69autobot...");
        let client = reqwest::Client::builder().timeout(Duration::from_secs(30)).build().unwrap();

        loop {
            let token = get_bot_token();
            let offset = LAST_UPDATE_ID.load(Ordering::SeqCst);
            let url = format!(
                "https://api.telegram.org/bot{}/getUpdates?timeout=15&offset={}",
                token, offset
            );

            match client.get(&url).send().await {
                Ok(resp) => {
                    if let Ok(data) = resp.json::<serde_json::Value>().await {
                        if let Some(updates) = data.get("result").and_then(|r| r.as_array()) {
                            for up in updates {
                                if let Some(uid) = up.get("update_id").and_then(|v| v.as_i64()) {
                                    LAST_UPDATE_ID.store(uid + 1, Ordering::SeqCst);
                                }

                                if let Some(msg) = up.get("message") {
                                    let chat_id = msg.get("chat").and_then(|c| c.get("id")).and_then(|v| v.as_i64()).unwrap_or(0);
                                    let text = msg.get("text").and_then(|t| t.as_str()).unwrap_or("").trim();
                                    let tg_username = msg.get("from").and_then(|f| f.get("username")).and_then(|v| v.as_str()).map(|s| s.to_string());
                                    let first_name = msg.get("from").and_then(|f| f.get("first_name")).and_then(|v| v.as_str()).map(|s| s.to_string());

                                    if chat_id == 0 || text.is_empty() {
                                        continue;
                                    }

                                    handle_incoming_telegram_message(chat_id, text, tg_username, first_name).await;
                                }
                            }
                        }
                    }
                }
                Err(_e) => {
                    tokio::time::sleep(Duration::from_secs(5)).await;
                }
            }

            tokio::time::sleep(Duration::from_millis(1500)).await;
        }
    });
}

async fn handle_incoming_telegram_message(
    chat_id: i64,
    text: &str,
    tg_username: Option<String>,
    first_name: Option<String>,
) {
    let clean = text.trim();

    // 1. Lệnh /myid
    if clean.eq_ignore_ascii_case("/myid") || clean.eq_ignore_ascii_case("/id") {
        let resp = format!(
            "🆔 <b>Telegram ID của bạn:</b> <code>{}</code>\n\
             👤 <b>Username:</b> @{}\n\
             💡 Bạn có thể dùng ID này điền vào tool hoặc gửi: <code>/start &lt;tên_client&gt;</code> để kích hoạt.",
            chat_id, tg_username.as_deref().unwrap_or("none")
        );
        send_telegram_raw(chat_id, &resp);
        return;
    }

    // 2. Lệnh /start hoặc cú pháp xác thực
    let target_client = if clean.starts_with("/start") || clean.starts_with("/verify") || clean.starts_with("/link") {
        let parts: Vec<&str> = clean.split_whitespace().collect();
        if parts.len() > 1 {
            Some(parts[1].trim().to_lowercase())
        } else {
            None
        }
    } else if !clean.starts_with('/') && clean.len() >= 3 && clean.len() <= 32 {
        // Client gõ thẳng username của họ (ví dụ "lanemm", "tiktok12")
        Some(clean.to_lowercase())
    } else {
        None
    };

    if let Some(client_name) = target_client {
        // Kiểm tra xem client này có phải là username hợp lệ trên C69 không
        let c69_valid = verify_c69_user_exists(&client_name).await;
        
        link_client_chat_id(&client_name, chat_id, tg_username.clone(), first_name.clone());

        let welcome_msg = format!(
            "✅ <b>XÁC THỰC LIÊN KẾT THÀNH CÔNG!</b>\n\
             ━━━━━━━━━━━━━━━━━━━━━━\n\
             👤 <b>Tài khoản C69:</b> <code>{}</code>\n\
             🆔 <b>Telegram Chat ID:</b> <code>{}</code>\n\
             📱 <b>Xác thực C69:</b> {}\n\
             ━━━━━━━━━━━━━━━━━━━━━━\n\
             🎉 Từ bây giờ, bot <b>@C69autobot</b> sẽ tự động gửi thông báo trực tiếp khi tài khoản của bạn:\n\
             • Đăng nhập thành công / Nuôi tương tác video\n\
             • Bị Rate-limit / Đổi Proxy tự động\n\
             • Bị khóa (Banned) hoặc Sai mật khẩu\n\n\
             <i>Chúc bạn vận hành hiệu quả cùng hệ sinh thái C69!</i>",
            client_name, chat_id, if c69_valid { "Đã khớp C69 Database ✓" } else { "Đã ghi nhận ✓" }
        );
        send_telegram_raw(chat_id, &welcome_msg);
        info!("🎉 [Telegram] Đã liên kết thành công client '{}' với chat_id: {}", client_name, chat_id);
    } else {
        let help_msg = format!(
            "👋 <b>Xin chào {}!</b>\n\n\
             Để nhận thông báo tự động từ tool Phone Farm C69, vui lòng gửi tin nhắn theo cú pháp:\n\
             👉 <code>/start &lt;tên_tài_khoản_c69&gt;</code>\n\
             <i>(Ví dụ: <code>/start lanemm</code> hoặc <code>/start tiktok12</code>)</i>\n\n\
             Hoặc gõ <code>/myid</code> để xem ID Telegram của bạn.",
            first_name.as_deref().unwrap_or("bạn")
        );
        send_telegram_raw(chat_id, &help_msg);
    }
}

async fn verify_c69_user_exists(username: &str) -> bool {
    let sess = crate::browser_nurture::load_c69_session();
    let server_url = sess.as_ref().map(|s| s.server_url.as_str()).unwrap_or(crate::browser_nurture::DEFAULT_C69_API_URL);
    let token = sess.as_ref().and_then(|s| s.token.clone()).unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());

    let client = reqwest::Client::builder().timeout(Duration::from_secs(6)).build().ok();
    if let Some(client) = client {
        let url = format!("{}/dashboard/api/accounts/users-list/?search={}&page_size=5", server_url, urlencoding::encode(username));
        if let Ok(resp) = client.get(&url).header("Authorization", &token).send().await {
            if let Ok(val) = resp.json::<serde_json::Value>().await {
                if let Some(results) = val.get("results").and_then(|r| r.as_array()) {
                    return results.iter().any(|u| {
                        u.get("username").and_then(|v| v.as_str()).map(|un| un.eq_ignore_ascii_case(username)).unwrap_or(false)
                    });
                }
            }
        }
    }
    false
}
