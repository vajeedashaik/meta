import { RetentionChart } from "@/components/RetentionChart";
import { Card, CardContent } from "@/components/ui/card";
import { retentionSeries } from "@/lib/mock-data";

export default function RetentionPage() {
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold">Retention Intelligence</h1>
      <RetentionChart data={retentionSeries} />
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardContent className="p-5">
            <p className="text-xs text-slate-500">AUC Improvement</p>
            <p className="mt-1 text-2xl font-bold text-primary">+24%</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs text-slate-500">Drop-off Shift</p>
            <p className="mt-1 text-2xl font-bold text-primary">6s {"->"} 20s</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-5">
            <p className="text-xs text-slate-500">Insight</p>
            <p className="mt-1 text-sm text-slate-600">Hook rewrite improved early retention by +22%.</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
