#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time,os;
from PIL import Image, ImageMath
import json, urllib, base64, mybrowser,captcha2upload
from urllib.parse import urlparse, parse_qsl, unquote, unquote_plus
from bs4 import BeautifulSoup, SoupStrainer;
import base64
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


class Uhp:
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
        # self.browser.link_host = 'store.bigfishgames.com'
        # self.browser.link_origin = 'https://store.bigfishgames.com'
        self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'
        self.site_url = 'https://shop.uhp.com.au/'


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
        self.update_status('Trying login to Your account:' + email + '|' + password)
        i = 0
        while i < 4:
            try:
                r = self.browser.open('https://www.uhp.com.au/customer/account/login/', timeout=30)
                html = r.text
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die:'



        all_forms = self.browser.selectForm(html)
        # print(all_forms)
        changeform =None
        for form in all_forms:
            # print(form)
            if form['action'].find('customer/account/loginPost/') != -1:
                changeform = form
                break
        if not changeform:
            print('check die: cant find customers_email_address form')
            return
        inputForm = self.browser.getInputForm(changeform)
        form_key_re = re.search('form_key" type="hidden" value="(.+?)"', html)
        if form_key_re:
            print(inputForm)
            form_key = form_key_re.group(1).strip()
            print('form_key==', form_key)
            # print(dien)
            data = {}
            data['login[username]'] = email
            data['login[password]'] = password
            data['send'] = ''
            data['form_key'] = form_key

            post_url = changeform['action']
            # print(dien)
            self.add_header('https://www.uhp.com.au/',extraHeader={'content-type':'application/x-www-form-urlencoded'})
            i = 0
            while i < 4:
                try:
                    # self.browser.link_host = 'susi.bigfishgames.com'
                    print('Trying Post to:', post_url)
                    r = self.browser.open(post_url, data, timeout=30)
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
            
            c = open('dien.html','w', encoding='utf-8')
            c.write(html)
            if html.find('My Wish List') == -1:
                print('socks die')
                return
            # r = self.browser.open('https://susi.bigfishgames.com/confirm', timeout=5)

            print('Logged to your account')
            return email.strip() + '|' + password.strip()

    def get_products_list(self,linkItem):
        self.update_status('Trying open catalogues Link:' + linkItem)
        i = 0
        while i < 4:
            try:
                r = self.browser.open(linkItem, timeout=30)
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
        # list_produts = re.findall(r'<a href="(.+?)" class="product photo product-item-photo',html)
        soup = BeautifulSoup(html, 'html.parser')
        list_items = soup.find_all('li', attrs={"class": "item product product-item"})
        list_products = []
        for line_item in list_items:
            data_item = {}
            if not line_item.find("div", attrs={"class": "stock unavailable"}):
                item_url = line_item.find("a", attrs={"class": "product photo product-item-photo"}, href=True)['href'].strip()
                item_cover = line_item.find("img", attrs={"class": "product-image-photo"})['src'].split('?')[0].strip()
                item_sku = line_item.find("span", attrs={"class": "product-item-sku"}).text.strip()
                item_brand = line_item.find("p", attrs={"class": "product-item-brand"}).text.strip()
                item_name = line_item.find("div", attrs={"class": "product name product-item-name"}).text.strip()
                item_price = line_item.find("span", attrs={"data-price-type": "finalPrice"})['data-price-amount'].strip()
                
                item_price_sale_exits = line_item.find("span", attrs={"class": "rrp-price"})
                if not item_price_sale_exits:
                    item_price_sale_exits = str(round(float(item_price)/0.65,2))
                else:
                    item_price_sale_exits = item_price_sale_exits.text
                item_price_sale = item_price_sale_exits.replace('RRP','').replace('$','').strip()
                
                item_weight_info = line_item.find("div", attrs={"class": "product name product-item-name"}).find('b').text.lower().strip()
                if item_weight_info.find('x') != -1:
                    item_price = round(float(item_price)/float(item_weight_info.split('x')[0]),2)
                    item_name = item_name.replace(item_weight_info.split('x')[0]+'x','')
                    print(item_name, item_price)                    
                if item_weight_info.find('ml') != -1 and item_weight_info.find('x') != -1:
                    item_weight = (float(item_weight_info.replace('ml', '').split('x')[0]) * float(item_weight_info.replace('ml', '').split('x')[1]))/1000
                elif item_weight_info.find('ml') != -1:
                    item_weight = float(item_weight_info.replace('ml', ''))/1000
                    # print(item_weight)
                elif item_weight_info.find('l') != -1:
                    item_weight = float(item_weight_info.replace('l', ''))
                    # print(item_weight)                
                elif item_weight_info.find('kg') != -1:
                    item_weight = float(item_weight_info.replace('kg', ''))
                    # print(item_weight)                
                elif item_weight_info.find('g') != -1 and item_weight_info.find('x') != -1:
                    item_weight = (float(item_weight_info.replace('g', '').split('x')[0]) * float(item_weight_info.replace('g', '').split('x')[1]))/1000

                elif item_weight_info.find('g') != -1:
                    item_weight = float(item_weight_info.replace('g', ''))/1000
                    # print(item_weight)
                else:                                
                    item_weight = 1

                data_item['item_url'] = item_url
                data_item['item_cover'] = item_cover
                data_item['item_sku'] = item_sku
                data_item['item_brand'] = item_brand
                data_item['item_name'] = item_name
                data_item['item_weight'] = item_weight
                data_item['item_price'] = item_price
                data_item['item_price_sale'] = item_price_sale
                # print(item_price)
                list_products.append(data_item)

        return list_products


    def get_product_informations(self, linkItem):
        self.update_status('Trying open product Link:' + linkItem)
        i = 0
        while i < 4:
            try:
                r = self.browser.open(linkItem, timeout=30)
                html = r.text
                # linkget = r.url
                # html = self.fixHTML(html);
            except Exception as e:
                print(e)
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die:'
        tags = []
        data = {}
        images=[]
        if html.find('Notify me when available') != -1:
            data['inventory_quantity'] = 0
            data['old_inventory_quantity'] = 0
            data['weight'] = 0
        else:
            data['inventory_quantity'] = 3
            data['old_inventory_quantity'] = 3
            data['weight'] = 0
        #{src=link_image}
        soup = BeautifulSoup(html, 'html.parser')

        image_re = re.search('<a href="images/products/(.+?)"',html)
        if image_re:
            link_image = self.site_url+'images/products/'+image_re.group(1).strip()

            image_base64 = base64.b64encode(self.browser.open(link_image).content).decode('utf-8')
            images.append({'attachment': image_base64})
            print(image_base64)
            data['images'] = images
            print(link_image)
        price_re = re.search('<!--B-->\s*\$(.+?)</span>',html)
        if price_re:
            compare_at_price = float(price_re.group(1).strip())
            data['compare_at_price'] = compare_at_price
            print('compare_at_price',compare_at_price)
        priceRRP_re = re.search('RRP\s*\$(.+?)<sup',html)
        if priceRRP_re:
            priceRRP = float(priceRRP_re.group(1).strip())
            data['price'] = priceRRP
            print('priceRRP',priceRRP)
        WEBBRAND_re = re.search('\[WEBBRAND\]=(.+?)"',html)
        if WEBBRAND_re:
            WEBBRAND = unquote_plus(WEBBRAND_re.group(1).strip())
            tags.append(WEBBRAND)
            data['vendor'] = WEBBRAND
            print(WEBBRAND)


        barcode_re = re.search('<h3>Barcode</h3>\s*</div>\s*<div class="infoBox">\s*<div class="infoBoxContentsBg"\s*>\s*(.+?)\s*<div class="clear">', html, re.DOTALL)
        if barcode_re:
            barcode = barcode_re.group(1).strip()
            data['sku'] = barcode
            data['barcode'] = barcode
            print(barcode)
        Carton_barcode_re = re.search('Carton Barcode:<br>\s*(.+?)\s*<', html, re.DOTALL)
        if Carton_barcode_re:
            barcode = Carton_barcode_re.group(1).strip()
            data['sku'] = barcode
            data['barcode'] = barcode
            print(barcode)
        Individual_barcode_re = re.search('Individual Barcode:<br>\s*(.+?)\s*<', html, re.DOTALL)
        if Individual_barcode_re:
            barcode = Individual_barcode_re.group(1).strip()
            data['sku'] = barcode
            data['barcode'] = barcode
            print(barcode)

        product_type = soup.find('div', attrs={"class": "breadcrumb"}).find('a', href=re.compile("display\.php\?cPath")).text
        tags.append(product_type)
        data['product_type'] = product_type
        print(product_type)
        title = soup.find("div", attrs={"id": "pageHeadingTop"}).find('h2').text
        tags.append(title)
        data['title'] = title
        print(title)
        product_attributes = soup.find("ul", attrs={"class": "product_attributes"})
        try:
            list_tags = product_attributes.find("li").text.strip().split('\n')
        except:
            list_tags = []
        tags = tags+list_tags
        data['tags'] = tags

        print(tags)
        infobox_table = soup.find_all('div', attrs={"class": "infobox_table"})
        # for line in infobox_table:
        #     print(type(line))
        # print(infobox_table)
        html_body = '\n'.join([str(item)for item in infobox_table if str(item).find('Related Products') == -1])
        data['body_html'] = html_body
        # print(html_body)
        # c = open('dien.html','w', encoding='utf-8')
        # c.write(html)
        return data

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


def main():



    ordervr = Uhp()
    logged = ordervr.site_login(email='shop@bearfootwholefoods.com.au', password='Hanoi123!@#')
    if logged:

        # line_product = 'https://shop.uhp.com.au/products_info.php?products_id=8491'
        # data = ordervr.get_product_informations(line_product)
        # print(data)
        # print(unquote_plus('MARTIN+%26+PLEASANCE'))
        # import myshopify
        # shopifyApi = myshopify.MyShopify()
        'Out Of Stock Alert'
        i=1
        lastPage=16
        while i <= lastPage:
            products_list = ordervr.get_products_list('https://www.uhp.com.au/myproducts/index/view/requisition_id/4134/?p='+str(i))
            for line_product in products_list:
                # break
                print(line_product['item_url'])
                data = ordervr.get_product_informations(line_product['item_url'])
            i+=1
            # for line_product in products_list:
            #     # break

            #     data = ordervr.get_product_informations(line_product)

            #     data['status'] = 'active'
            #     import myshopify
            #     print(data)
            #     shopifyApi = myshopify.MyShopify()
            #     try:
            #         r = shopifyApi.get_products(title=data['title'])
            #         get_products = r.json()
            #     except:
            #         continue

            #     if data['inventory_quantity'] == 0:
            #         print(get_products)
            #         print('===Found:', data['title'])
            #         for line in get_products['products']:
            #             print(line)
            #             data_product = {'id': line['id'], 'status': 'draft'}
            #             update = shopifyApi.update_product(line['id'], data_product)
            #             print(update)
            #             products_variants = shopifyApi.get_products_variants(line['id'])
            #             print(products_variants)
            #             for line_var in products_variants['variants']:
            #                 time.sleep(0.5)
            #                 # print(line_var)
            #                 print(line_var['inventory_item_id'])
            #                 update_inventory = {'id':line_var['inventory_item_id'], 'cost':data['compare_at_price']}
            #                 r = shopifyApi.updateInventoryItem(line_var['inventory_item_id'],update_inventory)
            #                 print('==updated InventoryItem==', r)
            #                 data_variants = {'id':line['id'],
            #                     'price':float(line_var['price']) * 0.9,
            #                     'compare_at_price':line_var['price'],

            #                 }
            #                 r = shopifyApi.update_product_variants(line_var['id'],data_variants)
            #                 print('==updated variant==',r)
            #                 data_get = {'inventory_item_ids':str(line_var['inventory_item_id'])}
            #                 r = shopifyApi.getInventoryLevels(**data_get)
            #                 print('==get InventoryLevels==', r)
            #                 data_levels = {'available': 0, 'inventory_item_id':line_var['inventory_item_id'],'location_id':'63468732571'}
            #                 r = shopifyApi.setInventoryLevels(data_levels)
            #                 print('==updated InventoryLevels==', r)
            #         # print(dien)
            #         continue
                # if not get_products['products']:
                #     try:
                #         created = shopifyApi.create_product(**data)
                #         print(created)
                #     except:
                #         continue
                # try:
                #     vendor_collections = shopifyApi.get_smart_collections(title=data['vendor'])
                # except:
                #     continue
                # if not vendor_collections['smart_collections']:
                #     data_collection = {}
                #     data_collection['title'] = data['vendor']
                #     data_collection['column'] = 'vendor'
                #     data_collection['relation'] = 'contains'
                #     data_collection['condition'] = data['vendor']
                #     try:
                #         vendor_collections = shopifyApi.create_smart_collections(**data_collection)
                #     except:
                #         continue
                # print(vendor_collections)
                # try:
                #     product_type_collections = shopifyApi.get_smart_collections(title=data['product_type'])
                # except:
                #     continue
                # if not product_type_collections['smart_collections']:
                #     data_collection = {}
                #     data_collection['title'] = data['product_type']
                #     data_collection['column'] = 'type'
                #     data_collection['relation'] = 'contains'
                #     data_collection['condition'] = data['product_type']
                #     try:
                #         product_type_collections = shopifyApi.create_smart_collections(**data_collection)
                #     except:
                #         continue
                # print(product_type_collections)
        # print(products_list)



if __name__ == "__main__":
    sys.exit(main())
