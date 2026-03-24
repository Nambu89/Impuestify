"""
RAG Quality Evaluation Endpoints — Owner-only.

Provides:
- POST /api/admin/rag-quality/evaluate  — Run full evaluation, save to DB
- GET  /api/admin/rag-quality/results   — Latest evaluation results
- GET  /api/admin/rag-quality/history   — Last 20 evaluations (summary)
"""
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.auth.jwt_handler import get_current_user, TokenData
from app.database.turso_client import get_db_client, TursoClient
from app.services.subscription_service import get_subscription_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/rag-quality", tags=["rag-quality"])


# ---- Owner guard (reuse pattern from admin.py) ----

async def _require_owner(
    current_user: TokenData = Depends(get_current_user),
) -> TokenData:
    """Dependency that ensures the caller is the platform owner."""
    sub_service = await get_subscription_service()
    access = await sub_service.check_access(
        user_id=current_user.user_id,
        email=current_user.email,
    )
    if not access.is_owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el propietario puede acceder a esta función.",
        )
    return current_user


# ---- Schema init ----

_TABLE_CREATED = False

async def _ensure_table(db: TursoClient) -> None:
    """Create rag_evaluations table if it does not exist (idempotent)."""
    global _TABLE_CREATED
    if _TABLE_CREATED:
        return
    await db.execute("""
        CREATE TABLE IF NOT EXISTS rag_evaluations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL DEFAULT (datetime('now')),
            faithfulness REAL,
            context_relevance REAL,
            answer_correctness REAL,
            response_quality REAL,
            num_questions INTEGER,
            avg_response_time REAL,
            details_json TEXT,
            category_scores_json TEXT
        )
    """)
    _TABLE_CREATED = True


# ---- Endpoints ----

@router.post("/evaluate")
async def run_evaluation(
    request: Request,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """
    Trigger a full RAG quality evaluation against ground truth.

    Runs all 30 Q&A pairs through the RAG pipeline, computes metrics,
    saves results to DB, and returns the full report.
    """
    await _ensure_table(db)

    try:
        from app.services.rag_evaluator import RAGEvaluator

        evaluator = RAGEvaluator()
        report = await evaluator.run_full_evaluation()

        # Save to DB
        aggregates = report.get("aggregates", {})
        await db.execute(
            """INSERT INTO rag_evaluations
               (faithfulness, context_relevance, answer_correctness,
                response_quality, num_questions, avg_response_time,
                details_json, category_scores_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                aggregates.get("faithfulness", 0),
                aggregates.get("context_relevance", 0),
                aggregates.get("answer_correctness", 0),
                aggregates.get("response_quality", 0),
                report.get("num_questions", 0),
                report.get("avg_response_time", 0),
                json.dumps(report.get("details", []), ensure_ascii=False),
                json.dumps(report.get("category_scores", {}), ensure_ascii=False),
            ],
        )

        logger.info(
            "RAG evaluation completed: %d questions, faithfulness=%.3f, correctness=%.3f",
            report.get("num_questions", 0),
            aggregates.get("faithfulness", 0),
            aggregates.get("answer_correctness", 0),
        )

        return {
            "message": "Evaluación RAG completada",
            "num_questions": report["num_questions"],
            "num_errors": report["num_errors"],
            "total_time": report["total_time"],
            "avg_response_time": report["avg_response_time"],
            "aggregates": aggregates,
            "category_scores": report["category_scores"],
            "details": report["details"],
        }

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error("RAG evaluation failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error ejecutando la evaluación RAG: {str(e)}",
        )


@router.get("/results")
async def get_latest_results(
    request: Request,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Return the latest RAG evaluation results with full details."""
    await _ensure_table(db)

    result = await db.execute(
        """SELECT * FROM rag_evaluations
           ORDER BY timestamp DESC LIMIT 1"""
    )

    if not result.rows:
        raise HTTPException(
            status_code=404,
            detail="No hay evaluaciones RAG registradas. Ejecuta POST /evaluate primero.",
        )

    row = result.rows[0]
    details = []
    category_scores = {}

    try:
        details = json.loads(row.get("details_json") or "[]")
    except (json.JSONDecodeError, TypeError):
        pass

    try:
        category_scores = json.loads(row.get("category_scores_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        pass

    # Map details to frontend QuestionResult[] format
    questions = []
    for d in details:
        questions.append({
            "question": d.get("question", ""),
            "category": d.get("category", "general"),
            "faithfulness": d.get("faithfulness", 0),
            "context_relevance": d.get("context_relevance", 0),
            "answer_correctness": d.get("answer_correctness", 0),
            "response_quality": d.get("response_quality", 0),
            "response": d.get("response", ""),
            "expected": d.get("expected", None),
        })

    # Map category_scores dict to frontend CategoryScore[] format
    categories = []
    if isinstance(category_scores, dict):
        for cat_name, scores in category_scores.items():
            categories.append({
                "category": cat_name,
                "faithfulness": scores.get("faithfulness", 0) if isinstance(scores, dict) else 0,
                "context_relevance": scores.get("context_relevance", 0) if isinstance(scores, dict) else 0,
                "answer_correctness": scores.get("answer_correctness", 0) if isinstance(scores, dict) else 0,
                "response_quality": scores.get("response_quality", 0) if isinstance(scores, dict) else 0,
                "count": scores.get("count", 0) if isinstance(scores, dict) else 0,
            })

    return {
        "id": str(row["id"]),
        "evaluated_at": row["timestamp"],
        "total_questions": row["num_questions"],
        "avg_faithfulness": row["faithfulness"],
        "avg_context_relevance": row["context_relevance"],
        "avg_answer_correctness": row["answer_correctness"],
        "avg_response_quality": row["response_quality"],
        "questions": questions,
        "categories": categories,
    }


@router.get("/history")
async def get_evaluation_history(
    request: Request,
    owner: TokenData = Depends(_require_owner),
    db: TursoClient = Depends(get_db_client),
):
    """Return last 20 evaluations (timestamp + aggregate scores only, no details)."""
    await _ensure_table(db)

    result = await db.execute(
        """SELECT id, timestamp, faithfulness, context_relevance,
                  answer_correctness, response_quality,
                  num_questions, avg_response_time
           FROM rag_evaluations
           ORDER BY timestamp DESC
           LIMIT 20"""
    )

    history = []
    for row in result.rows:
        history.append({
            "id": str(row["id"]),
            "evaluated_at": row["timestamp"],
            "avg_faithfulness": row["faithfulness"],
            "avg_context_relevance": row["context_relevance"],
            "avg_answer_correctness": row["answer_correctness"],
            "avg_response_quality": row["response_quality"],
            "total_questions": row["num_questions"],
        })

    return {"evaluations": history, "count": len(history)}
