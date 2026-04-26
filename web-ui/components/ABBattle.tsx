"use client";

import { useState } from "react";
import { Trophy } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function ABBattle() {
  const [step, setStep] = useState(0);
  const a = [0.52, 0.61, 0.68, 0.72];
  const b = [0.51, 0.64, 0.73, 0.8];
  const leader = b[step] >= a[step] ? "B" : "A";

  return (
    <div className="space-y-4">
      <div className="flex gap-2">
        <Button onClick={() => setStep((prev) => Math.min(prev + 1, 3))} disabled={step >= 3}>
          Advance Step
        </Button>
        <Button variant="outline" onClick={() => setStep(0)}>
          Reset Battle
        </Button>
      </div>

      <div className="grid gap-4 lg:grid-cols-[1fr_auto_1fr]">
        <Card className={leader === "A" ? "border-blue-200" : ""}>
          <CardHeader>
            <CardTitle>Trajectory A — Critic First</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>Prioritizes high-severity critique early; faster hook lift but occasional coherence risk.</p>
            <p className="font-semibold text-slate-800">Reward: {a[step].toFixed(2)}</p>
          </CardContent>
        </Card>

        <div className="flex items-center justify-center text-3xl font-bold text-primary">VS</div>

        <Card className={leader === "B" ? "border-blue-200" : ""}>
          <CardHeader>
            <CardTitle>Trajectory B — Defender First</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-slate-600">
            <p>Preserves voice first, then applies narrower edits. Better long-term retention curve.</p>
            <p className="font-semibold text-slate-800">Reward: {b[step].toFixed(2)}</p>
            {step >= 3 ? (
              <div className="inline-flex items-center gap-2 rounded-lg bg-blue-50 px-3 py-2 text-blue-700">
                <Trophy className="h-4 w-4" /> Winner: Trajectory B (+0.08 reward)
              </div>
            ) : null}
          </CardContent>
        </Card>
      </div>

      <div className="rounded-xl bg-blue-50 px-3 py-2 text-sm text-blue-700">
        Current leader: Trajectory {leader}
      </div>
    </div>
  );
}
