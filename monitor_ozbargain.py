#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import re
from flask import jsonify
import numpy as np
from time import sleep, time
import sched
from datetime import datetime
import sqlite3
import pickle

db = {}
s = sched.scheduler(time, sleep)

sqlite3.connect('deal.db')

def clean():
    for key in db:
        delete_list = []
        print(db[key]['time'])
        datetime_object = datetime.strptime(db[key]['time'], '%d/%m/%Y - %H:%M')
        time_elapsed = datetime.now() - datetime_object
        if(time_elapsed.total_seconds()/60 > 45):
            delete_list.append(key)
        for key in delete_list:
            del db[key]


def store(ad_id, vote, title, time):
    if ad_id in db:
        db[ad_id]['vote'].append(int(vote))
    else:
        db[ad_id] = {'vote': [int(vote)], 'title': title, 'time': time}


def process_page(link):
    page = requests.get(link)
    soup = BeautifulSoup(page.text, 'html.parser')
    # Title = soup.findAll('h2', {'class':'title'})
    ads = soup.findAll('div', {'class': 'node-ozbdeal'})

    for ad in ads:
        store(ad['id'], re.search(r'[0-9]+', str(ad.find('span', {'class': 'voteup'}).find('span'))).group(), ad.find('h2',{'class':'title'})['data-title'], re.search(r'[0-9]{2}/[0-9]{2}/20[0-9]{2} - [0-9]{2}:[0-9]{2}', str(ad.find('div',{'class':'submitted'}))).group())


'''
    src: https://stackoverflow.com/questions/34516729/quickest-way-to-calculate-the-average-growth-rate-across-columns-of-a-numpy-arra
'''


def growth_rate():
    for key in db:
        if len(db[key]['vote']) > 1:
            # print(db[key]['vote'])
            a = np.array([db[key]['vote']]).astype(float)
            growth_rate = np.nanmean((a[:, 1:]/a[:, :-1]), axis=1) - 1
            if growth_rate > 0.51 and len(db[key]['vote'])


while True:
    process_page('https://www.ozbargain.com.au/deals')
    growth_rate()
    clean()
    sleep(5)
# ozbargain_struct(response)
