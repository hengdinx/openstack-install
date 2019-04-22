#!/bin/bash

systemctl stop packagekit
killall yum
yum remove -y PackageKit
rm -rf /etc/yum.repos.d/*
yum clean all
cd ./ansible/
yum localinstall -y *.rpm
sed -i 's/^[# ]*deprecation_warnings.*$/deprecation_warnings = False/g' /etc/ansible/ansible.cfg

cd ..
cp ./yum.conf /etc/httpd/conf.d/

rm -rf /var/www/html/zero
cd ./rpms/
createrepo .
cd ..
cp -r ./rpms/ /var/www/html/zero
chown -R root:apache /var/www/html/zero
chmod -R 0755 /var/www/html/zero

systemctl restart httpd

cp e3c_operator.service /usr/lib/systemd/system/

systemctl daemon-reload
systemctl start e3cwizard
systemctl start e3c_operator
