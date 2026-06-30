
import os
import re
import json
import sys
import urllib.request
import urllib.error
import ssl

def get_mandatory_keys():
    """
    Lit dynamiquement les clés obligatoires depuis 'contexte.md'.
    En cas de problème, utilise le schéma bilingue par défaut.
    """
    default_keys = [
        'titre_en', 'titre_fr', 'source', 'resume_fr', 'resume_en', 
        'lien', 'date', 'impact_fr', 'impact_en', 'categorie', 'stack',
        'score_fiabilite', 'rationnel_source'
    ]
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
            f"     Aperçu de la zone d'erreur : ... {repr(snippet)} ..."
        )


def check_if_url_exists(url):
    """
    Fait une requête HTTP pour vérifier l'existence du lien réel.
    Gère les blocages TLS, les redirections, les certificats SSL non valides,
    et les codes HTTP comme 403/401/405/429 qui prouvent que le lien existe mais est protégé.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3'
    }
    
    # Ignorer les problèmes de certificats locaux SSL courants en Python
    try:
        context = ssl._create_unverified_context()
    except AttributeError:
        context = None

    # 1. Tentative rapide via requête HEAD
    try:
        req = urllib.request.Request(url, method='HEAD', headers=headers)
        with urllib.request.urlopen(req, timeout=5, context=context) as response:
            if response.status in [200, 301, 302, 307, 308]:
                return True
    except urllib.error.HTTPError as e:
        # Si le serveur renvoie un code de restriction d'accès (401, 403, 405, 429),
        # l'URL existe bel et bien sur la plateforme (ce n'est pas une hallucination 404).
        if e.code in [401, 403, 405, 429]:
            return True
        if e.code == 404:
            return False
    except Exception:
        pass
        
    # 2. Repli de sécurité via requête GET (lecture partielle)
    try:
        req_get = urllib.request.Request(url, method='GET', headers=headers)
        with urllib.request.urlopen(req_get, timeout=5, context=context) as response:
            if response.status in [200, 301, 302, 307, 308]:
                return True
    except urllib.error.HTTPError as e:
        if e.code in [401, 403, 405, 429]:
            return True
        if e.code == 404:
            return False
    except Exception:
        return False

    return False


def rebuild_links_from_split_data(articles):
    """
    Reconstruit l'URL à partir de base_domaine et chemin_complet,
    vérifie si elle est valide, injecte le lien propre et nettoie les résidus.
    """
    rebuilt_articles = []
    
    for item in articles:
        if not isinstance(item, dict):
            continue
            
        base_domaine = item.get("base_domaine", "").strip()
        chemin_complet = item.get("chemin_complet", "").strip("/")
        
        # FIX : Récupération bilingue du titre pour éviter "Article sans titre" dans les logs de la console
        title_preview = item.get('titre_fr', item.get('titre_en', 'Article sans titre'))
        
        if base_domaine and chemin_complet:
            domaine_propre = base_domaine.replace(" ", ".")
            url_reconstruite = f"https://{domaine_propre}/{chemin_complet}"
            
            print(f"[+] Analyse Web : Vérification de -> {url_reconstruite}")
            
            if check_if_url_exists(url_reconstruite):
                item["lien"] = url_reconstruite
                # Retrait des clés temporaires de contournement de censure
                item.pop("base_domaine", None)
                item.pop("chemin_complet", None)
                rebuilt_articles.append(item)
            else:
                print(f"[🚨 INTERCEPTION] Hallucination détectée ou lien mort (404). Article supprimé : '{title_preview}'")
        else:
            print(f"[⚠️ DONNÉE INCOMPLÈTE] Impossible de reconstituer le lien pour : '{title_preview}'")
                
    return rebuilt_articles


def validate_json_data(data, mandatory_keys):
    """
    Valide le schéma final des données par rapport aux exigences de contexte.md.
    """
    if not isinstance(data, list):
        raise ValueError("Le JSON extrait doit être sous forme de tableau (liste).")

    if not data:
        raise ValueError("Le tableau JSON extrait est vide après filtrage des liens morts.")

    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"L'élément à l'index {idx} n'est pas un dictionnaire d'article valide.")

        # FIX : Récupération bilingue du titre lors des messages d'erreur de validation
        title_preview = item.get('titre_fr', item.get('titre_en', f"Article #{idx + 1}"))

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
    Sauvegarde le tableau final d'articles dans data.json.
    """
    output_path = 'data.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def main():
    print("=========================================================")
    print("        WORKFLOW DE SYNCHRONISATION VEILLE TECHNIQUE      ")
    print("=========================================================\n")

    input_file_path = 'test veille.txt'
    mandatory_keys = get_mandatory_keys()

    print(f"[+] Lecture du fichier source brut : '{input_file_path}'...")
    if not os.path.exists(input_file_path):
        print(f"\n[❌ ERREUR CRITIQUE] Le fichier '{input_file_path}' est introuvable.")
        sys.exit(1)
        
    try:
        with open(input_file_path, 'r', encoding='utf-8') as f:
            raw_document = f.read()
    except Exception as e:
        print(f"\n[❌ ERREUR] Échec de la lecture du fichier : {e}")
        sys.exit(1)

    try:
        print("[+] Isolation et extraction du bloc JSON...")
        extracted_json = extract_json_array(raw_document)

        print("[+] Ingestion et validation HTTP (Anti-Hallucination)...")
        clean_json = rebuild_links_from_split_data(extracted_json)

        print("[+] Validation finale de l'intégrité du schéma...")
        validate_json_data(clean_json, mandatory_keys)

        save_data(clean_json)
        
        article_count = len(clean_json)
        print("\n" + "=" * 57)
        print(f"[SUCCESS] {article_count} articles certifiés et importés dans data.json !")
        print("=" * 57 + "\n")

    except ValueError as val_err:
        print("\n" + "#" * 65)
        print(" [ERREUR] LA SYNCHRONISATION A ÉCHOUÉ (DONNÉES BLOQUÉES)")
        print("#" * 65)
        print(f"Détail technique : {val_err}")
        print("\n--> SÉCURITÉ : Le fichier 'data.json' d'origine N'A PAS été écrasé.")
        print("#" * 65 + "\n")
        sys.exit(1)


if __name__ == '__main__':
    main()