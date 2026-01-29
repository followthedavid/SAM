# SAM Launchd Services

**Generated:** 2026-01-29
**Location:** `~/Library/LaunchAgents/com.sam.*`

---

## Active Services (5)

### 1. com.sam.api

| Property | Value |
|----------|-------|
| **Status** | RUNNING (PID 1449, exit 0) |
| **Script** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/.venv/bin/python3 sam_api.py server 8765` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain` |
| **Env: PATH** | `.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin` |
| **RunAtLoad** | YES |
| **KeepAlive** | YES (unconditional -- always restart) |
| **Logs (stdout)** | `/tmp/sam_api.stdout.log` |
| **Logs (stderr)** | `/tmp/sam_api.stderr.log` |
| **Schedule** | Continuous (starts at login, always kept alive) |
| **External Drive Dep** | NONE -- all paths on internal drive |

**Purpose:** SAM's WebSocket API server on port 8765. The primary interface for the Warp terminal and other clients to communicate with SAM's brain.

---

### 2. com.sam.autolearner

| Property | Value |
|----------|-------|
| **Status** | RUNNING (PID 33587, exit 0) |
| **Script** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/.venv/bin/python auto_learner.py daemon` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain` |
| **Env: PATH** | `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |
| **RunAtLoad** | YES |
| **KeepAlive** | YES (unconditional) |
| **Logs (stdout)** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/auto_learner_stdout.log` |
| **Logs (stderr)** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/auto_learner_stderr.log` |
| **Schedule** | Continuous (starts at login, always kept alive) |
| **External Drive Dep** | UNKNOWN -- depends on what auto_learner.py accesses internally |

**Purpose:** Autonomous learning daemon. Continuously monitors and learns from SAM's interactions and environment.

---

### 3. com.sam.perpetual

| Property | Value |
|----------|-------|
| **Status** | RUNNING (PID 11426, exit -9 / SIGKILL received at some point) |
| **Script** | `/opt/homebrew/bin/python3 perpetual_learner.py` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain` |
| **Env: PATH** | `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |
| **RunAtLoad** | YES |
| **KeepAlive** | YES (unconditional) |
| **Logs (stdout)** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/perpetual_stdout.log` |
| **Logs (stderr)** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain/perpetual_stderr.log` |
| **Schedule** | Continuous (starts at login, always kept alive) |
| **ProcessType** | Background |
| **LowPriorityIO** | YES |
| **Nice** | 10 (reduced CPU priority) |
| **External Drive Dep** | UNKNOWN -- depends on internal access patterns |

**Purpose:** Perpetual learning system. Runs at low priority to continuously process and learn without impacting foreground tasks. NOTE: Using 13.8% of RAM (~1.1GB) as of snapshot -- this is significant on 8GB.

**WARNING:** Last exit code was -9 (SIGKILL), meaning macOS killed it (likely OOM). It was restarted by launchd and is currently running.

---

### 4. com.sam.scraper-daemon

| Property | Value |
|----------|-------|
| **Status** | LOADED but NOT RUNNING (PID -, exit 0) |
| **Script** | `/opt/homebrew/opt/python@3.14/bin/python3.14 scraper_daemon.py start` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/scrapers` |
| **Env: PATH** | `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |
| **RunAtLoad** | NO |
| **KeepAlive** | Only on crash (`Crashed: true`) |
| **Logs (stdout)** | `/Volumes/David External/scraper_daemon/daemon.log` |
| **Logs (stderr)** | `/Volumes/David External/scraper_daemon/daemon.log` |
| **ThrottleInterval** | 60 seconds (min time between restarts) |
| **Schedule** | Manual start only; restarts only if it crashes |
| **External Drive Dep** | YES -- logs to `/Volumes/David External/scraper_daemon/` |

**Purpose:** Content scraper daemon. Manages automated scraping jobs. Does NOT start at boot -- must be started manually. Note: a separate scraper_daemon.py process IS running (PID 50174) but was started with `--bg` flag, likely manually.

**RISK:** If `/Volumes/David External` is not mounted, the log path will fail. The daemon may crash or silently lose logs.

---

### 5. com.sam.scraper-watchdog

| Property | Value |
|----------|-------|
| **Status** | LOADED but NOT RUNNING (PID -, exit 0) |
| **Script** | `/opt/homebrew/bin/python3 scraper_watchdog.py` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/scrapers` |
| **Env: PATH** | None set (inherits system default) |
| **RunAtLoad** | YES |
| **KeepAlive** | NO (not set) |
| **Logs (stdout)** | `/Volumes/David External/scraper_daemon/watchdog_stdout.log` |
| **Logs (stderr)** | `/Volumes/David External/scraper_daemon/watchdog_stderr.log` |
| **StartInterval** | 300 seconds (runs every 5 minutes) |
| **Schedule** | Periodic: every 5 minutes, starting at login |
| **External Drive Dep** | YES -- logs to `/Volumes/David External/scraper_daemon/` |

**Purpose:** Monitors the scraper daemon health. Runs every 5 minutes to check if scraper processes are alive and healthy.

**RISK:** Same external drive dependency for logs. If drive is unmounted, log writes fail.

---

## Disabled Services (8)

These have `.disabled` suffix and are NOT loaded by launchd.

### 6. com.sam.autonomous-daemon (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/usr/bin/python3 autonomous_daemon.py` |
| **Working Dir** | Not set |
| **RunAtLoad** | NO |
| **KeepAlive** | NO |
| **Logs** | `/Volumes/Plex/SSOT/daemon_stdout.log`, `/Volumes/Plex/SSOT/daemon_stderr.log` |
| **External Drive Dep** | YES -- logs and possibly working data on `/Volumes/Plex/` |

**Note:** Uses system python (`/usr/bin/python3`), not homebrew or venv. Likely an earlier iteration of the autonomous system.

---

### 7. com.sam.autonomous (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/bin/bash autonomous_loop.sh` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri` |
| **RunAtLoad** | YES (was enabled before disabling) |
| **KeepAlive** | YES |
| **Logs** | `/tmp/sam_autonomous_stdout.log`, `/tmp/sam_autonomous_stderr.log` |
| **External Drive Dep** | NONE |

**Note:** Shell script based autonomous loop. Superseded by Python-based daemons.

---

### 8. com.sam.brain.daemon (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/usr/bin/python3 sam_daemon.py start` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain` |
| **RunAtLoad** | YES (was enabled) |
| **KeepAlive** | YES |
| **Logs** | `sam_brain/daemon_stdout.log`, `sam_brain/daemon_stderr.log` |
| **External Drive Dep** | NONE |

**Note:** Earlier brain daemon. Uses system python. Superseded by sam_api.

---

### 9. com.sam.brain (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/usr/bin/python3 brain_daemon.py run` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/warp_tauri/sam_brain` |
| **RunAtLoad** | YES (was enabled) |
| **KeepAlive** | On non-zero exit (`SuccessfulExit: false`) |
| **Logs** | `/tmp/sam_brain_daemon.stdout.log`, `/tmp/sam_brain_daemon.stderr.log` |
| **External Drive Dep** | NONE |

**Note:** Another earlier brain daemon variant. Would restart only if it crashed (non-zero exit).

---

### 10. com.sam.bridge (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/usr/bin/python3 bridge_daemon.py` |
| **Working Dir** | Not set |
| **RunAtLoad** | YES (was enabled) |
| **KeepAlive** | YES |
| **Logs** | `~/.sam_bridge_stdout.log`, `~/.sam_bridge_stderr.log` |
| **External Drive Dep** | NONE |

**Note:** Bridge between Tauri frontend and Python backend. No working directory set. No PATH env.

---

### 11. com.sam.daemon (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/bin/bash sam_daemon.sh` |
| **Working Dir** | `/Users/davidquinton/ReverseLab/SAM/media` |
| **RunAtLoad** | YES (was enabled) |
| **KeepAlive** | YES |
| **ThrottleInterval** | 30 seconds |
| **Env: PATH** | `/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin` |
| **Env: HOME** | `/Users/davidquinton` |
| **Env: DISCOGS_TOKEN** | Set (API key for music metadata) |
| **Logs** | `~/.sam_daemon_stdout.log`, `~/.sam_daemon_stderr.log` |
| **External Drive Dep** | NONE (plist itself), but the media scripts likely access external drives |

**Note:** Media processing daemon with Discogs API integration. Contains an API token in the plist.

**SECURITY NOTE:** Contains plaintext API token (DISCOGS_TOKEN) in the plist file.

---

### 12. com.sam.evolution (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/usr/bin/python3 /Volumes/Plex/SSOT/sam_brain/advanced_evolution.py run --interval 15` |
| **Working Dir** | `/Volumes/Plex/SSOT` |
| **RunAtLoad** | YES (was enabled) |
| **KeepAlive** | On non-zero exit only |
| **ThrottleInterval** | 60 seconds |
| **ProcessType** | Background |
| **LowPriorityBackgroundIO** | YES |
| **Logs** | `/Volumes/Plex/SSOT/sam_brain/evolution.log`, `/Volumes/Plex/SSOT/sam_brain/evolution_error.log` |
| **External Drive Dep** | YES -- script AND working dir AND logs ALL on `/Volumes/Plex/` |

**Note:** Self-evolution system. Entirely dependent on Plex external drive. Would fail completely if drive not mounted.

---

### 13. com.sam.mlx-server (DISABLED)

| Property | Value |
|----------|-------|
| **Script** | `/Users/davidquinton/.sam/mlx_venv/bin/python3 mlx_server.py` |
| **Working Dir** | Not set |
| **RunAtLoad** | YES (was enabled) |
| **KeepAlive** | YES |
| **Logs** | `/tmp/sam_mlx_server.log` (both stdout and stderr) |
| **External Drive Dep** | NONE |

**Note:** Standalone MLX inference server. Uses a dedicated venv at `~/.sam/mlx_venv/`. Superseded by direct MLX integration in cognitive modules.

---

## Boot Sequence Analysis

### What happens when the Mac boots (user login):

```
TIME 0: User login
  |
  +-- com.sam.api               --> STARTS (port 8765 WebSocket server)
  +-- com.sam.autolearner        --> STARTS (auto learning daemon)
  +-- com.sam.perpetual          --> STARTS (perpetual learner, low priority)
  +-- com.sam.scraper-watchdog   --> STARTS (first watchdog run)
  |
  |   com.sam.scraper-daemon     --> does NOT start (RunAtLoad: false)
  |
  +-- All .disabled services     --> NOT loaded at all
  |
TIME +300s:
  +-- com.sam.scraper-watchdog   --> Runs again (every 5 minutes)
```

All RunAtLoad services start simultaneously. There is no explicit ordering between them. launchd does not guarantee startup order for user agents.

### Dependency Analysis

```
com.sam.api          -- Independent. No external drive deps. SAFE at boot.
com.sam.autolearner  -- Independent. No external drive deps in plist. SAFE at boot.
com.sam.perpetual    -- Independent. No external drive deps in plist. SAFE at boot.
com.sam.scraper-watchdog -- Logs to /Volumes/David External. RISKY at boot.
com.sam.scraper-daemon   -- Logs to /Volumes/David External. Manual start only.
```

### What if external drives are not mounted?

| Service | Impact |
|---------|--------|
| **com.sam.api** | No impact -- all paths internal |
| **com.sam.autolearner** | No impact from plist -- but if it internally accesses external storage, those operations will fail silently |
| **com.sam.perpetual** | Same as autolearner -- plist is fine, internal access unknown |
| **com.sam.scraper-watchdog** | WILL FAIL to write logs to `/Volumes/David External/scraper_daemon/`. macOS will either create the path as a local directory (bad!) or the process will crash on write |
| **com.sam.scraper-daemon** | Not auto-started, but if manually started: same log path failure |

**Critical Risk:** If `/Volumes/David External` is not mounted and the watchdog starts, macOS may create `/Volumes/David External/` as a local directory on the boot drive. When the real drive later mounts, it will mount at a different path (e.g., `/Volumes/David External 1`), causing confusion and orphaned directories.

### Python Interpreter Inconsistencies

| Service | Python Used |
|---------|-------------|
| com.sam.api | `.venv/bin/python3` (project venv) |
| com.sam.autolearner | `.venv/bin/python` (project venv) |
| com.sam.perpetual | `/opt/homebrew/bin/python3` (homebrew) |
| com.sam.scraper-daemon | `/opt/homebrew/opt/python@3.14/bin/python3.14` (explicit 3.14) |
| com.sam.scraper-watchdog | `/opt/homebrew/bin/python3` (homebrew) |

Note: The disabled services mostly used `/usr/bin/python3` (system python). The active services are split between the project venv and homebrew python. This inconsistency could cause import failures if packages are installed in one env but not the other.

---

## RAM Impact Summary

As of 2026-01-29 snapshot:

| Service | PID | RAM % | RAM (approx) |
|---------|-----|-------|---------------|
| com.sam.api | 1449 | 0.0% | ~2 MB |
| com.sam.autolearner | 33587 | 0.3% | ~21 MB |
| com.sam.perpetual | 11426 | 13.8% | ~1.1 GB |
| scraper_daemon (manual) | 50174 | 0.1% | ~11 MB |
| **TOTAL** | | **~14.2%** | **~1.13 GB** |

The perpetual learner alone consumes ~1.1GB, which is 13.8% of the 8GB total. On a memory-constrained system, this is significant. It has already been OOM-killed once (exit code -9).

---

## Recommendations

1. **External drive guard:** Add a pre-check script to scraper-watchdog and scraper-daemon that verifies `/Volumes/David External` exists before running. Use `WatchPaths` on the mount point instead of `RunAtLoad`.

2. **Perpetual learner memory:** Monitor and cap `perpetual_learner.py` memory usage. At 1.1GB it risks OOM kills. Consider adding `SoftResourceLimits` to the plist.

3. **Python consistency:** Standardize on `.venv/bin/python3` for all sam_brain services and `/opt/homebrew/bin/python3` for scraper services. Mixed interpreters cause hard-to-debug import failures.

4. **Log location cleanup:** Active services split logs between `/tmp/`, project directories, and external drives. Consider consolidating to a single location.

5. **Disabled service cleanup:** 8 disabled plists are accumulating. Archive or delete ones that are confirmed superseded (bridge, brain, brain.daemon, autonomous, mlx-server).

6. **Security:** Move the DISCOGS_TOKEN out of the plist file into a keychain entry or environment config file.

---

*Last updated: 2026-01-29*
