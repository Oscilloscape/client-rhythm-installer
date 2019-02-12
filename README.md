This installer uses fbs to build cross platform PyQt5 Python application.

For more info, see: https://build-system.fman.io/pyqt5-tutorial

As of now, only Python 3.6 is supported for fbs.

##Installation and Build

Use the supported Python v3.6 and PyInstaller 3.4 (as of now)

To install PyInstaller v3.4, run

pip3 install pyinstaller==3.4 

Install fbs and PyQt5 packages

pip3 install fbs PyQt5

###Finding the fbs and pyinstaller executable

fbs and pyinstaller binary are often not installed in the path. Look for the installation location using

python3 -m site --user-base

To run the executable, run: 

fbs run

Mac OS

Install Python 3.6 using below link (instead of brew due to difficulty with versioning): 
https://www.python.org/downloads/release/python-360/

You may need to downgrade pip to get correct version of PyInstaller (3.4 as of now)

If so, do as below:
https://stackoverflow.com/questions/44740792/pyinstaller-no-module-named-pyinstaller

Make symbolic link of PyInstaller as below:
ln -s /Library/Frameworks/Python.framework/Versions/3.6/bin/pyinstaller /usr/local/bin/pyinstaller

open -a Installer.app in target
