# RuFlo (claude-flow) V3.5 -- Comprehensive Audit Report

> Audit date: 2026-03-20
> Official source: https://github.com/ruvnet/ruflo (README.md)
> Local installation: `.claude-flow/`, `.claude/helpers/`, `.claude/settings.json`

---

## 1. Feature Comparison: Official Docs vs Local Installation

### 1.1 Core Systems

| Feature | Documented in RuFlo | Installed Locally | Working | Notes |
|---------|:-------------------:|:-----------------:|:-------:|-------|
| CLI (`npx ruflo@latest`) | YES | PARTIAL | UNKNOWN | Not in `package.json` as dependency; relies on `npx` remote fetch |
| Config file (`config.yaml`) | YES | YES | YES | Well-configured with project integration |
| CAPABILITIES.md reference | YES | YES | YES | Comprehensive, matches docs |
| `.claude-flow/` directory structure | YES | PARTIAL | PARTIAL | Missing: `data/`, `logs/`, `sessions/`, `hooks/`, `workflows/`, `neural/` -- all empty |
| Agent team definitions | YES | YES | YES | `impuestify-team.yaml` with 10 agents, routing rules, quality gates |
| Hook handler dispatch | YES | YES | YES | `hook-handler.cjs` handles 11 commands |
| Statusline | YES | YES | YES | `statusline.cjs` is comprehensive, reads stdin JSON from Claude Code |
| Task router | YES | YES | PARTIAL | `router.js` uses simple keyword matching only -- no ML/SONA |
| Session manager | YES | YES | YES | `session.js` handles start/restore/end/metrics |
| Memory helper | YES | YES | MINIMAL | `memory.js` is basic key-value JSON -- no vector search |
| Intelligence layer | YES | YES | YES | `intelligence.cjs` has PageRank, trigram matching, confidence evolution |
| Auto-memory bridge | YES | YES | DEGRADED | `auto-memory-hook.mjs` tries to import `@claude-flow/memory` -- package NOT installed |
| Learning service | YES | YES | NOT WORKING | `learning-service.mjs` requires `better-sqlite3` -- NOT installed |
| Metrics DB | YES | YES | NOT WORKING | `metrics-db.mjs` requires `sql.js` -- NOT installed |

### 1.2 Advanced Systems

| Feature | Documented | Installed | Working | Notes |
|---------|:----------:|:---------:|:-------:|-------|
| **Swarm Orchestration** (6 topologies) | YES | CONFIG ONLY | NO | Config says `hierarchical-mesh`, but no actual swarm runtime. `swarm-state.json` tracks agents via hooks only |
| **HNSW Vector Search** (150x-12500x) | YES | CODE EXISTS | NOT WORKING | `learning-service.mjs` has HNSW implementation but `better-sqlite3` dep missing |
| **SONA Neural Learning** | YES | CONFIG ONLY | NO | Config enables it, but no SONA runtime code exists locally |
| **MCP Server** (259 tools) | YES | NOT CONFIGURED | NO | `.mcp.json` has playwright/stitch/nanobanana -- NO ruflo MCP server |
| **Hive-Mind Consensus** | YES | NOT INSTALLED | NO | No hive-mind runtime or data files |
| **Background Workers** (12 types) | YES | CONFIG ONLY | NO | `settings.json` lists 10 workers but no daemon process runs them |
| **Security Scanner** | YES | STUB ONLY | NO | `audit-status.json` has `lastScan: null`, no actual scanner |
| **Agent Booster (WASM)** | YES | NOT INSTALLED | NO | No WASM files or agentic-flow package |
| **AgentDB** (20+ controllers) | YES | NOT INSTALLED | NO | No `@claude-flow/memory` or `agentdb` package |
| **RuVector PostgreSQL Bridge** | YES | NOT INSTALLED | NO | No PostgreSQL integration |
| **Plugins System** | YES | NOT INSTALLED | NO | No plugin files or configs |
| **Embeddings (ONNX)** | YES | CODE EXISTS | NOT WORKING | `learning-service.mjs` has fallback hash embeddings but no ONNX model |
| **ADR System** | YES | CONFIG ONLY | NO | `adr` config exists but no ADR directory or files |
| **DDD Tracking** | YES | CONFIG ONLY | NO | `ddd` config exists but no domain tracking |
| **Multi-provider LLM** | YES | NOT CONFIGURED | NO | No provider configuration beyond Anthropic |
| **GitHub Integration** | YES | NOT INSTALLED | NO | No PR manager, issue tracker, etc. |

### 1.3 CLI Commands Availability

| CLI Command | Documented Subcommands | Available Locally | Notes |
|-------------|:----------------------:|:-----------------:|-------|
| `init` | 4 | UNTESTED | Ran once (`npx ruflo@latest init --wizard`) |
| `agent` | 8 | PARTIAL | `agents/store.json` has 1 agent entry |
| `swarm` | 6 | UNTESTED | Config only |
| `memory` | 11 | UNTESTED | No npm dependency installed |
| `mcp` | 9 | NOT CONFIGURED | No ruflo MCP in `.mcp.json` |
| `task` | 6 | PARTIAL | `tasks/store.json` has 2 pending tasks |
| `session` | 7 | UNTESTED | Local `session.js` provides basic impl |
| `config` | 7 | UNTESTED | `config.yaml` exists |
| `hooks` | 17+ | BYPASSED | Hooks run via `.claude/helpers/` not via CLI |
| `hive-mind` | 6 | NOT INSTALLED | No runtime |
| `neural` | 5 | NOT INSTALLED | No runtime |
| `security` | 6 | NOT INSTALLED | No scanner |
| `daemon` | 5 | NOT INSTALLED | No daemon process |
| `doctor` | 1 | UNTESTED | |
| `plugins` | 5 | NOT INSTALLED | |
| `embeddings` | 4 | NOT INSTALLED | |
| `providers` | 5 | NOT INSTALLED | |
| `ruvector` | 6 | NOT INSTALLED | |

---

## 2. Hooks Audit

### 2.1 Claude Code Hook Events Configured (settings.json)

| Hook Event | Configured | Handler | Working |
|------------|:----------:|---------|:-------:|
| `PreToolUse` (Bash) | YES | `hook-handler.cjs pre-bash` | YES -- basic dangerous-command check |
| `PreToolUse` (Write/Edit/MultiEdit) | YES | `hook-handler.cjs pre-edit` | YES -- but pre-edit has no handler (falls to pass-through) |
| `PostToolUse` (Write/Edit/MultiEdit) | YES | `hook-handler.cjs post-edit` | YES -- records edit for session metrics + intelligence |
| `PostToolUse` (Bash) | YES | `hook-handler.cjs post-bash` | PASS-THROUGH -- no `post-bash` handler defined |
| `UserPromptSubmit` | YES | `hook-handler.cjs route` | YES -- runs router + intelligence context |
| `SessionStart` | YES | `hook-handler.cjs session-restore` + `auto-memory-hook.mjs import` | PARTIAL -- session restore works; auto-memory import fails (missing package) |
| `SessionEnd` | YES | `hook-handler.cjs session-end` | YES -- intelligence consolidation + session archive |
| `Stop` | YES | `auto-memory-hook.mjs sync` | DEGRADED -- sync fails (missing package), exits silently |
| `PreCompact` (manual) | YES | `hook-handler.cjs compact-manual` + `session-end` | PASS-THROUGH -- no `compact-manual` handler |
| `PreCompact` (auto) | YES | `hook-handler.cjs compact-auto` + `session-end` | PASS-THROUGH -- no `compact-auto` handler |
| `SubagentStart` | YES | `hook-handler.cjs status` | YES -- writes to swarm-state.json |
| `SubagentStop` | YES | `hook-handler.cjs agent-stop` | YES -- updates swarm-state.json |
| `Notification` | YES | `hook-handler.cjs notify` | PASS-THROUGH -- no `notify` handler |

### 2.2 hook-handler.cjs Defined Handlers vs Registered Hooks

| Handler | Defined in hook-handler.cjs | Called by settings.json | Gap |
|---------|:---------------------------:|:----------------------:|-----|
| `route` | YES | YES (UserPromptSubmit) | -- |
| `pre-bash` | YES | YES (PreToolUse Bash) | -- |
| `post-edit` | YES | YES (PostToolUse Write/Edit) | -- |
| `session-restore` | YES | YES (SessionStart) | -- |
| `session-end` | YES | YES (SessionEnd, PreCompact) | -- |
| `status` | YES | YES (SubagentStart) | -- |
| `agent-stop` | YES | YES (SubagentStop) | -- |
| `pre-task` | YES | NOT CALLED | GAP: Defined but never triggered |
| `post-task` | YES | NOT CALLED | GAP: Defined but never triggered |
| `stats` | YES | NOT CALLED | GAP: Diagnostic only, no hook |
| `pre-edit` | NOT DEFINED | YES (PreToolUse Write/Edit) | GAP: Registered but handler missing -- falls to pass-through |
| `post-bash` | NOT DEFINED | YES (PostToolUse Bash) | GAP: Registered but handler missing -- falls to pass-through |
| `compact-manual` | NOT DEFINED | YES (PreCompact) | GAP: Falls to pass-through |
| `compact-auto` | NOT DEFINED | YES (PreCompact) | GAP: Falls to pass-through |
| `notify` | NOT DEFINED | YES (Notification) | GAP: Falls to pass-through |

### 2.3 RuFlo Documented Hooks vs Installed

Of the 27 documented hooks in CAPABILITIES.md:

| Category | Documented | Implemented | Gap |
|----------|:---------:|:-----------:|-----|
| Core (pre/post-edit, pre/post-command, pre/post-task) | 6 | 4 of 6 | Missing: pre-command, post-command |
| Session (start, end, restore, notify) | 4 | 3 of 4 | notify is pass-through |
| Intelligence (route, explain, pretrain, build-agents, transfer) | 5 | 1 of 5 | Only `route` implemented |
| Coverage (route, suggest, gaps) | 3 | 0 of 3 | None implemented |
| Worker hooks (12 background workers) | 12 | 0 of 12 | None running |

**Summary: 8 of 27 hooks are functional, 5 are registered but pass-through, 14 are not implemented at all.**

---

## 3. Swarm Bridge (SubagentStart/SubagentStop)

### Status: WORKING

The bridge between Claude Code's `SubagentStart`/`SubagentStop` events and `.claude-flow/swarm/swarm-state.json` is correctly implemented:

- `SubagentStart` --> `hook-handler.cjs status` --> Creates/updates agent entry in `swarm-state.json` + `swarm-activity.json`
- `SubagentStop` --> `hook-handler.cjs agent-stop` --> Marks agent as `completed`, decrements count
- Statusline reads `swarm-state.json` to display active agents
- Has 5-minute staleness check -- stale state shows 0 agents

### Issues:
1. Agent info extraction from stdin relies on `hookInput.agent_name` / `hookInput.subagent_type` which may not be provided by Claude Code -- falls back to timestamp-based IDs
2. No cleanup of completed agents from the state file -- grows indefinitely
3. Current state: `agentCount: 0`, `coordinationActive: false` -- no agents active

---

## 4. Intelligence/Learning (SONA)

### Status: PARTIALLY WORKING (Local Implementation Only)

**What works:**
- `intelligence.cjs` provides a functional PageRank-based intelligence layer:
  - Builds knowledge graph from auto-memory-store.json
  - Computes PageRank over memory entries
  - Trigram-based Jaccard similarity matching for context retrieval
  - Confidence boosting/decay based on pattern usage
  - Consolidation pipeline (process pending insights, rebuild edges, recompute PageRank)
  - Snapshot history for delta tracking and trend analysis
  - Bootstraps from MEMORY.md files when store is empty

**What does NOT work:**
- **SONA (Self-Optimizing Neural Architecture)**: Not implemented. Config says `neural.enabled: true` but there is no SONA runtime code. The `intelligence.cjs` uses trigram matching, not neural embeddings.
- **EWC++ (Elastic Weight Consolidation)**: Not implemented
- **MoE (Mixture of Experts) routing**: Not implemented
- **Flash Attention**: Not implemented
- **LoRA/MicroLoRA**: Not implemented
- **Real RL algorithms** (PPO, A2C, DQN, etc.): Not implemented

**learning-service.mjs** has an HNSW index + SQLite persistence + ONNX embeddings system, BUT:
- Requires `better-sqlite3` npm package -- NOT installed
- Requires `agentic-flow` for ONNX embeddings -- NOT installed
- Falls back to hash-based embeddings (not semantic)
- **This module is completely non-functional** due to missing dependencies

### Metrics State (learning.json):
```json
{
  "patterns": { "shortTerm": 0, "longTerm": 0, "quality": 0 },
  "sessions": { "total": 0, "current": null },
  "routing": { "accuracy": 0, "decisions": 0 }
}
```

All zeros -- no learning has occurred.

---

## 5. Memory System (AgentDB / Vector Memory)

### Status: MINIMAL (JSON-only, No Vector Search)

| Component | Documented | Local Status |
|-----------|:----------:|:------------:|
| AgentDB with 20+ controllers | YES | NOT INSTALLED |
| HNSW vector indexing | YES | CODE EXISTS (learning-service.mjs) but broken deps |
| SQLite cache with WAL | YES | NOT INSTALLED (no better-sqlite3) |
| Knowledge graph with PageRank | YES | YES -- in intelligence.cjs (works) |
| ReasoningBank | YES | NOT INSTALLED |
| Hyperbolic Poincare embeddings | YES | NOT INSTALLED |
| 3-scope agent memory | YES | CONFIG ONLY (agentScopes.enabled: true) |
| Cross-session persistence | YES | PARTIAL -- session.js archives sessions, intelligence.cjs has snapshots |

**What actually exists for memory:**
1. `memory.js` -- Simple key-value JSON file (`memory.json`) -- no namespaces, no search
2. `intelligence.cjs` -- PageRank knowledge graph over `auto-memory-store.json` -- works but is trigram-based, not vector
3. `auto-memory-hook.mjs` -- Bridge to `@claude-flow/memory` package -- FAILS because package is not installed
4. `.claude-flow/data/` -- EMPTY directory. No `auto-memory-store.json`, no `graph-state.json`, no `ranked-context.json`

**The intelligence layer has never run** because there is no data in `.claude-flow/data/`.

---

## 6. MCP Server

### Status: NOT CONFIGURED

| Check | Result |
|-------|--------|
| ruflo MCP in `.mcp.json` | NO -- only playwright, stitch, nanobanana, google_workspace |
| `claude mcp add ruflo` executed | NO |
| MCP autoStart in config.yaml | `false` |
| MCP tools available | 0 of 259 documented |

The documented MCP setup command has never been run:
```bash
claude mcp add ruflo -- npx -y ruflo@latest
```

---

## 7. Missing Features (Documented but Not Installed/Configured)

### Critical (Would Unlock Major Capabilities)

1. **npm dependency `ruflo`/`claude-flow`**: Not in `package.json`. All CLI commands rely on `npx` remote fetch, which is slow and unreliable.
2. **MCP Server**: Not configured. This would provide 259 tools to Claude Code natively.
3. **`@claude-flow/memory` package**: Not installed. The auto-memory bridge, learning bridge, and memory graph all fail silently.
4. **`better-sqlite3` package**: Not installed. The learning service with HNSW is completely broken.
5. **`agentic-flow` package**: Not installed. ONNX embeddings unavailable.
6. **`sql.js` package**: Not installed. Metrics database is non-functional.
7. **Background daemon**: Never started (`npx ruflo@latest daemon start`). All 12 workers are dormant.
8. **Doctor diagnostics**: Never run (`npx ruflo@latest doctor --fix`).

### Important (Would Improve Quality)

9. **Missing directories**: `data/`, `logs/`, `sessions/`, `hooks/`, `workflows/`, `neural/` are all empty or non-existent under `.claude-flow/`
10. **Security scanner**: Never run. `audit-status.json` has `lastScan: null`.
11. **Pre-edit handler**: Registered in settings.json but not defined in hook-handler.cjs.
12. **Post-bash handler**: Registered but not defined.
13. **Compact handlers**: Registered but not defined.
14. **Notify handler**: Registered but not defined.
15. **Pre-task/post-task hooks**: Defined in handler but not triggered by any Claude Code event.

### Nice-to-Have (Advanced Features)

16. **Hive-Mind consensus**: Not installed (requires runtime)
17. **Multi-provider LLM**: Not configured (only Anthropic)
18. **Plugin system**: Not installed
19. **GitHub integration agents**: Not installed
20. **RuVector PostgreSQL bridge**: Not installed
21. **ADR generation**: Not configured (no ADR directory)
22. **DDD domain tracking**: Not configured (no DDD directory)

---

## 8. Broken Features (Installed but Not Working)

| Feature | Symptom | Root Cause |
|---------|---------|------------|
| Auto-memory import (SessionStart) | Fails silently | `@claude-flow/memory` package not installed |
| Auto-memory sync (Stop) | Fails silently | `@claude-flow/memory` package not installed |
| Learning service | Cannot initialize | `better-sqlite3` not in package.json |
| Metrics DB sync | Cannot initialize | `sql.js` not in package.json |
| HNSW vector search | No embeddings generated | Missing `agentic-flow` + `better-sqlite3` |
| Intelligence init | No data to index | `.claude-flow/data/` is empty -- bootstrap never ran |
| Background workers | All dormant | Daemon never started |
| Pre-edit hook | Falls to pass-through | Handler not defined in hook-handler.cjs |
| Post-bash hook | Falls to pass-through | Handler not defined in hook-handler.cjs |
| Compact hooks | Fall to pass-through | Handlers not defined in hook-handler.cjs |
| Notification hook | Falls to pass-through | Handler not defined in hook-handler.cjs |
| Task store | 2 tasks stuck in `pending` | No agent processing them |
| Agent store | 1 agent in `idle` | No task assignment loop |

---

## 9. Recommendations (Priority-Ordered)

### P0 -- Critical (Do First)

1. **Install core npm dependencies**:
   ```bash
   npm install ruflo@latest
   npm install better-sqlite3 sql.js
   ```
   This unlocks: CLI commands without npx delay, learning service, metrics DB.

2. **Add ruflo MCP server**:
   ```bash
   claude mcp add ruflo -- npx -y ruflo@latest
   ```
   This gives Claude Code native access to 259 ruflo tools.

3. **Run doctor diagnostics**:
   ```bash
   npx ruflo@latest doctor --fix
   ```
   This should detect and auto-fix missing directories and config issues.

4. **Bootstrap the intelligence data**:
   - Run `node .claude/helpers/intelligence.cjs init` to bootstrap from MEMORY.md files
   - This populates `.claude-flow/data/auto-memory-store.json`, `graph-state.json`, `ranked-context.json`
   - The intelligence layer will then provide actual context to the `route` hook

### P1 -- Important (Do This Week)

5. **Add missing hook handlers** in `hook-handler.cjs`:
   - `pre-edit`: Could provide file context before edits (e.g., check if file is in a hot path)
   - `post-bash`: Could record command execution patterns
   - `compact-manual` / `compact-auto`: Could save intelligence state before compaction
   - `notify`: Could log cross-agent notifications

6. **Wire pre-task and post-task to Claude Code events**:
   - These handlers exist but are never called. Wire them to appropriate lifecycle events.

7. **Start the daemon** for background workers:
   ```bash
   npx ruflo@latest daemon start
   ```
   This enables: audit, optimize, consolidate, testgaps, ultralearn, deepdive, document, refactor, benchmark workers.

8. **Run security scan**:
   ```bash
   npx ruflo@latest security scan
   ```

9. **Upgrade router from keyword to semantic**:
   - Current `router.js` uses basic regex pattern matching
   - The `impuestify-team.yaml` has richer routing rules that are NOT connected to the router
   - Should integrate the team YAML patterns OR use SONA-based routing

### P2 -- Medium Priority (Next 2 Weeks)

10. **Create missing directories** with initial data:
    ```
    .claude-flow/data/       -- auto-memory-store.json
    .claude-flow/logs/       -- operation logs
    .claude-flow/sessions/   -- session archives
    .claude-flow/hooks/      -- custom hook scripts
    .claude-flow/workflows/  -- workflow templates
    .claude-flow/neural/     -- neural model data
    ```

11. **Connect impuestify-team.yaml routing rules to the actual router**:
    - The team file defines 8 domain-based routing rules
    - These are ignored by `router.js` which has its own hardcoded patterns
    - Should read from YAML or merge patterns

12. **Fix settings.json hook conflicts**:
    - `settings.json` (project) defines the comprehensive ruflo hooks
    - `settings.local.json` (local) defines DIFFERENT hooks (bash-gate.js, quality-check.js)
    - Claude Code merges these -- potential conflicts or double-execution
    - Should consolidate into one coherent hook chain

13. **Initialize ADR and DDD directories**:
    ```bash
    mkdir -p docs/adr docs/ddd
    npx ruflo@latest init --skills
    ```

### P3 -- Nice-to-Have (Backlog)

14. **Install optional MCP servers**: ruv-swarm, flow-nexus for extended swarm capabilities
15. **Configure multi-provider LLM failover**: Add OpenAI/Google as fallback providers
16. **Install plugins**: agentic-qe, prime-radiant for advanced capabilities
17. **Set up RuVector** if PostgreSQL is available
18. **Enable hive-mind consensus** for multi-agent decision making

---

## 10. Summary Scorecard

| Category | Score | Notes |
|----------|:-----:|-------|
| Configuration | 8/10 | Well-structured config.yaml, settings.json, team YAML |
| Hooks Integration | 5/10 | 8 of 27 functional, 5 pass-through, 14 missing |
| Swarm Bridge | 7/10 | Works for SubagentStart/Stop but no actual orchestration |
| Intelligence/Learning | 3/10 | PageRank layer exists but has no data; SONA not implemented |
| Memory/AgentDB | 1/10 | Only basic JSON key-value; no vector search, no AgentDB |
| MCP Server | 0/10 | Not configured at all |
| Background Workers | 0/10 | Daemon never started |
| Security | 1/10 | Config exists, no scans run |
| CLI Accessibility | 2/10 | No local install, relies on npx remote |

**Overall: ~27% of RuFlo's documented capabilities are functional.**

The installation is essentially a **configuration-only setup** with custom hook handler scripts that provide basic routing, session management, and intelligence (PageRank). The heavy features (HNSW, SONA, AgentDB, MCP, daemon, security, hive-mind) are all either not installed or broken due to missing npm dependencies.

**The single highest-impact action is installing the npm dependencies** (`ruflo`, `better-sqlite3`, `sql.js`) and adding the MCP server. This alone would move from ~27% to ~50%+ functional.
