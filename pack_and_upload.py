import os
import zipfile
import sys
import subprocess

sys.stdout.reconfigure(encoding='utf-8')

def zip_files(zip_name, files_to_zip):
    print(f"Creating zip archive {zip_name}...")
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in files_to_zip:
            if os.path.exists(f):
                print(f"Adding {f} to zip...")
                zipf.write(f, os.path.basename(f))
            else:
                print(f"Warning: File not found: {f}")
    print("Zip archive created successfully!")

def main():
    dist_dir = "d:/Workspace/Python/QHTDautomation/dist"
    exe_path = os.path.join(dist_dir, "C69Automation.exe")
    updater_path = os.path.join(dist_dir, "c69update.exe")
    
    zip_path = os.path.join(dist_dir, "QHTDautomation.zip")
    
    if not os.path.exists(exe_path):
        print(f"Error: Build file not found: {exe_path}")
        sys.exit(1)
        
    # Zip the built files
    zip_files(zip_path, [exe_path, updater_path])
    
    # Run the upload script
    print("Running upload_tool.py to upload to C69 server...")
    upload_script = "d:/Workspace/Python/c69-backend/scratch/upload_tool.py"
    if os.path.exists(upload_script):
        result = subprocess.run([sys.executable, upload_script], capture_output=True, text=True, encoding='utf-8')
        print(result.stdout)
        if result.stderr:
            print("Errors:")
            print(result.stderr)
    else:
        print(f"Error: Upload script not found at {upload_script}")

if __name__ == "__main__":
    main()
