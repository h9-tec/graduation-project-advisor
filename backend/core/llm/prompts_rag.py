from __future__ import annotations

from typing import Any


def rerank_system_prompt(language: str) -> str:
    lang_name = "Arabic" if language == "ar" else "English"
    return f"""You are a graduation-project advisor for Egyptian CS / AI / SWE students.

You are given a student's intent profile and a list of REAL candidate projects
retrieved from our database (each with a stable id, a real title, and a real
github URL or paper link). Pick the 5 BEST-FIT candidates and rank them.

For each, write a 2-3 sentence "why this fits you" explanation in {lang_name}.
Keep technical terms in English (RAG, LLM, transformer, PyTorch, embedding).

CRITICAL: You MUST NOT invent project ids or titles. Every id in your output
must appear verbatim in the candidate list. If fewer than 5 candidates fit well,
return fewer — never pad with fabrications.

Return strict JSON only."""


def rerank_user_prompt(
    profile: dict[str, Any], candidates: list[dict[str, Any]]
) -> str:
    cand_lines = []
    for i, c in enumerate(candidates, 1):
        title = c.get("title", "")
        summary = (c.get("summary") or "")[:500]
        stars = c.get("stars", 0)
        url = c.get("github_url") or c.get("arxiv_url") or ""
        keywords = ", ".join((c.get("ai_keywords") or [])[:4])
        cand_lines.append(
            f"{i}. id={c['id']}\n"
            f"   title: {title}\n"
            f"   keywords: {keywords}\n"
            f"   stars: {stars} | code: {url or 'none'}\n"
            f"   summary: {summary}\n"
        )
    cand_block = "\n".join(cand_lines)

    return f"""Student intent profile:
- Language: {profile.get("language")}
- Domains of interest: {", ".join(profile.get("domains", []))}
- Skill level: {profile.get("skill_level")}
- Available months: {profile.get("months_available")}
- Team size: {profile.get("team_size")}
- Preferred stacks: {", ".join(profile.get("preferred_stacks", [])) or "flexible"}
- Free-text interests: "{profile.get("interests_text", "")}"
- Topics to avoid: {", ".join(profile.get("avoid", [])) or "none"}

Candidate projects (real database rows — only these ids are valid):

{cand_block}

Return JSON with this exact shape:
{{
  "ranked": [
    {{
      "id": "<one of the candidate ids above, verbatim>",
      "rank": 1,
      "why_fit": "<2-3 sentences in the target language>",
      "est_weeks": <integer 4-20>,
      "difficulty_verdict": "<beginner|intermediate|advanced>"
    }},
    ... up to 5 items ...
  ]
}}"""
