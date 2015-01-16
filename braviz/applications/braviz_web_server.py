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


import os

import tornado.ioloop
import tornado.web

import braviz
from braviz.visualization.d3_visualizations import ParallelCoordinatesHandler, IndexHandler, MessageHandler
from braviz.interaction.connection import PassiveMessageClient

__author__ = 'da.angulo39'

settings = {
    "static_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_static"),
    "template_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_templates")
}

if __name__ == "__main__":
    message_client = PassiveMessageClient("tcp://127.0.0.1:52818","tcp://127.0.0.1:57914")
    application = tornado.web.Application(
        [
        (r"/parallel", ParallelCoordinatesHandler),
        (r"/messages", MessageHandler,{"message_client":message_client}),
        (r"/", IndexHandler),
        ],
        **settings)
    try:
        application.listen(8100)
        tornado.ioloop.IOLoop.instance().start()
    except Exception:
        print "Couldn't start server, maybe already running?"
