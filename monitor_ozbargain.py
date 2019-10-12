#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import re
from time import sleep, time
import sched
import sqlite3
import uuid
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from fuzzywuzzy import fuzz


from email_me import create_message, send_message

s = sched.scheduler(time, sleep)
SCOPES = ['https://www.googleapis.com/auth/gmail.send']
STRING_MATCHING_THRESHOLD = 49


def init_databases():
    conn = sqlite3.connect('ozbargain.db')
    c = conn.cursor()

    try:
        c.execute('''CREATE TABLE VOTES(
        [entry_id] PRIMARY KEY,
        [deal_id] INTEGER,
        [vote] TEXT,
        [datetime] DATETIME)
        ''')
    except sqlite3.OperationalError as error:
        print("Warning in VOTES: ", error)
        input("Press Any Key to continue, Ctrl+C to exit")

    try:
        c.execute('''CREATE TABLE DEALS(
        [deal_id] PRIMARY KEY,
        [title] TEXT,
        [datetime] DATETIME,
        [email_sent] INTEGER)
        ''')
    except sqlite3.OperationalError as error:
        print("Warning in DEALS: ", error)
        input("Press Any Key to continue, Ctrl+C to exit")

    try:
        c.execute('''CREATE TABLE USERS(
        [email] TEXT,
        [wants] TEXT,
        [priority] INTEGER,
        UNIQUE(email,wants))
        ''')
    except sqlite3.OperationalError as error:
        print("Warning in USERS: ", error)
        input("Press Any Key to continue, Ctrl+C to exit")

    conn.commit()
    conn.close()


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


def process_page(conn, link):
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

        insert_deals = '''INSERT INTO DEALS(
                                            deal_id,
                                            title,
                                            datetime,
                                            email_sent)
                                            VALUES (?, ?, ?, ?)'''
        insert_votes = '''INSERT INTO VOTES(
                                            entry_id,
                                            deal_id,
                                            vote,
                                            datetime)
                                            VALUES (?, ?, ?, ?)'''

        # DEAL
        value = (
                    ad['id'].replace('node', ''),
                    ad.find('h2', {'class': 'title'})['data-title'],
                    date_time,
                    0
                )
        try:
            conn.execute(insert_deals, value)
        except sqlite3.IntegrityError as error:
            pass
        except sqlite3.OperationalError as error:
            print("Warning Insert in deal: ", error)
            input("Press Any Key to continue, Ctrl+C to exit")
        # VOTE
        value = (
                    str(uuid.uuid1()),
                    ad['id'].replace('node', ''),
                    re.search(r'[0-9]+', str(span_voteup.find('span'))).group(),
                    date_time,
                )
        try:
            conn.execute(insert_votes, value)
        except sqlite3.OperationalError as error:
            print("Warning Insert in vote: ", error)
            input("Press Any Key to continue, Ctrl+C to exit")


def trending_deal():
    pass


def add_users(conn):
    '''
    https://stackoverflow.com/questions/50535725/manage-data-from-txt-file-to-store-it-to-sqlite3-in-python
    '''
    # read data from file
    f = open('wanted.txt', 'r')
    cont = f.read()
    f.close()

    # format for inserting to db
    rows = cont.split('\n')
    formatted = [tuple(x.split()) for x in rows]
    insert_user_needs = ('''INSERT INTO USERS(
                                            email,
                                            wants,
                                            priority)
                                            VALUES (?, ?, ?)''')
    for item in formatted:
        try:
            if item:
                conn.execute(insert_user_needs, item)
        except sqlite3.IntegrityError as error:
            pass
        except sqlite3.OperationalError as error:
            print("Warning Insert in user: ", error)
            input("Press Any Key to continue, Ctrl+C to exit")


def removearticles(text):
    '''
    https://stackoverflow.com/questions/4709665/remove-all-articles-connector-words-etc-from-a-string-in-python
    '''
    articles = {'a': '', 'an': '', 'and': '', 'the': ''}
    rest = []
    for word in text.split():
        if word not in articles:
            rest.append(word)
    return ' '.join(rest)


def substring_search(user_wants, deal_title):
    '''
    https://chairnerd.seatgeek.com/fuzzywuzzy-fuzzy-string-matching-in-python/
    '''
    if user_wants in deal_title:
        return 1
    score = fuzz.ratio(user_wants, deal_title)
    print(score)
    if score > STRING_MATCHING_THRESHOLD:
        return 1
    return 0


def wanted_item(conn):
    email_dict = {}
    fetch_user_wants = ('''SELECT email, wants
                            FROM USERS''')
    fetch_deals = ('''SELECT deal_id,title,email_sent
                        FROM DEALS''')
    add_users(conn)

    cur = conn.cursor()

    cur.execute(fetch_user_wants)
    user_wants_list = cur.fetchall()

    cur.execute(fetch_deals)
    deals_list = cur.fetchall()
    # print(user_wants_list)
    # print(deals_list)
    for user_wants in user_wants_list:
        for deal in deals_list:
            temp1 = user_wants[1].lower()
            temp2 = deal[1].lower()
            if deal[2] == 0 and substring_search(temp1, temp2):
                if user_wants[0] in email_dict:
                    email_dict[user_wants[0]].append(deal[0])

    update_email_set = ('''UPDATE DEALS
                        SET email_sent = 1
                        WHERE email_sent = 0''')
    cur.execute(update_email_set)
    for key in email_dict.keys():
        print(key+' '+email_dict[key])


def init_email(message):
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
    return service
    message = create_message("pytonray@gmail.com",)
    send_message(service, "me", message)


if __name__ == "__main__":

    init_databases()
    conn = sqlite3.connect('ozbargain.db')
    while True:
        process_page(conn, 'https://www.ozbargain.com.au/deals?page=1')
        process_page(conn, 'https://www.ozbargain.com.au/deals?page=2')
        wanted_item(conn)
        sleep(5)
    # ozbargain_struct(response)
