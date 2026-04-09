import pandas as pd
import json
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import os 
from datetime import datetime
from google.oauth2 import service_account
from google.cloud import storage
from dotenv import load_dotenv
import requests
from test import get_parser_files, sentiment_analysis
load_dotenv()
date = datetime.now().strftime("%Y-%m-%d")
def save_to_gcs(local_file, bucket_name, destination_blob_name):
    service_account_key = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    credentials = service_account.Credentials.from_service_account_file(service_account_key)
    client = storage.Client(project=os.getenv("PROJECT_ID"),
                            credentials=credentials)
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(local_file)
    

files = get_parser_files()
df = sentiment_analysis(files[0],files[1],files[2])
output_file = f"{date}_comments_with_sentiment.csv"
df.to_csv(output_file,index=False)
save_to_gcs(output_file,os.getenv("GCP_BUCKET_NAME"), f"log/{output_file}")
