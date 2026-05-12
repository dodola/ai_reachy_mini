use std::path::{Path, PathBuf};

use tauri::{AppHandle, State};

use crate::daemon::DaemonState;
use crate::paths::get_data_dir;

/// Remove a directory, using the extended-length path prefix on Windows
/// to handle paths longer than 260 characters (common in Python venvs).
fn remove_dir_all_long_path(path: &Path) -> std::io::Result<()> {
    let path = long_path(path);
    std::fs::remove_dir_all(&path)
}

#[cfg(target_os = "windows")]
fn long_path(path: &Path) -> PathBuf {
    // Canonicalize resolves to \\?\C:\... which bypasses MAX_PATH
    path.canonicalize().unwrap_or_else(|_| path.to_path_buf())
}

#[cfg(not(target_os = "windows"))]
fn long_path(path: &Path) -> PathBuf {
    path.to_path_buf()
}

/// Reset the apps virtual environment.
/// Stops the daemon, deletes apps_venv. Next app install will recreate it.
#[tauri::command]
pub async fn reset_apps_venv(
    app_handle: AppHandle,
    state: State<'_, DaemonState>,
) -> Result<String, String> {
    log::info!("[reset] Resetting apps_venv...");

    let _ = crate::stop_daemon(app_handle, state);
    tokio::time::sleep(tokio::time::Duration::from_millis(500)).await;

    let data_dir = get_data_dir()?;
    let apps_venv = data_dir.join("apps_venv");
    if apps_venv.exists() {
        remove_dir_all_long_path(&apps_venv)
            .map_err(|e| format!("Failed to delete apps_venv: {}", e))?;
        log::info!("[reset] Deleted apps_venv at {}", apps_venv.display());
    } else {
        log::info!("[reset] apps_venv not found, nothing to delete");
    }

    Ok("Apps environment reset successfully".to_string())
}

/// Reset the entire Python environment.
/// Stops the daemon, deletes the full data directory (uv, cpython, .venv, apps_venv).
/// Next daemon start will trigger a full bootstrap.
#[tauri::command]
pub async fn reset_python_env(
    app_handle: AppHandle,
    state: State<'_, DaemonState>,
) -> Result<String, String> {
    log::info!("[reset] Resetting entire Python environment...");

    let _ = crate::stop_daemon(app_handle, state);
    tokio::time::sleep(tokio::time::Duration::from_millis(1000)).await;

    let data_dir = get_data_dir()?;
    if data_dir.exists() {
        remove_dir_all_long_path(&data_dir)
            .map_err(|e| format!("Failed to delete data directory: {}", e))?;
        log::info!("[reset] Deleted data directory at {}", data_dir.display());
    } else {
        log::info!("[reset] Data directory not found, nothing to delete");
    }

    Ok("Python environment reset successfully".to_string())
}
