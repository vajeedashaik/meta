"use client";

import { AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DefenderPanel({
  coreStrength,
  warnings,
}: {
  coreStrength: string;
  warnings: string[];
}) {
  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
      <Card>
        <CardHeader>
          <CardTitle className="text-white">Act 3 — Defender Response</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-violet-600/40 bg-violet-900/30 p-4 shadow-[0_0_24px_rgba(139,92,246,0.15)]">
            <p className="text-xs font-medium uppercase tracking-wide text-violet-400">What Must Be Preserved</p>
            <p className="mt-1 text-sm text-purple-100">{coreStrength}</p>
          </div>
          <div className="space-y-2">
            {warnings.map((warning) => (
              <div key={warning} className="flex items-start gap-2 rounded-lg bg-purple-900/30 border border-purple-800/40 p-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-400 shrink-0" />
                <p className="text-sm text-purple-200/80">{warning}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
