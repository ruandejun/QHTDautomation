import requests, sys, re, random, pickle, json, captcha2upload, os
import captcha2upload, time
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from optparse import OptionParser

# from selenium.webdriver.firefox.options import Options
# from selenium.webdriver.edge.options import Options
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver import Edge
from selenium.webdriver.edge.service import Service as EdgeService
import datetime


class VCB():

    def __init__(self, email, password, account_number, decaptcha_key=''):

        self.decaptcha_key = decaptcha_key
        self.email = email
        self.password = password
        self.account_number = account_number

    def scan_bank(self, url, token):

        try:
            self.site_login()
            self.get_transaction(url, token)
        except:
            try:
                self.driver.quit()
            except:
                pass
            print('===Có lỗi xảy ra nghỉ 15 Pt==')
            time.sleep(900)
            self.scan_bank(url, token)
        return

    def site_login(self):

        alphabet = 'abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 5
        max = 10
        stringimg = ''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        captcha_save = 'captchaIMG' + stringimg + '.png'
        print('==Loading login page==')
        edge_options = EdgeOptions()
        # options.
        # options.headless = True
        # options.add_argument("--headless")  # Runs Chrome in headless mode.
        # options.add_argument('--no-sandbox')  # Bypass OS security model
        # options.add_argument('--disable-gpu')  # applicable to windows os only
        # try:
        #     self.driver = webdriver.Firefox(executable_path='geckodriver.exe',options=options)
        # except Exception:
        #     self.driver = webdriver.Firefox(executable_path='D://geckodriver.exe',options=options)
        # edge_options.use_chromium = True  # use_chromium is not needed in selenium 4
        # A little different from Chrome cause we don't need two lines before 'headless' and 'disable-gpu'
        # edge_options.add_argument('headless')
        # edge_options.add_argument('disable-gpu')
        try:
            service = EdgeService(executable_path='msedgedriver.exe')
            self.driver = Edge(service=service, options=edge_options)
        except Exception:
            service = EdgeService(executable_path='msedgedriver.exe')
            self.driver = Edge(service=service, options=edge_options)

        self.driver.get("https://vcbdigibank.vietcombank.com.vn/#/login?returnUrl=%2Fhome")
        self.driver.find_element(By.ID, 'username').send_keys(self.email)
        try:
            self.driver.find_element(By.ID, 'app_password_login').send_keys(self.password)
        except:
            self.driver.find_element(By.CLASS_NAME, 'pass').send_keys(self.password)
        self.driver.find_element(By.XPATH, "//img[contains(./@src, 'captcha')]").screenshot(captcha_save)
        print('==Getting captcha results==')
        decaptcha_key = 'aa15c055da98e4867e9c924dce54f1e2'
        captcha_save = captcha_save
        captcha = captcha2upload.CaptchaUpload(decaptcha_key)
        captcha_input = captcha.solve(captcha_save)
        print('captcha:', captcha_input)
        os.remove(captcha_save)
        self.driver.find_element(By.XPATH,  "//*[@formcontrolname='captcha']").send_keys(captcha_input)
        # self.driver.find_element_by_name('captcha').send_keys(captcha_input)
        self.driver.find_element(By.ID, 'btnLogin').click()
        print('==Getting danhsachtaikhoan==')
        timeout = 30
        element_present = EC.presence_of_element_located(
            (By.XPATH, "//a[@routerlink='/thongtintaikhoan/danhsachtaikhoan']"))
        WebDriverWait(self.driver, timeout).until(element_present)
        element = self.driver.find_element(By.XPATH, "//a[@routerlink='/thongtintaikhoan/danhsachtaikhoan']")
        self.driver.execute_script("arguments[0].click();", element)
        print('==Getting chitiettaikhoan==')
        element_present = EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'VND')]"))
        WebDriverWait(self.driver, timeout).until(element_present)
        time.sleep(2)
        element = self.driver.find_elements(By.XPATH, "//div[contains(text(), '" + self.account_number + "')]")[-1]
        self.driver.execute_script("arguments[0].click();", element)
        element_present = EC.presence_of_element_located(
            (By.XPATH, "//*[contains(text(), '" + self.account_number + " - VND')]"))
        WebDriverWait(self.driver, timeout).until(element_present)

        time.sleep(1)
        return True

    def captcha_solve(self, captcha_save):
        print(captcha_save, self.decaptcha_key)
        captcha = captcha2upload.CaptchaUpload(self.decaptcha_key)
        print(captcha.getbalance())
        captcha_input = captcha.solve(captcha_save)
        print(captcha_input)
        return captcha_input

    def download_image(self, url):
        r = self.browser.get(url, stream=True)
        alphabet = 'abcdefghijklmnopqrstuvwxyz1234567890ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        min = 5
        max = 10
        stringimg = ''
        for x in random.sample(alphabet, random.randint(min, max)):
            stringimg += x
        captcha_save = 'captchaIMG' + stringimg + '.png'
        f = open(captcha_save, 'wb')
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
        return captcha_save

    def get_transaction(self, url, token):

        header = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36',
            'Accept-Encoding': 'gzip, deflate',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Connection': 'keep-alive',
            'Accept-Language': 'en-US',
            'Accept': 'application/json',
            'Authorization': 'Token ' + token
        }
        self.browser = requests.session()
        self.browser.headers = header
        timeout = 30
        dict_giao_dich = {}
        while 1:
            element = self.driver.find_element(By.XPATH,"//span[@class='ubtn-text' and contains(text(), 'Tìm kiếm')]")
            self.driver.execute_script("arguments[0].click();", element)
            element_present = EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Số tham chiếu')]"))
            WebDriverWait(self.driver, timeout).until(element_present)
            i=0
            while i < 10:
                element = self.driver.find_element(By.XPATH,"//span[@class='ubtn-text' and contains(text(), 'Xem thêm')]")
                self.driver.execute_script("arguments[0].click();", element)      
                element_present = EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Số tham chiếu')]"))
                WebDriverWait(self.driver, timeout).until(element_present)
                time.sleep(3)                
                i+=1

            html = self.driver.page_source
            list_giao_dich = re.findall(
                r'</div><div class="list-info-txt-main color-white">(.+?)</div>.+?">Số tham chiếu:(.+?)</div>.+?">(.+?)</div>',
                html)
            print('tìm giao dịch', datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), len(list_giao_dich), url)
            for line_giao_dich in list_giao_dich:
                Mota, Sothamchieu, Sotien = line_giao_dich
                if Sothamchieu.strip() not in dict_giao_dich:
                    print(Mota.strip(), Sothamchieu.strip(), Sotien.strip())

                    data = {}
                    data['mota'] = Mota.strip()
                    data['sothamchieu'] = Sothamchieu.strip()
                    data['sotien'] = Sotien.strip()
                    try:
                        r = self.browser.post(url, data, timeout=30)
                        print(r.json())
                    except:
                        continue
                    else:
                        dict_giao_dich[Sothamchieu.strip()] = 1
      

            # self.driver.refresh()
            time.sleep(15)

            # print(line_giao_dich)


def main():
    parser = OptionParser()

    Hello = """
    	CHECKER V.1.0

    """
    print(Hello)
    parser.add_option("-s", dest="site", help="Get vcb site", metavar="<maidzo>", type="string")
    try:
        (options, args) = parser.parse_args()
        # list
        if options.site:
            email = None
            password = None
            account_number = None
            url = None
            token = None
            if options.site == 'maidzo':
                email = '0948002324'
                password = 'Ttbd123!@#'
                account_number = '0451000349077'
                url = 'https://maidzo.vn/page/import_vcb_transaction/'
                token = 'a6280f7708d7fa9ced8101d58cff6e9cc2831baf'
            elif options.site == 'shipway247':
                email = '0705891987'
                password = 'Hanoi1234@#'
                account_number = '0451000307966'
                url = 'https://shipway247.com/page/import_vcb_transaction/'
                token = 'dc9432155d351ef593f04739886473af2e8f8918'
            elif options.site == 'alo68':
                email = '0904657943'
                password = 'Tuan123@'
                account_number = '0691002933741'
                url = 'https://alo68.vn/page/import_vcb_transaction/'
                token = 'dc4fffcf58574cd3c204dff31713668dcbb9a610'                
            if email and password and account_number:
                vcb_tool = VCB(email, password, account_number)
                vcb_tool.site_login()
                vcb_tool.get_transaction(url, token)
        else:
            parser.print_help()
            sys.exit(1)

    except IOError as e:
        if "directory" in str(e[1]):
            print("==\t\tCan't open file")
            sys.exit(1)
        else:
            print("==\t\t" + e[1])
            sys.exit(1)

    # vcb_tool = vcb()
    # session = vcb_tool.site_login()
    # vcb_tool.get_transaction()


if __name__ == "__main__":
    sys.exit(main())
