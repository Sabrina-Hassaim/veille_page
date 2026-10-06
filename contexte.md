# Contexte - Newsletter Analytics Engineering

Cette newsletter mensuelle est destinée à nos clients pour leur présenter les dernières avancées et bonnes pratiques en Analytics Engineering.

## Schéma des Données

Chaque article doit posséder les clés obligatoires suivantes. Elles sont utilisées par `sync.py` pour valider les données de `veille.json` avant de mettre à jour `data.json`.

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

1. `generate.py` lit `prompts/veille.md`, appelle Gemini avec Google Search, et écrit `veille.json`.
2. `sync.py` reconstruit les URLs, vérifie qu'elles répondent, puis écrit `data.json` si le schéma est valide.
3. `index.html` affiche `data.json`.
4. GitHub Actions enchaîne ces étapes le 1er du mois, puis GitHub Pages publie `main`.

La clé `GEMINI_API_KEY` reste dans les secrets GitHub. Elle n'est pas dans le dépôt.