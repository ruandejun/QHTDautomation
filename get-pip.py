from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from multiprocessing import Process
import time

# The main process calls this function to create the driver instance.
def createDriverInstance():
    options = Options()
    options.add_argument('--disable-infobars')
    driver = webdriver.Chrome(chrome_options=options, port=9515)
    return driver

# Called by the second process only.
def secondProcess(executor_url, session_id):
    options = Options()
    options.add_argument("--disable-infobars")
    options.add_argument("--enable-file-cookies")
    capabilities = options.to_capabilities()
    same_driver = webdriver.Remote(command_executor=executor_url, desired_capabilities=capabilities)
    same_driver.close()
    same_driver.session_id = session_id
    same_driver.get("https://www.wikipedia.org")
    time.sleep(4)
    same_driver.quit()

if __name__ == '__main__':
    driver = createDriverInstance()
    driver.get("https://google.com")
    time.sleep(2)

    # Pass the driver session and command_executor to the second process.
    p = Process(target=secondProcess, args=(driver.command_executor._url,driver.session_id))
    p.start()