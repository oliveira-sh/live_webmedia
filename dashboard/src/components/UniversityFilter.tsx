"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import { buildAffilColorMap } from "@/types";

interface Props {
  affiliations: string[];
  selected: Set<string>;
  onChange: (selected: Set<string>) => void;
}

export default function UniversityFilter({ affiliations, selected, onChange }: Props) {
  const [search, setSearch] = useState("");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    return q ? affiliations.filter((a) => a.toLowerCase().includes(q)) : affiliations;
  }, [affiliations, search]);

  const colorMap = useMemo(() => buildAffilColorMap(selected), [selected]);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  function toggle(aff: string) {
    const next = new Set(selected);
    if (next.has(aff)) next.delete(aff);
    else next.add(aff);
    onChange(next);
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-semibold uppercase tracking-wider text-slate-400">
          Filter by University
        </span>
        {selected.size > 0 && (
          <button
            onClick={() => onChange(new Set())}
            className="text-[10px] text-indigo-400 hover:text-indigo-300"
          >
            Clear ({selected.size})
          </button>
        )}
      </div>

      {/* Search input */}
      <input
        type="text"
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        onFocus={() => setOpen(true)}
        placeholder="Search affiliation…"
        className="w-full bg-slate-800 border border-slate-700 rounded px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-indigo-500"
      />

      {/* Dropdown */}
      {open && (
        <div className="absolute z-50 mt-1 w-full max-h-44 overflow-y-auto bg-slate-800 border border-slate-700 rounded shadow-xl">
          {filtered.length === 0 ? (
            <div className="px-2 py-2 text-xs text-slate-500">No results</div>
          ) : (
            filtered.map((aff) => (
              <label
                key={aff}
                className="flex items-center gap-2 px-2 py-1 text-xs text-slate-200 hover:bg-slate-700 cursor-pointer"
              >
                <input
                  type="checkbox"
                  checked={selected.has(aff)}
                  onChange={() => toggle(aff)}
                  className="accent-indigo-500 shrink-0"
                />
                <span className="truncate">{aff}</span>
              </label>
            ))
          )}
        </div>
      )}

      {/* Selected badges */}
      {selected.size > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {[...selected].sort().map((aff) => {
            const color = colorMap.get(aff) ?? "#6366f1";
            return (
              <span
                key={aff}
                onClick={() => toggle(aff)}
                style={{ borderColor: color, color }}
                className="inline-flex items-center gap-0.5 border text-[10px] px-1.5 py-0.5 rounded cursor-pointer hover:opacity-80 bg-slate-900/60"
              >
                <span
                  style={{ backgroundColor: color }}
                  className="inline-block w-1.5 h-1.5 rounded-full shrink-0"
                />
                {aff}
                <span className="ml-0.5 opacity-60">×</span>
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
