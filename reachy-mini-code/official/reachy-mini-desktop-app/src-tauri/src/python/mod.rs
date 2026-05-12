// Helper to build daemon arguments
// IMPORTANT: Use .venv/bin/python3 directly instead of "uv run python" to ensure
// we use the venv Python with all installed packages, not the cpython bundle
#[allow(unused_variables)]
pub fn build_daemon_args(
    app_handle: &tauri::AppHandle,
    sim_mode: bool,
    preload_datasets: bool,
) -> Result<Vec<String>, String> {
    // Use Python from .venv directly (not via uv run)
    // This ensures we use the venv with all installed packages
    #[cfg(target_os = "windows")]
    let python_cmd = ".venv\\Scripts\\python.exe";
    #[cfg(not(target_os = "windows"))]
    let python_cmd = ".venv/bin/python3";

    let mut args = vec![python_cmd.to_string()];

    // On Windows, use avast_ssl_fix wrapper to prevent Avast antivirus SSL injection issues
    // Avast injects SSLKEYLOGFILE pointing to aswMonFltProxy which causes PermissionError
    // This is a Windows-specific issue (Avast is primarily a Windows antivirus)
    #[cfg(target_os = "windows")]
    {
        // In dev mode, the script is in the project source tree
        // In production, Tauri bundles it as a resource next to the executable
        let script_path = if cfg!(debug_assertions) {
            let manifest_dir = std::path::Path::new(env!("CARGO_MANIFEST_DIR"));
            manifest_dir
                .parent()
                .unwrap_or(manifest_dir)
                .join("scripts")
                .join("avast_ssl_fix.py")
        } else {
            use tauri::Manager;
            app_handle
                .path()
                .resource_dir()
                .map_err(|e| format!("Failed to get resource dir: {}", e))?
                .join("scripts")
                .join("avast_ssl_fix.py")
        };
        args.push(script_path.to_string_lossy().to_string());
    }

    // On macOS/Linux, run the daemon module directly (no wrapper needed)
    #[cfg(not(target_os = "windows"))]
    {
        args.push("-m".to_string());
        args.push("reachy_mini.daemon.app.main".to_string());
    }

    // Common daemon arguments
    args.push("--desktop-app-daemon".to_string());
    args.push("--no-wake-up-on-start".to_string()); // Robot starts sleeping, toggle controls wake

    // Pre-download emotions/dances at startup (requires newer reachy-mini)
    // We'll try with this first, and fall back to without it if the daemon doesn't support it
    if preload_datasets {
        args.push("--preload-datasets".to_string());
    }

    if sim_mode {
        // Use --mockup-sim for mockup simulation (no MuJoCo required)
        args.push("--mockup-sim".to_string());
    }

    Ok(args)
}
