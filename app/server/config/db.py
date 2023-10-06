from pymongo import MongoClient
from pymongo.server_api import ServerApi
from urllib.parse import quote_plus, quote
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

mongodb_url = os.getenv("MONGODB_URL")


# Create a new client and connect to the server
conn = MongoClient(mongodb_url, server_api=ServerApi('1'))
db = conn["rojgar-db"]
# Send a ping to confirm a successful connection
try:
    conn.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)
