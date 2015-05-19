from __future__ import print_function
import os
from itertools import izip

import tornado.ioloop
import tornado.web

import braviz
from braviz.utilities import configure_logger_from_conf
from braviz.readAndFilter.config_file import get_apps_config
import vtk
from io import BytesIO
import numpy as np
import nibabel as nib


settings = {
    "static_path": os.path.dirname(__file__),
    "template_path": os.path.dirname(__file__)
}


class XtkHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        self.render('xtk_test.html')

class XtkDataHandler(tornado.web.RequestHandler):
    def initialize(self, reader):
        self.reader = reader
        conf = get_apps_config()
        self.subj = conf.get_default_subject()

    def get(self, data):
        print(data)
        if data == "surf.vtk":
            out_string=self.get_surf()
        elif data == "colors.txt":
            out_string=self.get_colors()
        elif data == "cctracks.trk":
            out_string = self.get_tracks()
        else:
            self.write_error(404)
            return
        print("ok")
        self.set_header("Content-Type","application/octet-stream")
        self.write(out_string)

    def get_surf(self):
        data = reader.get("SURF", self.subj, name="pial", hemi="r", scalars="aparc")
        writer = vtk.vtkPolyDataWriter()
        writer.SetWriteToOutputString(True)
        writer.SetInputData(data)
        writer.Update()
        out_string=writer.GetOutputString()
        return out_string

    def get_colors(self):
        lut = reader.get("surf_scalar", self.subj, scalars="aparc", lut=True)
        annotated_values = lut.GetAnnotatedValues()
        values = [annotated_values.GetValue(i).ToInt() for i in xrange(annotated_values.GetNumberOfValues())]
        colors = []
        for v in values:
            c = [0,0,0,0]
            lut.GetAnnotationColor(v,c)
            c = [int(x*255) for x in c]
            colors.append(c)
        annots = lut.GetAnnotations()
        annotations = [annots.GetValue(i) for i in values]

        out_strings = []
        for v,s,c in izip(values, annotations, colors):
            out_strings.append("%d %s %d %d %d %d"%(v,s,c[0], c[1], c[2], c[3]))
        return "\n".join(out_strings)

    def get_tracks(self):
        fibs = self.reader.get("FIBERS", self.subj)
        points = fibs.GetPoints()
        scalars = fibs.GetPointData().GetScalars()
        ncells = fibs.GetNumberOfCells()

        def get_cell_data(cell_id):
            cell = fibs.GetCell(cell_id)
            pids = cell.GetPointIds()
            ids = [pids.GetId(i) for i in xrange(pids.GetNumberOfIds())]
            coords = np.array([points.GetPoint(i) for i in ids])
            scs = np.array([scalars.GetTuple(i) for i in ids])
            return coords, scs, None

        file_obj = BytesIO()
        streamlines = ( get_cell_data(i) for i in xrange(ncells))
        nib.trackvis.write(file_obj, streamlines)
        file_obj.seek(0)
        return file_obj.read()


if __name__ == "__main__":
    configure_logger_from_conf("test_xtk")
    reader = braviz.readAndFilter.BravizAutoReader()
    application = tornado.web.Application(
        [
            (r"/data/(.*)",XtkDataHandler, {'reader': reader}),
            (r"/",XtkHandler, ),
        ],
        **settings)
    try:

        application.listen(8100)
        tornado.ioloop.IOLoop.instance().start()
    except Exception:
        print("Couldn't start server, maybe already running?")
