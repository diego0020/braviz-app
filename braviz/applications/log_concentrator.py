from __future__ import division, print_function
import sys
import os
import braviz
from braviz.interaction.connection import BlockingMessageClient
import braviz.readAndFilter
import time

__author__ = 'diego'


class LogConcentrator(object):

    def __init__(self, broadcast_address):
        client = BlockingMessageClient(broadcast_address)
        route = braviz.readAndFilter.braviz_auto_dynamic_data_root()
        self.output_name = os.path.join(route, "last_session_log.txt")
        while True:
            msg = client.get_message()
            if msg["type"] == "log":
                self.process_log_event(msg)
            else:
                self.process_message_event(msg)

    def process_log_event(self, msg):
        app = msg["application"]
        action = msg["action"]
        pid = msg["pid"]
        pretty_time = time.ctime(msg["time"])

        line="[%s] %s (%s) : %s\n"%(pretty_time,app,pid,action)

        with open(self.output_name,"a") as out:
            out.write(line)

    def process_message_event(self, msg):
        msg_type=msg["type"]
        t= time.ctime()

        line="[%s] %s (%s) : %s\n"%(t,"message",msg_type,msg)

        with open(self.output_name,"a") as out:
            out.write(line)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("The server broadcast address is required")
    else:
        server_broadcast = sys.argv[1]
        LogConcentrator(server_broadcast)
