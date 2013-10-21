from __future__ import division
import Tkinter as tk
import ttk
from os.path import join as path_join
from braviz.readAndFilter.read_csv import get_headers,get_column
from braviz.visualization.create_lut import get_colorbrewer_lut
import vtk
import thread
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import braviz

#globals
__author__ = 'Diego'
root = tk.Tk()
root.withdraw()
reader=braviz.readAndFilter.kmc40AutoReader(max_cache=2)
data_root=reader.getDataRoot()
file_name=path_join(data_root,'test_small.csv')
id_list=reader.get('ids')
models_set=set()
fibers_var=tk.BooleanVar()
fibers_op_var=tk.StringVar()
color_column=None
color_data_dict={}
sort_data_dict={}
sort_column=None

widgets=[]
models_dict={}
async_processing_models=False
def load_models(event=None):
    global async_processing_models
    #disable buttons
    for w in widgets:
        w.config(state='disabled')
    async_processing_models=True
    progress.set(0)
    #async_load_models()
    thread.start_new_thread(async_load_models,tuple())
    top.after(20,finish_load_models)
    #finish_load_models()

def finish_load_models():
    global models_dict,async_processing_models
    if async_processing_models==False:
        grid_view.set_data(models_dict)
        grid_view.Render()
        for w in widgets:
            w.config(state='normal')
        add_fibers_operation['state']='readonly'
        set_hide_waypoints_state()
    else:
        top.after(20,finish_load_models)
    progress.set(len(models_dict)/len(id_list)*100)
#-------------------------
def async_load_models():
    global models_dict,async_processing_models
    models_dict.clear()
    for i,subj in enumerate(id_list):
        models=[]
        if not (fibers_var.get() and hide_waypoints_var.get()):
            for model_name in models_set:
                try:
                    models.append(reader.get('model',subj,name=model_name))
                except:
                    pass
        #load fibers
        if fibers_var.get() is True:
            if fibers_op_var.get()=='through any':
                operation='or'
            else:
                operation='and'
            try:
                fibers=reader.get('fibers',subj,waypoint=list(models_set),operation=operation)
            except:
                pass
            models.append(fibers)
        #append
        append_filter=vtk.vtkAppendPolyData()
        for mod in models:
            append_filter.AddInputData(mod)
        append_filter.Update()
        models_dict[subj]=append_filter.GetOutput()
    async_processing_models=False


def get_data_dict(col_name,nan_value=float('nan')):
    codes=get_column(file_name,'code')
    data=get_column(file_name,col_name,True,nan_value=nan_value)
    return dict(zip(codes,data))

def sort_models():
    global sort_data_dict,sort_column
    col_idx=tab_list.curselection()
    sort_column=tab_list.get(col_idx)
    sort_data_dict=get_data_dict(sort_column,nan_value=float('+inf'))
    sorted_subjects=id_list[:]
    sorted_subjects.sort(key=lambda x:sort_data_dict.get(x,float('+inf')))
    grid_view.sort(sorted_subjects)
    grid_view.reset_camera()
    update_balloons()
    grid_view.set_sort_message_visibility(True)
    grid_view.update_sort_message(sort_column)
    grid_view.Render()
    #print sort_data_dict['1258']
    #print sorted_subjects

def color_models():
    global color_data_dict,color_column
    col_idx=tab_list.curselection()
    color_column=tab_list.get(col_idx)
    color_data_dict=get_data_dict(color_column)
    min_value=min(color_data_dict.values())
    max_value=max(color_data_dict.values())
    color_table=get_colorbrewer_lut(min_value,max_value,'RdBu',9,nan_color=(0.95,0.47,0.85))
    def color_fun(s):
        x=color_data_dict.get(s,float('nan'))
        return color_table.GetColor(x)
    grid_view.set_color_function(color_fun)
    grid_view.set_color_bar_visibility(True)
    grid_view.update_color_bar(color_table,color_column)
    update_balloons()
    grid_view.Render()

def update_balloons():
    messages_dict={}
    for subj in id_list:
        message="%s\n%s : %.2f\n%s : %.2f"%(subj,
                                            color_column,color_data_dict.get(subj,float('nan')),
                                            sort_column,sort_data_dict.get(subj,float('nan')))
        messages_dict[subj]=message
    grid_view.set_balloon_messages(messages_dict)

#===========GUI=====================


top = tk.Toplevel(root)
top.title('BraViz-grid view')

control_frame = tk.Frame(top,width=100,border=1)
control_frame.grid(row=0,column=0,sticky='nsew')
top.columnconfigure(0, minsize=100)
top.rowconfigure(0, weight=1)

tab_frame=tk.Frame(control_frame)
sep=ttk.Separator(control_frame,orient=tk.HORIZONTAL)
struct_frame=tk.Frame(control_frame)

tab_frame.grid(column=0,row=0,sticky='nsew')
sep.grid(column=0,row=1,sticky='ew')

control_frame.rowconfigure(0,weight=1)
control_frame.rowconfigure(2,weight=1)
control_frame.columnconfigure(0,weight=1,minsize=120)
struct_frame.grid(column=0,row=2,sticky='snew')

#===========================Tabular================================
tab_frame.columnconfigure(0, weight=1)
tab_frame.rowconfigure(2, weight=1)
Tabular_label=tk.Label(tab_frame,text='Tabular Data')
Tabular_label.grid(row=0,column=0,sticky='ew',pady=10)

tab_operation_frame=tk.Frame(tab_frame)
sort_button=tk.Button(tab_operation_frame,text='Sort by',command=sort_models)
color_button=tk.Button(tab_operation_frame,text='Color by',command=color_models)

sort_button.grid(row=0,column=0,sticky='ew')
color_button.grid(row=0,column=1,sticky='ew')
tab_operation_frame.columnconfigure(0,weight=1)
tab_operation_frame.columnconfigure(1,weight=1)
tab_operation_frame.grid(row=1,sticky='ew')

tab_list_frame=tk.LabelFrame(tab_frame,text='Select Variable')


tab_list_and_bar=tk.Frame(tab_list_frame)
tab_list_and_bar.pack(side='top',fill='both',expand=1)
tab_scrollbar=tk.Scrollbar(tab_list_and_bar,orient=tk.VERTICAL)
tab_list=tk.Listbox(tab_list_and_bar,selectmode=tk.BROWSE,yscrollcommand=tab_scrollbar.set,exportselection=0)
tab_scrollbar.config(command=tab_list.yview)
tab_scrollbar.pack(side=tk.RIGHT,fill=tk.Y,expand=1)
tab_list.pack(side="left",fill='both',expand=1)
headers=get_headers(file_name)
#headers=['babd','abfdb','sadf']

for h in headers:
    tab_list.insert(tk.END,h)

tab_list.select_set(1,1)


tab_list_frame.grid(row=2,column=0,sticky='nsew')


#===========================Structure Metrics=================================
struct_frame.columnconfigure(0, weight=1)
struct_frame.rowconfigure(1, weight=1)
struct_label=tk.Label(struct_frame,text='Structures')
struct_label.grid(row=0,column=0,sticky='ew',pady=10)
def change_models(action,model_name):
    if action=='add':
        models_set.add(model_name)
    else:
        models_set.remove(model_name)

select_model_frame=braviz.interaction.structureList(reader,'144',change_models,struct_frame)
select_model_frame.grid(row=1,column=0,sticky='snew',pady=5)

def set_hide_waypoints_state(event=None):
    if fibers_var.get() is True:
        hide_waypoints_check.config(state='normal')
    else:
        hide_waypoints_check.config(state='disabled')
fibers_frame=tk.Frame(struct_frame)
add_fibers_check=tk.Checkbutton(fibers_frame,text='add fibers',variable=fibers_var,command=set_hide_waypoints_state)
add_fibers_check.grid(row=0,column=0,sticky='w')
fibers_op_var.set('through any')
add_fibers_operation=ttk.Combobox(fibers_frame,textvariable=fibers_op_var,state='readonly',width=10)
add_fibers_operation['values']=('through all','through any')
add_fibers_operation.grid(row=0,column=1,sticky='e')
hide_waypoints_var=tk.BooleanVar()
hide_waypoints_var.set(0)
hide_waypoints_check=tk.Checkbutton(fibers_frame,variable=hide_waypoints_var,text='hide waypoints',state='disabled')
hide_waypoints_check.grid(row=1,column=0,columnspan=2,sticky='w')
fibers_frame.grid(sticky='ew')

apply_model_selection_button=tk.Button(struct_frame,text='Apply selection',command=load_models)
apply_model_selection_button.grid(sticky='ew')


progress=tk.IntVar()
progress.set(0)

progress_bar=ttk.Progressbar(struct_frame,orient='horizontal',length='100',mode='determinate',variable=progress)
progress_bar.grid(sticky='ew',pady=5,padx=5)

#=====================================================================
renderer_frame = tk.Frame(top)
renderer_frame.grid(row=0,column=1,sticky='ewsn')
top.columnconfigure(1, weight=1)


grid_view=braviz.visualization.grid_view()

render_widget = vtkTkRenderWindowInteractor(renderer_frame,rw=grid_view,width=600, height=600)



renderer_frame.columnconfigure(0, weight=1)
renderer_frame.rowconfigure(0, weight=1)
render_widget.grid(row=0,column=0,sticky='ewsn')


iact=render_widget.GetRenderWindow().GetInteractor()
grid_view.set_interactor(iact)
iact.SetInteractorStyle(vtk.vtkInteractorStyleTrackballActor())
widgets=[apply_model_selection_button,sort_button,color_button,add_fibers_check,add_fibers_operation,select_model_frame,tab_list,hide_waypoints_check]

def clean_exit():
    global grid_view
    print "adios"
    grid_view.FastDelete()
    del grid_view

    quit(0)
top.protocol("WM_DELETE_WINDOW", clean_exit)

#===============================================
#create interesting initial view
async_load_models()
finish_load_models()
color_models()
sort_models()
grid_view.set_orientation((-11.357671297580744, -94.18586865794096, 97.555764310434))
root.after(20,sort_models)
# Start Tkinter event loop
root.mainloop()
