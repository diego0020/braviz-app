from __future__ import division
__author__ = 'Diego'

import braviz
import vtk
import math
import os
import numpy as np
import nibabel as nib

reader=braviz.readAndFilter.kmc40AutoReader()
viewer=braviz.visualization.simpleVtkViewer()

subject='144'
slice=34
world_coordinates=(-33,-74-1)
TR=3

os.chdir(r'C:\Users\Diego\Documents\kmc40-db\KAB-db\144\spm\POWERGRIP')
img_4d=nib.load('smoothed.nii.gz')
data_d4=img_4d.get_data()
vol0=data_d4[slice,:,:,:]
vol0=np.rollaxis(vol0,2)
nslices=vol0.shape[0]
vtk0=braviz.readAndFilter.numpy2vtk_img(vol0)
vtk0.SetSpacing(0,2,2)
#img=reader.get('fMRI',subject,name='powergrip',format='vtk')
img=vtk0

slice_mapper=vtk.vtkImageSliceMapper()
slice_mapper.SetInputData(img)
slice_mapper.SetOrientationToX()
slice_actor=vtk.vtkImageSlice()
slice_actor.SetMapper(slice_mapper)
viewer.ren.AddActor(slice_actor)
slice_mapper.SetSliceNumber(slice)

image_property=vtk.vtkImageProperty()
slice_actor.SetProperty(image_property)
image_property.SetColorWindow(2000)
image_property.SetColorLevel(1000)


#plane_widget=viewer.addImg(img)
#plane_widget.SetResliceInterpolateToNearestNeighbour()
ctxt=vtk.vtkContextActor()
chart=vtk.vtkChartXY()
scene=vtk.vtkContextScene()

chart.SetAutoSize(False)
chart.SetSize(vtk.vtkRectf(0,0,300,200))
scene.AddItem(chart)
ctxt.SetScene(scene)

viewer.ren.AddActor(ctxt)
scene.SetRenderer(viewer.ren)

table=vtk.vtkTable()
arrX=vtk.vtkFloatArray()
arrX.SetName('X Axis')

arrC=vtk.vtkFloatArray()
arrC.SetName('Cosine')

arrS=vtk.vtkFloatArray()
arrS.SetName('Sine')

arrT=vtk.vtkFloatArray()
arrT.SetName('Sine-Cosine')

table.AddColumn(arrC)
table.AddColumn(arrS)
table.AddColumn(arrX)
table.AddColumn(arrT)

numPoints=nslices

inc=1
table.SetNumberOfRows(numPoints)
tao=100
omega=2*math.pi/tao
for i in xrange(numPoints):
    table.SetValue(i,0,i*TR*inc)
    table.SetValue(i,1,math.cos(i*inc*omega))
    table.SetValue(i,2,math.sin(i*inc*omega))
    table.SetValue(i,3,math.sin(i*inc*omega)-math.cos(i*inc*omega))

points=chart.AddPlot(vtk.vtkChart.LINE)
points.SetInputData(table,0,1)
points.SetColor(0,0,0,255)
points.SetWidth(1.0)
points.SetMarkerStyle(vtk.vtkPlotPoints.CROSS)

points=chart.AddPlot(vtk.vtkChart.LINE)
points.SetInputData(table,0,2)
points.SetColor(0,0,0,255)
points.SetWidth(1.0)
points.SetMarkerStyle(vtk.vtkPlotPoints.PLUS)

#points=chart.AddPlot(vtk.vtkChart.POINTS)
#points.SetInputData(table,0,3)
#points.SetColor(0,0,255,255)
#points.SetWidth(1.0)
#points.SetMarkerStyle(vtk.vtkPlotPoints.CIRCLE)

ax=chart.GetAxis(1)
ax.SetMaximum(nslices*TR)
ax.SetMaximumLimit(nslices*TR)
ax.SetTitle('Time (s)')

ay=chart.GetAxis(0)
ay.SetTitle('Bold Signal')
viewer.ren.SetBackground(0.8,0.8,0.8)
viewer.renWin.SetMultiSamples(4)


line_plot_id=None
def add_line_to_graph(coord):
    global line_plot_id
    if line_plot_id:
        chart.RemovePlot(line_plot_id)
    line_plot_id=chart.GetNumberOfPlots()
    line=chart.AddPlot(vtk.vtkChart.LINE)
    line_table=vtk.vtkTable()
    arrlX=vtk.vtkFloatArray()
    arrlX.SetName('X line')
    arrlY=vtk.vtkFloatArray()
    arrlY.SetName('Y line')
    line_table.AddColumn(arrlX)
    line_table.AddColumn(arrlY)
    line_table.SetNumberOfRows(2)
    ay=chart.GetAxis(0)
    min_y=ay.GetMinimum()
    max_y=ay.GetMaximum()
    line_table.SetValue(0,0,coord) #x
    line_table.SetValue(1,0,coord) #x
    line_table.SetValue(0,1,min_y) #y
    line_table.SetValue(1,1,max_y) #y
    line.SetInputData(line_table,0,1)

def click_event_handler(caller=None,event=None):
    #print event
    #print obj
    position=caller.GetEventPosition()
    p1=chart.GetPoint1()
    p2=chart.GetPoint2()
    if p1[0] < position[0] < p2[0] and p1[1] < position[1] < p2[1]:
        #print 'Click detected'
        #print position
        ax=chart.GetAxis(1)
        t=(position[0]-ax.GetPoint1()[0])/(ax.GetPoint2()[0]-ax.GetPoint1()[0])
        coord=ax.GetMinimum()+(ax.GetMaximum()-ax.GetMinimum())*t
        #print coord
        slice_idx=int(round(coord/TR))
        add_line_to_graph(slice_idx*TR)
        #plane_widget.SetSliceIndex(slice_idx)
        slice_mapper.SetSliceNumber(slice_idx)

        command=caller.GetCommand(click_obs_id)
        command.SetAbortFlag(1)
        viewer.renWin.Render()


click_obs_id=viewer.iren.AddObserver('LeftButtonPressEvent',click_event_handler,10)

def resize_event_handler(obj=None,event=None):
    #print 'Resize detected'
    new_width=viewer.renWin.GetSize()[0]
    new_height=viewer.renWin.GetSize()[1]
    chart.SetSize(vtk.vtkRectf(0,0,new_width,new_height//3))

scene.AddObserver('ModifiedEvent',resize_event_handler)

def slicing_event(obj=None,event=None):
    #coord=plane_widget.GetSliceIndex()
    coord=10
    add_line_to_graph(coord)

#plane_widget.AddObserver(plane_widget.slice_change_event,slicing_event)

viewer.iren.Initialize()
viewer.renWin.Render()
cam1=viewer.ren.GetActiveCamera()
cam1.Azimuth(180)

#slicing_event()

viewer.start()