
import tornado.ioloop
import tornado.web
import os
import braviz
import braviz.readAndFilter.tabular_data as tab_data
from braviz.readAndFilter import user_data
from braviz.interaction.config_file import get_config
import json


__author__ = 'da.angulo39'

default_variables=None

def get_default_vars():
    global default_variables
    conf = get_config(__file__)
    vars=conf.get_default_variables()
    var_keys=("nom1","nom2","ratio1","ratio2")
    all_vars=map(vars.get,var_keys)
    codes=map(tab_data.get_var_idx,all_vars)
    def_vars=",".join(map(str,codes))
    default_variables=def_vars

class MainHandler(tornado.web.RequestHandler):
    def get(self):

        vars_s = self.get_query_argument("vars",default_variables)
        sample = self.get_query_argument("sample",None)
        vars=map(int,vars_s.split(","))
        data = tab_data.get_data_frame_by_index(vars)
        if sample is not None:
            subjs = user_data.get_sample_data(sample)
            data=data.loc[subjs]
            #print subjs

        data2 = data.dropna()
        missing = len(data)-len(data2)
        #print "%d missing values"%missing
        data = data2

        cols = data.columns
        cols2=list(cols)
        cols2[0]="category"
        data.columns=cols2
        labels = tab_data.get_labels_dict(vars[0])

        for k,v in labels.iteritems():
            if v is None:
                labels[k]="label%s"%k
            if v[0].isdigit():
                v = "c_"+v
            labels[k]=v.replace(' ','_')


        #sanitize label name
        col0 = cols2[0]
        data[col0]=data[col0].map(labels)
        data["code"]=data.index

        json_data = data.to_json(orient="records")

        caths = data[col0].unique()
        caths_json = json.dumps(list(caths))

        #1: cathegories, 2: code
        attrs=list(data.columns[1:-1])
        attrs_json = json.dumps(attrs)
        self.render("parallel_coordinates.html",data=json_data,caths=caths_json,vars=attrs_json,cath_name=col0,
                    missing=missing)

    def post(self, *args, **kwargs):
        print "got post"
        name=self.get_body_argument("sample_name")
        desc=self.get_body_argument("sample_desc","")
        subjs=self.get_body_argument("sample_subjects")
        print name
        print desc
        print subjs
        if user_data.sample_name_existst(name):
            print "Name already exists"
            self.send_error(409)
        else:
            print "Name is unique"
            subj_list=map(int,subjs.split(","))
            print subj_list
            user_data.save_sub_sample(name,subj_list,desc)
            self.write("ok")


settings = {
    "static_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_static"),
    "template_path":os.path.join(os.path.dirname(braviz.__file__),"visualization/web_templates")
}

if __name__ == "__main__":
    get_default_vars()
    application = tornado.web.Application([
    (r"/", MainHandler),
    ],
    **settings)
    try:
        application.listen(8100)
        tornado.ioloop.IOLoop.instance().start()
    except Exception:
        print "Couldn't start server, maybe already running?"
