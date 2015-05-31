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

from braviz.utilities import set_pyqt_api_2

set_pyqt_api_2()

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow
import numpy as np

from braviz.interaction.qt_guis.anova import Ui_Anova_gui
import braviz.interaction.qt_dialogs
import braviz.applications.sample_select
from braviz.interaction.qt_dialogs import MultiPlotOutcomeSelectDialog, RegressorSelectDialog, InteractionSelectDialog

import braviz.interaction.r_functions
from braviz.interaction.connection import MessageClient, MessageServer
from braviz.readAndFilter.config_file import get_config

import braviz.interaction.qt_models as braviz_models
from braviz.readAndFilter.tabular_data import get_data_frame_by_name
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data

import seaborn as sns

from itertools import izip

import sys
import datetime
import os
import platform

import logging
from braviz.interaction.qt_widgets import MatplotWidget
from braviz.utilities import launch_sub_process

__author__ = 'Diego'

config = get_config(__file__)
def_vars = config.get_default_variables()
INITIAL_OUTCOMES = map(
    braviz_tab_data.get_var_idx, [def_vars["ratio1"], def_vars["ratio2"]])
INITIAL_OUTCOMES = filter(lambda x: x is not None, INITIAL_OUTCOMES)

SAMPLE_TREE_COLUMNS = (def_vars["nom1"], def_vars["nom2"])


class AnovaApp(QMainWindow):
    def __init__(self, scenario, server_broadcast_address, server_receive_address):
        QMainWindow.__init__(self)
        self.outcome_var_name = None
        self.anova = None
        self.regressors_model = braviz_models.AnovaRegressorsModel()
        self.result_model = braviz_models.AnovaResultsModel()
        self.sample_model = braviz_models.SampleTree(SAMPLE_TREE_COLUMNS)
        self.plot = None
        self.plot_data_frame = None
        self.plot_x_var = None
        self.plot_z_var = None
        self.plot_color = None
        self.plot_var_name = None
        self.last_viewed_subject = None
        self.mri_viewer_pipe = None
        self.sample = braviz_tab_data.get_subjects()
        self.missing = None
        self.sample_message_policy = "ask"
        self.ui = None

        if server_broadcast_address is not None or server_receive_address is not None:
            self._message_client = MessageClient(
                server_broadcast_address, server_receive_address)
            self._message_client.message_received.connect(self.receive_message)
        else:
            self._message_client = None

        self.setup_gui()
        if scenario is not None:
            scn_int = int(scenario)
            if scn_int > 0:
                self.load_scenario_id(scenario)

    def setup_gui(self):
        self.ui = Ui_Anova_gui()
        self.ui.setupUi(self)
        for v_idx in INITIAL_OUTCOMES:
            self.ui.outcome_sel.insertItem(
                0, braviz_tab_data.get_var_name(v_idx))
        self.ui.outcome_sel.insertSeparator(self.ui.outcome_sel.count() - 1)
        self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count() - 1)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.clicked.connect(
            self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(
            self.launch_regressors_context_menu)
        self.ui.add_interaction_button.clicked.connect(
            self.dispatch_interactions_dialog)
        self.ui.calculate_button.clicked.connect(self.calculate_anova)
        self.ui.results_table.setModel(self.result_model)

        self.ui.matplot_layout = QtGui.QVBoxLayout()
        self.plot = MatplotWidget(
            initial_message="Welcome\n\nSelect Outcome and add Regressors to start")
        self.ui.matplot_layout.addWidget(self.plot)
        self.ui.plot_frame.setLayout(self.ui.matplot_layout)
        self.plot.box_outlier_pick_signal.connect(self.handle_box_outlier_pick)
        self.plot.scatter_pick_signal.connect(self.handle_scatter_pick)
        self.plot.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.plot.customContextMenuRequested.connect(
            self.subject_details_from_plot)
        self.ui.results_table.activated.connect(
            self.update_main_plot_from_results)
        self.ui.reg_table.activated.connect(
            self.update_main_plot_from_regressors)

        self.ui.sample_tree.setModel(self.sample_model)
        self.ui.sample_tree.activated.connect(self.add_subjects_to_plot)
        self.ui.sample_tree.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.sample_tree.customContextMenuRequested.connect(
            self.subject_details_from_tree)
        self.ui.modify_sample_button.clicked.connect(self.modify_sample)
        self.ui.modify_sample_button.setEnabled(True)

        self.ui.actionSave_scneario.triggered.connect(
            self.save_scenario_dialog)
        self.ui.actionLoad_scenario.triggered.connect(
            self.load_scenario_dialog)
        self.ui.actionLoad_sample.triggered.connect(self.load_sample)
        self.ui.actionImages.triggered.connect(self.save_figure)
        self.ui.actionData.triggered.connect(self.save_data)

        self.ui.actionAsk.triggered.connect(lambda: self.update_samples_policy("ask"))
        self.ui.actionNever.triggered.connect(lambda: self.update_samples_policy("never"))
        self.ui.actionAlways.triggered.connect(lambda: self.update_samples_policy("always"))
        self.ui.actionSend_sample.triggered.connect(self.send_sample)

    def dispatch_outcome_select(self):

        # print "outcome select %s /
        # %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count() - 1:
            # print "dispatching dialog"
            params = {}
            plots = self.__create_plots_dictionary()
            dialog = MultiPlotOutcomeSelectDialog(
                params, sample=self.sample, available_plots=plots)
            selection = dialog.exec_()
            logger = logging.getLogger(__name__)
            logger.info("Outcome selection %s", params)
            if selection > 0:
                self.set_outcome_var_type(params["selected_outcome"])
            else:
                self.set_outcome_var_type(None)
        else:
            self.set_outcome_var_type(
                self.ui.outcome_sel.itemText(self.ui.outcome_sel.currentIndex()))

    def __create_plots_dictionary(self):
        regs_df = self.regressors_model.get_data_frame()
        plots = dict()
        for i, row in regs_df.iterrows():
            var_name = row["variable"]
            interaction = row["Interaction"]
            if interaction == 0:
                plots["x = '%s'" % var_name] = ("scatter", var_name)
                var_nominal = braviz_tab_data.is_variable_name_nominal(
                    var_name)
                if var_nominal:
                    plots["box (%s)" % var_name] = ("box", var_name)
            else:
                comps = var_name.split("*")
                if len(comps) == 2:
                    plots["Interaction (%s)" % var_name] = (
                        "interaction", var_name)

        return plots

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
            # self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
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
        try:
            var_is_real = braviz_tab_data.is_variable_name_real(new_bar)
        except TypeError:
            var_type_text = "Type"
        else:
            var_type_text = "Real" if var_is_real else "Nominal"
        self.ui.outcome_type.setText(var_type_text)
        self.update_main_plot(self.plot_var_name)
        self.check_if_ready()

    def launch_add_regressor_dialog(self):
        reg_dialog = RegressorSelectDialog(
            self.outcome_var_name, self.regressors_model, sample=self.sample)
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
        self.get_missing_values()

    def get_missing_values(self):
        a_vars = list(self.regressors_model.get_regressors())
        if self.outcome_var_name is not None:
            a_vars.append(self.outcome_var_name)
        whole_df = braviz_tab_data.get_data_frame_by_name(a_vars)
        whole_df = whole_df.loc[self.sample]
        whole_df.dropna(inplace=True)
        self.missing = len(self.sample) - len(whole_df)
        self.ui.missing_label.setText("Missing Values: %d" % self.missing)

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
                                                                        self.regressors_model.get_interactors_dict(
                                                                        ),
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
        var_name = unicode(
            self.result_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.update_main_plot(var_name)

    def update_main_plot_from_regressors(self, index):
        row = index.row()
        var_name_index = self.regressors_model.index(row, 0)
        var_name = unicode(
            self.regressors_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.update_main_plot(var_name)

    def update_main_plot(self, var_name):
        self.plot_var_name = var_name
        self.plot_x_var = None
        self.plot_data_frame = None
        self.plot_z_var = None
        self.plot_color = None
        if self.outcome_var_name is None:
            return
        if self.plot_var_name is None:
            return
        if var_name == "Residuals":
            residuals = self.result_model.residuals
            fitted = self.result_model.fitted
            self.plot.make_diagnostics(residuals, fitted)
            pass
        elif var_name == "(Intercept)":
            data = get_data_frame_by_name(self.outcome_var_name)
            data = data.loc[self.sample]
            data.dropna(inplace=True)

            self.plot_data_frame = data

            ylims = braviz_tab_data.get_min_max_values_by_name(
                self.outcome_var_name)
            self.plot.make_box_plot(data, None, self.outcome_var_name, "(Intercept)", self.outcome_var_name,
                                    None, ylims, intercet=self.result_model.intercept)

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
        # classify factors
        for f in factors_list:
            is_real = braviz_tab_data.is_variable_name_real(f)
            if is_real == 0:
                nominal_factors.append(f)
            else:
                real_factors.append(f)
            # print nominal_factors
        # print real_factors
        if len(real_factors) == 1:

            top_labels_dict = braviz_tab_data.get_labels_dict_by_name(
                nominal_factors[0])
            colors = sns.color_palette("Dark2", len(top_labels_dict))
            # print top_labels_strings
            colors_dict = dict(izip(top_labels_dict.iterkeys(), colors))
            self.plot_color = colors_dict
            # Get Data
            data = get_data_frame_by_name(
                [real_factors[0], nominal_factors[0], self.outcome_var_name])
            data = data.loc[self.sample]
            data.dropna(inplace=True)
            self.plot_data_frame = data

            datax = []
            datay = []
            colors = []
            labels = []
            urls = []
            for k, v in top_labels_dict.iteritems():
                if k is None:
                    continue
                if v is None:
                    v = "?"
                labels.append(v)
                colors.append(colors_dict[k])
                #raise NotImplementedError("Error here")
                datay.append(
                    data[self.outcome_var_name][data[nominal_factors[0]] == k].get_values())
                datax.append(
                    data[real_factors[0]][data[nominal_factors[0]] == k].get_values())
                urls.append(
                    data[self.outcome_var_name][data[nominal_factors[0]] == k].index.get_values())
                # print datax
            self.plot_x_var = real_factors[0]
            self.plot_z_var = nominal_factors[0]

            self.plot.compute_scatter(
                datax, datay, real_factors[0], self.outcome_var_name, colors, labels, urls=urls)

        elif len(real_factors) == 2:
            log = logging.getLogger(__name__)
            log.warning("Not yet implemented")
            self.plot.initial_text("Not yet implemented")
        else:
            # get data
            data = get_data_frame_by_name(
                nominal_factors + [self.outcome_var_name])
            data = data.loc[self.sample]
            data.dropna(inplace=True)
            # find number of levels for nominal
            nlevels = {}
            for f in nominal_factors:
                nlevels[f] = len(data[f].unique())
                # print nlevels
            nominal_factors.sort(key=nlevels.get, reverse=True)
            # print nominal_factors

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

            # get ylims
            miny, maxy = braviz_tab_data.get_min_max_values_by_name(
                self.outcome_var_name)
            if miny is None or maxy is None:
                log = logging.getLogger(__name__)
                log.critical("Incosistency in DB")
                raise Exception("Incosistency in DB")

            self.plot_x_var = nominal_factors[0]
            self.plot_z_var = nominal_factors[1]
            self.plot.make_linked_box_plot(data, self.outcome_var_name, nominal_factors[0], nominal_factors[1],
                                           ylims=(miny, maxy))

    def one_reg_plot(self, var_name):
        # find if variable is nominal

        is_reg_real = braviz_tab_data.is_variable_name_real(var_name)
        # get outcome min and max values
        miny, maxy = braviz_tab_data.get_min_max_values_by_name(
            self.outcome_var_name)
        self.plot_x_var = var_name

        if not is_reg_real:
            # is nominal
            # create whisker plot
            labels_dict = braviz_tab_data.get_labels_dict_by_name(var_name)
            for k, v in labels_dict.iteritems():
                if v is None or len(v) == 0:
                    labels_dict[k] = "level_%s" % k
                # print labels_dict
            # get data from
            data = get_data_frame_by_name([self.outcome_var_name, var_name])

            data = data.loc[self.sample]
            # remove nans
            data.dropna(inplace=True)

            self.plot_data_frame = data

            # print data_list
            self.plot.make_box_plot(
                data, var_name, self.outcome_var_name, var_name, self.outcome_var_name, labels_dict, (miny, maxy))

        else:
            # is real
            # create scatter plot
            data = get_data_frame_by_name([self.outcome_var_name, var_name])
            data = data.loc[self.sample]

            self.plot_data_frame = data
            data.dropna(inplace=True)
            self.plot.compute_scatter(data[var_name].get_values(),
                                      data[self.outcome_var_name].get_values(),
                                      var_name,
                                      self.outcome_var_name, urls=data.index.get_values())

    def add_subjects_to_plot(self, tree_indexes=None, subject_ids=None):
        # tree_indexes used when called from tree
        # find selected subjects
        if subject_ids is None:
            selection = self.ui.sample_tree.currentIndex()
            leafs = self.sample_model.get_leafs(selection)
            subject_ids = map(int, leafs)

        if not isinstance(subject_ids, list):
            subject_ids = list(subject_ids)

        # get data
        # print subject_ids
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

        self.plot.add_subject_points(
            x_data, y_data, z_data, colors, urls=subject_ids)

    def change_subject_in_mri_viewer(self, subj):
        log = logging.getLogger(__name__)
        subj = str(subj)
        msg1 = {"subject": subj}
        log.info(msg1)
        if self._message_client is not None:
            self._message_client.send_message(msg1)

    def receive_message(self, msg):
        log = logging.getLogger(__name__)
        log.info("RECEIVED %s" % msg)
        subj = msg.get("subject")
        if subj is not None:
            log.info("showing subject %s" % subj)
            self.add_subjects_to_plot(subject_ids=(int(subj),))
        if "sample" in msg:
            self.handle_sample_message(msg)

    def handle_box_outlier_pick(self, u, position):
        # print "received signal"
        # print x_l,y_l
        message = "Outlier: %s" % u
        self.last_viewed_subject = u
        QtCore.QTimer.singleShot(2000, self.clear_last_viewed_subject)
        QtGui.QToolTip.showText(
            self.plot.mapToGlobal(QtCore.QPoint(*position)), message, self.plot)

    def handle_scatter_pick(self, subj, position):
        message = "Subject: %s" % subj
        QtGui.QToolTip.showText(
            self.plot.mapToGlobal(QtCore.QPoint(*position)), message, self.plot)
        self.last_viewed_subject = subj
        QtCore.QTimer.singleShot(2000, self.clear_last_viewed_subject)

    def create_context_action(self, subject, scenario_id, scenario_name, show_name=None, new_viewer=True):
        if show_name is None:
            show_name = scenario_name
        if scenario_id is None:
            scenario_id = 0

        def show_subject():
            self.change_subject_in_mri_viewer(subject)
            self.add_subjects_to_plot(subject_ids=(int(subject),))

        def launch_new_viewer():
            self.launch_mri_viewer(subject, scenario_id)
            self.add_subjects_to_plot(subject_ids=(int(subject),))

        if new_viewer:
            action = QtGui.QAction(
                "Show subject %s's %s in new viewer" % (subject, show_name), None)
            action.triggered.connect(launch_new_viewer)
        else:
            action = QtGui.QAction(
                "Show %s in existing viewers" % subject, None)
            action.triggered.connect(show_subject)
        return action

    def create_view_details_context_menu(self, global_pos, subject=None):
        if subject is None:
            subject = self.last_viewed_subject
            if subject is None:
                return

        scenarios = {}
        outcome_idx = braviz_tab_data.get_var_idx(self.outcome_var_name)
        outcome_scenarios = braviz_user_data.get_variable_scenarios(
            outcome_idx)
        if len(outcome_scenarios) > 0:
            scenarios[self.outcome_var_name] = outcome_scenarios.items()
        regressors = self.regressors_model.get_regressors()
        for reg in regressors:
            reg_idx = braviz_tab_data.get_var_idx(reg)
            reg_scenarios = braviz_user_data.get_variable_scenarios(reg_idx)
            if len(reg_scenarios):
                scenarios[reg] = reg_scenarios.items()

        menu = QtGui.QMenu("Subject %s" % subject)
        show_action = self.create_context_action(
            subject, None, None, new_viewer=False)
        menu.addAction(show_action)
        launch_mri_action = self.create_context_action(subject, None, "MRI")
        menu.addAction(launch_mri_action)

        log = logging.getLogger(__name__)
        log.debug(scenarios)
        for var, scn_lists in scenarios.iteritems():
            for scn_id, scn_name in scn_lists:
                action = self.create_context_action(
                    subject, scn_id, scn_name, var)
                menu.addAction(action)

        menu.exec_(global_pos)

    def subject_details_from_plot(self, pos):
        # print "context menu"
        # print pos
        global_pos = self.plot.mapToGlobal(pos)
        self.create_view_details_context_menu(global_pos)

    def subject_details_from_tree(self, pos):
        global_pos = self.ui.sample_tree.mapToGlobal(pos)
        selection = self.ui.sample_tree.currentIndex()
        selection = self.sample_model.index(
            selection.row(), 0, selection.parent())
        # check if it is a leaf
        if self.sample_model.hasChildren(selection) is True:
            return
        else:
            # print "this is a leaf"
            subject = self.sample_model.data(selection, QtCore.Qt.DisplayRole)
            # print subject
            self.create_view_details_context_menu(global_pos, subject)

    def clear_last_viewed_subject(self):
        self.last_viewed_subject = None


    def launch_mri_viewer(self, subject, scenario):
        log = logging.getLogger(__name__)

        log.info("launching viewer")
        if self._message_client is None:
            log.warning("Menu is not available, can't launch viewer")
            return

        args = [sys.executable, "-m", "braviz.applications.subject_overview", str(scenario),
                self._message_client.server_broadcast, self._message_client.server_receive, str(subject)]

        log.info(args)
        braviz.utilities.launch_sub_process(args)

    def closeEvent(self, *args, **kwargs):
    # if self.mri_viewer_process is not None:
    # self.mri_viewer_process.terminate()
        log = logging.getLogger(__name__)
        log.info("Finishing")

    def get_state(self):
        state = {}
        vars_state = {"outcome": self.outcome_var_name, "regressors": self.regressors_model.get_regressors(),
                      "interactions": self.regressors_model.get_interactions()}
        state["vars"] = vars_state
        state["plot"] = {"var_name": self.plot_var_name}
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
        dialog = braviz.interaction.qt_dialogs.SaveScenarioDialog(
            app_name, state, params)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            # save main plot as screenshot
            scn_id = params["scn_id"]
            pixmap = QtGui.QPixmap.grabWidget(self.plot)
            file_name = "scenario_%d.png" % scn_id
            data_root = braviz.readAndFilter.braviz_auto_dynamic_data_root()
            file_path = os.path.join(
                data_root, "braviz_data", "scenarios", file_name)
            log.info(file_path)
            pixmap.save(file_path)
        log.info("saving")
        log.info(state)

    def load_scenario_dialog(self):
        app_name = os.path.splitext(os.path.basename(__file__))[0]
        wanted_state = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(
            app_name, wanted_state)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            log.info("Loading state")
            log.info(wanted_state)
            self.restore_state(wanted_state)

    def load_scenario_id(self, scn_id):
        wanted_state = braviz_user_data.get_scenario_data_dict(scn_id)
        app = wanted_state.get("meta").get("application")
        if app == os.path.splitext(os.path.basename(__file__))[0]:
            self.restore_state(wanted_state)
        else:
            log = logging.getLogger(__file__)
            log.error(
                "Scenario id doesn't correspond to an anova scenario, ignoring")

    def restore_state(self, wanted_state):
        # restore outcome
        # sample
        logger = logging.getLogger(__name__)
        logger.info("loading state %s", wanted_state)
        sample = wanted_state.get("sample")
        if sample is not None:
            self.sample = sample
            self.sample_model.set_sample(sample)
        self.ui.calculate_button.setEnabled(0)
        reg_name = wanted_state["vars"].get("outcome")
        if reg_name is not None:
            index = self.ui.outcome_sel.findText(reg_name)
            if index >= 0:
                self.ui.outcome_sel.setCurrentIndex(index)
            else:
                self.ui.outcome_sel.insertItem(0, reg_name)
                self.ui.outcome_sel.setCurrentIndex(0)
        self.set_outcome_var_type(reg_name)
        # restore regressors
        regressors = wanted_state["vars"].get("regressors", tuple())
        self.regressors_model.reset_data(regressors)
        # restore interactions
        interactions = wanted_state["vars"].get("interactions", tuple())
        # TODO: Must find a better way to encode interactions
        for inter in interactions:
            tokens = inter.split("*")
            self.regressors_model.add_interactor_by_names(tokens)
        self.regressors_model.show_interactions(True)
        self.regressors_model.show_regressors(True)
        # calculate anova
        self.check_if_ready()
        if self.ui.calculate_button.isEnabled():
            self.calculate_anova()
            # set plot
        plot_name = wanted_state["plot"].get("var_name")
        if plot_name is not None:
            self.update_main_plot(plot_name)

    def load_sample(self):
        dialog = braviz.applications.sample_select.SampleLoadDialog(
            new__and_load=True,
            server_broadcast=self._message_client.server_broadcast,
            server_receive=self._message_client.server_receive)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            log.info("new sample")
            log.info(new_sample)
            self.set_sample(new_sample)

    def set_sample(self, new_sample):
        self.sample = new_sample
        self.sample_model.set_sample(new_sample)
        self.update_main_plot(self.plot_var_name)
        self.get_missing_values()

    def send_sample(self):
        msg = {"sample" : list(self.sample)}
        self._message_client.send_message(msg)

    def modify_sample(self):
        self.ui.modify_sample_button.setEnabled(False)
        if self._message_client is not None:
            braviz.applications.sample_select.launch_sample_create_dialog(
                server_broadcast=self._message_client.server_broadcast,
                server_receive=self._message_client.server_receive,
                parent_id=os.getpid(),
                sample=self.sample
            )
        else:
            braviz.applications.sample_select.launch_sample_create_dialog(
                sample=self.sample
            )
        QtCore.QTimer.singleShot(5000, lambda: self.ui.modify_sample_button.setEnabled(True))

    def handle_sample_message(self, msg):
        sample = msg.get("sample", tuple())
        target = msg.get("target")
        if target is not None:
            accept = target == os.getpid()
        else:
            accept = self.accept_samples()
        if accept:
            self.set_sample(sample)

    def accept_samples(self):
        if self.sample_message_policy == "ask":
            answer = QtGui.QMessageBox.question(
                self, "Sample Received", "Accept sample?",
                QtGui.QMessageBox.Yes | QtGui.QMessageBox.No | QtGui.QMessageBox.YesToAll | QtGui.QMessageBox.NoToAll,
                QtGui.QMessageBox.Yes)
            if answer == QtGui.QMessageBox.Yes:
                return True
            elif answer == QtGui.QMessageBox.YesToAll:
                self.update_samples_policy("always")
                return True
            elif answer == QtGui.QMessageBox.No:
                return False
            elif answer == QtGui.QMessageBox.NoToAll:
                self.update_samples_policy("never")
                return False
        elif self.sample_message_policy == "always":
            return True
        else:
            return False

    def update_samples_policy(self, item):
        if item == "ask":
            self.ui.actionAlways.setChecked(False)
            self.ui.actionNever.setChecked(False)
            self.ui.actionAsk.setChecked(True)
        elif item == "never":
            self.ui.actionAlways.setChecked(False)
            self.ui.actionNever.setChecked(True)
            self.ui.actionAsk.setChecked(False)
        elif item == "always":
            self.ui.actionAlways.setChecked(True)
            self.ui.actionNever.setChecked(False)
            self.ui.actionAsk.setChecked(False)
        else:
            assert False
        self.sample_message_policy = item

    def save_figure(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Plot", ".", "PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.plot.fig.savefig(filename)

    def save_data(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Data", ".", "csv (*.csv)"))
        if len(filename) > 0:
            s_vars = [self.outcome_var_name] + \
                     list(self.regressors_model.get_regressors())
            out_df = braviz_tab_data.get_data_frame_by_name(s_vars)
            out_df.to_csv(filename)


def run():
    import sys
    from braviz.utilities import configure_logger_from_conf

    configure_logger_from_conf("anova_app")
    args = sys.argv
    scenario = None
    server_broadcast_address = None
    server_receive_address = None
    if len(args) > 1:
        scenario = int(args[1])
        if len(args) > 2:
            server_broadcast_address = args[2]
            if len(args) > 3:
                server_receive_address = args[3]
    app = QtGui.QApplication([])
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = AnovaApp(
        scenario, server_broadcast_address, server_receive_address)
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()
