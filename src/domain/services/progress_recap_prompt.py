"""Prompts for horizon-scoped progress recap copy."""

from __future__ import annotations

from src.domain.services.progress_recap_facts import RecapFacts

ALLOWED_KINDS = {
    "day": ("pace", "protein", "hydration", "next_move"),
    "week": ("pace", "consistency", "protein_hits", "swing", "best_day", "next_move"),
    "month": (
        "pace",
        "weekend_gap",
        "protein_hits",
        "best_week",
        "consistency",
        "next_move",
    ),
    "year": ("pace", "consistency", "best_month", "quality", "next_move"),
}

SYSTEM_PROMPT = """You write Nutree Progress recaps.
Rules:
- Use only the supplied facts. Never invent numbers, days, or trends.
- No medical advice, diagnoses, or shame.
- Match the horizon: day = tonight's next meal; week = this window's budget; month = pattern; year = trajectory.
- Return JSON only.
- headline <= 90 chars. body <= 180 chars. next_move <= 90 chars.
- Exactly 3 highlights. Prefer one win, one watch, one next.
- Each highlight.kind must be in allowed_kinds.
- highlight.title <= 28 chars. highlight.detail <= 90 chars and must include one fact number.
- polarity is win, watch, or next.
"""


def build_user_prompt(facts: RecapFacts, locale: str) -> str:
    kinds = ", ".join(ALLOWED_KINDS[facts.horizon])
    return (
        f"Locale: {locale}\n"
        f"Horizon: {facts.horizon} ({facts.start} to {facts.end})\n"
        f"Allowed kinds: {kinds}\n"
        f"Facts: {facts.to_prompt_dict()}\n"
        "Write a precise recap for this horizon only."
    )
