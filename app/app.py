"""
Python Flask WebApp Auth0 integration example
"""

from os import environ as env
from urllib.parse import quote_plus, urlencode
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, request, Response, url_for, send_file
import orm
import openai
import data
from threading import Thread
import json
import time
import sys

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = Flask(__name__)
app.secret_key = env.get("APP_SECRET_KEY")
openai.api_key = env.get("OPENAI_KEY")

oauth = OAuth(app)

oauth.register(
    "auth0",
    client_id=env.get("AUTH0_CLIENT_ID"),
    client_secret=env.get("AUTH0_CLIENT_SECRET"),
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f'https://{env.get("AUTH0_DOMAIN")}/.well-known/openid-configuration',
)


def require_auth(func):
    def wrapper(*args, **kwargs):
        if session.get('user'):
            return func(*args, **kwargs)
        else:
            return redirect('/login')
    wrapper.__name__ = func.__name__
    return wrapper


@app.route("/")
def home():
    if not session.get('user', None):
        return render_template('landing.html')
    dates = orm.get_past_entry_dates(
        user_id=session['user']['user_id'])
    return render_template('home.html', dates=dates)


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
    session['user']['user_id'] = data.get_user_id(
        session['user']['userinfo']['sub'])
    return redirect("/")


@app.route("/login")
def login():
    redirect_uri = url_for("callback", _scheme='https', _external=True)
    return oauth.auth0.authorize_redirect(redirect_uri=redirect_uri)


@app.route("/logout")
@require_auth
def logout():
    session.clear()
    return redirect(
        "https://"
        + env.get("AUTH0_DOMAIN")
        + "/v2/logout?"
        + urlencode(
            {
                "returnTo": "https://www.thegagali.com",
                "client_id": env.get("AUTH0_CLIENT_ID"),
            },
            quote_via=quote_plus,
        )
    )


@app.route("/chat")
# @require_auth
def chat():
    return render_template('chat.html')


@app.route('/get_response', methods=['POST'])
@require_auth
def get_response():
    # get the payload
    start = time.time()
    req_data = request.get_json()
    user_text = req_data['msg']
    chat_history = req_data['history']
    print('step 1: ', time.time()-start, file=sys.stderr)

    # store the user input to db
    thread_input_txt = Thread(target=orm.insert_chat, args=(
        session['user']['user_id'], user_text, 'user'))
    thread_input_txt.start()
    print('step 2: ', time.time()-start, file=sys.stderr)
    # get response from the bot
    messages = [{'role': 'system',
                 "content": "You help me write a better diary journal by providing brief and thoughtful prompts. Be brief"}]
    messages.extend(chat_history)
    messages.append({'role': 'user', 'content': user_text})
    print('step 3: ', time.time()-start, file=sys.stderr)
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=200,
        temperature=0,
    )
    print('step 4: ', time.time()-start, file=sys.stderr)

    # store the bot's response to the db
    thread_output_txt = Thread(target=orm.insert_chat, args=(
        session['user']['user_id'], res['choices'][0]['message']['content'], 'bot'))
    thread_output_txt.start()
    print('step 5: ', time.time()-start, file=sys.stderr)
    return res['choices'][0]['message']['content']


@ app.route("/past_entries/<date>")
@ require_auth
def past_entries(date):
    entries = orm.get_entries(date, session['user']['user_id'])
    return render_template('journal-entry.html', entries=entries, date=date)


@app.route('/logo')
def get_log0():
    return send_file('./images/gagalilogo.jpg', mimetype='image/jpg')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 8000), debug=True)
