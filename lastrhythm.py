#!/usr/bin/env python

import os
import optparse

import requests
import xml.etree.ElementTree as ET


BASE_URL = "http://ws.audioscrobbler.com/2.0/"
API_KEY = "5fd9edac8d47aee4c1a5cb4214a7eb87"
USERNAME = "mkanyicy"
RHYTHM_DB = os.path.expanduser('~/.local/share/rhythmbox/rhythmdb.xml')

PARAMS = {
    "format": "json",
    "method": "library.gettracks",
    "page": 1,
    "limit": 200,
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
    tree = ET.parse(RHYTHM_DB)
    root = tree.getroot()
    return [
        {
            'playcount': str(int(getattr(child.find('play-count'), 'text', 0))),
            'duration': str(int(1000 * int(getattr(child.find('duration'), 'text', 0)))),
            'title': getattr(child.find('title'), 'text', ''),
            'artist': getattr(child.find('artist'), 'text', None),
            'album': getattr(child.find('album'), 'text', None),
            'node': child,
            'tree': tree
        }
        for child in root
    ]


def get_tracks(items):
    return [get_track(item) for item in items]

if __name__ == '__main__':
    resp = requests.get(BASE_URL, params=PARAMS)
    assert resp.status_code == 200, "Failed fetching data from Last.fm"
    data = resp.json()
    last_fm_tracks = get_tracks(data['tracks']['track'])
    pagination = data['tracks']['@attr']
    while PARAMS['page'] > int(pagination['totalPages']):
        PARAMS['page'] += 1
        resp = requests.get(BASE_URL, params=PARAMS)
        assert resp.status_code == 200

        data = resp.json()
        last_fm_tracks += get_tracks(data['tracks']['track'])

    rhythmbox_tracks = load_rb_tracks()
    tree = None
    for track in rhythmbox_tracks:
        node = track.pop('node')
        tree = track.pop('tree')
        playcount = track.pop('playcount')
        duration = track.pop('duration')

        for stats in last_fm_tracks:
            stats = stats.copy()
            stats.pop('duration')
            last_fm_playcount = stats.pop('playcount')
            if stats == track and int(last_fm_playcount) > int(playcount):
                children = node.getchildren()
                playcount_element = None
                for child in children:
                    if child.tag == 'play-count':
                        playcount_element = child
                        break
                if playcount_element is None:
                    playcount_element = ET.SubElement(node, 'play-count')
                playcount_element.text = str(last_fm_playcount)

    if tree is not None:
        tree.write(RHYTHM_DB)

