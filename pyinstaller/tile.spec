# -*- mode: python -*-

block_cipher = None

import os
dirs = [os.path.abspath(d[0]) for d in os.walk(os.path.join('..', 'tile_generator', 'templates'))]
files = [(os.path.join(d,'*'), d) for d in dirs]

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
          name='tile',
          debug=False,
          strip=False,
          upx=False,
          runtime_tmpdir=None,
          console=True )
