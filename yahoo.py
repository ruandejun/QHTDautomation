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


class Hotmail:
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

#         browser = await launch(headless=False,args=[
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
                self.browser.add_header('https://google.com')
                r = self.browser.open('https://signup.live.com/signup')
                html = r.text
                url = r.url
                uaidToken = re.search('uaid":"(.+?)"', html).group(1).strip()
                tcxtToken = re.search('tcxt":"(.+?)"', html).group(1).strip()
                apiCanary = re.search('apiCanary":"(.+?)"', html).group(1).strip()
                # extraHeader = {'cookie':'MSFPC=GUID=390282859f0c41f883d00d7c67b6900b&HASH=3902&LV=202105&V=4&LU=1621948552904; logonLatency=LGN01=637772821401584959; amsc=P+bSlxrOWJoPhiqXLeydjrORULpIk1WsmBAWGRteJDRqThgWier17Pfw5Foy9PCOgwDn8sPsFrbUhPKodVIsKF8nvvy1iCRuemxgzeY1x7eM6JxnQTSkwLHO997AscZfdzX94qS8h8aXihXNDNaiZ/VbfsMzyWVrYwJn7VK8Dlt6WiNynA1ybunHE6YWt0EBs32HdtJUdifO69tPGLexB4IFcxmsU/OQ7XDp3pzp0ndncp5sZnWyWEeNdlldRUgWylPTAMul9FCmmIt5RDqtQEaNNJ9mgiyXCDgX7toHcsfoWlsx2YH+sTMrUwAdhDN/:2:3c; fptctx2=taBcrIH61PuCVH7eNCyH0FC0izOzUpX5wN2Z%252b5egc%252f6vt4beP%252fwcBOudveX9HihwB9JGL2ocLzmBBO5r6cLNhI2aGnEt0kWUqhmPmkMxNaF5a86cRaWBEdBFxxAvMdTdSLiq2VMOU1G78ZQDAeZ453oUpFIyC9z1Yicpc33UZlCrnC%252ffjgFfeVLNHm%252fjpIsJg3uOvzSxTrPqP08uqSbICwK%252bOkoSzZEHr9RFJKDgZEqurE3V95ioxt3x8F4SRUtzTfhHR02RsVGQGRo%252bThSkbeoQs3Rgf0XHQVwGb0dgywA%253d; MUID=472d9b16d1ea486ba2ab2ad392cdceb0; clrc={%2219001%22%3a[%22d7PFy/1V%22%2c%22+VC+x0R6%22%2c%22FutSZdvn%22]}','origin':'https://signup.live.com','x-ms-apitransport':'xhr','x-ms-apiversion':'2','Accept':'application/json','Content-Type':'application/json','tcxt':,'uaid':uaidToken,'canary':apiCanary.encode('utf-8').decode( 'unicode-escape'),'uiflvr':'1001','scid':'100118','hpgid':'200639'}
                extraHeader = {
                    "accept": "application/json",
                    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,vi;q=0.6",
                    "cache-control": "no-cache",
                    "canary": apiCanary.encode('utf-8').decode( 'unicode-escape'),
                    "content-type": "application/json",
                    "hpgid": "200639",
                    "pragma": "no-cache",
                    "scid": "100118",
                    "tcxt": tcxtToken.encode('utf-8').decode( 'unicode-escape'),
                    "uaid": uaidToken.encode('utf-8').decode( 'unicode-escape'),
                    "uiflvr": "1001",
                    "x-ms-apitransport": "xhr",
                    "x-ms-apiversion": "2"
                }

                # print(tcxtToken.encode('utf-8').decode( 'unicode-escape'))
                self.browser.add_header(url, extraHeader=extraHeader)
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('check die:socks die')
            return 'check die:socks die'

        # link_request = 'https://login.live.com/GetCredentialType.srf?'+re.search("GetCredentialType\.srf\?(.+?)'", html).group(1).strip()


        # url = new_url.split("?")[1]
        # f = {x[0]: x[1] for x in [x.split("=") for x in url[1:].split("&")]}
        # if not 'uaid' in f.keys():
        #     return 'check die:socks die'
        # uaid = f['uaid']
        link_request = 'https://signup.live.com/API/CheckAvailableSigninNames?lic=1&uaid='+uaidToken
        print(link_request, uaidToken,tcxtToken)
        data_request = {}
        data_request['signInName'] = account
        data_request['uaid'] = uaidToken
        data_request['includeSuggestions'] = 'true'
        data_request['hpgid'] = '200639'
        data_request['scid'] = '100118'
        data_request['uiflvr'] = '1001'
        # data_request['flowToken'] = flowToken
        # data_request['isOtherIdpSupported'] = False
        # data_request['checkPhones'] = False
        # data_request['isRemoteNGCSupported'] = True
        # data_request['isCookieBannerShown'] = False
        # data_request['isFidoSupported'] = False
        # data_request['forceotclogin'] = False
        # data_request['otclogindisallowed'] = False
        # data_request['isExternalFederationDisallowed'] = False
        # data_request['isRemoteConnectSupported'] = False
        # data_request['federationFlags'] = 3
        # data_request['isSignup'] = False
        i = 0
        while i <= 4:
            try:
                # print(self.browser.header)
                # dict = self.browser.header
                # outdict = {}
                # for k, v in dict.items():
                #     outdict[k.lower()] = v.lower()
                # self.browser.header = outdict
                print(self.browser.header)

                r = self.browser.open(link_request,json_data=data_request)
                html = r.text
                if html.find('suggestions') == -1 and html.find('apiCanary') != -1:
                    print('==Not Existed==')
                    return account + '|'
                else:
                    print('==Existed==')
                    return
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('check die:socks die')
            return 'check die:socks die'
        # all_forms = self.browser.selectForm(html)
        # print(all_forms)
        # c = open('dien.html','w', encoding='utf-8')
        # c.write(html)
        # print(html)





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
    ordervr = Hotmail()
    # asyncio.get_event_loop().run_until_complete(ordervr.check_exist('sadassaddasdsaeqwe124@hotmail.com'))
    ordervr.check_exist('tanzelarafiq@hotmail.com')
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
