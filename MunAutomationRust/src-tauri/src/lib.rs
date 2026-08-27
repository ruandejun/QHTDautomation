pub mod android_nurture;
pub mod anti_browser;
pub mod c69_router;
pub mod commands;
pub mod network_auditor;

use commands::{list_network_interfaces, scan_adb_devices, start_nurture, stop_nurture, AppState};
use std::sync::atomic::AtomicBool;
use std::sync::Arc;

pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .manage(AppState {
            is_running: Arc::new(AtomicBool::new(false)),
        })
        .invoke_handler(tauri::generate_handler![
            scan_adb_devices,
            list_network_interfaces,
            start_nurture,
            stop_nurture
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
