from __future__ import division

import vtk
import numpy as np
import nibabel as nib
import itertools

import braviz
from braviz.readAndFilter import geom_db
from braviz.readAndFilter import write_nib_image
from braviz.readAndFilter import tabular_data

__author__ = 'da.angulo39'


def export_roi(subject, roi_id, space, out_file, reader=None):

    sphere_img,affine,hdr = generate_roi_image(subject,roi_id,space,reader)
    print "h"
    nib_image = nib.Nifti1Image(sphere_img,affine,hdr)
    nib_image.update_header()
    nib_image.to_filename(out_file)


def generate_roi_image(subject, roi_id, space, reader=None):
    if reader is None:
        reader = braviz.readAndFilter.BravizAutoReader()

    r, x, y, z = geom_db.load_sphere(roi_id, subject)
    r2 = r*r
    sphere_space = geom_db.get_roi_space(roi_id=roi_id)
    subject_id = tabular_data.get_var_value(tabular_data.IMAGE_CODE,subject)
    fa = reader.get("fa", subject_id, space="diff")

    affine = fa.get_affine()
    new_data = np.zeros(fa.get_shape(),fa.get_data_dtype())

    h_coords = np.ones(4)
    ctr = np.array((x,y,z))
    points = vtk.vtkPoints()
    points.SetNumberOfPoints(new_data.size)
    for i in xrange(new_data.size):
        h_coords[3]=1
        index = np.unravel_index(i, new_data.shape)
        h_coords[0:3] = index
        h_point = affine.dot(h_coords)
        p = h_point[0:3]/h_point[3]
        points.SetPoint(i,p)
    pd = vtk.vtkPolyData()
    pd.SetPoints(points)
    print "bu"
    pp_w = reader.transform_points_to_space(pd,"diff",subject_id,inverse=True)
    pp_s = reader.transform_points_to_space(pp_w,sphere_space,subject_id,inverse=False)
    points_sphere = pp_s.GetPoints()
    print "ba"
    j = 0
    for i in xrange(new_data.size):
        p_s = points_sphere.GetPoint(i)
        p_m_c = (p_s - ctr)
        if np.dot(p_m_c,p_m_c) <= r2:
            new_data[np.unravel_index(i, new_data.shape)]=255
            j+=1
    print j
    return new_data,affine,fa.get_header()


if __name__ == "__main__":
    #generate_roi_image(144,3,"world")
    export_roi(119,1,"diff",r"D:\kmc400-braviz\test.nii.gz")