from __future__ import division
import os

from numpy.linalg import inv
import vtk
import numpy as np
import nibabel as nib

from braviz.readAndFilter import nibNii2vtk,applyTransform
import braviz
import braviz.visualization.vtk_charts
from braviz.readAndFilter.readDartelTransform import dartel2GridTransform_cached as dartel2GridTransform

__author__ = 'Diego'



reader=braviz.readAndFilter.kmc40AutoReader()
viewer=braviz.visualization.simpleVtkViewer()

#====================global variables===========
subject='144'
TR=3
current_volume=34
current_x_coord=25
current_y_coord=10
spatial_slice=62

current_mode='space' #time or space
#===============================================

#====================BOLD IMAGE==================

root_dir=reader.getDataRoot()
test_dir=os.path.join(root_dir,'%s\spm\POWERGRIP'%subject)
#os.chdir(r'C:\Users\Diego\Documents\kmc40-db\KAB-db\%s\spm\POWERGRIP'%subject)
os.chdir(test_dir)
img_4d=nib.load('smoothed.nii.gz')
data_d4=img_4d.get_data()

slice_mapper=vtk.vtkImageSliceMapper()


def get_time_vol(spatial_slice):
    global vol0,vtk0,nslices
    vol0=data_d4[spatial_slice,:,:,:]
    vol0=np.rollaxis(vol0,2)
    nslices=vol0.shape[0]
    vtk0=braviz.readAndFilter.numpy2vtk_img(vol0)
    vtk0.SetSpacing(TR,2,2)
    slice_mapper.SetInputData(vtk0)
#img=reader.get('fMRI',subject,name='powergrip',format='vtk')
get_time_vol(spatial_slice)

slice_mapper.SetOrientationToX()
slice_actor=vtk.vtkImageSlice()
slice_actor.SetMapper(slice_mapper)
viewer.ren.AddActor(slice_actor)
slice_mapper.SetSliceNumber(current_volume)
slice_actor.SetPosition(-1*TR*slice_mapper.GetSliceNumber()-2*spatial_slice,0,0)

slice_actor.SetVisibility(0)

image_property=vtk.vtkImageProperty()
slice_actor.SetProperty(image_property)

image_property.SetColorWindow(2000)
image_property.SetColorLevel(1000)


#============CURSORS=====================

cursors=braviz.visualization.cursors()
cursors.set_spacing(-2,2,2)
set_cursor= cursors.set_cursor

viewer.ren.AddActor(cursors)
#===============T-IMAGE=================
plane_widget=braviz.visualization.persistentImagePlane()
#plane_widget.EnabledOff()

fa_lut=vtk.vtkLookupTable()
fa_lut.SetRampToLinear ()
fa_lut.SetTableRange(0.0,1.0)
fa_lut.SetHueRange(0.0, 0.0)
fa_lut.SetSaturationRange(1.0, 1.0)
fa_lut.SetValueRange(0.0, 1.0)
fa_lut.Build()

fmri_color_int=vtk.vtkColorTransferFunction()
fmri_color_int.ClampingOn()
fmri_color_int.SetColorSpaceToRGB()
fmri_color_int.SetRange(-7,7)
fmri_color_int.Build()
#                           x   ,r   ,g   , b
fmri_color_int.AddRGBPoint(-7.0 ,0.0 ,1.0 ,1.0)
#fmri_color_int.AddRGBPoint(-3.0 ,0.0 ,0.0 ,0.0)
fmri_color_int.AddRGBPoint( 0.0 ,0.0 ,0.0 ,0.0)
#fmri_color_int.AddRGBPoint( 3.0 ,0.0 ,0.0 ,0.0)
fmri_color_int.AddRGBPoint( 7.0 ,1.0 ,0.27,0.0)

fmri_lut=vtk.vtkLookupTable()
fmri_lut.SetTableRange(-7.0,7.0)
fmri_lut.SetNumberOfColors(101)
fmri_lut.Build()
for i in range(101):
    s=-7+14*i/100
    if False and (s<-3 or s>3):
        color=list(fmri_color_int.GetColor(s))+[0.0]
    else:
        color=list(fmri_color_int.GetColor(s))+[1.0]
    #print color
    fmri_lut.SetTableValue(i,color)

t_stat_img=reader.get('fMRI',subject,name='powergrip',space='native',format='vtk')
t_stat_img.SetSpacing([-2,2,2])
#move T1_img to fmri space
origin2=(78,-112,-50)
dimension2=(79,95,68)
spacing2=(-2,2,2)

print origin2
print dimension2
print spacing2

t1_img=nib.load('T1.nii.gz')
t1_img_vtk=nibNii2vtk(t1_img)
t1_img_vtk=applyTransform(t1_img_vtk, inv(t1_img.get_affine()))
dartel_trans=dartel2GridTransform('y_seg_back.nii.gz',True)
mri_img=applyTransform(t1_img_vtk, dartel_trans, origin2, dimension2, spacing2)
mri_img.SetOrigin((0,0,0))
mri_img.SetSpacing((-2,2,2))

#blend

blend=vtk.vtkImageBlend()

color_mapper2=vtk.vtkImageMapToColors()
color_mapper2.SetInputData(t_stat_img)
color_mapper2.SetLookupTable(fmri_color_int)




color_mapper1=vtk.vtkImageMapToWindowLevelColors()
color_mapper1.SetInputData(mri_img)
mri_lut=vtk.vtkWindowLevelLookupTable()
mri_lut.Build()
color_mapper1.SetLookupTable(mri_lut)

mri_lut.SetWindow(2000)
mri_lut.SetLevel(647)



blend.AddInputConnection(color_mapper2.GetOutputPort())
blend.AddInputConnection(color_mapper1.GetOutputPort())

blend.SetOpacity(0,0.5)
blend.SetOpacity(1,0.5)
blend.Update()

plane_widget.SetInputConnection(blend.GetOutputPort())
plane_widget.SetInteractor(viewer.iren)
plane_widget.On()
plane_widget.GetColorMap().SetLookupTable(None)
plane_widget.DisplayTextOff()

# An outline is shown for context.
outline = vtk.vtkOutlineFilter()
outline.SetInputData(t_stat_img)

outlineMapper = vtk.vtkPolyDataMapper()
outlineMapper.SetInputConnection(outline.GetOutputPort())

outlineActor = vtk.vtkActor()
outlineActor.SetMapper(outlineMapper)
viewer.ren.AddActor(outlineActor)

#=========================EXTRA INTERACTION IN SPACE MODE======================================================

def copy_cursor(caller,event,event_name='std'):
    global current_x_coord,current_y_coord,spatial_slice
    if event_name=='slice_change':
        spatial_slice=caller.GetSliceIndex()
        get_time_vol(spatial_slice)
        calculate_bold_signal(spatial_slice,current_x_coord,current_y_coord)
        set_cursor(spatial_slice,current_x_coord,current_y_coord)
        refresh_t_chart()
    else:
        cursor_pos=caller.GetCurrentCursorPosition()
        calculate_bold_signal(*cursor_pos)
        spatial_slice=caller.GetSliceIndex()
        current_x_coord=cursor_pos[1]
        current_y_coord=cursor_pos[2]
        set_cursor(spatial_slice,current_x_coord,current_y_coord)
        refresh_t_chart()

plane_widget.SetSliceIndex(spatial_slice)
custom_id=plane_widget.AddObserver(plane_widget.cursor_change_event,lambda x,y: copy_cursor(x,y,'cursor_change'))
custom_id2=plane_widget.AddObserver(plane_widget.slice_change_event,lambda x,y: copy_cursor(x,y,'slice_change'))

#=====================IMAGE PICKING=======================
p=vtk.vtkCellPicker()
p.SetTolerance(0.001)
viewer.iren.SetPicker(p)

def picking_observer(caller=None,event=None):
    #print "pica pica"
    global current_x_coord,current_y_coord
    x,y= p.GetPointIJK()[1:]
    set_cursor(spatial_slice,x,y)
    current_x_coord=x
    current_y_coord=y
    calculate_bold_signal(spatial_slice,x,y)
    t_score=get_t_score(spatial_slice,x,y)
    refresh_t_chart()
    #print "t-score=%f"%t_score
slice_actor.AddObserver(vtk.vtkCommand.PickEvent,picking_observer)



#========================T-SCORE=============================


def get_t_score(z,x,y):
    return t_stat_img.GetScalarComponentAsDouble(int(z),int(x),int(y),0)

t_ctxt = braviz.visualization.vtk_charts.BarPlot()

win_width = viewer.renWin.GetSize()[0]
win_height = viewer.renWin.GetSize()[1]
t_ctxt.set_position(win_width - 110, win_height - 110, 100, 100)

t_ctxt.set_x_axis(title="%(value)f",visible=False)
t_ctxt.set_y_axis(title="SPM-T Score",limits=(-7,7),ticks=(-5,0,5))

viewer.ren.AddActor(t_ctxt)
t_ctxt.set_renderer(viewer.ren)

def refresh_t_chart():
    t_score = get_t_score(spatial_slice, current_x_coord, current_y_coord)
    t_color = fmri_color_int.GetColor(t_score)
    t_ctxt.set_value(t_score, t_color)

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
def calculate_bold_signal(z,x,y):
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
    if current_mode=='time':
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
ax.SetTitle('Time (s.)')

ay=chart.GetAxis(0)
ay.SetTitle('Bold Signal')
viewer.ren.SetBackground(0.8,0.8,0.8)
viewer.renWin.SetMultiSamples(4)

#=======================================LINE IN TIME PLOT===============================
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


#=======================GLOBAL EVENT HANDLERS======================

def click_event_handler(caller=None,event=None):
    global current_volume
    position=caller.GetEventPosition()
    p1=chart.GetPoint1()
    p2=chart.GetPoint2()

    t_x,t_y,t_w,t_h=t_ctxt.get_position()
    if p1[0] < position[0] < p2[0] and p1[1] < position[1] < p2[1]:
        #print 'Click detected'
        if current_mode=='space':
            change_to_time_mode()
        ax=chart.GetAxis(1)
        t=(position[0]-ax.GetPoint1()[0])/(ax.GetPoint2()[0]-ax.GetPoint1()[0])
        coord=ax.GetMinimum()+(ax.GetMaximum()-ax.GetMinimum())*t
        slice_idx=int(round(coord/TR))
        add_line_to_graph(slice_idx*TR)
        current_volume=slice_idx
        slice_mapper.SetSliceNumber(slice_idx)
        slice_actor.SetPosition(-1*TR*slice_idx-2*spatial_slice,0,0)#To keep it still
        command=caller.GetCommand(click_obs_id)
        command.SetAbortFlag(1)
    elif t_x < position[0] < (t_x+t_w) and t_y < position[1] < (t_y+t_h):
        if current_mode=='time':
            change_to_space_mode()

    viewer.renWin.Render()

def change_to_space_mode():
    global current_mode,line_plot_id
    #print "changing to space mode"
    current_mode='space'
    #remove line from time plot
    if line_plot_id:
        chart.RemovePlot(line_plot_id)
        line_plot_id=None
    #hide bold image
    slice_actor.SetVisibility(0)
    plane_widget.EnabledOn()

def change_to_time_mode():
    global current_mode
    #print "changing to time mode"
    current_mode='time'
    #add line again
    add_line_to_graph()
    #make bold image visible again
    slice_actor.SetVisibility(1)
    plane_widget.EnabledOff()

click_to_pick_obs_id1=None

orig_cam_position=None
def click_to_pick(caller=None,event=None):
    global picking_time_slice,orig_cam_position
    ex,ey=viewer.iren.GetEventPosition()
    #print event
    if event=='StartInteractionEvent':
        picked=p.Pick(ex,ey,0,viewer.ren)
        if picked:
            picking_time_slice=True
            viewer.iren.GetInteractorStyle().Off()
            cam1=viewer.ren.GetActiveCamera()
            orig_cam_position=cam1.GetPosition()
            return
    if picking_time_slice:
        picked=p.Pick(ex,ey,0,viewer.ren)
        cam1=viewer.ren.GetActiveCamera()
        cam1.SetPosition(orig_cam_position)
    if event=='EndInteractionEvent':
        picking_time_slice=False
        #print "done"
        #viewer.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        #print "============================="

picking_time_slice=False

click_obs_id=viewer.iren.AddObserver('LeftButtonPressEvent',click_event_handler,10)
viewer.iren.AddObserver('StartInteractionEvent',click_to_pick,9)
viewer.iren.AddObserver('ModifiedEvent',click_to_pick,100)
viewer.iren.AddObserver('EndInteractionEvent',click_to_pick,9)
viewer.iren.AddObserver('LeftButtonReleaseEvent',click_to_pick,9)


def resize_event_handler(obj=None,event=None):
    new_width=viewer.renWin.GetSize()[0]
    new_height=viewer.renWin.GetSize()[1]
    chart.SetSize(vtk.vtkRectf(0,0,new_width,new_height//3))
    t_ctxt.set_position(new_width-110,new_height-110,100,100)

scene.AddObserver('ModifiedEvent',resize_event_handler)

viewer.iren.Initialize()
viewer.renWin.Render()
cam1=viewer.ren.GetActiveCamera()
cam1.Azimuth(120)

set_cursor(spatial_slice,current_x_coord,current_y_coord)
calculate_bold_signal(spatial_slice,current_x_coord,current_y_coord)
refresh_t_chart()
viewer.renWin.SetMultiSamples(10)
viewer.start()