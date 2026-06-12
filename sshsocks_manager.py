#!/usr/bin/python2.7
# -*- coding:utf8 -*-

from SocksService import ThreadingSocksServer, SocksSSHRemoteRequestHandler, SocksRequestHandler, SocksProxy
import random, multiprocessing
import socket,time
import mybrowser
import os
import paramiko, signal, threading


class SshSockManager:
    def __init__(self,):

        self.list_stop = []

    def openSock(self, domain, port, username, password, local_port, queue):
        server_port = local_port
        server_listen = '127.0.0.1'  # localhost;
        timeout = 5
        socket.setdefaulttimeout(timeout)

        queue.put_nowait(os.getpid())

        sshtunnel = SocksSSHRemoteRequestHandler(domain,
                                                    username,
                                                    password,
                                                    port)
        self.server = ThreadingSocksServer(( server_listen,
                                        server_port),
                                        SocksRequestHandler,
                                        sshtunnel)
        # self.server.start()
        print('==open socks done==')
        self.server.serve_forever()


    def stop(self, process_name):  # tat' sock
        print('active_children',multiprocessing.active_children())
        for p in multiprocessing.active_children():
            print('===name===',p.name)
            if p.name == process_name:
                print ("Shutdown sock5 ssh process name=" + process_name);
                p.terminate();
                p.join();
                break

    def check_ssh(self, domain, port, username, password):
        self.ssh = paramiko.SSHClient()
        ssh_policy = paramiko.WarningPolicy()
        self.ssh.set_missing_host_key_policy(ssh_policy)
        timeout = 5
        # socket.setdefaulttimeout(timeout)
        try:
            self.ssh.connect(domain,
                             port=port,
                             timeout=timeout,
                             username=username,
                             password=password)
            # self.ssh.exec_command('pwd')
        # transport = self.ssh.get_transport()
        except Exception as e:
            # print e
            return ('check die:' + domain)
        else:
            # print '=live='
            self.ssh.close()
            del self.ssh
            print ('==ssh login ok==')
            return '==ssh login ok=='

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

    def start(self, domain, username, password, port=22, check=False, local_port=None):  # bat. sock
        if not local_port:
            local_port = self.get_local_port()
        else:
            check_port = self.check_local_port(local_port)
            if not check_port:
                return 'check die:Your port:' + str(local_port) + ' already used'
        # port=int(port);
        checklogin = self.check_ssh(str(domain), int(port), str(username), str(password))
        if checklogin.find('check die') == -1:
            print('===Open socks:',local_port)
            openport = self.ssh_open_port(domain, port, username, password, local_port, check=check)
            if openport.find('check die') == -1:
                return openport
            else:
                return 'check die:' + domain + ':' + str(local_port)
        else:
            return 'check die:Cant Login To Your SSH'

    def ssh_open_port(self, domain, port, username, password, local_port, check=False,check_site='https://google.com'):
        ## use multiprocessing for acceptable for kill process
        self.queue = multiprocessing.Queue()

        p = multiprocessing.Process(name='ssh:127.0.0.1:' + str(local_port), target=self.openSock,
                                    args=(domain, port, username, password, local_port, self.queue,));
        p.start();
        print('==multiprocessing==',p.name)

        # time.sleep(0.5)
        try:
            self.pid = self.queue.get()
        except:
            p.terminate()
            p.join()
            return 'check die:socks die'
        # os.kill(self.pid,signal.SIGILL)
        # if check:
        check_socks = self.fake_socks('127.0.0.1:' + str(local_port),check_site=check_site)
        if check:
            p.terminate()
            p.join()
            try:
                os.kill(int(self.pid),signal.SIGILL)
            except:
                pass
        if check_socks:
            print ("Open sock5 ssh process name=%s through ip: %s at local port: %s" % (
                domain + ':' + str(local_port), domain, local_port));
            return domain + ':' + str(local_port) + '|' + str(self.pid)
        else:
            p.terminate()
            p.join()
            try:
                os.kill(int(self.pid),signal.SIGILL)
            except:
                pass
            return 'check die:socks die'


    def restart(self, process_name):
        self.stop(process_name);
        self.start(process_name);


    def fake_socks(self, sock,check_site='https://google.com'):
        print('==fake socks=='+sock)
        # socks.setdefaultproxy()
        # socket.socket = socks.socksocket


        browser = mybrowser.Rqbrowser()
        browser.set_proxies(sock5=sock)
        # browser.quite = True
        try:
            r = browser.open(check_site, timeout=15)
            html = r.text
        except:
            return
        # print(html)
        if html.find('<html') != -1:
            return sock
        else:
            return





if __name__ == '__main__':
    # demo bat. sock number 0 trong 60s roi` tat' roi` bat. lai. o? port moi'
    import time

    processList = []
    manager = SshSockManager()
    # start = manager.check_ssh('149.28.164.116',22, 'root', '3aQ+N)m1bcw3Ttwz')
    start = manager.ssh_open_port('149.28.164.116',22, 'root', '3aQ+N)m1bcw3Ttwz',local_port=9000)
    print(start)
    time.sleep(3)
    print('==stop==')
    
    # manager.stop('ssh:127.0.0.1:9000')
