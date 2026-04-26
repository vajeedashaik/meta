"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Session = { id: string; date: string; weak: string; strength: string; score: number };

export function CreatorMemory({ sessions }: { sessions: Session[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Creator Memory Timeline</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {sessions.map((s) => (
          <div key={s.id} className="rounded-xl border border-blue-100 bg-blue-50/40 p-3">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium">{s.id}</p>
              <p className="text-xs text-slate-500">{s.date}</p>
            </div>
            <p className="mt-1 text-sm text-slate-600">Weak point: {s.weak}</p>
            <p className="text-sm text-slate-600">Strength: {s.strength}</p>
            <div className="mt-2 h-2 rounded-full bg-blue-100">
              <div className="h-2 rounded-full bg-primary" style={{ width: `${s.score}%` }} />
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
