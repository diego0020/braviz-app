from __future__ import division
import os
from math import floor,ceil

from numpy.linalg import inv
import vtk
import numpy as np
import nibabel as nib

import braviz
from braviz import _test_arrow
from braviz.readAndFilter.images import write_vtk_image, nibNii2vtk
from braviz.readAndFilter.transforms import applyTransform
import braviz.visualization.vtk_charts
import braviz.visualization.fmri_view
from braviz.readAndFilter.readDartelTransform import dartel2GridTransform_cached as dartel2GridTransform


__author__ = 'Diego'

reader=braviz.readAndFilter.BravizAutoReader()
viewer= simpleVtkViewer()

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

root_dir=reader.get_data_root()
test_dir=os.path.join(root_dir,'%s\spm\POWERGRIP'%subject)
os.chdir(test_dir)
img_4d=nib.load('smoothed.nii.gz')
data_d4=img_4d.get_data()

slice_actor=braviz.visualization.fmri_view.time_slice_viewer()


viewer.ren.AddActor(slice_actor)
slice_actor.set_time_point(current_volume)
slice_actor.set_window_level(2000,1000)

#start in spatial mode
slice_actor.SetVisibility(0)




def get_time_vol(spatial_slice):
    global vol0,vtk0,nslices
    vol0=data_d4[spatial_slice,:,:,:]
    vol0=np.rollaxis(vol0,2)
    nslices=vol0.shape[0]
    vtk0= numpy2vtk_img(vol0)
    vtk0.SetSpacing(TR,2,2)
    slice_actor.set_input(vtk0,spatial_slice)

get_time_vol(spatial_slice)
#============CURSORS=====================

cursors= cursors()
cursors.set_spacing(-2,2,2)
set_cursor= cursors.set_cursor

viewer.ren.AddActor(cursors)
#===============T-IMAGE=================
plane_widget= persistentImagePlane()


t_stat_img=reader.get('fMRI',subject,name='powergrip',space='native',format='vtk')
t_stat_img.SetSpacing([-2,2,2])
#move T1_img to fmri space
origin2=(78,-112,-50)
dimension2=(79,95,68)
spacing2=(-2,2,2)

t1_img=nib.load('T1.nii.gz')
t1_img_vtk=nibNii2vtk(t1_img)
t1_img_vtk=applyTransform(t1_img_vtk, inv(t1_img.get_affine()))
dartel_trans=dartel2GridTransform('y_seg_back.nii.gz',True)
mri_img=applyTransform(t1_img_vtk, dartel_trans, origin2, dimension2, spacing2)
mri_img.SetOrigin((0,0,0))
mri_img.SetSpacing((-2,2,2))

#blend

blend=braviz.visualization.fmri_view.blend_fmri_and_mri(t_stat_img,mri_img,threshold=1.0,alfa=True)
fmri_lut=braviz.visualization.fmri_view.get_fmri_lut(1)

plane_widget.SetInputConnection(blend.GetOutputPort())
#plane_widget.SetInputConnection(color_mapper2.GetOutputPort())
plane_widget.SetInteractor(viewer.iren)
plane_widget.On()
plane_widget.GetColorMap().SetLookupTable(None)
plane_widget.DisplayTextOff()

# An outline is shown for context.
outline = OutlineActor()
outline.set_input_data(t_stat_img)

viewer.ren.AddActor(outline)

#=========================EXTRA INTERACTION IN SPACE MODE======================================================

def image_interaction(caller,event,event_name='std'):
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
custom_id=plane_widget.AddObserver(plane_widget.cursor_change_event,lambda x,y: image_interaction(x,y,'cursor_change'))
custom_id2=plane_widget.AddObserver(plane_widget.slice_change_event,lambda x,y: image_interaction(x,y,'slice_change'))

#=====================Time IMAGE PICKING=======================
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
    refresh_t_chart()
    #t_score = get_t_score(spatial_slice, x, y)
    #print "t-score=%f"%t_score
slice_actor.AddObserver(vtk.vtkCommand.PickEvent,picking_observer)

#========================T-SCORE=============================

def get_t_score(z,x,y):
    return t_stat_img.GetScalarComponentAsDouble(int(z),int(x),int(y),0)

bar_plot = braviz.visualization.vtk_charts.BarPlot()

win_width = viewer.renWin.GetSize()[0]
win_height = viewer.renWin.GetSize()[1]
bar_plot.set_position(win_width - 110, win_height - 110, 100, 100)

bar_plot.set_x_axis(title="%(value)f",visible=False)
bar_plot.set_y_axis(title="SPM-T Score",limits=(-7,7),ticks=(-5,0,5))

viewer.ren.AddActor(bar_plot)
bar_plot.set_renderer(viewer.ren)

def refresh_t_chart():
    t_score = get_t_score(spatial_slice, current_x_coord, current_y_coord)
    t_color = fmri_lut.GetColor(t_score)
    bar_plot.set_value(t_score, t_color)

#====================Line Chart================================

line_plot = braviz.visualization.vtk_charts.LinePlot()
viewer.ren.AddActor(line_plot)
line_plot.set_renderer(viewer.ren)
line_plot.set_x_axis("Time (s.)",(0,TR*nslices))

#=====================BOLD SIGNAL=========================
min_bold=-1
max_bold=1
def calculate_bold_signal(z,x,y):
    global min_bold,max_bold
    #ignore first volume
    bold_signal=vol0[1:,x,y]
    time_signal=[t*TR for t in xrange(1,nslices)]
    min_y=floor(min(bold_signal))
    max_y=ceil(max(bold_signal))
    scale=max_y-min_y
    center=(max_y+min_y)/2
    min_bar_y=float(min_y-scale*0.1)
    max_bar_y=float(max_y+scale*0.1)
    line_plot.set_y_axis("Bold Signal", (min_bar_y, max_bar_y))

    experiment=add_experiment_design(scale*1.1,center)

    colors=((0, 0, 0, 255),(0,0,255,255))
    widths=(None,1.0)
    markers=(vtk.vtkPlotPoints.CIRCLE,vtk.vtkPlotPoints.NONE)

    line_plot.set_values((time_signal,bold_signal,experiment),colors,widths,markers)

    if current_mode=='time':
        add_line_to_graph(current_volume*TR)


    viewer.renWin.Render()
#=========================================================


#================Experiment design========================
base_design=([-0.5]*10+[0.5]*10)*4
assert len(base_design) == 80
base_design=np.array( base_design )
def add_experiment_design(scale,center):
    design=np.dot(base_design,scale)+ center
    return design

#=======================================LINE IN TIME PLOT===============================
def add_line_to_graph(coord=None):
    line_plot.add_vertical_line(coord)

#=======================GLOBAL EVENT HANDLERS======================

def click_event_handler(caller=None,event=None):
    global current_volume
    position=caller.GetEventPosition()

    b_x, b_y, b_w, b_h = line_plot.get_position()
    t_x,t_y,t_w,t_h=bar_plot.get_position()
    if b_x < position[0] < (b_x+b_w) and b_y < position[1] < (b_y+b_h):
        #print 'Click detected'
        if current_mode=='space':
            change_to_time_mode()
        ax=line_plot.x_axis
        t=(position[0]-ax.GetPoint1()[0])/(ax.GetPoint2()[0]-ax.GetPoint1()[0])
        coord=nslices*t
        slice_idx=int(round(coord))
        current_volume = slice_idx
        add_line_to_graph(slice_idx*TR)
        slice_actor.set_time_point(slice_idx)
        #slice_actor.SetPosition(-1*TR*slice_idx-2*spatial_slice,0,0)#To keep it still
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
    line_plot.add_vertical_line(None)
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
    if event=='LeftButtonPressEvent':
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


picking_time_slice=False

click_obs_id=viewer.iren.AddObserver('LeftButtonPressEvent',click_event_handler,10)
viewer.iren.AddObserver('LeftButtonPressEvent',click_to_pick,9)
viewer.iren.AddObserver('ModifiedEvent',click_to_pick,100)
viewer.iren.AddObserver('EndInteractionEvent',click_to_pick,9)
viewer.iren.AddObserver('LeftButtonReleaseEvent',click_to_pick,9)


def resize_event_handler(obj=None,event=None):
    new_width=viewer.renWin.GetSize()[0]
    new_height=viewer.renWin.GetSize()[1]
    line_plot.set_position(0,0,new_width,new_height//3)
    bar_plot.set_position(new_width-110,new_height-110,100,100)

line_plot.scene.AddObserver('ModifiedEvent',resize_event_handler)

viewer.iren.Initialize()
viewer.renWin.Render()
cam1=viewer.ren.GetActiveCamera()
cam1.Azimuth(120)

set_cursor(spatial_slice,current_x_coord,current_y_coord)
calculate_bold_signal(spatial_slice,current_x_coord,current_y_coord)
refresh_t_chart()

viewer.ren.SetBackground(0.8,0.8,0.8)
viewer.renWin.SetMultiSamples(4)
viewer.renWin.SetMultiSamples(10)
viewer.start()