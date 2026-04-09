import re
import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import storage

load_dotenv()

API_KEY = os.getenv('TS_API_KEY')
SERVICE_ACCOUNT_KEY = os.getenv('GCP_SERVICE_ACCOUNT_KEY')
PROJECT_ID = os.getenv('GCP_PROJECT_ID')
BUCKET_NAME = os.getenv('GCP_BUCKET_NAME')

BASE_URL = 'https://api.scrapecreators.com/v1/truthsocial'
USERNAMES = ['realDonaldTrump', 'JDVance1']

def retrieve_topics_from_gcp(service_account_key=SERVICE_ACCOUNT_KEY,
                      project_id=PROJECT_ID, bucket_name=BUCKET_NAME):
    '''
    Grabs topics from bucket files
    '''
    credentials = service_account.Credentials.from_service_account_file(service_account_key)
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
            for kw in keywords:
                all_topics.append(kw.strip())
    return all_topics


def call_api_truth_social(topics, limit=100, api_key=API_KEY, base_url=BASE_URL):
    '''
    Calling API for truth social for all usernames retrieved
    '''
    responses = []
    for user in USERNAMES:
        url = f"{base_url}/user/posts"

        headers = {"x-api-key": api_key, "accept": "application/json"}

        params = {"handle": user, "limit": limit}

        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            for post in data['posts']:
                for topic in topics:
                    for word in topic.split():
                        post['content'] = re.sub(re.compile('<.*?>'), '', post['content'])
                        if word in post['content'].split():
                            posts = {}
                            posts['platform'] = 'Truth Social'
                            labels = ['created_at', 'content']
                            for label in labels:
                                item = post[label]
                                if label == 'created_at':
                                    label = 'date'
                                posts[label] = item
                            posts['topic'] =  topic
                            responses.append(posts)
        else:
            print(f"Error for '{topics} for user {user}'", response.status_code, response.text)
    return responses


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
    file_name= f"truth/truthsocial_{datetime.now().strftime('%Y-%m-%d_%H:%M:%S')}.json"
    file = bucket.blob(file_name)
    file.upload_from_string(json.dumps(data))
    return {"message": f"file {file_name} has been uploaded\
            to {bucket_name} successfully."}

def retrieve_from_gcp(service_account_key=SERVICE_ACCOUNT_KEY,
                      project_id=PROJECT_ID, bucket_name=BUCKET_NAME):
    '''
    grabs all truthsocial json files
    '''
    credentials = service_account.Credentials.from_service_account_file(
        service_account_key)
    client = storage.Client(project=project_id, credentials=credentials)
    bucket = client.bucket(bucket_name)
    files = []
    for blob in bucket.list_blobs():
        if blob.name.startswith('truthsocial/truthsocial'):
            file = bucket.blob(blob.name)
            files.append(json.loads(file.download_as_string()))
    return files

if __name__ == "__main__":
    TOPICS = retrieve_topics_from_gcp()
    DATA = call_api_truth_social(topics=TOPICS)
    store_data_in_gcs(DATA)
