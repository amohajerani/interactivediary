'''
Users collection: 
- _id
- username
- email

s3:
    thegagali
        username1
            resume.csv
            ...

Files collection
- _id
- filepath
- username
- private


'''
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


def create_username(email):
    username = email.split("@")[0]
    username = ''.join(e for e in username if e.isalnum())
    num = 0
    while Users.find_one({'username': username}):
        username = username+str(num)
        num += 1
    return username


def get_username(email):
    user_obj = Users.find_one({'email': email})
    if not user_obj:
        username = create_username(email)
        Users.insert_one({'email': email, 'username': username})
    else:
        username = user_obj['username']
    return username


def insert_chat(username, txt, bot):
    Chats.insert_one(
        {'txt': txt, 'bot': bot, 'username': username, 'time': datetime.datetime.now(), 'date': datetime.date.today().strftime('%Y-%m-%d')})


def get_past_entry_dates(username):
    dates = Chats.distinct('date', {'username': username})
    dates.sort(reverse=True)
    return dates


def get_entries(date, username):
    res = list(Chats.find({'username': username, 'date': date}))
    sorted(res, key=lambda x: x['time'])
    return res
