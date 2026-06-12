#!/usr/bin/python
# -*- coding: utf-8 -*-   
#
# forum_automator.py
#  Xcode-IPython
#
#  Created by V.Anh Tran on 25/09/2012.
#  Copyright (c) 2012 __MyCompanyName__. All rights reserved.
#
import uuid
import socket;
import sys, mybrowser, re, os, subprocess
import hashlib


class Hwid:
    """ Get Hwid And Check
    """

    def __init__(self, emit='', qtcode='', header=''):

        #add header
        self.browser = mybrowser.Rqbrowser()
        # self.browser.link_host = 'store.bigfishgames.com'
        # self.browser.link_origin = 'https://store.bigfishgames.com'
        self.decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'
        self.emit = emit;
        self.qtcode = qtcode;

    def get_hwid(self):
        if 'nt' in os.name:
            current_machine_id = str(subprocess.check_output('wmic csproduct get uuid'), 'utf-8').split('\n')[1].strip()
            # print(current_machine_id)

        else:
            cmd = "system_profiler SPHardwareDataType | awk '/Serial Number/ {print $4}'"
            result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True, check=True)
            current_machine_id = result.stdout.decode("utf-8").strip()
            print(current_machine_id)
        # print(computernode.args)
        name_computer = socket.gethostname()
        # print(uuid.getnode())
        # computernode = hashlib.md5().hexdigest()
        hwid = str(name_computer) + str(current_machine_id)
        #print hwid
        return hwid.strip()

    def check_hwid(self, hwid):
        r = self.browser.open('http://pastebin.com/raw.php?i=StJBJULe')
        content = r.text
        if content.find(hwid) != -1:
            orderfuntion = content.split(hwid + 'order function:')[-1].split('\n')[0].strip()
            return orderfuntion
        else:
            return;


def main():
    #Barbip421|poochie1|JUAN|FERNANDEZ|2408 NE 41ST PL|HOMESTEAD|FL|33033|

    #frederickadi|erick86|FREDERICK|ADI|39547 GALLAUDET DR APT 3013|FREMONT|CA|94538|6263213857
    #4762 57AVE N|SAINT PETERSBURG|FL|33714
    #lgrubich|leander|LEAH CHAPUT|12619 FERGUS ST NE|MINNEAPOLIS|MN|55449|


    ordervr = Hwid(
        header='Mozilla/5.0 (iPad; CPU OS 6_0 like Mac OS X) AppleWebKit/536.26 (KHTML, like Gecko) Version/6.0 Mobile/10A403 Safari/8536.25')
    # check = ordervr.check_hwid('svss8-PC-7eabd5843a48a75d9066fef1f42295ad')
    hwid = ordervr.get_hwid()
    print(hwid)
    # print(check)
    # print ordervr.check_hwid('7111215161920212223242527303233404243484950515253545556575859606162636472-SONANH-GJHJ9W1-A16')


if __name__ == "__main__":
    sys.exit(main())			