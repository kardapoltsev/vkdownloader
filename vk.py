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

import argparse
import json, sys, os
from vkdownloader import VkDownloader

def process_music(args):
  if args.action == "load":
    vk.load(args.user, args.dest)
  elif args.action == "show":
    vk.show(args.user)
  elif args.action == "play": 
    vk.play(args.user)

def process_friends(args):
  if args.action == "show":
    vk.show_friends(args.user)

topParser = argparse.ArgumentParser()

topParser.add_argument("-u", "--user", help = "user id")
subParsers = topParser.add_subparsers(title = "Command categories")
music = subParsers.add_parser("music", description = "working with music")
friends = subParsers.add_parser("friends", description = "working with friends")

friends.add_argument("action", help = "friends actions", choices=["list"])
friends.set_defaults(func = process_friends)

music.add_argument("action", help = "music actions", choices=["list", "load", "play"])
music.add_argument("-d", "--dest", help = "destination directory for music download, default is current dir")
music.set_defaults(func = process_music)

try:
    import argcomplete
    argcomplete.autocomplete(topParser)
except ImportError:
    pass

args = topParser.parse_args()

vk = VkDownloader()

args.func(args)
