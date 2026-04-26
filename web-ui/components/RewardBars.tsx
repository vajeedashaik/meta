"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type RewardSet = Record<string, number>;

const labels = [
  { key: "r1",      name: "R1 Hook Strength",      color: "bg-violet-500" },
  { key: "r2",      name: "R2 Coherence",           color: "bg-purple-500" },
  { key: "r3",      name: "R3 Cultural Alignment",  color: "bg-indigo-500" },
  { key: "r4",      name: "R4 Debate Resolution",   color: "bg-fuchsia-500" },
  { key: "r5",      name: "R5 Defender Preserve",   color: "bg-violet-400" },
  { key: "r6",      name: "R6 Safety",              color: "bg-rose-500"   },
  { key: "r7",      name: "R7 Originality",         color: "bg-orange-500" },
  { key: "r8",      name: "R8 Persona Fit",         color: "bg-amber-500"  },
  { key: "r9",      name: "R9 Platform Pacing",     color: "bg-emerald-500"},
  { key: "r10",     name: "R10 Retention Curve",    color: "bg-teal-500"   },
  { key: "process", name: "Process Quality",        color: "bg-sky-500"    },
];

export function RewardBars({ data, title }: { data: RewardSet; title: string }) {
  const total = data.total ?? 0;
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between text-white">
          <span>{title}</span>
          <span className="text-lg font-bold text-violet-400">{(total * 100).toFixed(0)}%</span>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2.5">
        {labels.map((item, i) => {
          const val = data[item.key] ?? 0;
          return (
            <div key={item.key}>
              <div className="mb-1 flex justify-between text-xs text-purple-300/70">
                <span className="font-medium">{item.name}</span>
                <span className="tabular-nums">{(val * 100).toFixed(0)}%</span>
              </div>
              <div className="h-1.5 rounded-full bg-purple-900/60">
                <motion.div
                  className={`h-1.5 rounded-full ${item.color}`}
                  initial={{ width: 0 }}
                  animate={{ width: `${val * 100}%` }}
                  transition={{ delay: i * 0.06, duration: 0.4, ease: "easeOut" }}
                />
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
