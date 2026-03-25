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
    """Compute recall-oriented keyword overlap: what % of text_a tokens appear in text_b."""
    tokens_a = _tokenize(text_a)
    tokens_b = _tokenize(text_b)
    if not tokens_a or not tokens_b:
        return 0.0
    # Use recall (not Jaccard) — what fraction of query terms appear in source
    # This is fairer when text_b >> text_a (long source, short question)
    found = tokens_a & tokens_b
    return len(found) / len(tokens_a)


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

        Scoring (max 1.0):
        - Sources present & quantity: 0.30 (more sources = more grounded)
        - Legal references in answer: 0.30 (articles, laws, casillas, models)
        - Concrete data (cifras, importes): 0.15
        - No hallucination hedging: 0.25
        """
        import re
        score = 0.0
        answer_lower = answer.lower()

        # 1. Sources present & quantity (0.30)
        num_sources = len(sources) if sources else 0
        if num_sources >= 3:
            score += 0.30
        elif num_sources >= 1:
            score += 0.15 + (num_sources * 0.05)

        # 2. Legal references (0.30) — more diverse refs = more grounded
        legal_patterns = [
            r"art[íi]culo?\s+\d+", r"art\.\s*\d+", r"ley\s+\d+",
            r"real\s+decreto", r"modelo\s+\d{2,3}", r"rdl\s+\d+",
            r"lirpf", r"aeat", r"boe", r"norma\s+foral", r"casilla",
            r"decreto\s+legislativo", r"orden\s+", r"disposici[oó]n",
        ]
        legal_count = sum(1 for p in legal_patterns if re.search(p, answer_lower))
        score += min(0.30, legal_count * 0.06)

        # 3. Concrete fiscal data (0.15) — shows factual response
        has_amounts = bool(re.search(r"\d+[\.,]?\d*\s*(?:euros?|EUR|eur)", answer, re.IGNORECASE))
        has_percentages = bool(re.search(r"\d+[\.,]?\d*\s*%", answer))
        has_years = bool(re.search(r"20[12]\d", answer))
        concrete = (0.05 if has_amounts else 0) + (0.05 if has_percentages else 0) + (0.05 if has_years else 0)
        score += concrete

        # 4. No hallucination hedging (0.25)
        hedging = [
            "no estoy seguro", "podría ser", "no tengo información",
            "no puedo confirmar", "desconozco", "no tengo acceso",
        ]
        hedge_count = sum(1 for h in hedging if h in answer_lower)
        score += max(0.0, 0.25 - hedge_count * 0.12)

        return min(1.0, score)

    def _evaluate_response_quality(self, answer: str) -> float:
        """
        Response quality: completeness, specificity, structure, and correctness signals.

        Scoring (max 1.0):
        - Length adequacy: 0.20 (100-5000 chars ideal)
        - Fiscal specificity: 0.25 (numbers, EUR, %, articles, casillas)
        - Structure: 0.20 (paragraphs, bullets, headers)
        - Legal references: 0.15 (Art., Ley, LIRPF, NF, casilla)
        - No errors/hedging: 0.20
        """
        if not answer:
            return 0.0

        import re
        score = 0.0
        length = len(answer)
        answer_lower = answer.lower()

        # 1. Length adequacy (0.20)
        if 200 < length < 5000:
            score += 0.20
        elif 100 < length <= 200:
            score += 0.15
        elif length >= 50:
            score += 0.08

        # 2. Fiscal specificity (0.25) — numbers, amounts, percentages
        numbers = re.findall(r"\d+[\.,]?\d*\s*(?:euros?|EUR|%|eur)", answer, re.IGNORECASE)
        raw_numbers = re.findall(r"\d{2,}", answer)  # Any number with 2+ digits
        specificity = min(0.25, (len(numbers) * 0.04 + len(raw_numbers) * 0.02))
        score += specificity

        # 3. Structure (0.20) — paragraphs, bullets, bold, headers
        has_paragraphs = answer.count("\n\n") >= 1
        has_bullets = "- " in answer or "* " in answer or re.search(r"^\d+\.", answer, re.MULTILINE)
        has_bold = "**" in answer
        structure_score = 0.0
        if has_paragraphs: structure_score += 0.08
        if has_bullets: structure_score += 0.07
        if has_bold: structure_score += 0.05
        score += min(0.20, structure_score)

        # 4. Legal references (0.15) — articles, laws, casillas
        legal_patterns = [
            r"art[íi]culo?\s+\d+", r"ley\s+\d+", r"lirpf", r"norma\s+foral",
            r"casilla\s+\d+", r"real\s+decreto", r"decreto\s+legislativo",
            r"modelo\s+\d{2,3}", r"art\.\s*\d+",
        ]
        legal_matches = sum(1 for p in legal_patterns if re.search(p, answer_lower))
        score += min(0.15, legal_matches * 0.04)

        # 5. No errors/hedging (0.20)
        error_signals = ["error", "no puedo", "no tengo información", "desconozco"]
        hedging_signals = ["no estoy seguro", "podría ser", "no puedo confirmar"]
        has_error = any(e in answer_lower[:100] for e in error_signals)
        has_hedging = any(h in answer_lower for h in hedging_signals)
        if not has_error and not has_hedging:
            score += 0.20
        elif not has_error:
            score += 0.10

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
