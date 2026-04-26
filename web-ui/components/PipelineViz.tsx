"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const nodes = [
  { id: "script",    label: "Raw Script",          icon: "📝", color: "bg-slate-100 border-slate-300",    dot: "bg-slate-400" },
  { id: "critic",    label: "Critic Agent",         icon: "⚔️",  color: "bg-red-50 border-red-200",         dot: "bg-red-400" },
  { id: "defender",  label: "Defender Agent",       icon: "🛡️",  color: "bg-blue-50 border-blue-200",       dot: "bg-blue-400" },
  { id: "arbitrator",label: "Arbitrator",           icon: "⚖️",  color: "bg-violet-50 border-violet-200",   dot: "bg-violet-400" },
  { id: "rewriter",  label: "Rewriter",             icon: "✍️",  color: "bg-emerald-50 border-emerald-200", dot: "bg-emerald-400" },
  { id: "rewards",   label: "Reward Engine (R1-R10)", icon: "🏆", color: "bg-amber-50 border-amber-200",   dot: "bg-amber-400" },
  { id: "retention", label: "Retention Model",      icon: "📈", color: "bg-teal-50 border-teal-200",       dot: "bg-teal-400" },
  { id: "memory",    label: "Creator Memory",       icon: "🧠", color: "bg-purple-50 border-purple-200",   dot: "bg-purple-400" }
];

const flowSteps = [0, 1, 2, 3, 4, 5, 6, 7];

export function PipelineViz({ activeStep }: { activeStep?: number }) {
  const [step, setStep] = useState(activeStep ?? -1);
  const [auto, setAuto] = useState(false);

  useEffect(() => {
    if (activeStep !== undefined) setStep(activeStep);
  }, [activeStep]);

  useEffect(() => {
    if (!auto) return;
    const interval = setInterval(() => {
      setStep((prev) => (prev >= flowSteps.length - 1 ? 0 : prev + 1));
    }, 900);
    return () => clearInterval(interval);
  }, [auto]);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-base">
          <span>Live Pipeline</span>
          <div className="flex gap-2">
            <button
              onClick={() => { setAuto((a) => !a); }}
              className={`rounded-lg px-3 py-1 text-xs font-medium transition-colors ${
                auto ? "bg-primary text-white" : "bg-slate-100 text-slate-600 hover:bg-blue-50"
              }`}
            >
              {auto ? "⏸ Pause" : "▶ Animate"}
            </button>
            <button
              onClick={() => setStep(-1)}
              className="rounded-lg bg-slate-100 px-3 py-1 text-xs font-medium text-slate-600 hover:bg-slate-200"
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
                  boxShadow: step === i ? "0 0 0 3px rgba(24,119,242,0.35)" : "none"
                }}
                transition={{ duration: 0.25 }}
                onClick={() => setStep(i)}
                className={`cursor-pointer rounded-xl border px-3 py-2 text-sm transition-all ${node.color} ${
                  step === i ? "ring-2 ring-primary/40" : ""
                } ${step > i ? "opacity-60" : ""}`}
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2 w-2 rounded-full ${step >= i ? node.dot : "bg-slate-200"}`} />
                  <span className="text-base">{node.icon}</span>
                  <span className="text-xs font-medium text-slate-700">{node.label}</span>
                  {step === i && (
                    <motion.span
                      initial={{ opacity: 0 }}
                      animate={{ opacity: [0, 1, 0] }}
                      transition={{ repeat: Infinity, duration: 1 }}
                      className="ml-1 h-1.5 w-1.5 rounded-full bg-primary"
                    />
                  )}
                </div>
              </motion.div>
              {i < nodes.length - 1 && (
                <motion.span
                  animate={{ color: step > i ? "#1877F2" : "#cbd5e1" }}
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
              className="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 px-4 py-3 text-sm text-blue-800"
            >
              <span className="font-semibold">{nodes[step].icon} {nodes[step].label}</span>
              {" — "}
              {[
                "Raw script ingested with platform, region, and niche metadata.",
                "CriticAgent generates high/medium severity claims against the script.",
                "DefenderAgent identifies what must be preserved: cultural anchors, creator voice.",
                "BaselineArbitrator resolves critic-defender conflict, selects best action.",
                "Rewriter applies targeted rewrite. Script diff generated for review.",
                "All 10 reward signals computed: R1-R10 + process quality score.",
                "RetentionCurvePredictor forecasts 60-second viewer drop-off (MAE 0.031).",
                "CreatorHistoryBuffer stores session patterns for longitudinal improvement."
              ][step]}
            </motion.div>
          )}
        </AnimatePresence>
      </CardContent>
    </Card>
  );
}
