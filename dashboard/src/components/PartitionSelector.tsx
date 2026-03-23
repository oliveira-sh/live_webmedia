"use client";

import { PartitionsMeta } from "@/types";

interface Props {
  meta: PartitionsMeta;
  activeKey: string | null;
  onSelect: (key: string) => void;
}

const ORDER = [
  "partition_best_modularity",
  "partition_best_region",
  "partition_best_tipo",
  "partition_best_affiliation",
  "partition_default",
];

export default function PartitionSelector({ meta, activeKey, onSelect }: Props) {
  const keys = ORDER.filter((k) => k in meta);

  return (
    <div className="flex flex-col gap-1.5">
      <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-0.5">
        Pre-computed Partitions
      </div>
      {keys.map((key) => {
        const m = meta[key];
        const active = key === activeKey;
        return (
          <button
            key={key}
            onClick={() => onSelect(key)}
            className={`w-full text-left px-3 py-2 rounded-md text-xs transition-all border ${
              active
                ? "bg-indigo-600/30 border-indigo-500/60 text-indigo-200"
                : "bg-slate-800/60 border-slate-700 text-slate-300 hover:bg-slate-700/60 hover:border-slate-500"
            }`}
          >
            <div className="font-medium">{m.label}</div>
            <div className="text-slate-400 mt-0.5">{m.n_communities} communities</div>
          </button>
        );
      })}
    </div>
  );
}
