##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU General Public License as published by    #
#    the Free Software Foundation, either version 3 of the License, or       #
#    (at your option) any later version.                                     #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU General Public License for more details.                            #
#                                                                            #
#    You should have received a copy of the GNU General Public License       #
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################

import json
import tornado.web
import logging

from braviz.readAndFilter import tabular_data as tab_data, user_data
from braviz.readAndFilter.cache import memoize
from braviz.readAndFilter.config_file import get_config

__author__ = 'diego'


#TODO: receive messages to highlight subjects


class ParallelCoordinatesHandler(tornado.web.RequestHandler):
    """
    Implements a parallel coordinates view from variables in the database

    It is based on the `parallel coordinates <http://mbostock.github.io/d3/talk/20111116/iris-parallel.html>`_
    d3 example

    The *GET* method receives as arguments:

        - **vars** : A list of variable ids to include in the parallel coordinates, in order
                     If it is not given, the default from the configuration file are used
        - **sample** : A sample ID for subjects to include in the visualizaiton, if None is given the whole dataset
                       is displayed

    It returns a parallel coordinates web page, by rendering the template ``parallel_coordinates.html`` found inside
    ``web_template`` in the directory containing the :mod:`braviz.visualization` module.


    The *POST* method is used to save samples from the visualization,
    it receives the following arguments

        - **sample_name** : Name for the new sample
        - **sample_desc** : Description for the new sample
        - **sample_subjects** :  Subject ids inside the new sample

    It returns a `409` error code if the *sample_name* already existed, or ``ok`` with code 200, if the sample was
    successfully saved
    """

    def __init__(self, application, request, **kwargs):
        super(ParallelCoordinatesHandler, self).__init__(application, request, **kwargs)
        self.default_variables = None



    @staticmethod
    @memoize
    def get_default_vars():
        """
        Read default variables from a configuration file

        Returns:
            A string
        """
        conf = get_config(__file__)
        vars=conf.get_default_variables()
        var_keys=("nom1","nom2","ratio1","ratio2")
        all_vars=map(vars.get,var_keys)
        codes=map(tab_data.get_var_idx,all_vars)
        def_vars=",".join(map(str,codes))
        return def_vars

    def get(self):

        vars_s = self.get_query_argument("vars",self.default_variables)
        if vars_s is None:
            vars_s = ParallelCoordinatesHandler.get_default_vars()
            self.default_variables = vars_s
        sample = self.get_query_argument("sample",None)
        vars=map(int,vars_s.split(","))
        data = tab_data.get_data_frame_by_index(vars)
        if sample is not None:
            subjs = user_data.get_sample_data(sample)
            data=data.loc[subjs]

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
        name=self.get_body_argument("sample_name")
        desc=self.get_body_argument("sample_desc","")
        subjs=self.get_body_argument("sample_subjects")
        log = logging.getLogger(__name__)
        log.info("Saving new sample")
        log.info(name)
        log.info(desc)
        log.info(subjs)
        if user_data.sample_name_existst(name):
            print "Name already exists"
            self.send_error(409)
        else:
            print "Name is unique"
            subj_list=map(int,subjs.split(","))
            print subj_list
            user_data.save_sub_sample(name,subj_list,desc)
            self.write("ok")