#!/usr/bin/env python3
"""
SAM Voice Preprocessor - Text preprocessing for TTS.

Cleans and prepares text for optimal text-to-speech synthesis.

Features:
- Remove markdown formatting
- Expand abbreviations (API -> A P I)
- Convert numbers to words
- Handle URLs (strip or read domain)
- Handle code blocks (skip or describe)
- Handle emojis (skip or describe)
- Normalize whitespace
- Split into sentences

Usage:
    from voice.voice_preprocessor import VoicePreprocessor

    preprocessor = VoicePreprocessor()
    clean_text = preprocessor.clean_text("Hello **world**! API is version 1.23")
    sentences = preprocessor.split_sentences(clean_text)
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from pathlib import Path


class URLHandling(Enum):
    """How to handle URLs in text."""
    STRIP = "strip"           # Remove entirely
    DOMAIN = "domain"         # Read just the domain
    FULL = "full"             # Read full URL (rarely wanted)
    DESCRIBE = "describe"     # Say "a link to [domain]"


class CodeBlockHandling(Enum):
    """How to handle code blocks in text."""
    SKIP = "skip"             # Remove code blocks
    DESCRIBE = "describe"     # Say "code block containing..."
    BRIEF = "brief"           # Say "code block" only
    READ = "read"             # Read code (can be awkward)


class EmojiHandling(Enum):
    """How to handle emojis in text."""
    SKIP = "skip"             # Remove emojis
    DESCRIBE = "describe"     # Convert to text description
    KEEP = "keep"             # Keep (TTS may skip or mispronounce)


@dataclass
class PreprocessorConfig:
    """Configuration for text preprocessing."""

    # Markdown handling
    remove_bold: bool = True
    remove_italic: bool = True
    remove_strikethrough: bool = True
    remove_code_inline: bool = True
    remove_headers: bool = True

    # URL handling
    url_handling: URLHandling = URLHandling.DOMAIN

    # Code block handling
    code_block_handling: CodeBlockHandling = CodeBlockHandling.DESCRIBE

    # Emoji handling
    emoji_handling: EmojiHandling = EmojiHandling.DESCRIBE

    # Abbreviation expansion
    expand_abbreviations: bool = True
    custom_abbreviations: dict = field(default_factory=dict)

    # Number handling
    expand_numbers: bool = True
    max_number_digits: int = 15  # Numbers with more digits than this are kept as-is

    # Whitespace
    normalize_whitespace: bool = True
    collapse_newlines: bool = True

    # Sentence handling
    min_sentence_length: int = 3  # Minimum chars for a sentence
    max_sentence_length: int = 500  # Split long sentences

    # Additional cleaning
    remove_parenthetical_refs: bool = True  # Remove (1), [2], etc.
    clean_quotes: bool = True  # Normalize quote characters


# Common tech abbreviations
DEFAULT_ABBREVIATIONS = {
    # Technology
    "API": "A P I",
    "APIs": "A P I s",
    "URL": "U R L",
    "URLs": "U R L s",
    "HTTP": "H T T P",
    "HTTPS": "H T T P S",
    "HTML": "H T M L",
    "CSS": "C S S",
    "JSON": "J SON",
    "XML": "X M L",
    "SQL": "sequel",
    "NoSQL": "no sequel",
    "UI": "U I",
    "UX": "U X",
    "AI": "A I",
    "ML": "M L",
    "MLX": "M L X",
    "NLP": "N L P",
    "GPU": "G P U",
    "CPU": "C P U",
    "RAM": "ram",
    "ROM": "rom",
    "SSD": "S S D",
    "HDD": "H D D",
    "USB": "U S B",
    "VPN": "V P N",
    "DNS": "D N S",
    "IP": "I P",
    "TCP": "T C P",
    "UDP": "U D P",
    "SSH": "S S H",
    "FTP": "F T P",
    "SFTP": "S F T P",
    "CLI": "C L I",
    "GUI": "G U I",
    "IDE": "I D E",
    "SDK": "S D K",
    "iOS": "I O S",
    "macOS": "mac O S",
    "OS": "O S",
    "TTS": "T T S",
    "STT": "S T T",
    "ASR": "A S R",
    "LLM": "L L M",
    "GPT": "G P T",
    "RVC": "R V C",
    "VLM": "V L M",
    "OCR": "O C R",

    # Common units/formats
    "GB": "gigabytes",
    "MB": "megabytes",
    "KB": "kilobytes",
    "TB": "terabytes",
    "MHz": "megahertz",
    "GHz": "gigahertz",
    "ms": "milliseconds",
    "fps": "frames per second",
    "px": "pixels",
    "dB": "decibels",

    # Common phrases
    "e.g.": "for example",
    "i.e.": "that is",
    "etc.": "et cetera",
    "vs.": "versus",
    "vs": "versus",
    "w/": "with",
    "w/o": "without",

    # SAM-specific
    "SAM": "sam",
    "Dustin": "Dustin",
}


# Number word mappings
ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
        "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
        "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
SCALES = ["", "thousand", "million", "billion", "trillion", "quadrillion"]


def number_to_words(n: int) -> str:
    """Convert an integer to words."""
    if n == 0:
        return "zero"

    if n < 0:
        return "negative " + number_to_words(-n)

    if n < 20:
        return ONES[n]

    if n < 100:
        tens_digit = n // 10
        ones_digit = n % 10
        if ones_digit == 0:
            return TENS[tens_digit]
        return f"{TENS[tens_digit]} {ONES[ones_digit]}"

    if n < 1000:
        hundreds = n // 100
        remainder = n % 100
        if remainder == 0:
            return f"{ONES[hundreds]} hundred"
        return f"{ONES[hundreds]} hundred {number_to_words(remainder)}"

    # Handle thousands, millions, etc.
    parts = []
    scale_idx = 0

    while n > 0:
        chunk = n % 1000
        if chunk > 0:
            chunk_words = number_to_words(chunk) if chunk < 1000 else str(chunk)
            if SCALES[scale_idx]:
                parts.append(f"{chunk_words} {SCALES[scale_idx]}")
            else:
                parts.append(chunk_words)
        n //= 1000
        scale_idx += 1

        if scale_idx >= len(SCALES):
            break

    return " ".join(reversed(parts))


def float_to_words(f: float, decimal_places: int = 2) -> str:
    """Convert a float to words."""
    if f == int(f):
        return number_to_words(int(f))

    # Split into integer and decimal parts
    int_part = int(f)
    dec_part = round((f - int_part) * (10 ** decimal_places))

    int_words = number_to_words(int_part)

    # Read decimal digits individually
    dec_str = str(dec_part).zfill(decimal_places)
    dec_words = " ".join(ONES[int(d)] if d != "0" else "zero" for d in dec_str)

    return f"{int_words} point {dec_words}"


# Emoji to text mapping (common ones)
EMOJI_DESCRIPTIONS = {
    # Smileys
    "\U0001F600": "grinning face",
    "\U0001F601": "beaming face",
    "\U0001F602": "laughing with tears",
    "\U0001F603": "smiling face",
    "\U0001F604": "grinning face with smiling eyes",
    "\U0001F605": "grinning face with sweat",
    "\U0001F606": "squinting face",
    "\U0001F609": "winking face",
    "\U0001F60A": "smiling face with smiling eyes",
    "\U0001F60B": "face savoring food",
    "\U0001F60C": "relieved face",
    "\U0001F60D": "heart eyes",
    "\U0001F60E": "smiling face with sunglasses",
    "\U0001F60F": "smirking face",
    "\U0001F610": "neutral face",
    "\U0001F611": "expressionless face",
    "\U0001F612": "unamused face",
    "\U0001F613": "downcast face with sweat",
    "\U0001F614": "pensive face",
    "\U0001F615": "confused face",
    "\U0001F616": "confounded face",
    "\U0001F617": "kissing face",
    "\U0001F618": "face blowing a kiss",
    "\U0001F619": "kissing face with smiling eyes",
    "\U0001F61A": "kissing face with closed eyes",
    "\U0001F61B": "face with tongue",
    "\U0001F61C": "winking face with tongue",
    "\U0001F61D": "squinting face with tongue",
    "\U0001F61E": "disappointed face",
    "\U0001F61F": "worried face",
    "\U0001F620": "angry face",
    "\U0001F621": "pouting face",
    "\U0001F622": "crying face",
    "\U0001F623": "persevering face",
    "\U0001F624": "face with steam from nose",
    "\U0001F625": "sad but relieved face",
    "\U0001F626": "frowning face with open mouth",
    "\U0001F627": "anguished face",
    "\U0001F628": "fearful face",
    "\U0001F629": "weary face",
    "\U0001F62A": "sleepy face",
    "\U0001F62B": "tired face",
    "\U0001F62C": "grimacing face",
    "\U0001F62D": "loudly crying face",
    "\U0001F62E": "face with open mouth",
    "\U0001F62F": "hushed face",
    "\U0001F630": "anxious face with sweat",
    "\U0001F631": "face screaming in fear",
    "\U0001F632": "astonished face",
    "\U0001F633": "flushed face",
    "\U0001F634": "sleeping face",
    "\U0001F635": "dizzy face",
    "\U0001F636": "face without mouth",
    "\U0001F637": "face with medical mask",

    # Gestures
    "\U0001F44D": "thumbs up",
    "\U0001F44E": "thumbs down",
    "\U0001F44C": "OK hand",
    "\U0001F44B": "waving hand",
    "\U0001F44F": "clapping hands",
    "\U0001F64F": "folded hands",
    "\U0001F4AA": "flexed biceps",

    # Hearts
    "\u2764": "red heart",
    "\U0001F494": "broken heart",
    "\U0001F495": "two hearts",
    "\U0001F496": "sparkling heart",
    "\U0001F497": "growing heart",
    "\U0001F498": "heart with arrow",
    "\U0001F499": "blue heart",
    "\U0001F49A": "green heart",
    "\U0001F49B": "yellow heart",
    "\U0001F49C": "purple heart",

    # Symbols
    "\u2705": "check mark",
    "\u274C": "cross mark",
    "\u2757": "exclamation mark",
    "\u2753": "question mark",
    "\U0001F4A1": "light bulb",
    "\U0001F4A5": "collision",
    "\U0001F525": "fire",
    "\u2728": "sparkles",
    "\U0001F389": "party popper",
    "\U0001F3C6": "trophy",
    "\U0001F4AF": "hundred points",

    # Weather
    "\u2600": "sun",
    "\U0001F324": "sun behind small cloud",
    "\u26C5": "sun behind cloud",
    "\U0001F325": "sun behind large cloud",
    "\U0001F326": "sun behind rain cloud",
    "\U0001F327": "cloud with rain",
    "\U0001F328": "cloud with snow",
    "\u26C8": "cloud with lightning and rain",
    "\U0001F329": "cloud with lightning",

    # Tech
    "\U0001F4BB": "laptop",
    "\U0001F4F1": "mobile phone",
    "\U0001F5A5": "desktop computer",
    "\U0001F50D": "magnifying glass",
    "\u2699": "gear",
}


class VoicePreprocessor:
    """
    Preprocesses text for optimal TTS synthesis.

    Handles markdown, abbreviations, numbers, URLs, code blocks,
    emojis, and whitespace normalization.
    """

    def __init__(self, config: Optional[PreprocessorConfig] = None):
        """
        Initialize the preprocessor.

        Args:
            config: Preprocessing configuration. Uses defaults if None.
        """
        self.config = config or PreprocessorConfig()

        # Build abbreviation map
        self._abbreviations = {**DEFAULT_ABBREVIATIONS}
        if self.config.custom_abbreviations:
            self._abbreviations.update(self.config.custom_abbreviations)

        # Compile regex patterns
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns for efficiency."""
        # Markdown patterns
        self._bold_pattern = re.compile(r'\*\*(.+?)\*\*|__(.+?)__')
        self._italic_pattern = re.compile(r'\*(.+?)\*|_([^_]+)_')
        self._strikethrough_pattern = re.compile(r'~~(.+?)~~')
        self._code_inline_pattern = re.compile(r'`([^`]+)`')
        self._header_pattern = re.compile(r'^#{1,6}\s+', re.MULTILINE)

        # Code blocks (multiline)
        self._code_block_pattern = re.compile(r'```[\w]*\n?(.*?)```', re.DOTALL)

        # URL pattern
        self._url_pattern = re.compile(
            r'https?://(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)(?:/[^\s)]*)?'
        )

        # Number patterns
        self._float_pattern = re.compile(r'\b(\d+\.\d+)\b')
        self._integer_pattern = re.compile(r'\b(\d{1,15})\b')
        self._ordinal_pattern = re.compile(r'\b(\d+)(st|nd|rd|th)\b', re.IGNORECASE)

        # Parenthetical refs like (1), [2], etc.
        self._ref_pattern = re.compile(r'\[?\(?\d+\)?\]?(?=[\s,.]|$)')

        # Emoji pattern (basic - covers most common)
        self._emoji_pattern = re.compile(
            r'[\U0001F300-\U0001F9FF]|'
            r'[\U00002600-\U000027BF]|'
            r'[\U0001F600-\U0001F64F]|'
            r'[\U0001F680-\U0001F6FF]|'
            r'[\U0001F1E0-\U0001F1FF]'
        )

        # Whitespace
        self._multiple_spaces = re.compile(r' {2,}')
        self._multiple_newlines = re.compile(r'\n{3,}')

    def clean_text(self, text: str) -> str:
        """
        Clean text for TTS synthesis.

        Applies all configured preprocessing operations.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text ready for TTS
        """
        if not text:
            return ""

        result = text

        # 1. Handle code blocks first (before other markdown)
        result = self._handle_code_blocks(result)

        # 2. Remove markdown formatting
        result = self._remove_markdown(result)

        # 3. Handle URLs
        result = self._handle_urls(result)

        # 4. Handle emojis
        result = self._handle_emojis(result)

        # 5. Expand abbreviations
        if self.config.expand_abbreviations:
            result = self._expand_abbreviations(result)

        # 6. Expand numbers
        if self.config.expand_numbers:
            result = self._expand_numbers(result)

        # 7. Remove parenthetical references
        if self.config.remove_parenthetical_refs:
            result = self._ref_pattern.sub('', result)

        # 8. Clean quotes
        if self.config.clean_quotes:
            result = self._clean_quotes(result)

        # 9. Normalize whitespace
        if self.config.normalize_whitespace:
            result = self._normalize_whitespace(result)

        return result.strip()

    def _handle_code_blocks(self, text: str) -> str:
        """Handle code blocks according to config."""
        if self.config.code_block_handling == CodeBlockHandling.SKIP:
            return self._code_block_pattern.sub('', text)

        elif self.config.code_block_handling == CodeBlockHandling.BRIEF:
            return self._code_block_pattern.sub('(code block)', text)

        elif self.config.code_block_handling == CodeBlockHandling.DESCRIBE:
            def describe_code(match):
                code = match.group(1).strip()
                lines = len(code.split('\n'))
                if lines == 1:
                    return f'(code: {code[:50]}...)' if len(code) > 50 else f'(code: {code})'
                return f'(code block with {lines} lines)'
            return self._code_block_pattern.sub(describe_code, text)

        else:  # READ
            return self._code_block_pattern.sub(r'\1', text)

    def _remove_markdown(self, text: str) -> str:
        """Remove markdown formatting."""
        result = text

        if self.config.remove_bold:
            result = self._bold_pattern.sub(r'\1\2', result)

        if self.config.remove_italic:
            result = self._italic_pattern.sub(r'\1\2', result)

        if self.config.remove_strikethrough:
            result = self._strikethrough_pattern.sub(r'\1', result)

        if self.config.remove_code_inline:
            result = self._code_inline_pattern.sub(r'\1', result)

        if self.config.remove_headers:
            result = self._header_pattern.sub('', result)

        # Remove bullet points and list markers
        result = re.sub(r'^[\s]*[-*+]\s+', '', result, flags=re.MULTILINE)
        result = re.sub(r'^[\s]*\d+\.\s+', '', result, flags=re.MULTILINE)

        # Remove links but keep text: [text](url) -> text
        result = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', result)

        # Remove images: ![alt](url) -> (image: alt)
        result = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'(image: \1)', result)

        return result

    def _handle_urls(self, text: str) -> str:
        """Handle URLs according to config."""
        if self.config.url_handling == URLHandling.STRIP:
            return self._url_pattern.sub('', text)

        elif self.config.url_handling == URLHandling.DOMAIN:
            return self._url_pattern.sub(r'\1', text)

        elif self.config.url_handling == URLHandling.DESCRIBE:
            return self._url_pattern.sub(r'link to \1', text)

        else:  # FULL
            return text

    def _handle_emojis(self, text: str) -> str:
        """Handle emojis according to config."""
        if self.config.emoji_handling == EmojiHandling.SKIP:
            return self._emoji_pattern.sub('', text)

        elif self.config.emoji_handling == EmojiHandling.DESCRIBE:
            def describe_emoji(match):
                emoji = match.group(0)
                description = EMOJI_DESCRIPTIONS.get(emoji)
                if description:
                    return f"({description})"
                return ''  # Unknown emoji, remove
            return self._emoji_pattern.sub(describe_emoji, text)

        else:  # KEEP
            return text

    def _expand_abbreviations(self, text: str) -> str:
        """Expand abbreviations to speakable form."""
        result = text

        # Sort by length (longest first) to avoid partial matches
        sorted_abbrevs = sorted(
            self._abbreviations.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )

        for abbrev, expansion in sorted_abbrevs:
            # Word boundary matching
            pattern = r'\b' + re.escape(abbrev) + r'\b'
            result = re.sub(pattern, expansion, result)

        return result

    def _expand_numbers(self, text: str) -> str:
        """Convert numbers to words."""
        result = text

        # Handle ordinals first (1st, 2nd, 3rd, 4th, etc.)
        def ordinal_to_words(match):
            num = int(match.group(1))
            if num > 10**self.config.max_number_digits:
                return match.group(0)

            word = number_to_words(num)
            suffix = match.group(2).lower()

            # Determine proper ordinal suffix
            if word.endswith('one'):
                return word[:-3] + 'first' if word != 'one' else 'first'
            elif word.endswith('two'):
                return word[:-3] + 'second' if word != 'two' else 'second'
            elif word.endswith('three'):
                return word[:-5] + 'third' if word != 'three' else 'third'
            elif word.endswith('ve'):
                return word[:-2] + 'fth'
            elif word.endswith('eight'):
                return word + 'h'
            elif word.endswith('nine'):
                return word[:-1] + 'th'
            elif word.endswith('y'):
                return word[:-1] + 'ieth'
            else:
                return word + 'th'

        result = self._ordinal_pattern.sub(ordinal_to_words, result)

        # Handle floats
        def float_to_words_match(match):
            f = float(match.group(1))
            return float_to_words(f)

        result = self._float_pattern.sub(float_to_words_match, result)

        # Handle integers
        def int_to_words_match(match):
            n = int(match.group(1))
            if len(match.group(1)) > self.config.max_number_digits:
                return match.group(0)
            return number_to_words(n)

        result = self._integer_pattern.sub(int_to_words_match, result)

        return result

    def _clean_quotes(self, text: str) -> str:
        """Normalize quote characters."""
        # Smart quotes to straight quotes
        result = text.replace('\u201c', '"').replace('\u201d', '"')  # " "
        result = result.replace('\u2018', "'").replace('\u2019', "'")  # ' '
        result = result.replace('\u00ab', '"').replace('\u00bb', '"')  # « »

        return result

    def _normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        result = text

        # Replace tabs with spaces
        result = result.replace('\t', ' ')

        # Collapse multiple spaces
        result = self._multiple_spaces.sub(' ', result)

        # Collapse multiple newlines
        if self.config.collapse_newlines:
            result = self._multiple_newlines.sub('\n\n', result)

        return result

    def split_sentences(self, text: str) -> list[str]:
        """
        Split text into sentences for TTS.

        Intelligently splits on sentence boundaries while respecting
        abbreviations and other special cases.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        if not text:
            return []

        # Split on sentence-ending punctuation
        # But not after common abbreviations
        sentences = []

        # Pattern to split on . ! ? followed by space and capital or end
        split_pattern = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z])|'  # Period/etc followed by capital
            r'(?<=[.!?])$'  # Period/etc at end
        )

        parts = split_pattern.split(text)

        for part in parts:
            part = part.strip()

            if not part:
                continue

            # Skip if too short
            if len(part) < self.config.min_sentence_length:
                # Append to previous sentence if exists
                if sentences:
                    sentences[-1] = sentences[-1] + ' ' + part
                continue

            # Split if too long
            if len(part) > self.config.max_sentence_length:
                # Try to split on commas or semicolons
                sub_parts = re.split(r'[,;]\s+', part)

                current = ""
                for sub in sub_parts:
                    if len(current) + len(sub) < self.config.max_sentence_length:
                        current = (current + ', ' + sub) if current else sub
                    else:
                        if current:
                            sentences.append(current)
                        current = sub

                if current:
                    sentences.append(current)
            else:
                sentences.append(part)

        return sentences

    def get_stats(self, original: str, cleaned: str) -> dict:
        """
        Get preprocessing statistics.

        Args:
            original: Original text
            cleaned: Cleaned text

        Returns:
            Dictionary with preprocessing stats
        """
        return {
            "original_length": len(original),
            "cleaned_length": len(cleaned),
            "reduction_percent": round((1 - len(cleaned) / max(len(original), 1)) * 100, 1),
            "original_words": len(original.split()),
            "cleaned_words": len(cleaned.split()),
            "sentences": len(self.split_sentences(cleaned)),
        }

    def add_abbreviation(self, abbrev: str, expansion: str):
        """Add a custom abbreviation expansion."""
        self._abbreviations[abbrev] = expansion

    def remove_abbreviation(self, abbrev: str):
        """Remove an abbreviation from expansion."""
        self._abbreviations.pop(abbrev, None)


# Convenience functions

def clean_for_tts(text: str, **config_kwargs) -> str:
    """
    Quick function to clean text for TTS.

    Args:
        text: Text to clean
        **config_kwargs: Override config options

    Returns:
        Cleaned text
    """
    config = PreprocessorConfig(**config_kwargs)
    preprocessor = VoicePreprocessor(config)
    return preprocessor.clean_text(text)


def split_for_tts(text: str, clean: bool = True, **config_kwargs) -> list[str]:
    """
    Quick function to split text into sentences for TTS.

    Args:
        text: Text to split
        clean: Whether to clean text first
        **config_kwargs: Override config options

    Returns:
        List of sentences
    """
    config = PreprocessorConfig(**config_kwargs)
    preprocessor = VoicePreprocessor(config)

    if clean:
        text = preprocessor.clean_text(text)

    return preprocessor.split_sentences(text)


# CLI for testing
if __name__ == "__main__":
    import sys

    test_texts = [
        "Hello **world**! The API is version 1.23 and uses HTTPS.",
        "Check out https://github.com/example/repo for more info!",
        "I found 3,241 files across 7 drives.",
        "The 1st, 2nd, and 3rd places go to the winners.",
        "Here's some code:\n```python\nprint('hello')\n```\nPretty cool right?",
        "Great job! \U0001F44D\U0001F525 You're amazing! \U0001F600",
        "The e.g. abbreviation means for example, i.e. that is to say.",
    ]

    preprocessor = VoicePreprocessor()

    print("Voice Preprocessor Demo")
    print("=" * 60)

    for text in test_texts:
        print(f"\nOriginal: {text}")
        cleaned = preprocessor.clean_text(text)
        print(f"Cleaned:  {cleaned}")
        sentences = preprocessor.split_sentences(cleaned)
        print(f"Sentences: {sentences}")
        stats = preprocessor.get_stats(text, cleaned)
        print(f"Stats: {stats}")
