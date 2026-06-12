#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
# encoding=utf8

import re,random;
import sys, time;

import socks;
import os;
import urllib, mybrowser
from markdown2 import Markdown
from datetime import datetime
import itertools
import mimetools
import mimetypes
from cStringIO import StringIO
import urllib
import urllib2, captcha2upload,json


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


class Ebay:
    """ Test reg forum
    """

    def __init__(self, emit='', qtcode='', header='', orderfinalForm=[], updatestatus='update',captcha_queue=None):
        self.updatestatus = updatestatus
        self.orderfinalForm = orderfinalForm;

        # ua.set_debug_responses(False)

        self.header = header
        self.emit = emit;
        self.qtcode = qtcode;
        self.captcha_queue = captcha_queue
        self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'
        # self.creat_browser()
    def update_captcha(self,captcha_path):
        if self.updatestatus.find('ircbot') == -1:
            try:
                self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "type_captcha",str(captcha_path))
                return 'sent captcha'
            except:
                return

        else:
            return
    def update_status(self,status):
        if self.updatestatus.find('ircbot') == -1:
            print(status)
            try:
                self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "updatestatus",str(status))
            except:
                pass
        else:
            to_user = self.updatestatus.split('|')[1].strip()
            print to_user
            self.send_message(status,to_user=to_user)

    def creat_browser(self):
        self.browser = mybrowser.Rqbrowser()
        self.browser.link_host = 'm.ebay.com'
        self.browser.link_origin = 'https://m.ebay.com'

    def remove_browser(self):
        self.browser.cookies.clear()
        self.browser.close()
        del self.browser

    def write_test_html(self, html):
        c = open('test.html', 'w')
        c.write(html)
        c.close()
        return
    def add_header(self, link_refer, XMLHttpRequest=None, extraHeader={}):
        self.browser.add_header(link_refer, XMLHttpRequest=XMLHttpRequest, extraHeader=extraHeader)

    def fixHTML(self, html):
        return html.replace("'", '"');

    def sell_buy_cgi5(self,item_title='',path_img='',description='',price='',quality='',paypal_account='',cookies_path=None,email='',password='',sock='',buyitnow=True):
        'http://cgi5.ebay.com/ws/eBayISAPI.dll?aidZ153=&MfcISAPICommand=SellHub3'
        self.browser.link_host = 'cgi5.ebay.com'
        self.browser.link_origin = 'http://cgi5.ebay.com'
        self.update_status('Trying List Your Item ^_^')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('http://cgi5.ebay.com/ws/eBayISAPI.dll?aidZ153=&MfcISAPICommand=SellHub3')
                html = r.read()
                linkget=r.geturl()
                print linkget
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen='http://cgi5.ebay.com/ws/eBayISAPI.dll?aidZ153=&MfcISAPICommand=SellHub3',cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            self.write_test_html(html)
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'

    def sell_buy_csr(self,item_title='',path_img='',description='',price='',quality='',paypal_account='',cookies_path=None,email='',password='',sock='',buyitnow=True):
        self.browser.link_host = 'csr.ebay.com'
        self.browser.link_origin = 'http://csr.ebay.com'
        self.update_status('Trying List Your Item ^_^')
        self.add_header('http://csr.ebay.com/cse/start.jsf?nu=1')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('http://csr.ebay.com/cse/start.jsf?nu=1')
                html = r.read()
                linkget=r.geturl()
                print linkget
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen='http://csr.ebay.com/cse/start.jsf?nu=1',cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            self.write_test_html(html)
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        ##
        # listform = None
        # for form in all_forms:
        #     print form
        #     if str(form).find('TextControl(keywords') != -1:
        #         listform = form
        #         break
        # if not listform:
        #     self.write_test_html(html)
        #     print 'Cant find list form'
        #     return 'check die:Cant find list form'
        self.update_status('Trying find your item catalog')
        print 'Find Item catalog'
        # print listform
        # listform.set_all_readonly(False)
        # listform['keywords'] = item_title
        # listform['js'] = '1'
        # request = listform.click()
        request = 'http://csr.ebay.com/sell/results?keywords='+urllib.quote(item_title)+'&fn='+urllib.quote(item_title)

        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'

        ##check login
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        if html.find('paypalEmailAddress">PayPal email address') == -1:
            listform = None
            for form in all_forms:
                # print form
                if str(form).find('TextareaControl(catJSON') != -1:
                    listform = form
                    break
            if not listform:
                self.write_test_html(html)
                print 'check die:cant find catJSON form'
                return 'check die:cant find catJSON form'
            print str(listform)
            if str(listform).find('"ids":["') != -1:
                categoryPath_re=re.search('"ids":\["(.+?)"\]',str(listform))
            else:
                categoryPath_re=re.search('"dcid":\["(.+?)"\]',str(listform))
            if not categoryPath_re:
                print str(listform)
                # self.write_test_html(str(listform))
                print 'check die:cant find categoryPath'
                return 'check die:cant find categoryPath'
            categoryPath = categoryPath_re.group(1).strip().replace('","','|')

            categoryId = categoryPath.split('|')[-1].strip()
            self.update_status('categoryPath='+categoryPath+'&categoryId='+categoryId)
            # print 'categoryPath='+categoryPath+'&categoryId='+categoryId


            link_item_catalog='http://csr.ebay.com/sell/list.jsf?usecase=create&mode=AddItem&categoryId='+categoryId+'&rp=srp&categoryPath='+categoryPath+'&title='+urllib.quote(item_title)+'&motors=0'
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(link_item_catalog)
                    html = r.read()
                    linkget=r.geturl()
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            # allforms = self.browser.selectForm(html,linkget)
            all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen=link_item_catalog,cookies_path=cookies_path,return_html=html)
            if str(html).find('check die') != -1:
                return html
            if html.find('Confirm your account') != -1:
                print 'check die:Confirm your account'
                return 'check die:Confirm your account'

        draftId_re = re.search('name="draftId" value="(.+?)"',html)
        date_time_re = re.search('<!--ts:(.+?)--><',html)
        if not date_time_re:
            print 'check die:cant not find date time for list'
            return 'check die:cant not find date time for list'
        date_time = date_time_re.group(1).strip()
        date_object = datetime.strptime(date_time, "%Y.%m.%d.%H:%M").date()

        date_list = str(date_object.month)+'/'+str(date_object.day)+'/'+str(date_object.year)+'+00:00'

        if not draftId_re:
            self.write_test_html(html)
            print 'check die:cant find draftId'
            return 'check die:cant find draftId'
        draftId = draftId_re.group(1).strip()

        self.update_status('Trying upload your item picture')

        # uaek_re = re.search('name="uaek" value="(.+?)"',html)
        # if not uaek_re:
        #     print 'check die:cant find uaek value'
        #     return 'check die:cant find uaek value'
        # uaes_re = re.search('name="uaes" value="(.+?)"',html)
        # if not uaes_re:
        #     print 'check die:cant find uaes value'
        #     return 'check die:cant find uaes value'

        link_img = self.upload_picture_from_computer(path_img)
        if link_img.find('check die') != -1:
            return link_img
        listform = None
        for form in all_forms:
            if str(form).find('description=') != -1:
                listform = form
                break
        if not listform:
            print 'check die:cant find item description form'
            return 'check die:cant find upload description form'
        link_get_extra_info = 'http://csr.ebay.com/sell/sellertags.jsf?siteId=0&categoryId='+listform['categoryId']+'&draftId='+draftId+'&title='+urllib.quote(item_title)+'&modifiedItemSpecifics='
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_get_extra_info)
                html = r.read()
                # linkget=r.geturl()
                # print html
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        self.update_status('Trying List It!')
        # print html
        item_type_re = re.search('tn":"Type","dataType":"string","selectedValues":"(.+?)"',html)
        if not item_type_re:
            item_type = ''
        else:
            item_type = item_type_re.group(1).strip()
        item_brand_re = re.search('Brand","dataType":"string","selectedValues":"(.+?)"',html)
        if not item_brand_re:
            item_brand = ''
        else:
            item_brand = item_brand_re.group(1).strip()
        markdowner = Markdown()
        description = markdowner.convert(description)
        print listform
        listform.set_all_readonly(False)
        listform['condition'] = ['1000']
        listform['pictureUrl'] = link_img
        listform['pictureUrl0'] = link_img
        listform['description'] = description



        if buyitnow:
            self.update_status('Trying list Buy it now type')

            listform['format'] = ['FixedPrice']
            listform['duration'] = ['Days_10']
            listform['quantity'] = quality
            listform['price'] = str(float(price))
        else:
            self.update_status('Trying list Bid type')
            listform['startPrice'] = str(float(price))
            listform['format'] = ['ChineseAuction']
            try:
                listform['duration'] = ['Days_1']
            except:
                listform['duration'] = ['Days_3']
            listform['quantity'] = '1'
        listform['itemSpecifics'] = 'Brand$^'+item_brand+'!#Type$^'+item_type+'!#'
        listform['modifiedItemSpecifics'] = 'Brand$^'+item_brand+'!#Type$^'+item_type+'!#'

        listform['recommendedFormat'] = 'CHINESE_AUCTION'
        listform['recommendedFormatMessage'] = 'Items in this category sell best as an auction.'
        listform['startPriceRecommended'] = 'true'
        listform['defaultStartPriceRecommended'] = 'true' #note cai co cai khong
        listform['recommendedStartPrice'] = str(int(float(price))-30)
        listform['startPriceRangeMin'] = str(int(float(price))-30)
        listform['startPriceRangeMax'] = str(int(float(price))-30)
        listform['recommendedPrice'] = str(float(price))
        listform['recommendedAuctionBinPrice'] = str(float(price))
        listform['binPriceRangeMin'] = str(float(price)-5)
        listform['binPriceRangeMax'] = str(float(price)+5)
        listform['actualRecommendedStartPrice'] = '-1.0'
        listform['actualRecommendedPrice'] = str(float(price))
        listform['binPriceRecommended'] = 'true'
        listform['actualRecommendedFormat'] = 'CHINESE_AUCTION'
        listform['gotFormatRecommendation'] = 'true'
        listform['gotStartPriceRecommendation'] = 'true'
        listform['gotBinPriceRecommendation'] = 'true'
        listform['isFormatSelected'] = 'true'
        listform['isFormatModified'] = 'true'
        listform['startDateDate'] = date_list#12/17/2015+00:00
        # listform['domesticShippingType'] = ['FLAT_RATE']
        listform['phDomesticShippingType'] = ['FLAT_RATE']
        # listform['rDomesticFreeShipping'] = ['true']
        listform['domesticFreeShipping'] = ['true']
        listform['eBayAPISoapServiceCode0'] = ['UPSGround']
        try:
            listform['shippingFee0'] = '0.00'
        except:
            listform.new_control('text','shippingFee0',{'value':'0.00'})
            listform.fixup()
        listform['rShippingFee0'] = '0.00'
        listform['useShipReco'] = 'false'
        listform['paypalEmailAddress'] = paypal_account
        try:
            listform['autoRelist'] = ['true']
        except:
            pass
        listform['handlingDuration'] = ['3']
        # print listform

        request = listform.click('btnListIt')
        self.add_header('http://csr.ebay.com/cse/start.jsf?nu=1')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget = r.geturl()
                print linkget
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            self.write_test_html(html)
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        self.write_test_html(html)
        self.browser.save_cookies(cookies_path)
        if linkget.find('success') != -1:
            self.update_status('List success!^_^ ')
            item_id_re = re.search('ViewItem&amp;item=(.+?)"',html)
            if item_id_re:
                item_id = item_id_re.group(1).strip()
            else:
                item_id = 'Can not find your item_id'
            return item_id
        else:
            self.update_status('List Error!^_^ ')
            # self.write_test_html(html)
            error_re = re.search('<span class="t"><div>(.+?)</div>',html)
            if error_re:
                error_result = re.sub(r'<.+?>|&.+?;','',re.sub(r'</p>|<br\s*/>','\n',error_re.group(1).strip(),re.DOTALL))
                self.update_status(error_result)
            elif html.find('Select an automatic payment method') != -1:
                self.update_status('Select an automatic payment method for your fees and refundsCharges related to selling and reimbursements')
            elif html.find('Confirm your account') != -1:

                self.update_status('Confirm your account')
                confirm_account = self.confirm_account_ebay(html,linkget)
            return 'check die: List Error!^_^'

    def list_an_item_new(self,item_title='',path_img='',description='',price='',quality='',paypal_account='',cookies_path=None,email='',password='',sock='',buyitnow=True):
        # self.cookiespath = cookiespath
        if int(float(price)) < 30:
            buyitnow = False
        self.browser = mybrowser.Rqbrowser(header=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        self.browser.link_host = 'bulksell.ebay.com'
        self.browser.link_origin = 'http://bulksell.ebay.com'
        self.update_status('Trying List Your Item ^_^')
        link_list_new = 'http://bulksell.ebay.com/ws/eBayISAPI.dll?SingleList&&DraftURL=http://my.ebay.com/ws/eBayISAPI.dll?MyEbayBeta&currentpage=MyeBayNextSavedDraft'
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_list_new)
                html = r.content
                linkget=r.url
                print linkget
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen=link_list_new,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            self.write_test_html(html)
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        link_request = 'http://bulksell.ebay.com/ws/eBayISAPI.dll?SingleList&&DraftURL=http://my.ebay.com/ws/eBayISAPI.dll?MyEbayBeta&currentpage=MyeBayNextSavedDrafts'
        request_data = {}
        request_data['title'] = item_title
        request_data['suggestedCategories'] = '[]'


        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_request,request_data)
                html = r.content
                linkget=r.url

            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        draftId_re = re.search('draftId":"(.+?)"',html)
        pId_re = re.search("message.pId = '(.+?)'",html)
        stok_re = re.search("message.stok = '(.+?)'",html)
        if not pId_re:
            self.write_test_html(html)
            print 'check die:cant find pId_re'
            return 'check die:cant find pId_re'
        if not stok_re:
            self.write_test_html(html)
            print 'check die:cant find stok_re'
            return 'check die:cant find stok_re'
        if not draftId_re:
            self.write_test_html(html)
            print 'check die:cant find draftId_re'
            return 'check die:cant find draftId_re'
        request_link = 'http://bulksell.ebay.com/V4Ajax'
        request = {
        "basePage":{"draftIds":[draftId_re.group(1)],"wsId":"-1","wsType":"-1"},
        "mode":"INDIVIDUAL",
        "action":"PUBLISH",
        "layerName":"EDITPANE",
        "variation":'null',
        "callbackFun":"publish_item",
        "currencyInfo":{"currencySymbolLeft":"true","singularName":"U.S. dollars","moneySymbol":"$","decimalSymbol":".","groupingSymbol":",","gS":",","decimalPlaces":"2","currencyCode":"USD","pluralName":"U.S. dollar"},
        "singleList":"true",
        "listingMode":"AddItem",
        "updateRequired":"true",
        "fields":{"galleryPlus":"false","title":"apple watch","bold":"false","subtitle":"","itemCondition":"1000","itemConditionDescription":"","description":"aaaaaaaaaaaaaaa","rteMode":"0","_st_Brand":"Apple","_st_Model":"","_st_MPN":"Does Not Apply","_st_Serial Number":"","_st_Series":"","_st_Operating System":"","_st_Compatible Operating System":"","_st_Storage Capacity":"","_st_Case Size":"","_st_Bundle Listing":"-","_st_Case Material":"","_st_Band Material":"","_st_Band Color":"","_st_Network":"","_st_Features":"","_st_Country/Region of Manufacture":"-","domesticShipping":"FLAT_RATE","domUseRateTableId":"false","domesticRateTable":"false","shipService1":"UPSGround","shipFee1":"0.00","freeShipping":"true","domesticSurchargeCost1":"false","localPickup":"false","localPickupFee":"","shipsWithinDays":"5","intlShipping":"NOT_SPECIFIED","pmPayPal":"true","paypalEmail":"fsgrafix_mun@outlook.com","immediatePayment":"false","paymentInstructions":"","prevSelectedReturns":"ReturnsNotAccepted","returnsAccepted":"ReturnsNotAccepted","cat1":"178893","cat2":"","format":"ChineseAuction","duration":"Days_7","schldLstng":"false","startPrice":"0.99","binPrice":"","reservePrice":"","lotSizeFlag":"false","privateAuction":"false","upc":"Does not apply","pkgSize":"PackageThickEnvelope","pkgLength":"","pkgWidth":"","pkgHeight":"","pkgIrregular":"false","estimatedWeight":"CUSTOM_WEIGHT","majorUnitWeight":"0","minorUnitWeight":"0","itemCountry":"US","itemPostalCode":"92869","location":"Orange, California","salesTaxRegion":"--","salesTaxRate":"","applyTaxToShipping":"false","autoRelist":"false"},
        "customFields":{},
        "epsUrls":"http://i.ebayimg.com/00/s/MTQ2N1gxMjAw/z/vJoAAOSw5l5Zmp1N/$_57.JPG?set_id=8800005007;http://i.ebayimg.com/00/s/MTQ2N1gxMjAw/z/dvEAAOSwJThZmp1R/$_57.JPG?set_id=8800005007",
        "savePref":"true",
        "byPassUpdate":"false",
        "isAdd":"",
        "saveUlsi":"true",
        "edpCrNew":"false",
        "deletedFields":[],
        "draftMode":"Listing",
        "restricted":"false",
        "customPreference":{"preferences":{"scheduleStartTime":"true","reservePrice":"true","sellAsLot":"true","privateListing":"true","eBayForCharity":"true","additionalPaymentOptions":"true","additionalCheckoutInstructions":"true","salesTax":"true","additionalReturnPolicyDetails":"true","internationalShipping":"true","shippingExclusionList":"true","shippingRateTable":"true"},"sellerDetails":["NO_STORE_SUBSCRIPTION","NO_SHIPPING_DISCOUNTS","NON_SM_SELLER"]},
        "isvShown":"false"
        }
        print  stok_re.group(1),pId_re.group(1)
        request_data={}
        request_data['svcid'] = 'WRKSPC_LAYER_SERVICE'
        request_data['stok'] = stok_re.group(1)
        request_data['pId'] = pId_re.group(1)
        request_data['v'] = '0'
        request_data['reqttype'] = 'JSON'
        request_data['resptype'] = 'JSON'
        request_data['clientType'] = 'Firefox:54:'
        request_data['request'] = request

        i = 0
        while i <= 4:
            try:
                self.add_header('http://bulksell.ebay.com/ws/eBayISAPI.dll?SingleList&&DraftURL=http://my.ebay.com/ws/eBayISAPI.dll?MyEbayBeta&currentpage=MyeBayNextSavedDrafts')
                r = self.browser.open(request_link, request_data)
                html = r.content
                linkget=r.url
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'

        listform = None
        for form in all_forms:
            print form
            if str(form).find('TextareaControl(itemConditionDescription') != -1:
                listform = form
                break
        if not listform:
            self.write_test_html(html)
            print 'check die:cant find itemConditionDescription form'
            return 'check die:cant find itemConditionDescription form'
        listform.set_all_readonly(False)
        listform['itemCondition']=['1000']
        listform['js']= '1'
        listform['description']= description
        listform['paypalEmail']= paypal_account
        link_img = self.upload_picture_from_computer(path_img)
        if link_img.find('check die') != -1:
            return link_img
        listform['upc'] = 'Does not apply'
        # listform['BrandISS'] = 'st_selval_0_0'
        listform['st_selval_0_1'] = item_title.split(' ')[0].strip()
        if buyitnow:
            self.update_status('Trying list Buy it now type')
            listform['format'] = ['9']
            listform['duration'] = ['10']
            # listform['quantity'] = quality
            listform['binPrice'] = price
        else:
            self.update_status('Trying list Bid type')
            listform['format'] = ['1']
            listform['startPrice'] = price
            try:
                listform['duration'] = ['1']
            except:
                listform['duration'] = ['3']
        listform['shipService1'] = ['3']

        listform['shipFee1'] = '0.00'
        listform['shipsWithinDays'] = ['5']
        listform['returnsAccepted'] = ['ReturnsNotAccepted']
        # listform['st_tmdata_0_0'] = 'Brand!?^5!?^0!?^""!?^2'
        # listform['MPNISS'] = 'st_selval_0_1'
        # listform['st_tmdata_0_1'] = 'MPN!?^5!?^0!?^""!?^2'
        # listform['TypeISS'] = 'st_selval_0_2'
        # listform['st_tmdata_0_2'] = 'Type!?^2!?^0!?^""!?^2'
        listform.new_control('hidden', 'pictureUrl',   {'value': link_img})
        picData_info_re = re.search('sWarnModelData=\{(.+?)\};',html)
        if not picData_info_re:
            self.write_test_html(html)
            print 'check die:Cant find your picData'
            return 'check die:Cant find your picData'
        picData_info = eval('{'+picData_info_re.group(1)+'}')
        picData_info['item']['title'] = urllib.quote(item_title)
        picData_info['item']['conditionID'] = 1000
        picData_info['item']['warningcount'] = 0
        picData_info['item']['onmove'] = False
        picData_info['item']['productDetails']['upc'] = 'Does+not+apply'
        picData_info['item']['pictureDetails']['galleryURL'] = link_img
        picData_info['item']['pictureDetails']['pictureURL'] = [link_img]
        print picData_info
        listform.fixup()
        request = listform.click('aidZ1')
        i = 0
        while i <= 4:
            try:
                self.add_header(linkget)
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'

        listform = None
        for form in all_forms:
            # print form
            if str(form).find('SubmitControl(aidZ18=List your item') != -1:
                listform = form
                break
        if not listform:
            self.write_test_html(html)
            print 'check die:cant find itemConditionDescription form'
            return 'check die:cant find itemConditionDescription form'
        request = listform.click('aidZ18')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        self.write_test_html(html)
        self.browser.save_cookies(cookies_path)
        if html.find('Congratulations') != -1:
            self.update_status('List success!^_^ ')
            item_id_re = re.search('ViewItem&amp;item=(.+?)"',html)
            if item_id_re:
                item_id = item_id_re.group(1).strip()
            else:
                item_id = 'Can not find your item_id'
            return item_id
        else:
            self.update_status('List Error!^_^ ')
            # self.write_test_html(html)
            error_re = re.search('<span class="t"><div>(.+?)</div>',html)
            if error_re:
                error_result = re.sub(r'<.+?>|&.+?;','',re.sub(r'</p>|<br\s*/>','\n',error_re.group(1).strip(),re.DOTALL))
                self.update_status(error_result)
            elif html.find('Select an automatic payment method') != -1:
                self.update_status('Select an automatic payment method for your fees and refundsCharges related to selling and reimbursements')
            elif html.find('Confirm your account') != -1:

                self.update_status('Confirm your account')
                confirm_account = self.confirm_account_ebay(html,linkget)
            return 'check die: List Error!^_^'

    def list_an_item(self,item_title='',path_img='',description='',price='',quality='',paypal_account='',cookies_path=None,email='',password='',sock='',buyitnow=True):
        # self.cookiespath = cookiespath
        if int(float(price)) < 30:
            buyitnow = False
        self.browser = mybrowser.Mechanizebrowser(header=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        self.browser.link_host = 'cgi5.ebay.com'
        self.browser.link_origin = 'http://cgi5.ebay.com'
        self.update_status('Trying List Your Item ^_^')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('http://cgi5.ebay.com/ws/eBayISAPI.dll?aidZ153=&MfcISAPICommand=SellHub3')
                html = r.read()
                linkget=r.geturl()
                print linkget
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen='http://cgi5.ebay.com/ws/eBayISAPI.dll?aidZ153=&MfcISAPICommand=SellHub3',cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            self.write_test_html(html)
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        listform = None
        for form in all_forms:
            # print form
            if str(form).find('TextControl(keywords') != -1:
                listform = form
                break
        if not listform:
            self.write_test_html(html)
            print 'check die:cant find keywords form'
            return 'check die:cant find keywords form'
        listform['keywords'] = item_title
        request = listform.click('aidZ4')
        i = 0
        while i <= 4:
            try:
                self.add_header(linkget)
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()

            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'

        listform = None
        for form in all_forms:
            print form
            if str(form).find('SelectControl(cat1') != -1:
                listform = form
                break
        if not listform:
            self.write_test_html(html)
            print 'check die:cant find cat1 form'
            return 'check die:cant find cat1 form'
        request = listform.click('aidZ1')
        i = 0
        while i <= 4:
            try:
                self.add_header(linkget)
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'

        listform = None
        for form in all_forms:
            print form
            if str(form).find('TextareaControl(itemConditionDescription') != -1:
                listform = form
                break
        if not listform:
            self.write_test_html(html)
            print 'check die:cant find itemConditionDescription form'
            return 'check die:cant find itemConditionDescription form'
        listform.set_all_readonly(False)
        listform['itemCondition']=['1000']
        listform['js']= '1'
        listform['description']= description
        listform['paypalEmail']= paypal_account
        link_img = self.upload_picture_from_computer(path_img)
        if link_img.find('check die') != -1:
            return link_img
        listform['upc'] = 'Does not apply'
        # listform['BrandISS'] = 'st_selval_0_0'
        listform['st_selval_0_1'] = item_title.split(' ')[0].strip()
        if buyitnow:
            self.update_status('Trying list Buy it now type')
            listform['format'] = ['9']
            listform['duration'] = ['10']
            # listform['quantity'] = quality
            listform['binPrice'] = price
        else:
            self.update_status('Trying list Bid type')
            listform['format'] = ['1']
            listform['startPrice'] = price
            try:
                listform['duration'] = ['1']
            except:
                listform['duration'] = ['3']
        listform['shipService1'] = ['3']

        listform['shipFee1'] = '0.00'
        listform['shipsWithinDays'] = ['5']
        listform['returnsAccepted'] = ['ReturnsNotAccepted']
        # listform['st_tmdata_0_0'] = 'Brand!?^5!?^0!?^""!?^2'
        # listform['MPNISS'] = 'st_selval_0_1'
        # listform['st_tmdata_0_1'] = 'MPN!?^5!?^0!?^""!?^2'
        # listform['TypeISS'] = 'st_selval_0_2'
        # listform['st_tmdata_0_2'] = 'Type!?^2!?^0!?^""!?^2'
        listform.new_control('hidden', 'pictureUrl',   {'value': link_img})
        picData_info_re = re.search('sWarnModelData=\{(.+?)\};',html)
        if not picData_info_re:
            self.write_test_html(html)
            print 'check die:Cant find your picData'
            return 'check die:Cant find your picData'
        picData_info = eval('{'+picData_info_re.group(1)+'}')
        picData_info['item']['title'] = urllib.quote(item_title)
        picData_info['item']['conditionID'] = 1000
        picData_info['item']['warningcount'] = 0
        picData_info['item']['onmove'] = False
        picData_info['item']['productDetails']['upc'] = 'Does+not+apply'
        picData_info['item']['pictureDetails']['galleryURL'] = link_img
        picData_info['item']['pictureDetails']['pictureURL'] = [link_img]
        print picData_info
        listform.fixup()
        request = listform.click('aidZ1')
        i = 0
        while i <= 4:
            try:
                self.add_header(linkget)
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'

        listform = None
        for form in all_forms:
            # print form
            if str(form).find('SubmitControl(aidZ18=List your item') != -1:
                listform = form
                break
        if not listform:
            self.write_test_html(html)
            print 'check die:cant find itemConditionDescription form'
            return 'check die:cant find itemConditionDescription form'
        request = listform.click('aidZ18')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        if html.find('Confirm your account') != -1:
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        self.write_test_html(html)
        self.browser.save_cookies(cookies_path)
        if html.find('Congratulations') != -1:
            self.update_status('List success!^_^ ')
            item_id_re = re.search('ViewItem&amp;item=(.+?)"',html)
            if item_id_re:
                item_id = item_id_re.group(1).strip()
            else:
                item_id = 'Can not find your item_id'
            return item_id
        else:
            self.update_status('List Error!^_^ ')
            # self.write_test_html(html)
            error_re = re.search('<span class="t"><div>(.+?)</div>',html)
            if error_re:
                error_result = re.sub(r'<.+?>|&.+?;','',re.sub(r'</p>|<br\s*/>','\n',error_re.group(1).strip(),re.DOTALL))
                self.update_status(error_result)
            elif html.find('Select an automatic payment method') != -1:
                self.update_status('Select an automatic payment method for your fees and refundsCharges related to selling and reimbursements')
            elif html.find('Confirm your account') != -1:

                self.update_status('Confirm your account')
                confirm_account = self.confirm_account_ebay(html,linkget)
            return 'check die: List Error!^_^'

    def confirm_question_ebay(self,html,linkget):
        question_ebay = re.search('<label for="questionId2">(.+?)</label>',html).group(1).strip()
        try:
            self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "type_question",question_ebay)
        except:
            pass
        else:
            question_result = self.captcha_queue.get()
            if str(question_result).find('cancel') != -1:
                return
            all_forms = self.browser.selectForm(html,linkget)
            confirm_form = None
            for form in all_forms:
                print form
                if str(form).find('RadioControl(questionId') != -1:
                    confirm_form=form
                    break
            if not confirm_form:
                return
            confirm_form['answer'] = str(question_result)
            confirm_form['questionId'] = ['100000002']
            request = confirm_form.click('submitBtn')
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request)
                    html = r.read()
                    linkget=r.geturl()
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            self.confirm_code_ebay(html,linkget)

    def confirm_code_ebay(self,html,linkget):
        all_forms = self.browser.selectForm(html,linkget)
        confirm_form = None
        for form in all_forms:
            print form
            if str(form).find('TextControl(code') != -1:
                confirm_form=form
                break
        if not confirm_form:
            return
        try:
            self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "type_code",'type_code')
        except:
            pass
        else:
            question_result = self.captcha_queue.get()
            if str(question_result).find('cancel') != -1:
                return
            confirm_form['code'] = question_result
            request = confirm_form.click('submitBtn')
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request)
                    html = r.read()
                    linkget=r.geturl()
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            self.write_test_html(html)

    def confirm_account_ebay(self,html,linkget):
        if html.find('<label for="questionId2">') != -1:
            print 'Question'
            self.confirm_question_ebay(html,linkget)
        if html.find('Enter Confirmation code') != -1:
            print 'Code'
            self.confirm_code_ebay(html,linkget)
        else:
            try:
                self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "type_confirm",'confirm_account')
            except:
                pass
            else:
                confirm_result = self.captcha_queue.get()
                if str(confirm_result).find('cancel') != -1:
                    return
                all_forms = self.browser.selectForm(html,linkget)
                confirm_form = None
                for form in all_forms:
                    print form
                    if str(form).find('fullscale POST') != -1:
                        confirm_form=form
                        break
                if not confirm_form:
                    return
                confirm_form['selectedOption'] = [str(confirm_result).lower()]
                request = confirm_form.click('submitBtn')
                i = 0
                while i <= 4:
                    try:
                        r = self.browser.open(request)
                        html = r.read()
                        linkget=r.geturl()
                    except:
                        time.sleep(1)
                    else:
                        break
                    i += 1
                if i >= 4:
                    print 'check die:socks die'
                    return 'check die:socks die'
                if html.find('<label for="questionId2">') != -1:
                    self.confirm_question_ebay(html,linkget)
                self.write_test_html(html)

    def upload_picture_from_computer(self,path_picture,uaek='',uaes=''):
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('http://cgi5.ebay.com/_picupload/main?popup=1&ver=3&serial=1&hostAppUrl=http%3A%2F%2Fcgi5.ebay.com')
                html = r.read()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        uaek_re = re.search('name="uaek" value="(.+?)"',html)
        if not uaek_re:
            print 'check die:cant find uaek value'
            return 'check die:cant find uaek value'
        uaes_re = re.search('name="uaes" value="(.+?)"',html)
        if not uaes_re:
            print 'check die:cant find uaes value'
            return 'check die:cant find uaes value'
        print path_picture
        request_url = 'http://msa-b1.cgi5.ebay.com/ws/eBayISAPI.dll?EpsBasic'
        form = MultiPartForm()
        form.add_field('s', 'Supersize')
        form.add_field('n', 'i')
        form.add_field('v', '2')
        form.add_field('aXRequest', '2')
        form.add_field('wm', '2')
        form.add_field('uaek', uaek_re.group(1))
        form.add_field('uaes', uaes_re.group(1))

        path, file = os.path.split(path_picture);
        # Add a fake file
        f = open(path_picture,'rb')
        form.add_file('Filedata', file,
                      fileHandle=StringIO(f.read()))
        f.close()
        request = urllib2.Request(request_url)
        body = str(form)
        request.add_header('Content-type', form.get_content_type())
        request.add_header('Content-length', len(body))
        request.add_data(body)
        # print request.get_data()
        self.browser.link_host = 'msa-b1.cgi5.ebay.com'
        # self.browser.link_origin='http://cgi5.ebay.com'
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        self.write_test_html(html)

        if html.find('$_1.JPG') == -1:
            print 'check die:cant upload img by path'
            return 'check die:cant upload img by path'
        link_img = html.replace('VERSION:2;','')
        print link_img
        return link_img

    def upload_picture_by_url(self,link_picture):
        link_upload_pic='http://cgi5.ebay.com/_picupload/main?popup=1&ver=3&serial=1&hostAppUrl=http%3A%2F%2Fcgi5.ebay.com'
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_upload_pic)
                html = r.read()
                linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        uploadform = None
        all_forms = self.browser.selectForm(html,linkget)
        for form in all_forms:
            if str(form).find('FileControl(d=') != -1:
                uploadform = form
                break
        if not uploadform:
            return 'check die:cant find upload IMG'
        uaek= re.search("userAppEncKey:\s*'(.+?)'",html).group(1).strip()
        uaes= re.search("userAppEncStr:\s*'(.+?)'",html).group(1).strip()
        # print uaes,uaek
        data = {}
        data['s'] = 'Standard'
        data['n'] = 'i'
        data['v'] = '2'
        data['aXRequest'] = '2'
        data['uaek'] = uaek
        data['uaes'] = uaes
        data['w'] = link_picture
        data['wm'] = ''

        self.browser.link_host = 'msa-b1.cgi5.ebay.com'
        self.browser.link_origin='http://cgi5.ebay.com'
        # uploadform.add_file(open(path_img, 'rb'), 'image/jpeg', os.path.basename(path_img), nr=0)
        # uploadform.set_all_readonly(False)
        # uploadform['s'] = 'Supersize'
        self.add_header('http://cgi5.ebay.com/_picupload/main?popup=1&ver=3&serial=1&hostAppUrl=http%3A%2F%2Fcgi5.ebay.com')
        # request = uploadform.click()
        # print urllib.quot(data)
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('http://msa-b1.cgi5.ebay.com/ws/eBayISAPI.dll?EpsBasic',urllib.urlencode(data))
                html = r.read()
                # linkget=r.geturl()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        if html.find('VERSION:2;') != -1:
            link_img = re.search('VERSION:2;(.+)',html).group(1).strip()
            print link_img
        else:
            print 'cant upload img'

    def get_ebay_selling_infomation(self,email,password,cookiespath):


        self.update_status('Trying get ebay selling infomation')
        print 'Trying get ebay selling infomation'

        self.add_header('https://my.ebay.com/ws/eBayISAPI.dll?MyeBay&CurrentPage=MyeBayPersonalInfo&gbh=1&ssPageName=STRK:ME:LNLK')
        self.browser.open('https://my.ebay.com/ws/eBayISAPI.dll?MyeBay&CurrentPage=MyeBayPersonalInfo&gbh=1&ssPageName=STRK:ME:LNLK')
        html = self.browser.read()
        linkget=self.browser.get_url()
        html = self.fixHTML(html)
        print html
        self.write_test_html(html)
        self.update_status('Trying get selling infomation')
        selling_infore = re.search('class="cellHd">(.+?)</',html)
        if selling_infore:
            selling_info = selling_infore.group(1).strip()
        else:
            selling_info = 'You can sell up to unlimited items or up to $unlimited per month, whichever comes first.'
        self.update_status(selling_info)
        print selling_info

        member_idre = re.search('userid=(.+?)&',html)
        if member_idre:
            member_id = member_idre.group(1).strip()
            self.update_status('Your ebay username:'+member_id)
            self.update_status('Trying get ebay infomation')
            infomation_eb = self.get_information(member_id)
        else:
            self.write_test_html(html)
            infomation_eb = ''
        path, file = os.path.split(cookiespath)
        print path
        self.update_status(email+'|'+password+'|'+infomation_eb)
        # if not os.path.isfile(path+'/ebay_infomation.txt'):
        #     print path+'/ebay_infomation.txt'
        f = open(path+'/ebay_infomation.txt','w')

        f.write(email+'|'+password+'|'+infomation_eb+'\n')
        f.write(selling_info+'\n')
        # ebay_info = self.create_paypal(email,password,get_info=True)
        # f.write(ebay_info+'\n')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('http://ip-api.com/json')
                html = self.browser.read()
                linkget=self.browser.get_url()
                print html
                my_ip = re.search('query":"(.+?)"',html).group(1).strip()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            my_ip=''
        f.write('Login Ip is:'+my_ip+'\n')
        f.write('Cookies path:'+str(cookiespath)+'\n')
        f.write('Header:'+str(self.browser.header)+'\n')
        f.close()
        self.update_status('Login Ip is:'+my_ip)
        return email+'|'+password+'|'+infomation_eb+'#==#'+my_ip+'#==#'+selling_info+'#==#'+self.header

    def re_loginebay(self,html,linkget,email,password,link_reopen='',cookies_path='',return_html=''):
        # self.browser.link_host = 'signin.ebay.com'
        # self.browser.link_origin = 'https://signin.ebay.com'
        all_forms = self.browser.selectForm(html,linkget)
        html_login = self.get_loginform_and_login(html,linkget,email,password,link_reopen=link_reopen)
        if html_login.find('check die') != -1:
            if html_login.find('Cant find login form') != -1:
                return (all_forms,html)
            else:
                return None,html_login
        elif html_login.find('title="Captcha Image" src="') != -1:

            link_captcha = re.search('title="Captcha Image" src="(.+?)"',html_login).group(1).strip().replace('amp;','')

            self.write_test_html(html_login)
            self.update_status('Type your captcha')
            link_captcha_show = self.save_captcha(link_captcha)
            captcha_tokenstring = re.search('\&tokenString=(.+?)\&',link_captcha).group(1).strip()
            if link_captcha_show.find('check die') == -1:
                send_captcha = self.update_captcha(link_captcha_show)
                if send_captcha:
                    captcha_result = self.captcha_queue.get()
                else:
                    captcha_result = raw_input('input captcha')
                print 'Captcha:'+str(captcha_result)
                html = self.get_loginform_and_login(html_login,linkget,email,password,captcha_result=captcha_result,captcha_tokenstring=captcha_tokenstring,link_reopen=link_reopen)
                self.write_test_html(html)
                print '======dien====='
                if html.find('check die') != -1:
                    return None,html
                if link_reopen:
                    print 'Reopen Link:'+link_reopen
                    i = 0
                    while i <= 4:
                        try:
                            r = self.browser.open(link_reopen)
                            html = r.content
                            linkget=r.url
                        except:
                            time.sleep(1)
                        else:
                            break
                        i += 1
                    if i >= 4:
                        print 'check die:socks die'
                        return None,'check die:socks die'
                    # self.write_test_html(html)
                allforms = self.browser.selectForm(html,linkget)
                return allforms,html
        else:
            self.update_status('Trying relogin to your account')
            # self.browser.save_cookies(cookies_path)
            if link_reopen:
                print link_reopen
                i = 0
                while i <= 4:
                    try:
                        r = self.browser.open(link_reopen)
                        html = r.content
                        linkget=r.url
                    except:
                        time.sleep(1)
                    else:
                        break
                    i += 1
                if i >= 4:
                    print 'check die:socks die'
                    return None,'check die:socks die'
                allforms = self.browser.selectForm(html,linkget)
                return allforms,html
            else:
                allforms = self.browser.selectForm(html_login,linkget)
                return allforms,html_login

    def get_loginform_and_login(self,html,linkget,email,password,captcha_result='',captcha_tokenstring='',link_reopen=''):
        loginform = None
        all_forms = self.browser.selectForm(html,linkget)
        for form in all_forms:
            # print form
            if str(form).find('pass=') != -1:
                loginform = form
                break
        if not loginform:
            c = open('dien.html','w')
            c.write(html)
            print 'check die:Cant find login form'
            return 'check die:Cant find login form'
        print email,password
        print loginform
        # loginform.set_all_readonly(False)
        # if link_reopen:
        #     loginform['ru'] = link_reopen
        loginform['userid'] = str(email)
        loginform['pass'] = str(password)
        if str(loginform).find('keepMeSignInOption3') != -1:
            loginform['keepMeSignInOption3'] = ['on']
        if captcha_result and captcha_tokenstring:
            print loginform
            loginform['tokenText'] = str(captcha_result)
            loginform.new_control('text','htmid',{'value':''})
            loginform.new_control('text','kdata',{'value':''})
            loginform.new_control('text','tokenstring',{'value':captcha_tokenstring})
            loginform.fixup()
            print urllib.unquote(captcha_tokenstring)
            loginform['tokenstring'] = captcha_tokenstring
        # request = loginform.click('sgnBt')

        self.browser.submit_form(loginform)
        html = self.browser.read()
        linkget=self.browser.get_url()
        html = self.fixHTML(html)
        # linkget = r.geturl()

        # self.write_test_html(html)
        c = open('test_login.html', 'w')
        c.write(html)
        c.close()
        if html.find('name="pass"') != -1 or html.find('Change your password') != -1:
            print 'check die:your password incorect'
            return 'check die:your password incorect'
        # if link_reopen:
        #     i = 0
        #     while i <= 4:
        #         try:
        #             if link_reopen:
        #                 r = self.browser.open(link_reopen)
        #             else:
        #                 r = self.browser.open('http://my.ebay.com/ws/eBayISAPI.dll?MyEbayBeta&MyEbay=&CurrentPage=MyeBayAllSelling&ssPageName=STRK%3AME%3ALNLK%3AMESX&gbh=1&guest=1')
        #             html = r.read()
        #             linkget = r.geturl()
        #         except:
        #             time.sleep(1)
        #         else:
        #             break
        #         i += 1
        #     if i >= 4:
        #         print 'check die:socks die'
        #         return 'check die:socks die'
        return html

    def check_ebay_status(self,html,linkget,email,password):
        if html.find('name="pass"') == -1:
            self.add_header('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn')
            if linkget.find('ChangeSecretQuestion') != -1:
                self.update_status('Trying to change secret question')
                all_forms = self.browser.selectForm(html,linkget)
                questionform=None
                for form in all_forms:
                    if str(form).find('secretQuestion1') != -1:
                        questionform = form
                        break
                if questionform:

                    questionform.set_all_readonly(False)
                    questionform['secretQuestion1'] = '100000003'
                    questionform['secretQuestion2'] = '100000006'
                    questionform['secretQuestion3'] = '100000008'
                    questionform['dp_SECRET_QUESTION_1'] = 'Name of your first pet?'
                    questionform['dp_SECRET_QUESTION_2'] = 'Your childhood nickname?'
                    questionform['dp_SECRET_QUESTION_3'] = 'Name of the street you grew up on?'
                    questionform['secretAnswer1'] = 'bull'
                    questionform['secretAnswer2'] = 'mun'
                    questionform['secretAnswer3'] = 'ngoctruc'
                    request = questionform.click()
                    i = 0
                    while i <= 4:
                        try:
                            r = self.browser.open(request)
                        except:
                            time.sleep(1)
                        else:
                            break
                        i += 1
                    if i >= 4:
                        print 'check die:socks die'
                        return 'check die:socks die'
                    print 'change question success'
                    self.update_status('Change secret question success')

            return 'Login success'
        elif html.find('title="Captcha Image" src="') != -1:
            link_captcha = re.search('title="Captcha Image" src="(.+?)"',html).group(1).strip().replace('amp;','')

            self.write_test_html(html)
            self.update_status('Type your captcha')
            link_captcha_show = self.save_captcha(link_captcha)
            captcha_tokenstring = re.search('\&tokenString=(.+?)\&',link_captcha).group(1).strip()
            if link_captcha_show.find('check die') == -1:
                print link_captcha_show
                print captcha_tokenstring
                self.update_captcha(link_captcha_show)
                captcha_result = self.captcha_queue.get()
                print 'Captcha:'+str(captcha_result)
                html = self.get_loginform_and_login(html,linkget,email,password,captcha_result=captcha_result,captcha_tokenstring=captcha_tokenstring)
                # self.write_test_html(html)
                if html.find('check die') != -1:
                    return html
                else:
                    check_status = self.check_ebay_status(html,linkget,email,password)
                    return check_status
            else:
                return link_captcha_show
        else:
            self.write_test_html(html)
            self.update_status('your password incorect')
            print 'your password incorect'
            return 'check die:your password incorect#==#'+email

    def login_savecookies(self,email, password,sock='',cookiespath=None):
        self.browser = mybrowser.Rqbrowser(agent=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookiespath):
            print 'load cookies'

            self.browser.load_cookies(cookiespath)
        self.update_status('Trying go to ebay')
        i = 0
        while i <= 4:
            try:
                self.browser.link_host = 'www.ebay.com'
                r = self.browser.open('http://ebay.com')
            except Exception as e:
                print e
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        self.update_status('Trying to login your ebay')

        self.browser.link_host = 'signin.ebay.com'
        self.browser.link_origin = 'https://signin.ebay.com'
        self.browser.open('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn')
        html = self.browser.read()
        linkget=self.browser.get_url()

        html = self.get_loginform_and_login(html,linkget,email,password)
        if html.find('check die') != -1:
            return html
        else:
            print 'check ebay status'
            cookiespath = self.save_cookies(cookiespath,email)
            check_status = self.check_ebay_status(html,linkget,email,password)
            if check_status.find('check die') != -1:
                return check_status
            else:
                info_account = self.get_ebay_selling_infomation(email,password,cookiespath)
                cookiespath = self.save_cookies(cookiespath,email)
                self.update_status('Login and get cookies done ^.^')
                return info_account+'#==#'+cookiespath

    def save_captcha(self,link_captcha,check=False):
        alphabet = 'abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 5
        max = 10
        stringimg = ''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        captcha_save = 'captchaIMG' + stringimg + '.png'
        f = open(captcha_save, 'wb');
        i = 0
        while i <= 4:
            try:
                response = self.browser.open(link_captcha);
                if check:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk: # filter out keep-alive new chunks
                            f.write(chunk)
                else:
                    data = True;
                    while data:
                        data = response.read(1024);
                        f.write(data);
                    response.close();
                f.close();
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'

        return captcha_save

    def save_cookies(self,cookiespath,email):
        if cookiespath and email:
            cookiespath = str(cookiespath).replace('\\','/')
            username_new = email.split('@')[0].strip()
            username_old = str(cookiespath).replace('\\','/').split('/')[-1].strip()
            if os.path.isdir(cookiespath) and username_new != username_old:
                os.renames(cookiespath,str(cookiespath).replace(username_old,username_new))
                cookiespath = str(cookiespath).replace(username_old,username_new)
            if not os.path.isfile(cookiespath) and cookiespath:
                if not os.path.isdir(cookiespath):
                    os.makedirs(cookiespath)
                cookiespath = cookiespath+'/cookies.txt'
                if not os.path.isfile(cookiespath):
                    f = open(cookiespath,'w')
                    f.close()
            self.browser.save_cookies(cookiespath)
            self.update_status('Saved ebay cookies:'+str(cookiespath).replace('\\','/'))
            try:
                self.emit(self.qtcode.SIGNAL('update(QString,QString)'), "update_cookiespath",
                          cookiespath + '#==#' + email);
            except:
                pass
            return cookiespath

    def site_login(self, email, password,sock='',sock_type=''):

        print('trying login to ebay:'+email+'|'+password)

        self.browser = mybrowser.Rqbrowser(agent=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)

        self.update_status('Trying go to ebay')
        i = 0
        while i <= 4:
            try:
                self.browser.link_host = 'signin.ebay.com'
                self.browser.link_origin = 'https://signin.ebay.com'
                self.browser.open('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn')
                html = self.browser.read()
                linkget = self.browser.get_url()
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('check die:socks die')
            return 'check die:socks die'
        self.update_status('Trying to login your ebay')
        ###

        loginform = None

        all_forms = self.browser.selectForm(html,linkget)
        for form in all_forms:
            print(form)
            if str(form).find('pass=') != -1:
                loginform = form
                break
        if not loginform:

            captcha_linkre = re.search('title="Captcha Image" src="(.+?)"',html)
            if captcha_linkre:
                print('========back list socks========')
                return 'check die:socks die'
            else:
                c = open('dien.html','w')
                c.write(html)
                print('check die:socks die')
                return 'check die:socks die'


        loginform['userid'] = str(email)
        loginform['pass'] = str(password)
        if str(loginform).find('keepMeSignInOption3') != -1:
            loginform['keepMeSignInOption3'] = ['on']
        i = 0
        while i <= 4:
            try:
                self.browser.submit_form(loginform)
                html = self.browser.read()
                linkget = self.browser.get_url()
                html = self.fixHTML(html)
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('check die:socks die')
            return 'check die:socks die'
        if html.find('Reset your password') != -1:
            print('===Black list email===')
            return 'check die:socks die';

        elif html.find('name="pass"') == -1 and html.find('userInfo" name="input" value="') == -1:
            self.write_test_html(html)
            print('==logged==')
            print('Trying get ebay selling infomation')
            i = 0
            while i <= 4:
                try:
                    self.add_header(
                        'https://my.ebay.com/ws/eBayISAPI.dll?MyeBay&CurrentPage=MyeBayPersonalInfo&gbh=1&ssPageName=STRK:ME:LNLK')
                    self.browser.open(
                        'https://my.ebay.com/ws/eBayISAPI.dll?MyeBay&CurrentPage=MyeBayPersonalInfo&gbh=1&ssPageName=STRK:ME:LNLK')
                    html = self.browser.read()
                    linkget = self.browser.get_url()
                    html = self.fixHTML(html)
                    # print html
                    # self.write_test_html(html)
                except Exception as e:
                    print(e)
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print('check die:socks die')
                return 'check die:socks die'

            self.update_status('Trying get selling infomation')

            member_idre = re.search('userid=(.+?)&', html)
            if member_idre:
                member_id = member_idre.group(1).strip()
                return member_id
            else:
                # self.write_test_html(html)
                print('===KO BIET==')
                return 'check die:your password incorect';
            # timuser = re.search('<span class="user">(.+?)</', result)
            # if timuser:
            #     username = timuser.group(1).strip()
            #     print username
            #
            #     return username
            # else:
            #     print 'than kinh'
            #
            #     return'check die:socks die';

        elif html.find('eBayISAPI.dll?LoadBotImage') != -1:

            print('========Captcha==========')
            return 'check die:socks die';
            # loginforms = self.browser.selectForm(r)
            # checkform = None
            # for form in loginforms:
            #     print form
            #     if str(form).find('PasswordControl(pass') != -1:
            #         checkform=form
            #         break
            # self.write_test_html(html)
            # # return 'check die:socks die'
            # link_captcha = re.search('title="Captcha Image" src="(.+?)"',html).group(1).strip().replace('amp;','')
            # print link_captcha
            # captcha_tokenstring = re.search('\&tokenString=(.+?)\&',link_captcha).group(1).strip()
            # print captcha_tokenstring
            # captcha_save  = self.save_captcha(link_captcha,check=True)
            # print captcha_save
            # if self.decaptcha_key:
            #     i = 0
            #     while i < 4:
            #         try:
            #             captcha = captcha2upload.CaptchaUpload(self.decaptcha_key)
            #             captcha_input = captcha.solve(captcha_save)
            #         except Exception as e:
            #             print e
            #             time.sleep(1)
            #         else:
            #             break
            #         i += 1
            #     if i >= 4:
            #         print 'socks die'
            #         return 'order die:socks die:'
            #     os.remove(captcha_save)
            #
            #     checkform['tokenText'] = captcha_input
            #     checkform.new_control('text','htmid',{'value':''})
            #     checkform.new_control('text','kdata',{'value':''})
            #     checkform.new_control('text','tokenstring',{'value':captcha_tokenstring})
            #     checkform.fixup()
            #     checkform['userid'] = email
            #     checkform['pass'] = password
            #     request = checkform.click('sgnBt')
            #     r = self.browser.open(request, timeout=10)
            #     try:
            #         result = r.read()
            #     except:
            #         result = r.content
            #     self.write_test_html(result)
            #
            # else:
            #     self.update_captcha(captcha_save)
        else:
            print('your password incorect')
            return 'check die:your password incorect';

    def get_information(self, username):
        link_getfb_6month = 'https://feedback.ebay.com/ws/eBayISAPI.dll?ViewFeedback2&ftab=FeedbackAsSeller&userid='+username+'&iid=-1&de=off&items=25&interval=180'
        link_getfb_all = 'https://feedback.ebay.com/ws/eBayISAPI.dll?ViewFeedback2&userid='+username+'&ftab=FeedbackAsSeller&searchInterval=30'

        i = 0
        while i <= 4:
            try:
                self.browser.open(link_getfb_all)
                result = self.browser.read()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        c = open('test_login.html', 'w')
        c.write(result)
        c.close()
        try:
            receivedfb = re.search('class="FeedBackStatusLine">(.+?)</', result, re.DOTALL).group(1).strip().replace('<b>', '')
        except:
            receivedfb = ''
        try:
            revisedfb = re.search('font-size:12px;font-weight:bold;">(.+?)</', result, re.DOTALL).group(1).strip().replace(
                '<b>', '')
        except:
            revisedfb = ''
        try:
            countrye = re.sub(r'<.+?>','',re.search('Member since:(.+?)</span></div>', result, re.DOTALL).group(1).strip())
        except:
            countrye = ''
        try:
            positivefb12 = re.search('Positive Feedback \(last 12 months\):(.+?)</', result, re.DOTALL| re.IGNORECASE).group(1).strip().replace('<b>', '')
        except:
            positivefb12 = ''
        try:
            fbscore = re.search('<span class="mbg-l">\s*\((.+?)\s*<', result, re.DOTALL).group(1).strip().replace('<b>', '')
        except:
            fbscore = ''
        list_fbok =username + '|Positive feedback last 12 months:' + positivefb12 + '|Feedback score:' + fbscore + '|' + receivedfb + '|' + revisedfb + '|' + countrye
        print list_fbok
        return list_fbok

    def check(self, email='', password='', username='', sock='', sock_type=''):
        self.creat_browser()
        self.sock = sock
        if self.sock and sock_type == 'proxy':
            self.browser.set_proxies(proxy=self.sock)
        elif self.sock and sock_type == 'socks':
            # print self.sock
            self.browser.set_proxies(sock5=self.sock)
        login_html = self.site_login(email, password,sock=self.sock,sock_type=sock_type)
        if login_html.find('check die') == -1:
            if login_html.find('Reset pass') != -1:
                # ebay_infomation = 'Use clear socks for change password'
                ebay_infomation = self.change_password_old(email=email, password=password, sock=sock)
                return ebay_infomation
            else:
                ebay_infomation = self.get_information(login_html)
            if ebay_infomation:
                return email + '|' + password+'|'+ebay_infomation
            else:
                return  email + '|' + password
        else:
            print login_html
            return login_html

    def change_password(self,email, password, new_password='hanoi123',cookies_path='',sock=''):
        self.update_status('Trying Change password')

        self.browser = mybrowser.Rqbrowser(header=self.header)
        self.browser.link_host = "reg.ebay.com"
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        self.add_header('https://www.ebay.com/')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&UsingSSL=1&siteid=0&co_partnerId=2&pageType=2370920&pp=pass&i1=0&ru=https%3A%2F%2Freg.ebay.com%2Freg%2FChangePwd')
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        changeform =None
        for form in all_forms:
            print form
            if str(form).find('PasswordControl(opass') != -1:
                changeform = form
                break
        # self.write_test_html(html)
        if not changeform:
            print 'check die: cant find ChangePassForm'
            return 'check die: cant find ChangePassForm'
        changeform['opass'] = password
        changeform['npass'] = new_password
        changeform['rpass'] = new_password
        request = changeform.click()
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        self.write_test_html(html)
        error_re = re.search('aria-live="polite"><p>(.+?)</p',html)
        if error_re:
            return 'check die:'+error_re.group(1).strip()
        else:
            self.update_status('Your password has saved')
            self.update_status(email+'|'+new_password)
            return 'Your password has saved'

    def change_password_old(self,email, password,username='',sock='',new_pass='hanoi123'):
        self.browser = mybrowser.Rqbrowser()
        self.browser.link_host = 'www.ebay.com'
        self.browser.link_origin = 'https://www.ebay.com'
        if socks:
            self.browser.set_proxies(sock5=sock)
        self.add_header('https://www.ebay.com/')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('https://signin.ebay.com/ws/eBayISAPI.dll?SignIn&ru=http%3A%2F%2Fwww.ebay.com%2F')
                # html = r.read()
                loginforms = self.browser.selectForm(r)
                loginform = None
                for form in loginforms:
                    # print form
                    if str(form).find('PasswordControl(pass') != -1:
                        loginform=form
                        break
                if loginform:
                    # print loginform
                    loginform['userid'] = email
                    loginform['pass'] = password
                    request = loginform.click('sgnBt')
                    r = self.browser.open(request)
                    if r.url != r.headers['location'] and r.headers['location']:
                        if r.headers['location'].find('http') == -1:
                            link_location = r.url.split('://')[0] + '://' + r.url.split('://')[1].split('/')[0]
                            link_open = link_location + r.headers['location']
                        else:
                            link_open = r.headers['location']
                        print link_open
                        r = self.browser.open(link_open)
                    html = r.content
                else:
                    i+=1
                    time.sleep(1)
                    continue
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        if html.find('New password') != -1:
            loginforms = self.browser.selectForm(r)
            loginform = None
            for form in loginforms:
                # print form
                if str(form).find('PasswordControl(pass') != -1:
                    loginform=form
                    break
            if loginform:
                i = 0
                while i <= 4:
                    try:
                        loginform['pass'] = new_pass
                        loginform['rpass'] = new_pass
                        request = loginform.click('submitBtn')
                        r = self.browser.open(request)
                    except:
                        time.sleep(1)
                    else:
                        break
                    i += 1
                if i >= 4:
                    print 'check die:socks die'
                    return 'check die:socks die'
            else:
                return 'check die:socks die'
            # print r.headers
            ebay_info = self.check(email,new_pass,sock=sock,sock_type='socks')
            if ebay_info.find('socks die:') != -1:
                ebay_info = email+'|'+new_pass+'|cant get ebay infomation'
            return ebay_info
        elif html.find('Your email/user ID or password is incorrect') != -1:
            print 'pass sai'
            return 'check die:password is incorrect'
        else:
            print 'socks dien'
            return 'check die:socks die'
        # self.write_test_html(html)

    def add_automatic_payment(self,email,password,ccpayment_information='',cookies_path=None,sock=''):
        self.browser = mybrowser.Rqbrowser(header=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        self.update_status('Trying to setup CC payment')
        if ccpayment_information.find('|') == -1:
            return 'check die:Check you CC information length'

        list_cc = ccpayment_information.split('|')
        if len(list_cc) < 3:
            return 'check die:Check you CC information lenght'
        cc_number = list_cc[0].strip()
        cc_month = list_cc[1].strip()
        if cc_month[:1] == '0':
            cc_month = cc_month[1:]
        cc_years = list_cc[2].strip()
        if len(cc_years) == 2:
            cc_years = '20'+cc_month
        cvv2 = list_cc[3].strip()
        self.update_status('Trying Add CC:'+ccpayment_information)
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('https://arbd.ebay.com/ws/eBayISAPI.dll?SetupCCPayment')
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html,link_reopen='https://arbd.ebay.com/ws/eBayISAPI.dll?SetupCCPayment')
        if str(html).find('check die') != -1:
            return html
        changeform =None
        for form in all_forms:
            print form
            if str(form).find('TextControl(cardnumber=') != -1:
                changeform = form
                break
        if not changeform:
            print 'check die:cant find payment form1'
            return 'check die:cant find payment form1'
        changeform['cardnumber'] = cc_number
        changeform['ccexpirationmonth'] = [cc_month]
        changeform['ccexpirationyear'] = [cc_years]
        changeform['cvv2num'] = cvv2
        request = changeform.click('submit')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # self.write_test_html(html)
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        changeform =None
        for form in all_forms:
            print form
            if str(form).find('SubmitControl(submit=Authorize Credit Card') != -1:
                changeform = form
                break
        if not changeform:
            self.write_test_html(html)
            print 'check die:cant find payment form'
            return 'check die:cant find payment form'
        request = changeform.click('submit')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        if html.find('Your changes have been saved') != -1:
            self.update_status('Your changes have been saved')
        else:
            self.update_status('Please check your CC information')
        self.write_test_html(html)

    def change_email(self,email,password,new_email='',cookies_path='',sock=''):

        self.update_status('Trying change your email and phone')
        print '===',self.header
        self.browser = mybrowser.Rqbrowser(agent=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        print 'Trying Change ebay Email'

        self.update_status('Trying Get Change ebay Email')
        link_change_url = 'https://scgi.ebay.com/ws/eBayISAPI.dll?ChangeEmail'
        self.add_header('https://scgi.ebay.com/ws/eBayISAPI.dll?ChangeEmail')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('https://scgi.ebay.com/ws/eBayISAPI.dll?ChangeEmail')
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        self.write_test_html(html)
        changeform =None
        for form in all_forms:
            # print form
            if str(form).find('TextControl(newemail=') != -1:
                changeform = form
                break
        if not changeform:
            print 'check die:cant find changephone form'
            return 'check die:cant find changephone form'

        link_captcha_iframe = re.search('<iframe src="(.+?)"',html).group(1).strip().replace('amp;','')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_captcha_iframe)
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        link_captcha = re.search('<img src="(.+?)"',html).group(1).strip().replace('amp;','')
        self.update_status('Type your captcha')
        # print link_captcha
        link_captcha_show = self.save_captcha(link_captcha)

        if link_captcha_show.find('check die') == -1:
            # self.update_captcha(link_captcha_show)
            send_captcha = self.update_captcha(link_captcha_show)
            if send_captcha:
                captcha_result = self.captcha_queue.get()
            else:
                captcha_result = raw_input('input captcha')
            print 'Captcha:'+str(captcha_result)
            captcha_tokenstring = re.search('\&tokenString=(.+?)\&',link_captcha).group(1).strip()
            print captcha_tokenstring
            changeform.set_all_readonly(False)
            changeform['newemail']=new_email
            changeform['retypeemail']=new_email
            # self.write_test_html(html)
            changeform['tokentext'] = captcha_result
            changeform['tokenstring'] = captcha_tokenstring
            request = changeform.click()
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request)
                    html = r.content
                    linkget=r.url
                    self.add_header(linkget)
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            self.write_test_html(html)
            if html.find('We have sent an email to your address') != -1:
                self.save_cookies(cookies_path,email)
                self.update_status('We have sent an email to your address')
                return 'We have sent an email to your address'
            else:
                return 'check die: cant change your email'
            # html = self.get_loginform_and_login(html_login,linkget,email,password,captcha_result=captcha_result,captcha_tokenstring=captcha_tokenstring,link_reopen=link_reopen)

    def change_secret_question(self,email,password,cookies_path='',sock=''):
        self.update_status('Trying Change Secret Question')

        self.browser = mybrowser.Rqbrowser(header=self.header)
        self.browser.link_host = "reg.ebay.com"
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        self.add_header('https://reg.ebay.com/reg/ChangeSecretQuestion?flow=MY_EBAY&ru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyeBay%26tokenid%3D4%26CurrentPage%3DMyeBayPersonalInfo%26ssPageName%3DsuccessSecretQuestion')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('https://reg.ebay.com/reg/ChangeSecretQuestion?flow=MY_EBAY&ru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyeBay%26tokenid%3D4%26CurrentPage%3DMyeBayPersonalInfo%26ssPageName%3DsuccessSecretQuestion')
                html = r.content
                linkget=r.url
                self.add_header(linkget)

            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        changeform =None
        for form in all_forms:
            print form
            if str(form).find('HiddenControl(secretQuestion1') != -1:
                changeform = form
                break
        if not changeform:
            print 'check die: cant find secretQuestion1 form'
            return 'check die: cant find secretQuestion1 form'
        changeform.set_all_readonly(False)
        question_1re = re.search('SECRET_QUESTION_1_3" op-value="(.+?)".+?">(.+?)</li>',html)
        if question_1re:
            question_one_id =  question_1re.group(1).strip()
            question_one = question_1re.group(2).strip()
        else:
            question_one_id = '100000003'
            question_one = 'Name of your first pet?'
        changeform['secretQuestion1'] = question_one_id
        changeform['dp_SECRET_QUESTION_1'] = question_one
        changeform['secretAnswer1'] = 'bull'
        ####

        question_2re = re.search('SECRET_QUESTION_1_6" op-value="(.+?)".+?">(.+?)</li>',html)
        if question_1re:
            question_2_id =  question_2re.group(1).strip()
            question_2 = question_2re.group(2).strip()
        else:
            question_2_id = '100000006'
            question_2 = 'Your childhood nickname?'
        changeform['secretQuestion2'] = question_2_id
        changeform['dp_SECRET_QUESTION_2'] = question_2
        changeform['secretAnswer2'] = 'mun'

        question_3re = re.search('SECRET_QUESTION_1_8" op-value="(.+?)".+?">(.+?)</li>',html)
        if question_1re:
            question_3_id =  question_3re.group(1).strip()
            question_3 = question_3re.group(2).strip()
        else:
            question_3_id = '100000008'
            question_3 = 'Name of the street you grew up on?'
        changeform['secretQuestion3'] = question_3_id
        changeform['dp_SECRET_QUESTION_3'] = question_3
        changeform['secretAnswer3'] = 'ngoctruc'
        request = changeform.click()
        print changeform
        # request_url = 'https://reg.ebay.com/reg/ChangeSecretQuestion'
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.content
                linkget=r.url
                self.add_header(linkget)

            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        self.write_test_html(html)
        if html.find('Your changes have been saved') != -1:
            self.update_status(question_one+':bull')
            self.update_status('Your childhood nickname?:mun')
            self.update_status('Name of the street you grew up on?:ngoctruc')
            self.save_cookies(cookies_path,email)
            return 'Your secret question has saved'
        else:
            return 'check die: Cant change your account information'

    def change_email_phone(self,email,password,new_email='',new_phone='',cookies_path='',sock=''):
        self.update_status('Trying change your email and phone')
        self.browser = mybrowser.Rqbrowser(agent=self.header)
        self.browser.link_host = "reg.ebay.com"
        # self.browser.link_origin='https://reg.ebay.com'
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        # print 'Trying Get Change ebay infomation'
        self.update_status('Trying Get Change ebay infomation')
        self.add_header('https://scgi.ebay.com/ws/eBayISAPI.dll?ChangeRegistrationShow&guest=1')

        r = self.browser.open('https://reg.ebay.com/reg/UpdateContactInfo?flow=MY_EBAY&idType=1&ru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyeBay%26tokenid%3D87%26CurrentPage%3DMyeBayPersonalInfo%26ssPageName%3DsuccessChangePhone')
        html = r.content
        linkget=r.url
        self.add_header(linkget)


        all_forms,html = self.re_loginebay(html,linkget,email,password,cookies_path=cookies_path,return_html=html,link_reopen='https://reg.ebay.com/reg/UpdateContactInfo?flow=MY_EBAY&idType=1&ru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyeBay%26tokenid%3D87%26CurrentPage%3DMyeBayPersonalInfo%26ssPageName%3DsuccessChangePhone')
        if str(html).find('check die') != -1:
            return html

        changeform =None
        for form in all_forms:
            # print form
            if str(form).find('TextControl(phoneFlagComp1') != -1:
                changeform = form
                break
        if not changeform:
            print changeform
            print 'check die:cant find changephone form'
            return 'check die:cant find changephone form'

        changeform.set_all_readonly(False)
        changeform['isMobilePhone'] = 'true'
        changeform['flow'] = 'VERF_EDIT'
        changeform['hiddenDialCodephoneFlagComp1'] = '+1'
        changeform['hiddenCountryCodephoneFlagComp1'] = 'us'
        changeform['hiddenNumberTypephoneFlagComp1'] = '2'
        new_phone_old = changeform['hiddenPlainphoneFlagComp1']
        if new_phone:
            self.update_status('Your new phone:'+new_phone)
            changeform['phoneFlagComp1'] = new_phone.replace('-','')
            changeform['hiddenPlainphoneFlagComp1'] = new_phone.replace('-','')
            changeform['hiddenphoneFlagComp1'] = '+1'+new_phone.replace('-','')
        else:
            min = 2000000000
            max = 9999999999

            new_phone_random = str(random.randint(min, max))
            changeform['phoneFlagComp1'] = '('+new_phone_random.replace('-','')[:3]+') '+new_phone_random.replace('-','')[3:6]+'-'+new_phone_random.replace('-','')[6:]
            changeform['hiddenPlainphoneFlagComp1'] = new_phone_random.replace('-','')
            changeform['hiddenphoneFlagComp1'] = '+1'+new_phone_random.replace('-','')
        url_change_email = 'https://reg.ebay.com/reg/UpdateContactInfo?flow=VERF_EDIT&ru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyeBay%26tokenid%3D87%26CurrentPage%3DMyeBayPersonalInfo%26ssPageName%3DsuccessChangePhone%26verfType%3D1&srt='+changeform['srt']
        self.update_status('Trying Update Contact Info')
        self.add_header(linkget)
        print changeform
        request = changeform.click()

        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request,timeout=10)
                html = r.content
                linkget=r.url

            except Exception as e:
                print e
                if str(e).find('The HTTP server returned a redirect') != -1:
                    break
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        if new_email:

            allforms = self.browser.selectForm(html,linkget)
            changeform =None
            for form in allforms:
                print form
                if str(form).find('phoneFlagComp1=') != -1:
                    changeform = form
                    break
            if not changeform:
                print 'check die:cant find phoneFlagComp1 form'
                return 'check die:cant find phoneFlagComp1 form'
            self.update_status('Trying change new email and phone:' + new_email + '|' + new_phone)
            changeform.set_all_readonly(False)
            changeform['email'] = new_email
            changeform['hiddenDialCodephoneFlagComp1'] = '+1'
            changeform['hiddenCountryCodephoneFlagComp1'] = 'us'
            changeform['hiddenNumberTypephoneFlagComp1'] = '2'
            changeform['flow'] = 'VERF_EDIT'
            if new_phone:
                self.update_status('Your new phone:'+new_phone)
                changeform['phoneFlagComp1'] = new_phone.replace('-','')
                changeform['hiddenPlainphoneFlagComp1'] = new_phone.replace('-','')
                changeform['hiddenphoneFlagComp1'] = '+1'+new_phone.replace('-','')
            else:
                changeform['phoneFlagComp1'] = new_phone_old.replace('-','')
                changeform['hiddenPlainphoneFlagComp1'] = new_phone_old.replace('-','')
                changeform['hiddenphoneFlagComp1'] = '+1'+new_phone_old.replace('-','')
            request = changeform.click()

            i = 0
            while i <= 4:
                try:
                    self.add_header(linkget,extraHeader={'Content-Type':'application/x-www-form-urlencoded'})
                    r = self.browser.open(request,timeout=10)
                    html = r.content
                    linkget=r.url
                    self.add_header(linkget)
                except Exception as e:
                    if str(e).find('The HTTP server returned a redirect') != -1:
                        print e
                        break
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            self.write_test_html(html)
        if new_phone:
            self.update_status('Trying confirm your phonenumber:'+new_phone)
            reinput_re = re.search('reqinput" value="(.+?)"',html)
            if not reinput_re:
                self.write_test_html(html)
                self.save_cookies(cookies_path,email)
                print 'check die:cant find reqinput form'
                return 'check die:cant find reqinput form'
            reinput_value = reinput_re.group(1).strip()
            request_data = {}
            request_data['reqinput'] = reinput_value
            request_data['contactBy'] = 'text'
            request_url = 'https://www.buyvrfn.ebay.com/UCIPhoneInfo'
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request_url,request_data,timeout=10)
                    html = r.content
                    linkget=r.url
                    self.add_header(linkget)
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            self.update_status('Trying confirm your phonenumber:'+new_phone)
            reinput_re = re.search('reqinput" value="(.+?)"',html)
            if not reinput_re:
                self.write_test_html(html)
                print 'check die:cant find reqinput confirmphone form'
                return 'check die:cant find reqinput confirmphone form'
            try:
                self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "type_code",'type_code')
            except:
                question_result = raw_input('input captcha')
                # os.remove(captcha_save)
            else:
                question_result = self.captcha_queue.get()
            print 'Phone Pin:'+str(question_result)
            # changeform['phonePin'] = question_result
            reinput_value = reinput_re.group(1).strip()
            request_data = {}
            request_data['reqinput'] = reinput_value
            request_data['pin'] = question_result
            request_url = 'https://www.buyvrfn.ebay.com/UCIVerifyPin/'
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request_url,request_data)
                    html = r.content
                    linkget=r.url
                    self.add_header(linkget)
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            self.write_test_html(html)
        self.update_status('Your new email and phone:'+new_email+'|'+new_phone)
        self.update_status('Changed email phone ^_^ Please confirm your account')
        self.save_cookies(cookies_path,email)
        return new_email

    def create_paypal(self,email,password,email_paypal='',get_info=False,cookies_path='',sock=''):
        if not get_info:
            self.browser = mybrowser.Rqbrowser(header=self.header)
            if sock:
                self.browser.set_proxies(sock5=sock)
            if os.path.isfile(cookies_path):
                print 'load cookies'
                try:
                    self.browser.load_cookies(cookies_path)
                except:
                    pass
        if not get_info:
            self.update_status('Trying create your paypal')
        else:
            self.update_status('Trying Get Ebay infomation')
        self.add_header('http://my.ebay.com/ws/eBayISAPI.dll?MyeBay&CurrentPage=MyeBayPersonalInfo&gbh=1&ssPageName=STRK:ME:LNLK')
        link_create_paypal = 'http://shiptrack.ebay.com/ws/eBayISAPI.dll?PayPalRegistrationRedirect&ru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyEbay%26CurrentPage%3DMyeBayMyAccounts&sru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyEbay%26CurrentPage%3DMyeBayMyAccounts&eru=http%3A%2F%2Fmy.ebay.com%2Fws%2FeBayISAPI.dll%3FMyEbay%26CurrentPage%3DMyeBayMyAccounts&flowtype=4&backToEbayRu=https%3A%2F%2Fpayments.ebay.com%2Fws%2FeBayISAPI.dll%3FTrinityDualAuthLink&link=0'
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_create_paypal)
                html = r.content
                linkget=r.url
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        self.update_status('Trying go to paypal page')
        all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen=link_create_paypal,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        paypalform = None
        for form in all_forms:
            if str(form).find('dont_have_account') != -1:
                paypalform = form
                break
        if paypalform:

            print paypalform
            request = paypalform.click('dont_have_account')
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request)
                    html = r.content
                    linkget=r.url
                    self.add_header(linkget)
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            all_forms = self.browser.selectForm(html,linkget)
        # all_forms = self.re_loginebay(allforms,email,password,link_reopen=linkget)
        paypalform = None
        for form in all_forms:
            if str(form).find('SubmitControl(signup') != -1:
                paypalform = form
                break
        if not paypalform:
            print 'check die:cant find paypal form'
            return 'check die:cant find paypal form'
        if not get_info:
            print paypalform
            paypalform['password'] = 'Hanoi123!@#'
            paypalform['retype_password'] = 'Hanoi123!@#'
            paypalform['email'] = email_paypal
            self.write_test_html(html)
            try:
                link_captcha = re.search('gl-test-image"><img border="1" src="(.+?)"',html).group(1).strip().replace('amp;','')
                self.update_status('Type your captcha')
                link_captcha_show = self.save_captcha(link_captcha)
                if link_captcha_show.find('check die') == -1:
                    self.update_captcha(link_captcha_show)
                    captcha_result = self.captcha_queue.get()
                    paypalform['string_answer'] = captcha_result
            except:
                pass
            try:
                self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "type_dob",'type_dob')
            except:
                pass
            else:
                question_result = self.captcha_queue.get()
            if question_result.find('/') == -1:
                print 'check die:Dob format error'
                return 'check die:Dob format error'
            paypalform['dob_a'] = question_result.split('/')[0].strip()
            paypalform['dob_b'] = question_result.split('/')[1].strip()
            paypalform['dob_c'] = question_result.split('/')[2].strip()
            # paypalform['terms'] = ['agree']
            request = paypalform.click('signup')
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request)
                    html = r.content
                    linkget=r.url
                    self.add_header(linkget)
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'

            # self.update_status('Create paypal done')
        else:
            first_name = paypalform['first_name']
            last_name = paypalform['last_name']
            address1 = paypalform['address1']
            address2 = paypalform['address2']
            city = paypalform['city']
            state = paypalform['state'][0]
            # print state
            zip = paypalform['zip']
            H_PhoneNumber = paypalform['H_PhoneNumber']
            ebay_infomation = first_name+'|'+last_name+'|'+address1+'|'+address2+'|'+city+'|'+state+'|'+zip+'|'+H_PhoneNumber
            print ebay_infomation
            self.update_status(ebay_infomation)
            return ebay_infomation
        self.save_cookies(cookies_path,email)
        self.write_test_html(html)
        if html.find('create your account with PayPal') != -1:
            error_re = re.search('Error Message</h2><p></p><ul><li>(.+?)</li>',html)
            if error_re:
                print 'check die:'+error_re.group(1).strip()
                return 'check die:'+error_re.group(1).strip()
            else:
                print 'check die:Create paypal error'
                return 'check die:Create paypal error'
        else:
            self.update_status('Create Paypal Success:'+email_paypal+'|Hanoi123!@#')
            return email_paypal+'|Hanoi123!@#|'

    def get_order_infomation(self,email,password,sock='',cookies_path=''):
        self.browser = mybrowser.Mechanizebrowser(header=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        self.browser.link_host='my.ebay.com'
        self.browser.link_origin='http://my.ebay.com'
        link_myaccount='http://my.ebay.com/ws/eBayISAPI.dll?MyEbayBeta&CurrentPage=MyeBayNextAllSelling&SubmitAction.ItemsPerPageSave=x&CustomizedContainer=241&ItemsPerPage=200&View=MYEBAY_NEXT_CONTAINER_CUSTOMIZE&NewPeriod=Last31Days&ssPageName=STRK:MESOX:COUNT:200&View=SoldNext#GoTo241'
        self.add_header('http://my.ebay.com/ws/eBayISAPI.dll?MyEbayBeta&CurrentPage=MyeBayNextAllSelling&SubmitAction.ItemsPerPageSave=x&CustomizedContainer=241&ItemsPerPage=200&View=MYEBAY_NEXT_CONTAINER_CUSTOMIZE&NewPeriod=Last31Days&ssPageName=STRK:MESOX:COUNT:200&View=SoldNext#GoTo241')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_myaccount)
                html_myorder = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html_myorder,linkget)
        all_forms,html_myorder = self.re_loginebay(html_myorder,linkget,email,password,link_reopen=link_myaccount,cookies_path=cookies_path,return_html=html_myorder)
        if str(html_myorder).find('check die') != -1:
            return html_myorder
        if html_myorder.find('Confirm your account') != -1:
            self.write_test_html(html_myorder)
            print 'check die:Confirm your account'
            return 'check die:Confirm your account'
        c = open('order_information.html','w')
        c.write(html_myorder)
        list_order=''
        list_order_item = re.findall('_ps_div"><b id="(\d+_\d+)_ps" class="i-pc" title="Paid on (.+?) to PayPal \((.+?)\)',html_myorder)
        for line_order in list_order_item:
            item_transId,date_paid,paypal_receive = line_order
            refund = False
            if item_transId.find('_ps" class="i-prf" title="') != -1:
                if item_transId.find('Your payment has been refunded') != -1:
                    refund = True
                item_transId = re.search('(.+?)_ps" class="i-prf" title="',item_transId).group(1).strip()
            itemid = item_transId.split('_')[0]
            transId = item_transId.split('_')[1]
            if html_myorder.find(itemid+'_'+transId+'_ss" class="i-sl" title="Not shipped"') != -1 and not refund:
                link_order='http://payments.ebay.com/ws/eBayISAPI.dll?ViewPaymentStatus&transId='+transId+'&ssPageName=STRK:MESOX:VPS&itemid='+itemid
                i = 0
                while i <= 4:
                    try:
                        r = self.browser.open(link_order)
                        html = r.read()
                        linkget=r.geturl()
                        self.add_header(linkget)
                    except:
                        time.sleep(1)
                    else:
                        break
                    i += 1
                if i >= 4:
                    print 'check die:socks die'
                    return 'check die:socks die'
                #161924913622_1347422867006_ps
                if html.find('shippingState":"NOT_SHIPPED') != -1:

                    # allforms = self.browser.selectForm(html,linkget)
                    all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen=link_order,cookies_path=cookies_path,return_html=html)
                    if str(html).find('check die') != -1:
                        return html
                    html = html.replace(':null',':None')
                    shipping_addres_re = re.search('"shippingAddress":(.+?)\}',html)
                    if not shipping_addres_re:
                        print 'check die:cant find shipping addresss'

                        return 'check die:cant find shipping addresss'
                    title_re = re.search('title":"(.+?)"',html)
                    if not title_re:
                        print 'check die:cant find order item'
                        return 'check die:cant find order item'
                    buyer_name_re = re.search('buyer":\{"name":"(.+?)"',html)
                    if not buyer_name_re:
                        print 'check die:cant find Buyerid'
                        return 'check die:cant find Buyerid'
                    order_shipping_adress = eval(shipping_addres_re.group(1).strip()+'}')
                    title_item = title_re.group(1).strip()
                    buyer_name = buyer_name_re.group(1).strip()
                    order_name= order_shipping_adress['name']
                    if order_name.find(' ') != -1:
                        order_fisrtname = order_name.split(' ')[0].strip()
                        order_lastname = order_name.replace(order_fisrtname,'').strip()
                    else:
                        order_fisrtname = buyer_name
                        order_lastname = order_name
                    order_address1= order_shipping_adress['addressLine1']
                    order_address2= order_shipping_adress['addressLine2']
                    if not order_address2:
                       order_address2 = ''
                    order_city= order_shipping_adress['city']
                    order_state= order_shipping_adress['stateOrProvince']
                    order_zipcode= order_shipping_adress['zip']
                    order_info = order_fisrtname+'|'+order_lastname+'|'+order_address1+'|'+str(order_address2)+'|'+order_city+'|'+order_state+'|'+order_zipcode+'#--#'+item_transId+'#--#'+buyer_name+'#--#'+title_item+'#--#'+date_paid+'#--#'+paypal_receive
                    self.update_status(order_info+'\n========')
                    list_order=list_order+order_info+'#==#'
        self.save_cookies(cookies_path,email)
        if list_order:
            print list_order
            return list_order
        else:
            return 'check die:Have not order'

    def end_list_item(self,item_name='',item_id=''):
        print('update')

    def add_tracking(self,email,password,sock='',cookies_path='',tracking='',orderid='',list_add_tracking=[]):
        print('add tracking')
        if list_add_tracking:
            tracking_lineid = ''
            for line_track in list_add_tracking:
                tracking_lineid=tracking_lineid+'LineID=Transactions.'+line_track['order_id'].replace('_ps','')+'&'
            link_addtracking='http://payments.ebay.com/ws/eBayISAPI.dll?AddTrackingNumber2&'+str(tracking_lineid)+'flow=&from=1&cm=&pg=&islpvcode=&ru=&claimid='
        else:
            link_addtracking='http://payments.ebay.com/ws/eBayISAPI.dll?AddTrackingNumber2&LineID=Transactions.'+orderid.replace('_ps','')+'&flow=&from=1&cm=&pg=&islpvcode=&ru=&claimid='
        self.browser = mybrowser.Mechanizebrowser(header=self.header)
        if sock:
            self.browser.set_proxies(sock5=sock)
        if os.path.isfile(cookies_path):
            print 'load cookies'
            try:
                self.browser.load_cookies(cookies_path)
            except:
                pass
        self.browser.link_host='payments.ebay.com'
        self.browser.link_origin='http://payments.ebay.com'
        self.add_header('http://my.ebay.com/ws/eBayISAPI.dll?MyEbay&gbh=1&CurrentPage=MyeBayAllSelling&ssPageName=STRK:ME:LNLK:MESX')
        i = 0
        while i <= 4:
            try:
                print link_addtracking
                r = self.browser.open(link_addtracking)
                html = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # allforms = self.browser.selectForm(html,linkget)
        all_forms,html = self.re_loginebay(html,linkget,email,password,link_reopen=link_addtracking,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html
        self.write_test_html(html)
        addtrackform = None
        for form in all_forms:
            # print form
            if str(form).find('TextControl(trackingNumber') != -1:
                addtrackform = form
                # break
        if not addtrackform:
            print 'check die:cant find paypal form'
            return 'check die:cant find paypal form'
        print addtrackform
        if list_add_tracking:
            for line_tracking in list_add_tracking:
                tracking = str(line_tracking['tracking'])
                order_id = str(line_tracking['order_id'])
                addtrackform['trackingNumber.'+order_id.replace('_ps','')+'_1'] = tracking
                if tracking[:2].find('1Z') != -1:
                    carrierName = 'UPS'
                elif tracking.isdigit():
                    carrierName = 'Fedex'
                elif tracking.find('C') != -1:
                    carrierName = 'Ontrac'
                else:
                    carrierName = 'Another'
                addtrackform['carrierName.'+order_id.replace('_ps','')+'_1'] = carrierName
        else:
            addtrackform['trackingNumber.'+orderid.replace('_ps','')+'_1'] = tracking
            if tracking[:2].find('1Z') != -1:
                carrierName = 'UPS'
            elif tracking.isdigit():
                carrierName = 'Fedex'
            else:
                carrierName = 'Another'
            addtrackform['carrierName.'+orderid.replace('_ps','')+'_1'] = carrierName
        request = addtrackform.click()
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        self.write_test_html(html)
        self.save_cookies(cookies_path,email)
        if html.find('addTrackingForm') == -1:
            return 'successfully added'
        else:
            return 'check die:Cant add your tracking'

    def create_account(self,email,password,phone,ebay_information, sock='',cookies_path=None):

        link_register = 'https://reg.ebay.com/reg/PartialReg'
        self.browser = mybrowser.Mechanizebrowser(header=self.header)
        self.browser.link_host = 'reg.ebay.com'
        if sock:
            self.browser.set_proxies(sock5=sock)
        print 'Trying create your ebay account'
        self.update_status('Trying create your ebay account')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(link_register)
                html = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        register_form = None
        all_forms = self.browser.selectForm(html,linkget)
        for form in all_forms:
            if str(form).find('TextControl(businessname') != -1:
                register_form = form
                break
        if not register_form:
            self.write_test_html(html)
            print 'check die:cant find register_form'
            return 'check die:cant find register_form'
        #liz|campanile|334 n chestnut st||westfield|NJ|07090
        hangbill = ebay_information.split('|')
        self.bfirstname = hangbill[0].strip()
        self.blastname = hangbill[1].strip()
        self.baddress1 = hangbill[2].strip()
        self.baddress2 = hangbill[3].strip()
        self.bcity = hangbill[4].strip()
        self.bstate = hangbill[5].strip()
        self.bzipcode = hangbill[6].strip()

        register_form.set_all_readonly(False)
        register_form['businessname'] = self.bfirstname +' '+self.blastname
        register_form['businessemail'] = email
        register_form['rbusinessemail'] = email
        register_form['PASSWORD_BIZREG'] = password
        register_form['phoneFlagComp1Business'] = phone
        register_form['hiddenphoneFlagComp1Business'] = '+1'+phone
        register_form['hiddenDialCodephoneFlagComp1Business'] = '+1'
        register_form['hiddenNumberTypephoneFlagComp1Business'] = '2'
        register_form['hiddenPlainphoneFlagComp1Business'] = phone
        register_form['bizFlag'] = 'true'
        request = register_form.click()
        print register_form
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        error_re = re.search('id="ertx" tabindex="0">(.+?)<',html)
        if error_re:
            print error_re.group(1).strip()
            return 'check die:'+error_re.group(1).strip()
        upgrade_business = self.upgrade_business_account(email,password,phone,cookies_path=cookies_path)
        return upgrade_business

    def upgrade_business_account(self,email,password,phone,ebay_information='',sock='',cookies_path=None):
        if ebay_information:
            hangbill = ebay_information.split('|')
            self.bfirstname = hangbill[0].strip()
            self.blastname = hangbill[1].strip()
            self.baddress1 = hangbill[2].strip()
            self.baddress2 = hangbill[3].strip()
            self.bcity = hangbill[4].strip()
            self.bstate = hangbill[5].strip()
            self.bzipcode = hangbill[6].strip()
        if sock:
            self.browser = mybrowser.Mechanizebrowser(header=self.header)
            self.browser.link_host = 'reg.ebay.com'
            self.browser.set_proxies(sock5=sock)
            if os.path.isfile(cookies_path):
                print 'load cookies'
                try:
                    self.browser.load_cookies(cookies_path)
                except:
                    pass
        print 'Trying Upgrade Business Your Account'
        self.update_status('Trying Upgrade Business Your Account')
        i = 0
        while i <= 4:
            try:
                r = self.browser.open('https://reg.ebay.com/reg/Upgrade')
                html = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        all_forms,html = self.re_loginebay(html,'https://reg.ebay.com/reg/Upgrade',email,password,cookies_path=cookies_path,return_html=html)
        if str(html).find('check die') != -1:
            return html

        register_form = None
        # all_forms = self.browser.selectForm(html,linkget)
        for form in all_forms:
            # print form
            if str(form).find('TextControl(address1') != -1:
                register_form = form
                break
        if not register_form:
            self.write_test_html(html)
            # info_account = self.get_ebay_selling_infomation(email,password,cookies_path)
            # cookiespath = self.save_cookies(cookies_path,email)
            # self.update_status('Login and get cookies done ^.^')
            print 'check die:cant find register_form address'
            return 'check die:cant find register_form address'
        print register_form
        register_form.set_all_readonly(False)
        try:
            register_form['firstname'] = self.bfirstname
            register_form['lastname'] = self.blastname
        except:
            register_form.new_control('hidden', 'firstname',   {'value': self.bfirstname})
            register_form.new_control('hidden', 'lastname',   {'value': self.blastname})
        register_form['address1'] = self.baddress1
        register_form['address2'] = self.baddress2
        register_form.find_control('city',nr=0).value = self.bcity
        register_form.find_control('city',nr=1).value = self.bcity
        register_form.find_control('state',nr=0).value = [self.bstate]
        register_form.find_control('state',nr=1).value = self.bstate

        register_form['zip'] = self.bzipcode
        register_form['phoneFlagComp1'] = phone
        try:
            register_form['contactType'] = ['1']
            register_form['contactPhone'] = phone
        except:
            register_form.new_control('hidden', 'contactType',   {'value': '1'})
            register_form.new_control('hidden', 'contactPhone',   {'value': phone})
        register_form['hiddenDialCodephoneFlagComp1'] = '+1'
        register_form['hiddenCountryCodephoneFlagComp1'] = 'us'
        try:
            register_form['hiddenCountryCodecontactPhone'] = 'us'
        except:
            register_form.new_control('hidden', 'hiddenCountryCodecontactPhone',   {'value': 'us'})
        try:
            register_form['hiddenNumberTypecontactPhone'] = '2'
            register_form['hiddenNumberTypephoneFlagComp1'] = '2'
            register_form['hiddenPlaincontactPhone'] = phone
            register_form['hiddenPlainphoneFlagComp1'] = phone
            register_form['hiddencontactPhone'] = '+1'+phone
        except:
            register_form.new_control('hidden', 'hiddenNumberTypecontactPhone',   {'value': '2'})
            register_form.new_control('hidden', 'hiddenNumberTypephoneFlagComp1',   {'value': '2'})
            register_form.new_control('hidden', 'hiddenPlaincontactPhone',   {'value': phone})
            register_form.new_control('hidden', 'hiddenPlainphoneFlagComp1',   {'value': phone})
            register_form.new_control('hidden', 'hiddencontactPhone',   {'value':  '+1'+phone})

        register_form['hiddenphoneFlagComp1'] = '+1'+phone

        request = register_form.click()
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'

        register_form = None
        all_forms = self.browser.selectForm(html,linkget)
        for form in all_forms:
            print form
            if str(form).find('HiddenControl(contactBy') != -1:
                register_form = form
                break
        if not register_form:
            # info_account = self.get_ebay_selling_infomation(email,password,cookies_path)
            # cookiespath = self.save_cookies(cookies_path,email)
            # self.update_status('Login and get cookies done ^.^')
            self.write_test_html(html)
            print 'check die:cant find register_form PhoneInfo'
            return 'check die:cant find register_form PhoneInfo'
        print 'Trying Upgrade Confirm Your Phone Number'
        self.update_status('Trying Upgrade Confirm Your Phone Number')

        register_form.set_all_readonly(False)
        register_form['contactBy'] = 'Text'
        register_form['hiddenDialCodeedit'] = '+1'
        register_form.new_control('hidden', 'phoneCountry',   {'value': 'us'})
        register_form.new_control('hidden', 'mobile',   {'value': 'on'})

        register_form.fixup()
        request = register_form.click('text')
        # print register_form
        i = 0
        while i <= 4:
            try:
                r = self.browser.open(request)
                html = r.read()
                linkget=r.geturl()
                self.add_header(linkget)
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print 'check die:socks die'
            return 'check die:socks die'
        # self.write_test_html(html)
        register_form = None
        all_forms = self.browser.selectForm(html,linkget)
        for form in all_forms:
            # print form
            if str(form).find('TextControl(phonePin') != -1:
                register_form = form
                break
        if not register_form:
            info_account = self.get_ebay_selling_infomation(email,password,cookies_path)
            cookiespath = self.save_cookies(cookies_path,email)
            self.update_status('Login and get cookies done ^.^')
            print 'check die:cant find register_form phonePin'
            return 'check die:cant find register_form phonePin'
        try:
            self.emit( self.qtcode.SIGNAL(self.updatestatus+'(QString,QString)'), "type_code",'type_code')
        except:
            pass
        else:
            question_result = self.captcha_queue.get()
            print 'Phone Pin:'+str(question_result)
            register_form['phonePin'] = question_result
            request = register_form.click('Continue')
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request)
                    html = r.read()
                    linkget=r.geturl()
                    self.add_header(linkget)
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'
            self.update_status('Trying select your bizType')
            self.write_test_html(html)
            register_form = None
            all_forms = self.browser.selectForm(html,linkget)
            for form in all_forms:
                print form
                if str(form).find('SelectControl(bizType') != -1:
                    register_form = form
                    break
            if not register_form:
                info_account = self.get_ebay_selling_infomation(email,password,cookies_path)
                cookiespath = self.save_cookies(cookies_path,email)
                self.update_status('Login and get cookies done ^.^')
                print 'check die:cant find register_form bizType'
                return 'check die:cant find register_form bizType'
            min = 100000000
            max = 999999999
            employerIDNum = str(random.randint(min, max))
            register_form['bizType']=['1']
            register_form['employerIDNum']=employerIDNum
            register_form['listingValue']=[str(register_form['listingValue'][random.randint(0,len(register_form['listingValue'])-1)])]
            request = register_form.click()
            i = 0
            while i <= 4:
                try:
                    r = self.browser.open(request)
                    html = r.read()
                    linkget=r.geturl()
                    self.add_header(linkget)
                except:
                    time.sleep(1)
                else:
                    break
                i += 1
            if i >= 4:
                print 'check die:socks die'
                return 'check die:socks die'


        # cookiespath = self.save_cookies(cookies_path,email)
        info_account = self.get_ebay_selling_infomation(email,password,cookies_path)
        cookiespath = self.save_cookies(cookies_path,email)
        self.update_status('Login and get cookies done ^.^')
        return info_account+'#==#'+cookiespath


class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = mimetools.choose_boundary()
        return

    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, value))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((fieldname, filename, mimetype, body))
        return

    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.
        parts = []
        part_boundary = '--' + self.boundary

        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              '',
              value,
            ]
            for name, value in self.form_fields
            )

        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )

        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)

def main():
    #eastliu@hotmail.com|1218hhhh|do-l228|Positive feedback last 12 months:0%|Feedback score:0 )|0 Feedback received|Revised Feedback: 0|Sep-08-14 in   United States
    listbilling = 'thi phuong|nguyen|861x E Sandhill cirr|free mail# 262136|Carson|CA|90741|'
    list_address_drop = 'thi phuong|nguyen|861x E Sandhill cirr|free mail# 262136|Carson|CA|90741|'
    #swissmiss57@hotmail.com|Leifer|aasta2006|Positive feedback:|Feedback score:|137 Feedback received|Revised Feedback: 0|United States
    title = 'Keurig 2.0 K250 Coffee Brewing System (White) 100% new'


    path_img = 'D:/pic/k250_White.jpg'
    price = '80'
    quality = '5'
    description = """
PRODUCT FEATURES

    Keurig 2.0 system brews a single K-cup or a 4-cup K-carafe pack.
    Keurig 2.0 Brewing Technology reads the lid to deliver a perfect beverage every time.
    Strength Control setting lets you brew a stronger cup.
    Removable 40-ounce water reservoir offers easy filling and cleaning.
    K-Cup Portion Pack allows you to enjoy a single serving.
    Touch display makes it easy to customize settings.
    Energy-saver mode and brewer maintenance alerts ensure long-lasting use.

WHAT'S INCLUDED

    4 K-Cup packs
    Water filter handle
    Water filter cartridge
    Keurig descaling solution

PRODUCT CARE

    Manufacturer's 1-year limited warranty

PRODUCT DETAILS

    14"H x 14"W x 15"D
    40-oz. water reservoir
    1470 watts"""
    paypal_account = 'yank462ppp@yahoo.com'
    # header = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_7; da-dk) AppleWebKit/533.21.1 (KHTML, like Gecko) Version/5.0.5 Safari/533.21.1'
    cookiespath = 'D:/Dropbox/forum_automator/storagon tool/tool/ebaymanager/fsgrafix/cookies.txt'
    new_emai = ''

    email='manonmath_mun@outlook.com'
    password = 'tommy2006'
    phone='4237978894'
    sock = '127.0.0.1:9951'
    ebay_information='John|Compton|4788 East D Ave||Kalamazoo|MI|49009'
    ebay_process = Ebay(header='Mozilla/5.0 (Windows NT 10.0; WOW64; rv:54.0) Gecko/20100101 Firefox/54.0')
    # ebay_process.check(email,password,sock='127.0.0.1:9951',sock_type='socks')
    #wacker212003@yahoo.com|jsl123456|litwacker|Positive feedback last 12 months:100%|Feedback score:209|88 Feedback received|Revised Feedback: 0|Jan-18-08 in   United States
    # ebay_process.check(email='tuan.storagon@gmail.com',password='hanoi123',sock='127.0.0.1:9951',sock_type='sock')
    # ebay_process.login_savecookies(email,password,cookiespath=cookiespath,sock=sock)
    ebay_process.change_email_phone(email,password,new_email=new_emai,new_phone=phone,sock='127.0.0.1:9951',cookies_path=cookiespath)
    # ebay_process.create_account(new_emai,password,phone,ebay_information,sock='127.0.0.1:9951')
    # ebay_process.change_email(email,password,new_email=new_emai,sock=sock,cookies_path=cookiespath)
    # ebay_process.change_secret_question(email,password,sock=sock,cookies_path=cookiespath)
    # ordervr.login_savecookies(email,password,sock=sock,cookiespath=cookiespath,header=header)
    # ebay_process.list_an_item_new(title,path_img=path_img,description=description,price=price,quality=quality,paypal_account=paypal_account,cookies_path=cookiespath,email=email,password=password,sock='127.0.0.1:9951')
    # ordervr.create_paypal(email,password,'dsdsadduij_mun@hotmail.com',get_info=True)
    # ordervr.get_order_infomation(email=email,password=password,cookies_path=cookiespath,sock=sock)
    # ordervr.add_tracking(email=email,password=password,cookies_path=cookiespath,sock=sock,orderid='161924913622_1347335936006_ps',tracking='1Z2991730300089514')
    # ordervr.change_email_phone(email,password,new_email='ho6333mama@yahoo.com',new_phone='',cookies_path=cookiespath,sock=sock)
    # ebay_process.check(email='vinylkuiper2v0_mun@outlook.com',password='hanoi123',sock='127.0.0.1:9951')
if __name__ == "__main__":
    sys.exit(main())

