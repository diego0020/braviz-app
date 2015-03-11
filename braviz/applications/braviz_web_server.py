##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

from __future__ import print_function
import os

import tornado.ioloop
import tornado.web

import braviz
from braviz.interaction.connection import GenericMessageClient
from braviz.interaction.tornado_connection import LongPollMessageHandler, MessageFutureProxy
from braviz.visualization.d3_visualizations import ParallelCoordinatesHandler, IndexHandler


__author__ = 'da.angulo39'

settings = {
    "static_path": os.path.join(os.path.dirname(braviz.__file__), "visualization/web_static"),
    "template_path": os.path.join(os.path.dirname(braviz.__file__), "visualization/web_templates")
}

if __name__ == "__main__":
    import sys
    broadcast_address = None
    receive_address = None

    if len(sys.argv) > 3:
        broadcast_address = sys.argv[2]
        receive_address = sys.argv[3]

    message_handler = MessageFutureProxy()
    message_client = GenericMessageClient(
        message_handler, broadcast_address, receive_address)
    application = tornado.web.Application(
        [
            (r"/parallel", ParallelCoordinatesHandler),
            (r"/messages", LongPollMessageHandler,
             {"message_client": message_client}),
            (r"/", IndexHandler),
        ],
        **settings)
    try:
        application.listen(8100)
        tornado.ioloop.IOLoop.instance().start()
    except Exception:
        print("Couldn't start server, maybe already running?")
