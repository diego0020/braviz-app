
import os

import tornado.ioloop
import tornado.web

import braviz
from braviz.visualization.d3_visualizations import ParallelCoordinatesHandler


__author__ = 'da.angulo39'

settings = {
    "static_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_static"),
    "template_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_templates")
}

if __name__ == "__main__":
    application = tornado.web.Application(
        [
        (r"/", ParallelCoordinatesHandler),
        ],
        **settings)
    try:
        application.listen(8100)
        tornado.ioloop.IOLoop.instance().start()
    except Exception:
        print "Couldn't start server, maybe already running?"
