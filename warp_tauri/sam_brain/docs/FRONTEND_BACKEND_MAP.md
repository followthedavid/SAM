# Frontend-Backend API Mapping

**Generated:** 2026-01-28
**Last Updated:** 2026-01-28

This document maps all API calls between the Tauri frontend (`warp_tauri/src/`) and the SAM Brain backend (`sam_brain/sam_api.py`), including WebSocket/SSE connections, Tauri IPC commands, and port configurations.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Port Configuration](#port-configuration)
3. [Frontend API Calls to Backend](#frontend-api-calls-to-backend)
4. [Backend Endpoints](#backend-endpoints)
5. [WebSocket/SSE Connections](#websocketsse-connections)
6. [Tauri IPC Commands (Rust)](#tauri-ipc-commands-rust)
7. [Mismatches: Frontend Calls with No Backend Handler](#mismatches-frontend-calls-with-no-backend-handler)
8. [Mismatches: Backend Endpoints Never Called](#mismatches-backend-endpoints-never-called)
9. [Shared Types/Schemas](#shared-typesschemas)

---

## Architecture Overview

```
+---------------------------+       HTTP/REST        +---------------------------+
|                           |  <----------------->   |                           |
|   Tauri Frontend (Vue)    |      Port 8765        |   SAM Brain (Python)      |
|   warp_tauri/src/         |                       |   sam_brain/sam_api.py    |
|                           |                       |                           |
+---------------------------+                       +---------------------------+
           |                                                    |
           |  Tauri IPC (invoke)                               |
           v                                                    |
+---------------------------+                                   |
|   Rust Backend            |                                   |
|   src-tauri/src/          |       Python subprocess           |
|   - main.rs               |  <------------------------------->|
|   - commands.rs           |       (shell exec to sam_api.py)  |
|   - brain.rs              |                                   |
+---------------------------+                                   |

           |                                                    |
           |  WebSocket (Avatar)                               |
           v  Port 8765                                        |
+---------------------------+                                   |
|   Game Engine Avatar      |                                   |
|   Unity/Unreal            |                                   |
+---------------------------+                                   |

           |                                                    |
           |  TTS Server                                       |
           v  Port 5002/5003                                    |
+---------------------------+                                   |
|   Local TTS (Coqui/Piper) |                                   |
+---------------------------+                                   |
```

---

## Port Configuration

| Port | Service | Used By |
|------|---------|---------|
| **8765** | SAM Brain API (Primary) | `useCognitiveAPI.ts`, `useSAM.ts`, `sam-daemon.ts` |
| **8766** | Vision Server (Persistent) | Vision processing (optional) |
| **11434** | Ollama (DECOMMISSIONED) | Legacy - migrated to MLX |
| **1234** | LM Studio (Optional) | `useMultiModel.ts` fallback |
| **4005** | Agent Bridge Server | `useAgentBridge.ts` |
| **5002** | Coqui TTS Server | `useSAMVoice.ts` |
| **5003** | Piper TTS Server | `useSAMVoice.ts` |
| **3847** | Cross-Device API Server | `src/server/api.ts` (iOS/Apple devices) |

---

## Frontend API Calls to Backend

### Primary Cognitive API (`useCognitiveAPI.ts`)

| Frontend Method | HTTP Method | Endpoint | Backend Handler |
|-----------------|-------------|----------|-----------------|
| `ping()` | GET | `/api/health` | Health check |
| `process(query)` | POST | `/api/cognitive/process` | `api_cognitive_process()` |
| `stream(query)` | SSE | `/api/cognitive/stream` | `api_cognitive_stream()` |
| `processImage(path, query)` | POST | `/api/vision/process` | `api_vision_process()` |
| `describeImage(path)` | POST | `/api/vision/describe` | `api_vision_describe()` |
| `detectObjects(path)` | POST | `/api/vision/detect` | `api_vision_detect()` |
| `getState()` | GET | `/api/cognitive/state` | `api_cognitive_state()` |
| `getMood()` | GET | `/api/cognitive/mood` | `api_cognitive_mood()` |
| `submitFeedback(id, helpful, comment)` | POST | `/api/cognitive/feedback` | `api_cognitive_feedback()` |
| `speak(query)` | POST | `/api/cognitive/speak` | Not implemented |

### Agent Bridge (`useAgentBridge.ts`)

| Frontend Method | HTTP Method | Endpoint | Backend Handler |
|-----------------|-------------|----------|-----------------|
| `fetchState()` | GET | `/state` | ai_agent_server.cjs |
| `enqueue(type, payload)` | POST | `/enqueue` | ai_agent_server.cjs |
| `approve(id, approved, by)` | POST | `/approve` | ai_agent_server.cjs |
| `executeNow(id)` | POST | `/execute-now` | ai_agent_server.cjs |
| `getLogs()` | GET | `/logs` | ai_agent_server.cjs |

**Note:** Agent Bridge connects to port 4005 (Node.js server, not Python).

### AI/Ollama Integration (Multiple Files)

These endpoints call Ollama (DECOMMISSIONED - should migrate to SAM Brain):

| File | Endpoint | Purpose |
|------|----------|---------|
| `useAI.ts` | `localhost:11434/api/generate` | Text generation |
| `useUniversalMemory.ts` | `localhost:11434/api/embeddings` | Embeddings |
| `useMultiModel.ts` | `localhost:11434/api/tags` | Model listing |
| `useAIMemory.ts` | `localhost:11434/api/generate` | Memory queries |
| `useContextCompression.ts` | `localhost:11434/api/generate` | Prompt compression |
| `useErrorRecovery.ts` | `localhost:11434/api/generate` | Error analysis |
| `useTestRunner.ts` | `localhost:11434/api/generate` | Test generation |
| `useCodeExecution.ts` | `localhost:11434/api/generate` | Code analysis |
| `useGitAI.ts` | `localhost:11434/api/generate` | Git commit messages |
| `useCodeExplainer.ts` | `localhost:11434/api/generate` | Code explanation |
| `useGitIntegration.ts` | `localhost:11434/api/generate` | Git operations |
| `useScaffoldedAgent.ts` | `localhost:11434/api/tags` | Model check |
| `autonomousDeveloper.ts` | `localhost:11434/api/generate` | Autonomous tasks |

### Voice/TTS Integration

| File | Endpoint | Purpose |
|------|----------|---------|
| `useSAMVoice.ts` | `localhost:5002/api/tts` | Coqui TTS |
| `useSAMVoice.ts` | `localhost:5003/api/tts` | Piper TTS |
| `useTTS.ts` | ElevenLabs API | Cloud TTS |

### External APIs (Not SAM Brain)

| File | Endpoint | Purpose |
|------|----------|---------|
| `useTTS.ts` | `api.elevenlabs.io` | ElevenLabs TTS |
| `useSAMVoice.ts` | `api.openai.com/v1/audio/speech` | OpenAI TTS |
| `src/server/api.ts` | Internal (Port 3847) | Cross-device iOS API |

---

## Backend Endpoints

### SAM Brain API (`sam_api.py`) - Port 8765

#### Health & Status

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/status` | GET | System status |
| `/api/projects` | GET | Project list |
| `/api/memory` | GET | Interaction history |

#### Query Processing

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/query` | GET/POST | Query SAM |
| `/api/orchestrate` | POST | Route to specialized handlers |

#### Cognitive System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/cognitive/state` | GET | Cognitive system state |
| `/api/cognitive/mood` | GET | Current emotional state |
| `/api/cognitive/process` | GET/POST | Process query |
| `/api/cognitive/stream` | POST | SSE streaming tokens |
| `/api/cognitive/escalate` | POST | Escalate to Claude |
| `/api/cognitive/feedback` | GET/POST | Feedback operations |
| `/api/cognitive/feedback/recent` | GET | Recent feedback |

#### Self-Improvement

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/self` | GET | SAM explains itself |
| `/api/suggest` | GET | Improvement suggestions |
| `/api/proactive` | GET | What SAM noticed |
| `/api/learning` | GET | What SAM learned |
| `/api/scan` | GET | Trigger improvement scan |
| `/api/intelligence` | GET | Distillation/feedback/memory stats |

#### Thinking System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/think` | GET/POST | SAM thinks about query |
| `/api/think/stream` | POST | SSE streaming thought process |
| `/api/think/colors` | GET | Color scheme for thought types |

#### Vision System

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vision/models` | GET | Available vision models |
| `/api/vision/stats` | GET | Vision engine statistics |
| `/api/vision/process` | POST | Process image |
| `/api/vision/analyze` | POST | Analyze image (Swift UI) |
| `/api/vision/stream` | POST | SSE streaming vision |
| `/api/vision/describe` | GET/POST | Describe image |
| `/api/vision/detect` | GET/POST | Object detection |
| `/api/vision/ocr` | POST | Text extraction (Apple Vision) |
| `/api/vision/smart` | GET/POST | Auto-routing to best tier |
| `/api/vision/smart/stats` | GET | Cache statistics |

#### Image Chat

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/image/context` | GET | Current image context |
| `/api/image/context/clear` | GET | Clear image context |
| `/api/image/followup/check` | GET/POST | Check if query is follow-up |
| `/api/image/chat` | POST | Image conversation |

#### Project Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/project` | GET | Detect project, get context |
| `/api/project/recent` | GET | Recently accessed projects |
| `/api/project/current` | GET | Current project |
| `/api/project/todos` | GET | TODOs for project |
| `/api/project/session` | POST | Update session |

#### Facts/Memory

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/facts` | GET/POST | List/add facts |
| `/api/facts/<id>` | GET/DELETE | Get/remove fact |
| `/api/facts/search` | GET | Search facts |
| `/api/facts/context` | GET | Formatted context for prompts |
| `/api/facts/remember` | POST | Remember a fact |

#### Code Index

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/code/search` | GET | Search indexed code |
| `/api/code/stats` | GET | Code index statistics |
| `/api/code/index` | POST | Index code path |
| `/api/index/status` | GET | Comprehensive index stats |
| `/api/index/search` | GET | Search index |
| `/api/index/build` | POST | Build/rebuild index |
| `/api/index/clear` | POST | Clear index |
| `/api/index/watch` | POST | Start file watcher |
| `/api/index/watch/stop` | GET | Stop file watcher |

#### Voice Pipeline

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/voice/start` | GET | Start voice pipeline |
| `/api/voice/stop` | GET | Stop voice pipeline |
| `/api/voice/status` | GET | Pipeline status |
| `/api/voice/emotion` | GET | Current detected emotion |
| `/api/voice/config` | GET/POST | Get/update configuration |
| `/api/voice/conversation` | GET | Full conversation state |
| `/api/voice/process` | POST | Process audio chunk |
| `/api/voice/stream` | POST | SSE streaming audio |
| `/api/voice/settings` | GET/PUT | Voice settings (Phase 6.1) |

#### Distillation Review

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/distillation/review` | GET/POST | Get pending/review example |
| `/api/distillation/review/stats` | GET | Review queue statistics |
| `/api/distillation/review/<id>` | GET | Get example details |
| `/api/distillation/review/batch` | POST | Batch approve/reject |

#### Approval Queue

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/approval/queue` | GET | Pending approvals |
| `/api/approval/stats` | GET | Approval statistics |
| `/api/approval/history` | GET | Approval history |
| `/api/approval/<id>` | GET | Get approval details |
| `/api/approval/approve` | POST | Approve action |
| `/api/approval/reject` | POST | Reject action |

#### Resources

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/resources` | GET | System resources |
| `/api/context/stats` | GET | Compression monitoring |
| `/api/unload` | GET | Unload model to free memory |
| `/api/notifications` | GET | Proactive feedback alerts |
| `/api/feedback/dashboard` | GET | Feedback dashboard |

---

## WebSocket/SSE Connections

### WebSocket Connections

| File | URL Pattern | Purpose |
|------|-------------|---------|
| `useAvatarBridge.ts` | `ws://localhost:8765` | Avatar control |
| `useCollaboration.ts` | WebSocket | Real-time collaboration |
| `useTestRunner.ts` | WebSocket | Test streaming |
| `useCodeExecution.ts` | WebSocket | Code execution streaming |
| `src/core/sam.ts` | `ws://localhost:{avatar.wsPort}` | Avatar WebSocket |
| `src/core/sam-safety.ts` | WebSocket | Safety monitoring |
| `src/server/api.ts` | `ws://0.0.0.0:3847` | Cross-device API |

### Server-Sent Events (SSE)

| File | Endpoint | Purpose |
|------|----------|---------|
| `useCognitiveAPI.ts` | `/api/cognitive/stream` | Token streaming |
| Backend | `/api/think/stream` | Thought process streaming |
| Backend | `/api/vision/stream` | Vision analysis streaming |
| Backend | `/api/voice/stream` | Voice processing streaming |

---

## Tauri IPC Commands (Rust)

The Rust backend (`src-tauri/`) provides IPC commands that bypass HTTP entirely. These are invoked via `invoke()` from the frontend.

### Core Commands (from `main.rs`)

#### PTY/Terminal
- `spawn_pty`, `send_input`, `resize_pty`, `read_pty`, `close_pty`
- `start_pty_output_stream`

#### AI Integration
- `ai_query`, `ai_query_stream`
- `query_ollama`, `query_ollama_stream`, `query_ollama_chat`
- `list_ollama_models`, `prewarm_model`
- `smart_process`, `smart_set_character`, `smart_clear_character`

#### File Operations
- `read_file`, `write_file`, `edit_file`
- `create_file_safe`, `append_to_file`
- `smart_edit`, `edit_line`, `insert_after_line`, `delete_lines`
- `regex_replace`, `undo_edit`
- `glob_files`, `grep_files`
- `list_directory`, `list_directory_tree`, `current_working_dir`

#### Shell/Command Execution
- `execute_shell`
- `get_shell_completions`, `get_ai_completion`

#### SSH
- `ssh_connect_password`, `ssh_connect_key`
- `ssh_send_input`, `ssh_read_output`
- `ssh_resize`, `ssh_disconnect`, `ssh_list_sessions`

#### Session/State
- `save_session`, `load_session`
- `get_session_state`, `get_history`, `get_last_command`
- `detect_project`, `get_error_suggestion`

#### Agent/AI Systems
- `start_agent_task`, `list_agent_models`, `check_ollama_status`
- `execute_agent_tool`
- `start_unified_task`, `resume_unified_task`
- `list_unified_tasks`, `get_unified_task_status`
- `intelligence_run`, `intelligence_parse`
- `intelligence_v2_run`, `intelligence_v2_parse`

#### Workflows/Multi-edit
- `workflow_create`, `workflow_add_step`, `workflow_list`
- `workflow_get`, `workflow_resolve`, `workflow_delete`, `workflow_builtins`
- `multi_edit_begin`, `multi_edit_add`, `multi_edit_commit`
- `multi_edit_rollback`, `multi_edit_list`

#### Todo Tracker
- `todo_add`, `todo_add_many`, `todo_set_status`
- `todo_list`, `todo_stats`, `todo_remove`
- `todo_clear`, `todo_clear_completed`

#### Command Palette
- `palette_search`, `palette_search_files`
- `palette_update_files`, `palette_record_usage`, `palette_recent`

#### Pane Management
- `pane_new_tab`, `pane_close_tab`, `pane_switch_tab`, `pane_list_tabs`
- `pane_split`, `pane_close`, `pane_focus`
- `pane_focus_next`, `pane_focus_prev`, `pane_active`
- `pane_set_pty`, `pane_layout`, `pane_sizes`

#### AI Options
- `ai_route_request`, `ai_routing_stats`
- `embedding_index_directory`, `embedding_search`
- `embedding_search_name`, `embedding_stats`, `embedding_save`, `embedding_load`
- `template_list`, `template_get`, `template_search`
- `template_fill`, `template_generate_prompt`
- `model_select`, `model_stats`, `model_list_available`
- `model_mark_loaded`, `model_mark_unloaded`, `model_record_result`, `model_get_idle`

#### Character System
- `cmd_list_archetypes`, `cmd_get_archetype`, `cmd_create_from_archetype`
- `cmd_parse_character_description`, `cmd_save_character`
- `cmd_list_saved_characters`, `cmd_get_character`, `cmd_delete_character`
- `cmd_toggle_favorite`, `cmd_update_character`, `cmd_update_character_traits`
- `cmd_add_dialogue_example`, `cmd_get_character_prompt`
- `cmd_search_archetypes`, `cmd_get_archetypes_by_category`
- `cmd_record_character_usage`

#### Character Memory
- `cmd_get_character_memory`, `cmd_add_character_message`
- `cmd_get_recent_character_context`, `cmd_remember_character_fact`
- `cmd_clear_character_history`, `cmd_delete_character_memory`
- `cmd_list_characters_with_memory`, `cmd_get_active_character`
- `cmd_set_active_character`, `cmd_clear_active_character`

### Brain Commands (`brain.rs`)

These call Python scripts directly via subprocess:

| Command | Python Script | Purpose |
|---------|---------------|---------|
| `get_brain_status` | Reads inventory JSON | Brain health |
| `search_projects` | `project_browser.py search` | Project search |
| `get_project_categories` | `project_browser.py categories` | Categories |
| `generate_code` | `ollama run sam-coder` | Code generation |
| `get_starred_projects` | Reads inventory JSON | Favorites |
| `add_memory` | `semantic_memory.py` | Add memory |
| `query_memory` | `semantic_memory.py` | Query memory |

---

## Mismatches: Frontend Calls with No Backend Handler

### Critical Issues

| Frontend Location | Endpoint | Issue |
|-------------------|----------|-------|
| `useCognitiveAPI.ts:speak()` | `POST /api/cognitive/speak` | **NOT IMPLEMENTED** in sam_api.py |

### Ollama Deprecation (DECOMMISSIONED 2026-01-18)

All these calls to `localhost:11434` need migration to SAM Brain MLX:

| File | Current Endpoint | Recommended Migration |
|------|------------------|----------------------|
| `useAI.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useUniversalMemory.ts` | `localhost:11434/api/embeddings` | `/api/code/search` or local MLX |
| `useMultiModel.ts` | `localhost:11434/api/tags` | `/api/status` |
| `useAIMemory.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useContextCompression.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useErrorRecovery.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useTestRunner.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useCodeExecution.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useGitAI.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useCodeExplainer.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useGitIntegration.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |
| `useScaffoldedAgent.ts` | `localhost:11434/api/tags` | `/api/status` |
| `autonomousDeveloper.ts` | `localhost:11434/api/generate` | `/api/cognitive/process` |

---

## Mismatches: Backend Endpoints Never Called

These backend endpoints exist but are **not called from the frontend**:

### Unused API Endpoints

| Endpoint | Category | Notes |
|----------|----------|-------|
| `/api/orchestrate` | Query routing | May be used internally |
| `/api/think` | Thinking | UI not implemented |
| `/api/think/stream` | Thinking | UI not implemented |
| `/api/think/colors` | Thinking | UI not implemented |
| `/api/cognitive/escalate` | Escalation | May be internal |
| `/api/vision/smart` | Vision | Auto-routing |
| `/api/vision/smart/stats` | Vision | Cache stats |
| `/api/image/chat` | Vision | Image conversation |
| `/api/image/context` | Vision | Context management |
| `/api/image/context/clear` | Vision | Clear context |
| `/api/image/followup/check` | Vision | Follow-up detection |
| `/api/code/index` | Indexing | Via Rust IPC instead |
| `/api/index/*` | Indexing | Via Rust IPC instead |
| `/api/voice/*` | Voice | Voice pipeline (Phase 6) |
| `/api/distillation/*` | Training | Review system |
| `/api/approval/*` | Approvals | Queue system |
| `/api/facts/remember` | Facts | Memory addition |
| `/api/feedback/dashboard` | Feedback | Dashboard |
| `/api/notifications` | Proactive | Alerts |

### Potentially Useful but Uncalled

| Endpoint | Suggested Frontend Integration |
|----------|-------------------------------|
| `/api/self` | SAM self-description panel |
| `/api/suggest` | Improvement suggestions UI |
| `/api/proactive` | Proactive insights notification |
| `/api/learning` | Learning progress display |
| `/api/scan` | Manual improvement trigger |
| `/api/resources` | Resource monitor widget |
| `/api/context/stats` | Token budget display |

---

## Shared Types/Schemas

### CognitiveResponse (Both sides)

**Frontend (`useCognitiveAPI.ts`):**
```typescript
interface CognitiveResponse {
  response: string
  confidence: number
  mood: string
  model_used: string | null
  escalated: boolean
  processing_time_ms?: number
}
```

**Backend (`sam_api.py`):**
```python
{
    "success": True,
    "response": str,
    "confidence": float,
    "mood": str,
    "model_used": str | None,
    "escalated": bool,
    "processing_time_ms": int
}
```

### Vision Response

**Frontend:**
```typescript
interface VisionResponse {
  response: string
  confidence: number
  model_used: string
  objects_detected?: string[]
  escalated: boolean
}
```

**Backend:**
```python
{
    "success": True,
    "response": str,
    "description": str,  # Alias
    "confidence": float,
    "model_used": str,
    "task_type": str,
    "escalated": bool,
    "escalation_reason": str | None,
    "processing_time_ms": int
}
```

---

## Recommendations

### High Priority

1. **Implement `/api/cognitive/speak`** - Frontend calls this but backend doesn't have it
2. **Migrate Ollama calls to SAM Brain** - 13 files still call decommissioned Ollama
3. **Add frontend UI for thinking endpoints** - Backend has rich thinking API unused

### Medium Priority

4. **Expose voice pipeline to frontend** - `/api/voice/*` endpoints ready
5. **Add proactive notifications UI** - `/api/notifications` exists
6. **Implement distillation review UI** - Training review system ready

### Low Priority

7. **Add resource monitoring widget** - `/api/resources` available
8. **Implement approval queue UI** - Full approval system in backend
9. **Add image chat interface** - `/api/image/chat` ready

---

## Change Log

- **2026-01-28**: Initial comprehensive mapping created
