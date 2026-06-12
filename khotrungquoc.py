import requests, sys, re, random, pickle, json, captcha2upload, os
import captcha2upload, time
from optparse import OptionParser
import datetime, os
import sqlite3 as lite

class Khotrungquoc():

    def __init__(self,appFolderPath='', site='https://khotrungquoc.com', trigger=None):
        self.trigger = trigger
        self.site = site
        self.appFolderPath = appFolderPath
        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
            # 'Accept-Encoding': 'gzip, deflate, br',
            # 'Content-Type': 'multipart/form-data; boundary=----WebKitFormBoundaryg9PeJyeShMfrx5Kx',
            # 'Connection': 'keep-alive',
            # 'Accept-Language': 'en-US',
            # 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        }
        self.browser = requests.session()
        self.browser.headers = header
    
    def check_uploaded(self,file_name):
        con = lite.connect(self.appFolderPath + '/kuaidi.db')
        with con:
            con.row_factory = lite.Row
            cur = con.cursor()
            try:
                cur.execute("SELECT * from kuaidi WHERE number='%s'" % (file_name))
            except:
                cur.execute('''CREATE TABLE kuaidi
				       (id INTEGER PRIMARY KEY  AUTOINCREMENT,
				       number       CHAR(255) NOT NULL,
				       url      CHAR(999) NOT NULL,
				       weight      CHAR(255) NOT NULL,
				       updated     CHAR(255) NOT NULL);''')
                return
            rows = cur.fetchall()
            if len(rows) > 0:
                return True
        con.close();        
        return
    
    def save_uploaded(self, number,url,weight,updated):
        con = lite.connect(self.appFolderPath + '/kuaidi.db')
        with con:
            con.row_factory = lite.Row
            cur = con.cursor()

            cur.execute("INSERT INTO kuaidi (number,url,weight,updated) \
									VALUES ('%s', '%s', '%s', '%s')" % (number,url,weight,updated));
        con.close()
        if self.trigger:
            self.trigger.emit('reload', 'reload_table');
        return True

    def upload_images(self,path_file):
        # print(path_file)
        created_time = datetime.datetime.fromtimestamp(os.path.getctime(path_file)).strftime('%Y-%m-%d %H:%M:%S')
        # print(created_time)
        url = self.site+'/page/upload_images/'
        files = {'upload_images': open(path_file, 'rb')}
        try:
            r = self.browser.post(url, files=files, data={'tracking_departed':created_time})
            result = r.json()
        except:
            return
        if result['success']:
            return result
        else:
            return        
    
    def save_last_sync(self):
        r = open('config.txt','w')
        last_sync = datetime.datetime.now()
        r.write(last_sync.strftime('%Y-%m-%d %H:%M:%S'))
        r.close()      
        return last_sync

    def upload_folder(self,path):
        list_files = os.listdir(path)
        newer_files = [f for f in list_files if re.search(r'N(.+?)W(.+?).jpeg',f)]#datetime.datetime.fromtimestamp(os.path.getctime(os.path.join(path,f))) >= last_sync]
        for f in newer_files:
            ext = os.path.splitext(f)[1]
            info_images = re.search(r'N(.+?)W(.+?).jpeg',f)
            if not info_images:
                continue
            image_path = os.path.join(path,f)
            if self.check_uploaded(f):
                continue
            print(f)
            created_time = datetime.datetime.fromtimestamp(os.path.getctime(image_path)).strftime('%Y-%m-%d %H:%M:%S')
            result = self.upload_images(image_path)
            if result:
                print(f,result['url'],info_images.group(2),created_time)
                
                self.save_uploaded(f,result['url'],info_images.group(2),created_time)

    def sync_images(self, path='C:/Users/tuans/Desktop/kuaidi'):
        while 1:
            print('==Trying to upload==')
            list_files = os.listdir(path)
            valid_images = ['.jpeg']
            try:
                r = open('config.txt','r')
                last_sync = datetime.datetime.strptime(r.read(), '%Y-%m-%d %H:%M:%S')
            except:
                last_sync = datetime.datetime(2000, 1, 1, 1, 1)
            
            self.upload_folder(path)    
            
            listPaths = [os.path.join(path,f) for f in list_files if os.path.isdir(os.path.join(path,f))]

            for line_path in listPaths:
                self.upload_folder(line_path) 

            last_sync = self.save_last_sync()    
            time.sleep(120)


def main():
    try:
        currentRunningScriptPath = os.path.realpath(__file__)
        appFolderPath, scriptName = os.path.split(currentRunningScriptPath);
    except Exception as e:
        appFolderPath = os.getcwd();  # for window build
    khotrungquoc = Khotrungquoc(appFolderPath=appFolderPath)
    khotrungquoc.sync_images()

    # vcb_tool = vcb()
    # session = vcb_tool.site_login()
    # vcb_tool.get_transaction()


if __name__ == "__main__":
    sys.exit(main())
