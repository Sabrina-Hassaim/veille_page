# Contexte - Newsletter Analytics Engineering

Cette newsletter mensuelle est destinée à nos clients pour leur présenter les dernières avancées et bonnes pratiques en Analytics Engineering.

## Schéma des Données

Chaque article doit posséder les clés obligatoires suivantes. Elles sont utilisées par le script de synchronisation `sync.py` pour valider les données extraites du Google Doc avant de mettre à jour le fichier `data.json`.

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

## Fonctionnement du Workflow de Synchronisation

Le script `sync.py` permet d'automatiser la mise à jour des articles :
1. Recherche du dernier Google Doc contenant "test veille" dans le titre.
2. Téléchargement du contenu sous format texte brut.
3. Extraction du tableau JSON délimité par `[` et `]`.
4. Reconstruction des URLs réelles (fusion de base_domaine et chemin_complet) et validation par ping HTTP (HEAD) en temps réel pour éliminer automatiquement les liens morts et les hallucinations de l'IA.
5. Validation par rapport aux clés obligatoires bilingues et techniques listées ci-dessus, puis sauvegarde dans le fichier `data.json` si les données sont valides.

### Configuration Google API
### Pour exécuter le script, placez votre fichier `credentials.json` (téléchargé depuis la console Google Cloud avec l'API Google Drive activée) à la racine de ce dossier. Au premier lancement, une fenêtre s'ouvrira pour vous authentifier et créer le fichier `token.json` requis pour les lancements futurs en tâche de fond.