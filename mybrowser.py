#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- coding: latin-1 -*-
# from asyncio import subprocess
from operator import le
import re, random, socket
from turtle import xcor
# import ClientForm;
import urllib
from io import StringIO ## for Python 3
import json
import requests
import time
import mechanize, socks,certifi
import http.cookiejar as cookielib
from bs4 import BeautifulSoup, SoupStrainer;
from urllib3.util import connection
import os, dns.resolver
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service as ChromiumService
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.support.select import Select
import time, random, httpagentparser
# from user_agents import parse
from collections import OrderedDict
import cloudscraper, hashlib
from urllib.parse import unquote, quote, urlencode
from threading import Thread
from sys import platform
import math
import undetected_chromedriver as uc
from selenium_stealth import stealth
import munproxy, multiprocessing
from functools import reduce
import tempfile, pickle
from selenium.webdriver.support.ui import WebDriverWait
from PyQt5 import QtCore, QtWidgets

class PutRequest(mechanize.Request):
  def get_method(self):
    return 'PUT'
class Mechanizebrowser:
    def __getattr__(self, name):
        return getattr(self.browser, name)

    def __init__(self, cookiePath=None, headermobile=False,header='',add_cookies={}):
        self.header = header
        self.browser = mechanize.Browser()


        self.cookie = mechanize.MozillaCookieJar()
        self.cookie.clear_session_cookies()
        self.cookie.clear()

        self.browser.set_cookiejar(self.cookie)
        self.browser.set_handle_robots(False)
        # self.browser.set_handle_equiv(True)
        # self.browser.set_handle_gzip(True)

        self.browser.set_handle_redirect(True)
        self.browser.set_handle_referer(True)
        # self.browser.set_debug_http(True)
        self.browser.set_debug_redirects(True)
        self.browser.set_handle_refresh(False)
        listheader_open = open('headerpc.txt').read()
        listheader_win = listheader_open.split('\n')
        listheader_mobile = [
            'Mozilla/5.0 (BlackBerry; U; BlackBerry 9900; en-US) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.1.0.346 Mobile Safari/534.11+',
            'Mozilla/5.0 (BlackBerry; U; BlackBerry 9860; en-US) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.0.0.254 Mobile Safari/534.11+',
            'Mozilla/5.0 (iPad; U; CPU OS 4_3_1 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8G4 Safari/6533.18.5',
            'Mozilla/5.0 (iPad; U; CPU OS 4_3 like Mac OS X; en-US) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8F191 Safari/6533.18.5',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A405 Safari/7534.48.3',
            'Mozilla/5.0 (iPod; U; CPU iPhone OS 4_3_3 like Mac OS X; en-us) AppleWebKit/533.17.9 (KHTML, like Gecko) Version/5.0.2 Mobile/8J2 Safari/6533.18.5',
            'Mozilla/5.0 (iPhone; CPU iPhone OS 5_0_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9A405 Safari/7534.48.3',
            'Mozilla/5.0 (iPad; CPU OS 6_1_3 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10B329 Safari/8536.25',
            'Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A403 Safari/8536.25',
        ]
        # header = listheader[]
        # ua = mechanize.UserAgent()
        # ua.set_seekable_responses(False)
        # ua.set_handle_equiv(False)
        # self.header = ''
        extra_info = str(random.randint(99999, 9999999))
        while not self.header:
            if not headermobile:
                self.header = listheader_win[random.randint(0, len(listheader_win) - 1)].strip()+'/'+extra_info
            else:
                self.header = listheader_mobile[random.randint(0, len(listheader_mobile) - 1)].strip()+'/'+extra_info
        print(self.header)
        self.tt = {'User-Agent': self.header,
                   'Accept-Encoding': 'gzip, deflate, br',
                   'Connection': 'keep-alive',
                   'Accept-Language': 'en-US',
                   'Cache-Control': 'max-age=0',
                   'Upgrade-Insecure-Requests': '1',
                   'Referer': '',
                   'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.5,/;q=0.5'};
        self.sock5 = False
        self.proxy = False

        self.link_host = ''
        self.link_origin = ''
    def set_handle_redirect(self,value=True):
        self.browser.set_handle_redirect(value)
        return
    def set_proxies(self, sock5='', proxy=''):
        self.sock5 = sock5
        self.proxy = proxy
        return True

    def selectForm(self):
        forms_post = self.browser.forms()
        return forms_post

    def set_cookies(self,cookies_dict={},cookies_list=[]):
        if cookies_dict:
            self.cookie.set_cookie(cookielib.Cookie(version = 0, name = cookies_dict['name'], value = cookies_dict['value'], port = '80', port_specified = False, domain = cookies_dict['domain'], domain_specified = True, domain_initial_dot = False, path = cookies_dict['path'], path_specified = True, secure = cookies_dict['secure'], expires = cookies_dict['expiry'], discard = False, comment = None, comment_url = None, rest = None, rfc2109 = False))
        elif cookies_list:
            for cookies_dict in cookies_list:
                self.cookie.set_cookie(cookielib.Cookie(version = 0, name = cookies_dict['name'], value = cookies_dict['value'], port = '80', port_specified = False, domain = cookies_dict['domain'], domain_specified = True, domain_initial_dot = False, path = cookies_dict['path'], path_specified = True, secure = cookies_dict['secure'], expires = cookies_dict['expiry'], discard = False, comment = None, comment_url = None, rest = None, rfc2109 = False))
    def load_cookies(self,cookies_file):
        self.cookie.load(cookies_file)
    def save_cookies(self,cookies_file):
        self.cookie.save(cookies_file)
    def add_header(self, link_refer='', XMLHttpRequest=False, extraHeader={}):
        self.tt = {
        'User-Agent': self.header,
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Accept-Language': 'en-US',
        'Host': self.link_host,
        'Origin': self.link_origin,
        'Cache-Control': 'max-age=0',
        'Referer': link_refer,
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.5,/;q=0.5'
        };
        if XMLHttpRequest:
            self.tt['X-Requested-With']='XMLHttpRequest'
        if extraHeader:
            self.tt = dict(self.tt.items() + extraHeader.items())

    def open(self, url, data='',put_data='',json_data='', timeout=10):
        headerList = []
        for h, v in self.tt.items():
            headerList.append((h, v))
        self.browser.addheaders = headerList;

        if self.sock5:
            socksip = self.sock5.split(':')[0].strip()
            socksport = self.sock5.split(':')[1].strip()
            socket.setdefaulttimeout(timeout)
            socks.setdefaultproxy(socks.SOCKS5, socksip, int(socksport), True)
            socket.socket = socks.socksocket
            # self.browser.add_handler(SocksiPyHandler(socks.SOCKS5, socksip, int(socksport),True))
        elif self.proxy:
            self.browser.set_proxies({'http': self.proxy, 'https': self.proxy})

        def getaddrinfo(*args):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, '', (args[0], args[1]))]

        socket.getaddrinfo = getaddrinfo
        self.browser.set_cookiejar(self.cookie)
        if data:
            r = self.browser.open(url, data, timeout=timeout)
        elif put_data:
            print (put_data)

            r = self.browser.open(PutRequest(url,
                data=json.dumps(put_data),headers={'Content-Type': 'application/json'}),timeout=timeout)
        elif json_data:
            r = self.browser.open(mechanize.Request(url,
                data=json.dumps(json_data),headers={'Content-Type': 'application/json'}),timeout=timeout)
        else:
            r = self.browser.open(url, timeout=timeout)
        return r;
    def close(self):
        self.cookie.clear_session_cookies()
        self.cookie.clear()
        self.browser.close()
        del self.browser
        del self.cookie

    def follow_link(self, url_regex='', text_regex='', nr=0):
        if url_regex:
            r = self.browser.follow_link(url_regex=url_regex, text_regex=text_regex, nr=nr)
        if text_regex:
            r = self.browser.follow_link(text_regex=text_regex, nr=nr)
        return r

class Rqbrowser:
    """ Test reg forum
    """

    def __init__(self,agent='',agent_mobile=False, SECRET_KEY='', token=''):
        ##Agent

        THIS_FOLDER = os.getcwd();
        # my_file = os.path.join(THIS_FOLDER, 'headerpc.txt')
        comboBoxDevicesList = ['Desktop', 'Phone']
        comboBoxOSList = ['Window', 'Mac OS X', 'Linux', 'ChromeOS']
        list_chrome_version = ["109.0.5414.75","109.0.0.0","107.0.0.0","107.0.5304.88","107.0.5304.66", "106.0.5249.91","105.0.5195.125","105.0.0.0","105.0.5195.136","104.0.5112.79","104.0.0.0"]
        comboBoxDevices = comboBoxDevicesList[random.randint(0, len(comboBoxDevicesList)-1)]
        comboBoxOS = comboBoxOSList[random.randint(0, len(comboBoxOSList)-1)]
        Agentversion = list_chrome_version[random.randint(0, len(list_chrome_version)-1)]
        comboBoxPhoneOSList = ['iPhone', 'Android']
        comboBoxPhoneOS = comboBoxPhoneOSList[random.randint(0, len(comboBoxPhoneOSList)-1)]
        list_apple_ios = ['16_1','15_7','14_8', '13_7']
        list_android_os = ['9', '10', '11', '12', '13']
        list_android_resolution = {'Samsung Galaxy Z Flip 4':{'resolution':'412 x 1004','scale':'3', 'model':'SM-F721B'},'Samsung Galaxy S9+': {'resolution':'360 x 740','scale':'3', 'model':'SM-G965F'}, 'Samsung Galaxy S9': {'resolution':'360 x 740','scale':'3', 'model':'SM-G960U'}, 'Samsung Galaxy S8+': {'resolution':'360 x 740','scale':'3' , 'model':'SM-G955F'}, 'Samsung Galaxy S8': {'resolution':'360 x 740','scale':'3', 'model':'SM-G950F'}, 'Nexus 6P': {'resolution':'412 x 732','scale':'3', 'model':'Nexus 6P'}, 'Nexus 5X': {'resolution':'412 x 732','scale':'3', 'model':'Nexus 5X'}, 'Google Pixel 4 XL': {'resolution':'412 x 869','scale':'3', 'model': 'Pixel 4 XL'}, 'Google Pixel 4': {'resolution':'412 x 869','scale':'3', 'model': 'Pixel 4'} }
        listAndroidOS = list(list_android_resolution.keys())
        listAndroid = listAndroidOS[random.randint(0, len(listAndroidOS)-1)]
        print(comboBoxDevices, listAndroid)
        if comboBoxDevices == 'Desktop':
            AgentOperationOS = ''
            if comboBoxOS == 'Window':
                AgentOperationOS = 'Windows NT 10.0; Win64; x64'
            elif comboBoxOS == 'Mac OS X':
                os_version = list_apple_ios[random.randint(0, len(list_apple_ios)-1)]
                AgentOperationOS = 'Macintosh; Intel Mac OS X '+ os_version
            elif comboBoxOS == 'Linux':
                AgentOperationOS = 'X11; Linux x86_64'
            else:
                AgentOperationOS = "X11; CrOS x86_64 14909.100.0"
            self.agent = "Mozilla/5.0 (%s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36" % (AgentOperationOS, Agentversion)
        else:
            if comboBoxPhoneOS.lower().find('iphone') != -1:
                os_version = list_apple_ios[random.randint(0, len(list_apple_ios)-1)]
                self.agent = "Mozilla/5.0 (iPhone; CPU iPhone OS %s like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/%s Mobile/15E148 Safari/604.1" % (os_version, Agentversion)
            else:
                os_version = list_android_os[random.randint(0, len(list_android_os)-1)]
                self.agent = "Mozilla/5.0 (Linux; Android %s; %s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Mobile Safari/537.36 TwitterAndroid" % (os_version, list_android_resolution[listAndroid]['model'], Agentversion)
        print(self.agent)    
        # self.agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36' % ()
        self.SECRET_KEY = SECRET_KEY
        self.token = token
        ##cookies
        self.all_cookies = {}
        self.cookies_jar = {}#requests.cookies.RequestsCookieJar()
        
        self.browser = requests.session()
        # self.browser = cloudscraper.create_scraper(self.browser)
        # self.browser = RoboBrowser(session=self.session,timeout=15,history=True,parser='lxml')
        # self.browser.cookies = self.cookies_jar

        self.sock5 = False
        self.proxy = False
        self.proxies = ''
        self.link_host = ''
        self.link_origin = ''

        self.header = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'user-Agent': self.agent,
                    'connection': 'keep-alive',
                    'accept-Language': 'en-US',
                    'cache-Control': 'no-cache',
                    "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site"
                   };
    def add_signature(self,url, params={}, play_load=False):
        if len(params.keys()) == 0:
            params = url
        elif len(params.keys()) > 0 and play_load:
            params = str(json.dumps(params))
        else:
            params = urlencode(params)  # case 1
               
        correct_signature = hashlib.md5(str(self.SECRET_KEY + params).encode('utf-8')).hexdigest()
        self.header.update({'signature-Authorization':correct_signature,'Referer':url})

        self.browser.headers = OrderedDict(self.header)
        return correct_signature
    def add_token(self, token):

        self.header.update({'authorization':'Token '+token})
        self.browser.headers = OrderedDict(self.header)
    # self.cookie = cookielib.MozillaCookieJar()
    def load_cookies(self,cookies_file):

        self.cookies_jar.load(cookies_file)
        # Load existing cookies (file might not yet exist)
        self.browser.cookies = self.cookies_jar
    def stringify(self, obj: dict) -> dict:
        """turn every value in the dictionary to a string"""
        for k, v in obj.items():
            if isinstance(v, dict):
                # if value is a dictionary, stringifiy recursively
                self.stringify(v)
                continue
            if not isinstance(v, str):
                if isinstance(v, bool):
                    # False/True -> false/true
                    obj[k] = str(v).lower()
                else:
                    obj[k] = str(v)
        return obj
    def add_cookies(self, cookies_json={}):
        # requests.utils.add_dict_to_cookiejar(self.cookies_jar, self.stringify(cookies_json))
        self.cookies_jar.update(cookies_json)
        
    def save_cookies(self,cookies_file):
      
        self.cookies_jar.save(cookies_file)
        
    def get_cookies(self):
        return self.browser.cookies.get_dict()
    
    def add_header(self, link_refer='', XMLHttpRequest=None, extraHeader={}):
        self.header = {
                    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
                    'user-Agent': self.agent,
                    'connection': 'keep-alive',
                    'accept-Language': 'en-US',
                    'cache-Control': 'no-cache',
                    "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site"
                   };
        if self.agent:
            self.header.update({'user-agent': self.agent})
        if link_refer:
            self.header.update({'Referer':link_refer})
        # if self.link_host:
        #     self.header.update({'Host':self.link_host})
        # if self.link_origin:
        #     self.header.update({'Origin': self.link_origin})
        if extraHeader:
            self.header.update(extraHeader)
        if XMLHttpRequest:
            self.header.update({'x-requested-With': 'XMLHttpRequest'})
    def add_cookies_to_header(self):
        self.header['cookie'] = "; ".join(
            [str(x)+"="+str(y) for x, y in OrderedDict(self.cookies_jar).items()])
        return self.header['cookie'] 
    def set_proxies(self, sock5='', proxy=''):
        if len(sock5) >= 3:
            self.sock5 = sock5
        elif len(proxy) >= 3:
            self.proxy = proxy

        # _orig_create_connection = connection.create_connection
        #
        # # my_resolver.nameservers = ['8.8.8.8']
        # def myResolver(host):
        #     r = dns.resolver.Resolver()
        #     r.nameservers = ['8.8.8.8']
        #     answers = r.query(host, 'A')
        #     for rdata in answers:
        #         return str(rdata)
        #
        # # myResolver('24.14.49.175','24.14.49.175')
        # def patched_create_connection(address, *args, **kwargs):
        #     """Wrap urllib3's create_connection to resolve the name elsewhere"""
        #     # resolve hostname to an ip address; use your own
        #     # resolver here, as otherwise the system resolver will be used.
        #     host, port = address
        #     hostname = myResolver(host)
        #
        #     return _orig_create_connection((hostname, port), *args, **kwargs)
        #
        # connection.create_connection = patched_create_connection

    def open(self, url, data='',put_data='', json_data='',params='', agent='', timeout=60, allow_redirects=True,add_cookies={}, method=''):

        if self.sock5:
            self.proxies = f'socks5h://{self.sock5}'#dict({'http': 'socks5://' + self.sock5, 'https': 'socks5://' + self.sock5})
        elif self.proxy:
            self.proxies = f'{self.sock5}' #dict({'http': self.proxy, 'https': self.proxy})

        if self.token:
            self.add_token(self.token)
        if self.header:
            self.browser.headers = OrderedDict(self.header)
        if self.proxies:
            print('===set proxies===',self.proxies)
            self.browser.proxies['http'] = self.proxies
            self.browser.proxies['https'] = self.proxies
        if add_cookies:
            self.all_cookies.update(add_cookies)
        if data:
            if self.SECRET_KEY:
                self.add_signature(url,params=data)
            self.result = self.browser.post(url, data=data, timeout=timeout,allow_redirects=allow_redirects, cookies=self.cookies_jar, headers=self.header)
        elif json_data:
            if self.SECRET_KEY:
                self.add_signature(url,params=json_data, play_load=True)
            self.result = self.browser.post(url, json=json_data, timeout=timeout, allow_redirects=allow_redirects, cookies=self.cookies_jar, headers=self.header)
        elif put_data:
            if self.SECRET_KEY:
                self.add_signature(url,params=put_data, play_load=True)
            self.result = self.browser.put(url, json=put_data, timeout=timeout,
                                           allow_redirects=allow_redirects, cookies=self.cookies_jar, headers=self.header)
        else:
            if self.SECRET_KEY:
                self.add_signature(url)
            self.result = self.browser.get(
                url, allow_redirects=allow_redirects, timeout=timeout, cookies=self.cookies_jar, headers=self.header)
        # print(requests.utils.dict_from_cookiejar(self.browser.cookies))
        self.cookies_jar.update(self.browser.cookies.get_dict())
        # print(self.cookies_jar)

        # print(self.header)
        return self.result

    def close(self):
        del self.browser
    def read(self):
        return
    def get_url(self):
        return
    def fixHTML(self, html):
        return html.replace("'", '"');

    def selectForm(self, html,nr=0):
        forms_post = None
        # print(html)
        soup = BeautifulSoup(html,features="html5lib")
        forms = soup.find_all('form')
        if nr:
            forms = forms[nr]
        return forms
    def getInputForm(self, form):
        data = {e.attrs.get("name"): e.attrs.get("value") for e in form.find_all("input")}
        return data
    def getActionUrl(self,form):
        c_form_submit = form.attrs["action"]
        return c_form_submit

class ChromeWithPrefs(uc.Chrome):
    def __init__(self, *args, options=None, **kwargs):
        if options:
            self._handle_prefs(options)

        super().__init__(*args, options=options, **kwargs)

        # remove the user_data_dir when quitting
        self.keep_user_data_dir = True

    @staticmethod
    def _handle_prefs(options):
        print('=user_data_dir',options.user_data_dir)
        if prefs := options.experimental_options.get("prefs"):
            # turn a (dotted key, value) into a proper nested dict
            def undot_key(key, value):
                if "." in key:
                    key, rest = key.split(".", 1)
                    value = undot_key(rest, value)
                return {key: value}

            # undot prefs dict keys
            undot_prefs = reduce(
                lambda d1, d2: {**d1, **d2},  # merge dicts
                (undot_key(key, value) for key, value in prefs.items()),
            )
            if options.user_data_dir:
              default_dir = os.path.join(options.user_data_dir , "Default")
            else:
              # create an user_data_dir and add its path to the options
              user_data_dir = os.path.normpath(tempfile.mkdtemp())
              options.add_argument(f"--user-data-dir={user_data_dir}")

              # create the preferences json file in its default directory
              default_dir = os.path.join(user_data_dir, "Default")
            os.mkdir(default_dir)
            print('====mkdir')
            prefs_file = os.path.join(default_dir, "Preferences")
            with open(prefs_file, encoding="latin1", mode="w") as f:
                json.dump(undot_prefs, f)

            # pylint: disable=protected-access
            # remove the experimental_options to avoid an error
            del options._experimental_options["prefs"]

class MunAntiBrowser:
    """
        Test reg forum

    """

    def __init__(self, statusqueue=None, captchaQueQue=None):
        ##Agent
        self.window_handles = []
        self.window_execute_cdp_cmd = {}
        self.statusqueue = statusqueue
        self.captchaQueQue = captchaQueQue
        self.browser_ip = {}
    
    def get_captcha(self, id):
      while 1:
        data = self.captchaQueQue.get()
        data_info = json.loads(data)
        if id in data_info:
          return data[id]
        else:
          self.captchaQueQue.put(data)
          time.sleep(0.5)
          
    def request_captcha(self):
      print('==request input captcha==')
      if self.statusqueue:
        self.statusqueue.put(('input_captcha', json.dumps({'id':self.profileInfo['id']})))

        
    def get_geo_ip(self, socks5='', proxy=''):
        print('self.profile_socks5_details==',self.profile_socks5_details)
        print('self.profile_proxy_details==', self.profile_proxy_details)
        requestBrowser = Rqbrowser()
        i=0
        while i < 4:
          try:
            requestBrowser.set_proxies(sock5=socks5,proxy=proxy)
            r = requestBrowser.open('http://ip-api.com/json')
            result = r.json()
            self.browser_ip = result['query']
          except:
            self.set_time_zone = {}
            self.Map_coordinates = {}
            time.sleep(1)
          else:
            # print(result)
            timezone = result['timezone']
            lat = result['lat']
            lon = result['lon']
            print(timezone,lat, lon)
            # timezone = 'America/New_York'
            self.set_time_zone= dict({
            'timezoneId':timezone
            })                   
                              
            self.Map_coordinates = dict({
                "latitude": lat,
                "longitude":lon,
                "accuracy": 100
                })
            return timezone
          i+=1
          
    def clear_cookies(self):
        self.driver.delete_all_cookies()
        
    def setting(self,inject_str={}, profileInfo={}, onetime=False, type_browser='Chrome', head_less=False, disable_images=False, fake_finger=True, pageLoad=True, positionW=0, positionH=0):
        THIS_FOLDER = os.getcwd();
        self.seleniumwire_options = {'verify_ssl': True}
        self.profileInfo = profileInfo
        self.inject_str = inject_str
        
        self.inject_driver = '''
          document.addEventListener('DOMContentLoaded', function() {
            let objectToInspect = window,
                result = [];
            while(objectToInspect !== null) 
            { result = result.concat(Object.getOwnPropertyNames(objectToInspect));
              objectToInspect = Object.getPrototypeOf(objectToInspect); }
            result.forEach(p => p.match(/.+_.+_(Array|Promise|Symbol)/ig)
                                &&delete window[p]&&console.log('removed',p))
          });     

          (function fakeWebdriver() {
            Object.defineProperty(navigator, 'webdriver', {   value: undefined,   configurable: true });
          })();
        '''
        self.profile_user_agent = profileInfo['profile_user_agent']
        self.profile_os = profileInfo['profile_os']
        self.profile_resolution = profileInfo['profile_resolution']
        self.profile_cpu = profileInfo['profile_cpu']
        self.profile_time_zone = profileInfo['profile_time_zone']
        self.start_url = profileInfo['profile_start_url']
        self.profile_proxy_details = profileInfo['profile_proxy_details']
        self.profile_socks5_details = profileInfo['profile_socks5_details']
        if self.profile_user_agent:
            # print(self.inject_str)
            self.inject_driver += self.inject_str['UserAgent'].replace('{{UserAgent}}', self.profile_user_agent)
        if self.profile_resolution:
            split_str = self.profile_resolution.strip().split('x')
            print('self.profile_resolution',self.profile_resolution)
            self.screen_width = split_str[0]
            self.screen_height = split_str[1]
            # self.inject_driver += self.inject_str['resolution'].replace('{{screen_width}}', self.screen_width).replace('{{screen_height}}', self.screen_height)
          
        if profileInfo['profile_webrtc']:
            self.inject_driver += self.inject_str['webrtc']
        if profileInfo['profile_canvas']:
            self.inject_driver += self.inject_str['canvas'].replace('{{canvas_shift}}', str(profileInfo['profile_canvas']))
        if profileInfo['profile_audio']:
            audio_str = self.inject_str['audio']
            profileInfoAudio = json.loads(profileInfo['profile_audio'])
            for key in profileInfoAudio.keys():
                audio_str = audio_str.replace('{{'+key+'}}', str(profileInfoAudio[key]))
            self.inject_driver+=audio_str  
        if profileInfo['profile_webgl']:
            webgl_str = self.inject_str['webgl']
            profileInfoWebgl = json.loads(profileInfo['profile_webgl'])
            for key in profileInfoWebgl.keys():
                webgl_str = webgl_str.replace('{{'+key+'}}', str(profileInfoWebgl[key]))      
            self.inject_driver+=webgl_str
        if profileInfo['profile_rects']:
            # print('==========profile_rects', profileInfo['profile_rects'])
            if profileInfo['profile_rects'] == 'Noise':
                
                rects_value = round(random.uniform(0.2, 0.35), 5)
                # print('==========profile_rects', rects_value)
            else:
                rects_value = profileInfo['profile_rects']
            self.inject_driver+=self.inject_str['rects'].replace('{{rects}}', str(rects_value))
            
        if profileInfo['profile_font']:
            self.inject_driver+=self.inject_str['fonts'].replace('{{fonts}}', profileInfo['profile_font'])    
        self.inject_driver+=self.inject_str['network']
        self.inject_driver+=self.inject_str['battery'] 
        if profileInfo['profile_name']:
          self.inject_driver+=self.html_inject(profileInfo['profile_name'])
        if type_browser == 'Chrome':
            if profileInfo['profile_name']:
                chrome_data_path = os.path.join(THIS_FOLDER, 'chrome data/'+profileInfo['profile_name']+str(profileInfo['id']))

            # chrome_driver_path = os.path.join(THIS_FOLDER, 'chrome/macos/chromedriver')
    
            if platform == "linux" or platform == "linux2":
                # linux
                chrome_binary_path = os.path.join(THIS_FOLDER, 'chrome/macos/Chrome.app/Contents/MacOS/Google Chrome')
            elif platform == "darwin":
                # OS X
                chrome_binary_path = os.path.join(THIS_FOLDER, 'chrome/macos/Chrome.app/Contents/MacOS/Google Chrome')
            else:       
                chrome_binary_path = os.path.join(THIS_FOLDER, 'chrome/win/Chrome/Application/chrome.exe')
                
            if platform == "linux" or platform == "linux2":
                # linux
                chrome_driver_path = os.path.join(THIS_FOLDER, 'chrome/macos/Chrome.app/Contents/MacOS/Google Chrome')
            elif platform == "darwin":
                # OS X
                chrome_driver_path = os.path.join(THIS_FOLDER, 'chrome/macos/chromedriver')
            else:       
                chrome_driver_path = os.path.join(THIS_FOLDER, 'chrome/win/chromedriver.exe')     
             
            self.phoneSetting = False
            flatform = 'Win32'
            if self.profile_os == 'Window':
                flatform = 'Win32'
            elif self.profile_os == 'Mac OS X':
                flatform = 'MacIntel'
            elif self.profile_os == 'Linux':
                flatform = 'Linux x86_64'
            elif self.profile_os == 'Chrome OS':
                flatform = 'CrOS X86_64'
            elif self.profile_os.lower().find('iphone') != -1:
                flatform = 'iPhone'
                self.phoneSetting = True
            else:
                flatform = 'Android'
                self.phoneSetting = True
            # print('xxxxx', self.profile_os.lower(), flatform)  
            self.options = uc.ChromeOptions()
            # if self.profile_user_agent:
            #     self.options.add_argument(f'--user-agent={self.profile_user_agent}')
            self.options.add_argument("--window-size=%s,%s" % (int(self.screen_width)+10, int(self.screen_height)+100))  
            self.options.add_argument('--window-position=%s, %s' % (positionW,positionH))
            # self.options.add_argument(f"--window-size={screen_width},{screen_height}")
            #chrome_options.add_argument('--remote-debugging-port=9222')
            self.options.binary_location = chrome_binary_path
            if profileInfo['profile_name']:
                print('==chrome_data_path', chrome_data_path)
                # self.options.user_data_dir = chrome_data_path
                
                self.options.add_argument('--user-data-dir='+chrome_data_path)    
            if head_less:
                self.options.headless = True
            self.options.add_argument('--disable-infobars')    
            self.options.add_argument('--disable-plugins-discovery')
            self.options.add_argument('--no-service-autorun')
            # self.options.add_argument("--disable-web-security")
            # self.options.add_argument("--disable-blink-features")
            # self.options.add_argument("--disable-blink-features=AutomationControlled")
            self.options.add_argument("--log-level=3")
            self.options.add_argument("--disable-encryption")
            self.options.add_argument("--lang=en-US")
            self.options.add_argument("--password-store=basic")
            self.options.add_argument("--no-default-browser-check")
            self.options.add_argument("--font-masking-mode=2")
            self.options.add_argument("--flag-switches-begin")
            self.options.add_argument("--flag-switches-end")
            # self.options.add_argument("--start-maximized")
            self.options.add_argument("--no-first-run")
            self.options.add_argument('--disable-gpu')  # google render, canvas fingerprint[3Win/1Android]
            self.options.add_argument('--override-use-software-gl-for-tests')  # google render, unique canvas fingerprint
            self.options.add_argument('--disable-dev-shm-usage')
            self.options.add_argument('--disable-browser-side-navigation')
            self.options.add_argument('--no-sandbox')
            self.options.add_argument('--allow-insecure-localhost')
            self.options.add_argument('--allow-running-insecure-content')
            self.options.add_argument('--disable-web-security')
            self.options.add_argument('--disable-blink-features=AutomationControlled')
            self.options.set_capability("detach", True)
            self.options.set_capability("acceptInsecureCerts", True)
            self.options.set_capability("acceptSslCerts", True)
            self.options.set_capability("goog:loggingPrefs", {"performance": "ALL"})
            # self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
            # self.options.add_experimental_option('useAutomationExtension', False)

            self.options.add_argument("--disk-cache-size=0")
            self.options.add_argument("--disk-cache-dir=/dev/null")
            self.options.add_argument('--ignore-certificate-errors')
            if self.phoneSetting:

              self.options.add_argument('--app')  # unknown?
            #   # self.options.add_argument('--app-shell-host-window-size=400x400')  # unknown?, doesn't change anything?
              self.options.add_argument('--force-app-mode')  # disables desktop features
              self.options.add_argument('--arc-availability=officially-supported')
              self.options.add_argument('--force-device-ownership')  # unknown?
              self.options.add_argument('--arc-generate-play-auto-install')
              self.options.add_argument('--arc-play-store-auto-update=on')
              self.options.add_argument('--arc-start-mode=always-start')
              self.options.add_argument('--touch-devices')
              self.options.add_argument('--enable-features=UserActivationV2')
              self.options.add_argument("--touch-events=enabled")
              self.options.add_argument('--enable-touchview')  # unknown?
              self.options.add_argument('--enable-virtual-keyboard')  # unknown?
              self.options.add_argument(  # unknown?
                  '--use-mobile-user-agent --enable-viewport --validate-input-event-stream --enable-longpress-drag-selection ' # todo does "--use-mobile-user-agent" have an effect?
                  '--touch-selection-strategy=direction --disable-composited-antialiasing --enable-dom-distiller '
                  ' --top-controls-show-threshold=0.5 '
                  '--top-controls-hide-threshold=0.5')      
            if disable_images:
                self.options.add_argument('--blink-settings=imagesEnabled=false')
            # self.options.add_experimental_option("excludeSwitches", ["enable-automation"])
            # self.options.add_experimental_option('useAutomationExtension', False)
            # self.options.add_experimental_option("detach", True)
            # s = ChromiumService(chrome_driver_path)
            # self.options.add_experimental_option("mobileEmulation", {
            #   "deviceName": "Pixel 2"
            # })
            desired_capabilities = self.options.to_capabilities()
            print(desired_capabilities)
            if not pageLoad:
                self.options.set_capability("pageLoadStrategy", "none")
            
            # self.options.enable_mobile('com.android.chrome')
            self.options.set_capability('platformName',flatform)
            user_agent = httpagentparser.detect(self.profile_user_agent)
            self.options.set_capability('browserVersion',user_agent['browser']['version'])
            socks5_details = self.profile_socks5_details.strip()
            proxy_details = self.profile_proxy_details.strip()
            if profileInfo['profile_proxy_details'].strip():
              self.proxy_details = profileInfo['profile_proxy_details']
              print('==profile_proxy_details==',self.proxy_details)
              if self.proxy_details.find('@') != -1:
                proxy_strip = self.proxy_details.split('@')
                proxy_ip_port = proxy_strip[1]
                proxy_authen = proxy_strip[0]
                proxy_ip = proxy_ip_port.split(':')[0]
                proxy_port = proxy_ip_port.split(':')[1]
                proxy_username = proxy_authen.split(':')[0]
                proxy_password = proxy_authen.split(':')[1]
              elif self.proxy_details.find('#') != -1:
                proxy_strip = self.proxy_details.split('#')
                proxy_ip_port = proxy_strip[0]
                proxy_authen = proxy_strip[1]
                proxy_ip = proxy_ip_port.split(':')[0].strip()
                proxy_port = proxy_ip_port.split(':')[1].strip()
                proxy_username = proxy_authen.split(':')[0].strip()
                proxy_password = proxy_authen.split(':')[1].strip()
              elif profileInfo['profile_proxy_username'] and profileInfo['profile_proxy_password']:
                proxy_ip_port = self.proxy_details.strip()
                proxy_ip = proxy_ip_port.split(':')[0]
                proxy_port = proxy_ip_port.split(':')[1]
                proxy_username = profileInfo['profile_proxy_username']     
                proxy_password =  profileInfo['profile_proxy_password']                 
              elif self.proxy_details.find(':') != -1:
                proxy_split = self.proxy_details.strip().split(':')
                proxy_ip_port = self.proxy_details.strip()
                proxy_ip = proxy_split[0]
                proxy_port =proxy_split[1]    
                if len(proxy_split) == 4:
                  proxy_username = proxy_split[2]
                  proxy_password = proxy_split[3]
                else:
                  proxy_username = None
                  proxy_password = None
              else:
                return
              if proxy_username and proxy_password:
                print(proxy_ip,proxy_port, proxy_username, proxy_password)        
                mun_proxy = munproxy.MunProxy()
                proxy_details = mun_proxy.forward(proxy_type='http+ssl',proxy_ip=proxy_ip, proxy_port=proxy_port, local_port=None, proxy_username=proxy_username, proxy_password=proxy_password)
                if proxy_details:
                  socks5_proxy, pid_id = proxy_details
                  self.profile_proxy_details = socks5_proxy
                socks5_details = proxy_username+':'+proxy_password+'@'+proxy_ip+':'+proxy_port
              print('profile_proxy_details','--proxy-server=https://' + self.profile_proxy_details)
              self.options.add_argument(
                  '--proxy-server=socks5://' + self.profile_socks5_details)
            if profileInfo['profile_socks5_details'].strip():
                print(profileInfo['profile_socks5_details'])
                if self.profile_socks5_details.find('@') != -1:
                  proxy_strip = self.profile_socks5_details.split('@')
                  proxy_ip_port = proxy_strip[1]
                  proxy_authen = proxy_strip[0]
                  proxy_ip = proxy_ip_port.split(':')[0]
                  proxy_port = proxy_ip_port.split(':')[1]
                  proxy_username = proxy_authen.split(':')[0]
                  proxy_password = proxy_authen.split(':')[1]
                elif self.profile_socks5_details.find('#') != -1:
                  proxy_strip = self.profile_socks5_details.split('#')
                  proxy_ip_port = proxy_strip[0]
                  proxy_authen = proxy_strip[1]
                  proxy_ip = proxy_ip_port.split(':')[0].strip()
                  proxy_port = proxy_ip_port.split(':')[1].strip()
                  proxy_username = proxy_authen.split(':')[0].strip()
                  proxy_password = proxy_authen.split(':')[1].strip()
                elif profileInfo['profile_proxy_username'] and profileInfo['profile_proxy_password']:
                  proxy_ip_port = self.profile_socks5_details.strip()
                  proxy_ip = proxy_ip_port.split(':')[0]
                  proxy_port = proxy_ip_port.split(':')[1]
                  proxy_username = profileInfo['profile_proxy_username']     
                  proxy_password =  profileInfo['profile_proxy_password']                 
                else:
                  proxy_ip_port = self.profile_socks5_details.strip()
                  proxy_ip = proxy_ip_port.split(':')[0]
                  proxy_port = proxy_ip_port.split(':')[1]        
                  proxy_username = None
                  proxy_password = None
                if proxy_username and proxy_password:
                  print(proxy_ip,proxy_port, proxy_username, proxy_password)        
                  mun_proxy = munproxy.MunProxy()
                  proxy_details = mun_proxy.forward(proxy_type='socks5',proxy_ip=proxy_ip, proxy_port=proxy_port, local_port=None, proxy_username=proxy_username, proxy_password=proxy_password)
                  if proxy_details:
                    socks5_proxy, pid_id = proxy_details
                    self.profile_socks5_details = socks5_proxy
                  socks5_details = proxy_username+':'+proxy_password+'@'+proxy_ip+':'+proxy_port
                print('profile_socks5_details','--proxy-server=socks5://' + self.profile_socks5_details)
                self.options.add_argument(
                    '--proxy-server=socks5://' + self.profile_socks5_details)

            if profileInfo['profile_webrtc']:
                print('==profile_webrtc==')
                # self.options.add_experimental_option("prefs", {"--enforce-webrtc-ip-permission-check": True 
                # })   
                self.options.add_argument("--enforce-webrtc-ip-permission-check")     
                self.options.add_argument("--force-webrtc-ip-handling-policy")
                preferences = {
                  "webrtc.ip_handling_policy": "disable_non_proxied_udp", 
                  "webrtc.multiple_routes_enabled": False,
                  "webrtc.nonproxied_udp_enabled": False
                   }

                self.options.add_experimental_option("prefs", preferences)
            if self.profile_time_zone == 2:
                timeZone = self.get_geo_ip(socks5=self.profile_socks5_details, proxy=self.profile_proxy_details)
                if not timeZone:
                  return
            # uc_caps = self.options.to_capabilities()    
            # self.capabilities = webdriver.DesiredCapabilities.CHROME.copy()
            
            # self.driver = webdriver.Chrome(service=ChromiumService(ChromeDriverManager(version='105.0.5195.52').install()), chrome_options=self.options)
            # self.driver.maximize_window()
            
            # print(self.seleniumwire_options)

                # if not timeZone:
                #   return
            # caps = DesiredCapabilities().CHROME

            # cacrt_path = os.path.join(THIS_FOLDER, 'ca.crt')   
            # cakey_path = os.path.join(THIS_FOLDER, 'ca.crt')   
            # self.seleniumwire_options.update({
            #     'ca_cert': cacrt_path,  # Use own root certificate
            #     'ca_key': cakey_path
            # })
            # print(THIS_FOLDER+'ca.crt')
            # mobile_emulation = {
            #     "deviceMetrics": { "width": 375, "height": 812, "pixelRatio": 3.0 },
            #     "userAgent": "Mozilla/5.0 (Linux; Android 4.2.1; en-us; Nexus 5 Build/JOP40D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166 Mobile Safari/535.19"
            # }

            # self.options.add_experimental_option("mobileEmulation", mobile_emulation)
            if self.phoneSetting:
                self.driver = uc.Chrome(driver_executable_path=chrome_driver_path, use_subprocess=True,version_main=109, options=self.options, browser_executable_path=chrome_binary_path, keep_alive=True)
            else:
                self.driver = uc.Chrome(driver_executable_path=chrome_driver_path, use_subprocess=True,version_main=109, options=self.options, browser_executable_path=chrome_binary_path)
            self.driver.execute_script(
            """
            (function byPassCloudFlare() {
                let objectToInspect = window,
                    result = [];
                while(objectToInspect !== null)
                { result = result.concat(Object.getOwnPropertyNames(objectToInspect));
                  objectToInspect = Object.getPrototypeOf(objectToInspect); }
                return result.filter(i => i.match(/.+_.+_(Array|Promise|Symbol)/ig))
            })();           

            (function fakeWebdriver() {
              Object.defineProperty(navigator, 'webdriver', {   value: undefined,   configurable: true });
            })();
            """
            )
            self.driver.execute_script(self.inject_driver)
            # time.sleep(0.5)
            if fake_finger:
                self.set_execute_cdp_cmd(self.driver, self.profile_os, self.profile_user_agent, onetime=True, sock5=self.profile_socks5_details, proxy=self.profile_proxy_details)
                self.set_excute_cdp_cmd_theard(onetime=onetime)

            self.driver.get('https://iphey.com')

            # time.sleep(1000)
            # split_str = self.profile_resolution.strip().split('x')
            # print('self.profile_resolution',self.profile_resolution)
            # screen_width = int(split_str[0])
            # screen_height = int(split_str[1])
            # self.driver.set_window_size(screen_width, screen_height)
            # self.driver.set_window_position(0, 0)
            # dict_size = self.driver.get_window_size()
            # self.open_start_url()
        return self.driver  
           
    def set_execute_cdp_cmd(self, driver, profile_os, profile_user_agent, onetime=False, sock5='', proxy=''):
 
        self.driver = driver
        self.profile_os = profile_os
        self.profile_user_agent = profile_user_agent
      
        while 1 :
            try:
              list_win_handles = self.driver.window_handles
            except:
              list_win_handles = []

            if len(list_win_handles) != 0:

              for window_handles in list_win_handles:
                  if window_handles not in self.window_execute_cdp_cmd:
                      try:
                        print('execute_cdp_cmd==', window_handles)
                        # self.driver.execute_cdp_cmd('Network.enable', {})
                        phoneSeting = False
                        self.driver.switch_to.window(window_handles)    
                        setCacheDisabled = dict({
                                              "cacheDisabled": True
                                          })                        
                        self.driver.execute_cdp_cmd('Network.setCacheDisabled', setCacheDisabled)

                        if self.profile_time_zone == 2:   
                            try:                   
                                self.driver.execute_cdp_cmd('Emulation.setTimezoneOverride', self.set_time_zone)  
                            except:
                                print('==error==setTimezoneOverride')
                            self.driver.execute_cdp_cmd("Emulation.setGeolocationOverride", self.Map_coordinates)      
                        if self.profile_os:
                            
                            flatform = 'Win32'
                            if self.profile_os == 'Window':
                                flatform = 'Win32'
                            elif self.profile_os == 'Mac OS X':
                                flatform = 'MacIntel'
                            elif self.profile_os == 'Linux':
                                flatform = 'Linux'
                            elif self.profile_os == 'Chrome OS':
                                flatform = 'CrOS'
                            elif self.profile_os.lower().find('iphone') != -1:
                                flatform = 'iPhone'
                                phoneSeting = True
                            else:
                                flatform = 'Android'
                                phoneSeting = True
                            self.set_navigator_override = dict({
                                'platform': flatform
                            }) 

                            self.driver.execute_cdp_cmd(
                                'Emulation.setNavigatorOverrides', self.set_navigator_override)
                            # self.profile_user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/104.0.0.0 Safari/537.36'
                            
                            user_agent = httpagentparser.detect(self.profile_user_agent)
                            # print('====',flatform, user_agent.os.version_string, user_agent.device.brand, user_agent.device.model, user_agent.browser.version_string)
                            if not user_agent['platform']['version']:
                              platform_verison = flatform
                            else:
                              platform_verison = user_agent['platform']['version']
                            version_first = user_agent['browser']['version'].split('.')[0]
                            userAgentMetadata = {'platform':flatform, 'platformVersion':platform_verison,'architecture':'x86','model':'','mobile':False, 'fullVersion':user_agent['browser']['version'],'fullVersionList':[{"brand": 'Chrome', "version": version_first}], 'brands': [{"brand": 'Chrome', "version": version_first}, {"brand": 'Chromium', "version": version_first}, {"brand": 'Not A;Brand', "version": '24'}]}
                            
                            if phoneSeting:
                              print('===mobile useragent==')
                              userAgentMetadata['architecture'] = ''
                              userAgentMetadata['model'] = ''
                              userAgentMetadata['mobile'] = True                           

                            self.set_profile_user_agent = dict({
                                'userAgent': self.profile_user_agent,
                                'platform': flatform,
                                'acceptLanguage': 'en-US;en',
                                'userAgentMetadata': userAgentMetadata
                            })  

                            self.driver.execute_cdp_cmd( 
                                'Network.setUserAgentOverride', self.set_profile_user_agent)                
                            self.driver.execute_cdp_cmd(
                                'Emulation.setUserAgentOverride', self.set_profile_user_agent)  
                        if self.profile_resolution:

                            split_str = self.profile_resolution.strip().split('x')
                            print('self.profile_resolution',self.profile_resolution)
                            screen_width = int(split_str[0])
                            screen_height = int(split_str[1])
                            # self.driver.set_window_size(screen_width, screen_height)
                            # self.driver.set_window_position(0, 0)
                            dict_size = self.driver.get_window_size()
                            print('====',dict_size)
                            setMobile = False
                            ScaleFactor = 0
                            if phoneSeting:
                              ScaleFactor = 50
                            self.set_device_metrics_override = dict({
                                            "width": screen_width,
                                            "height": screen_height,
                                            "screenWidth":screen_width,
                                            "screenHeight":screen_height,
                                            "deviceScaleFactor": ScaleFactor,
                                            "mobile": phoneSeting,
                                            'screenOrientation': {'type': 'portraitPrimary',
                                                              'angle': 0}
                                        })
                            
                            self.driver.execute_cdp_cmd('Emulation.setDeviceMetricsOverride', self.set_device_metrics_override)
                            self.driver.execute_cdp_cmd('Page.setDeviceMetricsOverride', self.set_device_metrics_override)
                            if phoneSeting:
                              setEmitTouchEventsForMouse = dict({
                                              "enabled": True,
                                              "configuration": 'mobile'
                                          })                        
                              self.driver.execute_cdp_cmd('Emulation.setEmitTouchEventsForMouse', setEmitTouchEventsForMouse)
                              
                              setTouchEmulationEnabled = dict({
                                              "enabled": True,
                                              "maxTouchPoints": 5
                                          })                        
                              self.driver.execute_cdp_cmd('Emulation.setTouchEmulationEnabled', setTouchEmulationEnabled)
                        if self.profile_cpu:    
                            self.set_hardware_override = dict({
                            'hardwareConcurrency':int(self.profile_cpu)
                            })
                            self.driver.execute_cdp_cmd('Emulation.setHardwareConcurrencyOverride', self.set_hardware_override)
                            
                        self.driver.execute_script(
                        """
                        document.addEventListener('DOMContentLoaded', function() {

                          let objectToInspect = window,
                          result = [];
                          while(objectToInspect !== null)
                          { result = result.concat(Object.getOwnPropertyNames(objectToInspect));
                            objectToInspect = Object.getPrototypeOf(objectToInspect); }
                          return result.filter(i => i.match(/.+_.+_(Array|Promise|Symbol)/ig))
                        });

                        """
                        )

                        self.driver.execute_script(self.inject_driver)   
                        
                        self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {'source': self.inject_driver})
                        # self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        # self.driver.execute_script('Object.defineProperty(navigator,"platform", { get: function () { return "MacIntel"; },  set: function (a) {} });')
                        
                        self.window_execute_cdp_cmd[window_handles] = 1
                        print('finished==execute_cdp_cmd')
                        # self.driver.execute_cdp_cmd('Network.disable', {})
                      except Exception as e:
                        print('===Error execute_cdp_cmd==', e)
                      time.sleep(1)
              if onetime:
                  break

            else:
                if self.statusqueue:
                    self.statusqueue.put(('closed_browser', json.dumps({'id':self.profileInfo['id']})))
                break
            #   print('==================list_win_handles', len(list_win_handles))
            #   try:
            #     self.driver.quit()
            #   except:
            #     pass
            #   for p in multiprocessing.active_children():
            #     print(p.name)
            #     p.terminate()
            #     # p.kill()
            #     p.join()
              # print('==kill process==',{'id':self.profileInfo['id']})


            time.sleep(0.01)
        # self.driver.service.stop()
        print('=====done theard====')

    def process_browser_log_entry(self, entry):
      response = json.loads(entry['message'])['message']
      return response    
    def get_browser_log(self):
      browser_log = self.driver.get_log('performance') 
      events = [self.process_browser_log_entry(entry) for entry in browser_log]
      events = [event for event in events if 'Network.response' in event['method']]
      return events
    def get_event_body(self, requestId):
      return self.driver.execute_cdp_cmd('Network.getResponseBody', {'requestId': requestId})  
    def html_inject(self, text):
      html = '''
        document.addEventListener('DOMContentLoaded', function() {

          const para = document.createElement("div");
          para.setAttribute("id", "MunAnti_bottom");
          para.style.cssText = 'background-color: #01ae7d;overflow: hidden; position: fixed;bottom: 0;width: 100%;text-align: center;z-index: 999999;';
          const node = document.createTextNode("{{text}}");
          para.appendChild(node);
          document.body.appendChild(para)
        });

      '''.replace('{{text}}', text)
      return html
    def set_excute_cdp_cmd_theard(self, onetime=False):
        thread = Thread(target=self.set_execute_cdp_cmd,
                        args=(self.driver, self.profile_os, self.profile_user_agent, onetime, self.profile_socks5_details, self.profile_proxy_details))
        thread.start()

    def close_browser(self):
      self.driver.quit()
      print('kill process')
      for p in multiprocessing.active_children():
        p.terminate()
        p.join()
            
    def open_start_url(self):
        if self.start_url:
            self.driver.get(self.start_url)    
    # self.cookie = cookielib.MozillaCookieJar()
    def set_cookies(self,cookies_file):
        cookies = []
        with open(cookies_file, 'r') as f:
            for e in f:
                e = e.strip()
                if e.startswith('#'): continue
                k = e.split('\t')
                if len(k) < 3: continue	# not enough data
                # with expiry
                if k[0][1:] == '.':
                  domain = k[0][1:]
                else:
                  domain = k[0]
                cookies_json = {'domain':domain.lower(),'secure':json.loads(k[1].lower()), 'httpOnly':json.loads(k[3].lower()),'path':k[2].lower(),'name': k[-2].lower(), 'value': k[-1].lower(), 'expires': int(k[-3])}
                cookies.append(dict(cookies_json))
                # self.driver.execute_cdp_cmd('Network.enable', {})
                # self.driver.execute_cdp_cmd('Network.setCookie' ,dict(cookies_json))  
                # self.driver.execute_cdp_cmd('Network.disable', {})
        self.set_cookies = {
          'cookies': list(cookies)
        }
        # self.driver.execute_cdp_cmd('Network.enable', {})
        self.driver.execute_cdp_cmd('Network.setCookies' , self.set_cookies)  
        # self.driver.execute_cdp_cmd('Network.disable', {})
        print('===imported coookies===')
        return True
    def save_cookies(self,cookies_file):
        all_cookies=self.driver.get_cookies();
        with open(cookies_file, 'r') as f:
          f.write(all_cookies)
        return cookies_file
    
    def get_cookies(self):
        all_cookies = self.driver.execute_cdp_cmd('Network.getAllCookies', {})
        # print(all_cookies['cookies'])
        return all_cookies['cookies'];
    
    def add_header(self, link_refer='', XMLHttpRequest=None, extraHeader={}):
        self.header = {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.5,/;q=0.5',
                    'Accept-Encoding': 'gzip, deflate, br',
                    'Accept-Language': 'en-US',
                    'Cache-Control': 'no-cache',
                    'Connection': 'keep-alive',
                    'User-Agent': self.agent,
                    "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-site"
                       };
        if self.agent:
            self.header.update({'User-Agent': self.agent})
        if link_refer:
            self.header.update({'Referer':link_refer})
        if extraHeader:
            self.header.update(extraHeader)
        if XMLHttpRequest:
            self.header.update({'X-Requested-With': 'XMLHttpRequest'})

    def set_proxies(self, sock5='', proxy=''):
        if sock5:
            self.sock5 = sock5
        elif proxy:
            self.proxy = proxy

    def get_inject_data(self):
      
      inject_data = {}
      inject_data['resolution'] = '''
        (function fakeScreenResolution(){
          "use strict";
          /**
          * Define property on an object.
          */
          var defineProp = function(obj, prop, val) {
            Object.defineProperty(obj, prop, {
              enumerable: true,
              configurable: true,
              value: val
            });
          };
          /**
          * Return screen attributes based on the most commons ones.
          */
          var getScreenAttrs = function() {
            return {
              width: {{screen_width}},
              height: {{screen_height}},
              colorDepth: 24,
              pixelDepth: 24
            };
          };
          /**
          * Spoof screen resolution.
          */
          var spoofScreenResolution = function() {
            var screen = getScreenAttrs();
            defineProp(window.screen, "width", screen.width);
            defineProp(window.screen, "height", screen.height);
            defineProp(window.screen, "availWidth", screen.width);
            defineProp(window.screen, "availHeight", screen.height);
            defineProp(window.screen, "top", 0);
            defineProp(window.screen, "left", 0);
            defineProp(window.screen, "availTop", 0);
            defineProp(window.screen, "availLeft", 0);
            defineProp(window.screen, "colorDepth", screen.colorDepth);
            defineProp(window.screen, "pixelDepth", screen.pixelDepth);
            /**
            * @todo Implement window.innerHeight, window.innerWidth, etc...
            * @see https://developer.mozilla.org/en-US/docs/Web/API/Screen
            */
          };
        
          /**
          * Initialize script
          */
          var init = function() {
            // LET SPOOF THAT FUCKIN' RES/COLOR DEPTH
            spoofScreenResolution();
          };
          init();
        })();


      '''
      inject_data['UserAgent'] = '''
      (function fakeUserAgent() {
        Object.defineProperty(navigator, 'userAgent', {   value: '{{UserAgent}}',   configurable: true });
      })();
      '''
      inject_data['vendor'] = '''
       (function fakeVendor() {
        Object.defineProperty(navigator, 'vendor', {   value: '{{vendor}}', configurable: true });
      })();     
      '''
      inject_data['MaxTouchPoints'] = '''
      (function fakeMaxTouchPoints() {
        Object.defineProperty(navigator, 'maxTouchPoints', {   value: {{MaxTouchPoints}},   configurable: true });
      })();
      '''
      inject_data['audio'] = '''
      (function fakeAudioFinger() {
        const context = {
          "BUFFER": null,
          "getChannelData": function (e) {
            const getChannelData = e.prototype.getChannelData;
            Object.defineProperty(e.prototype, "getChannelData", {
              "value": function () {
                const results_1 = getChannelData.apply(this, arguments);
                if (context.BUFFER !== results_1) {
                  context.BUFFER = results_1;
    
                  let obj2 = {{audio_content}};
                  for (const key of Object.keys(obj2)) {
                      results_1[key] = obj2[key]
                  }
                }
                return results_1;
              }, configurable: true, writable: true
            });
          },
          "createAnalyser": function (e) {
            const createAnalyser = e.prototype.__proto__.createAnalyser;
            Object.defineProperty(e.prototype.__proto__, "createAnalyser", {
              "value": function () {
                const results_2 = createAnalyser.apply(this, arguments);
                const getFloatFrequencyData = results_2.__proto__.getFloatFrequencyData;
                Object.defineProperty(results_2.__proto__, "getFloatFrequencyData", {
                  "value": function () {
                    const results_3 = getFloatFrequencyData.apply(this, arguments);
                    for (var i = 0; i < arguments[0].length; i += 100) {
                      let index = Math.floor({{audio_random1}} * i);
                      var new_value = arguments[0][index] + {{audio_random2}} * 0.1;
                      arguments[0][index] = new_value
                    }
                    return results_3;
                  }, configurable: true, writable: true
                });
                //
                return results_2;
              }, configurable: true, writable: true
            });
          }
        };
        //
        context.getChannelData(AudioBuffer);
        context.createAnalyser(AudioContext);
        context.getChannelData(OfflineAudioContext);
        context.createAnalyser(OfflineAudioContext);
        console.log('==fakeAudioFinger==',AudioBuffer);
      })();
      '''
      inject_data['canvas'] = '''
        (function fakeCanvasFingerPrint() {
          const toBlob = HTMLCanvasElement.prototype.toBlob;
          const toDataURL = HTMLCanvasElement.prototype.toDataURL;
          const getImageData = CanvasRenderingContext2D.prototype.getImageData;
          //
          var noisify = function (canvas, context) {
              //console.log('==let noisify==',context);
              if (context) {
                const shift = {{canvas_shift}};
                //
                let ctxIdx = ctxArr.indexOf(context);
                let info = ctxInf[ctxIdx];
                const width = canvas.width;
                const height = canvas.height;
                if (info.useArc || info.useFillText && width && height) {
                  const imageData = getImageData.apply(context, [0, 0, width, height]);
                  for (let i = 0; i < height; i++) {
                    for (let j = 0; j < width; j++) {
                      const n = ((i * (width * 4)) + (j * 4));
                      imageData.data[n + 0] = imageData.data[n + 0] + shift.r;
                      imageData.data[n + 1] = imageData.data[n + 1] + shift.g;
                      imageData.data[n + 2] = imageData.data[n + 2] + shift.b;
                      imageData.data[n + 3] = imageData.data[n + 3] + shift.a;
                    }
                  }
                  //
                  //window.top.postMessage("canvas-fingerprint-defender-alert", '*');
                  context.putImageData(imageData, 0, 0); 
                }
              }
          };
          let ctxArr = [];
          let ctxInf = [];    
          let rawGetContext = HTMLCanvasElement.prototype.getContext
      
          Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
              "value": function () {
                  let result = rawGetContext.apply(this, arguments);
                  if (arguments[0] === '2d') {
                      ctxArr.push(result)
                      ctxInf.push({})
                  }
                  return result;
              }, configurable: true
          });
      
          Object.defineProperty(HTMLCanvasElement.prototype.constructor, "length", {
              "value": 1, configurable: true, writable: true
          });
      
          Object.defineProperty(HTMLCanvasElement.prototype.constructor, "toString", {
              "value": () => "function getContext() { [native code] }", configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.constructor, "name", {
              "value": "getContext", configurable: true
          });
          let rawArc = CanvasRenderingContext2D.prototype.arc
          Object.defineProperty(CanvasRenderingContext2D.prototype, "arc", {
              "value": function () {
                  let ctxIdx = ctxArr.indexOf(this);
                  ctxInf[ctxIdx].useArc = true;
                  return rawArc.apply(this, arguments);
              }, configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "length", {
              "value": 5, configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "toString", {
              "value": () => "function arc() { [native code] }", configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.arc, "name", {
              "value": "arc", configurable: true, writable: true
          });    
          const rawFillText = CanvasRenderingContext2D.prototype.fillText;
          Object.defineProperty(CanvasRenderingContext2D.prototype, "fillText", {
              "value": function () {
                  let ctxIdx = ctxArr.indexOf(this);
                  ctxInf[ctxIdx].useFillText = true;
                  return rawFillText.apply(this, arguments);
              }, configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "length", {
              "value": 4, configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "toString", {
              "value": () => "function fillText() { [native code] }", configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.fillText, "name", {
              "value": "fillText", configurable: true, writable: true
          }); 
          //
          Object.defineProperty(HTMLCanvasElement.prototype, "toBlob", {
              "value": function () {
                noisify(this, this.getContext("2d"));
                return toBlob.apply(this, arguments);
              }, configurable: true, writable: true
          });
          Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "length", {
              "value": 1, configurable: true, writable: true
          });
      
          Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "toString", {
              "value": () => "function toBlob() { [native code] }", configurable: true, writable: true
          });
      
          Object.defineProperty(HTMLCanvasElement.prototype.toBlob, "name", {
              "value": "toBlob", configurable: true, writable: true
          });  
          //
          Object.defineProperty(HTMLCanvasElement.prototype, "toDataURL", {
              "value": function () {
                noisify(this, this.getContext("2d"));
                return toDataURL.apply(this, arguments);
              }, configurable: true, writable: true
          });
          Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "length", {
              "value": 0, configurable: true, writable: true
          });
      
          Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "toString", {
              "value": () => "function toDataURL() { [native code] }", configurable: true, writable: true
          });
      
          Object.defineProperty(HTMLCanvasElement.prototype.toDataURL, "name", {
              "value": "toDataURL", configurable: true, writable: true
          });
          //
          Object.defineProperty(CanvasRenderingContext2D.prototype, "getImageData", {
              "value": function () {
                noisify(this.canvas, this);
                return getImageData.apply(this, arguments);
              }, configurable: true, writable: true
          });
          Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "length", {
              "value": 4, configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "toString", {
              "value": () => "function getImageData() { [native code] }", configurable: true, writable: true
          });
      
          Object.defineProperty(CanvasRenderingContext2D.prototype.getImageData, "name", {
              "value": "getImageData", configurable: true, writable: true
          });
        })(); 
 
      '''
      inject_data['time_zone'] = '''
      ( function fakeTimeZone() {
          Date.prefs = {{timeZoneArray}};
          console.log('==Date.prefs==',Date.prefs);
          const ODateTimeFormat = Intl.DateTimeFormat;
          Intl.DateTimeFormat = function(locales, options = {}) {
            Object.assign(options, {
              timeZone: Date.prefs[0]
            });
            return ODateTimeFormat(locales, options);
          };
          Intl.DateTimeFormat.prototype = Object.create(ODateTimeFormat.prototype);
          Intl.DateTimeFormat.supportedLocalesOf = ODateTimeFormat.supportedLocalesOf;
          const clean = str => {
            const toGMT = offset => {
              const z = n => (n < 10 ? '0' : '') + n;
              const sign = offset <= 0 ? '+' : '-';
              offset = Math.abs(offset);
              return sign + z(offset / 60 | 0) + z(offset % 60);
            };
            str = str.replace(/([T\\(])[\\+-]\\d+/g, '$1' + toGMT(Date.prefs[1]));
            if (str.indexOf(' (') !== -1) {
              str = str.split(' (')[0] + ' (' + Date.prefs[3] + ')';
            }
            return str;
          }

          const ODate = Date;
          const {
            getTime, getDate, getDay, getFullYear, getHours, getMilliseconds, getMinutes, getMonth, getSeconds, getYear,
            toDateString, toLocaleString, toString, toTimeString, toLocaleTimeString, toLocaleDateString,
            setYear, setHours, setTime, setFullYear, setMilliseconds, setMinutes, setMonth, setSeconds, setDate,
            setUTCDate, setUTCFullYear, setUTCHours, setUTCMilliseconds, setUTCMinutes, setUTCMonth, setUTCSeconds
          } = ODate.prototype;
          
          class ShiftedDate extends ODate {
            constructor(...args) {
              super(...args);
              this.nd = new ODate(
                getTime.apply(this) + (Date.prefs[2] - Date.prefs[1]) * 60 * 1000
              );
            }
            // get
            toLocaleString(...args) {
              return toLocaleString.apply(this.nd, args);
            }
            toLocaleTimeString(...args) {
              return toLocaleTimeString.apply(this.nd, args);
            }
            toLocaleDateString(...args) {
              return toLocaleDateString.apply(this.nd, args);
            }
            toDateString(...args) {
              return toDateString.apply(this.nd, args);
            }
            getDate(...args) {
              return getDate.apply(this.nd, args);
            }
            getDay(...args) {
              return getDay.apply(this.nd, args);
            }
            getFullYear(...args) {
              return getFullYear.apply(this.nd, args);
            }
            getHours(...args) {
              return getHours.apply(this.nd, args);
            }
            getMilliseconds(...args) {
              return getMilliseconds.apply(this.nd, args);
            }
            getMinutes(...args) {
              return getMinutes.apply(this.nd, args);
            }
            getMonth(...args) {
              return getMonth.apply(this.nd, args);
            }
            getSeconds(...args) {
              return getSeconds.apply(this.nd, args);
            }
            getYear(...args) {
              return getYear.apply(this.nd, args);
            }
            // set
            setHours(...args) {
              const a = getTime.call(this.nd);
              const b = setHours.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setFullYear(...args) {
              const a = getTime.call(this.nd);
              const b = setFullYear.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setMilliseconds(...args) {
              const a = getTime.call(this.nd);
              const b = setMilliseconds.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setMinutes(...args) {
              const a = getTime.call(this.nd);
              const b = setMinutes.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setMonth(...args) {
              const a = getTime.call(this.nd);
              const b = setMonth.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setSeconds(...args) {
              const a = getTime.call(this.nd);
              const b = setSeconds.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setDate(...args) {
              const a = getTime.call(this.nd);
              const b = setDate.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setYear(...args) {
              const a = getTime.call(this.nd);
              const b = setYear.apply(this.nd, args);
              setTime.call(this, getTime.call(this) + b - a);
              return b;
            }
            setTime(...args) {
              const a = getTime.call(this);
              const b = setTime.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            setUTCDate(...args) {
              const a = getTime.call(this);
              const b = setUTCDate.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            setUTCFullYear(...args) {
              const a = getTime.call(this);
              const b = setUTCFullYear.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            setUTCHours(...args) {
              const a = getTime.call(this);
              const b = setUTCHours.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            setUTCMilliseconds(...args) {
              const a = getTime.call(this);
              const b = setUTCMilliseconds.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            setUTCMinutes(...args) {
              const a = getTime.call(this);
              const b = setUTCMinutes.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            setUTCMonth(...args) {
              const a = getTime.call(this);
              const b = setUTCMonth.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            setUTCSeconds(...args) {
              const a = getTime.call(this);
              const b = setUTCSeconds.apply(this, args);
              setTime.call(this.nd, getTime.call(this.nd) + b - a);
              return b;
            }
            // toString
            toString(...args) {
              return clean(toString.apply(this.nd, args));
            }
            toTimeString(...args) {
              return clean(toTimeString.apply(this.nd, args));
            }
            // offset
            getTimezoneOffset() {
              return Date.prefs[1];
            }
          }
          Date = ShiftedDate;
          console.log('==fakeTimeZone==');       
      })();    
      '''
      inject_data['webgl'] = '''
        (function fakeWebgl() {
          var config = {
            "random": {
              "value": function () {
                return Math.random();
              },
              "item": function (e) {
                var rand = e.length * config.random.value();
                return e[Math.floor(rand)];
              },
              "number": function (power) {
                var tmp = [];
                for (var i = 0; i < power.length; i++) {
                  tmp.push(Math.pow(2, power[i]));
                }
                /*  */
                return config.random.item(tmp);
              },
              "int": function (power) {
                var tmp = [];
                for (var i = 0; i < power.length; i++) {
                  var n = Math.pow(2, power[i]);
                  tmp.push(new Int32Array([n, n]));
                }
                /*  */
                return config.random.item(tmp);
              },
              "float": function (power) {
                var tmp = [];
                for (var i = 0; i < power.length; i++) {
                  var n = Math.pow(2, power[i]);
                  tmp.push(new Float32Array([1, n]));
                }
                /*  */
                return config.random.item(tmp);
              }
            },
            "spoof": {
              "webgl": {
                "buffer": function (target) {
                  var proto = target.prototype ? target.prototype : target.__proto__;
                  const bufferData = proto.bufferData;
                  Object.defineProperty(proto, "bufferData", {
                    "value": function () {
                      var index = Math.floor({{gl_index}} * arguments[1].length);
                      var noise = arguments[1][index] !== undefined ? 0.1 * {{gl_noise}} * arguments[1][index] : 0;
                      //
                      arguments[1][index] = arguments[1][index] + noise;
                      //
                      return bufferData.apply(this, arguments);
                    }, configurable: true, writable: true
                  });
                },
                "parameter": function (target) {
                  var proto = target.prototype ? target.prototype : target.__proto__;
                  const getParameter = proto.getParameter;
                  Object.defineProperty(proto, "getParameter", {
                    "value": function () {
                      //window.top.postMessage("webgl-fingerprint-defender-alert", '*');
                      //
                      if (arguments[0] === 3415) return {{3412}};
                      else if (arguments[0] === 3414) return {{3412}};
                      else if (arguments[0] === 3415) return {{3412}};
                      else if (arguments[0] === 35375) return {{3412}};
                      else if (arguments[0] === 35374) return {{3412}};
                      else if (arguments[0] === 35380) return {{3412}};
                      else if (arguments[0] === 34045) return {{3412}};
                      else if (arguments[0] === 36348) return {{3412}};
                      else if (arguments[0] === 35371) return {{3412}};
                      else if (arguments[0] === 37154) return {{3412}};
                      else if (arguments[0] === 35659) return {{3412}};
                      else if (arguments[0] === 35978) return {{3412}};
                      else if (arguments[0] === 35979) return {{3412}};
                      else if (arguments[0] === 35968) return {{3412}};
                      else if (arguments[0] === 34852) return {{3412}};
                      else if (arguments[0] === 36063) return {{3412}};
                      else if (arguments[0] === 36183) return {{3412}};
                      else if (arguments[0] === 7936) return "WebKit";
                      else if (arguments[0] === 37445) return "{{37445}}";
                      else if (arguments[0] === 7937) return "WebKit WebGL";
                      else if (arguments[0] === 3379) return {{3379}};
                      else if (arguments[0] === 36347) return {{36347}};
                      else if (arguments[0] === 34076) return {{34076}};
                      else if (arguments[0] === 34024) return {{34024}};
                      else if (arguments[0] === 3386) return {{3386}};
                      else if (arguments[0] === 3413) return {{3413}};
                      else if (arguments[0] === 3412) return {{3412}};
                      else if (arguments[0] === 3411) return {{3411}};
                      else if (arguments[0] === 3410) return {{3410}};
                      else if (arguments[0] === 34047) return {{34047}};
                      else if (arguments[0] === 34930) return {{34930}};
                      else if (arguments[0] === 34921) return {{34921}};
                      else if (arguments[0] === 34324) return Math.floor({{34324}} * 6100) + 8192;
                      else if (arguments[0] === 35376) return Math.floor({{35376}} * 36384) + 10384;
                      else if (arguments[0] === 35377) return Math.floor({{35377}} * 50188) + 20188;
                      else if (arguments[0] === 35379) return Math.floor({{35379}} * 50188) + 20188;
                      else if (arguments[0] === 35658) return Math.floor({{35658}} * 36) + 1000;
                      else if (arguments[0] === 35660) return {{35660}};
                      else if (arguments[0] === 35661) return {{35661}};                  
                      else if (arguments[0] === 36349) return {{36349}};
                      else if (arguments[0] === 33902) return {{33902}};
                      else if (arguments[0] === 33901) return {{33901}};
                      else if (arguments[0] === 37446) return "{{37446}}";
                      else if (arguments[0] === 7938) return "{{7938}}";
                      else if (arguments[0] === 35724) return "{{35724}}";
                      //
                      return getParameter.apply(this, arguments);
                    }, configurable: true, writable: true
                  });
                }
              }
            }
          };  
          config.spoof.webgl.buffer(WebGLRenderingContext);
          config.spoof.webgl.buffer(WebGL2RenderingContext);
          config.spoof.webgl.parameter(WebGLRenderingContext);
          config.spoof.webgl.parameter(WebGL2RenderingContext);
          console.log('==fakeWebglFingerPrint==');
        })();

      '''
      inject_data['network'] = '''
      (function fakeNetwork() {
          function doUpdateProp(obj, prop, newVal){
              let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};

              props["value"] = newVal;
              props["configurable"] = true;
              Object.defineProperty(obj, prop, props);

              return props;
          }
          var rand = function(max){
              return Math.floor(Math.random()*max);
          };
          var randArr = function(arr){
              return arr[Math.floor(Math.random() * arr.length)];
          };

          let NetworkInformation = function(){
              this.downlink = rand(10);
              this.downlinkMax = Infinity;
              this.effectiveType = "4g"; // randArr(["4g","3g","2g"]);
              this.rtt = randArr([50,75,100,125,150]);
              this.saveData = false;
              this.type = randArr(["wifi","ethernet","other"]);

              this.onchange = null;
              this.ontypechange = null;

              this.__proto__ = NetworkInformation;
          };
          let fakeNet = new NetworkInformation();

          fakeNet.addEventListener = function(){};

          doUpdateProp(navigator,"connection", fakeNet);
          console.log('==fakeNetwork==');
      })();

      '''
      inject_data['fonts'] = '''
      
        (function fakeFonts() {
          function defineobjectproperty(val, e, c, w) {
            // Makes an object describing a property
            return {
              value: val,
              enumerable: !!e,
              configurable: !!c,
              writable: !!w
            }
          }
          
          var DEFAULT = 'auto'
          var originalStyleSetProperty = CSSStyleDeclaration.prototype.setProperty
          var originalSetAttrib = Element.prototype.setAttribute
          var originalNodeAppendChild = Node.prototype.appendChild
          var FontListToUse = {{fonts}}.map(function(x){return x.toLowerCase()});
          var baseFonts= ["default"]
          var keywords = ["inherit", "auto", "default", "!Important"]
          baseFonts.push.apply(baseFonts, FontListToUse)
          baseFonts.push.apply(baseFonts, keywords)

          function getAllowedFontFamily(family) {
            var fonts = family.replace(/"|'/g,'').split(',')
            var allowedFonts = fonts.filter(function(font) {
              if(font && font.length) {
                var normalised = font.trim().toLowerCase()
                // Allow base fonts
                for(var allowed of baseFonts)
                  if(normalised == allowed) return true
                // Allow web fonts
                for (var allowed of document.fonts.values())
                  if(normalised == allowed) return true
              }
            })
            return allowedFonts.map(function(f){
              var trimmed = f.trim()
              return ~trimmed.indexOf(' ') ? "'" + trimmed + "'" : trimmed
            }).join(", ")
          }
          

          function modifiedCssSetProperty(key, val) {
            if(key.toLowerCase() == 'font-family') {
              var keyresult = key.toLowerCase()
              var allowed = getAllowedFontFamily(val)
              var oldFF = this.fontFamily
              return originalStyleSetProperty.call(this, 'font-family', allowed || DEFAULT)
            }
            return originalStyleSetProperty.call(this, key, val)
          }
          
          function makeModifiedSetCssText(originalSetCssText) {
            return function modifiedSetCssText(css) {
              var fontFamilyMatch = css.match(/\b(?:font-family:([^;]+)(?:;|$))/i)
              if(fontFamilyMatch && fontFamilyMatch.length == 1) {
                css = css.replace(/\b(font-family:[^;]+(;|$))/i, '').trim()
                var allowed = getAllowedFontFamily(fontFamilyMatch[1]) || DEFAULT
                if(css.length && css[css.length - 1] != ';')
                  css += ';'
                css += "font-family: " + allowed + ";"
              }
              return originalSetCssText.call(this, css)
            }
          }
          
          var modifiedSetAttribute = (function() {
            var innerModify = makeModifiedSetCssText(function (val) {
              return originalSetAttrib.call(this, 'style', val)
            })
            return function modifiedSetAttribute(key, val) {
              if(key.toLowerCase() == 'style') {
                return innerModify.call(this, val)
              }
              return originalSetAttrib.call(this, key, val)
            }
          })();
          
          function makeModifiedInnerHTML(originalInnerHTML) {
            return function modifiedInnerHTML(html) {
              var retval = originalInnerHTML.call(this, html)
              recursivelyModifyFonts(this.parentNode)
              return retval
            }
          }
          
          function recursivelyModifyFonts(elem) {
            if(elem) {
              if(elem.style && elem.style.fontFamily) {
                modifiedCssSetProperty.call(elem.style, 'font-family', elem.style.fontFamily) // Uses the special setter
              }
              if(elem.childNodes)
                elem.childNodes.forEach(recursivelyModifyFonts)
            }
            return elem
          }

          function modifiedAppend(child) {
            child = recursivelyModifyFonts(child)
            return originalNodeAppendChild.call(this, child)
          }
          
            
          var success = true
          
          function overrideFunc(obj, name, f) {
            try {
              Object.defineProperty(obj.prototype, name, defineobjectproperty(f, true))
            } catch(e) {success=false;}
          }
          
          
          function overrideSetter(obj, name, makeSetter) {
            try {
              var current = Object.getOwnPropertyDescriptor(obj.prototype, name)
              current.set = makeSetter(current.set)
              current.configurable = false
              Object.defineProperty(obj.prototype, name, current)
            } catch(e) {success=false;}
          }
          
          overrideFunc(Node, 'appendChild', modifiedAppend)
          overrideFunc(CSSStyleDeclaration, 'setProperty', modifiedCssSetProperty)
          overrideFunc(Element, 'setAttribute', modifiedSetAttribute)
          
          
          
          try {
            Object.defineProperty(CSSStyleDeclaration.prototype, "fontFamily", {
              set: function fontFamily(f) {
                modifiedCssSetProperty.call(this, 'font-family', f)
              },
              get: function fontFamily() {
                return this.getPropertyValue('font-family')
              }
            })
          } catch(e) {success=false;}
          
          overrideSetter(CSSStyleDeclaration,'cssText', makeModifiedSetCssText)
          overrideSetter(Element,'innerHTML', makeModifiedInnerHTML)
          overrideSetter(Element,'outerHTML', makeModifiedInnerHTML)
          console.log('==fakeFonts=='); 
        })();
      '''
      inject_data['rects'] = '''
        self['MunAnti_NloJhCLvAOj_func'] = function(frame){
          if (frame === null) {
            console.error("Frame is null");
            return;
          }

          if (!frame['MunAnti_NloJhCLvAOj_done']) {
            (function(frame){
                function doUpdateProp(obj, prop, newVal){
                let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};

                if (!props["configurable"]) {
                    //console.warn("Issue with property not being able to be configured.");
                    return;
                }

                props["value"] = newVal;
                Object.defineProperty(obj, prop, props);

                return props;
            }

            // Generate offset
            let off = {{rects}};

            function updatedRect(old,round,overwrite){
                function genOffset(round,val){
                    return val + (round ? Math.round(off) : off);
                }

                let temp = overwrite === true ? old : new DOMRect();

                temp.top 	= genOffset(round,old.top);
                temp.right	= genOffset(round,old.right);
                temp.bottom = genOffset(round,old.bottom);
                temp.left 	= genOffset(round,old.left);
                temp.width 	= genOffset(round,old.width);
                temp.height = genOffset(round,old.height);
                temp.x 		= genOffset(round,old.x);
                temp.y 		= genOffset(round,old.y);

                return temp;
            }

            function getClientRectsProtection(el){
                if (window.location.host === "docs.google.com") return;

                let clientRects = frame[el].prototype.getClientRects;
                doUpdateProp(frame[el].prototype,"getClientRects",function(){
                    let rects = clientRects.apply(this,arguments);
                    let krect = Object.keys(rects);

                    let DOMRectList = function(){};
                    let list = new DOMRectList();
                    list.length = krect.length;
                    for (let i = 0;i<list.length;i++){
                        if (krect[i] === "length") continue;
                        list[i] = updatedRect(rects[krect[i]],false,false);
                    }

                    //window.top.postMessage("trace-protection::ran::clientrects::" + el + "get", '*');
                    return list;
                });
                doUpdateProp(frame[el].prototype.getClientRects, "toString",function(){
                    //window.top.postMessage("trace-protection::ran::clientrects::" + el + "getstring", '*');
                    return "getClientRects() { [native code] }";
                });
                console.log('==getClientRectsProtection==')
            }
            function getBoundingClientRectsProtection(el){
                let boundingRects = frame[el].prototype.getBoundingClientRect;
                doUpdateProp(frame[el].prototype,"getBoundingClientRect",function(){
                    let rect = boundingRects.apply(this,arguments);
                    if (this === undefined || this === null) return rect;

                    //window.top.postMessage("trace-protection::ran::clientrectsbounding::" + el + "get", '*');

                    return updatedRect(rect,true,true);
                });
                doUpdateProp(frame[el].prototype.getBoundingClientRect, "toString",function(){
                    //window.top.postMessage("trace-protection::ran::clientrectsbounding::" + el + "getstring", '*');
                    return "getBoundingClientRect() { [native code] }";
                });
                console.log('==getBoundingClientRectsProtection==')
            }

            ["Element","Range"].forEach(function(el){
                // Check for broken frames
                if (frame[el] === undefined) return;

                // getClientRects
                getClientRectsProtection(el);

                // getBoundingClientRect
                getBoundingClientRectsProtection(el);
            });
          })(frame);
          } else {
              frame['MunAnti_NloJhCLvAOj_done'] = true;
              //console.log(frame);
          }
        };

        self['MunAnti_NloJhCLvAOj_func'](window);


        ["HTMLIFrameElement","HTMLFrameElement"].forEach(function(el) {
            var wind = self[el].prototype.__lookupGetter__('contentWindow'),
                cont = self[el].prototype.__lookupGetter__('contentDocument');

            Object.defineProperties(self[el].prototype,{
                contentWindow:{
                    get:function(){
                        if (this.src && this.src.indexOf('//') !== -1 && location.host !== this.src.split('/')[2]) return wind.apply(this);

                        let frame = wind.apply(this);
                        if (frame) self['MunAnti_NloJhCLvAOj_func'](frame);

                        return frame;
                    }
                },
                contentDocument:{
                    get:function(){
                        if (this.src && this.src.indexOf('//') !== -1 && location.host !== this.src.split('/')[2]) return cont.apply(this);

                        let frame = cont.apply(this);
                        if (frame) self['MunAnti_NloJhCLvAOj_func'](frame);

                        return frame;
                    }
                }
            });
        });
      '''
      inject_data['webrtc'] = '''
        (function disableWebrtc() {
          if (typeof window.MediaStreamTrack !== "undefined") window.MediaStreamTrack = undefined;
          if (typeof window.RTCPeerConnection !== "undefined") window.RTCPeerConnection = undefined;
          if (typeof window.RTCSessionDescription !== "undefined") window.RTCSessionDescription = undefined;
          if (typeof window.webkitMediaStreamTrack !== "undefined") window.webkitMediaStreamTrack = undefined;
          if (typeof window.webkitRTCPeerConnection !== "undefined") window.webkitRTCPeerConnection = undefined;
          if (typeof window.webkitRTCSessionDescription !== "undefined") window.webkitRTCSessionDescription = undefined;
        })();
        console.log('==disableWebrtc=='); 
      '''
      inject_data['battery'] = '''
        (function fakeBattery() {
          // Random 2 dp value
          let setting_level = Math.floor(Math.random()*100)/100;

          function doUpdateProp(obj, prop, newVal){
              let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};

              props["value"] = newVal;
              props["configurable"] = true;
              Object.defineProperty(obj, prop, props);

              return props;
          }



          let BatteryPromise = new Promise(function(resolve, reject){
              let BatteryManager = function(){
                  this.charging = true;
                  this.chargingTime = Infinity;
                  this.dischargingTime = Infinity;
                  this.level = setting_level;

                  this.onchargingchange = null;
                  this.onchargingtimechange = null;
                  this.ondischargingtimechange = null;
                  this.onlevelchange = null;

                  //window.top.postMessage("trace-protection::ran::battery::main", '*');
              };

              resolve(new BatteryManager())
          });

          doUpdateProp(navigator,"getBattery",function() {
              return BatteryPromise;
          });
          doUpdateProp(navigator.getBattery,"toString","function getBattery() { [native code] }");
        })();

      '''
      inject_data['ping'] = '''
       (function fakePing() {
          if (!navigator || !navigator.sendBeacon){
            return;
          }
          function doUpdateProp(obj, prop, newVal){
            let props = Object.getOwnPropertyDescriptor(obj, prop) || {configurable:true};

            if (!props["configurable"]) {
              //console.warn("Issue with property not being able to be configured.");
              return;
            }

            props["value"] = newVal;
            Object.defineProperty(obj, prop, props);
            return props;
          }

          doUpdateProp(navigator,"sendBeacon",function() {
            //window.top.postMessage("trace-protection::ran::sendbeacon::main", '*');
            return true;
          });
          doUpdateProp(navigator.sendBeacon,"toString","function sendBeacon() { [native code] }");
      })();    


 
      '''
      
      return inject_data
    
   
    def open_random_driver(self, sock5='', proxy='', proxy_username='', proxy_password='', phoneOs=False, disable_images=False, pageLoad=True, fakefirstTab=False):
      profile_info  = self.create_random_profile(sock5=sock5, proxy=proxy, proxy_username=proxy_username, proxy_password=proxy_password, phoneOs=phoneOs)
      inject_data = self.get_inject_data()
      # # print(profile_info)
      self.driver = self.setting(inject_str=inject_data,
                          profileInfo=profile_info, onetime=fakefirstTab, type_browser='Chrome', disable_images=disable_images, pageLoad=pageLoad)
      return self.driver
    
    def create_random_profile(self, sock5='', proxy='', proxy_username='', proxy_password='', phoneOs=False):
        profile_dict = {}

        #GEO

        profile_dict['profile_geo'] = 2

        #webrtc

        profile_dict['profile_webrtc'] = 2
        #time_zone

        profile_dict['profile_time_zone'] = 2

        #proxy
        profile_dict['profile_socks5_details'] = sock5
        profile_dict['profile_proxy_details'] = proxy
        profile_dict['profile_proxy_username'] = proxy_username
        profile_dict['profile_proxy_password'] = proxy_password
        profile_dict['profile_proxy_type'] = 2
        #audio

        list_length = 44100
        listAudioContent = {}
        i = 0
        while i < list_length:
            index = int(random.uniform(0.01, 0.99)*i)
            listAudioContent[index] = round(
                random.uniform(0.01, 0.99) * 0.0000001, 15)
            i += 100
        audio_random1 = round(random.uniform(0.01, 0.99), 15)
        audio_random2 = round(random.uniform(0.01, 0.99), 15)
        audio_dict = {}
        audio_dict['audio_content'] = listAudioContent
        audio_dict['audio_random1'] = audio_random1
        audio_dict['audio_random2'] = audio_random2
        profile_dict['profile_audio'] = json.dumps(audio_dict)
        #canvas

        list_canvas = [-3, -2, -1, 0, 1, 2, 3]
        rsalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
        gsalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
        bsalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
        asalt_content = list_canvas[random.randint(0, len(list_canvas) - 1)]
        canvas_shift = {'r': rsalt_content, 'g': gsalt_content,
                        'b': bsalt_content, 'a': asalt_content}
        profile_dict['profile_canvas'] = json.dumps(canvas_shift)

        #webgl
        list_floats = [math.pow(2, 0), math.pow(2, 10), math.pow(
            2, 11), math.pow(2, 12), math.pow(2, 13)]
        list_int = [math.pow(2, 13), math.pow(2, 14), math.pow(2, 15)]
        int_3386 = int(list_int[random.randint(0, len(list_int) - 1)])
        list_1234 = [math.pow(2, 1), math.pow(
            2, 2), math.pow(2, 3), math.pow(2, 4)]
        list_1415 = [math.pow(2, 14), math.pow(2, 15)]
        list_1213 = [math.pow(2, 12), math.pow(2, 13)]
        list_45678 = [math.pow(2, 4), math.pow(2, 5), math.pow(
            2, 6), math.pow(2, 7), math.pow(2, 8)]
        list_10111213 = [math.pow(2, 10), math.pow(
            2, 11), math.pow(2, 12), math.pow(2, 13)]
        webgl_replace = {}
        webgl_replace['36347'] = int(
            list_1213[random.randint(0, len(list_1213) - 1)])
        webgl_replace['3379'] = int(
            list_1415[random.randint(0, len(list_1415) - 1)])
        webgl_replace['34076'] = int(
            list_1415[random.randint(0, len(list_1415) - 1)])
        webgl_replace['34024'] = int(
            list_1415[random.randint(0, len(list_1415) - 1)])
        webgl_replace['35661'] = int(
            list_45678[random.randint(0, len(list_45678) - 1)])
        webgl_replace['36349'] = int(
            list_10111213[random.randint(0, len(list_10111213) - 1)])
        webgl_replace['3413'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['3412'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['3411'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['3410'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['35660'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['34047'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['34930'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['34921'] = int(
            list_1234[random.randint(0, len(list_1234) - 1)])
        webgl_replace['3386'] = [int_3386, int_3386]
        webgl_replace['33901'] = [round(random.uniform(
            0.01, 1), 15), list_floats[random.randint(0, len(list_floats) - 1)]]
        webgl_replace['33902'] = [round(random.uniform(
            0.01, 1), 15), list_floats[random.randint(0, len(list_floats) - 1)]]
        webgl_replace['34324'] = round(random.uniform(0.01, 0.99), 15)
        webgl_replace['35376'] = round(random.uniform(0.01, 0.99), 15)
        webgl_replace['35377'] = round(random.uniform(0.01, 0.99), 15)
        webgl_replace['35379'] = round(random.uniform(0.01, 0.99), 15)
        webgl_replace['35658'] = round(random.uniform(0.01, 0.99), 15)
        webgl_replace['gl_index'] = round(random.uniform(0.01, 0.99), 15)
        webgl_replace['gl_noise'] = round(random.uniform(0.01, 0.99), 15)
        # list_vgas[random.randint(0, len(list_vgas) - 1)]
        list_vgas = ['ANGLE (NVIDIA Quadro 2000M Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA Quadro K420 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro 2000M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro K2000M Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 3800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0)','ANGLE (AMD Radeon R9 200 Series Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 3000 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 4 Series Express Chipset Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) Graphics Media Accelerator 3150 Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) G41 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 6150SE nForce 430 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000)','ANGLE (Mobile Intel(R) 965 Express Chipset Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (AMD Radeon HD 6310 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Graphics Media Accelerator 3600 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (AMD Radeon HD 6320 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) G41 Express Chipset)','ANGLE (ATI Mobility Radeon HD 5470 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q45/Q43 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 310M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G41 Express Chipset Direct3D9 vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 45 Express Chipset Family (Microsoft Corporation - WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 440 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4300/4500 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7310 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics)','ANGLE (Intel(R) 4 Series Internal Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon(TM) HD 6480G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 3200 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G41 Express Chipset (Microsoft Corporation - WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 210 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 630 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7340 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) 82945G Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 430 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 7025 / NVIDIA nForce 630a Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q35 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) HD Graphics 4600 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7520G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD 760G (Microsoft Corporation WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 220 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9500 GT Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9 vs_3_0 ps_3_0)','ANGLE (Intel(R) Graphics Media Accelerator HD Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9800 GT Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GTX 550 Ti Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (AMD M880G with ATI Mobility Radeon HD 4250 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 650 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Mobility Radeon HD 5650 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4200 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7700 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family)','ANGLE (Intel(R) 82945G Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (SiS Mirage 3 Graphics Direct3D9Ex vs_2_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 430)','ANGLE (AMD RADEON HD 6450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon 3000 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) 4 Series Internal Chipset Direct3D9 vs_3_0 ps_3_0)','ANGLE (Intel(R) Q35 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 220 Direct3D9 vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7640G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD 760G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 640 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9200 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 610 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6290 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Mobility Radeon HD 4250 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 8600 GT Direct3D9 vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 5570 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G45/G43 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4600 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro NVS 160M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 3000)','ANGLE (NVIDIA GeForce G100)','ANGLE (AMD Radeon HD 8610G + 8500M Dual Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 4 Series Express Chipset Family Direct3D9 vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 7025 / NVIDIA nForce 630a (Microsoft Corporation - WDDM) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (AMD RADEON HD 6350 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 5450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9500 GT)','ANGLE (AMD Radeon HD 6500M/5600/5700 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 965 Express Chipset Family)','ANGLE (NVIDIA GeForce 8400 GS Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Direct3D9 vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 560 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 620 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 660 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon(TM) HD 6520G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 240 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 8240 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro NVS 140M)','ANGLE (Intel(R) Q35 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)']
        if phoneOs == 'iPhone':
          webgl_replace['37446'] = 'Apple GPU'
        else:
          webgl_replace['37446'] = list_vgas[random.randint(0, len(list_vgas) - 1)]
        list_es = ["WebGL 2.0 (OpenGL ES 3.0 Chromium)"]
        list_glsl = ["WebGL GLSL ES (OpenGL Chromium)","WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)"]
        webgl_replace['7938'] = list_es[random.randint(0, len(list_es) - 1)]
        webgl_replace['35724'] = list_glsl[random.randint(0, len(list_glsl) - 1)]
        if phoneOs == 'iPhone':
          gpu_vendor = "Apple Computer, Inc."
        else:
          gpu_vendor = "Google Inc. (ATI Technologies Inc.)"
        webgl_replace['37445'] = gpu_vendor 
        profile_dict['profile_webgl'] = json.dumps(webgl_replace)
        profile_dict['profile_name'] = ''
        # profile_dict['profile_user_agent'] = ''
        # if not phoneOs:
        list_os = ['Window', 'Mac OS X', 'Linux', 'Chrome OS']
        comboBoxOS = list_os[random.randint(0, len(list_os)-1)]

          
        self.list_cpu = ["2","4","6","8","10"]
        
        self.list_screen_resolution = ['1920x1200','1920x1080','1536x864','1440x900','1366x768','1280x720']
        
        self.list_chrome_version = ["109.0.5414.75","109.0.0.0", "107.0.0.0","107.0.5304.88","107.0.5304.66", "106.0.5249.91","105.0.5195.125","105.0.0.0","105.0.5195.136","104.0.5112.79","104.0.0.0"]
		         
        self.list_iPhone_resolution = {'iPhone 14 Pro Max':{'resolution':'430x932','scale':'3'},'iPhone 14 Pro':{'resolution':'393x852','scale':'3'}, 'iPhone 14 Plus':{'resolution':'428x926','scale':'3'},'iPhone 14':{'resolution':'390x844','scale':'3'},'iPhone SE 3rd gen':{'resolution':'375x667','scale':'2'},'iPhone 13':{'resolution':'390x844','scale':'3'}, 'iPhone 13 mini':{'resolution':'375x812','scale':'3'},'iPhone 13 Pro Max':{'resolution':'428x926','scale':'3'}, 'iPhone 13 Pro':{'resolution':'390x844','scale':'3'}, 'iPhone 12':{'resolution':'390x844','scale':'3'},'iPhone 12 mini':{'resolution':'375x812','scale':'3'}, 'iPhone 12 Pro Max':{'resolution':'428x926','scale':'3'}, 'iPhone 12 Pro': {'resolution':'390x844','scale':'3'}, 'iPhone SE 2nd gen':{'resolution':'375x667','scale':'2'}, 'iPhone 11 Pro Max':{'resolution':'414x896','scale':'3'}, 'iPhone 11 Pro':{'resolution':'375x812','scale':'3'}, 'iPhone 11':{'resolution':'414x896','scale':'2'}, 'iPhone XR':{'resolution':'414x896','scale':'2'}, 'iPhone XS Max':{'resolution':'414x896','scale':'3'}, 'iPhone XS':{'resolution':'375x812','scale':'3'}, 'iPhone X':{'resolution':'375x812','scale':'3'}}
        
        self.list_apple_ios = ['16_1','15_7','14_8', '13_7']
        
        self.list_android_resolution = {'Samsung Galaxy Z Flip 4':{'resolution':'412 x 1004','scale':'3', 'model':'SM-F721B'},'Samsung Galaxy S9+': {'resolution':'360 x 740','scale':'3', 'model':'SM-G965F'}, 'Samsung Galaxy S9': {'resolution':'360 x 740','scale':'3', 'model':'SM-G960U'}, 'Samsung Galaxy S8+': {'resolution':'360 x 740','scale':'3' , 'model':'SM-G955F'}, 'Samsung Galaxy S8': {'resolution':'360 x 740','scale':'3', 'model':'SM-G950F'}, 'Nexus 6P': {'resolution':'412 x 732','scale':'3', 'model':'Nexus 6P'}, 'Nexus 5X': {'resolution':'412 x 732','scale':'3', 'model':'Nexus 5X'}, 'Google Pixel 4 XL': {'resolution':'412 x 869','scale':'3', 'model': 'Pixel 4 XL'}, 'Google Pixel 4': {'resolution':'412 x 869','scale':'3', 'model': 'Pixel 4'} }
        self.list_android_os = ['9', '10', '11', '12', '13']
        
        AgentOperationOS = ''
        if comboBoxOS == 'Window':
            AgentOperationOS = 'Windows NT 10.0; Win64; x64'
        elif comboBoxOS == 'Mac OS X':
          os_version = self.list_apple_ios[random.randint(0, len(self.list_apple_ios)-1)]
          AgentOperationOS = 'Macintosh; Intel Mac OS X '+ os_version
        elif comboBoxOS == 'Linux':
          AgentOperationOS = 'X11; Linux x86_64'
        else:
          AgentOperationOS = "X11; CrOS x86_64 14909.100.0"
                  
        Agentversion = self.list_chrome_version[random.randint(
              0, len(self.list_chrome_version)-1)]
        if phoneOs == 'iPhone':
          list_phone_os = list(self.list_iPhone_resolution.keys())
          # print(list_phone_os)
          comboBoxOS = list_phone_os[random.randint(0, len(list_phone_os)-1)]
          self.user_header_set = "Mozilla/5.0 (iPhone; CPU iPhone OS 16_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/%s Mobile/15E148 Safari/604.1" % (Agentversion)		
          profile_resolution = self.list_iPhone_resolution[comboBoxOS]['resolution']
        elif phoneOs == 'Android':
          list_phone_os = list(self.list_android_resolution.keys())
          # print(list_phone_os)
          comboBoxOS = list_phone_os[random.randint(0, len(list_phone_os)-1)]
          os_version = self.list_android_os[random.randint(0, len(self.list_android_os)-1)]
          self.user_header_set = "Mozilla/5.0 (Linux; Android %s; %s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Mobile Safari/537.36 TwitterAndroid" % (os_version, self.list_android_resolution[comboBoxOS]['model'], Agentversion)	
          profile_resolution = self.list_android_resolution[comboBoxOS]['resolution']          
        else:
          self.user_header_set = "Mozilla/5.0 (%s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36" % (
                          AgentOperationOS, Agentversion)
        
          profile_resolution = self.list_screen_resolution[random.randint(
              0, len(self.list_screen_resolution)-1)]
        profile_cpu = self.list_cpu[random.randint(
            0, len(self.list_cpu)-1)]
        
        profile_dict['profile_user_agent'] = self.user_header_set
        profile_dict['profile_os'] = comboBoxOS
        profile_dict['profile_resolution'] = profile_resolution
        profile_dict['profile_cpu'] = profile_cpu
        if sock5:
            profile_dict['profile_sock5_details'] = sock5
        elif proxy:
            profile_dict['profile_proxy_details'] = proxy
        else:
            profile_dict['profile_proxy_details'] = ''

        profile_dict['profile_rects'] = round(random.uniform(0.2, 0.35), 5)
        listFonts = ['Arial', 'Calibri', 'Cambria', 'Cambria Math', 'Candara', 'Comic Sans MS', 'Comic Sans MS Bold', 'Comic Sans', 'Consolas', 'Constantia', 'Corbel', 'Courier New', 'Caurier Regular', 'Ebrima', 'Fixedsys Regular', 'Franklin Gothic', 'Gabriola Regular', 'Gadugi', 'Georgia', 'HoloLens MDL2 Assets Regular', 'Impact Regular', 'Javanese Text Regular', 'Leelawadee UI', 'Lucida Console Regular', 'Lucida Sans Unicode Regular', 'Malgun Gothic', 'Microsoft Himalaya Regular', 'Microsoft JhengHei', 'Microsoft JhengHei UI', 'Microsoft PhangsPa', 'Microsoft Sans Serif Regular', 'Microsoft Tai Le', 'Microsoft YaHei', 'Microsoft YaHei UI', 'Microsoft Yi Baiti Regular', 'MingLiU_HKSCS-ExtB Regular', 'MingLiu-ExtB Regular', 'Modern Regular', 'Mongolia Baiti Regular', 'MS Gothic Regular', 'MS PGothic Regular', 'MS Sans Serif Regular', 'MS Serif Regular', 'MS UI Gothic Regular', 'MV Boli Regular', 'Myanmar Text', 'Nimarla UI', 'Myanmar Tet', 'Nirmala UI', 'NSimSun Regular', 'Palatino Linotype', 'PMingLiU-ExtB Regular', 'Roman Regular', 'Script Regular', 'Segoe MDL2 Assets Regular', 'Segoe Print', 'Segoe Script', 'Segoe UI', 'Segoe UI Emoji Regular', 'Segoe UI Historic Regular', 'Segoe UI Symbol Regular', 'SimSun Regular', 'SimSun-ExtB Regular', 'Sitka Banner', 'Sitka Display', 'Sitka Heading', 'Sitka Small', 'Sitka Subheading', 'Sitka Text', 'Small Fonts Regular', 'Sylfaen Regular', 'Symbol Regular', 'System Bold', 'Tahoma', 'Terminal', 'Times New Roman', 'Trebuchet MS', 'Verdana', 'Webdings Regular', 'Wingdings Regular', 'Yu Gothic', 'Yu Gothic UI', 'Arial Black', 'Calibri Light', 'Courier', 'Fixedsys', 'Franklin Gothic Medium', 'Gabriola', 'HoloLens MDL2 Assets', 'Impact', 'Javanese Text', 'Leelawadee UI Semilight', 'Lucida Console', 'Lucida Sans Unicode', 'MS Gothic', 'MS PGothic', 'MS Sans Serif', 'MS Serif', 'MS UI Gothic', 'MV Boli', 'Malgun Gothic Semilight', 'Marlett', 'Microsoft Himalaya', 'Microsoft JhengHei Light', 'Microsoft JhengHei UI Light', 'Microsoft New Tai Lue', 'Microsoft PhagsPa', 'Microsoft Sans Serif', 'Microsoft YaHei Light', 'Microsoft YaHei UI Light', 'Microsoft Yi Baiti', 'MingLiU-ExtB', 'MingLiU_HKSCS-ExtB', 'Modern', 'Mongolian Baiti', 'NSimSun', 'Nirmala UI Semilight', 'PMingLiU-ExtB', 'Roman', 'Script', 'Segoe MDL2 Assets', 'Segoe UI Black', 'Segoe UI Emoji', 'Segoe UI Historic', 'Segoe UI Light', 'Segoe UI Semibold', 'Segoe UI Semilight', 'Segoe UI Symbol', 'SimSun', 'SimSun-ExtB', 'Small Fonts', 'Sylfaen', 'Symbol', 'System', 'Webdings', 'Wingdings', 'Yu Gothic Light', 'Yu Gothic Medium', 'Yu Gothic UI Light', 'Yu Gothic UI Semibold', 'Yu Gothic UI Semilight', 'Arial Narrow', 'Arial Unicode MS', 'Book Antiqua', 'Bookman Old Style', 'Century', 'Century Gothic', 'Century Schoolbook', 'Garamond', 'Helvetica', 'Lucida Bright', 'Lucida Calligraphy', 'Lucida Fax', 'Lucida Handwriting', 'Lucida Sans', 'Lucida Sans Typewriter', 'Monotype Corsiva', 'MS Outlook', 'MS Reference Sans Serif', 'Times', 'Wingdings 2', 'Wingdings 3', 'default', 'sans-serif', 'serif', 'monospace', 'cursive', 'fantasy', 'inherit', 'auto', 'Brush Script MT', 'Broadway', 'Bell MT', 'Berlin Sans FB', 'Blackadder ITC', 'Curlz MT', 'Elephant', 'Engravers MT', 'Goudy Old Style', 'Minion Pro', 'Papyrus', 'Wide Latin', 'Snap ITC', 'Stencil', 'Old English Text MT', 'Ubuntu', 'Ubuntu Mono', 'Terminus Font', 'Terminus', 'Ubuntu Mono 13', 'Ubuntu Mono Regular', 'Apple Braille Outline 6 Dot', 'Apple Braille Outline 8 Dot', 'Apple Braille Pinpoint 6 Dot', 'Apple Braille Pinpoint 8 Dot', 'Apple Braille', 'Apple Symbols', 'AppleGothic', 'AquaKana', 'Geeza Pro Bold', 'Geeza Pro', 'Geneva', 'HelveLTMM', 'Helvetica LT MM', 'HelveticaNeue', 'Hiragino Kaku Gothic ProN W3', 'Hiragino Kaku Gothic ProN W6', 'Hiragino Mincho ProN W3', 'Hiragino Mincho ProN W6', 'Keyboard', 'LastResort', 'LiHei Pro', 'LucidaGrande', 'Menlo', 'Monaco', 'STHeiti', 'STHeiti Light', 'STXihei', 'Thonburi', 'ThonburiBold', 'Times LT MM', 'TimesLTMM', 'ZapfDingbats', 'AmericanTypewriter', 'Andale Mono', 'Apple Chancery', 'Apple LiGothic Medium', 'Arial Bold Italic', 'Arial Bold', 'Arial Italic', 'Arial Narrow Bold Italic', 'Arial Narrow Bold', 'Arial Narrow Italic', 'Arial Rounded Bold', 'Arial Unicode', 'Baskerville', 'BigCaslon', 'Brush Script', 'Chalkboard', 'Chalkduster', 'Cochin', 'Copperplate', 'Courier New Bold Italic', 'Courier New Bold', 'Courier New Italic', 'Didot', 'Futura', 'Georgia Bold Italic', 'Georgia Bold', 'Georgia Italic', 'GillSans', 'Hei', 'Herculanum', 'Hiragino Kaku Gothic Pro W3', 'Hiragino Kaku Gothic Pro W6', 'Hiragino Kaku Gothic Std W8', 'Hiragino Kaku Gothic StdN W8', 'Hiragino Maru Gothic Pro W4', 'Hiragino Maru Gothic ProN W4', 'Hiragino Mincho Pro W3', 'Hiragino Mincho Pro W6', 'Hoefler Text', 'Hoefler Text Ornaments', 'Kai', 'MarkerFelt', 'Optima', 'Osaka', 'OsakaMono', 'Skia', 'Tahoma Bold', 'Times New Roman Bold Italic', 'Times New Roman Bold', 'Times New Roman Italic', 'Trebuchet MS Bold Italic', 'Trebuchet MS Bold', 'Trebuchet MS Italic', 'Verdana Bold Italic', 'Verdana Bold', 'Verdana Italic', 'Zapfino', 'Aharoni Bold', 'Andalus Regular', 'Angsana New', 'Angsana New Bold', 'Angsana New Italic', 'Angsana New Bold Italic', 'AngsanaUPC', 'AngsanaUPC Bold', 'AngsanaUPC Italic', 'AngsanaUPC Bold Italic', 'Aparajita', 'Aparajita Bold', 'Aparajita Italic', 'Aparajita Bold Italic', 'Arabic Typesetting Regular', 'Arial Unicode MS Regular', 'Batang', 'BatangChe', 'Browallia New', 'Browallia New Bold', 'Browallia New Italic', 'Browallia New Bold Italic', 'BrowalliaUPC', 'BrowalliaUPC Bold', 'BrowalliaUPC Italic', 'BrowalliaUPC Bold Italic', 'Calibri Bold', 'Calibri Italic', 'Calibri Bold Italic', 'Cambria Bold', 'Cambria Italic', 'Cambria Bold Italic', 'Candara Bold', 'Candara Italic', 'Candara Bold Italic', 'Consolas Bold', 'Consolas Italic', 'Consolas Bold Italic', 'Constantia Bold', 'Constantia Italic', 'Constantia Bold Italic', 'Corbel Bold', 'Corbel Italic', 'Corbel Bold Italic', 'Cordia New', 'Cordia New Bold', 'Cordia New Italic', 'Cordia New Bold Italic', 'CordiaUPC', 'CordiaUPC Bold', 'CordiaUPC Italic', 'CordiaUPC Bold Italic', 'DFKai-SB', 'DaunPenh', 'David', 'David Bold', 'DilleniaUPC', 'DilleniaUPC Bold', 'DilleniaUPC Italic', 'DilleniaUPC Bold Italic', 'DokChampa', 'Dotum', 'DotumChe', 'Ebrima Bold', 'Estrangelo Edessa', 'EucrosiaUPC', 'EucrosiaUPC Bold', 'EucrosiaUPC Italic', 'EucrosiaUPC Bold Italic', 'Euphemia', 'FangSong', 'FrankRuehl', 'Franklin Gothic Medium Italic', 'FreesiaUPC', 'FreesiaUPC Bold', 'FreesiaUPC Italic', 'FreesiaUPC Bold Italic', 'Gautami', 'Gautami Bold', '& Georgia Bold Italic', 'Gisha', 'Gisha Bold', 'Gulim', 'GulimChe', 'Gungsuh', 'GungsuhChe', 'IrisUPC', 'IrisUPC Bold', 'IrisUPC Italic', 'IrisUPC Bold Italic', 'Iskoola Pota', 'IskoolaPota Bold', 'JasmineUPC', 'JasmineUPC Bold', 'JasmineUPC Italic', 'JasmineUPC Bold Italic', 'KaiTi', 'Kalinga', 'Kalinga Bold', 'Kartika', 'Kartika Bold', 'Khmer UI', 'Khmer UI Bold', 'KodchiangUPC', 'KodchiangUPC Bold', 'KodchiangUPC Italic', 'KodchiangUPC Bold Italic', 'Kokila', 'Kokila Bold', 'Kokila Italic', 'Kokila Bold Italic', 'Lao UI', 'Lao UI Bold', 'Latha', 'Latha Bold', 'Leelawadee', 'Leelawadee Bold', 'Levenim MT', 'Levenim MT Bold', 'LilyUPC', 'LilyUPC Bold', 'LilyUPC Italic', 'LilyUPC Bold Italic', 'MS Mincho', 'MS PMincho', 'Malgun Gothic Bold', 'Mangal', 'Mangal Bold', 'Meiryo UI', 'Meiryo UI Bold', 'Meiryo UI Italic', 'Meiryo UI Bold Italic', 'Meiryo', 'Meiryo Bold', 'Meiryo Italic', 'Meiryo Bold Italic', 'Microsoft JhengHei Bold', 'Microsoft New Tai Lue Bold', 'Microsoft PhagsPa Bold', 'Microsoft Tai Le Bold', 'Microsoft Uighur', 'Microsoft YaHei Bold', 'MingLiU', 'MingLiU_HKSCS', 'Miriam', 'Miriam Fixed', 'MoolBoran', 'Narkisim', 'Nyala', 'PMingLiU', 'Palatino Linotype Bold', 'Palatino Linotype Italic', 'Palatino Linotype Bold Italic', 'Plantagenet Cherokee', 'Raavi', 'Raavi Bold', 'Rod', 'Sakkal Majalla', 'Sakkal Majalla Bold', 'Segoe Print Bold', 'Segoe Script Bold', 'Segoe UI Bold', 'Segoe UI Italic', 'Segoe UI Bold Italic', 'Shonar Bangla', 'Shonar Bangla Bold', 'Shruti', 'Shruti Bold', 'SimHei', 'Simplified Arabic', 'Simplified Arabic Bold', 'Simplified Arabic Fixed', ' Times New Roman Bold', 'Traditional Arabic', 'Traditional Arabic Bold', 'Tunga', 'Tunga Bold', 'Utsaah', 'Utsaah Bold', 'Utsaah Italic', 'Utsaah Bold Italic', 'Vani', 'Vani Bold', 'Vijaya', 'Vijaya Bold', 'Vrinda', 'Vrinda Bold']
        fonts_max = random.randint(200, len(listFonts)-1)
        fonts_min = random.randint(0, 150)
        listUse = listFonts[fonts_min:fonts_max]
        profile_dict['profile_font'] = str(listUse)
        
        profile_dict['profile_start_url'] = ''
        return profile_dict

    def send_keys_like_human(self,elem, text):
        self.driver.execute_script("arguments[0].value='';", elem)
        self.driver.execute_script("arguments[0].focus();", elem)
        actions = ActionChains(self.driver)
        for character in text:
            # elem.send_keys(character)
            # elem.send_keys(character)
            # print(character)
            # actions.perform()
            actions = ActionChains(self.driver)
            # actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            # actions.w3c_actions.pointer_action.move_to(element)
            # actions.w3c_actions.pointer_action.pointer_down()
            # actions.w3c_actions.pointer_action.pointer_up()   
            actions.send_keys(character)
            actions.perform()  
            time.sleep(random.uniform(0.05, 0.2))

    def scroll_like_human(self, scoll_times=0, star_review=False):
        try:
          footer_y = self.driver.execute_script("return document.body.scrollHeight")
        except:
          footer_y = random.uniform(300, 1000)
        # print('footer_y====', footer_y)
        if not scoll_times:
            scoll_times = random.randint(5, 10)
        scooled = 0
        last_pos = 0
        total_y = 0
        while scooled < scoll_times:
            random_pos = random.uniform(300, 1000)
            random_action = random.randint(-1, 3)
            # print('next pos==',last_pos , int(last_pos)-int(random_pos))
            scroll_pos = self.driver.execute_script(
                "return window.scrollY")

            if random_action <= 0 or total_y >= footer_y or scroll_pos >= footer_y-random_action:
                # print('===am==', -1 * int(random_pos))
                down_scool = -1 * int(random_pos)
            else:
                down_scool = int(random_pos)
            # print('last_pos==',int(last_pos), int(down_scool))
            actions = ActionChains(self.driver)
            actions.scroll_by_amount(0, int(down_scool))
            actions.perform()

            time.sleep(random.uniform(0.3, 0.8))
            if star_review:
                self.click_on_random_star()
            # print('clicked===' + str(scooled))

            last_pos = down_scool
            total_y += down_scool
            scooled += 1
            time.sleep(0.1)
      
    def select_options(self,element,value):
      select = Select(element)
      # print('====',select)
      select.select_by_value(value) 
            
    def move_to_and_click(self, element):
        self.driver.execute_script("arguments[0].focus();", element)
        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        actions.w3c_actions.pointer_action.move_to(element)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.pointer_up()
        actions.perform()
        
    def click_and_send_keys(self, element, keys):
        self.driver.execute_script("arguments[0].value='';", element)
        self.driver.execute_script("arguments[0].focus();", element)
        actions = ActionChains(self.driver)
        actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
        # actions.w3c_actions.pointer_action.move_to(element)
        # actions.w3c_actions.pointer_action.pointer_down()
        # actions.w3c_actions.pointer_action.pointer_up()   
        actions.send_keys(keys)
        actions.perform()   
           
    def click_random_offset_element(self, element, context=False, move=False):
        # print(self.mun_browser.get_window_position())
        # print(element.location, element.rect)
       
        # desired_y = (element.size['height'] / 2) + element.location['y']
        # current_y = (self.driver.execute_script('return window.innerHeight') / 2) + self.mun_bdriverrowser.execute_script('return window.pageYOffset')
        # scroll_y_by = desired_y - current_y
        self.driver.switch_to.default_content()
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'});", element)

        elem_left_bound = element.location.get('x')
        elem_top_bound = element.location.get('y')
        elem_width = element.size.get('width')
        elem_height = element.size.get('height')
        print(elem_left_bound, elem_top_bound, elem_width, elem_height)
        left_random_offset = random.uniform(elem_width/3,elem_width/1.5)
        top_random_offset = random.uniform(elem_height/3,elem_height/1.5)
        # print('elem_width:',elem_width,'elem_height:',elem_height, 'left_random_offset',left_random_offset,'top_random_offset',top_random_offset)
        random_left_offset = elem_left_bound + left_random_offset#(elem_width/2) #+ left_random_offset
        random_top_offset = elem_top_bound + top_random_offset#(elem_height/2) #+ top_random_offset
        
        actions = ActionChains(self.driver)
        actions.reset_actions()
        win_upper_bound = self.driver.execute_script('return window.pageYOffset')
        win_left_bound = self.driver.execute_script('return window.pageXOffset')

        start_x = random_left_offset - win_left_bound
        start_y = random_top_offset - win_upper_bound
        end_x = start_x
        end_y = start_y
        time.sleep(random.uniform(0.3,1))
        
        if self.phoneSetting:
            print('win_bound==', win_left_bound, win_upper_bound)
            print('==phone click==', start_x, start_y)
            actions.w3c_actions = ActionBuilder(self.driver, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            actions.w3c_actions.pointer_action.move_by(start_x, start_y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.pointer_up()
            # actions.w3c_actions.pointer_action.move_to_location(end_x, end_y)
            # actions.w3c_actions.pointer_action.release()
            actions.perform()
        else:
            try:
                if move:
                    actions.move_by_offset(random_left_offset - win_left_bound, random_top_offset-win_upper_bound).perform()
                    actions.pause(random.uniform(0.5,1))
                else:
                    if context:
                        actions.move_by_offset(random_left_offset - win_left_bound, random_top_offset-win_upper_bound).context_click().perform()
                    else:
                        actions.move_by_offset(random_left_offset - win_left_bound, random_top_offset-win_upper_bound).click().perform()
            except Exception as e:
                print('===error', e)
                # self.click_random_offset_element(element,context, move)
                return
        # 'sau khi click ko ton tai element'
        actions.reset_actions()


        return True
        # assert "resultPage.html" in driver.current_url




if __name__ == "__main__":

    def read_cookies(p='cookies_test.txt'):
        cookies = []
        with open(p, 'r') as f:
            for e in f:
                e = e.strip()
                if e.startswith('#'): continue
                k = e.split('\t')
                if len(k) < 3: continue	# not enough data
                # with expiry
                print(k[0][1:])
                cookies.append(json.dumps({'domain':k[0],'secure':k[1], 'httpOnly':k[3],'path':k[2],'name': k[-2], 'value': k[-1], 'expiry': int(k[-3])}))
        return cookies  
    list_coookies = read_cookies()
    # print(list_coookies)
    br = Rqbrowser()
    # br.open('http://httpbin.org/cookies/set?k1=v1&k2=v2')
    # ck = br.add_cookies_to_header()
    # print(ck)
    mun_browser = MunAntiBrowser()
    driver = mun_browser.open_random_driver(sock5='Bproxy2023-rotate:Hanoi2023@p.webshare.io:80')
    # profile_info  = mun_browser.create_random_profile(sock5='192.168.0.114:30000', phoneOs='Android')
    # inject_data = mun_browser.get_inject_data()
    # # print(profile_info)
    # driver = mun_browser.setting(inject_str=inject_data,
    #                     profileInfo=profile_info, onetime=False, type_browser='Chrome')
    
    # mun_browser.set_cookies('cookies_test.txt')
    # print(mun_browser.get_cookies())
    # mun_browser.request_captcha()
    
    # driver.get("https://www.google.com")
    # for cookies in list_coookies:
    #   driver.add_cookie(json.loads(cookies))
    # time.sleep(100)
    # print('get_cookies==',driver.get_cookies() )
    # time.sleep(10000)
    # Barbip421|poochie1|JUAN|FERNANDEZ|2408 NE 41ST PL|HOMESTEAD|FL|33033|

    # frederickadi|erick86|FREDERICK|ADI|39547 GALLAUDET DR APT 3013|FREMONT|CA|94538|6263213857
    # 4762 57AVE N|SAINT PETERSBURG|FL|33714
    # lgrubich|leander|LEAH CHAPUT|12619 FERGUS ST NE|MINNEAPOLIS|MN|55449|
    #Bryan|Lloyd|3600 Winthrop Dr Apt 4101||Lexington|KY|40514-1798|
    listbilling = ''
    list_address_drop = 'frederickadi|erick86|FREDERICK|ADI|39547 GALLAUDET DR APT 3013|FREMONT|CA|94538|6263213857'
    timeout = 30
    #socket.setdefaulttimeout(timeout)
    #socks.setdefaultproxy(socks.SOCKS5, '127.0.0.1', 9951)
    #socket.socket = socks.socksocket
    # Magic!

    # browser = Mechanizebrowser()
    # # browser.link_host = 'whoer.net'
    # # browser.link_origin = 'http://whoer.net'
    # browser.set_proxies(sock5='127.0.0.1:9951')
    # r = browser.open('https://api.ipify.org/?format=json')
    # print (r.read())
    # #browser = Rqbrowser()
    # #browser = CurlBrowser()
    # def test(socks):
    #     browser = Rqbrowser()
    #     browser.link_host = 'whoer.net'
    #     browser.link_origin = 'http://whoer.net'
    #     #browser.quite = True
    #     browser.set_proxies(sock5=socks)
    #     html = browser.open('http://whoer.net')
    #     #html = r.read()
    #     c = open('dien.html', 'w')
    #     c.write(html)
    #     mm = re.findall(r'ipadotted">(.+?)</div>', html);
    #     print (mm);
    #     m = re.search(r'dns\?domain=(\w+\.br)', html);
    #     try:
    #         browser.open('http://%s.whoer.net/css/null.css' % (m.group(1)));
    #     except:
    #         pass;
    #     for ti in range(3):
    #         html = browser.open('http://whoer.net/' + m.group(0));
    #         #html = r.read()
    #         print (html)
    #         if html.strip(): break;
    #         time.sleep(1);

    # import threading

    # listport = [1080]
    # for line in listport:
    #     print line
    #     t = threading.Thread(target=test, args=('127.0.0.1:1080',))
    #     t.start()
    #result = app.exec_();
    print ('done')

