import networkx as nx
from pymocd import HpMocd, fitness
import matplotlib.pyplot as plt
import json
import csv


def detect_communities(graphml_path, pop_size=1000, num_gens=1000):
    G = nx.read_graphml(graphml_path)

    # HpMocd expects integer-labeled nodes; build a mapping
    node_list = list(G.nodes())
    label_to_int = {label: i for i, label in enumerate(node_list)}
    int_to_label = {i: label for label, i in label_to_int.items()}

    # Build integer-labeled graph preserving weights
    G_int = nx.Graph()
    G_int.add_nodes_from(range(len(node_list)))
    for u, v, data in G.edges(data=True):
        G_int.add_edge(
            label_to_int[u], label_to_int[v], weight=float(data.get("weight", 1.0))
        )

    print(f"Graph: {G_int.number_of_nodes()} nodes, {G_int.number_of_edges()} edges")

    # Run HpMocd
    detector = HpMocd(G_int, pop_size=pop_size, num_gens=num_gens, debug_level=3)
    partition = detector.run()

    # Map back to original labels
    partition_labeled = {int_to_label[node]: comm for node, comm in partition.items()}

    # Stats
    communities = {}
    for author, comm_id in partition_labeled.items():
        communities.setdefault(comm_id, []).append(author)

    # Filter out isolated nodes (community -1)
    valid = {k: v for k, v in communities.items() if k != -1}
    print(f"Communities found: {len(valid)}")
    print(f"Isolated nodes (degree=0): {len(communities.get(-1, []))}")

    q_score = fitness(G_int, partition)
    print(f"Modularity (Q): {q_score:.4f}")

    # Top 10 communities by size
    top = sorted(valid.items(), key=lambda x: len(x[1]), reverse=True)[:10]
    print("\nTop 10 communities by size:")
    for comm_id, members in top:
        print(f"  Community {comm_id}: {len(members)} authors")

    return G, partition_labeled, communities


def save_results(partition_labeled, communities, output_dir):
    # Save partition as JSON
    with open(f"{output_dir}/partition.json", "w", encoding="utf-8") as f:
        json.dump(partition_labeled, f, ensure_ascii=False, indent=2)
    print(f"Saved: {output_dir}/partition.json")

    # Save communities as CSV
    with open(f"{output_dir}/communities.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["author", "community_id"])
        for author, comm in sorted(partition_labeled.items(), key=lambda x: x[1]):
            writer.writerow([author, comm])
    print(f"Saved: {output_dir}/communities.csv")


def visualize(G, partition_labeled, output_dir):
    # Largest component for visualization
    largest_cc = max(nx.connected_components(G), key=len)
    subG = G.subgraph(largest_cc).copy()

    # Assign community colors using random distinct hues
    import random

    rng = random.Random(42)
    sub_comms = set(partition_labeled.get(n, -1) for n in subG.nodes()) - {-1}
    hues = {c: rng.random() for c in sub_comms}

    import colorsys

    node_colors = []
    for n in subG.nodes():
        c = partition_labeled.get(n, -1)
        if c == -1:
            node_colors.append("lightgray")
        else:
            h = hues[c]
            rgb = colorsys.hsv_to_rgb(h, 0.7, 0.9)
            node_colors.append(rgb)

    degrees = dict(subG.degree())
    node_sizes = [degrees[n] * 10 for n in subG.nodes()]

    fig, ax = plt.subplots(figsize=(18, 14))
    pos = nx.spring_layout(subG, k=0.3, seed=42)
    nx.draw_networkx_edges(subG, pos, alpha=0.15, ax=ax)
    nx.draw_networkx_nodes(
        subG, pos, node_size=node_sizes, alpha=0.8, node_color=node_colors, ax=ax
    )

    ax.set_title("WebMedia Co-authorship Network — HpMocd Communities")
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(f"{output_dir}/communities_network.png", dpi=150)
    print(f"Saved: {output_dir}/communities_network.png")
    plt.close()


def main():
    graphml_path = "data/coauthorship_network.graphml"
    output_dir = "src/communities"

    G, partition_labeled, communities = detect_communities(graphml_path)
    save_results(partition_labeled, communities, output_dir)
    visualize(G, partition_labeled, output_dir)


if __name__ == "__main__":
    main()
