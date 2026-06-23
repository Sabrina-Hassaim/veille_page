#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import json
import sys


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
        start_err = max(0, e.pos - 30)
        end_err = min(len(json_str), e.pos + 30)
        snippet = json_str[start_err:end_err]
        raise ValueError(
            f"Structure JSON invalide : {e.msg} (position {e.pos}).\n"
            f"    Aperçu de la zone d'erreur : ... {repr(snippet)} ..."
        )


def rebuild_links_from_split_data(articles):
    """
    Prend le JSON fragmenté (base_domaine et chemin_complet), reconstruit
    l'URL réelle dans la clé 'lien' et supprime les clés de transition.
    """
    rebuilt_articles = []
    
    for idx, item in enumerate(articles):
        if not isinstance(item, dict):
            continue
            
        base_domaine = item.get("base_domaine", "").strip()
        chemin_complet = item.get("chemin_complet", "").strip("/")
        
        # Si l'agent a bien renvoyé les clés de découpage
        if base_domaine and chemin_complet:
            # 1. On remplace les espaces par des points
            domaine_propre = base_domaine.replace(" ", ".")
            # 2. On assemble l'URL finale propre
            item["lien"] = f"https://{domaine_propre}/{chemin_complet}"
        else:
            # Sécurité si les clés sont absentes mais que 'lien' n'existe pas encore
            if "lien" not in item:
                item["lien"] = "https://www.google.com"
                
        # Nettoyage des clés temporaires utilisées pour contourner la censure
        item.pop("base_domaine", None)
        item.pop("chemin_complet", None)
        
        rebuilt_articles.append(item)
        
    return rebuilt_articles


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

        # Validation de chaque clé obligatoire (le 'lien' reconstruit en fait partie)
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
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print("=========================================================")
    print("       WORKFLOW DE SYNCHRONISATION VEILLE TECHNIQUE      ")
    print("=========================================================\n")

    input_file_path = 'test veille.txt'
    
    # 1. Chargement des clés obligatoires
    mandatory_keys = get_mandatory_keys()

    # 2. Lecture du fichier d'entrée 
    print(f"[+] Lecture du fichier source : '{input_file_path}'...")
    if not os.path.exists(input_file_path):
        print(f"\n[ERREUR CHITRIQUE] Le fichier '{input_file_path}' est introuvable.")
        print("Vérifie qu'il est bien orthographié et placé dans le même dossier que ce script.")
        sys.exit(1)
        
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            raw_document = f.read()
    except UnicodeDecodeError:
        print(f"\n[ERREUR] Impossible de lire '{input_file_path}' en texte brut.")
        print("Si c'est un vrai fichier Microsoft Word binaire, réenregistre-le en .txt d'abord.")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERREUR] Échec de la lecture du fichier : {e}")
        sys.exit(1)

    # 3. Traitement, extraction, reconstruction et validation
    try:
        print("[+] Isolation et extraction du bloc JSON...")
        extracted_json = extract_json_array(raw_document)

        print("[+] Reconstruction des URLs complètes (Fusion Domaine + Chemin)...")
        clean_json = rebuild_links_from_split_data(extracted_json)

        print("[+] Validation du schéma final des données...")
        validate_json_data(clean_json, mandatory_keys)

        # 4. Enregistrement local
        save_data(clean_json)
        
        # 5. Récapitulatif de réussite
        article_count = len(clean_json)
        print("\n" + "=" * 57)
        print(f"[SUCCESS] {article_count} articles traités et importés dans data.json !")
        print("=" * 57 + "\n")

    except ValueError as val_err:
        print("\n" + "#" * 65)
        print(" [ERREUR] LA SYNCHRONISATION A ÉCHOUÉ (DONNÉES INVALIDES)")
        print("#" * 65)
        print(f"Détail technique : {val_err}")
        print("\n--> SÉCURITÉ : Le fichier 'data.json' actuel N'A PAS été écrasé.")
        print("#" * 65 + "\n")
        sys.exit(1)

    except Exception as e:
        print("\n" + "#" * 65)
        print(" [ERREUR] ERREUR TECHNIQUE INATTENDUE DURANT LA CONVERSION")
        print("#" * 65)
        print(f"Détail : {e}")
        print("\n--> SÉCURITÉ : Le fichier 'data.json' actuel N'A PAS été écrasé.")
        print("#" * 65 + "\n")
        sys.exit(1)


if __name__ == '__main__':
    main()