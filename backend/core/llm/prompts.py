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


def blueprint_user_prompt(
    card: dict[str, Any], profile: dict[str, Any]
) -> str:
    """Legacy entry point — delegates to the richer prompt so existing
    callers that pass only the card payload still work."""
    return blueprint_user_prompt_grounded(card, profile)


def blueprint_user_prompt_grounded(
    ctx: dict[str, Any], profile: dict[str, Any]
) -> str:
    """Full-grounded blueprint prompt.

    `ctx` carries the card + the *real* paper abstract + *real* README
    excerpt + AI-generated keywords + organization + published_year. The
    LLM is instructed to anchor every section in this material; any
    ambiguity should fall back to "details to refine with your supervisor"
    rather than confabulation.
    """
    paper_block = ""
    if ctx.get("abstract") or ctx.get("ai_summary"):
        paper_block = "\n".join(
            filter(
                None,
                [
                    "--- ACTUAL PAPER (ground truth) ---",
                    f"Title: {ctx.get('title')}",
                    f"arXiv URL: {ctx.get('arxiv_url') or 'n/a'}",
                    f"Published year: {ctx.get('published_year') or 'unknown'}",
                    f"Organization: {ctx.get('organization') or 'unknown'}",
                    "Abstract:",
                    ctx.get("abstract") or "",
                    "AI-generated summary:" if ctx.get("ai_summary") else "",
                    ctx.get("ai_summary") or "",
                    f"Keywords: {', '.join(ctx.get('ai_keywords') or []) or 'n/a'}",
                ],
            )
        ).strip()

    repo_block = ""
    readme = ctx.get("readme_excerpt") or ""
    if readme:
        repo_block = (
            "--- ACTUAL REPO README (ground truth, first ~4 KB) ---\n"
            f"GitHub URL: {ctx.get('github_url')}\n"
            f"Language: {ctx.get('code_language') or 'unknown'}\n"
            f"Stars: {ctx.get('stars') or 0}\n\n"
            f"{readme}"
        )

    blocks = [b for b in (paper_block, repo_block) if b]
    grounding = "\n\n".join(blocks) if blocks else (
        "--- No upstream abstract or README was retrievable — ground the "
        "blueprint in the research_hook below and flag assumptions explicitly. ---\n"
        f"Research hook: {ctx.get('research_hook') or ''}\n"
        f"Stack hook: {ctx.get('stack_hook') or ''}"
    )

    return f"""Student intent profile:
{profile}

Card being expanded:
- Title: {ctx.get("title")}
- Estimated weeks: {ctx.get("est_weeks")}
- Difficulty: {ctx.get("difficulty_verdict")}

{grounding}

Rules:
- Anchor every section in the grounding above. Quote or paraphrase the
  abstract/README where relevant. If a detail is not in the material,
  say "details to refine with your supervisor" — do NOT invent.
- Milestones must map to concrete tasks the student can execute against
  the real repo (train the model, fine-tune on dataset X, write a
  FastAPI wrapper, etc.). No generic filler.
- `paper_refs[0]` MUST be the actual paper URL given above when present.
- `repo_refs[0]` MUST be the actual GitHub URL given above when present.
- Keep technical terms (RAG, LLM, transformer, embedding, PyTorch,
  FastAPI, etc.) in English.

Return JSON with this exact shape:
{{
  "problem_statement": "<2-3 sentences>",
  "why_it_matters": "<2-3 sentences>",
  "in_scope": ["<bullet>", "<bullet>", ...],
  "out_of_scope": ["<bullet>", "<bullet>", ...],
  "suggested_architecture": "<markdown, 2-4 paragraphs, name the actual components from the README / paper>",
  "tech_stack": ["<tool>", "<tool>", ...],
  "milestones_by_week": [
    {{"weeks": "1-2", "goals": ["<concrete task grounded in the repo>"]}},
    ...
  ],
  "datasets": [
    {{"name": "<dataset from the paper/README>", "url": "<URL if known>", "note": "<1 sentence>"}}
  ],
  "evaluation_metrics": ["<metric the paper itself uses>", ...],
  "risks_and_mitigations": [
    {{"risk": "<risk>", "mitigation": "<mitigation>"}}
  ],
  "how_to_stand_out": ["<differentiation idea that goes beyond what the README already ships>", ...],
  "paper_refs": [
    {{"title": "<paper title from grounding>", "note": "<why relevant>"}}
  ],
  "repo_refs": [
    {{"name": "<owner/repo from grounding>", "note": "<why relevant>"}}
  ]
}}"""
