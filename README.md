# Veille Analytics Engineering

Newsletter mensuelle Converteo. La page lit `data.json` et l'affiche sur GitHub Pages.

https://sabrina-hassaim.github.io/veille_page/

## Flux

```text
prompts/veille.md
    → generate.py (Gemini + Google Search) → veille.json
    → sync.py (liens vérifiés) → data.json
    → index.html
```

`veille.json` est un fichier de travail. Il n'est pas versionné. `data.json` et `rapport-veille.md` le sont.

## Lancement

Automatique le 1er du mois à 06:00 UTC, via `.github/workflows/monthly-sync.yml`.

Manuel : Actions → Monthly Newsletter Sync → Run workflow → branche `main`.

Secret requis : `GEMINI_API_KEY`.

## Fichiers utiles

| Fichier | Rôle |
|---|---|
| `prompts/veille.md` | Prompt de recherche et de rédaction |
| `generate.py` | Appel Gemini |
| `sync.py` | Validation des URLs et du schéma |
| `data.json` | Articles publiés |
| `rapport-veille.md` | Sources sans article ce mois-là |
| `contexte.md` | Clés obligatoires lues par `sync.py` |
| `index.html` | Page |
