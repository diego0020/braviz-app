##############################################################################
#    Braviz, Brain Data interactive visualization                            #
#    Copyright (C) 2014  Diego Angulo                                        #
#                                                                            #
#    This program is free software: you can redistribute it and/or modify    #
#    it under the terms of the GNU Lesser General Public License as          #
#    published by  the Free Software Foundation, either version 3 of the     #
#    License, or (at your option) any later version.                         #
#                                                                            #
#    This program is distributed in the hope that it will be useful,         #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of          #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the           #
#    GNU Lesser General Public License for more details.                     #
#                                                                            #
#    You should have received a copy of the GNU Lesser General Public License#
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.   #
##############################################################################


from __future__ import division, print_function
import Tkinter as tk
import functools
import ttk
from os.path import join as path_join
import thread

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
import numpy as np

from braviz.readAndFilter.read_csv import get_headers, get_tuples_dict
from braviz.visualization.create_lut import get_colorbrewer_lut
import braviz


if __name__ == "__main__":
    #============globals=======================
    __author__ = 'Diego'
    root = tk.Tk()
    root.withdraw()
    reader = braviz.readAndFilter.BravizAutoReader()
    data_root = reader.get_data_root()
    file_name = path_join(data_root, 'test_small.csv')
    id_list = reader.get('ids')
    models_set = set()
    fibers_var = tk.BooleanVar()
    fibers_op_var = tk.StringVar()
    color_column = None
    color_data_dict = {}
    sort_data_dict = {}
    sort_column = None
    overlay_view = False
    messages_dict = {}

    widgets = []
    models_dict = {}
    async_processing_models = False

    removed_items = 0

    #============end-globals=====================

    def load_models(event=None):
        global async_processing_models
        # disable buttons
        for w in widgets:
            w.config(state='disabled')
        async_processing_models = True
        progress.set(0)
        # async_load_models()
        thread.start_new_thread(
            async_load_models, (fibers_var.get(), hide_waypoints_var.get()))
        top.after(20, finish_load_models)
        # finish_load_models()

    def finish_load_models():
        global models_dict, async_processing_models
        if async_processing_models is False:
            grid_view.set_data(models_dict)
            grid_view.Render()
            for w in widgets:
                w.config(state='normal')
            add_fibers_operation['state'] = 'readonly'
            set_hide_waypoints_state()
            update_balloons()
        else:
            top.after(20, finish_load_models)
        progress.set(len(models_dict) / len(id_list) * 100)
    #-------------------------

    def async_load_models(fibers_var_bool, hide_waypoints_bar_bool):
        global models_dict, async_processing_models
        models_dict.clear()
        for i, subj in enumerate(id_list):
            models = []
            if not (fibers_var_bool and hide_waypoints_bar_bool):
                for model_name in models_set:
                    try:
                        models.append(
                            reader.get('model', subj, name=model_name))
                    except Exception:
                        pass
            # load fibers
            if fibers_var_bool is True:
                if fibers_op_var.get() == 'through any':
                    operation = 'or'
                else:
                    operation = 'and'
                try:
                    fibers = reader.get(
                        'fibers', subj, waypoint=list(models_set), operation=operation)
                except Exception:
                    pass
                else:
                    models.append(fibers)
            # append
            append_filter = vtk.vtkAppendPolyData()
            for mod in models:
                append_filter.AddInputData(mod)
            append_filter.Update()
            models_dict[subj] = append_filter.GetOutput()
        async_processing_models = False

    def get_data_dict(col_name, nan_value=float('nan')):
        return get_tuples_dict(file_name, 'code', col_name, numeric=True, nan_value=nan_value)

    def sort_models(overlay=False):
        global overlay_view, sort_data_dict, sort_column

        col_idx = tab_list.curselection()
        sort_column = tab_list.get(col_idx)
        sort_data_dict = get_data_dict(sort_column, nan_value=float('+inf'))
        if overlay is False:
            sorted_subjects = id_list[:]
            sorted_subjects.sort(
                key=lambda x: sort_data_dict.get(x, float('+inf')))
        else:
            group_dict = {}
            for id_item in id_list:
                key = sort_data_dict.get(id_item, 'nan')
                group_dict.setdefault(key, []).append(id_item)
            sorted_subjects = group_dict.values()
        grid_view.sort(sorted_subjects, overlay=overlay)
        if overlay_view != overlay:
            overlay_view = overlay
        color_models(new_variable=False)
        overlay_view = overlay
        grid_view.reset_camera()
        update_balloons()
        grid_view.set_sort_message_visibility(True)
        grid_view.update_sort_message(sort_column)
        grid_view.Render()

    def color_models(new_variable=True):
        global color_data_dict, color_column
        if new_variable is True:
            col_idx = tab_list.curselection()
            color_column = tab_list.get(col_idx)
            color_data_dict = get_data_dict(color_column)
        min_value = min(color_data_dict.values())
        max_value = max(color_data_dict.values())
        color_table = get_colorbrewer_lut(
            min_value, max_value, scheme='RdBu', steps=9, nan_color=(0.95, 0.47, 0.85))

        def color_fun(s):
            x = color_data_dict.get(s, float('nan'))
            return color_table.GetColor(x)
        opacity = 1.0
        if overlay_view is True:
            opacity = 0.1
        grid_view.set_color_function(color_fun, opacity=opacity)
        grid_view.set_color_bar_visibility(True)
        grid_view.update_color_bar(color_table, color_column)
        update_balloons()
        grid_view.Render()

    def update_balloons():
        global messages_dict
        messages_dict = {}
        for subj in id_list:
            message = "%s\n%s : %.2f\n%s : %.2f" % (subj,
                                                    color_column, color_data_dict.get(
                                                        subj, float('nan')),
                                                    sort_column, sort_data_dict.get(subj, float('nan')))
            messages_dict[subj] = message
        grid_view.set_balloon_messages(messages_dict)
        data_dict = {}
        for s in id_list:
            color_datum = color_data_dict.get(s, float('nan'))
            sort_datum = sort_data_dict.get(s, float('nan'))
            if np.isfinite(color_datum) and np.isfinite(sort_datum):
                data_dict[s] = (color_datum, sort_datum)
        if len(data_dict) > 0 and scatter_sel_var.get():
            grid_view.set_mini_scatter_visible(True)
            grid_view.update_mini_scatter(data_dict, color_column, sort_column)
        else:
            grid_view.set_mini_scatter_visible(False)
        show_labels()
        grid_view.Render()
    #===========GUI=====================

    top = tk.Toplevel(root)
    top.title('BraViz-grid view')

    control_frame = tk.Frame(top, width=100, border=1)
    control_frame.grid(row=0, column=0, sticky='nsew')
    top.columnconfigure(0, minsize=100)
    top.rowconfigure(0, weight=1)

    tab_frame = tk.Frame(control_frame)
    sep = ttk.Separator(control_frame, orient=tk.HORIZONTAL)
    struct_frame = tk.Frame(control_frame)

    tab_frame.grid(column=0, row=0, sticky='nsew')
    sep.grid(column=0, row=1, sticky='ew')

    control_frame.rowconfigure(0, weight=1)
    control_frame.rowconfigure(2, weight=1)
    control_frame.columnconfigure(0, weight=1, minsize=120)
    struct_frame.grid(column=0, row=2, sticky='snew')

    #===========================Tabular================================
    tab_frame.columnconfigure(0, weight=1)
    tab_frame.rowconfigure(2, weight=1)
    Tabular_label = tk.Label(tab_frame, text='Tabular Data')
    Tabular_label.grid(row=0, column=0, sticky='ew', pady=10)

    tab_operation_frame = tk.Frame(tab_frame)
    group_button = tk.Button(
        tab_operation_frame, text='Group by', command=functools.partial(sort_models, overlay=True))
    sort_button = tk.Button(
        tab_operation_frame, text='Sort by', command=sort_models)
    color_button = tk.Button(
        tab_operation_frame, text='Color by', command=color_models)

    group_button.grid(row=0, column=1, sticky='ew')
    sort_button.grid(row=0, column=0, sticky='ew')
    color_button.grid(row=0, column=2, sticky='ew')
    tab_operation_frame.columnconfigure(0, weight=1)
    tab_operation_frame.columnconfigure(1, weight=1)
    tab_operation_frame.grid(row=1, sticky='ew')

    tab_list_frame = tk.LabelFrame(tab_frame, text='Select Variable')

    tab_list_and_bar = tk.Frame(tab_list_frame)
    tab_list_and_bar.pack(side='top', fill='both', expand=1)
    tab_scrollbar = tk.Scrollbar(tab_list_and_bar, orient=tk.VERTICAL)
    tab_list = tk.Listbox(tab_list_and_bar, selectmode=tk.BROWSE,
                          yscrollcommand=tab_scrollbar.set, exportselection=0)
    tab_scrollbar.config(command=tab_list.yview)
    tab_scrollbar.pack(side=tk.RIGHT, fill=tk.Y, expand=1)
    tab_list.pack(side="left", fill='both', expand=1)
    headers = get_headers(file_name)
    # headers=['babd','abfdb','sadf']

    for h in headers:
        tab_list.insert(tk.END, h)

    tab_list.select_set(10, 10)

    tab_list_frame.grid(row=2, column=0, sticky='nsew')

    #===========================Structure Metrics=============================
    struct_frame.columnconfigure(0, weight=1)
    struct_frame.rowconfigure(1, weight=1)
    struct_label = tk.Label(struct_frame, text='Structures')
    struct_label.grid(row=0, column=0, sticky='ew', pady=5)

    def change_models(action, model_name):
        if action == 'add':
            models_set.add(model_name)
        else:
            models_set.remove(model_name)

    select_model_frame = braviz.interaction.structureList(
        reader, '144', change_models, struct_frame)
    select_model_frame.grid(row=1, column=0, sticky='snew', pady=5)

    def set_hide_waypoints_state(event=None):
        if fibers_var.get() is True:
            hide_waypoints_check.config(state='normal')
        else:
            hide_waypoints_check.config(state='disabled')
    fibers_frame = tk.Frame(struct_frame)
    add_fibers_check = tk.Checkbutton(
        fibers_frame, text='add fibers', variable=fibers_var, command=set_hide_waypoints_state)
    add_fibers_check.grid(row=0, column=0, sticky='w')
    fibers_op_var.set('through any')
    add_fibers_operation = ttk.Combobox(
        fibers_frame, textvariable=fibers_op_var, state='readonly', width=10)
    add_fibers_operation['values'] = ('through all', 'through any')
    add_fibers_operation.grid(row=0, column=1, sticky='e')
    hide_waypoints_var = tk.BooleanVar()
    hide_waypoints_var.set(0)
    hide_waypoints_check = tk.Checkbutton(
        fibers_frame, variable=hide_waypoints_var, text='hide waypoints', state='disabled')
    hide_waypoints_check.grid(row=1, column=0, columnspan=2, sticky='w')
    fibers_frame.grid(sticky='ew')

    apply_model_selection_button = tk.Button(
        struct_frame, text='Apply model selection', command=load_models)
    apply_model_selection_button.grid(sticky='ew')

    progress = tk.IntVar()
    progress.set(0)

    progress_bar = ttk.Progressbar(
        struct_frame, orient='horizontal', length='100', mode='determinate', variable=progress)
    progress_bar.grid(sticky='ew', pady=5, padx=5)

    #---------------------------------------------
    grid_manip_frame = tk.Frame(control_frame)

    scatter_sel_var = tk.BooleanVar()
    scatter_sel_var.set(1)

    def show_scatter_plot(event=None):
        grid_view.set_mini_scatter_visible(scatter_sel_var.get())

    scatter_sel_box = tk.Checkbutton(grid_manip_frame, text='Show scatter plot', variable=scatter_sel_var,
                                     command=show_scatter_plot)
    scatter_sel_box.grid(sticky='w')

    labels_sel_var = tk.BooleanVar()
    labels_sel_var.set(0)

    def show_labels(event=None):
        if event is not None:
            update_balloons()
        else:
            if labels_sel_var.get():
                if overlay_view is True:
                    group_message_dict = get_group_message_dict()
                    grid_view.add_labels(group_message_dict)
                else:
                    grid_view.add_labels(messages_dict)
            else:
                grid_view.remove_labels()

    def get_group_message_dict():
        working_dict = {}
        group_repr_dict = {}
        for subj in id_list:
            group = sort_data_dict[subj]
            color_val = color_data_dict[subj]
            data_list = working_dict.setdefault(group, [])
            group_repr_dict.setdefault(group, subj)
            if np.isfinite(color_val):
                data_list.append(color_val)
        for group, val_list in working_dict.iteritems():
            working_dict[group] = np.mean(val_list)
        group_message_dict = {}
        for group, group_repr in group_repr_dict.iteritems():
            group_message_dict[group_repr] = "Group %s\nMean %s: %.2f" % (
                group, color_column, working_dict[group])
        return group_message_dict

    labels_sel_box = tk.Checkbutton(
        grid_manip_frame, text='Show text labels', variable=labels_sel_var, command=show_labels)
    labels_sel_box.grid(sticky='w')

    def remove_id(event=None):
        global removed_items
        id_to_remove = grid_view.get_selection()
        if id_to_remove is not None:
            id_list.remove(id_to_remove)
            removed_items += 1
            if removed_items >= 1:
                removed_reminder.SetInput("%d" % removed_items)
                removed_reminder.SetVisibility(1)
                removed_reminder_label.SetVisibility(1)
            load_models()

    remove_selection_button = tk.Button(
        grid_manip_frame, text='Remove selected item', command=remove_id)
    remove_selection_button.grid(sticky='ew')

    def restore_list(event=None):
        global id_list, removed_items
        id_list = reader.get('ids')
        removed_items = 0
        removed_reminder.SetVisibility(0)
        removed_reminder_label.SetVisibility(0)
        load_models()
    restore_all_items_button = tk.Button(
        grid_manip_frame, text='Restore all items', command=restore_list)
    restore_all_items_button.grid(sticky='ew')

    grid_manip_frame.columnconfigure(0, weight=1)
    grid_manip_frame['border'] = 1
    # flat, groove, raised, ridge, solid, or sunken
    grid_manip_frame['relief'] = 'groove'
    grid_manip_frame.grid(sticky='ew', pady=5, padx=5, ipadx=2, ipady=2)
    #=====================================================================
    renderer_frame = tk.Frame(top)
    renderer_frame.grid(row=0, column=1, sticky='ewsn')
    top.columnconfigure(1, weight=1)

    grid_view = braviz.visualization.GridView()

    removed_reminder = vtk.vtkTextActor()
    grid_view.ren.AddViewProp(removed_reminder)
    removed_reminder.SetInput('10')
    removed_reminder.SetTextScaleModeToProp()
    reminder_coord = removed_reminder.GetPositionCoordinate()
    reminder_coord2 = removed_reminder.GetPosition2Coordinate()
    # removed_reminder.SetPosition2(1.0,1.0)

    reminder_coord.SetCoordinateSystemToViewport()
    reminder_coord2.SetCoordinateSystemToViewport()
    corner_coord = vtk.vtkCoordinate()
    corner_coord.SetCoordinateSystemToNormalizedViewport()
    corner_coord.SetValue(1.0, 0.0)
    reminder_coord2.SetReferenceCoordinate(corner_coord)
    reminder_coord.SetReferenceCoordinate(corner_coord)

    reminder_coord.SetValue(-80, 50)
    reminder_coord2.SetValue(-10, 85)
    removed_reminder.UseBorderAlignOn()

    tprop = removed_reminder.GetTextProperty()
    tprop.SetFontSize(18)
    tprop.ShadowOn()
    tprop.SetJustificationToCentered()

    removed_reminder_label = vtk.vtkTextActor()
    grid_view.ren.AddViewProp(removed_reminder_label)
    removed_reminder_label.SetInput('Removed')

    removed_reminder_label.SetTextScaleModeToProp()
    reminder_coord = removed_reminder_label.GetPositionCoordinate()
    reminder_coord2 = removed_reminder_label.GetPosition2Coordinate()
    # removed_reminder.SetPosition2(1.0,1.0)

    reminder_coord.SetCoordinateSystemToViewport()
    reminder_coord2.SetCoordinateSystemToViewport()
    reminder_coord2.SetReferenceCoordinate(corner_coord)
    reminder_coord.SetReferenceCoordinate(corner_coord)

    reminder_coord.SetValue(-80, 10)
    reminder_coord2.SetValue(-10, 50)
    removed_reminder_label.UseBorderAlignOn()

    tprop = removed_reminder_label.GetTextProperty()
    tprop.SetFontSize(18)
    tprop.ShadowOn()
    tprop.SetJustificationToCentered()
    tprop.SetVerticalJustificationToTop()

    removed_reminder.SetVisibility(0)
    removed_reminder_label.SetVisibility(0)

    render_widget = vtkTkRenderWindowInteractor(
        renderer_frame, rw=grid_view, width=600, height=600)

    renderer_frame.columnconfigure(0, weight=1)
    renderer_frame.rowconfigure(0, weight=1)
    render_widget.grid(row=0, column=0, sticky='ewsn')

    iact = render_widget.GetRenderWindow().GetInteractor()
    grid_view.set_interactor(iact)
    iact.SetInteractorStyle(vtk.vtkInteractorStyleTrackballActor())
    widgets = [apply_model_selection_button, sort_button, color_button, add_fibers_check, add_fibers_operation,
               select_model_frame, tab_list, hide_waypoints_check]

    def clean_exit():
        global grid_view
        grid_view.FastDelete()
        del grid_view

        quit(0)
    top.protocol("WM_DELETE_WINDOW", clean_exit)

    #===============================================
    # create interesting initial view
    async_load_models(False, False)
    finish_load_models()
    color_models()
    sort_models()
    grid_view.set_orientation(
        (-11.357671297580744, -94.18586865794096, 97.555764310434))
    grid_view.set_mini_scatter_visible(True)
    root.after(20, sort_models)
    # Start Tkinter event loop
    root.mainloop()
