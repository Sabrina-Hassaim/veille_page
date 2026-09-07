# Contexte - Newsletter Analytics Engineering

Cette newsletter mensuelle est destinée à nos clients pour leur présenter les dernières avancées et bonnes pratiques en Analytics Engineering.

Le contenu est généré par Gemini (recherche Google), validé par `sync.py`, puis affiché par `index.html`.

## Schéma des Données

Chaque article doit posséder les clés obligatoires suivantes. Elles sont utilisées par le script de synchronisation `sync.py` pour valider les données extraites de `test veille.txt` avant de mettre à jour le fichier `data.json`.

### Clés Obligatoires
- `titre_en` : Le titre de l'article dans sa version originale en anglais.
- `titre_fr` : La traduction technique et professionnelle du titre en français.
- `source` : Le média, blog technique ou newsletter d'origine de l'article.
- `resume_fr` : Un résumé clair et accessible pour nos clients rédigé en français (exactement 2 phrases).
- `resume_en` : La traduction fidèle du résumé en anglais.
- `lien` : L'adresse URL reconstruite et vérifiée pour lire l'article complet.
- `date` : La date de publication de la veille au format strict JJ/MM/AAAA.
- `impact_fr` : L'impact opérationnel direct en français pour un Analytics Engineer (affiché en italique).
- `impact_en` : La traduction de l'impact technique en anglais.
- `categorie` : La catégorie de l'article (ex: DevOps, Gouvernance, BI, CI/CD, AI, Infrastructure, Best Practices).
- `stack` : L'écosystème technologique principal (ex: Google Cloud, Microsoft, AWS, Snowflake, Databricks, Multi-Stack).
- `score_fiabilite` : Une note entière de 1 à 5 mesurant la qualité technique et l'autorité de la source d'origine.
- `rationnel_source` : Une courte phrase en français expliquant le score de fiabilité attribué.

## Pipeline

1. `generate.py` charge `prompts/veille.md`, injecte la date du jour, appelle Gemini avec Google Search.
2. La PARTIE 1 (JSON avec `base_domaine` + `chemin_complet`) est écrite dans `test veille.txt`.
3. La PARTIE 2 (audit des sources) est écrite dans `rapport-veille.md`.
4. `sync.py` reconstruit les URLs (`https://` + domaine + chemin), ping HTTP, élimine les liens morts / hallucinations.
5. Si le schéma bilingue est valide, `data.json` est mis à jour. Sinon il n'est pas écrasé.
6. GitHub Actions commit `data.json` le 1er de chaque mois (ou via lancement manuel).

## Configuration

- Secret GitHub / variable locale : `GEMINI_API_KEY` (jamais commitée).
- Dépendance Python : voir `requirements.txt` (`google-genai`).
- `sync.py` n'a besoin d'aucune clé.
