from flask import request, Flask
from threading import Thread
import openai
import orm
from dotenv import find_dotenv, load_dotenv
from os import environ as env
from bson.objectid import ObjectId
import datetime
import pymongo
import tiktoken
from wordcloud import WordCloud
import os

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


def init_app():
    app = Flask(__name__)
    app.secret_key = env.get("APP_SECRET_KEY")

    return app


openai.api_key = env.get("OPENAI_KEY")

summarize_prompt = '.\n Summarize what I said: '


def store_message(user_id, text, role):
    '''
    If the message is from the bot, just store it in mongo.
    If the message is from the user, first get teh summary. If the summary makes sense, add it to
    the object and then store it. 
    If a message does not have summary, it is because it is from bot
    If a message has an empty summary, it is because we should use the original text.
    '''
    obj = {'user_id': user_id, 'txt': text, 'role': role}
    if role == 'user':
        summary = summarize(text)
        obj.update({'summary': summary})
    orm.insert_chat(obj)
    orm.update_user(user_id, {'last_msg': datetime.datetime.now()})


def get_user_id(email):
    user = orm.Users.find_one({'email': email})
    if user:
        return str(user['_id'])
    user = orm.Users.insert_one(
        {'email': email, 'subscriptions': [], 'subscribers': []})
    return str(user.inserted_id)


def get_response(req_data, user_id, store=True):
    '''
    Send the user's input to GPT and return the response. 
    If store is set to True, store this exchange to the db.
    '''
    # get the payload
    user_text = req_data['msg']
    quiet_mode = req_data['quietMode']
    # store the input message immediately so it is retained.
    if store:
        thread_input_txt = Thread(target=store_message, args=(
            user_id, user_text, 'user'))
        thread_input_txt.start()
    # if it is quiet mode, you are done
    if quiet_mode:
        return {'success': True}
    chat_history = req_data['history']
    # let's just use the last response from bot as history
    if chat_history:
        chat_history = chat_history[-1:]
    # get response from the bot
    messages = [{'role': 'system',
                 "content": "You are a therapist. Be brief. Keep your response under 30 words"}]
    messages.extend(chat_history)
    messages.append({'role': 'user', 'content': user_text})
    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=200,
            temperature=0,
        )
    except Exception as e:
        print(e)
        return "Gagali is sorry. She cannot be reached now, you message is safe with her"

    # store the user input and bot's response to db
    if store:
        thread_output_txt = Thread(target=store_message, args=(
            user_id, res['choices'][0]['message']['content'], 'bot'))
        thread_output_txt.start()

    return res['choices'][0]['message']['content']


def remove_subscriber(req_data, publisher_user_id, publisher_email):
    subscriber_email = req_data['email']
    orm.Users.update_one({"_id": ObjectId(publisher_user_id)}, {
        "$pull": {"subscribers": subscriber_email}})

    orm.Users.update_one({"email": subscriber_email}, {
        "$pull": {"subscriptions": publisher_email}})


def add_subscriber(req_data, publisher_user_id, publisher_email):
    subscriber_email = req_data['email']
    subscriber_exists = orm.Users.find_one({'email': subscriber_email})
    if not subscriber_exists:
        return False

    orm.Users.update_one({"_id": ObjectId(publisher_user_id)}, {
        "$push": {"subscribers": subscriber_email}})

    orm.Users.update_one({"email": subscriber_email}, {
        "$push": {"subscriptions": publisher_email}})
    return True


def get_subscribers(user_id):
    user = orm.Users.find_one({'_id': ObjectId(user_id)})
    return user['subscribers']


def get_subscriptions(user_id):
    user = orm.Users.find_one({'_id': ObjectId(user_id)})
    return user['subscriptions']


def get_summary():
    # this assumes the job runs once an hour.
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    start_time = datetime.datetime.now()-datetime.timedelta(hours=1)
    # get users who had a new msg since the last function run.
    users = orm.Users.find({'last_msg': {'$gte': start_time}}, {'_id': 1})
    # for each user, concat all today's messages.
    for user in users:
        user_id = str(user['_id'])
        chats = orm.Chats.find({'user_id': user_id, 'date': today_str, 'role': 'user'}).sort(
            "time", pymongo.ASCENDING)
        # make a list of user texts
        diary = ''
        for chat in chats:
            diary = diary + ' ' + chat.get('summary')
        summary = summarize(diary)
        print('diary: ', diary)
        print('summary: ', summary)
        orm.insert_summary(user_id, today_str, summary)


def get_token_count(message, model="text-curie-001"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = encoding.encode(message+summarize_prompt)
    return num_tokens


def summarize(text):
    summary = text
    if len(text) < 150:
        return summary

    prompt = text+summarize_prompt
    try:
        res = openai.Completion.create(
            model="text-curie-001",
            prompt=prompt,
            temperature=0.15,
            max_tokens=500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        summary = res['choices'][0]['text']
        if len(summary)/len(text) > 0.9:  # use the summary if it is sufficiently shorter
            summary = text
    except Exception as e:
        print(e)
    return summary


def generate_wordcloud():
    # get all the messages from the past one week

    users = orm.Users.find({}, {'_id': 1})
    for user in users:
        today = datetime.date.today()
        today_str = today.strftime('%Y-%m-%d')
        user_id = str(user['_id'])
        date = today-datetime.timedelta(days=7)
        date_str = date.strftime('%Y-%m-%d')
        messages = orm.Chats.find(
            {'user_id': user_id, 'date': {'$gte': date_str}, 'role': 'user'}, {'txt': 1})
        # concat the texts
        txt = ''
        for message in messages:
            txt = txt + ' '+message['txt']
        # if there is not much text, let's make it a 2 week window
        if len(txt) < 400:
            date = today-datetime.timedelta(days=14)
            date_str = date.strftime('%Y-%m-%d')
            messages = orm.Chats.find(
                {'user_id': user_id, 'date': {'$gte': date_str}, 'role': 'user'}, {'txt': 1})
            # concat the texts
            txt = ''
            for message in messages:
                txt = txt + ' '+message['txt']
        if not txt:
            continue
        image = WordCloud(collocations=False,
                          background_color='white').generate(txt)
        file_path = f"./uploads/{user_id}_{today_str}.png"
        image.to_file(file_path)

        if os.path.exists(file_path):
            orm.upload_to_s3(file_path, user_id, today_str)
            os.remove(file_path)


def analyze(user_id):
    # get today's chat

    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    msgs = list(orm.Chats.find({'user_id': user_id, 'date': today_str, 'role': 'user'}).sort(
        "time", pymongo.ASCENDING))
    msgs = [msg['summary'] for msg in msgs]
    txt = ''

    for msg in msgs:
        txt = txt + '\n'+msg
    insight = get_insight(txt)
    # get insights from today's chat
    actions = get_actions(txt)
    # make wordcloud from today's chat
    image = WordCloud(collocations=False,
                      background_color='white').generate(txt)
    filename = f"{user_id}_{today_str}.png"
    image.to_file('./uploads/'+filename)
    return insight, actions, filename


def get_insight(txt):
    insight_prompt = "\n You are a therapist. Give a summary of insights from this text: "

    if len(txt) < 150:
        return "Not enough content to get insights from"

    prompt = txt+insight_prompt
    try:
        res = openai.Completion.create(
            model="text-curie-001",
            prompt=prompt,
            temperature=0.15,
            max_tokens=500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        insight = res['choices'][0]['text']
    except Exception as e:
        print(e)
    return insight


def get_actions(txt):
    action_prompt = "\n Summarize the action items from this text: "

    if len(txt) < 150:
        return "Not enough content to get action items from"

    prompt = txt+action_prompt
    try:
        res = openai.Completion.create(
            model="text-curie-001",
            prompt=prompt,
            temperature=0.15,
            max_tokens=500,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        actions = res['choices'][0]['text']
    except Exception as e:
        print(e)
    return actions
