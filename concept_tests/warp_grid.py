from __future__ import division

import vtk
import numpy as np

import braviz
from braviz import _test_arrow


__author__ = 'Diego'
subject='143'

reader=braviz.readAndFilter.BravizAutoReader()
viewer= simpleVtkViewer()

orig_img=reader.get('MRI',subject,space='subject',format='vtk')
target_space='dartel'
#target_space='talairach'

def build_grid(img,slice,sampling_rate=5):
    dimensions=orig_img.GetDimensions()
    spacing = orig_img.GetSpacing()
    origin = orig_img.GetOrigin()
    n_points=int(dimensions[1]*dimensions[2])
    def img2world(i,j,k):
        return np.array((i,j,k))*spacing+origin
    def flat_index(j,k):
        return j*dimensions[2]+k
    points=vtk.vtkPoints()
    points.SetNumberOfPoints(n_points)
    for j in xrange(dimensions[1]):
        for k in xrange(dimensions[2]):
            idx=flat_index(j,k)
            coords=img2world(slice,j,k)
            points.SetPoint(idx,coords)
    grid=vtk.vtkPolyData()
    grid.SetPoints(points)
    lines=vtk.vtkCellArray()
    #vertical:
    for j in xrange(dimensions[1]):
        if j%sampling_rate==0:
            lines.InsertNextCell(dimensions[2])
            for k in xrange(dimensions[2]):
                lines.InsertCellPoint(flat_index(j, k))
    #horizontal
    for k in xrange(dimensions[2]):
        if k % sampling_rate == 0:
            lines.InsertNextCell(dimensions[1])
            for j in xrange(dimensions[1]):
                lines.InsertCellPoint(flat_index(j, k))

    grid.SetLines(lines)
    cleaner=vtk.vtkCleanPolyData()
    cleaner.SetInputData(grid)
    cleaner.Update()
    clean_grid=cleaner.GetOutput()
    return clean_grid

dartel_img=reader.get('MRI',subject,space=target_space,format='vtk')


pw=viewer.addImg(dartel_img)
pw.GetTexturePlaneProperty().SetOpacity(0.8)

pd_act=None
def add_grid(slice_idx):
    global pd_act
    if pd_act is not None:
        viewer.ren.RemoveActor(pd_act)
    test_grid=build_grid(orig_img,slice_idx)
    dertel_grid=reader.transform_points_to_space(test_grid,target_space,subject)
    pd_act=viewer.addPolyData(dertel_grid)

add_grid(128)
viewer.start()

def get_orig_slice_index():
    p1 = pw.GetPoint1()
    p2 = pw.GetPoint2()
    center=(np.array(p1)+np.array(p2))/2
    orig_center=reader.transform_points_to_space(center, target_space, subject, True)
    orig_img_center=(np.array(orig_center)-orig_img.GetOrigin())/orig_img.GetSpacing()
    orig_slice=round(orig_img_center[0])
    #print orig_slice
    add_grid(orig_slice)
get_orig_slice_index()
viewer.renWin.Render()
viewer.start()