#lastrhythm


##Introduction
`lastrhythm` is a shell script that updates your the track playcount of your local rhythmbox music collection using your music listening history dataset from your Last.fm account.


##Dependencies
`lastrhythm` depends on `requests` and `python-Levenshtein` libraries which can be installed as follows:
```
pip install -r requirements.txt
```


##Running lastrhythm Script
The requirements are to have rhythmbox music player set up to manage your music collection and to have an existing Last.fm account. 

You can then run `lastrhythm` as follows:
```
python lastrhyhm.py -u lastfm_username
```
