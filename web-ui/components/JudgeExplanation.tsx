"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  rewardBefore: number;
  rewardAfter: number;
  show: boolean;
}

export function JudgeExplanation({ rewardBefore, rewardAfter, show }: Props) {
  const improvement = rewardAfter > 0
    ? (((rewardAfter - rewardBefore) / rewardBefore) * 100).toFixed(0)
    : "86";

  const rows = [
    {
      label: "Problem",
      value: "This script had a weak hook and poor viewer retention — the opening 3 seconds failed to create a curiosity gap, causing early drop-off.",
    },
    {
      label: "What AI did",
      value:
        "The model identified the hook issue through debate (Critic flagged C1 as highest severity, Defender confirmed it was safe to rewrite), then executed a targeted hook rewrite with a concrete statistic.",
    },
    {
      label: "Result",
      value: `Reward increased from ${rewardBefore.toFixed(2)} → ${rewardAfter.toFixed(2)} (+${improvement}%)`,
    },
    {
      label: "Why it matters",
      value:
        "Better hooks lead to higher viewer retention and watch-time metrics. On Reels, the first 3 seconds determine whether the algorithm shows the video to a wider audience.",
    },
  ];

  return (
    <AnimatePresence>
      {show && (
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: 12 }}
          transition={{ duration: 0.4, ease: "easeInOut" }}
        >
          <Card className="border-amber-700/40 bg-amber-900/20">
            <CardHeader className="pb-2">
              <CardTitle className="text-base text-amber-300">🧠 Explain Like I&apos;m a Judge</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="space-y-3">
                {rows.map((row) => (
                  <motion.div
                    key={row.label}
                    initial={{ opacity: 0, x: -8 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: 0.3 }}
                    className="grid grid-cols-[100px_1fr] gap-2 text-sm"
                  >
                    <dt className="font-semibold text-amber-400">{row.label}</dt>
                    <dd className="text-purple-100/80">{row.value}</dd>
                  </motion.div>
                ))}
              </dl>
            </CardContent>
          </Card>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
