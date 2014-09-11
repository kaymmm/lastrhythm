#!/usr/bin/env python

import json
import requests
import xml.etree.ElementTree as ET


BASE_URL = "http://ws.audioscrobbler.com/2.0/"
API_KEY = "5fd9edac8d47aee4c1a5cb4214a7eb87"
USERNAME = "mkanyicy"

PARAMS = {
    "format": "json",
    "method": "library.gettracks",
    "page": 1,
    "limit": 10,
    "api_key": API_KEY,
    "user": USERNAME
}

def get_track(item):
    return {
        'title': item['name'],
        'artist': item.get('artist', {}).get('name'),
        'album': item.get('album', {}).get('name'),
        'playcount': item['playcount'],
        'duration': item['duration']
    }


def load_rb_tracks():
    rb_file = 'rhythmdb.xml'
    tree = ET.parse(rb_file)
    root = tree.getroot()
    fields = [
        ('play-count', 0),
        ('duration', 0),
        ('title', ''),
        ('artist', ''),
        ('album', '')
    ]
    return [{k.replace('-', ''): getattr(child.find(k), 'text', v) for k, v in fields for child in root}]

def get_tracks(items):
    return [get_track(item) for item in items]

if __name__ == '__main__':
    resp = requests.get(BASE_URL, params=PARAMS)
    assert resp.status_code == 200, "Failed fetching data from Last.fm"
    data = resp.json()
    last_fm_tracks = get_tracks(data['tracks']['track'])
    pagination = data['tracks']['@attr']

    debug = True
    while not debug and PARAMS['page'] > int(pagination['totalPages']):
        PARAMS['page'] += 1
        resp = requests.get(BASE_URL, params=PARAMS)
        assert resp.status_code == 200

        data = resp.json()
        last_fm_tracks += get_tracks(data['tracks']['track'])

    print last_fm_tracks
    rhythmbox_tracks = load_rb_tracks()
    for track in rhythmbox_tracks:
        track['duration'] += '000'

    match_fields = ['title', 'duration', 'artist', 'album']
    for track in last_fm_tracks:
        print track
        found = False
        for rb_track in rhythmbox_tracks:
            for m in match_fields:
                pass