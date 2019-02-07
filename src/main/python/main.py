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

    def __init__(self, config, fel_mode_script=None):
        QThread.__init__(self)

        self.app_directory = ''

        if is_mac():
            self.app_directory = ''

        self.copy_directory = 'files'

        if is_linux() or is_mac():
            self.mount_dir = '/media/synchrony/allwinner'
        else:
            self.mount_dir = ''

        self.os_rootdir = '/media/{0}/SYSTEM/@'.format(getpass.getuser())

        self.config = config
        self.fel_mode_script = fel_mode_script

        self.files_dest = { 
                'u-boot.scr': self.mount_dir,
                'client-rhythm.json': os.path.join(self.os_rootdir, 'etc'),
                'client-rhythm-user.json': os.path.join(self.os_rootdir, 'etc'), 
                'client-rhythm': os.path.join(self.os_rootdir, 'usr/local/bin')
        }

        self.sudo_password = ''
        self.partition = None
        self.system_partition = None
        self.completed_before = False

    
    def initiate_fel_mode(self):

        os.makedirs(self.mount_dir, exist_ok=True)

        # Catching fel-mass-storage failure

        print(os.path.dirname(self.fel_mode_script))

        p = subprocess.Popen([self.fel_mode_script], cwd=os.path.dirname(self.fel_mode_script), 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        
        while True:
            if p.poll() is not None:
                break
            else:
                out, err = p.communicate('\n'.encode('ascii'))
                sys.stdout.write(str(out))
                sys.stdout.flush()


        return (True, 'Success')

    def mount(self):

        fdisk_cmd = ['fdisk', '-l']
        out = subprocess.check_output(fdisk_cmd)
        out = out.decode()
        lines = filter(lambda x : x.startswith('/dev'), out.split('\n'))
        print(out)

        self.partition = None
        self.system_partition = None

        for p in lines:
            print(p.split())
            part_info = p.split()
            partition_name, boot_flag, size  = part_info[0], part_info[1], part_info[5]
            if boot_flag == '*' and size == '255M':
                print('Mounting {0}'.format(partition_name))
                self.partition = partition_name 

        if self.partition:
            p = subprocess.Popen(['mount', '-t', 'vfat' , self.partition, self.mount_dir], 
                                 stdin=subprocess.PIPE)
            if p.wait() != 0:
                return (False, 'Failed to mount')
            else: 
                self.system_partition = self.partition[:-1] + str(int(self.partition[-1:]) + 1) 
                print('Mounting {0} as SYSTEM'.format(self.system_partition))
                p = subprocess.Popen(['udisksctl', 'mount', '--block-device', self.system_partition])

                if p.wait() != 0:
                    return (False, 'Failed to mount SYSTEM')
                
                print('Succeeded to mount SYSTEM')
            
            return (True, 'Success')

        return (False, 'Could not find device partition from output {0}'.format(out))

    def unmount(self):
        print('Unmounting {0} as SYSTEM'.format(self.system_partition))

        p = subprocess.Popen(['udisksctl', 'unmount', '--block-device', self.system_partition])
        if p.wait() != 0:
            return (False, 'Failed to unmount SYSTEM')

        p = subprocess.Popen(['umount', self.mount_dir], stdin=subprocess.PIPE)
        p.communicate()
        if p.wait() != 0:
            return (False, 'Failed to unmount')
        
        self.completed_before = True
        return (True, 'Finished with unmount')

    def download_files(self):
        os.makedirs(self.copy_directory, exist_ok=True)

        s3_bucket_url = self.config.s3_bucket_url

        try:
            self.progress_signal.emit('Downloading latest updates...', 0, 100)

            r = requests.get('{0}/latest-version'.format(s3_bucket_url))
            if r.status_code != 200:
                return (False, 'Failed to get latest updates')
            latest_version = r.content.strip().decode()

            for file_name, dest in self.files_dest.items():
                file_url = '{0}/{1}/{2}'.format(s3_bucket_url, latest_version, file_name)
                r = requests.get(file_url)
                if r.status_code == 200:
                    file_copy_dest = '{0}/{1}'.format(self.copy_directory, file_name)
                    with open(file_copy_dest, 'wb') as f:
                        f.write(r.content)
                    print('Downloaded {0}'.format(file_name))
                else:
                    print('Did not find or failed to download {0}'.format(file_url))
        except Exception as e:
            return (False, str(e))

        return (True, '')

    
    def copy_files(self):

        if not os.path.exists(self.copy_directory):
            return (False, 'The directory {0} does not exist'.format(self.copy_directory))

        print('Copying from directory {0}'.format(self.copy_directory))

        add_dir = lambda f : os.path.join(self.copy_directory, f)
        user = getpass.getuser()

        def check_file(file_loc): 
            if os.path.isfile(file_loc):
                return True
            else: 
                return False

        def copy_file_print(file_name, dest):
            print('Copying from {0} to {1}'.format(file_name, dest))

            try:
                shutil.copy(file_name, dest)
            except Exception as e:
                return (False, 'Copy failed from {0} to {1}: {2}'.format(file_name, dest, e))

            # p = subprocess.Popen(['cp', file_name, dest], 
            #         stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            # out, err = p.communicate() # '{0}\n'.format(self.sudo_password))
            # if out:
            #     print(str(out))
            # if err:
            #     print(err)
            # if p.wait() != 0:
            #     print()
            #     return -1
            return (True, '')

        for f, dest in self.files_dest.items():
            file_loc = add_dir(f)
            
            if check_file(file_loc):
                failed, msg = copy_file_print(file_loc, os.path.join(dest, f))
                if failed:
                    return (failed, msg)

        return (True, 'Success')

    def wait_with_progress(self, message, sec):
        counter = 0
        while counter <= sec:
            self.progress_signal.emit(message, counter, sec)
            QThread.sleep(1)
            counter += 1

    def run(self):

        success = False

        if self.completed_before:
            self.unplug_signal.emit()
        else:
            success, msg = self.download_files()    

        if is_linux() or is_mac():
            if success:
                success, msg = self.initiate_fel_mode()
        
        if success:
            self.wait_with_progress('Mounting the device...', 10)

        if success: 
            success, msg = self.mount()

        if success:
            success, msg = self.copy_files()

        if success:
            self.wait_with_progress('Copying files...', 45)

        if success:
            success, msg = self.unmount()
            self.wait_with_progress('Unmounting device...', 10)

        self.finish_signal.emit(success, msg)




class AppContext(ApplicationContext):

    def run(self):
        config_file = self.get_resource('config.json')
        config = json.loads(open(config_file).read())

        fel_mode_script = None
        if is_linux() or is_mac():
            fel_mode_script = self.get_resource('fel-mass-storage/start.sh')

        window = QMainWindow()
        version = self.build_settings['version']
        window.setWindowTitle('Synchrony Installer')
        window.resize(250, 150)

        layout = QVBoxLayout()

        self.install_handler = InstallHandler(config, fel_mode_script)

        self.install_button = QPushButton('Install')
        self.install_button.clicked.connect(self.clicked_install)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.install_handler.progress_signal.connect(self.update_progress)

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
            self.progress_bar.setFormat('Failed to update the device')

    def update_progress(self, current, done, total):
        self.progress_bar.setValue((done / total) * 100)
        self.progress_bar.setFormat('{0}'.format(current))

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

