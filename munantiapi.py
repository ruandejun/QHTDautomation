#!/usr/bin/python
# -*- coding: utf-8 -*-   
import re
import random
import sys
import time
import json
import base64
import os
import hashlib
import subprocess
import socket
import zipfile
import requests
import pathlib
import functools
import shutil
from urllib.parse import unquote, quote, urlencode
from mybrowser import Rqbrowser
from tqdm.auto import tqdm

class MunAntiApi:
    """
    MunAntiApi - Client API for antidetect browser management.
    Features automatic offline fallback using local JSON files when the server is unreachable.
    """
    def __init__(self):
        self.OFFLINE = True  # Kích hoạt chế độ Offline mặc định vì server đã offline
        
        if hasattr(sys, 'frozen'):
            basis = sys.executable
        else:
            basis = sys.argv[0]
        self.appFolderPath = os.path.split(basis)[0]
        self.path_munlogin = os.path.join(self.appFolderPath, 'munlogin.json')
        self.token = self.get_or_save_token()
        self.browser = Rqbrowser(SECRET_KEY='7yn^8pwp+yzd2l4ki6+v9kp(h)rzs$9gxu4ao^_p+9x_5+1*6o', token=self.token)

    def _read_local_db(self, filename, default=None):
        if default is None:
            default = []
        path = os.path.join(self.appFolderPath, filename)
        if not os.path.exists(path):
            return default
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return default

    def _write_local_db(self, filename, data):
        path = os.path.join(self.appFolderPath, filename)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            return True
        except Exception:
            return False

    def get_or_save_token(self, token=''):
        self.token = token
        if not token:
            try:
                f = open(self.path_munlogin, 'r')
                result = json.loads(f.read())
                if 'token' in result:
                    self.token = result['token']
                else:
                    with open(self.path_munlogin, 'w') as f:
                        data = {'token': ''}
                        json.dump(data, f, ensure_ascii=False)    
            except:
                with open(self.path_munlogin, 'w') as f:
                    data = {'token': ''}
                    json.dump(data, f, ensure_ascii=False)         
        else:
            print('save token==')
            try:
                f = open(self.path_munlogin, 'r')
                result = json.loads(f.read())
                f.close()
            except:
                result = {}
            with open(self.path_munlogin, 'w') as f:
                result.update({'token': token})
                json.dump(result, f, ensure_ascii=False)
        return self.token                
    
    def site_login(self, email, password):
        if self.OFFLINE:
            self.token = 'mock_offline_token_' + hashlib.md5(email.encode()).hexdigest()[:10]
            self.browser.token = self.token
            self.get_or_save_token(token=self.token)
            return self.token
        
        try:
            data = {'username': email, 'password': password}
            r = self.browser.open('https://api.munlogin.vip/clapi/user/login/', data=data)
            result = r.json()
            if 'token' in result:
                self.token = result['token']
                self.browser.token = self.token
                self.get_or_save_token(token=self.token)
                return self.token
        except Exception:
            pass
        return None
    
    def get_all_profiles(self):
        if self.OFFLINE:
            return {'success': True, 'data': self._read_local_db('profiles.json', [])}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_browser_profiles/')
            return r.json()
        except Exception:
            return {'success': True, 'data': self._read_local_db('profiles.json', [])}

    def get_accounts_created(self, action=None, dataGet={}):
        if self.OFFLINE:
            accounts = self._read_local_db('accounts.json', [])
            if action == 'random':
                acc_type = dataGet.get('type')
                filtered = [a for a in accounts if a.get('type') == acc_type]
                if filtered:
                    return {'success': True, 'data': [random.choice(filtered)]}
                return {'success': False, 'msg': 'No accounts found'}
            return {'success': True, 'data': accounts}
        try:
            if action:
                request_url = 'https://api.munlogin.vip/telegram/bapi/get_accounts_created/?action=' + action
                for key, value in dataGet.items():
                    request_url = request_url + '&' + key + '=' + value
                r = self.browser.open(request_url, timeout=60)
            else:    
                r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_accounts_created/', timeout=60)
            return r.json()
        except Exception:
            return {'success': True, 'data': self._read_local_db('accounts.json', [])}

    def get_profile_by_id(self, id=None):
        if self.OFFLINE:
            profiles = self._read_local_db('profiles.json', [])
            for p in profiles:
                if str(p.get('id')) == str(id):
                    return {'success': True, 'data': p}
            return {'success': False, 'msg': 'Profile not found'}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_browser_profile_by_id/', data={'id': id})
            return r.json()
        except Exception:
            return self.get_profile_by_id(id)

    def get_profile_by_account_id(self, id=None):
        if self.OFFLINE:
            profiles = self._read_local_db('profiles.json', [])
            for p in profiles:
                if str(p.get('account_id')) == str(id):
                    return {'success': True, 'data': p}
            if profiles:
                return {'success': True, 'data': profiles[0]}
            return {'success': False, 'msg': 'Profile not found'}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_profile_by_account_id/', data={'id': id})
            return r.json()
        except Exception:
            return {'success': False}

    def create_profile(self, profile_info={}):
        if self.OFFLINE:
            profiles = self._read_local_db('profiles.json', [])
            if 'id' not in profile_info or not profile_info['id']:
                profile_info['id'] = int(time.time() * 1000)
            profiles.append(profile_info)
            self._write_local_db('profiles.json', profiles)
            return {'success': True, 'data': profile_info}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/create_browser_profile/', json_data=profile_info)
            return r.json()
        except Exception:
            return self.create_profile(profile_info)

    def remove_profiles(self, data={}):
        if self.OFFLINE:
            profiles = self._read_local_db('profiles.json', [])
            ids_to_remove = [str(x) for x in data.get('list_id', [])]
            profiles = [p for p in profiles if str(p.get('id')) not in ids_to_remove]
            self._write_local_db('profiles.json', profiles)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/remove_profiles/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}

    def remove_accounts(self, data={}):
        if self.OFFLINE:
            accounts = self._read_local_db('accounts.json', [])
            ids_to_remove = [str(x) for x in data.get('list_id', [])]
            accounts = [a for a in accounts if str(a.get('id')) not in ids_to_remove]
            self._write_local_db('accounts.json', accounts)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/remove_accounts/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}

    def remove_emails(self, data={}):
        if self.OFFLINE:
            emails = self._read_local_db('emails.json', [])
            ids_to_remove = [str(x) for x in data.get('list_id', [])]
            emails = [e for e in emails if str(e.get('id')) not in ids_to_remove]
            self._write_local_db('emails.json', emails)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/remove_emails/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}

    def update_profile_by_id(self, update_data={}):
        if self.OFFLINE:
            profiles = self._read_local_db('profiles.json', [])
            profile_id = update_data.get('id')
            for p in profiles:
                if str(p.get('id')) == str(profile_id):
                    p.update(update_data)
                    break
            self._write_local_db('profiles.json', profiles)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_profile_by_id/', json_data=update_data)
            return r.json()
        except Exception:
            return {'success': False}

    def update_account_by_id(self, update_data={}):
        if self.OFFLINE:
            accounts = self._read_local_db('accounts.json', [])
            acc_id = update_data.get('id')
            for a in accounts:
                if str(a.get('id')) == str(acc_id):
                    a.update(update_data)
                    break
            self._write_local_db('accounts.json', accounts)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_account_by_id/', json_data=update_data)
            return r.json()
        except Exception:
            return {'success': False}

    def add_accounts_created(self, update_data={}):
        if self.OFFLINE:
            accounts = self._read_local_db('accounts.json', [])
            if 'id' not in update_data or not update_data['id']:
                update_data['id'] = int(time.time() * 1000)
            accounts.append(update_data)
            self._write_local_db('accounts.json', accounts)
            return {'success': True, 'data': update_data}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/add_accounts_created/', json_data=update_data)
            return r.json()
        except Exception:
            return {'success': False}

    def add_accounts_emails(self, list_emails=[]):
        if self.OFFLINE:
            emails = self._read_local_db('emails.json', [])
            for e in list_emails:
                if 'id' not in e or not e['id']:
                    e['id'] = int(time.time() * 1000) + random.randint(0, 1000)
                emails.append(e)
            self._write_local_db('emails.json', emails)
            return {'success': True}
        try:
            data = {'list_emails': list_emails}
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/add_accounts_emails/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}

    def remove_accounts_emails(self, data={}):
        if self.OFFLINE:
            emails = self._read_local_db('emails.json', [])
            ids_to_remove = [str(x) for x in data.get('list_id', [])]
            emails = [e for e in emails if str(e.get('id')) not in ids_to_remove]
            self._write_local_db('emails.json', emails)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/remove_accounts_emails/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}

    def get_accounts_emails(self, action=None, dataGet={}):
        if self.OFFLINE:
            emails = self._read_local_db('emails.json', [])
            if action == 'list_signup_emails':
                acc_type = dataGet.get('account_type')
                return {'success': True, 'data': [e for e in emails if e.get('type') == acc_type]}
            return {'success': True, 'data': emails}
        try:
            if action:
                request_url = 'https://api.munlogin.vip/telegram/bapi/get_accounts_emails/?action=' + action
                for key, value in dataGet.items():
                    request_url = request_url + '&' + key + '=' + value
                r = self.browser.open(request_url, timeout=60)
            else:    
                r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_accounts_emails/', timeout=60)
            return r.json()
        except Exception:
            return {'success': True, 'data': self._read_local_db('emails.json', [])}

    def set_black_list_accounts_emails(self, update_data={}):
        if self.OFFLINE:
            emails = self._read_local_db('emails.json', [])
            ids = [str(x) for x in update_data.get('list_id', [])]
            for e in emails:
                if str(e.get('id')) in ids:
                    e['blacklist'] = True
            self._write_local_db('emails.json', emails)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/set_black_list_accounts_emails/', json_data=update_data)
            return r.json()
        except Exception:
            return {'success': False}

    def update_accounts_emails(self, update_data={}):
        if self.OFFLINE:
            emails = self._read_local_db('emails.json', [])
            email_id = update_data.get('id')
            for e in emails:
                if str(e.get('id')) == str(email_id):
                    e.update(update_data)
                    break
            self._write_local_db('emails.json', emails)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_accounts_emails/', json_data=update_data)
            return r.json()
        except Exception:
            return {'success': False}
    
    def get_accounts_data(self, action=None, dataGet={}):
        if self.OFFLINE:
            if action == 'random_address':
                return {
                    'success': True,
                    'data': {
                        'first_name': 'John',
                        'last_name': 'Doe',
                        'street': '123 Main St',
                        'city': 'New York',
                        'state': 'NY',
                        'zip_code': '10001',
                        'phone': '1234567890'
                    }
                }
            return {'success': True, 'data': {}}
        try:
            if action:
                request_url = 'https://api.munlogin.vip/telegram/bapi/get_accounts_data/?action=' + action
                for key, value in dataGet.items():
                    request_url = request_url + '&' + key + '=' + value
                r = self.browser.open(request_url, timeout=60)
            else:    
                r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_accounts_data/', timeout=60)
            return r.json()
        except Exception:
            return {'success': False}

    def get_inject_info(self):
        if self.OFFLINE:
            path_dien = os.path.join(self.appFolderPath, 'dist', 'dien.html')
            if os.path.exists(path_dien):
                try:
                    with open(path_dien, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass
            path_dien_parent = os.path.join(self.appFolderPath, 'dien.html')
            if os.path.exists(path_dien_parent):
                try:
                    with open(path_dien_parent, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass
            return {'success': True, 'data': {}}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_inject_info/', timeout=60)
            return r.json()
        except Exception:
            return self.get_inject_info()
    
    def get_key_for_search(self):
        if self.OFFLINE:
            return {'success': True, 'data': []}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_key_for_search/', timeout=60)
            return r.json()
        except Exception:
            return {'success': False}
    
    def add_key_for_search(self, list_keys):
        if self.OFFLINE:
            return {'success': True}
        try:
            data = {'list_keys': list_keys}
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/add_key_for_search/', json_data=data, timeout=60)
            return r.json()
        except Exception:
            return {'success': False}
    
    def set_auto_views(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/set_auto_views/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}

    def accounts_update_new_profiles(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/accounts_update_new_profiles/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}
    
    def update_new_profiles(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_new_profiles/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}
 
    def remove_auto_views(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/remove_auto_views/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}
    
    def get_profile_for_auto_views(self, data={}):
        if self.OFFLINE:
            return {'success': True, 'data': {}}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_profile_for_auto_views/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}
    
    def update_auto_views(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_auto_views/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}  
      
    def check_version_for_update(self):
        if self.OFFLINE:
            return {'success': True, 'version': '1.3.5'}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/check_version_for_update/')
            return r.json()    
        except Exception:
            return {'success': True, 'version': '1.3.5'}

    def get_mun_proxies(self):
        if self.OFFLINE:
            return {'success': True, 'data': self._read_local_db('munproxies.json', [])}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_mun_proxies/')
            return r.json()   
        except Exception:
            return {'success': True, 'data': self._read_local_db('munproxies.json', [])}
    
    def add_mun_proxies(self, data={}):
        if self.OFFLINE:
            proxies = self._read_local_db('munproxies.json', [])
            if 'id' not in data or not data['id']:
                data['id'] = int(time.time() * 1000)
            proxies.append(data)
            self._write_local_db('munproxies.json', proxies)
            return {'success': True, 'data': data}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/add_mun_proxies/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}
    
    def remove_mun_proxies(self, data={}):
        if self.OFFLINE:
            proxies = self._read_local_db('munproxies.json', [])
            ids_to_remove = [str(x) for x in data.get('list_id', [])]
            proxies = [p for p in proxies if str(p.get('id')) not in ids_to_remove]
            self._write_local_db('munproxies.json', proxies)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/remove_mun_proxies/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}
    
    def update_munproxies_by_id(self, data={}):
        if self.OFFLINE:
            proxies = self._read_local_db('munproxies.json', [])
            proxy_id = data.get('id')
            for p in proxies:
                if str(p.get('id')) == str(proxy_id):
                    p.update(data)
                    break
            self._write_local_db('munproxies.json', proxies)
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_munproxies_by_id/', json_data=data)
            return r.json()
        except Exception:
            return {'success': False}

    def get_link_checkout(self, action=None, dataGet={}):
        if self.OFFLINE:
            return {'success': True, 'data': []}
        try:
            if action:
                request_url = 'https://api.munlogin.vip/telegram/bapi/get_link_checkout/?action=' + action
                for key, value in dataGet.items():
                    request_url = request_url + '&' + key + '=' + value
                r = self.browser.open(request_url, timeout=60)
            else:    
                r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_link_checkout/', timeout=60)
            return r.json() 
        except Exception:
            return {'success': False}
        
    def add_link_checkout(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/add_link_checkout/', json_data=data)
            return r.json()      
        except Exception:
            return {'success': False}

    def update_link_checkout(self, update_data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_link_checkout/', json_data=update_data)
            return r.json()        
        except Exception:
            return {'success': False}
    
    def get_tool_setting(self, action=None, dataGet={}):
        if self.OFFLINE:
            if action == 'hwid':
                return {
                    'hwid': dataGet.get('hwid', 'mock_hwid'),
                    'create_data': [{'value': 'Amazon'}, {'value': 'Ebay'}, {'value': 'Walmart'}],
                    'check_data': [{'value': 'Amazon'}, {'value': 'Ebay'}, {'value': 'Walmart'}, {'value': 'Macys'}]
                }
            return {'success': True}
        try:
            if action:
                request_url = 'https://api.munlogin.vip/telegram/bapi/get_tool_setting/?action=' + action
                for key, value in dataGet.items():
                    request_url = request_url + '&' + key + '=' + value
                r = self.browser.open(request_url, timeout=60)
            else:    
                r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_tool_setting/', timeout=60)
            return r.json()  
        except Exception:
            return self.get_tool_setting(action, dataGet)

    def get_files_map(self, action=None, dataGet={}):
        if self.OFFLINE:
            return {'success': True, 'data': {}}
        try:
            if action:
                request_url = 'https://api.munlogin.vip/telegram/bapi/get_files_map/?action=' + action
                for key, value in dataGet.items():
                    request_url = request_url + '&' + key + '=' + value
                r = self.browser.open(request_url, timeout=60)
            else:    
                r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_files_map/', timeout=60)
            return r.json()   
        except Exception:
            return {'success': False}

    def get_checker_task(self, action=None, dataGet={}):
        if self.OFFLINE:
            return {'success': True, 'data': []}
        try:
            if action:
                request_url = 'https://api.munlogin.vip/telegram/bapi/get_checker_task/?action=' + action
                for key, value in dataGet.items():
                    request_url = request_url + '&' + key + '=' + str(value)
                r = self.browser.open(request_url, timeout=60)
            else:    
                r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_checker_task/', timeout=60)
            return r.json()  
        except Exception:
            return {'success': False}
    
    def update_checker_task(self, update_data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/update_checker_task/', json_data=update_data)
            return r.json()  
        except Exception:
            return {'success': False}
    
    def add_checker_valid(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/add_checker_valid/', json_data=data)
            return r.json()    
        except Exception:
            return {'success': False}

    def add_checker_invalid(self, data={}):
        if self.OFFLINE:
            return {'success': True}
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/add_checker_invalid/', json_data=data)
            return r.json() 
        except Exception:
            return {'success': False}

    def get_hwid(self):
        try:
            if 'nt' in os.name:
                current_machine_id = str(subprocess.check_output('wmic csproduct get uuid'), 'utf-8').split('\n')[1].strip()
            else:
                cmd = "system_profiler SPHardwareDataType | awk '/Serial Number/ {print $4}'"
                result = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True, check=True)
                current_machine_id = result.stdout.decode("utf-8").strip()
            name_computer = socket.gethostname()
            hwid = str(name_computer) + str(current_machine_id)
            return hwid.strip()    
        except Exception:
            return 'mock_offline_hwid'

    def get_checker_files(self, file_id):
        if self.OFFLINE:
            return ''
        try:
            r = self.browser.open('https://api.munlogin.vip/telegram/bapi/get_checker_files/?file_id=%s' % (file_id))
            return r.text
        except Exception:
            return ''
    
    def unzip_file(self, path_file):
        try:
            if str(path_file)[len(str(path_file))-3:] == 'zip':
                with zipfile.ZipFile(path_file, 'r') as zip_ref:
                    zip_ref.extractall(self.appFolderPath)
                os.remove(path_file)
            return True    
        except Exception:
            return False
    
    def download_file(self, url):
        local_filename = url.split('/')[-1]
        r = requests.get(url, stream=True, allow_redirects=True)
        if r.status_code != 200:
            r.raise_for_status()
            raise RuntimeError(f"Request to {url} returned status code {r.status_code}")
        file_size = int(r.headers.get('Content-Length', 0))

        path = pathlib.Path(local_filename).expanduser().resolve()
        path.parent.mkdir(parents=True, exist_ok=True)

        desc = "(Unknown total file size)" if file_size == 0 else ""
        r.raw.read = functools.partial(r.raw.read, decode_content=True)
        with tqdm.wrapattr(r.raw, "read", total=file_size, desc=desc) as r_raw:
            with path.open("wb") as f:
                shutil.copyfileobj(r_raw, f)
        return path     
    
    def check_download_files_map(self, fileMaps={}):
        if self.OFFLINE:
            print("[OFFLINE] Skipping downloads in offline mode")
            return
        try:
            for value_key in fileMaps.keys():
                path_check = os.path.join(self.appFolderPath, value_key)
                isExist = os.path.exists(path_check)
                if not isExist:
                    file_path = self.download_file(fileMaps[value_key]['download_url'])
                    self.unzip_file(file_path)
        except Exception as e:
            print(f"Error checking downloads: {e}")

def main():
    mun_anti = MunAntiApi()
    print("HWID:", mun_anti.get_hwid())
    print("Profiles:", mun_anti.get_all_profiles())

if __name__ == "__main__":
    main()
