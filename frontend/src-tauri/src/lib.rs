//! Tauri shell for Kazu.
//!
//! Almost all application logic lives in the Python service and the React UI.
//! This layer only: creates the window, starts the Python sidecar, hands the
//! frontend a connection token, and makes sure the sidecar dies with the app.

use std::sync::Mutex;

use tauri::{Manager, RunEvent, State};
use tauri_plugin_shell::process::CommandChild;
use tauri_plugin_shell::ShellExt;

/// Where the sidecar listens. Loopback only, never 0.0.0.0.
const HOST: &str = "127.0.0.1";
const PORT: u16 = 8765;

/// Connection details handed to the frontend via `backend_info`.
#[derive(Clone, serde::Serialize)]
struct BackendInfo {
    base_url: String,
    token: String,
    /// False when we attached to an already-running service (dev, or a future
    /// user-level systemd service) instead of spawning one ourselves.
    managed: bool,
}

/// Holds the child handle so we can kill it on exit.
struct Sidecar(Mutex<Option<CommandChild>>);

/// Random hex token, so other local processes cannot call the API.
fn generate_token() -> String {
    use std::time::{SystemTime, UNIX_EPOCH};
    let nanos = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_nanos())
        .unwrap_or(0);
    let pid = std::process::id() as u128;
    format!("{:032x}{:016x}", nanos.wrapping_mul(0x9E37_79B9_7F4A_7C15), pid)
}

#[tauri::command]
fn backend_info(info: State<'_, BackendInfo>) -> BackendInfo {
    info.inner().clone()
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // In dev we run the Python service ourselves (`npm run dev:api`) so it can
    // hot-reload independently of the Rust build; the shell then just connects.
    let managed = !cfg!(debug_assertions);
    let token = if managed {
        generate_token()
    } else {
        std::env::var("KAZU_AUTH_TOKEN").unwrap_or_default()
    };

    let info = BackendInfo {
        base_url: format!("http://{HOST}:{PORT}"),
        token: token.clone(),
        managed,
    };

    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(info)
        .manage(Sidecar(Mutex::new(None)))
        .setup(move |app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            if managed {
                let (mut rx, child) = app
                    .shell()
                    .sidecar("kazu-service")?
                    .env("KAZU_HOST", HOST)
                    .env("KAZU_PORT", PORT.to_string())
                    .env("KAZU_AUTH_TOKEN", token.clone())
                    .spawn()?;

                app.state::<Sidecar>().0.lock().unwrap().replace(child);

                // Drain the sidecar's output into the app log; without a reader
                // the pipe fills and the Python process blocks on write.
                tauri::async_runtime::spawn(async move {
                    use tauri_plugin_shell::process::CommandEvent;
                    while let Some(event) = rx.recv().await {
                        match event {
                            CommandEvent::Stdout(line) | CommandEvent::Stderr(line) => {
                                log::info!("[service] {}", String::from_utf8_lossy(&line).trim());
                            }
                            CommandEvent::Terminated(payload) => {
                                log::warn!("[service] exited: {:?}", payload.code);
                                break;
                            }
                            _ => {}
                        }
                    }
                });
            }

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![backend_info])
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app, event| {
            // The sidecar's lifetime is tied to the window: no orphaned Python
            // process left listening after the app closes.
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                if let Some(child) = app.state::<Sidecar>().0.lock().unwrap().take() {
                    let _ = child.kill();
                }
            }
        });
}
