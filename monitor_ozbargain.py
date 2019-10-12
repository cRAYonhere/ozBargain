#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import re
from time import sleep, time
import sched
from datetime import datetime
import sqlite3
import base64
import uuid

import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request



db = {}
s = sched.scheduler(time, sleep)
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

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
        print("Warning in VOTES: ",error)
        input("Press Any Key to continue, Ctrl+C to exit")

    try:
        c.execute('''CREATE TABLE DEALS(
        [deal_id] PRIMARY KEY,
        [title] TEXT,
        [datetime] DATETIME,
        [email_sent] INTEGER)
        ''')
    except sqlite3.OperationalError as error:
        print("Warning in DEALS: ",error)
        input("Press Any Key to continue, Ctrl+C to exit")

    try:
        c.execute('''CREATE TABLE USERS(
        [email] TEXT,
        [wants] TEXT,
        [priority] INTEGER),
        UNIQUE(email,wants)
        ''')
    except sqlite3.OperationalError as error:
        print("Warning in USERS: ",error)
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

        insert_deals = '''INSERT INTO DEALS(deal_id, title, datetime, email_sent) VALUES (?, ?, ?, ?)'''
        insert_votes = '''INSERT INTO VOTES(entry_id, deal_id, vote, datetime) VALUES (?, ?, ?, ?)'''

        #DEAL
        value = (
                    ad['id'].replace('node',''),
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
        #VOTE
        value = (
                    str(uuid.uuid1()),
                    ad['id'].replace('node',''),
                    re.search(r'[0-9]+', str(span_voteup.find('span'))).group(),
                    date_time,
                )
        try:
            conn.execute(insert_votes, value)
        except sqlite3.OperationalError as error:
            print("Warning Insert in deal: ", error)
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
    insert_user_needs = '''INSERT INTO VOTES(email, wants, priority) VALUES (?, ?, ?)'''
    for item in formatted:
        try:
            conn.execute(insert_user_needs, item)
        except sqlite3.IntegrityError as error:
            pass
        except sqlite3.OperationalError as error:
            print("Warning Insert in deal: ", error)
            input("Press Any Key to continue, Ctrl+C to exit")

def wanted_item(conn):
    add_users(conn)
    

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
    add_users()
    '''
    #init_linear_growth_table()
    init_databases()
    conn = sqlite3.connect('ozbargain.db')
    while True:
        process_page(conn,'https://www.ozbargain.com.au/deals?page=1')
        process_page(conn, 'https://www.ozbargain.com.au/deals?page=2')
        trending_deal()
        wanted_item(conn)
        clean()
        sleep(5)
    # ozbargain_struct(response)
    '''
