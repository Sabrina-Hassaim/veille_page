# Contexte - Newsletter Analytics Engineering

Cette newsletter mensuelle est destinée à nos clients pour leur présenter les dernières avancées et bonnes pratiques en Analytics Engineering.

## Schéma des Données

Chaque article doit posséder les clés obligatoires suivantes. Elles sont utilisées par le script de synchronisation `sync.py` pour valider les données extraites du Google Doc avant de mettre à jour le fichier `data.json`.

### Clés Obligatoires
- `titre` : Le titre principal de l'article en gras.
- `source` : Le média ou blog d'origine de l'article.
- `resume` : Un résumé clair et accessible pour nos clients.
- `lien` : L'adresse URL pour lire l'article complet.
- `date` : La date de publication de la veille.
- `impact` : L'impact concret sur l'équipe technique ou métier (affiché en italique).
- `categorie` : La catégorie de l'article (ex: Gouvernance, Architecture, Infrastructure, Business Intelligence, Outils).

## Fonctionnement du Workflow de Synchronisation

Le script `sync.py` permet d'automatiser la mise à jour des articles :
1. Recherche du dernier Google Doc contenant "test veille" dans le titre.
2. Téléchargement du contenu sous format texte brut.
3. Extraction du tableau JSON délimité par `[` et `]`.
4. Validation par rapport aux clés obligatoires listées ci-dessus.
5. Sauvegarde dans le fichier `data.json` si les données sont valides.

### Configuration Google API
Pour exécuter le script, placez votre fichier `credentials.json` (téléchargé depuis la console Google Cloud avec l'API Google Drive activée) à la racine de ce dossier. Au premier lancement, une fenêtre s'ouvrira pour vous authentifier et créer le fichier `token.json` requis pour les lancements futurs en tâche de fond.