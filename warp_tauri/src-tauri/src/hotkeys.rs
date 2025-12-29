// Global Hotkey Support for SAM
// Quick access from anywhere on your system

use tauri::{AppHandle, GlobalShortcutManager, Manager};

/// Default hotkeys
pub struct SAMHotkeys {
    pub quick_chat: &'static str,      // Open quick chat overlay
    pub toggle_avatar: &'static str,   // Show/hide avatar window
    pub toggle_voice: &'static str,    // Mute/unmute voice
    pub screenshot_chat: &'static str, // Screenshot + ask about it
}

impl Default for SAMHotkeys {
    fn default() -> Self {
        Self {
            quick_chat: "CmdOrCtrl+Shift+A",       // ⌘⇧A
            toggle_avatar: "CmdOrCtrl+Shift+V",    // ⌘⇧V
            toggle_voice: "CmdOrCtrl+Shift+M",     // ⌘⇧M
            screenshot_chat: "CmdOrCtrl+Shift+S",  // ⌘⇧S
        }
    }
}

/// Register all global hotkeys
pub fn register_hotkeys(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let hotkeys = SAMHotkeys::default();
    let mut manager = app.global_shortcut_manager();

    // Quick Chat - ⌘⇧A
    let app_handle = app.clone();
    manager.register(hotkeys.quick_chat, move || {
        open_quick_chat(&app_handle);
    })?;

    // Toggle Avatar - ⌘⇧V
    let app_handle = app.clone();
    manager.register(hotkeys.toggle_avatar, move || {
        toggle_avatar(&app_handle);
    })?;

    // Toggle Voice - ⌘⇧M
    let app_handle = app.clone();
    manager.register(hotkeys.toggle_voice, move || {
        let _ = app_handle.emit_all("atlas:toggle_voice", ());
    })?;

    // Screenshot Chat - ⌘⇧S
    let app_handle = app.clone();
    manager.register(hotkeys.screenshot_chat, move || {
        capture_and_chat(&app_handle);
    })?;

    println!("[SAM] Global hotkeys registered:");
    println!("  {} - Quick Chat", hotkeys.quick_chat);
    println!("  {} - Toggle Avatar", hotkeys.toggle_avatar);
    println!("  {} - Toggle Voice", hotkeys.toggle_voice);
    println!("  {} - Screenshot Chat", hotkeys.screenshot_chat);

    Ok(())
}

/// Unregister all hotkeys
pub fn unregister_hotkeys(app: &AppHandle) -> Result<(), Box<dyn std::error::Error>> {
    let hotkeys = SAMHotkeys::default();
    let mut manager = app.global_shortcut_manager();

    manager.unregister(hotkeys.quick_chat)?;
    manager.unregister(hotkeys.toggle_avatar)?;
    manager.unregister(hotkeys.toggle_voice)?;
    manager.unregister(hotkeys.screenshot_chat)?;

    Ok(())
}

fn open_quick_chat(app: &AppHandle) {
    if let Some(window) = app.get_window("quick_chat") {
        if window.is_visible().unwrap_or(false) {
            let _ = window.hide();
        } else {
            let _ = window.show();
            let _ = window.center();
            let _ = window.set_focus();
        }
    } else {
        // Create the quick chat window
        let _ = tauri::WindowBuilder::new(
            app,
            "quick_chat",
            tauri::WindowUrl::App("/quick-chat".into()),
        )
        .title("")
        .inner_size(600.0, 80.0)
        .resizable(false)
        .decorations(false)
        .transparent(true)
        .always_on_top(true)
        .center()
        .skip_taskbar(true)
        .build();
    }
}

fn toggle_avatar(app: &AppHandle) {
    if let Some(window) = app.get_window("avatar") {
        if window.is_visible().unwrap_or(false) {
            let _ = window.hide();
        } else {
            let _ = window.show();
            let _ = window.set_focus();
        }
    } else {
        // Emit event to create/show avatar
        let _ = app.emit_all("atlas:toggle_avatar", ());
    }
}

fn capture_and_chat(app: &AppHandle) {
    // Take screenshot using macOS screencapture
    use std::process::Command;

    let timestamp = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap()
        .as_secs();

    let path = format!("/tmp/atlas_screenshot_{}.png", timestamp);

    // Interactive screenshot selection
    let output = Command::new("screencapture")
        .args(["-i", "-s", &path])
        .output();

    match output {
        Ok(result) if result.status.success() => {
            // Check if file was created (user didn't cancel)
            if std::path::Path::new(&path).exists() {
                // Emit event with screenshot path
                let _ = app.emit_all("atlas:screenshot_chat", path);

                // Open quick chat with image context
                open_quick_chat(app);
            }
        }
        _ => {
            // User cancelled or error
        }
    }
}

/// Custom hotkey registration (for user preferences)
pub fn register_custom_hotkey(
    app: &AppHandle,
    shortcut: &str,
    action: &str,
) -> Result<(), Box<dyn std::error::Error>> {
    let mut manager = app.global_shortcut_manager();
    let app_handle = app.clone();
    let action = action.to_string();

    manager.register(shortcut, move || {
        let _ = app_handle.emit_all(&format!("atlas:{}", action), ());
    })?;

    Ok(())
}
