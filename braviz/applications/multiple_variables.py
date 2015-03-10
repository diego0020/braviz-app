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


from __future__ import division
import Tkinter as tk
from Tkinter import Frame as tkFrame
import ttk
from itertools import izip
import os
from collections import defaultdict, OrderedDict
from tkFileDialog import askopenfile, asksaveasfile
from collections import namedtuple
from tkMessageBox import showerror, showinfo
import json
import thread
import threading

import numpy as np
from vtk.tk.vtkTkRenderWindowInteractor import \
    vtkTkRenderWindowInteractor

import braviz
from braviz.interaction.tk_gui import hierarchy_dict_to_tree
from braviz.visualization.matplotlib_charts import BarPlot, ScatterPlot, SpiderPlot
from braviz.interaction.tk_tooltip import ToolTip
from braviz.interaction.tms_variables import data_codes_dict
from braviz.readAndFilter.read_csv import get_column, get_headers
from braviz.readAndFilter.link_with_rdf import get_braint_hierarchy
from braviz.interaction.structure_metrics import cached_get_struct_metric_col
from braviz.interaction.structural_hierarchy import get_structural_hierarchy
from braviz.interaction.tms_variables import hierarchy_dnd as tms_hierarchy
from braviz.interaction.tms_variables import long_messages_dict as tms_long_messages
from braviz.utilities import get_leafs
from braviz.visualization.grid_viewer import GridView
from braviz.readAndFilter.link_with_rdf import cached_get_free_surfer_dict
from braviz.interaction.structure_metrics import solve_laterality


__author__ = 'Diego'


class VariableSelectFrame(tkFrame):

    def __init__(self, reader, parent, **kwargs):
        tkFrame.__init__(self, parent, **kwargs)
        super_tree_frame = tk.Frame(self)
        self.columnconfigure(0, weight=1)
        super_tree = ttk.Treeview(
            super_tree_frame, show='tree', selectmode='browse')
        super_tree_frame.grid(row=0, sticky='nsew', padx=2, pady=5)
        super_tree_scroll = ttk.Scrollbar(
            super_tree_frame, orient=tk.VERTICAL, command=super_tree.yview)
        super_tree['yscrollcommand'] = super_tree_scroll.set
        super_tree.grid(row=0, column=0, sticky='nsew')
        super_tree_scroll.grid(row=0, column=1, sticky='sn')
        super_tree_frame.rowconfigure(0, weight=1)
        super_tree_frame.columnconfigure(0, weight=1)
        self.__super_tree_tooltip = None
        self.__super_tree_message_dict = {}
        self.rowconfigure(0, weight=1)
        self.rowconfigure(5, weight=0)

        metric_select_frame = tk.Frame(self)
        metric_label = tk.Label(metric_select_frame, text='Metric: ')
        metric_selection_var = tk.StringVar()
        metric_selection_var.set('None')
        metric_select_box = ttk.Combobox(
            metric_select_frame, width=10, textvariable=metric_selection_var)
        metric_label.grid(row=0, column=0, sticky='w')
        metric_select_box.grid(row=0, column=1, sticky='ew')
        metric_select_frame.columnconfigure(1, weight=1)

        metric_select_frame.grid(row=1, column=0, sticky='ew', padx=2, pady=2)

        add_to_selection_button = tk.Button(self, text="Add to selection")
        add_to_selection_button.grid(row=2, sticky='ew', padx=2, pady=2)

        selected_variables_list = tk.Listbox(
            self, height=10, exportselection=0)
        selected_variables_list.grid(row=5, sticky='nsew', padx=2, pady=5)

        def get_full_name(event=None):
            y = event.y
            index = selected_variables_list.nearest(y)
            full_name = selected_variables_list.get(index)
            return full_name
        self.__selected_valriables_tooltip = ToolTip(
            selected_variables_list, msgFunc=get_full_name, delay=0.5, follow=1)

        bottom_buttons_frame = tk.Frame(self)
        bottom_buttons_frame.grid(row=6, sticky='ew', pady=5, padx=2)

        remove_from_selection_button = tk.Button(
            bottom_buttons_frame, text='Remove')
        clear_selection_button = tk.Button(bottom_buttons_frame, text='Clear')
        apply_selection_button = tk.Button(
            bottom_buttons_frame, text='Apply Selection')
        progress = tk.IntVar()
        progress.set(100)
        progress_bar = ttk.Progressbar(bottom_buttons_frame, orient='horizontal', length='100', mode='determinate',
                                       variable=progress)
        clear_selection_button.grid(row=0, column=0, sticky='ew')
        remove_from_selection_button.grid(row=0, column=1, sticky='ew')
        apply_selection_button.grid(row=1, column=0, columnspan=2, sticky='ew')
        progress_bar.grid(row=2, column=0, columnspan=2, sticky='ew')
        bottom_buttons_frame.columnconfigure(0, weight=1)
        bottom_buttons_frame.columnconfigure(1, weight=1)

        self.__reader = reader
        self.__super_tree = super_tree
        self.__fill_super_tree()

        self.__add_to_selection_button = add_to_selection_button
        self.__metric_select_box = metric_select_box
        self.__metric_selection_var = metric_selection_var
        self.__selected_variables_list = selected_variables_list
        self.__clear_selection_button = clear_selection_button
        self.__remove_from_selection_button = remove_from_selection_button
        self.__apply_selection_button = apply_selection_button
        self.__progress = progress
        self.__add_observers()

        # public access to tree_view
        self.tree_view = super_tree

    def __fill_super_tree(self):
        super_tree = self.__super_tree
        message_dict = self.__super_tree_message_dict
        # TABLE
        table_file = os.path.join(
            self.__reader.get_data_root(), 'test_small.csv')
        table_headers = get_headers(table_file)
        table_dict = dict(((hdr, {}) for hdr in table_headers))
        super_tree.insert('', tk.END, 'table', text='Table')
        message_dict['table'] = "From big table file"
        hierarchy_dict_to_tree(super_tree, table_dict, 'table', tags=['table'])
        # BRAINT
        try:
            braint = get_braint_hierarchy()
        except Exception:
            super_tree.insert('', tk.END, 'braint', text='Braint (offline)')
        else:
            super_tree.insert('', tk.END, 'braint', text='Braint')
            hierarchy_dict_to_tree(
                super_tree, braint, 'braint', tags=['braint'])
        # TMS

        super_tree.insert('', tk.END, 'tms', text='TMS')
        message_dict['tms'] = "TMS-Tests"
        hierarchy_dict_to_tree(super_tree, tms_hierarchy, 'tms', tags=['tms'],
                               tooltip_dict=message_dict, tooltip_source=tms_long_messages, default_message="TMS-Tests")

        # ANATOMY

        super_tree.insert('', tk.END, 'structural', text='Structural')
        anatomy_hierarchy = get_structural_hierarchy(self.__reader, '144')
        free_surfer_pretty_names = cached_get_free_surfer_dict()
        hierarchy_dict_to_tree(super_tree, anatomy_hierarchy, 'structural', tags=['struct'],
                               tooltip_dict=message_dict, tooltip_source=free_surfer_pretty_names)

        def get_super_tree_tooltip(event=None):
            coord = event.y
            element = super_tree.identify_row(coord)
            if len(element) == 0:
                return ''
            else:
                return self.__super_tree_message_dict.get(element, "missing")
        self.__super_tree_tooltip = ToolTip(
            super_tree, msgFunc=get_super_tree_tooltip, follow=1, delay=0.5)

    def __add_observers(self):
        add_to_selection_button = self.__add_to_selection_button
        add_to_selection_button['state'] = 'disabled'
        metric_select_box = self.__metric_select_box
        metric_select_box['state'] = 'disabled'
        valid_metrics = {
            'fibers': ("Number", "Mean FA", "Mean Length"),
            'multiple': ('Volume', 'Fibers Crossing', 'Mean FA of Fibers Crossing', 'Mean Length of Fibers Crossing'),
            'leaf_struct': ('Volume', 'Surface Area', 'Fibers Crossing',
                            'Mean FA of Fibers Crossing', 'Mean Length of Fibers Crossing')
        }

        def toggle_add_button(event=None):
            super_tree = self.__super_tree
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
                    # if selection[0] in ('structural:Left_Hemisphere','structural:Right_Hemisphere'):
                    #    metric_select_box['state'] = 'disabled'
                    #    add_to_selection_button['state'] = 'disabled'
                    #    return
                    metrics = valid_metrics['multiple']
                else:
                    metrics = valid_metrics['leaf_struct']
                metric_select_box['values'] = metrics
                metric_select_box['state'] = 'readonly'
                metric_selection_var = self.__metric_selection_var
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
            if not self.__add_to_selection_button['state'] == 'normal':
                return
            super_tree = self.__super_tree
            metric_selection_var = self.__metric_selection_var

            tree_variable = super_tree.selection()[0]
            if tree_variable.startswith('structural'):
                tree_variable = ':'.join(
                    (metric_selection_var.get(), tree_variable[11:]))
            selected_variables_list = self.__selected_variables_list
            selected_variables_list.insert(tk.END, tree_variable)

        add_to_selection_button['command'] = add_variable
        self.__super_tree.bind("<Double-Button-1>", add_variable)

        def clear_variables(event=None):
            selected_variables_list = self.__selected_variables_list
            selected_variables_list.delete(0, tk.END)

        clear_selection_button = self.__clear_selection_button
        clear_selection_button['command'] = clear_variables

        def remove_variable(event=None):
            selected_variables_list = self.__selected_variables_list
            index = selected_variables_list.curselection()
            if len(index) > 0:
                selected_variables_list.delete(index)

        remove_from_selection_button = self.__remove_from_selection_button
        remove_from_selection_button['command'] = remove_variable

    def get_selected_variables(self):
        return self.__selected_variables_list.get(0, tk.END)

    def set_selected_variables(self, selection):
        self.__selected_variables_list.delete(0, tk.END)
        self.__selected_variables_list.insert(0, *selection)

    def set_apply_callback(self, callback):
        def callback2(event=None):
            callback(self.get_selected_variables())
        self.__apply_selection_button['command'] = callback2

    def set_progress(self, prog):
        self.__progress.set(prog)

    def disable_apply(self):
        self.__apply_selection_button['state'] = 'disabled'

    def enable_apply(self):
        self.__apply_selection_button['state'] = 'normal'


class VtkWidget(tkFrame):

    def __init__(self, reader, parent, max_structs=30, **kwargs):
        self.__default_struct_list = ['Brain-Stem', 'CC_Anterior', 'CC_Central', 'CC_Mid_Anterior', 'CC_Mid_Posterior',
                                      'CC_Posterior', 'ctx-lh-paracentral', 'ctx-lh-precuneus', 'ctx-lh-superiorfrontal']
        self.__max_structs = max_structs
        self.__groups_dict = {}
        self.__groups_list_list = []
        self.__codes = []
        self.__reader = reader
        self.__color_fun = lambda x: (1.0, 0.0, 0.0)
        tkFrame.__init__(self, parent, **kwargs)
        self.__grid_viewer = GridView(use_lod=False)
        grid_widget = vtkTkRenderWindowInteractor(self, rw=self.__grid_viewer,
                                                  width=kwargs.get('width', 600), height=kwargs.get('height', 300))
        grid_widget.grid(row=0, column=0, sticky='NSEW')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        iact = grid_widget.GetRenderWindow().GetInteractor()
        self.__grid_viewer.set_interactor(iact)
        self.grid_view = self.__grid_viewer
        self.__grid_viewer.set_orientation((0, -90, 90))
        self.__models_dict = None
        self.__laterality = {}

    def set_laterality_dict(self, lat_dict):
        self.__laterality = lat_dict

    def set_groups_dict(self, groups_dict, group_colors):
        self.__groups_dict = groups_dict
        self.__codes = groups_dict.keys()
        inv_groups_dict = defaultdict(list)
        for subj, group in groups_dict.iteritems():
            inv_groups_dict[group].append(subj)
        groups_list = inv_groups_dict.items()
        groups_list.sort(key=lambda x: x[0])
        self.__groups_list_list = [x[1] for x in groups_list]

        def color_function(subj_id):
            return group_colors[groups_dict[subj_id]]
        self.__color_fun = color_function

    def clear_memory(self):
        self.__models_dict = {}
        self.grid_view.clear_all()

    def update_structures(self, struct_list, fibers_list, async=True, state_vars={}):
        models_dict = {}
        if async is False:
            self.grid_view.clear_all()
        if len(struct_list) + len(fibers_list) == 0:
            struct_list = self.__default_struct_list
            #self.__grid_viewer.set_orientation((3.060316756674142, -94.78573096609321, 97.86560994941594))
            self.__grid_viewer.set_orientation((0, -90, 90))
        if len(struct_list) >= self.__max_structs:
            # get the first 10, from fibers and if left from structs
            struct_list = sorted(struct_list)[:self.__max_structs]
        state_vars['number_requested'] = len(self.__codes)
        state_vars['number_loaded'] = 0
        for i, cod in enumerate(self.__codes):
            state_vars['number_loaded'] = i
            model_list = []
            struct_list2 = solve_laterality(
                self.__laterality.get(cod, 'unknwon'), struct_list)
            fibers_list2 = solve_laterality(
                self.__laterality.get(cod, 'unknwon'), fibers_list)
            for struct in struct_list2:
                # print "loading model %s for subject %s" % (struct, cod)
                try:
                    model = self.get_structure(cod, struct)
                except Exception as e:
                    print "**couldn't load model %s for subject %s" % (struct, cod)
                    print e
                else:
                    if model is not None:
                        model_list.append(model)

            try:
                # print "loading fibers %s for subject %s" % (fibers_list, cod)
                fibers = self.get_fibers(cod, fibers_list2)
            except Exception:
                print "couldn't load fibers %s for subject %s" % (fibers_list2, cod)
            else:
                if fibers is not None:
                    model_list.append(fibers)
            if len(model_list) > 0:
                models_dict[cod] = model_list
        state_vars['number_loaded'] = len(self.__codes)
        self.__models_dict = models_dict
        if async is False:
            self.render()

    def render(self):
        models_dict = self.__models_dict
        self.__grid_viewer.set_data(models_dict)
        self.__grid_viewer.set_color_function(self.__color_fun, opacity=0.05)
        group_list = self.__groups_list_list[:]
        filter_func = lambda y: filter(lambda x: x in models_dict.keys(), y)
        group_list = map(filter_func, group_list)
        self.__grid_viewer.sort(group_list, overlay=True)
        self.__grid_viewer.reset_camera()
        self.__grid_viewer.Render()

    def set_messages(self, message_dict):
        self.__grid_viewer.set_balloon_messages(message_dict)

    def get_structure(self, code, struct_name):
        if struct_name.startswith('Fibs:'):
            model = self.__reader.get('fibers', code, name=struct_name[5:])
            return model
        else:
            model = self.__reader.get('model', code, name=struct_name)
            return model

    def get_fibers(self, code, waypoints):
        if len(waypoints) > 0:
            fibs = self.__reader.get(
                'fibers', code, waypoint=waypoints, operation='or')
            return fibs
        else:
            return None

    def set_selection(self, subj_id):
        self.__grid_viewer.select_name(subj_id)

    def set_selection_handler(self, function):
        """function will receive two parameters, (event,subj_id) """
        def internal_observer(caller=None, event=None):
            subj_id = self.__grid_viewer.get_selection()
            function("actor_selected_event", subj_id)
        self.__grid_viewer.AddObserver(
            self.__grid_viewer.actor_selected_event, internal_observer)

    def get_orientation(self):
        return self.grid_view.get_orientation()

    def set_orientation(self, orintation):
        self.grid_view.set_orientation(orintation)

    def get_selected_id(self):
        return self.grid_view.get_selection()


class GraphFrame(tkFrame):

    def __init__(self, ubica_dict, parent, **kwargs):
        tkFrame.__init__(self, parent, **kwargs)
        self.__group_dict = ubica_dict
        self.__bar_chart = None
        self.__scatter_plot = None
        self.__widget = None
        self.__spider_plot = None
        self.__active_plot = None
        self.__color_fun = lambda x, y: (1, 0, 1)
        self.__data = {}
        self.__axes = []
        self.__messages = {}
        self.__width = kwargs.get('width', 600)
        self.__height = kwargs.get('height', 200)
        self.__selection_handler = lambda x: None
        self.__name2idx = {}
        init_panel = tk.Frame(
            self, relief='ridge', border=2, height=self.__height, width=self.__width,)

        init_label = tk.Label(init_panel, text='Select some data to start')
        init_panel.pack_propagate(0)
        init_label.pack(fill='both', expand=True)

        init_panel.grid(row=0, column=0, sticky='NSEW', padx=2, pady=2)
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.__widget = init_panel
        self.tool_tip = ToolTip(
            init_label, msgFunc=self.get_subject_message, follow=1, delay=0.5)

    def set_color_function(self, color_func):
        """Function must take val,code pairs and return a color"""
        self.__color_fun = color_func

    def update_representation(self, data=None):
        if data is None:
            data = self.__data
        else:
            self.__data = data
            self.update_popups_messages()
        if len(data) == 0:
            return
        if self.__widget is not None:
            self.__widget.grid_forget()
            self.__widget.bind('<<PlotSelected>>')
            self.__widget = None
        if len(data) == 1:
            self.draw_bar_chart(data)
            self.__active_plot = self.__bar_chart
        elif len(data) == 2:
            self.draw_scatter(data)
            self.__active_plot = self.__scatter_plot
        else:
            self.draw_spiders(data)
            self.__active_plot = self.__spider_plot
        del self.tool_tip
        self.tool_tip = ToolTip(
            self.__widget, msgFunc=self.get_subject_message, follow=1, delay=0.5)
        self.__widget.bind('<<PlotSelected>>', self.__selection_handler)

    def draw_bar_chart(self, data):
        y_label, data_dict = data.popitem()
        # put it back in, incase it is reused
        data[y_label] = data_dict

        if self.__bar_chart is None:
            bar_plot = BarPlot(tight=True)
            self.__bar_chart = bar_plot
        else:
            bar_plot = self.__bar_chart

        bar_widget = bar_plot.get_widget(
            self, height=self.__height, width=self.__width)
        bar_widget.grid(row=0, column=0, sticky='NSEW')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.__widget = bar_widget
        good_data = dict(((k, v)
                          for k, v in data_dict.iteritems() if np.isfinite(v)))
        if len(good_data) == 0:
            print "Something went wrong... there are not real values"
            return
        term_data = [
            v for k, v in good_data.iteritems() if self.__group_dict[k] == '3']
        term_mean = np.mean(term_data)
        term_std = np.std(term_data)
        good_min = np.min(good_data.values())
        good_max = np.max(good_data.values())
        good_extent = good_max - good_min
        bar_plot.set_y_limits(
            good_min - good_extent / 20, good_max + good_extent / 20)
        bar_plot.set_lines(
            [term_mean - term_std, term_mean, term_mean + term_std], (True, False, True))
        bar_plot.set_y_title(y_label)
        data_tuples = good_data.items()
        data_tuples.sort(key=lambda x: self.__group_dict[x[0]])

        bar_plot.set_color_fun(self.__color_fun, code_and_val=True)
        codes, datums = zip(*data_tuples)
        bar_plot.set_data(datums, codes)
        for i, cd in enumerate(codes):
            self.__name2idx[cd] = i
        group_stats = self.get_group_stats(good_data)
        groups = sorted(group_stats.keys())
        means, stds, ns = zip(*map(group_stats.get, groups))

        bar_plot.set_back_bars(
            back_bars=zip(means, ns), back_error=stds, back_codes=("1", "2", "3"))
        bar_plot.paint_bar_chart()

    def draw_scatter(self, data_dict):
        good_data_dict = self.filter_dict(data_dict)
        if self.__scatter_plot is None:
            self.__scatter_plot = ScatterPlot(tight=True)
        scatter = self.__scatter_plot
        scatter_widget = scatter.get_widget(
            self, height=self.__height, width=self.__width)
        scatter_widget.grid(row=0, column=0, sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.__widget = scatter_widget
        x_label, x_data_dict = good_data_dict.popitem()
        y_label, y_data_dict = good_data_dict.popitem()
        codes = x_data_dict.keys()
        for i, cd in enumerate(codes):
            self.__name2idx[cd] = i
        y_data = [y_data_dict[k] for k in codes]
        x_data = [x_data_dict[k] for k in codes]
        try:
            x_min = np.min(x_data)
            x_max = np.max(x_data)
        except ValueError:
            x_min = 0
            x_max = 1
        x_extent = x_max - x_min
        try:
            y_min = np.min(y_data)
            y_max = np.max(y_data)
        except ValueError:
            y_max = 1
            y_min = 0

        y_extent = y_max - y_min
        scatter.set_limits((x_min - x_extent / 10, x_max + x_extent / 10),
                           (y_min - y_extent / 10, y_max + y_extent / 10))
        scatter.set_labels(x_label, y_label)
        scatter.set_data(x_data, y_data, codes)
        scatter.set_color_function(self.__color_fun)
        scatter.set_groups(self.__group_dict)
        # print zip(x_data,y_data)
        scatter.draw_scatter()
        self.__widget = scatter_widget

    def draw_spiders(self, data_dict):
        good_data_dict = self.filter_dict(data_dict)
        if self.__spider_plot is None:
            self.__spider_plot = SpiderPlot()
        spider = self.__spider_plot
        spider_widget = spider.get_widget(
            self, height=self.__height, width=self.__width)
        spider_widget.grid(row=0, column=0, sticky='nsew')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)
        self.__widget = spider_widget

        norm_data = self.normalize_variables(good_data_dict)
        spider_dict = {}
        variables = norm_data.keys()
        codes = norm_data[variables[0]].keys()
        for cd in codes:
            spider_dict[cd] = [norm_data[v][cd] for v in variables]
        spider.set_data(spider_dict, range(len(variables)))
        spider.set_groups(self.__group_dict)
        spider.set_rmax(1)
        spider.set_color_fun(self.__color_fun)
        spider.draw_spider()
        self.__widget = spider_widget

    @staticmethod
    def normalize_variables(data_frame):
        for key, data_dict in data_frame.iteritems():
            keys, values = zip(*data_dict.items())
            minimum = np.min(values)
            maximum = np.max(values)
            width = maximum - minimum
            if width < 0.001:
                width = 1
            norm_values = map(
                lambda x: 0.9 * (x - minimum) / width + 0.1, values)
            data_dict.update(izip(keys, norm_values))
        return data_frame

    def get_group_stats(self, data_dict):
        group_values_dict = {}
        for cd, value in data_dict.iteritems():
            group = self.__group_dict[cd]
            if np.isfinite(value):
                group_values_dict.setdefault(group, []).append(value)
        results = {}
        # 1=canguro, 2=control, 3=gorditos
        for g, values in group_values_dict.iteritems():
            n = len(values)
            if len(values) > 0:
                mean = np.mean(values)
                std = np.std(values)
            else:
                mean = 0
                std = 0
            results[g] = (mean, std, n)
        return results

    @staticmethod
    def filter_dict(data, get_subj_dict=False):
        """ Removes all ids which contain nan values"""

        subjects_dir = defaultdict(dict)
        for col, col_data in data.iteritems():
            for subj, value in col_data.iteritems():
                subjects_dir[subj][col] = col_data.get(subj, float('nan'))
        for subj, data_dict in subjects_dir.items():
            if not np.all(np.isfinite(data_dict.values())):
                subjects_dir.pop(subj)
        out_data = OrderedDict()
        for col in data.iterkeys():
            out_data[col] = dict((k, values[col])
                                 for k, values in subjects_dir.iteritems())
        return out_data

    def update_popups_messages(self):
        messages = {}
        subj_data = {}
        axes = []
        for var, var_dict in self.__data.iteritems():
            axes.append(var)
            group_stats = self.get_group_stats(var_dict)
            for subj, value in var_dict.iteritems():
                subj_group = self.__group_dict[subj]
                subj_data.setdefault(subj, ["%s ( group %s )" % (subj, subj_group)]).append(
                    "%s : %.2f (%.2f)" % (var, value, group_stats.get(subj_group, (0,))[0]))
        for subj, data in subj_data.iteritems():
            messages[subj] = "\n".join(data)
        self.__messages = messages
        self.__axes = axes

    def get_subject_message(self, event=None):
        if self.__active_plot is not None:
            hover_item = self.__active_plot.get_current_name()
            if hover_item is None:
                return ''
            elif hover_item.startswith('axis'):
                return self.__axes[int(hover_item[5:])]
            else:
                return self.__messages[hover_item]
        else:
            return 'Select some data and click "Apply Selection"'
        return "hola: %s" % hover_item

    def get_messages_dict(self):
        return self.__messages

    def resize_bars(self):
        if self.__bar_chart is not None:
            # self.__bar_chart.figure.subplots_adjust(top=100,bottom=0)
            # self.__bar_chart.figure.subplots_adjust(bottom=0,top=1)
            self.__bar_chart.show()

    def set_selection_handler(self, function):
        """funciton must take two parameters, (event, subj_id)"""
        def selection_handler_internal(event=None):
            current_subj = self.__active_plot.get_current_name()
            function(event, current_subj)
        self.__selection_handler = selection_handler_internal
        self.__widget.bind('<<PlotSelected>>', self.__selection_handler)

    def set_highlight(self, highlight_code):
        if self.__active_plot == None:
            return
        if self.__active_plot == self.__spider_plot:
            self.__spider_plot.set_highlighted_key(highlight_code)
        else:
            idx = self.__name2idx[highlight_code]
            self.__active_plot.set_higlight_index(idx)
        self.__active_plot.paint()


class DataFetcher(object):

    def __init__(self, reader, codes=None):
        self.__reader = reader
        self.__codes = codes
        self.__struct_hierarchy = get_structural_hierarchy(
            self.__reader, '144')
        self.__laterality = None
        self.__tms_file = os.path.join(
            self.__reader.get_data_root(), 'baseFinal_TMS.csv')

    def get_data(self, data_variables, state_dict={}):
        # decode
        data_dict = OrderedDict()
        structures = set()
        fibers_set = set()
        state_dict['len'] = len(data_variables)
        state_dict['done'] = 0
        for col in data_variables:
            # print col
            if col.startswith('braint'):
                out_data = self.get_braint_data_col(col)
            elif col.startswith('tms'):
                out_data = self.get_tms_data_col(col)
            elif col.startswith('table'):
                out_data = self.get_matrix_data_col(col)
            else:
                out_data, structural_structs, fibers = self.get_structural_data_col(
                    col, state_dict)
                structures.update(structural_structs)
                if fibers is not None:
                    fibers_set.update(fibers)
            data_dict[col] = out_data
            state_dict['number_calculated'] = 0
            state_dict['done'] += 1

        return data_dict, structures, fibers_set

    def get_tms_data_col(self, col):

        tms_csv_file = os.path.join(
            self.__reader.get_data_root(), self.__tms_file)
        tokens = col.split(':')
        hemisphere = tokens[-1]
        if hemisphere == 'Dominant':
            h = 'd'
        else:
            h = 'nd'
        decoded_col = tokens[-2]
        decoded_col = decoded_col.replace('_', ' ')
        decoded_col = data_codes_dict[decoded_col]
        data_col = get_column(tms_csv_file, decoded_col + h, numeric=True)
        codes_col = get_column(tms_csv_file, 'CODE', numeric=False)
        data_dict = dict(izip(codes_col, data_col))
        return data_dict

    def set_codes(self, codes):
        self.__codes = codes

    def get_codes(self):

        if self.__codes is not None:
            return self.__codes
        else:
            tms_csv_file = os.path.join(
                self.__reader.get_data_root(), 'baseFinal_TMS.csv')
            codes_col = get_column(tms_csv_file, 'CODE', numeric=False)
            return codes_col

    def get_ubica_dict(self):

        tms_csv_file = os.path.join(
            self.__reader.get_data_root(), self.__tms_file)
        codes_col = get_column(tms_csv_file, 'CODE', numeric=False)
        ubica_col = get_column(tms_csv_file, 'UBICA', numeric=False)
        return dict(izip(codes_col, ubica_col))

    def get_later_dict(self):
        if self.__laterality is not None:
            return self.__laterality
        tms_csv_file = os.path.join(
            self.__reader.get_data_root(), self.__tms_file)
        codes_col = get_column(tms_csv_file, 'CODE', numeric=False)
        ubica_col = get_column(tms_csv_file, 'LATER', numeric=False)
        # 1: Right Handed

        def words_laterality(x):
            if x == "1":
                return "r"
            elif x == "2":
                return "l"
            else:
                return "u"
        return dict(izip(codes_col, map(words_laterality, ubica_col)))

    def get_structural_data_col(self, col, state_vars={}):

        # decode
        metrics_dict = {
            'Volume': 'volume',
            'Surface Area': 'area',
            'Fibers Crossing': 'nfibers',
            'Mean FA': 'fa_fibers',
            'Mean FA of Fibers Crossing': 'fa_fibers',
            'Number': 'nfibers',
            'Mean Length': 'lfibers',
            'Mean Length of Fibers Crossing': 'lfibers',
        }
        # print col
        tokens = col.split(':')
        metric = metrics_dict[tokens[0]]
        sub_d = self.__struct_hierarchy
        for tok in tokens[1:]:
            if sub_d.has_key(tok):
                sub_d = sub_d[tok]
            else:
                sub_d = sub_d[tok.replace('_', ' ')]

        # print children
        if len(sub_d) == 0:
            children = (tokens,)
        else:
            children_str = get_leafs(sub_d, col)
            children = map(lambda x: x.split(':'), children_str)
        names = map(self.__reconstruct_struct_name, children)
        # unique names
        names = set(names)
        codes = self.get_codes()
        # data_col=map(metric_func,codes)
        if self.__laterality is None:
            self.__laterality = self.get_later_dict()

        data_col = cached_get_struct_metric_col(self.__reader, codes, names, metric, force_reload=False,
                                                laterality_dict=self.__laterality, state_variables=state_vars)
        result_dict = dict(izip(codes, data_col))
        struct_tuple = namedtuple(
            'struct_descriptor', ['with_fibers', 'names'])
        if metric.endswith('fibers') and (len(names) > 1 or not iter(names).next().startswith('Fibs:')):
            fibers = tuple(names)
        else:
            fibers = None
        return result_dict, names, fibers

    def get_matrix_data_col(self, col):
        matrix_file = os.path.join(
            self.__reader.get_data_root(), 'test_small.csv')
        tokens = col.split(':')
        decoded_col = tokens[-1]
        data_col = get_column(matrix_file, decoded_col, numeric=True)
        codes_col = get_column(matrix_file, 'code', numeric=False)
        data_dict_1 = dict(izip(codes_col, data_col))
        data_dict_2 = dict(
            ((cd, data_dict_1.get(cd, float('nan'))) for cd in self.get_codes()))
        return data_dict_2

    @staticmethod
    def __reconstruct_struct_name(tokens):
        structure_type = tokens[1]
        if structure_type == 'Fibers':
            name = 'Fibs:' + tokens[2]
        elif structure_type in ('Base', 'Spharm'):
            name = tokens[2]
        elif structure_type[0] == 'C':
            # Corpus Callosum
            name = 'CC_' + tokens[2]
        else:
            # cortex
            if tokens[2].startswith('All_'):
                if tokens[2][4] == 'G':
                    matter = 'ctx'
                else:
                    matter = 'wm'
                pname = tokens[-1]
            else:
                if tokens[-1][0] == 'G':
                    # gray matter
                    matter = 'ctx'
                else:
                    # white matter
                    matter = 'wm'
                pname = tokens[-2]
            if structure_type[0] == 'L':
                h = 'lh'
            elif structure_type[0] == 'R':
                h = 'rh'
            elif structure_type[0] == 'D':
                h = 'dh'
            elif structure_type[0] == 'N':
                h = 'nh'
            full_name = '-'.join([matter, h, pname])
            name = full_name
        return name

    def get_braint_data_col(self, col):
        print "Braint data Not yet implemented"
        raise Exception("Not Implemented")


class SaveAndRestore(object):

    def __init__(self, application_name, parent, default_dir=None):
        self.__application_name = application_name
        self.__parent = parent
        self.__extension = '.braviz'
        self.__defautl_dir = default_dir

    def save(self, variables_dict={}):
        write_file = asksaveasfile(mode='w', defaultextension=self.__extension, parent=self.__parent, title="Save Scenario",
                                   initialdir=self.__defautl_dir, filetypes=[("braviz scenario", "*.braviz")])
        if write_file is None:
            return
        try:
            variables_dict["__app_name__"] = self.__application_name
            json.dump(variables_dict, write_file, sort_keys=True,
                      separators=(',', ': '), indent=4)
        except TypeError:
            showerror(
                "Braviz", "Fatal Error, please contact application developer")
        except IOError:
            showerror(
                "Braviz", "There was a problem saving the file, please try again")
        else:
            showinfo("Braviz", "File saved correctly")
        finally:
            write_file.close()

    def load(self):
        read_file = askopenfile(mode='r', defaultextension=self.__extension, parent=self.__parent,
                                title="Load Scenario",
                                initialdir=self.__defautl_dir, filetypes=[("braviz scenario", "*.braviz")])
        if read_file is None:
            return
        try:
            variables_dict = json.load(read_file, )
            if not variables_dict.pop("__app_name__") == self.__application_name:
                showerror(
                    "Braviz", "This file was NOT created with the current application")
                return
        except Exception:
            showerror("Braviz", "Invalid File")
        finally:
            read_file.close()
        return variables_dict


class AsyncUpdataAll(object):

    def __init__(self, var_select, fetch, plots, vtk_view):
        self.var_select = var_select
        self.fetcher = fetch
        self.plots = plots
        self.vtk_view = vtk_view
        self.fetched_data = None

    def update_all(self, new_data_vars=None):
        if new_data_vars is None:
            new_data_vars = self.var_select.get_selected_variables()
        internal_vars = {
            'stage': 0,
        }
        # stage -1: Error
        # stage 0: Fetching Data
        # stage 1: Loading Vtk
        # stage 2: Prepared to render vtk
        # stage 3: Rendering vtk
        # stage 4: unused
        # stage 5: Done

        self.var_select.disable_apply()
        self.var_select.set_progress(0)
        external_state = {}

        def fetch_data(state_vars):
            print "getting variables"
            print "================="
            self.fetched_data = self.fetcher.get_data(
                new_data_vars, state_dict=external_state)

        def generate_vtk(state_vars):
            print "generating vtk graphics"
            print "================="
            new_data, structures, fibers = self.fetched_data
            self.vtk_view.update_structures(
                structures, fibers, async=True, state_vars=state_vars)

        def generate_plots():
            print "generating plot"
            print "================="
            new_data, _, _ = self.fetched_data
            self.plots.update_representation(new_data)
            self.vtk_view.set_messages(self.plots.get_messages_dict())

        def poll_progress(event=None):
            # print "polling: stage=%d"%state_vars['stage']
            if internal_vars['stage'] == 3:
                # final stage
                self.vtk_view.render()
                generate_plots()
                print "done"
                print "================="
                self.var_select.set_progress(100)
                internal_vars['stage'] = 5
            elif internal_vars['stage'] == 0:
                # fetching data
                prog_per_var = (50 / external_state.get('len', 10000))
                progress = external_state.get('done', 0) * prog_per_var
                sub_progress = (external_state.get(
                    'number_calculated', 0) / (external_state.get('number_requested', 1)))
                progress += sub_progress * prog_per_var
                self.var_select.set_progress(progress)
            elif internal_vars['stage'] == 1:
                # loading vtk models
                progress = 50 + \
                    external_state.get(
                        'number_loaded', 0) / external_state.get('number_requested', 1) * 40
                self.var_select.set_progress(progress)
            elif internal_vars['stage'] == 2:
                # preparing for final rendering... interface will freeze
                self.var_select.set_progress(90)
                internal_vars['stage'] = 3
            elif internal_vars['stage'] < 0:
                showerror(
                    "Error calculating", "There was an error loading the data, please check output")
                self.var_select.set_progress(0)
                self.var_select.enable_apply()
                internal_vars['stage'] = 5

            if internal_vars['stage'] < 5:
                self.var_select.after(20, poll_progress)
            else:
                self.var_select.enable_apply()
                print "number of threads: ", threading.active_count()
                return

        def async_update():
            try:
                internal_vars['stage'] = 0
                fetch_data(external_state)
                internal_vars['stage'] = 1
                generate_vtk(external_state)
                internal_vars['stage'] = 2
            except Exception as e:
                print e
                raise e
                internal_vars['stage'] = -1
            finally:
                return None

        self.var_select.set_progress(1)
        self.vtk_view.clear_memory()
        internal_vars['plots_rendered'] = 0
        thread_id = thread.start_new_thread(async_update, tuple())
        # async_update()
        self.var_select.after(20, poll_progress)
        # async_update()


class MultipleVariablesApp(object):

    def __init__(self, pipe=None):
        self.pipe = pipe

        self.root = tk.Tk()
        self.root.title('Braviz-Multiple Variables')

        self.reader2 = braviz.readAndFilter.BravizAutoReader()
        # reader2=braviz.readAndFilter.kmc40AutoReader()

        self.panned_window = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.panned_window.grid(sticky='nsew')
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.variable_select_frame = VariableSelectFrame(
            self.reader2, self.panned_window, height=500, width=200)
        self.display_frame = tk.Frame(
            self.panned_window, height=500, width=800, bg='black')
        self.panned_window.add(self.variable_select_frame)
        self.panned_window.add(self.display_frame)

        # vtk_frame=tk.Frame(display_frame,bg='green',height=400,width=600)
        # graph_frame=tk.Frame(display_frame,bg='blue',height=200,width=600)

        self.fetcher = DataFetcher(self.reader2)
        self.groups_dict = self.fetcher.get_ubica_dict()
        self.int_colors = {
            '1': [77, 175, 74],
            '2': [55, 126, 184],
            '3': [166, 86, 40]}

        self.float_colors = {}
        for key, color in self.int_colors.iteritems():
            self.float_colors[key] = map(lambda x: x / 255.0, color)
        self.groups_colors_matplotlib = self.float_colors

        def group_color_fun(val, key2):
            col = self.groups_colors_matplotlib.get(key2, None)
            if col is None:
                col = self.groups_colors_matplotlib[self.groups_dict[key2]]
            return col

        self.graph_frame = GraphFrame(
            self.groups_dict, self.display_frame, height=250, width=800)
        self.graph_frame.set_color_function(group_color_fun)
        self.vtk_frame = VtkWidget(
            self.reader2, self.display_frame, height=250, width=800)
        self.vtk_frame.set_groups_dict(self.groups_dict, self.float_colors)
        self.vtk_frame.set_laterality_dict(self.fetcher.get_later_dict())
        self.vtk_frame.grid(row=0, column=0, sticky='nsew')
        self.graph_frame.grid(row=1, column=0, sticky='nsew')

        self.display_frame.rowconfigure(0, weight=1)
        self.display_frame.rowconfigure(1, weight=1)
        self.display_frame.columnconfigure(0, weight=1)

        def plot_selection(event=None, subject=None):
            # print "graph selection: %s"%subject
            self.vtk_frame.set_selection(subject)
            if self.pipe is not None:
                self.pipe.send({'subject': subject})

        self.graph_frame.set_selection_handler(plot_selection)

        def vtk_event_listener(event, subj_id):
            # print subj_id
            self.graph_frame.set_highlight(subj_id)
            if self.pipe is not None:
                self.pipe.send({'subject': subj_id})

        self.vtk_frame.set_selection_handler(vtk_event_listener)
        # variable_select_frame.set_apply_callback(graph_frame.update_representation)

        self.updater = AsyncUpdataAll(
            self.variable_select_frame, self.fetcher, self.graph_frame, self.vtk_frame)
        # variable_select_frame.set_apply_callback(fetcher.get_data)
        self.variable_select_frame.set_apply_callback(self.updater.update_all)

        # aux_button=tk.Button(variable_select_frame,text="aux")
        # aux_button.grid(sticky='ew')
        # def print_orientation(event=None):
        #    print vtk_frame.grid_view.clear_all()
        # aux_button['command']=print_orientation

        app_name = application_name = os.path.basename(__file__)
        app_name = os.path.splitext(app_name)[0]
        self.save_and_restore = SaveAndRestore(app_name + '.py',
                                               default_dir=os.path.join(
                                                   os.path.dirname(__file__), "saved_scenarios"),
                                               parent=self.root)
        self.menu_bar = tk.Menu(self.root)
        self.file_menu = tk.Menu(self.menu_bar, tearoff=0)

        def save_state(event=None):
            fields = dict()
            fields[
                "selected_variables"] = self.variable_select_frame.get_selected_variables()
            fields["orientation"] = self.vtk_frame.get_orientation()
            fields["Selected_subject"] = self.vtk_frame.get_selected_id()
            self.save_and_restore.save(fields)

        def load_state(event=None):
            fields = self.save_and_restore.load()
            self.variable_select_frame.set_selected_variables(
                fields["selected_variables"])
            self.vtk_frame.set_orientation(fields["orientation"])
            self.updater.update_all()
            self.vtk_frame.set_selection(fields["Selected_subject"])
            self.graph_frame.set_highlight(fields["Selected_subject"])

        self.file_menu.add_command(label="Open", command=load_state)
        self.file_menu.add_command(label="Save", command=save_state)
        self.menu_bar.add_cascade(label="File", menu=self.file_menu)
        self.root.config(menu=self.menu_bar)

        def poll_for_messages(event=None):
            if self.pipe is not None:
                if self.pipe.poll():
                    message = self.pipe.recv()
                    subj = message.get('subject')
                    if subj is not None:
                        self.vtk_frame.set_selection(subj)
                        self.graph_frame.set_highlight(subj)

            self.root.after(200, poll_for_messages)
        if self.pipe is not None:
            self.root.after(500, poll_for_messages)

    def run(self):
        self.root.focus()
        tk.mainloop()


def launch_new(pipe=None):
    application = MultipleVariablesApp(pipe)
    application.run()

if __name__ == "__main__":
    launch_new()
