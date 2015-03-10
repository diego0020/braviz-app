from __future__ import division
import braviz
from braviz.visualization import simple_vtk
import vtk
import numpy as np
import os

__author__ = 'da.angulo39'


file_name=os.path.normpath(r"C:\Users\da.angulo39\Documents\axial.png")
perpendicular=np.array((0,0,1))
x=np.array((0,-1,0))
y=np.array((-1,0,0))

# file_name=os.path.normpath(r"C:\Users\da.angulo39\Documents\sagital2.png")
# perpendicular=np.array((-1,0,0))
# x=np.array((0,1,0))
# y=np.array((0,0,1))

#file_name=os.path.normpath(r"C:\Users\da.angulo39\Documents\sagital.png")
#perpendicular=np.array((1,0,0))
#x=np.array((0,1,0))
#y=np.array((0,0,1))


r=braviz.readAndFilter.BravizAutoReader()

lh=r.get("surf",15,hemi="l",name="pial",scalars="aparc")
rh=r.get("surf",15,hemi="r",name="pial",scalars="aparc")
lut=r.get("surf_scalar",15,lut=True,scalars="aparc")
box=vtk.vtkBox()
box.AddBounds(lh.GetBounds())
box.AddBounds(rh.GetBounds())
print box


xmin=np.array([0,0,0])
box.GetXMin(xmin)
xmax=np.array([0,0,0])
box.GetXMax(xmax)

v=simple_vtk.SimpleVtkViewer()
v.addPolyData(lh,LUT=lut)
v.addPolyData(rh,LUT=lut)
v.start()

camera=v.ren.GetActiveCamera()



center=(xmin+xmax)/2
pos=center+perpendicular*100

extent=xmax-xmin
print extent
width=np.abs(extent.dot(x))
height=np.abs(extent.dot(y))

factor=width/height

win_width=800
win_height=int(round(800/factor))
v.renWin.SetSize(win_width,win_height)

camera.ParallelProjectionOn()
camera.SetPosition(pos)
camera.SetFocalPoint(center)
camera.SetViewUp(y)
camera.SetParallelScale(np.abs(extent.dot(y))*0.5)

near=((pos-center).dot(perpendicular)-np.abs(extent.dot(perpendicular)/2))*0.9
far=((pos-center).dot(perpendicular)+np.abs(extent.dot(perpendicular)/2))*1.1

camera.SetClippingRange(near,far)

v.iren.Start()

file_filter=vtk.vtkWindowToImageFilter()
file_filter.SetInput(v.renWin)
file_filter.SetMagnification(3)
file_filter.Update()

writer=vtk.vtkPNGWriter()


writer.SetFileName(file_name)
writer.SetInputConnection(file_filter.GetOutputPort())
writer.Write()
