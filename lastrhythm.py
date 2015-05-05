#!/usr/bin/env python

import os
import sys
import optparse

import requests
import xml.etree.ElementTree as ET

API_KEY = "5fd9edac8d47aee4c1a5cb4214a7eb87"
BASE_URL = "http://ws.audioscrobbler.com/2.0/"
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
RHYTHM_DB = os.path.expanduser('~/.local/share/rhythmbox/rhythmdb.xml')


def get_track(item):
    return {
        'title'     : item['name'],
        'artist'    : item.get('artist', {}).get('name'),
        'album'     : item.get('album', {}).get('name'),
        'playcount' : item['playcount'],
        'duration'  : item['duration']
    }


def load_rb_tracks():
    db = ET.parse(RHYTHM_DB)
    root = db.getroot()
    return [
        {
            'playcount' : str(int(getattr(child.find('play-count'), 'text', 0))),
            'duration'  : str(int(1000 * int(getattr(child.find('duration'), 'text', 0)))),
            'title'     : getattr(child.find('title'), 'text', ''),
            'artist'    : getattr(child.find('artist'), 'text', None),
            'album'     : getattr(child.find('album'), 'text', None),
            'node'      : node,
            'tree'      : db
        }
        for node in root
    ]


def get_tracks(items):
    return [get_track(item) for item in items]


def get_last_fm_data(tracks=None, **params):
    print 'Fetching tracks from Last.fm ... ',
    params.setdefault('page', 1)
    resp = requests.get(BASE_URL, params=params)
    assert resp.status_code == 200, "Failed fetching data from Last.fm"
    data = resp.json()
    pagination = data['tracks']['@attr']
    tracks = tracks if tracks else []
    tracks += get_tracks(data['tracks']['track'])
    percent = 100.0 * params['page'] / float(pagination['totalPages'])
    print 'ok ... [%.1f%%]' % percent

    # recursively fetch all the available pages.
    if params['page'] <= int(pagination['totalPages']):
        params['page'] += 1
        get_last_fm_data(tracks=tracks, **params)
    return tracks


def is_equal(a, b, fuzzy=True):
    is_same = sorted(a.keys()) == sorted(b.keys())
    if is_same:
        if not fuzzy:
            is_same = all([
                a[key].lower() == b[key].lower()
                if a[key] is not None and b[key] is not None else a[key] == b[key]
                for key in a
            ])
        else:
            duration_a = int(a.pop('duration', -1))
            duration_b = int(a.pop('duration', -1))
            delta = abs(duration_a - duration_b)
            is_same = duration_a > 0 and duration_b > 0 and delta <= 10E3
            if is_same:
                import Levenshtein
                is_same = all([
                    abs(len(a[key]) - len(b[key])) < max(len(a[key]), len(b[key]))
                    and Levenshtein.distance(unicode(a[key].lower()), unicode(b[key].lower())) <= 5
                    if a[key] is not None and b[key] is not None else a[key] == b[key]
                    for key in a
                ])
    return is_same


def validate():
    if options.username is None:
        raise SystemExit('Last.fm username required. Use --help for help.')
    if os.system('which rhythmbox > /dev/null 2>&1') != 0:
        raise SystemExit('Rhythmbox music player is not installed.')
    if not os.path.exists(RHYTHM_DB):
        raise SystemExit('Rhythmbox DB file does not exist.')
    if os.system('rhythmbox-client --check-running') == 0:
        if options.force:
            print 'Warning: Rhythmbox is running.'
        else:
            raise SystemExit('Rhythmbox is running.')


if __name__ == '__main__':
    parser = optparse.OptionParser(usage='Usage: %prog --username <last.fm username>', version='1.0')
    parser.add_option('-u', '--username', help='Last.fm username')
    parser.add_option('-l', '--limit', type=int, default=250, help='Number of tracks per page to fetch')
    parser.add_option('--fuzzy', action='store_true', default=False,
                      help='Use fuzzy matching. Depends on python-Levenshtein library.')
    parser.add_option('-f', '--force', action='store_true', default=False,
                      help='Ignore warnings and continue regardless.')
    options, files = parser.parse_args()

    validate()

    last_fm_tracks = get_last_fm_data(
        format='json',
        method='library.gettracks',
        limit=options.limit,
        api_key=API_KEY,
        user=options.username
    )

    print 'Loading rhythmbox database file ... ',
    rhythmbox_tracks = load_rb_tracks()
    print 'ok'

    tree = None
    print 'Syncing '
    match_count = []
    total_tracks = len(rhythmbox_tracks)
    buckets = range(100, 0, -10)
    for count, track in enumerate(rhythmbox_tracks):
        if buckets and 100.0 * (count + 1) / float(total_tracks) >= buckets[-1]:
            print '|||{0}%'.format(buckets[-1])
            buckets.pop()
        if track['title'] is None or track['duration'] <= 0:
            continue
        node = track.pop('node')
        tree = track.pop('tree')
        playcount = track.pop('playcount')
        duration = track.pop('duration')

        for stats in last_fm_tracks:
            stats = stats.copy()
            last_fm_duration = stats.pop('duration')
            last_fm_playcount = stats.pop('playcount')
            if int(last_fm_playcount) > int(playcount):
                is_found = is_equal(track, stats, fuzzy=False)
                if not is_found and options.fuzzy:
                    a = track.copy()
                    b = stats.copy()
                    a['duration'] = duration
                    b['duration'] = last_fm_duration
                    is_found = is_equal(a, b, fuzzy=True)
                if not is_found:
                    a = track.copy()
                    b = stats.copy()
                    _ = a.pop('album')
                    _ = b.pop('album')
                    a['duration'] = duration
                    b['duration'] = last_fm_duration
                    is_found = is_equal(a, b, fuzzy=True)
                if not is_found:
                    a = track.copy()
                    b = stats.copy()
                    a['duration'] = duration
                    b['duration'] = last_fm_duration
                    _ = a.pop('artist')
                    _ = b.pop('artist')
                    is_found = is_equal(a, b, fuzzy=True)

                if is_found:
                    match_count += [stats]
                    children = node.getchildren()
                    playcount_element = None
                    for child in children:
                        if child.tag == 'play-count':
                            playcount_element = child
                            break
                    if playcount_element is None:
                        playcount_element = ET.SubElement(node, 'play-count')
                    playcount_element.text = str(last_fm_playcount)

    print 'Saving changes to rhythmbox db file ... ',
    if tree is not None:
        tree.write(RHYTHM_DB)
    print 'ok'

