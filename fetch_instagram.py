import os
import json
import requests
from datetime import datetime

USERNAME = "hugodecrypte"
OUTPUT_FILE = "instagram_data.json"
APIFY_TOKEN = os.getenv("APIFY_TOKEN")
MAX_POSTS_TO_FETCH = 15

MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def format_insta_date(timestamp_val, iso_str=None):
    try:
        if timestamp_val and float(timestamp_val) > 0:
            ts = float(timestamp_val)
            if ts < 10000000000:
                ts = ts * 1000
            dt = datetime.fromtimestamp(ts / 1000.0)
        elif iso_str:
            dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        else:
            dt = datetime.now()
        
        day = dt.day
        month = MONTHS_FR[dt.month]
        year = dt.year
        hour = f"{dt.hour:02d}"
        minute = f"{dt.minute:02d}"
        
        return f"{day} {month} {year} à {hour}:{minute}", dt.strftime("%Y-%m-%d")
    except Exception:
        return "Récents", ""

def parse_any_timestamp(val):
    if not val:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        try:
            return float(val)
        except ValueError:
            pass
        try:
            dt = datetime.fromisoformat(val.replace("Z", "+00:00"))
            return dt.timestamp()
        except Exception:
            return 0.0
    return 0.0

def fetch_instagram_posts():
    if not APIFY_TOKEN:
        print("❌ Token APIFY manquant.")
        return []

    print(f"🔄 Extraction des posts images uniquement pour @{USERNAME}...")
    url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={APIFY_TOKEN}"
    
    payload = {
        "directUrls": [f"https://www.instagram.com/{USERNAME}/"],
        "resultsLimit": MAX_POSTS_TO_FETCH,
        "resultsType": "posts"
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
        if response.status_code not in [200, 201]:
            print(f"❌ Erreur API ({response.status_code})")
            return []

        data = response.json()
        new_posts = []

        for item in data:
            is_video = item.get("isVideo", False)
            product_type = str(item.get("productType", "")).lower()
            type_str = str(item.get("type", "")).lower()

            if is_video or product_type in ["clips", "reel"] or type_str in ["video"]:
                continue

            images = []
            if "childPosts" in item and isinstance(item["childPosts"], list):
                for child in item["childPosts"]:
                    if child.get("displayUrl"):
                        images.append(child.get("displayUrl"))
            
            if not images and item.get("displayUrl"):
                images.append(item.get("displayUrl"))

            caption = item.get("caption", "")
            timestamp = item.get("timestamp", 0)
            date_formatted, date_iso = format_insta_date(timestamp)

            title_summary = caption.split('\n')[0] if caption else "Publication Instagram"
            if len(title_summary) > 90:
                title_summary = title_summary[:87] + "..."

            new_posts.append({
                "type": "instagram",
                "id": str(item.get("id")),
                "title": title_summary,
                "caption": caption,
                "fullCaption": caption,
                "display_url": item.get("displayUrl", ""),
                "images": images,
                "url": item.get("url", ""),
                "date": date_formatted,
                "dateIso": date_iso,
                "timestamp": timestamp,
                "likesCount": item.get("likesCount", 0)
            })

        print(f"✅ {len(new_posts)} posts images récupérés.")
        return new_posts

    except Exception as e:
        print(f"❌ Erreur : {e}")
        return []

def merge_and_save_posts(new_posts):
    existing_posts = []
    if os.path.exists(OUTPUT_FILE):
        try:
            with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
                existing_posts = json.load(f)
        except Exception:
            existing_posts = []

    posts_dict = {}
    for post in existing_posts:
        if "id" in post and not post.get("isVideo", False):
            posts_dict[str(post["id"])] = post

    for post in new_posts:
        posts_dict[str(post["id"])] = post

    final_posts = list(posts_dict.values())
    final_posts.sort(key=lambda x: parse_any_timestamp(x.get("timestamp")), reverse=True)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final_posts, f, ensure_ascii=False, indent=2)

    print(f"💾 Fichier mis à jour sans doublon. Total posts : {len(final_posts)}")

if __name__ == "__main__":
    new_posts = fetch_instagram_posts()
    if new_posts:
        merge_and_save_posts(new_posts)