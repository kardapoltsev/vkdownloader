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
import re
import os
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
        expires = datetime.now() + timedelta(seconds=int(expires_in))
        with open(self.auth_file, 'wb') as output:
            pickle.dump(access_token, output)
            pickle.dump(expires, output)
            pickle.dump(user_id, output)
     
     
    def get_auth_params(self):
        auth_url = ("https://oauth.vk.com/authorize?client_id={app_id}"
            "&scope=audio&redirect_uri=http://oauth.vk.com/blank.html"
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
        url = BASE_URL + "audio.get.json?uid={uid}&access_token={atoken}".format(
                uid = user_id, atoken = self.access_token)
        response = request.urlopen(url)
        audio_get_page = response.read().decode("utf-8")
        return json.loads(audio_get_page)['response']
     
     
    def get_track_full_name(self, t_data):
        html_parser = HTMLParser()
        full_name = "{0}_{1}".format(
            html_parser.unescape(t_data['artist'][:100]).strip(),
            html_parser.unescape(t_data['title'][:100]).strip(),
        )
        full_name = re.sub('[' + FORBIDDEN_CHARS + ']', "", full_name)
        full_name = re.sub(' +', ' ', full_name)
        return full_name + ".mp3"
     
     
    def download_track(self, t_url, t_name):
        t_path = os.path.join(self.destination, t_name)
        if not os.path.exists(t_path):
            request.urlretrieve(t_url, t_path)
    
    def auth(self):
        access_token, current_user_id = self.get_saved_auth_params()

        if not access_token or not current_user_id:
            access_token, user_id = self.get_auth_params()
        return access_token, current_user_id

		
    def get_friends(self, user_id):
        url = BASE_URL + "friends.get.json?fields=uid,first_name,last_name&uid={uid}&access_token={atoken}".format(
                uid = user_id or self.user_id, atoken = self.access_token)
        response = request.urlopen(url)
        audio_get_page = response.read().decode("utf-8")
        return json.loads(audio_get_page)['response']
      
    
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


    def load(self, user, path):
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
        print("All music is up to date")
     
