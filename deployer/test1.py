#!/usr/bin/env python
 
import json
import shutil
from collections import namedtuple
from ansible.parsing.dataloader import DataLoader
from ansible.vars.manager import VariableManager
from ansible.inventory.manager import InventoryManager
from ansible.playbook.play import Play
from ansible.executor.task_queue_manager import TaskQueueManager
from ansible.executor.playbook_executor import PlaybookExecutor
from ansible.plugins.callback import CallbackBase
import ansible.constants as C
 
 
class ResultCallback(CallbackBase):
    def __init__(self, *args, **kwargs):
        # super(ResultsCollector, self).__init__(*args, **kwargs)
        self.host_ok = {}
        self.host_unreachable = {}
        self.host_failed = {}
 
    def v2_runner_on_unreachable(self, result):
        self.host_unreachable[result._host.get_name()] = result
 
    def v2_runner_on_ok(self, result, *args, **kwargs):
        self.host_ok[result._host.get_name()] = result
 
    def v2_runner_on_failed(self, result, *args, **kwargs):
        self.host_failed[result._host.get_name()] = result
 
 
class AnsibleRunner(object):
    def __init__(self):
        self.Options = namedtuple('Options',
                             ['connection',
                              'remote_user',
                              'ask_sudo_pass',
                              'verbosity',
                              'ack_pass',
                              'module_path',
                              'forks',
                              'become',
                              'become_method',
                              'become_user',
                              'check',
                              'listhosts',
                              'listtasks',
                              'listtags',
                              'syntax',
                              'sudo_user',
                              'sudo',
                              'diff'])
        
        self.ops = self.Options(connection='smart',
                              remote_user=None,
                              ack_pass=None,
                              sudo_user=None,
                              forks=5,
                              sudo=None,
                              ask_sudo_pass=False,
                              verbosity=None,
                              module_path=None,
                              become=None,
                              become_method=None,
                              become_user=None,
                              check=False,
                              diff=False,
                              listhosts=None,
                              listtasks=None,
                              listtags=None,
                              syntax=None)
 
        self.loader = DataLoader()
        self.passwords = {}
 
    def runansible(self):
 
        play_source = dict(
            name="Ansible Play",
            hosts=host_list,
            gather_facts='no',
            tasks=task_list
        )
        play = Play().load(play_source, variable_manager=self.variable_manager, loader=self.loader)
 
        tqm = None
        try:
            tqm = TaskQueueManager(
                inventory=self.inventory,
                variable_manager=self.variable_manager,
                loader=self.loader,
                options=self.ops,
                passwords=self.passwords,
                stdout_callback=self.results_callback,
                run_additional_callbacks=C.DEFAULT_LOAD_CALLBACK_PLUGINS,
                run_tree=False,
            )
            result = tqm.run(play)
        finally:
            if tqm is not None:
                tqm.cleanup()
            shutil.rmtree(C.DEFAULT_LOCAL_TMP, True)
 
        results_raw = {}
        results_raw['success'] = {}
        results_raw['failed'] = {}
        results_raw['unreachable'] = {}
 
        for host, result in self.results_callback.host_ok.items():
            results_raw['success'][host] = json.dumps(result._result)
 
        for host, result in self.results_callback.host_failed.items():
            results_raw['failed'][host] = result._result['msg']
 
        for host, result in self.results_callback.host_unreachable.items():
            results_raw['unreachable'][host] = result._result['msg']
 
        print results_raw
 
 
    def run_playbook(self, host_list, playbooks):
        inventory = InventoryManager(loader=self.loader, sources=host_list)
        variable_manager = VariableManager(loader=self.loader, inventory=inventory)
 
        variable_manager.extra_vars = {'customer': 'test', 'disabled': 'yes'}
        play = PlaybookExecutor(playbooks=playbooks,
                                    inventory=inventory,
                                    variable_manager=variable_manager,
                                    loader=self.loader, options=self.ops, passwords=self.passwords)
        self.results_callback = ResultCallback()
        result = play.run()
        return result
 
 
if __name__ == "__main__":
    runner = AnsibleRunner()
    host_list = ['inventory']
    #tasks_list = [
    #    dict(action=dict(module='command', args='ls')),
    #    # dict(action=dict(module='shell', args='python sleep.py')),
    #    # dict(action=dict(module='synchronize', args='src=/home/op/test dest=/home/op/ delete=yes')),
    #]
    #a.runansible(host_list,tasks_list)
    print runner.run_playbook(host_list, ['site.yml'])

