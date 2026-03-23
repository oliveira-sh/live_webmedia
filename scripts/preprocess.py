#!/usr/bin/env python3
"""
Preprocess HPMOCD data for the web dashboard.
Outputs JSON files to dashboard/public/data/
"""

import json
import csv
import os
import xml.etree.ElementTree as ET
import shutil
import math
import argparse
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
SRC_DIR  = BASE_DIR / "src" / "communities"
OUT_DIR  = BASE_DIR / "dashboard" / "public" / "data"

# ── helpers ────────────────────────────────────────────────────────────────────

STATE_TO_REGION = {
    "Acre": "Norte", "Amapá": "Norte", "Amazonas": "Norte",
    "Pará": "Norte", "Rondônia": "Norte", "Roraima": "Norte", "Tocantins": "Norte",
    "Alagoas": "Nordeste", "Bahia": "Nordeste", "Ceará": "Nordeste",
    "Maranhão": "Nordeste", "Paraíba": "Nordeste", "Pernambuco": "Nordeste",
    "Piauí": "Nordeste", "Rio Grande do Norte": "Nordeste", "Sergipe": "Nordeste",
    "Espírito Santo": "Sudeste", "Minas Gerais": "Sudeste",
    "Rio de Janeiro": "Sudeste", "São Paulo": "Sudeste",
    "Paraná": "Sul", "Rio Grande do Sul": "Sul", "Santa Catarina": "Sul",
    "Distrito Federal": "Centro-Oeste", "Goiás": "Centro-Oeste",
    "Mato Grosso": "Centro-Oeste", "Mato Grosso do Sul": "Centro-Oeste",
}

def extract_region(cidade: str) -> str:
    for state, region in STATE_TO_REGION.items():
        if state in cidade:
            return region
    return "Unknown"


# ── GraphML parsing ────────────────────────────────────────────────────────────

def parse_graphml():
    print("Parsing GraphML …")
    tree = ET.parse(DATA_DIR / "coauthorship_network.graphml")
    root = tree.getroot()

    # Detect namespace from root tag, e.g. {http://graphml.graphdrawing.org/xmlns}graphml
    tag = root.tag
    ns_uri = tag[1:tag.index("}")] if tag.startswith("{") else ""
    ns = {"g": ns_uri} if ns_uri else {}

    def find_all(el: ET.Element, local: str):
        if ns_uri:
            return el.findall(f"g:{local}", ns)
        return el.findall(local)

    def find_one(el: ET.Element, local: str):
        if ns_uri:
            return el.find(f"g:{local}", ns)
        return el.find(local)

    key_map = {}          # id → attr.name
    for key in find_all(root, "key"):
        key_map[key.get("id")] = key.get("attr.name")

    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    graph = find_one(root, "graph")

    if graph is None:
        raise RuntimeError("Could not find <graph> element in GraphML file.")

    for node_el in find_all(graph, "node"):
        nid = node_el.get("id")
        attrs = {key_map.get(d.get("key"), d.get("key")): d.text
                 for d in find_all(node_el, "data")}
        nodes[nid] = {
            "id": nid,
            "papers": int(attrs.get("papers", 1) or 1),
            "affiliation": (attrs.get("affiliation") or "Unknown").strip() or "Unknown",
        }

    for edge_el in find_all(graph, "edge"):
        src = edge_el.get("source")
        tgt = edge_el.get("target")
        attrs = {key_map.get(d.get("key"), d.get("key")): d.text
                 for d in find_all(edge_el, "data")}
        edges.append({
            "source": src,
            "target": tgt,
            "weight": float(attrs.get("weight", 1) or 1),
        })

    print(f"  {len(nodes)} nodes, {len(edges)} edges")
    return nodes, edges


# ── Metadata enrichment ────────────────────────────────────────────────────────

def enrich_with_metadata(nodes: dict) -> dict:
    print("Enriching nodes with author metadata …")
    author_meta: dict[str, dict] = {}

    with open(DATA_DIR / "DataWebMedia_IFB.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f, delimiter=";")
        for row in reader:
            author = (row.get("Autor") or "").strip()
            if not author:
                continue
            if author not in author_meta:
                author_meta[author] = {
                    "tipo": (row.get("Tipo") or "").strip(),
                    "cidade": (row.get("Cidade") or "").strip(),
                }

    enriched = 0
    for nid, node in nodes.items():
        meta = author_meta.get(nid, {})
        node["tipo"]   = meta.get("tipo", "Unknown") or "Unknown"
        node["cidade"] = meta.get("cidade", "") or ""
        node["region"] = extract_region(node["cidade"])
        if meta:
            enriched += 1

    print(f"  Enriched {enriched}/{len(nodes)} nodes with metadata")
    return nodes


# ── Layout ─────────────────────────────────────────────────────────────────────

def _fruchterman_reingold(node_ids: list, adj_weights: dict,
                           iterations: int, k: float, seed: int = 42) -> dict:
    """Fruchterman-Reingold spring layout implemented with stdlib only.
    O(n²) per iteration – suitable for the community-level graph (~100-800 nodes).
    adj_weights: {node_id: {neighbor_id: weight, ...}}
    Returns: {node_id: [x, y]}
    """
    import random
    rng = random.Random(seed)
    n = len(node_ids)
    if n == 0:
        return {}
    if n == 1:
        return {node_ids[0]: [0.0, 0.0]}

    pos = {nid: [rng.uniform(-1.0, 1.0), rng.uniform(-1.0, 1.0)]
           for nid in node_ids}

    temp = 1.0
    cool = temp / (iterations + 1)

    for _ in range(iterations):
        disp = {nid: [0.0, 0.0] for nid in node_ids}

        # repulsive forces (all pairs)
        for i in range(n):
            v = node_ids[i]
            pv = pos[v]
            for j in range(i + 1, n):
                u = node_ids[j]
                pu = pos[u]
                dx, dy = pv[0] - pu[0], pv[1] - pu[1]
                dist = math.sqrt(dx * dx + dy * dy) or 1e-6
                rep = k * k / dist
                nx_, ny_ = dx / dist * rep, dy / dist * rep
                disp[v][0] += nx_;  disp[v][1] += ny_
                disp[u][0] -= nx_;  disp[u][1] -= ny_

        # attractive forces (edges)
        for v, neighbours in adj_weights.items():
            pv = pos[v]
            for u, w in neighbours.items():
                pu = pos[u]
                dx, dy = pv[0] - pu[0], pv[1] - pu[1]
                dist = math.sqrt(dx * dx + dy * dy) or 1e-6
                att = dist * dist / k * w
                nx_, ny_ = dx / dist * att, dy / dist * att
                disp[v][0] -= nx_;  disp[v][1] -= ny_

        # apply capped by temperature
        for nid in node_ids:
            dx, dy = disp[nid]
            d = math.sqrt(dx * dx + dy * dy) or 1e-6
            scale = min(d, temp) / d
            pos[nid][0] += dx * scale
            pos[nid][1] += dy * scale

        temp -= cool

    return pos


def compute_community_layout(nodes: dict, edges: list, partition: dict,
                              iterations: int = 50) -> dict:
    """Two-level layout:
    1. Fruchterman-Reingold on the community graph (no external deps needed).
    2. Phyllotaxis (sunflower) spiral to pack nodes within each cluster.

    Uses networkx if available for a faster level-1 layout; falls back to the
    pure-stdlib implementation otherwise.
    """
    print(f"Computing community-aware two-level layout (iterations={iterations}) …")

    # ── group nodes by community ───────────────────────────────────────────────
    community_members: dict[int, list] = {}
    for nid in nodes:
        cid = partition.get(nid, -1)
        community_members.setdefault(cid, []).append(nid)

    for members in community_members.values():
        members.sort()

    non_isolated = {c: m for c, m in community_members.items() if c != -1}
    isolated     = community_members.get(-1, [])
    n_comm       = len(non_isolated)
    print(f"  {n_comm} communities, {len(isolated)} isolated nodes")

    if n_comm == 0:
        import random
        rng = random.Random(42)
        for node in nodes.values():
            node["x"] = rng.uniform(-1, 1)
            node["y"] = rng.uniform(-1, 1)
        return nodes

    # ── level-1: layout of community centroids ────────────────────────────────
    # Build inter-community adjacency (weighted by edge count)
    comm_adj: dict[int, dict[int, float]] = {c: {} for c in non_isolated}
    for e in edges:
        c1 = partition.get(e["source"], -1)
        c2 = partition.get(e["target"], -1)
        if c1 != -1 and c2 != -1 and c1 != c2:
            comm_adj[c1][c2] = comm_adj[c1].get(c2, 0.0) + e["weight"]
            comm_adj[c2][c1] = comm_adj[c2].get(c1, 0.0) + e["weight"]

    comm_ids = list(non_isolated.keys())
    k_comm   = 2.0 / math.sqrt(max(n_comm, 1))

    try:
        import networkx as nx
        CG = nx.Graph()
        CG.add_nodes_from(comm_ids)
        for c1, neighbours in comm_adj.items():
            for c2, w in neighbours.items():
                if c1 < c2:
                    CG.add_edge(c1, c2, weight=w)
        raw = nx.spring_layout(CG, k=k_comm, iterations=iterations,
                               weight="weight", seed=42)
        comm_pos = {c: list(p) for c, p in raw.items()}
        print("  (using networkx for community-level spring layout)")
    except ImportError:
        comm_pos = _fruchterman_reingold(
            comm_ids, comm_adj, iterations=iterations, k=k_comm)

    # ── level-2: phyllotaxis spiral inside each community ─────────────────────
    max_size     = max(len(m) for m in non_isolated.values())
    cluster_scale = 0.65 / math.sqrt(max(n_comm, 1))
    golden_angle  = math.pi * (3.0 - math.sqrt(5.0))   # ≈ 137.5°

    final_pos: dict[str, tuple] = {}

    for cid, members in non_isolated.items():
        cx, cy = comm_pos[cid]
        n      = len(members)
        r_max  = cluster_scale * math.sqrt(n) / math.sqrt(max_size)

        for i, nid in enumerate(members):
            if n == 1:
                final_pos[nid] = (cx, cy)
            else:
                r     = r_max * math.sqrt((i + 0.5) / n)
                theta = golden_angle * i
                final_pos[nid] = (cx + r * math.cos(theta),
                                  cy + r * math.sin(theta))

    # isolated nodes in a ring at the periphery
    for i, nid in enumerate(isolated):
        theta = 2 * math.pi * i / max(len(isolated), 1)
        final_pos[nid] = (1.6 * math.cos(theta), 1.6 * math.sin(theta))

    # ── normalise to [-1, 1] ──────────────────────────────────────────────────
    all_x  = [p[0] for p in final_pos.values()]
    all_y  = [p[1] for p in final_pos.values()]
    min_x, max_x = min(all_x), max(all_x)
    min_y, max_y = min(all_y), max(all_y)
    span_x = max_x - min_x or 1
    span_y = max_y - min_y or 1

    for nid, (x, y) in final_pos.items():
        if nid in nodes:
            nodes[nid]["x"] = round((x - min_x) / span_x * 2 - 1, 5)
            nodes[nid]["y"] = round((y - min_y) / span_y * 2 - 1, 5)

    print("  Layout done.")
    return nodes


def compute_layout(nodes: dict, edges: list, iterations: int = 50) -> dict:
    """Flat spring layout (fallback when no partition is available)."""
    try:
        import networkx as nx
        print(f"Computing spring layout with NetworkX (iterations={iterations}) …")
        G = nx.Graph()
        G.add_nodes_from(nodes.keys())
        for e in edges:
            G.add_edge(e["source"], e["target"], weight=e["weight"])

        k   = 2.0 / math.sqrt(len(G))
        pos = nx.spring_layout(G, k=k, iterations=iterations, seed=42)

        xs = [p[0] for p in pos.values()]
        ys = [p[1] for p in pos.values()]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max_x - min_x or 1
        span_y = max_y - min_y or 1

        for nid, (x, y) in pos.items():
            if nid in nodes:
                nodes[nid]["x"] = round((x - min_x) / span_x * 2 - 1, 5)
                nodes[nid]["y"] = round((y - min_y) / span_y * 2 - 1, 5)
        print("  Layout done.")
    except ImportError:
        print("  NetworkX not found – assigning random positions.")
        import random
        rng = random.Random(42)
        for node in nodes.values():
            node["x"] = rng.uniform(-1, 1)
            node["y"] = rng.uniform(-1, 1)
    return nodes


# ── Pareto results ─────────────────────────────────────────────────────────────

def load_pareto_results() -> list[dict]:
    print("Loading pareto_results.csv …")
    results = []
    with open(SRC_DIR / "pareto_results.csv") as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                "idx":                int(row["idx"]),
                "intra":              float(row["intra"]),
                "inter":              float(row["inter"]),
                "q_score":            float(row["q_score"]),
                "n_communities":      int(row["n_communities"]),
                "region_purity":      float(row["region_purity"]),
                "tipo_purity":        float(row["tipo_purity"]),
                "affiliation_purity": float(row["affiliation_purity"]),
                "partition_key":      None,
            })
    print(f"  {len(results)} solutions loaded")
    return results


# ── Partition helpers ──────────────────────────────────────────────────────────

PARTITION_DEFS = [
    # (key,                      filename,                          opt_metric,           label)
    ("partition_best_modularity",    "partition_best_modularity.json",    "q_score",            "Best Modularity"),
    ("partition_best_region",        "partition_best_region.json",        "region_purity",      "Best Region Purity"),
    ("partition_best_tipo",          "partition_best_tipo.json",          "tipo_purity",        "Best Type Purity"),
    ("partition_best_affiliation",   "partition_best_affiliation.json",   "affiliation_purity", "Best Affiliation Purity"),
    ("partition_default",            "partition.json",                     None,                 "Default"),
]


def load_partition(filename: str) -> dict:
    with open(SRC_DIR / filename) as f:
        return json.load(f)


def find_best_idx(results: list[dict], metric: str) -> int:
    return max(results, key=lambda r: r[metric])["idx"]


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-layout", action="store_true",
                        help="Use random positions instead of computing spring layout")
    parser.add_argument("--layout-iterations", type=int, default=50)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "partitions").mkdir(exist_ok=True)

    # Network
    nodes, edges = parse_graphml()
    nodes = enrich_with_metadata(nodes)

    if not args.skip_layout:
        # Prefer community-aware layout using the best-modularity partition
        layout_partition_file = SRC_DIR / "partition_best_modularity.json"
        if layout_partition_file.exists():
            with open(layout_partition_file) as f:
                layout_partition = json.load(f)
            nodes = compute_community_layout(nodes, edges, layout_partition,
                                             iterations=args.layout_iterations)
        else:
            print("No partition found – falling back to flat spring layout.")
            nodes = compute_layout(nodes, edges, iterations=args.layout_iterations)
    else:
        print("Skipping layout computation – using random positions.")
        import random
        rng = random.Random(42)
        for node in nodes.values():
            node["x"] = rng.uniform(-1, 1)
            node["y"] = rng.uniform(-1, 1)

    network_path = OUT_DIR / "network.json"
    print(f"Saving {network_path} …")
    with open(network_path, "w") as f:
        json.dump({"nodes": list(nodes.values()), "edges": edges}, f, separators=(",", ":"))
    size_mb = network_path.stat().st_size / 1_048_576
    print(f"  Saved ({size_mb:.1f} MB)")

    # Pareto results
    pareto_results = load_pareto_results()

    # Partitions
    partitions_meta = {}
    for key, filename, metric, label in PARTITION_DEFS:
        src = SRC_DIR / filename
        if not src.exists():
            print(f"  Skipping {filename} (not found)")
            continue

        dst = OUT_DIR / "partitions" / filename
        shutil.copy(src, dst)

        partition = load_partition(filename)
        community_ids = [v for v in partition.values() if v != -1]
        n_communities = len(set(community_ids))

        if metric:
            idx = find_best_idx(pareto_results, metric)
            for r in pareto_results:
                if r["idx"] == idx:
                    r["partition_key"] = key
                    break
        else:
            idx = pareto_results[0]["idx"]

        partitions_meta[key] = {
            "key":           key,
            "filename":      filename,
            "label":         label,
            "idx":           idx,
            "n_communities": n_communities,
        }
        print(f"  {label}: {n_communities} communities  →  {dst.name}")

    print("Saving pareto_results.json …")
    with open(OUT_DIR / "pareto_results.json", "w") as f:
        json.dump(pareto_results, f, separators=(",", ":"))

    print("Saving partitions_meta.json …")
    with open(OUT_DIR / "partitions_meta.json", "w") as f:
        json.dump(partitions_meta, f, indent=2)

    print("\n✓ Preprocessing complete. Data written to:", OUT_DIR)


if __name__ == "__main__":
    main()
