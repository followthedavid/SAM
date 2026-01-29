# API Security Audit - SAM Brain

**Date:** 2026-01-29
**Scope:** `sam_api.py`, `vision_server.py`, `voice/voice_server.py`
**Auditor:** Claude Code (automated analysis)

---

## Executive Summary

All three API servers have **no authentication, no rate limiting, and permissive CORS**. They bind to `0.0.0.0` (all interfaces), meaning any device on the network can access every endpoint without credentials. This is acceptable for a local development/home-lab tool behind a firewall, but would be a critical risk if exposed to the internet.

| Category | sam_api.py | vision_server.py | voice_server.py |
|---|---|---|---|
| Authentication | NONE | NONE | NONE |
| CORS | `*` (wildcard) | `*` (wildcard) | `*` (wildcard, all methods/headers) |
| Rate Limiting | NONE | NONE | NONE |
| Input Validation | Minimal | Minimal | Basic (length check) |
| Bind Address | `0.0.0.0` | `0.0.0.0` | `0.0.0.0` |
| SSL/TLS | NONE | NONE | Optional (self-signed) |

**Risk Level:** LOW for local/Tailscale use. CRITICAL if port-forwarded or internet-exposed.

---

## 1. Authentication

### sam_api.py (port 8765)
- **Finding:** Zero authentication on any endpoint.
- **Evidence:** No imports of auth libraries. No API key checks, no token validation, no session management. The `SAMHandler` class (line 4358) processes all requests unconditionally.
- **Impact:** Anyone who can reach port 8765 can query SAM, read memory/facts, approve/reject items, delete facts, trigger model inference, and access all cognitive endpoints.

### vision_server.py (port 8766)
- **Finding:** Zero authentication.
- **Evidence:** `VisionHandler` (line 122) has no auth checks. The `/process` endpoint accepts arbitrary image paths or base64 data from any caller.
- **Impact:** Anyone on the network can submit images for processing, consuming GPU/CPU resources.

### voice/voice_server.py (port 8765 default)
- **Finding:** Zero authentication.
- **Evidence:** FastAPI app (line 282) has no auth middleware, no dependency injection for auth. All endpoints are public.
- **Impact:** Anyone can generate TTS audio, consuming compute and potentially abusing the voice pipeline.

---

## 2. CORS (Cross-Origin Resource Sharing)

### sam_api.py
- **Finding:** Wildcard `Access-Control-Allow-Origin: *` on every response.
- **Evidence:** Lines 4365, 4382, 4401, 4703, 4798, 4864, 5071 -- every `send_json` call and static file response includes `Access-Control-Allow-Origin: *`.
- **Missing:** No `do_OPTIONS` handler for CORS preflight. Browsers making cross-origin POST requests with `Content-Type: application/json` will send a preflight OPTIONS request that gets a 501 (Method Not Implemented) from `BaseHTTPRequestHandler`. This means browser-based cross-origin POST requests may actually fail despite the permissive header on responses.
- **Impact:** Any website open in the user's browser can make GET requests to SAM API endpoints and read the responses (CSRF-like). POST requests from browsers would be blocked by missing preflight support.

### vision_server.py
- **Finding:** Wildcard `Access-Control-Allow-Origin: *` plus a proper `do_OPTIONS` handler.
- **Evidence:** Lines 132-133 (on responses), lines 136-142 (`do_OPTIONS` handler allowing GET, POST, OPTIONS with Content-Type header).
- **Impact:** Any website can make full cross-origin requests (including POST with JSON) to the vision server.

### voice/voice_server.py
- **Finding:** Maximum permissive CORS via FastAPI middleware.
- **Evidence:** Lines 289-295:
  ```python
  app.add_middleware(
      CORSMiddleware,
      allow_origins=["*"],
      allow_credentials=True,
      allow_methods=["*"],
      allow_headers=["*"],
  )
  ```
- **Note:** `allow_origins=["*"]` combined with `allow_credentials=True` is explicitly warned against in the CORS spec. FastAPI/Starlette will actually override this to not send credentials with wildcard origins, but it signals intent to be maximally permissive.
- **Impact:** Any website can make any type of cross-origin request to the voice server.

---

## 3. Rate Limiting

### All three servers
- **Finding:** No rate limiting whatsoever.
- **Evidence:** No imports of `slowapi`, `ratelimit`, `flask-limiter`, or any throttling mechanism. No request counting, no per-IP tracking, no cooldown logic.
- **Impact:** An attacker (or misconfigured client) can flood any endpoint with unlimited requests. Given the 8GB RAM constraint and that inference endpoints load ML models, this could trivially cause an OOM crash or system freeze.
- **Especially dangerous endpoints:**
  - `POST /api/cognitive/process` (triggers MLX inference)
  - `POST /api/think` (triggers MLX inference)
  - `POST /process` on vision server (triggers VLM inference, 120s timeout)
  - `POST /api/speak` on voice server (triggers TTS + optional RVC)

---

## 4. Input Validation

### sam_api.py
- **Finding:** Minimal validation -- only checks for missing required fields.
- **Details:**
  - Query parameters: Checks if `q` parameter exists, returns 400 if missing. No length limits on query strings.
  - POST body: Parses JSON, checks for required fields (`query`, `improvement_id`, `message`, etc.). No max length enforcement.
  - `int()` casts on `limit` parameters (lines 4428, 4437, etc.) with no try/except -- a non-numeric value would cause an unhandled exception / 500 error.
  - **Path traversal on static files** (line 4393): `file_path = static_dir / path[8:]` -- the path is not sanitized. A request to `/static/../../sam_api.py` could potentially serve arbitrary files. The `Path` concatenation provides some protection, but no explicit `..` filtering or `resolve()` check is performed.
  - **DELETE endpoint** (line 5150): Accepts fact IDs from the URL path with only a check against reserved words, no format validation.

### vision_server.py
- **Finding:** Minimal validation.
- **Details:**
  - `image_path` parameter (line 191): Checks `os.path.exists()` but does not restrict which paths can be read. An attacker can point this at any file on the filesystem that the process can access.
  - `max_tokens` and `temperature` (lines 176-177): No bounds checking. Extreme values could cause unexpected behavior.
  - `image_base64` (line 185): No size limit on the base64 payload. A multi-gigabyte payload would be decoded into memory.
  - JSON parse errors are caught (line 211).

### voice/voice_server.py
- **Finding:** Best of the three -- uses Pydantic models and has explicit length checks.
- **Details:**
  - `SpeakRequest` Pydantic model (line 63) enforces field types.
  - Text length check (line 343): Max 5000 characters.
  - Empty text check (line 340-341).
  - However, `pitch_shift` (line 68) has a comment saying "-12 to 12" but no `Field(ge=-12, le=12)` validator.
  - `speed` (line 69) has no bounds -- a value of 0 or negative could cause issues.

---

## 5. Network Binding

### sam_api.py
- **Finding:** Binds to `0.0.0.0` (all interfaces).
- **Evidence:** Line 5166: `server = HTTPServer(("0.0.0.0", port), SAMHandler)`
- **Comment on line 5165:** "Bind to all interfaces for network access (Tailscale, phone, etc.)"
- **Impact:** Accessible from any network interface -- LAN, Tailscale VPN, and potentially the internet if the router has port forwarding enabled.

### vision_server.py
- **Finding:** Binds to `0.0.0.0`.
- **Evidence:** Line 225: `server = HTTPServer(("0.0.0.0", port), VisionHandler)`
- **Impact:** Same as above.

### voice/voice_server.py
- **Finding:** Binds to `0.0.0.0` by default.
- **Evidence:** Line 375: `parser.add_argument("--host", type=str, default="0.0.0.0", help="Server host")`
- **Impact:** Same as above.

---

## 6. SSL/TLS

### sam_api.py
- **Finding:** No SSL/TLS support.
- **Evidence:** Uses Python's `http.server.HTTPServer` which does not support SSL. No SSL wrapper code present.
- **Impact:** All traffic is plaintext. On a shared network, queries, responses, memory contents, and facts can be intercepted.

### vision_server.py
- **Finding:** No SSL/TLS support.
- **Evidence:** Same `http.server.HTTPServer` without SSL wrapping.

### voice/voice_server.py
- **Finding:** Optional SSL/TLS via self-signed certificates.
- **Evidence:** Lines 380-383 and 402-409: Checks for `voice_cert.pem` and `voice_key.pem` files and passes them to uvicorn's `ssl_certfile`/`ssl_keyfile` parameters when `--https` flag is used.
- **Note:** Self-signed certificates provide encryption but not identity verification. The startup banner (line 397-399) even mentions trusting the certificate on iOS.
- **Impact:** Voice server can optionally encrypt traffic. The other two servers cannot.

---

## 7. Additional Concerns

### Path Traversal (sam_api.py)
The static file handler at line 4393 constructs a file path from user input:
```python
file_path = static_dir / path[8:]  # Remove /static/
```
No sanitization against `..` sequences. A request like `GET /static/../../../etc/passwd` could potentially serve system files, depending on how Python's `pathlib` resolves the path.

### Arbitrary File Access (vision_server.py)
The `image_path` parameter at line 191 allows specifying any filesystem path:
```python
image_path = data["image_path"]
if not os.path.exists(image_path):
    ...
```
While it checks existence, it does not restrict to a specific directory. An attacker could process any readable file on the system.

### Shell Injection (vision_server.py)
The `process_image` function (line 71) constructs a shell command with `shell=True`:
```python
cmd = f'''python3 -m mlx_vlm generate \
    --model "{MODEL_ID}" \
    --image "{image_path}" \
    --prompt '{escaped_prompt}' \
    ...'''
result = subprocess.run(cmd, shell=True, ...)
```
The `escaped_prompt` handling (line 68) attempts to escape quotes but is not robust. A carefully crafted prompt could inject shell commands. The `image_path` is also interpolated directly into the shell command with only double-quote wrapping.

### Command Injection via TTS (voice/voice_server.py)
The `generate_base_tts` method (line 130) passes user-provided text to the macOS `say` command:
```python
cmd = ["say", "-v", DEFAULT_TTS_VOICE, "-r", str(rate), "-o", str(output_file), text]
```
Using a list with `create_subprocess_exec` (not `shell=True`) provides protection against shell injection, so this is safe.

### Error Information Leakage
All three servers return raw exception messages in error responses (e.g., `str(e)`). This could leak internal paths, library versions, or configuration details to an attacker.

### Logging Suppression (sam_api.py)
Line 4359-4360: `log_message` is overridden to do nothing. This means no access logs are recorded, making it impossible to detect or investigate abuse.

---

## 8. Recommendations (Prioritized)

### Immediate (if exposing beyond localhost/Tailscale)

1. **Add API key authentication** -- A simple shared secret in a header (`X-API-Key`) checked by middleware would block unauthorized access.
2. **Restrict CORS origins** -- Replace `*` with specific origins (`http://localhost:1420` for Tauri, the Tailscale IP, etc.).
3. **Fix path traversal** -- Add `resolve()` check in static file handler:
   ```python
   file_path = (static_dir / path[8:]).resolve()
   if not str(file_path).startswith(str(static_dir.resolve())):
       self.send_json({"error": "Forbidden"}, 403)
       return
   ```
4. **Fix shell injection in vision_server.py** -- Use `subprocess.run` with a list (no `shell=True`).

### Short-term

5. **Add rate limiting** -- Even a simple per-IP counter (e.g., max 60 requests/minute) would prevent resource exhaustion.
6. **Add input length limits** -- Cap query strings and POST bodies to reasonable sizes (e.g., 10KB for text, 50MB for images).
7. **Restrict vision image_path** -- Whitelist allowed directories or require base64-only input.
8. **Enable access logging** -- Restore `log_message` or add a request logger.

### Long-term

9. **Add SSL/TLS to all servers** -- Use a reverse proxy (e.g., Caddy, nginx) or wrap the HTTP servers with SSL context.
10. **Implement proper Pydantic validation** -- Migrate sam_api.py to FastAPI (like voice_server.py) for automatic request validation.
11. **Add request size limits** -- Set `max_content_length` to prevent memory exhaustion from large payloads.

---

## 9. Context: Current Risk Assessment

These servers are designed for **local/home network use** on an M2 Mac Mini, primarily accessed by:
- The Tauri desktop app (localhost)
- An iPhone over the local network / Tailscale VPN
- Claude Code sessions on the same machine

In this context, the risk is **low** because:
- The Mac Mini is behind a home router (no port forwarding assumed)
- Tailscale provides encrypted, authenticated network access
- The only users are David and automated tools

The risk becomes **critical** if:
- Any port is forwarded to the internet
- The machine connects to an untrusted network (coffee shop, hotel)
- A malicious website is visited while SAM is running (cross-origin attacks via permissive CORS)
