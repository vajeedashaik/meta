import { CreatorMemory } from "@/components/CreatorMemory";
import { Card, CardContent } from "@/components/ui/card";
import { sessions } from "@/lib/mock-data";

export default function MemoryPage() {
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold">Creator Memory</h1>
      <CreatorMemory sessions={sessions} />
      <Card>
        <CardContent className="p-5">
          <p className="text-xs text-slate-500">Voice Stability Meter</p>
          <div className="mt-2 h-3 rounded-full bg-blue-100">
            <div className="h-3 rounded-full bg-primary" style={{ width: "78%" }} />
          </div>
          <p className="mt-2 text-sm text-slate-600">Stability improving across last 5 sessions.</p>
        </CardContent>
      </Card>
    </div>
  );
}
