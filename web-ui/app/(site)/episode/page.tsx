"use client";

import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArbitratorReasoning } from "@/components/ArbitratorReasoning";
import { CriticPanel } from "@/components/CriticPanel";
import { DefenderPanel } from "@/components/DefenderPanel";
import { RewardBars } from "@/components/RewardBars";
import { ScriptPanel } from "@/components/ScriptPanel";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ApiObservation, fetchState, healthCheck, resetEpisode, stepEpisode } from "@/lib/api";
import { JudgeExplanation } from "@/components/JudgeExplanation";
import {
  criticClaims,
  defender,
  diffLines,
  metadata,
  rawScript,
  reasoning,
  rewardAfter,
  rewardBefore
} from "@/lib/mock-data";

function mapRewards(raw?: Record<string, number>) {
  if (!raw) return rewardBefore;
  return {
    r1: raw.r1_hook_strength ?? rewardBefore.r1,
    r2: raw.r2_coherence ?? rewardBefore.r2,
    r3: raw.r3_cultural_alignment ?? rewardBefore.r3,
    r4: raw.r4_debate_resolution ?? rewardBefore.r4,
    r5: raw.r5_defender_preservation ?? rewardBefore.r5,
    process: raw.process_reward ?? rewardBefore.process,
    total: raw.total ?? rewardBefore.total
  };
}

function parseDiff(diff?: string) {
  if (!diff) return diffLines;
  const rows = diff
    .split("\n")
    .filter((line) => line.startsWith("+") || line.startsWith("-"))
    .slice(0, 8)
    .map((line) => ({
      type: line.startsWith("+") ? ("added" as const) : ("removed" as const),
      text: line.slice(1).trim()
    }));
  return rows.length > 0 ? rows : diffLines;
}

export default function EpisodePage() {
  const [trained, setTrained] = useState(true);
  const [judgeMode, setJudgeMode] = useState(false);
  const [sessionId] = useState(() => `ui-${Date.now()}`);
  const [observation, setObservation] = useState<ApiObservation | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [status, setStatus] = useState<"checking" | "online" | "offline">("checking");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    healthCheck()
      .then(() => setStatus("online"))
      .catch(() => setStatus("offline"));
  }, []);

  const lastRound = observation?.debate_history?.[observation.debate_history.length - 1];
  const liveRewards = mapRewards(observation?.reward_components);
  const rewards = trained ? liveRewards : rewardBefore;
  const improvement = useMemo(() => ((rewardAfter.total - rewardBefore.total) / rewardBefore.total) * 100, []);

  const claims: { id: string; text: string; severity: "high" | "medium" }[] =
    lastRound?.critic_claims?.map((c, i) => ({
      id: c.claim_id ?? `C${i + 1}`,
      text: c.claim_text ?? "Critique generated.",
      severity: c.severity === "high" ? "high" : "medium"
    })) ?? criticClaims;

  const defenderData = {
    coreStrength: lastRound?.defender_response?.core_strength ?? defender.coreStrength,
    warnings:
      lastRound?.defender_response?.regional_voice_elements?.map((item) => `Preserve: ${item}`) ??
      defender.warnings
  };

  const actionReasoning = lastRound?.arbitrator_action?.reasoning;
  const liveReasoning = actionReasoning
    ? [
        `Priority assessment: ${actionReasoning}`,
        `Conflict check: defended claims were reviewed.`,
        `Defender consideration: regional anchors retained.`,
        `Action: ${lastRound?.arbitrator_action?.action_type ?? "hook_rewrite"}.`
      ]
    : reasoning.after;

  async function handleReset() {
    setError(null);
    setIsRunning(true);
    try {
      const res = await resetEpisode(sessionId, "easy");
      setObservation(res.observation);
      setStatus("online");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to reset episode.");
      setStatus("offline");
    } finally {
      setIsRunning(false);
    }
  }

  async function runSingleStep() {
    setError(null);
    setIsRunning(true);
    try {
      if (!observation) {
        const res = await resetEpisode(sessionId, "easy");
        setObservation(res.observation);
      }
      const action = trained
        ? {
            action_type: "hook_rewrite" as const,
            target_section: "hook" as const,
            instruction: "Rewrite opening with specific reveal while preserving regional tone.",
            critique_claim_id: "C1",
            reasoning: "Target highest-severity claim while preserving defender constraints."
          }
        : {
            action_type: "hook_rewrite" as const,
            target_section: "hook" as const,
            instruction: "Rewrite intro quickly for stronger attention.",
            critique_claim_id: "C1",
            reasoning: "General improvement without explicit trade-off handling."
          };
      await stepEpisode(sessionId, action);
      const nextState = await fetchState(sessionId);
      setObservation(nextState);
      setStatus("online");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to run step.");
      setStatus("offline");
    } finally {
      setIsRunning(false);
    }
  }

  async function playEpisode() {
    await handleReset();
    for (let i = 0; i < 3; i += 1) {
      await runSingleStep();
    }
  }

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center gap-2">
        <Button variant={trained ? "outline" : "default"} onClick={() => setTrained(false)}>
          Before Training
        </Button>
        <Button variant={trained ? "default" : "outline"} onClick={() => setTrained(true)}>
          After Training
        </Button>
        <Button
          variant={judgeMode ? "default" : "outline"}
          onClick={() => setJudgeMode((j) => !j)}
          className="ml-2"
        >
          🧠 Judge Mode
        </Button>
        <Button className="ml-auto" onClick={playEpisode} disabled={isRunning || status === "offline"}>
          {isRunning ? "Running..." : "Play Episode"}
        </Button>
        <Button variant="outline" onClick={runSingleStep} disabled={isRunning || status === "offline"}>
          Next Step
        </Button>
        <Button variant="outline" onClick={handleReset} disabled={isRunning || status === "offline"}>
          Reset
        </Button>
      </div>
      <p className="text-xs text-purple-300/60">
        Engine status:{" "}
        <span className={status === "online" ? "text-emerald-400" : status === "offline" ? "text-red-400" : "text-purple-300"}>
          {status}
        </span>
        {observation?.step_num !== undefined ? ` • Step ${observation.step_num}/${observation.max_steps ?? 5}` : ""}
      </p>
      {error ? (
        <p className="rounded-lg bg-red-900/40 border border-red-700/40 px-3 py-2 text-sm text-red-300">{error}</p>
      ) : null}

      <ScriptPanel
        script={observation?.original_script ?? rawScript}
        meta={{
          platform: observation?.platform ?? metadata.platform,
          region: observation?.region ?? metadata.region,
          niche: observation?.niche ?? metadata.niche
        }}
      />

      <JudgeExplanation
        rewardBefore={rewardBefore.total}
        rewardAfter={trained ? rewards.total : rewardBefore.total}
        show={judgeMode}
      />

      <CriticPanel claims={claims} />
      <DefenderPanel coreStrength={defenderData.coreStrength} warnings={defenderData.warnings} />
      <ArbitratorReasoning before={reasoning.before} after={trained ? liveReasoning : reasoning.before} />

      <Card>
        <CardHeader>
          <CardTitle className="text-white">Act 5 — Rewrite + Impact</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2 rounded-xl border border-purple-800/40 bg-purple-900/20 p-4">
            <h4 className="text-sm font-semibold text-purple-100">Script Diff</h4>
            {parseDiff(lastRound?.rewrite_diff).map((line, i) => (
              <motion.p
                key={i}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.12 }}
                className={`rounded-lg px-2 py-1 text-sm ${
                  line.type === "added"
                    ? "bg-emerald-900/40 text-emerald-300"
                    : "bg-red-900/40 text-red-300"
                }`}
              >
                {line.type === "added" ? "+" : "-"} {line.text}
              </motion.p>
            ))}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <RewardBars data={rewards} title="Reward Components (R1-R5 + process)" />
            <Card>
              <CardHeader>
                <CardTitle className="text-white">Impact Metric</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-purple-300/70">Total reward before to after</p>
                <p className="mt-2 text-3xl font-bold text-violet-400">
                  {rewardBefore.total.toFixed(2)} {"->"} {(trained ? rewards.total : rewardBefore.total).toFixed(2)}
                </p>
                <p className="mt-1 text-sm text-emerald-400">+{improvement.toFixed(0)}% improvement</p>
              </CardContent>
            </Card>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
