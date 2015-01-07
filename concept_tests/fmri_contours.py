from __future__ import division
import vtk
import braviz
from braviz.visualization.simple_vtk import _test_arrow

__author__ = 'Diego'

reader = braviz.readAndFilter.BravizAutoReader()
subject = reader.get("ids")[0]
pdgms = reader.get("fmri",None,index=True)
pdgm = list(pdgms)[0]
fmri_img = reader.get("fmri",subject,name=pdgm,contrast=1,format="vtk",space = "fmri-%s"%pdgm)

viewer = simpleVtkViewer()
viewer.addImg(fmri_img)

contour_filter = vtk.vtkContourFilter()
contour_filter.UseScalarTreeOn()
contour_filter.SetInputData(fmri_img)

contour_filter.SetValue(0,2.0)
contour_filter.ComputeNormalsOff()
contour_filter.Update()
out = contour_filter.GetOutput()

ac = viewer.addPolyData(out)

viewer.start()