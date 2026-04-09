import json
from datetime import date
from datetime import datetime
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from google.cloud import storage
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
#wanted to create something that would sift through key words/ test
#def duplication_check(file_path,text):


def parse_GCP_creation():
    #if not os.path.exists(file):
        #return "This file does not exist."
    #if os.path.getsize(file) == 0:
        #return "You cannot pass an empty file to GCP Bucket"
    df = merge_df("gemini_output.json","gemini_output.txt")
    today = date.today()
    timestamp = datetime.now()
    time = timestamp.time()
    json_str = df.to_json(orient = "records")
    service_account_key = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    credentials = service_account.Credentials.from_service_account_file(service_account_key)
    client = storage.Client(project=os.getenv("PROJECT_ID"),
                            credentials=credentials)
    bucket = client.bucket(os.getenv("GCP_BUCKET_NAME"))
    file = bucket.blob(f"NewsData{time}.json")
    file.upload_from_string(json_str, content_type="application/json")
        
def merge_df(json_path,txt_path):
    with open(txt_path,'r') as f:
        obj = f.read()
    
    entries = [entry.strip() for entry in obj.split("*") if entry.strip()]
    snippet = [entry[:entry.find('(')] for entry in entries]
    keys = [entry[entry.find('('):] for entry in entries]
    keys.pop(0)
    snippet.pop(0)
    df = pd.read_json(json_path, orient="records")
    df["Title"] = snippet
    df["Keywords"] = keys
    return df






