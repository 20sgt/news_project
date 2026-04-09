# analyze_comments.py
#import streamlit as st
import pandas as pd
import json
import pandas as pd
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import os 
from datetime import datetime,timezone,timedelta
from google.oauth2 import service_account
from google.cloud import storage
from dotenv import load_dotenv
import requests

load_dotenv()

def get_parser_files():
    now_utc = datetime.now(timezone.utc)
    now_pst = now_utc - timedelta(hours=8)  # Convert UTC to PST
    today = now_pst.strftime("%Y-%m-%d")
    service_account_key = os.getenv("GCP_SERVICE_ACCOUNT_KEY")
    credentials = service_account.Credentials.from_service_account_file(service_account_key)
    client = storage.Client(project=os.getenv("PROJECT_ID"),
                            credentials=credentials)
    bucket = client.bucket(os.getenv("GCP_BUCKET_NAME"))
    blobs = bucket.list_blobs(prefix=f'Bluesky/{today}/')
    files = [blob for blob in blobs]
    Bluesky_data = []
    for file in files:
        json_str = file.download_as_string() #this should only contain one file but just in case we parse
        json_str = json_str.decode("utf-8")
        Bluesky_data.extend(json.loads(json_str))
        #data = json.loads(json_str)
    Bluesky_df = pd.DataFrame(Bluesky_data)
    blobs = bucket.list_blobs(prefix='reddit/')
    files = [blob for blob in blobs if today in blob.name]
    Reddit_data = []
    for file in files:
        json_str = file.download_as_string() 
        json_str = json_str.decode("utf-8")
        Reddit_data.extend(json.loads(json_str))
        #data = json.loads(json_str)
    Reddit_df = pd.DataFrame(Reddit_data)
    print(Reddit_df.columns)
    Reddit_df = Reddit_df.drop(columns=['title'],errors='ignore')
    blobs = bucket.list_blobs(prefix='truth/')
    files = [blob for blob in blobs if today in blob.name]
    Truth_data = []
    for file in files:
        json_str = file.download_as_string() 
        json_str = json_str.decode("utf-8")
        Truth_data.extend(json.loads(json_str))
        #data = json.loads(json_str)
    Truth_df = pd.DataFrame(Truth_data)
    Truth_df['comment'] = Truth_df['content'] if 'content' in Truth_df.columns else pd.Series(dtype=str)

    #Truth_df['comment'] = Truth_df['content']
    Truth_df = Truth_df.drop(columns=['content'],errors='ignore')
    #flat_comments = []
    #for article in data:
        #title = article["Title"]
        #for comment in article["Comments"]:
            #flat_comments.append({
            #"Title": title,
            #"user_id": comment["user_id"],
            #"timestamp": comment["timestamp"],
            #"comment": comment["comment"],
            #"likes": comment["likes"],
            #"reposts": comment["reposts"]
            #})
    #X_df = pd.DataFrame(flat_comments)
    Bluesky_df = Bluesky_df.dropna(subset=['comment'])
    Reddit_df = Reddit_df.dropna(subset=['comment'])
    Truth_df = Truth_df.dropna(subset=['comment'])
    return Bluesky_df, Reddit_df, Truth_df
#Bluesky_df = get_parser_files()
#X_df = get_parser_files()[1]


def sentiment_analysis(Blue_df,Reddit_df,Truth_df):
    df = pd.concat([Blue_df, Reddit_df,Truth_df], ignore_index=True)
    nltk.download("vader_lexicon")
    sia = SentimentIntensityAnalyzer()


    def get_sentiment_scores(text):
        return sia.polarity_scores(text)
    sentiment_scores = df["comment"].apply(get_sentiment_scores)


    sentiment_df = pd.DataFrame(list(sentiment_scores))
    df = pd.concat([df, sentiment_df], axis=1)


    def sentiment_calc(compound):
        if compound >= 0.05:
            return "positive"
        elif compound <= -0.05:
            return "negative"
        else:
            return "neutral"
    df["sentiment"] = df["compound"].apply(sentiment_calc)
    df = df.drop(columns=["neg", "neu", "pos", "compound"])
    return df    

#print(Bluesky_df.head())
#print(datetime.now().strftime("%Y-%m-%d"))
bdf = get_parser_files()[0]
rdf = get_parser_files()[1]
tdf = get_parser_files()[2]
df = sentiment_analysis(bdf,rdf,tdf)
#print(rdf.columns)
#print(bdf.columns)
#print(tdf.columns)
#print(rdf.columns)
df.to_csv("shit.csv",index=False)

print(datetime.now().strftime("%Y-%m-%d"))
    