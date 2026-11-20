fn main() {
    let manifest_dir = std::path::PathBuf::from(
        std::env::var("CARGO_MANIFEST_DIR").expect("CARGO_MANIFEST_DIR missing"),
    );
    let version_file = manifest_dir
        .join("..")
        .join("..")
        .join("bridge")
        .join("version.py");
    println!("cargo:rerun-if-changed={}", version_file.display());

    let mut version = std::env::var("CARGO_PKG_VERSION").unwrap_or_else(|_| "0.0.0".to_string());
    let mut api_revision = "3".to_string();
    if let Ok(text) = std::fs::read_to_string(&version_file) {
        for line in text.lines() {
            let trimmed = line.trim();
            if let Some(rest) = trimmed.strip_prefix("VERSION") {
                if let Some((_, val)) = rest.split_once('=') {
                    let clean = val.trim().trim_matches('"').trim_matches('\'');
                    if !clean.is_empty() {
                        version = clean.to_string();
                    }
                }
            } else if let Some(rest) = trimmed.strip_prefix("API_REVISION") {
                if let Some((_, val)) = rest.split_once('=') {
                    let clean = val.trim().trim_matches('"').trim_matches('\'');
                    if !clean.is_empty() {
                        api_revision = clean.to_string();
                    }
                }
            }
        }
    }
    println!("cargo:rustc-env=COJAM_EXPECTED_VERSION={version}");
    println!("cargo:rustc-env=COJAM_EXPECTED_API_REVISION={api_revision}");

    tauri_build::try_build(
        tauri_build::Attributes::new().app_manifest(
            tauri_build::AppManifest::new()
                .commands(&["cojam_choose_workdir", "cojam_choose_agent_file"]),
        ),
    )
    .expect("failed to run tauri-build");
}
