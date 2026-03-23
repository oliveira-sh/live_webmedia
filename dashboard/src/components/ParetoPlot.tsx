"use client";

import {
  ScatterChart, Scatter, XAxis, YAxis, Tooltip,
  CartesianGrid, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { ParetoSolution, MetricKey, METRIC_LABELS } from "@/types";
import { useMemo } from "react";

interface Props {
  data: ParetoSolution[];
  xKey: MetricKey;
  yKey: MetricKey;
  selectedIdx: number | null;
  onSelect: (solution: ParetoSolution) => void;
  onAxisChange: (axis: "x" | "y", key: MetricKey) => void;
}

const AXIS_OPTIONS: MetricKey[] = [
  "intra", "inter", "q_score", "region_purity", "tipo_purity", "affiliation_purity",
];

// Colour each dot by whether it has a pre-computed partition
function dotColor(s: ParetoSolution, selectedIdx: number | null): string {
  if (s.idx === selectedIdx) return "#f59e0b";  // amber – selected
  if (s.partition_key)       return "#6366f1";  // indigo – has partition
  return "#334155";                              // slate – generic
}

// Custom dot renderer
function CustomDot(props: {
  cx?: number; cy?: number; payload?: ParetoSolution;
  selectedIdx: number | null; onClick: (s: ParetoSolution) => void;
}) {
  const { cx = 0, cy = 0, payload, selectedIdx, onClick } = props;
  if (!payload) return null;
  const isSelected   = payload.idx === selectedIdx;
  const hasPartition = Boolean(payload.partition_key);
  const r = isSelected ? 7 : hasPartition ? 6 : 3;
  const fill = dotColor(payload, selectedIdx);

  return (
    <circle
      cx={cx} cy={cy} r={r} fill={fill}
      stroke={isSelected ? "#fbbf24" : hasPartition ? "#818cf8" : "none"}
      strokeWidth={isSelected ? 2 : 1}
      style={{ cursor: "pointer" }}
      onClick={() => onClick(payload)}
    />
  );
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function CustomTooltip({ active, payload }: any) {
  if (!active || !payload?.length) return null;
  const s: ParetoSolution = payload[0].payload;
  return (
    <div className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-xs shadow-xl">
      <div className="font-semibold text-slate-200 mb-1">Solution #{s.idx}</div>
      {s.partition_key && (
        <div className="text-indigo-400 mb-1">{s.partition_key.replace(/_/g, " ")}</div>
      )}
      <div className="space-y-0.5 text-slate-400">
        <div>Communities: <span className="text-white">{s.n_communities}</span></div>
        <div>Q-score: <span className="text-white">{s.q_score.toFixed(4)}</span></div>
        <div>Intra: <span className="text-white">{s.intra.toFixed(4)}</span></div>
        <div>Inter: <span className="text-white">{s.inter.toFixed(4)}</span></div>
      </div>
    </div>
  );
}

export default function ParetoPlot({
  data, xKey, yKey, selectedIdx, onSelect, onAxisChange,
}: Props) {
  const chartData = useMemo(() =>
    data.map((s) => ({ ...s, _x: s[xKey] as number, _y: s[yKey] as number })),
    [data, xKey, yKey]
  );

  return (
    <div className="flex flex-col gap-2">
      {/* Axis selectors */}
      <div className="flex gap-2 text-xs">
        {(["x", "y"] as const).map((axis) => (
          <div key={axis} className="flex items-center gap-1 flex-1">
            <span className="text-slate-400 uppercase">{axis}:</span>
            <select
              className="flex-1 bg-slate-800 border border-slate-600 rounded px-1.5 py-0.5 text-slate-200 text-xs"
              value={axis === "x" ? xKey : yKey}
              onChange={(e) => onAxisChange(axis, e.target.value as MetricKey)}
            >
              {AXIS_OPTIONS.map((k) => (
                <option key={k} value={k}>{METRIC_LABELS[k]}</option>
              ))}
            </select>
          </div>
        ))}
      </div>

      {/* Scatter plot */}
      <ResponsiveContainer width="100%" height={260}>
        <ScatterChart margin={{ top: 4, right: 4, bottom: 4, left: -16 }}>
          <CartesianGrid stroke="#1e2433" strokeDasharray="3 3" />
          <XAxis
            dataKey="_x"
            type="number"
            domain={["auto", "auto"]}
            tick={{ fill: "#64748b", fontSize: 10 }}
            label={{ value: METRIC_LABELS[xKey], position: "insideBottom", offset: -2, fill: "#64748b", fontSize: 9 }}
          />
          <YAxis
            dataKey="_y"
            type="number"
            domain={["auto", "auto"]}
            tick={{ fill: "#64748b", fontSize: 10 }}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />
          <Scatter
            data={chartData}
            // @ts-expect-error recharts accepts custom shape
            shape={(props) => (
              <CustomDot {...props} selectedIdx={selectedIdx} onClick={onSelect} />
            )}
          />
          {selectedIdx !== null && (() => {
            const sel = data.find((s) => s.idx === selectedIdx);
            if (!sel) return null;
            return (
              <>
                <ReferenceLine x={sel[xKey] as number} stroke="#fbbf2466" strokeWidth={1} />
                <ReferenceLine y={sel[yKey] as number} stroke="#fbbf2466" strokeWidth={1} />
              </>
            );
          })()}
        </ScatterChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex gap-4 text-xs text-slate-500 justify-center">
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-indigo-500" />
          Has partition
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-amber-400" />
          Selected
        </span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-slate-600" />
          Other
        </span>
      </div>
    </div>
  );
}
