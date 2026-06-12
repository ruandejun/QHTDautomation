#!/usr/bin/python
# -*- coding: utf-8 -*-
import socket, sys, os, re, random, time, datetime, queue
from PyQt5 import uic, QtGui, QtCore, QtWidgets
import sqlite3 as lite
# from aescipher import AESCipher
import multiprocessing
import threading, socks
from PyQt5.QtCore import QThread, pyqtSignal
from html.parser import HTMLParser
import json, hwid
import signal
import sys
if sys.version_info[0] >= 3:
	unicode = str
import threading, openssh, emailcheck, geoip2.database, sshsocks_manager
from aescipher import AESCipher
import subprocess
# import pydevd, socket
# pydevd.settrace(host=socket.gethostname(),port=60126 ,suspend=False, trace_only_current_thread=True)
#############################Main
class MainWindow(QtWidgets.QMainWindow):
	finish_check_update = pyqtSignal(int, float, str, str)

	def __init__(self):
		super(MainWindow, self).__init__()

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

		self.checksite = CheckSite(self);
		self.SSH = SSH(self);

		self.tabbedViewWidget.addTab(self.checksite, QtGui.QIcon(appFolderPath + '/img/post.png'), "Check site");
		self.tabbedViewWidget.addTab(self.SSH, QtGui.QIcon(appFolderPath + '/img/post.png'), "SSH Manager");



		self.setCentralWidget(self.tabbedViewWidget);

		exitAction = QtWidgets.QAction(QtGui.QIcon(appFolderPath + '/img/exit.png'), "Exit", self)
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
		width, height = 1280, 800;
		screenRect = QtWidgets.QDesktopWidget().availableGeometry();
		x, y = (
			(screenRect.width() - screenRect.x() - width) / 2, (screenRect.height() - screenRect.y() - height) / 2);
		self.setGeometry(int(x), int(y), width, height);
		self.setWindowTitle("Tập đoàn triệu phú ^o^");
		self.setWindowIcon(QtGui.QIcon(appFolderPath + '/icon.jpg'))
		self.Msgbox = QtWidgets.QMessageBox(self)

		self.show()

	def close(self):
		for p in multiprocessing.active_children():
			p.terminate();
			p.join();
		QtWidgets.QApplication.instance().quit()

class CheckThread(QtCore.QThread):
	def __init__(self, statusLabel, listchecklineEdit, socklist, check_site, socksTextEdit, soluongvalid,
				 theard, usesocks='', dontsupporttextEdit='', validTextEdit='', save_file='', ssh_database='',
				 statusqueue=None, extraoption='', checkAmazon=False, checkEbay=False):
		# super(CheckThread, self).__init__()
		print ('===init CheckTheard====')
		QtCore.QThread.__init__(self);
		self.usesocks = usesocks
		print('listchecklineEdit:',listchecklineEdit)
		if not listchecklineEdit.isdigit():
			print(listchecklineEdit)
			listcheckopen = open(listchecklineEdit,'r');
			self.listcheckss = listcheckopen.read()
			listcheckopen.close()
			self.listcheckss = self.listcheckss.replace('\r', '\n')
			self.list_check = self.listcheckss.split('\n')
		else:
			list_creat = int(listchecklineEdit)
			self.list_check = []
			i = 0
			while i < list_creat:
				self.list_check.append(str(i))
				i += 1
		if check_site.find('Order Ebay Infomation') != -1:
			if re.search('==\s', self.listcheckss, re.DOTALL | re.IGNORECASE):
				print ('get kieu new')
				self.list_check = re.findall('(.+?)\s*==\s', self.listcheckss, re.DOTALL | re.IGNORECASE)
			elif re.search('//\s', self.listcheckss, re.DOTALL | re.IGNORECASE):
				print ('get kieu new')
				self.list_check = re.findall('(.+?)\s*//\s', self.listcheckss, re.DOTALL | re.IGNORECASE)
		print(len(self.list_check))

		self.listsocklist = socklist.split('\n');
		self.check_site = check_site;
		self.checkAmazon = checkAmazon;
		self.checkEbay = checkEbay;
		self.header = None;
		self.socksTextEdit = socksTextEdit;

		if soluongvalid:
			self.soluongvalid = soluongvalid;
		else:
			self.soluongvalid = None
		if self.usesocks == 'null' or self.usesocks.find('Auto') != -1:
			if self.check_site != 'Bot traffic':
				self.maxNumberOfThread = int(theard);
			else:
				self.maxNumberOfThread = 20;
		else:
			if self.soluongvalid and self.check_site != 'Bot traffic':
				self.maxNumberOfThread = int(self.soluongvalid)
			elif check_site.find('Register Paypal') != -1:
				self.maxNumberOfThread = 1
			else:
				self.maxNumberOfThread = int(theard);
		if len(self.list_check) < self.maxNumberOfThread and self.check_site != 'Bot traffic':
			self.maxNumberOfThread = len(self.list_check)

		self.total_theard_check = []
		##qt update
		self.statusLabel = statusLabel;
		self.dontsupporttextEdit = dontsupporttextEdit;
		self.save_file = save_file;
		self.validTextEdit = validTextEdit;
		self.ssh_database = ssh_database
		##status
		self.statusqueue = statusqueue
		self.extraoption = extraoption
		##
		self.sshthread_running = {}
		##send to check thread
		self.stoped = False
		self.sent_check = 0
		self.checked = 0
		self.list_valid = 0

		self.checkqueque = queue.Queue()
		self.ssh_okq = queue.Queue()
		self.sock_check = {}
		self.check_sockdie = {}
		#proxy queue
		self.proxy_queue = queue.Queue()
		# check dup
		self.mail_dup = {}
		self.line_check=''
		self.line_check_valid={}

	def check_valid_line_for_check(self, line_check, recheck_status):
		if self.check_site.find('Tracking Status') != -1:
			if 11 < len(line_check.strip()) <= 22 or line_check.strip()[:2] == '1Z' or line_check.strip()[
																					   :3] == '940' or line_check.strip()[
																									   :2] == 'C1':
				return True
			return
		elif line_check.find('|') != -1:
			if self.check_site.find('Bodybuilding Status') != -1:
				ordernumber = line_check.split('|')[0].strip()
				if len(ordernumber) != 10 or re.search('\D', ordernumber) or 3 < len(line_check) > 4:
					return True
				return
			elif self.check_site.find('Macys Status') != -1:
				ordernumber = line_check.split('|')[0].strip()
				if len(ordernumber.replace('-', '')) == 10 and ordernumber.replace('-', '').isdigit():
					return True
				return
			elif self.check_site.find('Jcp Shipped Status') != -1:
				ordernumber = line_check.split('|')[0].strip()
				if len(ordernumber.replace('-', '')) == 16 and ordernumber.replace('-', '').isdigit():
					return True
				return
			elif self.check_site.find('Jcp Status') != -1:
				ordernumber = line_check.split('|')[0].strip()
				if len(ordernumber.replace('-', '')) == 16 and ordernumber.replace('-', '').isdigit():
					return True
				return
			elif self.check_site.find('Drugstore Status') != -1:
				print ('Check Drugstore Status')
				ordernumber = line_check.split('|')[0].strip()
				if len(ordernumber) == 14:
					return True
				return
			elif self.check_site.find('Bedbath Status') != -1:
				ordernumber = line_check.split('|')[1].strip()
				if ordernumber.find('BBB') != -1:
					return True
				return
			elif self.check_site.find('CCN Gate') != -1:
				check_line = line_check.split('|')
				i = 0
				while i < len(check_line):
					line_email = check_line[i].strip()
					if 14 < len(line_email) <= 16 and line_email.strip().isdigit():
						return True
					i += 1
				return
			elif self.check_site.find('Hotmail not exist') != -1:
				if re.search('@hotmail\.|@live\.|@outlook\.', line_check, re.IGNORECASE):
					return line_check
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
							if line_email + '|' + password not in self.mail_dup or recheck_status == 'recheck' or recheck_status == 'get_ssh':
								self.mail_dup[line_email + '|' + password] = 1
								return line_email + '|' + password
					elif re.search('(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line_email):
						try:
							username = check_line[i + 1].strip()
							password = check_line[i + 2].strip()
						except:
							pass
						else:
							if line_email + '|' + username+'|'+password not in self.mail_dup or recheck_status == 'recheck':
								self.mail_dup[line_email + '|' + username+'|'+password] = 1
								return line_email + '|' + username+'|'+password
					i += 1
				return
		elif self.check_site.find('Bot traffic') != -1:
			if line_check.find('http') != -1:
				return True
		else:
			return

	def stop_ssh(self, name='',pid=''):
		socks.setdefaultproxy()
		socket.socket = socks.socksocket
		print('trying stop:' + name)
		for p in multiprocessing.active_children():
			# 'ssh:'+name
			if p.name.find(name) != -1:
				print('Stoped SSH :' + name)
				try:
					p.terminate()
					p.join()
				except:
					pass
		if pid:
			print('stop:'+str(pid))
			try:
				os.kill(int(pid),signal.SIGILL)
			except:
				pass
		# list_remove = []
		# for ssh_name in self.sshthread_running:
		#     if ssh_name == name:
		#         print '==Time Out=='+ssh_name
		#         list_remove.append(ssh_name)
		# for r in list_remove:
		#     del self.sshthread_running[r]

	def run(self):

		if self.check_site == 'Loc email':
			open_list_loc = open('totalemail.txt','r')
			if not self.save_file:
				self.save_file = open('email_loc_roi.txt','w')
			list_loc = open_list_loc.read()
			open_list_loc.close()
			for line_loc in list_loc.split('\n'):
				if line_loc.find('|') == -1:
					continue
				i = 0
				while i < line_loc.split('|'):
					if line_loc.split('|')[i].find('@') != -1:
						if self.listcheckss.find(line_loc) == -1:
							self.save_file.write(line_loc+'\n')
							self.save_file.flush()
							break
					i+=1
			self.save_file.close()
			self.statusqueue.put(('update_status', 'Done Check file email_loc_roi.txt' ))
			return
		self.theard_process = 1
		print('===run===')
		if self.usesocks == 'Auto SSH' and self.check_site != 'SSH':
			if str(self.check_site) == 'Bot traffic':
				# print( a)
				self.get_ssh_th = openssh.Getsshandproxy('ssh_database.db', get_ssh=True,
														 total_ssh_get=int(self.soluongvalid) * 10,
														 ssh_okq=self.ssh_okq)
				self.get_ssh_th.start()
				self.statusqueue.put(('update_status', 'Trying Get %s SSH' % (str(int(self.soluongvalid) * 2))))

			else:
				print('Bot openssh')
				self.get_ssh_th = openssh.Getsshandproxy('ssh_database.db', get_ssh=True,
														 total_ssh_get=len(self.list_check) * 2,
														 ssh_okq=self.ssh_okq,check_site=self.check_site)
				self.get_ssh_th.start()
				self.statusqueue.put(('update_status', 'Trying Get %s SSH' % (str(len(self.list_check)))))
		elif self.usesocks == 'Auto Proxy' and self.check_site != 'SSH':
			if str(self.check_site) == 'Bot traffic':
				self.get_ssh_th = openssh.Getsshandproxy(get_proxy=True,total_ssh_get=int(self.soluongvalid) * 2,proxy_queue=self.proxy_queue)
				self.get_ssh_th.start()
				self.statusqueue.put(('update_status', 'Trying Get %s Proxy' % (str(len(self.list_check)))))
			else:
				self.get_ssh_th = openssh.Getsshandproxy(get_proxy=True,total_ssh_get=len(self.list_check) * 2,proxy_queue=self.proxy_queue)
				self.get_ssh_th.start()
				self.statusqueue.put(('update_status', 'Trying Get %s Proxy' % (str(len(self.list_check)))))
		elif self.usesocks == 'Rsproxy':
			print('Trying Get %s Proxy' % (str(len(self.list_check))))
			self.statusqueue.put(('update_status', 'Trying Get %s Proxy' % (str(len(self.list_check)))))
			self.listsocklist = []
			i = 10000
			while i < 60000:
				self.listsocklist.append('rsproxy.online:'+str(i))
				i+=1

		while 1:
			if self.stoped:
				break
			try:
				l_check = self.list_check.pop(0)
				self.line_check = l_check
			except:
				if self.check_site == 'Bot traffic':
					if self.line_check not in self.line_check_valid:
						self.list_check.append(self.line_check)
						self.line_check_valid[self.line_check] = 1
					elif self.line_check_valid[self.line_check] <= int(self.soluongvalid):
						self.list_check.append(self.line_check)
						self.line_check_valid[self.line_check] = self.line_check_valid[self.line_check]+1
				if self.checked >= self.sent_check:
					self.statusqueue.put(('update_status', 'Check done %s/%s With %s Valid' % (
						str(self.checked), str(self.sent_check), str(self.list_valid))))

					for line_q in self.total_theard_check:
						line_q.terminate()
					break
				else:
					self.statusqueue.put(('update_status', 'Checked %s/%s With %s Valid' % (
						str(self.checked), str(self.sent_check), str(self.list_valid))))
					time.sleep(0.05)
					continue
			# print l_check,type(l_check)

			if type(l_check) is tuple:
				recheck_status, line_check = l_check
				# print '===========ok=============' + line_check
				# del self.mail_dup[line_check]
			else:
				line_check = l_check
				recheck_status = 'Check'
				# print '===========ok=============' + line_check
			if not line_check.strip():
				continue;
			# print '=====strip===='+line_check


			check_valid = self.check_valid_line_for_check(line_check, recheck_status)
			if not check_valid:
				print('not_valid',line_check)
				continue

			#print('check_valid',check_valid)
			socks_type = ''
			pid=''
			if (self.usesocks == 'socks' or self.usesocks == 'proxy') and str(self.check_site) != 'SSH':
				# get proxy tu list socks
				# print 'input proxy'
				try:
					self.sock = self.listsocklist.pop(0).strip();
				except:
					self.list_check.insert(0, line_check)
					if self.usesocks != 'Auto Proxy':
						print ('ko co socks')
						self.statusqueue.put(('update_status', 'Input Socks And Try Again'))
						self.statusqueue.put(('het_socks', 'Input Socks And Try Again'))
						time.sleep(5)

						continue;
					else:
						time.sleep(1)
						self.sock = ''
						print (len(self.listsocklist))
						if self.wait_get_proxy == 'stop' and len(self.listsocklist) == 0:
							print ('Trying Get New Proxy')
							self.statusqueue.put(('update_status', 'Trying Get New Proxy'))
							list_proxiers = self.get_proxy_for_check()
							self.listsocklist = list_proxiers.get('proxy')
							print ('=====start check ===')
							print (len(self.listsocklist))
							continue
						else:
							continue
				if not self.sock.strip():
					self.list_check.insert(0, line_check)
					continue;
				elif self.sock.find('|') != -1:
					self.sock = self.sock.split('|')[0].strip()
				if self.sock.find(':') == -1:
					self.list_check.insert(0, line_check)
					continue

				if self.usesocks == 'Auto Proxy':
					socks_type = 'proxy'
				elif self.usesocks == 'null':
					self.sock = ''
					socks_type = ''

				else:
					socks_type = self.usesocks
			elif self.usesocks == 'Rsproxy':

				try:
					self.sock = self.listsocklist.pop(0).strip();
				except:
					self.list_check.insert(0, line_check)
					self.statusqueue.put(('update_status', 'Trying Get %s Proxy' % (str(len(self.list_check)))))
					self.listsocklist = []
					i = 10000
					while i < 60000:
						self.listsocklist.append('rsproxy.online:' + str(i))
						i += 1
				socks_type = 'proxy'
			elif self.usesocks == 'Auto Proxy' and str(self.check_site) != 'SSH':
				# print '=========Auto Get Proxy=========='
				try:
					self.sock = self.proxy_queue.get()
					socks_type = 'proxy'
					pid=None
				except:
					# print l_check
					if type(l_check) is tuple:
						self.list_check.insert(0,l_check)
					else:
						self.list_check.insert(0,('get_ssh',l_check))
					# print '===========len:',len(self.list_check)
					time.sleep(0.05)
					continue
				print ('============'+self.sock+'=========')
			elif self.usesocks == 'Auto SSH' and str(self.check_site) != 'SSH':
				# print '=========Auto Get SSH=========='
				list_remove = []
				for ssh_name in self.sshthread_running:
					start_time,pid = self.sshthread_running[ssh_name]
					if int(time.time() - start_time) >= 180:
						print ('==Time Out=='+ssh_name)
						self.stop_ssh(ssh_name,pid=pid)
						list_remove.append(ssh_name)
				for r in list_remove:
					del self.sshthread_running[r]
				try:
					self.sock, pid = self.ssh_okq.get_nowait()
				except:

					if type(l_check) is tuple:
						self.list_check.insert(0,l_check)
					else:
						self.list_check.insert(0,('get_ssh',l_check))
					# print '===========len:',len(self.list_check)
					time.sleep(0.05)
					continue
				self.sshthread_running[self.sock]= (time.time(),pid)
				socks_type = 'socks'
				print ('============'+self.sock+'=========')

			else:
				self.sock=''
				socks_type=''


			if len(self.total_theard_check) < self.maxNumberOfThread:
				checkThread = CheckThreadMinor(self);
				checkThread.start();
				self.total_theard_check.append(checkThread)
			##
			print((str(self.theard_process), line_check, self.check_site, self.sock, socks_type,
								  self.extraoption, self.usesocks,pid))
			self.checkqueque.put((str(self.theard_process), line_check, self.check_site, self.checkAmazon,self.checkEbay, self.sock, socks_type,
								  self.extraoption, self.usesocks,pid))
			##
			if recheck_status == 'Check' or recheck_status == 'get_ssh':
				self.sent_check += 1
			self.theard_process += 1

			self.statusqueue.put(('update_status', 'Checked %s/%s With %s Valid' % (
				str(self.checked), str(self.sent_check), str(self.list_valid))))
			time.sleep(0.05)
		print ('===stop all threading===')
		# stop all thread
		if self.usesocks == 'Auto SSH' or self.usesocks == 'Auto Proxy':
			self.stop_all_thread(self.maxNumberOfThread)

		return

	def stop_all_thread(self, total_stop):

		# self.get_ssh_th.stop = True

		while self.checked < self.sent_check:
			self.statusqueue.put(('update_status', 'Checked %s/%s With %s Valid' % (
				str(self.checked), str(self.sent_check), str(self.list_valid))))

			# print threading.enumerate()
			time.sleep(0.05)
		if self.usesocks == 'Auto SSH':
			print ('===Trying Stop all ssh runing===' + str(len(multiprocessing.active_children())))
			self.statusqueue.put(('update_status', 'Check done %s/%s With %s Valid' % (
				str(self.checked), str(self.sent_check), str(self.list_valid))))
			while len(multiprocessing.active_children()) > 0:
				for p in multiprocessing.active_children():
					p.terminate();
					p.join()
				time.sleep(3)
			return

class CheckThreadMinor(QtCore.QThread):
	def __init__(self, checkmain):
		print('==init CheckThreadMinor==')
		# super(CheckThreadMinor, self).__init__()
		QtCore.QThread.__init__(self);
		self.checkmain = checkmain

	def run(self):
		while 1:
			self.name_theard, self.line_check, self.check_site, self.checkAmazon, self.checkEbay, self.sock, self.sock_type, self.extraoption, self.usesocks, self.pid = self.checkmain.checkqueque.get()

			print('===Bat Dau Check===')
			try:
				emailcheckConnection = emailcheck.Emailcheck(header=self.checkmain.header,
															 appFolderPath=appFolderPath);
				status_recive = emailcheckConnection.check_email(self.line_check, check_site=self.check_site,
																 sock=self.sock, sock_type=self.sock_type,
																 extraoption=self.extraoption);

				if status_recive.find('socks die') != -1:
					print('===========socks die===========')
					self.stop_ssh(name=self.sock,pid=self.pid)
					try:
						value_sockdie = self.checkmain.check_sockdie[self.line_check]
					except:
						value_sockdie = 1
					else:
						value_sockdie += 1

					self.checkmain.check_sockdie[self.line_check] = value_sockdie
					if value_sockdie >= 10:
						self.checkmain.statusqueue.put_nowait(('uncheck', self.line_check))
						self.checkmain.checked += 1
					elif str(self.usesocks) != 'Auto SSH' and str(self.usesocks) != 'Auto Proxy':
						self.checkmain.statusqueue.put_nowait(('uncheck', self.line_check))
						self.checkmain.checked += 1
					else:
						print('===Recheck=='+self.line_check)
						self.checkmain.list_check.insert(0,('recheck', self.line_check))
						# self.checkmain.sent_check -= 1
						# self.checkmain.socksdie = True

				else:
					print('==ok==' + status_recive)
					self.checkmain.checked += 1
					if status_recive.find('check die') == -1:
						self.checkmain.list_valid += 1
						self.checkmain.statusqueue.put_nowait(('check_done', status_recive))

					if self.sock:
						try:
							value_ssh = self.checkmain.sock_check[self.sock]
						except:
							value_ssh = 1
						else:
							value_ssh += 1
						self.checkmain.sock_check[self.sock] = value_ssh
						if value_ssh >= 10:
							self.stop_ssh(name=self.sock,pid=self.pid)
						elif self.usesocks == 'Auto SSH':
							print ('==input socks==')
							self.checkmain.ssh_okq.put_nowait((self.sock, self.pid))
			except Exception as e:
				print(e)
				self.checkmain.statusqueue.put_nowait(('uncheck', self.line_check))
				self.checkmain.checked += 1
				self.stop_ssh(name=self.sock, pid=self.pid)

			time.sleep(0.05)

	def stop_ssh(self, name='',pid=''):
		# socks.setdefaultproxy()
		# socket.socket = socks.socksocket
		print('trying stop:' + name)
		for p in multiprocessing.active_children():
			# 'ssh:'+name
			if p.name.find(name) != -1:

				p.terminate();
				p.join();
				print('Stoped SSH :' + name)
		if pid:
			print('stop:'+str(pid))
			try:
				os.kill(int(pid),signal.SIGILL)
			except:
				pass

class CheckSite(QtWidgets.QWidget):
	def __init__(self, mainWindow):
		super(CheckSite, self).__init__();
		# variable
		self.formReady = [];
		self.submitFormThread = None
		self.lastFilePath = ""
		self.lastDirContentPath = ""
		global registerForm
		registerForm = []
		self.save_file = ''
		self.fileForumPath = ''
		self.socksTextEdit = ''
		self.dontsupporttextEdit = ''
		self.validTextEdit = ''

		self.mainWindow = mainWindow
		uic.loadUi(appFolderPath + '/ui/checksite.ui', self)
		# connect
		self.startButton.clicked.connect(self.startCheck)
		self.savepushButton.clicked.connect(self.email_save_file)
		self.stopButton.clicked.connect(self.Stoptheard)
		self.listEmailButton.clicked.connect(self.email_select_file)

		##ssh setup
		if not os.path.isdir(appFolderPath + '/ssh/'):
			os.makedirs(appFolderPath + '/ssh/')
		listdircatalog = os.listdir(appFolderPath + '/ssh/')
		added = 0
		i = 0
		while i < len(listdircatalog):
			linecatalog = listdircatalog[i]
			if not os.path.isdir(appFolderPath + '/ssh/' + linecatalog) and linecatalog.find('.db') != -1:
				self.comboBoxcheck_ssh_database.addItem(linecatalog)
			i += 1
		# show
		self.show();
		global orderfunction
		self.hwid = hwid.Hwid()
		hwid_id = self.hwid.get_hwid()
		orderfunction = self.hwid.check_hwid(hwid_id)
	def email_save_file(self):
		self.fileSavePath, typeFile = QtWidgets.QFileDialog.getSaveFileName(self, "Select files to Save!", self.lastFilePath);
		print(self.fileSavePath)
		self.savefilelineEdit.setText(self.fileSavePath)
		self.save_file = open(self.fileSavePath, 'a')

	def email_select_file(self):

		self.fileForumPath, type_file = QtWidgets.QFileDialog.getOpenFileName(self, "Select files to Check Account!",
															   self.lastFilePath);
		print(self.fileForumPath)
		self.listchecklineEdit.setText(self.fileForumPath)

	def startCheck(self):

		print('==startCheck==')
		global orderfunction
		if not orderfunction:
			QtWidgets.QMessageBox.about(self, "Error", "Contact Dev for approval")
			self.validTextEdit.setPlainText(hwid.Hwid().get_hwid())
			return
		self.statustheard = None
		self.statusqueue = queue.Queue()

		self.validTextEdit.setPlainText('')
		socklist = self.socksTextEdit.toPlainText()
		check_site = self.checksitecomboBox.currentText()
		checkAmazon = self.checkBoxAmazon.isChecked()
		checkEbay = self.checkBoxEbay.isChecked()
		print(check_site,checkAmazon)
		# self.header = unicode(self.headercomboBox.currentText()).encode('utf-8');
		sock_type = self.socktypecomboBox.currentText()
		ssh_database = self.comboBoxcheck_ssh_database.currentText()
		soluongvalid = self.validlineEdit.text()
		theard = self.lineEdittheard.text()
		extraoption = self.extraoptionlineEdit.text()

		# if check_site.find('Register Paypal') != -1:
		#     self.fileForumPath = ''
		# print(self.statusLabel,self.fileForumPath,)
		if not self.fileForumPath:
			QtWidgets.QMessageBox.about(self, "Error", "Input List for checking")
			return
		self.checkThread = CheckThread(self.statusLabel, self.fileForumPath, socklist, check_site,
									   self.socksTextEdit, soluongvalid, theard, usesocks=str(sock_type),
									   dontsupporttextEdit=self.dontsupporttextEdit, validTextEdit=self.validTextEdit,
									   save_file=self.save_file, ssh_database=str(ssh_database),
									   statusqueue=self.statusqueue, extraoption=str(extraoption))


		self.checkThread.start()
		if not self.statustheard:
			self.statustheard = Update_status_worker(self.statusqueue)
			self.statustheard.trigger.connect(self.update_status)
			self.statustheard.start()

	def Stoptheard(self):
		# Tried the following, also one by one and altogether:
		global stoped
		stoped = 'stop'
		self.statusLabel.setText('Stoped');

		# Again, none work

	def update_status(self, tag, data):
		if tag == 'check_done':
			if data.find('check die') == -1:
				self.validTextEdit.setPlainText(self.validTextEdit.toPlainText() + '\n' + data)
				if self.save_file:
					self.save_file.write(data + '\n')
					self.save_file.flush()
		elif tag == 'update_status':
			# data = unicode(data).encode('utf-8')
			self.statusLabel.setText(data)
		elif tag == 'uncheck':
			self.dontsupporttextEdit.setPlainText(self.dontsupporttextEdit.toPlainText() + '\n' + data);
		elif tag == 'het_socks':
			self.socksTextEdit.setPlainText('')

class Update_status_worker(QtCore.QThread):
	trigger = pyqtSignal(str, str)

	def __init__(self, statusqueue):
		QtCore.QThread.__init__(self)
		self.statusqueue = statusqueue

	def run(self):
		while 1:
			tag, status_recive = self.statusqueue.get()
			try:
				self.trigger.emit(tag, status_recive);
			except Exception as e:
				print(e)

			# time.sleep(0.1)

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
		uic.loadUi(appFolderPath + '/ui/ssh.ui', self)
		# self.Ui_sshForm = Ui_sshForm()
		# self.Ui_sshForm.setupUi(self)
		# uic.loadUi(appFolderPath+'/ui/ssh.ui',self);
		# connect

		self.cbselectssh.activated.connect(self.show_ssh_combox_list)
		self.btnsshsetup.clicked.connect(self.ssh_setup)
		self.btnstopallssh.clicked.connect(self.stopallssh)
		self.btnfind.clicked.connect(self.find)
		self.btreload.clicked.connect(self.show_ssh_combox_list)
		self.btnsavessh.clicked.connect(self.save_ssh)
		# self.Ui_sshForm.sshtableWidget.cellDoubleClicked.connect(self.run_ssh_auto_port)
		# setup table
		self.sshtableWidget.verticalHeader().setVisible(False)
		self.sshtableWidget.setSortingEnabled(True)
		self.sshtableWidget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
		# show
		self.createActions()
		self.show();
		# variable

		##ssh setup
		if not os.path.isdir(appFolderPath + '/ssh/'):
			os.makedirs(appFolderPath + '/ssh/')
		listdircatalog = os.listdir(appFolderPath + '/ssh/')
		added = 0
		i = 0
		while i < len(listdircatalog):
			linecatalog = listdircatalog[i]
			if not os.path.isdir(appFolderPath + '/ssh/' + linecatalog) and linecatalog.find('.db') != -1:
				added += 1
				# if added == 1:
				# self.Ui_sshForm.cbselectssh.setItemText(0,QtCore.QString(linecatalog))
				# else:
				#	print i
				self.cbselectssh.addItem(linecatalog)
			i += 1
		# menu
		self.menu = QtWidgets.QMenu(self)
		global local_port_list
		local_port_list = []

	# load ssh list
	# self.show_ssh_combox_list()
	# self.connect( sshtheard, QtCore.SIGNAL("update(QString,QString)"), self.threadUpdate );
	def save_ssh(self):
		cbcatalog_text = self.cbselectssh.currentText()
		if cbcatalog_text.find('.db') != -1:
			self.save_to_database(database=cbcatalog_text)

	def save_to_database(self, database=''):
		rows = self.sshtableWidget.rowCount()
		con = lite.connect(appFolderPath + '/ssh/' + database)
		if rows:
			with con:
				con.row_factory = lite.Row
				cur = con.cursor()
				r = 0
				while r < rows:
					id = self.sshtableWidget.item(r, 0).text()
					city = self.sshtableWidget.item(r, 2).text()
					state = self.sshtableWidget.item(r, 3).text()
					country = self.sshtableWidget.item(r, 4).text()
					ssh_note = self.sshtableWidget.item(r, 7).text()
					ssh_blacklist = self.sshtableWidget.item(r, 8).text()
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
		rows = self.sshtableWidget.rowCount()
		row = 0
		while row < rows:
			port = None
			try:
				port = self.sshtableWidget.item(row, 6).text()
			except:
				pass
			if port:
				self.sshtableWidget.setItem(row, 5, QtWidgets.QTableWidgetItem(''))
				self.sshtableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem('Stoped'))
			row += 1
		global local_port_list
		local_port_list = []

	def find(self):
		self.sshtableWidget.setRowCount(0)

		findText = self.cbfind.currentText()

		if findText:
			cbcatalog_text = self.cbselectssh.currentText()
			con = lite.connect(appFolderPath + '/ssh/' + cbcatalog_text)
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
		self.sshtableWidget.setRowCount(0)
		for row_db in rows:
			row = self.sshtableWidget.rowCount()
			self.sshtableWidget.insertRow(row)
			ip = str(row_db["ip"])
			ip_infodecrypt = str(ip)
			self.sshtableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(str(row_db["id"])))
			self.sshtableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(ip_infodecrypt))
			self.sshtableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(row_db["city"]))
			self.sshtableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(row_db["state"]))
			self.sshtableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(row_db["country"]))
			self.sshtableWidget.setItem(row, 7, QtWidgets.QTableWidgetItem(row_db["ssh_note"]))
			self.sshtableWidget.setItem(row, 8, QtWidgets.QTableWidgetItem(row_db["ssh_blacklist"]))
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
		rows = self.sshtableWidget.selectionModel().selectedRows()
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

		id = self.sshtableWidget.item(row, 0).text()
		cbcatalog_text = str(self.cbselectssh.currentText())
		if cbcatalog_text.find('.db') != -1:
			con_bill = lite.connect(appFolderPath + '/ssh/' + cbcatalog_text)
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
									  password=password, sshtablewidget=self.sshtableWidget, row=row)
				self.sshtheard.trigger.connect(self.update_status)
				self.sshtheard.start()

	def run_ssh_auto_port(self):
		## run order theard
		rows = self.sshtableWidget.selectionModel().selectedRows()
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
			pass
		else:
			return True

	def stopselectrowssh(self):
		rows = self.sshtableWidget.selectionModel().selectedRows()
		for r in rows:
			row = r.row()
			port = self.sshtableWidget.item(row, 5).text()
			# wait and terminate all child process
			for p in multiprocessing.active_children():
				# print p.name
				# print ip+port
				if p.name.find('ssh:127.0.0.1:' + port) != -1:
					p.terminate();
					p.join();
					self.sshtableWidget.setItem(row, 5, QtWidgets.QTableWidgetItem(''))
					self.sshtableWidget.setItem(row, 6, QtWidgets.QTableWidgetItem('Stoped'))
					local_port_list.remove(int(port))
					print ('stoped: ' + 'ssh:127.0.0.1:' + port)

	def removeselectrowssh(self):
		rows = self.sshtableWidget.selectionModel().selectedRows()
		self.removerow(rows)

	def removerow(self, rows):
		cbcatalog_text = str(self.cbselectssh.currentText())

		con = lite.connect(appFolderPath + '/ssh/' + cbcatalog_text)
		with con:
			con.row_factory = lite.Row
			cur = con.cursor()
			i = 0
			while i < len(rows):
				r = rows[i].row()
				info_id = self.sshtableWidget.item(r, 0).text()
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
		self.sshtableWidget.setRowCount(0)
		cbcatalog_text = self.cbselectssh.currentText()
		if cbcatalog_text.find('.db') != -1:
			con_bill = lite.connect(appFolderPath + '/ssh/' + cbcatalog_text)
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
		row = self.sshtableWidget.rowCount()
		self.sshtableWidget.insertRow(row)
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
		self.sshtableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(str(line_row["id"]).strip()))
		self.sshtableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(ip_infodecrypt.strip()))
		self.sshtableWidget.setItem(row, 2, QtWidgets.QTableWidgetItem(str(line_row["city"]).strip()))
		self.sshtableWidget.setItem(row, 3, QtWidgets.QTableWidgetItem(str(line_row["state"]).strip()))
		self.sshtableWidget.setItem(row, 4, QtWidgets.QTableWidgetItem(str(line_row["country"]).strip()))
		##
		self.sshtableWidget.setItem(row, 7, QtWidgets.QTableWidgetItem(ssh_note))
		self.sshtableWidget.setItem(row, 8, QtWidgets.QTableWidgetItem(ssh_blacklist))
		# self.Ui_sshForm.sshtableWidget.setItem(row, 9, QtGui.QTableWidgetItem(ssh_false))

	def update_status(self, tag, data):
		if tag == 'check_done':
			if data.find('check die') == -1:
				self.validTextEdit.setPlainText(self.validTextEdit.toPlainText() + '\n' + data)
				if self.save_file:
					self.save_file.write(data + '\n')
					self.save_file.flush()
		elif tag == 'update_status':
			# data = unicode(data).encode('utf-8')
			self.statusLabel.setText(data)
		elif tag == 'uncheck':
			self.dontsupporttextEdit.setPlainText(self.dontsupporttextEdit.toPlainText() + '\n' + data);
		elif tag == 'het_socks':
			self.socksTextEdit.setPlainText('')

#############################billing and shipping manager
class SSHsetup(QtWidgets.QDialog):
	def __init__(self, parent=None):
		QtWidgets.QDialog.__init__(self, parent)
		self.main = parent
		uic.loadUi(appFolderPath + '/ui/sshsetup.ui', self)
		# self.Ui_Dialogssh = Ui_Dialogssh()
		# self.Ui_Dialogssh.setupUi(self)
		self.btnokssh.clicked.connect(self.add_ssh)
		self.btncancelssh.clicked.connect(self.cancel)

		if not os.path.isdir(appFolderPath + '/ssh/'):
			os.makedirs(appFolderPath + '/ssh/')

		listdircatalog = os.listdir(appFolderPath + '/ssh/')
		for linecatalog in listdircatalog:
			if not os.path.isdir(appFolderPath + '/shipping/' + linecatalog) and linecatalog.find('.db') != -1:
				self.cbsshdatabase.addItem(linecatalog)

	def cancel(self):
		self.close()

	def add_ssh(self):
		# Brent|Bohan|1530 15th Ave #503||Seattle|WA|98122|4449060000591979|10|2015|
		ssh_plain_text = self.plainTextEditssh.toPlainText()
		comboBoxcatalogue = self.cbsshdatabase.currentText()

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
							self.plainTextEditsshfailed.setPlainText(
								self.plainTextEditsshfailed.toPlainText() + '\n' +
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
			reader = geoip2.database.Reader(appFolderPath + '/ssh/GeoLite2-City.mmdb')
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

				self.main.cbsshdatabase.addItem(QtCore.QString(comboBoxcatalogue))
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



def main():
	# get appFolderPath
	global appFolderPath
	try:
		import ctypes
		myappid = 'Meomun.Automator'  # arbitrary string
		ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
	except:
		pass
	try:
		appFolderPath, os.path.dirname(os.path.realpath(__file__));
	except Exception as e:
		appFolderPath = os.getcwd();  # for window build

	print('appFolderPath',appFolderPath)
	print('path',os.path.dirname(sys.executable))
	# load config
	# global config;
	# config = Config(appFolderPath);

	app = QtWidgets.QApplication(sys.argv)
	app.setWindowIcon(QtGui.QIcon(appFolderPath + '/icon.jpg'))
	# add freeze support

	ex = MainWindow()
	result = app.exec_()

	# wait and terminate all child process
	print('kill process')
	for p in multiprocessing.active_children():
		p.terminate()
		p.join()
	sys.exit(result)
	print('done')


if __name__ == '__main__':
	multiprocessing.freeze_support()
	main()

