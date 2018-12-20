#!/usr/bin/python

import MySQLdb

DBNAME = "operator"
DBUSER = "root"
DBPASSWORD = "qwer1234"
DBHOST = "controllervhostname"

class DB_conn(object):
    def __init__(self, dbname=None, user=DBUSER, pw=DBPASSWORD, host=DBHOST):
        if dbname:
            self.dbcon = MySQLdb.connect(host, user, pw, dbname, charset='utf8')
        else:
            self.dbcon = MySQLdb.connect(host, user, pw, charset='utf8')
        self.cursor = self.dbcon.cursor()

    def drop_table(self, table_name):
        self.cursor.execute('drop table if exists '+table_name)
        #sql = """CREATE TABLE  table_name(
        #    FIRST_NAME  CHAR(20) NOT NULL,
        #    LAST_NAME  CHAR(20),
        #    AGE INT,  
        #    SEX CHAR(1),
        #    INCOME FLOAT )"""

    def recreate_db(self, name):
        self.cursor.execute("drop database if exists " + name)
        self.cursor.execute('create database if not exists ' + name)

    def close(self):
        self.dbcon.close()

if __name__ == '__main__':
    conn = DB_conn()
    conn.recreate_db(DBNAME)
    conn.close()

    conn = DB_conn(dbname=DBNAME)
    conn.drop_table('network_node')
    conn.cursor.execute("create table node_network( \
                        node_id int(10) not null auto_increment primary key, \
                        hostname char(20),\
                        role char(20),\
                        mg_ip char(15),\
                        mg_netmask char(15),\
                        sto_ip char(15),\
                        sto_netmask char(15)\
                        )")
    conn.drop_table('global_options')
    conn.cursor.execute("create table global_options(\
                        option_id int(10) not null auto_increment primary key,\
                        name char(30),\
                        value char(20)\
                        )")
    conn.close()
