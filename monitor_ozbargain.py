#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import re
from time import sleep, time
import sched
from datetime import datetime
import sqlite3
import base64

import pickle
import os.path
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from email.mime.text import MIMEText


db = {}
s = sched.scheduler(time, sleep)
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def init_database():
    conn = sqlite3.connect('deal.db')
    global c
    c = conn.cursor()
    c.execute('''CREATE TABLE DEALS(
    [deal_id] INTEGER PRIMARY KEY,
    [title] TEXT,o365_auth = ('YourAccount@office365.com','YourPassword')
    [vote] TEXT,
    [datetime] DATETIME)
    ''')
    conn.commit()


def growth_rate(votes):
    try:
        y = ((votes[-1] - votes[0])/votes[0]) * 100
        x = y/len(votes)
    except ZeroDivisionError:
        x = 0
    return x


def init_linear_growth_table():
    global linear_growth_table
    linear_growth_table = []
    for val in range(1, 46):
        temp = [i for i in range(1, val)]
        if len(temp) > 1:
            linear_growth_table.append(growth_rate(temp))
            # print(temp)
            # print(growth_rate(temp))


def clean():
    delete_list = []
    for key in db:
        # print(db[key]['time'])
        datetime_object = datetime.strptime(
            db[key]['time'],
            '%d/%m/%Y - %H:%M'
            )
        time_elapsed = datetime.now() - datetime_object
        if(time_elapsed.total_seconds()/60 > 45):
            delete_list.append(key)
    for key in delete_list:
        del db[key]


def debug(ad_id, vote, title, time):
    debug_file = open('debug.txt', 'a')
    debug_file.write(ad_id+", "+vote+", "+title+", "+time+"\n")
    debug_file.close()


def store(ad_id, vote, title, time):
    debug(ad_id, vote, title, time)
    # print(ad_id, vote, title, time)
    if ad_id in db:
        db[ad_id]['vote'].append(int(vote))

        """
        c.execute('''INSERT INTO DEALS(
        [deal_id] INTEGER PRIMARY KEY,
        [title] TEXT,
        [vote] TEXT,
        [datetime] DATETIME)''')
        """

    else:
        db[ad_id] = {'vote': [int(vote)], 'title': title, 'time': time}


def process_page(link):
    page = requests.get(link)
    soup = BeautifulSoup(page.text, 'html.parser')
    # Title = soup.findAll('h2', {'class':'title'})
    ads = soup.findAll('div', {'class': 'node-ozbdeal'})

    for ad in ads:
        span_voteup = ad.find('span', {'class': 'voteup'})
        div_submitted = ad.find('div', {'class': 'submitted'})
        date_time = re.search(
            r'[0-9]{2}/[0-9]{2}/20[0-9]{2} - [0-9]{2}:[0-9]{2}',
            str(div_submitted)).group()
        store(
            ad['id'],
            re.search(r'[0-9]+', str(span_voteup.find('span'))).group(),
            ad.find('h2', {'class': 'title'})['data-title'],
            date_time
            )


'''
    src: https://stackoverflow.com/questions/
    34516729/quickest-way-to-calculate-the-average-growth-rate-across-columns-of-a-numpy-arra
'''


def deal_growth_rate_cal():
    for key in db:
        if len(db[key]['vote']) > 2:
            # print(db[key]['vote'])
            growth_r = growth_rate(db[key]['vote'])
            # print("Growth_rate "+str(growth_r))
            if growth_r > 350:
                print(db[key])
                init_email()


def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.

    Returns:
    An object containing a base64url encoded email object.
    """
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_string().encode()).decode()}

def send_message(service, user_id, message):
    """
    Send an email message.

    Args:
        service: Authorized Gmail API service instance.
        user_id: User's email address. The special value "me"
        can be used to indicate the authenticated user.
    message: Message to be sent.

    Returns:
        Sent Message.
    """
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print('Message Id: %s', message['id'])
        return message
    except HttpError as error:
        print('An error occurred: %s', error)

def init_email():
    """
    Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('gmail', 'v1', credentials=creds)

    # Call the Gmail API
    message = create_message()
    send_message(service, "me", message)

if __name__ == "__main__":

    init_linear_growth_table()
    while True:
        process_page('https://www.ozbargain.com.au/deals')
        deal_growth_rate_cal()
        clean()
        sleep(60)
    # ozbargain_struct(response)
