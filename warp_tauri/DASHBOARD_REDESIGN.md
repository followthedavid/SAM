# SAM Dashboard Redesign

## Vision
Full-screen project gallery with autonomous task execution. No chat tabs - the grid IS the interface.

## Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Search & Chat Bar - Large, spans full width]                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│   │  Stash  │  │  Music  │  │  SAM    │  │  RVC    │  │ ComfyUI │  │
│   │         │  │ Library │  │Terminal │  │ Voice   │  │         │  │
│   │  [icon] │  │  [icon] │  │  [icon] │  │  [icon] │  │  [icon] │  │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │
│                                                                     │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  │
│   │  SSOT   │  │ Account │  │Cloudflr │  │ Topaz   │  │   ...   │  │
│   │ System  │  │  Auto   │  │ Tunnel  │  │ Parity  │  │         │  │
│   │  [icon] │  │  [icon] │  │  [icon] │  │  [icon] │  │  [icon] │  │
│   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘  │
│                                                                     │
│                    [Gallery fills 90% of screen]                    │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Card Click → Expand In-Place

When clicking a project card, it expands to show:

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Search & Chat Bar]                                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐  │
│   │  STASH PROJECT                                    [X Close] │  │
│   ├─────────────────────────────────────────────────────────────┤  │
│   │                                                             │  │
│   │  METRICS                                                    │  │
│   │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│   │  Lines of Code: 2,847                                       │  │
│   │  Files Modified: 23                                         │  │
│   │  Last Activity: 2 hours ago                                 │  │
│   │                                                             │  │
│   │  GOALS                                           [73%] ████░│  │
│   │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│   │  • Organize 5000 scenes with metadata       ✓ Complete      │  │
│   │  • Auto-tag performers via StashDB          ✓ Complete      │  │
│   │  • Generate preview thumbnails              ◐ 73% (3,650)   │  │
│   │  • Set up Cloudflare caching                ○ Pending       │  │
│   │                                                             │  │
│   │  SUGGESTED TASKS (10+ hours)                    [Approve All]│  │
│   │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│   │  □ Regenerate all scene previews (4h est.)     [Approve]    │  │
│   │  □ Run StashDB identify on unmatched (2h)      [Approve]    │  │
│   │  □ Warm Cloudflare cache for all thumbs (1h)   [Approve]    │  │
│   │  □ Clean duplicate performers (30m)            [Approve]    │  │
│   │  □ Export metadata backup to SSOT (15m)        [Approve]    │  │
│   │  □ Analyze scene quality scores (2h)           [Approve]    │  │
│   │                                                             │  │
│   │  RUNNING IN BACKGROUND                                      │  │
│   │  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ │  │
│   │  ▶ Preview generation: 73% (ETA 45min)         [Pause]      │  │
│   │                                                             │  │
│   └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│   ┌─────────┐  ┌─────────┐  ┌─────────┐  (other cards dimmed)      │
│   │  Music  │  │  SAM    │  │  RVC    │                            │
│   └─────────┘  └─────────┘  └─────────┘                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## Data Model

### Project Schema
```typescript
interface Project {
  id: string
  name: string
  icon: string

  // Metrics
  metrics: {
    linesOfCode: number
    filesModified: number
    lastActivity: Date
  }

  // Goals with progress
  goals: Array<{
    id: string
    description: string
    status: 'pending' | 'in_progress' | 'complete'
    progress?: number  // 0-100 for in_progress
  }>

  // Suggested autonomous tasks
  suggestedTasks: Array<{
    id: string
    description: string
    estimatedHours: number
    approved: boolean
    command: string  // What to execute
  }>

  // Currently running background tasks
  runningTasks: Array<{
    id: string
    description: string
    progress: number
    eta?: string
    pid?: number
  }>
}
```

## Implementation Steps

### Phase 1: Layout Restructure
1. Remove tab bar (or minimize to icon)
2. Make TopicGrid full-screen
3. Add large search/chat bar at top
4. Style cards for gallery feel

### Phase 2: Project Expansion
1. Click handler expands card in-place
2. Fetch project metrics from backend
3. Display goals with progress bars
4. Show suggested tasks list

### Phase 3: Task Suggestion Engine
1. Backend analyzes each project
2. Generates 10+ hours of actionable tasks
3. Tasks have estimated duration
4. Tasks have executable commands

### Phase 4: Background Execution
1. Approve button queues task
2. Task runs via Rust backend
3. Progress tracked and displayed
4. Results feed back to metrics

## Files to Modify

- `src/App.vue` - Remove tab bar, full-screen grid
- `src/components/TopicGrid.vue` - Gallery layout, card expansion
- `src/components/ProjectPanel.vue` - NEW: Expanded project view
- `src/stores/topicStore.js` - Add metrics, goals, tasks
- `src-tauri/src/commands.rs` - Task execution commands
- `src-tauri/src/scaffolding/task_engine.rs` - NEW: Task suggestion/execution

## 24-Hour Progress View

A collapsible panel (or toggle) showing everything accomplished in the last 24 hours:

```
┌─────────────────────────────────────────────────────────────────────┐
│  [Search & Chat Bar]                              [24h Progress ▼]  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │  LAST 24 HOURS                                    Total: 47 tasks│
│  ├───────────────────────────────────────────────────────────────┤ │
│  │                                                               │ │
│  │  TODAY                                                        │ │
│  │  ─────────────────────────────────────────────────────────── │ │
│  │  19:30  ✓ Stash: Generated 1,350 preview thumbnails          │ │
│  │  18:45  ✓ Music: Imported 847 new tracks via beets           │ │
│  │  17:20  ✓ SAM: Rebuilt with model fix (qwen2.5-coder)        │ │
│  │  16:00  ✓ Stash: Identified 230 performers via StashDB       │ │
│  │  14:30  ✓ Cloudflare: Cache warmed for 2,500 thumbnails      │ │
│  │  12:15  ✓ RVC: Training checkpoint saved (epoch 50)          │ │
│  │                                                               │ │
│  │  YESTERDAY                                                    │ │
│  │  ─────────────────────────────────────────────────────────── │ │
│  │  23:45  ✓ Music: Fixed featured artists metadata             │ │
│  │  22:00  ✓ SSOT: Full context scan completed                  │ │
│  │  20:30  ✓ Stash: Preview settings updated (1min samples)     │ │
│  │  ...                                                          │ │
│  │                                                               │ │
│  │  SUMMARY                                                      │ │
│  │  ─────────────────────────────────────────────────────────── │ │
│  │  Stash:     12 tasks  ████████████░░░░  (4.2h)               │ │
│  │  Music:      8 tasks  ████████░░░░░░░░  (2.8h)               │ │
│  │  SAM:        6 tasks  ██████░░░░░░░░░░  (1.5h)               │ │
│  │  RVC:        4 tasks  ████░░░░░░░░░░░░  (3.0h)               │ │
│  │  Other:     17 tasks  █████████████████  (5.1h)              │ │
│  │                                                               │ │
│  │  Total work: 16.6 hours across 5 projects                    │ │
│  │                                                               │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│   [Gallery Grid below or behind]                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Activity Log Schema
```typescript
interface ActivityEntry {
  id: string
  timestamp: Date
  project: string
  action: string
  details?: string
  duration?: number  // seconds
  status: 'success' | 'failed' | 'partial'
}

interface DailySummary {
  date: Date
  totalTasks: number
  totalHours: number
  byProject: Record<string, {
    tasks: number
    hours: number
  }>
  entries: ActivityEntry[]
}
```

### Storage
- Activity log stored in SQLite (already have rusqlite)
- Persists across sessions
- Query: `SELECT * FROM activity WHERE timestamp > datetime('now', '-24 hours')`

## Search/Chat Bar Behavior

The top bar serves dual purpose:
1. **Search**: Filter projects, search within project
2. **Chat**: Natural language commands that affect all projects
   - "Show me projects with pending tasks"
   - "What's running in background?"
   - "Approve all suggested tasks for Stash"
   - "What did we accomplish today?"
