# SAM Perpetual Ladder Architecture

## Vision
A self-improving AI system that autonomously evolves across multiple dimensions (coding, reasoning, creativity, personality) through continuous learning cycles.

---

## Core Principles

1. **Measure Everything** - Every action produces measurable outcomes
2. **Learn From Failure** - Failures are more valuable than successes
3. **Small Increments** - Prefer many small improvements over big changes
4. **Verify Before Commit** - No change without verification
5. **Track Evolution** - Progress is quantified across dimensions

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PERPETUAL LADDER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐          │
│  │   PLANNER    │───▶│   EXECUTOR   │───▶│   VERIFIER   │          │
│  │  (Ollama)    │    │ (Claude Code)│    │  (tsc/cargo) │          │
│  └──────────────┘    └──────────────┘    └──────────────┘          │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│  ┌─────────────────────────────────────────────────────┐           │
│  │                   LEARNING DATABASE                  │           │
│  │  • Task outcomes (success/failure/partial)          │           │
│  │  • Pattern recognition (what works where)           │           │
│  │  • Evolution levels (per project, per dimension)    │           │
│  │  • Confidence scores (how sure are we)              │           │
│  └─────────────────────────────────────────────────────┘           │
│                              │                                      │
│                              ▼                                      │
│  ┌─────────────────────────────────────────────────────┐           │
│  │                 TRAINING DATA PIPELINE               │           │
│  │  • Success patterns → training examples             │           │
│  │  • Failure patterns → negative examples             │           │
│  │  • Periodic retraining with new data                │           │
│  └─────────────────────────────────────────────────────┘           │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Evolution Dimensions

### 1. Code Quality (Level 1-5)
| Level | Name | Capabilities |
|-------|------|--------------|
| 1 | Basic | Fix typos, add comments |
| 2 | Functional | Add simple functions, fix bugs |
| 3 | Integrated | Modify multiple files coherently |
| 4 | Autonomous | Design and implement features |
| 5 | Mastery | Architectural decisions, optimization |

### 2. Reasoning (Level 1-5)
| Level | Name | Capabilities |
|-------|------|--------------|
| 1 | Reactive | Respond to direct questions |
| 2 | Analytical | Break down complex problems |
| 3 | Strategic | Multi-step planning |
| 4 | Predictive | Anticipate issues |
| 5 | Creative | Novel solutions |

### 3. Personality (Level 1-5)
| Level | Name | Capabilities |
|-------|------|--------------|
| 1 | Neutral | Basic responses |
| 2 | Consistent | Maintains tone |
| 3 | Expressive | Emotional range |
| 4 | Adaptive | Matches user mood |
| 5 | Authentic | Unique voice |

### 4. Integration (Level 1-5)
| Level | Name | Capabilities |
|-------|------|--------------|
| 1 | Isolated | Single tool usage |
| 2 | Connected | Multiple tool chaining |
| 3 | Orchestrated | Smart routing |
| 4 | Autonomous | Self-directed workflow |
| 5 | Emergent | Creates new integrations |

---

## Data Collection Strategy

### Training Data Sources

| Source | Purpose | Target Size | Status |
|--------|---------|-------------|--------|
| Nifty Stories | Roleplay, creativity | 100K+ stories | In progress |
| Fashion Articles | Style, personality | 300K+ articles | In progress |
| GitHub PRs | Code improvement patterns | 10K+ diffs | In progress |
| Stack Overflow | Problem-solving | 50K+ Q&As | Planned |
| SAM Interactions | Self-learning | Continuous | Active |

### Data Quality Filters
- Minimum word count: 500+ words
- No duplicate content
- Language detection (English only)
- Quality scoring (engagement, votes, stars)

---

## Learning Database Schema

```sql
-- Tasks and outcomes
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    project_id TEXT,
    task_type TEXT,          -- code|test|docs|refactor|feature
    description TEXT,
    status TEXT,             -- pending|executing|verifying|success|failed
    execution_time_seconds INTEGER,
    error_message TEXT,
    files_changed INTEGER,
    created_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- Learning patterns
CREATE TABLE learning_patterns (
    id INTEGER PRIMARY KEY,
    project_id TEXT,
    task_type TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    avg_execution_time REAL,
    common_errors TEXT,      -- JSON array
    best_practices TEXT,     -- JSON array
    updated_at TIMESTAMP
);

-- Evolution tracking
CREATE TABLE evolution (
    project_id TEXT PRIMARY KEY,
    code_level INTEGER DEFAULT 1,
    reasoning_level INTEGER DEFAULT 1,
    personality_level INTEGER DEFAULT 1,
    integration_level INTEGER DEFAULT 1,
    total_improvements INTEGER DEFAULT 0,
    last_level_up TIMESTAMP
);

-- Daily metrics
CREATE TABLE daily_stats (
    date TEXT PRIMARY KEY,
    tasks_attempted INTEGER,
    tasks_succeeded INTEGER,
    tasks_failed INTEGER,
    total_files_changed INTEGER,
    total_execution_time INTEGER
);
```

---

## Cycle Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                     PERPETUAL CYCLE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. ANALYZE                                                     │
│     • Check project registry for active projects                │
│     • Review learning database for patterns                     │
│     • Calculate success rates per task type                     │
│                                                                  │
│  2. SELECT                                                      │
│     • Choose project (weighted by priority + success rate)      │
│     • Choose task type (prefer higher success patterns)         │
│     • Generate specific task (via Ollama)                       │
│                                                                  │
│  3. EXECUTE                                                     │
│     • Spawn Claude Code with task prompt                        │
│     • Monitor execution (timeout handling)                      │
│     • Capture output and changes                                │
│                                                                  │
│  4. VERIFY                                                      │
│     • Run type checks (tsc --noEmit)                           │
│     • Run build (cargo check)                                   │
│     • Run tests (if applicable)                                 │
│     • Check for regressions                                     │
│                                                                  │
│  5. LEARN                                                       │
│     • Record outcome (success/failure/partial)                  │
│     • Update pattern database                                   │
│     • Adjust confidence scores                                  │
│     • Check for level-up conditions                             │
│                                                                  │
│  6. WAIT                                                        │
│     • Cooldown period (10-60 min based on outcomes)            │
│     • Backoff on repeated failures                              │
│                                                                  │
│  7. REPEAT                                                      │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Level-Up Conditions

A project advances to the next level when:

| Current Level | Requirement to Level Up |
|---------------|------------------------|
| 1 → 2 | 10 successful tasks, 60%+ success rate |
| 2 → 3 | 25 successful tasks, 70%+ success rate |
| 3 → 4 | 50 successful tasks, 75%+ success rate |
| 4 → 5 | 100 successful tasks, 80%+ success rate |

---

## Guardrails

### Dangerous Operations (Require Approval)
- `rm`, `delete`, `remove`
- `git push --force`
- `drop`, `truncate`
- Any operation on production data

### Auto-Approved Operations
- `lint`, `format`, `test`, `build`
- `git add`, `git commit`
- Documentation changes
- Type annotation additions

### Resource Limits
- Max file size: 100MB
- Max execution time: 30 minutes
- Max files per task: 10
- Large outputs → external drive only

---

## Integration Points

### Current
- **Ollama**: Task planning (local LLM)
- **Claude Code**: Task execution
- **SQLite**: Learning database
- **Git**: Version control

### Planned
- **MLX**: Local model training
- **ComfyUI**: Visual generation
- **RVC**: Voice synthesis
- **Unity**: 3D avatar

---

## Monitoring & Observability

### Logs
- `~/.sam/logs/perpetual_daemon.log` - Main daemon log
- `~/.sam/logs/tasks/` - Per-task execution logs

### Commands
```bash
# Check status
python3 perpetual_daemon.py status

# View learning history
python3 perpetual_daemon.py history

# Check evolution levels
python3 perpetual_daemon.py evolution

# View daily stats
python3 perpetual_daemon.py stats
```

### Metrics Dashboard (Planned)
- Tasks per day (success/failure)
- Evolution level trends
- Execution time trends
- Error pattern analysis

---

## Roadmap

### Phase 1: Foundation (Current)
- [x] Basic perpetual loop
- [x] Task selection via Ollama
- [x] Execution via Claude Code
- [x] Learning database
- [x] Evolution tracking
- [ ] Fix TypeScript verification issues
- [ ] Complete training data collection

### Phase 2: Intelligence
- [ ] Pattern-based task selection
- [ ] Confidence scoring
- [ ] Failure analysis
- [ ] Automatic retry with different approach

### Phase 3: Self-Training
- [ ] Export success patterns to training data
- [ ] Periodic MLX fine-tuning
- [ ] A/B testing of model versions
- [ ] Automated model deployment

### Phase 4: Multi-Modal
- [ ] Visual generation integration
- [ ] Voice synthesis integration
- [ ] Cross-modal learning

### Phase 5: Autonomy
- [ ] Self-directed goal setting
- [ ] Resource management
- [ ] Priority optimization
- [ ] Emergent capabilities

---

## Files & Locations

| File | Purpose |
|------|---------|
| `perpetual_daemon.py` | Main daemon implementation |
| `evolution_tracker.py` | Evolution level management |
| `evolution_ladders.py` | Level definitions |
| `improvement_detector.py` | Scans for opportunities |
| `sam_intelligence.py` | Self-awareness system |
| `~/.sam/perpetual_ladder.db` | Learning database |
| `~/.sam/projects/registry.json` | Project configuration |

---

## Contributing

When modifying the perpetual ladder system:

1. **Test locally first** - Run `python3 perpetual_daemon.py once`
2. **Check learning impact** - Verify database updates
3. **Update this document** - Keep architecture docs current
4. **Monitor after deploy** - Watch logs for regressions

---

*Last updated: 2026-01-15*
*Version: 1.0.0*
