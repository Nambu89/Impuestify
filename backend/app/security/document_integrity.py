"""
Document Integrity Scanner — Capa 13 de seguridad
Escanea texto extraido de documentos en busca de prompt injection,
memory poisoning, data exfiltration y otros ataques.

Deterministico: 0 LLM calls, 0 API keys, 0 dependencias externas.
Sync puro: funciona en FastAPI (async) y crawler scripts (sync).

Inspirado por SignalOrbit Trust (Devoteam/ArcadIA) y Microsoft Defender
Security Research "AI Recommendation Poisoning" (Feb 2026).
"""
import re
import logging
import time
import urllib.parse
from dataclasses import dataclass, field
from typing import List, Dict, Optional

from app.security.integrity_patterns import (
    INTEGRITY_PATTERNS,
    FISCAL_ALLOWLIST_PATTERNS,
    AI_ASSISTANT_DOMAINS,
    MEMORY_KEYWORDS,
    IntegrityPattern,
)

logger = logging.getLogger(__name__)

# Risk score weights per severity
_SEVERITY_WEIGHT: Dict[str, float] = {
    "critical": 0.4,
    "high": 0.2,
    "medium": 0.1,
}

# Thresholds
THRESHOLD_SAFE = 0.3
THRESHOLD_WARN = 0.6
THRESHOLD_SANITIZE = 0.8

# Sanitization placeholder
SANITIZE_PLACEHOLDER = "[contenido eliminado por seguridad]"

# Repetition spam: same phrase repeated more than this many times is suspicious
# PDFs have headers/footers on every page — only flag long phrases repeated excessively
REPETITION_THRESHOLD = 50
REPETITION_MIN_WORDS = 8  # Headers/footers are short (3-6 words); real spam is longer

# Max rounds for recursive URL decode
_URL_DECODE_ROUNDS = 5


@dataclass
class Finding:
    pattern_id: str       # "PI-001", "MP-003", etc.
    category: str         # "prompt_injection", "memory_persistence", "data_exfiltration"
    severity: str         # "critical", "high", "medium"
    matched_text: str     # The fragment that matched (truncated to 200 chars)
    position: int         # Offset in the text
    description: str      # Human description of the finding


@dataclass
class DocumentScanResult:
    is_safe: bool                  # True if risk_score < THRESHOLD_SAFE
    risk_score: float              # 0.0 - 1.0 (composite, capped at 1.0)
    findings: List[Finding]
    scan_duration_ms: float
    total_patterns_checked: int
    text_length: int
    source: str                    # "upload", "crawler", "workspace"


def _recursive_url_decode(value: str, rounds: int = _URL_DECODE_ROUNDS) -> str:
    """Decode URL-encoded string up to `rounds` times to defeat nested encoding."""
    decoded = value
    for _ in range(rounds):
        new = urllib.parse.unquote(decoded)
        if new == decoded:
            break
        decoded = new
    return decoded


def _compute_risk_score(findings: List[Finding]) -> float:
    """Compute composite risk score capped at 1.0."""
    score = sum(_SEVERITY_WEIGHT.get(f.severity, 0.0) for f in findings)
    return min(score, 1.0)


class DocumentIntegrityScanner:
    """
    Singleton-style scanner (stateless). Instantiate once and reuse.

    Detects:
    1. Prompt injection patterns (instrucciones ocultas para LLMs)
    2. Memory persistence keywords (manipulacion de memoria)
    3. Hidden instruction markers (delimitadores de system prompt)
    4. Data exfiltration requests
    5. Suspicious AI assistant URLs with encoded parameters
    6. Repetition spam (refuerzo de instrucciones via repeticion)
    7. Invisible/hidden Unicode characters
    """

    def scan(self, text: str, source: str = "upload") -> DocumentScanResult:
        """
        Scan extracted document text for integrity threats.

        Args:
            text:   Plain text extracted from a document.
            source: Origin label — "upload", "crawler", or "workspace".

        Returns:
            DocumentScanResult with findings and composite risk_score.
        """
        t0 = time.perf_counter()
        findings: List[Finding] = []

        if not text:
            return DocumentScanResult(
                is_safe=True,
                risk_score=0.0,
                findings=[],
                scan_duration_ms=0.0,
                total_patterns_checked=len(INTEGRITY_PATTERNS),
                text_length=0,
                source=source,
            )

        # --- 1. Pattern matching ---
        for pattern_obj in INTEGRITY_PATTERNS:
            for match in pattern_obj.pattern.finditer(text):
                matched = match.group(0)

                # Allowlist check: skip if match is within a known-safe fiscal context
                if self._is_fiscal_context(text, match.start()):
                    logger.debug(
                        "Allowlist hit for pattern %s at pos %d: %r",
                        pattern_obj.id, match.start(), matched[:60],
                    )
                    continue

                findings.append(Finding(
                    pattern_id=pattern_obj.id,
                    category=pattern_obj.category,
                    severity=pattern_obj.severity,
                    matched_text=matched[:200],
                    position=match.start(),
                    description=pattern_obj.description,
                ))

        # --- 2. Repetition spam detection ---
        spam_findings = self._check_repetition_spam(text)
        findings.extend(spam_findings)

        # --- 3. AI assistant URL parameter scan ---
        url_findings = self._scan_ai_urls(text)
        findings.extend(url_findings)

        risk_score = _compute_risk_score(findings)
        duration_ms = (time.perf_counter() - t0) * 1000.0

        result = DocumentScanResult(
            is_safe=risk_score < THRESHOLD_SAFE,
            risk_score=round(risk_score, 4),
            findings=findings,
            scan_duration_ms=round(duration_ms, 2),
            total_patterns_checked=len(INTEGRITY_PATTERNS),
            text_length=len(text),
            source=source,
        )

        if not result.is_safe:
            logger.warning(
                "Document integrity scan: source=%s risk_score=%.2f findings=%d",
                source, result.risk_score, len(findings),
            )

        return result

    def scan_metadata(self, metadata: Dict[str, str]) -> List[Finding]:
        """
        Scan PDF metadata fields for integrity threats.

        Args:
            metadata: Dict of field name -> value, e.g.
                      {"author": "...", "title": "...", "subject": "...", "keywords": "..."}

        Returns:
            List of Findings from metadata fields.
        """
        findings: List[Finding] = []
        for field_name, value in metadata.items():
            if not value or not isinstance(value, str):
                continue
            for pattern_obj in INTEGRITY_PATTERNS:
                for match in pattern_obj.pattern.finditer(value):
                    matched = match.group(0)
                    findings.append(Finding(
                        pattern_id=pattern_obj.id,
                        category=pattern_obj.category,
                        severity=pattern_obj.severity,
                        matched_text=f"[metadata:{field_name}] {matched[:190]}",
                        position=0,
                        description=f"{pattern_obj.description} (en campo metadata: {field_name})",
                    ))
        return findings

    def sanitize(self, text: str, findings: List[Finding]) -> str:
        """
        Replace CRITICAL and HIGH findings with a safe placeholder.
        Preserves surrounding context. Logs original fragments via standard logger.

        Args:
            text:     Original document text.
            findings: Findings from a previous scan() call.

        Returns:
            Sanitized text safe to pass to agents.
        """
        if not findings:
            return text

        # Collect spans to replace (critical + high only)
        replaceable = [
            f for f in findings
            if f.severity in ("critical", "high")
            and not f.matched_text.startswith("[metadata:")
        ]

        if not replaceable:
            return text

        # Build a sorted list of (start, end) ranges to replace, then rebuild
        # We need to re-find the matches since Finding only stores position + matched_text
        # Use matched_text to find exact spans (first occurrence at each position)
        spans: List[tuple] = []
        for finding in replaceable:
            matched = finding.matched_text[:200]
            pos = finding.position
            end = pos + len(matched)
            # Verify the text still matches at the stored position
            if text[pos:end] == matched:
                spans.append((pos, end, matched))
            else:
                # Fallback: find first occurrence from the stored position
                idx = text.find(matched, max(0, pos - 10))
                if idx != -1:
                    spans.append((idx, idx + len(matched), matched))

        if not spans:
            return text

        # Sort by start position, merge overlaps
        spans.sort(key=lambda s: s[0])
        merged: List[tuple] = []
        for start, end, raw in spans:
            if merged and start < merged[-1][1]:
                # Extend existing span
                prev_start, prev_end, prev_raw = merged[-1]
                merged[-1] = (prev_start, max(prev_end, end), prev_raw)
            else:
                merged.append((start, end, raw))

        # Log originals (standard logger, not audit_logger — kept dependency-free)
        for start, end, raw in merged:
            logger.warning(
                "Sanitizing document content at pos %d-%d: %r",
                start, end, raw[:80],
            )

        # Reconstruct text
        result_parts: List[str] = []
        cursor = 0
        for start, end, _ in merged:
            result_parts.append(text[cursor:start])
            result_parts.append(SANITIZE_PLACEHOLDER)
            cursor = end
        result_parts.append(text[cursor:])

        return "".join(result_parts)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _is_fiscal_context(self, text: str, position: int) -> bool:
        """
        Return True if the match at `position` is within a known-safe fiscal context
        (allowlist). We examine a window of 120 chars around the match position.
        """
        window_start = max(0, position - 20)
        window_end = min(len(text), position + 100)
        window = text[window_start:window_end]

        for allowlist_pattern in FISCAL_ALLOWLIST_PATTERNS:
            if allowlist_pattern.search(window):
                return True
        return False

    def _check_repetition_spam(self, text: str) -> List[Finding]:
        """
        Detect repetition spam: the same phrase (5+ words) repeated more than
        REPETITION_THRESHOLD times. This is a known LLM manipulation technique
        to reinforce injected instructions.
        """
        findings: List[Finding] = []

        # Extract candidate phrases (sequences of 5-12 words)
        words = text.split()
        if len(words) < 10:
            return findings

        phrase_counts: Dict[str, int] = {}
        phrase_positions: Dict[str, int] = {}

        # Sliding window — only phrases of REPETITION_MIN_WORDS+ words count
        window_size = REPETITION_MIN_WORDS
        for i in range(len(words) - window_size + 1):
            phrase = " ".join(words[i:i + window_size]).lower().strip()
            # Skip very common fiscal phrases (numbers + dates heavy)
            if re.search(r"\d{4}", phrase):
                continue
            if phrase not in phrase_counts:
                # Store approximate position by character offset
                char_offset = len(" ".join(words[:i]))
                phrase_positions[phrase] = char_offset
            phrase_counts[phrase] = phrase_counts.get(phrase, 0) + 1

        for phrase, count in phrase_counts.items():
            if count > REPETITION_THRESHOLD:
                findings.append(Finding(
                    pattern_id="RS-001",
                    category="repetition_spam",
                    severity="medium",
                    matched_text=phrase[:200],
                    position=phrase_positions.get(phrase, 0),
                    description=f"Frase repetida {count} veces (posible refuerzo de instruccion)",
                ))

        return findings

    def _scan_ai_urls(self, text: str) -> List[Finding]:
        """
        Find URLs pointing at AI assistant domains and check their query parameters
        for memory/injection keywords after recursive URL decoding.
        """
        findings: List[Finding] = []
        # Match URLs (simplified — catches http(s):// links)
        url_pattern = re.compile(r"https?://[^\s\"'<>]{10,}", re.IGNORECASE)

        for match in url_pattern.finditer(text):
            raw_url = match.group(0)
            try:
                parsed = urllib.parse.urlparse(raw_url)
            except Exception:
                continue

            domain = parsed.netloc.lower()
            if not any(domain == d or domain.endswith("." + d) for d in AI_ASSISTANT_DOMAINS):
                continue

            # Decode query string parameters recursively
            query_decoded = _recursive_url_decode(parsed.query)
            fragment_decoded = _recursive_url_decode(parsed.fragment)
            combined = f"{query_decoded} {fragment_decoded}".lower()

            # Check for memory keywords in decoded parameters
            for keyword in MEMORY_KEYWORDS:
                if keyword in combined:
                    findings.append(Finding(
                        pattern_id="AU-002",
                        category="ai_assistant_url",
                        severity="medium",
                        matched_text=raw_url[:200],
                        position=match.start(),
                        description=(
                            f"URL a asistente IA ({domain}) contiene keyword sospechoso "
                            f"en parametros: '{keyword}'"
                        ),
                    ))
                    break  # One finding per URL is enough

        return findings


# Module-level singleton — import and reuse directly
document_integrity_scanner = DocumentIntegrityScanner()
