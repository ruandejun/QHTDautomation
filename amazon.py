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
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions import interaction
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

# from selenium.webdriver.common.touch_actions import TouchActions
# from selenium.webdriver import Proxy 
import munantiapi, munemail, viotp
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


class Amazon:
    """ Test reg forum
    """


    def __init__(self,mun_browser=None, orderfinalForm=[], updatestatus='update',captcha_queue=None, mobile=False, antidetectQueQue=None, statusqueue=None):
        self.updatestatus = updatestatus
        self.orderfinalForm = orderfinalForm;

        # ua.set_debug_responses(False)
        self.captcha_queue = captcha_queue;
        self.statusqueue = statusqueue
        self.mun_browser  = mun_browser
        
        self.browser = mybrowser.Rqbrowser()
        self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'
        self.mun_api = munantiapi.MunAntiApi()
        self.mobile = mobile
        self.phoneApi = None

    def add_header(self, link_refer, XMLHttpRequest=None, extraHeader={}):
        self.browser.add_header(link_refer, XMLHttpRequest=XMLHttpRequest, extraHeader=extraHeader)

    def fixHTML(self, html):
        return html.replace("'", '"');
    def check_in_google_site(self):
        current_url= self.mun_browser.current_url
        if current_url.find('/google.com') != -1:
            return True
        else:
            return
    def go_home_page_by_google(self, extraKey=''):
        clicked = 0
        while clicked <= random.randint(2,5):
            try:
                r = self.mun_api.get_key_for_search()
                key= r['data']
                r = self.mun_browser.get('https://google.com')
                element_present = EC.presence_of_element_located((By.XPATH, "//input[@name='q']"))
                WebDriverWait(self.mun_browser, 30).until(element_present)
                
                q_elements = self.mun_browser.find_elements(By.XPATH, "//input[@name='q']")
                if q_elements:
                    # self.click_random_offset_element(q_elements[0])
                    time.sleep(random.uniform(0.3,1))
                    self.send_keys_like_human(key+' '+extraKey, q_elements[0])
                    time.sleep(random.uniform(0.3,1))  
                    q_elements[0].send_keys(Keys.ENTER)
                    self.scroll_like_human()
                    presentation_elements = self.mun_browser.find_elements(By.XPATH, "//div[@role='link']")
                    print('===presentation_elements==')
                    if presentation_elements:
                        presentation_element = presentation_elements[random.randint(0, len(presentation_elements)-1)]
                        self.scroll_like_human(element=presentation_element)
                        try:
                            self.click_random_offset_element(presentation_element)
                            if not self.check_in_google_site():
                                self.mun_browser.back()
                        except:
                            continue
                    if extraKey:
                        return True
            except:
                continue
            clicked+=1
        self.go_home_page_by_google(extraKey='amazon')        
        
    def fake_socks(self, sock):
        self.browser.set_proxies(sock5=sock)

    def check_exist(self, account, sock='',sock_type=''):
        if sock and sock_type == 'socks':
            self.browser.set_proxies(sock5=sock)
        elif sock and sock_type == 'proxy':
            self.browser.set_proxies(proxy=sock)
        i = 0
        while i <= 4:
            try:

                self.browser.add_header('https://google.com')
                r = self.browser.open('https://www.amazon.com/ap/signin?openid.pape.max_auth_age=0&openid.return_to=https%3A%2F%2Fwww.amazon.com%2F%3Fref_%3Dnav_ya_signin&openid.identity=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.assoc_handle=usflex&openid.mode=checkid_setup&openid.claimed_id=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0%2Fidentifier_select&openid.ns=http%3A%2F%2Fspecs.openid.net%2Fauth%2F2.0&')
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


        all_forms = self.browser.selectForm(html)
        login_form = None
        action_link = None
        for form in all_forms:
            input_form = self.browser.getInputForm(form)

            if 'email' in input_form:
                login_form = input_form
                action_link = self.browser.getActionUrl(form)
                break
            # print(input_form)
        # print(action_link,login_form)
        login_form['email'] = account
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(action_link, data=login_form)
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
        if html.find('We cannot find an account with that email address') != -1:
            print('==Not Existed==')
            return
        elif html.find('An error occurred when we tried to process your request') != -1:
            print('check die:socks die')
            return 'check die:socks die'
        elif html.find('id="ap_password"') != -1:
            print('==Existed==')
            return account+'|'
        else:
            print('check die:socks die')
            return 'check die:socks die'

    def site_login(self,email,password, sock='',order=False,sock_type=''):
        print('Logged to your account')
        return email.strip() + '|' + password.strip()

    def search_by_key_word(self, key_search):
        if self.mobile:
            list_elements = self.mun_browser.find_elements(By.ID, "nav-search-keywords")   
        else:
            list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='twotabsearchtextbox']")   
        if list_elements:
            search_box = list_elements[0]
            # time.sleep(3)
            print('===trying search===', key_search)
            
            self.click_random_offset_element(search_box)
            self.send_keys_like_human(key_search, search_box)
            search_box.send_keys(Keys.ENTER)
            return True
        else:
            self.go_to_homepage()
            return
    
    def element_in_viewport(self, driver, elem):
        elem_left_bound = elem.location.get('x')
        elem_top_bound = elem.location.get('y')
        elem_width = elem.size.get('width')
        elem_height = elem.size.get('height')
        elem_right_bound = elem_left_bound + elem_width
        elem_lower_bound = elem_top_bound + elem_height

        win_upper_bound = driver.execute_script('return window.pageYOffset')
        win_left_bound = driver.execute_script('return window.pageXOffset')
        win_width = driver.execute_script('return document.documentElement.clientWidth')
        win_height = driver.execute_script('return document.documentElement.clientHeight')
        win_right_bound = win_left_bound + win_width
        win_lower_bound = win_upper_bound + win_height

        return all((win_left_bound <= elem_left_bound,
                    win_right_bound >= elem_right_bound,
                    win_upper_bound <= elem_top_bound,
                    win_lower_bound >= elem_lower_bound)
                )
    
    def random_move_and_click(self):
        self.scroll_like_human()
        win_upper_bound = 0
        win_left_bound = 0
        
        win_width = self.mun_browser.execute_script('return document.documentElement.clientWidth')
        win_height = self.mun_browser.execute_script('return document.documentElement.clientHeight')
        win_right_bound = win_left_bound + win_width
        win_lower_bound = win_upper_bound + win_height 

        actions = ActionChains(self.mun_browser)
        actions.reset_actions()
        print(random.uniform(win_left_bound,win_right_bound),random.uniform(win_upper_bound,win_lower_bound))
        start_x = random.uniform(win_left_bound,win_right_bound)
        start_y = random.uniform(win_upper_bound,win_lower_bound)
        end_x = start_x
        end_y = start_y
        if self.mobile:
            actions.w3c_actions = ActionBuilder(self.mun_browser, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
            actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
            actions.w3c_actions.pointer_action.pointer_down()
            actions.w3c_actions.pointer_action.pause(2)
            actions.w3c_actions.pointer_action.move_to_location(end_x, end_y)
            actions.w3c_actions.pointer_action.release()
            actions.perform()
            print('==random_move_and_touch==')
        else:
            try:
                print('==random_move_and_click==')
                actions.move_by_offset(random.uniform(win_left_bound,win_right_bound),random.uniform(win_upper_bound,win_lower_bound))
                actions.click()
                actions.perform()
            except Exception as e:
                print('==error==', e)
                self.random_move_and_click()
        
    def got_to_site_by_url(self):
        r = self.mun_browser.get('https://amazon.com')  
            
    def view_random_page(self):
        view_mins = (60 * random.uniform(1, 3))
        i = 1
        t_end = time.time() + view_mins
        add_to_cart = 0

        while time.time() < t_end:
            print('running=='+str(i))
            r = self.mun_browser.get('https://amazon.com')
            clicked_to_item = False
            while not clicked_to_item:
                if self.mobile:
                    self.click_close_icon()
                self.scroll_like_human(star_review=True)
                random_int = random.randint(0, 1)
                if random_int == 0:
                    print('===search===')
                    try:
                        r = self.mun_api.get_key_for_search()
                        self.search_by_key_word(r['data'])
                    except:
                        continue
                # elif random_int == 1: 
                #     # print('running==',i)
                #     print('===click_item_list_in_home_page===')
                #     self.click_item_list_in_home_page()
                elif random_int == 1:
                    print('===random_move_and_click===')
                    self.random_move_and_click()
                self.scroll_like_human(star_review=True)
                if self.check_page_in_item_details():
                    print('===in page items details==')
                    clicked_to_item = True 
                    break
                if self.get_item_element():
                    click_item = self.click_random_item()
                    if not click_item:
                        self.go_to_homepage()
                        continue
                    if self.get_element_add_to_cart():
                        print('===in page items details==')
                        clicked_to_item = True 
                        break
                time.sleep(0.1)
                
            clicked_to_item_details = False
            while not clicked_to_item_details:
                if self.mobile:
                    self.click_close_icon()
                self.scroll_like_human()
                self.click_random_images_in_item_details()
                self.click_random_otpions_in_item_details()
                random_int = random.randint(-2, 1)
                if random_int <= 0:
                    print('click_random_in_item_details==')
                    result = self.click_random_in_item_details()
                    if not result:
                        break
                elif random_int == 1:
                    random_int = random.randint(1, 3)
                    if random_int == 1:
                        print('add_to_cart==')
                        clicked_to_item_details = self.add_to_cart()
                        if clicked_to_item_details:
                            add_to_cart+=1
                    elif random_int == 2:
                        print('buy_it_now==')
                        clicked_to_item_details = self.buy_it_now()
                    elif random_int == 3:
                        print('add_to_list==')
                        clicked_to_item_details = self.add_to_list() 
                    if add_to_cart > 0:
                        random_int = random.randint(2, 5)    
                        if random_int == 4:
                            print('delete_item_in_cart==')
                            clicked_to_item_details = self.delete_item_in_cart()  
                            if clicked_to_item_details:
                                add_to_cart-=1 
                        elif random_int == 5:
                            print('delete_all_item_in_cart==')
                            clicked_to_item_details = self.delete_all_item_in_cart()    
                            if clicked_to_item_details:
                                add_to_cart=0
                time.sleep(0.1)             
            
            i+=1
            self.go_to_homepage()
            time.sleep(0.1)
            # click_item_details = True
        print('==finished viewing')
        return view_mins
        
    def click_to_sign_in_icon(self):
        print('==click to sigin in==')
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='nav-progressive-greeting']") 
        if list_elements:
            self.click_random_offset_element(list_elements[0])
            return True
    
    def check_login_page(self):
        current_url= self.mun_browser.current_url
        if current_url.find('ap/signin') != -1:
            return True
        else:
            return   
        
    def click_signup_ratio(self):
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='accordion-row-register']") 
        if list_elements:
            self.click_random_offset_element(list_elements[0])
            return True
        
        
    def input_signup_details(self, email, password,first_name, last_name):
        print('==Trying input signup detail==')    
        #input first name and lastname
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='ap_customer_name']") 
        if not ap_customer_name_elements:
            print('===Error click to ap_customer_name===')
            return
        self.click_random_offset_element(ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))
        self.send_keys_like_human(first_name + ' '+ last_name, ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))
        
        ##input email
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='ap_email']") 
        if not ap_customer_name_elements:
            print('===Error click to ap_email===')
            return
        self.click_random_offset_element(ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))
        self.send_keys_like_human(email, ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))  
             
        #input password
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='ap_password']") 
        if not ap_customer_name_elements:
            print('===Error click to ap_password===')
            return
        self.click_random_offset_element(ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))
        self.send_keys_like_human(password, ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))
        # ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='auth-continue-announce']") 
        # if not ap_customer_name_elements:
        #     print('===Error click to continue===')
        #     return
        # time.sleep(random.uniform(0.3,1))
        ap_customer_name_elements[0].send_keys(Keys.ENTER)
        # self.click_random_offset_element(ap_customer_name_elements[0])
        # time.sleep(random.uniform(0.3,1))         
        return True

    def input_vcf_code(self, otp_code):
        print('==Trying input otp code===')
        
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='cvf-input-code']") 
        if not ap_customer_name_elements:
            print('===Error click to cvf-input-code===')
            return
        self.click_random_offset_element(ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))
        self.send_keys_like_human(otp_code, ap_customer_name_elements[0])
        time.sleep(random.uniform(0.3,1))
        ap_customer_name_elements[0].send_keys(Keys.ENTER)
        return True
    
    def input_phone_number(self, phone_number):
        print('==Trying input phone number===')
        cvf_phone_cc_aui_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='cvf_phone_cc_aui']") 
        if not cvf_phone_cc_aui_elements:
            print('===Error click to cvf_phone_cc_aui_elements===')
            return
        self.click_random_offset_element(cvf_phone_cc_aui_elements[0])
        time.sleep(random.uniform(0.3,1))
        cvf_phone_cc_native_221_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='cvf_phone_cc_native_221']") 
        if not cvf_phone_cc_native_221_elements:
            print('===Error click to cvf_phone_cc_native_221===')
            return
        self.scroll_like_human(element=cvf_phone_cc_native_221_elements[0])
        time.sleep(random.uniform(0.3,1))
        self.click_random_offset_element(cvf_phone_cc_native_221_elements[0])
        time.sleep(random.uniform(0.3,1))
        cvf_phone_num_elements = self.mun_browser.find_elements(By.XPATH, "//*[@name='cvf_phone_num']") 
        if not cvf_phone_num_elements:
            print('===Error click to cvf_phone_num_elements===')
            return
        self.click_random_offset_element(cvf_phone_num_elements[0])
        time.sleep(random.uniform(0.3,1))
        self.send_keys_like_human(phone_number, cvf_phone_num_elements[0])
        time.sleep(random.uniform(0.3,1))
        cvf_phone_num_elements[0].send_keys(Keys.ENTER)     
        return True 
    
    def input_otp_phone_code(self, otp_code):
        print('==Trying input otp Phone code===')
        code_elements = self.mun_browser.find_elements(By.XPATH, "//*[@name='code']") 
        if not code_elements:
            print('===Error click to code_elements===')
            return
        self.click_random_offset_element(code_elements[0])
        time.sleep(random.uniform(0.3,1))
        self.send_keys_like_human(otp_code, code_elements[0])
        time.sleep(random.uniform(0.3,1))
        code_elements[0].send_keys(Keys.ENTER)
        return True   
     
    def check_otp_page(self):  
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='cvf-input-code']") 
        if ap_customer_name_elements:
            return True
        else:
            return
       
    def check_logged_account_page(self):  
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='nav-greeting-name']") 
        if ap_customer_name_elements:
            return True
        else:
            return 
    def check_captcha_page(self):
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='descriptionVerify']") 
        if ap_customer_name_elements:
            return True
        ap_customer_name_elements = self.mun_browser.find_elements(By.XPATH, "//*[@name='cvf_captcha_input']") 
        if ap_customer_name_elements:
            return True
        else:
            return
    def check_verify_phonenumer_page(self):
        current_url= self.mun_browser.current_url
        if current_url.find('/ap/cvf/verify') != -1:
            return True
        else:
            return
        
    def check_otp_phonenumer_page(self):
        code_elements = self.mun_browser.find_elements(By.XPATH, "//*[@name='code']") 
        if code_elements:
            return True  
        
         
    def get_phone_number_input(self, signup_info):
        if 'viotp_token' in signup_info:
            viotp_token = signup_info['viotp_token']
            self.phoneApi = viotp.Viotp(viotp_token)
            result_json = self.phoneApi.get_phone_number('21')
            #'{"status_code":200,"success":true,"message":"successful","data":{"phone_number":"987654321","balance":50000,"request_id":"122314","re_phone_number":"84987654321","countryISO":"VN","countryCode":"84"}}'
            return result_json['data']
    def get_otp_phone_number(self, data_phonenumber):
        request_id = data_phonenumber['request_id']
        print('request_id==',request_id)
        get_time = 0
        SmsCode = None
        while not SmsCode:
            if get_time >= 60:
                return
            result_json = self.phoneApi.get_otp_code(request_id) 
            print(result_json)
            SmsCode = result_json['data']['Code']
            if SmsCode:
                return SmsCode
            if self.check_logged_account_page():
                return
            time.sleep(5)
            get_time+=1
            
                
    def get_email_otp(self,email,password):
        
        self.mun_email = munemail.MunEmail(email, password)
        login_result = self.mun_email.login()
        if login_result:
            print('===login sussess==')
            while 1:
                time.sleep(3)
                list_imap_emails = self.mun_email.getEmails(limit=10)
                for msg in list_imap_emails:
                    # print(msg)
                    email_data = {}
                    email_data['date'] = msg.date_str
                    email_data['from_'] = msg.from_
                    email_data['to'] = msg.to
                    email_data['subject'] = msg.subject
                    email_data['text'] = msg.text.strip()
                    email_data['html'] = msg.html.strip()
                    # self.statusqueue.put(('email_msg', json.dumps(email_data)))
                    text_body = msg.text or msg.html
                    if text_body.find('Verify your new Amazon account') != -1:
                        # print(text_body)
                        otp_research = re.search('<p class="otp">(.+?)</', text_body)
                        if otp_research:
                            print('==otp==', otp_research.group(1).strip())
                            return otp_research.group(1).strip()
                        return
                print('==finish refesh email==')  
        else:
            print('===login error==')
            return
        
    def sign_up_account(self, signup_info, sock='',sock_type='', mobile=True):
        print('==trying go to home page==')
        print(signup_info)
        email = signup_info['email']
        password = signup_info['password']
        first_name = signup_info['first_name']
        last_name = signup_info['last_name']
        # self.go_home_page_by_google()
        # self.view_random_page()
        self.got_to_site_by_url()
        time.sleep(random.uniform(0.3,1))
        self.scroll_like_human()
        click_login = self.click_to_sign_in_icon()
        if not click_login:
            print('===Error click to sign in icon===')
            return
        
        login_page = self.check_login_page()
        if not login_page:
            print('===Error go to login page===')
            return
        time.sleep(random.uniform(0.3,1))
        self.scroll_like_human(scoll_times=1)
        print('==trying click signup ratio==')
        click_signup_ratio = self.click_signup_ratio()
        if not click_signup_ratio:
            print('===Error click signup ratio===')
            return
        input_signup = self.input_signup_details(email, password,first_name, last_name)
        if not input_signup:
            print('==Error input signup page==')
        if self.check_captcha_page():
            print('==captcha page==')
            while not self.check_otp_page():
                time.sleep(3)
        if not self.check_otp_page():
            print('==Error go to otp page==')
            while not self.check_otp_page():
                time.sleep(3)
        otp_code = None
        if 'email_password' in signup_info:
            print('===login to email get otp===')
            otp_code = self.get_email_otp(email, signup_info['email_password'])
        if otp_code:    
            self.input_vcf_code(otp_code)
        else:
            print('==Manual otp code==')
            
        if self.check_verify_phonenumer_page():
            print('==verify phone number==')

            if 'phone_number' in signup_info:
                phone_number_verify = signup_info['phone_number']
            elif 'viotp_token' in signup_info:
                print('==get phone number for verify==')
                phone_data = self.get_phone_number_input(signup_info)
                phone_number_verify = phone_data['phone_number']
                signup_info['phone_number'] = phone_number_verify
            else:
                return
            self.input_phone_number(phone_number_verify)
            
            while not self.check_otp_phonenumer_page():
                print('==waiting otp_phonenumer_page==')
                time.sleep(3)
            if self.phoneApi:
                time.sleep(3)
                otp_phone = self.get_otp_phone_number(phone_data)
                if otp_phone:
                    self.input_otp_phone_code(otp_phone)
        if not 'phone_number' in signup_info:
            signup_info['phone_number'] = ''

        if self.check_logged_account_page():
            print('==created account==')
            return signup_info
                
    def go_to_homepage(self):
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='nav-logo-sprites']")
        
        if list_elements:
            self.click_random_offset_element(list_elements[0])
            return list_elements
        else:
            list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='nav-bb-logo']")
            if list_elements:
                self.click_random_offset_element(list_elements[0])
                return list_elements
            else:
                list_elements = self.mun_browser.get('https://amazon.com')
    
    def get_item_element(self):
        
        element = None
        list_elements = self.mun_browser.find_elements(By.XPATH, '//span[@data-component-type="s-product-image"]')
        ProductGrid = self.mun_browser.find_elements(By.XPATH, '//li[@data-testid="product-grid-item"]') 
        extra_item_element = self.mun_browser.find_elements(By.XPATH, '//span[@data-action="rhf-shoveler"]')
        if list_elements:
            list_elements_viewports = [elem for elem in list_elements if self.element_in_viewport(self.mun_browser, elem)]
            if list_elements_viewports:
                line_element = list_elements_viewports[random.randint(0, len(list_elements_viewports)-1)]
                list_element_click = line_element.find_elements(By.CLASS_NAME, 's-image')
                if list_element_click:
                    element = list_element_click[random.randint(0, len(list_element_click)-1)]   
        elif ProductGrid: 
            list_elements_viewports = [elem for elem in ProductGrid if self.element_in_viewport(self.mun_browser, elem)]
            if list_elements_viewports:
                element = list_elements_viewports[random.randint(0, len(list_elements_viewports)-1)]   
            
        elif extra_item_element:
            list_elements = extra_item_element[0].find_elements(By.CLASS_NAME, 'a-carousel-card')   
            list_elements_viewports = [elem for elem in list_elements if self.element_in_viewport(self.mun_browser, elem)]
            if list_elements_viewports:
                line_element = list_elements_viewports[random.randint(0, len(list_elements_viewports)-1)]
                list_element_click = line_element.find_elements(By.CLASS_NAME, 'a-link-normal')
                if list_element_click:
                    element = list_element_click[random.randint(0, len(list_element_click)-1)] 
                
        return element     
    
    def click_random_item(self):
        self.scroll_like_human(scoll_times=1)
        element = self.get_item_element()
        if not element:
            # self.click_random_item()
            return
        self.click_random_offset_element(element)
        return element
        
    def click_on_random_star(self):
        
        star_elements = self.mun_browser.find_elements(By.XPATH, '//i[contains(@class, "a-icon-star-small")]')
        list_elements_viewports = [elem for elem in star_elements if self.element_in_viewport(self.mun_browser, elem)]

        if list_elements_viewports:
            line_element = list_elements_viewports[random.randint(0, len(list_elements_viewports)-1)]
            self.click_random_offset_element(line_element)
            return line_element
        
    def click_item_list_in_home_page(self):
        self.scroll_like_human(scoll_times=1)
        element = self.get_item_list_element_home_page()
        if not element:
            # self.get_item_list_element_home_page()
            return
        # time.sleep(1)
        self.click_random_offset_element(element)  
        return element
            
    def get_item_list_element_home_page(self):
        
        element = None
        list_desktop_grid = []
        i=1
        while i <= 7:
            desktop_grid = self.mun_browser.find_elements(By.XPATH, "//*[@id='desktop-grid-%s']" % (str(i)) )
            desktop_ = self.mun_browser.find_elements(By.XPATH, "//*[@id='desktop-%s']" % (str(i)) )
            desktop_btf = self.mun_browser.find_elements(By.XPATH, "//*[@id='desktop-btf-grid-%s']" % (str(i)))
            # print(len(desktop_grid),len(desktop_), len(desktop_btf))
            if desktop_grid:
                list_elements_viewports = [elem for elem in desktop_grid if self.element_in_viewport(self.mun_browser, elem)]
                # print(list_elements_viewports)
                if list_elements_viewports:
                    list_desktop_grid.append(list_elements_viewports)
            if desktop_:
                list_elements_viewports = [elem for elem in desktop_ if self.element_in_viewport(self.mun_browser, elem)]
                if list_elements_viewports:
                    list_desktop_grid.append(list_elements_viewports)
            if desktop_btf:
                list_elements_viewports = [elem for elem in desktop_btf if self.element_in_viewport(self.mun_browser, elem)]
                if list_elements_viewports:
                    list_desktop_grid.append(list_elements_viewports)
            i+=1
        if list_desktop_grid:
            element_lists = list_desktop_grid[random.randint(0, len(list_desktop_grid)-1)]
            a_link_normal = element_lists[0].find_elements(By.CLASS_NAME, 'a-link-normal')
            list_elements_ = [elem for elem in a_link_normal if self.element_in_viewport(self.mun_browser, elem)]
            if list_elements_:
                element = list_elements_[random.randint(0, len(list_elements_)-1)]
                return element
      
      
    def get_all_items_links(self):
        list_elements = self.mun_browser.find_elements(By.CLASS_NAME, "a-dynamic-image")
        if list_elements:
            element = list_elements[random.randint(0, len(list_elements)-1)]
            return element
    def check_menu_navmobile(self):
        list_elements = self.mun_browser.find_elements(By.CLASS_NAME, 'hmenu-visible')
        return list_elements
        
    def click_close_icon(self):
        if self.check_menu_navmobile():
            list_elements = self.mun_browser.find_elements(By.CLASS_NAME, 'hmenu-close-icon')
            # list_elements1 = self.mun_browser.find_elements(By.CLASS_NAME, 'aok-float-right')
            if list_elements:
                print('==Click close Icon==')
                self.click_random_offset_element(list_elements[0])
                return list_elements[0]
        # elif list_elements1:
        #     self.click_random_offset_element(list_elements[0])
        #     return list_elements[0]            
        
    def get_item_element_in_item_details(self):
        element = None
        list_items_elements = []
        anonCarousel1 = self.mun_browser.find_elements(By.XPATH, "//*[@rel='anonCarousel1']")
        anonCarousel2 = self.mun_browser.find_elements(By.XPATH,  "//*[@id='anonCarousel2']")
        if anonCarousel1 and anonCarousel2: 
            random_int = random.randint(1, 2)
            if random_int == 1:
                list_items_elements = anonCarousel1
            else:
                list_items_elements = anonCarousel2
        elif anonCarousel1:
            list_items_elements = anonCarousel1 
        elif anonCarousel2:
            list_items_elements = anonCarousel2       
        if list_items_elements:
            list_elements = list_items_elements[0].find_elements(By.CLASS_NAME, 'a-link-normal')
            # list_elements_viewports = [elem for elem in list_elements if self.element_in_viewport(self.mun_browser, elem)]
            if list_elements:
                element = list_elements[random.randint(0, len(list_elements)-1)]
         
        return element  
    
    def get_item_images_in_item_details(self):
        element = None
        list_items_elements = []
        list_items_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='altImages']")
        if list_items_elements:
            list_elements = list_items_elements[0].find_elements(By.CLASS_NAME, 'a-list-item')
            list_elements_viewports = [elem for elem in list_elements if self.element_in_viewport(self.mun_browser, elem)]
            if list_elements_viewports:
                element = list_elements_viewports[random.randint(0, len(list_elements_viewports)-1)]        
        return element
    
    def get_item_otpions_in_item_details(self):
        element = None
        list_items_elements = []
        variation_color_name = self.mun_browser.find_elements(By.XPATH, "//*[@id='variation_color_name']")
        variation_size_name = self.mun_browser.find_elements(By.XPATH, "//*[@id='variation_size_name']")
        if variation_color_name and variation_size_name: 
            random_int = random.randint(1, 2)
            if random_int == 1:
                list_items_elements = variation_color_name
            else:
                list_items_elements = variation_size_name
        elif variation_color_name:
            list_items_elements = variation_color_name 
        elif variation_size_name:
            list_items_elements = variation_size_name       
        if list_items_elements:
            list_elements = list_items_elements[0].find_elements(By.CLASS_NAME, 'a-list-item')
            list_elements_viewports = [elem for elem in list_elements if self.element_in_viewport(self.mun_browser, elem)]
            if list_elements_viewports:
                element = list_elements_viewports[random.randint(0, len(list_elements_viewports)-1)]
        return element
    
    def get_element_add_to_cart(self):
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='add-to-cart-button']")
        if list_elements:
            return list_elements[0]
    
    def check_page_in_item_details(self):
        current_url= self.mun_browser.current_url
        if current_url.find('/dp/') != -1:
            return True
        else:
            return
 
    def click_random_images_in_item_details(self):
        self.scroll_like_human(scoll_times=1)
        element = self.get_item_images_in_item_details()
        if not element:
            # self.click_random_images_in_item_details()
            return
        # time.sleep(1)
        self.click_random_offset_element(element)   
        return element
    
    def click_random_otpions_in_item_details(self):
        # self.scroll_like_human(scoll_times=1)
        element = self.get_item_otpions_in_item_details()
        if not element:
            # self.click_random_otpions_in_item_details()
            return
        # time.sleep(1)

        self.click_random_offset_element(element)  
        return element  
           
    def click_random_in_item_details(self):
        if self.check_page_in_item_details():
            self.scroll_like_human(scoll_times=1)
            element = self.get_all_items_links()
            # element = self.get_item_element_in_item_details()
            if not element:
                print('==Can not find out the element==')
                # self.click_random_in_item_details()
                return
            # time.sleep(1)
            try:
                self.click_random_offset_element(element)
            except:
                self.click_random_in_item_details()
            print('===Clicked item_details===')
            return element
    
    def click_random_item_in_added_to_cart(self):
        self.scroll_like_human(scoll_times=1)
        element = self.get_item_element_in_item_details()
        if not element:
            # self.click_random_in_added_to_cart()
            return
        self.click_random_offset_element(element)
        return element
        
    def delete_item_in_cart(self):
        self.go_to_cart()
        list_elements = self.mun_browser.find_elements(By.XPATH, '//span[@data-action="delete"]')
        if list_elements:
            list_elements_viewports = [elem for elem in list_elements if self.element_in_viewport(self.mun_browser, elem)]
            line_element = list_elements_viewports[random.randint(0, len(list_elements_viewports)-1)]
            self.click_random_offset_element(line_element)
            return line_element
            
    def delete_all_item_in_cart(self):
        self.go_to_cart()
        list_elements = self.mun_browser.find_elements(By.XPATH, '//span[@data-action="delete"]')
        if list_elements:
            list_elements_viewports = [elem for elem in list_elements if self.element_in_viewport(self.mun_browser, elem)]
            for line_element in list_elements_viewports:
                try:
                    self.click_random_offset_element(line_element)
                    time.sleep(random.uniform(0.3,1))
                except:
                    pass
            return list_elements
                      
    def go_to_cart(self):
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='nav-cart-count']")
        if list_elements:
            self.click_random_offset_element(list_elements[0])
            return list_elements
    
    def add_to_cart(self):
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='add-to-cart-button']")
        if list_elements:
            print('==click add to cart==')
            self.click_random_offset_element(list_elements[0])
            return list_elements
  
    def add_to_list(self):
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='wishListMainButton']")
        if list_elements:
            self.click_random_offset_element(list_elements[0])
            return list_elements
        
    def buy_it_now(self):
        list_elements = self.mun_browser.find_elements(By.XPATH, "//*[@id='buy-now-button']")
        if list_elements:
            self.click_random_offset_element(list_elements[0])
            return list_elements
   
    def send_keys_like_human(self, text, elem):
        for character in text:
            elem.send_keys(character)
            time.sleep(random.uniform(0.05,0.2))
    
    def scroll_like_human(self, scoll_times=0, star_review=False, element=None):
        # footerElements = self.mun_browser.find_elements(By.XPATH, "//*[@id='navBackToTop']")
        # if footerElements:
        #     footer_y = footerElements[0].rect['y']
        # else:
        #     footerElements = self.mun_browser.find_elements(By.XPATH, "//*[@id='nav-bb-footer-logo']")
        #     if not footerElements:
        #         self.go_to_homepage()
        #         return
        #     footer_y = footerElements[0].rect['y']
        try:
            footer_y = self.mun_browser.execute_script("return document.body.scrollHeight")
        except:
            return
        # print(footer_y)
        if not scoll_times:
            scoll_times = random.randint(5, 10)
        scooled = 0
        last_pos = 0
        total_y = 0
        while scooled < scoll_times:
            random_pos = random.randint(300, 1000)
            random_action = random.randint(-1, 3)
            # print('next pos==',last_pos , int(last_pos)-int(random_pos))
            scroll_pos = self.mun_browser.execute_script("return window.scrollY")

            if random_action <= 0 or total_y >= footer_y or scroll_pos >= footer_y-random_action:
                # print('===am==', -1 * int(random_pos))
                down_scool = -1 * int(random_pos)
            else:
                down_scool = int(random_pos)
            # print('last_pos==',int(last_pos), int(down_scool))   
            actions = ActionChains(self.mun_browser)
            actions.scroll_by_amount(0, int(down_scool))
            actions.perform()   

            time.sleep(random.uniform(0.3,0.8))  
            if star_review:
                try:
                    self.click_on_random_star()
                except:
                    pass
            # print('clicked===' + str(scooled))           
            
            last_pos = down_scool
            total_y+=down_scool
            scooled+=1
            time.sleep(0.1)
        if element:
            self.mun_browser.execute_script("arguments[0].scrollIntoView(true);", element)
            
    def click_random_offset_element(self, element,context=False, move=False):
        # print(self.mun_browser.get_window_position())
        # print(element.location, element.rect)
        self.mun_browser.execute_script("arguments[0].scrollIntoView(true);", element)
        # desired_y = (element.size['height'] / 2) + element.location['y']
        # current_y = (self.mun_browser.execute_script('return window.innerHeight') / 2) + self.mun_browser.execute_script('return window.pageYOffset')
        # scroll_y_by = desired_y - current_y
        
        elem_left_bound = element.location.get('x')
        elem_top_bound = element.location.get('y')
        elem_width = element.size.get('width')
        elem_height = element.size.get('height')
        print(elem_left_bound, elem_top_bound, elem_width, elem_height)
        left_random_offset = random.uniform(0,elem_width/2)
        top_random_offset = random.uniform(0,elem_height/2)
        # print('elem_width:',elem_width,'elem_height:',elem_height, 'left_random_offset',left_random_offset,'top_random_offset',top_random_offset)
        random_left_offset = elem_left_bound+left_random_offset
        random_top_offset = elem_top_bound+top_random_offset
        

        actions = ActionChains(self.mun_browser)
        actions.reset_actions()
        win_upper_bound = self.mun_browser.execute_script('return window.pageYOffset')
        win_left_bound = self.mun_browser.execute_script('return window.pageXOffset')
        print('====',win_upper_bound, win_left_bound)
        # win_width = self.mun_browser.execute_script('return document.documentElement.clientWidth')
        # win_height = self.mun_browser.execute_script('return document.documentElement.clientHeight')

        # scroll_pos = self.mun_browser.execute_script("return window.scrollY")
        # print(left-win_right_bound,top-win_lower_bound, win_lower_bound)
        # actions.scroll_to_element(element)
        # browser_location = self.mun_browser.get_window_position()
        # print(random_left_offset - win_left_bound, random_top_offset-win_upper_bound)
        start_x = random_left_offset - win_left_bound
        start_y = random_top_offset - win_upper_bound
        end_x = start_x
        end_y = start_y
        time.sleep(random.uniform(0.3,1))
        if self.mobile:
            actions.w3c_actions = ActionBuilder(self.mun_browser, mouse=PointerInput(interaction.POINTER_TOUCH, "touch"))
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
    import mybrowser, munantiapi
    mun_anti = munantiapi.MunAntiApi()
    inject_info = mun_anti.get_inject_info()
    profile_info = mun_anti.get_profile_by_id(id='2581')
    # print(profile_info)
    mun_browser = mybrowser.MunAntiBrowser()
    mun_driver = mun_browser.setting(inject_str=inject_info['data'], profileInfo=profile_info['data'])
    ordervr = Amazon(mun_browser=mun_driver, mobile=True)
    # ordervr.view_random_page()
    signup_info = {}
    signup_info['email'] = 'ropunkantorm@hotmail.com'
    signup_info['password'] = 'iW9KmT09'
    signup_info['first_name'] = 'Tony'
    signup_info['last_name'] = 'Nguyen'
    signup_info['email_password'] = 'iW9KmT09'
    signup_info['viotp_token'] = 'bb116c18f3ce450e8193f8de9fb7298f'
    ordervr.sign_up_account(signup_info, mobile=True)
    # ordervr.got_to_site_by_url()
    # ordervr.search_by_key_word('iphone', mobile=True)
    # ordervr.sign_up_account('dsaidhaosdh@gmail.com','hanoi123')
    # ordervr.check_exist('tuannguyen@maidzo.vn')
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
