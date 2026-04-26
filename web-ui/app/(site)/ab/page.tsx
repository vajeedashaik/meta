"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ABBattle } from "@/components/ABBattle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const CHOSEN = {
  label: "Chosen Path — Trajectory B (Defender First)",
  delta: +0.12,
  description:
    "Preserving cultural voice first before applying targeted hook edits produced better retention and higher total reward.",
  outcome: "better" as const,
};

const ALTERNATE = {
  label: "Alternate Path — Trajectory A (Critic First)",
  delta: -0.08,
  description:
    "Aggressive hook rewrite first improved R1 but caused coherence drop (R2 −0.11), net reward lower by 0.08.",
  outcome: "worse" as const,
};

export default function ABPage() {
  const [rewound, setRewound] = useState(false);
  const [showLesson, setShowLesson] = useState(false);
  const current = rewound ? ALTERNATE : CHOSEN;

  function handleRewind() {
    setRewound((r) => !r);
    setShowLesson(false);
    setTimeout(() => setShowLesson(true), 600);
  }

  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold text-white">A/B Battle Mode</h1>

      {/* Counterfactual controls */}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="outline" onClick={handleRewind} className="gap-1.5">
          ↺ Rewind Decision
        </Button>
        <div className="flex rounded-lg border border-purple-700/40 overflow-hidden text-sm">
          <button
            onClick={() => { setRewound(false); setShowLesson(false); setTimeout(() => setShowLesson(true), 400); }}
            className={`px-3 py-1.5 transition-colors ${!rewound ? "bg-violet-600 text-white" : "text-purple-200 hover:bg-purple-800/40"}`}
          >
            Chosen Path
          </button>
          <button
            onClick={() => { setRewound(true); setShowLesson(false); setTimeout(() => setShowLesson(true), 400); }}
            className={`px-3 py-1.5 transition-colors ${rewound ? "bg-red-600 text-white" : "text-purple-200 hover:bg-purple-800/40"}`}
          >
            Alternate Path
          </button>
        </div>

        <AnimatePresence mode="wait">
          <motion.span
            key={current.label}
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.3 }}
            className={`ml-auto rounded-full px-3 py-1 text-xs font-semibold ${
              current.outcome === "better"
                ? "bg-emerald-900/50 text-emerald-300 border border-emerald-700/40"
                : "bg-red-900/50 text-red-300 border border-red-700/40"
            }`}
          >
            {current.delta > 0 ? "+" : ""}
            {current.delta.toFixed(2)} reward {current.outcome === "better" ? "improvement" : "penalty"}
          </motion.span>
        </AnimatePresence>
      </div>

      {/* Animated path description */}
      <AnimatePresence mode="wait">
        <motion.div
          key={current.label}
          initial={{ opacity: 0, x: rewound ? 20 : -20 }}
          animate={{ opacity: 1, x: 0 }}
          exit={{ opacity: 0, x: rewound ? -20 : 20 }}
          transition={{ duration: 0.4, ease: "easeInOut" }}
          className={`rounded-2xl border p-4 text-sm ${
            current.outcome === "better"
              ? "border-emerald-700/40 bg-emerald-900/30 text-emerald-200"
              : "border-red-700/40 bg-red-900/30 text-red-200"
          }`}
        >
          <p className="font-semibold">{current.label}</p>
          <p className="mt-1 text-xs opacity-80">{current.description}</p>
        </motion.div>
      </AnimatePresence>

      <ABBattle />

      {/* Lesson Learned card */}
      <AnimatePresence>
        {showLesson && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 12 }}
            transition={{ duration: 0.45, ease: "easeInOut" }}
          >
            <Card className="border-violet-600/30 bg-violet-950/40">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm text-violet-300">Lesson Learned</CardTitle>
              </CardHeader>
              <CardContent className="text-purple-200/80 text-sm">
                {rewound
                  ? "Starting with an aggressive hook rewrite before defending cultural anchors caused coherence to drop — proving that critic-first strategies can sacrifice overall quality for a single metric spike."
                  : "Preserving core script strength before hook rewrite improved retention and overall reward. Defender-first strategies produce more balanced, sustainable improvements across all 10 reward components."}
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
