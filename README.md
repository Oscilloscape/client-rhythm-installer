This installer uses fbs to build cross platform PyQt5 Python application.

For more info, see: https://build-system.fman.io/pyqt5-tutorial

As of now, only Python 3.6 is supported for fbs.

## Installation and Build

Use the supported Python v3.6 and PyInstaller 3.4 (as of now)

To install PyInstaller v3.4, run

pip3 install pyinstaller==3.4 

Install fbs and PyQt5 packages

pip3 install fbs PyQt5

### Finding the fbs and pyinstaller executable

fbs and pyinstaller binary are often not installed in the path. Look for the installation location using

python3 -m site --user-base

To run the executable, first initialize the config file in src/main/resources/base by copying the config.json.example file to config.json.

Then, run:

fbs run

if error occurs do the following (works for Mac):

pip uninstall fbs

pip install fbs==0.8.2

pip install reuqests elevate

fbs clean

now you can run: fbs run

this error occurs because of a bug in the updated fbs version 0.8.3

## Mac OS

Install Python 3.6 using below link (instead of brew due to difficulty with versioning): 
https://www.python.org/downloads/release/python-360/

You may need to downgrade pip to get correct version of PyInstaller (3.4 as of now)

If so, do as below:
https://stackoverflow.com/questions/44740792/pyinstaller-no-module-named-pyinstaller

Make symbolic link of PyInstaller as below:
ln -s /Library/Frameworks/Python.framework/Versions/3.6/bin/pyinstaller /usr/local/bin/pyinstaller

open -a Installer.app in target

## Windows

Install Windows 10 SDK from: https://dev.windows.com/en-us/downloads/windows-10-sdk
Note: You might have to restart the command prompt to get the fbs to work.

## Sunxi-fel

Each OS requires the executable sunxi-fel to engage the device into fel-mode and make it available for mounting.

Currently, sunxi-fel for each OS is in the src/resources directory.

Below are the instructions if the sunxi-fel needs to get compiled again.

For Linux and Mac, one just needs to compile the sunxi-tools as instructed in the repo.

For Windows, a bit of cross compiling is needed. Below are the instructions.

1. Install Mingw (compiler for cross-compiling)
sudo apt-get install gcc-mingw-w64-x86-64 g++-mingw-w64-x86-64 
2. Go to the build-script repo (original author eperie) and download the script: build-sunxi-tools-mingw64.sh
3. Edit the script to remove the part of cloning the sunxi-tools repo, as v1.5 version of the sunxi-tools are needed. Move the v1.5 sunxi-tools directory into the same directory as the script.
4. Run the script. 


