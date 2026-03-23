// ─── Network data ──────────────────────────────────────────────────────────────

export interface NetworkNode {
  id: string;          // author name
  papers: number;
  affiliation: string;
  tipo: string;        // UNIVERSIDADE PÚBLICA | PRIVADA | INSTITUTO FEDERAL | OUTROS
  cidade: string;
  region: string;      // Norte | Nordeste | Sudeste | Sul | Centro-Oeste | Unknown
  x: number;          // pre-computed position [-1, 1]
  y: number;
}

export interface NetworkEdge {
  source: string;
  target: string;
  weight: number;
}

export interface NetworkData {
  nodes: NetworkNode[];
  edges: NetworkEdge[];
}

// ─── Pareto solutions ──────────────────────────────────────────────────────────

export type MetricKey =
  | "intra"
  | "inter"
  | "q_score"
  | "n_communities"
  | "region_purity"
  | "tipo_purity"
  | "affiliation_purity";

export interface ParetoSolution {
  idx: number;
  intra: number;
  inter: number;
  q_score: number;
  n_communities: number;
  region_purity: number;
  tipo_purity: number;
  affiliation_purity: number;
  partition_key: string | null;
}

// ─── Partitions ────────────────────────────────────────────────────────────────

export type PartitionData = Record<string, number>; // author → community_id

export interface PartitionMeta {
  key: string;
  filename: string;
  label: string;
  idx: number;
  n_communities: number;
}

export type PartitionsMeta = Record<string, PartitionMeta>;

// ─── UI state ──────────────────────────────────────────────────────────────────

export const METRIC_LABELS: Record<MetricKey, string> = {
  intra:              "Intra-community",
  inter:              "Inter-community",
  q_score:            "Modularity (Q)",
  n_communities:      "# Communities",
  region_purity:      "Region Purity",
  tipo_purity:        "Type Purity",
  affiliation_purity: "Affiliation Purity",
};

export const METRIC_KEYS: MetricKey[] = [
  "intra", "inter", "q_score", "region_purity", "tipo_purity", "affiliation_purity",
];

export const METRIC_DESCRIPTIONS: Record<MetricKey, string> = {
  intra:
    "Fraction of possible edges that exist within communities. " +
    "Higher means denser, more cohesive groups.",
  inter:
    "Fraction of edges that cross community boundaries. " +
    "Lower means communities are better separated from each other.",
  q_score:
    "Newman–Girvan modularity. Compares internal edge density to what " +
    "would be expected at random. Values above 0.3 are typically considered good.",
  n_communities:
    "Total number of communities found by this Pareto solution.",
  region_purity:
    "How often co-authors within the same community share the same " +
    "Brazilian geographic region (Norte, Nordeste, Sudeste, Sul, Centro-Oeste). " +
    "Higher means geographically cohesive collaboration clusters.",
  tipo_purity:
    "How often co-authors in the same community belong to the same " +
    "institution type (public university, private university, federal institute, etc.). " +
    "Higher means institutionally homogeneous groups.",
  affiliation_purity:
    "How often co-authors in the same community share the exact same " +
    "institution (e.g. USP, UFMG, UFPE). Higher means the algorithm found " +
    "tight intra-institution collaboration clusters.",
};

// Palette shared between UniversityFilter badges and NetworkGraph node borders
export const AFFIL_PALETTE = [
  "#f59e0b", "#ec4899", "#10b981", "#3b82f6", "#ef4444",
  "#8b5cf6", "#06b6d4", "#84cc16", "#f97316", "#e879f9",
];

/** Returns a stable color → affiliation mapping sorted alphabetically. */
export function buildAffilColorMap(selected: Set<string>): Map<string, string> {
  const sorted = [...selected].sort();
  const map = new Map<string, string>();
  sorted.forEach((aff, i) => map.set(aff, AFFIL_PALETTE[i % AFFIL_PALETTE.length]));
  return map;
}
