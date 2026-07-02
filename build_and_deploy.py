import os
import sys
import subprocess
import zipfile
import paramiko

# Đảm bảo output có mã hóa UTF-8 để hiển thị tiếng Việt chính xác
sys.stdout.reconfigure(encoding='utf-8')

def run_pyinstaller():
    print("=== Bắt đầu chạy PyInstaller ===")
    spec_path = "MunAutomation.spec"
    if not os.path.exists(spec_path):
        print(f"Lỗi: Không tìm thấy file spec tại {spec_path}")
        return False
    
    # Sử dụng python trong môi trường ảo để chạy pyinstaller hoặc gọi trực tiếp từ .venv
    venv_pyinstaller = os.path.join(".venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(venv_pyinstaller):
        # Fallback nếu không chạy trong venv
        venv_pyinstaller = "pyinstaller"
        
    cmd = [venv_pyinstaller, spec_path, "--clean"]
    print(f"Đang chạy lệnh: {' '.join(cmd)}")
    
    try:
        # Chạy lệnh build và hiển thị output trực tiếp
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding='utf-8')
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc == 0:
            print("=== Đóng gói PyInstaller thành công! ===")
            return True
        else:
            print(f"=== PyInstaller thất bại với mã lỗi: {rc} ===")
            return False
    except Exception as e:
        print(f"Lỗi khi chạy PyInstaller: {e}")
        return False

def zip_executable():
    print("=== Bắt đầu nén file C69Automation.exe ===")
    exe_path = os.path.join("dist", "C69Automation.exe")
    zip_path = os.path.join("dist", "C69Automation.zip")
    qhtd_zip = os.path.join("dist", "QHTDautomation.zip")
    
    if not os.path.exists(exe_path):
        print(f"Lỗi: Không tìm thấy file thực thi tại {exe_path}")
        return False
        
    try:
        # Dùng ZIP_LZMA để nén tốt hơn ZIP_DEFLATED (~50-60% nhỏ hơn)
        print(f"Đang nén với thuật toán LZMA (chặm hơn nhưng tỷ lệ nén cao hơn)...")
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_LZMA) as zipf:
            print(f"Đang nén {exe_path} vào {zip_path}...")
            zipf.write(exe_path, os.path.basename(exe_path))
        
        zip_size = os.path.getsize(zip_path) / (1024 * 1024)
        print(f"=== Nén file thành công! Kích thước file zip: {zip_size:.2f} MB ===")
        
        if zip_size > 100:
            print(f"[Cảnh báo] File zip vẫn lớn ({zip_size:.1f} MB). Cân nhắc tối ưu --excludes trong spec file.")
        
        # Copy sang QHTDautomation.zip (tên được dùng trong version.json download_url)
        import shutil
        shutil.copyfile(zip_path, qhtd_zip)
        print(f"=== Đã tạo QHTDautomation.zip ({zip_size:.2f} MB) ===")
        return True
    except Exception as e:
        print(f"Lỗi khi nén file: {e}")
        return False

def upload_progress(transferred, total):
    percentage = (transferred / total) * 100
    print(f"\rĐang tải lên: {transferred / (1024*1024):.2f}MB / {total / (1024*1024):.2f}MB ({percentage:.1f}%)", end='', flush=True)

def upload_to_server():
    print("=== Bắt đầu upload lên Server ===")
    hostname = "167.233.89.198"
    username = "root"
    password = "fJU9JtkbELfi"
    
    local_zip = os.path.join("dist", "C69Automation.zip")
    local_qhtd_zip = os.path.join("dist", "QHTDautomation.zip")
    remote_zip = "/root/storagon/static/C69Automation.zip"
    remote_qhtd_zip = "/root/storagon/static/QHTDautomation.zip"
    
    if not os.path.exists(local_zip):
        print(f"Lỗi: Không tìm thấy file zip để upload tại {local_zip}")
        return False
        
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        print(f"Đang kết nối tới {hostname}...")
        ssh.connect(hostname, username=username, password=password, timeout=30)
        print("Kết nối thành công!")
        
        # Đảm bảo thư mục static tồn tại trên server
        ssh.exec_command("mkdir -p /root/storagon/static")
        
        sftp = ssh.open_sftp()
        
        # Upload C69Automation.zip
        print(f"Bắt đầu upload SFTP tới {remote_zip}...")
        sftp.put(local_zip, remote_zip, callback=upload_progress)
        print("\n=== Tải lên C69Automation.zip thành công! ===")
        
        # Upload QHTDautomation.zip
        print(f"Bắt đầu upload SFTP tới {remote_qhtd_zip}...")
        sftp.put(local_qhtd_zip, remote_qhtd_zip, callback=upload_progress)
        print("\n=== Tải lên QHTDautomation.zip thành công! ===")
        
        sftp.close()
        return True
    except Exception as e:
        print(f"\nLỗi khi upload file: {e}")
        return False
    finally:
        ssh.close()

if __name__ == "__main__":
    if run_pyinstaller():
        if zip_executable():
            if upload_to_server():
                print("\n=== HOÀN THÀNH TOÀN BỘ QUY TRÌNH! ===")
                sys.exit(0)
    sys.exit(1)
