#!/usr/bin/python

import os
import json
from collections import namedtuple
from ansible.inventory.manager import InventoryManager
from ansible.vars.manager import VariableManager
from ansible.parsing.dataloader import DataLoader
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
from ansible.errors import AnsibleParserError

class mycallback(CallbackBase):
    def __init__(self,*args):
        super(mycallback,self).__init__(display=None)
        self.status_ok=json.dumps({})
        self.status_fail=json.dumps({})
        self.status_unreachable=json.dumps({})
        self.status_playbook=''
        self.status_no_hosts=False
        self.host_ok = {}
        self.host_failed={}
        self.host_unreachable={}
    def v2_runner_on_ok(self,result):
        host=result._host.get_name()
        self.runner_on_ok(host, result._result)
        #self.status_ok=json.dumps({host:result._result},indent=4)
        self.host_ok[host] = result
    def v2_runner_on_failed(self, result, ignore_errors=False):
        host = result._host.get_name()
        self.runner_on_failed(host, result._result, ignore_errors)
        #self.status_fail=json.dumps({host:result._result},indent=4)
        self.host_failed[host] = result
    def v2_runner_on_unreachable(self, result):
        host = result._host.get_name()
        self.runner_on_unreachable(host, result._result)
        #self.status_unreachable=json.dumps({host:result._result},indent=4)
        self.host_unreachable[host] = result
    def v2_playbook_on_no_hosts_matched(self):
        self.playbook_on_no_hosts_matched()
        self.status_no_hosts=True
    def v2_playbook_on_play_start(self, play):
        self.playbook_on_play_start(play.name)
        self.playbook_path=play.name

class my_ansible_play():
    def __init__(self, playbook, extra_vars={}, 
                        host_list='inventory/all', 
                        connection='ssh',
                        become=False,
                        become_user=None,
                        module_path=None,
                        fork=50,
                        ansible_cfg=None,   #os.environ["ANSIBLE_CONFIG"] = None
                        passwords={},
                        check=False):
        self.playbook_path=playbook
        self.passwords=passwords
        self.extra_vars=extra_vars
        Options = namedtuple('Options',
                   ['listtags', 'listtasks', 'listhosts', 'syntax', 'connection','module_path',
                   'forks', 'private_key_file', 'ssh_common_args', 'ssh_extra_args', 'sftp_extra_args',
                      'scp_extra_args', 'become', 'become_method', 'become_user', 'verbosity', 'check', 'diff'])
        self.options = Options(listtags=False, listtasks=False, 
                              listhosts=False, syntax=False, 
                              connection=connection, module_path=module_path, 
                              forks=fork, private_key_file=None, 
                              ssh_common_args=None, ssh_extra_args=None, 
                              sftp_extra_args=None, scp_extra_args=None, 
                              become=become, become_method=None, 
                              become_user=become_user, 
                              verbosity=None, check=check, diff=False)
        if ansible_cfg != None:
            os.environ["ANSIBLE_CONFIG"] = ansible_cfg
        #self.variable_manager=VariableManager()
        self.loader=DataLoader()
        self.inventory = InventoryManager(loader=self.loader,sources=host_list)
        self.variable_manager = VariableManager(loader=self.loader, inventory=self.inventory)
    def run(self):
        complex_msg={}
        if not os.path.exists(self.playbook_path):
            code=1000
            results={'playbook':self.playbook_path,'msg':self.playbook_path+' playbook is not exist','flag':False}
            #results=self.playbook_path+'playbook is not existed'
            #return code,complex_msg,results
        pbex= PlaybookExecutor(playbooks=[self.playbook_path],
                       inventory=self.inventory,
                       variable_manager=self.variable_manager,
                       loader=self.loader,
                       options=self.options,
                       passwords=self.passwords)
        self.results_callback=mycallback()
        pbex._tqm._stdout_callback=self.results_callback
        try:
            code=pbex.run()
            print "run finished!!!!!!!!!!!!!!!"
        except AnsibleParserError:
            code=1001
            results={'playbook':self.playbook_path,'msg':self.playbook_path+' playbook have syntax error','flag':False}
            #results='syntax error in '+self.playbook_path
            return code,results
        if self.results_callback.status_no_hosts:
            code=1002
            results={'playbook':self.playbook_path,'msg':self.results_callback.status_no_hosts,'flag':False,'executed':False}
            #results='no host match in '+self.playbook_path
            return code,results
    def get_result(self):
        self.result_all={'success':{},'failed':{},'unreachable':{}}
        #print dir(self.results_callback)
        for host, result in self.results_callback.host_ok.items():
            self.result_all['success'][host] = result._result
            succ = self.result_all['success'][host]
            succ_json = json.dumps(succ, indent=4)

        for host, result in self.results_callback.host_failed.items():
            self.result_all['failed'][host] = result._result['msg']
            failed = self.result_all['failed'][host]
            failed_json = json.dumps(failed, indent=4)

        for host, result in self.results_callback.host_unreachable.items():
            self.result_all['unreachable'][host]= result._result['msg']
            unre = json.dumps(self.result_all['unreachable'][host], indent=4)
        
        for i in self.result_all['success'].keys():
            #print i,self.result_all['success'][i]
            #print self.result_all['failed']
            print type(succ_json)
            #print i+"\n"+succ_json
            print "!!!!!!!!!!!!!!!!!!!!!"
            #print i+"\n"+failed_json
            #print self.result_all['unreachable']
            print "!!!!!!!!!!!!!!!!!!!!!"
            #print self.result_all['success']
        
        
    
if __name__ =='__main__':
    play_book=my_ansible_play('site.yml')
    play_book.run()
    play_book.get_result()
