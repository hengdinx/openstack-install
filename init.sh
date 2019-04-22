#!/bin/bash
systemctl -l|grep e3c_operator && systemctl stop e3c_operator
systemctl -l|grep e3cwizard && systemctl stop e3cwizard
rm -rf /opt/e3c-install*
mkdir -p /opt/e3c-install
tar -zxf ./e3c-install*.gz -C /opt/e3c-install/

cd /opt/e3c-install/yum
./init_yum.sh

ln -s /opt/e3c-install/ /opt/e3c-install-4.3
