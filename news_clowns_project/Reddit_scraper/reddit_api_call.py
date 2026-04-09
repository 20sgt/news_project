import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import storage

load_dotenv()

SERVICE_ACCOUNT_KEY = os.getenv('GCP_SERVICE_ACCOUNT_KEY')
PROJECT_ID = os.getenv('GCP_PROJECT_ID')
BUCKET_NAME = os.getenv('GCP_BUCKET_NAME')

CLIENT_ID = os.getenv('R_CLIENT_ID')
CLIENT_SECRET = os.getenv('R_CLIENT_SECRET')

USERNAME = os.getenv('R_USERNAME')
PASSWORD = os.getenv('R_PASSWORD')
USER_AGENT = os.getenv('R_USER_AGENT')

BASE_URL = 'https://oauth.reddit.com'
LIMIT = 20

def retrieve_topics_from_gcp(service_account_key=SERVICE_ACCOUNT_KEY,
                      project_id=PROJECT_ID, bucket_name=BUCKET_NAME):
    '''
    Grabs topics from latest bucket file
    '''
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key)
    client = storage.Client(project=project_id, credentials=credentials)
    bucket = client.bucket(bucket_name)
    files = []
    for blob in bucket.list_blobs():
        if blob.name.startswith('NewsData'):
            file = bucket.blob(blob.name)
            files.append(json.loads(file.download_as_string()))
            break

    all_topics = []
    for file in files:
        for item in file:
            keywords = item["Keywords"].strip("()").split(",")
            all_topics.append([kw.strip() for kw in keywords])
    return all_topics


def get_access_token(client_id, client_secret, user_agent):
    """Authenticate and return Reddit OAuth2 access token."""
    auth = requests.auth.HTTPBasicAuth(client_id, client_secret)
    data = {"grant_type": "client_credentials"}
    headers = {"User-Agent": user_agent}

    res = requests.post("https://www.reddit.com/api/v1/access_token",
                        auth=auth, data=data, headers=headers)
    res.raise_for_status()
    token = res.json()["access_token"]
    return token


def search_posts(token, keywords, limit=5):
    """Search posts by keyword."""
    query = " OR ".join([f'"{kw}"' for kw in keywords])
    headers = {"Authorization": f"bearer {token}", "User-Agent": USER_AGENT}
    params = {"q": query, "limit": limit, "sort": "relevance", "type": "link"}
    res = requests.get(f"{BASE_URL}/search", headers=headers, params=params)
    res.raise_for_status()
    posts = res.json().get("data", {}).get("children", [])
    return posts


def collect_reddit_data():
    """Collect Reddit data for all keywords."""
    token = get_access_token(CLIENT_ID, CLIENT_SECRET, USER_AGENT)
    all_data = []
    topics = retrieve_topics_from_gcp()
    for keywords in topics:
        print(f"\n Searching Reddit for: {keywords}")
        posts = search_posts(token, keywords, LIMIT)

        for post in posts:
            data = post['data']
            if data['selftext'] != '':
                post_info = {
                    'platform': 'Reddit',
                    'date': datetime.fromtimestamp(data['created_utc']).date().isoformat(),
                    'title': data['title'],
                    'comment': data['selftext'],
                    'topic': keywords,
                }
                all_data.append(post_info)
    return all_data


def store_data_in_gcs(data, service_account_key=SERVICE_ACCOUNT_KEY,
                      project_id=PROJECT_ID, bucket_name=BUCKET_NAME):
    '''
    Take the data and store into GCP
    '''
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key)
    client = storage.Client(project=project_id,
                            credentials=credentials)
    bucket = client.bucket(bucket_name)
    file_name= f"reddit/reddit_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.json"
    file = bucket.blob(file_name)
    file.upload_from_string(json.dumps(data))
    return {"message": f"file {file_name} has been uploaded\
            to {bucket_name} successfully."}

if __name__ == "__main__":
    data = collect_reddit_data()
    store_data_in_gcs(data)
