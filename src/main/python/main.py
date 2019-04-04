#!/usr/bin/python3 

from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import * 
from PyQt5.QtCore import QTime, QThread, pyqtSignal

import requests
from elevate import elevate

# from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout, QMainWindow

from subprocess import Popen, PIPE, STDOUT
import subprocess
import sys
from sys import platform
import os
import re
import getpass
import time
from shutil import copyfile
from threading import Thread
import shutil
import json
import shlex

def is_linux():
    return platform == 'linux' or platform == 'linux2'

def is_mac(): 
    return platform == 'darwin'

def is_windows():
    return platform == 'win32'

class InstallHandler(QThread):

    finish_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(str, int, int)
    unplug_signal = pyqtSignal()

    def __init__(self, fel_mode_script=None, sunxi_fel=None):
        QThread.__init__(self)

        self.fel_mode_script = fel_mode_script
        self.sunxi_fel = sunxi_fel

    
    def initiate_fel_mode(self):

        os.makedirs(self.mount_dir, exist_ok=True)

        p = None

        if is_linux() or is_mac(): 
            p = subprocess.Popen([self.fel_mode_script],
                                  cwd=os.path.dirname(self.fel_mode_script),
                                  env={ 'SUNXI_FEL': self.sunxi_fel })
        else:
            
            p = subprocess.Popen([self.fel_mode_script],
                                 cwd=os.path.dirname(self.fel_mode_script))

        if p:
            if p.wait() != 0:
                return (False, 'Failed to engage in FEL mode')
        else:
            return (False, 'Invalid operating system')

        return (True, 'Successful engaged in FEL mode')


    def wait_with_progress(self, message, sec):
        counter = 0
        while counter <= sec:
            self.progress_signal.emit(message, counter, sec)
            QThread.sleep(1)
            counter += 1

    def report_progress(self, message):
        print(message)
        self.progress_signal.emit(message, 0, 1)


    def run(self):

        success = False

        if self.completed_before:
            self.unplug_signal.emit()
        else:
            pass

        self.report_progress('hello')

        success = True

        if success:
            self.report_progress('Initiating the mounting of the device...')
            success, msg = self.initiate_fel_mode()

        self.finish_signal.emit(success, msg)




class AppContext(ApplicationContext):

    def run(self):

        fel_mode_script = None
        if is_linux() or is_mac():
            fel_mode_script = self.get_resource('fel-mass-storage/start.sh')
        else:
            fel_mode_script = self.get_resource('fel-mass-storage/start.bat')

        # For windows, sunxi-fel.exe is located in fel-mass-storage/win32
        sunxi_fel = None
        if is_linux() or is_mac():
            sunxi_fel = self.get_resource('sunxi-fel')

        window = QMainWindow()
        version = self.build_settings['version']
        window.setWindowTitle('Synchrony Installer')
        window.setFixedSize(250, 100)

        layout = QVBoxLayout()

        self.install_handler = InstallHandler(fel_mode_script, sunxi_fel)

        self.install_button = QPushButton('Install')
        self.install_button.clicked.connect(self.clicked_install)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.install_handler.progress_signal.connect(self.update_progress)
        
        if is_mac():
            self.progress_status = QStatusBar()
            self.install_handler.progress_signal.connect(self.update_progress_text)
            window.setStatusBar(self.progress_status)

        self.install_handler.unplug_signal.connect(self.prompt_unplug)

        layout.addWidget(self.install_button)
        layout.addWidget(self.progress_bar)

        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        central_widget.setLayout(layout)

        window.show()
        return self.app.exec_()

    def clicked_install(self):
        self.install_button.setEnabled(False)
        self.install_handler.start()
        self.install_handler.finish_signal.connect(self.finished_install)
        self.install_handler.finish_signal.connect(self.clear_progress_bar)

    def finished_install(self, success, msg):
        print('Success: {0}'.format(success))
        print(msg)
        self.install_button.setEnabled(True)

    def clear_progress_bar(self, success, msg):
        if success:
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat('Finished updating the device')
        else:
            self.progress_bar.setValue(0)
            self.progress_bar.setFormat('Failed to update the device:\n {0}'.format(msg))

    def update_progress(self, current, done, total):
        self.progress_bar.setValue((done / total) * 100)
        self.progress_bar.setFormat('{0}'.format(current))
    
    def update_progress_text(self, current, done, total):
        self.progress_status.showMessage(current)

    def prompt_unplug(self):
        prompt = QMessageBox()
        prompt.setIcon(QMessageBox.Warning)
        prompt.setText('Plug out the device and plug it back in fel-mode.')
        prompt.setStandardButtons(QMessageBox.Ok)

        self.install_handler.completed_before = False


if __name__ == '__main__':
    if is_linux():
        elevate(graphical=False)
    else:
        elevate()

    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)

