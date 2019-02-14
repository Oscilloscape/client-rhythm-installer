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

    def __init__(self, config, fel_mode_script=None, sunxi_fel=None):
        QThread.__init__(self)

        self.copy_directory = 'files'
        if is_mac():
            self.copy_directory = '/Library/Application Support/synchrony/files'

        if is_linux():
            self.mount_dir = '/media/synchrony/allwinner'
        elif is_mac():
            self.mount_dir = ''
            self.system_mount_dir = ''
        else:
            self.mount_dir = ''

        self.os_rootdir = '/media/{0}/SYSTEM/@'.format(getpass.getuser())

        self.config = config
        self.fel_mode_script = fel_mode_script
        self.sunxi_fel = sunxi_fel

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

        if is_linux() or is_mac(): 

            p = subprocess.Popen([self.fel_mode_script],
                                  cwd=os.path.dirname(self.fel_mode_script),
                                  env={ 'SUNXI_FEL': self.sunxi_fel })

            if p.wait() != 0:
                return (False, 'Failed to engage in FEL mode')
        else:
            
            p = subprocess.Popen([self.fel_mode_script],
                                 cwd=os.path.dirname(self.fel_mode_script))

            if p.wait() != 0:
                return (False, 'Failed to engage in FEL mode')


        return (True, 'Successful engaged in FEL mode')


    def mount(self):
        
        self.partition = None
        self.system_partition = None
        
        if is_linux():
            fdisk_cmd = ['fdisk', '-l']
            out = subprocess.check_output(fdisk_cmd)
            out = out.decode()
            lines = filter(lambda x : x.startswith('/dev'), out.split('\n'))
            print(out)
        
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

                self.system_partition = self.partition[:-1] + str(int(self.partition[-1:]) + 1)
                print('Mounting {0} as SYSTEM'.format(self.system_partition))
                p = subprocess.Popen(['udisksctl', 'mount', '--block-device', self.system_partition])
                
                if p.wait() != 0:
                    return (False, 'Failed to mount SYSTEM')

            return (True, 'Successfully mounted the device')
                        
        elif is_mac():
            out = subprocess.check_output(shlex.split('diskutil list'))
            out = out.decode()
            disks = out.split('/dev/')
            print(disks)
            diskutil_lines = out.split('\n')
            print(diskutil_lines)
            for i, l in enumerate(diskutil_lines):
                parts = list(filter(None, l.split(' ')))
                print(parts)
                if l.startswith('/dev') and parts[1].contains('external') and i + 4 < len(diskutil_lines):
                    current_disk = l.split(' ')[0]
                    print(current_disk)
                    main_disk_line = diskutil_lines[i + 2]
                    boot_part_line = diskutil_lines[i + 3]
                    linux_part_line = diskutil_lines[i + 4]
                    _, _, disk_size, _ = main_disk_line
                    _, boot_name, boot_size, boot_id = boot_part_line
                    _, linux_name, _, linux_id = linux_part_line
                    print(disk_size, boot_name, boot_size, linux_name, linux_id)

            if self.partition and self.system_partition:
                out = subprocess.check_output(
                    shlex.split('sudo mount -t msdos {0} {1}'.format(self.partition, self.mount_dir)))

                out = out.decode()

                print(out)

                out = subprocess.check_output(
                    shlex.split('sudo mount -t msdos {0} {1}'.format(self.system_partition, self.system_mount_dir)))

                out = out.decode()

                print('Succeeded to mount SYSTEM')
            
                return (True, 'Success')

        else:
            pass
  

        return (False, 'Could not find device partition from output {0}'.format(out))

    def unmount(self):
        print('Unmounting {0} as SYSTEM'.format(self.system_partition))
        
        if is_linux():

            p = subprocess.Popen(['udisksctl', 'unmount', '--block-device', self.system_partition])
            if p.wait() != 0:
                return (False, 'Failed to unmount SYSTEM')

            p = subprocess.Popen(['umount', self.mount_dir], stdin=subprocess.PIPE)
            p.communicate()
            if p.wait() != 0:
                return (False, 'Failed to unmount')

        elif is_mac():
            out = subprocess.check_output(shlex.split('diskutil unmount {0}'.format(self.partition)))
            out = out.decode()

        else:
            pass
        
        self.completed_before = True
        return (True, 'Finished with unmount')

    def download_files(self):
        #os.makedirs(self.copy_directory, exist_ok=True)

        s3_bucket_url = self.config.s3_bucket_url

        # try:
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
                self.progress_signal.emit('Downloaded {0}'.format(file_name), 0, 100)
            else:
                print('Did not find or failed to download {0}'.format(file_url))
        # except Exception as e:
        #    return (False, str(e))

        return (True, '')

    
    def copy_files(self):

        if not os.path.exists(self.copy_directory):
            return (False, 'The directory {0} does not exist'.format(self.copy_directory))

        print('Copying from directory {0}'.format(self.copy_directory))

        add_dir = lambda f : os.path.join(self.copy_directory, f)
        user = getpass.getuser()

        def copy_file_print(file_name, dest):
            print('Copying from {0} to {1}'.format(file_name, dest))

            try:
                shutil.copy(file_name, dest)
            except Exception as e:
                return (False, 'Copy failed from {0} to {1}: {2}'.format(file_name, dest, e))

            return (True, '')

        for f, dest in self.files_dest.items():
            file_loc = add_dir(f)
            
            if os.path.isfile(file_loc):
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

    def report_progress(self, message):
        self.progress_signal.emit(message, 0, 1)

    def run(self):

        success = False

        if self.completed_before:
            self.unplug_signal.emit()
        else:
            pass
            # success, msg = self.download_files()

        self.report_progress('hello')

        success = True

        if success:
            self.report_progress('Initiating the mounting of the device...')
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
        config_file, config = None, None
        try:
            config_file = self.get_resource('config.json')
            config = json.loads(open(config_file).read())
        except:
            pass

        fel_mode_script = None
        if is_linux() or is_mac():
            fel_mode_script = self.get_resource('fel-mass-storage/start.sh')
        else:
            fel_mode_script = self.get_resource('fel-mass-storage/start.bat')

        sunxi_fel = None
        if is_linux() or is_mac():
            sunxi_fel = self.get_resource('sunxi-fel')

        window = QMainWindow()
        version = self.build_settings['version']
        window.setWindowTitle('Synchrony Installer')
        window.resize(250, 150)

        layout = QVBoxLayout()

        if not config:
            errorBox = QMessageBox()
            errorBox.critical(0, 'Failed to find config file')

        self.install_handler = InstallHandler(config, fel_mode_script, sunxi_fel)

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

        if is_mac():
            self.install_handler.finish_signal.connect(self.update_progress_text)

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
    
    def update_progress_text(self, current, done, total):
        self.progress_status.showMessage(current)

    def update_progress_text(self, success, msg):
        self.progress_status.showMessage(msg)

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

