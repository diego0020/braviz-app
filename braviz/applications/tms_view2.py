from __future__ import division
import Tkinter as tk
import ttk
import numpy as np
import math
from braviz.readAndFilter.read_csv import get_column
from braviz.visualization.mathplotlib_charts import BarPlot
import os
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
    vtkTkRenderWindowInteractor
from braviz.interaction.tk_tooltip import ToolTip

import braviz
from itertools import izip
import thread
__author__ = 'Diego'
reader = braviz.readAndFilter.kmc40AutoReader()


#=======global variables=======
current_subject = '207'
tms_column = 'ICId'
invert_data = True   # perform 100 - tms_data
term_mean = 0
term_std_dev = 0
codes2 = []
tms_data2 = []
tms_data_dict = {}
group_stats_dict={}
context_lines = [term_mean + term_std_dev, term_mean, term_mean - term_std_dev]
context_dashes = [True, False, True]
data_code = 'ICI'
selected_codes = []
showing_history = True
animation=False
laterality_dict={}
genders_dict={}
group_dict={}
#====================

fibers = reader.get('fibers', current_subject, space='talairach')

config = braviz.interaction.get_config(__file__)
background = config.get_background()

ren = vtk.vtkRenderer()
renWin = vtk.vtkRenderWindow()
renWin.AddRenderer(ren)
ren.SetBackground(background)

fibers_mapper = vtk.vtkPolyDataMapper()
fibers_mapper.SetInputData(fibers)
fibers_actor = vtk.vtkActor()
fibers_actor.SetMapper(fibers_mapper)

ren.AddActor(fibers_actor)


#context
brain_stem=reader.get('model',current_subject,space='talairach',name='Brain-Stem')
brain_stem_mapper= vtk.vtkPolyDataMapper()
brain_stem_mapper.SetInputData(brain_stem)
brain_stem_actor= vtk.vtkActor()
brain_stem_actor.SetMapper(brain_stem_mapper)
brain_stem_actor.SetVisibility(0)
brain_stem_actor.GetProperty().SetOpacity(0.5)
ren.AddActor(brain_stem_actor)

precentral=reader.get('model',current_subject,space='talairach',name='ctx-lh-precentral')
precentral_mapper= vtk.vtkPolyDataMapper()
precentral_mapper.SetInputData(precentral)
precentral_actor= vtk.vtkActor()
precentral_actor.SetMapper(precentral_mapper)
precentral_actor.SetVisibility(0)
precentral_actor.GetProperty().SetOpacity(0.5)
ren.AddActor(precentral_actor)

#number of fibers message

number_of_fibers_message=vtk.vtkTextActor()
ren.AddViewProp(number_of_fibers_message)
number_of_fibers_message.SetInput('HOLA')
text_property=number_of_fibers_message.GetTextProperty()
text_property.SetFontSize(14)
text_property.SetJustificationToLeft()
text_property.SetVerticalJustificationToCentered()
text_property.ShadowOn()
text_property.SetColor(0,0,0)
text_property.ShadowOn()
number_of_fibers_message.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
number_of_fibers_message.GetPositionCoordinate().SetValue(0.01,0.5)#number of fibers message

#orientation message

orientation_message=vtk.vtkTextActor()
ren.AddViewProp(orientation_message)
orientation_message.SetInput('HOLA')
text_property=orientation_message.GetTextProperty()
text_property.SetFontSize(14)
text_property.SetJustificationToRight()
text_property.SetVerticalJustificationToCentered()
text_property.ShadowOn()
text_property.SetColor(0,0,0)
text_property.ShadowOn()
orientation_message.GetPositionCoordinate().SetCoordinateSystemToNormalizedViewport()
orientation_message.GetPositionCoordinate().SetValue(0.99,0.5)


#________TMS_DATA_________________

csv_file = os.path.join(reader.getDataRoot(), 'baseFinal_TMS.csv')
#--------------------------------------------------------
#create_chart_1
bars_view1 = BarPlot(tight=True)

#create chart2
bars_view2 = BarPlot(tight=True)

group_colors_dict={
    '1': 'navajo white', # canguro
    '2': 'beige',  # incubadora
    '3': 'SlateGray1',  # gorditos
}


def turn_on_animation():
    global animation
    animation=True
#===============read data=====================

previous_img_type=None
generating_images=False
def init_get_img(subject,img_type,side='r'):
    global generating_images
    generating_images=True
    render_widget.after(50,end_get_img, img_type)
    #get_img(subject,img_type,side)
    thread.start_new_thread(get_img,(subject,img_type,side))


def get_img(subject,img_type,side='r'):
    global fibers,brain_stem,precentral,generating_images
    if img_type == 'cc':
        precentral_actor.SetVisibility(0)
        brain_stem_actor.SetVisibility(0)
        try:
            fibers = reader.get('fibers', subject, space='talairach',name='corpus_callosum')
        except Exception:
            print "cc not found"
            fibers_actor.SetVisibility(0)
            orientation_message.SetVisibility(0)
        else:
            fibers_mapper.SetInputData(fibers)
            fibers_actor.SetVisibility(1)
            orientation_message.SetVisibility(1)
            orientation_message.SetInput('Posterior')
    elif img_type=='motor':
        try:
            #fibers = reader.get('fibers', subject, space='talairach',waypoint=['ctx-%ch-precentral'%side,'Brain-Stem'])
            fibers = reader.get('fibers', subject, space='talairach',name='cortico_spinal_%c'%side)
            brain_stem = reader.get('model', current_subject, space='talairach',name='Brain-Stem')
            precentral = reader.get('model', current_subject, space='talairach',name='ctx-%ch-precentral'%side)
        except Exception:
            fibers_actor.SetVisibility(0)
            precentral_actor.SetVisibility(0)
            brain_stem_actor.SetVisibility(0)
            orientation_message.SetVisibility(0)
        else:
            fibers_mapper.SetInputData(fibers)
            precentral_mapper.SetInputData(precentral)
            brain_stem_mapper.SetInputData(brain_stem)
            fibers_actor.SetVisibility(1)
            precentral_actor.SetVisibility(1)
            brain_stem_actor.SetVisibility(1)
            orientation_message.SetVisibility(1)
            orientation_message.SetInput('Right')
    else:
        print "not supported yet"
        fibers_actor.SetVisibility(0)
    if fibers_actor.GetVisibility():
        number_of_fibers_message.SetVisibility(1)
        number_of_fibers_message.SetInput('%d\nFibers'%fibers.GetNumberOfLines())
    else:
        number_of_fibers_message.SetVisibility(0)
    generating_images=False

def end_get_img(img_type):
    global previous_img_type,generating_images
    if generating_images is True:
        render_widget.after(50,end_get_img,img_type)
        return
    if img_type != previous_img_type:
        #reset camera
        cam = ren.GetActiveCamera()
        if img_type=='motor':
            cam.SetPosition(-18.2446, -261.939, 170.821)
            cam.SetViewUp(0, 0.5, 1)
            cam.SetFocalPoint(1.8137, -10.6985, -0.800431)
        elif img_type=='cc':
            cam.SetPosition(0.358526, 8.24682, 122.243)
            cam.SetViewUp(1, 0, 0)
            cam.SetFocalPoint(-0.00880438, -6.19902, 5.5735)
        else:
            print "Unkown image type"
        ren.ResetCameraClippingRange()
    previous_img_type = img_type
    render_widget.Render()

def set_data(event=None):
    global codes2, tms_data2, term_mean, term_std_dev, tms_column, context_lines, data_code, animation,tms_data_dict
    invert_data_values = invet_data_dict[data_code]
    tms_column = data_code + side_var.get()
    codes = get_column(csv_file, 'CODE')
    if len(laterality_dict)==0:
        later = get_column(csv_file, 'LATER')
        laterality_dict.update(izip(codes,later))

    if len(genders_dict)==0:
        genres = get_column(csv_file, 'GENDE')
        genders_dict.update(izip(codes,genres))

    if len(group_dict)==0:
        grupo = get_column(csv_file, 'UBICA')  # 1=canguro, 2=control, 3=gorditos
        group_dict.update(izip(codes,grupo))

    TMS_metric = get_column(csv_file, tms_column, True)
    if invert_data_values is True:
        TMS_metric = map(lambda x: 100 - x, TMS_metric)

    valid_genres = set()
    if male_selected_var.get(): valid_genres.add('2')
    if female_selected_var.get(): valid_genres.add('1')
    #table = izip(codes, genres, grupo, TMS_metric)
    tms_data_dict=dict(izip(codes,TMS_metric))

    genre_codes = filter(lambda x: genders_dict[x] in valid_genres, codes)
    term_codes = filter(lambda x: group_dict[x]== '3', genre_codes)
    if len(term_codes) > 0:
        term_data = [tms_data_dict[x] for x in term_codes]
        term_data = filter(lambda x: not math.isnan(x), term_data)
        term_mean = np.mean(term_data)
        term_std_dev = np.std(term_data)
    else:
        term_mean = 0
        term_std_dev = 0
    if len(genre_codes) > 0:
        codes2=genre_codes
        tms_data2=map(lambda x:tms_data_dict.get(x,float('Nan')),codes2)
    else:
        codes2 = []
        tms_data2 = []

    #only keep codes and tms_data columns from filtered table

    context_lines = [term_mean + term_std_dev, term_mean, term_mean - term_std_dev]

    bars_view1.change_style(styles_dict[data_code])

    color_inversion_factor=1
    if more_is_better_dict[data_code]:
        color_inversion_factor=-1

    bars_view1.set_color_fun(lambda  x: get_color(x,color_inversion_factor))
    bars_view1.set_y_limits(*limits_dict[data_code])

    bars_view1.set_lines(context_lines, context_dashes)

    bars_view1.set_y_title(labels_dict[data_code])

    bars_view2.change_style(styles_dict[data_code])
    bars_view2.set_y_title(labels_dict[data_code])
    bars_view2.set_y_limits(*limits_dict[data_code],right=True)
    bars_view2.set_color_fun(lambda  x: get_color(x,color_inversion_factor))
    bars_view2.set_lines(context_lines, context_dashes)
    try:
        previous_selection = select_subj_frame.get()
    except tk.TclError:
        previous_selection = None
    select_subj_frame.tk_listvariable.set(tuple(codes2))

    if previous_selection in codes2:
        idx = codes2.index(previous_selection)
        select_subj_frame.subjects_list.selection_clear(0, tk.END)
        select_subj_frame.subjects_list.select_set(idx, idx)

    #color subjects list
    if show_groups_var.get() is True:
        for i,cod in enumerate(codes2):
            select_subj_frame.itemconfigure(i,background=group_colors_dict[group_dict[cod]])
    else:
        for i, cod in enumerate(codes2):
            select_subj_frame.itemconfigure(i, background='')
    draw_bars_1()
    animation=False
    root.after(100,turn_on_animation)
    set_subj()

def get_group_stats():
    group_values_dict={}
    for cd in codes2:
        group=group_dict[cd]
        value=tms_data_dict[cd]
        if np.isfinite(value):
            group_values_dict.setdefault(group,[]).append(value)
    results=[]
    for g in ['1','2','3']: # 1=canguro, 2=control, 3=gorditos
        values=group_values_dict[g]
        if len(values)>0:
            mean=np.mean(values)
            std=np.std(values)
        else:
            mean=0
            std=0
        results.append((mean,std))
    return zip(*results)



def draw_bars_1():
    if showing_history is True:
        selected_values = [tms_data_dict[s] for s in selected_codes]
        bars_view1.set_data(selected_values, selected_codes)
        try:
            idx = selected_codes.index(current_subject)
        except ValueError:
            bars_view1.set_higlight_index(None)
        else:
            bars_view1.set_higlight_index(idx)
    else:
        if not show_groups_var.get():
            selected_values = [tms_data_dict[s] for s in codes2]
            bars_view1.set_data(selected_values, codes2)
            try:
                idx = codes2.index(current_subject)
            except ValueError:
                bars_view1.set_higlight_index(None)
            else:
                bars_view1.set_higlight_index(idx)
        else:
            means,stds=get_group_stats()
            bars_view1.set_data(means, ['KMC','INCUB','TERM'],stds)
            group_stats_dict.update(zip(['KMC','INCUB','TERM'], zip(means,stds)))
            bars_view1.set_higlight_index(None)

    bars_view1.paint_bar_chart()


previous_value = 0
animated_draw_bar_id=None


def set_subj(event=None):
    global fibers, current_subject, previous_value,animated_draw_bar_id
    #print "setting subjects"
    if len(codes2) == 0:
        bars_view2.set_data([], [])
        bars_view2.set_y_limits(*limits_dict[data_code])
        bars_view2.paint_bar_chart()
        fibers_actor.SetVisibility(0)
        renWin.Render()
        return
    try:
        current_subject = select_subj_frame.get()
    except tk.TclError:
        select_subj_frame.subjects_list.select_set(0, 0)
        current_subject = select_subj_frame.get()
    try:
        if showing_history is True :
            idx = selected_codes.index(current_subject)
        elif show_groups_var.get():
            idx=int(group_dict[current_subject])-1
        else:
            idx = codes2.index(current_subject)
    except ValueError:
        bars_view1.set_higlight_index(None)
    else:
        bars_view1.set_higlight_index(idx)

    bars_view1.paint_bar_chart()

    hemisphere='l'
    if images_dict[data_code]=='motor':
        if side_var.get()=='d':
            if laterality_dict.get(current_subject)=='2':
                hemisphere='r'
        else:
            if laterality_dict.get(current_subject) == '1':
                hemisphere='r'

    #update bar chart 2

    new_value = tms_data_dict[current_subject]
    if animation is False:
        bars_view2.set_data([new_value], [current_subject])
        bars_view2.paint_bar_chart()
        previous_value=new_value
    else:
        time_steps = 7

        if time_steps > 0:
            slope = (new_value - previous_value) / time_steps
        else:
            previous_value = new_value
            slope = 0
        bars_view2.set_data([previous_value],[current_subject])
        if animated_draw_bar_id is not None: root.after_cancel(animated_draw_bar_id)
        animated_draw_bar(time_steps-1, slope, previous_value+slope)
        previous_value = new_value

    init_get_img(current_subject, images_dict[data_code], hemisphere)

def animated_draw_bar(time, slope, value):
    global animated_draw_bar_id
    bars_view2.change_bars([value])
    if time > 0:
        animated_draw_bar_id=root.after(50, animated_draw_bar, time - 1, slope, value + slope)


def get_color(value,factor=1):
    z_score = factor*(value - term_mean) / term_std_dev

    if z_score >= 2:
        return '#D7191C'
    elif z_score >= 1:
        return '#FDAE61'
    elif z_score >= -1:
        return '#FFFFBF'
    elif z_score >= -2:
        return'#A6D96A'
    else:
        return '#1A9641'


#===============================================Inteface=================================

root = tk.Tk()
root.title('BraViz-TMS_View')

control_frame = tk.Frame(root, width=100)

select_data_frame = tk.Frame(control_frame)
#select data

invet_data_dict = {
    'IHIfreq': False,
    'RMT': True,
    'IHIdur': False,
    'MEPlat': False,
    'ICF': False,
    'ICI': True,
    'IHIlat': False
}

limits_dict = {
    'IHIfreq': (-1, 100),
    'RMT': (0, 100),
    'IHIdur': (0, 35),
    'MEPlat': (10, 15),
    'ICF': (-10, 400),
    'ICI': (-10, 100),
    'IHIlat': (0, 35 )
}

styles_dict = {
    'IHIfreq': 'bars',
    'RMT': 'bars',
    'IHIdur': 'markers',
    'MEPlat': 'markers',
    'ICF': 'bars',
    'ICI': 'bars',
    'IHIlat': 'markers'
}

images_dict = {
    'IHIfreq': 'cc',
    'RMT': 'motor',
    'IHIdur': 'cc',
    'MEPlat': 'motor',
    'ICF': 'motor',
    'ICI': 'motor',
    'IHIlat': 'cc'
}

more_is_better_dict = {
    'IHIfreq': True,
    'RMT': True,
    'IHIdur': True,
    'MEPlat': False,
    'ICF': True,
    'ICI': True,
    'IHIlat': False
}


labels_dict = {
    'IHIfreq': 'Frequency (%)',
    'RMT': 'Level of excitability (%)',
    'IHIdur': 'Duration (ms.)',
    'MEPlat': 'Latency (ms.)',
    'ICF': 'Facilitation (%)',
    'ICI': 'Inverted Inhibition (%)',
    'IHIlat': 'Latency (ms.)'
}

#data_selection=tk.Frame(select_data_frame,height=200,width=100,relief='sunken',border=5)
data_selection_tree = ttk.Treeview(select_data_frame, show='tree', height=8, selectmode='browse')
data_selection_tree.insert('', 'end', 'motor_brain', text='Motor Brain', tags='parent')
data_selection_tree.insert('motor_brain', 'end', 'exci', text='Excitability', tags='leaf')
data_selection_tree.insert('motor_brain', 'end', 'sync', text='Synchronization', tags='leaf')
data_selection_tree.insert('motor_brain', 'end', 'balan', text='Balanced Activity', tags='parent')
data_selection_tree.insert('balan', 'end', 'inhi', text='Level of Inhibition', tags='leaf')
data_selection_tree.insert('balan', 'end', 'faci', text='Level of Facilitation', tags='leaf')
data_selection_tree.insert('motor_brain', 'end', 'coop', text='Cooperation between hemispheres', tags='parent')
data_selection_tree.insert('coop', 'end', 'freq', text='Frequency', tags='leaf')
data_selection_tree.insert('coop', 'end', 'trans', text='Transfer time', tags='leaf')
data_selection_tree.insert('coop', 'end', 'dura', text='Duration', tags='leaf')

data_codes_dict = {
    'inhi': 'ICI',
    'faci': 'ICF',
    'trans': 'IHIlat',
    'dura': 'IHIdur',
    'exci': 'RMT',
    'sync': 'MEPlat',
    'freq': 'IHIfreq'
}


def select_data(event=None):
    data_selection_tree.after_idle(select_data2)


def select_data2(event=None):
    global data_code

    selected_leaf = data_selection_tree.focus()
    data_code = data_codes_dict[selected_leaf]
    set_data()


data_selection_tree.tag_bind('leaf', '<1>', select_data)


#--------------tooltips------------

long_messages_dict = {
    'motor_brain': 'Tms tests',
    'exci': 'Basic level = 100% - motor threshold',
    'sync': 'Corticospinal efficiency, msec',
    'balan': 'Balance between inhibition and facilitation mechanisms',
    'inhi': 'GABAa synapses = 100% - cond*100/test',
    'faci': 'Glutamate synapses = cond*100/test - 100%',
    'coop': 'Integrity of corpus callosum = test of inhibition from the other hemisphere',
    'freq': 'Frequency of observation of an inhibition triggered by the other hemisphere',
    'trans': 'Time for the transfer of the inhibition triggered by the other hemisphere',
    'dura': 'Duration of the inhibition triggered by the other hemisphere',
}


def data_tree_message_func(event=None):
    coord = event.y
    element = data_selection_tree.identify_row(coord)
    if len(element) == 0:
        return ''
    return long_messages_dict[element]


data_tree_tooltip = ToolTip(data_selection_tree, msgFunc=data_tree_message_func, follow=1, delay=0.5)


#---------------------------------------
data_selection_tree.grid(row=0, column=0, columnspan=2, sticky='ew')
#select side
side_var = tk.StringVar()
side_var.set('d')
hemisphere_label = tk.Label(select_data_frame, text='Hemisphere:')
hemisphere_label.grid(row=1, column=0, columnspan=2, sticky='ew')
dominant_radio = tk.Radiobutton(select_data_frame, text='Dominant', variable=side_var, value='d', command=set_data)
non_dominant_radio = tk.Radiobutton(select_data_frame, text='Nondominant', variable=side_var, value='nd',
                                    command=set_data)
dominant_radio.grid(row=2, column=0, sticky='w')
non_dominant_radio.grid(row=2, column=1,sticky='w')
#select gender
male_selected_var = tk.BooleanVar()
female_selected_var = tk.BooleanVar()
male_checkbox = tk.Checkbutton(select_data_frame, text='males', command=set_data, variable=male_selected_var)
female_checkbox = tk.Checkbutton(select_data_frame, text='females', command=set_data, variable=female_selected_var)
female_checkbox.select()
male_checkbox.grid(row=3, column=0, sticky='w')
female_checkbox.grid(row=3, column=1, sticky='w')
show_groups_var=tk.BooleanVar()
show_groups_var.set(False)
show_groups_box=tk.Checkbutton(select_data_frame,text='Show groups',variable=show_groups_var,command=set_data)
show_groups_box.grid(row=4,column=0,columnspan=2,sticky='w')
select_data_frame.grid(row=0, pady=5)

select_subj_frame = braviz.interaction.subjects_list(reader, set_subj, control_frame, text='Subject', padx=10, pady=5,
                                                     height='100')
select_subj_frame.grid(column=0, row=1, sticky='news')
control_frame.rowconfigure(1, weight=1)


#def print_camera(event=None):
#    cam1 = ren.GetActiveCamera()
#    print cam1
#
#print_camera_button=tk.Button(control_frame,text='print_cammera',command=print_camera)
#print_camera_button.grid()


def show_all_or_history(event=None):
    global showing_history
    if showing_history is True:
        showing_history = False
        show_all_or_history_button['text'] = 'Show history'
        add_to_hist_button['state'] = 'disabled'
        remove_from_hist_button['state'] = 'disabled'
    else:
        showing_history = True
        show_all_or_history_button['text'] = 'Show all'
        add_to_hist_button['state'] = 'normal'
        remove_from_hist_button['state'] = 'normal'
    draw_bars_1()


show_all_or_history_button = tk.Button(control_frame, text='Show all', command=show_all_or_history)
show_all_or_history_button.grid(sticky='ew')


def add_to_history(event=None):
    if current_subject in selected_codes:
        selected_codes.remove(current_subject)
    selected_codes.append(current_subject)
    #print selected_codes
    draw_bars_1()


add_to_hist_button = tk.Button(control_frame, text='Add to history <----', command=add_to_history)
add_to_hist_button.grid(sticky='ew')


def remove_from_history(event=None):
    if current_subject in selected_codes:
        selected_codes.remove(current_subject)
    draw_bars_1()


remove_from_hist_button = tk.Button(control_frame, text='Remove from history', command=remove_from_history)
remove_from_hist_button.grid(sticky='ew')


#=====================================================================
display_frame = tk.Frame(root)
renderer_frame = tk.Frame(display_frame)
renderer_frame.grid(padx=3, pady=3, row=0, column=0, sticky='nsew')
render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                            rw=renWin, width=600,
                                            height=300)
render_widget.pack(fill='both', expand='true')
display_frame.rowconfigure(0, weight=1)
display_frame.columnconfigure(0, weight=1)

graphs_frame = tk.Frame(display_frame)

bars_widget1 = bars_view1.get_widget(graphs_frame,
                                     width=500,
                                     height=200)

bars_widget1.grid(column=0, row=0, sticky='nsew')

bars_widget2 = bars_view2.get_widget(graphs_frame,
                                     width=100,
                                     height=200)

bars_widget2.grid(column=1, row=0, sticky='nsew')

graphs_frame.grid(padx=3, pady=3, row=1, column=0, sticky='nsew')
graphs_frame.columnconfigure(0, weight=3)
graphs_frame.columnconfigure(1, weight=0)
graphs_frame.rowconfigure(0, weight=1)

display_frame.rowconfigure(0, weight=3)
display_frame.rowconfigure(1, weight=2)
control_frame.pack(side="left", anchor="n", fill="y", expand="false")
display_frame.pack(side="left", anchor="n", fill="both", expand="true")


def clean_exit(event=None):
    global renWin
    print "adios"
    renWin.FastDelete()
    del renWin
    root.after_idle(root.quit)
    root.destroy()

    #root.destroy()
    #root.withdraw()
    #root.after_idle(quit2)

#root.protocol("WM_DELETE_WINDOW", clean_exit)
#render_widget.bind('<Destroy>',clean_exit,'+')




def print_event(caller=None, event=None):
    print event


def click_in_bar(event=None):
    if show_groups_var.get() and not showing_history:
        print "Not implemented yet"
        return
    select_subj_frame.subjects_list.selection_clear(0, tk.END)
    clicked_subj=bars_view1.get_current_name()
    index=codes2.index(clicked_subj)
    select_subj_frame.subjects_list.select_set(index,index)
    set_subj()
bars_widget1.bind('<<PlotSelected>>',click_in_bar)


def bars_1_msg_func(event=None):
    hover_subj=bars_view1.get_current_name()
    if not showing_history and show_groups_var.get():
        mean,std=group_stats_dict.get(hover_subj)
        return "%s : %.2f ( %.2f )"%(hover_subj,mean,std)
    tms_value=tms_data_dict.get(hover_subj)
    if tms_value is None:
        return ''
    return "%s : %.2f"%(hover_subj,tms_value)

bars_1_tooltip=ToolTip(bars_widget1, msgFunc=bars_1_msg_func, follow=1, delay=0.5)


def bars_2_msg_func(event=None):
    hover_subj=bars_view2.get_current_name()
    if hover_subj is None:
        return ''
    try:
        hover_code=codes2.index(hover_subj)
    except ValueError:
        return ''
    tms_value=tms_data2[hover_code]
    return "%s : %.2f"%(hover_subj,tms_value)


bars_2_tooltip=ToolTip(bars_widget2, msgFunc=bars_2_msg_func, follow=1, delay=0.5)

data_selection_tree.see('inhi')
data_selection_tree.selection_add('inhi')

root.after(8000,turn_on_animation)

iact = render_widget.GetRenderWindow().GetInteractor()
custom_iact_style = config.get_interaction_style()
iact_style = getattr(vtk, custom_iact_style)()
iact.SetInteractorStyle(iact_style)

cam1 = ren.GetActiveCamera()
cam1.SetPosition(0.358526, 8.24682, 122.243)
cam1.SetViewUp(1, 0, 0)
cam1.SetFocalPoint(-0.00880438, -6.19902, 5.5735)
ren.ResetCameraClippingRange()
render_widget.Render()

iact.Initialize()
renWin.Render()
iact.Start()
set_data()
set_subj()

root.focus()
root.mainloop()