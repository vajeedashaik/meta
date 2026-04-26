import { RetentionChart } from "@/components/RetentionChart";
import { retentionSeries } from "@/lib/mock-data";

export default function RetentionPage() {
  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-3xl font-bold text-white">Retention Intelligence</h1>
        <p className="mt-1 text-sm text-purple-300/70">
          Hover any data point to see why viewers dropped off at that moment.
        </p>
      </div>
      <RetentionChart data={retentionSeries} />
    </div>
  );
}
