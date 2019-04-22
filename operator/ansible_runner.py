import subprocess
import struct
import json
import time
import os
import sys

from mylog import Logger
from send_json import send_json
import process_bar

LOG_FILE = "/var/log/openstack-install.log"
dataBuffer = bytes()
headerSize = 12
ANSIBLE_PATH = os.path.dirname(__file__)+"/../deployer"

class Ansible_runner(object):
    def __init__(self, inventory_file, action_type, sock):
        self.inventory_file = inventory_file
        self.sock = sock
        self.logger = Logger('/var/log/openstack-install.log')
        if action_type in ["init", "reinstall_init"]:
            self.playbook = ANSIBLE_PATH+"/"+action_type+".yml"
            self.process_all = iter(process_bar.init_process_bar)
            self.process_step = 0
        if action_type == "install":
            self.playbook = ANSIBLE_PATH+"/install.yml"
            self.process_all = iter(process_bar.install_process_bar)
            self.process_step = 99.9/len(process_bar.install_process_bar)
        if action_type == "install_aio":
            self.playbook = ANSIBLE_PATH+"/install_aio.yml"
            self.process_all = iter(process_bar.install_aio_process_bar)
            self.process_step = 99.9/len(process_bar.install_aio_process_bar)
        if action_type == "add_compute":
            self.playbook = ANSIBLE_PATH+"/add_compute.yml"
            self.process_all = iter(process_bar.add_compute_process_bar)
            self.process_step = 99.9/len(process_bar.add_compute_process_bar)
        if action_type == "recover_controller":
            self.playbook = ANSIBLE_PATH+"/recover_controller.yml"
            self.process_all = iter(process_bar.recover_controller_process_bar)
            self.process_step = 99.9/len(process_bar.recover_controller_process_bar)
                

    def run(self):
        run_cmd = "ansible-playbook -i "+self.inventory_file+" "+self.playbook+" --vault-password-file /opt/openstack-install/deployer/.vault_pass"
        p = subprocess.Popen(run_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

        cur_process = 0.0
        cur_option = self.process_all.next()
        while p.poll() is None:
            if p.stdout:
                output_msg = p.stdout.readline()
            if p.stderr:
                output_msg = p.stderr.readline()
            log_msg = output_msg.strip()
            if log_msg:
                log_msg = time.strftime('%H:%M:%S')+": "+log_msg
                print log_msg
                sys.stdout.flush()
                self.logger.debug(log_msg)

                if cur_option != None and cur_option in log_msg:
                    try:
                        cur_option = self.process_all.next()
                    except StopIteration:
                        pass
                    cur_process += self.process_step
                    cur_process = round(cur_process, 2)
                send_json(self.sock, "running", cur_process, log_msg)
        if p.returncode == 0:
            print('Subprogram success')
            sys.stdout.flush()
        else:
            send_json(self.sock, "failed", cur_process, log_msg)
            print('Subprogram failed')
            sys.stdout.flush()
