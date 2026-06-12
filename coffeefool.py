#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time,os;
from PIL import Image, ImageMath
import json, urllib, base64, mybrowser,captcha2upload
from urllib.parse import urlparse, parse_qsl
import munantiapi, mybrowser
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput


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


class Coffeefool:
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



    def add_header(self, link_refer, XMLHttpRequest=None, extraHeader={}):
        self.browser.add_header(link_refer, XMLHttpRequest=XMLHttpRequest, extraHeader=extraHeader)

    def fixHTML(self, html):
        return html.replace("'", '"');


    def fake_socks(self, sock):
        self.browser.set_proxies(sock5=sock)



    def add_to_cart(self, link_add_to_cart):
        current_url= self.driver.current_url
        print(current_url)
        if str(current_url).find('/order-confirmation') != -1 or str(current_url).find('iphey') != -1 or str(current_url).find('new-tab-page') != -1:
            link_add_to_cart = 'https://coffeefool.com/fools-english-toffee/'
            r = self.driver.get(link_add_to_cart)
            element_present = EC.presence_of_element_located((By.XPATH, "//div[@id='bsub-widget']"))
            WebDriverWait(self.driver, 30).until(element_present) 
                
            element_present = EC.presence_of_element_located((By.XPATH, "//input[@id='form-action-addToCart']"))
            WebDriverWait(self.driver, 30).until(element_present)
            self.driver.implicitly_wait(1)
            list_elements = self.driver.find_elements(By.XPATH, "//input[@id='form-action-addToCart']")  
            if list_elements:
                print(list_elements[0])
                self.mun_browser.click_random_offset_element(list_elements[0])
                return True
        return True
            
      
    def check_confirmation_page(self):
        current_url= self.driver.current_url
        if str(current_url).find('/order-confirmation') != -1:
            return True
        else:
            return  
            
    def check_out(self, checkoutInfo={}):
        print('==go to checkout page==')
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
        # errorModalMessage_elements = self.driver.find_elements(By.XPATH, "//p[@id='errorModalMessage']")
        payment_elements = self.driver.find_elements(By.XPATH, "//button[@id='checkout-payment-continue']")
        if not payment_elements:
            r = self.driver.get('https://coffeefool.com/checkout')

            element_presentcheckout = EC.presence_of_element_located((By.XPATH, "//a[@id='checkout-customer-login']"))
            WebDriverWait(self.driver, 30).until(element_presentcheckout)  
            
            element_present = EC.presence_of_element_located((By.XPATH, "//input[@id='email']"))
            WebDriverWait(self.driver, 30).until(element_present)   
            list_elements = self.driver.find_elements(By.XPATH, "//input[@id='email']")  
            time.sleep(1)
            if list_elements:  
                email_elements = list_elements[0]
                self.mun_browser.click_and_send_keys(email_elements, self.email_chuan)
                element_present = EC.presence_of_element_located((By.XPATH, "//a[@id='checkout-customer-login']"))
                WebDriverWait(self.driver, 30).until(element_present)     
                # time.sleep(2)
                list_elements = self.driver.find_elements(By.XPATH, "//button[@id='checkout-customer-continue']")  
                if list_elements:     
                    self.driver.execute_script("arguments[0].click();", list_elements[0])
            # time.sleep(1) 
            element_present = EC.presence_of_element_located((By.XPATH, "//button[@id='checkout-shipping-continue']"))
            WebDriverWait(self.driver, 30).until(element_present)   
            # print('===input firstNameInput===')  
            list_elements = self.driver.find_elements(By.XPATH, "//input[@id='firstNameInput']")  
            # print(len(list_elements))
            if list_elements:  
                firstName_elements = list_elements[0]
                self.mun_browser.click_and_send_keys(firstName_elements, checkoutInfo['first_name'])
                
            # print('===input lastNameInput===')  
            list_elements = self.driver.find_elements(By.XPATH, "//input[@id='lastNameInput']")  
            if list_elements:  
                lastName_elements = list_elements[0]
                self.mun_browser.click_and_send_keys(lastName_elements, checkoutInfo['last_name'])

            # print('===input addressLine1Input===')  
            list_elements = self.driver.find_elements(By.XPATH, "//input[@id='addressLine1Input']")  
            if list_elements:  
                address_elements = list_elements[0]
                self.mun_browser.click_and_send_keys(address_elements, checkoutInfo['address1'])       


            # print('===input cityInput===')  
            list_elements = self.driver.find_elements(By.XPATH, "//input[@id='cityInput']")  
            if list_elements:  
                city_elements = list_elements[0]
                self.mun_browser.click_and_send_keys(city_elements, checkoutInfo['city'])

    
            # print('===input postCodeInput===')  
            list_elements = self.driver.find_elements(By.XPATH, "//input[@id='postCodeInput']")  
            if list_elements:  
                postcode_elements = list_elements[0]
                self.mun_browser.click_and_send_keys(postcode_elements, checkoutInfo['zipcode'])  
                

            # print('===input countryCodeInput===')  
            list_elements = self.driver.find_elements(By.XPATH, "//select[@id='countryCodeInput']")  
            if list_elements:  
                countryCode_elements = list_elements[0]
                self.mun_browser.select_options(countryCode_elements, 'US')
                # self.mun_browser.move_to_and_click(countryCode_elements)
                # self.mun_browser.click_and_send_keys(postcode_elements, '12345')    
            element_present = EC.presence_of_element_located((By.XPATH, "//select[@id='provinceCodeInput']"))
            WebDriverWait(self.driver, 30).until(element_present)     
            # time.sleep(2)
            list_elements = self.driver.find_elements(By.XPATH, "//select[@id='provinceCodeInput']")  
            if list_elements:   
                provinceCode_elements = list_elements[0]
                self.mun_browser.select_options(provinceCode_elements, checkoutInfo['state'])           
    
            element_present = EC.presence_of_element_located((By.CLASS_NAME, "shippingOption-price"))
            WebDriverWait(self.driver, 30).until(element_present)   

            # print('===input checkout-shipping-continue===')  
            list_elements = self.driver.find_elements(By.XPATH, "//button[@id='checkout-shipping-continue']")   
            if list_elements:      
                while 1:
                    try:
                        payment_elements = self.driver.find_elements(By.XPATH, "//button[@id='checkout-payment-continue']")  
                        # print(len(payment_elements))
                        if payment_elements:
                            break
                        list_elements = self.driver.find_elements(By.XPATH, "//button[@id='checkout-shipping-continue']")  
                        if list_elements:
                            shipping_elements = list_elements[0]
                            self.mun_browser.click_random_offset_element(shipping_elements)
                        else:
                            break
                    except:
                        pass
                    time.sleep(1) 
                    
        print('===checkout-payment-continue===') 
        element_present = EC.presence_of_element_located((By.XPATH, "//button[@id='checkout-payment-continue']"))
        WebDriverWait(self.driver, 30).until(element_present)   
        list_elements = self.driver.find_elements(By.XPATH, "//input[@id='ccNumber']")  
        if list_elements:  
            ccNumber_elements = list_elements[0]

            #ccnumber='4358806409808201',ccmonth='04',ccyear='2030'
            self.mun_browser.click_and_send_keys(ccNumber_elements, checkoutInfo['ccnumber'])
            
        list_elements = self.driver.find_elements(By.XPATH, "//input[@id='ccExpiry']")  
        if list_elements:  
            ccExpiry_elements = list_elements[0]

            self.mun_browser.click_and_send_keys(ccExpiry_elements, checkoutInfo['ccmonth']+checkoutInfo['ccyear'])
            
        list_elements = self.driver.find_elements(By.XPATH, "//input[@id='ccName']")  
        if list_elements:  
            ccName_elements = list_elements[0]

            self.mun_browser.click_and_send_keys(ccName_elements, checkoutInfo['first_name'] + ' ' + checkoutInfo['last_name'])
            
        element_present = EC.presence_of_element_located((By.XPATH, "//button[@id='checkout-payment-continue']"))
        WebDriverWait(self.driver, 30).until(element_present)          
        payment_elements = self.driver.find_elements(By.XPATH, "//button[@id='checkout-payment-continue']")   
        if payment_elements:
            self.driver.execute_script("arguments[0].click();", payment_elements[0])
            
        while 1:
            try:
                errorModalMessage_elements = self.driver.find_elements(By.XPATH, "//p[@id='errorModalMessage']")      
                if errorModalMessage_elements:
                    errorModalMessage_element = errorModalMessage_elements[0]
                    print(errorModalMessage_element.text)
                    return
                elif self.check_confirmation_page():
                    return checkoutInfo
                elif not self.driver.find_elements(By.XPATH, "//button[@id='checkout-payment-continue']"):
                    return
                    
            except:
                pass
            time.sleep(1)


            
        
             

    def check(self, checkoutInfo = {}):
        #MobileSafari/9537.53 CFNetwork/672.0.8 Darwin/14.0.0/3647344
        #Mozilla/5.0 (Windows; U; Windows NT 6.0; en-US) AppleWebKit/528.16 (KHTML, like Gecko) Version/4.0 Safari/528.16/686133
        # header='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Oupeng/10.2.1.86910 Safari/534.30'
        # self.browser = mybrowser.Rqbrowser()
        add_to_cart = self.add_to_cart(link_add_to_cart='https://coffeefool.com/zach-larsons-deadliest-brew/?')
        time.sleep(1)
        # checkoutInfo['ccnumber'] = ccnumber
        # checkoutInfo['ccmonth'] = ccmonth
        # checkoutInfo['ccyear'] = ccyear
        checkout = self.check_out(checkoutInfo)
        if not checkout:
            print('==die==')
            return
        else:
            print('==live==')
            return checkoutInfo
        # self.driver.quit()
        # login = self.site_login(self.email_chuan, password,sock=sock,sock_type=sock_type)
        # if add_to_cart.find('check die') == -1:
        #     check_card = self.check_cc(ccnumber,ccmonth,ccyear,cvv)
        #     return check_card

        # else:
        #     return add_to_cart
        'https://coffeefool.com/checkout/order-confirmation'


def main():


    listbilling = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    list_address_drop = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    #1288375392|FPTgeoEICiYnzs@sbcglobal.net|brynargust@yahoo.com|bryn0320
    #4147098647146372|12|2019|00|Brandon Braun|Address||||||bdogg3000@gmail.com
    #5376280708882256|12|2026
    mun_browser = mybrowser.MunAntiBrowser()
    profile_info  = mun_browser.create_random_profile(phoneOs='iPhone', sock5='192.168.8.108:30000')
    inject_data = mun_browser.get_inject_data()
    # # print(profile_info)
    driver = mun_browser.setting(inject_str=inject_data,
                        profileInfo=profile_info, onetime=False, type_browser='Chrome', pageLoad=False)
    ordervr = Coffeefool(mun_browser=mun_browser, driver=driver)
    checkInfo = {'ccnumber': '5510290071571177', 'ccmonth': '11', 'ccyear': '26', 'ccv': '914', 'id': 2430, 'created': '2022-11-29 09:48:40.420488+0700', 'modified': '2022-11-29 09:48:40.420507+0700', 'created_by': None, 'customer': None, 'modified_by': None, 'type': None, 'owner': None, 'note': None, 'first_name': 'NYUEN', 'last_name': 'BRADY', 'address1': '511 WARM SPRINGS CI', 'address2': None, 'city': 'ROSWELL', 'state': 'GA', 'zipcode': '30075', 'dob': 'Dec 18 1972 12:00AM', 'ssn': '522191897', 'status': 0, 'price': '0.00', 'used': 0}

    ordervr.check(checkInfo)
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
