import asyncio, pproxy, multiprocessing, socket, random, mybrowser, os, time, signal, re
from datetime import datetime
import stem.process
from stem.control import Controller
from stem import Signal
import stem.descriptor.remote
from stem import CircStatus

class MunProxy:

    def __init__(self):
        self.list_stop = []

    def stop(self, process_name):  # tat' sock
        print('active_children',multiprocessing.active_children())
        for p in multiprocessing.active_children():
            print('===name===',p.name)
            if p.name == process_name:
                print ("Shutdown process name=" + process_name);
                p.terminate();
                p.join();
                break
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
        
    def replaySock(self, proxy_type=None,proxy_ip=None, proxy_port=None,local_port=None, proxy_username=None, proxy_password=None, queue=None):
        server = pproxy.Server('socks5://0.0.0.0:%s' % ( local_port))
        if proxy_username and proxy_password:
            print('%s://%s:%s#%s:%s' % ( proxy_type, proxy_ip, proxy_port, proxy_username, proxy_password ))
            remote = pproxy.Connection('%s://%s:%s#%s:%s' % ( proxy_type, proxy_ip, proxy_port, proxy_username, proxy_password ))
        else:
            remote = pproxy.Connection('%s://%s:%s' % ( proxy_type, proxy_ip, proxy_port ))
        args = dict( rserver = [remote],
                    verbose = print )
        loop = asyncio.get_event_loop()
        handler = loop.run_until_complete(server.start_server(args))
        if queue:
            queue.put(os.getpid())
        try:
            loop.run_forever()
        except KeyboardInterrupt:
            print('exit!')

        handler.close()
        loop.run_until_complete(handler.wait_closed())
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()
        print('===done')
           
    def forward(self, proxy_type=None,proxy_ip=None, proxy_port=None, local_port=None, proxy_username=None, proxy_password=None):
        THIS_FOLDER = os.getcwd();
        self.queue = multiprocessing.Queue()
        if not local_port:
            local_port = self.get_local_port()
            
        p = multiprocessing.Process(name='replaySock:127.0.0.1:' + str(local_port), target=self.replaySock,
                                    args=(proxy_type,proxy_ip, proxy_port,local_port, proxy_username, proxy_password, self.queue));
        p.start();
        print('==multiprocessing==',p.name)
        self.pid = None
        while not self.pid:
            try:
                self.pid = self.queue.get()
            except:
                pass
            time.sleep(0.1)
        # check_socks = self.fake_socks('127.0.0.1:' + str(local_port))
        # print(check_socks)
        if self.pid:
            processing_pid_path = os.path.join(THIS_FOLDER, 'processing_pid.txt')
            with open(processing_pid_path, 'a+') as f:
                f.write(str(self.pid)+'\r\n')
            return ('127.0.0.1:'+ str(local_port),self.pid)
        else:
            p.terminate()
            p.join()
            try:
                os.kill(int(self.pid),signal.SIGILL)
            except:
                pass
            return
        
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
 
    def switch_tor_ip(self, port):
        with Controller.from_port(port=int(port)) as controller:
            controller.authenticate()
            controller.signal(Signal.NEWNYM)
        return True
    def quit_tor(self, port):
        with Controller.from_port(port=int(port)) as controller:
            controller.authenticate()
            controller.signal(Signal.TERM)
        return True
    
    def stop(self,tor_process):
        tor_process.kill()
        
    def stop_all(self):
        print("Killing all current Tor instances...")
        os.system("taskkill.exe /im tor.exe /F")
        os.system("cls")
        print("Killing all current Tor instances...")
        print("Starting first instance and replicating cache...")
        
    def get_random_path(self):
        random_path = str(random.randint(0, 9999))
        while os.path.exists(os.getcwd()+"/MunProxies/data/"+random_path):
            random_path = str(random.randint(0, 9999))
            time.sleep(0.5)
        return random_path        
            
        
        
    def create_proxy(self, ExitNodes, SOCKS_PORT=None, CONTROL_PORT=None, Rotating_time=30, Rotating=True, DataDirectory=None, Bridge_String=''):
        if not SOCKS_PORT:
            SOCKS_PORT = self.get_local_port()
        if not CONTROL_PORT:
            CONTROL_PORT = self.get_local_port()
        TOR_PATH = os.path.normpath(os.getcwd()+"/MunProxies/tor/tor.exe")
        if not DataDirectory:
            DataDirectory = self.get_random_path()
        DATA_DIR = os.path.normpath(os.getcwd()+"/MunProxies/data/"+DataDirectory) 
        GEOIPFILE_PATH = os.path.normpath(os.getcwd()+"/MunProxies/data/geo/geoip")
        GEOIP6FILE_PATH = os.path.normpath(os.getcwd()+"/MunProxies/data/geo/geoip6")
        obfs4_PATH = os.path.normpath(os.getcwd()+"/MunProxies/tor/PluggableTransports/obfs4proxy.exe")
        import urllib
        try:
            urllib.request.urlretrieve('https://raw.githubusercontent.com/torproject/tor/main/src/config/geoip', GEOIPFILE_PATH)
        except:
            print ('[INFO] Unable to update geoip file. Using local copy.')
        tor_config = {
                'SocksPort' : str(SOCKS_PORT),
                'ControlPort': str(CONTROL_PORT),
                'DataDirectory': DATA_DIR,
                'GeoIPFile': GEOIPFILE_PATH,
                'GeoIPv6File': GEOIP6FILE_PATH,
                # 'EntryNodes' : '{VN}',
                'ExitNodes' : '{'+ExitNodes+'}',
                'StrictNodes' : '1',
                'CookieAuthentication' : '1',                
            }
        if Rotating:
            tor_config['MaxCircuitDirtiness']= str(Rotating_time)
        if Bridge_String:
            tor_config['ClientTransportPlugin'] = 'obfs2,obfs3,obfs4,scramblesuit exec '+obfs4_PATH
            tor_config['Bridge'] = Bridge_String
            tor_config['UseBridges'] = '1'
            
        self.tor_process = stem.process.launch_tor_with_config(
        config = tor_config,
        init_msg_handler = lambda line: print(line) if re.search('Bootstrapped', line) else False,
        tor_cmd = TOR_PATH
        )
        return (SOCKS_PORT, CONTROL_PORT, self.tor_process)   
def main():
    print('===Replay Proxy==')
    #bietdeobao_wXcTg:nLyIdPKHeI_country-us@185.193.157.60:12325
    'dtdkvn.custom1:3f36dd1ca0@207.225.26.244:9093'
    munproxy = MunProxy()
    Bridge_String='''obfs4 14.71.66.213:9292 CC7A95E4131BD45DE85838CA8F5D4D96EEB42123 cert=OfZfnOxPT2TMSRsQjEq9/siGJodvgK3qIt3T8xyEL4vRHHZAlQImq8EiZKZoUMaGOS4EDw iat-mode=0
obfs4 206.196.145.143:9451 F89620802CE58C9DB19E27E5F8F502C5B462005C cert=25mzOx3wrJxmtE4T6D2Emp2uKG0U6EHIIHtW8eWANnf/Uq52LKw5OUUjkAp3jtTotiZnGw iat-mode=0
obfs4 66.181.41.122:8042 96801CA6673693F43D1DAF4B15DDA81E0E1A36E2 cert=P8CAMmYxUBmPEVca6iqzC0PtQss9JpHFbdlneHPlpGXm9DNjC1RJ8PEHBL5t4L5eN0LdeA iat-mode=0'''
    munproxy.forward('http+http+ssl','66.42.99.181',10000, 1234, 'usrLTeXO','passWwDGw')
    # munproxy.create_proxy('US', SOCKS_PORT='1234',DataDirectory=1, Bridge_String='obfs4 14.71.66.213:9292 CC7A95E4131BD45DE85838CA8F5D4D96EEB42123 cert=OfZfnOxPT2TMSRsQjEq9/siGJodvgK3qIt3T8xyEL4vRHHZAlQImq8EiZKZoUMaGOS4EDw iat-mode=0')
    # munproxy.create_proxy('US', SOCKS_PORT='12345',DataDirectory=2, Bridge_String='obfs4 144.91.120.156:57983 B46763883D90989228CCA988A5392E11FAFF3AED cert=V7vS/uc9eRcu9TX2Guhckp8B2bHwYMOyciFCzucKbVXNO7ufEtIGm4aPiCd1nTdDZcoKUQ iat-mode=0')
if __name__ == '__main__':
	multiprocessing.freeze_support()
	main()