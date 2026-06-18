import argparse
from typing import Callable

import pandas as pd
import tiktoken
from tqdm import tqdm
from transformers import AutoTokenizer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tiktoken_counter(encoding: tiktoken.Encoding) -> Callable[[str], int]:
    def count(text: str) -> int:
        if not isinstance(text, str):
            return 0
        return len(encoding.encode(text))
    return count


def _hf_counter(tokenizer) -> Callable[[str], int]:
    def count(text: str) -> int:
        if not isinstance(text, str):
            return 0
        return len(tokenizer.encode(text, add_special_tokens=False))
    return count


def _apply(series: pd.Series, fn: Callable[[str], int], desc: str) -> pd.Series:
    tqdm.pandas(desc=desc)
    return series.progress_apply(fn)


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

HF_MODELS = {
    "qwen":    "Qwen/Qwen2.5-7B",
    "mistral": "mistralai/Mistral-7B-v0.3",
    "gemma":   "google/gemma-2-9b",
}

OUTPUT_COLUMNS = [
    "id", "text", "lang", "category",
    "tokens_gpt4o", "tokens_cl100k_base",
    "tokens_qwen", "tokens_mistral", "tokens_gemma",
]


def run_benchmark(corpus_path: str, output_path: str) -> None:
    df = pd.read_csv(corpus_path)
    print(f"Corpus chargé : {len(df)} lignes\n")

    # --- tiktoken -----------------------------------------------------------
    enc_gpt4o   = tiktoken.encoding_for_model("gpt-4o")
    enc_cl100k  = tiktoken.get_encoding("cl100k_base")

    df["tokens_gpt4o"]       = _apply(df["text"], _tiktoken_counter(enc_gpt4o),  "GPT-4o")
    df["tokens_cl100k_base"] = _apply(df["text"], _tiktoken_counter(enc_cl100k), "cl100k_base")

    # --- HuggingFace tokenizers ---------------------------------------------
    for col_suffix, model_id in HF_MODELS.items():
        print(f"\nChargement tokenizer : {model_id}")
        tokenizer = AutoTokenizer.from_pretrained(model_id, use_fast=True)
        df[f"tokens_{col_suffix}"] = _apply(
            df["text"],
            _hf_counter(tokenizer),
            model_id.split("/")[-1],
        )

    # --- Sauvegarde ---------------------------------------------------------
    df[OUTPUT_COLUMNS].to_csv(output_path, index=False)
    print(f"\nRésultats sauvegardés → {output_path}")
    print("\nAperçu statistiques tokens :")
    token_cols = [c for c in OUTPUT_COLUMNS if c.startswith("tokens_")]
    print(df[token_cols].describe().round(1).to_string())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Benchmark de tokenizers sur le corpus EN↔FR.")
    parser.add_argument("--corpus",  default="data/corpus.csv")
    parser.add_argument("--output",  default="data/benchmark_results.csv")
    args = parser.parse_args()

    run_benchmark(args.corpus, args.output)
