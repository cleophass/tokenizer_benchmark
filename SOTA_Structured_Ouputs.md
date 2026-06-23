# Benchmarks de génération structurée et d'extraction d'information — Étude comparative

> Étude destinée à un choix d'architecture LLM d'entreprise (extraction documentaire, génération JSON conforme à schéma, structuration automatique, workflows RAG).
> Sources privilégiées : articles scientifiques, dépôts GitHub officiels, leaderboards officiels.
> Date de l'étude : 23 juin 2026.

**Avertissement méthodologique transverse.** Les quatre benchmarks ne mesurent pas la même chose, et c'est un point décisif pour une décision d'architecture :

- **JSONSchemaBench** mesure surtout la qualité des *moteurs de décodage contraint* (Guidance, Outlines, XGrammar…), pas directement les LLM.
- **StructEval** mesure la capacité d'un *LLM* à générer/convertir 18 formats structurés à partir de consignes en langage naturel.
- **SOB (Structured Output Benchmark)** mesure la *justesse des valeurs extraites* (value accuracy / faithfulness) depuis des sources réelles (texte, OCR de PDF, audio) — c'est le plus proche d'un cas d'extraction documentaire.
- **BFCL** mesure le *function calling / tool use* (capacité agentique), pas l'extraction de documents.

---

# 1. JSONSchemaBench

## 1. Présentation du benchmark

**Objectif.** JSONSchemaBench est un cadre d'évaluation conçu pour mesurer rigoureusement la génération de sorties conformes à un **JSON Schema**. Il a été introduit par Saibo Geng et al. (EPFL + Microsoft Research + JSON Schema), arXiv 2501.10868, « Generating Structured Outputs from Language Models: Benchmark and Studies » (publié sous le titre « JSONSchemaBench: A Rigorous Benchmark of Structured Outputs for Language Models »).

**Problème mesuré.** Le décodage contraint (*constrained decoding*) est devenu la technologie dominante pour forcer des sorties structurées, mais son efficacité réelle restait peu évaluée systématiquement. JSONSchemaBench comble ce vide : il mesure si, et à quel coût, un moteur de génération contrainte produit effectivement du JSON valide vis-à-vis de schémas réels.

**Capacités LLM évaluées.** Le benchmark n'évalue pas en priorité un LLM isolé : il évalue six **frameworks de décodage contraint** (Guidance, Outlines, Llamacpp, XGrammar, OpenAI, Gemini) selon trois axes — **efficacité**, **couverture** (coverage), **qualité** des sorties — avec un LLM sous-jacent (Llama-3.2-1B pour la couverture, Llama-3.1-8B pour efficacité/qualité).

**Contexte d'utilisation.** Choix et calibrage d'une couche de décodage contraint dans un pipeline de génération JSON : quel moteur supporte réellement les schémas complexes, à quel surcoût de latence, et avec quel impact sur la qualité de la tâche.

**Cas d'usage visés.** Réponses d'API, signatures de fonctions (function calling), configurations système (Kubernetes), extraction orientée machine où la sortie doit strictement respecter un format. Le papier cite explicitement la « data extraction » et le « tool use » comme motivations.

## 2. Données d'évaluation

**Description du dataset.** ~10 000 schémas JSON réels (9 558 effectivement utilisés en expérience), organisés en 10 collections de complexité croissante. Licence MIT. Sources : dépôts GitHub publics (corpus Baazizi et al. 2021), JSON Schema Store, dataset de function calling GlaiveAI v2, configurations Kubernetes, schémas Snowplow (analytics événementielle), spécification ANS du Washington Post, et la JSON Schema Test Suite officielle (utilisée en complément pour l'analyse de couverture par fonctionnalité).

| Dataset | Catégorie | Nb schémas |
|---|---|---|
| GlaiveAI-2K | Function Call | 1 707 |
| Github-Trivial | Divers | 444 |
| Github-Easy | Divers | 1 943 |
| Snowplow | API opérationnelle | 403 |
| Github-Medium | Divers | 1 976 |
| Kubernetes | API Kubernetes | 1 064 |
| Washington Post | API d'accès ressource | 125 |
| Github-Hard | Divers | 1 240 |
| JSONSchemaStore | Divers | 492 |
| Github-Ultra | Divers | 164 |
| **Total** | | **9 558** |

(Github-Trivial et Github-Ultra sont conservés dans le benchmark mais exclus des expériences principales — l'un trop facile, l'autre comme cible « aspirationnelle ».)

**Structure des entrées.** Un JSON Schema (Draft 2020-12 après normalisation) + un prompt système demandant de générer un objet JSON conforme, avec deux exemples *few-shot*.

**Structure des sorties attendues.** Un objet JSON valide au regard du schéma, vérifié par la librairie Python `jsonschema` (vérifications de `format` activées).

### Exemple 1 (représentatif, dérivé de la documentation officielle)

> Les schémas exacts sont publics (HuggingFace `epfl-dlab/JSONSchemaBench`) mais volumineux. Exemple représentatif d'une signature de fonction (catégorie GlaiveAI) :

**Entrée (schéma) :**
```json
{
  "type": "object",
  "properties": {
    "location": {"type": "string"},
    "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
  },
  "required": ["location"]
}
```
**Sortie attendue :**
```json
{"location": "Paris, FR", "unit": "celsius"}
```
**Ce qui est évalué :** la sortie est-elle valide vis-à-vis du schéma (type, `enum`, champ `required` présent) ? Le moteur a-t-il accepté de traiter ce schéma (declared coverage), et la sortie est-elle effectivement conforme (empirical coverage) ?

**Pourquoi représentatif :** les signatures de fonction sont la catégorie la « plus facile » — la quasi-totalité des moteurs y réussit (>0,9). Elle sert de baseline.

### Exemple 2 (représentatif — schéma complexe Kubernetes)

**Entrée :** un schéma Kubernetes profondément imbriqué (médiane ~41 champs, jusqu'à 11 720 champs, fan-out jusqu'à 600).
**Sortie attendue :** un objet de configuration respectant la hiérarchie imbriquée, les types et les contraintes.
**Ce qui est évalué :** la robustesse du moteur face aux structures récursives/imbriquées.
**Pourquoi difficile :** sur ce type de schéma, la couverture s'effondre. XGrammar n'atteint qu'une couverture déclarée de 0,12 sur Kubernetes (empirique 0,07), illustrant qu'un moteur rapide peut silencieusement rejeter ou mal contraindre les schémas réalistes complexes.

## 3. Métriques d'évaluation

| Métrique | Description / calcul | Avantages | Limites |
|---|---|---|---|
| **Declared Coverage** | Proportion de schémas que le moteur accepte sans erreur/exception. | Mesure simple du support « annoncé ». | N'indique pas si la sortie est *réellement* conforme (borne supérieure). |
| **Empirical Coverage** | Proportion de schémas pour lesquels la sortie générée est effectivement valide (vérifiée par `jsonschema`). | Indicateur réaliste de performance terrain. | Dépend du LLM sous-jacent et de l'échantillonnage ; mesurée sur la sortie top-1 uniquement. |
| **True Coverage** | Idéal théorique : contraintes exactement équivalentes au schéma. | Définition de référence. | Non mesurable en pratique (infinité d'instances). Approximée par l'empirique. |
| **Compliance Rate** | Empirical ÷ Declared. Fiabilité du moteur *sachant qu'il a accepté le schéma*. | Sépare « j'accepte » de « je garantis ». | Un moteur très restrictif (peu de schémas acceptés) peut afficher un compliance rate flatteur. |
| **Efficiency : GCT / TTFT / TPOT** | Grammar Compilation Time, Time To First Token, Time Per Output Token (médianes). | Quantifie le surcoût de latence du décodage contraint. | Sensible au modèle, au tokenizer, au backend ; biais de couverture corrigé en n'évaluant que l'intersection des schémas couverts par tous. |
| **Quality (task accuracy)** | Exactitude sur 3 tâches de raisonnement (Last Letter, Shuffle Objects, GSM8K) avec sortie JSON `{"reasoning", "answer"}`. | Vérifie que contraindre ne dégrade pas la qualité. | Tâches volontairement simples ; ne couvre pas l'extraction documentaire. |
| **Over-/Under-constrained** (JSON Schema Test Suite) | Nb de catégories où le moteur rejette des instances valides (over) ou accepte des instances invalides (under). | Diagnostic fin des modes de défaillance. | Pas de correspondance directe avec la couverture empirique réelle. |

## 4. Leaderboard

Le benchmark compare des **frameworks**, pas des modèles commerciaux entre eux. Résultats de couverture/conformité agrégés (papier, Geng et al. 2025). Le classement par **fiabilité de conformité (compliance) et couverture** est dominé par Guidance.

| Rang | Framework | Organisation | Constat principal | Métrique | Date |
|---|---|---|---|---|---|
| 1 | **Guidance** | Microsoft / guidance-ai | Meilleure couverture empirique sur 6/8 datasets ; meilleur compliance rate ; meilleure efficacité (TPOT le plus bas grâce au *token healing* / fast-forward) ; meilleure qualité (~+3 % vs LM seul) | Coverage / Compliance / Efficiency / Quality | Jan–Fév 2025 |
| 2 | **Llamacpp** | ggerganov | En tête sur 2 datasets « durs » (Washington Post, JSONSchemaStore) ; bon compromis | Coverage / Compliance | Jan–Fév 2025 |
| 3 | **XGrammar** | mlc-ai | Compilation quasi nulle, très rapide ; mais nombreux échecs *under-constrained* (le plus permissif) | Coverage / Compliance | Jan–Fév 2025 |
| 4 | **Outlines** | dottxt-ai | Couverture correcte mais temps de compilation élevés et *timeouts* fréquents | Coverage / Compliance | Jan–Fév 2025 |
| – | **OpenAI / Gemini** | OpenAI / Google | Couverture empirique la plus basse (stratégie conservatrice : peu de fonctionnalités supportées) mais compliance rate ~1,0 sur ce qu'ils acceptent | Coverage / Compliance | Jan–Fév 2025 |
| – | **LM only** (sans contrainte) | — | Couverture déclarée 1,0 mais conformité réelle la plus faible, surtout sur schémas durs | Empirical Coverage | Jan–Fév 2025 |

Ordres de grandeur de couverture empirique (Llama-3.2-1B sous-jacent) : sur GlaiveAI, Guidance ≈ 0,96 ; sur Github-Hard, Guidance ≈ 0,41, Outlines ≈ 0,03 ; sur JSONSchemaStore, Guidance ≈ 0,30. La couverture chute drastiquement avec la complexité du schéma (constat clé : la conformité « garantie » ne tient pas sur les schémas réels complexes).

Sur la **JSON Schema Test Suite**, Guidance obtient une couverture complète (100 %) sur 13 catégories et la plus haute couverture isolée sur 19 catégories ; XGrammar minimise les erreurs de compilation mais cumule le plus d'échecs *under-constrained* (38 catégories).

*Leaderboard officiel unique avec scores par modèle commercial : non disponible — le benchmark est conçu pour comparer des frameworks. JSONSchemaBench est désormais intégré à `EleutherAI/lm-evaluation-harness`, ce qui permet d'évaluer ses propres modèles.*

## 5. Analyse critique

- **Pertinent pour la génération de JSON ?** Oui, c'est le benchmark de référence sur la *conformité* JSON Schema et le choix du moteur de contrainte. Très pertinent pour décider de la couche de décodage contraint.
- **Pertinent pour l'extraction d'information ?** Faiblement. Il n'y a aucun document source à partir duquel extraire : on génère un objet valide *étant donné* un schéma, sans contenu d'entrée à transformer. Il ne mesure pas la justesse des valeurs (value accuracy).
- **Pertinent pour un déploiement on-premise ?** Très utile : tous les moteurs gagnants (Guidance, Llamacpp, XGrammar, Outlines) sont open-source et s'intègrent à des LLM auto-hébergés ; les métriques d'efficacité (GCT/TTFT/TPOT) sont directement exploitables pour dimensionner une infra.
- **Biais.** Schémas majoritairement issus de GitHub/Kubernetes/function-calling → biais « configuration logicielle », loin des documents métier (factures, pièces d'identité). Drafts JSON Schema hétérogènes (beaucoup de draft-04 et de versions « unknown »).
- **Limites.** Couverture empirique mesurée en top-1 et avec un petit modèle (Llama-3.2-1B). Ne dit rien de la qualité sémantique des valeurs extraites.
- **Modèles/moteurs avantagés.** Moteurs à compilation incrémentale et *token healing* (Guidance). Moteurs permissifs (XGrammar) gonflent la couverture déclarée.
- **Modèles/moteurs pénalisés.** Moteurs à compilation lourde (Outlines, regex) ; implémentations conservatrices (OpenAI/Gemini) couvrant peu de fonctionnalités.

## 6. Recommandation

| Critère | Note /10 | Justification |
|---|---|---|
| Extraction de données non structurées | 3 | Aucune source à extraire ; mesure la conformité de génération, pas le mapping document→structure. |
| Génération de JSON | 8 | Référence sur la conformité JSON Schema et le choix du moteur de contrainte ; expose la chute de couverture sur schémas complexes. |
| Structuration automatique de documents | 4 | Informe la fiabilité de format, pas la transformation de documents réels en structure. |
| Workflows RAG | 4 | Pertinent pour la fiabilité de la couche de formatage, mais aucune dimension de récupération ni de *grounding*. |
| Workflows de traitement documentaire | 4 | Utile pour calibrer le décodage contraint d'un pipeline ; n'évalue pas la justesse des valeurs. |

**Sources**
- Geng et al., « JSONSchemaBench / Generating Structured Outputs from Language Models », arXiv:2501.10868 — https://arxiv.org/abs/2501.10868 et https://arxiv.org/html/2501.10868v3
- Dépôt officiel : https://github.com/guidance-ai/jsonschemabench (miroir https://github.com/epfl-dlab/jsonschemabench)
- Dataset : https://huggingface.co/datasets/epfl-dlab/JSONSchemaBench

---

# 2. StructEval

## 1. Présentation du benchmark

**Objectif.** StructEval (Yang, Jiang et al., University of Waterloo / TIGER-Lab ; arXiv 2505.20139) évalue la capacité des **LLM** à produire des sorties structurées dans des formats **non rendus** (JSON, YAML, CSV, XML, TOML) et **rendus** (HTML, React, SVG, Mermaid, LaTeX…).

**Problème mesuré.** La plupart des benchmarks évaluent la qualité sémantique ou le raisonnement, peu la *conformité de format* sur une large palette de formats. StructEval comble ce vide avec une évaluation automatisée de la fidélité structurelle.

**Capacités évaluées.** Deux paradigmes : (1) **génération** (langage naturel → format structuré) et (2) **conversion** (format → format). Deux sous-ensembles : **StructEval-T** (texte) et **StructEval-V** (visuel/rendu).

**Contexte d'utilisation.** Comparer des LLM sur leur aptitude à produire du code/format directement exploitable (pipelines de données, génération d'UI, documentation, publication scientifique).

**Cas d'usage visés.** Génération de JSON pour API, YAML/TOML pour config, HTML/React pour UI, LaTeX/Markdown pour rédaction technique, conversions inter-formats.

## 2. Données d'évaluation

**Description du dataset.** 2 035 exemples, 44 tâches, 18 formats. StructEval-T : 950 exemples, 19 tâches (5 génération + 14 conversion). StructEval-V : 1 085 exemples, 25 tâches (13 génération + 12 conversion). Construction par pipeline en 3 étapes : sélection de tâches, synthèse par LLM, **double relecture humaine** (LabelStudio). Dataset HuggingFace `TIGER-Lab/StructEval`.

> Divergence à signaler : l'abstract et le site mentionnent **18 formats**, mais l'introduction du papier mentionne « 21 distinct formats ». Le chiffre cohérent retenu dans le dataset et le leaderboard est **18**.

**Structure des entrées.** Un prompt en langage naturel décrivant la tâche + des *feature requirements* explicites (ex. « champ `authors` = liste de 2 éléments »), avec un gabarit imposant des balises `<|BEGIN_CODE|>` / `<|END_CODE|>`.

**Structure des sorties attendues.** Le format demandé (JSON, HTML…). Chaque exemple est un triplet (question, mots-clés attendus, paires VQA pour le visuel).

### Exemple 1 — StructEval-T, génération JSON (issu de la documentation officielle)

**Entrée (prompt) :**
```
Please output JSON code.
Task: Summarize metadata about a fictional scientific article.
Feature Requirements:
1. Top-level field "title" is a string
2. Field "authors" is a list of exactly two items
3. Each author has "name" and "affiliation"
4. Field "publication.year" is an integer
5. Field "keywords" is a list of strings
```
**Sortie attendue (mots-clés / dot-paths vérifiés) :** `title`, `authors[0].name`, `authors[1].affiliation`, `publication.year`, `keywords[2]`.
**Ce qui est évalué :** la sortie parse-t-elle (Syntax Score) et contient-elle les chemins imbriqués attendus (Keyword Matching via dot-path) ?
**Pourquoi représentatif :** teste la fidélité structurelle imbriquée (listes, objets, types) au-delà de la simple validité JSON.

### Exemple 2 — StructEval-V, génération HTML

**Entrée (prompt) :** « Concevoir une page d'itinéraire de voyage : `<h1>` centré "Trip Summary" ; `<table>` 3 lignes × 2 colonnes ; classe "highlight" sur la 2ᵉ ligne ; `<button>` "Export PDF". »
**Sortie attendue :** code HTML rendu, vérifié par paires VQA (« Combien de lignes dans le tableau ? → 3 », « Quelle classe sur la 2ᵉ ligne ? → highlight »).
**Ce qui est évalué :** Render Score (le code se rend-il ?), Keyword Matching, puis VQA Score via un VLM (GPT-4.1-mini).
**Pourquoi difficile :** exige un raisonnement spatial/visuel ; les formats visuels rares (Mermaid, TikZ, SVG) restent < 50 %.

## 3. Métriques d'évaluation

| Métrique | Description / calcul | Avantages | Limites |
|---|---|---|---|
| **Render Score** | Binaire (0/1) : le code se charge/rend-il sans erreur de syntaxe ? | Vérification objective et exécutable. | Ne dit rien du contenu correct. |
| **Syntax Score** (T) | % de règles dot-path satisfaites (existence des clés, relations, hiérarchie). | Capte la correction structurelle fine, y compris imbrication. | Vérifie la présence des clés, pas la justesse des valeurs métier. |
| **Keyword Matching** (V) | % de mots-clés attendus présents (exact match / regex). | Simple, automatisable. | Match de surface ; sensible à la formulation. |
| **VQA Score** (V) | % de paires Q/R satisfaites par le rendu, jugées par un VLM (GPT-4.1-mini). | Évalue la fidélité *visuelle* réelle. | Dépend de la fiabilité du VLM juge → biais d'auto-évaluation par modèle propriétaire. |
| **Score final (T)** | `0.2·Render + 0.8·Syntax` | Pondère validité et structure. | Pondération fixe, discutable selon le cas d'usage. |
| **Score final (V)** | `0.2·Render + 0.1·Keyword + 0.7·VQA` | Met l'accent sur le rendu visuel. | Forte dépendance au VLM juge. |

## 4. Leaderboard

Évaluation *zero-shot*, *greedy decoding*, température 0 (Table 5 du papier). Scores moyens sur 100.

| Rang | Modèle | Organisation | Score (Avg) | Métrique | Date |
|---|---|---|---|---|---|
| 1 | GPT-4o | OpenAI | **76,02** | StructEval Avg | Mai 2025 |
| 2 | GPT-4.1-mini | OpenAI | 75,64 | StructEval Avg | Mai 2025 |
| 3 | o1-mini | OpenAI | 75,58 | StructEval Avg | Mai 2025 |
| 4 | GPT-4o-mini | OpenAI | 73,19 | StructEval Avg | Mai 2025 |
| 5 | Gemini-1.5-pro | Google | 71,75 | StructEval Avg | Mai 2025 |
| 6 | **Qwen3-4B** (meilleur open-source) | Alibaba | 67,04 | StructEval Avg | Mai 2025 |
| 7 | Gemini-2.0-flash | Google | 62,55 | StructEval Avg | Mai 2025 |
| 8 | Llama-3.1-8B-Instruct | Meta | 61,77 | StructEval Avg | Mai 2025 |
| 9 | Qwen2.5-7B-Instruct | Alibaba | 59,03 | StructEval Avg | Mai 2025 |
| 10 | Phi-4-mini-instruct | Microsoft | 56,97 | StructEval Avg | Mai 2025 |
| 11 | Meta-Llama-3-8B-Instruct | Meta | 51,59 | StructEval Avg | Mai 2025 |
| 12 | Phi-3-mini-128k-instruct | Microsoft | 40,79 | StructEval Avg | Mai 2025 |

> **Divergence à signaler.** L'abstract du papier écrit « even state-of-the-art models like o1-mini achieve only 75.58 » et mentionne « Llama-3-8B » comme meilleur open-source ; or la table finale et le site officiel (« Key Findings ») désignent **GPT-4o (76,02) comme premier** et **Qwen3-4B (67,04) comme meilleur open-source**. Le texte de l'abstract est donc incohérent avec ses propres résultats détaillés ; les chiffres de la Table 5 / du site font foi.

**Faits saillants.** Tâches saturées (>90 %) : Text→JSON, Text→HTML, Text→CSV, YAML→JSON, React→HTML. Tâches très difficiles (<50 % tous modèles) : Text→TOML (35,8 %), Text→Mermaid (18,9 %), Matplotlib→TikZ (28,4 %). Sur StructEval-T génération JSON spécifiquement, GPT-4o ≈ 99,4, GPT-4.1-mini ≈ 99,3, Qwen3-4B ≈ 91,0 — c'est-à-dire que la génération JSON pure est largement résolue et peu discriminante.

*Leaderboard interactif officiel : https://tiger-ai-lab.github.io/StructEval/ (tableau chargé dynamiquement).*

## 5. Analyse critique

- **Pertinent pour la génération de JSON ?** Oui mais peu discriminant : Text→JSON est saturé (≥90 %). L'intérêt de StructEval est sa largeur de formats, pas la finesse sur JSON.
- **Pertinent pour l'extraction d'information ?** Faiblement. Génération à partir de consignes NL ou conversion format→format — pas d'extraction depuis un document métier, pas de mesure de justesse de valeur (faithfulness).
- **Pertinent pour un déploiement on-premise ?** Modérément : il classe des modèles open-source (Qwen, Llama, Phi) testés via vLLM, ce qui aide à présélectionner un modèle auto-hébergeable — mais le meilleur open-source (Qwen3-4B) reste ~9 points sous GPT-4o.
- **Biais.** (1) Données générées par LLM puis revues — biais résiduels possibles. (2) Juge VQA = GPT-4.1-mini (modèle OpenAI) → avantage potentiel aux modèles OpenAI sur le volet visuel. (3) Forte pondération du rendu visuel, peu pertinent pour l'extraction documentaire texte.
- **Limites.** Pas d'interactivité ; pas de *grounding* ; pas de justesse de valeur ; un seul run, température 0.
- **Modèles avantagés.** Grands modèles propriétaires (raisonnement, formats rares), modèles à fort raisonnement (Qwen3-4B, o1-mini sur la conversion T).
- **Modèles pénalisés.** Petits modèles à raisonnement faible (Phi-3-mini), pénalisés sur conversions T (erreurs de balises, hiérarchies CSV→JSON).

## 6. Recommandation

| Critère | Note /10 | Justification |
|---|---|---|
| Extraction de données non structurées | 3 | Génération depuis consignes / conversion ; pas d'extraction depuis source documentaire. |
| Génération de JSON | 6 | Couvre Text→JSON et conversions, mais JSON saturé → faible pouvoir discriminant. |
| Structuration automatique de documents | 5 | Les tâches de conversion sont pertinentes ; absence de mapping document brut → structure. |
| Workflows RAG | 3 | Aucune récupération, aucun *grounding*, aucune faithfulness. |
| Workflows de traitement documentaire | 4 | Fidélité de format utile ; pas de justesse de valeur ni de source réelle. |

**Sources**
- Yang, Jiang et al., « StructEval », arXiv:2505.20139 — https://arxiv.org/abs/2505.20139 et https://arxiv.org/html/2505.20139v1
- Site officiel + leaderboard : https://tiger-ai-lab.github.io/StructEval/
- Code : https://github.com/TIGER-AI-Lab/StructEval — Dataset : https://huggingface.co/datasets/TIGER-Lab/StructEval

---

# 3. Structured Output Benchmark (SOB)

> Désambiguïsation : « SOB » désigne ici **The Structured Output Benchmark** d'Interfaze / JigsawStack (arXiv 2604.25359). À ne pas confondre avec **SO-Bench** (arXiv 2511.21750, benchmark *multimodal* distinct) ni avec les jeux de données « structured output » de Cleanlab.

## 1. Présentation du benchmark

**Objectif.** SOB évalue la **qualité réelle des valeurs** d'une sortie structurée — pas seulement la conformité de schéma. Il vise les déploiements où des LLM extraient des données structurées depuis des sources non/semi-structurées (factures, dossiers médicaux, conversion de PDF en entrées de base de données).

**Problème mesuré.** Les benchmarks existants se concentrent soit sur la conformité de schéma seule, soit sur la justesse de valeur dans un seul domaine. SOB démontre l'écart critique : la plupart des modèles dépassent 95 % de « JSON Pass » mais leur **Value Accuracy** est 15 à 30 points plus basse. C'est précisément cet écart qui compte en production.

**Capacités évaluées.** Extraction et structuration de valeurs *grounded* dans le contexte source, sur trois modalités sources : **texte natif, image (PDF OCRisé), audio (conversations)** — toutes converties en contexte textuel normalisé pour isoler la capacité de structuration de la qualité vision/ASR.

**Contexte d'utilisation.** Sélection d'un modèle pour un pipeline d'extraction documentaire en production, où l'on doit pouvoir faire confiance aux valeurs sans relecture humaine.

**Cas d'usage visés.** Parsing de factures, dossiers médicaux, PDF multi-colonnes → JSON ; extraction multi-hop ; documents OCRisés.

## 2. Données d'évaluation

**Description du dataset.** 5 000 enregistrements d'évaluation texte (tirés d'un corpus complet de 25 091, à partir de QA multi-hop), 209 enregistrements image (PDF OCRisés via olmOCR-bench, ≥7 types de documents dont mises en page multi-colonnes), 115 enregistrements audio (AMI Meeting Corpus, transcriptions multi-locuteurs ~7 300 tokens). Chaque enregistrement est apparié à un **JSON Schema** et une **vérité terrain** rédigée par revue humaine puis recontrôlée par un LLM relecteur (Gemini 2.5 Flash) signalant champs manquants, types incohérents, valeurs non *grounded*. Taux d'erreur résiduel estimé ~3 % sur le texte après relecture. Dataset HuggingFace `interfaze-ai/sob`, code `github.com/JigsawStack/sob`.

| Modalité | Source | Enregistrements évalués |
|---|---|---|
| Texte | Passages HotpotQA | 5 000 |
| Image | Documents olmOCR-bench | 209 |
| Audio | Conversations AMI Meeting Corpus | 115 |

**Structure des entrées.** Contexte textuel normalisé (même pour image/audio) + un JSON Schema (étiqueté easy / medium / hard).
**Structure des sorties attendues.** Un objet JSON conforme au schéma, dont chaque valeur feuille doit correspondre exactement à la vérité terrain.

### Exemple 1 (représentatif, dérivé de la documentation officielle)

**Entrée :** un passage texte (style HotpotQA) + un schéma demandant, par exemple, `{"person": {"name": str, "birth_year": int}, "awards": [str]}`.
**Sortie attendue :** valeurs exactes *grounded* dans le passage.
**Ce qui est évalué :** Value Accuracy (correspondance feuille à feuille), Faithfulness (valeur ancrée dans la source vs hallucinée), plus les métriques structurelles.
**Pourquoi représentatif :** la documentation officielle illustre un cas qui obtient un score parfait sur toutes les métriques structurelles mais seulement **0,667 en Value Accuracy** — exactement l'écart que le benchmark cherche à exposer.

### Exemple 2 (modalité image — OCR de PDF)

**Entrée :** un document PDF multi-colonnes OCRisé (normalisé en texte) + schéma d'extraction.
**Sortie attendue :** champs extraits corrects malgré le bruit OCR / la mise en page complexe.
**Ce qui est évalué :** robustesse de l'extraction sur documents réels. Le meilleur Value Accuracy en image plafonne à **67,2 %** (Gemma-4-31B), illustrant la difficulté sur documents.
**Pourquoi pertinent :** c'est le cas le plus proche d'une extraction JSON on-premise depuis des pièces documentaires.

## 3. Métriques d'évaluation

| Métrique | Description / calcul | Avantages | Limites |
|---|---|---|---|
| **Value Accuracy** | Correspondance exacte feuille à feuille vs vérité terrain. *La* métrique de production. | Mesure ce qui compte réellement : valeurs exploitables sans relecture. | Match exact → sensible aux variantes légitimes de formatage. |
| **Faithfulness** | Fréquence à laquelle les valeurs sont ancrées dans le contexte source plutôt qu'hallucinées. | Cœur de la fiabilité RAG / anti-hallucination. | Dépend de la qualité de la vérité terrain. |
| **JSON Pass** | La réponse est-elle un JSON parsable ? | Pré-requis. | Saturé (>95 % pour quasi tous) → non discriminant. |
| **Path Recall** | Toutes les clés requises sont-elles présentes ? | Détecte les champs manquants. | Près du plafond pour les modèles frontière. |
| **Structure Coverage** | Objets/tableaux imbriqués présents avec la bonne forme ? | Capte la fidélité structurelle. | Près du plafond. |
| **Type Safety** | Les valeurs feuilles respectent-elles les types déclarés ? | Détecte les erreurs de type. | Près du plafond. |
| **Perfect Response** | Fraction d'enregistrements où *toutes* les valeurs sont exactes. | Métrique la plus exigeante. | Chute à ~50 % même pour les meilleurs. |

**Garde-fous (gates).** *Hardening gate* : si le JSON ne parse pas, toutes les métriques sémantiques sont mises à 0 pour cet enregistrement. *Coverage gate* : la Value Accuracy n'est créditée que sur les champs réellement retournés (champ manquant = faux). Classement final **pondéré par la complexité du schéma** (easy=1, medium=2, hard=3). Exécution à température 0, max 2 048 tokens, sans *reasoning*.

## 4. Leaderboard

Classement officiel (Interfaze, 28 modèles sur texte+image, 27 sur audio), moyenne pondérée par difficulté sur les 7 métriques. Extrait du haut de tableau.

| Rang | Modèle | Organisation | Overall | Value Acc | Faithfulness | JSON Pass | Date |
|---|---|---|---|---|---|---|---|
| 1 | GPT-5.4 | OpenAI | 87,0 % | 79,8 % | 86,9 % | 99,3 % | 2026 |
| 2 | Gemini-3.1-Pro | Google | 86,9 % | 82,0 % | 87,6 % | 96,6 % | 2026 |
| 3 | GLM-5.1 | Z.ai | 86,6 % | 80,6 % | 87,2 % | 97,5 % | 2026 |
| 4 | Claude-Opus-4.7 | Anthropic | 86,4 % | 78,7 % | 87,7 % | 99,3 % | 2026 |
| 5 | GLM-4.7 | Z.ai | 86,1 % | 80,4 % | 86,8 % | 96,5 % | 2026 |
| 6 | Qwen3.5-35B | Alibaba | 86,1 % | 80,1 % | 86,3 % | 96,9 % | 2026 |
| 7 | Interfaze-Beta | Interfaze/JigsawStack | 86,0 % | 80,5 % | 86,1 % | 96,6 % | 2026 |
| 8 | GPT-5.5 | OpenAI | 86,0 % | 79,5 % | 86,8 % | 97,8 % | 2026 |
| 9 | Gemini-2.5-Flash | Google | 86,0 % | 79,6 % | 85,6 % | 97,2 % | 2026 |
| 10 | Qwen3-235B | Alibaba | 85,7 % | 78,6 % | 85,4 % | 97,8 % | 2026 |
| 11 | Claude-Sonnet-4.6 | Anthropic | 85,4 % | 77,9 % | 85,8 % | 97,9 % | 2026 |
| … | (jusqu'à 28 modèles) | | | | | | |
| 23 | Schematron-8B | (extraction-spécialisé) | 83,2 % | 73,1 % | 80,7 % | 98,7 % | 2026 |
| 25 | Phi-4 | Microsoft | 83,1 % | 78,7 % | 84,9 % | 96,9 % | 2026 |
| 28 | GPT-OSS-20B | OpenAI | 73,2 % | 66,7 % | 73,0 % | 84,5 % | 2026 |

**Meilleure Value Accuracy par modalité :** Texte 84,5 % (Gemini-3.1-Pro) · Image 67,2 % (Gemma-4-31B) · Audio 23,7 % (Gemini-2.5-Flash). Aucun modèle ne domine les trois modalités (ex. GPT-5.4 : 1er global mais 13ᵉ en image ; Gemma-4-31B : 18ᵉ en texte mais 1er en image). Constat de méthode : le décodage contraint par schéma n'est « pas gratuit » — il aide le JSON Pass pour certains modèles, le dégrade pour d'autres, et ne déplace presque pas la Value Accuracy.

> Note de fraîcheur : ce benchmark et son leaderboard datent de 2026 (postérieurs à de nombreuses bases de connaissances). Les noms de modèles (GPT-5.4, Gemini-3.1-Pro, Claude-Opus-4.7, GLM-5.1…) reflètent l'état du leaderboard officiel à la date de consultation.

## 5. Analyse critique

- **Pertinent pour la génération de JSON ?** Oui, et plus utilement que les autres : il montre que le JSON Pass est saturé et déplace l'attention vers la justesse de valeur et la sûreté de type.
- **Pertinent pour l'extraction d'information ?** Très fortement — c'est sa raison d'être. Value Accuracy + Faithfulness sur sources réelles (texte, OCR, audio) répondent directement au besoin d'extraction.
- **Pertinent pour un déploiement on-premise ?** Oui : présence de nombreux modèles open-weight (Qwen, GLM, Gemma, Phi, Granite, Nemotron, GPT-OSS, Schematron) avec scores par modalité, et l'observation « la modalité compte plus que la taille » aide à choisir un modèle auto-hébergeable selon le type de document.
- **Biais.** (1) **Conflit d'intérêt potentiel** : Interfaze/JigsawStack est un éditeur commercial, et son propre modèle « Interfaze-Beta » figure 7ᵉ — à interpréter avec prudence. (2) Vérité terrain recontrôlée par un LLM (Gemini 2.5 Flash) → biais possible. (3) Sources texte = HotpotQA (QA multi-hop), pas des documents métier type facture/pièce d'identité.
- **Limites.** Image/audio en petit volume (209 / 115). Normalisation texte → ne mesure pas la chaîne vision/OCR de bout en bout (choix délibéré, mais à compléter par un test OCR réel). Match exact de valeur potentiellement sévère.
- **Modèles avantagés.** Modèles forts en *grounding* et fidélité ; spécifique à la modalité (un 35B open peut battre un propriétaire frontière sur texte).
- **Modèles pénalisés.** Petits modèles peu robustes (Ministral-3-14B, GPT-OSS-20B) ; tous les modèles s'effondrent sur l'audio.

## 6. Recommandation

| Critère | Note /10 | Justification |
|---|---|---|
| Extraction de données non structurées | 9 | Conçu exactement pour cela : extraction de valeurs *grounded* depuis sources réelles, mesurée par Value Accuracy + Faithfulness. |
| Génération de JSON | 7 | Couvre JSON Pass / Type Safety / Structure, mais le différenciateur est la valeur, pas la conformité (saturée). |
| Structuration automatique de documents | 8 | Modalité image = PDF OCRisés multi-colonnes — proche du cas documentaire ; volume image modeste. |
| Workflows RAG | 8 | Faithfulness (ancrage vs hallucination) = préoccupation centrale RAG. |
| Workflows de traitement documentaire | 9 | Cadrage explicite « factures, dossiers médicaux, PDF→base » ; le plus aligné avec un pipeline d'extraction on-premise. |

**Sources**
- « The Structured Output Benchmark (SOB) », arXiv:2604.25359 — https://arxiv.org/abs/2604.25359 et https://arxiv.org/html/2604.25359v1
- Leaderboard officiel : https://interfaze.ai/leaderboards/structured-output-benchmark
- Blog : https://interfaze.ai/blog/introducing-structured-output-benchmark
- Dataset : https://huggingface.co/datasets/interfaze-ai/sob — Code : https://github.com/JigsawStack/sob

---

# 4. Berkeley Function Calling Leaderboard (BFCL)

## 1. Présentation du benchmark

**Objectif.** BFCL (Patil, Mao et al., UC Berkeley / projet Gorilla ; ICML 2025) évalue la capacité des LLM à **appeler des fonctions/outils** (function calling) avec précision. La version courante, **BFCL V4**, étend l'évaluation au domaine **agentique** (recherche web, mémoire, sensibilité au format).

**Problème mesuré.** Sélectionner la bonne fonction, formater correctement l'appel (arguments typés, JSON), gérer le résultat, sur des scénarios simples, parallèles, multiples, multi-tours et agentiques.

**Capacités évaluées.** Appels simples/multiples/parallèles, multi-tours, raisonnement agentique (web search multi-hop, mémoire lecture/écriture), détection d'hallucination (pertinence/non-pertinence), sensibilité au format. Langages : Python, Java, JavaScript, REST.

**Contexte d'utilisation.** Choisir un modèle pour des pipelines d'agents pilotés par API (ReAct, Plan-and-Execute) où la fiabilité de l'appel d'outil conditionne la chaîne de tâches.

**Cas d'usage visés.** Agents outillés, deep-research, automatisation de tâches, orchestration d'API.

## 2. Données d'évaluation

**Description du dataset.** ~2 000+ paires question-fonction-réponse à l'origine ; BFCL V4 compte ~5 088 entrées scorées et ~5 218 entrées non scorées (sensibilité au format). Données expert-curées (non-live) et contribuées par la communauté (live). Le volet Web Search ajoute 100 questions multi-hop rédigées et vérifiées manuellement (via DuckDuckGo Search API). Code et données : `github.com/ShishirPatil/gorilla`.

**Composition du score global V4 :** Agentique 40 % (Web Search + Mémoire), Multi-Turn 30 %, Live 10 %, Non-Live 10 %, Mesure d'hallucination 10 %. La sensibilité au format (26 configurations × 200 cas) est non scorée.

**Structure des entrées.** Une requête utilisateur + une ou plusieurs définitions de fonctions (signatures, types). Pour le web search : une question multi-hop + des outils `duckduckgo_search` et `fetch_url_content`.

**Structure des sorties attendues.** Un (ou des) appel(s) de fonction syntaxiquement et sémantiquement corrects, évalués par **AST** (Abstract Syntax Tree) ; pour l'agentique web, une réponse finale `{"answer", "context"}` évaluée en *exact match* normalisé sur le champ `answer`.

### Exemple 1 — appel de fonction (catégorie non-live, AST)

**Entrée :** « Quelle météo à Paris en Celsius ? » + signature `get_weather(location: str, unit: str)`.
**Sortie attendue :** `get_weather(location="Paris", unit="celsius")`.
**Ce qui est évalué :** correspondance AST (bon nom de fonction, bons arguments, bons types) sans exécution.
**Pourquoi représentatif :** baseline de l'appel simple ; l'AST permet une évaluation déterministe et fuzzy.

### Exemple 2 — web search multi-hop (V4 agentique)

**Entrée :** « Combien d'étages compte le plus haut bâtiment de la ville ayant reçu le plus de touristes internationaux en 2024 ? »
**Sortie attendue (chaîne) :** identifier Bangkok → trouver le plus haut bâtiment (Magnolias Waterfront Residences, Iconsiam) → réponse `{"answer": "70", …}`.
**Ce qui est évalué :** décomposition en sous-requêtes, sélection de mots-clés, lecture correcte du contenu, robustesse aux échecs réseau simulés (503/429/403/timeouts).
**Pourquoi difficile :** modes de défaillance documentés — éviter l'outil et halluciner depuis la mémoire paramétrique, mauvaise sélection de mots-clés, mauvaise lecture de la page.

## 3. Métriques d'évaluation

| Métrique | Description / calcul | Avantages | Limites |
|---|---|---|---|
| **AST Accuracy** | Correspondance de l'arbre syntaxique abstrait : nom de fonction, arguments, types vs vérité terrain. | Déterministe, reproductible, sans exécution ; cœur historique de BFCL. | Vérifie la forme de l'appel, pas son effet réel ; sensible aux paraphrases. |
| **Executable Accuracy** | Exécution réelle de l'appel et comparaison des sorties. | Vérifie l'effet fonctionnel. | Coûteux ; dépend d'environnements d'exécution. |
| **Multi-Turn / State-transition** | Vérification par transitions d'état sur dialogues multi-tours (base, fonction manquante, paramètre manquant, contexte long). | Capte les interactions réalistes. | Complexe à construire ; pondération fixe. |
| **Hallucination / Relevance-Irrelevance** | Le modèle s'abstient-il quand aucune fonction n'est pertinente, et appelle-t-il quand il le faut ? | Mesure la retenue (anti sur-déclenchement). | Binaire ; cas limites. |
| **Web Search exact-match** (V4) | *Exact match* normalisé (minuscules, ponctuation retirée) sur le champ `answer`. | Évite les faux positifs des réponses longues. | Sévère sur les variantes de formulation. |
| **Format Sensitivity** (non scoré) | Variation des configurations de format (tags, JSON/XML doc, markdown/plaintext) ×26. | Révèle la fragilité au formatage du prompt. | Non intégré au score global. |
| **Cost / Latency** | Estimation du coût total du benchmark (USD) et latence (s). | Critère opérationnel. | Estimations. |

## 4. Leaderboard

> **Avertissement fort sur les divergences.** Le tableau du **leaderboard officiel** (gorilla.cs.berkeley.edu/leaderboard.html, dernière mise à jour 2026-04-12, commit `f7cf735`, `bfcl-eval==2025.12.17`) est **rendu dynamiquement (JavaScript)** : son classement exact courant n'a pas pu être extrait de façon fiable lors de cette étude. Les agrégateurs tiers divergent nettement (et plusieurs sont *self-reported*, non vérifiés). **Le classement officiel fait foi** ; les chiffres ci-dessous sont à confirmer directement sur le site.

| Source | Tête de classement rapportée | Nature | Date |
|---|---|---|---|
| llm-stats.com/benchmarks/bfcl-v4 | Qwen3.7 Max 0,750 ; Qwen3.5-397B-A17B 0,729 ; Qwen3.5-122B-A10B 0,722 | Agrégateur, 9 modèles, **self-reported, 0 vérifié** | Juin 2026 |
| Grokipedia (citant la source officielle) | Famille Claude (Anthropic) en tête | Encyclopédie tierce | Mars 2026 |
| clickrank.ai (composite) | GPT-5 « leads BFCL » (~92 %+) | Agrégateur composite | Mai 2026 |
| emergentmind.com | ToolACE-8B > GPT-4 / Claude-3.5 ; Granite-20B meilleur open-licence | Synthèse (instantané ancien) | Fév 2026 |

Ces sources ne sont **pas réconciliables en l'état** (versions, sous-ensembles et méthodes d'agrégation différents). En conséquence, pour un classement BFCL V4 par modèle, l'information fiable et à jour doit être lue **directement sur le leaderboard officiel** :

> **Classement officiel exact par modèle à la date de l'étude : information non disponible de façon vérifiable dans les sources publiques consultées (tableau officiel rendu dynamiquement).**

Ce qui est solidement établi par la source officielle : la composition du score (Agentique 40 % / Multi-Turn 30 % / Live 10 % / Non-Live 10 % / Hallucination 10 %), la méthode AST, et le fait que les catégories agentiques (web search, mémoire) sont les plus discriminantes en V4.

## 5. Analyse critique

- **Pertinent pour la génération de JSON ?** Indirectement. Les arguments d'appel de fonction sont des structures JSON typées vérifiées par AST → bon signal de fiabilité de *formatage* d'appel, mais pas d'extraction depuis schéma.
- **Pertinent pour l'extraction d'information ?** Faiblement en V1–V3 (tool use). En V4, le volet **web search multi-hop** se rapproche d'un RAG agentique (récupérer, lire, synthétiser), mais il évalue l'orchestration d'outils, pas l'extraction structurée depuis un document.
- **Pertinent pour un déploiement on-premise ?** Oui pour le choix d'un modèle agentique auto-hébergé : BFCL classe de nombreux modèles open (Qwen, Granite, ToolACE, Llama…) et fournit coût/latence. Évaluable en local via le package `bfcl-eval`.
- **Biais.** Évaluation AST sensible aux paraphrases ; web search via DuckDuckGo (choix délibéré, mais résultats moins « optimaux » que Google/Bing) ; risque de fuite mémoire paramétrique sur questions récentes (mitigé par renouvellement des questions).
- **Limites.** Volume web search modeste (100 questions) ; format sensitivity non scoré ; classement officiel difficile à figer (mises à jour fréquentes, table dynamique).
- **Modèles avantagés.** Modèles fortement post-entraînés au function calling natif (FC) et au raisonnement multi-étapes ; modèles RL-optimisés tool use (ToolACE, FunRL, RC-GRPO).
- **Modèles pénalisés.** Modèles « prompt-only » sans support FC natif, fragiles à la sensibilité de format ; modèles qui hallucinent au lieu d'appeler l'outil.

## 6. Recommandation

| Critère | Note /10 | Justification |
|---|---|---|
| Extraction de données non structurées | 2 | Mesure le tool use, pas l'extraction depuis documents. |
| Génération de JSON | 5 | Arguments d'appel = JSON typé vérifié AST → signal de fiabilité de formatage, mais pas d'extraction sous schéma. |
| Structuration automatique de documents | 2 | Hors périmètre (orchestration d'outils). |
| Workflows RAG | 5 | Le volet web search V4 est un proxy de RAG agentique (récupérer/lire/synthétiser), sans extraction structurée. |
| Workflows de traitement documentaire | 2 | Non documentaire. Utile seulement si le pipeline doit *appeler* des outils d'extraction. |

**Sources**
- Patil, Mao et al., « The Berkeley Function Calling Leaderboard (BFCL): From Tool Use to Agentic Evaluation », ICML 2025 — leaderboard officiel : https://gorilla.cs.berkeley.edu/leaderboard.html
- Blog BFCL V4 (Web Search) : https://gorilla.cs.berkeley.edu/blogs/15_bfcl_v4_web_search.html
- Code et données : https://github.com/ShishirPatil/gorilla/tree/main/berkeley-function-call-leaderboard
- Agrégateurs (divergents, à recouper) : https://llm-stats.com/benchmarks/bfcl-v4 · https://grokipedia.com/page/Berkeley_Function_Calling_Leaderboard

---

# Synthèse comparative pour un choix d'architecture

| Benchmark | Ce qu'il mesure vraiment | Extraction doc. /10 | Génération JSON /10 | Structuration doc. /10 | RAG /10 | Traitement doc. /10 | Pertinence pour un pipeline d'extraction JSON on-premise |
|---|---|---|---|---|---|---|---|
| **SOB** | Justesse des valeurs extraites (texte/OCR/audio) | 9 | 7 | 8 | 8 | 9 | **La plus élevée** — value accuracy + faithfulness, modalité image OCR |
| **JSONSchemaBench** | Fiabilité des moteurs de décodage contraint | 3 | 8 | 4 | 4 | 4 | Élevée pour **choisir la couche de contrainte** (Guidance/XGrammar/llama.cpp) |
| **StructEval** | Génération/conversion multi-formats par LLM | 3 | 6 | 5 | 3 | 4 | Moyenne — présélection de modèles open-source, JSON peu discriminant |
| **BFCL** | Function calling / agentique | 2 | 5 | 2 | 5 | 2 | Faible pour l'extraction ; pertinente si l'architecture est agentique/outillée |

**Recommandation d'usage combiné.** Pour un projet d'extraction JSON on-premise depuis des documents (ex. pièces d'identité) :
1. **SOB** pour sélectionner le modèle d'extraction (privilégier Value Accuracy et Faithfulness, regarder spécifiquement la **modalité image**), tout en gardant à l'esprit le biais éditeur et en complétant par un test OCR de bout en bout sur vos propres documents.
2. **JSONSchemaBench** pour choisir et calibrer la **couche de décodage contraint** (Guidance ressort comme le plus fiable ; vérifier la couverture sur vos schémas réels, souvent complexes).
3. **StructEval** comme filtre secondaire pour présélectionner des modèles open-source auto-hébergeables.
4. **BFCL** uniquement si l'architecture cible est agentique (le modèle doit appeler des outils d'extraction/recherche).

> Rappel d'honnêteté méthodologique : aucun score n'a été inventé. Lorsqu'une donnée n'était pas vérifiable (classement officiel BFCL V4 par modèle), cela a été indiqué explicitement. Les divergences entre sources (StructEval abstract vs table ; BFCL agrégateurs) ont été signalées. Je ne suis ni avocat ni conseiller financier ; cette étude est un support technique d'aide à la décision d'architecture.