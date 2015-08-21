from __future__ import division, print_function

import os
import tornado.ioloop
import tornado.web
from tornado.escape import url_unescape, json_encode
import braviz
import braviz.readAndFilter
from braviz.readAndFilter import config_file

class MainHandler(tornado.web.RequestHandler):
    def initialize(self,out_stream=None):
        if out_stream is not None:
            self.out_stream = out_stream

    def post(self):
        body = self.request.body
        data =  url_unescape(body)
        items=data.split("&")
        data_dict=dict(i.split("=") for i in items)
        data_dict["ip"]=self.request.remote_ip
        json_dict = json_encode(data_dict)
        print(json_dict)
        self.out_stream.write(json_dict+"\n")
        self.write("Success")


settings = {
    "debug" : True,
            }
if __name__ == "__main__":
    dynamic_path=braviz.readAndFilter.braviz_auto_dynamic_data_root()
    out_file=os.path.join(dynamic_path,"web_logger.txt")
    print("output file: %s"%out_file)
    with open(out_file,"a") as out_stream:
        application = tornado.web.Application([
            (r"/", MainHandler,{"out_stream":out_stream}),
        ], **settings)
        application.listen(8050)
        tornado.ioloop.IOLoop.current().start()
