from pymongo import MongoClient
from datetime import date
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
import boto3
from botocore.exceptions import ClientError

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

# Email configuration

SENDER_EMAIL = env.get("SMTP_USERNAME")
AWS_REGION = "us-east-1"
chat_system_message = "You are a therapist. Be brief. Keep your response under 30 words"


def init_app():
    app = Flask(__name__)
    app.secret_key = env.get("APP_SECRET_KEY")

    return app


openai.api_key = env.get("OPENAI_KEY")

summarize_prompt = """Your task is to generate a short summary of a diary entry based on principles of reflective listening. 
Offer validation for feelings expressed. Summarize the below diary delimited by triple backticks, in 3 sentences or less.
Diary: """
insight_prompt = """Provide the overall sentiment of the passage in one sentence.
Then, analyze the passage and describe the feelings, thoughts and facts, each as one bullet point.
Then, list the writer's beliefs that lead to those feelings and thoughts in three bullet points.
Finally, list action items that the writer could follow in at most four bullet points.
Passage: """


def store_message(user_id, content, role, date):
    orm.Entries.update_one({'user_id': user_id, 'date': date},
                           {"$push": {"chats": {'role': role, 'content': content}}},
                           upsert=True
                           )


def get_user_id(email):
    user = orm.Users.find_one({'email': email})
    if user:
        return str(user['_id'])
    user = orm.Users.insert_one(
        {'email': email, 'subscriptions': [], 'subscribers': []})
    return str(user.inserted_id)


def get_response(req_data, user_id):
    '''
    Send the user's input to GPT and return the response. 
    '''
    # get the payload
    content = req_data['msg']
    quiet_mode = req_data['quietMode']
    # store the input message immediately so it is retained.
    today = datetime.date.today().strftime('%Y-%m-%d')

    # get the prior chats from today
    entry = orm.Entries.find_one(
        {"user_id": user_id, 'date': today}, {'chats': 1, '_id': 0})
    if not entry or not entry.get('chats'):
        chats = []
    else:
        chats = entry.get('chats')

    # store the last user message
    thread_input_txt = Thread(target=store_message, args=(
        user_id, content, 'user', today))
    thread_input_txt.start()
    # if it is quiet mode, you are done
    if quiet_mode:
        return {'success': True}

    chats.append({'role': 'user', 'content': content})

    # let's just use the last response from bot as history
    # We need to use more text though unless we run out of token limit.
    chat_history = chats[-1:]
    # get response from the bot
    messages = [{'role': 'system',
                 "content": chat_system_message}]
    messages.extend(chat_history)
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
    outpt = res['choices'][0]['message']['content']
    thread_output_txt = Thread(target=store_message, args=(
        user_id, outpt, 'bot', today))
    thread_output_txt.start()

    return outpt


def get_chats_by_date(user_id, date):
    entry = orm.Entries.find_one({'user_id': user_id, 'date': date})
    if entry:
        return entry.get('chats')
    else:
        return []


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
        orm.insert_summary(user_id, today_str, summary=summary)


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
        return "not enough content to summarize."
    prompt = f"{summarize_prompt} ```{text}```"
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
        return "there was an error in the summary"
    summary = summary.strip()
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
                          background_color='white', color_func=lambda *args, **kwargs: "blue").generate(txt)
        file_path = f"./uploads/{user_id}_{today_str}.png"
        image.to_file(file_path)

        if os.path.exists(file_path):
            orm.upload_to_s3(file_path, user_id, today_str)
            os.remove(file_path)


def analyze(user_id, analysis_type, wordcloud=False):
    # get today's chat
    today = datetime.date.today().strftime('%Y-%m-%d')
    entry = orm.Entries.find_one(
        {'user_id': user_id, 'date': today}, {'chats': 1, '_id': 0})
    if entry and entry.get('chats'):
        chats = entry.get('chats')
    else:
        chats = []

    content = ''
    for chat in chats:
        if chat.get('role') == 'user':
            content = content + '\n' + chat['content']
    insights = get_insight(content)
    # get insights from today's chat
    summary = summarize(content)
    # make wordcloud from today's chat
    if wordcloud:
        image = WordCloud(collocations=False,
                          background_color='white').generate(content)
        filename = f"{user_id}_{today}.png"
        image.to_file('./static/'+filename)
    orm.insert_summary(user_id, today,
                       summary=summary, insights=insights)
    if analysis_type == 'insights':
        return insights
    if analysis_type == 'summary':
        return summary
    if analysis_type == 'done':
        return None


def get_insight(txt):

    if len(txt) < 150:
        return "Not enough content to get insights from"

    prompt = f"{insight_prompt} ```{txt}```"
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
        return ''
    insight = insight.strip()
    return insight


def get_chat_history(user_id):
    '''
    preload the chat page with
    - prior chat from the same day
    - if none, then summary and insights from the last day
    - if none, then general prompt
    '''

    # Get today's date as a string
    today = str(date.today())

    sort = [("time", 1)]  # Sort by the "time" field in ascending order

    entry = orm.Entries.find_one(
        {"user_id": user_id, "date": today}, {'chats': 1, '_id': 0})

    if not entry or not entry.get('chats'):
        chats = []
    else:
        chats = entry['chats']

    if not chats:
        last_entry = list(orm.Summaries.find({'user_id': user_id}).sort(
            'date', pymongo.DESCENDING).limit(1))
        if last_entry and last_entry[0].get('summary'):
            content = f"To help you start a new entry, here are summary ans insights from your last writing: \n {last_entry[0].get('summary')} \n {last_entry[0].get('insights')}"
            return [{'role': 'initial_prompt', 'content': content}]
        # the first ever prompt
        else:
            content = "This is your first entry. If you prefer, set me on Quiet mode, and start writing. If you prefer to get my input, leave it on interactive mode.\nHere are some suggestions to get started:\nDescibe your day\nTalk about your emotions\nWrite a letter to future self"
            return [{'role': 'initial_prompt', 'content': content}]

    return chats


def send_email(date, email, content):
    aws_client = boto3.client('ses', region_name=AWS_REGION)

    BODY_TEXT = (content
                 )
    BODY_HTML = f"""<html>
        <head></head>
        <body>
          <p>{content}</p>
        </body>
        </html>
            """
    try:
        # Provide the contents of the email.
        response = aws_client.send_email(
            Destination={
                'ToAddresses': [
                    email,
                ],
            },
            Message={
                'Body': {
                    'Html': {
                        'Charset': "UTF-8",
                        'Data': BODY_HTML,
                    },
                    'Text': {
                        'Charset': "UTF-8",
                        'Data': BODY_TEXT,
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': f'Chat Content for {date}',
                },
            },
            Source=SENDER_EMAIL,
            # If you are not using a configuration set, comment or delete the
            # following line
            # ConfigurationSetName=CONFIGURATION_SET,
        )
    # Display an error if something goes wrong.
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])
