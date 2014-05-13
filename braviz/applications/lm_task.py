from __future__ import division

__author__ = 'Diego'

import PyQt4.QtGui as QtGui
import PyQt4.QtCore as QtCore
from PyQt4.QtGui import QMainWindow

from braviz.interaction.qt_guis.linear_reg import Ui_LinearModel
import braviz.interaction.qt_dialogs
import braviz.interaction.qt_sample_select_dialog
from braviz.interaction.qt_dialogs import OutcomeSelectDialog, RegressorSelectDialog, MatplotWidget,\
    InteractionSelectDialog

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


class LnearModelApp(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.outcome_var_name = None
        self.model = None
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
        self.ui = Ui_LinearModel()
        self.ui.setupUi(self)
        self.ui.outcome_sel.insertSeparator(self.ui.outcome_sel.count()-1)
        self.ui.outcome_sel.setCurrentIndex(self.ui.outcome_sel.count()-1)
        #self.ui.outcome_sel.currentIndexChanged.connect(self.dispatch_outcome_select)
        self.ui.outcome_sel.activated.connect(self.dispatch_outcome_select)
        self.ui.add_regressor_button.clicked.connect(self.launch_add_regressor_dialog)
        self.ui.reg_table.setModel(self.regressors_model)
        self.ui.reg_table.customContextMenuRequested.connect(self.launch_regressors_context_menu)
        self.ui.add_interaction_button.clicked.connect(self.dispatch_interactions_dialog)
        self.ui.calculate_button.clicked.connect(self.calculate_linear_reg)
        self.ui.results_table.setModel(self.result_model)

        self.ui.matplot_layout = QtGui.QVBoxLayout()
        self.plot = MatplotWidget(initial_message="Welcome\n\nSelect Outcome and add Regressors to start")
        self.ui.matplot_layout.addWidget(self.plot)
        self.ui.plot_frame.setLayout(self.ui.matplot_layout)
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


    def calculate_linear_reg(self):
        log = logging.getLogger(__name__)
        log.info("calculating lm")
        try:
            regressors = self.regressors_model.get_data_frame()
            interactions = self.regressors_model.get_interactors_dict()
            res = braviz.interaction.r_functions.calculate_normalized_linear_regression(self.outcome_var_name,
                                                                                  regressors,interactions,self.sample)
        except Exception as e:
            msg = QtGui.QMessageBox()
            msg.setText(str(e.message))
            msg.setIcon(msg.Warning)
            msg.setWindowTitle("lm Error")
            log.warning("lm Error")
            log.exception(e)
            msg.exec_()
            raise
        else:
            return
            self.result_model = braviz_models.AnovaResultsModel(*self.anova)
            self.ui.results_table.setModel(self.result_model)
            self.update_main_plot("Residuals")

    def update_main_plot_from_results(self, index):
        print "not yet implemented"
        return


    def update_main_plot_from_regressors(self, index):
        print "not yet implemented"
        return

    def update_main_plot(self, var_name):
        print "not yet implemented"
        return


    def add_subjects_to_plot(self, index=None,subject_ids=None):
        #find selected subjects
        print "not yet implemented"
        return


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


def run():
    import sys
    from braviz.utilities import configure_console_logger
    #configure_logger("lm_task")
    configure_console_logger("lm_task")
    app = QtGui.QApplication(sys.argv)
    log = logging.getLogger(__name__)
    log.info("started")
    main_window = LnearModelApp()
    #ic = main_window.windowIcon()
    main_window.show()
    try:
        app.exec_()
    except Exception as e:
        log.exception(e)
        raise

if __name__ == '__main__':
    run()
