import argparse
import numpy as np
import pandas as pd


def assign_categories(lengths: pd.Series) -> pd.Series:
    q33 = lengths.quantile(0.33)
    q66 = lengths.quantile(0.66)
    return pd.cut(
        lengths,
        bins=[-np.inf, q33, q66, np.inf],
        labels=["short", "medium", "long"],
    )


def build_corpus(input_path: str, output_path: str, n_sample: int = 1000, seed: int = 42) -> None:
    df = pd.read_csv(input_path)

    if len(df) < n_sample:
        raise ValueError(
            f"Le fichier source ne contient que {len(df)} lignes, "
            f"impossible d'en échantillonner {n_sample}."
        )

    df_sample = df.sample(n=n_sample, random_state=seed).reset_index(drop=True)

    en_rows = pd.DataFrame({"text": df_sample.iloc[:, 0].values, "lang": "en"})
    fr_rows = pd.DataFrame({"text": df_sample.iloc[:, 1].values, "lang": "fr"})

    corpus = (
        pd.concat([en_rows, fr_rows], ignore_index=True)
        .dropna(subset=["text"])
        .sample(frac=1, random_state=seed)
        .reset_index(drop=True)
    )

    corpus.insert(0, "id", range(1, len(corpus) + 1))

    char_lengths = corpus["text"].str.len()
    corpus["category"] = assign_categories(char_lengths)

    corpus.to_csv(output_path, index=False)

    q33 = char_lengths.quantile(0.33)
    q66 = char_lengths.quantile(0.66)
    print(f"Corpus généré : {len(corpus)} lignes → {output_path}")
    print(f"  Seuils (caractères) — short ≤ {q33:.0f} | medium ≤ {q66:.0f} | long > {q66:.0f}")
    print(corpus["category"].value_counts().to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Génère le corpus d'évaluation à partir d'un CSV EN↔FR.")
    parser.add_argument("--input", default="data/en-fr.csv")
    parser.add_argument("--output", default="data/corpus.csv")
    parser.add_argument("--n-sample", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    build_corpus(args.input, args.output, args.n_sample, args.seed)
