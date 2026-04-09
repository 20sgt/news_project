from datetime import datetime, timedelta
from dateutil import parser
import json
import os

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from google.cloud import storage
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import pandas as pd
from google import genai



load_dotenv()

app = FastAPI()


class GoogleSearch(BaseModel):
    url: str
    search_engine_id: str 
    api_key: str
    no_days: str  
    q: str


@app.get("/search")
def call_google_search(search_param: GoogleSearch):
    params = {
        "q": search_param.q,
        "key": search_param.api_key,
        "cx": search_param.search_engine_id,
        "dateRestrict": f"d{search_param.no_days}"
    }
    print(params)
    results = []
    ind = 1
    while len(results) < 50:
        params["start"] = ind
        data = requests.get(search_param.url, params=params).json()
        items = data.get("items", [])
        if not items:
            break
        results += items
        ind += 10

    return {"results": results}


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_KEY = os.getenv("API_KEY")
CX = os.getenv("SEARCH_ENGINE_ID")

search = {"q": "Current News","key":API_KEY,
          "cx":CX, "dateRestrict":1}

#response = requests.get("http://127.0.0.1:8000/search",params = search)
#print(response.content)


#response = requests.get(url="https://www.googleapis.com/customsearch/v1",params = search)
#data = response.json()
#print(data['items'][0])
#df = pd.DataFrame(data['items'])

#df = df.drop(columns=["kind","pagemap",'htmlFormattedUrl','htmlTitle'])
#df = df[["title","link","snippet"]]
#print(df.head())

import feedparser

def GetSearch():
    rss_url = "https://news.google.com/rss"
    feed = feedparser.parse(rss_url)
    data =[]
    title=[]
    for entry in feed.entries[:20]:
        data.append({"Title": entry.title,"Link": entry.link,"Published": entry.published})
        title.append(entry.title)
    df = pd.DataFrame(data)
    df.to_json("gemini_output.json",orient="records")
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    #print(df.head())
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"Given the following list of titles: {title}, output the same list but with simplified summary entries, and key phrases in perenthesis."
    )
    with open("gemini_output.txt",'w') as f:
        f.write(response.text + "\n")



