//! Audio Bell - Terminal bell and notification sounds
//!
//! Provides audio feedback for:
//! - Terminal bell (BEL character \x07)
//! - Command completion
//! - Error alerts
//! - Custom notifications

use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};

// =============================================================================
// TYPES
// =============================================================================

/// Sound type
#[derive(Debug, Clone, Copy, Serialize, Deserialize, PartialEq, Eq, Hash)]
pub enum SoundType {
    /// Terminal bell (BEL character)
    Bell,
    /// Command completed successfully
    Success,
    /// Command failed
    Error,
    /// Notification
    Notification,
    /// Agent needs attention
    Attention,
    /// Custom sound
    Custom,
}

/// Sound configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SoundConfig {
    /// Whether sounds are enabled
    pub enabled: bool,
    /// Volume (0.0 - 1.0)
    pub volume: f32,
    /// Bell sound enabled
    pub bell_enabled: bool,
    /// Success sound enabled
    pub success_enabled: bool,
    /// Error sound enabled
    pub error_enabled: bool,
    /// Notification sound enabled
    pub notification_enabled: bool,
    /// Custom sound paths
    pub custom_sounds: std::collections::HashMap<SoundType, String>,
    /// Mute during focus mode
    pub mute_when_focused: bool,
    /// Rate limit (max sounds per second)
    pub rate_limit: u32,
}

impl Default for SoundConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            volume: 0.5,
            bell_enabled: true,
            success_enabled: false,
            error_enabled: true,
            notification_enabled: true,
            custom_sounds: std::collections::HashMap::new(),
            mute_when_focused: false,
            rate_limit: 5,
        }
    }
}

// =============================================================================
// SOUND MANAGER
// =============================================================================

pub struct SoundManager {
    config: SoundConfig,
    last_sound_time: std::time::Instant,
    sounds_this_second: u32,
    muted: bool,
}

impl SoundManager {
    pub fn new() -> Self {
        Self::with_config(SoundConfig::default())
    }

    pub fn with_config(config: SoundConfig) -> Self {
        Self {
            config,
            last_sound_time: std::time::Instant::now(),
            sounds_this_second: 0,
            muted: false,
        }
    }

    /// Play a sound
    pub fn play(&mut self, sound_type: SoundType) -> bool {
        if !self.should_play(sound_type) {
            return false;
        }

        // Rate limiting
        let now = std::time::Instant::now();
        if now.duration_since(self.last_sound_time).as_secs() >= 1 {
            self.sounds_this_second = 0;
        }

        if self.sounds_this_second >= self.config.rate_limit {
            return false;
        }

        self.sounds_this_second += 1;
        self.last_sound_time = now;

        // Play the sound
        self.play_sound(sound_type);
        true
    }

    /// Play bell sound
    pub fn bell(&mut self) -> bool {
        self.play(SoundType::Bell)
    }

    /// Play success sound
    pub fn success(&mut self) -> bool {
        self.play(SoundType::Success)
    }

    /// Play error sound
    pub fn error(&mut self) -> bool {
        self.play(SoundType::Error)
    }

    /// Play notification sound
    pub fn notification(&mut self) -> bool {
        self.play(SoundType::Notification)
    }

    /// Play attention sound
    pub fn attention(&mut self) -> bool {
        self.play(SoundType::Attention)
    }

    /// Mute all sounds
    pub fn mute(&mut self) {
        self.muted = true;
    }

    /// Unmute sounds
    pub fn unmute(&mut self) {
        self.muted = false;
    }

    /// Toggle mute
    pub fn toggle_mute(&mut self) -> bool {
        self.muted = !self.muted;
        self.muted
    }

    /// Check if muted
    pub fn is_muted(&self) -> bool {
        self.muted
    }

    /// Update config
    pub fn set_config(&mut self, config: SoundConfig) {
        self.config = config;
    }

    /// Get config
    pub fn config(&self) -> &SoundConfig {
        &self.config
    }

    /// Set volume (0.0 - 1.0)
    pub fn set_volume(&mut self, volume: f32) {
        self.config.volume = volume.clamp(0.0, 1.0);
    }

    /// Get volume
    pub fn volume(&self) -> f32 {
        self.config.volume
    }

    /// Process terminal output for bell character
    pub fn process_output(&mut self, output: &str) -> bool {
        if output.contains('\x07') {
            return self.bell();
        }
        false
    }

    fn should_play(&self, sound_type: SoundType) -> bool {
        if !self.config.enabled || self.muted {
            return false;
        }

        match sound_type {
            SoundType::Bell => self.config.bell_enabled,
            SoundType::Success => self.config.success_enabled,
            SoundType::Error => self.config.error_enabled,
            SoundType::Notification => self.config.notification_enabled,
            SoundType::Attention => self.config.notification_enabled,
            SoundType::Custom => true,
        }
    }

    fn play_sound(&self, sound_type: SoundType) {
        // Check for custom sound
        if let Some(path) = self.config.custom_sounds.get(&sound_type) {
            self.play_audio_file(path);
            return;
        }

        // Play system sound
        match sound_type {
            SoundType::Bell => self.play_system_bell(),
            SoundType::Success => self.play_system_sound("success"),
            SoundType::Error => self.play_system_sound("error"),
            SoundType::Notification => self.play_system_sound("notification"),
            SoundType::Attention => self.play_system_sound("attention"),
            SoundType::Custom => {}
        }
    }

    #[cfg(target_os = "macos")]
    fn play_system_bell(&self) {
        // Use afplay with system sound
        let _ = std::process::Command::new("afplay")
            .args(["/System/Library/Sounds/Tink.aiff", "-v", &self.config.volume.to_string()])
            .spawn();
    }

    #[cfg(target_os = "linux")]
    fn play_system_bell(&self) {
        // Use paplay or aplay
        let _ = std::process::Command::new("paplay")
            .args(["/usr/share/sounds/freedesktop/stereo/bell.oga"])
            .spawn();
    }

    #[cfg(not(any(target_os = "macos", target_os = "linux")))]
    fn play_system_bell(&self) {
        // Fallback: print BEL character
        print!("\x07");
    }

    #[cfg(target_os = "macos")]
    fn play_system_sound(&self, name: &str) {
        let sound = match name {
            "success" => "/System/Library/Sounds/Glass.aiff",
            "error" => "/System/Library/Sounds/Basso.aiff",
            "notification" => "/System/Library/Sounds/Ping.aiff",
            "attention" => "/System/Library/Sounds/Sosumi.aiff",
            _ => "/System/Library/Sounds/Tink.aiff",
        };

        let _ = std::process::Command::new("afplay")
            .args([sound, "-v", &self.config.volume.to_string()])
            .spawn();
    }

    #[cfg(target_os = "linux")]
    fn play_system_sound(&self, name: &str) {
        let sound = match name {
            "success" => "/usr/share/sounds/freedesktop/stereo/complete.oga",
            "error" => "/usr/share/sounds/freedesktop/stereo/dialog-error.oga",
            "notification" => "/usr/share/sounds/freedesktop/stereo/message.oga",
            "attention" => "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga",
            _ => "/usr/share/sounds/freedesktop/stereo/bell.oga",
        };

        let _ = std::process::Command::new("paplay")
            .arg(sound)
            .spawn();
    }

    #[cfg(not(any(target_os = "macos", target_os = "linux")))]
    fn play_system_sound(&self, _name: &str) {
        print!("\x07");
    }

    fn play_audio_file(&self, path: &str) {
        #[cfg(target_os = "macos")]
        {
            let _ = std::process::Command::new("afplay")
                .args([path, "-v", &self.config.volume.to_string()])
                .spawn();
        }

        #[cfg(target_os = "linux")]
        {
            let _ = std::process::Command::new("paplay")
                .arg(path)
                .spawn();
        }
    }
}

impl Default for SoundManager {
    fn default() -> Self {
        Self::new()
    }
}

// =============================================================================
// GLOBAL INSTANCE
// =============================================================================

lazy_static::lazy_static! {
    static ref SOUND_MANAGER: Arc<Mutex<SoundManager>> =
        Arc::new(Mutex::new(SoundManager::new()));
}

/// Get the global sound manager
pub fn sounds() -> Arc<Mutex<SoundManager>> {
    SOUND_MANAGER.clone()
}

/// Play bell sound
pub fn bell() -> bool {
    SOUND_MANAGER.lock().unwrap().bell()
}

/// Play error sound
pub fn error() -> bool {
    SOUND_MANAGER.lock().unwrap().error()
}

/// Play success sound
pub fn success() -> bool {
    SOUND_MANAGER.lock().unwrap().success()
}

/// Play notification sound
pub fn notification() -> bool {
    SOUND_MANAGER.lock().unwrap().notification()
}

/// Mute all sounds
pub fn mute() {
    SOUND_MANAGER.lock().unwrap().mute();
}

/// Unmute sounds
pub fn unmute() {
    SOUND_MANAGER.lock().unwrap().unmute();
}

/// Process output for bell character
pub fn process_output(output: &str) -> bool {
    SOUND_MANAGER.lock().unwrap().process_output(output)
}

// =============================================================================
// TESTS
// =============================================================================

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_sound_manager_new() {
        let manager = SoundManager::new();
        assert!(manager.config.enabled);
        assert!(!manager.is_muted());
    }

    #[test]
    fn test_mute_unmute() {
        let mut manager = SoundManager::new();

        manager.mute();
        assert!(manager.is_muted());

        manager.unmute();
        assert!(!manager.is_muted());
    }

    #[test]
    fn test_toggle_mute() {
        let mut manager = SoundManager::new();

        assert!(manager.toggle_mute()); // Now muted
        assert!(!manager.toggle_mute()); // Now unmuted
    }

    #[test]
    fn test_disabled_sounds() {
        let mut manager = SoundManager::new();
        manager.config.enabled = false;

        assert!(!manager.play(SoundType::Bell));
    }

    #[test]
    fn test_muted_sounds() {
        let mut manager = SoundManager::new();
        manager.mute();

        assert!(!manager.play(SoundType::Bell));
    }

    #[test]
    fn test_rate_limiting() {
        let mut manager = SoundManager::new();
        manager.config.rate_limit = 2;

        // First two should succeed
        assert!(manager.play(SoundType::Bell));
        assert!(manager.play(SoundType::Bell));

        // Third should be rate limited
        assert!(!manager.play(SoundType::Bell));
    }

    #[test]
    fn test_process_output_bell() {
        let mut manager = SoundManager::new();

        // Contains BEL
        assert!(manager.process_output("Hello\x07World"));

        // No BEL
        assert!(!manager.process_output("Hello World"));
    }

    #[test]
    fn test_volume() {
        let mut manager = SoundManager::new();

        manager.set_volume(0.8);
        assert!((manager.volume() - 0.8).abs() < 0.001);

        // Clamp to valid range
        manager.set_volume(2.0);
        assert!((manager.volume() - 1.0).abs() < 0.001);

        manager.set_volume(-0.5);
        assert!((manager.volume() - 0.0).abs() < 0.001);
    }

    #[test]
    fn test_disabled_sound_types() {
        let mut manager = SoundManager::new();
        manager.config.success_enabled = false;

        assert!(!manager.play(SoundType::Success));
        assert!(manager.play(SoundType::Bell)); // Bell still enabled
    }
}
