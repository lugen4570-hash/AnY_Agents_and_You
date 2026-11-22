//! Platform-specific dialogs, title bar theming, and safe external URL launch.

use url::Url;

pub const TITLE: &str = "AnY";

/// Display an error dialog using native platform chrome, falling back to stderr.
pub fn show_error(text: &str) {
    #[cfg(windows)]
    {
        if win32_message_box(text, 0x0000_0010) != 0 {
            return;
        }
    }
    #[cfg(target_os = "macos")]
    {
        let script = "on run argv\n display alert \"AnY\" message (item 1 of argv)\nend run";
        if std::process::Command::new("/usr/bin/osascript")
            .args(["-e", script, text])
            .status()
            .is_ok()
        {
            return;
        }
    }
    eprintln!("{text}");
}

/// Ask the user to confirm an action. Defaults to false if dialog creation fails.
pub fn show_confirm(text: &str) -> bool {
    #[cfg(windows)]
    {
        // MB_YESNO (0x04) | MB_ICONWARNING (0x30) | MB_DEFBUTTON2 (0x100)
        return win32_message_box(text, 0x0000_0004 | 0x0000_0030 | 0x0000_0100) == 6;
    }
    #[cfg(target_os = "macos")]
    {
        let script = "on run argv\n display dialog (item 1 of argv) with title \"AnY\" buttons {\"取消\", \"确定\"} default button \"确定\"\nend run";
        return std::process::Command::new("/usr/bin/osascript")
            .args(["-e", script, text])
            .status()
            .map(|s| s.success())
            .unwrap_or(false);
    }
    #[cfg(not(any(windows, target_os = "macos")))]
    {
        let _ = text;
        false
    }
}

/// Validate and open an external http/https URL in the OS default browser without a shell.
pub fn open_external_url(url: &Url) -> bool {
    if !is_safe_external_url(url) {
        return false;
    }
    #[cfg(windows)]
    {
        win32_open_url(url.as_str())
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("/usr/bin/open")
            .arg(url.as_str())
            .spawn()
            .is_ok()
    }
    #[cfg(not(any(windows, target_os = "macos")))]
    {
        std::process::Command::new("xdg-open")
            .arg(url.as_str())
            .spawn()
            .is_ok()
    }
}

/// Allow only non-empty http/https URLs without credentials for external browser launch.
pub fn is_safe_external_url(url: &Url) -> bool {
    matches!(url.scheme(), "http" | "https")
        && url.has_host()
        && url.username().is_empty()
        && url.password().is_none()
}

/// Apply Windows 11 dark/light DWM title bar, text and border attributes matching Cojam's CSS.
#[cfg(windows)]
pub fn tint_title_bar_hwnd(hwnd_val: isize) {
    use windows_sys::Win32::Foundation::HWND;
    use windows_sys::Win32::Graphics::Dwm::DwmSetWindowAttribute;

    if hwnd_val == 0 {
        return;
    }
    let dark = system_dark_theme();
    let use_dark: u32 = if dark { 1 } else { 0 };
    let caption = colorref(if dark { "#0a1417" } else { "#e6f0ec" });
    let text = colorref(if dark { "#f3f2e7" } else { "#18302b" });
    let border = caption;
    let hwnd = hwnd_val as HWND;

    unsafe {
        let _ = DwmSetWindowAttribute(hwnd, 20, &use_dark as *const u32 as *const _, 4);
        let _ = DwmSetWindowAttribute(hwnd, 35, &caption as *const u32 as *const _, 4);
        let _ = DwmSetWindowAttribute(hwnd, 36, &text as *const u32 as *const _, 4);
        let _ = DwmSetWindowAttribute(hwnd, 34, &border as *const u32 as *const _, 4);
    }
}

#[cfg(not(windows))]
pub fn tint_title_bar_hwnd(_hwnd_val: isize) {}

/// Convert `#RRGGBB` to Win32 BGR `COLORREF`.
pub fn colorref(hex: &str) -> u32 {
    let clean = hex.trim_start_matches('#');
    if clean.len() != 6 {
        return 0;
    }
    let r = u32::from_str_radix(&clean[0..2], 16).unwrap_or(0);
    let g = u32::from_str_radix(&clean[2..4], 16).unwrap_or(0);
    let b = u32::from_str_radix(&clean[4..6], 16).unwrap_or(0);
    (b << 16) | (g << 8) | r
}

#[cfg(windows)]
fn to_wide(text: &str) -> Vec<u16> {
    use std::ffi::OsStr;
    use std::os::windows::ffi::OsStrExt;
    OsStr::new(text)
        .encode_wide()
        .chain(std::iter::once(0))
        .collect()
}

#[cfg(windows)]
fn win32_message_box(text: &str, flags: u32) -> i32 {
    use windows_sys::Win32::UI::WindowsAndMessaging::MessageBoxW;
    let body = to_wide(text);
    let title = to_wide(TITLE);
    unsafe { MessageBoxW(std::ptr::null_mut(), body.as_ptr(), title.as_ptr(), flags) }
}

#[cfg(windows)]
fn win32_open_url(url: &str) -> bool {
    use windows_sys::Win32::UI::Shell::ShellExecuteW;
    use windows_sys::Win32::UI::WindowsAndMessaging::SW_SHOWNORMAL;
    let verb = to_wide("open");
    let target = to_wide(url);
    let rc = unsafe {
        ShellExecuteW(
            std::ptr::null_mut(),
            verb.as_ptr(),
            target.as_ptr(),
            std::ptr::null(),
            std::ptr::null(),
            SW_SHOWNORMAL,
        )
    };
    (rc as isize) > 32
}

#[cfg(windows)]
fn system_dark_theme() -> bool {
    use windows_sys::Win32::System::Registry::{
        RegCloseKey, RegGetValueW, RegOpenKeyExW, HKEY_CURRENT_USER, KEY_READ, RRF_RT_REG_DWORD,
    };
    let subkey = to_wide(r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize");
    let value_name = to_wide("AppsUseLightTheme");
    let mut hkey = std::ptr::null_mut();
    unsafe {
        if RegOpenKeyExW(HKEY_CURRENT_USER, subkey.as_ptr(), 0, KEY_READ, &mut hkey) != 0 {
            return false;
        }
        let mut data: u32 = 1;
        let mut size: u32 = std::mem::size_of::<u32>() as u32;
        let rc = RegGetValueW(
            hkey,
            std::ptr::null(),
            value_name.as_ptr(),
            RRF_RT_REG_DWORD,
            std::ptr::null_mut(),
            &mut data as *mut u32 as *mut _,
            &mut size,
        );
        let _ = RegCloseKey(hkey);
        rc == 0 && data == 0
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn colorref_matches_bgr_order() {
        assert_eq!(colorref("#1b1b1e"), 0x001E_1B1B);
        assert_eq!(colorref("#ececf1"), 0x00F1_ECEC);
        assert_eq!(colorref("#ffffff"), 0x00FF_FFFF);
        assert_eq!(colorref("#18181b"), 0x001B_1818);
    }

    #[test]
    fn external_url_validation_blocks_unsafe_schemes() {
        assert!(is_safe_external_url(
            &Url::parse("https://example.com/docs").unwrap()
        ));
        assert!(is_safe_external_url(
            &Url::parse("http://192.168.1.10:8080/x").unwrap()
        ));
        assert!(!is_safe_external_url(
            &Url::parse("file:///C:/Windows/win.ini").unwrap()
        ));
        assert!(!is_safe_external_url(
            &Url::parse("javascript:alert(1)").unwrap()
        ));
        assert!(!is_safe_external_url(
            &Url::parse("https://user:pass@example.com").unwrap()
        ));
    }
}
