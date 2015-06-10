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

from __future__ import division, print_function

import json
import logging

import tornado.web

from braviz.readAndFilter import tabular_data as tab_data, user_data
from braviz.readAndFilter.cache import memoize
from braviz.readAndFilter.config_file import get_apps_config
from braviz.interaction.connection import NpJSONEncoder

__author__ = 'diego'


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
        super(ParallelCoordinatesHandler, self).__init__(
            application, request, **kwargs)
        self.default_variables = None

    @staticmethod
    @memoize
    def get_default_vars():
        """
        Read default variables from a configuration file

        Returns:
            A string
        """
        conf = get_apps_config()
        variables = conf.get_default_variables()
        var_keys = ("nom1", "nom2", "ratio1", "ratio2")
        all_vars = map(variables.get, var_keys)
        codes = [tab_data.get_var_idx(v) for v in all_vars if v is not None]
        def_vars = ",".join(str(c) for c in codes if c is not None)
        return def_vars

    def get(self):

        vars_s = self.get_query_argument("vars", self.default_variables)
        if vars_s is None:
            vars_s = ParallelCoordinatesHandler.get_default_vars()
            self.default_variables = vars_s
        sample_idx = self.get_query_argument("sample", None)
        variables = map(int, vars_s.split(","))
        traits_idx_json = json.dumps(variables[1:])
        cath_idx = variables[0]

        data = tab_data.get_data_frame_by_index(variables)
        if sample_idx is not None:
            sample = sorted(user_data.get_sample_data(sample_idx))
        else:
            sample = data.index

        sample_json = json.dumps(sample, cls=NpJSONEncoder)
        data2 = data.dropna()
        missing = sorted(set(data.index) - set(data2.index))
        missing_json = json.dumps(missing, cls=NpJSONEncoder)
        data = data2

        cols = data.columns
        cols2 = list(cols)
        cols2[0] = "category"
        data.columns = cols2
        labels = tab_data.get_labels_dict(variables[0])

        for i, (k, v) in enumerate(labels.iteritems()):
            if v is None:
                labels[k] = "label%s" % k
            if v is None or len(v) == 0:
                v = "level_%d" % i
            elif v[0].isdigit():
                v = "c_" + v
            labels[k] = v.replace(' ', '_')

        # sanitize label name
        col0 = cols2[0]
        data[col0] = data[col0].map(labels)
        data["code"] = data.index

        json_data = data.to_json(orient="records")

        caths = labels.values()
        caths_json = json.dumps(list(caths))


        # 1: cathegories, -1: code
        attrs = list(data.columns[1:-1])
        attrs_json = json.dumps(attrs)
        self.render("parallel_coordinates.html", data=json_data, caths=caths_json, vars=attrs_json, cath_name=col0,
                    missing=missing_json, sample=sample_json, cath_index=cath_idx, var_indices=traits_idx_json)

    def post(self, *args, **kwargs):
        name = self.get_body_argument("sample_name")
        desc = self.get_body_argument("sample_desc", "")
        subjs = self.get_body_argument("sample_subjects")
        log = logging.getLogger(__name__)
        log.info("Saving new sample")
        log.info(name)
        log.info(desc)
        log.info(subjs)
        if user_data.sample_name_existst(name):
            log.warning("Name already exists")
            self.send_error(409)
        else:
            log.info("Name is unique")
            subj_list = map(int, subjs.split(","))
            log.info(subj_list)
            user_data.save_sub_sample(name, subj_list, desc)
            self.write("ok")


class ParallelCoordsDataHandler(tornado.web.RequestHandler):
    """
    Returns data for the given sample and variables as a json object

    """

    def get(self, data_type):
        out = {}
        if data_type == "variables":
            out = self.get_variable_lists()
        elif data_type == "values":
            cats = self.get_argument("category")
            variables = self.get_argument("variables").split(",")
            out = self.get_values(cats, variables)
        else:
            self.send_error("404")

        self.write(out)
        self.set_header('Content-Type', "application/json")

    def get_variable_lists(self):
        vars_df = tab_data.get_variables_and_type()
        vars_df.sort("var_name", inplace=True)
        vars_df["var_id"] = vars_df.index
        vars_df.rename(columns={"is_real": "type", "var_name": "name"}, inplace=True)
        nominal = vars_df["type"] == 0
        vars_df["type"] = "numeric"
        vars_df.loc[nominal, "type"] = "nominal"
        return json.dumps({"variables": vars_df.to_dict("records")}, cls=NpJSONEncoder)

    def get_values(self, cat, vs):
        vars_list = [int(cat)] + [int(v) for v in vs]
        data = tab_data.get_data_frame_by_index(vars_list)
        data2 = data.dropna()
        missing = sorted(set(data.index) - set(data2.index))
        data = data2
        # cleaning
        cols = data.columns
        cols2 = list(cols)
        cols2[0] = "category"
        data.columns = cols2
        labels = tab_data.get_labels_dict(vars_list[0])

        for i, (k, v) in enumerate(labels.iteritems()):
            if v is None:
                labels[k] = "label%s" % k
            if v is None or len(v) == 0:
                v = "level_%d" % i
            elif v[0].isdigit():
                v = "c_" + v
            labels[k] = v.replace(' ', '_')

        # sanitize label name
        col0 = cols2[0]
        data[col0] = data[col0].map(labels)
        data["code"] = data.index
        data_dict = data.to_dict("records")
        cats = labels.values()
        attrs = list(data.columns[1:-1])
        return json.dumps({"data": data_dict,
                           "categories": cats,
                           "vars": attrs,
                           "cat_name": col0,
                           "missing": missing,
                           "cat_idx": vars_list[0],
                           "var_indices": vars_list[1:]
                           }, cls=NpJSONEncoder)


class IndexHandler(tornado.web.RequestHandler):
    """
    Displays the braviz start page
    """

    def __init__(self, application, request, **kwargs):
        super(IndexHandler, self).__init__(application, request, **kwargs)

    def get(self):
        index = IndexHandler.read_index()
        self.write(index)

    @staticmethod
    @memoize
    def read_index():
        import os

        path = os.path.join(
            os.path.dirname(__file__), "web_static", "index.html")
        with open(path) as f:
            data = f.read()
        return data


class SubjectSwitchHandler(tornado.web.RequestHandler):
    """
    Implements a simple web page for changing the current subject from a mobile.

    """

    def get(self):
        samples_df = user_data.get_samples_df()
        sample_names = [(i, samples_df.sample_name[i]) for i in samples_df.index]
        sample = self.get_argument("sample", None)
        if sample is None:
            subjs = [unicode(s) for s in tab_data.get_subjects()]
            sample_id = ""
        else:
            subjs = [unicode(s) for s in sorted(user_data.get_sample_data(sample))]
            sample_id = sample

        self.render("subject_switch.html", subjs=subjs, samples=sample_names, sample_id=sample_id)
