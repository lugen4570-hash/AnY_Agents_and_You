//! AnY Tauri 2 desktop shell entrypoint, controlled native IPC, and lifecycle wiring.

pub mod backend;
pub mod platform;

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::Arc;

use tauri::webview::DownloadEvent;
use tauri::{Manager, WebviewUrl, WebviewWindowBuilder, WindowEvent};

struct AppState {
    port: u16,
}

fn ensure_trusted_main_caller(
    window: &tauri::WebviewWindow,
    expected_port: u16,
) -> Result<(), String> {
    if window.label() != "main" {
        return Err("仅主窗口可调用桌面文件选择器".to_string());
    }
    let current = window
        .url()
        .map_err(|_| "无法验证当前页面来源".to_string())?;
    if !backend::is_local_app_url(&current, expected_port) || current.path() != "/" {
        return Err("非本地受信任来源禁止调用桌面选择器".to_string());
    }
    Ok(())
}

#[tauri::command]
fn any_choose_workdir(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, AppState>,
) -> Result<Option<String>, String> {
    ensure_trusted_main_caller(&window, state.port)?;
    let selected = rfd::FileDialog::new().set_parent(&window).pick_folder();
    Ok(selected.map(|p| p.to_string_lossy().into_owned()))
}

#[tauri::command]
fn any_choose_agent_file(
    window: tauri::WebviewWindow,
    state: tauri::State<'_, AppState>,
) -> Result<Option<String>, String> {
    ensure_trusted_main_caller(&window, state.port)?;
    let selected = rfd::FileDialog::new().set_parent(&window).pick_file();
    Ok(selected.map(|p| p.to_string_lossy().into_owned()))
}

fn downloads_dir(app: &tauri::AppHandle) -> PathBuf {
    app.path()
        .download_dir()
        .unwrap_or_else(|_| std::env::temp_dir())
}

fn apply_window_theme(window: &tauri::WebviewWindow) {
    #[cfg(windows)]
    {
        if let Ok(hwnd) = window.hwnd() {
            platform::tint_title_bar_hwnd(hwnd.0 as isize);
        }
    }
    #[cfg(not(windows))]
    let _ = window;
}

/// Start or attach to the verified AnY backend and launch the Tauri 2 main window.
pub fn run() -> i32 {
    let (base, port) = backend::base_url_and_port();
    let Some(core) = backend::find_core(None) else {
        platform::show_error("找不到 AnY 后台。请确认应用包完整；Windows 版需要把 AnY.exe 和 AnYCore.exe 放在同一个文件夹里。");
        return 2;
    };

    let token = match backend::ensure_backend(&base, port, &core) {
        Ok(tok) => tok,
        Err(msg) => {
            platform::show_error(&msg);
            return 2;
        }
    };

    let tab = backend::new_tab_id();
    let heartbeat = match backend::TabHeartbeat::start(base.clone(), token.clone(), tab.clone()) {
        Ok(heartbeat) => Arc::new(heartbeat),
        Err(error) => {
            platform::show_error(&error);
            return 2;
        }
    };
    let app_url: url::Url = match format!("{base}/?owner_tab={tab}").parse() {
        Ok(u) => u,
        Err(_) => {
            heartbeat.stop();
            platform::show_error("AnY 本地地址无效，无法打开窗口。");
            return 2;
        }
    };

    let init_script = format!("\
(function(){{\
  if(window===window.top && location.origin==='http://127.0.0.1:{port}' && location.pathname==='/'){{\
    window.__ANY_NATIVE_HEARTBEAT__=true;\
    window.__COJAM_NATIVE_HEARTBEAT__=true;\
    window.dispatchEvent(new Event('anydesktopready'));\
    window.dispatchEvent(new Event('cojamdesktopready'));\
  }}\
}})();");

    let closing_allowed = Arc::new(AtomicBool::new(false));
    let close_heartbeat = Arc::clone(&heartbeat);
    let close_flag = Arc::clone(&closing_allowed);
    let close_base = base.clone();
    let close_token = token.clone();
    let download_port = port;
    let nav_port = port;
    let new_win_port = port;

    let app = tauri::Builder::default()
        .manage(AppState { port })
        .invoke_handler(tauri::generate_handler![
            any_choose_workdir,
            any_choose_agent_file
        ])
        .setup(move |app| {
            // Grant IPC to this launch's exact backend origin, never every local port.
            app.add_capability(
                tauri::ipc::CapabilityBuilder::new("any-main-runtime")
                    .local(false)
                    .window("main")
                    .remote(format!("http://127.0.0.1:{port}/"))
                    .permission("allow-any-choose-workdir")
                    .permission("allow-any-choose-agent-file"),
            )?;
            let dl_dir = downloads_dir(app.handle());
            let mut builder = WebviewWindowBuilder::new(app, "main", WebviewUrl::External(app_url))
                .title(platform::TITLE)
                .inner_size(1280.0, 860.0)
                .min_inner_size(960.0, 640.0)
                .on_document_title_changed(|window, _title| {
                    // Meeting titles change in HTML, but the updater finds this fixed native title.
                    let _ = window.set_title(platform::TITLE);
                })
                .initialization_script(&init_script)
                .on_navigation(move |url| {
                    if backend::is_local_app_url(url, nav_port) {
                        return true;
                    }
                    if platform::is_safe_external_url(url) {
                        platform::open_external_url(url);
                    }
                    false
                })
                .on_new_window(move |url, _features| {
                    if backend::is_local_app_url(&url, new_win_port) {
                        return tauri::webview::NewWindowResponse::Allow;
                    }
                    if platform::is_safe_external_url(&url) {
                        platform::open_external_url(&url);
                    }
                    tauri::webview::NewWindowResponse::Deny
                })
                .on_download(move |_webview, event| match event {
                    DownloadEvent::Requested { url, destination } => {
                        if !backend::is_allowed_download_url(&url, download_port) {
                            return false;
                        }
                        *destination = backend::resolve_download_destination(&dl_dir, destination);
                        true
                    }
                    DownloadEvent::Finished { .. } => true,
                    _ => true,
                });

            builder = builder.focused(true);
            let window = builder.build()?;
            apply_window_theme(&window);
            Ok(())
        })
        .on_window_event(move |window, event| {
            if window.label() != "main" {
                return;
            }
            if let WindowEvent::ThemeChanged(_) = event {
                if let Some(webview) = window.app_handle().get_webview_window("main") {
                    apply_window_theme(&webview);
                }
            }
            if let WindowEvent::CloseRequested { api, .. } = event {
                if close_flag.load(Ordering::Acquire) {
                    close_heartbeat.stop();
                    return;
                }
                if backend::confirm_close(&close_base, &close_token, port) {
                    close_flag.store(true, Ordering::Release);
                    close_heartbeat.stop();
                } else {
                    api.prevent_close();
                }
            }
        })
        .build(tauri::generate_context!());

    let app = match app {
        Ok(a) => a,
        Err(err) => {
            // Fallback to system browser if WebView2 runtime fails to initialize.
            if let Ok(parsed) = format!("{base}/").parse() {
                if platform::open_external_url(&parsed) {
                    heartbeat.handoff_to_browser();
                    platform::show_error(&format!(
                        "没能打开桌面窗口（可能缺少 WebView2 运行时），已改用浏览器打开 AnY。\n{err}"
                    ));
                    return 0;
                }
            }
            heartbeat.stop();
            platform::show_error(&format!("没能打开桌面窗口，也没能打开浏览器。\n{err}"));
            return 2;
        }
    };

    app.run(|_handle, _event| {});
    heartbeat.stop();
    0
}
