import json
import struct

def send_json(sock, status, process_bar=0, log_msg=""):
    json_msg = {
    "status": status,
    "progress": process_bar,
    "log_message": log_msg
    }
    ver = 1
    body = json.dumps(json_msg)
    pkg_type = 101
    header = [ver, body.__len__(), pkg_type]
    head_pack = struct.pack("!3I", *header)
    send_data = head_pack+body.encode()
    try:
        sock.send(send_data)
    except Exception as e:
        raise e

