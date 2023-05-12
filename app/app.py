"""
Python Flask WebApp Auth0 integration example
"""
from authlib.integrations.flask_client import OAuth

from os import environ as env
from urllib.parse import quote_plus, urlencode
from dotenv import find_dotenv, load_dotenv
from flask import redirect, render_template, session, request, Response, url_for, send_file
import orm
import data
import urllib.parse

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

app = data.init_app()

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
        session['user']['userinfo']['email'])

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


@app.route('/get_response_test', methods=['POST'])
def get_response_test():
    return data.get_response(request.json, 'blank', False)


@app.route('/get_response', methods=['POST'])
@require_auth
def get_response():
    return data.get_response(request.json, session['user']['user_id'])


@ app.route("/past_entries/<date>")
@ require_auth
def past_entries(date):
    entries = orm.get_entries(date, session['user']['user_id'])
    return render_template('journal-entry.html', entries=entries, date=date)


@app.route('/logo')
def get_log0():
    return send_file('./images/gagalilogo.jpg', mimetype='image/jpg')


@app.route('/subscriptions')
# @require_auth
def subscriptions():
    return render_template('subscriptions.html')


@app.route('/remove-subscriber', methods=['POST'])
@require_auth
def remove_subscriber():
    data.remove_subscriber(
        request.form, session['user']['user_id'], session['user']['userinfo']['email'])
    return render_template('subscriptions.html')


@app.route('/add-subscriber', methods=['POST'])
@require_auth
def add_subscriber():
    success = data.add_subscriber(
        request.form, session['user']['user_id'], session['user']['userinfo']['email'])

    if success:
        return request.form.get('email')
    return ''


@app.route('/get-subscribers')
@require_auth
def get_subscribers():
    return data.get_subscribers(session['user']['user_id'])


@app.route('/get-subscriptions')
@require_auth
def get_subscriptions():
    return data.get_subscriptions(session['user']['user_id'])


@app.route('/subscription/<encoded_email>')
@require_auth
def subscription_content(encoded_email):
    subscriber_email = session['user']['userinfo']['email']
    subscription_email = urllib.parse.unquote(encoded_email)
    subscription_user = orm.Users.find_one({'email': subscription_email})
    if not subscription_user or subscriber_email not in subscription_user['subscribers']:
        return 'you are not allowed'
    dates = orm.get_past_entry_dates(user_id=str(subscription_user['_id']))
    return render_template('home_subscription.html', dates=dates, email=subscription_email)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 8000), debug=True)
