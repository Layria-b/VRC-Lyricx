import vrchatapi
from vrchatapi.api import authentication_api
from vrchatapi.models.two_factor_email_code import TwoFactorEmailCode
from vrchatapi.models.two_factor_auth_code import TwoFactorAuthCode
from vrchatapi.exceptions import UnauthorizedException
from pythonosc import udp_client
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import requests
from http.cookiejar import LWPCookieJar
import threading
from threading import Event
from time import sleep 
from configparser import RawConfigParser
import win32gui
import ctypes

ctypes.windll.kernel32.SetConsoleTitleW("VRC-Lyricx")
config = RawConfigParser()
config.read("info/config.ini")
udpClient = udp_client.SimpleUDPClient("127.0.0.1", 9000)

VRCCookieFilename = "info/VRCCookies.txt"
SpotifyCookieFilename = "info/SpotifyCookies.cache"

client_id = config["SPOTIFY"]["client_id"]
client_secret = config["SPOTIFY"]["client_secret"]
redirect_uri = config["SPOTIFY"]["redirect_uri"]
scope = 'user-read-playback-state'

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope=scope,
    client_id=client_id,
    client_secret=client_secret,
    redirect_uri=redirect_uri,
    cache_path=SpotifyCookieFilename
    )
)

def ThreadMonitor():
    while not threading.main_thread().is_alive():
        closeThreads.set()
        break
    sleep(1)

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

def spotifyAndStatus(showLyrics):
    lastSpotifyWindowTitle = ""
    while True:
        if closeThreads.is_set():
            print("Closing lyrics thread.")
            break
        spotifyWindowTitle = win32gui.GetWindowText(hWnd)
        
        if (lastSpotifyWindowTitle in {"Spotify Free", "Spotify Premium"} and spotifyWindowTitle != lastSpotifyWindowTitle) or (showLyrics.is_set() and spotifyWindowTitle != lastSpotifyWindowTitle):
            showLyrics.clear()
        
        if spotifyWindowTitle != lastSpotifyWindowTitle: 
            lastSpotifyWindowTitle = spotifyWindowTitle

            SpotifyRequ = sp.current_user_playing_track()
            try: 
                if SpotifyRequ["is_playing"] == True:
                    track_name = SpotifyRequ['item']['name']
                    artists = [artist for artist in SpotifyRequ['item']['artists']]
                    artist_names = ', '.join([artist['name'] for artist in artists])
                    song = f'{track_name} by {artist_names}'
                    song = song.translate({ord(c): '`' for c in "\'\""})
                    
                    status_description = config['VRC']['statusFormat'].format(song = song)
                    status_description = (status_description[:29] + '...') if len(status_description) > 29 else status_description
                    
                    update_user_request = vrchatapi.UpdateUserRequest(
                    status_description=status_description
                    )
                    bio_request = user_api.update_user(current_user.id, update_user_request=update_user_request)
                    
                    songUrl = SpotifyRequ["item"]["external_urls"]["spotify"]
                    lastStartTimeMs = SpotifyRequ['progress_ms']
                    print("Starting lyrics thread")
                    sleep(3)
                    lyricsThread = threading.Thread(target=lyrics, args=(showLyrics, songUrl, lastStartTimeMs,))
                    lyricsThread.start()
            except TypeError:
                sleep(1)
                continue
        sleep(1)

def lyrics(showLyrics, songUrl:str, lastStartTimeMs:float):
    print("Lyrics thread started")
    showLyrics.set()
    lastStartTimeMs = (lastStartTimeMs/1000)+3.25
    requUrl = f"https://spotify-lyric-api.herokuapp.com/?url={songUrl}&autoplay=true"
    requ = requests.get(requUrl)
    requJson = requ.json()
    
    try:
        for lyric in range(len(requJson["lines"])):
            print(showLyrics.is_set())
            if not showLyrics.is_set():
                print("Stopping lyrics thread")
                print("Because song was paused")
                showLyrics.set()
                break
            elif closeThreads.is_set():
                print("Closing lyrics thread.")
                break


            StartTimeMs = (float(requJson["lines"][lyric]["startTimeMs"]))/1000
            if lastStartTimeMs>StartTimeMs:
                continue
            sleep(StartTimeMs-lastStartTimeMs)
            lastStartTimeMs = StartTimeMs

            print(requJson["lines"][lyric]["words"])
            udpClient.send_message("/chatbox/input", [requJson["lines"][lyric]["words"], True, False])
    except KeyError:
        print("No lyrics for current song.")
        udpClient.send_message("/chatbox/input", ["No lyrics for current song...", True, False])

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

hWnd = win32gui.FindWindowEx(None, None, None, 'Spotify Free')
while (hWnd == 0):
    input("Getting spotify's hWnd, Make sure spotify is open and not playing any songs, Press any key to continue...")
    hWnd = win32gui.FindWindowEx(None, None, None, 'Spotify Free')
print("Found spotify's hWnd.")

if __name__ == "__main__":
    showLyrics = Event()
    closeThreads = Event()

    threadMonitor = threading.Thread(target=ThreadMonitor)
    threadMonitor.start()
    
    spotifyThread = threading.Thread(target=spotifyAndStatus, args=(showLyrics,))
    print("Waiting for song to be played!")
    spotifyThread.start()

