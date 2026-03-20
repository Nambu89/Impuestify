#!/usr/bin/env node
/**
 * Claude Flow Agent Router with Adaptive Learning
 *
 * Routes tasks to optimal agents based on patterns + learned success rates.
 * After each task completes, the router updates agent scores for similar tasks.
 * Over time, routing becomes more accurate as it learns which agents work best
 * for which types of tasks.
 *
 * Learning model:
 * - Each (pattern, agent) pair has a success score (0.0 to 1.0)
 * - On success: score += LEARNING_RATE * (1 - score)
 * - On failure: score -= LEARNING_RATE * score
 * - Routing prefers agents with higher scores for matching patterns
 * - Scores persist across sessions in .claude-flow/data/routing-history.json
 */

const path = require('path');
const fs = require('fs');

const projectDir = process.env.CLAUDE_PROJECT_DIR || path.resolve(__dirname, '..', '..');
const HISTORY_FILE = path.join(projectDir, '.claude-flow', 'data', 'routing-history.json');
const LEARNING_RATE = 0.15;
const MIN_CONFIDENCE = 0.3;
const MAX_CONFIDENCE = 0.95;

// ─── Agent definitions ──────────────────────────────────────────────
const AGENT_CAPABILITIES = {
  'pm-coordinator': ['project-management', 'roadmap-planning', 'architecture-decisions', 'task-decomposition', 'delegation', 'research'],
  'backend-architect': ['fastapi', 'python', 'database-turso', 'security', 'api-design', 'testing-backend'],
  'frontend-dev': ['react', 'typescript', 'css', 'vite', 'pwa', 'ux-design'],
  'python-pro': ['python-optimization', 'debugging', 'async-patterns', 'profiling'],
  'qa-tester': ['playwright-e2e', 'regression-testing', 'bug-reporting', 'screenshot-verification'],
  'doc-crawler': ['web-crawling', 'pdf-extraction', 'document-classification'],
  'competitive-intel': ['market-analysis', 'pricing-research', 'competitor-tracking'],
  'doc-auditor': ['documentation-audit', 'changelog-update', 'readme-maintenance', 'memory-management'],
  'plan-checker': ['plan-verification', 'scope-analysis', 'dependency-check', 'risk-assessment'],
  'verifier': ['post-implementation-check', 'goal-backward-verification', 'test-execution', 'build-verification'],
  coder: ['code-generation', 'refactoring', 'implementation'],
  tester: ['unit-testing', 'integration-testing', 'coverage'],
  reviewer: ['code-review', 'security-audit', 'quality-check'],
  researcher: ['web-search', 'analysis', 'summarization'],
  architect: ['system-design', 'architecture', 'patterns'],
};

// ─── Base patterns (regex → default agent) ──────────────────────────
const TASK_PATTERNS = {
  'test|playwright|e2e|qa|bug|regression|screenshot': 'qa-tester',
  'backend|fastapi|endpoint|router|database|turso|security|irpf|simulador|pagador': 'backend-architect',
  'frontend|react|component|css|hook|ui|ux|tsx|vite': 'frontend-dev',
  'python|optimize|debug|profile|performance|async': 'python-pro',
  'crawl|document|pdf|aeat|boe|url|crawler': 'doc-crawler',
  'competitor|market|pricing|taxdown|declarando': 'competitive-intel',
  'docs|readme|changelog|memory|audit|documentacion': 'doc-auditor',
  'plan|roadmap|decision|strategy|architecture|delegate': 'pm-coordinator',
  'verify|check-plan|post-implementation': 'verifier',
  'implement|create|build|add|write code': 'coder',
  'review|validate|code review': 'reviewer',
  'research|find|search|explore': 'researcher',
  'design|architect|structure': 'architect',
};

// ─── History I/O ────────────────────────────────────────────────────

function loadHistory() {
  try {
    if (fs.existsSync(HISTORY_FILE)) {
      return JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf-8'));
    }
  } catch (e) { /* corrupted — start fresh */ }
  return {
    // Per-agent success rates by matched pattern
    agentScores: {},    // { "backend-architect": { "backend|fastapi|...": { score: 0.8, count: 5 } } }
    // Recent routing decisions (for feedback matching)
    pendingFeedback: [], // [{ task, agent, pattern, timestamp }]
    // Aggregate stats
    stats: {
      totalRouted: 0,
      totalFeedback: 0,
      agentUsage: {},   // { "backend-architect": 12, "frontend-dev": 8, ... }
    },
    version: "1.0",
  };
}

function saveHistory(history) {
  try {
    const dir = path.dirname(HISTORY_FILE);
    if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
    fs.writeFileSync(HISTORY_FILE, JSON.stringify(history, null, 2));
  } catch (e) { /* non-fatal */ }
}

// ─── Core routing with learned scores ───────────────────────────────

function routeTask(task) {
  const taskLower = task.toLowerCase();
  const history = loadHistory();

  // Find all matching patterns
  const matches = [];
  for (const [pattern, defaultAgent] of Object.entries(TASK_PATTERNS)) {
    const regex = new RegExp(pattern, 'i');
    if (regex.test(taskLower)) {
      // Get learned score for this agent+pattern combination
      const agentScore = (history.agentScores[defaultAgent] || {})[pattern];
      const learnedConfidence = agentScore ? agentScore.score : 0.8;
      const taskCount = agentScore ? agentScore.count : 0;

      matches.push({
        agent: defaultAgent,
        pattern,
        confidence: Math.max(MIN_CONFIDENCE, Math.min(MAX_CONFIDENCE, learnedConfidence)),
        taskCount,
      });
    }
  }

  if (matches.length === 0) {
    return {
      agent: 'coder',
      confidence: 0.5,
      reason: 'Default routing - no specific pattern matched',
      learned: false,
    };
  }

  // Sort by confidence (learned score), take the best
  matches.sort((a, b) => b.confidence - a.confidence);
  const best = matches[0];

  // Record this routing decision for later feedback
  history.pendingFeedback.push({
    task: task.substring(0, 200),
    agent: best.agent,
    pattern: best.pattern,
    timestamp: Date.now(),
  });
  // Keep only last 50 pending
  if (history.pendingFeedback.length > 50) {
    history.pendingFeedback = history.pendingFeedback.slice(-50);
  }

  // Update usage stats
  history.stats.totalRouted = (history.stats.totalRouted || 0) + 1;
  history.stats.agentUsage = history.stats.agentUsage || {};
  history.stats.agentUsage[best.agent] = (history.stats.agentUsage[best.agent] || 0) + 1;

  saveHistory(history);

  return {
    agent: best.agent,
    confidence: best.confidence,
    reason: best.taskCount > 0
      ? `Learned routing (${best.taskCount} previous tasks, score: ${best.confidence.toFixed(2)})`
      : `Pattern match: ${best.pattern.substring(0, 40)}`,
    learned: best.taskCount > 0,
    alternatives: matches.slice(1, 3).map(m => ({
      agent: m.agent,
      confidence: m.confidence,
    })),
  };
}

// ─── Feedback: update scores after task completion ──────────────────

function recordFeedback(success, agentName) {
  const history = loadHistory();

  // Find the most recent pending feedback for this agent (or any if not specified)
  let feedbackIdx = -1;
  if (agentName) {
    feedbackIdx = history.pendingFeedback.findLastIndex(f => f.agent === agentName);
  }
  if (feedbackIdx === -1 && history.pendingFeedback.length > 0) {
    feedbackIdx = history.pendingFeedback.length - 1;
  }

  if (feedbackIdx === -1) return null;

  const feedback = history.pendingFeedback.splice(feedbackIdx, 1)[0];
  const agent = feedback.agent;
  const pattern = feedback.pattern;

  // Initialize agent scores if needed
  if (!history.agentScores[agent]) history.agentScores[agent] = {};
  if (!history.agentScores[agent][pattern]) {
    history.agentScores[agent][pattern] = { score: 0.8, count: 0, successes: 0, failures: 0 };
  }

  const entry = history.agentScores[agent][pattern];
  entry.count += 1;

  if (success) {
    entry.successes += 1;
    // Increase score: move toward 1.0
    entry.score = Math.min(MAX_CONFIDENCE, entry.score + LEARNING_RATE * (1 - entry.score));
  } else {
    entry.failures += 1;
    // Decrease score: move toward MIN_CONFIDENCE
    entry.score = Math.max(MIN_CONFIDENCE, entry.score - LEARNING_RATE * entry.score);
  }

  entry.lastFeedback = Date.now();
  history.stats.totalFeedback = (history.stats.totalFeedback || 0) + 1;

  saveHistory(history);

  return {
    agent,
    pattern: pattern.substring(0, 40),
    newScore: entry.score.toFixed(3),
    count: entry.count,
    successRate: entry.count > 0 ? ((entry.successes / entry.count) * 100).toFixed(0) + '%' : 'N/A',
  };
}

// ─── Stats: show routing performance ────────────────────────────────

function getStats() {
  const history = loadHistory();
  const result = {
    totalRouted: history.stats.totalRouted || 0,
    totalFeedback: history.stats.totalFeedback || 0,
    pendingFeedback: history.pendingFeedback.length,
    agentUsage: history.stats.agentUsage || {},
    agentScores: {},
  };

  // Summarize scores per agent
  for (const [agent, patterns] of Object.entries(history.agentScores || {})) {
    const entries = Object.values(patterns);
    if (entries.length === 0) continue;
    const avgScore = entries.reduce((sum, e) => sum + e.score, 0) / entries.length;
    const totalTasks = entries.reduce((sum, e) => sum + e.count, 0);
    const totalSuccesses = entries.reduce((sum, e) => sum + e.successes, 0);
    result.agentScores[agent] = {
      avgScore: avgScore.toFixed(3),
      totalTasks,
      successRate: totalTasks > 0 ? ((totalSuccesses / totalTasks) * 100).toFixed(0) + '%' : 'N/A',
      patterns: entries.length,
    };
  }

  return result;
}

// ─── CLI interface ──────────────────────────────────────────────────

const args = process.argv.slice(2);
const command = args[0];

if (command === '--feedback') {
  // Usage: router.js --feedback success [agent-name]
  //        router.js --feedback failure [agent-name]
  const success = args[1] !== 'failure';
  const agent = args[2] || null;
  const result = recordFeedback(success, agent);
  if (result) {
    console.log(JSON.stringify(result, null, 2));
  } else {
    console.log('No pending feedback to process');
  }
} else if (command === '--stats') {
  console.log(JSON.stringify(getStats(), null, 2));
} else if (command === '--reset') {
  saveHistory({ agentScores: {}, pendingFeedback: [], stats: { totalRouted: 0, totalFeedback: 0, agentUsage: {} }, version: "1.0" });
  console.log('Routing history reset');
} else if (command) {
  const task = args.join(' ');
  const result = routeTask(task);
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log('Usage: router.js <task description>');
  console.log('       router.js --feedback success|failure [agent-name]');
  console.log('       router.js --stats');
  console.log('       router.js --reset');
  console.log('\nAvailable agents:', Object.keys(AGENT_CAPABILITIES).join(', '));
}

module.exports = { routeTask, recordFeedback, getStats, AGENT_CAPABILITIES, TASK_PATTERNS };
