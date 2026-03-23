"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import dynamic from "next/dynamic";
import type {
  NetworkData, ParetoSolution, PartitionData,
  PartitionsMeta, MetricKey,
} from "@/types";
import MetricsSidebar    from "@/components/MetricsSidebar";
import ParetoPlot        from "@/components/ParetoPlot";
import SearchBar         from "@/components/SearchBar";
import PartitionSelector from "@/components/PartitionSelector";
import UniversityFilter  from "@/components/UniversityFilter";

// Cytoscape is browser-only
const NetworkGraph = dynamic(() => import("@/components/NetworkGraph"), { ssr: false });

// ── Data fetching helpers ──────────────────────────────────────────────────────

const BASE_PATH = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

async function fetchJSON<T>(path: string): Promise<T> {
  const url = `${BASE_PATH}${path}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to fetch ${url}: ${res.status}`);
  return res.json() as Promise<T>;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function Dashboard() {
  // Raw data
  const [network,       setNetwork]       = useState<NetworkData | null>(null);
  const [pareto,        setPareto]         = useState<ParetoSolution[]>([]);
  const [partitionsMeta, setPartitionsMeta] = useState<PartitionsMeta>({});
  const [loadingData,   setLoadingData]   = useState(true);
  const [dataError,     setDataError]     = useState<string | null>(null);

  // Active partition
  const [activePartitionKey,  setActivePartitionKey]  = useState<string | null>(null);
  const [partitionData,       setPartitionData]        = useState<PartitionData | null>(null);
  const [loadingPartition,    setLoadingPartition]     = useState(false);

  // Pareto selection
  const [selectedSolutionIdx, setSelectedSolutionIdx] = useState<number | null>(null);

  // Axes
  const [xKey, setXKey] = useState<MetricKey>("intra");
  const [yKey, setYKey] = useState<MetricKey>("q_score");

  // Search / focus
  const [focusNode, setFocusNode] = useState<string | null>(null);

  // Affiliation filter
  const [affiliationFilter, setAffiliationFilter] = useState<Set<string>>(new Set());

  // ── Load base data ─────────────────────────────────────────────────────────
  useEffect(() => {
    (async () => {
      try {
        const [net, par, pmeta] = await Promise.all([
          fetchJSON<NetworkData>("/data/network.json"),
          fetchJSON<ParetoSolution[]>("/data/pareto_results.json"),
          fetchJSON<PartitionsMeta>("/data/partitions_meta.json"),
        ]);
        setNetwork(net);
        setPareto(par);
        setPartitionsMeta(pmeta);

        // Auto-select first partition
        const firstKey = Object.keys(pmeta)[0] ?? null;
        if (firstKey) loadPartition(firstKey, pmeta, par);
      } catch (err) {
        setDataError(String(err));
      } finally {
        setLoadingData(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ── Load a partition ───────────────────────────────────────────────────────
  const loadPartition = useCallback(
    async (key: string, meta: PartitionsMeta, solutions: ParetoSolution[]) => {
      const m = meta[key];
      if (!m) return;
      setLoadingPartition(true);
      setActivePartitionKey(key);
      try {
        const data = await fetchJSON<PartitionData>(`/data/partitions/${m.filename}`);
        setPartitionData(data);
        // Sync selected solution
        setSelectedSolutionIdx(m.idx);
      } catch (err) {
        console.error("Failed to load partition", err);
      } finally {
        setLoadingPartition(false);
      }
    },
    []
  );

  const handlePartitionSelect = useCallback(
    (key: string) => loadPartition(key, partitionsMeta, pareto),
    [loadPartition, partitionsMeta, pareto]
  );

  // ── Pareto point click ─────────────────────────────────────────────────────
  const handleParetoSelect = useCallback(
    (solution: ParetoSolution) => {
      setSelectedSolutionIdx(solution.idx);
      if (solution.partition_key) {
        loadPartition(solution.partition_key, partitionsMeta, pareto);
      }
    },
    [loadPartition, partitionsMeta, pareto]
  );

  // ── Derived ────────────────────────────────────────────────────────────────
  const selectedSolution = useMemo(
    () => pareto.find((s) => s.idx === selectedSolutionIdx) ?? null,
    [pareto, selectedSolutionIdx]
  );

  const activePartitionLabel = useMemo(
    () => (activePartitionKey ? partitionsMeta[activePartitionKey]?.label ?? null : null),
    [activePartitionKey, partitionsMeta]
  );

  const nodeIds = useMemo(
    () => network?.nodes.map((n) => n.id) ?? [],
    [network]
  );

  const affiliations = useMemo(
    () => [...new Set((network?.nodes ?? []).map((n) => n.affiliation))].sort(),
    [network]
  );

  // ── Render ─────────────────────────────────────────────────────────────────
  if (loadingData) {
    return (
      <div className="flex items-center justify-center h-full bg-surface">
        <div className="text-center">
          <div className="animate-spin w-10 h-10 border-2 border-slate-700 border-t-indigo-500 rounded-full mx-auto mb-4" />
          <p className="text-slate-400 text-sm">Loading dashboard data…</p>
          <p className="text-slate-600 text-xs mt-1">
            Make sure you have run <code className="text-indigo-400">python3 scripts/preprocess.py</code> first.
          </p>
        </div>
      </div>
    );
  }

  if (dataError) {
    return (
      <div className="flex items-center justify-center h-full bg-surface">
        <div className="max-w-md text-center p-6 rounded-xl border border-red-900 bg-red-900/20">
          <div className="text-red-400 font-semibold mb-2">Failed to load data</div>
          <p className="text-slate-400 text-sm mb-3">{dataError}</p>
          <p className="text-slate-500 text-xs">
            Run <code className="text-indigo-400 bg-slate-800 px-1 rounded">python3 scripts/preprocess.py</code> from
            the repo root, then restart the dev server.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-surface">
      {/* ── Header ─────────────────────────────────────────────────────────── */}
      <header className="shrink-0 border-b border-border bg-panel px-5 py-3 flex items-center gap-4">
        <div>
          <h1 className="text-base font-bold text-white tracking-tight">
            HPMOCD Community Explorer
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            WebMedia Co-authorship Network · {network?.nodes.length.toLocaleString()} authors ·{" "}
            {network?.edges.length.toLocaleString()} edges · {pareto.length} Pareto solutions
          </p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {loadingPartition && (
            <span className="text-xs text-indigo-400 flex items-center gap-1.5">
              <span className="inline-block w-3 h-3 border border-indigo-500 border-t-transparent rounded-full animate-spin" />
              Loading partition…
            </span>
          )}
          <SearchBar
            nodeIds={nodeIds}
            onSelect={setFocusNode}
            onClear={() => setFocusNode(null)}
          />
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">
        {/* ── Left sidebar ─────────────────────────────────────────────────── */}
        <aside className="w-80 shrink-0 border-r border-border bg-panel flex flex-col overflow-y-auto">
          <div className="p-4 space-y-5">
            {/* Pareto plot */}
            <section>
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
                Pareto Front ({pareto.length} solutions)
              </div>
              <ParetoPlot
                data={pareto}
                xKey={xKey}
                yKey={yKey}
                selectedIdx={selectedSolutionIdx}
                onSelect={handleParetoSelect}
                onAxisChange={(axis, key) =>
                  axis === "x" ? setXKey(key) : setYKey(key)
                }
              />
            </section>

            <div className="border-t border-border" />

            {/* Partition quick-select */}
            {Object.keys(partitionsMeta).length > 0 && (
              <section>
                <PartitionSelector
                  meta={partitionsMeta}
                  activeKey={activePartitionKey}
                  onSelect={handlePartitionSelect}
                />
              </section>
            )}

            <div className="border-t border-border" />

            {/* University filter */}
            <section>
              <UniversityFilter
                affiliations={affiliations}
                selected={affiliationFilter}
                onChange={setAffiliationFilter}
              />
            </section>

            <div className="border-t border-border" />

            {/* Metrics */}
            <section>
              <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-0.5">
                Solution Metrics
              </div>
              <MetricsSidebar
                solution={selectedSolution}
                partitionLabel={activePartitionLabel}
              />
            </section>
          </div>
        </aside>

        {/* ── Network graph ─────────────────────────────────────────────────── */}
        <main className="flex-1 overflow-hidden relative">
          <NetworkGraph
            network={network}
            partition={partitionData}
            focusNode={focusNode}
            affiliationFilter={affiliationFilter}
          />
          {!partitionData && !loadingPartition && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="text-slate-600 text-sm bg-surface/80 rounded-lg px-4 py-2 border border-border">
                Select a partition to colour-code communities
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
