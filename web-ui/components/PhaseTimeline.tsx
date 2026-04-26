"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { phases } from "@/lib/mock-data";

export function PhaseTimeline() {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-white">Build History — 12 Phases</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative pl-6">
          <div className="absolute left-2 top-0 h-full w-0.5 bg-purple-800/60" />
          <div className="space-y-3">
            {phases.map((phase, i) => (
              <motion.div
                key={phase.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04, duration: 0.3 }}
                className="relative"
              >
                <div className="absolute -left-4 top-2 h-2.5 w-2.5 rounded-full border-2 border-purple-900 bg-emerald-400 shadow-sm" />
                <div className="rounded-xl border border-purple-800/40 bg-purple-900/20 px-4 py-2.5 hover:border-violet-600/40 hover:bg-purple-900/30 transition-all">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="shrink-0 rounded-md bg-violet-900/60 px-1.5 py-0.5 text-xs font-bold text-violet-300">
                        P{phase.id}
                      </span>
                      <span className="truncate text-sm font-semibold text-purple-100">{phase.name}</span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {phase.tests > 0 && (
                        <span className="rounded-full bg-emerald-900/50 px-2 py-0.5 text-xs text-emerald-400">
                          {phase.tests} tests
                        </span>
                      )}
                      <span className="rounded-full bg-emerald-900/50 px-2 py-0.5 text-xs font-medium text-emerald-400">
                        ✓ PASS
                      </span>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-purple-300/70">{phase.summary}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
