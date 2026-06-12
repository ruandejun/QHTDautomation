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


class Completehealthproducts:
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
        self.site_url = 'https://www.completehealthproducts.com.au/'
        self.cookies_data = 'PHPSESSID=dbedca7b29a89d11635fe52f5b4bfee0; __utmc=208563712; __utmz=208563712.1632747953.5.2.utmcsr=google|utmccn=(organic)|utmcmd=organic|utmctr=(not%20provided); __utma=208563712.1166266219.1632491873.1633008040.1633039675.12; __utmt=1; __utmb=208563712.7.10.1633039675'


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
                r = self.browser.open(self.site_url+'login', timeout=30)
                html = r.content
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
            if form['action'].find('execfunc.php') != -1:
                changeform = form
                break
        if not changeform:
            print('check die: cant find customers_email_address form')
            return 'check die:socks die:'
        data = {}
        data['customers_email_address'] = email
        data['customers_password'] = password
        data['labels[customers_email_address]'] = 'Email'
        data['labels[customers_password]'] = 'Password'
        data['labels[login]'] = ''
        data['groups[]'] = '11'
        data['callback'] = 'login.php'
        post_url = changeform['action']
        # print(dien)
        # self.add_header('https://susi.bigfishgames.com/login',XMLHttpRequest=True)
        i = 0
        while i < 4:
            try:
                # self.browser.link_host = 'susi.bigfishgames.com'
                print('Trying Post to:', post_url)
                r = self.browser.open(self.site_url+post_url,data, timeout=30)
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
        if html.find('class="logoff_link"') == -1:
            print('socks die')
            return 'check die:socks die:'
        # r = self.browser.open('https://susi.bigfishgames.com/confirm', timeout=5)

        print('Logged to your account')
        return email.strip() + '|' + password.strip()

    def get_products_list(self,linkItem):
        self.update_status('Trying open catalogues Link:' + linkItem)
        self.browser.add_header(extraHeader={'cookie':self.cookies_data})
        i = 0
        while i < 4:
            try:
                r = self.browser.open(linkItem, timeout=30)
                html = r.text
                # print(html)
                linkget = r.url
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

        soup = BeautifulSoup(html, 'html.parser')
        product_list_soup = soup.find_all('div', attrs={"class": "prod-text"})
        list_produts = []
        for line_product in product_list_soup:
            product_url = line_product.find('a', href=re.compile("id="))['href']
            list_produts.append(self.site_url+product_url.strip())


        # list_produts = re.findall(r'products_description altera">\s*<a href="(.+?)"',html)
        return list_produts
        # print(list_produts)
        # c = open('dien.html','w', encoding='utf-8')
        # c.write(html)

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
        c = open('dien.html','w', encoding='utf-8')
        c.write(html)
        tags = []
        data = {}
        images=[]
        if html.find('<span>out of stock</span>') != -1:
            data['inventory_quantity'] = 0
            data['old_inventory_quantity'] = 0
            data['weight'] = 0
            return data
        else:
            data['inventory_quantity'] = 10
            data['old_inventory_quantity'] = 10
            data['weight'] = 0
        #{src=link_image}
        soup = BeautifulSoup(html, 'html.parser')
        title = soup.find('h1').text
        print('title',title)
        tags.append(title)
        data['title'] = title
        id_re = re.search('name="add\[(.+?)\]',html)
        product_id= None
        if id_re:
            product_id = id_re.group(1).strip()
            if product_id.find('_') != -1:
                product_id = product_id.split('_')[0]
            print('product_id',product_id)
        barcode_re = re.search('Barcode <strong>(.+?)</strong>', html, re.DOTALL)
        if barcode_re:
            barcode = barcode_re.group(1).strip()
            data['sku'] = barcode
            data['barcode'] = barcode
            print('barcode',barcode)
        try:
            link_image = soup.find('img', attrs={'src': re.compile(product_id)})['src']
        except:
            return data

        print('image_re',link_image)

        link_image = self.site_url+link_image
        image_base64 = base64.b64encode(self.browser.open(link_image).content).decode('utf-8')
        images.append({'attachment': image_base64})
        print(image_base64)
        data['images'] = images
        print(link_image)
        price_re = re.search("\).value,'(.+?)',",html)
        if price_re:
            price_org = float(price_re.group(1).strip())
            data['cost'] = price_org
            print('cost',price_org)
            product_price =  int(price_org * float(1.35))+ 0.95
            data['price'] = product_price
            print('product_price',product_price)
        try:
            WEBBRAND = soup.find('a', attrs={'id':'brand-btn'})['title']
            print('WEBBRAND',WEBBRAND)
            tags.append(WEBBRAND)
            data['vendor'] = WEBBRAND
            print(WEBBRAND)
        except:
            data['vendor'] = ''
        list_breadcrumb = soup.find('ul', attrs={"id": "breadcrumbs"}).find_all('a', href=True)
        product_collection = list_breadcrumb[1].text
        product_type = list_breadcrumb[-1].text
        tags.append(product_type)
        data['product_type'] = product_type
        print(product_type)
        html_body_re = re.search('</a></h2>(.+?)<a href=', html, re.DOTALL)
        if html_body_re:
            data['body_html'] = html_body_re.group(1).strip()
            print(html_body_re.group(1).strip())
        else:
            data['body_html'] = title
        data['tags'] = tags
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



    ordervr = Completehealthproducts()


    i=5
    lastPage=100
    while i <= lastPage:
        print('==page==',i)
        products_list = ordervr.get_products_list('https://www.completehealthproducts.com.au/grocery.php?pg='+str(i))
        i+=1
        for line_product in products_list:
            # break
            data = ordervr.get_product_informations(line_product)
            data['inventory_quantity'] = 10
            data['old_inventory_quantity'] = 10
            data['weight'] = 1
            data['weight_unit'] = 'kg'
            data['status'] = 'active'
            import myshopify
            print(data)
            # print(stop)
            shopifyApi = myshopify.MyShopify()
            try:
                r = shopifyApi.get_products(title=data['title'])
                get_products = r.json()
                print(get_products)
            except:
                continue

            if data['inventory_quantity'] != 0 and len(get_products['products']) == 0:
                print('==Trying create product==')
                try:
                    created = shopifyApi.create_product(**data)
                    print(created)
                except:
                    continue
                else:
                    if 'product' not in created:
                        continue
                    products_variants = shopifyApi.get_products_variants(created['product']['id'])
                    print(products_variants)
                    for line_var in products_variants['variants']:
                        time.sleep(0.5)
                        print(line_var)
                        print(line_var['inventory_item_id'])
                        update_inventory = {'id':line_var['inventory_item_id'], 'cost':data['cost']}
                        r = shopifyApi.updateInventoryItem(line_var['inventory_item_id'],update_inventory)
                        print('==updated InventoryItem==', r)
                        # data = {'id':created['id']['id'],
                        #     'price':float(line_var['price']) * 0.9,
                        #     'compare_at_price':''
                        # }
                        # r = shopifyApi.update_product_variants(line_var['id'],data)
                        # print('==updated variant==',r)

            try:
                vendor_collections = shopifyApi.get_smart_collections(title=data['vendor'])
            except:
                continue
            if not vendor_collections['smart_collections']:
                data_collection = {}
                data_collection['title'] = data['vendor']
                data_collection['column'] = 'vendor'
                data_collection['relation'] = 'contains'
                data_collection['condition'] = data['vendor']
                try:
                    vendor_collections = shopifyApi.create_smart_collections(**data_collection)
                except:
                    continue
            print(vendor_collections)
            try:
                product_type_collections = shopifyApi.get_smart_collections(title=data['product_type'])
            except:
                continue
            if not product_type_collections['smart_collections']:
                data_collection = {}
                data_collection['title'] = data['product_type']
                data_collection['column'] = 'type'
                data_collection['relation'] = 'contains'
                data_collection['condition'] = data['product_type']
                try:
                    product_type_collections = shopifyApi.create_smart_collections(**data_collection)
                except:
                    continue
            print(product_type_collections)
    print(products_list)



if __name__ == "__main__":
    sys.exit(main())
