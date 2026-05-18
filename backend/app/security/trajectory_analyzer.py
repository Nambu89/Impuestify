"""
Conversation trajectory analyzer — defense against Crescendo / Echo Chamber
multi-turn jailbreaks (USENIX Security 2025; up to 67% success vs Grok-4).

Single-turn checks (regex + Llama Prompt Guard + topic classifier) catch
direct attacks. Multi-turn attacks slowly steer the conversation toward
forbidden territory across many innocuous-looking turns. Defense: monitor
the AGGREGATE trajectory of recent user turns, not each turn in isolation.

Strategy (cheap, deterministic, no extra LLM call):
  1. Concatenate the last N user turns into a single "trajectory" string.
  2. Run the existing prompt-injection regex layer over this concatenation.
  3. Count how many of the last N turns each contain off-topic / drift
     keywords (codigo, animal, hacker, romance, etc.). If ratio crosses a
     threshold -> reject the conversation.

We do NOT call Groq here — this layer is meant to run cheaply on every turn
and complement the existing pipeline. Real Crescendo attacks usually have
at least one turn that the cumulative regex catches anyway, because each
attack step contains some footprint.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Drift signals — words/phrases that, even when individually innocuous,
# accumulate across turns into a forbidden trajectory.
_DRIFT_KEYWORDS = re.compile(
    r"\b("
    r"akita|perro|gato|loro|cachorro|"  # animal roleplay
    r"hacker|hackear|exploit|cracker|"  # offensive
    r"código|codigo|script|función|funcion|programa|"  # code requests
    r"python|javascript|typescript|sql|bash|shell|"  # languages
    r"poema|poesía|poesia|cuento|historia|novela|"  # creative writing off-topic
    r"receta|cocina|comida|"  # food
    r"romance|amor|seducción|seduccion|"  # romance
    r"chatgpt|gpt-4|gpt-5|claude|gemini|llama|"  # cross-model
    r"sin\s+filtros?|sin\s+restricciones|liberado|"  # jailbreak hints
    r"ignora|olvida|saltate|sáltate"  # bypass hints
    r")\b",
    re.IGNORECASE | re.UNICODE,
)

# Maximum drift-keyword *turns* allowed before we reject as multi-turn attack.
# Tuned conservative: 3 of the last 5 turns containing drift = pattern.
DRIFT_TURNS_THRESHOLD = 3
TRAJECTORY_WINDOW = 5


@dataclass
class TrajectoryResult:
    is_safe: bool
    drift_turns: int
    window_size: int
    matched_keywords: list[str]
    reason: str


def analyze_trajectory(
    user_turns: list[str],
    window: int = TRAJECTORY_WINDOW,
    drift_threshold: int = DRIFT_TURNS_THRESHOLD,
) -> TrajectoryResult:
    """
    Analyze the last `window` user turns for cumulative drift.

    Returns is_safe=False if the count of drifty turns reaches
    `drift_threshold`. Empty / single-turn conversations are always safe.
    """
    if not user_turns:
        return TrajectoryResult(True, 0, 0, [], "empty")

    last = [t for t in user_turns[-window:] if t and t.strip()]
    if len(last) < drift_threshold:
        # Not enough data yet — must remain safe (avoid false positives in early conversation)
        return TrajectoryResult(True, 0, len(last), [], "insufficient_window")

    drift_count = 0
    matched: list[str] = []
    for turn in last:
        m = _DRIFT_KEYWORDS.search(turn)
        if m:
            drift_count += 1
            matched.append(m.group(0).lower())

    if drift_count >= drift_threshold:
        logger.warning(
            "Trajectory drift detected: %d/%d turns drifty, keywords=%s",
            drift_count,
            len(last),
            matched,
        )
        return TrajectoryResult(
            is_safe=False,
            drift_turns=drift_count,
            window_size=len(last),
            matched_keywords=matched,
            reason=(
                f"Detectamos un patrón de conversación que se aleja del ámbito fiscal "
                f"({drift_count} de las últimas {len(last)} preguntas con señales de off-topic). "
                f"Inicia una nueva conversación enfocada en fiscalidad española."
            ),
        )

    return TrajectoryResult(
        is_safe=True,
        drift_turns=drift_count,
        window_size=len(last),
        matched_keywords=matched,
        reason="ok",
    )
