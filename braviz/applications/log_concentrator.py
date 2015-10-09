from __future__ import division, print_function
import sys
import os
import braviz
from braviz.interaction.connection import BlockingMessageClient
import braviz.readAndFilter
from braviz.readAndFilter import log_db
import time
import logging
import braviz.utilities

__author__ = 'diego'

class LogConcentrator(object):

    def __init__(self, broadcast_address):
        client = BlockingMessageClient(broadcast_address)
        route = braviz.readAndFilter.braviz_auto_dynamic_data_root()
        self.output_name = os.path.join(route, "last_session_log.txt")
        self.log = logging.getLogger(__name__)
        while True:
            msg = client.get_message()
            try:
                if msg["type"] == "log":
                    self.process_log_event(msg)
                else:
                    self.process_message_event(msg)
            except Exception as e:
                self.log.exception(e)

    def process_log_event(self, msg):
        app = msg["application"]
        action = msg["action"]
        pid = msg["pid"]
        pretty_time = time.ctime(msg["time"])
        state = msg["state"]
        picture = msg.get("screenshot")
        if picture is not None:
            # Transform to binary blob
            pass

        line="[%s] %s (%s) : %s\n"%(pretty_time,app,pid,action)
        self.log.info(line)
        log_db.add_event(app, pid, action, state, picture)
        with open(self.output_name,"a") as out:
            out.write(line)

    def process_message_event(self, msg):
        msg_type=msg["type"]
        t= time.ctime()

        line="[%s] %s (%s) : %s\n"%(t,"message",msg_type,msg)
        self.log.info(line)
        with open(self.output_name,"a") as out:
            out.write(line)


if __name__ == "__main__":
    braviz.utilities.configure_console_logger(__file__)
    if len(sys.argv) < 2:
        print("The server broadcast address is required")
    else:
        server_broadcast = sys.argv[1]
        LogConcentrator(server_broadcast)
