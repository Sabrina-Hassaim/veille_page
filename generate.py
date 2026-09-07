#!/usr/bin/env python3
"""
Génère test veille.txt via Gemini + Google Search.
La sortie est ensuite validée par sync.py (reconstruction d'URL + ping HTTP).
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

PROMPT_FILE = "prompts/veille.md"
OUTPUT_JSON = "test veille.txt"
OUTPUT_RAPPORT = "rapport-veille.md"
DEFAULT_MODEL = "gemini-2.5-flash"

AGENT_KEYS = [
    "titre_en",
    "titre_fr",
    "source",
    "resume_fr",
    "resume_en",
    "base_domaine",
    "chemin_complet",
    "date",
    "impact_fr",
    "impact_en",
    "categorie",
    "stack",
    "score_fiabilite",
    "rationnel_source",
]


def get_api_key() -> str:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError(
            "Variable d'environnement GEMINI_API_KEY manquante. "
            "Exporte-la en local ou ajoute-la comme secret GitHub Actions."
        )
    return key


def load_prompt() -> str:
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"Prompt introuvable : {PROMPT_FILE}")
    with open(PROMPT_FILE, encoding="utf-8") as handle:
        return handle.read()


def inject_runtime_context(prompt: str, now: datetime | None = None) -> str:
    today = now or datetime.now()
    months_fr = [
        "janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre",
    ]
    month_fr = months_fr[today.month - 1]
    return (
        f"Date d'exécution : {today.strftime('%d/%m/%Y')} "
        f"({month_fr} {today.year}).\n"
        "Utilise exclusivement cette date pour calculer le mois civil précédent.\n\n"
        + prompt
    )


def call_gemini(prompt: str) -> str:
    from google import genai
    from google.genai import types

    model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
    client = genai.Client(api_key=get_api_key())

    search_tool = types.Tool(
        google_search=types.GoogleSearch(exclude_domains=["converteo.com"])
    )
    config = types.GenerateContentConfig(
        tools=[search_tool],
        temperature=0.2,
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
    except Exception as first_error:
        print(f"[!] Appel avec exclude_domains en échec ({first_error}). Nouvel essai sans exclusion API.")
        config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())],
            temperature=0.2,
        )
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )

    text = getattr(response, "text", None)
    if not text:
        raise ValueError("Gemini n'a renvoyé aucun texte exploitable.")
    return text


def extract_json_part(raw: str) -> list:
    marker_start = raw.find("---JSON-START---")
    marker_end = raw.find("---JSON-END---")
    if marker_start != -1 and marker_end != -1 and marker_end > marker_start:
        raw = raw[marker_start + len("---JSON-START---"):marker_end]

    cleaned = re.sub(r"```json\s*", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)
    cleaned = cleaned.replace("“", '"').replace("”", '"')
    cleaned = cleaned.replace("‘", '"').replace("’", '"')

    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("PARTIE 1 : aucun tableau JSON trouvé dans la réponse Gemini.")

    json_str = cleaned[start:end]
    json_str = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", json_str)

    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as error:
        snippet = json_str[max(0, error.pos - 40): error.pos + 40]
        raise ValueError(
            f"JSON invalide dans la PARTIE 1 : {error.msg} (position {error.pos}). "
            f"Aperçu : {snippet!r}"
        ) from error

    if not isinstance(data, list):
        raise ValueError("La PARTIE 1 doit être un tableau JSON d'articles.")
    return data


def extract_rapport_part(raw: str) -> str:
    match = re.search(r"(RAPPORT DE VEILLE.*)", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Aucun rapport d'audit généré par Gemini."


def validate_agent_output(articles: list) -> None:
    if not articles:
        raise ValueError("Gemini n'a produit aucun article.")

    for index, article in enumerate(articles):
        if not isinstance(article, dict):
            raise ValueError(f"L'élément à l'index {index} n'est pas un objet article.")
        title = article.get("titre_fr") or article.get("titre_en") or f"#{index + 1}"
        for key in AGENT_KEYS:
            if key not in article or article[key] is None or (
                isinstance(article[key], str) and not str(article[key]).strip()
            ):
                raise ValueError(f"Clé manquante ou vide '{key}' dans l'article '{title}'.")
        try:
            score = int(article["score_fiabilite"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"score_fiabilite invalide pour '{title}'.") from error
        if not 1 <= score <= 5:
            raise ValueError(f"score_fiabilite hors plage 1-5 pour '{title}'.")
        article["score_fiabilite"] = score

    count = len(articles)
    if count < 9:
        print(f"[⚠️] Quota bas : {count} articles (objectif 9-12). sync.py filtrera ensuite les liens morts.")
    if count > 12:
        print(f"[⚠️] {count} articles produits (> 12). sync.py conservera ceux dont l'URL est valide.")


def save_results(articles: list, rapport: str) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(articles, handle, ensure_ascii=False, indent=2)

    with open(OUTPUT_RAPPORT, "w", encoding="utf-8") as handle:
        handle.write(f"# Rapport de veille — {datetime.now():%d/%m/%Y}\n\n")
        handle.write(rapport)
        handle.write("\n")

    print(f"[SUCCESS] {len(articles)} articles → {OUTPUT_JSON}")
    print(f"[SUCCESS] Rapport d'audit → {OUTPUT_RAPPORT}")


def main() -> None:
    print("=" * 57)
    print("     GÉNÉRATION VEILLE ANALYTICS ENGINEERING (GEMINI)")
    print("=" * 57)

    try:
        prompt = inject_runtime_context(load_prompt())
        print("[+] Appel Gemini + Google Search...")
        raw_response = call_gemini(prompt)
        articles = extract_json_part(raw_response)
        rapport = extract_rapport_part(raw_response)
        validate_agent_output(articles)
        save_results(articles, rapport)
        print("[+] Prochaine étape : python sync.py")
    except Exception as error:
        print("\n" + "#" * 65)
        print(" [ERREUR] LA GÉNÉRATION A ÉCHOUÉ")
        print("#" * 65)
        print(f"Détail : {error}")
        print("--> SÉCURITÉ : test veille.txt n'a pas été écrasé (sauf si l'écriture a déjà eu lieu).")
        print("#" * 65 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
