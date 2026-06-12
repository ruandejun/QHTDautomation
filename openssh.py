#!/usr/bin/python
# -*- coding: utf-8 -*-
# -*- coding: latin-1 -*-
from aescipher import AESCipher
import sqlite3 as lite
import mybrowser, time, random
import socks;
import socket;
import os, queue, multiprocessing;
import sshsocks_manager
import signal,threading
# from PyQt4 import QtCore
#############################Check Site

class Getsshandproxy(threading.Thread):
    def __init__(self, ssh_database='', ssh_okq=None, get_proxy=False, get_ssh=False, total_ssh_get=10,proxy_queue=None,check_site=''):
        super(Getsshandproxy, self).__init__()
        self.ssh_database = ssh_database

        self.proxy_queue = proxy_queue
        self.get_proxy = get_proxy
        self.get_ssh = get_ssh
        self.sshthread = []
        self.total_ssh_get = total_ssh_get
        if not self.total_ssh_get:
            self.total_ssh_get = 10
        # print self.total_ssh_get
        # global aes_cipher
        self.aes_cipher = AESCipher('stay123!@#')

        try:
            currentRunningScriptPath = os.path.realpath(__file__)
            self.appFolderPath, scriptName = os.path.split(currentRunningScriptPath);
        except Exception as e:
            self.appFolderPath = os.getcwd();  # for window build

        # queue list good ssh
        if str(check_site).find('http') == -1:

            if str(check_site).find('CCN Gate 1') != -1:
                self.check_site = 'https://www.bigfishgames.com/'
            elif len(check_site) >=3:
                self.check_site = 'http://'+str(check_site)+'.com'
            else:
                self.check_site = 'https://google.com'
        else:
            self.check_site = check_site
        
        
        self.ssh_okq = ssh_okq

        # bad ssh queue
        self.ssh_nonok = queue.Queue()

        self.ssh_running = []

        self.list_ssh_vaid = []

        self.stop = False

    def get_local_port(self):
        reuse_port = False
        local_port = None
        while not reuse_port:
            local_port = random.randint(2000, 50000)
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
            pass
        else:
            return True

    def stop_ssh(self, name=''):
        socks.setdefaultproxy()
        socket.socket = socks.socksocket
        print ('trying stop:' + name)
        for p in multiprocessing.active_children():
            if p.name.find(name) != -1:
                print ('Stoped SSH:' + name)
                p.terminate();
                p.join();

    def get_list_ssh_form_database(self):

        con = lite.connect(self.appFolderPath + '/ssh/' + self.ssh_database)
        with con:
            con.row_factory = lite.Row
            cur = con.cursor()
            cur.execute("SELECT * FROM ssh_info")
            rows = cur.fetchall()

        con.close()
        random.shuffle(rows)
        return rows

    def stop_all_thread(self, total_stop):
        self.sshq.empty()
        for th in self.sshthread:
            th.terminate()
            th.exit()
            th.quit()
        i = 0
        while i < total_stop*2:
            self.sshq.put('stop')
            i += 1

    def run(self):
        if int(self.total_ssh_get) > 50:
            get_ssh_worker = 50
        else:
            get_ssh_worker = int(self.total_ssh_get)
        # ssh queue for check
        self.sshq = queue.Queue()
        list_proxy_good=[]
        dict_thearding_run = {}
        while len(self.ssh_running) < int(self.total_ssh_get) and len(list_proxy_good) < int(self.total_ssh_get):
            print ('========get ssh========')
            if self.stop:
                print ('Getsshandproxy Stopped')
                break
            # if self.get_proxy:
            #     proxy = getproxy.Getproxy()
            #     self.list_proxy_check = proxy.get_proxy(proxy_queue=self.proxy_queue)
            #     list_proxy_good.extend(self.list_proxy_check)
            if self.get_ssh:
                list_ssh = self.get_list_ssh_form_database()
                i = 0
                while i < len(list_ssh) and len(self.ssh_running) < int(self.total_ssh_get):

                    if self.stop:
                        print ('check ssh Stopped')
                        break

                    if len(self.sshthread) < get_ssh_worker:

                        a = 0
                        while a < get_ssh_worker:
                            ssh_th = SSHThread(self.sshq, self.ssh_okq, self.ssh_nonok, self.ssh_running,check_site=self.check_site,last_time_running=time.time(),ssh_database=self.ssh_database,list_ssh_vaid=self.list_ssh_vaid)
                            ssh_th.start()
                            self.sshthread.append(ssh_th)
                            a += 1

                    if len(self.list_ssh_vaid) < 100 or self.sshq.qsize() < 100:
                        # print 'SSH runing:=====' + str(len(self.ssh_running)) + '===' + str(self.total_ssh_get),len(multiprocessing.active_children())
                        row_db = list_ssh[i]
                        ip = str(row_db["ip"])
                        username = row_db["username"]
                        password = row_db["password"]
                        ip_infodecrypt = str(ip)
                        # print('username',username)
                        username_infodecrypt = self.aes_cipher.decrypt(username)
                        password_infodecrypt = self.aes_cipher.decrypt(password)
                        # print('username_infodecrypt',username_infodecrypt,password_infodecrypt)
                        # local_port = self.get_local_port()
                        self.sshq.put_nowait((ip_infodecrypt, username_infodecrypt, password_infodecrypt))
                        i += 1

                    time.sleep(0.05)
            time.sleep(1);
            # stop all worker
        print ('===stop all ssh===')
        self.stop_all_thread(get_ssh_worker)
        return

#############################SSH
class SSHThread(threading.Thread):
    def __init__(self, sshq, ssh_okq, ssh_nonok, ssh_running,check_site='',last_time_running=0,ssh_database='',list_ssh_vaid=[]):
        # super(SSHThread,self).__init__(name_theard)
        super(SSHThread, self).__init__()
        # int queue

        self.ssh_database = ssh_database
        self.last_time_running = last_time_running
        self.sshq = sshq
        self.ssh_okq = ssh_okq
        self.ssh_nonok = ssh_nonok
        self.ssh_running = ssh_running
        self.check_site = check_site
        self.list_ssh_vaid = list_ssh_vaid
        # self.aes_cipher = AESCipher('stay123!@#')
    def remove_ssh_from_database(self,ip):
        try:
            currentRunningScriptPath = os.path.realpath(__file__)
            self.appFolderPath, scriptName = os.path.split(currentRunningScriptPath);
        except Exception as e:
            self.appFolderPath = os.getcwd();  # for window build
        con = lite.connect(self.appFolderPath + '/ssh/' + self.ssh_database)
        with con:
            con.row_factory = lite.Row
            cur = con.cursor()
            cur.execute("DELETE FROM ssh_info WHERE ip='%s'" % (ip))
            con.commit()

        con.close()
        print ('Removed ip:'+ip)
        return
    def run(self):
        # self.update_ssh_status('Opening')
        print('==SSHThread==',self.sshq.qsize())
        while 1:
            try:
                ssh_get = self.sshq.get_nowait()
                if ssh_get == 'stop':
                    print ('stopped')
                    return

                ip, username, password = ssh_get
                print('ip===',ip,username,password)
                self.last_time_running = time.time()

                sshmanager = sshsocks_manager.SshSockManager()
                checklogin = sshmanager.check_ssh(str(ip), 22, str(username), str(password))
                # print checklogin
                if checklogin.find('check die') == -1:
                    self.list_ssh_vaid.append((str(ip), 22, str(username), str(password)))
                print ('========running==========',str(ip))
                if len(multiprocessing.active_children()) <= 50:
                    # print '==========open socks=============='
                    try:
                        domain_valid, port_valid,username_valid,password_valid = self.list_ssh_vaid.pop(0)
                    except:
                        continue
                    local_port = sshmanager.get_local_port()
                    sshopen_socks = sshmanager.ssh_open_port(domain_valid, port_valid,username_valid,password_valid,local_port,check_site=self.check_site)
                    if sshopen_socks.find('check die') == -1:
                        self.ssh_running.append(local_port)
                        pid = sshopen_socks.split('|')[1]
                        self.ssh_okq.put_nowait(('127.0.0.1:'+str(local_port), pid))
                    else:
                        print ('==========Error:' + sshopen_socks)
                        # if sshopen_socks.find('Cant Login To Your SSH') != -1:
                        #     self.remove_ssh_from_database(ip)
                        for p in multiprocessing.active_children():
                            if p.name.find(str(ip) ) != -1:
                                print ('Stoped SSH:' + str(ip) + ':' + str(local_port))
                                p.terminate()
                                p.join()
                            # p.join();
                        # self.ssh_nonok.put_nowait(local_port)
                        # input to ssh list
            except Exception as e:
                print (e)
            time.sleep(0.1)

    def check_socks_and_proxy(self, sock, sock_type):
        if sock_type == 'socks':
            try:
                print (self.check_site)
                browser = mybrowser.Rqbrowser()
                browser.set_proxies(sock5=sock)
                # browser.quite = True
                r = browser.open('https://google.com', timeout=3)
                html = r.content
                if html.find('google') != -1:
                    return sock

            except:
                return

        else:
            try:
                print ('check proxy:' + sock)
                self.statusLabel.setText('check proxy:' + sock);
                proxy = urllib2.ProxyHandler({'http': sock, 'https': sock})

                opener = urllib2.build_opener(proxy)
                opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                r = opener.open('http://whoer.net/', timeout=10)
                html = r.read()
                r.close()
                opener.close()
                del opener
                return sock
            except Exception as e:
                print (e)
                self.statusLabel.setText('Proxy Died:' + sock);
                return

                #############################


if __name__ == '__main__':
    # demo bat. sock number 0 trong 60s roi` tat' roi` bat. lai. o? port moi'
    import time

    processList = []
    # manager = SSHThread('', '', '', '',ssh_database='ssh_database.db')
    # manager.remove_ssh_from_database('177.67.5.35')
    ssh_okq = queue.Queue()
    get_ssh_th = Getsshandproxy('ssh_new.db', get_ssh=True,
                                             total_ssh_get=10,
                                             ssh_okq=ssh_okq)
    get_ssh_th.start()
    # print start
    # time.sleep(3)
    # print 'stop'
    #
    # manager.stop('dien')