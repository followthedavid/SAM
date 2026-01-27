#!/usr/bin/env osascript -l JavaScript
/**
 * SAM Automation - JavaScript for Automation (JXA) Test Helpers
 *
 * Usage:
 *   osascript sam_automation.js focus
 *   osascript sam_automation.js click 100 200
 *   osascript sam_automation.js getWindows
 *   osascript sam_automation.js inspectUI
 */

const DEBUG_PORT = 9998;
const DEBUG_URL = `http://localhost:${DEBUG_PORT}`;

// Get System Events for UI automation
const SystemEvents = Application("System Events");
SystemEvents.includeStandardAdditions = true;

// Helper to find SAM process
function getSAMProcess() {
    try {
        return SystemEvents.processes.byName("SAM");
    } catch (e) {
        throw new Error("SAM is not running");
    }
}

// Focus SAM window
function focus() {
    const sam = getSAMProcess();
    sam.frontmost = true;
    return { success: true, message: "SAM focused" };
}

// Get window information
function getWindows() {
    const sam = getSAMProcess();
    const windows = [];

    sam.windows().forEach(win => {
        windows.push({
            name: win.name(),
            position: win.position(),
            size: win.size(),
            focused: win.focused ? win.focused() : null
        });
    });

    return windows;
}

// Click at coordinates (relative to screen)
function click(x, y) {
    const sam = getSAMProcess();
    sam.frontmost = true;

    // Use cliclick if available, otherwise use AppleScript workaround
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;

    try {
        app.doShellScript(`cliclick c:${x},${y}`);
        return { success: true, x, y };
    } catch (e) {
        // Fallback: use System Events click
        // Note: This requires accessibility permissions
        return { success: false, error: "cliclick not installed. Install with: brew install cliclick" };
    }
}

// Type text
function typeText(text) {
    const sam = getSAMProcess();
    sam.frontmost = true;

    SystemEvents.keystroke(text);
    return { success: true, typed: text };
}

// Press key (return, tab, etc)
function pressKey(key) {
    const sam = getSAMProcess();
    sam.frontmost = true;

    const keyCodes = {
        "return": 36,
        "enter": 36,
        "tab": 48,
        "escape": 53,
        "space": 49,
        "delete": 51,
        "up": 126,
        "down": 125,
        "left": 123,
        "right": 124
    };

    const code = keyCodes[key.toLowerCase()];
    if (code) {
        SystemEvents.keyCode(code);
        return { success: true, key };
    } else {
        return { success: false, error: `Unknown key: ${key}` };
    }
}

// Inspect UI elements (basic accessibility dump)
function inspectUI() {
    const sam = getSAMProcess();
    const elements = [];

    sam.windows().forEach(win => {
        const winInfo = {
            type: "window",
            name: win.name(),
            position: win.position(),
            size: win.size(),
            children: []
        };

        // Try to get UI elements
        try {
            const contents = win.entireContents();
            contents.forEach(elem => {
                try {
                    winInfo.children.push({
                        class: elem.class(),
                        name: elem.name ? elem.name() : null,
                        role: elem.role ? elem.role() : null,
                        position: elem.position ? elem.position() : null
                    });
                } catch (e) {
                    // Skip elements we can't inspect
                }
            });
        } catch (e) {
            winInfo.error = "Could not enumerate UI elements";
        }

        elements.push(winInfo);
    });

    return elements;
}

// Query debug server
function queryDebug(endpoint) {
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;

    try {
        const result = app.doShellScript(`curl -s ${DEBUG_URL}${endpoint}`);
        return JSON.parse(result);
    } catch (e) {
        return { error: e.message };
    }
}

// Get app state from debug server
function getState() {
    return queryDebug("/debug/state");
}

// Get Ollama status
function getOllama() {
    return queryDebug("/debug/ollama");
}

// Warm models
function warmModels() {
    const app = Application.currentApplication();
    app.includeStandardAdditions = true;

    try {
        const result = app.doShellScript(`curl -s -X POST ${DEBUG_URL}/debug/warm`);
        return JSON.parse(result);
    } catch (e) {
        return { error: e.message };
    }
}

// Run a test sequence
function runTest(testName) {
    const tests = {
        "startup": () => {
            const results = [];

            // Check debug server
            const state = getState();
            results.push({ test: "debug_server", passed: !state.error, data: state });

            // Check Ollama
            const ollama = getOllama();
            results.push({ test: "ollama", passed: !ollama.error && ollama.loaded_count > 0, data: ollama });

            // Check window
            const windows = getWindows();
            results.push({ test: "window_exists", passed: windows.length > 0, data: windows });

            return results;
        },
        "chat": () => {
            const results = [];

            // Focus window
            focus();
            results.push({ test: "focus", passed: true });

            // TODO: Find chat input and type
            // This requires more detailed accessibility inspection

            return results;
        }
    };

    if (tests[testName]) {
        return tests[testName]();
    } else {
        return { error: `Unknown test: ${testName}`, available: Object.keys(tests) };
    }
}

// Main entry point
function run(argv) {
    const command = argv[0] || "help";
    const args = argv.slice(1);

    const commands = {
        "focus": () => focus(),
        "windows": () => getWindows(),
        "click": () => click(parseInt(args[0]) || 0, parseInt(args[1]) || 0),
        "type": () => typeText(args.join(" ")),
        "key": () => pressKey(args[0] || "return"),
        "inspect": () => inspectUI(),
        "state": () => getState(),
        "ollama": () => getOllama(),
        "warm": () => warmModels(),
        "test": () => runTest(args[0] || "startup"),
        "help": () => ({
            commands: [
                "focus - Bring SAM window to front",
                "windows - Get window information",
                "click X Y - Click at coordinates",
                "type TEXT - Type text",
                "key KEYNAME - Press key (return, tab, escape, etc)",
                "inspect - Inspect UI elements",
                "state - Get app state (debug server)",
                "ollama - Get Ollama status",
                "warm - Warm models",
                "test [name] - Run test sequence (startup, chat)"
            ]
        })
    };

    if (commands[command]) {
        const result = commands[command]();
        return JSON.stringify(result, null, 2);
    } else {
        return JSON.stringify({ error: `Unknown command: ${command}`, help: commands.help() }, null, 2);
    }
}
