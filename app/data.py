from flask import request, Flask
from threading import Thread
import openai
import orm
from dotenv import find_dotenv, load_dotenv
from os import environ as env

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
