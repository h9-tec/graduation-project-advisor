export type Domain =
  | "nlp"
  | "cv"
  | "rl"
  | "mlops"
  | "agents"
  | "rag"
  | "robotics"
  | "audio"
  | "timeseries"
  | "security"
  | "iot"
  | "web"
  | "mobile"
  | "data_engineering";

export type SkillLevel = "beginner" | "intermediate" | "advanced";
export type Language = "en" | "ar";

export type IntentProfile = {
  language: Language;
  domains: Domain[];
  skill_level: SkillLevel;
  months_available: number;
  team_size: number;
  preferred_stacks: string[];
  interests_text: string;
  requires_code_reference: boolean;
  avoid: string[];
};

export type LeanCard = {
  id: string;
  rank: number;
  title: string;
  domains: string[];
  why_fit: string;
  est_weeks: number;
  difficulty_verdict: string;
  research_hook: string;
  stack_hook: string;
  stars_estimate: number;
  arxiv_url?: string | null;
  github_url?: string | null;
};

export type Milestone = { weeks: string; goals: string[] };
export type DatasetRef = { name: string; url?: string | null; note: string };
export type RiskItem = { risk: string; mitigation: string };
export type Ref = { name?: string | null; title?: string | null; note: string };

export type Blueprint = {
  problem_statement: string;
  why_it_matters: string;
  in_scope: string[];
  out_of_scope: string[];
  suggested_architecture: string;
  tech_stack: string[];
  milestones_by_week: Milestone[];
  datasets: DatasetRef[];
  evaluation_metrics: string[];
  risks_and_mitigations: RiskItem[];
  how_to_stand_out: string[];
  paper_refs: Ref[];
  repo_refs: Ref[];
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8010";

async function postJSON<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`POST ${path} failed: ${res.status} ${text}`);
  }
  return (await res.json()) as T;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(`GET ${path} failed: ${res.status} ${text}`);
  }
  return (await res.json()) as T;
}

export async function submitRecommendations(
  profile: IntentProfile,
): Promise<{ session_id: string; cards: LeanCard[] }> {
  return postJSON("/api/v1/recommendations", profile);
}

export async function fetchCards(sessionId: string): Promise<LeanCard[]> {
  return getJSON(`/api/v1/sessions/${sessionId}/cards`);
}

export async function expandCard(
  sessionId: string,
  cardId: string,
): Promise<{ card_id: string; blueprint: Blueprint }> {
  return postJSON(
    `/api/v1/sessions/${sessionId}/cards/${cardId}/expand`,
    {},
  );
}

export type RefineResponse = {
  session_id: string;
  cards: LeanCard[];
  assistant_msg: string;
  refinement_count: number;
  history_depth: number;
};

export async function refineSession(
  sessionId: string,
  message: string,
): Promise<RefineResponse> {
  return postJSON(`/api/v1/sessions/${sessionId}/refine`, { message });
}

export async function undoRefinement(
  sessionId: string,
): Promise<RefineResponse> {
  return postJSON(`/api/v1/sessions/${sessionId}/refine/undo`, {});
}

export const MAX_REFINEMENTS_PER_SESSION = 15;

export type Reaction = "up" | "down";

export async function postFeedback(
  sessionId: string,
  cardId: string,
  reaction: Reaction,
): Promise<{ feedback_id: string }> {
  return postJSON("/api/v1/feedback", {
    session_id: sessionId,
    card_id: cardId,
    reaction,
  });
}

export async function listSaved(sessionId: string): Promise<{ cards: LeanCard[] }> {
  return getJSON(`/api/v1/sessions/${sessionId}/saved`);
}

export async function saveCard(
  sessionId: string,
  cardId: string,
): Promise<{ cards: LeanCard[] }> {
  return postJSON(`/api/v1/sessions/${sessionId}/saved`, { card_id: cardId });
}

export async function unsaveCard(
  sessionId: string,
  cardId: string,
): Promise<{ cards: LeanCard[] }> {
  const res = await fetch(
    `${API_BASE}/api/v1/sessions/${sessionId}/saved/${cardId}`,
    { method: "DELETE", cache: "no-store" },
  );
  if (!res.ok) {
    throw new Error(`DELETE /saved/${cardId} failed: ${res.status}`);
  }
  return (await res.json()) as { cards: LeanCard[] };
}
