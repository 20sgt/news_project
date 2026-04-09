import os, re, json, asyncio, datetime
from google.cloud import storage
from dotenv import load_dotenv
import asyncpraw

load_dotenv()

# --- GCS setup ---
BUCKET = os.getenv("GCP_BUCKET_NAME")
INPUT_PREFIX = os.getenv("KEYWORD_JSON_PREFIX", "")   # can be empty = root
OUTPUT_PREFIX = os.getenv("RESULTS_PREFIX", "reddit/")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_REDDIT_DIR = os.path.join(SCRIPT_DIR, "reddit")
os.makedirs(LOCAL_REDDIT_DIR, exist_ok=True)

# --- GCS helpers ---
def gcs_client():
    cred_path = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    if cred_path and os.path.exists(cred_path):
        return storage.Client.from_service_account_json(cred_path)
    return storage.Client()

def list_json_blobs(bucket_name, prefix=""):
    client = gcs_client()
    return [b.name for b in client.list_blobs(bucket_name, prefix=prefix) if b.name.endswith(".json")]

def download_text(blob_name, bucket_name):
    client = gcs_client()
    blob = client.bucket(bucket_name).blob(blob_name)
    return blob.download_as_text()

def upload_file(local_path, bucket_name, dest_blob_name):
    client = gcs_client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(dest_blob_name)
    blob.upload_from_filename(local_path)
    print(f"  ⬆ Uploaded to gs://{bucket_name}/{dest_blob_name}")

def save_json(rows, path):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)
    print(f" Saved {len(rows)} posts to {path}")

# --- Normalizer ---
def _iso_from_epoch(sec):
    if sec is None:
        return None
    return datetime.datetime.utcfromtimestamp(float(sec)).replace(
        tzinfo=datetime.timezone.utc
    ).isoformat().replace("+00:00","Z")

def normalize_for_streamlit(rows):
    out = []
    for r in rows:
        rr = dict(r)
        rr["platform"] = rr.get("platform") or "Reddit"
        if not rr.get("keyword"):
            topics = rr.get("topics") or []
            rr["keyword"] = topics[0] if topics else None
        rr["topics"] = rr.get("topics") or ([rr["keyword"]] if rr.get("keyword") else [])
        rr["comment"] = rr.get("comment") or rr.get("title") or rr.get("text") or rr.get("body") or ""
        if rr.get("created_utc") is None and rr.get("created_at"):
            try:
                rr["created_utc"] = datetime.datetime.fromisoformat(
                    rr["created_at"].replace("Z", "+00:00")
                ).timestamp()
            except Exception:
                pass
        if rr.get("created_at") is None and rr.get("created_utc") is not None:
            rr["created_at"] = _iso_from_epoch(rr["created_utc"])
        out.append(rr)
    return out

# --- Reddit async fetchers ---
_SEMAPHORE = asyncio.Semaphore(6)

async def fetch_keyword(reddit, kw, *, subreddit="all", limit=10, sort="new", time_filter="week"):
    async with _SEMAPHORE:
        posts = []
        sub = await reddit.subreddit(subreddit)
        async for s in sub.search(kw, sort=sort, time_filter=time_filter, limit=limit):
            created_utc = getattr(s, "created_utc", None)
            posts.append({
                "platform": "Reddit",
                "subreddit": str(s.subreddit),
                "keyword": kw,
                "topics": [kw],
                "title": s.title,
                "comment": s.title,
                "url": s.url,
                "permalink": f"https://www.reddit.com{s.permalink}",
                "author": str(getattr(s.author, "name", "")) if s.author else None,
                "score": s.score,
                "num_comments": s.num_comments,
                "created_utc": created_utc,
                "created_at": _iso_from_epoch(created_utc)
            })
        return posts

async def fetch_all_keywords(keywords, *, subreddit="all", limit=10, sort="new", time_filter="week"):
    reddit = asyncpraw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent="reddit-scraper/0.1"
    )
    try:
        tasks = [fetch_keyword(reddit, kw, subreddit=subreddit, limit=limit, sort=sort, time_filter=time_filter)
                 for kw in keywords]
        results = await asyncio.gather(*tasks)
        rows = [p for batch in results for p in batch]
        return rows
    finally:
        await reddit.close()

# --- Main runner ---
def run_from_gcs(input_prefix, output_prefix, limit=10):
    blobs = list_json_blobs(BUCKET, prefix=input_prefix)
    if not blobs:
        print(f"⚠ No JSON found under gs://{BUCKET}/{input_prefix}")
        return

    existing = [f for f in os.listdir(LOCAL_REDDIT_DIR) if f.startswith("reddit_scrape_") and f.endswith(".json")]
    max_n = 0
    for name in existing:
        m = re.match(r"reddit_scrape_(\d+)\.json$", name)
        if m:
            max_n = max(max_n, int(m.group(1)))
    counter = max_n + 1

    for blob_name in blobs:
        print(f"▶ Processing {blob_name}")
        try:
            cfg = json.loads(download_text(blob_name, BUCKET))
        except Exception as e:
            print(f"  ✖ Failed to parse {blob_name}: {e}")
            continue

        if isinstance(cfg, dict):
            keywords = cfg.get("keywords") or []
            sr = str(cfg.get("subreddit", "all")).strip() or "all"
            per_kw_limit = int(cfg.get("limit_per_keyword", limit))
        elif isinstance(cfg, list):
            keywords = cfg
            sr = "all"
            per_kw_limit = limit
        else:
            print(f"  ⚠ Unsupported config format in {blob_name}")
            continue

        keywords = [str(k).strip() for k in keywords if str(k).strip()]
        if not keywords:
            print(f"  ⚠ No keywords in {blob_name}")
            continue

        try:
            rows = asyncio.run(fetch_all_keywords(keywords, subreddit=sr, limit=per_kw_limit))
        except Exception as e:
            print(f"  ✖ Fetch failed for {blob_name}: {e}")
            continue

        if not rows:
            print(f"  ⚠ No posts for {blob_name}")
            continue

        rows = normalize_for_streamlit(rows)
        print("  sample keys:", sorted(rows[0].keys()))

        filename = f"reddit_scrape_{counter}.json"
        local_json = os.path.join(LOCAL_REDDIT_DIR, filename)
        save_json(rows, local_json)

        # 🔹 Upload to GCS
        dest = f"{output_prefix.rstrip('/')}/{filename}"
        upload_file(local_json, BUCKET, dest)

        counter += 1

# --- Entry ---
if __name__ == "__main__":
    LIMIT = int(os.getenv("SEARCH_LIMIT", "20"))
    run_from_gcs(INPUT_PREFIX, OUTPUT_PREFIX, limit=LIMIT)
