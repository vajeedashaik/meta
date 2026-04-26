import { LearningGraph } from "@/components/LearningGraph";
import { Card, CardContent } from "@/components/ui/card";
import { learningSeries } from "@/lib/mock-data";

export default function LearningPage() {
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold">Learning Progression</h1>
      <LearningGraph data={learningSeries} />
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardContent className="p-5">
            <p className="text-xs text-slate-500">Baseline vs Trained</p>
            <p className="mt-1 text-sm text-slate-600">
              Trained policy consistently outperforms baseline after episode 20.
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs text-slate-500">Success Rate</p>
            <p className="mt-1 text-2xl font-bold text-primary">81%</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
