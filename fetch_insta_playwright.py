import os
import json
import re
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
PUBLIC_DIR = os.path.join(BASE_DIR, 'public')
IMAGES_DIR = os.path.join(PUBLIC_DIR, 'images')
INSTA_PATH = os.path.join(BASE_DIR, 'instagram_data.json')

MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def clean_title_from_filename(prefix):
    """ Transformer le nom de fichier en un titre propre pour la carte """
    # Enlever 'hugodecrypte_' et remplacer les underscores par des espaces
    title = prefix.replace("hugodecrypte_", "").replace("_", " ").strip()
    # Mettre la première lettre en majuscule
    return title.capitalize() if title else "Actualité HugoDécrypte"

def parse_sodafox_folder():
    print("🚀 Analyse fine des carrousels multiples par journée...")
    
    # Recherche du dossier racine
    target_root = IMAGES_DIR
    if os.path.exists(IMAGES_DIR):
        for item in os.listdir(IMAGES_DIR):
            full_path = os.path.join(IMAGES_DIR, item)
            if os.path.isdir(full_path) and "multi_creator" in item:
                target_root = full_path
                break

    print(f"📂 Exploration de : {target_root}")
    posts_data = []

    if not os.path.exists(target_root):
        print(f"⚠️ Le dossier {target_root} n'existe pas.")
        return []

    # Parcourir chaque dossier de date (ex: 2026-10-19)
    for entry in sorted(os.listdir(target_root), reverse=True):
        folder_path = os.path.join(target_root, entry)
        if not os.path.isdir(folder_path):
            continue

        try:
            dt = datetime.strptime(entry, "%Y-%m-%d")
        except ValueError:
            continue

        # Filtrer à partir du 1er octobre 2026
        OCTOBER_FIRST_2026 = datetime(2026, 10, 1)
        if dt < OCTOBER_FIRST_2026:
            continue

        day = dt.day
        month_name = MONTHS_FR[dt.month]
        year = dt.year
        date_formatted = f"{day} {month_name} {year}"
        date_iso = dt.strftime("%Y-%m-%d")

        hugodecrypte_sub = os.path.join(folder_path, "hugodecrypte")
        search_dir = hugodecrypte_sub if os.path.exists(hugodecrypte_sub) else folder_path

        # 🧠 REGROUPEMENT DES IMAGES PAR POST (selon le nom de fichier)
        # Ex: "hugodecrypte_La_surprise_01.jpg" -> préfixe: "hugodecrypte_La_surprise"
        post_groups = {}

        for file in sorted(os.listdir(search_dir)):
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                full_img_path = os.path.join(search_dir, file)
                rel_path = "/" + os.path.relpath(full_img_path, PUBLIC_DIR).replace("\\", "/")

                # Extraire la racine du nom en retirant le numéro final (ex: _01, _1, -1)
                prefix = re.sub(r'[-_]\d+\.(jpg|jpeg|png|webp)$', '', file, flags=re.IGNORECASE)
                
                if prefix not in post_groups:
                    post_groups[prefix] = []
                post_groups[prefix].append((file, rel_path))

        # Créer un post distinct pour chaque groupe d'images trouvé dans la journée
        for post_idx, (prefix, files_list) in enumerate(post_groups.items()):
            # Trier les images du carrousel dans l'ordre 01, 02, 03...
            files_list.sort(key=lambda x: x[0])
            sorted_images_paths = [img[1] for img in files_list]

            title = clean_title_from_filename(prefix)
            post_id = f"post_{date_iso}_{post_idx + 1}"

            # Décalage léger du timestamp pour préserver l'ordre d'affichage dans la même journée
            post_timestamp = dt.timestamp() + (100 - post_idx)

            posts_data.append({
                "type": "instagram",
                "id": post_id,
                "title": title,
                "fullCaption": f"{title} - {date_formatted}",
                "imageUrl": sorted_images_paths[0],  # Vignette (Image 01)
                "images": sorted_images_paths,       # Carrousel complet (01, 02, 03...)
                "date": date_formatted,              # Ex: "19 octobre 2026"
                "dateIso": date_iso,
                "timestamp": post_timestamp
            })

    # Trier toutes les publications du plus récent au plus ancien
    posts_data.sort(key=lambda x: x["timestamp"], reverse=True)

    with open(INSTA_PATH, 'w', encoding='utf-8') as f:
        json.dump(posts_data, f, ensure_ascii=False, indent=2)

    print(f"🎉 SUCCÈS : {len(posts_data)} publication(s) distincte(s) extraite(s) avec carrousels complets !")
    return posts_data

if __name__ == "__main__":
    parse_sodafox_folder()