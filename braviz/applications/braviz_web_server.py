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
import braviz.readAndFilter
from braviz.interaction.connection import GenericMessageClient
from braviz.interaction import tornado_connection
from braviz.visualization import d3_visualizations
import logging

__author__ = 'da.angulo39'

settings = {
    "static_path": os.path.join(os.path.dirname(braviz.__file__), "visualization/web_static"),
    "template_path": os.path.join(os.path.dirname(braviz.__file__), "visualization/web_templates")
}

if __name__ == "__main__":
    import sys
    broadcast_address = None
    receive_address = None
    log = logging.getLogger(__name__)
    conf = braviz.readAndFilter.config_file.get_apps_config()
    port = conf.get("Braviz","server_port")

    warning_log = logging.getLogger("tornado.access")
    warning_log.setLevel(logging.ERROR)

    if len(sys.argv) > 3:
        broadcast_address = sys.argv[2]
        receive_address = sys.argv[3]

    socket_manager = tornado_connection.WebSocketManager()
    message_client2 = GenericMessageClient(
        socket_manager, broadcast_address, receive_address)
    socket_manager.message_client = message_client2
    application = tornado.web.Application(
        [
            (r"/parallel/data/(.*)", d3_visualizations.ParallelCoordsDataHandler),
            (r"/parallel", d3_visualizations.ParallelCoordinatesHandler),
            (r"/messages_ws",tornado_connection.WebSocketMessageHandler,
                {"socket_manager": socket_manager}),
            (r"/subject", d3_visualizations.SubjectSwitchHandler),
            (r"/histogram", d3_visualizations.HistogramHandler),
            (r"/histogram/data", d3_visualizations.HistogramDataHandler),
            (r"/history", d3_visualizations.SessionIndexHandler),
            (r"/history/data/(.*)", d3_visualizations.SessionDataHandler),
            (r"/slices", d3_visualizations.SliceViewerHandler),
            (r"/slices/data/(.*)", d3_visualizations.SliceViewerDataHandler),
            (r"/bars", d3_visualizations.BarsHandler),
            (r"/bars/data", d3_visualizations.BarsDataHandler),
            (r"/dialog/data", d3_visualizations.DialogDataHandler),
            (r"/", d3_visualizations.IndexHandler),
        ],
        **settings)
    try:
        application.listen(port)
        tornado.ioloop.IOLoop.instance().start()
    except Exception:
        log.warning("Couldn't start server, maybe already running?")
    else:
        log.info("Web server listening on port {}".format(port))
