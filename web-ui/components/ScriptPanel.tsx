"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ScriptPanel({
  script,
  meta
}: {
  script: string;
  meta: { platform: string; region: string; niche: string };
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
      <Card>
        <CardHeader>
          <CardTitle>Act 1 — Raw Script</CardTitle>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {[meta.platform, meta.region, meta.niche].map((chip) => (
              <span key={chip} className="rounded-full bg-blue-50 px-3 py-1 text-blue-700">
                {chip}
              </span>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-line leading-7 text-slate-700">{script}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
