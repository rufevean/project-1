from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()


def get_connection():
    try:
        client = MongoClient(os.getenv("MONGO_URI"))
        if client is not None:
            print("Connected to the MongoDB database")
        else:
            print("Failed to connect to the MongoDB database")
        database = client.get_database("development")
        return database
    except Exception as e:
        raise Exception("Unable to find the document due to the following error: ", e)
