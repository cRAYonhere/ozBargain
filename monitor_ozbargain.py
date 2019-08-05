#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import re
import numpy as np
from time import sleep, time
import sched
from datetime import datetime
import sqlite3

db = {}
s = sched.scheduler(time, sleep)


def init_database():
    conn = sqlite3.connect('deal.db')
    global c
    c = conn.cursor()
    c.execute('''CREATE TABLE DEALS(
    [deal_id] INTEGER PRIMARY KEY,
    [title] TEXT,
    [vote] TEXT,
    [datetime] DATETIME)
    ''')
    conn.commit()


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
    debug_file = open('debug.txt', 'w')
    debug_file.write(ad_id+", "+vote+", "+title+", "+time)
    debug_file.close()


def store(ad_id, vote, title, time):
    debug(ad_id, vote, title, time)
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


def growth_rate():
    for key in db:
        if len(db[key]['vote']) > 1:
            # print(db[key]['vote'])
            a = np.array([db[key]['vote']]).astype(float)
            growth_rate = np.nanmean((a[:, 1:]/a[:, :-1]), axis=1) - 1
            # Need a Better Notification Mechanism
            if growth_rate > 0.51:
                print("Found a Good Deal")
                # Email Me


if __name__ == "__main__":
    while True:
        process_page('https://www.ozbargain.com.au/deals')
        growth_rate()
        clean()
        sleep(5)
    # ozbargain_struct(response)
