//! Tự động TẠO tài khoản TikTok trên phone farm bằng Native XML (uiautomator) + OTP đọc từ hòm thư C69.
//!
//! Module con của `xml_login` để tái dùng các primitive đã verify live (dump_screen, tap, fill_field,
//! rotate_device_proxy, reset_app_clean, fetch_otp_from_c69, ...).
//!
//! Luồng (đã đi tay trên máy thật để lấy đúng text/desc từng màn hình):
//!   Profile(guest) -> Login -> "Don't have an account? Sign up" -> "Use phone or email"
//!   -> Birthday (3 SeekBar picker, đọc lại EditText "October 21, 2001" để verify)
//!   -> tab Email -> nhập email -> Continue -> (Captcha?) -> nhập mã 6 số từ C69
//!   -> Create password -> (Create username) -> Feed -> mở Profile đọc @username thật
//!   -> đăng ký nick vào C69 (add-manual, link accounts_emails_id).
//!
//! Mọi bước đều chờ MÀN HÌNH ĐÍCH xuất hiện (verify bằng XML) rồi mới đi tiếp; không có bước "tin là xong".

use super::*;

// ───────────────────────────── Types ─────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, Default)]
pub struct SignupSpec {
    /// Email dùng đăng ký (phải đọc được trên C69).
    pub email: String,
    /// ID hộp thư trên C69; bỏ trống thì tự tra theo email.
    #[serde(default)]
    pub email_id: Option<u64>,
    /// Mật khẩu TikTok; bỏ trống thì tự sinh (8-20 ký tự, có chữ hoa/thường/số/ký tự đặc biệt).
    #[serde(default)]
    pub password: String,
    /// Client sở hữu (Telegram notify + owner trên C69).
    #[serde(default)]
    pub client: Option<String>,
}

#[derive(Debug, Clone, Serialize, Default)]
pub struct SignupStatus {
    pub serial: String,
    pub email: String,
    /// queued | running | success | failed
    pub state: String,
    pub step: String,
    pub message: String,
    pub username: String,
    pub c69_account_id: Option<u64>,
    pub updated: String,
    pub logs: Vec<String>,
}

#[derive(Debug, Clone)]
pub struct SignupOutcome {
    pub ok: bool,
    pub code: String,
    pub msg: String,
    pub username: Option<String>,
    pub password: String,
    pub c69_account_id: Option<u64>,
}

fn su_map() -> &'static RwLock<HashMap<String, SignupStatus>> {
    static M: OnceLock<RwLock<HashMap<String, SignupStatus>>> = OnceLock::new();
    M.get_or_init(|| RwLock::new(HashMap::new()))
}

static SU_STOP: AtomicBool = AtomicBool::new(false);
static SU_RUNNING: AtomicBool = AtomicBool::new(false);

pub fn signup_snapshot() -> Vec<SignupStatus> {
    let mut v: Vec<SignupStatus> = su_map().read().values().cloned().collect();
    v.sort_by(|a, b| a.serial.cmp(&b.serial));
    v
}
pub fn signup_is_running() -> bool {
    SU_RUNNING.load(Ordering::SeqCst)
}
pub fn signup_stop() {
    SU_STOP.store(true, Ordering::SeqCst);
}

fn su_upd(serial: &str, f: impl FnOnce(&mut SignupStatus)) {
    let mut m = su_map().write();
    let e = m.entry(serial.to_string()).or_insert_with(|| SignupStatus { serial: serial.to_string(), ..Default::default() });
    f(e);
    e.updated = now_str();
}

fn slog(serial: &str, step: &str, msg: impl Into<String>) {
    let msg = msg.into();
    info!("[XMLSignup {}] {} — {}", serial, step, msg);
    su_upd(serial, |s| {
        s.step = step.to_string();
        s.logs.push(format!("{} {} — {}", now_str(), step, msg));
        if s.logs.len() > 60 {
            let drop = s.logs.len() - 60;
            s.logs.drain(0..drop);
        }
    });
}

// ───────────────────────────── Pure helpers (có unit test) ─────────────────────────────

const MONTHS: [&str; 12] = [
    "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december",
];

/// "October 21, 2001" -> (month 1..12, day, year)
pub fn parse_birthday(text: &str) -> Option<(u32, u32, i32)> {
    let t = text.trim().replace(',', " ");
    let parts: Vec<&str> = t.split_whitespace().collect();
    if parts.len() != 3 {
        return None;
    }
    let m0 = parts[0].to_lowercase();
    if m0.len() < 3 {
        return None;
    }
    let month = MONTHS.iter().position(|m| m.starts_with(&m0[..3]))? as u32 + 1;
    let day: u32 = parts[1].parse().ok()?;
    let year: i32 = parts[2].parse().ok()?;
    if !(1..=31).contains(&day) || !(1900..=2100).contains(&year) {
        return None;
    }
    Some((month, day, year))
}

/// Ngày sinh ngẫu nhiên, luôn ≥ 21 tuổi (năm 1992..=2002), ngày ≤ 28 để mọi tháng đều hợp lệ.
pub fn gen_birthday(rng: &mut impl Rng) -> (u32, u32, i32) {
    (rng.gen_range(1..=12), rng.gen_range(1..=28), rng.gen_range(1992..=2002))
}

/// Mật khẩu TikTok hợp lệ: 12 ký tự, đủ hoa/thường/số/đặc biệt.
pub fn gen_password(rng: &mut impl Rng) -> String {
    const LOW: &[u8] = b"abcdefghjkmnpqrstuvwxyz";
    const UP: &[u8] = b"ABCDEFGHJKLMNPQRSTUVWXYZ";
    const NUM: &[u8] = b"23456789";
    const SPC: &[u8] = b"!@#$%";
    let mut v: Vec<u8> = Vec::new();
    for _ in 0..4 { v.push(LOW[rng.gen_range(0..LOW.len())]); }
    for _ in 0..3 { v.push(UP[rng.gen_range(0..UP.len())]); }
    for _ in 0..3 { v.push(NUM[rng.gen_range(0..NUM.len())]); }
    for _ in 0..2 { v.push(SPC[rng.gen_range(0..SPC.len())]); }
    v.shuffle(rng);
    // ký tự đầu luôn là chữ cái để tránh bị TikTok/ADB hiểu nhầm
    if !v[0].is_ascii_alphabetic() {
        if let Some(p) = v.iter().position(|c| c.is_ascii_alphabetic()) { v.swap(0, p); }
    }
    String::from_utf8(v).unwrap_or_else(|_| "Abcd1234!xyz".into())
}

#[derive(Debug, PartialEq, Eq, Clone, Copy)]
pub enum SignupScreen {
    NotTikTok,
    LoginMenu,
    SignUpMenu,
    Birthday,
    PhoneEmailForm,
    EmailCode,
    CreatePassword,
    CreateUsername,
    RateLimit,
    Captcha,
    Feed,
    ProfileGuest,
    Onboarding,
    Unknown,
}

pub fn classify(scr: &Screen) -> SignupScreen {
    if !scr.pkg.is_empty() && scr.pkg != APP_PKG {
        return SignupScreen::NotTikTok;
    }
    match scr.error_kind() {
        Some(("RATE_LIMIT", _)) => return SignupScreen::RateLimit,
        Some(("CAPTCHA", _)) => return SignupScreen::Captcha,
        _ => {}
    }
    if scr.has_contains(&["when's your birthday"]) {
        return SignupScreen::Birthday;
    }
    if scr.edit_field(true).is_some() {
        return SignupScreen::CreatePassword;
    }
    let has_tabs = scr.has_label(&["Phone"]) && scr.has_label(&["Email"]);
    if has_tabs && scr.any_edit().is_some() {
        return SignupScreen::PhoneEmailForm;
    }
    if scr.has_contains(&["6-digit", "6 digit", "enter code", "verification code", "enter the code", "we sent a", "code was sent", "sent a code"]) {
        return SignupScreen::EmailCode;
    }
    if scr.any_edit().is_some() && scr.has_contains(&["create username", "choose a username", "choose your username", "pick a username", "create your username"]) {
        return SignupScreen::CreateUsername;
    }
    if scr.has_label(&["Use phone or email"]) {
        return SignupScreen::SignUpMenu;
    }
    if scr.has_label(&["Use phone / email / username"]) {
        return SignupScreen::LoginMenu;
    }
    if scr.has_contains(&["log into existing account"]) {
        return SignupScreen::ProfileGuest;
    }
    if scr.has_contains(&["choose your interests", "how ads are shown", "reconfirm", "swipe up for more", "allow tiktok", "find your friends"])
        || scr.find_btn(&["Skip", "Not now", "Maybe later", "Later", "Got it"]).is_some()
    {
        return SignupScreen::Onboarding;
    }
    if scr.has_label(&["Home"]) && scr.has_label(&["Inbox"]) && scr.has_label(&["Profile"]) {
        return SignupScreen::Feed;
    }
    SignupScreen::Unknown
}

fn screen_digest(scr: &Screen) -> String {
    let mut out: Vec<String> = Vec::new();
    for n in &scr.nodes {
        let t = n.text.trim();
        let d = n.desc.trim();
        let s = if !t.is_empty() { t } else { d };
        if !s.is_empty() && s.len() < 70 {
            out.push(s.to_string());
        }
        if out.len() >= 14 {
            break;
        }
    }
    out.join(" | ")
}

// ───────────────────────────── Device actions ─────────────────────────────

fn find_by_desc<'a>(scr: &'a Screen, desc: &str) -> Option<&'a UiNode> {
    scr.nodes.iter().find(|n| n.desc == desc && n.has_area())
}

fn birthday_field_text(scr: &Screen) -> Option<String> {
    scr.nodes.iter().find(|n| n.is_edit() && n.has_area()).map(|n| n.text.clone())
}

/// Vuốt 1 cột picker tới khi EditText "Month D, YYYY" khớp `target` (vòng kín: đọc lại XML sau mỗi lần vuốt).
fn spin_picker(adb: &Path, serial: &str, picker_desc: &str, target: i32, read: impl Fn(&(u32, u32, i32)) -> i32) -> bool {
    for _ in 0..30 {
        if SU_STOP.load(Ordering::SeqCst) {
            return false;
        }
        let scr = match dump_screen(adb, serial) {
            Some(s) => s,
            None => {
                sleep_ms(700);
                continue;
            }
        };
        let cur = match birthday_field_text(&scr).and_then(|t| parse_birthday(&t)) {
            Some(b) => read(&b),
            None => {
                // EditText còn hint "Birthday": nhúc nhẹ picker để nó điền giá trị mặc định
                if let Some(n) = find_by_desc(&scr, picker_desc) {
                    let (cx, _) = n.center();
                    adb_shell(adb, serial, &format!("input swipe {} {} {} {} 500", cx, n.bounds.1 + 110, cx, n.bounds.1 + 150));
                }
                sleep_ms(900);
                continue;
            }
        };
        if cur == target {
            return true;
        }
        let node = match find_by_desc(&scr, picker_desc) {
            Some(n) => n.clone(),
            None => return false,
        };
        let (cx, _) = node.center();
        let top = node.bounds.1;
        let diff = cur - target;
        // vuốt xuống = giá trị giảm; vuốt lên = giá trị tăng
        let (a, b, dur) = if diff.abs() >= 3 { (top + 40, top + 220, 250) } else { (top + 100, top + 180, 600) };
        let (y1, y2) = if diff > 0 { (a, b) } else { (b, a) };
        adb_shell(adb, serial, &format!("input swipe {} {} {} {} {}", cx, y1, cx, y2, dur));
        sleep_ms(1300);
    }
    false
}

fn set_birthday(adb: &Path, serial: &str, target: (u32, u32, i32)) -> bool {
    for _round in 0..2 {
        if !spin_picker(adb, serial, "Year picker", target.2, |b| b.2) {
            continue;
        }
        if !spin_picker(adb, serial, "Month picker", target.0 as i32, |b| b.0 as i32) {
            continue;
        }
        if !spin_picker(adb, serial, "Day picker", target.1 as i32, |b| b.1 as i32) {
            continue;
        }
        // verify cuối: cả 3 thành phần phải khớp sau khi tất cả picker đã dừng
        if let Some(b) = dump_screen(adb, serial).and_then(|s| birthday_field_text(&s)).and_then(|t| parse_birthday(&t)) {
            if b == (target.0, target.1, target.2) {
                return true;
            }
        }
    }
    false
}

/// Gõ chuỗi số bằng keyevent (không phụ thuộc IME).
fn type_digits(adb: &Path, serial: &str, digits: &str) {
    for ch in digits.chars() {
        if let Some(d) = ch.to_digit(10) {
            adb_shell(adb, serial, &format!("input keyevent {}", 7 + d));
            sleep_ms(110);
        }
    }
}

/// Dọn dẹp dialog hệ thống / quyền xin trong lúc signup. Trả về true nếu đã bấm gì đó.
fn dismiss_system_dialog(adb: &Path, serial: &str, scr: &Screen) -> bool {
    if let Some(b) = scr.find_btn(&["Allow", "While using the app", "ALLOW", "OK", "Got it", "Don't allow", "DENY"]) {
        tap_node(adb, serial, b);
        sleep_ms(900);
        return true;
    }
    false
}

/// Chuẩn bị máy: proxy US mới + danh tính mới + app sạch. `hard=false` -> không reboot.
fn prepare_device(adb: &Path, serial: &str) -> Result<(), String> {
    let px = rotate_device_proxy(adb, serial)?;
    slog(serial, "PROXY", format!("Proxy US mới + IP thoát đã đối soát: {}", px));
    adb_shell(adb, serial, "input keyevent 224");
    adb_shell(adb, serial, "input keyevent 82");
    // Ưu tiên danh tính thuần Rust nếu phần cứng thuộc pool Exynos 8895; ngược lại dùng đường reset sẵn có của login.
    match crate::device_profile::apply_new(adb, serial) {
        Ok(p) => {
            slog(serial, "IDENTITY", format!("device_profile (Rust): {} / {} / IMEI {}", p.model, p.build, p.imei));
            adb_shell(adb, serial, &format!("am force-stop {}", APP_PKG));
            adb_shell(adb, serial, &format!("pm clear {}", APP_PKG));
            launch_app(adb, serial);
            sleep_ms(2500);
        }
        Err(e) => {
            slog(serial, "IDENTITY", format!("device_profile không áp dụng được ({}), dùng reset_app_clean của login", e));
            reset_app_clean(adb, serial, false);
        }
    }
    Ok(())
}

// ───────────────────────────── C69 helpers ─────────────────────────────

fn c69_block<T>(f: impl std::future::Future<Output = T>) -> Option<T> {
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().ok()?;
    Some(rt.block_on(f))
}

pub fn register_on_c69(username: &str, spec: &SignupSpec, password: &str, email_id: u64) -> Option<u64> {
    let payload = serde_json::json!({
        "username": username,
        "email": spec.email,
        "password": password,
        "type": "tiktok",
        "accounts_emails_id": email_id,
        "profile_id": "none",
        "note": format!("[{}] Tạo tự động bằng MunAutomation (XML Rust)", chrono::Local::now().format("%d/%m %H:%M")),
    });
    let res = c69_block(crate::browser_nurture::add_c69_account_manual(payload))?;
    match res {
        Ok(v) => {
            if v.get("success").and_then(|s| s.as_bool()).unwrap_or(false) {
                v.get("account_id").and_then(|i| i.as_u64())
            } else {
                warn!("[XMLSignup] C69 add-manual từ chối: {}", v);
                None
            }
        }
        Err(e) => {
            warn!("[XMLSignup] C69 add-manual lỗi: {}", e);
            None
        }
    }
}

/// Chờ OTP mới từ C69 (mã chưa từng dùng trong phiên này). Trả về None nếu quá `max_s` giây.
fn wait_otp(serial: &str, email_id: u64, used: &[String], max_s: u64) -> Option<String> {
    let start = Instant::now();
    let mut attempt = 0;
    while start.elapsed() < Duration::from_secs(max_s) {
        if SU_STOP.load(Ordering::SeqCst) {
            return None;
        }
        attempt += 1;
        if let Some(code) = fetch_otp_from_c69(email_id) {
            if !used.contains(&code) {
                return Some(code);
            }
        }
        if attempt % 5 == 0 {
            slog(serial, "OTP_WAIT", format!("Chưa có OTP mới trong hòm thư C69 (đã chờ {}s)", start.elapsed().as_secs()));
        }
        sleep_ms(4000);
    }
    None
}

// ───────────────────────────── Worker chính cho 1 máy / 1 email ─────────────────────────────

fn fail(serial: &str, code: &str, msg: &str, password: &str) -> SignupOutcome {
    su_upd(serial, |s| {
        s.state = "failed".into();
        s.message = format!("{}: {}", code, msg);
    });
    slog(serial, code, msg);
    SignupOutcome { ok: false, code: code.into(), msg: msg.into(), username: None, password: password.into(), c69_account_id: None }
}

pub fn signup_one(adb: PathBuf, serial: String, mut spec: SignupSpec) -> SignupOutcome {
    su_upd(&serial, |s| {
        s.state = "running".into();
        s.email = spec.email.clone();
        s.message.clear();
        s.username.clear();
        s.c69_account_id = None;
    });
    slog(&serial, "START", format!("Đăng ký TikTok bằng email {}", spec.email));

    let mut rng = rand::thread_rng();
    if spec.password.trim().is_empty() {
        spec.password = gen_password(&mut rng);
    }
    let password = spec.password.clone();
    let birthday = gen_birthday(&mut rng);
    drop(rng);

    // 1. Email phải tồn tại và đọc được trên C69
    let email_id = match spec.email_id.or_else(|| resolve_email_id_by_address(&spec.email)) {
        Some(i) => i,
        None => return fail(&serial, "EMAIL_NOT_ON_C69", "Không tìm thấy email này trên C69", &password),
    };
    let (chk, _) = check_c69_email_status(email_id);
    if chk != C69EmailCheck::Readable && chk != C69EmailCheck::Unregistered {
        // Hòm thư trống (chưa có thư nào) cũng là trạng thái hợp lệ cho email mới -> check_c69_email_status trả Unreadable khi emails=[]
        // nên dùng thêm phép đọc trực tiếp để phân biệt "trống" với "lỗi đọc".
        if !mailbox_reachable(email_id) {
            return fail(&serial, "EMAIL_UNREADABLE", "Hòm thư C69 không đọc được (không lấy được OTP) -> bỏ qua email này", &password);
        }
    }
    slog(&serial, "EMAIL_CHECK", format!("Hòm thư C69 #{} đọc được 🟢", email_id));

    // 2. Chuẩn bị máy
    if let Err(e) = prepare_device(&adb, &serial) {
        return fail(&serial, "NO_INTERNET", &e, &password);
    }

    let started = Instant::now();
    let mut used_codes: Vec<String> = Vec::new();
    let mut restarts = 0;
    let mut last_class = SignupScreen::Unknown;
    let mut same_class_count = 0;
    let mut unknown = 0;
    let mut dump_fail = 0;
    let mut bday_done = false;
    let mut email_submitted = false;
    let mut code_tries = 0;
    let mut pwd_done = false;
    let mut code_screen_since: Option<Instant> = None;
    let mut resend_done = false;
    let mut verify_attempts = 0;

    for _step in 0..260 {
        if SU_STOP.load(Ordering::SeqCst) {
            return fail(&serial, "STOPPED", "Đã dừng theo yêu cầu", &password);
        }
        if started.elapsed() > Duration::from_secs(900) {
            return fail(&serial, "TIMEOUT", "Quá 15 phút chưa đăng ký xong", &password);
        }
        let scr = match dump_screen(&adb, &serial) {
            Some(s) => {
                dump_fail = 0;
                s
            }
            None => {
                dump_fail += 1;
                slog(&serial, "DUMP", format!("Không đọc được UI XML (lần {})", dump_fail));
                if dump_fail == 2 {
                    relaunch_app(&adb, &serial);
                } else if dump_fail >= 4 {
                    return fail(&serial, "DUMP_FAIL", "Không đọc được UI XML nhiều lần liên tiếp", &password);
                }
                sleep_ms(1200);
                continue;
            }
        };

        let cls = classify(&scr);
        if cls == last_class {
            same_class_count += 1;
        } else {
            same_class_count = 0;
            last_class = cls;
            slog(&serial, "SCREEN", format!("{:?}", cls));
        }
        if same_class_count > 14 && !matches!(cls, SignupScreen::EmailCode) {
            let dg = screen_digest(&scr);
            return fail(&serial, "STUCK", &format!("Kẹt ở màn {:?} quá lâu: {}", cls, dg), &password);
        }

        match cls {
            SignupScreen::NotTikTok => {
                if !dismiss_system_dialog(&adb, &serial, &scr) {
                    launch_app(&adb, &serial);
                    sleep_ms(2500);
                }
            }
            SignupScreen::RateLimit => {
                restarts += 1;
                if restarts > 3 {
                    return fail(&serial, "RATE_LIMIT", "TikTok báo 'Maximum number of attempts' sau 3 lần đổi proxy + danh tính", &password);
                }
                slog(&serial, "RATE_LIMIT", format!("Maximum attempts -> đổi proxy + danh tính mới (lần {}/3)", restarts));
                if let Err(e) = prepare_device(&adb, &serial) {
                    return fail(&serial, "NO_INTERNET", &e, &password);
                }
                bday_done = false;
                email_submitted = false;
            }
            SignupScreen::Captcha => {
                slog(&serial, "CAPTCHA", "Gặp captcha puzzle -> giải bằng captcha_solver (Rust)");
                match crate::captcha_solver::solve_if_present_sync(&adb, &serial, 720, 1480) {
                    Ok(true) => slog(&serial, "CAPTCHA", "Đã kéo mảnh ghép, chờ TikTok xác nhận"),
                    Ok(false) => {}
                    Err(e) => slog(&serial, "CAPTCHA", format!("Giải captcha lỗi: {}", e)),
                }
                sleep_ms(2500);
            }
            SignupScreen::ProfileGuest => {
                if let Some(b) = scr.find_btn(&["Login"]) {
                    tap_node(&adb, &serial, b);
                } else {
                    tap(&adb, &serial, 360, 732);
                }
                sleep_ms(1800);
            }
            SignupScreen::LoginMenu => {
                if let Some(b) = scr.find_btn(&["Don’t have an account? Sign up", "Don't have an account? Sign up"]) {
                    tap_node(&adb, &serial, b);
                } else {
                    tap(&adb, &serial, 360, 1343);
                }
                sleep_ms(1800);
            }
            SignupScreen::SignUpMenu => {
                if let Some(b) = scr.find_btn(&["Use phone or email"]) {
                    tap_node(&adb, &serial, b);
                } else {
                    tap(&adb, &serial, 349, 692);
                }
                sleep_ms(1800);
            }
            SignupScreen::Birthday => {
                if bday_done {
                    // đã đặt xong nhưng vẫn ở màn này => bấm Next lại
                    if let Some(b) = scr.find_btn(&["Next"]) {
                        tap_node(&adb, &serial, b);
                    }
                    sleep_ms(1800);
                } else {
                    slog(&serial, "BIRTHDAY", format!("Đặt ngày sinh {}/{}/{}", birthday.0, birthday.1, birthday.2));
                    if !set_birthday(&adb, &serial, birthday) {
                        return fail(&serial, "BIRTHDAY_FAIL", "Không đặt được ngày sinh bằng picker (verify EditText không khớp)", &password);
                    }
                    bday_done = true;
                    slog(&serial, "BIRTHDAY", "Ngày sinh đã khớp EditText ✔");
                    if let Some(s2) = dump_screen(&adb, &serial) {
                        if let Some(b) = s2.find_btn(&["Next"]) {
                            tap_node(&adb, &serial, b);
                        } else {
                            tap(&adb, &serial, 360, 508);
                        }
                    }
                    sleep_ms(2200);
                }
            }
            SignupScreen::PhoneEmailForm => {
                // đảm bảo đang ở tab Email
                let on_email = scr.has_contains(&["email address"]);
                if !on_email {
                    if let Some(tab) = find_by_desc(&scr, "Email") {
                        tap_node(&adb, &serial, tab);
                        sleep_ms(1200);
                        continue;
                    }
                }
                let field = match scr.any_edit() {
                    Some(f) => f.clone(),
                    None => {
                        sleep_ms(800);
                        continue;
                    }
                };
                if email_submitted && scr.has_contains(&["maximum number of attempts"]) {
                    continue;
                }
                if !fill_field(&adb, &serial, &field, &spec.email, true) {
                    return fail(&serial, "EMAIL_TYPE_FAIL", "Gõ email vào ô Email address nhưng XML không khớp", &password);
                }
                slog(&serial, "EMAIL", format!("Đã nhập {} (verify XML ✔)", spec.email));
                tap_submit(&adb, &serial, &["Continue", "Next"], &scr);
                email_submitted = true;
                code_screen_since = None;
                // chờ rời form: sang EmailCode / lỗi / captcha
                wait_leave(&adb, &serial, |s| classify(s) == SignupScreen::PhoneEmailForm && !s.has_contains(&["maximum number of attempts"]), 25);
                // TikTok báo email đã dùng/không hợp lệ ngay trên form
                if let Some(s2) = dump_screen(&adb, &serial) {
                    if classify(&s2) == SignupScreen::PhoneEmailForm {
                        if s2.has_contains(&["already", "registered", "linked to another", "already in use", "has been used"]) {
                            return fail(&serial, "EMAIL_USED", "Email này đã gắn với tài khoản TikTok khác", &password);
                        }
                        if s2.has_contains(&["invalid email", "enter a valid email", "not a valid email"]) {
                            return fail(&serial, "EMAIL_INVALID", "TikTok báo email không hợp lệ", &password);
                        }
                    }
                }
            }
            SignupScreen::EmailCode => {
                let since = *code_screen_since.get_or_insert_with(Instant::now);
                code_tries += 1;
                if code_tries > 4 {
                    return fail(&serial, "OTP_FAIL", "Nhập mã OTP sai/hết hạn 4 lần", &password);
                }
                slog(&serial, "OTP", format!("Đang chờ mã 6 số trong hòm thư C69 #{} (lần {})", email_id, code_tries));
                let code = match wait_otp(&serial, email_id, &used_codes, 120) {
                    Some(c) => c,
                    None => {
                        if !resend_done {
                            resend_done = true;
                            if let Some(b) = scr.find_btn(&["Resend code", "Resend"]) {
                                slog(&serial, "OTP", "Chưa có mã -> bấm Resend code");
                                tap_node(&adb, &serial, b);
                                sleep_ms(2000);
                                continue;
                            }
                        }
                        let _ = since;
                        return fail(&serial, "OTP_TIMEOUT", "Không nhận được OTP trong hòm thư C69 (120s)", &password);
                    }
                };
                slog(&serial, "OTP", format!("Có mã {} -> nhập vào TikTok", code));
                used_codes.push(code.clone());
                if let Some(f) = scr.any_edit() {
                    tap_node(&adb, &serial, f);
                } else {
                    tap(&adb, &serial, 138, 255);
                }
                sleep_ms(400);
                type_digits(&adb, &serial, &code);
                sleep_ms(900);
                if let Some(s2) = dump_screen(&adb, &serial) {
                    if classify(&s2) == SignupScreen::EmailCode {
                        if let Some(b) = s2.find_btn(&["Next", "Continue", "Verify", "Submit"]) {
                            tap_node(&adb, &serial, b);
                        }
                    }
                }
                wait_leave(&adb, &serial, |s| classify(s) == SignupScreen::EmailCode && !s.has_contains(&["incorrect", "invalid", "expired", "try again"]), 25);
                if let Some(s3) = dump_screen(&adb, &serial) {
                    if classify(&s3) == SignupScreen::EmailCode {
                        slog(&serial, "OTP", "Mã bị từ chối -> thử mã mới");
                        resend_done = false;
                        code_screen_since = None;
                    } else {
                        slog(&serial, "OTP", "Mã được chấp nhận ✔");
                    }
                }
            }
            SignupScreen::CreatePassword => {
                if pwd_done && scr.has_contains(&["password"]) && same_class_count > 3 {
                    // Có thể TikTok từ chối mật khẩu -> đọc lý do
                    let dg = screen_digest(&scr);
                    return fail(&serial, "PASSWORD_REJECTED", &format!("TikTok không nhận mật khẩu: {}", dg), &password);
                }
                let pf = match scr.edit_field(true) {
                    Some(f) => f.clone(),
                    None => continue,
                };
                tap_node(&adb, &serial, &pf);
                sleep_ms(500);
                let mut cmd = String::from("input keyevent 123");
                for _ in 0..40 {
                    cmd.push_str(" 67");
                }
                adb_shell(&adb, &serial, &cmd);
                input_text(&adb, &serial, &password);
                sleep_ms(700);
                slog(&serial, "PASSWORD", "Đã nhập mật khẩu");
                tap_submit(&adb, &serial, &["Next", "Continue", "Sign up"], &scr);
                pwd_done = true;
                wait_leave(&adb, &serial, |s| classify(s) == SignupScreen::CreatePassword, 20);
            }
            SignupScreen::CreateUsername => {
                // Giữ username gợi ý của TikTok (đã hợp lệ/khả dụng): chỉ bấm xác nhận
                if let Some(b) = scr.find_btn(&["Sign up", "Confirm", "Continue", "Next", "Skip"]) {
                    tap_node(&adb, &serial, b);
                } else {
                    tap(&adb, &serial, 360, 1295);
                }
                sleep_ms(2000);
            }
            SignupScreen::Onboarding => {
                if let Some(b) = scr.find_btn(&["Skip", "Not now", "Maybe later", "Later", "Got it", "Confirm", "Select", "Allow"]) {
                    tap_node(&adb, &serial, b);
                } else if scr.has_contains(&["swipe up for more"]) {
                    adb_shell(&adb, &serial, "input swipe 360 1100 360 400 300");
                } else {
                    key(&adb, &serial, 4);
                }
                sleep_ms(1500);
            }
            SignupScreen::Feed => {
                // Đã vào trong app: mở tab Profile và đọc @username thật
                verify_attempts += 1;
                if verify_attempts > 8 {
                    return fail(&serial, "NO_PROFILE", "Vào được feed nhưng không đọc được @username ở tab Profile", &password);
                }
                if let Some(p) = scr.find_btn(&["Profile"]) {
                    tap_node(&adb, &serial, p);
                } else {
                    tap(&adb, &serial, 660, 1360);
                }
                sleep_ms(2500);
                if let Some(ps) = dump_screen(&adb, &serial) {
                    if let Some(u) = ps.own_profile_user() {
                        if !u.is_empty() {
                            return finish_ok(&serial, &spec, &password, email_id, u);
                        }
                        // profile của chính mình nhưng chưa thấy @user: thử lại sau
                        slog(&serial, "VERIFY", "Đã ở profile của mình nhưng chưa đọc được @username, thử lại");
                    }
                }
            }
            SignupScreen::Unknown => {
                unknown += 1;
                let dg = screen_digest(&scr);
                slog(&serial, "UNKNOWN", format!("Màn hình lạ #{}: {}", unknown, dg));
                if unknown >= 8 {
                    return fail(&serial, "UNKNOWN_SCREEN", &format!("Không nhận diện được màn hình: {}", dg), &password);
                }
                if let Some(b) = scr.find_btn(&["Continue", "Next", "OK", "Close"]) {
                    tap_node(&adb, &serial, b);
                } else {
                    sleep_ms(1500);
                }
            }
        }
        sleep_ms(500);
    }
    fail(&serial, "MAX_STEPS", "Hết số bước tối đa mà chưa đăng ký xong", &password)
}

fn finish_ok(serial: &str, spec: &SignupSpec, password: &str, email_id: u64, username: String) -> SignupOutcome {
    slog(serial, "VERIFY", format!("Profile hiển thị @{} -> đăng ký THÀNH CÔNG ✔", username));
    let acc_id = register_on_c69(&username, spec, password, email_id);
    match acc_id {
        Some(id) => slog(serial, "C69", format!("Đã lưu nick @{} lên C69 (account #{})", username, id)),
        None => slog(serial, "C69", "⚠️ Chưa lưu được nick lên C69 — username/mật khẩu vẫn nằm trong log phiên"),
    }
    let msg_c69 = format!("Đã tạo nick TikTok @{} bằng email {} (XML Rust) 🟢", username, spec.email);
    if let Some(id) = acc_id {
        sync_c69_timeline_log(id, &msg_c69, None);
    }
    crate::telegram_notifier::notify_client(spec.client.as_deref().unwrap_or("tony"), "Tạo Nick TikTok Thành Công ✅", &msg_c69);
    su_upd(serial, |s| {
        s.state = "success".into();
        s.username = username.clone();
        s.c69_account_id = acc_id;
        s.message = format!("SUCCESS: @{}", username);
    });
    SignupOutcome { ok: true, code: "SUCCESS".into(), msg: msg_c69, username: Some(username), password: password.into(), c69_account_id: acc_id }
}

fn resolve_email_id_by_address(email: &str) -> Option<u64> {
    let rt = tokio::runtime::Builder::new_current_thread().enable_all().build().ok()?;
    rt.block_on(crate::browser_nurture::find_c69_email_id_by_address(email)).ok().flatten()
}

/// Hòm thư có truy cập được không (kể cả đang trống) — phân biệt "trống" với "lỗi đọc (500/timeout)".
fn mailbox_reachable(email_id: u64) -> bool {
    match c69_block(crate::browser_nurture::read_c69_email_mailbox(email_id)) {
        Some(Ok(v)) => v.get("success").and_then(|s| s.as_bool()).unwrap_or(false),
        _ => false,
    }
}

// ───────────────────────────── Auto-pick email ─────────────────────────────

/// Lấy tối đa `n` email trên C69 chưa gắn TikTok (has_tiktok=false, status=0) và ĐỌC ĐƯỢC hòm thư.
/// Trả về (email_id, email).
pub fn pick_unused_emails(n: usize) -> Vec<(u64, String)> {
    let sess = crate::browser_nurture::load_c69_session();
    let server_url = sess
        .as_ref()
        .map(|s| s.server_url.clone())
        .unwrap_or_else(|| crate::browser_nurture::DEFAULT_C69_API_URL.to_string());
    let token = sess
        .as_ref()
        .and_then(|s| s.token.clone())
        .unwrap_or_else(|| crate::browser_nurture::c69_token().to_string());
    let url = format!(
        "{}/dashboard/api/emails/?has_tiktok=false&status=0&page_size={}",
        server_url,
        (n * 6).clamp(10, 100)
    );
    let rt = match tokio::runtime::Builder::new_current_thread().enable_all().build() {
        Ok(r) => r,
        Err(_) => return vec![],
    };
    let data: Option<serde_json::Value> = rt.block_on(async {
        let c = reqwest::Client::builder().timeout(Duration::from_secs(15)).build().ok()?;
        c.get(&url).header("Authorization", &token).send().await.ok()?.json().await.ok()
    });
    let mut out = Vec::new();
    let arr = data
        .as_ref()
        .and_then(|d| d.get("results").and_then(|r| r.as_array()).or_else(|| d.as_array()))
        .cloned()
        .unwrap_or_default();
    for it in arr {
        if out.len() >= n {
            break;
        }
        let id = match it.get("id").and_then(|v| v.as_u64()) {
            Some(i) => i,
            None => continue,
        };
        let email = it.get("email").and_then(|v| v.as_str()).unwrap_or("").to_string();
        if email.is_empty() || !email.contains('@') {
            continue;
        }
        if check_c69_email_readable(id) {
            out.push((id, email));
        }
    }
    out
}

// ───────────────────────────── Batch ─────────────────────────────

pub fn start_signup(adb: PathBuf, serials: Vec<String>, specs: Vec<SignupSpec>) -> Result<usize, String> {
    if serials.is_empty() {
        return Err("Không có thiết bị Android nào online".into());
    }
    if specs.is_empty() {
        return Err("Không có email nào để đăng ký".into());
    }
    if SU_RUNNING.swap(true, Ordering::SeqCst) {
        return Err("Đang có phiên đăng ký TikTok khác đang chạy".into());
    }
    SU_STOP.store(false, Ordering::SeqCst);
    su_map().write().clear();
    for s in &serials {
        su_upd(s, |st| {
            st.state = "queued".into();
            st.step = "QUEUED".into();
        });
    }
    let total = specs.len();
    let queue = Arc::new(std::sync::Mutex::new(std::collections::VecDeque::from(specs)));
    std::thread::spawn(move || {
        let mut handles = Vec::new();
        for serial in serials {
            let adb = adb.clone();
            let queue = queue.clone();
            handles.push(std::thread::spawn(move || {
                while !SU_STOP.load(Ordering::SeqCst) {
                    let spec = {
                        let mut q = match queue.lock() {
                            Ok(g) => g,
                            Err(p) => p.into_inner(),
                        };
                        match q.pop_front() {
                            Some(s) => s,
                            None => break,
                        }
                    };
                    let out = signup_one(adb.clone(), serial.clone(), spec);
                    info!("[XMLSignup {}] kết quả: ok={} code={} user={:?}", serial, out.ok, out.code, out.username);
                }
                su_upd(&serial, |s| {
                    if s.state == "queued" {
                        s.state = "idle".into();
                    }
                });
            }));
        }
        for h in handles {
            let _ = h.join();
        }
        SU_RUNNING.store(false, Ordering::SeqCst);
    });
    Ok(total)
}

// ───────────────────────────── Tests ─────────────────────────────

#[cfg(test)]
mod tests {
    use super::*;

    fn node(class: &str, text: &str, desc: &str, pw: bool) -> String {
        format!(
            r#"<node class="{}" text="{}" content-desc="{}" package="com.zhiliaoapp.musically" bounds="[10,10][500,100]" clickable="true" password="{}" selected="false"/>"#,
            class, text, desc, pw
        )
    }
    fn screen(nodes: &[String]) -> Screen {
        let xml = format!("<hierarchy>{}</hierarchy>", nodes.join(""));
        Screen::parse(&xml).expect("parse")
    }

    #[test]
    fn birthday_parse() {
        assert_eq!(parse_birthday("October 21, 2001"), Some((10, 21, 2001)));
        assert_eq!(parse_birthday("January 1, 1995"), Some((1, 1, 1995)));
        assert_eq!(parse_birthday("Birthday"), None);
        assert_eq!(parse_birthday(""), None);
    }

    #[test]
    fn password_is_valid_for_tiktok() {
        let mut rng = rand::thread_rng();
        for _ in 0..200 {
            let p = gen_password(&mut rng);
            assert_eq!(p.len(), 12);
            assert!(p.chars().any(|c| c.is_ascii_lowercase()));
            assert!(p.chars().any(|c| c.is_ascii_uppercase()));
            assert!(p.chars().any(|c| c.is_ascii_digit()));
            assert!(p.chars().any(|c| "!@#$%".contains(c)));
            assert!(p.chars().next().unwrap().is_ascii_alphabetic());
        }
    }

    #[test]
    fn birthday_is_adult() {
        let mut rng = rand::thread_rng();
        for _ in 0..200 {
            let (m, d, y) = gen_birthday(&mut rng);
            assert!((1..=12).contains(&m) && (1..=28).contains(&d) && (1992..=2002).contains(&y));
        }
    }

    #[test]
    fn classify_real_screens() {
        // Màn hình thật đã dump trên máy ce0117112dccec3404
        let login_menu = screen(&[
            node("android.widget.TextView", "Log in to TikTok", "", false),
            node("android.widget.Button", "", "Use phone / email / username", false),
        ]);
        assert_eq!(classify(&login_menu), SignupScreen::LoginMenu);

        let signup_menu = screen(&[
            node("android.widget.TextView", "Sign up for TikTok", "", false),
            node("android.widget.Button", "", "Use phone or email", false),
        ]);
        assert_eq!(classify(&signup_menu), SignupScreen::SignUpMenu);

        let bday = screen(&[
            node("android.widget.TextView", "When’s your birthday?", "", false),
            node("android.widget.EditText", "Birthday", "", false),
        ]);
        assert_eq!(classify(&bday), SignupScreen::Birthday);

        let email_form = screen(&[
            node("android.widget.LinearLayout", "", "Phone", false),
            node("android.widget.LinearLayout", "", "Email", false),
            node("android.widget.EditText", "Email address", "", false),
        ]);
        assert_eq!(classify(&email_form), SignupScreen::PhoneEmailForm);

        let rate = screen(&[
            node("android.widget.LinearLayout", "", "Phone", false),
            node("android.widget.LinearLayout", "", "Email", false),
            node("android.widget.EditText", "x@y.com", "", false),
            node("android.widget.TextView", "Maximum number of attempts reached. Try again later.", "", false),
        ]);
        assert_eq!(classify(&rate), SignupScreen::RateLimit);

        let pwd = screen(&[node("android.widget.EditText", "", "", true)]);
        assert_eq!(classify(&pwd), SignupScreen::CreatePassword);

        let guest = screen(&[
            node("android.widget.TextView", "Log into existing account", "", false),
            node("android.widget.Button", "Login", "", false),
        ]);
        assert_eq!(classify(&guest), SignupScreen::ProfileGuest);
    }

    #[test]
    fn classify_feed_and_unknown() {
        let feed = screen(&[
            node("android.widget.TextView", "Home", "", false),
            node("android.widget.TextView", "Inbox", "", false),
            node("android.widget.TextView", "Profile", "", false),
        ]);
        assert_eq!(classify(&feed), SignupScreen::Feed);
        let unk = screen(&[node("android.widget.TextView", "Something new", "", false)]);
        assert_eq!(classify(&unk), SignupScreen::Unknown);
    }
}
