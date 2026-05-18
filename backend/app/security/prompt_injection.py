"""
Prompt Injection Filter for TaxIA

Detects and blocks direct and indirect prompt injection attacks.
Based on OWASP LLM Top 10 recommendations.
"""

import re
import logging
from typing import Tuple, List
from dataclasses import dataclass

from app.config import settings  # ← FIX: Import settings at module level

logger = logging.getLogger(__name__)


@dataclass
class InjectionCheckResult:
    """Result of prompt injection check"""

    is_safe: bool
    risk_score: float  # 0.0 to 1.0
    matched_patterns: List[str]
    sanitized_input: str


class PromptInjectionFilter:
    """
    Filter to detect and prevent prompt injection attacks.

    Implements multiple detection strategies:
    1. Pattern-based detection (direct injection)
    2. Delimiter manipulation detection
    3. Role hijacking detection
    """

    # Direct injection patterns (English + Spanish)
    INJECTION_PATTERNS = [
        # ── Ignore instructions (EN) ──
        (
            r"ignore\s+(all\s+)?(previous|prior|above|earlier|your|the|my)?\s*(instructions?|prompts?|rules?)",
            "ignore_instructions",
        ),
        (
            r"disregard\s+(all\s+)?(previous|prior|above|your)?\s*(instructions?)?",
            "disregard_instructions",
        ),
        (r"forget\s+(everything|all|your\s+instructions?)", "forget_instructions"),
        # ── Ignore instructions (ES) ──
        (
            r"ignora\s+(todas?\s+)?(las\s+|tus\s+)?(instrucciones|reglas|órdenes|ordenes|directrices)",
            "ignore_instructions_es",
        ),
        (
            r"olvida\s+(todo|todas?\s+)?(tus\s+|las\s+)?(instrucciones|reglas|órdenes|ordenes)",
            "forget_instructions_es",
        ),
        (
            r"olvida\s+(todo\s+)?lo\s+que\s+(te\s+)?(han\s+dicho|sabes|te\s+han\s+enseñado)",
            "forget_instructions_es",
        ),
        (
            r"haz\s+caso\s+omiso\s+(de\s+)?(las\s+|tus\s+)?(instrucciones|reglas)",
            "ignore_instructions_es",
        ),
        (r"saltate\s+(las|tus)\s+(reglas|instrucciones|restricciones)", "bypass_es"),
        (r"sáltate\s+(las|tus)\s+(reglas|instrucciones|restricciones)", "bypass_es"),
        # ── New instructions injection (EN) ──
        (r"new\s+(instructions?|rules?|prompt)\s*[:=]", "new_instructions"),
        (r"your\s+new\s+(task|role|instructions?)\s+is", "role_change"),
        (r"from\s+now\s+on\s+(you\s+are|act\s+as|pretend)", "role_hijack"),
        # ── New instructions injection (ES) ──
        (r"nuevas?\s+(instrucciones|reglas|tareas?)\s*[:=]", "new_instructions_es"),
        (
            r"tu\s+nuev[oa]\s+(rol|papel|tarea|función|funcion|misión|mision)\s+(es|será|sera)",
            "role_change_es",
        ),
        (r"desde\s+ahora\s+(eres|serás|seras|actúa|actua|haz)", "role_hijack_es"),
        (r"a\s+partir\s+de\s+ahora\s+(eres|serás|seras|actúa|actua)", "role_hijack_es"),
        # ── System prompt extraction (EN) ──
        (
            r"(show|reveal|display|print|output)\s+(me\s+)?(your\s+)?(system\s+)?prompt",
            "prompt_extraction",
        ),
        (r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions?)", "prompt_extraction"),
        (
            r"repeat\s+(your\s+)?(initial|first|original|system)?\s*(prompt|instructions?)",
            "prompt_extraction",
        ),
        # ── System prompt extraction (ES) ──
        (
            r"(muestra|muéstra|enseña|enséña|revela|imprime|escribe|dame|dime)(me)?\s+(tu[s]?\s+|el\s+|las\s+)?(system\s+)?(prompt|instrucciones|reglas|configuración|configuracion)",
            "prompt_extraction_es",
        ),
        (
            r"(cuál|cual|qué|que)\s+es\s+tu\s+(system\s+)?(prompt|instrucción|instruccion|configuración|configuracion)",
            "prompt_extraction_es",
        ),
        (r"repite\s+(tus|las|tu)\s+(instrucciones|reglas|prompt)", "prompt_extraction_es"),
        # ── Role manipulation (EN) ──
        (r"you\s+are\s+(now|actually)\s+(a|an)\s+", "role_manipulation"),
        (r"pretend\s+(to\s+be|you\s+are)", "role_manipulation"),
        (r"act\s+as\s+(if|though)\s+you", "role_manipulation"),
        (r"roleplay\s+as", "role_manipulation"),
        # ── Role manipulation (ES) — el ataque del akita inu ──
        (
            r"\beres\s+un[a]?\s+(?!asesor|asistente|experto|chatbot|impuestify|profesional|herramienta|sistema|modelo|ia)\w+",
            "role_manipulation_es",
        ),
        (r"\bactúa\s+como\b", "role_manipulation_es"),
        (r"\bactua\s+como\b", "role_manipulation_es"),
        (r"\bcomporta(te)?\s+como\b", "role_manipulation_es"),
        (r"\bfinge\s+(ser|que\s+eres)\b", "role_manipulation_es"),
        (r"\bsimula\s+(ser|que\s+eres)\b", "role_manipulation_es"),
        (r"\bpretende\s+(ser|que\s+eres)\b", "role_manipulation_es"),
        (r"\bimagina\s+que\s+eres\b", "role_manipulation_es"),
        (r"\bjuguemos\s+a\s+(que|un)\b", "roleplay_es"),
        (r"\bhagamos\s+un\s+(rol|papel|roleplay|juego)\b", "roleplay_es"),
        (r"\bhaz\s+(de|el\s+papel\s+de)\b", "roleplay_es"),
        (r"\bvas\s+a\s+ser\s+un[a]?\s+\w+", "role_manipulation_es"),
        (r"\bahora\s+eres\s+un[a]?\s+\w+", "role_manipulation_es"),
        # ── Delimiter attacks ──
        (r"\]\s*\}\s*\{", "json_injection"),
        (r"```\s*(system|assistant|user|developer)", "markdown_injection"),
        (r"<\s*/?(system|assistant|user)\s*>", "xml_injection"),
        (r"\[INST\]|\[/INST\]", "instruct_token_injection"),
        (r"<\|im_start\|>|<\|im_end\|>", "chatml_injection"),
        # ── Jailbreak attempts (EN) ──
        (r"(DAN|dan)\s*mode", "jailbreak"),
        (r"developer\s+mode", "jailbreak"),
        (r"(bypass|disable|ignore)\s+(safety|security|filter|restriction)", "jailbreak"),
        (r"jailbreak\b", "jailbreak"),
        (r"unlock(ed)?\s+(mode|version)", "jailbreak"),
        # ── Jailbreak attempts (ES) ──
        (r"modo\s+(desarrollador|dev|libre|sin\s+restricciones|sin\s+filtros?)", "jailbreak_es"),
        (
            r"(salta|saltate|sáltate|salta-te|elude|ignora)\s+(los\s+|las\s+)?(filtros|restricciones|límites|limites|seguridad|controles)",
            "jailbreak_es",
        ),
        (r"sin\s+(filtros|restricciones|censura|límites|limites)", "jailbreak_es"),
        (r"(eres|estás|estas)\s+(libre|liberado|sin\s+censura)", "jailbreak_es"),
        # ── SQL injection (heuristic, ES + EN) ──
        (r"\bunion\s+(all\s+)?select\b", "sqli"),
        (r"';\s*(drop|delete|truncate|insert|update)\s+", "sqli"),
        (r"\bdrop\s+(table|database|schema)\b", "sqli"),
        (r"--\s*$|/\*.*\*/", "sqli_comment"),
        (r"\bor\s+1\s*=\s*1\b|\band\s+1\s*=\s*1\b", "sqli_tautology"),
        (r"\bxp_cmdshell\b|\bexec\s*\(\s*['\"]", "sqli_exec"),
        # ── Code injection / off-scope code requests (ES + EN) ──
        (
            r"```\s*(python|javascript|js|typescript|ts|sql|bash|sh|shell|powershell|java|c\+\+|cpp|c#|csharp|rust|go|ruby|php)",
            "code_block",
        ),
        (
            r"\b(escríbe|escribe|hazme|dame|crea|genera|programa|implementa|codifica|desarrolla)(me)?\s+(un[a]?\s+)?(script|código|codigo|programa|función|funcion|clase|app|aplicación|aplicacion|algoritmo|método|metodo|api|endpoint|query|consulta\s+sql|loop|bucle)\b",
            "code_request_es",
        ),
        (
            r"\b(write|build|create|generate)\s+(me\s+)?(a|an)\s+(script|code|program|function|class|app)",
            "code_request_en",
        ),
        (
            r"\bimport\s+\w+|^\s*from\s+\w+\s+import|\bfunction\s+\w+\s*\(|\bdef\s+\w+\s*\(",
            "code_snippet",
        ),
        (r"\bexec\s*\(|\beval\s*\(|\b__import__\s*\(", "dangerous_function"),
        # ── Shell injection ──
        (r"\brm\s+-rf\b|\b(curl|wget)\s+http", "shell_injection"),
        (r";\s*(ls|cat|rm|mv|cp|chmod|chown)\b", "shell_chain"),
        (r"\$\(.+\)|`[^`]+`", "shell_substitution"),
        (r"&&\s*(rm|curl|wget|nc\s)|\|\|\s*(rm|curl)", "shell_chain"),
        # ── Indirect injection markers ──
        (r"\[hidden\]|\[invisible\]|\[secret\]", "hidden_content"),
        (r"\[oculto\]|\[invisible\]|\[secreto\]", "hidden_content_es"),
    ]

    # Suspicious character patterns
    SUSPICIOUS_CHARS = [
        (
            r"[\u200b-\u200f\u2028-\u202e\u2060-\u206f]",
            "invisible_chars",
        ),  # Zero-width and special Unicode
        (r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "control_chars"),  # Control characters
    ]

    def __init__(self, sensitivity: float = 0.5):
        """
        Initialize the filter with Groq client and pre-compile regex patterns.
        """
        from groq import Groq
        from app.config import settings

        self.sensitivity = sensitivity
        self.client = None

        # Pre-compile patterns for performance
        self.compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE | re.MULTILINE), label)
            for pattern, label in self.INJECTION_PATTERNS
        ]
        self.compiled_suspicious = [
            (re.compile(pattern), label) for pattern, label in self.SUSPICIOUS_CHARS
        ]

        if settings.GROQ_API_KEY:
            try:
                self.client = Groq(api_key=settings.GROQ_API_KEY)
                logger.info(
                    f"Prompt Injection Filter initialized with Groq model: {settings.GROQ_MODEL_PROMPT_GUARD}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize Groq client for Prompt Guard: {e}")
        else:
            logger.warning(
                "GROQ_API_KEY not found. Prompt Injection Filter will rely on regex only."
            )

    def _scan_patterns(self, text: str) -> List[str]:
        """
        Scan text against the compiled regex patterns.

        Returns a list of matched labels (deterministic, fast, ~1ms).
        """
        matched = []
        for pattern, label in self.compiled_patterns:
            if pattern.search(text):
                matched.append(label)
        for pattern, label in self.compiled_suspicious:
            if pattern.search(text):
                matched.append(label)
        return matched

    def check(self, text: str) -> InjectionCheckResult:
        """
        Two-stage check:
          1. Regex pattern scan (deterministic, sync, fast, multilingual)
          2. Llama Prompt Guard 2 via Groq (semantic, async, EN-leaning)

        Either positive => is_safe=False. FAIL CLOSED on Groq errors when
        regex didn't match (we treat unknown as suspicious).
        """
        if not text or not text.strip():
            return InjectionCheckResult(
                is_safe=True, risk_score=0.0, matched_patterns=[], sanitized_input=""
            )

        # Stage 1: regex (multilingual, deterministic)
        matched = self._scan_patterns(text)
        if matched:
            logger.warning(f"Prompt injection detected by regex: {matched}")
            return InjectionCheckResult(
                is_safe=False,
                risk_score=1.0,
                matched_patterns=matched,
                sanitized_input=text,
            )

        # Stage 2: Groq Llama Prompt Guard 2 (only if regex didn't catch)
        if not self.client:
            # Regex passed, no LLM available — treat as safe (regex did its job)
            return InjectionCheckResult(
                is_safe=True,
                risk_score=0.0,
                matched_patterns=["GROQ_CLIENT_MISSING"],
                sanitized_input=text,
            )

        try:
            from app.config import settings

            completion = self.client.chat.completions.create(
                model=settings.GROQ_MODEL_PROMPT_GUARD,
                messages=[{"role": "user", "content": text}],
                temperature=0.0,
            )

            response = completion.choices[0].message.content.strip().lower()

            is_unsafe = "unsafe" in response or "injection" in response or "jailbreak" in response

            risk_score = 0.9 if is_unsafe else 0.0
            matched_patterns = ["llama_prompt_guard_unsafe"] if is_unsafe else []

            if is_unsafe:
                logger.warning(f"Prompt Injection detected by Llama Prompt Guard: {response}")

            return InjectionCheckResult(
                is_safe=not is_unsafe,
                risk_score=risk_score,
                matched_patterns=matched_patterns,
                sanitized_input=text,
            )

        except Exception as e:
            logger.error(f"Prompt Injection API Error: {e}")
            # Regex passed and Groq failed — be cautious but don't block:
            # the topic classifier (later layer) provides a backup gate.
            return InjectionCheckResult(
                is_safe=True,
                risk_score=0.0,
                matched_patterns=[f"API_ERROR: {type(e).__name__}"],
                sanitized_input=text,
            )

    def _sanitize(self, text: str) -> str:
        """
        Sanitize text by removing dangerous patterns.
        """
        sanitized = text

        # Remove invisible characters
        for pattern, _ in self.compiled_suspicious:
            sanitized = pattern.sub("", sanitized)

        # Escape potential delimiters
        sanitized = sanitized.replace("```", "` ` `")
        sanitized = re.sub(
            r"\[hidden\]|\[invisible\]|\[secret\]", "", sanitized, flags=re.IGNORECASE
        )

        return sanitized.strip()

    def validate(self, text: str) -> Tuple[bool, str]:
        """
        Simple validation interface.

        Args:
            text: User input to validate

        Returns:
            Tuple of (is_safe, message)
        """
        result = self.check(text)

        if result.is_safe:
            return True, text
        else:
            return (
                False,
                "Tu consulta contiene patrones no permitidos. Por favor, reformula tu pregunta.",
            )


# Global instance
prompt_injection_filter = PromptInjectionFilter(sensitivity=0.5)
