
from pymongo.mongo_client import MongoClient
from dotenv import find_dotenv, load_dotenv
from os import environ as env
import requests
import datetime
from bson.objectid import ObjectId
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
MONGO_URL = env.get("MONGO_URI")
client = MongoClient(MONGO_URL)
db = client.interactivechat
Users = db.users
Chats = db.chats
Summaries = db.summaries


def insert_chat(obj):
    obj.update({'time': datetime.datetime.now(),
               'date': datetime.date.today().strftime('%Y-%m-%d')})
    Chats.insert_one(obj)


def get_past_entry_dates(user_id):
    dates = Chats.distinct('date', {'user_id': user_id})
    dates.sort(reverse=True)
    return dates


def get_entries(date, user_id):
    res = list(Chats.find({'user_id': user_id, 'date': date}))
    sorted(res, key=lambda x: x['time'])
    return res


def insert_summary(user_id, date, summary):
    update = {"$set": {'user_id': user_id, 'date': date,
                       'summary': summary, 'time': datetime.datetime.now()}}
    Summaries.update_one(
        {'user_id': user_id, 'date': date}, update, upsert=True)


def update_user(user_id, new_data):
    Users.find_one({'_id': ObjectId(user_id)})
    update = {"$set": new_data}
    Users.update_one({'_id': ObjectId(user_id)}, update, upsert=True)
