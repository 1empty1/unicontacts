import PyInstaller.__main__
import customtkinter
import os
import sys

ctk_path = os.path.dirname(customtkinter.__file__)
path_separator = ';' if os.name == 'nt' else ':'

pyinstaller_args = [
    'main.py',
    '--name=UniversityPhoneBook',
    '--onefile',
    '--noconsole',
    '--windowed',
    f'--add-data=isrgrootx1.pem{path_separator}.',
    f'--add-data={ctk_path}{path_separator}customtkinter',
    '--icon=NONE',
    '--clean',
    '--hidden-import=cryptography',
    '--hidden-import=cryptography.hazmat.bindings._openssl',
    '--hidden-import=cryptography.hazmat.bindings._rust',
    '--hidden-import=cryptography.hazmat.bindings.openssl',
    '--hidden-import=cryptography.hazmat.primitives',
    '--hidden-import=cryptography.hazmat.backends.openssl',
    '--hidden-import=matplotlib',
    '--hidden-import=matplotlib.backends.backend_tkagg',
    '--hidden-import=pymysql',
    '--hidden-import=openpyxl',
    '--hidden-import=openpyxl.styles',
    '--hidden-import=openpyxl.utils',
]

PyInstaller.__main__.run(pyinstaller_args)