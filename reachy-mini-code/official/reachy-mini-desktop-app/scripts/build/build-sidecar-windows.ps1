# build_sidecar_windows.ps1
# Script to build the uv-trampoline sidecar for Windows

$DST_DIR = "src-tauri/binaries"
New-Item -ItemType Directory -Path $DST_DIR -Force | Out-Null

# Get Rust target triplet
$TRIPLET = (rustc -Vv | Select-String "host:" | ForEach-Object { $_.Line.Split(" ")[1] })

Push-Location uv-wrapper
    cargo build --release --bin uv-trampoline
    Copy-Item target/release/uv-trampoline.exe ../$DST_DIR/uv-trampoline-$TRIPLET.exe -Force
Pop-Location
