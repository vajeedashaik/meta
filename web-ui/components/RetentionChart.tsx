"use client";

import { useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Point = { t: number; before: number; after: number };

const DROP_REASONS: Record<number, string> = {
  6:  "Weak hook caused early drop-off — viewers didn't engage with the opening line",
  12: "Mid-section lacks pacing — generic advice triggered attention drop",
  20: "CTA appeared too early — created friction before value was delivered",
  30: "Momentum lost after repositioned CTA — body needs stronger bridge",
  45: "Engagement floor reached — retained viewers are highly-interested segment",
  60: "End-card CTA fires here — drop is expected at natural completion point",
};

function auc(points: Point[], key: "before" | "after"): number {
  let area = 0;
  for (let i = 1; i < points.length; i++) {
    const dt = points[i].t - points[i - 1].t;
    area += ((points[i][key] + points[i - 1][key]) / 2) * dt;
  }
  return area / (points[points.length - 1].t * 100);
}

interface CustomDotProps {
  cx?: number;
  cy?: number;
  payload?: Point;
  dataKey?: string;
  activePoint?: number | null;
  onHover?: (t: number | null) => void;
}

function CustomDot({ cx = 0, cy = 0, payload, dataKey, activePoint, onHover }: CustomDotProps) {
  if (!payload || !onHover) return null;
  const isActive = activePoint === payload.t;
  const color = dataKey === "after" ? "#8b5cf6" : "#4b3a7a";
  return (
    <circle
      cx={cx}
      cy={cy}
      r={isActive ? 7 : 4}
      fill={color}
      stroke="#09080f"
      strokeWidth={2}
      style={{ cursor: "pointer" }}
      onMouseEnter={() => onHover(payload.t)}
      onMouseLeave={() => onHover(null)}
    />
  );
}

export function RetentionChart({ data }: { data: Point[] }) {
  const [activePoint, setActivePoint] = useState<number | null>(null);

  const aucBefore = auc(data, "before");
  const aucAfter  = auc(data, "after");

  const dropPoint      = data.find((p, i) => i > 0 && p.before < data[i - 1].before - 10);
  const dropAfterPoint = data.find((p, i) => i > 0 && p.after  < data[i - 1].after  - 10);

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-white">Retention Curve (0–60s)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} onMouseLeave={() => setActivePoint(null)}>
                <XAxis
                  dataKey="t"
                  tick={{ fill: "#a78bfa", fontSize: 12 }}
                  label={{ value: "Time (seconds)", position: "insideBottom", offset: -2, fontSize: 11, fill: "#a78bfa" }}
                />
                <YAxis
                  tick={{ fill: "#a78bfa", fontSize: 12 }}
                  label={{ value: "Viewers (%)", angle: -90, position: "insideLeft", offset: 10, fontSize: 11, fill: "#a78bfa" }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.length) return null;
                    const t = payload[0].payload.t as number;
                    const reason = DROP_REASONS[t];
                    return (
                      <div className="rounded-xl border border-purple-700/40 bg-[#120f1e] p-3 shadow-md text-xs max-w-[220px]">
                        <p className="font-semibold mb-1 text-white">t = {t}s</p>
                        <p className="text-purple-300">Before: {payload.find((p) => p.dataKey === "before")?.value}%</p>
                        <p className="text-violet-400">After: {payload.find((p) => p.dataKey === "after")?.value}%</p>
                        {reason && <p className="mt-2 text-purple-400/70 italic">{reason}</p>}
                      </div>
                    );
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="before"
                  stroke="#4b3a7a"
                  strokeWidth={2}
                  isAnimationActive
                  animationDuration={800}
                  dot={(props) => (
                    <CustomDot {...props} dataKey="before" activePoint={activePoint} onHover={setActivePoint} />
                  )}
                />
                <Line
                  type="monotone"
                  dataKey="after"
                  stroke="#8b5cf6"
                  strokeWidth={3}
                  isAnimationActive
                  animationDuration={1000}
                  dot={(props) => (
                    <CustomDot {...props} dataKey="after" activePoint={activePoint} onHover={setActivePoint} />
                  )}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <AnimatePresence>
            {activePoint !== null && DROP_REASONS[activePoint] && (
              <motion.div
                key={activePoint}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.2 }}
                className="rounded-xl bg-purple-900/40 border border-purple-700/40 px-4 py-2 text-sm text-purple-200"
              >
                <span className="font-semibold text-white">t={activePoint}s — </span>
                {DROP_REASONS[activePoint]}
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm text-white">Retention Analysis</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3 text-sm">
            <div>
              <p className="text-xs text-purple-400/70 mb-1">AUC Before → After</p>
              <p className="font-bold text-violet-400">
                {aucBefore.toFixed(2)} → {aucAfter.toFixed(2)}
              </p>
              <p className="text-xs text-emerald-400 mt-0.5">
                +{(((aucAfter - aucBefore) / aucBefore) * 100).toFixed(0)}% improvement
              </p>
            </div>
            <div>
              <p className="text-xs text-purple-400/70 mb-1">First Major Drop</p>
              <p className="font-bold text-purple-100">
                {dropPoint?.t ?? "—"}s → {dropAfterPoint?.t ?? "—"}s
              </p>
              <p className="text-xs text-emerald-400 mt-0.5">Drop point moved later</p>
            </div>
            <div>
              <p className="text-xs text-purple-400/70 mb-1">Explanation</p>
              <p className="text-purple-200/70 text-xs">
                Hook rewrite improved early engagement by delaying the first major drop-off and creating a stronger open loop in the first 6 seconds.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
