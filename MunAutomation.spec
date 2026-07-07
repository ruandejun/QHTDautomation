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
    # Loại các DLL đồ hoạ/WebEngine khỏi UPX — nén UPX lên các DLL này (ANGLE giả lập
    # OpenGL ES qua DirectX, D3D compiler, chính Qt WebEngine/Chromium) là nguyên nhân
    # phổ biến gây lỗi rendering (nhấp nháy, giật hình) CHỈ xảy ra ở bản exe đã đóng gói
    # UPX — vì lúc chạy code nguồn dùng thẳng DLL gốc chưa nén nên không gặp lỗi này.
    upx_exclude=[
        'Qt6WebEngineCore.dll',
        'Qt6WebEngineWidgets.dll',
        'Qt6Gui.dll',
        'Qt6Quick.dll',
        'libEGL.dll',
        'libGLESv2.dll',
        'd3dcompiler_47.dll',
        'opengl32sw.dll',
        'python3*.dll',
        'vcruntime*.dll',
    ],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='MunAutomationDesktop/icon.ico',
)
