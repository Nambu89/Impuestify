# Task Types for Impuestify Development

Specialized agent configurations for different task types.
Use with Claude Code's Agent tool by specifying the subagent_type.

## Available Types

### `coder` — Implementation tasks
For writing code, creating files, implementing features.
Focus: write clean code, run tests, commit.

### `researcher` — Investigation tasks
For researching APIs, docs, pricing, best practices.
Focus: gather info, summarize findings, no code changes.

### `tester` — Testing tasks
For writing tests, running test suites, debugging failures.
Focus: TDD, test coverage, regression detection.

### `reviewer` — Code review tasks
For reviewing changes, checking quality, finding issues.
Focus: read code, identify problems, suggest fixes.

### `Explore` — Codebase exploration
For finding files, understanding architecture, mapping dependencies.
Focus: search, read, summarize structure.

## Usage Examples

```
# Implementation task
Agent(subagent_type="coder", prompt="Implement X feature...")

# Research task
Agent(subagent_type="researcher", prompt="Research Gemini API pricing...")

# Testing task
Agent(subagent_type="tester", prompt="Write tests for warmup_service.py...")

# Parallel execution (Wave pattern)
Agent(subagent_type="coder", name="backend-worker", prompt="...", run_in_background=True)
Agent(subagent_type="coder", name="frontend-worker", prompt="...", run_in_background=True)
```
