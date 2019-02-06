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



def is_linux():
    return platform == 'linux' or platform == 'linux2'

def is_mac(): 
    return platform == 'darwin'

def is_windows():
    return platform == 'win32'

class InstallHandler(QThread):

    finish_signal = pyqtSignal(bool, str)
    progress_signal = pyqtSignal(str, int, int)

    def __init__(self):
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
        
        fel_mass_dir = '/home/helmholtz/fel-mass-storage'.format(getpass.getuser())
        if not os.path.exists(fel_mass_dir):
            return (False, 'Cant find fel-mass-storage dir at {0}'.format(fel_mass_dir))

        if not os.path.exists(self.mount_dir):
            os.mkdir(self.mount_dir)

        # p = subprocess.Popen(['sudo', '-S', 'mkdir', '-p', self.mount_dir], stdin=subprocess.PIPE)
        #p.communicate('{0}\n'.format(sudo_password))
        #if p.wait() != 0:
        #    return (False, 'Failed to make directory {0}'.format(self.mount_dir)) 

        # Catching fel-mass-storage failure

        p = subprocess.Popen(['./start.sh'], cwd=fel_mass_dir, 
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
        success, message = self.initiate_fel_mode()

        if not success:
            return (False, "Failed to initiate fel mode")

        fdisk_cmd = ['fdisk', '-l']
        #p = subprocess.Popen(fdisk_cmd, stdout=subprocess.PIPE, stderr = subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
        
        #out = ''
        # try:
        #     out = subprocess.check_output(fdisk_cmd).strip()
        # except OSError as e:
        #     return (False, str(e))
        out = subprocess.check_output(fdisk_cmd)
        #out, err =  p.communicate() # '{0}\n'.format(sudo_password).encode('ascii'))
        # out = subprocess.check_output(fdisk_cmd).strip()
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
            # p.communicate('{0}\n'.format(self.sudo_password))
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

        p = subprocess.Popen(['sudo', '-S', 'umount', self.mount_dir], stdin=subprocess.PIPE)
        p.communicate('{0}\n'.format(self.sudo_password))
        if p.wait() != 0:
            return (False, 'Failed to unmount')
        
        self.completed_before = True
        return (True, 'Finished with unmount')

    def download_files(self):
        if not os.path.exists(self.copy_directory):
            os.mkdir(self.copy_directory)

        # get list of latest files

        # requests.get('')

        # download into 

        return (True, '')

    
    def copy_files(self):

        if not os.path.exists(dir_name):
            return (False, 'The directory {0} does not exist'.format(dir_name))

        print('Copying from directory {0}'.format(dir_name))

        add_dir = lambda f : os.path.join(dir_name, f)
        user = getpass.getuser()

        def check_file(file_loc): 
            if os.path.isfile(file_loc):
                return True
            else: 
                print('Could not find file {0}'.format(file_loc))
                return False

        def copy_file_print(file_name, dest):
            print('Copying from {0} to {1}'.format(file_name, dest))
            p = subprocess.Popen(['sudo', '-S', 'cp', file_name, dest], 
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
            out, err = p.communicate() # '{0}\n'.format(self.sudo_password))
            if out:
                print(str(out))
            if err:
                print(err)
            if p.wait() != 0:
                print('Copy failed from {0} to {1}'.format(file_name, dest))
                return -1
            return 0

        for f, dest in self.files_dest.iteritems():
            file_loc = add_dir(f)
            
            if check_file(file_loc):
                failed = copy_file_print(file_loc, os.path.join(dest, f))
                if failed:
                    return

        return (True, 'Success')

    def wait_with_progress(self, message, sec):
        counter = 0
        while counter < sec:
            self.progress_signal.emit(message, counter, sec)
            QThread.sleep(1)
            counter += 1

    def run(self):

        success = False

        if not self.completed_before:
            # prompt to unplug and plug the device again

            success, msg = self.download_files()
            

        if success:
            success, msg = self.initiate_fel_mode()
        
        if success:
            self.wait_with_progress('Mouting the device...', 10)

        if success: 
            success, msg = self.mount()

        if success:
            success, msg = self.copy_files()
            self.wait_with_progress('Copying files...', 45)

        if success:
            success, msg = self.unmount()
            self.wait_with_progress('Unmounting device...', 10)

        self.finish_signal.emit(success, msg)




class AppContext(ApplicationContext):

    def run(self):
        window = QMainWindow()
        version = self.build_settings['version']
        window.setWindowTitle('Synchrony Installer')
        window.resize(250, 150)

        layout = QVBoxLayout()

        self.install_handler = InstallHandler()

        self.install_button = QPushButton('Install')
        self.install_button.clicked.connect(self.clicked_install)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(100)
        self.install_handler.progress_signal.connect(self.update_progress)

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
        self.progress_bar.setFormat('{0} {1}%'.format(current, (done / total) * 100))


if __name__ == '__main__':
    if is_linux():
        elevate(graphical=False)
    else:
        elevate()

    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)

