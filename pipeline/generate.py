#!/usr/bin/env python3
"""
Étape 2 — génération locale de la veille.

Lit prompts/veille.md, appelle Gemini avec Google Search,
écrit data/veille.json (JSON) et data/rapport-veille.md (audit).

La clé n'est lue que depuis la variable d'environnement GEMINI_API_KEY.
Elle n'est jamais écrite dans un fichier du dépôt.

Ensuite : python pipeline/sync.py  (reconstruction des URLs + ping HTTP).
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime

PROMPT_FILE = "prompts/veille.md"
OUTPUT_JSON = "data/veille.json"
OUTPUT_RAPPORT = "data/rapport-veille.md"
DEFAULT_MODEL = "gemini-3.8-flash"

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
    if not key or not key.strip():
        raise RuntimeError(
            "GEMINI_API_KEY est absente. "
            "En local : export GEMINI_API_KEY='…'  (ne pas la coller dans un fichier suivi par Git)."
        )
    return key.strip()


def load_prompt() -> str:
    if not os.path.exists(PROMPT_FILE):
        raise FileNotFoundError(f"Prompt introuvable : {PROMPT_FILE}")
    with open(PROMPT_FILE, encoding="utf-8") as handle:
        return handle.read()


def inject_runtime_context(prompt: str, now: datetime | None = None) -> str:
    """Ajoute la date du jour pour que Gemini calcule le mois civil précédent."""
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
    # exclude_domains n'est pas supporté par la clé Gemini Developer API.
    # L'exclusion de Converteo reste dans le prompt.
    config = types.GenerateContentConfig(
        tools=[types.Tool(google_search=types.GoogleSearch())],
        temperature=0.2,
    )
    response = client.models.generate_content(model=model, contents=prompt, config=config)

    text = getattr(response, "text", None)
    if not text:
        raise ValueError("Gemini n'a renvoyé aucun texte.")
    return text


def remove_trailing_commas(json_str: str) -> str:
    """Retire les virgules placées juste avant } ou ], hors des chaînes de caractères."""
    result = []
    in_string = False
    escaped = False
    pending_comma = None

    for char in json_str:
        if in_string:
            result.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if pending_comma is not None:
            if char.isspace():
                pending_comma.append(char)
                continue
            if char not in "}]":
                result.append(",")
            result.extend(pending_comma)
            pending_comma = None

        if char == ",":
            pending_comma = []
        else:
            result.append(char)
            if char == '"':
                in_string = True

    if pending_comma is not None:
        result.append(",")
        result.extend(pending_comma)
    return "".join(result)


def extract_json_part(raw: str) -> list:
    """Isole le tableau JSON de la PARTIE 1 (marqueurs, sinon premier [ … dernier ])."""
    marker_start = raw.find("---JSON-START---")
    marker_end = raw.find("---JSON-END---")
    if marker_start != -1 and marker_end > marker_start:
        raw = raw[marker_start + len("---JSON-START---"):marker_end]

    cleaned = re.sub(r"```json\s*", "", raw, flags=re.IGNORECASE)
    cleaned = re.sub(r"```\s*", "", cleaned)

    start = cleaned.find("[")
    end = cleaned.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("PARTIE 1 : aucun tableau JSON trouvé dans la réponse.")

    json_str = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", cleaned[start:end])
    json_str = remove_trailing_commas(json_str)
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError:
        # Gemini met parfois des guillemets typographiques comme délimiteurs JSON.
        # Les apostrophes ’ restent intactes : elles apparaissent dans le texte français.
        try:
            data = json.loads(json_str.replace("“", '"').replace("”", '"'))
        except json.JSONDecodeError as error:
            snippet = json_str[max(0, error.pos - 40): error.pos + 40]
            raise ValueError(
                f"JSON invalide : {error.msg} (position {error.pos}). Aperçu : {snippet!r}"
            ) from error

    if not isinstance(data, list):
        raise ValueError("La PARTIE 1 doit être un tableau d'articles.")
    return data


def extract_rapport_part(raw: str) -> str:
    match = re.search(r"(RAPPORT DE VEILLE.*)", raw, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return "Aucun rapport d'audit dans la réponse Gemini."


def validate_agent_output(articles: list) -> None:
    if not articles:
        raise ValueError("Gemini n'a produit aucun article.")

    for index, article in enumerate(articles):
        if not isinstance(article, dict):
            raise ValueError(f"L'élément {index} n'est pas un objet article.")
        title = article.get("titre_fr") or article.get("titre_en") or f"#{index + 1}"
        for key in AGENT_KEYS:
            value = article.get(key)
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Clé manquante ou vide '{key}' dans '{title}'.")
        try:
            score = int(article["score_fiabilite"])
        except (TypeError, ValueError) as error:
            raise ValueError(f"score_fiabilite invalide pour '{title}'.") from error
        if not 1 <= score <= 5:
            raise ValueError(f"score_fiabilite hors 1-5 pour '{title}'.")
        article["score_fiabilite"] = score

    count = len(articles)
    if count < 9 or count > 12:
        print(f"[!] {count} articles (objectif 9-12). Le fichier est quand même écrit ; sync.py filtrera les liens morts.")


def save_results(articles: list, rapport: str) -> None:
    with open(OUTPUT_JSON, "w", encoding="utf-8") as handle:
        json.dump(articles, handle, ensure_ascii=False, indent=2)
    with open(OUTPUT_RAPPORT, "w", encoding="utf-8") as handle:
        handle.write(f"# Rapport de veille — {datetime.now():%d/%m/%Y}\n\n")
        handle.write(rapport)
        handle.write("\n")
    print(f"[SUCCESS] {len(articles)} articles → {OUTPUT_JSON}")
    print(f"[SUCCESS] Audit → {OUTPUT_RAPPORT}")


def main() -> None:
    print("=" * 57)
    print("     GÉNÉRATION VEILLE (GEMINI, EN LOCAL)")
    print("=" * 57)
    try:
        prompt = inject_runtime_context(load_prompt())
        print("[+] Appel Gemini + Google Search...")
        raw = call_gemini(prompt)
        articles = extract_json_part(raw)
        rapport = extract_rapport_part(raw)
        validate_agent_output(articles)
        save_results(articles, rapport)
        print("[+] Ensuite : python pipeline/sync.py")
    except Exception as error:
        print("\n[ERREUR] Génération interrompue.")
        print(f"Détail : {error}")
        print("data/veille.json n'a pas été réécrit.")
        sys.exit(1)


if __name__ == "__main__":
    main()
