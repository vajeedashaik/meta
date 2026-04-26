"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Session = { id: string; date: string; weak: string; strength: string; score: number };

export function CreatorMemory({ sessions }: { sessions: Session[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-white">Creator Memory Timeline</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {sessions.map((s) => (
          <div key={s.id} className="rounded-xl border border-purple-800/40 bg-purple-900/20 p-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-purple-100">{s.id}</p>
              <p className="text-xs text-purple-400/70">{s.date}</p>
            </div>
            <p className="mt-1 text-sm text-purple-200/80">Weak point: {s.weak}</p>
            <p className="text-sm text-purple-200/80">Strength: {s.strength}</p>
            <div className="mt-2 h-2 rounded-full bg-purple-900/60">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-violet-600 to-violet-400"
                style={{ width: `${s.score}%` }}
              />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
