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
TR=3
#global variables
current_volume=34
current_x_coord=25
current_y_coord=10
spatial_slice=34

os.chdir(r'C:\Users\Diego\Documents\kmc40-db\KAB-db\%s\spm\POWERGRIP'%subject)
img_4d=nib.load('smoothed.nii.gz')
data_d4=img_4d.get_data()
vol0=data_d4[spatial_slice,:,:,:]
vol0=np.rollaxis(vol0,2)
nslices=vol0.shape[0]
vtk0=braviz.readAndFilter.numpy2vtk_img(vol0)
vtk0.SetSpacing(TR,2,2) #Hacky
#img=reader.get('fMRI',subject,name='powergrip',format='vtk')
img=vtk0

slice_mapper=vtk.vtkImageSliceMapper()
slice_mapper.SetInputData(img)
slice_mapper.SetOrientationToX()
slice_actor=vtk.vtkImageSlice()
slice_actor.SetMapper(slice_mapper)
viewer.ren.AddActor(slice_actor)
slice_mapper.SetSliceNumber(current_volume)
slice_actor.SetPosition(-1*TR*slice_mapper.GetSliceNumber(),0,0)

image_property=vtk.vtkImageProperty()
slice_actor.SetProperty(image_property)

image_property.SetColorWindow(2000)
image_property.SetColorLevel(1000)


#============CURSORS=====================

cursor_x=vtk.vtkLineSource()
cursor_x_mapper=vtk.vtkPolyDataMapper()
cursor_x_mapper.SetInputConnection(cursor_x.GetOutputPort())
cursor_x_actor=vtk.vtkActor()
cursor_x_actor.SetMapper(cursor_x_mapper)
viewer.ren.AddActor(cursor_x_actor)

cursor_y=vtk.vtkLineSource()
cursor_y_mapper=vtk.vtkPolyDataMapper()
cursor_y_mapper.SetInputConnection(cursor_y.GetOutputPort())
cursor_y_actor=vtk.vtkActor()
cursor_y_actor.SetMapper(cursor_y_mapper)
viewer.ren.AddActor(cursor_y_actor)

cursor_x_actor.GetProperty().SetColor(1.0 , 0 , 0)
cursor_y_actor.GetProperty().SetColor(1.0 , 0 , 0)

def set_cursor(x,y):
    current_slice=slice_mapper.GetSliceNumber()
    dz,dx,dy=img.GetSpacing()
    dz=0
    cursor_x.SetPoint1((dz*current_slice,dx*x,dy*0))
    cursor_x.SetPoint2((dz*current_slice,dx*x,dy*68))
    cursor_y.SetPoint1((dz*current_slice,dx*0,dy*y))
    cursor_y.SetPoint2((dz*current_slice,dx*95,dy*y))




#=====================IMAGE PICKING=======================
p=vtk.vtkCellPicker()
p.SetTolerance(0.001)
viewer.iren.SetPicker(p)

def picking_observer(caller=None,event=None):
    global current_x_coord,current_y_coord
    x,y= p.GetPointIJK()[1:]
    set_cursor(x,y)
    current_x_coord=x
    current_y_coord=y
    calculate_bold_signal(x,y)
    t_score=get_t_score(x,y)
    add_t_chart()
    #print "t-score=%f"%t_score
slice_actor.AddObserver(vtk.vtkCommand.PickEvent,picking_observer)



#========================T-SCORE=============================
t_stat_img=reader.get('fMRI',subject,name='powergrip',space='native',format='vtk')

def get_t_score(x,y):
    return t_stat_img.GetScalarComponentAsDouble(spatial_slice,x,y,0)

t_ctxt=vtk.vtkContextActor()
t_chart=vtk.vtkChartXY()
t_scene=vtk.vtkContextScene()

t_chart.SetAutoSize(False)
t_chart.SetSize(vtk.vtkRectf(200,200,400,400))
t_scene.AddItem(t_chart)
t_ctxt.SetScene(t_scene)

viewer.ren.AddActor(t_ctxt)
t_scene.SetRenderer(viewer.ren)
t_table=vtk.vtkTable()
arr_t=vtk.vtkFloatArray()
arr_t.SetName("T-score")

arri_t=vtk.vtkFloatArray()
arri_t.SetName("index")

t_table.AddColumn(arri_t)
t_table.AddColumn(arr_t)
t_table.SetNumberOfRows(1)

fmri_color_int=vtk.vtkColorTransferFunction()
fmri_color_int.ClampingOn()
fmri_color_int.SetColorSpaceToRGB()
fmri_color_int.SetRange(-7,7)
fmri_color_int.Build()
#                           x   ,r   ,g   , b
fmri_color_int.AddRGBPoint(-7.0 ,0.0 ,1.0 ,1.0)
fmri_color_int.AddRGBPoint(-3.0 ,0.0 ,0.0 ,0.0)
fmri_color_int.AddRGBPoint( 0.0 ,0.0 ,0.0 ,0.0)
fmri_color_int.AddRGBPoint( 3.0 ,0.0 ,0.0 ,0.0)
fmri_color_int.AddRGBPoint( 7.0 ,1.0 ,0.27,0.0)


def add_t_chart():

    t_table.SetValue(0,0,1)
    t_score=get_t_score(current_x_coord,current_y_coord)
    t_table.SetValue(0,1,t_score)
    color=fmri_color_int.GetColor(t_score)
    t_chart.ClearPlots()
    t_bar=t_chart.AddPlot(vtk.vtkChart.BAR)
    t_bar.SetInputData(t_table,0,1)
    rgb_color=np.concatenate((np.dot(color,255),(255,)))
    rgb_color=rgb_color.astype(int)
    t_bar.SetColor(*rgb_color)
    t_bar.SetWidth(4.0)
    t_ay=t_chart.GetAxis(0)
    t_ay.SetMinimum(-5)
    t_ay.SetMaximum(5)
    t_ay.SetBehavior(1)
    t_ay.SetTitle("T-score")

    t_ax=t_chart.GetAxis(1)

    t_ax.SetGridVisible(0)
    t_ax.SetTicksVisible(0)
    t_ax.SetLabelsVisible(0)
    t_ax.SetBehavior(1)
    t_ax.SetMinimum(0.9)
    t_ax.SetMaximum(1.1)
    t_ax.SetTitle('')

#====================CHART================================
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
arrX.SetName("Time")

arrC=vtk.vtkFloatArray()
arrC.SetName("Bold")

arrS=vtk.vtkFloatArray()
arrS.SetName("Design")


table.AddColumn(arrC)
table.AddColumn(arrS)
table.AddColumn(arrX)



table.SetNumberOfRows(nslices-1) #ignoring first volume as it contains significantive larger signal
for i in xrange(nslices-1):
    table.SetValue(i,0,(i+1)*TR)

    #table.SetValue(i,2,math.sin(i*inc*omega))


#=====================BOLD SIGNAL=========================
def calculate_bold_signal(x,y):
    bold_signal=vol0[:,x,y]
    for i in xrange(nslices-1):
        table.SetValue(i,1,float(bold_signal[i+1]))
    chart.ClearPlots()
    points=chart.AddPlot(vtk.vtkChart.LINE)
    points.SetInputData(table,0,1)
    points.SetColor(0,0,0,255)
    points.SetWidth(1.0)
    points.SetMarkerStyle(vtk.vtkPlotPoints.CROSS)
    ay=chart.GetAxis(0)
    ay.SetBehavior(0)
    chart.Update()
    viewer.renWin.Render()
    add_line_to_graph(current_volume*TR)
    add_experiment_design()
    viewer.renWin.Render()
#=========================================================


#================Experiment design========================
base_design=([0]*10+[1]*10)*4
assert len(base_design)==80
base_design=np.array( base_design )
def add_experiment_design():
    ay=chart.GetAxis(0)
    min_y=ay.GetMinimum()
    max_y=ay.GetMaximum()
    scale=max_y-min_y
    ay.SetBehavior(1)
    design=np.dot(base_design,scale*0.8)+(min_y+0.1*scale)
    for i in xrange(nslices-1):
        table.SetValue(i,2,float(design[i+1]))
    points=chart.AddPlot(vtk.vtkChart.LINE)
    points.SetInputData(table,0,2)
    points.SetColor(0,0,255,255)
    points.SetWidth(1.0)
    points.SetMarkerStyle(vtk.vtkPlotPoints.NONE)

ax=chart.GetAxis(1)
ax.SetMaximum(nslices*TR)
ax.SetMaximumLimit(nslices*TR)
ax.SetTitle('Time (s)')

ay=chart.GetAxis(0)
ay.SetTitle('Bold Signal')
viewer.ren.SetBackground(0.8,0.8,0.8)
viewer.renWin.SetMultiSamples(4)


line_plot_id=None
def add_line_to_graph(coord=None):
    global line_plot_id
    if coord==None:
        coord=current_volume*TR
    global line_plot_id
    if line_plot_id:
        chart.RemovePlot(line_plot_id)
    line_plot_id=chart.GetNumberOfPlots()
    line=chart.AddPlot(vtk.vtkChart.LINE)
    line.SetColor(255,0,0,255)
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
    ay.SetBehavior(1)
    line_table.SetValue(0,0,coord) #x
    line_table.SetValue(1,0,coord) #x
    line_table.SetValue(0,1,min_y) #y
    line_table.SetValue(1,1,max_y) #y
    line.SetInputData(line_table,0,1)

def click_event_handler(caller=None,event=None):
    global current_volume
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
        current_volume=slice_idx
        slice_mapper.SetSliceNumber(slice_idx)
        slice_actor.SetPosition(-1*TR*slice_idx,0,0)#To keep it still
        command=caller.GetCommand(click_obs_id)
        command.SetAbortFlag(1)

        viewer.renWin.Render()

def click_to_pick(caller=None,event=None):
    ex,ey=viewer.iren.GetEventPosition()
    if p.Pick(ex,ey,0,viewer.ren):
        command=caller.GetCommand(click_obs_id)
        command.SetAbortFlag(1)

click_obs_id=viewer.iren.AddObserver('LeftButtonPressEvent',click_event_handler,10)
click_to_pick_obs_id=viewer.iren.AddObserver('LeftButtonPressEvent',click_to_pick,9)
def resize_event_handler(obj=None,event=None):
    #print 'Resize detected'
    new_width=viewer.renWin.GetSize()[0]
    new_height=viewer.renWin.GetSize()[1]
    chart.SetSize(vtk.vtkRectf(0,0,new_width,new_height//3))
    t_chart.SetSize(vtk.vtkRectf(new_width-110,new_height-110,
                                 100,100))

scene.AddObserver('ModifiedEvent',resize_event_handler)

def slicing_event(obj=None,event=None):
    #coord=plane_widget.GetSliceIndex()
    coord=10
    add_line_to_graph(coord)

#plane_widget.AddObserver(plane_widget.slice_change_event,slicing_event)

viewer.iren.Initialize()
viewer.renWin.Render()
cam1=viewer.ren.GetActiveCamera()
cam1.Azimuth(120)

set_cursor(current_x_coord,current_y_coord)
calculate_bold_signal(current_x_coord,current_y_coord)
add_t_chart()
#slicing_event()

viewer.start()