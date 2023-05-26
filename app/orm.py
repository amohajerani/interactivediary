
from pymongo.mongo_client import MongoClient
from dotenv import find_dotenv, load_dotenv
from os import environ as env
import datetime
from bson.objectid import ObjectId
import boto3
import os
import pymongo
import time
from logger import logger
ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)
MONGO_URL = env.get("MONGO_URI")
client = MongoClient(MONGO_URL)
db = client.interactivechat
Users = db.users
Entries = db.entries


def create_entry(user_id):
    # assign a default title
    today_str = datetime.date.today().strftime('%Y-%m-%d')
    entry_id = Entries.insert_one(
        {'user_id': user_id, 'completed': False, 'title': '', 'last_update': int(time.time()), 'title':today_str, 'chats':[]})
    return str(entry_id.inserted_id)


def get_entries(user_id):
    '''
    Get user entries
    '''
    # from newest to oldest
    entries = Entries.find(
        {'user_id': user_id}, {'title': 1, 'completed': 1, 'last_update': 1}).sort(
            'last_update', pymongo.DESCENDING)
    in_progress_entries = []
    completed_entries = []
    for entry in entries:
        entry['_id'] = str(entry['_id'])
        if entry.get('completed'):
            completed_entries.append(entry)
        else:
            in_progress_entries.append(entry) 
    return in_progress_entries, completed_entries


def update_entry(entry_id, update_obj):
    update_obj.update({'last_update': int(time.time())})
    update_data = {'$set': update_obj}
    Entries.update_one({'_id': ObjectId(entry_id)}, update_data)

def get_entry(entry_id:str):
    entry = Entries.find_one({'_id':ObjectId(entry_id)})
    entry['_id']=str(entry['_id'])
    return entry

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
