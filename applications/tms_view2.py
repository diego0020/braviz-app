from __future__ import division
import Tkinter as tk
import ttk
import numpy as np
import math
from braviz.readAndFilter.read_csv import get_column
from braviz.visualization.vtk_charts import multi_bar_plot
import os
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
    vtkTkRenderWindowInteractor
from braviz.interaction.tk_tooltip import ToolTip

import braviz

__author__ = 'Diego'
reader = braviz.readAndFilter.kmc40AutoReader(max_cache=100)


#=======global variables=======
current_subject = '207'
tms_column = 'ICId'
invert_data = True   # perform 100 - tms_data
term_mean = 0
term_std_dev = 0
codes2 = []
tms_data2 = []
tms_data_dict = {}
context_lines = [term_mean + term_std_dev, term_mean, term_mean - term_std_dev]
context_dashes = [True, False, True]
data_code = 'ICI'
selected_codes = []
showing_history = True
data_code = ""
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
#________TMS_DATA_________________

csv_file = os.path.join(reader.getDataRoot(), 'baseFinal_TMS.csv')
#--------------------------------------------------------
#create_chart_1
bars_view_1 = multi_bar_plot()

#create chart2
bars_view_2 = multi_bar_plot()

#===============read data=====================
def setData(Event=None):
    global codes2, tms_data2, term_mean, term_std_dev, tms_column, context_lines, data_code, disp2axis
    invert_data = invet_data_dict[data_code]
    tms_column = data_code + side_var.get()
    codes = get_column(csv_file, 'CODE')
    genres = get_column(csv_file, 'GENDE')
    grupo = get_column(csv_file, 'UBICA') #1=canguro, 2=control, 3=gorditos
    TMS_metric = get_column(csv_file, tms_column, True)
    if invert_data is True:
        TMS_metric = map(lambda x: 100 - x, TMS_metric)

    valid_genres = []
    if male_selected_var.get(): valid_genres.append('2')
    if female_selected_var.get(): valid_genres.append('1')
    table = zip(codes, genres, grupo, TMS_metric)
    for row in table:
        tms_data_dict[row[0]] = row[3]
    table_genre = filter(lambda y: y[1] in valid_genres, table)
    term = filter(lambda x: x[2] == '3', table_genre)
    if len(term) > 0:
        term_data = zip(*term)[3]
        term_data = filter(lambda x: not math.isnan(x), term_data)
        term_mean = np.mean(term_data)
        term_std_dev = np.std(term_data)
    else:
        term_mean = 0
        term_std_dev = 0
    if len(table_genre) > 0:
        codes2, _, _, tms_data2 = zip(*table_genre)
    else:
        codes2 = []
        tms_data2 = []

    #only keep codes and tms_data columns from filtered table

    context_lines = [term_mean + term_std_dev, term_mean, term_mean - term_std_dev]

    bars_view_1.set_color_fun(get_color)
    bars_view_1.set_y_limis(*limits_dict[data_code])

    bars_view_1.set_lines(context_lines, context_dashes)

    bars_view_1.set_y_title(labels_dict[data_code])

    bars_view_2.set_y_title(labels_dict[data_code])
    bars_view_2.set_y_limis(*limits_dict[data_code])
    bars_view_2.set_all(1, 5, 100)
    bars_view_2.set_color_fun(get_color)
    bars_view_2.set_lines(context_lines, context_dashes)
    draw_bars_1()
    try:
        previous_selection = select_subj_frame.get()
    except tk.TclError:
        previous_selection = None
    select_subj_frame.tk_listvariable.set(codes2)
    if previous_selection in codes2:
        idx = codes2.index(previous_selection)
        select_subj_frame.subjects_list.selection_clear(0, tk.END)
        select_subj_frame.subjects_list.select_set(idx, idx)

    setSubj()


def draw_bars_1():
    global disp2axis
    if showing_history is True:
        bars_view_1.set_all(len(selected_codes), 5, 500)
        selected_values = [tms_data_dict[s] for s in selected_codes]
        bars_view_1.set_data(selected_values, selected_codes)
        try:
            idx = selected_codes.index(current_subject)
        except ValueError:
            bars_view_1.set_enphasis(None)
        else:
            bars_view_1.set_enphasis(idx)
    else:
        bars_view_1.set_all(len(codes2), 5, 500)
        selected_values = [tms_data_dict[s] for s in codes2]
        bars_view_1.set_data(selected_values, codes2)
        try:
            idx = codes2.index(current_subject)
        except ValueError:
            bars_view_1.set_enphasis(None)
        else:
            bars_view_1.set_enphasis(idx)
    bars_view_1.paint_bar_chart()
    disp2axis = get_mapper_function()


previous_value = 0


def setSubj(Event=None):
    global fibers, current_subject, previous_value
    #print "setting subjects"
    if len(codes2) == 0:
        bars_view_2.set_data([], [])
        bars_view_2.set_y_limis(*limits_dict[data_code])
        bars_view_2.paint_bar_chart()
        fibers_actor.SetVisibility(0)
        renWin.Render()
        return
    try:
        current_subject = select_subj_frame.get()
    except tk.TclError:
        select_subj_frame.subjects_list.select_set(0, 0)
        current_subject = select_subj_frame.get()
    try:
        fibers = reader.get('fibers', current_subject, space='talairach')
    except:
        fibers_actor.SetVisibility(0)
    else:
        fibers_mapper.SetInputData(fibers)
        fibers_actor.SetVisibility(1)

    try:
        if showing_history is True:
            idx = selected_codes.index(current_subject)
        else:
            idx = codes2.index(current_subject)
    except ValueError:
        bars_view_1.set_enphasis(None)
    else:
        bars_view_1.set_enphasis(idx)

    bars_view_1.paint_bar_chart()
    new_value = tms_data_dict[current_subject]
    time_steps = 7
    renWin.Render()
    if time_steps > 0:
        slope = (new_value - previous_value) / time_steps
    else:
        previous_value = new_value
        slope = 0
    animated_draw_bar(time_steps, slope, previous_value, current_subject)
    previous_value = new_value


def animated_draw_bar(time, slope, value, code):
    bars_view_2.set_data([value], [code])
    #bars_view_2.set_y_limis(-100,100)
    bars_view_2.paint_bar_chart()
    if (time > 0):
        root.after(50, animated_draw_bar, time - 1, slope, value + slope, code)


def get_color(value):
    z_score = abs(value - term_mean) / term_std_dev

    if z_score <= 0.5:
        return (26, 150, 65, 255)
    elif z_score <= 1:
        return (166, 217, 106, 255)
    elif z_score <= 1.5:
        return (255, 225, 191, 255)
    elif z_score <= 2:
        return (253, 174, 97, 255)
    else:
        return (215, 25, 28, 255)


#===============================================Inteface=================================

root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
top.title('BraViz-TMS_View')

control_frame = tk.Frame(top, width=100)

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
    'IHIfreq': (-20, 120),
    'RMT': (0, 100),
    'IHIdur': (-2, 35),
    'MEPlat': (-2, 20),
    'ICF': (-10, 400),
    'ICI': (-10, 120),
    'IHIlat': (-2, 35 )
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
data_code = 'ICI'
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


def select_data(Event=None):
    data_selection_tree.after_idle(select_data2)


def select_data2(Event=None):
    global data_code

    selected_leaf = data_selection_tree.focus()
    data_code = data_codes_dict[selected_leaf]
    setData()


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


def msgFunc(event=None):
    coord = event.y
    #print coor
    element = data_selection_tree.identify_row(coord)
    if len(element) == 0:
        return ''
    return long_messages_dict[element]


t1 = ToolTip(data_selection_tree, msgFunc=msgFunc, follow=1, delay=1)


#---------------------------------------
data_selection_tree.grid(row=0, column=0, columnspan=2, sticky='ew')
#select side
side_var = tk.StringVar()
side_var.set('d')
hemisphere_label = tk.Label(select_data_frame, text='Hemisphere:')
hemisphere_label.grid(row=1, column=0, columnspan=2, sticky='ew')
dominant_radio = tk.Radiobutton(select_data_frame, text='Dominant', variable=side_var, value='d', command=setData)
non_dominant_radio = tk.Radiobutton(select_data_frame, text='Nondominant', variable=side_var, value='nd',
                                    command=setData)
dominant_radio.grid(row=2, column=0, sticky='w')
non_dominant_radio.grid(row=2, column=1)
#select gender
male_selected_var = tk.BooleanVar()
female_selected_var = tk.BooleanVar()
male_checkbox = tk.Checkbutton(select_data_frame, text='male', command=setData, variable=male_selected_var)
female_checkbox = tk.Checkbutton(select_data_frame, text='female', command=setData, variable=female_selected_var)
female_checkbox.select()
male_checkbox.grid(row=3, column=0)
female_checkbox.grid(row=3, column=1)

select_data_frame.grid(row=0, pady=5)

select_subj_frame = braviz.interaction.subjects_list(reader, setSubj, control_frame, text='Subject', padx=10, pady=5,
                                                     height='100')
select_subj_frame.grid(column=0, row=1, sticky='news')
control_frame.rowconfigure(1, weight=1)


def print_camera(Event=None):
    cam1 = ren.GetActiveCamera()
    #cam1.Elevation(80)
    #cam1.SetViewUp(0, 0, 1)
    #cam1.Azimuth(80)
    print cam1

#print_camera_button=tk.Button(control_frame,text='print_cammera',command=print_camera)
#print_camera_button.grid()
def show_all_or_history(Event=None):
    global showing_history
    if showing_history == True:
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


def add_to_history(Event=None):
    if current_subject in selected_codes:
        selected_codes.remove(current_subject)
    selected_codes.append(current_subject)
    #print selected_codes
    draw_bars_1()


add_to_hist_button = tk.Button(control_frame, text='Add to history <----', command=add_to_history)
add_to_hist_button.grid(sticky='ew')


def remove_from_history(Event=None):
    if current_subject in selected_codes:
        selected_codes.remove(current_subject)
    draw_bars_1()


remove_from_hist_button = tk.Button(control_frame, text='Remove from history', command=remove_from_history)
remove_from_hist_button.grid(sticky='ew')



#=====================================================================
display_frame = tk.Frame(top)
renderer_frame = tk.Frame(display_frame)
renderer_frame.grid(padx=3, pady=3, row=0, column=0, sticky='nsew')
render_widget = vtkTkRenderWindowInteractor(renderer_frame,
                                            rw=renWin, width=600,
                                            height=300)
render_widget.pack(fill='both', expand='true')
display_frame.rowconfigure(0, weight=1)
display_frame.columnconfigure(0, weight=1)

graphs_frame = tk.Frame(display_frame)
bars_widget1 = vtkTkRenderWindowInteractor(graphs_frame,
                                           width=500,
                                           height=200)
bars_view_1.SetRenderWindow(bars_widget1.GetRenderWindow())
bars_view_1.SetInteractor(bars_widget1.GetRenderWindow().GetInteractor())

bars_widget1.grid(column=0, row=0, sticky='nsew')

bars_widget2 = vtkTkRenderWindowInteractor(graphs_frame,
                                           width=100,
                                           height=200)
bars_view_2.SetRenderWindow(bars_widget2.GetRenderWindow())
bars_view_2.SetInteractor(bars_widget2.GetRenderWindow().GetInteractor())
bars_widget2.grid(column=1, row=0, sticky='nsew')

graphs_frame.grid(padx=3, pady=3, row=1, column=0, sticky='nsew')
graphs_frame.columnconfigure(0, weight=3)
graphs_frame.columnconfigure(1, weight=1)
graphs_frame.rowconfigure(0, weight=1)

display_frame.rowconfigure(0, weight=3)
display_frame.rowconfigure(1, weight=2)
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
custom_iact_style = config.get_interaction_style()
iact_style = getattr(vtk, custom_iact_style)()
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
    ax0 = a1.GetMinimum()
    axf = a1.GetMaximum()

    def disp2axis(x):
        t = (x - x0) / (xf - x0)
        x = (t * (axf - ax0) + ax0)
        return x

    return disp2axis


disp2axis = lambda x: x


def get_subj_index(x):
    if bars_view_1.start < x < bars_view_1.get_bar_graph_width() + bars_view_1.start:
        index = int((x - bars_view_1.start) // (bars_view_1.width + 1))
        if showing_history is True:
            code = selected_codes[index]
            index = codes2.index(code)
        return index
    return None


iact.Initialize()
renWin.Render()
iact.Start()
setData()
setSubj()
bars_view_1.Render()
disp2axis = get_mapper_function()


def print_event(caller=None, event=None):
    print event


def resize_handler(caller=None, event=None):
    top.after(1000, do_resize)


def do_resize():
    global disp2axis
    bars_view_2.ren.Render()
    disp2axis = get_mapper_function()


def draw_bar1_tooltip(caller=None, event=None):
    tool_tip = bars_view_1.chart.GetTooltip()
    event_position = caller.GetEventPosition()
    event_coordinates = disp2axis(event_position[0])
    if get_subj_index(event_coordinates) is not None:
        tool_tip.SetVisible(1)
        tool_tip.SetPosition(event_position)
        index = int((event_coordinates - bars_view_1.start) // (bars_view_1.width + 1))
        if showing_history is True:
            code = selected_codes[index]
        else:
            code = codes2[index]
        datum = tms_data_dict[code]
        message = "%s : %.2f" % (code, datum)
        tool_tip.SetText(message)
    else:
        tool_tip.SetVisible(0)

    bars_view_1.Render()


def draw_bar2_tooltip(caller=None, event=None):
    tool_tip2 = bars_view_2.chart.GetTooltip()
    event_position = caller.GetEventPosition()
    event_x = event_position[0]
    x0 = bars_view_2.chart.GetAxis(1).GetPoint1()[0]
    xf = bars_view_2.chart.GetAxis(1).GetPoint2()[0]
    if x0 < event_x < xf:
        tool_tip2.SetVisible(1)
        tool_tip2.SetPosition(event_position)
        code = current_subject
        datum = tms_data_dict[code]
        message = "%s : %.2f" % (code, datum)
        tool_tip2.SetText(message)
    else:
        tool_tip2.SetVisible(0)
    bars_view_2.Render()


def click_in_bar(caller=None, event=None):
    event_position = caller.GetEventPosition()
    event_coordinates = disp2axis(event_position[0])
    index = get_subj_index(event_coordinates)
    if index is not None:
        select_subj_frame.subjects_list.selection_clear(0, tk.END)
        select_subj_frame.subjects_list.select_set(index, index)
        setSubj()


#interaction_event_id=bars_view_1.chart.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
#interaction_event_id=bars_view_1.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
#interaction_event_id=bars_view_1.GetScene().AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
#bar1=bars_view_1.chart.GetPlot(0)
#interaction_event_id=bar1.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)

iact2 = bars_view_1.GetInteractor()
iact3 = bars_view_2.GetInteractor()
#print iact2
#interaction_event_id=iact2.AddObserver(vtk.vtkCommand.AnyEvent,print_event,100)
interaction_event_id = iact2.AddObserver(vtk.vtkCommand.MouseMoveEvent, draw_bar1_tooltip, 100)
interaction_event_id = iact3.AddObserver(vtk.vtkCommand.MouseMoveEvent, draw_bar2_tooltip, 100)
interaction_event_id = iact2.AddObserver(vtk.vtkCommand.LeftButtonPressEvent, click_in_bar, 100)
#MouseMoveEvent_event_id=iact2.AddObserver(vtk.vtkCommand.MouseMoveEvent,abort_interaction_event,100)
# Start Tkinter event loop
top.bind('<Configure>', resize_handler)
top.focus()
root.mainloop()