"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";

const features = [
  { title: "Run Episode", href: "/episode", icon: "▶", desc: "Play full critic-defender-arbitrator trajectory." },
  { title: "A/B Battle Mode", href: "/ab", icon: "⚔", desc: "Compare two trajectories and declare a winner." },
  { title: "Retention Intelligence", href: "/retention", icon: "📈", desc: "See retention impact from rewrite decisions." },
  { title: "Creator Memory", href: "/memory", icon: "🧠", desc: "Track session patterns and voice stability." }
];

export default function HomePage() {
  return (
    <div className="space-y-8">
      <section className="rounded-2xl border border-blue-100 bg-white/80 p-8 shadow-soft">
        <h1 className="text-4xl font-bold tracking-tight">Viral Script Debugging Engine</h1>
        <p className="mt-3 max-w-2xl text-slate-600">
          Watch AI learn to optimize content like a strategist.
        </p>
        <div className="mt-5">
          <Button asChild size="lg">
            <Link href="/episode">Play Episode</Link>
          </Button>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2">
        {features.map((item, i) => (
          <motion.div key={item.href} whileHover={{ y: -4, scale: 1.01 }} transition={{ duration: 0.2 }}>
            <Link href={item.href}>
              <Card className="h-full transition-shadow hover:shadow-[0_14px_35px_rgba(24,119,242,0.18)]">
                <CardHeader>
                  <CardTitle>
                    {item.icon} {item.title}
                  </CardTitle>
                </CardHeader>
                <CardContent className="text-sm text-slate-600">{item.desc}</CardContent>
              </Card>
            </Link>
          </motion.div>
        ))}
      </section>
    </div>
  );
}
