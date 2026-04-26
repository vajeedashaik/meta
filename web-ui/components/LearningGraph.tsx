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
  YAxis
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
        <CardTitle>Learning Progression</CardTitle>
      </CardHeader>
      <CardContent className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="episode" />
            <YAxis />
            <Tooltip />
            <Legend />
            <Line dataKey="baseline" stroke="#94a3b8" strokeWidth={2} />
            <Line dataKey="trained" stroke="#1877F2" strokeWidth={3} />
            <Line dataKey="success" stroke="#0ea5e9" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
