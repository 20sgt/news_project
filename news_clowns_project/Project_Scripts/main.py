import json
from datetime import date
import datetime
import os
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from google.oauth2 import service_account
from google.cloud import storage
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import pandas as pd

from Search import *
from df_creation import *

GetSearch()
parse_GCP_creation()

