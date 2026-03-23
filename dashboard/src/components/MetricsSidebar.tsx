"use client";

import { ParetoSolution, METRIC_LABELS, METRIC_DESCRIPTIONS, MetricKey } from "@/types";

interface Props {
  solution: ParetoSolution | null;
  partitionLabel: string | null;
}

const RATIO_METRICS: MetricKey[] = [
  "intra", "inter", "q_score", "region_purity", "tipo_purity", "affiliation_purity",
];

function MetricBar({ label, description, value }: { label: string; description: string; value: number }) {
  const pct = Math.max(0, Math.min(1, value)) * 100;
  const color =
    value >= 0.75 ? "#22c55e" :
    value >= 0.5  ? "#84cc16" :
    value >= 0.25 ? "#eab308" : "#f97316";

  return (
    <div className="mb-3 group">
      <div className="flex justify-between text-xs mb-1 items-start gap-1">
        <span className="text-slate-400 flex items-center gap-1">
          {label}
          <span
            title={description}
            className="inline-flex items-center justify-center w-3.5 h-3.5 rounded-full bg-slate-700 text-slate-400 text-[9px] cursor-help shrink-0 hover:bg-slate-600 hover:text-slate-200"
          >
            ?
          </span>
        </span>
        <span className="font-mono text-slate-200 shrink-0">{value.toFixed(4)}</span>
      </div>
      <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      {/* Description shown below on hover */}
      <p className="hidden group-hover:block text-[10px] text-slate-500 mt-1 leading-tight">
        {description}
      </p>
    </div>
  );
}

export default function MetricsSidebar({ solution, partitionLabel }: Props) {
  if (!solution) {
    return (
      <div className="text-sm text-slate-500 italic px-1 mt-4">
        Click a point on the Pareto plot to view metrics.
      </div>
    );
  }

  return (
    <div className="mt-4">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Active Solution
        </span>
        <span className="text-xs font-mono bg-indigo-900/50 text-indigo-300 px-2 py-0.5 rounded">
          #{solution.idx}
        </span>
      </div>

      {partitionLabel && (
        <div className="mb-3 text-xs bg-indigo-600/20 border border-indigo-500/30 rounded-md px-2 py-1.5 text-indigo-300">
          {partitionLabel}
        </div>
      )}

      <div className="mb-3 p-2 rounded-md bg-slate-800/60 border border-slate-700 flex items-center gap-3">
        <div className="text-center">
          <div className="text-xl font-bold text-white">{solution.n_communities}</div>
          <div className="text-xs text-slate-400">communities</div>
        </div>
        <div className="flex-1 border-l border-slate-700 pl-3 text-xs text-slate-400 space-y-0.5">
          <div>
            Q-score:{" "}
            <span className="text-slate-200 font-mono">{solution.q_score.toFixed(4)}</span>
          </div>
          <div>
            Intra:{" "}
            <span className="text-slate-200 font-mono">{solution.intra.toFixed(4)}</span>
          </div>
          <div>
            Inter:{" "}
            <span className="text-slate-200 font-mono">{solution.inter.toFixed(4)}</span>
          </div>
        </div>
      </div>

      <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
        Purity Scores
      </div>
      {RATIO_METRICS.map((k) => (
        <MetricBar
          key={k}
          label={METRIC_LABELS[k]}
          description={METRIC_DESCRIPTIONS[k]}
          value={solution[k] as number}
        />
      ))}
    </div>
  );
}
