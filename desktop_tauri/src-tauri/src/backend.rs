//! Backend discovery, identity/runtime verification, lifecycle heartbeat, and safe close checks.

use std::collections::HashSet;
use std::env;
use std::net::{SocketAddr, TcpListener};
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::atomic::{AtomicBool, Ordering};
use std::sync::{Arc, Condvar, Mutex};
use std::thread::{self, JoinHandle};
use std::time::{Duration, Instant};

use rand::Rng;
use serde::Deserialize;

use crate::platform;

pub const APP_NAME: &str = "AI Bridge";
pub const EXPECTED_VERSION: &str = env!("ANY_EXPECTED_VERSION");
pub const EXPECTED_API_REVISION_STR: &str = env!("ANY_EXPECTED_API_REVISION");

pub const BUSY_TEXT: &str =
    "还有任务正在运行或排队。现在关闭窗口，如果这是最后一个 AnY 页面，任务会中断。确定关闭吗？";
pub const BUSY_UNKNOWN_TEXT: &str =
    "无法确认后台是否仍有任务正在运行或排队。现在关闭窗口可能导致进行中的任务中断。确定关闭吗？";

#[derive(Debug, Clone)]
pub struct CoreLaunch {
    pub program: PathBuf,
    pub args: Vec<String>,
    pub cwd: PathBuf,
    pub install_path: PathBuf,
    pub data_dir: PathBuf,
    pub log_path: PathBuf,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ServerInfo {
    pub app: Option<String>,
    pub version: Option<String>,
    pub api_revision: Option<u64>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct RuntimeInfo {
    pub install: Option<String>,
    pub data: Option<String>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum ProbeResult {
    AnY(String, Option<u64>),
    Free,
    Timeout,
    Foreign,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BusyState {
    Idle,
    Busy,
    Unknown,
}

/// Resolve `http://127.0.0.1:<port>` from `ROUNDTABLE_PORT` (default `8765`).
pub fn base_url_and_port() -> (String, u16) {
    let port = env::var("ROUNDTABLE_PORT")
        .ok()
        .and_then(|s| s.trim().parse::<u16>().ok())
        .filter(|&p| p > 0)
        .unwrap_or(8765);
    (format!("http://127.0.0.1:{port}"), port)
}

/// Locate the sibling `AnYCore.exe` / `AnY.exe` backend, or source `roundtable.py` during dev.
pub fn find_core(current_exe: Option<&Path>) -> Option<CoreLaunch> {
    let exe = match current_exe {
        Some(p) => p.to_path_buf(),
        None => env::current_exe().ok()?,
    };
    let exe_canon = strip_win_prefix(&exe.canonicalize().unwrap_or_else(|_| exe.clone()));
    let exe_dir = exe.parent()?.to_path_buf();

    let candidates = if cfg!(windows) {
        ["AnYCore.exe", "AnY.exe"]
    } else {
        ["AnYCore", "AnY"]
    };
    for name in candidates {
        let candidate = exe_dir.join(name);
        if candidate.is_file() {
            let cand_canon = strip_win_prefix(
                &candidate
                    .canonicalize()
                    .unwrap_or_else(|_| candidate.clone()),
            );
            if !same_path_str(&cand_canon.to_string_lossy(), &exe_canon.to_string_lossy()) {
                let data_dir = resolve_data_dir(&exe_dir);
                let log_path = data_dir.join("any.log");
                return Some(CoreLaunch {
                    program: candidate,
                    args: Vec::new(),
                    cwd: exe_dir,
                    install_path: cand_canon,
                    data_dir,
                    log_path,
                });
            }
        }
    }

    // Source / Cargo dev fallback: locate repo root with roundtable.py.
    if let Ok(explicit) = env::var("ROUNDTABLE_CORE") {
        let explicit_path = PathBuf::from(explicit.trim());
        if explicit_path.is_file() {
            let cwd = explicit_path.parent().unwrap_or(&exe_dir).to_path_buf();
            let canon = strip_win_prefix(
                &explicit_path
                    .canonicalize()
                    .unwrap_or_else(|_| explicit_path.clone()),
            );
            let data_dir = resolve_data_dir(&cwd);
            let log_path = data_dir.join("any.log");
            return Some(CoreLaunch {
                program: explicit_path,
                args: Vec::new(),
                cwd,
                install_path: canon,
                data_dir,
                log_path,
            });
        }
    }

    let mut cur = exe.parent();
    while let Some(dir) = cur {
        let script = dir.join("roundtable.py");
        if script.is_file() {
            let py = find_python(dir);
            let repo_canon =
                strip_win_prefix(&dir.canonicalize().unwrap_or_else(|_| dir.to_path_buf()));
            let data_dir = resolve_data_dir(&repo_canon);
            let log_path = data_dir.join("any.log");
            return Some(CoreLaunch {
                program: py,
                args: vec![script.to_string_lossy().into_owned()],
                cwd: repo_canon.clone(),
                install_path: repo_canon,
                data_dir,
                log_path,
            });
        }
        cur = dir.parent();
    }
    None
}

fn find_python(_repo: &Path) -> PathBuf {
    if let Ok(explicit) = env::var("ROUNDTABLE_PYTHON") {
        let p = PathBuf::from(explicit.trim());
        if p.is_file() {
            return p;
        }
    }
    PathBuf::from(if cfg!(windows) {
        "pythonw.exe"
    } else {
        "python3"
    })
}

fn resolve_data_dir(core_dir: &Path) -> PathBuf {
    if let Ok(custom) = env::var("ROUNDTABLE_LOG_DIR") {
        let trimmed = custom.trim();
        if !trimmed.is_empty() {
            let path = PathBuf::from(trimmed);
            return if path.is_absolute() {
                path
            } else {
                core_dir.join(path)
            };
        }
    }
    #[cfg(target_os = "macos")]
    {
        if let Ok(home) = env::var("HOME") {
            let support = PathBuf::from(home).join("Library").join("Application Support");
            let new_dir = support.join("AnY");
            let old_dir = support.join("Cojam");
            if !new_dir.exists() && old_dir.exists() {
                return old_dir;
            }
            return new_dir;
        }
    }
    core_dir.join("data")
}

/// Normalize path casing and separators, stripping Windows `\\?\` prefix for parity with Python `realpath`.
pub fn strip_win_prefix(path: &Path) -> PathBuf {
    let raw = path.to_string_lossy();
    if let Some(rest) = raw.strip_prefix(r"\\?\UNC\") {
        return PathBuf::from(format!(r"\\{rest}"));
    }
    if let Some(rest) = raw.strip_prefix(r"\\?\") {
        return PathBuf::from(rest);
    }
    path.to_path_buf()
}

pub fn normalize_path_key(raw: &str) -> String {
    let stripped = strip_win_prefix(Path::new(raw.trim()));
    let mut s = stripped.to_string_lossy().replace('/', r"\");
    while s.len() > 3 && s.ends_with('\\') {
        s.pop();
    }
    if cfg!(windows) {
        s.to_lowercase()
    } else {
        stripped.to_string_lossy().into_owned()
    }
}

pub fn same_path_str(a: &str, b: &str) -> bool {
    !a.trim().is_empty() && !b.trim().is_empty() && normalize_path_key(a) == normalize_path_key(b)
}

fn same_path_buf(remote_str: Option<&str>, expected: &Path) -> bool {
    let Some(remote) = remote_str else {
        return false;
    };
    let expected_canon = strip_win_prefix(
        &expected
            .canonicalize()
            .unwrap_or_else(|_| expected.to_path_buf()),
    );
    let remote_canon = Path::new(remote)
        .canonicalize()
        .map(|p| strip_win_prefix(&p))
        .unwrap_or_else(|_| strip_win_prefix(Path::new(remote)));
    same_path_str(
        &remote_canon.to_string_lossy(),
        &expected_canon.to_string_lossy(),
    )
}

fn http_agent(timeout: Duration) -> ureq::Agent {
    ureq::AgentBuilder::new()
        .timeout_connect(timeout)
        .timeout_read(timeout)
        .timeout_write(timeout)
        .build()
}

fn port_bindable(port: u16) -> bool {
    TcpListener::bind(SocketAddr::from(([127, 0, 0, 1], port))).is_ok()
}

pub fn probe(base: &str, port: u16, timeout: Duration) -> ProbeResult {
    let url = format!("{}/api/server/info", base.trim_end_matches('/'));
    let agent = http_agent(timeout);
    match agent.get(&url).call() {
        Ok(resp) => {
            if let Ok(info) = resp.into_json::<ServerInfo>() {
                if info.app.as_deref() == Some(APP_NAME) {
                    return ProbeResult::AnY(info.version.unwrap_or_default(), info.api_revision);
                }
            }
            ProbeResult::Foreign
        }
        Err(ureq::Error::Status(_, _)) => ProbeResult::Foreign,
        Err(ureq::Error::Transport(t)) => {
            let msg = t.to_string().to_lowercase();
            if msg.contains("timed out") || msg.contains("timeout") {
                if port_bindable(port) {
                    ProbeResult::Free
                } else {
                    ProbeResult::Timeout
                }
            } else if port_bindable(port) {
                ProbeResult::Free
            } else {
                ProbeResult::Timeout
            }
        }
    }
}

pub fn expected_api_revision() -> Option<u64> {
    EXPECTED_API_REVISION_STR.trim().parse::<u64>().ok()
}

pub fn extract_rt_token(html: &str) -> Option<String> {
    let marker = r#"name="rt-token" content=""#;
    let start = html.find(marker)? + marker.len();
    let end = html[start..].find('"')?;
    let tok = &html[start..start + end];
    if tok.is_empty() {
        None
    } else {
        Some(tok.to_string())
    }
}

pub fn fetch_token(base: &str) -> Result<String, String> {
    let url = format!("{}/", base.trim_end_matches('/'));
    let html = http_agent(Duration::from_secs(3))
        .get(&url)
        .call()
        .map_err(|_| "已运行的 AnY 后台版本不兼容，请先退出旧版再打开桌面版。".to_string())?
        .into_string()
        .map_err(|_| "已运行的 AnY 后台版本不兼容，请先退出旧版再打开桌面版。".to_string())?;
    extract_rt_token(&html)
        .ok_or_else(|| "已运行的 AnY 后台版本不兼容，请先退出旧版再打开桌面版。".to_string())
}

pub fn fetch_runtime(base: &str, token: &str) -> Result<RuntimeInfo, String> {
    let url = format!("{}/api/server/runtime", base.trim_end_matches('/'));
    http_agent(Duration::from_secs(3))
        .get(&url)
        .set("X-RT-Token", token)
        .call()
        .map_err(|_| "已运行的 AnY 后台版本不兼容，请先退出旧版再打开桌面版。".to_string())?
        .into_json::<RuntimeInfo>()
        .map_err(|_| "已运行的 AnY 后台版本不兼容，请先退出旧版再打开桌面版。".to_string())
}

/// Verify an already-running AnY instance matches app, install/data paths, and version/API.
/// If same install & data directory runs a stale version, stop it cleanly when idle.
pub fn ensure_backend(base: &str, port: u16, core: &CoreLaunch) -> Result<String, String> {
    match probe(base, port, Duration::from_millis(500)) {
        ProbeResult::Foreign | ProbeResult::Timeout => {
            return Err(format!("端口 {port} 被其他程序占用，AnY 无法启动。"));
        }
        ProbeResult::AnY(ver, rev) => {
            let token = fetch_token(base)?;
            let runtime = fetch_runtime(base, &token)?;
            if !same_path_buf(runtime.install.as_deref(), &core.install_path)
                || !same_path_buf(runtime.data.as_deref(), &core.data_dir)
            {
                return Err(
                    "端口上已有另一份 AnY。请先退出原来的程序，再打开这一份，以免混用会话数据。"
                        .to_string(),
                );
            }
            if ver == EXPECTED_VERSION && rev == expected_api_revision() {
                return Ok(token);
            }
            // Same installation & data directory with a mismatched version: try stopping idle old core.
            let stop_url = format!("{}/api/server/stop", base.trim_end_matches('/'));
            match http_agent(Duration::from_secs(3))
                .post(&stop_url)
                .set("X-RT-Token", &token)
                .send_string("{}")
            {
                Ok(_) => {
                    let deadline = Instant::now() + Duration::from_secs(3);
                    let mut freed = false;
                    while Instant::now() < deadline {
                        if matches!(
                            probe(base, port, Duration::from_millis(250)),
                            ProbeResult::Free
                        ) {
                            freed = true;
                            break;
                        }
                        thread::sleep(Duration::from_millis(100));
                    }
                    if !freed {
                        return Err("旧后台尚未退出，请稍后重新打开 AnY。".to_string());
                    }
                }
                Err(ureq::Error::Status(409, _)) => {
                    return Err(
                        "旧后台还有任务运行或排队。请等待任务结束，再重新打开 AnY 更新。"
                            .to_string(),
                    );
                }
                Err(_) => {
                    return Err(
                        "已运行的 AnY 后台版本不兼容，请先退出旧版再打开桌面版。".to_string()
                    );
                }
            }
        }
        ProbeResult::Free => {}
    }

    let mut child = spawn_core(core)?;
    if wait_ready(base, port, &mut child, Duration::from_secs(30)).is_none() {
        stop_process(&mut child);
        return Err(format!(
            "AnY 后台没有启动成功。日志：{}",
            core.log_path.display()
        ));
    }
    // Once ready, another UI may already own this core. Never kill it on a
    // later verification error; an unclaimed core has its own startup lease.
    let token = fetch_token(base)?;
    let runtime = fetch_runtime(base, &token)?;
    if !same_path_buf(runtime.install.as_deref(), &core.install_path)
        || !same_path_buf(runtime.data.as_deref(), &core.data_dir)
    {
        return Err("启动后的 AnY 后台路径校验失败，请检查端口占用后重试。".to_string());
    }
    Ok(token)
}

fn spawn_core(core: &CoreLaunch) -> Result<Child, String> {
    let mut cmd = Command::new(&core.program);
    cmd.args(&core.args)
        .current_dir(&core.cwd)
        .env("ROUNDTABLE_NO_BROWSER", "1")
        .env("ROUNDTABLE_OWNER_LIFECYCLE", "1")
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null());

    #[cfg(target_os = "macos")]
    {
        if env::var_os("ROUNDTABLE_LOG_DIR").is_none() {
            cmd.env("ROUNDTABLE_LOG_DIR", &core.data_dir);
        }
    }

    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        const CREATE_NEW_PROCESS_GROUP: u32 = 0x0000_0200;
        cmd.creation_flags(CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP);
    }

    cmd.spawn()
        .map_err(|e| format!("AnY 后台没有启动成功。\n{e}"))
}

fn wait_ready(base: &str, port: u16, child: &mut Child, timeout: Duration) -> Option<()> {
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if let ProbeResult::AnY(ver, rev) = probe(base, port, Duration::from_millis(500)) {
            if ver == EXPECTED_VERSION && rev == expected_api_revision() {
                return Some(());
            }
            return None;
        }
        if matches!(child.try_wait(), Ok(Some(_))) {
            for _ in 0..5 {
                if let ProbeResult::AnY(ver, rev) = probe(base, port, Duration::from_millis(400))
                {
                    if ver == EXPECTED_VERSION && rev == expected_api_revision() {
                        return Some(());
                    }
                    return None;
                }
                thread::sleep(Duration::from_millis(200));
            }
            return None;
        }
        thread::sleep(Duration::from_millis(150));
    }
    None
}

fn stop_process(child: &mut Child) {
    if matches!(child.try_wait(), Ok(Some(_))) {
        return;
    }
    let _ = child.kill();
    let _ = child.wait();
}

pub fn new_tab_id() -> String {
    const CHARS: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-";
    let mut rng = rand::thread_rng();
    (0..32)
        .map(|_| {
            let idx = rng.gen_range(0..CHARS.len());
            CHARS[idx] as char
        })
        .collect()
}

pub fn valid_tab_id(value: &str) -> bool {
    let len = value.len();
    (16..=80).contains(&len)
        && value
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b == b'_' || b == b'-')
}

pub fn post_session(
    base: &str,
    token: &str,
    tab: &str,
    action: &str,
    instance: &str,
) -> Result<(), String> {
    if !valid_tab_id(tab) || !valid_tab_id(instance) {
        return Err("无效页面状态".to_string());
    }
    let url = format!("{}/api/ui/session", base.trim_end_matches('/'));
    let body = serde_json::json!({
        "tab": tab,
        "action": action,
        "instance": instance,
    });
    http_agent(Duration::from_secs(3))
        .post(&url)
        .set("X-RT-Token", token)
        .set("Content-Type", "application/json")
        .send_json(body)
        .map(|_| ())
        .map_err(|e| format!("会话心跳失败: {e}"))
}

/// Native owner-tab heartbeat owned solely by the desktop shell.
pub struct TabHeartbeat {
    base: String,
    token: String,
    tab: String,
    closed: Arc<AtomicBool>,
    stop_signal: Arc<(Mutex<bool>, Condvar)>,
    handle: Mutex<Option<JoinHandle<()>>>,
}

impl TabHeartbeat {
    pub fn start(base: String, token: String, tab: String) -> Result<Self, String> {
        let closed = Arc::new(AtomicBool::new(false));
        let stop_signal = Arc::new((Mutex::new(false), Condvar::new()));
        post_session(&base, &token, &tab, "open", &tab)?;

        let bg_base = base.clone();
        let bg_token = token.clone();
        let bg_tab = tab.clone();
        let bg_signal = Arc::clone(&stop_signal);
        let bg_closed = Arc::clone(&closed);

        let handle = thread::Builder::new()
            .name("any-desktop-heartbeat".to_string())
            .spawn(move || {
                let (lock, cvar) = &*bg_signal;
                let mut guard = lock.lock().unwrap_or_else(|e| e.into_inner());
                while !*guard && !bg_closed.load(Ordering::Acquire) {
                    let (next_guard, res) = cvar
                        .wait_timeout(guard, Duration::from_secs(20))
                        .unwrap_or_else(|e| e.into_inner());
                    guard = next_guard;
                    if *guard || bg_closed.load(Ordering::Acquire) {
                        break;
                    }
                    if res.timed_out() {
                        drop(guard);
                        // Re-open is idempotent and restores the lease after sleep/expiry.
                        let _ = post_session(&bg_base, &bg_token, &bg_tab, "open", &bg_tab);
                        guard = lock.lock().unwrap_or_else(|e| e.into_inner());
                    }
                }
            })
            .map_err(|error| {
                let _ = post_session(&base, &token, &tab, "close", &tab);
                format!("无法启动桌面心跳线程：{error}")
            })?;

        Ok(Self {
            base,
            token,
            tab,
            closed,
            stop_signal,
            handle: Mutex::new(Some(handle)),
        })
    }

    pub fn stop(&self) {
        self.finish(true);
    }

    /// Let the startup owner expire naturally while a browser registers its own tab.
    pub fn handoff_to_browser(&self) {
        self.finish(false);
    }

    fn finish(&self, report_close: bool) {
        if self.closed.swap(true, Ordering::AcqRel) {
            return;
        }
        let (lock, cvar) = &*self.stop_signal;
        if let Ok(mut stopped) = lock.lock() {
            *stopped = true;
            cvar.notify_all();
        }
        if let Ok(mut guard) = self.handle.lock() {
            if let Some(h) = guard.take() {
                let _ = h.join();
            }
        }
        // Join before close so an in-flight renewal cannot re-open a closed owner.
        if report_close {
            let _ = post_session(&self.base, &self.token, &self.tab, "close", &self.tab);
        }
    }
}

impl Drop for TabHeartbeat {
    fn drop(&mut self) {
        self.stop();
    }
}

#[derive(Debug, Deserialize)]
struct RoomsResponse {
    rooms: Option<Vec<RoomRow>>,
}

#[derive(Debug, Deserialize)]
struct RoomRow {
    #[serde(default)]
    running: serde_json::Value,
    #[serde(default)]
    queued: u64,
}

fn value_is_truthy(val: &serde_json::Value) -> bool {
    match val {
        serde_json::Value::Null => false,
        serde_json::Value::Bool(b) => *b,
        serde_json::Value::Number(n) => n.as_u64().unwrap_or(0) > 0,
        serde_json::Value::String(s) => !s.is_empty(),
        serde_json::Value::Array(arr) => !arr.is_empty(),
        serde_json::Value::Object(map) => !map.is_empty(),
    }
}

/// Query `/api/rooms` with explicit Unknown state on errors (never silently assume idle).
pub fn query_busy_state(base: &str, token: &str, port: u16) -> BusyState {
    let url = format!("{}/api/rooms", base.trim_end_matches('/'));
    let resp = http_agent(Duration::from_secs(3))
        .get(&url)
        .set("X-RT-Token", token)
        .call();

    let ok = match resp {
        Ok(response) => response,
        // An HTTP failure is an unknown task state even if the server then exits.
        Err(ureq::Error::Status(_, _)) => return BusyState::Unknown,
        Err(ureq::Error::Transport(_)) => {
            // A stopped backend (e.g. sidebar "退出") has no listener left.
            return if port_bindable(port) {
                BusyState::Idle
            } else {
                BusyState::Unknown
            };
        }
    };
    let Ok(payload) = ok.into_json::<RoomsResponse>() else {
        return BusyState::Unknown;
    };
    let Some(rooms) = payload.rooms else {
        return BusyState::Unknown;
    };
    let busy = rooms
        .iter()
        .any(|row| row.queued > 0 || value_is_truthy(&row.running));
    if busy {
        BusyState::Busy
    } else {
        BusyState::Idle
    }
}

/// Prompt the user when tasks are running/queued OR when busy state could not be verified.
pub fn confirm_close(base: &str, token: &str, port: u16) -> bool {
    match query_busy_state(base, token, port) {
        BusyState::Idle => true,
        BusyState::Busy => platform::show_confirm(BUSY_TEXT),
        BusyState::Unknown => platform::show_confirm(BUSY_UNKNOWN_TEXT),
    }
}

/// Check the exact local HTTP origin; reject aliases and embedded credentials.
pub fn is_local_app_url(url: &url::Url, port: u16) -> bool {
    url.scheme() == "http"
        && url.host_str() == Some("127.0.0.1")
        && url.port_or_known_default() == Some(port)
        && url.username().is_empty()
        && url.password().is_none()
}

/// Allow downloads only from the AnY localhost origin or safe in-page `blob:`/`data:` payloads.
pub fn is_allowed_download_url(url: &url::Url, port: u16) -> bool {
    is_local_app_url(url, port) || matches!(url.scheme(), "blob" | "data")
}

/// Build an idempotent safe local filename inside `downloads_dir` (prevents traversal/overwrite).
pub fn resolve_download_destination(downloads_dir: &Path, suggested_path: &Path) -> PathBuf {
    let raw_name = suggested_path
        .file_name()
        .and_then(|n| n.to_str())
        .unwrap_or("any-download")
        .trim();
    let clean_name: String = raw_name
        .chars()
        .map(|c| {
            if matches!(c, '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*') || c.is_control() {
                '_'
            } else {
                c
            }
        })
        .collect();
    let base_name = if clean_name.is_empty() || clean_name == "." || clean_name == ".." {
        "any-download".to_string()
    } else {
        clean_name
    };
    let candidate = downloads_dir.join(&base_name);
    if !candidate.exists() {
        return candidate;
    }
    let path_obj = Path::new(&base_name);
    let stem = path_obj
        .file_stem()
        .and_then(|s| s.to_str())
        .unwrap_or("any-download");
    let ext = path_obj.extension().and_then(|e| e.to_str()).unwrap_or("");
    let mut existing = HashSet::new();
    if let Ok(entries) = std::fs::read_dir(downloads_dir) {
        for entry in entries.flatten() {
            existing.insert(entry.file_name());
        }
    }
    for n in 1..1000u32 {
        let numbered = if ext.is_empty() {
            format!("{stem} ({n})")
        } else {
            format!("{stem} ({n}).{ext}")
        };
        if !existing.contains(std::ffi::OsStr::new(&numbered)) {
            return downloads_dir.join(numbered);
        }
    }
    downloads_dir.join(format!("{}-{base_name}", new_tab_id()))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::{Read, Write};

    #[test]
    fn path_normalization_ignores_unc_prefix_and_windows_case() {
        assert!(same_path_str(
            r"\\?\D:\AnY\AnYCore.exe",
            r"d:/any/AnYCore.exe"
        ));
        assert!(same_path_str(r"D:\AnY\data\", r"d:\any\data"));
        assert!(!same_path_str(r"D:\AnYA\data", r"D:\AnYB\data"));
    }

    #[test]
    fn extracts_rt_token_from_index_html() {
        let html = r#"<html><meta name="rt-token" content="tok_abc-123"></html>"#;
        assert_eq!(extract_rt_token(html).as_deref(), Some("tok_abc-123"));
        assert_eq!(extract_rt_token("<html></html>"), None);
    }

    #[test]
    fn url_checks_restrict_navigation_and_downloads() {
        let local = url::Url::parse("http://127.0.0.1:8765/files/m1/files/a.txt").unwrap();
        let other_port = url::Url::parse("http://127.0.0.1:9999/").unwrap();
        let external = url::Url::parse("https://example.com/").unwrap();
        let blob = url::Url::parse("blob:http://127.0.0.1:8765/1234").unwrap();
        assert!(is_local_app_url(&local, 8765));
        assert!(!is_local_app_url(&other_port, 8765));
        assert!(!is_local_app_url(&external, 8765));
        assert!(!is_local_app_url(
            &url::Url::parse("http://localhost:8765/").unwrap(),
            8765
        ));
        assert!(!is_local_app_url(
            &url::Url::parse("http://user:pass@127.0.0.1:8765/").unwrap(),
            8765
        ));
        assert!(is_allowed_download_url(&local, 8765));
        assert!(is_allowed_download_url(&blob, 8765));
        assert!(!is_allowed_download_url(&external, 8765));
    }

    #[test]
    fn heartbeat_registration_failure_does_not_launch_a_worker() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let server = thread::spawn(move || {
            let (mut stream, _) = listener.accept().unwrap();
            let mut buf = [0u8; 4096];
            let _ = stream.read(&mut buf);
            stream
                .write_all(
                    b"HTTP/1.1 403 Forbidden\r\nContent-Length: 0\r\nConnection: close\r\n\r\n",
                )
                .unwrap();
        });
        let result = TabHeartbeat::start(
            format!("http://127.0.0.1:{port}"),
            "invalid".into(),
            new_tab_id(),
        );
        assert!(result.is_err());
        server.join().unwrap();
    }

    #[test]
    fn busy_query_returns_unknown_when_server_returns_500() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let handle = thread::spawn(move || {
            if let Ok((mut stream, _)) = listener.accept() {
                let mut buf = [0u8; 1024];
                let _ = stream.read(&mut buf);
                let body = r#"{"error":"boom"}"#;
                let resp = format!(
                    "HTTP/1.1 500 Internal Server Error\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
                let _ = stream.write_all(resp.as_bytes());
            }
        });
        let base = format!("http://127.0.0.1:{port}");
        assert_eq!(query_busy_state(&base, "tok", port), BusyState::Unknown);
        let _ = handle.join();
    }

    #[test]
    fn busy_query_returns_busy_when_room_has_queued_or_running() {
        let listener = TcpListener::bind("127.0.0.1:0").unwrap();
        let port = listener.local_addr().unwrap().port();
        let handle = thread::spawn(move || {
            if let Ok((mut stream, _)) = listener.accept() {
                let mut buf = [0u8; 1024];
                let _ = stream.read(&mut buf);
                let body = r#"{"rooms":[{"running":["codex"],"queued":0}]}"#;
                let resp = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
                    body.len(),
                    body
                );
                let _ = stream.write_all(resp.as_bytes());
            }
        });
        let base = format!("http://127.0.0.1:{port}");
        assert_eq!(query_busy_state(&base, "tok", port), BusyState::Busy);
        let _ = handle.join();
    }
}
