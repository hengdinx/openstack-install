START TRANSACTION;
insert into mysql.user(Host,User,Password) values('localhost','zabbixsrv',password('qwer1234'));
insert into mysql.user(Host,User,Password) values('%','zabbixsrv',password('qwer1234'));
flush privileges;
grant all on zabbix.* to zabbixsrv@'localhost' identified by 'qwer1234';
grant all on zabbix.* to zabbixsrv@'%' identified by 'qwer1234';
flush privileges;
commit;
