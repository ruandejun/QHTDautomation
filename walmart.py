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


class Walmart:
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
    def go_login_page_by_google(self):

        # r = self.mun_api.get_key_for_search()
        # key= r['data']
        r = self.driver.get('https://google.com')
        element_present = EC.presence_of_element_located((By.XPATH, "//input[@name='q']"))
        WebDriverWait(self.driver, 30).until(element_present)
        
        q_elements = self.driver.find_elements(By.XPATH, "//input[@name='q']")
        if q_elements:
            # self.click_random_offset_element(q_elements[0])
            time.sleep(random.uniform(0.3,1))
            self.mun_browser.send_keys_like_human(q_elements[0],'walmart login')
            time.sleep(random.uniform(0.3,1))  
            q_elements[0].send_keys(Keys.ENTER)
            # self.scroll_like_human()
            element_present = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//a[@role='presentation' and contains(@href, 'https')]")))
            
            presentation_elements = self.driver.find_elements(By.XPATH, "//a[@role='presentation' and contains(@href, 'https')]")
            
            print('===presentation_elements==')
            if presentation_elements:
                presentation_element = presentation_elements[0]
                self.mun_browser.click_random_offset_element(presentation_element)



    def login(self, email, password):
        print('==login==')
        self.email = email
        self.password = password
        # self.go_login_page_by_google()
        self.driver.get('https://www.walmart.com/')
        
        signin_element = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//div[@data-automation-id='headerSignIn']")))  
        script_run = '''
            function sleep(ms) {
                return new Promise(resolve => setTimeout(resolve, ms));
            }
            function waitForElm(selector) {
                return new Promise(resolve => {
                    if (document.querySelector(selector)) {
                        return resolve(document.querySelector(selector));
                    }

                    const observer = new MutationObserver(mutations => {
                        if (document.querySelector(selector)) {
                            resolve(document.querySelector(selector));
                            observer.disconnect();
                        }
                    });

                    observer.observe(document.body, {
                        childList: true,
                        subtree: true
                    });
                });
            }
            function getElementByXpath(path) {
                return document.evaluate(path, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
            }   
            let element_signin = getElementByXpath("//div[@data-automation-id='headerSignIn']");  
            element_signin.click();
            sleep(1000);
            waitForElm('[link-identifier="Purchase History"]').then((elm) => {
                let element_signin_button = getElementByXpath("//button[contains(text(), 'Sign in or create account')]");  
                element_signin_button.click(); 
            });
            sleep(5000);
            waitForElm('[name="Email Address"]').then((elm) => {
                console.log('====login====')
                let element_signin_button = getElementByXpath("//input[@name='Email Address']");  
                element_signin_button.value='dinhngockhuong@gmail.com'; 
                let signin_button = getElementByXpath("//button[contains(text(), 'Continue')]");  
                signin_button.click();
                
            });
        '''
        # scroll_pos = self.driver.execute_script(
        #         "return window.scrollY")
        self.driver.execute_script(script_run)

        # email_elemnts.send_keys('dinhngockhuong@gmail.com')    
        # print(footer_y, scroll_pos)
        # actions = ActionChains(self.driver)
        # actions.scroll_by_amount(0, int(115.343))
        # actions.perform()
        # self.mun_browser.scroll_like_human()
        # # self.driver.get('https://www.walmart.com/ip/Hyper-Tough-4-Tier-Wire-Shelf-Unit-Black-Capacity-1400-lbs/559553159?athcpid=559553159&athpgid=AthenaHomepageDesktop__gm__1.0&athcgid=null&athznid=SeasonalCampaigns_ae47eef6-d001-4d3f-9175-f997e3f042fe_items&athieid=null&athstid=CS020&athguid=KDbtwofk1wErtL440Yg6YyZX6-ebz5o_5dSf&athancid=null&athena=true&athbdg=L1300')
        
        # signin_element = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH , "//input[@type='email']")))  
           
        # self.driver.execute_script(script_run)
        
        # self.mun_browser.scroll_like_human(scoll_times=1)
        
        # self.mun_browser.click_random_offset_element(signin_element)
        
        # signin_or_create_element = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//button[contains(text(), 'Sign in or create account')]")))  
                
        # self.mun_browser.click_random_offset_element(signin_or_create_element)
        
        # # self.driver.get('https://www.walmart.com/account/login?vid=oaoh&tid=0&returnUrl=%2F')
        # self.mun_browser.scroll_like_human(scoll_times=1)
        # input_email_element = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//input[@name='Email Address']")))   
        # time.sleep(random.uniform(3, 5))
        # self.mun_browser.send_keys_like_human(input_email_element, email)

        # continue_element = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH ,"//button[contains(text(), 'Continue')]")))  
        # time.sleep(random.uniform(3, 5))
        # self.mun_browser.click_random_offset_element(continue_element)             
   

                             


    def check(self, checkoutInfo={}, sock5='', proxy=''):
        checkout = self.check_out(checkoutInfo, sock5=sock5, proxy=proxy)
        if not checkout:
            print('==die==')
            return
        else:
            print('==live==')
            return checkoutInfo

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
    driver = mun_browser.open_random_driver(sock5='', pageLoad=False, phoneOs='')
    ordervr = Walmart(mun_browser=mun_browser,driver=driver)

    ordervr.login(email='dinhngockhuong@gmail.com', password='Hanoi123!@#')
    # link_checkout = ordervr.get_link_checkout(sock5='fwhjolqn-rotate:d3oxuwiomiii@p.webshare.io:80', email='CeparanoMaziya@hotmail.com', password='sjvcvA7ej')
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
