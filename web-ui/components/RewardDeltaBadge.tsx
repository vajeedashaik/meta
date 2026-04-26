"use client";

import { motion } from "framer-motion";

interface Props {
  delta: number;
  className?: string;
}

export function RewardDeltaBadge({ delta, className = "" }: Props) {
  const positive = delta >= 0;
  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.8 }}
      animate={{ opacity: 1, scale: 1 }}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${
        positive
          ? "bg-emerald-900/50 text-emerald-400 border border-emerald-700/40"
          : "bg-red-900/50 text-red-400 border border-red-700/40"
      } ${className}`}
    >
      {positive ? "+" : ""}
      {(delta * 100).toFixed(0)}%
    </motion.span>
  );
}
