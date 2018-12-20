#!/usr/bin/python

import socket
import struct
import time
import json

def init_sock():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect(('127.0.0.1', 8111))
    return s

def read_in_block(fileobj):
    while True:
        data_part=fileobj.read(1024)
        if not data_part:
            break
        else:
            yield data_part
    
def send_file(file_name):
    s = init_sock()
    resp = ""
    data_len = 0
    with open(file_name) as f:
        for block in read_in_block(f):
            data_len += len(block)
    data_len_byte = struct.pack('i',data_len)
    s.send(data_len_byte)
    
    with open(file_name) as f:
        for data_part in read_in_block(f):
            s.send(data_part)
    s.close()
def send_data(data):
    s = init_sock()
    data_len = len(data)
    data_len_byte = struct.pack('i',data_len)
    print data_len_byte
    s.send(data_len_byte)
    print s.recv(6)
    s.send(data)
    s.close()

def dataHandle(headPack, body):
    global sn
    sn += 1
    print("ver:%s, bodySize:%s, cmd:%s" % headPack)
    print(body.decode())
    print("")


def send_file_all(file_name):
    s = init_sock()
    with open(file_name) as f:
        data=f.read()
    ver = 1
    body = json.dumps(data)
    cmd = 101
    header = [ver, body.__len__(), cmd]
    headPack = struct.pack("!3I", *header)
    sendData = headPack+body.encode()
    s.send(sendData)

    dataBuffer = bytes()
    headerSize = 12
    data = ""
    finished = False
    while True:
        if finished:
            break
        data = s.recv(1024)
        if data:
            dataBuffer += data
            while True:
                if len(dataBuffer) < headerSize:
                    #print("packet(%s byte, shorter than the header, break)" % len(dataBuffer))
                    break

                headPack = struct.unpack('!3I', dataBuffer[:headerSize])
                bodySize = headPack[1]

                if len(dataBuffer) < headerSize+bodySize :
                    #print("packet(%s byte) shorter than total(%s), break" % (len(dataBuffer), headerSize+bodySize))
                    break
                body = dataBuffer[headerSize:headerSize+bodySize]

                #dataHandle(headPack, body)
                data = json.loads(body)

                dataBuffer = dataBuffer[headerSize+bodySize:]
                if data["status"] in ["finished", "failed"]:
                    finished = True
                    break
    s.close()

#send_file("interface.txt")
#print "sleep 10s"
#
send_file_all("interface.txt")
