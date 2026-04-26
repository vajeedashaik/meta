export type ApiRound = {
  critic_claims?: Array<{
    claim_id?: string;
    claim_text?: string;
    severity?: "high" | "medium" | string;
    critique_class?: string;
  }>;
  defender_response?: {
    core_strength?: string;
    flagged_critic_claims?: string[];
    regional_voice_elements?: string[];
  };
  arbitrator_action?: {
    action_type?: string;
    instruction?: string;
    critique_claim_id?: string;
    reasoning?: string;
  };
  rewrite_diff?: string;
  reward_components?: Record<string, number>;
};

export type ApiObservation = {
  current_script?: string;
  original_script?: string;
  region?: string;
  platform?: string;
  niche?: string;
  step_num?: number;
  max_steps?: number;
  debate_history?: ApiRound[];
  reward_components?: Record<string, number>;
  difficulty_level?: string;
  episode_id?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_ENGINE_API_BASE ?? "http://localhost:7860";

async function parseJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${res.status}: ${text}`);
  }
  return (await res.json()) as T;
}

export async function healthCheck() {
  const res = await fetch(`${API_BASE}/health`, { cache: "no-store" });
  return parseJson<{ status: string }>(res);
}

export async function resetEpisode(sessionId: string, difficulty = "easy") {
  const res = await fetch(`${API_BASE}/reset`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, difficulty })
  });
  return parseJson<{ observation: ApiObservation }>(res);
}

export async function stepEpisode(
  sessionId: string,
  action: {
    action_type: "hook_rewrite" | "section_reorder" | "cultural_ref_sub" | "cta_placement";
    target_section: "hook" | "body" | "cta" | "full";
    instruction: string;
    critique_claim_id: string;
    reasoning: string;
  }
) {
  const res = await fetch(`${API_BASE}/step`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ session_id: sessionId, action })
  });
  return parseJson<{ observation: ApiObservation; reward: number; terminated: boolean; truncated: boolean }>(res);
}

export async function fetchState(sessionId: string) {
  const res = await fetch(`${API_BASE}/state/${sessionId}`, { cache: "no-store" });
  return parseJson<ApiObservation>(res);
}
