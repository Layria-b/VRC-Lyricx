# VRC-lyricx

Hello! This is a program that takes what your playing on spotify and depending on if theres synced lyrics for the song it will display thoughs synced lyrics in the VRChat chatbox and the name of the song playing in your status!

**You NEED to turn on OSC in VRChat for the program to display the lyrics, You can turn on OSC in the Action Menu under Osc > Enabled.**

### Installation:
Download latest release, unzip<br />

**Note: You need a spotify application, Click [here](https://developer.spotify.com/documentation/web-api/concepts/apps) for how to make one.**<br />
**Make name/discription anything you like, Set the redirect uri to "http://localhost:7777/callback" without quotation marks**

### Configuring:
Go to info/config.ini and open it in notepad enter appropriate info: <br />
```
[SPOTIFY]
client_id =  Enter your spotify client ID.
client_secret =  Enter your spotify client secret.
redirect_uri =  Enter the redirect url for your spotify application.

[VRC]
username =  Enter your VRchat username.
password =  Enter your VRchat password.
statusFormat = Enter how you would like your status to look like.
```
**Note: Writing {song} in your status puts the song there, Status can only be 32 chara long so song may get cut short. You DO NOT have to include {song} in statusFormat.**
