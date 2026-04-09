import requests
import json
import pandas as pd
from google.cloud import storage
import os
from dotenv import load_dotenv
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
AUTHOR_FEED_BASE = "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed"


def fetch_feed(handle, limit=100, cursor=None):
    params = {"actor": handle, "limit": limit}
    if cursor:
        params["cursor"] = cursor
    r = requests.get(AUTHOR_FEED_BASE, params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def scrape_all_posts(handle, pause=1.0):
    """Scrape all posts for a given handle."""
    all_posts, cursor = [], None
    while True:
        data = fetch_feed(handle, limit=100, cursor=cursor)
        feed = data.get("feed", [])
        if not feed:
            break
        for p in feed:
            post = p.get("post", {})
            record = {
                "uri": post.get("uri"),
                "displayName": post.get("author", {}).get("displayName"),
                "text": post.get("record", {}).get("text"),
                "createdAt": post.get("record", {}).get("createdAt"),
            }
            all_posts.append(record)
        cursor = data.get("cursor")
        if not cursor:
            break
        time.sleep(pause)
    return all_posts


def filter_posts_by_keywords(posts, keywords):
    """Filter posts by keywords and assign topic."""
    filtered = []
    for post in posts:
        text = post.get("text", "")
        for kw in keywords:
            if kw.lower() in text.lower():
                filtered.append({
                    "platform": "BlueSky",
                    "date": datetime.utcnow().strftime("%Y-%m-%d"),
                    "comment": text,
                    "topic": kw
                })
                break  
    return filtered


def upload_to_gcs_json(bucket_name, data, destination_blob):
    """Upload JSON data to GCS."""
    temp_file = "/tmp/temp.json"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob)
    blob.upload_from_filename(temp_file)
    print(f"Uploaded {destination_blob} → gs://{bucket_name}/{destination_blob}")


if __name__ == "__main__":
    # Handles to scrape (author feeds)
    handles = ["cnn.com", "msnbc.com", "wsj.com"]  # add as needed

    # Topics/keywords
    keywords = ["Russia", "AI", "Democrats", "Republicans", "Donald Trump"]

    # Scrape all handles in parallel
    print("Scraping all handles in parallel...")
    all_posts = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(scrape_all_posts, handles))
    for posts in results:
        all_posts.extend(posts)

    # Filter posts by keywords
    filtered_posts = filter_posts_by_keywords(all_posts, keywords)
    print(f"Found {len(filtered_posts)} posts matching keywords.")

    # Create destination path
    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    gcs_path = f"Bluesky/{today_str}/bluesky_posts.json"

    # Upload JSON to GCS
    upload_to_gcs_json(GCS_BUCKET_NAME, filtered_posts, gcs_path)

