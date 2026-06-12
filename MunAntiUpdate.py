#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
from importlib.resources import contents
import re, random;
import sys, time;
import json, base64
from urllib.parse import unquote, quote, urlencode
from mybrowser import Rqbrowser
import os, hashlib, cloudscraper
import munantiapi
import functools
import pathlib
import shutil
import requests
from tqdm.auto import tqdm
import zipfile, subprocess
from sys import platform
class MunAntiUpdate:
    """ MunAntiUpdate
    """
    def __init__(self):
        self.mun_api = munantiapi.MunAntiApi()
    def check_update_version(self):
        result = self.mun_api.check_version_for_update()
        THIS_FOLDER = os.getcwd();
        f = open(THIS_FOLDER+'/version.txt','r')
        version = f.read().strip()
        if version != result['version']:
            print('==link update', result['update_url'])
            return result['update_url']
    def download_file(self, url):
        local_filename = url.split('/')[-1]

        r = requests.get(url, stream=True, allow_redirects=True)
        if r.status_code != 200:
            r.raise_for_status()  # Will only raise for 4xx codes, so...
            raise RuntimeError(f"Request to {url} returned status code {r.status_code}")
        file_size = int(r.headers.get('Content-Length', 0))

        path = pathlib.Path(local_filename).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        desc = "(Unknown total file size)" if file_size == 0 else ""
        r.raw.read = functools.partial(r.raw.read, decode_content=True)  # Decompress if needed
        with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc) as r_raw:
            with path.open("wb") as f:
                shutil.copyfileobj(r_raw, f)
        return path   
        
def main():
    if getattr(sys, 'frozen', False):
        appFolderPath = os.path.dirname(os.path.realpath(sys.executable))
    elif __file__:
        appFolderPath = os.path.dirname(__file__)
    mun_anti = MunAntiUpdate()
    link_update = mun_anti.check_update_version()
    if link_update:
        print('==Trying update==')
        path_file = mun_anti.download_file(link_update)
        if str(path_file)[len(str(path_file))-3:] == 'zip':
            with zipfile.ZipFile(path_file, 'r') as zip_ref:
                zip_ref.extractall(appFolderPath)
            os.remove(path_file)    
    print(appFolderPath+"/MunAnti.exe")
    if platform == "linux" or platform == "linux2":
        # linux
        subprocess.run(['open',appFolderPath+"/MunAnti.exe"],check=True) 
    elif platform == "darwin":
        # OS X
        subprocess.run([appFolderPath+"/MunAnti.exe"],check=True) 
    else:       
        subprocess.Popen([appFolderPath+"/MunAnti.exe"], stdout=None, stderr=None, stdin=None, close_fds=True)
        # subprocess.run([appFolderPath+"/MunAnti.exe"],check=True) 
    print('==done==')
    
if __name__ == "__main__":
    sys.exit(main())
