import os
import json
import urllib.request
import requests
from datetime import datetime

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
INSTAGRAM_USERNAME = "hugodecrypte"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_PATH = os.path.join(BASE_DIR, "instagram_data.json")
IMAGES_DIR = os.path.join(BASE_DIR, "public", "images", "auto_posts")

os.makedirs(IMAGES_DIR, exist_ok=True)

MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def save_posts(posts):
    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(posts, f, ensure_ascii=False, indent=2)
    print(f"💾 Base mise à jour avec succès dans : {JSON_PATH}")

def download_image(url, filename):
    local_path = os.path.join(IMAGES_DIR, filename)
    relative_url = f"/images/auto_posts/{filename}"
    
    if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
        return relative_url
    
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as response, open(local_path, "wb") as out_file:
            out_file.write(response.read())
        return relative_url
    except Exception as e:
        print(f"⚠️ Erreur téléchargement {filename} : {e}")
        return None

def format_french_date_with_time(dt):
    return f"{dt.day} {MONTHS_FR[dt.month]} {dt.year} à {dt.strftime('%H:%M')}"

def main():
    print(f"🔄 Lancement de l'extraction API pour @{INSTAGRAM_USERNAME}...")

    apify_url = f"https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    payload = {
        "username": [INSTAGRAM_USERNAME],
        "resultsLimit": 150
    }

    try:
        response = requests.post(apify_url, json=payload, timeout=120)
        if response.status_code not in (200, 201):
            print(f"❌ Erreur API ({response.status_code})")
            return
        items = response.json()
    except Exception as e:
        print(f"❌ Erreur de connexion API : {e}")
        return

    new_entries = []
    seen_shortcodes = set()

    for item in items:
        type_str = str(item.get("type", "")).lower()
        product_type = str(item.get("productType", "")).lower()
        is_video = item.get("isVideo", False) or "video" in type_str or "reel" in product_type or item.get("videoUrl") is not None
        
        if is_video:
            continue

        shortcode = item.get("shortCode") or item.get("id")
        if not shortcode or shortcode in seen_shortcodes:
            continue
        
        seen_shortcodes.add(shortcode)
        post_id = f"post_api_{shortcode}"

        caption = item.get("caption", "")
        title = caption.split("\n")[0][:80] if caption else "Publication Instagram"
        
        # Récupération des statistiques d'engagement réelles
        likes_count = item.get("likesCount", 0) or 0
        comments_count = item.get("commentsCount", 0) or 0

        raw_timestamp = item.get("timestamp", "")
        if raw_timestamp:
            try:
                dt = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
                date_iso = dt.strftime("%Y-%m-%d")
                timestamp = dt.timestamp()
                date_fr = format_french_date_with_time(dt)
            except Exception:
                dt = datetime.now()
                date_iso = dt.strftime("%Y-%m-%d")
                timestamp = dt.timestamp()
                date_fr = format_french_date_with_time(dt)
        else:
            dt = datetime.now()
            date_iso = dt.strftime("%Y-%m-%d")
            timestamp = dt.timestamp()
            date_fr = format_french_date_with_time(dt)

        images_urls = []
        child_posts = item.get("childPosts", [])

        if child_posts:
            for idx, child in enumerate(child_posts):
                img_src = child.get("displayUrl") or child.get("imageUrl")
                if img_src:
                    fn = f"{shortcode}_{idx+1:02d}.jpg"
                    local_path = download_image(img_src, fn)
                    if local_path:
                        images_urls.append(local_path)
        else:
            img_src = item.get("displayUrl") or item.get("imageUrl")
            if img_src:
                fn = f"{shortcode}_01.jpg"
                local_path = download_image(img_src, fn)
                if local_path:
                    images_urls.append(local_path)

        if not images_urls:
            continue

        new_entries.append({
            "type": "instagram",
            "id": post_id,
            "shortcode": shortcode,
            "title": title,
            "fullCaption": caption,
            "imageUrl": images_urls[0],
            "image": images_urls[0],
            "cover": images_urls[0],
            "images": images_urls,
            "date": date_fr,
            "dateIso": date_iso,
            "timestamp": timestamp,
            "likesCount": likes_count,
            "commentsCount": comments_count
        })

    new_entries.sort(key=lambda p: float(p.get("timestamp", 0)), reverse=True)
    save_posts(new_entries)
    print(f"🎉 Extraction terminée ! {len(new_entries)} posts enregistrés avec leurs stats.")

if __name__ == "__main__":
    main()