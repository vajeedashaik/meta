"use client";

import { AlertTriangle } from "lucide-react";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function DefenderPanel({
  coreStrength,
  warnings
}: {
  coreStrength: string;
  warnings: string[];
}) {
  return (
    <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.4 }}>
      <Card>
        <CardHeader>
          <CardTitle>Act 3 — Defender Response</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 shadow-[0_0_24px_rgba(24,119,242,0.24)]">
            <p className="text-xs font-medium uppercase tracking-wide text-blue-600">What Must Be Preserved</p>
            <p className="mt-1 text-sm text-slate-700">{coreStrength}</p>
          </div>
          <div className="space-y-2">
            {warnings.map((warning) => (
              <div key={warning} className="flex items-start gap-2 rounded-lg bg-slate-50 p-3">
                <AlertTriangle className="mt-0.5 h-4 w-4 text-amber-500" />
                <p className="text-sm text-slate-600">{warning}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
