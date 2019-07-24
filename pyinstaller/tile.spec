# -*- mode: python -*-

# work-around for https://github.com/pyinstaller/pyinstaller/issues/4064
import distutils
if distutils.distutils_path.endswith('__init__.py'):
    distutils.distutils_path = os.path.dirname(distutils.distutils_path)

import os
import platform
import sys

block_cipher = None
arch = '64bit' if sys.maxsize > 2**32 else '32bit'

dirs = [os.path.abspath(d[0]) for d in os.walk(os.path.join('.', 'tile_generator', 'templates'))]
files = [(os.path.join(d,'*'), os.path.relpath(d)) for d in dirs]

a = Analysis(['tile_entrypoint.py'],
             pathex=['.'],
             binaries=[],
             datas=files,
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='tile_' + platform.system().lower() + '-' + arch,
          debug=False,
          strip=False,
          upx=False,
          runtime_tmpdir=None,
          console=True )
