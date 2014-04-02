from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow
import numpy as np

from braviz.interaction.qt_guis.anova import Ui_Anova_gui
from braviz.interaction.qt_dialogs import OutcomeSelectDialog, RegressorSelectDialog, MatplotWidget,\
    InteractionSelectDialog
import braviz.interaction.r_functions

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection, get_data_frame_by_name
import braviz.readAndFilter.tabular_data as braviz_tab_data
import random

import colorbrewer

from itertools import izip

import multiprocessing
import multiprocessing.connection
import subprocess
import sys

#TODO: Move all database access to read and filter

class AnovaApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.outcome_var_name = None
        self.anova = None
        self.regressors_model = braviz_models.AnovaRegressorsModel()
        self.result_model = braviz_models.AnovaResultsModel()
        self.sample_model = braviz_models.SampleTree()
        self.plot = None
        self.plot_data_frame = None
        self.plot_x_var = None
        self.plot_z_var = None
        self.plot_color = None
        self.last_viewed_subject = None
        self.mri_viewer_pipe = None
        self.mri_viewer_process = None
        self.poll_timer = None
        self.ui = None
        self.setup_gui()


    def setup_gui(self):
        self.ui = Ui_Anova_gui()
        self.ui.setupUi(self)
        self.ui.outcome_sel.insertSeparator(self.ui.outcome_sel.count()-1)
        self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
        #self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.pressed.connect(self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(self.launch_regressors_context_menu)
        self.ui.add_interaction_button.pressed.connect(self.dispatch_interactions_dialog)
        self.ui.calculate_button.pressed.connect(self.calculate_anova)
        self.ui.results_table.setModel(self.result_model)

        self.ui.matplot_layout = QtGui.QVBoxLayout()
        self.plot = MatplotWidget(initial_message="Welcome\n\nSelect Outcome and add Regressors to start")
        self.ui.matplot_layout.addWidget(self.plot)
        self.ui.plot_frame.setLayout(self.ui.matplot_layout)
        self.plot.box_outlier_pick_signal.connect(self.handle_box_outlier_pick)
        self.plot.scatter_pick_signal.connect(self.handle_scatter_pick)
        self.plot.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.plot.customContextMenuRequested.connect(self.subject_details_from_plot)
        self.ui.results_table.activated.connect(self.update_main_plot_from_results)
        self.ui.reg_table.activated.connect(self.update_main_plot_from_regressors)

        self.ui.sample_tree.setModel(self.sample_model)
        self.ui.sample_tree.activated.connect(self.add_subjects_to_plot)
        self.ui.sample_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.sample_tree.customContextMenuRequested.connect(self.subject_details_from_tree)
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.timeout.connect(self.poll_messages_from_mri_viewer)



    def dispatch_outcome_select(self):

        #print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count() - 1:
            #print "dispatching dialog"
            params = {}
            dialog = OutcomeSelectDialog(params)
            selection = dialog.exec_()
            if selection > 0:
                self.set_outcome_var_type(params["selected_outcome"])
            else:
                self.set_outcome_var_type(None)
        else:
            self.set_outcome_var_type(self.ui.outcome_sel.itemText(self.ui.outcome_sel.currentIndex()))

    def dispatch_interactions_dialog(self):
        interaction_dialog = InteractionSelectDialog(self.regressors_model)
        interaction_dialog.exec_()
        self.regressors_model.show_regressors(True)
        try:
            ints = self.regressors_model.get_interactions()[-1]
        except (KeyError, IndexError):
            return
        if type(ints) == str or type(ints) == unicode:
            self.update_main_plot(ints)
        elif len(ints) > 0:
            self.update_main_plot(ints[-1])

    def set_outcome_var_type(self, new_bar):
        if new_bar is None:
            var_type_text = "Type"
            self.ui.outcome_type.setText(var_type_text)
            self.outcome_var_name = None
            #self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
            return
        new_bar = unicode(new_bar)
        if new_bar == self.outcome_var_name:
            return
        print "succesfully selected %s" % new_bar
        index = self.ui.outcome_sel.findText(new_bar)
        if index < 0:
            self.ui.outcome_sel.setCurrentIndex(index)
            self.ui.outcome_sel.insertItem(0, new_bar)
            index = 0
            pass
        self.outcome_var_name = new_bar
        self.ui.outcome_sel.setCurrentIndex(index)
        conn = get_connection()
        try:
            var_is_real = conn.execute("SELECT is_real FROM variables WHERE var_name = ? ;", (new_bar,)).fetchone()[0]
        except TypeError:
            var_type_text = "Type"
        else:
            var_type_text = "Real" if var_is_real else "Nominal"
        self.ui.outcome_type.setText(var_type_text)
        self.check_if_ready()

    def launch_add_regressor_dialog(self):
        reg_dialog = RegressorSelectDialog(self.outcome_var_name, self.regressors_model)
        result = reg_dialog.exec_()
        if self.regressors_model.rowCount() > 0:
            regn = self.regressors_model.get_regressors()[-1]
            self.update_main_plot(regn)
        self.check_if_ready()

    def check_if_ready(self):
        if (self.outcome_var_name is not None) and (self.regressors_model.rowCount() > 0):
            self.ui.calculate_button.setEnabled(True)
        else:
            self.ui.calculate_button.setEnabled(False)

    def launch_regressors_context_menu(self, pos):
        global_pos = self.ui.reg_table.mapToGlobal(pos)
        selection = self.ui.reg_table.currentIndex()
        remove_action = QtGui.QAction("Remove", None)
        menu = QtGui.QMenu()
        menu.addAction(remove_action)

        def remove_item(*args):
            self.regressors_model.removeRows(selection.row(), 1)

        remove_action.triggered.connect(remove_item)
        menu.addAction(remove_action)
        selected_item = menu.exec_(global_pos)

    def update_sample_info(self):
        #TODO: Allow choosing different sub-samples
        pass

    def calculate_anova(self):

        try:
            self.anova = braviz.interaction.r_functions.calculate_anova(self.outcome_var_name,
                                                                        self.regressors_model.get_data_frame(),
                                                                        self.regressors_model.get_interactors_dict())
        except Exception as e:
            msg = QtGui.QMessageBox()
            msg.setText(str(e.message))
            msg.setIcon(msg.Warning)
            msg.setWindowTitle("Anova Error")
            msg.exec_()
            raise
        else:
            self.result_model = braviz_models.AnovaResultsModel(*self.anova)
            self.ui.results_table.setModel(self.result_model)
            self.update_main_plot("Residuals")

    def update_main_plot_from_results(self, index):
        row = index.row()
        var_name_index = self.result_model.index(row, 0)
        var_name = unicode(self.result_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.update_main_plot(var_name)

    def update_main_plot_from_regressors(self, index):
        row = index.row()
        var_name_index = self.regressors_model.index(row, 0)
        var_name = unicode(self.regressors_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.update_main_plot(var_name)

    def update_main_plot(self, var_name):
        self.plot_x_var = None
        self.plot_data_frame = None
        self.plot_z_var = None
        self.plot_color = None
        if self.outcome_var_name is None:
            return
        if var_name == "Residuals":
            residuals = self.result_model.residuals
            self.plot.make_histogram(residuals, "Residuals")
            pass
        elif var_name == "(Intercept)":
            data = get_data_frame_by_name(self.outcome_var_name)
            self.plot_data_frame = data
            data_values = data[self.outcome_var_name].get_values()

            conn = get_connection()
            #get outcome min and max values
            cur = conn.execute("SELECT min_val, max_val FROM ratio_meta NATURAL JOIN variables WHERE var_name=?",
                               (self.outcome_var_name,))
            ylims = cur.fetchone()
            self.plot.make_box_plot([data_values], "(Intercept)", self.outcome_var_name,
                                    None, ylims,intercet=self.result_model.intercept)

        else:
            if ":" in var_name:
                factors = var_name.split(":")
                self.two_factors_plot(factors[:2])
            elif "*" in var_name:
                factors = var_name.split("*")
                self.two_factors_plot(factors[:2])
            else:
                self.one_reg_plot(var_name)

    def two_factors_plot(self, factors_list):
        nominal_factors = []
        real_factors = []
        conn = get_connection()
        #classify factors
        for f in factors_list:
            is_real = conn.execute("SELECT is_real FROM variables WHERE var_name=?", (f,))
            is_real = is_real.fetchone()[0]
            if is_real == 0:
                nominal_factors.append(f)
            else:
                real_factors.append(f)
        #print nominal_factors
        #print real_factors
        if len(real_factors) == 1:

            labels = conn.execute(
                "SELECT nom_meta.label, nom_meta.name FROM variables NATURAL JOIN nom_meta WHERE var_name = ?",
                (nominal_factors[0],))
            top_labels_dict = dict(labels.fetchall())
            colors = colorbrewer.Dark2[max(len(top_labels_dict), 3)]
            #print top_labels_strings
            if len(top_labels_dict) == 2:
                colors = colors[:2]
            colors = [map(lambda x: x / 255, c) for c in colors]
            colors_dict = dict(izip(top_labels_dict.iterkeys(), colors))
            self.plot_color = colors_dict
            self.plot_z_var = nominal_factors[0]
            #Get Data
            data = get_data_frame_by_name([real_factors[0], nominal_factors[0], self.outcome_var_name])
            data.dropna(inplace=True)
            self.plot_data_frame = data
            datax = []
            datay = []
            colors = []
            labels = []
            urls = []
            for k, v in top_labels_dict.iteritems():
                labels.append(v)
                colors.append(colors_dict[k])
                datay.append(data[self.outcome_var_name][data[nominal_factors[0]] == k].get_values())
                datax.append(data[real_factors[0]][data[nominal_factors[0]] == k].get_values())
                urls.append(data[self.outcome_var_name][data[nominal_factors[0]] == k].index.get_values())
            #print datax
            self.plot_x_var = real_factors[0]

            self.plot.compute_scatter(datax, datay, real_factors[0], self.outcome_var_name, colors, labels, urls=urls)


        elif len(real_factors) == 2:
            print "Not yet implemented"
        else:
            #find number of levels for nominal
            nlevels = {}
            for f in nominal_factors:
                n = conn.execute("SELECT count(*) FROM variables NATURAL JOIN nom_meta WHERE var_name=?", (f,))
                nlevels[f] = n.fetchone()[0]
            #print nlevels
            nominal_factors.sort(key=nlevels.get, reverse=True)
            #print nominal_factors
            data = get_data_frame_by_name(nominal_factors + [self.outcome_var_name])
            self.plot_data_frame = data
            levels_second_factor = set(data[nominal_factors[1]].get_values())
            levels_first_factor = set(data[nominal_factors[0]].get_values())
            data_lists_top = []
            for i in levels_second_factor:
                data_list = []
                for j in levels_first_factor:
                    data_col = data[self.outcome_var_name][(data[nominal_factors[1]] == i) &
                                                           (data[nominal_factors[0]] == j)].get_values()
                    data_list.append(data_col)
                data_lists_top.append(data_list)
            #print data_lists_top
            labels = conn.execute(
                "SELECT nom_meta.label, nom_meta.name FROM variables NATURAL JOIN nom_meta WHERE var_name = ?",
                (nominal_factors[0],))
            labels_dict = dict(labels.fetchall())
            labels_strings = [labels_dict[i] for i in levels_first_factor]
            labels = conn.execute(
                "SELECT nom_meta.label, nom_meta.name FROM variables NATURAL JOIN nom_meta WHERE var_name = ?",
                (nominal_factors[1],))
            top_labels_dict = dict(labels.fetchall())
            top_labels_strings = [top_labels_dict[i] for i in levels_second_factor]
            colors = colorbrewer.Dark2[max(len(levels_second_factor), 3)]
            #print top_labels_strings
            if len(levels_second_factor) == 2:
                colors = colors[:2]
            colors = [map(lambda x: x / 255, c) for c in colors]
            self.plot_color = dict(izip(levels_second_factor, colors))
            self.plot_z_var = nominal_factors[1]
            #print colors
            #get ylims
            cur = conn.execute("SELECT min_val , max_val FROM variables NATURAL JOIN ratio_meta WHERE var_name=?",
                               (self.outcome_var_name,))
            miny, maxy = cur.fetchone()
            if miny is None or maxy is None:
                raise Exception("Incosistency in DB")

            self.plot_x_var = nominal_factors[0]
            self.plot.make_linked_box_plot(data_lists_top, nominal_factors[0], self.outcome_var_name, labels_strings,
                                           colors, top_labels_strings, ylims=(miny, maxy))


    def one_reg_plot(self, var_name):
        #find if variable is nominal

        is_reg_real = braviz_tab_data.is_variable_name_real(var_name)
        #get outcome min and max values
        #TODO This has to be updatede when implementing logistic regression
        miny, maxy = braviz_tab_data.get_min_max_values_by_name(self.outcome_var_name)
        self.plot_x_var = var_name
        if is_reg_real == 0:
            #is nominal
            #create whisker plot
            labels_dict = braviz_tab_data.get_names_label_dict(var_name)
            #print labels_dict
            #get data from
            data = get_data_frame_by_name([self.outcome_var_name, var_name])
            self.plot_data_frame = data
            label_nums = set(data[var_name])
            data_list = []
            ticks = []
            for i in label_nums:
                data_col = data[self.outcome_var_name][data[var_name] == i]
                data_list.append(data_col.get_values())
                ticks.append(labels_dict.get(i, str(i)))
            #print data_list
            self.plot.make_box_plot(data_list, var_name, self.outcome_var_name, ticks, (miny, maxy))

        else:
            #is real
            #create scatter plot
            data = get_data_frame_by_name([self.outcome_var_name, var_name])
            data.dropna(inplace=True)
            self.plot_data_frame = data
            self.plot.compute_scatter(data[var_name].get_values(),
                                      data[self.outcome_var_name].get_values(),
                                      var_name,
                                      self.outcome_var_name, urls=data.index.get_values())

    def add_subjects_to_plot(self, index=None,subject_ids=None):
        #find selected subjects
        if subject_ids is None:
            selection = self.ui.sample_tree.currentIndex()
            leafs = self.sample_model.get_leafs(selection)
            subject_ids = map(int, leafs)

        #get data
        #print subject_ids
        if self.plot_data_frame is None:
            return
        y_data = self.plot_data_frame[self.outcome_var_name][subject_ids].get_values()
        subject_ids = self.plot_data_frame[self.outcome_var_name][subject_ids].index.get_values()
        if self.plot_x_var is None:
            x_data = np.ones(y_data.shape)
        else:
            x_data = self.plot_data_frame[self.plot_x_var][subject_ids].get_values()
        colors = None
        if self.plot_z_var is not None and self.plot_color is not None:
            z_data = self.plot_data_frame[self.plot_z_var][subject_ids].get_values()
            colors = [self.plot_color[i] for i in z_data]
        self.plot.add_subject_points(x_data, y_data, colors, urls=subject_ids)

    def poll_messages_from_mri_viewer(self):
        #print "polling"
        if self.mri_viewer_process is None or (self.mri_viewer_process.poll() is not None):
            #stop timer
            self.poll_timer.stop()
            return
        if self.mri_viewer_pipe.poll():
            message = self.mri_viewer_pipe.recv()
            subj = message.get('subject')
            if subj is not None:
                print "showing subject %s"%subj
                self.add_subjects_to_plot(subject_ids=[int(subj)])


    def handle_box_outlier_pick(self, x, y, position):
        #print "received signal"
        #print x_l,y_l
        if self.plot_data_frame is not None:
            #identify subject
            df = self.plot_data_frame
            if self.plot_x_var is None:
                subj = df[df[self.outcome_var_name] == y].index
            else:
                subj = df[(df[self.plot_x_var] == x) & (df[self.outcome_var_name] == y)].index
            #print subj[0]
            message = "Outlier: %s" % subj[0]
            self.last_viewed_subject = subj[0]
            QtCore.QTimer.singleShot(2000, self.clear_last_viewed_subject)
            QtGui.QToolTip.showText(self.plot.mapToGlobal(QtCore.QPoint(*position)), message, self.plot)

    def handle_scatter_pick(self, subj, position):
        message = "Subject: %s" % subj
        QtGui.QToolTip.showText(self.plot.mapToGlobal(QtCore.QPoint(*position)), message, self.plot)
        self.last_viewed_subject = subj
        QtCore.QTimer.singleShot(2000, self.clear_last_viewed_subject)

    def create_view_details_context_menu(self, global_pos, subject=None):
        #TODO: Open images of a given subject
        if subject is None:
            subject = self.last_viewed_subject
            if subject is None:
                return

        def show_MRI(*args):
            self.change_subject_in_mri_viewer(subject)

        launch_mri_action = QtGui.QAction("Show subject %s MRI" % subject, None)
        menu = QtGui.QMenu("Subject %s" % subject)
        menu.addAction(launch_mri_action)
        launch_mri_action.triggered.connect(show_MRI)
        menu.addAction(launch_mri_action)
        menu.exec_(global_pos)

    def subject_details_from_plot(self, pos):
        #print "context menu"
        #print pos
        global_pos = self.plot.mapToGlobal(pos)
        self.create_view_details_context_menu(global_pos)

    def subject_details_from_tree(self, pos):
        global_pos = self.ui.sample_tree.mapToGlobal(pos)
        selection = self.ui.sample_tree.currentIndex()
        selection = self.sample_model.index(selection.row(), 0, selection.parent())
        #check if it is a leaf
        if self.sample_model.hasChildren(selection) is True:
            return
        else:
            #print "this is a leaf"
            subject = self.sample_model.data(selection, QtCore.Qt.DisplayRole)
            #print subject
            self.create_view_details_context_menu(global_pos, subject)

    def clear_last_viewed_subject(self):
        self.last_viewed_subject = None

    def launch_mri_viewer(self):
        print
        #TODO: think of better way of choicing ports
        address = ('localhost',6001)
        auth_key=multiprocessing.current_process().authkey
        rand_char = "%c"%random.randint(0,255)
        auth_key.replace("\x00",rand_char)
        listener = multiprocessing.connection.Listener(address,authkey=auth_key)

        #self.mri_viewer_process = multiprocessing.Process(target=mriMultSlicer.launch_new, args=(pipe_mri_side,))
        print [sys.executable,"-m","braviz.applications.subject_overview",auth_key]
        self.mri_viewer_process = subprocess.Popen([sys.executable,"-m","braviz.applications.subject_overview",auth_key])

        #self.mri_viewer_process = multiprocessing.Process(target=subject_overview.run, args=(pipe_mri_side,))
        #self.mri_viewer_process.start()
        self.mri_viewer_pipe = listener.accept()
        self.poll_timer.start(200)

    def change_subject_in_mri_viewer(self, subj):
        if (self.mri_viewer_process is None) or (self.mri_viewer_process.poll() is not None):
            self.launch_mri_viewer()
        if self.mri_viewer_pipe is not None:
            self.mri_viewer_pipe.send({'subject': str(subj), 'lift': True})
            print "sending message: subj:", str(subj)

    def closeEvent(self, *args, **kwargs):
        if self.mri_viewer_process is not None:
            self.mri_viewer_process.terminate()
        print "ciao"


def run():
    import sys
    app = QtGui.QApplication(sys.argv)
    main_window = AnovaApp()
    main_window.show()
    app.exec_()

if __name__ == '__main__':
    run()
