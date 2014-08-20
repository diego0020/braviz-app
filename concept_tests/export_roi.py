from __future__ import division

import vtk
import numpy as np
import nibabel as nib
import itertools

import braviz
from braviz.readAndFilter import geom_db

__author__ = 'da.angulo39'

def export_roi(subject,roi_id,space,out_file,reader=None):
    if reader is None:
        reader = braviz.readAndFilter.BravizAutoReader()

    r,x,y,z = geom_db.load_sphere(roi_id,subject)
    sphere_space = geom_db.get_roi_space(roi_id=roi_id)
    mri = reader.get("mri",subject,space=sphere_space,format="vtk")
    sx,sy,sz = mri.GetSpacing()
    ox,oy,oz = mri.GetOrigin()

    rx = r/sx
    ry = r/sy
    rz = r/sz

    cx = (x-ox)/sx
    cy = (y-oy)/sy
    cz = (z-oz)/sz

    source = vtk.vtkImageEllipsoidSource()
    source.SetCenter(cx,cy,cz)
    source.SetRadius(rx,ry,rz)

    print cx,cy,cz

    extent = mri.GetExtent()
    source.SetWholeExtent(extent)
    source.Update()

    sphere_img_p = source.GetOutput()
    sphere_img_p.SetOrigin(ox,oy,oz)
    sphere_img_p.SetSpacing(sx,sy,sz)

    #move to world
    sphere_img_w=reader.move_img_to_world(sphere_img_p,sphere_space,subject)

    #move to out
    sphere_img=reader.move_img_from_world(sphere_img_w,space,subject)

    viewer = braviz.visualization.simpleVtkViewer()
    viewer.addImg(sphere_img)
    viewer.start()

    dx,dy,dz = sphere_img.GetDimensions()
    data = np.zeros((dx,dy,dz),np.uint8)
    for i,j,k in itertools.product(xrange(dx),xrange(dy),xrange(dz)):
        v = sphere_img.GetScalarComponentAsDouble(i,j,k,0)
        data[i,j,k]=v
    af = np.eye(4)
    sx,sy,sz = sphere_img.GetSpacing()
    ox,oy,oz = sphere_img.GetOrigin()
    af[0,0],af[1,1],af[2,2]=sx,sy,sz
    af[0,3],af[1,3],af[2,3]=ox,oy,oz
    nib_img = nib.Nifti1Image(data,affine=af)
    nib_img.to_filename(out_file)

    print out_file

if __name__ == "__main__":
    subject = 1021
    space = "talairach"
    roi_id = 9
    out_file = "D:/temp/roi.nii.gz"
    export_roi(subject,roi_id,space,out_file)
    print "done"