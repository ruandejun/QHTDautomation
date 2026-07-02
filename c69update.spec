# -*- mode: python ; coding: utf-8 -*-
"""
c69update.spec — Build c69update.exe (standalone updater with tkinter UI)
"""
import sys

a = Analysis(
    ['MunAutomationDesktop/c69update.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'psutil',
        'tkinter',
        'tkinter.ttk',
        '_tkinter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Loại bỏ toàn bộ GUI frameworks nặng
        'PyQt6', 'PyQt5', 'PySide6', 'PySide2',
        'wx', 'gi',
        # Loại bỏ scientific libs
        'numpy', 'pandas', 'scipy', 'matplotlib',
        'PIL', 'Pillow',
        # Loại bỏ network libs không cần
        'selenium', 'requests', 'urllib3', 'certifi',
        'cryptography', 'paramiko',
        'boto3', 'botocore',
        # Loại bỏ misc
        'pydub', 'tqdm', 'pytelegrambotapi',
        'undetected_chromedriver', 'selenium_stealth',
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='c69update',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,       # Ẩn console, chỉ hiện UI window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
