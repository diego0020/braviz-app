from __future__ import division
import Tkinter as tk
import ttk
from os.path import join as path_join
import cPickle
import thread
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
     vtkTkRenderWindowInteractor

import braviz
from scipy.stats import linregress
import numpy as np
from itertools import izip
from braviz.readAndFilter.link_with_rdf import cached_get_free_surfer_dict
from braviz.interaction.tk_tooltip import ToolTip

reader=braviz.readAndFilter.kmc40AutoReader(max_cache=500)
data_root=reader.getDataRoot()
file_name=path_join(data_root,'test_small.csv')
cancel_calculation_flag=False
named_fibers=set(reader.get('fibers','093',index=1))


def get_headers():
    csv_file=open(file_name)
    headers=csv_file.readline()
    headers=headers.rstrip('\n')
    headers=headers.split(';')
    csv_file.close()    
    return headers


def get_column(name,numeric=False):
    csv_file=open(file_name)
    headers=csv_file.readline()
    headers=headers.rstrip('\n')
    headers=headers.split(';')
    if name not in headers:
        print "column %s not found in file"%name
        return None
    idx=headers.index(name)
    column=[]
    for l in iter(csv_file.readline,''):
        l2=l.rstrip('\n')
        l2=l2.split(';')
        item=l2[idx]
        if numeric:
            try:
                num=float(item)
            except ValueError:
                try:
                    #some decimals number saved using a comma
                    item=item.replace(',','.')
                    num=float(item)
                except:
                    num=float('nan')
            item=num
        column.append(item)
    csv_file.close()
    return column


def column_to_vtk_array(col,name='unknown'):
    if not isinstance(col[0],str):
        array=vtk.vtkFloatArray()
        array.InsertNextValue(col[0])
    else:
        array=vtk.vtkStringArray()
        array.InsertNextValue(col[0])
    for item in col:
        array.InsertNextValue(item)
        #print "adding %s"%item
    array.SetName(name)
    return array


def get_struct_metric(struct_name,code,metric='volume'):
    print "calculating %s for %s"%(metric,struct_name)
    if not struct_name.startswith('Fib'):
        try:
            model=reader.get('model',code,name=struct_name)
        except Exception:
            print "%s not found for subject %s"%(struct_name,code)
            return float('nan')
    if metric=='volume':
        return reader.get('model',code,name=struct_name,volume=1)
    if metric=='area':
        area, volume = braviz.interaction.compute_volume_and_area(model)
        return area
    elif metric=='nfibers':
        return get_fibers_metric(struct_name,code,'number')
    elif metric=='lfibers':
        return get_fibers_metric(struct_name,code,'mean_length')
    elif metric=='fa_fibers':
        return get_fibers_metric(struct_name,code,'mean_fa')
    else:
        print "unknown metric %s"%metric
        return None

def get_fibers_metric(struct_name,code,metric='number'):
    #print "calculating for subject %s"%code
    n=0
    if struct_name.startswith('Fibs:'):
        #print "we are dealing with special fibers"
        try:
            fibers = reader.get('fibers', code, name=struct_name[6:], color='fa')
        except Exception:
            n = float('nan')
            return n
    else:
        try:
            fibers=reader.get('fibers',code,waypoint=struct_name,color='fa')
        except Exception:
            n=float('nan')
            return n
    if fibers is None:
        #print "Problem loading fibers for subject %s"%code
        n=float('nan')
        return n
    elif metric=='number':
        n=fibers.GetNumberOfLines()
    elif metric=='mean_length':
        desc=braviz.interaction.get_fiber_bundle_descriptors(fibers)
        n=float(desc[1])
    elif metric=='mean_fa':
        desc=braviz.interaction.aggregate_fiber_scalar(fibers, component=0, norm_factor=1/255)
        del fibers
        n=float(desc[1])
    else:
        print 'unknowm fiber metric %s'%metric
        return float('nan')
    #print '%s : %f'%(code,n)
    return n


def get_struct_metrics_col():
    global struct_metrics_col,temp_struct_metrics_col,processing,cancel_calculation_flag,struct_name,metric
    metric_temp=long_names_dict[metric_var.get()]
    struct_idx = model_list.curselection()
    struct_name_temp = model_list.get(struct_idx)
    key='column_%s_%s'%(struct_name_temp.replace(':','_'),metric_temp.replace(':','_'))
    cache_file_name=path_join(reader.getDataRoot(),'pickles','%s.pickle'%key)
    try:
        with open(cache_file_name,'rb') as cachef:
            struct_metrics_col=cPickle.Unpickler(cachef).load()
    except IOError:
        pass
    else:
        struct_name=struct_name_temp
        metric=metric_temp
        refresh_table()
        refresh_display()
        return
    print "Calculating %s for structure %s"%(metric_temp,struct_name_temp)
    temp_struct_metrics_col=[]
    #async_get_struct_metric()
    calculate_button['text']='Cancel'
    processing=True
    cancel_calculation_flag=False
    thread.start_new_thread(async_get_struct_metric,(metric_temp,struct_name_temp))
    top.after(20,finish_get_struct_metric,cache_file_name)


def async_get_struct_metric(metric_temp,struct_name_temp):
    global temp_struct_metrics_col
    for code in codes:
        if cancel_calculation_flag is True:
            print "cancel flag received"
            temp_struct_metrics_col = []
            break
        scalar=get_struct_metric(struct_name_temp,code,metric_temp)
        temp_struct_metrics_col.append(scalar)


def finish_get_struct_metric(cache_file_name):
    global struct_metrics_col,processing,struct_name,metric
    number_calculated = len(temp_struct_metrics_col)
    if (cancel_calculation_flag is True) and (number_calculated==0):
        print "aborting"
        processing=False
        calculate_button['text']='Calculate'
        refresh_table()
        refresh_display()
        return
    if number_calculated==len(codes):
        try:
            with open(cache_file_name,'wb') as cachef: cPickle.Pickler(cachef,2).dump(struct_metrics_col)
        except Exception:
            print "cache write failed"
            print "file was %s"%cache_file_name
            pass
        struct_metrics_col=temp_struct_metrics_col
        metric=long_names_dict[metric_var.get()]
        processing = False
        calculate_button['text']='Calculate'
        struct_idx = model_list.curselection()
        struct_name = model_list.get(struct_idx)
        refresh_table()
        refresh_display()
    else:
        #print number_calculated/len(codes)
        progress_bar_var.set(number_calculated/len(codes)*100)
        top.after(20, finish_get_struct_metric, cache_file_name)

tab_var_name='WMIIQ'
tab_column=get_column(tab_var_name, True)

codes=get_column('code', False)
#print codes

struct_name='CC_Anterior'
metric='volume'
table=vtk.vtkTable()

struct_metrics_col=[]

view=vtk.vtkContextView()
view.GetRenderer().SetBackground(1.0,1.0,1.0)
view.GetRenderWindow().SetSize(400,300)


chart=vtk.vtkChartXY()
view.GetScene().AddItem(chart)
chart.SetShowLegend(False)

points=chart.AddPlot(vtk.vtkChart.POINTS)

points.SetColor(0,0,0,255)
points.SetWidth(1.0)
points.SetMarkerStyle(vtk.vtkPlotPoints.CIRCLE)
points.SetIndexedLabels(column_to_vtk_array(codes,'code'))
points.SetTooltipLabelFormat('code=%i')
table.AddColumn(column_to_vtk_array(codes,'Code'))

def refresh_table():
    table.RemoveColumn(2)
    table.RemoveColumn(1)

    #print struct_metrics_col
    table.AddColumn(column_to_vtk_array(tab_column,tab_var_name))
    table.AddColumn(column_to_vtk_array(struct_metrics_col,'%s - %s'%(struct_name,metric) ))
     
    #for c,t,s in izip(codes,tab_column,struct_metrics_col):
    #    print "%s: %f , %f"%(c,t,s)
    
    points.SetInputData(table,1,2)
    points.Update()
    xaxis=chart.GetAxis(1)
    xaxis.SetTitle(tab_var_name)
    yaxis=chart.GetAxis(0)
    xaxis.SetBehavior(0)
    yaxis.SetBehavior(0)
    chart.RecalculateBounds()

    if metric=='volume':
        yaxis.SetTitle('%s - Volume (mm3)'%struct_name)
    elif metric=='area':
        yaxis.SetTitle('%s - Area (mm2)'%struct_name)
    elif metric=='nfibers':
        yaxis.SetTitle('Number of fibers crossing %s'%struct_name)
    elif metric=='lfibers':
        yaxis.SetTitle('Mean length of fibers crossing %s (mm)'%struct_name)
    elif metric=='fa_fibers':
        yaxis.SetTitle('Mean FA of fibers crossing %s '%struct_name)
    else:
        yaxis.SetTitle('unknown')
    add_correlation()

corr_coefficient=''
reg_line_table=None
reg_line=None
def add_correlation():
    """adapted from mini_scatter_plot"""
    global corr_coefficient, reg_line_table, reg_line
    #print "adding correlation"
    try:
        x, y = zip(*filter(lambda x: np.all(np.isfinite(x)), izip(tab_column, struct_metrics_col)))
    except ValueError:
        return
    if len(x) < 2:
        return

    slope, intercept, r_value, p_value, std_err = linregress(x, y)
    if np.isnan(slope) or np.isnan(intercept):
        corr_coefficient="r=NaN"
        return
    corr_coefficient="r=%.2f" % r_value
    if reg_line is not None:
        chart.RemovePlot(1)
    reg_line = chart.AddPlot(vtk.vtkChart.LINE)
    if reg_line_table is None:
        line_table = vtk.vtkTable()
        arrX = vtk.vtkFloatArray()
        arrX.SetName("X_axis")
        line_table.AddColumn(arrX)
        arrY = vtk.vtkFloatArray()
        arrY.SetName("Y_axis")
        line_table.AddColumn(arrY)
        reg_line_table = line_table
    reg_line_table = reg_line_table
    chart.RecalculateBounds()
    renWin.Render()
    x_axis = chart.GetAxis(1)
    y_axis = chart.GetAxis(0)
    min_x = x_axis.GetMinimum()
    max_x = x_axis.GetMaximum()
    min_y = y_axis.GetMinimum()
    max_y = y_axis.GetMaximum()
    x_axis.SetBehavior(1)
    y_axis.SetBehavior(1)
    min_y_intercept = (min_y - intercept) / slope
    max_y_intercept = (max_y - intercept) / slope
    min_x_intercept = min_x * slope + intercept
    max_x_intercept = max_x * slope + intercept
    interceptions = 0
    reg_line_table.SetNumberOfRows(2)
    if min_y <= min_x_intercept < max_y:
        reg_line_table.SetValue(interceptions, 0, min_x)
        reg_line_table.SetValue(interceptions, 1, min_x_intercept)
        interceptions += 1
    if min_x <= max_y_intercept < max_x:
        reg_line_table.SetValue(interceptions, 0, max_y_intercept)
        reg_line_table.SetValue(interceptions, 1, max_y)
        interceptions += 1
    if min_y < max_x_intercept <= max_y:
        reg_line_table.SetValue(interceptions, 0, max_x)
        reg_line_table.SetValue(interceptions, 1, max_x_intercept)
        interceptions += 1
    if min_x < min_y_intercept <= max_x:
        reg_line_table.SetValue(interceptions, 0, min_y_intercept)
        reg_line_table.SetValue(interceptions, 1, min_y)
        interceptions += 1
    assert (interceptions == 2 )
    reg_line.SetInputData(reg_line_table, 0, 1)
    reg_line.Update()
    refresh_display()
    chart.SetTitle(" r = %.2f "%r_value)
    #print reg_line_table.GetValue(0,0)
    #print reg_line_table.GetValue(0,1)
    #print reg_line_table.GetValue(1,0)
    #print reg_line_table.GetValue(1,1)
#===========GUI=====================


root = tk.Tk()
root.withdraw()
top = tk.Toplevel(root)
top.title('BraViz-tab V.S. struct')

control_frame = tk.Frame(top,width=100,border=1)#,relief='raised')
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
tab_frame.rowconfigure(1, weight=1)
Tabular_label=tk.Label(tab_frame,text='Tabular Data')
Tabular_label.grid(row=0,column=0,sticky='ew',pady=10)

tab_list_frame=tk.LabelFrame(tab_frame,text='Select Variable')


tab_list_and_bar=tk.Frame(tab_list_frame)
tab_list_and_bar.pack(side='top',fill='both',expand=1)
tab_scrollbar=tk.Scrollbar(tab_list_and_bar,orient=tk.VERTICAL)
tab_list=tk.Listbox(tab_list_and_bar,selectmode=tk.BROWSE,yscrollcommand=tab_scrollbar.set,exportselection=0)
tab_scrollbar.config(command=tab_list.yview)
tab_scrollbar.pack(side=tk.RIGHT,fill=tk.Y,expand=1)
tab_list.pack(side="left",fill='both',expand=1)
headers=get_headers()

for h in headers:
    tab_list.insert(tk.END,h)

tab_list.select_set(1,1)

def change_tabular(event=None):
    global tab_column,tab_var_name
    for w in widgets:
        w['state']='disabled'
    var_idx=tab_list.curselection()
    tab_var_name=tab_list.get(var_idx)
    #print tab_var_name
    tab_column=get_column(tab_var_name, True)
    #print tab_column
    refresh_table()
    refresh_display()


tab_list.bind('<<ListboxSelect>>',change_tabular)

tab_list_frame.grid(row=1,column=0,sticky='nsew')
#===========================Structure Metrics=================================
struct_frame.columnconfigure(0, weight=1)
struct_frame.rowconfigure(1, weight=1)
struct_label=tk.Label(struct_frame,text='Structure Metric')
struct_label.grid(row=0,column=0,sticky='ew',pady=3)

metric_buttons=tk.Frame(struct_frame)
metric_buttons.grid(row=1,column=0,sticky='ew',padx=5)

metric_label=tk.Label(metric_buttons,text='Metric:')
long_names_dict={
    'Surface Area' : 'area',
    'Volume' : 'volume',
    'Number of fibers crossing' : 'nfibers',
    'Mean length of fibers crossing': 'lfibers',
    'Mean FA of fibers crossing' : 'fa_fibers',
}
metric_var=tk.StringVar()
metric_select=ttk.Combobox(metric_buttons,textvariable=metric_var)
metric_select['values']=sorted(long_names_dict.keys(),reverse=True)
metric_select['state']='readonly'
metric_var.set('Volume')

#metric_label.grid(row=0,column=0)
metric_select.grid(row=0,column=0,sticky='ew')

select_model_frame=tk.LabelFrame(struct_frame,text='Select Model',padx=1,pady=10)


model_list_and_bar=tk.Frame(select_model_frame)
model_list_and_bar.grid(sticky='nsew')
model_scrollbar=tk.Scrollbar(model_list_and_bar,orient=tk.VERTICAL)
model_list=tk.Listbox(model_list_and_bar,selectmode=tk.BROWSE,yscrollcommand=model_scrollbar.set,exportselection=0)
model_scrollbar.config(command=model_list.yview)
model_scrollbar.pack(side=tk.RIGHT,fill=tk.Y,expand=1)
model_list.pack(side="left",fill='both',expand=1)
models=reader.get('model','093',index='t')

for m in sorted(models):
    model_list.insert(tk.END,m)
for special_fibers in named_fibers:
    model_list.insert(tk.END, "Fibs: "+special_fibers)

model_list.select_set(3,3)
cool_names_dict=cached_get_free_surfer_dict(reader)

def get_tooltip( event=None):
    y_coord = event.y
    index = model_list.nearest(y_coord)
    name = model_list.get(index)
    cool_name = cool_names_dict.get(name, '')
    return "%s : %s " % (name, cool_name)

models_tooltip=ToolTip(model_list,msgFunc=get_tooltip,delay=0.5,follow=True)
model_list.focus()
def check_selection_compatibility(event=None):
    model_idx=model_list.curselection()
    model_name=model_list.get(model_idx)
    if model_name.startswith('Fibs'):
        if metric_var.get() in ['Volume','Area']:
            metric_var.set('Number of fibers crossing')
        metric_select['values'] = ['Number of fibers crossing','Mean length of fibers crossing',
                                   'Mean FA of fibers crossing']
    else:
        metric_select['values'] = sorted(long_names_dict.keys(), reverse=True)
model_list.bind('<<ListboxSelect>>',check_selection_compatibility)

select_model_frame.grid(row=2,column=0,sticky='snew',pady=5)


processing=False
def change_struct(event=None):
    global struct_name,metric,struct_metrics_col,processing,cancel_calculation_flag
    if processing is True:
        cancel_calculation_flag=True
        print "CANCELLING"
        calculate_button['text']='Cancelling...'
        return
    for w in widgets:
        w['state']='disabled'
    get_struct_metrics_col()



#model_list.bind('<<ListboxSelect>>',change_struct)

calculate_frame=tk.Frame(struct_frame)
calculate_button=tk.Button(calculate_frame,text='calculate',command=change_struct)
calculate_button.grid(sticky='ew',pady=5)
progress_bar_var=tk.IntVar()

progress_bar=ttk.Progressbar(calculate_frame,orient='horizontal',length='100',mode='determinate',
                                                                                    variable=progress_bar_var)
progress_bar.grid(sticky='ew',pady=5)
calculate_frame.columnconfigure(0,weight=1)
calculate_frame.grid(sticky='ew',padx=5)
#=====================================================================
renderer_frame = tk.Frame(top)
renderer_frame.grid(row=0,column=1,sticky='ewsn')
top.columnconfigure(1, weight=1)

renWin=vtk.vtkRenderWindow()
render_widget = vtkTkRenderWindowInteractor(renderer_frame,rw=renWin,width=600, height=600)  

iact=render_widget.GetRenderWindow().GetInteractor()                            
view.SetRenderWindow(render_widget.GetRenderWindow())
view.SetInteractor(iact)

renderer_frame.columnconfigure(0, weight=1)
renderer_frame.rowconfigure(0, weight=1)
render_widget.grid(row=0,column=0,sticky='ewsn')

view.GetRenderWindow().SetMultiSamples(0)
iact.Initialize()


view.GetRenderWindow().Render()
iact.Start()

widgets=[tab_list, model_list,metric_select]

def refresh_display():
    view.Update()
    view.GetRenderWindow().Render()
    for w in widgets:
        w['state']='normal'
    metric_select['state']='readonly'
    progress_bar_var.set(100)

def clean_exit():
    global renWin
    print "adios"
    renWin.FastDelete()
    #renWin.Finalize()
    del renWin
    #render_widget.destroy()
    #root.quit()
    #root.destroy()
    quit(0)
top.protocol("WM_DELETE_WINDOW", clean_exit)


#========================VTK INERACTION==================

def listen_and_print(obj,event):
    print
    print event
    print "================"
    #print obj
    print

chart.SetTitle("hola")
title_properties=chart.GetTitleProperties()
title_properties.SetFontSize(14)
title_properties.SetColor(228/255,26/255,28/255)
get_struct_metrics_col()
refresh_table()
refresh_display()

# Start Tkinter event loop
root.mainloop()
