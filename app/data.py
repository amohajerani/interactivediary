from flask import request, Flask
from threading import Thread
import openai
import orm
from dotenv import find_dotenv, load_dotenv
from os import environ as env
from bson.objectid import ObjectId
import datetime

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)


def init_app():
    app = Flask(__name__)
    app.secret_key = env.get("APP_SECRET_KEY")

    return app


openai.api_key = env.get("OPENAI_KEY")


def store_message(user_id, text, role):
    '''
    If the message is from the bot, just store it in mongo.
    If the message is from the user, first get teh summary. If the summary makes sense, add it to
    the object and then store it. 
    If a message does not have summary, it is because it is from bot
    If a message has an empty summary, it is because we should use the original text.
    '''
    obj = {'user_id': user_id, 'txt': text, 'role': role}
    if role == 'user' and len(text) > 150:
        start_sequence = " Summarize what I said:"
        prompt = text+start_sequence
        try:
            res = openai.Completion.create(
                model="text-curie-001",
                prompt=prompt,
                temperature=0.15,
                max_tokens=300,
                top_p=1,
                frequency_penalty=0,
                presence_penalty=0
            )
            summary = res['choices'][0]['text']
            if len(summary)/len(text) < 0.8:  # use the summary if it is sufficiently shorter
                obj.update({'summary': summary})
        except Exception as e:
            print(e)
            obj.update({'summary': ''})
    orm.insert_chat(obj)


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
        thread_input_txt = Thread(target=store_message, args=(
            user_id, user_text, 'user'))
        thread_input_txt.start()
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
    with open("current_time.txt", "w") as f:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        f.write(current_time)
