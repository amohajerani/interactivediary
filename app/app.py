"""
Python Flask WebApp Auth0 integration example
"""

import json
from os import environ as env
from urllib.parse import quote_plus, urlencode
import os
from authlib.integrations.flask_client import OAuth
from dotenv import find_dotenv, load_dotenv
from flask import Flask, redirect, render_template, session, request, Response, url_for
from mongo import get_username, insert_chat, get_past_entry_dates, get_entries
import datetime
import openai
from threading import Thread

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
# Controllers API


@app.route("/")
def home():
    if not session.get('user'):
        return render_template('landing.html')
    dates = get_past_entry_dates(
        username=get_username(session['user']['userinfo']['email']))
    return render_template('home.html', dates=dates)


@app.route("/callback", methods=["GET", "POST"])
def callback():
    token = oauth.auth0.authorize_access_token()
    session["user"] = token
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
@require_auth
def chat():
    return render_template('chat.html')


@app.route('/get_response', methods=['POST'])
def get_response():

    username = get_username(session['user']['userinfo']['email']))
    input_text=request.form['input_text']

    thread_input_txt=Thread(target = insert_chat, args = (
        username, input_text, False))
    thread_input_txt.start()
    res=openai.Completion.create(
        model = "text-davinci-003",
        prompt = input_text,
        max_tokens = 50,
        temperature = 0,
    )

    thread_output_txt=Thread(target = insert_chat, args = (
        username, res.choices[0].text, True))
    thread_output_txt.start()
    return res.choices[0].text


@ app.route("/past_entries/<date>")
@ require_auth
def past_entries(date):
    username=get_username(session['user']['userinfo']['email'])
    entries=get_entries(date, username)
    return render_template('journal-entry.html', entries = entries)


if __name__ == "__main__":
    app.run(host = "0.0.0.0", port = env.get("PORT", 8000), debug = True)
