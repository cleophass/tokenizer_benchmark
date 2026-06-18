# Tokenizer Benchmark

Benchmark de tokenizers sur un corpus bilingue EN↔FR pour comparer l'efficacité de différents tokenizers sur les deux langues.

## Pipeline

### Step 1 — Génération du corpus

```bash
python build_corpus.py --input data/en-fr.csv --output data/corpus.csv --n-sample 1000
```

Échantillonne 1000 paires EN↔FR, les explose en 2000 lignes (une par langue) et assigne une catégorie de longueur par quantile sur les longueurs en caractères.

| Colonne | Description |
|---|---|
| `id` | Identifiant unique |
| `text` | Texte brut |
| `lang` | `en` ou `fr` |
| `category` | `short` / `medium` / `long` (seuils Q33 / Q66) |

### Step 2 — Benchmark des tokenizers

```bash
python benchmark_tokenizers.py --corpus data/corpus.csv --output data/benchmark_results.csv
```

Applique 5 tokenizers et compte le nombre de tokens produits pour chaque texte.

| Colonne | Tokenizer |
|---|---|
| `tokens_gpt4o` | tiktoken — `gpt-4o` |
| `tokens_cl100k_base` | tiktoken — `cl100k_base` |
| `tokens_qwen` | `Qwen/Qwen2.5-7B` |
| `tokens_mistral` | `mistralai/Mistral-7B-v0.3` |
| `tokens_gemma` | `google/gemma-2-9b` |

## Installation

```bash
pip install -r requirements.txt
```

> **Note** : le tokenizer Gemma nécessite d'accepter les conditions d'utilisation sur [huggingface.co/google/gemma-2-9b](https://huggingface.co/google/gemma-2-9b) et d'être authentifié (`huggingface-cli login`).
