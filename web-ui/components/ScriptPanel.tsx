"use client";

import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ScriptPanel({
  script,
  meta,
}: {
  script: string;
  meta: { platform: string; region: string; niche: string };
}) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
      <Card>
        <CardHeader>
          <CardTitle className="text-white">Act 1 — Raw Script</CardTitle>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {[meta.platform, meta.region, meta.niche].map((chip) => (
              <span key={chip} className="rounded-full bg-violet-900/60 border border-violet-700/40 px-3 py-1 text-violet-300">
                {chip}
              </span>
            ))}
          </div>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-line leading-7 text-purple-100/90">{script}</p>
        </CardContent>
      </Card>
    </motion.div>
  );
}
