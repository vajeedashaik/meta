"use client";

import { AnimatePresence, motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function ReasoningColumn({ title, lines, highlight }: { title: string; lines: string[]; highlight?: boolean }) {
  return (
    <div className={`rounded-xl border p-4 ${highlight ? "border-blue-200 bg-blue-50/60" : "border-slate-200 bg-white"}`}>
      <h4 className="mb-3 text-sm font-semibold text-slate-800">{title}</h4>
      <div className="space-y-2">
        <AnimatePresence mode="wait">
          {lines.map((line, i) => (
            <motion.p
              key={`${title}-${i}`}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.15, duration: 0.25 }}
              className="text-sm text-slate-600"
            >
              {line}
            </motion.p>
          ))}
        </AnimatePresence>
      </div>
    </div>
  );
}

export function ArbitratorReasoning({
  before,
  after
}: {
  before: string[];
  after: string[];
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Act 4 — Arbitrator Thinking</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-4 md:grid-cols-2">
        <ReasoningColumn title="Untrained Model" lines={before} />
        <ReasoningColumn title="Trained Model" lines={after} highlight />
      </CardContent>
    </Card>
  );
}
