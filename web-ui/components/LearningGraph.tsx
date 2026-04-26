"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Point = {
  episode: number;
  baseline: number;
  trained: number;
  retentionLift: number;
  success: number;
};

export function LearningGraph({ data }: { data: Point[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-white">Learning Progression</CardTitle>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#2e2255" />
            <XAxis dataKey="episode" tick={{ fill: "#a78bfa", fontSize: 12 }} />
            <YAxis tick={{ fill: "#a78bfa", fontSize: 12 }} />
            <Tooltip
              contentStyle={{
                background: "#120f1e",
                border: "1px solid #2e2255",
                borderRadius: "0.75rem",
                color: "#ede9f8",
              }}
            />
            <Legend wrapperStyle={{ color: "#c4b5fd" }} />
            <Line dataKey="baseline" stroke="#4b3a7a" strokeWidth={2} dot={false} />
            <Line dataKey="trained"  stroke="#8b5cf6" strokeWidth={3} dot={false} />
            <Line dataKey="success"  stroke="#06b6d4" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
