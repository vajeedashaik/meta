"use client";

import { AnimatePresence, motion } from "framer-motion";
import {
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { RewardDeltaBadge } from "@/components/RewardDeltaBadge";
import { RewardBars } from "@/components/RewardBars";
import { ScriptPanel } from "@/components/ScriptPanel";
import { ArbitratorReasoning } from "@/components/ArbitratorReasoning";

export interface EpisodeSnapshot {
  episode: number;
  script: string;
  reasoning: string[];
  rewards: {
    r1: number; r2: number; r3: number; r4: number; r5: number;
    r6: number; r7: number; r8: number; r9: number; r10: number;
    process: number; total: number;
  };
}

interface Props {
  episodes: EpisodeSnapshot[];
  current: number;
  historySeries: { episode: number; total: number }[];
}

export function LearningTimeline({ episodes, current, historySeries }: Props) {
  const snap = episodes[current];
  const prev = current > 0 ? episodes[current - 1] : null;
  const delta = prev ? snap.rewards.total - prev.rewards.total : 0;
  const improved = delta > 0.01;

  return (
    <div className="grid gap-5 lg:grid-cols-3">
      {/* LEFT — Script */}
      <div>
        <AnimatePresence mode="wait">
          <motion.div
            key={current}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.35, ease: "easeInOut" }}
          >
            <ScriptPanel
              script={snap.script}
              meta={{ platform: "Reels", region: "India", niche: "Creator productivity" }}
            />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* CENTER — Reasoning */}
      <div>
        <AnimatePresence mode="wait">
          <motion.div
            key={current}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.4, ease: "easeInOut" }}
            className={improved ? "ring-2 ring-emerald-500/50 rounded-2xl" : ""}
          >
            <ArbitratorReasoning before={snap.reasoning} after={snap.reasoning} />
          </motion.div>
        </AnimatePresence>
      </div>

      {/* RIGHT — Rewards */}
      <div className="space-y-3">
        <AnimatePresence mode="wait">
          <motion.div
            key={current}
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -10 }}
            transition={{ duration: 0.35, ease: "easeInOut" }}
          >
            <RewardBars data={snap.rewards} title="Reward Components (R1–R10)" />
          </motion.div>
        </AnimatePresence>

        <Card>
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-purple-400/70">Total Reward</p>
              <p className="text-2xl font-bold text-violet-400 tabular-nums">
                {snap.rewards.total.toFixed(3)}
              </p>
            </div>
            {prev && (
              <RewardDeltaBadge
                delta={(snap.rewards.total - prev.rewards.total) / prev.rewards.total}
              />
            )}
          </CardContent>
        </Card>

        {/* Progress chart */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-sm text-white">Reward Over Episodes</CardTitle>
          </CardHeader>
          <CardContent className="h-36 px-2 pb-3">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={historySeries.slice(0, current + 1)}>
                <XAxis dataKey="episode" tick={{ fontSize: 10, fill: "#a78bfa" }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#a78bfa" }} />
                <Tooltip contentStyle={{ background: "#120f1e", border: "1px solid #2e2255", borderRadius: "0.5rem", color: "#ede9f8" }} />
                <ReferenceLine y={historySeries[0]?.total} stroke="#4b3a7a" strokeDasharray="4 2" />
                <Line
                  type="monotone"
                  dataKey="total"
                  stroke="#8b5cf6"
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive
                />
              </LineChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
