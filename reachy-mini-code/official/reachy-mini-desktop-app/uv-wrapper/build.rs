//! Tell cargo to rebuild the trampoline whenever the env vars consumed by
//! `option_env!()` in `get_reachy_mini_spec()` change. Without this, cargo's
//! incremental cache happily serves a stale binary that still bakes in the
//! previous branch, and you end up debugging a "wrong daemon version is
//! installed" bug for an hour.
//!
//! Also tracks `REACHY_MINI_PATCH_VERSION` for parity with the desktop
//! app's release pipeline.
fn main() {
    println!("cargo:rerun-if-env-changed=REACHY_MINI_SOURCE");
    println!("cargo:rerun-if-env-changed=REACHY_MINI_VERSION");
    println!("cargo:rerun-if-env-changed=REACHY_MINI_PATCH_VERSION");
}
