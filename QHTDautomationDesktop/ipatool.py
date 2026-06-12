import os
import re
import json
import hashlib
import plistlib
import requests
import zipfile
import shutil

class IPATool:
    def __init__(self, apple_id, password):
        self.apple_id = apple_id
        self.password = password
        self.guid = self.generate_guid(apple_id)
        self.session = requests.Session()
        self.pod = None
        self.auth_headers = {}
        self.account_name = ""
        self.is_authenticated = False
        
    @staticmethod
    def generate_guid(apple_id: str) -> str:
        DEFAULT_GUID = "000C2941396B"
        GUID_DEFAULT_PREFIX = 2
        GUID_SEED = "CAFEBABE"
        GUID_POS = 10

        h = hashlib.sha1((GUID_SEED + apple_id + GUID_SEED).encode('utf-8')).hexdigest()
        default_part = DEFAULT_GUID[:GUID_DEFAULT_PREFIX]
        hash_part = h[GUID_POS : GUID_POS + (len(DEFAULT_GUID) - GUID_DEFAULT_PREFIX)]
        return (default_part + hash_part).upper()

    def get_bag_endpoint(self) -> str:
        fallback = "https://buy.itunes.apple.com/WebObjects/MZFinance.woa/wa/authenticate"
        headers = {
            "Accept": "application/xml",
            "User-Agent": "Configurator/2.17 (Macintosh; OS X 15.2; 24C5089c) AppleWebKit/0620.1.16.11.6"
        }
        url = f"https://init.itunes.apple.com/bag.xml?guid={self.guid}"
        try:
            r = self.session.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                content = r.content
                start = content.find(b"<plist")
                end = content.find(b"</plist>")
                if start != -1 and end != -1:
                    plist_data = content[start:end+8]
                    plist = plistlib.loads(plist_data)
                    url_bag = plist.get("urlBag", {})
                    endpoint = url_bag.get("authenticateAccount")
                    if endpoint:
                        # Rất quan trọng: Thêm dấu '/' vào cuối nếu chưa có, Apple yêu cầu kết thúc bằng /fast/ hoặc /native/ để xử lý POST.
                        if not endpoint.endswith("/"):
                            endpoint += "/"
                        return endpoint
        except Exception as e:
            print(f"Failed to get bag endpoint: {e}")
        return fallback

    def authenticate(self, code=None) -> tuple[bool, str]:
        """
        Xác thực với Apple.
        Nếu tài khoản yêu cầu 2FA, lần đầu gọi hàm này sẽ kích hoạt gửi mã 2FA.
        Sau đó gọi lại hàm này với tham số `code` chứa mã 2FA 6 chữ số.
        Trả về: (Thành công/Thất bại, Thông báo lỗi hoặc thông tin)
        """
        final_password = self.password
        if code:
            final_password = self.password + str(code)

        auth_url = self.get_bag_endpoint()
        
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Configurator/2.17 (Macintosh; OS X 15.2; 24C5089c) AppleWebKit/0620.1.16.11.6"
        }
        
        req_payload = {
            "appleId": self.apple_id,
            "password": final_password,
            "guid": self.guid,
            "rmp": "0",
            "why": "signIn"
        }
        
        # Thử xác thực (tối đa 4 lần thử như bản gốc)
        last_error = "Đăng nhập thất bại"
        for attempt in range(1, 5):
            req_payload["attempt"] = str(attempt)
            try:
                # Gửi body dưới dạng JSON compact theo đúng cấu trúc của Apple
                compact_body = json.dumps(req_payload, separators=(',', ':'))
                r = self.session.post(auth_url, data=compact_body, headers=headers, timeout=15)
                
                # Cập nhật pod và storefront từ response headers
                if "pod" in r.headers:
                    self.pod = r.headers["pod"]
                if "x-set-apple-store-front" in r.headers:
                    self.storefront = r.headers["x-set-apple-store-front"]
                else:
                    self.storefront = "143441-1,29" # Default US Storefront
                
                if not r.content:
                    # Nếu body rỗng, thử gọi sang endpoint kết thúc bằng fast/ trực tiếp
                    fallback_url = auth_url.rstrip("/") + "/fast/"
                    r = self.session.post(fallback_url, data=compact_body, headers=headers, timeout=15)
                    if "pod" in r.headers:
                        self.pod = r.headers["pod"]
                    if "x-set-apple-store-front" in r.headers:
                        self.storefront = r.headers["x-set-apple-store-front"]
                
                try:
                    resp = plistlib.loads(r.content)
                except Exception as e:
                    return False, f"Không thể giải mã phản hồi từ Apple: {e}"
                
                # Kiểm tra xem đăng nhập thành công hay chưa
                ds_person_id = resp.get("dsPersonId")
                password_token = resp.get("passwordToken")
                
                if ds_person_id and password_token:
                    # Thành công!
                    download_queue_info = resp.get("download-queue-info", {})
                    dsid = download_queue_info.get("dsid", ds_person_id)
                    
                    self.auth_headers = {
                        "X-Dsid": str(dsid),
                        "iCloud-Dsid": str(dsid),
                        "X-Apple-Store-Front": self.storefront,
                        "X-Token": str(password_token)
                    }
                    
                    account_info = resp.get("accountInfo", {})
                    address = account_info.get("address", {})
                    first_name = address.get("firstName", "")
                    last_name = address.get("lastName", "")
                    self.account_name = f"{first_name} {last_name}".strip() or self.apple_id
                    
                    self.is_authenticated = True
                    return True, "Xác thực thành công"
                
                else:
                    # Kiểm tra xem có phải lỗi yêu cầu mã 2FA không
                    customer_message = resp.get("customerMessage", "Thông tin đăng nhập không chính xác")
                    last_error = customer_message
                    
                    # Nếu là mã 2FA (thông thường Apple trả về thông báo yêu cầu nhập mã)
                    # Hoặc nếu người dùng chưa truyền mã code nhưng máy chủ yêu cầu
                    # Bản gốc coi như đã gửi code và kích hoạt form điền code
                    if "verification" in customer_message.lower() or "mã" in customer_message.lower() or attempt == 1:
                        # Trả về thành công trung gian để yêu cầu nhập 2FA
                        if not code:
                            return False, "REQUIRES_2FA"
                    
            except Exception as e:
                last_error = str(e)
                print(f"Lỗi xác thực (lần thử {attempt}): {e}")
                
        return False, last_error

    def get_version_ids(self, app_id: str) -> list[str]:
        """
        Lấy danh sách ID phiên bản của ứng dụng từ Apple Store
        """
        if not self.is_authenticated or not self.pod:
            raise Exception("Chưa đăng nhập hoặc thiếu thông tin Pod")
            
        url = f"https://p{self.pod}-buy.itunes.apple.com/WebObjects/MZFinance.woa/wa/volumeStoreDownloadProduct?guid={self.guid}"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Configurator/2.17 (Macintosh; OS X 15.2; 24C5089c) AppleWebKit/0620.1.16.11.6"
        }
        headers.update(self.auth_headers)
        
        payload = {
            "creditDisplay": "",
            "guid": self.guid,
            "salableAdamId": str(app_id)
        }
        
        try:
            r = self.session.post(url, data=json.dumps(payload), headers=headers, timeout=15)
            resp = plistlib.loads(r.content)
            
            # Ghi log lỗi nếu Apple từ chối mua
            if "cancel-purchase-batch" in resp:
                error_msg = resp.get("customerMessage", "Không thể lấy thông tin ứng dụng.")
                raise Exception(error_msg)
                
            song_list = resp.get("songList", [])
            if not song_list:
                raise Exception("Không tìm thấy thông tin ứng dụng. Vui lòng kiểm tra lại tài khoản đã từng 'mua' ứng dụng này chưa.")
                
            down_info = song_list[0]
            metadata = down_info.get("metadata", {})
            app_ver_ids = metadata.get("softwareVersionExternalIdentifiers", [])
            return [str(x) for x in app_ver_ids]
        except Exception as e:
            raise Exception(f"Lỗi lấy phiên bản ứng dụng: {e}")

    def download_ipa(self, app_id: str, version_id: str, output_ipa_path: str, progress_callback=None) -> None:
        """
        Tải xuống IPA phiên bản mong muốn và nhúng chữ ký cá nhân
        """
        if not self.is_authenticated or not self.pod:
            raise Exception("Chưa đăng nhập hoặc thiếu thông tin Pod")
            
        url = f"https://p{self.pod}-buy.itunes.apple.com/WebObjects/MZFinance.woa/wa/volumeStoreDownloadProduct?guid={self.guid}"
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Configurator/2.17 (Macintosh; OS X 15.2; 24C5089c) AppleWebKit/0620.1.16.11.6"
        }
        headers.update(self.auth_headers)
        
        payload = {
            "creditDisplay": "",
            "guid": self.guid,
            "salableAdamId": str(app_id),
            "externalVersionId": str(version_id)
        }
        
        # 1. Gọi mua/tải ứng dụng
        if progress_callback:
            progress_callback("Đang yêu cầu link tải từ Apple...")
            
        r = self.session.post(url, data=json.dumps(payload), headers=headers, timeout=15)
        resp = plistlib.loads(r.content)
        
        if "cancel-purchase-batch" in resp:
            error_msg = resp.get("customerMessage", "Không thể tải ứng dụng.")
            raise Exception(error_msg)
            
        song_list = resp.get("songList", [])
        if not song_list:
            raise Exception("Không tìm thấy thông tin tải xuống ứng dụng.")
            
        down_info = song_list[0]
        download_url = down_info.get("URL")
        sinfs = down_info.get("sinfs", [])
        metadata = down_info.get("metadata", {})
        
        if not download_url:
            raise Exception("Không có URL tải xuống từ máy chủ Apple.")
            
        # 2. Tải file zip/ipa tạm thời
        temp_zip_path = output_ipa_path + ".tmp"
        if progress_callback:
            progress_callback("Đang kết nối tải file IPA...")
            
        r_dl = self.session.get(download_url, stream=True, timeout=60)
        total_size = int(r_dl.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_zip_path, 'wb') as f:
            for chunk in r_dl.iter_content(chunk_size=1024*128):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        percent = int((downloaded / total_size) * 100)
                        progress_callback(f"Đang tải: {percent}% ({downloaded // (1024*1024)}MB / {total_size // (1024*1024)}MB)")
                        
        if progress_callback:
            progress_callback("Đang giải nén và nhúng chữ ký (SINF)...")
            
        # 3. Giải nén và chèn chữ ký / iTunesMetadata
        temp_extract_dir = temp_zip_path + "_extracted"
        if os.path.exists(temp_extract_dir):
            shutil.rmtree(temp_extract_dir)
        os.makedirs(temp_extract_dir)
        
        try:
            with zipfile.ZipFile(temp_zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_extract_dir)
                
            # Ghi iTunesMetadata.plist
            metadata_path = os.path.join(temp_extract_dir, "iTunesMetadata.plist")
            metadata["apple-id"] = self.apple_id
            metadata["userName"] = self.apple_id
            with open(metadata_path, 'wb') as f_meta:
                plistlib.dump(metadata, f_meta)
                
            # Tìm thư mục .app
            payload_dir = os.path.join(temp_extract_dir, "Payload")
            if not os.path.exists(payload_dir):
                raise Exception("Không tìm thấy thư mục Payload trong file tải về")
                
            app_folder_name = None
            for item in os.listdir(payload_dir):
                if item.endswith(".app"):
                    app_folder_name = item
                    break
                    
            if not app_folder_name:
                raise Exception("Không tìm thấy file thực thi .app")
                
            app_content_dir = os.path.join(payload_dir, app_folder_name)
            
            # Ghi chữ ký
            sc_info_dir = os.path.join(app_content_dir, "SC_Info")
            manifest_path = os.path.join(sc_info_dir, "Manifest.plist")
            
            if os.path.exists(manifest_path):
                with open(manifest_path, 'rb') as f_man:
                    sc_manifest = plistlib.load(f_man)
                sinf_paths = sc_manifest.get("SinfPaths", [])
                for i, sinf_path in enumerate(sinf_paths):
                    target_sinf_path = os.path.join(app_content_dir, sinf_path.replace("\\", "/"))
                    os.makedirs(os.path.dirname(target_sinf_path), exist_ok=True)
                    sinf_data = sinfs[i]["sinf"]
                    with open(target_sinf_path, 'wb') as f_sinf:
                        f_sinf.write(sinf_data)
            else:
                info_plist_path = os.path.join(app_content_dir, "Info.plist")
                with open(info_plist_path, 'rb') as f_inf:
                    info_list = plistlib.load(f_inf)
                executable_name = info_list.get("CFBundleExecutable")
                if not executable_name:
                    raise Exception("Không tìm thấy trường CFBundleExecutable trong Info.plist")
                target_sinf_path = os.path.join(sc_info_dir, f"{executable_name}.sinf")
                os.makedirs(os.path.dirname(target_sinf_path), exist_ok=True)
                sinf_data = sinfs[0]["sinf"]
                with open(target_sinf_path, 'wb') as f_sinf:
                    f_sinf.write(sinf_data)
                    
            # 4. Đóng gói lại thành IPA
            if progress_callback:
                progress_callback("Đang đóng gói file IPA hoàn chỉnh...")
                
            if os.path.exists(output_ipa_path):
                os.remove(output_ipa_path)
                
            with zipfile.ZipFile(output_ipa_path, 'w', zipfile.ZIP_DEFLATED) as zip_out:
                for root, dirs, files in os.walk(temp_extract_dir):
                    for file in files:
                        abs_path = os.path.join(root, file)
                        rel_path = os.path.relpath(abs_path, temp_extract_dir)
                        zip_out.write(abs_path, rel_path)
                        
            if progress_callback:
                progress_callback("Tải và ký IPA thành công!")
                
        finally:
            # Dọn dẹp file tạm
            if os.path.exists(temp_zip_path):
                os.remove(temp_zip_path)
            if os.path.exists(temp_extract_dir):
                shutil.rmtree(temp_extract_dir)

def extract_app_id(url_or_id: str) -> str:
    url_or_id = url_or_id.strip()
    if url_or_id.isdigit():
        return url_or_id
    if "id" in url_or_id:
        part = url_or_id.split("id")[-1]
        digits = []
        for char in part:
            if char.isdigit():
                digits.append(char)
            else:
                break
        if digits:
            return "".join(digits)
    return ""

def get_app_details_from_itunes(app_id: str) -> dict:
    """
    Truy vấn thông tin cơ bản của ứng dụng (Tên, Nhà phát triển, Ảnh Icon) từ API iTunes công khai
    """
    url = f"https://itunes.apple.com/lookup?id={app_id}&entity=software"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        results = data.get("results", [])
        if results:
            item = results[0]
            return {
                "name": item.get("trackName"),
                "artist": item.get("artistName"),
                "icon": item.get("artworkUrl512") or item.get("artworkUrl100"),
                "bundle_id": item.get("bundleId"),
                "version": item.get("version"),
                "success": True
            }
    except Exception as e:
        print(f"Failed to fetch public app details: {e}")
    return {"success": False}
