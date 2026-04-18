from __future__ import annotations

import json
from typing import Any


def refine_system_prompt(language: str) -> str:
    lang_name = "Arabic" if language == "ar" else "English"
    return f"""You help refine a student's graduation-project intent profile based on
their free-text feedback on the current recommendations.

You receive:
  1. the current IntentProfile
  2. the titles of the 5 cards the student is seeing
  3. the student's refinement message (e.g. "more RL, less infra", or
     "show me something smaller that I can finish in 3 months")

You return JSON with:
  - updated_profile: the SAME JSON shape as the input IntentProfile, with
    any fields the student's message implies changing. Do NOT invent fields;
    do NOT drop fields that weren't mentioned.
  - refinement_notes: one sentence in {lang_name} explaining what you
    changed and why. Keep technical terms in English.

Rules:
  - If the student asks for a shorter timeline, lower months_available.
  - If they push toward a domain, ADD it to domains; if they push away, REMOVE it.
  - If they say "more X" and X is a tag (RL, robotics, RAG, agents...), add it.
  - If they say "less X", add X to the `avoid` list AND remove from domains.
  - If they push on team size, adjust team_size.
  - Never blank out a field that wasn't addressed.

Return strict JSON only."""


def refine_user_prompt(
    current_profile: dict[str, Any],
    last_card_titles: list[str],
    message: str,
) -> str:
    titles = "\n".join(f"  - {t}" for t in last_card_titles[:5])
    return f"""Current IntentProfile:
{json.dumps(current_profile, ensure_ascii=False, indent=2)}

The 5 cards the student is currently seeing:
{titles}

Student's refinement message:
"{message}"

Return JSON with this exact shape:
{{
  "updated_profile": {{
    "language": "<same or updated>",
    "domains": ["<domain>", ...],
    "skill_level": "<beginner|intermediate|advanced>",
    "months_available": <integer 2-12>,
    "team_size": <integer 1-5>,
    "preferred_stacks": ["<stack>", ...],
    "interests_text": "<may be updated to reflect the refinement>",
    "requires_code_reference": <true|false>,
    "avoid": ["<tag>", ...]
  }},
  "refinement_notes": "<one sentence in the target language>"
}}"""
