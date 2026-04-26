"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PhaseTimeline } from "@/components/PhaseTimeline";
import { PipelineViz } from "@/components/PipelineViz";
import { LearningGraph } from "@/components/LearningGraph";
import { RetentionChart } from "@/components/RetentionChart";
import { RewardBars } from "@/components/RewardBars";
import { systemStats, learningSeries, retentionSeries, rewardAfter } from "@/lib/mock-data";

const statCards = [
  { label: "Phases Complete",   value: `${systemStats.totalPhases}/12`, sub: "All gates passing",          color: "text-emerald-600" },
  { label: "Total Tests",       value: systemStats.totalTests,          sub: "All passing",                 color: "text-blue-600"    },
  { label: "Reward Signals",    value: `R1–R10`,                        sub: "+ process quality",           color: "text-violet-600"  },
  { label: "Peak Total Reward", value: `${(systemStats.peakReward * 100).toFixed(0)}%`, sub: "After training ep.100", color: "text-primary" },
  { label: "Retention Lift",    value: `+${systemStats.retentionLift}%`, sub: "viewer drop-off improved",   color: "text-teal-600"    },
  { label: "Success Rate",      value: `${systemStats.successRate}%`,   sub: "at episode 100",              color: "text-emerald-600" },
  { label: "Retention MAE",     value: systemStats.retentionModelMAE,   sub: "R10 model accuracy",          color: "text-amber-600"   },
  { label: "A/B Win Margin",    value: `+${systemStats.abWinnerMargin}`, sub: "Trajectory B vs A",          color: "text-indigo-600"  }
];

export default function DashboardPage() {
  const [pipelineStep, setPipelineStep] = useState(-1);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">System Dashboard</h1>
        <p className="mt-1 text-sm text-slate-500">
          Viral Script Debugging Engine — 12 phases, 181 tests, 10 reward signals
        </p>
      </div>

      {/* Stats grid */}
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-4">
        {statCards.map((s, i) => (
          <motion.div
            key={s.label}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.05, duration: 0.3 }}
          >
            <Card className="h-full">
              <CardContent className="p-4">
                <p className="text-xs font-medium uppercase tracking-wide text-slate-400">{s.label}</p>
                <p className={`mt-1 text-2xl font-bold tabular-nums ${s.color}`}>{s.value}</p>
                <p className="mt-0.5 text-xs text-slate-500">{s.sub}</p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Pipeline */}
      <PipelineViz activeStep={pipelineStep} />

      {/* Charts row */}
      <div className="grid gap-5 lg:grid-cols-2">
        <RetentionChart data={retentionSeries} />
        <LearningGraph data={learningSeries} />
      </div>

      {/* Reward breakdown + Phase timeline */}
      <div className="grid gap-5 lg:grid-cols-2">
        <RewardBars data={rewardAfter} title="Current Reward Profile (Trained)" />
        <PhaseTimeline />
      </div>

      {/* Architecture summary */}
      <Card>
        <CardHeader>
          <CardTitle>Architecture Overview</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2 md:grid-cols-3 text-sm">
            {[
              { cat: "Agents",       items: ["BaselineArbitrator", "CriticAgent", "DefenderAgent", "RewriterAgent"] },
              { cat: "Rewards",      items: ["R1 Hook", "R2 Coherence", "R3 Cultural", "R4 Debate", "R5 Preserve", "R6 Safety", "R7 Originality", "R8 Persona", "R9 Platform", "R10 Retention"] },
              { cat: "Environment",  items: ["ViralScriptEnv", "ABScriptEnv", "EpisodeState", "DifficultyTracker"] },
              { cat: "Memory",       items: ["CreatorHistoryBuffer", "MemoryCompressor", "HistoryStore"] },
              { cat: "Retention",    items: ["RetentionCurveSimulator", "CurvePredictor (Ridge, MAE 0.031)", "150-sample dataset"] },
              { cat: "Infrastructure", items: ["FastAPI app.py", "HuggingFace Spaces", "Next.js Web UI", "GRPO pipeline"] }
            ].map((block) => (
              <div key={block.cat} className="rounded-xl border border-slate-100 p-3">
                <p className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">{block.cat}</p>
                <ul className="space-y-1">
                  {block.items.map((item) => (
                    <li key={item} className="flex items-center gap-1.5 text-xs text-slate-600">
                      <span className="h-1 w-1 rounded-full bg-primary/60" />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
