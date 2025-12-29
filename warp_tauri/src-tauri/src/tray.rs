// SAM System Tray / Menu Bar Integration
// Makes SAM always present in your macOS menu bar

use tauri::{
    AppHandle, CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu,
    SystemTrayMenuItem, SystemTraySubmenu, Window,
};

/// Build the system tray menu
pub fn create_tray() -> SystemTray {
    // Quick actions
    let open = CustomMenuItem::new("open", "Open SAM");
    let quick_chat = CustomMenuItem::new("quick_chat", "Quick Chat... ⌘⇧A");
    let separator1 = SystemTrayMenuItem::Separator;

    // Status
    let status_idle = CustomMenuItem::new("status_idle", "● Online").disabled();

    // Mood submenu
    let mood_happy = CustomMenuItem::new("mood_happy", "😊 Happy");
    let mood_playful = CustomMenuItem::new("mood_playful", "😏 Playful");
    let mood_focused = CustomMenuItem::new("mood_focused", "💻 Focused");
    let mood_flirty = CustomMenuItem::new("mood_flirty", "😈 Flirty");
    let mood_menu = SystemTraySubmenu::new(
        "Set Mood",
        SystemTrayMenu::new()
            .add_item(mood_happy)
            .add_item(mood_playful)
            .add_item(mood_focused)
            .add_item(mood_flirty),
    );

    // Avatar controls
    let show_avatar = CustomMenuItem::new("show_avatar", "Show Avatar Window");
    let hide_avatar = CustomMenuItem::new("hide_avatar", "Hide Avatar");
    let avatar_settings = CustomMenuItem::new("avatar_settings", "Customize Avatar...");

    // Voice
    let voice_enabled = CustomMenuItem::new("voice_enabled", "✓ Voice Enabled");
    let voice_mute = CustomMenuItem::new("voice_mute", "Mute Voice");

    // Proactive
    let proactive_on = CustomMenuItem::new("proactive_on", "✓ Proactive Check-ins");
    let proactive_off = CustomMenuItem::new("proactive_off", "Disable Check-ins");

    let separator2 = SystemTrayMenuItem::Separator;

    // Memory & Settings
    let view_memories = CustomMenuItem::new("view_memories", "View Memories...");
    let clear_conversation = CustomMenuItem::new("clear_conversation", "Clear Conversation");
    let settings = CustomMenuItem::new("settings", "Settings...");

    let separator3 = SystemTrayMenuItem::Separator;

    // Quit
    let quit = CustomMenuItem::new("quit", "Quit SAM");

    let tray_menu = SystemTrayMenu::new()
        .add_item(open)
        .add_item(quick_chat)
        .add_native_item(separator1)
        .add_item(status_idle)
        .add_submenu(mood_menu)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(show_avatar)
        .add_item(hide_avatar)
        .add_item(avatar_settings)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(voice_enabled)
        .add_item(voice_mute)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(proactive_on)
        .add_item(proactive_off)
        .add_native_item(separator2)
        .add_item(view_memories)
        .add_item(clear_conversation)
        .add_item(settings)
        .add_native_item(separator3)
        .add_item(quit);

    SystemTray::new().with_menu(tray_menu)
}

/// Handle system tray events
pub fn handle_tray_event(app: &AppHandle, event: SystemTrayEvent) {
    match event {
        SystemTrayEvent::LeftClick { .. } => {
            // Toggle main window on click
            if let Some(window) = app.get_window("main") {
                if window.is_visible().unwrap_or(false) {
                    let _ = window.hide();
                } else {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
            }
        }
        SystemTrayEvent::MenuItemClick { id, .. } => {
            handle_menu_click(app, &id);
        }
        _ => {}
    }
}

fn handle_menu_click(app: &AppHandle, id: &str) {
    match id {
        "open" => {
            if let Some(window) = app.get_window("main") {
                let _ = window.show();
                let _ = window.set_focus();
            }
        }
        "quick_chat" => {
            // Open quick chat overlay
            open_quick_chat(app);
        }
        "show_avatar" => {
            // Emit event to show avatar
            let _ = app.emit_all("atlas:show_avatar", ());
        }
        "hide_avatar" => {
            let _ = app.emit_all("atlas:hide_avatar", ());
        }
        "avatar_settings" => {
            let _ = app.emit_all("atlas:open_customizer", ());
        }
        "mood_happy" => {
            let _ = app.emit_all("atlas:set_mood", "happy");
        }
        "mood_playful" => {
            let _ = app.emit_all("atlas:set_mood", "playful");
        }
        "mood_focused" => {
            let _ = app.emit_all("atlas:set_mood", "focused");
        }
        "mood_flirty" => {
            let _ = app.emit_all("atlas:set_mood", "flirty");
        }
        "voice_enabled" | "voice_mute" => {
            let _ = app.emit_all("atlas:toggle_voice", ());
        }
        "proactive_on" | "proactive_off" => {
            let _ = app.emit_all("atlas:toggle_proactive", ());
        }
        "view_memories" => {
            let _ = app.emit_all("atlas:view_memories", ());
        }
        "clear_conversation" => {
            let _ = app.emit_all("atlas:clear_conversation", ());
        }
        "settings" => {
            let _ = app.emit_all("atlas:open_settings", ());
        }
        "quit" => {
            std::process::exit(0);
        }
        _ => {}
    }
}

fn open_quick_chat(app: &AppHandle) {
    // Create or show quick chat window
    if let Some(window) = app.get_window("quick_chat") {
        let _ = window.show();
        let _ = window.center();
        let _ = window.set_focus();
    } else {
        // Create new quick chat window
        let _ = tauri::WindowBuilder::new(
            app,
            "quick_chat",
            tauri::WindowUrl::App("/quick-chat".into()),
        )
        .title("SAM")
        .inner_size(500.0, 100.0)
        .resizable(false)
        .decorations(false)
        .transparent(true)
        .always_on_top(true)
        .center()
        .build();
    }
}

/// Update tray icon based on SAM state
pub fn update_tray_icon(app: &AppHandle, state: &str) {
    // In production, you'd swap icons based on state
    // e.g., different colored icons for different moods
    match state {
        "thinking" => {
            // Show thinking indicator
        }
        "talking" => {
            // Show talking indicator
        }
        "intimate" => {
            // Maybe a heart icon?
        }
        _ => {
            // Default icon
        }
    }
}

/// Update menu item states
pub fn update_menu_state(app: &AppHandle, voice_enabled: bool, proactive_enabled: bool) {
    if let Some(tray) = app.tray_handle().try_get_item("voice_enabled") {
        let _ = tray.set_title(if voice_enabled {
            "✓ Voice Enabled"
        } else {
            "Voice Enabled"
        });
    }
    if let Some(tray) = app.tray_handle().try_get_item("proactive_on") {
        let _ = tray.set_title(if proactive_enabled {
            "✓ Proactive Check-ins"
        } else {
            "Proactive Check-ins"
        });
    }
}
