# -*- coding: utf-8 -*-
#!/usr/bin/env python
from http.cookiejar import Cookie
import requests, re

from requests import cookies
# from http.cookiejar import CookieJar
# import json, re
# from bs4 import BeautifulSoup,SoupStrainer
# import captcha2upload
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from optparse import OptionParser

from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver import Edge
from selenium.webdriver.edge.service import Service as EdgeService
import datetime

gw = 'http://gw.open.1688.com/openapi'
app_key = '9996942'
app_secret = 'dGi4rAY67n3'
# access_token = 'd5e193bd-aa82-41e6-a252-4a889fe2e0b2'
mediaId = '1757035'
mediaZoneId = '1356006'

token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjo5MTgzLCJ1c2VybmFtZSI6Im1lb211bjIwMTQiLCJleHAiOjE1NjI4NDk1ODUsImVtYWlsIjoidHVhbi5zdG9yYWdvbkBnbWFpbC5jb20iLCJvcmlnX2lhdCI6MTU2Mjg0OTI4NX0.OE3NMSCH_O-6cO5nLeF_Smdqsv_n9DtUqpPutitmq0E'





def macys():

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/76.0.3809.132 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate, br',
        # 'Authorization': 'JWT eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTU2NSwidXNlcm5hbWUiOiJ0dW5nYmsiLCJleHAiOjE1NjYyNTg4MzUsImVtYWlsIjoidHR1bmcuYmtAZ21haWwuY29tIiwib3JpZ19pYXQiOjE1NjYyNTg1MzV9.lnFHG5j1i2QrtvbhNyVCUchsrei4hYp8M6plfYYLbAM',
        # 'Connection': 'keep-alive',
        'Accept-Language': 'en-US,en;q=0.9',
        # 'Authorization': 'Basic cGpqNjhwY2FtYmJ1cWIyODh5NmFuN3Y1Om1lVVlGRlJDYWhyOUtXRkRHdDZoUjR3Mg==',
        # 'host': 'www.mapprouter.com',
        # 'origin': 'https://hifiorder.com',
        # 'x-requested-with': 'XMLHttpRequest',
        'Cookie':'bm_sv=E812D92D0D092B38E0898D839A39D92F~UENVRv108aRCO0BL6jPZ2oGsfBvwj+oSM2KM0m4G84JKmVSt3na/vHvbtiUEAv2Uyi4mpay5PCXi7JP85xBYThSxvHeaQ6Q5rqrJD+VpFj5owyD8UyDxbb7QS3zfTuwcIwIXSIs7JBEyD7WH2e9Y6i6WS2FwChRSxY8C1yERt0w=; TS0132ea28=011c444591f0e8e9904eb514632654e5bb7f573c6602efcdaa105bbc21d7f6b8743c7cbfa2ee61592e171a9f2acc8b16c3e1303685;SEED=-1717446300563336725; SignedIn=0; TS01ad411f=011c4445915d20c31f94cd48fd21f2bda9fac13102dea618f25bc3b0805225ca1a00fb74a858240118719c13cd05a151c661e1edcdd1f1b4d41534d68ff4c604873a01576bf8c4e9d4c8acbb9994f68901df2a4ca5d643e0dd532b1554a03085a34ee3e521; ak_bmsc=4CDB20705F93CAA1116D2493BFA12D8417394325D04B0000449B1A600F03AD33~plPxWxjz0/RiPwTy05Xx6qxC7+2Ctc6JcoLwEpHWVAYPOGVB45nLqTuglDGMuB8pVpHMxXPtL8g0kq0mNfBxjT+Sod6NCp/ufGjyJ36/7qAETkbU0TWwBSdJ+tPRWfIYqZUKshNOsWg9tiT5+SyIsIdn5fACgYrOqQfVnqmWNYmvwXvkQgPIZOvspbsBNxEMVNMwyd6vNIY0Wec4/YD75+I222fSO97E8WzJuOSVU+Cds=; dca=WDC; mercury=true; TS0132ea28=011c44459157cd453db5cd1c76417d676c7b97387fdea618f25bc3b0805225ca1a00fb74a81e751dfc7a930a23720e9023edcd138e; akavpau_www_www1_macys=1612356720~id=0dc5a39462fd33f54d8d22d7052ea367',
        'referer': 'https://www.macys.com/account/signin',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'sec-fetch-dest':'empty',
        'sec-fetch-mode':'cors',
        'sec-fetch-site':'same-origin',
        'x-requested-with':'XMLHttpRequest',
        'content-type':'application/json',
        'origin':'https://www.macys.com'
    }
    browser = requests.session()
    browser.headers = headers
    # browser.cookies = CookieJar()

    r = browser.get('https://www.macys.com/account/signin')
    cookies = r.cookies.get_dict()
    cookie_string1 = "; ".join([str(x)+"="+str(y) for x,y in cookies.items()])
    # print(cookie_string1)

    r = browser.get('https://www.macys.com/account-xapi/api/account/signin?')

    cookies = r.cookies.get_dict()
    cookie_string = "; ".join([str(x)+"="+str(y) for x,y in cookies.items()])

    print(cookie_string+';'+cookie_string1)
    # print(r.cookies)
    # print(r.cookies)
    import json
    url = 'https://www.macys.com/account-xapi/api/myaccount/email?_deviceType=PC'
    data = {"user":{"email":"asdasdasdasdsdsa@gmail.com"}}
    r = browser.post(url,json=data,headers=headers)
    # print(r.headers)
    print(r.text)
    print(r.cookies)
    url = 'https://auth.macys.com/v3/oauth2/token'
    data = {}
    data['grant_type'] = 'password'
    data['username'] = 'weqweweqwe%40gmail.com'
    data['password'] = 'password'
    data['registrySignIn'] = 'false'
    data['request_url'] = 'https%3A%2F%2Fwww.macys.com%2Faccount%2Fsignin'
    data['deviceFingerPrint'] = ''
    data['authWebKey'] = 'cGpqNjhwY2FtYmJ1cWIyODh5NmFuN3Y1Om1lVVlGRlJDYWhyOUtXRkRHdDZoUjR3Mg%253D%253D'
    # r = browser.post(url,data, headers=headers)

    # print(r.text)

# def get_tao_kou_ling(text: str) -> str:
#     pattern = "؋‎฿₿¢₡₵$₫֏€₲₾₴₭₺₼₥₦₱£﷼‎៛₽₨௹₹৲৳૱₪₸₮₩¥₳₠₢₯₣₤₶₧₰₷￥"
#     pattern = "([" + pattern + "])" + "(\\w+)\\1"
#     result = re.compile(pattern).findall(text)
#     try:
#         result = result[0][0] + result[0][1] + result[0][0]  # 取匹配到的第一个
#     except IndexError:
#         result = ""
#     return result
#     pass
# print('===',get_tao_kou_ling('￥bRHg1JEXN5q￥'))
# url = 'https://maps.googleapis.com/maps/api/place/autocomplete/json?input='+search_str+'&components=country:vn&language=en_vn&key=AIzaSyDmVnG8MytwnXovpwF2DZl_7RolwYXvGaM'
# r = browser.get(url)
# result = r.json()
# for line in result['predictions']:
#     print(line['description'])
# print (r.json())

# ACCESS_TOKEN = 'DN_D1uCsxaqvSiC5XJVgJJrmoGM7B-SMOYd5BwGfZ1DS0lW3knBEJbmadWMO6-ST82Io2UOQ_JOf4jCCur3-6YPLZ3B5S-5v3tRCSCnHlJmnR90TwrouNonlzd3cUwnf4N3QP_qugIy93VbWx3-DOWuSeawo1OvJ3aVsNV5ZtcGP8A1ueIBOMHyagMZz8zuWD3E74iianYii6QfcwYtKI0XejbxjOU5zEYIBOT0QqtqI9u4hsWRo7mm0iotiDDi60GEpDDPV_WHlMf0pW4ZT7MDwZ3MCKzO9Kuvn6tk88EH8'
# data = {
#     "recipient": {"user_id":"406609696884033062"},
#     "message": {"text":"Chào mừng bạn đến với Zalo Official Account!"}
#  }
# url = 'https://openapi.zalo.me/v2.0/oa/message?access_token='+ACCESS_TOKEN
# headers = {}
# r = browser.post(url,json=data)
# print(r.text)
# from zalo.sdk.oa import *
#
# zalo_info = ZaloOaInfo(oa_id="2508630445377281964", secret_key="DN_D1uCsxaqvSiC5XJVgJJrmoGM7B-SMOYd5BwGfZ1DS0lW3knBEJbmadWMO6-ST82Io2UOQ_JOf4jCCur3-6YPLZ3B5S-5v3tRCSCnHlJmnR90TwrouNonlzd3cUwnf4N3QP_qugIy93VbWx3-DOWuSeawo1OvJ3aVsNV5ZtcGP8A1ueIBOMHyagMZz8zuWD3E74iianYii6QfcwYtKI0XejbxjOU5zEYIBOT0QqtqI9u4hsWRo7mm0iotiDDi60GEpDDPV_WHlMf0pW4ZT7MDwZ3MCKzO9Kuvn6tk88EH8")
# zalo_oa_client = ZaloOaClient(zalo_info)
# data = {
#     'uid': '406609696884033062',
#     'message': 'hello there'
# }
# params = {'data': data}
# send_text_message = zalo_oa_client.post('/sendmessage/text', params)
# print(zalo_oa_client)
# data = {
#     'qrdata': 'qrcode',
#     'size': 10
# }
# params = {'data': data}
# qrcode = zalo_oa_client.post('/qrcode', params)


from hashlib import sha1
import hmac
import time
def sign(key, value):
    key = bytes(key, encoding='utf8')
    value = bytes(value, encoding='utf8')
    val = hmac.new(key, value, sha1).hexdigest()
    return val.upper()

def invoke(api, params):
    # http://gw.open.1688.com/openapi/param2/1/com.alibaba.product/alibaba.product.get/8384550
    url = 'param2/1/{}/{}'.format(api, app_key)

    # 签名
    pstr = ''
    for key, value in params.items():
        pstr += key
        pstr += str(value)
    # 通用参数
    # print(url)
    # print(pstr)
    # print(url + pstr)

    sign_str = sign(app_secret, url + pstr)
    print(sign_str)
    base = {
        # 签名
        'access_token': 'xxx',
        '_aop_signature': sign_str,
    }

    reqUrl = '{}/{}'.format(gw, url)

    for key, value in params.items():
        base[key] = str(value)

    # 发起请求
    # r = requests.post(url=reqUrl, data=base)
    print(reqUrl)
    r = requests.get(url=reqUrl, params=base)
    rs = r.json()
    if 'exception' in rs:
        raise RuntimeError(rs.get('error_message') + '\n error detail:' + r.text)

    return rs

class Api:
    def __init__(self, namespace):
        self.namespace = namespace

    def call(self, api, params):
        return invoke(self.namespace + '/' + api, params)

class Get_link:
    def __init__(self):
        self.api = Api('com.alibaba.p4p')

    def get(self, product_id):
        '''
           获取产品详情 https://open.1688.com/api/apidocdetail.htm?aopApiCategory=product_new&id=com.alibaba.product:alibaba.product.get-1
           :param product_id:
           :return:
           '''

        return self.api.call('alibaba.cps.genClickUrl', {
            'mediaId': mediaId,
            'mediaZoneId': mediaZoneId,
            'objectValueList': product_id,
            'type': '0'
        })
    def get_info(self, product_id):
        '''
           获取产品详情 https://open.1688.com/api/apidocdetail.htm?aopApiCategory=product_new&id=com.alibaba.product:alibaba.product.get-1
           :param product_id:
           :return:
           '''

        return self.api.call('alibaba.cps.listOfferPageQuery', {
            # 'mediaId': mediaId,
            # 'mediaZoneId': mediaZoneId,
            'feedInfo': product_id,
            'pageNo': 1,
            'pageSize': 100
        })
    def get_trade_list(self):
        '''
           获取产品详情 https://open.1688.com/api/apidocdetail.htm?aopApiCategory=product_new&id=com.alibaba.product:alibaba.product.get-1
           :param product_id:
           :return:
           '''

        return self.api.call('alibaba.cps.tradeBillList', {
            # 'mediaId': mediaId,
            'queryOrderType': 'orderAll',
            'queryTimeType': 'gmtCreateTime',
            'queryStartTime': '2020-05-27',
            'queryEndTime': '2020-05-27',
            'pageNo': 1,
            'pageSize': 100
        })


def get_1688_trade_list():
    product = Get_link()
    trade_list = product.get_trade_list()
    print(trade_list)
# get_1688_trade_list()
#

def get_1688_info(item_url):
    #https://detail.1688.com/offer/595415883603.html?spm=a2615.7691456.autotrace-offerGeneral.1.4cae3fba1f8DzW
    link_re = re.search('offer\/(\d+)\.html',item_url)
    if link_re:
        offer_id = link_re.group(1).strip()
        product = Get_link()
        # 替换成自己的产品id
        info_link = product.get_info(offer_id)
        print(info_link)
        return info_link

        # if str(info_link).find('error_message') != -1:
        #     return
        #
        # if info_link['result']:
        #     link_1688 = info_link['result'][0]['longClickUrl']
        #     return link_1688
        # else:
        #     return

def get_1688_link(item_url):
    #https://detail.1688.com/offer/595415883603.html?spm=a2615.7691456.autotrace-offerGeneral.1.4cae3fba1f8DzW
    link_re = re.search('offer\/(\d+)\.html',item_url)
    if link_re:
        offer_id = link_re.group(1).strip()
        product = Get_link()
        # 替换成自己的产品id
        info_link = product.get(offer_id)
        print(info_link)
        if str(info_link).find('error_message') != -1:
            return

        if info_link['result']:
            link_1688 = info_link['result'][0]['longClickUrl']
            return link_1688
        else:
            return

def get_1688_commission(item_url):
    link_re = re.search('offer\/(\d+)\.html',item_url)
    if link_re:
        offer_id = link_re.group(1).strip()
        product = Get_link()
        info_items = product.get_info(offer_id)
        print(info_items['result'])
        # info_commission = json.loads(info_items)
        if 'result' in info_items:
            result = info_items['result']
            if result:
                link_commissions = product.get(offer_id)
                return {'item_info':result,'link_commissions':link_commissions}
            else:
                return
    return


###
# req.access_token = ''
# req.feedInfo = 574248450765
# req.pageNo = 1
# req.pageSize = 100
####
# 'feedInfo': product_id,
# 'pageNo': 1,
# 'pageSize': 100
# req.ext = 'ssss'
# req.mediaId = mediaId
# req.mediaZoneId = mediaZoneId
# req.objectValueList = 574248450765
# req.type = '0'
# resp = req.get_response()
# print(resp)
# for line in resp['tradeBillList']:
#     print(line)
# req = aop.api.AlibabaCpsTradeBillListParam()


# req.settleState = 1
#req.ext = '{"sđsds":"dsdad"}'


cmd = 'tk tuannguyen'
print(cmd.find('tk'))
username = cmd.split('tk')[-1]
print(username.strip())

import top.api
# TAOBAO_APPKEY = '28313470'
# TAOBAO_SECRET = 'bcc56502f937ebee377ddac0036dff72'
# TAOBAO_ADZONE_ID = '110006400113'


taobao_appkey = '28313470'#data_api['appkey']
taobao_secret = 'bcc56502f937ebee377ddac0036dff72'#data_api['secret']
taobao_adzone_id = '110006400113'#data_api['adzone']


#taobao
appkey = taobao_appkey
secret = taobao_secret
adzone_id = taobao_adzone_id
# appkey = settings.TAOBAO_APPKEY
# secret = settings.TAOBAO_SECRET
# adzone_id = settings.TAOBAO_ADZONE_ID
# app_key_1688 = '7606588'
# app_secret_1688 = '4xQLenq2zSl7'
# mediaId_1688 = '1354012'
# mediaZoneId_1688 = '1355006'
#1688



# 获取淘宝客商品优惠券
def get_material_optional(key):
    req = top.api.TbkDgMaterialOptionalRequest()
    req.set_app_info(top.appinfo(appkey, secret))

    req.page_size = 20
    req.page_no = 1
    req.platform = 1

    req.is_overseas = 'false'

    req.q = key

    req.adzone_id = adzone_id
    req.external_id = "1323123123"


    try:
        resp = req.getResponse()
        print(resp)
        if len(resp['tbk_dg_material_optional_response']['result_list']['map_data']) == 1:
            return resp['tbk_dg_material_optional_response']['result_list']['map_data'][0]
        else:
            return
        # print(resp)
    except Exception as e:
        print(e)
        return


def get_optimus_optional():
    req = top.api.TbkDgOptimusMaterialRequest()
    req.set_app_info(top.appinfo(appkey, secret))
    #san pham:6708
    #ban chay:28026
    #flash sale:4094
    # req.start_dsr = 10
    req.page_size = 5
    req.page_no = 1
    req.material_id = 4093
    req.platform = 1
    req.adzone_id = adzone_id
    req.device_encrypt = "MD5"
    req.device_value = "xxx"
    req.device_type = "IMEI"
    resp = req.getResponse()
    print(resp)

# get_optimus_optional()
fomat_time = '%Y-%m-%d %H:%M:%S'
from datetime import datetime, timedelta
from pytz import timezone
import pytz
utc = pytz.utc
print(utc.zone)
eastern = timezone('US/Eastern')
print(eastern.zone)
amsterdam = timezone('Europe/Amsterdam')
loc_dt  = eastern.localize(datetime.now())
amsterdam_time = loc_dt.astimezone(amsterdam)
print(amsterdam_time.strftime(fomat_time))

start_time = (datetime.now() - timedelta(hours=3)).strftime(fomat_time)
print(start_time)
print(float('+ 24,402,200'.replace(',', '').replace(' ', '')))



def import_excel_tmdt_info():

    import xlrd
    loc = ("02-05-08-20.xls")
    wb = xlrd.open_workbook(loc)
    sheet = wb.sheet_by_index(0)
    print(sheet.nrows)
    i = 1
    while i < sheet.nrows:
        tracking_number = sheet.cell_value(i, 1)
        created_time = sheet.cell_value(i, 2)
        weight = sheet.cell_value(i, 3)

        print(tracking_number,created_time,weight)
        i+=1

def login_vcb():
    driver = webdriver.Chrome('D:/chromedriver.exe')
    driver.get("https://vcbdigibank.vietcombank.com.vn/#/login?returnUrl=%2Fhome")
    driver.find_element_by_id('username').send_keys("0705891987")
    driver.find_element_by_name('pass').send_keys('Hanoi1234@#')
    return driver
    # driver.find_element_by_xpath("//img[contains(./@src, 'get-captcha')]").screenshot('screen.png')
    # decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'
    # captcha_save = 'screen.png'
    # captcha = captcha2upload.CaptchaUpload(decaptcha_key)
    # captcha_input = captcha.solve(captcha_save)
    # print('captcha:',captcha_input)
    # driver.find_element_by_name('captcha').send_keys(captcha_input)
    # driver.find_element_by_id('btnLogin').click()
    # timeout = 10
    # try:
    #     element_present = EC.presence_of_element_located((By.XPATH, '//a[contains(@href, "#/thongtintaikhoan/danhsachtaikhoan/")]'))
    #     WebDriverWait(driver, timeout).until(element_present)
    # except TimeoutException:
    #     print ("==Timed out waiting for page to load")
    #
    # # element = driver.find_elements_by_xpath("//*[@class='ubtn account-list-item-ic circle ic-arrow-right-white']")[0]
    # element = driver.find_element_by_xpath('//a[contains(@href, "#/thongtintaikhoan/danhsachtaikhoan/")]')
    # driver.execute_script("arguments[0].click();", element)
    #
    # try:
    #     element_present = EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'VND')]"))
    #     WebDriverWait(driver, timeout).until(element_present)
    # except TimeoutException:
    #     print ("Timed out waiting for page to load 0451000307966")
    # time.sleep(2)
    # element = driver.find_elements_by_xpath("//div[contains(text(), '0451000307966')]")[1]
    # # for element in elements:
    # #     print(element.id,element.text,element.location,element.parent, element.rect)
    # driver.execute_script("arguments[0].click();", element)
    #
    # try:
    #     element_present = EC.presence_of_element_located((By.XPATH, "//*[contains(text(), '0451000307966 - VND')]"))
    #     WebDriverWait(driver, timeout).until(element_present)
    # except TimeoutException:
    #     print ("Timed out waiting for page to load Tìm kiếm")
    # time.sleep(1)

# import_excel_tmdt_info()
def vcb_get_info(url,token):

    # driver.set_window_size(1120, 550)
    # driver.set_window_size(1120, 550)

    driver = login_vcb()
    header = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Connection': 'keep-alive',
        'Accept-Language': 'en-US',
        'Accept': 'application/json',
        'Authorization': 'Token '+token
    }
    browser = requests.session()
    browser.headers = header
    timeout = 10
    dict_giao_dich = {}
    while 1:

        try:
            element = driver.find_element_by_xpath("//*[contains(text(), 'Tìm kiếm')]")
            driver.execute_script("arguments[0].click();", element)
            element_present = EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Số tham chiếu')]"))
            WebDriverWait(driver, timeout).until(element_present)
        except Exception:
            print ("active show")
            time.sleep(1)
            driver.quit()
            # driver.quit()
            login_vcb()
        else:
            time.sleep(1)

            # print(element)
            # element.click()
            html = driver.find_element_by_tag_name('html').get_attribute('innerHTML')
            print('tìm giao dịch')
            list_giao_dich = re.findall(r'</div><div class="list-info-txt-main color-white">(.+?)</div>.+?">Số tham chiếu:(.+?)</div>.+?">(.+?)</div>',html)

            for line_giao_dich in list_giao_dich:
                Mota, Sothamchieu, Sotien = line_giao_dich
                if Sothamchieu.strip() not in dict_giao_dich:
                    print(Mota.strip(), Sothamchieu.strip(), Sotien.strip())
                    dict_giao_dich[Sothamchieu.strip()] = 1
                    data = {}
                    data['mota'] = Mota.strip()
                    data['sothamchieu'] = Sothamchieu.strip()
                    data['sotien'] = Sotien.strip()
                    r = browser.post(url,data)
                    print(r.json())
            driver.refresh()
            time.sleep(30)

        # print(line_giao_dich)
    # print(html)
    print(ccc)


def get_taobao_info(item_id):
    data_item = {'success': False}
    access_get_link = False

    req = top.api.TbkItemInfoGetRequest()
    req.set_app_info(top.appinfo(appkey, secret))

    req.num_iids = item_id
    req.platform = 1
    # req.ip = "11.22.33.43"

    resp = req.getResponse()
    print(resp)
    data_item['success'] = True
    data_item['data'] = resp

def get_taobao_word_info(item_id):
    data_item = {'success': False}
    access_get_link = False

    req = top.api.TbkItemWordGetRequest()
    req.set_app_info(top.appinfo(appkey, secret))

    req.item_id = item_id
    req.adzone_id = taobao_adzone_id
    req.count = 5
    # req.platform = 1
    # req.ip = "11.22.33.43"

    resp = req.getResponse()
    print(resp)
    data_item['success'] = True
    data_item['data'] = resp

def get_taobao_order_detail():
    req = top.api.TbkOrderDetailsGetRequest()
    req.set_app_info(top.appinfo(appkey, secret))
    start_time = (datetime.now().astimezone(pytz.timezone('Asia/Shanghai')) - timedelta(hours=6)).strftime(
        '%Y-%m-%d %H:%M:%S')
    end_time = (datetime.now().astimezone(pytz.timezone('Asia/Shanghai')) - timedelta(hours=3)).strftime('%Y-%m-%d %H:%M:%S')
    print(start_time,end_time)
    # req.start_dsr = 10
    req.page_size = 200
    req.start_time = start_time
    req.end_time = end_time
    req.page_no = 1


    resp = req.getResponse()
    print('===',resp)
    # print(resp)

def macys_selenium():

    edge_options = EdgeOptions()
    # options.
    # options.headless = True
    # options.add_argument("--headless")  # Runs Chrome in headless mode.
    # options.add_argument('--no-sandbox')  # Bypass OS security model
    # options.add_argument('--disable-gpu')  # applicable to windows os only
    # try:
    #     self.driver = webdriver.Firefox(executable_path='geckodriver.exe',options=options)
    # except Exception:
    #     self.driver = webdriver.Firefox(executable_path='D://geckodriver.exe',options=options)
    # edge_options.use_chromium = True  # use_chromium is not needed in selenium 4
    # A little different from Chrome cause we don't need two lines before 'headless' and 'disable-gpu'
    # edge_options.add_argument('headless')
    # edge_options.add_argument('disable-gpu')
    try:
        service = EdgeService(executable_path='msedgedriver.exe')
        driver = Edge(service=service, options=edge_options)
    except Exception:
        service = EdgeService(executable_path='D://msedgedriver.exe')
        driver = Edge(service=service, options=edge_options)

    driver.get("https://vcbdigibank.vietcombank.com.vn/#/login?returnUrl=%2Fhome")


def sign(key, value):
    key = bytes(key, encoding='utf8')
    value = bytes(value, encoding='utf8')
    val = hmac.new(key, value, sha1).hexdigest()
    return val.upper()

def invoke(api, params):
    # http://gw.open.1688.com/openapi/param2/1/com.alibaba.product/alibaba.product.get/8384550
    url = 'param2/1/{}/{}'.format(api, app_key)

    # 签名
    pstr = ''
    for key, value in params.items():
        pstr += key
        pstr += str(value)
    # 通用参数
    print(url)
    print(pstr)
    print(url + pstr)

    sign_str = sign(app_secret, url + pstr)
    print(sign_str)
    base = {
        # 签名
        '_aop_signature': sign_str,
    }

    reqUrl = '{}/{}'.format(gw, url)

    for key, value in params.items():
        base[key] = str(value)

    # 发起请求
    # r = requests.post(url=reqUrl, data=base)
    r = requests.get(url=reqUrl, params=base)
    rs = r.json()
    if 'exception' in rs:
        raise RuntimeError(rs.get('error_message') + '\n error detail:' + r.text)

    return rs

class Api:
    def __init__(self, namespace):
        self.namespace = namespace

    def call(self, api, params):
        return invoke(self.namespace + '/' + api, params)

class Get_link:
    def __init__(self):
        self.api = Api('com.alibaba.p4p')

    def get(self, product_id):
        '''
           获取产品详情 https://open.1688.com/api/apidocdetail.htm?aopApiCategory=product_new&id=com.alibaba.product:alibaba.product.get-1
           :param product_id:
           :return:
           '''

        return self.api.call('alibaba.cps.genClickUrl', {
            'mediaId': mediaId,
            'mediaZoneId': mediaZoneId,
            'objectValueList': product_id,
            'type': '0'
        })

from aescipher import AESCipher
import sqlite3 as lite
import os, geoip2.database
key = 'stay123!@#'
str = '9uBc37ycdase5bE1D5fPKLgf81iczgB1MbUiV+iBpP0='
aes_cipher = AESCipher('stay123!@#')
# de_str = aes_cipher.decrypt_string(str)
# print('====',de_str)


def get_ip_infomation(ip):
    appFolderPath = os.getcwd()
    try:

        reader = geoip2.database.Reader(appFolderPath + '/ssh/GeoLite2-City.mmdb')
        response = reader.city(ip)
        city = response.city.name
        state = response.subdivisions.most_specific.iso_code
        country = response.country.iso_code
        reader.close()
    except:
        city = 'None'
        state = 'None'
        country = 'None'

    return city, state, country

def add_ssh_to_db(ip, username, password, city, state, country, comboBoxcatalogue):
    global aes_cipher
    ip_add_encrypt = ip
    username_add_encrypt = aes_cipher.encrypt(username)
    password_add_encrypt = aes_cipher.encrypt(password)
    print(username_add_encrypt,password_add_encrypt)
    appFolderPath = os.getcwd()
    con_ship = lite.connect(appFolderPath + '/ssh/' + comboBoxcatalogue)
    with con_ship:
        con_ship.row_factory = lite.Row
        cur = con_ship.cursor()
        try:
            cur.execute("SELECT * FROM ssh_info")
        except:
            cur.execute('''CREATE TABLE ssh_info
                   (id INT PRIMARY KEY      NOT NULL,
                   ip       CHAR(255) NOT NULL,
                   username      CHAR(255) NOT NULL,
                   password      CHAR(255) NOT NULL,
                   city     CHAR(255),
                   state     CHAR(255),
                   country     CHAR(255),
                   ssh_note     CHAR(255),
                   ssh_blacklist   CHAR(255));''')
            cur.execute("SELECT * FROM ssh_info")

        rows = cur.fetchall()

        if not rows:
            idssh = 1
        else:
            lastrow = rows[len(rows) - 1]
            list_id_db = int(lastrow['id'])
            idssh = list_id_db + 1

        try:
            city = str(city).encode('utf8', 'ignore').encode("ascii", "ignore")
        except:
            try:
                city = str(city).decode('utf8', 'ignore').encode("ascii", "ignore")
            except:
                city = 'None'
        try:
            state = str(state).encode('utf8', 'ignore').encode("ascii", "ignore")
        except:
            try:
                state = str(state).decode('utf8', 'ignore').encode("ascii", "ignore")
            except:
                state = 'None'

        cur.execute("INSERT INTO ssh_info (id,ip,username,password,city,state,country,ssh_note,ssh_blacklist) \
                                VALUES (%d, '%s', '%s', '%s', '%s', '%s', '%s', '%s', '%s' )" % (
            int(idssh), ip_add_encrypt, username_add_encrypt, password_add_encrypt,
            city.replace("'", ''), state.replace("'", ''), country.replace("'", ''), '', ''));
        return True


    con_ship.close()


def get_list_ssh_form_database(ssh_database):
    appFolderPath = os.getcwd()
    print(appFolderPath)
    con = lite.connect(appFolderPath + '/ssh/' + ssh_database)
    with con:
        con.row_factory = lite.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM ssh_info")
        rows = cur.fetchall()

    con.close()
    # random.shuffle(rows)
    return rows
# list_ssh = get_list_ssh_form_database('ssh_database.db')
#
# print(len(list_ssh))
# c = open('ssh_old.txt','w')
# list_ssh =  open('ssh_old.txt','r').readlines()
# for line in list_ssh:
#     ip = line.split('|')[0]
#     username = line.split('|')[1]
#     password = line.split('|')[2]
#     print(username,password)
#     # username_de = aes_cipher.decrypt_string(username)
#     # password_de = aes_cipher.decrypt_string(password)
#     city, state, country = get_ip_infomation(ip)
#     print(ip, city, state, country)
#     adddb = add_ssh_to_db(ip, username, password, city, state, country, 'ssh_new.db')

    # c.write(ip+'|'+username_de+'|'+password_de+'\n')
#
# def get_1688_link(item_url):
#     #https://detail.1688.com/offer/595415883603.html?spm=a2615.7691456.autotrace-offerGeneral.1.4cae3fba1f8DzW
#     link_re = re.search('offer\/(\d+)\.html',item_url)
#     if link_re:
#         offer_id = link_re.group(1).strip()
#         product = Get_link()
#         # 替换成自己的产品id
#         info_link = product.get(offer_id)
#         print(info_link)
#         if str(info_link).find('error_message') != -1:
#             return
#
#         if info_link['result']:
#             link_1688 = info_link['result'][0]['longClickUrl']
#             return link_1688
#         else:
#             return
# print(get_1688_link('https://detail.1688.com/offer/626378913479.html?tracelog=cps&clickid=3b3f0294a8eabc294b0c7cf490b31ec8'))
# data = get_material_optional('http://item.taobao.com/item.htm?spm=a219t.11816981.0.d5b7ff802.433c6a15oKC8PM&id=624913682054')
#
# if 'coupon_amount' in data:
#     commission_price_org = (float(data['zk_final_price']) - float(data['coupon_amount'])) * (
#                 float(data['commission_rate']) / float(10000))
#     commission_price = round(commission_price_org - (commission_price_org * float(0.20)), 2)
# else:
#     commission_price_org = float(data['zk_final_price']) * (float(data['commission_rate']) / float(10000))
#     commission_price = round(commission_price_org - (commission_price_org * float(0.20)), 2)
# print(commission_price)
# import paramiko

# '149.28.164.116', 'root', '3aQ+N)m1bcw3Ttwz'

# print('local_bind_port',server.local_bind_port)  # show assigned local port
# work with `SECRET SERVICE` through `server.local_bind_port`.


# ssh = paramiko.SSHClient()
# ssh_policy = paramiko.WarningPolicy()
# ssh.set_missing_host_key_policy(ssh_policy)
# timeout = 5
# socket.setdefaulttimeout(timeout)

# ssh.connect(domain,port=port,timeout=timeout,username=username,password=password)
    # self.ssh.exec_command('pwd')
# transport = self.ssh.get_transport()


# ssh.connect('149.28.164.116', username='root', password='3aQ+N)m1bcw3Ttwz', timeout=10)
# trans = ssh.get_transport()
# stdin,stdout,stderr=ssh.exec_command('ps')
# outlines=stdout.readlines()
# resp=''.join(outlines)
# print(resp)


# trans.request_port_forward
# trans.open_channel("direct-tcpip", dest_addr=(domain,9000), src_addr=('127.0.0.1',9000))
# from openpyxl import load_workbook
# wb = load_workbook(filename = 'B1_rm.xlsx')
# sheet_ranges = wb['Sheet1']
# # print(sheet_ranges['A3'].value)
# list = {}
# i = 2
# while i <= sheet_ranges.max_row:
#
#     tracking_number = sheet_ranges['D'+str(i)].value
#     if tracking_number and tracking_number not in list:
#         list[tracking_number] = 1
#         try:
#             quantity = float(sheet_ranges['N'+str(i)].value)
#         except:
#             print(tracking_number)
#         else:
#             # print(sheet_ranges['M'+str(i)].value)
#             if quantity == 0:
#                 print(tracking_number)
#         try:
#             quantity = float(sheet_ranges['J'+str(i)].value)
#         except:
#             print(tracking_number)
#         else:
#             # print(sheet_ranges['M'+str(i)].value)
#             if quantity == 0:
#                 print(tracking_number)
#         if not sheet_ranges['K'+str(i)].value or not sheet_ranges['L'+str(i)].value:
#             print(tracking_number)
#
#     elif tracking_number:
#         print(tracking_number)
#         sheet_ranges['C' + str(i)] = ''
#         sheet_ranges['D' + str(i)] = ''
#         sheet_ranges['E' + str(i)] = ''
#         sheet_ranges['F' + str(i)] = ''
#         sheet_ranges['G' + str(i)] = ''
#         sheet_ranges['H' + str(i)] = ''
#         # sheet_ranges.delete_rows(i, 1)
#
#         # num = random.randint(1, 1000)
#         # new_order_number = str(num)
#         # print(tracking_number)
#     # weight = sheet_ranges['C'+str(i)].value
#     # details = sheet_ranges['D'+str(i)].value
#     # quantity = sheet_ranges['E'+str(i)].value
#     # print(tracking_number,weight,details,quantity)
#     i+=1
# wb.save('B1_rm.xlsx')

