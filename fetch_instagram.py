import json
import os
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
OUTPUT_PATH = os.path.join(BASE_DIR, 'instagram_data.json')

MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def format_date_french(dt):
    return f"{dt.day} {MONTHS_FR[dt.month]} {dt.year}"

def fetch_instagram_data():
    print("📸 Récupération des posts Instagram via Apify...")
    token = os.environ.get("APIFY_TOKEN")
    if not token:
        print("❌ Token APIFY manquant.")
        return []

    try:
        from apify_client import ApifyClient
        client = ApifyClient(token)
        
        run_input = {
            "directUrls": ["https://www.instagram.com/hugodecrypte/"],
            "username": ["hugodecrypte"],
            "usernames": ["hugodecrypte"],
            "resultsLimit": 50,
        }
        
        # Lancement de l'acteur
        client.actor("apify/instagram-scraper").call(run_input=run_input)
        
        # Récupération directe des éléments depuis le dataset par défaut du dernier run de cet acteur
        actor_client = client.actor("apify/instagram-scraper")
        dataset_items = actor_client.last_run().dataset().list_items().items
        
        posts = []
        for item in dataset_items:
            raw_time = item.get("timestamp") or item.get("takenAt")
            dt = datetime.now()
            
            if raw_time:
                try:
                    if isinstance(raw_time, (int, float)):
                        if raw_time < 10000000000:
                            raw_time *= 1000
                        dt = datetime.fromtimestamp(raw_time / 1000.0)
                    elif isinstance(raw_time, str):
                        if raw_time.isdigit():
                            num = float(raw_time)
                            if num < 10000000000:
                                num *= 1000
                            dt = datetime.fromtimestamp(num / 1000.0)
                        else:
                            dt = datetime.fromisoformat(raw_time.replace("Z", "+00:00"))
                except Exception:
                    pass

            images = []
            if item.get("displayUrl"):
                images.append(item.get("displayUrl"))
            if item.get("images"):
                images.extend(item.get("images"))
            if item.get("childPosts"):
                for child in item.get("childPosts"):
                    if child.get("displayUrl"):
                        images.append(child.get("displayUrl"))
            
            if not images and item.get("imageUrl"):
                images = [item.get("imageUrl")]

            posts.append({
                "type": "instagram",
                "id": item.get("id") or item.get("shortCode"),
                "title": item.get("caption", "Post Instagram")[:80] + "...",
                "fullCaption": item.get("caption", ""),
                "imageUrl": images[0] if images else "",
                "images": images,
                "date": format_date_french(dt),
                "dateIso": dt.strftime("%Y-%m-%d"),
                "timestamp": dt.timestamp()
            })

        # Tri strict du plus récent au plus ancien
        posts.sort(key=lambda x: x.get('timestamp', 0), reverse=True)

        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(posts, f, ensure_ascii=False, indent=2)
            
        print(f"✅ {len(posts)} posts Instagram enregistrés avec succès.")
        return posts
    except Exception as e:
        print(f"❌ Erreur lors de l'appel Apify : {e}")
        return []

if __name__ == "__main__":
    fetch_instagram_data()