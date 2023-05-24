from pymongo import MongoClient
import datetime
from flask import Flask
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
import logging

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')

# Create a logger
logger = logging.getLogger('app_logger')

ENV_FILE = find_dotenv()
if ENV_FILE:
    load_dotenv(ENV_FILE)

# Email configuration

SENDER_EMAIL = env.get("SMTP_USERNAME")
AWS_REGION = "us-east-1"


def init_app():
    app = Flask(__name__)
    app.secret_key = env.get("APP_SECRET_KEY")

    return app


openai.api_key = env.get("OPENAI_KEY")

# this is the system message for chat echanges
chat_system_message = "Your task is to be a good listener, and encourage deeper conversation. You may aknowledge what you were said or ask follow up questions. Respond 'I am listening' if not sure about the answer. Be as brief as possible. Say at most 30 words."

summarize_prompt = """Your task is to generate a short summary of a diary based on principles of reflective listening.
Offer validation for feelings expressed. Summarize the diary in 3 sentences or less.
Diary: {text}
Summary:"""

insight_prompt = """Your task is to extract insights from the entry. Provide the overall sentiment of the entry in one sentence.
Then, analyze the entry and describe the feelings, thoughts and facts in one sentence.
Then, list the beliefs that lead to those feelings and thoughts. Say at most two sentences.
Entry: {text}
Insights:"""

actions_prompt = """List action items that the writer of the diary could follow. Respond in at most 80 words.
Diary: {text}
Actions:"""

# the max number of tokens I want to receive from the assistant in chat exchanges
max_chat_tokens = 200

# the max number of tokens I want to receive from the assistant in the summary and insights
max_analysis_tokens = 350


def store_message(user_id, content, role, date):
    '''
    When a new chat exchange happens, it appends it to the entry document
    '''
    orm.Entries.update_one({'user_id': user_id, 'date': date},
                           {"$push": {"chats": {'role': role, 'content': content}}},
                           upsert=True
                           )


def store_analysis(user_id, summary, insights, actions, date):
    '''
    Store summary and insight to in the entry document
    '''
    orm.Entries.update_one(
        {'user_id': user_id, 'date': date},
        {'$set': {'summary': summary, 'insights': insights, 'actions': actions}},
        upsert=True
    )


def get_user_id(email):
    '''
    return 
    - user_id for given email address. 
    - true or false for signing terms and conditions

    '''
    user = orm.Users.find_one({'email': email})
    if user:
        return str(user['_id']), user.get('terms_conditions', False)
    user = orm.Users.insert_one(
        {'email': email, 'subscriptions': [], 'subscribers': []})
    return str(user.inserted_id), False


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

    # we want to send the largest piece of text that does not exceed token limit
    gpt_3p5_token_limit = 4096 - max_chat_tokens - 5  # 5 is the margin for error
    start = 0
    exceeds_token_limit = True
    while exceeds_token_limit and start < len(chats):
        chats_truncated = chats[start:]
        messages = [{'role': 'system',
                     "content": chat_system_message}]
        messages.extend(chats_truncated)
        token_cnt = get_token_count_chat_gpt(messages)
        if token_cnt < gpt_3p5_token_limit:
            exceeds_token_limit = False
        else:
            start += 1

    try:
        res = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=max_chat_tokens,
            temperature=0.1,
        )
    except Exception as e:
        logger.exception('openai exception occured')
        return "Gagali cannot respond. Sorry about that. Go on."

    # store the user input and assistant's response to db
    outpt = res['choices'][0]['message']['content']
    thread_output_txt = Thread(target=store_message, args=(
        user_id, outpt, 'assistant', today))
    thread_output_txt.start()

    return outpt


def get_chats_by_date(user_id, date):
    '''
    return the chat exchanges for a given date
    '''
    entry = orm.Entries.find_one({'user_id': user_id, 'date': date})
    if not entry.get('summary'):
        analyze(user_id, date, 'done')
    if entry:
        return entry.get('chats'), entry.get('summary'), entry.get('insights')
    else:
        return []


def remove_subscriber(req_data, publisher_user_id, publisher_email):
    '''
    If you don't want your therapist to follow you anymore
    '''
    subscriber_email = req_data['email']
    orm.Users.update_one({"_id": ObjectId(publisher_user_id)}, {
        "$pull": {"subscribers": subscriber_email}})

    orm.Users.update_one({"email": subscriber_email}, {
        "$pull": {"subscriptions": publisher_email}})


def add_subscriber(req_data, publisher_user_id, publisher_email):
    '''
    add your therapist as your follower
    '''
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
    '''
    Make a list of your subscribers , like therapists, etc
    '''
    user = orm.Users.find_one({'_id': ObjectId(user_id)})
    return user['subscribers']


def get_subscriptions(user_id):
    '''
    if you are a therapist and you want to get a list of your patients
    '''
    user = orm.Users.find_one({'_id': ObjectId(user_id)})
    return user['subscriptions']


def get_token_count_analysis(content, model="text-curie-001"):
    """Returns the number of tokens used by a single text body.
    We use this for completion tasks, like summary and insights"""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    num_tokens = len(encoding.encode(content))
    return num_tokens


def get_token_count_chat_gpt(messages, model="gpt-3.5-turbo"):
    """Returns the number of tokens used by a list of messages."""
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    # every message follows <|start|>{role/name}\n{content}<|end|>\n
    tokens_per_message = 4
    tokens_per_name = -1  # if there's a name, the role is omitted

    num_tokens = 0
    for message in messages:
        num_tokens += tokens_per_message
        for key, value in message.items():
            num_tokens += len(encoding.encode(value))
            if key == "name":
                num_tokens += tokens_per_name
    num_tokens += 3  # every reply is primed with <|start|>assistant<|message|>
    return num_tokens


def summarize(text):
    summary = text
    if len(text) < 150:
        return text
    prompt = summarize_prompt.format(text)
    try:
        res = openai.Completion.create(
            model="text-curie-001",
            prompt=prompt,
            temperature=0.15,
            max_tokens=max_chat_tokens,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0
        )
        summary = res['choices'][0]['text']
        if len(summary)/len(text) > 0.9:  # use the summary if it is sufficiently shorter
            summary = text
    except Exception as e:
        logger.exception('there was an error with summarize')
        return "there was an error in the summary"
    summary = summary.strip()
    return summary


def generate_wordcloud(user_id, date, content):

    users = orm.Users.find({}, {'_id': 1})
    # if there is not much text, skip this
    if len(content) < 400:
        return

    image = WordCloud(collocations=False,
                      background_color='white', color_func=lambda *args, **kwargs: "blue").generate(content)
    file_path = f"./wordcloud/{user_id}_{date}.png"
    image.to_file(file_path)

    if os.path.exists(file_path):
        orm.upload_to_s3(file_path, user_id, date)
        os.remove(file_path)


def analyze(user_id, date, analysis_type):
    entry = orm.Entries.find_one(
        {'user_id': user_id, 'date': date}, {'chats': 1, '_id': 0})
    if entry and entry.get('chats'):
        chats = entry.get('chats')
    else:
        chats = []

    content = []
    for chat in chats:
        if chat.get('role') == 'user':
            content.append(chat['content'])

    total_words = 0
    for sentence in content:
        words = sentence.split()
        total_words += len(words)
    if total_words < 30:
        return 'not enough content'

    # let's make sure we don't go over the token limit
    completion_token_limit = 2049 - max_analysis_tokens - 5  # 5 for the margin of error
    start = 0
    exceeds_token_limit = True
    if len(summarize_prompt) > len(insight_prompt):
        longest_prompt = summarize_prompt
    else:
        longest_prompt = insight_prompt
    while start < len(content) and exceeds_token_limit:
        content_trunc = content[start:]

        token_cnt = get_token_count_analysis(
            longest_prompt+'. '.join(content_trunc))
        if token_cnt < completion_token_limit:
            exceeds_token_limit = False
        else:
            start += 1
    content_trunc = '. '.join(content_trunc)
    insights = get_insight(content_trunc)
    # get insights from today's chat
    summary = summarize(content_trunc)
    # get actions
    actions = get_actions(content_trunc)

    # make wordcloud from today's chat
    thread_wordcloud = Thread(
        target=generate_wordcloud, args=(user_id, date, ' '.join(content)))
    thread_wordcloud.start()
    thread_analyziz = Thread(target=store_analysis, args=(
        user_id, summary, insights, actions, date))
    thread_analyziz.start()

    if analysis_type == 'insights':
        return insights
    if analysis_type == 'summary':
        return summary
    if analysis_type == 'done':
        return None
    if analysis_type == 'actions':
        return actions


def get_insight(text):

    if len(text) < 150:
        return "Not enough content for insights"

    prompt = insight_prompt.format(text)
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
        logger.exception('insights error')
        return ''
    insight = insight.strip()
    return insight


def get_actions(text):

    if len(text) < 150:
        return "Not enough content for analysis"

    prompt = actions_prompt.format(text)
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
        logger.exception('actions error')
        return ''
    actions = actions.strip()
    return actions


def get_chat_history(user_id):
    '''
    preload the chat page with
    - prior chat from the same day
    - if none, then summary and insights from the last day
    - if none, then general prompt
    '''

    # Get today's date as a string
    today = datetime.date.today()
    today_str = today.strftime('%Y-%m-%d')
    entry = orm.Entries.find_one(
        {"user_id": user_id, "date": today_str}, {'chats': 1, '_id': 0})

    if not entry or not entry.get('chats'):
        chats = []
    else:
        chats = entry['chats']

    if not chats:
        last_entry = list(orm.Entries.find({'user_id': user_id}).sort(
            'date', pymongo.DESCENDING).limit(1))
        if last_entry and last_entry[0].get('summary'):
            content = f"To help you start a new entry, here are summary ans insights from your last writing: \n {last_entry[0].get('summary')} \n {last_entry[0].get('insights')}"
            return [{'role': 'initial_prompt', 'content': content}]
        # the first ever prompt
        else:
            content = "This is your first entry. If you prefer, set me on Quiet mode, and start writing. If you prefer to get my input, leave it on interactive mode.\nHere are some suggestions to get started:\nDescibe your day\nTalk about your emotions\nWrite a letter to future self"
            return [{'role': 'initial_prompt', 'content': content}]

    return chats


def send_email(date, email, chats, summary, insights):
    aws_client = boto3.client('ses', region_name=AWS_REGION)

    BODY_TEXT = ''
    for chat in chats:
        BODY_TEXT = BODY_TEXT + \
            f"\n{chat.get('role','')}: {chat.get('content','')}"

    BODY_HTML = '<html>\n<body>\n'
    if summary:
        BODY_HTML += '<h4>Summary</h4>\n'
        BODY_HTML += '<p><em>{}</em></p>\n'.format(summary)
    if insights:
        BODY_HTML += '<h4>Insights</h4>\n'
        BODY_HTML += '<p><em>{}</em></p>\n'.format(insights)
        BODY_HTML += '<h4>Entry</h4>\n'
    for chat in chats:
        role = chat.get('role', '')
        content = chat.get('content', '')

        if role == 'assistant':
            BODY_HTML += '<p><em>{}</em></p>\n'.format(content)
        else:
            BODY_HTML += '<p>{}</p>\n'.format(content)

    BODY_HTML += '</body>\n</html>'

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
        logger.exception('email error')
    else:
        print("Email sent! Message ID:"),
        print(response['MessageId'])


def register_terms(user_id):
    try:
        orm.Users.update_one({'_id': ObjectId(user_id)}, {'$set': {'terms_conditions': True}}
                             )
    except Exception as e:
        logger.exception('register terms error')
