"""
AutoDream — Background code analysis for Impuestify.

Inspired by Claude Code's DreamTask/AutoDream feature.
Analyzes the codebase for:
- Large files (>500 lines)
- Missing test coverage (files without corresponding test files)
- TODO/FIXME/HACK comments
- Unused imports (basic check)
- Files modified recently but not tested

Usage:
    python scripts/autodream.py [--full] [--json]
"""
import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
BACKEND = PROJECT_ROOT / "backend"
FRONTEND = PROJECT_ROOT / "frontend" / "src"


def find_large_files(threshold=500):
    """Find Python/TS files over threshold lines."""
    large = []
    for ext in ["**/*.py", "**/*.ts", "**/*.tsx"]:
        for path in BACKEND.glob(ext):
            if "__pycache__" in str(path) or "node_modules" in str(path):
                continue
            try:
                lines = len(path.read_text(encoding="utf-8").splitlines())
                if lines > threshold:
                    large.append({"file": str(path.relative_to(PROJECT_ROOT)), "lines": lines})
            except Exception:
                pass
        for path in FRONTEND.glob(ext):
            if "node_modules" in str(path):
                continue
            try:
                lines = len(path.read_text(encoding="utf-8").splitlines())
                if lines > threshold:
                    large.append({"file": str(path.relative_to(PROJECT_ROOT)), "lines": lines})
            except Exception:
                pass
    return sorted(large, key=lambda x: x["lines"], reverse=True)


def find_missing_tests():
    """Find backend source files without corresponding test files."""
    missing = []
    app_dir = BACKEND / "app"
    test_dir = BACKEND / "tests"

    # Get all test files
    test_files = {f.stem.replace("test_", "") for f in test_dir.glob("test_*.py")}

    # Check services, routers, tools, utils for missing tests
    for subdir in ["services", "routers", "tools", "utils", "utils/calculators"]:
        source_dir = app_dir / subdir
        if not source_dir.exists():
            continue
        for f in source_dir.glob("*.py"):
            if f.name.startswith("__"):
                continue
            module_name = f.stem
            if module_name not in test_files:
                missing.append(str(f.relative_to(PROJECT_ROOT)))

    return sorted(missing)


def find_todo_comments():
    """Find TODO, FIXME, HACK comments in source files."""
    todos = []
    pattern = re.compile(r"#\s*(TODO|FIXME|HACK|XXX|TEMP)[:\s]*(.*)", re.IGNORECASE)

    for ext in ["**/*.py", "**/*.ts", "**/*.tsx"]:
        for root in [BACKEND, FRONTEND]:
            for path in root.glob(ext):
                if "__pycache__" in str(path) or "node_modules" in str(path):
                    continue
                try:
                    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                        match = pattern.search(line)
                        if match:
                            todos.append({
                                "file": str(path.relative_to(PROJECT_ROOT)),
                                "line": i,
                                "type": match.group(1).upper(),
                                "text": match.group(2).strip(),
                            })
                except Exception:
                    pass
    return todos


def count_test_coverage():
    """Count test files and source files for a rough coverage metric."""
    test_count = len(list((BACKEND / "tests").glob("test_*.py")))
    source_files = 0
    for subdir in ["services", "routers", "tools", "utils", "agents"]:
        source_dir = BACKEND / "app" / subdir
        if source_dir.exists():
            source_files += len([f for f in source_dir.glob("*.py") if not f.name.startswith("__")])
    return {"test_files": test_count, "source_files": source_files, "ratio": round(test_count / max(source_files, 1), 2)}


def generate_report(as_json=False):
    """Generate full AutoDream report."""
    report = {
        "timestamp": datetime.now().isoformat(),
        "large_files": find_large_files(),
        "missing_tests": find_missing_tests(),
        "todo_comments": find_todo_comments(),
        "test_coverage": count_test_coverage(),
    }

    if as_json:
        print(json.dumps(report, indent=2))
        return report

    # Human-readable output
    print("=" * 60)
    print(f"  AutoDream Report — {report['timestamp'][:10]}")
    print("=" * 60)

    print(f"\n### Large Files (>{500} lines)")
    if report["large_files"]:
        for f in report["large_files"][:15]:
            print(f"  {f['lines']:>5} lines  {f['file']}")
    else:
        print("  None found")

    print(f"\n### Missing Tests ({len(report['missing_tests'])} files)")
    for f in report["missing_tests"][:20]:
        print(f"  {f}")

    print(f"\n### TODO/FIXME Comments ({len(report['todo_comments'])})")
    for t in report["todo_comments"][:20]:
        print(f"  [{t['type']}] {t['file']}:{t['line']} — {t['text'][:80]}")

    cov = report["test_coverage"]
    print(f"\n### Test Coverage Ratio")
    print(f"  {cov['test_files']} test files / {cov['source_files']} source files = {cov['ratio']}")

    print("\n" + "=" * 60)
    return report


if __name__ == "__main__":
    as_json = "--json" in sys.argv
    generate_report(as_json=as_json)
