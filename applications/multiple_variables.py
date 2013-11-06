from __future__ import division
import Tkinter as tk
from Tkinter import Frame as tkFrame
import ttk
import vtk
from vtk.tk.vtkTkRenderWindowInteractor import \
    vtkTkRenderWindowInteractor
import braviz
from braviz.interaction.tk_gui import hierarchy_dict_to_tree
from braviz.readAndFilter.link_with_rdf import get_braint_hierarchy
from braviz.interaction.tms_variables import hierarchy as tms_hierarchy
from braviz.interaction.structural_hierarchy import get_structural_hierarchy
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
        clear_selection_button.grid(row=0,column=0,sticky='ew')
        remove_from_selection_button.grid(row=0,column=1,sticky='ew')
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
        self.__add_observers()

    def __fill_super_tree(self):
        super_tree=self.__super_tree
        #BRAINT
        braint = get_braint_hierarchy()
        super_tree.insert('', tk.END, 'braint', text='Braint')
        hierarchy_dict_to_tree(super_tree, braint, 'braint', tags=['braint'])
        #TMS
        super_tree.insert('', tk.END, 'tms', text='TMS')
        hierarchy_dict_to_tree(super_tree, tms_hierarchy, 'tms', tags=['tms'])

        #ANATOMY
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
            'multiple': ('Volume', 'Fibers Crossing', 'Mean FA of Fibers Crossing'),
            'leaf_struct': ('Volume', 'Surface Area', 'Fibers Crossing', 'Mean FA of Fibers Crossing')
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

class vtk_widget(tkFrame):
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
        cam1.Elevation(80)
        cam1.Azimuth(80)
        cam1.SetViewUp(0, 0, 1)
        self.pd_actors=[]

        self.renWin.Render()


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
    graph_frame=tk.Frame(display_frame,bg='blue',height=200,width=600)
    vtk_frame=vtk_widget(reader,display_frame,height=400,width=600)

    vtk_frame.grid(row=0,column=0,sticky='nsew')
    graph_frame.grid(row=1,column=0,sticky='nsew')

    display_frame.rowconfigure(0,weight=1)
    display_frame.rowconfigure(1,weight=1)
    display_frame.columnconfigure(0,weight=1)

    tk.mainloop()


