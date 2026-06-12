from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver import Chrome

import os, time
import speech_recognition as sr
from time import sleep
from typing import Type

from pypasser.exceptions import IpBlock
from pypasser.utils import download_audio, convert_to_wav

class reCaptchaV2:
    """
    reCaptchaV2 bypass
    -----------------
    Solving reCaptcha V2 using speech to text
    
    Attributes
    ----------
    driver: webdriver
    
    play: bool
        default is True
    
    attempts: int
        default is 3 times

    Returns
    ----------
    bool: result of solver
    """
    def __init__(self, driver: Type[Chrome], play: bool = True, attempts: int = 3):
        self.driver   = driver
        self.play     = play
        self.attempts = attempts
        
    def resolve_captcha(self):
       
        remaining_attempts = self.attempts
        file_path = None

        try:
            self.__click_check_box__()
            
            if self.__is_checked__():
                return True
            
            self.__click_audio_button__()
            
            while remaining_attempts:
                remaining_attempts -= 1
                
                link = self.__get_audio_link__()
                file_path = convert_to_wav(download_audio(link))
                self.__type_text__(self.speech_to_text(file_path))
                os.remove(file_path)
                
                checked = self.__is_checked__()
                if checked or not remaining_attempts:
                    return checked
            
        except Exception as e:
            if file_path:
                os.remove(file_path)
                
            if 'rc-doscaptcha-header' in self.driver.page_source:
                raise IpBlock()
            else:
                raise e
        

      
    def __click_check_box__(self):
        element = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.XPATH, "//iframe[@title='reCAPTCHA']")))
        # element = driver.find_element(By.XPATH, "//iframe[@title='reCAPTCHA']")
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'});", element)
        time.sleep(3)
        self.driver.switch_to.frame(element)
        
        check_box = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#recaptcha-anchor")))
        element = self.driver.find_element(By.CSS_SELECTOR ,"#recaptcha-anchor")
        self.driver.execute_script("arguments[0].scrollIntoView({behavior: 'auto', block: 'center', inline: 'center'});", element)
        self.driver.execute_script("arguments[0].click();", check_box)
        self.driver.switch_to.default_content()
        
    def __click_audio_button__(self):
        self.driver.switch_to.frame(self.driver.find_element(By.XPATH, "//iframe[@title='recaptcha challenge expires in two minutes']"))
        audio_btn = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#recaptcha-audio-button")))
        self.driver.execute_script("arguments[0].click();", audio_btn)
        self.driver.switch_to.default_content()

    def __get_audio_link__(self):
        voice  = self.driver.find_element(By.XPATH, "//iframe[@title='recaptcha challenge expires in two minutes']")
        self.driver.switch_to.frame(voice)
        download_btn = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR ,".rc-audiochallenge-tdownload-link, .audio-source")))
        link = download_btn.get_attribute('href')
        if not link:
            link = download_btn.get_attribute('src')
        if self.play:
            play_button = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".rc-audiochallenge-play-button > button")))
            self.driver.execute_script("arguments[0].click();", play_button)
        return link
    
    def __type_text__(self, text):
        text_field = WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR ,"#audio-response")))
        text_field.send_keys(text , Keys.ENTER)
        self.driver.switch_to.default_content()
        
    def __is_checked__(self):
        sleep(3)
        self.driver.switch_to.frame(WebDriverWait(self.driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'iframe[name^=a]'))))
        try:
            self.driver.find_element(By.CSS_SELECTOR, '.recaptcha-checkbox-checked')
            self.driver.switch_to.default_content()
            return True
        except NoSuchElementException:
            self.driver.switch_to.default_content()
            return False
        
    def speech_to_text(self, audio_path: str) -> str:   
        r = sr.Recognizer()
        with sr.AudioFile(audio_path) as source:
            audio = r.record(source)

        return r.recognize_sphinx(audio)