# SAM Voice on iPhone

Talk to SAM with Dustin Steele's voice from your iPhone.

## Your Mac IP: `192.168.132.63`
## Server Port: `8765`

---

## Option 1: Siri Shortcut (Recommended)

### Create the Shortcut:

1. Open **Shortcuts** app on iPhone
2. Tap **+** to create new shortcut
3. Add these actions:

```
[Ask for Input] → "What should SAM say?"
       ↓
[Get Contents of URL]
   URL: http://192.168.132.63:8765/api/speak
   Method: POST
   Headers: Content-Type: application/json
   Request Body: {"text": "[Input from previous]", "voice": "dustin"}
       ↓
[Play Sound]
```

### Detailed Steps:

1. **Ask for Input**
   - Add "Ask for Input" action
   - Prompt: "What should SAM say?"

2. **Get Contents of URL**
   - Add "Get Contents of URL" action
   - URL: `http://192.168.132.63:8765/api/speak`
   - Method: POST
   - Headers: Add `Content-Type` = `application/json`
   - Request Body: JSON
   ```json
   {
     "text": "[Provided Input]",
     "voice": "dustin"
   }
   ```

3. **Play Sound**
   - Add "Play Sound" action
   - Input: Contents of URL

4. Name your shortcut "Talk to SAM"

5. Add to Home Screen or say "Hey Siri, Talk to SAM"

---

## Option 2: Quick Test via Safari

Open Safari and go to:
```
http://192.168.132.63:8765/api/health
```

Should return: `{"status":"ok","rvc_available":true,...}`

---

## Option 3: Voice Conversation Shortcut

For a back-and-forth conversation:

```
[Dictate Text] → Your question
       ↓
[Get Contents of URL]
   URL: http://192.168.132.63:8765/api/speak
   Body: {"text": "[Dictated Text]", "voice": "dustin"}
       ↓
[Play Sound]
       ↓
[Repeat]
```

---

## Starting the Server

On your Mac, run:
```bash
cd ~/ReverseLab/SAM/warp_tauri/sam_brain
./start_voice_server.sh
```

Or to run in background:
```bash
nohup ./start_voice_server.sh > voice_server.log 2>&1 &
```

---

## API Reference

### Speak
```
POST /api/speak
Content-Type: application/json

{
  "text": "Hello David",
  "voice": "dustin",      // "dustin" or "default"
  "pitch_shift": 0,       // -12 to 12 semitones
  "speed": 1.0            // 0.5 to 2.0
}

Returns: audio/wav
```

### List Voices
```
GET /api/voices

Returns:
[
  {"id": "dustin", "name": "Dustin Steele", "available": true},
  {"id": "default", "name": "Default (Alex)", "available": true}
]
```

### Health Check
```
GET /api/health

Returns: {"status": "ok", "rvc_available": true}
```

---

## Troubleshooting

### "Could not connect"
- Make sure your Mac and iPhone are on the same WiFi network
- Check the server is running: `curl http://192.168.132.63:8765/api/health`
- Check firewall allows port 8765

### "Server error"
- Check server logs: `tail -f ~/ReverseLab/SAM/warp_tauri/sam_brain/voice_server.log`

### Slow response
- First request loads RVC model (~10 seconds)
- Subsequent requests are faster
- Results are cached for repeated phrases

---

## Future: Full SAM Conversation

To have SAM actually respond (not just speak your text):

1. Send your text to SAM API for processing
2. Get SAM's response
3. Send response to voice server
4. Play the audio

This requires the full SAM API running alongside the voice server.
