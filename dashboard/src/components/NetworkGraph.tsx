"use client";

import { useEffect, useRef, useCallback } from "react";
import type { NetworkData, PartitionData } from "@/types";
import { buildAffilColorMap } from "@/types";
import type { ElementDefinition } from "cytoscape";

interface Props {
  network: NetworkData | null;
  partition: PartitionData | null;
  focusNode: string | null;
  affiliationFilter: Set<string>;
}

// ── Community colour palette ──────────────────────────────────────────────────
// 30 visually distinct colours for the largest communities; rest get grey.
const PALETTE = [
  "#6366f1","#ec4899","#f59e0b","#10b981","#3b82f6",
  "#ef4444","#8b5cf6","#06b6d4","#84cc16","#f97316",
  "#14b8a6","#e879f9","#fbbf24","#4ade80","#60a5fa",
  "#fb7185","#a78bfa","#34d399","#fcd34d","#67e8f9",
  "#d946ef","#22d3ee","#a3e635","#fdba74","#c084fc",
  "#86efac","#93c5fd","#fca5a5","#5eead4","#bef264",
];
const ISOLATED_COLOR = "#475569";
const GENERIC_COLOR  = "#1e2433";

function communityColor(communityId: number, rank: number): string {
  if (communityId === -1) return ISOLATED_COLOR;
  if (rank < PALETTE.length) return PALETTE[rank];
  return GENERIC_COLOR;
}

// Build rank map: community → rank (by size, descending)
function buildRankMap(partition: PartitionData): Map<number, number> {
  const counts = new Map<number, number>();
  for (const cid of Object.values(partition)) {
    if (cid !== -1) counts.set(cid, (counts.get(cid) ?? 0) + 1);
  }
  const sorted = [...counts.entries()].sort((a, b) => b[1] - a[1]);
  const rank = new Map<number, number>();
  sorted.forEach(([cid], i) => rank.set(cid, i));
  return rank;
}

// Tooltip element helpers
function getTooltip(): HTMLElement {
  let el = document.getElementById("cy-tooltip");
  if (!el) {
    el = document.createElement("div");
    el.id = "cy-tooltip";
    el.className = "cy-tooltip";
    el.style.display = "none";
    document.body.appendChild(el);
  }
  return el;
}

function showTooltip(x: number, y: number, html: string) {
  const el = getTooltip();
  el.innerHTML = html;
  el.style.display = "block";
  el.style.left = `${x + 14}px`;
  el.style.top  = `${y + 14}px`;
}

function hideTooltip() {
  const el = document.getElementById("cy-tooltip");
  if (el) el.style.display = "none";
}

export default function NetworkGraph({ network, partition, focusNode, affiliationFilter }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cyRef = useRef<any>(null);
  const affiliationFilterRef = useRef<Set<string>>(new Set());
  const partitionRef = useRef<PartitionData | null>(null);

  // ── Initialise Cytoscape ───────────────────────────────────────────────────
  useEffect(() => {
    if (!network || !containerRef.current) return;

    let cancelled = false;

    (async () => {
      const cytoscape = (await import("cytoscape")).default;

      if (cancelled || !containerRef.current) return;

      // Scale positions to pixels
      const W = containerRef.current.clientWidth  || 800;
      const H = containerRef.current.clientHeight || 600;

      const elements: ElementDefinition[] = [];

      for (const n of network.nodes) {
        elements.push({
          data: {
            id:          n.id,
            label:       n.id,
            papers:      n.papers,
            affiliation: n.affiliation,
            tipo:        n.tipo,
            region:      n.region,
          },
          position: {
            x: ((n.x + 1) / 2) * W * 0.9 + W * 0.05,
            y: ((n.y + 1) / 2) * H * 0.9 + H * 0.05,
          },
        });
      }

      for (const e of network.edges) {
        elements.push({
          data: {
            id:     `${e.source}__${e.target}`,
            source: e.source,
            target: e.target,
            weight: e.weight,
          },
        });
      }

      const cy = cytoscape({
        container: containerRef.current,
        elements,
        layout: { name: "preset" },
        style: [
          {
            selector: "node",
            style: {
              "background-color":    "#334155",
              "width":               "mapData(papers, 1, 30, 6, 22)",
              "height":              "mapData(papers, 1, 30, 6, 22)",
              "border-width":        0,
              "label":               "",
              "overlay-opacity":     0,
            },
          },
          {
            selector: "edge",
            style: {
              "line-color":          "#1e2433",
              "width":               "mapData(weight, 1, 10, 0.5, 3)",
              "opacity":             0.6,
              "curve-style":         "haystack",
              "overlay-opacity":     0,
            },
          },
          {
            selector: ".highlighted",
            style: {
              "border-width":        3,
              "border-color":        "#f59e0b",
              "border-opacity":      1,
              "z-index":             999,
            },
          },
          {
            selector: ".ego-node",
            style: {
              "border-width":        2,
              "border-color":        "#6366f1",
              "border-opacity":      0.8,
            },
          },
          {
            selector: ".ego-edge",
            style: {
              "line-color":          "#6366f1",
              "opacity":             1,
              "width":               2,
            },
          },
          {
            selector: ".faded",
            style: {
              "opacity":             0.1,
            },
          },
        ],
        minZoom: 0.05,
        maxZoom: 8,
        wheelSensitivity: 1.5,
        motionBlur: false,
        textureOnViewport: true,
        hideEdgesOnViewport: true,
        pixelRatio: 1,           // skip HiDPI upscaling — major perf gain
      });

      cy.fit(undefined, 40);    // fit all nodes into view on load

      // Tooltip on hover
      cy.on("mouseover", "node", (e: { target: any; originalEvent: MouseEvent }) => {
        const n = e.target;
        const d = n.data();
        showTooltip(
          e.originalEvent.clientX,
          e.originalEvent.clientY,
          `<strong style="color:#e2e8f0">${d.id}</strong><br>
           <span style="color:#94a3b8">Affiliation:</span> ${d.affiliation}<br>
           <span style="color:#94a3b8">Type:</span> ${d.tipo}<br>
           <span style="color:#94a3b8">Region:</span> ${d.region}<br>
           <span style="color:#94a3b8">Papers:</span> ${d.papers}`
        );
      });
      cy.on("mouseout", "node", hideTooltip);
      cy.on("tap", "node", (e: { target: any }) => {
        const nid: string = e.target.id();
        highlightEgo(cy, nid);
      });
      cy.on("tap", (e: { target: any }) => {
        if (e.target === cy) clearHighlight(cy);
      });

      cyRef.current = cy;
    })();

    return () => {
      cancelled = true;
      if (cyRef.current) {
        cyRef.current.destroy();
        cyRef.current = null;
      }
      hideTooltip();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [network]);

  // ── Apply partition colours ────────────────────────────────────────────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || !partition) return;
    partitionRef.current = partition;

    const rankMap = buildRankMap(partition);

    cy.batch(() => {
      cy.nodes().forEach((node: any) => {
        const cid: number = partition[node.id()] ?? -1;
        const rank = cid === -1 ? -1 : (rankMap.get(cid) ?? PALETTE.length);
        node.style("background-color", communityColor(cid, rank));
        node.data("community", cid);
      });
    });
  }, [partition]);

  // ── Apply affiliation filter ───────────────────────────────────────────────
  useEffect(() => {
    affiliationFilterRef.current = affiliationFilter;
    const cy = cyRef.current;
    if (!cy) return;
    applyAffilFilter(cy);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [affiliationFilter]);

  // ── Affiliation filter helpers ─────────────────────────────────────────────
  function applyAffilFilter(cy: any) {
    const filter = affiliationFilterRef.current;
    if (filter.size === 0) {
      // Restore community colors and full opacity
      const p = partitionRef.current;
      const rankMap = p ? buildRankMap(p) : null;
      cy.nodes().forEach((n: any) => {
        n.style("opacity", 1);
        if (p && rankMap) {
          const cid: number = p[n.id()] ?? -1;
          const rank = cid === -1 ? -1 : (rankMap.get(cid) ?? PALETTE.length);
          n.style("background-color", communityColor(cid, rank));
        }
      });
      return;
    }
    const colorMap = buildAffilColorMap(filter);
    cy.nodes().forEach((n: any) => {
      const aff = n.data("affiliation") as string;
      if (filter.has(aff)) {
        n.style("opacity", 1);
        n.style("background-color", colorMap.get(aff) ?? "#f59e0b");
      } else {
        n.style("opacity", 0.05);
      }
    });
  }

  // ── Focus / ego-network ────────────────────────────────────────────────────
  const highlightEgo = useCallback((cy: any, nodeId: string) => {
    clearHighlight(cy);
    const node = cy.getElementById(nodeId);
    if (!node.length) return;

    const neighbors = node.neighborhood();
    cy.elements().addClass("faded");
    node.removeClass("faded").addClass("highlighted");
    neighbors.removeClass("faded").addClass("ego-node");
    node.connectedEdges().removeClass("faded").addClass("ego-edge");

    cy.animate({ fit: { eles: node.union(neighbors), padding: 80 }, duration: 600 });
  }, []);

  function clearHighlight(cy: any) {
    cy.elements().removeClass("faded highlighted ego-node ego-edge");
    applyAffilFilter(cy);
  }

  // ── React to focusNode prop ────────────────────────────────────────────────
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    if (!focusNode) {
      clearHighlight(cy);
      return;
    }
    highlightEgo(cy, focusNode);
  }, [focusNode, highlightEgo]);

  // ── Loading state ──────────────────────────────────────────────────────────
  if (!network) {
    return (
      <div className="flex items-center justify-center h-full text-slate-500 text-sm">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-slate-600 border-t-indigo-500 rounded-full mx-auto mb-3" />
          Loading network…
        </div>
      </div>
    );
  }

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} id="cy" className="w-full h-full" />

      {/* Controls hint */}
      <div className="absolute bottom-3 right-3 text-xs text-slate-600 bg-slate-900/80 rounded px-2 py-1 pointer-events-none">
        Scroll to zoom · Drag to pan · Click node for ego-network
      </div>
    </div>
  );
}
