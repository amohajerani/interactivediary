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
from logger import logger
import time
import re

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

summarize_prompt = """Identify the most salient sentiment of my diary.  List most important facts, organized into 4 brief bullets points.
Diary: {text}
Summary:"""

insight_prompt = """Respond in a friendly and thoughtful tone. Refer to the writer as "you". Analyze my diary and write the following 3 bullet points: First, describe my overall sentiment from the diary. Start with "It sounds like". Second, summarize main conflict conveyed in my diary. Start with "The issue is that" Third, list the my beliefs that lead to those feelings and thoughts. Provide validation for the sentiment in one sentence. Then, under heading "challenge", gently invite or challenge me to do one thing that could lead to improved well being. If poor exhaustion, negative feelings, poor self care is noted in the diary, lovingly suggest more self care. Also gently suggest an alternative to my belief outlined earlier.
Diary: {text}
Insights:"""

actions_prompt = """List, in at most 100 words, the action items that the writer of the diary could follow. Do not number the action items.
Diary: {text}
Actions:"""

# the max number of tokens I want to receive from the assistant in chat exchanges
max_chat_tokens = 200

# the max number of tokens I want to receive from the assistant in the summary and insights
max_analysis_tokens = 350


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


def get_response(req_data):
    '''
    Send the user's input to GPT and return the response.
    '''
    # get the payload
    content = req_data['msg']
    quiet_mode = req_data['quietMode']
    entry_id = req_data['entry_id']

    # get the prior chats from today
    entry = orm.get_entry(entry_id)
    chats = entry.get('chats')

    # store the last user message
    thread_input_txt = Thread(target=orm.add_chat_to_entry, args=(
        entry_id, 'user',content))
    thread_input_txt.start()
    # if it is quiet mode, you are done
    if quiet_mode:
        return {'success': True}

    chats.append({'role': 'user', 'content': content})

    # we want to send the largest piece of text that does not exceed token limit
    gpt_3p5_token_limit = 4096 - max_chat_tokens - 5  # 5 is the margin for error.
    start = 2 # instead of zero to ensure initial prompting messages are retained
    exceeds_token_limit = True
    while exceeds_token_limit and start < len(chats):
        chats_truncated = chats[start:]
        messages = chats[:2]+chats_truncated
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
            temperature=0.0,
        )
    except Exception as e:
        logger.exception('openai exception occured')
        return "Gagali cannot respond. Sorry about that. Go on."

    # store the assistant's response to db
    outpt = res['choices'][0]['message']['content']
    thread_output_txt = Thread(target=orm.add_chat_to_entry, args=(
        entry_id, 'assistant', outpt))
    thread_output_txt.start()

    return outpt



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
    if not text:
        return 'No entry yet'
    summary = text
    if len(text) < 150:
        return text
    prompt = summarize_prompt.format(text=text)

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


def generate_wordcloud(user_id, content):
    # make word cloud for the content provided. 
    # if there is not much text, skip this
    if len(content) < 400:
        return

    image = WordCloud(collocations=False,
                      background_color='white', color_func=lambda *args, **kwargs: "black").generate(content)
    date=str(int(time.time()))
    file_path = f"./wordcloud/{user_id}_{date}.png"
    image.to_file(file_path)

    if os.path.exists(file_path):
        orm.upload_to_s3(file_path, user_id, date)
        os.remove(file_path)


def analyze(entry_id, analysis_type):
    entry = orm.Entries.find_one(
        {'_id': ObjectId(entry_id)})
    user_id = entry.get('user_id')
    chats = entry.get('chats')
    content = []
    for chat in chats[2:]:
        if chat.get('role') == 'user':
            processed_content = chat['content'].replace("'", "\\'")
            processed_content = chat['content'].replace('"', '\\"') 
            content.append(processed_content)

    total_words = 0
    for sentence in content:
        words = sentence.split()
        total_words += len(words)


    # let's make sure we don't go over the token limit
    completion_token_limit = 2049 - max_analysis_tokens - 5  # 5 for the margin of error
    start = 0
    exceeds_token_limit = True
    content_trunc=[]# for the edge case where there are no chats
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
    if analysis_type=='insights':
        return get_insight(content_trunc)
    # get insights from today's chat
    if analysis_type=='summary':
        return summarize(content_trunc)
    # get actions
    if analysis_type=='actions':
        return get_actions(content_trunc)
    if analysis_type=='done':
        # make wordcloud from today's chat
        thread_wordcloud = Thread(
            target=generate_wordcloud, args=(user_id, ' '.join(content)))
        thread_wordcloud.start()

        entry_updates = {'summary':summarize(content_trunc),
                        'insights':get_insight(content_trunc),
                        'actions':get_actions(content_trunc)}
        orm.update_entry(entry_id, entry_updates)
        return None


def get_insight(text):
    insight=''
    if len(text) < 150:
        return insight

    prompt = insight_prompt.format(text=text)

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
    return insight+'\n prompt was: prompt'


def get_actions(text):
    actions=''
    if len(text) < 150:
        return actions

    prompt = actions_prompt.format(text=text)
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
    if '1.' in actions:
        actions = re.split(r'\d+\.\s', actions)
    elif '- ' in actions:
        actions = actions.split('- ')
    else:
        actions = actions.split('. ')
    cleaned_actions = []
    for action in actions:
        if len(action)>2:
            action = action.strip()
            action = action.rstrip('\n')
            cleaned_actions.append(action)
    return cleaned_actions

def send_email(entry, email):
    aws_client = boto3.client('ses', region_name=AWS_REGION)

    BODY_TEXT = ''
    for chat in entry.chats:
        BODY_TEXT = BODY_TEXT + \
            f"\n{chat.get('role','')}: {chat.get('content','')}"

    BODY_HTML = '<html>\n<body>\n'
    if entry.summary:
        BODY_HTML += '<h4>Summary</h4>\n'
        BODY_HTML += '<p><em>{}</em></p>\n'.format(entry.summary)
    if entry.insights:
        BODY_HTML += '<h4>Insights</h4>\n'
        BODY_HTML += '<p><em>{}</em></p>\n'.format(entry.insights)
        BODY_HTML += '<h4>Entry</h4>\n'
    for chat in entry.chats:
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
                    'Data': f'Entry: {entry.title}',
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

def close_entry(entry_id):
    orm.update_entry(entry_id, {'completed':1})
    thread_analyze = Thread(target=analyze, args=(
        entry_id, 'done'))
    thread_analyze.start()
    return
