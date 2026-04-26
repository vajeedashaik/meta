"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const nodes = [
  { id: "script",     label: "Raw Script",            icon: "📝", color: "bg-purple-900/40 border-purple-700/40",   dot: "bg-purple-400" },
  { id: "critic",     label: "Critic Agent",           icon: "⚔️",  color: "bg-red-900/40 border-red-700/40",         dot: "bg-red-400"    },
  { id: "defender",   label: "Defender Agent",         icon: "🛡️",  color: "bg-blue-900/40 border-blue-700/40",       dot: "bg-blue-400"   },
  { id: "arbitrator", label: "Arbitrator",             icon: "⚖️",  color: "bg-violet-900/40 border-violet-600/40",   dot: "bg-violet-400" },
  { id: "rewriter",   label: "Rewriter",               icon: "✍️",  color: "bg-emerald-900/40 border-emerald-700/40", dot: "bg-emerald-400"},
  { id: "rewards",    label: "Reward Engine (R1-R10)", icon: "🏆",  color: "bg-amber-900/40 border-amber-700/40",     dot: "bg-amber-400"  },
  { id: "retention",  label: "Retention Model",        icon: "📈",  color: "bg-teal-900/40 border-teal-700/40",       dot: "bg-teal-400"   },
  { id: "memory",     label: "Creator Memory",         icon: "🧠",  color: "bg-fuchsia-900/40 border-fuchsia-700/40", dot: "bg-fuchsia-400"},
];

const STEP_DESCRIPTIONS = [
  "Raw script ingested with platform, region, and niche metadata.",
  "CriticAgent generates high/medium severity claims against the script.",
  "DefenderAgent identifies what must be preserved: cultural anchors, creator voice.",
  "BaselineArbitrator resolves critic-defender conflict, selects best action.",
  "Rewriter applies targeted rewrite. Script diff generated for review.",
  "All 10 reward signals computed: R1-R10 + process quality score.",
  "RetentionCurvePredictor forecasts 60-second viewer drop-off (MAE 0.031).",
  "CreatorHistoryBuffer stores session patterns for longitudinal improvement.",
];

export function PipelineViz({ activeStep }: { activeStep?: number }) {
  const [step, setStep] = useState(activeStep ?? -1);
  const [auto, setAuto] = useState(false);

  useEffect(() => {
    if (activeStep !== undefined) setStep(activeStep);
  }, [activeStep]);

  useEffect(() => {
    if (!auto) return;
    const interval = setInterval(() => {
      setStep((prev) => (prev >= nodes.length - 1 ? 0 : prev + 1));
    }, 900);
    return () => clearInterval(interval);
  }, [auto]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base text-white">
          <span>Live Pipeline</span>
          <div className="flex gap-2">
            <button
              onClick={() => setAuto((a) => !a)}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${
                auto
                  ? "bg-violet-600 text-white"
                  : "bg-purple-900/50 text-purple-300 hover:bg-purple-800/60"
              }`}
            >
              {auto ? "⏸ Pause" : "▶ Animate"}
            </button>
            <button
              onClick={() => setStep(-1)}
              className="rounded-lg bg-purple-900/50 px-3 py-1 text-xs font-medium text-purple-300 hover:bg-purple-800/60"
            >
              Reset
            </button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap gap-2">
          {nodes.map((node, i) => (
            <div key={node.id} className="flex items-center gap-1.5">
              <motion.div
                animate={{
                  scale: step === i ? 1.08 : 1,
                  boxShadow: step === i ? "0 0 0 3px rgba(139,92,246,0.4)" : "none",
                }}
                transition={{ duration: 0.25 }}
                onClick={() => setStep(i)}
                className={`cursor-pointer rounded-xl border px-3 py-2 text-sm transition-all ${node.color} ${
                  step === i ? "ring-2 ring-violet-500/40" : ""
                } ${step > i ? "opacity-50" : ""}`}
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${step >= i ? node.dot : "bg-purple-800"}`} />
                  <span className="text-base">{node.icon}</span>
                  <span className="text-xs font-medium text-purple-100">{node.label}</span>
                  {step === i && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: [0, 1, 0] }}
                      transition={{ repeat: Infinity, duration: 1 }}
                      className="ml-1 h-1.5 w-1.5 rounded-full bg-violet-400"
                    />
                  )}
                </div>
              </motion.div>
              {i < nodes.length - 1 && (
                <motion.span
                  animate={{ color: step > i ? "#8b5cf6" : "#3b2d6e" }}
                  className="text-lg font-light"
                >
                  →
                </motion.span>
              )}
            </div>
          ))}
        </div>

        <AnimatePresence mode="wait">
          {step >= 0 && (
            <motion.div
              key={step}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -6 }}
              transition={{ duration: 0.22 }}
              className="mt-4 rounded-xl border border-violet-700/40 bg-violet-900/30 px-4 py-3 text-sm text-violet-200"
            >
              <span className="font-semibold">{nodes[step].icon} {nodes[step].label}</span>
              {" — "}
              {STEP_DESCRIPTIONS[step]}
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
