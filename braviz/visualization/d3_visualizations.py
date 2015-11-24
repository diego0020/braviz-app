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
import math
import tornado.web


import pandas as pd
import numpy as np
from braviz.readAndFilter import tabular_data as tab_data, user_data, log_db
from braviz.readAndFilter.cache import memoize, memo_ten
from braviz.readAndFilter.config_file import get_apps_config
from braviz.interaction.connection import NpJSONEncoder

__author__ = 'diego'


class ParallelCoordinatesHandler(tornado.web.RequestHandler):
    """
    Implements a parallel coordinates view from variables in the database

    It is based on the `parallel coordinates <http://mbostock.github.io/d3/talk/20111116/iris-parallel.html>`_
    d3 example

    The *GET* method receives as arguments:

        - **category** : Id of a variable to use as categories, lines will be colored according to this variable
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
            sample = data.index.get_values()
            sample_idx = "null"

        sample_json = json.dumps(sample, cls=NpJSONEncoder)
        data2 = data.dropna()
        missing = sorted(set(data.index) - set(data2.index))
        missing_json = json.dumps(missing, cls=NpJSONEncoder)
        data = data2

        if variables[0] in variables[1:]:
            all_columns = list(data.columns)
            cats_name = all_columns[0]
            data["_category"] = data[cats_name]
            data = data[["_category"]+all_columns]
        else:
            cols = data.columns
            cols2 = list(cols)
            cols2[0] = "_category"
            data.columns = cols2

        labels = tab_data.get_labels_dict(variables[0])

        for i, (k, v) in enumerate(labels.iteritems()):
            if v is None or len(v) == 0:
                v = "level_%d" % i
            elif v[0].isdigit():
                v = "c_" + v
            labels[k] = v.replace(' ', '_')

        # sanitize label name
        col0 = "_category"
        data[col0] = data[col0].map(labels)
        data["code"] = data.index

        json_data = data.to_json(orient="records")

        caths = labels.values()
        caths_json = json.dumps(list(caths))

        # 1: cathegories, -1: code
        attrs = list(data.columns[1:-1])
        attrs_json = json.dumps(attrs)
        self.render("parallel_coordinates.html", data=json_data, caths=caths_json, vars=attrs_json, cath_name=col0,
                    missing=missing_json, sample=sample_json, cath_index=cath_idx, var_indices=traits_idx_json,
                    sample_id=sample_idx)

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
        if data_type == "values":
            cats = self.get_argument("category")
            variables = self.get_argument("variables").split(",")
            sample = self.get_argument("sample",None)
            out = self.get_values(cats, variables, sample)
        else:
            self.send_error("404")

        self.write(out)
        self.set_header('Content-Type', "application/json")

    def get_values(self, cat, vs, sample_idx):
        vars_list = [int(cat)] + [int(v) for v in vs]
        data = tab_data.get_data_frame_by_index(vars_list)
        if sample_idx is not None:
            sample = user_data.get_sample_data(sample_idx)
        else:
            sample = tab_data.get_subjects()
        data2 = data.dropna()
        missing = sorted(set(data.index) - set(data2.index))
        data = data2
        # cleaning
        # handle category variable repeated as attribute
        if vars_list[0] in vars_list[1:]:
            all_columns = list(data.columns)
            cats_name = all_columns[0]
            data["_category"] = data[cats_name]
            data = data[["_category"]+all_columns]
        else:
            cols = data.columns
            cols2 = list(cols)
            cols2[0] = "_category"
            data.columns = cols2
        labels = tab_data.get_labels_dict(vars_list[0])
        # sanitize label name
        for i, (k, v) in enumerate(labels.iteritems()):
            if v is None:
                labels[k] = "label%s" % k
            if v is None or len(v) == 0:
                v = "level_%d" % i
            elif v[0].isdigit():
                v = "c_" + v
            labels[k] = v.replace(' ', '_')
        col0 = "_category"
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
                           "var_indices": vars_list[1:],
                           "sample" : sample,
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

class HistogramHandler(tornado.web.RequestHandler):
    """
    Implements a simple web page for changing the current subject from a mobile.

    """

    def get(self):
        var_name = self.get_argument("var",None)
        color_name = self.get_argument("color",None)

        if var_name is None or color_name is None:
            default_variables = get_apps_config().get_default_variables()
            if var_name is None:
                var_name = default_variables["ratio1"]
            if color_name is None:
                color_name = default_variables["nom1"]

        df = tab_data.get_data_frame_by_name([var_name,color_name])
        df.dropna(inplace=True)
        df["index"]=df.index.astype(str)
        labels = tab_data.get_labels_dict(var_name=color_name)
        for i, (k, v) in enumerate(labels.iteritems()):
            if v is None or len(v) == 0:
                v = "level_%d" % i
            labels[k] = v
        df[color_name] = df[color_name].map(labels)
        levels = list(labels.values())
        data = df.to_json(orient="records")

        variable_id = tab_data.get_var_idx(var_name)
        categories_id = tab_data.get_var_idx(color_name)
        sample_id = "null"

        sample_param = self.get_argument("sample", None)
        if sample_param is not None:
            sample_id = sample_param
            sample = sorted(user_data.get_sample_data(sample_param))
        else:
            sample = sorted(tab_data.get_subjects())

        self.render("histogram.html",values=data, var_name=var_name, color_name=color_name, color_levels=levels,
                    variable_id=variable_id, categories_id=categories_id, sample_id=sample_id, sample=sample)

class HistogramDataHandler(tornado.web.RequestHandler):
    """
    Implements a simple web page for changing the current subject from a mobile.

    """

    def get(self):
        var_index = int(self.get_argument("variable"))
        color_index = int(self.get_argument("color"))
        try:
            sample_param = int(self.get_argument("sample"))
        except ValueError:
            sample_param = None

        df = tab_data.get_data_frame_by_index([var_index,color_index])
        variable_name, categories_name = df.columns
        df.dropna(inplace=True)
        df["index"]=df.index.astype(str)
        labels = tab_data.get_labels_dict(var_idx=color_index)
        for i, (k, v) in enumerate(labels.iteritems()):
            if v is None or len(v) == 0:
                v = "level_%d" % i
            labels[k] = v
        df[categories_name] = df[categories_name].map(labels)
        levels = list(labels.values())
        data_json = df.to_json(orient="records")
        sample_id = "null"

        if sample_param is not None:
            sample_id = sample_param
            sample = sorted(user_data.get_sample_data(sample_param))
        else:
            sample = sorted(tab_data.get_subjects())


        ans = """{{ "data" : {data}, "var_name" : {var_name}, "color_name" : {color_name},
         "color_levels" : {levels_dict},
         "variable_id" : {var_id}, "categories_id" : {cat_id}, "sample_id" : {sample_id},
          "sample" : {sample} }}""".format(data = data_json,
                                           var_name = json.dumps(variable_name,cls=NpJSONEncoder),
                                           color_name = json.dumps(categories_name,cls=NpJSONEncoder),
                                           levels_dict = json.dumps(levels,cls=NpJSONEncoder),
                                           var_id = json.dumps(var_index,cls=NpJSONEncoder),
                                           cat_id = json.dumps(color_index,cls=NpJSONEncoder),
                                           sample_id = json.dumps(sample_id,cls=NpJSONEncoder),
                                           sample = json.dumps(sample,cls=NpJSONEncoder)
                                           )
        self.write(ans)
        self.set_header("Content-Type", "application/json")


class SessionIndexHandler(tornado.web.RequestHandler):
    """
    Implements a web interface for reviewing analysis history

    """

    def format_session(self, session):
        abbreviated_time = "%a %d - %I %p"
        full_time = "%Y-%m-%d %H:%M:%S"
        return {"name": session.name,
                "abv_start": session.start_date.strftime(abbreviated_time),
                "full_start": session.  start_date.strftime(full_time),
                "duration": session.duration.seconds//60,  # in minutes
                "description": session.description if len(session.description)>0 else "(no description)",
                "id": session.index,
                "favorite" : session.favorite,
                }

    def get(self):
        sessions = [self.format_session(s) for s in log_db.get_sessions()]
        sessions_json=json.dumps(sessions)
        self.render("sessions.html", sessions=sessions_json)

class SessionDataHandler(tornado.web.RequestHandler):
    """
    Data manipulations related to analysis history
    """

    full_time = "%Y/%m/%d %H:%M:%S"
    def initialize(self):
        self.application_icons = {
            "anova" : self.static_url("icons/anova.png"),
            "braviz_menu2" :self.static_url("icons/braviz.png"),
            "subject_overview" :self.static_url("icons/subject_overview.png"),
            "linear_model" : self.static_url("icons/linear.png"),
            "correlations" : self.static_url("icons/correlations.png"),
            "sample_overview" : self.static_url("icons/sample_overview.png"),
        }
    def format_events(self, event):
        abbreviated_time = "%I:%M %p"
        return {"name": event.action,
                "abv_date": event.date.strftime(abbreviated_time),
                "full_date": event.date.strftime(self.full_time),
                "id": event.index,
                "favorite": event.favorite,
                "icon_url":self.application_icons.get(event.application_name,""),
                "application" : event.application_name,
                "comments": [],
                "instance": event.instance_id,
                }

    def get(self, ent):
        if ent=="events":
            session_id = self.get_argument("session")
            events = {e.index : self.format_events(e) for e in log_db.get_events(session_id)}
            comments = log_db.get_event_annotations(session_id)
            for c in comments:
                events[c.event_id]["comments"].append({"id":c.annotation_id,
                                                       "date":c.date.strftime(self.full_time),
                                                       "text":c.annotation,
                                                       })
            sorted_events =  sorted(events.itervalues(),key=lambda x:x["full_date"])
            app_ids = {}
            for e in sorted_events:
                app = e["application"]
                instance = e["instance"]
                instances_indices = app_ids.setdefault(app,dict())
                instance_i = instances_indices.get(instance)
                if instance_i is None:
                    instance_i = len(instances_indices)
                    instances_indices[instance] = instance_i
                e["instance_index"] = instance_i
            self.write({"events":sorted_events})
        elif ent=="event_data":
            event_id = self.get_argument("event_id")
            state_string = log_db.get_event_state(event_id)
            self.set_header("Content-Type", "application/json")
            self.write(state_string)
            self.finish()
        else:
            self.send_error(404)

    def post(self, ent):
        if ent == "session":
            session_id = self.get_body_argument("session")
            new_name = self.get_body_argument("name",None)
            new_description = self.get_body_argument("desc",None)
            delete_session = self.get_body_argument("delete",None)
            favorite = self.get_body_argument("favorite",None)
            if new_name is not None:
                log_db.set_session_name(session_id,new_name)
                self.set_status(202,"Name changed")
                self.finish()
                return
            if new_description is not None:
                log_db.set_session_description(session_id,new_description)
                self.set_status(202,"description changed")
                self.finish()
                return
            if favorite is not None:
                fav = favorite == "true"
                log_db.set_session_favorite(session_id,fav)
                self.set_status(202,"Favorite toggled")
                self.finish()
                return
            if delete_session is not None:
                active_session = log_db.get_active_session()
                if int(session_id) == int(active_session):
                    self.send_error(403)
                    return
                log_db.delete_session(session_id);
                self.set_status(202,"Name changed")
                self.finish()
                return
        elif ent == "event":
            event_id = self.get_body_argument("event")
            fav = self.get_body_argument("favorite",None)
            ant = self.get_body_argument("annotation",None)
            delete_annotation = self.get_body_argument("delete_annotation",None)
            if fav is not None:
                fav = fav == "true"
                log_db.set_event_favorite(event_id,fav)
                self.set_status(202,"Favorite toggled")
                self.finish()
                return
            if ant is not None:
                ant_id = self.get_body_argument("annotation_id",None)
                if ant_id is not None:
                    log_db.modify_event_annotaiton(ant_id,ant)
                    self.set_status(202,"Annotation modified")
                    self.finish()
                    return
                else:
                    ant_id = log_db.add_event_annotation(event_id,ant)
                    self.set_status(202,"Annotation added")
                    self.write("%d"%ant_id)
                    self.finish()
                    return
            if delete_annotation is not None and delete_annotation:
                ant_id = self.get_body_argument("annotation_id",None)
                log_db.delete_annotation(ant_id)
                self.set_status(202,"Annotation modified")
                self.finish()
                return
        self.send_error(404)


class SliceViewerHandler(tornado.web.RequestHandler):
    """
    Implements a web page for visualizing several image slices

    """

    def get_fmri_contrasts(self,paradigms, reader):
        fmri_contrasts = {}
        all_subjs = reader.get("ids")
        cfg = get_apps_config()
        favorite_subj = cfg.get_default_subject()
        all_subjs.insert(0,favorite_subj)
        for pdgm in paradigms:
            for s in all_subjs:
                try:
                    cnts = reader.get("FMRI",s,name=pdgm,contrasts_dict=True)
                except Exception:
                    pass
                else:
                    fmri_contrasts[pdgm]=cnts
                    break
                fmri_contrasts[pdgm] = {}
        return fmri_contrasts

    def initialize(self):
        import braviz.readAndFilter
        self.images = []
        reader = braviz.readAndFilter.BravizAutoReader()
        imgs = reader.get("IMAGE",None,index=True)
        fmri = reader.get("FMRI",None,index=True)
        fmri_contrasts = self.get_fmri_contrasts(fmri, reader)
        labels = reader.get("LABEL",None,index=True)
        self.images += [("IMAGE/"+n,n) for n in sorted(imgs)]
        self.images += [("DTI/DTI","DTI")]
        self.images += [("LABEL/"+n,n) for n in sorted(labels)]
        self.images += [("/".join(("FMRI",n,str(ci))),"FMRI-"+n.title()+": "+cn)
                        for n in sorted(fmri)
                        for ci, cn in fmri_contrasts[n].iteritems()
                        ]

    def get(self):
        self.render("slices.html",images=self.images)


class SliceViewerDataHandler(tornado.web.RequestHandler):
    """
    Implements a web page for visualizing several image slices

    """
    def get(self, element):
        if element == "img":
            subj = self.get_argument("subj")
            slice_number = self.get_argument("slice",None)
            orientation = self.get_argument("orientation","axial")
            coordinates = self.get_argument("coordinates","talairach")
            img_type = self.get_argument("type","IMAGE")
            img_name = self.get_argument("name","MRI")
            try:
                img = self.get_slice_img(subj,slice_number, orientation, coordinates, img_type, img_name)
            except Exception as e:
                log = logging.getLogger(__name__)
                log.exception(e)
                self.send_error(404)
            else:
                self.set_header("Content-Type", "image/png")
                self.write(img)
        elif element == "samples":
            samples = user_data.get_samples_df()
            self.write(samples.to_json())
            self.set_header("Content-Type", "application/json")
        elif element == "subjects":
            sample_idx = self.get_argument("sample",None)
            variable = self.get_argument("variable",None)
            if sample_idx is not None:
                sample = user_data.get_sample_data(sample_idx)
                if variable is None:
                    self.write({"sample": [int(x) for x in sample]})
                    return
            if variable is not None:
                df = tab_data.get_data_frame_by_index(variable)
                if sample_idx is not None:
                    df = df.loc[sample]
                df.sort_values(by=df.columns[0],inplace=True)
                self.write({"sample":[int(x) for x in df.index],
                            "values":[float(x) if not math.isnan(x) else ""
                                      for x in df.iloc[:,0]]})
                return
            if sample_idx is None and variable is None:
                sample = tab_data.get_subjects()
                self.write({"sample":[int(x) for x in sample]})
                return
            self.write_error(400)
        elif element == "variables":
            vars_df = tab_data.get_variables_and_type()
            vars_df = vars_df[["var_name"]]
            vars_df.sort_values(by="var_name", inplace=True)
            descriptions = tab_data.get_descriptions_dict()
            vars_df["desc"]=pd.Series(descriptions)
            json_vars = vars_df.to_json(orient="split")
            self.set_header("Content-Type", "application/json")
            self.write(json_vars)
        else:
            self.write_error(404)


    def initialize(self):
        import braviz.readAndFilter
        self.reader = braviz.readAndFilter.BravizAutoReader()
        self.orientation_dict = {"axial": 2, "coronal": 1, "sagital": 0}

    def get_slice_img(self, subj, slice_number, orientation, coordinates, img_type, img_name):
            import braviz.readAndFilter.images
            import braviz.visualization.fmri_view
            from cStringIO import StringIO
            import PIL.Image
            import numpy as np
            import vtk

            orientation_int = self.orientation_dict.get(orientation.lower(), 0)
            img_type = img_type.upper()
            if img_type == "IMAGE":
                vtk_img = self.reader.get("IMAGE",subj, name=img_name, space=coordinates, format="vtk")
                np_img = braviz.readAndFilter.images.vtk2numpy(vtk_img)
                min_value, max_value = np_img.min(), np_img.max()
                np_img = (np_img-min_value)/(max_value-min_value)*255
            elif img_type == "DTI":
                vtk_img = self.reader.get("DTI",subj, space=coordinates, format="vtk")
                np_img = braviz.readAndFilter.images.vtk2numpy(vtk_img)
            elif img_type == "FMRI":
                contrast = self.get_argument("contrast",1)
                fmri_img = self.reader.get("FMRI",subj, name=img_name, space=coordinates,
                                           format="vtk", contrast=contrast)
                mri_img = self.reader.get("IMAGE",subj, name="MRI", space=coordinates, format="vtk")
                blend = braviz.visualization.fmri_view.blend_fmri_and_mri(fmri_img, mri_img, threshold=3, alfa=True)
                blend.Update()
                vtk_img = blend.GetOutput()
                np_img = braviz.readAndFilter.images.vtk2numpy(vtk_img)
            elif img_type == "LABEL":
                label_img = self.reader.get("LABEL",subj, name=img_name, space=coordinates, format="vtk")
                lut = self.reader.get("LABEL",subj, name=img_name, lut=True)
                color_mapper = vtk.vtkImageMapToColors()
                color_mapper.SetInputData(label_img)
                color_mapper.SetLookupTable(lut)
                color_mapper.Update()
                vtk_img=color_mapper.GetOutput()
                np_img = braviz.readAndFilter.images.vtk2numpy(vtk_img)
            else:
                raise NameError("Unknown image type")

            if slice_number is None:
                slice_number = np_img.shape[orientation_int] // 2

            if orientation_int == 0:
                slice_img = np_img[slice_number, :, :].astype(np.uint8)
                slice_img = np.rot90(slice_img)
            elif orientation_int == 1:
                slice_img = np_img[:, slice_number, :].astype(np.uint8)
                slice_img = np.rot90(slice_img)
            else:
                slice_img = np_img[:, :, slice_number].astype(np.uint8)

            pillow_img = PIL.Image.fromarray(slice_img)
            out_buffer = StringIO()
            pillow_img.save(out_buffer,"png")
            return out_buffer.getvalue()


class BarsHandler(tornado.web.RequestHandler):
    """
    Implements a simple web page for changing the current subject from a mobile.

    """
    def get(self):
        subj = self.get_argument("subject",None)
        vars = self.get_argument("variables",None)
        if vars is None:
            vars = ParallelCoordinatesHandler.get_default_vars()
        if subj is None:
            subj = get_apps_config().get_default_subject()

        self.render("var_values.html",variables=vars,subject=subj)



class BarsDataHandler(tornado.web.RequestHandler):
    """
    Implements a simple web page for changing the current subject from a mobile.

    """
    def get(self):
        variables=tuple(self.get_argument("variables").split(","))
        subject = self.get_argument("subj")
        df = tab_data.get_subject_variables(subject, variables)
        meta_df= self.get_vars_meta(variables)
        real_df = df.merge(meta_df)

        nom_df = df.loc[df.index.isin(real_df["index"])==False]
        nom_df.loc[:,"index"]=nom_df.index

        real_df.sort_values(by="name")
        nom_df.sort_values(by="name")

        full_json='{{ "real" : {real_df} , "nominal" : {nom_df} }}'.format(
            real_df=real_df.to_json(orient="records"),
            nom_df=nom_df.to_json(orient="records")
        )

        self.write(full_json)
        self.set_header("Content-Type", "application/json")

    @staticmethod
    @memo_ten
    def get_vars_meta(variables):
        real_meta = []
        for v in variables:
            var_real = tab_data.is_variable_real(v)
            if var_real:
                vm={
                    "name" : tab_data.get_var_name(v),
                }
                var_min, var_max = tab_data.get_min_max_values(v)
                vm["index"]=v
                vm["min"]=var_min
                vm["max"]=var_max
                real_meta.append(vm)
        df = pd.DataFrame.from_records(real_meta,index="index")
        df["index"]=df.index
        return df


class DialogDataHandler(tornado.web.RequestHandler):
    """
    Returns data for the given sample and variables as a json object

    """

    def get(self):
        samples_requested = self.get_argument("samples","false") == "true"
        variables_requested = self.get_argument("variables","false") == "true"
        subjects_requested = self.get_argument("subjects","false") == "true"

        samples = self.get_samples() if samples_requested else "[]"
        vars = self.get_variables() if variables_requested else "[]"
        subjs = self.get_subjects() if subjects_requested else "[]"

        out = '{{ "variables" : {vars}, "samples" : {samples}, "subjects" : {subjs} }}'.format(
            vars=vars, samples=samples, subjs=subjs
        )

        self.write(out)
        self.set_header('Content-Type', "application/json")

    def get_variables(self):
        vars_df = tab_data.get_variables_and_type()
        vars_df.sort_values(by="var_name", inplace=True)
        descriptions = tab_data.get_descriptions_dict()
        vars_df["desc"]=pd.Series(descriptions)
        vars_df.loc[vars_df["desc"].isnull(),"desc"] = ""
        vars_df["index"]=vars_df.index
        vars_json = vars_df.to_json(orient="records")
        return vars_json

    def get_subjects(self):
        subjects = tab_data.get_subjects()
        subjs_json = json.dumps(subjects)
        return subjs_json

    def get_samples(self):
        samples_df = user_data.get_samples_df()
        samples_df["index"]=samples_df.index
        samples_json = samples_df.to_json(orient="records")
        return samples_json

