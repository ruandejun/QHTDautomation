//! Chèn thao tác chạm/vuốt/phím độ trễ thấp qua `scrcpy-server` (chế độ control-only).
//!
//! `adb shell input tap` tốn ~450ms/lệnh vì mỗi lần phải khởi động lại JVM trên máy.
//! Ở đây mỗi máy có 1 worker giữ sẵn 1 kết nối control tới scrcpy-server (bật 1 lần ~0.5s),
//! sau đó mỗi sự kiện chạm chỉ là 32 byte qua socket (< 10ms).
//! Nếu không bật được scrcpy-server thì tự động rơi về `adb shell input` như cũ.

use std::collections::HashMap;
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpStream};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::{mpsc, Mutex};
use std::time::{Duration, Instant};

const SERVER_VERSION: &str = "3.1";
const REMOTE_JAR: &str = "/data/local/tmp/scrcpy-server.jar";
const POINTER_ID_FINGER: i64 = -2; // SC_POINTER_ID_GENERIC_FINGER

#[derive(Clone, Debug)]
pub enum Cmd {
    /// Bật sẵn kết nối (gọi khi chuột rê vào màn hình máy).
    Warm,
    /// Toạ độ chuẩn hoá 0..1 theo màn hình.
    Down(f32, f32),
    Move(f32, f32),
    Up(f32, f32),
    Tap(f32, f32),
    Key(u32),
    /// (x1, y1, x2, y2, thời_gian_ms)
    Swipe(f32, f32, f32, f32, u32),
}

pub struct FastTouch {
    adb: PathBuf,
    jar: Option<PathBuf>,
    workers: Mutex<HashMap<String, mpsc::Sender<Cmd>>>,
}

impl FastTouch {
    pub fn new(adb: PathBuf) -> Self {
        let jar = [
            "bin/scrcpy-win64-v3.1/scrcpy-server",
            "../bin/scrcpy-win64-v3.1/scrcpy-server",
            "scrcpy-server",
            r"D:\Workspace\Python\QHTDautomation\bin\scrcpy-win64-v3.1\scrcpy-server",
        ]
        .iter()
        .map(PathBuf::from)
        .find(|p| p.exists());
        Self { adb, jar, workers: Mutex::new(HashMap::new()) }
    }

    pub fn send(&self, serial: &str, cmd: Cmd) {
        let mut map = self.workers.lock().unwrap_or_else(|e| e.into_inner());
        if let Some(tx) = map.get(serial) {
            if tx.send(cmd.clone()).is_ok() {
                return;
            }
        }
        let (tx, rx) = mpsc::channel();
        let mut w = Worker::new(serial.to_string(), self.adb.clone(), self.jar.clone());
        let _ = tx.send(cmd);
        std::thread::spawn(move || w.run(rx));
        map.insert(serial.to_string(), tx);
    }
}

struct Worker {
    serial: String,
    adb: PathBuf,
    jar: Option<PathBuf>,
    w: u32,
    h: u32,
    conn: Option<TcpStream>,
    server: Option<Child>,
    port: Option<u16>,
    retry_at: Option<Instant>,
    down: Option<(f32, f32, Instant)>,
    last: (f32, f32),
}

fn adb_cmd(adb: &Path) -> Command {
    let mut c = Command::new(adb);
    #[cfg(target_os = "windows")]
    {
        use std::os::windows::process::CommandExt;
        c.creation_flags(0x08000000);
    }
    c
}

impl Worker {
    fn new(serial: String, adb: PathBuf, jar: Option<PathBuf>) -> Self {
        Self {
            serial,
            adb,
            jar,
            w: 720,
            h: 1480,
            conn: None,
            server: None,
            port: None,
            retry_at: None,
            down: None,
            last: (0.5, 0.5),
        }
    }

    fn run(&mut self, rx: mpsc::Receiver<Cmd>) {
        while let Ok(first) = rx.recv() {
            // Gom các lệnh đang chờ; chuỗi Move liên tiếp chỉ giữ lệnh cuối (chống trễ tích luỹ).
            let mut batch = vec![first];
            while let Ok(c) = rx.try_recv() {
                batch.push(c);
            }
            let mut collapsed: Vec<Cmd> = Vec::with_capacity(batch.len());
            for c in batch {
                if let (Cmd::Move(..), Some(Cmd::Move(..))) = (&c, collapsed.last()) {
                    collapsed.pop();
                }
                collapsed.push(c);
            }
            for c in collapsed {
                self.handle(c);
            }
        }
    }

    fn handle(&mut self, cmd: Cmd) {
        if self.conn.is_none() && self.retry_at.map_or(true, |t| Instant::now() >= t) {
            self.connect();
        }
        if matches!(cmd, Cmd::Warm) {
            return;
        }
        let fast = self.conn.is_some();
        match cmd {
            Cmd::Warm => {}
            Cmd::Down(x, y) => {
                self.last = (x, y);
                self.down = Some((x, y, Instant::now()));
                if fast {
                    self.touch(0, x, y, 0xFFFF);
                }
            }
            Cmd::Move(x, y) => {
                self.last = (x, y);
                if fast {
                    self.touch(2, x, y, 0xFFFF);
                }
            }
            Cmd::Up(x, y) => {
                if fast {
                    self.touch(1, x, y, 0);
                } else if let Some((sx, sy, t0)) = self.down {
                    let ms = (t0.elapsed().as_millis() as u32).clamp(100, 800);
                    self.fallback_swipe(sx, sy, x, y, ms);
                }
                self.down = None;
            }
            Cmd::Tap(x, y) => {
                if fast {
                    self.touch(0, x, y, 0xFFFF);
                    std::thread::sleep(Duration::from_millis(35));
                    self.touch(1, x, y, 0);
                } else {
                    let (px, py) = self.px(x, y);
                    self.shell(&["input", "tap", &px.to_string(), &py.to_string()]);
                }
            }
            Cmd::Key(code) => {
                if fast {
                    self.key(0, code);
                    self.key(1, code);
                } else {
                    self.shell(&["input", "keyevent", &code.to_string()]);
                }
            }
            Cmd::Swipe(x1, y1, x2, y2, dur) => {
                if fast {
                    let steps = (dur / 16).clamp(4, 40);
                    self.touch(0, x1, y1, 0xFFFF);
                    for i in 1..=steps {
                        std::thread::sleep(Duration::from_millis((dur / steps).max(8) as u64));
                        let t = i as f32 / steps as f32;
                        self.touch(2, x1 + (x2 - x1) * t, y1 + (y2 - y1) * t, 0xFFFF);
                    }
                    self.touch(1, x2, y2, 0);
                } else {
                    self.fallback_swipe(x1, y1, x2, y2, dur);
                }
            }
        }
    }

    fn px(&self, fx: f32, fy: f32) -> (u32, u32) {
        (
            (fx.clamp(0.0, 1.0) * self.w as f32).min(self.w as f32 - 1.0) as u32,
            (fy.clamp(0.0, 1.0) * self.h as f32).min(self.h as f32 - 1.0) as u32,
        )
    }

    fn shell(&self, args: &[&str]) {
        let mut c = adb_cmd(&self.adb);
        c.args(["-s", &self.serial, "shell"]).args(args);
        let _ = c.stdout(Stdio::null()).stderr(Stdio::null()).status();
    }

    fn fallback_swipe(&self, x1: f32, y1: f32, x2: f32, y2: f32, dur: u32) {
        let (a, b) = self.px(x1, y1);
        let (c, d) = self.px(x2, y2);
        let moved = (a as i64 - c as i64).abs() + (b as i64 - d as i64).abs();
        if moved < 12 {
            self.shell(&["input", "tap", &a.to_string(), &b.to_string()]);
        } else {
            self.shell(&[
                "input", "swipe", &a.to_string(), &b.to_string(), &c.to_string(), &d.to_string(), &dur.to_string(),
            ]);
        }
    }

    /// INJECT_TOUCH_EVENT (type 2) của scrcpy 3.1: 32 byte, big-endian.
    fn touch(&mut self, action: u8, fx: f32, fy: f32, pressure: u16) {
        let (px, py) = self.px(fx, fy);
        let mut m = [0u8; 32];
        m[0] = 2;
        m[1] = action;
        m[2..10].copy_from_slice(&POINTER_ID_FINGER.to_be_bytes());
        m[10..14].copy_from_slice(&(px as i32).to_be_bytes());
        m[14..18].copy_from_slice(&(py as i32).to_be_bytes());
        m[18..20].copy_from_slice(&(self.w as u16).to_be_bytes());
        m[20..22].copy_from_slice(&(self.h as u16).to_be_bytes());
        m[22..24].copy_from_slice(&pressure.to_be_bytes());
        // action_button (4) + buttons (4) = 0 cho ngón tay
        self.write(&m);
    }

    /// INJECT_KEYCODE (type 0): 14 byte.
    fn key(&mut self, action: u8, code: u32) {
        let mut m = [0u8; 14];
        m[0] = 0;
        m[1] = action;
        m[2..6].copy_from_slice(&(code as i32).to_be_bytes());
        self.write(&m);
    }

    fn write(&mut self, data: &[u8]) {
        let ok = match self.conn.as_mut() {
            Some(s) => s.write_all(data).is_ok(),
            None => false,
        };
        if !ok {
            // Mất kết nối: thử lại sau 2s, trong lúc đó dùng đường `input` dự phòng.
            self.drop_conn();
            self.retry_at = Some(Instant::now() + Duration::from_secs(2));
        }
    }

    fn drop_conn(&mut self) {
        self.conn = None;
        if let Some(mut s) = self.server.take() {
            let _ = s.kill();
        }
        if let Some(p) = self.port.take() {
            let _ = adb_cmd(&self.adb)
                .args(["-s", &self.serial, "forward", "--remove", &format!("tcp:{}", p)])
                .stdout(Stdio::null())
                .stderr(Stdio::null())
                .status();
        }
    }

    fn query_size(&mut self) {
        let out = adb_cmd(&self.adb).args(["-s", &self.serial, "shell", "wm", "size"]).output();
        if let Ok(o) = out {
            let text = String::from_utf8_lossy(&o.stdout).to_string();
            let (mut phys, mut over) = (None, None);
            for line in text.lines() {
                if let Some((k, v)) = line.split_once(':') {
                    if let Some((a, b)) = v.trim().split_once('x') {
                        if let (Ok(a), Ok(b)) = (a.trim().parse::<u32>(), b.trim().parse::<u32>()) {
                            if k.to_lowercase().contains("override") {
                                over = Some((a, b));
                            } else {
                                phys = Some((a, b));
                            }
                        }
                    }
                }
            }
            if let Some((a, b)) = over.or(phys) {
                self.w = a;
                self.h = b;
            }
        }
    }

    fn connect(&mut self) {
        let jar = match &self.jar {
            Some(j) => j.clone(),
            None => {
                self.retry_at = Some(Instant::now() + Duration::from_secs(3600));
                return;
            }
        };
        self.drop_conn();
        self.query_size();

        let pushed = adb_cmd(&self.adb)
            .args(["-s", &self.serial, "push"])
            .arg(&jar)
            .arg(REMOTE_JAR)
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
        if !pushed {
            self.retry_at = Some(Instant::now() + Duration::from_secs(20));
            return;
        }

        let scid: u32 = rand::random::<u32>() & 0x7fff_ffff | 1;
        let server = adb_cmd(&self.adb)
            .args(["-s", &self.serial, "shell"])
            .arg(format!("CLASSPATH={}", REMOTE_JAR))
            .args([
                "app_process",
                "/",
                "com.genymobile.scrcpy.Server",
                SERVER_VERSION,
                &format!("scid={:x}", scid),
                "log_level=error",
                "tunnel_forward=true",
                "video=false",
                "audio=false",
                "control=true",
                "cleanup=false",
                "clipboard_autosync=false",
            ])
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn();
        self.server = server.ok();
        if self.server.is_none() {
            self.retry_at = Some(Instant::now() + Duration::from_secs(20));
            return;
        }

        let fwd = adb_cmd(&self.adb)
            .args(["-s", &self.serial, "forward", "tcp:0", &format!("localabstract:scrcpy_{:08x}", scid)])
            .output();
        let port: Option<u16> = fwd
            .ok()
            .and_then(|o| String::from_utf8_lossy(&o.stdout).trim().parse().ok());
        let port = match port {
            Some(p) => p,
            None => {
                self.drop_conn();
                self.retry_at = Some(Instant::now() + Duration::from_secs(20));
                return;
            }
        };
        self.port = Some(port);

        let addr = SocketAddr::from(([127, 0, 0, 1], port));
        for _ in 0..40 {
            if let Ok(mut s) = TcpStream::connect_timeout(&addr, Duration::from_millis(500)) {
                let _ = s.set_read_timeout(Some(Duration::from_millis(500)));
                let mut dummy = [0u8; 1];
                if let Ok(1) = s.read(&mut dummy) {
                    let _ = s.set_read_timeout(None);
                    let _ = s.set_nodelay(true);
                    self.conn = Some(s);
                    self.retry_at = None;
                    return;
                }
            }
            std::thread::sleep(Duration::from_millis(250));
        }
        self.drop_conn();
        self.retry_at = Some(Instant::now() + Duration::from_secs(30));
    }
}
