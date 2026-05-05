"""
Daily RAG quality check.

Runs the existing RAGEvaluator over the ground-truth set and emails the owner
if faithfulness drops below the configured threshold (default 0.85). Designed
as a Railway cron service ('0 5 * * *' — 5 AM UTC).

Why this matters: PoisonedRAG, doc rot, model drift can silently degrade
answer quality. We want to detect it BEFORE users complain.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT.parent / ".env")
except ImportError:
    pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


FAITHFULNESS_THRESHOLD = float(os.getenv("RAG_FAITHFULNESS_THRESHOLD", "0.85"))
ANSWER_CORRECTNESS_THRESHOLD = float(os.getenv("RAG_ANSWER_THRESHOLD", "0.75"))


async def main() -> int:
    from app.services.rag_evaluator import RAGEvaluator

    owner_email = os.getenv("OWNER_EMAIL") or os.getenv("ALERT_EMAIL")
    if not owner_email:
        logger.error("OWNER_EMAIL or ALERT_EMAIL not set — refusing to run")
        return 1

    evaluator = RAGEvaluator()
    report = await evaluator.run_full_evaluation()
    aggregates = report.get("aggregates", {}) if isinstance(report, dict) else {}

    faithfulness = aggregates.get("faithfulness", 0.0)
    answer_correctness = aggregates.get("answer_correctness", 0.0)
    relevance = aggregates.get("context_relevance", 0.0)
    quality = aggregates.get("response_quality", 0.0)

    logger.info(
        "RAG metrics: faithfulness=%.3f answer=%.3f relevance=%.3f quality=%.3f",
        faithfulness, answer_correctness, relevance, quality,
    )

    breaches = []
    if faithfulness < FAITHFULNESS_THRESHOLD:
        breaches.append(f"faithfulness {faithfulness:.3f} < {FAITHFULNESS_THRESHOLD}")
    if answer_correctness < ANSWER_CORRECTNESS_THRESHOLD:
        breaches.append(f"answer_correctness {answer_correctness:.3f} < {ANSWER_CORRECTNESS_THRESHOLD}")

    if not breaches:
        logger.info("RAG quality OK")
        return 0

    logger.warning("RAG quality breaches: %s", breaches)

    # Build email
    rows = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee'>{m}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #eee;text-align:right'>{aggregates.get(m, 0):.3f}</td></tr>"
        for m in ("faithfulness", "answer_correctness", "context_relevance", "response_quality")
    )
    breach_html = "<ul>" + "".join(f"<li>{b}</li>" for b in breaches) + "</ul>"
    body = (
        "<h2>Alerta de calidad RAG</h2>"
        f"<p>Las siguientes métricas han caído por debajo del umbral configurado:</p>"
        f"{breach_html}"
        "<p><strong>Métricas actuales:</strong></p>"
        "<table style='border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px'>"
        "<thead><tr style='background:#f3f4f6'>"
        "<th style='padding:8px 10px;text-align:left'>Métrica</th>"
        "<th style='padding:8px 10px;text-align:right'>Score</th>"
        "</tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        "<p style='color:#666;font-size:12px;margin-top:16px'>"
        "Posibles causas: nuevo doc poisoned, model drift, regresion en system prompt, "
        "RAG retriever roto. Revisa el panel /admin/rag-quality."
        "</p>"
    )
    try:
        from app.services.email_service import EmailService
        email = EmailService()
        await email.send_email(
            to=owner_email,
            subject=f"[Impuestify] Calidad RAG por debajo del umbral ({len(breaches)} métricas)",
            html=body,
        )
        logger.info("Alert email sent to %s", owner_email)
    except Exception as e:
        logger.error("Failed to send alert email: %s", e)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
