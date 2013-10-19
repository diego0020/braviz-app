from __future__ import division
import Tkinter as tk
import ttk
import numpy as np
from braviz.readAndFilter.read_csv import get_column
from braviz.visualization.vtk_charts import multi_bar_plot
import os
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import math
import braviz

__author__ = 'Diego'
reader=braviz.readAndFilter.kmc40AutoReader(max_cache=100)


#=======global variables=======
current_subject='207'
tms_column='ICId'
invert_data=True #perform 100 - tms_data
term_mean=0
term_std_dev=0
codes2=[]
tms_data2=[]
context_lines = [term_mean + term_std_dev, term_mean, term_mean - term_std_dev]
context_dashes = [True, False, True]
data_code='ICI'
#====================

fibers=reader.get('fibers',current_subject,space='talairach')

config=braviz.interaction.get_config(__file__)
background= config.get_background()

ren=vtk.vtkRenderer()
renWin=vtk.vtkRenderWindow()
renWin.AddRenderer(ren)
ren.SetBackground(background)

fibers_mapper=vtk.vtkPolyDataMapper()
fibers_mapper.SetInputData(fibers)
fibers_actor=vtk.vtkActor()
fibers_actor.SetMapper(fibers_mapper)

ren.AddActor(fibers_actor)
#________TMS_DATA_________________

csv_file = os.path.join(reader.getDataRoot(), 'baseFinal_TMS.csv')
#--------------------------------------------------------
#create_chart_1
bars_view_1=multi_bar_plot()

#create chart2
bars_view_2=multi_bar_plot()


#===============read data=====================
def setData(Event=None):
    global codes2,tms_data2,term_mean,term_std_dev,tms_column,context_lines,data_code,disp2axis
    data_code=data_codes_dict[data_type_var.get()]
    invert_data=invet_data_dict[data_code]
    tms_column=data_code+side_var.get()
    codes=get_column(csv_file,'CODE')
    genres=get_column(csv_file,'GENDE')
    grupo=get_column(csv_file,'UBICA') #1=canguro, 2=control, 3=gorditos
    TMS_metric=get_column(csv_file,tms_column,True)
    if invert_data is True:
        TMS_metric=map(lambda x:100-x,TMS_metric)

    valid_genres=[]
    if male_selected_var.get(): valid_genres.append('2')
    if female_selected_var.get(): valid_genres.append('1')
    table=zip(codes,genres,grupo,TMS_metric)
    table_genre=filter(lambda y: y[1] in valid_genres ,table)
    term=filter(lambda x:x[2]=='3',table_genre)
    if len(term)>0:
        term_data=zip(*term)[3]
        term_data = filter(lambda x: not math.isnan(x), term_data)
        term_mean=np.mean(term_data)
        term_std_dev=np.std(term_data)
        codes2, _, _, tms_data2 = zip(*table_genre)
        bars_view_1.set_all(len(codes2), 5, 500)
    else:
        codes2=[]
        tms_data2=[]
        term_mean=0
        term_std_dev=0

    #only keep codes and tms_data columns from filtered table

    context_lines = [term_mean + term_std_dev, term_mean, term_mean - term_std_dev]

    bars_view_1.set_color_fun(get_color)
    bars_view_1.set_y_limis(*limits_dict[data_code])


    bars_view_1.set_lines(context_lines, context_dashes)
    bars_view_1.set_data(tms_data2, codes2)
    bars_view_1.set_y_title(labels_dict[data_code])

    bars_view_2.set_y_title(labels_dict[data_code])
    bars_view_2.set_y_limis(*limits_dict[data_code])
    bars_view_2.set_all(1, 5, 100)
    bars_view_2.set_color_fun(get_color)
    bars_view_2.set_lines(context_lines, context_dashes)
    bars_view_1.paint_bar_chart()
    try:
        previous_selection=select_subj_frame.get()
    except tk.TclError:
        previous_selection=None
    select_subj_frame.tk_listvariable.set(codes2)
    if previous_selection in codes2:
        idx=codes2.index(previous_selection)
        select_subj_frame.subjects_list.selection_clear(0,tk.END)
        select_subj_frame.subjects_list.select_set(idx,idx)

    setSubj()
    disp2axis=get_mapper_function()

previous_value=0
def setSubj(Event=None):
    global fibers,current_subject,previous_value
    #print "setting subjects"
    if len(codes2)==0:
        bars_view_2.set_data([], [])
        bars_view_2.set_y_limis(*limits_dict[data_code])
        bars_view_2.paint_bar_chart()
        fibers_actor.SetVisibility(0)
        renWin.Render()
        return
    try:
        current_subject=select_subj_frame.get()
    except tk.TclError:
        select_subj_frame.subjects_list.select_set(0,0)
        current_subject = select_subj_frame.get()
    try:
        fibers = reader.get('fibers', current_subject, space='talairach')
    except:
        fibers_actor.SetVisibility(0)
    else:
        fibers_mapper.SetInputData(fibers)
        fibers_actor.SetVisibility(1)


    idx=codes2.index(current_subject)
    renWin.Render()
    bars_view_1.set_enphasis(idx)
    bars_view_1.paint_bar_chart()
    new_value=tms_data2[idx]
    time_steps=7
    if time_steps>0:
        slope=(new_value-previous_value)/time_steps
    else:
        previous_value=new_value
        slope=0
    animated_draw_bar(time_steps,slope,previous_value,codes2[idx])
    previous_value=new_value

def animated_draw_bar(time,slope,value,code):
    bars_view_2.set_data([value],[code] )
    #bars_view_2.set_y_limis(-100,100)
    bars_view_2.paint_bar_chart()
    if(time>0):
        root.after(50,animated_draw_bar,time-1,slope,value+slope,code)


def get_color(value):
    z_score=abs(value-term_mean)/term_std_dev

    if  z_score <= 0.5:
        return (26, 150, 65,255)
    elif z_score <=1:
        return (166, 217, 106,255)
    elif z_score <= 1.5:
        return (255, 225, 191,255)
    elif z_score <=2:
        return (253, 174, 97,255)
    else:
        return (215, 25, 28,255)






#===============================================Inteface=================================

root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
top.title('BraViz-TMS_View')

control_frame = tk.Frame(top,width=100)




select_data_frame=tk.Frame(control_frame)
#select data
#data_codes_dict={
#    'IntraCortical Inhibition' :'ICI',
#    'IntraCortical Facilitation':'ICF',
#    'IHI Latency' :'IHIlat',
#    'IHI Duration':'IHIdur',
#    'MotorThreshold' :'RMT',
#    'MEP Latency' : 'MEPlat',
#    'IHI Frequency' :'IHIfreq'
#}

data_codes_dict={
    'IntraCortical Inhibition' :'ICI',
    'IntraCortical Facilitation':'ICF',
    'IHI Latency' :'IHIlat',
    'IHI Duration':'IHIdur',
    'MotorThreshold' :'RMT',
    'Corticospinal efficiency ' : 'MEPlat',
    'IHI Frequency' :'IHIfreq'
}

invet_data_dict={
    'IHIfreq' : False,
    'RMT' : True,
    'IHIdur': False,
    'MEPlat': False,
    'ICF': False,
    'ICI': True,
    'IHIlat' : False
}
limits_dict={
    'IHIfreq': (-20,120),
    'RMT': (-10,120),
    'IHIdur': (-2,35),
    'MEPlat': (-2,20),
    'ICF':(-10,400),
    'ICI':(-10,120),
    'IHIlat':(-2,35 )
}

labels_dict={
    'IHIfreq' : 'Frequency (%)',
    'RMT' : 'Power (%)',
    'IHIdur': 'Duration (ms.)',
    'MEPlat': 'Latency (ms.)',
    'ICF': 'Facilitation (%)',
    'ICI': 'Inverted Inhibition (%)',
    'IHIlat' : 'Latency (ms.)'
}



data_type_var=tk.StringVar()
data_selection=ttk.Combobox(select_data_frame,textvariable=data_type_var)
#data_selection['values']=('IntraCortical Inhibition','IntraCortical Facilitation','InterHemispheric Inhibition Latency','InterHemispheric Inhibition Duration','MotorThreshold','Motor Evoked Potential Latency,InterHemispheric Inhibition Frequency')
data_selection['values']=sorted(data_codes_dict.keys())
data_selection['state']='readonly'
data_selection.set('IntraCortical Inhibition')
data_selection.pack(side='top')
data_selection.bind('<<ComboboxSelected>>',setData)
data_selection.grid(row=0,column=0,columnspan=2,sticky='ew')
#select side
side_var=tk.StringVar()
side_var.set('d')
dominant_radio=tk.Radiobutton(select_data_frame,text='Dominant',variable=side_var,value='d',command=setData)
non_dominant_radio=tk.Radiobutton(select_data_frame,text='Nondominant',variable=side_var,value='nd',command=setData)
dominant_radio.grid(row=1,column=0)
non_dominant_radio.grid(row=1,column=1)
#select gender
male_selected_var=tk.BooleanVar()
female_selected_var=tk.BooleanVar()
male_checkbox=tk.Checkbutton(select_data_frame,text='male',command=setData,variable=male_selected_var)
female_checkbox=tk.Checkbutton(select_data_frame,text='female',command=setData,variable=female_selected_var)
female_checkbox.select()
male_checkbox.grid(row=2,column=0)
female_checkbox.grid(row=2,column=1)

select_data_frame.grid(row=0,pady=20)

select_subj_frame=braviz.interaction.subjects_list(reader,setSubj,control_frame,text='Subject',padx=10,pady=5,height='100')
select_subj_frame.grid(column=0,row=1,sticky='news')
control_frame.rowconfigure(1,weight=1)

def print_camera(Event=None):
    cam1 = ren.GetActiveCamera()
    #cam1.Elevation(80)
    #cam1.SetViewUp(0, 0, 1)
    #cam1.Azimuth(80)
    print cam1
#print_camera_button=tk.Button(control_frame,text='print_cammera',command=print_camera)
#print_camera_button.grid()

#=====================================================================
display_frame = tk.Frame(top)
renderer_frame = tk.Frame(display_frame)
renderer_frame.grid(padx=3, pady=3,row=0,column=0,sticky='nsew')
render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                            rw=renWin, width=600,
                                            height=300)
render_widget.pack(fill='both', expand='true')
display_frame.rowconfigure(0,weight=1)
display_frame.columnconfigure(0,weight=1)

graphs_frame=tk.Frame(display_frame)
bars_widget1= vtkTkRenderWindowInteractor(graphs_frame,
                                           width=500,
                                          height=200)
bars_view_1.SetRenderWindow(bars_widget1.GetRenderWindow())
bars_view_1.SetInteractor(bars_widget1.GetRenderWindow().GetInteractor())

bars_widget1.grid(column=0,row=0,sticky='nsew')

bars_widget2 = vtkTkRenderWindowInteractor(graphs_frame,
                                           width=100,
                                           height=200)
bars_view_2.SetRenderWindow(bars_widget2.GetRenderWindow())
bars_view_2.SetInteractor(bars_widget2.GetRenderWindow().GetInteractor())
bars_widget2.grid(column=1,row=0,sticky='nsew')

graphs_frame.grid(padx=3, pady=3,row=1,column=0,sticky='nsew')
graphs_frame.columnconfigure(0,weight=3)
graphs_frame.columnconfigure(1,weight=1)
graphs_frame.rowconfigure(0,weight=1)

display_frame.rowconfigure(0,weight=3)
display_frame.rowconfigure(1,weight=2)
control_frame.pack(side="left", anchor="n", fill="y", expand="false")
display_frame.pack(side="left", anchor="n", fill="both", expand="true")
def clean_exit():
    global renWin
    print "adios"
    renWin.FastDelete()
    del renWin
    quit(0)

top.protocol("WM_DELETE_WINDOW", clean_exit)


#display_frame.pack(side="top", anchor="n", fill="both", expand="true")
iact = render_widget.GetRenderWindow().GetInteractor()
custom_iact_style=config.get_interaction_style()
iact_style=getattr(vtk,custom_iact_style)()
iact.SetInteractorStyle(iact_style)


cam1 = ren.GetActiveCamera()
cam1.SetPosition(-1.0733, 2.56344, 122.951)
cam1.SetViewUp(1, 0, 0)
cam1.SetFocalPoint(-1.44063, -11.8824, 6.28172)
ren.ResetCameraClippingRange()
render_widget.Render()


def get_mapper_function():
    a1 = bars_view_1.chart.GetAxis(1)
    x0 = a1.GetPoint1()[0]
    xf = a1.GetPoint2()[0]
    #xf_x0=xf-x0
    #print "%f ----- %f"%(x0,xf)
    ax0=a1.GetMinimum()
    axf=a1.GetMaximum()

    def disp2axis(x):
        t=(x-x0)/(xf-x0)
        x=(t*(axf-ax0)+ax0)
        return x
    return disp2axis
disp2axis=lambda x:x


def get_subj_index(x):
    if bars_view_1.start < x < bars_view_1.get_bar_graph_width() + bars_view_1.start:
        index = int((x - bars_view_1.start) // (bars_view_1.width + 1))
        return index
    return None


iact.Initialize()
renWin.Render()
iact.Start()
setData()
setSubj()
bars_view_1.Render()
disp2axis=get_mapper_function()
def print_event(caller=None,event=None):
    print event

def resize_handler(caller=None,event=None):
    top.after(1000,do_resize)
def do_resize():
    global disp2axis
    bars_view_2.ren.Render()
    disp2axis = get_mapper_function()

def draw_tooltip(caller=None,event=None):


    tool_tip=bars_view_1.chart.GetTooltip()
    event_position = caller.GetEventPosition()
    event_coordinates=disp2axis(event_position[0])
    if get_subj_index(event_coordinates) is not None:
        tool_tip.SetVisible(1)
        tool_tip.SetPosition(event_position)
        index=int((event_coordinates-bars_view_1.start)//(bars_view_1.width+1))
        code=codes2[index]
        datum=tms_data2[index]
        message="%s : %.2f"%(code,datum)
        tool_tip.SetText(message)
    else:
        tool_tip.SetVisible(0)
    bars_view_1.Render()
def draw_tooltip2(caller=None, event=None):
    tool_tip2=bars_view_2.chart.GetTooltip()
    event_position = caller.GetEventPosition()
    event_x=event_position[0]
    x0=bars_view_2.chart.GetAxis(1).GetPoint1()[0]
    xf=bars_view_2.chart.GetAxis(1).GetPoint2()[0]
    if x0 < event_x < xf:
        tool_tip2.SetVisible(1)
        tool_tip2.SetPosition(event_position)
        idx=codes2.index(current_subject)
        datum = tms_data2[idx]
        message = "%s : %.2f" % (current_subject, datum)
        tool_tip2.SetText(message)
    else:
        tool_tip2.SetVisible(0)
    bars_view_2.Render()

def click_in_bar(caller=None,event=None):
    event_position = caller.GetEventPosition()
    event_coordinates=disp2axis(event_position[0])
    index=get_subj_index(event_coordinates)
    if index is not None:
        select_subj_frame.subjects_list.selection_clear(0, tk.END)
        select_subj_frame.subjects_list.select_set(index,index)
        setSubj()


#interaction_event_id=bars_view_1.chart.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
#interaction_event_id=bars_view_1.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
#interaction_event_id=bars_view_1.GetScene().AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
#bar1=bars_view_1.chart.GetPlot(0)
#interaction_event_id=bar1.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)

iact2=bars_view_1.GetInteractor()
iact3=bars_view_2.GetInteractor()
#print iact2
#interaction_event_id=iact2.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
interaction_event_id=iact2.AddObserver(vtk.vtkCommand.MouseMoveEvent,draw_tooltip,100)
interaction_event_id=iact3.AddObserver(vtk.vtkCommand.MouseMoveEvent,draw_tooltip2,100)
iact2.AddObserver(vtk.vtkCommand.LeftButtonPressEvent,click_in_bar,100)

#bars_view_1.ren.AddObserver('ModifiedEvent',resize_handler)
top.bind('<Configure>',resize_handler)
root.bind('<Configure>',resize_handler)
#MouseMoveEvent_event_id=iact2.AddObserver(vtk.vtkCommand.MouseMoveEvent,abort_interaction_event,100)
# Start Tkinter event loop
root.mainloop()