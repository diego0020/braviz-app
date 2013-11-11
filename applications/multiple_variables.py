from __future__ import division
import Tkinter as tk
from Tkinter import Frame as tkFrame
import ttk
from itertools import izip
import os
from functools import partial
from braviz.visualization.create_lut import get_colorbrewer_lut
import numpy as np
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
    vtkTkRenderWindowInteractor

import braviz
from braviz.interaction.tk_gui import hierarchy_dict_to_tree
from braviz.visualization.mathplotlib_charts import BarPlot,ScatterPlot,SpiderPlot
import numpy as np
from braviz.interaction.tk_tooltip import ToolTip
__author__ = 'Diego'


class VariableSelectFrame(tkFrame):
    def __init__(self,parent,**kwargs):
        tkFrame.__init__(self,parent,**kwargs)
        super_tree_frame=tk.Frame(self)
        self.columnconfigure(0,weight=1)
        super_tree=ttk.Treeview(super_tree_frame,show='tree',selectmode='browse')
        super_tree_frame.grid(row=0,sticky='nsew',padx=2,pady=5)
        super_tree_scroll=ttk.Scrollbar(super_tree_frame,orient=tk.VERTICAL,command=super_tree.yview)
        super_tree['yscrollcommand']=super_tree_scroll.set
        super_tree.grid(row=0,column=0,sticky='nsew')
        super_tree_scroll.grid(row=0,column=1,sticky='sn')
        super_tree_frame.rowconfigure(0,weight=1)
        super_tree_frame.columnconfigure(0,weight=1)

        self.rowconfigure(0,weight=1)
        self.rowconfigure(5,weight=0)

        metric_select_frame=tk.Frame(self)
        metric_label=tk.Label(metric_select_frame,text='Metric: ')
        metric_selection_var=tk.StringVar()
        metric_selection_var.set('None')
        metric_select_box=ttk.Combobox(metric_select_frame,width=10,textvariable=metric_selection_var)
        metric_label.grid(row=0,column=0,sticky='w')
        metric_select_box.grid(row=0,column=1,sticky='ew')
        metric_select_frame.columnconfigure(1,weight=1)

        metric_select_frame.grid(row=1,column=0,sticky='ew',padx=2,pady=2)

        add_to_selection_button=tk.Button(self,text="Add to selection")
        add_to_selection_button.grid(row=2,sticky='ew',padx=2,pady=2)

        selected_variables_list=tk.Listbox(self,height=10,exportselection=0)
        selected_variables_list.grid(row=5,sticky='nsew',padx=2,pady=5)

        bottom_buttons_frame=tk.Frame(self)
        bottom_buttons_frame.grid(row=6,sticky='ew',pady=5,padx=2)

        remove_from_selection_button=tk.Button(bottom_buttons_frame,text='Remove')
        clear_selection_button=tk.Button(bottom_buttons_frame,text='Clear')
        apply_selection_button=tk.Button(bottom_buttons_frame,text='Apply Selection')
        progress=tk.IntVar()
        progress.set(100)
        progress_bar=ttk.Progressbar(bottom_buttons_frame,orient='horizontal',length='100',mode='determinate',
                                     variable=progress)
        clear_selection_button.grid(row=0,column=0,sticky='ew')
        remove_from_selection_button.grid(row=0,column=1,sticky='ew')
        apply_selection_button.grid(row=1,column=0,columnspan=2,sticky='ew')
        progress_bar.grid(row=2,column=0,columnspan=2,sticky='ew')
        bottom_buttons_frame.columnconfigure(0,weight=1)
        bottom_buttons_frame.columnconfigure(1,weight=1)

        self.__super_tree = super_tree
        self.__fill_super_tree()

        self.__add_to_selection_button=add_to_selection_button
        self.__metric_select_box=metric_select_box
        self.__metric_selection_var=metric_selection_var
        self.__selected_variables_list=selected_variables_list
        self.__clear_selection_button=clear_selection_button
        self.__remove_from_selection_button=remove_from_selection_button
        self.__apply_selection_button=apply_selection_button
        self.__progress=progress
        self.__add_observers()
        #public access to tree_view
        self.tree_view=super_tree

    def __fill_super_tree(self):
        super_tree=self.__super_tree
        #BRAINT
        from braviz.readAndFilter.link_with_rdf import get_braint_hierarchy
        braint = get_braint_hierarchy()
        super_tree.insert('', tk.END, 'braint', text='Braint')
        hierarchy_dict_to_tree(super_tree, braint, 'braint', tags=['braint'])
        #TMS
        from braviz.interaction.tms_variables import hierarchy_dnd as tms_hierarchy
        super_tree.insert('', tk.END, 'tms', text='TMS')
        hierarchy_dict_to_tree(super_tree, tms_hierarchy, 'tms', tags=['tms'])

        #ANATOMY
        from braviz.interaction.structural_hierarchy import get_structural_hierarchy
        super_tree.insert('', tk.END, 'structural', text='Structural')
        anatomy_hierarchy = get_structural_hierarchy(reader, '144')
        hierarchy_dict_to_tree(super_tree, anatomy_hierarchy, 'structural', tags=['struct'])
    def __add_observers(self):
        add_to_selection_button=self.__add_to_selection_button
        add_to_selection_button['state'] = 'disabled'
        metric_select_box=self.__metric_select_box
        metric_select_box['state'] = 'disabled'
        valid_metrics = {
            'fibers': ("Number", "Mean FA", "Mean Length"),
            'multiple': ('Volume', 'Fibers Crossing', 'Mean FA of Fibers Crossing','Mean Length of Fibers Crossing'),
            'leaf_struct': ('Volume', 'Surface Area', 'Fibers Crossing',
                            'Mean FA of Fibers Crossing','Mean Length of Fibers Crossing')
        }

        def toggle_add_button(event=None):
            super_tree=self.__super_tree
            selection = super_tree.selection()
            selection_tags = super_tree.item(selection)['tags']
            if 'struct' in selection_tags:
                if selection[0].startswith('structural:Fibers'):
                    if 'parent' in selection_tags:
                        metric_select_box['state'] = 'disabled'
                        add_to_selection_button['state'] = 'disabled'
                        return
                    else:
                        metrics = valid_metrics['fibers']
                elif 'parent' in selection_tags:
                    metrics = valid_metrics['multiple']
                else:
                    metrics = valid_metrics['leaf_struct']
                metric_select_box['values'] = metrics
                metric_select_box['state'] = 'readonly'
                metric_selection_var=self.__metric_selection_var
                if metric_selection_var.get() not in metrics:
                    metric_selection_var.set(metrics[0])
                add_to_selection_button['state'] = 'normal'
                return
            else:
                metric_select_box['state'] = 'disabled'
            if 'leaf' in selection_tags:
                add_to_selection_button['state'] = 'normal'
            else:
                add_to_selection_button['state'] = 'disabled'

        self.__super_tree.bind('<<TreeviewSelect>>', toggle_add_button)


        def add_variable(event=None):
            super_tree=self.__super_tree
            metric_selection_var=self.__metric_selection_var

            tree_variable = super_tree.selection()[0]
            if tree_variable.startswith('structural'):
                tree_variable = ':'.join((metric_selection_var.get(), tree_variable[11:]))
            selected_variables_list=self.__selected_variables_list
            selected_variables_list.insert(tk.END, tree_variable)

        add_to_selection_button['command'] = add_variable


        def clear_variables(event=None):
            selected_variables_list = self.__selected_variables_list
            selected_variables_list.delete(0, tk.END)

        clear_selection_button=self.__clear_selection_button
        clear_selection_button['command'] = clear_variables


        def remove_variable(event=None):
            selected_variables_list=self.__selected_variables_list
            index = selected_variables_list.curselection()
            if len(index) > 0:
                selected_variables_list.delete(index)

        remove_from_selection_button=self.__remove_from_selection_button
        remove_from_selection_button['command'] = remove_variable
    def get_selected_variables(self):
        return self.__selected_variables_list.get(0,tk.END)
    def set_apply_callback(self,callback):
        def callback2(event=None):
            callback(self.get_selected_variables())
        self.__apply_selection_button['command']=callback2
    def set_progress(self,prog):
        self.__progress.set(prog)


class VtkWidget(tkFrame):
    def __init__(self,reader,parent,**kwargs):

        tkFrame.__init__(self, parent, **kwargs)
        self.ren=vtk.vtkRenderer()
        self.renWin=vtk.vtkRenderWindow()

        self.renWin.AddRenderer(self.ren)
        self.ren.SetBackground2(170/255,204/255,245/255)
        self.ren.SetBackground(107/255,150/255,299/255)
        self.ren.SetGradientBackground(1)
        render_widget = vtkTkRenderWindowInteractor(self,rw=self.renWin)
        render_widget.pack(fill='both', expand='true')

        sphere_source=vtk.vtkSphereSource()
        sphere_mapper=vtk.vtkPolyDataMapper()
        sphere_actor=vtk.vtkActor()
        self.ren.AddActor(sphere_actor)
        sphere_actor.SetMapper(sphere_mapper)
        sphere_mapper.SetInputConnection(sphere_source.GetOutputPort())

        self.iren=render_widget.GetRenderWindow().GetInteractor()
        self.iren.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.iren.SetRenderWindow(self.renWin)
        self.ren.Render()
        self.renWin.Initialize()
        self.iren.Initialize()
        self.picker = vtk.vtkCellPicker()
        self.picker.SetTolerance(0.005)
        cam1 = self.ren.GetActiveCamera()
        self.ren.ResetCamera()
        #cam1.Elevation(80)
        #cam1.Azimuth(80)
        #cam1.SetViewUp(0, 0, 1)
        self.pd_actors=[]

        self.renWin.Render()


class GraphFrame(tkFrame):
    def __init__(self,ubica_dict,parent,**kwargs):
        tkFrame.__init__(self,parent,**kwargs)
        self.__ubica_dict=ubica_dict
        self.__bar_chart=None
        self.__scatter_plot=None
        self.__widget=None
        self.__spider_plot=None
        self.__active_plot=None
        self.__color_fun=lambda x,y:(1,0,1)
        init_panel=tk.Frame(self,relief='ridge',border=2,height=kwargs.get('height',200),width=kwargs.get('width',600),)

        init_label=tk.Label(init_panel,text='Select some data to start')
        init_panel.pack_propagate(0)
        init_label.pack(fill='both',expand=True)

        init_panel.grid(row=0,column=0,sticky='NSEW',padx=2,pady=2)
        self.rowconfigure(0,weight=1)
        self.columnconfigure(0,weight=1)
        self.__widget=init_panel
        self.tool_tip=ToolTip(init_label,msgFunc=self.get_subject_message,follow=1,delay=0.5)
    def set_color_function(self,color_func):
        """Function must take val,code pairs and return a color"""
        self.__color_fun=color_func


    def update_representation(self,data):
        #print data
        if len(data)==0:
            return
        if self.__widget is not None:
            self.__widget.grid_forget()
            self.__widget=None
        if len(data)==1:
            self.draw_bar_chart(data)
            self.__active_plot =self.__bar_chart
        elif len(data)==2:
            self.draw_scatter(data)
            self.__active_plot = self.__scatter_plot
        else:
            self.draw_spiders(data)
            self.__active_plot = self.__spider_plot
        del self.tool_tip
        self.tool_tip = ToolTip(self.__widget, msgFunc=self.get_subject_message, follow=1, delay=0.5)
    def draw_bar_chart(self,data):
        y_label, data_dict = data.popitem()
        good_data = dict(( (k, v) for k, v in data_dict.iteritems() if np.isfinite(v)))
        term_data = [v for k, v in good_data.iteritems() if self.__ubica_dict[k] == '3']
        term_mean = np.mean(term_data)
        term_std = np.std(term_data)
        if self.__bar_chart is None:
            bar_plot = BarPlot(tight=True)
            self.__bar_chart=bar_plot
        else:
            bar_plot = self.__bar_chart
        bar_widget = bar_plot.get_widget(self, height=200, width=600)
        bar_widget.grid(row=0, column=0, sticky='NSEW')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        good_min = np.min(good_data.values())
        good_max = np.max(good_data.values())
        bar_plot.set_y_limits(good_min, good_max)
        bar_plot.set_lines([term_mean - term_std, term_mean, term_mean + term_std], (True, False, True))
        bar_plot.set_y_title(y_label)
        data_tuples = good_data.items()
        data_tuples.sort(key=lambda x: self.__ubica_dict[x[0]])

        bar_plot.set_color_fun(self.__color_fun,code_and_val=True)
        codes, datums = zip(*data_tuples)
        bar_plot.set_data(datums, codes)
        group_stats = self.get_group_stats(good_data)
        means, stds, ns = group_stats

        bar_plot.set_back_bars(back_bars=zip(means, ns), back_error=stds,back_codes=("1","2","3"))
        bar_plot.paint_bar_chart()
        self.__widget=bar_widget
    def draw_scatter(self,data_dict):
        good_data_dict=self.filter_dict(data_dict)
        if self.__scatter_plot is None:
            self.__scatter_plot=ScatterPlot(tight=True)
        scatter=self.__scatter_plot
        scatter_widget=scatter.get_widget(self,height=200, width=600)
        scatter_widget.grid(row=0,column=0,sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.__widget=scatter_widget
        x_label,x_data_dict=good_data_dict.popitem()
        y_label,y_data_dict=good_data_dict.popitem()
        codes=x_data_dict.keys()
        x_data=[x_data_dict[k] for k in codes]
        y_data=[y_data_dict[k] for k in codes]
        x_min=np.min(x_data)
        x_max=np.max(x_data)
        x_extent=x_max-x_min
        y_min=np.min(y_data)
        y_max=np.max(y_data)
        y_extent=y_max-y_min
        scatter.set_limits((x_min-x_extent/10,x_max+x_extent/10),
                           (y_min - y_extent / 10, y_max + y_extent / 10))
        scatter.set_labels(x_label,y_label)
        scatter.set_data(x_data,y_data,codes)
        scatter.set_color_function(self.__color_fun)
        scatter.set_groups(self.__ubica_dict)
        #print zip(x_data,y_data)
        scatter.draw_scatter()
        self.__widget = scatter_widget
    def draw_spiders(self,data_dict):
        good_data_dict = self.filter_dict(data_dict)
        if self.__spider_plot is None:
            self.__spider_plot=SpiderPlot()
        spider=self.__spider_plot
        spider_widget=spider.get_widget(self,height=200, width=600)
        spider_widget.grid(row=0, column=0, sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.__widget=spider_widget

        norm_data=self.normalize_variables(good_data_dict)
        spider_dict={}
        variables=norm_data.keys()
        codes=norm_data[variables[0]].keys()
        for cd in codes:
            spider_dict[cd]=[norm_data[v][cd] for v in variables]
        spider.set_data(spider_dict,range(len(variables)))
        spider.set_groups(self.__ubica_dict)
        spider.set_rmax(1)
        spider.set_color_fun(self.__color_fun)
        spider.draw_spider()
        self.__widget = spider_widget

    def normalize_variables(self,data_frame):
        for key,data_dict in data_frame.iteritems():
            keys,values=zip(*data_dict.items())
            minimum=np.min(values)
            maximum=np.max(values)
            width=maximum-minimum
            if width<0.001:
                width=1
            norm_values=map(lambda x:(x-minimum)/width,values)
            data_dict.update(izip(keys,norm_values))
        return data_frame

    def get_group_stats(self,data_dict):
        group_values_dict = {}
        for cd,value in data_dict.iteritems():
            group = self.__ubica_dict[cd]
            if np.isfinite(value):
                group_values_dict.setdefault(group, []).append(value)
        results = []
        for g in ['1', '2', '3']: # 1=canguro, 2=control, 3=gorditos
            values = group_values_dict[g]
            n=len(values)
            if len(values) > 0:
                mean = np.mean(values)
                std = np.std(values)
            else:
                mean = 0
                std = 0
            results.append((mean, std,n))
        return zip(*results)

    @staticmethod
    def filter_dict(data,get_subj_dict=False):
        """ Removes all ids which contain nan values"""
        from collections import defaultdict
        subjects_dir=defaultdict(dict)
        for col,col_data in data.iteritems():
            for subj,value in col_data.iteritems():
                subjects_dir[subj][col]=col_data.get(subj,float('nan'))
        for subj,data_dict in subjects_dir.items():
            if not np.all(np.isfinite(data_dict.values())):
                subjects_dir.pop(subj)
        out_data={}
        for col in data.iterkeys():
            out_data[col]=dict( (k,values[col]) for k,values in subjects_dir.iteritems())
        return out_data
    def update_popups_messages(self):
        pass
    def get_subject_message(self,event=None):
        if self.__active_plot is not None:
            hover_item=self.__active_plot.get_current_name()
        else:
            return 'Select some data and click "Apply Selection"'
        return "hola: %s"%hover_item
    def resize_bars(self):
        if self.__bar_chart is not None:
            #self.__bar_chart.figure.subplots_adjust(top=100,bottom=0)
            #self.__bar_chart.figure.subplots_adjust(bottom=0,top=1)
            self.__bar_chart.show()


class DataFetcher():
    def __init__(self,reader,tree_view=None,codes=None):
        self.__reader=reader
        self.__tree_view=tree_view
        self.__codes=codes
    def get_data(self,data_variables):
        #decode
        data_dict={}
        for col in data_variables:
            #print col
            if col.startswith('braint'):
                out_data= self.get_braint_data_col(col)
            elif col.startswith('tms'):
                out_data = self.get_tms_data_col(col)
            else:
                out_data = self.get_structural_data_col(col)
            data_dict[col] = out_data
        return data_dict
    def get_tms_data_col(self,col):
        from braviz.interaction.tms_variables import data_codes_dict
        from braviz.readAndFilter.read_csv import get_column
        tms_csv_file=os.path.join(self.__reader.getDataRoot(), 'baseFinal_TMS.csv')
        tokens=col.split(':')
        hemisphere=tokens[-1]
        if hemisphere=='Dominant':
            h='d'
        else:
            h='nd'
        decoded_col = tokens[-2]
        decoded_col=decoded_col.replace('_',' ')
        decoded_col=data_codes_dict[decoded_col]
        data_col=get_column(tms_csv_file,decoded_col+h,numeric=True)
        codes_col=get_column(tms_csv_file,'CODE',numeric=False)
        data_dict=dict(izip(codes_col,data_col))
        return data_dict
    def set_codes(self,codes):
        self.__codes=codes
    def get_codes(self):
        from braviz.readAndFilter.read_csv import get_column
        if self.__codes is not None:
            return self.__codes
        else:
            tms_csv_file = os.path.join(self.__reader.getDataRoot(), 'baseFinal_TMS.csv')
            codes_col = get_column(tms_csv_file, 'CODE', numeric=False)
            return codes_col
    def get_ubica_dict(self):
        from braviz.readAndFilter.read_csv import get_column
        tms_csv_file = os.path.join(self.__reader.getDataRoot(), 'baseFinal_TMS.csv')
        codes_col = get_column(tms_csv_file, 'CODE', numeric=False)
        ubica_col = get_column(tms_csv_file, 'UBICA', numeric=False)
        return dict(izip(codes_col,ubica_col))

    def get_structural_data_col(self,col):
        from braviz.interaction.structure_metrics import get_mult_struct_metric,cached_get_struct_metric_col
        #decode
        metrics_dict={
            'Volume':'volume',
            'Surface Area':'area',
            'Fibers Crossing':'nfibers',
            'Mean FA':'fa_fibers',
            'Mean FA of Fibers Crossing':'fa_fibers',
            'Number':'nfibers',
            'Mean Length':'lfibers',
            'Mean Length of Fibers Crossing':'lfibers',
        }
        #print col
        tokens=col.split(':')
        metric=metrics_dict[tokens[0]]

        id_in_tree='structural:'+':'.join(tokens[1:])
        selection_tags = self.__tree_view.item(id_in_tree)['tags']
        children=self.__tree_view.get_children(id_in_tree)

        #print children
        if len(children) == 0:
            children=(col,)

        def test_for_leaf(kid):
            tokens=kid.split(':')
            id_in_tree = 'structural:' + ':'.join(tokens[1:])
            return len(self.__tree_view.get_children(id_in_tree))==0
        children2=filter(test_for_leaf,children)
        names=[]
        for kid in children2:
            tokens2 = kid.split(':')
            name=self.__reconstruct_struct_name(tokens2)
            names.append(name)
        codes = self.get_codes()
        metric_func=partial(get_mult_struct_metric,self.__reader,names,metric=metric)
        #data_col=map(metric_func,codes)
        data_col=cached_get_struct_metric_col(self.__reader,codes,names,metric)
        result_dict=dict(izip(codes,data_col))
        return result_dict





    def __reconstruct_struct_name(self,tokens):
        structure_type = tokens[1]
        if structure_type == 'Fibers':
            name = 'Fibs:' + tokens[2]
        elif structure_type == 'Base':
            name = tokens[2]
        elif structure_type[0] == 'C':
            #Corpus Callosum
            name = 'CC_' + tokens[2]
        else:
            #cortex
            if tokens[-1][0] == 'G':
                #gray matter
                matter = 'ctx'
            else:
                #white matter
                matter = 'wm'
            if structure_type[0] == 'L':
                h = 'lh'
            else:
                h = 'rh'
            pname = tokens[-2]
            full_name = '-'.join([matter, h, pname])
            name = full_name
        return name

    def get_braint_data_col(self):
        print "Not yet implemented"

if __name__=="__main__":
    root=tk.Tk()
    root.focus()
    root.title('Braviz-Multiple Variables')

    reader=braviz.readAndFilter.kmc40AutoReader()

    panned_window=ttk.PanedWindow(root,orient=tk.HORIZONTAL)
    panned_window.grid(sticky='nsew')
    root.columnconfigure(0,weight=1)
    root.rowconfigure(0,weight=1)

    variable_select_frame=VariableSelectFrame(panned_window,height=600,width=200)
    display_frame=tk.Frame(panned_window,height=600,width=600,bg='black')
    panned_window.add(variable_select_frame)
    panned_window.add(display_frame)

    #vtk_frame=tk.Frame(display_frame,bg='green',height=400,width=600)
    #graph_frame=tk.Frame(display_frame,bg='blue',height=200,width=600)

    fetcher=DataFetcher(reader,variable_select_frame.tree_view)
    groups_dict=fetcher.get_ubica_dict()
    groups_colors={
        "1": 'r',
        "2": 'g',
        "3": 'b',
    }
    def group_color_fun(val,key):
        col=groups_colors.get(key,None)
        if col is None:
            col=groups_colors[groups_dict[key]]
        return col

    graph_frame=GraphFrame(groups_dict,display_frame,height=200,width=600)
    graph_frame.set_color_function(group_color_fun)
    vtk_frame=VtkWidget(reader,display_frame,height=400,width=600)

    vtk_frame.grid(row=0,column=0,sticky='nsew')
    graph_frame.grid(row=1,column=0,sticky='nsew')

    display_frame.rowconfigure(0,weight=1)
    display_frame.rowconfigure(1,weight=1)
    display_frame.columnconfigure(0,weight=1)

    #variable_select_frame.set_apply_callback(graph_frame.update_representation)

    def update_all(new_data_vars):
        new_data=fetcher.get_data(new_data_vars)
        #print new_data
        graph_frame.update_representation(new_data)
    #variable_select_frame.set_apply_callback(fetcher.get_data)
    variable_select_frame.set_apply_callback(update_all)

    aux_button=tk.Button(variable_select_frame,text="aux")
    aux_button.grid(sticky='ew')
    def bars_resize(event=None):
        graph_frame.resize_bars()
    aux_button['command']=bars_resize

    tk.mainloop()


