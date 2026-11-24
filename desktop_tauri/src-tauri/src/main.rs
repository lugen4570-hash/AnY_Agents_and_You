#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

fn main() {
    let code = any_desktop_lib::run();
    if code != 0 {
        std::process::exit(code);
    }
}
