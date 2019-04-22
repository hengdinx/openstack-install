#!/usr/bin/python

import socket
import subprocess
import ConfigParser
import threading
import time
import json
import struct
from IPy import IP
import cPickle as pickle
import os
import pexpect
import sys
import uuid
import paramiko

from send_json import send_json
from ansible_runner import Ansible_runner
from db import DB_conn
from mydaemon import MyDaemon

CONFIG_PATH=os.path.dirname(__file__)+"/"
BUF_SIZE = 1024
DEFAULT_PASSWORD = 'qwer1234'
GROUP_VARS_FILE = 'all'
VPN_NET_START = '169.255.0.0/20'
ANSIBLE_PATH = CONFIG_PATH+"../deployer"
CEPHFILE_PATH = "/tmp/ceph"
DBNAME = 'operator'

class Json_config(object):
    def __init__(self, data):
        
        config_tmp = json.loads(data)
        #config_tmp = json.loads(config_tmp)
        self.new_node = []
        deploy_conf = config_tmp["deploy_conf"]
        self.action = deploy_conf["action_type"]
        self.deploy_ip_mg = deploy_conf['deploy_ip_mg']
        self.deploy_ip_sto = deploy_conf['deploy_ip_sto']
        self.need_updatedb = False
        if deploy_conf.get("master_node"):
            self.master_node = deploy_conf["master_node"]
        else:
            self.master_node = "\"{{ groups.controller[0] }}\""

        if self.action == "install" or self.action == "init":
            self.json_config = config_tmp
        elif self.action in ["add_compute", "reinstall_init", "add_storage"]:
            self.new_node_hostnames = []
            conn = DB_conn(dbname=DBNAME)
            sql = """ select value from global_options where name='json_conf'; """
            conn.cursor.execute(sql)
            pickled_config = conn.cursor.fetchone()
            self.json_config = pickle.loads(str(pickled_config[0]))
            for node in deploy_conf["nodes"]:
                existed = False
                for existed_node in self.json_config["deploy_conf"]["nodes"]:
                    if node["hostname"] == existed_node["hostname"]:
                        existed = True
                if not existed:
                    if "osd" in node["node_role"]:
                        self.need_updatedb = True
                    self.json_config["deploy_conf"]["nodes"].append(node)
                    self.new_node_hostnames.append(node['hostname'])
                self.new_node.append(node)
        elif self.action == "recover_controller":
            self.new_node_hostnames = []
            conn = DB_conn(dbname=DBNAME)
            sql = """ select value from global_options where name='json_conf'; """
            conn.cursor.execute(sql)
            pickled_config = conn.cursor.fetchone()
            self.json_config = pickle.loads(str(pickled_config[0]))
            for node in deploy_conf["nodes"]:
                self.new_node.append(node)
                self.new_node_hostnames.append(node['hostname'])

        for node in self.json_config["deploy_conf"]["nodes"]:
            if len(node["mg_net"]["ip"]) > 0:
                if not self.get_reachable(node["mg_net"]["ip"]):
                    self.json_config["deploy_conf"]["nodes"].remove(node)
            elif len(node["storage_net"]["ip"]) > 0:
                if not self.get_reachable(node["storage_net"]["ip"]):
                    self.json_config["deploy_conf"]["nodes"].remove(node)

        deploy_conf = self.json_config["deploy_conf"]
        self.nodes = deploy_conf["nodes"]
        self.gateway = deploy_conf['gateway']
        self.domain = deploy_conf["domain"]
        if len(deploy_conf["nova_storage_type"]) > 0 and len(deploy_conf["nova_storage_type"][0]) > 0:
            self.nova_storage_type = deploy_conf["nova_storage_type"]
        else:
            self.nova_storage_type = ["local"]
        self.glance_storage_type = deploy_conf["glance_storage_type"]
        self.enable_compute_ha = deploy_conf["enable_compute_ha"]
        self.controller_vip = deploy_conf["controller_vip"]
        self.node_info_all = []
        self.controller_list, self.compute_list,self.storage_node_list,self.neutron_list = self._get_node_list(self.nodes)
        if len(self.controller_list) >= 3:
            self.ha_enabled = True
        else:
            self.ha_enabled = False

        if len(self.neutron_list) >=3:
            self.neutron_ha_enabled = True
        else:
            self.neutron_ha_enabled = False

        if deploy_conf.get("neutron_vhostname_short"):
            self.neutron_vhostname_short = deploy_conf.get["neutron_vhostname_short"]
            self.neutron_master_node = self.neutron_list[0]["hostname"]
        else:
            self.neutron_vhostname_short = "\"{{ controller_vhostname_short }}\""
            self.neutron_master_node = self.neutron_vhostname_short

        self.ansible_vars = {}


    def _get_node_list(self, nodes):
        controller_list = []
        compute_list = []
        storage_node_list = []
        neutron_list = []
        loop = 1
        vpn_subnet = VPN_NET_START
        for node in nodes:
            node_summary = {}
            node_info = {}
            hostname = node["hostname"]
            root_password = node["root_password"]
            node_role = node["node_role"]
    
            mg_port =       node["mg_net"]["port"]
            mg_ip =         node["mg_net"]["ip"]
            mg_netmask =    node["mg_net"]["netmask"]
    
            cluster_port =      node["cluster_net"]["port"]
            cluster_ip =        node["cluster_net"]["ip"]
            cluster_netmask =   node["cluster_net"]["netmask"]
    
            ext_port =       node["ex_net"]["port"]
            ext_ip =         node["ex_net"]["ip"]
            ext_netmask =    node["ex_net"]["netmask"]
    
            tenant_port =       node["tenant_net"]["port"]
            tenant_ip =         node["tenant_net"]["ip"]
            tenant_netmask =    node["tenant_net"]["netmask"]
    
            sto_port =       node["storage_net"]["port"]
            sto_ip =         node["storage_net"]["ip"]
            sto_netmask =    node["storage_net"]["netmask"]
            if sto_ip != None and len(sto_ip) > 0:
                self.sto_net = IP(sto_ip).make_net(sto_netmask)
            else:
                self.sto_net = ""
    
            sto_internal_ip =         node["storage_internal_net"]["ip"]
            sto_internal_netmask =    node["storage_internal_net"]["netmask"]
            sto_internal_port =       node["storage_internal_net"]["port"]
    
            if cluster_port == "" and mg_port != "":
                cluster_port = mg_port
                cluster_ip = mg_ip
                cluster_netmask = mg_netmask

            if "neutron" in node_role or "controller" in node_role:
                self.cluster_net = IP(cluster_ip).make_net(cluster_netmask)
                self.vip_netmask = cluster_netmask
                vpn_ip_seg = vpn_subnet
                vpn_subnet = self.get_next_subnet(vpn_subnet)
                node_info['vpn_ip_seg'] = str(vpn_ip_seg).split('/')[0]

            node_info['ntp_server'] = "\"{{ controller_vhostname }}\""
            node_info['hostname'] = hostname
            node_info['root_password'] = root_password
            node_info['my_role'] = json.dumps(node_role)
            node_info['mg_ip'] = mg_ip
            node_info['mg_card'] = mg_port
            node_info['mg_netmask'] = mg_netmask
            node_info['cluster_ip'] = cluster_ip
            node_info['cluster_card'] = cluster_port
            node_info['cluster_netmask'] = cluster_netmask
            node_info['tenant_ip'] = tenant_ip
            node_info['tenant_netmask'] = tenant_netmask
            node_info['tenant_card'] = tenant_port
            node_info['ext_ip'] = ext_ip
            node_info['ext_netmask'] = ext_netmask
            node_info['ext_card'] = ext_port
            node_info['sto_ip'] = sto_ip
            node_info['sto_netmask'] = sto_netmask
            node_info['sto_card'] = sto_port
            node_info['sto_internal_ip'] = sto_internal_ip
            node_info['sto_internal_netmask'] = sto_internal_netmask
            node_info['sto_internal_card'] = sto_internal_port

            node_id = loop
            loop = loop + 1
            node_info['id'] = node_id
            
            self.node_info_all.append(node_info)
            
            node_summary["hostname"] = hostname
            node_summary["mg_ip"] = mg_ip
            node_summary["cluster_ip"] = cluster_ip
            node_summary["sto_ip"] = sto_ip
            node_summary["domain"] = self.domain
            node_summary["id"] = node_id
            if "controller" in node_role:
                controller_list.append(node_summary)
            if "compute" in node_role:
                compute_list.append(node_summary)
            if "neutron" in node_role:
                neutron_list.append(node_summary)
            if "osd" in node_role:
                storage_node_list.append(node_summary)
    
        return controller_list,compute_list,storage_node_list,neutron_list

    def get_reachable(self, ip):
        if not subprocess.call("ping "+ip+" -c10 -i 0.1", shell=True):
            return True
        else:
            return False

    def get_next_subnet(self, subnet):
        startip = IP(subnet).broadcast().int()+1
        netmask = IP(subnet).netmask()
        return str(IP(startip).make_net(netmask))

    def get_json_vars(self):
        self.ansible_vars['deploy_ip_mg'] = self.deploy_ip_mg
        self.ansible_vars['deploy_ip_sto'] = self.deploy_ip_sto
        self.ansible_vars['cluster_net'] = self.cluster_net
        if len(self.sto_net) > 0:
            self.ansible_vars['sto_net'] = self.sto_net
        else:
            self.ansible_vars['sto_net'] = ""
        if self.ha_enabled:
            self.ansible_vars['vip'] = self.controller_vip
        else:
            self.ansible_vars['vip'] =  self.controller_list[0]['cluster_ip']
        self.ansible_vars['vip_netmask'] = self.vip_netmask
        self.ansible_vars['gateway'] = self.gateway
        self.ansible_vars['vip_prefix'] = str(self.cluster_net).split('/')[1]
        self.ansible_vars['domain'] = self.domain
        self.ansible_vars['default_password'] = DEFAULT_PASSWORD
        self.ansible_vars['controllers'] = json.dumps(self.controller_list)
        self.ansible_vars['neutrons'] = json.dumps(self.neutron_list)
        self.ansible_vars['computes'] = json.dumps(self.compute_list)
        self.ansible_vars['ceph_nodes'] = json.dumps(self.storage_node_list)
        self.ansible_vars['nova_storage_type'] = json.dumps(self.nova_storage_type)
        self.ansible_vars['enable_compute_ha'] = json.dumps(self.enable_compute_ha)
        self.ansible_vars['ha_enabled'] = self.ha_enabled
        self.ansible_vars['neutron_ha_enabled'] = self.neutron_ha_enabled
        self.ansible_vars['action_type'] = self.action
        self.ansible_vars['master_node'] = self.master_node
        self.ansible_vars['neutron_vhostname_short'] = self.neutron_vhostname_short
        self.ansible_vars['neutron_master_node'] = self.neutron_master_node

    def write_conf(self):
        # write group_vars/all
        with open(ANSIBLE_PATH+"/group_vars/"+GROUP_VARS_FILE, 'w') as f:
            for key in self.ansible_vars.keys():
                f.write(key+": "+str(self.ansible_vars[key])+"\n")
        if self.action in ["install", "add_compute", "recover_controller", "reinstall_init"]:
            with open(ANSIBLE_PATH+"/keys.yml", 'w') as f:
                if self.action == "install":
                    self.ansible_vars['openstack_key'] = str(uuid.uuid4()).replace("-","")[:16]
                    if "ceph" in self.nova_storage_type:
                        try:
                            self.ansible_vars['ceph_uuid'] = str(uuid.uuid4())
                            p = subprocess.Popen("cat "+CEPHFILE_PATH+"/client.cephe3c.keyring|grep key|awk -F ' = ' '{print $2}'", \
                                            shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                            self.ansible_vars['ceph_key'] = p.stdout.readlines()[0].strip()
                        except Exception as e:
                            raise e
                        f.write("ceph_uuid: "+self.ansible_vars['ceph_uuid']+"\nceph_key: "+self.ansible_vars['ceph_key']+"\n")

                elif self.action in ["add_compute", "recover_controller", "reinstall_init"]:
                    conn = DB_conn(dbname=DBNAME)
                    if "ceph" in self.nova_storage_type:
                        keys = ["openstack_key", "ceph_key", "ceph_uuid"]
                    else:
                        keys = ["openstack_key"]
                    for key in keys:
                        sql = """ select value from global_options where name='%s'; """ % key
                        conn.cursor.execute(sql)
                        value = conn.cursor.fetchone()

                        self.ansible_vars[key] = str(value[0])
                    conn.close()

                    if "ceph" in self.nova_storage_type:
                        f.write("ceph_uuid: "+self.ansible_vars['ceph_uuid']+"\nceph_key: "+self.ansible_vars['ceph_key']+"\n")

                f.write("openstack_key: "+self.ansible_vars['openstack_key']+"\n")

        # write host_vars
        for node in self.node_info_all:
            if node['mg_ip'] == self.deploy_ip_mg or (node['sto_ip'] == self.deploy_ip_sto and node['sto_ip'] not in [None,""]):
                with open(ANSIBLE_PATH+"/host_vars/localhost", 'w') as f:
                    for key in node.keys():
                        f.write(key+": "+str(node[key])+"\n")

            with open(ANSIBLE_PATH+"/host_vars/"+node['hostname'], 'w') as f:
                for key in node.keys():
                    f.write(key+": "+str(node[key])+"\n")

        with open(ANSIBLE_PATH+"/inventory/all", 'w') as f:
            f.write("[all]\n")
            for node in self.node_info_all:
                f.write(node['hostname']+"\n")

            f.write("[controller]\n")
            for node in self.controller_list:
                f.write(node['hostname']+"\n")

            f.write("[compute]\n")
            for node in self.compute_list:
                f.write(node['hostname']+"\n")

            f.write("[neutron]\n")
            for node in self.neutron_list:
                f.write(node['hostname']+"\n")

            if len(self.new_node) > 0:
                f.write("[new_node]\n")
                for node in self.new_node:
                    f.write(node['hostname']+"\n")
                f.write("[new_node_neutron]\n")
                for node in self.new_node:
                    if "neutron" in node["node_role"]:
                        f.write(node['hostname']+"\n")
                f.write("[new_node_compute]\n")
                for node in self.new_node:
                    if "compute" in node["node_role"]:
                        f.write(node['hostname']+"\n")


    def ssh_prepare(self):
        '''
        Write /etc/hosts for ansible. You should be aware that the content
        added to /etc/hosts here may be different from what will be write
        in ansible, cause what ansible done is to bind cluster IP for
        hostname, and this is for cluster to use service provided by other
        nodes, while what we do here is to let ansible knows all nodes for
        deploy.
        '''
        with open("/etc/hosts", 'w') as f:
            for node in self.node_info_all:
                if node['mg_ip'] != None and node['mg_ip'] != "":
                    f.write(node['mg_ip']+" "+node['hostname']+"\n")
                elif node['sto_ip'] != None and node['sto_ip'] != "":
                    f.write(node['sto_ip']+" "+node['hostname']+"\n")
            f.write(self.controller_vip+" controllervhostname")

        # generate rsa keys for ssh trust and run ssh-copy-id need to sleep 5s to wait until key generate
        subprocess.Popen("sed -i 's/^[\t #]*StrictHostKeyChecking.*$/StrictHostKeyChecking no/g' /etc/ssh/ssh_config", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        subprocess.Popen("rm -f /root/.ssh/known_hosts", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if not os.path.exists('/root/.ssh/id_rsa'):
            subprocess.Popen("ssh-keygen -t rsa -f /root/.ssh/id_rsa -P ''", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            time.sleep(5)
        for node in self.node_info_all:
            if node['mg_ip'] != None and node['mg_ip'] != "":
                ansible_ip = node['mg_ip']
            else:
                ansible_ip = node['sto_ip']
            process=pexpect.spawn('ssh-copy-id -i /root/.ssh/id_rsa root@'+ansible_ip, timeout=120)
            #process.logfile_read = sys.stdout
            index = process.expect(['s password:','already exist on the remote', pexpect.EOF, pexpect.TIMEOUT])
            if index == 0:
                process.sendline(node['root_password'])
                index = process.expect(['Number of key', pexpect.EOF, pexpect.TIMEOUT])
            process.close()

    def create_operator_db(self):
        conn = DB_conn()
        conn.recreate_db(DBNAME)
        conn.close()

        conn = DB_conn(dbname=DBNAME)
        conn.drop_table('network_node')
        conn.cursor.execute("create table node_network( \
                            node_id int(10) not null auto_increment primary key, \
                            hostname char(50),\
                            role char(50),\
                            monitor_ip char(15), \
                            mg_ip char(15),\
                            mg_netmask char(15),\
                            sto_ip char(15),\
                            sto_netmask char(15)\
                            )")
        conn.drop_table('global_options')
        conn.cursor.execute("create table global_options(\
                        option_id int(10) not null auto_increment primary key,\
                        name varchar(30),\
                        value varchar(65535)\
                        )")
        #conn.drop_table('ansible_vars')
        #conn.cursor.execute("create table ansible_vars(\
        #                option_id int(10) not null auto_increment primary key,\
        #                option varchar(30),\
        #                value varchar(65535)\
        #                )")
        conn.close()

    def db_insert(self, dbname, values):
        pass

    def init_operator_db(self):
        conn = DB_conn(DBNAME)
        for node in self.node_info_all:
            node_role = ",".join(json.loads(node['my_role']))
            if node['mg_ip'] not in [None, ""]:
                monitor_ip = node['mg_ip']
            elif node['sto_ip'] not in [None, ""]:
                monitor_ip = node['sto_ip']
            #node_role = pickle.dumps(node['my_role'])
            sql = "insert into node_network (node_id, hostname, role, monitor_ip, mg_ip, mg_netmask, sto_ip, sto_netmask) values ("+ \
                            "\"" + str(node['id']) + "\"," + \
                            "\"" + node['hostname']+ "." + self.domain + "\"," + \
                            "\'" + node_role + "\'," + \
                            "\'" + monitor_ip + "\'," + \
                            "\"" + node['mg_ip'] + "\"," + \
                            "\"" + node['mg_netmask'] + "\"," + \
                            "\"" + node['sto_ip'] + "\"," + \
                            "\"" + node['sto_netmask'] \
                       +"\")"
            conn.cursor.execute(sql)

        global_options = {}
        if len(self.controller_list) >= 3:
            global_options['ctl_ha'] = "True"
        else:
            global_options['ctl_ha'] = "False"
        global_options['cmp_ha_enable'] = self.enable_compute_ha
        global_options['storage_type'] = self.nova_storage_type
        global_options['json_conf'] = pickle.dumps(self.json_config)
        if "ceph" in self.nova_storage_type:
            global_options['ceph_uuid'] = self.ansible_vars['ceph_uuid']
            global_options['ceph_key'] = self.ansible_vars['ceph_key']
        global_options['openstack_key'] = self.ansible_vars['openstack_key']
        for key in global_options.keys():
            if key == "storage_type":
                global_option_value = ",".join(global_options["storage_type"])
            else:
                global_option_value = str(global_options[key])
            sql = "insert into global_options (name, value) values ("+ \
                "\"" + key + "\"," \
                "\"" + global_option_value + "\")"
            conn.cursor.execute(sql)

        conn.dbcon.commit()
        conn.close()

    def update_node_network(self):
        conn = DB_conn(DBNAME)
        for node in self.node_info_all:
            node_role = ",".join(json.loads(node['my_role']))
            if node['mg_ip'] not in [None, ""]:
                monitor_ip = node['mg_ip']
            elif node['sto_ip'] not in [None, ""]:
                monitor_ip = node['sto_ip']

            if node['hostname'] in self.new_node_hostnames:
            #node_role = pickle.dumps(node['my_role'])
                sql = "insert into node_network (hostname, role, monitor_ip, mg_ip, mg_netmask, sto_ip, sto_netmask) values ("+ \
                                "\"" + node['hostname']+ "." + self.domain + "\"," + \
                                "\'" + node_role + "\'," + \
                                "\'" + monitor_ip + "\'," + \
                                "\"" + node['mg_ip'] + "\"," + \
                                "\"" + node['mg_netmask'] + "\"," + \
                                "\"" + node['sto_ip'] + "\"," + \
                                "\"" + node['sto_netmask'] \
                           +"\")"
                conn.cursor.execute(sql)
        conn.dbcon.commit()
        conn.close()


    def update_global_option(self):
        conn = DB_conn(DBNAME)
        global_options = {}
        if len(self.controller_list) >= 3:
            global_options['ctl_ha'] = "True"
        else:
            global_options['ctl_ha'] = "False"
        global_options['json_conf'] = pickle.dumps(self.json_config)
        if "ceph" in self.nova_storage_type:
            global_options['ceph_uuid'] = self.ansible_vars['ceph_uuid']
            global_options['ceph_key'] = self.ansible_vars['ceph_key']
        global_options['openstack_key'] = self.ansible_vars['openstack_key']
        for key in global_options.keys():
            if key == "storage_type":
                global_option_value = ",".join(global_options["storage_type"])
            else:
                global_option_value = str(global_options[key])
            sql = """update global_options set value="%s" where name='%s';""" % (global_options[key], key)
            conn.cursor.execute(sql)
        conn.dbcon.commit()
        conn.close()

    def fetch_key_files(self):
        for node in self.controller_list:
            if node['hostname'] not in self.new_node_hostnames:
                subprocess.Popen("scp root@"+node['mg_ip']+":/var/lib/rabbitmq/.erlang.cookie /tmp/", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                subprocess.Popen("scp -r root@"+node['mg_ip']+":/etc/keystone/credential-keys /tmp/", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                subprocess.Popen("scp -r root@"+node['mg_ip']+":/etc/keystone/fernet-keys /tmp/", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                subprocess.Popen("scp -r root@"+node['mg_ip']+":/etc/corosync/corosync.conf /tmp/", shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                break

class e3c_operator(E3c_daemon):
    def __init__(self, name, save_path, stdin=os.devnull, stdout=os.devnull, stderr=os.devnull, home_dir='.', umask=022, verbose=1):
        E3c_daemon.__init__(self, save_path, stdin, stdout, stderr, home_dir, umask, verbose)
        self.name = name

    def run_ansible(self, inventory_file, action_type, sock):
        runner = Ansible_runner(inventory_file, action_type, sock)
        runner.run()
    
    def tcplink(self, sock, addr):
        print time.strftime('%H:%M:%S')+': Accept new connection from %s:%s...' % addr
        sys.stdout.flush()
        data_buffer = bytes()
        head_size = 12
        data = ""
        recv_finished = False
        while True:
            if recv_finished:
                break
            data = sock.recv(1024)
            if data:
                data_buffer += data
                while True:
                    if len(data_buffer) < head_size:
                        print("packet(%s byte, shorter than the header, break)" % len(data_buffer))
                        sys.stdout.flush()
                        break
    
                    head_pack = struct.unpack('!3I', data_buffer[:head_size])
                    body_size = head_pack[1]
    
                    if len(data_buffer) < head_size+body_size:
                        print("packet(%s byte) shorter than total(%s), break" % (len(data_buffer), head_size+body_size))
                        sys.stdout.flush()
                        break
                    body = data_buffer[head_size:head_size+body_size]
    
                    data_buffer = data_buffer[head_size+body_size:]
                    recv_finished = True
    
        data = json.loads(body, encoding='utf-8')
        json_conf = Json_config(data)
    
        # Config network for all nodes
        if json_conf.action == "init":
            json_conf.get_json_vars()
            json_conf.write_conf()
            json_conf.ssh_prepare()
            self.run_ansible(ANSIBLE_PATH+"/inventory/all", json_conf.action, sock)
        '''
        TODO
        Need to install ceph here.
        '''
        #Run install process
        if json_conf.action == "install":
            json_conf.get_json_vars()
            json_conf.write_conf()
            if json_conf.ha_enabled:
                action_type = "install"
                ssh_cmd = "pcs resource restart httpd-clone"
            elif not json_conf.ha_enabled:
                action_type = "install_aio"
                ssh_cmd = "systemctl restart httpd"
            self.run_ansible(ANSIBLE_PATH+"/inventory/all", action_type, sock)
            json_conf.create_operator_db()
            json_conf.init_operator_db()

        if json_conf.action == "add_compute":
            json_conf.get_json_vars()
            json_conf.write_conf()
            json_conf.ssh_prepare()
            self.run_ansible(ANSIBLE_PATH+"/inventory/all", json_conf.action, sock)
            json_conf.update_global_option()
            json_conf.update_node_network()
            
        if json_conf.action == "recover_controller":
            json_conf.get_json_vars()
            json_conf.write_conf()
            json_conf.ssh_prepare()
            json_conf.fetch_key_files()
            self.run_ansible(ANSIBLE_PATH+"/inventory/all", json_conf.action, sock)

        if json_conf.action == "reinstall_init":
            json_conf.get_json_vars()
            json_conf.write_conf()
            json_conf.ssh_prepare()
            self.run_ansible(ANSIBLE_PATH+"/inventory/all", json_conf.action, sock)
            if json_conf.need_updatedb:
                json_conf.update_global_option()
                json_conf.update_node_network()

        if json_conf.action == "add_storage":
            json_conf.get_json_vars()
            json_conf.update_global_option()
            json_conf.update_node_network()
            
        if json_conf.action in ["install", "recover_controller"]:
            import ast
            if json_conf.ha_enabled:
                ssh_cmd = "pcs resource restart httpd-clone"
            elif not json_conf.ha_enabled:
                ssh_cmd = "systemctl restart httpd"
            ssh_target = ast.literal_eval(json_conf.ansible_vars['controllers'])[0]['hostname']
            ssh_conn = paramiko.SSHClient()
            key = paramiko.AutoAddPolicy()
            ssh_conn.set_missing_host_key_policy(key)
            ssh_conn.connect(ssh_target, 22, 'root', timeout=30)
            try:
                time.sleep(20)
                stdin, stdout, stderr = ssh_conn.exec_command(ssh_cmd)
                print "run command \"%s\" on %s" % (ssh_cmd, ssh_target)
            except Exception as e:
                print stderr
                raise e

    
        send_json(sock, "finished", 100)
        sock.close()
        print time.strftime('%H:%M:%S')+': Connection from %s:%s closed.' % addr
        sys.stdout.flush()
    
    def run(self):
        conf = ConfigParser.ConfigParser()
        conf.read(CONFIG_PATH+"/operator.conf")
        
        bind_ip = conf.get("network", "bind_ip")
        port = int(conf.get("network", "port"))
        
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((bind_ip, port))
        s.listen(1)
        
        while True:
            sock, addr = s.accept()
            t = threading.Thread(target=self.tcplink, args=(sock, addr))
            t.start()
