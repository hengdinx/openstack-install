#!/usr/bin/python

import subprocess
import pexpect
import sys

process=pexpect.spawn("gluster volume remove-brick mygfs replica 2 "+sys.argv[1]+":/mnt/gfs force", timeout=120)

index = process.expect(["(y/n)", pexpect.EOF, pexpect.TIMEOUT])

if index == 0:
    process.sendline("y")
    sys.exit(0)
else:
    sys.exit(1)
