# Documentation — Veille Analytics Engineering

Newsletter technique mensuelle Converteo destinée aux clients. Elle présente une sélection d’articles récents en Analytics Engineering (dbt, Snowflake, BigQuery, Power BI, gouvernance, CI/CD, IA, etc.) sous forme de cartes bilingues FR/EN, avec impact opérationnel pour un Analytics Engineer.

Cette documentation décrit **l’état actuel du dépôt**, le **processus manuel en place**, et le **pipeline automatisé prévu** (non implémenté dans le code au moment de la rédaction).

---

## 1. Objectif produit

| Besoin | Réponse du projet |
|--------|-------------------|
| Informer les clients | Page web type newsletter (`index.html`) |
| Contenu actionnable | Résumé + impact équipe par article |
| Bilingue | FR / EN, bascule dans l’interface |
| Fiabilité des liens | Reconstruction d’URL + ping HTTP anti-hallucination |
| Diffusion | Édition mensuelle, export PDF (impression navigateur) |

Public cible : Analytics Engineers, responsables data, consultants BI.

---

## 2. Architecture actuelle (ce qui existe dans le repo)

```
[Agent externe / Gemini]
        │  recherche web + rédaction
        ▼
   copier-coller manuel
        │
        ▼
  test veille.txt          ← JSON brut (base_domaine + chemin_complet)
        │
        ▼
     sync.py               ← reconstruction URL, ping HTTP, validation schéma
        │
        ▼
     data.json             ← JSON certifié (clé "lien")
        │
        ▼
    index.html             ← newsletter (fetch data.json)
```

**Point de friction** : l’étape agent → `test veille.txt` est manuelle. C’est ce que le pipeline prévu vise à supprimer.

---

## 3. Carte des fichiers

| Fichier | Rôle |
|---------|------|
| `index.html` | Interface newsletter (Tailwind CDN, JS vanilla) |
| `data.json` | Articles validés, lus par la page |
| `test veille.txt` | Sortie brute de l’agent (entrée de `sync.py`) |
| `sync.py` | Validation, reconstruction des liens, écriture de `data.json` |
| `contexte.md` | Schéma de données et consignes métier |
| `Logos_RVB_Converteo.svg` | Logo header |
| `.github/workflows/monthly-sync.yml` | CI prévue (incomplète : lance `sync.py` sans génération) |
| `.gitignore` | Ignore `.env`, `credentials.json`, `__pycache__/` |

Pas de `README.md`, pas de `requirements.txt`, pas de `generate.py` dans le dépôt actuel.

---

## 4. Schéma des données

### 4.1 Sortie agent (`test veille.txt`)

L’agent **ne produit pas** de clé `lien`. Il découpe l’URL pour éviter les blocages / hallucinations :

| Clé | Description | Exemple |
|-----|-------------|---------|
| `titre_en` | Titre original | `CoCoEvolve: What If a Coding Agent Could…` |
| `titre_fr` | Traduction professionnelle | `CoCoEvolve : Et si un agent de codage…` |
| `source` | Nom lisible du média | `Snowflake` |
| `resume_fr` | Exactement 2 phrases | … |
| `resume_en` | Traduction fidèle | … |
| `base_domaine` | Domaine, points remplacés par des espaces, **sans** chemin | `cloud google com` |
| `chemin_complet` | Chemin après le domaine, **sans** slash initial | `blog/products/…/nom-article` |
| `date` | Publication `JJ/MM/AAAA` | `03/06/2026` |
| `impact_fr` | Impact opérationnel (1 phrase) | … |
| `impact_en` | Traduction | … |
| `categorie` | Une parmi : DevOps, Gouvernance, BI, CI/CD, AI, Infrastructure, Best Practices | `AI` |
| `stack` | Une parmi : Google Cloud, Microsoft, AWS, Snowflake, Databricks, Multi-Stack | `Snowflake` |
| `score_fiabilite` | Entier 1 à 5 | `5` |
| `rationnel_source` | 1 phrase expliquant le score | … |


### 4.2 Sortie validée (`data.json`)

Identique, **plus** :

| Clé | Description |
|-----|-------------|
| `lien` | URL reconstruite `https://{domaine}/{chemin}` et vérifiée HTTP |

Les clés `base_domaine` et `chemin_complet` sont retirées après reconstruction.

`sync.py` lit les clés obligatoires depuis `contexte.md` (listes Markdown `- \`cle\``). La clé `lien` est donc exigée **après** reconstruction. Si une clé manque ou est vide, `data.json` n’est **pas** écrasé.

---

## 5. Interface (`index.html`)

Page statique, sans backend.

### Fonctionnalités

- Header Converteo + titre « Veille Analytics Engineering »
- Bascule **FR / EN**
- Libellé d’édition mensuelle (dérivé des dates d’articles)
- Export PDF via 
- Filtres catégories (Tous, Best Practices, AI, Gouvernance, BI, DevOps, …)
- Filtres stack (Google Cloud, Microsoft, AWS, Snowflake, Databricks, Multi-Stack)
- Recherche plein texte
- Compteur d’articles + temps de lecture estimé
- Cartes : badges, date, titre, source, résumé, impact équipe, bouton « Lire l’article »

### Stack UI

- Tailwind CSS v3 (CDN)
- Polices Inter + Montserrat
- Couleurs marque : violet `#3D1C69` / `#2E1452`, turquoise `#2BD6D9`

---

## 6. Script `sync.py`

Point d’entrée : `python sync.py` (à la racine du projet).

### Étapes

1. Lire `test veille.txt`
2. Extraire le tableau JSON entre le premier `[` et le dernier `]`
3. Normaliser les guillemets typographiques
4. Pour chaque article : fusionner `base_domaine` + `chemin_complet` → URL `https://…`
5. Ping HTTP (HEAD puis GET en repli). Codes 401/403/405/429 = URL considérée existante. 404 = rejet
6. Valider toutes les clés obligatoires (dont `lien`)
7. Écrire `data.json` (UTF-8, indent 2)

### Comportement de sécurité

- JSON invalide, tableau vide après filtrage, clé manquante → **exit 1**, `data.json` inchangé
- Articles sans `base_domaine` / `chemin_complet` : ignorés (warning)
- SSL non vérifié volontairement (`ssl._create_unverified_context`) pour limiter les faux négatifs TLS

### Écart doc / code

`contexte.md` et le workflow GitHub parlent encore de **Google Drive** (`credentials.json`, `token.json`). **`sync.py` ne parle plus à Google** : il lit uniquement `test veille.txt`. Les packages `google-api-python-client` installés en CI ne sont pas utilisés par le script actuel.

---

## 7. Processus actuel (manuel)

1. Exécuter l’agent (Gemini / autre) avec le prompt de veille
2. Copier la **PARTIE 1** (JSON) dans `test veille.txt`
3. Lancer `python sync.py`
4. Vérifier `data.json` et la page
5. Commit / push si besoin

La **PARTIE 2** (rapport d’audit des sources) n’est pas consommée par le code.

---

## 8. Prompt de veille (source de vérité métier)

Utilisé tel quel par l’agent. À versionner plus tard dans `prompts/veille.md`.

### Règles métier

- Fenêtre = **mois civil précédent** (si on est en juillet 2026 → 1er–30 juin 2026)
- **9 à 12** articles (le prompt mentionne aussi 12–15 comme volume de recherche ; le quota retenu est 9–12)
- **Max 2–3 articles par source**
- Exclure **Converteo**
- Prioriser les `site:` listés, puis élargir (Medium ingénierie, Dev.to, blogs d’entreprises) avec « Analytics Engineering », « Modern Data Stack », « Data Mesh » + mois + année
- Hors liste : rejeter fermes de contenu et tutos sans REX ; prioriser blogs d’ingénierie (Netflix, Airbnb, Uber, experts reconnus)

### Sources prioritaires (`site:`)

- `cloud.google.com/blog` (BigQuery, Dataform, Looker, Data Studio)
- `snowflake.com/en/blog`
- `learnanalyticsengineering.substack.com`
- `omni.co`
- `sqlbi.com`
- `githubnext.com`
- `powerbi.microsoft.com/blog`
- `about.gitlab.com/blog`
- `datageneration.co`

### Format de réponse attendu

1. **PARTIE 1** — JSON uniquement (pas de fence \`\`\`json), schéma ci-dessus
2. **PARTIE 2** — `RAPPORT DE VEILLE` : sources de la liste sans article ce mois-là ; sources en erreur / inaccessibles

---

## 9. GitHub Actions actuel

Fichier : `.github/workflows/monthly-sync.yml`

- Déclencheurs : cron + `workflow_dispatch`
- Job : checkout → Python 3.11 → installe les libs Google → `python sync.py` → commit `data.json` si diff

### Limites

| Problème | Détail |
|----------|--------|
| Cron | `* * 2 * *` = **toutes les minutes le 2 de chaque mois**. Valeur attendue : `0 6 1 * *` (ex. 1er du mois, 06:00 UTC) |
| Génération | Aucun appel LLM : suppose que `test veille.txt` est déjà à jour dans le repo |
| Auth Google | Étapes `token.json` / `credentials.json` commentées |
| Clé YAML | `python-run-version` n’est pas l’input standard d’`actions/setup-python` (`python-version`) |

---

## 10. Pipeline automatisé prévu (non dans le repo)

Objectif : **zéro copier-coller**. Une clé suffit : **`GEMINI_API_KEY`**.

```
Cron 1er du mois
    → generate.py
         charge prompts/veille.md
         injecte la date du jour
         Gemini + Grounding Google Search
         parse PARTIE 1 → test veille.txt
         parse PARTIE 2 → rapport-veille.md
    → sync.py (inchangé dans l’esprit)
         URLs + schéma → data.json
    → commit + push (+ GitHub Pages optionnel)
```

### Fichiers à ajouter (quand on implémentera)

| Fichier | Rôle |
|---------|------|
| `prompts/veille.md` | Prompt actuel, versionné |
| `generate.py` | Appel Gemini + parsing des 2 parties |
| `requirements.txt` | `google-genai>=1.0` |
| Workflow unifié | generate → sync → commit |

### Secret

- GitHub Actions : `GEMINI_API_KEY` (https://aistudio.google.com/apikey)
- Local : `export GEMINI_API_KEY="…"` — **jamais commitée**, jamais collée dans un chat

`sync.py` et `index.html` n’ont besoin d’aucune clé.

### Appel Gemini (esquisse)

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=prompt,
    config=types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch(
            exclude_domains=["converteo.com"]
        ))]
    ),
)
```

Le LLM **cherche** (Google Search, y compris `site:domaine.com` et le web hors liste). Il **ne doit pas inventer d’URL**. `sync.py` reste la barrière : reconstruction + ping HTTP, rejet des 404.

### Pourquoi pas une liste d’URL figées

La recherche se fait sur **tout le site** via `site:snowflake.com/en/blog`, etc., puis élargissement hors liste si le quota n’est pas atteint. Pas de flux RSS à maintenir.

---

## 11. Commandes utiles (état actuel)

```bash
# Valider un export agent déjà collé dans test veille.txt
python3 sync.py

# Prévisualiser la newsletter
python3 -m http.server 8080
```

Dépendances actuelles de `sync.py` : **stdlib uniquement** (`json`, `urllib`, `re`, `ssl`).

---

## 12. Garde-fous qualité

| Risque | Parade |
|--------|--------|
| URL inventée par le LLM | Pas de clé `lien` en entrée ; reconstruction + ping |
| Lien mort | Article retiré, pas d’écriture partielle de `data.json` si le lot devient invalide |
| JSON malformé | Extraction `[`…`]` + `JSONDecodeError` bloquante |
| Schéma incomplet | Clés lues depuis `contexte.md` |
| Doublons de source | Règle 2–3 max dans le prompt (pas encore enforced dans `sync.py`) |
| Fenêtre de dates | Calcul mois précédent dans le prompt (pas encore enforced dans `sync.py`) |

---

## 13. Pistes d’évolution (rappel)

1. Versionner le prompt dans `prompts/veille.md`
2. Implémenter `generate.py` (Gemini + Google Search)
3. Corriger le workflow : cron, `python-version`, enchaînement generate → sync
4. Optionnel : `rapport-veille.md` versionné, notification Slack, GitHub Pages
5. Harmoniser `contexte.md` (retirer Google Drive si on n’y revient pas)

---

