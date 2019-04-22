#!/usr/bin/python
import subprocess
import os

PATH = os.path.abspath(__file__).split('/')
PATH.pop()
PATH = '/'.join(PATH)

cmd = "ansible-vault view --vault-password-file "+PATH+"/../deployer/.vault_pass "+PATH+"/../deployer/install.yml|grep -v yml|egrep '[ \t]+- '|sed -e 's/[- ]//g'"
install_process_bar = subprocess.Popen(cmd, \
    shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.read().strip().split()

init_process_bar = [
    None
]

cmd = "ansible-vault view --vault-password-file "+PATH+"/../deployer/.vault_pass "+PATH+"/../deployer/install_aio.yml|grep -v yml|egrep '[ \t]+- '|sed -e 's/[- ]//g'"
install_aio_process_bar = subprocess.Popen(cmd, \
    shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.read().strip().split()

cmd = "ansible-vault view --vault-password-file "+PATH+"/../deployer/.vault_pass "+PATH+"/../deployer/add_compute.yml|grep -v yml|egrep '[ \t]+- '|sed -e 's/[- ]//g'"
add_compute_process_bar = subprocess.Popen(cmd, \
    shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.read().strip().split()

cmd = "ansible-vault view --vault-password-file "+PATH+"/../deployer/.vault_pass "+PATH+"/../deployer/recover_controller.yml|grep -v yml|egrep '[ \t]+- '|sed -e 's/[- ]//g'"
recover_controller_process_bar = subprocess.Popen(cmd, \
    shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout.read().strip().split()
