#!/usr/bin/python3 

from fbs_runtime.application_context import ApplicationContext
from PyQt5.QtWidgets import * 
# from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QPushButton, QVBoxLayout, QMainWindow

from subprocess import Popen, PIPE, STDOUT
import subprocess
import sys
from sys import platform
import os
import re
import getpass
import time
from elevate import elevate
from shutil import copyfile
from threading import Thread
from PyQt5.QtWidgets import *

def isLinux():
    return platform == 'linux' or platform == 'linux2'

def isMac(): 
    return platform == 'darwin'

def isWindows():
    return platform == 'win32'

class InstallHandler():

    def __init__(self, password, update_progress):
        self.copy_directory = None

        self.mount_dir = '/media/synchrony/allwinner'
        self.os_rootdir = '/media/{0}/SYSTEM/@'.format(getpass.getuser())

        files_dest = { 
                'u-boot.scr': self.mount_dir,
                'client-rhythm.json': os.path.join(self.os_rootdir, 'etc'),
                'client-rhythm-user.json': os.path.join(self.os_rootdir, 'etc'), 
                'client-rhythm': os.path.join(self.os_rootdir, 'usr/local/bin'),
                'record-audio': os.path.join(self.os_rootdir, 'usr/local/bin'),
                'record-audio.cpp': os.path.join(self.os_rootdir, 'usr/local/bin')
        }

        self.sudo_password = ''
        self.partition = None
        self.system_partition = None
        self.update_progress = update_progress
    
    def wait_seconds(wait_time):
        seconds_remaining = wait_time
        while seconds_remaining > 0:
            self.update_progress(seconds_remaining / waiting_time)
            time.sleep(1)
            seconds_remaining -= 1
        print('')

    def mount(self):
        global sudo_password, mount_dir, partition, system_partition
        
        user = getpass.getuser()
        fel_mass_dir = '/home/{0}/fel-mass-storage'.format(user)
        if not os.path.exists(fel_mass_dir):
            print('Cant find fel-mass-storage dir at {0}'.format(fel_mass_dir))
            return

        p = subprocess.Popen(['sudo', '-S', 'mkdir', '-p', self.mount_dir], stdin=subprocess.PIPE)
        p.communicate('{0}\n'.format(sudo_password))
        if p.wait() != 0:
            return (-1, 'Failed to make directory {0}'.format(self.mount_dir)) 

        # Catching fel-mass-storage failure
        start = time.time()

        p = subprocess.Popen(['./start.sh'], cwd=fel_mass_dir, 
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, stdin=subprocess.PIPE)
        
        
        while True:
            if p.poll() is not None:
                break
            else:
                out, err = p.communicate('\n')
                sys.stdout.write(out)
                sys.stdout.flush()

        end = time.time()

        if (end - start) < 1: 
            print('Initiating fel mass mode failed')
            return

        wait_seconds(10)

        fdisk_cmd = ['sudo', '-S', 'fdisk', '-l']
        p = subprocess.Popen(fdisk_cmd, stdout=subprocess.PIPE, stderr = subprocess.PIPE, stdin=subprocess.PIPE)
        out, err =  p.communicate('{0}\n'.format(sudo_password))
        lines = filter(lambda x : x.startswith('/dev'), out.split('\n'))

        self.partition = None
        self.system_partition = None

        for p in lines:
            print(p.split())
            part_info = p.split()
            partition_name, boot_flag, size  = part_info[0], part_info[1], part_info[5]
            if boot_flag == '*' and size == '255M':
                print('Mounting {0}'.format(partition_name))
                partition = partition_name 

        if partition:
            p = subprocess.Popen(['sudo', '-S', 'mount', '-t', 'vfat' , partition, mount_dir], 
                                 stdin=subprocess.PIPE)
            p.communicate('{0}\n'.format(self.sudo_password))
            if p.wait() != 0:
                print('Failed to mount')
            else: 
                system_partition = partition[:-1] + str(int(partition[-1:]) + 1) 
                print('Mounting {0} as SYSTEM'.format(system_partition))
                p = subprocess.Popen(['udisksctl', 'mount', '--block-device', system_partition])

                if p.wait() != 0:
                    print ('Failed to mount SYSTEM')
                else:
                    print('Succeeded to mount SYSTEM')
        else:
            print('Could not find device partition')

    def unmount(self):
        print('Unmounting {0} as SYSTEM'.format(self.system_partition))

        p = subprocess.Popen(['udisksctl', 'unmount', '--block-device', self.system_partition])
        if p.wait() != 0:
            return (-1, 'Failed to unmount SYSTEM')

        p = subprocess.Popen(['sudo', '-S', 'umount', self.mount_dir], stdin=subprocess.PIPE)
        p.communicate('{0}\n'.format(self.sudo_password))
        if p.wait() != 0:
            return (-1, 'Failed to unmount')
        else:
            return (0, 'Finished with unmount')


    def copy_files(self, dir_name):

            if not dir_name.startswith('\\'):
                dir_name  = os.path.abspath(dir_name)

            if not os.path.exists(dir_name):
                print('The directory {0} does not exist'.format(dir_name))
                return

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
                out, err = p.communicate('{0}\n'.format(self.sudo_password))
                if out:
                    print(out)
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

            wait_seconds(45)


    def set_copy_dir(self, d):
        self.copy_directory = d

"""
class MainWidget(BaseWidget):

    def __init__(self, *args, **kwargs):

        super().__init__('Installer')

        self._run_button = ControlButton('Run')
        self._progress = ControlProgress('Progress', value=0, min=0, max=100)
        self._selectDir = ControlDir('Select Source Dir')
        self._installer = InstallHandler('clllc4hermann', self.updateProgress)
        
        self._run_button.value = self.__install 

        # self._formset = []

    def updateProgress(self, percentDone):
        self._progress.value = percentDone

    def __install(self):
        
        self._installer.mount()
        self._installer.set_copy_dir()
        self._installer.copy_files()
        self._installer.unmount()

    def __mount(self):
        pass

    def __copy(self):
        copy_dir = self._selectDir.value
        self._installer.set_copy_dir(copy_dir)
        self._installer.copy_files()

    def __unmount(self):
        self._installer.unmount()

    def closeEvent(self, event):
        self._installer.unmount()

"""

class AppContext(ApplicationContext):
    def run(self):
        window = QMainWindow()
        version = self.build_settings['version']
        window.setWindowTitle('Installer v' + version)
        window.resize(250, 150)

        layout = QVBoxLayout()
        layout.addWidget(QPushButton('Top'))

        centralWidget = QWidget()
        window.setCentralWidget(centralWidget)
        centralWidget.setLayout(layout)

        window.show()
        return self.app.exec_()

if __name__ == '__main__':
    
    elevate()
    appctxt = AppContext()
    exit_code = appctxt.run()
    sys.exit(exit_code)

