"""
Pareto front analysis for HpMocd community detection.

Key advantage over Louvain/Leiden: instead of a single partition,
HpMocd produces a Pareto front of trade-off solutions (intra vs inter).
We can then use external qualitative attributes (region, institution type)
to pick the partition that best captures a particular structure.
"""

import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import json
from collections import Counter
from pymocd import HpMocd, fitness

OUTPUT_DIR = "src/communities"

# ── Brazilian state → region mapping ─────────────────────────────────────────
STATE_TO_REGION = {
    # Norte
    "AC": "Norte", "Acre": "Norte",
    "AM": "Norte", "Amazonas": "Norte",
    "AP": "Norte", "Amapá": "Norte",
    "PA": "Norte", "Pará": "Norte",
    "RO": "Norte", "Rondônia": "Norte",
    "RR": "Norte", "Roraima": "Norte",
    "TO": "Norte", "Tocantins": "Norte",
    # Nordeste
    "AL": "Nordeste", "Alagoas": "Nordeste",
    "BA": "Nordeste", "Bahia": "Nordeste",
    "CE": "Nordeste", "Ceará": "Nordeste",
    "MA": "Nordeste", "Maranhão": "Nordeste",
    "PB": "Nordeste", "Paraíba": "Nordeste",
    "PE": "Nordeste", "Pernambuco": "Nordeste",
    "PI": "Nordeste", "Piauí": "Nordeste",
    "RN": "Nordeste", "Rio Grande do Norte": "Nordeste",
    "SE": "Nordeste", "Sergipe": "Nordeste",
    # Centro-Oeste
    "DF": "Centro-Oeste", "Distrito Federal": "Centro-Oeste",
    "GO": "Centro-Oeste", "Goiás": "Centro-Oeste",
    "MS": "Centro-Oeste", "Mato Grosso do Sul": "Centro-Oeste",
    "MT": "Centro-Oeste", "Mato Grosso": "Centro-Oeste",
    # Sudeste
    "ES": "Sudeste", "Espírito Santo": "Sudeste",
    "MG": "Sudeste", "Minas Gerais": "Sudeste",
    "RJ": "Sudeste", "Rio de Janeiro": "Sudeste",
    "SP": "Sudeste", "São Paulo": "Sudeste",
    # Sul
    "PR": "Sul", "Paraná": "Sul",
    "RS": "Sul", "Rio Grande do Sul": "Sul",
    "SC": "Sul", "Santa Catarina": "Sul",
}


def extract_state(cidade):
    """Extract state abbreviation or name from city string."""
    if not isinstance(cidade, str):
        return None
    parts = [p.strip() for p in cidade.split(",")]
    # Check if it's a Brazilian city (contains "Brasil" or no country specified)
    is_brazil = any("Brasil" in p or "Brazil" in p for p in parts)
    # Also accept entries without country (assumed Brazil)
    has_foreign = any(
        k in cidade
        for k in [
            "Argentina", "Colômbia", "EUA", "Itália", "Alemanha",
            "Áustria", "Portugal", "França", "Espanha", "Chile",
            "México", "Canadá", "Inglaterra", "UK", "USA",
            "China", "Japan", "Japão", "Índia", "Holanda",
        ]
    )
    if has_foreign:
        return "Internacional"
    # Try to find state in the parts
    for part in parts:
        part = part.strip()
        if part in STATE_TO_REGION:
            return part
    return None


def get_region(state):
    if state is None:
        return "Desconhecido"
    if state == "Internacional":
        return "Internacional"
    return STATE_TO_REGION.get(state, "Desconhecido")


def compute_homogeneity(partition, author_attr):
    """
    Measures how homogeneous communities are w.r.t. an external attribute.
    Returns normalized mutual information-like score (0=random, 1=perfect alignment).
    Uses simple purity: avg fraction of dominant attribute per community.
    """
    comms = {}
    for author, comm in partition.items():
        if comm == -1:
            continue
        if author in author_attr:
            comms.setdefault(comm, []).append(author_attr[author])

    if not comms:
        return 0.0

    total = 0
    weighted_purity = 0.0
    for comm_id, attrs in comms.items():
        counts = Counter(attrs)
        majority = counts.most_common(1)[0][1]
        n = len(attrs)
        weighted_purity += majority
        total += n

    return weighted_purity / total if total > 0 else 0.0


def load_and_prepare():
    df = pd.read_csv("data/DataWebMedia_IFB.csv", sep=";", quotechar='"')

    # Build author → region
    df["state"] = df["Cidade"].apply(extract_state)
    df["region"] = df["state"].apply(get_region)

    # Most frequent region per author
    author_region = (
        df.groupby("Autor")["region"]
        .agg(lambda x: x.mode()[0])
        .to_dict()
    )
    # Most frequent tipo per author
    author_tipo = (
        df.groupby("Autor")["Tipo"]
        .agg(lambda x: x.mode()[0])
        .to_dict()
    )
    # Most frequent affiliation per author
    author_afil = (
        df.groupby("Autor")["Afiliação"]
        .agg(lambda x: x.mode()[0])
        .to_dict()
    )

    return df, author_region, author_tipo, author_afil


def build_int_graph(graphml_path):
    G = nx.read_graphml(graphml_path)
    node_list = list(G.nodes())
    label_to_int = {label: i for i, label in enumerate(node_list)}
    int_to_label = {i: label for label, i in label_to_int.items()}

    G_int = nx.Graph()
    G_int.add_nodes_from(range(len(node_list)))
    for u, v, data in G.edges(data=True):
        G_int.add_edge(
            label_to_int[u], label_to_int[v],
            weight=float(data.get("weight", 1.0)),
        )
    return G_int, int_to_label


def main():
    df, author_region, author_tipo, author_afil = load_and_prepare()
    G_int, int_to_label = build_int_graph("data/coauthorship_network.graphml")

    print(f"Graph: {G_int.number_of_nodes()} nodes, {G_int.number_of_edges()} edges")

    # Generate Pareto front
    alg = HpMocd(
        graph=G_int,
        debug_level=1,
        pop_size=1000,
        num_gens=1000,
        cross_rate=0.8,
        mut_rate=0.2,
    )
    frontier = alg.generate_pareto_front()
    print(f"Pareto front size: {len(frontier)} solutions\n")

    # Evaluate each solution
    results = []
    for idx, (labels, (intra, inter)) in enumerate(frontier):
        partition = {int_to_label[node]: comm for node, comm in labels.items()}
        n_comms = len(set(c for c in partition.values() if c != -1))

        region_purity = compute_homogeneity(partition, author_region)
        tipo_purity = compute_homogeneity(partition, author_tipo)
        afil_purity = compute_homogeneity(partition, author_afil)
        q = fitness(G_int, labels)

        results.append({
            "idx": idx,
            "intra": intra,
            "inter": inter,
            "q_score": q,
            "n_communities": n_comms,
            "region_purity": region_purity,
            "tipo_purity": tipo_purity,
            "affiliation_purity": afil_purity,
        })

    res_df = pd.DataFrame(results)
    res_df.to_csv(f"{OUTPUT_DIR}/pareto_results.csv", index=False)
    print(res_df.describe().to_string())

    # ── Find best solutions for each criterion ───────────────────────────
    best_region = res_df.loc[res_df["region_purity"].idxmax()]
    best_tipo = res_df.loc[res_df["tipo_purity"].idxmax()]
    best_afil = res_df.loc[res_df["affiliation_purity"].idxmax()]
    best_q = res_df.loc[res_df["q_score"].idxmax()]

    print("\n── Best partition per criterion ──")
    for name, row in [
        ("Region", best_region),
        ("Inst. type", best_tipo),
        ("Affiliation", best_afil),
        ("Modularity Q", best_q),
    ]:
        print(
            f"  {name:15s}: idx={int(row['idx']):3d}, "
            f"Q={row['q_score']:.4f}, "
            f"comms={int(row['n_communities']):3d}, "
            f"region={row['region_purity']:.4f}, "
            f"tipo={row['tipo_purity']:.4f}, "
            f"afil={row['affiliation_purity']:.4f}"
        )

    # Save the best partitions
    for crit_name, best_row in [
        ("region", best_region),
        ("tipo", best_tipo),
        ("affiliation", best_afil),
        ("modularity", best_q),
    ]:
        idx = int(best_row["idx"])
        labels, _ = frontier[idx]
        partition = {int_to_label[n]: int(c) for n, c in labels.items()}
        with open(f"{OUTPUT_DIR}/partition_best_{crit_name}.json", "w", encoding="utf-8") as f:
            json.dump(partition, f, ensure_ascii=False, indent=2)

    # ── Plot 1: Pareto front colored by region purity ────────────────────
    fig, axes = plt.subplots(1, 3, figsize=(20, 6))

    for ax, metric, label, cmap_name in [
        (axes[0], "region_purity", "Region purity", "RdYlGn"),
        (axes[1], "tipo_purity", "Institution type purity", "RdYlBu"),
        (axes[2], "affiliation_purity", "Affiliation purity", "plasma"),
    ]:
        sc = ax.scatter(
            res_df["intra"], res_df["inter"],
            c=res_df[metric], cmap=cmap_name,
            s=40, alpha=0.8, edgecolors="k", linewidths=0.3,
        )
        fig.colorbar(sc, ax=ax, label=label)
        ax.set_xlabel("Intra-community score")
        ax.set_ylabel("Inter-community score")
        ax.set_title(f"Pareto front — {label}")

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/pareto_front_purity.png", dpi=150)
    print(f"\nSaved: {OUTPUT_DIR}/pareto_front_purity.png")
    plt.close()

    # ── Plot 2: Pareto front — Q score and num communities ───────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    sc = axes[0].scatter(
        res_df["intra"], res_df["inter"],
        c=res_df["q_score"], cmap="viridis",
        s=40, alpha=0.8, edgecolors="k", linewidths=0.3,
    )
    fig.colorbar(sc, ax=axes[0], label="Modularity Q")
    axes[0].set_xlabel("Intra-community score")
    axes[0].set_ylabel("Inter-community score")
    axes[0].set_title("Pareto front — Modularity Q")

    sc = axes[1].scatter(
        res_df["intra"], res_df["inter"],
        c=res_df["n_communities"], cmap="coolwarm",
        s=40, alpha=0.8, edgecolors="k", linewidths=0.3,
    )
    fig.colorbar(sc, ax=axes[1], label="# Communities")
    axes[1].set_xlabel("Intra-community score")
    axes[1].set_ylabel("Inter-community score")
    axes[1].set_title("Pareto front — Number of communities")

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/pareto_front_metrics.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/pareto_front_metrics.png")
    plt.close()

    # ── Plot 3: Best region partition — community composition by region ──
    best_idx = int(best_region["idx"])
    labels_best, _ = frontier[best_idx]
    partition_best = {int_to_label[n]: c for n, c in labels_best.items()}

    comms_region = {}
    for author, comm in partition_best.items():
        if comm == -1:
            continue
        region = author_region.get(author, "Desconhecido")
        comms_region.setdefault(comm, []).append(region)

    # Top 15 communities by size
    comm_sizes = sorted(comms_region.items(), key=lambda x: len(x[1]), reverse=True)[:15]
    comm_ids = [c for c, _ in comm_sizes]

    region_order = ["Sudeste", "Nordeste", "Sul", "Norte", "Centro-Oeste", "Internacional", "Desconhecido"]
    region_colors = {
        "Sudeste": "#e63946",
        "Nordeste": "#f4a261",
        "Sul": "#2a9d8f",
        "Norte": "#264653",
        "Centro-Oeste": "#e9c46a",
        "Internacional": "#6c757d",
        "Desconhecido": "#dee2e6",
    }

    fig, ax = plt.subplots(figsize=(14, 6))
    bottom = np.zeros(len(comm_ids))
    for region in region_order:
        vals = []
        for c in comm_ids:
            vals.append(Counter(comms_region[c]).get(region, 0))
        vals = np.array(vals)
        ax.bar(range(len(comm_ids)), vals, bottom=bottom,
               label=region, color=region_colors[region])
        bottom += vals

    ax.set_xticks(range(len(comm_ids)))
    ax.set_xticklabels([f"C{c}" for c in comm_ids], rotation=45)
    ax.set_xlabel("Community")
    ax.set_ylabel("Number of authors")
    ax.set_title("Best region-aligned partition — community composition by Brazilian region")
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/pareto_best_region.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/pareto_best_region.png")
    plt.close()

    # ── Plot 4: Comparison bar — purity across criteria for key solutions ─
    solutions = {
        "Best Region": best_region,
        "Best Inst. Type": best_tipo,
        "Best Affiliation": best_afil,
        "Best Modularity": best_q,
    }
    metrics = ["region_purity", "tipo_purity", "affiliation_purity", "q_score"]
    metric_labels = ["Region", "Inst. Type", "Affiliation", "Modularity Q"]

    fig, ax = plt.subplots(figsize=(12, 6))
    x = np.arange(len(solutions))
    width = 0.2
    colors = ["#e63946", "#457b9d", "#2a9d8f", "#6c757d"]

    for i, (m, ml) in enumerate(zip(metrics, metric_labels)):
        vals = [sol[m] for sol in solutions.values()]
        ax.bar(x + i * width, vals, width, label=ml, color=colors[i])

    ax.set_xticks(x + 1.5 * width)
    ax.set_xticklabels(solutions.keys())
    ax.set_ylabel("Score")
    ax.set_title("Pareto solutions — purity comparison across criteria")
    ax.legend()
    ax.set_ylim(0, 1.05)
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/pareto_comparison.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/pareto_comparison.png")
    plt.close()


if __name__ == "__main__":
    main()
