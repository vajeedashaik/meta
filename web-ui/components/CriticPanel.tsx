"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Claim = { id: string; text: string; severity: "high" | "medium" };

export function CriticPanel({ claims }: { claims: Claim[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Act 2 — Critic Attack</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {claims.map((claim, i) => (
          <motion.div
            key={claim.id}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.18, duration: 0.35 }}
            className={`rounded-xl border p-3 ${
              claim.severity === "high" ? "border-red-200 bg-red-50" : "border-yellow-200 bg-yellow-50"
            }`}
          >
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              {claim.id} • {claim.severity}
            </p>
            <p className="mt-1 text-sm text-slate-700">{claim.text}</p>
          </motion.div>
        ))}
      </CardContent>
    </Card>
  );
}
