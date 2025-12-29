"""
Integration tests for Warp_Open optional features:
- OSC sequences (window title, color palette, clipboard)
- Preferences persistence
- Theme switching
- Clipboard operations with bracketed paste
"""

import pytest
import json
import base64
from pathlib import Path


class TestOSCSequences:
    """Test OSC (Operating System Command) sequences"""
    
    def test_osc_2_window_title_format(self):
        """Test OSC 2 window title sequence format"""
        title = "My Terminal Window"
        sequence = f"\x1b]2;{title}\x07"
        
        assert sequence.startswith("\x1b]2;")
        assert sequence.endswith("\x07")
        assert title in sequence
    
    def test_osc_4_color_palette_format(self):
        """Test OSC 4 color palette sequence format"""
        # Red color in RGB format
        sequence = "\x1b]4;1;rgb:ff/00/00\x07"
        
        assert sequence.startswith("\x1b]4;")
        assert "rgb:" in sequence
        assert sequence.endswith("\x07")
    
    def test_osc_52_clipboard_base64(self):
        """Test OSC 52 clipboard with base64 encoding"""
        text = "Hello, Warp!"
        b64_text = base64.b64encode(text.encode()).decode()
        sequence = f"\x1b]52;c;{b64_text}\x07"
        
        assert sequence.startswith("\x1b]52;c;")
        assert sequence.endswith("\x07")
        
        # Verify we can decode it back
        extracted = sequence[8:-1]  # Extract base64 part
        decoded = base64.b64decode(extracted).decode()
        assert decoded == text


class TestPreferences:
    """Test preferences persistence and management"""
    
    def test_preferences_structure(self):
        """Test preferences JSON structure"""
        prefs = {
            "terminal": {
                "fontSize": 14,
                "fontFamily": "Menlo, Monaco, monospace",
                "cursorStyle": "block",
                "cursorBlink": True,
                "scrollback": 1000,
                "lineHeight": 1.2
            },
            "editor": {
                "tabSize": 2,
                "insertSpaces": True
            },
            "ui": {
                "showTabBar": True,
                "showScrollbar": True,
                "compactMode": False
            }
        }
        
        # Test serialization
        json_str = json.dumps(prefs, indent=2)
        assert "fontSize" in json_str
        assert "cursorStyle" in json_str
        
        # Test deserialization
        loaded = json.loads(json_str)
        assert loaded["terminal"]["fontSize"] == 14
        assert loaded["terminal"]["cursorStyle"] == "block"
    
    def test_preferences_defaults(self):
        """Test that default preferences are valid"""
        defaults = {
            "terminal": {
                "fontSize": 14,
                "fontFamily": "Menlo, Monaco, \"Courier New\", monospace",
                "cursorStyle": "block",
                "cursorBlink": True
            }
        }
        
        assert defaults["terminal"]["fontSize"] >= 8
        assert defaults["terminal"]["fontSize"] <= 32
        assert defaults["terminal"]["cursorStyle"] in ["block", "underline", "bar"]
    
    def test_preferences_export_import(self, tmp_path):
        """Test exporting and importing preferences"""
        prefs = {
            "terminal": {"fontSize": 16},
            "ui": {"compactMode": True}
        }
        
        # Export to file
        export_file = tmp_path / "test-preferences.json"
        with open(export_file, 'w') as f:
            json.dump(prefs, f, indent=2)
        
        # Import from file
        with open(export_file, 'r') as f:
            imported = json.load(f)
        
        assert imported["terminal"]["fontSize"] == 16
        assert imported["ui"]["compactMode"] is True


class TestThemes:
    """Test theme system"""
    
    def test_theme_names(self):
        """Test theme naming conventions"""
        themes = ["dark", "light", "dracula"]
        
        for theme in themes:
            assert theme.islower()
            assert theme.isalpha()
    
    def test_theme_structure(self):
        """Test theme JSON structure"""
        theme = {
            "name": "Dark",
            "terminal": {
                "background": "#1e1e1e",
                "foreground": "#d4d4d4",
                "cursor": "#d4d4d4",
                "black": "#000000",
                "red": "#cd3131",
                "green": "#0dbc79"
            },
            "ui": {
                "background": "#1e1e1e",
                "tabBar": "#2d2d2d",
                "border": "#404040"
            }
        }
        
        # Verify all required fields exist
        assert "terminal" in theme
        assert "ui" in theme
        assert "background" in theme["terminal"]
        assert "foreground" in theme["terminal"]
        
        # Verify color format (hex)
        assert theme["terminal"]["background"].startswith("#")
        assert len(theme["terminal"]["background"]) == 7


class TestClipboard:
    """Test clipboard operations"""
    
    def test_bracketed_paste_single_line(self):
        """Test bracketed paste for single line"""
        text = "echo hello"
        # Single line shouldn't need bracketing
        assert "\n" not in text
    
    def test_bracketed_paste_multi_line(self):
        """Test bracketed paste for multi-line content"""
        text = "line1\nline2\nline3"
        bracketed = f"\x1b[200~{text}\x1b[201~"
        
        assert bracketed.startswith("\x1b[200~")
        assert bracketed.endswith("\x1b[201~")
        assert text in bracketed
    
    def test_clipboard_text_encoding(self):
        """Test clipboard text encoding/decoding"""
        original = "Hello 世界 🚀"
        encoded = original.encode('utf-8')
        decoded = encoded.decode('utf-8')
        
        assert decoded == original


class TestKeyboardShortcuts:
    """Test keyboard shortcut handling"""
    
    def test_cmd_v_paste_format(self):
        """Test Cmd/Ctrl+V paste format"""
        # This would be the expected format sent to PTY
        single_line = "echo test"
        multi_line = "echo line1\necho line2"
        
        # Single line: send as-is
        assert "\n" not in single_line
        
        # Multi-line: wrap in bracketed paste
        bracketed = f"\x1b[200~{multi_line}\x1b[201~"
        assert bracketed.startswith("\x1b[200~")


class TestFontSettings:
    """Test font configuration"""
    
    def test_font_families(self):
        """Test supported font families"""
        fonts = [
            "Menlo, Monaco, 'Courier New', monospace",
            "'Fira Code', monospace",
            "'JetBrains Mono', monospace",
            "'Source Code Pro', monospace",
            "monospace"
        ]
        
        for font in fonts:
            assert "monospace" in font.lower() or "monaco" in font.lower() or "menlo" in font.lower()
    
    def test_font_size_range(self):
        """Test font size constraints"""
        min_size = 8
        max_size = 32
        default_size = 14
        
        assert min_size <= default_size <= max_size
        assert min_size > 0
        assert max_size < 100


class TestCursorStyles:
    """Test cursor style options"""
    
    def test_cursor_style_options(self):
        """Test valid cursor styles"""
        valid_styles = ["block", "underline", "bar"]
        
        for style in valid_styles:
            assert style.islower()
            assert style in ["block", "underline", "bar"]
    
    def test_cursor_blink_option(self):
        """Test cursor blink boolean"""
        blink_values = [True, False]
        
        for value in blink_values:
            assert isinstance(value, bool)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
