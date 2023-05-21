
from pymongo.mongo_client import MongoClient
from dotenv import find_dotenv, load_dotenv
from os import environ as env
import requests
import datetime
from bson.objectid import ObjectId
import boto3
import os

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


def get_dates(user_id):
    dates = list(Chats.find(
        {'user_id': user_id}, {'date': 1}).distinct('date'))

    dates.sort()
    return dates


def get_entries(date, user_id):
    res = list(Chats.find({'user_id': user_id, 'date': date}))
    res = sorted(res, key=lambda x: x['time'])
    return res


def insert_summary(user_id, date, summary, insights):
    update = {"$set": {'user_id': user_id,
                       'date': date,
                       'summary': summary,
                       'insights': insights,
                       'time': datetime.datetime.now()}}
    Summaries.update_one(
        {'user_id': user_id, 'date': date}, update, upsert=True)


def update_user(user_id, new_data):
    Users.find_one({'_id': ObjectId(user_id)})
    update = {"$set": new_data}
    Users.update_one({'_id': ObjectId(user_id)}, update, upsert=True)


def upload_to_s3(file_location, user_id, date):
    s3_client = boto3.client('s3',
                             aws_access_key_id=os.environ.get('S3_KEY'),
                             aws_secret_access_key=os.environ.get('S3_SECRET'))
    s3_path = user_id+'/'+date+'.png'
    response = s3_client.upload_file(
        file_location,
        "diary-gagali",
        s3_path, ExtraArgs={'ContentType': '.png'})
    return response


def get_latest_wordcloud(user_id):
    s3_client = boto3.client('s3',
                             aws_access_key_id=os.environ.get('S3_KEY'),
                             aws_secret_access_key=os.environ.get('S3_SECRET'))

    files = []
    folder = user_id+'/'
    try:
        for item in s3_client.list_objects(Bucket='diary-gagali', Prefix=folder)['Contents']:
            filename = item['Key']
            files.append(filename)
    except Exception as e:
        print(e)
        pass
    files.sort(reverse=True)
    if files:
        return files[0]
    return None


def get_wordcloud_file(user_id):
    file_name = get_latest_wordcloud(user_id)
    s3_client = boto3.client('s3',
                             aws_access_key_id=os.environ.get('S3_KEY'),
                             aws_secret_access_key=os.environ.get('S3_SECRET'))
    if not file_name:
        file_name = 'not_enough_data.png'
    response = s3_client.get_object(Bucket='diary-gagali', Key=file_name)
    file_contents = response['Body'].read()
    return file_contents
