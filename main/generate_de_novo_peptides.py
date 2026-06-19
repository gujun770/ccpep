import argparse
import math
import random
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from main.screen_monomer_candidates import aggregate_monomer_features, build_training_frame
from main.train_enhanced_predictor import build_monomer_lookup
from utils.project_paths import DATASET_DIR, RESULT_DIR


NATURAL_SYMBOLS = {
    "A", "R", "N", "D", "C", "Q", "E", "G", "H", "I",
    "L", "K", "M", "F", "P", "S", "T", "W", "Y", "V",
}


def natural_ratio(tokens):
    return sum(t in NATURAL_SYMBOLS for t in tokens) / max(len(tokens), 1)


def n_methyl_ratio(tokens):
    return sum(t.lower().startswith("me") or "_me" in t.lower() for t in tokens) / max(len(tokens), 1)


def d_ratio(tokens):
    return sum(t.lower().startswith("d") for t in tokens) / max(len(tokens), 1)


def token_signature(tokens):
    return ".".join(tokens)


def composition_signature(tokens):
    return ".".join(sorted(tokens))


def helm_from_tokens(tokens, idx):
    rendered = [f"[{t}]" if not (len(t) == 1 and t.isalpha() and t.isupper()) else t for t in tokens]
    joined = ".".join(rendered)
    return f"PEPTIDE{idx}{{{joined}}}$PEPTIDE{idx},PEPTIDE{idx},1:R1-6:R2$$$"


def tree_prediction_std(rf_model, x):
    preds = np.vstack([est.predict(x) for est in rf_model.estimators_])
    return preds.std(axis=0)


def tree_positive_prob_std(rf_model, x):
    probs = []
    for est in rf_model.estimators_:
        p = est.predict_proba(x)
        if p.shape[1] == 1:
            cls = est.classes_[0]
            probs.append(np.ones(x.shape[0]) if cls == 1 else np.zeros(x.shape[0]))
        else:
            pos_idx = list(est.classes_).index(1)
            probs.append(p[:, pos_idx])
    return np.vstack(probs).std(axis=0)


def smooth_distribution(count_map, pool, alpha=1.0):
    raw = np.array([count_map.get(tok, 0.0) + alpha for tok in pool], dtype=float)
    return raw / raw.sum()


def build_elite_profiles(train_df, monomer_pool, elite_fraction=0.18, alpha=1.0):
    elite_n = max(120, int(len(train_df) * elite_fraction))
    elite_df = train_df.sort_values("Permeability", ascending=False).head(elite_n).copy()
    length = len(elite_df["tokens"].iloc[0])

    global_counts = {}
    for tokens in elite_df["tokens"]:
        for token in tokens:
            global_counts[token] = global_counts.get(token, 0) + 1

    position_counts = []
    for pos in range(length):
        count_map = {}
        for tokens in elite_df["tokens"]:
            token = tokens[pos]
            count_map[token] = count_map.get(token, 0) + 1
        position_counts.append(count_map)

    position_probs = [smooth_distribution(counts, monomer_pool, alpha=alpha) for counts in position_counts]
    global_probs = smooth_distribution(global_counts, monomer_pool, alpha=alpha)

    elite_stats = {
        "target_natural_ratio": float(elite_df["tokens"].apply(natural_ratio).mean()),
        "target_n_methyl_ratio": float(elite_df["tokens"].apply(n_methyl_ratio).mean()),
        "target_d_ratio": float(elite_df["tokens"].apply(d_ratio).mean()),
        "elite_signatures": set(elite_df["tokens"].apply(token_signature).tolist()),
        "elite_permeability_mean": float(elite_df["Permeability"].mean()),
        "elite_permeability_std": float(elite_df["Permeability"].std() or 1.0),
    }
    return elite_df, position_probs, global_probs, elite_stats


def sample_guided_peptides(monomer_pool, global_probs, position_probs, n_samples, length, explore_rate=0.28):
    sequences = []
    for _ in range(n_samples):
        tokens = []
        for pos in range(length):
            if random.random() < explore_rate:
                dist = global_probs
            else:
                dist = 0.72 * position_probs[pos] + 0.28 * global_probs
                dist = dist / dist.sum()
            token = np.random.choice(monomer_pool, p=dist)
            tokens.append(str(token))
        sequences.append(tokens)
    return sequences


def alignment_score(value, target, tolerance):
    return max(0.0, 1.0 - abs(value - target) / max(tolerance, 1e-6))


def motif_score(tokens, monomer_pool, position_probs, global_probs):
    tok_to_idx = {tok: idx for idx, tok in enumerate(monomer_pool)}
    scores = []
    for pos, token in enumerate(tokens):
        idx = tok_to_idx.get(token)
        if idx is None:
            scores.append(0.0)
            continue
        pos_prob = position_probs[pos][idx]
        glob_prob = global_probs[idx]
        scores.append(0.7 * pos_prob + 0.3 * glob_prob)
    return float(np.mean(scores)) if scores else 0.0


def evaluate_sequences(sequences, reg, cls, monomer_lookup, feature_cols, monomer_pool, global_probs, position_probs, train_signatures, elite_stats):
    feat_df = pd.DataFrame([aggregate_monomer_features(tokens, monomer_lookup) for tokens in sequences])
    x = feat_df[feature_cols].fillna(0.0).to_numpy()

    pred_perm = reg.predict(x)
    pred_prob = cls.predict_proba(x)[:, 1]
    perm_std = tree_prediction_std(reg, x)
    prob_std = tree_positive_prob_std(cls, x)

    token_strings = [token_signature(t) for t in sequences]
    nat_ratios = np.array([natural_ratio(t) for t in sequences], dtype=float)
    me_ratios = np.array([n_methyl_ratio(t) for t in sequences], dtype=float)
    d_ratios = np.array([d_ratio(t) for t in sequences], dtype=float)
    motif_scores = np.array([motif_score(t, monomer_pool, position_probs, global_probs) for t in sequences], dtype=float)
    novelty_scores = np.array([1.0 if sig not in train_signatures else 0.0 for sig in token_strings], dtype=float)

    perm_quality = 1.0 / (1.0 + np.exp(-(pred_perm - elite_stats["elite_permeability_mean"]) / max(elite_stats["elite_permeability_std"], 1e-6)))
    uncertainty_stability = 1.0 / (1.0 + perm_std + prob_std)
    natural_align = np.array([alignment_score(v, elite_stats["target_natural_ratio"], 0.28) for v in nat_ratios], dtype=float)
    methyl_align = np.array([alignment_score(v, elite_stats["target_n_methyl_ratio"], 0.28) for v in me_ratios], dtype=float)
    d_align = np.array([alignment_score(v, elite_stats["target_d_ratio"], 0.22) for v in d_ratios], dtype=float)
    composition_align = (natural_align + methyl_align + d_align) / 3.0

    multiobjective = (
        0.30 * perm_quality
        + 0.24 * pred_prob
        + 0.16 * motif_scores
        + 0.16 * composition_align
        + 0.08 * uncertainty_stability
        + 0.06 * novelty_scores
    )
    robust = pred_perm - 0.5 * perm_std + pred_prob - 0.25 * prob_std

    out = feat_df.copy()
    out["tokens"] = token_strings
    out["composition_signature"] = [composition_signature(t) for t in sequences]
    out["predicted_permeability"] = pred_perm
    out["predicted_positive_prob"] = pred_prob
    out["permeability_std"] = perm_std
    out["positive_prob_std"] = prob_std
    out["perm_quality"] = perm_quality
    out["robust_score"] = robust
    out["natural_ratio"] = nat_ratios
    out["n_methyl_ratio"] = me_ratios
    out["d_ratio"] = d_ratios
    out["motif_score"] = motif_scores
    out["novelty_score"] = novelty_scores
    out["composition_alignment"] = composition_align
    out["uncertainty_stability"] = uncertainty_stability
    out["multiobjective_score"] = multiobjective
    return out


def top_tokens_for_position(position_prob, monomer_pool, top_k):
    indices = np.argsort(position_prob)[::-1][:top_k]
    return [monomer_pool[idx] for idx in indices]


def mutate_guided_tokens(tokens, monomer_pool, global_probs, position_probs, offspring_per_seed=40, position_top_k=8):
    proposals = []
    length = len(tokens)
    top_per_position = [top_tokens_for_position(position_probs[pos], monomer_pool, position_top_k) for pos in range(length)]

    proposals.append(tokens.copy())
    for _ in range(offspring_per_seed):
        mutated = tokens.copy()
        n_mut = 1 if random.random() < 0.65 else 2
        positions = random.sample(range(length), k=n_mut)
        for pos in positions:
            candidate_pool = top_per_position[pos]
            if random.random() < 0.25:
                replacement = random.choices(monomer_pool, weights=global_probs, k=1)[0]
            else:
                replacement = random.choice(candidate_pool)
            if replacement == mutated[pos] and len(candidate_pool) > 1:
                alternatives = [tok for tok in candidate_pool if tok != mutated[pos]]
                replacement = random.choice(alternatives) if alternatives else replacement
            mutated[pos] = replacement
        proposals.append(mutated)
    return proposals


def select_top_diverse(df, top_k, min_jaccard=0.34):
    selected = []
    selected_sets = []
    seen_signatures = set()
    seen_compositions = set()

    for _, row in df.iterrows():
        sig = row["tokens"]
        comp = row["composition_signature"]
        if sig in seen_signatures or comp in seen_compositions:
            continue
        token_set = set(sig.split("."))
        keep = True
        for other in selected_sets:
            union = len(token_set | other)
            if union == 0:
                dist = 0.0
            else:
                dist = 1.0 - len(token_set & other) / union
            if dist < min_jaccard:
                keep = False
                break
        if keep:
            selected.append(row)
            selected_sets.append(token_set)
            seen_signatures.add(sig)
            seen_compositions.add(comp)
        if len(selected) >= top_k:
            break
    return pd.DataFrame(selected)


def main():
    parser = argparse.ArgumentParser(description="Multi-objective de novo cyclic peptide generator guided by descriptor RF scorers.")
    parser.add_argument("--label-csv", default=str(DATASET_DIR / "CycPeptMPDB_Peptide_Length_6.csv"))
    parser.add_argument("--monomer-csv", default=str(DATASET_DIR / "CycPeptMPDB_Monomer_All.csv"))
    parser.add_argument("--result-dir", default=str(RESULT_DIR / "de_novo_generation"))
    parser.add_argument("--global-samples", type=int, default=24000)
    parser.add_argument("--stage1-top-k", type=int, default=400)
    parser.add_argument("--local-offspring-per-seed", type=int, default=48)
    parser.add_argument("--final-top-k", type=int, default=120)
    parser.add_argument("--length", type=int, default=6)
    parser.add_argument("--elite-fraction", type=float, default=0.18)
    parser.add_argument("--n-jobs", type=int, default=1)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)

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

    reg = RandomForestRegressor(
        n_estimators=500, max_depth=None, min_samples_leaf=2, random_state=args.seed, n_jobs=args.n_jobs
    )
    cls = RandomForestClassifier(
        n_estimators=500, max_depth=None, min_samples_leaf=2, class_weight="balanced_subsample", random_state=args.seed, n_jobs=args.n_jobs
    )
    x_train = train_df[feature_cols].fillna(0.0).to_numpy()
    reg.fit(x_train, train_df["Permeability"].to_numpy())
    cls.fit(x_train, train_df["label"].to_numpy())

    global_counts = {}
    for tokens in train_df["tokens"]:
        for token in tokens:
            global_counts[token] = global_counts.get(token, 0) + 1
    monomer_pool = [tok for tok, _ in sorted(global_counts.items(), key=lambda kv: kv[1], reverse=True)[:36]]
    elite_df, position_probs, global_probs, elite_stats = build_elite_profiles(
        train_df, monomer_pool, elite_fraction=args.elite_fraction, alpha=1.0
    )

    train_signatures = set(train_df["tokens"].apply(token_signature).tolist())

    global_sequences = sample_guided_peptides(
        monomer_pool=monomer_pool,
        global_probs=global_probs,
        position_probs=position_probs,
        n_samples=args.global_samples,
        length=args.length,
        explore_rate=0.30,
    )
    stage1_df = evaluate_sequences(
        global_sequences, reg, cls, monomer_lookup, feature_cols, monomer_pool, global_probs, position_probs, train_signatures, elite_stats
    )
    stage1_df = stage1_df.loc[stage1_df["novelty_score"] > 0].copy()
    stage1_df = stage1_df.sort_values(
        ["multiobjective_score", "robust_score", "predicted_positive_prob", "predicted_permeability"],
        ascending=False,
    ).drop_duplicates(subset=["tokens"]).reset_index(drop=True)
    stage1_top = select_top_diverse(stage1_df, args.stage1_top_k, min_jaccard=0.28).copy()

    local_sequences = []
    parent_tokens = []
    for token_str in stage1_top["tokens"]:
        tokens = token_str.split(".")
        proposals = mutate_guided_tokens(
            tokens=tokens,
            monomer_pool=monomer_pool,
            global_probs=global_probs,
            position_probs=position_probs,
            offspring_per_seed=args.local_offspring_per_seed,
            position_top_k=8,
        )
        local_sequences.extend(proposals)
        parent_tokens.extend([token_str] * len(proposals))

    stage2_df = evaluate_sequences(
        local_sequences, reg, cls, monomer_lookup, feature_cols, monomer_pool, global_probs, position_probs, train_signatures, elite_stats
    )
    stage2_df["parent_tokens"] = parent_tokens
    stage2_df = stage2_df.loc[stage2_df["novelty_score"] > 0].copy()
    stage2_df = stage2_df.sort_values(
        ["multiobjective_score", "robust_score", "predicted_positive_prob", "predicted_permeability"],
        ascending=False,
    ).drop_duplicates(subset=["tokens"]).reset_index(drop=True)
    final_df = select_top_diverse(stage2_df, args.final_top_k, min_jaccard=0.34).copy()

    final_df["HELM"] = [helm_from_tokens(tokens.split("."), i) for i, tokens in enumerate(final_df["tokens"], start=1)]
    final_df["novelty_vs_train"] = 1
    final_df["stage"] = "focused_refinement"

    stage1_top_out = stage1_top.copy()
    stage1_top_out["HELM"] = [helm_from_tokens(tokens.split("."), i) for i, tokens in enumerate(stage1_top_out["tokens"], start=1)]
    stage1_top_out["stage"] = "global_discovery"

    stage1_top_out.to_csv(result_dir / "stage1_top_candidates.csv", index=False)
    final_df.to_csv(result_dir / "final_generated_candidates.csv", index=False)

    summary = pd.DataFrame(
        [
            {
                "global_samples": args.global_samples,
                "elite_training_examples": int(len(elite_df)),
                "stage1_candidates": int(len(stage1_df)),
                "stage1_top_candidates": int(len(stage1_top_out)),
                "stage2_candidates": int(len(stage2_df)),
                "final_generated_candidates": int(len(final_df)),
                "mean_predicted_permeability": float(final_df["predicted_permeability"].mean()) if len(final_df) else None,
                "mean_positive_prob": float(final_df["predicted_positive_prob"].mean()) if len(final_df) else None,
                "mean_multiobjective_score": float(final_df["multiobjective_score"].mean()) if len(final_df) else None,
                "mean_motif_score": float(final_df["motif_score"].mean()) if len(final_df) else None,
                "mean_composition_alignment": float(final_df["composition_alignment"].mean()) if len(final_df) else None,
                "mean_natural_ratio": float(final_df["natural_ratio"].mean()) if len(final_df) else None,
                "mean_n_methyl_ratio": float(final_df["n_methyl_ratio"].mean()) if len(final_df) else None,
            }
        ]
    )
    summary.to_csv(result_dir / "summary.csv", index=False)

    print(summary.to_string(index=False))
    print("Top 20 de novo candidates:")
    print(
        final_df[
            [
                "HELM",
                "tokens",
                "predicted_permeability",
                "predicted_positive_prob",
                "motif_score",
                "composition_alignment",
                "multiobjective_score",
                "robust_score",
                "natural_ratio",
                "n_methyl_ratio",
            ]
        ].head(20).to_string(index=False)
    )
    print(f"Saved final de novo candidates to: {result_dir / 'final_generated_candidates.csv'}")


if __name__ == "__main__":
    main()
