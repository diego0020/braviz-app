from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow
import numpy as np

from braviz.interaction.qt_guis.anova import Ui_Anova_gui
import braviz.interaction.qt_dialogs
import braviz.interaction.qt_sample_select_dialog
from braviz.interaction.qt_dialogs import OutcomeSelectDialog, RegressorSelectDialog, MatplotWidget,\
    InteractionSelectDialog

import braviz.interaction.r_functions

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_connection, get_data_frame_by_name
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data

import colorbrewer

from itertools import izip

import multiprocessing
import multiprocessing.connection
import subprocess
import sys
import binascii
import datetime
import os
import platform

import logging
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
        self.plot_var_name = None
        self.last_viewed_subject = None
        self.mri_viewer_pipe = None
        self.mri_viewer_process = None
        self.poll_timer = None
        self.sample = braviz_tab_data.get_subjects()
        self.ui = None
        self.setup_gui()


    def setup_gui(self):
        self.ui = Ui_Anova_gui()
        self.ui.setupUi(self)
        self.ui.outcome_sel.insertSeparator(self.ui.outcome_sel.count()-1)
        self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
        #self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.clicked.connect(self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(self.launch_regressors_context_menu)
        self.ui.add_interaction_button.clicked.connect(self.dispatch_interactions_dialog)
        self.ui.calculate_button.clicked.connect(self.calculate_anova)
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
        self.ui.modify_sample_button.clicked.connect(self.load_sample)
        self.ui.modify_sample_button.setEnabled(True)
        self.poll_timer = QtCore.QTimer(self)
        self.poll_timer.timeout.connect(self.poll_messages_from_mri_viewer)

        self.ui.actionSave_scneario.triggered.connect(self.save_scenario_dialog)
        self.ui.actionLoad_scenario.triggered.connect(self.load_scenario_dialog)
        self.ui.actionImages.triggered.connect(self.save_figure)
        self.ui.actionData.triggered.connect(self.save_data)


    def dispatch_outcome_select(self):

        #print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count() - 1:
            #print "dispatching dialog"
            params = {}
            dialog = OutcomeSelectDialog(params,sample=self.sample)
            selection = dialog.exec_()
            logger = logging.getLogger(__name__)
            logger.info("Outcome selection %s",params)
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
        log = logging.getLogger(__name__)
        if new_bar is None:
            var_type_text = "Type"
            self.ui.outcome_type.setText(var_type_text)
            self.outcome_var_name = None
            #self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
            return
        new_bar = unicode(new_bar)
        if new_bar == self.outcome_var_name:
            return
        log.debug("succesfully selected %s" % new_bar)
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
        reg_dialog = RegressorSelectDialog(self.outcome_var_name, self.regressors_model,sample=self.sample)
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


    def calculate_anova(self):
        log = logging.getLogger(__name__)
        log.info("calculating anova")
        try:
            self.anova = braviz.interaction.r_functions.calculate_anova(self.outcome_var_name,
                                                                        self.regressors_model.get_data_frame(),
                                                                        self.regressors_model.get_interactors_dict(),
                                                                        self.sample)
        except Exception as e:
            msg = QtGui.QMessageBox()
            msg.setText(str(e.message))
            msg.setIcon(msg.Warning)
            msg.setWindowTitle("Anova Error")
            log.warning("Anova Error")
            log.exception(e)
            msg.exec_()
            #raise
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
        self.plot_var_name = var_name
        self.plot_x_var = None
        self.plot_data_frame = None
        self.plot_z_var = None
        self.plot_color = None
        if self.outcome_var_name is None:
            return
        if var_name == "Residuals":
            residuals = self.result_model.residuals
            fitted = self.result_model.fitted
            self.plot.make_diagnostics(residuals,fitted)
            pass
        elif var_name == "(Intercept)":
            data = get_data_frame_by_name(self.outcome_var_name)
            data = data.loc[self.sample]

            self.plot_data_frame = data
            data_values = data[self.outcome_var_name].get_values()

            ylims = braviz_tab_data.get_min_max_values_by_name(self.outcome_var_name)
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
        #classify factors
        for f in factors_list:
            is_real = braviz_tab_data.is_variable_name_real(f)
            if is_real == 0:
                nominal_factors.append(f)
            else:
                real_factors.append(f)
        #print nominal_factors
        #print real_factors
        if len(real_factors) == 1:

            top_labels_dict = braviz_tab_data.get_names_label_dict(nominal_factors[0])
            colors = colorbrewer.Dark2[max(len(top_labels_dict), 3)]
            #print top_labels_strings
            if len(top_labels_dict) == 2:
                colors = colors[:2]
            colors = [map(lambda x: x / 255, c) for c in colors]
            colors_dict = dict(izip(top_labels_dict.iterkeys(), colors))
            self.plot_color = colors_dict
            #Get Data
            data = get_data_frame_by_name([real_factors[0], nominal_factors[0], self.outcome_var_name])
            data = data.loc[self.sample]
            self.plot_data_frame = data
            data.dropna(inplace=True)
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
            self.plot_z_var = nominal_factors[0]


            self.plot.compute_scatter(datax, datay, real_factors[0], self.outcome_var_name, colors, labels, urls=urls)


        elif len(real_factors) == 2:
            log = logging.getLogger(__name__)
            log.warning("Not yet implemented")
            self.plot.initial_text("Not yet implemented")
        else:
            #get data
            data = get_data_frame_by_name(nominal_factors + [self.outcome_var_name])
            #find number of levels for nominal
            nlevels = {}
            for f in nominal_factors:
                nlevels[f] = len(data[f].unique())
            #print nlevels
            nominal_factors.sort(key=nlevels.get, reverse=True)
            #print nominal_factors
            data = data.loc[self.sample]
            self.plot_data_frame = data

            data.dropna(inplace=True)
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

            #get ylims
            miny, maxy = braviz_tab_data.get_min_max_values_by_name(self.outcome_var_name)
            if miny is None or maxy is None:
                log = logging.getLogger(__name__)
                log.critical("Incosistency in DB")
                raise Exception("Incosistency in DB")

            self.plot_x_var = nominal_factors[0]
            self.plot_z_var = nominal_factors[1]
            self.plot.make_linked_box_plot(data, self.outcome_var_name, nominal_factors[0], nominal_factors[1],
                                           ylims=(miny, maxy))


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
            label_nums = set(data[var_name])
            data = data.loc[self.sample]

            self.plot_data_frame = data

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
            data = data.loc[self.sample]

            self.plot_data_frame = data
            data.dropna(inplace=True)
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
        df = self.plot_data_frame.loc[subject_ids]
        df = df.dropna()
        y_data = df[self.outcome_var_name].get_values()
        subject_ids = df.index.get_values()
        if self.plot_x_var is None:
            x_data = np.ones(y_data.shape)
        else:
            x_data = df[self.plot_x_var].get_values()
        z_data = None
        colors = None
        if self.plot_z_var is not None:
            z_data = df[self.plot_z_var].get_values()
            if self.plot_color is not None:
                colors = [self.plot_color[i] for i in z_data]

        self.plot.add_subject_points(x_data, y_data,z_data, colors,urls=subject_ids)

    def poll_messages_from_mri_viewer(self):
        #print "polling"
        log = logging.getLogger(__name__)
        if self.mri_viewer_process is None or (self.mri_viewer_process.poll() is not None):
            #stop timer
            self.poll_timer.stop()
            return
        if self.mri_viewer_pipe.poll():
            try:
                message = self.mri_viewer_pipe.recv()
            except EOFError:
                #process should have ended

                log.info("Pipe closed")
                self.mri_viewer_process = None
                self.mri_viewer_pipe = None
                return
            subj = message.get('subject')
            if subj is not None:
                log.info("showing subject %s"%subj)
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

    def create_context_action(self,subject,scenario_id,scenario_name,show_name = None):
        if show_name is None:
            show_name = scenario_name
        def show_scenario():
            self.change_subject_in_mri_viewer(subject,scenario_id)
        action = QtGui.QAction("Show subject %s's %s" % (subject,show_name), None)
        action.triggered.connect(show_scenario)
        return action

    def create_view_details_context_menu(self, global_pos, subject=None):
        #TODO: Open images of a given subject
        if subject is None:
            subject = self.last_viewed_subject
            if subject is None:
                return

        scenarios = {}
        outcome_idx = braviz_tab_data.get_var_idx(self.outcome_var_name)
        outcome_scenarios = braviz_user_data.get_variable_scenarios(outcome_idx)
        if len(outcome_scenarios)>0:
            scenarios[self.outcome_var_name]=outcome_scenarios.items()
        regressors = self.regressors_model.get_regressors()
        for reg in regressors:
            reg_idx = braviz_tab_data.get_var_idx(reg)
            reg_scenarios = braviz_user_data.get_variable_scenarios(reg_idx)
            if len(reg_scenarios):
                scenarios[reg]=reg_scenarios.items()

        menu = QtGui.QMenu("Subject %s" % subject)
        launch_mri_action = self.create_context_action(subject,None,"MRI")
        menu.addAction(launch_mri_action)

        log = logging.getLogger(__name__)
        log.debug(scenarios)
        for var,scn_lists in scenarios.iteritems():
            for scn_id,scn_name in scn_lists:
                action = self.create_context_action(subject,scn_id,scn_name,var)
                menu.addAction(action)

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
        log = logging.getLogger(__name__)
        #TODO: think of better way of choicing ports
        address = ('localhost',6001)
        auth_key=multiprocessing.current_process().authkey
        auth_key_asccii = binascii.b2a_hex(auth_key)
        listener = multiprocessing.connection.Listener(address,authkey=auth_key)

        #self.mri_viewer_process = multiprocessing.Process(target=mriMultSlicer.launch_new, args=(pipe_mri_side,))
        log.info("launching viewer")
        log.info([sys.executable,"-m","braviz.applications.subject_overview","0",auth_key_asccii])
        self.mri_viewer_process = subprocess.Popen([sys.executable,"-m","braviz.applications.subject_overview",
                                                    "0",auth_key_asccii])

        #self.mri_viewer_process = multiprocessing.Process(target=subject_overview.run, args=(pipe_mri_side,))
        #self.mri_viewer_process.start()
        self.mri_viewer_pipe = listener.accept()
        self.poll_timer.start(200)

    def change_subject_in_mri_viewer(self, subj,scenario=None):
        log = logging.getLogger(__name__)
        if (self.mri_viewer_process is None) or (self.mri_viewer_process.poll() is not None):
            self.launch_mri_viewer()
        if self.mri_viewer_pipe is not None:
            message = {'subject': str(subj)}
            if scenario is not None:
                message["scenario"]=scenario
            self.mri_viewer_pipe.send(message)
            log.info("sending message: subj: %s", message)

    def closeEvent(self, *args, **kwargs):
        #if self.mri_viewer_process is not None:
            #self.mri_viewer_process.terminate()
        log = logging.getLogger(__name__)
        log.info("Finishing")

    def get_state(self):
        state = {}
        vars_state = {}
        vars_state["outcome"]=self.outcome_var_name
        vars_state["regressors"]=self.regressors_model.get_regressors()
        vars_state["interactions"]=self.regressors_model.get_interactions()
        state["vars"] = vars_state
        state["plot"] = {"var_name":self.plot_var_name}
        state["sample"] = self.sample

        meta = dict()
        meta["date"] = datetime.datetime.now()
        meta["exec"] = sys.argv
        meta["machine"] = platform.node()
        meta["application"] = os.path.splitext(os.path.basename(__file__))[0]
        state["meta"] = meta
        return state

    def save_scenario_dialog(self):
        state = self.get_state()
        params = {}
        app_name = state["meta"]["application"]
        dialog = braviz.interaction.qt_dialogs.SaveScenarioDialog(app_name,state,params)
        res=dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            #save main plot as screenshot
            scn_id = params["scn_id"]
            pixmap = QtGui.QPixmap.grabWidget(self.plot)
            file_name = "scenario_%d.png"%scn_id
            data_root = braviz.readAndFilter.kmc40_auto_data_root()
            file_path = os.path.join(data_root, "braviz_data","scenarios",file_name)
            log.info(file_path)
            pixmap.save(file_path)
        log.info("saving")
        log.info(state)

    def load_scenario_dialog(self):
        app_name = os.path.splitext(os.path.basename(__file__))[0]
        wanted_state = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(app_name,wanted_state)
        res= dialog.exec_()
        log = logging.getLogger(__name__)
        if res==dialog.Accepted:
            log.info("Loading state")
            log.info(wanted_state)
            self.restore_state(wanted_state)

    def restore_state(self,wanted_state):
        #restore outcome
        #sample
        logger = logging.getLogger(__name__)
        logger.info("loading state %s",wanted_state)
        sample = wanted_state.get("sample")
        if sample is not None:
            self.sample = sample
            self.sample_model.set_sample(sample)
        self.ui.calculate_button.setEnabled(0)
        reg_name = wanted_state["vars"].get("outcome")
        if reg_name is not None:
            index = self.ui.outcome_sel.findText(reg_name)
            if index >=0:
                self.ui.outcome_sel.setCurrentIndex(index)
            else:
                self.ui.outcome_sel.insertItem(0,reg_name)
                self.ui.outcome_sel.setCurrentIndex(0)
        self.set_outcome_var_type(reg_name)
        #restore regressors
        regressors = wanted_state["vars"].get("regressors",tuple())
        self.regressors_model.reset_data(regressors)
        #restore interactions
        interactions = wanted_state["vars"].get("interactions",tuple())
        #TODO: Must find a better way to encode interactions
        for inter in interactions:
            tokens = inter.split("*")
            self.regressors_model.add_interactor_by_names(tokens)
        self.regressors_model.show_interactions(True)
        self.regressors_model.show_regressors(True)
        #calculate anova
        self.check_if_ready()
        if self.ui.calculate_button.isEnabled():
            self.calculate_anova()
        #set plot
        plot_name = wanted_state["plot"].get("var_name")
        if plot_name is not None:
            self.update_main_plot(plot_name)

    def load_sample(self):
        dialog = braviz.interaction.qt_sample_select_dialog.SampleLoadDialog()
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            log.info("new sample")
            log.info(new_sample)
            self.sample = new_sample
            self.sample_model.set_sample(new_sample)
            self.update_main_plot(self.plot_var_name)

    def save_figure(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                 "Save Plot",".","PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.plot.fig.savefig(filename)

    def save_data(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                             "Save Data",".","csv (*.csv)"))
        vars = [self.outcome_var_name]+list(self.regressors_model.get_regressors())
        out_df = braviz_tab_data.get_data_frame_by_name(vars)
        out_df.to_csv(filename)

def run():
    import sys
    from braviz.utilities import configure_logger
    configure_logger("anova_app")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = AnovaApp()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()
