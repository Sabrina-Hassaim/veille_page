# Veille Analytics Engineering

Newsletter technique mensuelle Converteo : une sélection d’articles récents (dbt, Snowflake, BigQuery, Power BI, gouvernance, CI/CD, IA, etc.) en cartes bilingues FR/EN, avec impact opérationnel pour un Analytics Engineer.

## Pipeline

```
Gemini + Google Search          sync.py                         index.html
generate.py  →  test veille.txt  →  data.json (URLs vérifiées)  →  newsletter
             →  rapport-veille.md
```

1. **`generate.py`** exécute le prompt (`prompts/veille.md`) via Gemini avec grounding Google Search.
2. **`sync.py`** reconstruit chaque URL (`base_domaine` + `chemin_complet`), ping HTTP, valide le schéma, écrit `data.json`.
3. **`index.html`** affiche `data.json` (filtres, FR/EN, export PDF).

La clé API **n’est jamais** dans le dépôt.

## Prérequis

- Python 3.11+
- Une clé Gemini (`GEMINI_API_KEY`) sur le projet GCP, API **Generative Language** activée

```bash
python -m pip install -r requirements.txt
cp .env.example .env   # y coller la clé, fichier ignoré par Git
export GEMINI_API_KEY="…"   # ou source .env
```

## Commandes

```bash
# Génération (appelle Gemini, coûte quelques requêtes Search)
python generate.py

# Validation des URLs + data.json
python sync.py

# Prévisualiser la newsletter
python3 -m http.server 8080
# http://localhost:8080/index.html
```

## GitHub Actions

Workflow `.github/workflows/monthly-sync.yml` :

- Cron : 1er de chaque mois, 06:00 UTC
- Lancement manuel : **Actions → Monthly Newsletter Sync → Run workflow**
- Secret obligatoire : `GEMINI_API_KEY` (Settings → Secrets and variables → Actions)

Le job enchaîne `generate.py` → `sync.py` → commit de `data.json`, `test veille.txt` et `rapport-veille.md`.

## Schéma

L’agent ne produit **pas** de clé `lien`. `sync.py` fusionne :

- `base_domaine` : `cloud google com`
- `chemin_complet` : `blog/products/.../nom-article`

puis vérifie `https://cloud.google.com/blog/products/.../nom-article`. Un 404 fait tomber l’article. Si le lot restant est invalide, `data.json` n’est pas écrasé.

Les clés obligatoires sont listées dans `contexte.md`.

## Fichiers

| Fichier | Rôle |
|---------|------|
| `prompts/veille.md` | Prompt métier (mois précédent, 9–12 articles, sources `site:`) |
| `generate.py` | Appel Gemini + parse JSON / rapport |
| `sync.py` | Anti-hallucination HTTP + schéma |
| `data.json` | Articles certifiés pour l’UI |
| `index.html` | Newsletter |
| `rapport-veille.md` | Audit des sources (généré) |
