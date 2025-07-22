# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

# Source files from the Development directory (copied from Source)
source_files = [
    ('requirements.txt', '.'),
    ('worker_node.py', '.'),
    ('job_queue_manager.py', '.'),
    ('config.json', '.'),
    ('app_config.json', '.'),
    ('main_app.py', '.'),
    ('server.py', '.'),
    ('distributed_renderers.py', '.'),
    ('unified_app.py', '.'),
    ('server_config.json', '.'),
    ('worker_machines.json', '.'),
    ('worker_deployment_manager.py', '.'),
]

a = Analysis(
    ['setup_installer_simple.py'],
    pathex=[],
    binaries=[],
    datas=source_files,
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='RenderFarmSetup_Final',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='../logo.ico',
)