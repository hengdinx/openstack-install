#!/usr/bin/python
import os
import sys

os.sys.path.append(os.path.dirname(__file__))

from operator import operator

APP_PATH = os.path.dirname(__file__)

def main():
    help_msg = 'Usage: python %s <start|stop|restart|status>' % sys.argv[0]
    if len(sys.argv) != 2:
        print help_msg
        sys.exit(1)
    p_name = 'operator'
    pid_fn = APP_PATH+'/operator.pid'
    log_fn = APP_PATH+'/operator.log'
    err_fn = APP_PATH+'/operator.err.log'
    cD = operator(p_name, pid_fn, stdout=log_fn, stderr=err_fn, verbose=1)

    if sys.argv[1] == 'start':
        cD.start(log_fn)
    elif sys.argv[1] == 'stop':
        cD.stop()
    elif sys.argv[1] == 'restart':
        cD.restart(log_fn)
    elif sys.argv[1] == 'status':
        alive = cD.is_running()
        if alive:
            print 'process [%s] is running ......' % cD.get_pid()
        else:
            print 'daemon process [%s] stopped' %cD.name
    else:
        print 'invalid argument!'
        print help_msg

main()
