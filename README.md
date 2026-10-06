# Veille Analytics Engineering

Newsletter mensuelle Converteo. La page lit `data/data.json` et l'affiche sur GitHub Pages.

https://sabrina-hassaim.github.io/veille_page/

## Flux

```text
prompts/veille.md
    → pipeline/generate.py (Gemini + Google Search) → data/veille.json
    → pipeline/sync.py (liens vérifiés) → data/data.json
    → index.html
```

`data/veille.json` est un fichier de travail. Il n'est pas versionné. `data/data.json` et `data/rapport-veille.md` le sont.

Les commandes se lancent depuis la racine du dépôt.

## Lancement

Automatique le 1er du mois à 06:00 UTC, via `.github/workflows/monthly-sync.yml`.

Manuel : Actions → Monthly Newsletter Sync → Run workflow → branche `main`.

Secret requis : `GEMINI_API_KEY`.

## Dossiers

| Dossier | Rôle |
|---|---|
| `assets/` | Logo et médias |
| `data/` | Articles publiés et audit des sources |
| `prompts/` | Prompt Gemini et clés obligatoires |
| `pipeline/` | `generate.py` et `sync.py` |
| `index.html` | Page, à la racine pour GitHub Pages |
