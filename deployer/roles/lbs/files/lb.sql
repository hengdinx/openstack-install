drop database if exists `lbs`;
CREATE DATABASE lbs;

CREATE TABLE `lbs`.`computes` (
  `hostname` varchar(255) NOT NULL,
  `cpu` int(20) unsigned NOT NULL,
  `mem` int(20) unsigned NOT NULL,
  `disk` int(20) unsigned NOT NULL,
  `connections` int(20) unsigned NOT NULL,
   PRIMARY KEY (`hostname`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8;
