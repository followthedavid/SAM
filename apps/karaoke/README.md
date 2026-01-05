# SAM Karaoke Apps

Native iOS + tvOS karaoke apps that work together like Apple Music Sing, but with your own library.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      SAM Karaoke System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────────┐         MultipeerConnectivity             │
│   │   iOS App       │◄────────────────────────────────┐         │
│   │   (iPhone)      │                                  │         │
│   ├─────────────────┤                                  │         │
│   │ • Mic capture   │         ┌─────────────────┐     │         │
│   │ • Song browser  │────────►│   tvOS App      │     │         │
│   │ • Playback ctrl │  audio  │   (Apple TV)    │     │         │
│   └─────────────────┘  stream ├─────────────────┤     │         │
│                               │ • Video player  │     │         │
│                               │ • Audio mixer   │     │         │
│                               │ • Lyrics overlay│     │         │
│                               └────────┬────────┘     │         │
│                                        │              │         │
│                                        ▼              │         │
│                               ┌─────────────────┐     │         │
│                               │   TV Speakers   │◄────┘         │
│                               │ (mixed output)  │               │
│                               └─────────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### iOS App (SAMKaraoke)
- **MicrophoneManager.swift** - Captures iPhone mic audio
- **KaraokeMicApp.swift** - Main UI with mic control, song browser
- Streams audio to Apple TV via MultipeerConnectivity

### tvOS App (SAMKaraokeTV)
- **AudioMixer.swift** - Mixes backing track + mic audio
- **KaraokePlayerApp.swift** - Video player with lyrics overlay
- Receives mic audio, plays karaoke videos

### Shared
- **KaraokeSession.swift** - MultipeerConnectivity protocol, message types

## Setup

### Prerequisites
- Xcode 15+
- Apple ID (free works, 7-day re-sign required)
- iPhone 11+ (for mic)
- Apple TV 4K (any generation)

### Create Xcode Projects

1. **iOS App**
   ```
   File → New → Project → iOS App
   Name: SAMKaraoke
   Interface: SwiftUI
   Language: Swift
   ```

   Add files:
   - `iOS/SAMKaraoke/*.swift`
   - `Shared/KaraokeSession.swift`

2. **tvOS App**
   ```
   File → New → Project → tvOS App
   Name: SAMKaraokeTV
   Interface: SwiftUI
   Language: Swift
   ```

   Add files:
   - `tvOS/SAMKaraokeTV/*.swift`
   - `Shared/KaraokeSession.swift`

### Configure Signing

1. Xcode → Preferences → Accounts → Add Apple ID
2. Select project → Signing & Capabilities
3. Team: Your Apple ID
4. Let Xcode manage signing

### Deploy

**iOS:**
1. Connect iPhone via USB
2. Select device in Xcode
3. Build & Run (Cmd+R)
4. Trust developer on iPhone: Settings → General → VPN & Device Management

**tvOS:**
1. Connect Apple TV via USB-C
2. Select Apple TV in Xcode
3. Build & Run (Cmd+R)

## Usage

1. Launch tvOS app on Apple TV
2. Launch iOS app on iPhone
3. Apps auto-discover each other on local network
4. Browse songs on iPhone or Apple TV remote
5. Tap mic button to start singing
6. Your voice plays through TV speakers mixed with backing track

## Karaoke Library

Place karaoke videos in:
```
/Users/Shared/SAMKaraoke/
├── Britney Spears - Toxic (Karaoke).mp4
├── Air - Sexy Boy (Karaoke).mp4
└── ...
```

Generate videos using the SAM karaoke pipeline:
```bash
cd ~/ReverseLab/SAM/media/karaoke
python3 generate_karaoke.py -i "song.m4a" -o /Users/Shared/SAMKaraoke/
```

## Features

| Feature | Status |
|---------|--------|
| iPhone as wireless mic | ✅ |
| Local network discovery | ✅ |
| Karaoke video playback | ✅ |
| Audio mixing (backing + mic) | ✅ |
| Song browser | ✅ |
| Multiple mic support | 🔄 Planned |
| Mic volume control | 🔄 Planned |
| Lyrics highlighting | ✅ (in video) |

## Comparison to Apple Music Sing

| Feature | Apple Music Sing | SAM Karaoke |
|---------|-----------------|-------------|
| iPhone as mic | ✅ | ✅ |
| Multiple singers | ✅ | 🔄 Planned |
| Apple TV display | ✅ | ✅ |
| Song library | Apple Music only | Your own files |
| Subscription | Required | Free |
| Vocal separation | ✅ | ✅ (Demucs) |
| Synced lyrics | ✅ | ✅ (LRCLIB) |

## Troubleshooting

**Apps don't discover each other:**
- Ensure both devices on same Wi-Fi
- Check firewall/router settings
- Restart both apps

**No audio from mic:**
- Check iPhone mic permission in Settings
- Ensure mic button is activated (green)

**7-day signing expiry:**
- Reconnect device to Mac
- Build & Run again in Xcode

## License

MIT - Personal karaoke use.
