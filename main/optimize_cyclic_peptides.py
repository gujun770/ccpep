import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.screen_monomer_candidates import (
    aggregate_monomer_features,
    build_training_frame,
    helm_with_tokens,
)
from main.train_enhanced_predictor import build_monomer_lookup, parse_helm_monomers
from utils.project_paths import DATASET_DIR, RESULT_DIR


NATURAL_SYMBOLS = {
    "A", "R", "N", "D", "C", "Q", "E", "G", "H", "I",
    "L", "K", "M", "F", "P", "S", "T", "W", "Y", "V",
}


def token_signature(tokens):
    return ".".join(tokens)


def composition_signature(tokens):
    return ".".join(sorted(tokens))


def jaccard_distance(tokens_a, tokens_b):
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    union = len(set_a | set_b)
    if union == 0:
        return 0.0
    return 1.0 - (len(set_a & set_b) / union)


def mutation_distance(tokens_a, tokens_b):
    return sum(a != b for a, b in zip(tokens_a, tokens_b))


def natural_ratio(tokens):
    return sum(t in NATURAL_SYMBOLS for t in tokens) / max(len(tokens), 1)


def select_diverse_seeds(train_df, seed_count, min_jaccard_distance=0.34, max_per_source=5):
    ranked = train_df.sort_values("Permeability", ascending=False).copy()
    selected = []
    selected_tokens = []
    source_counter = {}

    for _, row in ranked.iterrows():
        source = row["Source"]
        if source_counter.get(source, 0) >= max_per_source:
            continue
        tokens = row["tokens"]
        keep = True
        for existing in selected_tokens:
            if jaccard_distance(tokens, existing) < min_jaccard_distance:
                keep = False
                break
        if keep:
            selected.append(row)
            selected_tokens.append(tokens)
            source_counter[source] = source_counter.get(source, 0) + 1
        if len(selected) >= seed_count:
            break

    if len(selected) < seed_count:
        selected_ids = {row["HELM"] for row in selected}
        for _, row in ranked.iterrows():
            if row["HELM"] in selected_ids:
                continue
            source = row["Source"]
            if source_counter.get(source, 0) >= max_per_source:
                continue
            selected.append(row)
            source_counter[source] = source_counter.get(source, 0) + 1
            if len(selected) >= seed_count:
                break

    return pd.DataFrame(selected)


def train_models(train_df, feature_cols):
    x = train_df[feature_cols].fillna(0.0).to_numpy()
    y_reg = train_df["Permeability"].to_numpy()
    y_cls = train_df["label"].to_numpy()

    reg = RandomForestRegressor(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    cls = RandomForestClassifier(
        n_estimators=500,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )
    reg.fit(x, y_reg)
    cls.fit(x, y_cls)
    return reg, cls


def build_candidate_pool(train_df, monomer_df, top_monomers):
    counts = {}
    for tokens in train_df["tokens"]:
        for token in tokens:
            counts[token] = counts.get(token, 0) + 1

    monomer_meta = monomer_df[["Symbol", "Natural_Analog", "MolLogP", "TPSA"]].copy()
    monomer_meta["Symbol"] = monomer_meta["Symbol"].astype(str).str.strip()
    monomer_meta["MolLogP"] = pd.to_numeric(monomer_meta["MolLogP"], errors="coerce")
    monomer_meta["TPSA"] = pd.to_numeric(monomer_meta["TPSA"], errors="coerce")
    monomer_meta = monomer_meta.drop_duplicates(subset=["Symbol"]).set_index("Symbol")

    pool = []
    for token, _ in sorted(counts.items(), key=lambda kv: kv[1], reverse=True):
        if token not in monomer_meta.index:
            continue
        pool.append(token)
        if len(pool) >= top_monomers:
            break
    return pool, monomer_meta


def allowed_replacement(original, replacement, monomer_meta, max_logp_shift, max_tpsa_shift):
    if original == replacement:
        return False
    if original not in monomer_meta.index or replacement not in monomer_meta.index:
        return False
    orig_logp = monomer_meta.loc[original, "MolLogP"]
    repl_logp = monomer_meta.loc[replacement, "MolLogP"]
    orig_tpsa = monomer_meta.loc[original, "TPSA"]
    repl_tpsa = monomer_meta.loc[replacement, "TPSA"]
    if pd.notna(orig_logp) and pd.notna(repl_logp) and abs(orig_logp - repl_logp) > max_logp_shift:
        return False
    if pd.notna(orig_tpsa) and pd.notna(repl_tpsa) and abs(orig_tpsa - repl_tpsa) > max_tpsa_shift:
        return False
    return True


def enumerate_candidates(seed_df, candidate_pool, monomer_lookup, monomer_meta, max_logp_shift, max_tpsa_shift, max_mutations):
    rows = []
    seen = set()

    for _, row in seed_df.iterrows():
        base_tokens = list(row["tokens"])
        single_mutants = []

        for pos in range(len(base_tokens)):
            for replacement in candidate_pool:
                if not allowed_replacement(base_tokens[pos], replacement, monomer_meta, max_logp_shift, max_tpsa_shift):
                    continue
                mutated = base_tokens.copy()
                mutated[pos] = replacement
                signature = token_signature(mutated)
                if signature in seen:
                    continue
                seen.add(signature)
                single_mutants.append((pos, mutated))
                rows.append({
                    "parent_helm": row["HELM"],
                    "parent_tokens": base_tokens,
                    "tokens": mutated,
                    "mutation_sites": str([pos]),
                    "mutation_count": 1,
                    "from_monomer": base_tokens[pos],
                    "to_monomer": replacement,
                    "mutation_description": f"{pos}:{base_tokens[pos]}->{replacement}",
                    "HELM": helm_with_tokens(row["HELM"], mutated),
                    "parent_permeability": row["Permeability"],
                })

        if max_mutations >= 2:
            for idx_a in range(len(single_mutants)):
                pos_a, tokens_a = single_mutants[idx_a]
                for pos_b in range(pos_a + 1, len(base_tokens)):
                    for replacement in candidate_pool:
                        if not allowed_replacement(tokens_a[pos_b], replacement, monomer_meta, max_logp_shift, max_tpsa_shift):
                            continue
                        mutated = tokens_a.copy()
                        mutated[pos_b] = replacement
                        signature = token_signature(mutated)
                        if signature in seen:
                            continue
                        seen.add(signature)
                        rows.append({
                            "parent_helm": row["HELM"],
                            "parent_tokens": base_tokens,
                            "tokens": mutated,
                            "mutation_sites": str(sorted([pos_a, pos_b])),
                            "mutation_count": 2,
                            "from_monomer": f"{base_tokens[pos_a]}|{tokens_a[pos_b]}",
                            "to_monomer": f"{tokens_a[pos_a]}|{replacement}",
                            "mutation_description": f"{pos_a}:{base_tokens[pos_a]}->{tokens_a[pos_a]};{pos_b}:{tokens_a[pos_b]}->{replacement}",
                            "HELM": helm_with_tokens(row["HELM"], mutated),
                            "parent_permeability": row["Permeability"],
                        })

    return pd.DataFrame(rows)


def greedy_diverse_selection(df, top_k, min_jaccard_distance=0.34, min_mutation_distance=2, max_per_parent=2):
    selected = []
    selected_tokens = []
    parent_counter = {}

    for _, row in df.iterrows():
        tokens = row["tokens"]
        parent = row["parent_helm"]
        if parent_counter.get(parent, 0) >= max_per_parent:
            continue
        keep = True
        for existing in selected_tokens:
            if jaccard_distance(tokens, existing) < min_jaccard_distance and mutation_distance(tokens, existing) < min_mutation_distance:
                keep = False
                break
        if keep:
            selected.append(row)
            selected_tokens.append(tokens)
            parent_counter[parent] = parent_counter.get(parent, 0) + 1
        if len(selected) >= top_k:
            break

    return pd.DataFrame(selected)


def main():
    parser = argparse.ArgumentParser(description="Constrained cyclic peptide optimization with descriptor RandomForest scorers.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "design_pipeline"))
    parser.add_argument("--seed-count", type=int, default=40)
    parser.add_argument("--top-monomers", type=int, default=24)
    parser.add_argument("--max-mutations", type=int, default=2)
    parser.add_argument("--min-improvement", type=float, default=0.15)
    parser.add_argument("--min-positive-prob", type=float, default=0.85)
    parser.add_argument("--min-natural-ratio", type=float, default=0.0)
    parser.add_argument("--max-natural-ratio", type=float, default=1.0)
    parser.add_argument("--max-logp-shift", type=float, default=1.25)
    parser.add_argument("--max-tpsa-shift", type=float, default=25.0)
    parser.add_argument("--top-k", type=int, default=100)
    args = parser.parse_args()

    result_dir = Path(args.result_dir)
    result_dir.mkdir(parents=True, exist_ok=True)

    label_df = pd.read_csv(args.label_csv)
    monomer_df = pd.read_csv(args.monomer_csv, low_memory=False)
    monomer_lookup = build_monomer_lookup(monomer_df)

    train_df = build_training_frame(label_df, monomer_lookup)
    feature_cols = [
        c for c in train_df.columns
        if c not in {"HELM", "Permeability", "Monomer_Length_in_Main_Chain", "Source", "Year", "tokens", "label"}
    ]
    reg, cls = train_models(train_df, feature_cols)

    candidate_pool, monomer_meta = build_candidate_pool(train_df, monomer_df, args.top_monomers)
    seed_df = select_diverse_seeds(train_df, seed_count=args.seed_count)

    candidate_df = enumerate_candidates(
        seed_df=seed_df,
        candidate_pool=candidate_pool,
        monomer_lookup=monomer_lookup,
        monomer_meta=monomer_meta,
        max_logp_shift=args.max_logp_shift,
        max_tpsa_shift=args.max_tpsa_shift,
        max_mutations=args.max_mutations,
    )

    candidate_features = pd.DataFrame(
        [aggregate_monomer_features(tokens, monomer_lookup) for tokens in candidate_df["tokens"]]
    )
    candidate_df = pd.concat([candidate_df.reset_index(drop=True), candidate_features], axis=1)
    candidate_x = candidate_df[feature_cols].fillna(0.0).to_numpy()
    candidate_df["predicted_permeability"] = reg.predict(candidate_x)
    candidate_df["predicted_positive_prob"] = cls.predict_proba(candidate_x)[:, 1]
    candidate_df["natural_ratio"] = candidate_df["tokens"].apply(natural_ratio)
    candidate_df["improvement"] = candidate_df["predicted_permeability"] - candidate_df["parent_permeability"]
    candidate_df["signature"] = candidate_df["tokens"].apply(token_signature)
    candidate_df["composition_signature"] = candidate_df["tokens"].apply(composition_signature)
    candidate_df["parent_composition_signature"] = candidate_df["parent_tokens"].apply(composition_signature)

    candidate_df = candidate_df.loc[
        candidate_df["composition_signature"] != candidate_df["parent_composition_signature"]
    ].copy()

    filter_schedules = [
        (args.min_improvement, args.min_positive_prob),
        (max(args.min_improvement - 0.05, 0.05), max(args.min_positive_prob - 0.02, 0.75)),
        (max(args.min_improvement - 0.10, 0.0), max(args.min_positive_prob - 0.05, 0.70)),
    ]
    filtered = pd.DataFrame()
    selected_schedule = filter_schedules[-1]
    for min_improvement, min_positive_prob in filter_schedules:
        trial = candidate_df.loc[
            (candidate_df["improvement"] >= min_improvement)
            & (candidate_df["predicted_positive_prob"] >= min_positive_prob)
            & (candidate_df["natural_ratio"] >= args.min_natural_ratio)
            & (candidate_df["natural_ratio"] <= args.max_natural_ratio)
        ].copy()
        filtered = trial
        selected_schedule = (min_improvement, min_positive_prob)
        if len(trial) >= max(args.top_k // 2, 20):
            break

    filtered = (
        filtered.sort_values(
            ["predicted_positive_prob", "predicted_permeability", "improvement"],
            ascending=False,
        )
        .drop_duplicates(subset=["signature"])
        .reset_index(drop=True)
    )

    diverse_top = greedy_diverse_selection(filtered, top_k=args.top_k)
    diverse_top = diverse_top.copy()
    diverse_top["tokens"] = diverse_top["tokens"].apply(lambda x: ".".join(x))
    filtered_out = filtered.copy()
    filtered_out["tokens"] = filtered_out["tokens"].apply(lambda x: ".".join(x))

    filtered_out.to_csv(result_dir / "filtered_candidates.csv", index=False)
    diverse_top.to_csv(result_dir / "diverse_top_candidates.csv", index=False)

    summary = {
        "seed_count": int(len(seed_df)),
        "unique_seed_sources": int(seed_df["Source"].nunique()),
        "candidate_pool_size": int(len(candidate_pool)),
        "generated_candidates": int(len(candidate_df)),
        "filtered_candidates": int(len(filtered_out)),
        "diverse_top_candidates": int(len(diverse_top)),
        "unique_parents_in_top": int(diverse_top["parent_helm"].nunique()) if len(diverse_top) else 0,
        "selected_min_improvement": float(selected_schedule[0]),
        "selected_min_positive_prob": float(selected_schedule[1]),
        "mean_predicted_permeability": float(filtered["predicted_permeability"].mean()) if len(filtered) else None,
        "mean_improvement": float(filtered["improvement"].mean()) if len(filtered) else None,
    }

    pd.DataFrame([summary]).to_csv(result_dir / "summary.csv", index=False)

    print(summary)
    print("Top 20 diverse optimized candidates:")
    print(
        diverse_top[
            [
                "HELM",
                "parent_permeability",
                "mutation_sites",
                "mutation_count",
                "predicted_permeability",
                "predicted_positive_prob",
                "improvement",
                "natural_ratio",
            ]
        ]
        .head(20)
        .to_string(index=False)
    )
    print(f"Saved optimized candidates to: {result_dir / 'diverse_top_candidates.csv'}")


if __name__ == "__main__":
    main()
