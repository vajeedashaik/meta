"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { phases } from "@/lib/mock-data";

export function PhaseTimeline() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Build History — 12 Phases</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="relative pl-6">
          <div className="absolute left-2 top-0 h-full w-0.5 bg-blue-100" />
          <div className="space-y-3">
            {phases.map((phase, i) => (
              <motion.div
                key={phase.id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.04, duration: 0.3 }}
                className="relative"
              >
                <div className="absolute -left-4 top-2 h-2.5 w-2.5 rounded-full border-2 border-white bg-emerald-500 shadow-sm" />
                <div className="rounded-xl border border-slate-100 bg-white px-4 py-2.5 shadow-sm hover:border-blue-200 hover:shadow-soft transition-all">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="shrink-0 rounded-md bg-blue-50 px-1.5 py-0.5 text-xs font-bold text-blue-600">
                        P{phase.id}
                      </span>
                      <span className="truncate text-sm font-semibold text-slate-800">{phase.name}</span>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      {phase.tests > 0 && (
                        <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs text-emerald-700">
                          {phase.tests} tests
                        </span>
                      )}
                      <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-medium text-emerald-700">
                        ✓ PASS
                      </span>
                    </div>
                  </div>
                  <p className="mt-1 text-xs text-slate-500">{phase.summary}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
