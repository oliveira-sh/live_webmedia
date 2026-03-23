---
name: HPMOCD Dashboard
description: Web dashboard built for exploring multi-objective community detection results on the WebMedia co-authorship network
type: project
---

Next.js 14 + Cytoscape.js + Recharts dashboard at `dashboard/`.

**Why:** Visualise the Pareto front of HPMOCD solutions (1000 trade-offs) and explore the underlying co-authorship network coloured by community assignment.

**How to apply:** When making changes, the preprocessing pipeline must be re-run (`python3 scripts/preprocess.py`) before the data shows up in the UI.

Key files:
- `scripts/preprocess.py` – converts GraphML + CSV + partition JSONs → `dashboard/public/data/`
- `dashboard/src/app/page.tsx` – main page with all state
- `dashboard/src/components/NetworkGraph.tsx` – Cytoscape.js wrapper (dynamic import, browser-only)
- `dashboard/src/components/ParetoPlot.tsx` – Recharts ScatterChart for the 1000-solution Pareto front
- `dashboard/src/components/MetricsSidebar.tsx` – metric bars for selected solution
- `dashboard/src/components/SearchBar.tsx` – author autocomplete → ego-network focus
- `dashboard/src/components/PartitionSelector.tsx` – quick-select for 5 pre-computed partitions

Data flow: GraphML (3108 nodes, 7487 edges) + 5 partition JSONs + pareto_results.csv → `network.json`, `pareto_results.json`, `partitions_meta.json`, `partitions/*.json` → served as static files.

Spring layout is pre-computed in Python (50 iterations). Pass `--skip-layout` for fast testing.
