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
    authorize_url="https://auth.thegagali.com",
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
    if not session.get('user'):
        return render_template('landing.html')
    dates = orm.get_past_entry_dates(
        username=orm.get_username(session['user']['userinfo']['email']))
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
# @require_auth
def chat():
    return render_template('chat.html')


@app.route('/get_response', methods=['POST'])
def get_response():

    username = orm.get_username(session['user']['userinfo']['email'])
    input_text = request.form['input_text']

    thread_input_txt = Thread(target=orm.insert_chat, args=(
        username, input_text, False))
    thread_input_txt.start()
    res = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a therapist."},
            {"role": "user", "content": input_text}],
        max_tokens=20,
        temperature=0,
    )

    thread_output_txt = Thread(target=orm.insert_chat, args=(
        username, res['choices'][0]['message']['content'], True))
    thread_output_txt.start()
    return res['choices'][0]['message']['content']


@ app.route("/past_entries/<date>")
@ require_auth
def past_entries(date):
    username = orm.get_username(session['user']['userinfo']['email'])
    entries = orm.get_entries(date, username)
    return render_template('journal-entry.html', entries=entries, date=date)


@app.route('/logo')
def get_log0():
    return send_file('./images/gagalilogo.jpg', mimetype='image/jpg')


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 8000), debug=True)
