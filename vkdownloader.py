#!/usr/bin/env python3

# Copyright 2013 Alexey Kardapoltsev
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
 
import webbrowser
import pickle
import json
import urllib
from urllib import request
from html.parser import HTMLParser
from subprocess import call
import re
import os
import sys
import tempfile
from urllib import parse
from datetime import datetime, timedelta

# id of vk.com application, that has access to audio
APP_ID = '4065695'
# chars to exclude from filename
FORBIDDEN_CHARS = '/\\\?%*:|"<>!'
# vk.com api url
BASE_URL = "https://api.vkontakte.ru/method/"

class VkDownloader:

    def __init__(self):
        # get home dir
        if os.name != "posix":
            from win32com.shell import shellcon, shell
            self.homedir = shell.SHGetFolderPath(0, shellcon.CSIDL_APPDATA, 0, 0)
        else:
            self.homedir = os.path.expanduser("~")

        # file, where auth data is saved
        self.auth_file = os.path.join(self.homedir, '.vkrc')
        token, user_id = self.auth()
        self.access_token = token
        self.user_id = user_id
     
    def get_saved_auth_params(self):
        access_token = None
        user_id = None
        try:
            with open(self.auth_file, 'rb') as pkl_file:
                token = pickle.load(pkl_file)
                expires = pickle.load(pkl_file)
                uid = pickle.load(pkl_file)
            if datetime.now() < expires:
                access_token = token
                user_id = uid
        except IOError:
            pass
        return access_token, user_id
     
     
    def save_auth_params(self, access_token, expires_in, user_id):
        td = timedelta(seconds=int(expires_in))
        #if we got offline token expires_in will be 0, so set expires in 5 years
        if(int(expires_in) == 0):
            td = timedelta(days = 5*365)

        expires = datetime.now() + td
        with open(self.auth_file, 'wb') as output:
            pickle.dump(access_token, output)
            pickle.dump(expires, output)
            pickle.dump(user_id, output)
     
     
    def get_auth_params(self):
        auth_url = ("https://oauth.vk.com/authorize?client_id={app_id}"
            "&scope=audio,friends,offline&redirect_uri=http://oauth.vk.com/blank.html"
            "&display=page&response_type=token".format(app_id=APP_ID))
        webbrowser.open_new_tab(auth_url)
        redirected_url = input("Paste here url you where redirected:\n")
        aup = parse.parse_qs(redirected_url)
        aup['access_token'] = aup.pop(
            'https://oauth.vk.com/blank.html#access_token')
        self.save_auth_params(aup['access_token'][0], aup['expires_in'][0],
            aup['user_id'][0])
        return aup['access_token'][0], aup['user_id'][0]
     
     
    def get_tracks_metadata(self, user_id):
        url = "audio.get.json?uid={uid}".format(uid = user_id)
        return self._call_api(url)

     
    def get_track_full_name(self, t_data):
        return self._get_track_name(t_data) + ".mp3"


    def _get_track_name(self, t_data):
        html_parser = HTMLParser()
        full_name = "{0} - {1}".format(
            html_parser.unescape(t_data['artist'])[:50].strip(),
            html_parser.unescape(t_data['title'])[:50].strip(),
        )
        full_name = re.sub('[' + FORBIDDEN_CHARS + ']', "", full_name)
        full_name = re.sub(' +', ' ', full_name)
        return full_name


     
    def download_track(self, t_url, t_name):
        t_path = os.path.join(self.destination, t_name)
        if not os.path.exists(t_path):
            try:
                request.urlretrieve(t_url, t_path)
            except Exception as e:
                print("error downloading {}: {}".format(t_name, str(e)))
                pass

    def auth(self):
        access_token, current_user_id = self.get_saved_auth_params()

        if not access_token or not current_user_id:
            access_token, user_id = self.get_auth_params()
        return access_token, current_user_id

		
    def get_friends(self, user_id):
        url = "friends.get.json?fields=uid,first_name,last_name&uid={uid}".format(
                uid = user_id or self.user_id)
        return self._call_api(url)
      
    
    def show_friends(self, user_id):
      friends = self.get_friends(user_id)
      for f in friends:
        print("{} {} - {}".format(f['first_name'], f['last_name'], f['uid']))


    def show(self, user):
        access_token, current_user_id = self.auth()
        tracks = self.get_tracks_metadata(user)

        total = len(tracks)
        print("{} has {} tracks".format(user or self.user_id, total))
    
        for i, t in enumerate(tracks):
            print(self.get_track_full_name(t))


    def load(self, user, path, clean = False):
        access_token, current_user_id = self.auth()
        uid = user or self.user_id

        tracks = self.get_tracks_metadata(uid)

        dest = os.path.expanduser(path or ".")
        if dest and not os.path.exists(dest):
            os.makedirs(dest)

        self.destination = dest


        total = len(tracks)
        print("Found {} tracks for {}".format(total, uid))
    
        for i, t in enumerate(tracks):
            t_name = self.get_track_full_name(t)
            print("Downloading {} of {}: {}".format(i + 1, total, t_name))
            self.download_track(t['url'], t_name)

        if clean:
            self._clean(tracks, path)
            
        print("All music is up to date")
     

    def _clean(self, tracks, path):
        names = set(map((lambda t: self.get_track_full_name(t)), tracks))
        files = os.listdir(path)
        for f in files:
            if f not in names:
                print("Deleting {}".format(f))
                os.remove(os.path.join(path, f))
      


    def _create_playlist(self, tracks):
        playlist = []

        playlist.append('#EXTM3U')

        for t in tracks:
            playlist.append("#EXTINF: {},{}".format(t['duration'], self._get_track_name(t)))
            playlist.append(t['url'] + "\n")
        
        return playlist


    def save_playlist(self, playlist, filename):
        with open(filename, 'w') as f:
            for l in playlist:
                print(l, file=f)
        return filename


    def play(self, user_id):
        tracks = user_id or self.get_tracks_metadata(self.user_id)
        playlist = self._create_playlist(tracks)
        playlist_file = self.save_playlist(playlist, tempfile.mkstemp()[1])
        call(["mplayer", "-playlist", playlist_file])
        

    def _call_api(self, req):
        self.auth()
        #assume, that url has params, so add additional params after &
        url = BASE_URL + req + "&access_token={atoken}".format(atoken = self.access_token)
        try:
          response = request.urlopen(url)
          js = json.loads(response.read().decode("utf-8"))
          if 'error' in js:
            print("Error {}: {}".format(js["error"]["error_code"], js["error"]["error_msg"]))
            sys.exit(1)
          else:
            return js['response']
        except urllib.error.HTTPError as e:
          print("Network error `{} - {}`".format(e.code, e.msg))
          sys.exit(1)

# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4
