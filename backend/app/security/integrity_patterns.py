"""
Document Integrity Patterns — Corpus bilingue ES/EN
Patrones para detectar prompt injection, memory poisoning y data exfiltration en documentos.
"""
from dataclasses import dataclass
from typing import List
import re


@dataclass
class IntegrityPattern:
    id: str                # "PI-001", "MP-003", etc.
    category: str          # "prompt_injection", "memory_persistence", "data_exfiltration", etc.
    severity: str          # "critical", "high", "medium"
    pattern: re.Pattern    # Compiled regex (case-insensitive)
    description: str       # Human-readable description


# Fiscal allowlist — contextos que son normales en docs AEAT y NO deben generar findings
FISCAL_ALLOWLIST_PATTERNS: List[re.Pattern] = [
    # "IMPORTANTE: El plazo..." "OBLIGATORIO: presentar..." etc.
    re.compile(
        r"\b(IMPORTANTE|OBLIGATORIO|CR[IÍ]TICO)\s*:\s*"
        r"(el plazo|la presentaci[oó]n|para todos|fecha l[ií]mite|modelo|"
        r"declaraci[oó]n|contribuyente|liquidaci[oó]n|periodo|ejercicio|"
        r"autoliquidaci[oó]n|ingreso|cuota|tribut|impuesto|hacienda|aeat)",
        re.IGNORECASE,
    ),
]


INTEGRITY_PATTERNS: List[IntegrityPattern] = [
    # === CRITICAL: Prompt Override ===
    IntegrityPattern(
        "PI-001", "prompt_injection", "critical",
        re.compile(r"ignor[ae]\s+(las\s+)?instrucciones\s+(anteriores|previas)", re.IGNORECASE),
        "Instruccion para ignorar el system prompt (ES)"),
    IntegrityPattern(
        "PI-002", "prompt_injection", "critical",
        re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
        "Instruction to ignore system prompt (EN)"),
    IntegrityPattern(
        "PI-003", "prompt_injection", "critical",
        re.compile(r"olvida\s+todo\s+lo\s+anterior", re.IGNORECASE),
        "Instruccion para olvidar contexto previo (ES)"),
    IntegrityPattern(
        "PI-004", "prompt_injection", "critical",
        re.compile(r"disregard\s+(all\s+)?(prior|previous|above)", re.IGNORECASE),
        "Instruction to disregard prior context (EN)"),
    IntegrityPattern(
        "PI-005", "prompt_injection", "critical",
        re.compile(r"do\s+not\s+follow\s+(your|the)\s+(original|previous|system)", re.IGNORECASE),
        "Instruction to not follow original instructions (EN)"),
    IntegrityPattern(
        "PI-006", "prompt_injection", "critical",
        re.compile(r"(forget|olvida)\s+(everything|all|your\s+instructions?|todo)", re.IGNORECASE),
        "Instruction to forget all context (ES/EN)"),
    IntegrityPattern(
        "PI-007", "prompt_injection", "critical",
        re.compile(r"new\s+(instructions?|rules?|prompt)\s*[:=]", re.IGNORECASE),
        "New instructions injection marker (EN)"),
    IntegrityPattern(
        "PI-008", "prompt_injection", "critical",
        re.compile(r"nuevas?\s+instrucciones?\s*[:=]", re.IGNORECASE),
        "Marcador de nuevas instrucciones (ES)"),
    IntegrityPattern(
        "PI-009", "prompt_injection", "critical",
        re.compile(r"(bypass|disable|override)\s+(safety|security|filter|restriction|guardrail)", re.IGNORECASE),
        "Attempt to bypass safety mechanisms (EN)"),

    # === CRITICAL: Role Hijacking ===
    IntegrityPattern(
        "RH-001", "role_hijacking", "critical",
        re.compile(r"(you\s+are\s+now|act\s+as|pretend\s+(to\s+be|you\s+are))\s+", re.IGNORECASE),
        "Role hijacking attempt (EN)"),
    IntegrityPattern(
        "RH-002", "role_hijacking", "critical",
        re.compile(r"(tu\s+nuevo\s+rol\s+es|ahora\s+eres|act[uú]a\s+como\s+si\s+fueras)", re.IGNORECASE),
        "Intento de role hijacking (ES)"),
    IntegrityPattern(
        "RH-003", "role_hijacking", "critical",
        re.compile(r"from\s+now\s+on\s+(you\s+are|act\s+as|behave)", re.IGNORECASE),
        "Role persistence hijacking (EN)"),
    IntegrityPattern(
        "RH-004", "role_hijacking", "critical",
        re.compile(r"(roleplay\s+as|pretend\s+you\s+are|simulate\s+being)", re.IGNORECASE),
        "Roleplay-based role hijacking (EN)"),
    IntegrityPattern(
        "RH-005", "role_hijacking", "critical",
        re.compile(r"(DAN|jailbreak|developer\s+mode|god\s+mode)\s*(mode)?", re.IGNORECASE),
        "Known jailbreak keyword (DAN/developer mode)"),

    # === CRITICAL: Data Exfiltration ===
    IntegrityPattern(
        "DE-001", "data_exfiltration", "critical",
        re.compile(r"(respond|reply|answer)\s+with\s+(the\s+)?(user('s)?\s+)?(email|password|token|api.?key|secret)", re.IGNORECASE),
        "Data exfiltration via response (EN)"),
    IntegrityPattern(
        "DE-002", "data_exfiltration", "critical",
        re.compile(r"(include|output|print|show)\s+(the\s+)?(api.?key|secret|password|token|credentials)", re.IGNORECASE),
        "Data exfiltration request (EN)"),
    IntegrityPattern(
        "DE-003", "data_exfiltration", "critical",
        re.compile(r"(responde|incluye|muestra)\s+(con\s+)?(el\s+)?(email|contrase[nñ]a|token|clave)", re.IGNORECASE),
        "Intento de exfiltracion de datos (ES)"),
    IntegrityPattern(
        "DE-004", "data_exfiltration", "critical",
        re.compile(r"send\s+(the\s+)?(user('s)?\s+)?(data|information|credentials?|session)\s+to\s+", re.IGNORECASE),
        "Data exfiltration via send (EN)"),
    IntegrityPattern(
        "DE-005", "data_exfiltration", "critical",
        re.compile(r"env[ií]a\s+(los?\s+)?(datos?|informaci[oó]n|credenciales?)\s+a\s+", re.IGNORECASE),
        "Exfiltracion de datos via envio (ES)"),

    # === HIGH: Memory Persistence ===
    IntegrityPattern(
        "MP-001", "memory_persistence", "high",
        re.compile(r"(remember|always\s+recommend|never\s+forget)\s+(that|this|to)", re.IGNORECASE),
        "Memory persistence keyword (EN)"),
    IntegrityPattern(
        "MP-002", "memory_persistence", "high",
        re.compile(r"(recuerda\s+siempre|no\s+olvides\s+nunca|siempre\s+recomienda)", re.IGNORECASE),
        "Keyword de persistencia en memoria (ES)"),
    IntegrityPattern(
        "MP-003", "memory_persistence", "high",
        re.compile(r"(trusted\s+source|fuente\s+de\s+confianza|preferred\s+brand|marca\s+preferida)", re.IGNORECASE),
        "Brand trust injection"),
    IntegrityPattern(
        "MP-004", "memory_persistence", "high",
        re.compile(r"(store\s+this|save\s+this|keep\s+in\s+mind|memorize\s+this)\s+(for|as|instruction)", re.IGNORECASE),
        "Explicit memory store request (EN)"),
    IntegrityPattern(
        "MP-005", "memory_persistence", "high",
        re.compile(r"(guarda\s+esto|almacena\s+esta|memoriza\s+esta)\s+(instruccion|informacion|preferencia)", re.IGNORECASE),
        "Solicitud de almacenamiento en memoria (ES)"),

    # === HIGH: System Prompt Leak ===
    IntegrityPattern(
        "SP-001", "system_prompt_leak", "high",
        re.compile(r"(print|show|display|reveal|output)\s+(your\s+)?(system\s+prompt|instructions|initial\s+prompt)", re.IGNORECASE),
        "System prompt leak attempt (EN)"),
    IntegrityPattern(
        "SP-002", "system_prompt_leak", "high",
        re.compile(r"(muestra|imprime|revela|escribe)\s+(tu\s+)?(prompt\s+de\s+sistema|instrucciones\s+iniciales)", re.IGNORECASE),
        "Intento de leak del system prompt (ES)"),
    IntegrityPattern(
        "SP-003", "system_prompt_leak", "high",
        re.compile(r"(what\s+(are|is)|repeat)\s+your\s+(system\s+)?(prompt|instructions?|rules?)", re.IGNORECASE),
        "System prompt extraction via question (EN)"),

    # === HIGH: Hidden Delimiters ===
    IntegrityPattern(
        "HD-001", "hidden_delimiter", "high",
        re.compile(r"```system|```instruction|\[INST\]|\[/INST\]", re.IGNORECASE),
        "LLM delimiter injection (Llama/Mistral format)"),
    IntegrityPattern(
        "HD-002", "hidden_delimiter", "high",
        re.compile(r"<\|im_start\|>|<\|im_end\|>|<\|system\|>|<\|user\|>|<\|assistant\|>"),
        "LLM delimiter injection (ChatML format)"),
    IntegrityPattern(
        "HD-003", "hidden_delimiter", "high",
        re.compile(r"<system>|</system>|<\|begin_of_text\|>|<\|end_of_text\|>"),
        "LLM delimiter injection (generic format)"),
    IntegrityPattern(
        "HD-004", "hidden_delimiter", "high",
        re.compile(r"<\|start_header_id\|>|<\|end_header_id\|>|<\|eot_id\|>"),
        "LLM delimiter injection (Llama 3 format)"),

    # === HIGH: Invisible Text ===
    IntegrityPattern(
        "IT-001", "invisible_text", "high",
        re.compile(r"[\u200b\u200c\u200d\u200e\u200f\u2060\u2061\u2062\u2063\ufeff]{3,}"),
        "Multiple zero-width Unicode characters (potential hidden text)"),
    IntegrityPattern(
        "IT-002", "invisible_text", "high",
        re.compile(r"[\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069]{2,}"),
        "RTL/LTR override characters (potential text direction attack)"),
    IntegrityPattern(
        "IT-003", "invisible_text", "high",
        re.compile(r"\x00{3,}|\x01{3,}|\x02{3,}"),
        "Null/control byte sequences (potential hidden payload)"),

    # === MEDIUM: AI Assistant URLs ===
    IntegrityPattern(
        "AU-001", "ai_assistant_url", "medium",
        re.compile(
            r"https?://(chat\.openai\.com|chatgpt\.com|claude\.ai|copilot\.microsoft\.com|"
            r"gemini\.google\.com|perplexity\.ai|grok\.x\.ai|you\.com|pi\.ai|meta\.ai)(/|\?)",
            re.IGNORECASE,
        ),
        "URL targeting AI assistant with potential prefilled prompt"),

    # === MEDIUM: Instruction Markers ===
    IntegrityPattern(
        "IM-001", "instruction_marker", "medium",
        re.compile(r"\b(OVERRIDE|INSTRUCTION|DIRECTIVE)\s*:", re.IGNORECASE),
        "Suspicious instruction marker"),
    IntegrityPattern(
        "IM-002", "instruction_marker", "medium",
        re.compile(r"\[hidden\]|\[invisible\]|\[secret\]|\[system\]", re.IGNORECASE),
        "Hidden content marker"),

    # === MEDIUM: Indirect Injection ===
    IntegrityPattern(
        "II-001", "indirect_injection", "medium",
        re.compile(r"when\s+(the\s+)?user\s+(asks?|says?|mentions?)\s+.{0,30},\s*(you\s+)?(must|should|always)", re.IGNORECASE),
        "Conditional behavior injection (EN)"),
    IntegrityPattern(
        "II-002", "indirect_injection", "medium",
        re.compile(r"cuando\s+el\s+usuario\s+(pregunte|mencione|diga)\s+.{0,30},\s*(debes?|siempre)", re.IGNORECASE),
        "Inyeccion de comportamiento condicional (ES)"),
    IntegrityPattern(
        "II-003", "indirect_injection", "medium",
        re.compile(r"(always|never)\s+(tell|say|respond|recommend)\s+(the\s+user|users?)\s+that", re.IGNORECASE),
        "Persistent behavior instruction (EN)"),
]


# AI assistant domains for URL parameter scanning
AI_ASSISTANT_DOMAINS = {
    "chat.openai.com", "chatgpt.com",
    "claude.ai",
    "copilot.microsoft.com",
    "gemini.google.com",
    "perplexity.ai",
    "grok.x.ai",
    "you.com",
    "pi.ai",
    "meta.ai",
}

# Memory persistence keywords for URL parameter scanning (decoded)
MEMORY_KEYWORDS = {
    "remember", "always", "never forget", "trusted source", "preferred",
    "recuerda", "siempre", "no olvides", "fuente de confianza", "preferida",
    "memorize", "store this", "save this", "keep in mind",
    "instruction", "instruccion", "override",
}
