import json
import os
import urllib.request
import xml.etree.ElementTree as ET
import re
from datetime import datetime

BASE_DIR = os.path.dirname(__file__)
INSTA_PATH = os.path.join(BASE_DIR, 'instagram_data.json')
OUTPUT_PATH = os.path.join(BASE_DIR, 'all_media_data.json')

MONTHS_FR = {
    1: "janvier", 2: "février", 3: "mars", 4: "avril",
    5: "mai", 6: "juin", 7: "juillet", 8: "août",
    9: "septembre", 10: "octobre", 11: "novembre", 12: "décembre"
}

def format_date_french(dt):
    day = dt.day
    month_name = MONTHS_FR[dt.month]
    year = dt.year
    return f"{day} {month_name} {year}"

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

def parse_iso8601_duration_to_seconds(duration_str):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_str)
    if not match:
        return 0
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    return hours * 3600 + minutes * 60 + seconds

def classify_podcast_theme(title, description=""):
    title_raw = str(title).lower()
    desc_raw = str(description).lower()
    full_text = f"{title_raw} {desc_raw}".replace("hugodécrypte", "").replace("hugodecrypte", "")

    is_pop = "(pop)" in title_raw or " pop " in title_raw
    culture_strict_keywords = ['cinéma', 'film', 'série', 'musique', 'album', 'spectacle', 'festival', 'actrice', 'acteur', 'artiste', 'louvre', 'musée', 'cinéastes']
    
    if is_pop or any(kw in full_text for kw in culture_strict_keywords):
        return "Culture"

    media_strict_keywords = ['médias', 'media', 'télévision', 'journaliste', 'réseaux sociaux', 'tiktok', 'instagram', 'presse', 'interview plateau', 'chaîne tv', 'brut']
    
    if any(kw in full_text for kw in media_strict_keywords):
        return "Médias"

    return "Infos"

def clean_and_format_summary(text):
    if not text:
        return "Résumé non disponible."
    clean_text = re.sub(r'<br\s*/?>', '\n', text)
    clean_text = re.sub(r'<[^<]+?>', '', clean_text).strip()
    lines = [line.strip() for line in clean_text.split('\n') if line.strip()]
    
    main_summary = lines[0] if lines else "Résumé de l'épisode"
    topics = []
    
    for line in lines:
        if re.match(r'^(?:[0-9]{1,2}:[0-9]{2}|[•\-\*▪▶]|aussi|au sommaire|également|en bref|1\.|2\.|3\.)', line, re.IGNORECASE):
            clean_line = re.sub(r'^(?:[0-9]{1,2}:[0-9]{2}|[•\-\*▪▶]|1\.|2\.|3\.)\s*', '', line).strip()
            if len(clean_line) > 5 and not clean_line.startswith("http"):
                topics.append(clean_line)

    html = f"<div style='margin-bottom: 16px; color: #e2e8f0; font-size: 0.95rem; line-height: 1.6;'>{main_summary}</div>"
    if topics:
        html += "<div style='font-weight: 800; color: #1ed760; margin-bottom: 10px; font-size: 0.9rem;'>📌 AU SOMMAIRE DE CET ÉPISODE :</div>"
        html += "<ul style='list-style-type: none; padding-left: 0; display: flex; flex-direction: column; gap: 8px;'>"
        for topic in topics:
            html += f"<li style='background: #1e2430; padding: 8px 12px; border-radius: 8px; border-left: 3px solid #1ed760; color: #cbd5e1; font-size: 0.88rem;'>{topic}</li>"
        html += "</ul>"
    return html

def fetch_podcasts():
    print("🎙️ Extraction des podcasts en direct...")
    podcasts = []
    rss_url = "https://feeds.acast.com/public/shows/95497e34-ecc2-596a-b910-bb3342918621"
    
    try:
        req = urllib.request.Request(rss_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            xml_data = response.read()
            
        root = ET.fromstring(xml_data)
        channel = root.find('channel')
        
        for item in channel.findall('item'):
            title = item.find('title').text if item.find('title') is not None else "Podcast HugoDécrypte"
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
            desc_elem = item.find('description')
            raw_desc = desc_elem.text if desc_elem is not None else ""
            formatted_summary = clean_and_format_summary(raw_desc)
            
            enclosure = item.find('enclosure')
            audio_url = enclosure.get('url') if enclosure is not None else None
            
            if audio_url:
                try:
                    dt = datetime.strptime(pub_date[:25], "%a, %d %b %Y %H:%M:%S")
                    date_str = format_date_french(dt)
                    date_iso = dt.strftime("%Y-%m-%d")
                    timestamp = dt.timestamp()
                except Exception:
                    dt = datetime.now()
                    date_str = format_date_french(dt)
                    date_iso = dt.strftime("%Y-%m-%d")
                    timestamp = dt.timestamp()
                
                podcasts.append({
                    "type": "podcast",
                    "id": f"pod-{len(podcasts)}",
                    "title": title,
                    "descriptionHtml": formatted_summary,
                    "fullCaption": raw_desc,
                    "audioUrl": audio_url,
                    "date": date_str,
                    "dateIso": date_iso,
                    "timestamp": timestamp,
                    "theme": classify_podcast_theme(title, raw_desc)
                })

        print(f"✅ {len(podcasts)} podcasts synchronisés !")
    except Exception as e:
        print(f"❌ Erreur podcasts : {e}")
        
    return podcasts

def fetch_youtube_channel(channel_key, channel_id, api_key):
    print(f"▶️ Récupération des vidéos pour la chaîne YouTube [{channel_key}]...")
    videos = []
    try:
        channels_url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={api_key}"
        req = urllib.request.Request(channels_url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if not data.get('items'):
                print(f"⚠️ Chaîne YouTube introuvable pour l'ID {channel_id}")
                return []
            uploads_playlist_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
            
        next_page_token = ""
        raw_items = []
        video_ids = []

        while True:
            playlist_url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=50&key={api_key}"
            if next_page_token:
                playlist_url += f"&pageToken={next_page_token}"
                
            req_pl = urllib.request.Request(playlist_url)
            with urllib.request.urlopen(req_pl) as response_pl:
                pl_data = json.loads(response_pl.read().decode('utf-8'))
                
                for item in pl_data.get('items', []):
                    title = item['snippet']['title']
                    if title != "Private video" and title != "Deleted video":
                        raw_items.append(item)
                        video_ids.append(item['snippet']['resourceId']['videoId'])
                
                next_page_token = pl_data.get('nextPageToken')
                if not next_page_token:
                    break

        durations_map = {}
        for i in range(0, len(video_ids), 50):
            chunk_ids = ",".join(video_ids[i:i+50])
            details_url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={chunk_ids}&key={api_key}"
            req_det = urllib.request.Request(details_url)
            with urllib.request.urlopen(req_det) as resp_det:
                det_data = json.loads(resp_det.read().decode('utf-8'))
                for v_item in det_data.get('items', []):
                    duration_iso = v_item['contentDetails']['duration']
                    total_seconds = parse_iso8601_duration_to_seconds(duration_iso)
                    durations_map[v_item['id']] = "short" if total_seconds < 300 else "long"

        for item in raw_items:
            snippet = item['snippet']
            video_id = snippet['resourceId']['videoId']
            title = snippet['title']
            published_at = snippet['publishedAt']
            
            dt = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            date_str = format_date_french(dt)
            date_iso = dt.strftime("%Y-%m-%d")
            
            video_format = durations_map.get(video_id, "long")
            
            videos.append({
                "type": "youtube",
                "id": video_id,
                "title": title,
                "fullCaption": snippet.get('description', title),
                "embedUrl": f"https://www.youtube-nocookie.com/embed/{video_id}",
                "date": date_str,
                "dateIso": date_iso,
                "timestamp": dt.timestamp(),
                "format": video_format,
                "channel": channel_key
            })

        print(f"✅ [{channel_key}] {len(videos)} vidéos récupérées.")
    except Exception as e:
        print(f"❌ Erreur YouTube [{channel_key}] : {e}")
        
    return videos

def fetch_youtube():
    API_KEY = "AIzaSyA3VbH-aCZTQtsoErxhLrzwS-JdFGNxD6g"
    channels = {
        "actus": "UCAcAnMF0OrCtUep3Y4M-ZPw",
        "grands_formats": "UCUo1RqYV8tGjV38sQ8S5p9A"
    }
    all_videos = []
    for key, cid in channels.items():
        all_videos.extend(fetch_youtube_channel(key, cid, API_KEY))
    return all_videos

def fetch_instagram():
    print("📸 Chargement des posts Instagram...")
    insta_posts = []
    if os.path.exists(INSTA_PATH):
        try:
            with open(INSTA_PATH, 'r', encoding='utf-8') as f:
                raw_posts = json.load(f)
                
            for post in raw_posts:
                ts = post.get("timestamp", 0)
                if not ts or ts == 0 or ts == "0":
                    dt = datetime.now()
                    post["timestamp"] = dt.timestamp()
                else:
                    try:
                        num_ts = float(ts)
                        if num_ts < 10000000000:
                            num_ts = num_ts * 1000
                        dt = datetime.fromtimestamp(num_ts / 1000.0)
                    except Exception:
                        dt = datetime.now()
                        post["timestamp"] = dt.timestamp()
                
                post["date"] = format_date_french(dt)
                post["dateIso"] = dt.strftime("%Y-%m-%d")
                
            insta_posts = raw_posts
            print(f"✅ {len(insta_posts)} posts Instagram chargés !")
        except Exception as e:
            print(f"⚠️ Erreur lors de la lecture de instagram_data.json : {e}")
    return insta_posts

def main():
    insta_data = fetch_instagram()
    podcasts = fetch_podcasts()
    videos = fetch_youtube()

    all_media = insta_data + podcasts + videos
    
    # Tri corrigé en reverse=True pour afficher les plus récents en premier
    all_media.sort(key=lambda x: parse_any_timestamp(x.get('timestamp')), reverse=True)

    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(all_media, f, ensure_ascii=False, indent=2)

    public_output = os.path.join(BASE_DIR, 'public', 'all_media_data.json')
    if os.path.exists(os.path.join(BASE_DIR, 'public')):
        with open(public_output, 'w', encoding='utf-8') as f:
            json.dump(all_media, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Base globale synchronisée avec succès ({len(all_media)} médias au total) !")

if __name__ == "__main__":
    main()
