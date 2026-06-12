#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import re, random;
import sys, time,os;
from PIL import Image, ImageMath
import json, urllib, base64, mybrowser,captcha2upload, requests, shopify
from urllib.parse import urlparse, parse_qsl, quote_plus


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


class MyShopify:
	""" Test reg forum
	"""


	def __init__(self, emit='', qtcode='', header='', orderfinalForm=[], updatestatus='update',captcha_queue=None):
		self.updatestatus = updatestatus
		self.orderfinalForm = orderfinalForm;

		# ua.set_debug_responses(False)
		self.captcha_queue = captcha_queue;
		self.emit = emit;
		self.qtcode = qtcode;
		self.browser = requests.session()
		# API_KEY = ''
		# self.shopify = shopify.Session.setup(api_key=API_KEY, secret=API_SECRET)


		# self.browser.link_host = 'store.bigfishgames.com'
		# self.browser.link_origin = 'https://store.bigfishgames.com'
		self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'

		self.main_url = 'https://ApiKey:shppa_FakeShopifyPasswordForBypassingGitHubPush@bearfootwholefoods.myshopify.com/admin/api/2021-07/';

	def get_products(self, **kwargs):
		get_url = self.main_url+'products.json'
		if kwargs.items():
			get_url = get_url + '?'
		for key, value in kwargs.items():
			get_url = get_url+'&'+key+'='+quote_plus(value)
			# print("%s == %s" % (key, value))
		print(get_url)
		r = self.browser.get(get_url)
		# print()
		return r

	def get_products_variants(self,product_id, **kwargs):

		get_url = self.main_url + 'products/' + str(product_id) + '/'+'variants.json'
		for key, value in kwargs.items():
			get_url = get_url + '&' + key + '=' + quote_plus(value)
		# print("%s == %s" % (key, value))
		print(get_url)
		r = self.browser.get(get_url)
		return r.json()
	def open_next_page(self,link):
		r = self.browser.get(link)
		return r
	def update_product_variants(self,variant_id,data):

		pay_load = {
			"variant": data#product_dicts
		}
		print(self.main_url+'variants/'+str(variant_id)+'.json')
		r = self.browser.put(self.main_url+'variants/'+str(variant_id)+'.json',json=pay_load)
		return r.json()

	def updateInventoryItem(self,inventory_id,data):

		pay_load = {
			"inventory_item": data#product_dicts
		}
		print(self.main_url+'inventory_items/'+str(inventory_id)+'.json')
		r = self.browser.put(self.main_url+'inventory_items/'+str(inventory_id)+'.json',json=pay_load)
		return r.json()
	def setInventoryLevels(self, data):
		pay_load = data
		post_url = self.main_url + 'inventory_levels/set.json'
		print(post_url)
		r = self.browser.post(post_url,json=pay_load)
		return r.json()
	def getInventoryLevels(self,**kwargs):

		get_url = self.main_url + 'inventory_levels.json'
		if kwargs.items():
			get_url = get_url + '?'
		for key, value in kwargs.items():
			get_url = get_url + '&' + key + '=' + quote_plus(str(value))
		# print("%s == %s" % (key, value))
		print(get_url)
		r = self.browser.get(get_url)
		return r.json()

	def getInventoryItem(self,inventory_item_id,**kwargs):

		get_url = self.main_url + 'inventory_items/' + inventory_item_id +'.json'
		if kwargs.items():
			get_url = get_url + '?'
		for key, value in kwargs.items():
			get_url = get_url + '&' + key + '=' + quote_plus(value)
		# print("%s == %s" % (key, value))
		print(get_url)
		r = self.browser.get(get_url)
		return r.json()

	def create_product_variants(self,product_id, variant):

		get_url = self.main_url + 'products/' + product_id + '/' + 'variants.json'
		pay_load = {
			"variant": variant#product_dicts
		}
		print(get_url)
		r = self.browser.post(get_url,json=pay_load)
		return r.json()
	def get_smart_collections(self, **kwargs):
		get_url = self.main_url+'smart_collections.json'
		if kwargs.items():
			get_url = get_url + '?'
		for key, value in kwargs.items():
			get_url = get_url+'&'+key+'='+quote_plus(value)
			# print("%s == %s" % (key, value))
		print(get_url)
		r = self.browser.get(get_url)
		return r.json()
	def create_smart_collections(self,**kwargs):

		product_exp = {
				"title": kwargs['title'],
				'published_scope': 'global',
				"rules": [
					  {
						"column": kwargs['column'],
						"relation": kwargs['relation'],
						"condition": kwargs['condition']
					  }
					],
				}

		pay_load = {
			"smart_collection": product_exp#product_dicts
		}

		r = self.browser.post(self.main_url+'smart_collections.json',json=pay_load)
		return r.json()

	def update_product(self,product_id,data):

		pay_load = {
			"product": data#product_dicts
		}
		print(self.main_url+'products/'+str(product_id)+'.json')
		r = self.browser.put(self.main_url+'products/'+str(product_id)+'.json',json=pay_load)
		return r.json()


	def create_product(self,**kwargs):

		product_exp = {'title': kwargs['title'],
					'body_html': kwargs['body_html'],
					'vendor': kwargs['vendor'],
					'product_type': kwargs['product_type'],
					'status': kwargs['status'],
					'published_scope': 'global',
					'tags': kwargs['tags'],
					'variants': [{'title': 'Default Title',
								  'price': kwargs['price'],
								  'sku': kwargs['sku'],
								  'position': 1,
								  'inventory_policy': 'deny',
								  'fulfillment_service': 'manual',
								  'inventory_management': 'shopify',
								  'option1': 'Default Title',
								  'option2': None,
								  'option3': None,
								  'taxable': True,
								  'barcode': kwargs['barcode'],
								  'grams': 0,
								  'image_id': None,
								  'weight': kwargs['weight'],
								  'weight_unit': 'kg',
								  'inventory_quantity': kwargs['inventory_quantity'],
								  'old_inventory_quantity': kwargs['old_inventory_quantity'],
								  'requires_shipping': True}],
					'images': kwargs['images'],# list {src=link_image}
				}

		pay_load = {
			"product": product_exp#product_dicts
		}

		r = self.browser.post(self.main_url+'products.json',json=pay_load)
		return r.json()


def main():


	# listbilling = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
	# list_address_drop = 'Yingge|Wang|39078 Guradino Dr. APT 308||Fremont|CA|94538|Visa6087|4388576044536087|2|2019'
	#1288375392|FPTgeoEICiYnzs@sbcglobal.net|brynargust@yahoo.com|bryn0320
	#4147098647146372|12|2019|00|Brandon Braun|Address||||||bdogg3000@gmail.com
	#5376280708882256|12|2026
	api = MyShopify()
	variant = {
		"option1": "10 Pairs",
		"price": "70"
	}
	product_id = api.get_products_variants('9340755001695')
	print(product_id)
	# print(dien)
	# last_product = list_products['products'][-1]
	current_last_product = None
	max_page = 300

	# i = 0
	# while i < max_page:
	# 	i+=1
	# get_data = {'limit': '250', 'status': 'active'}
	# r = api.get_products(**get_data)
	# main_url = 'https://ApiKey:shppa_FakeShopifyPasswordForBypassingGitHubPush@bearfootwholefoods.myshopify.com/admin/api/2021-07/';
	# list_products = r.json()
	# # print(list_products)
	# for line in list_products['products']:
	# 	print(line)
	# while 1:


	# 	list_products = r.json()
	# 	if 'link' not in r.headers:
	# 		break

	# 	next_page = main_url+r.headers['link'].replace('>; rel="next"','').replace('<','').replace('https://bearfootwholefoods.myshopify.com/admin/api/2021-07/','')
	# 	# print(list_products)
	# 	# print(list_products['products'][-1])
	# 	print(next_page)

	# 	# get_data['since_id'] = str(last_product['id'])
	# 	# list_products = api.get_products(**get_data)
	# 	# print(list_products)
	# 	for line in list_products['products']:

	# 		if line['variants'][0]['compare_at_price']:
	# 			if float(line['variants'][0]['compare_at_price']) > float(line['variants'][0]['price']):
	# 				print(line['variants'][0]['compare_at_price'],line['variants'][0]['price'])
	# 				print(line['id'])
	# 				data = {'id': line['id'], 'status': 'draft'}
	# 				update = api.update_product(line['id'],data)
	# 				print('==updated product==',update)
	# 			else:
	# 				products_variants = api.get_products_variants(line['id'])
	# 				print(products_variants)
	# 				for line_var in products_variants['variants']:
	# 					time.sleep(0.5)
	# 					print(line_var)
	# 					# print(line_var['inventory_item_id'])
	# 					# update_inventory = {'id':line_var['inventory_item_id'], 'cost':line['variants'][0]['compare_at_price']}
	# 					# r = api.updateInventoryItem(line_var['inventory_item_id'],update_inventory)
	# 					# print('==updated InventoryItem==', r)
	# 					# data = {'id':line['id'],
	# 					# 	'price':float(line_var['price']) * 0.9,
	# 					# 	'compare_at_price':''
	# 					# }
	# 					# r = api.update_product_variants(line_var['id'],data)
	# 					# print('==updated variant==',r)
	# 		# break
	# 	# break
	# 	r = api.open_next_page(next_page)
	# 	# print(r.json())
	# 	print(r.headers)
		# last_product = list_products['products'][-1]
		# if last_product != current_last_product:
		# 	current_last_product = last_product
		# else:
		# 	break
	# create_variants = api.create_product_variants('7040114983067',variant)
	# print(create_variants)
	# list_products = api.get_products_variants('7040114983067')
	#
	# print(list_products)
	# for line in list_products['variants']:
	# 	data = {'id':line['id'],
	# 		'compare_at_price':''
	# 	}
	# 	r = api.update_product_variants(**data)
	# 	print(r)


	# data = {}
	# data['title'] = 'test'
	# data['column'] = 'title'
	# data['relation'] = 'starts_with'
	# data['condition'] = 'test'

	# created_collection = api.create_smart_collections(**data)
	# print(created_collection)
	# created = api.create_product({})
	# print(created)
	# ordervr.check(ccnumber='5376282688376242',ccmonth='12',ccyear='2026',cvv='9700',sock='127.0.0.1:1084')
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
