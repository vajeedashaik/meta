"use client";

import { useState } from "react";
import { Trophy } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Trajectory = {
  label: string;
  strategy: string;
  rewards: number[];
  rewardBreakdown: Array<{ name: string; a: number; b: number }>;
  tag: string;
};

const trajectoryA: Trajectory = {
  label: "Trajectory A — Critic First",
  strategy: "Prioritizes highest-severity critique immediately. Faster hook lift but coherence occasionally suffers.",
  tag: "critic-first",
  rewards: [0.52, 0.61, 0.68, 0.72],
  rewardBreakdown: [
    { name: "R1 Hook",       a: 0.71, b: 0.65 },
    { name: "R2 Coherence",  a: 0.63, b: 0.74 },
    { name: "R3 Cultural",   a: 0.67, b: 0.82 },
    { name: "R5 Preserve",   a: 0.58, b: 0.79 },
    { name: "R10 Retention", a: 0.66, b: 0.85 }
  ]
};

const trajectoryB: Trajectory = {
  label: "Trajectory B — Defender First",
  strategy: "Preserves voice and cultural anchors first, then applies narrower targeted edits for better retention.",
  tag: "defender-first",
  rewards: [0.51, 0.64, 0.73, 0.80],
  rewardBreakdown: trajectoryA.rewardBreakdown
};

const stepLabels = ["Step 1", "Step 2", "Step 3", "Final"];
const stepDescriptions = [
  "Initial rewrite applied",
  "Cultural anchor check done",
  "CTA repositioned",
  "Final scoring complete"
];

export function ABBattle() {
  const [step, setStep] = useState(0);
  const aScore = trajectoryA.rewards[step];
  const bScore = trajectoryB.rewards[step];
  const leader = bScore >= aScore ? "B" : "A";
  const done = step >= 3;

  return (
    <div className="space-y-5">
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-2">
        <Button onClick={() => setStep((p) => Math.min(p + 1, 3))} disabled={done}>
          Advance Step →
        </Button>
        <Button variant="outline" onClick={() => setStep(0)}>
          Reset Battle
        </Button>
        <span className="ml-2 text-xs text-slate-500">
          {stepLabels[step]} — {stepDescriptions[step]}
        </span>
      </div>

      {/* Progress bar */}
      <div className="flex gap-1.5">
        {stepLabels.map((label, i) => (
          <div key={label} className="flex-1">
            <div
              className={`h-1.5 rounded-full transition-colors duration-500 ${
                i <= step ? "bg-primary" : "bg-slate-100"
              }`}
            />
            <p className="mt-1 text-center text-xs text-slate-400">{label}</p>
          </div>
        ))}
      </div>

      {/* Battle cards */}
      <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr]">
        {/* A */}
        <motion.div animate={{ scale: leader === "A" ? 1.01 : 1 }} transition={{ duration: 0.2 }}>
          <Card className={`h-full transition-all ${leader === "A" ? "border-primary shadow-soft" : "border-slate-200"}`}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between text-base">
                <span>⚔️ {trajectoryA.label}</span>
                {leader === "A" && !done && <span className="text-xs text-primary font-normal">Leading</span>}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-slate-500">{trajectoryA.strategy}</p>
              <AnimatePresence mode="wait">
                <motion.p
                  key={aScore}
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-3xl font-bold text-slate-800 tabular-nums"
                >
                  {aScore.toFixed(2)}
                </motion.p>
              </AnimatePresence>
              <div className="h-2 rounded-full bg-slate-100">
                <motion.div
                  className="h-2 rounded-full bg-slate-400"
                  animate={{ width: `${aScore * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
            </CardContent>
          </Card>
        </motion.div>

        <div className="flex items-center justify-center text-2xl font-bold text-slate-300">VS</div>

        {/* B */}
        <motion.div animate={{ scale: leader === "B" ? 1.01 : 1 }} transition={{ duration: 0.2 }}>
          <Card className={`h-full transition-all ${leader === "B" ? "border-primary shadow-soft" : "border-slate-200"}`}>
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between text-base">
                <span>🛡️ {trajectoryB.label}</span>
                {leader === "B" && !done && <span className="text-xs text-primary font-normal">Leading</span>}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-slate-500">{trajectoryB.strategy}</p>
              <AnimatePresence mode="wait">
                <motion.p
                  key={bScore}
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="text-3xl font-bold text-primary tabular-nums"
                >
                  {bScore.toFixed(2)}
                </motion.p>
              </AnimatePresence>
              <div className="h-2 rounded-full bg-blue-100">
                <motion.div
                  className="h-2 rounded-full bg-primary"
                  animate={{ width: `${bScore * 100}%` }}
                  transition={{ duration: 0.5 }}
                />
              </div>
              <AnimatePresence>
                {done && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="inline-flex items-center gap-2 rounded-xl bg-blue-50 px-3 py-2 text-sm font-semibold text-primary"
                  >
                    <Trophy className="h-4 w-4" /> Winner — Trajectory B (+0.08 reward)
                  </motion.div>
                )}
              </AnimatePresence>
            </CardContent>
          </Card>
        </motion.div>
      </div>

      {/* Reward breakdown */}
      {done && (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Final Reward Breakdown</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {trajectoryA.rewardBreakdown.map((row) => (
                <div key={row.name}>
                  <div className="mb-1 flex justify-between text-xs text-slate-500">
                    <span className="font-medium">{row.name}</span>
                    <span>A: {(row.a * 100).toFixed(0)}% &nbsp; B: {(row.b * 100).toFixed(0)}%</span>
                  </div>
                  <div className="flex gap-1">
                    <div className="h-1.5 flex-1 rounded-full bg-slate-100">
                      <motion.div
                        className="h-1.5 rounded-full bg-slate-400"
                        initial={{ width: 0 }}
                        animate={{ width: `${row.a * 100}%` }}
                        transition={{ duration: 0.4 }}
                      />
                    </div>
                    <div className="h-1.5 flex-1 rounded-full bg-blue-100">
                      <motion.div
                        className="h-1.5 rounded-full bg-primary"
                        initial={{ width: 0 }}
                        animate={{ width: `${row.b * 100}%` }}
                        transition={{ duration: 0.4, delay: 0.05 }}
                      />
                    </div>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        </motion.div>
      )}

      <div className={`rounded-xl px-4 py-2.5 text-sm font-medium ${done ? "bg-primary text-white" : "bg-blue-50 text-blue-700"}`}>
        {done
          ? "✓ Trajectory B wins — Defender-first preserves cultural anchors and achieves better retention (+0.08 reward)"
          : `Current leader: Trajectory ${leader} (${Math.abs(bScore - aScore).toFixed(2)} margin)`}
      </div>
    </div>
  );
}
