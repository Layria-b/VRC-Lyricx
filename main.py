#look into instead of using the api useing spotifys window title, use window handle. looking for way to get window handle

import configparser
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import threading
from threading import Event
import time 
import requests
import os
from pythonosc import udp_client

config = configparser.ConfigParser()
config.read("info/details.ini")
udpClient = udp_client.SimpleUDPClient("127.0.0.1", 9000)

client_id = config["SPOTIFYAUTH"]["client_id"]
client_secret = config["SPOTIFYAUTH"]["client_secret"]
redirect_uri = config["SPOTIFYAUTH"]["redirect_uri"]
scope = 'user-read-playback-state'
os.environ["lastTrackName"] = ""

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope=scope,
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    cache_path="info/.cache")
)

def lyrics(event, songUrl:str, lastStartTimeMs:float):
    print("lyrics thread started")
    requUrl = f"https://spotify-lyric-api.herokuapp.com/?url={songUrl}&autoplay=true"
    requ = requests.get(requUrl)
    requJson = requ.json()
    lastStartTimeMs = lastStartTimeMs/1000
    event.clear() #event = False
    try:
        for lyric in range(len(requJson["lines"])):
            if event.is_set():
                print("Stopping lyrics thread")
                event.clear() #event = False
                print(event.is_set())
                break
            StartTimeMs = float(requJson["lines"][lyric]["startTimeMs"])/1000
            if lastStartTimeMs>StartTimeMs:
                continue
            time.sleep(StartTimeMs-lastStartTimeMs)
            lastStartTimeMs = StartTimeMs

            print(requJson["lines"][lyric]["words"]) #just used for testing replace with below 
            #udpClient.send_message("/chatbox/input", [requJson["lines"][lyric]["words"], True, False])
    except KeyError:
        print("No lyrics for current song.") #just used for testing replace with below 
        #udpClient.send_message("/chatbox/input", ["No lyrics for current song.", True, False])

def spotify(event, paused):
    while True:
        spotify_song_resp = sp.current_user_playing_track()
        try:
            if spotify_song_resp["is_playing"] == True and spotify_song_resp['item']['name'] != os.environ["lastTrackName"]:
                track_name = spotify_song_resp['item']['name']
                os.environ["lastTrackName"] = track_name
                artists = [artist for artist in spotify_song_resp['item']['artists']]
                artist_names = ', '.join([artist['name'] for artist in artists])
                song = f'{track_name} by {artist_names}'
                song = song.translate({ord(c): '`' for c in "\'\""})
                
                #
                 # vrc status request stuff here
                #
                
                songUrl = spotify_song_resp["item"]["external_urls"]["spotify"]
                lastStartTimeMs = spotify_song_resp['progress_ms']
                t2 = threading.Thread(target=lyrics, args=(event, songUrl, lastStartTimeMs,))
                t2.start()
            elif spotify_song_resp["is_playing"] == True and spotify_song_resp['item']['name'] == os.environ["lastTrackName"] and paused.is_set(): #paused is true?
                print('playing lyrics from paused song')
                paused.clear() #paused = False
                songUrl = spotify_song_resp["item"]["external_urls"]["spotify"]
                lastStartTimeMs = spotify_song_resp['progress_ms']
                t2 = threading.Thread(target=lyrics, args=(event, songUrl, lastStartTimeMs,))
                t2.start()
            elif spotify_song_resp["is_playing"] == False and spotify_song_resp['item']['name'] == os.environ["lastTrackName"]:
                paused.set() #paused = True
                print(event.is_set())
        except TypeError:
            time.sleep(1)
        time.sleep(1)

paused = Event()
event = Event()
t1 = threading.Thread(target=spotify, args=(event, paused,))
t1.start()
