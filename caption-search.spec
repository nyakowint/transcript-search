# -*- mode: python ; coding: utf-8 -*-

import sys

is_windows = sys.platform == 'win32'
is_macos = sys.platform == 'darwin'
is_linux = not is_windows and not is_macos

if is_windows:
    # pythonnet backs the WinForms/EdgeChromium backend and is reached through
    # clr, which the analyzer cannot follow.
    hiddenimports = ['clr_loader', 'pythonnet']
elif is_linux:
    # pywebview picks its GTK backend at runtime and the WebKit2/Soup versions
    # are chosen inside a try/except, so the typelibs have to be named here.
    hiddenimports = [
        'gi',
        'gi.repository.Gtk',
        'gi.repository.Gdk',
        'gi.repository.GLib',
        'gi.repository.Gio',
        'gi.repository.Soup',
        'gi.repository.WebKit2',
    ]
else:
    hiddenimports = []

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('build/ui', 'build/ui'),
        ('src/public/favicon.ico', 'src/public'),
    ],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6',
        'tkinter', 'matplotlib', 'numpy', 'pandas',
        'scipy', 'PIL', 'cv2', 'torch', 'tensorflow',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

# One-file build: binaries and datas are passed to EXE instead of a COLLECT, so
# there is a single executable rather than an exe plus an `_internal` directory.
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='transcript-search',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    # UPX mangles Mach-O binaries badly enough that they refuse to launch, and
    # is not usually present on Linux build machines either.
    upx=is_windows,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # .ico is Windows-only; converting it elsewhere would need Pillow.
    icon='src/public/favicon.ico' if is_windows else None,
)

if is_macos:
    # Finder will not launch a bare Unix executable, so macOS gets a .app
    # wrapper around that same one-file binary.
    app = BUNDLE(
        exe,
        name='Transcript Search.app',
        icon=None,
        bundle_identifier='com.github.transcript-search',
        info_plist={
            'NSHighResolutionCapable': True,
            'LSApplicationCategoryType': 'public.app-category.utilities',
        },
    )
