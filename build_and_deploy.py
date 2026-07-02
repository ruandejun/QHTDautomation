"""
build_and_deploy.py — Build, nén và upload C69Automation lên Cloudflare R2 CDN.

SETUP CLOUDFLARE R2 (làm 1 lần):
----------------------------------
1. Đăng nhập https://dash.cloudflare.com → chọn "R2 Object Storage"
2. Tạo bucket tên: "c69-releases" (hoặc tên tùy ý)
3. Vào Settings → Public Access → bật "Allow Public Access"
   → Sao chép "Public Bucket URL" (dạng: https://pub-xxxx.r2.dev/...)
4. Tạo API Token:
   - Vào Profile → API Tokens → Create Token
   - Chọn template "R2 Token" → Edit Object Storage
   - Permissions: Object:Read, Object:Write, Bucket:Read
   - Sao chép: Account ID, Token
5. Điền vào phần CONFIG bên dưới.

CÁCH DÙNG:
----------
  python build_and_deploy.py          # Full: build + zip + upload
  python build_and_deploy.py --zip    # Chỉ zip + upload (không build lại)
  python build_and_deploy.py --upload # Chỉ upload file zip đã có
"""

import os
import sys
import subprocess
import zipfile
import hashlib
import json
import time

# Tự động load biến từ .env trong thư mục của script này
_here = os.path.dirname(os.path.abspath(__file__))
_env_path = os.path.join(_here, ".env")
try:
    from dotenv import load_dotenv
    if os.path.exists(_env_path):
        load_dotenv(dotenv_path=_env_path)
except ImportError:
    # Manual fallback nếu python-dotenv chưa cài
    if os.path.exists(_env_path):
        with open(_env_path) as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith('#') and '=' in _line:
                    _k, _v = _line.split('=', 1)
                    os.environ.setdefault(_k.strip(), _v.strip())

sys.stdout.reconfigure(encoding='utf-8')

# ============================================================
# CONFIG — Điền thông tin Cloudflare R2 của bạn tại đây
# ============================================================
CLOUDFLARE_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "")        # Lấy từ Cloudflare dashboard
CLOUDFLARE_API_TOKEN  = os.environ.get("CF_API_TOKEN",  "")        # R2 API Token
R2_BUCKET_NAME        = os.environ.get("CF_R2_BUCKET",  "c69-releases")

# URL public của bucket (sau khi bật Public Access trên dashboard)
# Dạng: https://pub-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX.r2.dev
R2_PUBLIC_URL         = os.environ.get("CF_R2_PUBLIC_URL", "")

# Fallback: server riêng (dùng khi chưa có R2 config)
FALLBACK_SFTP_HOST    = "167.233.89.198"
FALLBACK_SFTP_USER    = "root"
FALLBACK_SFTP_PASS    = "fJU9JtkbELfi"
FALLBACK_REMOTE_PATH  = "/root/storagon/static"

# Ten file zip upload len R2 (co version de bypass CDN cache)
ZIP_FILENAME = "QHTDautomation-v2.zip"
# ============================================================


def run_pyinstaller(spec_path="MunAutomation.spec", label="C69Automation"):
    print(f"=== Bắt đầu chạy PyInstaller: {label} ===")
    if not os.path.exists(spec_path):
        print(f"Lỗi: Không tìm thấy file spec tại {spec_path}")
        return False

    venv_pyinstaller = os.path.join(".venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(venv_pyinstaller):
        venv_pyinstaller = "pyinstaller"

    cmd = [venv_pyinstaller, spec_path, "--clean"]
    print(f"Chạy: {' '.join(cmd)}")

    try:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8'
        )
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        rc = process.poll()
        if rc == 0:
            print(f"=== {label}: Đóng gói thành công! ===")
            return True
        else:
            print(f"=== {label}: Thất bại (exit code {rc}) ===")
            return False
    except Exception as e:
        print(f"Lỗi khi chạy PyInstaller: {e}")
        return False


def zip_executable():
    """Nén cả C69Automation.exe và c69update.exe vào cùng 1 file zip."""
    main_exe    = os.path.join("dist", "C69Automation.exe")
    updater_exe = os.path.join("dist", "c69update.exe")
    zip_path    = os.path.join("dist", ZIP_FILENAME)

    if not os.path.exists(main_exe):
        print(f"Lỗi: Không tìm thấy {main_exe}")
        return None

    if not os.path.exists(updater_exe):
        print(f"  [Cảnh báo] Không tìm thấy c69update.exe tại {updater_exe}")
        print(f"  => Chỉ đóng gói C69Automation.exe")
        updater_exe = None

    try:
        print("Đang nén với thuật toán LZMA...")
        t0 = time.time()
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_LZMA) as zipf:
            # Exe chính
            size_main = os.path.getsize(main_exe) / 1024 / 1024
            print(f"  + C69Automation.exe ({size_main:.1f} MB)")
            zipf.write(main_exe, "C69Automation.exe")

            # Updater (nếu tồn tại)
            if updater_exe:
                size_upd = os.path.getsize(updater_exe) / 1024 / 1024
                print(f"  + c69update.exe ({size_upd:.1f} MB)")
                zipf.write(updater_exe, "c69update.exe")

        zip_size = os.path.getsize(zip_path) / 1024 / 1024
        elapsed  = time.time() - t0
        print(f"=== Nén thành công! {zip_size:.1f} MB | {elapsed:.0f}s ===")
        return zip_path
    except Exception as e:
        print(f"Lỗi khi nén file: {e}")
        return None


def compute_sha256(filepath):
    """Tính checksum SHA256 để verify tải về."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────
# CLOUDFLARE R2 UPLOAD (S3-compatible API)
# ─────────────────────────────────────────────────────────────

def _r2_upload_boto3(zip_path: str) -> str | None:
    """Upload qua boto3 (S3-compatible). Trả về public URL nếu thành công."""
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        print("  [R2] boto3 chưa cài. Đang cài: pip install boto3...")
        os.system(f"{sys.executable} -m pip install boto3 -q")
        import boto3
        from botocore.config import Config

    endpoint = f"https://{CLOUDFLARE_ACCOUNT_ID}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=CLOUDFLARE_API_TOKEN.split(":")[0] if ":" in CLOUDFLARE_API_TOKEN else CLOUDFLARE_API_TOKEN,
        aws_secret_access_key=CLOUDFLARE_API_TOKEN.split(":")[1] if ":" in CLOUDFLARE_API_TOKEN else CLOUDFLARE_API_TOKEN,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )

    file_size = os.path.getsize(zip_path)
    print(f"  Bắt đầu upload lên R2 bucket [{R2_BUCKET_NAME}]...")
    print(f"  File: {os.path.basename(zip_path)} ({file_size / 1024 / 1024:.1f} MB)")

    uploaded = [0]
    start_time = [time.time()]

    def progress(bytes_transferred):
        uploaded[0] += bytes_transferred
        pct = uploaded[0] / file_size * 100
        speed = uploaded[0] / (time.time() - start_time[0] + 0.001) / 1024 / 1024
        print(
            f"\r  {uploaded[0]/1024/1024:.1f} MB / {file_size/1024/1024:.1f} MB "
            f"({pct:.0f}%) — {speed:.1f} MB/s",
            end="", flush=True
        )

    s3.upload_file(
        zip_path,
        R2_BUCKET_NAME,
        ZIP_FILENAME,
        Callback=progress,
        ExtraArgs={"ContentType": "application/zip"},
    )
    print(f"\n  Upload hoàn tất!")

    public_url = f"{R2_PUBLIC_URL.rstrip('/')}/{ZIP_FILENAME}" if R2_PUBLIC_URL else None
    return public_url


def upload_to_r2(zip_path: str) -> str | None:
    """
    Upload file lên Cloudflare R2.
    Trả về public URL hoặc None nếu thất bại.
    """
    if not CLOUDFLARE_ACCOUNT_ID or not CLOUDFLARE_API_TOKEN:
        print("  [R2] Chưa cấu hình CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN.")
        print("  Hãy set biến môi trường hoặc chỉnh CONFIG trong file này.")
        return None

    print("=== Upload lên Cloudflare R2 ===")
    try:
        url = _r2_upload_boto3(zip_path)
        return url
    except Exception as e:
        print(f"\n  [R2] Upload thất bại: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# FALLBACK: Upload lên server riêng qua SFTP
# ─────────────────────────────────────────────────────────────

def upload_to_server_sftp(zip_path: str) -> str | None:
    """Upload lên server riêng qua SFTP (fallback)."""
    import paramiko
    print(f"=== Fallback: Upload SFTP lên {FALLBACK_SFTP_HOST} ===")

    filename = os.path.basename(zip_path)
    remote_path = f"{FALLBACK_REMOTE_PATH}/{filename}"

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        ssh.connect(FALLBACK_SFTP_HOST, username=FALLBACK_SFTP_USER,
                    password=FALLBACK_SFTP_PASS, timeout=30)
        sftp = ssh.open_sftp()
        file_size = os.path.getsize(zip_path)

        def progress(transferred, total):
            pct = transferred / total * 100
            speed = transferred / max(1, time.time() - t0) / 1024 / 1024
            print(f"\r  {transferred/1024/1024:.1f} MB / {total/1024/1024:.1f} MB "
                  f"({pct:.0f}%) — {speed:.1f} MB/s", end="", flush=True)

        t0 = time.time()
        sftp.put(zip_path, remote_path, callback=progress)
        print(f"\n  Upload SFTP thành công!")

        # Copy sang QHTDautomation.zip (backward compat)
        if filename != ZIP_FILENAME:
            qhtd_path = f"{FALLBACK_REMOTE_PATH}/{ZIP_FILENAME}"
            ssh.exec_command(f'cp "{remote_path}" "{qhtd_path}"')

        sftp.close()
        return f"https://c69.us/static/{ZIP_FILENAME}"
    except Exception as e:
        print(f"\n  SFTP upload thất bại: {e}")
        return None
    finally:
        ssh.close()


# ─────────────────────────────────────────────────────────────
# CẬP NHẬT version.json local + server
# ─────────────────────────────────────────────────────────────

def update_version_json(download_url: str, version: str | None = None):
    """Cập nhật version.json với download_url mới (sau khi upload lên CDN)."""
    vf = "version.json"
    with open(vf, "r", encoding="utf-8") as f:
        data = json.load(f)

    if version:
        data["version"] = version
    data["download_url"] = download_url

    with open(vf, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    print(f"  version.json cập nhật → download_url: {download_url}")

    # Push lên server backend để API /api/tool-version/ trả URL mới
    try:
        import paramiko
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(FALLBACK_SFTP_HOST, username=FALLBACK_SFTP_USER,
                    password=FALLBACK_SFTP_PASS, timeout=20)
        sftp = ssh.open_sftp()
        sftp.put(vf, "/root/storagon/version.json")
        sftp.close()
        ssh.close()
        print("  version.json đồng bộ lên server thành công!")
    except Exception as e:
        print(f"  [Cảnh báo] Không thể sync version.json lên server: {e}")
        print("  Hãy chạy: git push và deploy thủ công.")


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build & Deploy C69Automation")
    parser.add_argument("--build",  action="store_true", help="Chỉ build (PyInstaller)")
    parser.add_argument("--zip",    action="store_true", help="Chỉ zip + upload")
    parser.add_argument("--upload", action="store_true", help="Chỉ upload (dùng zip đã có)")
    parser.add_argument("--version", default=None,       help="Ghi đè version (vd: 2.0.2)")
    parser.add_argument("--sftp",   action="store_true", help="Ép dùng SFTP thay vì R2")
    args = parser.parse_args()

    # Mặc định: full pipeline
    do_build  = args.build  or not (args.zip or args.upload)
    do_zip    = args.zip    or not (args.build or args.upload)
    do_upload = args.upload or not (args.build or args.zip) or args.zip

    zip_path = os.path.join("dist", ZIP_FILENAME)

    # 1. Build
    if do_build:
        # 1a. Build c69update.exe trước (nhỏ, nhanh ~30s)
        print("\n--- Bước 1/2: Build c69update.exe ---")
        ok_updater = run_pyinstaller("c69update.spec", label="c69update")
        if not ok_updater:
            print("[Cảnh báo] Build c69update.exe thất bại — tiếp tục build main app...")

        # 1b. Build C69Automation.exe chính
        print("\n--- Bước 2/2: Build C69Automation.exe ---")
        if not run_pyinstaller("MunAutomation.spec", label="C69Automation"):
            sys.exit(1)


    # 2. Zip
    if do_zip:
        result = zip_executable()
        if not result:
            sys.exit(1)
        zip_path = result

    # 3. Upload
    if do_upload:
        if not os.path.exists(zip_path):
            print(f"Lỗi: Không tìm thấy {zip_path}")
            sys.exit(1)

        sha256 = compute_sha256(zip_path)
        print(f"  SHA256: {sha256}")

        # Thử R2 trước, fallback SFTP
        download_url = None
        if not args.sftp and CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN:
            download_url = upload_to_r2(zip_path)

        if download_url is None:
            print("  Dùng fallback SFTP...")
            download_url = upload_to_server_sftp(zip_path)

        if download_url:
            print(f"\n✅ File có thể tải tại: {download_url}")
            update_version_json(download_url, args.version)
            print("\n=== HOÀN THÀNH TOÀN BỘ QUY TRÌNH! ===")
        else:
            print("\n❌ Upload thất bại hoàn toàn.")
            sys.exit(1)


if __name__ == "__main__":
    main()
