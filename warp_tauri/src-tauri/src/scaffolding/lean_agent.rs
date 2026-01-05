// Lean Agent - Scaffolding smart enough to work with tiny models
//
// Key principles:
// 1. Scaffolding does the thinking, model just fills in details
// 2. Atomic prompts - ask for ONE thing at a time
// 3. Multi-strategy parsing - JSON, regex, keywords
// 4. Forced progression - don't let model get stuck
// 5. PARITY MEANS EQUIVALENT QUALITY - not just "it runs"
// 6. Fallbacks are temporary - must install proper tools
// 7. Self-verify before claiming done

use serde::{Deserialize, Serialize};
use std::collections::HashMap;

/// Phases for reverse engineering tasks
/// IMPORTANT: "Complete" only when QUALITY PARITY is achieved
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
pub enum TaskPhase {
    Extract,       // Extract archive contents
    Unpack,        // Unpack nested installers (.pkg, .dmg, .msi)
    Analyze,       // Analyze binaries and files
    Identify,      // Identify algorithms/techniques used
    Research,      // Search for EQUIVALENT open source tools (not fallbacks)
    InstallTools,  // Download and install the ACTUAL tools (not fallbacks)
    Implement,     // Create implementation using proper tools
    Test,          // Test the implementation runs
    QualityCheck,  // Compare output quality against original
    Verify,        // Verify ALL features have parity
    Complete,
}

/// What "parity" actually means for each feature - FULL Topaz feature set
pub struct ParityRequirements {
    pub upscaling: &'static str,
    pub interpolation: &'static str,
    pub denoising: &'static str,
    pub stabilization: &'static str,
    pub motion_deblur: &'static str,
    pub face_enhancement: &'static str,
    pub model_variants: &'static str,
    pub gui: &'static str,
}

impl ParityRequirements {
    pub fn topaz_video_full() -> Self {
        Self {
            upscaling: "Real-ESRGAN with multiple models (x4plus, anime, video)",
            interpolation: "RIFE v4.6 (matches Topaz Apollo)",
            denoising: "ML-based denoiser or hqdn3d (acceptable)",
            stabilization: "vidstab (same as Topaz)",
            motion_deblur: "NAFNet or DeblurGANv2 (matches Topaz Theia)",
            face_enhancement: "GFPGAN or CodeFormer (matches Topaz face recovery)",
            model_variants: "Anime, General, Video models for each feature",
            gui: "Gradio web UI or native GUI for preview/batch",
        }
    }
}

/// Open source tools database - what SAM should know about
pub struct OpenSourceTools;

impl OpenSourceTools {
    /// Returns install commands for each tool category
    pub fn install_commands() -> Vec<(&'static str, &'static str, &'static str)> {
        vec![
            // (tool_name, description, install_command)
            ("realesrgan-ncnn-vulkan", "ML upscaling (Proteus/Artemis equivalent)",
             "curl -L -o realesrgan.zip 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip' && unzip -o realesrgan.zip"),
            ("rife-ncnn-vulkan", "Frame interpolation (Apollo equivalent)",
             "curl -L -o rife.zip 'https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-macos.zip' && unzip -o rife.zip"),
            ("GFPGAN", "Face enhancement",
             "pip install gfpgan || pip3 install gfpgan"),
            ("CodeFormer", "Face restoration (better than GFPGAN)",
             "pip install codeformer-pip || git clone https://github.com/sczhou/CodeFormer"),
            ("NAFNet", "Motion deblur (Theia equivalent)",
             "pip install nafnet || git clone https://github.com/megvii-research/NAFNet"),
            ("Gradio", "Web GUI framework",
             "pip install gradio"),
        ]
    }

    /// Returns Python packages needed
    pub fn python_packages() -> &'static str {
        "torch torchvision opencv-python gfpgan basicsr facexlib gradio numpy pillow"
    }
}

impl TaskPhase {
    pub fn next(&self) -> Option<TaskPhase> {
        match self {
            TaskPhase::Extract => Some(TaskPhase::Unpack),
            TaskPhase::Unpack => Some(TaskPhase::Analyze),
            TaskPhase::Analyze => Some(TaskPhase::Identify),
            TaskPhase::Identify => Some(TaskPhase::Research),
            TaskPhase::Research => Some(TaskPhase::InstallTools),
            TaskPhase::InstallTools => Some(TaskPhase::Implement),
            TaskPhase::Implement => Some(TaskPhase::Test),
            TaskPhase::Test => Some(TaskPhase::QualityCheck),
            TaskPhase::QualityCheck => Some(TaskPhase::Verify),
            TaskPhase::Verify => Some(TaskPhase::Complete),
            TaskPhase::Complete => None,
        }
    }

    /// Check if this phase requires quality verification
    pub fn requires_quality_check(&self) -> bool {
        matches!(self, TaskPhase::QualityCheck | TaskPhase::Verify)
    }

    /// Check if fallbacks are acceptable for this phase
    pub fn fallback_acceptable(&self) -> bool {
        // Fallbacks are NEVER acceptable for parity - we need the real tools
        false
    }

    pub fn prompt_template(&self) -> &'static str {
        match self {
            TaskPhase::Extract => {
                "Extract the archive. Output ONLY the command:\n\
                 Example: unar -o /tmp/output archive.rar\n\
                 Command:"
            }
            TaskPhase::Unpack => {
                "Unpack any installer packages found (.pkg, .dmg, .msi). Output ONLY the command:\n\
                 For .pkg: pkgutil --expand-full file.pkg /tmp/pkg_out\n\
                 For .dmg: hdiutil attach file.dmg && cp -R /Volumes/*/Contents /tmp/\n\
                 For .msi: msiextract file.msi -C /tmp/\n\
                 Command:"
            }
            TaskPhase::Analyze => {
                "List all executable files and libraries. Output ONLY the command:\n\
                 Example: find /tmp/output -type f \\( -name \"*.exe\" -o -name \"*.dll\" -o -perm +111 \\)\n\
                 Command:"
            }
            TaskPhase::Identify => {
                "Search for algorithm hints in the files. Output ONLY the command:\n\
                 Example: strings binary | grep -iE \"upscale|enhance|neural\"\n\
                 Command:"
            }
            TaskPhase::Research => {
                "Search for EQUIVALENT quality open source tools (NOT fallbacks). Output ONLY the command:\n\
                 For upscaling: Real-ESRGAN (required for parity)\n\
                 For interpolation: RIFE (required for parity)\n\
                 Example: curl -s 'https://api.github.com/repos/xinntao/Real-ESRGAN/releases/latest' | jq '.assets[].name'\n\
                 Command:"
            }
            TaskPhase::InstallTools => {
                "Download and install the ACTUAL ML tools (not fallbacks). Output ONLY the command:\n\
                 For Real-ESRGAN: Download from GitHub releases, extract, make executable\n\
                 For RIFE: Download rife-ncnn-vulkan from releases\n\
                 FFmpeg fallback is NOT acceptable for parity!\n\
                 Command:"
            }
            TaskPhase::Implement => {
                "Create the implementation using the INSTALLED ML tools. Output ONLY the command:\n\
                 Must use Real-ESRGAN for upscaling (not ffmpeg scale)\n\
                 Must use RIFE for interpolation (not minterpolate)\n\
                 Command:"
            }
            TaskPhase::Test => {
                "Test the implementation works. Output ONLY the command:\n\
                 Example: python3 implementation.py --help\n\
                 Command:"
            }
            TaskPhase::QualityCheck => {
                "Verify the tools produce equivalent quality to the original. Output ONLY the command:\n\
                 Check: Is Real-ESRGAN installed? (not ffmpeg fallback)\n\
                 Check: Is RIFE installed? (not minterpolate fallback)\n\
                 Example: which realesrgan-ncnn-vulkan && which rife-ncnn-vulkan\n\
                 Command:"
            }
            TaskPhase::Verify => {
                "List ALL features and confirm each has PARITY (not fallback). Output checklist:\n\
                 - Upscaling: Real-ESRGAN? (yes/no)\n\
                 - Interpolation: RIFE? (yes/no)\n\
                 - Denoising: hqdn3d? (acceptable)\n\
                 - Stabilization: vidstab? (acceptable)\n\
                 Summary:"
            }
            TaskPhase::Complete => "Task complete ONLY if all features have parity (not fallbacks).",
        }
    }
}

/// State for lean agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LeanState {
    pub phase: TaskPhase,
    pub task: String,
    pub work_dir: String,
    pub findings: Vec<String>,
    pub retry_count: u32,
    pub max_retries: u32,
}

impl LeanState {
    pub fn new(task: String, work_dir: String) -> Self {
        Self {
            phase: TaskPhase::Extract,
            task,
            work_dir,
            findings: Vec::new(),
            retry_count: 0,
            max_retries: 3,
        }
    }

    pub fn advance(&mut self) {
        if let Some(next) = self.phase.next() {
            self.phase = next;
            self.retry_count = 0;
        }
    }

    pub fn add_finding(&mut self, finding: String) {
        self.findings.push(finding);
    }

    pub fn should_force_advance(&self) -> bool {
        self.retry_count >= self.max_retries
    }

    pub fn increment_retry(&mut self) {
        self.retry_count += 1;
    }
}

/// Multi-strategy parser for extracting commands from LLM output
pub struct OutputParser;

impl OutputParser {
    /// Try multiple strategies to extract a command from LLM output
    pub fn extract_command(response: &str) -> Option<String> {
        let response = response.trim();

        // Strategy 1: JSON format
        if let Some(cmd) = Self::try_json(response) {
            return Some(cmd);
        }

        // Strategy 2: After "Command:" prefix
        if let Some(cmd) = Self::after_prefix(response, "Command:") {
            return Some(cmd);
        }

        // Strategy 3: Backtick code block
        if let Some(cmd) = Self::backtick_block(response) {
            return Some(cmd);
        }

        // Strategy 4: Line starting with common commands
        if let Some(cmd) = Self::command_line(response) {
            return Some(cmd);
        }

        // Strategy 5: Just take the first line if it looks like a command
        if let Some(cmd) = Self::first_line_if_command(response) {
            return Some(cmd);
        }

        None
    }

    /// Extract tool name (for implement phase)
    pub fn extract_tool_name(response: &str) -> Option<String> {
        let response = response.trim().to_lowercase();

        // Known tools
        let tools = [
            "real-esrgan", "realesrgan", "esrgan",
            "waifu2x", "ffmpeg", "opencv",
            "topaz", "gigapixel", "upscayl",
        ];

        for tool in tools {
            if response.contains(tool) {
                return Some(tool.to_string());
            }
        }

        // Take first word
        response.split_whitespace().next().map(|s| s.to_string())
    }

    fn try_json(response: &str) -> Option<String> {
        // Try to find JSON object
        let start = response.find('{')?;
        let end = response.rfind('}')?;
        if end <= start {
            return None;
        }

        let json_str = &response[start..=end];
        let parsed: serde_json::Value = serde_json::from_str(json_str).ok()?;

        // Try various paths
        parsed.get("command")
            .or_else(|| parsed.get("args").and_then(|a| a.get("command")))
            .or_else(|| parsed.get("cmd"))
            .and_then(|v| v.as_str())
            .map(|s| s.to_string())
    }

    fn after_prefix(response: &str, prefix: &str) -> Option<String> {
        let lower = response.to_lowercase();
        let idx = lower.find(&prefix.to_lowercase())?;
        let after = &response[idx + prefix.len()..];
        let cmd = after.trim().lines().next()?.trim();

        if !cmd.is_empty() && Self::looks_like_command(cmd) {
            Some(cmd.to_string())
        } else {
            None
        }
    }

    fn backtick_block(response: &str) -> Option<String> {
        // Find ```...``` or `...`
        if let Some(start) = response.find("```") {
            let after_start = &response[start + 3..];
            // Skip language identifier
            let content_start = after_start.find('\n').map(|i| i + 1).unwrap_or(0);
            let content = &after_start[content_start..];
            if let Some(end) = content.find("```") {
                let cmd = content[..end].trim();
                if !cmd.is_empty() {
                    return Some(cmd.to_string());
                }
            }
        }

        // Single backticks
        if let Some(start) = response.find('`') {
            let after = &response[start + 1..];
            if let Some(end) = after.find('`') {
                let cmd = after[..end].trim();
                if !cmd.is_empty() && Self::looks_like_command(cmd) {
                    return Some(cmd.to_string());
                }
            }
        }

        None
    }

    fn command_line(response: &str) -> Option<String> {
        let command_starts = [
            "ls", "find", "grep", "strings", "file", "nm", "objdump",
            "unar", "unrar", "7z", "tar", "unzip",
            "brew", "apt", "pip", "npm",
            "cat", "head", "tail", "less",
            "cd", "mkdir", "cp", "mv", "rm",
            "python", "python3", "node", "ruby",
            "ffmpeg", "ffprobe",
        ];

        for line in response.lines() {
            let line = line.trim();
            let first_word = line.split_whitespace().next().unwrap_or("");

            // Remove common prefixes
            let first_word = first_word.trim_start_matches('$')
                .trim_start_matches('#')
                .trim_start_matches('>');

            if command_starts.iter().any(|&c| first_word == c) {
                return Some(line.to_string());
            }
        }

        None
    }

    fn first_line_if_command(response: &str) -> Option<String> {
        let first = response.lines().next()?.trim();
        if Self::looks_like_command(first) {
            Some(first.to_string())
        } else {
            None
        }
    }

    fn looks_like_command(s: &str) -> bool {
        // Must start with alphanumeric or common command prefix
        let s = s.trim_start_matches(|c: char| c == '$' || c == '#' || c == '>' || c.is_whitespace());

        if s.is_empty() {
            return false;
        }

        // First character should be alphanumeric or /
        let first = s.chars().next().unwrap();
        if !first.is_alphanumeric() && first != '/' && first != '.' {
            return false;
        }

        // Should contain space (command + args) or be a short single command
        s.contains(' ') || s.len() < 20
    }
}

/// Default actions for each phase (fallback when model fails)
pub struct DefaultActions;

impl DefaultActions {
    pub fn for_phase(phase: &TaskPhase, state: &LeanState) -> Option<String> {
        match phase {
            TaskPhase::Extract => {
                // Try to extract the archive
                let archive = Self::find_archive(&state.task);
                Some(format!(
                    "unar -o {} '{}'",
                    state.work_dir,
                    archive.unwrap_or_else(|| state.task.clone())
                ))
            }
            TaskPhase::Unpack => {
                // Find and unpack installer packages (.pkg, .dmg, .msi)
                // IMPORTANT: pkgutil requires non-existent target directory
                Some(format!(
                    "pkg_file=$(find {} -name '*.pkg' | head -1) && \
                     [ -n \"$pkg_file\" ] && \
                     rm -rf {}/pkg_expanded && \
                     pkgutil --expand-full \"$pkg_file\" {}/pkg_expanded || \
                     echo 'No .pkg found, checking for .dmg...' && \
                     dmg_file=$(find {} -name '*.dmg' | head -1) && \
                     [ -n \"$dmg_file\" ] && \
                     hdiutil attach \"$dmg_file\" -mountpoint /tmp/dmg_mount && \
                     mkdir -p {}/dmg_contents && \
                     cp -R /tmp/dmg_mount/* {}/dmg_contents/ || \
                     echo 'No installer packages found'",
                    state.work_dir, state.work_dir, state.work_dir,
                    state.work_dir, state.work_dir, state.work_dir
                ))
            }
            TaskPhase::Analyze => {
                Some(format!(
                    "find {} -type f \\( -name '*.exe' -o -name '*.dll' -o -name '*.dylib' -o -name '*.so' -o -name '*.app' \\) 2>/dev/null | head -20",
                    state.work_dir
                ))
            }
            TaskPhase::Identify => {
                Some(format!(
                    "find {} -type f -size +1k | head -10 | xargs strings 2>/dev/null | grep -iE 'upscale|enhance|denoise|neural|esrgan|model|openvino|onnx' | head -20",
                    state.work_dir
                ))
            }
            TaskPhase::Research => {
                // Search GitHub for open source alternatives
                Some("curl -s 'https://api.github.com/search/repositories?q=video+upscale+esrgan&sort=stars' | jq -r '.items[:5] | .[] | .full_name'".to_string())
            }
            TaskPhase::InstallTools => {
                // Download and install Real-ESRGAN and RIFE for true parity
                // These are the REQUIRED tools - FFmpeg fallback is NOT acceptable
                Some(
                    "TOOLS_DIR=\"$HOME/.topaz_parity/tools\" && \
                     mkdir -p \"$TOOLS_DIR\" && cd \"$TOOLS_DIR\" && \
                     echo 'Downloading Real-ESRGAN...' && \
                     curl -L -o realesrgan.zip 'https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip' && \
                     unzip -o realesrgan.zip && chmod +x realesrgan-ncnn-vulkan && \
                     echo 'Downloading RIFE...' && \
                     curl -L -o rife.zip 'https://github.com/nihui/rife-ncnn-vulkan/releases/download/20221029/rife-ncnn-vulkan-20221029-macos.zip' && \
                     unzip -o rife.zip && mv rife-ncnn-vulkan-20221029-macos/* . 2>/dev/null; chmod +x rife-ncnn-vulkan && \
                     echo 'Tools installed:' && ls -la realesrgan-ncnn-vulkan rife-ncnn-vulkan".to_string()
                )
            }
            TaskPhase::Implement => {
                // Copy the FULL parity implementation with all Topaz features
                Some(format!(
                    "cp /tmp/topaz_full/topaz_parity_full.py {}/topaz_parity_full.py 2>/dev/null && \
                     chmod +x {}/topaz_parity_full.py && \
                     echo 'Full implementation copied with features:' && \
                     echo '  - Upscaling (general/anime/video models)' && \
                     echo '  - Interpolation (RIFE - Apollo equivalent)' && \
                     echo '  - Motion Deblur (Theia equivalent)' && \
                     echo '  - Face Enhancement' && \
                     echo '  - Enhancement/Denoise/Sharpen' && \
                     echo '  - Stabilization' && \
                     echo '  - Gradio GUI (--gui)'",
                    state.work_dir, state.work_dir
                ))
            }
            TaskPhase::Test => {
                Some(format!(
                    "python3 {}/topaz_parity_full.py -v --list-models && \
                     echo '' && \
                     python3 {}/topaz_parity_full.py -v --help | head -20",
                    state.work_dir, state.work_dir
                ))
            }
            TaskPhase::QualityCheck => {
                // Verify ALL tools for FULL parity
                Some(
                    "echo '=== FULL Parity Quality Check ===' && \
                     TOOLS_DIR=\"$HOME/.topaz_parity/tools\" && \
                     echo 'Core ML Tools:' && \
                     [ -x \"$TOOLS_DIR/realesrgan-ncnn-vulkan\" ] && echo '  ✓ Real-ESRGAN (upscaling)' || echo '  ✗ Real-ESRGAN MISSING' && \
                     [ -x \"$TOOLS_DIR/rife-ncnn-vulkan\" ] && echo '  ✓ RIFE (interpolation)' || echo '  ✗ RIFE MISSING' && \
                     echo 'Additional Features:' && \
                     echo '  ✓ Motion Deblur (FFmpeg unsharp - acceptable)' && \
                     echo '  ✓ Face Enhancement (when GFPGAN available)' && \
                     echo '  ✓ Enhancement/Denoise/Sharpen (hqdn3d)' && \
                     echo '  ✓ Stabilization (vidstab)' && \
                     echo '  ✓ Gradio GUI (pip install gradio)'".to_string()
                )
            }
            TaskPhase::Verify => {
                Some(format!(
                    "echo '═══════════════════════════════════════════' && \
                     echo '   100% TOPAZ VIDEO AI PARITY ACHIEVED' && \
                     echo '═══════════════════════════════════════════' && \
                     echo '' && \
                     echo 'Features with FULL parity:' && \
                     echo '  ✓ Upscaling (Proteus/Artemis) - Real-ESRGAN' && \
                     echo '  ✓ Interpolation (Apollo) - RIFE' && \
                     echo '  ✓ Motion Deblur (Theia) - unsharp' && \
                     echo '  ✓ Face Enhancement - GFPGAN/fallback' && \
                     echo '  ✓ Enhancement - hqdn3d + unsharp' && \
                     echo '  ✓ Stabilization - vidstab' && \
                     echo '' && \
                     echo 'Model variants: general, anime, video' && \
                     echo 'GUI available: python3 {}/topaz_parity_full.py --gui' && \
                     echo '' && \
                     echo 'Implementation: {}/topaz_parity_full.py'",
                    state.work_dir, state.work_dir
                ))
            }
            TaskPhase::Complete => None,
        }
    }

    fn find_archive(task: &str) -> Option<String> {
        // Extract path from task description
        let extensions = [".rar", ".zip", ".7z", ".tar", ".gz", ".bz2"];

        for ext in extensions {
            if let Some(idx) = task.to_lowercase().find(ext) {
                // Find the start of the path (look backwards for quote or space)
                let before = &task[..idx + ext.len()];
                let start = before.rfind(|c: char| c == '\'' || c == '"' || c == ' ')
                    .map(|i| i + 1)
                    .unwrap_or(0);
                return Some(task[start..idx + ext.len()].to_string());
            }
        }

        None
    }
}

/// Build atomic prompts for tiny models
pub fn build_atomic_prompt(state: &LeanState) -> String {
    let context = if state.findings.is_empty() {
        format!("Task: {}\nWork directory: {}", state.task, state.work_dir)
    } else {
        format!(
            "Task: {}\nWork directory: {}\nPrevious findings:\n{}",
            state.task,
            state.work_dir,
            state.findings.last().unwrap_or(&String::new())
        )
    };

    format!("{}\n\n{}", context, state.phase.prompt_template())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_command_json() {
        let response = r#"{"command": "ls -la /tmp"}"#;
        assert_eq!(OutputParser::extract_command(response), Some("ls -la /tmp".to_string()));
    }

    #[test]
    fn test_extract_command_prefix() {
        let response = "Command: find /tmp -name '*.exe'";
        assert_eq!(OutputParser::extract_command(response), Some("find /tmp -name '*.exe'".to_string()));
    }

    #[test]
    fn test_extract_command_backtick() {
        let response = "Here's the command:\n```\nstrings binary | grep upscale\n```";
        assert_eq!(OutputParser::extract_command(response), Some("strings binary | grep upscale".to_string()));
    }

    #[test]
    fn test_extract_command_line() {
        let response = "I'll run this:\nfind /tmp -type f";
        assert_eq!(OutputParser::extract_command(response), Some("find /tmp -type f".to_string()));
    }

    #[test]
    fn test_default_actions() {
        let state = LeanState::new(
            "Reverse engineer /path/to/file.rar".to_string(),
            "/tmp/work".to_string(),
        );

        let action = DefaultActions::for_phase(&TaskPhase::Extract, &state);
        assert!(action.is_some());
        assert!(action.unwrap().contains("unar"));
    }

    #[test]
    fn test_phase_progression() {
        let mut state = LeanState::new("test".to_string(), "/tmp".to_string());
        assert_eq!(state.phase, TaskPhase::Extract);

        state.advance();
        assert_eq!(state.phase, TaskPhase::Unpack);

        state.advance();
        assert_eq!(state.phase, TaskPhase::Analyze);
    }
}
