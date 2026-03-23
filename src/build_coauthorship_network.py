import pandas as pd
import networkx as nx
from itertools import combinations
import matplotlib.pyplot as plt


def build_coauthorship_network(csv_path):
    df = pd.read_csv(csv_path, sep=";", quotechar='"', encoding="utf-8")

    # Group authors by paper ID to find co-authors
    papers = df.groupby("ID")["Autor"].apply(list).reset_index()

    G = nx.Graph()

    for _, row in papers.iterrows():
        authors = list(set(row["Autor"]))  # deduplicate within same paper
        # Add nodes
        for author in authors:
            if G.has_node(author):
                G.nodes[author]["papers"] += 1
            else:
                G.add_node(author, papers=1)

        # Add edges between all co-author pairs
        for a1, a2 in combinations(authors, 2):
            if G.has_edge(a1, a2):
                G[a1][a2]["weight"] += 1
            else:
                G.add_edge(a1, a2, weight=1)

    print(f"Nodes (authors): {G.number_of_nodes()}")
    print(f"Edges (co-authorships): {G.number_of_edges()}")
    print(f"Connected components: {nx.number_connected_components(G)}")

    # Add affiliation info to nodes (take the most frequent affiliation per author)
    affiliations = df.groupby("Autor")["Afiliação"].agg(lambda x: x.mode()[0])
    nx.set_node_attributes(G, affiliations.to_dict(), "affiliation")

    return G


def main():
    G = build_coauthorship_network("data/DataWebMedia_IFB.csv")

    # Save as GraphML for later use with pymocd or other tools
    nx.write_graphml(G, "data/coauthorship_network.graphml")
    print("Saved: data/coauthorship_network.graphml")

    # Save edgelist (simpler format)
    nx.write_weighted_edgelist(G, "data/coauthorship_network.edgelist")
    print("Saved: data/coauthorship_network.edgelist")

    # Basic visualization
    largest_cc = max(nx.connected_components(G), key=len)
    subG = G.subgraph(largest_cc)
    print(f"Largest component: {subG.number_of_nodes()} nodes, {subG.number_of_edges()} edges")

    fig, ax = plt.subplots(figsize=(16, 12))
    pos = nx.spring_layout(subG, k=0.3, seed=42)
    weights = [subG[u][v]["weight"] for u, v in subG.edges()]
    degrees = dict(subG.degree())
    node_sizes = [degrees[n] * 10 for n in subG.nodes()]

    nx.draw_networkx_edges(subG, pos, alpha=0.2, width=weights, ax=ax)
    nx.draw_networkx_nodes(subG, pos, node_size=node_sizes, alpha=0.7,
                           node_color="steelblue", ax=ax)
    # Label only high-degree nodes
    top_authors = {n: n for n, d in degrees.items() if d >= 10}
    nx.draw_networkx_labels(subG, pos, labels=top_authors, font_size=6, ax=ax)

    ax.set_title("WebMedia Co-authorship Network (largest component)")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig("data/coauthorship_network.png", dpi=150)
    print("Saved: data/coauthorship_network.png")
    plt.close()


if __name__ == "__main__":
    main()
