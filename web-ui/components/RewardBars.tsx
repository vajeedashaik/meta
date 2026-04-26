"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type RewardSet = Record<string, number>;

const labels = [
  { key: "r1", name: "R1 Hook" },
  { key: "r2", name: "R2 Coherence" },
  { key: "r3", name: "R3 Cultural" },
  { key: "r4", name: "R4 Debate" },
  { key: "r5", name: "R5 Preserve" },
  { key: "process", name: "Process" }
];

export function RewardBars({ data, title }: { data: RewardSet; title: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {labels.map((item, i) => (
          <div key={item.key}>
            <div className="mb-1 flex justify-between text-xs text-slate-600">
              <span>{item.name}</span>
              <span>{Math.round((data[item.key] ?? 0) * 100)}%</span>
            </div>
            <div className="h-2 rounded-full bg-blue-100">
              <motion.div
                className="h-2 rounded-full bg-primary"
                initial={{ width: 0 }}
                animate={{ width: `${(data[item.key] ?? 0) * 100}%` }}
                transition={{ delay: i * 0.08, duration: 0.35 }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
