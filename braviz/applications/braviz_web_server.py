
import tornado.ioloop
import tornado.web
import os
import braviz
import braviz.readAndFilter.tabular_data as tab_data
import json


__author__ = 'da.angulo39'

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        vars_s = self.get_query_argument("vars","1982,1002,1003,1004")
        vars=map(int,vars_s.split(","))
        data = tab_data.get_data_frame_by_index(vars)
        data.dropna(inplace=True)
        cols = data.columns
        cols2=list(cols)
        cols2[0]="species"
        data.columns=cols2
        col0 = cols[0]
        labels = tab_data.get_labels_dict(vars[0])
        for k,v in labels.iteritems():
            if v is None:
                labels[k]="label%s"%k

        col0 = cols2[0]
        data[col0]=data[col0].map(labels)

        json_data = data.to_json(orient="records")

        caths = data[col0].unique()
        caths_json = json.dumps(list(caths))

        attrs=list(data.columns[1:])
        attrs_json = json.dumps(attrs)
        self.render("parallel_coordinates.html",data=json_data,caths=caths_json,vars=attrs_json,cath_name=col0)

settings = {
    "static_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_static"),
    "template_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_templates")
}

if __name__ == "__main__":
    application = tornado.web.Application([
    (r"/", MainHandler),
    ],
    **settings)
    try:
        application.listen(8100)
        tornado.ioloop.IOLoop.instance().start()
    except Exception:
        print "Couldn't start server, maybe already running?"