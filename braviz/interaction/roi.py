from __future__ import division

import vtk
import numpy as np
import nibabel as nib
import itertools

import braviz
from braviz.readAndFilter import geom_db
from braviz.readAndFilter import write_image
from braviz.readAndFilter import tabular_data

__author__ = 'da.angulo39'


def export_roi(subject, roi_id, space, out_file, reader=None):

    sphere_img = generate_roi_image(subject,roi_id,space,reader)
    write_image(sphere_img,out_file)


def generate_roi_image(subject, roi_id, space, reader=None):
    if reader is None:
        reader = braviz.readAndFilter.BravizAutoReader()

    r, x, y, z = geom_db.load_sphere(roi_id, subject)
    sphere_space = geom_db.get_roi_space(roi_id=roi_id)
    subject_id = tabular_data.get_var_value(tabular_data.IMAGE_CODE,subject)
    mri = reader.get("mri", subject_id, space=sphere_space, format="vtk")

    sx, sy, sz = mri.GetSpacing()
    ox, oy, oz = mri.GetOrigin()

    rx = r / sx
    ry = r / sy
    rz = r / sz

    cx = (x - ox) / sx
    cy = (y - oy) / sy
    cz = (z - oz) / sz

    source = vtk.vtkImageEllipsoidSource()
    source.SetCenter(cx, cy, cz)
    source.SetRadius(rx, ry, rz)

    extent = mri.GetExtent()
    source.SetWholeExtent(extent)
    source.Update()

    sphere_img_p = source.GetOutput()
    sphere_img_p.SetOrigin(ox, oy, oz)
    sphere_img_p.SetSpacing(sx, sy, sz)

    #move to world
    sphere_img_w=reader.move_img_to_world(sphere_img_p,sphere_space,subject)

    #move to out
    sphere_img=reader.move_img_from_world(sphere_img_w,space,subject)

    return sphere_img


