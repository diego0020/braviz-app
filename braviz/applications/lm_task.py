from __future__ import division
import random

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

from braviz.interaction.qt_guis.linear_reg import Ui_LinearModel
import braviz.interaction.qt_dialogs
import braviz.interaction.qt_sample_select_dialog
from braviz.interaction.qt_dialogs import (OutcomeSelectDialog, RegressorSelectDialog,
                                           InteractionSelectDialog)

from braviz.visualization.matplotlib_qt_widget import MatplotWidget
import braviz.interaction.r_functions

import braviz.interaction.qt_models as braviz_models
import braviz.readAndFilter.tabular_data as braviz_tab_data
import braviz.readAndFilter.user_data as braviz_user_data

import multiprocessing
import multiprocessing.connection
import subprocess
import sys
import binascii
import datetime
import os
import platform

import logging
import numpy as np
import pandas as pd
from itertools import izip

class LinearModelApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.outcome_var_name = None
        self.model = None
        self.regressors_model = braviz_models.AnovaRegressorsModel()
        self.__table_cols = ["Slope", "T Value", "P Value"]
        empty_df = pd.DataFrame(columns=self.__table_cols)
        empty_df.index.name = "Coefficient"
        self.result_model = braviz_models.DataFrameModel(empty_df, self.__table_cols)
        self.sample_model = braviz_models.SampleTree()
        self.plot = None
        self.last_viewed_subject = None
        self.mri_viewer_pipe = None
        self.mri_viewer_process = None
        self.poll_timer = None
        self.sample = braviz_tab_data.get_subjects()
        self.coefs_df = None
        self.regression_results = None
        self.ui = None
        self.setup_gui()


    def setup_gui(self):
        self.ui = Ui_LinearModel()
        self.ui.setupUi(self)
        self.ui.outcome_sel.insertSeparator(self.ui.outcome_sel.count() - 1)
        self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count() - 1)
        #self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.clicked.connect(self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(self.launch_regressors_context_menu)
        self.ui.add_interaction_button.clicked.connect(self.dispatch_interactions_dialog)
        self.ui.calculate_button.clicked.connect(self.calculate_linear_reg)
        self.ui.results_table.setModel(self.result_model)

        self.ui.matplot_layout = QtGui.QVBoxLayout()
        self.plot = MatplotWidget()
        self.plot.draw_message("Welcome\n\nSelect Outcome and add Regressors to start")
        self.ui.matplot_layout.addWidget(self.plot)
        self.ui.plot_frame.setLayout(self.ui.matplot_layout)
        self.ui.results_table.activated.connect(self.update_main_plot_from_results)
        self.ui.reg_table.activated.connect(self.update_main_plot_from_regressors)

        self.ui.factor_plot_button.clicked.connect(self.draw_coefficints_plot)
        self.ui.residuals_plot_button.clicked.connect(self.draw_residuals_plot)

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


    def dispatch_outcome_select(self):

        #print "outcome select %s / %s"%(self.ui.outcome_sel.currentIndex(),self.ui.outcome_sel.count()-1)
        if self.ui.outcome_sel.currentIndex() == self.ui.outcome_sel.count() - 1:
            #print "dispatching dialog"
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
            self.set_outcome_var_type(self.ui.outcome_sel.itemText(self.ui.outcome_sel.currentIndex()))

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
            #self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
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
        self.check_if_ready()

    def launch_add_regressor_dialog(self):
        reg_dialog = RegressorSelectDialog(self.outcome_var_name, self.regressors_model, sample=self.sample)
        result = reg_dialog.exec_()
        if result == reg_dialog.Accepted:
            if self.regressors_model.rowCount() > 0:
                index = self.regressors_model.index(self.regressors_model.rowCount() - 1, 0)
                self.update_main_plot_from_regressors(index)
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
            #print res
            self.ui.r_squared_label.setText("R<sup>2</sup> = %.2f" % res.get("adj_r2", np.nan))
            f_nom, f_dem = res.get("f_stat_df", (0, 0))
            self.ui.f_value_label.setText("F(%d,%d) = %.2f" % (f_nom, f_dem, res.get("f_stats_val", np.nan)))
            self.ui.p_value_label.setText("P = %g" % res.get("f_pval", np.nan))
            coeffs_df = res["coefficients_df"]
            self.result_model.set_df(coeffs_df)
            self.coefs_df = coeffs_df
            self.regression_results = res
            self.draw_coefficints_plot()
            self.ui.calculate_button.setEnabled(1)
            return


    def update_main_plot_from_results(self, index):
        row = index.row()
        var_name_index = self.result_model.index(row, 0)
        var_name = unicode(self.result_model.data(var_name_index, QtCore.Qt.DisplayRole))
        if var_name == "(Intercept)":
            df2 = self.regression_results["data"]
            #df2["Jitter"] = np.random.random(len(df2))
            #df2.dropna(inplace=True)
            #self.plot.draw_scatter(df2, "Jitter", self.outcome_var_name, reg_line=False)
            #b = np.mean(df2[self.outcome_var_name])
            #self.plot.axes.axhline(b, ls="--", c=(0.3, 0.3, 0.3))
            self.plot.draw_intercept(df2, self.outcome_var_name)
            #self.plot.draw()
        else:
            #get components
            components = self.coefs_df.loc[var_name, "components"]
            if len(components) > 1:
                #interaction term
                if len(components)==2:
                    self.draw_interaction_plot(components[0],components[1])
                else:
                    components2 = np.random.choice(components,2,replace=False)
                    self.draw_interaction_plot(components2[0],components2[1])
            else:
                target_var = components[0]
                target_type = self.regression_results["var_types"][target_var]
                df2 = self.isolate_one(target_var)
                if target_type == "n":
                    self.plot_nominal_intercepts(df2, target_var)
                else:
                    self.plot.draw_scatter(df2, target_var, self.outcome_var_name, reg_line=True)
                self.plot.set_figure_title("Mean effect of %s" % target_var)
        return


    def update_main_plot_from_regressors(self, index):
        row = index.row()
        var_name_index = self.regressors_model.index(row, 0)
        var_name = unicode(self.regressors_model.data(var_name_index, QtCore.Qt.DisplayRole))
        if "*" in var_name:
            factors = var_name.split("*")
            if len(factors) > 2:
                factors = random.sample(factors, 2)
            self.draw_two_vars_scatter_plot(factors[0], factors[1])
        else:
            self.draw_simple_scatter_plot(var_name)
        return


    def add_subjects_to_plot(self, index=None, subject_ids=None):
        #find selected subjects
        print "not yet implemented"
        return

    def draw_coefficints_plot(self):
        if self.coefs_df is not None:
            self.plot.draw_coefficients_plot(self.coefs_df)
        return

    def draw_residuals_plot(self):
        if self.regression_results is None:
            return
        residuals = self.regression_results["residuals"]
        fitted = self.regression_results["fitted"]
        names = self.regression_results["data_points"]
        assert isinstance(names, list)
        self.plot.draw_residuals(residuals, fitted, names)

    def draw_simple_scatter_plot(self, regressor_name):
        df = braviz_tab_data.get_data_frame_by_name([self.outcome_var_name, regressor_name])
        df.dropna(inplace=True)
        if braviz_tab_data.is_variable_name_real(regressor_name):
            reg_line = True
            labels_dict = None
            self.plot.draw_scatter(df, regressor_name, self.outcome_var_name, reg_line=reg_line, x_labels=labels_dict)
        else:
            labels_dict = braviz_tab_data.get_names_label_dict(regressor_name)
            if len(labels_dict) == 2:
                self.plot.draw_scatter(df, regressor_name, self.outcome_var_name, reg_line=True, x_labels=labels_dict)
            else:
                self.plot.draw_intercept(df, self.outcome_var_name, regressor_name, group_labels=labels_dict)


    def cut_and_sort(self, regressor1, regressor2,df):
        var_1_real = braviz_tab_data.is_variable_name_real(regressor1)
        var_2_real = braviz_tab_data.is_variable_name_real(regressor2)
        outcome = self.outcome_var_name
        hue_var = regressor2
        x_var = regressor1
        qualitative_map = True
        x_labels = None

        if var_2_real and not var_1_real:
            hue_var = regressor1
            x_var = regressor2
            labels = braviz_tab_data.get_names_label_dict(hue_var)
        elif var_2_real and var_1_real:
            #cut var2
            real_data = df.pop(regressor2)
            dmin, dmax = np.min(real_data), np.max(real_data)
            N_PIECES = 3
            delta = (dmax - dmin) / N_PIECES
            nom_data = (real_data - dmin) * N_PIECES // (dmax - dmin) + 1
            nom_data = np.minimum(nom_data, N_PIECES)
            nom_data = nom_data.astype(np.int)
            df[regressor2] = nom_data
            labels = dict((i + 1, "%s $\\geq$ %.3f" % (regressor2, dmin + i * delta)) for i in xrange(N_PIECES))
            qualitative_map = False
        else:
            labels = braviz_tab_data.get_names_label_dict(hue_var)
            assert x_var == regressor1
            if not var_1_real:
                x_labels = braviz_tab_data.get_names_label_dict(x_var)

        return df,x_var,hue_var,outcome,labels,qualitative_map,x_labels

    def draw_two_vars_scatter_plot(self, regressor1, regressor2):
        df = braviz_tab_data.get_data_frame_by_name([regressor1, regressor2, self.outcome_var_name])
        df.dropna(inplace=True)
        df,x_var,hue_var,outcome,labels,qualitative_map,x_labels = self.cut_and_sort(regressor1,regressor2,df)
        self.plot.draw_scatter(df, x_var, outcome, hue_var=hue_var, hue_labels=labels, qualitative_map=qualitative_map,
                               x_labels=x_labels)

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
                log.info("showing subject %s" % subj)
                self.add_subjects_to_plot(subject_ids=[int(subj)])


    def create_context_action(self, subject, scenario_id, scenario_name, show_name=None):
        if show_name is None:
            show_name = scenario_name

        def show_scenario():
            self.change_subject_in_mri_viewer(subject, scenario_id)

        action = QtGui.QAction("Show subject %s's %s" % (subject, show_name), None)
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
        if len(outcome_scenarios) > 0:
            scenarios[self.outcome_var_name] = outcome_scenarios.items()
        regressors = self.regressors_model.get_regressors()
        for reg in regressors:
            reg_idx = braviz_tab_data.get_var_idx(reg)
            reg_scenarios = braviz_user_data.get_variable_scenarios(reg_idx)
            if len(reg_scenarios):
                scenarios[reg] = reg_scenarios.items()

        menu = QtGui.QMenu("Subject %s" % subject)
        launch_mri_action = self.create_context_action(subject, None, "MRI")
        menu.addAction(launch_mri_action)

        log = logging.getLogger(__name__)
        log.debug(scenarios)
        for var, scn_lists in scenarios.iteritems():
            for scn_id, scn_name in scn_lists:
                action = self.create_context_action(subject, scn_id, scn_name, var)
                menu.addAction(action)

        menu.exec_(global_pos)

    def subject_details_from_plot(self, pos):
        #print "context menu"
        #print pos
        print "not yet implemented"
        return
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
        address = ('localhost', 6001)
        auth_key = multiprocessing.current_process().authkey
        auth_key_asccii = binascii.b2a_hex(auth_key)
        listener = multiprocessing.connection.Listener(address, authkey=auth_key)

        #self.mri_viewer_process = multiprocessing.Process(target=mriMultSlicer.launch_new, args=(pipe_mri_side,))
        log.info("launching viewer")
        log.info([sys.executable, "-m", "braviz.applications.subject_overview", "0", auth_key_asccii])
        self.mri_viewer_process = subprocess.Popen([sys.executable, "-m", "braviz.applications.subject_overview",
                                                    "0", auth_key_asccii])

        #self.mri_viewer_process = multiprocessing.Process(target=subject_overview.run, args=(pipe_mri_side,))
        #self.mri_viewer_process.start()
        self.mri_viewer_pipe = listener.accept()
        self.poll_timer.start(200)

    def change_subject_in_mri_viewer(self, subj, scenario=None):
        log = logging.getLogger(__name__)
        if (self.mri_viewer_process is None) or (self.mri_viewer_process.poll() is not None):
            self.launch_mri_viewer()
        if self.mri_viewer_pipe is not None:
            message = {'subject': str(subj)}
            if scenario is not None:
                message["scenario"] = scenario
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
        vars_state["outcome"] = self.outcome_var_name
        vars_state["regressors"] = self.regressors_model.get_regressors()
        vars_state["interactions"] = self.regressors_model.get_interactions()
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
        dialog = braviz.interaction.qt_dialogs.SaveScenarioDialog(app_name, state, params)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            #save main plot as screenshot
            scn_id = params["scn_id"]
            pixmap = QtGui.QPixmap.grabWidget(self.plot)
            file_name = "scenario_%d.png" % scn_id
            data_root = braviz.readAndFilter.kmc40_auto_data_root()
            file_path = os.path.join(data_root, "braviz_data", "scenarios", file_name)
            log.info(file_path)
            pixmap.save(file_path)
        log.info("saving")
        log.info(state)

    def load_scenario_dialog(self):
        app_name = os.path.splitext(os.path.basename(__file__))[0]
        wanted_state = {}
        dialog = braviz.interaction.qt_dialogs.LoadScenarioDialog(app_name, wanted_state)
        res = dialog.exec_()
        log = logging.getLogger(__name__)
        if res == dialog.Accepted:
            log.info("Loading state")
            log.info(wanted_state)
            self.restore_state(wanted_state)

    def restore_state(self, wanted_state):
        #restore outcome
        #sample
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
        #restore regressors
        regressors = wanted_state["vars"].get("regressors", tuple())
        self.regressors_model.reset_data(regressors)
        #restore interactions
        interactions = wanted_state["vars"].get("interactions", tuple())
        #TODO: Must find a better way to encode interactions
        for inter in interactions:
            tokens = inter.split("*")
            self.regressors_model.add_interactor_by_names(tokens)
        self.regressors_model.show_interactions(True)
        self.regressors_model.show_regressors(True)
        #calculate anova
        self.check_if_ready()
        if self.ui.calculate_button.isEnabled():
            self.calculate_linear_reg()
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

        def calculate_beta_hat(a_isolating,a_components,a_factor_terms,a_beta_j):
            _other_components = set(a_components)
            _other_components.remove(a_isolating)
            _var_types = map(results_var_types_.get,_other_components)
            if "b" in _var_types or "r" in _var_types:
                return 0
            else:
                _indicator_vec = np.ones(len(standarized_data))
                for _base_var in _other_components:
                    #find level associated with current factor in other terms
                    for _cand in a_factor_terms:
                        if _cand.startswith(_base_var):
                            _level = _cand[len(_base_var)+1:]
                            _l_dict = braviz_tab_data.get_names_label_dict(_base_var)
                            _i_l_dict=dict((v,k) for k,v in _l_dict.iteritems())
                            _li = int(_i_l_dict[_level])
                            _col = standarized_data[_base_var].get_values().astype(np.int)
                            _matches = (_col == _li).astype(np.int)
                            _indicator_vec *= _matches
                _indicator_mean = np.mean(_indicator_vec)
                _beta_j_hat = _indicator_mean*a_beta_j
                return _beta_j_hat

        if results_var_types_[isolating_factor] == "n":
            ls = np.unique(standarized_data[isolating_factor])
            levels = [df3.index[df3[isolating_factor] == l] for l in ls]
            labels_dict = braviz_tab_data.get_names_label_dict(isolating_factor)
            i_labels_dict=dict((v,k) for k,v in labels_dict.iteritems())
        for l,l_id in izip(levels,ls):
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
                            sub_level = var[len(base_var)+1 :]
                            sub_level_id = i_labels_dict[sub_level]
                            if int(sub_level_id) == int(l_id):
                                # it is really an intercept term
                                beta_0 += beta_j
                    else:
                        #first need to find if I am at correct level
                        interaction_terms = var.split("*")
                        for cand in interaction_terms:
                            if cand.startswith(isolating_factor):
                                sub_level = cand[len(isolating_factor)+1 :]
                                sub_level_id = i_labels_dict[sub_level]
                                if int(sub_level_id) == int(l_id):
                                    beta_j_hat = calculate_beta_hat(isolating_factor,components,
                                                                    interaction_terms,beta_j)
                                    if np.isfinite(beta_j_hat):
                                        beta_0 += beta_j_hat
                else:
                    if len(components) == 1:
                        base_var = components[0]
                        if base_var == isolating_factor:
                            beta_1 += beta_j
                    else:
                        interaction_terms = var.split("*")
                        beta_j_hat = calculate_beta_hat(isolating_factor,components,interaction_terms,beta_j)
                        if np.isfinite(beta_j_hat):
                            beta_1 += beta_j_hat

            print "beta1", beta_1
            print "beta0", beta_0
            df3[self.outcome_var_name][l] = beta_0 + beta_1 * df3[isolating_factor][l].values.squeeze().astype(np.int)
        df3[self.outcome_var_name] += res
        if un_standardize is False:
            return df3
        #fix outcome var
        outcome_data = df3[self.outcome_var_name]
        m, s = self.regression_results["mean_sigma"][self.outcome_var_name]
        us_outcome = 2 * s * outcome_data + m
        df3[self.outcome_var_name] = us_outcome
        #fix x_var
        type = results_var_types_[isolating_factor]
        x_data = df3[isolating_factor]
        if type == "r":
            m, s = self.regression_results["mean_sigma"][isolating_factor]
            us_x_data = 2 * s * x_data + m
            df3[isolating_factor] = us_x_data
        elif type == "b":
            m, s = self.regression_results["mean_sigma"][isolating_factor]
            us_x_data = s * x_data + m
            df3[isolating_factor] = us_x_data
        return df3

    def plot_nominal_intercepts(self, df, var_name):
        # df = braviz_tab_data.get_data_frame_by_name((self.outcome_var_name,var_name))
        group_labels = braviz_tab_data.get_names_label_dict(var_name)
        df[var_name]=df[var_name].astype(np.int)
        self.plot.draw_intercept(df, self.outcome_var_name, var_name, group_labels=group_labels)

    def draw_interaction_plot(self,reg1,reg2):

        df = self.regression_results["standardized_model"]
        df2,x_var,hue_var,outcome,labels,qualitative_map,x_labels = self.cut_and_sort(reg1,reg2,df.copy())
        groups_series=df2[hue_var]
        print "testing %s %s"%(reg1,reg2)
        print "==============="
        print df
        print groups_series
        print "==============="
        df2 = self.isolate_in_groups(x_var,outcome,hue_var,groups_series)
        #df2[outcome]+=self.regression_results["residuals"]
        #df2[outcome]+=df2[hue_var]
        #un standardize yvar
        #self.plot.draw_scatter(df2, x_var, outcome, hue_var=hue_var, hue_labels=labels, qualitative_map=qualitative_map,
        #                       x_labels=x_labels)
        self.plot.draw_scatter(df2,x_var,outcome,hue_var=hue_var,reg_line = False)

    def isolate_in_groups(self,x_var,y_var,z_var,groups):
        work_df = self.regression_results["standardized_model"]
        fitted = self.evaluate_linear_model(work_df)
        df_ans = self.regression_results["data"][[x_var]].copy()
        df_ans[z_var]=groups
        df_ans[y_var]=fitted
        return df_ans
    def evaluate_linear_model(self,variables_df):
        coefs_df = self.coefs_df
        var_types = self.regression_results["var_types"]

        fitted = np.zeros(len(variables_df))
        for coef in coefs_df.index:
            if coef == "(Intercept)":
                fitted+=coefs_df["Slope"][coef]
            else:
                comps = coefs_df["components"][coef]
                c_df = variables_df[list(comps)]
                for c in comps:
                    if var_types[c] == "n":
                        pass
                prod=c_df.product(axis=1)
                prod*=coefs_df["Slope"][coef]
                fitted+=prod
        return fitted

def run():
    import sys
    from braviz.utilities import configure_console_logger
    #configure_logger("lm_task")
    configure_console_logger("lm_task")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = LinearModelApp()
    #ic = main_window.windowIcon()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise


if __name__ == '__main__':
    run()
