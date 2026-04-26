import { CreatorMemory } from "@/components/CreatorMemory";
import { Card, CardContent } from "@/components/ui/card";
import { sessions } from "@/lib/mock-data";

export default function MemoryPage() {
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold text-white">Creator Memory</h1>
      <CreatorMemory sessions={sessions} />
      <Card>
        <CardContent className="p-5">
          <p className="text-xs text-purple-400/70 font-medium uppercase tracking-wide">
            Voice Stability Meter
          </p>
          <div className="mt-3 h-3 rounded-full bg-purple-900/60">
            <div
              className="h-3 rounded-full bg-gradient-to-r from-violet-600 to-violet-400"
              style={{ width: "78%" }}
            />
          </div>
          <p className="mt-2 text-sm text-purple-200/80">
            Stability improving across last 5 sessions.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
