#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import urllib2, urllib;
import re, random;
import sys, datetime, time;
import ClientForm;
import socks;
import socket;
import StringIO;
import HTMLParser;
import threading;
from BeautifulSoup import BeautifulSoup, SoupStrainer;


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


class Getproxy:
    """ Test reg forum
    """

    def __init__(self, emit='', qtcode='', header='', orderfinalForm=[], updatestatus='update'):
        # import urllib2
        self.updatestatus = updatestatus
        self.browser = urllib2.build_opener()
        self.browser.addheaders = [('User-agent', 'Mozilla/5.0')]
        # ua.set_debug_responses(False)
        self.emit = emit;
        self.qtcode = qtcode;

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
        if self.updatestatus.find('ircbot') == -1:
            try:
                self.emit(self.qtcode.SIGNAL(self.updatestatus + '(QString,QString)'), "updatestatus", str(status))
            except:
                pass
        else:
            to_user = self.updatestatus.split('|')[1].strip()
            print (to_user)
            self.send_message(status, to_user=to_user)

    def add_header(self, link_refer, XMLHttpRequest=None):
        if XMLHttpRequest:
            tt = [('User-Agent', self.header),
                  ('Connection', 'keep-alive'),
                  ('Accept-Language', 'en-US,en;q=0.5 | en-US'),
                  ('Host', 'www.macys.com'),
                  ('Origin', 'https://www.macys.com'),
                  ('Cache-Control', 'max-age=0'),
                  ('Referer', link_refer),
                  ('X-Requested-With', 'XMLHttpRequest'),
                  ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.5,image/webp,*/*;q=0.5')];

        else:
            tt = [('User-Agent', self.header),
                  ('Connection', 'keep-alive'),
                  ('Accept-Language', 'en-US,en;q=0.5 | en-US'),
                  ('Host', 'www.macys.com'),
                  ('Origin', 'https://www.macys.com'),
                  ('Cache-Control', 'max-age=0'),
                  ('Referer', link_refer),
                  ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.5,image/webp,*/*;q=0.5')];
            # ('X-Requested-With','XMLHttpRequest')
            # add header
            # print tt
        self.browser.addheaders = tt;

    def fixHTML(self, html):
        return html.replace("'", '"');

    def selectForm(self, html, linkget):
        try:
            forms_filter = SoupStrainer('form');
            soup = BeautifulSoup(html, parseOnlyThese=forms_filter);
            forms_post = ClientForm.ParseFile(StringIO.StringIO(soup.prettify()), linkget, backwards_compat=False);
            # print forms_post
        except:
            forms_post = self.browser.forms()
        return forms_post

    def nordvpn_req(self):
        ''' Make the request to checkerproxy and create a master list from that site '''
        try:
            url = 'https://nordvpn.com/free-proxy-list/?country=&ports=&by=c&order=ASC&perpage=500'
            r = self.browser.open(url, timeout=30)
            html = r.read()
        except Exception:
            print('[!] Failed to get reply from %s' % url)
            checkerproxy_list = []
            return checkerproxy_list
        c = open('dien.html', 'w')
        c.write(html)
        nordvpn_list = self.parse_nordvpn(html)
        return nordvpn_list

    def parse_nordvpn(self, html):
        ''' Parse out list of IP:port strings from the html '''
        # \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}  -  matches IP addresses
        # </a></td><td>  -  is in between the IP and the port
        # .*?<  -  match all text (.) for as many characters as possible (*) but don't be greedy (?) and stop at the next greater than (<)
        raw_ips = re.findall('<th>\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}</th>\s*\d{2,5}</th>', html, re.DOTALL)
        ips = []
        print (raw_ips)
        for ip in raw_ips:
            print (ip)
            ips.append(ip)
        return ips

    def checkerproxy_req(self):
        ''' Make the request to checkerproxy and create a master list from that site '''

        try:
            url = 'https://checkerproxy.net/'
            r = self.browser.open(url, timeout=30)
            html = r.read()
        except Exception:
            print ('[!] Failed to get reply from %s' % url)
            checkerproxy_list = []
            return checkerproxy_list
        list_checked_proxy = re.findall('Proxies archive</p><ul><li><a href="(.+?)">',html)
        checkerproxy_list = []
        for line_checkedproxy in list_checked_proxy:
            try:
                url = 'https://checkerproxy.net'+line_checkedproxy
                print (url)
                r = self.browser.open(url, timeout=30)
                html = r.read()
            except Exception:
                pass
            else:
                proxy_list = self.parse_checkerproxy(html)
                checkerproxy_list.extend(proxy_list)
        return checkerproxy_list

    def parse_checkerproxy(self, html):
        ''' Only get elite proxies from checkerproxy '''
        ips = []
        raw_ips = re.findall('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}', html)
        ips = []
        for ip in raw_ips:
            # print ip
            # ip = ip.replace('</a></td><td>', ':')
            # ip = ip.strip('<')
            ips.append(ip)
        return ips

    def letushide_req(self):
        ''' Make the request to the proxy site and create a master list from that site '''
        letushide_ips = []
        for i in xrange(1, 20):  # can search maximum of 20 pages
            try:
                url = 'http://letushide.com/filter/http,hap,all/%s/list_of_free_HTTP_High_Anonymity_proxy_servers' % str(
                    i)
                r = self.browser.open(url, timeout=30)
                html = r.read()
                ips = self.parse_letushide(html)

                # Check html for a link to the next page
                if '/filter/http,hap,all/%s/list_of_free_HTTP_High_Anonymity_proxy_servers' % str(i + 1) in html:
                    pass
                else:
                    letushide_ips.append(ips)
                    break
                letushide_ips.append(ips)
            except:
                print ('[!] Failed get reply from %s' % url)
                break

        # Flatten list of lists (1 list containing 1 list of ips for each page)
        letushide_list = [item for sublist in letushide_ips for item in sublist]
        return letushide_list

    def parse_letushide(self, html):
        ''' Parse out list of IP:port strings from the html '''
        # \d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}  -  matches IP addresses
        # </a></td><td>  -  is in between the IP and the port
        # .*?<  -  match all text (.) for as many characters as possible (*) but don't be greedy (?) and stop at the next greater than (<)
        raw_ips = re.findall('\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}</a></td><td>.*?<', html)
        ips = []
        for ip in raw_ips:
            ip = ip.replace('</a></td><td>', ':')
            ip = ip.strip('<')
            ips.append(ip)
        return ips

    def freeproxylists_req(self):

        urls = [
                'http://www.freeproxylists.com/elite.html',
                'http://www.freeproxylists.com/anonymous.html']
        gatherproxy_list = []
        for url in urls:
            try:
                r = self.browser.open(url, timeout=5)
                html = r.read()
            except:
                print ('[!] Failed get reply from %s' % url)
                # gatherproxy_list = []
                return gatherproxy_list

            exp = r'''href\s*=\s*['"](?P<t>[^'"]*)/(?P<uts>\d{10})[^'"]*['"]'''
            params = re.findall(exp,html)
            for url_ex in params:
                type_proxy,id = url_ex
                url_proxy = 'http://www.freeproxylists.com/load_'+type_proxy+'_'+id+'.html'
                print (url_proxy)
                try:
                    r = self.browser.open(url_proxy, timeout=5)
                    html = r.read()
                except:
                    print ('[!] Failed get reply from %s' % url)
                    # gatherproxy_list = []
                    # return gatherproxy_list
                else:
                    # print html
                    proxy_list = self.parse_socks_proxy2(html)
                    gatherproxy_list.extend(proxy_list)

        return gatherproxy_list


    def parse_gp(self, html):
        ''' Parse the raw scraped data '''
        h = HTMLParser.HTMLParser()
        gatherproxy_list = []
        list_proxy_re = re.findall(
            "document\.write\('(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'\)</script></td>\s*<td><script>document\.write\(gp\.dep\('(.+?)'\)",
            html)
        for line_proxy in list_proxy_re:
            proxyid, proxyport = line_proxy
            d = h.unescape('&#x' + proxyport + ';')
            proxy = proxyid + ':' + str(ord(d))
            gatherproxy_list.append(proxy)

        return gatherproxy_list


    def didsoft_req(self):
        socks_proxy_chuan = []
        url='http://list.didsoft.com/get?email=ruandejun@gmail.com&pass=chtrwr&pid=http4000&showcountry=no'
        html = ''
        try:
            r = self.browser.open(url, timeout=30)
            html = r.read()
        except:
            print '[!] Failed get reply from %s' % url
            socks_proxy = []
        if html:
            socks_proxy_chuan.extend(self.parse_socks_proxy1(html))
            return socks_proxy_chuan
    def sockproxynet_req(self):
        list_site = ['http://socks-proxy.net/',
                     'http://www.us-proxy.org/',
                     'http://google-proxy.net',
                     'http://free-proxy-list.net/anonymous-proxy.html',
                     'http://free-proxy-list.net/uk-proxy.html'
                     ]
        socks_proxy_chuan = []
        for url in list_site:
            html = ''
            # print url
            try:
                r = self.browser.open(url, timeout=30)
                html = r.read()
            except:
                print '[!] Failed get reply from %s' % url
                socks_proxy = []
            if html:
                socks_proxy_chuan.extend(self.parse_socks_proxy(html))
        return socks_proxy_chuan


    def parse_socks_proxy2(self, html):
        list_ip = []
        raw_ips = re.findall('\&lt\;td\&gt\;(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\&lt\;/td\&gt\;\&lt\;td\&gt;(.*?)\&lt\;/td\&gt\;', html)
        for ip in raw_ips:
            ip_id, port = ip
            list_ip.append(ip_id + ':' + str(port))
        return list_ip
    def parse_socks_proxy1(self, html):
        list_ip = []
        raw_ips = re.findall('(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}):(\d{1,5})', html)
        for ip in raw_ips:
            ip_id, port = ip
            list_ip.append(ip_id + ':' + str(port))
        return list_ip
    def parse_socks_proxy(self, html):
        list_ip = []
        raw_ips = re.findall('<tr><td>(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})</td><td>(.*?)</td>', html)
        for ip in raw_ips:
            ip_id, port = ip
            list_ip.append(ip_id + ':' + str(port))
        return list_ip


    def check_proxy(self, line_proxy, list_proxy_good,proxy_queue):
        # timeout = 3
        # socket.setdefaulttimeout(timeout)
        # print 'check proxy '+ line_proxy
        try:
            proxy = urllib2.ProxyHandler({'http': line_proxy, 'https': line_proxy})

            opener = urllib2.build_opener(proxy)
            opener.addheaders = [('User-agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Oupeng/10.2.1.86910 Safari/534.30')]
            # opener = urllib2.install_opener(opener)
            r = opener.open('http://www.bing.com/', timeout=10)
            html = r.read()
            ips = re.search('<title>Bing</title>', html)
            if ips:
                list_proxy_good.append(line_proxy)
                if proxy_queue:
                    proxy_queue.put_nowait(line_proxy)
            r.close()
            opener.close()
            return
        except Exception as e:
            return


    def get_proxy(self,proxy_queue=None):
        list_proxy = []
        print 'trying get proxy sock site'

        # self.update_status('trying get proxy sock site')
        list_proxy_red = self.sockproxynet_req()
        list_proxy.extend(list_proxy_red)
        print 'Found ' + str(len(list_proxy_red)) + ' proxys'
        self.update_status('Found ' + str(len(list_proxy_red)) + ' proxys')
        # get checkedproxy site
        # print 'trying get proxy checkedproxy site'
        # self.update_status('trying get proxy checkedproxy site')
        # list_checkedproxy = self.checkerproxy_req()
        # list_proxy.extend(list_checkedproxy)
        # print 'Found ' + str(len(list_checkedproxy)) + ' proxys'
        # self.update_status('Found ' + str(len(list_checkedproxy)) + ' proxys')

        print 'trying get proxy gatherproxy site'
        self.update_status('trying get proxy gatherproxy site')
        list_gatherproxy = self.freeproxylists_req()
        list_proxy.extend(list_gatherproxy)
        print len(list_gatherproxy)
        print 'Found ' + str(len(list_gatherproxy)) + ' proxys'
        self.update_status('Found ' + str(len(list_gatherproxy)) + ' proxys')
        #####
        print 'trying get proxy didsoft site'
        self.update_status('trying get proxy didsoft site')
        list_didsoftproxy = self.didsoft_req()
        list_proxy.extend(list_didsoftproxy)
        print len(list_didsoftproxy)
        print 'Found ' + str(len(list_didsoftproxy)) + ' proxys'
        self.update_status('Found ' + str(len(list_didsoftproxy)) + ' proxys')
        # remove dup
        list_proxy = list(set(list_proxy))
        print 'Trying Check Proxy:' + str(len(list_proxy))
        self.update_status('Trying Check Proxy:' + str(len(list_proxy)))
        # check proxy
        self.browser.close()

        list_proxy_good = self.get_proxy_good(list_proxy,proxy_queue)
        print list_proxy_good
        print 'Got ' + str(len(list_proxy_good)) + ' good proxies'
        return list_proxy_good


    def get_proxy_good(self, list_proxy,proxy_queue):
        list_proxy_good = []
        list_theard = []
        a = 0
        while a < len(list_proxy):
            if threading.activeCount() < 101:
                time.sleep(0.01)
                t = threading.Thread(target=self.check_proxy, args=(list_proxy[a].strip(), list_proxy_good,proxy_queue,))
                t.start()
                list_theard.append(t)
                self.update_progress(a / float(len(list_proxy)))
                a += 1
        for t in list_theard:
            t.join()
        return list_proxy_good


    def update_progress(self, progress):
        barLength = 10  # Modify this to change the length of the progress bar
        status = ""
        if isinstance(progress, int):
            progress = float(progress)
        if not isinstance(progress, float):
            progress = 0
            status = "error: progress var must be float\r\n"
        if progress < 0:
            progress = 0
            status = "Halt...\r\n"
        if progress >= 1:
            progress = 1
            status = "Done...\r\n"
        block = int(round(barLength * progress))
        text = "\rPercent: [{0}] {1}% {2}".format("#" * block + "-" * (barLength - block), progress * 100, status)
        sys.stdout.write(text)
        sys.stdout.flush()


# print 'proxys live:'+str(len(list_proxy_good))


def main():

    listbilling = ''
    list_address_drop = 'Karen|Green|4962A Camp Run Road||Georgetown|OH|45121|'
    gerproxy = Getproxy(
        header='Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.131 Safari/537.36')
    gerproxy.get_proxy()


if __name__ == "__main__":
    sys.exit(main())
