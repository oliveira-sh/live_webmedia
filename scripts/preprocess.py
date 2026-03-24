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

def compute_layout(nodes: dict, edges: list, iterations: int = 50) -> dict:
    import networkx as nx
    print(f"Computing spring layout (iterations={iterations}) …")
    G = nx.Graph()
    G.add_nodes_from(nodes.keys())
    for e in edges:
        G.add_edge(e["source"], e["target"], weight=e["weight"])

    pos = nx.spring_layout(G, iterations=iterations, seed=42)

    for nid, (x, y) in pos.items():
        if nid in nodes:
            nodes[nid]["x"] = round(float(x), 5)
            nodes[nid]["y"] = round(float(y), 5)
    print("  Layout done.")
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
        nodes = compute_layout(nodes, edges, iterations=args.layout_iterations)
    else:
        print("Skipping layout – using random positions.")
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
