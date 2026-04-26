"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { PipelineViz } from "@/components/PipelineViz";
import { systemStats } from "@/lib/mock-data";

const features = [
  { title: "Dashboard",          href: "/dashboard",  icon: "🖥️",  desc: "Live system overview: all 12 phases, 181 tests, full metrics." },
  { title: "Run Episode",        href: "/episode",    icon: "▶️",   desc: "Play full critic-defender-arbitrator trajectory with live API." },
  { title: "A/B Battle Mode",    href: "/ab",         icon: "⚔️",  desc: "Compare two trajectories step-by-step and declare a winner." },
  { title: "Retention Curves",   href: "/retention",  icon: "📈",  desc: "See 60s viewer drop-off before and after rewrite decisions." },
  { title: "Creator Memory",     href: "/memory",     icon: "🧠",  desc: "Track session patterns, voice stability, longitudinal memory." },
  { title: "Learning Graph",     href: "/learning",   icon: "📊",  desc: "Baseline vs trained reward over 100 episodes." }
];

const highlights = [
  { label: "Phases",   value: "12/12", color: "text-emerald-600" },
  { label: "Tests",    value: "181",   color: "text-blue-600"    },
  { label: "Rewards",  value: "R1-R10",color: "text-violet-600"  },
  { label: "Peak R",   value: "79%",   color: "text-primary"     }
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      {/* Hero */}
      <section className="rounded-2xl border border-blue-100 bg-white/80 p-8 shadow-soft">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-4xl font-bold tracking-tight">Viral Script Debugging Engine</h1>
            <p className="mt-2 max-w-2xl text-slate-500">
              Multi-agent RL system: Critic attacks, Defender preserves, Arbitrator decides, Rewriter executes.
              10 reward signals. 181 tests passing. Retention curve predictor (MAE 0.031).
            </p>
            <div className="mt-4 flex gap-3">
              <Button asChild size="lg">
                <Link href="/episode">Play Episode</Link>
              </Button>
              <Button asChild size="lg" variant="outline">
                <Link href="/dashboard">View Dashboard</Link>
              </Button>
            </div>
          </div>

          {/* Quick stats */}
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {highlights.map((h) => (
              <div key={h.label} className="rounded-xl border border-blue-100 bg-blue-50/40 px-4 py-3 text-center">
                <p className={`text-2xl font-bold ${h.color}`}>{h.value}</p>
                <p className="mt-0.5 text-xs text-slate-500">{h.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Live pipeline preview */}
      <PipelineViz />

      {/* Feature cards */}
      <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {features.map((item, i) => (
          <motion.div
            key={item.href}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.07, duration: 0.3 }}
            whileHover={{ y: -3, scale: 1.01 }}
          >
            <Link href={item.href} className="block h-full">
              <Card className="h-full transition-shadow hover:shadow-[0_14px_35px_rgba(24,119,242,0.15)]">
                <CardHeader className="pb-2">
                  <CardTitle className="text-lg">
                    {item.icon} {item.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-slate-500">{item.desc}</CardContent>
              </Card>
            </Link>
          </motion.div>
        ))}
      </section>

      {/* Phase status strip */}
      <section className="rounded-2xl border border-slate-100 bg-white/70 p-5">
        <p className="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">All 12 Phases</p>
        <div className="flex flex-wrap gap-2">
          {Array.from({ length: 12 }, (_, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: i * 0.04 }}
              className="flex items-center gap-1.5 rounded-lg bg-emerald-50 border border-emerald-100 px-2.5 py-1.5"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" />
              <span className="text-xs font-semibold text-emerald-700">Phase {i + 1}</span>
              <span className="text-xs text-emerald-600">✓</span>
            </motion.div>
          ))}
        </div>
      </section>
    </div>
  );
}
