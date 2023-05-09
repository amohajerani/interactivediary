
from pymongo.mongo_client import MongoClient
from dotenv import find_dotenv, load_dotenv
from os import environ as env
import requests
import datetime

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
MONGO_URL = env.get("MONGO_URI")
client = MongoClient(MONGO_URL)
db = client.interactivechat
Users = db.users
Chats = db.chats


def insert_chat(user_id, txt, agent):
    Chats.insert_one(
        {'txt': txt, 'agent': agent, 'user_id': user_id, 'time': datetime.datetime.now(), 'date': datetime.date.today().strftime('%Y-%m-%d')})


def get_past_entry_dates(user_id):
    dates = Chats.distinct('date', {'user_id': user_id})
    dates.sort(reverse=True)
    return dates


def get_entries(date, user_id):
    res = list(Chats.find({'user_id': user_id, 'date': date}))
    sorted(res, key=lambda x: x['time'])
    return res
