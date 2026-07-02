# -*- mode: python ; coding: utf-8 -*-
# Spec file tối ưu kích thước: loại bỏ các Qt module không sử dụng

a = Analysis(
    ['MunAutomationDesktop\\main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('MunAutomationDesktop/style.qss', '.'),
        ('MunAutomationDesktop/icon.png', '.'),
        ('MunAutomationDesktop/mun_anti_browser/inject_scripts', 'mun_anti_browser/inject_scripts'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=1,  # Tối ưu bytecode Python (loại bỏ assert và docstring)
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='C69Automation',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='MunAutomationDesktop/icon.ico',
)
