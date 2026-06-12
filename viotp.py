#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time,os;
from PIL import Image, ImageMath
import json, urllib, base64, mybrowser,captcha2upload
from urllib.parse import urlparse, parse_qsl
import asyncio
from pyppeteer import launch
from urllib.parse import urlsplit, parse_qs
# from furl import furl
class FinalForm:
    """ Final form of registration
    """
    form = "form";
    html = "source code";
    captchaControlName = None;
    questionControlName = None;
    captchaImage = None;
    captchaResult = None;
    keyantigate = None;
    questionString = None;
    questionResult = None;
    listLink = None;

    def __init__(self, form, html):
        self.form = form;
        self.html = html;


class Viotp:
    """ Test reg forum
    """


    def __init__(self, token):
        self.token = token
        self.browser = mybrowser.Rqbrowser()

    def add_header(self, link_refer, XMLHttpRequest=None, extraHeader={}):
        self.browser.add_header(link_refer, XMLHttpRequest=XMLHttpRequest, extraHeader=extraHeader)

    def fixHTML(self, html):
        return html.replace("'", '"');

    def fake_socks(self, sock):
        self.browser.set_proxies(sock5=sock)

    def get_phone_number(self,serviceID):
        print('==get_phone_number==')
        #{"phone_number":"987654321","balance":50000,"request_id":"122314","re_phone_number":"84987654321","countryISO":"VN","countryCode":"84"}}
        request_url = 'https://api.viotp.com/request/getv2?token='+self.token+'&serviceId='+serviceID
        r = self.browser.open(request_url)
        html_json = r.json()
        return html_json
    def get_otp_code(self, sessionID):
        print('==')
        request_url ='https://api.viotp.com/session/getv2?requestId='+str(sessionID)+'&token='+ self.token
        r = self.browser.open(request_url)
        html_json = r.json()
        return html_json        
def main():

    ordervr = Viotp()


if __name__ == "__main__":
    sys.exit(main())
