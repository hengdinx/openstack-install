#!/bin/bash

if [ $# -ne 1 ]; then
    echo usage: $0 version
    exit 1
fi

build_dir=/root/build
cur_dir=`pwd`
rm -rf $build_dir/e3c-install*
rm -rf $build_dir/*
cp -r $cur_dir $build_dir/e3c-install

#password=qwer1234
#expect <<EOF
#set timeout 300
#spawn sh -c "/usr/bin/find ${build_dir}/e3c-install/e3c-deploy/ -name \"*.yml\" | xargs ansible-vault encrypt"
#expect "New Vault password:"
#send "${password}\n"
#expect "Confirm New Vault password:"
#send "${password}\n"
#expect "Encryption successful"
#expect eof;
#EOF

find ${build_dir}/e3c-install/e3c-deploy/ -name "*.yml" | xargs ansible-vault encrypt --vault-password-file ${build_dir}/e3c-install/e3c-deploy/.vault_pass

cd $build_dir/e3c-install/e3c-operator
rm -rf  $build_dir/e3c-install/.git
python -m compileall ./
python -O -m compileall ./
rm -rf ./*.py

cd ..
tar -zcf $build_dir/e3c-install-$1.tar.gz yum e3c-operator e3c-deploy
test -f ./data.tar.gz && cp ./data.tar.gz /root/build/
cp init*.sh /root/build/
cd /root/build
test -f ./data.tar.gz &&  mkisofs -r -o e3c-install-$1.iso e3c-install-$1.tar.gz init*.sh data.tar.gz || mkisofs -r -o e3c-install-$1.iso e3c-install-$1.tar.gz init.sh 
