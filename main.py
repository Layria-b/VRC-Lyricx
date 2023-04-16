import vrchatapi
from vrchatapi.api import authentication_api
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.exceptions import UnauthorizedException
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from http.cookiejar import LWPCookieJar
import configparser
from spotipy.oauth2 import SpotifyOAuth
import threading
from threading import Event
import time 
import requests
import os
from pythonosc import udp_client

config = configparser.RawConfigParser()
config.read("info/details.ini")
udpClient = udp_client.SimpleUDPClient("127.0.0.1", 9000)

client_id = config["SPOTIFY"]["client_id"]
client_secret = config["SPOTIFY"]["client_secret"]
redirect_uri = config["SPOTIFY"]["redirect_uri"]
scope = 'user-read-playback-state'
os.environ["lastTrackName"] = ""
VRCCookieFilename = "info/VRCCookies.txt"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope=scope,
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    cache_path="info/.cache")
)

def save_cookies(filename: str):
    cookie_jar = LWPCookieJar(filename=filename)
    
    for cookie in api_client.rest_client.cookie_jar:
        cookie_jar.set_cookie(cookie)
        
    cookie_jar.save()
        
def load_cookies(filename: str):
    cookie_jar = LWPCookieJar(filename=filename)

    try:
        cookie_jar.load()
    except FileNotFoundError:
        cookie_jar.save()
        return
    
    for cookie in cookie_jar:
        api_client.rest_client.cookie_jar.set_cookie(cookie)

try: 
    with vrchatapi.ApiClient() as api_client:
        load_cookies(filename=VRCCookieFilename)
        
        auth_api = authentication_api.AuthenticationApi(api_client)
        current_user = auth_api.get_current_user()
        print("Found Valid Cookies!")
        print("logged in as", current_user.display_name, "! :3")
        user_api = vrchatapi.UsersApi(api_client)
except UnauthorizedException:

    print("No Cookie Found, Using username/password to login!")
    configuration = vrchatapi.Configuration(
    username = config["VRC"]["username"],
    password = config["VRC"]["password"]
    )

    with vrchatapi.ApiClient(configuration) as api_client:
        auth_api = authentication_api.AuthenticationApi(api_client)
        try:
            current_user = auth_api.get_current_user()
        except ValueError:
            auth_api.verify2_fa_email_code(two_factor_email_code=TwoFactorEmailCode(input("Enter the code sent to your email: ")))
            current_user = auth_api.get_current_user()
            user_api = vrchatapi.UsersApi(api_client)
        except UnauthorizedException as e:
            if UnauthorizedException.status == 200:
                auth_api.verify2_fa(two_factor_auth_code=TwoFactorAuthCode(input("Enter your 2fa code: ")))
                current_user = auth_api.get_current_user()
            else:
                print("Exception when calling API: %s\n", e)
        except vrchatapi.ApiException as e:
            print("Exception when calling API: %s\n", e)
    print("logged in as", current_user.display_name, "! :3")
    save_cookies(filename=VRCCookieFilename)


def lyrics(paused, songUrl:str, lastStartTimeMs:float):
    print("lyrics thread started")
    requUrl = f"https://spotify-lyric-api.herokuapp.com/?url={songUrl}&autoplay=true"
    requ = requests.get(requUrl)
    requJson = requ.json()
    lastStartTimeMs = lastStartTimeMs/1000
    paused.clear() #paused = False
    try:
        for lyric in range(len(requJson["lines"])):
            if paused.is_set():
                print("Stopping lyrics thread")
                print("Because song ended or was paused.")
                paused.clear() #paused = False
                print(paused.is_set())
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

def spotifyAndStatus(paused):
    while True:
        spotify_song_resp = sp.current_user_playing_track()
        try:
            if spotify_song_resp["is_playing"] == True and spotify_song_resp['item']['name'] != os.environ["lastTrackName"]:
                paused.set() #paused = True (even though its not paused idk it works i think)
                track_name = spotify_song_resp['item']['name']
                os.environ["lastTrackName"] = track_name
                artists = [artist for artist in spotify_song_resp['item']['artists']]
                artist_names = ', '.join([artist['name'] for artist in artists])
                song = f'{track_name} by {artist_names}'
                song = song.translate({ord(c): '`' for c in "\'\""})
                
                status_description = config['VRC']['statusFormat'].format(song = song)
                if len(status_description) > 28:
                    shorten_by_status = len(status_description[:-28])
                    status_description = f"{status_description[:-shorten_by_status]}..."
                
                update_user_request = vrchatapi.UpdateUserRequest(
                status_description=status_description
                )
                bio_request = user_api.update_user(current_user.id, update_user_request=update_user_request)
                
                songUrl = spotify_song_resp["item"]["external_urls"]["spotify"]
                lastStartTimeMs = spotify_song_resp['progress_ms']
                t2 = threading.Thread(target=lyrics, args=(paused, songUrl, lastStartTimeMs,))
                t2.start()
            
            elif spotify_song_resp["is_playing"] == True and spotify_song_resp['item']['name'] == os.environ["lastTrackName"] and paused.is_set(): #paused is true?
                print('playing lyrics from paused song')
                paused.clear() #paused = False
                songUrl = spotify_song_resp["item"]["external_urls"]["spotify"]
                lastStartTimeMs = spotify_song_resp['progress_ms']
                t2 = threading.Thread(target=lyrics, args=(paused, songUrl, lastStartTimeMs,))
                t2.start()
            elif spotify_song_resp["is_playing"] == False and spotify_song_resp['item']['name'] == os.environ["lastTrackName"]:
                paused.set() #paused = True
        except TypeError:
            time.sleep(1)
        time.sleep(1)

paused = Event()
t1 = threading.Thread(target=spotifyAndStatus, args=(paused,))
print("Waiting for song to be played!")
t1.start()
