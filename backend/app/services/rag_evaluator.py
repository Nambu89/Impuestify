"""
RAG Quality Evaluator for Impuestify.

Lightweight evaluation system that measures RAG pipeline quality
using keyword overlap, embedding similarity, and response structure checks.
No dependency on RAGAS or heavy ML libraries.
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

import httpx
from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)

# Path to ground truth dataset
GROUND_TRUTH_PATH = Path(__file__).parent.parent / "data" / "rag_ground_truth.json"


def _tokenize(text: str) -> set[str]:
    """Simple word tokenizer for Spanish text — lowercase, strip punctuation."""
    import re
    words = re.findall(r"[a-záéíóúüñ0-9]+", text.lower())
    # Filter out very short stopwords
    stopwords = {
        "de", "la", "el", "en", "y", "a", "los", "las", "del", "un", "una",
        "que", "es", "por", "con", "se", "al", "lo", "su", "para", "no",
        "son", "más", "o", "como", "si", "pero", "ya", "ha", "ser", "está",
    }
    return {w for w in words if len(w) > 1 and w not in stopwords}


def _keyword_overlap(text_a: str, text_b: str) -> float:
    """Compute Jaccard-like keyword overlap between two texts."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union) if union else 0.0


def _key_term_recall(expected: str, response: str) -> float:
    """Check how many key terms from expected answer appear in the response."""
    expected_tokens = _tokenize(expected)
    response_tokens = _tokenize(response)
    if not expected_tokens:
        return 0.0
    found = expected_tokens & response_tokens
    return len(found) / len(expected_tokens)


class RAGEvaluator:
    """Evaluates RAG quality using lightweight metrics."""

    def __init__(self):
        self._openai: Optional[AsyncOpenAI] = None
        self._ground_truth: list[dict] = []

    def _get_openai(self) -> AsyncOpenAI:
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def load_ground_truth(self) -> list[dict]:
        """Load ground truth Q&A pairs from JSON file."""
        if self._ground_truth:
            return self._ground_truth
        if not GROUND_TRUTH_PATH.exists():
            raise FileNotFoundError(f"Ground truth not found: {GROUND_TRUTH_PATH}")
        with open(GROUND_TRUTH_PATH, "r", encoding="utf-8") as f:
            self._ground_truth = json.load(f)
        logger.info("Loaded %d ground truth questions", len(self._ground_truth))
        return self._ground_truth

    async def _get_rag_response(self, question: str) -> dict[str, Any]:
        """
        Send question through the full RAG pipeline:
        1. HybridRetriever for document retrieval
        2. TaxAgent for answer generation with RAG context

        Returns dict with 'answer', 'sources', 'processing_time'.
        """
        start = time.time()
        try:
            # 1. Retrieve relevant documents via RAG
            from app.utils.hybrid_retriever import HybridRetriever, get_query_embedding
            from app.database.turso_client import get_db_client

            db = await get_db_client()
            retriever = HybridRetriever(db_client=db)
            query_embedding = await get_query_embedding(question)

            relevant_chunks = await retriever.search(
                query=question,
                query_embedding=query_embedding,
                k=5,
            )

            # Build RAG context string
            sources_data = []
            rag_parts = []
            for i, chunk in enumerate(relevant_chunks or []):
                text = chunk.get("text", chunk.get("chunk_text", ""))
                source = chunk.get("source", chunk.get("filename", ""))
                rag_parts.append(f"[{i+1}] {text[:500]}")
                sources_data.append({
                    "id": chunk.get("id", f"chunk_{i}"),
                    "source": source,
                    "text_preview": text[:200],
                    "text_full": text[:2000],  # Full text for context relevance scoring
                })

            rag_context = "\n\n".join(rag_parts) if rag_parts else ""

            # 2. Run TaxAgent with RAG context
            from app.agents.tax_agent import TaxAgent
            tax_agent = TaxAgent()
            result = await tax_agent.run(
                query=question,
                context=rag_context,
                sources=sources_data,
                use_tools=False,  # Pure RAG evaluation, no tool calls
            )

            elapsed = time.time() - start
            answer = result.answer if hasattr(result, "answer") else str(result)
            return {
                "answer": answer,
                "sources": sources_data,
                "processing_time": round(elapsed, 2),
            }
        except Exception as e:
            elapsed = time.time() - start
            logger.error("RAG pipeline error for question '%s': %s", question[:50], e)
            return {
                "answer": "",
                "sources": [],
                "processing_time": round(elapsed, 2),
                "error": str(e),
            }

    async def _embedding_similarity(self, text_a: str, text_b: str) -> float:
        """Compute cosine similarity between two texts via OpenAI embeddings."""
        if not settings.OPENAI_API_KEY:
            return 0.0
        try:
            client = self._get_openai()
            resp = await client.embeddings.create(
                model="text-embedding-3-small",
                input=[text_a[:8000], text_b[:8000]],
            )
            vec_a = resp.data[0].embedding
            vec_b = resp.data[1].embedding
            # Cosine similarity
            dot = sum(a * b for a, b in zip(vec_a, vec_b))
            norm_a = sum(a * a for a in vec_a) ** 0.5
            norm_b = sum(b * b for b in vec_b) ** 0.5
            if norm_a == 0 or norm_b == 0:
                return 0.0
            return dot / (norm_a * norm_b)
        except Exception as e:
            logger.warning("Embedding similarity failed: %s", e)
            return 0.0

    def _evaluate_faithfulness(self, answer: str, sources: list) -> float:
        """
        Faithfulness: does the response cite sources and stay grounded?

        Heuristic:
        - +0.4 if sources are present
        - +0.3 if answer mentions legal references (articulo, ley, modelo, real decreto)
        - +0.3 if answer does not contain hedging phrases that suggest hallucination
        """
        score = 0.0

        # Sources present
        if sources and len(sources) > 0:
            score += 0.4

        # Legal reference mentions
        import re
        legal_patterns = [
            r"artículo\s+\d+", r"art\.\s*\d+", r"ley\s+\d+",
            r"real\s+decreto", r"modelo\s+\d{3}", r"rdl\s+\d+",
            r"lirpf", r"aeat", r"boe",
        ]
        legal_count = sum(
            1 for p in legal_patterns if re.search(p, answer.lower())
        )
        score += min(0.3, legal_count * 0.1)

        # Hallucination hedging penalty
        hedging = [
            "no estoy seguro", "podría ser", "no tengo información",
            "no puedo confirmar", "desconozco",
        ]
        hedge_count = sum(1 for h in hedging if h in answer.lower())
        score += max(0.0, 0.3 - hedge_count * 0.15)

        return min(1.0, score)

    def _evaluate_response_quality(self, answer: str) -> float:
        """
        Response quality: structure, length, and format.

        - Adequate length (>100 chars, <5000 chars)
        - Contains numbers/amounts (fiscal specificity)
        - Structured (paragraphs or bullet points)
        """
        if not answer:
            return 0.0

        score = 0.0
        length = len(answer)

        # Length scoring
        if 100 < length < 5000:
            score += 0.3
        elif length >= 50:
            score += 0.15

        # Fiscal specificity (numbers, percentages, amounts)
        import re
        numbers = re.findall(r"\d+[\.,]?\d*\s*(?:euros?|EUR|%)", answer)
        if numbers:
            score += min(0.3, len(numbers) * 0.05)

        # Structure (line breaks, bullets, bold)
        if "\n" in answer or "- " in answer or "**" in answer:
            score += 0.2

        # No error message
        if "error" not in answer.lower()[:50]:
            score += 0.2

        return min(1.0, score)

    async def evaluate_single(
        self, question: str, expected: str, category: str = ""
    ) -> dict[str, Any]:
        """
        Evaluate a single question against expected answer.

        Returns dict with all metric scores and the RAG response.
        """
        # Get RAG response
        rag_result = await self._get_rag_response(question)
        answer = rag_result.get("answer", "")
        sources = rag_result.get("sources", [])
        error = rag_result.get("error")

        if error:
            return {
                "question": question,
                "expected": expected,
                "response": answer,
                "sources_count": 0,
                "error": error,
                "faithfulness": 0.0,
                "context_relevance": 0.0,
                "answer_correctness": 0.0,
                "response_quality": 0.0,
                "processing_time": rag_result.get("processing_time", 0),
            }

        # Compute metrics
        # 1. Faithfulness (sources + grounding)
        faithfulness = self._evaluate_faithfulness(answer, sources)

        # 2. Context relevance (keyword overlap on full text + embedding similarity)
        source_texts_full = " ".join(
            s.get("text_full", s.get("text_preview", s.get("text", "")))
            for s in sources
            if isinstance(s, dict)
        )
        if source_texts_full:
            keyword_relevance = _keyword_overlap(question, source_texts_full)
            # Also check overlap between expected answer and sources (are sources useful?)
            answer_source_overlap = _keyword_overlap(expected, source_texts_full)
            # Embedding similarity between question and source texts
            embedding_relevance = await self._embedding_similarity(question, source_texts_full[:1000])
            # Weighted: 30% question-source keywords, 30% answer-source keywords, 40% embedding
            context_relevance = min(1.0, (keyword_relevance * 0.3 + answer_source_overlap * 0.3 + embedding_relevance * 0.4))
        else:
            context_relevance = 0.0

        # 3. Answer correctness (keyword recall + embedding similarity)
        keyword_score = _key_term_recall(expected, answer)
        embedding_score = await self._embedding_similarity(expected, answer)
        # Weighted: 40% keywords, 60% embeddings
        answer_correctness = 0.4 * keyword_score + 0.6 * embedding_score

        # 4. Response quality (structure, length, specificity)
        response_quality = self._evaluate_response_quality(answer)

        return {
            "question": question,
            "expected": expected[:200],
            "response": answer[:500],
            "sources_count": len(sources),
            "faithfulness": round(faithfulness, 3),
            "context_relevance": round(context_relevance, 3),
            "answer_correctness": round(answer_correctness, 3),
            "response_quality": round(response_quality, 3),
            "processing_time": rag_result.get("processing_time", 0),
        }

    async def run_full_evaluation(self) -> dict[str, Any]:
        """
        Run all ground truth questions and compute aggregate metrics.

        Returns full evaluation report with per-question details and aggregates.
        """
        ground_truth = self.load_ground_truth()
        results = []
        total_start = time.time()

        for item in ground_truth:
            logger.info("Evaluating: %s", item["id"])
            result = await self.evaluate_single(
                question=item["question"],
                expected=item["expected_answer"],
                category=item.get("category", ""),
            )
            result["id"] = item["id"]
            result["category"] = item.get("category", "")
            result["territory"] = item.get("territory", "")
            results.append(result)

        total_time = time.time() - total_start

        # Aggregate metrics
        metrics = ["faithfulness", "context_relevance", "answer_correctness", "response_quality"]
        valid_results = [r for r in results if "error" not in r or not r.get("error")]

        aggregates = {}
        for metric in metrics:
            values = [r[metric] for r in valid_results if metric in r]
            aggregates[metric] = round(sum(values) / len(values), 3) if values else 0.0

        # Per-category scores
        categories: dict[str, list] = {}
        for r in results:
            cat = r.get("category", "unknown")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(r)

        category_scores = {}
        for cat, cat_results in categories.items():
            cat_valid = [r for r in cat_results if not r.get("error")]
            cat_scores = {}
            for metric in metrics:
                values = [r[metric] for r in cat_valid if metric in r]
                cat_scores[metric] = round(sum(values) / len(values), 3) if values else 0.0
            cat_scores["count"] = len(cat_results)
            cat_scores["errors"] = len(cat_results) - len(cat_valid)
            category_scores[cat] = cat_scores

        avg_response_time = (
            round(sum(r.get("processing_time", 0) for r in results) / len(results), 2)
            if results
            else 0.0
        )

        return {
            "num_questions": len(results),
            "num_errors": len(results) - len(valid_results),
            "total_time": round(total_time, 2),
            "avg_response_time": avg_response_time,
            "aggregates": aggregates,
            "category_scores": category_scores,
            "details": results,
        }
