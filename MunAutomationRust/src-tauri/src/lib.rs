pub mod commands;

use commands::{scan_adb_devices, start_nurture, stop_nurture, AppState};
use std::sync::atomic::AtomicBool;
use std::sync::Arc;

pub fn run() {
    tauri::Builder::default()
        .manage(AppState {
            is_running: Arc::new(AtomicBool::new(false)),
        })
        .invoke_handler(tauri::generate_handler![
            scan_adb_devices,
            start_nurture,
            stop_nurture
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
