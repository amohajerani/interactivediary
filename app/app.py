"""
Python Flask WebApp Auth0 integration example
"""
from authlib.integrations.flask_client import OAuth

from os import environ as env
from urllib.parse import quote_plus, urlencode
from dotenv import find_dotenv, load_dotenv
from flask import redirect, render_template, session, request, Response, url_for, send_file, jsonify
import orm
import data
import urllib.parse
import base64

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


@app.template_filter('b64encode')
def b64encode_filter(s):
    return base64.b64encode(s).decode('utf-8')


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
    user_id = session['user']['user_id']
    dates = orm.get_dates(
        user_id=user_id)
    wordcloud = orm.get_wordcloud_file(user_id)
    return render_template('home.html', dates=dates, wordcloud=wordcloud)


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
@require_auth
def chat():
    chat_history = data.get_chat_history(session['user']['user_id'])
    return render_template('chat.html', chat_history=chat_history)


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
    return send_file('./static/gagalilogo.jpg', mimetype='image/jpg')


@app.route('/subscriptions')
@require_auth
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
    summaries = orm.get_summaries(user_id=str(subscription_user['_id']))
    wordcloud = orm.get_wordcloud_file(str(subscription_user['_id']))
    return render_template('home_subscription.html', summaries=summaries, wordcloud=wordcloud, email=subscription_email, encoded_email=urllib.parse.quote(subscription_email))


@app.route('/subscription/past_entry/<encoded_email>/<date>')
@require_auth
def subscription_entry(encoded_email, date):
    subscription_email = urllib.parse.unquote(encoded_email)
    subscriber_email = session['user']['userinfo']['email']
    subscription_user = orm.Users.find_one({'email': subscription_email})
    if not subscription_user or subscriber_email not in subscription_user['subscribers']:
        return 'you are not allowed'
    entries = orm.get_entries(date, str(subscription_user['_id']))
    return render_template('journal-entry-subscription.html', entries=entries, date=date, email=subscription_email)


@app.route('/analyze/<analysis_type>')
@require_auth
def analyze(analysis_type):
    """
    return a json like {'text':'......'}
    """
    return data.analyze(session['user']['user_id'], analysis_type)


@app.route('/email_content',  methods=['POST'])
@require_auth
def email_content():
    try:
        payload = request.get_json()
        date = payload.get('date')
        email = payload.get('email')
        user_id = session['user']['user_id']
        chats = data.get_chat_content(user_id, date)
        # Format chat content for email
        formatted_content = ''
        for chat in chats:
            role = chat.get('role')
            text = chat.get('content')
            formatted_content += f'{role}: {text}\n'

        # Call the send_email function from the email module
        data.send_email(date, email, formatted_content)

        return jsonify({'message': 'Email sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=env.get("PORT", 8000), debug=True)
