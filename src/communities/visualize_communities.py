import pandas as pd
import json
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from collections import Counter

OUTPUT_DIR = "src/communities"


def load_data():
    df = pd.read_csv("data/DataWebMedia_IFB.csv", sep=";", quotechar='"')
    with open(f"{OUTPUT_DIR}/partition.json", "r", encoding="utf-8") as f:
        partition = json.load(f)
    # Attach community to each author row
    df["community"] = df["Autor"].map(partition)
    df = df[df["community"] != -1]  # drop isolated
    return df, partition


def top_n_communities(df, n=15):
    """Return the top N community IDs by number of distinct authors."""
    comm_sizes = df.groupby("community")["Autor"].nunique().sort_values(ascending=False)
    return comm_sizes.head(n).index.tolist()


# ── 1. Community composition by institution type (Tipo) ──────────────────────
def plot_community_by_tipo(df, top_comms):
    tipo_colors = {
        "UNIVERSIDADE PÚBLICA": "#e63946",
        "UNIVERSIDADE PRIVADA": "#457b9d",
        "INSTITUTO FEDERAL": "#2a9d8f",
        "OUTROS": "#6c757d",
    }
    pivot = (
        df[df["community"].isin(top_comms)]
        .drop_duplicates(subset=["Autor", "community"])
        .groupby(["community", "Tipo"])
        .size()
        .unstack(fill_value=0)
    )
    pivot = pivot.loc[top_comms]  # keep order

    fig, ax = plt.subplots(figsize=(14, 6))
    bottom = np.zeros(len(pivot))
    for tipo in pivot.columns:
        vals = pivot[tipo].values
        ax.bar(range(len(pivot)), vals, bottom=bottom,
               label=tipo, color=tipo_colors.get(tipo, "#aaa"))
        bottom += vals

    ax.set_xticks(range(len(pivot)))
    ax.set_xticklabels([f"C{c}" for c in pivot.index], rotation=45)
    ax.set_xlabel("Community")
    ax.set_ylabel("Number of authors")
    ax.set_title("Top 15 communities — composition by institution type")
    ax.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/communities_by_tipo.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/communities_by_tipo.png")
    plt.close()


# ── 2. Top affiliations per community (heatmap) ─────────────────────────────
def plot_affiliation_heatmap(df, top_comms):
    sub = df[df["community"].isin(top_comms)].drop_duplicates(subset=["Autor", "community"])
    # Top 20 affiliations overall
    top_afils = sub["Afiliação"].value_counts().head(20).index.tolist()
    pivot = (
        sub[sub["Afiliação"].isin(top_afils)]
        .groupby(["community", "Afiliação"])
        .size()
        .unstack(fill_value=0)
    )
    pivot = pivot.loc[[c for c in top_comms if c in pivot.index]]
    pivot = pivot[top_afils]

    fig, ax = plt.subplots(figsize=(16, 8))
    im = ax.imshow(pivot.values, aspect="auto", cmap="YlOrRd")
    ax.set_xticks(range(len(top_afils)))
    ax.set_xticklabels(top_afils, rotation=60, ha="right", fontsize=8)
    ax.set_yticks(range(len(pivot)))
    ax.set_yticklabels([f"C{c}" for c in pivot.index])
    ax.set_title("Authors per affiliation × community (top 15 communities, top 20 affiliations)")
    fig.colorbar(im, ax=ax, label="# authors")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/affiliation_heatmap.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/affiliation_heatmap.png")
    plt.close()


# ── 3. Community size distribution ──────────────────────────────────────────
def plot_community_sizes(df):
    sizes = df.groupby("community")["Autor"].nunique().sort_values(ascending=False)

    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Bar chart top 30
    top30 = sizes.head(30)
    axes[0].bar(range(len(top30)), top30.values, color="steelblue")
    axes[0].set_xticks(range(len(top30)))
    axes[0].set_xticklabels([f"C{c}" for c in top30.index], rotation=60, fontsize=7)
    axes[0].set_ylabel("Number of authors")
    axes[0].set_title("Top 30 communities by size")

    # Histogram of all community sizes
    axes[1].hist(sizes.values, bins=30, color="steelblue", edgecolor="white")
    axes[1].set_xlabel("Community size (authors)")
    axes[1].set_ylabel("Frequency")
    axes[1].set_title(f"Community size distribution (n={len(sizes)})")

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/community_sizes.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/community_sizes.png")
    plt.close()


# ── 4. Communities over time ────────────────────────────────────────────────
def plot_communities_over_time(df, top_comms):
    sub = df[df["community"].isin(top_comms[:10])]
    pivot = (
        sub.drop_duplicates(subset=["ID", "community"])
        .groupby(["Ano", "community"])
        .size()
        .unstack(fill_value=0)
    )

    fig, ax = plt.subplots(figsize=(14, 6))
    for comm in pivot.columns:
        ax.plot(pivot.index, pivot[comm], marker="o", markersize=4, label=f"C{comm}")
    ax.set_xlabel("Year")
    ax.set_ylabel("Number of papers")
    ax.set_title("Top 10 communities — papers per year")
    ax.legend(ncol=2, fontsize=8)
    ax.set_xticks(sorted(df["Ano"].unique()))
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/communities_over_time.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/communities_over_time.png")
    plt.close()


# ── 5. Inter-community collaboration (which communities share papers) ──────
def plot_intercommunity(df, top_comms):
    # A paper with authors in multiple communities = inter-community link
    sub = df.drop_duplicates(subset=["ID", "community"])
    paper_comms = sub.groupby("ID")["community"].apply(set)

    from itertools import combinations
    edge_counts = Counter()
    for comms in paper_comms:
        comms_in_top = comms & set(top_comms)
        for a, b in combinations(sorted(comms_in_top), 2):
            edge_counts[(a, b)] += 1

    if not edge_counts:
        print("No inter-community links found among top communities.")
        return

    import networkx as nx
    G = nx.Graph()
    for (a, b), w in edge_counts.items():
        G.add_edge(f"C{a}", f"C{b}", weight=w)

    fig, ax = plt.subplots(figsize=(10, 10))
    pos = nx.spring_layout(G, seed=42, k=1.5)
    weights = [G[u][v]["weight"] for u, v in G.edges()]
    max_w = max(weights)
    widths = [1 + 4 * w / max_w for w in weights]

    comm_sizes = df.groupby("community")["Autor"].nunique()
    node_sizes = [comm_sizes.get(int(n[1:]), 10) * 8 for n in G.nodes()]

    nx.draw_networkx_edges(G, pos, width=widths, alpha=0.5, ax=ax)
    nx.draw_networkx_nodes(G, pos, node_size=node_sizes, node_color="coral",
                           alpha=0.8, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=9, font_weight="bold", ax=ax)
    edge_labels = {(u, v): G[u][v]["weight"] for u, v in G.edges()}
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=7, ax=ax)

    ax.set_title("Inter-community collaboration (top 15 communities)")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/intercommunity.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/intercommunity.png")
    plt.close()


# ── 6. Top affiliations — community diversity ──────────────────────────────
def plot_affiliation_diversity(df):
    afil_comms = (
        df.drop_duplicates(subset=["Autor", "community"])
        .groupby("Afiliação")["community"]
        .nunique()
        .sort_values(ascending=False)
        .head(20)
    )

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.barh(range(len(afil_comms)), afil_comms.values, color="teal")
    ax.set_yticks(range(len(afil_comms)))
    ax.set_yticklabels(afil_comms.index)
    ax.invert_yaxis()
    ax.set_xlabel("Number of distinct communities")
    ax.set_title("Top 20 affiliations by community diversity")
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/affiliation_diversity.png", dpi=150)
    print(f"Saved: {OUTPUT_DIR}/affiliation_diversity.png")
    plt.close()


def main():
    df, partition = load_data()
    top_comms = top_n_communities(df, 15)
    print(f"Total authors with community: {df['Autor'].nunique()}")
    print(f"Top 15 communities: {top_comms}\n")

    plot_community_sizes(df)
    plot_community_by_tipo(df, top_comms)
    plot_affiliation_heatmap(df, top_comms)
    plot_communities_over_time(df, top_comms)
    plot_intercommunity(df, top_comms)
    plot_affiliation_diversity(df)


if __name__ == "__main__":
    main()
