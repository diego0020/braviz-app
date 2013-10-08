
from __future__ import division
import Tkinter as tk
import ttk
import numpy as np
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor


import braviz
import braviz.visualization.fmri_view
import braviz.visualization.vtk_charts

from math import ceil,floor
__author__ = 'Diego'

#====================global variables===========
subject='093'
TR=3
current_volume=34
current_x_coord=25
current_y_coord=10
spatial_slice=62

current_mode='space' #time or space
#===============================================


reader=braviz.readAndFilter.kmc40AutoReader(max_cache=10)
t_stat_img=reader.get('fMRI',subject,format='VTK',space='func',name='powergrip')
origin=t_stat_img.GetOrigin()
spacing=t_stat_img.GetSpacing()
dimensions=t_stat_img.GetDimensions()

bold_img=reader.get('BOLD',subject,name='powergrip')
bold_data=bold_img.get_data()

mri_img=reader.get('MRI',subject,format='VTK',space='fmri_powergrip')


picker = vtk.vtkCellPicker()
picker.SetTolerance(0.001)

#Visualization
ren=vtk.vtkRenderer()
renWin=vtk.vtkRenderWindow()
renWin.AddRenderer(ren)


planeWidget=braviz.visualization.persistentImagePlane()

planeWidget.SetPicker(picker)
planeWidget.UpdatePlacement()


blend=braviz.visualization.fmri_view.blend_fmri_and_mri(t_stat_img,mri_img,threshold=1.0,alfa=True)
fmri_lut=braviz.visualization.fmri_view.get_fmri_lut(1)

planeWidget.SetInputData(blend.GetOutput())
#plane_widget.SetInputConnection(color_mapper2.GetOutputPort())


planeWidget.GetColorMap().SetLookupTable(None)
planeWidget.DisplayTextOff()






slice_actor=braviz.visualization.fmri_view.time_slice_viewer()
ren.AddActor(slice_actor)
slice_actor.set_time_point(current_volume)
slice_actor.set_window_level(2000,1000)
#start in spatial mode
slice_actor.SetVisibility(0)
slice_actor.set_z_spacing(spacing[0])

cursors=braviz.visualization.cursors()
cursors.set_spacing(*spacing)
cursors.set_dimensions(*dimensions)
cursors.set_origin(*origin)
set_cursor= cursors.set_cursor
ren.AddActor(cursors)


outline = braviz.visualization.outline_actor()
outline.set_input_data(t_stat_img)

config=braviz.interaction.get_config(__file__)
background= config.get_background()
ren.SetBackground(background)
renWin.SetSize(600, 600)
ren.AddActor(outline)

#========================T-SCORE=============================

def get_t_score(z,x,y):
    return t_stat_img.GetScalarComponentAsDouble(int(z),int(x),int(y),0)

bar_plot = braviz.visualization.vtk_charts.BarPlot()

win_width = renWin.GetSize()[0]
win_height =renWin.GetSize()[1]
bar_plot.set_position(win_width - 110, win_height - 110, 100, 100)

bar_plot.set_x_axis(title="%(value)f",visible=False)
bar_plot.set_y_axis(title="SPM-T Score",limits=(-7,7),ticks=(-5,0,5))

ren.AddActor(bar_plot)
bar_plot.set_renderer(ren)

def refresh_t_chart():
    t_score = get_t_score(spatial_slice, current_x_coord, current_y_coord)
    t_color = fmri_lut.GetColor(t_score)
    bar_plot.set_value(t_score, t_color)

#====================Line Chart================================

line_plot = braviz.visualization.vtk_charts.LinePlot()
ren.AddActor(line_plot)
line_plot.set_renderer(ren)


#=====================BOLD SIGNAL=========================
min_bar_y=-1
max_bar_y=1
def calculate_bold_signal(z,x,y):
    global min_bar_y,max_bar_y
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


    renWin.Render()
#=========================================================


#================Experiment design========================
base_design=([-0.5]*10+[0.5]*10)*4
assert len(base_design) == 80
base_design=np.array( base_design )
def add_experiment_design(scale,center):
    design=np.dot(base_design,scale)+(center)
    return design

#=======================================LINE IN TIME PLOT===============================
def add_line_to_graph(coord=None):
    line_plot.add_vertical_line(coord)

#===============================Observers====================
nslices=0
def get_time_vol(spatial_slice):
    global vol0,vtk0,nslices
    vol0=bold_data[spatial_slice,:,:,:]
    vol0=np.rollaxis(vol0,2)
    nslices=vol0.shape[0]
    vtk0=braviz.readAndFilter.numpy2vtk_img(vol0)
    time_spacing=(TR,spacing[1],spacing[2])
    vtk0.SetSpacing(time_spacing)
    vtk0.SetOrigin(origin)
    slice_actor.set_input(vtk0,spatial_slice)




def setSubj(Event=None):
    global origin,spacing,bold_data,mri_img,spatial_slice,subject,dimensions,t_stat_img
    subject=select_subj_frame.get()
    t_stat_img = reader.get('fMRI', subject, format='VTK', space='func', name=paradigm_var.get())
    origin = t_stat_img.GetOrigin()
    spacing = t_stat_img.GetSpacing()
    dimensions= t_stat_img.GetDimensions()

    bold_img = reader.get('BOLD', subject, name=paradigm_var.get())
    bold_data = bold_img.get_data()

    mri_img = reader.get('MRI', subject, format='VTK', space='fmri_%s'%paradigm_var.get())
    blend.change_imgs(mri_img,t_stat_img)
    spatial_slice=planeWidget.GetSliceIndex()
    #planeWidget.SetInputConnection(blend.GetOutputPort())

    get_time_vol(spatial_slice)
    calculate_bold_signal(spatial_slice, current_x_coord, current_y_coord)
    set_cursor(spatial_slice, current_x_coord, current_y_coord)
    refresh_t_chart()
    if current_mode=='time':
        add_line_to_graph(current_volume*TR)
    renWin.Render()


def setThreshold(Event=None):
    blend.change_threshold(threshold_slider.get())
    renWin.Render()

def resize_event_handler(obj=None, event=None):
    new_width = renWin.GetSize()[0]
    new_height = renWin.GetSize()[1]
    line_plot.set_position(0, 0, new_width, new_height // 3)
    bar_plot.set_position(new_width - 110, new_height - 110, 100, 100)

line_plot.scene.AddObserver('ModifiedEvent', resize_event_handler)

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

planeWidget.SetSliceIndex(spatial_slice)
custom_id=planeWidget.AddObserver(planeWidget.cursor_change_event,lambda x,y: image_interaction(x,y,'cursor_change'))
custom_id2=planeWidget.AddObserver(planeWidget.slice_change_event,lambda x,y: image_interaction(x,y,'slice_change'))

click_to_pick_obs_id1=None

orig_cam_position=None
def click_to_pick(caller=None,event=None):
    global picking_time_slice,orig_cam_position
    ex,ey=iact.GetEventPosition()
    #print event
    if event=='LeftButtonPressEvent':
        picked=picker.Pick(ex,ey,0,ren)
        if picking_time_slice:
            command = caller.GetCommand(mouse_press_event_id)
            command.SetAbortFlag(1)
            return
    if picking_time_slice:
        picked=picker.Pick(ex,ey,0,ren)
        if event=='MouseMoveEvent':
            command=caller.GetCommand(mouse_move_event_id)
            command.SetAbortFlag(1)
    if event=='EndInteractionEvent' or event=='LeftButtonReleaseEvent':
        picking_time_slice=False


picking_time_slice=False


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

    renWin.Render()


#=====================Time IMAGE PICKING=======================


def picking_observer(caller=None,event=None):
    #print "pica pica"
    global current_x_coord,current_y_coord,picking_time_slice
    picking_time_slice = True
    x,y= picker.GetPointIJK()[1:]
    set_cursor(spatial_slice,x,y)
    current_x_coord=x
    current_y_coord=y
    calculate_bold_signal(spatial_slice,x,y)
    refresh_t_chart()
    #t_score = get_t_score(spatial_slice, x, y)
    #print "t-score=%f"%t_score
slice_actor.AddObserver(vtk.vtkCommand.PickEvent,picking_observer)

def change_to_space_mode():
    global current_mode,line_plot_id
    #print "changing to space mode"
    current_mode='space'
    #remove line from time plot
    line_plot.add_vertical_line(None)
    #hide bold image
    slice_actor.SetVisibility(0)
    planeWidget.EnabledOn()
    mode_button['text'] = 'Switch to time mode'

def change_to_time_mode():
    global current_mode
    #print "changing to time mode"
    current_mode='time'
    #add line again
    add_line_to_graph(current_volume*TR)
    #make bold image visible again
    slice_actor.SetVisibility(1)
    planeWidget.EnabledOff()
    mode_button['text'] = 'Switch to space mode'

def switch_mode(Evento=None):
    global current_mode
    if current_mode=='space':
        change_to_time_mode()
    else:
        change_to_space_mode()



#===============================================Inteface=================================

root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
top.title('BraViz-Mri')

control_frame = tk.Frame(top,width=100)

select_subj_frame=braviz.interaction.subjects_list(reader,setSubj,control_frame,text='Subject',padx=10,pady=5,height='100')
select_subj_frame.grid(row=0)

#--------------------

mode_button=tk.Button(control_frame,text="Switch to time mode",command=switch_mode)
mode_button.grid(row=2,sticky='EW',padx=10,pady=20)

#--------------------
paradigm_panel=tk.Frame(control_frame)
paradigm_var=tk.StringVar()
select_paradigm=ttk.Combobox(paradigm_panel,textvariable=paradigm_var,width=10)
select_paradigm.grid(row=0,column=1)
select_paradigm['values']=('Precision','Powergrip')
select_paradigm['state']='readonly'
select_paradigm.set('Powergrip')
select_paradigm.bind('<<ComboboxSelected>>',setSubj)

paradigm_label=tk.Label(paradigm_panel,text="Paradigm: ")
paradigm_label.grid(row=0,column=0)

paradigm_panel.grid(row=3,pady=10)


#--------------------


threshold_frame=tk.Frame(control_frame)
threshold_label=tk.Label(threshold_frame,text="Threshold:")
threshold_slider=tk.Scale(threshold_frame, orient=tk.HORIZONTAL, from_=0.0, to=7.0, resolution=0.5,command=setThreshold)
threshold_slider.set(3.0)

threshold_label.grid(row=0,sticky='EW',padx=10,column=0)
threshold_slider.grid(row=1,sticky='EW',padx=10,column=0)
threshold_frame.columnconfigure(0,weight=1)
threshold_frame.grid(row=4,pady=20,sticky='WE',column=0)


#=====================================================================
display_frame = tk.Frame(top)
control_frame.pack(side="left", anchor="n", fill="y", expand="false")
display_frame.pack(side="left", anchor="n", fill="both", expand="true")
renderer_frame = tk.Frame(display_frame)
renderer_frame.pack(padx=3, pady=3,side="left",
                    fill="both", expand="true")

render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                            rw=renWin,width=600,
                                            height=600)
def clean_exit():
    global renWin
    print "adios"
    renWin.Finalize()
    del renWin
    render_widget.destroy()
    root.quit()
    root.destroy()
top.protocol("WM_DELETE_WINDOW", clean_exit)

render_widget.pack(fill='both', expand='true')
iact = render_widget.GetRenderWindow().GetInteractor()
custom_iact_style=config.get_interaction_style()
iact_style=getattr(vtk,custom_iact_style)()
iact.SetInteractorStyle(iact_style)
planeWidget.SetInteractor(iact)
planeWidget.On()

#-----------------Initialization----------------
get_time_vol(spatial_slice)
set_cursor(spatial_slice,current_x_coord,current_y_coord)
refresh_t_chart()
line_plot.set_x_axis("Time (s.)",(0,TR*nslices))
calculate_bold_signal(spatial_slice,current_x_coord,current_y_coord)
picker.PickFromListOff()



click_obs_id=iact.AddObserver('LeftButtonPressEvent',click_event_handler,10)
mouse_press_event_id=iact.AddObserver('LeftButtonPressEvent',click_to_pick,9)
mouse_move_event_id=iact.AddObserver('MouseMoveEvent',click_to_pick,100)
iact.AddObserver('EndInteractionEvent',click_to_pick,9)
iact.AddObserver('LeftButtonReleaseEvent',click_to_pick,9)




cam1 = ren.GetActiveCamera()
cam1.Elevation(80)
cam1.SetViewUp(0, 0, 1)
cam1.Azimuth(80)
ren.ResetCameraClippingRange()
render_widget.Render()

iact.Initialize()
renWin.Render()
iact.Start()

# Start Tkinter event loop
root.mainloop()