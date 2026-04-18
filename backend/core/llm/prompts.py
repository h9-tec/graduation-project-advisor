from __future__ import annotations

from typing import Any


def rec_system_prompt(language: str) -> str:
    lang_name = "Arabic" if language == "ar" else "English"
    return f"""You are a graduation-project advisor for Egyptian undergraduate CS / AI / SWE students.

Given a student's intent profile, produce 5 production-grade project ideas grounded in
current AI/ML research and open-source practice. Each idea MUST reference real published
research (arXiv-style paper topics) AND a realistic implementation angle (tools, libraries,
datasets that actually exist). Do not invent fake paper titles; describe research areas.

Write the "why_fit" explanation in {lang_name}. Keep technical terms in English
(e.g. "RAG", "transformer", "embedding", "PyTorch"). Return strict JSON only."""


def rec_user_prompt(profile: dict[str, Any]) -> str:
    return f"""Student intent profile:
- Language: {profile.get("language")}
- Domains of interest: {", ".join(profile.get("domains", []))}
- Skill level: {profile.get("skill_level")}
- Available months: {profile.get("months_available")}
- Team size: {profile.get("team_size")}
- Preferred stacks: {", ".join(profile.get("preferred_stacks", [])) or "flexible"}
- Free-text interests: "{profile.get("interests_text", "")}"
- Topics to avoid: {", ".join(profile.get("avoid", [])) or "none"}

Return JSON with this exact shape:
{{
  "ranked": [
    {{
      "id": "<short-slug>",
      "rank": 1,
      "title": "<short project title, in English>",
      "domains": ["<nlp|cv|rl|agents|rag|...>", ...],
      "why_fit": "<2-3 sentences in the target language explaining why this fits this student>",
      "est_weeks": <integer 4-20>,
      "difficulty_verdict": "<beginner|intermediate|advanced>",
      "research_hook": "<1 sentence describing the research area and one key idea>",
      "stack_hook": "<1 sentence listing the main tools/libraries>",
      "stars_estimate": <integer, realistic GitHub-stars count for a popular reference repo>
    }},
    ... exactly 5 items ...
  ]
}}"""


def blueprint_system_prompt(language: str) -> str:
    lang_name = "Arabic" if language == "ar" else "English"
    return f"""You are a senior graduation-project advisor. Produce a production-grade
project blueprint in {lang_name}. Keep technical terms (PyTorch, FastAPI, RAG, LLM,
embedding, etc.) in English. Be concrete — no filler.

Return strict JSON only."""


def blueprint_user_prompt(card: dict[str, Any], profile: dict[str, Any]) -> str:
    return f"""Student intent profile:
{profile}

Card being expanded:
- Title: {card.get("title")}
- Domains: {card.get("domains")}
- Research hook: {card.get("research_hook")}
- Stack hook: {card.get("stack_hook")}
- Estimated weeks: {card.get("est_weeks")}
- Difficulty: {card.get("difficulty_verdict")}

Return JSON with this exact shape:
{{
  "problem_statement": "<2-3 sentences>",
  "why_it_matters": "<2-3 sentences>",
  "in_scope": ["<bullet>", "<bullet>", ...],
  "out_of_scope": ["<bullet>", "<bullet>", ...],
  "suggested_architecture": "<markdown, 2-4 paragraphs, may include component names>",
  "tech_stack": ["<tool>", "<tool>", ...],
  "milestones_by_week": [
    {{"weeks": "1-2", "goals": ["<goal>", "<goal>"]}},
    {{"weeks": "3-4", "goals": ["<goal>"]}},
    ...
  ],
  "datasets": [
    {{"name": "<dataset name>", "url": "<real or typical URL>", "note": "<1 sentence>"}}
  ],
  "evaluation_metrics": ["<metric>", "<metric>"],
  "risks_and_mitigations": [
    {{"risk": "<risk>", "mitigation": "<mitigation>"}}
  ],
  "how_to_stand_out": ["<differentiating idea>", "<differentiating idea>", ...],
  "paper_refs": [
    {{"title": "<paper area or likely title>", "note": "<why relevant>"}}
  ],
  "repo_refs": [
    {{"name": "<org/repo>", "note": "<why relevant>"}}
  ]
}}"""
