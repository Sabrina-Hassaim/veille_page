#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import sys

# Simulation de la sortie brute du workflow Workspace Studio
# Contient le JSON des articles d'actualité Analytics Engineering
# suivi d'une section "AUDIT DES SOURCES" comme spécifié.
MOCK_WORKSPACE_STUDIO_OUTPUT = """
Flux d'intégration Workspace Studio - Édition de Juin 2026
---------------------------------------------------------
Voici les articles de veille technique collectés pour nos clients.
Les données brutes ont été structurées ci-dessous sous forme de tableau JSON.

[
  {
    "titre": "L'essor des Data Contracts : Garants de la qualité des données en amont",
    "source": "Data Engineering Blog",
    "resume": "Les data contracts redéfinissent la relation entre producteurs et consommateurs de données en formalisant les schémas et SLA sous forme de code. Cet article détaille leur implémentation avec les outils modernes.",
    "lien": "https://example.com/data-contracts",
    "date": "12 Juin 2026",
    "impact": "Réduit les pannes de pipelines de 40% en forçant les équipes de développement à notifier les changements de schéma.",
    "categorie": "Gouvernance"
  },
  {
    "titre": "dbt Mesh : Organiser son projet d'Analytics Engineering à l'échelle",
    "source": "dbt Labs Developer Hub",
    "resume": "Découvrez comment l'architecture d'entreprise de dbt (dbt Mesh) permet de diviser un projet monolithique en sous-projets indépendants mais connectés grâce aux références cross-projets.",
    "lien": "https://www.youtube.com/",
    "date": "08 Juin 2026",
    "impact": "Permet aux grandes équipes de collaborer sur des modèles partagés sans goulot d'étranglement ni conflits de fusion.",
    "categorie": "Architecture"
  },
  {
    "titre": "Apache Iceberg vs Delta Lake : Le choix du format de table en 2026",
    "source": "Modern Data Stack Weekly",
    "resume": "Un comparatif technique approfondi entre les deux géants des formats de table ouverts. Nous analysons les performances, le support communautaire et l'intégration avec les moteurs de requêtes.",
    "lien": "https://example.com/iceberg-delta",
    "date": "01 Juin 2026",
    "impact": "Optimisation des coûts de stockage de 25% et requêtes de lecture 2x plus rapides sur les grands volumes.",
    "categorie": "Infrastructure"
  },
  {
    "titre": "Le Semantic Layer : Rapprocher la technique des besoins métiers",
    "source": "Analytics Frontiers",
    "resume": "Le couche sémantique s'impose comme le pont indispensable entre l'analytics engineering et les outils de BI, centralisant la logique de calcul des métriques au plus près de l'entrepôt.",
    "lien": "https://example.com/semantic-layer",
    "date": "28 Mai 2026",
    "impact": "Garantit une version unique de la vérité pour les indicateurs clés (KPIs), partagée entre dbt, Tableau et Excel.",
    "categorie": "Business Intelligence"
  }
]

=========================================================
AUDIT DES SOURCES :
- Data Engineering Blog : Statut 200 OK (temps de réponse 120ms)
- dbt Labs Developer Hub : Statut 200 OK (temps de réponse 95ms)
- Modern Data Stack Weekly : Statut 200 OK (temps de réponse 150ms)
- Analytics Frontiers : Statut 200 OK (temps de réponse 80ms)
Rapport de conformité des flux : 100% opérationnel.
Généré par le service de scraping Workspace Studio.
=========================================================
"""


def get_mandatory_keys():
    """
    Lit dynamiquement les clés obligatoires depuis 'contexte.md'.
    En cas de problème, utilise le schéma par défaut.
    """
    default_keys = ['titre', 'source', 'resume', 'lien', 'date', 'impact', 'categorie']
    contexte_path = 'contexte.md'

    if not os.path.exists(contexte_path):
        print(f"[!] Fichier '{contexte_path}' introuvable. Schéma par défaut appliqué.")
        return default_keys

    try:
        with open(contexte_path, 'r', encoding='utf-8') as f:
            content = f.read()

        keys = []
        lines = content.split('\n')
        for line in lines:
            # Recherche des listes Markdown (- `cle` ou - cle)
            match = re.search(r'^\s*[\-\*\+]\s+`?(\w+)`?', line)
            if match:
                key = match.group(1)
                if key not in keys:
                    keys.append(key)

        if keys:
            print(f"[DEBUG] Clés obligatoires lues depuis 'contexte.md' : {keys}")
            return keys
        else:
            print("[DEBUG] Aucune clé détectée dans 'contexte.md'. Clés par défaut appliquées.")
            return default_keys
    except Exception as e:
        print(f"[!] Erreur de lecture de 'contexte.md' ({e}). Utilisation du schéma par défaut.")
        return default_keys


def extract_json_array(raw_text):
    """
    Isole et extrait le tableau JSON délimité par le premier '[' et le dernier ']'.
    Nettoie également les guillemets intelligents.
    """
    first_bracket = raw_text.find('[')
    last_bracket = raw_text.rfind(']')

    if first_bracket == -1 or last_bracket == -1 or last_bracket < first_bracket:
        raise ValueError("Impossible de localiser le bloc JSON (délimité par '[' et ']') dans le document.")

    # Découpage du texte pour isoler le JSON
    json_str = raw_text[first_bracket:last_bracket + 1]

    # Remplacement des guillemets spéciaux pour la compatibilité JSON standard
    json_str = json_str.replace('“', '"').replace('”', '"')
    json_str = json_str.replace('‘', '"').replace('’', '"')

    # Nettoyage des caractères de contrôle invisibles indésirables
    json_str = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', json_str)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Fournit un aperçu de l'erreur pour aider au diagnostic
        start_err = max(0, e.pos - 30)
        end_err = min(len(json_str), e.pos + 30)
        snippet = json_str[start_err:end_err]
        raise ValueError(
            f"Structure JSON invalide : {e.msg} (position {e.pos}).\n"
            f"    Aperçu de la zone d'erreur : ... {repr(snippet)} ..."
        )


def validate_json_data(data, mandatory_keys):
    """
    Valide le format et s'assure de la présence et du contenu de chaque clé requise.
    """
    if not isinstance(data, list):
        raise ValueError("Le JSON extrait doit être sous forme de tableau (liste).")

    if not data:
        raise ValueError("Le tableau JSON extrait est vide.")

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"L'élément à l'index {idx} n'est pas un dictionnaire d'article valide.")

        title_preview = item.get('titre', f"Article #{idx + 1}")

        # Validation de chaque clé obligatoire
        for key in mandatory_keys:
            if key not in item:
                raise ValueError(
                    f"Clé requise manquante : '{key}' (dans l'article '{title_preview}' à l'index {idx})"
                )
            
            value = item[key]
            if value is None:
                raise ValueError(
                    f"La valeur pour la clé '{key}' ne peut pas être nulle (dans l'article '{title_preview}')"
                )
            if isinstance(value, str) and not value.strip():
                raise ValueError(
                    f"La valeur pour la clé '{key}' ne peut pas être vide (dans l'article '{title_preview}')"
                )

    return True


def save_data(data):
    """
    Sauvegarde le tableau d'articles propre dans data.json à la racine.
    """
    output_path = 'data.json'
    
    # Sauvegarde sécurisée
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print("=========================================================")
    print("  SIMULATION WORKFLOW WORKSPACE STUDIO (VEILLE TECH)  ")
    print("=========================================================\n")

    # 1. Chargement des clés obligatoires
    mandatory_keys = get_mandatory_keys()

    # 2. Simulation de la récupération brute de l'API
    print("[+] Simulation de la récupération du dernier document Workspace Studio...")
    raw_document = MOCK_WORKSPACE_STUDIO_OUTPUT

    # 3. Traitement, extraction et validation
    try:
        print("[+] Isolation et extraction du bloc JSON...")
        clean_json = extract_json_array(raw_document)

        print("[+] Validation du schéma des données...")
        validate_json_data(clean_json, mandatory_keys)

        # 4. Enregistrement local
        save_data(clean_json)
        
        # 5. Récapitulatif de réussite stylisé
        article_count = len(clean_json)
        print("\n" + "=" * 57)
        print(f"[SUCCESS] {article_count} articles importés dans data.json !")
        print("=" * 57 + "\n")

    except ValueError as val_err:
        print("\n" + "#" * 65)
        print(" [ERREUR] LA SIMULATION DE SYNCHRONISATION A ÉCHOUÉ (DONNÉES INVALIDES)")
        print("#" * 65)
        print(f"Détail technique : {val_err}")
        print("\n--> SÉCURITÉ : Le fichier 'data.json' actuel N'A PAS été écrasé.")
        print("#" * 65 + "\n")
        sys.exit(1)

    except Exception as e:
        print("\n" + "#" * 65)
        print(" [ERREUR] ERREUR TECHNIQUE INATTENDUE DURANT LA SIMULATION")
        print("#" * 65)
        print(f"Détail : {e}")
        print("\n--> SÉCURITÉ : Le fichier 'data.json' actuel N'A PAS été écrasé.")
        print("#" * 65 + "\n")
        sys.exit(1)


if __name__ == '__main__':
    main()
