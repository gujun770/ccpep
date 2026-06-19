import argparse
from pathlib import Path
import pandas as pd


def extract_monomers(helm_notation: str):
    start_index = helm_notation.find('{')
    end_index = helm_notation.find('}')
    if start_index == -1 or end_index == -1:
        return []
    sequence = helm_notation[start_index + 1:end_index]
    return [token.strip() for token in sequence.split('.') if token.strip()]


def natural_ratio(tokens):
    if not tokens:
        return 0.0
    natural_vocab = {
        "A", "R", "N", "D", "C",
        "Q", "E", "G", "H", "I",
        "L", "K", "M", "F", "P",
        "S", "T", "W", "Y", "V",
    }
    natural_count = sum(1 for token in tokens if token in natural_vocab)
    return natural_count / len(tokens)


def summarize_generation(generated_df, reference_df=None, target_length=None, min_score=None):
    helms = generated_df['HELM'].dropna().astype(str).tolist()
    token_lists = [extract_monomers(helm) for helm in helms]
    valid_flags = [len(tokens) > 0 for tokens in token_lists]
    valid_helms = [helm for helm, valid in zip(helms, valid_flags) if valid]

    metrics = {
        'num_generated': len(helms),
        'validity': sum(valid_flags) / max(len(valid_flags), 1),
        'uniqueness': len(set(valid_helms)) / max(len(valid_helms), 1),
    }

    if 'Score1' in generated_df.columns and min_score is not None:
        metrics['high_permeability_rate'] = (generated_df['Score1'] >= min_score).mean()

    if target_length is not None:
        length_success = [len(tokens) == target_length for tokens in token_lists if tokens]
        metrics['length_success_rate'] = sum(length_success) / max(len(length_success), 1)

    natural_scores = [natural_ratio(tokens) for tokens in token_lists if tokens]
    metrics['mean_natural_ratio'] = sum(natural_scores) / max(len(natural_scores), 1)

    if reference_df is not None and 'HELM' in reference_df.columns:
        reference_helms = set(reference_df['HELM'].dropna().astype(str).tolist())
        novel = [helm not in reference_helms for helm in valid_helms]
        metrics['novelty'] = sum(novel) / max(len(novel), 1)

    return metrics


def main():
    parser = argparse.ArgumentParser(description='Summarize cyclic peptide generation quality metrics.')
    parser.add_argument('--generated', required=True, help='CSV file produced by generation.')
    parser.add_argument('--reference', help='Reference training CSV for novelty calculation.')
    parser.add_argument('--target-length', type=int, help='Target cyclic peptide length.')
    parser.add_argument('--min-score', type=float, help='Permeability threshold for hit-rate calculation.')
    args = parser.parse_args()

    generated_df = pd.read_csv(args.generated)
    reference_df = pd.read_csv(args.reference) if args.reference else None
    metrics = summarize_generation(
        generated_df=generated_df,
        reference_df=reference_df,
        target_length=args.target_length,
        min_score=args.min_score,
    )

    output = pd.DataFrame([metrics])
    print(output.to_string(index=False))


if __name__ == '__main__':
    main()
