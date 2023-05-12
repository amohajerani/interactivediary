from flask import request, Flask
from threading import Thread
import openai
import orm
from dotenv import find_dotenv, load_dotenv
from os import environ as env
from bson.objectid import ObjectId

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


def init_app():
    app = Flask(__name__)
    app.secret_key = env.get("APP_SECRET_KEY")

    return app


openai.api_key = env.get("OPENAI_KEY")


def get_user_id(id):
    id = id.replace('auth0|', '')
    return id


def get_response(req_data, user_id, store=True):
    '''
    Send the user's input to GPT and return the response. 
    If store is set to True, store this exchange to the db.
    '''
    # get the payload
    user_text = req_data['msg']
    chat_history = req_data['history']

    # get response from the bot
    messages = [{'role': 'system',
                 "content": "You help me write a better diary journal by providing brief and thoughtful prompts. Be brief"}]
    messages.extend(chat_history)
    messages.append({'role': 'user', 'content': user_text})
    if store:
        thread_input_txt = Thread(target=orm.insert_chat, args=(
            user_id, user_text, 'user'))
        thread_input_txt.start()
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
        thread_output_txt = Thread(target=orm.insert_chat, args=(
            user_id, res['choices'][0]['message']['content'], 'bot'))
        thread_output_txt.start()
    return res['choices'][0]['message']['content']


def update_subscription(req_data, publisher_user_id):
    '''
    We have publisheres and subscribers. Publisher write a diary and subscribers read it
    For now only the publisher can take action. Maybe in future, I add subscribers too.
    '''
    subscriber_email = req_data['email']
    action = req_data['action']
    publisher_email = orm.Users.find_one(
        {'_id': ObjectId(publisher_user_id)})['email']

    # to remove a subscriber, so they cannot see your content
    if action == 'remove':
        orm.Users.update_one({"_id": ObjectId(publisher_user_id)}, {
                             "$pull": {"subscribers": subscriber_email}},
                             upsert=True)

        orm.Users.update_one({"email": subscriber_email}, {
                             "$pull": {"subscriptions": publisher_email}},
                             upsert=True)

    # to add a subscriber, so they see your content
    if action == 'add':
        orm.Users.update_one({"_id": ObjectId(publisher_user_id)}, {
                             "$push": {"subscribers": subscriber_email}},
                             upsert=True)

        orm.Users.update_one({"email": subscriber_email}, {
                             "$push": {"subscriptions": publisher_email}},
                             upsert=True)
