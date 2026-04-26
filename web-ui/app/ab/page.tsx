import { ABBattle } from "@/components/ABBattle";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function ABPage() {
  return (
    <div className="space-y-5">
      <h1 className="text-3xl font-bold">A/B Battle Mode</h1>
      <ABBattle />
      <Card>
        <CardHeader>
          <CardTitle>Lesson Learned</CardTitle>
        </CardHeader>
        <CardContent className="text-slate-600">
          Preserving cultural voice first led to better retention and higher final reward.
        </CardContent>
      </Card>
    </div>
  );
}
