"""
Fiscal Drift Analyzer — intelligent change detection layer.

Runs after the document crawler when _pending_ingest.json exists.
Classifies changed documents and optionally invokes Claude headless
to determine if tax rates, deductions, or deadlines need updating.

Architecture:
  Layer 1 (free)  — Python pattern matching on filenames → priority classification
  Layer 2 (cheap) — Claude haiku via CLI only for high-priority changes → drift report

Usage:
  python -m backend.scripts.doc_crawler.drift_analyzer [--dry-run] [--skip-llm]
"""
import json
import logging
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root in path
project_root = Path(__file__).resolve().parents[3]
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from backend.scripts.doc_crawler.config import DOCS_DIR, PENDING_INGEST

logger = logging.getLogger(__name__)

PLANS_DIR = project_root / "plans"
NOTIFY_EMAIL = True  # Send email alerts via Resend for high-priority changes
MAX_BUDGET_USD = 0.50  # Hard cap per analysis session
CLAUDE_MODEL = "haiku"
CLAUDE_MAX_TURNS = 2

# ── Layer 1: Pattern-based classification (free) ─────────────────

# Filename patterns that indicate high-priority fiscal changes
HIGH_PRIORITY_PATTERNS = [
    # IRPF laws and manuals
    ("irpf", "IRPF law or manual changed"),
    ("renta", "Renta manual changed"),
    ("manual_practico", "AEAT practical manual changed"),
    ("retenciones", "Withholding rates changed"),
    ("algoritmo", "Withholding algorithm changed"),
    # IVA / IGIC / IPSI
    ("iva", "IVA law changed"),
    ("igic", "IGIC law changed"),
    ("ipsi", "IPSI law changed"),
    # Tributos cedidos (deductions live here)
    ("tributoscedidos", "Regional tax law changed — deductions may be affected"),
    ("tributos_cedidos", "Regional tax law changed — deductions may be affected"),
    # Sociedades
    ("sociedades", "Corporate tax changed"),
    # ISD
    ("isd", "Inheritance/Gift tax changed"),
    # Patrimonio
    ("patrimonio", "Wealth tax changed"),
    # Social Security
    ("reta", "Self-employed SS quotas changed"),
    ("cotizacion", "SS contribution tables changed"),
    # Foral
    ("foral", "Foral law changed"),
    # Modelo forms
    ("modelo303", "VAT form changed"),
    ("modelo130", "Quarterly payment form changed"),
    ("dr303", "VAT form design changed"),
    ("dr130", "Quarterly payment design changed"),
    ("dr131", "Modules form design changed"),
]

MEDIUM_PRIORITY_PATTERNS = [
    ("estatuto", "Autonomy statute changed"),
    ("ref_canarias", "Canarias REF changed"),
    ("reglamento", "Tax regulation changed"),
    ("lgt", "General Tax Law changed"),
]


def classify_file(file_path: str) -> tuple[str, str]:
    """
    Classify a changed file by priority based on filename patterns.
    Returns (priority, reason).
    """
    path_lower = file_path.lower().replace(" ", "").replace("-", "").replace("_", "")

    for pattern, reason in HIGH_PRIORITY_PATTERNS:
        if pattern.lower() in path_lower:
            return "high", reason

    for pattern, reason in MEDIUM_PRIORITY_PATTERNS:
        if pattern.lower() in path_lower:
            return "medium", reason

    return "low", "General document change"


def extract_territory(file_path: str) -> str:
    """Extract territory from file path (first directory component)."""
    parts = Path(file_path).parts
    if parts:
        return parts[0]
    return "Unknown"


# ── Layer 2: Claude headless analysis (cheap) ────────────────────

def build_analysis_prompt(changes: list[dict]) -> str:
    """Build the prompt for Claude headless analysis."""
    files_summary = "\n".join(
        f"- [{c['priority'].upper()}] {c['path']} ({c['territory']}) — {c['reason']}"
        for c in changes
    )

    return f"""Eres un analista fiscal español. Se han detectado cambios en documentos fiscales oficiales.

DOCUMENTOS CAMBIADOS:
{files_summary}

ANALIZA cada cambio y responde SOLO con un JSON así:
{{
  "critical_changes": [
    {{
      "file": "path",
      "territory": "CCAA",
      "impact": "descripción breve del impacto",
      "action_needed": "what to update in TaxIA database",
      "urgency": "immediate|next_sprint|informational"
    }}
  ],
  "summary": "resumen ejecutivo en 2-3 líneas",
  "db_tables_affected": ["irpf_scales", "deductions", "fiscal_deadlines"],
  "recommendation": "acción recomendada para el equipo"
}}

Sé conciso. Solo reporta cambios que afecten a: tramos IRPF, deducciones, plazos fiscales, tipos IVA/IGIC/IPSI, cuotas RETA, o bonificaciones ISD.
Si un documento cambiado es solo un reglamento procedimental sin impacto en cálculos, márcalo como urgency: "informational"."""


def run_claude_analysis(prompt: str, dry_run: bool = False) -> dict | None:
    """
    Run Claude headless via CLI for document analysis.
    Returns parsed JSON response or None on failure.
    """
    if dry_run:
        logger.info("[DRY-RUN] Would invoke Claude headless with haiku model")
        return None

    try:
        cmd = [
            "claude",
            "-p", prompt,
            "--model", CLAUDE_MODEL,
            "--max-turns", str(CLAUDE_MAX_TURNS),
            "--output-format", "json",
        ]

        logger.info(f"Invoking Claude headless (model={CLAUDE_MODEL}, budget=${MAX_BUDGET_USD})")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            cwd=str(project_root),
        )

        if result.returncode != 0:
            logger.warning(f"Claude CLI returned {result.returncode}: {result.stderr[:200]}")
            return None

        # Parse the JSON output
        output = result.stdout.strip()
        if not output:
            logger.warning("Claude CLI returned empty output")
            return None

        # Claude --output-format json wraps in {"result": "..."}
        try:
            wrapper = json.loads(output)
            content = wrapper.get("result", output)
        except json.JSONDecodeError:
            content = output

        # Try to extract JSON from the content
        if isinstance(content, str):
            # Find JSON block in response
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                content = content[start:end]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Could not parse Claude response as JSON")
                # Return raw content as fallback
                return {"summary": content, "critical_changes": [], "raw": True}
        elif isinstance(content, dict):
            return content

        return None

    except subprocess.TimeoutExpired:
        logger.error("Claude CLI timed out after 120s")
        return None
    except FileNotFoundError:
        logger.error("Claude CLI not found — install with: npm install -g @anthropic-ai/claude-code")
        return None
    except Exception as e:
        logger.error(f"Claude analysis failed: {e}")
        return None


# ── Report generation ────────────────────────────────────────────

def generate_drift_report(
    changes: list[dict],
    analysis: dict | None,
    report_path: Path,
) -> None:
    """Generate a markdown drift report."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        f"# Fiscal Drift Report — {now}",
        "",
        f"## Changed Documents ({len(changes)})",
        "",
    ]

    # Group by priority
    for priority in ("high", "medium", "low"):
        group = [c for c in changes if c["priority"] == priority]
        if group:
            emoji = {"high": "!!!", "medium": "!!", "low": "!"}[priority]
            lines.append(f"### {priority.upper()} Priority ({emoji})")
            for c in group:
                lines.append(f"- **{c['territory']}**: `{c['path']}` — {c['reason']}")
            lines.append("")

    # Claude analysis section
    if analysis and not analysis.get("raw"):
        lines.append("## AI Analysis")
        lines.append("")

        summary = analysis.get("summary", "No summary available")
        lines.append(f"> {summary}")
        lines.append("")

        critical = analysis.get("critical_changes", [])
        if critical:
            lines.append("### Critical Changes")
            lines.append("")
            lines.append("| File | Territory | Impact | Action | Urgency |")
            lines.append("|------|-----------|--------|--------|---------|")
            for c in critical:
                lines.append(
                    f"| `{c.get('file', '')}` | {c.get('territory', '')} "
                    f"| {c.get('impact', '')} | {c.get('action_needed', '')} "
                    f"| **{c.get('urgency', '')}** |"
                )
            lines.append("")

        tables = analysis.get("db_tables_affected", [])
        if tables:
            lines.append(f"### DB Tables Affected: {', '.join(f'`{t}`' for t in tables)}")
            lines.append("")

        rec = analysis.get("recommendation", "")
        if rec:
            lines.append(f"### Recommendation")
            lines.append(f"{rec}")
            lines.append("")

    elif analysis and analysis.get("raw"):
        lines.append("## AI Analysis (raw)")
        lines.append("")
        lines.append(analysis.get("summary", ""))
        lines.append("")

    # Footer
    lines.append("---")
    lines.append(f"*Generated by TaxIA Drift Analyzer — {now}*")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    logger.info(f"Drift report written to: {report_path}")


# ── Email notification via Resend ─────────────────────────────────

def send_drift_email(changes: list[dict], analysis: dict | None, report_path: Path) -> bool:
    """
    Send drift alert email via Resend to OWNER_EMAIL.
    Only sends if high-priority changes are detected.
    Returns True if sent successfully.
    """
    try:
        import resend
        from backend.app.config import settings

        if not settings.is_resend_configured:
            logger.warning("Resend not configured — skipping email notification")
            return False

        resend.api_key = settings.RESEND_API_KEY
        from_email = settings.RESEND_FROM_EMAIL
        to_email = settings.OWNER_EMAIL

        high = [c for c in changes if c["priority"] == "high"]
        medium = [c for c in changes if c["priority"] == "medium"]

        # Build HTML body
        changes_html = ""
        for c in high:
            changes_html += (
                f'<tr style="background:#fef2f2;">'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#dc2626;font-weight:600;">ALTA</td>'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{c["territory"]}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-family:monospace;font-size:12px;">{c["path"]}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{c["reason"]}</td>'
                f'</tr>'
            )
        for c in medium:
            changes_html += (
                f'<tr>'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;color:#d97706;font-weight:600;">MEDIA</td>'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{c["territory"]}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;font-family:monospace;font-size:12px;">{c["path"]}</td>'
                f'<td style="padding:8px;border-bottom:1px solid #e5e7eb;">{c["reason"]}</td>'
                f'</tr>'
            )

        ai_summary = ""
        if analysis and not analysis.get("raw"):
            summary_text = analysis.get("summary", "")
            recommendation = analysis.get("recommendation", "")
            if summary_text or recommendation:
                ai_summary = f"""
                <div style="background:#f0f9ff;border:1px solid #bae6fd;border-radius:6px;padding:15px;margin:15px 0;">
                    <h3 style="margin:0 0 8px 0;color:#0369a1;font-size:14px;">Analisis IA</h3>
                    <p style="margin:0 0 8px 0;font-size:13px;">{summary_text}</p>
                    {"<p style='margin:0;font-size:13px;font-weight:600;'>" + recommendation + "</p>" if recommendation else ""}
                </div>
                """

        subject = f"Impuestify Drift Alert — {len(high)} alta, {len(medium)} media prioridad"

        html = f"""
        <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;max-width:650px;margin:0 auto;">
            <div style="background:linear-gradient(135deg,#dc2626,#ea580c);color:white;padding:20px;border-radius:8px 8px 0 0;">
                <h1 style="margin:0;font-size:18px;">Cambio fiscal detectado</h1>
                <p style="margin:5px 0 0 0;opacity:0.9;font-size:13px;">
                    {len(high)} cambio(s) alta prioridad | {len(medium)} media prioridad | {len(changes)} total
                </p>
            </div>
            <div style="background:#f8f9fa;padding:20px;border-radius:0 0 8px 8px;">
                <table style="width:100%;border-collapse:collapse;font-size:13px;">
                    <thead>
                        <tr style="background:#e5e7eb;">
                            <th style="padding:8px;text-align:left;">Prioridad</th>
                            <th style="padding:8px;text-align:left;">Territorio</th>
                            <th style="padding:8px;text-align:left;">Documento</th>
                            <th style="padding:8px;text-align:left;">Motivo</th>
                        </tr>
                    </thead>
                    <tbody>
                        {changes_html}
                    </tbody>
                </table>
                {ai_summary}
                <p style="color:#666;font-size:12px;margin-top:15px;">
                    Drift report: <code>{report_path.name}</code><br>
                    Generado por TaxIA Drift Analyzer
                </p>
            </div>
        </div>
        """

        result = resend.Emails.send({
            "from_": from_email,
            "to": [to_email],
            "subject": subject,
            "html": html,
        })

        logger.info(f"Drift alert email sent to {to_email} (id: {getattr(result, 'id', result)})")
        return True

    except ImportError:
        logger.warning("resend package not installed — skipping email")
        return False
    except Exception as e:
        logger.error(f"Failed to send drift email: {e}")
        return False


# ── Main entry point ─────────────────────────────────────────────

def analyze_drift(dry_run: bool = False, skip_llm: bool = False) -> dict:
    """
    Main drift analysis pipeline.

    1. Read _pending_ingest.json
    2. Classify each changed file (Layer 1 — free)
    3. If high-priority changes exist, invoke Claude headless (Layer 2 — cheap)
    4. Generate drift report

    Returns summary dict.
    """
    logger.info("=" * 50)
    logger.info("TaxIA Fiscal Drift Analyzer")
    logger.info("=" * 50)

    # Step 1: Read pending ingest
    if not PENDING_INGEST.exists():
        logger.info("No _pending_ingest.json found — nothing to analyze")
        return {"status": "no_changes", "analyzed": 0}

    with open(PENDING_INGEST, "r", encoding="utf-8") as f:
        pending = json.load(f)

    files = pending.get("files", [])
    if not files:
        logger.info("_pending_ingest.json is empty — nothing to analyze")
        return {"status": "no_changes", "analyzed": 0}

    logger.info(f"Found {len(files)} changed document(s)")

    # Step 2: Classify (Layer 1 — free)
    changes = []
    for file_info in files:
        path = file_info.get("path", "")
        priority, reason = classify_file(path)
        territory = extract_territory(path)
        changes.append({
            "path": path,
            "territory": territory,
            "status": file_info.get("status", "unknown"),
            "size": file_info.get("size", 0),
            "priority": priority,
            "reason": reason,
        })

    high_count = sum(1 for c in changes if c["priority"] == "high")
    medium_count = sum(1 for c in changes if c["priority"] == "medium")
    low_count = sum(1 for c in changes if c["priority"] == "low")

    logger.info(f"Classification: {high_count} high, {medium_count} medium, {low_count} low priority")

    # Step 3: Claude analysis (Layer 2 — only for high/medium priority)
    analysis = None
    actionable = [c for c in changes if c["priority"] in ("high", "medium")]

    if actionable and not skip_llm:
        logger.info(f"Invoking Claude for {len(actionable)} actionable change(s)...")
        prompt = build_analysis_prompt(actionable)
        analysis = run_claude_analysis(prompt, dry_run=dry_run)

        if analysis:
            logger.info("Claude analysis completed successfully")
        else:
            logger.warning("Claude analysis returned no result — report will be pattern-based only")
    elif skip_llm:
        logger.info("Skipping LLM analysis (--skip-llm)")
    else:
        logger.info("No high/medium priority changes — skipping LLM analysis")

    # Step 4: Generate report
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = PLANS_DIR / f"drift-report-{today}.md"
    generate_drift_report(changes, analysis, report_path)

    # Step 5: Email alert (only for high/medium priority, not in dry-run)
    email_sent = False
    if actionable and NOTIFY_EMAIL and not dry_run:
        email_sent = send_drift_email(changes, analysis, report_path)

    summary = {
        "status": "analyzed",
        "analyzed": len(changes),
        "high_priority": high_count,
        "medium_priority": medium_count,
        "low_priority": low_count,
        "llm_invoked": analysis is not None,
        "email_sent": email_sent,
        "report_path": str(report_path),
    }

    logger.info(f"Drift analysis complete: {json.dumps(summary, indent=2)}")
    return summary


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    dry_run = "--dry-run" in sys.argv
    skip_llm = "--skip-llm" in sys.argv

    if dry_run:
        logger.info("Running in DRY-RUN mode (no Claude calls)")
    if skip_llm:
        logger.info("Running with --skip-llm (pattern classification only)")

    try:
        result = analyze_drift(dry_run=dry_run, skip_llm=skip_llm)
        if result["status"] == "no_changes":
            print("No pending changes to analyze.")
        else:
            print(f"Analysis complete. Report: {result.get('report_path', 'N/A')}")
    except Exception as e:
        logger.error(f"Drift analysis failed: {e}", exc_info=True)
        sys.exit(1)
