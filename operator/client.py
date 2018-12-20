#!/usr/bin/python

import socket
import struct
import time
import json

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

send_file_all("interface.txt")
