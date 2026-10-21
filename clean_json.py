import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "instagram_data.json")

months_fr = {
    "01": "janvier", "02": "février", "03": "mars", "04": "avril",
    "05": "mai", "06": "juin", "07": "juillet", "08": "août",
    "09": "septembre", "10": "octobre", "11": "novembre", "12": "décembre"
}

if os.path.exists(JSON_PATH):
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        posts = json.load(f)

    for p in posts:
        # Si c'est un post SodaFox, on extrait la vraie date depuis le chemin de l'image
        img_url = p.get("imageUrl", "")
        if "multi_creator" in img_url:
            match = re.search(r'/(\d{4}-\d{2}-\d{2})/', img_url)
            if match:
                date_iso = match.group(1) # ex: 2026-10-19
                parts = date_iso.split("-")
                day = str(int(parts[2]))
                month = months_fr.get(parts[1], "octobre")
                year = parts[0]
                
                p["dateIso"] = date_iso
                p["date"] = f"{day} {month} {year}"
                
                # Ajuster le timestamp en fonction de cette vraie date pour le tri
                from datetime import datetime
                dt = datetime.strptime(date_iso, "%Y-%m-%d")
                p["timestamp"] = dt.timestamp()

    # Tri global de toute la base
    posts.sort(key=lambda x: float(x.get("timestamp", 0)), reverse=True)

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    
    print("✅ Fichier JSON nettoyé et synchronisé avec les vraies dates des dossiers !")
else:
    print("❌ Fichier instagram_data.json introuvable.")