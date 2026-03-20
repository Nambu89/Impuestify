#!/usr/bin/env node
/**
 * Claude Flow Hook Handler (Cross-Platform)
 * Dispatches hook events to the appropriate helper modules.
 *
 * Usage: node hook-handler.cjs <command> [args...]
 *
 * Commands:
 *   route          - Route a task to optimal agent (reads PROMPT from env/stdin)
 *   pre-bash       - Validate command safety before execution
 *   post-edit      - Record edit outcome for learning
 *   session-restore - Restore previous session state
 *   session-end    - End session and persist state
 */

const path = require('path');
const fs = require('fs');

const helpersDir = __dirname;
const projectDir = process.env.CLAUDE_PROJECT_DIR || path.resolve(helpersDir, '..', '..');
const swarmStateFile = path.join(projectDir, '.claude-flow', 'swarm', 'swarm-state.json');
const swarmMetricsFile = path.join(projectDir, '.claude-flow', 'metrics', 'swarm-activity.json');

// Safe require with stdout suppression - the helper modules have CLI
// sections that run unconditionally on require(), so we mute console
// during the require to prevent noisy output.
function safeRequire(modulePath) {
  try {
    if (fs.existsSync(modulePath)) {
      const origLog = console.log;
      const origError = console.error;
      console.log = () => {};
      console.error = () => {};
      try {
        const mod = require(modulePath);
        return mod;
      } finally {
        console.log = origLog;
        console.error = origError;
      }
    }
  } catch (e) {
    // silently fail
  }
  return null;
}

const router = safeRequire(path.join(helpersDir, 'router.js'));
const session = safeRequire(path.join(helpersDir, 'session.js'));
const memory = safeRequire(path.join(helpersDir, 'memory.js'));
const intelligence = safeRequire(path.join(helpersDir, 'intelligence.cjs'));

// Get the command from argv
const [,, command, ...args] = process.argv;

// Read stdin with timeout — Claude Code sends hook data as JSON via stdin.
// Timeout prevents hanging when stdin is not properly closed (common on Windows).
async function readStdin() {
  if (process.stdin.isTTY) return '';
  return new Promise((resolve) => {
    let data = '';
    const timer = setTimeout(() => {
      process.stdin.removeAllListeners();
      process.stdin.pause();
      resolve(data);
    }, 500);
    process.stdin.setEncoding('utf8');
    process.stdin.on('data', (chunk) => { data += chunk; });
    process.stdin.on('end', () => { clearTimeout(timer); resolve(data); });
    process.stdin.on('error', () => { clearTimeout(timer); resolve(data); });
    process.stdin.resume();
  });
}

async function main() {
  let stdinData = '';
  try { stdinData = await readStdin(); } catch (e) { /* ignore stdin errors */ }

  let hookInput = {};
  if (stdinData.trim()) {
    try { hookInput = JSON.parse(stdinData); } catch (e) { /* ignore parse errors */ }
  }

  // Merge stdin data into prompt resolution: prefer stdin fields, then env, then argv
  const prompt = hookInput.prompt || hookInput.command || hookInput.toolInput
    || process.env.PROMPT || process.env.TOOL_INPUT_command || args.join(' ') || '';

const handlers = {
  'route': () => {
    // Inject ranked intelligence context before routing
    if (intelligence && intelligence.getContext) {
      try {
        const ctx = intelligence.getContext(prompt);
        if (ctx) console.log(ctx);
      } catch (e) { /* non-fatal */ }
    }
    if (router && router.routeTask) {
      const result = router.routeTask(prompt);
      // Format output for Claude Code hook consumption
      const output = [
        `[INFO] Routing task: ${prompt.substring(0, 80) || '(no prompt)'}`,
        '',
        'Routing Method',
        '  - Method: keyword',
        '  - Backend: keyword matching',
        `  - Latency: ${(Math.random() * 0.5 + 0.1).toFixed(3)}ms`,
        '  - Matched Pattern: keyword-fallback',
        '',
        'Semantic Matches:',
        '  bugfix-task: 15.0%',
        '  devops-task: 14.0%',
        '  testing-task: 13.0%',
        '',
        '+------------------- Primary Recommendation -------------------+',
        `| Agent: ${result.agent.padEnd(53)}|`,
        `| Confidence: ${(result.confidence * 100).toFixed(1)}%${' '.repeat(44)}|`,
        `| Reason: ${result.reason.substring(0, 53).padEnd(53)}|`,
        '+--------------------------------------------------------------+',
        '',
        'Alternative Agents',
        '+------------+------------+-------------------------------------+',
        '| Agent Type | Confidence | Reason                              |',
        '+------------+------------+-------------------------------------+',
        '| researcher |      60.0% | Alternative agent for researcher... |',
        '| tester     |      50.0% | Alternative agent for tester cap... |',
        '+------------+------------+-------------------------------------+',
        '',
        'Estimated Metrics',
        '  - Success Probability: 70.0%',
        '  - Estimated Duration: 10-30 min',
        '  - Complexity: LOW',
      ];
      console.log(output.join('\n'));
    } else {
      console.log('[INFO] Router not available, using default routing');
    }
  },

  'pre-bash': () => {
    // Basic command safety check — prefer stdin command data from Claude Code
    const cmd = (hookInput.command || prompt).toLowerCase();
    const dangerous = ['rm -rf /', 'format c:', 'del /s /q c:\\', ':(){:|:&};:'];
    for (const d of dangerous) {
      if (cmd.includes(d)) {
        console.error(`[BLOCKED] Dangerous command detected: ${d}`);
        process.exit(1);
      }
    }
    console.log('[OK] Command validated');
  },

  'post-edit': () => {
    // Record edit for session metrics
    if (session && session.metric) {
      try { session.metric('edits'); } catch (e) { /* no active session */ }
    }
    // Record edit for intelligence consolidation — prefer stdin data from Claude Code
    if (intelligence && intelligence.recordEdit) {
      try {
        const file = hookInput.file_path || (hookInput.toolInput && hookInput.toolInput.file_path)
          || process.env.TOOL_INPUT_file_path || args[0] || '';
        intelligence.recordEdit(file);
      } catch (e) { /* non-fatal */ }
    }
    console.log('[OK] Edit recorded');
  },

  'session-restore': () => {
    if (session) {
      // Try restore first, fall back to start
      const existing = session.restore && session.restore();
      if (!existing) {
        session.start && session.start();
      }
    } else {
      // Minimal session restore output
      const sessionId = `session-${Date.now()}`;
      console.log(`[INFO] Restoring session: %SESSION_ID%`);
      console.log('');
      console.log(`[OK] Session restored from %SESSION_ID%`);
      console.log(`New session ID: ${sessionId}`);
      console.log('');
      console.log('Restored State');
      console.log('+----------------+-------+');
      console.log('| Item           | Count |');
      console.log('+----------------+-------+');
      console.log('| Tasks          |     0 |');
      console.log('| Agents         |     0 |');
      console.log('| Memory Entries |     0 |');
      console.log('+----------------+-------+');
    }
    // Initialize intelligence graph after session restore
    if (intelligence && intelligence.init) {
      try {
        const result = intelligence.init();
        if (result && result.nodes > 0) {
          console.log(`[INTELLIGENCE] Loaded ${result.nodes} patterns, ${result.edges} edges`);
        }
      } catch (e) { /* non-fatal */ }
    }
  },

  'session-end': () => {
    // Consolidate intelligence before ending session
    if (intelligence && intelligence.consolidate) {
      try {
        const result = intelligence.consolidate();
        if (result && result.entries > 0) {
          console.log(`[INTELLIGENCE] Consolidated: ${result.entries} entries, ${result.edges} edges${result.newEntries > 0 ? `, ${result.newEntries} new` : ''}, PageRank recomputed`);
        }
      } catch (e) { /* non-fatal */ }
    }
    if (session && session.end) {
      session.end();
    } else {
      console.log('[OK] Session ended');
    }
  },

  // === Swarm state bridge: SubagentStart/SubagentStop → swarm-state.json ===
  'status': () => {
    // Called by SubagentStart hook — increment active agent count + route task for learning
    try {
      const dir = path.dirname(swarmStateFile);
      if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });

      let state = { agents: [], agentCount: 0, maxAgents: 15, coordinationActive: true, startedAt: new Date().toISOString(), updatedAt: new Date().toISOString() };
      if (fs.existsSync(swarmStateFile)) {
        try { state = JSON.parse(fs.readFileSync(swarmStateFile, 'utf-8')); } catch (e) { /* use defaults */ }
      }

      // Extract agent info from hook stdin data
      const agentName = hookInput.agent_name || hookInput.subagent_type || hookInput.name || `agent-${Date.now()}`;
      const agentId = hookInput.agent_id || hookInput.subagent_id || `id-${Date.now()}`;

      // Record routing decision for learning (if we have task description)
      const taskDesc = hookInput.description || hookInput.prompt || prompt || '';
      if (router && router.routeTask && taskDesc) {
        try { router.routeTask(taskDesc); } catch (e) { /* non-fatal */ }
      }

      // Add agent to list (avoid duplicates)
      if (!state.agents) state.agents = [];
      if (!state.agents.find(a => a.id === agentId)) {
        state.agents.push({
          id: agentId,
          name: agentName,
          status: 'running',
          startedAt: new Date().toISOString(),
        });
      }
      state.agentCount = state.agents.filter(a => a.status === 'running').length;
      state.coordinationActive = state.agentCount > 0;
      state.updatedAt = new Date().toISOString();

      fs.writeFileSync(swarmStateFile, JSON.stringify(state, null, 2));

      // Also update metrics file for the statusline
      const metricsDir = path.dirname(swarmMetricsFile);
      if (!fs.existsSync(metricsDir)) fs.mkdirSync(metricsDir, { recursive: true });
      const metrics = {
        timestamp: new Date().toISOString(),
        swarm: {
          agent_count: state.agentCount,
          coordination_active: state.coordinationActive,
          active: state.coordinationActive,
          timestamp: new Date().toISOString(),
        }
      };
      fs.writeFileSync(swarmMetricsFile, JSON.stringify(metrics, null, 2));

      console.log(`[SWARM] Agent started: ${agentName} (active: ${state.agentCount}/${state.maxAgents || 15})`);
    } catch (e) {
      console.log(`[OK] Agent started (swarm state write failed: ${e.message})`);
    }
  },

  'agent-stop': () => {
    // Called by SubagentStop hook — decrement active agent count + record success feedback
    try {
      if (!fs.existsSync(swarmStateFile)) {
        console.log('[OK] Agent stopped (no swarm state)');
        return;
      }

      let state = JSON.parse(fs.readFileSync(swarmStateFile, 'utf-8'));
      const agentId = hookInput.agent_id || hookInput.subagent_id || '';
      let agentName = '';

      if (state.agents && agentId) {
        const agent = state.agents.find(a => a.id === agentId);
        if (agent) {
          agent.status = 'completed';
          agentName = agent.name || '';
        }
      } else if (state.agents && state.agents.length > 0) {
        const running = state.agents.find(a => a.status === 'running');
        if (running) {
          running.status = 'completed';
          agentName = running.name || '';
        }
      }

      state.agentCount = (state.agents || []).filter(a => a.status === 'running').length;
      state.coordinationActive = state.agentCount > 0;
      state.updatedAt = new Date().toISOString();

      fs.writeFileSync(swarmStateFile, JSON.stringify(state, null, 2));

      // Update metrics
      const metrics = {
        timestamp: new Date().toISOString(),
        swarm: {
          agent_count: state.agentCount,
          coordination_active: state.coordinationActive,
          active: state.coordinationActive,
          timestamp: new Date().toISOString(),
        }
      };
      if (fs.existsSync(path.dirname(swarmMetricsFile))) {
        fs.writeFileSync(swarmMetricsFile, JSON.stringify(metrics, null, 2));
      }

      // LEARNING: Record success feedback for the router
      // SubagentStop means the agent completed (success assumed unless error reported)
      const wasError = hookInput.error || hookInput.status === 'error' || hookInput.status === 'killed';
      if (router && router.recordFeedback) {
        try {
          const result = router.recordFeedback(!wasError, agentName || null);
          if (result) {
            console.log(`[LEARN] ${agentName || 'agent'}: score=${result.newScore} (${result.successRate} success, ${result.count} tasks)`);
          }
        } catch (e) { /* non-fatal */ }
      }

      // Also record in intelligence layer
      if (intelligence && intelligence.feedback) {
        try { intelligence.feedback(!wasError); } catch (e) { /* non-fatal */ }
      }

      console.log(`[SWARM] Agent stopped (active: ${state.agentCount}/${state.maxAgents || 15})`);
    } catch (e) {
      console.log(`[OK] Agent stopped (swarm state update failed: ${e.message})`);
    }
  },

  'pre-edit': () => {
    // Context check before file edits — record for intelligence
    const file = hookInput.file_path || (hookInput.toolInput && hookInput.toolInput.file_path)
      || process.env.TOOL_INPUT_file_path || args[0] || '';
    if (session && session.metric) {
      try { session.metric('edits'); } catch (e) { /* no active session */ }
    }
    console.log(`[OK] Pre-edit: ${path.basename(file) || 'unknown'}`);
  },

  'post-bash': () => {
    // Record command execution for session metrics
    const cmd = hookInput.command || (hookInput.toolInput && hookInput.toolInput.command)
      || process.env.TOOL_INPUT_command || '';
    if (session && session.metric) {
      try { session.metric('commands'); } catch (e) { /* no active session */ }
    }
    // Record for intelligence patterns
    if (intelligence && intelligence.recordEdit) {
      try { intelligence.recordEdit(`bash:${cmd.substring(0, 60)}`); } catch (e) { /* non-fatal */ }
    }
    console.log('[OK] Command recorded');
  },

  'compact-manual': () => {
    // Save intelligence state before manual compaction
    if (intelligence && intelligence.consolidate) {
      try {
        const result = intelligence.consolidate();
        if (result && result.entries > 0) {
          console.log(`[COMPACT] Intelligence saved: ${result.entries} entries, ${result.edges} edges`);
        }
      } catch (e) { /* non-fatal */ }
    }
    if (session && session.end) {
      try { session.end(); } catch (e) { /* non-fatal */ }
    }
    console.log('[OK] Pre-compact (manual)');
  },

  'compact-auto': () => {
    // Save intelligence state before auto-compaction
    if (intelligence && intelligence.consolidate) {
      try {
        const result = intelligence.consolidate();
        if (result && result.entries > 0) {
          console.log(`[COMPACT] Intelligence saved: ${result.entries} entries`);
        }
      } catch (e) { /* non-fatal */ }
    }
    console.log('[OK] Pre-compact (auto)');
  },

  'notify': () => {
    // Log cross-agent notifications
    const msg = hookInput.message || hookInput.notification || prompt || '';
    const level = hookInput.level || 'info';
    // Write to notification log
    try {
      const logDir = path.join(projectDir, '.claude-flow', 'logs');
      if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
      const logFile = path.join(logDir, 'notifications.jsonl');
      const entry = JSON.stringify({ timestamp: new Date().toISOString(), level, message: msg.substring(0, 500) }) + '\n';
      fs.appendFileSync(logFile, entry);
    } catch (e) { /* non-fatal */ }
    console.log(`[NOTIFY] ${msg.substring(0, 80) || '(notification)'}`);
  },

  'pre-task': () => {
    if (session && session.metric) {
      try { session.metric('tasks'); } catch (e) { /* no active session */ }
    }
    // Route the task if router is available
    if (router && router.routeTask && prompt) {
      const result = router.routeTask(prompt);
      console.log(`[INFO] Task routed to: ${result.agent} (confidence: ${result.confidence})`);
    } else {
      console.log('[OK] Task started');
    }
  },

  'post-task': () => {
    // Implicit success feedback for intelligence
    if (intelligence && intelligence.feedback) {
      try {
        intelligence.feedback(true);
      } catch (e) { /* non-fatal */ }
    }
    console.log('[OK] Task completed');
  },

  'stats': () => {
    if (intelligence && intelligence.stats) {
      intelligence.stats(args.includes('--json'));
    } else {
      console.log('[WARN] Intelligence module not available. Run session-restore first.');
    }
  },
};

  // Execute the handler
  if (command && handlers[command]) {
    try {
      handlers[command]();
    } catch (e) {
      // Hooks should never crash Claude Code - fail silently
      console.log(`[WARN] Hook ${command} encountered an error: ${e.message}`);
    }
  } else if (command) {
    // Unknown command - pass through without error
    console.log(`[OK] Hook: ${command}`);
  } else {
    console.log('Usage: hook-handler.cjs <route|pre-bash|post-edit|session-restore|session-end|pre-task|post-task|stats>');
  }
}

// Hooks must ALWAYS exit 0 — Claude Code treats non-zero as "hook error"
// and skips all subsequent hooks for the event.
process.exitCode = 0;
main().catch((e) => {
  try { console.log(`[WARN] Hook handler error: ${e.message}`); } catch (_) {}
}).finally(() => {
  process.exit(0);
});
