DEBUG = True
VIDEO_STREAM_URL = None

from os import path

if path.isfile("config_local.py"):
    exec(open("config_local.py").read())
