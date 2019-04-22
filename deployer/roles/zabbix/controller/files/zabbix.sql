grant all privileges on zabbix.* to 'zabbixsrv'@'localhost' identified by 'qwer1234';
grant all privileges on zabbix.* to 'zabbixsrv'@'%' identified by 'qwer1234';
flush privileges;
DROP TABLE if EXISTS `zabbix`.`e3cloud_history`;
CREATE TABLE `zabbix`.`e3cloud_history` (
  `hostid` bigint(20) unsigned NOT NULL,
  `flagid` bigint(20) unsigned NOT NULL,
  `value` varchar(255) NOT NULL,
  `others` varchar(255) DEFAULT  NULL,
   PRIMARY KEY (`hostid`,`flagid`) 
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
