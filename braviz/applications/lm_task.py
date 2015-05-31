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
from braviz.utilities import set_pyqt_api_2
set_pyqt_api_2()

import random

import sys

import datetime
import os
import platform
import logging
from itertools import izip

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow
import numpy as np
import pandas as pd

from braviz.interaction.qt_guis.linear_reg import Ui_LinearModel
import braviz.interaction.qt_dialogs
import braviz.applications.sample_select
from braviz.interaction.qt_dialogs import (OutcomeSelectDialog, RegressorSelectDialog,
                                           InteractionSelectDialog)
from braviz.visualization.matplotlib_qt_widget import MatplotWidget
import braviz.interaction.r_functions
import braviz.interaction.qt_models as braviz_models
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data
from braviz.interaction.connection import MessageClient, MessageServer
from braviz.readAndFilter.config_file import get_config
from braviz.utilities import launch_sub_process

__author__ = 'Diego'

config = get_config(__file__)
def_vars = config.get_default_variables()
INITIAL_OUTCOMES = map(
    braviz_tab_data.get_var_idx, [def_vars["ratio1"], def_vars["ratio2"]])
INITIAL_OUTCOMES = filter(lambda x: x is not None, INITIAL_OUTCOMES)

SAMPLE_TREE_COLUMNS = (def_vars["nom1"], def_vars["nom2"])


class LinearModelApp(QMainWindow):

    def __init__(self, scenario, server_broadcast_address, server_receive_address):
        QMainWindow.__init__(self)
        self.outcome_var_name = None
        self.model = None
        self.regressors_model = braviz_models.AnovaRegressorsModel()
        self.__table_cols = ["Slope", "T Value", "P Value"]
        empty_df = pd.DataFrame(columns=self.__table_cols)
        empty_df.index.name = "Coefficient"
        self.result_model = braviz_models.DataFrameModel(
            empty_df, self.__table_cols, string_columns={0})
        self.sample_model = braviz_models.SampleTree(SAMPLE_TREE_COLUMNS)
        self.plot = None
        self.plot_name = None
        self.sample = braviz_tab_data.get_subjects()
        self.coefs_df = None
        self.regression_results = None
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

    def setup_gui(self):
        self.ui = Ui_LinearModel()
        self.ui.setupUi(self)
        for v_idx in INITIAL_OUTCOMES:
            self.ui.outcome_sel.insertItem(
                0, braviz_tab_data.get_var_name(v_idx))
        self.ui.outcome_sel.insertSeparator(self.ui.outcome_sel.count() - 1)
        self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count() - 1)
        # self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.clicked.connect(
            self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(
            self.launch_regressors_context_menu)
        self.ui.add_interaction_button.clicked.connect(
            self.dispatch_interactions_dialog)
        self.ui.calculate_button.clicked.connect(self.calculate_linear_reg)
        self.ui.results_table.setModel(self.result_model)

        self.ui.matplot_layout = QtGui.QVBoxLayout()
        self.plot = MatplotWidget()
        self.plot.draw_message(
            "Welcome\n\nSelect Outcome and add Regressors to start")
        self.plot.customContextMenuRequested.connect(
            self.subject_details_from_plot)
        self.plot.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.matplot_layout.addWidget(self.plot)
        self.ui.plot_frame.setLayout(self.ui.matplot_layout)
        self.ui.results_table.activated.connect(
            self.update_main_plot_from_results)
        self.ui.reg_table.activated.connect(
            self.update_main_plot_from_regressors)

        self.ui.factor_plot_button.clicked.connect(self.draw_coefficints_plot)
        self.ui.residuals_plot_button.clicked.connect(self.draw_residuals_plot)

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
        self.ui.actionData.triggered.connect(self.save_data)
        self.ui.actionImages.triggered.connect(self.save_figure)

        self.ui.actionLoad_sample.triggered.connect(self.load_sample)
        self.ui.actionModify_sample.triggered.connect(self.modify_sample)
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
            dialog = OutcomeSelectDialog(params, sample=self.sample)
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

    def dispatch_interactions_dialog(self):
        interaction_dialog = InteractionSelectDialog(self.regressors_model)
        interaction_dialog.exec_()
        self.regressors_model.show_regressors(True)
        try:
            ints = self.regressors_model.get_interactions()[-1]
        except (KeyError, IndexError):
            return

    def set_outcome_var_type(self, new_var):
        log = logging.getLogger(__name__)
        if new_var is None:
            var_type_text = "Type"
            self.ui.outcome_type.setText(var_type_text)
            self.outcome_var_name = None
            # self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
            return
        new_var = unicode(new_var)
        if new_var == self.outcome_var_name:
            return
        log.debug("succesfully selected %s" % new_var)
        index = self.ui.outcome_sel.findText(new_var)
        if index < 0:
            self.ui.outcome_sel.setCurrentIndex(index)
            self.ui.outcome_sel.insertItem(0, new_var)
            index = 0
            pass
        self.outcome_var_name = new_var
        self.ui.outcome_sel.setCurrentIndex(index)
        try:
            var_is_real = braviz_tab_data.is_variable_name_real(new_var)
        except TypeError:
            var_type_text = "Type"
        else:
            var_type_text = "Real" if var_is_real else "Nominal"
        self.ui.outcome_type.setText(var_type_text)
        # update plot
        if self.plot_name is not None:
            plot_type, var_name = self.plot_name
            if plot_type == 2:
                self.update_main_plot_from_regressors(None, var_name)
            else:
                self.plot.draw_message("Click on a regressor to see a plot")
            self.clear_regression_results()

        self.check_if_ready()

    def launch_add_regressor_dialog(self):
        reg_dialog = RegressorSelectDialog(
            self.outcome_var_name, self.regressors_model, sample=self.sample)
        result = reg_dialog.exec_()
        if result == reg_dialog.Accepted:
            if self.regressors_model.rowCount() > 0:
                index = self.regressors_model.index(
                    self.regressors_model.rowCount() - 1, 0)
                self.update_main_plot_from_regressors(index)
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

    def calculate_linear_reg(self):
        log = logging.getLogger(__name__)
        log.info("calculating lm")
        try:
            regressors = self.regressors_model.get_data_frame()
            interactions = self.regressors_model.get_interactors_dict()
            self.ui.calculate_button.setEnabled(0)
            res = braviz.interaction.r_functions.calculate_normalized_linear_regression(self.outcome_var_name,
                                                                                        regressors, interactions,
                                                                                        self.sample)
        except Exception as e:
            msg = QtGui.QMessageBox()
            msg.setText(str(e.message))
            msg.setIcon(msg.Warning)
            msg.setWindowTitle("lm Error")
            log.warning("lm Error")
            log.exception(e)
            msg.exec_()
            self.ui.calculate_button.setEnabled(1)
            self.coefs_df = None
            self.regression_results = None
        else:
            # print res
            self.ui.r_squared_label.setText(
                "R<sup>2</sup> = %.2f" % res.get("adj_r2", np.nan))
            f_nom, f_dem = res.get("f_stat_df", (0, 0))
            self.ui.f_value_label.setText(
                "F(%d,%d) = %.2f" % (f_nom, f_dem, res.get("f_stats_val", np.nan)))
            self.ui.p_value_label.setText("P = %g" % res.get("f_pval", np.nan))
            coeffs_df = res["coefficients_df"]
            self.result_model.set_df(coeffs_df)
            self.coefs_df = coeffs_df
            self.regression_results = res
            self.draw_coefficints_plot()
            self.ui.calculate_button.setEnabled(1)
            return

    def clear_regression_results(self):
        self.ui.r_squared_label.setText("R<sup>2</sup> = ")
        self.ui.f_value_label.setText("F = ")
        self.ui.p_value_label.setText("P = ")
        empty_df = pd.DataFrame(columns=self.__table_cols)
        empty_df.index.name = "Coefficient"
        self.result_model.set_df(empty_df)
        self.coefs_df = None
        self.regression_results = None

    def update_main_plot_from_results(self, index, var_name=None):
        if var_name is None:
            row = index.row()
            var_name_index = self.result_model.index(row, 0)
            var_name = unicode(
                self.result_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.plot_name = (1, var_name)
        if var_name == "(Intercept)":
            df2 = self.regression_results["data"]
            #df2["Jitter"] = np.random.random(len(df2))
            # df2.dropna(inplace=True)
            #self.plot.draw_scatter(df2, "Jitter", self.outcome_var_name, reg_line=False)
            #b = np.mean(df2[self.outcome_var_name])
            #self.plot.axes.axhline(b, ls="--", c=(0.3, 0.3, 0.3))
            self.plot.draw_intercept(df2, self.outcome_var_name)
            # self.plot.draw()
        else:
            # get components
            components = self.coefs_df.loc[var_name, "components"]
            if len(components) > 1:
                # interaction term
                if len(components) == 2:
                    self.draw_interaction_plot(components[0], components[1])
                else:
                    components2 = np.random.choice(
                        components, 2, replace=False)
                    self.draw_interaction_plot(components2[0], components2[1])
            else:
                target_var = components[0]
                target_type = self.regression_results["var_types"][target_var]
                df2 = self.isolate_one(target_var)
                if target_type == "n":
                    self.plot_nominal_intercepts(df2, target_var)
                elif target_type == "r":
                    self.plot.draw_scatter(
                        df2, target_var, self.outcome_var_name, reg_line=True)
                else:
                    x_labels = braviz_tab_data.get_labels_dict_by_name(
                        target_var)
                    self.plot.draw_scatter(
                        df2, target_var, self.outcome_var_name, reg_line=True, x_labels=x_labels)
                self.plot.set_figure_title("Mean effect of %s" % target_var)
        return

    def update_main_plot_from_regressors(self, index, var_name=None):
        if var_name is None:
            row = index.row()
            var_name_index = self.regressors_model.index(row, 0)
            var_name = unicode(
                self.regressors_model.data(var_name_index, QtCore.Qt.DisplayRole))
        self.plot_name = (2, var_name)
        if "*" in var_name:
            factors = var_name.split("*")
            if len(factors) > 2:
                factors = random.sample(factors, 2)
            self.draw_two_vars_scatter_plot(factors[0], factors[1])
        else:
            self.draw_simple_scatter_plot(var_name)

    def add_subjects_to_plot(self, tree_indexes=None, subject_ids=None):
        # tree_indexes used when called from tree
        if subject_ids is None:
            selection = self.ui.sample_tree.currentIndex()
            leafs = self.sample_model.get_leafs(selection)
            subject_ids = map(int, leafs)
        self.plot.add_subject_markers(subject_ids)
        return

    def draw_coefficints_plot(self):
        self.plot_name = (3, None)
        if self.coefs_df is not None:
            self.plot.draw_coefficients_plot(self.coefs_df)
        return

    def draw_residuals_plot(self):
        self.plot_name = (4, None)
        if self.regression_results is None:
            return
        residuals = self.regression_results["residuals"]
        fitted = self.regression_results["fitted"]
        names = self.regression_results["data_points"]
        assert isinstance(names, list)
        self.plot.draw_residuals(residuals, fitted, names)

    def draw_simple_scatter_plot(self, regressor_name):
        df = braviz_tab_data.get_data_frame_by_name(
            [self.outcome_var_name, regressor_name])
        df = df.loc[self.sample]
        df.dropna(inplace=True)
        if braviz_tab_data.is_variable_name_real(regressor_name):
            reg_line = True
            labels_dict = None
            self.plot.draw_scatter(
                df, regressor_name, self.outcome_var_name, reg_line=reg_line, x_labels=labels_dict)
        else:
            labels_dict = braviz_tab_data.get_labels_dict_by_name(
                regressor_name)
            if len(labels_dict) == 2:
                self.plot.draw_scatter(
                    df, regressor_name, self.outcome_var_name, reg_line=True, x_labels=labels_dict)
            else:
                self.plot.draw_intercept(
                    df, self.outcome_var_name, regressor_name, group_labels=labels_dict)
        self.plot.set_figure_title("RAW effect of %s" % regressor_name)

    def cut_and_sort(self, regressor1, regressor2, df):
        var_1_real = braviz_tab_data.is_variable_name_real(regressor1)
        var_2_real = braviz_tab_data.is_variable_name_real(regressor2)
        outcome = self.outcome_var_name
        hue_var = regressor2
        x_var = regressor1
        qualitative_map = True
        x_labels = None

        if var_2_real:
            if not var_1_real:
                # var 1 is nominal
                hue_var = regressor1
                x_var = regressor2
                labels = braviz_tab_data.get_labels_dict_by_name(hue_var)
            else:
                # both are real
                # cut var2
                real_data = df.pop(regressor2)
                dmin, dmax = np.min(real_data), np.max(real_data)
                N_PIECES = 3
                delta = (dmax - dmin) / N_PIECES
                nom_data = (real_data - dmin) * N_PIECES // (dmax - dmin) + 1
                nom_data = np.minimum(nom_data, N_PIECES)
                nom_data = nom_data.astype(np.int)
                df[regressor2] = nom_data
                labels = dict(
                    (i + 1, (dmin + i * delta, dmin + (i + 1) * delta)) for i in xrange(N_PIECES))
                qualitative_map = False
        else:
            if not var_1_real:
                # both are nominal
                labels_1 = braviz_tab_data.get_labels_dict_by_name(regressor1)
                labels_2 = braviz_tab_data.get_labels_dict_by_name(regressor2)
                if len(labels_1) < len(labels_2):
                    x_var = regressor1
                    x_labels = labels_1
                    labels = labels_2
                    hue_var = regressor2
                else:
                    x_var = regressor2
                    x_labels = labels_2
                    labels = labels_1
                    hue_var = regressor1
            else:
                # var2 nominal and var1 real
                hue_var = regressor2
                x_var = regressor1
                labels = None

        return df, x_var, hue_var, outcome, labels, qualitative_map, x_labels

    def draw_two_vars_scatter_plot(self, regressor1, regressor2):
        df = braviz_tab_data.get_data_frame_by_name(
            [regressor1, regressor2, self.outcome_var_name])
        df = df.loc[self.sample]
        df.dropna(inplace=True)
        df, x_var, hue_var, outcome, labels, qualitative_map, x_labels = self.cut_and_sort(
            regressor1, regressor2, df)
        if qualitative_map is False:
            # build string labels
            labels2 = dict((k, "%.3g - %.3g" % (l, h))
                           for k, (l, h) in labels.iteritems())
        else:
            labels2 = labels
        self.plot.draw_scatter(df, x_var, outcome, hue_var=hue_var, hue_labels=labels2, qualitative_map=qualitative_map,
                               x_labels=x_labels)
        self.plot.set_figure_title(
            "RAW interaction of %s and %s" % (regressor1, regressor2))

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
            subject = self.plot.last_viewed_subject
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
        state["plot"] = {"var_name": self.plot_name}
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

    def save_figure(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Plot", ".", "PDF (*.pdf);;PNG (*.png);;svg (*.svg)"))
        self.plot.fig.savefig(filename)

    def save_data(self):
        filename = unicode(QtGui.QFileDialog.getSaveFileName(self,
                                                             "Save Data", ".", "csv (*.csv)"))
        if len(filename) > 0:
            a_vars = [self.outcome_var_name] + \
                list(self.regressors_model.get_regressors())
            out_df = braviz_tab_data.get_data_frame_by_name(a_vars)
            out_df.to_csv(filename)

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
            self.calculate_linear_reg()
        # set plot
        plot_name = wanted_state["plot"].get("var_name")
        if plot_name is not None:
            plot_type, args = plot_name
            if plot_type == 1:
                self.update_main_plot_from_regressors(args)
            elif plot_type == 2:
                self.update_main_plot_from_results(args)
            elif plot_type == 3:
                self.draw_coefficints_plot()
            elif plot_type == 4:
                self.draw_residuals_plot()
            else:
                logger.error("Unknown plot type %s", plot_type)


    def isolate_one(self, isolating_factor, un_standardize=True):
        standarized_data = self.regression_results["standardized_model"]
        coefs = self.coefs_df
        res = self.regression_results["residuals"]
        INTERCEPT = "(Intercept)"
        #data = self.regression_results["data"]

        df3 = pd.DataFrame(standarized_data[isolating_factor])
        df3[self.outcome_var_name] = np.nan
        levels = (df3.index,)
        ls = (None,)
        results_var_types_ = self.regression_results["var_types"]
        factor_t = results_var_types_[isolating_factor]

        def calculate_beta_hat(a_isolating, a_components, a_factor_terms, a_beta_j):
            _other_components = set(a_components)
            _other_components.remove(a_isolating)
            _var_types = map(results_var_types_.get, _other_components)
            if "b" in _var_types or "r" in _var_types:
                return 0
            else:
                _indicator_vec = np.ones(len(standarized_data))
                for _base_var in _other_components:
                    # find level associated with current factor in other terms
                    for _cand in a_factor_terms:
                        if _cand.startswith(_base_var):
                            _level = _cand[len(_base_var) + 1:]
                            _li = self.regression_results[
                                "dummy_levels"][_base_var][_level]
                            _col = standarized_data[
                                _base_var].get_values().astype(np.int)
                            _matches = (_col == _li).astype(np.int)
                            _indicator_vec *= _matches
                            break
                _indicator_mean = np.mean(_indicator_vec)
                _beta_j_hat = _indicator_mean * a_beta_j
                return _beta_j_hat

        if results_var_types_[isolating_factor] == "n":
            ls = np.unique(standarized_data[isolating_factor])
            levels = [df3.index[df3[isolating_factor] == l] for l in ls]
        for l, l_id in izip(levels, ls):
            beta_0 = coefs.loc[INTERCEPT, "Slope"]
            beta_1 = 0
            for var in coefs.index:
                if var == INTERCEPT:
                    continue
                row = coefs.loc[var]
                components = row["components"]
                beta_j = row["Slope"]

                if factor_t == "n":
                    if len(components) == 1:
                        base_var = components[0]
                        if base_var == isolating_factor:
                            sub_level = var[len(base_var) + 1:]
                            sub_level_id = self.regression_results[
                                "dummy_levels"][base_var][sub_level]
                            if int(sub_level_id) == int(l_id):
                                # it is really an intercept term
                                beta_0 += beta_j
                    else:
                        # first need to find if I am at correct level
                        interaction_terms = var.split("*")
                        for cand in interaction_terms:
                            if cand.startswith(isolating_factor):
                                sub_level = cand[len(isolating_factor) + 1:]
                                sub_level_id = self.regression_results[
                                    "dummy_levels"][isolating_factor][sub_level]
                                if int(sub_level_id) == int(l_id):
                                    beta_j_hat = calculate_beta_hat(isolating_factor, components,
                                                                    interaction_terms, beta_j)
                                    if np.isfinite(beta_j_hat):
                                        beta_0 += beta_j_hat
                else:
                    if len(components) == 1:
                        base_var = components[0]
                        if base_var == isolating_factor:
                            beta_1 += beta_j
                    else:
                        interaction_terms = var.split("*")
                        if isolating_factor in interaction_terms:
                            beta_j_hat = calculate_beta_hat(
                                isolating_factor, components, interaction_terms, beta_j)
                            if np.isfinite(beta_j_hat):
                                beta_1 += beta_j_hat
            log = logging.getLogger(__name__)
            log.info("beta1: %s", beta_1)
            log.info("beta0: %s", beta_0)
            df3[self.outcome_var_name][l] = beta_0 + beta_1 * \
                df3[isolating_factor][l].values.squeeze().astype(np.int)
        df3[self.outcome_var_name] += res
        if un_standardize is False:
            return df3
        # fix outcome var
        outcome_data = df3[self.outcome_var_name]
        m, s = self.regression_results["mean_sigma"][self.outcome_var_name]
        us_outcome = 2 * s * outcome_data + m
        df3[self.outcome_var_name] = us_outcome
        # fix x_var
        v_type = results_var_types_[isolating_factor]
        x_data = df3[isolating_factor]
        if v_type == "r":
            m, s = self.regression_results["mean_sigma"][isolating_factor]
            us_x_data = 2 * s * x_data + m
            df3[isolating_factor] = us_x_data
        elif v_type == "b":
            m, s = self.regression_results["mean_sigma"][isolating_factor]
            us_x_data = s * x_data + m
            df3[isolating_factor] = us_x_data
        return df3

    def plot_nominal_intercepts(self, df, var_name):
        # df = braviz_tab_data.get_data_frame_by_name((self.outcome_var_name,var_name))
        group_labels = braviz_tab_data.get_labels_dict_by_name(var_name)
        df[var_name] = df[var_name].astype(np.int)
        self.plot.draw_intercept(
            df, self.outcome_var_name, var_name, group_labels=group_labels)

    def draw_interaction_plot(self, reg1, reg2):

        df = self.regression_results["standardized_model"]
        df2, x_var, hue_var, outcome, labels, qualitative_map, x_labels = self.cut_and_sort(
            reg1, reg2, df.copy())
        # Fix labels
        var_types = self.regression_results["var_types"]
        hue_t = var_types[hue_var]
        if hue_t == "r":
            hue_mean, hue_sigma = self.regression_results[
                "mean_sigma"][hue_var]
            labels2 = dict()
            for k, (l, h) in labels.iteritems():
                l2 = 2 * hue_sigma * l + hue_mean
                h2 = 2 * hue_sigma * h + hue_mean
                labels2[k] = "%.3g - %.3g" % (l2, h2)
        else:
            labels2 = labels

        groups_series = df2[hue_var]
        log=logging.getLogger(__name__)
        log.info("testing %s %s" % (reg1, reg2))
        log.info("===============")
        log.info(df)
        log.info(groups_series)
        log.info("===============")
        df2 = self.isolate_in_groups(x_var, outcome, hue_var, groups_series)
        df2[outcome] += self.regression_results["residuals"]
        # un standardize yvar
        y_m, y_s = self.regression_results["mean_sigma"][outcome]
        df2[outcome] = 2 * y_s * df2[outcome] + y_m

        if hue_t == "b":
            ks = sorted(labels.keys())
            pos = df2[hue_var] >= 0
            df2[hue_var][pos] = ks[1]
            df2[hue_var][np.logical_not(pos)] = ks[0]
        self.plot.draw_scatter(df2, x_var, outcome, hue_var=hue_var, reg_line=True, hue_labels=labels2,
                               qualitative_map=qualitative_map, x_labels=x_labels)
        self.plot.set_figure_title(
            "Mean Interaction between %s and %s" % (x_var, hue_var))

    def isolate_in_groups(self, x_var, y_var, z_var, groups):
        # dont mess with the good copy of data
        work_df = self.regression_results["standardized_model"].copy()
        var_types = self.regression_results["var_types"]
        groups_r = (var_types[z_var] == "r")
        dummy_columns = pd.DataFrame(index=work_df.index)
        # make a copy, because maybe will add new columns
        for var in work_df:
            if (var == x_var) or (var == y_var):
                # leave alone
                pass
            elif var == z_var:
                # find mean in each group
                # only necessary if the groups variable is real
                if groups_r is True:
                    pass
                    group_vals = np.unique(groups)
                    # group_means
                    averaged_group_col = np.zeros(len(work_df))
                    for val in group_vals:
                        g_i = (groups == val)
                        g_m = np.mean(work_df[z_var][g_i])
                        averaged_group_col[g_i.get_values()] = g_m
                    work_df[z_var] = averaged_group_col
                elif var_types[z_var] == "n":
                    # we need to generate dummy columns
                    possible_levels = np.unique(work_df[var])
                    for l in possible_levels:
                        dummy_name = "%s_%s" % (var, l)
                        indicator = (work_df[var] == l).astype(np.float)
                        # inside each level it will be constant, so no need of
                        # averaging
                        dummy_columns[dummy_name] = indicator
            else:
                # find mean, remember dataframe is standardized
                if var_types[var] == "n":
                    # we will create new columns for each dummy level
                    possible_levels = np.unique(work_df[var])
                    for l in possible_levels:
                        dummy_name = "%s_%s" % (var, l)
                        indicator = (work_df[var] == l).astype(np.float)
                        avg_i = np.mean(indicator)
                        dummy_columns[dummy_name] = avg_i
                    pass
                else:
                    work_df[var] = 0

        fitted = self.evaluate_linear_model(work_df, dummy_columns)
        df_ans = self.regression_results["data"][[x_var]].copy()
        df_ans[z_var] = groups
        df_ans[y_var] = fitted
        return df_ans

    def evaluate_linear_model(self, variables_df, dummy_columns):
        coefs_df = self.coefs_df
        var_types = self.regression_results["var_types"]

        fitted = np.zeros(len(variables_df))
        for coef in coefs_df.index:
            if coef == "(Intercept)":
                fitted += coefs_df["Slope"][coef]
            else:
                slope = coefs_df["Slope"][coef]
                if not np.isfinite(slope):
                    continue
                comps = coefs_df["components"][coef]
                c_df = variables_df[list(comps)].copy()
                for c in comps:
                    if var_types[c] == "n":
                        # find original factor
                        for fact in coef.split("*"):
                            if fact.startswith(c):
                                label = fact[len(c) + 1:]
                                label_i = self.regression_results[
                                    "dummy_levels"][c][label]
                                # find dummy column
                                dummy_name = "%s_%s" % (c, label_i)
                                dummy_col = dummy_columns[dummy_name]
                                c_df[c] = dummy_col
                prod = c_df.product(axis=1)

                if not np.all(prod == 0) and np.isfinite(slope):
                    prod *= slope
                    fitted += prod
        return fitted

    def load_scenario_id(self, scn_id):
        wanted_state = braviz_user_data.get_scenario_data_dict(scn_id)
        app = wanted_state.get("meta").get("application")
        if app == os.path.splitext(os.path.basename(__file__))[0]:
            self.restore_state(wanted_state)
        else:
            log = logging.getLogger(__file__)
            log.error(
                "Scenario id doesn't correspond to an anova scenario, ignoring")

    def set_sample(self, new_sample):
        log = logging.getLogger(__name__)
        log.info("new sample")
        log.info(new_sample)
        self.sample = new_sample
        self.sample_model.set_sample(new_sample)
        self.update_main_plot_from_regressors(
            self.regressors_model.index(self.plot_name[0], 0), var_name=self.plot_name[1])
        self.get_missing_values()

    def load_sample(self):
        dialog = braviz.applications.sample_select.SampleLoadDialog(
            new__and_load=True,
            server_broadcast=self._message_client.server_broadcast,
            server_receive=self._message_client.server_receive)
        res = dialog.exec_()
        if res == dialog.Accepted:
            new_sample = dialog.current_sample
            self.set_sample(new_sample)

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


def run():
    import sys
    from braviz.utilities import configure_logger_from_conf
    # configure_logger("lm_task")
    configure_logger_from_conf("lm_task")
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
    main_window = LinearModelApp(
        scenario, server_broadcast_address, server_receive_address)
    #ic = main_window.windowIcon()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()
