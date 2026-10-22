//! Bộ giải Captcha Puzzle trượt (TikTok Slider / Puzzle Piece Captcha) thuần Rust 100%.
//!
//! Tự động nhận diện:
//! 1. Phát hiện dialog captcha "Verify to continue" / "Drag the puzzle piece into place".
//! 2. Xác định bounds ảnh nền, mảnh ghép nguồn và thanh trượt từ XML hoặc tỉ lệ chuẩn.
//! 3. Chụp ảnh màn hình trực tiếp bằng `adb exec-out screencap -p` và decode qua crate `image`.
//! 4. Phân tích Luminance contrast drop để tìm chính xác tọa độ lỗ khuyết (shadow target).
//! 5. Thực hiện thao tác kéo trượt mô phỏng hành vi con người (human-like swipe with duration & jitter).
//! 6. Xác nhận giải thành công (dialog biến mất); nếu chưa được, bấm nút Refresh và thử lại (tối đa 3 lần).

use std::path::Path;
use std::process::Command;
use std::time::Duration;
use rand::Rng;
use tracing::{info, warn};

/// Kiểm tra chuỗi XML có chứa dấu hiệu Captcha TikTok không.
pub fn detect_captcha_in_xml(xml: &str) -> bool {
    let lower = xml.to_lowercase();
    let keywords = [
        "verify to continue",
        "drag the puzzle piece into place",
        "drag the slider",
        "slide to verify",
        "captcha-verify-image",
        "secsdk-captcha-drag-wrapper",
        "verify captcha",
        "select 2 objects",
    ];
    keywords.iter().any(|k| lower.contains(k))
}

/// Chụp màn hình dạng PNG raw bytes trực tiếp qua ADB exec-out và load vào DynamicImage.
pub fn capture_screen_png(adb: &Path, serial: &str) -> Result<image::DynamicImage, String> {
    let mut cmd = Command::new(adb);
    cmd.args(["-s", serial, "exec-out", "screencap", "-p"]);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    let out = cmd.output().map_err(|e| format!("screencap command error: {}", e))?;
    if !out.status.success() || out.stdout.is_empty() {
        return Err("screencap output rỗng hoặc trả về lỗi".into());
    }
    image::load_from_memory(&out.stdout).map_err(|e| format!("decode screencap png thất bại: {}", e))
}

/// Thông tin bounds tọa độ của các thành phần trong Captcha Dialog.
#[derive(Debug, Clone)]
pub struct CaptchaBounds {
    pub bg_x1: u32,
    pub bg_x2: u32,
    pub piece_x1: u32,
    pub piece_x2: u32,
    pub piece_y1: u32,
    pub piece_y2: u32,
    pub slider_start_x: u32,
    pub slider_start_y: u32,
    pub refresh_btn_x: u32,
    pub refresh_btn_y: u32,
}

impl CaptchaBounds {
    /// Tính bounds theo tỉ lệ chuẩn trên màn hình (chuẩn gốc thiết kế TikTok WebView trên màn 720x1480).
    pub fn from_screen_size(w: u32, h: u32) -> Self {
        Self {
            bg_x1: (w as f32 * 96.0 / 720.0).round() as u32,
            bg_x2: (w as f32 * 625.0 / 720.0).round() as u32,
            piece_x1: (w as f32 * 110.0 / 720.0).round() as u32,
            piece_x2: (w as f32 * 217.0 / 720.0).round() as u32,
            piece_y1: (h as f32 * 646.0 / 1480.0).round() as u32,
            piece_y2: (h as f32 * 752.0 / 1480.0).round() as u32,
            slider_start_x: (w as f32 * 150.0 / 720.0).round() as u32,
            slider_start_y: (h as f32 * 894.0 / 1480.0).round() as u32,
            refresh_btn_x: (w as f32 * 118.0 / 720.0).round() as u32,
            refresh_btn_y: (h as f32 * 967.0 / 1480.0).round() as u32,
        }
    }
}

/// Phân tích ảnh và tìm khoảng cách kéo (offset_x tính bằng pixel) từ vị trí mảnh ghép nguồn tới lỗ khuyết đích.
pub fn find_puzzle_offset(img: &image::DynamicImage, bounds: &CaptchaBounds) -> Result<u32, String> {
    let (img_w, img_h) = (img.width(), img.height());
    if img_w == 0 || img_h == 0 {
        return Err("Ảnh màn hình rỗng".into());
    }

    // Quét vùng Y nằm trọn trong chiều cao của mảnh ghép (bỏ viền trên dưới 15px)
    let y_min = bounds.piece_y1.saturating_add(15).min(img_h - 1);
    let y_max = bounds.piece_y2.saturating_sub(15).min(img_h - 1);
    if y_min >= y_max {
        return Err(format!("Vùng quét Y không hợp lệ: y_min={} >= y_max={}", y_min, y_max));
    }

    // Quét các cột X từ sau mép phải mảnh ghép tới trước mép phải ảnh nền
    let x_min = bounds.piece_x2.saturating_add(15).min(img_w - 1);
    let x_max = bounds.bg_x2.saturating_sub(25).min(img_w - 1);
    if x_min >= x_max {
        return Err(format!("Vùng quét X không hợp lệ: x_min={} >= x_max={}", x_min, x_max));
    }

    let rgb_img = img.to_rgb8();

    // 1. Tính Luminance trung bình của từng cột X trong vùng quét
    let mut lum_profile: Vec<(u32, f32)> = Vec::with_capacity((x_max - x_min + 1) as usize);
    for x in x_min..=x_max {
        let mut sum_lum = 0.0f32;
        let mut count = 0u32;
        for y in (y_min..=y_max).step_by(2) {
            let pixel = rgb_img.get_pixel(x, y);
            // Luminance chuẩn Rec. 601
            let lum = 0.299 * (pixel[0] as f32) + 0.587 * (pixel[1] as f32) + 0.114 * (pixel[2] as f32);
            sum_lum += lum;
            count += 1;
        }
        let avg_lum = if count > 0 { sum_lum / (count as f32) } else { 255.0 };
        lum_profile.push((x, avg_lum));
    }

    if lum_profile.len() < 20 {
        return Err("Vùng quét Luminance quá hẹp".into());
    }

    // 2. Tìm sliding window có độ sáng trung bình thấp nhất (vùng bóng tối của lỗ khuyết)
    // Chiều rộng lỗ khuyết khoảng 60% chiều rộng của mảnh ghép
    let piece_width = bounds.piece_x2.saturating_sub(bounds.piece_x1).max(50);
    let window_size = ((piece_width as usize) * 6 / 10).clamp(25, 60);

    let mut best_center_x = x_min;
    let mut min_window_lum = f32::MAX;

    if lum_profile.len() > window_size {
        for i in 0..=(lum_profile.len() - window_size) {
            let window_sum: f32 = lum_profile[i..i + window_size].iter().map(|(_, l)| *l).sum();
            let avg = window_sum / (window_size as f32);
            if avg < min_window_lum {
                min_window_lum = avg;
                let center_idx = i + window_size / 2;
                best_center_x = lum_profile[center_idx].0;
            }
        }
    } else {
        // Fallback tìm cột tối nhất
        if let Some((x, _)) = lum_profile.iter().min_by(|a, b| a.1.partial_cmp(&b.1).unwrap_or(std::cmp::Ordering::Equal)) {
            best_center_x = *x;
        }
    }

    let piece_center_x = (bounds.piece_x1 + bounds.piece_x2) / 2;
    if best_center_x <= piece_center_x {
        return Err(format!("Tọa độ đích {} nhỏ hơn hoặc bằng tâm mảnh ghép {}", best_center_x, piece_center_x));
    }

    let offset_x = best_center_x - piece_center_x;
    info!(
        "[Captcha] Phân tích hoàn tất: Tâm mảnh ghép={}, Tâm lỗ khuyết={}, Offset kéo={}px, Lum cực tiểu={:.1}",
        piece_center_x, best_center_x, offset_x, min_window_lum
    );

    Ok(offset_x)
}

/// Thực hiện thao tác vuốt thanh trượt mô phỏng người thật qua lệnh ADB shell input.
pub fn execute_human_drag(adb: &Path, serial: &str, bounds: &CaptchaBounds, offset_x: u32) {
    let mut rng = rand::thread_rng();

    let jitter_x = rng.gen_range(-1..=1);
    let jitter_y = rng.gen_range(-1..=1);
    let start_x = (bounds.slider_start_x as i32 + jitter_x).max(10);
    let start_y = (bounds.slider_start_y as i32 + jitter_y).max(10);

    let end_x = start_x + (offset_x as i32);
    let end_y = start_y + rng.gen_range(-2..=2);

    // Thời gian vuốt ngẫu nhiên giữa 750ms và 950ms để giống thao tác kéo tay người
    let duration = rng.gen_range(760..=940);

    info!(
        "[Captcha {}] Kéo slider từ ({}, {}) -> ({}, {}), offset={}px, dur={}ms",
        serial, start_x, start_y, end_x, end_y, offset_x, duration
    );

    let mut cmd = Command::new(adb);
    cmd.args(["-s", serial, "shell", "input", "swipe", &start_x.to_string(), &start_y.to_string(), &end_x.to_string(), &end_y.to_string(), &duration.to_string()]);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    let _ = cmd.output();
}

/// Bấm nút Refresh trên giao diện Captcha Dialog để đổi ảnh mới khi kéo trượt không khớp.
pub fn tap_refresh(adb: &Path, serial: &str, bounds: &CaptchaBounds) {
    let mut rng = rand::thread_rng();
    let rx = bounds.refresh_btn_x as i32 + rng.gen_range(-2..=2);
    let ry = bounds.refresh_btn_y as i32 + rng.gen_range(-2..=2);
    info!("[Captcha {}] Bấm nút Refresh tại ({}, {})", serial, rx, ry);
    let mut cmd = Command::new(adb);
    cmd.args(["-s", serial, "shell", "input", "tap", &rx.to_string(), &ry.to_string()]);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }
    let _ = cmd.output();
}

/// Dump nhanh XML của màn hình thiết bị hiện tại qua ADB.
pub fn dump_screen_xml(adb: &Path, serial: &str) -> String {
    let mut dump_cmd = Command::new(adb);
    dump_cmd.args(["-s", serial, "exec-out", "uiautomator", "dump", "/sdcard/window_dump.xml"]);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        dump_cmd.creation_flags(0x08000000);
    }
    let _ = dump_cmd.output();

    let mut cat_cmd = Command::new(adb);
    cat_cmd.args(["-s", serial, "shell", "cat", "/sdcard/window_dump.xml"]);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        cat_cmd.creation_flags(0x08000000);
    }
    cat_cmd.output().ok().map(|o| String::from_utf8_lossy(&o.stdout).to_string()).unwrap_or_default()
}

/// Hàm chính giải Captcha Puzzle nếu xuất hiện trên màn hình thiết bị.
///
/// Trả về:
/// - `Ok(true)`: Đã phát hiện và giải thành công (hoặc màn hình không còn captcha).
/// - `Ok(false)`: Không có captcha nào trên màn hình hiện tại.
/// - `Err(msg)`: Có captcha nhưng giải thất bại sau max_attempts lần thử.
pub async fn solve_if_present(adb: &Path, serial: &str, screen_w: u32, screen_h: u32) -> Result<bool, String> {
    let initial_xml = dump_screen_xml(adb, serial);
    if !detect_captcha_in_xml(&initial_xml) {
        return Ok(false);
    }

    info!("[Captcha {}] Phát hiện Captcha 'Verify to continue / Slider Puzzle' trên màn hình! Bắt đầu giải...", serial);
    let bounds = CaptchaBounds::from_screen_size(screen_w, screen_h);
    let max_attempts = 3u32;

    for attempt in 1..=max_attempts {
        info!("[Captcha {}] Lần thử giải thứ {}/{}...", serial, attempt, max_attempts);

        // 1. Chụp ảnh màn hình
        let img = match capture_screen_png(adb, serial) {
            Ok(im) => im,
            Err(e) => {
                warn!("[Captcha {}] Lỗi chụp màn hình: {}. Thử lại...", serial, e);
                tokio::time::sleep(Duration::from_millis(1500)).await;
                continue;
            }
        };

        // 2. Tìm khoảng cách kéo
        let offset_x = match find_puzzle_offset(&img, &bounds) {
            Ok(off) => off,
            Err(e) => {
                warn!("[Captcha {}] Không xác định được lỗ khuyết: {}. Bấm refresh...", serial, e);
                tap_refresh(adb, serial, &bounds);
                tokio::time::sleep(Duration::from_millis(2500)).await;
                continue;
            }
        };

        // 3. Thực hiện kéo thanh trượt
        execute_human_drag(adb, serial, &bounds, offset_x);

        // 4. Chờ TikTok SecSDK xác minh và cập nhật DOM
        tokio::time::sleep(Duration::from_millis(2200)).await;

        // 5. Kiểm tra lại xem captcha đã biến mất chưa
        let check_xml = dump_screen_xml(adb, serial);
        if !detect_captcha_in_xml(&check_xml) {
            info!("[Captcha {}] Giải Captcha Puzzle THÀNH CÔNG ở lần thử thứ {}! 🎉", serial, attempt);
            return Ok(true);
        }

        warn!("[Captcha {}] Chưa khớp ở lần thử {} (captcha vẫn còn). Bấm Refresh để lấy ảnh mới...", serial, attempt);
        tap_refresh(adb, serial, &bounds);
        tokio::time::sleep(Duration::from_millis(2500)).await;
    }

    Err(format!("[Captcha {}] Không thể tự động giải Captcha sau {} lần thử!", serial, max_attempts))
}

/// Bản đồng bộ của solve_if_present (dùng std::thread::sleep), phù hợp gọi từ các worker luồng sync như xml_login.
pub fn solve_if_present_sync(adb: &Path, serial: &str, screen_w: u32, screen_h: u32) -> Result<bool, String> {
    let initial_xml = dump_screen_xml(adb, serial);
    if !detect_captcha_in_xml(&initial_xml) {
        return Ok(false);
    }

    info!("[Captcha {}] Phát hiện Captcha 'Verify to continue / Slider Puzzle' trên màn hình! Bắt đầu giải (Sync)...", serial);
    let bounds = CaptchaBounds::from_screen_size(screen_w, screen_h);
    let max_attempts = 3u32;

    for attempt in 1..=max_attempts {
        info!("[Captcha {}] (Sync) Lần thử giải thứ {}/{}...", serial, attempt, max_attempts);

        let img = match capture_screen_png(adb, serial) {
            Ok(im) => im,
            Err(e) => {
                warn!("[Captcha {}] Lỗi chụp màn hình: {}. Thử lại...", serial, e);
                std::thread::sleep(Duration::from_millis(1500));
                continue;
            }
        };

        let offset_x = match find_puzzle_offset(&img, &bounds) {
            Ok(off) => off,
            Err(e) => {
                warn!("[Captcha {}] Không xác định được lỗ khuyết: {}. Bấm refresh...", serial, e);
                tap_refresh(adb, serial, &bounds);
                std::thread::sleep(Duration::from_millis(2500));
                continue;
            }
        };

        execute_human_drag(adb, serial, &bounds, offset_x);
        std::thread::sleep(Duration::from_millis(2200));

        let check_xml = dump_screen_xml(adb, serial);
        if !detect_captcha_in_xml(&check_xml) {
            info!("[Captcha {}] (Sync) Giải Captcha Puzzle THÀNH CÔNG ở lần thử thứ {}! 🎉", serial, attempt);
            return Ok(true);
        }

        warn!("[Captcha {}] Chưa khớp ở lần thử {} (captcha vẫn còn). Bấm Refresh để lấy ảnh mới...", serial, attempt);
        tap_refresh(adb, serial, &bounds);
        std::thread::sleep(Duration::from_millis(2500));
    }

    Err(format!("[Captcha {}] Không thể tự động giải Captcha sau {} lần thử!", serial, max_attempts))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_puzzle_offset_on_fixture() {
        let fixture_path = Path::new("tests/fixtures/captcha_sample1.png");
        if !fixture_path.exists() {
            println!("Bỏ qua test vì chưa có file fixture {}", fixture_path.display());
            return;
        }
        let img = image::open(fixture_path).expect("Không mở được ảnh fixture");
        let bounds = CaptchaBounds::from_screen_size(img.width(), img.height());
        let offset = find_puzzle_offset(&img, &bounds).expect("Phải tính được offset");
        println!("Test Fixture Offset tính được: {}px", offset);
        // Với ảnh s3101.png, lỗ khuyết ở tâm ~442, mảnh ghép ở tâm ~163 -> offset ~279px (±15px)
        assert!(offset >= 250 && offset <= 310, "Offset {} phải nằm trong khoảng 250..310px", offset);
    }
}
