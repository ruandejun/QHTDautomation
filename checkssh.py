#!/usr/bin/python
# -*- coding: utf-8 -*-   
# -*- coding: latin-1 -*-
import sys;
import socks;
import socket;
import sshsocks_manager


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


class Checkssh:
    """ Test reg forum
    """

    def __init__(self):
        pass


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



    def site_login(self, checkport=False):
        processList = []
        self.manager = sshsocks_manager.SshSockManager()
        checklogin = self.manager.check_ssh(self.domain, 22, self.username, self.password)
        # print(checklogin
        if checklogin.find('check die') == -1:
            # openport = '==ssh login ok=='
            if checkport:
                print('check ssh live')
                check_port = self.check_open_port()
                return check_port
            else:
                return self.domain + '|' + self.username + '|' + self.password
        else:
            return 'check die:login ssh incorect'

    def check_open_port(self):
        local_port = self.manager.get_local_port()
        openport = self.manager.ssh_open_port(self.domain, 22, self.username, self.password, local_port, check=True)
        if openport.find('check die') == -1:
            return self.domain + '|' + self.username + '|' + self.password
        else:
            return 'check die:Cant Use SSH for open port'

    def get_info_account(self):
        pass

    def check(self, domain='', username='', password='', checkport=False):
        self.domain = domain
        self.password = password
        self.username = username
        login = self.site_login(checkport=checkport)
        return login


def main():
    # Barbip421|poochie1|JUAN|FERNANDEZ|2408 NE 41ST PL|HOMESTEAD|FL|33033|

    # frederickadi|erick86|FREDERICK|ADI|39547 GALLAUDET DR APT 3013|FREMONT|CA|94538|6263213857
    #4762 57AVE N|SAINT PETERSBURG|FL|33714
    #lgrubich|leander|LEAH CHAPUT|12619 FERGUS ST NE|MINNEAPOLIS|MN|55449|
    #108.33.103.59|admin|admin|

    listbilling = ''
    list_address_drop = 'frederickadi|erick86|FREDERICK|ADI|39547 GALLAUDET DR APT 3013|FREMONT|CA|94538|6263213857'
    ordervr = Checkssh()
    check = ordervr.check('149.28.164.116', 'root', '3aQ+N)m1bcw3Ttwz',checkport=True)
    print(check)


if __name__ == "__main__":
    sys.exit(main())			
	
