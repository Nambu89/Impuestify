#!/usr/bin/env node
/**
 * Post-install patches for RuFlo/AgentDB/ReasoningBank on Windows.
 *
 * Fixes two known issues:
 * 1. agentic-flow bundles onnxruntime-node v1.24.3 (NAPI v6) which fails
 *    with long Windows paths (\\?\ prefix). Renaming it forces fallback to
 *    the top-level onnxruntime-node v1.14.0 (NAPI v3) which works.
 * 2. AgentDB v1.3.9 has an ESM export bug — controllers/index.js is at
 *    dist/src/controllers/ but imports expect dist/controllers/.
 *
 * Run automatically via "postinstall" in package.json or manually:
 *   node scripts/postinstall-patches.js
 */

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
let patched = 0;

// --- Patch 1: Rename nested onnxruntime-node (NAPI v6) ---
const nestedOnnx = path.join(root, 'node_modules', 'agentic-flow', 'node_modules', 'onnxruntime-node');
const backupOnnx = nestedOnnx + '.bak-napi6';

if (fs.existsSync(nestedOnnx) && !fs.existsSync(backupOnnx)) {
  try {
    fs.renameSync(nestedOnnx, backupOnnx);
    console.log('[PATCH 1] Renamed agentic-flow/node_modules/onnxruntime-node -> .bak-napi6');
    console.log('          Falls back to top-level onnxruntime-node v1.14.0 (NAPI v3)');
    patched++;
  } catch (e) {
    console.warn('[PATCH 1] FAILED:', e.message);
  }
} else if (fs.existsSync(backupOnnx)) {
  console.log('[PATCH 1] Already applied (backup exists)');
} else {
  console.log('[PATCH 1] Skipped (nested onnxruntime-node not found)');
}

// --- Patch 2: AgentDB controllers path alias ---
const controllersTarget = path.join(root, 'node_modules', 'agentdb', 'dist', 'controllers');
const controllersSource = path.join(root, 'node_modules', 'agentdb', 'dist', 'src', 'controllers', 'index.js');

if (fs.existsSync(controllersSource) && !fs.existsSync(path.join(controllersTarget, 'index.js'))) {
  try {
    if (!fs.existsSync(controllersTarget)) {
      fs.mkdirSync(controllersTarget, { recursive: true });
    }
    fs.copyFileSync(controllersSource, path.join(controllersTarget, 'index.js'));
    // Also copy .d.ts if exists
    const dts = controllersSource.replace('.js', '.d.ts');
    if (fs.existsSync(dts)) {
      fs.copyFileSync(dts, path.join(controllersTarget, 'index.d.ts'));
    }
    console.log('[PATCH 2] Created agentdb/dist/controllers/index.js (ESM export fix)');
    patched++;
  } catch (e) {
    console.warn('[PATCH 2] FAILED:', e.message);
  }
} else if (fs.existsSync(path.join(controllersTarget, 'index.js'))) {
  console.log('[PATCH 2] Already applied');
} else {
  console.log('[PATCH 2] Skipped (agentdb not found)');
}

console.log(`\n[postinstall-patches] Done. ${patched} patch(es) applied.`);
